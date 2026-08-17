"""Training loop for the signature neural SDE.

Trains the conditional neural SDE against the truncated-signature MMD loss on
an internal FIT subset of training windows, monitoring the same loss on an
internal SELECTION subset (also training-period data).  External validation is
never touched here: the trainer only ever sees windows handed to it.

The training objective is the PRIMARY distributional loss only -- no direct
optimization of stylized-fact metrics.  Numerical regularization is limited to
AdamW weight decay and gradient-norm clipping, both documented.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

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
from neuralmarket.models.signature import augment_path, signature_mmd, truncated_signature_features


@dataclass(frozen=True)
class TrainingConfig:
    """Frozen training hyperparameters (never tuned on external validation)."""

    optimizer: str = "AdamW"
    learning_rate: float = 1e-3
    weight_decay: float = 1e-6
    batch_size: int = 64
    max_epochs: int = 400
    patience: int = 40
    grad_norm_clip: float = 1.0
    model_init_seed: int = 4242
    data_seed: int = 4243
    eval_seed: int = 4244
    fit_fraction: float = 0.8

    def config_hash(self) -> str:
        """Deterministic identity of the training config (no wall clock)."""
        return hashlib.sha256(canonical_dumps(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TrainingOutcome:
    """Recorded outcome of an internal training run (fit subset)."""

    initial_internal_loss: float
    best_internal_loss: float
    best_epoch: int
    final_epoch: int
    best_epoch_params: dict[str, list[float]]
    final_params: dict[str, list[float]]
    loss_curve: list[float]
    selection_curve: list[float]

    @property
    def percent_improvement(self) -> float:
        """Percent improvement of best over initial internal loss (positive is good)."""
        if self.initial_internal_loss == 0.0:
            return 0.0
        return 100.0 * (
            (self.initial_internal_loss - self.best_internal_loss) / abs(self.initial_internal_loss)
        )


def _param_snapshot(model: nn.Module) -> dict[str, list[float]]:
    return {
        name: [float(v) for v in param.detach().flatten().tolist()]
        for name, param in model.named_parameters()
    }


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
    ctx_tensor = torch.tensor(contexts, dtype=torch.float32)
    target_tensor = torch.tensor(targets, dtype=torch.float32)
    return ctx_tensor, target_tensor, ids


def evaluate_signature_loss(
    model: ConditionalNeuralSde,
    contexts: Tensor,
    targets: Tensor,
    cumret_scale: float,
    spec: WindowSpec,
    generator: torch.Generator,
) -> Tensor:
    """Mean truncated-signature MMD of one-shot generated vs real batches.

    Args:
        model: The neural SDE.
        contexts: Normalized context tensor ``(n, n_context)``.
        targets: Real target returns ``(n, horizon)``.
        cumret_scale: Training-derived cumulative-return channel scale.
        spec: Window geometry.
        generator: Noise generator for the generated paths.

    Returns:
        Scalar loss tensor (no grad through the model parameters).
    """
    noise = torch.randn(
        contexts.shape[0],
        spec.horizon,
        model.config.brownian_dim,
        dtype=contexts.dtype,
        device=contexts.device,
        generator=generator,
    )
    with torch.no_grad():
        generated = model(contexts, noise)
        real_features = truncated_signature_features(
            augment_path(targets, contexts, cumret_scale, spec), model.config.signature_level
        )
        gen_features = truncated_signature_features(
            augment_path(generated, contexts, cumret_scale, spec), model.config.signature_level
        )
        return signature_mmd(real_features, gen_features)


def train_internal(
    model: ConditionalNeuralSde,
    config: TrainingConfig,
    split: FitSelectionSplit,
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    spec: WindowSpec | None = None,
) -> TrainingOutcome:
    """Run internal fit/selection training on training-period windows only.

    Args:
        model: The conditional neural SDE (initialized deterministically by the
            caller from the frozen model-init seed policy).
        config: Frozen training settings.
        split: Internal chronological fit/selection split.
        normalizer: Training-fitted context normalizer.
        training_returns: Training log-return tensor used only for the
            cumulative-return channel scale (training-derived, never validation).
        spec: Window geometry.

    Returns:
        The recorded training outcome.

    Raises:
        RuntimeError: If training does not improve on the internal selection
            loss, or on any non-finite loss/gradient/parameter.
    """
    spec = WindowSpec() if spec is None else spec
    cfg = model.config
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

    def selection_loss() -> Tensor:
        return evaluate_signature_loss(model, sel_ctx, sel_targets, cumret_scale, spec, noise_gen)

    initial_loss = float(selection_loss().item())
    best_loss = initial_loss
    best_epoch = 0
    best_params = _param_snapshot(model)
    epochs_without_improvement = 0

    loss_curve: list[float] = []
    selection_curve: list[float] = [initial_loss]
    n_fit = fit_ctx.shape[0]
    n_batches = max(1, (n_fit + config.batch_size - 1) // config.batch_size)

    for epoch in range(1, config.max_epochs + 1):
        # Fixed deterministic data order per run (seeded permutation).
        order = torch.randperm(n_fit, generator=order_gen)
        epoch_loss = 0.0
        for start in range(0, n_fit, config.batch_size):
            idx = order[start : start + config.batch_size]
            batch_ctx = fit_ctx[idx]
            batch_targets = fit_targets[idx]
            noise = torch.randn(
                batch_ctx.shape[0],
                spec.horizon,
                cfg.brownian_dim,
                dtype=batch_ctx.dtype,
                device=batch_ctx.device,
                generator=noise_gen,
            )
            generated = model(batch_ctx, noise)
            real_features = truncated_signature_features(
                augment_path(batch_targets, batch_ctx, cumret_scale, spec),
                cfg.signature_level,
            )
            gen_features = truncated_signature_features(
                augment_path(generated, batch_ctx, cumret_scale, spec),
                cfg.signature_level,
            )
            loss = signature_mmd(real_features, gen_features)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite signature loss during training")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()  # type: ignore[no-untyped-call]
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), config.grad_norm_clip)
            if not torch.isfinite(torch.as_tensor(grad_norm)):
                raise RuntimeError("non-finite gradient norm during training")
            for param in model.parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError("non-finite gradient during training")
            optimizer.step()
            for param in model.parameters():
                if not torch.isfinite(param).all():
                    raise RuntimeError("non-finite parameters after optimizer step")
            epoch_loss += float(loss.item())

        loss_curve.append(epoch_loss / n_batches)
        sel = float(selection_loss().item())
        selection_curve.append(sel)
        if not math.isfinite(sel):
            raise RuntimeError("non-finite internal-selection loss")
        if sel < best_loss:
            best_loss = sel
            best_epoch = epoch
            best_params = _param_snapshot(model)
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                break

    if best_epoch == 0 or best_loss >= initial_loss:
        raise RuntimeError(
            "NO LEARNING: best internal signature loss did not improve on initial loss "
            f"(initial={initial_loss:.6e}, best={best_loss:.6e})"
        )

    state = model.state_dict()
    for name, values in best_params.items():
        state[name].copy_(torch.tensor(values, dtype=state[name].dtype).reshape(state[name].shape))
    model.load_state_dict(state)

    return TrainingOutcome(
        initial_internal_loss=initial_loss,
        best_internal_loss=best_loss,
        best_epoch=best_epoch,
        final_epoch=epoch,
        best_epoch_params=best_params,
        final_params=_param_snapshot(model),
        loss_curve=loss_curve,
        selection_curve=selection_curve,
    )


def refit_final(
    model: ConditionalNeuralSde,
    config: TrainingConfig,
    windows: Sequence[object],
    normalizer: FeatureNormalizer,
    training_returns: Tensor,
    epochs: int,
    spec: WindowSpec | None = None,
) -> dict[str, list[float]]:
    """Refit on ALL eligible training windows for exactly ``epochs`` epochs.

    Args:
        model: A freshly reinitialized model (same model-init policy).
        config: Frozen training settings (seeds, optimizer, batching).
        windows: All eligible training windows.
        normalizer: Training-fitted context normalizer.
        training_returns: Training returns (for the scale only).
        epochs: The frozen best epoch count from the internal run.
        spec: Window geometry.

    Returns:
        Final parameter snapshot.

    Raises:
        RuntimeError: On any non-finite loss/gradient/parameter.
    """
    spec = WindowSpec() if spec is None else spec
    cfg = model.config
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
                cfg.brownian_dim,
                dtype=batch_ctx.dtype,
                device=batch_ctx.device,
                generator=noise_gen,
            )
            generated = model(batch_ctx, noise)
            real_features = truncated_signature_features(
                augment_path(batch_targets, batch_ctx, cumret_scale, spec),
                cfg.signature_level,
            )
            gen_features = truncated_signature_features(
                augment_path(generated, batch_ctx, cumret_scale, spec),
                cfg.signature_level,
            )
            loss = signature_mmd(real_features, gen_features)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite signature loss during final refit")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()  # type: ignore[no-untyped-call]
            grad_norm = nn.utils.clip_grad_norm_(model.parameters(), config.grad_norm_clip)
            if not torch.isfinite(torch.as_tensor(grad_norm)):
                raise RuntimeError("non-finite gradient norm during final refit")
            for param in model.parameters():
                if param.grad is not None and not torch.isfinite(param.grad).all():
                    raise RuntimeError("non-finite gradient during final refit")
            optimizer.step()
            for param in model.parameters():
                if not torch.isfinite(param).all():
                    raise RuntimeError("non-finite parameters after optimizer step")
    return _param_snapshot(model)
