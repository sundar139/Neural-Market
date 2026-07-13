"""Deterministic, metadata-only calendar helpers for acquisition planning.

All session and window selection here is calendar-based only; none of it
inspects market prices, quotes, or returns, so budget planning cannot
introduce look-ahead bias. Quote windows use the scheduled session close
(regular or early), converted to timezone-aware UTC.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import cast

import exchange_calendars as xcals

from neuralmarket.data.errors import CoverageError

QUOTE_WINDOW_MINUTES = 10
PILOT_MINIMUM_SESSIONS = 18


_YEAR_PAD = timedelta(days=7)


@lru_cache(maxsize=64)
def _cached_calendar(calendar_name: str, year_start: int, year_end: int) -> xcals.ExchangeCalendar:
    return xcals.get_calendar(
        calendar_name,
        start=(date(year_start, 1, 1) - _YEAR_PAD).isoformat(),
        end=(date(year_end, 12, 31) + _YEAR_PAD).isoformat(),
    )


def _calendar(calendar_name: str, start: date, end: date | None = None) -> xcals.ExchangeCalendar:
    """Return a whole-year-bounded calendar, cached by (name, year range).

    Callers query specific dates within ``[start, end]``, which always fall
    strictly inside the returned calendar's whole-year bounds, so this never
    hits a boundary edge case. Caching by year avoids rebuilding a fresh
    calendar for every single session queried.
    """
    span_end = end or start
    return _cached_calendar(calendar_name, start.year, span_end.year)


def session_close_utc(calendar_name: str, session: date) -> datetime:
    """Return the timezone-aware UTC scheduled close for one exchange session.

    Uses the exchange calendar's actual scheduled close, so early-close
    sessions are handled without hardcoding a fixed close time.
    """
    calendar = _calendar(calendar_name, session, session)
    close = calendar.session_close(session.isoformat())
    pydatetime = cast(datetime, close.to_pydatetime())
    return pydatetime.astimezone(UTC)


def quote_window(calendar_name: str, session: date) -> tuple[datetime, datetime]:
    """Return the half-open ``[window_start, window_end)`` final quote window.

    ``window_end`` is the scheduled session close; ``window_start`` is exactly
    :data:`QUOTE_WINDOW_MINUTES` earlier. Both bounds are timezone-aware UTC.
    """
    window_end = session_close_utc(calendar_name, session)
    window_start = window_end - timedelta(minutes=QUOTE_WINDOW_MINUTES)
    return window_start, window_end


def definition_window(session: date) -> tuple[datetime, datetime]:
    """Return a discrete, half-open 24-hour UTC interval for one session date."""
    start = datetime(session.year, session.month, session.day, tzinfo=UTC)
    return start, start + timedelta(days=1)


def full_day_range_window(start: date, end_inclusive: date) -> tuple[datetime, datetime]:
    """Return a half-open, whole-day-multiple UTC interval covering ``[start, end_inclusive]``.

    Used for catalog (definition/daily/statistics) cost estimates, which must
    use discrete 24-hour-multiple ranges rather than ten-minute windows.

    Raises:
        ValueError: If ``end_inclusive`` is before ``start``.
    """
    if end_inclusive < start:
        raise ValueError("end_inclusive must not be before start")
    window_start = datetime(start.year, start.month, start.day, tzinfo=UTC)
    end_next = end_inclusive + timedelta(days=1)
    window_end = datetime(end_next.year, end_next.month, end_next.day, tzinfo=UTC)
    return window_start, window_end


def daily_schedule(sessions: list[date]) -> list[date]:
    """Return every session unchanged (Strategy A: daily close windows)."""
    return list(sessions)


def twice_weekly_schedule(sessions: list[date]) -> list[date]:
    """Return sessions falling on Tuesday or Thursday (Strategy B).

    A target weekday that is not itself a session is omitted rather than
    shifted, so the schedule never selects an ambiguous adjacent day.
    """
    return [s for s in sessions if s.weekday() in (1, 3)]


def weekly_schedule(sessions: list[date]) -> list[date]:
    """Return sessions falling on Wednesday (Strategy C); non-sessions omitted."""
    return [s for s in sessions if s.weekday() == 2]


def _quarter_index(month: int) -> int:
    return (month - 1) // 3


def _quarter_middle_month(quarter: int) -> int:
    # Quarter 0 -> Feb (2), 1 -> May (5), 2 -> Aug (8), 3 -> Nov (11).
    return quarter * 3 + 2


def _first_weekday_of_month(year: int, month: int, weekday: int) -> date:
    candidate = date(year, month, 1)
    offset = (weekday - candidate.weekday()) % 7
    return candidate + timedelta(days=offset)


def _third_weekday_of_month(year: int, month: int, weekday: int) -> date:
    return _first_weekday_of_month(year, month, weekday) + timedelta(days=14)


def _last_day_of_month(year: int, month: int) -> date:
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    return next_month - timedelta(days=1)


def _nearest_session_on_or_after(sorted_sessions: list[date], candidate: date) -> date | None:
    for session in sorted_sessions:
        if session >= candidate:
            return session
    return None


def _nearest_session_on_or_before(sorted_sessions: list[date], candidate: date) -> date | None:
    for session in reversed(sorted_sessions):
        if session <= candidate:
            return session
    return None


def quarterly_sample_sessions(sessions: list[date]) -> list[date]:
    """Return a deterministic, calendar-based cost-sampling session set.

    For each calendar quarter overlapping ``sessions``, select up to three
    sessions:

    1. Ordinary-session sample: the first Wednesday of the quarter's middle
       month (nearest session on or after, if that Wednesday is not itself a
       session).
    2. Expiry-proxy sample: the third Friday of the middle month, or the
       preceding session when that Friday is not a session.
    3. Quarter-end sample: the final session of the quarter.

    Coincident sessions are deduplicated. No market value is inspected.

    Args:
        sessions: Sorted session dates spanning the development period.

    Returns:
        A sorted, deduplicated list of sampled session dates.

    Raises:
        CoverageError: If ``sessions`` is empty.
    """
    if not sessions:
        raise CoverageError("Cannot sample sessions from an empty session list.")
    ordered = sorted(sessions)
    quarters: dict[tuple[int, int], list[date]] = {}
    for session in ordered:
        key = (session.year, _quarter_index(session.month))
        quarters.setdefault(key, []).append(session)

    sampled: set[date] = set()
    for (year, quarter), quarter_sessions in quarters.items():
        middle_month = _quarter_middle_month(quarter)
        ordinary_candidate = _first_weekday_of_month(year, middle_month, 2)  # Wednesday
        ordinary = _nearest_session_on_or_after(quarter_sessions, ordinary_candidate)
        if ordinary is not None:
            sampled.add(ordinary)

        expiry_candidate = _third_weekday_of_month(year, middle_month, 4)  # Friday
        expiry = _nearest_session_on_or_before(quarter_sessions, expiry_candidate)
        if expiry is not None:
            sampled.add(expiry)

        sampled.add(quarter_sessions[-1])

    return sorted(sampled)


def sessions_in_month(calendar_name: str, year_month: str) -> list[date]:
    """Return sorted session dates for one calendar month.

    Args:
        calendar_name: Exchange calendar code, for example ``"XNYS"``.
        year_month: Month label in ``"YYYY-MM"`` form.

    Returns:
        Sorted list of session dates within that month.
    """
    year_str, month_str = year_month.split("-")
    year, month = int(year_str), int(month_str)
    start = date(year, month, 1)
    end = _last_day_of_month(year, month)
    calendar = _calendar(calendar_name, start, end)
    return [ts.date() for ts in calendar.sessions_in_range(start.isoformat(), end.isoformat())]


def select_pilot_month(calendar_name: str, candidate_year: int) -> tuple[str, list[date]]:
    """Select the first complete calendar month with enough sessions, by calendar rule only.

    Scans January through December of ``candidate_year`` in order and returns
    the first month whose session count is at least
    :data:`PILOT_MINIMUM_SESSIONS`. Selection never inspects market prices.

    Args:
        calendar_name: Exchange calendar code, for example ``"XNYS"``.
        candidate_year: The calendar year to scan.

    Returns:
        A tuple of ``(month_label, sessions)`` where ``month_label`` is
        ``"YYYY-MM"`` and ``sessions`` are the month's session dates.

    Raises:
        CoverageError: If no month in the candidate year qualifies.
    """
    for month in range(1, 13):
        start = date(candidate_year, month, 1)
        end = _last_day_of_month(candidate_year, month)
        calendar = _calendar(calendar_name, start, end)
        month_sessions = [
            ts.date() for ts in calendar.sessions_in_range(start.isoformat(), end.isoformat())
        ]
        if len(month_sessions) >= PILOT_MINIMUM_SESSIONS:
            return f"{candidate_year:04d}-{month:02d}", month_sessions
    raise CoverageError(f"No complete month in {candidate_year} has enough valid sessions.")
