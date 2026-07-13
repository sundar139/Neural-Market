"""Tests for the pilot executor state machine and dual authorization guard.

The centerpiece is proving the dual guard: a real paid provider is only ever
constructed when BOTH a valid, hash-bound authorization artifact AND an
explicit matching plan-hash confirmation are present. Every failure path
asserts the injected ``paid_provider_factory`` is never called.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    compute_authorization_hash,
)
from neuralmarket.data.acquisition.executor import ExecutorGuardError, PilotExecutor
from neuralmarket.data.acquisition.journal import RequestJournal


def _write_valid_auth_file(path: Path, *, plan_hash: str = "p" * 64) -> None:
    import json

    now = datetime.now(UTC)
    payload = {
        "authorization_version": "1.0",
        "pilot_plan_hash": plan_hash,
        "source_manifest_hash": "s" * 64,
        "split_manifest_hash": "v" * 64,
        "acquisition_policy_hash": "a" * 64,
        "maximum_spend_usd": "5.00",
        "authorized_currency": "USD",
        "authorized_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "authorized_by": "Test User",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
    }
    payload["authorization_hash"] = compute_authorization_hash(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_guard_execute_blocks_when_authorization_file_missing(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=tmp_path / "missing.json",
            confirm_plan_hash="p" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
        )
    assert exc.value.reason == "missing_authorization"
    factory.assert_not_called()


def test_guard_execute_blocks_when_confirm_plan_hash_mismatched(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash="p" * 64)
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=auth_path,
            confirm_plan_hash="WRONG_HASH",
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
        )
    assert exc.value.reason == "plan_hash_confirmation_mismatch"
    factory.assert_not_called()


def test_guard_execute_blocks_invalid_authorization(tmp_path) -> None:
    # A structurally valid file whose plan hash does not match the live plan.
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash="p" * 64)
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="q" * 64,  # live plan differs from the authorized plan
            authorization_path=auth_path,
            confirm_plan_hash="q" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
        )
    assert exc.value.reason == "invalid_authorization"
    factory.assert_not_called()


def test_guard_execute_blocks_template_authorization(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    # parents[4] is the repository root (acquisition/data/unit/tests/<root>).
    repo_root = Path(__file__).resolve().parents[4]
    template_path = repo_root / "configs/data/acquisition/pilot_authorization.template.json"
    assert template_path.exists(), f"template not found at {template_path}"
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=template_path,
            confirm_plan_hash="p" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
        )
    assert exc.value.reason == "invalid_authorization"
    factory.assert_not_called()


def test_guard_execute_succeeds_only_with_both_valid_guards(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash="p" * 64)
    sentinel_provider = Mock()
    factory = Mock(return_value=sentinel_provider)
    result = executor.guard_execute(
        plan_hash="p" * 64,
        authorization_path=auth_path,
        confirm_plan_hash="p" * 64,
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        now=datetime.now(UTC),
        paid_provider_factory=factory,
    )
    assert result is sentinel_provider
    factory.assert_called_once()


def test_prepare_writes_planned_state_for_every_request(tmp_path, arcx_request) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare([arcx_request])
    entry = journal.get(arcx_request.request_id)
    assert entry is not None
    assert entry.state == "planned"


def test_transition_rejects_illegal_jump(tmp_path, arcx_request) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare([arcx_request])
    with pytest.raises(ValueError):
        executor.transition(arcx_request.request_id, "downloaded")


def test_transition_allows_legal_step(tmp_path, arcx_request) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare([arcx_request])
    executor.transition(arcx_request.request_id, "preflight_validated")
    entry = journal.get(arcx_request.request_id)
    assert entry is not None
    assert entry.state == "preflight_validated"


def test_metadata_provider_can_be_constructed_during_preparation() -> None:
    # A MetadataEstimator (already-existing metadata-only provider) is freely constructible.
    from neuralmarket.data.acquisition.estimation import MetadataEstimator

    estimator = MetadataEstimator(client=Mock())
    assert estimator is not None


def test_init_has_no_paid_provider_parameter() -> None:
    # Structural guarantee: a paid provider cannot exist as a constructor attribute.
    import inspect

    params = set(inspect.signature(PilotExecutor.__init__).parameters)
    assert not any("paid" in p or "provider" in p for p in params)
