"""Process-isolated, checkpointed Databento metadata estimation."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import multiprocessing
import os
import queue
import time
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from neuralmarket.data.acquisition.cost_estimation import (
    ACQUISITION_FEED_MODE,
    CostSource,
    PlanCostEntry,
    PlanCostSummary,
    ProviderCostSample,
    UnitPriceSnapshot,
    build_derived_estimate,
    cross_validate,
    parse_unit_price_snapshot,
    summarize_plan,
)
from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.providers import DatabentoMetadataProvider
from neuralmarket.data.acquisition.requests import AcquisitionRequest
from neuralmarket.data.acquisition.unit_price_diagnostics import (
    UnitPriceFailureCode,
    UnitPriceFailureDiagnostic,
    UnitPriceFailureStage,
    build_diagnostic,
    classify_parsing_code,
    classify_sanitization_code,
    structural_fingerprint,
    summarize_response_shape,
)
from neuralmarket.data.errors import CostEstimationError

_UNIT_PRICE_TARGET_SCHEMA = "cbbo-1m"

ESTIMATOR_VERSION = "pilot-metadata-process-v1"
Endpoint = Literal["record-count", "billable-size", "cost"]


class MetadataOperationEvent(BaseModel):
    """One flushed, secret-free child operation event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    request_index: int
    request_count: int
    request_id: str
    dataset: str
    schema_name: str
    session_date: str | None
    endpoint: Endpoint
    attempt: int
    started_at: str
    completed_at: str | None = None
    elapsed_seconds: float | None = None
    outcome: str = "started"
    exception_class: str | None = None
    http_status: int | None = None
    child_pid: int


class IsolatedMetadataResult(BaseModel):
    """Typed outcome for one logical request child."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate: MetadataEstimate | None = None
    endpoint_values: dict[Endpoint, int | float | str] = Field(default_factory=dict)
    events: list[MetadataOperationEvent]
    failure_type: str | None = None
    failed_endpoint: Endpoint | None = None
    child_pid: int
    child_exitcode: int | None
    child_terminated: bool = False
    child_joined: bool
    remaining_children: int


def _status(exc: BaseException) -> int | None:
    value = getattr(exc, "http_status", None) or getattr(exc, "status_code", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _metadata_child(
    output: Any,
    request_payload: dict[str, Any],
    run_id: str,
    request_index: int,
    request_count: int,
    attempt: int,
    only_endpoint: Endpoint | None,
) -> None:
    """Construct a restricted client and execute one request in a child process."""
    import databento as db

    request = AcquisitionRequest.model_validate(request_payload)
    provider = DatabentoMetadataProvider(db.Historical())
    kwargs = {
        "dataset": request.dataset,
        "symbols": list(request.symbols),
        "schema": request.schema_name,
        "stype_in": request.stype_in,
        "start": request.start.isoformat(),
        "end": request.end_exclusive.isoformat(),
    }
    values: dict[str, object] = {}
    operations: tuple[tuple[Endpoint, str], ...] = (
        ("record-count", "get_record_count"),
        ("billable-size", "get_billable_size"),
        ("cost", "get_cost"),
    )
    try:
        for endpoint, method in operations:
            if only_endpoint is not None and endpoint != only_endpoint:
                continue
            started = datetime.now(UTC)
            event = MetadataOperationEvent(
                run_id=run_id,
                request_index=request_index,
                request_count=request_count,
                request_id=request.request_id,
                dataset=request.dataset,
                schema_name=request.schema_name,
                session_date=request.session_date.isoformat() if request.session_date else None,
                endpoint=endpoint,
                attempt=attempt,
                started_at=started.isoformat(),
                child_pid=os.getpid(),
            )
            output.put(("event", event.model_dump(mode="json")))
            try:
                values[endpoint] = getattr(provider, method)(**kwargs)
            except BaseException as exc:
                failed = event.model_copy(
                    update={
                        "completed_at": datetime.now(UTC).isoformat(),
                        "elapsed_seconds": (datetime.now(UTC) - started).total_seconds(),
                        "outcome": "failed",
                        "exception_class": type(exc).__name__,
                        "http_status": _status(exc),
                    }
                )
                output.put(("event", failed.model_dump(mode="json")))
                output.put(("failure", {"endpoint": endpoint, "message": type(exc).__name__}))
                return
            completed = event.model_copy(
                update={
                    "completed_at": datetime.now(UTC).isoformat(),
                    "elapsed_seconds": (datetime.now(UTC) - started).total_seconds(),
                    "outcome": "succeeded",
                }
            )
            output.put(("event", completed.model_dump(mode="json")))
        output.put(("result", values))
    finally:
        provider.close()


def _nonnegative(value: object, kind: type[int] | type[float]) -> int | float:
    parsed = kind(str(value))
    if parsed < 0:
        raise ValueError("negative metadata estimate")
    return parsed


def run_isolated_metadata_request(
    *,
    request: AcquisitionRequest,
    run_id: str,
    request_index: int,
    request_count: int,
    attempt: int,
    timeout_seconds: float,
    event_sink: Callable[[MetadataOperationEvent], None] | None = None,
    only_endpoint: Endpoint | None = None,
    worker: Callable[..., None] = _metadata_child,
) -> IsolatedMetadataResult:
    """Run one metadata request in a spawn child and kill it at the deadline."""
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    child = context.Process(
        target=worker,
        args=(
            output,
            request.model_dump(mode="json", by_alias=True),
            run_id,
            request_index,
            request_count,
            attempt,
            only_endpoint,
        ),
        name=f"neuralmarket-metadata-{request.request_id}",
    )
    child.start()
    deadline = time.monotonic() + timeout_seconds
    events: list[MetadataOperationEvent] = []
    values: dict[str, object] | None = None
    failure: dict[str, object] | None = None
    while time.monotonic() < deadline and child.is_alive():
        try:
            kind, payload = output.get(timeout=min(0.1, max(0.01, deadline - time.monotonic())))
        except queue.Empty:
            continue
        if kind == "event":
            event = MetadataOperationEvent.model_validate(payload)
            events.append(event)
            if event_sink:
                event_sink(event)
        elif kind == "result":
            values = payload
        elif kind == "failure":
            failure = payload
    child.join(timeout=0.2)
    terminated = False
    if child.is_alive():
        terminated = True
        child.terminate()
        child.join(timeout=2)
        if child.is_alive():
            child.kill()
            child.join(timeout=2)
    while True:
        try:
            kind, payload = output.get_nowait()
        except queue.Empty:
            break
        if kind == "event":
            event = MetadataOperationEvent.model_validate(payload)
            events.append(event)
            if event_sink:
                event_sink(event)
        elif kind == "result":
            values = payload
        elif kind == "failure":
            failure = payload
    active = sum(
        item.name.startswith("neuralmarket-metadata-") for item in multiprocessing.active_children()
    )
    active_endpoint = next(
        (event.endpoint for event in reversed(events) if event.outcome == "started"), None
    )
    if terminated:
        return IsolatedMetadataResult(
            events=events,
            failure_type="metadata_hard_timeout",
            failed_endpoint=active_endpoint,
            child_pid=child.pid or -1,
            child_exitcode=child.exitcode,
            child_terminated=True,
            child_joined=not child.is_alive(),
            remaining_children=active,
        )
    if failure is not None or values is None:
        return IsolatedMetadataResult(
            events=events,
            failure_type=str((failure or {}).get("message", "metadata_child_failed")),
            failed_endpoint=cast(Endpoint | None, (failure or {}).get("endpoint")),
            child_pid=child.pid or -1,
            child_exitcode=child.exitcode,
            child_joined=not child.is_alive(),
            remaining_children=active,
        )
    if only_endpoint is not None:
        estimate = None
    else:
        estimate = MetadataEstimate(
            dataset=request.dataset,
            schema=request.schema_name,
            symbol=request.symbols[0],
            stype_in=request.stype_in,
            window_start=request.start,
            window_end=request.end_exclusive,
            record_count=int(_nonnegative(values["record-count"], int)),
            billable_size_bytes=int(_nonnegative(values["billable-size"], int)),
            cost_usd=Decimal(str(_nonnegative(values["cost"], float))),
            retries=attempt - 1,
        )
    return IsolatedMetadataResult(
        estimate=estimate,
        endpoint_values={
            cast(Endpoint, key): cast(int | float | str, value) for key, value in values.items()
        },
        events=events,
        child_pid=child.pid or -1,
        child_exitcode=child.exitcode,
        child_joined=not child.is_alive(),
        remaining_children=active,
    )


def endpoint_response_hash(endpoint: Endpoint, value: int | float | str) -> str:
    """Hash only stable endpoint semantics, excluding attempts and timings."""
    payload = json.dumps(
        {"endpoint": endpoint, "value": str(value)}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()


CostResponseKind = Literal["provider_response", "derived_response", "portal_response"]


class MetadataEndpointResult(BaseModel):
    """One reusable endpoint result within a fresh checkpoint generation.

    The cost-source and derived-provenance fields are optional and default to
    ``None`` so legacy checkpoints (value/completed_at/response_hash only) remain
    readable; a cost endpoint with ``cost_source`` unset is interpreted as a
    provider ``get_cost`` result.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["complete"] = "complete"
    value: int | float | str
    completed_at: str
    response_hash: str
    # Cost-source provenance (only populated on cost endpoints).
    cost_source: CostResponseKind | None = None
    raw_cost_usd: str | None = None
    conservative_cost_usd: str | None = None
    billable_size_bytes: int | None = None
    billable_size_response_hash: str | None = None
    unit_price_usd_per_gib: str | None = None
    unit_price_snapshot_hash: str | None = None
    cross_validation_evidence_hash: str | None = None
    calculation_version: str | None = None
    fallback_trigger_class: str | None = None
    fallback_trigger_http_status: int | None = None
    derivation_hash: str | None = None


class MetadataCheckpoint(BaseModel):
    """Hash-bound local progress for resumable metadata preparation."""

    model_config = ConfigDict(extra="forbid")

    checkpoint_version: Literal["1.0"] = "1.0"
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str
    updated_at: str
    source_manifest_hash: str
    split_manifest_hash: str
    acquisition_policy_hash: str
    pilot_config_hash: str
    calendar_version: str
    databento_client_version: str
    estimator_version: str = ESTIMATOR_VERSION
    ordered_request_specification_hashes: list[str]
    completed_estimates: dict[str, dict[str, Any]] = Field(default_factory=dict)
    endpoint_results: dict[str, dict[Endpoint, MetadataEndpointResult]] = Field(
        default_factory=dict
    )
    pending_request_ids: list[str]
    failed_request_id: str | None = None
    failed_endpoint: Endpoint | None = None
    last_failure: str | None = None
    attempt_history: list[dict[str, Any]] = Field(default_factory=list)


def write_checkpoint(path: Path, checkpoint: MetadataCheckpoint) -> None:
    """Atomically fsync and replace a local metadata checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with partial.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(checkpoint.model_dump(mode="json"), handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def load_checkpoint(
    path: Path,
    *,
    expected: dict[str, object],
    maximum_age_minutes: int,
) -> MetadataCheckpoint:
    """Load a complete, fresh checkpoint whose dependency bindings match exactly."""
    try:
        checkpoint = MetadataCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise ValueError("invalid_metadata_checkpoint") from exc
    for key, value in expected.items():
        if getattr(checkpoint, key) != value:
            raise ValueError(f"metadata_checkpoint_mismatch:{key}")
    updated = datetime.fromisoformat(checkpoint.updated_at)
    if datetime.now(UTC) - updated > timedelta(minutes=maximum_age_minutes):
        raise ValueError("metadata_checkpoint_expired")
    for estimate in checkpoint.completed_estimates.values():
        MetadataEstimate(**estimate)
        if any(
            float(estimate[key]) < 0 for key in ("record_count", "billable_size_bytes", "cost_usd")
        ):
            raise ValueError("invalid_metadata_checkpoint_estimate")
    for endpoints in checkpoint.endpoint_results.values():
        for endpoint, result in endpoints.items():
            if result.response_hash != endpoint_response_hash(endpoint, result.value):
                raise ValueError("invalid_metadata_endpoint_hash")
    return checkpoint


def checkpoint_client_version() -> str:
    """Return the exact Databento version bound into checkpoints."""
    return importlib.metadata.version("databento")


# --- Derived-cost fallback integration ---------------------------------------

#: Terminal cost-endpoint failures eligible for the derived fallback.
_FALLBACK_HTTP_STATUSES = frozenset({500, 502, 503, 504})
_FALLBACK_EXCEPTION_CLASSES = frozenset({"TimeoutError", "ConnectionError", "ConnectionResetError"})


def cost_fallback_trigger(result: IsolatedMetadataResult) -> tuple[int | None, str | None] | None:
    """Classify a terminal cost failure into a fallback trigger, or ``None``.

    Returns ``(http_status, failure_category)`` when the failure is a bounded
    provider ``5xx`` or a connection/network timeout; ``None`` when the failure
    is prohibited (4xx, auth, entitlement, rate limit, invalid request) or the
    failed endpoint was not ``cost``. Fail-closed: unknown failures return ``None``.
    """
    if result.failed_endpoint != "cost":
        return None
    if result.failure_type == "metadata_hard_timeout":
        return None, "provider_timeout"
    last = result.events[-1] if result.events else None
    if last is None:
        return None
    if last.http_status in _FALLBACK_HTTP_STATUSES:
        return last.http_status, None
    if last.exception_class in _FALLBACK_EXCEPTION_CLASSES:
        return last.http_status, "provider_network_timeout"
    return None


def build_provider_cost_samples(
    checkpoint: MetadataCheckpoint,
    *,
    dataset: str,
    schema: str,
    feed_mode: str,
    account_pricing_context: str,
) -> list[ProviderCostSample]:
    """Gather compatible successful provider ``get_cost`` cross-validation samples.

    Only provider-sourced costs (``cost_source`` unset or ``provider_response``)
    for the exact dataset and schema count; derived costs are never evidence.
    """
    samples: list[ProviderCostSample] = []
    for request_id, estimate in checkpoint.completed_estimates.items():
        if estimate.get("dataset") != dataset or estimate.get("schema") != schema:
            continue
        cost_endpoint = checkpoint.endpoint_results.get(request_id, {}).get("cost")
        if cost_endpoint is not None and cost_endpoint.cost_source not in (
            None,
            "provider_response",
        ):
            continue
        samples.append(
            ProviderCostSample(
                dataset=dataset,
                schema=schema,
                feed_mode=feed_mode,
                account_pricing_context=account_pricing_context,
                billable_size_bytes=int(estimate["billable_size_bytes"]),
                provider_cost_usd=Decimal(str(estimate["cost_usd"])),
            )
        )
    return samples


def derive_cost_endpoint_result(
    *,
    request: AcquisitionRequest,
    billable_size_result: MetadataEndpointResult,
    snapshot: UnitPriceSnapshot,
    samples: list[ProviderCostSample],
    account_pricing_context: str,
    failure_http_status: int | None,
    failure_category: str | None,
    now_utc: str,
) -> MetadataEndpointResult:
    """Build a derived cost endpoint result, fail-closed via the estimator.

    Raises :class:`~neuralmarket.data.errors.CostEstimationError` when the
    failure is ineligible, evidence is incompatible, or cross-validation fails.
    """
    cross_validation = cross_validate(
        snapshot,
        dataset=request.dataset,
        schema=request.schema_name,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=account_pricing_context,
        samples=samples,
    )
    estimate = build_derived_estimate(
        request_id=request.request_id,
        request_specification_hash=request.request_hash,
        dataset=request.dataset,
        schema=request.schema_name,
        feed_mode=ACQUISITION_FEED_MODE,
        billable_size_bytes=int(billable_size_result.value),
        billable_size_response_hash=billable_size_result.response_hash,
        snapshot=snapshot,
        cross_validation=cross_validation,
        failure_http_status=failure_http_status,
        failure_category=failure_category,
        calculated_at=now_utc,
    )
    value = str(estimate.cost_usd)
    return MetadataEndpointResult(
        value=value,
        completed_at=now_utc,
        response_hash=endpoint_response_hash("cost", value),
        cost_source="derived_response",
        raw_cost_usd=str(estimate.cost_usd),
        conservative_cost_usd=str(estimate.conservative_cost_usd),
        billable_size_bytes=estimate.billable_size_bytes,
        billable_size_response_hash=estimate.billable_size_response_hash,
        unit_price_usd_per_gib=str(estimate.unit_price_usd_per_gib),
        unit_price_snapshot_hash=estimate.unit_price_snapshot_hash,
        cross_validation_evidence_hash=estimate.cross_validation_evidence_hash,
        calculation_version=estimate.calculation_version,
        fallback_trigger_class=failure_category or "http_5xx",
        fallback_trigger_http_status=failure_http_status,
        derivation_hash=estimate.estimate_hash,
    )


class UnitPriceSnapshotCache:
    """At-most-once-per-dataset unit-price snapshot cache for one preflight."""

    def __init__(self, loader: Callable[[str], UnitPriceSnapshot]) -> None:
        """Wrap a per-dataset snapshot loader (production wraps list_unit_prices)."""
        self._loader = loader
        self._cache: dict[str, UnitPriceSnapshot] = {}
        self.load_count = 0

    def get(self, dataset: str) -> UnitPriceSnapshot:
        """Return the cached snapshot for a dataset, loading it at most once."""
        if dataset not in self._cache:
            self.load_count += 1
            self._cache[dataset] = self._loader(dataset)
        return self._cache[dataset]


def plan_cost_rollup(
    checkpoint: MetadataCheckpoint, *, tracked_total_usd: Decimal
) -> PlanCostSummary:
    """Aggregate provider and derived costs and evaluate conservative gates."""
    entries: list[PlanCostEntry] = []
    for request_id, estimate in checkpoint.completed_estimates.items():
        raw = Decimal(str(estimate["cost_usd"]))
        cost_endpoint = checkpoint.endpoint_results.get(request_id, {}).get("cost")
        if cost_endpoint is not None and cost_endpoint.cost_source == "derived_response":
            source = CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE
            conservative = Decimal(str(cost_endpoint.conservative_cost_usd))
        else:
            source = CostSource.PROVIDER_GET_COST
            conservative = raw
        entries.append(PlanCostEntry(request_id, source, raw, conservative))
    return summarize_plan(entries, tracked_total_usd=tracked_total_usd)


def _unit_price_child(
    output: Any,
    dataset: str,
    client_version: str,
    retrieved_at_utc: str,
    expires_at_utc: str,
) -> None:
    """Fetch one dataset's unit prices in a child and emit snapshot or diagnostic."""
    import databento as db

    provider = DatabentoMetadataProvider(db.Historical())
    try:
        try:
            raw = provider.list_unit_prices(dataset=dataset)
        except BaseException as exc:
            diagnostic = build_diagnostic(
                stage=UnitPriceFailureStage.PROVIDER_CALL,
                code=UnitPriceFailureCode.PROVIDER_ERROR,
                dataset=dataset,
                feed_mode=ACQUISITION_FEED_MODE,
                schema=_UNIT_PRICE_TARGET_SCHEMA,
                failure_type=type(exc).__name__,
            )
            output.put(("failure", diagnostic.model_dump(mode="json")))
            return
        output.put(
            process_unit_price_response(
                raw,
                dataset=dataset,
                client_version=client_version,
                retrieved_at_utc=retrieved_at_utc,
                expires_at_utc=expires_at_utc,
            )
        )
    finally:
        provider.close()


def process_unit_price_response(
    raw: object,
    *,
    dataset: str,
    client_version: str,
    retrieved_at_utc: str,
    expires_at_utc: str,
) -> tuple[str, dict[str, Any]]:
    """Summarize, sanitize, and parse a raw response into a snapshot or diagnostic.

    Returns ``("snapshot", snapshot_dict)`` on success or
    ``("failure", diagnostic_dict)`` on any expected/unexpected failure, tagging
    the failing stage and a stable structural code. Parser behavior is unchanged;
    this only observes and classifies it.
    """
    summary = summarize_response_shape(raw)
    fingerprint = structural_fingerprint(summary)

    def _fail(
        stage: UnitPriceFailureStage, code: UnitPriceFailureCode, failure_type: str | None
    ) -> tuple[str, dict[str, Any]]:
        diagnostic = build_diagnostic(
            stage=stage,
            code=code,
            dataset=dataset,
            feed_mode=ACQUISITION_FEED_MODE,
            schema=_UNIT_PRICE_TARGET_SCHEMA,
            failure_type=failure_type,
            summary=summary,
            fingerprint=fingerprint,
        )
        return ("failure", diagnostic.model_dump(mode="json"))

    try:
        blocks = _sanitize_unit_price_response(raw)
    except CostEstimationError as exc:
        return _fail(
            UnitPriceFailureStage.SANITIZATION,
            classify_sanitization_code(raw),
            type(exc).__name__,
        )
    except Exception as exc:
        return _fail(
            UnitPriceFailureStage.SANITIZATION,
            UnitPriceFailureCode.UNEXPECTED_INTERNAL_ERROR,
            type(exc).__name__,
        )

    try:
        snapshot = parse_unit_price_snapshot(
            blocks,
            dataset=dataset,
            feed_mode=ACQUISITION_FEED_MODE,
            databento_client_version=client_version,
            retrieved_at_utc=retrieved_at_utc,
            expires_at_utc=expires_at_utc,
        )
    except CostEstimationError as exc:
        return _fail(
            UnitPriceFailureStage.SNAPSHOT_PARSING,
            classify_parsing_code(
                blocks, feed_mode=ACQUISITION_FEED_MODE, schema=_UNIT_PRICE_TARGET_SCHEMA
            ),
            type(exc).__name__,
        )
    except Exception as exc:
        return _fail(
            UnitPriceFailureStage.SNAPSHOT_PARSING,
            UnitPriceFailureCode.UNEXPECTED_INTERNAL_ERROR,
            type(exc).__name__,
        )
    return ("snapshot", dict(snapshot.__dict__))


def _mode_block(mode: object, schemas: object) -> dict[str, Any]:
    """Build one canonical ``{mode, schemas}`` block, failing closed on malformed input.

    Structure and representation only: each SDK price is normalized to its string
    form (the real ``list_unit_prices`` response carries JSON floats), so the
    canonical block round-trips through the child boundary as decimal strings.
    Price *validity* (positive, finite, decimal, non-bool) is decided downstream
    by :func:`parse_unit_price_snapshot`, never here.
    """
    if not isinstance(mode, str) or not mode.strip():
        raise CostEstimationError(f"unit-price feed mode must be a nonempty string: {mode!r}")
    if not isinstance(schemas, Mapping) or not schemas:
        raise CostEstimationError(f"unit-price schemas for {mode!r} must be a nonempty mapping")
    return {"mode": mode, "schemas": {str(schema): str(price) for schema, price in schemas.items()}}


def _sanitize_list_item(item: Mapping[Any, Any]) -> list[dict[str, Any]]:
    """Normalize one list item into one or more canonical mode blocks, fail-closed.

    Recognizes, in order: the confirmed SDK form ``{"mode", "unit_prices"}``, the
    canonical form ``{"mode", "schemas"}``, and the direct mode-map form
    ``{<mode>: {schema: price}}``. An item declaring both ``schemas`` and
    ``unit_prices`` is ambiguous, a ``mode``/``unit_prices`` item with unexpected
    sibling keys is unsupported, and a ``mode`` or ``unit_prices`` without a valid
    pairing is malformed; each fails closed.
    """
    has_mode = "mode" in item
    has_schemas = "schemas" in item
    has_unit_prices = "unit_prices" in item
    if has_mode and has_schemas and has_unit_prices:
        raise CostEstimationError("unit-price item declares both 'schemas' and 'unit_prices'")
    if has_mode and (has_schemas or has_unit_prices):
        wrapper = "schemas" if has_schemas else "unit_prices"
        extra = set(item.keys()) - {"mode", wrapper}
        if extra:
            raise CostEstimationError(
                f"unit-price item has unsupported sibling keys: {sorted(map(str, extra))!r}"
            )
        return [_mode_block(item["mode"], item[wrapper])]
    if has_mode or has_unit_prices:
        raise CostEstimationError(
            "unit-price item has 'mode'/'unit_prices' without a valid mode/schemas pairing"
        )
    return [_mode_block(mode, schemas) for mode, schemas in item.items()]


def _sanitize_unit_price_response(raw: object) -> list[dict[str, Any]]:
    """Normalize a Databento unit-price response into sanitized mode blocks.

    Supported shapes (anything else fails closed):

    * a top-level mapping ``{mode: {schema: price}}``;
    * a list of confirmed SDK items ``[{"mode": m, "unit_prices": {...}}, ...]``
      (databento ``0.81.0``);
    * a list of canonical blocks ``[{"mode": m, "schemas": {...}}, ...]``;
    * a list of direct mode maps ``[{mode: {schema: price}}, ...]``.

    Each feed mode becomes one block; duplicate modes are preserved (never
    merged) so downstream ambiguity checks can reject them, and block ordering is
    deterministic. A malformed entry fails the entire response rather than
    yielding only the valid subset. The raw input is never mutated.
    """
    blocks: list[dict[str, Any]] = []
    if isinstance(raw, Mapping):
        for mode, schemas in raw.items():
            blocks.append(_mode_block(mode, schemas))
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                raise CostEstimationError("unit-price list entry is not a mapping")
            blocks.extend(_sanitize_list_item(item))
    else:
        raise CostEstimationError("unit-price response is not a mapping or list")
    return blocks


class IsolatedUnitPriceResult(BaseModel):
    """Typed outcome for one isolated unit-price snapshot child."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    snapshot: UnitPriceSnapshot | None = None
    failure_type: str | None = None
    diagnostic: UnitPriceFailureDiagnostic | None = None
    child_terminated: bool = False
    child_joined: bool
    child_exit_code: int | None = None
    remaining_children: int


def run_isolated_unit_price_request(
    *,
    dataset: str,
    client_version: str,
    retrieved_at_utc: str,
    expires_at_utc: str,
    timeout_seconds: float,
    worker: Callable[..., None] = _unit_price_child,
) -> IsolatedUnitPriceResult:
    """Fetch one dataset's unit-price snapshot in a spawn child, killed at deadline."""
    context = multiprocessing.get_context("spawn")
    output = context.Queue()
    child = context.Process(
        target=worker,
        args=(output, dataset, client_version, retrieved_at_utc, expires_at_utc),
        name=f"neuralmarket-unitprice-{dataset}",
    )
    child.start()
    deadline = time.monotonic() + timeout_seconds
    snapshot_payload: dict[str, Any] | None = None
    failure: dict[str, object] | None = None
    while time.monotonic() < deadline and child.is_alive():
        try:
            kind, payload = output.get(timeout=min(0.1, max(0.01, deadline - time.monotonic())))
        except queue.Empty:
            continue
        if kind == "snapshot":
            snapshot_payload = payload
        elif kind == "failure":
            failure = payload
    child.join(timeout=0.2)
    terminated = False
    if child.is_alive():
        terminated = True
        child.terminate()
        child.join(timeout=2)
        if child.is_alive():
            child.kill()
            child.join(timeout=2)
    while True:
        try:
            kind, payload = output.get_nowait()
        except queue.Empty:
            break
        if kind == "snapshot":
            snapshot_payload = payload
        elif kind == "failure":
            failure = payload
    active = sum(
        item.name.startswith("neuralmarket-unitprice-")
        for item in multiprocessing.active_children()
    )
    exit_code = child.exitcode
    if terminated:
        return IsolatedUnitPriceResult(
            failure_type="unit_price_hard_timeout",
            diagnostic=build_diagnostic(
                stage=UnitPriceFailureStage.CHILD_TIMEOUT,
                code=UnitPriceFailureCode.CHILD_TIMEOUT,
                dataset=dataset,
                feed_mode=ACQUISITION_FEED_MODE,
                schema=_UNIT_PRICE_TARGET_SCHEMA,
            ),
            child_terminated=True,
            child_joined=not child.is_alive(),
            child_exit_code=exit_code,
            remaining_children=active,
        )
    if failure is not None:
        diagnostic = UnitPriceFailureDiagnostic.model_validate(failure)
        return IsolatedUnitPriceResult(
            failure_type=diagnostic.failure_type or diagnostic.failure_code.value,
            diagnostic=diagnostic,
            child_joined=not child.is_alive(),
            child_exit_code=exit_code,
            remaining_children=active,
        )
    if snapshot_payload is None:
        return IsolatedUnitPriceResult(
            failure_type="unit_price_child_failed",
            diagnostic=build_diagnostic(
                stage=UnitPriceFailureStage.CHILD_TRANSPORT,
                code=UnitPriceFailureCode.CHILD_NO_RESULT,
                dataset=dataset,
                feed_mode=ACQUISITION_FEED_MODE,
                schema=_UNIT_PRICE_TARGET_SCHEMA,
            ),
            child_joined=not child.is_alive(),
            child_exit_code=exit_code,
            remaining_children=active,
        )
    return IsolatedUnitPriceResult(
        snapshot=UnitPriceSnapshot(**snapshot_payload),
        child_joined=not child.is_alive(),
        child_exit_code=exit_code,
        remaining_children=active,
    )
