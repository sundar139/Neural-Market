"""Plan-bound provider execution fragments for paid Strategy-B development acquisition.

The canonical :class:`DevelopmentPlan` freezes 499 scientific logical
requirements and must never change.  This module adds a *separate*, deterministic
execution layer: a :class:`DevelopmentExecutionManifest` that maps canonical
logical requests onto provider execution requests (fragments), so oversized
logical requirements can be executed as many independently quoted, individually
capped provider requests while the scientific plan stays byte-identical.

Everything here is offline and provider-free by construction.  Fresh provider
quotes for fragments are required before any execution scope becomes
authorization-ready.
"""

from __future__ import annotations

import hashlib
import itertools
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from neuralmarket.data.acquisition.development import (
    DevelopmentPlan,
    DevelopmentRequest,
    DevelopmentSplit,
)
from neuralmarket.data.acquisition.manifests import (
    load_json,
    write_json,
)
from neuralmarket.data.acquisition.requests import (
    compute_request_hash,
    compute_specification_hash,
)
from neuralmarket.data.contracts import AwareUTCDatetime
from neuralmarket.data.manifests import canonical_dumps

_FRAGMENTATION_POLICY: Literal["development-fragmentation-v1"] = "development-fragmentation-v1"
_EXECUTION_MANIFEST_KIND: Literal["development_execution"] = "development_execution"
_EXECUTION_MANIFEST_VERSION: Literal["1.0"] = "1.0"
_STYPE_OUT = "instrument_id"
_ONE_USD = Decimal("1.00")


class DevelopmentExecutionError(ValueError):
    """A development execution trust boundary or evidence invariant failed."""


def _require_sha256(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DevelopmentExecutionError(f"{label} must be a 64-character hex SHA-256")


def _strict_decimal_string(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} is not a valid decimal") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return parsed


def _execution_identity_payload(
    *,
    parent_request_id: str,
    fragment_index: int,
    fragment_count: int,
    wave: str,
    purpose: str,
    dataset: str,
    schema_name: str,
    symbols: tuple[str, ...],
    stype_in: str,
    start: datetime,
    end_exclusive: datetime,
    expected_split: str,
    session_date: str | None,
    calendar_name: str,
    raw_dbn_retention_required: bool,
    observation_time_source: str | None,
) -> dict[str, Any]:
    return {
        "parent_request_id": parent_request_id,
        "fragment_index": fragment_index,
        "fragment_count": fragment_count,
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
        "session_date": session_date,
        "calendar": calendar_name,
        "raw_dbn_retention_required": raw_dbn_retention_required,
        "observation_time_source": observation_time_source,
        "normalized_event_time_receive_fallback_allowed": False,
    }


def _execution_request_id(identity: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_dumps(identity).encode("utf-8")).hexdigest()[:16]


def _logical_output_path(request: DevelopmentRequest, execution_request_id: str) -> str:
    if request.session_date is not None:
        partition = f"session_date={request.session_date.isoformat()}"
    else:
        partition = (
            f"start_date={request.start.date().isoformat()}/"
            f"end_exclusive_date={request.end_exclusive.date().isoformat()}"
        )
    return (
        "data/raw/databento/development_strategy_b/"
        f"{request.expected_split}/{request.dataset}/{request.schema_name}/"
        f"{partition}/{execution_request_id}.dbn"
    )


def _month_boundaries(start: datetime, end_exclusive: datetime) -> list[tuple[datetime, datetime]]:
    """Return calendar-month windows clipped to ``[start, end_exclusive)``."""
    if start.tzinfo is None or end_exclusive.tzinfo is None:
        raise DevelopmentExecutionError("fragment windows require timezone-aware bounds")
    current = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    windows: list[tuple[datetime, datetime]] = []
    while current < end_exclusive:
        if current.month == 12:
            following = current.replace(year=current.year + 1, month=1, day=1)
        else:
            following = current.replace(month=current.month + 1, day=1)
        lower = max(start, current)
        upper = min(end_exclusive, following)
        if lower < upper:
            windows.append((lower, upper))
        current = following
    return windows


def _recompute_execution_hashes(payload: dict[str, Any]) -> tuple[str, str, str]:
    identity = _execution_identity_payload(
        parent_request_id=str(payload["parent_request_id"]),
        fragment_index=int(payload["fragment_index"]),
        fragment_count=int(payload["fragment_count"]),
        wave=str(payload["wave"]),
        purpose=str(payload["purpose"]),
        dataset=str(payload["dataset"]),
        schema_name=str(payload["schema"]),
        symbols=tuple(str(item) for item in payload["symbols"]),
        stype_in=str(payload["stype_in"]),
        start=datetime.fromisoformat(str(payload["start"])),
        end_exclusive=datetime.fromisoformat(str(payload["end_exclusive"])),
        expected_split=str(payload["expected_split"]),
        session_date=str(payload["session_date"]) if payload.get("session_date") else None,
        calendar_name=str(payload["calendar"]),
        raw_dbn_retention_required=bool(payload["raw_dbn_retention_required"]),
        observation_time_source=payload.get("observation_time_source"),
    )
    execution_request_id = _execution_request_id(identity)
    hashable = dict(payload)
    hashable["execution_request_id"] = ""
    hashable["execution_specification_hash"] = ""
    hashable["execution_request_hash"] = ""
    hashable["logical_output_path"] = ""
    hashable["start"] = datetime.fromisoformat(str(payload["start"])).isoformat()
    hashable["end_exclusive"] = datetime.fromisoformat(str(payload["end_exclusive"])).isoformat()
    specification_hash = compute_specification_hash(hashable)
    hashable["execution_specification_hash"] = specification_hash
    request_hash = compute_request_hash(hashable)
    return execution_request_id, specification_hash, request_hash


class DevelopmentExecutionRequest(BaseModel):
    """One provider execution request (or fragment) bound to a canonical logical request."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    execution_request_id: str
    parent_request_id: str
    parent_request_hash: str
    parent_specification_hash: str
    fragment_index: int = Field(ge=1)
    fragment_count: int = Field(ge=1)
    wave: str
    purpose: str
    dataset: str
    schema_name: str = Field(alias="schema")
    symbols: tuple[str, ...]
    stype_in: str
    stype_out: str = _STYPE_OUT
    start: AwareUTCDatetime
    end_exclusive: AwareUTCDatetime
    encoding: Literal["dbn"] = "dbn"
    compression: Literal["zstd", "none"] = "zstd"
    expected_split: DevelopmentSplit
    session_date: str | None = None
    calendar: str
    logical_output_path: str
    execution_specification_hash: str
    execution_request_hash: str
    raw_dbn_retention_required: bool
    observation_time_source: Literal["ts_recv"] | None = None
    normalized_event_time_receive_fallback_allowed: Literal[False] = False
    fresh_quote_required: bool = True

    @model_validator(mode="after")
    def _validate_identity(self) -> DevelopmentExecutionRequest:
        if self.start >= self.end_exclusive:
            raise ValueError("execution request start must precede end_exclusive")
        if self.fragment_index > self.fragment_count:
            raise ValueError("fragment index must not exceed fragment count")
        if self.schema_name == "cbbo-1m":
            if self.purpose != "strategy_b_closing_quote" or self.session_date is None:
                raise ValueError("cbbo-1m execution requests require the closing-quote purpose")
            if not self.raw_dbn_retention_required or self.observation_time_source != "ts_recv":
                raise ValueError("cbbo-1m execution requests require ts_recv raw retention")
        elif self.session_date is not None or self.observation_time_source is not None:
            raise ValueError("catalog/reference execution requests must not carry session_date")
        for label, value in (
            ("parent request hash", self.parent_request_hash),
            ("parent specification hash", self.parent_specification_hash),
            ("execution specification hash", self.execution_specification_hash),
            ("execution request hash", self.execution_request_hash),
        ):
            _require_sha256(value, label)
        payload = self.model_dump(mode="json", by_alias=True)
        expected_id, expected_specification, expected_request_hash = _recompute_execution_hashes(
            payload
        )
        if self.execution_request_id != expected_id:
            raise ValueError("execution request id does not match its identity")
        if self.execution_specification_hash != expected_specification:
            raise ValueError("execution specification hash does not match its identity")
        if self.execution_request_hash != expected_request_hash:
            raise ValueError("execution request hash does not match its identity")
        return self


def build_development_execution_request(
    *,
    parent: DevelopmentRequest,
    fragment_index: int,
    fragment_count: int,
    window: tuple[datetime, datetime],
) -> DevelopmentExecutionRequest:
    """Build one deterministic, self-hashed provider execution request/fragment."""
    start, end_exclusive = window
    payload = {
        "execution_request_id": "",
        "parent_request_id": parent.request_id,
        "parent_request_hash": parent.request_hash,
        "parent_specification_hash": parent.specification_hash,
        "fragment_index": fragment_index,
        "fragment_count": fragment_count,
        "wave": parent.wave,
        "purpose": parent.purpose,
        "dataset": parent.dataset,
        "schema": parent.schema_name,
        "symbols": list(parent.symbols),
        "stype_in": parent.stype_in,
        "stype_out": _STYPE_OUT,
        "start": start.isoformat(),
        "end_exclusive": end_exclusive.isoformat(),
        "encoding": "dbn",
        "compression": "zstd",
        "expected_split": parent.expected_split,
        "session_date": parent.session_date.isoformat() if parent.session_date else None,
        "calendar": parent.calendar,
        "logical_output_path": "",
        "execution_specification_hash": "",
        "execution_request_hash": "",
        "raw_dbn_retention_required": parent.raw_dbn_retention_required,
        "observation_time_source": parent.observation_time_source,
        "normalized_event_time_receive_fallback_allowed": (
            parent.normalized_event_time_receive_fallback_allowed
        ),
        "fresh_quote_required": True,
    }
    execution_request_id, specification_hash, request_hash = _recompute_execution_hashes(payload)
    payload.update(
        {
            "execution_request_id": execution_request_id,
            "logical_output_path": _logical_output_path(parent, execution_request_id),
            "execution_specification_hash": specification_hash,
            "execution_request_hash": request_hash,
        }
    )
    return DevelopmentExecutionRequest.model_validate(payload)


class DevelopmentExecutionManifest(BaseModel):
    """Deterministic, separately hashed provider execution representation of the frozen plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: Literal["1.0"] = _EXECUTION_MANIFEST_VERSION
    manifest_kind: Literal["development_execution"] = _EXECUTION_MANIFEST_KIND
    strategy_id: Literal["B"] = "B"
    plan_file_sha256: str
    plan_hash: str
    source_scope_hash: str
    fragmentation_policy: Literal["development-fragmentation-v1"] = _FRAGMENTATION_POLICY
    fragmentation_rule: str
    parent_request_count: int = Field(ge=0)
    execution_request_count: int = Field(ge=0)
    fragmented_parent_request_ids: tuple[str, ...]
    parent_requests: tuple[DevelopmentRequest, ...]
    execution_requests: tuple[DevelopmentExecutionRequest, ...]
    manifest_hash: str

    @model_validator(mode="after")
    def _validate_manifest(self) -> DevelopmentExecutionManifest:
        for label, value in (
            ("plan file SHA-256", self.plan_file_sha256),
            ("plan hash", self.plan_hash),
            ("source scope hash", self.source_scope_hash),
        ):
            _require_sha256(value, label)
        if self.parent_request_count != len(self.parent_requests):
            raise ValueError("execution manifest parent count mismatch")
        if self.execution_request_count != len(self.execution_requests):
            raise ValueError("execution manifest execution count mismatch")
        execution_ids = [item.execution_request_id for item in self.execution_requests]
        if len(execution_ids) != len(set(execution_ids)):
            raise ValueError("execution manifest contains duplicate execution requests")
        parents = {item.request_id: item for item in self.parent_requests}
        if len(parents) != len(self.parent_requests):
            raise ValueError("execution manifest contains duplicate parents")
        children: dict[str, list[DevelopmentExecutionRequest]] = {}
        for item in self.execution_requests:
            children.setdefault(item.parent_request_id, []).append(item)
        if set(children) != set(parents):
            raise ValueError("execution manifest parent coverage mismatch")
        for request_id, items in children.items():
            parent = parents[request_id]
            ordered = sorted(items, key=lambda item: item.fragment_index)
            if [item.fragment_index for item in ordered] != list(range(1, len(ordered) + 1)):
                raise ValueError("execution fragment ordering mismatch")
            for item in ordered:
                if item.fragment_count != len(ordered):
                    raise ValueError("execution fragment count mismatch")
                if not (
                    item.dataset == parent.dataset
                    and item.schema_name == parent.schema_name
                    and item.symbols == parent.symbols
                    and item.stype_in == parent.stype_in
                    and item.expected_split == parent.expected_split
                    and item.purpose == parent.purpose
                    and item.raw_dbn_retention_required == parent.raw_dbn_retention_required
                    and item.observation_time_source == parent.observation_time_source
                    and item.normalized_event_time_receive_fallback_allowed
                    == parent.normalized_event_time_receive_fallback_allowed
                    and item.calendar == parent.calendar
                ):
                    raise ValueError("execution fragment does not match its parent semantics")
                if not (parent.start <= item.start < item.end_exclusive <= parent.end_exclusive):
                    raise ValueError("execution fragment exceeds its parent bounds")
            if len(ordered) == 1:
                if (
                    ordered[0].start != parent.start
                    or ordered[0].end_exclusive != parent.end_exclusive
                ):
                    raise ValueError("unfragmented execution request must equal its parent bounds")
            else:
                if (
                    ordered[0].start != parent.start
                    or ordered[-1].end_exclusive != parent.end_exclusive
                ):
                    raise ValueError("execution fragments must cover their parent bounds")
                for previous, current in itertools.pairwise(ordered):
                    if previous.end_exclusive != current.start:
                        raise ValueError("execution fragments must be contiguous")
            if not any(item.fresh_quote_required for item in ordered):
                raise ValueError("execution fragments must require fresh quotes")
        fragmented = tuple(
            sorted(request_id for request_id, items in children.items() if len(items) > 1)
        )
        if self.fragmented_parent_request_ids != fragmented:
            raise ValueError("execution manifest fragmented-parent set mismatch")
        expected_hash = hashlib.sha256(
            canonical_dumps(
                self.model_dump(mode="json", by_alias=True, exclude={"manifest_hash"})
            ).encode("utf-8")
        ).hexdigest()
        if self.manifest_hash and self.manifest_hash != expected_hash:
            raise ValueError("execution manifest hash mismatch")
        return self


def build_development_execution_manifest(
    *,
    plan: DevelopmentPlan,
    plan_file_sha256: str,
    source_scope_hash: str,
    oversize_parent_request_ids: set[str],
) -> DevelopmentExecutionManifest:
    """Fragment the oversized parents by calendar month; map all others one-to-one."""
    _require_sha256(plan_file_sha256, "plan file SHA-256")
    _require_sha256(source_scope_hash, "source scope hash")
    plan_ids = {item.request_id for item in plan.requests}
    unknown = oversize_parent_request_ids - plan_ids
    if unknown:
        raise DevelopmentExecutionError(f"oversize parents are not in the plan: {sorted(unknown)}")
    execution_requests: list[DevelopmentExecutionRequest] = []
    for parent in plan.requests:
        if parent.request_id in oversize_parent_request_ids:
            windows = _month_boundaries(parent.start, parent.end_exclusive)
            count = len(windows)
            for index, window in enumerate(windows, start=1):
                execution_requests.append(
                    build_development_execution_request(
                        parent=parent, fragment_index=index, fragment_count=count, window=window
                    )
                )
        else:
            execution_requests.append(
                build_development_execution_request(
                    parent=parent,
                    fragment_index=1,
                    fragment_count=1,
                    window=(parent.start, parent.end_exclusive),
                )
            )
    payload = {
        "manifest_version": _EXECUTION_MANIFEST_VERSION,
        "manifest_kind": _EXECUTION_MANIFEST_KIND,
        "strategy_id": "B",
        "plan_file_sha256": plan_file_sha256,
        "plan_hash": plan.plan_hash,
        "source_scope_hash": source_scope_hash,
        "fragmentation_policy": _FRAGMENTATION_POLICY,
        "fragmentation_rule": (
            "calendar-month fragments clipped to the parent [start, end); "
            "only oversized parents under accepted cost evidence are fragmented"
        ),
        "parent_request_count": len(plan.requests),
        "execution_request_count": len(execution_requests),
        "fragmented_parent_request_ids": tuple(sorted(oversize_parent_request_ids)),
        "parent_requests": [item.model_dump(mode="json", by_alias=True) for item in plan.requests],
        "execution_requests": [
            item.model_dump(mode="json", by_alias=True) for item in execution_requests
        ],
        "manifest_hash": "",
    }
    manifest = DevelopmentExecutionManifest.model_validate(payload)
    manifest_hash = hashlib.sha256(
        canonical_dumps(
            manifest.model_dump(mode="json", by_alias=True, exclude={"manifest_hash"})
        ).encode("utf-8")
    ).hexdigest()
    return manifest.model_copy(update={"manifest_hash": manifest_hash})


def write_development_execution_manifest(
    path: Path, manifest: DevelopmentExecutionManifest
) -> None:
    """Atomically write one validated development execution manifest."""
    write_json(path, manifest.model_dump(mode="json", by_alias=True))


def load_development_execution_manifest(path: Path) -> DevelopmentExecutionManifest:
    """Load and fully validate a development execution manifest."""
    try:
        payload = load_json(path)
        manifest = DevelopmentExecutionManifest.model_validate(payload)
    except (OSError, ValueError, ValidationError) as exc:
        raise DevelopmentExecutionError(f"invalid development execution manifest: {exc}") from exc
    _require_sha256(manifest.manifest_hash, "execution manifest hash")
    return manifest


class DevelopmentExecutionQuote(BaseModel):
    """One fresh, exact provider cost quote for one execution request/fragment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_request_id: str
    execution_request_hash: str
    cost_usd: str
    currency: Literal["USD"] = "USD"
    quote_source: Literal["provider_response"] = "provider_response"
    response_sha256: str
    observed_at: AwareUTCDatetime

    @model_validator(mode="after")
    def _validate_quote(self) -> DevelopmentExecutionQuote:
        _require_sha256(self.execution_request_hash, "quoted execution request hash")
        _require_sha256(self.response_sha256, "quote response SHA-256")
        _strict_decimal_string(self.cost_usd, "execution quote cost")
        return self


class DevelopmentPaidExecutionScope(BaseModel):
    """Exact paid provider execution scope derived from manifest, dispositions, and quotes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["development-paid-execution-scope-v1"] = (
        "development-paid-execution-scope-v1"
    )
    status: Literal["pending_fresh_fragment_quotes", "authorization_ready"]
    authorization_ready: bool
    plan_hash: str
    execution_manifest_hash: str
    cost_evidence_hash: str
    execution_request_ids: tuple[str, ...]
    pending_quote_execution_request_ids: tuple[str, ...]
    excluded_reused_execution_request_ids: tuple[str, ...]
    excluded_unavailable_execution_request_ids: tuple[str, ...]
    scope_hash: str

    @model_validator(mode="after")
    def _validate_scope(self) -> DevelopmentPaidExecutionScope:
        if self.authorization_ready != (self.status == "authorization_ready"):
            raise ValueError("development paid scope readiness mismatch")
        if self.status == "authorization_ready" and self.pending_quote_execution_request_ids:
            raise ValueError("authorization-ready scope cannot carry pending quotes")
        ids = list(self.execution_request_ids)
        if len(ids) != len(set(ids)):
            raise ValueError("development paid scope contains duplicate execution requests")
        if not set(self.pending_quote_execution_request_ids).issubset(set(ids)):
            raise ValueError("development paid scope pending set is outside the executable scope")
        return self


def derive_development_paid_execution_scope(
    *,
    manifest: DevelopmentExecutionManifest,
    quotes: Mapping[str, DevelopmentExecutionQuote],
    excluded_reused_ids: set[str],
    excluded_unavailable_ids: set[str],
    cost_evidence_hash: str = "",
    maximum_single_request_usd: Decimal = _ONE_USD,
) -> DevelopmentPaidExecutionScope:
    """Derive the exact paid execution scope; fail closed until every fragment is quoted."""
    executable: list[DevelopmentExecutionRequest] = []
    pending: list[str] = []
    for item in manifest.execution_requests:
        if item.execution_request_id in excluded_reused_ids | excluded_unavailable_ids:
            continue
        executable.append(item)
        quote = quotes.get(item.execution_request_id)
        if quote is None:
            pending.append(item.execution_request_id)
            continue
        if not _constant_time_equal(quote.execution_request_hash, item.execution_request_hash):
            raise DevelopmentExecutionError(
                f"execution quote hash mismatch: {item.execution_request_id}"
            )
        cost = _strict_decimal_string(quote.cost_usd, "execution quote cost")
        if cost > maximum_single_request_usd:
            raise DevelopmentExecutionError(
                f"execution quote exceeds the per-request cap: {item.execution_request_id}"
            )
    status: Literal["pending_fresh_fragment_quotes", "authorization_ready"] = (
        "authorization_ready" if not pending else "pending_fresh_fragment_quotes"
    )
    payload = {
        "schema_version": "development-paid-execution-scope-v1",
        "status": status,
        "authorization_ready": status == "authorization_ready",
        "plan_hash": manifest.plan_hash,
        "execution_manifest_hash": manifest.manifest_hash,
        "cost_evidence_hash": cost_evidence_hash,
        "execution_request_ids": [item.execution_request_id for item in executable],
        "pending_quote_execution_request_ids": pending,
        "excluded_reused_execution_request_ids": sorted(excluded_reused_ids),
        "excluded_unavailable_execution_request_ids": sorted(excluded_unavailable_ids),
        "scope_hash": "",
    }
    scope = DevelopmentPaidExecutionScope.model_validate(payload)
    scope_hash = hashlib.sha256(
        canonical_dumps(
            scope.model_dump(mode="json", by_alias=True, exclude={"scope_hash"})
        ).encode("utf-8")
    ).hexdigest()
    return scope.model_copy(update={"scope_hash": scope_hash})


def _constant_time_equal(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)


def development_execution_quote_gate(
    request: DevelopmentExecutionRequest,
    quotes: Mapping[str, DevelopmentExecutionQuote],
    maximum_single_request_usd: Decimal,
) -> Decimal:
    """Return the exact accepted quote cost for one execution request or fail closed."""
    quote = quotes.get(request.execution_request_id)
    if quote is None:
        raise DevelopmentExecutionError(
            f"fresh exact provider quote is required: {request.execution_request_id}"
        )
    if not _constant_time_equal(quote.execution_request_hash, request.execution_request_hash):
        raise DevelopmentExecutionError(
            f"execution quote hash mismatch: {request.execution_request_id}"
        )
    cost = _strict_decimal_string(quote.cost_usd, "execution quote cost")
    if cost > maximum_single_request_usd:
        raise DevelopmentExecutionError(
            f"execution quote exceeds the per-request cap: {request.execution_request_id}"
        )
    return cost


class DevelopmentAuthorization(BaseModel):
    """Development-specific paid acquisition authorization contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["development-acquisition-authorization-v1"] = (
        "development-acquisition-authorization-v1"
    )
    plan_hash: str
    execution_manifest_hash: str
    execution_scope_hash: str
    cost_evidence_hash: str
    maximum_spend_usd: str
    maximum_single_request_usd: str
    currency: Literal["USD"] = "USD"
    source_head: str
    expires_at: AwareUTCDatetime
    purchase_authorized: bool
    authorization_hash: str = ""

    @model_validator(mode="after")
    def _validate_authorization(self) -> DevelopmentAuthorization:
        for label, value in (
            ("plan hash", self.plan_hash),
            ("execution manifest hash", self.execution_manifest_hash),
            ("execution scope hash", self.execution_scope_hash),
            ("cost evidence hash", self.cost_evidence_hash),
        ):
            _require_sha256(value, label)
        if self.authorization_hash:
            _require_sha256(self.authorization_hash, "authorization hash")
        maximum_spend = _strict_decimal_string(self.maximum_spend_usd, "maximum spend")
        single_request = _strict_decimal_string(
            self.maximum_single_request_usd, "maximum single request spend"
        )
        if maximum_spend <= 0 or single_request <= 0:
            raise ValueError("authorization ceilings must be positive")
        if single_request > _ONE_USD:
            raise ValueError("maximum single request ceiling must not exceed 1.00 USD")
        if not self.source_head:
            raise ValueError("authorization source head is required")
        return self


def compute_development_authorization_hash(
    payload_without_hash: dict[str, Any],
) -> str:
    """Return the canonical SHA-256 of a development authorization payload."""
    return hashlib.sha256(canonical_dumps(payload_without_hash).encode("utf-8")).hexdigest()


def validate_development_authorization(
    authorization: DevelopmentAuthorization,
    *,
    now: datetime,
    expected_plan_hash: str,
    expected_manifest_hash: str,
    expected_scope_hash: str,
    expected_cost_evidence_hash: str,
    expected_source_head: str,
    expected_maximum_spend_usd: Decimal,
    expected_maximum_single_request_usd: Decimal,
    consumed_ids: set[str],
) -> None:
    """Validate a development authorization against exact expected bindings."""
    for label, actual, expected in (
        ("plan", authorization.plan_hash, expected_plan_hash),
        ("manifest", authorization.execution_manifest_hash, expected_manifest_hash),
        ("scope", authorization.execution_scope_hash, expected_scope_hash),
        ("cost evidence", authorization.cost_evidence_hash, expected_cost_evidence_hash),
    ):
        if not _constant_time_equal(actual, expected):
            raise DevelopmentExecutionError(f"development authorization {label} hash mismatch")
    if not _constant_time_equal(authorization.source_head, expected_source_head):
        raise DevelopmentExecutionError("development authorization source head mismatch")
    if (
        _strict_decimal_string(authorization.maximum_spend_usd, "maximum spend")
        != expected_maximum_spend_usd
    ):
        raise DevelopmentExecutionError("development authorization maximum spend mismatch")
    if (
        _strict_decimal_string(
            authorization.maximum_single_request_usd, "maximum single request spend"
        )
        != expected_maximum_single_request_usd
    ):
        raise DevelopmentExecutionError("development authorization per-request ceiling mismatch")
    if now >= authorization.expires_at:
        raise DevelopmentExecutionError("development authorization has expired")
    if not authorization.purchase_authorized:
        raise DevelopmentExecutionError("development authorization does not authorize purchase")
    if authorization.authorization_hash in consumed_ids:
        raise DevelopmentExecutionError("development authorization was already consumed")
