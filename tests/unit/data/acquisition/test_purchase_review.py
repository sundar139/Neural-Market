"""Offline fail-closed tests for the pilot purchase-review gate.

No test constructs a real Databento client or touches the network; an autouse
guard fails the module if ``databento`` is ever imported.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.purchase_review import (
    AUTHORIZATION_STATEMENT_TEMPLATE,
    ExpectedPurchaseBindings,
    compute_portal_attestation_hash,
    compute_review_hash,
    load_json_artifact,
    review_purchase_package,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)
HEAD = "d3d43d2f7491ec664deee5eb791d9074285e7e51"
PLAN = "5ee6126ca9e27e3d1909c58b4e555526d5894dcd9ea129faf8d6159973aff1fe"
CKPT = "ede035f92b30c3b15d6fa0a9c61991225e216c943e86f059b7c52ed03b435706"
REQMAN = "8e63d7b0de534173ce65ee7992f4e82239f531d16bbb4f67866771ac1f0bc9a8"
SRC = "3d31e373defbe43aa8eb30c453c1e65c1913d3103e336e02b26757fecd710604"
SPLIT = "877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe"
POLICY = "affce36b4e5da07f60c578e3743b320a6c5ce63e559433b473148423fbb4e9b6"
RAW = Decimal("0.460514456032759765625")
CONSERVATIVE = Decimal("0.46298506855869970703125")
DRIFT_CEILING = Decimal("0.6907716840495")
STORED_CONFIG = "b490b3a11d89707d8a9ab6d154eb6c03ee5d312e247a9d936e1caca4d2621426"
CURRENT_CONFIG = "7be6bae3197ee7debe0827c8119c3d5ad186832d3b6f2b9b7215a63f6969fbbb"

EXPECTED = ExpectedPurchaseBindings(
    repository_head=HEAD,
    plan_hash=PLAN,
    completed_checkpoint_sha256=CKPT,
    request_manifest_sha256=REQMAN,
    source_manifest_hash=SRC,
    split_manifest_hash=SPLIT,
    acquisition_policy_hash=POLICY,
    raw_total_usd=RAW,
    conservative_total_usd=CONSERVATIVE,
    maximum_ceiling_usd=DRIFT_CEILING,
)


@pytest.fixture(autouse=True)
def _no_real_databento() -> Any:
    already_imported = "databento" in sys.modules
    yield
    newly_imported = "databento" in sys.modules and not already_imported
    assert not newly_imported, "purchase-review tests must never import databento"


def _valid_authorization(ceiling: str = "0.50") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "pilot-purchase-authorization-v1",
        "template_only": False,
        "authorized": True,
        "consumed": False,
        "repository_head": HEAD,
        "plan_hash": PLAN,
        "completed_checkpoint_sha256": CKPT,
        "request_manifest_sha256": REQMAN,
        "source_manifest_hash": SRC,
        "split_manifest_hash": SPLIT,
        "acquisition_policy_hash": POLICY,
        "configuration_compatibility": {
            "checkpoint_stored_pilot_config_hash": STORED_CONFIG,
            "current_config_sha256": CURRENT_CONFIG,
            "compatible": True,
        },
        "databento_client_version": "0.81.0",
        "raw_total_usd": str(RAW),
        "conservative_total_usd": str(CONSERVATIVE),
        "authorized_ceiling_usd": ceiling,
        "scope": {
            "pilot_month": "2019-01",
            "datasets": ["ARCX.PILLAR", "OPRA.PILLAR"],
            "schemas": ["cbbo-1m", "definition", "ohlcv-1d", "statistics"],
            "symbols": ["SPY", "SPY.OPT"],
            "window_start": "2019-01-02T00:00:00+00:00",
            "window_end": "2019-02-01T00:00:00+00:00",
            "logical_request_count": 25,
        },
        "created_at": (NOW - timedelta(hours=1)).isoformat(),
        "expires_at": (NOW + timedelta(hours=12)).isoformat(),
        "authorized_by": "test-operator",
        "authorization_statement": AUTHORIZATION_STATEMENT_TEMPLATE.format(amount=ceiling),
        "review_hash": None,
    }
    payload["review_hash"] = compute_review_hash(payload)
    return payload


def _valid_attestation() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "pilot-portal-attestation-v1",
        "template_only": False,
        "attested": True,
        "dataset_scope": ["ARCX.PILLAR", "OPRA.PILLAR"],
        "schema_scope": ["cbbo-1m", "definition", "ohlcv-1d", "statistics"],
        "symbol_scope": ["SPY", "SPY.OPT"],
        "window_start": "2019-01-02T00:00:00+00:00",
        "window_end": "2019-02-01T00:00:00+00:00",
        "portal_estimate_usd": "0.47",
        "currency": "USD",
        "observed_at": (NOW - timedelta(minutes=5)).isoformat(),
        "expires_at": (NOW + timedelta(minutes=20)).isoformat(),
        "completed_checkpoint_sha256": CKPT,
        "request_manifest_sha256": REQMAN,
        "operator_confirmation": "reviewed portal estimate for the bound scope",
        "attestation_hash": None,
    }
    payload["attestation_hash"] = compute_portal_attestation_hash(payload)
    return payload


def _review(auth: dict[str, Any] | None, att: dict[str, Any] | None, tmp: Path, **kw: Any):
    assert auth is not None
    return review_purchase_package(
        authorization=auth,
        attestation=att,
        expected=EXPECTED,
        now=kw.pop("now", NOW),
        journal_path=kw.pop("journal_path", tmp / "journal.sqlite"),
        consumption_marker=kw.pop("consumption_marker", tmp / "consumed.local.json"),
    )


def _codes(result: Any) -> set[str]:
    return {rej.code for rej in result.rejections}


def _rehash(auth: dict[str, Any]) -> dict[str, Any]:
    auth = dict(auth)
    auth["review_hash"] = compute_review_hash(auth)
    return auth


def test_missing_authorization_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing_authorization"):
        load_json_artifact(
            tmp_path / "absent.json",
            schema_relative="data_contracts/pilot_purchase_authorization.schema.json",
            kind="authorization",
        )


def test_template_only_rejected(tmp_path: Path) -> None:
    auth = _rehash({**_valid_authorization(), "template_only": True})
    assert "template_only" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_not_authorized_rejected(tmp_path: Path) -> None:
    auth = _rehash({**_valid_authorization(), "authorized": False})
    assert "not_authorized" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_missing_attestation_rejected(tmp_path: Path) -> None:
    assert "missing_attestation" in _codes(_review(_valid_authorization(), None, tmp_path))


def test_not_attested_rejected(tmp_path: Path) -> None:
    att = dict(_valid_attestation())
    att["attested"] = False
    att["attestation_hash"] = compute_portal_attestation_hash(att)
    assert "not_attested" in _codes(_review(_valid_authorization(), att, tmp_path))


def test_ceiling_below_conservative_rejected(tmp_path: Path) -> None:
    auth = _valid_authorization(ceiling="0.46")
    assert "ceiling_below_conservative" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_ceiling_above_drift_limit_rejected(tmp_path: Path) -> None:
    auth = _valid_authorization(ceiling="0.75")
    assert "ceiling_above_drift_limit" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_checkpoint_hash_mismatch_rejected(tmp_path: Path) -> None:
    auth = _rehash({**_valid_authorization(), "completed_checkpoint_sha256": "0" * 64})
    assert "checkpoint_hash_mismatch" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_plan_hash_mismatch_rejected(tmp_path: Path) -> None:
    auth = _rehash({**_valid_authorization(), "plan_hash": "1" * 64})
    assert "plan_hash_mismatch" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_request_manifest_mismatch_rejected(tmp_path: Path) -> None:
    auth = _rehash({**_valid_authorization(), "request_manifest_sha256": "2" * 64})
    assert "request_manifest_mismatch" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_expired_authorization_rejected(tmp_path: Path) -> None:
    auth = _valid_authorization()
    result = _review(auth, _valid_attestation(), tmp_path, now=NOW + timedelta(hours=13))
    assert "authorization_expired" in _codes(result)


def test_expired_attestation_rejected(tmp_path: Path) -> None:
    att = _valid_attestation()
    result = _review(_valid_authorization(), att, tmp_path, now=NOW + timedelta(minutes=25))
    assert "attestation_expired" in _codes(result)


def test_future_dated_artifact_rejected(tmp_path: Path) -> None:
    auth = _rehash(
        {
            **_valid_authorization(),
            "created_at": (NOW + timedelta(hours=1)).isoformat(),
            "expires_at": (NOW + timedelta(hours=2)).isoformat(),
        }
    )
    assert "future_dated" in _codes(_review(auth, _valid_attestation(), tmp_path))


@pytest.mark.parametrize(
    "statement",
    [
        "looks good",
        "continue",
        "probably okay",
        "run it",
        "I authorize the acquisition if it seems fine",
        "I authorize NeuralMarket to execute the pilot",  # no amount, wrong wording
    ],
)
def test_ambiguous_statement_rejected(tmp_path: Path, statement: str) -> None:
    auth = _rehash({**_valid_authorization(), "authorization_statement": statement})
    result = _review(auth, _valid_attestation(), tmp_path)
    assert "ambiguous_or_missing_statement" in _codes(result)


def test_reused_authorization_rejected(tmp_path: Path) -> None:
    marker = tmp_path / "consumed.local.json"
    marker.write_text("{}", encoding="utf-8")
    result = _review(
        _valid_authorization(), _valid_attestation(), tmp_path, consumption_marker=marker
    )
    assert "already_consumed" in _codes(result)
    consumed = _rehash({**_valid_authorization(), "consumed": True})
    assert "already_consumed" in _codes(_review(consumed, _valid_attestation(), tmp_path))


def test_paid_journal_conflict_rejected(tmp_path: Path) -> None:
    journal = tmp_path / "journal.sqlite"
    con = sqlite3.connect(journal)
    con.executescript(
        """
        CREATE TABLE consumed_authorizations (plan_hash TEXT, authorization_hash TEXT);
        CREATE TABLE requests (
            request_id TEXT, actual_billed_cost_usd TEXT, raw_path TEXT);
        CREATE TABLE billing_reconciliations (
            artifact_hash TEXT, billing_resolution TEXT,
            supersedes_reconciliation_hash TEXT);
        INSERT INTO requests VALUES ('abc123', '0.24', '/data/raw/abc.dbn.zst');
        """
    )
    con.commit()
    con.close()
    result = _review(_valid_authorization(), _valid_attestation(), tmp_path, journal_path=journal)
    assert "paid_journal_conflict" in _codes(result)


def test_tampered_review_hash_rejected(tmp_path: Path) -> None:
    auth = dict(_valid_authorization())
    auth["authorized_ceiling_usd"] = "0.55"  # edit after signing, no rehash
    assert "hash_tampered" in _codes(_review(auth, _valid_attestation(), tmp_path))


def test_valid_fake_pair_reaches_pre_provider_gate(tmp_path: Path) -> None:
    result = _review(_valid_authorization(), _valid_attestation(), tmp_path)
    assert result.ok, [f"{rej.code}: {rej.detail}" for rej in result.rejections]
    assert result.rejections == []
    # Even the valid pair never constructs a provider: the module has no
    # databento import and the autouse guard verifies none was pulled in.


def test_reconciled_not_billed_journal_does_not_block(tmp_path: Path) -> None:
    journal = tmp_path / "journal.sqlite"
    con = sqlite3.connect(journal)
    con.executescript(
        """
        CREATE TABLE consumed_authorizations (plan_hash TEXT, authorization_hash TEXT);
        CREATE TABLE requests (
            request_id TEXT, actual_billed_cost_usd TEXT, raw_path TEXT);
        CREATE TABLE billing_reconciliations (
            artifact_hash TEXT, billing_resolution TEXT,
            supersedes_reconciliation_hash TEXT);
        INSERT INTO consumed_authorizations
            VALUES ('9654fe1c' || printf('%056d', 0), 'x');
        INSERT INTO requests VALUES ('2750995e515e4f1a', NULL, NULL);
        INSERT INTO billing_reconciliations VALUES ('h1', 'unresolved', NULL);
        INSERT INTO billing_reconciliations VALUES ('h2', 'confirmed_not_billed', 'h1');
        """
    )
    con.commit()
    con.close()
    result = _review(_valid_authorization(), _valid_attestation(), tmp_path, journal_path=journal)
    assert result.ok, [f"{rej.code}: {rej.detail}" for rej in result.rejections]


def test_template_files_validate_against_schemas() -> None:
    root = Path(__file__).resolve().parents[4]
    auth_template = root / (
        "reports/data/execution/authorization/pilot_purchase_authorization_template.local.json"
    )
    att_template = root / (
        "reports/data/execution/authorization/pilot_portal_attestation_template.local.json"
    )
    if not auth_template.exists():
        pytest.skip("local templates not present in this checkout")
    auth = load_json_artifact(
        auth_template,
        schema_relative="data_contracts/pilot_purchase_authorization.schema.json",
        kind="authorization",
    )
    att = load_json_artifact(
        att_template,
        schema_relative="data_contracts/pilot_portal_attestation.schema.json",
        kind="attestation",
    )
    assert auth["template_only"] is True and auth["authorized"] is False
    assert att["template_only"] is True and att["attested"] is False
    assert att["portal_estimate_usd"] is None and att["operator_confirmation"] is None
    assert auth["authorization_statement"] is None
    # Templates themselves must be rejected outright.
    result = review_purchase_package(
        authorization=auth,
        attestation=att,
        expected=EXPECTED,
        now=NOW,
        journal_path=root / "nonexistent-journal.sqlite",
        consumption_marker=root / "nonexistent-marker.json",
    )
    assert not result.ok
    assert "template_only" in {rej.code for rej in result.rejections}


def test_json_artifact_schema_rejection(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid_authorization"):
        load_json_artifact(
            bad,
            schema_relative="data_contracts/pilot_purchase_authorization.schema.json",
            kind="authorization",
        )
