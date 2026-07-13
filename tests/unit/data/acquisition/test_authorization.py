from datetime import UTC, datetime, timedelta

import pytest

from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    AuthorizationError,
    PilotAuthorization,
    compute_authorization_hash,
    validate_authorization,
)

pytestmark = pytest.mark.unit


def _valid_payload(**overrides):
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
    }
    defaults.update(kwargs)
    validate_authorization(auth, **defaults)


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
    payload = _valid_payload(
        authorized_at=(now - timedelta(days=2)).isoformat(),
        expires_at=(now - timedelta(days=1)).isoformat(),
    )
    with pytest.raises(AuthorizationError) as exc:
        _validate(payload, now=now)
    assert exc.value.reason == "expired"


def test_rejects_authorization_before_validity_window() -> None:
    now = datetime.now(UTC)
    payload = _valid_payload(
        authorized_at=(now + timedelta(minutes=1)).isoformat(),
        expires_at=(now + timedelta(days=1)).isoformat(),
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
    payload["authorized_by"] = "Someone Else"  # mutate after hashing
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

    # The template's placeholder hash fields (e.g. "REPLACE_WITH_EXACT_HASH")
    # are plain strings, so schema/pydantic parsing succeeds; it is
    # validate_authorization's hash-tampered check that must reject it,
    # since the placeholder authorization_hash never matches a freshly
    # recomputed hash of the rest of the payload.
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
