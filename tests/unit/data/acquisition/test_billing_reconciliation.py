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
    artifact = build_reconciliation_artifact(
        execution_id=EXECUTION_ID,
        request_id=REQUEST_ID,
        plan_hash=PLAN_HASH,
        authorization_hash=AUTH_HASH,
        portal_review_status=status,
        observed_usage_usd=usage,
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="running",
    )
    result = apply_billing_reconciliation(journal=journal, artifact=artifact)
    assert result.request_state_after == expected_state
    assert result.retry_eligible is retry
    assert result.manual_action_required is manual
    assert result.execution_attempt_status_after != "running"
    assert result.finished_at_populated
    assert journal.get(REQUEST_ID).state == expected_state  # type: ignore[union-attr]
    row = journal.connection.execute(
        "SELECT state FROM authorization_reservations WHERE authorization_hash = ?", (AUTH_HASH,)
    ).fetchone()
    assert row[0] == "consumed"


def test_identical_reconciliation_is_idempotent(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    artifact = build_reconciliation_artifact(
        execution_id=EXECUTION_ID,
        request_id=REQUEST_ID,
        plan_hash=PLAN_HASH,
        authorization_hash=AUTH_HASH,
        portal_review_status="UNKNOWN",
        observed_usage_usd="UNKNOWN",
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="running",
    )
    first = apply_billing_reconciliation(journal=journal, artifact=artifact)
    second = apply_billing_reconciliation(journal=journal, artifact=artifact)
    assert first.idempotent_replay is False
    assert second.idempotent_replay is True
    count = journal.connection.execute("SELECT count(*) FROM billing_reconciliations").fetchone()
    assert count[0] == 1


def test_conflicting_reconciliation_rejected(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    unknown = build_reconciliation_artifact(
        execution_id=EXECUTION_ID,
        request_id=REQUEST_ID,
        plan_hash=PLAN_HASH,
        authorization_hash=AUTH_HASH,
        portal_review_status="UNKNOWN",
        observed_usage_usd="UNKNOWN",
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="running",
    )
    apply_billing_reconciliation(journal=journal, artifact=unknown)
    billed = build_reconciliation_artifact(
        execution_id=EXECUTION_ID,
        request_id=REQUEST_ID,
        plan_hash=PLAN_HASH,
        authorization_hash=AUTH_HASH,
        portal_review_status="BILLED",
        observed_usage_usd="0.01",
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="running",
    )
    with pytest.raises(BillingReconciliationError, match="conflicting"):
        apply_billing_reconciliation(journal=journal, artifact=billed)


def test_artifact_hash_detects_tamper() -> None:
    artifact = build_reconciliation_artifact(
        execution_id=EXECUTION_ID,
        request_id=REQUEST_ID,
        plan_hash=PLAN_HASH,
        authorization_hash=AUTH_HASH,
        portal_review_status="UNKNOWN",
        observed_usage_usd="UNKNOWN",
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="running",
    )
    payload = artifact.model_dump()
    assert canonical_artifact_hash(payload) == artifact.artifact_hash
    payload["request_id"] = "other"
    assert canonical_artifact_hash(payload) != artifact.artifact_hash
