"""Tests for successful-request billing settlement artifact and application."""

from __future__ import annotations

import contextlib
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
import pytest

from neuralmarket.data.acquisition.billing_reconciliation import (
    SettlementError,
    SuccessfulSettlementArtifact,
    _settlement_canonical,
    apply_successful_settlement,
    build_successful_settlement,
    load_successful_settlement,
)
from neuralmarket.data.acquisition.journal import (
    JournalEntry,
    RequestJournal,
)
from neuralmarket.data.raw.integrity import sha256_of_file

pytestmark = pytest.mark.unit

_EXEC = "f3f1674285c421b0665359753d284591"  # pragma: allowlist secret
_REQ = "2750995e515e4f1a"  # pragma: allowlist secret
_REQ_HASH = (  # pragma: allowlist secret
    "b8b0a410ace7a8a5d710b8bc04e37560ab7b08ceb9aa316a4a3334b6b0980d7a"  # pragma: allowlist secret
)
_PLAN = (  # pragma: allowlist secret
    "ab8560a02feb250c859afd04a3a64fe88a4be1aaa8555d8e1314ec188017233f"  # pragma: allowlist secret
)
_AUTH = (  # pragma: allowlist secret
    "80cf80a881f9e6bcdbfd1e0a81d0b6108a85ec9909736da40722691fb3f3b3e8"  # pragma: allowlist secret
)


def _make_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create dummy raw, normalized and quality files."""
    raw = tmp_path / "test.dbn"
    raw.write_bytes(b"raw content")
    norm = tmp_path / "test.parquet"
    norm.write_bytes(b"normalized content")
    qr = tmp_path / "quality.json"
    qr.write_text(
        json.dumps(
            {"request_id": _REQ, "status": "passed", "validated_at": "2026-07-26T21:09:19+00:00"}
        ),
        encoding="utf-8",
    )
    return raw, norm, qr


def _make_journal(tmp_path: Path, raw: Path, norm: Path) -> Path:
    """Create a v9 journal with a quality_validated completed request."""
    jp = tmp_path / "journal.sqlite"
    journal = RequestJournal(jp)
    now = datetime.now(UTC).isoformat()

    # Use journal API for auth reservation/consumption
    assert journal.reserve_authorization(
        authorization_hash=_AUTH,
        plan_hash=_PLAN,
        execution_id=_EXEC,
        reserved_at=now,
    )
    assert journal.consume_reserved_authorization(
        authorization_hash=_AUTH,
        execution_id=_EXEC,
        consumed_at=now,
    )

    journal.upsert(
        JournalEntry(
            request_id=_REQ,
            request_hash=_REQ_HASH,
            state="quality_validated",
            attempt_count=2,
            estimated_cost_usd="0.000112652779",
            actual_billed_cost_usd=None,
            raw_path=str(raw),
            raw_checksum=sha256_of_file(raw),
            raw_byte_count=raw.stat().st_size,
            raw_record_count=21,
            provider_response_id=None,
            request_started_at=now,
            request_completed_at=now,
            normalized_path=str(norm),
            normalized_checksum=sha256_of_file(norm),
            failure_category=None,
            failure_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    # Set execution attempt completed
    journal.connection.execute(
        "UPDATE execution_attempts SET status='completed', requests_completed=1, "
        "paid_request_calls=1, downloaded_records=21 WHERE execution_id=?",
        (_EXEC,),
    )
    journal.connection.commit()
    journal.connection.close()
    return jp


# ── Artifact model tests ──────────────────────────────────────────


class TestArtifactModel:
    def test_billed_exact_artifact(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw),
            raw_artifact_sha256=sha256_of_file(raw),
            normalized_artifact_path=str(norm),
            normalized_artifact_sha256=sha256_of_file(norm),
            quality_report_path=str(qr),
            quality_report_sha256=sha256_of_file(qr),
            evidence_classification="BILLED_EXACT",
            billed_amount_usd="0.05",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        assert a.manifest_version == "successful-request-billing-settlement-v1"
        assert a.evidence_classification == "BILLED_EXACT"
        assert a.billed_amount_usd == "0.05"
        assert a.currency == "USD"
        assert len(a.settlement_hash) == 64

    def test_not_billed_exact_artifact(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw),
            raw_artifact_sha256=sha256_of_file(raw),
            normalized_artifact_path=str(norm),
            normalized_artifact_sha256=sha256_of_file(norm),
            quality_report_path=str(qr),
            quality_report_sha256=sha256_of_file(qr),
            evidence_classification="NOT_BILLED_EXACT",
            billed_amount_usd="0",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        assert a.billed_amount_usd == "0"

    def test_canonical_stable(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        kwargs = {
            "execution_id": _EXEC,
            "request_id": _REQ,
            "request_hash": _REQ_HASH,
            "plan_hash": _PLAN,
            "authorization_hash": _AUTH,
            "raw_artifact_path": str(raw),
            "raw_artifact_sha256": sha256_of_file(raw),
            "normalized_artifact_path": str(norm),
            "normalized_artifact_sha256": sha256_of_file(norm),
            "quality_report_path": str(qr),
            "quality_report_sha256": sha256_of_file(qr),
            "evidence_classification": "BILLED_EXACT",
            "billed_amount_usd": "0.05",
            "provider_observed_at": "2026-07-27T00:00:00+00:00",
            "reviewed_at": "2026-07-27T00:00:00+00:00",
            "provider_evidence_description": "test",
            "provider_evidence_reference": "test-ref",
        }
        a1 = build_successful_settlement(**kwargs)
        a2 = build_successful_settlement(**kwargs)
        assert a1.settlement_hash == a2.settlement_hash

    def test_tampered_amount_invalidates(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw),
            raw_artifact_sha256=sha256_of_file(raw),
            normalized_artifact_path=str(norm),
            normalized_artifact_sha256=sha256_of_file(norm),
            quality_report_path=str(qr),
            quality_report_sha256=sha256_of_file(qr),
            evidence_classification="BILLED_EXACT",
            billed_amount_usd="0.05",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        d = json.loads(a.model_dump_json())
        d["billed_amount_usd"] = "999"
        bad_hash = _settlement_canonical(d)
        assert bad_hash != a.settlement_hash

    def test_billed_exact_zero_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError, match="BILLED_EXACT requires billed_amount_usd > 0"):
            build_successful_settlement(
                execution_id=_EXEC,
                request_id=_REQ,
                request_hash=_REQ_HASH,
                plan_hash=_PLAN,
                authorization_hash=_AUTH,
                raw_artifact_path=str(raw),
                raw_artifact_sha256=sha256_of_file(raw),
                normalized_artifact_path=str(norm),
                normalized_artifact_sha256=sha256_of_file(norm),
                quality_report_path=str(qr),
                quality_report_sha256=sha256_of_file(qr),
                evidence_classification="BILLED_EXACT",
                billed_amount_usd="0",
                provider_observed_at="2026-07-27T00:00:00+00:00",
                provider_evidence_description="test",
                provider_evidence_reference="test-ref",
            )

    def test_not_billed_exact_nonzero_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError, match="NOT_BILLED_EXACT requires billed_amount_usd = 0"):
            build_successful_settlement(
                execution_id=_EXEC,
                request_id=_REQ,
                request_hash=_REQ_HASH,
                plan_hash=_PLAN,
                authorization_hash=_AUTH,
                raw_artifact_path=str(raw),
                raw_artifact_sha256=sha256_of_file(raw),
                normalized_artifact_path=str(norm),
                normalized_artifact_sha256=sha256_of_file(norm),
                quality_report_path=str(qr),
                quality_report_sha256=sha256_of_file(qr),
                evidence_classification="NOT_BILLED_EXACT",
                billed_amount_usd="0.01",
                provider_observed_at="2026-07-27T00:00:00+00:00",
                provider_evidence_description="test",
                provider_evidence_reference="test-ref",
            )

    def test_float_amount_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SuccessfulSettlementArtifact.model_validate(
                {
                    "manifest_version": "successful-request-billing-settlement-v1",
                    "execution_id": _EXEC,
                    "request_id": _REQ,
                    "request_hash": _REQ_HASH,
                    "plan_hash": _PLAN,
                    "authorization_hash": _AUTH,
                    "raw_artifact_path": str(raw),
                    "raw_artifact_sha256": sha256_of_file(raw),
                    "normalized_artifact_path": str(norm),
                    "normalized_artifact_sha256": sha256_of_file(norm),
                    "quality_report_path": str(qr),
                    "quality_report_sha256": sha256_of_file(qr),
                    "evidence_classification": "BILLED_EXACT",
                    "billed_amount_usd": 0.05,
                    "currency": "USD",
                    "provider_observed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_by": "neuralmarket_local_operator",
                    "review_method": "manual_databento_provider_review",
                    "provider_evidence_description": "test",
                    "provider_evidence_reference": "test-ref",
                    "settlement_hash": "a" * 64,
                }
            )

    def test_nan_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError, match="finite"):
            SuccessfulSettlementArtifact.model_validate(
                {
                    "manifest_version": "successful-request-billing-settlement-v1",
                    "execution_id": _EXEC,
                    "request_id": _REQ,
                    "request_hash": _REQ_HASH,
                    "plan_hash": _PLAN,
                    "authorization_hash": _AUTH,
                    "raw_artifact_path": str(raw),
                    "raw_artifact_sha256": sha256_of_file(raw),
                    "normalized_artifact_path": str(norm),
                    "normalized_artifact_sha256": sha256_of_file(norm),
                    "quality_report_path": str(qr),
                    "quality_report_sha256": sha256_of_file(qr),
                    "evidence_classification": "BILLED_EXACT",
                    "billed_amount_usd": "NaN",
                    "currency": "USD",
                    "provider_observed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_by": "neuralmarket_local_operator",
                    "review_method": "manual_databento_provider_review",
                    "provider_evidence_description": "test",
                    "provider_evidence_reference": "test-ref",
                    "settlement_hash": "a" * 64,
                }
            )

    def test_infinity_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError, match="finite"):
            SuccessfulSettlementArtifact.model_validate(
                {
                    "manifest_version": "successful-request-billing-settlement-v1",
                    "execution_id": _EXEC,
                    "request_id": _REQ,
                    "request_hash": _REQ_HASH,
                    "plan_hash": _PLAN,
                    "authorization_hash": _AUTH,
                    "raw_artifact_path": str(raw),
                    "raw_artifact_sha256": sha256_of_file(raw),
                    "normalized_artifact_path": str(norm),
                    "normalized_artifact_sha256": sha256_of_file(norm),
                    "quality_report_path": str(qr),
                    "quality_report_sha256": sha256_of_file(qr),
                    "evidence_classification": "BILLED_EXACT",
                    "billed_amount_usd": "Infinity",
                    "currency": "USD",
                    "provider_observed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_by": "neuralmarket_local_operator",
                    "review_method": "manual_databento_provider_review",
                    "provider_evidence_description": "test",
                    "provider_evidence_reference": "test-ref",
                    "settlement_hash": "a" * 64,
                }
            )

    def test_negative_amount_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError, match="non-negative"):
            build_successful_settlement(
                execution_id=_EXEC,
                request_id=_REQ,
                request_hash=_REQ_HASH,
                plan_hash=_PLAN,
                authorization_hash=_AUTH,
                raw_artifact_path=str(raw),
                raw_artifact_sha256=sha256_of_file(raw),
                normalized_artifact_path=str(norm),
                normalized_artifact_sha256=sha256_of_file(norm),
                quality_report_path=str(qr),
                quality_report_sha256=sha256_of_file(qr),
                evidence_classification="BILLED_EXACT",
                billed_amount_usd="-1",
                provider_observed_at="2026-07-27T00:00:00+00:00",
                provider_evidence_description="test",
                provider_evidence_reference="test-ref",
            )

    def test_invalid_classification_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError):
            SuccessfulSettlementArtifact.model_validate(
                {
                    "manifest_version": "successful-request-billing-settlement-v1",
                    "execution_id": _EXEC,
                    "request_id": _REQ,
                    "request_hash": _REQ_HASH,
                    "plan_hash": _PLAN,
                    "authorization_hash": _AUTH,
                    "raw_artifact_path": str(raw),
                    "raw_artifact_sha256": sha256_of_file(raw),
                    "normalized_artifact_path": str(norm),
                    "normalized_artifact_sha256": sha256_of_file(norm),
                    "quality_report_path": str(qr),
                    "quality_report_sha256": sha256_of_file(qr),
                    "evidence_classification": "BILLED_AGGREGATE_ONLY",
                    "billed_amount_usd": "0.05",
                    "currency": "USD",
                    "provider_observed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_by": "neuralmarket_local_operator",
                    "review_method": "manual_databento_provider_review",
                    "provider_evidence_description": "test",
                    "provider_evidence_reference": "test-ref",
                    "settlement_hash": "a" * 64,
                }
            )

    def test_invalid_evidence_unknown_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError):
            SuccessfulSettlementArtifact.model_validate(
                {
                    "manifest_version": "successful-request-billing-settlement-v1",
                    "execution_id": _EXEC,
                    "request_id": _REQ,
                    "request_hash": _REQ_HASH,
                    "plan_hash": _PLAN,
                    "authorization_hash": _AUTH,
                    "raw_artifact_path": str(raw),
                    "raw_artifact_sha256": sha256_of_file(raw),
                    "normalized_artifact_path": str(norm),
                    "normalized_artifact_sha256": sha256_of_file(norm),
                    "quality_report_path": str(qr),
                    "quality_report_sha256": sha256_of_file(qr),
                    "evidence_classification": "UNKNOWN",
                    "billed_amount_usd": "0.05",
                    "currency": "USD",
                    "provider_observed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_by": "neuralmarket_local_operator",
                    "review_method": "manual_databento_provider_review",
                    "provider_evidence_description": "test",
                    "provider_evidence_reference": "test-ref",
                    "settlement_hash": "a" * 64,
                }
            )


# ── JSON Schema tests ─────────────────────────────────────────────


class TestJsonSchema:
    def test_valid_artifact_passes_schema(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw),
            raw_artifact_sha256=sha256_of_file(raw),
            normalized_artifact_path=str(norm),
            normalized_artifact_sha256=sha256_of_file(norm),
            quality_report_path=str(qr),
            quality_report_sha256=sha256_of_file(qr),
            evidence_classification="BILLED_EXACT",
            billed_amount_usd="0.05",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        schema = json.loads(
            Path("data_contracts/successful_request_billing_settlement.schema.json").read_text()
        )
        jsonschema.validate(json.loads(a.model_dump_json()), schema)

    def test_missing_required_fails_schema(self, tmp_path: Path) -> None:
        schema = json.loads(
            Path("data_contracts/successful_request_billing_settlement.schema.json").read_text()
        )
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                {"manifest_version": "successful-request-billing-settlement-v1"}, schema
            )

    def test_extra_field_fails_schema(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw),
            raw_artifact_sha256=sha256_of_file(raw),
            normalized_artifact_path=str(norm),
            normalized_artifact_sha256=sha256_of_file(norm),
            quality_report_path=str(qr),
            quality_report_sha256=sha256_of_file(qr),
            evidence_classification="BILLED_EXACT",
            billed_amount_usd="0.05",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        d = json.loads(a.model_dump_json())
        d["extra_field"] = "no"
        schema = json.loads(
            Path("data_contracts/successful_request_billing_settlement.schema.json").read_text()
        )
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(d, schema)

    def test_load_validates_schema(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw),
            raw_artifact_sha256=sha256_of_file(raw),
            normalized_artifact_path=str(norm),
            normalized_artifact_sha256=sha256_of_file(norm),
            quality_report_path=str(qr),
            quality_report_sha256=sha256_of_file(qr),
            evidence_classification="BILLED_EXACT",
            billed_amount_usd="0.05",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        p = tmp_path / "settle.json"
        p.write_text(a.model_dump_json(), encoding="utf-8")
        loaded = load_successful_settlement(p)
        assert loaded.settlement_hash == a.settlement_hash


# ── Settlement function tests ─────────────────────────────────────


def _artifact(
    tmp_path: Path, raw: Path, norm: Path, qr: Path, **kw
) -> SuccessfulSettlementArtifact:
    defaults: dict = {
        "execution_id": _EXEC,
        "request_id": _REQ,
        "request_hash": _REQ_HASH,
        "plan_hash": _PLAN,
        "authorization_hash": _AUTH,
        "raw_artifact_path": str(raw),
        "raw_artifact_sha256": sha256_of_file(raw),
        "normalized_artifact_path": str(norm),
        "normalized_artifact_sha256": sha256_of_file(norm),
        "quality_report_path": str(qr),
        "quality_report_sha256": sha256_of_file(qr),
        "evidence_classification": "BILLED_EXACT",
        "billed_amount_usd": "0.05",
        "provider_observed_at": "2026-07-27T00:00:00+00:00",
        "provider_evidence_description": "test",
        "provider_evidence_reference": "test-ref",
    }
    defaults.update(kw)
    return build_successful_settlement(**defaults)


class TestSettlementApply:
    def test_billed_exact_succeeds(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        r = apply_successful_settlement(journal=journal, artifact=a)
        assert r.status == "ok"
        assert r.billed_amount_usd == "0.05"
        assert r.cost_status == "confirmed_billed"
        assert r.request_state == "quality_validated"

    def test_not_billed_exact_succeeds(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(
            tmp_path,
            raw,
            norm,
            qr,
            evidence_classification="NOT_BILLED_EXACT",
            billed_amount_usd="0",
        )
        journal = RequestJournal(jp)
        r = apply_successful_settlement(journal=journal, artifact=a)
        assert r.cost_status == "confirmed_not_billed"

    def test_state_preserved(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a)
        conn = sqlite3.connect(str(jp))
        conn.row_factory = sqlite3.Row
        req = conn.execute("SELECT * FROM requests WHERE request_id = ?", (_REQ,)).fetchone()
        assert req["state"] == "quality_validated"
        assert req["attempt_count"] == 2
        assert req["raw_path"] is not None
        assert req["normalized_path"] is not None
        assert req["actual_billed_cost_usd"] == "0.05"
        assert req["actual_provider_cost_status"] == "confirmed_billed"
        conn.close()

    def test_execution_preserved(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a)
        conn = sqlite3.connect(str(jp))
        conn.row_factory = sqlite3.Row
        ea = conn.execute(
            "SELECT * FROM execution_attempts WHERE execution_id = ?", (_EXEC,)
        ).fetchone()
        assert ea["status"] == "completed"
        assert ea["requests_completed"] == 1
        conn.close()

    def test_event_appended(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a)
        conn = sqlite3.connect(str(jp))
        conn.row_factory = sqlite3.Row
        events = conn.execute(
            "SELECT * FROM request_events "
            "WHERE event_type = 'successful_request_billing_settlement_recorded'"
        ).fetchall()
        assert len(events) == 1
        detail = json.loads(str(events[0]["detail_json"]))
        assert detail["settlement_hash"] == a.settlement_hash
        assert detail["billed_amount_usd"] == "0.05"
        assert detail["evidence_classification"] == "BILLED_EXACT"
        conn.close()

    def test_idempotent_replay(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a)
        r2 = apply_successful_settlement(journal=journal, artifact=a)
        assert r2.idempotent_replay is True
        # only one event
        conn = sqlite3.connect(str(jp))
        events = conn.execute(
            "SELECT COUNT(*) FROM request_events "
            "WHERE event_type = 'successful_request_billing_settlement_recorded'"
        ).fetchone()[0]
        assert events == 1
        conn.close()

    def test_conflicting_amount_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a1 = _artifact(tmp_path, raw, norm, qr, billed_amount_usd="0.05")
        a2 = _artifact(tmp_path, raw, norm, qr, billed_amount_usd="0.06")
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a1)
        with pytest.raises(SettlementError, match="conflicting"):
            apply_successful_settlement(journal=journal, artifact=a2)

    def test_conflicting_hash_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a1 = _artifact(
            tmp_path, raw, norm, qr, billed_amount_usd="0.05", provider_evidence_description="first"
        )
        a2 = _artifact(
            tmp_path,
            raw,
            norm,
            qr,
            billed_amount_usd="0.05",
            provider_evidence_description="second",
        )
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a1)
        with pytest.raises(SettlementError, match="conflicting"):
            apply_successful_settlement(journal=journal, artifact=a2)

    def test_wrong_request_hash_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, request_hash="b" * 64)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="request hash mismatch"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_wrong_execution_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, execution_id="wrong")
        journal = RequestJournal(jp)
        with pytest.raises((SettlementError, Exception)):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_wrong_plan_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, plan_hash="c" * 64)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="execution plan hash mismatch"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_missing_raw_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, raw_artifact_path="/nonexistent/path.dbn")
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_wrong_authorization_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, authorization_hash="d" * 64)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="execution authorization hash mismatch"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_raw_checksum_mismatch_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, raw_artifact_sha256="e" * 64)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="raw checksum mismatch"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_missing_quality_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(
            tmp_path,
            raw,
            norm,
            qr,
            quality_report_path="/nonexistent/qr.json",
            quality_report_sha256=sha256_of_file(qr),
        )
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="quality report file not found"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_failed_quality_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        # Write failed quality BEFORE journal creation so checksums match
        qr.write_text(json.dumps({"request_id": _REQ, "status": "failed"}))
        jp = _make_journal(tmp_path, raw, norm)
        # Update journal with the new quality checksum
        conn = sqlite3.connect(str(jp))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        a = _artifact(tmp_path, raw, norm, qr, quality_report_sha256=sha256_of_file(qr))
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="quality report has not passed"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_not_quality_validated_fails(self, tmp_path: Path) -> None:
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        conn = sqlite3.connect(str(jp))
        conn.execute(
            "UPDATE requests SET state = 'uncertain_billing' WHERE request_id = ?", (_REQ,)
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="must be quality_validated"):
            apply_successful_settlement(journal=journal, artifact=a)


# ── Migration tests ───────────────────────────────────────────────


class TestSettlementMigration:
    def test_fresh_journal_is_v9(self, tmp_path: Path) -> None:
        jp = tmp_path / "j.sqlite"
        journal = RequestJournal(jp)
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert v == 9
        cols = {c[1] for c in journal.connection.execute("PRAGMA table_info(requests)")}
        assert "actual_provider_cost_status" in cols
        journal.connection.close()

    def test_v8_adds_column(self, tmp_path: Path) -> None:
        # Create a v8-shaped database manually
        jp = tmp_path / "v8.sqlite"
        conn = sqlite3.connect(str(jp))
        conn.executescript("""
            CREATE TABLE schema_meta (version INTEGER NOT NULL);
            INSERT INTO schema_meta VALUES (8);
            CREATE TABLE requests (request_id TEXT PRIMARY KEY);
            INSERT INTO requests VALUES ('test');
        """)
        conn.close()
        journal = RequestJournal(jp)
        v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert v == 9
        cols = {c[1] for c in journal.connection.execute("PRAGMA table_info(requests)")}
        assert "actual_provider_cost_status" in cols
        journal.connection.close()

    def test_reopen_idempotent(self, tmp_path: Path) -> None:
        jp = tmp_path / "idem.sqlite"
        RequestJournal(jp).connection.close()
        RequestJournal(jp).connection.close()
        conn = sqlite3.connect(str(jp))
        v = conn.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert v == 9
        conn.close()


# ── Temporary production-copy tests ───────────────────────────────


class TestProdCopyMigration:
    def test_prod_copy_migrates(self, tmp_path: Path) -> None:
        src = Path("data/state/pilot_acquisition_journal.sqlite")
        if not src.exists():
            pytest.skip("production journal not available")
        dst = tmp_path / "prod_copy.sqlite"
        shutil.copy2(src, dst)
        pre = sqlite3.connect(str(dst))
        pre_v = pre.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert pre_v == 8
        pre.close()

        journal = RequestJournal(dst)
        journal.connection.row_factory = sqlite3.Row
        post_v = journal.connection.execute("SELECT version FROM schema_meta").fetchone()[0]
        assert post_v == 9
        req = journal.connection.execute(
            "SELECT state, actual_billed_cost_usd, actual_provider_cost_status "
            "FROM requests WHERE request_id=?",
            (_REQ,),
        ).fetchone()
        assert req["state"] == "quality_validated"
        assert req["actual_billed_cost_usd"] is None
        journal.connection.close()

    def test_prod_copy_settlement_validates(self, tmp_path: Path) -> None:
        src = Path("data/state/pilot_acquisition_journal.sqlite")
        if not src.exists():
            pytest.skip("production journal not available")
        dst = tmp_path / "prod_copy.sqlite"
        shutil.copy2(src, dst)

        journal = RequestJournal(dst)
        # Read actual artifact paths from journal
        conn = journal.connection
        conn.row_factory = sqlite3.Row
        req = conn.execute("SELECT * FROM requests WHERE request_id = ?", (_REQ,)).fetchone()
        raw_path = Path(str(req["raw_path"]))
        norm_path = Path(str(req["normalized_path"]))
        qr_path = Path("reports/data/quality/2750995e515e4f1a.json")
        if not raw_path.exists() or not norm_path.exists() or not qr_path.exists():
            journal.connection.close()
            pytest.skip("production artifacts not at expected paths")

        # Use synthetic amount, not portal aggregate
        a = build_successful_settlement(
            execution_id=_EXEC,
            request_id=_REQ,
            request_hash=_REQ_HASH,
            plan_hash=_PLAN,
            authorization_hash=_AUTH,
            raw_artifact_path=str(raw_path),
            raw_artifact_sha256=sha256_of_file(raw_path),
            normalized_artifact_path=str(norm_path),
            normalized_artifact_sha256=sha256_of_file(norm_path),
            quality_report_path=str(qr_path),
            quality_report_sha256=sha256_of_file(qr_path),
            evidence_classification="BILLED_EXACT",
            billed_amount_usd="0.05",
            provider_observed_at="2026-07-27T00:00:00+00:00",
            provider_evidence_description="test",
            provider_evidence_reference="test-ref",
        )
        r = apply_successful_settlement(journal=journal, artifact=a)
        assert r.status == "ok"
        assert r.request_state == "quality_validated"
        journal.connection.close()


# ── Additional required tests ──────────────────────────────────────


class TestMonetaryContract:
    def test_nonfinite_rejected(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        for bad in ["NaN", "Infinity"]:
            with pytest.raises(ValueError, match="finite"):
                build_successful_settlement(
                    execution_id=_EXEC,
                    request_id=_REQ,
                    request_hash=_REQ_HASH,
                    plan_hash=_PLAN,
                    authorization_hash=_AUTH,
                    raw_artifact_path=str(raw),
                    raw_artifact_sha256=sha256_of_file(raw),
                    normalized_artifact_path=str(norm),
                    normalized_artifact_sha256=sha256_of_file(norm),
                    quality_report_path=str(qr),
                    quality_report_sha256=sha256_of_file(qr),
                    evidence_classification="BILLED_EXACT",
                    billed_amount_usd=bad,
                    provider_observed_at="2026-07-27T00:00:00+00:00",
                    provider_evidence_description="test",
                    provider_evidence_reference="test-ref",
                )

    def test_empty_amount_rejected(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        for bad in ["", "  "]:
            with pytest.raises(ValueError):
                build_successful_settlement(
                    execution_id=_EXEC,
                    request_id=_REQ,
                    request_hash=_REQ_HASH,
                    plan_hash=_PLAN,
                    authorization_hash=_AUTH,
                    raw_artifact_path=str(raw),
                    raw_artifact_sha256=sha256_of_file(raw),
                    normalized_artifact_path=str(norm),
                    normalized_artifact_sha256=sha256_of_file(norm),
                    quality_report_path=str(qr),
                    quality_report_sha256=sha256_of_file(qr),
                    evidence_classification="BILLED_EXACT",
                    billed_amount_usd=bad,
                    provider_observed_at="2026-07-27T00:00:00+00:00",
                    provider_evidence_description="test",
                    provider_evidence_reference="test-ref",
                )

    def test_unsupported_currency_rejected(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        with pytest.raises(ValueError):
            SuccessfulSettlementArtifact.model_validate(
                {
                    "manifest_version": "successful-request-billing-settlement-v1",
                    "execution_id": _EXEC,
                    "request_id": _REQ,
                    "request_hash": _REQ_HASH,
                    "plan_hash": _PLAN,
                    "authorization_hash": _AUTH,
                    "raw_artifact_path": str(raw),
                    "raw_artifact_sha256": sha256_of_file(raw),
                    "normalized_artifact_path": str(norm),
                    "normalized_artifact_sha256": sha256_of_file(norm),
                    "quality_report_path": str(qr),
                    "quality_report_sha256": sha256_of_file(qr),
                    "evidence_classification": "BILLED_EXACT",
                    "billed_amount_usd": "0.05",
                    "currency": "EUR",
                    "provider_observed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_at": "2026-07-27T00:00:00+00:00",
                    "reviewed_by": "neuralmarket_local_operator",
                    "review_method": "manual_databento_provider_review",
                    "provider_evidence_description": "test",
                    "provider_evidence_reference": "test-ref",
                    "settlement_hash": "a" * 64,
                }
            )


class TestAuthEdge:
    def test_unconsumed_auth_fails(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        conn = sqlite3.connect(str(jp))
        conn.execute(
            "UPDATE authorization_reservations SET state='reserved',"
            "consumed_at=NULL WHERE authorization_hash=?",
            (_AUTH,),
        )
        conn.execute("DELETE FROM consumed_authorizations WHERE plan_hash=?", (_PLAN,))
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="authorization is not consumed"):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_auth_row_preserved(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        apply_successful_settlement(journal=journal, artifact=a)
        conn = sqlite3.connect(str(jp))
        conn.row_factory = sqlite3.Row
        r = conn.execute(
            "SELECT * FROM authorization_reservations WHERE authorization_hash=?", (_AUTH,)
        ).fetchone()
        assert r["state"] == "consumed"
        assert r["consumed_at"] is not None
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM consumed_authorizations WHERE plan_hash=?", (_PLAN,)
            ).fetchone()[0]
            == 1
        )
        conn.close()


class TestNormEdge:
    def test_missing_normalized_fails(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, normalized_artifact_path="/x/norm.parquet")
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError):
            apply_successful_settlement(journal=journal, artifact=a)

    def test_normalized_checksum_mismatch_fails(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr, normalized_artifact_sha256="f" * 64)
        journal = RequestJournal(jp)
        with pytest.raises(SettlementError, match="normalized checksum mismatch"):
            apply_successful_settlement(journal=journal, artifact=a)


class TestRollback:
    def test_transaction_rollback(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        journal = RequestJournal(jp)
        conn = journal.connection
        conn.execute("DROP TABLE request_events")
        conn.commit()
        with pytest.raises(sqlite3.OperationalError):
            apply_successful_settlement(journal=journal, artifact=a)
        conn2 = sqlite3.connect(str(jp))
        conn2.row_factory = sqlite3.Row
        req = conn2.execute("SELECT * FROM requests WHERE request_id=?", (_REQ,)).fetchone()
        assert req["actual_billed_cost_usd"] is None
        assert req["actual_provider_cost_status"] is None
        conn2.close()


class TestCliValidateOnly:
    def test_validate_no_writes(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        ap = tmp_path / "s.json"
        ap.write_text(a.model_dump_json(), encoding="utf-8")
        op = tmp_path / "r.json"
        ph = hashlib.sha256(jp.read_bytes()).hexdigest()
        from neuralmarket.cli.data import pilot_settle_successful_billing

        with contextlib.suppress(Exception):
            pilot_settle_successful_billing(
                settlement=ap,
                journal_path=jp,
                output=op,
                validate_only=True,
                confirm_settlement_hash="",
            )
        assert hashlib.sha256(jp.read_bytes()).hexdigest() == ph
        assert (
            sqlite3.connect(str(jp))
            .execute(
                "SELECT COUNT(*) FROM request_events WHERE event_type='successful_request_billing_settlement_recorded'"
            )
            .fetchone()[0]
            == 0
        )

    def test_validate_only_no_provider(self, tmp_path, monkeypatch):
        """Validate-only never constructs or calls a Databento provider."""
        import databento  # ensure already imported

        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        ap = tmp_path / "s.json"
        ap.write_text(a.model_dump_json(), encoding="utf-8")
        op = tmp_path / "r.json"
        ph = hashlib.sha256(jp.read_bytes()).hexdigest()

        called = []

        def fake_historical(*args, **kwargs):
            called.append(("Historical", args, kwargs))
            raise RuntimeError("provider must not be constructed")

        monkeypatch.setattr(databento, "Historical", fake_historical)
        from neuralmarket.cli.data import pilot_settle_successful_billing

        with contextlib.suppress(Exception):
            pilot_settle_successful_billing(
                settlement=ap,
                journal_path=jp,
                output=op,
                validate_only=True,
                confirm_settlement_hash="",
            )
        assert len(called) == 0, f"provider constructed {len(called)} times"
        assert hashlib.sha256(jp.read_bytes()).hexdigest() == ph
        assert "databento" in sys.modules


class TestCliConfirm:
    def test_missing_confirm_fails(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        ap = tmp_path / "s.json"
        ap.write_text(a.model_dump_json(), encoding="utf-8")
        op = tmp_path / "r.json"
        ph = hashlib.sha256(jp.read_bytes()).hexdigest()
        from neuralmarket.cli.data import pilot_settle_successful_billing

        with contextlib.suppress(Exception):
            pilot_settle_successful_billing(
                settlement=ap,
                journal_path=jp,
                output=op,
                validate_only=False,
                confirm_settlement_hash="",
            )
        assert hashlib.sha256(jp.read_bytes()).hexdigest() == ph

    def test_wrong_confirm_fails(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        ap = tmp_path / "s.json"
        ap.write_text(a.model_dump_json(), encoding="utf-8")
        op = tmp_path / "r.json"
        ph = hashlib.sha256(jp.read_bytes()).hexdigest()
        from neuralmarket.cli.data import pilot_settle_successful_billing

        with contextlib.suppress(Exception):
            pilot_settle_successful_billing(
                settlement=ap,
                journal_path=jp,
                output=op,
                validate_only=False,
                confirm_settlement_hash="b" * 64,
            )
        assert hashlib.sha256(jp.read_bytes()).hexdigest() == ph

    def test_correct_confirm_applies(self, tmp_path):
        raw, norm, qr = _make_files(tmp_path)
        jp = _make_journal(tmp_path, raw, norm)
        a = _artifact(tmp_path, raw, norm, qr)
        ap = tmp_path / "s.json"
        ap.write_text(a.model_dump_json(), encoding="utf-8")
        op = tmp_path / "r.json"
        from neuralmarket.cli.data import pilot_settle_successful_billing

        with contextlib.suppress(Exception):
            pilot_settle_successful_billing(
                settlement=ap,
                journal_path=jp,
                output=op,
                validate_only=False,
                confirm_settlement_hash=a.settlement_hash,
            )
        conn = sqlite3.connect(str(jp))
        conn.row_factory = sqlite3.Row
        req = conn.execute("SELECT * FROM requests WHERE request_id=?", (_REQ,)).fetchone()
        assert req["actual_billed_cost_usd"] == "0.05"
        assert req["state"] == "quality_validated"
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM request_events WHERE event_type='successful_request_billing_settlement_recorded'"
            ).fetchone()[0]
            == 1
        )
        conn.close()
