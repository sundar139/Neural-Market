"""Resumable SQLite request journal for the acquisition pipeline.

Tracks per-request execution progress so a crashed or interrupted pilot run
can resume without re-requesting already-downloaded data. Uses stdlib
``sqlite3`` only -- no ORM. State transitions are enforced against the
shared allow-list in :mod:`neuralmarket.data.acquisition.states` so an
executor bug (e.g. skipping preflight) fails loudly instead of silently
corrupting the journal.

No API key, account ID, or billing-header field is stored here: only
request identity, lifecycle state, and cost/path bookkeeping that is safe to
keep on disk.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.states import ALLOWED_TRANSITIONS

JOURNAL_SCHEMA_VERSION = 1

_COLUMNS = (
    "request_id",
    "request_hash",
    "state",
    "attempt_count",
    "estimated_cost_usd",
    "actual_billed_cost_usd",
    "raw_path",
    "raw_checksum",
    "normalized_path",
    "normalized_checksum",
    "failure_category",
    "failure_message",
    "created_at",
    "updated_at",
)


class JournalEntry(BaseModel):
    """One request's persisted lifecycle state in the journal."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    request_hash: str
    state: str
    attempt_count: int
    estimated_cost_usd: str
    actual_billed_cost_usd: str | None
    raw_path: str | None
    raw_checksum: str | None
    normalized_path: str | None
    normalized_checksum: str | None
    failure_category: str | None
    failure_message: str | None
    created_at: str
    updated_at: str


class RequestJournal:
    """Transactional, resumable SQLite journal of acquisition request state."""

    def __init__(self, db_path: Path) -> None:
        """Open or create the journal SQLite database at ``db_path``."""
        self._connection = sqlite3.connect(db_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    def _migrate(self) -> None:
        with self._connection:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER NOT NULL)"
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    estimated_cost_usd TEXT NOT NULL,
                    actual_billed_cost_usd TEXT,
                    raw_path TEXT,
                    raw_checksum TEXT,
                    normalized_path TEXT,
                    normalized_checksum TEXT,
                    failure_category TEXT,
                    failure_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            row = self._connection.execute("SELECT version FROM schema_meta").fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_meta (version) VALUES (?)", (JOURNAL_SCHEMA_VERSION,)
                )

    def upsert(self, entry: JournalEntry) -> None:
        """Insert or update ``entry``'s row, rejecting illegal state transitions."""
        with self._connection:
            row = self._connection.execute(
                "SELECT state FROM requests WHERE request_id = ?", (entry.request_id,)
            ).fetchone()
            if row is not None:
                old_state = row[0]
                if old_state != entry.state and (old_state, entry.state) not in ALLOWED_TRANSITIONS:
                    raise ValueError(
                        f"illegal state transition: {old_state} -> {entry.state}"
                    )
            values = tuple(getattr(entry, column) for column in _COLUMNS)
            placeholders = ", ".join("?" for _ in _COLUMNS)
            update_clause = ", ".join(f"{c} = excluded.{c}" for c in _COLUMNS if c != "request_id")
            self._connection.execute(
                f"""
                INSERT INTO requests ({", ".join(_COLUMNS)}) VALUES ({placeholders})
                ON CONFLICT(request_id) DO UPDATE SET {update_clause}
                """,
                values,
            )

    def get(self, request_id: str) -> JournalEntry | None:
        """Return the journal entry for ``request_id``, or ``None`` if absent."""
        row = self._connection.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if row is None:
            return None
        return JournalEntry(**dict(zip(_COLUMNS, row, strict=True)))

    def all(self) -> list[JournalEntry]:
        """Return every journal entry, in no particular order."""
        rows = self._connection.execute(f"SELECT {', '.join(_COLUMNS)} FROM requests").fetchall()
        return [JournalEntry(**dict(zip(_COLUMNS, row, strict=True))) for row in rows]

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._connection.close()

    def __enter__(self) -> RequestJournal:
        """Return ``self`` for use as a context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the journal on context-manager exit."""
        self.close()
