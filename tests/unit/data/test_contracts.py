import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from neuralmarket.data.contracts import (
    CONTRACT_MODELS,
    OptionDefinition,
    OptionQuoteSnapshot,
    OptionType,
    UnderlyingDailyBar,
    UnderlyingQuoteSnapshot,
    json_schema_for,
    option_quote_arrow_schema,
    underlying_daily_arrow_schema,
    underlying_quote_arrow_schema,
)
from neuralmarket.data.errors import ContractValidationError
from neuralmarket.data.validation import (
    ensure_quote_matches_definition,
    validate_record,
)

_FIXTURES = Path("tests/fixtures/data")


def _load(name: str) -> list[dict]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.unit
def test_valid_underlying_fixture() -> None:
    for row in _load("underlying_daily_valid.json"):
        bar = UnderlyingDailyBar.model_validate(row)
        assert bar.symbol == "SPY"
        assert isinstance(bar.open, Decimal)
        assert bar.event_timestamp.tzinfo is not None


@pytest.mark.unit
def test_valid_option_fixtures() -> None:
    definition = OptionDefinition.model_validate(_load("option_definition_valid.json")[0])
    quote = OptionQuoteSnapshot.model_validate(_load("option_quote_valid.json")[0])
    assert definition.option_type is OptionType.CALL
    ensure_quote_matches_definition(quote, definition)


@pytest.mark.unit
def test_locked_quote_flagged() -> None:
    rows = _load("option_quote_valid.json")
    locked = OptionQuoteSnapshot.model_validate(rows[1])
    assert locked.is_locked is True


@pytest.mark.unit
def test_naive_timestamp_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_record(
            UnderlyingDailyBar,
            {**_load("underlying_daily_valid.json")[0], "event_timestamp": "2020-01-02T21:00:00"},
        )


@pytest.mark.unit
def test_timestamp_normalized_to_utc() -> None:
    row = {
        **_load("underlying_daily_valid.json")[0],
        "event_timestamp": "2020-01-02T16:00:00-05:00",
    }
    bar = UnderlyingDailyBar.model_validate(row)
    assert bar.event_timestamp.utcoffset().total_seconds() == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "case",
    [
        "underlying_naive_timestamp",
        "underlying_impossible_ohlc",
        "underlying_negative_price",
        "underlying_lowercase_currency",
        "option_invalid_type",
        "option_negative_strike",
        "quote_crossed",
        "quote_negative_size",
        "quote_missing_side",
    ],
)
def test_invalid_records_rejected(case: str) -> None:
    records = {r["case"]: r for r in _load("invalid_records.json")}
    entry = records[case]
    model = CONTRACT_MODELS[entry["model"]]
    with pytest.raises(ContractValidationError):
        validate_record(model, entry["payload"])


@pytest.mark.unit
def test_arrow_schema_fields() -> None:
    underlying = underlying_daily_arrow_schema()
    assert underlying.field("session_date").type.equals(underlying.field("session_date").type)
    assert "event_timestamp" in underlying.names
    quote = option_quote_arrow_schema()
    assert "bid" in quote.names and "ask" in quote.names


@pytest.mark.unit
def test_quote_definition_mismatch_detected() -> None:
    definition = OptionDefinition.model_validate(_load("option_definition_valid.json")[0])
    bad_quote = OptionQuoteSnapshot.model_validate(
        {**_load("option_quote_valid.json")[0], "strike": "999.00"}
    )
    with pytest.raises(ContractValidationError):
        ensure_quote_matches_definition(bad_quote, definition)


@pytest.mark.unit
def test_committed_json_schema_matches_model() -> None:
    for name, model in CONTRACT_MODELS.items():
        committed = json.loads(
            Path(f"data_contracts/{name}.schema.json").read_text(encoding="utf-8")
        )
        assert committed == json_schema_for(model)


@pytest.mark.unit
def test_option_type_enum_is_strict() -> None:
    with pytest.raises(ContractValidationError):
        validate_record(
            OptionDefinition,
            {**_load("option_definition_valid.json")[0], "option_type": "CALL"},
        )


@pytest.mark.unit
def test_expiration_is_date_type() -> None:
    definition = OptionDefinition.model_validate(_load("option_definition_valid.json")[0])
    assert isinstance(definition.expiration_date, date)


def _uq_base() -> dict:
    return _load("underlying_quote_valid.json")[0]


@pytest.mark.unit
def test_underlying_quote_valid_fixture() -> None:
    for row in _load("underlying_quote_valid.json"):
        quote = UnderlyingQuoteSnapshot.model_validate(row)
        assert quote.symbol == "SPY"
        assert quote.midpoint == (quote.bid + quote.ask) / Decimal(2)


@pytest.mark.unit
def test_underlying_quote_locked_flagged() -> None:
    locked = UnderlyingQuoteSnapshot.model_validate(_load("underlying_quote_valid.json")[1])
    assert locked.is_locked is True
    assert locked.relative_spread == Decimal("0")


@pytest.mark.unit
def test_underlying_quote_bad_midpoint_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_record(UnderlyingQuoteSnapshot, {**_uq_base(), "midpoint": "999.00"})


@pytest.mark.unit
def test_underlying_quote_bad_relative_spread_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_record(UnderlyingQuoteSnapshot, {**_uq_base(), "relative_spread": "0.5"})


@pytest.mark.unit
def test_underlying_quote_crossed_rejected() -> None:
    with pytest.raises(ContractValidationError):
        validate_record(
            UnderlyingQuoteSnapshot,
            {**_uq_base(), "bid": "323.80", "ask": "323.70", "midpoint": "323.75"},
        )


@pytest.mark.unit
def test_underlying_quote_missing_side_rejected() -> None:
    payload = _uq_base()
    del payload["bid"]
    with pytest.raises(ContractValidationError):
        validate_record(UnderlyingQuoteSnapshot, payload)


@pytest.mark.unit
def test_underlying_quote_zero_midpoint_requires_null_spread() -> None:
    zero = {
        **_uq_base(),
        "bid": "0",
        "ask": "0",
        "midpoint": "0",
        "relative_spread": None,
    }
    quote = UnderlyingQuoteSnapshot.model_validate(zero)
    assert quote.relative_spread is None
    with pytest.raises(ContractValidationError):
        validate_record(UnderlyingQuoteSnapshot, {**zero, "relative_spread": "0.1"})


@pytest.mark.unit
def test_underlying_quote_arrow_schema() -> None:
    schema = underlying_quote_arrow_schema()
    assert "midpoint" in schema.names
    assert "relative_spread" in schema.names
