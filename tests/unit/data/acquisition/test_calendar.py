from datetime import date, timedelta

import pytest

from neuralmarket.data.acquisition.calendar import (
    QUOTE_WINDOW_MINUTES,
    daily_schedule,
    definition_window,
    full_day_range_window,
    quarterly_sample_sessions,
    quote_window,
    select_pilot_month,
    sessions_in_month,
    twice_weekly_schedule,
    weekly_schedule,
)
from neuralmarket.data.calendar import session_dates
from neuralmarket.data.errors import CoverageError

_CALENDAR = "XNYS"


@pytest.mark.unit
def test_quote_window_regular_close_is_ten_minutes() -> None:
    start, end = quote_window(_CALENDAR, date(2019, 1, 2))
    assert (end - start) == timedelta(minutes=QUOTE_WINDOW_MINUTES)
    assert start.tzinfo is not None and end.tzinfo is not None
    assert end.hour == 21 and end.minute == 0  # 16:00 ET regular close in UTC (winter)


@pytest.mark.unit
def test_quote_window_early_close_uses_actual_close() -> None:
    # 2019-07-03 is a scheduled early close (day before July 4th).
    start, end = quote_window(_CALENDAR, date(2019, 7, 3))
    assert (end - start) == timedelta(minutes=QUOTE_WINDOW_MINUTES)
    assert end.hour == 17 and end.minute == 0  # 13:00 ET early close in UTC (summer)


@pytest.mark.unit
def test_definition_window_is_whole_day() -> None:
    start, end = definition_window(date(2019, 1, 2))
    assert (end - start) == timedelta(days=1)
    assert start.hour == 0 and start.minute == 0


@pytest.mark.unit
def test_full_day_range_window_spans_inclusive_end() -> None:
    start, end = full_day_range_window(date(2018, 5, 1), date(2018, 5, 3))
    assert start == start.replace(hour=0, minute=0, second=0, microsecond=0)
    assert (end - start) == timedelta(days=3)


@pytest.mark.unit
def test_full_day_range_window_rejects_reversed_range() -> None:
    with pytest.raises(ValueError, match="must not be before"):
        full_day_range_window(date(2018, 5, 3), date(2018, 5, 1))


@pytest.mark.unit
def test_daily_schedule_is_identity() -> None:
    sessions = session_dates(_CALENDAR, date(2019, 1, 1), date(2019, 1, 31))
    assert daily_schedule(sessions) == sessions


@pytest.mark.unit
def test_twice_weekly_schedule_only_tuesday_thursday() -> None:
    sessions = session_dates(_CALENDAR, date(2019, 1, 1), date(2019, 3, 31))
    schedule = twice_weekly_schedule(sessions)
    assert schedule
    assert all(d.weekday() in (1, 3) for d in schedule)


@pytest.mark.unit
def test_weekly_schedule_only_wednesday() -> None:
    sessions = session_dates(_CALENDAR, date(2019, 1, 1), date(2019, 3, 31))
    schedule = weekly_schedule(sessions)
    assert schedule
    assert all(d.weekday() == 2 for d in schedule)


@pytest.mark.unit
def test_twice_weekly_omits_non_session_holiday_weekday() -> None:
    # 2019-01-01 is a Tuesday and a holiday (not a session); it must be
    # entirely absent, not shifted to an adjacent day.
    sessions = session_dates(_CALENDAR, date(2018, 12, 28), date(2019, 1, 4))
    assert date(2019, 1, 1) not in sessions
    schedule = twice_weekly_schedule(sessions)
    assert date(2019, 1, 1) not in schedule
    assert date(2018, 12, 31) not in schedule  # Monday, correctly excluded


@pytest.mark.unit
def test_quarterly_sample_sessions_dedup_and_bounded() -> None:
    sessions = session_dates(_CALENDAR, date(2019, 1, 1), date(2019, 12, 31))
    sampled = quarterly_sample_sessions(sessions)
    assert sampled == sorted(set(sampled))
    assert 1 <= len(sampled) <= 12  # at most 3 per quarter, 4 quarters
    assert all(s in sessions for s in sampled)


@pytest.mark.unit
def test_quarterly_sample_sessions_empty_raises() -> None:
    with pytest.raises(CoverageError):
        quarterly_sample_sessions([])


@pytest.mark.unit
def test_quarterly_sample_includes_quarter_end_session() -> None:
    sessions = session_dates(_CALENDAR, date(2019, 1, 1), date(2019, 3, 31))
    sampled = quarterly_sample_sessions(sessions)
    assert sessions[-1] in sampled


@pytest.mark.unit
def test_sessions_in_month_matches_january_2019() -> None:
    sessions = sessions_in_month(_CALENDAR, "2019-01")
    assert sessions == session_dates(_CALENDAR, date(2019, 1, 1), date(2019, 1, 31))
    assert len(sessions) == 21
    assert sessions == sorted(sessions)


@pytest.mark.unit
def test_select_pilot_month_deterministic_2019() -> None:
    label, month_sessions = select_pilot_month(_CALENDAR, 2019)
    assert label == "2019-01"
    assert len(month_sessions) >= 18
    assert month_sessions == sorted(month_sessions)
    assert all(d.year == 2019 and d.month == 1 for d in month_sessions)


@pytest.mark.unit
def test_select_pilot_month_no_qualifying_month_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import neuralmarket.data.acquisition.calendar as cal

    monkeypatch.setattr(cal, "PILOT_MINIMUM_SESSIONS", 10_000)
    with pytest.raises(CoverageError):
        select_pilot_month(_CALENDAR, 2019)
