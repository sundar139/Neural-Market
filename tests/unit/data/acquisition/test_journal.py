import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal

pytestmark = pytest.mark.unit


def _entry(request_id: str = "req-1", state: str = "planned") -> JournalEntry:
    now = datetime.now(UTC).isoformat()
    return JournalEntry(
        request_id=request_id,
        request_hash="a" * 64,
        state=state,
        attempt_count=0,
        estimated_cost_usd="0.05",
        actual_billed_cost_usd=None,
        raw_path=None,
        raw_checksum=None,
        normalized_path=None,
        normalized_checksum=None,
        failure_category=None,
        failure_message=None,
        created_at=now,
        updated_at=now,
    )


def test_upsert_and_get_roundtrip(tmp_path: Path) -> None:
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        journal.upsert(_entry())
        fetched = journal.get("req-1")
    assert fetched is not None
    assert fetched.state == "planned"


def test_no_api_key_or_billing_id_field_exists() -> None:
    fields = set(JournalEntry.model_fields)
    assert not fields & {"api_key", "account_id", "billing_id", "request_headers"}


def test_illegal_state_transition_is_rejected(tmp_path: Path) -> None:
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        journal.upsert(_entry(state="planned"))
        with pytest.raises(ValueError, match="transition"):
            journal.upsert(_entry(state="normalized"))


def test_same_state_reupsert_is_idempotent_then_allows_legal_transition(tmp_path: Path) -> None:
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        journal.upsert(_entry(state="planned"))
        journal.upsert(_entry(state="planned"))
        fetched = journal.get("req-1")
        assert fetched is not None
        assert fetched.state == "planned"

        journal.upsert(_entry(state="preflight_validated"))
        fetched = journal.get("req-1")
        assert fetched is not None
        assert fetched.state == "preflight_validated"


def test_request_hash_is_immutable(tmp_path: Path) -> None:
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        entry = _entry()
        journal.upsert(entry)
        with pytest.raises(ValueError, match="hash is immutable"):
            journal.upsert(entry.model_copy(update={"request_hash": "b" * 64}))


def test_journal_persists_across_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "journal.sqlite"
    with RequestJournal(db_path) as journal:
        journal.upsert(_entry())
    with RequestJournal(db_path) as reopened:
        assert reopened.get("req-1") is not None


def test_all_returns_every_entry(tmp_path: Path) -> None:
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        journal.upsert(_entry("req-1"))
        journal.upsert(_entry("req-2"))
        assert {e.request_id for e in journal.all()} == {"req-1", "req-2"}


def test_authorization_consumption_is_atomic_and_durable(tmp_path: Path) -> None:
    db_path = tmp_path / "journal.sqlite"
    with RequestJournal(db_path) as journal:
        assert journal.consume_authorization(
            plan_hash="p" * 64,
            authorization_hash="a" * 64,
            consumed_at=datetime.now(UTC).isoformat(),
        )
        assert not journal.consume_authorization(
            plan_hash="p" * 64,
            authorization_hash="b" * 64,
            consumed_at=datetime.now(UTC).isoformat(),
        )
    with RequestJournal(db_path) as reopened:
        assert reopened.consumed_authorization_ids() == {"p" * 64}


def test_journal_migrates_prior_request_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "journal.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE schema_meta (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_meta VALUES (2)")
        connection.execute(
            """
            CREATE TABLE requests (
                request_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
                state TEXT NOT NULL, attempt_count INTEGER NOT NULL,
                estimated_cost_usd TEXT NOT NULL, actual_billed_cost_usd TEXT,
                raw_path TEXT, raw_checksum TEXT, normalized_path TEXT,
                normalized_checksum TEXT, failure_category TEXT,
                failure_message TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
    with RequestJournal(db_path):
        pass
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(requests)")}
        version = connection.execute("SELECT version FROM schema_meta").fetchone()
    assert {"raw_byte_count", "raw_record_count", "provider_response_id"} <= columns
    assert version == (6,)


def test_release_reservation_terminalizes_provider_construction_attempt(tmp_path: Path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    assert journal.reserve_authorization(
        authorization_hash="a" * 64,
        plan_hash="p" * 64,
        execution_id="execution",
        reserved_at="2026-07-14T00:00:00+00:00",
    )
    assert journal.release_reservation(
        authorization_hash="a" * 64,
        execution_id="execution",
        message="paid provider construction failed",
    )
    row = journal.connection.execute(
        "SELECT status, finished_at FROM execution_attempts WHERE execution_id = ?",
        ("execution",),
    ).fetchone()
    assert row[0] == "failed_provider_construction"
    assert row[1] is not None
    consumed = journal.connection.execute("SELECT count(*) FROM consumed_authorizations").fetchone()
    assert consumed[0] == 0
