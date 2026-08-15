"""Deterministic Heston stochastic-volatility simulator and grid calibration.

Minimal research-valid baseline without new dependencies: Euler-Maruyama
discretization with full truncation for variance; calibration is a bounded
deterministic grid search matching the empirical daily log-return moments
(std, skewness, excess kurtosis) against a fixed-seed Monte Carlo of the
model. kappa is held at a conventional value and v0 = theta, so the fit is
deliberately not claimed to be uniquely identified; the artifact records
bounds, grid resolution, objective, and final parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HestonParameters:
    """Annualized Heston model parameters."""

    mu: float
    kappa: float
    theta: float
    xi: float
    rho: float
    v0: float


@dataclass(frozen=True)
class HestonCalibrationResult:
    """Deterministic grid-calibration outcome and full configuration."""

    parameters: HestonParameters
    objective: float
    convergence: str
    grid_evaluations: int
    parameter_bounds: dict[str, tuple[float, float]]
    grid_points_per_dimension: int
    refinement_passes: int
    calibration_paths: int
    horizon: int
    dt: float
    seed: int
    at_boundary: tuple[str, ...]
    empirical_moments: dict[str, float]
    simulated_moments: dict[str, float]


def sample_heston(
    n_paths: int,
    horizon: int,
    *,
    mu: float,
    kappa: float,
    theta: float,
    xi: float,
    rho: float,
    v0: float,
    dt: float,
    seed: int,
) -> np.ndarray:
    """Sample daily log-return increments from a Heston model.

    Returns shape ``(n_paths, horizon)`` using Euler-Maruyama with full
    truncation for the variance process and a Cholesky-implied correlation
    between variance and log-price shocks.
    """
    if n_paths < 1 or horizon < 1:
        raise ValueError("n_paths and horizon must be >= 1")
    if theta <= 0 or xi <= 0 or kappa <= 0 or v0 <= 0 or dt <= 0:
        raise ValueError("variance parameters must be positive")
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must lie in (-1, 1)")

    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal((n_paths, horizon, 2))
    variance = np.full(n_paths, v0, dtype=np.float64)
    increments = np.empty((n_paths, horizon), dtype=np.float64)
    z_var = shocks[:, :, 0]
    z_corr = rho * z_var + np.sqrt(max(1.0 - rho**2, 0.0)) * shocks[:, :, 1]
    for step in range(horizon):
        v_pos = np.maximum(variance, 0.0)
        increments[:, step] = (mu - 0.5 * v_pos) * dt + np.sqrt(v_pos * dt) * z_corr[:, step]
        variance = v_pos + kappa * (theta - v_pos) * dt + xi * np.sqrt(v_pos * dt) * z_var[:, step]
    return increments


def _simulate_moments(
    base_shocks: np.ndarray,
    *,
    mu: float,
    kappa: float,
    theta: float,
    xi: float,
    rho: float,
    dt: float,
) -> dict[str, float]:
    """Seeded-matrix simulation of one candidate; returns std/skew/kurt of increments."""
    horizon = base_shocks.shape[1]
    variance = np.full(base_shocks.shape[0], theta, dtype=np.float64)
    steps = np.empty((base_shocks.shape[0], horizon), dtype=np.float64)
    z_var = base_shocks[:, :, 0]
    z_corr = rho * z_var + np.sqrt(max(1.0 - rho**2, 0.0)) * base_shocks[:, :, 1]
    for step in range(horizon):
        v_pos = np.maximum(variance, 0.0)
        steps[:, step] = (mu - 0.5 * v_pos) * dt + np.sqrt(v_pos * dt) * z_corr[:, step]
        variance = v_pos + kappa * (theta - v_pos) * dt + xi * np.sqrt(v_pos * dt) * z_var[:, step]
    flat = steps.ravel()
    std = float(np.std(flat, ddof=1))
    centered = flat - np.mean(flat)
    m2 = float(np.mean(centered**2))
    m3 = float(np.mean(centered**3))
    m4 = float(np.mean(centered**4))
    skew = m3 / m2**1.5 if m2 > 1e-30 else 0.0
    kurt = m4 / m2**2 - 3.0 if m2 > 1e-30 else 0.0
    return {"std": std, "skewness": skew, "excess_kurtosis": kurt}


def _objective(
    simulated: dict[str, float],
    empirical: dict[str, float],
) -> float:
    """Sum of squared relative moment errors with skewness/kurtosis guards."""
    std_err = (simulated["std"] / empirical["std"] - 1.0) ** 2
    skew_err = (simulated["skewness"] - empirical["skewness"]) ** 2 / (
        1.0 + abs(empirical["skewness"])
    )
    kurt_err = (simulated["excess_kurtosis"] - empirical["excess_kurtosis"]) ** 2 / (
        1.0 + abs(empirical["excess_kurtosis"])
    )
    return std_err + skew_err + kurt_err


def calibrate_heston(
    returns: np.ndarray,
    *,
    dt: float,
    seed: int,
    kappa: float,
    calibration_paths: int,
    horizon: int,
    grid_points: int = 8,
    refinement_passes: int = 1,
) -> HestonCalibrationResult:
    """Calibrate theta/xi/rho via bounded deterministic grid search.

    mu is set from the first-moment condition ``E[r] = (mu - 0.5*v0)*dt``
    with ``v0 = theta``; kappa is fixed. Returns parameters and the full
    configuration for the provenance artifact.
    """
    returns = np.asarray(returns, dtype=np.float64)
    if returns.ndim != 1 or len(returns) < 10:
        raise ValueError("returns must be a 1-D array with >= 10 observations")
    empirical = {
        "std": float(np.std(returns, ddof=1)),
        "skewness": float(_moment_skewness(returns)),
        "excess_kurtosis": float(_moment_kurtosis(returns)),
    }

    bounds: dict[str, tuple[float, float]] = {
        "theta": (0.02, 0.30),
        "xi": (0.10, 1.20),
        "rho": (-0.95, -0.05),
    }
    rng = np.random.default_rng(seed)
    base_shocks = rng.standard_normal((calibration_paths, horizon, 2))

    def evaluate(theta: float, xi: float, rho: float) -> tuple[float, dict[str, float]]:
        mu = (np.mean(returns) + 0.5 * theta * dt) / dt
        simulated = _simulate_moments(
            base_shocks, mu=mu, kappa=kappa, theta=theta, xi=xi, rho=rho, dt=dt
        )
        return _objective(simulated, empirical), simulated

    theta_grid = np.linspace(*bounds["theta"], grid_points)
    xi_grid = np.linspace(*bounds["xi"], grid_points)
    rho_grid = np.linspace(*bounds["rho"], grid_points)
    evaluations = 0
    best: tuple[float, float, float, float, dict[str, float]] | None = None
    for theta in theta_grid:
        for xi in xi_grid:
            for rho in rho_grid:
                score, simulated = evaluate(theta, xi, rho)
                evaluations += 1
                if best is None or score < best[3]:
                    best = (theta, xi, rho, score, simulated)

    assert best is not None
    for _ in range(refinement_passes):
        theta, xi, rho, _, _ = best
        refined: list[tuple[float, float, float, float, dict[str, float]]] = []
        for dt_theta in (-1, 0, 1):
            for d_xi in (-1, 0, 1):
                for d_rho in (-1, 0, 1):
                    if dt_theta == 0 and d_xi == 0 and d_rho == 0:
                        refined.append(best)
                        continue
                    candidate_theta = theta + dt_theta * (theta_grid[1] - theta_grid[0]) / 2
                    candidate_xi = xi + d_xi * (xi_grid[1] - xi_grid[0]) / 2
                    candidate_rho = rho + d_rho * (rho_grid[1] - rho_grid[0]) / 2
                    candidate_theta = float(np.clip(candidate_theta, *bounds["theta"]))
                    candidate_xi = float(np.clip(candidate_xi, *bounds["xi"]))
                    candidate_rho = float(np.clip(candidate_rho, *bounds["rho"]))
                    score, simulated = evaluate(candidate_theta, candidate_xi, candidate_rho)
                    evaluations += 1
                    refined.append((candidate_theta, candidate_xi, candidate_rho, score, simulated))
        best = min(refined, key=lambda item: item[3])

    theta, xi, rho, objective, simulated = best
    mu = (np.mean(returns) + 0.5 * theta * dt) / dt
    parameters = HestonParameters(mu=mu, kappa=kappa, theta=theta, xi=xi, rho=rho, v0=theta)
    at_boundary = tuple(
        name
        for name, (low, high) in bounds.items()
        if abs(getattr(parameters, name) - low) < 1e-9
        or abs(getattr(parameters, name) - high) < 1e-9
    )
    if not np.isfinite(objective):
        raise ValueError("Heston calibration objective is non-finite")
    convergence = "grid_search_refined_with_boundary_flag" if at_boundary else "grid_search_refined"
    return HestonCalibrationResult(
        parameters=parameters,
        objective=float(objective),
        convergence=convergence,
        grid_evaluations=evaluations,
        parameter_bounds=bounds,
        grid_points_per_dimension=grid_points,
        refinement_passes=refinement_passes,
        calibration_paths=calibration_paths,
        horizon=horizon,
        dt=dt,
        seed=seed,
        at_boundary=at_boundary,
        empirical_moments=empirical,
        simulated_moments=simulated,
    )


def _moment_skewness(x: np.ndarray) -> float:
    centered = x - np.mean(x)
    m2 = np.mean(centered**2)
    m3 = np.mean(centered**3)
    return float(m3 / m2**1.5) if m2 > 1e-30 else 0.0


def _moment_kurtosis(x: np.ndarray) -> float:
    centered = x - np.mean(x)
    m2 = np.mean(centered**2)
    m4 = np.mean(centered**4)
    return float(m4 / m2**2 - 3.0) if m2 > 1e-30 else 0.0
