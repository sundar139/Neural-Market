from datetime import UTC, datetime, timedelta

import pytest

from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    AuthorizationError,
    EvidenceReference,
    PilotAuthorization,
    build_remaining_scope,
    compute_authorization_hash,
    validate_authorization,
)

pytestmark = pytest.mark.unit

_SCOPE_HASH = build_remaining_scope(
    source_plan_hash="p" * 64,
    completed_request_ids=["2750995e515e4f1a"],
    completed_request_hashes=["b" * 64],
    remaining_request_ids=[f"{i:016x}" for i in range(24)],
    remaining_request_hashes=[f"{i:064x}" for i in range(24)],
).scope_hash


def _valid_payload(**overrides):
    now = datetime.now(UTC)
    payload: dict = {
        "authorization_version": "2.0",
        "pilot_plan_hash": "p" * 64,
        "source_manifest_hash": "s" * 64,
        "split_manifest_hash": "v" * 64,
        "acquisition_policy_hash": "a" * 64,
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "authorized_by": "Test User",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
        "remaining_scope_hash": _SCOPE_HASH,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        },
    }
    payload.update(overrides)
    payload["authorization_hash"] = compute_authorization_hash(payload)
    return payload


def _validate(payload, **kwargs):
    auth = PilotAuthorization.model_validate(payload)
    defaults = {
        "expected_plan_hash": "p" * 64,
        "expected_source_manifest_hash": "s" * 64,
        "expected_split_manifest_hash": "v" * 64,
        "expected_acquisition_policy_hash": "a" * 64,
        "now": datetime.now(UTC),
        "consumed_ids": set(),
        "expected_scope_hash": _SCOPE_HASH,
        "expected_cost_evidence_sha256": "c" * 64,
        "expected_portal_evidence_sha256": "d" * 64,
    }
    defaults.update(kwargs)
    validate_authorization(auth, **defaults)


# ── v2 valid ──────────────────────────────────────────────────────────


def test_valid_authorization_passes() -> None:
    _validate(_valid_payload())


def test_authorization_hash_canonicalizes_equivalent_utc_timestamp_forms() -> None:
    payload = _valid_payload(
        authorized_at="2026-07-13T09:00:00Z",
        expires_at="2026-07-14T09:00:00Z",
    )
    payload["authorization_hash"] = compute_authorization_hash(payload)
    _validate(payload, now=datetime(2026, 7, 13, 10, tzinfo=UTC))

    equivalent = {
        **payload,
        "authorized_at": "2026-07-13T09:00:00+00:00",
        "expires_at": "2026-07-14T09:00:00+00:00",
    }
    assert compute_authorization_hash(equivalent) == payload["authorization_hash"]


# ── Existing checks (v2 context) ─────────────────────────────────────


def test_rejects_plan_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_plan_hash="x" * 64)
    assert exc.value.reason == "plan_hash_mismatch"


def test_rejects_manifest_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_source_manifest_hash="x" * 64)
    assert exc.value.reason == "manifest_hash_mismatch"


def test_rejects_split_manifest_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_split_manifest_hash="x" * 64)
    assert exc.value.reason == "manifest_hash_mismatch"


def test_rejects_acquisition_policy_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_acquisition_policy_hash="x" * 64)
    assert exc.value.reason == "manifest_hash_mismatch"


def test_rejects_expired() -> None:
    now = datetime.now(UTC)
    # evidence must stay fresh; only auth should expire
    evidence_expiry = (now + timedelta(hours=2)).isoformat()
    payload = _valid_payload(
        authorized_at=(now - timedelta(days=2)).isoformat(),
        expires_at=(now - timedelta(days=1)).isoformat(),
        cost_evidence={
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": evidence_expiry,
        },
        portal_evidence={
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": evidence_expiry,
        },
    )
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "expired"


def test_rejects_authorization_before_validity_window() -> None:
    now = datetime.now(UTC)
    payload = _valid_payload(
        authorized_at=(now + timedelta(minutes=1)).isoformat(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
    )
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "not_yet_valid"


def test_rejects_invalid_authorization_interval() -> None:
    now = datetime.now(UTC)
    payload = _valid_payload(
        authorized_at=now.isoformat(),
        expires_at=(now - timedelta(seconds=1)).isoformat(),
    )
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "invalid_validity_interval"


def test_rejects_already_consumed() -> None:
    payload = _valid_payload()
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, consumed_ids={payload["pilot_plan_hash"]})
    assert exc.value.reason == "already_consumed"


def test_rejects_currency_mismatch() -> None:
    payload = _valid_payload(authorized_currency="EUR")
    payload["authorization_hash"] = compute_authorization_hash(payload)
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload)
    assert exc.value.reason == "currency_mismatch"


def test_rejects_confirmation_phrase_mismatch() -> None:
    payload = _valid_payload(confirmation_phrase="WRONG")
    payload["authorization_hash"] = compute_authorization_hash(payload)
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload)
    assert exc.value.reason == "confirmation_phrase_mismatch"


def test_rejects_purchase_not_authorized() -> None:
    payload = _valid_payload(purchase_authorized=False)
    payload["authorization_hash"] = compute_authorization_hash(payload)
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload)
    assert exc.value.reason == "purchase_not_authorized"


def test_rejects_tampered_hash() -> None:
    payload = _valid_payload()
    payload["authorized_by"] = "Someone Else"
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload)
    assert exc.value.reason == "hash_tampered"


def test_rejects_spend_cap_exceeded() -> None:
    with pytest.raises(ValueError):
        PilotAuthorization.model_validate(_valid_payload(maximum_spend_usd="5.01"))


def test_template_file_is_rejected(tmp_path) -> None:
    import json
    from pathlib import Path

    from neuralmarket.data.acquisition.authorization import load_authorization

    repo_root = Path(__file__).resolve().parents[4]
    template_path = repo_root / "configs/data/acquisition/pilot_authorization.template.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    assert template["purchase_authorized"] is False

    auth = load_authorization(template_path)
    with pytest.raises(AuthorizationError) as exc:
        _validate(
            template,
            expected_plan_hash=auth.pilot_plan_hash,
            expected_source_manifest_hash=auth.source_manifest_hash,
            expected_split_manifest_hash=auth.split_manifest_hash,
            expected_acquisition_policy_hash=auth.acquisition_policy_hash,
        )
    assert exc.value.reason == "hash_tampered"


# ── v1 rejection ─────────────────────────────────────────────────────


def test_rejects_v1_authorization() -> None:
    """v1 artifacts pass validation by default, but fail when v2 params expected."""
    now = datetime.now(UTC)
    payload = {
        "authorization_version": "1.0",
        "pilot_plan_hash": "p" * 64,
        "source_manifest_hash": "s" * 64,
        "split_manifest_hash": "v" * 64,
        "acquisition_policy_hash": "a" * 64,
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "authorized_by": "Test User",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
    }
    payload["authorization_hash"] = compute_authorization_hash(payload)
    auth = PilotAuthorization.model_validate(payload)

    # v1 passes when no v2 params are expected
    validate_authorization(
        auth,
        expected_plan_hash="p" * 64,
        expected_source_manifest_hash="s" * 64,
        expected_split_manifest_hash="v" * 64,
        expected_acquisition_policy_hash="a" * 64,
        now=now,
        consumed_ids=set(),
    )

    # v1 fails when v2 params are expected
    with pytest.raises(AuthorizationError) as exc:
        validate_authorization(
            auth,
            expected_plan_hash="p" * 64,
            expected_source_manifest_hash="s" * 64,
            expected_split_manifest_hash="v" * 64,
            expected_acquisition_policy_hash="a" * 64,
            now=now,
            consumed_ids=set(),
            expected_scope_hash="s" * 64,
        )
    assert exc.value.reason == "authorization_scope_missing"


# ── v2 scope rejection ───────────────────────────────────────────────


def test_rejects_scope_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_scope_hash="x" * 64)
    assert exc.value.reason == "scope_hash_mismatch"


def test_rejects_cost_evidence_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_cost_evidence_sha256="x" * 64)
    assert exc.value.reason == "cost_evidence_hash_mismatch"


def test_rejects_portal_evidence_hash_mismatch() -> None:
    with pytest.raises(AuthorizationError) as exc:
        _validate(_valid_payload(), expected_portal_evidence_sha256="x" * 64)
    assert exc.value.reason == "portal_evidence_hash_mismatch"


# ── staleness rejection ──────────────────────────────────────────────


def test_rejects_stale_cost_evidence() -> None:
    now = datetime.now(UTC)
    payload = _valid_payload(
        cost_evidence={
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(minutes=1)).isoformat(),
        },
    )
    payload["authorization_hash"] = compute_authorization_hash(payload)
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "cost_evidence_stale"


def test_rejects_stale_portal_evidence() -> None:
    now = datetime.now(UTC)
    payload = _valid_payload(
        portal_evidence={
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(minutes=1)).isoformat(),
        },
    )
    payload["authorization_hash"] = compute_authorization_hash(payload)
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "portal_evidence_stale"


# ── effective expiry rejection ───────────────────────────────────────


def test_rejects_authorization_expiry_exceeds_evidence() -> None:
    now = datetime.now(UTC)
    payload = _valid_payload(
        expires_at=(now + timedelta(days=7)).isoformat(),
        cost_evidence={
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    payload["authorization_hash"] = compute_authorization_hash(payload)
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "authorization_expiry_exceeds_evidence"


def test_accepts_bounded_authorization_expiry() -> None:
    """Authorization expiry ≤ evidence expiry should pass."""
    now = datetime.now(UTC)
    evidence_expiry = (now + timedelta(hours=1)).isoformat()
    payload = _valid_payload(
        expires_at=evidence_expiry,
        cost_evidence={
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": evidence_expiry,
        },
        portal_evidence={
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": evidence_expiry,
        },
    )
    payload["authorization_hash"] = compute_authorization_hash(payload)
    _validate(payload, now=now)


# ── remaining request scope ──────────────────────────────────────────


def test_scope_requires_exactly_25_total() -> None:
    with pytest.raises(ValueError):
        build_remaining_scope(
            source_plan_hash="p" * 64,
            completed_request_ids=["id1"],
            completed_request_hashes=["h1" * 32],
            remaining_request_ids=["id2"],
            remaining_request_hashes=["h2" * 32],
        )


def test_scope_deterministic() -> None:
    s1 = build_remaining_scope(
        source_plan_hash="p" * 64,
        completed_request_ids=["c1"],
        completed_request_hashes=["h" * 64],
        remaining_request_ids=[f"r{i}" for i in range(24)],
        remaining_request_hashes=[f"{i:064x}" for i in range(24)],
    )
    s2 = build_remaining_scope(
        source_plan_hash="p" * 64,
        completed_request_ids=["c1"],
        completed_request_hashes=["h" * 64],
        remaining_request_ids=[f"r{i}" for i in range(24)],
        remaining_request_hashes=[f"{i:064x}" for i in range(24)],
    )
    assert s1.scope_hash == s2.scope_hash


def test_scope_changes_with_different_ids() -> None:
    s1 = build_remaining_scope(
        source_plan_hash="p" * 64,
        completed_request_ids=["c1"],
        completed_request_hashes=["h" * 64],
        remaining_request_ids=[f"r{i}" for i in range(24)],
        remaining_request_hashes=[f"{i:064x}" for i in range(24)],
    )
    s2 = build_remaining_scope(
        source_plan_hash="p" * 64,
        completed_request_ids=["c1"],
        completed_request_hashes=["h" * 64],
        remaining_request_ids=[f"r{i}" for i in range(1, 25)],
        remaining_request_hashes=[f"{i:064x}" for i in range(1, 25)],
    )
    assert s1.scope_hash != s2.scope_hash


def test_evidence_reference_requires_timezone_aware() -> None:
    with pytest.raises(ValueError):
        EvidenceReference.model_validate(
            {
                "evidence_type": "test",
                "evidence_sha256": "c" * 64,
                "observed_at": "2026-01-01T00:00:00",
                "expires_at": "2026-01-02T00:00:00",
            }
        )
