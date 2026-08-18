"""Production-shaped v3 signature neural-SDE run on frozen local data.

Runs the v3 experiment with a short deterministic config and requires
deterministic reproducibility.  Verifies every frozen binding, v1/v2
preservation (no mutation), the internal-gate-before-validation ordering,
and the objective/gate fields of the sealed artifact.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from neuralmarket.research.neural_sde_experiment_v3 import (
    NeuralSdeExperimentV3Artifact,
    run_neural_sde_experiment_v3,
)

pytestmark = [pytest.mark.integration]

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = _ROOT / "data/manifests/research_development_inventory_v1.json"
_BENCHMARK = _ROOT / "data/processed/research/benchmark/empirical_benchmark_v1.json"
_SUITE = _ROOT / "data/processed/research/benchmark/simulator_baseline_suite_v1.json"
_CONFIG = _ROOT / "configs/research/neural_sde_signature_v3_smoke.yaml"
_V1_CONFIG = _ROOT / "configs/research/neural_sde_signature_v1.yaml"
_V2_CONFIG = _ROOT / "configs/research/neural_sde_signature_v2.yaml"
_V1_ARTIFACT = (
    _ROOT
    / "data/processed/research/model/signature-neural-sde-v1"
    / "3857055bb83bea7b"
    / "neural_sde_signature_v1_experiment.json"
)
_V1_CKPT = (
    _ROOT
    / "data/processed/research/model/signature-neural-sde-v1"
    / "3857055bb83bea7b"
    / "checkpoint.pt"
)
_V2_ARTIFACT = (
    _ROOT
    / "data/processed/research/model/signature-neural-sde-v2"
    / "727520d44f381ba2"
    / "neural_sde_signature_v2_experiment.json"
)
_V2_CKPT = (
    _ROOT
    / "data/processed/research/model/signature-neural-sde-v2"
    / "727520d44f381ba2"
    / "checkpoint.pt"
)
_RAW_ROOT = _ROOT / "data/raw/databento"
_PROCESSED_ROOT = _ROOT / "data/processed"

_FROZEN_INVENTORY_HASH = "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"
_FROZEN_BENCHMARK_HASH = "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"
_FROZEN_METRIC_SPEC_HASH = "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"
_FROZEN_SUITE_HASH = "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"
_FROZEN_V1_CHECKPOINT_HASH = "01fce85964335e592da88f72fd23c54d878fa84acc3c4fd1d3e239632d0411e8"
_FROZEN_V2_CHECKPOINT_HASH = "262d8358f4dfbb9615c39e16936ecc92475aa395d226c8661370c4ace92b1b32"

_AVAILABLE = (
    _INVENTORY.is_file()
    and _BENCHMARK.is_file()
    and _SUITE.is_file()
    and _RAW_ROOT.is_dir()
    and _V1_ARTIFACT.is_file()
    and _V2_ARTIFACT.is_file()
)
if not _AVAILABLE:
    pytestmark.append(pytest.mark.skipif(True, reason="frozen research inputs are not present"))


def _v1_hashes() -> dict[str, str]:
    return {
        "config": hashlib.sha256(_V1_CONFIG.read_bytes()).hexdigest(),
        "artifact": hashlib.sha256(_V1_ARTIFACT.read_bytes()).hexdigest(),
        "checkpoint": hashlib.sha256(_V1_CKPT.read_bytes()).hexdigest(),
    }


def _v2_hashes() -> dict[str, str]:
    return {
        "config": hashlib.sha256(_V2_CONFIG.read_bytes()).hexdigest(),
        "artifact": hashlib.sha256(_V2_ARTIFACT.read_bytes()).hexdigest(),
        "checkpoint": hashlib.sha256(_V2_CKPT.read_bytes()).hexdigest(),
    }


def _run(tmp_path: Path, index: int) -> NeuralSdeExperimentV3Artifact:
    return run_neural_sde_experiment_v3(
        config_path=_CONFIG,
        inventory_path=_INVENTORY,
        benchmark_path=_BENCHMARK,
        suite_path=_SUITE,
        v1_artifact_path=_V1_ARTIFACT,
        v2_artifact_path=_V2_ARTIFACT,
        raw_root=_RAW_ROOT,
        processed_root=_PROCESSED_ROOT,
        output_root=tmp_path / f"v3_model_run{index}",
        report_path=tmp_path / f"v3_run{index}.json",
    )


@pytest.fixture(scope="module")
def v3_artifact(tmp_path_factory: pytest.TempPathFactory) -> NeuralSdeExperimentV3Artifact:
    root = tmp_path_factory.mktemp("neural_sde_v3_integration")
    return _run(root, 0)


@pytest.fixture(scope="module")
def v3_artifact_second(
    tmp_path_factory: pytest.TempPathFactory,
) -> NeuralSdeExperimentV3Artifact:
    root = tmp_path_factory.mktemp("neural_sde_v3_integration_2")
    return _run(root, 1)


class TestV1V2Preservation:
    def test_v1_hashes_unchanged_after_v3_runs(
        self, v3_artifact: NeuralSdeExperimentV3Artifact
    ) -> None:
        before = _v1_hashes()
        _ = v3_artifact
        after = _v1_hashes()
        assert before == after
        assert v3_artifact.v1_preservation["v1_checkpoint_sha256"] == _FROZEN_V1_CHECKPOINT_HASH

    def test_v2_hashes_unchanged_after_v3_runs(
        self, v3_artifact: NeuralSdeExperimentV3Artifact
    ) -> None:
        before = _v2_hashes()
        _ = v3_artifact
        after = _v2_hashes()
        assert before == after
        assert v3_artifact.v2_preservation["v2_checkpoint_sha256"] == _FROZEN_V2_CHECKPOINT_HASH


class TestV3Determinism:
    def test_two_runs_identical_except_provenance_and_paths(
        self,
        v3_artifact: NeuralSdeExperimentV3Artifact,
        v3_artifact_second: NeuralSdeExperimentV3Artifact,
    ) -> None:
        assert v3_artifact.experiment_id == v3_artifact_second.experiment_id
        assert v3_artifact.artifact_hash == v3_artifact_second.artifact_hash
        training_a = dict(v3_artifact.training)
        training_b = dict(v3_artifact_second.training)
        training_a.pop("training_curve_artifact", None)
        training_b.pop("training_curve_artifact", None)
        assert training_a == training_b
        assert v3_artifact.internal_gate == v3_artifact_second.internal_gate
        assert v3_artifact.objective_definition == v3_artifact_second.objective_definition
        f1 = v3_artifact.model_dump(mode="json", by_alias=True)
        f2 = v3_artifact_second.model_dump(mode="json", by_alias=True)
        for f in (f1, f2):
            f.pop("provenance")
            f["training"].pop("training_curve_artifact", None)
            f["checkpoint"].pop("path")
        assert f1 == f2


class TestV3Contract:
    def test_frozen_bindings(self, v3_artifact: NeuralSdeExperimentV3Artifact) -> None:
        assert v3_artifact.inventory_hash == _FROZEN_INVENTORY_HASH
        assert v3_artifact.benchmark_hash == _FROZEN_BENCHMARK_HASH
        assert v3_artifact.metric_spec_hash == _FROZEN_METRIC_SPEC_HASH
        assert v3_artifact.baseline_suite_hash == _FROZEN_SUITE_HASH

    def test_objective_definition(self, v3_artifact: NeuralSdeExperimentV3Artifact) -> None:
        obj = v3_artifact.objective_definition
        assert obj["kernel"] == "rbf"
        assert obj["signature_level"] == 3
        assert obj["representation"] == "lead-lag (standard discrete interleaving)"
        assert obj["augmented_path_dim"] == 7  # 3 + n_context(4)
        assert obj["bandwidth_sq"] > 0
        assert len(obj["standardization_hash"]) == 64
        assert obj["variance_penalty_coefficient"] == 1.0

    def test_training_recorded(self, v3_artifact: NeuralSdeExperimentV3Artifact) -> None:
        t = v3_artifact.training
        assert t["best_internal_rbf"] < t["initial_internal_rbf"]
        assert t["percent_improvement"] > 0
        assert t["best_epoch"] >= 1

    def test_internal_gate_present_and_has_all_criteria(
        self, v3_artifact: NeuralSdeExperimentV3Artifact
    ) -> None:
        gate = v3_artifact.internal_gate
        for key in (
            "generated_daily_variance",
            "real_daily_variance",
            "variance_ratio",
            "terminal_dispersion_ratio",
            "path_uniqueness_fraction",
            "generated_return_acf1",
            "real_return_acf1",
            "return_acf1_abs_diff",
            "drift_increment_rms",
            "diffusion_increment_rms",
            "drift_diffusion_rms_ratio",
            "criterion_results",
            "gate_passed",
        ):
            assert key in gate
        cr = gate["criterion_results"]
        criteria = (
            "variance_ratio",
            "dispersion_ratio",
            "uniqueness",
            "acf1_agreement",
            "drift_diffusion_ratio",
        )
        for crit in criteria:
            assert crit in cr
            assert cr[crit] in (True, False)

    def test_validation_only_after_gate_or_audit(
        self, v3_artifact: NeuralSdeExperimentV3Artifact
    ) -> None:
        if v3_artifact.internal_gate["gate_passed"]:
            assert v3_artifact.evaluation
            assert "contract" in v3_artifact.evaluation
            assert not v3_artifact.data_value_of_information
        else:
            assert not v3_artifact.evaluation
            assert v3_artifact.data_value_of_information.get("candidates")

    def test_v2_architecture_preserved(self, v3_artifact: NeuralSdeExperimentV3Artifact) -> None:
        m = v3_artifact.model
        assert m["state_dim"] == 2
        assert m["brownian_dim"] == 2
        assert m["representation"] == "lead-lag (standard discrete interleaving)"

    def test_final_test_isolation(self, v3_artifact: NeuralSdeExperimentV3Artifact) -> None:
        payload = v3_artifact.model_dump_json()
        assert "2023-07" not in payload and "2024-" not in payload

    def test_tamper_rejected(self, v3_artifact: NeuralSdeExperimentV3Artifact) -> None:
        tampered = v3_artifact.model_copy(update={"training_series_sha256": "0" * 64})
        with pytest.raises(ValueError, match="hash mismatch"):
            NeuralSdeExperimentV3Artifact.model_validate(
                tampered.model_dump(mode="json", by_alias=True)
            )


class TestZeroProviderProof:
    def test_v3_modules_never_touch_provider(self) -> None:
        import inspect

        from neuralmarket.models import leadlag as leadlag_module
        from neuralmarket.research import neural_sde_experiment_v3 as exp_module
        from neuralmarket.research import neural_sde_trainer_v3 as trainer_module

        for module in (leadlag_module, exp_module, trainer_module):
            source = inspect.getsource(module)
            assert "dotenv" not in source
            assert "DATABENTO_API_KEY" not in source
            assert "databento.Historical" not in source
            assert "__import__('requests')" not in source
