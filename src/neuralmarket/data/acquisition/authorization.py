"""One-time, hash-bound authorization for a real paid pilot data purchase.

A real Databento request must never fire without a valid, single-use
authorization artifact: the plan/manifest/policy hashes must match the exact
artifacts under review, the artifact must not have expired or already been
consumed, and the artifact's own hash must confirm it has not been edited
after it was signed. This module is the gate; it makes no purchase decisions
itself.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, field_validator

from neuralmarket.core.environment import find_repository_root
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.manifests import canonical_dumps

CONFIRMATION_PHRASE = "AUTHORIZE_NEURALMARKET_PILOT_PURCHASE"

_SCHEMA_RELATIVE_PATH = "data_contracts/pilot_authorization.schema.json"

# Fields excluded from an authorization's own hash input (the hash field itself).
_HASH_EXCLUDED = ("authorization_hash",)


class AuthorizationError(ValueError):
    """Raised when a pilot authorization artifact fails validation.

    Attributes:
        reason: A short machine-readable rejection code.
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        """Store the machine-readable rejection ``reason`` alongside the message."""
        self.reason = reason
        super().__init__(message or reason)


class PilotAuthorization(BaseModel):
    """A signed, single-use authorization to spend real money on the pilot purchase."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_version: str
    pilot_plan_hash: str
    source_manifest_hash: str
    split_manifest_hash: str
    acquisition_policy_hash: str
    maximum_spend_usd: Decimal = Field(le=Decimal("5.00"))
    authorized_currency: str
    authorized_at: datetime
    expires_at: datetime
    authorized_by: str
    confirmation_phrase: str
    purchase_authorized: bool
    authorization_hash: str

    @field_validator("maximum_spend_usd", mode="before")
    @classmethod
    def _coerce_maximum_spend(cls, value: Any) -> Decimal:
        return to_decimal(value)


def compute_authorization_hash(auth_payload_without_hash: dict[str, Any]) -> str:
    """Return the SHA-256 hash of an authorization payload's canonical JSON.

    ``authorization_hash`` is stripped from the payload before hashing
    (whether or not present), mirroring ``compute_request_hash`` /
    ``canonical_hash`` so the hash never depends on itself.
    """
    reduced = {k: v for k, v in auth_payload_without_hash.items() if k not in _HASH_EXCLUDED}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def load_authorization(path: Path) -> PilotAuthorization:
    """Parse and schema-validate a pilot authorization artifact from disk.

    Args:
        path: Path to a JSON authorization artifact.

    Returns:
        The validated, unconsumed-state ``PilotAuthorization``. Callers must
        still call ``validate_authorization`` before treating it as live.

    Raises:
        jsonschema.ValidationError: If the JSON does not match the checked-in
            contract schema.
        pydantic.ValidationError: If the JSON does not match the model
            (including the ``maximum_spend_usd`` <= 5.00 cap).
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    repo_root = find_repository_root()
    schema = json.loads((repo_root / _SCHEMA_RELATIVE_PATH).read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    return PilotAuthorization.model_validate(payload)


def validate_authorization(
    auth: PilotAuthorization,
    *,
    expected_plan_hash: str,
    expected_source_manifest_hash: str,
    expected_split_manifest_hash: str,
    expected_acquisition_policy_hash: str,
    now: datetime,
    consumed_ids: set[str],
) -> None:
    """Validate a parsed authorization against the live plan/state, or raise.

    Raises:
        AuthorizationError: With ``.reason`` set to the first rejection
            reason encountered, checked in this order: hash tampering, plan
            hash, manifest hashes, expiry, single-use consumption, currency,
            confirmation phrase, then the explicit purchase-authorized flag.
    """
    # Rebuild the payload manually (not via model_dump) so string/datetime
    # formatting exactly matches what was hashed on disk: Decimal round-trips
    # as its original "5.00" string either way, but model_dump(mode="json")
    # renders aware datetimes with a "Z" suffix where the source JSON used
    # "+00:00", which would make every untampered artifact look tampered.
    payload = {
        "authorization_version": auth.authorization_version,
        "pilot_plan_hash": auth.pilot_plan_hash,
        "source_manifest_hash": auth.source_manifest_hash,
        "split_manifest_hash": auth.split_manifest_hash,
        "acquisition_policy_hash": auth.acquisition_policy_hash,
        "maximum_spend_usd": str(auth.maximum_spend_usd),
        "authorized_currency": auth.authorized_currency,
        "authorized_at": auth.authorized_at.isoformat(),
        "expires_at": auth.expires_at.isoformat(),
        "authorized_by": auth.authorized_by,
        "confirmation_phrase": auth.confirmation_phrase,
        "purchase_authorized": auth.purchase_authorized,
    }
    fresh_hash = compute_authorization_hash(payload)
    if not hmac.compare_digest(fresh_hash, auth.authorization_hash):
        raise AuthorizationError("hash_tampered", "authorization_hash does not match payload")

    if not hmac.compare_digest(auth.pilot_plan_hash, expected_plan_hash):
        raise AuthorizationError("plan_hash_mismatch", "pilot_plan_hash does not match plan")

    if not hmac.compare_digest(
        auth.source_manifest_hash, expected_source_manifest_hash
    ) or not hmac.compare_digest(
        auth.split_manifest_hash, expected_split_manifest_hash
    ) or not hmac.compare_digest(
        auth.acquisition_policy_hash, expected_acquisition_policy_hash
    ):
        raise AuthorizationError(
            "manifest_hash_mismatch", "a source/split/policy manifest hash does not match"
        )

    if now > auth.expires_at:
        raise AuthorizationError("expired", "authorization has expired")

    if auth.pilot_plan_hash in consumed_ids:
        raise AuthorizationError("already_consumed", "authorization already consumed")

    if not hmac.compare_digest(auth.authorized_currency, "USD"):
        raise AuthorizationError("currency_mismatch", "authorized_currency must be USD")

    if not hmac.compare_digest(auth.confirmation_phrase, CONFIRMATION_PHRASE):
        raise AuthorizationError(
            "confirmation_phrase_mismatch", "confirmation_phrase does not match"
        )

    if auth.purchase_authorized is not True:
        raise AuthorizationError("purchase_not_authorized", "purchase_authorized is not True")


def mark_consumed(request_id_or_plan_hash: str, consumed_ids: set[str]) -> None:
    """Record an authorization identifier as consumed (single-use tracking)."""
    consumed_ids.add(request_id_or_plan_hash)
