from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.billing_reconciliation import (
    BillingReconciliationError,
    apply_billing_reconciliation,
    build_reconciliation_artifact,
    canonical_artifact_hash,
)
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal

pytestmark = pytest.mark.unit

PLAN_HASH = "p" * 64
AUTH_HASH = "a" * 64
EXECUTION_ID = "execution-1"
REQUEST_ID = "request-1"


def _entry(state: str = "uncertain_billing") -> JournalEntry:
    now = datetime.now(UTC).isoformat()
    return JournalEntry(
        request_id=REQUEST_ID,
        request_hash="r" * 64,
        state=state,
        attempt_count=1,
        estimated_cost_usd="0.01",
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


def _journal(tmp_path: Path) -> RequestJournal:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    journal.upsert(_entry())
    assert journal.reserve_authorization(
        authorization_hash=AUTH_HASH,
        plan_hash=PLAN_HASH,
        execution_id=EXECUTION_ID,
        reserved_at=datetime.now(UTC).isoformat(),
    )
    assert journal.consume_reserved_authorization(
        authorization_hash=AUTH_HASH,
        execution_id=EXECUTION_ID,
        consumed_at=datetime.now(UTC).isoformat(),
    )
    return journal


def _artifact(status: str, usage: str, **kwargs):
    return build_reconciliation_artifact(
        execution_id=kwargs.pop("execution_id", EXECUTION_ID),
        request_id=kwargs.pop("request_id", REQUEST_ID),
        plan_hash=kwargs.pop("plan_hash", PLAN_HASH),
        authorization_hash=kwargs.pop("authorization_hash", AUTH_HASH),
        portal_review_status=status,
        observed_usage_usd=usage,
        journal_state_before="uncertain_billing",
        execution_attempt_status_before=kwargs.pop("attempt_before", "running"),
        **kwargs,
    )


@pytest.mark.parametrize(
    ("status", "usage", "expected_state", "retry", "manual"),
    [
        ("BILLED", "0.01", "billed_without_validated_artifact", False, True),
        (
            "NOT_BILLED",
            "0.00",
            "retry_eligible_after_manual_nonbilling_confirmation",
            True,
            False,
        ),
        ("UNKNOWN", "UNKNOWN", "uncertain_billing", False, True),
    ],
)
def test_apply_billing_reconciliation_resolutions(
    tmp_path: Path, status: str, usage: str, expected_state: str, retry: bool, manual: bool
) -> None:
    journal = _journal(tmp_path)
    artifact = _artifact(status, usage)
    result = apply_billing_reconciliation(journal=journal, artifact=artifact)
    assert result.request_state_after == expected_state
    assert result.retry_eligible is retry
    assert result.manual_action_required is manual
    assert result.automatic_retry_allowed is False
    assert result.new_authorization_required is retry
    assert result.execution_attempt_status_after != "running"
    assert result.finished_at_populated
    assert journal.get(REQUEST_ID).state == expected_state  # type: ignore[union-attr]
    row = journal.connection.execute(
        "SELECT state FROM authorization_reservations WHERE authorization_hash = ?", (AUTH_HASH,)
    ).fetchone()
    assert row[0] == "consumed"


def test_unknown_to_not_billed_supersession_appends_chain_and_preserves_original(
    tmp_path: Path,
) -> None:
    journal = _journal(tmp_path)
    unknown = _artifact("UNKNOWN", "UNKNOWN")
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    superseding = _artifact(
        "NOT_BILLED",
        "0.00",
        supersedes_reconciliation_hash=unknown.artifact_hash,
        supersession_reason="operator obtained definitive portal nonbilling evidence",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
        attempt_before="blocked_uncertain_billing",
    )

    result = apply_billing_reconciliation(journal=journal, artifact=superseding)

    assert result.reconciliation_chain_valid is True
    assert result.request_state_after == "retry_eligible_after_manual_nonbilling_confirmation"
    assert result.execution_attempt_status_after == "blocked_reconciled_not_billed"
    assert result.retry_eligible is True
    assert result.new_authorization_required is True
    assert result.automatic_retry_allowed is False
    assert result.paid_request_calls == 1
    assert result.downloaded_records == 0
    rows = journal.connection.execute(
        "SELECT artifact_hash, supersedes_reconciliation_hash, supersession_sequence "
        "FROM billing_reconciliations ORDER BY supersession_sequence"
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        (unknown.artifact_hash, None, 1),
        (superseding.artifact_hash, unknown.artifact_hash, 2),
    ]


def test_unknown_to_billed_supersession_succeeds_without_retry(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    unknown = _artifact("UNKNOWN", "UNKNOWN")
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    billed = _artifact(
        "BILLED",
        "0.01",
        supersedes_reconciliation_hash=unknown.artifact_hash,
        supersession_reason="operator obtained definitive portal billing evidence",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
        attempt_before="blocked_uncertain_billing",
    )
    result = apply_billing_reconciliation(journal=journal, artifact=billed)
    assert result.request_state_after == "billed_without_validated_artifact"
    assert result.retry_eligible is False
    assert result.new_authorization_required is False


def test_identical_reconciliation_is_idempotent(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    artifact = _artifact("UNKNOWN", "UNKNOWN")
    first = apply_billing_reconciliation(journal=journal, artifact=artifact)
    second = apply_billing_reconciliation(journal=journal, artifact=artifact)
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True
    count = journal.connection.execute("SELECT count(*) FROM billing_reconciliations").fetchone()
    assert count[0] == 1


def test_identical_supersession_replay_adds_no_duplicate_event(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    unknown = _artifact("UNKNOWN", "UNKNOWN")
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    superseding = _artifact(
        "NOT_BILLED",
        "0.00",
        supersedes_reconciliation_hash=unknown.artifact_hash,
        supersession_reason="operator obtained definitive portal nonbilling evidence",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
        attempt_before="blocked_uncertain_billing",
    )
    apply_billing_reconciliation(journal=journal, artifact=superseding)
    before = journal.connection.execute("SELECT count(*) FROM request_events").fetchone()[0]
    replay = apply_billing_reconciliation(journal=journal, artifact=superseding)
    after = journal.connection.execute("SELECT count(*) FROM request_events").fetchone()[0]
    assert replay.idempotent_replay is True
    assert after == before


def test_conflicting_reconciliation_rejected(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    unknown = _artifact("UNKNOWN", "UNKNOWN")
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    billed = _artifact("BILLED", "0.01")
    with pytest.raises(BillingReconciliationError, match="supersed"):
        apply_billing_reconciliation(journal=journal, artifact=billed)


@pytest.mark.parametrize(
    ("first", "second"),
    [("NOT_BILLED", "BILLED"), ("BILLED", "NOT_BILLED")],
)
def test_terminal_resolution_cannot_be_superseded(tmp_path: Path, first: str, second: str) -> None:
    journal = _journal(tmp_path)
    first_artifact = _artifact(first, "0.00" if first == "NOT_BILLED" else "0.01")
    apply_billing_reconciliation(journal=journal, artifact=first_artifact)
    second_artifact = _artifact(
        second,
        "0.00" if second == "NOT_BILLED" else "0.01",
        supersedes_reconciliation_hash=first_artifact.artifact_hash,
        supersession_reason="operator changed mind",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
        attempt_before="blocked_uncertain_billing",
    )
    with pytest.raises(BillingReconciliationError, match="terminal"):
        apply_billing_reconciliation(journal=journal, artifact=second_artifact)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"supersedes_reconciliation_hash": "f" * 64}, "stale"),
        ({"supersession_sequence": 3}, "sequence"),
        ({"execution_id": "other-execution"}, "not found"),
        ({"request_id": "other-request"}, "not found"),
        ({"plan_hash": "b" * 64}, "binding"),
        ({"authorization_hash": "b" * 64}, "not found"),
    ],
)
def test_invalid_supersession_bindings_fail_closed(
    tmp_path: Path, kwargs: dict[str, object], match: str
) -> None:
    journal = _journal(tmp_path)
    unknown = _artifact("UNKNOWN", "UNKNOWN")
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    payload = {
        "supersedes_reconciliation_hash": unknown.artifact_hash,
        "supersession_reason": "operator obtained definitive portal nonbilling evidence",
        "supersession_evidence_method": "manual_databento_portal_review",
        "supersession_sequence": 2,
        "attempt_before": "blocked_uncertain_billing",
        **kwargs,
    }
    artifact = _artifact("NOT_BILLED", "0.00", **payload)
    with pytest.raises(BillingReconciliationError, match=match):
        apply_billing_reconciliation(journal=journal, artifact=artifact)


def test_same_sequence_different_artifact_rejected(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    unknown = _artifact("UNKNOWN", "UNKNOWN")
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    first = _artifact(
        "NOT_BILLED",
        "0.00",
        supersedes_reconciliation_hash=unknown.artifact_hash,
        supersession_reason="operator obtained definitive portal nonbilling evidence",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
        attempt_before="blocked_uncertain_billing",
    )
    apply_billing_reconciliation(journal=journal, artifact=first)
    second = _artifact(
        "NOT_BILLED",
        "0.01",
        supersedes_reconciliation_hash=unknown.artifact_hash,
        supersession_reason="operator obtained definitive portal nonbilling evidence",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
        attempt_before="blocked_uncertain_billing",
    )
    with pytest.raises(BillingReconciliationError, match="sequence"):
        apply_billing_reconciliation(journal=journal, artifact=second)


def test_artifact_hash_detects_tamper() -> None:
    artifact = _artifact("UNKNOWN", "UNKNOWN")
    payload = artifact.model_dump()
    assert canonical_artifact_hash(payload) == artifact.artifact_hash
    payload["request_id"] = "other"
    assert canonical_artifact_hash(payload) != artifact.artifact_hash
