"""Offline, read-only recovery inspection for the acquisition journal.

Compares journal state against the filesystem and reports discrepancies.
This module is strictly read-only: it never writes to the journal (only
``.all()``), never retries a request, and never deletes a file -- including
stale ``.partial`` files. Any remediation (quarantine, retry, deletion) is a
separate explicit action taken elsewhere.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from neuralmarket.data.acquisition.journal import RequestJournal
from neuralmarket.data.raw.integrity import verify_checksum

_RAW_PRESENT_STATES = frozenset({"raw_validated", "normalized", "quality_validated"})


class RecoveryFinding(BaseModel):
    """One anomaly (or confirmation) observed for a single request."""

    request_id: str
    category: Literal[
        "journal_missing_file", "checksum_mismatch", "stale_partial", "consistent"
    ]
    detail: str


class RecoveryReport(BaseModel):
    """Read-only summary of a recovery inspection run."""

    generated_at: str
    findings: list[RecoveryFinding]
    quarantine_recommended: list[str]
    manual_recovery_required: list[str]
    retried: int
    deleted: int


def run_recovery(*, journal: RequestJournal, data_root: Path) -> RecoveryReport:
    """Inspect the journal and filesystem for recovery-worthy anomalies.

    Read-only: only calls ``journal.all()``, never mutates the journal, and
    never deletes or renames anything on disk (including stale ``.partial``
    files).
    """
    findings: list[RecoveryFinding] = []
    quarantine_recommended: list[str] = []
    manual_recovery_required: list[str] = []

    for entry in journal.all():
        if entry.state in _RAW_PRESENT_STATES and entry.raw_path is not None:
            path = data_root / entry.raw_path
            if not path.exists():
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="journal_missing_file",
                        detail=f"journal state {entry.state!r} but file missing: {path}",
                    )
                )
                quarantine_recommended.append(entry.request_id)
            elif entry.raw_checksum is not None and not verify_checksum(path, entry.raw_checksum):
                findings.append(
                    RecoveryFinding(
                        request_id=entry.request_id,
                        category="checksum_mismatch",
                        detail=f"checksum mismatch for {path}",
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

        # ponytail: scan the whole data_root for this request's stray
        # .partial files rather than deriving an "expected directory" --
        # raw_path is often still None (e.g. pre-download states), so there
        # is no per-entry directory to scope to yet. Upgrade to a scoped
        # glob if data_root ever grows large enough for this to matter.
        partials = sorted(data_root.rglob(f"{entry.request_id}*.partial"))
        for partial in partials:
            findings.append(
                RecoveryFinding(
                    request_id=entry.request_id,
                    category="stale_partial",
                    detail=f"stale partial file found: {partial}",
                )
            )
            manual_recovery_required.append(entry.request_id)

    return RecoveryReport(
        generated_at=datetime.now(UTC).isoformat(),
        findings=findings,
        quarantine_recommended=quarantine_recommended,
        manual_recovery_required=manual_recovery_required,
        retried=0,
        deleted=0,
    )
