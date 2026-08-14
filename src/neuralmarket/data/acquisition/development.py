"""Canonical Strategy-B development acquisition planning.

This module is fully offline. It freezes immutable research requirements from
accepted manifests/configuration and deliberately keeps mutable artifact reuse
and provider execution outside the canonical plan identity.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from neuralmarket.core.configuration import config_sha256
from neuralmarket.data.acquisition.calendar import full_day_range_window, quote_window
from neuralmarket.data.acquisition.configuration import (
    AcquisitionConfig,
    load_acquisition_config,
)
from neuralmarket.data.acquisition.contracts import AcquisitionPolicyManifest
from neuralmarket.data.acquisition.manifests import (
    parse_policy_manifest,
    verify_policy_hash,
    write_json,
)
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    compute_request_hash,
    compute_specification_hash,
    plan_hash,
    plan_hash_metadata,
    validate_canonical_pilot_plan,
    verify_final_request,
)
from neuralmarket.data.acquisition.strategies import STRATEGY_B
from neuralmarket.data.calendar import calendar_library_version, compute_splits, session_dates
from neuralmarket.data.configuration import load_data_config
from neuralmarket.data.contracts import AwareUTCDatetime
from neuralmarket.data.errors import PlanValidationError
from neuralmarket.data.manifests import (
    SourceManifest,
    SplitManifest,
    canonical_dumps,
    load_manifest,
    parse_source_manifest,
    parse_split_manifest,
    verify_manifest_hash,
)

_DEVELOPMENT_PLAN_VERSION: Literal["1.0"] = "1.0"
_PLAN_KIND: Literal["development_acquisition"] = "development_acquisition"
_STRATEGY_RULE = "XNYS Tuesday and Thursday development sessions; non-sessions omitted, not shifted"
_QUOTE_WINDOW_RULE = (
    "final 10 minutes before the scheduled XNYS session close, timezone-aware UTC, "
    "half-open [start, end_exclusive)"
)
TIMESTAMP_POLICY = (
    "Future close/snapshot construction must use raw DBN ts_recv as authoritative "
    "observation time. Normalized ts_event is not a receive-time fallback."
)
_STYPE_OUT = "instrument_id"
_SPLIT_ORDER = {"training": 0, "validation": 1}
_WAVE_ORDER = {
    "arcx_catalog": 0,
    "arcx_underlying": 1,
    "opra_definitions": 2,
    "opra_closing_quotes": 3,
}
_NEW_PROVIDER_ELIGIBLE_PILOT_STATES = frozenset(
    {
        "not_started",
        "planned",
        "preflight_validated",
        "retry_eligible_after_manual_nonbilling_confirmation",
    }
)

DevelopmentSplit = Literal["training", "validation"]
DevelopmentPurpose = Literal[
    "underlying_definition",
    "underlying_daily_reference",
    "underlying_statistics",
    "option_definitions",
    "strategy_b_closing_quote",
]


class DevelopmentRequest(BaseModel):
    """One immutable provider request in the Strategy-B development plan."""

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
    expected_split: DevelopmentSplit
    session_date: date | None
    calendar: str
    logical_output_path: str
    specification_hash: str
    estimated_record_count: int | None
    estimated_billable_size: int | None
    estimated_cost: str | None
    currency: Literal["USD"]
    estimate_timestamp: AwareUTCDatetime | None
    estimate_method: str | None
    estimate_response_hash: str | None
    request_hash: str
    purpose: DevelopmentPurpose
    raw_dbn_retention_required: bool
    observation_time_source: Literal["ts_recv"] | None
    normalized_event_time_receive_fallback_allowed: Literal[False] = False

    @model_validator(mode="after")
    def _validate_development_semantics(self) -> DevelopmentRequest:
        if self.start >= self.end_exclusive:
            raise ValueError("request start must precede end_exclusive")
        is_cbbo = self.schema_name == "cbbo-1m"
        if is_cbbo:
            if self.wave != "opra_closing_quotes" or self.purpose != "strategy_b_closing_quote":
                raise ValueError("cbbo-1m requires the Strategy-B closing-quote purpose")
            if self.session_date is None:
                raise ValueError("cbbo-1m requires session_date")
            if not self.raw_dbn_retention_required:
                raise ValueError("cbbo-1m requires raw DBN retention")
            if self.observation_time_source != "ts_recv":
                raise ValueError("cbbo-1m observation time must be ts_recv")
            if (self.end_exclusive - self.start).total_seconds() != 600:
                raise ValueError("cbbo-1m quote window must be exactly ten minutes")
        elif self.session_date is not None:
            raise ValueError("catalog/reference range requests must not carry session_date")
        elif self.observation_time_source is not None:
            raise ValueError("catalog/reference requests have no observation_time_source")
        return self


class DevelopmentPlanBindings(BaseModel):
    """Frozen dependency hashes covered by the development plan identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_manifest_hash: str
    split_manifest_hash: str
    acquisition_policy_hash: str
    acquisition_config_hash: str
    data_config_hash: str


class DevelopmentPlan(BaseModel):
    """Canonical immutable Strategy-B development research plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: Literal["1.0"] = _DEVELOPMENT_PLAN_VERSION
    plan_kind: Literal["development_acquisition"] = _PLAN_KIND
    strategy_id: Literal["B"] = "B"
    strategy_rule: str
    quote_window_rule: str
    timestamp_policy: str
    bindings: DevelopmentPlanBindings
    logical_requirement_count: int = Field(ge=0)
    catalog_request_count: int = Field(ge=0)
    cbbo_request_count: int = Field(ge=0)
    training_session_count: int = Field(ge=0)
    validation_session_count: int = Field(ge=0)
    duplicate_request_count: int = Field(ge=0)
    sealed_test_overlap_count: int = Field(ge=0)
    excluded_boundary_overlap_count: int = Field(ge=0)
    requests: tuple[DevelopmentRequest, ...]
    plan_hash: str

    @model_validator(mode="after")
    def _validate_shape(self) -> DevelopmentPlan:
        catalog = [request for request in self.requests if request.schema_name != "cbbo-1m"]
        cbbo = [request for request in self.requests if request.schema_name == "cbbo-1m"]
        request_ids = [request.request_id for request in self.requests]
        specification_hashes = [request.specification_hash for request in self.requests]
        request_hashes = [request.request_hash for request in self.requests]
        paths = [request.logical_output_path.lower() for request in self.requests]
        duplicates = sum(
            len(values) - len(set(values))
            for values in (request_ids, specification_hashes, request_hashes, paths)
        )
        if duplicates:
            raise ValueError("development plan contains duplicate request identity")
        if self.duplicate_request_count != 0:
            raise ValueError("duplicate_request_count must be zero")
        if self.logical_requirement_count != len(self.requests):
            raise ValueError("logical_requirement_count does not match requests")
        if self.catalog_request_count != len(catalog):
            raise ValueError("catalog_request_count does not match requests")
        if self.cbbo_request_count != len(cbbo):
            raise ValueError("cbbo_request_count does not match requests")
        training = sum(request.expected_split == "training" for request in cbbo)
        validation = sum(request.expected_split == "validation" for request in cbbo)
        if self.training_session_count != training or self.validation_session_count != validation:
            raise ValueError("Strategy-B split counts do not match requests")
        if (
            self.logical_requirement_count != 499
            or self.catalog_request_count != 8
            or self.cbbo_request_count != 491
            or self.training_session_count != 377
            or self.validation_session_count != 114
        ):
            raise ValueError("development plan is not the frozen Strategy-B shape")
        if self.sealed_test_overlap_count or self.excluded_boundary_overlap_count:
            raise ValueError("development plan overlaps a forbidden split")
        return self


def _development_sort_key(request: DevelopmentRequest) -> tuple[Any, ...]:
    return (
        _WAVE_ORDER[request.wave],
        _SPLIT_ORDER[request.expected_split],
        request.session_date or date.min,
        request.dataset,
        request.schema_name,
        request.purpose,
        request.symbols,
        request.start,
        request.end_exclusive,
    )


def _request_identity_payload(
    *,
    wave: str,
    purpose: str,
    dataset: str,
    schema_name: str,
    symbols: tuple[str, ...],
    stype_in: str,
    start: datetime,
    end_exclusive: datetime,
    expected_split: str,
    session_date: date | None,
    calendar_name: str,
    raw_dbn_retention_required: bool,
    observation_time_source: str | None,
) -> dict[str, Any]:
    return {
        "wave": wave,
        "purpose": purpose,
        "dataset": dataset,
        "schema": schema_name,
        "symbols": list(symbols),
        "stype_in": stype_in,
        "stype_out": _STYPE_OUT,
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "encoding": "dbn",
        "compression": "zstd",
        "expected_split": expected_split,
        "session_date": session_date.isoformat() if session_date else None,
        "calendar": calendar_name,
        "raw_dbn_retention_required": raw_dbn_retention_required,
        "observation_time_source": observation_time_source,
        "normalized_event_time_receive_fallback_allowed": False,
    }


def _request_id(identity: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_dumps(identity).encode("utf-8")).hexdigest()[:16]


def build_development_request(
    *,
    wave: Literal["arcx_catalog", "arcx_underlying", "opra_definitions", "opra_closing_quotes"],
    purpose: DevelopmentPurpose,
    dataset: str,
    schema_name: str,
    symbols: tuple[str, ...],
    stype_in: str,
    window: tuple[datetime, datetime],
    expected_split: DevelopmentSplit,
    session_date: date | None,
    calendar_name: str,
    raw_dbn_retention_required: bool,
    observation_time_source: Literal["ts_recv"] | None,
) -> DevelopmentRequest:
    """Build and self-hash one machine-neutral development request."""
    start, end_exclusive = window
    identity = _request_identity_payload(
        wave=wave,
        purpose=purpose,
        dataset=dataset,
        schema_name=schema_name,
        symbols=symbols,
        stype_in=stype_in,
        start=start,
        end_exclusive=end_exclusive,
        expected_split=expected_split,
        session_date=session_date,
        calendar_name=calendar_name,
        raw_dbn_retention_required=raw_dbn_retention_required,
        observation_time_source=observation_time_source,
    )
    request_id = _request_id(identity)
    if session_date is not None:
        partition = f"session_date={session_date.isoformat()}"
    else:
        partition = (
            f"start_date={start.date().isoformat()}/"
            f"end_exclusive_date={end_exclusive.date().isoformat()}"
        )
    logical_output_path = (
        "data/raw/databento/development_strategy_b/"
        f"{expected_split}/{dataset}/{schema_name}/{partition}/{request_id}.dbn"
    )
    request = DevelopmentRequest(
        request_id=request_id,
        wave=wave,
        purpose=purpose,
        dataset=dataset,
        schema=schema_name,
        symbols=symbols,
        stype_in=stype_in,
        stype_out=_STYPE_OUT,
        start=start,
        end_exclusive=end_exclusive,
        encoding="dbn",
        compression="zstd",
        expected_split=expected_split,
        session_date=session_date,
        calendar=calendar_name,
        logical_output_path=logical_output_path,
        specification_hash="",
        estimated_record_count=None,
        estimated_billable_size=None,
        estimated_cost=None,
        currency="USD",
        estimate_timestamp=None,
        estimate_method=None,
        estimate_response_hash=None,
        request_hash="",
        raw_dbn_retention_required=raw_dbn_retention_required,
        observation_time_source=observation_time_source,
        normalized_event_time_receive_fallback_allowed=False,
    )
    specification_hash = compute_specification_hash(request.model_dump(mode="json", by_alias=True))
    specified = request.model_copy(update={"specification_hash": specification_hash})
    request_hash = compute_request_hash(specified.model_dump(mode="json", by_alias=True))
    return specified.model_copy(update={"request_hash": request_hash})


def _plan_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"bindings", "requests", "plan_hash"}
    }


def _compute_development_plan_hash(
    requests: list[DevelopmentRequest],
    bindings: DevelopmentPlanBindings,
    metadata: dict[str, Any],
) -> str:
    ordered = sorted(requests, key=_development_sort_key)
    return plan_hash(
        cast(list[AcquisitionRequest], ordered),
        bindings.model_dump(mode="json"),
        metadata,
    )


def _load_dependencies(
    *,
    acquisition_config_path: Path,
    data_config_path: Path,
    source_manifest_path: Path,
    split_manifest_path: Path,
    policy_manifest_path: Path,
) -> tuple[
    AcquisitionConfig,
    SourceManifest,
    SplitManifest,
    AcquisitionPolicyManifest,
    DevelopmentPlanBindings,
]:
    acquisition_config = load_acquisition_config(acquisition_config_path)
    data_config = load_data_config(data_config_path)

    source_payload = load_manifest(source_manifest_path)
    split_payload = load_manifest(split_manifest_path)
    policy_payload = load_manifest(policy_manifest_path)
    verify_manifest_hash(source_payload)
    verify_manifest_hash(split_payload)
    verify_policy_hash(policy_payload)
    source = parse_source_manifest(source_payload)
    split = parse_split_manifest(split_payload)
    policy = parse_policy_manifest(policy_payload)

    acquisition_hash = config_sha256(acquisition_config_path)
    data_hash = config_sha256(data_config_path)
    if source.config_hash != data_hash or split.config_hash != data_hash:
        raise PlanValidationError("source/split manifests are not bound to the data config")
    if policy.config_hash != acquisition_hash:
        raise PlanValidationError("acquisition policy is not bound to the acquisition config")
    if (
        policy.source_manifest_hash != source.manifest_hash
        or policy.split_manifest_hash != split.manifest_hash
    ):
        raise PlanValidationError("acquisition policy dependency hash mismatch")
    if source.qualification_status != "qualified":
        raise PlanValidationError("source manifest is not qualified")
    if split.final_test_access_status != "sealed":
        raise PlanValidationError("final test must remain sealed")
    if policy.recommended_strategy_id != STRATEGY_B:
        raise PlanValidationError("acquisition policy does not freeze Strategy B")
    if policy.recommendation_status != "recommended_not_authorized":
        raise PlanValidationError("Strategy B must remain recommended and unauthorized")
    if policy.purchase_authorized or not policy.download_guard_enabled:
        raise PlanValidationError("acquisition policy must remain guarded and unauthorized")

    if calendar_library_version() != split.calendar_library_version:
        raise PlanValidationError("calendar library version does not match the split manifest")
    if (
        data_config.study.calendar != split.calendar_name
        or data_config.study.timezone != split.calendar_timezone
        or data_config.study.start_date != split.study_start
        or data_config.study.end_date != split.study_end
    ):
        raise PlanValidationError("data config calendar does not match the split manifest")
    all_sessions = session_dates(split.calendar_name, split.study_start, split.study_end)
    computed = compute_splits(data_config, all_sessions)
    computed_identity = (
        computed.training_start,
        computed.training_end,
        computed.validation_start,
        computed.validation_end,
        computed.test_start,
        computed.test_end,
        computed.training_sessions,
        computed.validation_sessions,
        computed.test_sessions,
        computed.training_hash,
        computed.validation_hash,
        computed.test_hash,
        computed.calendar_hash,
        tuple(
            (item.start_date, item.end_date, item.session_count, item.session_hash)
            for item in computed.boundary_exclusions
        ),
    )
    manifest_identity = (
        split.training_start,
        split.training_end,
        split.validation_start,
        split.validation_end,
        split.test_start,
        split.test_end,
        split.training_sessions,
        split.validation_sessions,
        split.test_sessions,
        split.training_hash,
        split.validation_hash,
        split.test_hash,
        split.calendar_hash,
        tuple(
            (item.start_date, item.end_date, item.session_count, item.session_hash)
            for item in split.excluded_boundary_ranges
        ),
    )
    if computed_identity != manifest_identity:
        raise PlanValidationError("current calendar does not reproduce the split manifest")

    bindings = DevelopmentPlanBindings(
        source_manifest_hash=source.manifest_hash,
        split_manifest_hash=split.manifest_hash,
        acquisition_policy_hash=policy.manifest_hash,
        acquisition_config_hash=acquisition_hash,
        data_config_hash=data_hash,
    )
    return acquisition_config, source, split, policy, bindings


def _catalog_requests(
    config: AcquisitionConfig,
    split: SplitManifest,
) -> list[DevelopmentRequest]:
    products: tuple[tuple[str, DevelopmentPurpose, str, str, tuple[str, ...], str], ...] = (
        (
            "arcx_catalog",
            "underlying_definition",
            config.underlying.dataset,
            config.underlying.definition_schema,
            (config.underlying.symbol,),
            config.underlying.symbol_type,
        ),
        (
            "arcx_underlying",
            "underlying_daily_reference",
            config.underlying.dataset,
            config.underlying.daily_schema,
            (config.underlying.symbol,),
            config.underlying.symbol_type,
        ),
        (
            "arcx_underlying",
            "underlying_statistics",
            config.underlying.dataset,
            config.underlying.statistics_schema,
            (config.underlying.symbol,),
            config.underlying.symbol_type,
        ),
        (
            "opra_definitions",
            "option_definitions",
            config.options.dataset,
            config.options.definition_schema,
            (config.options.parent_symbol,),
            config.options.symbol_type,
        ),
    )
    periods: tuple[tuple[DevelopmentSplit, date, date], ...] = (
        ("training", split.training_start, split.training_end),
        ("validation", split.validation_start, split.validation_end),
    )
    requests: list[DevelopmentRequest] = []
    for expected_split, start, end in periods:
        window = full_day_range_window(start, end)
        for wave, purpose, dataset, schema_name, symbols, stype_in in products:
            requests.append(
                build_development_request(
                    wave=cast(Any, wave),
                    purpose=purpose,
                    dataset=dataset,
                    schema_name=schema_name,
                    symbols=symbols,
                    stype_in=stype_in,
                    window=window,
                    expected_split=expected_split,
                    session_date=None,
                    calendar_name=split.calendar_name,
                    raw_dbn_retention_required=True,
                    observation_time_source=None,
                )
            )
    return requests


def _quote_requests(
    config: AcquisitionConfig,
    split: SplitManifest,
) -> tuple[list[DevelopmentRequest], list[date], list[date]]:
    from neuralmarket.data.acquisition.calendar import twice_weekly_schedule

    training = session_dates(split.calendar_name, split.training_start, split.training_end)
    validation = session_dates(split.calendar_name, split.validation_start, split.validation_end)
    all_sessions = sorted(set(training) | set(validation))
    schedule = twice_weekly_schedule(all_sessions)
    training_set = set(training)
    validation_set = set(validation)
    requests: list[DevelopmentRequest] = []
    for session in schedule:
        if session in training_set:
            expected_split: DevelopmentSplit = "training"
        elif session in validation_set:
            expected_split = "validation"
        else:  # pragma: no cover - schedule is built only from these exact sets
            raise PlanValidationError(f"Strategy-B session outside development splits: {session}")
        requests.append(
            build_development_request(
                wave="opra_closing_quotes",
                purpose="strategy_b_closing_quote",
                dataset=config.options.dataset,
                schema_name=config.options.quote_schema,
                symbols=(config.options.parent_symbol,),
                stype_in=config.options.symbol_type,
                window=quote_window(split.calendar_name, session),
                expected_split=expected_split,
                session_date=session,
                calendar_name=split.calendar_name,
                raw_dbn_retention_required=True,
                observation_time_source="ts_recv",
            )
        )
    return requests, training, validation


def build_development_plan_from_files(
    *,
    acquisition_config_path: Path,
    data_config_path: Path,
    source_manifest_path: Path,
    split_manifest_path: Path,
    policy_manifest_path: Path,
) -> DevelopmentPlan:
    """Build the exact canonical Strategy-B plan without provider construction."""
    config, _source, split, _policy, bindings = _load_dependencies(
        acquisition_config_path=acquisition_config_path,
        data_config_path=data_config_path,
        source_manifest_path=source_manifest_path,
        split_manifest_path=split_manifest_path,
        policy_manifest_path=policy_manifest_path,
    )
    catalog = _catalog_requests(config, split)
    quotes, training, validation = _quote_requests(config, split)
    ordered = sorted([*catalog, *quotes], key=_development_sort_key)

    excluded_overlap = sum(
        any(
            excluded.start_date <= request.session_date <= excluded.end_date
            for excluded in split.excluded_boundary_ranges
        )
        for request in quotes
        if request.session_date is not None
    )
    sealed_overlap = sum(
        split.test_start <= request.session_date <= split.test_end
        for request in quotes
        if request.session_date is not None
    )
    duplicate_count = len(ordered) - len({request.request_id for request in ordered})
    payload: dict[str, Any] = {
        "manifest_version": _DEVELOPMENT_PLAN_VERSION,
        "plan_kind": _PLAN_KIND,
        "strategy_id": STRATEGY_B,
        "strategy_rule": _STRATEGY_RULE,
        "quote_window_rule": _QUOTE_WINDOW_RULE,
        "timestamp_policy": TIMESTAMP_POLICY,
        "bindings": bindings.model_dump(mode="json"),
        "logical_requirement_count": len(ordered),
        "catalog_request_count": len(catalog),
        "cbbo_request_count": len(quotes),
        "training_session_count": sum(request.expected_split == "training" for request in quotes),
        "validation_session_count": sum(
            request.expected_split == "validation" for request in quotes
        ),
        "duplicate_request_count": duplicate_count,
        "sealed_test_overlap_count": sealed_overlap,
        "excluded_boundary_overlap_count": excluded_overlap,
        "requests": [request.model_dump(mode="json", by_alias=True) for request in ordered],
    }
    payload["plan_hash"] = _compute_development_plan_hash(
        ordered,
        bindings,
        _plan_metadata(payload),
    )
    plan = DevelopmentPlan.model_validate(payload)
    if len(training) != split.training_sessions or len(validation) != split.validation_sessions:
        raise PlanValidationError("split session counts do not match the frozen split manifest")
    return plan


def verify_development_request(request: DevelopmentRequest) -> None:
    """Reject any request whose ID, specification hash, or request hash was changed."""
    payload = request.model_dump(mode="json", by_alias=True)
    if compute_specification_hash(payload) != request.specification_hash:
        raise PlanValidationError(
            f"development request specification hash mismatch: {request.request_id}"
        )
    if compute_request_hash(payload) != request.request_hash:
        raise PlanValidationError(f"development request hash mismatch: {request.request_id}")
    identity = _request_identity_payload(
        wave=request.wave,
        purpose=request.purpose,
        dataset=request.dataset,
        schema_name=request.schema_name,
        symbols=request.symbols,
        stype_in=request.stype_in,
        start=request.start,
        end_exclusive=request.end_exclusive,
        expected_split=request.expected_split,
        session_date=request.session_date,
        calendar_name=request.calendar,
        raw_dbn_retention_required=request.raw_dbn_retention_required,
        observation_time_source=request.observation_time_source,
    )
    if _request_id(identity) != request.request_id:
        raise PlanValidationError(f"development request ID mismatch: {request.request_id}")


def verify_development_plan_from_files(
    plan: DevelopmentPlan,
    *,
    acquisition_config_path: Path,
    data_config_path: Path,
    source_manifest_path: Path,
    split_manifest_path: Path,
    policy_manifest_path: Path,
) -> None:
    """Fail closed unless a plan exactly matches all frozen dependencies."""
    if plan.logical_requirement_count != len(plan.requests):
        raise PlanValidationError("development plan request count mismatch")
    for request in plan.requests:
        verify_development_request(request)
    payload = plan.model_dump(mode="json", by_alias=True)
    recomputed = _compute_development_plan_hash(
        list(plan.requests),
        plan.bindings,
        _plan_metadata(payload),
    )
    if recomputed != plan.plan_hash:
        raise PlanValidationError("development plan hash mismatch")
    expected = build_development_plan_from_files(
        acquisition_config_path=acquisition_config_path,
        data_config_path=data_config_path,
        source_manifest_path=source_manifest_path,
        split_manifest_path=split_manifest_path,
        policy_manifest_path=policy_manifest_path,
    )
    if plan.model_dump(mode="json", by_alias=True) != expected.model_dump(
        mode="json", by_alias=True
    ):
        raise PlanValidationError("development plan does not match the canonical Strategy-B plan")


def write_development_plan(path: Path, plan: DevelopmentPlan) -> None:
    """Atomically write a canonical development plan as stable sorted JSON."""
    write_json(path, plan.model_dump(mode="json", by_alias=True), compact=True)


def load_development_plan(path: Path) -> DevelopmentPlan:
    """Load and self-verify a development plan without external I/O."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        plan = DevelopmentPlan.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PlanValidationError(f"invalid development plan: {exc}") from exc
    for request in plan.requests:
        verify_development_request(request)
    recomputed = _compute_development_plan_hash(
        list(plan.requests),
        plan.bindings,
        _plan_metadata(plan.model_dump(mode="json", by_alias=True)),
    )
    if recomputed != plan.plan_hash:
        raise PlanValidationError("development plan hash mismatch")
    return plan


class PilotJournalState(BaseModel):
    """Read-only pilot state needed to classify exact development overlaps."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    request_hash: str
    state: str
    raw_path: str | None = None
    raw_checksum: str | None
    normalized_path: str | None = None
    normalized_checksum: str | None


class DevelopmentDisposition(BaseModel):
    """One explicit reusable or unavailable canonical development requirement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    development_request_id: str
    development_request_hash: str
    disposition: Literal["reusable", "unavailable"]
    source_kind: Literal["pilot", "development"]
    source_request_id: str
    source_request_hash: str
    source_state: str
    raw_artifact_path: str | None
    raw_checksum: str | None
    normalized_artifact_path: str | None
    normalized_checksum: str | None
    quality_report_path: str | None

    @model_validator(mode="after")
    def _validate_artifact_evidence(self) -> DevelopmentDisposition:
        evidence = (
            self.raw_artifact_path,
            self.raw_checksum,
            self.normalized_artifact_path,
            self.normalized_checksum,
            self.quality_report_path,
        )
        if self.disposition == "reusable" and any(value is None for value in evidence):
            raise ValueError("reusable disposition requires complete artifact evidence")
        if self.disposition == "unavailable" and any(
            value is not None
            for value in (
                self.raw_artifact_path,
                self.raw_checksum,
                self.normalized_artifact_path,
                self.normalized_checksum,
                self.quality_report_path,
            )
        ):
            raise ValueError("unavailable disposition must not claim validated artifacts")
        return self


class PilotDispositionResult(BaseModel):
    """Exact pilot overlap classifications plus unrelated quarantined IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dispositions: tuple[DevelopmentDisposition, ...]
    other_quarantined_request_ids: tuple[str, ...]


class DevelopmentRequestScope(BaseModel):
    """Current mutable provider scope derived from one immutable development plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_version: Literal["1.0"] = "1.0"
    source_plan_hash: str
    derivation_rule: Literal["canonical_plan_minus_exact_dispositions"] = (
        "canonical_plan_minus_exact_dispositions"
    )
    canonical_request_count: int = Field(ge=0)
    new_request_count: int = Field(ge=0)
    new_catalog_request_count: int = Field(ge=0)
    new_cbbo_request_count: int = Field(ge=0)
    reusable_request_count: int = Field(ge=0)
    unavailable_request_count: int = Field(ge=0)
    duplicate_request_count: int = Field(ge=0)
    reusable: tuple[DevelopmentDisposition, ...]
    unavailable: tuple[DevelopmentDisposition, ...]
    other_quarantined_source_request_ids: tuple[str, ...]
    requests: tuple[DevelopmentRequest, ...]
    scope_hash: str

    @model_validator(mode="after")
    def _validate_scope_shape(self) -> DevelopmentRequestScope:
        new_ids = [request.request_id for request in self.requests]
        reusable_ids = [item.development_request_id for item in self.reusable]
        unavailable_ids = [item.development_request_id for item in self.unavailable]
        all_disposition_ids = [*reusable_ids, *unavailable_ids]
        duplicate_count = (len(new_ids) - len(set(new_ids))) + (
            len(all_disposition_ids) - len(set(all_disposition_ids))
        )
        if duplicate_count or self.duplicate_request_count:
            raise ValueError("development scope contains duplicate request identity")
        if set(new_ids) & set(all_disposition_ids):
            raise ValueError("new requests overlap reusable or unavailable requirements")
        if self.new_request_count != len(self.requests):
            raise ValueError("new_request_count does not match requests")
        catalog = sum(request.schema_name != "cbbo-1m" for request in self.requests)
        cbbo = sum(request.schema_name == "cbbo-1m" for request in self.requests)
        if self.new_catalog_request_count != catalog or self.new_cbbo_request_count != cbbo:
            raise ValueError("new request breakdown does not match requests")
        if self.reusable_request_count != len(self.reusable):
            raise ValueError("reusable_request_count does not match bindings")
        if self.unavailable_request_count != len(self.unavailable):
            raise ValueError("unavailable_request_count does not match bindings")
        if self.canonical_request_count != (
            self.new_request_count + self.reusable_request_count + self.unavailable_request_count
        ):
            raise ValueError("scope dispositions do not account for the canonical plan")
        if any(item.disposition != "reusable" for item in self.reusable):
            raise ValueError("reusable list contains another disposition")
        if any(item.disposition != "unavailable" for item in self.unavailable):
            raise ValueError("unavailable list contains another disposition")
        return self


def _provider_semantic_key(request: Any) -> tuple[Any, ...]:
    return (
        request.dataset,
        request.schema_name,
        tuple(request.symbols),
        request.stype_in,
        request.stype_out,
        request.start,
        request.end_exclusive,
        request.encoding,
        request.compression,
        request.session_date,
        request.calendar,
    )


def _verified_artifact(
    value: str | None,
    expected_checksum: str | None,
    *,
    repository_root: Path,
    label: str,
) -> tuple[Path, str]:
    if value is None or expected_checksum is None:
        raise PlanValidationError(f"quality-validated pilot request lacks {label} evidence")
    root = repository_root.resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root).as_posix()
    except (FileNotFoundError, ValueError) as exc:
        raise PlanValidationError(f"{label} is missing or outside the repository: {value}") from exc
    actual_checksum = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if actual_checksum != expected_checksum:
        raise PlanValidationError(f"{label} checksum mismatch: {relative}")
    return resolved, relative


def _verify_reusable_disposition(
    disposition: DevelopmentDisposition,
    *,
    repository_root: Path,
) -> DevelopmentDisposition:
    """Verify reusable artifact bytes and quality provenance at the scope boundary."""
    _, raw_relative = _verified_artifact(
        disposition.raw_artifact_path,
        disposition.raw_checksum,
        repository_root=repository_root,
        label="raw artifact",
    )
    normalized_path, normalized_relative = _verified_artifact(
        disposition.normalized_artifact_path,
        disposition.normalized_checksum,
        repository_root=repository_root,
        label="normalized artifact",
    )
    root = repository_root.resolve()
    if disposition.quality_report_path is None:
        raise PlanValidationError("reusable disposition lacks quality report evidence")
    quality_candidate = Path(disposition.quality_report_path)
    if not quality_candidate.is_absolute():
        quality_candidate = root / quality_candidate
    try:
        quality_path = quality_candidate.resolve(strict=True)
        quality_relative = quality_path.relative_to(root).as_posix()
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise PlanValidationError(
            "quality report is missing, invalid, or outside the repository"
        ) from exc
    quality_normalized = Path(str(quality.get("normalized_path", "")))
    if not quality_normalized.is_absolute():
        quality_normalized = root / quality_normalized
    if (
        quality.get("request_id") != disposition.source_request_id
        or quality.get("status") != "passed"
        or quality_normalized.resolve() != normalized_path
    ):
        raise PlanValidationError(f"quality report provenance mismatch: {quality_relative}")
    return disposition.model_copy(
        update={
            "raw_artifact_path": raw_relative,
            "normalized_artifact_path": normalized_relative,
            "quality_report_path": quality_relative,
        }
    )


def derive_pilot_development_dispositions(
    plan: DevelopmentPlan,
    pilot_requests: list[AcquisitionRequest],
    pilot_states: dict[str, PilotJournalState],
    *,
    repository_root: Path | None = None,
) -> PilotDispositionResult:
    """Classify only exact pilot request-semantic overlaps with the canonical plan."""
    canonical_by_semantics = {_provider_semantic_key(request): request for request in plan.requests}
    dispositions: list[DevelopmentDisposition] = []
    matched_source_ids: set[str] = set()
    for pilot in pilot_requests:
        development = canonical_by_semantics.get(_provider_semantic_key(pilot))
        state = pilot_states.get(pilot.request_id)
        if state is None:
            if development is not None:
                raise PlanValidationError(f"missing pilot journal state: {pilot.request_id}")
            continue
        if state.request_hash != pilot.request_hash:
            raise PlanValidationError(f"pilot journal request hash mismatch: {pilot.request_id}")
        if development is None:
            continue
        if state.state == "quality_validated":
            if repository_root is None:
                raise PlanValidationError(
                    "quality-validated pilot overlap requires artifact verification"
                )
            if any(
                value is None
                for value in (
                    state.raw_path,
                    state.raw_checksum,
                    state.normalized_path,
                    state.normalized_checksum,
                )
            ):
                raise PlanValidationError(
                    f"quality-validated pilot request lacks artifact evidence: {pilot.request_id}"
                )
            dispositions.append(
                _verify_reusable_disposition(
                    DevelopmentDisposition(
                        development_request_id=development.request_id,
                        development_request_hash=development.request_hash,
                        disposition="reusable",
                        source_kind="pilot",
                        source_request_id=pilot.request_id,
                        source_request_hash=pilot.request_hash,
                        source_state=state.state,
                        raw_artifact_path=state.raw_path,
                        raw_checksum=state.raw_checksum,
                        normalized_artifact_path=state.normalized_path,
                        normalized_checksum=state.normalized_checksum,
                        quality_report_path=f"reports/data/quality/{pilot.request_id}.json",
                    ),
                    repository_root=repository_root,
                )
            )
            matched_source_ids.add(pilot.request_id)
        elif state.state not in _NEW_PROVIDER_ELIGIBLE_PILOT_STATES:
            dispositions.append(
                DevelopmentDisposition(
                    development_request_id=development.request_id,
                    development_request_hash=development.request_hash,
                    disposition="unavailable",
                    source_kind="pilot",
                    source_request_id=pilot.request_id,
                    source_request_hash=pilot.request_hash,
                    source_state=state.state,
                    raw_artifact_path=None,
                    raw_checksum=None,
                    normalized_artifact_path=None,
                    normalized_checksum=None,
                    quality_report_path=None,
                )
            )
            matched_source_ids.add(pilot.request_id)

    order = {request.request_id: index for index, request in enumerate(plan.requests)}
    dispositions.sort(key=lambda item: order[item.development_request_id])
    other_quarantined = sorted(
        request_id
        for request_id, state in pilot_states.items()
        if state.state not in _NEW_PROVIDER_ELIGIBLE_PILOT_STATES
        and state.state != "quality_validated"
        and request_id not in matched_source_ids
    )
    return PilotDispositionResult(
        dispositions=tuple(dispositions),
        other_quarantined_request_ids=tuple(other_quarantined),
    )


def _scope_hash(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "scope_hash"}
    return hashlib.sha256(canonical_dumps(unsigned).encode("utf-8")).hexdigest()


def derive_current_development_scope(
    plan: DevelopmentPlan,
    dispositions: list[DevelopmentDisposition] | tuple[DevelopmentDisposition, ...],
    *,
    other_quarantined_source_request_ids: tuple[str, ...] | list[str] = (),
    repository_root: Path | None = None,
) -> DevelopmentRequestScope:
    """Subtract exact reusable/unavailable requirements from the canonical plan."""
    canonical = {request.request_id: request for request in plan.requests}
    disposition_ids = [item.development_request_id for item in dispositions]
    if len(disposition_ids) != len(set(disposition_ids)):
        raise PlanValidationError("duplicate development disposition")
    for item in dispositions:
        request = canonical.get(item.development_request_id)
        if request is None:
            raise PlanValidationError(
                f"disposition is not in canonical plan: {item.development_request_id}"
            )
        if request.request_hash != item.development_request_hash:
            raise PlanValidationError(
                f"disposition request hash mismatch: {item.development_request_id}"
            )
    if any(item.disposition == "reusable" for item in dispositions):
        if repository_root is None:
            raise PlanValidationError("reusable disposition requires artifact verification")
        dispositions = tuple(
            _verify_reusable_disposition(item, repository_root=repository_root)
            if item.disposition == "reusable"
            else item
            for item in dispositions
        )
    disposed = set(disposition_ids)
    new_requests = tuple(request for request in plan.requests if request.request_id not in disposed)
    order = {request.request_id: index for index, request in enumerate(plan.requests)}
    reusable = tuple(
        sorted(
            (item for item in dispositions if item.disposition == "reusable"),
            key=lambda item: order[item.development_request_id],
        )
    )
    unavailable = tuple(
        sorted(
            (item for item in dispositions if item.disposition == "unavailable"),
            key=lambda item: order[item.development_request_id],
        )
    )
    other_quarantined = tuple(sorted(set(other_quarantined_source_request_ids)))
    payload: dict[str, Any] = {
        "scope_version": "1.0",
        "source_plan_hash": plan.plan_hash,
        "derivation_rule": "canonical_plan_minus_exact_dispositions",
        "canonical_request_count": len(plan.requests),
        "new_request_count": len(new_requests),
        "new_catalog_request_count": sum(
            request.schema_name != "cbbo-1m" for request in new_requests
        ),
        "new_cbbo_request_count": sum(request.schema_name == "cbbo-1m" for request in new_requests),
        "reusable_request_count": len(reusable),
        "unavailable_request_count": len(unavailable),
        "duplicate_request_count": 0,
        "reusable": [item.model_dump(mode="json") for item in reusable],
        "unavailable": [item.model_dump(mode="json") for item in unavailable],
        "other_quarantined_source_request_ids": list(other_quarantined),
        "requests": [request.model_dump(mode="json", by_alias=True) for request in new_requests],
    }
    payload["scope_hash"] = _scope_hash(payload)
    return DevelopmentRequestScope.model_validate(payload)


def write_development_scope(path: Path, scope: DevelopmentRequestScope) -> None:
    """Atomically write a deterministic current development provider scope."""
    write_json(path, scope.model_dump(mode="json", by_alias=True))


def load_development_scope(
    path: Path,
    plan: DevelopmentPlan,
    *,
    repository_root: Path | None = None,
) -> DevelopmentRequestScope:
    """Load and verify a scope against its immutable canonical development plan."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        scope = DevelopmentRequestScope.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PlanValidationError(f"invalid development scope: {exc}") from exc
    if scope.source_plan_hash != plan.plan_hash:
        raise PlanValidationError("development scope is bound to a different plan")
    if _scope_hash(scope.model_dump(mode="json", by_alias=True)) != scope.scope_hash:
        raise PlanValidationError("development scope hash mismatch")
    expected = derive_current_development_scope(
        plan,
        [*scope.reusable, *scope.unavailable],
        other_quarantined_source_request_ids=scope.other_quarantined_source_request_ids,
        repository_root=repository_root,
    )
    if scope != expected:
        raise PlanValidationError("development scope does not match exact dispositions")
    return scope


def _journal_snapshot(path: Path) -> tuple[bytes, bool, int, bytes]:
    wal_path = path.with_name(f"{path.name}-wal")
    try:
        main_before = hashlib.sha256(path.read_bytes()).digest()
        wal_exists = wal_path.exists()
        wal = wal_path.read_bytes() if wal_exists else b""
        main_after = hashlib.sha256(path.read_bytes()).digest()
    except OSError as exc:
        raise PlanValidationError(f"unable to fingerprint pilot journal: {exc}") from exc
    if main_before != main_after:
        raise PlanValidationError("pilot journal changed during read-only scope derivation")
    return main_after, wal_exists, len(wal), hashlib.sha256(wal).digest()


@contextmanager
def _read_only_journal(path: Path) -> Iterator[sqlite3.Connection]:
    before = _journal_snapshot(path)
    if before[2]:
        raise PlanValidationError("pilot journal has uncheckpointed WAL state")
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro&immutable=1",
            uri=True,
        )
        yield connection
    except sqlite3.Error as exc:
        raise PlanValidationError(f"unable to read pilot journal: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
        if _journal_snapshot(path) != before:
            raise PlanValidationError("pilot journal changed during read-only scope derivation")


def load_pilot_journal_states(path: Path) -> dict[str, PilotJournalState]:
    """Read pilot state through immutable read-only SQLite without migrations/WAL."""
    with _read_only_journal(path) as database:
        rows = database.execute(
            """
            SELECT request_id, request_hash, state, raw_path, raw_checksum,
                   normalized_path, normalized_checksum
            FROM requests
            ORDER BY request_id
            """
        ).fetchall()
    states = [
        PilotJournalState(
            request_id=str(request_id),
            request_hash=str(request_hash),
            state=str(state),
            raw_path=str(raw_path) if raw_path is not None else None,
            raw_checksum=str(raw_checksum) if raw_checksum is not None else None,
            normalized_path=str(normalized_path) if normalized_path is not None else None,
            normalized_checksum=(
                str(normalized_checksum) if normalized_checksum is not None else None
            ),
        )
        for (
            request_id,
            request_hash,
            state,
            raw_path,
            raw_checksum,
            normalized_path,
            normalized_checksum,
        ) in rows
    ]
    return {state.request_id: state for state in states}


def load_finalized_pilot_requests(path: Path) -> list[AcquisitionRequest]:
    """Load and fully verify the accepted finalized pilot request manifest."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        requests = [AcquisitionRequest.model_validate(item) for item in payload["requests"]]
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        raise PlanValidationError(f"invalid pilot request plan: {exc}") from exc
    for request in requests:
        verify_final_request(request)
    validate_canonical_pilot_plan(requests)
    computed = plan_hash(
        requests,
        payload.get("bindings", {}),
        plan_hash_metadata(payload),
    )
    if computed != payload.get("plan_hash"):
        raise PlanValidationError("pilot request plan hash mismatch")
    return requests


def derive_current_development_scope_from_pilot(
    plan: DevelopmentPlan,
    *,
    pilot_plan_path: Path,
    pilot_journal_path: Path,
) -> DevelopmentRequestScope:
    """Derive the exact current provider scope from accepted pilot state."""
    journal_before = _journal_snapshot(pilot_journal_path)
    try:
        pilot_requests = load_finalized_pilot_requests(pilot_plan_path)
        pilot_states = load_pilot_journal_states(pilot_journal_path)
        result = derive_pilot_development_dispositions(
            plan,
            pilot_requests,
            pilot_states,
            repository_root=pilot_plan_path.resolve().parents[2],
        )
        return derive_current_development_scope(
            plan,
            result.dispositions,
            other_quarantined_source_request_ids=result.other_quarantined_request_ids,
            repository_root=pilot_plan_path.resolve().parents[2],
        )
    finally:
        if _journal_snapshot(pilot_journal_path) != journal_before:
            raise PlanValidationError("pilot journal changed during read-only scope derivation")
