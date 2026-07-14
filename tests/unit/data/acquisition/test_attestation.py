from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from neuralmarket.data.acquisition.attestation import (
    PortalAttestationError,
    PortalLimitAttestation,
    compute_attestation_hash,
    validate_portal_attestation,
)

pytestmark = pytest.mark.unit


def _attestation(**changes: object) -> PortalLimitAttestation:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    payload: dict[str, object] = {
        "attestation_version": "1.0",
        "portal_historical_limit_usd": "5.00",
        "portal_limit_confirmed": True,
        "portal_limit_confirmed_at": now.isoformat(),
        "portal_limit_confirmed_by": "local_operator",
        "confirmation_method": "manual_portal_review",
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
        "plan_hash": "a" * 64,
    }
    payload.update(changes)
    payload["attestation_hash"] = compute_attestation_hash(payload)
    return PortalLimitAttestation.model_validate(payload)


def test_valid_portal_attestation_passes() -> None:
    validate_portal_attestation(
        _attestation(), plan_hash="a" * 64, now=datetime(2026, 7, 13, 0, 1, tzinfo=UTC)
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"portal_limit_confirmed": False}, "not confirmed"),
        ({"portal_historical_limit_usd": Decimal("4.99")}, "exactly 5.00"),
        ({"plan_hash": "b" * 64}, "plan_hash"),
    ],
)
def test_portal_attestation_rejects_invalid_values(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(PortalAttestationError, match=message):
        validate_portal_attestation(
            _attestation(**changes), plan_hash="a" * 64, now=datetime(2026, 7, 13, 0, 1, tzinfo=UTC)
        )


def test_portal_attestation_rejects_expiry_and_tampering() -> None:
    with pytest.raises(PortalAttestationError, match="expired"):
        validate_portal_attestation(
            _attestation(expires_at="2026-07-13T00:00:00+00:00"),
            plan_hash="a" * 64,
            now=datetime(2026, 7, 13, 0, 1, tzinfo=UTC),
        )
    tampered = _attestation().model_copy(update={"attestation_hash": "0" * 64})
    with pytest.raises(PortalAttestationError, match="hash"):
        validate_portal_attestation(
            tampered, plan_hash="a" * 64, now=datetime(2026, 7, 13, 0, 1, tzinfo=UTC)
        )
