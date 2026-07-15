"""Fail-closed usage-based cost estimation with a conservative derived fallback.

This module implements levels 1 and 2 of the acquisition cost hierarchy:

1. Databento ``metadata.get_cost`` (the authoritative provider quote).
2. A derived estimate from ``metadata.get_billable_size`` and
   ``metadata.list_unit_prices`` when, and only when, ``get_cost`` fails for a
   bounded provider-side ``5xx`` or a gateway/network timeout.

Levels 3 (operator-attested portal quote) and 4 (block execution) are modelled
by the :class:`CostSource` enum but are not implemented here.

Every monetary value is a :class:`decimal.Decimal`. Binary floating point is
never used for a price, a size product, a tolerance comparison, or a hash
input. Rounding happens only at presentation, never for a policy check.

The derived fallback is fail-closed: a derived estimate can only be built by
:func:`build_derived_estimate`, which requires (a) a fallback-eligible terminal
failure, (b) a hash-valid billable size for the exact request, (c) a fresh,
non-expired unit-price snapshot for the exact dataset/feed-mode/schema, and
(d) a passing cross-validation result. Any missing or mismatched input raises
:class:`~neuralmarket.data.errors.CostEstimationError` rather than returning a
usable number.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from neuralmarket.data.errors import (
    AuthenticationError,
    CostEstimationError,
    EntitlementError,
    ProviderNetworkError,
    RateLimitError,
)

# --- Constants ---------------------------------------------------------------

#: Exact binary gibibyte used by Databento billing. Never 1e9.
BYTES_PER_BILLING_GIB = 1_073_741_824

#: Version stamp bound into every derived estimate and cross-validation.
CALCULATION_VERSION = "derived-cost-v1"

#: Conservative safety margin applied to every derived estimate for gates.
CONSERVATIVE_MARGIN = Decimal("1.25")

#: Feed mode bound to the planned paid path. The successful reference
#: ``get_cost`` (SDK default mode ``historical-streaming``, the same streaming
#: path ``timeseries.get_range`` uses) reproduces exactly at 2.0 USD/GiB, so the
#: derived fallback must price against the ``historical-streaming`` unit price,
#: never the cheaper ``historical`` batch mode (batch submission is unauthorized).
ACQUISITION_FEED_MODE = "historical-streaming"

#: Cross-validation tolerances (Decimal, never float).
CROSS_VALIDATION_ABS_TOLERANCE = Decimal("1e-9")
CROSS_VALIDATION_REL_TOLERANCE = Decimal("1e-6")

#: Terminal ``get_cost`` failures that may license a derived fallback.
_FALLBACK_ELIGIBLE_STATUSES = frozenset({500, 502, 503, 504})
_FALLBACK_ELIGIBLE_CATEGORIES = frozenset(
    {"provider_timeout", "provider_network_timeout", "network_timeout"}
)


class CostSource(Enum):
    """Provenance of a single usage-based cost estimate, highest trust first."""

    PROVIDER_GET_COST = "provider_get_cost"
    DERIVED_BILLABLE_SIZE_UNIT_PRICE = "derived_billable_size_unit_price"
    PORTAL_ATTESTED_QUOTE = "portal_attested_quote"
    UNAVAILABLE = "unavailable"


class CrossValidationStatus(Enum):
    """Whether the derived method has been validated against a provider quote."""

    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


# --- Canonical hashing -------------------------------------------------------


def canonical_hash(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 of a canonical JSON encoding of ``payload``.

    Keys are sorted and separators are fixed so the digest is stable across
    processes. ``Decimal`` values are encoded as their exact string form.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --- Formula -----------------------------------------------------------------


def derive_cost(billable_size_bytes: int, unit_price_usd_per_gib: Decimal) -> Decimal:
    """Return the exact derived cost in USD, full precision preserved.

    ``derived = billable_size_bytes * unit_price_usd_per_gib / 2**30``
    """
    if isinstance(billable_size_bytes, bool):
        raise CostEstimationError("billable_size_bytes must be an integer, not a bool")
    if billable_size_bytes < 0:
        raise CostEstimationError(
            f"billable_size_bytes must be non-negative: {billable_size_bytes}"
        )
    if not isinstance(unit_price_usd_per_gib, Decimal):
        raise CostEstimationError("unit_price_usd_per_gib must be a Decimal")
    return Decimal(billable_size_bytes) * unit_price_usd_per_gib / Decimal(BYTES_PER_BILLING_GIB)


def conservative_cost(raw_derived_usd: Decimal) -> Decimal:
    """Return the conservative estimate: ``max(raw, raw * 1.25)`` (i.e. raw*1.25)."""
    return max(raw_derived_usd, raw_derived_usd * CONSERVATIVE_MARGIN)


# --- Fallback eligibility ----------------------------------------------------


def fallback_permitted(*, http_status: int | None, failure_category: str | None) -> bool:
    """Return whether a terminal ``get_cost`` failure may license a fallback.

    Fail-closed: only a bounded ``5xx`` (500/502/503/504) or a provider/network
    timeout returns ``True``. Every other condition -- 4xx, entitlement,
    authentication, rate limiting, invalid request -- returns ``False``.
    """
    if http_status in _FALLBACK_ELIGIBLE_STATUSES:
        return True
    return failure_category in _FALLBACK_ELIGIBLE_CATEGORIES


def classify_exception(exc: Exception) -> tuple[int | None, str | None]:
    """Extract ``(http_status, failure_category)`` from a domain/vendor error.

    Only used to feed :func:`fallback_permitted`. Authentication, entitlement,
    and rate-limit errors deliberately yield a non-eligible category.
    """
    status_attr = getattr(exc, "http_status", None)
    http_status: int | None
    try:
        http_status = int(status_attr) if status_attr is not None else None
    except (TypeError, ValueError):
        http_status = None
    if isinstance(exc, AuthenticationError):
        return http_status, "authentication"
    if isinstance(exc, EntitlementError):
        return http_status, "entitlement"
    if isinstance(exc, RateLimitError):
        return http_status, "rate_limit"
    if isinstance(exc, ProviderNetworkError):
        return http_status, "provider_network_timeout"
    return http_status, None


# --- Unit-price snapshot -----------------------------------------------------


def _parse_positive_price(value: object, *, schema: str) -> Decimal:
    if isinstance(value, bool):
        raise CostEstimationError(f"unit price for {schema!r} must not be a bool")
    if isinstance(value, float):
        raise CostEstimationError(
            f"unit price for {schema!r} must be a decimal string, not a binary float"
        )
    try:
        price = Decimal(str(value))
    except Exception as exc:
        raise CostEstimationError(f"unit price for {schema!r} is not decimal: {value!r}") from exc
    if not price.is_finite():
        raise CostEstimationError(f"unit price for {schema!r} is nonfinite: {price}")
    if price <= 0:
        raise CostEstimationError(f"unit price for {schema!r} must be positive: {price}")
    return price


@dataclass(frozen=True)
class UnitPriceSnapshot:
    """A fresh, hash-bound unit-price snapshot for one dataset and feed mode.

    The sanitized ``list_unit_prices`` response is a sequence of per-mode blocks
    ``[{"mode": <str>, "schemas": {<schema>: <usd_per_gib>}}, ...]``. Exactly one
    block must match the requested feed mode; a missing block, a duplicate mode,
    or a missing/invalid schema price fails closed.
    """

    dataset: str
    feed_mode: str
    databento_client_version: str
    retrieved_at_utc: str
    expires_at_utc: str
    schema_prices: Mapping[str, str]
    snapshot_hash: str

    def price_for(self, schema: str) -> Decimal:
        """Return the unit price (USD/GiB) for ``schema`` or fail closed."""
        if schema not in self.schema_prices:
            raise CostEstimationError(
                f"no {self.feed_mode!r} unit price for schema {schema!r} in snapshot"
            )
        return Decimal(self.schema_prices[schema])

    def is_expired(self, now_utc: datetime) -> bool:
        """Return whether the snapshot has expired at ``now_utc``."""
        return now_utc >= datetime.fromisoformat(self.expires_at_utc)


def parse_unit_price_snapshot(
    response: Sequence[Mapping[str, Any]],
    *,
    dataset: str,
    feed_mode: str,
    databento_client_version: str,
    retrieved_at_utc: str,
    expires_at_utc: str,
) -> UnitPriceSnapshot:
    """Validate a sanitized ``list_unit_prices`` response into a snapshot."""
    matching = [block for block in response if block.get("mode") == feed_mode]
    if not matching:
        raise CostEstimationError(f"unit-price response has no {feed_mode!r} feed mode")
    if len(matching) > 1:
        raise CostEstimationError(f"unit-price response has duplicate {feed_mode!r} feed mode")
    raw_schemas = matching[0].get("schemas")
    if not isinstance(raw_schemas, Mapping) or not raw_schemas:
        raise CostEstimationError(f"unit-price {feed_mode!r} block has no schemas")
    prices: dict[str, str] = {
        str(schema): str(_parse_positive_price(price, schema=str(schema)))
        for schema, price in raw_schemas.items()
    }
    snapshot_hash = canonical_hash(
        {
            "dataset": dataset,
            "feed_mode": feed_mode,
            "databento_client_version": databento_client_version,
            "retrieved_at_utc": retrieved_at_utc,
            "expires_at_utc": expires_at_utc,
            "schema_prices": prices,
            "calculation_version": CALCULATION_VERSION,
        }
    )
    return UnitPriceSnapshot(
        dataset=dataset,
        feed_mode=feed_mode,
        databento_client_version=databento_client_version,
        retrieved_at_utc=retrieved_at_utc,
        expires_at_utc=expires_at_utc,
        schema_prices=prices,
        snapshot_hash=snapshot_hash,
    )


# --- Cross-validation --------------------------------------------------------


@dataclass(frozen=True)
class ProviderCostSample:
    """A successful ``get_cost`` result used to validate the derived method."""

    dataset: str
    schema: str
    feed_mode: str
    account_pricing_context: str
    billable_size_bytes: int
    provider_cost_usd: Decimal


@dataclass(frozen=True)
class CrossValidationResult:
    """Outcome of validating the derived method against provider quotes."""

    dataset: str
    schema: str
    feed_mode: str
    account_pricing_context: str
    calculation_version: str
    sample_count: int
    maximum_absolute_error: Decimal
    maximum_relative_error: Decimal
    passed: bool
    evidence_hash: str

    @property
    def status(self) -> CrossValidationStatus:
        """Return the derived-method status implied by the sample outcome."""
        if self.sample_count == 0:
            return CrossValidationStatus.UNAVAILABLE
        return CrossValidationStatus.PASSED if self.passed else CrossValidationStatus.FAILED


def cross_validate(
    snapshot: UnitPriceSnapshot,
    *,
    dataset: str,
    schema: str,
    feed_mode: str,
    account_pricing_context: str,
    samples: Sequence[ProviderCostSample],
) -> CrossValidationResult:
    """Validate the derived formula against compatible successful provider quotes.

    Only samples matching the exact dataset, schema, and feed mode are used.
    Passing requires at least one compatible sample and every compatible sample
    within both the absolute and relative tolerance. Fail-closed on no samples.
    """
    if snapshot.dataset != dataset or snapshot.feed_mode != feed_mode:
        raise CostEstimationError("snapshot does not match the cross-validation dataset/mode")
    unit_price = snapshot.price_for(schema)
    compatible = [
        s
        for s in samples
        if s.dataset == dataset
        and s.schema == schema
        and s.feed_mode == feed_mode
        and s.account_pricing_context == account_pricing_context
    ]
    max_abs = Decimal(0)
    max_rel = Decimal(0)
    all_ok = True
    evidence: list[dict[str, str]] = []
    for sample in compatible:
        derived = derive_cost(sample.billable_size_bytes, unit_price)
        abs_err = abs(derived - sample.provider_cost_usd)
        rel_err = (
            abs_err / abs(sample.provider_cost_usd) if sample.provider_cost_usd != 0 else abs_err
        )
        max_abs = max(max_abs, abs_err)
        max_rel = max(max_rel, rel_err)
        if abs_err > CROSS_VALIDATION_ABS_TOLERANCE or rel_err > CROSS_VALIDATION_REL_TOLERANCE:
            all_ok = False
        evidence.append(
            {
                "billable_size_bytes": str(sample.billable_size_bytes),
                "provider_cost_usd": str(sample.provider_cost_usd),
                "derived_cost_usd": str(derived),
                "absolute_error": str(abs_err),
                "relative_error": str(rel_err),
            }
        )
    passed = bool(compatible) and all_ok
    evidence_hash = canonical_hash(
        {
            "dataset": dataset,
            "schema": schema,
            "feed_mode": feed_mode,
            "account_pricing_context": account_pricing_context,
            "calculation_version": CALCULATION_VERSION,
            "unit_price_snapshot_hash": snapshot.snapshot_hash,
            "samples": evidence,
        }
    )
    return CrossValidationResult(
        dataset=dataset,
        schema=schema,
        feed_mode=feed_mode,
        account_pricing_context=account_pricing_context,
        calculation_version=CALCULATION_VERSION,
        sample_count=len(compatible),
        maximum_absolute_error=max_abs,
        maximum_relative_error=max_rel,
        passed=passed,
        evidence_hash=evidence_hash,
    )


# --- Derived estimate --------------------------------------------------------


@dataclass(frozen=True)
class DerivedCostEstimate:
    """An immutable, hash-bound derived cost estimate for one request."""

    request_id: str
    request_specification_hash: str
    dataset: str
    schema: str
    feed_mode: str
    cost_usd: Decimal
    cost_source: CostSource
    billable_size_bytes: int
    unit_price_usd_per_gib: Decimal
    unit_price_snapshot_hash: str
    billable_size_response_hash: str
    cross_validation_evidence_hash: str
    calculation_version: str
    calculated_at: str
    cross_validation_status: CrossValidationStatus
    conservative_cost_usd: Decimal
    provider_cost_usd: Decimal | None = None
    estimate_hash: str = field(default="")

    def provenance_hash(self) -> str:
        """Recompute the binding hash over every provenance input."""
        return canonical_hash(
            {
                "request_specification_hash": self.request_specification_hash,
                "billable_size_response_hash": self.billable_size_response_hash,
                "unit_price_snapshot_hash": self.unit_price_snapshot_hash,
                "cross_validation_evidence_hash": self.cross_validation_evidence_hash,
                "calculation_version": self.calculation_version,
                "billable_size_bytes": str(self.billable_size_bytes),
                "unit_price_usd_per_gib": str(self.unit_price_usd_per_gib),
                "cost_usd": str(self.cost_usd),
            }
        )


def build_derived_estimate(
    *,
    request_id: str,
    request_specification_hash: str,
    dataset: str,
    schema: str,
    feed_mode: str,
    billable_size_bytes: int,
    billable_size_response_hash: str,
    snapshot: UnitPriceSnapshot,
    cross_validation: CrossValidationResult,
    failure_http_status: int | None,
    failure_category: str | None,
    calculated_at: str,
) -> DerivedCostEstimate:
    """Build a derived estimate, fail-closed on any unmet precondition.

    Preconditions (all required): fallback-eligible terminal failure, a fresh
    unit-price snapshot for the exact dataset/feed-mode/schema, and a passing
    cross-validation result for the same context.
    """
    if feed_mode != ACQUISITION_FEED_MODE:
        raise CostEstimationError(
            f"derived fallback is bound to {ACQUISITION_FEED_MODE!r}, not {feed_mode!r}"
        )
    if not fallback_permitted(http_status=failure_http_status, failure_category=failure_category):
        raise CostEstimationError(
            "derived fallback is not permitted for this terminal failure "
            f"(http_status={failure_http_status}, category={failure_category})"
        )
    if snapshot.dataset != dataset or snapshot.feed_mode != feed_mode:
        raise CostEstimationError("unit-price snapshot does not match the request")
    if not (
        cross_validation.passed
        and cross_validation.dataset == dataset
        and cross_validation.schema == schema
        and cross_validation.feed_mode == feed_mode
        and cross_validation.calculation_version == CALCULATION_VERSION
    ):
        raise CostEstimationError("cross-validation did not pass for this request context")

    unit_price = snapshot.price_for(schema)
    raw = derive_cost(billable_size_bytes, unit_price)
    estimate = DerivedCostEstimate(
        request_id=request_id,
        request_specification_hash=request_specification_hash,
        dataset=dataset,
        schema=schema,
        feed_mode=feed_mode,
        cost_usd=raw,
        cost_source=CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE,
        billable_size_bytes=billable_size_bytes,
        unit_price_usd_per_gib=unit_price,
        unit_price_snapshot_hash=snapshot.snapshot_hash,
        billable_size_response_hash=billable_size_response_hash,
        cross_validation_evidence_hash=cross_validation.evidence_hash,
        calculation_version=CALCULATION_VERSION,
        calculated_at=calculated_at,
        cross_validation_status=cross_validation.status,
        conservative_cost_usd=conservative_cost(raw),
        provider_cost_usd=None,
    )
    binding = estimate.provenance_hash()
    return DerivedCostEstimate(**{**estimate.__dict__, "estimate_hash": binding})


# --- Plan-level rollup -------------------------------------------------------

#: Conservative authorization limits (unchanged spending gates).
CONSERVATIVE_PLAN_TOTAL_CAP_USD = Decimal("5.00")
CONSERVATIVE_PER_REQUEST_CAP_USD = Decimal("1.00")
#: Wider drift ceiling for the conservative total only (each request carries 25%).
CONSERVATIVE_DRIFT_CEILING = Decimal("1.50")


@dataclass(frozen=True)
class PlanCostEntry:
    """One request's contribution to the plan-level cost summary."""

    request_id: str
    cost_source: CostSource
    raw_cost_usd: Decimal
    conservative_cost_usd: Decimal


@dataclass(frozen=True)
class PlanCostSummary:
    """Aggregate cost accounting across a metadata preflight plan."""

    provider_cost_count: int
    derived_cost_count: int
    portal_cost_count: int
    unavailable_cost_count: int
    raw_total_usd: Decimal
    conservative_total_usd: Decimal
    largest_raw_request_usd: Decimal
    largest_conservative_request_usd: Decimal
    within_total_cap: bool
    within_per_request_cap: bool
    within_drift_ceiling: bool

    @property
    def within_all_gates(self) -> bool:
        """Return whether every conservative spending gate is satisfied."""
        return self.within_total_cap and self.within_per_request_cap and self.within_drift_ceiling


def summarize_plan(
    entries: Sequence[PlanCostEntry], *, tracked_total_usd: Decimal
) -> PlanCostSummary:
    """Roll up per-request entries and evaluate the conservative spending gates."""
    raw_total = sum((e.raw_cost_usd for e in entries), Decimal(0))
    conservative_total = sum((e.conservative_cost_usd for e in entries), Decimal(0))
    largest_raw = max((e.raw_cost_usd for e in entries), default=Decimal(0))
    largest_conservative = max((e.conservative_cost_usd for e in entries), default=Decimal(0))
    drift_ceiling = tracked_total_usd * CONSERVATIVE_DRIFT_CEILING
    return PlanCostSummary(
        provider_cost_count=sum(e.cost_source is CostSource.PROVIDER_GET_COST for e in entries),
        derived_cost_count=sum(
            e.cost_source is CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE for e in entries
        ),
        portal_cost_count=sum(e.cost_source is CostSource.PORTAL_ATTESTED_QUOTE for e in entries),
        unavailable_cost_count=sum(e.cost_source is CostSource.UNAVAILABLE for e in entries),
        raw_total_usd=raw_total,
        conservative_total_usd=conservative_total,
        largest_raw_request_usd=largest_raw,
        largest_conservative_request_usd=largest_conservative,
        within_total_cap=conservative_total <= CONSERVATIVE_PLAN_TOTAL_CAP_USD,
        within_per_request_cap=largest_conservative <= CONSERVATIVE_PER_REQUEST_CAP_USD,
        within_drift_ceiling=conservative_total <= drift_ceiling,
    )
