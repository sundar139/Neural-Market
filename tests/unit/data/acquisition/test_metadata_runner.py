"""Process-boundary and checkpoint regression tests for metadata preparation."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.cost_estimation import (
    ACQUISITION_FEED_MODE,
    parse_unit_price_snapshot,
)
from neuralmarket.data.acquisition.metadata_runner import (
    IsolatedMetadataResult,
    MetadataCheckpoint,
    MetadataEndpointResult,
    MetadataOperationEvent,
    UnitPriceSnapshotCache,
    build_provider_cost_samples,
    cost_fallback_trigger,
    derive_cost_endpoint_result,
    endpoint_response_hash,
    load_checkpoint,
    plan_cost_rollup,
    run_isolated_metadata_request,
    run_isolated_unit_price_request,
    write_checkpoint,
)
from neuralmarket.data.acquisition.requests import AcquisitionRequest
from neuralmarket.data.errors import CostEstimationError

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


def test_checkpoint_rejects_endpoint_hash_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint = _checkpoint(datetime.now(UTC))
    checkpoint.endpoint_results["request"] = {
        "record-count": MetadataEndpointResult(
            value=10,
            completed_at=datetime.now(UTC).isoformat(),
            response_hash=endpoint_response_hash("record-count", 10),
        )
    }
    write_checkpoint(path, checkpoint)
    payload = path.read_text(encoding="utf-8").replace(
        endpoint_response_hash("record-count", 10), "0" * 64
    )
    path.write_text(payload, encoding="utf-8")
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
    with pytest.raises(ValueError, match="endpoint_hash"):
        load_checkpoint(path, expected=expected, maximum_age_minutes=30)


# --- Derived-cost fallback integration ---------------------------------------

OPRA = "OPRA.PILLAR"
CBBO = "cbbo-1m"
ACCOUNT = "pilot-databento-historical-v1"
REF_BILLABLE = 5209600
REF_COST = "0.009703636169"
BLK_BILLABLE = 5616000


def _opra_request() -> AcquisitionRequest:
    now = datetime(2019, 1, 2, tzinfo=UTC)
    return AcquisitionRequest(
        request_id="d5352ffb04e4bc83",
        wave="opra_closing_quotes",
        dataset=OPRA,
        schema=CBBO,
        symbols=("SPY.OPT",),
        stype_in="parent",
        stype_out="instrument_id",
        start=now,
        end_exclusive=now + timedelta(days=1),
        encoding="dbn",
        compression="zstd",
        expected_split="training",
        session_date=now.date(),
        calendar="XNYS",
        estimated_record_count=70200,
        estimated_billable_size=BLK_BILLABLE,
        estimated_cost="0.01",
        currency="USD",
        request_hash="8" * 64,
    )


def _snapshot(price: str = "2.0"):
    return parse_unit_price_snapshot(
        [{"mode": ACQUISITION_FEED_MODE, "schemas": {CBBO: price}}],
        dataset=OPRA,
        feed_mode=ACQUISITION_FEED_MODE,
        databento_client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
    )


def _endpoint(endpoint: str, value: Any, **extra: Any) -> MetadataEndpointResult:
    return MetadataEndpointResult(
        value=value,
        completed_at=datetime.now(UTC).isoformat(),
        response_hash=endpoint_response_hash(endpoint, value),  # type: ignore[arg-type]
        **extra,
    )


def _billable_result() -> MetadataEndpointResult:
    return _endpoint("billable-size", BLK_BILLABLE)


def _isolated_cost_failure(
    http_status: int | None, exc_class: str | None
) -> IsolatedMetadataResult:
    event = MetadataOperationEvent(
        run_id="run",
        request_index=5,
        request_count=25,
        request_id="d5352ffb04e4bc83",
        dataset=OPRA,
        schema_name=CBBO,
        session_date="2019-01-02",
        endpoint="cost",
        attempt=3,
        started_at=datetime.now(UTC).isoformat(),
        completed_at=datetime.now(UTC).isoformat(),
        elapsed_seconds=60.0,
        outcome="failed",
        exception_class=exc_class,
        http_status=http_status,
        child_pid=1,
    )
    return IsolatedMetadataResult(
        endpoint_values={},
        events=[event],
        failure_type=exc_class or "BentoServerError",
        failed_endpoint="cost",
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _checkpoint_with_reference() -> MetadataCheckpoint:
    now = datetime.now(UTC)
    cp = MetadataCheckpoint(
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        pilot_config_hash="c" * 64,
        calendar_version="1",
        databento_client_version="0.81.0",
        ordered_request_specification_hashes=["r" * 64],
        pending_request_ids=["d5352ffb04e4bc83"],
    )
    cp.endpoint_results["ref"] = {
        "record-count": _endpoint("record-count", 70200),
        "billable-size": _endpoint("billable-size", REF_BILLABLE),
        "cost": _endpoint("cost", REF_COST, cost_source="provider_response"),
    }
    cp.completed_estimates["ref"] = {
        "dataset": OPRA,
        "schema": CBBO,
        "symbol": "SPY.OPT",
        "stype_in": "parent",
        "window_start": "2019-01-24T00:00:00+00:00",
        "window_end": "2019-02-01T00:00:00+00:00",
        "record_count": 70200,
        "billable_size_bytes": REF_BILLABLE,
        "cost_usd": REF_COST,
        "retries": 0,
    }
    cp.endpoint_results["d5352ffb04e4bc83"] = {
        "record-count": _endpoint("record-count", 70200),
        "billable-size": _billable_result(),
    }
    return cp


def test_fallback_trigger_eligible_5xx_and_timeout() -> None:
    assert cost_fallback_trigger(_isolated_cost_failure(504, "BentoServerError")) == (504, None)
    assert cost_fallback_trigger(_isolated_cost_failure(503, "BentoServerError")) == (503, None)
    timeout = _isolated_cost_failure(None, "ConnectionError")
    assert cost_fallback_trigger(timeout) == (None, "provider_network_timeout")


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 429])
def test_fallback_trigger_blocks_prohibited_status(status: int) -> None:
    assert cost_fallback_trigger(_isolated_cost_failure(status, "BentoClientError")) is None


def test_fallback_trigger_ignores_non_cost_endpoint() -> None:
    result = _isolated_cost_failure(504, "BentoServerError").model_copy(
        update={"failed_endpoint": "billable-size"}
    )
    assert cost_fallback_trigger(result) is None


def test_build_provider_cost_samples_selects_compatible_only() -> None:
    cp = _checkpoint_with_reference()
    samples = build_provider_cost_samples(
        cp,
        dataset=OPRA,
        schema=CBBO,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
    )
    assert len(samples) == 1
    assert samples[0].billable_size_bytes == REF_BILLABLE
    assert samples[0].provider_cost_usd == Decimal(REF_COST)
    assert (
        build_provider_cost_samples(
            cp,
            dataset=OPRA,
            schema="definition",
            feed_mode=ACQUISITION_FEED_MODE,
            account_pricing_context=ACCOUNT,
        )
        == []
    )


def test_derive_cost_endpoint_result_completes_with_derived_provenance() -> None:
    cp = _checkpoint_with_reference()
    samples = build_provider_cost_samples(
        cp,
        dataset=OPRA,
        schema=CBBO,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
    )
    result = derive_cost_endpoint_result(
        request=_opra_request(),
        billable_size_result=_billable_result(),
        snapshot=_snapshot(),
        samples=samples,
        account_pricing_context=ACCOUNT,
        failure_http_status=504,
        failure_category=None,
        now_utc=datetime.now(UTC).isoformat(),
    )
    assert result.cost_source == "derived_response"
    raw = Decimal(BLK_BILLABLE) * Decimal("2.0") / Decimal(2**30)
    assert Decimal(str(result.raw_cost_usd)) == raw
    assert Decimal(str(result.conservative_cost_usd)) == raw * Decimal("1.25")
    assert result.derivation_hash
    assert result.fallback_trigger_http_status == 504


def test_derive_cost_endpoint_result_fails_closed_without_samples() -> None:
    with pytest.raises(CostEstimationError):
        derive_cost_endpoint_result(
            request=_opra_request(),
            billable_size_result=_billable_result(),
            snapshot=_snapshot(),
            samples=[],
            account_pricing_context=ACCOUNT,
            failure_http_status=504,
            failure_category=None,
            now_utc=datetime.now(UTC).isoformat(),
        )


def test_derive_cost_endpoint_result_fails_closed_on_prohibited_status() -> None:
    cp = _checkpoint_with_reference()
    samples = build_provider_cost_samples(
        cp,
        dataset=OPRA,
        schema=CBBO,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
    )
    with pytest.raises(CostEstimationError):
        derive_cost_endpoint_result(
            request=_opra_request(),
            billable_size_result=_billable_result(),
            snapshot=_snapshot(),
            samples=samples,
            account_pricing_context=ACCOUNT,
            failure_http_status=403,
            failure_category="entitlement",
            now_utc=datetime.now(UTC).isoformat(),
        )


def _completed_endpoints(cp: MetadataCheckpoint) -> int:
    return sum(len(endpoints) for endpoints in cp.endpoint_results.values())


def test_fixture_checkpoint_fallback_advances_16_to_17() -> None:
    cp = _checkpoint_with_reference()
    for i in range(11):
        cp.endpoint_results[f"filler-{i}"] = {"record-count": _endpoint("record-count", i)}
    assert _completed_endpoints(cp) == 16
    assert 75 - _completed_endpoints(cp) == 59

    samples = build_provider_cost_samples(
        cp,
        dataset=OPRA,
        schema=CBBO,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
    )
    derived = derive_cost_endpoint_result(
        request=_opra_request(),
        billable_size_result=cp.endpoint_results["d5352ffb04e4bc83"]["billable-size"],
        snapshot=_snapshot(),
        samples=samples,
        account_pricing_context=ACCOUNT,
        failure_http_status=504,
        failure_category=None,
        now_utc=datetime.now(UTC).isoformat(),
    )
    cp.endpoint_results["d5352ffb04e4bc83"]["cost"] = derived
    assert _completed_endpoints(cp) == 17
    assert 75 - _completed_endpoints(cp) == 58


def test_plan_cost_rollup_mixes_provider_and_derived() -> None:
    cp = _checkpoint_with_reference()
    raw_derived = Decimal(BLK_BILLABLE) * Decimal("2.0") / Decimal(2**30)
    cp.endpoint_results["d5352ffb04e4bc83"]["cost"] = MetadataEndpointResult(
        value=str(raw_derived),
        completed_at=datetime.now(UTC).isoformat(),
        response_hash=endpoint_response_hash("cost", str(raw_derived)),
        cost_source="derived_response",
        raw_cost_usd=str(raw_derived),
        conservative_cost_usd=str(raw_derived * Decimal("1.25")),
    )
    cp.completed_estimates["d5352ffb04e4bc83"] = {
        "dataset": OPRA,
        "schema": CBBO,
        "symbol": "SPY.OPT",
        "stype_in": "parent",
        "window_start": "2019-01-02T00:00:00+00:00",
        "window_end": "2019-01-03T00:00:00+00:00",
        "record_count": 70200,
        "billable_size_bytes": BLK_BILLABLE,
        "cost_usd": str(raw_derived),
        "retries": 0,
    }
    summary = plan_cost_rollup(cp, tracked_total_usd=Decimal("0.46"))
    assert summary.provider_cost_count == 1
    assert summary.derived_cost_count == 1
    assert summary.raw_total_usd == Decimal(REF_COST) + raw_derived
    assert summary.conservative_total_usd == Decimal(REF_COST) + raw_derived * Decimal("1.25")
    assert summary.within_all_gates


def test_unit_price_snapshot_cache_loads_once_per_dataset() -> None:
    calls: list[str] = []

    def loader(dataset: str):
        calls.append(dataset)
        return _snapshot()

    cache = UnitPriceSnapshotCache(loader)
    cache.get(OPRA)
    cache.get(OPRA)
    cache.get("ARCX.PILLAR")
    assert cache.load_count == 2
    assert calls == [OPRA, "ARCX.PILLAR"]


def test_legacy_checkpoint_cost_without_source_loads_as_provider(tmp_path: Path) -> None:
    cp = _checkpoint_with_reference()
    cp.endpoint_results["ref"]["cost"] = MetadataEndpointResult(
        value=REF_COST,
        completed_at=datetime.now(UTC).isoformat(),
        response_hash=endpoint_response_hash("cost", REF_COST),
    )
    path = tmp_path / "legacy.json"
    write_checkpoint(path, cp)
    before = path.read_text(encoding="utf-8")
    expected = {
        key: getattr(cp, key)
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
    loaded = load_checkpoint(path, expected=expected, maximum_age_minutes=30)
    assert loaded.endpoint_results["ref"]["cost"].cost_source is None
    summary = plan_cost_rollup(loaded, tracked_total_usd=Decimal("0.46"))
    assert summary.provider_cost_count == 1
    assert summary.derived_cost_count == 0
    assert path.read_text(encoding="utf-8") == before


def unitprice_cooperative_worker(output, dataset, *_args) -> None:
    snapshot = parse_unit_price_snapshot(
        [{"mode": ACQUISITION_FEED_MODE, "schemas": {"cbbo-1m": "2.0"}}],
        dataset=dataset,
        feed_mode=ACQUISITION_FEED_MODE,
        databento_client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
    )
    output.put(("snapshot", snapshot.__dict__))


def unitprice_hang_worker(output, dataset, *_args) -> None:
    time.sleep(60)


def test_isolated_unit_price_child_completes_and_joins() -> None:
    result = run_isolated_unit_price_request(
        dataset=OPRA,
        client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
        timeout_seconds=10,
        worker=unitprice_cooperative_worker,
    )
    assert result.snapshot is not None
    assert result.snapshot.price_for("cbbo-1m") == Decimal("2.0")
    assert result.child_joined is True
    assert result.child_terminated is False
    assert result.remaining_children == 0


def test_isolated_unit_price_child_timeout_is_killed() -> None:
    started = time.monotonic()
    result = run_isolated_unit_price_request(
        dataset=OPRA,
        client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
        timeout_seconds=3,
        worker=unitprice_hang_worker,
    )
    assert time.monotonic() - started < 8
    assert result.failure_type == "unit_price_hard_timeout"
    assert result.child_terminated is True
    assert result.remaining_children == 0
