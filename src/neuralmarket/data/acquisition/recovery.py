"""Offline, read-only recovery inspection for the acquisition journal.

Compares journal state against the filesystem and reports discrepancies.
This module is strictly read-only: it never writes to the journal (only
``.all()``), never retries a request, and never deletes a file -- including
stale ``.partial`` files. Any remediation (quarantine, retry, deletion) is a
separate explicit action taken elsewhere.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.storage import PathSafetyError, resolve_under_data_root
from neuralmarket.data.raw.integrity import verify_checksum

_RAW_PRESENT_STATES = frozenset({"raw_validated", "normalized", "quality_validated"})


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
