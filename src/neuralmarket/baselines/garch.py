"""Deterministic GJR-GARCH(1,1) volatility baseline with Gaussian innovations.

Protocol comparator (``reports/protocol/research_protocol_v1.md`` line 30:
"GJR-GARCH or EGARCH"). Specification:

```text
mean:     r_t = mu + e_t,           e_t = sqrt(h_t) * z_t,  z_t ~ N(0, 1) iid
variance: h_t = omega + (alpha + gamma * 1{e_{t-1} < 0}) * e_{t-1}^2 + beta * h_{t-1}
```

``mu`` is the sample mean and ``omega`` follows from variance targeting
(``omega = s^2 * (1 - persistence)``), so only ``(alpha, gamma, beta)`` are
searched. The optimizer is a bounded deterministic grid search with shrinking
refinement passes on the exact Gaussian log-likelihood, matching the existing
no-new-dependency calibration convention used for Heston. Fitting consumes the
single return array it is given; validation data never enters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_MAX_PERSISTENCE = 0.999
_MEAN_EQUATION = "r_t = mu + e_t with e_t = sqrt(h_t) * z_t"
_VARIANCE_EQUATION = "h_t = omega + (alpha + gamma * 1{e_{t-1} < 0}) * e_{t-1}^2 + beta * h_{t-1}"
_INITIALIZATION = "h_1 = sample variance of the fitted returns (= unconditional variance)"
_OPTIMIZER = "bounded_grid_search_with_shrinking_refinement"


@dataclass(frozen=True)
class GjrGarchParameters:
    """GJR-GARCH(1,1) parameters on the native (daily) return scale."""

    mu: float
    omega: float
    alpha: float
    gamma: float
    beta: float


@dataclass(frozen=True)
class GjrGarchCalibrationResult:
    """Deterministic calibration outcome and full estimator configuration."""

    parameters: GjrGarchParameters
    log_likelihood: float
    objective: float
    convergence: str
    persistence: float
    unconditional_variance: float
    initial_variance: float
    n_observations: int
    mean_equation: str
    variance_equation: str
    innovation_distribution: str
    initialization: str
    optimizer: str
    parameter_bounds: dict[str, tuple[float, float]]
    constraints: tuple[str, ...]
    grid_points_per_dimension: int
    refinement_passes: int
    grid_evaluations: int
    at_boundary: tuple[str, ...]


def _check_parameters(omega: float, alpha: float, gamma: float, beta: float) -> None:
    if not all(np.isfinite([omega, alpha, gamma, beta])):
        raise ValueError("GJR-GARCH parameters must be finite")
    if omega <= 0:
        raise ValueError("GJR-GARCH parameter omega must be positive")
    if alpha < 0 or beta < 0:
        raise ValueError("GJR-GARCH parameters alpha and beta must be non-negative")
    if alpha + gamma < 0:
        raise ValueError("GJR-GARCH parameter constraint alpha + gamma >= 0 is violated")


def gjr_garch_variance(
    returns: np.ndarray,
    *,
    mu: float,
    omega: float,
    alpha: float,
    gamma: float,
    beta: float,
    initial_variance: float,
) -> np.ndarray:
    """Filter the conditional-variance path implied by a return series.

    Args:
        returns: 1-D observed return series.
        mu: Constant mean.
        omega: Variance intercept (> 0).
        alpha: Symmetric ARCH coefficient (>= 0).
        gamma: Asymmetry (leverage) coefficient, with ``alpha + gamma >= 0``.
        beta: GARCH coefficient (>= 0).
        initial_variance: Strictly positive ``h_1``.

    Returns:
        Conditional variances ``h_t`` of the same length as ``returns``.

    Raises:
        ValueError: If the series, parameters, or initialization are invalid.
    """
    series = np.asarray(returns, dtype=np.float64)
    if series.ndim != 1 or series.size < 1:
        raise ValueError("returns must be a 1-D array with >= 1 observation")
    if np.any(~np.isfinite(series)):
        raise ValueError("returns must be finite")
    _check_parameters(omega, alpha, gamma, beta)
    if not np.isfinite(initial_variance) or initial_variance <= 0:
        raise ValueError("initial_variance must be positive and finite")

    residuals = series - mu
    variance = np.empty(series.size, dtype=np.float64)
    variance[0] = initial_variance
    for t in range(1, series.size):
        previous = residuals[t - 1]
        shock = (alpha + (gamma if previous < 0 else 0.0)) * previous * previous
        variance[t] = omega + shock + beta * variance[t - 1]
    if np.any(~np.isfinite(variance)) or np.any(variance <= 0):
        raise ValueError("GJR-GARCH variance recursion produced a non-positive or non-finite value")
    return variance


def gjr_garch_loglikelihood(
    returns: np.ndarray,
    *,
    mu: float,
    omega: float,
    alpha: float,
    gamma: float,
    beta: float,
    initial_variance: float,
) -> float:
    """Exact Gaussian log-likelihood of a GJR-GARCH(1,1) specification."""
    series = np.asarray(returns, dtype=np.float64)
    variance = gjr_garch_variance(
        series,
        mu=mu,
        omega=omega,
        alpha=alpha,
        gamma=gamma,
        beta=beta,
        initial_variance=initial_variance,
    )
    residuals = series - mu
    return float(-0.5 * np.sum(np.log(2.0 * np.pi) + np.log(variance) + residuals**2 / variance))


def calibrate_gjr_garch(
    returns: np.ndarray,
    *,
    grid_points: int = 9,
    refinement_passes: int = 6,
) -> GjrGarchCalibrationResult:
    """Calibrate GJR-GARCH(1,1) by bounded deterministic grid search.

    Args:
        returns: 1-D training log returns. This is the only data consumed.
        grid_points: Grid resolution per searched dimension.
        refinement_passes: Shrinking local refinement passes after the grid.

    Returns:
        The calibration result with full estimator provenance.

    Raises:
        ValueError: If the series is too short or the search fails to find a
            finite-likelihood feasible point.
    """
    series = np.asarray(returns, dtype=np.float64)
    if series.ndim != 1 or series.size < 100:
        raise ValueError("returns must be a 1-D array with >= 100 observations")
    if np.any(~np.isfinite(series)):
        raise ValueError("returns must be finite")

    mu = float(np.mean(series))
    sample_variance = float(np.var(series, ddof=1))
    if sample_variance <= 0:
        raise ValueError("returns must have positive sample variance")

    bounds: dict[str, tuple[float, float]] = {
        "alpha": (0.0, 0.30),
        "gamma": (0.0, 0.40),
        "beta": (0.30, 0.995),
    }
    constraints = (
        "omega > 0",
        "alpha >= 0",
        "beta >= 0",
        "alpha + gamma >= 0",
        f"persistence = alpha + 0.5 * gamma + beta < {_MAX_PERSISTENCE}",
        "omega = sample_variance * (1 - persistence)  [variance targeting]",
    )
    evaluations = 0

    def evaluate(alpha: float, gamma: float, beta: float) -> float:
        """Negative log-likelihood, or ``inf`` outside the feasible set."""
        nonlocal evaluations
        evaluations += 1
        persistence = alpha + 0.5 * gamma + beta
        if alpha < 0 or beta < 0 or alpha + gamma < 0 or not 0.0 < persistence < _MAX_PERSISTENCE:
            return float("inf")
        omega = sample_variance * (1.0 - persistence)
        try:
            value = gjr_garch_loglikelihood(
                series,
                mu=mu,
                omega=omega,
                alpha=alpha,
                gamma=gamma,
                beta=beta,
                initial_variance=sample_variance,
            )
        except ValueError:
            return float("inf")
        return -value if np.isfinite(value) else float("inf")

    grids = {name: np.linspace(low, high, grid_points) for name, (low, high) in bounds.items()}
    best: tuple[float, float, float, float] | None = None
    for alpha in grids["alpha"]:
        for gamma in grids["gamma"]:
            for beta in grids["beta"]:
                score = evaluate(float(alpha), float(gamma), float(beta))
                if best is None or score < best[3]:
                    best = (float(alpha), float(gamma), float(beta), score)
    if best is None or not np.isfinite(best[3]):
        raise ValueError("GJR-GARCH calibration found no feasible finite-likelihood point")

    spacing = {name: float(grid[1] - grid[0]) for name, grid in grids.items()}
    for level in range(refinement_passes):
        alpha, gamma, beta, _ = best
        scale = 0.5 ** (level + 1)
        for d_alpha in (-1, 0, 1):
            for d_gamma in (-1, 0, 1):
                for d_beta in (-1, 0, 1):
                    if d_alpha == 0 and d_gamma == 0 and d_beta == 0:
                        continue
                    candidate = (
                        float(
                            np.clip(alpha + d_alpha * spacing["alpha"] * scale, *bounds["alpha"])
                        ),
                        float(
                            np.clip(gamma + d_gamma * spacing["gamma"] * scale, *bounds["gamma"])
                        ),
                        float(np.clip(beta + d_beta * spacing["beta"] * scale, *bounds["beta"])),
                    )
                    score = evaluate(*candidate)
                    if score < best[3]:
                        best = (*candidate, score)

    alpha, gamma, beta, objective = best
    persistence = alpha + 0.5 * gamma + beta
    omega = sample_variance * (1.0 - persistence)
    parameters = GjrGarchParameters(mu=mu, omega=omega, alpha=alpha, gamma=gamma, beta=beta)
    at_boundary = tuple(
        name
        for name, (low, high) in bounds.items()
        if abs(getattr(parameters, name) - low) < 1e-12
        or abs(getattr(parameters, name) - high) < 1e-12
    )
    convergence = "grid_search_refined_with_boundary_flag" if at_boundary else "grid_search_refined"
    return GjrGarchCalibrationResult(
        parameters=parameters,
        log_likelihood=-objective,
        objective=objective,
        convergence=convergence,
        persistence=persistence,
        unconditional_variance=omega / (1.0 - persistence),
        initial_variance=sample_variance,
        n_observations=int(series.size),
        mean_equation=_MEAN_EQUATION,
        variance_equation=_VARIANCE_EQUATION,
        innovation_distribution="gaussian",
        initialization=_INITIALIZATION,
        optimizer=_OPTIMIZER,
        parameter_bounds=bounds,
        constraints=constraints,
        grid_points_per_dimension=grid_points,
        refinement_passes=refinement_passes,
        grid_evaluations=evaluations,
        at_boundary=at_boundary,
    )


def sample_gjr_garch(
    n_paths: int,
    horizon: int,
    *,
    mu: float,
    omega: float,
    alpha: float,
    gamma: float,
    beta: float,
    seed: int,
) -> np.ndarray:
    """Sample daily log-return increments from a stationary GJR-GARCH(1,1).

    Every path starts from the model's unconditional variance
    ``omega / (1 - alpha - 0.5 * gamma - beta)``, matching the long-run
    initialization convention used by the Heston baseline (``v0 = theta``).

    Args:
        n_paths: Number of independent paths.
        horizon: Number of steps per path.
        mu: Constant mean.
        omega: Variance intercept.
        alpha: Symmetric ARCH coefficient.
        gamma: Asymmetry coefficient.
        beta: GARCH coefficient.
        seed: Dedicated deterministic seed.

    Returns:
        Log-return increments of shape ``(n_paths, horizon)``.

    Raises:
        ValueError: If dimensions or parameters are invalid or non-stationary.
    """
    if n_paths < 1 or horizon < 1:
        raise ValueError("n_paths and horizon must be >= 1")
    _check_parameters(omega, alpha, gamma, beta)
    persistence = alpha + 0.5 * gamma + beta
    if not 0.0 <= persistence < 1.0:
        raise ValueError("GJR-GARCH parameters are non-stationary: alpha + 0.5*gamma + beta >= 1")

    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal((n_paths, horizon))
    variance = np.full(n_paths, omega / (1.0 - persistence), dtype=np.float64)
    increments = np.empty((n_paths, horizon), dtype=np.float64)
    for step in range(horizon):
        residual = np.sqrt(variance) * shocks[:, step]
        increments[:, step] = mu + residual
        variance = omega + (alpha + gamma * (residual < 0)) * residual * residual + beta * variance
    if np.any(~np.isfinite(increments)):
        raise ValueError("GJR-GARCH simulation produced non-finite increments")
    return increments
