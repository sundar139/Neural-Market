"""Tests for pilot cost preflight (Task 6).

Note: ``MetadataEstimator.estimate()`` does not accept a ``request_id``
keyword argument (see ``estimation.py``), so the fake estimator here tracks
which estimate belongs to which request by call order, not by a nonexistent
kwarg. ``run_preflight`` must call ``estimator.estimate(...)`` once per
request, in request order, and zip results back onto ``request_id`` itself.
"""

from datetime import UTC, datetime
from decimal import Decimal

from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.preflight import PilotPreflightConfig, run_preflight
from neuralmarket.data.acquisition.requests import AcquisitionRequest


class FakeEstimator:
    """Records call order; returns a pre-seeded cost per request_id, matched by order."""

    def __init__(self, cost_by_id: dict[str, Decimal], request_order: list[str]) -> None:
        """Seed per-request costs and the call order used to match calls to request ids."""
        self._cost_by_id = cost_by_id
        self._request_order = request_order
        self._call_index = 0
        self.metadata_call_count = 0
        self.retry_count = 0

    def estimate(self, **kwargs: object) -> MetadataEstimate:
        request_id = self._request_order[self._call_index]
        self._call_index += 1
        self.metadata_call_count += 1
        return MetadataEstimate(
            dataset=kwargs["dataset"],
            schema=kwargs["schema"],
            symbol=kwargs["symbol"],
            stype_in=kwargs["stype_in"],
            window_start=kwargs["start"],
            window_end=kwargs["end"],
            record_count=10,
            billable_size_bytes=1000,
            cost_usd=self._cost_by_id[request_id],
            retries=0,
        )


def _request(request_id: str, estimated_cost: str) -> AcquisitionRequest:
    now = datetime(2019, 1, 2, tzinfo=UTC)
    return AcquisitionRequest(
        request_id=request_id,
        wave="arcx_catalog",
        dataset="ARCX.PILLAR",
        schema="definition",
        symbols=("SPY",),
        stype_in="raw_symbol",
        stype_out="instrument_id",
        start=now,
        end_exclusive=now,
        encoding="dbn",
        compression="zstd",
        expected_split="training",
        session_date=None,
        calendar="XNYS",
        estimated_record_count=10,
        estimated_billable_size=1000,
        estimated_cost=estimated_cost,
        currency="USD",
        request_hash="f" * 64,
    )


def test_preflight_passes_within_caps() -> None:
    reqs = [_request("r1", "0.10")]
    config = PilotPreflightConfig(
        maximum_spend_usd=Decimal("5.00"),
        maximum_single_request_usd=Decimal("1.00"),
        estimate_increase_tolerance_fraction=Decimal("0.20"),
    )
    result = run_preflight(
        estimator=FakeEstimator({"r1": Decimal("0.11")}, ["r1"]), requests=reqs, config=config
    )
    assert result.passed is True
    assert result.metadata_call_count == 1


def test_preflight_rejects_single_request_over_cap() -> None:
    reqs = [_request("r1", "0.10")]
    config = PilotPreflightConfig(
        maximum_spend_usd=Decimal("5.00"),
        maximum_single_request_usd=Decimal("1.00"),
        estimate_increase_tolerance_fraction=Decimal("0.20"),
    )
    result = run_preflight(
        estimator=FakeEstimator({"r1": Decimal("1.50")}, ["r1"]), requests=reqs, config=config
    )
    assert result.passed is False
    assert any(r.reason == "single_request_cap_exceeded" for r in result.rejections)


def test_preflight_rejects_total_over_cap() -> None:
    reqs = [_request("r1", "0.10"), _request("r2", "0.10")]
    config = PilotPreflightConfig(
        maximum_spend_usd=Decimal("5.00"),
        maximum_single_request_usd=Decimal("3.00"),
        estimate_increase_tolerance_fraction=Decimal("0.20"),
    )
    result = run_preflight(
        estimator=FakeEstimator(
            {"r1": Decimal("3.00"), "r2": Decimal("2.50")}, ["r1", "r2"]
        ),
        requests=reqs,
        config=config,
    )
    assert result.passed is False
    assert any(r.reason == "total_cap_exceeded" for r in result.rejections)


def test_preflight_rejects_unexplained_estimate_increase() -> None:
    reqs = [_request("r1", "0.10")]
    config = PilotPreflightConfig(
        maximum_spend_usd=Decimal("5.00"),
        maximum_single_request_usd=Decimal("1.00"),
        estimate_increase_tolerance_fraction=Decimal("0.20"),
    )
    result = run_preflight(
        estimator=FakeEstimator({"r1": Decimal("0.50")}, ["r1"]), requests=reqs, config=config
    )
    assert result.passed is False
    assert any(r.reason == "unexplained_increase" for r in result.rejections)


def test_preflight_uses_decimal_not_float_for_total() -> None:
    reqs = [_request("r1", "0.10"), _request("r2", "0.20"), _request("r3", "0.15")]
    config = PilotPreflightConfig(
        maximum_spend_usd=Decimal("5.00"),
        maximum_single_request_usd=Decimal("1.00"),
        estimate_increase_tolerance_fraction=Decimal("0.20"),
    )
    result = run_preflight(
        estimator=FakeEstimator(
            {"r1": Decimal("0.10"), "r2": Decimal("0.20"), "r3": Decimal("0.15")},
            ["r1", "r2", "r3"],
        ),
        requests=reqs,
        config=config,
    )
    assert Decimal(result.fresh_total_usd) == Decimal("0.45")


def test_preflight_does_not_hide_one_spike_in_another_underrun() -> None:
    """A per-request spike must be flagged even if the aggregate total is unchanged."""
    reqs = [_request("r1", "1.00"), _request("r2", "1.00")]
    config = PilotPreflightConfig(
        maximum_spend_usd=Decimal("5.00"),
        maximum_single_request_usd=Decimal("5.00"),
        estimate_increase_tolerance_fraction=Decimal("0.20"),
    )
    # r1 spikes far above tolerance, r2 drops -- planned total (2.00) == fresh total (2.00).
    result = run_preflight(
        estimator=FakeEstimator(
            {"r1": Decimal("1.90"), "r2": Decimal("0.10")}, ["r1", "r2"]
        ),
        requests=reqs,
        config=config,
    )
    assert result.passed is False
    assert any(
        r.reason == "unexplained_increase" and r.request_id == "r1" for r in result.rejections
    )


def test_preflight_config_from_pilot_execution_config() -> None:
    from neuralmarket.data.acquisition.requests import PilotExecutionConfig

    raw = {
        "pilot_month": "2019-01",
        "calendar_name": "XNYS",
        "quote_window_minutes": 10,
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "estimate_increase_tolerance_fraction": "0.20",
        "require_exact_plan_hash": True,
        "require_authorization_file": True,
        "purchase_authorized": False,
        "underlying": {
            "dataset": "ARCX.PILLAR",
            "symbol": "SPY",
            "stype_in": "raw_symbol",
            "schemas": ["definition"],
        },
        "options": {
            "dataset": "OPRA.PILLAR",
            "symbol": "SPY",
            "stype_in": "parent",
            "definition_schema": "definition",
            "quote_schema": "cbbo-1m",
        },
        "retry": {
            "maximum_attempts": 3,
            "initial_delay_seconds": 1,
            "multiplier": 2,
            "maximum_delay_seconds": 10,
            "jitter": "none",
        },
    }
    full_config = PilotExecutionConfig.model_validate(raw)
    narrowed = PilotPreflightConfig.from_pilot_execution_config(full_config)
    assert narrowed.maximum_spend_usd == Decimal("5.00")
    assert narrowed.maximum_single_request_usd == Decimal("1.00")
    assert narrowed.estimate_increase_tolerance_fraction == Decimal("0.20")

    # run_preflight must also accept the full PilotExecutionConfig directly.
    reqs = [_request("r1", "0.10")]
    result = run_preflight(
        estimator=FakeEstimator({"r1": Decimal("0.11")}, ["r1"]),
        requests=reqs,
        config=full_config,
    )
    assert result.passed is True
