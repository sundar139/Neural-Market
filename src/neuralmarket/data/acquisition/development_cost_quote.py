"""Development-native, endpoint-checkpointed provider cost quotation.

The service is offline by default: it validates immutable plan/scope/state
bindings and orchestrates only injected, process-isolated metadata runners.
It never imports Databento, constructs a client, acquires data, or authorizes a
purchase. The CLI supplies the real isolated metadata runners only after this
module's fail-closed gate succeeds.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal, TypeVar, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    model_validator,
)

from neuralmarket.data.acquisition.development import (
    DevelopmentPlan,
    DevelopmentRequest,
    DevelopmentRequestScope,
    derive_current_development_scope_from_pilot,
    load_development_plan,
    load_development_scope,
    verify_development_plan_from_files,
    verify_development_request,
)
from neuralmarket.data.acquisition.manifests import write_json
from neuralmarket.data.acquisition.metadata_runner import (
    Endpoint,
    IsolatedMetadataResult,
    IsolatedSchemaResult,
)
from neuralmarket.data.contracts import AwareUTCDatetime
from neuralmarket.data.errors import PlanValidationError
from neuralmarket.data.manifests import canonical_dumps

DEVELOPMENT_ENDPOINTS: tuple[Endpoint, ...] = (
    "record-count",
    "billable-size",
    "cost",
)
Operation = Literal["list-schemas", "record-count", "billable-size", "cost"]
AttemptOutcome = Literal["started", "succeeded", "failed", "timeout"]
StopReason = Literal[
    "total_deadline_reached",
    "schema_attempts_exhausted",
    "unsupported_schema",
    "endpoint_attempts_exhausted",
    "invalid_provider_result",
]


class DevelopmentQuoteError(ValueError):
    """A development quote trust boundary or evidence invariant failed."""


class CheckpointGenerationMismatchError(DevelopmentQuoteError):
    """The on-disk checkpoint changed under a compare-and-swap resume write."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file's exact bytes."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise DevelopmentQuoteError(f"unable to hash file: {path}") from exc


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _require_sha256(value: str, label: str) -> None:
    if not _is_sha256(value):
        raise DevelopmentQuoteError(f"{label} must be 64 lowercase hex")


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_dumps(dict(payload)).encode("utf-8")).hexdigest()


def _aware_utc(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DevelopmentQuoteError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def _strict_decimal_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise DevelopmentQuoteError(f"{label} must be a Decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DevelopmentQuoteError(f"{label} is not Decimal") from exc
    if not parsed.is_finite():
        raise DevelopmentQuoteError(f"{label} must be finite")
    if parsed < 0:
        raise DevelopmentQuoteError(f"{label} must be non-negative")
    return value


def _provider_decimal_string(value: object) -> str:
    if isinstance(value, bool):
        raise DevelopmentQuoteError("provider cost must not be a bool")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise DevelopmentQuoteError("provider cost is not Decimal-compatible") from exc
    if not parsed.is_finite() or parsed < 0:
        raise DevelopmentQuoteError("provider cost must be finite and non-negative")
    return str(parsed)


def _provider_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DevelopmentQuoteError(f"provider {label} must be an integer")
    if value < 0:
        raise DevelopmentQuoteError(f"provider {label} must be non-negative")
    return value


class JournalFingerprint(BaseModel):
    """Stable main/WAL identity for the read-only pilot journal snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    main_sha256: str
    wal_exists: bool
    wal_size: int = Field(ge=0)
    wal_sha256: str

    @model_validator(mode="after")
    def _validate_fingerprint(self) -> JournalFingerprint:
        _require_sha256(self.main_sha256, "journal main SHA-256")
        _require_sha256(self.wal_sha256, "journal WAL SHA-256")
        if not self.wal_exists and self.wal_size:
            raise ValueError("absent journal WAL cannot have bytes")
        return self

    @classmethod
    def from_path(cls, path: Path) -> JournalFingerprint:
        """Fingerprint a stable journal main file and its WAL sidecar."""
        wal_path = path.with_name(f"{path.name}-wal")
        try:
            main_before = path.read_bytes()
            wal_exists = wal_path.exists()
            wal = wal_path.read_bytes() if wal_exists else b""
            main_after = path.read_bytes()
        except OSError as exc:
            raise DevelopmentQuoteError("unable to fingerprint pilot journal") from exc
        if main_before != main_after:
            raise DevelopmentQuoteError("pilot journal changed during fingerprinting")
        return cls(
            main_sha256=hashlib.sha256(main_after).hexdigest(),
            wal_exists=wal_exists,
            wal_size=len(wal),
            wal_sha256=hashlib.sha256(wal).hexdigest(),
        )


class DevelopmentQuoteBindings(BaseModel):
    """Exact source, protected-state, and native request identities for a quote."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_head: str
    development_plan_file_sha256: str
    development_plan_hash: str
    development_scope_file_sha256: str
    development_scope_hash: str
    pilot_plan_file_sha256: str
    journal_fingerprint: JournalFingerprint
    databento_client_version: str
    request_identities: tuple[DevelopmentRequest, ...]

    @model_validator(mode="after")
    def _validate_bindings(self) -> DevelopmentQuoteBindings:
        if len(self.repository_head) != 40 or any(
            character not in "0123456789abcdef" for character in self.repository_head
        ):
            raise ValueError("repository_head must be a lowercase Git object ID")
        for label, value in (
            ("development plan file SHA-256", self.development_plan_file_sha256),
            ("development plan hash", self.development_plan_hash),
            ("development scope file SHA-256", self.development_scope_file_sha256),
            ("development scope hash", self.development_scope_hash),
            ("pilot plan file SHA-256", self.pilot_plan_file_sha256),
        ):
            _require_sha256(value, label)
        if not self.databento_client_version:
            raise ValueError("databento_client_version is required")
        ids = [request.request_id for request in self.request_identities]
        if len(ids) != len(set(ids)):
            raise ValueError("development quote bindings contain duplicate request identity")
        for request in self.request_identities:
            verify_development_request(request)
        return self

    @classmethod
    def from_requests(
        cls,
        *,
        repository_head: str,
        development_plan_file_sha256: str,
        development_plan_hash: str,
        development_scope_file_sha256: str,
        development_scope_hash: str,
        pilot_plan_file_sha256: str,
        journal_fingerprint: JournalFingerprint,
        databento_client_version: str,
        requests: Sequence[DevelopmentRequest],
    ) -> DevelopmentQuoteBindings:
        """Build native bindings after verifying every development request."""
        try:
            for request in requests:
                verify_development_request(request)
            return cls(
                repository_head=repository_head,
                development_plan_file_sha256=development_plan_file_sha256,
                development_plan_hash=development_plan_hash,
                development_scope_file_sha256=development_scope_file_sha256,
                development_scope_hash=development_scope_hash,
                pilot_plan_file_sha256=pilot_plan_file_sha256,
                journal_fingerprint=journal_fingerprint,
                databento_client_version=databento_client_version,
                request_identities=tuple(requests),
            )
        except (PlanValidationError, ValidationError, ValueError) as exc:
            raise DevelopmentQuoteError(f"invalid development request identity: {exc}") from exc


class PreparedDevelopmentQuote(BaseModel):
    """Offline-verified canonical plan, exact current scope, and quote bindings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: DevelopmentPlan
    scope: DevelopmentRequestScope
    bindings: DevelopmentQuoteBindings


def prepare_development_quote(
    *,
    repository_root: Path,
    development_plan_path: Path,
    development_scope_path: Path,
    pilot_plan_path: Path,
    pilot_journal_path: Path,
    repository_head: str,
    expected_repository_head: str,
    expected_plan_file_sha256: str,
    expected_plan_hash: str,
    expected_scope_file_sha256: str,
    expected_scope_hash: str,
    databento_client_version: str,
    expected_pilot_plan_file_sha256: str | None = None,
    expected_journal_main_sha256: str | None = None,
) -> PreparedDevelopmentQuote:
    """Verify the canonical plan and artifact-backed current scope before a provider exists."""
    root = repository_root.resolve()
    for label, value in (
        ("expected plan file SHA-256", expected_plan_file_sha256),
        ("expected plan hash", expected_plan_hash),
        ("expected scope file SHA-256", expected_scope_file_sha256),
        ("expected scope hash", expected_scope_hash),
    ):
        _require_sha256(value, label)
    if repository_head != expected_repository_head:
        raise DevelopmentQuoteError("repository source revision mismatch")
    plan_file_sha = sha256_file(development_plan_path)
    scope_file_sha = sha256_file(development_scope_path)
    if plan_file_sha != expected_plan_file_sha256:
        raise DevelopmentQuoteError("development plan file SHA-256 mismatch")
    if scope_file_sha != expected_scope_file_sha256:
        raise DevelopmentQuoteError("development scope file SHA-256 mismatch")
    before = JournalFingerprint.from_path(pilot_journal_path)
    try:
        plan = load_development_plan(development_plan_path)
        if plan.plan_hash != expected_plan_hash:
            raise DevelopmentQuoteError("development plan hash mismatch")
        verify_development_plan_from_files(
            plan,
            acquisition_config_path=root / "configs/data/acquisition/spy_daily_budgeted.yaml",
            data_config_path=root / "configs/data/spy_daily_databento.yaml",
            source_manifest_path=root / "data/manifests/source_manifest_v1.json",
            split_manifest_path=root / "data/manifests/split_manifest_v1.json",
            policy_manifest_path=root / "data/manifests/acquisition_policy_v1.json",
        )
        scope = load_development_scope(
            development_scope_path,
            plan,
            repository_root=root,
        )
        if scope.scope_hash != expected_scope_hash:
            raise DevelopmentQuoteError("development scope hash mismatch")
        current = derive_current_development_scope_from_pilot(
            plan,
            pilot_plan_path=pilot_plan_path,
            pilot_journal_path=pilot_journal_path,
        )
        if current != scope:
            raise DevelopmentQuoteError(
                "development scope does not equal artifact-backed current pilot state"
            )
    except (OSError, PlanValidationError, ValidationError, ValueError) as exc:
        if isinstance(exc, DevelopmentQuoteError):
            raise
        raise DevelopmentQuoteError(f"development plan/scope gate failed: {exc}") from exc
    after = JournalFingerprint.from_path(pilot_journal_path)
    if before != after:
        raise DevelopmentQuoteError("pilot journal changed during development scope gate")
    pilot_plan_sha = sha256_file(pilot_plan_path)
    if (
        expected_pilot_plan_file_sha256 is not None
        and pilot_plan_sha != expected_pilot_plan_file_sha256
    ):
        raise DevelopmentQuoteError("pilot plan file SHA-256 mismatch")
    if (
        expected_journal_main_sha256 is not None
        and before.main_sha256 != expected_journal_main_sha256
    ):
        raise DevelopmentQuoteError("pilot journal SHA-256 mismatch")
    bindings = DevelopmentQuoteBindings.from_requests(
        repository_head=repository_head,
        development_plan_file_sha256=plan_file_sha,
        development_plan_hash=plan.plan_hash,
        development_scope_file_sha256=scope_file_sha,
        development_scope_hash=scope.scope_hash,
        pilot_plan_file_sha256=pilot_plan_sha,
        journal_fingerprint=before,
        databento_client_version=databento_client_version,
        requests=scope.requests,
    )
    return PreparedDevelopmentQuote(plan=plan, scope=scope, bindings=bindings)


class DevelopmentQuoteRunPolicy(BaseModel):
    """Bounded retry and hard-timeout policy persisted with a checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hard_operation_timeout_seconds: float = Field(gt=0, le=300)
    maximum_attempts: int = Field(gt=0, le=3)


class ProviderOperationCounters(BaseModel):
    """Metadata counters plus immutable zero-acquisition proof."""

    model_config = ConfigDict(extra="forbid")

    list_schemas: int = Field(default=0, ge=0)
    get_record_count: int = Field(default=0, ge=0)
    get_billable_size: int = Field(default=0, ge=0)
    get_cost: int = Field(default=0, ge=0)
    timeseries_get_range: Literal[0] = 0
    batch: Literal[0] = 0
    live: Literal[0] = 0
    symbology: Literal[0] = 0

    @property
    def total_metadata_operations(self) -> int:
        """Return all launched schema/count/size/cost operations."""
        return self.list_schemas + self.get_record_count + self.get_billable_size + self.get_cost


class SchemaObservation(BaseModel):
    """One accepted, hash-bound dataset schema-list response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    supported_schemas: tuple[str, ...]
    observed_at: AwareUTCDatetime
    attempt: int = Field(ge=1)
    provider_response_sha256: str

    @model_validator(mode="after")
    def _validate_observation(self) -> SchemaObservation:
        if not self.supported_schemas or tuple(sorted(set(self.supported_schemas))) != (
            self.supported_schemas
        ):
            raise ValueError("supported schemas must be nonempty, unique, and sorted")
        expected = _schema_response_hash(
            self.dataset,
            self.supported_schemas,
            self.observed_at.isoformat(),
        )
        if self.provider_response_sha256 != expected:
            raise ValueError("schema response hash mismatch")
        return self


class EndpointObservation(BaseModel):
    """One accepted provider metadata endpoint result for an exact request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    specification_hash: str
    request_hash: str
    endpoint: Endpoint
    value: int | str
    observed_at: AwareUTCDatetime
    attempt: int = Field(ge=1)
    quote_source: Literal["provider_response"] = "provider_response"
    provider_response_sha256: str

    @model_validator(mode="before")
    @classmethod
    def _validate_value_type(cls, payload: Any) -> Any:
        if not isinstance(payload, Mapping):
            return payload
        endpoint = payload.get("endpoint")
        value = payload.get("value")
        if endpoint == "cost":
            _strict_decimal_string(value, "endpoint cost")
        elif endpoint in {"record-count", "billable-size"}:
            _provider_nonnegative_int(value, str(endpoint))
        return payload

    @model_validator(mode="after")
    def _validate_observation(self) -> EndpointObservation:
        for label, value in (
            ("specification hash", self.specification_hash),
            ("request hash", self.request_hash),
            ("provider response SHA-256", self.provider_response_sha256),
        ):
            _require_sha256(value, label)
        expected = _endpoint_response_hash(
            request_id=self.request_id,
            specification_hash=self.specification_hash,
            request_hash=self.request_hash,
            endpoint=self.endpoint,
            value=self.value,
            observed_at=self.observed_at.isoformat(),
        )
        if self.provider_response_sha256 != expected:
            raise ValueError("endpoint response hash mismatch")
        return self


class DevelopmentQuoteAttempt(BaseModel):
    """One persist-before-launch provider metadata operation attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    operation: Operation
    dataset: str
    request_id: str | None = None
    attempt: int = Field(ge=1)
    retry: bool
    outcome: AttemptOutcome
    started_at: AwareUTCDatetime
    completed_at: AwareUTCDatetime | None = None
    failure_type: str | None = None
    http_status: int | None = None
    child_pid: int | None = None
    child_exitcode: int | None = None
    child_terminated: bool = False
    child_joined: bool | None = None
    remaining_children: int | None = None

    @model_validator(mode="after")
    def _validate_attempt(self) -> DevelopmentQuoteAttempt:
        if self.operation == "list-schemas" and self.request_id is not None:
            raise ValueError("schema attempt must not carry request_id")
        if self.operation != "list-schemas" and self.request_id is None:
            raise ValueError("endpoint attempt requires request_id")
        if self.outcome == "started" and self.completed_at is not None:
            raise ValueError("started attempt cannot be completed")
        if self.outcome != "started" and self.completed_at is None:
            raise ValueError("finished attempt requires completed_at")
        if self.outcome == "succeeded" and (
            self.child_joined is not True or self.remaining_children != 0
        ):
            raise ValueError("successful attempt requires a clean child")
        return self


def _counters_match_attempts(
    counters: ProviderOperationCounters,
    attempts: Sequence[DevelopmentQuoteAttempt],
) -> bool:
    counts = Counter(attempt.operation for attempt in attempts)
    return (
        counters.list_schemas == counts["list-schemas"]
        and counters.get_record_count == counts["record-count"]
        and counters.get_billable_size == counts["billable-size"]
        and counters.get_cost == counts["cost"]
    )


class DevelopmentQuoteCheckpoint(BaseModel):
    """Atomic, self-hashed endpoint-granular development quote progress."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["development-cost-checkpoint-v1"] = "development-cost-checkpoint-v1"
    status: Literal["incomplete", "complete"]
    resume_eligible: bool
    authorization_ready: Literal[False] = False
    purchase_authorized: Literal[False] = False
    bindings: DevelopmentQuoteBindings
    policy: DevelopmentQuoteRunPolicy
    created_at: AwareUTCDatetime
    updated_at: AwareUTCDatetime
    schema_results: dict[str, SchemaObservation]
    endpoint_results: dict[str, dict[Endpoint, EndpointObservation]]
    completed_request_ids: tuple[str, ...]
    pending_endpoints: dict[str, tuple[Endpoint, ...]]
    pending_schema_datasets: tuple[str, ...]
    attempt_history: list[DevelopmentQuoteAttempt]
    provider_operation_counters: ProviderOperationCounters
    retry_count: int = Field(ge=0)
    timeout_count: int = Field(ge=0)
    stop_reason: StopReason | None = None
    checkpoint_hash: str

    @model_validator(mode="after")
    def _validate_checkpoint(self, info: ValidationInfo) -> DevelopmentQuoteCheckpoint:
        identities = {request.request_id: request for request in self.bindings.request_identities}
        for request_id, endpoints in self.endpoint_results.items():
            request = identities.get(request_id)
            if request is None:
                raise ValueError("checkpoint contains an unknown request")
            for endpoint, observation in endpoints.items():
                if endpoint != observation.endpoint:
                    raise ValueError("checkpoint endpoint key mismatch")
                if (
                    observation.request_id != request.request_id
                    or observation.specification_hash != request.specification_hash
                    or observation.request_hash != request.request_hash
                ):
                    raise ValueError("checkpoint endpoint request identity mismatch")
        datasets = {request.dataset for request in self.bindings.request_identities}
        if set(self.schema_results) - datasets:
            raise ValueError("checkpoint contains an unknown schema dataset")
        for dataset, schema_observation in self.schema_results.items():
            if schema_observation.dataset != dataset:
                raise ValueError("checkpoint schema dataset key mismatch")
        expected_completed, expected_pending = _request_partitions(
            self.bindings.request_identities,
            self.endpoint_results,
        )
        if (
            self.completed_request_ids != expected_completed
            or self.pending_endpoints != expected_pending
        ):
            raise ValueError("checkpoint request endpoint partition mismatch")
        expected_pending_schemas = tuple(sorted(datasets - set(self.schema_results)))
        if self.pending_schema_datasets != expected_pending_schemas:
            raise ValueError("checkpoint schema partition mismatch")
        expected_complete = not expected_pending and not expected_pending_schemas
        if (self.status == "complete") != expected_complete:
            raise ValueError("checkpoint completion status mismatch")
        if self.resume_eligible == expected_complete:
            raise ValueError("checkpoint resume eligibility mismatch")
        if not _counters_match_attempts(self.provider_operation_counters, self.attempt_history):
            raise ValueError("checkpoint operation counters do not match attempts")
        if self.retry_count != sum(attempt.retry for attempt in self.attempt_history):
            raise ValueError("checkpoint retry count mismatch")
        if self.timeout_count != sum(
            attempt.outcome == "timeout" for attempt in self.attempt_history
        ):
            raise ValueError("checkpoint timeout count mismatch")
        sequences = [attempt.sequence for attempt in self.attempt_history]
        if sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("checkpoint attempt sequence mismatch")
        allow_unsealed = bool(info.context and info.context.get("allow_unsealed"))
        if not self.checkpoint_hash and not allow_unsealed:
            raise ValueError("checkpoint hash is required")
        if self.checkpoint_hash:
            expected_hash = _artifact_hash(
                self.model_dump(mode="json", by_alias=True),
                hash_field="checkpoint_hash",
            )
            if self.checkpoint_hash != expected_hash:
                raise ValueError("checkpoint hash mismatch")
        return self


def _schema_response_hash(dataset: str, schemas: Sequence[str], observed_at: str) -> str:
    return _canonical_hash(
        {
            "dataset": dataset,
            "supported_schemas": list(schemas),
            "observed_at": observed_at,
            "quote_source": "provider_response",
        }
    )


def _endpoint_response_hash(
    *,
    request_id: str,
    specification_hash: str,
    request_hash: str,
    endpoint: Endpoint,
    value: int | str,
    observed_at: str,
) -> str:
    return _canonical_hash(
        {
            "request_id": request_id,
            "specification_hash": specification_hash,
            "request_hash": request_hash,
            "endpoint": endpoint,
            "value": str(value),
            "observed_at": observed_at,
            "quote_source": "provider_response",
        }
    )


def _artifact_hash(payload: Mapping[str, Any], *, hash_field: str) -> str:
    return _canonical_hash({key: value for key, value in payload.items() if key != hash_field})


ModelT = TypeVar("ModelT", bound=BaseModel)


def _seal_model(model: type[ModelT], payload: Mapping[str, Any], *, hash_field: str) -> ModelT:
    normalized_input = dict(payload)
    normalized_input[hash_field] = ""
    draft = model.model_validate(normalized_input, context={"allow_unsealed": True})
    normalized = draft.model_dump(mode="json", by_alias=True)
    normalized[hash_field] = _artifact_hash(normalized, hash_field=hash_field)
    return model.model_validate(normalized)


def _request_partitions(
    requests: Sequence[DevelopmentRequest],
    endpoint_results: Mapping[str, Mapping[Endpoint, EndpointObservation]],
) -> tuple[tuple[str, ...], dict[str, tuple[Endpoint, ...]]]:
    completed: list[str] = []
    pending: dict[str, tuple[Endpoint, ...]] = {}
    for request in requests:
        present = endpoint_results.get(request.request_id, {})
        missing = tuple(endpoint for endpoint in DEVELOPMENT_ENDPOINTS if endpoint not in present)
        if missing:
            pending[request.request_id] = missing
        else:
            completed.append(request.request_id)
    return tuple(completed), pending


def _seal_checkpoint(
    state: DevelopmentQuoteCheckpoint,
    *,
    updated_at: datetime | None = None,
) -> DevelopmentQuoteCheckpoint:
    payload = state.model_dump(mode="json", by_alias=True)
    if updated_at is not None:
        payload["updated_at"] = _aware_utc(updated_at, "checkpoint update time").isoformat()
    completed, pending = _request_partitions(
        state.bindings.request_identities,
        state.endpoint_results,
    )
    datasets = {request.dataset for request in state.bindings.request_identities}
    pending_schemas = tuple(sorted(datasets - set(state.schema_results)))
    complete = not pending and not pending_schemas
    payload.update(
        {
            "status": "complete" if complete else "incomplete",
            "resume_eligible": not complete,
            "completed_request_ids": completed,
            "pending_endpoints": pending,
            "pending_schema_datasets": pending_schemas,
            "retry_count": sum(attempt.retry for attempt in state.attempt_history),
            "timeout_count": sum(attempt.outcome == "timeout" for attempt in state.attempt_history),
            "checkpoint_hash": "",
        }
    )
    try:
        return _seal_model(
            DevelopmentQuoteCheckpoint,
            payload,
            hash_field="checkpoint_hash",
        )
    except (ValidationError, ValueError) as exc:
        raise DevelopmentQuoteError(f"invalid development quote checkpoint: {exc}") from exc


def initialize_development_quote_checkpoint(
    *,
    bindings: DevelopmentQuoteBindings,
    policy: DevelopmentQuoteRunPolicy,
    now: datetime,
) -> DevelopmentQuoteCheckpoint:
    """Create zero-call incomplete progress for the exact bound development scope."""
    timestamp = _aware_utc(now, "checkpoint creation time")
    pending = {request.request_id: DEVELOPMENT_ENDPOINTS for request in bindings.request_identities}
    payload = {
        "schema_version": "development-cost-checkpoint-v1",
        "status": "incomplete",
        "resume_eligible": True,
        "authorization_ready": False,
        "purchase_authorized": False,
        "bindings": bindings.model_dump(mode="json", by_alias=True),
        "policy": policy.model_dump(mode="json"),
        "created_at": timestamp.isoformat(),
        "updated_at": timestamp.isoformat(),
        "schema_results": {},
        "endpoint_results": {},
        "completed_request_ids": [],
        "pending_endpoints": pending,
        "pending_schema_datasets": sorted(
            {request.dataset for request in bindings.request_identities}
        ),
        "attempt_history": [],
        "provider_operation_counters": ProviderOperationCounters().model_dump(mode="json"),
        "retry_count": 0,
        "timeout_count": 0,
        "stop_reason": None,
        "checkpoint_hash": "",
    }
    try:
        return _seal_model(
            DevelopmentQuoteCheckpoint,
            payload,
            hash_field="checkpoint_hash",
        )
    except (ValidationError, ValueError) as exc:
        raise DevelopmentQuoteError(
            f"unable to initialize development quote checkpoint: {exc}"
        ) from exc


def write_development_quote_checkpoint(
    path: Path,
    state: DevelopmentQuoteCheckpoint,
    *,
    expected_checkpoint_hash: str | None = None,
) -> DevelopmentQuoteCheckpoint:
    """Atomically fsync and replace one self-hashed development quote checkpoint.

    When ``expected_checkpoint_hash`` is provided the write is a compare-and-swap
    generation: the on-disk checkpoint's own hash must still equal it immediately
    before the atomic replace, otherwise :class:`CheckpointGenerationMismatchError` is
    raised and nothing is written. This prevents two concurrent quote runs from
    erasing each other's durably accepted endpoint observations.
    """
    if expected_checkpoint_hash is not None:
        try:
            on_disk_payload = json.loads(path.read_text(encoding="utf-8"))
            on_disk_hash = str(on_disk_payload.get("checkpoint_hash", ""))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise CheckpointGenerationMismatchError(
                f"development quote checkpoint changed concurrently: {exc}"
            ) from exc
        if on_disk_hash != expected_checkpoint_hash:
            raise CheckpointGenerationMismatchError(
                "development quote checkpoint changed concurrently; retry resume"
            )
    sealed = _seal_checkpoint(state)
    write_json(path, sealed.model_dump(mode="json", by_alias=True))
    return sealed


def load_development_quote_checkpoint(
    path: Path,
    *,
    expected_bindings: DevelopmentQuoteBindings,
    expected_policy: DevelopmentQuoteRunPolicy,
) -> DevelopmentQuoteCheckpoint:
    """Load a complete checkpoint generation and reject any incompatible binding."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        state = DevelopmentQuoteCheckpoint.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise DevelopmentQuoteError(f"invalid development quote checkpoint: {exc}") from exc
    if state.bindings != expected_bindings:
        raise DevelopmentQuoteError("development quote checkpoint binding mismatch")
    if state.policy != expected_policy:
        raise DevelopmentQuoteError("development quote checkpoint policy mismatch")
    return state


SchemaRunner = Callable[[str, int, float], IsolatedSchemaResult]
EndpointRunner = Callable[[DevelopmentRequest, Endpoint, int, float], IsolatedMetadataResult]
Clock = Callable[[], datetime]
Monotonic = Callable[[], float]


def _operation_counter_name(operation: Operation) -> str:
    return {
        "list-schemas": "list_schemas",
        "record-count": "get_record_count",
        "billable-size": "get_billable_size",
        "cost": "get_cost",
    }[operation]


def _prior_attempts(
    state: DevelopmentQuoteCheckpoint,
    *,
    operation: Operation,
    dataset: str,
    request_id: str | None,
) -> int:
    return sum(
        attempt.operation == operation
        and attempt.dataset == dataset
        and attempt.request_id == request_id
        for attempt in state.attempt_history
    )


def _begin_attempt(
    state: DevelopmentQuoteCheckpoint,
    *,
    checkpoint_path: Path,
    operation: Operation,
    dataset: str,
    request_id: str | None,
    attempt: int,
    retry: bool,
    now: datetime,
    expected_checkpoint_hash: str | None,
) -> tuple[DevelopmentQuoteCheckpoint, str]:
    state.stop_reason = None
    state.attempt_history.append(
        DevelopmentQuoteAttempt(
            sequence=len(state.attempt_history) + 1,
            operation=operation,
            dataset=dataset,
            request_id=request_id,
            attempt=attempt,
            retry=retry,
            outcome="started",
            started_at=_aware_utc(now, "attempt start time"),
        )
    )
    name = _operation_counter_name(operation)
    counters = state.provider_operation_counters
    setattr(counters, name, int(getattr(counters, name)) + 1)
    sealed = write_development_quote_checkpoint(
        checkpoint_path,
        _seal_checkpoint(state, updated_at=now),
        expected_checkpoint_hash=expected_checkpoint_hash,
    )
    return sealed, sealed.checkpoint_hash


def _finish_attempt(
    state: DevelopmentQuoteCheckpoint,
    *,
    outcome: Literal["succeeded", "failed", "timeout"],
    completed_at: datetime,
    failure_type: str | None,
    http_status: int | None,
    child_pid: int,
    child_exitcode: int | None,
    child_terminated: bool,
    child_joined: bool,
    remaining_children: int,
) -> None:
    started = state.attempt_history[-1]
    state.attempt_history[-1] = started.model_copy(
        update={
            "outcome": outcome,
            "completed_at": _aware_utc(completed_at, "attempt completion time"),
            "failure_type": failure_type,
            "http_status": http_status,
            "child_pid": child_pid,
            "child_exitcode": child_exitcode,
            "child_terminated": child_terminated,
            "child_joined": child_joined,
            "remaining_children": remaining_children,
        }
    )


def _retryable(failure_type: str | None, http_status: int | None) -> bool:
    return failure_type in {
        "metadata_hard_timeout",
        "schema_list_hard_timeout",
        "TimeoutError",
        "ConnectionError",
        "ConnectionResetError",
    } or http_status in {429, 500, 502, 503, 504}


def _deadline_remaining(started: float, deadline: float, monotonic: Monotonic) -> float:
    return deadline - (monotonic() - started)


def _schema_failure(
    result: IsolatedSchemaResult,
) -> tuple[str | None, int | None, bool]:
    clean = result.child_joined and result.remaining_children == 0
    failure = result.failure_type
    if failure is None and (result.supported_schemas is None or not clean):
        failure = "invalid_schema_provider_result"
    return failure, result.http_status, clean


def _metadata_failure(
    result: IsolatedMetadataResult,
) -> tuple[str | None, int | None, bool]:
    clean = result.child_joined and result.remaining_children == 0
    last = result.events[-1] if result.events else None
    failure = result.failure_type
    if failure is None and not clean:
        failure = "unclean_metadata_child"
    return failure, last.http_status if last else None, clean


def run_development_quote(
    *,
    state: DevelopmentQuoteCheckpoint,
    checkpoint_path: Path,
    schema_runner: SchemaRunner,
    endpoint_runner: EndpointRunner,
    total_deadline_seconds: float,
    monotonic: Monotonic,
    now: Clock,
    expected_checkpoint_hash: str | None = None,
) -> DevelopmentQuoteCheckpoint:
    """Run bounded pending metadata work, persisting before launch and after acceptance.

    ``expected_checkpoint_hash`` anchors every checkpoint write to the generation
    that was loaded: if another process advanced the checkpoint since, the first
    write fails closed with :class:`CheckpointGenerationMismatchError` instead of
    erasing the concurrent run's durably accepted endpoint observations.
    """
    if total_deadline_seconds <= 0:
        raise DevelopmentQuoteError("total_deadline_seconds must be positive")
    state = _seal_checkpoint(state)
    anchor = expected_checkpoint_hash or state.checkpoint_hash
    started = monotonic()
    requests = state.bindings.request_identities
    required_schemas: dict[str, set[str]] = {}
    for request in requests:
        required_schemas.setdefault(request.dataset, set()).add(request.schema_name)

    for dataset in sorted(required_schemas):
        if dataset in state.schema_results:
            continue
        for run_attempt in range(1, state.policy.maximum_attempts + 1):
            remaining = _deadline_remaining(started, total_deadline_seconds, monotonic)
            if remaining <= 0:
                state.stop_reason = "total_deadline_reached"
                return write_development_quote_checkpoint(
                    checkpoint_path,
                    state,
                    expected_checkpoint_hash=anchor,
                )
            previous = _prior_attempts(
                state,
                operation="list-schemas",
                dataset=dataset,
                request_id=None,
            )
            attempt = previous + 1
            started_at = now()
            state, anchor = _begin_attempt(
                state,
                checkpoint_path=checkpoint_path,
                operation="list-schemas",
                dataset=dataset,
                request_id=None,
                attempt=attempt,
                retry=previous > 0 or run_attempt > 1,
                now=started_at,
                expected_checkpoint_hash=anchor,
            )
            schema_result = schema_runner(
                dataset,
                attempt,
                min(state.policy.hard_operation_timeout_seconds, remaining),
            )
            completed_at = now()
            failure, http_status, clean = _schema_failure(schema_result)
            if failure is None:
                supported = tuple(sorted(set(schema_result.supported_schemas or ())))
                missing = sorted(required_schemas[dataset] - set(supported))
                if missing:
                    failure = f"unsupported_schema:{','.join(missing)}"
            outcome: Literal["succeeded", "failed", "timeout"] = (
                "timeout" if failure == "schema_list_hard_timeout" else "failed"
            )
            if failure is None:
                outcome = "succeeded"
            _finish_attempt(
                state,
                outcome=outcome,
                completed_at=completed_at,
                failure_type=failure,
                http_status=http_status,
                child_pid=schema_result.child_pid,
                child_exitcode=schema_result.child_exitcode,
                child_terminated=schema_result.child_terminated,
                child_joined=schema_result.child_joined,
                remaining_children=schema_result.remaining_children,
            )
            if failure is None:
                observed_at = _aware_utc(completed_at, "schema observation time")
                state.schema_results[dataset] = SchemaObservation(
                    dataset=dataset,
                    supported_schemas=supported,
                    observed_at=observed_at,
                    attempt=attempt,
                    provider_response_sha256=_schema_response_hash(
                        dataset,
                        supported,
                        observed_at.isoformat(),
                    ),
                )
                state = write_development_quote_checkpoint(
                    checkpoint_path,
                    _seal_checkpoint(state, updated_at=completed_at),
                    expected_checkpoint_hash=anchor,
                )
                anchor = state.checkpoint_hash
                break
            state = write_development_quote_checkpoint(
                checkpoint_path,
                _seal_checkpoint(state, updated_at=completed_at),
                expected_checkpoint_hash=anchor,
            )
            anchor = state.checkpoint_hash
            if failure.startswith("unsupported_schema:"):
                state.stop_reason = "unsupported_schema"
                return write_development_quote_checkpoint(
                    checkpoint_path,
                    state,
                    expected_checkpoint_hash=anchor,
                )
            if not _retryable(failure, http_status) or run_attempt == state.policy.maximum_attempts:
                state.stop_reason = "schema_attempts_exhausted"
                return write_development_quote_checkpoint(
                    checkpoint_path,
                    state,
                    expected_checkpoint_hash=anchor,
                )

    for request in requests:
        for endpoint in DEVELOPMENT_ENDPOINTS:
            if endpoint in state.endpoint_results.setdefault(request.request_id, {}):
                continue
            for run_attempt in range(1, state.policy.maximum_attempts + 1):
                remaining = _deadline_remaining(started, total_deadline_seconds, monotonic)
                if remaining <= 0:
                    state.stop_reason = "total_deadline_reached"
                    return write_development_quote_checkpoint(
                        checkpoint_path,
                        state,
                        expected_checkpoint_hash=anchor,
                    )
                previous = _prior_attempts(
                    state,
                    operation=endpoint,
                    dataset=request.dataset,
                    request_id=request.request_id,
                )
                attempt = previous + 1
                started_at = now()
                state, anchor = _begin_attempt(
                    state,
                    checkpoint_path=checkpoint_path,
                    operation=endpoint,
                    dataset=request.dataset,
                    request_id=request.request_id,
                    attempt=attempt,
                    retry=previous > 0 or run_attempt > 1,
                    now=started_at,
                    expected_checkpoint_hash=anchor,
                )
                endpoint_result = endpoint_runner(
                    request,
                    endpoint,
                    attempt,
                    min(state.policy.hard_operation_timeout_seconds, remaining),
                )
                completed_at = now()
                failure, http_status, clean = _metadata_failure(endpoint_result)
                value: int | str | None = None
                if failure is None:
                    try:
                        if set(endpoint_result.endpoint_values) != {endpoint}:
                            raise DevelopmentQuoteError(
                                "isolated endpoint result did not contain exactly one endpoint"
                            )
                        raw = endpoint_result.endpoint_values[endpoint]
                        value = (
                            _provider_decimal_string(raw)
                            if endpoint == "cost"
                            else _provider_nonnegative_int(raw, endpoint)
                        )
                    except DevelopmentQuoteError:
                        failure = "invalid_provider_value"
                endpoint_outcome: Literal["succeeded", "failed", "timeout"] = (
                    "succeeded" if failure is None else "failed"
                )
                if failure == "metadata_hard_timeout":
                    endpoint_outcome = "timeout"
                _finish_attempt(
                    state,
                    outcome=endpoint_outcome,
                    completed_at=completed_at,
                    failure_type=failure,
                    http_status=http_status,
                    child_pid=endpoint_result.child_pid,
                    child_exitcode=endpoint_result.child_exitcode,
                    child_terminated=endpoint_result.child_terminated,
                    child_joined=endpoint_result.child_joined,
                    remaining_children=endpoint_result.remaining_children,
                )
                if failure is None:
                    assert value is not None and clean
                    observed_at = _aware_utc(completed_at, "endpoint observation time")
                    observation = EndpointObservation(
                        request_id=request.request_id,
                        specification_hash=request.specification_hash,
                        request_hash=request.request_hash,
                        endpoint=endpoint,
                        value=value,
                        observed_at=observed_at,
                        attempt=attempt,
                        provider_response_sha256=_endpoint_response_hash(
                            request_id=request.request_id,
                            specification_hash=request.specification_hash,
                            request_hash=request.request_hash,
                            endpoint=endpoint,
                            value=value,
                            observed_at=observed_at.isoformat(),
                        ),
                    )
                    state.endpoint_results.setdefault(request.request_id, {})[endpoint] = (
                        observation
                    )
                    state = write_development_quote_checkpoint(
                        checkpoint_path,
                        _seal_checkpoint(state, updated_at=completed_at),
                        expected_checkpoint_hash=anchor,
                    )
                    anchor = state.checkpoint_hash
                    break
                state = write_development_quote_checkpoint(
                    checkpoint_path,
                    _seal_checkpoint(state, updated_at=completed_at),
                    expected_checkpoint_hash=anchor,
                )
                anchor = state.checkpoint_hash
                if failure == "invalid_provider_value" or not clean:
                    state.stop_reason = "invalid_provider_result"
                    return write_development_quote_checkpoint(
                        checkpoint_path,
                        state,
                        expected_checkpoint_hash=anchor,
                    )
                if (
                    not _retryable(failure, http_status)
                    or run_attempt == state.policy.maximum_attempts
                ):
                    state.stop_reason = "endpoint_attempts_exhausted"
                    return write_development_quote_checkpoint(
                        checkpoint_path,
                        state,
                        expected_checkpoint_hash=anchor,
                    )
    state.stop_reason = None
    return write_development_quote_checkpoint(
        checkpoint_path,
        state,
        expected_checkpoint_hash=anchor,
    )


class DevelopmentRequestQuote(BaseModel):
    """One complete, native development request's three provider observations."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    request_id: str
    specification_hash: str
    request_hash: str
    dataset: str
    schema_name: str = Field(alias="schema")
    symbols: tuple[str, ...]
    stype_in: str
    start: AwareUTCDatetime
    end_exclusive: AwareUTCDatetime
    expected_split: Literal["training", "validation"]
    purpose: str
    raw_dbn_retention_required: bool
    observation_time_source: Literal["ts_recv"] | None
    normalized_event_time_receive_fallback_allowed: Literal[False]
    record_count: int = Field(ge=0)
    billable_size_bytes: int = Field(ge=0)
    cost_usd: str
    currency: Literal["USD"] = "USD"
    quote_source: Literal["provider_response"] = "provider_response"
    provider_observed_start: AwareUTCDatetime
    provider_observed_end: AwareUTCDatetime
    endpoint_response_sha256: dict[Endpoint, str]
    attempt_sequences: tuple[int, ...]
    quote_sha256: str

    @model_validator(mode="before")
    @classmethod
    def _validate_cost_input(cls, payload: Any) -> Any:
        if isinstance(payload, Mapping):
            _strict_decimal_string(payload.get("cost_usd"), "quote cost_usd")
        return payload

    @model_validator(mode="after")
    def _validate_quote(self, info: ValidationInfo) -> DevelopmentRequestQuote:
        if set(self.endpoint_response_sha256) != set(DEVELOPMENT_ENDPOINTS):
            raise ValueError("quote endpoint response partition is incomplete")
        for value in self.endpoint_response_sha256.values():
            _require_sha256(value, "quote endpoint response SHA-256")
        expected = _quote_hash(self.model_dump(mode="json", by_alias=True))
        allow_unsealed = bool(info.context and info.context.get("allow_unsealed"))
        if not self.quote_sha256 and not allow_unsealed:
            raise ValueError("development request quote hash is required")
        if self.quote_sha256 and self.quote_sha256 != expected:
            raise ValueError("development request quote hash mismatch")
        return self


def _quote_matches_request(quote: DevelopmentRequestQuote, request: DevelopmentRequest) -> bool:
    return (
        quote.request_id,
        quote.specification_hash,
        quote.request_hash,
        quote.dataset,
        quote.schema_name,
        quote.symbols,
        quote.stype_in,
        quote.start,
        quote.end_exclusive,
        quote.expected_split,
        quote.purpose,
        quote.raw_dbn_retention_required,
        quote.observation_time_source,
        quote.normalized_event_time_receive_fallback_allowed,
    ) == (
        request.request_id,
        request.specification_hash,
        request.request_hash,
        request.dataset,
        request.schema_name,
        request.symbols,
        request.stype_in,
        request.start,
        request.end_exclusive,
        request.expected_split,
        request.purpose,
        request.raw_dbn_retention_required,
        request.observation_time_source,
        request.normalized_event_time_receive_fallback_allowed,
    )


class DevelopmentCostRollups(BaseModel):
    """Exact Decimal totals and deterministic nearest-rank distribution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cbbo_total_usd: str
    catalog_total_usd: str
    training_total_usd: str
    validation_total_usd: str
    grand_total_usd: str
    smallest_request_usd: str
    largest_request_usd: str
    median_request_usd: str
    p95_request_usd: str

    @model_validator(mode="before")
    @classmethod
    def _validate_decimal_fields(cls, payload: Any) -> Any:
        if isinstance(payload, Mapping):
            for name, value in payload.items():
                _strict_decimal_string(value, str(name))
        return payload


class DevelopmentCostEvidence(BaseModel):
    """Complete exact-scope provider cost estimates, never billing or authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["development-cost-evidence-v1"] = "development-cost-evidence-v1"
    status: Literal["complete"] = "complete"
    evidence_kind: Literal["provider_cost_estimates"] = "provider_cost_estimates"
    authorization_ready: Literal[False] = False
    purchase_authorized: Literal[False] = False
    bindings: DevelopmentQuoteBindings
    checkpoint_hash: str
    checkpoint_file_sha256: str
    observation_period_start: AwareUTCDatetime
    observation_period_end: AwareUTCDatetime
    request_count: int = Field(ge=1)
    quotes: tuple[DevelopmentRequestQuote, ...]
    rollups: DevelopmentCostRollups
    provider_operation_counters: ProviderOperationCounters
    attempt_history: tuple[DevelopmentQuoteAttempt, ...]
    evidence_hash: str

    @model_validator(mode="after")
    def _validate_evidence(self, info: ValidationInfo) -> DevelopmentCostEvidence:
        for label, value in (
            ("checkpoint hash", self.checkpoint_hash),
            ("checkpoint file SHA-256", self.checkpoint_file_sha256),
        ):
            _require_sha256(value, label)
        ids = [quote.request_id for quote in self.quotes]
        if len(ids) != len(set(ids)):
            raise ValueError("development cost evidence contains duplicate request IDs")
        expected_requests = self.bindings.request_identities
        if ids != [request.request_id for request in expected_requests]:
            raise ValueError("development cost evidence exact scope coverage mismatch")
        if any(
            not _quote_matches_request(quote, request)
            for quote, request in zip(self.quotes, expected_requests, strict=True)
        ):
            raise ValueError("development cost evidence request identity mismatch")
        if self.request_count != len(self.quotes):
            raise ValueError("development cost evidence request count mismatch")
        if not _counters_match_attempts(self.provider_operation_counters, self.attempt_history):
            raise ValueError("development cost evidence operation counter mismatch")
        if self.rollups != _rollups(self.quotes):
            raise ValueError("development cost evidence Decimal rollup mismatch")
        if self.observation_period_end < self.observation_period_start:
            raise ValueError("development cost evidence observation period is reversed")
        expected = _artifact_hash(
            self.model_dump(mode="json", by_alias=True), hash_field="evidence_hash"
        )
        allow_unsealed = bool(info.context and info.context.get("allow_unsealed"))
        if not self.evidence_hash and not allow_unsealed:
            raise ValueError("development cost evidence hash is required")
        if self.evidence_hash and self.evidence_hash != expected:
            raise ValueError("development cost evidence hash mismatch")
        return self


class DevelopmentQuoteProgressEvidence(BaseModel):
    """Explicit incomplete, resumable development quote progress."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["development-cost-progress-v1"] = "development-cost-progress-v1"
    status: Literal["incomplete"] = "incomplete"
    authorization_ready: Literal[False] = False
    purchase_authorized: Literal[False] = False
    resume_eligible: Literal[True] = True
    bindings: DevelopmentQuoteBindings
    checkpoint_hash: str
    checkpoint_file_sha256: str
    completed_request_ids: tuple[str, ...]
    pending_endpoints: dict[str, tuple[Endpoint, ...]]
    pending_schema_datasets: tuple[str, ...]
    stop_reason: StopReason | None
    retry_count: int = Field(ge=0)
    timeout_count: int = Field(ge=0)
    provider_operation_counters: ProviderOperationCounters
    attempt_history: tuple[DevelopmentQuoteAttempt, ...]
    evidence_hash: str

    @model_validator(mode="after")
    def _validate_progress(self, info: ValidationInfo) -> DevelopmentQuoteProgressEvidence:
        if not self.pending_endpoints and not self.pending_schema_datasets:
            raise ValueError("partial evidence has no pending work")
        request_ids = [request.request_id for request in self.bindings.request_identities]
        expected_pending_ids = [
            request_id for request_id in request_ids if request_id not in self.completed_request_ids
        ]
        if list(self.pending_endpoints) != expected_pending_ids:
            raise ValueError("partial evidence pending request partition mismatch")
        if self.completed_request_ids != tuple(
            request_id for request_id in request_ids if request_id not in self.pending_endpoints
        ):
            raise ValueError("partial evidence completed request partition mismatch")
        for endpoints in self.pending_endpoints.values():
            expected_endpoints = tuple(
                endpoint for endpoint in DEVELOPMENT_ENDPOINTS if endpoint in endpoints
            )
            if (
                not endpoints
                or endpoints != expected_endpoints
                or len(endpoints) != len(set(endpoints))
            ):
                raise ValueError("partial evidence endpoint partition mismatch")
        datasets = {request.dataset for request in self.bindings.request_identities}
        if not set(self.pending_schema_datasets).issubset(datasets):
            raise ValueError("partial evidence schema partition mismatch")
        if not _counters_match_attempts(self.provider_operation_counters, self.attempt_history):
            raise ValueError("partial evidence operation counter mismatch")
        _require_sha256(self.checkpoint_hash, "checkpoint hash")
        _require_sha256(self.checkpoint_file_sha256, "checkpoint file SHA-256")
        expected_hash = _artifact_hash(
            self.model_dump(mode="json", by_alias=True), hash_field="evidence_hash"
        )
        allow_unsealed = bool(info.context and info.context.get("allow_unsealed"))
        if not self.evidence_hash and not allow_unsealed:
            raise ValueError("development quote progress hash is required")
        if self.evidence_hash and self.evidence_hash != expected_hash:
            raise ValueError("development quote progress hash mismatch")
        return self


def _quote_hash(payload: Mapping[str, Any]) -> str:
    return _artifact_hash(payload, hash_field="quote_sha256")


def _nearest_rank(ordered: Sequence[Decimal], percentile: Decimal) -> Decimal:
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _rollups(quotes: Sequence[DevelopmentRequestQuote]) -> DevelopmentCostRollups:
    costs = [(quote, Decimal(quote.cost_usd)) for quote in quotes]
    ordered = sorted(cost for _, cost in costs)
    if not ordered:
        raise DevelopmentQuoteError("cannot roll up empty development quote evidence")

    def total(predicate: Callable[[DevelopmentRequestQuote], bool]) -> Decimal:
        return sum((cost for quote, cost in costs if predicate(quote)), Decimal(0))

    return DevelopmentCostRollups(
        cbbo_total_usd=str(total(lambda quote: quote.schema_name == "cbbo-1m")),
        catalog_total_usd=str(total(lambda quote: quote.schema_name != "cbbo-1m")),
        training_total_usd=str(total(lambda quote: quote.expected_split == "training")),
        validation_total_usd=str(total(lambda quote: quote.expected_split == "validation")),
        grand_total_usd=str(sum(ordered, Decimal(0))),
        smallest_request_usd=str(ordered[0]),
        largest_request_usd=str(ordered[-1]),
        median_request_usd=str(_nearest_rank(ordered, Decimal("0.5"))),
        p95_request_usd=str(_nearest_rank(ordered, Decimal("0.95"))),
    )


def _request_quote(
    request: DevelopmentRequest,
    endpoints: Mapping[Endpoint, EndpointObservation],
    attempts: Sequence[DevelopmentQuoteAttempt],
) -> DevelopmentRequestQuote:
    record = endpoints["record-count"]
    billable = endpoints["billable-size"]
    cost = endpoints["cost"]
    observations = [record.observed_at, billable.observed_at, cost.observed_at]
    payload: dict[str, Any] = {
        "request_id": request.request_id,
        "specification_hash": request.specification_hash,
        "request_hash": request.request_hash,
        "dataset": request.dataset,
        "schema": request.schema_name,
        "symbols": request.symbols,
        "stype_in": request.stype_in,
        "start": request.start.isoformat(),
        "end_exclusive": request.end_exclusive.isoformat(),
        "expected_split": request.expected_split,
        "purpose": request.purpose,
        "raw_dbn_retention_required": request.raw_dbn_retention_required,
        "observation_time_source": request.observation_time_source,
        "normalized_event_time_receive_fallback_allowed": (
            request.normalized_event_time_receive_fallback_allowed
        ),
        "record_count": record.value,
        "billable_size_bytes": billable.value,
        "cost_usd": cost.value,
        "currency": "USD",
        "quote_source": "provider_response",
        "provider_observed_start": min(observations).isoformat(),
        "provider_observed_end": max(observations).isoformat(),
        "endpoint_response_sha256": {
            endpoint: endpoints[endpoint].provider_response_sha256
            for endpoint in DEVELOPMENT_ENDPOINTS
        },
        "attempt_sequences": tuple(
            attempt.sequence for attempt in attempts if attempt.request_id == request.request_id
        ),
        "quote_sha256": "",
    }
    return _seal_model(DevelopmentRequestQuote, payload, hash_field="quote_sha256")


def build_complete_development_cost_evidence(
    *,
    state: DevelopmentQuoteCheckpoint,
    checkpoint_file_sha256: str,
    requests: Sequence[DevelopmentRequest],
) -> DevelopmentCostEvidence:
    """Build complete evidence only after exact native request/endpoint coverage."""
    _require_sha256(checkpoint_file_sha256, "checkpoint file SHA-256")
    state = _seal_checkpoint(state)
    if state.status != "complete":
        raise DevelopmentQuoteError("complete evidence requires complete endpoint coverage")
    if tuple(requests) != state.bindings.request_identities:
        raise DevelopmentQuoteError("complete evidence request inventory mismatch")
    quotes = tuple(
        _request_quote(request, state.endpoint_results[request.request_id], state.attempt_history)
        for request in requests
    )
    observed = [
        observation.observed_at
        for endpoints in state.endpoint_results.values()
        for observation in endpoints.values()
    ]
    payload: dict[str, Any] = {
        "schema_version": "development-cost-evidence-v1",
        "status": "complete",
        "evidence_kind": "provider_cost_estimates",
        "authorization_ready": False,
        "purchase_authorized": False,
        "bindings": state.bindings.model_dump(mode="json", by_alias=True),
        "checkpoint_hash": state.checkpoint_hash,
        "checkpoint_file_sha256": checkpoint_file_sha256,
        "observation_period_start": min(observed).isoformat(),
        "observation_period_end": max(observed).isoformat(),
        "request_count": len(quotes),
        "quotes": [quote.model_dump(mode="json", by_alias=True) for quote in quotes],
        "rollups": _rollups(quotes).model_dump(mode="json"),
        "provider_operation_counters": state.provider_operation_counters.model_dump(mode="json"),
        "attempt_history": [attempt.model_dump(mode="json") for attempt in state.attempt_history],
        "evidence_hash": "",
    }
    return _seal_model(DevelopmentCostEvidence, payload, hash_field="evidence_hash")


def validate_complete_development_cost_evidence(
    payload: Mapping[str, Any],
    *,
    expected_bindings: DevelopmentQuoteBindings,
    requests: Sequence[DevelopmentRequest],
) -> DevelopmentCostEvidence:
    """Validate evidence self-hashes, exact coverage, identities, and Decimal rollups."""
    raw_quotes = payload.get("quotes")
    expected_ids = [request.request_id for request in requests]
    if not isinstance(raw_quotes, list) or any(
        not isinstance(item, Mapping) for item in raw_quotes
    ):
        raise DevelopmentQuoteError("development cost evidence exact scope coverage mismatch")
    raw_ids = [cast(Mapping[str, Any], item).get("request_id") for item in raw_quotes]
    if any(not isinstance(request_id, str) for request_id in raw_ids):
        raise DevelopmentQuoteError("development cost evidence exact scope coverage mismatch")
    if raw_ids != expected_ids or len(set(raw_ids)) != len(expected_ids):
        raise DevelopmentQuoteError("development cost evidence exact scope coverage mismatch")
    try:
        evidence = DevelopmentCostEvidence.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise DevelopmentQuoteError(f"invalid development cost evidence: {exc}") from exc
    if evidence.bindings != expected_bindings:
        raise DevelopmentQuoteError("development cost evidence binding mismatch")
    actual_ids = [quote.request_id for quote in evidence.quotes]
    if actual_ids != expected_ids or len(set(actual_ids)) != len(expected_ids):
        raise DevelopmentQuoteError("development cost evidence exact scope coverage mismatch")
    for request, quote in zip(requests, evidence.quotes, strict=True):
        expected_identity = (
            request.request_id,
            request.specification_hash,
            request.request_hash,
            request.dataset,
            request.schema_name,
            request.symbols,
            request.stype_in,
            request.start,
            request.end_exclusive,
            request.expected_split,
            request.purpose,
            request.raw_dbn_retention_required,
            request.observation_time_source,
            request.normalized_event_time_receive_fallback_allowed,
        )
        actual_identity = (
            quote.request_id,
            quote.specification_hash,
            quote.request_hash,
            quote.dataset,
            quote.schema_name,
            quote.symbols,
            quote.stype_in,
            quote.start,
            quote.end_exclusive,
            quote.expected_split,
            quote.purpose,
            quote.raw_dbn_retention_required,
            quote.observation_time_source,
            quote.normalized_event_time_receive_fallback_allowed,
        )
        if actual_identity != expected_identity:
            raise DevelopmentQuoteError("development cost evidence request identity mismatch")
    if evidence.rollups != _rollups(evidence.quotes):
        raise DevelopmentQuoteError("development cost evidence Decimal rollup mismatch")
    return evidence


def build_partial_development_quote_evidence(
    *,
    state: DevelopmentQuoteCheckpoint,
    checkpoint_file_sha256: str,
) -> DevelopmentQuoteProgressEvidence:
    """Build explicit resumable progress without claiming complete evidence."""
    _require_sha256(checkpoint_file_sha256, "checkpoint file SHA-256")
    state = _seal_checkpoint(state)
    if state.status != "incomplete":
        raise DevelopmentQuoteError("partial evidence requires pending work")
    payload: dict[str, Any] = {
        "schema_version": "development-cost-progress-v1",
        "status": "incomplete",
        "authorization_ready": False,
        "purchase_authorized": False,
        "resume_eligible": True,
        "bindings": state.bindings.model_dump(mode="json", by_alias=True),
        "checkpoint_hash": state.checkpoint_hash,
        "checkpoint_file_sha256": checkpoint_file_sha256,
        "completed_request_ids": state.completed_request_ids,
        "pending_endpoints": state.pending_endpoints,
        "pending_schema_datasets": state.pending_schema_datasets,
        "stop_reason": state.stop_reason,
        "retry_count": state.retry_count,
        "timeout_count": state.timeout_count,
        "provider_operation_counters": state.provider_operation_counters.model_dump(mode="json"),
        "attempt_history": [attempt.model_dump(mode="json") for attempt in state.attempt_history],
        "evidence_hash": "",
    }
    return _seal_model(
        DevelopmentQuoteProgressEvidence,
        payload,
        hash_field="evidence_hash",
    )
