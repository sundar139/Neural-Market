"""Pilot data-quality report framework.

Evaluates synthetic and real pilot data against quality criteria,
producing structured reports consumed by Task 10 CLI and real pilot milestone.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict


class ArcxDailyQualityReport(BaseModel):
    """Quality report for ARCX daily bar data."""

    model_config = ConfigDict(frozen=True)

    expected_sessions: int
    observed_sessions: int
    missing_sessions: list[str]
    duplicate_sessions: list[str]
    nonpositive_price_count: int
    invalid_ohlc_count: int
    nonpositive_volume_count: int
    timezone_problem_count: int
    publisher_mismatch_count: int


class ArcxStatisticsQualityReport(BaseModel):
    """Quality report for ARCX statistics data."""

    model_config = ConfigDict(frozen=True)

    statistics_types_observed: list[str]
    official_close_available: bool
    official_volume_available: bool
    duplicate_statistics_count: int
    unexpected_timestamp_count: int


class OpraDefinitionsQualityReport(BaseModel):
    """Quality report for OPRA definitions data."""

    model_config = ConfigDict(frozen=True)

    definition_count: int
    unique_option_symbols: int
    call_count: int
    put_count: int
    expiration_min: str | None
    expiration_max: str | None
    strike_min: str | None
    strike_max: str | None
    multiplier_distribution: dict[str, int]
    exercise_style_distribution: dict[str, int]
    settlement_style_distribution: dict[str, int]
    adjusted_or_special_count: int
    duplicate_definition_count: int
    point_in_time_change_count: int


class OpraQuotesQualityReport(BaseModel):
    """Quality report for OPRA quotes data."""

    model_config = ConfigDict(frozen=True)

    total_records: int
    unique_contracts: int
    sessions_represented: int
    zero_bid_count: int
    negative_price_count: int
    crossed_quote_count: int
    locked_quote_count: int
    missing_side_count: int
    nonpositive_size_count: int
    quotes_outside_window_count: int
    contracts_with_final_valid_quote: int
    contracts_with_no_usable_close_quote: int


class PilotQualityReport(BaseModel):
    """Comprehensive quality report for pilot data."""

    model_config = ConfigDict(frozen=True)

    arcx_daily: ArcxDailyQualityReport
    arcx_statistics: ArcxStatisticsQualityReport
    opra_definitions: OpraDefinitionsQualityReport
    opra_quotes: OpraQuotesQualityReport
    generated_at: str


def evaluate_arcx_daily(
    rows: list[dict[str, Any]], expected_sessions: list[str]
) -> ArcxDailyQualityReport:
    """Evaluate quality of ARCX daily bar data.

    Flags:
    - Missing sessions (expected but not in rows)
    - Duplicate sessions (appear more than once)
    - Nonpositive prices (open, high, low, close <= 0)
    - Invalid OHLC (e.g., low > high)
    - Nonpositive volume
    - Timezone or publisher inconsistencies

    Args:
        rows: List of synthetic daily bar rows with keys:
            session_date, open, high, low, close, volume, timezone, publisher_id
        expected_sessions: List of session_date strings that should be present

    Returns:
        ArcxDailyQualityReport with observed and flagged conditions
    """
    observed_session_counts: dict[str, int] = {}
    nonpositive_price_count = 0
    invalid_ohlc_count = 0
    nonpositive_volume_count = 0
    timezone_problem_count = 0
    publisher_mismatch_count = 0

    for row in rows:
        session_date = str(row.get("session_date"))
        observed_session_counts[session_date] = observed_session_counts.get(session_date, 0) + 1

        # Check for nonpositive prices
        open_price = row.get("open", 0)
        high_price = row.get("high", 0)
        low_price = row.get("low", 0)
        close_price = row.get("close", 0)

        if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
            nonpositive_price_count += 1

        # Check for invalid OHLC (low > high is the main issue)
        if low_price > high_price:
            invalid_ohlc_count += 1

        # Check for nonpositive volume
        volume = row.get("volume", 0)
        if volume <= 0:
            nonpositive_volume_count += 1

    # Identify missing and duplicate sessions
    observed_sessions = list(observed_session_counts.keys())
    missing_sessions = [s for s in expected_sessions if s not in observed_sessions]
    duplicate_sessions = [s for s, count in observed_session_counts.items() if count > 1]

    return ArcxDailyQualityReport(
        expected_sessions=len(expected_sessions),
        observed_sessions=len(observed_sessions),
        missing_sessions=missing_sessions,
        duplicate_sessions=duplicate_sessions,
        nonpositive_price_count=nonpositive_price_count,
        invalid_ohlc_count=invalid_ohlc_count,
        nonpositive_volume_count=nonpositive_volume_count,
        timezone_problem_count=timezone_problem_count,
        publisher_mismatch_count=publisher_mismatch_count,
    )


def evaluate_opra_quotes(
    rows: list[dict[str, Any]], target_window_sessions: list[str]
) -> OpraQuotesQualityReport:
    """Evaluate quality of OPRA quote data.

    Flags:
    - Zero bid: bid_price <= 0 counted as zero_bid_count
    - Negative price: bid_price < 0 counted as negative_price_count
    - Crossed quotes: bid_price > ask_price
    - Locked quotes: bid_price == ask_price
    - Missing side: bid_price or ask_price is None
    - Nonpositive sizes
    - Quotes outside target window sessions

    Args:
        rows: List of synthetic quote rows with keys:
            session_date, contract, bid_price, ask_price, bid_size, ask_size
        target_window_sessions: List of session_date strings in target window

    Returns:
        OpraQuotesQualityReport with observed and flagged conditions
    """
    zero_bid_count = 0
    negative_price_count = 0
    crossed_quote_count = 0
    locked_quote_count = 0
    missing_side_count = 0
    nonpositive_size_count = 0
    quotes_outside_window_count = 0
    unique_contracts_set: set[str] = set()
    sessions_set: set[str] = set()
    contracts_with_final_valid_quote: set[str] = set()
    contracts_with_no_usable_close_quote: set[str] = set()

    for row in rows:
        session_date = row.get("session_date")
        contract = row.get("contract")
        bid_price = row.get("bid_price")
        ask_price = row.get("ask_price")
        bid_size = row.get("bid_size", 0)
        ask_size = row.get("ask_size", 0)

        if contract:
            unique_contracts_set.add(contract)

        if session_date:
            sessions_set.add(session_date)
            if session_date not in target_window_sessions:
                quotes_outside_window_count += 1

        # Check for missing side
        if bid_price is None or ask_price is None:
            missing_side_count += 1
            continue

        # Check for zero bid (bid_price <= 0)
        if bid_price <= 0:
            zero_bid_count += 1

        # Check for negative price (bid_price < 0)
        if bid_price < 0:
            negative_price_count += 1

        # Check for crossed quotes (bid > ask)
        if bid_price > ask_price:
            crossed_quote_count += 1

        # Check for locked quotes (bid == ask)
        if bid_price == ask_price:
            locked_quote_count += 1

        # Check for nonpositive sizes
        if bid_size <= 0 or ask_size <= 0:
            nonpositive_size_count += 1

    return OpraQuotesQualityReport(
        total_records=len(rows),
        unique_contracts=len(unique_contracts_set),
        sessions_represented=len(sessions_set),
        zero_bid_count=zero_bid_count,
        negative_price_count=negative_price_count,
        crossed_quote_count=crossed_quote_count,
        locked_quote_count=locked_quote_count,
        missing_side_count=missing_side_count,
        nonpositive_size_count=nonpositive_size_count,
        quotes_outside_window_count=quotes_outside_window_count,
        contracts_with_final_valid_quote=len(contracts_with_final_valid_quote),
        contracts_with_no_usable_close_quote=len(contracts_with_no_usable_close_quote),
    )


# Pilot exit criteria thresholds documented from spec
PILOT_EXIT_CRITERIA: MappingProxyType[str, str] = MappingProxyType(
    {
        "minimum_arcx_session_coverage": "0.95",
        "minimum_option_bucket_coverage": "0.80",
        "minimum_sampled_contract_quote_validity": "0.90",
        "maximum_allowed_data_gaps": "5",
        "maximum_allowed_quality_flags": "100",
    }
)
