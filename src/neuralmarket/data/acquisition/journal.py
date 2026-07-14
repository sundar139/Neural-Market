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
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.states import ALLOWED_TRANSITIONS

JOURNAL_SCHEMA_VERSION = 6

_COLUMNS = (
    "request_id",
    "request_hash",
    "state",
    "attempt_count",
    "estimated_cost_usd",
    "actual_billed_cost_usd",
    "raw_path",
    "raw_checksum",
    "raw_byte_count",
    "raw_record_count",
    "provider_response_id",
    "request_started_at",
    "request_completed_at",
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
    raw_byte_count: int | None = None
    raw_record_count: int | None = None
    provider_response_id: str | None = None
    request_started_at: str | None = None
    request_completed_at: str | None = None


class RequestJournal:
    """Transactional, resumable SQLite journal of acquisition request state."""

    def __init__(self, db_path: Path) -> None:
        """Open or create the journal SQLite database at ``db_path``."""
        self._connection = sqlite3.connect(db_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    @property
    def connection(self) -> sqlite3.Connection:
        """Expose the underlying connection for coordinated journal transactions."""
        return self._connection

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
                    raw_byte_count INTEGER,
                    raw_record_count INTEGER,
                    provider_response_id TEXT,
                    request_started_at TEXT,
                    request_completed_at TEXT,
                    normalized_path TEXT,
                    normalized_checksum TEXT,
                    failure_category TEXT,
                    failure_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS consumed_authorizations (
                    plan_hash TEXT PRIMARY KEY,
                    authorization_hash TEXT NOT NULL,
                    consumed_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS execution_attempts (
                    execution_id TEXT PRIMARY KEY,
                    plan_hash TEXT NOT NULL,
                    authorization_hash TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    finished_at TEXT,
                    blocking_request TEXT,
                    blocking_state TEXT,
                    requests_completed INTEGER,
                    requests_uncertain INTEGER,
                    paid_request_calls INTEGER,
                    downloaded_records INTEGER,
                    manual_action_required INTEGER
                )
            """)
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS request_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_at TEXT NOT NULL,
                    detail_json TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS billing_reconciliations (
                    artifact_hash TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    authorization_hash TEXT NOT NULL,
                    portal_review_status TEXT NOT NULL,
                    observed_usage_usd TEXT NOT NULL,
                    billing_resolution TEXT NOT NULL,
                    retry_eligible INTEGER NOT NULL,
                    manual_action_required INTEGER NOT NULL,
                    reviewed_by TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    review_method TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    UNIQUE(execution_id, request_id)
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS authorization_reservations (
                    authorization_hash TEXT PRIMARY KEY,
                    plan_hash TEXT NOT NULL,
                    execution_id TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL
                        CHECK(state IN ('available','reserved','consumed','voided')),
                    reserved_at TEXT,
                    consumed_at TEXT,
                    failure_message TEXT
                )
                """
            )
            row = self._connection.execute("SELECT version FROM schema_meta").fetchone()
            request_columns = {
                str(column[1])
                for column in self._connection.execute("PRAGMA table_info(requests)").fetchall()
            }
            for column, statement in {
                "raw_byte_count": "ALTER TABLE requests ADD COLUMN raw_byte_count INTEGER",
                "raw_record_count": "ALTER TABLE requests ADD COLUMN raw_record_count INTEGER",
                "provider_response_id": "ALTER TABLE requests ADD COLUMN provider_response_id TEXT",
                "request_started_at": "ALTER TABLE requests ADD COLUMN request_started_at TEXT",
                "request_completed_at": "ALTER TABLE requests ADD COLUMN request_completed_at TEXT",
            }.items():
                if column not in request_columns:
                    self._connection.execute(statement)
            consumed_columns = {
                str(column[1])
                for column in self._connection.execute(
                    "PRAGMA table_info(consumed_authorizations)"
                ).fetchall()
            }
            for column, statement in {
                "execution_id": "ALTER TABLE consumed_authorizations ADD COLUMN execution_id TEXT",
                "maximum_authorized_spend_usd": (
                    "ALTER TABLE consumed_authorizations "
                    "ADD COLUMN maximum_authorized_spend_usd TEXT"
                ),
                "currency": "ALTER TABLE consumed_authorizations ADD COLUMN currency TEXT",
            }.items():
                if column not in consumed_columns:
                    self._connection.execute(statement)
            attempt_columns = {
                str(column[1])
                for column in self._connection.execute(
                    "PRAGMA table_info(execution_attempts)"
                ).fetchall()
            }
            for column, statement in {
                "finished_at": "ALTER TABLE execution_attempts ADD COLUMN finished_at TEXT",
                "blocking_request": "ALTER TABLE execution_attempts ADD COLUMN blocking_request TEXT",  # noqa: E501
                "blocking_state": "ALTER TABLE execution_attempts ADD COLUMN blocking_state TEXT",
                "requests_completed": "ALTER TABLE execution_attempts ADD COLUMN requests_completed INTEGER",  # noqa: E501
                "requests_uncertain": "ALTER TABLE execution_attempts ADD COLUMN requests_uncertain INTEGER",  # noqa: E501
                "paid_request_calls": "ALTER TABLE execution_attempts ADD COLUMN paid_request_calls INTEGER",  # noqa: E501
                "downloaded_records": "ALTER TABLE execution_attempts ADD COLUMN downloaded_records INTEGER",  # noqa: E501
                "manual_action_required": (
                    "ALTER TABLE execution_attempts ADD COLUMN manual_action_required INTEGER"
                ),
            }.items():
                if column not in attempt_columns:
                    self._connection.execute(statement)
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_meta (version) VALUES (?)", (JOURNAL_SCHEMA_VERSION,)
                )
            elif int(row[0]) > JOURNAL_SCHEMA_VERSION:
                raise RuntimeError(f"journal schema version {row[0]} is newer than supported")
            elif int(row[0]) < JOURNAL_SCHEMA_VERSION:
                self._connection.execute(
                    "UPDATE schema_meta SET version = ?", (JOURNAL_SCHEMA_VERSION,)
                )

    def consumed_authorization_ids(self) -> set[str]:
        """Return plan hashes whose one-time authorization has been consumed."""
        rows = self._connection.execute("SELECT plan_hash FROM consumed_authorizations").fetchall()
        return {str(row[0]) for row in rows}

    def reserve_authorization(
        self, *, authorization_hash: str, plan_hash: str, execution_id: str, reserved_at: str
    ) -> bool:
        """Reserve an authorization for exactly one execution transactionally."""
        try:
            with self._connection:
                row = self._connection.execute(
                    "SELECT state FROM authorization_reservations WHERE authorization_hash = ?",
                    (authorization_hash,),
                ).fetchone()
                if row is not None:
                    return False
                self._connection.execute(
                    "INSERT INTO authorization_reservations "
                    "(authorization_hash, plan_hash, execution_id, state, reserved_at) "
                    "VALUES (?, ?, ?, 'reserved', ?)",
                    (authorization_hash, plan_hash, execution_id, reserved_at),
                )
                self._connection.execute(
                    "INSERT INTO execution_attempts "
                    "(execution_id, plan_hash, authorization_hash, started_at, status) "
                    "VALUES (?, ?, ?, ?, 'running')",
                    (execution_id, plan_hash, authorization_hash, reserved_at),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def release_reservation(
        self, *, authorization_hash: str, execution_id: str, message: str
    ) -> bool:
        """Release an unused reservation after local provider construction fails."""
        with self._connection:
            self._connection.execute(
                "UPDATE execution_attempts SET status = ?, finished_at = ?, "
                "blocking_state = ?, manual_action_required = 0 "
                "WHERE execution_id = ? AND status = 'running'",
                (
                    "failed_provider_construction",
                    datetime.now(UTC).isoformat(),
                    "provider_construction_failed",
                    execution_id,
                ),
            )
            count = self._connection.execute(
                "DELETE FROM authorization_reservations WHERE authorization_hash = ? "
                "AND execution_id = ? AND state = 'reserved'",
                (authorization_hash, execution_id),
            ).rowcount
        return bool(count)

    def consume_reserved_authorization(
        self, *, authorization_hash: str, execution_id: str, consumed_at: str
    ) -> bool:
        """Consume a reservation immediately before the first paid invocation."""
        with self._connection:
            count = self._connection.execute(
                "UPDATE authorization_reservations SET state = 'consumed', consumed_at = ? "
                "WHERE authorization_hash = ? AND execution_id = ? AND state = 'reserved'",
                (consumed_at, authorization_hash, execution_id),
            ).rowcount
            if count:
                plan_hash = self._connection.execute(
                    "SELECT plan_hash FROM authorization_reservations WHERE authorization_hash = ?",
                    (authorization_hash,),
                ).fetchone()[0]
                self._connection.execute(
                    "INSERT INTO consumed_authorizations "
                    "(plan_hash, authorization_hash, consumed_at, execution_id) "
                    "VALUES (?, ?, ?, ?)",
                    (plan_hash, authorization_hash, consumed_at, execution_id),
                )
                self._connection.execute(
                    "INSERT OR IGNORE INTO execution_attempts "
                    "(execution_id, plan_hash, authorization_hash, started_at, status) "
                    "VALUES (?, ?, ?, ?, 'running')",
                    (execution_id, plan_hash, authorization_hash, consumed_at),
                )
        return bool(count)

    def finalize_execution_attempt(
        self,
        *,
        execution_id: str,
        status: str,
        finished_at: str,
        blocking_request: str | None,
        blocking_state: str | None,
        requests_completed: int,
        requests_uncertain: int,
        paid_request_calls: int,
        downloaded_records: int,
        manual_action_required: bool,
    ) -> bool:
        """Finalize a known execution outcome without changing authorization state."""
        with self._connection:
            count = self._connection.execute(
                "UPDATE execution_attempts SET status = ?, finished_at = ?, blocking_request = ?, "
                "blocking_state = ?, requests_completed = ?, requests_uncertain = ?, "
                "paid_request_calls = ?, downloaded_records = ?, manual_action_required = ? "
                "WHERE execution_id = ? AND status = 'running'",
                (
                    status,
                    finished_at,
                    blocking_request,
                    blocking_state,
                    requests_completed,
                    requests_uncertain,
                    paid_request_calls,
                    downloaded_records,
                    int(manual_action_required),
                    execution_id,
                ),
            ).rowcount
        return bool(count)

    def consume_authorization(
        self, *, plan_hash: str, authorization_hash: str, consumed_at: str
    ) -> bool:
        """Atomically consume a plan authorization; return false if already used."""
        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO consumed_authorizations
                        (plan_hash, authorization_hash, consumed_at)
                    VALUES (?, ?, ?)
                    """,
                    (plan_hash, authorization_hash, consumed_at),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def consume_authorization_and_create_execution(
        self,
        *,
        plan_hash: str,
        authorization_hash: str,
        consumed_at: str,
        execution_id: str,
        maximum_authorized_spend_usd: str,
        currency: str,
    ) -> bool:
        """Consume authorization and create the execution attempt atomically."""
        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO consumed_authorizations
                        (plan_hash, authorization_hash, consumed_at, execution_id,
                         maximum_authorized_spend_usd, currency)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        plan_hash,
                        authorization_hash,
                        consumed_at,
                        execution_id,
                        maximum_authorized_spend_usd,
                        currency,
                    ),
                )
                self._connection.execute(
                    """
                    INSERT INTO execution_attempts
                        (execution_id, plan_hash, authorization_hash, started_at, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (execution_id, plan_hash, authorization_hash, consumed_at, "authorized"),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def upsert(self, entry: JournalEntry) -> None:
        """Insert or update ``entry``'s row, rejecting illegal state transitions."""
        with self._connection:
            row = self._connection.execute(
                "SELECT state, request_hash FROM requests WHERE request_id = ?",
                (entry.request_id,),
            ).fetchone()
            if row is not None:
                old_state = row[0]
                if old_state != entry.state and (old_state, entry.state) not in ALLOWED_TRANSITIONS:
                    raise ValueError(f"illegal state transition: {old_state} -> {entry.state}")
                if row[1] != entry.request_hash:
                    raise ValueError(f"request hash is immutable for request {entry.request_id}")
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
