"""Candidate OPRA acquisition strategies and deterministic ranking.

Strategy D (contract-targeted) represents the future state after OPRA
definitions are acquired and eligible contracts are selected locally; its cost
is never fabricated here and it is always reported as pending the definition
catalog.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from neuralmarket.data.acquisition.calendar import (
    daily_schedule,
    twice_weekly_schedule,
    weekly_schedule,
)
from neuralmarket.data.acquisition.contracts import StrategyProjection

STRATEGY_A = "A"
STRATEGY_B = "B"
STRATEGY_C = "C"
STRATEGY_D = "D"

DEVELOPMENT_SAFETY_FACTOR = Decimal("1.25")
TEST_RESERVE_SAFETY_FACTOR = Decimal("1.50")
MAX_SYMBOLS_PER_REQUEST = 2000
COST_STATUS_PROJECTED = "provider_estimate_projection"
COST_STATUS_PENDING_CATALOG = "requires_definition_catalog"


@dataclass(frozen=True)
class StrategyDefinition:
    """A candidate strategy and its deterministic session-schedule builder."""

    strategy_id: str
    name: str
    schedule_builder: Callable[[list[date]], list[date]] | None


STRATEGY_DEFINITIONS: tuple[StrategyDefinition, ...] = (
    StrategyDefinition(STRATEGY_A, "Daily close windows", daily_schedule),
    StrategyDefinition(STRATEGY_B, "Twice-weekly close windows (Tue/Thu)", twice_weekly_schedule),
    StrategyDefinition(STRATEGY_C, "Weekly close windows (Wed)", weekly_schedule),
    StrategyDefinition(STRATEGY_D, "Contract-targeted close windows", None),
)


def project_strategy_cost(
    scheduled_session_count: int,
    p95_cost_usd: Decimal,
    safety_factor: Decimal = DEVELOPMENT_SAFETY_FACTOR,
) -> Decimal:
    """Project a strategy's development-quote cost from the sampled p95 cost."""
    return Decimal(scheduled_session_count) * p95_cost_usd * safety_factor


def project_worst_case_cost(scheduled_session_count: int, maximum_cost_usd: Decimal) -> Decimal:
    """Project a strategy's worst-case development-quote cost from the sampled maximum."""
    return Decimal(scheduled_session_count) * maximum_cost_usd


def project_test_reserve_cost(scheduled_session_count: int, p95_cost_usd: Decimal) -> Decimal:
    """Project the final-test quote reserve from development-period sampling only."""
    return Decimal(scheduled_session_count) * p95_cost_usd * TEST_RESERVE_SAFETY_FACTOR


def rank_strategies(projections: list[StrategyProjection]) -> list[StrategyProjection]:
    """Rank candidate strategies by the fixed, deterministic ranking rule.

    Feasible strategies (satisfying every budget constraint, with a known
    projected cost) are ranked by highest inception-session frequency, then by
    lowest projected cost. Infeasible or cost-pending strategies (Strategy D)
    receive no rank.
    """
    feasible = [
        p
        for p in projections
        if p.projected_quote_cost_usd is not None
        and p.satisfies_project_cap
        and p.satisfies_unspent_reserve
        and p.satisfies_test_reserve
        and p.satisfies_development_cap
        and p.satisfies_pilot_cap
    ]
    ordered = sorted(
        feasible,
        key=lambda p: (-p.scheduled_session_count, Decimal(p.projected_quote_cost_usd or "0")),
    )
    ranked_ids = {p.strategy_id: index + 1 for index, p in enumerate(ordered)}
    return [p.model_copy(update={"rank": ranked_ids.get(p.strategy_id)}) for p in projections]
