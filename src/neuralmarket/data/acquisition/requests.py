"""Deterministic, exact request-plan model and generation for the pilot.

Every request in the generated plan is a *plan*, never an executed download:
no network client is constructed here, and every estimate field is a
placeholder (zero) until Task 6's preflight refreshes it via
:class:`~neuralmarket.data.acquisition.estimation.MetadataEstimator`. The
plan itself is derived purely from the pilot YAML config and the exchange
calendar, so it is byte-for-byte deterministic across regenerations.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from neuralmarket.core.configuration import ConfigurationError
from neuralmarket.data.acquisition.budget import round_usd, to_decimal
from neuralmarket.data.acquisition.calendar import (
    full_day_range_window,
    quote_window,
    sessions_in_month,
)
from neuralmarket.data.contracts import AwareUTCDatetime
from neuralmarket.data.manifests import canonical_dumps

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
    estimated_record_count: int
    estimated_billable_size: int
    estimated_cost: str
    currency: Literal["USD"]
    request_hash: str


def compute_request_hash(request_payload_without_hash: dict[str, Any]) -> str:
    """Return the SHA-256 hash of a request payload's canonical JSON.

    ``request_hash`` is stripped from the payload before hashing (whether or
    not it is present) so a request's hash never depends on itself, and the
    payload must already be JSON-safe (no machine-specific paths, datetimes,
    or ``Decimal`` values -- callers pass ISO-string/plain-JSON fields only).
    """
    reduced = {k: v for k, v in request_payload_without_hash.items() if k != "request_hash"}
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
        estimated_record_count=0,
        estimated_billable_size=0,
        estimated_cost=_PLACEHOLDER_COST,
        currency="USD",
        request_hash="",
    )
    payload = request.model_dump(mode="json", by_alias=True)
    request_hash = compute_request_hash(payload)
    return request.model_copy(update={"request_hash": request_hash})


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


def plan_hash(requests: list[AcquisitionRequest]) -> str:
    """Return the SHA-256 hash over the canonical JSON of every request payload.

    Each request's own ``request_hash`` is included; the requests are sorted
    into the same deterministic order used by :func:`build_pilot_request_plan`
    so this value is stable across regenerations and independent of caller
    ordering.
    """
    ordered = sorted(requests, key=_sort_key)
    payloads = [r.model_dump(mode="json", by_alias=True) for r in ordered]
    canonical = canonical_dumps({"requests": payloads})
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
