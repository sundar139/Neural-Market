from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal


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
