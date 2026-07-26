"""Offline, read-only recovery inspection for the acquisition journal.

Compares journal state against the filesystem and reports discrepancies.
This module is strictly read-only: it never writes to the journal (only
``.all()``), never retries a request, and never deletes a file -- including
stale ``.partial`` files. Any remediation (quarantine, retry, deletion) is a
separate explicit action taken elsewhere.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, model_validator

from neuralmarket.data.acquisition.billing_reconciliation import (
    BillingReconciliationArtifact,
    load_reconciliation_artifact,
)
from neuralmarket.data.acquisition.journal import (
    JOURNAL_SCHEMA_VERSION,
    JournalEntry,
    RequestJournal,
)
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    plan_hash,
    plan_hash_metadata,
    validate_canonical_pilot_plan,
    verify_final_request,
)
from neuralmarket.data.acquisition.storage import PathSafetyError, resolve_under_data_root
from neuralmarket.data.raw.integrity import verify_checksum

_RAW_PRESENT_STATES = frozenset({"raw_validated", "normalized", "quality_validated"})
_RECOVERY_STATE = "retry_eligible_after_manual_nonbilling_confirmation"
_RECOVERY_RESOLUTION = "confirmed_not_billed"


class RecoveryPlanError(ValueError):
    """Raised when one-request recovery provenance is incomplete or ambiguous."""


class RecoveryPlanProvenance(BaseModel):
    """Immutable parent history required to authorize exactly one recovery."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    parent_plan_hash: str
    prior_execution_id: str
    prior_authorization_hash: str
    request_id: str
    request_hash: str
    reconciliation_artifact_hash: str
    required_prior_resolution: Literal["confirmed_not_billed"] = "confirmed_not_billed"
    required_journal_state: Literal["retry_eligible_after_manual_nonbilling_confirmation"] = (
        "retry_eligible_after_manual_nonbilling_confirmation"
    )
    automatic_retry_allowed: Literal[False] = False


class RecoveryPlan(BaseModel):
    """A normal one-request plan identity with explicit recovery provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: Literal["pilot-recovery-plan-v1"] = "pilot-recovery-plan-v1"
    plan_hash: str
    bindings: dict[str, str]
    estimated_total_cost_usd: str
    estimated_maximum_single_request_usd: str
    maximum_allowed_total_usd: str
    maximum_allowed_single_request_usd: str
    authorization: Literal["required"] = "required"
    purchase_authorized: Literal[False] = False
    request_count: Literal[1] = 1
    recovery: RecoveryPlanProvenance
    requests: tuple[AcquisitionRequest]

    @model_validator(mode="after")
    def _validate_identity(self) -> RecoveryPlan:
        if len(self.requests) != 1:
            raise ValueError("recovery plan must contain exactly one request")
        request = self.requests[0]
        if (
            request.request_id != self.recovery.request_id
            or request.request_hash != self.recovery.request_hash
        ):
            raise ValueError("recovery request provenance mismatch")
        verify_final_request(request)
        metadata = plan_hash_metadata(self.model_dump(mode="json", by_alias=True))
        if plan_hash([request], self.bindings, metadata) != self.plan_hash:
            raise ValueError("recovery plan hash mismatch")
        if self.plan_hash == self.recovery.parent_plan_hash:
            raise ValueError("recovery plan hash must differ from parent plan hash")
        return self


def _journal_snapshot(path: Path) -> tuple[bytes, bool, int, bytes]:
    """Fingerprint journal state without opening SQLite."""
    wal_path = path.with_name(f"{path.name}-wal")
    main_before = hashlib.sha256(path.read_bytes()).digest()
    wal_exists = wal_path.exists()
    wal = wal_path.read_bytes() if wal_exists else b""
    main_after = hashlib.sha256(path.read_bytes()).digest()
    if main_before != main_after:
        raise RecoveryPlanError("journal changed during recovery preparation")
    return main_after, wal_exists, len(wal), hashlib.sha256(wal).digest()


@contextmanager
def _read_only_connection(path: Path) -> Iterator[sqlite3.Connection]:
    """Open an existing SQLite journal without initialization or migration."""
    before = _journal_snapshot(path)
    if before[2]:
        raise RecoveryPlanError("journal has uncheckpointed WAL state")
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
        if _journal_snapshot(path) != before:
            raise RecoveryPlanError("journal changed during recovery preparation")


def _one_row(
    connection: sqlite3.Connection, query: str, parameters: tuple[object, ...], label: str
) -> sqlite3.Row:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        raise RecoveryPlanError(f"{label} is missing")
    return cast(sqlite3.Row, row)


def _zero_or_null(value: object) -> bool:
    if value is None:
        return True
    try:
        return Decimal(str(value)) == 0
    except InvalidOperation:
        return False


def _validate_parent_plan(payload: dict[str, Any]) -> list[AcquisitionRequest]:
    raw_requests = payload.get("requests")
    if not isinstance(raw_requests, list):
        raise RecoveryPlanError("parent plan requests are missing")
    requests = [AcquisitionRequest.model_validate(item) for item in raw_requests]
    validate_canonical_pilot_plan(requests)
    for request in requests:
        verify_final_request(request)
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        raise RecoveryPlanError("parent plan bindings are missing")
    computed = plan_hash(requests, bindings, plan_hash_metadata(payload))
    if payload.get("plan_hash") != computed:
        raise RecoveryPlanError("parent plan hash mismatch")
    return requests


def _validate_recovery_state(
    *,
    journal_path: Path,
    parent_plan_hash: str,
    request: AcquisitionRequest,
    reconciliation: BillingReconciliationArtifact,
) -> tuple[str, str]:
    with _read_only_connection(journal_path) as connection:
        schema_rows = connection.execute("SELECT version FROM schema_meta").fetchall()
        if len(schema_rows) != 1 or int(schema_rows[0][0]) != JOURNAL_SCHEMA_VERSION:
            raise RecoveryPlanError("journal schema version is not supported")
        consumed = _one_row(
            connection,
            "SELECT * FROM consumed_authorizations WHERE plan_hash = ?",
            (parent_plan_hash,),
            "parent authorization consumption",
        )
        prior_execution_id = str(consumed["execution_id"] or "")
        prior_authorization_hash = str(consumed["authorization_hash"])
        if not prior_execution_id:
            raise RecoveryPlanError("consumed parent authorization has no execution ID")

        reservation = _one_row(
            connection,
            "SELECT * FROM authorization_reservations WHERE authorization_hash = ?",
            (prior_authorization_hash,),
            "parent authorization reservation",
        )
        if (
            reservation["plan_hash"] != parent_plan_hash
            or reservation["execution_id"] != prior_execution_id
            or reservation["state"] != "consumed"
            or reservation["consumed_at"] != consumed["consumed_at"]
        ):
            raise RecoveryPlanError("parent authorization reservation binding mismatch")

        execution = _one_row(
            connection,
            "SELECT * FROM execution_attempts WHERE execution_id = ?",
            (prior_execution_id,),
            "prior execution",
        )
        if (
            execution["plan_hash"] != parent_plan_hash
            or execution["authorization_hash"] != prior_authorization_hash
        ):
            raise RecoveryPlanError("prior execution binding mismatch")
        expected_execution = {
            "status": "blocked_reconciled_not_billed",
            "blocking_request": request.request_id,
            "blocking_state": "block_uncertain_billing",
            "requests_completed": 0,
            "requests_uncertain": 0,
            "paid_request_calls": 1,
            "downloaded_records": 0,
            "manual_action_required": 0,
        }
        if any(execution[field] != value for field, value in expected_execution.items()):
            raise RecoveryPlanError("reconciled execution state mismatch")

        row = _one_row(
            connection,
            "SELECT * FROM requests WHERE request_id = ?",
            (request.request_id,),
            "recovery request",
        )
        if row["request_hash"] != request.request_hash:
            raise RecoveryPlanError("recovery request hash mismatch")
        if int(row["attempt_count"]) != 1:
            raise RecoveryPlanError("recovery request must have exactly one prior attempt")
        if row["state"] != _RECOVERY_STATE:
            raise RecoveryPlanError("recovery request is not retry eligible")
        if not _zero_or_null(row["actual_billed_cost_usd"]):
            raise RecoveryPlanError("recovery request has billed cost")
        if row["request_completed_at"] is not None:
            raise RecoveryPlanError("recovery request is completed")
        artifact_fields = (
            "raw_path",
            "raw_checksum",
            "raw_record_count",
            "raw_byte_count",
            "provider_response_id",
            "normalized_path",
            "normalized_checksum",
        )
        if any(row[field] is not None for field in artifact_fields):
            raise RecoveryPlanError("recovery request has registered artifacts")

        reconciliation_rows = connection.execute(
            "SELECT * FROM billing_reconciliations "
            "WHERE execution_id = ? AND request_id = ? "
            "ORDER BY supersession_sequence, applied_at",
            (prior_execution_id, request.request_id),
        ).fetchall()
        if not reconciliation_rows:
            raise RecoveryPlanError("effective reconciliation is missing")
        previous_hash: str | None = None
        for sequence, item in enumerate(reconciliation_rows, start=1):
            if (
                item["supersession_sequence"] != sequence
                or item["supersedes_reconciliation_hash"] != previous_hash
            ):
                raise RecoveryPlanError("reconciliation chain mismatch")
            previous_hash = str(item["artifact_hash"])
        effective = reconciliation_rows[-1]
        required = {
            "artifact_hash": reconciliation.artifact_hash,
            "plan_hash": parent_plan_hash,
            "authorization_hash": prior_authorization_hash,
            "portal_review_status": "NOT_BILLED",
            "observed_usage_usd": reconciliation.observed_usage_usd,
            "billing_resolution": _RECOVERY_RESOLUTION,
            "retry_eligible": 1,
            "manual_action_required": 0,
            "reviewed_by": reconciliation.reviewed_by,
            "reviewed_at": reconciliation.reviewed_at,
            "review_method": reconciliation.review_method,
            "supersedes_reconciliation_hash": reconciliation.supersedes_reconciliation_hash,
            "supersession_reason": reconciliation.supersession_reason,
            "supersession_evidence_method": reconciliation.supersession_evidence_method,
            "supersession_sequence": reconciliation.supersession_sequence,
        }
        if any(effective[field] != value for field, value in required.items()):
            raise RecoveryPlanError(
                "selected reconciliation is not the effective NOT_BILLED record"
            )
        if (
            reconciliation.execution_id != prior_execution_id
            or reconciliation.request_id != request.request_id
            or reconciliation.plan_hash != parent_plan_hash
            or reconciliation.authorization_hash != prior_authorization_hash
            or reconciliation.portal_review_status != "NOT_BILLED"
            or reconciliation.billing_resolution != _RECOVERY_RESOLUTION
            or Decimal(reconciliation.observed_usage_usd) != 0
        ):
            raise RecoveryPlanError("reconciliation provenance mismatch")
    return prior_execution_id, prior_authorization_hash


def validate_recovery_plan(
    payload: dict[str, Any],
    *,
    journal_path: Path,
) -> RecoveryPlan:
    """Revalidate a prepared recovery identity against current journal state."""
    recovery = RecoveryPlan.model_validate(payload)
    request = recovery.requests[0]
    provenance = recovery.recovery
    with _read_only_connection(journal_path) as connection:
        schema_rows = connection.execute("SELECT version FROM schema_meta").fetchall()
        if len(schema_rows) != 1 or int(schema_rows[0][0]) != JOURNAL_SCHEMA_VERSION:
            raise RecoveryPlanError("journal schema version is not supported")
        consumed = _one_row(
            connection,
            "SELECT * FROM consumed_authorizations WHERE plan_hash = ?",
            (provenance.parent_plan_hash,),
            "parent authorization consumption",
        )
        if (
            consumed["authorization_hash"] != provenance.prior_authorization_hash
            or consumed["execution_id"] != provenance.prior_execution_id
        ):
            raise RecoveryPlanError("parent authorization consumption binding mismatch")
        reservation = _one_row(
            connection,
            "SELECT * FROM authorization_reservations WHERE authorization_hash = ?",
            (provenance.prior_authorization_hash,),
            "parent authorization reservation",
        )
        if (
            reservation["plan_hash"] != provenance.parent_plan_hash
            or reservation["execution_id"] != provenance.prior_execution_id
            or reservation["state"] != "consumed"
            or reservation["consumed_at"] != consumed["consumed_at"]
        ):
            raise RecoveryPlanError("parent authorization reservation binding mismatch")
        execution = _one_row(
            connection,
            "SELECT * FROM execution_attempts WHERE execution_id = ?",
            (provenance.prior_execution_id,),
            "prior execution",
        )
        expected_execution = {
            "plan_hash": provenance.parent_plan_hash,
            "authorization_hash": provenance.prior_authorization_hash,
            "status": "blocked_reconciled_not_billed",
            "blocking_request": request.request_id,
            "blocking_state": "block_uncertain_billing",
            "requests_completed": 0,
            "requests_uncertain": 0,
            "paid_request_calls": 1,
            "downloaded_records": 0,
            "manual_action_required": 0,
        }
        if any(execution[field] != value for field, value in expected_execution.items()):
            raise RecoveryPlanError("reconciled execution state mismatch")
        row = _one_row(
            connection,
            "SELECT * FROM requests WHERE request_id = ?",
            (request.request_id,),
            "recovery request",
        )
        if row["request_hash"] != request.request_hash:
            raise RecoveryPlanError("recovery request hash mismatch")
        if int(row["attempt_count"]) != 1:
            raise RecoveryPlanError("recovery request must have exactly one prior attempt")
        if row["state"] != _RECOVERY_STATE:
            raise RecoveryPlanError("recovery request is not retry eligible")
        if not _zero_or_null(row["actual_billed_cost_usd"]):
            raise RecoveryPlanError("recovery request has billed cost")
        if row["request_completed_at"] is not None:
            raise RecoveryPlanError("recovery request is completed")
        artifact_fields = (
            "raw_path",
            "raw_checksum",
            "raw_record_count",
            "raw_byte_count",
            "provider_response_id",
            "normalized_path",
            "normalized_checksum",
        )
        if any(row[field] is not None for field in artifact_fields):
            raise RecoveryPlanError("recovery request has registered artifacts")
        reconciliations = connection.execute(
            "SELECT * FROM billing_reconciliations "
            "WHERE execution_id = ? AND request_id = ? "
            "ORDER BY supersession_sequence, applied_at",
            (provenance.prior_execution_id, request.request_id),
        ).fetchall()
        if not reconciliations:
            raise RecoveryPlanError("effective reconciliation is missing")
        previous_hash: str | None = None
        for sequence, reconciliation in enumerate(reconciliations, start=1):
            if (
                reconciliation["supersession_sequence"] != sequence
                or reconciliation["supersedes_reconciliation_hash"] != previous_hash
            ):
                raise RecoveryPlanError("reconciliation chain mismatch")
            previous_hash = str(reconciliation["artifact_hash"])
        effective = reconciliations[-1]
        required = {
            "artifact_hash": provenance.reconciliation_artifact_hash,
            "plan_hash": provenance.parent_plan_hash,
            "authorization_hash": provenance.prior_authorization_hash,
            "portal_review_status": "NOT_BILLED",
            "billing_resolution": _RECOVERY_RESOLUTION,
            "retry_eligible": 1,
            "manual_action_required": 0,
        }
        if (
            any(effective[field] != value for field, value in required.items())
            or Decimal(str(effective["observed_usage_usd"])) != 0
        ):
            raise RecoveryPlanError(
                "selected reconciliation is not the effective NOT_BILLED record"
            )
    return recovery


def prepare_recovery_plan(
    *,
    parent_plan_path: Path,
    journal_path: Path,
    reconciliation_path: Path,
    request_id: str,
) -> RecoveryPlan:
    """Build one deterministic recovery identity from read-only authoritative state."""
    payload = json.loads(parent_plan_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RecoveryPlanError("parent plan must be an object")
    parent_requests = _validate_parent_plan(payload)
    matches = [request for request in parent_requests if request.request_id == request_id]
    if len(matches) != 1:
        raise RecoveryPlanError("recovery scope must select exactly one parent request")
    request = matches[0]
    reconciliation = load_reconciliation_artifact(reconciliation_path)
    parent_plan_hash = str(payload["plan_hash"])
    prior_execution_id, prior_authorization_hash = _validate_recovery_state(
        journal_path=journal_path,
        parent_plan_hash=parent_plan_hash,
        request=request,
        reconciliation=reconciliation,
    )
    provenance = RecoveryPlanProvenance(
        parent_plan_hash=parent_plan_hash,
        prior_execution_id=prior_execution_id,
        prior_authorization_hash=prior_authorization_hash,
        request_id=request.request_id,
        request_hash=request.request_hash,
        reconciliation_artifact_hash=reconciliation.artifact_hash,
    )
    cost = str(request.estimated_cost)
    recovery_payload: dict[str, Any] = {
        "estimated_total_cost_usd": cost,
        "estimated_maximum_single_request_usd": cost,
        "maximum_allowed_total_usd": payload["maximum_allowed_total_usd"],
        "maximum_allowed_single_request_usd": payload["maximum_allowed_single_request_usd"],
        "authorization": "required",
        "purchase_authorized": False,
        "recovery": provenance.model_dump(mode="json"),
    }
    bindings = cast(dict[str, str], payload["bindings"])
    recovery_hash = plan_hash(
        [request],
        bindings,
        plan_hash_metadata(recovery_payload),
    )
    if recovery_hash == parent_plan_hash:
        raise RecoveryPlanError("recovery plan hash must differ from parent plan hash")
    return RecoveryPlan(
        plan_hash=recovery_hash,
        bindings=bindings,
        requests=(request,),
        **recovery_payload,
    )


class RecoveryFinding(BaseModel):
    """One anomaly (or confirmation) observed for a single request."""

    request_id: str
    category: Literal[
        "journal_missing_file",
        "checksum_mismatch",
        "normalized_missing_file",
        "normalized_checksum_mismatch",
        "sidecar_missing",
        "sidecar_mismatch",
        "unsafe_path",
        "stale_partial",
        "consistent",
    ]
    detail: str


class RecoveryReport(BaseModel):
    """Read-only summary of a recovery inspection run."""

    generated_at: str
    findings: list[RecoveryFinding]
    uncertain_billing_count: int = 0
    billed_without_validated_artifact_count: int = 0
    confirmed_not_billed_count: int = 0
    retry_eligible_count: int = 0
    stale_running_attempt_count: int = 0
    automatic_retry_allowed: bool = False
    retry_eligible_under_new_authorization: bool = False
    quarantine_recommended: list[str]
    manual_recovery_required: list[str]
    stale_running_attempts: list[str] = []
    retried: int
    deleted: int


def _checksum_matches(path: Path, expected: str | None) -> bool:
    """Fail closed for missing checksums or unreadable files."""
    if expected is None:
        return False
    try:
        return verify_checksum(path, expected)
    except OSError:
        return False


def _sidecar_payload(path: Path) -> dict[str, object] | None:
    sidecar_path = path.with_suffix(path.suffix + ".json")
    if not sidecar_path.exists():
        return None
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _raw_sidecar_matches(path: Path, entry: JournalEntry) -> bool:
    payload = _sidecar_payload(path)
    return bool(
        payload is not None
        and payload.get("request_id") == entry.request_id
        and payload.get("request_hash") == entry.request_hash
        and payload.get("logical_path") == entry.raw_path
        and payload.get("sha256") == entry.raw_checksum
        and payload.get("byte_count") == entry.raw_byte_count
        and isinstance(payload.get("stored_at"), str)
    )


def _normalized_sidecar_matches(path: Path, entry: JournalEntry) -> bool:
    payload = _sidecar_payload(path)
    return bool(
        payload is not None
        and payload.get("source_request_id") == entry.request_id
        and payload.get("raw_sha256") == entry.raw_checksum
        and payload.get("normalized_sha256") == entry.normalized_checksum
        and isinstance(payload.get("normalized_row_count"), int)
        and isinstance(payload.get("schema_fingerprint"), str)
        and len(str(payload.get("schema_fingerprint"))) == 64
    )


def run_recovery(*, journal: RequestJournal, data_root: Path) -> RecoveryReport:
    """Inspect the journal and filesystem for recovery-worthy anomalies.

    Read-only: only calls ``journal.all()``, never mutates the journal, and
    never deletes or renames anything on disk (including stale ``.partial``
    files).
    """
    findings: list[RecoveryFinding] = []
    quarantine_recommended: list[str] = []
    manual_recovery_required: list[str] = []
    partials = sorted(data_root.rglob("*.partial"))
    uncertain_count = 0
    billed_without_artifact_count = 0
    confirmed_not_billed_count = 0

    for entry in journal.all():
        if entry.state == "uncertain_billing":
            uncertain_count += 1
            findings.append(
                RecoveryFinding(
                    request_id=entry.request_id,
                    category="consistent",
                    detail="uncertain billing requires manual portal reconciliation; automatic retry disabled",  # noqa: E501
                )
            )
            manual_recovery_required.append(entry.request_id)
        elif entry.state == "billed_without_validated_artifact":
            billed_without_artifact_count += 1
            findings.append(
                RecoveryFinding(
                    request_id=entry.request_id,
                    category="consistent",
                    detail="billed without validated artifact; manual decision required; automatic retry disabled",  # noqa: E501
                )
            )
            manual_recovery_required.append(entry.request_id)
        elif entry.state == "retry_eligible_after_manual_nonbilling_confirmation":
            confirmed_not_billed_count += 1
            findings.append(
                RecoveryFinding(
                    request_id=entry.request_id,
                    category="consistent",
                    detail="manual nonbilling confirmation recorded; future retry requires new authorization",  # noqa: E501
                )
            )
        if entry.state in _RAW_PRESENT_STATES and entry.raw_path is None:
            findings.append(
                RecoveryFinding(
                    request_id=entry.request_id,
                    category="journal_missing_file",
                    detail=f"journal state {entry.state!r} has no raw_path",
                )
            )
            quarantine_recommended.append(entry.request_id)
        elif entry.state in _RAW_PRESENT_STATES and entry.raw_path is not None:
            try:
                path = resolve_under_data_root(entry.raw_path, data_root)
            except PathSafetyError:
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="unsafe_path",
                        detail=f"unsafe raw path in journal: {entry.raw_path}",
                    )
                )
                quarantine_recommended.append(entry.request_id)
                continue
            if not path.exists():
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="journal_missing_file",
                        detail=f"journal state {entry.state!r} but file missing: {path}",
                    )
                )
                quarantine_recommended.append(entry.request_id)
            elif not _checksum_matches(path, entry.raw_checksum):
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="checksum_mismatch",
                        detail=f"checksum mismatch for {path}",
                    )
                )
                quarantine_recommended.append(entry.request_id)
            elif not path.with_suffix(path.suffix + ".json").exists():
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="sidecar_missing",
                        detail=f"raw sidecar missing: {path.with_suffix(path.suffix + '.json')}",
                    )
                )
                quarantine_recommended.append(entry.request_id)
            elif not _raw_sidecar_matches(path, entry):
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="sidecar_mismatch",
                        detail=f"raw sidecar mismatch: {path.with_suffix(path.suffix + '.json')}",
                    )
                )
                quarantine_recommended.append(entry.request_id)
            else:
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="consistent",
                        detail=f"raw file present and verified: {path}",
                    )
                )

        if entry.state in {"normalized", "quality_validated"}:
            if entry.normalized_path is None:
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="normalized_missing_file",
                        detail="normalized journal state has no normalized_path",
                    )
                )
                quarantine_recommended.append(entry.request_id)
            else:
                try:
                    normalized_path = resolve_under_data_root(entry.normalized_path, data_root)
                except PathSafetyError:
                    findings.append(
                        RecoveryFinding(
                            request_id=entry.request_id,
                            category="unsafe_path",
                            detail=f"unsafe normalized path in journal: {entry.normalized_path}",
                        )
                    )
                    quarantine_recommended.append(entry.request_id)
                else:
                    if not normalized_path.exists():
                        findings.append(
                            RecoveryFinding(
                                request_id=entry.request_id,
                                category="normalized_missing_file",
                                detail=f"normalized file missing: {normalized_path}",
                            )
                        )
                        quarantine_recommended.append(entry.request_id)
                    elif not _checksum_matches(normalized_path, entry.normalized_checksum):
                        findings.append(
                            RecoveryFinding(
                                request_id=entry.request_id,
                                category="normalized_checksum_mismatch",
                                detail=f"normalized checksum mismatch: {normalized_path}",
                            )
                        )
                        quarantine_recommended.append(entry.request_id)
                    elif not normalized_path.with_suffix(normalized_path.suffix + ".json").exists():
                        findings.append(
                            RecoveryFinding(
                                request_id=entry.request_id,
                                category="sidecar_missing",
                                detail="normalized sidecar missing: "
                                f"{normalized_path.with_suffix(normalized_path.suffix + '.json')}",
                            )
                        )
                        quarantine_recommended.append(entry.request_id)
                    elif not _normalized_sidecar_matches(normalized_path, entry):
                        findings.append(
                            RecoveryFinding(
                                request_id=entry.request_id,
                                category="sidecar_mismatch",
                                detail="normalized sidecar mismatch: "
                                f"{normalized_path.with_suffix(normalized_path.suffix + '.json')}",
                            )
                        )
                        quarantine_recommended.append(entry.request_id)

        for partial in (path for path in partials if path.name.startswith(f"{entry.request_id}.")):
            findings.append(
                RecoveryFinding(
                    request_id=entry.request_id,
                    category="stale_partial",
                    detail=f"stale partial file found: {partial}",
                )
            )
            manual_recovery_required.append(entry.request_id)

    stale_running_attempts = [
        str(row[0])
        for row in journal.connection.execute(
            "SELECT execution_id FROM execution_attempts WHERE status = 'running'"
        ).fetchall()
    ]

    return RecoveryReport(
        generated_at=datetime.now(UTC).isoformat(),
        findings=findings,
        uncertain_billing_count=uncertain_count,
        billed_without_validated_artifact_count=billed_without_artifact_count,
        confirmed_not_billed_count=confirmed_not_billed_count,
        retry_eligible_count=confirmed_not_billed_count,
        stale_running_attempt_count=len(stale_running_attempts),
        automatic_retry_allowed=False,
        retry_eligible_under_new_authorization=confirmed_not_billed_count > 0,
        quarantine_recommended=quarantine_recommended,
        manual_recovery_required=sorted(set(manual_recovery_required)),
        stale_running_attempts=stale_running_attempts,
        retried=0,
        deleted=0,
    )
