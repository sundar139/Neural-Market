"""Offline purchase-review gate for the January 2019 pilot acquisition.

This module validates the human purchase decision BEFORE the execution-layer
gates (``authorization.py``/``attestation.py``/the journal-backed executor)
ever run. It binds the decision to the completed metadata checkpoint bytes,
the frozen plan, the repository revision, and exact Decimal cost evidence,
and it fails closed with structured, secret-free rejection reasons. It makes
no purchase decision itself, constructs no provider, and performs no network
operation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import jsonschema

from neuralmarket.core.environment import find_repository_root
from neuralmarket.data.manifests import canonical_dumps

AUTHORIZATION_SCHEMA = "data_contracts/pilot_purchase_authorization.schema.json"
ATTESTATION_SCHEMA = "data_contracts/pilot_portal_attestation.schema.json"

#: Maximum review-authorization validity window (creation to expiry).
AUTHORIZATION_VALIDITY = timedelta(hours=24)
#: Maximum portal cost-attestation validity window (observation to expiry).
ATTESTATION_VALIDITY = timedelta(minutes=30)
#: Frozen project hard caps (mirror the pilot config and execution gates).
HARD_TOTAL_CAP_USD = Decimal("5.00")
HARD_SINGLE_REQUEST_CAP_USD = Decimal("1.00")

#: The exact required authorization statement; ``{amount}`` is the ceiling.
AUTHORIZATION_STATEMENT_TEMPLATE = (
    "I authorize NeuralMarket to execute the bound January 2019 pilot acquisition "
    "with a maximum total charge of USD {amount}. I understand that this permits "
    "paid Databento historical market-data requests only for the hashes and request "
    "scope recorded in this authorization."
)

_HASH_EXCLUDED_AUTH = ("review_hash",)
_HASH_EXCLUDED_ATTEST = ("attestation_hash",)


@dataclass(frozen=True)
class Rejection:
    """One structured, secret-free reason the purchase package is invalid."""

    code: str
    detail: str


@dataclass(frozen=True)
class ExpectedPurchaseBindings:
    """Immutable evidence a valid purchase authorization must bind to."""

    repository_head: str
    plan_hash: str
    completed_checkpoint_sha256: str
    request_manifest_sha256: str
    source_manifest_hash: str
    split_manifest_hash: str
    acquisition_policy_hash: str
    raw_total_usd: Decimal
    conservative_total_usd: Decimal
    maximum_ceiling_usd: Decimal


@dataclass(frozen=True)
class PurchaseReviewResult:
    """Outcome of the offline purchase-package review."""

    ok: bool
    rejections: list[Rejection] = field(default_factory=list)


def compute_review_hash(payload: dict[str, Any]) -> str:
    """Hash canonical authorization-review content, excluding its self-hash."""
    reduced = {k: v for k, v in payload.items() if k not in _HASH_EXCLUDED_AUTH}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def compute_portal_attestation_hash(payload: dict[str, Any]) -> str:
    """Hash canonical attestation content, excluding its self-hash."""
    reduced = {k: v for k, v in payload.items() if k not in _HASH_EXCLUDED_ATTEST}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def _load_schema(relative: str) -> dict[str, Any]:
    root = find_repository_root()
    schema: dict[str, Any] = json.loads((root / relative).read_text(encoding="utf-8"))
    return schema


def load_json_artifact(path: Path, *, schema_relative: str, kind: str) -> dict[str, Any]:
    """Load and schema-validate a review artifact, raising with a stable reason.

    Raises:
        FileNotFoundError: When the artifact is absent (``missing_{kind}``).
        ValueError: When it cannot be parsed or fails its schema
            (``invalid_{kind}``); the message never embeds file content.
    """
    if not path.exists():
        raise FileNotFoundError(f"missing_{kind}: artifact not found at {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        jsonschema.validate(payload, _load_schema(schema_relative))
    except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
        raise ValueError(f"invalid_{kind}: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_{kind}: artifact must be a JSON object")
    return payload


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        return None
    return stamp.astimezone(UTC)


def _journal_conflicts(journal_path: Path, *, plan_hash: str) -> list[Rejection]:
    """Fail closed on journal evidence that a paid execution already ran.

    Rejects when the journal records a consumed authorization for the SAME
    plan hash, any completed/billed paid request, or an unresolved billing
    reconciliation. A journal whose only history is a fully reconciled
    not-billed prior attempt under a different plan hash does not block, but
    callers should surface its presence for review.
    """
    if not journal_path.exists():
        return []
    rejections: list[Rejection] = []
    try:
        con = sqlite3.connect(f"file:{journal_path.as_posix()}?mode=ro", uri=True)
        try:
            cur = con.cursor()
            consumed = cur.execute(
                "SELECT COUNT(*) FROM consumed_authorizations WHERE plan_hash = ?",
                (plan_hash,),
            ).fetchone()[0]
            if consumed:
                rejections.append(
                    Rejection(
                        "paid_journal_conflict",
                        "journal already records a consumed authorization for this plan hash",
                    )
                )
            billed = cur.execute(
                "SELECT COUNT(*) FROM requests WHERE actual_billed_cost_usd IS NOT NULL "
                "OR raw_path IS NOT NULL"
            ).fetchone()[0]
            if billed:
                rejections.append(
                    Rejection(
                        "paid_journal_conflict",
                        "journal records completed or billed paid requests",
                    )
                )
            unresolved = cur.execute(
                "SELECT COUNT(*) FROM billing_reconciliations b "
                "WHERE b.billing_resolution = 'unresolved' AND NOT EXISTS ("
                "  SELECT 1 FROM billing_reconciliations s "
                "  WHERE s.supersedes_reconciliation_hash = b.artifact_hash)"
            ).fetchone()[0]
            if unresolved:
                rejections.append(
                    Rejection(
                        "paid_journal_conflict",
                        "journal holds an unresolved billing reconciliation",
                    )
                )
        finally:
            con.close()
    except sqlite3.Error:
        rejections.append(
            Rejection("paid_journal_conflict", "journal exists but could not be inspected")
        )
    return rejections


def review_purchase_package(
    *,
    authorization: dict[str, Any],
    attestation: dict[str, Any] | None,
    expected: ExpectedPurchaseBindings,
    now: datetime,
    journal_path: Path,
    consumption_marker: Path,
) -> PurchaseReviewResult:
    """Validate the complete purchase package offline, fail-closed.

    Returns every applicable rejection (not only the first) so the operator
    can fix the package in one pass. An empty rejection list means the
    package has reached the final pre-provider gate; actual execution still
    happens only through the journal-backed execution-layer gates.
    """
    r: list[Rejection] = []
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("review time must be timezone-aware")
    now = now.astimezone(UTC)

    # --- Template / decision state ------------------------------------
    if authorization.get("template_only") is not False:
        r.append(Rejection("template_only", "authorization is still the unmodified template"))
    if authorization.get("authorized") is not True:
        r.append(Rejection("not_authorized", "authorized flag is not exactly true"))
    if authorization.get("consumed") is not False:
        r.append(Rejection("already_consumed", "authorization is marked consumed"))
    if consumption_marker.exists():
        r.append(
            Rejection("already_consumed", "a consumption record for this package already exists")
        )

    # --- Tamper evidence ------------------------------------------------
    review_hash = authorization.get("review_hash")
    if not isinstance(review_hash, str) or not hmac.compare_digest(
        compute_review_hash(authorization), review_hash
    ):
        r.append(Rejection("hash_tampered", "review_hash does not match the payload"))

    # --- Immutable evidence bindings -------------------------------------
    bindings = {
        "repository_head_mismatch": ("repository_head", expected.repository_head),
        "plan_hash_mismatch": ("plan_hash", expected.plan_hash),
        "checkpoint_hash_mismatch": (
            "completed_checkpoint_sha256",
            expected.completed_checkpoint_sha256,
        ),
        "request_manifest_mismatch": (
            "request_manifest_sha256",
            expected.request_manifest_sha256,
        ),
        "manifest_hash_mismatch:source": ("source_manifest_hash", expected.source_manifest_hash),
        "manifest_hash_mismatch:split": ("split_manifest_hash", expected.split_manifest_hash),
        "manifest_hash_mismatch:policy": (
            "acquisition_policy_hash",
            expected.acquisition_policy_hash,
        ),
    }
    for code, (fieldname, want) in bindings.items():
        got = authorization.get(fieldname)
        if not isinstance(got, str) or not hmac.compare_digest(got, want):
            r.append(Rejection(code.split(":")[0], f"{fieldname} does not match live evidence"))

    compat = authorization.get("configuration_compatibility")
    if not isinstance(compat, dict) or compat.get("compatible") is not True:
        r.append(
            Rejection("configuration_incompatible", "configuration compatibility is not proven")
        )

    # --- Exact Decimal cost bindings -------------------------------------
    raw_total = _decimal(authorization.get("raw_total_usd"))
    conservative = _decimal(authorization.get("conservative_total_usd"))
    if raw_total != expected.raw_total_usd or conservative != expected.conservative_total_usd:
        r.append(
            Rejection("totals_mismatch", "raw/conservative totals differ from validated evidence")
        )

    ceiling = _decimal(authorization.get("authorized_ceiling_usd"))
    if ceiling is None:
        r.append(Rejection("missing_ceiling", "authorized_ceiling_usd is absent"))
    else:
        if ceiling < expected.conservative_total_usd:
            r.append(
                Rejection(
                    "ceiling_below_conservative",
                    "ceiling is below the conservative expected total",
                )
            )
        if ceiling > expected.maximum_ceiling_usd:
            r.append(
                Rejection(
                    "ceiling_above_drift_limit",
                    "ceiling exceeds the validated maximum drift total",
                )
            )
        if ceiling > HARD_TOTAL_CAP_USD:
            r.append(Rejection("ceiling_above_hard_cap", "ceiling exceeds the project hard cap"))

    # --- Timestamps -------------------------------------------------------
    created = _timestamp(authorization.get("created_at"))
    expires = _timestamp(authorization.get("expires_at"))
    if created is None or expires is None:
        r.append(Rejection("invalid_timestamps", "authorization timestamps are missing/naive"))
    else:
        if created > now:
            r.append(Rejection("future_dated", "authorization is created in the future"))
        if expires <= created:
            r.append(Rejection("invalid_timestamps", "expires_at is not after created_at"))
        elif expires - created > AUTHORIZATION_VALIDITY:
            r.append(Rejection("validity_too_long", "authorization validity exceeds 24 hours"))
        if expires <= now:
            r.append(Rejection("authorization_expired", "authorization has expired"))

    # --- Explicit statement ------------------------------------------------
    operator = authorization.get("authorized_by")
    if not isinstance(operator, str) or not operator.strip():
        r.append(Rejection("missing_operator", "authorized_by operator label is required"))
    statement = authorization.get("authorization_statement")
    expected_statement = (
        AUTHORIZATION_STATEMENT_TEMPLATE.format(amount=str(ceiling))
        if ceiling is not None
        else None
    )
    if (
        not isinstance(statement, str)
        or expected_statement is None
        or not hmac.compare_digest(statement.strip(), expected_statement)
    ):
        r.append(
            Rejection(
                "ambiguous_or_missing_statement",
                "authorization statement must exactly match the required wording with the "
                "ceiling amount",
            )
        )

    # --- Portal attestation --------------------------------------------------
    if attestation is None:
        r.append(Rejection("missing_attestation", "portal cost attestation is absent"))
    else:
        if attestation.get("template_only") is not False:
            r.append(Rejection("template_only", "attestation is still the unmodified template"))
        if attestation.get("attested") is not True:
            r.append(Rejection("not_attested", "attested flag is not exactly true"))
        att_hash = attestation.get("attestation_hash")
        if not isinstance(att_hash, str) or not hmac.compare_digest(
            compute_portal_attestation_hash(attestation), att_hash
        ):
            r.append(Rejection("hash_tampered", "attestation_hash does not match the payload"))
        # Explicit three-way repository binding: attestation must match the
        # expected review context AND the purchase authorization. (Authorization
        # vs expected is already checked in the immutable-bindings loop above.)
        att_head = attestation.get("repository_head")
        auth_head = authorization.get("repository_head")
        if not isinstance(att_head, str) or not hmac.compare_digest(
            att_head, expected.repository_head
        ):
            r.append(
                Rejection(
                    "repository_head_mismatch",
                    "attestation repository_head does not match the expected review context",
                )
            )
        elif isinstance(auth_head, str) and not hmac.compare_digest(att_head, auth_head):
            r.append(
                Rejection(
                    "repository_head_mismatch",
                    "attestation and authorization repository_head disagree",
                )
            )
        for fieldname, want, code in (
            (
                "completed_checkpoint_sha256",
                expected.completed_checkpoint_sha256,
                "checkpoint_hash_mismatch",
            ),
            (
                "request_manifest_sha256",
                expected.request_manifest_sha256,
                "request_manifest_mismatch",
            ),
        ):
            got = attestation.get(fieldname)
            if not isinstance(got, str) or not hmac.compare_digest(got, want):
                r.append(Rejection(code, f"attestation {fieldname} does not match live evidence"))
        if _decimal(attestation.get("portal_estimate_usd")) is None:
            r.append(
                Rejection("missing_portal_estimate", "portal-displayed estimate is not recorded")
            )
        if not isinstance(attestation.get("operator_confirmation"), str):
            r.append(
                Rejection("missing_operator_confirmation", "operator confirmation is not recorded")
            )
        observed = _timestamp(attestation.get("observed_at"))
        att_expires = _timestamp(attestation.get("expires_at"))
        if observed is None or att_expires is None:
            r.append(Rejection("invalid_timestamps", "attestation timestamps are missing/naive"))
        else:
            if observed > now:
                r.append(Rejection("future_dated", "attestation is observed in the future"))
            if att_expires <= now:
                r.append(Rejection("attestation_expired", "portal attestation has expired"))
            if att_expires > observed + ATTESTATION_VALIDITY:
                r.append(Rejection("validity_too_long", "attestation validity exceeds 30 minutes"))

    # --- Prior paid activity ----------------------------------------------
    r.extend(_journal_conflicts(journal_path, plan_hash=expected.plan_hash))

    return PurchaseReviewResult(ok=not r, rejections=r)
