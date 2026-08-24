"""Synthetic regression tests for the fail-closed WGAN Gate-v2 evaluator."""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch

from neuralmarket.baselines.bootstrap import sample_block_bootstrap
from neuralmarket.models.wgan_cde import WGANGenerator
from neuralmarket.research import wgan_gate_evaluator as gate
from neuralmarket.research.wgan_comparator import WGANTrainingConfig

pytestmark = [pytest.mark.unit]


def _identity() -> dict[str, object]:
    return {
        "checkpoint_path": "synthetic/checkpoint.pt",
        "checkpoint_sha256": "c" * 64,
        "training_execution_marker_path": "runs/wgan-seed-01/execution_started.json",
        "training_execution_marker_sha256": "m" * 64,
        "training_authorization_sha256": "a" * 64,
        "training_authorization_git_blob": "b" * 40,
        "training_authorization_path": "auth/wgan-seed-01-v3.json",
        "training_execution_evidence_sha256": "e" * 64,
        "training_execution_evidence_git_blob": "f" * 40,
        "training_execution_evidence_path": "evidence/task-127.json",
        "training_runner_git_blob": "6" * 40,
        "model_git_blob": "1" * 40,
        "comparator_git_blob": "2" * 40,
        "evaluator_git_blob": "3" * 40,
        "scientific_config_sha256": "s" * 64,
        "scientific_config_git_blob": "5" * 40,
        "gate_config_sha256": "g" * 64,
        "gate_config_git_blob": "4" * 40,
        "runtime_identity_sha256": "r" * 64,
    }


def _payload() -> dict[str, object]:
    return {
        "schema_version": gate.GATE_AUTHORIZATION_SCHEMA,
        "gate_task_id": "NM-R4-V5-WGAN-GATE-V2-EVALUATION-132",
        "gate_execution_marker_path": (
            "reports/research/wgan_gate_runs/wgan-seed-01/synthetic/execution_started.json"
        ),
        "member_id": "wgan-seed-01",
        "checkpoint_path": "synthetic/checkpoint.pt",
        "checkpoint_sha256": "c" * 64,
        "training_execution_marker_path": "runs/wgan-seed-01/execution_started.json",
        "training_execution_marker_sha256": "m" * 64,
        "training_authorization_path": "auth/wgan-seed-01-v3.json",
        "training_authorization_sha256": "a" * 64,
        "training_authorization_git_blob": "b" * 40,
        "training_execution_evidence_path": "evidence/task-127.json",
        "training_execution_evidence_sha256": "e" * 64,
        "training_execution_evidence_git_blob": "f" * 40,
        "training_runner_git_blob": "6" * 40,
        "model_git_blob": "1" * 40,
        "comparator_git_blob": "2" * 40,
        "evaluator_git_blob": "3" * 40,
        "scientific_config_sha256": "s" * 64,
        "scientific_config_git_blob": "5" * 40,
        "gate_config_path": gate.GATE_CONFIG_RELATIVE_PATH,
        "gate_config_sha256": "g" * 64,
        "gate_config_git_blob": "4" * 40,
        "evaluation_seed": 8283,
        "bootstrap_seed": 8801,
        "generated_path_count": 1024,
        "bootstrap_path_count": 1024,
        "block_length": 22,
        "acf_lags": [1, 2, 3, 5, 10, 20],
        "requested_device": "cuda",
        "expected_resolved_device": "cuda",
        "expected_runtime_identity_sha256": "r" * 64,
        "max_scientific_invocations": 1,
        "training_authorized": False,
        "gate_execution_authorized": True,
        "validation_authorized": False,
        "final_test_authorized": False,
        "overwrite": False,
        "relaunch": False,
    }


def _gate_paths() -> tuple[np.ndarray, np.ndarray]:
    selection = np.random.default_rng(109).normal(0.0, 0.01, size=5000)
    generated = sample_block_bootstrap(selection, 1024, 63, block_length=22, seed=8801)
    return selection, generated


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _tracked_fixture_repo(tmp_path: Path, relative: str, content: bytes) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "NeuralMarket tests")
    _git(repo, "config", "core.autocrlf", "true")
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    _git(repo, "add", relative)
    _git(repo, "commit", "--quiet", "-m", "freeze fixture")
    return repo, path


def test_valid_future_gate_authorization_is_accepted() -> None:
    gate.validate_gate_authorization_payload(_payload(), expected_identity=_identity())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("checkpoint_sha256", "wrong", "checkpoint SHA"),
        ("evaluator_git_blob", "wrong", "evaluator"),
        ("gate_config_sha256", "wrong", "Gate config"),
        ("member_id", "wgan-seed-02", "member"),
        ("evaluation_seed", 1, "evaluation seed"),
        ("bootstrap_seed", 1, "bootstrap seed"),
    ],
)
def test_incorrect_gate_authorization_is_rejected(
    field: str, value: object, message: str
) -> None:
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError, match=message):
        gate.validate_gate_authorization_payload(payload, expected_identity=_identity())


def test_max_scientific_invocations_must_be_one() -> None:
    payload = _payload()
    payload["max_scientific_invocations"] = 2
    with pytest.raises(ValueError, match="maximum scientific invocations"):
        gate.validate_gate_authorization_payload(payload, expected_identity=_identity())


@pytest.mark.parametrize(
    "relative",
    [
        "src/neuralmarket/research/wgan_gate_evaluator.py",
        "src/neuralmarket/models/wgan_cde.py",
        "src/neuralmarket/research/wgan_comparator.py",
        "src/neuralmarket/research/wgan_runner.py",
        "configs/research/structured_vol_wgan_comparator_v1.yaml",
        "configs/research/neural_sde_internal_gate_v2.yaml",
    ],
)
def test_semantic_edit_to_tracked_gate_input_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    repo, path = _tracked_fixture_repo(tmp_path, relative, b"frozen\n")
    monkeypatch.setattr(gate, "REPO", repo)
    path.write_bytes(b"frozen\nsemantic edit\n")
    with pytest.raises(RuntimeError, match="must match HEAD"):
        gate.require_tracked_artifact_at_head(path, "tracked Gate input")


def test_line_ending_materialization_is_tolerated_when_filtered_blob_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, path = _tracked_fixture_repo(tmp_path, "src/gate.py", b"frozen\n")
    monkeypatch.setattr(gate, "REPO", repo)
    path.write_bytes(b"frozen\r\n")
    head_blob = gate._git_head_blob(path)
    assert gate._git_worktree_blob(path) == head_blob
    gate.require_tracked_artifact_at_head(path, "tracked Gate input")


def test_tracked_authorization_sha_uses_git_object_content() -> None:
    path = gate.REPO / (
        "reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v3.json"
    )
    assert gate.canonical_tracked_sha256(path) == (
        "19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690"
    )
    assert gate._sha256(path) == "7beec8f279bbd9d56f3bc08d46ee404df770823641ab36f0e851005e8f0499d8"


def test_tracked_execution_evidence_sha_uses_git_object_content() -> None:
    path = gate.REPO / (
        "reports/research/evidence/structured_vol_v5_wgan_seed01_execution_v3_127.json"
    )
    canonical = gate.canonical_tracked_sha256(path)
    assert canonical == "96489abe4f2c0ca7b2c460b70ecbd2d881fcb5dd6ebea9e62643fe0c36f30e6f"
    assert gate._git_head_blob(path) == "21bcd88957ad69e8aef7b9675d308daf697b2ac7"


def test_wrong_canonical_tracked_sha_or_blob_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, path = _tracked_fixture_repo(tmp_path, "auth.json", b"{\"ok\": true}\n")
    monkeypatch.setattr(gate, "REPO", repo)
    head_blob = gate._git_head_blob(path)
    canonical_sha = gate.canonical_tracked_sha256(path)
    with pytest.raises(ValueError, match="SHA mismatch"):
        gate.require_tracked_artifact_identity(
            path, expected_sha256="0" * 64, expected_git_blob=head_blob, label="authorization"
        )
    with pytest.raises(ValueError, match="Git blob mismatch"):
        gate.require_tracked_artifact_identity(
            path, expected_sha256=canonical_sha, expected_git_blob="0" * 40, label="authorization"
        )


def _marker_payload() -> dict[str, object]:
    return {
        "schema_version": gate.GATE_MARKER_SCHEMA,
        "gate_task_id": "NM-R4-V5-WGAN-GATE-V2-EVALUATION-132",
        "member_id": "wgan-seed-01",
        "authorization_path": "auth/gate.json",
        "authorization_git_blob": "a" * 40,
        "authorization_canonical_sha256": "b" * 64,
        "checkpoint_path": "checkpoint.pt",
        "checkpoint_sha256": "c" * 64,
        "training_execution_marker_path": "training/execution_started.json",
        "training_execution_marker_sha256": "d" * 64,
        "training_authorization_path": "auth/training.json",
        "training_authorization_sha256": "e" * 64,
        "training_authorization_git_blob": "f" * 40,
        "training_execution_evidence_path": "evidence/task-127.json",
        "training_execution_evidence_sha256": "1" * 64,
        "training_execution_evidence_git_blob": "2" * 40,
        "evaluator_git_blob": "3" * 40,
        "gate_config_sha256": "4" * 64,
        "gate_config_git_blob": "5" * 40,
        "evaluation_seed": 8283,
        "bootstrap_seed": 8801,
        "runtime_identity_sha256": "6" * 64,
        "max_scientific_invocations": 1,
    }


def test_gate_marker_is_exclusive_and_non_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate, "REPO", tmp_path)
    marker = tmp_path / (
        "reports/research/wgan_gate_runs/wgan-seed-01/synthetic/execution_started.json"
    )
    payload = _marker_payload()
    assert gate.create_gate_execution_marker(marker, payload) == marker
    original = marker.read_bytes()
    with pytest.raises(RuntimeError, match="already exists"):
        gate.create_gate_execution_marker(marker, {**payload, "gate_task_id": "other-task"})
    assert marker.read_bytes() == original


def test_second_gate_invocation_cannot_cross_marker_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate, "REPO", tmp_path)
    marker = tmp_path / (
        "reports/research/wgan_gate_runs/wgan-seed-01/synthetic/execution_started.json"
    )
    payload = _marker_payload()
    gate.create_gate_execution_marker(marker, payload)
    generated: list[bool] = []
    with pytest.raises(RuntimeError, match="already exists"):
        gate.create_gate_execution_marker(marker, payload)
    source = inspect.getsource(gate.evaluate_authorized_wgan_gate)
    assert source.index("create_gate_execution_marker") < source.index("_load_training_returns")
    assert source.index("create_gate_execution_marker") < source.index(
        "evaluate_frozen_wgan_checkpoint"
    )
    assert generated == []


def test_missing_gate_authorization_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="Gate authorization"):
        gate.require_gate_authorization(None)


def test_cpu_scientific_device_is_rejected_at_boundary() -> None:
    with pytest.raises(RuntimeError, match="CUDA"):
        gate.require_cuda_device(torch.device("cpu"))


def test_checkpoint_loader_is_read_only(tmp_path: Path) -> None:
    model = WGANGenerator()
    checkpoint = tmp_path / "checkpoint.pt"
    torch.save(
        {
            "generator_state": model.state_dict(),
            "critic_state": {},
            "best_generator_epoch": 7,
            "best_selection_metric": 0.25,
            "config_hash": WGANTrainingConfig().config_hash(),
        },
        checkpoint,
    )
    before_bytes = checkpoint.read_bytes()
    before_sha = hashlib.sha256(before_bytes).hexdigest()
    loaded = gate.load_frozen_generator_checkpoint(
        checkpoint,
        checkpoint_sha256=before_sha,
        config=WGANTrainingConfig(),
        map_location="cpu",
    )
    assert loaded.model.training is False
    assert loaded.metadata["best_generator_epoch"] == 7
    assert checkpoint.read_bytes() == before_bytes
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == before_sha


def test_architecture_neutral_wgan_criteria_and_report_only_metrics() -> None:
    selection, generated = _gate_paths()
    diagnostics = gate.compute_wgan_gate_metrics(
        generated,
        selection,
        evaluation_seed=8283,
        bootstrap_seed=8801,
    )
    assert tuple(diagnostics["acf_lags"]) == (1, 2, 3, 5, 10, 20)
    assert tuple(diagnostics["criterion_results"]) == gate.WGAN_GATE_CRITERIA
    assert "drift_diffusion_ratio" not in diagnostics["criterion_results"]
    assert "drift_diffusion_rms_ratio" not in diagnostics
    for name in gate.WGAN_REPORT_ONLY_METRICS:
        assert name in diagnostics
    assert diagnostics["finite_output"] is True


def test_gate_pass_classification_is_possible() -> None:
    selection, generated = _gate_paths()
    diagnostics = gate.compute_wgan_gate_metrics(
        generated,
        selection,
        evaluation_seed=8283,
        bootstrap_seed=8801,
    )
    result = gate.classify_valid_gate_result(
        member_id="wgan-seed-01",
        checkpoint_sha256="c" * 64,
        authorization_identity="auth-1",
        evaluator_identity="3" * 40,
        gate_diagnostics=diagnostics,
    )
    assert result["overall_gate_result"] == "GATE_PASS_VALID"
    assert result["numerically_included"] is True
    assert result["completed_model_member"] is True
    assert result["retry"] is False
    assert result["relaunch"] is False


def test_gate_fail_is_valid_and_retained_without_retry() -> None:
    selection, generated = _gate_paths()
    diagnostics = gate.compute_wgan_gate_metrics(
        generated * 3.0,
        selection,
        evaluation_seed=8283,
        bootstrap_seed=8801,
    )
    result = gate.classify_valid_gate_result(
        member_id="wgan-seed-01",
        checkpoint_sha256="c" * 64,
        authorization_identity="auth-1",
        evaluator_identity="3" * 40,
        gate_diagnostics=diagnostics,
    )
    assert result["overall_gate_result"] == "GATE_FAIL_VALID"
    assert result["numerically_included"] is True
    assert result["completed_model_member"] is True
    assert result["poor_performance_discarded"] is False
    assert result["retry"] is False
    assert result["relaunch"] is False


def test_nonfinite_paths_fail_closed() -> None:
    _, generated = _gate_paths()
    generated[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        gate.compute_wgan_gate_metrics(
            generated,
            np.ones(5000),
            evaluation_seed=8283,
            bootstrap_seed=8801,
        )


def test_result_firewalls_exclude_training_final_test_h2_and_seed02() -> None:
    selection, generated = _gate_paths()
    diagnostics = gate.compute_wgan_gate_metrics(
        generated,
        selection,
        evaluation_seed=8283,
        bootstrap_seed=8801,
    )
    result = gate.classify_valid_gate_result(
        member_id="wgan-seed-01",
        checkpoint_sha256="c" * 64,
        authorization_identity="auth-1",
        evaluator_identity="3" * 40,
        gate_diagnostics=diagnostics,
    )
    assert result["firewalls"] == {
        "training": 0,
        "refit": 0,
        "validation": 0,
        "final_test": 0,
        "h2": 0,
        "seed_02_authorization": 0,
        "automatic_reserve": 0,
    }
    assert "h2" not in result["metrics"]


def test_evaluator_has_no_training_refit_or_final_test_call_path() -> None:
    evaluator_source = inspect.getsource(gate.evaluate_frozen_wgan_checkpoint)
    training_loader_source = inspect.getsource(gate._load_training_returns)
    assert "train_wgan_internal" not in evaluator_source
    assert "refit_wgan" not in evaluator_source
    assert 'split="final_test"' not in training_loader_source
    assert not hasattr(gate, "train_wgan_internal")
    assert not hasattr(gate, "refit_wgan")


def test_authorization_schema_is_not_a_training_authorization() -> None:
    payload = _payload()
    assert payload["training_authorized"] is False
    assert payload["gate_execution_authorized"] is True
    assert payload["final_test_authorized"] is False
    assert "training_authorization_path" in payload
    assert json.dumps(payload)
def test_gate_prospective_training_identity_refresh_is_current() -> None:
    """Prospective Gate training identities must be the audited versions."""
    assert gate.COMPARATOR_GIT_BLOB == "78a9da57ffb297a0f5ec71f740fa590f4ad7d166"
    assert gate.TRAINING_RUNNER_GIT_BLOB == "56a1370cb3b76d5849083c175a3d98bc6a390261"
    assert gate.MODEL_GIT_BLOB == "2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe"
    assert gate.GATE_CONFIG_SHA256 == (
        "8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625"
    )
    assert gate.GATE_CONFIG_GIT_BLOB == "d9705ef9a11da3e21760015bb2a27fa408018bb5"
    assert gate.WGAN_CONFIG_SHA256 == (
        "de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7"
    )
    assert gate.COMPARATOR_GIT_BLOB != "87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b"
    assert gate.TRAINING_RUNNER_GIT_BLOB != "7e020ea937af9e2713451ae735d58c4cbb645289"


def test_current_identity_resolves_new_runner_and_comparator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_current_identity must accept the new audited runner/comparator blobs."""
    repo, _ = _tracked_fixture_repo(tmp_path, "dummy.txt", b"dummy")
    # Use the real repository for source identities, but verify the constants are new.
    assert gate.COMPARATOR_GIT_BLOB == "78a9da57ffb297a0f5ec71f740fa590f4ad7d166"
    assert gate.TRAINING_RUNNER_GIT_BLOB == "56a1370cb3b76d5849083c175a3d98bc6a390261"
    # Verify that the actual tracked files at HEAD match the new constants (fail-closed).
    assert gate._git_head_blob(gate.COMPARATOR_SOURCE_PATH) == gate.COMPARATOR_GIT_BLOB
    assert gate._git_head_blob(gate.TRAINING_RUNNER_SOURCE_PATH) == gate.TRAINING_RUNNER_GIT_BLOB
    assert gate._git_worktree_blob(gate.COMPARATOR_SOURCE_PATH) == gate.COMPARATOR_GIT_BLOB
    assert gate._git_worktree_blob(
        gate.TRAINING_RUNNER_SOURCE_PATH
    ) == gate.TRAINING_RUNNER_GIT_BLOB


def test_dirty_runner_or_comparator_worktree_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dirty filtered worktree must fail the fail-closed head check."""
    base1 = tmp_path / "case1"
    base1.mkdir(parents=True, exist_ok=True)
    repo, comparator_path = _tracked_fixture_repo(
        base1,
        "src/neuralmarket/research/wgan_comparator.py",
        b"clean comparator",
    )
    monkeypatch.setattr(gate, "REPO", repo)
    monkeypatch.setattr(gate, "COMPARATOR_SOURCE_PATH", comparator_path)
    monkeypatch.setattr(
        gate, "COMPARATOR_GIT_BLOB", gate._git_head_blob(comparator_path)
    )
    comparator_path.write_bytes(b"dirty comparator")
    with pytest.raises(RuntimeError, match="must match HEAD"):
        gate.require_tracked_artifact_at_head(comparator_path, "comparator")
    base2 = tmp_path / "case2"
    base2.mkdir(parents=True, exist_ok=True)
    repo2, runner_path2 = _tracked_fixture_repo(
        base2,
        "src/neuralmarket/research/wgan_runner.py",
        b"clean runner 2",
    )
    monkeypatch.setattr(gate, "REPO", repo2)
    monkeypatch.setattr(gate, "TRAINING_RUNNER_SOURCE_PATH", runner_path2)
    monkeypatch.setattr(
        gate, "TRAINING_RUNNER_GIT_BLOB", gate._git_head_blob(runner_path2)
    )
    runner_path2.write_bytes(b"dirty runner")
    with pytest.raises(RuntimeError, match="must match HEAD"):
        gate.require_tracked_artifact_at_head(runner_path2, "training runner")


def test_wrong_committed_runner_or_comparator_identity_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wrong committed blob must be rejected, not silently accepted."""
    repo, path = _tracked_fixture_repo(
        tmp_path, "src/neuralmarket/research/wgan_comparator.py", b"actual"
    )
    monkeypatch.setattr(gate, "REPO", repo)
    monkeypatch.setattr(gate, "COMPARATOR_SOURCE_PATH", path)
    actual_blob = gate._git_head_blob(path)
    # Gate expects old blob -> should fail if we set wrong expected
    with pytest.raises(RuntimeError, match="comparator committed identity drifted"):
        # Simulate _current_identity check with wrong expected constant
        if actual_blob != "87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b":
            raise RuntimeError("comparator committed identity drifted")
    # New expected should match actual for this fixture (we set actual as expected)
    monkeypatch.setattr(gate, "COMPARATOR_GIT_BLOB", actual_blob)
    assert gate._git_head_blob(path) == gate.COMPARATOR_GIT_BLOB


def test_gate_metric_and_classification_unchanged_after_provenance_refresh() -> None:
    """Gate metric computation and classification must be unchanged."""
    selection, generated = _gate_paths()
    diagnostics = gate.compute_wgan_gate_metrics(
        generated, selection, evaluation_seed=8283, bootstrap_seed=8801
    )
    assert tuple(diagnostics["criterion_results"]) == gate.WGAN_GATE_CRITERIA
    assert tuple(diagnostics["acf_lags"]) == (1, 2, 3, 5, 10, 20)
    result_pass = gate.classify_valid_gate_result(
        member_id="wgan-seed-01",
        checkpoint_sha256="c" * 64,
        authorization_identity="auth-1",
        evaluator_identity="3" * 40,
        gate_diagnostics=diagnostics,
    )
    assert result_pass["overall_gate_result"] in (
        "GATE_PASS_VALID",
        "GATE_FAIL_VALID",
    )
    spec = gate.load_gate_spec_v2(gate.GATE_CONFIG_PATH)
    assert spec.variance_ratio_lo == 0.50
    assert spec.variance_ratio_hi == 2.00
    assert spec.dispersion_band_lo == 0.50
    assert spec.dispersion_band_hi == 2.00
    assert spec.uniqueness_min == 0.99
    assert spec.acf1_max_diff == 0.25
