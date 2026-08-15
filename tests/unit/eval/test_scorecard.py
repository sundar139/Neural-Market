"""Tests for stylized-fact scorecard."""

from __future__ import annotations

import json

import numpy as np
import pytest

from neuralmarket.eval.scorecard import (
    ScorecardConfig,
    compute_scorecard,
)

pytestmark = pytest.mark.unit


# ── validation ───────────────────────────────────────────────────────


def test_rejects_empty() -> None:
    with pytest.raises(ValueError, match="at least"):
        compute_scorecard(np.array([]))


def test_rejects_too_few_observations() -> None:
    rng = np.random.default_rng(42)
    with pytest.raises(ValueError, match="at least"):
        compute_scorecard(rng.standard_normal(100))


def test_rejects_nan() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(300)
    x[10] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        compute_scorecard(x)


def test_rejects_inf() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(300)
    x[10] = np.inf
    with pytest.raises(ValueError, match="infinity"):
        compute_scorecard(x)


def test_rejects_2d() -> None:
    with pytest.raises(ValueError, match="1-D"):
        compute_scorecard(np.ones((100, 2)))


def test_rejects_wrong_lag_count() -> None:
    rng = np.random.default_rng(42)
    config = ScorecardConfig(lags=(500,))
    with pytest.raises(ValueError, match="more than"):
        compute_scorecard(rng.standard_normal(300), config=config)


def test_rejects_small_aggregation() -> None:
    rng = np.random.default_rng(42)
    config = ScorecardConfig(aggregation_horizons=(1,))
    with pytest.raises(ValueError, match=">= 2"):
        compute_scorecard(rng.standard_normal(500), config=config)


# ── determinism ─────────────────────────────────────────────────────


def test_deterministic_output() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    r1 = compute_scorecard(x)
    r2 = compute_scorecard(x)
    assert r1 == r2


def test_no_input_mutation() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    x_copy = x.copy()
    compute_scorecard(x)
    assert np.array_equal(x, x_copy)


# ── constant series ─────────────────────────────────────────────────


def test_constant_series() -> None:
    x = np.zeros(500)  # zero returns
    r = compute_scorecard(x)
    assert r.variance == 0.0
    assert r.excess_kurtosis == 0.0


# ── Gaussian control ─────────────────────────────────────────────────


def test_gaussian_kurtosis_near_zero() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(5000)
    r = compute_scorecard(x)
    assert abs(r.excess_kurtosis) < 0.5


def test_gaussian_insignificant_acf() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(5000)
    r = compute_scorecard(x)
    # IID → all ACF near zero
    for v in r.return_acf.values():
        assert abs(v) < 0.1
    for v in r.sq_return_acf.values():
        assert abs(v) < 0.1


# ── heavy-tail detection ────────────────────────────────────────────


def test_heavy_tail_higher_kurtosis() -> None:
    rng = np.random.default_rng(42)
    n = 5000
    gauss = rng.standard_normal(n)
    # t-distributed with 3 df → heavy tails
    heavy = rng.standard_t(3, size=n)
    r_gauss = compute_scorecard(gauss)
    r_heavy = compute_scorecard(heavy)
    assert r_heavy.excess_kurtosis > r_gauss.excess_kurtosis + 1.0


# ── clustering detection ────────────────────────────────────────────


def test_clustered_volatility_detected() -> None:
    rng = np.random.default_rng(777)
    n = 8000
    burn = 2000
    total = n + burn
    # GARCH(1,1) with standard parameters: omega=1e-6, alpha=0.1, beta=0.85
    omega, alpha, beta = 1e-6, 0.1, 0.85
    sigma2 = np.ones(total)
    noise = rng.standard_normal(total)
    for i in range(1, total):
        sigma2[i] = omega + beta * sigma2[i - 1] + alpha * noise[i - 1] ** 2
    clustered = np.sqrt(sigma2[burn:]) * noise[burn:]
    r = compute_scorecard(clustered)
    assert r.sq_return_acf[1] > 0.07


def test_shuffling_destroys_clustering() -> None:
    rng = np.random.default_rng(42)
    n = 2000
    sigma = np.ones(n)
    for i in range(1, n):
        sigma[i] = np.sqrt(0.05 + 0.90 * sigma[i - 1] ** 2 + 0.05 * rng.standard_normal() ** 2)
    clustered = sigma * rng.standard_normal(n)

    r_orig = compute_scorecard(clustered)
    shuffled = rng.permutation(clustered)
    r_shuffled = compute_scorecard(shuffled)

    assert r_orig.sq_return_acf[1] > r_shuffled.sq_return_acf[1] * 2
    # Marginals preserved (approx means)
    assert abs(r_orig.mean - r_shuffled.mean) < 0.1


# ── aggregation ─────────────────────────────────────────────────────


def test_aggregation_discards_trailing() -> None:
    """Excess observations at the end are discarded, not padded."""
    rng = np.random.default_rng(42)
    x = rng.standard_normal(253)  # 253 / 5 = 50 rem 3
    r = compute_scorecard(x)
    assert r.discarded_at_horizon[5] == 3


def test_gaussian_aggregation_reduces_kurtosis() -> None:
    """CLT: aggregating IID normal should reduce excess kurtosis toward zero."""
    rng = np.random.default_rng(42)
    x = rng.standard_normal(25000)
    r = compute_scorecard(x)
    assert r.aggregated_kurtosis[5] is not None
    # With large N, aggregated kurtosis should be close to zero
    assert abs(r.aggregated_kurtosis[5]) < 0.15


# ── leverage ────────────────────────────────────────────────────────


def test_leverage_indexing() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    r = compute_scorecard(x)
    assert 1 in r.leverage_correlations
    assert abs(r.leverage_correlations[1]) < 0.2  # near zero for IID


# ── serialization ───────────────────────────────────────────────────


def test_result_serializable() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    r = compute_scorecard(x)
    d = {
        "n": r.n_observations,
        "mean": r.mean,
        "var": r.variance,
        "kurt": r.excess_kurtosis,
        "hill": r.hill_tail_index,
        "return_acf": r.return_acf,
    }
    json.dumps(d)


# ── scorecard configuration ─────────────────────────────────────────


def test_custom_config() -> None:
    config = ScorecardConfig(lags=(1, 2, 3), aggregation_horizons=(2, 4, 8))
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    r = compute_scorecard(x, config=config)
    assert set(r.return_acf.keys()) == {1, 2, 3}
    assert set(r.aggregated_kurtosis.keys()) == {2, 4, 8}


# ── skewness and tail quantiles ─────────────────────────────────────


def test_gaussian_skewness_near_zero() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(5000)
    r = compute_scorecard(x)
    assert abs(r.skewness) < 0.15


def test_skewed_series_detected() -> None:
    rng = np.random.default_rng(42)
    x = -rng.standard_t(4, size=5000)  # left-skewed heavy tails
    r = compute_scorecard(x)
    assert r.skewness < 0


def test_quantiles_match_numpy() -> None:
    rng = np.random.default_rng(42)
    x = rng.standard_normal(1000)
    r = compute_scorecard(x)
    for level, value in r.quantiles.items():
        assert value == pytest.approx(float(np.quantile(x, float(level))), abs=1e-12)
    assert set(r.quantiles.keys()) == {"0.01", "0.05", "0.1", "0.9", "0.95", "0.99"}


# ── metric specification ────────────────────────────────────────────


def test_spec_hash_deterministic() -> None:
    from neuralmarket.eval.scorecard import MetricSpecification

    first = MetricSpecification()
    second = MetricSpecification()
    assert first.spec_hash() == second.spec_hash()


def test_spec_hash_changes_with_config() -> None:
    from neuralmarket.eval.scorecard import MetricSpecification

    base = MetricSpecification().spec_hash()
    changed = MetricSpecification(scorecard=ScorecardConfig(lags=(1, 5, 22))).spec_hash()
    assert changed != base


def test_spec_hash_changes_with_seed() -> None:
    from neuralmarket.eval.scorecard import MetricSpecification

    base = MetricSpecification().spec_hash()
    changed = MetricSpecification(gbm_seed=9999).spec_hash()
    assert changed != base


def test_spec_has_no_wall_clock_identity() -> None:
    from neuralmarket.eval.scorecard import MetricSpecification

    spec = MetricSpecification()
    import time

    time.sleep(0.01)
    assert spec.spec_hash() == MetricSpecification().spec_hash()
