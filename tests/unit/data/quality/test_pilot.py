"""Tests for pilot data-quality report framework."""

from neuralmarket.data.quality.pilot import (
    PILOT_EXIT_CRITERIA,
    evaluate_arcx_daily,
    evaluate_opra_quotes,
)


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


def test_pilot_exit_criteria_documented() -> None:
    assert "minimum_arcx_session_coverage" in PILOT_EXIT_CRITERIA
    assert "minimum_option_bucket_coverage" in PILOT_EXIT_CRITERIA
    assert "minimum_sampled_contract_quote_validity" in PILOT_EXIT_CRITERIA
