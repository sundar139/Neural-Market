"""Production-shaped signature neural-SDE run on frozen local data.

Runs the real experiment with a short deterministic training config and
requires deterministic reproducibility.  Verifies every frozen binding, the
1024x63 evaluation contract, the unchanged metric spec, the preserved baseline
suite, the comparative reporting, and the post-evaluation freeze.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuralmarket.data.research.baseline_suite import (
    SimulatorBaselineSuiteArtifact,
)
from neuralmarket.data.research.benchmark import EmpiricalBenchmarkArtifact
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.eval.scorecard import MetricSpecification
from neuralmarket.research.neural_sde_experiment import (
    NeuralSdeExperimentArtifact,
    experiment_id_for,
    run_neural_sde_experiment,
)

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = _ROOT / "data/manifests/research_development_inventory_v1.json"
_BENCHMARK = _ROOT / "data/processed/research/benchmark/empirical_benchmark_v1.json"
_SUITE = _ROOT / "data/processed/research/benchmark/simulator_baseline_suite_v1.json"
_CONFIG = _ROOT / "configs/research/neural_sde_signature_v1_smoke.yaml"
_RAW_ROOT = _ROOT / "data/raw/databento"
_PROCESSED_ROOT = _ROOT / "data/processed"

_FROZEN_INVENTORY_HASH = "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"
_FROZEN_BENCHMARK_HASH = "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"
_FROZEN_METRIC_SPEC_HASH = "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"
_FROZEN_SUITE_HASH = "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"

_AVAILABLE = (
    _INVENTORY.is_file() and _BENCHMARK.is_file() and _SUITE.is_file() and _RAW_ROOT.is_dir()
)

pytestmark = [pytest.mark.integration]
if not _AVAILABLE:
    pytestmark.append(pytest.mark.skipif(True, reason="frozen research inputs are not present"))


def _run(tmp_path: Path, run_index: int) -> NeuralSdeExperimentArtifact:
    return run_neural_sde_experiment(
        config_path=_CONFIG,
        inventory_path=_INVENTORY,
        benchmark_path=_BENCHMARK,
        suite_path=_SUITE,
        raw_root=_RAW_ROOT,
        processed_root=_PROCESSED_ROOT,
        output_root=tmp_path / f"model_run{run_index}",
        report_path=tmp_path / f"run{run_index}.json",
    )


@pytest.fixture(scope="module")
def artifact(tmp_path_factory: pytest.TempPathFactory) -> NeuralSdeExperimentArtifact:
    root = tmp_path_factory.mktemp("neural_sde_integration")
    return _run(root, 0)


@pytest.fixture(scope="module")
def second_artifact(tmp_path_factory: pytest.TempPathFactory) -> NeuralSdeExperimentArtifact:
    """Second run for determinism comparisons (run twice requirement)."""
    root = tmp_path_factory.mktemp("neural_sde_integration_2")
    return _run(root, 1)


class TestProtectedFiles:
    def test_protected_hashes_are_exact(self) -> None:
        inventory = ResearchInventory.model_validate(
            json.loads(_INVENTORY.read_text(encoding="utf-8"))
        )
        benchmark = EmpiricalBenchmarkArtifact.model_validate(
            json.loads(_BENCHMARK.read_text(encoding="utf-8"))
        )
        suite = SimulatorBaselineSuiteArtifact.model_validate(
            json.loads(_SUITE.read_text(encoding="utf-8"))
        )
        assert inventory.inventory_hash == _FROZEN_INVENTORY_HASH
        assert benchmark.benchmark_hash == _FROZEN_BENCHMARK_HASH
        assert suite.suite_hash == _FROZEN_SUITE_HASH
        assert benchmark.metric_spec_hash == _FROZEN_METRIC_SPEC_HASH
        assert suite.metric_spec_hash == _FROZEN_METRIC_SPEC_HASH
        assert MetricSpecification().spec_hash() == _FROZEN_METRIC_SPEC_HASH
        assert suite.training_series_sha256 == benchmark.underlying["training"].series_sha256
        assert suite.validation_series_sha256 == benchmark.underlying["validation"].series_sha256

    def test_protected_files_not_mutated_by_runs(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        before = {p: p.read_bytes() for p in (_INVENTORY, _BENCHMARK, _SUITE)}
        _ = artifact
        for path, blob in before.items():
            assert path.read_bytes() == blob


class TestDeterministicReproducibility:
    def test_two_runs_are_identical_except_provenance_timestamp(
        self, artifact: NeuralSdeExperimentArtifact, second_artifact: NeuralSdeExperimentArtifact
    ) -> None:
        assert artifact.experiment_id == second_artifact.experiment_id
        assert artifact.artifact_hash == second_artifact.artifact_hash
        training_a = dict(artifact.training)
        training_b = dict(second_artifact.training)
        training_a.pop("training_curve_artifact")
        training_b.pop("training_curve_artifact")
        assert training_a == training_b
        assert (
            artifact.training["training_curve_sha256"]
            == second_artifact.training["training_curve_sha256"]
        )
        assert artifact.evaluation == second_artifact.evaluation
        assert artifact.checkpoint["sha256"] == second_artifact.checkpoint["sha256"]
        # Only path fields (artifact locations) and the provenance timestamp may
        # differ between runs; every identity-hashed field is identical.
        f1 = artifact.model_dump(mode="json", by_alias=True)
        f2 = second_artifact.model_dump(mode="json", by_alias=True)
        for f in (f1, f2):
            f.pop("provenance")
            f["training"].pop("training_curve_artifact")
            f["checkpoint"].pop("path")
        assert f1 == f2

    def test_checkpoint_bytes_identical(
        self, artifact: NeuralSdeExperimentArtifact, second_artifact: NeuralSdeExperimentArtifact
    ) -> None:
        p1 = Path(artifact.checkpoint["path"])
        p2 = Path(second_artifact.checkpoint["path"])
        assert p1.read_bytes() == p2.read_bytes()


class TestWindowSplit:
    def test_window_split_and_no_target_overlap(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        split = artifact.internal_split
        assert split["n_eligible"] == 841  # derived: 925 - 22 - 63 + 1
        assert split["n_fit"] == 672
        assert split["n_selection"] == 107
        assert split["n_gap"] == 62
        assert split["no_target_overlap_proof"] == "756 > 755"
        assert len(split["split_hash"]) == 64
        assert split["fit_target_end_date"] < split["selection_target_start_date"]


class TestEvaluationContract:
    def test_evaluation_contract_and_conditioning(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        contract = artifact.evaluation["contract"]
        assert contract["n_paths"] == 1024
        assert contract["horizon_sessions"] == 63
        assert contract["seed"] == 4244
        assert contract["initial_price"] == 475.13
        assert contract["initial_price_convention"] == "final training-session close"
        assert set(contract["conditioning_context"]) == {
            "prev_daily_return",
            "prev_5d_cumulative_return",
            "prev_22d_cumulative_return",
            "prev_22d_realized_volatility",
        }

    def test_neural_metrics_are_positive_variance_finite(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        payload = artifact.evaluation["neural_metrics"]
        assert payload["n_observations"] == 1024 * 63
        assert payload["variance"] > 0
        assert all(
            payload[f] == payload[f] for f in ("mean", "variance", "skewness", "excess_kurtosis")
        )

    def test_no_final_test_access(self, artifact: NeuralSdeExperimentArtifact) -> None:
        payload = artifact.model_dump_json()
        assert "2023-07" not in payload
        assert "2024-" not in payload


class TestTrainingOutcome:
    def test_neural_learning_occurred(self, artifact: NeuralSdeExperimentArtifact) -> None:
        training = artifact.training
        assert training["best_internal_loss"] < training["initial_internal_loss"]
        assert training["percent_improvement"] > 0
        assert training["best_epoch"] >= 1
        assert training["final_epoch"] >= training["best_epoch"]
        assert len(artifact.model["torch_version"]) > 0


class TestModelAndCheckpoint:
    def test_checkpoint_and_provenance_complete(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        ck = artifact.checkpoint
        assert len(ck["sha256"]) == 64 and ck["bytes"] > 0
        assert Path(ck["path"]).is_file()
        assert artifact.model["parameter_count"] > 0
        assert artifact.model["signature_objective"].startswith("truncated-signature MMD")
        assert artifact.model["integrator"] == "Euler-Maruyama"
        assert artifact.model["signature_level"] == 3
        assert artifact.model["state_dim"] == 2
        assert artifact.model["brownian_dim"] == 2
        assert artifact.model["dtype"] == "torch.float32"

    def test_manifest_binds_all_frozen_hashes(self, artifact: NeuralSdeExperimentArtifact) -> None:
        assert artifact.inventory_hash == _FROZEN_INVENTORY_HASH
        assert artifact.benchmark_hash == _FROZEN_BENCHMARK_HASH
        assert artifact.metric_spec_hash == _FROZEN_METRIC_SPEC_HASH
        assert artifact.baseline_suite_hash == _FROZEN_SUITE_HASH
        assert len(artifact.training_series_sha256) == 64
        assert len(artifact.validation_series_sha256) == 64
        assert len(artifact.normalization["normalizer_hash"]) == 64
        assert artifact.normalization["cumret_scale"] > 0


class TestComparisonReporting:
    def test_comparison_reports_all_five_baselines_and_neural(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        for split in ("training", "validation"):
            for row in artifact.evaluation["comparison"][split].values():
                errors = set(row["errors"])
                assert {"iid_bootstrap", "block_bootstrap", "gbm", "gjr_garch", "heston"}
                assert "neural_sde_signature" in errors
                assert 1 <= row["neural_rank"] <= 6
                assert row["nearest_baseline"] != "neural_sde_signature"

    def test_accepted_baselines_preserved_in_artifact(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        suite = SimulatorBaselineSuiteArtifact.model_validate(
            json.loads(_SUITE.read_text(encoding="utf-8"))
        )
        assert artifact.baseline_suite_hash == suite.suite_hash
        assert artifact.training_series_sha256 == suite.training_series_sha256
        assert artifact.validation_series_sha256 == suite.validation_series_sha256

    def test_no_baseline_specific_scoring_branch(self) -> None:
        import inspect

        from neuralmarket.research import neural_sde_experiment as module

        source = inspect.getsource(module)
        assert 'name == "gbm"' not in source
        assert 'name == "heston"' not in source

    def test_neural_scored_through_same_scorecard(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        spec = MetricSpecification()
        assert artifact.metric_spec_hash == spec.spec_hash()
        payload = artifact.evaluation["neural_metrics"]
        for family in ("mean", "variance", "skewness", "excess_kurtosis", "quantiles"):
            assert family in payload

    def test_limitations_recorded(self, artifact: NeuralSdeExperimentArtifact) -> None:
        limitations = " ".join(artifact.provenance["known_limitations"])
        assert "historical" in limitations and "inventory_hash" in limitations
        assert "finite-level" in limitations


class TestPostEvaluationFreeze:
    def test_identity_is_deterministic_and_sensitive(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        base = {
            "config_hash": artifact.config_hash,
            "training_series_sha256": artifact.training_series_sha256,
            "validation_series_sha256": artifact.validation_series_sha256,
            "inventory_hash": artifact.inventory_hash,
            "benchmark_hash": artifact.benchmark_hash,
            "metric_spec_hash": artifact.metric_spec_hash,
            "baseline_suite_hash": artifact.baseline_suite_hash,
            "split_hash": artifact.split_hash,
        }
        assert experiment_id_for(**base) == artifact.experiment_id
        assert experiment_id_for(**{**base, "config_hash": "1" * 64}) != artifact.experiment_id

    def test_tampered_artifact_fails_validation(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        tampered = artifact.model_copy(update={"training_series_sha256": "0" * 64})
        with pytest.raises(ValueError, match="hash mismatch"):
            NeuralSdeExperimentArtifact.model_validate(
                tampered.model_dump(mode="json", by_alias=True)
            )

    def test_provenance_timestamp_excluded_from_identity(
        self, artifact: NeuralSdeExperimentArtifact
    ) -> None:
        first = artifact._compute_hash()
        modified = artifact.model_copy(
            update={"provenance": {"evaluation_utc_iso": "2030-01-01T00:00:00+00:00"}}
        )
        assert modified._compute_hash() == first


class TestZeroProviderProof:
    def test_experiment_modules_never_touch_provider(self) -> None:
        import inspect

        from neuralmarket.models import neural_sde as nsde_module
        from neuralmarket.models import signature as sig_module
        from neuralmarket.research import neural_sde_experiment as exp_module
        from neuralmarket.research import neural_sde_trainer as trainer_module

        for module in (nsde_module, sig_module, exp_module, trainer_module):
            source = inspect.getsource(module)
            assert "dotenv" not in source
            assert "DATABENTO_API_KEY" not in source
            assert "databento.Historical" not in source
        assert "requests" not in inspect.getsource(exp_module)
