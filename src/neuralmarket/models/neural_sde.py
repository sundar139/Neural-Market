"""Conditional neural SDE generator with Euler-Maruyama integration.

The model is the FROZEN FALLBACK conditional neural SDE for the SPY daily
cumulative log-return process: a two-dimensional state (observable cumulative
log return ``x`` plus a latent state ``z``) driven by two Brownian motions.
The drift and diagonal diffusion are MLPs over normalized time, current state,
and normalized conditioning context.  Diffusion is forced positive with
``softplus(raw) + eps``.  Integration is plain Euler-Maruyama at
``dt = 1/252`` over the frozen 63-session horizon, returning exactly 63 daily
log returns per path.  Non-finite state fails closed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import cast

import numpy as np
import torch
from torch import Tensor, nn

from neuralmarket.data.manifests import canonical_dumps


def set_deterministic_seeds(seed: int) -> None:
    """Seed Python, NumPy, torch CPU, and torch CUDA deterministically."""
    import random

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def configure_determinism(enabled: bool = True) -> None:
    """Configure torch for deterministic operation where supported.

    On CPU this enables ``torch.use_deterministic_algorithms`` and disables
    the nondeterministic cuDNN benchmark mode.  Mixed precision is never used
    in v1.  CUDA is not required: if an operation is not deterministic on the
    selected device, torch raises rather than silently degrading.
    """
    torch.use_deterministic_algorithms(enabled, warn_only=False)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


@dataclass(frozen=True)
class SdeConfig:
    """Frozen neural-SDE architecture and integration configuration."""

    state_dim: int = 2
    brownian_dim: int = 2
    n_context: int = 4
    hidden_units: int = 64
    hidden_layers: int = 2
    activation: str = "SiLU"
    diffusion_epsilon: float = 1e-6
    dt: float = 1.0 / 252.0
    horizon: int = 63
    signature_level: int = 3

    def config_hash(self) -> str:
        """Deterministic identity of the architecture config (no wall clock)."""
        return hashlib.sha256(
            canonical_dumps(
                {
                    "state_dim": self.state_dim,
                    "brownian_dim": self.brownian_dim,
                    "n_context": self.n_context,
                    "hidden_units": self.hidden_units,
                    "hidden_layers": self.hidden_layers,
                    "activation": self.activation,
                    "diffusion_epsilon": self.diffusion_epsilon,
                    "dt": self.dt,
                    "horizon": self.horizon,
                    "signature_level": self.signature_level,
                }
            ).encode("utf-8")
        ).hexdigest()


def _mlp(in_dim: int, out_dim: int, hidden_units: int, hidden_layers: int) -> nn.Sequential:
    layers: list[nn.Module] = []
    current = in_dim
    for _ in range(hidden_layers):
        layers.append(nn.Linear(current, hidden_units))
        layers.append(nn.SiLU())
        current = hidden_units
    layers.append(nn.Linear(current, out_dim))
    return nn.Sequential(*layers)


class ConditionalNeuralSde(nn.Module):
    """Conditional neural SDE: ``dX = mu(t, X, C) dt + sigma(t, X, C) dW``.

    Attributes:
        drift: MLP mapping ``(1 + state_dim + n_context) -> state_dim``.
        diffusion: MLP mapping the same input to ``state_dim`` diagonal
            diffusion coordinates, forced positive with ``softplus + eps``.
        z0_layer: Small deterministic context-conditioned initialization layer
            mapping ``n_context -> 1`` used for the latent initial state.
    """

    def __init__(self, config: SdeConfig | None = None) -> None:
        """Initialize the conditional neural SDE with a frozen config.

        Args:
            config: Architecture/integration config; defaults to the frozen
                fallback design when omitted.
        """
        super().__init__()
        self.config = SdeConfig() if config is None else config
        cfg = self.config
        in_dim = 1 + cfg.state_dim + cfg.n_context
        self.drift = _mlp(in_dim, cfg.state_dim, cfg.hidden_units, cfg.hidden_layers)
        self.diffusion = _mlp(in_dim, cfg.state_dim, cfg.hidden_units, cfg.hidden_layers)
        self.z0_layer = nn.Linear(cfg.n_context, 1)

    def _state_input(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        # t: (B,) or (B,1), state: (B, state_dim), context: (B, n_context)
        if t.ndim == 1:
            t = t.unsqueeze(1)
        return torch.cat((t, state, context), dim=1)

    def initial_state(self, context: Tensor) -> Tensor:
        """Deterministic initial state: x_0 = 0, z_0 from a context layer.

        Args:
            context: Shape ``(batch, n_context)`` normalized conditioning.

        Returns:
            Tensor ``(batch, state_dim)`` with the observable coordinate zero
            and the latent coordinate produced by the context layer.

        Raises:
            ValueError: If the context is malformed or non-finite.
        """
        if context.ndim != 2 or context.shape[1] != self.config.n_context:
            raise ValueError(f"context must have shape (batch, {self.config.n_context})")
        if not torch.isfinite(context).all():
            raise ValueError("context must be finite")
        z0 = self.z0_layer(context)  # (B, 1)
        x0 = torch.zeros(context.shape[0], 1, dtype=context.dtype, device=context.device)
        return torch.cat((x0, z0), dim=1)

    def drift_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Drift vector at time ``t`` and state ``state`` for one batch."""
        from typing import cast

        return cast(Tensor, self.drift(self._state_input(t, state, context)))

    def diffusion_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Positive diagonal diffusion coordinates at ``(t, state)``."""
        raw = self.diffusion(self._state_input(t, state, context))
        return torch.nn.functional.softplus(raw) + self.config.diffusion_epsilon

    def forward(
        self,
        context: Tensor,
        noise: Tensor,
        dt: float | None = None,
    ) -> Tensor:
        """Simulate ``horizon`` daily log return increments with Euler-Maruyama.

        The returned tensor contains one-step x-coordinate *increments*
        (daily log returns), NOT cumulative state levels.

        Args:
            context: Shape ``(batch, n_context)`` training-normalized context.
            noise: Shape ``(batch, horizon, brownian_dim)`` standard normal
                increments of the Brownian motions (pre-scaled by ``sqrt(dt)``
                by the caller or here).
            dt: Optional time step (defaults to the config ``dt``).

        Returns:
            Daily log return increments of shape ``(batch, horizon)``.
            Each element is x_{k+1} - x_k, always finite.

        Raises:
            RuntimeError: If any state, diffusion, or increment is non-finite.
            ValueError: If the inputs are malformed.
        """
        cfg = self.config
        dt = cfg.dt if dt is None else dt
        if context.ndim != 2 or context.shape[1] != cfg.n_context:
            raise ValueError(f"context must have shape (batch, {cfg.n_context})")
        if noise.ndim != 3 or noise.shape[0] != context.shape[0]:
            raise ValueError("noise must share the batch dimension with context")
        if noise.shape[1] != cfg.horizon or noise.shape[2] != cfg.brownian_dim:
            raise ValueError(f"noise must have shape (batch, {cfg.horizon}, {cfg.brownian_dim})")
        batch = context.shape[0]
        device, dtype = context.device, context.dtype

        state = self.initial_state(context)
        sqrt_dt = float(dt) ** 0.5
        scaled_noise = noise * sqrt_dt
        increments: list[Tensor] = []
        time_unit = 1.0 / cfg.horizon
        for k in range(cfg.horizon):
            t = torch.full((batch,), float(k) * time_unit, device=device, dtype=dtype)
            mu = self.drift_at(t, state, context)
            sigma = self.diffusion_at(t, state, context)
            if not torch.isfinite(mu).all() or not torch.isfinite(sigma).all():
                raise RuntimeError("non-finite drift or diffusion during simulation")
            if torch.any(sigma <= 0.0):
                raise RuntimeError("non-positive diffusion during simulation")
            step = mu * dt + sigma * scaled_noise[:, k, :]
            if not torch.isfinite(step).all():
                raise RuntimeError("non-finite state increment during simulation")
            state = state + step
            if not torch.isfinite(state).all():
                raise RuntimeError("non-finite state during simulation")
            increments.append(step[:, 0].unsqueeze(1))
        return torch.cat(increments, dim=1)


def simulate(
    model: ConditionalNeuralSde,
    context: Tensor,
    seed: int,
    generator: torch.Generator | None = None,
) -> Tensor:
    """Generate ``n_paths`` x ``horizon`` daily returns under a fixed seed.

    Args:
        model: The frozen neural SDE (evaluation mode).
        context: Shape ``(n_paths, n_context)`` normalized context; the same
            context is used to generate all paths.
        seed: Deterministic noise seed for the Brownian innovations.
        generator: Optional pre-seeded generator (overrides ``seed``).

    Returns:
        Tensor ``(n_paths, horizon)`` of generated daily log returns.

    Raises:
        RuntimeError: If the simulation produces non-finite values.
    """
    cfg = model.config
    n_paths = context.shape[0]
    device, dtype = context.device, context.dtype
    gen = generator if generator is not None else torch.Generator(device=device).manual_seed(seed)
    noise = torch.randn(
        n_paths, cfg.horizon, cfg.brownian_dim, device=device, dtype=dtype, generator=gen
    )
    with torch.no_grad():
        increments = model(context, noise)
    if not torch.isfinite(increments).all():
        raise RuntimeError("simulation produced non-finite increments")
    return cast(Tensor, increments)


def reconstruct_prices(increments: Tensor, initial_price: float) -> Tensor:
    """Reconstruct prices from daily log returns.

    ``price_t = initial_price * exp(cumsum(increments))``.

    Args:
        increments: Tensor of daily log returns.
        initial_price: Positive starting price.

    Returns:
        Price tensor of the same shape as ``increments``.

    Raises:
        ValueError: If the initial price is non-positive or inputs are bad.
    """
    if initial_price <= 0 or not np.isfinite(initial_price):
        raise ValueError("initial price must be positive and finite")
    if not torch.isfinite(increments).all():
        raise ValueError("increments must be finite")
    prices = initial_price * torch.exp(increments.cumsum(dim=-1))
    if not torch.isfinite(prices).all() or torch.any(prices <= 0.0):
        raise RuntimeError("reconstructed prices must be positive and finite")
    return prices


def count_parameters(model: nn.Module) -> int:
    """Total trainable parameter count of a module."""
    return sum(int(p.numel()) for p in model.parameters() if p.requires_grad)
