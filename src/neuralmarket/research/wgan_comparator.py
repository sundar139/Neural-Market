"""Frozen WGAN-GP training, selection, and H2 metric boundaries.

All functions operate on caller-provided tensors or frozen training-window
objects.  No function in this module loads validation/final-test data, writes a
scientific checkpoint, or computes an H2 status.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from statistics import stdev
from typing import Any

import numpy as np
import torch
from torch import Tensor

from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.sde_windows import (
    FeatureNormalizer,
    FitSelectionSplit,
    WindowSpec,
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
)
from neuralmarket.models.wgan_cde import (
    CONTEXT_DIM,
    DT,
    HORIZON,
    LATENT_DIM,
    WGANCritic,
    WGANGenerator,
)

WGAN_PREREGISTRATION_SHA256 = (
    "6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037"
)
WGAN_PREREGISTRATION_BLOB = "72311888542ee83ff497b5f0adbbaf6429e8452a"
AMENDMENT_060_SHA256 = "2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c"
AMENDMENT_060_BLOB = "a1ba052abe8b4a50887ec84b934e16a328e60596"
WGAN_PRIMARY_MEMBER_IDS = tuple(f"wgan-seed-0{i}" for i in range(1, 6))
WGAN_RESERVE_MEMBER_IDS = ("reserve-wgan-j01", "reserve-wgan-j02", "reserve-wgan-j03")
REASON_TAXONOMY = (
    "NONFINITE_TRAINING_OR_SELECTION",
    "MISSING_VALID_CHECKPOINT",
    "GOVERNANCE_INVALID",
    "OTHER_FROZEN_FAILURE",
    "NONE",
)


def _require_finite(name: str, value: Tensor) -> None:
    if not torch.isfinite(value).all():
        raise ValueError(f"{name} must be finite")


def _require_scores(name: str, value: Tensor) -> None:
    if value.ndim != 1:
        raise ValueError(f"{name} must have shape (batch,)")
    _require_finite(name, value)


@dataclass(frozen=True)
class WGANTrainingConfig:
    """Singleton WGAN-GP configuration frozen by the preregistration."""

    optimizer: str = "Adam"
    learning_rate: float = 1e-4
    betas: tuple[float, float] = (0.0, 0.9)
    eps: float = 1e-8
    weight_decay: float = 0.0
    gradient_clipping: bool = False
    lambda_gp: float = 10.0
    critic_generator_update_ratio: int = 5
    batch_size: int = 64
    max_generator_epochs: int = 400
    patience_generator_epochs: int = 40
    min_delta: float = 0.0
    fit_fraction: float = 0.8
    selection_paths: int = 1024
    real_reference_paths: int = 1024
    bootstrap_seed: int = 8801
    block_length: int = 22
    eval_seed: int = 8283
    dt: float = DT
    horizon: int = HORIZON
    context_lookback: int = 22
    latent_dim: int = LATENT_DIM
    replicate_seed: int = 8281
    model_init_seed: int = 8281
    data_seed: int = 8282

    def config_hash(self) -> str:
        """Return the deterministic effective WGAN configuration hash."""
        return hashlib.sha256(canonical_dumps(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CheckpointCandidate:
    """Identity and selection values for one candidate checkpoint."""

    identity: str
    epoch: int
    metric: float


@dataclass
class EarlyStoppingState:
    """Strict lower-is-better early-stopping state with frozen tie behavior."""

    patience: int
    min_delta: float
    best_metric: float | None = None
    best_epoch: int | None = None
    bad_epochs: int = 0

    def consider(self, *, epoch: int, metric: float) -> bool:
        """Record a strict improvement and return whether a new checkpoint wins."""
        if not math.isfinite(metric):
            raise ValueError("selection metric must be finite")
        if self.best_metric is None or metric < self.best_metric - self.min_delta:
            self.best_metric = metric
            self.best_epoch = epoch
            self.bad_epochs = 0
            return True
        self.bad_epochs += 1
        return False

    @property
    def should_stop(self) -> bool:
        """Whether patience has been exhausted."""
        return self.bad_epochs >= self.patience


def select_checkpoint(candidates: Sequence[CheckpointCandidate]) -> CheckpointCandidate:
    """Select metric, earliest epoch, then lexical identity."""
    if not candidates:
        raise ValueError("at least one checkpoint candidate is required")
    for candidate in candidates:
        if candidate.epoch < 1 or not math.isfinite(candidate.metric):
            raise ValueError("checkpoint candidates must have positive finite values")
    return min(candidates, key=lambda item: (item.metric, item.epoch, item.identity))


def critic_wgan_gp_loss(
    real_scores: Tensor,
    fake_scores: Tensor,
    gradient_penalty_value: Tensor,
    *,
    lambda_gp: float = 10.0,
) -> Tensor:
    """Return the minimization-form critic WGAN-GP loss."""
    _require_scores("real_scores", real_scores)
    _require_scores("fake_scores", fake_scores)
    if gradient_penalty_value.ndim != 0 or not torch.isfinite(gradient_penalty_value):
        raise ValueError("gradient_penalty_value must be one finite scalar")
    if not math.isfinite(lambda_gp) or lambda_gp < 0.0:
        raise ValueError("lambda_gp must be finite and non-negative")
    result = fake_scores.mean() - real_scores.mean() + float(lambda_gp) * gradient_penalty_value
    _require_finite("critic loss", result.reshape(1))
    return result


def generator_wgan_loss(fake_scores: Tensor) -> Tensor:
    """Return the minimization-form generator WGAN loss ``-mean(D(fake))``."""
    _require_scores("fake_scores", fake_scores)
    result = -fake_scores.mean()
    _require_finite("generator loss", result.reshape(1))
    return result


def gradient_penalty(
    critic: WGANCritic,
    real_paths: Tensor,
    fake_paths: Tensor,
    context: Tensor,
    *,
    cumulative_return_scale: float,
    generator: torch.Generator | None = None,
) -> Tensor:
    """Compute WGAN-GP on uniformly interpolated full path inputs."""
    if real_paths.shape != fake_paths.shape:
        raise ValueError("real_paths and fake_paths must have identical shapes")
    if real_paths.ndim != 2 or real_paths.shape[1] != HORIZON:
        raise ValueError(f"paths must have shape (batch, {HORIZON})")
    if context.ndim != 2 or context.shape != (real_paths.shape[0], CONTEXT_DIM):
        raise ValueError(f"context must have shape (batch, {CONTEXT_DIM})")
    _require_finite("real_paths", real_paths)
    _require_finite("fake_paths", fake_paths)
    _require_finite("context", context)
    alpha = torch.rand(
        real_paths.shape[0],
        1,
        device=real_paths.device,
        dtype=real_paths.dtype,
        generator=generator,
    )
    interpolated = (alpha * real_paths + (1.0 - alpha) * fake_paths).requires_grad_(True)
    scores = critic(interpolated, context, cumulative_return_scale)
    gradients = torch.clone(torch.autograd.grad(
        outputs=scores,
        inputs=interpolated,
        grad_outputs=torch.ones_like(scores),
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0])
    norms = gradients.reshape(gradients.shape[0], -1).norm(2, dim=1)
    result: Tensor = ((norms - 1.0) ** 2).mean()
    _require_finite("gradient penalty", result.reshape(1))
    return result


def non_scientific_cpu_smoke(seed: int = 109) -> dict[str, Any]:
    """Exercise model/loss boundaries on tiny synthetic CPU tensors only."""
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        generator_model = WGANGenerator()
        critic_model = WGANCritic(cumulative_return_scale=1.0)
        context = torch.randn(2, CONTEXT_DIM)
        static_latent = torch.randn(2, LATENT_DIM)
        temporal_noise = torch.randn(2, HORIZON, 2)
        real_paths = torch.randn(2, HORIZON)
        fake_paths = generator_model(context, static_latent, temporal_noise)
        real_scores = critic_model(real_paths, context)
        fake_scores = critic_model(fake_paths.detach(), context)
        penalty = gradient_penalty(
            critic_model,
            real_paths,
            fake_paths.detach(),
            context,
            cumulative_return_scale=1.0,
        )
        critic_loss = critic_wgan_gp_loss(real_scores, fake_scores, penalty)
        generator_loss = generator_wgan_loss(critic_model(fake_paths, context))
    return {
        "classification": "NON_SCIENTIFIC_TEST_ONLY",
        "generator_shape": tuple(fake_paths.shape),
        "critic_shape": tuple(fake_scores.shape),
        "critic_loss_finite": bool(torch.isfinite(critic_loss)),
        "generator_loss_finite": bool(torch.isfinite(generator_loss)),
        "gradient_penalty_finite": bool(torch.isfinite(penalty)),
    }


def normalized_terminal_wasserstein(fake_terminal: Tensor, real_terminal: Tensor) -> float:
    """Compute Gate-compatible normalized one-dimensional Wasserstein distance."""
    if fake_terminal.ndim != 1 or real_terminal.ndim != 1:
        raise ValueError("terminal values must be one-dimensional")
    _require_finite("fake_terminal", fake_terminal)
    _require_finite("real_terminal", real_terminal)
    real = real_terminal.detach().cpu().numpy()
    fake = fake_terminal.detach().cpu().numpy()
    if len(real) == 0 or len(fake) == 0:
        raise ValueError("terminal values must be non-empty")
    from neuralmarket.research.neural_sde_internal_gate import _wasserstein_1d

    distance = _wasserstein_1d(fake, real)
    scale = float(np.std(real))
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("real terminal standard deviation must be positive and finite")
    return distance / scale


@dataclass(frozen=True)
class PreparedWGANData:
    """Training-only tensors and provenance for a future authorized run."""

    split: FitSelectionSplit
    normalizer: FeatureNormalizer
    cumulative_return_scale: float
    fit_context: Tensor
    fit_targets: Tensor
    selection_context: Tensor
    selection_targets: Tensor
    all_context: Tensor
    all_targets: Tensor
    selection_daily_returns: np.ndarray
    training_returns: np.ndarray
    spec: WindowSpec


def prepare_wgan_training_data(
    training_returns: np.ndarray,
    return_dates: Sequence[str],
    *,
    fit_fraction: float = 0.8,
    spec: WindowSpec | None = None,
    device: torch.device | str = "cpu",
) -> PreparedWGANData:
    """Prepare only the frozen training and internal-selection windows."""
    spec = WindowSpec() if spec is None else spec
    returns = np.asarray(training_returns, dtype=np.float64)
    if returns.ndim != 1 or returns.size == 0 or not np.isfinite(returns).all():
        raise ValueError("training_returns must be a finite non-empty one-dimensional array")
    windows = build_windows(returns, return_dates, spec)
    split = _split_windows(windows, fit_fraction, spec)
    fit_features = np.stack(
        [compute_context_features(window, spec).array() for window in split.fit_windows], axis=0
    )
    normalizer = fit_feature_normalizer(fit_features)
    scale = fit_cumret_scale(returns, spec.horizon)
    fit_context, fit_targets = _window_tensors(split.fit_windows, normalizer, spec)
    selection_context, selection_targets = _window_tensors(
        split.selection_windows, normalizer, spec
    )
    all_context, all_targets = _window_tensors(windows, normalizer, spec)
    resolved = torch.device(device)
    return PreparedWGANData(
        split=split,
        normalizer=normalizer,
        cumulative_return_scale=scale,
        fit_context=fit_context.to(resolved),
        fit_targets=fit_targets.to(resolved),
        selection_context=selection_context.to(resolved),
        selection_targets=selection_targets.to(resolved),
        all_context=all_context.to(resolved),
        all_targets=all_targets.to(resolved),
        selection_daily_returns=returns[split.selection_target_start_index :].copy(),
        training_returns=returns.copy(),
        spec=spec,
    )


def _split_windows(
    windows: Sequence[Any], fit_fraction: float, spec: WindowSpec
) -> FitSelectionSplit:
    """Import the established split helper without exposing a duplicate policy."""
    from neuralmarket.data.research.sde_windows import split_fit_selection

    return split_fit_selection(windows, fit_fraction, spec)


def _window_tensors(
    windows: Sequence[Any], normalizer: FeatureNormalizer, spec: WindowSpec
) -> tuple[Tensor, Tensor]:
    contexts: list[list[float]] = []
    targets: list[list[float]] = []
    for window in windows:
        context = normalizer.normalize(compute_context_features(window, spec).array())
        contexts.append([float(value) for value in context])
        targets.append([float(value) for value in window.target_returns])
    return torch.tensor(contexts, dtype=torch.float32), torch.tensor(targets, dtype=torch.float32)


def _draw_noise(
    batch_size: int, device: torch.device, generator: torch.Generator
) -> tuple[Tensor, Tensor]:
    static = torch.randn(batch_size, LATENT_DIM, device=device, generator=generator)
    temporal = torch.randn(batch_size, HORIZON, 2, device=device, generator=generator)
    return static, temporal


def _check_parameters_finite(*modules: torch.nn.Module) -> None:
    for module in modules:
        for parameter in module.parameters():
            if not torch.isfinite(parameter).all():
                raise RuntimeError("non-finite model parameter")
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                raise RuntimeError("non-finite model gradient")


def _selection_metric(
    generator_model: WGANGenerator,
    selection_context: Tensor,
    selection_daily_returns: np.ndarray,
    *,
    cumulative_return_scale: float,
    config: WGANTrainingConfig,
) -> float:
    """Evaluate the frozen internal-selection terminal Wasserstein metric."""
    device = selection_context.device
    gen = torch.Generator(device=device)
    gen.manual_seed(config.data_seed)
    n = config.selection_paths
    context = selection_context.repeat(
        (n + len(selection_context) - 1) // len(selection_context), 1
    )[:n]
    static, temporal = _draw_noise(n, device, gen)
    with torch.no_grad():
        generated = generator_model(context, static, temporal)
    real_bootstrap = _circular_block_bootstrap(
        selection_daily_returns,
        config.real_reference_paths,
        HORIZON,
        block_length=config.block_length,
        seed=config.bootstrap_seed,
    )
    real_terminal = torch.tensor(real_bootstrap.sum(axis=1), dtype=generated.dtype, device=device)
    fake_terminal = generated.sum(dim=1)
    return normalized_terminal_wasserstein(
        fake_terminal,
        real_terminal,
    )


def _circular_block_bootstrap(
    returns: np.ndarray,
    n_paths: int,
    horizon: int,
    *,
    block_length: int,
    seed: int,
) -> np.ndarray:
    """Use the established block-bootstrap helper for the Gate reference."""
    from neuralmarket.baselines.bootstrap import sample_block_bootstrap

    result = sample_block_bootstrap(
        returns,
        n_paths,
        horizon,
        block_length=block_length,
        seed=seed,
    )
    if not np.isfinite(result).all():
        raise RuntimeError("non-finite internal-selection bootstrap reference")
    return result


@dataclass(frozen=True)
class WGANTrainingOutcome:
    """In-memory result of a future authorized internal WGAN training run."""

    best_generator_epoch: int
    best_selection_metric: float
    final_generator_epoch: int
    critic_loss_curve: tuple[float, ...]
    generator_loss_curve: tuple[float, ...]
    gradient_penalty_curve: tuple[float, ...]
    selection_metric_curve: tuple[float, ...]
    best_generator_state: dict[str, Tensor] = field(repr=False)
    best_critic_state: dict[str, Tensor] = field(repr=False)


def train_wgan_internal(
    data: PreparedWGANData,
    *,
    config: WGANTrainingConfig | None = None,
    generator_model: WGANGenerator | None = None,
    critic_model: WGANCritic | None = None,
    device: torch.device | str | None = None,
) -> WGANTrainingOutcome:
    """Train the frozen WGAN contract on fit windows with internal selection only."""
    config = WGANTrainingConfig() if config is None else config
    resolved = data.fit_context.device if device is None else torch.device(device)
    if resolved.type != "cuda":
        raise RuntimeError("scientific WGAN training requires CUDA; CPU is smoke-only")
    generator_model = WGANGenerator(dt=config.dt) if generator_model is None else generator_model
    critic_model = (
        WGANCritic(cumulative_return_scale=data.cumulative_return_scale, dt=config.dt)
        if critic_model is None
        else critic_model
    )
    generator_model.to(resolved)
    critic_model.to(resolved)
    generator_model.train()
    critic_model.train()
    critic_optimizer = torch.optim.Adam(
        critic_model.parameters(),
        lr=config.learning_rate,
        betas=config.betas,
        eps=config.eps,
        weight_decay=config.weight_decay,
    )
    generator_optimizer = torch.optim.Adam(
        generator_model.parameters(),
        lr=config.learning_rate,
        betas=config.betas,
        eps=config.eps,
        weight_decay=config.weight_decay,
    )
    data_generator = torch.Generator(device=resolved)
    data_generator.manual_seed(config.bootstrap_seed)
    order_generator = torch.Generator(device=resolved)
    order_generator.manual_seed(config.bootstrap_seed)
    tracker = EarlyStoppingState(config.patience_generator_epochs, config.min_delta)
    critic_curve: list[float] = []
    generator_curve: list[float] = []
    penalty_curve: list[float] = []
    metric_curve: list[float] = []
    best_generator_state: dict[str, Tensor] | None = None
    best_critic_state: dict[str, Tensor] | None = None
    n_fit = data.fit_context.shape[0]
    for epoch in range(1, config.max_generator_epochs + 1):
        order = torch.randperm(n_fit, generator=order_generator, device=resolved)
        epoch_critic = 0.0
        epoch_generator = 0.0
        epoch_penalty = 0.0
        n_batches = 0
        for start in range(0, n_fit, config.batch_size):
            index = order[start : start + config.batch_size]
            real_paths = data.fit_targets[index]
            context = data.fit_context[index]
            for _ in range(config.critic_generator_update_ratio):
                static, temporal = _draw_noise(len(index), resolved, data_generator)
                fake_paths = generator_model(context, static, temporal).detach()
                real_scores = critic_model(real_paths, context)
                fake_scores = critic_model(fake_paths, context)
                penalty = gradient_penalty(
                    critic_model,
                    real_paths,
                    fake_paths,
                    context,
                    cumulative_return_scale=data.cumulative_return_scale,
                    generator=data_generator,
                )
                loss = critic_wgan_gp_loss(
                    real_scores, fake_scores, penalty, lambda_gp=config.lambda_gp
                )
                critic_optimizer.zero_grad(set_to_none=True)
                loss.backward()  # type: ignore[no-untyped-call]
                critic_optimizer.step()
                _check_parameters_finite(critic_model)
                epoch_critic += float(loss.detach().item())
                epoch_penalty += float(penalty.detach().item())
            static, temporal = _draw_noise(len(index), resolved, data_generator)
            fake_paths = generator_model(context, static, temporal)
            generator_loss = generator_wgan_loss(critic_model(fake_paths, context))
            generator_optimizer.zero_grad(set_to_none=True)
            generator_loss.backward()  # type: ignore[no-untyped-call]
            generator_optimizer.step()
            _check_parameters_finite(generator_model)
            epoch_generator += float(generator_loss.detach().item())
            n_batches += 1
        metric = _selection_metric(
            generator_model,
            data.selection_context,
            data.selection_daily_returns,
            cumulative_return_scale=data.cumulative_return_scale,
            config=config,
        )
        metric_curve.append(metric)
        critic_curve.append(epoch_critic / max(1, n_batches))
        generator_curve.append(epoch_generator / max(1, n_batches))
        penalty_curve.append(
            epoch_penalty / max(1, n_batches * config.critic_generator_update_ratio)
        )
        if tracker.consider(epoch=epoch, metric=metric):
            best_generator_state = {
                key: value.detach().clone() for key, value in generator_model.state_dict().items()
            }
            best_critic_state = {
                key: value.detach().clone() for key, value in critic_model.state_dict().items()
            }
        if tracker.should_stop:
            break
    if (
        tracker.best_epoch is None
        or tracker.best_metric is None
        or best_generator_state is None
        or best_critic_state is None
    ):
        raise RuntimeError("NO_VALID_CHECKPOINT: no finite improving WGAN selection metric")
    return WGANTrainingOutcome(
        best_generator_epoch=tracker.best_epoch,
        best_selection_metric=tracker.best_metric,
        final_generator_epoch=len(metric_curve),
        critic_loss_curve=tuple(critic_curve),
        generator_loss_curve=tuple(generator_curve),
        gradient_penalty_curve=tuple(penalty_curve),
        selection_metric_curve=tuple(metric_curve),
        best_generator_state=best_generator_state,
        best_critic_state=best_critic_state,
    )


def refit_wgan(
    data: PreparedWGANData,
    *,
    epochs: int,
    config: WGANTrainingConfig | None = None,
    generator_model: WGANGenerator | None = None,
    critic_model: WGANCritic | None = None,
    device: torch.device | str | None = None,
) -> tuple[WGANGenerator, WGANCritic]:
    """Future-only exact-epoch refit on all eligible training windows."""
    if epochs < 1:
        raise ValueError("epochs must be positive")
    config = WGANTrainingConfig() if config is None else config
    resolved = data.fit_context.device if device is None else torch.device(device)
    if resolved.type != "cuda":
        raise RuntimeError("scientific WGAN refit requires CUDA; CPU is smoke-only")
    generator_model = WGANGenerator(dt=config.dt) if generator_model is None else generator_model
    critic_model = (
        WGANCritic(cumulative_return_scale=data.cumulative_return_scale, dt=config.dt)
        if critic_model is None
        else critic_model
    )
    generator_model.to(resolved).train()
    critic_model.to(resolved).train()
    critic_optimizer = torch.optim.Adam(
        critic_model.parameters(), lr=config.learning_rate, betas=config.betas,
        eps=config.eps, weight_decay=config.weight_decay,
    )
    generator_optimizer = torch.optim.Adam(
        generator_model.parameters(), lr=config.learning_rate, betas=config.betas,
        eps=config.eps, weight_decay=config.weight_decay,
    )
    noise_generator = torch.Generator(device=resolved)
    noise_generator.manual_seed(config.bootstrap_seed)
    order_generator = torch.Generator(device=resolved)
    order_generator.manual_seed(config.bootstrap_seed)
    n_fit = data.all_context.shape[0]
    for _ in range(epochs):
        order = torch.randperm(n_fit, generator=order_generator, device=resolved)
        for start in range(0, n_fit, config.batch_size):
            index = order[start : start + config.batch_size]
            real_paths = data.all_targets[index]
            context = data.all_context[index]
            for _ in range(config.critic_generator_update_ratio):
                static, temporal = _draw_noise(len(index), resolved, noise_generator)
                fake = generator_model(context, static, temporal).detach()
                real_score = critic_model(real_paths, context)
                fake_score = critic_model(fake, context)
                penalty = gradient_penalty(
                    critic_model, real_paths, fake, context,
                    cumulative_return_scale=data.cumulative_return_scale,
                    generator=noise_generator,
                )
                loss = critic_wgan_gp_loss(
                    real_score, fake_score, penalty, lambda_gp=config.lambda_gp
                )
                critic_optimizer.zero_grad(set_to_none=True)
                loss.backward()  # type: ignore[no-untyped-call]
                critic_optimizer.step()
                _check_parameters_finite(critic_model)
            static, temporal = _draw_noise(len(index), resolved, noise_generator)
            fake = generator_model(context, static, temporal)
            loss = generator_wgan_loss(critic_model(fake, context))
            generator_optimizer.zero_grad(set_to_none=True)
            loss.backward()  # type: ignore[no-untyped-call]
            generator_optimizer.step()
            _check_parameters_finite(generator_model)
    return generator_model, critic_model


@dataclass(frozen=True)
class AttemptOutcome:
    """Governance-preserving outcome for one primary or reserve identity."""

    member_id: str
    role: str
    status: str
    valid_checkpoint: bool
    nonfinite_training_or_selection: bool = False
    best_generator_epoch: int | None = None
    checkpoint_selection_metric: float | None = None
    reason: str | None = None


def _metric_provenance() -> dict[str, str]:
    return {
        "preregistration_sha256": WGAN_PREREGISTRATION_SHA256,
        "amendment_060_sha256": AMENDMENT_060_SHA256,
    }


def _require_primary_outcomes(outcomes: Sequence[AttemptOutcome]) -> list[AttemptOutcome]:
    primary = [item for item in outcomes if item.role == "PRIMARY"]
    if len(primary) != 5 or {item.member_id for item in primary} != set(WGAN_PRIMARY_MEMBER_IDS):
        raise ValueError("metrics require exactly the five WGAN primary outcomes")
    if len({item.member_id for item in primary}) != 5:
        raise ValueError("primary member identities must be unique")
    return sorted(primary, key=lambda item: WGAN_PRIMARY_MEMBER_IDS.index(item.member_id))


def compute_attempt_metrics(outcomes: Sequence[AttemptOutcome]) -> dict[str, Any]:
    """Serialize both Amendment-060 attempt-level metrics over denominator five."""
    primary = _require_primary_outcomes(outcomes)
    valid_statuses = {"GATE_PASS_VALID", "GATE_FAIL_VALID"}
    fraction_numerator = sum(item.status in valid_statuses for item in primary)
    attempt_entries: list[dict[str, Any]] = []
    for item in primary:
        if item.status == "GOVERNANCE_INVALID":
            indicator, reason = 1, "GOVERNANCE_INVALID"
        elif item.nonfinite_training_or_selection:
            indicator, reason = 1, "NONFINITE_TRAINING_OR_SELECTION"
        elif not item.valid_checkpoint:
            indicator, reason = 1, "MISSING_VALID_CHECKPOINT"
        elif item.reason is not None and item.reason != "NONE":
            indicator, reason = 1, "OTHER_FROZEN_FAILURE"
        else:
            indicator, reason = 0, "NONE"
        if reason not in REASON_TAXONOMY:
            raise ValueError(f"unknown failure reason {reason!r}")
        attempt_entries.append(
            {
                "member_id": item.member_id,
                "role": item.role,
                "status": item.status,
                "indicator": indicator,
                "reason": reason,
                "valid_checkpoint": item.valid_checkpoint,
                "nonfinite_training_or_selection": item.nonfinite_training_or_selection,
            }
        )
    missing_numerator = sum(item["indicator"] for item in attempt_entries)
    return {
        "valid_completed_member_fraction": {
            **_metric_provenance(),
            "numerator": fraction_numerator,
            "denominator": 5,
            "value": fraction_numerator / 5.0,
        },
        "nonfinite_or_missing_checkpoint_rate": {
            **_metric_provenance(),
            "numerator": missing_numerator,
            "denominator": 5,
            "value": missing_numerator / 5.0,
            "attempts": attempt_entries,
        },
    }


def compute_completed_member_metrics(
    outcomes: Sequence[AttemptOutcome], *, max_generator_epochs: int = 400
) -> dict[str, Any]:
    """Compute completed-member sample SDs without imputing missing values."""
    if max_generator_epochs <= 0:
        raise ValueError("max_generator_epochs must be positive")
    valid_statuses = {"GATE_PASS_VALID", "GATE_FAIL_VALID"}
    completed = [
        item for item in outcomes
        if item.status in valid_statuses and item.valid_checkpoint
    ]
    members: list[dict[str, Any]] = []
    missing = False
    for item in completed:
        entry: dict[str, Any] = {
            "member_id": item.member_id,
            "role": item.role,
            "status": item.status,
            "best_generator_epoch": item.best_generator_epoch,
            "checkpoint_selection_metric": item.checkpoint_selection_metric,
        }
        if (
            item.best_generator_epoch is None
            or item.checkpoint_selection_metric is None
            or not math.isfinite(float(item.checkpoint_selection_metric))
        ):
            missing = True
        else:
            entry["normalized_best_checkpoint_epoch"] = (
                item.best_generator_epoch / max_generator_epochs
            )
            entry["checkpoint_selection_metric"] = float(item.checkpoint_selection_metric)
        members.append(entry)
    if missing or len(members) < 2:
        epoch_sd = metric_sd = None
    else:
        epoch_values = [float(item["normalized_best_checkpoint_epoch"]) for item in members]
        metric_values = [float(item["checkpoint_selection_metric"]) for item in members]
        epoch_sd = stdev(epoch_values)
        metric_sd = stdev(metric_values)
    return {
        "normalized_best_checkpoint_epoch_sd": epoch_sd,
        "checkpoint_selection_metric_sd": metric_sd,
        "members": members,
        "missingness": "NO_IMPUTATION" if missing or len(members) < 2 else "NONE",
        **_metric_provenance(),
    }


__all__ = [
    "AMENDMENT_060_SHA256",
    "WGAN_PREREGISTRATION_SHA256",
    "WGAN_PRIMARY_MEMBER_IDS",
    "AttemptOutcome",
    "CheckpointCandidate",
    "EarlyStoppingState",
    "PreparedWGANData",
    "WGANTrainingConfig",
    "WGANTrainingOutcome",
    "compute_attempt_metrics",
    "compute_completed_member_metrics",
    "critic_wgan_gp_loss",
    "generator_wgan_loss",
    "gradient_penalty",
    "non_scientific_cpu_smoke",
    "normalized_terminal_wasserstein",
    "prepare_wgan_training_data",
    "refit_wgan",
    "select_checkpoint",
    "train_wgan_internal",
]
