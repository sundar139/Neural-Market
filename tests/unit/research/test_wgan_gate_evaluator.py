"""Synthetic regression tests for the fail-closed WGAN Gate-v2 evaluator."""
from __future__ import annotations

import hashlib
import inspect
import json
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
