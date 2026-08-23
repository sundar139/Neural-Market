"""Focused fail-closed readiness tests for the future WGAN runner."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuralmarket.research import wgan_runner


def _identity() -> dict[str, object]:
    return {
        "runner_git_blob": "runner-blob",
        "implementation_source_git_blobs": {"model": "model-blob", "comparator": "comparator-blob"},
        "execution_contract_git_blob": "contract-blob",
        "effective_config_sha256": "config-sha",
        "effective_config_git_blob": "config-blob",
        "preregistration_sha256": wgan_runner.PREREGISTRATION_SHA256,
        "amendment_060_sha256": wgan_runner.AMENDMENT_060_SHA256,
        "runtime_identity_sha256": "runtime-sha",
    }


def _payload() -> dict[str, object]:
    return {
        "schema_version": "structured-vol-v5-wgan-authorization-v1",
        "member_id": "wgan-seed-01",
        "replicate_seed": 8281,
        "model_init_seed": 8281,
        "data_seed": 8282,
        "eval_seed": 8283,
        "effective_config_sha256": "config-sha",
        "effective_config_git_blob": "config-blob",
        "comparator_methodology_sha256": wgan_runner.PREREGISTRATION_SHA256,
        "amendment_060_sha256": wgan_runner.AMENDMENT_060_SHA256,
        "seed_schedule_sha256": wgan_runner.SEED_SCHEDULE_SHA256,
        "seed_schedule_git_blob": wgan_runner.SEED_SCHEDULE_BLOB,
        "execution_contract_git_blob": "contract-blob",
        "runner_git_blob": "runner-blob",
        "implementation_source_git_blobs": {"model": "model-blob", "comparator": "comparator-blob"},
        "execution_recipe_head": "0" * 40,
        "requested_device": "cuda",
        "expected_resolved_device": "cuda",
        "expected_runtime_identity_sha256": "runtime-sha",
        "max_scientific_invocations": 1,
        "training_authorized": True,
        "validation_authorized": False,
        "final_test_authorized": False,
    }


def test_contract_binds_frozen_methodology_and_defers_implementation_blob() -> None:
    contract = json.loads(wgan_runner.EXECUTION_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["methodology"]["preregistration_sha256"] == wgan_runner.PREREGISTRATION_SHA256
    assert contract["methodology"]["amendment_060_sha256"] == wgan_runner.AMENDMENT_060_SHA256
    assert contract["implementation_binding"]["status"] == "DEFERRED_TO_LATER_AUTHORIZATION"
    assert "implementation_source_git_blobs" not in contract["implementation_binding"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("runner_git_blob", "wrong", "runner"),
        (
            "implementation_source_git_blobs",
            {"model": "wrong", "comparator": "comparator-blob"},
            "implementation",
        ),
        ("comparator_methodology_sha256", "wrong", "methodology"),
        ("amendment_060_sha256", "wrong", "Amendment-060"),
    ],
)
def test_wrong_identity_fails_closed(field: str, value: object, message: str) -> None:
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError, match=message):
        wgan_runner.validate_authorization_payload(payload, expected_identity=_identity())


def test_valid_identity_payload_and_authorization_flags() -> None:
    wgan_runner.validate_authorization_payload(_payload(), expected_identity=_identity())


def test_missing_authorization_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="authorization"):
        wgan_runner.require_authorization(None)


def test_cpu_scientific_execution_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="CUDA"):
        wgan_runner.require_scientific_cuda("cpu")


def test_dry_run_never_trains_or_creates_scientific_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wgan_runner, "WGAN_RUN_ROOT", tmp_path / "wgan-runs")
    monkeypatch.setattr(
        wgan_runner,
        "execute_authorized_wgan",
        lambda *args, **kwargs: pytest.fail("dry-run trained"),
    )
    assert wgan_runner.main(["--member-id", "wgan-seed-01"]) == 0
    assert not list(tmp_path.rglob("execution_started.json"))
    assert not list(tmp_path.rglob("*.pt"))


def test_primary_and_reserve_rosters_are_fixed_without_automatic_chain() -> None:
    assert tuple(f"wgan-seed-0{i}" for i in range(1, 6)) == wgan_runner.PRIMARY_MEMBER_IDS
    assert wgan_runner.RESERVE_MEMBER_IDS == (
        "reserve-wgan-j01",
        "reserve-wgan-j02",
        "reserve-wgan-j03",
    )
    assert wgan_runner.AUTO_RESERVE_CHAIN is False
