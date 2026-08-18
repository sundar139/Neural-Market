"""v3 training loop: lead-lag signature RBF-MMD + strengthened internal gate.

v3 replaces v2's cumulative-path-only signature with a lead-lag
representation that makes local variation and quadratic-variation
information visible to the truncated signature.  The RBF-MMD framework,
variance calibration, and architecture are preserved exactly from v2.

The internal gate is strengthened: it now requires bounded variance ratio,
bounded terminal dispersion, path uniqueness, return-ACF agreement, and a
drift-vs-diffusion RMS ratio (all computed from training/internal data
only).
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch
from torch import Tensor, nn

from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.sde_windows import (
    FeatureNormalizer,
    FitSelectionSplit,
    WindowSpec,
    compute_context_features,
    fit_cumret_scale,
)
from neuralmarket.models.leadlag import leadlag_augment_path
from neuralmarket.models.neural_sde import ConditionalNeuralSde
from neuralmarket.models.signature import truncated_signature_features
from neuralmarket.models.signature_mmd import (
    SignatureStandardizer,
    fit_rbf_bandwidth_sq,
    fit_signature_standardizer,
    log_variance_penalty_per_path,
    rbf_mmd_sq,
    signature_feature_vector,
)
from neuralmarket.research.neural_sde_trainer import TrainingConfig, _param_snapshot
from neuralmarket.research.neural_sde_trainer_v2 import (
    TrainingOutcomeV2,
    _as_window,
    _window_tensors,
)


@dataclass(frozen=True)
class V3ObjectiveConfig:
    """Frozen v3 objective and internal-gate configuration."""

    kernel: str = "rbf"
    signature_level: int = 3
    standardize_features: bool = True
    standardization_floor_eps: float = 1e-8
    bandwidth_source: str = "train_fit_real_standardized"
    bandwidth_method: str = "median_pairwise_squared_distance"
    bandwidth_max_vectors: int = 512
    variance_penalty_coefficient: float = 1.0
    variance_eps: float = 1e-12
    gate_variance_ratio_lo: float = 0.50
    gate_variance_ratio_hi: float = 2.00
    gate_dispersion_ratio_lo: float = 0.50
    gate_dispersion_ratio_hi: float = 2.00
    gate_uniqueness_min: float = 0.99
    gate_return_acf1_max_diff: float = 0.25
    gate_drift_diffusion_ratio_max: float = 0.50
    internal_gate_seed: int = 7777
    internal_selection_paths_per_window: int = 16

    def config_hash(self) -> str:
        """Deterministic identity of the objective/gate config."""
        return hashlib.sha256(canonical_dumps(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class V3Statistics:
    """Frozen v3 objective statistics from TRAINING-FIT real paths."""

    standardizer: SignatureStandardizer
    standardization_hash: str
    bandwidth_sq: float
    bandwidth_vectors: int
    target_log_variance: float
    feature_dim: int
    fit_feature_count: int
    augmented_path_dim: int


def build_v3_statistics(
    fit_windows: Sequence[object],
    normalizer: FeatureNormalizer,
    cumret_scale: float,
    spec: WindowSpec,
    objective: V3ObjectiveConfig,
) -> V3Statistics:
    """Fit standardizer, bandwidth, and variance target from training-fit real paths."""
    fit_targets = torch.stack(
        [
            torch.tensor([float(v) for v in _as_window(w).target_returns], dtype=torch.float32)
            for w in fit_windows
        ]
    )
    fit_contexts = torch.stack(
        [
            torch.tensor(
                [
                    float(v)
                    for v in normalizer.normalize(
                        compute_context_features(_as_window(w), spec).array()
                    )
                ],
                dtype=torch.float32,
            )
            for w in fit_windows
        ]
    )
    points = leadlag_augment_path(fit_targets, fit_contexts, cumret_scale, spec)
    augmented_path_dim = int(points.shape[2])
    features = truncated_signature_features(points, objective.signature_level)
    vectors = signature_feature_vector(features)

    standardizer = fit_signature_standardizer(vectors, objective.standardization_floor_eps)
    std_vectors = standardizer.standardize(vectors)
    bandwidth_sq = fit_rbf_bandwidth_sq(std_vectors, objective.bandwidth_max_vectors)

    eps = objective.variance_eps
    pooled_var = float(fit_targets.var(dim=None, unbiased=False).item())
    target_log_variance = float(math.log(pooled_var + eps))

    return V3Statistics(
        standardizer=standardizer,
        standardization_hash=standardizer.standardization_hash(),
        bandwidth_sq=bandwidth_sq,
        bandwidth_vectors=int(std_vectors.shape[0]),
        target_log_variance=target_log_variance,
        feature_dim=int(vectors.shape[1]),
        fit_feature_count=int(vectors.shape[0]),
        augmented_path_dim=augmented_path_dim,
    )


def _leadlag_signature_vectors(
    returns: Tensor,
    context: Tensor,
    cumret_scale: float,
    spec: WindowSpec,
    objective: V3ObjectiveConfig,
    standardizer: SignatureStandardizer,
) -> Tensor:
    """Augment lead-lag, truncate, concatenate, and standardize signature vectors."""
    points = leadlag_augment_path(returns, context, cumret_scale, spec)
    features = truncated_signature_features(points, objective.signature_level)
    vectors = signature_feature_vector(features)
    return standardizer.standardize(vectors)


def _evaluate_selection_v3(
    model: ConditionalNeuralSde,
    sel_ctx: Tensor,
    sel_targets: Tensor,
    cumret_scale: float,
    spec: WindowSpec,
    objective: V3ObjectiveConfig,
    standardizer: SignatureStandardizer,
    bandwidth_sq: float,
    generator: torch.Generator,
) -> tuple[Tensor, Tensor]:
    """Selection RBF-MMD + per-path variance with lead-lag representation."""
    noise = torch.randn(
        sel_ctx.shape[0], spec.horizon, model.config.brownian_dim, generator=generator
    )
    with torch.no_grad():
        generated = model(sel_ctx, noise)
    real_vectors = _leadlag_signature_vectors(
        sel_targets, sel_ctx, cumret_scale, spec, objective, standardizer
    )
    gen_vectors = _leadlag_signature_vectors(
        generated, sel_ctx, cumret_scale, spec, objective, standardizer
    )
    rbf = rbf_mmd_sq(real_vectors, gen_vectors, bandwidth_sq)
    penalty = log_variance_penalty_per_path(generated, sel_targets, objective.variance_eps)
    total = rbf + objective.variance_penalty_coefficient * penalty
    return rbf, total


def train_internal_v3(
    model: ConditionalNeuralSde,
    config: TrainingConfig,
    split: FitSelectionSplit,
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    statistics: V3Statistics,
    spec: WindowSpec | None = None,
    objective: V3ObjectiveConfig | None = None,
) -> TrainingOutcomeV2:
    """Train v3 with lead-lag RBF signature MMD on the fit subset."""
    spec = WindowSpec() if spec is None else spec
    objective = V3ObjectiveConfig() if objective is None else objective
    standardizer = statistics.standardizer
    bandwidth_sq = statistics.bandwidth_sq
    cumret_scale = fit_cumret_scale(training_returns.detach().cpu().numpy(), spec.horizon)

    fit_ctx, fit_targets, _ = _window_tensors(split.fit_windows, normalizer, cumret_scale, spec)
    sel_ctx, sel_targets, _ = _window_tensors(
        split.selection_windows, normalizer, cumret_scale, spec
    )

    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    noise_gen = torch.Generator().manual_seed(config.data_seed)
    order_gen = torch.Generator().manual_seed(config.data_seed)

    def selection_scores() -> tuple[float, float]:
        rbf, total = _evaluate_selection_v3(
            model,
            sel_ctx,
            sel_targets,
            cumret_scale,
            spec,
            objective,
            standardizer,
            bandwidth_sq,
            noise_gen,
        )
        return float(rbf.item()), float(total.item())

    initial_rbf, initial_sel_total = selection_scores()
    best_total = initial_sel_total
    best_rbf = initial_rbf
    best_epoch = 0
    best_params = _param_snapshot(model)
    epochs_without_improvement = 0

    rbf_curve: list[float] = []
    total_curve: list[float] = []
    selection_rbf_curve: list[float] = [initial_rbf]
    selection_total_curve: list[float] = []

    n_fit = fit_ctx.shape[0]
    n_batches = max(1, (n_fit + config.batch_size - 1) // config.batch_size)

    for epoch in range(1, config.max_epochs + 1):
        order = torch.randperm(n_fit, generator=order_gen)
        epoch_rbf = 0.0
        epoch_total = 0.0
        for start in range(0, n_fit, config.batch_size):
            idx = order[start : start + config.batch_size]
            batch_ctx = fit_ctx[idx]
            batch_targets = fit_targets[idx]
            noise = torch.randn(
                batch_ctx.shape[0],
                spec.horizon,
                model.config.brownian_dim,
                generator=noise_gen,
            )
            generated = model(batch_ctx, noise)
            real_vectors = _leadlag_signature_vectors(
                batch_targets,
                batch_ctx,
                cumret_scale,
                spec,
                objective,
                standardizer,
            )
            gen_vectors = _leadlag_signature_vectors(
                generated,
                batch_ctx,
                cumret_scale,
                spec,
                objective,
                standardizer,
            )
            rbf = rbf_mmd_sq(real_vectors, gen_vectors, bandwidth_sq)
            penalty = log_variance_penalty_per_path(
                generated, batch_targets, objective.variance_eps
            )
            total = rbf + objective.variance_penalty_coefficient * penalty
            if not torch.isfinite(total) or not torch.isfinite(rbf):
                raise RuntimeError("non-finite v3 signature loss")
            optimizer.zero_grad(set_to_none=True)
            total.backward()  # type: ignore[no-untyped-call]
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), config.grad_norm_clip)
            if not torch.isfinite(torch.as_tensor(grad_norm)):
                raise RuntimeError("non-finite gradient norm v3")
            for param in model.parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError("non-finite gradient v3")
            optimizer.step()
            for param in model.parameters():
                if not torch.isfinite(param).all():
                    raise RuntimeError("non-finite params v3")
            epoch_rbf += float(rbf.item())
            epoch_total += float(total.item())

        rbf_curve.append(epoch_rbf / n_batches)
        total_curve.append(epoch_total / n_batches)
        sel_rbf, sel_total = selection_scores()
        selection_rbf_curve.append(sel_rbf)
        selection_total_curve.append(sel_total)
        if not math.isfinite(sel_rbf):
            raise RuntimeError("non-finite v3 selection RBF-MMD")
        if sel_total < best_total:
            best_total = sel_total
            best_rbf = sel_rbf
            best_epoch = epoch
            best_params = _param_snapshot(model)
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                break

    if best_epoch == 0 or best_total >= initial_sel_total:
        raise RuntimeError(
            "V3 NO IMPROVEMENT: best total loss did not improve "
            f"(initial={initial_sel_total:.6e}, best={best_total:.6e})"
        )

    state = model.state_dict()
    for name, values in best_params.items():
        state[name].copy_(torch.tensor(values, dtype=state[name].dtype).reshape(state[name].shape))
    model.load_state_dict(state)

    return TrainingOutcomeV2(
        initial_internal_rbf=initial_rbf,
        best_internal_rbf=best_rbf,
        best_epoch=best_epoch,
        final_epoch=epoch,
        rbf_curve=rbf_curve,
        total_curve=total_curve,
        selection_rbf_curve=selection_rbf_curve,
        selection_total_curve=selection_total_curve,
    )


def refit_final_v3(
    model: ConditionalNeuralSde,
    config: TrainingConfig,
    windows: Sequence[object],
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    epochs: int,
    statistics: V3Statistics,
    spec: WindowSpec | None = None,
    objective: V3ObjectiveConfig | None = None,
) -> None:
    """Refit v3 on ALL eligible training windows for exactly N epochs."""
    spec = WindowSpec() if spec is None else spec
    objective = V3ObjectiveConfig() if objective is None else objective
    standardizer = statistics.standardizer
    bandwidth_sq = statistics.bandwidth_sq
    cumret_scale = fit_cumret_scale(training_returns.detach().cpu().numpy(), spec.horizon)

    ctx, targets, _ = _window_tensors(windows, normalizer, cumret_scale, spec)
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    noise_gen = torch.Generator().manual_seed(config.data_seed)
    order_gen = torch.Generator().manual_seed(config.data_seed)
    n = ctx.shape[0]

    for _ in range(epochs):
        order = torch.randperm(n, generator=order_gen)
        for start in range(0, n, config.batch_size):
            idx = order[start : start + config.batch_size]
            batch_ctx = ctx[idx]
            batch_targets = targets[idx]
            noise = torch.randn(
                batch_ctx.shape[0],
                spec.horizon,
                model.config.brownian_dim,
                generator=noise_gen,
            )
            generated = model(batch_ctx, noise)
            real_vectors = _leadlag_signature_vectors(
                batch_targets,
                batch_ctx,
                cumret_scale,
                spec,
                objective,
                standardizer,
            )
            gen_vectors = _leadlag_signature_vectors(
                generated,
                batch_ctx,
                cumret_scale,
                spec,
                objective,
                standardizer,
            )
            rbf = rbf_mmd_sq(real_vectors, gen_vectors, bandwidth_sq)
            penalty = log_variance_penalty_per_path(
                generated, batch_targets, objective.variance_eps
            )
            total = rbf + objective.variance_penalty_coefficient * penalty
            if not torch.isfinite(total):
                raise RuntimeError("non-finite v3 loss during final refit")
            optimizer.zero_grad(set_to_none=True)
            total.backward()  # type: ignore[no-untyped-call]
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), config.grad_norm_clip)
            if not torch.isfinite(torch.as_tensor(grad_norm)):
                raise RuntimeError("non-finite grad norm v3 refit")
            for param in model.parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError("non-finite gradient v3 refit")
            optimizer.step()
            for param in model.parameters():
                if not torch.isfinite(param).all():
                    raise RuntimeError("non-finite params v3 refit")


def _return_acf1(returns: np.ndarray) -> float:
    """Autocorrelation at lag 1 of a 1D return series."""
    n = returns.shape[0]
    if n < 2:
        return 0.0
    mean = returns.mean()
    var = returns.var()
    if var < 1e-30:
        return 0.0
    return float(np.mean((returns[:-1] - mean) * (returns[1:] - mean)) / var)


def _drift_diffusion_rms(
    model: ConditionalNeuralSde,
    ctx: Tensor,
    spec: WindowSpec,
    n_samples: int,
    generator: torch.Generator,
) -> tuple[float, float]:
    """Compute RMS of per-step drift and diffusion contributions.

    For each step:
        drift  = b_x(t, state, ctx) * dt
        diffusion = sigma_x(t, state, ctx) * sqrt(dt) * noise
    """
    batch = min(ctx.shape[0], n_samples)
    sub_ctx = ctx[:batch]
    n_ctx = sub_ctx.shape[0]
    dt = spec.dt
    sqrt_dt = dt**0.5
    time_unit = 1.0 / spec.horizon

    model.eval()
    state = model.initial_state(sub_ctx)
    drift_sq_sum = 0.0
    diff_sq_sum = 0.0
    count = 0

    noise = torch.randn(n_ctx, spec.horizon, model.config.brownian_dim, generator=generator)

    with torch.no_grad():
        for k in range(spec.horizon):
            t = torch.full(
                (n_ctx,),
                float(k) * time_unit,
                dtype=sub_ctx.dtype,
                device=sub_ctx.device,
            )
            mu = model.drift_at(t, state, sub_ctx)
            sigma = model.diffusion_at(t, state, sub_ctx)
            drift_contrib = (mu[:, 0] * dt).cpu().numpy()
            diff_contrib = (sigma[:, 0] * sqrt_dt * noise[:, k, 0]).cpu().numpy()
            drift_sq_sum += float(np.sum(drift_contrib**2))
            diff_sq_sum += float(np.sum(diff_contrib**2))
            count += n_ctx
            step = mu * dt + sigma * sqrt_dt * noise[:, k, :]
            state = state + step

    if count == 0:
        return 0.0, 0.0
    drift_rms = (drift_sq_sum / count) ** 0.5
    diff_rms = (diff_sq_sum / count) ** 0.5
    return drift_rms, diff_rms


def evaluate_internal_gate_v3(
    model: ConditionalNeuralSde,
    split: FitSelectionSplit,
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    spec: WindowSpec | None = None,
    objective: V3ObjectiveConfig | None = None,
) -> tuple[dict[str, float | int | str | bool], bool]:
    """Evaluate the v3 INTERNAL gate on the SELECTION subset only.

    Criteria (ALL must pass):
      B. 0.50 <= var_gen/var_real <= 2.00
      C. 0.50 <= std_gen_terminal/std_real_terminal <= 2.00
      D. path uniqueness >= 0.99
      E. |ACF1_gen - ACF1_real| <= 0.25
      F. drift_rms / diffusion_rms <= 0.50
    """
    spec = WindowSpec() if spec is None else spec
    objective = V3ObjectiveConfig() if objective is None else objective
    cumret_scale = fit_cumret_scale(training_returns.detach().cpu().numpy(), spec.horizon)
    sel_ctx, sel_targets, _ = _window_tensors(
        split.selection_windows, normalizer, cumret_scale, spec
    )

    gate_gen = torch.Generator().manual_seed(objective.internal_gate_seed)
    model.eval()
    with torch.no_grad():
        noise = torch.randn(
            sel_ctx.shape[0],
            spec.horizon,
            model.config.brownian_dim,
            generator=gate_gen,
        )
        generated = model(sel_ctx, noise)

    gen_returns = generated.cpu().numpy()
    real_returns = sel_targets.cpu().numpy()

    gen_var = float(np.var(gen_returns))
    real_var = float(np.var(real_returns))
    variance_ratio = gen_var / real_var if real_var > 0.0 else float("nan")

    gen_terminal = np.asarray([gen_returns[i].sum() for i in range(gen_returns.shape[0])])
    real_terminal = np.asarray([real_returns[i].sum() for i in range(real_returns.shape[0])])
    gen_terminal_std = float(np.std(gen_terminal))
    real_terminal_std = float(np.std(real_terminal))
    dispersion_ratio = (
        gen_terminal_std / real_terminal_std if real_terminal_std > 0.0 else float("nan")
    )

    fingerprints = {
        tuple(float(v) for v in row.round(6))
        for row in gen_returns[: min(gen_returns.shape[0], 2048)]
    }
    uniqueness = len(fingerprints) / min(gen_returns.shape[0], 2048)

    gen_flat = gen_returns.ravel()
    real_flat = real_returns.ravel()
    gen_acf1 = _return_acf1(gen_flat)
    real_acf1 = _return_acf1(real_flat)
    acf1_diff = abs(gen_acf1 - real_acf1)

    drift_gen = torch.Generator().manual_seed(objective.internal_gate_seed + 1)
    drift_rms, diff_rms = _drift_diffusion_rms(model, sel_ctx, spec, 64, drift_gen)
    dd_ratio = drift_rms / diff_rms if diff_rms > 0.0 else float("inf")

    criterion_results: dict[str, bool] = {}
    criterion_results["variance_ratio"] = bool(
        math.isfinite(variance_ratio)
        and objective.gate_variance_ratio_lo <= variance_ratio <= objective.gate_variance_ratio_hi
    )
    criterion_results["dispersion_ratio"] = bool(
        math.isfinite(dispersion_ratio)
        and objective.gate_dispersion_ratio_lo
        <= dispersion_ratio
        <= objective.gate_dispersion_ratio_hi
    )
    criterion_results["uniqueness"] = bool(uniqueness >= objective.gate_uniqueness_min)
    criterion_results["acf1_agreement"] = bool(
        math.isfinite(acf1_diff) and acf1_diff <= objective.gate_return_acf1_max_diff
    )
    criterion_results["drift_diffusion_ratio"] = bool(
        math.isfinite(dd_ratio) and dd_ratio <= objective.gate_drift_diffusion_ratio_max
    )

    gate_passed = all(criterion_results.values())

    diagnostics: dict[str, Any] = {
        "generated_daily_variance": gen_var,
        "real_daily_variance": real_var,
        "variance_ratio": variance_ratio,
        "generated_terminal_std": gen_terminal_std,
        "real_terminal_std": real_terminal_std,
        "terminal_dispersion_ratio": dispersion_ratio,
        "path_uniqueness_fraction": uniqueness,
        "generated_return_acf1": gen_acf1,
        "real_return_acf1": real_acf1,
        "return_acf1_abs_diff": acf1_diff,
        "drift_increment_rms": drift_rms,
        "diffusion_increment_rms": diff_rms,
        "drift_diffusion_rms_ratio": dd_ratio,
        "internal_gate_seed": objective.internal_gate_seed,
        "paths_per_window": 1,
        "criterion_results": criterion_results,
        "gate_passed": gate_passed,
        "gate_variance_ratio_range": [
            objective.gate_variance_ratio_lo,
            objective.gate_variance_ratio_hi,
        ],
        "gate_dispersion_ratio_range": [
            objective.gate_dispersion_ratio_lo,
            objective.gate_dispersion_ratio_hi,
        ],
        "gate_uniqueness_min": objective.gate_uniqueness_min,
        "gate_return_acf1_max_diff": objective.gate_return_acf1_max_diff,
        "gate_drift_diffusion_ratio_max": objective.gate_drift_diffusion_ratio_max,
    }
    return diagnostics, gate_passed
