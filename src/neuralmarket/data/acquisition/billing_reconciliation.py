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

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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
_TERMINAL_STATUSES = {"BILLED", "NOT_BILLED"}


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
    supersedes_reconciliation_hash: str | None = None
    supersession_reason: str | None = None
    supersession_evidence_method: str | None = None
    supersession_sequence: int = 1

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

    @model_validator(mode="after")
    def _validate_supersession_fields(self) -> BillingReconciliationArtifact:
        has_predecessor = self.supersedes_reconciliation_hash is not None
        if has_predecessor:
            if self.supersession_sequence < 2:
                raise ValueError("supersession sequence must be >= 2")
            if not self.supersession_reason:
                raise ValueError("supersession_reason is required")
            if self.supersession_evidence_method != "manual_databento_portal_review":
                raise ValueError(
                    "supersession_evidence_method must be manual_databento_portal_review"
                )
        elif any((self.supersession_reason, self.supersession_evidence_method)):
            raise ValueError("supersession metadata requires supersedes_reconciliation_hash")
        elif self.supersession_sequence != 1:
            raise ValueError("initial reconciliation sequence must be 1")
        return self


def canonical_artifact_hash(payload: dict[str, object]) -> str:
    """Return SHA-256 over canonical JSON excluding ``artifact_hash``."""
    unsigned = {key: value for key, value in payload.items() if key != "artifact_hash"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _attempt_status(status: str) -> str:
    if status == "UNKNOWN":
        return "blocked_uncertain_billing"
    if status == "NOT_BILLED":
        return "blocked_reconciled_not_billed"
    return "blocked_reconciled_billed"


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
    if artifact.execution_attempt_status_after != _attempt_status(artifact.portal_review_status):
        raise BillingReconciliationError(
            "execution_attempt_status_after does not match portal status"
        )
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
    automatic_retry_allowed: bool = False
    new_authorization_required: bool
    manual_action_required: bool
    execution_attempt_status_before: str
    execution_attempt_status_after: str
    finished_at_populated: bool
    blocking_request: str
    blocking_state: str
    authorization_state_before: str
    authorization_state_after: str
    reconciliation_chain_valid: bool = True
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


def _effective_reconciliation(
    conn: sqlite3.Connection, execution_id: str, request_id: str
) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM billing_reconciliations WHERE execution_id = ? AND request_id = ? "
        "ORDER BY supersession_sequence DESC, applied_at DESC LIMIT 1",
        (execution_id, request_id),
    ).fetchone()
    return cast(sqlite3.Row | None, row)


def _reconciliation_by_hash(conn: sqlite3.Connection, artifact_hash: str) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM billing_reconciliations WHERE artifact_hash = ?", (artifact_hash,)
    ).fetchone()
    return cast(sqlite3.Row | None, row)


def _validate_chain_transition(
    *, conn: sqlite3.Connection, artifact: BillingReconciliationArtifact
) -> None:
    existing_artifact = _reconciliation_by_hash(conn, artifact.artifact_hash)
    if existing_artifact is not None:
        return

    effective = _effective_reconciliation(conn, artifact.execution_id, artifact.request_id)
    if effective is None:
        if artifact.supersedes_reconciliation_hash is not None:
            raise BillingReconciliationError("stale predecessor hash; no current reconciliation")
        if artifact.supersession_sequence != 1:
            raise BillingReconciliationError("wrong supersession sequence")
        return

    if artifact.supersedes_reconciliation_hash is None:
        raise BillingReconciliationError("new reconciliation must supersede current effective hash")

    sequence_conflict = conn.execute(
        "SELECT artifact_hash FROM billing_reconciliations "
        "WHERE execution_id = ? AND request_id = ? AND supersession_sequence = ?",
        (artifact.execution_id, artifact.request_id, artifact.supersession_sequence),
    ).fetchone()
    if sequence_conflict is not None:
        raise BillingReconciliationError("conflicting reconciliation sequence already recorded")
    if artifact.supersedes_reconciliation_hash != effective["artifact_hash"]:
        raise BillingReconciliationError("stale predecessor hash")
    expected_sequence = int(effective["supersession_sequence"]) + 1
    if artifact.supersession_sequence != expected_sequence:
        raise BillingReconciliationError("wrong supersession sequence")

    current_status = str(effective["portal_review_status"])
    next_status = artifact.portal_review_status
    if current_status == "UNKNOWN" and next_status in {"BILLED", "NOT_BILLED"}:
        return
    if current_status == "UNKNOWN" and next_status == "UNKNOWN":
        if artifact.artifact_hash == effective["artifact_hash"]:
            return
        raise BillingReconciliationError("UNKNOWN supersession must be identical to be idempotent")
    if current_status in _TERMINAL_STATUSES and next_status != current_status:
        raise BillingReconciliationError("terminal reconciliation cannot be superseded")
    raise BillingReconciliationError("unsupported reconciliation supersession")


def _result(
    *,
    status: str,
    artifact: BillingReconciliationArtifact,
    request_state_before: str,
    request_state_after: str,
    attempt_status_before: str,
    attempt_status_after: str,
    finished_at_populated: bool,
    blocking_request: str,
    blocking_state: str,
    authorization_state: str,
    idempotent_replay: bool = False,
) -> ReconciliationResult:
    return ReconciliationResult(
        status=status,
        execution_id=artifact.execution_id,
        request_id=artifact.request_id,
        portal_review_status=artifact.portal_review_status,
        billing_resolution=artifact.billing_resolution,
        request_state_before=request_state_before,
        request_state_after=request_state_after,
        retry_eligible=artifact.retry_eligible,
        automatic_retry_allowed=False,
        new_authorization_required=artifact.retry_eligible,
        manual_action_required=artifact.manual_action_required,
        execution_attempt_status_before=attempt_status_before,
        execution_attempt_status_after=attempt_status_after,
        finished_at_populated=finished_at_populated,
        blocking_request=blocking_request,
        blocking_state=blocking_state,
        authorization_state_before=authorization_state,
        authorization_state_after=authorization_state,
        paid_request_calls=1,
        downloaded_records=0,
        idempotent_replay=idempotent_replay,
    )


def apply_billing_reconciliation(
    *, journal: RequestJournal, artifact: BillingReconciliationArtifact, dry_run: bool = False
) -> ReconciliationResult:
    """Apply a validated reconciliation transactionally and idempotently."""
    conn = journal.connection
    conn.row_factory = sqlite3.Row
    now = datetime.now(UTC).isoformat()
    target_state = _REQUEST_STATES[artifact.portal_review_status]
    target_attempt_status = _attempt_status(artifact.portal_review_status)

    request = _fetch_one(
        conn, "SELECT * FROM requests WHERE request_id = ?", (artifact.request_id,)
    )
    attempt = _fetch_one(
        conn, "SELECT * FROM execution_attempts WHERE execution_id = ?", (artifact.execution_id,)
    )
    reservation = _fetch_one(
        conn,
        "SELECT * FROM authorization_reservations "
        "WHERE authorization_hash = ? AND execution_id = ?",
        (artifact.authorization_hash, artifact.execution_id),
    )
    if (
        attempt["plan_hash"] != artifact.plan_hash
        or attempt["authorization_hash"] != artifact.authorization_hash
    ):
        raise BillingReconciliationError("execution attempt binding mismatch")
    consumed = _fetch_one(
        conn,
        "SELECT * FROM consumed_authorizations WHERE plan_hash = ? AND authorization_hash = ?",
        (artifact.plan_hash, artifact.authorization_hash),
    )
    if consumed["execution_id"] != artifact.execution_id:
        raise BillingReconciliationError("consumed authorization binding mismatch")
    if reservation["state"] != "consumed":
        raise BillingReconciliationError("authorization is not consumed")

    _validate_chain_transition(conn=conn, artifact=artifact)
    existing_artifact = _reconciliation_by_hash(conn, artifact.artifact_hash)
    if existing_artifact is not None:
        after_attempt = _fetch_one(
            conn,
            "SELECT * FROM execution_attempts WHERE execution_id = ?",
            (artifact.execution_id,),
        )
        after_request = _fetch_one(
            conn, "SELECT * FROM requests WHERE request_id = ?", (artifact.request_id,)
        )
        return _result(
            status="ok",
            artifact=artifact,
            request_state_before=str(request["state"]),
            request_state_after=str(after_request["state"]),
            attempt_status_before=str(attempt["status"]),
            attempt_status_after=str(after_attempt["status"]),
            finished_at_populated=after_attempt["finished_at"] is not None,
            blocking_request=str(after_attempt["blocking_request"]),
            blocking_state=str(after_attempt["blocking_state"]),
            authorization_state=str(reservation["state"]),
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

    result = _result(
        status="dry_run" if dry_run else "ok",
        artifact=artifact,
        request_state_before=str(request["state"]),
        request_state_after=target_state,
        attempt_status_before=str(attempt["status"]),
        attempt_status_after=target_attempt_status,
        finished_at_populated=True,
        blocking_request=artifact.request_id,
        blocking_state="block_uncertain_billing",
        authorization_state=str(reservation["state"]),
    )
    if dry_run:
        return result

    with conn:
        conn.execute(
            "INSERT INTO billing_reconciliations "
            "(artifact_hash, execution_id, request_id, plan_hash, authorization_hash, "
            "portal_review_status, observed_usage_usd, billing_resolution, retry_eligible, "
            "manual_action_required, reviewed_by, reviewed_at, review_method, applied_at, "
            "supersedes_reconciliation_hash, supersession_reason, "
            "supersession_evidence_method, supersession_sequence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                artifact.supersedes_reconciliation_hash,
                artifact.supersession_reason,
                artifact.supersession_evidence_method,
                artifact.supersession_sequence,
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
            "UPDATE requests "
            "SET state = ?, updated_at = ?, failure_category = ?, failure_message = ? "
            "WHERE request_id = ?",
            (
                target_state,
                now,
                artifact.billing_resolution,
                f"manual Databento portal reconciliation: {artifact.portal_review_status}",
                artifact.request_id,
            ),
        )
        conn.execute(
            "UPDATE execution_attempts "
            "SET status = ?, finished_at = COALESCE(finished_at, ?), "
            "blocking_request = ?, blocking_state = ?, requests_completed = 0, "
            "requests_uncertain = ?, paid_request_calls = 1, downloaded_records = 0, "
            "manual_action_required = ? WHERE execution_id = ?",
            (
                target_attempt_status,
                now,
                artifact.request_id,
                "block_uncertain_billing",
                1 if artifact.portal_review_status == "UNKNOWN" else 0,
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
    supersedes_reconciliation_hash: str | None = None,
    supersession_reason: str | None = None,
    supersession_evidence_method: str | None = None,
    supersession_sequence: int = 1,
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
        "execution_attempt_status_after": _attempt_status(status),
        "supersedes_reconciliation_hash": supersedes_reconciliation_hash,
        "supersession_reason": supersession_reason,
        "supersession_evidence_method": supersession_evidence_method,
        "supersession_sequence": supersession_sequence,
    }
    payload["artifact_hash"] = canonical_artifact_hash(payload)
    return BillingReconciliationArtifact.model_validate(payload)
