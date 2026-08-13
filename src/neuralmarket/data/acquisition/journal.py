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

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.states import ALLOWED_TRANSITIONS

JOURNAL_SCHEMA_VERSION = 10

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
        self._db_path = db_path
        self._connection = sqlite3.connect(db_path)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    @property
    def connection(self) -> sqlite3.Connection:
        """Expose the underlying connection for coordinated journal transactions."""
        return self._connection

    @property
    def db_path(self) -> Path:
        """Return the journal path for immutable recovery-state revalidation."""
        return self._db_path

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
                    authorization_hash TEXT PRIMARY KEY,
                    plan_hash TEXT NOT NULL,
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
                    supersedes_reconciliation_hash TEXT,
                    supersession_reason TEXT,
                    supersession_evidence_method TEXT,
                    supersession_sequence INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(execution_id, request_id, supersession_sequence)
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
                "actual_provider_cost_status": (
                    "ALTER TABLE requests ADD COLUMN actual_provider_cost_status TEXT"
                ),
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
            reconciliation_columns = {
                str(column[1])
                for column in self._connection.execute(
                    "PRAGMA table_info(billing_reconciliations)"
                ).fetchall()
            }
            if "supersession_sequence" not in reconciliation_columns:
                self._connection.execute(
                    "ALTER TABLE billing_reconciliations RENAME TO billing_reconciliations_old"
                )
                self._connection.execute(
                    """
                    CREATE TABLE billing_reconciliations (
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
                        supersedes_reconciliation_hash TEXT,
                        supersession_reason TEXT,
                        supersession_evidence_method TEXT,
                        supersession_sequence INTEGER NOT NULL DEFAULT 1,
                        UNIQUE(execution_id, request_id, supersession_sequence)
                    )
                    """
                )
                self._connection.execute(
                    """
                    INSERT INTO billing_reconciliations (
                        artifact_hash, execution_id, request_id, plan_hash, authorization_hash,
                        portal_review_status, observed_usage_usd, billing_resolution,
                        retry_eligible, manual_action_required, reviewed_by, reviewed_at,
                        review_method, applied_at, supersession_sequence
                    )
                    SELECT artifact_hash, execution_id, request_id, plan_hash, authorization_hash,
                        portal_review_status, observed_usage_usd, billing_resolution,
                        retry_eligible, manual_action_required, reviewed_by, reviewed_at,
                        review_method, applied_at, 1
                    FROM billing_reconciliations_old
                    """
                )
                self._connection.execute("DROP TABLE billing_reconciliations_old")
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_meta (version) VALUES (?)", (JOURNAL_SCHEMA_VERSION,)
                )
            elif int(row[0]) > JOURNAL_SCHEMA_VERSION:
                raise RuntimeError(f"journal schema version {row[0]} is newer than supported")
            elif int(row[0]) < JOURNAL_SCHEMA_VERSION:
                # --- v7 → v8: remove stale execution_attempts FK -----------------
                # Historical databases may retain a FOREIGN KEY (plan_hash)
                # REFERENCES consumed_authorizations (plan_hash) that was removed
                # from the CREATE TABLE code but never explicitly migrated away.
                # The FK prevents inserting execution attempts for new recovery
                # plans until their authorization is consumed, which creates a
                # circular dependency.
                # ponytail: rebuild only the affected table; the other migration
                # blocks already keep column-level upgrades idempotent.
                if int(row[0]) <= 7:
                    fks = self._connection.execute(
                        "PRAGMA foreign_key_list('execution_attempts')"
                    ).fetchall()
                    stale_fk = any(
                        fk[2] == "consumed_authorizations" and fk[3] == "plan_hash" for fk in fks
                    )
                    if stale_fk:
                        # Verify column set matches current schema exactly.
                        expected_cols = {
                            "execution_id",
                            "plan_hash",
                            "authorization_hash",
                            "started_at",
                            "status",
                            "finished_at",
                            "blocking_request",
                            "blocking_state",
                            "requests_completed",
                            "requests_uncertain",
                            "paid_request_calls",
                            "downloaded_records",
                            "manual_action_required",
                        }
                        actual_cols = {
                            str(c[1])
                            for c in self._connection.execute(
                                "PRAGMA table_info('execution_attempts')"
                            ).fetchall()
                        }
                        if actual_cols != expected_cols:
                            raise RuntimeError(
                                "execution_attempts schema has drifted; "
                                "cannot migrate stale FK safely"
                            )
                        before = self._connection.execute(
                            "SELECT COUNT(*) FROM execution_attempts"
                        ).fetchone()[0]
                        self._connection.execute(
                            "CREATE TABLE execution_attempts_v8 ("
                            "execution_id TEXT PRIMARY KEY,"
                            "plan_hash TEXT NOT NULL,"
                            "authorization_hash TEXT NOT NULL,"
                            "started_at TEXT NOT NULL,"
                            "status TEXT NOT NULL,"
                            "finished_at TEXT,"
                            "blocking_request TEXT,"
                            "blocking_state TEXT,"
                            "requests_completed INTEGER,"
                            "requests_uncertain INTEGER,"
                            "paid_request_calls INTEGER,"
                            "downloaded_records INTEGER,"
                            "manual_action_required INTEGER"
                            ")"
                        )
                        self._connection.execute(
                            "INSERT INTO execution_attempts_v8 ("
                            "execution_id, plan_hash, authorization_hash,"
                            "started_at, status, finished_at,"
                            "blocking_request, blocking_state,"
                            "requests_completed, requests_uncertain,"
                            "paid_request_calls, downloaded_records,"
                            "manual_action_required"
                            ") SELECT "
                            "execution_id, plan_hash, authorization_hash,"
                            "started_at, status, finished_at,"
                            "blocking_request, blocking_state,"
                            "requests_completed, requests_uncertain,"
                            "paid_request_calls, downloaded_records,"
                            "manual_action_required "
                            "FROM execution_attempts"
                        )
                        after = self._connection.execute(
                            "SELECT COUNT(*) FROM execution_attempts_v8"
                        ).fetchone()[0]
                        if after != before:
                            raise RuntimeError(
                                "execution_attempts row count mismatch during FK migration"
                            )
                        self._connection.execute("DROP TABLE execution_attempts")
                        self._connection.execute(
                            "ALTER TABLE execution_attempts_v8 RENAME TO execution_attempts"
                        )
                # --- v9 → v10: key consumption on the exact authorization -------
                if int(row[0]) <= 9:
                    self._rekey_consumed_authorizations()
                self._connection.execute(
                    "UPDATE schema_meta SET version = ?", (JOURNAL_SCHEMA_VERSION,)
                )

    def _rekey_consumed_authorizations(self) -> None:
        """Rebuild ``consumed_authorizations`` with ``authorization_hash`` as the key.

        Consumption was keyed on ``plan_hash``, so a plan could record only one
        consumed authorization ever — the settled authorization blocked every
        later one for the same plan. Runs inside the caller's ``_migrate``
        transaction: any raise rolls the whole thing back and leaves the
        original table in place.

        Raises:
            RuntimeError: If any historical ``authorization_hash`` is absent,
                not 64-character lowercase hex, or duplicated. Identities are
                never derived or invented from the plan hash.
        """
        table = self._connection.execute("PRAGMA table_info(consumed_authorizations)").fetchall()
        columns = [str(column[1]) for column in table]
        if [str(column[1]) for column in table if column[5]] == ["authorization_hash"]:
            return

        rows = self._connection.execute(
            "SELECT authorization_hash FROM consumed_authorizations"
        ).fetchall()
        seen: set[str] = set()
        for (authorization_hash,) in rows:
            candidate = str(authorization_hash or "")
            if len(candidate) != 64 or not all(c in "0123456789abcdef" for c in candidate):
                raise RuntimeError(
                    "consumed_authorizations holds an unusable authorization_hash; "
                    "refusing to rekey consumption"
                )
            if candidate in seen:
                raise RuntimeError(
                    "consumed_authorizations holds a duplicate authorization_hash; "
                    "refusing to rekey consumption"
                )
            seen.add(candidate)

        carried = ", ".join(columns)
        self._connection.execute(
            "CREATE TABLE consumed_authorizations_v10 ("
            "authorization_hash TEXT PRIMARY KEY,"
            "plan_hash TEXT NOT NULL,"
            "consumed_at TEXT NOT NULL,"
            "execution_id TEXT,"
            "maximum_authorized_spend_usd TEXT,"
            "currency TEXT"
            ")"
        )
        self._connection.execute(
            f"INSERT INTO consumed_authorizations_v10 ({carried}) "
            f"SELECT {carried} FROM consumed_authorizations"
        )
        migrated = self._connection.execute(
            "SELECT COUNT(*) FROM consumed_authorizations_v10"
        ).fetchone()[0]
        if migrated != len(rows):
            raise RuntimeError("consumed_authorizations row count mismatch during rekey")
        self._connection.execute("DROP TABLE consumed_authorizations")
        self._connection.execute(
            "ALTER TABLE consumed_authorizations_v10 RENAME TO consumed_authorizations"
        )

    def consumed_authorization_ids(self) -> set[str]:
        """Return plan hashes whose one-time authorization has been consumed."""
        rows = self._connection.execute("SELECT plan_hash FROM consumed_authorizations").fetchall()
        return {str(row[0]) for row in rows}

    def consumed_authorization_identities(self) -> set[str]:
        """Return the exact identity of every consumed authorization.

        Replay protection keys on ``authorization_hash``, which distinguishes
        two authorizations that share the canonical plan hash (for example a
        settled single-request authorization and a later remaining-scope one).
        A legacy row whose ``authorization_hash`` is not a usable 64-hex digest
        cannot be resolved that precisely, so it falls back to its ``plan_hash``
        and keeps blocking the whole plan rather than silently permitting it.
        """
        rows = self._connection.execute(
            "SELECT plan_hash, authorization_hash FROM consumed_authorizations"
        ).fetchall()
        identities: set[str] = set()
        for plan_hash, authorization_hash in rows:
            candidate = str(authorization_hash or "")
            usable = len(candidate) == 64 and all(c in "0123456789abcdef" for c in candidate)
            identities.add(candidate if usable else str(plan_hash))
        return identities

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

    def reserve_recovery_authorization(
        self,
        *,
        authorization_hash: str,
        execution_id: str,
        reserved_at: str,
        request_id: str,
        request_hash: str,
        recovery_plan_hash: str,
        parent_plan_hash: str,
        reconciliation_hash: str,
    ) -> bool:
        """Atomically reserve authorization and claim the reconciled request."""
        detail = json.dumps(
            {
                "recovery_plan_hash": recovery_plan_hash,
                "parent_plan_hash": parent_plan_hash,
                "reconciliation_hash": reconciliation_hash,
            },
            sort_keys=True,
        )
        try:
            with self._connection:
                if self._connection.execute(
                    "SELECT 1 FROM authorization_reservations WHERE authorization_hash = ?",
                    (authorization_hash,),
                ).fetchone():
                    return False
                self._connection.execute(
                    "INSERT INTO authorization_reservations "
                    "(authorization_hash, plan_hash, execution_id, state, reserved_at) "
                    "VALUES (?, ?, ?, 'reserved', ?)",
                    (authorization_hash, recovery_plan_hash, execution_id, reserved_at),
                )
                self._connection.execute(
                    "INSERT INTO execution_attempts "
                    "(execution_id, plan_hash, authorization_hash, started_at, status) "
                    "VALUES (?, ?, ?, ?, 'running')",
                    (execution_id, recovery_plan_hash, authorization_hash, reserved_at),
                )
                updated = self._connection.execute(
                    "UPDATE requests SET state = 'preflight_validated', updated_at = ? "
                    "WHERE request_id = ? AND request_hash = ? "
                    "AND state = 'retry_eligible_after_manual_nonbilling_confirmation' "
                    "AND attempt_count = 1 "
                    "AND request_completed_at IS NULL AND actual_billed_cost_usd IS NULL "
                    "AND raw_path IS NULL AND raw_checksum IS NULL "
                    "AND raw_byte_count IS NULL AND raw_record_count IS NULL "
                    "AND provider_response_id IS NULL "
                    "AND normalized_path IS NULL AND normalized_checksum IS NULL",
                    (reserved_at, request_id, request_hash),
                )
                if updated.rowcount != 1:
                    raise ValueError("recovery request is no longer eligible")
                self._connection.execute(
                    "INSERT INTO request_events (request_id, event_type, event_at, detail_json) "
                    "VALUES (?, 'recovery_execution_started', ?, ?)",
                    (request_id, reserved_at, detail),
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def release_recovery_reservation(
        self, *, authorization_hash: str, execution_id: str, request_id: str
    ) -> bool:
        """Undo a nonbillable recovery claim when provider construction fails."""
        now = datetime.now(UTC).isoformat()
        with self._connection:
            reverted = self._connection.execute(
                "UPDATE requests SET state = "
                "'retry_eligible_after_manual_nonbilling_confirmation', updated_at = ? "
                "WHERE request_id = ? AND state = 'preflight_validated' "
                "AND attempt_count = 1 AND request_completed_at IS NULL "
                "AND actual_billed_cost_usd IS NULL AND raw_path IS NULL "
                "AND raw_checksum IS NULL AND raw_byte_count IS NULL "
                "AND raw_record_count IS NULL AND provider_response_id IS NULL "
                "AND normalized_path IS NULL AND normalized_checksum IS NULL",
                (now, request_id),
            ).rowcount
            if reverted != 1:
                raise ValueError("recovery request could not be released safely")
            self._connection.execute(
                "INSERT INTO request_events (request_id, event_type, event_at, detail_json) "
                "VALUES (?, 'recovery_execution_released', ?, '{}')",
                (request_id, now),
            )
            self._connection.execute(
                "UPDATE execution_attempts SET status = 'failed_provider_construction', "
                "finished_at = ?, blocking_state = 'provider_construction_failed', "
                "manual_action_required = 0 WHERE execution_id = ? AND status = 'running'",
                (now, execution_id),
            )
            deleted = self._connection.execute(
                "DELETE FROM authorization_reservations WHERE authorization_hash = ? "
                "AND execution_id = ? AND state = 'reserved'",
                (authorization_hash, execution_id),
            ).rowcount
            if deleted != 1:
                raise ValueError("recovery authorization reservation could not be released")
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
        self,
        *,
        authorization_hash: str,
        execution_id: str,
        consumed_at: str,
        maximum_authorized_spend_usd: str | None = None,
    ) -> bool:
        """Consume a reservation immediately before the first paid invocation.

        Returns ``False`` when this exact authorization was already consumed, so
        the caller fails closed on a clean guard error rather than a raw
        ``sqlite3.IntegrityError`` from the primary key. A second, distinct
        authorization sharing the same ``plan_hash`` is permitted.
        """
        with self._connection:
            if self._connection.execute(
                "SELECT 1 FROM consumed_authorizations WHERE authorization_hash = ?",
                (authorization_hash,),
            ).fetchone():
                return False
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
                    "(plan_hash, authorization_hash, consumed_at, execution_id, "
                    "maximum_authorized_spend_usd, currency) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        plan_hash,
                        authorization_hash,
                        consumed_at,
                        execution_id,
                        maximum_authorized_spend_usd,
                        "USD" if maximum_authorized_spend_usd is not None else None,
                    ),
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

    def request_states(self) -> dict[str, str]:
        """Return a read-only snapshot of every request's current state."""
        rows = self._connection.execute("SELECT request_id, state FROM requests").fetchall()
        return {str(request_id): str(state) for request_id, state in rows}

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
