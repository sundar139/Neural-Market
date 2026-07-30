"""One-time, hash-bound authorization for a real paid pilot data purchase.

A real Databento request must never fire without a valid, single-use
authorization artifact: the plan/manifest/policy hashes must match the exact
artifacts under review, the artifact must not have expired or already been
consumed, and the artifact's own hash must confirm it has not been edited
after it was signed. This module is the gate; it makes no purchase decisions
itself.

.. versionchanged:: 2.0
   Added ``remaining_scope_hash``, ``cost_evidence``, ``portal_evidence``,
   and ``portal_source_evidence_sha256`` fields.  v1 and legacy artifacts are
   rejected during execution validation with
   ``authorization_version_not_executable``.  ``load_authorization`` accepts
   any version for audit; only ``validate_authorization`` gates execution.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from neuralmarket.core.environment import find_repository_root
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.manifests import canonical_dumps

CONFIRMATION_PHRASE = "AUTHORIZE_NEURALMARKET_PILOT_PURCHASE"

_EXECUTABLE_VERSION = "2.0"

_SCOPE_VERSION: Literal["1.0"] = "1.0"

_SCHEMA_RELATIVE_PATH = "data_contracts/pilot_authorization.schema.json"

# Fields excluded from an authorization's own hash input (the hash field itself).
_HASH_EXCLUDED = ("authorization_hash",)

# Accepted authorization versions for parsing.
_V1 = "1.0"
_V2 = "2.0"
_LEGACY_V1 = "pilot-authorization-v1"
_SUPPORTED_VERSIONS = {_V1, _V2, _LEGACY_V1}


class AuthorizationError(ValueError):
    """Raised when a pilot authorization artifact fails validation.

    Attributes:
        reason: A short machine-readable rejection code.
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        """Store the machine-readable rejection ``reason`` alongside the message."""
        self.reason = reason
        super().__init__(message or reason)


# ── Remaining-request scope ──────────────────────────────────────────


class RemainingRequestScope(BaseModel):
    """Deterministic 24-request subset derived from the canonical 25-request plan.

    Excludes exactly the completed, settled request.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_version: Literal["1.0"] = _SCOPE_VERSION
    source_plan_hash: str
    derivation_rule: Literal["canonical_25_minus_settled"] = "canonical_25_minus_settled"
    completed_request_ids: list[str]
    completed_request_hashes: list[str]
    remaining_request_ids: list[str]
    remaining_request_hashes: list[str]
    duplicate_count: int = 0
    overlap_count: int = 0
    scope_hash: str

    @model_validator(mode="after")
    def _validate_scope(self) -> RemainingRequestScope:
        if len(self.completed_request_ids) != len(self.completed_request_hashes):
            raise ValueError("completed ID and hash lists must be same length")
        if len(self.remaining_request_ids) != len(self.remaining_request_hashes):
            raise ValueError("remaining ID and hash lists must be same length")
        if len(self.completed_request_ids) < 1:
            raise ValueError("scope must exclude at least one completed request")
        expected_count = len(self.completed_request_ids) + len(self.remaining_request_ids)
        if expected_count != 25:
            raise ValueError(f"scope must contain exactly 25 total requests, got {expected_count}")
        completed_set = set(self.completed_request_ids)
        remaining_set = set(self.remaining_request_ids)
        object.__setattr__(self, "overlap_count", len(completed_set & remaining_set))
        if self.overlap_count > 0:
            raise ValueError("completed and remaining request IDs must not overlap")
        object.__setattr__(
            self,
            "duplicate_count",
            (len(self.completed_request_ids) - len(completed_set))
            + (len(self.remaining_request_ids) - len(remaining_set)),
        )
        if self.duplicate_count > 0:
            raise ValueError("request ID lists must not contain duplicates")
        return self


def build_remaining_scope(
    *,
    source_plan_hash: str,
    completed_request_ids: list[str],
    completed_request_hashes: list[str],
    remaining_request_ids: list[str],
    remaining_request_hashes: list[str],
) -> RemainingRequestScope:
    """Build and self-hash a deterministic remaining-request scope."""
    payload: dict[str, object] = {
        "scope_version": _SCOPE_VERSION,
        "source_plan_hash": source_plan_hash,
        "derivation_rule": "canonical_25_minus_settled",
        "completed_request_ids": completed_request_ids,
        "completed_request_hashes": completed_request_hashes,
        "remaining_request_ids": remaining_request_ids,
        "remaining_request_hashes": remaining_request_hashes,
    }
    payload["scope_hash"] = _scope_canonical(payload)
    return RemainingRequestScope.model_validate(payload)


def _scope_canonical(payload: dict[str, object]) -> str:
    unsigned = {k: v for k, v in payload.items() if k != "scope_hash"}
    canonical = canonical_dumps(unsigned)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_remaining_scope(
    scope: RemainingRequestScope,
    *,
    canonical_requests: list[Any],
    source_plan_hash: str,
) -> None:
    """Fail closed unless ``scope`` is a faithful subset of the canonical plan.

    Checks the bound plan identity, the scope's own canonical hash, the exact
    24-request size, duplicate IDs and hashes, completed-request exclusion, and
    that every scoped ID/hash pair appears in the canonical plan with the same
    pairing. Call this before constructing any provider.

    Args:
        scope: The remaining-request scope under review.
        canonical_requests: The canonical 25-request pilot plan.
        source_plan_hash: The plan hash the scope must be bound to.

    Raises:
        AuthorizationError: On any mismatch, with a machine-readable reason.
    """
    if not hmac.compare_digest(scope.source_plan_hash, source_plan_hash):
        raise AuthorizationError("scope_plan_hash_mismatch", "scope is bound to a different plan")

    recomputed = _scope_canonical(
        {
            "scope_version": scope.scope_version,
            "source_plan_hash": scope.source_plan_hash,
            "derivation_rule": scope.derivation_rule,
            "completed_request_ids": scope.completed_request_ids,
            "completed_request_hashes": scope.completed_request_hashes,
            "remaining_request_ids": scope.remaining_request_ids,
            "remaining_request_hashes": scope.remaining_request_hashes,
        }
    )
    if not hmac.compare_digest(recomputed, scope.scope_hash):
        raise AuthorizationError("scope_hash_mismatch", "scope_hash does not match the payload")

    if len(scope.remaining_request_ids) != 24:
        raise AuthorizationError(
            "scope_request_count",
            f"remaining scope must contain exactly 24 requests, got "
            f"{len(scope.remaining_request_ids)}",
        )
    if len(set(scope.remaining_request_hashes)) != len(scope.remaining_request_hashes):
        raise AuthorizationError(
            "scope_duplicate_hash", "remaining request hashes contain a duplicate"
        )
    if set(scope.remaining_request_hashes) & set(scope.completed_request_hashes):
        raise AuthorizationError(
            "scope_completed_included", "a completed request hash appears in the remaining scope"
        )

    canonical_pairs = {(item.request_id, item.request_hash) for item in canonical_requests}
    for request_id, request_hash in zip(
        scope.remaining_request_ids, scope.remaining_request_hashes, strict=True
    ):
        if (request_id, request_hash) not in canonical_pairs:
            raise AuthorizationError(
                "scope_unknown_request",
                f"scoped request is not in the canonical plan: {request_id}",
            )
    for request_id, request_hash in zip(
        scope.completed_request_ids, scope.completed_request_hashes, strict=True
    ):
        if (request_id, request_hash) not in canonical_pairs:
            raise AuthorizationError(
                "scope_unknown_completed",
                f"completed request is not in the canonical plan: {request_id}",
            )


# ── Evidence reference ───────────────────────────────────────────────


class EvidenceReference(BaseModel):
    """Immutable reference to an external evidence artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_type: str
    evidence_sha256: str
    observed_at: datetime
    expires_at: datetime

    @field_validator("observed_at", "expires_at")
    @classmethod
    def _require_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        return value


# ── Authorization model ──────────────────────────────────────────────


class PilotAuthorization(BaseModel):
    """A signed, single-use authorization to spend real money on the pilot purchase.

    v1 / legacy:
        Parsed for audit but rejected during ``validate_authorization``.

    v2 (``authorization_version == "2.0"``):
        Requires ``remaining_scope_hash``, ``cost_evidence``,
        ``portal_evidence``, and ``portal_source_evidence_sha256``.
        Validation enforces per-request scoping, evidence hash binding,
        evidence freshness, portal source provenance, and bounded
        authorization expiry.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_version: str
    pilot_plan_hash: str
    source_manifest_hash: str
    split_manifest_hash: str
    acquisition_policy_hash: str
    maximum_spend_usd: Decimal = Field(le=Decimal("5.00"))
    maximum_single_request_usd: Decimal = Field(le=Decimal("1.00"))
    authorized_currency: str
    authorized_at: datetime
    expires_at: datetime
    authorized_by: str
    confirmation_phrase: str
    purchase_authorized: bool
    authorization_hash: str

    # v2 fields
    remaining_scope_hash: str | None = None
    cost_evidence: EvidenceReference | None = None
    portal_evidence: EvidenceReference | None = None
    portal_source_evidence_sha256: str | None = None

    @field_validator("maximum_spend_usd", "maximum_single_request_usd", mode="before")
    @classmethod
    def _coerce_maximum_spend(cls, value: Any) -> Decimal:
        return to_decimal(value)

    @field_validator("authorized_at", "expires_at")
    @classmethod
    def _require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _validate_version(self) -> PilotAuthorization:
        if self.authorization_version not in _SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported authorization_version: {self.authorization_version}")
        return self


def compute_authorization_hash(auth_payload_without_hash: dict[str, Any]) -> str:
    """Return the SHA-256 hash of an authorization payload's canonical JSON."""
    reduced = {k: v for k, v in auth_payload_without_hash.items() if k not in _HASH_EXCLUDED}
    for field in ("maximum_spend_usd", "maximum_single_request_usd"):
        if field in reduced:
            reduced[field] = str(to_decimal(reduced[field]))
    for field in ("authorized_at", "expires_at"):
        value = reduced.get(field)
        if value is not None:
            timestamp = (
                value
                if isinstance(value, datetime)
                else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            )
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("authorization timestamps must be timezone-aware")
            reduced[field] = timestamp.astimezone(UTC).isoformat()
    for field in ("cost_evidence", "portal_evidence"):
        evidence = reduced.get(field)
        if isinstance(evidence, dict):
            evidence = dict(evidence)
            for ts_field in ("observed_at", "expires_at"):
                ts_val = evidence.get(ts_field)
                if isinstance(ts_val, datetime):
                    evidence[ts_field] = ts_val.astimezone(UTC).isoformat()
                elif isinstance(ts_val, str):
                    evidence[ts_field] = (
                        datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                        .astimezone(UTC)
                        .isoformat()
                    )
            reduced[field] = evidence
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def load_authorization(path: Path) -> PilotAuthorization:
    """Parse and schema-validate a pilot authorization artifact from disk.

    Accepts any supported version for audit.  Callers must still call
    ``validate_authorization`` before treating it as executable.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    repo_root = find_repository_root()
    schema = json.loads((repo_root / _SCHEMA_RELATIVE_PATH).read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)
    return PilotAuthorization.model_validate(payload)


# ── Execution validation ─────────────────────────────────────────────


def validate_authorization(
    auth: PilotAuthorization,
    *,
    expected_plan_hash: str,
    expected_source_manifest_hash: str,
    expected_split_manifest_hash: str,
    expected_acquisition_policy_hash: str,
    expected_scope: RemainingRequestScope,
    expected_cost_evidence_sha256: str,
    expected_portal_evidence_sha256: str,
    expected_portal_source_evidence_sha256: str,
    now: datetime,
    consumed_ids: set[str],  # authorization hashes, or plan hashes for legacy records
    expected_maximum_spend_usd: Decimal = Decimal("5.00"),
    expected_maximum_single_request_usd: Decimal = Decimal("1.00"),
) -> None:
    """Validate a parsed authorization for acquisition execution, or raise.

    Rejects v1 and legacy artifacts unconditionally.  All v2 scope and
    evidence context is mandatory — no parameter may be omitted.

    Raises:
        AuthorizationError: With ``.reason`` set to the first rejection reason.
    """
    # ── hash tampering ──────────────────────────────────────────────
    payload = _validation_payload(auth)
    fresh_hash = compute_authorization_hash(payload)
    if not hmac.compare_digest(fresh_hash, auth.authorization_hash):
        raise AuthorizationError("hash_tampered", "authorization_hash does not match payload")

    # ── plan & manifest ─────────────────────────────────────────────
    if not hmac.compare_digest(auth.pilot_plan_hash, expected_plan_hash):
        raise AuthorizationError("plan_hash_mismatch", "pilot_plan_hash does not match plan")
    if (
        not hmac.compare_digest(auth.source_manifest_hash, expected_source_manifest_hash)
        or not hmac.compare_digest(auth.split_manifest_hash, expected_split_manifest_hash)
        or not hmac.compare_digest(auth.acquisition_policy_hash, expected_acquisition_policy_hash)
    ):
        raise AuthorizationError(
            "manifest_hash_mismatch", "a source/split/policy manifest hash does not match"
        )

    # ── version gate ────────────────────────────────────────────────
    if auth.authorization_version not in _SUPPORTED_VERSIONS:
        raise AuthorizationError(
            "unsupported_version", f"unknown authorization_version: {auth.authorization_version}"
        )
    if auth.authorization_version != _EXECUTABLE_VERSION:
        raise AuthorizationError(
            "authorization_version_not_executable",
            f"only version {_EXECUTABLE_VERSION} is executable, got {auth.authorization_version}",
        )

    # ── scope ───────────────────────────────────────────────────────
    if auth.remaining_scope_hash is None:
        raise AuthorizationError("scope_missing", "authorization missing remaining_scope_hash")
    if not hmac.compare_digest(auth.remaining_scope_hash, expected_scope.scope_hash):
        raise AuthorizationError(
            "scope_hash_mismatch", "remaining_scope_hash does not match expected scope"
        )
    if len(expected_scope.remaining_request_ids) != 24:
        raise AuthorizationError(
            "scope_remaining_count_mismatch",
            f"expected 24 remaining requests, got {len(expected_scope.remaining_request_ids)}",
        )
    if expected_scope.duplicate_count != 0:
        raise AuthorizationError("scope_has_duplicates", "scope contains duplicate request IDs")
    if expected_scope.overlap_count != 0:
        raise AuthorizationError(
            "scope_has_overlap", "scope has overlap between completed and remaining"
        )

    # ── cost evidence ───────────────────────────────────────────────
    if auth.cost_evidence is None:
        raise AuthorizationError("cost_evidence_missing", "authorization missing cost_evidence")
    if not hmac.compare_digest(auth.cost_evidence.evidence_sha256, expected_cost_evidence_sha256):
        raise AuthorizationError(
            "cost_evidence_hash_mismatch", "cost evidence sha256 does not match expected"
        )
    if now >= auth.cost_evidence.expires_at:
        raise AuthorizationError("cost_evidence_stale", "cost evidence has expired")

    # ── portal evidence ─────────────────────────────────────────────
    if auth.portal_evidence is None:
        raise AuthorizationError("portal_evidence_missing", "authorization missing portal_evidence")
    if not hmac.compare_digest(
        auth.portal_evidence.evidence_sha256, expected_portal_evidence_sha256
    ):
        raise AuthorizationError(
            "portal_evidence_hash_mismatch", "portal evidence sha256 does not match expected"
        )
    if now >= auth.portal_evidence.expires_at:
        raise AuthorizationError("portal_evidence_stale", "portal evidence has expired")

    # ── portal source provenance ────────────────────────────────────
    if auth.portal_source_evidence_sha256 is None:
        raise AuthorizationError(
            "portal_source_evidence_missing",
            "authorization missing portal_source_evidence_sha256",
        )
    if not _is_valid_sha256(auth.portal_source_evidence_sha256):
        raise AuthorizationError(
            "portal_source_evidence_sha256_malformed",
            "portal_source_evidence_sha256 must be 64 lowercase hex",
        )
    if not hmac.compare_digest(
        auth.portal_source_evidence_sha256, expected_portal_source_evidence_sha256
    ):
        raise AuthorizationError(
            "portal_source_evidence_hash_mismatch",
            "portal source evidence sha256 does not match expected",
        )

    # ── effective expiry ────────────────────────────────────────────
    evidence_expiry = min(auth.cost_evidence.expires_at, auth.portal_evidence.expires_at)
    if auth.expires_at > evidence_expiry:
        raise AuthorizationError(
            "authorization_expiry_exceeds_evidence",
            f"authorization expires {auth.expires_at.isoformat()} "
            f"but evidence expires {evidence_expiry.isoformat()}",
        )

    # ── timestamp validity ──────────────────────────────────────────
    if auth.expires_at <= auth.authorized_at:
        raise AuthorizationError(
            "invalid_validity_interval", "expires_at must be after authorized_at"
        )
    if now < auth.authorized_at:
        raise AuthorizationError("not_yet_valid", "authorization is not yet valid")
    if now >= auth.expires_at:
        raise AuthorizationError("expired", "authorization has expired")

    # ── single-use ──────────────────────────────────────────────────
    # Identity is the authorization hash, so two distinct authorizations for
    # the same plan do not conflate; a plan hash still matches for legacy
    # consumption records that carry no usable authorization identity.
    if auth.authorization_hash in consumed_ids or auth.pilot_plan_hash in consumed_ids:
        raise AuthorizationError("already_consumed", "authorization already consumed")

    # ── spend caps ──────────────────────────────────────────────────
    # The authorizer may delegate less than the plan allows: a $0.50 ceiling
    # under a $5.00 plan authorizes $0.50, never $5.00. The per-request cap is
    # a plan invariant and must still match exactly.
    if auth.maximum_spend_usd <= Decimal(0):
        raise AuthorizationError(
            "authorization_ceiling_not_positive", "maximum_spend_usd must be greater than zero"
        )
    if auth.maximum_spend_usd > expected_maximum_spend_usd:
        raise AuthorizationError(
            "authorization_ceiling_above_plan",
            "maximum_spend_usd exceeds the plan maximum",
        )
    if auth.maximum_single_request_usd != expected_maximum_single_request_usd:
        raise AuthorizationError("spend_cap_mismatch", "authorization spend caps do not match plan")

    # ── currency ────────────────────────────────────────────────────
    if not hmac.compare_digest(auth.authorized_currency, "USD"):
        raise AuthorizationError("currency_mismatch", "authorized_currency must be USD")

    # ── confirmation phrase ─────────────────────────────────────────
    if not hmac.compare_digest(auth.confirmation_phrase, CONFIRMATION_PHRASE):
        raise AuthorizationError(
            "confirmation_phrase_mismatch", "confirmation_phrase does not match"
        )

    # ── purchase authorized ─────────────────────────────────────────
    if auth.purchase_authorized is not True:
        raise AuthorizationError("purchase_not_authorized", "purchase_authorized is not True")


# ── helpers ──────────────────────────────────────────────────────────


def _is_valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validation_payload(auth: PilotAuthorization) -> dict[str, object]:
    """Rebuild the canonical payload for hash comparison."""
    payload: dict[str, object] = {
        "authorization_version": auth.authorization_version,
        "pilot_plan_hash": auth.pilot_plan_hash,
        "source_manifest_hash": auth.source_manifest_hash,
        "split_manifest_hash": auth.split_manifest_hash,
        "acquisition_policy_hash": auth.acquisition_policy_hash,
        "maximum_spend_usd": str(auth.maximum_spend_usd),
        "maximum_single_request_usd": str(auth.maximum_single_request_usd),
        "authorized_currency": auth.authorized_currency,
        "authorized_at": auth.authorized_at.isoformat(),
        "expires_at": auth.expires_at.isoformat(),
        "authorized_by": auth.authorized_by,
        "confirmation_phrase": auth.confirmation_phrase,
        "purchase_authorized": auth.purchase_authorized,
    }
    if auth.authorization_version == _V2:
        payload["remaining_scope_hash"] = auth.remaining_scope_hash
        if auth.cost_evidence is not None:
            payload["cost_evidence"] = {
                "evidence_type": auth.cost_evidence.evidence_type,
                "evidence_sha256": auth.cost_evidence.evidence_sha256,
                "observed_at": auth.cost_evidence.observed_at.isoformat(),
                "expires_at": auth.cost_evidence.expires_at.isoformat(),
            }
        if auth.portal_evidence is not None:
            payload["portal_evidence"] = {
                "evidence_type": auth.portal_evidence.evidence_type,
                "evidence_sha256": auth.portal_evidence.evidence_sha256,
                "observed_at": auth.portal_evidence.observed_at.isoformat(),
                "expires_at": auth.portal_evidence.expires_at.isoformat(),
            }
        if auth.portal_source_evidence_sha256 is not None:
            payload["portal_source_evidence_sha256"] = auth.portal_source_evidence_sha256
    return payload
