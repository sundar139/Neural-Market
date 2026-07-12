import pytest

from neuralmarket.data.sources.symbology import (
    SymbologyStatus,
    normalize_status,
    status_acceptable,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, SymbologyStatus.OK),
        ("0", SymbologyStatus.OK),
        (" 0 ", SymbologyStatus.OK),
        (1, SymbologyStatus.PARTIALLY_RESOLVED),
        ("1", SymbologyStatus.PARTIALLY_RESOLVED),
        (2, SymbologyStatus.NOT_FOUND),
        ("2", SymbologyStatus.NOT_FOUND),
    ],
)
def test_normalize_status_accepts_known_codes(raw: object, expected: SymbologyStatus) -> None:
    assert normalize_status(raw) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw",
    [True, False, 0.0, 1.0, "OK", "", "  ", "0.0", 200, "200", -1, 3, None, [], {}, "success"],
)
def test_normalize_status_rejects_invalid(raw: object) -> None:
    with pytest.raises(ValueError):
        normalize_status(raw)


@pytest.mark.unit
def test_status_acceptable_raw_symbol_requires_ok() -> None:
    assert status_acceptable(SymbologyStatus.OK, parent_expansion=False) is True
    assert status_acceptable(SymbologyStatus.PARTIALLY_RESOLVED, parent_expansion=False) is False
    assert status_acceptable(SymbologyStatus.NOT_FOUND, parent_expansion=False) is False


@pytest.mark.unit
def test_status_acceptable_parent_permits_partial_but_not_found() -> None:
    assert status_acceptable(SymbologyStatus.OK, parent_expansion=True) is True
    assert status_acceptable(SymbologyStatus.PARTIALLY_RESOLVED, parent_expansion=True) is True
    assert status_acceptable(SymbologyStatus.NOT_FOUND, parent_expansion=True) is False
