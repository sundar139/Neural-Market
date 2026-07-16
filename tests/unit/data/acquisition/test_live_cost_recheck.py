"""Offline fail-closed tests for the fresh provider cost-recheck gate.

No test constructs a real Databento client or touches the network; an autouse
guard fails if ``databento`` is newly imported. The canonical 25-request plan is
built deterministically from the tracked pilot config.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.live_cost_recheck import (
    CostRecheckError,
    RequestQuote,
    recheck_costs,
)
from neuralmarket.data.acquisition.metadata_runner import (
    IsolatedMetadataResult,
    MetadataOperationEvent,
)
from neuralmarket.data.acquisition.requests import build_pilot_request_plan, load_pilot_config

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_CONFIG = _ROOT / "configs/data/acquisition/pilot_january_2019.yaml"
NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC)
PRIOR_RAW = Decimal("0.460514456032759765625")
PRIOR_CONS = Decimal("0.46298506855869970703125")
TRACKED = Decimal("0.460514456033")

_SUPPORTED = {
    "ARCX.PILLAR": ["definition", "ohlcv-1d", "statistics", "trades", "mbp-1"],
    "OPRA.PILLAR": ["definition", "cbbo-1m", "cbbo-1s", "trades", "tcbbo"],
}


@pytest.fixture(autouse=True)
def _no_real_databento() -> Any:
    before = "databento" in sys.modules
    yield
    assert not ("databento" in sys.modules and not before), "must not import databento"


def _plan() -> list[Any]:
    return build_pilot_request_plan(load_pilot_config(_CONFIG))


def _ok(cost: str = "0.01") -> IsolatedMetadataResult:
    return IsolatedMetadataResult(
        endpoint_values={"cost": float(cost)},
        events=[],
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _fail(http_status: int = 504, cls: str = "BentoServerError") -> IsolatedMetadataResult:
    event = MetadataOperationEvent(
        run_id="r",
        request_index=1,
        request_count=25,
        request_id="x",
        dataset="OPRA.PILLAR",
        schema_name="cbbo-1m",
        session_date=None,
        endpoint="cost",
        attempt=1,
        started_at=NOW.isoformat(),
        completed_at=NOW.isoformat(),
        elapsed_seconds=0.1,
        outcome="failed",
        exception_class=cls,
        http_status=http_status,
        child_pid=1,
    )
    return IsolatedMetadataResult(
        endpoint_values={},
        events=[event],
        failure_type=cls,
        failed_endpoint="cost",
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _lister(supported: dict[str, list[str]] | None = None):
    table = supported if supported is not None else _SUPPORTED
    calls: list[str] = []

    def lister(dataset: str) -> list[str]:
        calls.append(dataset)
        return list(table.get(dataset, []))

    lister.calls = calls  # type: ignore[attr-defined]
    return lister


def _run(
    *,
    quoter,
    lister=None,
    requests=None,
    max_attempts: int = 2,
) -> Any:
    return recheck_costs(
        requests=requests if requests is not None else _plan(),
        repository_head="0" * 40,
        checkpoint_sha256="e" * 64,
        plan_hash="5ee6126ca9e27e3d1909c58b4e555526d5894dcd9ea129faf8d6159973aff1fe",
        request_manifest_sha256="8" * 64,
        sdk_version="0.81.0",
        now=NOW,
        schema_lister=lister if lister is not None else _lister(),
        quoter=quoter,
        timeout_seconds=30.0,
        prior_raw_total_usd=PRIOR_RAW,
        prior_conservative_total_usd=PRIOR_CONS,
        tracked_total_usd=TRACKED,
        max_attempts=max_attempts,
    )


def test_exact_frozen_reconstruction_and_no_cross_product() -> None:
    seen: list[tuple[str, str, tuple[str, ...], str, str, str]] = []

    def quoter(request, attempt, timeout):
        seen.append(
            (
                request.dataset,
                request.schema_name,
                request.symbols,
                request.stype_in,
                request.start.isoformat(),
                request.end_exclusive.isoformat(),
            )
        )
        return _ok()

    result = _run(quoter=quoter)
    # Exactly 25 frozen requests, no dataset x schema cross product.
    assert len(seen) == 25
    combos = {(d, s) for d, s, *_ in seen}
    assert combos == {
        ("ARCX.PILLAR", "definition"),
        ("ARCX.PILLAR", "ohlcv-1d"),
        ("ARCX.PILLAR", "statistics"),
        ("OPRA.PILLAR", "definition"),
        ("OPRA.PILLAR", "cbbo-1m"),
    }
    assert result.status == "complete"
    assert result.provider_quote_count == 25


def test_one_list_schemas_call_per_dataset() -> None:
    lister = _lister()
    _run(quoter=lambda r, a, t: _ok(), lister=lister)
    assert sorted(lister.calls) == ["ARCX.PILLAR", "OPRA.PILLAR"]
    assert len(lister.calls) == 2


def test_unsupported_schema_rejected_before_quote() -> None:
    quoted: list[Any] = []

    def quoter(request, attempt, timeout):
        quoted.append(request)
        return _ok()

    bad = _lister({"ARCX.PILLAR": ["definition"], "OPRA.PILLAR": ["cbbo-1m", "definition"]})
    with pytest.raises(CostRecheckError, match="does not support"):
        _run(quoter=quoter, lister=bad)
    assert quoted == []  # failed before any get_cost


def test_spy_opt_uses_parent_and_spy_uses_frozen_stype() -> None:
    stypes: dict[str, set[str]] = {}

    def quoter(request, attempt, timeout):
        stypes.setdefault(request.symbols[0], set()).add(request.stype_in)
        return _ok()

    _run(quoter=quoter)
    assert stypes["SPY.OPT"] == {"parent"}
    assert stypes["SPY"] == {"raw_symbol"}


def test_exact_symbols_and_window_preserved() -> None:
    windows: list[tuple[str, str, str]] = []

    def quoter(request, attempt, timeout):
        assert len(request.symbols) == 1
        windows.append(
            (request.symbols[0], request.start.isoformat(), request.end_exclusive.isoformat())
        )
        return _ok()

    _run(quoter=quoter)
    # cbbo-1m quote windows are 600s; none is a whole-month substitute.
    plan = _plan()
    for req in plan:
        if req.schema_name == "cbbo-1m":
            assert (req.end_exclusive - req.start).total_seconds() == 600


def test_decimal_str_conversion_avoids_binary_float() -> None:
    # 0.1 as a float has no exact binary form; Decimal(str(0.1)) == Decimal("0.1").
    result = _run(quoter=lambda r, a, t: _ok("0.1"))
    assert all(q.cost_usd == "0.1" for q in result.quotes if q.status == "quoted")
    assert "0.1000000000000000055" not in result.fresh_raw_total_usd


def test_provider_only_quote_count() -> None:
    result = _run(quoter=lambda r, a, t: _ok())
    assert result.provider_quote_count == 25
    assert result.unavailable_quote_count == 0
    assert result.provider_call_inventory["get_cost"] >= 25


def test_one_failed_quote_makes_incomplete_no_fallback() -> None:
    plan = _plan()
    target = plan[-1].request_id

    def quoter(request, attempt, timeout):
        return _fail() if request.request_id == target else _ok()

    result = _run(quoter=quoter)
    assert result.status == "incomplete"
    assert result.authorization_ready is False
    assert result.unavailable_quote_count == 1
    bad = [q for q in result.quotes if q.status == "unavailable"]
    assert len(bad) == 1 and bad[0].cost_usd is None  # no derived substitution


def test_two_attempt_maximum() -> None:
    calls = {"n": 0}

    def quoter(request, attempt, timeout):
        calls["n"] += 1
        return _fail()

    result = _run(quoter=quoter, requests=_plan()[:0] or _plan())
    # 25 requests x 2 attempts each = 50 get_cost calls, then all unavailable.
    assert calls["n"] == 50
    assert result.unavailable_quote_count == 25
    per_request_attempts = [q.attempts for q in result.quotes]
    assert max(per_request_attempts) == 2


def test_success_on_second_attempt() -> None:
    state: dict[str, int] = {}

    def quoter(request, attempt, timeout):
        state[request.request_id] = state.get(request.request_id, 0) + 1
        return _ok() if state[request.request_id] >= 2 else _fail()

    result = _run(quoter=quoter)
    assert result.status == "complete"
    assert all(q.attempts == 2 for q in result.quotes)


def test_child_cleanup_recorded() -> None:
    result = _run(quoter=lambda r, a, t: _ok())
    assert all(q.remaining_children == 0 for q in result.quotes)
    assert all(a["remaining_children"] == 0 for a in result.attempt_history)


def test_cross_product_plan_rejected() -> None:
    # A broadened plan (e.g. duplicated / wrong shape) fails canonical validation.
    plan = _plan()
    with pytest.raises(ValueError):
        _run(quoter=lambda r, a, t: _ok(), requests=plan[:24])


def test_financial_gates_pass_small_costs() -> None:
    result = _run(quoter=lambda r, a, t: _ok("0.01"))
    assert result.within_total_cap
    assert result.within_per_request_cap
    assert result.within_drift_ceiling
    assert result.authorization_ready


def test_per_request_gate_fails_over_one_dollar() -> None:
    result = _run(quoter=lambda r, a, t: _ok("1.01"))
    assert result.within_per_request_cap is False
    assert result.authorization_ready is False


def test_total_and_drift_gate_fails_over_ceiling() -> None:
    # 25 x 0.20 = 5.00 raw: within $5 hard cap but far over the 0.69 drift ceiling.
    result = _run(quoter=lambda r, a, t: _ok("0.20"))
    assert result.within_drift_ceiling is False
    assert result.authorization_ready is False


def test_freshness_is_30_minutes() -> None:
    result = _run(quoter=lambda r, a, t: _ok())
    observed = datetime.fromisoformat(result.observed_at)
    expires = datetime.fromisoformat(result.expires_at)
    assert (expires - observed).total_seconds() == 1800


def test_deltas_reported() -> None:
    result = _run(quoter=lambda r, a, t: _ok("0.01"))
    assert result.prior_raw_total_usd == str(PRIOR_RAW)
    assert Decimal(result.fresh_raw_total_usd) == Decimal("0.25")
    assert Decimal(result.absolute_delta_usd) == Decimal("0.25") - PRIOR_RAW


def test_negative_cost_rejected() -> None:
    with pytest.raises(CostRecheckError, match="negative"):
        _run(quoter=lambda r, a, t: _ok("-0.01"))


def test_nonfinite_cost_rejected() -> None:
    def quoter(request, attempt, timeout):
        return IsolatedMetadataResult(
            endpoint_values={"cost": float("inf")},
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    with pytest.raises(CostRecheckError, match="finite"):
        _run(quoter=quoter)


def test_naive_now_rejected() -> None:
    with pytest.raises(CostRecheckError, match="timezone-aware"):
        recheck_costs(
            requests=_plan(),
            repository_head="0" * 40,
            checkpoint_sha256="e" * 64,
            plan_hash="p",
            request_manifest_sha256="8" * 64,
            sdk_version="0.81.0",
            now=datetime(2026, 7, 16, 12, 0, 0),  # naive
            schema_lister=_lister(),
            quoter=lambda r, a, t: _ok(),
            timeout_seconds=30.0,
            prior_raw_total_usd=PRIOR_RAW,
            prior_conservative_total_usd=PRIOR_CONS,
            tracked_total_usd=TRACKED,
        )


def test_provider_inventory_has_zero_forbidden_calls() -> None:
    inv = _run(quoter=lambda r, a, t: _ok()).provider_call_inventory
    assert inv["timeseries_get_range"] == 0
    assert inv["batch"] == 0
    assert inv["live"] == 0
    assert inv["symbology"] == 0
    assert inv["list_unit_prices"] == 0


def test_quote_dataclass_is_frozen() -> None:
    q = RequestQuote(
        request_id="a",
        dataset="OPRA.PILLAR",
        schema="cbbo-1m",
        symbols=("SPY.OPT",),
        stype_in="parent",
        start="s",
        end="e",
        status="quoted",
        cost_usd="0.01",
        attempts=1,
        last_failure_class=None,
        last_http_status=None,
        remaining_children=0,
    )
    with pytest.raises((AttributeError, TypeError, ValueError)):
        q.cost_usd = "9.99"  # type: ignore[misc]
