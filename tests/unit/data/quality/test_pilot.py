"""Tests for pilot data-quality report framework."""

import pytest

from neuralmarket.data.quality.pilot import (
    PILOT_EXIT_CRITERIA,
    evaluate_arcx_daily,
    evaluate_arcx_statistics,
    evaluate_opra_definitions,
    evaluate_opra_quotes,
)

pytestmark = pytest.mark.unit


def test_evaluate_arcx_daily_flags_missing_and_duplicate_sessions() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "open": 1,
            "high": 2,
            "low": 0.5,
            "close": 1.5,
            "volume": 100,
            "timezone": "UTC",
            "publisher_id": 1,
        },
        {
            "session_date": "2019-01-02",
            "open": 1,
            "high": 2,
            "low": 0.5,
            "close": 1.5,
            "volume": 100,
            "timezone": "UTC",
            "publisher_id": 1,
        },
    ]
    report = evaluate_arcx_daily(rows, expected_sessions=["2019-01-02", "2019-01-03"])
    assert "2019-01-03" in report.missing_sessions
    assert "2019-01-02" in report.duplicate_sessions


def test_evaluate_arcx_daily_flags_nonpositive_price_and_invalid_ohlc() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "open": -1,
            "high": 2,
            "low": 3,
            "close": 1.5,
            "volume": 100,
            "timezone": "UTC",
            "publisher_id": 1,
        },
    ]
    report = evaluate_arcx_daily(rows, expected_sessions=["2019-01-02"])
    assert report.nonpositive_price_count == 1
    assert report.invalid_ohlc_count == 1  # low > high


def test_evaluate_opra_quotes_flags_crossed_and_locked_and_zero_bid() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "A",
            "bid_price": 2.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "B",
            "bid_price": 1.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "C",
            "bid_price": 0.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
    ]
    report = evaluate_opra_quotes(rows, target_window_sessions=["2019-01-02"])
    assert report.crossed_quote_count == 1
    assert report.locked_quote_count == 1
    assert report.zero_bid_count == 1


def test_evaluate_opra_quotes_zero_and_negative_bid_counters_are_mutually_exclusive() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "A",
            "bid_price": -1.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "B",
            "bid_price": 0.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
    ]
    report = evaluate_opra_quotes(rows, target_window_sessions=["2019-01-02"])
    assert report.negative_price_count == 1
    assert report.zero_bid_count == 1


def test_evaluate_opra_quotes_flags_missing_side() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "A",
            "bid_price": None,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        }
    ]
    report = evaluate_opra_quotes(rows, target_window_sessions=["2019-01-02"])
    assert report.missing_side_count == 1


def test_evaluate_arcx_daily_checks_timezone_and_publisher_consistency() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "open": 1,
            "high": 2,
            "low": 0.5,
            "close": 1.5,
            "volume": 100,
            "timezone": "UTC",
            "publisher_id": 1,
        },
        {
            "session_date": "2019-01-03",
            "open": 1,
            "high": 2,
            "low": 0.5,
            "close": 1.5,
            "volume": 100,
            "timezone": "naive",
            "publisher_id": 2,
        },
    ]
    report = evaluate_arcx_daily(rows, ["2019-01-02", "2019-01-03"])
    assert report.timezone_problem_count == 1
    assert report.publisher_mismatch_count == 1


def test_evaluate_arcx_statistics_and_opra_definitions() -> None:
    statistics = evaluate_arcx_statistics(
        [
            {"session_date": "2019-01-02", "stat_type": "official_close", "publisher_id": 1},
            {"session_date": "2019-01-02", "stat_type": "official_volume", "publisher_id": 1},
        ]
    )
    assert statistics.official_close_available
    assert statistics.official_volume_available

    definitions = evaluate_opra_definitions(
        [
            {
                "option_symbol": "SPY190118C00250000",
                "option_type": "C",
                "expiration": "2019-01-18",
                "strike": "250",
                "multiplier": "100",
                "exercise_style": "A",
                "settlement_style": "P",
            },
            {
                "option_symbol": "SPY190118P00250000",
                "option_type": "P",
                "expiration": "2019-01-18",
                "strike": "250",
                "multiplier": "100",
                "exercise_style": "A",
                "settlement_style": "P",
            },
        ]
    )
    assert definitions.unique_option_symbols == 2
    assert definitions.call_count == 1
    assert definitions.put_count == 1


def test_evaluate_opra_quotes_computes_final_usable_contract_coverage() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "GOOD",
            "timestamp": "2019-01-02T20:59:00Z",
            "bid_price": 1.0,
            "ask_price": 1.1,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "BAD",
            "timestamp": "2019-01-02T20:59:00Z",
            "bid_price": 2.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
    ]
    report = evaluate_opra_quotes(rows, ["2019-01-02"])
    assert report.contracts_with_final_valid_quote == 1
    assert report.contracts_with_no_usable_close_quote == 1


def test_evaluate_opra_quotes_requires_latest_quote_to_be_valid() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "BECAME_BAD",
            "timestamp": "2019-01-02T20:58:00Z",
            "bid_price": 1.0,
            "ask_price": 1.1,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "BECAME_BAD",
            "timestamp": "2019-01-02T20:59:00Z",
            "bid_price": 2.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
    ]
    report = evaluate_opra_quotes(rows, ["2019-01-02"])
    assert report.contracts_with_final_valid_quote == 0
    assert report.contracts_with_no_usable_close_quote == 1


def test_evaluate_opra_quotes_compares_timezone_aware_instants() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "TZ",
            "timestamp": "2019-01-02T21:00:00+01:00",
            "bid_price": 2.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "TZ",
            "timestamp": "2019-01-02T20:59:00Z",
            "bid_price": 1.0,
            "ask_price": 1.1,
            "bid_size": 1,
            "ask_size": 1,
        },
    ]
    report = evaluate_opra_quotes(rows, ["2019-01-02"])
    assert report.contracts_with_final_valid_quote == 1
    assert report.contracts_with_no_usable_close_quote == 0


def test_evaluate_opra_quotes_enforces_five_minute_close_age() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "STALE",
            "timestamp": "2019-01-02T20:53:59Z",
            "bid_price": 1.0,
            "ask_price": 1.1,
            "bid_size": 1,
            "ask_size": 1,
        }
    ]
    report = evaluate_opra_quotes(rows, ["2019-01-02"])
    assert report.contracts_with_final_valid_quote == 0
    assert report.contracts_with_no_usable_close_quote == 1


def test_evaluate_opra_quotes_excludes_out_of_window_contracts_from_coverage() -> None:
    report = evaluate_opra_quotes(
        [
            {
                "session_date": "2019-01-03",
                "contract": "OUTSIDE",
                "timestamp": "2019-01-03T20:59:00Z",
                "bid_price": 1.0,
                "ask_price": 1.1,
                "bid_size": 1,
                "ask_size": 1,
            }
        ],
        ["2019-01-02"],
    )
    assert report.contracts_with_final_valid_quote == 0


def test_evaluate_opra_quotes_ignores_post_close_when_selecting_latest_close_quote() -> None:
    rows = [
        {
            "session_date": "2019-01-02",
            "contract": "POST_CLOSE",
            "timestamp": "2019-01-02T20:59:00Z",
            "bid_price": 1.0,
            "ask_price": 1.1,
            "bid_size": 1,
            "ask_size": 1,
        },
        {
            "session_date": "2019-01-02",
            "contract": "POST_CLOSE",
            "timestamp": "2019-01-02T21:00:01Z",
            "bid_price": 2.0,
            "ask_price": 1.0,
            "bid_size": 1,
            "ask_size": 1,
        },
    ]
    report = evaluate_opra_quotes(rows, ["2019-01-02"])
    assert report.contracts_with_final_valid_quote == 1
    assert report.contracts_with_no_usable_close_quote == 0


def test_quality_evaluators_fail_data_closed_without_crashing_on_nonfinite_values() -> None:
    daily = evaluate_arcx_daily(
        [
            {
                "session_date": "2019-01-02",
                "open": float("nan"),
                "high": "bad",
                "low": 1,
                "close": 1,
                "volume": None,
                "timezone": "UTC",
                "publisher_id": 1,
            }
        ],
        ["2019-01-02"],
    )
    assert daily.nonpositive_price_count == 1
    assert daily.invalid_ohlc_count == 1
    assert daily.nonpositive_volume_count == 1

    quotes = evaluate_opra_quotes(
        [
            {
                "session_date": "2019-01-02",
                "contract": "BAD",
                "bid_price": float("nan"),
                "ask_price": "bad",
                "bid_size": None,
                "ask_size": 1,
            }
        ],
        ["2019-01-02"],
    )
    assert quotes.missing_side_count == 1
    assert quotes.nonpositive_size_count == 1
    assert quotes.contracts_with_no_usable_close_quote == 1


def test_pilot_exit_criteria_documented() -> None:
    assert "minimum_arcx_session_coverage" in PILOT_EXIT_CRITERIA
    assert "minimum_option_bucket_coverage" in PILOT_EXIT_CRITERIA
    assert "minimum_sampled_contract_quote_validity" in PILOT_EXIT_CRITERIA
