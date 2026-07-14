import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.recovery import run_recovery

pytestmark = pytest.mark.unit


def _entry(
    request_id: str, state: str, raw_path: str | None, raw_checksum: str | None
) -> JournalEntry:
    now = datetime.now(UTC).isoformat()
    return JournalEntry(
        request_id=request_id,
        request_hash="a" * 64,
        state=state,
        attempt_count=1,
        estimated_cost_usd="0.05",
        actual_billed_cost_usd=None,
        raw_path=raw_path,
        raw_checksum=raw_checksum,
        normalized_path=None,
        normalized_checksum=None,
        failure_category=None,
        failure_message=None,
        created_at=now,
        updated_at=now,
    )


def test_recovery_flags_missing_file_for_journal_complete_entry(tmp_path: Path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    journal.upsert(_entry("r1", "planned", None, None))
    journal.upsert(_entry("r1", "preflight_validated", None, None))
    journal.upsert(_entry("r1", "authorized", None, None))
    journal.upsert(_entry("r1", "requesting", None, None))
    journal.upsert(_entry("r1", "downloaded", "data/raw/missing.dbn", None))
    journal.upsert(_entry("r1", "raw_validated", "data/raw/missing.dbn", "a" * 64))
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert any(f.category == "journal_missing_file" for f in report.findings)
    assert "r1" in report.quarantine_recommended
    assert report.retried == 0
    assert report.deleted == 0


def test_recovery_flags_checksum_mismatch(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "present.dbn").write_bytes(b"data")
    journal = RequestJournal(tmp_path / "journal.sqlite")
    states = (
        "planned",
        "preflight_validated",
        "authorized",
        "requesting",
        "downloaded",
        "raw_validated",
    )
    for state in states:
        journal.upsert(_entry("r1", state, "data/raw/present.dbn", "0" * 64))
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert any(f.category == "checksum_mismatch" for f in report.findings)


def test_recovery_does_not_treat_missing_checksum_as_consistent(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "present.dbn").write_bytes(b"data")
    journal = RequestJournal(tmp_path / "journal.sqlite")
    for state in (
        "planned",
        "preflight_validated",
        "authorized",
        "requesting",
        "downloaded",
        "raw_validated",
    ):
        journal.upsert(_entry("r1", state, "data/raw/present.dbn", None))
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert any(f.category == "checksum_mismatch" for f in report.findings)
    assert not any(f.category == "consistent" for f in report.findings)


@pytest.mark.parametrize(
    "sidecar",
    [
        {"sha256": "digest-only"},
        ["not", "a", "mapping"],
    ],
)
def test_recovery_requires_raw_sidecar_identity(tmp_path: Path, sidecar: object) -> None:
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    raw_path = raw_dir / "present.dbn"
    raw_path.write_bytes(b"data")
    digest = hashlib.sha256(b"data").hexdigest()
    raw_path.with_suffix(".dbn.json").write_text(json.dumps(sidecar), encoding="utf-8")
    journal = RequestJournal(tmp_path / "journal.sqlite")
    for state in (
        "planned",
        "preflight_validated",
        "authorized",
        "requesting",
        "downloaded",
        "raw_validated",
    ):
        journal.upsert(_entry("r1", state, "data/raw/present.dbn", digest))
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert any(f.category == "sidecar_mismatch" for f in report.findings)
    assert not any(f.category == "consistent" for f in report.findings)


def test_recovery_flags_stale_partial_file_without_deleting(tmp_path: Path) -> None:
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    partial = raw_dir / "req-2.dbn.partial"
    partial.write_bytes(b"incomplete")
    journal = RequestJournal(tmp_path / "journal.sqlite")
    journal.upsert(_entry("req-2", "planned", None, None))
    journal.upsert(_entry("req-2", "preflight_validated", None, None))
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert any(f.category == "stale_partial" for f in report.findings)
    assert "req-2" in report.manual_recovery_required
    assert partial.exists()  # never deleted automatically


def test_recovery_returns_empty_findings_on_empty_journal(tmp_path: Path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert report.findings == []
    assert report.retried == 0
    assert report.deleted == 0


def test_recovery_rejects_journal_path_escape(tmp_path: Path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    states = (
        "planned",
        "preflight_validated",
        "authorized",
        "requesting",
        "downloaded",
        "raw_validated",
    )
    for state in states:
        journal.upsert(_entry("r1", state, "../outside.dbn", "0" * 64))
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert any(f.category == "unsafe_path" for f in report.findings)


def test_recovery_surfaces_uncertain_billing_and_stale_attempt(tmp_path: Path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    journal.upsert(_entry("uncertain", "planned", None, None))
    journal.upsert(_entry("uncertain", "preflight_validated", None, None))
    journal.upsert(_entry("uncertain", "request_started", None, None))
    journal.upsert(_entry("uncertain", "uncertain_billing", None, None))
    assert journal.reserve_authorization(
        authorization_hash="a" * 64,
        plan_hash="p" * 64,
        execution_id="execution",
        reserved_at=datetime.now(UTC).isoformat(),
    )
    assert journal.consume_reserved_authorization(
        authorization_hash="a" * 64,
        execution_id="execution",
        consumed_at=datetime.now(UTC).isoformat(),
    )
    report = run_recovery(journal=journal, data_root=tmp_path)
    assert report.uncertain_billing_count == 1
    assert report.stale_running_attempt_count == 1
    assert report.stale_running_attempts == ["execution"]
    assert report.automatic_retry_allowed is False
    assert report.retried == 0
    assert report.deleted == 0
