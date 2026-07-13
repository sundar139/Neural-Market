"""Deterministic, exact request-plan model and generation for the pilot.

Every request in the generated plan is a *plan*, never an executed download:
no network client is constructed here, and draft estimate fields remain empty
until metadata preflight refreshes and finalizes them via
:class:`~neuralmarket.data.acquisition.estimation.MetadataEstimator`. The
plan itself is derived purely from the pilot YAML config and the exchange
calendar, so it is byte-for-byte deterministic across regenerations.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from neuralmarket.core.configuration import ConfigurationError
from neuralmarket.data.acquisition.budget import round_usd, to_decimal
from neuralmarket.data.acquisition.calendar import (
    QUOTE_WINDOW_MINUTES,
    full_day_range_window,
    quote_window,
    sessions_in_month,
)
from neuralmarket.data.contracts import AwareUTCDatetime
from neuralmarket.data.manifests import canonical_dumps

if TYPE_CHECKING:
    from neuralmarket.data.acquisition.estimation import MetadataEstimate

_STYPE_OUT = "instrument_id"
_PLACEHOLDER_COST = str(round_usd(Decimal(0)))


class _UnderlyingBlock(BaseModel):
    """Approved ARCX underlying dataset/symbol/schemas for the pilot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    symbol: str
    stype_in: str
    schemas: list[str]


class _OptionsBlock(BaseModel):
    """Approved OPRA options dataset/symbol/schemas for the pilot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    symbol: str
    stype_in: str
    definition_schema: str
    quote_schema: str


class _RetryBlock(BaseModel):
    """Deterministic retry/backoff policy for pilot execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    maximum_attempts: int
    initial_delay_seconds: int
    multiplier: int
    maximum_delay_seconds: int
    jitter: str


class PilotExecutionConfig(BaseModel):
    """Parsed ``pilot_january_2019.yaml`` pilot-execution configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pilot_month: str
    calendar_name: str
    quote_window_minutes: int
    maximum_spend_usd: Decimal
    maximum_single_request_usd: Decimal
    estimate_increase_tolerance_fraction: Decimal
    require_exact_plan_hash: bool
    require_authorization_file: bool
    purchase_authorized: Literal[False]
    underlying: _UnderlyingBlock
    options: _OptionsBlock
    retry: _RetryBlock

    @field_validator(
        "maximum_spend_usd",
        "maximum_single_request_usd",
        "estimate_increase_tolerance_fraction",
        mode="before",
    )
    @classmethod
    def _coerce_decimal(cls, value: Any) -> Decimal:
        return to_decimal(value)

    @field_validator("quote_window_minutes")
    @classmethod
    def _check_quote_window_minutes(cls, value: int) -> int:
        # quote_window() in calendar.py ignores this field and always uses its
        # own hardcoded QUOTE_WINDOW_MINUTES constant, so a mismatch here
        # would silently do nothing -- fail loudly instead.
        if value != QUOTE_WINDOW_MINUTES:
            raise ValueError(
                f"quote_window_minutes={value} does not match the hardcoded "
                f"calendar.QUOTE_WINDOW_MINUTES={QUOTE_WINDOW_MINUTES}; "
                "quote_window() is not parameterized by config, so this "
                "value cannot currently be honored."
            )
        return value


def load_pilot_config(path: Path | str) -> PilotExecutionConfig:
    """Load and validate the pilot-execution YAML config.

    Raises:
        ConfigurationError: If the file is missing, is not valid YAML, is not
            a mapping, is missing a required top-level block, or fails schema
            validation.
    """
    resolved = Path(path)
    try:
        text = resolved.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Pilot configuration file not found: {resolved}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Unable to read pilot configuration {resolved}: {exc}") from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Malformed YAML in pilot configuration {resolved}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"Pilot configuration {resolved} must contain a mapping, got {type(raw).__name__}."
        )

    try:
        flattened = {
            **raw["pilot_execution"],
            "underlying": raw["underlying"],
            "options": raw["options"],
            "retry": raw["retry"],
        }
        return PilotExecutionConfig.model_validate(flattened)
    except (KeyError, ValidationError) as exc:
        raise ConfigurationError(f"Invalid pilot configuration in {resolved}: {exc}") from exc


class AcquisitionRequest(BaseModel):
    """One planned, unexecuted metadata/download request in the pilot plan."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    request_id: str
    wave: Literal["arcx_catalog", "arcx_underlying", "opra_definitions", "opra_closing_quotes"]
    dataset: str
    schema_name: str = Field(alias="schema")
    symbols: tuple[str, ...]
    stype_in: str
    stype_out: str
    start: AwareUTCDatetime
    end_exclusive: AwareUTCDatetime
    encoding: Literal["dbn"]
    compression: Literal["zstd", "none"]
    expected_split: Literal["training"]
    session_date: date | None
    calendar: str
    logical_output_path: str = ""
    specification_hash: str = ""
    estimated_record_count: int | None = None
    estimated_billable_size: int | None = None
    estimated_cost: str | None = None
    currency: Literal["USD"]
    estimate_timestamp: AwareUTCDatetime | None = None
    estimate_method: str | None = None
    estimate_response_hash: str | None = None
    request_hash: str

    @model_validator(mode="after")
    def _validate_half_open_window(self) -> AcquisitionRequest:
        if self.start >= self.end_exclusive:
            raise ValueError("request start must precede end_exclusive")
        return self


def compute_request_hash(request_payload_without_hash: dict[str, Any]) -> str:
    """Return the SHA-256 hash of a request payload's canonical JSON.

    ``request_hash`` is stripped from the payload before hashing (whether or
    not it is present) so a request's hash never depends on itself, and the
    payload must already be JSON-safe (no machine-specific paths, datetimes,
    or ``Decimal`` values -- callers pass ISO-string/plain-JSON fields only).
    """
    reduced = {
        k: v
        for k, v in request_payload_without_hash.items()
        if k not in {"request_hash", "estimate_timestamp"}
    }
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def compute_specification_hash(request_payload: dict[str, Any]) -> str:
    """Hash stable request identity before metadata estimation."""
    estimate_fields = {
        "specification_hash",
        "estimated_record_count",
        "estimated_billable_size",
        "estimated_cost",
        "estimate_timestamp",
        "estimate_method",
        "estimate_response_hash",
        "request_hash",
    }
    reduced = {k: v for k, v in request_payload.items() if k not in estimate_fields}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def deterministic_request_id(
    wave: str,
    dataset: str,
    schema_name: str,
    symbols: tuple[str, ...],
    session_date: date | None,
) -> str:
    """Return a short, stable hex id derived from a request's identity fields."""
    seed = (
        f"{wave}:{dataset}:{schema_name}:{'-'.join(symbols)}:"
        f"{session_date.isoformat() if session_date else 'range'}"
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _sort_key(request: AcquisitionRequest) -> tuple[str, str, str, date, tuple[str, ...]]:
    return (
        request.wave,
        request.dataset,
        request.schema_name,
        request.session_date or date.min,
        request.symbols,
    )


def _build_request(
    *,
    wave: str,
    dataset: str,
    schema_name: str,
    symbols: tuple[str, ...],
    stype_in: str,
    window: tuple[Any, Any],
    session_date: date | None,
    calendar_name: str,
) -> AcquisitionRequest:
    start, end_exclusive = window
    request_id = deterministic_request_id(wave, dataset, schema_name, symbols, session_date)
    partition = (
        f"session_date={session_date.isoformat()}"
        if session_date is not None
        else (f"start_date={start.date().isoformat()}/end_date={end_exclusive.date().isoformat()}")
    )
    logical_output_path = (
        f"data/raw/databento/pilot_january_2019/{dataset}/{schema_name}/"
        f"{partition}/{request_id}.dbn"
    )
    request = AcquisitionRequest(
        request_id=request_id,
        wave=wave,  # type: ignore[arg-type]
        dataset=dataset,
        schema=schema_name,
        symbols=symbols,
        stype_in=stype_in,
        stype_out=_STYPE_OUT,
        start=start,
        end_exclusive=end_exclusive,
        encoding="dbn",
        compression="zstd",
        expected_split="training",
        session_date=session_date,
        calendar=calendar_name,
        logical_output_path=logical_output_path,
        currency="USD",
        request_hash="",
    )
    payload = request.model_dump(mode="json", by_alias=True)
    specification_hash = compute_specification_hash(payload)
    return request.model_copy(
        update={"specification_hash": specification_hash, "request_hash": specification_hash}
    )


def finalize_request(
    request: AcquisitionRequest,
    estimate: MetadataEstimate,
    estimated_at: Any,
) -> AcquisitionRequest:
    """Bind one metadata estimate to a draft request and compute its final hash."""
    identity = (
        request.dataset,
        request.schema_name,
        request.symbols[0],
        request.stype_in,
        request.start,
        request.end_exclusive,
    )
    if identity != (
        estimate.dataset,
        estimate.schema,
        estimate.symbol,
        estimate.stype_in,
        estimate.window_start,
        estimate.window_end,
    ):
        raise ValueError(f"metadata estimate does not match request {request.request_id}")
    method = "metadata:get_record_count+get_billable_size+get_cost"
    response = {
        "request_id": request.request_id,
        "record_count": estimate.record_count,
        "billable_size_bytes": estimate.billable_size_bytes,
        "cost_usd": str(estimate.cost_usd),
        "currency": request.currency,
        "method": method,
    }
    response_hash = hashlib.sha256(canonical_dumps(response).encode("utf-8")).hexdigest()
    finalized = request.model_copy(
        update={
            "estimated_record_count": estimate.record_count,
            "estimated_billable_size": estimate.billable_size_bytes,
            "estimated_cost": str(estimate.cost_usd),
            "estimate_timestamp": estimated_at,
            "estimate_method": method,
            "estimate_response_hash": response_hash,
            "request_hash": "",
        }
    )
    return finalized.model_copy(
        update={
            "request_hash": compute_request_hash(finalized.model_dump(mode="json", by_alias=True))
        }
    )


def build_pilot_request_plan(config: PilotExecutionConfig) -> list[AcquisitionRequest]:
    """Build the exact, deterministic pilot request plan from a validated config.

    Raises:
        ValueError: If the configured calendar has no sessions in the pilot month.
    """
    sessions = sessions_in_month(config.calendar_name, config.pilot_month)
    if not sessions:
        raise ValueError(
            f"No {config.calendar_name} sessions found for pilot month {config.pilot_month}."
        )

    underlying_symbols = (config.underlying.symbol,)
    options_symbols = (config.options.symbol,)
    catalog_window = full_day_range_window(sessions[0], sessions[-1])

    requests = [
        _build_request(
            wave="arcx_catalog",
            dataset=config.underlying.dataset,
            schema_name="definition",
            symbols=underlying_symbols,
            stype_in=config.underlying.stype_in,
            window=catalog_window,
            session_date=None,
            calendar_name=config.calendar_name,
        ),
        _build_request(
            wave="arcx_underlying",
            dataset=config.underlying.dataset,
            schema_name="ohlcv-1d",
            symbols=underlying_symbols,
            stype_in=config.underlying.stype_in,
            window=catalog_window,
            session_date=None,
            calendar_name=config.calendar_name,
        ),
        _build_request(
            wave="arcx_underlying",
            dataset=config.underlying.dataset,
            schema_name="statistics",
            symbols=underlying_symbols,
            stype_in=config.underlying.stype_in,
            window=catalog_window,
            session_date=None,
            calendar_name=config.calendar_name,
        ),
        _build_request(
            wave="opra_definitions",
            dataset=config.options.dataset,
            schema_name=config.options.definition_schema,
            symbols=options_symbols,
            stype_in="parent",
            window=catalog_window,
            session_date=None,
            calendar_name=config.calendar_name,
        ),
    ]
    for session in sessions:
        requests.append(
            _build_request(
                wave="opra_closing_quotes",
                dataset=config.options.dataset,
                schema_name=config.options.quote_schema,
                symbols=options_symbols,
                stype_in=config.options.stype_in,
                window=quote_window(config.calendar_name, session),
                session_date=session,
                calendar_name=config.calendar_name,
            )
        )

    return sorted(requests, key=_sort_key)


def plan_hash(
    requests: list[AcquisitionRequest],
    bindings: dict[str, Any] | None = None,
    plan_metadata: dict[str, Any] | None = None,
) -> str:
    """Return the SHA-256 hash over the canonical JSON of every request payload.

    Each request's own ``request_hash`` is included; the requests are sorted
    into the same deterministic order used by :func:`build_pilot_request_plan`
    so this value is stable across regenerations and independent of caller
    ordering.
    """
    ordered = sorted(requests, key=_sort_key)
    payloads = [r.model_dump(mode="json", by_alias=True) for r in ordered]
    for payload in payloads:
        payload.pop("estimate_timestamp", None)
    canonical = canonical_dumps({"bindings": bindings or {}, "requests": payloads})
    canonical = canonical_dumps(
        {
            "bindings": bindings or {},
            "plan_metadata": plan_metadata or {},
            "requests": payloads,
        }
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_final_request(request: AcquisitionRequest) -> None:
    """Reject a draft, tampered estimate, or tampered final request hash."""
    payload = request.model_dump(mode="json", by_alias=True)
    if compute_specification_hash(payload) != request.specification_hash:
        raise ValueError(f"request specification hash mismatch: {request.request_id}")
    required = (
        request.estimated_record_count,
        request.estimated_billable_size,
        request.estimated_cost,
        request.estimate_timestamp,
        request.estimate_method,
        request.estimate_response_hash,
    )
    if any(value is None for value in required):
        raise ValueError(f"request is not finalized: {request.request_id}")
    if request.estimated_record_count is None or request.estimated_record_count < 0:
        raise ValueError(f"request record-count estimate is negative: {request.request_id}")
    if request.estimated_billable_size is None or request.estimated_billable_size < 0:
        raise ValueError(f"request billable-size estimate is negative: {request.request_id}")
    if to_decimal(request.estimated_cost) < 0:
        raise ValueError(f"request cost estimate is negative: {request.request_id}")
    response = {
        "request_id": request.request_id,
        "record_count": request.estimated_record_count,
        "billable_size_bytes": request.estimated_billable_size,
        "cost_usd": request.estimated_cost,
        "currency": request.currency,
        "method": request.estimate_method,
    }
    response_hash = hashlib.sha256(canonical_dumps(response).encode("utf-8")).hexdigest()
    if response_hash != request.estimate_response_hash:
        raise ValueError(f"request estimate response hash mismatch: {request.request_id}")
    if compute_request_hash(payload) != request.request_hash:
        raise ValueError(f"request hash mismatch: {request.request_id}")
