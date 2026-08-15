"""Tests for deterministic GBM simulation."""

from __future__ import annotations

import numpy as np
import pytest

from neuralmarket.baselines.gbm import sample_gbm

pytestmark = pytest.mark.unit


def test_invalid_n_paths() -> None:
    with pytest.raises(ValueError):
        sample_gbm(0, 100)


def test_invalid_horizon() -> None:
    with pytest.raises(ValueError):
        sample_gbm(10, 0)


def test_invalid_sigma() -> None:
    with pytest.raises(ValueError):
        sample_gbm(10, 100, sigma=0)


def test_output_shape() -> None:
    x = sample_gbm(100, 252)
    assert x.shape == (100, 252)


def test_deterministic() -> None:
    x1 = sample_gbm(10, 100, seed=42)
    x2 = sample_gbm(10, 100, seed=42)
    assert np.array_equal(x1, x2)


def test_different_seed_different() -> None:
    x1 = sample_gbm(10, 100, seed=42)
    x2 = sample_gbm(10, 100, seed=43)
    assert not np.array_equal(x1, x2)


def test_log_return_mean_against_closed_form() -> None:
    """GBM log-return mean = (mu - 0.5*sigma^2)*dt."""
    mu, sigma, dt = 0.1, 0.2, 1.0
    x = sample_gbm(1000, 500, mu=mu, sigma=sigma, dt=dt, seed=42)
    expected = (mu - 0.5 * sigma**2) * dt
    actual = float(np.mean(x))
    assert abs(actual - expected) < 0.02


def test_log_return_std_against_closed_form() -> None:
    """GBM log-return std = sigma * sqrt(dt)."""
    sigma, dt = 0.2, 1.0
    x = sample_gbm(1000, 500, sigma=sigma, dt=dt, seed=42)
    expected = sigma * np.sqrt(dt)
    actual = float(np.std(x))
    assert abs(actual - expected) < 0.02


def test_gbm_produces_approximately_normal_returns() -> None:
    """GBM log-returns should be approximately normal (kurtosis near 0)."""
    from neuralmarket.eval.scorecard import compute_scorecard

    x = sample_gbm(100, 500, sigma=0.2, seed=42)
    r = compute_scorecard(x.flatten())
    assert abs(r.excess_kurtosis) < 0.5


def test_gbm_no_spurious_clustering() -> None:
    """GBM should not show meaningful volatility clustering."""
    from neuralmarket.eval.scorecard import compute_scorecard

    x = sample_gbm(100, 500, sigma=0.2, seed=42)
    r = compute_scorecard(x.flatten())
    assert abs(r.sq_return_acf[1]) < 0.15


# ── calibration ──────────────────────────────────────────────────────


def test_calibrate_gbm_recovers_known_parameters() -> None:
    """Calibrated sigma/mu recover a known GBM within sampling tolerance."""
    from neuralmarket.baselines.gbm import calibrate_gbm

    mu, sigma, dt = 0.10, 0.25, 1.0 / 252.0
    returns = sample_gbm(1000, 252, mu=mu, sigma=sigma, dt=dt, seed=42).ravel()
    fit = calibrate_gbm(returns, dt=dt)
    assert fit.sigma == pytest.approx(sigma, rel=0.05)
    assert fit.mu == pytest.approx(mu, abs=0.5)
    assert fit.n_observations == 1000 * 252


def test_calibrate_gbm_deterministic() -> None:
    from neuralmarket.baselines.gbm import calibrate_gbm

    rng = np.random.default_rng(11)
    returns = rng.standard_normal(500) * 0.01
    first = calibrate_gbm(returns, dt=1 / 252)
    second = calibrate_gbm(returns, dt=1 / 252)
    assert first == second


def test_calibrate_gbm_rejects_degenerate() -> None:
    from neuralmarket.baselines.gbm import calibrate_gbm

    with pytest.raises(ValueError, match="sigma"):
        calibrate_gbm(np.zeros(100), dt=1.0)
    with pytest.raises(ValueError, match="dt"):
        calibrate_gbm(np.ones(100) * 0.01, dt=0.0)
    with pytest.raises(ValueError, match="NaN"):
        calibrate_gbm(np.array([0.01, np.nan] * 50), dt=1.0)
