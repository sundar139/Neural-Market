"""Deterministic Geometric Brownian Motion simulator."""

from __future__ import annotations

import numpy as np


def sample_gbm(
    n_paths: int,
    horizon: int,
    *,
    mu: float = 0.0,
    sigma: float = 1.0,
    initial_price: float = 1.0,
    dt: float = 1.0,
    seed: int = 1337,
) -> np.ndarray:
    """Sample log-return paths from GBM.

    Returns log-returns of shape ``(n_paths, horizon)`` generated via:

        dS/S = mu * dt + sigma * sqrt(dt) * Z

    with ``Z ~ N(0, 1)``, using a local seeded generator.

    Args:
        n_paths: Number of independent paths.
        horizon: Number of steps per path.
        mu: Drift per unit time.
        sigma: Volatility per unit time.
        initial_price: Unused; retained for interface compatibility.
        dt: Time step.
        seed: Seeder for reproducibility.

    Returns:
        Array of shape ``(n_paths, horizon)`` with log-return increments.
    """
    if n_paths < 1 or horizon < 1:
        raise ValueError("n_paths and horizon must be >= 1")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")

    rng = np.random.default_rng(seed)
    # Log-return per step: N(mu*dt - 0.5*sigma^2*dt, sigma^2*dt)
    drift = (mu - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt)
    increments: np.ndarray = drift + diffusion * rng.standard_normal((n_paths, horizon))
    return increments
