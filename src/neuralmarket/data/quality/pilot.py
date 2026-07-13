"""Pilot data-quality report framework.

Evaluates synthetic and real pilot data against quality criteria,
producing structured reports consumed by Task 10 CLI and real pilot milestone.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, time, timedelta
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo

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
    """Quality report for OPRA quotes and final usable close coverage."""

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
    max_quote_age_seconds: float | None
    rejection_reasons: dict[str, int]


class PilotQualityReport(BaseModel):
    """Comprehensive quality report for pilot data."""

    model_config = ConfigDict(frozen=True)

    arcx_daily: ArcxDailyQualityReport
    arcx_statistics: ArcxStatisticsQualityReport
    opra_definitions: OpraDefinitionsQualityReport
    opra_quotes: OpraQuotesQualityReport
    generated_at: str


def _finite_number(value: Any) -> float | None:
    """Return a finite numeric value, or ``None`` for malformed/nonfinite input."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _aware_timestamp(row: dict[str, Any]) -> datetime | None:
    value = row.get("ts_event") or row.get("timestamp")
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _target_close_timestamp(row: dict[str, Any]) -> datetime | None:
    try:
        day = datetime.fromisoformat(str(row.get("session_date"))).date()
    except (TypeError, ValueError):
        return None
    local = datetime.combine(day, time(15, 59), tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(UTC)


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
        open_price = _finite_number(row.get("open"))
        high_price = _finite_number(row.get("high"))
        low_price = _finite_number(row.get("low"))
        close_price = _finite_number(row.get("close"))

        prices = (open_price, high_price, low_price, close_price)
        if any(price is None or price <= 0 for price in prices):
            nonpositive_price_count += 1

        # Every OHLC value must lie within [low, high].
        if any(price is None for price in prices) or (
            low_price is not None
            and high_price is not None
            and open_price is not None
            and close_price is not None
            and (
                low_price > min(open_price, close_price)
                or high_price < max(open_price, close_price)
            )
        ):
            invalid_ohlc_count += 1

        # Check for nonpositive volume
        volume = _finite_number(row.get("volume"))
        if volume is None or volume <= 0:
            nonpositive_volume_count += 1

        if row.get("timezone") not in {"UTC", "Etc/UTC", "America/New_York"}:
            timezone_problem_count += 1

    publishers = [row.get("publisher_id") for row in rows if row.get("publisher_id") is not None]
    if publishers:
        expected_publisher = publishers[0]
        publisher_mismatch_count = sum(
            row.get("publisher_id") != expected_publisher for row in rows
        )

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


def evaluate_arcx_statistics(rows: list[dict[str, Any]]) -> ArcxStatisticsQualityReport:
    """Evaluate official close/volume coverage and duplicate ARCX statistics."""
    observed = sorted({str(row.get("stat_type")) for row in rows if row.get("stat_type")})
    identities = [
        (row.get("session_date"), row.get("stat_type"), row.get("publisher_id")) for row in rows
    ]
    normalized = {value.lower().replace("_", " ") for value in observed}
    return ArcxStatisticsQualityReport(
        statistics_types_observed=observed,
        official_close_available=any("close" in value for value in normalized),
        official_volume_available=any("volume" in value for value in normalized),
        duplicate_statistics_count=len(identities) - len(set(identities)),
        unexpected_timestamp_count=sum(
            not bool(row.get("is_official", True)) or row.get("session_date") is None
            for row in rows
        ),
    )


def evaluate_opra_definitions(rows: list[dict[str, Any]]) -> OpraDefinitionsQualityReport:
    """Evaluate OPRA option-definition coverage and point-in-time uniqueness."""
    symbols = [str(row.get("option_symbol") or row.get("symbol") or "") for row in rows]
    nonempty_symbols = [symbol for symbol in symbols if symbol]
    expirations = [str(row["expiration"]) for row in rows if row.get("expiration") is not None]
    strikes = [
        (number, str(row["strike"]))
        for row in rows
        if (number := _finite_number(row.get("strike"))) is not None
    ]

    def distribution(field: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for row in rows:
            value = str(row.get(field) or "unknown")
            result[value] = result.get(value, 0) + 1
        return result

    by_symbol: dict[str, set[tuple[tuple[str, str], ...]]] = {}
    for symbol, row in zip(symbols, rows, strict=True):
        if symbol:
            signature = tuple(sorted((str(key), str(value)) for key, value in row.items()))
            by_symbol.setdefault(symbol, set()).add(signature)

    return OpraDefinitionsQualityReport(
        definition_count=len(rows),
        unique_option_symbols=len(set(nonempty_symbols)),
        call_count=sum(str(row.get("option_type", "")).upper() in {"C", "CALL"} for row in rows),
        put_count=sum(str(row.get("option_type", "")).upper() in {"P", "PUT"} for row in rows),
        expiration_min=min(expirations, default=None),
        expiration_max=max(expirations, default=None),
        strike_min=min(strikes)[1] if strikes else None,
        strike_max=max(strikes)[1] if strikes else None,
        multiplier_distribution=distribution("multiplier"),
        exercise_style_distribution=distribution("exercise_style"),
        settlement_style_distribution=distribution("settlement_style"),
        adjusted_or_special_count=sum(bool(row.get("is_adjusted_or_special")) for row in rows),
        duplicate_definition_count=len(nonempty_symbols) - len(set(nonempty_symbols)),
        point_in_time_change_count=sum(
            max(0, len(versions) - 1) for versions in by_symbol.values()
        ),
    )


def evaluate_opra_quotes(
    rows: list[dict[str, Any]], target_window_sessions: list[str]
) -> OpraQuotesQualityReport:
    """Evaluate quality of OPRA quote data.

    Flags:
    - Zero bid: bid_price == 0 counted as zero_bid_count
    - Negative price: bid_price < 0 counted as negative_price_count
      (mutually exclusive with zero_bid_count)
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
    quote_ages: list[float] = []
    grouped_rows: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    target_sessions = set(target_window_sessions)

    for row_index, row in enumerate(rows):
        session_date = row.get("session_date")
        contract = row.get("contract")
        bid_price = _finite_number(row.get("bid_price"))
        ask_price = _finite_number(row.get("ask_price"))
        bid_size = _finite_number(row.get("bid_size"))
        ask_size = _finite_number(row.get("ask_size"))
        quote_age = _finite_number(row.get("quote_age_seconds"))
        if quote_age is not None and quote_age >= 0:
            quote_ages.append(quote_age)

        if contract:
            unique_contracts_set.add(contract)
            if session_date in target_sessions:
                grouped_rows.setdefault(str(contract), []).append((row_index, row))

        if session_date:
            sessions_set.add(session_date)
            if session_date not in target_sessions:
                quotes_outside_window_count += 1

        # Check for missing side
        if bid_price is None or ask_price is None:
            missing_side_count += 1
            if bid_size is None or ask_size is None or bid_size <= 0 or ask_size <= 0:
                nonpositive_size_count += 1
            continue

        # Check for zero bid (bid_price == 0, exclusive of negative -- see
        # negative_price_count below) so the two counters are mutually
        # exclusive and sum to "nonpositive bid count" without double-counting.
        if bid_price == 0:
            zero_bid_count += 1

        # Check for negative price (bid_price < 0)
        if bid_price < 0 or ask_price < 0:
            negative_price_count += 1

        # Check for crossed quotes (bid > ask)
        if bid_price > ask_price:
            crossed_quote_count += 1

        # Check for locked quotes (bid == ask)
        if bid_price == ask_price:
            locked_quote_count += 1

        # Check for nonpositive sizes
        if bid_size is None or ask_size is None or bid_size <= 0 or ask_size <= 0:
            nonpositive_size_count += 1

    for contract, contract_rows in grouped_rows.items():
        timestamped = [(_aware_timestamp(row), row) for _, row in contract_rows]
        if any(timestamp is None for timestamp, _ in timestamped):
            contracts_with_no_usable_close_quote.add(contract)
            continue
        close_candidates = []
        for timestamp, row in timestamped:
            if timestamp is None:
                continue
            target_close = _target_close_timestamp(row)
            if target_close is None:
                continue
            earliest_close = target_close - timedelta(minutes=5)
            if earliest_close <= timestamp <= target_close:
                close_candidates.append((timestamp, row))
        if not close_candidates:
            contracts_with_no_usable_close_quote.add(contract)
            continue
        _, row = max(close_candidates, key=lambda item: item[0])
        bid = _finite_number(row.get("bid_price"))
        ask = _finite_number(row.get("ask_price"))
        bid_size = _finite_number(row.get("bid_size"))
        ask_size = _finite_number(row.get("ask_size"))
        has_valid_quote = (
            bid is not None
            and ask is not None
            and bid >= 0
            and ask >= bid
            and bid_size is not None
            and ask_size is not None
            and bid_size > 0
            and ask_size > 0
        )
        if has_valid_quote:
            contracts_with_final_valid_quote.add(contract)
        else:
            contracts_with_no_usable_close_quote.add(contract)

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
        max_quote_age_seconds=max(quote_ages, default=None),
        rejection_reasons={
            "missing_side": missing_side_count,
            "nonpositive_size": nonpositive_size_count,
            "negative_price": negative_price_count,
            "crossed": crossed_quote_count,
            "outside_window": quotes_outside_window_count,
            "no_usable_close_quote": len(contracts_with_no_usable_close_quote),
        },
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
