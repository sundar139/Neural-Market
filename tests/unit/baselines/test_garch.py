from __future__ import annotations

import numpy as np
import pytest

from neuralmarket.baselines.garch import (
    calibrate_gjr_garch,
    gjr_garch_loglikelihood,
    gjr_garch_variance,
    sample_gjr_garch,
)

pytestmark = pytest.mark.unit

_HAND = {"mu": 0.0, "omega": 1e-6, "alpha": 0.05, "gamma": 0.10, "beta": 0.90}


def _training() -> np.ndarray:
    """A GJR-flavoured synthetic training series with leverage and clustering."""
    rng = np.random.default_rng(3)
    n = 925
    returns = np.empty(n)
    h = 1e-4
    previous = 0.0
    for t in range(n):
        h = 2e-6 + (0.05 + 0.10 * (previous < 0)) * previous**2 + 0.88 * h
        previous = float(np.sqrt(h) * rng.standard_normal())
        returns[t] = 0.0004 + previous
    return returns


class TestVarianceRecursion:
    def test_matches_hand_computed_example(self) -> None:
        returns = np.array([0.01, -0.02, 0.03])
        variance = gjr_garch_variance(returns, initial_variance=1e-4, **_HAND)
        # h1 = 1e-4 (initialization)
        # h2 = 1e-6 + 0.05*(0.01)^2         + 0.9*1e-4    = 9.6e-5
        # h3 = 1e-6 + (0.05+0.10)*(-0.02)^2 + 0.9*9.6e-5  = 1.474e-4
        assert variance.shape == (3,)
        assert variance[0] == pytest.approx(1e-4, rel=1e-12)
        assert variance[1] == pytest.approx(9.6e-5, rel=1e-12)
        assert variance[2] == pytest.approx(1.474e-4, rel=1e-12)

    def test_asymmetry_is_active(self) -> None:
        up = gjr_garch_variance(np.array([0.02, 0.0]), initial_variance=1e-4, **_HAND)
        down = gjr_garch_variance(np.array([-0.02, 0.0]), initial_variance=1e-4, **_HAND)
        assert down[1] > up[1]

    def test_variance_is_positive_and_finite(self) -> None:
        variance = gjr_garch_variance(_training(), initial_variance=1e-4, **_HAND)
        assert np.all(variance > 0)
        assert np.all(np.isfinite(variance))

    def test_loglikelihood_is_finite_and_seed_free(self) -> None:
        returns = _training()
        first = gjr_garch_loglikelihood(returns, initial_variance=1e-4, **_HAND)
        second = gjr_garch_loglikelihood(returns, initial_variance=1e-4, **_HAND)
        assert np.isfinite(first)
        assert first == second


class TestParameterDomain:
    @pytest.mark.parametrize(
        "override",
        [
            {"omega": 0.0},
            {"omega": -1e-6},
            {"alpha": -0.01},
            {"beta": -0.01},
            {"gamma": -0.20},  # alpha + gamma < 0
        ],
    )
    def test_invalid_parameters_rejected(self, override: dict[str, float]) -> None:
        params = {**_HAND, **override}
        with pytest.raises(ValueError, match="parameter"):
            gjr_garch_variance(np.array([0.01, -0.01]), initial_variance=1e-4, **params)

    def test_nonpositive_initial_variance_rejected(self) -> None:
        with pytest.raises(ValueError, match="initial_variance"):
            gjr_garch_variance(np.array([0.01]), initial_variance=0.0, **_HAND)

    def test_nonfinite_returns_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            gjr_garch_variance(np.array([0.01, np.inf]), initial_variance=1e-4, **_HAND)


class TestCalibration:
    def test_deterministic_and_stationary(self) -> None:
        returns = _training()
        first = calibrate_gjr_garch(returns)
        second = calibrate_gjr_garch(returns)
        assert first == second
        assert 0.0 < first.persistence < 1.0
        assert first.parameters.omega > 0
        assert first.parameters.alpha >= 0
        assert first.parameters.beta >= 0
        assert first.parameters.alpha + first.parameters.gamma >= 0

    def test_records_full_specification(self) -> None:
        result = calibrate_gjr_garch(_training())
        assert result.innovation_distribution == "gaussian"
        assert "r_t = mu" in result.mean_equation
        assert "h_t" in result.variance_equation
        assert result.optimizer.startswith("bounded_grid")
        assert result.convergence
        assert result.grid_evaluations > 0
        assert result.n_observations == 925
        assert np.isfinite(result.log_likelihood)
        assert result.log_likelihood == -result.objective

    def test_variance_targeting_matches_sample_variance(self) -> None:
        returns = _training()
        result = calibrate_gjr_garch(returns)
        assert result.unconditional_variance == pytest.approx(float(np.var(returns, ddof=1)))
        implied = result.parameters.omega / (1.0 - result.persistence)
        assert implied == pytest.approx(result.unconditional_variance, rel=1e-9)

    def test_beats_a_symmetric_restriction_on_leveraged_data(self) -> None:
        returns = _training()
        fitted = calibrate_gjr_garch(returns)
        symmetric = gjr_garch_loglikelihood(
            returns,
            initial_variance=fitted.unconditional_variance,
            mu=fitted.parameters.mu,
            omega=fitted.parameters.omega,
            alpha=fitted.parameters.alpha + 0.5 * fitted.parameters.gamma,
            gamma=0.0,
            beta=fitted.parameters.beta,
        )
        assert fitted.log_likelihood > symmetric

    def test_fits_only_the_array_it_is_given(self) -> None:
        returns = _training()
        validation = np.full(274, -7.5)
        assert calibrate_gjr_garch(returns) == calibrate_gjr_garch(
            np.concatenate([returns, validation])[: len(returns)]
        )

    def test_rejects_short_series(self) -> None:
        with pytest.raises(ValueError, match="observations"):
            calibrate_gjr_garch(np.zeros(5) + 0.01)


class TestSimulation:
    def test_deterministic_shape_and_finiteness(self) -> None:
        first = sample_gjr_garch(1024, 63, seed=2039, **_stationary())
        second = sample_gjr_garch(1024, 63, seed=2039, **_stationary())
        assert first.shape == (1024, 63)
        assert np.array_equal(first, second)
        assert np.all(np.isfinite(first))

    def test_different_seed_changes_paths(self) -> None:
        assert not np.array_equal(
            sample_gjr_garch(16, 63, seed=2039, **_stationary()),
            sample_gjr_garch(16, 63, seed=2040, **_stationary()),
        )

    def test_produces_positive_prices(self) -> None:
        from neuralmarket.baselines import simulated_prices

        paths = sample_gjr_garch(64, 63, seed=2039, **_stationary())
        assert (simulated_prices(paths, initial_price=430.0) > 0).all()

    def test_nonstationary_parameters_rejected(self) -> None:
        params = {**_stationary(), "beta": 0.999, "alpha": 0.10, "gamma": 0.10}
        with pytest.raises(ValueError, match="stationar"):
            sample_gjr_garch(4, 5, seed=1, **params)

    def test_clusters_volatility(self) -> None:
        paths = sample_gjr_garch(512, 63, seed=2039, **_stationary())
        absolute = np.abs(paths)
        centered = absolute - absolute.mean(axis=1, keepdims=True)
        numerator = float(np.sum(centered[:, :-1] * centered[:, 1:]))
        denominator = float(np.sum(centered * centered))
        assert numerator / denominator > 0.05


def _stationary() -> dict[str, float]:
    return {"mu": 0.0004, "omega": 2e-6, "alpha": 0.05, "gamma": 0.10, "beta": 0.88}
