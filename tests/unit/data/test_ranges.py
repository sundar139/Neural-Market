from datetime import date

import pytest

from neuralmarket.data.sources.base import (
    HalfOpenDateRange,
    SymbolMappingInterval,
    merge_mapping_intervals,
)


@pytest.mark.unit
def test_inclusive_range_converts_to_half_open_next_year() -> None:
    result = HalfOpenDateRange.from_inclusive(date(2018, 5, 1), date(2025, 12, 31))
    assert result == HalfOpenDateRange(date(2018, 5, 1), date(2026, 1, 1))


@pytest.mark.unit
def test_inclusive_range_rejects_reverse_order() -> None:
    with pytest.raises(ValueError, match="before"):
        HalfOpenDateRange.from_inclusive(date(2025, 1, 2), date(2025, 1, 1))


@pytest.mark.unit
def test_merge_mapping_intervals_merges_adjacent_overlap_and_changing_ids() -> None:
    request = HalfOpenDateRange(date(2018, 5, 1), date(2026, 1, 1))
    intervals = (
        SymbolMappingInterval(date(2018, 5, 1), date(2020, 1, 1), "1"),
        SymbolMappingInterval(date(2020, 1, 1), date(2022, 1, 1), "2"),
        SymbolMappingInterval(date(2021, 6, 1), date(2026, 1, 1), "3"),
    )
    merged, uncovered = merge_mapping_intervals(intervals, request)
    assert merged == (HalfOpenDateRange(date(2018, 5, 1), date(2026, 1, 1)),)
    assert uncovered == ()


@pytest.mark.unit
def test_merge_mapping_intervals_preserves_one_day_gap() -> None:
    request = HalfOpenDateRange(date(2018, 5, 1), date(2026, 1, 1))
    intervals = (
        SymbolMappingInterval(date(2018, 5, 1), date(2020, 1, 1), "1"),
        SymbolMappingInterval(date(2020, 1, 2), date(2026, 1, 1), "2"),
    )
    _, uncovered = merge_mapping_intervals(intervals, request)
    assert uncovered == (HalfOpenDateRange(date(2020, 1, 1), date(2020, 1, 2)),)
