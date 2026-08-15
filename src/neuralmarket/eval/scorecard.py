"""Stylized-fact scorecard and frozen metric specification for return series."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

import numpy as np

from neuralmarket.data.manifests import canonical_dumps

_METRIC_SPEC_VERSION = "research-metric-spec-v1"


@dataclass(frozen=True)
class ScorecardConfig:
    """Configuration for a scorecard computation.

    Attributes:
        lags: Lags for ACF and leverage calculations.
        aggregation_horizons: Non-overlapping aggregation windows (in observations).
        min_observations: Minimum number of observations required.
        hill_sample_fraction: Fraction of largest absolute returns for Hill estimation.
        tail_quantiles: Quantile levels for the distribution/tail family.
    """

    lags: tuple[int, ...] = (1, 5, 22, 66)
    aggregation_horizons: tuple[int, ...] = (5, 22)
    min_observations: int = 252
    hill_sample_fraction: float = 0.1
    tail_quantiles: tuple[float, ...] = (0.01, 0.05, 0.10, 0.90, 0.95, 0.99)


@dataclass(frozen=True)
class MetricSpecification:
    """Frozen, versioned research metric specification.

    Freezes every convention the stylized-fact scorecard and baseline
    simulation comparison depend on, so results remain reproducible and the
    specification cannot be silently tuned after baselines are evaluated.
    """

    version: str = _METRIC_SPEC_VERSION
    scorecard: ScorecardConfig = field(default_factory=ScorecardConfig)
    leverage_convention: str = "corr(r_t, r2_{t+k}) for k in lags with k > 0"
    annualization: str = "none (raw daily log returns)"
    simulation_dt: float = 1.0 / 252.0
    simulation_horizon_sessions: int = 63
    simulation_paths: int = 1024
    calibration_paths: int = 2048
    gbm_seed: int = 1337
    heston_seed: int = 1729
    heston_kappa_annualized: float = 2.0
    heston_v0_convention: str = "v0 = theta"
    initial_price_convention: str = "final training-session close"

    def spec_hash(self) -> str:
        """Deterministic identity of the specification (no wall clock)."""
        return hashlib.sha256(canonical_dumps(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScorecardResult:
    """Deterministic structured result of a scorecard computation.

    All fields are plain serializable types.
    """

    n_observations: int
    mean: float
    variance: float
    skewness: float
    excess_kurtosis: float
    quantiles: dict[str, float]
    hill_tail_index: float | None
    return_acf: dict[int, float] = field(default_factory=dict)
    abs_return_acf: dict[int, float] = field(default_factory=dict)
    sq_return_acf: dict[int, float] = field(default_factory=dict)
    leverage_correlations: dict[int, float] = field(default_factory=dict)
    aggregated_kurtosis: dict[int, float] = field(default_factory=dict)
    ljung_box_return: dict[int, float] = field(default_factory=dict)
    ljung_box_squared: dict[int, float] = field(default_factory=dict)
    discarded_at_horizon: dict[int, int] = field(default_factory=dict)
    config: ScorecardConfig = field(default_factory=ScorecardConfig)


def compute_scorecard(
    returns: np.ndarray,
    config: ScorecardConfig | None = None,
) -> ScorecardResult:
    """Compute a deterministic stylized-fact scorecard for a return series.

    Args:
        returns: 1-D array of log or simple returns.
        config: Optional configuration. Uses defaults when ``None``.

    Returns:
        A frozen ``ScorecardResult``.

    Raises:
        ValueError: If the input is invalid.
    """
    if config is None:
        config = ScorecardConfig()

    returns = np.asarray(returns, dtype=np.float64)
    _validate_input(returns, config)

    n = len(returns)
    mean = float(np.mean(returns))
    var = float(np.var(returns, ddof=1))
    skew = _skewness(returns)
    kurt = _excess_kurtosis(returns)
    quantiles = {str(q): float(np.quantile(returns, q)) for q in config.tail_quantiles}

    # Hill tail index
    hill = None
    if n >= 100:
        hill = _hill_estimate(np.abs(returns), int(n * config.hill_sample_fraction))

    # ACF
    return_acf = {lag: _acf(returns, lag) for lag in config.lags}
    abs_acf = {lag: _acf(np.abs(returns), lag) for lag in config.lags}
    sq_acf = {lag: _acf(returns**2, lag) for lag in config.lags}

    # Leverage: corr(r_t, r²_{t+k})
    leverage: dict[int, float] = {}
    sq = returns**2
    for k in config.lags:
        if k > 0 and n > k:
            leverage[k] = float(np.corrcoef(returns[:-k], sq[k:])[0, 1])

    # Aggregation
    agg_kurt: dict[int, float] = {}
    discarded: dict[int, int] = {}
    for h in config.aggregation_horizons:
        n_agg = n // h
        discarded[h] = n - n_agg * h
        if n_agg >= 10:
            agg = returns[: n_agg * h].reshape(n_agg, h).sum(axis=1)
            agg_kurt[h] = _excess_kurtosis(agg)

    # Ljung-Box
    lb_ret = {lag: _ljung_box(returns, lag) for lag in config.lags}
    lb_sq = {lag: _ljung_box(returns**2, lag) for lag in config.lags}

    return ScorecardResult(
        n_observations=n,
        mean=mean,
        variance=var,
        skewness=skew,
        excess_kurtosis=kurt,
        quantiles=quantiles,
        hill_tail_index=hill,
        return_acf=return_acf,
        abs_return_acf=abs_acf,
        sq_return_acf=sq_acf,
        leverage_correlations=leverage,
        aggregated_kurtosis=agg_kurt,
        ljung_box_return=lb_ret,
        ljung_box_squared=lb_sq,
        discarded_at_horizon=discarded,
        config=config,
    )


# ── helpers ──────────────────────────────────────────────────────────


def _validate_input(returns: np.ndarray, config: ScorecardConfig) -> None:
    if returns.ndim != 1:
        raise ValueError("returns must be 1-D")
    n = len(returns)
    if n < config.min_observations:
        raise ValueError(f"need at least {config.min_observations} observations, got {n}")
    if not np.issubdtype(returns.dtype, np.floating):
        raise ValueError("returns must be numeric")
    if np.any(np.isnan(returns)) or np.any(np.isinf(returns)):
        raise ValueError("returns must not contain NaN or infinity")
    max_lag = max(config.lags) if config.lags else 0
    if n <= max_lag:
        raise ValueError(f"need more than {max_lag} observations for configured lags")
    for h in config.aggregation_horizons:
        if h < 2:
            raise ValueError(f"aggregation horizon must be >= 2, got {h}")


def _skewness(x: np.ndarray) -> float:
    """Fisher-Pearson standardized skewness (population moments)."""
    centered = x - np.mean(x)
    m2 = np.mean(centered**2)
    m3 = np.mean(centered**3)
    if m2 < 1e-30:
        return 0.0
    return float(m3 / m2**1.5)


def _excess_kurtosis(x: np.ndarray) -> float:
    """Excess kurtosis (Fisher definition: kurtosis - 3)."""
    centered = x - np.mean(x)
    m2 = np.mean(centered**2)
    m4 = np.mean(centered**4)
    if m2 < 1e-30:
        return 0.0
    return float(m4 / m2**2 - 3.0)


def _acf(x: np.ndarray, lag: int) -> float:
    """Sample autocorrelation at a given lag."""
    if lag <= 0 or lag >= len(x):
        return float("nan")
    xc = x - np.mean(x)
    return float(np.corrcoef(xc[:-lag], xc[lag:])[0, 1])


def _ljung_box(x: np.ndarray, lag: int) -> float:
    """Ljung-Box Q-statistic."""
    n = len(x)
    if lag <= 0 or lag >= n:
        return float("nan")
    acf_vals = [_acf(x, k) for k in range(1, lag + 1)]
    q = n * (n + 2) * sum(r**2 / (n - k) for k, r in enumerate(acf_vals, 1))
    return float(q)


def _hill_estimate(abs_x: np.ndarray, k: int) -> float:
    """Hill estimator of tail index.

    Uses the k largest values.  Returns 1/xi where xi is the
    Hill estimator of the shape parameter (so larger values mean
    thinner tails).
    """
    if k < 10:
        return float("nan")
    top = np.sort(abs_x)[-k:]
    threshold = top[0]
    xi = np.mean(np.log(top / threshold))
    if xi < 1e-30:
        return float("inf")
    return float(1.0 / xi)
