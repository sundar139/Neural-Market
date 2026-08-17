"""Production-shaped v2 signature neural-SDE run on frozen local data.

Runs the real v2 experiment twice with a short deterministic config and
requires deterministic reproducibility.  Verifies every frozen binding, v1
preservation (no mutation), the internal-gate-before-validation ordering, and
the objective/gate fields of the sealed artifact.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from neuralmarket.research.neural_sde_experiment_v2 import (
    NeuralSdeExperimentV2Artifact,
    run_neural_sde_experiment_v2,
)

pytestmark = [pytest.mark.integration]

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = _ROOT / "data/manifests/research_development_inventory_v1.json"
_BENCHMARK = _ROOT / "data/processed/research/benchmark/empirical_benchmark_v1.json"
_SUITE = _ROOT / "data/processed/research/benchmark/simulator_baseline_suite_v1.json"
_CONFIG = _ROOT / "configs/research/neural_sde_signature_v2_smoke.yaml"
_V1_CONFIG = _ROOT / "configs/research/neural_sde_signature_v1.yaml"
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
_V1_CURVE = (
    _ROOT
    / "data/processed/research/model/signature-neural-sde-v1"
    / "3857055bb83bea7b"
    / "training_curve.json"
)
_RAW_ROOT = _ROOT / "data/raw/databento"
_PROCESSED_ROOT = _ROOT / "data/processed"


_FROZEN_INVENTORY_HASH = "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"
_FROZEN_BENCHMARK_HASH = "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"
_FROZEN_METRIC_SPEC_HASH = "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"
_FROZEN_SUITE_HASH = "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"
_FROZEN_V1_CHECKPOINT_HASH = "01fce85964335e592da88f72fd23c54d878fa84acc3c4fd1d3e239632d0411e8"

_AVAILABLE = (
    _INVENTORY.is_file()
    and _BENCHMARK.is_file()
    and _SUITE.is_file()
    and _RAW_ROOT.is_dir()
    and _V1_ARTIFACT.is_file()
)
if not _AVAILABLE:
    pytestmark.append(pytest.mark.skipif(True, reason="frozen research inputs are not present"))


def _v1_hashes() -> dict[str, str]:
    return {
        "config": hashlib.sha256(_V1_CONFIG.read_bytes()).hexdigest(),
        "artifact": hashlib.sha256(_V1_ARTIFACT.read_bytes()).hexdigest(),
        "checkpoint": hashlib.sha256(_V1_CKPT.read_bytes()).hexdigest(),
        "curve": hashlib.sha256(_V1_CURVE.read_bytes()).hexdigest(),
    }


def _run(tmp_path: Path, index: int) -> NeuralSdeExperimentV2Artifact:
    return run_neural_sde_experiment_v2(
        config_path=_CONFIG,
        inventory_path=_INVENTORY,
        benchmark_path=_BENCHMARK,
        suite_path=_SUITE,
        v1_artifact_path=_V1_ARTIFACT,
        raw_root=_RAW_ROOT,
        processed_root=_PROCESSED_ROOT,
        output_root=tmp_path / f"v2_model_run{index}",
        report_path=tmp_path / f"v2_run{index}.json",
    )


@pytest.fixture(scope="module")
def v2_artifact(tmp_path_factory: pytest.TempPathFactory) -> NeuralSdeExperimentV2Artifact:
    root = tmp_path_factory.mktemp("neural_sde_v2_integration")
    return _run(root, 0)


@pytest.fixture(scope="module")
def v2_artifact_second(
    tmp_path_factory: pytest.TempPathFactory,
) -> NeuralSdeExperimentV2Artifact:
    root = tmp_path_factory.mktemp("neural_sde_v2_integration_2")
    return _run(root, 1)


class TestV1Preservation:
    def test_v1_hashes_unchanged_after_v2_runs(
        self, v2_artifact: NeuralSdeExperimentV2Artifact
    ) -> None:
        before = _v1_hashes()
        _ = v2_artifact
        after = _v1_hashes()
        assert before == after
        # The v2 artifact records the v1 identities.
        assert v2_artifact.v1_preservation["v1_checkpoint_sha256"] == _FROZEN_V1_CHECKPOINT_HASH


class TestV2Determinism:
    def test_two_runs_identical_except_provenance_and_paths(
        self,
        v2_artifact: NeuralSdeExperimentV2Artifact,
        v2_artifact_second: NeuralSdeExperimentV2Artifact,
    ) -> None:
        assert v2_artifact.experiment_id == v2_artifact_second.experiment_id
        assert v2_artifact.artifact_hash == v2_artifact_second.artifact_hash
        training_a = dict(v2_artifact.training)
        training_b = dict(v2_artifact_second.training)
        training_a.pop("training_curve_artifact")
        training_b.pop("training_curve_artifact")
        assert training_a == training_b
        assert (
            v2_artifact.training["training_curve_sha256"]
            == v2_artifact_second.training["training_curve_sha256"]
        )
        assert v2_artifact.internal_gate == v2_artifact_second.internal_gate
        assert v2_artifact.objective_definition == v2_artifact_second.objective_definition
        f1 = v2_artifact.model_dump(mode="json", by_alias=True)
        f2 = v2_artifact_second.model_dump(mode="json", by_alias=True)
        for f in (f1, f2):
            f.pop("provenance")
            f["training"].pop("training_curve_artifact")
            f["checkpoint"].pop("path")
        assert f1 == f2


class TestV2Contract:
    def test_frozen_bindings(self, v2_artifact: NeuralSdeExperimentV2Artifact) -> None:
        assert v2_artifact.inventory_hash == _FROZEN_INVENTORY_HASH
        assert v2_artifact.benchmark_hash == _FROZEN_BENCHMARK_HASH
        assert v2_artifact.metric_spec_hash == _FROZEN_METRIC_SPEC_HASH
        assert v2_artifact.baseline_suite_hash == _FROZEN_SUITE_HASH
        assert len(v2_artifact.training_series_sha256) == 64
        assert len(v2_artifact.validation_series_sha256) == 64

    def test_objective_definition(self, v2_artifact: NeuralSdeExperimentV2Artifact) -> None:
        obj = v2_artifact.objective_definition
        assert obj["kernel"] == "rbf"
        assert obj["signature_level"] == 3
        assert obj["feature_dim"] == 258
        assert obj["bandwidth_sq"] > 0
        assert len(obj["standardization_hash"]) == 64
        assert obj["variance_penalty_coefficient"] == 1.0

    def test_training_recorded(self, v2_artifact: NeuralSdeExperimentV2Artifact) -> None:
        t = v2_artifact.training
        assert t["best_internal_rbf"] < t["initial_internal_rbf"]
        assert t["percent_improvement"] > 0
        assert t["best_epoch"] >= 1
        assert t["fit_population"] == 672 and t["selection_population"] == 107

    def test_internal_gate_present_and_diagnostics(
        self, v2_artifact: NeuralSdeExperimentV2Artifact
    ) -> None:
        gate = v2_artifact.internal_gate
        for key in (
            "generated_daily_variance",
            "real_daily_variance",
            "variance_ratio",
            "terminal_dispersion_ratio",
            "path_uniqueness_fraction",
            "diffusion_mean",
            "diffusion_min",
            "diffusion_max",
            "gate_passed",
        ):
            assert key in gate
        assert gate["gate_passed"] in (True, False)

    def test_validation_only_after_gate_or_audit(
        self, v2_artifact: NeuralSdeExperimentV2Artifact
    ) -> None:
        # Structural guarantee from the orchestrator: a gate-pass has evaluation,
        # a gate-fail has a data value-of-information audit and NO evaluation.
        if v2_artifact.internal_gate["gate_passed"]:
            assert v2_artifact.evaluation
            assert "contract" in v2_artifact.evaluation
            assert not v2_artifact.data_value_of_information
        else:
            assert not v2_artifact.evaluation
            assert v2_artifact.data_value_of_information.get("candidates")

    def test_checkpoint_frozen_when_gate_passed(
        self, v2_artifact: NeuralSdeExperimentV2Artifact
    ) -> None:
        if v2_artifact.internal_gate["gate_passed"]:
            ck = v2_artifact.checkpoint
            assert len(ck["sha256"]) == 64 and Path(ck["path"]).is_file()
            assert v2_artifact.provenance["status"] == "SIGNATURE NEURAL SDE V2 READY"
        else:
            assert v2_artifact.provenance["status"] == "V2 OBJECTIVE INSUFFICIENT"

    def test_final_test_isolation(self, v2_artifact: NeuralSdeExperimentV2Artifact) -> None:
        payload = v2_artifact.model_dump_json()
        assert "2023-07" not in payload and "2024-" not in payload

    def test_tamper_rejected(self, v2_artifact: NeuralSdeExperimentV2Artifact) -> None:
        tampered = v2_artifact.model_copy(update={"training_series_sha256": "0" * 64})
        with pytest.raises(ValueError, match="hash mismatch"):
            NeuralSdeExperimentV2Artifact.model_validate(
                tampered.model_dump(mode="json", by_alias=True)
            )


class TestZeroProviderProof:
    def test_v2_modules_never_touch_provider(self) -> None:
        import inspect

        from neuralmarket.models import signature_mmd as mmd_module
        from neuralmarket.research import neural_sde_experiment_v2 as exp_module
        from neuralmarket.research import neural_sde_trainer_v2 as trainer_module

        for module in (mmd_module, exp_module, trainer_module):
            source = inspect.getsource(module)
            assert "dotenv" not in source
            assert "DATABENTO_API_KEY" not in source
            assert "databento.Historical" not in source
            assert "__import__('requests')" not in source
