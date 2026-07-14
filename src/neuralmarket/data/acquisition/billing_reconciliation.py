"""Manual billing reconciliation for uncertain pilot requests.

This module is deliberately offline: it validates a local operator artifact and
updates only journal accounting. It never constructs providers or downloads
market data.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, field_validator

from neuralmarket.data.acquisition.journal import RequestJournal

PORTAL_STATUS = Literal["BILLED", "NOT_BILLED", "UNKNOWN"]

_REQUEST_STATES = {
    "BILLED": "billed_without_validated_artifact",
    "NOT_BILLED": "retry_eligible_after_manual_nonbilling_confirmation",
    "UNKNOWN": "uncertain_billing",
}
_BILLING_RESOLUTIONS = {
    "BILLED": "confirmed_billed",
    "NOT_BILLED": "confirmed_not_billed",
    "UNKNOWN": "unresolved",
}


class BillingReconciliationError(RuntimeError):
    """Raised when a reconciliation artifact or journal transition fails closed."""


class BillingReconciliationArtifact(BaseModel):
    """Typed local artifact recording the manual portal review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    reconciliation_version: str
    execution_id: str
    request_id: str
    plan_hash: str
    authorization_hash: str
    portal_review_status: PORTAL_STATUS
    observed_usage_usd: str
    reviewed_by: str
    reviewed_at: str
    review_method: str
    billing_resolution: str
    retry_eligible: bool
    manual_action_required: bool
    journal_state_before: str
    journal_state_after: str
    execution_attempt_status_before: str
    execution_attempt_status_after: str
    artifact_hash: str

    @field_validator("observed_usage_usd")
    @classmethod
    def _validate_observed_usage(cls, value: str) -> str:
        if value == "UNKNOWN":
            return value
        try:
            decimal = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("observed_usage_usd must be decimal or UNKNOWN") from exc
        if decimal < 0:
            raise ValueError("observed_usage_usd must be nonnegative")
        return str(decimal)


def canonical_artifact_hash(payload: dict[str, object]) -> str:
    """Return SHA-256 over canonical JSON excluding ``artifact_hash``."""
    unsigned = {key: value for key, value in payload.items() if key != "artifact_hash"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_reconciliation_artifact(path: Path) -> BillingReconciliationArtifact:
    """Load and hash-validate a local reconciliation artifact."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BillingReconciliationError("reconciliation artifact must be an object")
    expected = canonical_artifact_hash(payload)
    if payload.get("artifact_hash") != expected:
        raise BillingReconciliationError("reconciliation artifact hash mismatch")
    artifact = BillingReconciliationArtifact.model_validate(payload)
    expected_resolution = _BILLING_RESOLUTIONS[artifact.portal_review_status]
    expected_state = _REQUEST_STATES[artifact.portal_review_status]
    expected_retry = artifact.portal_review_status == "NOT_BILLED"
    expected_manual = artifact.portal_review_status != "NOT_BILLED"
    if artifact.billing_resolution != expected_resolution:
        raise BillingReconciliationError("billing resolution does not match portal status")
    if artifact.journal_state_after != expected_state:
        raise BillingReconciliationError("journal_state_after does not match portal status")
    if artifact.retry_eligible != expected_retry:
        raise BillingReconciliationError("retry_eligible does not match portal status")
    if artifact.manual_action_required != expected_manual:
        raise BillingReconciliationError("manual_action_required does not match portal status")
    if artifact.reviewed_by != "neuralmarket_local_operator":
        raise BillingReconciliationError("reviewed_by must be neuralmarket_local_operator")
    if artifact.review_method != "manual_databento_portal_review":
        raise BillingReconciliationError("review_method must be manual_databento_portal_review")
    if artifact.portal_review_status == "UNKNOWN" and artifact.observed_usage_usd != "UNKNOWN":
        raise BillingReconciliationError("UNKNOWN status requires observed_usage_usd=UNKNOWN")
    if artifact.portal_review_status != "UNKNOWN" and artifact.observed_usage_usd == "UNKNOWN":
        raise BillingReconciliationError("known status requires decimal observed_usage_usd")
    return artifact


class ReconciliationResult(BaseModel):
    """Result of applying a reconciliation artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    execution_id: str
    request_id: str
    portal_review_status: str
    billing_resolution: str
    request_state_before: str
    request_state_after: str
    retry_eligible: bool
    manual_action_required: bool
    execution_attempt_status_before: str
    execution_attempt_status_after: str
    finished_at_populated: bool
    blocking_request: str
    blocking_state: str
    authorization_state_before: str
    authorization_state_after: str
    retried: int = 0
    deleted: int = 0
    paid_provider_constructed: bool = False
    paid_request_calls: int = 0
    metadata_calls: int = 0
    downloaded_records: int = 0
    idempotent_replay: bool = False


def _fetch_one(
    connection: sqlite3.Connection, query: str, params: tuple[object, ...]
) -> sqlite3.Row:
    row = connection.execute(query, params).fetchone()
    if row is None:
        raise BillingReconciliationError("target journal row not found")
    return cast(sqlite3.Row, row)


def apply_billing_reconciliation(
    *, journal: RequestJournal, artifact: BillingReconciliationArtifact, dry_run: bool = False
) -> ReconciliationResult:
    """Apply a validated reconciliation transactionally and idempotently."""
    conn = journal.connection
    conn.row_factory = sqlite3.Row
    now = datetime.now(UTC).isoformat()
    target_state = _REQUEST_STATES[artifact.portal_review_status]
    target_attempt_status = (
        "blocked_uncertain_billing"
        if artifact.portal_review_status == "UNKNOWN"
        else f"reconciled_{artifact.billing_resolution}"
    )

    request = _fetch_one(
        conn, "SELECT * FROM requests WHERE request_id = ?", (artifact.request_id,)
    )
    attempt = _fetch_one(
        conn, "SELECT * FROM execution_attempts WHERE execution_id = ?", (artifact.execution_id,)
    )
    reservation = _fetch_one(
        conn,
        "SELECT * FROM authorization_reservations WHERE authorization_hash = ? AND execution_id = ?",  # noqa: E501
        (artifact.authorization_hash, artifact.execution_id),
    )
    consumed = _fetch_one(
        conn,
        "SELECT * FROM consumed_authorizations WHERE plan_hash = ? AND authorization_hash = ?",
        (artifact.plan_hash, artifact.authorization_hash),
    )
    if (
        attempt["plan_hash"] != artifact.plan_hash
        or attempt["authorization_hash"] != artifact.authorization_hash
    ):
        raise BillingReconciliationError("execution attempt binding mismatch")
    if consumed["execution_id"] != artifact.execution_id:
        raise BillingReconciliationError("consumed authorization binding mismatch")
    if reservation["state"] != "consumed":
        raise BillingReconciliationError("authorization is not consumed")

    existing = conn.execute(
        "SELECT artifact_hash, portal_review_status FROM billing_reconciliations "
        "WHERE execution_id = ? AND request_id = ?",
        (artifact.execution_id, artifact.request_id),
    ).fetchone()
    if existing is not None:
        if existing["artifact_hash"] != artifact.artifact_hash:
            raise BillingReconciliationError("conflicting reconciliation already recorded")
        after_attempt = _fetch_one(
            conn,
            "SELECT * FROM execution_attempts WHERE execution_id = ?",
            (artifact.execution_id,),
        )
        after_request = _fetch_one(
            conn, "SELECT * FROM requests WHERE request_id = ?", (artifact.request_id,)
        )
        return ReconciliationResult(
            status="ok",
            execution_id=artifact.execution_id,
            request_id=artifact.request_id,
            portal_review_status=artifact.portal_review_status,
            billing_resolution=artifact.billing_resolution,
            request_state_before=str(request["state"]),
            request_state_after=str(after_request["state"]),
            retry_eligible=artifact.retry_eligible,
            manual_action_required=artifact.manual_action_required,
            execution_attempt_status_before=str(attempt["status"]),
            execution_attempt_status_after=str(after_attempt["status"]),
            finished_at_populated=after_attempt["finished_at"] is not None,
            blocking_request=str(after_attempt["blocking_request"]),
            blocking_state=str(after_attempt["blocking_state"]),
            authorization_state_before=str(reservation["state"]),
            authorization_state_after=str(reservation["state"]),
            idempotent_replay=True,
        )

    if request["state"] != artifact.journal_state_before and request["state"] != target_state:
        raise BillingReconciliationError("request state does not match reconciliation precondition")
    if request["state"] not in {"uncertain_billing", target_state}:
        raise BillingReconciliationError("request is not uncertain or already reconciled")
    if attempt["status"] not in {artifact.execution_attempt_status_before, target_attempt_status}:
        raise BillingReconciliationError(
            "execution attempt status does not match reconciliation precondition"
        )

    result = ReconciliationResult(
        status="dry_run" if dry_run else "ok",
        execution_id=artifact.execution_id,
        request_id=artifact.request_id,
        portal_review_status=artifact.portal_review_status,
        billing_resolution=artifact.billing_resolution,
        request_state_before=str(request["state"]),
        request_state_after=target_state,
        retry_eligible=artifact.retry_eligible,
        manual_action_required=artifact.manual_action_required,
        execution_attempt_status_before=str(attempt["status"]),
        execution_attempt_status_after=target_attempt_status,
        finished_at_populated=True,
        blocking_request=artifact.request_id,
        blocking_state="block_uncertain_billing",
        authorization_state_before=str(reservation["state"]),
        authorization_state_after=str(reservation["state"]),
    )
    if dry_run:
        return result

    with conn:
        conn.execute(
            "INSERT INTO billing_reconciliations "
            "(artifact_hash, execution_id, request_id, plan_hash, authorization_hash, portal_review_status, "  # noqa: E501
            "observed_usage_usd, billing_resolution, retry_eligible, manual_action_required, reviewed_by, "  # noqa: E501
            "reviewed_at, review_method, applied_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",  # noqa: E501
            (
                artifact.artifact_hash,
                artifact.execution_id,
                artifact.request_id,
                artifact.plan_hash,
                artifact.authorization_hash,
                artifact.portal_review_status,
                artifact.observed_usage_usd,
                artifact.billing_resolution,
                int(artifact.retry_eligible),
                int(artifact.manual_action_required),
                artifact.reviewed_by,
                artifact.reviewed_at,
                artifact.review_method,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO request_events "
            "(request_id, event_type, event_at, detail_json) VALUES (?, ?, ?, ?)",
            (
                artifact.request_id,
                "billing_reconciliation_applied",
                now,
                json.dumps(artifact.model_dump(), sort_keys=True, separators=(",", ":")),
            ),
        )
        conn.execute(
            "UPDATE requests SET state = ?, updated_at = ?, failure_category = ?, failure_message = ? "  # noqa: E501
            "WHERE request_id = ? AND state = 'uncertain_billing'",
            (
                target_state,
                now,
                artifact.billing_resolution,
                f"manual Databento portal reconciliation: {artifact.portal_review_status}",
                artifact.request_id,
            ),
        )
        conn.execute(
            "UPDATE execution_attempts SET status = ?, finished_at = COALESCE(finished_at, ?), "
            "blocking_request = ?, blocking_state = ?, requests_completed = 0, requests_uncertain = 1, "  # noqa: E501
            "paid_request_calls = 1, downloaded_records = 0, manual_action_required = ? "
            "WHERE execution_id = ?",
            (
                target_attempt_status,
                now,
                artifact.request_id,
                "block_uncertain_billing",
                int(artifact.manual_action_required),
                artifact.execution_id,
            ),
        )
    return result


def build_reconciliation_artifact(
    *,
    execution_id: str,
    request_id: str,
    plan_hash: str,
    authorization_hash: str,
    portal_review_status: str,
    observed_usage_usd: str,
    journal_state_before: str,
    execution_attempt_status_before: str,
    reviewed_at: str | None = None,
) -> BillingReconciliationArtifact:
    """Build a canonical artifact for the local operator's exact portal input."""
    status = portal_review_status
    if status not in _REQUEST_STATES:
        raise BillingReconciliationError("invalid portal review status")
    payload: dict[str, object] = {
        "reconciliation_version": "1.0",
        "execution_id": execution_id,
        "request_id": request_id,
        "plan_hash": plan_hash,
        "authorization_hash": authorization_hash,
        "portal_review_status": status,
        "observed_usage_usd": observed_usage_usd,
        "reviewed_by": "neuralmarket_local_operator",
        "reviewed_at": reviewed_at or datetime.now(UTC).isoformat(),
        "review_method": "manual_databento_portal_review",
        "billing_resolution": _BILLING_RESOLUTIONS[status],
        "retry_eligible": status == "NOT_BILLED",
        "manual_action_required": status != "NOT_BILLED",
        "journal_state_before": journal_state_before,
        "journal_state_after": _REQUEST_STATES[status],
        "execution_attempt_status_before": execution_attempt_status_before,
        "execution_attempt_status_after": "blocked_uncertain_billing"
        if status == "UNKNOWN"
        else f"reconciled_{_BILLING_RESOLUTIONS[status]}",
    }
    payload["artifact_hash"] = canonical_artifact_hash(payload)
    return BillingReconciliationArtifact.model_validate(payload)
