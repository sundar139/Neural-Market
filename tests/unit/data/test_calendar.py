from datetime import date
from pathlib import Path

import pytest

from neuralmarket.data.calendar import (
    calendar_library_version,
    compute_splits,
    session_dates,
)
from neuralmarket.data.configuration import load_data_config
from neuralmarket.data.errors import CoverageError

_CONFIG = Path("configs/data/spy_daily_databento.yaml")


@pytest.fixture(scope="module")
def config():  # type: ignore[no-untyped-def]
    return load_data_config(_CONFIG)


@pytest.fixture(scope="module")
def sessions(config):  # type: ignore[no-untyped-def]
    return session_dates(config.study.calendar, config.study.start_date, config.study.end_date)


@pytest.mark.unit
def test_calendar_version_available() -> None:
    assert calendar_library_version()


@pytest.mark.unit
def test_sessions_are_weekdays_and_sorted(sessions) -> None:  # type: ignore[no-untyped-def]
    assert sessions == sorted(sessions)
    assert all(d.weekday() < 5 for d in sessions)
    # Study starts 2018-05-01 (a valid XNYS session).
    assert sessions[0] == date(2018, 5, 1)


@pytest.mark.unit
def test_compute_splits_boundaries(config, sessions) -> None:  # type: ignore[no-untyped-def]
    result = compute_splits(config, sessions)
    assert result.training_start == date(2018, 5, 1)
    assert result.training_end <= date(2021, 12, 31)
    assert result.validation_end <= date(2023, 6, 30)
    assert result.test_end <= date(2025, 12, 31)
    # Exactly 100 excluded sessions at each development boundary.
    assert [e.session_count for e in result.boundary_exclusions] == [100, 100]


@pytest.mark.unit
def test_splits_do_not_overlap(config, sessions) -> None:  # type: ignore[no-untyped-def]
    result = compute_splits(config, sessions)
    assert result.training_end < result.validation_start
    assert result.validation_end < result.test_start
    # Gap between splits is strictly the boundary exclusion.
    assert result.training_start < result.training_end < result.test_start


@pytest.mark.unit
def test_all_split_dates_are_sessions(config, sessions) -> None:  # type: ignore[no-untyped-def]
    result = compute_splits(config, sessions)
    session_set = set(sessions)
    for boundary in (
        result.training_start,
        result.training_end,
        result.validation_start,
        result.validation_end,
        result.test_start,
        result.test_end,
    ):
        assert boundary in session_set


@pytest.mark.unit
def test_deterministic_hashes(config, sessions) -> None:  # type: ignore[no-untyped-def]
    first = compute_splits(config, sessions)
    second = compute_splits(config, sessions)
    assert first.training_hash == second.training_hash
    assert first.calendar_hash == second.calendar_hash


@pytest.mark.unit
def test_insufficient_calendar_raises(config) -> None:  # type: ignore[no-untyped-def]
    short = session_dates(config.study.calendar, date(2018, 1, 2), date(2018, 3, 1))
    with pytest.raises(CoverageError):
        compute_splits(config, short)
