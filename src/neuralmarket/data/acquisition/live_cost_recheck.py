"""Reusable, fail-closed fresh provider cost-recheck gate.

Obtains a fresh ``metadata.get_cost`` quote for the *exact* frozen January 2019
pilot requests and compares it against the completed preflight totals and the
project spending gates. The frozen request plan is the sole source of quoted
combinations: this gate never forms a dataset x schema cross product, never
broadens scope, and always uses each request's recorded ``stype_in`` (parent
symbology for ``SPY.OPT``). Every quote is a direct provider response; a failed
quote is reported as unavailable and never back-filled from the earlier derived
unit-price fallback.

The service is pure: it constructs no client and performs no network call
itself. Callers inject a per-dataset schema lister and a per-request quoter
(production wires them to isolated-child ``list_schemas`` / ``get_cost``; tests
inject fakes with a fixed clock).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from neuralmarket.data.acquisition.cost_estimation import (
    CostSource,
    PlanCostEntry,
    summarize_plan,
)
from neuralmarket.data.acquisition.metadata_runner import IsolatedMetadataResult
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    validate_canonical_pilot_plan,
)

#: Fresh quote is reviewed alongside the 30-minute manual portal attestation.
RECHECK_FRESHNESS = timedelta(minutes=30)
#: Bounded attempts per request (mirrors the metadata timeout policy).
DEFAULT_MAX_ATTEMPTS = 2

#: Per-dataset schema lister: dataset -> list of supported schema names.
SchemaLister = Callable[[str], list[str]]
#: Per-request quoter: (request, attempt, timeout_seconds) -> isolation result.
RequestQuoter = Callable[[AcquisitionRequest, int, float], IsolatedMetadataResult]


class CostRecheckError(ValueError):
    """A structural precondition of the cost recheck was violated."""


@dataclass(frozen=True)
class RequestQuote:
    """One frozen request's fresh provider quote (or unavailable outcome)."""

    request_id: str
    dataset: str
    schema: str
    symbols: tuple[str, ...]
    stype_in: str
    start: str
    end: str
    status: str  # "quoted" | "unavailable"
    cost_usd: str | None
    attempts: int
    last_failure_class: str | None
    last_http_status: int | None
    remaining_children: int | str


@dataclass(frozen=True)
class CostRecheckResult:
    """Structured, sanitized fresh-cost recheck evidence."""

    status: str  # "complete" | "incomplete"
    authorization_ready: bool
    observed_at: str
    expires_at: str
    sdk_version: str
    repository_head: str
    checkpoint_sha256: str
    plan_hash: str
    request_manifest_sha256: str
    quotes: list[RequestQuote]
    provider_quote_count: int
    unavailable_quote_count: int
    fresh_raw_total_usd: str
    fresh_conservative_total_usd: str
    prior_raw_total_usd: str
    prior_conservative_total_usd: str
    absolute_delta_usd: str
    relative_delta: str
    largest_request_usd: str
    within_total_cap: bool
    within_per_request_cap: bool
    within_drift_ceiling: bool
    schema_validation: dict[str, Any]
    provider_call_inventory: dict[str, int]
    attempt_history: list[dict[str, Any]] = field(default_factory=list)


def _quote_cost(value: object) -> Decimal:
    """Convert a provider numeric cost to an exact, finite, non-negative Decimal.

    Uses ``Decimal(str(value))`` so a binary float never contaminates the
    evidence; rejects NaN, infinity, and negatives.
    """
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise CostRecheckError(f"non-decimal provider cost: {type(value).__name__}") from exc
    if not parsed.is_finite():
        raise CostRecheckError("provider cost is not finite")
    if parsed < 0:
        raise CostRecheckError("provider cost is negative")
    return parsed


def _validate_schemas(
    requests: list[AcquisitionRequest], schema_lister: SchemaLister
) -> tuple[dict[str, Any], int]:
    """Group requests by dataset and verify each frozen schema is supported.

    Calls ``schema_lister`` exactly once per unique dataset. Raises
    ``CostRecheckError`` before any quote when a frozen schema is unsupported.
    """
    by_dataset: dict[str, set[str]] = {}
    for request in requests:
        by_dataset.setdefault(request.dataset, set()).add(request.schema_name)
    result: dict[str, Any] = {}
    calls = 0
    for dataset in sorted(by_dataset):
        requested = sorted(by_dataset[dataset])
        supported = set(schema_lister(dataset))
        calls += 1
        missing = [schema for schema in requested if schema not in supported]
        result[dataset] = {
            "requested_schemas": requested,
            "all_supported": not missing,
            "unsupported_schemas": missing,
        }
        if missing:
            raise CostRecheckError(
                f"dataset {dataset} does not support frozen schema(s): {', '.join(missing)}"
            )
    return result, calls


def recheck_costs(
    *,
    requests: list[AcquisitionRequest],
    repository_head: str,
    checkpoint_sha256: str,
    plan_hash: str,
    request_manifest_sha256: str,
    sdk_version: str,
    now: datetime,
    schema_lister: SchemaLister,
    quoter: RequestQuoter,
    timeout_seconds: float,
    prior_raw_total_usd: Decimal,
    prior_conservative_total_usd: Decimal,
    tracked_total_usd: Decimal,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> CostRecheckResult:
    """Fresh-quote every frozen request and evaluate spending gates, fail-closed.

    ``requests`` must be exactly the canonical 25-request pilot plan; any other
    shape is rejected before a single quote, preventing cross-product expansion.
    A quote that fails its bounded attempts marks the run ``incomplete`` and
    ``authorization_ready = False`` while preserving partial evidence. No derived
    fallback is ever substituted for a failed fresh provider quote.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise CostRecheckError("recheck time must be timezone-aware")
    now = now.astimezone(UTC)
    if max_attempts < 1:
        raise CostRecheckError("max_attempts must be >= 1")

    # Exact frozen shape (rejects any broadened / cross-product plan).
    validate_canonical_pilot_plan(requests)

    schema_validation, schema_calls = _validate_schemas(requests, schema_lister)

    quotes: list[RequestQuote] = []
    attempt_history: list[dict[str, Any]] = []
    entries: list[PlanCostEntry] = []
    get_cost_calls = 0
    unavailable = 0

    for request in requests:
        cost: Decimal | None = None
        attempts_used = 0
        last_failure: str | None = None
        last_status: int | None = None
        remaining: int | str = "unknown"
        for attempt in range(1, max_attempts + 1):
            attempts_used = attempt
            get_cost_calls += 1
            isolated = quoter(request, attempt, timeout_seconds)
            remaining = isolated.remaining_children
            last_event = isolated.events[-1] if isolated.events else None
            attempt_history.append(
                {
                    "request_id": request.request_id,
                    "attempt": attempt,
                    "failure_type": isolated.failure_type,
                    "http_status": last_event.http_status if last_event else None,
                    "remaining_children": isolated.remaining_children,
                    "child_joined": isolated.child_joined,
                    "child_terminated": isolated.child_terminated,
                }
            )
            if not isolated.failure_type:
                cost = _quote_cost(isolated.endpoint_values["cost"])
                break
            last_failure = isolated.failure_type
            last_status = last_event.http_status if last_event else None
        if cost is None:
            unavailable += 1
            quotes.append(
                RequestQuote(
                    request_id=request.request_id,
                    dataset=request.dataset,
                    schema=request.schema_name,
                    symbols=request.symbols,
                    stype_in=request.stype_in,
                    start=request.start.isoformat(),
                    end=request.end_exclusive.isoformat(),
                    status="unavailable",
                    cost_usd=None,
                    attempts=attempts_used,
                    last_failure_class=last_failure,
                    last_http_status=last_status,
                    remaining_children=remaining,
                )
            )
            continue
        # Provider-only quote: raw == conservative (no derived 1.25x margin).
        entries.append(PlanCostEntry(request.request_id, CostSource.PROVIDER_GET_COST, cost, cost))
        quotes.append(
            RequestQuote(
                request_id=request.request_id,
                dataset=request.dataset,
                schema=request.schema_name,
                symbols=request.symbols,
                stype_in=request.stype_in,
                start=request.start.isoformat(),
                end=request.end_exclusive.isoformat(),
                status="quoted",
                cost_usd=str(cost),
                attempts=attempts_used,
                last_failure_class=None,
                last_http_status=None,
                remaining_children=remaining,
            )
        )

    summary = summarize_plan(entries, tracked_total_usd=tracked_total_usd)
    fresh_raw = summary.raw_total_usd
    absolute_delta = fresh_raw - prior_raw_total_usd
    relative_delta = (
        absolute_delta / prior_raw_total_usd if prior_raw_total_usd != 0 else Decimal(0)
    )
    complete = unavailable == 0
    authorization_ready = complete and summary.within_all_gates

    return CostRecheckResult(
        status="complete" if complete else "incomplete",
        authorization_ready=authorization_ready,
        observed_at=now.isoformat(),
        expires_at=(now + RECHECK_FRESHNESS).isoformat(),
        sdk_version=sdk_version,
        repository_head=repository_head,
        checkpoint_sha256=checkpoint_sha256,
        plan_hash=plan_hash,
        request_manifest_sha256=request_manifest_sha256,
        quotes=quotes,
        provider_quote_count=len(entries),
        unavailable_quote_count=unavailable,
        fresh_raw_total_usd=str(fresh_raw),
        fresh_conservative_total_usd=str(summary.conservative_total_usd),
        prior_raw_total_usd=str(prior_raw_total_usd),
        prior_conservative_total_usd=str(prior_conservative_total_usd),
        absolute_delta_usd=str(absolute_delta),
        relative_delta=str(relative_delta),
        largest_request_usd=str(summary.largest_conservative_request_usd),
        within_total_cap=summary.within_total_cap,
        within_per_request_cap=summary.within_per_request_cap,
        within_drift_ceiling=summary.within_drift_ceiling,
        schema_validation=schema_validation,
        provider_call_inventory={
            "list_schemas": schema_calls,
            "get_cost": get_cost_calls,
            "get_record_count": 0,
            "get_billable_size": 0,
            "list_unit_prices": 0,
            "timeseries_get_range": 0,
            "batch": 0,
            "live": 0,
            "symbology": 0,
        },
        attempt_history=attempt_history,
    )
