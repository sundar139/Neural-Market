"""Deterministic Geometric Brownian Motion simulator and calibration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GbmCalibrationResult:
    """Closed-form GBM calibration from training log returns."""

    mu: float
    sigma: float
    dt: float
    n_observations: int
    empirical_mean_return: float
    empirical_return_std: float


def calibrate_gbm(returns: np.ndarray, *, dt: float = 1.0) -> GbmCalibrationResult:
    """Calibrate GBM drift and volatility from log returns.

    Formulas: ``sigma = std(r, ddof=1) / sqrt(dt)`` and
    ``mu = mean(r)/dt + 0.5 * sigma^2`` (inverting
    ``E[r] = (mu - 0.5*sigma^2) * dt``).
    """
    returns = np.asarray(returns, dtype=np.float64)
    if returns.ndim != 1 or len(returns) < 2:
        raise ValueError("returns must be a 1-D array with >= 2 observations")
    if dt <= 0:
        raise ValueError("dt must be positive")
    if np.any(~np.isfinite(returns)):
        raise ValueError("returns must not contain NaN or infinity")
    sigma = float(np.std(returns, ddof=1) / np.sqrt(dt))
    if sigma <= 0:
        raise ValueError("calibrated sigma must be positive")
    mu = float(np.mean(returns) / dt + 0.5 * sigma**2)
    return GbmCalibrationResult(
        mu=mu,
        sigma=sigma,
        dt=dt,
        n_observations=len(returns),
        empirical_mean_return=float(np.mean(returns)),
        empirical_return_std=float(np.std(returns, ddof=1)),
    )


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
