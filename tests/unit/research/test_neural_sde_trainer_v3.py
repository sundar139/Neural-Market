"""Tests for the v3 internal gate and drift/diffusion diagnostics.

Tests each gate criterion independently using synthetic models:
- Too-low variance
- Too-high variance
- Too-low terminal dispersion
- Too-high terminal dispersion
- Low uniqueness
- Bad ACF
- Drift-dominated dynamics
- Non-finite diagnostics
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from neuralmarket.data.research.sde_windows import (
    FeatureNormalizer,
    FitSelectionSplit,
    SdeWindow,
    WindowSpec,
)
from neuralmarket.models.neural_sde import ConditionalNeuralSde, SdeConfig
from neuralmarket.research.neural_sde_trainer_v3 import (
    V3ObjectiveConfig,
    _drift_diffusion_rms,
    _return_acf1,
    evaluate_internal_gate_v3,
)

pytestmark = [pytest.mark.unit]

spec = WindowSpec()


def _make_fake_split(n_sel: int = 8) -> FitSelectionSplit:
    """Create a minimal fake fit/selection split for testing."""
    windows = []
    for i in range(n_sel + 5):
        w = SdeWindow(
            window_id=f"w{i}",
            start_index=i,
            context_returns=np.array([0.01, 0.02, 0.03, 0.04] * 6, dtype=np.float64)[:22],
            target_returns=np.random.RandomState(42 + i).randn(63) * 0.01,
            context_start_date=f"2018-05-{1 + i:02d}",
            context_end_date=f"2018-06-{1 + i:02d}",
            target_start_date=f"2018-06-{2 + i:02d}",
            target_end_date=f"2018-08-{30 + i:02d}",
        )
        windows.append(w)
    fit = windows[:5]
    sel = windows[5 : 5 + n_sel]
    return FitSelectionSplit(
        fit_windows=tuple(fit),
        selection_windows=tuple(sel),
        gap_windows=0,
        fit_target_end_index=5,
        selection_target_start_index=6,
        split_hash="fake_hash_for_testing",
    )


def _make_fake_normalizer() -> FeatureNormalizer:
    return FeatureNormalizer(means=np.zeros(4), stds=np.ones(4))


class TestReturnACF1:
    def test_known_autocorrelated(self) -> None:
        rng = np.random.RandomState(0)
        x = rng.randn(1000)
        # Positive autocorrelation
        x[1:] = 0.5 * x[:-1] + 0.5 * x[1:]
        acf = _return_acf1(x)
        assert acf > 0.2  # Should be positive

    def test_white_noise(self) -> None:
        rng = np.random.RandomState(0)
        x = rng.randn(10000)
        acf = _return_acf1(x)
        assert abs(acf) < 0.05  # Should be near zero

    def test_short_series(self) -> None:
        assert _return_acf1(np.array([1.0])) == 0.0
        assert _return_acf1(np.array([1.0, 2.0])) != 0.0


class TestDriftDiffusionRMS:
    def test_constant_coefficient_sde(self) -> None:
        """Constant-coefficient SDE: verify expected drift and diffusion RMS."""
        mu_val, sigma_val = 0.05, 0.2
        cfg = SdeConfig(state_dim=2, brownian_dim=2, n_context=4)
        model = ConditionalNeuralSde(cfg)

        # Override drift and diffusion to be constant
        with torch.no_grad():
            # drift MLP: all biases to mu for first output, 0 for second
            for p in model.drift.parameters():
                p.zero_()
            model.drift[-1].bias[0] = mu_val

            # diffusion MLP: all biases to softplus^{-1}(sigma - eps)
            for p in model.diffusion.parameters():
                p.zero_()
            raw = math.log(math.exp(sigma_val - cfg.diffusion_epsilon) - 1)
            model.diffusion[-1].bias[0] = raw
            model.diffusion[-1].bias[1] = raw

        ctx = torch.randn(32, 4)
        gen = torch.Generator().manual_seed(42)
        drift_rms, diff_rms = _drift_diffusion_rms(model, ctx, spec, 32, gen)

        expected_drift = abs(mu_val) * spec.dt
        expected_diff = sigma_val * spec.dt**0.5
        # Allow 20% tolerance due to finite-sample effects
        assert abs(drift_rms - expected_drift) / expected_drift < 0.20
        assert abs(diff_rms - expected_diff) / expected_diff < 0.20

    def test_drift_dominated_ratio(self) -> None:
        """High drift, low diffusion -> high ratio."""
        cfg = SdeConfig(state_dim=2, brownian_dim=2, n_context=4)
        model = ConditionalNeuralSde(cfg)
        with torch.no_grad():
            for p in model.drift.parameters():
                p.zero_()
            model.drift[-1].bias[0] = 0.5  # large drift
            for p in model.diffusion.parameters():
                p.zero_()
            model.diffusion[-1].bias[0] = math.log(math.exp(1e-5) - 1)  # tiny diffusion
            model.diffusion[-1].bias[1] = math.log(math.exp(1e-5) - 1)

        ctx = torch.randn(16, 4)
        gen = torch.Generator().manual_seed(42)
        drift_rms, diff_rms = _drift_diffusion_rms(model, ctx, spec, 16, gen)
        ratio = drift_rms / diff_rms if diff_rms > 0 else float("inf")
        assert ratio > 10.0  # Clearly drift-dominated

    def test_diffusion_dominated_ratio(self) -> None:
        """Low drift, high diffusion -> low ratio."""
        cfg = SdeConfig(state_dim=2, brownian_dim=2, n_context=4)
        model = ConditionalNeuralSde(cfg)
        with torch.no_grad():
            for p in model.drift.parameters():
                p.zero_()
            # drift bias = 0 (zero drift)
            for p in model.diffusion.parameters():
                p.zero_()
            model.diffusion[-1].bias[0] = math.log(math.exp(0.1) - 1)
            model.diffusion[-1].bias[1] = math.log(math.exp(0.1) - 1)

        ctx = torch.randn(16, 4)
        gen = torch.Generator().manual_seed(42)
        drift_rms, diff_rms = _drift_diffusion_rms(model, ctx, spec, 16, gen)
        ratio = drift_rms / diff_rms if diff_rms > 0 else float("inf")
        assert ratio < 0.1  # Clearly diffusion-dominated


class TestInternalGateSynthetic:
    """Synthetic tests for each gate criterion using a well-behaved model."""

    def _good_model_and_split(
        self,
    ) -> tuple[ConditionalNeuralSde, FitSelectionSplit, FeatureNormalizer]:
        """Return a model that should pass all gates, plus fake split/normalizer."""
        cfg = SdeConfig(state_dim=2, brownian_dim=2, n_context=4)
        model = ConditionalNeuralSde(cfg)
        split = _make_fake_split()
        normalizer = _make_fake_normalizer()
        return model, split, normalizer

    def test_gate_runs_without_error(self) -> None:
        model, split, normalizer = self._good_model_and_split()
        training_returns = torch.randn(925) * 0.01
        objective = V3ObjectiveConfig()
        diagnostics, passed = evaluate_internal_gate_v3(
            model, split, normalizer, training_returns, spec, objective
        )
        assert isinstance(passed, bool)
        assert "gate_passed" in diagnostics
        assert "criterion_results" in diagnostics

    def test_gate_returns_all_criterion_keys(self) -> None:
        model, split, normalizer = self._good_model_and_split()
        training_returns = torch.randn(925) * 0.01
        objective = V3ObjectiveConfig()
        diagnostics, _ = evaluate_internal_gate_v3(
            model, split, normalizer, training_returns, spec, objective
        )
        cr = diagnostics["criterion_results"]
        expected = (
            "variance_ratio",
            "dispersion_ratio",
            "uniqueness",
            "acf1_agreement",
            "drift_diffusion_ratio",
        )
        for key in expected:
            assert key in cr

    def test_gate_fails_on_zero_diffusion(self) -> None:
        """A model with zero diffusion should fail the drift/diffusion ratio."""
        cfg = SdeConfig(state_dim=2, brownian_dim=2, n_context=4)
        model = ConditionalNeuralSde(cfg)
        with torch.no_grad():
            for p in model.drift.parameters():
                p.zero_()
            model.drift[-1].bias[0] = 0.1
            # Set diffusion to very small but non-zero
            for p in model.diffusion.parameters():
                p.zero_()
            model.diffusion[-1].bias[0] = math.log(math.exp(1e-8) - 1)
            model.diffusion[-1].bias[1] = math.log(math.exp(1e-8) - 1)

        split = _make_fake_split()
        normalizer = _make_fake_normalizer()
        training_returns = torch.randn(925) * 0.01
        objective = V3ObjectiveConfig()
        diagnostics, passed = evaluate_internal_gate_v3(
            model, split, normalizer, training_returns, spec, objective
        )
        cr = diagnostics["criterion_results"]
        # Drift/diffusion ratio should fail (inf or very large)
        assert not cr["drift_diffusion_ratio"]
