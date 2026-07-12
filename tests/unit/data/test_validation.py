import json
from pathlib import Path

import pytest

from neuralmarket.data.contracts import UnderlyingDailyBar
from neuralmarket.data.errors import ContractValidationError
from neuralmarket.data.validation import (
    duplicate_keys,
    ensure_unique,
    validate_records,
)

_FIXTURES = Path("tests/fixtures/data")


def _rows() -> list[dict]:
    return json.loads((_FIXTURES / "underlying_daily_valid.json").read_text(encoding="utf-8"))


@pytest.mark.unit
def test_validate_records_splits_valid_and_invalid() -> None:
    rows = _rows()
    rows.append({**rows[0], "high": "1.00"})  # impossible OHLC
    valid, rejected = validate_records(UnderlyingDailyBar, rows)
    assert len(valid) == 2
    assert len(rejected) == 1
    assert rejected[0][0] == 2


@pytest.mark.unit
def test_no_duplicates_in_clean_table() -> None:
    bars = [UnderlyingDailyBar.model_validate(r) for r in _rows()]
    assert duplicate_keys(bars) == []
    ensure_unique(bars)


@pytest.mark.unit
def test_duplicate_detected() -> None:
    rows = _rows()
    bars = [UnderlyingDailyBar.model_validate(r) for r in [rows[0], rows[0]]]
    assert len(duplicate_keys(bars)) == 1
    with pytest.raises(ContractValidationError, match="Duplicate"):
        ensure_unique(bars)


@pytest.mark.unit
def test_empty_table_has_no_duplicates() -> None:
    assert duplicate_keys([]) == []
