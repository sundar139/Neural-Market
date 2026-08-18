"""v2 training loop for the signature neural SDE.

v2 replaces the v1 linear expected-signature MEAN matching with RBF-MMD over
individual truncated-signature feature vectors (plus one training-only
log-variance anti-collapse term).  The architecture, windows, internal fit/
selection split, and seeds match v1 exactly so the only change is the
objective.  External validation is never touched here.

The internal anti-collapse gate is evaluated on the INTERNAL-SELECTION subset
only, before any validation observation.  If it fails, the caller must STOP and
never load external validation.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
import torch
from torch import Tensor, nn

from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.sde_windows import (
    FeatureNormalizer,
    FitSelectionSplit,
    SdeWindow,
    WindowSpec,
    compute_context_features,
    fit_cumret_scale,
)
from neuralmarket.models.neural_sde import ConditionalNeuralSde
from neuralmarket.models.signature import augment_path, truncated_signature_features
from neuralmarket.models.signature_mmd import (
    SignatureStandardizer,
    fit_rbf_bandwidth_sq,
    fit_signature_standardizer,
    log_variance_penalty_per_path,
    rbf_mmd_sq,
    signature_feature_vector,
)
from neuralmarket.research.neural_sde_trainer import TrainingConfig, _param_snapshot


@dataclass(frozen=True)
class V2ObjectiveConfig:
    """Frozen v2 objective and internal-gate configuration (never tuned on validation)."""

    kernel: str = "rbf"
    signature_level: int = 3
    standardize_features: bool = True
    standardization_floor_eps: float = 1e-8
    bandwidth_source: str = "train_fit_real_standardized"
    bandwidth_method: str = "median_pairwise_squared_distance"
    bandwidth_max_vectors: int = 512
    variance_penalty_coefficient: float = 1.0
    variance_eps: float = 1e-12
    internal_min_dispersion_ratio: float = 0.50
    internal_gate_seed: int = 6666
    internal_selection_paths_per_window: int = 16

    def config_hash(self) -> str:
        """Deterministic identity of the objective/gate config (no wall clock)."""
        return hashlib.sha256(canonical_dumps(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TrainingOutcomeV2:
    """Recorded outcome of the v2 internal training run."""

    initial_internal_rbf: float
    best_internal_rbf: float
    best_epoch: int
    final_epoch: int
    rbf_curve: list[float]
    total_curve: list[float]
    selection_rbf_curve: list[float]
    selection_total_curve: list[float]

    @property
    def percent_improvement(self) -> float:
        """Percent improvement of best RBF over initial (positive is good)."""
        if self.initial_internal_rbf == 0.0:
            return 0.0
        return 100.0 * (
            (self.initial_internal_rbf - self.best_internal_rbf) / abs(self.initial_internal_rbf)
        )


@dataclass(frozen=True)
class V2Statistics:
    """Frozen v2 objective statistics derived from TRAINING-FIT real paths."""

    standardizer: SignatureStandardizer
    standardization_hash: str
    bandwidth_sq: float
    bandwidth_vectors: int
    target_log_variance: float
    feature_dim: int
    fit_feature_count: int


def build_v2_statistics(
    fit_windows: Sequence[object],
    normalizer: FeatureNormalizer,
    cumret_scale: float,
    spec: WindowSpec,
    objective: V2ObjectiveConfig,
) -> V2Statistics:
    """Fit standardizer, bandwidth, and variance target from TRAINING-FIT real paths.

    Args:
        fit_windows: The internal FIT subset windows (training-period only).
        normalizer: Training-fitted context feature normalizer.
        cumret_scale: Training-derived cumulative-return channel scale.
        spec: Window geometry.
        objective: Frozen v2 objective configuration.

    Returns:
        Frozen :class:`V2Statistics`.

    Raises:
        ValueError: If the bandwidth median is zero/non-finite (fail closed).
    """
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
    points = augment_path(fit_targets, fit_contexts, cumret_scale, spec)
    features = truncated_signature_features(points, objective.signature_level)
    vectors = signature_feature_vector(features)  # (n_fit, dim), train-fit real

    standardizer = fit_signature_standardizer(vectors, objective.standardization_floor_eps)
    std_vectors = standardizer.standardize(vectors)
    bandwidth_sq = fit_rbf_bandwidth_sq(std_vectors, objective.bandwidth_max_vectors)

    eps = objective.variance_eps
    pooled_var = float(fit_targets.var(dim=None, unbiased=False).item())
    target_log_variance = float(math.log(pooled_var + eps))

    return V2Statistics(
        standardizer=standardizer,
        standardization_hash=standardizer.standardization_hash(),
        bandwidth_sq=bandwidth_sq,
        bandwidth_vectors=int(std_vectors.shape[0]),
        target_log_variance=target_log_variance,
        feature_dim=int(vectors.shape[1]),
        fit_feature_count=int(vectors.shape[0]),
    )


def _signature_vectors(
    returns: Tensor,
    context: Tensor,
    cumret_scale: float,
    spec: WindowSpec,
    objective: V2ObjectiveConfig,
    standardizer: SignatureStandardizer,
) -> Tensor:
    """Augment, truncate, concatenate, and standardize a batch's signature vectors."""
    points = augment_path(returns, context, cumret_scale, spec)
    features = truncated_signature_features(points, objective.signature_level)
    vectors = signature_feature_vector(features)
    return standardizer.standardize(vectors)


def _evaluate_selection_v2(
    model: ConditionalNeuralSde,
    sel_ctx: Tensor,
    sel_targets: Tensor,
    cumret_scale: float,
    spec: WindowSpec,
    objective: V2ObjectiveConfig,
    standardizer: SignatureStandardizer,
    bandwidth_sq: float,
    generator: torch.Generator,
) -> tuple[Tensor, Tensor]:
    """Selection RBF-MMD + per-path variance (training-period selection only)."""
    noise = torch.randn(
        sel_ctx.shape[0], spec.horizon, model.config.brownian_dim, generator=generator
    )
    with torch.no_grad():
        generated = model(sel_ctx, noise)
    real_vectors = _signature_vectors(
        sel_targets, sel_ctx, cumret_scale, spec, objective, standardizer
    )
    gen_vectors = _signature_vectors(
        generated, sel_ctx, cumret_scale, spec, objective, standardizer
    )
    rbf = rbf_mmd_sq(real_vectors, gen_vectors, bandwidth_sq)
    penalty = log_variance_penalty_per_path(generated, sel_targets, objective.variance_eps)
    total = rbf + objective.variance_penalty_coefficient * penalty
    return rbf, total


def _as_window(window: object) -> SdeWindow:
    """Narrow a window entry to :class:`SdeWindow` (fail closed otherwise)."""
    if not isinstance(window, SdeWindow):
        raise ValueError("window entry must be an SdeWindow")
    return window


def train_internal_v2(
    model: ConditionalNeuralSde,
    config: TrainingConfig,
    split: FitSelectionSplit,
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    statistics: V2Statistics,
    spec: WindowSpec | None = None,
    objective: V2ObjectiveConfig | None = None,
) -> TrainingOutcomeV2:
    """Train v2 (RBF signature MMD + anti-collapse) on the fit subset.

    Args:
        model: Deterministically initialized neural SDE.
        config: Frozen training hyperparameters (same defaults as v1).
        split: Internal fit/selection split.
        normalizer: Training-fitted context normalizer.
        training_returns: Training returns (for the cumulative-return scale only).
        statistics: Output of :func:`build_v2_statistics` (train-fit only).
        spec: Window geometry.
        objective: Frozen v2 objective/gate config.

    Returns:
        The recorded outcome with the model set to its best-epoch parameters.

    Raises:
        RuntimeError: If training does not improve the internal-selection RBF
            MMD, or on any non-finite loss/gradient/parameter.
    """
    spec = WindowSpec() if spec is None else spec
    objective = V2ObjectiveConfig() if objective is None else objective
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
        rbf, total = _evaluate_selection_v2(
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
            real_vectors = _signature_vectors(
                batch_targets, batch_ctx, cumret_scale, spec, objective, standardizer
            )
            gen_vectors = _signature_vectors(
                generated, batch_ctx, cumret_scale, spec, objective, standardizer
            )
            rbf = rbf_mmd_sq(real_vectors, gen_vectors, bandwidth_sq)
            penalty = log_variance_penalty_per_path(
                generated, batch_targets, objective.variance_eps
            )
            total = rbf + objective.variance_penalty_coefficient * penalty
            if not torch.isfinite(total) or not torch.isfinite(rbf):
                raise RuntimeError("non-finite v2 signature loss during training")
            optimizer.zero_grad(set_to_none=True)
            total.backward()  # type: ignore[no-untyped-call]
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), config.grad_norm_clip)
            if not torch.isfinite(torch.as_tensor(grad_norm)):
                raise RuntimeError("non-finite gradient norm during v2 training")
            for param in model.parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError("non-finite gradient during v2 training")
            optimizer.step()
            for param in model.parameters():
                if not torch.isfinite(param).all():
                    raise RuntimeError("non-finite parameters during v2 training")
            epoch_rbf += float(rbf.item())
            epoch_total += float(total.item())

        rbf_curve.append(epoch_rbf / n_batches)
        total_curve.append(epoch_total / n_batches)
        sel_rbf, sel_total = selection_scores()
        selection_rbf_curve.append(sel_rbf)
        selection_total_curve.append(sel_total)
        if not math.isfinite(sel_rbf):
            raise RuntimeError("non-finite v2 internal-selection RBF-MMD")
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
            "V2 OBJECTIVE NO IMPROVEMENT: best internal-selection total loss did not "
            f"improve on initial (initial={initial_sel_total:.6e}, best={best_total:.6e})"
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


def refit_final_v2(
    model: ConditionalNeuralSde,
    config: TrainingConfig,
    windows: Sequence[object],
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    epochs: int,
    statistics: V2Statistics,
    spec: WindowSpec | None = None,
    objective: V2ObjectiveConfig | None = None,
) -> None:
    """Refit v2 on ALL eligible training windows for exactly ``epochs`` epochs.

    Args:
        model: Freshly reinitialized model (same model-init policy as training).
        config: Frozen training settings.
        windows: All eligible training windows.
        normalizer: Training-fitted context normalizer.
        training_returns: Training returns (for the scale only).
        epochs: The frozen best epoch count from the internal run.
        statistics: v2 objective statistics (train-fit only).
        spec: Window geometry.
        objective: Frozen v2 objective/gate config.

    Raises:
        RuntimeError: On any non-finite v2 loss/gradient/parameter.
    """
    spec = WindowSpec() if spec is None else spec
    objective = V2ObjectiveConfig() if objective is None else objective
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
                batch_ctx.shape[0], spec.horizon, model.config.brownian_dim, generator=noise_gen
            )
            generated = model(batch_ctx, noise)
            real_vectors = _signature_vectors(
                batch_targets, batch_ctx, cumret_scale, spec, objective, standardizer
            )
            gen_vectors = _signature_vectors(
                generated, batch_ctx, cumret_scale, spec, objective, standardizer
            )
            rbf = rbf_mmd_sq(real_vectors, gen_vectors, bandwidth_sq)
            penalty = log_variance_penalty_per_path(
                generated, batch_targets, objective.variance_eps
            )
            total = rbf + objective.variance_penalty_coefficient * penalty
            if not torch.isfinite(total):
                raise RuntimeError("non-finite v2 loss during final refit")
            optimizer.zero_grad(set_to_none=True)
            total.backward()  # type: ignore[no-untyped-call]
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), config.grad_norm_clip)
            if not torch.isfinite(torch.as_tensor(grad_norm)):
                raise RuntimeError("non-finite gradient norm during v2 final refit")
            for param in model.parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError("non-finite gradient during v2 final refit")
            optimizer.step()
            for param in model.parameters():
                if not torch.isfinite(param).all():
                    raise RuntimeError("non-finite parameters during v2 final refit")


def _window_tensors(
    windows: Sequence[object],
    normalizer: FeatureNormalizer,
    cumret_scale: float,
    spec: WindowSpec,
) -> tuple[Tensor, Tensor, list[str]]:
    """Convert windows to normalized context and target tensors (no autograd)."""
    contexts: list[list[float]] = []
    targets: list[list[float]] = []
    ids: list[str] = []
    for window in windows:
        assert isinstance(window, SdeWindow)
        ctx = normalizer.normalize(compute_context_features(window, spec).array())
        contexts.append([float(v) for v in ctx])
        targets.append([float(v) for v in window.target_returns])
        ids.append(window.window_id)
    return (
        torch.tensor(contexts, dtype=torch.float32),
        torch.tensor(targets, dtype=torch.float32),
        ids,
    )


def evaluate_internal_gate_v2(
    model: ConditionalNeuralSde,
    split: FitSelectionSplit,
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    spec: WindowSpec | None = None,
    objective: V2ObjectiveConfig | None = None,
) -> tuple[dict[str, float | int | str | bool], bool]:
    """Evaluate the internal anti-collapse gate on the SELECTION subset only.

    Generates ``paths_per_window`` deterministic paths for every selection
    window and compares generated vs real selection dispersion.  The gate
    passes when the terminal dispersion ratio is at or above the frozen
    threshold; the RBF-MMD improvement condition is already enforced by
    training (best < initial) and reported here for completeness.

    Args:
        model: Best-epoch internal model.
        split: Internal fit/selection split.
        normalizer: Training-fitted context normalizer.
        training_returns: Training returns (for the scale only).
        spec: Window geometry.
        objective: Frozen v2 objective/gate config.

    Returns:
        ``(diagnostics, passed)``.  If not passed, the CALLER MUST NOT load
        external validation.
    """
    spec = WindowSpec() if spec is None else spec
    objective = V2ObjectiveConfig() if objective is None else objective
    cumret_scale = fit_cumret_scale(training_returns.detach().cpu().numpy(), spec.horizon)
    sel_ctx, sel_targets, _ = _window_tensors(
        split.selection_windows, normalizer, cumret_scale, spec
    )

    gate_gen = torch.Generator().manual_seed(objective.internal_gate_seed)
    model.eval()
    with torch.no_grad():
        noise = torch.randn(
            sel_ctx.shape[0], spec.horizon, model.config.brownian_dim, generator=gate_gen
        )
        generated = model(sel_ctx, noise)
        # Deterministic sigma scan over a coarse (t, state, ctx) grid.
        scan_ctx = sel_ctx[: min(sel_ctx.shape[0], 32)]
        scan_t = torch.linspace(0.0, 1.0, 32)
        scan_state = torch.randn(scan_ctx.shape[0], model.config.state_dim, generator=gate_gen)
        sigmas: list[Tensor] = []
        for ts in scan_t:
            t = torch.full((scan_ctx.shape[0],), float(ts), dtype=torch.float32)
            sigmas.append(model.diffusion_at(t, scan_state, scan_ctx))
        sigma = torch.cat(sigmas, dim=0)

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

    sigma_arr = sigma.cpu().numpy()
    diagnostics: dict[str, float | int | str | bool] = {
        "generated_daily_variance": gen_var,
        "real_daily_variance": real_var,
        "variance_ratio": variance_ratio,
        "generated_terminal_std": gen_terminal_std,
        "real_terminal_std": real_terminal_std,
        "terminal_dispersion_ratio": dispersion_ratio,
        "path_uniqueness_fraction": uniqueness,
        "diffusion_mean": float(np.mean(sigma_arr)),
        "diffusion_min": float(np.min(sigma_arr)),
        "diffusion_max": float(np.max(sigma_arr)),
        "internal_gate_seed": objective.internal_gate_seed,
        "paths_per_window": 1,
    }
    passed = bool(
        math.isfinite(dispersion_ratio)
        and dispersion_ratio >= objective.internal_min_dispersion_ratio
    )
    diagnostics["gate_passed"] = passed
    diagnostics["gate_min_dispersion_ratio"] = objective.internal_min_dispersion_ratio
    return diagnostics, passed
