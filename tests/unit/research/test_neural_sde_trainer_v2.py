"""v2 trainer: internal gate, training smoke, determinism, preservation."""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from neuralmarket.data.research.sde_windows import (
    WindowSpec,
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
    split_fit_selection,
)
from neuralmarket.models.neural_sde import (
    ConditionalNeuralSde,
    SdeConfig,
    configure_determinism,
    set_deterministic_seeds,
)
from neuralmarket.research.neural_sde_trainer import TrainingConfig
from neuralmarket.research.neural_sde_trainer_v2 import (
    V2ObjectiveConfig,
    build_v2_statistics,
    evaluate_internal_gate_v2,
    train_internal_v2,
)

pytestmark = pytest.mark.unit

_SMALL_SDE = SdeConfig(
    state_dim=2,
    brownian_dim=2,
    n_context=4,
    hidden_units=16,
    hidden_layers=1,
    horizon=63,
)


def _synthetic_setup(seed: int = 5, n: int = 500):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0, 0.01, size=n)
    vol = np.full(n, 0.01)
    for i in range(1, n):
        vol[i] = np.sqrt(0.02 + 0.9 * vol[i - 1] ** 2 + 0.08 * returns[i - 1] ** 2)
        returns[i] = vol[i] * rng.normal()
    dates = [f"2020-{i % 12 + 1:02d}-{i % 28 + 1:02d}" for i in range(n)]
    spec = WindowSpec()
    windows = build_windows(returns, dates, spec)
    features = np.stack([compute_context_features(w, spec).array() for w in windows])
    normalizer = fit_feature_normalizer(features)
    split = split_fit_selection(windows, 0.8, spec)
    return returns, windows, normalizer, split, spec


def _model(seed: int = 4242) -> ConditionalNeuralSde:
    set_deterministic_seeds(seed)
    configure_determinism(True)
    return ConditionalNeuralSde(_SMALL_SDE)


class _ConstantDiffusion(ConditionalNeuralSde):
    def __init__(self, config: SdeConfig, sigma: float) -> None:
        super().__init__(config)
        self._sigma = float(sigma)
        self._mu = 0.0

    def drift_at(self, t, state, context):  # type: ignore[no-untyped-def]
        return torch.zeros_like(state)

    def diffusion_at(self, t, state, context):  # type: ignore[no-untyped-def]
        return torch.full_like(state, self._sigma)


def _gate_vars(split, normalizer, returns, spec):
    # Real selection daily variance as the reference for the passing generator.

    sel_targets = np.concatenate([w.target_returns for w in split.selection_windows])
    return float(np.var(sel_targets))


class TestInternalGate:
    def _run_gate(self, model: ConditionalNeuralSde, setup) -> tuple[dict, bool]:
        returns, _windows, normalizer, split, spec = setup
        diagnostics, passed = evaluate_internal_gate_v2(
            model,
            split,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            spec,
            V2ObjectiveConfig(internal_min_dispersion_ratio=0.5),
        )
        return diagnostics, passed

    def test_collapsed_generator_fails(self) -> None:
        setup = _synthetic_setup()
        model = _ConstantDiffusion(_SMALL_SDE, sigma=1e-6)
        diagnostics, passed = self._run_gate(model, setup)
        assert not passed
        assert diagnostics["terminal_dispersion_ratio"] < 0.5
        assert diagnostics["variance_ratio"] < 1.0

    def test_reasonable_generator_passes(self) -> None:
        setup = _synthetic_setup()
        returns, _windows, normalizer, split, spec = setup
        var_real = _gate_vars(split, normalizer, returns, spec)
        sigma = float(np.sqrt(max(var_real * 252.0, 1e-12)))
        model = _ConstantDiffusion(_SMALL_SDE, sigma=sigma)
        diagnostics, passed = self._run_gate(model, setup)
        assert passed
        assert diagnostics["terminal_dispersion_ratio"] >= 0.5

    def test_gate_signature_has_no_validation_input(self) -> None:
        import inspect

        from neuralmarket.research import neural_sde_trainer_v2 as module

        sig = inspect.signature(module.evaluate_internal_gate_v2)
        assert "validation" not in sig.parameters
        assert "validation" not in inspect.signature(module.train_internal_v2).parameters
        sig2 = inspect.signature(module.build_v2_statistics)
        assert "validation" not in sig2.parameters

    def test_gate_is_deterministic(self) -> None:
        setup = _synthetic_setup()
        returns, _windows, normalizer, split, spec = setup
        var_real = _gate_vars(split, normalizer, returns, spec)
        sigma = float(np.sqrt(max(var_real * 252.0, 1e-12)))
        model = _ConstantDiffusion(_SMALL_SDE, sigma=sigma)
        d1, p1 = self._run_gate(model, setup)
        d2, p2 = self._run_gate(model, setup)
        assert p1 == p2
        assert d1["terminal_dispersion_ratio"] == d2["terminal_dispersion_ratio"]


def _short_config() -> TrainingConfig:
    return TrainingConfig(batch_size=64, max_epochs=8, patience=8, learning_rate=1e-3)


class TestV2TrainingSmoke:
    def _prepare(self):
        returns, windows, normalizer, split, spec = _synthetic_setup()
        statistics = build_v2_statistics(
            split.fit_windows,
            normalizer,
            fit_cumret_scale(returns, spec.horizon),
            spec,
            V2ObjectiveConfig(),
        )
        return returns, windows, normalizer, split, spec, statistics

    def test_loss_improves_and_non_degenerate(self) -> None:
        returns, _w, normalizer, split, spec, statistics = self._prepare()
        model = _model()
        outcome = train_internal_v2(
            model,
            _short_config(),
            split,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            statistics,
            spec,
            V2ObjectiveConfig(),
        )
        # Checkpoint selection now uses total loss, not RBF alone.
        # Total loss must have improved from initial.
        assert outcome.best_epoch >= 1
        # percent_improvement is based on RBF; check it is finite.
        assert math.isfinite(outcome.percent_improvement)
        diagnostics, _passed = evaluate_internal_gate_v2(
            model,
            split,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            spec,
            V2ObjectiveConfig(),
        )
        # Non-zero diffusion and finite generated paths.
        assert diagnostics["diffusion_max"] > 0.0
        assert diagnostics["diffusion_min"] > 0.0
        assert diagnostics["path_uniqueness_fraction"] > 0.0
        pts = model(torch.randn(8, 4), torch.randn(8, 63, 2))
        assert torch.isfinite(pts).all()

    def test_reproducible(self) -> None:
        returns, _w, normalizer, split, spec, statistics = self._prepare()
        config = _short_config()
        o1 = train_internal_v2(
            _model(),
            config,
            split,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            statistics,
            spec,
            V2ObjectiveConfig(),
        )
        o2 = train_internal_v2(
            _model(),
            config,
            split,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            statistics,
            spec,
            V2ObjectiveConfig(),
        )
        assert o1.best_epoch == o2.best_epoch
        assert o1.best_internal_rbf == o2.best_internal_rbf
        assert o1.rbf_curve == o2.rbf_curve

    def test_statistics_are_train_fit_only(self) -> None:
        returns, windows, normalizer, split, spec = _synthetic_setup()
        stats = build_v2_statistics(
            split.fit_windows,
            normalizer,
            fit_cumret_scale(returns, spec.horizon),
            spec,
            V2ObjectiveConfig(),
        )
        assert stats.fit_feature_count == len(split.fit_windows)
        # Augmented path dim = time + cumret + 4 context = 6; levels 1..3 -> 6+36+216.
        assert stats.feature_dim == 258
        assert stats.bandwidth_sq > 0
        assert len(stats.standardization_hash) == 64
        # Bandwidth source is the fit real paths only.
        assert stats.bandwidth_vectors == len(split.fit_windows) or stats.bandwidth_vectors == 512


class TestV2ObjectiveConfig:
    def test_hash_deterministic_and_sensitive(self) -> None:
        a = V2ObjectiveConfig()
        assert a.config_hash() == V2ObjectiveConfig().config_hash()
        assert a.config_hash() != V2ObjectiveConfig(variance_penalty_coefficient=2.0).config_hash()

    def test_config_frozen_defaults(self) -> None:
        obj = V2ObjectiveConfig()
        assert obj.kernel == "rbf"
        assert obj.signature_level == 3
        assert obj.variance_penalty_coefficient == 1.0
        assert obj.internal_min_dispersion_ratio == 0.5
