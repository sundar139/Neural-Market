"""Regression tests for the real Databento 0.81.0 unit-price response shape.

The installed SDK returns ``metadata.list_unit_prices`` as a list of maps of
feed mode to schema to unit price, e.g.
``[{"historical-streaming": {"cbbo-1m": 2.0}}]`` (prices are JSON floats). These
tests exercise the production sanitizer and snapshot parser against that shape
plus the previously supported shapes, entirely offline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.cost_estimation import (
    ACQUISITION_FEED_MODE,
    ProviderCostSample,
    parse_unit_price_snapshot,
)
from neuralmarket.data.acquisition.metadata_runner import (
    MetadataEndpointResult,
    _sanitize_unit_price_response,
    derive_cost_endpoint_result,
    endpoint_response_hash,
    process_unit_price_response,
    run_isolated_unit_price_request,
)
from neuralmarket.data.acquisition.requests import AcquisitionRequest
from neuralmarket.data.errors import CostEstimationError

pytestmark = pytest.mark.unit

CBBO = "cbbo-1m"
DATASET = "OPRA.PILLAR"
FEED_MODE = ACQUISITION_FEED_MODE
ACCOUNT = "pilot-databento-historical-v1"
REF_BILLABLE = 5209600
REF_COST = "0.009703636169"
BLK_BILLABLE = 5616000

# The observed real SDK shape: a list of maps of mode -> {schema: float}.
REAL_SINGLE = [{ACQUISITION_FEED_MODE: {CBBO: 2.0}}]


@pytest.fixture(autouse=True)
def _forbid_real_databento(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail immediately if any in-process real Databento client is constructed."""
    import databento

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("real Databento client construction attempted in an offline test")

    monkeypatch.setattr(databento, "Historical", _boom)


def _parse(blocks: list[dict[str, Any]]):
    return parse_unit_price_snapshot(
        blocks,
        dataset=DATASET,
        feed_mode=ACQUISITION_FEED_MODE,
        databento_client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
    )


def _opra_request() -> AcquisitionRequest:
    now = datetime(2019, 1, 2, tzinfo=UTC)
    return AcquisitionRequest(
        request_id="d5352ffb04e4bc83",
        wave="opra_closing_quotes",
        dataset=DATASET,
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


# --- Supported shapes --------------------------------------------------------


def test_real_shape_single_mode() -> None:
    blocks = _sanitize_unit_price_response(REAL_SINGLE)
    assert blocks == [{"mode": ACQUISITION_FEED_MODE, "schemas": {CBBO: "2.0"}}]
    snapshot = _parse(blocks)
    assert snapshot.feed_mode == ACQUISITION_FEED_MODE
    assert snapshot.price_for(CBBO) == Decimal("2.0")


def test_real_shape_multiple_modes_in_one_item() -> None:
    raw = [{ACQUISITION_FEED_MODE: {CBBO: 2.0}, "historical-download": {CBBO: 3.0}}]
    blocks = _sanitize_unit_price_response(raw)
    assert [b["mode"] for b in blocks] == [ACQUISITION_FEED_MODE, "historical-download"]
    assert _parse(blocks).price_for(CBBO) == Decimal("2.0")


def test_real_shape_multiple_list_items_preserved() -> None:
    raw = [
        {"historical": {CBBO: 1.0}},
        {ACQUISITION_FEED_MODE: {CBBO: 2.0}},
        {"live": {CBBO: 4.0}},
    ]
    blocks = _sanitize_unit_price_response(raw)
    assert [b["mode"] for b in blocks] == ["historical", ACQUISITION_FEED_MODE, "live"]


def test_duplicate_compatible_modes_preserved_then_rejected() -> None:
    raw = [{ACQUISITION_FEED_MODE: {CBBO: 2.0}}, {ACQUISITION_FEED_MODE: {CBBO: 3.0}}]
    blocks = _sanitize_unit_price_response(raw)
    assert len(blocks) == 2  # not merged
    with pytest.raises(CostEstimationError, match="duplicate"):
        _parse(blocks)


def test_legacy_canonical_list_shape_supported() -> None:
    raw = [{"mode": ACQUISITION_FEED_MODE, "schemas": {CBBO: "2.0"}}]
    assert _parse(_sanitize_unit_price_response(raw)).price_for(CBBO) == Decimal("2.0")


def test_top_level_dict_shape_supported() -> None:
    raw = {ACQUISITION_FEED_MODE: {CBBO: 2.0}, "historical": {CBBO: 1.0}}
    blocks = _sanitize_unit_price_response(raw)
    assert {b["mode"] for b in blocks} == {ACQUISITION_FEED_MODE, "historical"}
    assert _parse(blocks).price_for(CBBO) == Decimal("2.0")


# --- Fail-closed structures --------------------------------------------------


def test_malformed_mode_value_fails_closed() -> None:
    with pytest.raises(CostEstimationError):
        _sanitize_unit_price_response([{ACQUISITION_FEED_MODE: "not-a-schema-map"}])


def test_mixed_valid_and_malformed_fails_entirely() -> None:
    raw = [{ACQUISITION_FEED_MODE: {CBBO: 2.0}}, {"historical": "broken"}]
    with pytest.raises(CostEstimationError):
        _sanitize_unit_price_response(raw)


def test_empty_mode_mapping_fails_closed() -> None:
    with pytest.raises(CostEstimationError):
        _sanitize_unit_price_response([{ACQUISITION_FEED_MODE: {}}])


@pytest.mark.parametrize(
    "raw",
    [
        None,
        1,
        2.0,
        "string",
        [None],
        [1],
        ["x"],
        [{"": {CBBO: 2.0}}],
        [{ACQUISITION_FEED_MODE: []}],
        [{ACQUISITION_FEED_MODE: None}],
    ],
)
def test_structurally_malformed_inputs_fail_closed(raw: Any) -> None:
    with pytest.raises(CostEstimationError):
        _sanitize_unit_price_response(raw)


def test_empty_list_yields_no_blocks_and_parser_fails_closed() -> None:
    blocks = _sanitize_unit_price_response([])
    assert blocks == []
    with pytest.raises(CostEstimationError, match="no 'historical-streaming'"):
        _parse(blocks)


@pytest.mark.parametrize("price", [True, "0", "-2.0", "nan", "inf", "-inf", "abc"])
def test_invalid_prices_rejected_downstream(price: Any) -> None:
    blocks = _sanitize_unit_price_response([{ACQUISITION_FEED_MODE: {CBBO: price}}])
    with pytest.raises(CostEstimationError):
        _parse(blocks)


def test_sanitizer_output_carries_only_mode_and_schemas() -> None:
    for block in _sanitize_unit_price_response(REAL_SINGLE):
        assert set(block) == {"mode", "schemas"}
    with pytest.raises(CostEstimationError) as excinfo:
        _sanitize_unit_price_response([{ACQUISITION_FEED_MODE: "bad"}])
    message = str(excinfo.value).lower()
    assert "api" not in message and "key" not in message and "historical(" not in message


# --- Child-process integration ----------------------------------------------


def _real_shape_worker(output, dataset, client_version, retrieved_at_utc, expires_at_utc) -> None:
    from neuralmarket.data.acquisition import cost_estimation, metadata_runner

    feed_mode = cost_estimation.ACQUISITION_FEED_MODE
    raw = [{feed_mode: {"cbbo-1m": 2.0}}]
    snapshot = cost_estimation.parse_unit_price_snapshot(
        metadata_runner._sanitize_unit_price_response(raw),
        dataset=dataset,
        feed_mode=feed_mode,
        databento_client_version=client_version,
        retrieved_at_utc=retrieved_at_utc,
        expires_at_utc=expires_at_utc,
    )
    output.put(("snapshot", snapshot.__dict__))


def test_isolated_child_handles_real_shape() -> None:
    result = run_isolated_unit_price_request(
        dataset=DATASET,
        client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
        timeout_seconds=10,
        worker=_real_shape_worker,
    )
    assert result.snapshot is not None
    assert result.snapshot.price_for(CBBO) == Decimal("2.0")
    assert result.child_joined is True
    assert result.child_terminated is False
    assert result.remaining_children == 0


# --- Offline fallback readiness ----------------------------------------------


def test_derived_fallback_succeeds_with_real_shape_snapshot() -> None:
    snapshot = _parse(_sanitize_unit_price_response(REAL_SINGLE))
    billable = MetadataEndpointResult(
        value=BLK_BILLABLE,
        completed_at=datetime.now(UTC).isoformat(),
        response_hash=endpoint_response_hash("billable-size", BLK_BILLABLE),
    )
    samples = [
        ProviderCostSample(
            dataset=DATASET,
            schema=CBBO,
            feed_mode=ACQUISITION_FEED_MODE,
            account_pricing_context=ACCOUNT,
            billable_size_bytes=REF_BILLABLE,
            provider_cost_usd=Decimal(REF_COST),
        )
    ]
    result = derive_cost_endpoint_result(
        request=_opra_request(),
        billable_size_result=billable,
        snapshot=snapshot,
        samples=samples,
        account_pricing_context=ACCOUNT,
        failure_http_status=504,
        failure_category=None,
        now_utc=datetime.now(UTC).isoformat(),
    )
    raw = Decimal(BLK_BILLABLE) * Decimal("2.0") / Decimal(2**30)
    assert result.cost_source == "derived_response"
    assert Decimal(str(result.raw_cost_usd)) == raw
    assert Decimal(str(result.conservative_cost_usd)) == raw * Decimal("1.25")
    assert result.response_hash == endpoint_response_hash("cost", str(raw))


# --- Confirmed Databento 0.81.0 form: {"mode", "unit_prices"} -----------------

_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "fixtures/data/acquisition/databento_unit_prices_v0_81.json"
)


def _confirmed() -> list[dict[str, Any]]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def test_confirmed_single_item_sanitizes_and_parses() -> None:
    raw = [{"mode": FEED_MODE, "unit_prices": {CBBO: 2.0}}]
    blocks = _sanitize_unit_price_response(raw)
    assert blocks == [{"mode": FEED_MODE, "schemas": {CBBO: "2.0"}}]
    assert _parse(blocks).price_for(CBBO) == Decimal("2.0")


def test_confirmed_three_item_sequence_selects_target() -> None:
    raw = _confirmed()
    blocks = _sanitize_unit_price_response(raw)
    assert [b["mode"] for b in blocks] == [
        FEED_MODE,
        "historical-download",
        "another-nontarget-mode",
    ]
    snapshot = _parse(blocks)
    assert snapshot.feed_mode == FEED_MODE
    assert snapshot.price_for(CBBO) == Decimal("2.0")
    # All 12 schemas preserved for the target mode.
    assert len(snapshot.schema_prices) == 12
    assert snapshot.price_for("definition") == Decimal("1.0")


def test_confirmed_form_does_not_mutate_raw() -> None:
    raw = _confirmed()
    before = json.dumps(raw, sort_keys=True)
    _sanitize_unit_price_response(raw)
    assert json.dumps(raw, sort_keys=True) == before
    assert "unit_prices" in raw[0] and "schemas" not in raw[0]


def test_confirmed_form_hash_stable_for_equivalent_input() -> None:
    a = _parse(_sanitize_unit_price_response([{"mode": FEED_MODE, "unit_prices": {CBBO: 2.0}}]))
    b = _parse(_sanitize_unit_price_response([{"mode": FEED_MODE, "schemas": {CBBO: "2.0"}}]))
    assert a.snapshot_hash == b.snapshot_hash


def test_confirmed_duplicate_mode_rejected() -> None:
    raw = [
        {"mode": FEED_MODE, "unit_prices": {CBBO: 2.0}},
        {"mode": FEED_MODE, "unit_prices": {CBBO: 3.0}},
    ]
    blocks = _sanitize_unit_price_response(raw)
    assert len(blocks) == 2
    with pytest.raises(CostEstimationError, match="duplicate"):
        _parse(blocks)


def test_confirmed_missing_target_mode_rejected() -> None:
    raw = [{"mode": "historical-download", "unit_prices": {CBBO: 3.0}}]
    with pytest.raises(CostEstimationError, match="no 'historical-streaming'"):
        _parse(_sanitize_unit_price_response(raw))


def test_confirmed_missing_target_schema_builds_but_lookup_fails() -> None:
    raw = [{"mode": FEED_MODE, "unit_prices": {"trades": 1.0}}]
    snapshot = _parse(_sanitize_unit_price_response(raw))
    with pytest.raises(CostEstimationError):
        snapshot.price_for(CBBO)


@pytest.mark.parametrize(
    "raw",
    [
        [{"mode": FEED_MODE, "unit_prices": {}}],  # empty unit_prices
        [{"mode": FEED_MODE, "unit_prices": "x"}],  # nonmapping unit_prices
        [{"mode": "", "unit_prices": {CBBO: 2.0}}],  # empty mode
        [{"unit_prices": {CBBO: 2.0}}],  # mode missing
        [{"mode": FEED_MODE}],  # wrapper missing
        [{"mode": FEED_MODE, "schemas": {CBBO: 2.0}, "unit_prices": {CBBO: 2.0}}],  # both
        [{"mode": FEED_MODE, "unit_prices": {CBBO: 2.0}, "note": "x"}],  # unknown sibling
    ],
)
def test_confirmed_malformed_forms_fail_closed(raw: Any) -> None:
    with pytest.raises(CostEstimationError):
        _sanitize_unit_price_response(raw)


@pytest.mark.parametrize("price", [True, "0", "-2.0", "nan", "inf", "-inf"])
def test_confirmed_invalid_prices_rejected_downstream(price: Any) -> None:
    raw = [{"mode": FEED_MODE, "unit_prices": {CBBO: price}}]
    with pytest.raises(CostEstimationError):
        _parse(_sanitize_unit_price_response(raw))


def _confirmed_worker(output, dataset, client_version, retrieved_at_utc, expires_at_utc) -> None:
    from neuralmarket.data.acquisition import metadata_runner

    output.put(
        metadata_runner.process_unit_price_response(
            [{"mode": "historical-streaming", "unit_prices": {"cbbo-1m": 2.0}}],
            dataset=dataset,
            client_version=client_version,
            retrieved_at_utc=retrieved_at_utc,
            expires_at_utc=expires_at_utc,
        )
    )


def test_confirmed_child_integration() -> None:
    result = run_isolated_unit_price_request(
        dataset=DATASET,
        client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
        timeout_seconds=10,
        worker=_confirmed_worker,
    )
    assert result.snapshot is not None
    assert result.diagnostic is None
    assert result.snapshot.feed_mode == FEED_MODE
    assert result.snapshot.price_for(CBBO) == Decimal("2.0")
    assert result.child_joined is True
    assert result.child_terminated is False
    assert result.child_exit_code == 0
    assert result.remaining_children == 0


def test_confirmed_form_produces_no_failure_diagnostic() -> None:
    kind, _payload = process_unit_price_response(
        _confirmed(),
        dataset=DATASET,
        client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
    )
    assert kind == "snapshot"


def test_confirmed_form_derived_fallback() -> None:
    snapshot = _parse(_sanitize_unit_price_response(_confirmed()))
    billable = MetadataEndpointResult(
        value=BLK_BILLABLE,
        completed_at=datetime.now(UTC).isoformat(),
        response_hash=endpoint_response_hash("billable-size", BLK_BILLABLE),
    )
    samples = [
        ProviderCostSample(
            dataset=DATASET,
            schema=CBBO,
            feed_mode=ACQUISITION_FEED_MODE,
            account_pricing_context=ACCOUNT,
            billable_size_bytes=REF_BILLABLE,
            provider_cost_usd=Decimal(REF_COST),
        )
    ]
    result = derive_cost_endpoint_result(
        request=_opra_request(),
        billable_size_result=billable,
        snapshot=snapshot,
        samples=samples,
        account_pricing_context=ACCOUNT,
        failure_http_status=504,
        failure_category=None,
        now_utc=datetime.now(UTC).isoformat(),
    )
    raw = Decimal(BLK_BILLABLE) * Decimal("2.0") / Decimal(2**30)
    assert result.cost_source == "derived_response"
    assert Decimal(str(result.unit_price_usd_per_gib)) == Decimal("2.0")
    assert Decimal(str(result.raw_cost_usd)) == raw
    assert Decimal(str(result.conservative_cost_usd)) == raw * Decimal("1.25")
