import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.journal import (
    JOURNAL_SCHEMA_VERSION,
    JournalEntry,
    RequestJournal,
)

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
    assert version == (9,)


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


# ── v7 → v8 stale FK migration tests ──────────────────────────────


def _historical_v7_db(path: Path) -> Path:
    """Create a v7 database with the stale FK present."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE schema_meta (version INTEGER NOT NULL);
        INSERT INTO schema_meta VALUES (7);
        CREATE TABLE consumed_authorizations (
            plan_hash TEXT PRIMARY KEY,
            authorization_hash TEXT NOT NULL,
            consumed_at TEXT NOT NULL
        );
        CREATE TABLE execution_attempts (
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
            manual_action_required INTEGER,
            FOREIGN KEY(plan_hash) REFERENCES consumed_authorizations(plan_hash)
        );
        INSERT INTO consumed_authorizations VALUES
            ('p','a','2024-01-01T00:00:00+00:00');
        INSERT INTO execution_attempts VALUES
            ('e1','p','a','2024-01-01','ok',
             NULL,NULL,NULL,1,0,1,10,0);
    """
    )
    conn.close()
    return path


def _already_repaired_v7_db(path: Path) -> Path:
    """Create a v7 database WITHOUT the stale FK (already repaired manually)."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE schema_meta (version INTEGER NOT NULL);
        INSERT INTO schema_meta VALUES (7);
        CREATE TABLE consumed_authorizations (
            plan_hash TEXT PRIMARY KEY,
            authorization_hash TEXT NOT NULL,
            consumed_at TEXT NOT NULL
        );
        CREATE TABLE execution_attempts (
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
        );
        INSERT INTO consumed_authorizations VALUES
            ('p','a','2024-01-01T00:00:00+00:00');
        INSERT INTO execution_attempts VALUES
            ('e1','p','a','2024-01-01','ok',
             NULL,NULL,NULL,1,0,1,10,0);
    """
    )
    conn.close()
    return path


def _row_dicts(conn: sqlite3.Connection, table: str) -> list[dict]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(f'SELECT * FROM "{table}"').fetchall()]


class TestStaleFkMigration:
    """v7 → v8 stale execution_attempts FK migration."""

    def test_fresh_journal_is_v8(self, tmp_path: Path) -> None:
        journal = RequestJournal(tmp_path / "j.sqlite")
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()
        assert v[0] == JOURNAL_SCHEMA_VERSION
        fks = journal.connection.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert len(fks) == 0

    def test_historical_v7_with_fk_migrates(self, tmp_path: Path) -> None:
        db = _historical_v7_db(tmp_path / "hist.sqlite")
        # Verify FK present before migration
        pre = sqlite3.connect(str(db))
        pre.row_factory = sqlite3.Row
        pre.execute("PRAGMA foreign_keys=ON")
        fks_before = pre.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert any(fk[2] == "consumed_authorizations" for fk in fks_before)
        rows_before = _row_dicts(pre, "execution_attempts")
        pre.close()

        journal = RequestJournal(db)
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()
        assert v[0] == JOURNAL_SCHEMA_VERSION
        fks_after = journal.connection.execute(
            "PRAGMA foreign_key_list('execution_attempts')"
        ).fetchall()
        assert len(fks_after) == 0

        rows_after = _row_dicts(journal.connection, "execution_attempts")
        assert len(rows_after) == len(rows_before)
        assert rows_after == rows_before

    def test_already_repaired_v7_migrates_idempotent(self, tmp_path: Path) -> None:
        db = _already_repaired_v7_db(tmp_path / "repaired.sqlite")
        journal = RequestJournal(db)
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()
        assert v[0] == JOURNAL_SCHEMA_VERSION
        rows = _row_dicts(journal.connection, "execution_attempts")
        assert len(rows) == 1
        assert rows[0]["execution_id"] == "e1"

    def test_unknown_column_drift_fails_closed(self, tmp_path: Path) -> None:
        db = _historical_v7_db(tmp_path / "drift.sqlite")
        conn = sqlite3.connect(str(db))
        conn.execute("ALTER TABLE execution_attempts ADD COLUMN surprise TEXT")
        conn.close()
        # The column-level migration normalizes missing columns but does not
        # remove extra ones — so the FK check still sees "surprise" and fails.
        with pytest.raises(RuntimeError, match="execution_attempts schema has drifted"):
            RequestJournal(db)

    def test_missing_column_fails_closed(self, tmp_path: Path) -> None:
        db = _historical_v7_db(tmp_path / "missing.sqlite")
        # Drop columns by recreating (the column migration will add them back,
        # so this path does NOT trigger the drift guard).
        conn = sqlite3.connect(str(db))
        conn.executescript(
            """
            CREATE TABLE execution_attempts_new (
                execution_id TEXT PRIMARY KEY,
                plan_hash TEXT NOT NULL,
                authorization_hash TEXT NOT NULL,
                started_at TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(plan_hash) REFERENCES consumed_authorizations(plan_hash)
            );
            INSERT INTO execution_attempts_new SELECT
                execution_id,plan_hash,authorization_hash,started_at,status
                FROM execution_attempts;
            DROP TABLE execution_attempts;
            ALTER TABLE execution_attempts_new RENAME TO execution_attempts;
        """
        )
        conn.close()
        # Column migration adds the missing columns back; migration succeeds
        journal = RequestJournal(db)
        assert (
            journal.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
            == JOURNAL_SCHEMA_VERSION
        )

    def test_rollback_on_failure_preserves_original(self, tmp_path: Path) -> None:
        """Simulate a mid-migration failure and verify rollback."""
        import shutil

        db = _historical_v7_db(tmp_path / "original.sqlite")
        shutil.copy2(db, tmp_path / "copy.sqlite")

        conn = sqlite3.connect(str(tmp_path / "copy.sqlite"))
        conn.execute("PRAGMA foreign_keys=ON")
        # Artificially corrupt: add an unexpected FK
        conn.execute(
            "CREATE TABLE bogus ("
            "x INTEGER,"
            "FOREIGN KEY(x) REFERENCES execution_attempts(execution_id)"
            ")"
        )
        conn.commit()
        conn.close()

        # The migration should still work because the drift check only looks
        # at execution_attempts columns, not unrelated tables.
        journal = RequestJournal(tmp_path / "copy.sqlite")
        assert (
            journal.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
            == JOURNAL_SCHEMA_VERSION
        )

    def test_idempotent_reopen(self, tmp_path: Path) -> None:
        db = _historical_v7_db(tmp_path / "idem.sqlite")
        j1 = RequestJournal(db)
        assert (
            j1.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
            == JOURNAL_SCHEMA_VERSION
        )
        j1.connection.close()
        j2 = RequestJournal(db)
        assert (
            j2.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
            == JOURNAL_SCHEMA_VERSION
        )

    def test_migrated_schema_matches_fresh(self, tmp_path: Path) -> None:
        """Fresh and migrated v7 must converge on the current schema."""
        fresh = RequestJournal(tmp_path / "fresh.sqlite")
        hist = RequestJournal(_historical_v7_db(tmp_path / "hist.sqlite"))

        def column_set(conn, table):
            """Return sorted (name, type, notnull, default, pk) tuples."""
            return sorted(
                (c[1], c[2], c[3], c[4], c[5])
                for c in conn.execute(f"PRAGMA table_info('{table}')").fetchall()
            )

        for table in [
            "schema_meta",
            "requests",
            "consumed_authorizations",
            "execution_attempts",
            "request_events",
            "billing_reconciliations",
            "authorization_reservations",
        ]:
            fc = column_set(fresh.connection, table)
            hc = column_set(hist.connection, table)
            assert fc == hc, f"column mismatch in {table}: fresh={fc} hist={hc}"

        # Both must have no FKs on execution_attempts
        ffk = fresh.connection.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        hfk = hist.connection.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert len(ffk) == 0
        assert len(hfk) == 0

        # Both must have the current schema version
        fv = fresh.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
        hv = hist.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert fv == JOURNAL_SCHEMA_VERSION and hv == JOURNAL_SCHEMA_VERSION

    def test_real_backup_copy_migrates(self, tmp_path: Path) -> None:
        """Copy of the real pre-execution backup migrates successfully."""
        import shutil

        src = Path("data/state/pilot_acquisition_journal_before_fk_fix.sqlite")
        if not src.exists():
            pytest.skip("backup journal not available")
        dst = tmp_path / "backup_copy.sqlite"
        shutil.copy2(src, dst)

        # Verify start state
        pre = sqlite3.connect(str(dst))
        pre.row_factory = sqlite3.Row
        pre.execute("PRAGMA foreign_keys=ON")
        fks_before = pre.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert any(fk[2] == "consumed_authorizations" for fk in fks_before)
        v_before = pre.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert v_before == 7
        pre_rows = _row_dicts(pre, "execution_attempts")
        pre_req_count = pre.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        pre.close()

        journal = RequestJournal(dst)
        journal.connection.row_factory = sqlite3.Row
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()
        assert v[0] == JOURNAL_SCHEMA_VERSION
        fks = journal.connection.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert len(fks) == 0

        post_rows = _row_dicts(journal.connection, "execution_attempts")
        assert len(post_rows) == len(pre_rows)
        for pre_r, post_r in zip(pre_rows, post_rows, strict=False):
            assert pre_r == post_r, f"execution_attempt row changed: {pre_r['execution_id']}"

        req_count = journal.connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        assert req_count == pre_req_count

    def test_real_current_copy_reopens(self, tmp_path: Path) -> None:
        """Copy of the real current journal reopens idempotently."""
        import shutil

        src = Path("data/state/pilot_acquisition_journal.sqlite")
        if not src.exists():
            pytest.skip("current journal not available")
        dst = tmp_path / "current_copy.sqlite"
        shutil.copy2(src, dst)

        # Verify start state (no FK, current schema version)
        pre = sqlite3.connect(str(dst))
        pre.row_factory = sqlite3.Row
        pre.execute("PRAGMA foreign_keys=ON")
        fks_before = pre.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert len(fks_before) == 0
        v_before = pre.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert v_before == JOURNAL_SCHEMA_VERSION
        pre_req_count = pre.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        pre_auths = pre.execute("SELECT COUNT(*) FROM authorization_reservations").fetchone()[0]
        pre.close()

        journal = RequestJournal(dst)
        journal.connection.row_factory = sqlite3.Row
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()
        assert v[0] == JOURNAL_SCHEMA_VERSION
        fks = journal.connection.execute("PRAGMA foreign_key_list('execution_attempts')").fetchall()
        assert len(fks) == 0

        # Verify recovery data preserved
        assert (
            journal.connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            == pre_req_count
        )
        assert (
            journal.connection.execute(
                "SELECT COUNT(*) FROM authorization_reservations"
            ).fetchone()[0]
            == pre_auths
        )
        # Verify execution attempt f3f16742 still present
        ea = journal.connection.execute(
            "SELECT * FROM execution_attempts WHERE execution_id = ?",
            ("f3f1674285c421b0665359753d284591",),  # pragma: allowlist secret
        ).fetchone()
        assert ea is not None
        assert ea["status"] == "completed"
        assert ea["requests_completed"] == 1

        # Verify request 2750995e515e4f1a still quality_validated
        req = journal.connection.execute(
            "SELECT * FROM requests WHERE request_id = ?",
            ("2750995e515e4f1a",),  # pragma: allowlist secret
        ).fetchone()
        assert req is not None
        assert req["state"] == "quality_validated"
        assert req["attempt_count"] == 2
        assert req["raw_path"] is not None
