"""Offline tests for the source-backed portal evidence contract.

The portal shows bounded values such as ``<$0.01``; these tests pin that the
contract stores the display verbatim and treats the stated amount as the
conservative upper bound, without inventing precision the UI never gave.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from neuralmarket.data.acquisition.attestation import (
    PortalAttestationError,
    PortalSourceEvidence,
    validate_portal_source_evidence,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA = _ROOT / "data_contracts/pilot_portal_attestation.schema.json"

OBSERVED = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)


def _payload(**changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contract_version": "portal-source-evidence-v1",
        "observed_at": OBSERVED.isoformat(),
        "timezone": "America/New_York (EDT)",
        "billing_cycle_basis": "dated",
        "billing_cycle_start": "2026-06-30T20:00:00-04:00",
        "billing_cycle_end": "2026-07-31T20:00:00-04:00",
        "usage_display_text": "<$0.01",
        "usage_relation": "lt",
        "usage_amount_usd": "0.01",
        "currency": "USD",
        "configured_limit_usd": "5.00",
        "account_balance_usd": "0.00",
        "remaining_credits_usd": "125.00",
        "remaining_available_usd": None,
        "source_evidence_sha256": "a" * 64,
        "source_reference": "reports/data/execution/portal_observation.local.json",
        "source_classification": "sanitized_written_attestation",
        "reviewer": "neuralmarket_local_operator",
        "review_method": "manual_portal_inspection",
        "expires_at": (OBSERVED + timedelta(minutes=30)).isoformat(),
    }
    payload.update(changes)
    return payload


def _evidence(**changes: Any) -> PortalSourceEvidence:
    return PortalSourceEvidence.model_validate(_payload(**changes))


# ── Usage displays ───────────────────────────────────────────────────


def test_bounded_less_than_display_keeps_its_text_and_bound() -> None:
    evidence = _evidence()
    assert evidence.usage_display_text == "<$0.01"
    assert evidence.usage_relation == "lt"
    assert evidence.usage_amount_usd == Decimal("0.01")
    assert evidence.conservative_usage_upper_bound_usd == Decimal("0.01")


def test_exact_display_is_its_own_bound() -> None:
    evidence = _evidence(
        usage_display_text="$1.25", usage_relation="exact", usage_amount_usd="1.25"
    )
    assert evidence.conservative_usage_upper_bound_usd == Decimal("1.25")


def test_less_than_or_equal_display_is_bounded_by_its_amount() -> None:
    evidence = _evidence(
        usage_display_text="<=$0.05", usage_relation="lte", usage_amount_usd="0.05"
    )
    assert evidence.conservative_usage_upper_bound_usd == Decimal("0.05")


# ── Conservative capacity ────────────────────────────────────────────


def test_conservative_capacity_subtracts_the_upper_bound() -> None:
    # 5.00 limit against a "<$0.01" display: assume the full 0.01 was spent.
    assert _evidence().conservative_remaining_capacity_usd == Decimal("4.99")


def test_conservative_capacity_never_goes_negative() -> None:
    evidence = _evidence(
        configured_limit_usd="0.50",
        usage_display_text="$0.75",
        usage_relation="exact",
        usage_amount_usd="0.75",
    )
    assert evidence.conservative_remaining_capacity_usd == Decimal("0")


def test_money_never_passes_through_binary_float() -> None:
    evidence = _evidence(usage_amount_usd="0.10", configured_limit_usd="0.30")
    assert evidence.conservative_remaining_capacity_usd == Decimal("0.20")
    assert str(evidence.conservative_remaining_capacity_usd) == "0.20"


# ── Rejections ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"usage_amount_usd": "not-a-number"}, "usage_amount_usd"),
        ({"usage_amount_usd": "-0.01"}, "usage_amount_usd"),
        ({"usage_relation": "approximately"}, "usage_relation"),
        ({"source_evidence_sha256": "zz"}, "source_evidence_sha256"),
        ({"source_evidence_sha256": "A" * 64}, "source_evidence_sha256"),
        ({"source_classification": "screenshot"}, "source_classification"),
        ({"currency": "EUR"}, "currency"),
        ({"timezone": ""}, "timezone"),
        ({"reviewer": ""}, "reviewer"),
    ],
)
def test_malformed_fields_are_rejected(changes: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValidationError, match=reason):
        _evidence(**changes)


@pytest.mark.parametrize(
    "missing",
    ["source_evidence_sha256", "source_reference", "source_classification", "observed_at"],
)
def test_missing_required_source_fields_are_rejected(missing: str) -> None:
    payload = _payload()
    del payload[missing]
    with pytest.raises(ValidationError, match=missing):
        PortalSourceEvidence.model_validate(payload)


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _evidence(observed_at="2026-07-29T12:00:00")


def test_rolling_billing_cycle_needs_no_dates() -> None:
    """Some accounts bill on a rolling basis; that is recorded, not faked."""
    payload = _payload(billing_cycle_basis="rolling")
    del payload["billing_cycle_start"]
    del payload["billing_cycle_end"]
    evidence = PortalSourceEvidence.model_validate(payload)
    assert evidence.billing_cycle_basis == "rolling"
    assert evidence.billing_cycle_start is None
    assert evidence.billing_cycle_end is None
    # Capacity arithmetic is unaffected by the absence of cycle bounds.
    assert evidence.conservative_remaining_capacity_usd == Decimal("4.99")


def test_rolling_billing_cycle_must_not_carry_dates() -> None:
    with pytest.raises(ValidationError, match="must not carry start or end"):
        _evidence(billing_cycle_basis="rolling")


def test_dated_billing_cycle_requires_both_bounds() -> None:
    payload = _payload()
    del payload["billing_cycle_end"]
    with pytest.raises(ValidationError, match="requires billing_cycle_start and _end"):
        PortalSourceEvidence.model_validate(payload)


def test_dated_cycle_rejects_an_observation_outside_it() -> None:
    """The stale-cycle case that slipped through before: observed after cycle end."""
    with pytest.raises(ValidationError, match="must fall inside the stated billing cycle"):
        _evidence(
            billing_cycle_start="2026-06-30T20:00:00-04:00",
            billing_cycle_end="2026-07-27T20:00:00-04:00",
        )


def test_inverted_billing_cycle_is_rejected() -> None:
    with pytest.raises(ValidationError, match="billing_cycle_end"):
        _evidence(
            billing_cycle_start="2026-07-27T20:00:00-04:00",
            billing_cycle_end="2026-06-30T20:00:00-04:00",
        )


def test_validity_longer_than_thirty_minutes_is_rejected() -> None:
    with pytest.raises(ValidationError, match="exceeds 30 minutes"):
        _evidence(expires_at=(OBSERVED + timedelta(minutes=31)).isoformat())


def test_stale_portal_evidence_is_rejected() -> None:
    evidence = _evidence()
    with pytest.raises(PortalAttestationError, match="expired"):
        validate_portal_source_evidence(evidence, now=OBSERVED + timedelta(minutes=31))


def test_future_dated_portal_evidence_is_rejected() -> None:
    evidence = _evidence()
    with pytest.raises(PortalAttestationError, match="future"):
        validate_portal_source_evidence(evidence, now=OBSERVED - timedelta(minutes=1))


def test_fresh_portal_evidence_passes() -> None:
    validate_portal_source_evidence(_evidence(), now=OBSERVED + timedelta(minutes=29))


def test_naive_validation_time_is_rejected() -> None:
    with pytest.raises(PortalAttestationError, match="timezone-aware"):
        validate_portal_source_evidence(_evidence(), now=datetime(2026, 7, 29, 12, 5))


# ── Schema agreement ─────────────────────────────────────────────────


def _attestation(**changes: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "pilot-portal-attestation-v1",
        "template_only": False,
        "attested": True,
        "repository_head": "0" * 40,
        "dataset_scope": ["OPRA.PILLAR"],
        "schema_scope": ["cbbo-1m"],
        "symbol_scope": ["SPY.OPT"],
        "window_start": "2019-01-02T20:50:00+00:00",
        "window_end": "2019-01-02T21:00:00+00:00",
        "portal_estimate_usd": "0.01",
        "currency": "USD",
        "observed_at": OBSERVED.isoformat(),
        "expires_at": (OBSERVED + timedelta(minutes=30)).isoformat(),
        "completed_checkpoint_sha256": "b" * 64,
        "request_manifest_sha256": "c" * 64,
        "operator_confirmation": "reviewed",
        "attestation_hash": "d" * 64,
    }
    payload.update(changes)
    return payload


def test_attestation_schema_accepts_a_source_evidence_block() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(_attestation(source_evidence=_payload()), schema)


def test_attestation_schema_still_accepts_artifacts_without_source_evidence() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(_attestation(), schema)


def test_attestation_schema_rejects_source_evidence_on_a_template() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    template = {
        **_attestation(),
        "template_only": True,
        "attested": False,
        "portal_estimate_usd": None,
        "operator_confirmation": None,
        "observed_at": None,
        "expires_at": None,
        "attestation_hash": None,
        "source_evidence": _payload(),
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(template, schema)


def test_attestation_schema_rejects_an_incomplete_source_evidence_block() -> None:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    block = _payload()
    del block["source_evidence_sha256"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_attestation(source_evidence=block), schema)


# ── Authorization v2 compatibility ───────────────────────────────────


def test_authorization_v2_binds_the_source_backed_attestation(tmp_path: Path) -> None:
    """The existing strict path consumes the new contract with no changes to it."""
    import hashlib
    from datetime import timedelta as _timedelta

    from neuralmarket.data.acquisition.authorization import (
        CONFIRMATION_PHRASE,
        PilotAuthorization,
        build_remaining_scope,
        compute_authorization_hash,
        validate_authorization,
    )

    source = tmp_path / "portal_observation.local.json"
    source.write_text(json.dumps({"sanitized": True}), encoding="utf-8")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()

    evidence_block = _payload(source_evidence_sha256=source_sha, source_reference=source.name)
    PortalSourceEvidence.model_validate(evidence_block)
    attestation_file = tmp_path / "portal_attestation.local.json"
    attestation_file.write_text(
        json.dumps(_attestation(source_evidence=evidence_block)), encoding="utf-8"
    )
    attestation_sha = hashlib.sha256(attestation_file.read_bytes()).hexdigest()
    jsonschema.validate(
        json.loads(attestation_file.read_text(encoding="utf-8")),
        json.loads(_SCHEMA.read_text(encoding="utf-8")),
    )

    scope = build_remaining_scope(
        source_plan_hash="p" * 64,
        completed_request_ids=["completed-0"],
        completed_request_hashes=["b" * 64],
        remaining_request_ids=[f"remaining-{index:02d}" for index in range(24)],
        remaining_request_hashes=[f"{index:064x}" for index in range(24)],
    )
    now = OBSERVED
    payload: dict[str, Any] = {
        "authorization_version": "2.0",
        "pilot_plan_hash": "p" * 64,
        "source_manifest_hash": "s" * 64,
        "split_manifest_hash": "v" * 64,
        "acquisition_policy_hash": "a" * 64,
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": (now - _timedelta(minutes=1)).isoformat(),
        "expires_at": (now + _timedelta(minutes=20)).isoformat(),
        "authorized_by": "Test Operator",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
        "remaining_scope_hash": scope.scope_hash,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - _timedelta(minutes=5)).isoformat(),
            "expires_at": (now + _timedelta(minutes=30)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": attestation_sha,
            "observed_at": now.isoformat(),
            "expires_at": (now + _timedelta(minutes=30)).isoformat(),
        },
        "portal_source_evidence_sha256": source_sha,
    }
    payload["authorization_hash"] = compute_authorization_hash(payload)

    validate_authorization(
        PilotAuthorization.model_validate(payload),
        expected_plan_hash="p" * 64,
        expected_source_manifest_hash="s" * 64,
        expected_split_manifest_hash="v" * 64,
        expected_acquisition_policy_hash="a" * 64,
        expected_scope=scope,
        expected_cost_evidence_sha256="c" * 64,
        expected_portal_evidence_sha256=attestation_sha,
        expected_portal_source_evidence_sha256=source_sha,
        now=now + _timedelta(minutes=1),
        consumed_ids=set(),
    )
