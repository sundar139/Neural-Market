"""Manual, hash-bound Databento portal-limit attestation.

The provider API cannot read or set a portal spending limit.  This module
therefore records only a time-limited operator attestation; it never claims
that the limit was API verified and never stores portal/account information.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from neuralmarket.core.environment import find_repository_root
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.manifests import canonical_dumps

_SCHEMA = "data_contracts/portal_limit_attestation.schema.json"
_METHOD = "manual_portal_review"

#: Maximum portal source-evidence validity window (observation to expiry).
#: Mirrors ``purchase_review.ATTESTATION_VALIDITY`` so both portal records age out
#: on the same 30-minute policy.
PORTAL_EVIDENCE_VALIDITY = timedelta(minutes=30)


class PortalAttestationError(ValueError):
    """A portal attestation is missing, stale, tampered, or mismatched."""


class PortalLimitAttestation(BaseModel):
    """A short-lived, non-sensitive operator statement about the portal limit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attestation_version: str
    portal_historical_limit_usd: Decimal = Field(le=Decimal("5.00"))
    portal_limit_confirmed: bool
    portal_limit_confirmed_at: datetime
    portal_limit_confirmed_by: str
    confirmation_method: str
    expires_at: datetime
    plan_hash: str
    attestation_hash: str

    @field_validator("portal_historical_limit_usd", mode="before")
    @classmethod
    def _money(cls, value: Any) -> Decimal:
        return to_decimal(value)

    @field_validator("portal_limit_confirmed_at", "expires_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("portal-attestation timestamps must be timezone-aware")
        return value.astimezone(UTC)


class PortalSourceEvidence(BaseModel):
    """Sanitized, source-backed record of what the provider portal displayed.

    The portal shows bounded values such as ``<$0.01``. Rather than inventing a
    precision the UI never gave, the display text is kept verbatim alongside a
    relation and the exact Decimal bound it implies, and every capacity check
    uses that bound conservatively.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["portal-source-evidence-v1"]
    observed_at: datetime
    timezone: str = Field(min_length=1)
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    usage_display_text: str = Field(min_length=1)
    usage_relation: Literal["exact", "lt", "lte"]
    usage_amount_usd: Decimal = Field(ge=Decimal(0))
    currency: Literal["USD"]
    configured_limit_usd: Decimal = Field(ge=Decimal(0))
    account_balance_usd: Decimal | None = None
    remaining_credits_usd: Decimal | None = None
    remaining_available_usd: Decimal | None = None
    source_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_reference: str = Field(min_length=1)
    source_classification: Literal["sanitized_screenshot", "sanitized_written_attestation"]
    reviewer: str = Field(min_length=1)
    review_method: str = Field(min_length=1)
    expires_at: datetime

    @field_validator(
        "usage_amount_usd",
        "configured_limit_usd",
        "account_balance_usd",
        "remaining_credits_usd",
        "remaining_available_usd",
        mode="before",
    )
    @classmethod
    def _money(cls, value: Any) -> Any:
        return value if value is None else to_decimal(value)

    @field_validator("observed_at", "billing_cycle_start", "billing_cycle_end", "expires_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("portal-source-evidence timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _check_windows(self) -> PortalSourceEvidence:
        if self.billing_cycle_end <= self.billing_cycle_start:
            raise ValueError("billing_cycle_end must be after billing_cycle_start")
        if self.expires_at <= self.observed_at:
            raise ValueError("expires_at must be after observed_at")
        if self.expires_at > self.observed_at + PORTAL_EVIDENCE_VALIDITY:
            raise ValueError("portal source evidence validity exceeds 30 minutes")
        return self

    @property
    def conservative_usage_upper_bound_usd(self) -> Decimal:
        """Return the highest usage the display can possibly represent.

        ``exact`` is already the value; ``lt`` and ``lte`` are both bounded above
        by the stated amount, so the amount is the conservative figure in all
        three cases.
        """
        return self.usage_amount_usd

    @property
    def conservative_remaining_capacity_usd(self) -> Decimal:
        """Return limit minus the conservative usage bound, floored at zero."""
        return max(Decimal(0), self.configured_limit_usd - self.conservative_usage_upper_bound_usd)


def validate_portal_source_evidence(evidence: PortalSourceEvidence, *, now: datetime) -> None:
    """Fail closed unless the portal source evidence is still current.

    Raises:
        PortalAttestationError: If ``now`` is naive, or the evidence is
            future-dated or expired.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise PortalAttestationError("validation time must be timezone-aware")
    now = now.astimezone(UTC)
    if evidence.observed_at > now:
        raise PortalAttestationError("portal source evidence is observed in the future")
    if evidence.expires_at <= now:
        raise PortalAttestationError("portal source evidence has expired")


def compute_attestation_hash(payload: dict[str, Any]) -> str:
    """Hash canonical attestation content, excluding its self-hash."""
    reduced = {key: value for key, value in payload.items() if key != "attestation_hash"}
    if "portal_historical_limit_usd" in reduced:
        reduced["portal_historical_limit_usd"] = str(
            to_decimal(reduced["portal_historical_limit_usd"])
        )
    for key in ("portal_limit_confirmed_at", "expires_at"):
        if key in reduced:
            value = reduced[key]
            stamp = (
                value
                if isinstance(value, datetime)
                else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            )
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError("portal-attestation timestamps must be timezone-aware")
            reduced[key] = stamp.astimezone(UTC).isoformat()
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def load_portal_attestation(path: Path) -> PortalLimitAttestation:
    """Load a local portal attestation against the checked-in schema."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = find_repository_root()
    schema = json.loads((root / _SCHEMA).read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    return PortalLimitAttestation.model_validate(payload)


def validate_portal_attestation(
    attestation: PortalLimitAttestation, *, plan_hash: str, now: datetime
) -> None:
    """Fail closed unless an exact, recent manual $5 portal review exists."""
    payload = attestation.model_dump(mode="json")
    if not hmac.compare_digest(compute_attestation_hash(payload), attestation.attestation_hash):
        raise PortalAttestationError("attestation_hash does not match payload")
    if not hmac.compare_digest(attestation.plan_hash, plan_hash):
        raise PortalAttestationError("attestation plan_hash does not match plan")
    if attestation.portal_historical_limit_usd != Decimal("5.00"):
        raise PortalAttestationError("portal historical limit must be exactly 5.00 USD")
    if not attestation.portal_limit_confirmed:
        raise PortalAttestationError("portal limit is not confirmed")
    if attestation.confirmation_method != _METHOD:
        raise PortalAttestationError("portal limit requires manual_portal_review")
    if not attestation.portal_limit_confirmed_by.strip():
        raise PortalAttestationError("portal-limit operator label is required")
    if now.tzinfo is None or now.utcoffset() is None:
        raise PortalAttestationError("validation time must be timezone-aware")
    now = now.astimezone(UTC)
    if attestation.expires_at <= now:
        raise PortalAttestationError("portal attestation is expired")
    if attestation.expires_at > attestation.portal_limit_confirmed_at + timedelta(minutes=30):
        raise PortalAttestationError("portal attestation may not exceed 30 minutes")
