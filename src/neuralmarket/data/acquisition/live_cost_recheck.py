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

import hashlib
import json
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

# Ponytail: 60 minutes covers the current 25-request serial quote and review flow.
# Revisit when plan size or bounded retry duration increases materially.
RECHECK_FRESHNESS = timedelta(minutes=60)
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
    request_specification_sha256: str | None = None
    quote_source: str | None = None
    provider_response_sha256: str | None = None
    provider_observed_at: str | None = None


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
    source_evidence_sha256: str | None = None
    preserved_completed_quote_count: int = 0
    changed_completed_quote_count: int = 0
    missing_completed_quote_count: int = 0
    completed_request_refetch_count: int = 0
    resume_target_count: int = 0
    resume_attempt_count: int = 0
    final_provider_quote_count: int = 0
    final_unavailable_quote_count: int = 0


@dataclass(frozen=True)
class ResumeEvidence:
    """Validated prior evidence, ready for provider-free target selection."""

    source_evidence_sha256: str
    quotes: tuple[RequestQuote, ...]
    attempt_history: tuple[dict[str, Any], ...]
    schema_validation: dict[str, Any]
    observed_at: str
    expires_at: str


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


def _provider_response_sha256(request_id: str, specification_sha256: str, cost_usd: str) -> str:
    payload = json.dumps(
        [request_id, specification_sha256, cost_usd], separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _aware_timestamp(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise CostRecheckError(f"resume evidence {label} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise CostRecheckError(f"resume evidence {label} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CostRecheckError(f"resume evidence {label} is invalid")
    return value


def validate_resume_evidence(
    payload: dict[str, Any],
    *,
    requests: list[AcquisitionRequest],
    checkpoint_sha256: str,
    plan_hash: str,
    request_manifest_sha256: str,
    source_evidence_sha256: str,
) -> ResumeEvidence:
    """Validate prior quote evidence fully before any provider construction."""
    validate_canonical_pilot_plan(requests)
    version = payload.get("schema_version")
    if version not in {"pilot-fresh-cost-recheck-v1", "pilot-cost-recheck-v2"}:
        raise CostRecheckError("resume evidence schema/version is unsupported")
    for field_name, expected in (
        ("checkpoint_sha256", checkpoint_sha256),
        ("plan_hash", plan_hash),
        ("request_manifest_sha256", request_manifest_sha256),
    ):
        if payload.get(field_name) != expected:
            raise CostRecheckError(f"resume evidence {field_name} mismatch")
    if (
        not isinstance(source_evidence_sha256, str)
        or len(source_evidence_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_evidence_sha256)
    ):
        raise CostRecheckError("resume evidence identity is invalid")

    raw_quotes = payload.get("quotes")
    if not isinstance(raw_quotes, list) or len(raw_quotes) != len(requests):
        raise CostRecheckError("resume evidence quote partition is incomplete")
    by_id = {request.request_id: request for request in requests}
    quotes: list[RequestQuote] = []
    seen: set[str] = set()
    for raw in raw_quotes:
        if not isinstance(raw, dict) or not isinstance(raw.get("request_id"), str):
            raise CostRecheckError("resume evidence quote is invalid")
        request_id = raw["request_id"]
        if request_id in seen:
            raise CostRecheckError("resume evidence has duplicate request IDs")
        seen.add(request_id)
        request = by_id.get(request_id)
        if request is None:
            raise CostRecheckError("resume evidence contains an unknown request")
        expected_identity = (
            request.dataset,
            request.schema_name,
            list(request.symbols),
            request.stype_in,
            request.start.isoformat(),
            request.end_exclusive.isoformat(),
        )
        actual_identity = (
            raw.get("dataset"),
            raw.get("schema"),
            raw.get("symbols"),
            raw.get("stype_in"),
            raw.get("start"),
            raw.get("end"),
        )
        if actual_identity != expected_identity:
            raise CostRecheckError("resume evidence request specification changed")
        specification = raw.get("request_specification_sha256")
        if version == "pilot-cost-recheck-v2" and specification != request.specification_hash:
            raise CostRecheckError("resume evidence request identity mismatch")
        specification = request.specification_hash
        status = raw.get("status")
        if status not in {"quoted", "unavailable"}:
            raise CostRecheckError("resume evidence quote status is invalid")
        cost = raw.get("cost_usd")
        quote_source = raw.get("quote_source")
        response_sha = raw.get("provider_response_sha256")
        provider_observed_at = raw.get("provider_observed_at")
        if status == "quoted":
            if not isinstance(cost, str):
                raise CostRecheckError("resume evidence completed quote value is invalid")
            try:
                _quote_cost(cost)
            except CostRecheckError as exc:
                raise CostRecheckError("resume evidence completed quote value is invalid") from exc
            if version != "pilot-cost-recheck-v2" or quote_source != "provider_response":
                raise CostRecheckError("resume evidence completed quote lacks provider provenance")
            expected_response = _provider_response_sha256(request_id, specification, cost)
            if response_sha != expected_response:
                raise CostRecheckError("resume evidence provider quote identity mismatch")
            provider_observed_at = _aware_timestamp(
                provider_observed_at, "provider observation timestamp"
            )
        elif (
            cost is not None
            or quote_source not in {None, "unavailable"}
            or response_sha is not None
        ):
            raise CostRecheckError("resume evidence unavailable quote is invalid")
        attempts = raw.get("attempts")
        if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
            raise CostRecheckError("resume evidence attempt count is invalid")
        remaining = raw.get("remaining_children")
        if remaining != 0:
            raise CostRecheckError("resume evidence has an unclean provider child")
        quotes.append(
            RequestQuote(
                request_id=request_id,
                dataset=request.dataset,
                schema=request.schema_name,
                symbols=request.symbols,
                stype_in=request.stype_in,
                start=request.start.isoformat(),
                end=request.end_exclusive.isoformat(),
                status=status,
                cost_usd=cost,
                attempts=attempts,
                last_failure_class=raw.get("last_failure_class"),
                last_http_status=raw.get("last_http_status"),
                remaining_children=remaining,
                request_specification_sha256=specification,
                quote_source=quote_source,
                provider_response_sha256=response_sha,
                provider_observed_at=provider_observed_at,
            )
        )
    if seen != set(by_id):
        raise CostRecheckError("resume evidence quote partition is incomplete")
    unavailable = sum(quote.status == "unavailable" for quote in quotes)
    completed = len(quotes) - unavailable
    expected_status = "complete" if unavailable == 0 else "incomplete"
    if (
        payload.get("status") != expected_status
        or payload.get("provider_quote_count") != completed
        or payload.get("unavailable_quote_count") != unavailable
        or (unavailable > 0 and payload.get("authorization_ready") is not False)
    ):
        raise CostRecheckError("resume evidence status/count partition is invalid")
    try:
        financial = {
            name: _quote_cost(payload.get(name))
            for name in (
                "fresh_raw_total_usd",
                "fresh_conservative_total_usd",
                "prior_raw_total_usd",
                "prior_conservative_total_usd",
                "largest_request_usd",
            )
        }
        absolute_delta = Decimal(str(payload.get("absolute_delta_usd")))
        relative_delta = Decimal(str(payload.get("relative_delta")))
    except (CostRecheckError, InvalidOperation, TypeError) as exc:
        raise CostRecheckError("resume evidence Decimal values are invalid") from exc
    quoted_costs = [_quote_cost(quote.cost_usd) for quote in quotes if quote.status == "quoted"]
    raw_total = sum(quoted_costs, Decimal(0))
    expected_delta = raw_total - financial["prior_raw_total_usd"]
    expected_relative = (
        expected_delta / financial["prior_raw_total_usd"]
        if financial["prior_raw_total_usd"] != 0
        else Decimal(0)
    )
    if (
        not absolute_delta.is_finite()
        or not relative_delta.is_finite()
        or financial["fresh_raw_total_usd"] != raw_total
        or financial["fresh_conservative_total_usd"] != raw_total
        or financial["largest_request_usd"] != max(quoted_costs, default=Decimal(0))
        or absolute_delta != expected_delta
        or relative_delta != expected_relative
    ):
        raise CostRecheckError("resume evidence financial rollup is invalid")
    history = payload.get("attempt_history", [])
    if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
        raise CostRecheckError("resume evidence attempt history is invalid")
    schema_validation = payload.get("schema_validation", {})
    if not isinstance(schema_validation, dict):
        raise CostRecheckError("resume evidence schema validation is invalid")
    observed_at = _aware_timestamp(payload.get("observed_at"), "observation timestamp")
    expires_at = _aware_timestamp(payload.get("expires_at"), "expiry timestamp")
    if datetime.fromisoformat(expires_at) <= datetime.fromisoformat(observed_at):
        raise CostRecheckError("resume evidence freshness window is invalid")
    return ResumeEvidence(
        source_evidence_sha256=source_evidence_sha256,
        quotes=tuple(quotes),
        attempt_history=tuple(history),
        schema_validation=schema_validation,
        observed_at=observed_at,
        expires_at=expires_at,
    )


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
    resume: ResumeEvidence | None = None,
) -> CostRecheckResult:
    """Quote a frozen plan or only its validated unavailable resume targets.

    ``requests`` must be exactly the canonical 25-request pilot plan; any other
    shape is rejected before a single quote, preventing cross-product expansion.
    A quote that fails its bounded attempts marks the run ``incomplete`` and
    ``authorization_ready = False`` while preserving partial evidence. Completed
    provider quotes from validated resume evidence are never fetched again.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise CostRecheckError("recheck time must be timezone-aware")
    now = now.astimezone(UTC)
    if max_attempts < 1:
        raise CostRecheckError("max_attempts must be >= 1")

    # Exact frozen shape (rejects any broadened / cross-product plan).
    validate_canonical_pilot_plan(requests)
    preserved = [quote for quote in resume.quotes if quote.status == "quoted"] if resume else []
    preserved_ids = {quote.request_id for quote in preserved}
    target_ids = (
        {quote.request_id for quote in resume.quotes if quote.status == "unavailable"}
        if resume
        else {request.request_id for request in requests}
    )
    if preserved_ids & target_ids:
        raise CostRecheckError("completed requests overlap resume targets")
    targets = [request for request in requests if request.request_id in target_ids]
    schema_validation = dict(resume.schema_validation) if resume else {}
    current_schema_validation, schema_calls = _validate_schemas(targets, schema_lister)
    schema_validation.update(current_schema_validation)

    quotes = list(preserved)
    attempt_history = list(resume.attempt_history) if resume else []
    entries = [
        PlanCostEntry(
            quote.request_id,
            CostSource.PROVIDER_GET_COST,
            _quote_cost(quote.cost_usd),
            _quote_cost(quote.cost_usd),
        )
        for quote in preserved
    ]
    get_cost_calls = 0
    unavailable = 0

    for request in targets:
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
                    request_specification_sha256=request.specification_hash,
                )
            )
            entries.append(
                PlanCostEntry(request.request_id, CostSource.UNAVAILABLE, Decimal(0), Decimal(0))
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
                request_specification_sha256=request.specification_hash,
                quote_source="provider_response",
                provider_response_sha256=_provider_response_sha256(
                    request.request_id, request.specification_hash, str(cost)
                ),
                provider_observed_at=now.isoformat(),
            )
        )

    quotes_by_id = {quote.request_id: quote for quote in quotes}
    expected_ids = {request.request_id for request in requests}
    if len(quotes_by_id) != len(requests) or set(quotes_by_id) != expected_ids:
        raise CostRecheckError("final quote partition is incomplete")
    quotes = [quotes_by_id[request.request_id] for request in requests]
    summary = summarize_plan(entries, tracked_total_usd=tracked_total_usd)
    fresh_raw = summary.raw_total_usd
    absolute_delta = fresh_raw - prior_raw_total_usd
    relative_delta = (
        absolute_delta / prior_raw_total_usd if prior_raw_total_usd != 0 else Decimal(0)
    )
    unavailable = summary.unavailable_cost_count
    complete = unavailable == 0
    expires_at = min(
        now + RECHECK_FRESHNESS,
        datetime.fromisoformat(resume.expires_at).astimezone(UTC)
        if resume
        else now + RECHECK_FRESHNESS,
    )
    authorization_ready = complete and summary.within_all_gates and expires_at > now

    return CostRecheckResult(
        status="complete" if complete else "incomplete",
        authorization_ready=authorization_ready,
        observed_at=resume.observed_at if resume else now.isoformat(),
        expires_at=expires_at.isoformat(),
        sdk_version=sdk_version,
        repository_head=repository_head,
        checkpoint_sha256=checkpoint_sha256,
        plan_hash=plan_hash,
        request_manifest_sha256=request_manifest_sha256,
        quotes=quotes,
        provider_quote_count=summary.provider_cost_count,
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
        source_evidence_sha256=resume.source_evidence_sha256 if resume else None,
        preserved_completed_quote_count=len(preserved),
        changed_completed_quote_count=0,
        missing_completed_quote_count=0,
        completed_request_refetch_count=0,
        resume_target_count=len(targets) if resume else 0,
        resume_attempt_count=get_cost_calls if resume else 0,
        final_provider_quote_count=summary.provider_cost_count,
        final_unavailable_quote_count=summary.unavailable_cost_count,
    )
