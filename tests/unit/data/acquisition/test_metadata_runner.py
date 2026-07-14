"""Process-boundary and checkpoint regression tests for metadata preparation."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.metadata_runner import (
    MetadataCheckpoint,
    MetadataOperationEvent,
    load_checkpoint,
    run_isolated_metadata_request,
    write_checkpoint,
)

pytestmark = pytest.mark.unit


def _event(request: dict[str, Any], endpoint: str, outcome: str = "started") -> dict[str, Any]:
    return MetadataOperationEvent(
        run_id="run",
        request_index=1,
        request_count=25,
        request_id=request["request_id"],
        dataset=request["dataset"],
        schema_name=request["schema"],
        session_date=request.get("session_date"),
        endpoint=endpoint,
        attempt=1,
        started_at=datetime.now(UTC).isoformat(),
        completed_at=datetime.now(UTC).isoformat() if outcome != "started" else None,
        elapsed_seconds=0.0 if outcome != "started" else None,
        outcome=outcome,
        child_pid=1,
    ).model_dump(mode="json")


def cooperative_worker(output, request, *_args) -> None:
    for endpoint in ("record-count", "billable-size", "cost"):
        output.put(("event", _event(request, endpoint)))
        output.put(("event", _event(request, endpoint, "succeeded")))
    output.put(("result", {"record-count": 10, "billable-size": 100, "cost": "0.01"}))


def cost_hang_worker(output, request, *_args) -> None:
    for endpoint in ("record-count", "billable-size"):
        output.put(("event", _event(request, endpoint)))
        output.put(("event", _event(request, endpoint, "succeeded")))
    output.put(("event", _event(request, "cost")))
    time.sleep(60)


def test_spawn_child_completes_and_joins(arcx_request) -> None:
    result = run_isolated_metadata_request(
        request=arcx_request,
        run_id="run",
        request_index=1,
        request_count=25,
        attempt=1,
        timeout_seconds=10,
        worker=cooperative_worker,
    )
    assert result.estimate is not None
    assert result.child_joined is True
    assert result.child_terminated is False
    assert result.remaining_children == 0


def test_hung_cost_endpoint_is_killed_and_identified(arcx_request) -> None:
    started = time.monotonic()
    result = run_isolated_metadata_request(
        request=arcx_request,
        run_id="run",
        request_index=1,
        request_count=25,
        attempt=1,
        timeout_seconds=5,
        worker=cost_hang_worker,
    )
    assert time.monotonic() - started < 8
    assert result.failure_type == "metadata_hard_timeout"
    assert result.failed_endpoint == "cost"
    assert result.child_terminated is True
    assert result.child_joined is True
    assert result.remaining_children == 0


def _checkpoint(now: datetime) -> MetadataCheckpoint:
    return MetadataCheckpoint(
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        pilot_config_hash="c" * 64,
        calendar_version="1",
        databento_client_version="0.81.0",
        ordered_request_specification_hashes=["r" * 64],
        pending_request_ids=["request"],
    )


def test_checkpoint_is_atomic_and_hash_bound(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint = _checkpoint(datetime.now(UTC))
    write_checkpoint(path, checkpoint)
    expected = {
        key: getattr(checkpoint, key)
        for key in (
            "source_manifest_hash",
            "split_manifest_hash",
            "acquisition_policy_hash",
            "pilot_config_hash",
            "calendar_version",
            "databento_client_version",
            "estimator_version",
            "ordered_request_specification_hashes",
        )
    }
    assert load_checkpoint(path, expected=expected, maximum_age_minutes=30).run_id
    with pytest.raises(ValueError, match="mismatch"):
        load_checkpoint(
            path,
            expected={**expected, "pilot_config_hash": "x" * 64},
            maximum_age_minutes=30,
        )
    assert not path.with_name(path.name + ".partial").exists()


def test_checkpoint_rejects_expired_and_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint = _checkpoint(datetime.now(UTC) - timedelta(hours=1))
    write_checkpoint(path, checkpoint)
    expected = {
        "source_manifest_hash": checkpoint.source_manifest_hash,
        "split_manifest_hash": checkpoint.split_manifest_hash,
        "acquisition_policy_hash": checkpoint.acquisition_policy_hash,
        "pilot_config_hash": checkpoint.pilot_config_hash,
        "calendar_version": checkpoint.calendar_version,
        "databento_client_version": checkpoint.databento_client_version,
        "estimator_version": checkpoint.estimator_version,
        "ordered_request_specification_hashes": checkpoint.ordered_request_specification_hashes,
    }
    with pytest.raises(ValueError, match="expired"):
        load_checkpoint(path, expected=expected, maximum_age_minutes=30)
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        load_checkpoint(path, expected=expected, maximum_age_minutes=30)
