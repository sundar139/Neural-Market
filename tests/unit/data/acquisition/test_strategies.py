from decimal import Decimal

import pytest

from neuralmarket.data.acquisition.contracts import StrategyProjection
from neuralmarket.data.acquisition.strategies import (
    STRATEGY_DEFINITIONS,
    project_strategy_cost,
    project_test_reserve_cost,
    project_worst_case_cost,
    rank_strategies,
)


def _projection(**overrides: object) -> StrategyProjection:
    fields: dict[str, object] = {
        "strategy_id": "A",
        "name": "A",
        "scheduled_session_count": 100,
        "cost_status": "provider_estimate_projection",
        "projected_quote_cost_usd": "10.00",
        "worst_case_quote_cost_usd": "12.00",
        "safety_factor": "1.25",
        "satisfies_project_cap": True,
        "satisfies_unspent_reserve": True,
        "satisfies_test_reserve": True,
        "satisfies_development_cap": True,
        "satisfies_pilot_cap": True,
        "rank": None,
    }
    fields.update(overrides)
    return StrategyProjection(**fields)


@pytest.mark.unit
def test_strategy_definitions_cover_a_through_d() -> None:
    ids = [d.strategy_id for d in STRATEGY_DEFINITIONS]
    assert ids == ["A", "B", "C", "D"]
    assert STRATEGY_DEFINITIONS[-1].schedule_builder is None


@pytest.mark.unit
def test_project_strategy_cost_arithmetic() -> None:
    cost = project_strategy_cost(100, Decimal("0.10"), Decimal("1.25"))
    assert cost == Decimal("12.5")


@pytest.mark.unit
def test_project_worst_case_cost_arithmetic() -> None:
    cost = project_worst_case_cost(100, Decimal("0.20"))
    assert cost == Decimal("20.0")


@pytest.mark.unit
def test_project_test_reserve_cost_arithmetic() -> None:
    cost = project_test_reserve_cost(500, Decimal("0.02"))
    assert cost == Decimal("15.0")


@pytest.mark.unit
def test_rank_strategies_orders_by_frequency_then_cost() -> None:
    high_freq_expensive = _projection(
        strategy_id="A", scheduled_session_count=200, projected_quote_cost_usd="20.00"
    )
    low_freq_cheap = _projection(
        strategy_id="C", scheduled_session_count=50, projected_quote_cost_usd="5.00"
    )
    mid_freq = _projection(
        strategy_id="B", scheduled_session_count=100, projected_quote_cost_usd="10.00"
    )
    ranked = rank_strategies([low_freq_cheap, high_freq_expensive, mid_freq])
    by_id = {p.strategy_id: p for p in ranked}
    assert by_id["A"].rank == 1  # highest frequency wins regardless of cost
    assert by_id["B"].rank == 2
    assert by_id["C"].rank == 3


@pytest.mark.unit
def test_rank_strategies_tie_break_by_cost() -> None:
    cheaper = _projection(
        strategy_id="A", scheduled_session_count=100, projected_quote_cost_usd="5.00"
    )
    pricier = _projection(
        strategy_id="B", scheduled_session_count=100, projected_quote_cost_usd="10.00"
    )
    ranked = rank_strategies([pricier, cheaper])
    by_id = {p.strategy_id: p for p in ranked}
    assert by_id["A"].rank == 1
    assert by_id["B"].rank == 2


@pytest.mark.unit
def test_rank_strategies_excludes_infeasible() -> None:
    feasible = _projection(strategy_id="A")
    infeasible = _projection(strategy_id="B", satisfies_project_cap=False)
    ranked = rank_strategies([feasible, infeasible])
    by_id = {p.strategy_id: p for p in ranked}
    assert by_id["A"].rank == 1
    assert by_id["B"].rank is None


@pytest.mark.unit
def test_rank_strategies_excludes_pending_cost() -> None:
    feasible = _projection(strategy_id="A")
    pending = _projection(
        strategy_id="D",
        scheduled_session_count=0,
        cost_status="requires_definition_catalog",
        projected_quote_cost_usd=None,
        worst_case_quote_cost_usd=None,
        safety_factor=None,
        satisfies_project_cap=False,
        satisfies_unspent_reserve=False,
        satisfies_test_reserve=False,
        satisfies_development_cap=False,
        satisfies_pilot_cap=False,
    )
    ranked = rank_strategies([feasible, pending])
    by_id = {p.strategy_id: p for p in ranked}
    assert by_id["A"].rank == 1
    assert by_id["D"].rank is None


@pytest.mark.unit
def test_rank_strategies_all_infeasible_yields_no_ranks() -> None:
    a = _projection(strategy_id="A", satisfies_test_reserve=False)
    b = _projection(strategy_id="B", satisfies_pilot_cap=False)
    ranked = rank_strategies([a, b])
    assert all(p.rank is None for p in ranked)
