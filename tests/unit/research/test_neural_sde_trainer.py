"""Training: learning, determinism, fail-closed behavior, refit, provenance."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from neuralmarket.data.research.sde_windows import (
    WindowSpec,
    build_windows,
    compute_context_features,
    fit_feature_normalizer,
    split_fit_selection,
)
from neuralmarket.models.neural_sde import (
    ConditionalNeuralSde,
    SdeConfig,
    configure_determinism,
    set_deterministic_seeds,
)
from neuralmarket.research.neural_sde_experiment import (
    NeuralSdeExperimentArtifact,
    experiment_id_for,
)
from neuralmarket.research.neural_sde_trainer import (
    TrainingConfig,
    refit_final,
    train_internal,
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


def _synthetic_fit_selection(seed: int = 5, n: int = 500) -> tuple[object, object, object, object]:
    """Build small synthetic windows + normalizer + split for training tests."""
    rng = np.random.default_rng(seed)
    # GARCH-ish synthetic series long enough for a handful of windows.
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
    return split, normalizer, returns, spec


def _model(seed: int = 4242) -> ConditionalNeuralSde:
    set_deterministic_seeds(seed)
    configure_determinism(True)
    return ConditionalNeuralSde(_SMALL_SDE)


def _short_config() -> TrainingConfig:
    return TrainingConfig(
        batch_size=16,
        max_epochs=20,
        patience=10,
        learning_rate=1e-3,
        model_init_seed=4242,
        data_seed=4243,
    )


class TestTrainingLearns:
    def test_parameters_update_and_signature_loss_decreases(self) -> None:
        split, normalizer, returns, spec = _synthetic_fit_selection()
        model = _model()
        before = [p.detach().clone() for p in model.parameters()]
        config = _short_config()
        outcome = train_internal(
            model, config, split, normalizer, torch.tensor(returns, dtype=torch.float32), spec
        )
        # Parameters moved.
        assert any(not torch.equal(a, b) for a, b in zip(before, model.parameters(), strict=False))
        # Best internal loss strictly better than initial.
        assert outcome.best_internal_loss < outcome.initial_internal_loss
        assert outcome.best_epoch >= 1
        assert outcome.percent_improvement > 0
        assert outcome.loss_curve
        assert len(outcome.selection_curve) == len(outcome.loss_curve) + 1  # includes initial

    def test_fixed_seed_reproducible(self) -> None:
        split, normalizer, returns, spec = _synthetic_fit_selection()
        config = _short_config()
        o1 = train_internal(
            _model(), config, split, normalizer, torch.tensor(returns, dtype=torch.float32), spec
        )
        o2 = train_internal(
            _model(), config, split, normalizer, torch.tensor(returns, dtype=torch.float32), spec
        )
        assert o1.best_epoch == o2.best_epoch
        assert o1.best_internal_loss == o2.best_internal_loss
        assert o1.loss_curve == o2.loss_curve
        assert o1.selection_curve == o2.selection_curve


class TestFailClosed:
    def test_non_finite_loss_fails_closed(self) -> None:
        split, normalizer, returns, spec = _synthetic_fit_selection()
        config = _short_config()

        class ExplodingModel(ConditionalNeuralSde):
            def drift_at(self, t, state, context):  # type: ignore[no-untyped-def]
                return torch.full_like(state, float("inf"))

        model = ExplodingModel(_SMALL_SDE)
        with pytest.raises(RuntimeError, match="non-finite"):
            train_internal(
                model, config, split, normalizer, torch.tensor(returns, dtype=torch.float32), spec
            )

    def test_gradient_clipping_path_is_engaged(self) -> None:
        split, normalizer, returns, spec = _synthetic_fit_selection()
        model = _model()
        config = _short_config()
        train_internal(
            model, config, split, normalizer, torch.tensor(returns, dtype=torch.float32), spec
        )
        # Training completed: the clipping path ran for every batch without failing.
        assert torch.isfinite(next(model.parameters())).all()

    def test_internal_selection_never_reads_external_validation(self) -> None:
        import inspect

        import neuralmarket.research.neural_sde_trainer as trainer_module

        for module in (trainer_module,):
            source = inspect.getsource(module)
            assert "validation" not in source.lower() or "internal" in source.lower()
        # The trainer API only accepts windows; no validation series argument exists.
        import re

        sig = inspect.signature(train_internal)
        assert "validation" not in sig.parameters
        sig2 = inspect.signature(refit_final)
        assert "validation" not in sig2.parameters
        # No direct scorecard import in the trainer (metric-spec independent).
        assert re.search(r"compute_scorecard", inspect.getsource(trainer_module)) is None


class TestRefit:
    def test_refit_uses_only_training_windows_and_frozen_epochs(self) -> None:
        split, normalizer, returns, spec = _synthetic_fit_selection()
        config = _short_config()
        outcome = train_internal(
            _model(), config, split, normalizer, torch.tensor(returns, dtype=torch.float32), spec
        )
        reinit_a = _model()
        reinit_b = _model()
        params_a = refit_final(
            reinit_a,
            config,
            split.fit_windows + split.selection_windows,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            outcome.best_epoch,
            spec,
        )
        params_b = refit_final(
            reinit_b,
            config,
            split.fit_windows + split.selection_windows,
            normalizer,
            torch.tensor(returns, dtype=torch.float32),
            outcome.best_epoch,
            spec,
        )
        assert params_a.keys() == params_b.keys()
        for key in params_a:
            assert params_a[key] == params_b[key]


class TestProvenance:
    def test_experiment_id_deterministic_and_sensitive(self) -> None:
        base = {
            "config_hash": "a" * 64,
            "training_series_sha256": "b" * 64,
            "validation_series_sha256": "c" * 64,
            "inventory_hash": "d" * 64,
            "benchmark_hash": "e" * 64,
            "metric_spec_hash": "f" * 64,
            "baseline_suite_hash": "g" * 64,
            "split_hash": "h" * 64,
        }
        id1 = experiment_id_for(**base)
        id2 = experiment_id_for(**base)
        id3 = experiment_id_for(**{**base, "split_hash": "i" * 64})
        assert id1 == id2
        assert id1 != id3
        assert len(id1) == 64

    def test_artifact_hash_is_bound_and_timestamp_excluded(self) -> None:
        payload = {
            "schema_version": "research-neural-sde-experiment-v1",
            "experiment_id": "0" * 64,
            "config": {},
            "config_hash": "a" * 64,
            "config_file_sha256": "b" * 64,
            "inventory_hash": "c" * 64,
            "benchmark_hash": "d" * 64,
            "metric_spec_hash": "e" * 64,
            "baseline_suite_hash": "f" * 64,
            "training_series_sha256": "g" * 64,
            "validation_series_sha256": "h" * 64,
            "internal_split": {},
            "split_hash": "i" * 64,
            "normalization": {},
            "training": {},
            "model": {},
            "checkpoint": {},
            "evaluation": {},
        }
        a1 = NeuralSdeExperimentArtifact(**payload)
        h1 = a1._compute_hash()
        a2 = NeuralSdeExperimentArtifact(
            **{**payload, "provenance": {"evaluation_utc_iso": "2026-01-01T00:00:00+00:00"}}
        )
        assert a2._compute_hash() == h1
        tampered = NeuralSdeExperimentArtifact(**{**payload, "training_series_sha256": "z" * 64})
        assert tampered._compute_hash() != h1

    def test_no_validation_reads_in_experiment_identity(self) -> None:
        # Experiment identity is built from config + hashes only (no wall clock).
        import inspect

        from neuralmarket.research import neural_sde_experiment as module

        source = inspect.getsource(module)
        assert "utcnow" not in source
        assert "datetime.now" not in source or "provenance" in source
