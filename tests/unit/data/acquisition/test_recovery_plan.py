from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import neuralmarket.data.acquisition.recovery as recovery_module
from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    AuthorizationError,
    PilotAuthorization,
    compute_authorization_hash,
    validate_authorization,
)
from neuralmarket.data.acquisition.billing_reconciliation import (
    apply_billing_reconciliation,
    build_reconciliation_artifact,
)
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.recovery import (
    RecoveryPlan,
    RecoveryPlanError,
    prepare_recovery_plan,
)

pytestmark = pytest.mark.unit

_PARENT_PLAN = (
    "9654fe1c2dfe98946560e27c6f51f110"  # pragma: allowlist secret
    "038613060461fdf75936edf1a7d0ae77"  # pragma: allowlist secret
)
_PRIOR_AUTHORIZATION = (
    "db2cde39f5a5e96c7301b9d289fc0c8"  # pragma: allowlist secret
    "e5412b60d2b69faae30f12a7b99dd885e"  # pragma: allowlist secret
)
_PRIOR_EXECUTION = "132078783c31dcab22cb90d95c967c9c"  # pragma: allowlist secret
_REQUEST_ID = "2750995e515e4f1a"  # pragma: allowlist secret
_REQUEST_HASH = (
    "b8b0a410ace7a8a5d710b8bc04e37560"  # pragma: allowlist secret
    "ab7b08ceb9aa316a4a3334b6b0980d7a"  # pragma: allowlist secret
)


def _seed_reconciled_request(tmp_path: Path) -> tuple[Path, Path, Path]:
    journal_path = tmp_path / "journal.sqlite"
    now = datetime.now(UTC).isoformat()
    with RequestJournal(journal_path) as journal:
        journal.upsert(
            JournalEntry(
                request_id=_REQUEST_ID,
                request_hash=_REQUEST_HASH,
                state="uncertain_billing",
                attempt_count=1,
                estimated_cost_usd="0.000112652779",
                actual_billed_cost_usd=None,
                raw_path=None,
                raw_checksum=None,
                normalized_path=None,
                normalized_checksum=None,
                failure_category="provider_error",
                failure_message="paid historical provider operation failed",
                created_at=now,
                updated_at=now,
            )
        )
        assert journal.reserve_authorization(
            authorization_hash=_PRIOR_AUTHORIZATION,
            plan_hash=_PARENT_PLAN,
            execution_id=_PRIOR_EXECUTION,
            reserved_at=now,
        )
        assert journal.consume_reserved_authorization(
            authorization_hash=_PRIOR_AUTHORIZATION,
            execution_id=_PRIOR_EXECUTION,
            consumed_at=now,
        )
        unknown = build_reconciliation_artifact(
            execution_id=_PRIOR_EXECUTION,
            request_id=_REQUEST_ID,
            plan_hash=_PARENT_PLAN,
            authorization_hash=_PRIOR_AUTHORIZATION,
            portal_review_status="UNKNOWN",
            observed_usage_usd="UNKNOWN",
            journal_state_before="uncertain_billing",
            execution_attempt_status_before="running",
            reviewed_at=now,
        )
        apply_billing_reconciliation(journal=journal, artifact=unknown)
        not_billed = build_reconciliation_artifact(
            execution_id=_PRIOR_EXECUTION,
            request_id=_REQUEST_ID,
            plan_hash=_PARENT_PLAN,
            authorization_hash=_PRIOR_AUTHORIZATION,
            portal_review_status="NOT_BILLED",
            observed_usage_usd="0.00",
            journal_state_before="uncertain_billing",
            execution_attempt_status_before="blocked_uncertain_billing",
            reviewed_at=now,
            supersedes_reconciliation_hash=unknown.artifact_hash,
            supersession_reason="operator obtained definitive portal nonbilling evidence",
            supersession_evidence_method="manual_databento_portal_review",
            supersession_sequence=2,
        )
        apply_billing_reconciliation(journal=journal, artifact=not_billed)

    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(unknown.model_dump_json(indent=2), encoding="utf-8")
    reconciliation_path = tmp_path / "not_billed.json"
    reconciliation_path.write_text(not_billed.model_dump_json(indent=2), encoding="utf-8")
    return journal_path, reconciliation_path, unknown_path


def test_valid_reconciled_request_produces_distinct_one_request_plan(tmp_path: Path) -> None:
    journal_path, reconciliation_path, _ = _seed_reconciled_request(tmp_path)
    parent_path = Path("data/manifests/pilot_request_plan_v1.json")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))

    recovery = prepare_recovery_plan(
        parent_plan_path=parent_path,
        journal_path=journal_path,
        reconciliation_path=reconciliation_path,
        request_id=_REQUEST_ID,
    )
    payload = recovery.model_dump(mode="json", by_alias=True)

    assert payload["plan_hash"] != _PARENT_PLAN
    assert payload["request_count"] == 1
    assert [request["request_id"] for request in payload["requests"]] == [_REQUEST_ID]
    assert payload["requests"][0] == next(
        request for request in parent["requests"] if request["request_id"] == _REQUEST_ID
    )
    assert payload["recovery"] == {
        "parent_plan_hash": _PARENT_PLAN,
        "prior_execution_id": _PRIOR_EXECUTION,
        "prior_authorization_hash": _PRIOR_AUTHORIZATION,
        "request_id": _REQUEST_ID,
        "request_hash": _REQUEST_HASH,
        "reconciliation_artifact_hash": not_billed_hash(reconciliation_path),
        "required_prior_resolution": "confirmed_not_billed",
        "required_journal_state": "retry_eligible_after_manual_nonbilling_confirmation",
        "automatic_retry_allowed": False,
    }


def not_billed_hash(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["artifact_hash"])


def _prepare(tmp_path: Path) -> tuple[RecoveryPlan, Path, Path, Path]:
    journal, reconciliation, unknown = _seed_reconciled_request(tmp_path)
    recovery = prepare_recovery_plan(
        parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
        journal_path=journal,
        reconciliation_path=reconciliation,
        request_id=_REQUEST_ID,
    )
    return recovery, journal, reconciliation, unknown


def _update(journal: Path, sql: str, parameters: tuple[object, ...] = ()) -> None:
    connection = sqlite3.connect(journal)
    connection.execute(sql, parameters)
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()


def _authorization(plan_hash: str, bindings: dict[str, str]) -> PilotAuthorization:
    now = datetime.now(UTC)
    payload = {
        "authorization_version": "pilot-authorization-v1",
        "pilot_plan_hash": plan_hash,
        "source_manifest_hash": bindings["source_manifest_hash"],
        "split_manifest_hash": bindings["split_manifest_hash"],
        "acquisition_policy_hash": bindings["acquisition_policy_hash"],
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "authorized_by": "test-operator",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
    }
    return PilotAuthorization.model_validate(
        {**payload, "authorization_hash": compute_authorization_hash(payload)}
    )


def test_recovery_hash_is_deterministic_and_preparation_is_read_only(tmp_path: Path) -> None:
    recovery, journal, reconciliation, _ = _prepare(tmp_path)
    before = {path.name: path.read_bytes() for path in journal.parent.glob("journal.sqlite*")}

    repeated = prepare_recovery_plan(
        parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
        journal_path=journal,
        reconciliation_path=reconciliation,
        request_id=_REQUEST_ID,
    )

    after = {path.name: path.read_bytes() for path in journal.parent.glob("journal.sqlite*")}
    assert repeated.plan_hash == recovery.plan_hash
    assert after == before


def test_uncheckpointed_wal_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    Path(f"{journal}-wal").write_bytes(b"uncheckpointed")

    with pytest.raises(RecoveryPlanError, match="uncheckpointed WAL state"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_journal_change_during_preparation_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    real_connect = sqlite3.connect

    def racing_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        connection = real_connect(*args, **kwargs)
        with real_connect(journal) as writer:
            writer.execute(
                "UPDATE requests SET state = 'uncertain_billing' WHERE request_id = ?",
                (_REQUEST_ID,),
            )
        return connection

    monkeypatch.setattr(recovery_module.sqlite3, "connect", racing_connect)
    with pytest.raises(RecoveryPlanError, match="changed during recovery preparation"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_unsupported_journal_schema_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE schema_meta SET version = 8")

    with pytest.raises(RecoveryPlanError, match="journal schema version"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_non_consumed_reservation_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE authorization_reservations SET state = 'reserved'")

    with pytest.raises(RecoveryPlanError, match="reservation binding mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_inconsistent_reconciled_execution_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE execution_attempts SET blocking_request = 'other-request'")

    with pytest.raises(RecoveryPlanError, match="reconciled execution state mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_broken_reconciliation_chain_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(
        journal,
        "UPDATE billing_reconciliations SET supersedes_reconciliation_hash = NULL "
        "WHERE supersession_sequence = 2",
    )

    with pytest.raises(RecoveryPlanError, match="reconciliation chain mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_missing_reconciliation_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "DELETE FROM billing_reconciliations")

    with pytest.raises(RecoveryPlanError, match="effective reconciliation is missing"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_superseded_unknown_reconciliation_fails_closed(tmp_path: Path) -> None:
    _, journal, _, unknown = _prepare(tmp_path)

    with pytest.raises(RecoveryPlanError, match="not the effective NOT_BILLED"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=unknown,
            request_id=_REQUEST_ID,
        )


def test_effective_billed_reconciliation_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(
        journal,
        "UPDATE billing_reconciliations SET portal_review_status = 'BILLED', "
        "billing_resolution = 'confirmed_billed' WHERE supersession_sequence = 2",
    )

    with pytest.raises(RecoveryPlanError, match="not the effective NOT_BILLED"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


@pytest.mark.parametrize(
    ("assignment", "message"),
    [
        ("state = 'uncertain_billing'", "not retry eligible"),
        ("attempt_count = 0", "no prior attempt"),
        ("actual_billed_cost_usd = '0.01'", "has billed cost"),
        ("request_completed_at = '2026-07-16T00:00:00+00:00'", "is completed"),
        ("raw_path = 'data/raw/recovery.dbn'", "has registered artifacts"),
        ("normalized_path = 'data/normalized/recovery.parquet'", "has registered artifacts"),
    ],
)
def test_ineligible_request_state_fails_closed(
    tmp_path: Path, assignment: str, message: str
) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, f"UPDATE requests SET {assignment} WHERE request_id = ?", (_REQUEST_ID,))

    with pytest.raises(RecoveryPlanError, match=message):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_wrong_request_hash_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE requests SET request_hash = ?", ("0" * 64,))

    with pytest.raises(RecoveryPlanError, match="request hash mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_wrong_prior_execution_id_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(
        journal,
        "UPDATE consumed_authorizations SET execution_id = 'wrong-execution' WHERE plan_hash = ?",
        (_PARENT_PLAN,),
    )

    with pytest.raises(RecoveryPlanError, match="reservation binding mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_recovery_model_rejects_a_second_request(tmp_path: Path) -> None:
    recovery, _, _, _ = _prepare(tmp_path)
    payload = recovery.model_dump(mode="json", by_alias=True)
    parent = json.loads(
        Path("data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8")
    )
    payload["requests"].append(parent["requests"][1])

    with pytest.raises(ValueError, match="at most 1 item|exactly one request"):
        RecoveryPlan.model_validate(payload)


def test_parent_reauthorization_stays_blocked_but_recovery_identity_is_available(
    tmp_path: Path,
) -> None:
    recovery, journal, _, _ = _prepare(tmp_path)
    with sqlite3.connect(journal) as connection:
        consumed = {
            row[0] for row in connection.execute("SELECT plan_hash FROM consumed_authorizations")
        }
    parent_auth = _authorization(_PARENT_PLAN, recovery.bindings)
    recovery_auth = _authorization(recovery.plan_hash, recovery.bindings)
    expected = {
        "expected_source_manifest_hash": recovery.bindings["source_manifest_hash"],
        "expected_split_manifest_hash": recovery.bindings["split_manifest_hash"],
        "expected_acquisition_policy_hash": recovery.bindings["acquisition_policy_hash"],
        "now": datetime.now(UTC),
        "consumed_ids": consumed,
        "expected_maximum_spend_usd": Decimal("5.00"),
        "expected_maximum_single_request_usd": Decimal("1.00"),
    }

    with pytest.raises(AuthorizationError, match="already consumed"):
        validate_authorization(parent_auth, expected_plan_hash=_PARENT_PLAN, **expected)
    validate_authorization(recovery_auth, expected_plan_hash=recovery.plan_hash, **expected)
