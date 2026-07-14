"""Process-isolated, checkpointed Databento metadata estimation."""

from __future__ import annotations

import importlib.metadata
import json
import multiprocessing
import os
import queue
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.providers import DatabentoMetadataProvider
from neuralmarket.data.acquisition.requests import AcquisitionRequest

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
        events=events,
        child_pid=child.pid or -1,
        child_exitcode=child.exitcode,
        child_joined=not child.is_alive(),
        remaining_children=active,
    )


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
    return checkpoint


def checkpoint_client_version() -> str:
    """Return the exact Databento version bound into checkpoints."""
    return importlib.metadata.version("databento")
