"""v2 objective: RBF-MMD over individual truncated-signature feature vectors.

Replaces the v1 linear expected-signature MEAN-matching loss, which could not
distinguish distributions that share a mean signature vector but differ in
per-path dispersion (the v1 collapse).  v2 keeps the validated truncated
signature features (level 3) but compares every path's individual feature
vector through an RBF kernel, so per-path spread contributes directly to the
gradient.

All standardization statistics and the kernel bandwidth are derived from
TRAINING-FIT REAL signature vectors only; external validation can never enter
the estimator.  The estimator form is the clearly-specified biased MMD^2
(Gretton et al.); it is frozen here.

One minimal training-only anti-collapse term is included separately: a
log-variance matching penalty between generated and real TRAINING-target daily
returns.  It exists strictly to prevent trivial distributional collapse and is
not a stylized-fact scoreboard.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import torch
from torch import Tensor

from neuralmarket.data.manifests import canonical_dumps


def signature_feature_vector(features: dict[int, Tensor]) -> Tensor:
    """Concatenate per-level truncated-signature features into one vector.

    Args:
        features: Mapping ``{level: tensor (batch, dim**level)}``.

    Returns:
        Tensor ``(batch, sum_levels dim**level)`` for levels 1..max level.

    Raises:
        ValueError: If the feature set is empty or inconsistent.
    """
    if not features:
        raise ValueError("signature feature set is empty")
    keys = sorted(features)
    batch = next(iter(features.values())).shape[0]
    parts: list[Tensor] = []
    for key in keys:
        part = features[key]
        if part.ndim != 2 or part.shape[0] != batch:
            raise ValueError(f"signature feature level {key} must be (batch, dim**level)")
        parts.append(part)
    return torch.cat(parts, dim=1)


def signature_feature_dim(path_dim: int, level: int = 3) -> int:
    """Total dimension of the concatenated signature feature vector.

    Args:
        path_dim: Augmented path coordinate dimensionality.
        level: Maximum signature level.

    Returns:
        ``sum_k=1..level path_dim**k``.
    """
    if level < 1:
        raise ValueError("signature level must be at least 1")
    return int(sum(path_dim**k for k in range(1, level + 1)))


@dataclass(frozen=True)
class SignatureStandardizer:
    """Per-dimension z-score parameters fitted from training-fit real paths."""

    means: Tensor
    stds: Tensor

    def standardize(self, features: Tensor) -> Tensor:
        """Standardize individual signature vectors with fitted parameters.

        The standardizer's means/stds live on the device they were fitted on
        (historically cpu). When features are on another device (e.g. cuda),
        we co-locate the parameters to that device for the arithmetic.
        """
        features = torch.as_tensor(features)
        if features.ndim != 2 or features.shape[1] != self.means.shape[0]:
            raise ValueError(
                f"feature width {features.shape[1] if features.ndim == 2 else '?'} "
                f"does not match standardizer width {self.means.shape[0]}"
            )
        if not torch.isfinite(features).all():
            raise ValueError("standardizer input must be finite")
        means = self.means.to(device=features.device, dtype=features.dtype)
        stds = self.stds.to(device=features.device, dtype=features.dtype)
        return (features - means) / stds

    def standardization_hash(self) -> str:
        """Deterministic hash of the fitted standardization parameters."""
        return hashlib.sha256(
            canonical_dumps(
                {
                    "means": [float(v) for v in self.means.tolist()],
                    "stds": [float(v) for v in self.stds.tolist()],
                }
            ).encode("utf-8")
        ).hexdigest()


def fit_signature_standardizer(
    feature_matrix: Tensor, floor_eps: float = 1e-8
) -> SignatureStandardizer:
    """Fit per-dimension mean/std from a training-derived real feature matrix.

    Args:
        feature_matrix: ``(n_paths, dim)`` signature feature vectors of the
            training-fit REAL paths (never validation).
        floor_eps: Positive floor applied to per-dimension standard deviations
            so near-constant signature coordinates cannot divide by zero.

    Returns:
        Frozen standardizer.

    Raises:
        ValueError: If the matrix is empty, non-finite, or the floor is invalid.
    """
    matrix = torch.as_tensor(feature_matrix, dtype=torch.float32)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("feature matrix must be a non-empty 2-D tensor")
    if not matrix.isfinite().all():
        raise ValueError("feature matrix must be finite")
    if not math.isfinite(floor_eps) or floor_eps <= 0.0:
        raise ValueError("floor_eps must be positive and finite")
    means = matrix.mean(dim=0)
    stds = matrix.std(dim=0, unbiased=True)
    stds = torch.clamp(stds, min=floor_eps)
    return SignatureStandardizer(means=means, stds=stds)


def fit_rbf_bandwidth_sq(standardized_features: Tensor, max_vectors: int = 512) -> float:
    """Deterministic median-pairwise-squared-distance bandwidth (2*sigma^2 scale).

    The bandwidth is derived ONLY from training-fit real standardized
    signature vectors.  If more than ``max_vectors`` are supplied, the first
    ``max_vectors`` (deterministic chronological order) are used.  The median
    of the upper-triangle pairwise squared Euclidean distances is returned as
    ``bandwidth_sq``; the RBF kernel uses ``exp(-||x-y||^2 / (2*bandwidth_sq))``.

    Args:
        standardized_features: ``(n_paths, dim)`` standardized training-fit
            real signature vectors.
        max_vectors: Deterministic cap on vectors used for the pairwise median.

    Returns:
        Positive finite bandwidth_sq.

    Raises:
        ValueError: If the median is zero or non-finite (fail closed).
    """
    matrix = torch.as_tensor(standardized_features, dtype=torch.float32)
    if matrix.ndim != 2 or matrix.shape[0] < 2:
        raise ValueError("at least two feature vectors are required for a bandwidth")
    if not matrix.isfinite().all():
        raise ValueError("bandwidth input must be finite")
    if matrix.shape[0] > max_vectors:
        matrix = matrix[:max_vectors]
    n = matrix.shape[0]
    norms_sq = (matrix**2).sum(dim=1)  # (n,)
    # ||x - y||^2 = ||x||^2 + ||y||^2 - 2 x.y
    cross = matrix @ matrix.t()
    d2 = norms_sq.unsqueeze(1) + norms_sq.unsqueeze(0) - 2.0 * cross
    d2 = torch.clamp(d2, min=0.0)
    iu = torch.triu_indices(n, n, offset=1, device=matrix.device)
    values = d2[iu[0], iu[1]]
    if values.numel() == 0:
        raise ValueError("no pairwise distance available for bandwidth")
    median = float(values.median())
    if not math.isfinite(median) or median <= 0.0:
        raise ValueError(f"RBF bandwidth median must be positive and finite, got {median}")
    return median


def _rbf_kernel_matrix(a: Tensor, b: Tensor, bandwidth_sq: float) -> Tensor:
    """RBF kernel values between every pair in ``a`` and ``b``.

    ``k(x, y) = exp(-||x - y||^2 / (2 * bandwidth_sq))``.

    Args:
        a: ``(n_a, dim)`` standardized feature vectors.
        b: ``(n_b, dim)`` standardized feature vectors.
        bandwidth_sq: Positive kernel scale.

    Returns:
        ``(n_a, n_b)`` non-negative kernel matrix.
    """
    if not math.isfinite(bandwidth_sq) or bandwidth_sq <= 0.0:
        raise ValueError("bandwidth_sq must be positive and finite")
    norms_a = (a**2).sum(dim=1)
    norms_b = (b**2).sum(dim=1)
    d2 = norms_a.unsqueeze(1) + norms_b.unsqueeze(0) - 2.0 * (a @ b.t())
    d2 = torch.clamp(d2, min=0.0)
    return torch.exp(-d2 / (2.0 * bandwidth_sq))


def rbf_mmd_sq(real: Tensor, generated: Tensor, bandwidth_sq: float) -> Tensor:
    """Biased empirical MMD^2 between two sets of individual signature vectors.

    ``MMD^2 = E[k(x, x')] + E[k(y, y')] - 2 E[k(x, y)]`` with the RBF kernel,
    estimated as the average of the three kernel averages over the observed
    sets (the clearly-specified biased estimator; frozen form).

    Args:
        real: ``(n_real, dim)`` standardized real signature vectors.
        generated: ``(n_gen, dim)`` standardized generated signature vectors
            (gradient flows through these).
        bandwidth_sq: Positive frozen kernel scale.

    Returns:
        Non-negative scalar MMD^2 (biased), differentiable in ``generated``.

    Raises:
        ValueError: If the inputs are malformed or non-finite.
    """
    real = torch.as_tensor(real)
    generated = torch.as_tensor(generated)
    if real.ndim != 2 or generated.ndim != 2 or real.shape[1] != generated.shape[1]:
        raise ValueError("real and generated feature sets must be (batch, same_dim)")
    if real.shape[0] == 0 or generated.shape[0] == 0:
        raise ValueError("feature sets must be non-empty")
    if not real.isfinite().all() or not generated.isfinite().all():
        raise ValueError("MMD input features must be finite")
    k_xx = _rbf_kernel_matrix(real, real, bandwidth_sq)
    k_yy = _rbf_kernel_matrix(generated, generated, bandwidth_sq)
    k_xy = _rbf_kernel_matrix(real, generated, bandwidth_sq)
    mmd = k_xx.mean() + k_yy.mean() - 2.0 * k_xy.mean()
    return mmd


def per_path_variance(returns: Tensor) -> Tensor:
    """Within-path population variance of daily returns for each path.

    Computes the variance of each path's daily return increments
    independently, without pooling across paths or mixing path means.

    Args:
        returns: ``(n_paths, horizon)`` daily log return increments.

    Returns:
        ``(n_paths,)`` tensor of per-path population variances.

    Raises:
        ValueError: If the input is malformed.
    """
    if returns.ndim != 2:
        raise ValueError("returns must be (n_paths, horizon)")
    if not returns.isfinite().all():
        raise ValueError("returns must be finite")
    return returns.var(dim=1, unbiased=False)


def log_variance_penalty_per_path(
    generated: Tensor,
    real: Tensor,
    eps: float = 1e-12,
) -> Tensor:
    """Per-path log-variance matching penalty (anti-collapse term).

    For each path independently:
        L_i = (log(var(gen_i) + eps) - log(var(real_i) + eps))^2

    Then aggregates across the batch with mean.

    This avoids conflating within-path and between-path variation.

    Args:
        generated: ``(n_paths, horizon)`` generated daily log returns.
        real: ``(n_paths, horizon)`` real target daily log returns.
        eps: Positive floor so the log is always finite.

    Returns:
        Non-negative scalar penalty, differentiable in ``generated``.

    Raises:
        ValueError: If inputs are malformed.
    """
    if not math.isfinite(eps) or eps <= 0.0:
        raise ValueError("eps must be positive and finite")
    if generated.ndim != 2 or real.ndim != 2:
        raise ValueError("generated and real must be (n_paths, horizon)")
    if generated.shape != real.shape:
        raise ValueError("generated and real must have the same shape")
    if not generated.isfinite().all():
        raise ValueError("generated returns must be finite")
    var_gen = per_path_variance(generated)
    var_real = per_path_variance(real)
    log_var_gen = torch.log(var_gen + eps)
    log_var_real = torch.log(var_real + eps)
    return torch.mean((log_var_gen - log_var_real) ** 2)


def log_variance_penalty(
    generated: Tensor, target_log_variance: float, eps: float = 1e-12
) -> Tensor:
    """DEPRECATED: pooled log-variance penalty. Use log_variance_penalty_per_path.

    ``L = (log(var(generated) + eps) - target_log_variance)^2`` where
    ``var`` is the population variance pooled over all generated daily returns.

    This function is retained for backward compatibility only.
    """
    if not math.isfinite(target_log_variance):
        raise ValueError("target log-variance must be finite")
    if not math.isfinite(eps) or eps <= 0.0:
        raise ValueError("eps must be positive and finite")
    if generated.ndim != 2:
        raise ValueError("generated must be (n_paths, horizon)")
    if not generated.isfinite().all():
        raise ValueError("generated returns must be finite")
    var_gen = generated.var(dim=None, unbiased=False)
    log_var_gen = torch.log(var_gen + eps)
    return (log_var_gen - target_log_variance) ** 2
