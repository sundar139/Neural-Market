"""Frozen conditional Neural-CDE-style WGAN generator and path critic.

This module contains only the model-side implementation.  It deliberately does
not load market data, create checkpoints, or invoke a scientific runner.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

import torch
from torch import Tensor, nn

CONTEXT_DIM = 4
LATENT_DIM = 32
HORIZON = 63
DT = 1.0 / 252.0
GENERATOR_CONTROL_DIM = 3
CRITIC_CONTROL_DIM = 6
HIDDEN_DIM = 64


@dataclass(frozen=True)
class GeneratorNoise:
    """Independent static and temporal standard-normal generator noise."""

    static_latent: Tensor
    temporal_noise: Tensor


def _mlp(in_dim: int, out_dim: int, hidden_dim: int = HIDDEN_DIM) -> nn.Sequential:
    """Build the frozen two-hidden-layer SiLU MLP pattern."""
    return nn.Sequential(
        nn.Linear(in_dim, hidden_dim),
        nn.SiLU(),
        nn.Linear(hidden_dim, hidden_dim),
        nn.SiLU(),
        nn.Linear(hidden_dim, out_dim),
    )


def _require_finite(name: str, value: Tensor) -> None:
    """Reject non-finite tensors at a public model boundary."""
    if not torch.isfinite(value).all():
        raise ValueError(f"{name} must be finite")


def _require_context(context: Tensor) -> None:
    if context.ndim != 2 or context.shape[1] != CONTEXT_DIM:
        raise ValueError(f"context must have shape (batch, {CONTEXT_DIM})")
    _require_finite("context", context)


def _require_latent(static_latent: Tensor, batch_size: int) -> None:
    if static_latent.ndim != 2 or static_latent.shape != (batch_size, LATENT_DIM):
        raise ValueError(f"static_latent must have shape (batch, {LATENT_DIM})")
    _require_finite("static_latent", static_latent)


def _require_temporal_noise(temporal_noise: Tensor, batch_size: int) -> None:
    if temporal_noise.ndim != 3 or temporal_noise.shape != (batch_size, HORIZON, 2):
        raise ValueError(f"temporal_noise must have shape (batch, {HORIZON}, 2)")
    _require_finite("temporal_noise", temporal_noise)


def build_generator_control_increments(temporal_noise: Tensor, dt: float = DT) -> Tensor:
    """Return ``[dt, sqrt(dt)*epsilon_1, sqrt(dt)*epsilon_2]`` per interval."""
    if temporal_noise.ndim != 3 or temporal_noise.shape[1:] != (HORIZON, 2):
        raise ValueError(f"temporal_noise must have shape (batch, {HORIZON}, 2)")
    _require_finite("temporal_noise", temporal_noise)
    if not math.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be positive and finite")
    time = torch.full(
        (temporal_noise.shape[0], HORIZON, 1),
        float(dt),
        dtype=temporal_noise.dtype,
        device=temporal_noise.device,
    )
    controls = torch.cat((time, temporal_noise * math.sqrt(dt)), dim=-1)
    _require_finite("generator control increments", controls)
    return controls


def build_critic_control_path(
    paths: Tensor,
    context: Tensor,
    cumulative_return_scale: float,
) -> Tensor:
    """Build control points ``[normalized_time, scaled_cumulative_return, context]``."""
    if paths.ndim != 2 or paths.shape[1] != HORIZON:
        raise ValueError(f"paths must have shape (batch, {HORIZON})")
    _require_context(context)
    if paths.shape[0] != context.shape[0]:
        raise ValueError("paths and context must share the batch dimension")
    _require_finite("paths", paths)
    if not math.isfinite(cumulative_return_scale) or cumulative_return_scale <= 0.0:
        raise ValueError("cumulative_return_scale must be positive and finite")
    time = torch.linspace(
        0.0,
        1.0,
        HORIZON + 1,
        dtype=paths.dtype,
        device=paths.device,
    ).view(1, HORIZON + 1, 1).expand(paths.shape[0], -1, -1)
    cumulative = torch.cat(
        (
            torch.zeros(paths.shape[0], 1, dtype=paths.dtype, device=paths.device),
            paths.cumsum(dim=1),
        ),
        dim=1,
    ).unsqueeze(-1) / float(cumulative_return_scale)
    context_points = context.unsqueeze(1).expand(-1, HORIZON + 1, -1)
    controls = torch.cat((time, cumulative, context_points), dim=-1)
    _require_finite("critic control path", controls)
    return controls


def build_critic_control_increments(
    paths: Tensor,
    context: Tensor,
    cumulative_return_scale: float,
) -> Tensor:
    """Return fixed-grid increments of the six-channel critic control path."""
    points = build_critic_control_path(paths, context, cumulative_return_scale)
    increments = points[:, 1:, :] - points[:, :-1, :]
    _require_finite("critic control increments", increments)
    return increments


def sample_generator_noise(
    batch_size: int,
    seed: int,
    *,
    device: torch.device | str = "cpu",
    dtype: torch.dtype = torch.float32,
) -> GeneratorNoise:
    """Sample reproducible static and temporal standard-normal noise."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    resolved = torch.device(device)
    generator = torch.Generator(device=resolved)
    generator.manual_seed(seed)
    static = torch.randn(batch_size, LATENT_DIM, device=resolved, dtype=dtype, generator=generator)
    temporal = torch.randn(
        batch_size, HORIZON, 2, device=resolved, dtype=dtype, generator=generator
    )
    return GeneratorNoise(static_latent=static, temporal_noise=temporal)


class WGANGenerator(nn.Module):
    """Conditional 64-state Neural-CDE-style generator with Euler updates."""

    def __init__(self, *, dt: float = DT) -> None:
        """Initialize the fixed generator architecture."""
        super().__init__()
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be positive and finite")
        self.dt = float(dt)
        self.initial_state = _mlp(CONTEXT_DIM + LATENT_DIM, HIDDEN_DIM)
        self.vector_field = _mlp(HIDDEN_DIM, HIDDEN_DIM * GENERATOR_CONTROL_DIM)
        self.readout = _mlp(HIDDEN_DIM + CONTEXT_DIM, 1)

    def forward(self, context: Tensor, static_latent: Tensor, temporal_noise: Tensor) -> Tensor:
        """Generate a finite ``(batch, 63)`` raw daily-log-return path."""
        _require_context(context)
        batch_size = context.shape[0]
        _require_latent(static_latent, batch_size)
        _require_temporal_noise(temporal_noise, batch_size)
        if static_latent.device != context.device or temporal_noise.device != context.device:
            raise ValueError("context, static_latent, and temporal_noise must share a device")
        hidden = self.initial_state(torch.cat((context, static_latent), dim=-1))
        _require_finite("generator initial state", hidden)
        controls = build_generator_control_increments(temporal_noise, self.dt)
        increments: list[Tensor] = []
        for interval in range(HORIZON):
            vector_field = self.vector_field(hidden).reshape(
                batch_size, HIDDEN_DIM, GENERATOR_CONTROL_DIM
            )
            update = (vector_field * controls[:, interval, :].unsqueeze(1)).sum(dim=-1)
            hidden = hidden + update
            _require_finite("generator hidden state", hidden)
            output = self.readout(torch.cat((hidden, context), dim=-1)).squeeze(-1)
            _require_finite("generator output", output)
            increments.append(output.unsqueeze(1))
        result = torch.cat(increments, dim=1)
        _require_finite("generator path", result)
        return result


class WGANCritic(nn.Module):
    """Conditional path critic with a scalar linear terminal readout."""

    def __init__(self, *, cumulative_return_scale: float, dt: float = DT) -> None:
        """Initialize the fixed six-control-channel critic architecture."""
        super().__init__()
        if not math.isfinite(cumulative_return_scale) or cumulative_return_scale <= 0.0:
            raise ValueError("cumulative_return_scale must be positive and finite")
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be positive and finite")
        self.cumulative_return_scale = float(cumulative_return_scale)
        self.dt = float(dt)
        self.initial_state = _mlp(CONTEXT_DIM, HIDDEN_DIM)
        self.vector_field = _mlp(HIDDEN_DIM, HIDDEN_DIM * CRITIC_CONTROL_DIM)
        self.readout = nn.Linear(HIDDEN_DIM, 1)

    def forward(
        self,
        paths: Tensor,
        context: Tensor,
        cumulative_return_scale: float | None = None,
    ) -> Tensor:
        """Score each full path with a finite scalar terminal critic value."""
        if paths.ndim != 2 or paths.shape[1] != HORIZON:
            raise ValueError(f"paths must have shape (batch, {HORIZON})")
        _require_context(context)
        if paths.shape[0] != context.shape[0]:
            raise ValueError("paths and context must share the batch dimension")
        _require_finite("paths", paths)
        if paths.device != context.device:
            raise ValueError("paths and context must share a device")
        scale = (
            self.cumulative_return_scale
            if cumulative_return_scale is None
            else cumulative_return_scale
        )
        controls = build_critic_control_increments(paths, context, float(scale))
        hidden = self.initial_state(context)
        _require_finite("critic initial state", hidden)
        for interval in range(HORIZON):
            vector_field = self.vector_field(hidden).reshape(
                paths.shape[0], HIDDEN_DIM, CRITIC_CONTROL_DIM
            )
            hidden = hidden + (
                vector_field * controls[:, interval, :].unsqueeze(1)
            ).sum(dim=-1)
            _require_finite("critic hidden state", hidden)
        score = cast(Tensor, self.readout(hidden).squeeze(-1))
        _require_finite("critic score", score)
        return score
