"""NYSE-session-aware calendar utilities and chronological split computation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from importlib import metadata

import exchange_calendars as xcals

from neuralmarket.data.configuration import DataConfig
from neuralmarket.data.errors import CoverageError


def calendar_library_version() -> str:
    """Return the installed exchange-calendars library version."""
    return metadata.version("exchange-calendars")


def session_dates(calendar_name: str, start: date, end: date) -> list[date]:
    """Return valid session dates for a calendar within an inclusive range.

    Args:
        calendar_name: Exchange calendar code, for example ``"XNYS"``.
        start: Inclusive first date.
        end: Inclusive last date.

    Returns:
        Sorted list of session dates.
    """
    # Pad the constructed calendar window so a query bound that lands on a
    # non-session date (for example a Saturday month-end) stays in bounds. The
    # queried range is unchanged, so session-aligned callers are unaffected.
    pad = timedelta(days=7)
    calendar = xcals.get_calendar(
        calendar_name, start=(start - pad).isoformat(), end=(end + pad).isoformat()
    )
    sessions = calendar.sessions_in_range(start.isoformat(), end.isoformat())
    return [ts.date() for ts in sessions]


def _hash_dates(dates: list[date]) -> str:
    """Return a SHA-256 hash over a canonical list of ISO dates."""
    payload = "\n".join(d.isoformat() for d in dates)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BoundaryExclusion:
    """A contiguous block of excluded sessions between two splits."""

    start_date: date
    end_date: date
    session_count: int
    session_hash: str


@dataclass(frozen=True)
class SplitResult:
    """Computed chronological split boundaries and provenance hashes."""

    training_start: date
    training_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    training_sessions: int
    validation_sessions: int
    test_sessions: int
    training_hash: str
    validation_hash: str
    test_hash: str
    calendar_hash: str
    boundary_exclusions: tuple[BoundaryExclusion, ...]


def _last_index_on_or_before(sessions: list[date], anchor: date) -> int:
    for index in range(len(sessions) - 1, -1, -1):
        if sessions[index] <= anchor:
            return index
    raise CoverageError(f"No session on or before {anchor.isoformat()}")


def _first_index_on_or_after(sessions: list[date], anchor: date) -> int:
    for index, session in enumerate(sessions):
        if session >= anchor:
            return index
    raise CoverageError(f"No session on or after {anchor.isoformat()}")


def _exclusion(sessions: list[date], start_idx: int, count: int, label: str) -> BoundaryExclusion:
    block = sessions[start_idx : start_idx + count]
    if len(block) != count:
        raise CoverageError(
            f"Insufficient sessions for {label} exclusion: needed {count}, got {len(block)}"
        )
    return BoundaryExclusion(
        start_date=block[0],
        end_date=block[-1],
        session_count=count,
        session_hash=_hash_dates(block),
    )


def compute_splits(config: DataConfig, sessions: list[date]) -> SplitResult:
    """Compute deterministic chronological splits with purge and embargo.

    Follows the frozen split policy: training ends on the final session on or
    before its anchor; a fixed boundary of purge + embargo sessions is excluded;
    validation then begins on the next session; the same rule applies at the
    validation/test boundary.

    Args:
        config: Validated market-data configuration.
        sessions: Sorted session dates covering the full study range.

    Returns:
        A :class:`SplitResult`.

    Raises:
        CoverageError: If the calendar cannot supply the required sessions, a
            split is empty, or splits would overlap.
    """
    splits = config.splits
    boundary = splits.boundary_exclusion_sessions

    train_start_idx = _first_index_on_or_after(sessions, splits.training_start)
    train_end_idx = _last_index_on_or_before(sessions, splits.training_anchor_end)

    excl1 = _exclusion(sessions, train_end_idx + 1, boundary, "training/validation")
    val_start_idx = train_end_idx + 1 + boundary
    val_end_idx = _last_index_on_or_before(sessions, splits.validation_anchor_end)

    excl2 = _exclusion(sessions, val_end_idx + 1, boundary, "validation/test")
    test_start_idx = val_end_idx + 1 + boundary
    test_end_idx = _last_index_on_or_before(sessions, splits.test_anchor_end)

    ordered = [
        train_start_idx,
        train_end_idx,
        val_start_idx,
        val_end_idx,
        test_start_idx,
        test_end_idx,
    ]
    if ordered != sorted(ordered) or len(set(ordered)) != len(ordered):
        raise CoverageError("Computed split indices overlap or are out of order.")

    training = sessions[train_start_idx : train_end_idx + 1]
    validation = sessions[val_start_idx : val_end_idx + 1]
    test = sessions[test_start_idx : test_end_idx + 1]

    for label, block in (("training", training), ("validation", validation), ("test", test)):
        if len(block) < boundary:
            raise CoverageError(
                f"{label} split has too few sessions ({len(block)}); expected at least {boundary}."
            )

    return SplitResult(
        training_start=training[0],
        training_end=training[-1],
        validation_start=validation[0],
        validation_end=validation[-1],
        test_start=test[0],
        test_end=test[-1],
        training_sessions=len(training),
        validation_sessions=len(validation),
        test_sessions=len(test),
        training_hash=_hash_dates(training),
        validation_hash=_hash_dates(validation),
        test_hash=_hash_dates(test),
        calendar_hash=_hash_dates(sessions),
        boundary_exclusions=(excl1, excl2),
    )
