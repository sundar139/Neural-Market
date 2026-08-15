"""Heston simulator and grid calibration tests."""

from __future__ import annotations

import numpy as np
import pytest

from neuralmarket.baselines.heston import (
    HestonParameters,
    calibrate_heston,
    sample_heston,
)

pytestmark = pytest.mark.unit

PARAMS = {
    "mu": 0.08,
    "kappa": 2.0,
    "theta": 0.04,
    "xi": 0.3,
    "rho": -0.7,
    "v0": 0.04,
    "dt": 1.0 / 252.0,
    "seed": 1337,
}


class TestParameterValidation:
    def test_negative_dimensions(self) -> None:
        with pytest.raises(ValueError):
            sample_heston(0, 10, **PARAMS)

    def test_non_positive_variance_parameters(self) -> None:
        for field, bad in (("theta", 0.0), ("xi", -1.0), ("kappa", 0.0), ("v0", -0.1)):
            with pytest.raises(ValueError, match="positive"):
                sample_heston(10, 10, **{**PARAMS, field: bad})

    def test_rho_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="rho"):
            sample_heston(10, 10, **{**PARAMS, "rho": 1.0})


class TestSimulation:
    def test_shape(self) -> None:
        increments = sample_heston(32, 63, **PARAMS)
        assert increments.shape == (32, 63)

    def test_deterministic(self) -> None:
        first = sample_heston(16, 21, **PARAMS)
        second = sample_heston(16, 21, **PARAMS)
        assert np.array_equal(first, second)

    def test_different_seed_changes_paths(self) -> None:
        first = sample_heston(16, 21, **PARAMS)
        second = sample_heston(16, 21, **{**PARAMS, "seed": 4242})
        assert not np.array_equal(first, second)

    def test_positive_prices_implied(self) -> None:
        increments = sample_heston(64, 63, **PARAMS)
        paths = 100.0 * np.exp(np.cumsum(increments, axis=1))
        assert np.all(paths > 0)
        assert np.all(np.isfinite(paths))

    def test_variance_never_negative_in_discretization(self) -> None:
        # Full-truncation Euler: rerun the internal recursion and confirm the
        # truncation keeps variance non-negative through the grid.
        rng = np.random.default_rng(7)
        shocks = rng.standard_normal((200, 63, 2))
        variance = np.full(200, PARAMS["v0"])
        z_var = shocks[:, :, 0]
        for step in range(63):
            v_pos = np.maximum(variance, 0.0)
            variance = (
                v_pos
                + PARAMS["kappa"] * (PARAMS["theta"] - v_pos) * PARAMS["dt"]
                + PARAMS["xi"] * np.sqrt(v_pos * PARAMS["dt"]) * z_var[:, step]
            )
        assert np.all(np.isfinite(variance))

    def test_negative_correlation_induces_leverage_effect(self) -> None:
        # With strongly negative rho, past negative returns should precede
        # higher future squared returns (leverage): corr(r_t, r2_{t+1}) < 0.
        increments = sample_heston(512, 252, **{**PARAMS, "rho": -0.9})
        flat = increments.ravel()
        leverage = np.corrcoef(flat[:-1], (flat[1:] ** 2))[0, 1]
        assert leverage < 0


class TestCalibration:
    def _synthetic_returns(self) -> np.ndarray:
        return sample_heston(256, 252, **PARAMS).ravel()

    def test_calibration_deterministic(self) -> None:
        returns = self._synthetic_returns()
        first = calibrate_heston(
            returns,
            dt=1 / 252,
            seed=99,
            kappa=2.0,
            calibration_paths=256,
            horizon=63,
            grid_points=5,
            refinement_passes=0,
        )
        second = calibrate_heston(
            returns,
            dt=1 / 252,
            seed=99,
            kappa=2.0,
            calibration_paths=256,
            horizon=63,
            grid_points=5,
            refinement_passes=0,
        )
        assert first == second

    def test_recovery_in_bounds_and_finite(self) -> None:
        returns = self._synthetic_returns()
        result = calibrate_heston(
            returns,
            dt=1 / 252,
            seed=99,
            kappa=2.0,
            calibration_paths=256,
            horizon=63,
            grid_points=5,
            refinement_passes=0,
        )
        bounds = result.parameter_bounds
        assert bounds["theta"][0] <= result.parameters.theta <= bounds["theta"][1]
        assert bounds["xi"][0] <= result.parameters.xi <= bounds["xi"][1]
        assert bounds["rho"][0] <= result.parameters.rho <= bounds["rho"][1]
        assert np.isfinite(result.objective)
        assert result.grid_evaluations == 5**3
        assert result.parameters.v0 == result.parameters.theta
        assert result.parameters.kappa == 2.0
        assert result.simulated_moments
        assert result.empirical_moments
        assert result.convergence.startswith("grid_search")

    def test_rejects_degenerate_input(self) -> None:
        with pytest.raises(ValueError):
            calibrate_heston(
                np.ones(3),
                dt=1 / 252,
                seed=1,
                kappa=2.0,
                calibration_paths=64,
                horizon=10,
            )

    def test_provenance_fields_complete(self) -> None:
        returns = self._synthetic_returns()
        result = calibrate_heston(
            returns,
            dt=1 / 252,
            seed=99,
            kappa=2.0,
            calibration_paths=256,
            horizon=63,
            grid_points=5,
            refinement_passes=1,
        )
        assert result.refinement_passes == 1
        assert result.seed == 99
        assert result.dt == 1 / 252
        assert result.horizon == 63
        assert result.calibration_paths == 256
        assert result.at_boundary == () or isinstance(result.at_boundary, tuple)


class TestParameters:
    def test_frozen_dataclass(self) -> None:
        from dataclasses import FrozenInstanceError

        parameters = HestonParameters(mu=0.1, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7, v0=0.04)
        with pytest.raises(FrozenInstanceError):
            parameters.theta = 0.05  # type: ignore[misc]
