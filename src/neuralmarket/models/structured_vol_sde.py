"""Structured stochastic-volatility neural SDE.

State dimension 2:
  X_t: cumulative log-return level (observable)
  V_t: latent log-volatility state

Public simulation output: one-step daily log-return increments (X increments).
V_t is an internal latent state that structurally drives return diffusion.

Return dynamics:
  dX_t = mu_x(t, X_t, V_t, context) dt + sigma_x(V_t) dW1_t
  sigma_x(V_t) = softplus(a * V_t + b) + epsilon

Latent volatility dynamics:
  dV_t = kappa(t, context) * (theta(t, context) - V_t) dt + eta(t, context) dW2_t
  kappa, eta > 0 via softplus + epsilon
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import cast

import torch
from torch import Tensor, nn

from neuralmarket.data.manifests import canonical_dumps


@dataclass(frozen=True)
class StructuredVolConfig:
    """Frozen structured-volatility neural SDE configuration."""

    # Config fields are self-documenting

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
        """Deterministic identity of the config."""
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


class StructuredVolatilityNeuralSde(nn.Module):
    """Structured stochastic-volatility neural SDE.

    State (x, V):
      x: cumulative log-return level
      V: latent volatility state

    Return dynamics:
      dX = mu_x(t, x, V, ctx) dt + sigma_x(V) dW1
      sigma_x(V) = softplus(a * V + b) + eps

    Volatility dynamics:
      dV = kappa(t, ctx) * (theta(t, ctx) - V) dt + eta(t, ctx) dW2
    """

    def __init__(self, config: StructuredVolConfig | None = None) -> None:
        """Initialize the structured volatility model."""
        super().__init__()
        self.config = StructuredVolConfig() if config is None else config
        cfg = self.config

        # Shared input dimension: time + state(x,V) + context
        in_dim = 1 + cfg.state_dim + cfg.n_context  # 1 + 2 + 4 = 7

        # X drift: (t, x, V, ctx) -> mu_x
        self.x_drift = _mlp(in_dim, 1, cfg.hidden_units, cfg.hidden_layers)

        # Volatility dynamics networks
        self.theta_net = _mlp(in_dim, 1, cfg.hidden_units, cfg.hidden_layers)
        self.kappa_net = _mlp(in_dim, 1, cfg.hidden_units, cfg.hidden_layers)
        self.eta_net = _mlp(in_dim, 1, cfg.hidden_units, cfg.hidden_layers)

        # sigma_x: softplus(a * V + b) + eps
        # a is constrained positive via softplus
        self.a_raw = nn.Parameter(torch.tensor(0.5))
        self.b_param = nn.Parameter(torch.tensor(0.0))

        # V0 initializer: context -> V0
        self.v0_layer = nn.Linear(cfg.n_context, 1)

    @property
    def a_positive(self) -> Tensor:
        """Positive slope parameter via softplus."""
        return torch.nn.functional.softplus(self.a_raw) + 1e-6

    def _state_input(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        if t.ndim == 1:
            t = t.unsqueeze(1)
        return torch.cat((t, state, context), dim=1)

    def initial_state(self, context: Tensor) -> Tensor:
        """Deterministic initial state: x0 = 0, V0 from context layer."""
        if context.ndim != 2 or context.shape[1] != self.config.n_context:
            raise ValueError(f"context must have shape (batch, {self.config.n_context})")
        if not torch.isfinite(context).all():
            raise ValueError("context must be finite")
        v0 = self.v0_layer(context)  # (B, 1)
        x0 = torch.zeros(context.shape[0], 1, dtype=context.dtype, device=context.device)
        return torch.cat((x0, v0), dim=1)

    def sigma_x(self, V: Tensor) -> Tensor:  # noqa: N803
        """Monotonic return diffusion: softplus(a * V + b) + eps."""
        return (
            torch.nn.functional.softplus(self.a_positive * V + self.b_param)
            + self.config.diffusion_epsilon
        )

    def x_drift_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """X drift vector at (t, state, context)."""
        return cast(Tensor, self.x_drift(self._state_input(t, state, context)))

    def drift_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Drift vector (compatibility with ConditionalNeuralSde interface)."""
        return self.x_drift_at(t, state, context)

    def diffusion_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Positive diagonal diffusion (compatibility interface)."""
        sigma_x = self.sigma_x(state[:, 1:2])
        # Pad to (batch, state_dim) for compatibility with gate diagnostics
        return torch.cat([sigma_x, sigma_x], dim=1)

    def theta_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Volatility long-run mean."""
        return cast(Tensor, self.theta_net(self._state_input(t, state, context)))

    def kappa_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Volatility mean-reversion speed (positive)."""
        raw = self.kappa_net(self._state_input(t, state, context))
        return torch.nn.functional.softplus(raw) + self.config.diffusion_epsilon

    def eta_at(self, t: Tensor, state: Tensor, context: Tensor) -> Tensor:
        """Volatility diffusion intensity (positive)."""
        raw = self.eta_net(self._state_input(t, state, context))
        return torch.nn.functional.softplus(raw) + self.config.diffusion_epsilon

    def forward(
        self,
        context: Tensor,
        noise: Tensor,
        dt: float | None = None,
    ) -> Tensor:
        """Simulate daily log return increments.

        Args:
            context: (batch, n_context) normalized context.
            noise: (batch, horizon, brownian_dim) standard normals.
            dt: Time step.

        Returns:
            (batch, horizon) daily log return increments.
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

            # X drift
            mu_x = self.x_drift_at(t, state, context)

            # Return diffusion: structurally coupled to V
            sigma_x = self.sigma_x(state[:, 1:2])

            # Volatility dynamics
            theta = self.theta_at(t, state, context)
            kappa = self.kappa_at(t, state, context)
            eta = self.eta_at(t, state, context)

            if not torch.isfinite(mu_x).all() or not torch.isfinite(sigma_x).all():
                raise RuntimeError("non-finite X drift or diffusion")
            if torch.any(sigma_x <= 0.0):
                raise RuntimeError("non-positive X diffusion")
            if not torch.isfinite(kappa).all() or not torch.isfinite(eta).all():
                raise RuntimeError("non-finite volatility parameters")
            if torch.any(kappa <= 0.0) or torch.any(eta <= 0.0):
                raise RuntimeError("non-positive volatility parameters")

            # Euler-Maruyama updates
            dx = mu_x * dt + sigma_x * scaled_noise[:, k, 0:1]
            dV = kappa * (theta - state[:, 1:2]) * dt + eta * sqrt_dt * noise[:, k, 1:2]  # noqa: N806

            if not torch.isfinite(dx).all() or not torch.isfinite(dV).all():
                raise RuntimeError("non-finite state increment")

            state = state + torch.cat([dx, dV], dim=1)
            # Clamp V to prevent numerical divergence
            state = torch.clamp(state, min=-10.0, max=10.0)
            if not torch.isfinite(state).all():
                raise RuntimeError("non-finite state during simulation")

            increments.append(dx)

        return torch.cat(increments, dim=1)


def simulate_structured(
    model: StructuredVolatilityNeuralSde,
    context: Tensor,
    seed: int,
    generator: torch.Generator | None = None,
) -> Tensor:
    """Generate paths using the structured volatility model."""
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
