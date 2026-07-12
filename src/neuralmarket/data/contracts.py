"""Canonical, provider-neutral market-data contracts.

Row-level semantics are validated with Pydantic models; table-level storage
contracts are described with PyArrow schemas; JSON Schema documents provide a
language-neutral, versioned contract. The JSON Schema for each model is derived
from the same typed model so the three representations cannot silently diverge.

All event timestamps are timezone-aware UTC. Trading-session dates are kept
separate as calendar dates. Prices and strikes use :class:`decimal.Decimal` to
avoid binary-float equality hazards. No provider-specific class names, integer
price encodings, or vendor enum values appear here.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

import pyarrow as pa
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"

_CURRENCY_PATTERN = r"^[A-Z]{3}$"


def _ensure_utc(value: datetime) -> datetime:
    """Require a timezone-aware datetime and normalize it to UTC."""
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


AwareUTCDatetime = Annotated[datetime, AfterValidator(_ensure_utc)]


class OptionType(str, Enum):
    """Option right."""

    CALL = "call"
    PUT = "put"


class ExerciseStyle(str, Enum):
    """Option exercise style."""

    AMERICAN = "american"
    EUROPEAN = "european"


class SettlementStyle(str, Enum):
    """Option settlement style."""

    PHYSICAL = "physical"
    CASH = "cash"


class AdjustmentStatus(str, Enum):
    """Whether prices have been split/dividend adjusted."""

    UNADJUSTED = "unadjusted"
    ADJUSTED = "adjusted"


class RejectionReason(str, Enum):
    """Typed reasons a record may be rejected from a normalized table."""

    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_TIMESTAMP = "invalid_timestamp"
    DUPLICATE_RECORD = "duplicate_record"
    CROSSED_QUOTE = "crossed_quote"
    NEGATIVE_PRICE = "negative_price"
    INVALID_SIZE = "invalid_size"
    STALE_QUOTE = "stale_quote"
    UNKNOWN_CONTRACT = "unknown_contract"
    CONTRACT_MISMATCH = "contract_mismatch"
    OUTSIDE_REGULAR_SESSION = "outside_regular_session"
    CORRUPTED_RECORD = "corrupted_record"
    SPLIT_BOUNDARY_VIOLATION = "split_boundary_violation"


_NonEmptyStr = Annotated[str, Field(min_length=1)]
_PositivePrice = Annotated[Decimal, Field(gt=0)]
_NonNegativePrice = Annotated[Decimal, Field(ge=0)]
_Currency = Annotated[str, Field(pattern=_CURRENCY_PATTERN)]


class UnderlyingDailyBar(BaseModel):
    """Canonical daily OHLCV bar for an underlying instrument."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_date: date
    event_timestamp: AwareUTCDatetime
    symbol: _NonEmptyStr
    open: _PositivePrice
    high: _PositivePrice
    low: _PositivePrice
    close: _PositivePrice
    volume: int = Field(ge=0)
    currency: _Currency
    adjustment_status: AdjustmentStatus
    source: _NonEmptyStr
    source_dataset: _NonEmptyStr
    source_symbol: _NonEmptyStr
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def _check_ohlc(self) -> UnderlyingDailyBar:
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be >= open, low, and close")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be <= open, high, and close")
        return self


class OptionDefinition(BaseModel):
    """Canonical point-in-time option contract definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    definition_timestamp: AwareUTCDatetime
    instrument_id: _NonEmptyStr
    option_symbol: _NonEmptyStr
    raw_symbol: _NonEmptyStr
    underlying_symbol: _NonEmptyStr
    expiration_date: date
    strike: _PositivePrice
    option_type: OptionType
    exercise_style: ExerciseStyle
    settlement_style: SettlementStyle
    contract_multiplier: _PositivePrice
    currency: _Currency
    source: _NonEmptyStr
    source_dataset: _NonEmptyStr
    schema_version: str = SCHEMA_VERSION


class OptionQuoteSnapshot(BaseModel):
    """Canonical end-of-day consolidated option quote snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_timestamp: AwareUTCDatetime
    session_date: date
    instrument_id: _NonEmptyStr
    option_symbol: _NonEmptyStr
    underlying_symbol: _NonEmptyStr
    expiration_date: date
    strike: _PositivePrice
    option_type: OptionType
    bid: _NonNegativePrice
    ask: _NonNegativePrice
    bid_size: int = Field(ge=0)
    ask_size: int = Field(ge=0)
    currency: _Currency
    source: _NonEmptyStr
    source_dataset: _NonEmptyStr
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def _check_quote(self) -> OptionQuoteSnapshot:
        if self.ask < self.bid:
            raise ValueError("crossed quote: ask must be >= bid")
        return self

    @property
    def is_locked(self) -> bool:
        """Whether the quote is locked (bid equals ask)."""
        return self.bid == self.ask

    def agrees_with_definition(self, definition: OptionDefinition) -> bool:
        """Return whether this quote's contract terms match a point-in-time definition."""
        return (
            self.instrument_id == definition.instrument_id
            and self.strike == definition.strike
            and self.expiration_date == definition.expiration_date
            and self.option_type == definition.option_type
        )


_MIDPOINT_TOLERANCE = Decimal("0.000001")


class UnderlyingQuoteSnapshot(BaseModel):
    """Canonical end-of-day aggregated BBO snapshot for the underlying.

    ``midpoint`` is ``(bid + ask) / 2``. ``relative_spread`` uses the midpoint as
    its denominator, i.e. ``(ask - bid) / midpoint``; when the midpoint is zero the
    relative spread is unavailable (``None``) rather than infinite.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_timestamp: AwareUTCDatetime
    session_date: date
    symbol: _NonEmptyStr
    bid: _NonNegativePrice
    ask: _NonNegativePrice
    bid_size: int = Field(ge=0)
    ask_size: int = Field(ge=0)
    midpoint: _NonNegativePrice
    relative_spread: Decimal | None
    currency: _Currency
    source: _NonEmptyStr
    source_dataset: _NonEmptyStr
    source_symbol: _NonEmptyStr
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def _check_quote(self) -> UnderlyingQuoteSnapshot:
        if self.ask < self.bid:
            raise ValueError("crossed quote: ask must be >= bid")
        expected_mid = (self.bid + self.ask) / Decimal(2)
        if abs(self.midpoint - expected_mid) > _MIDPOINT_TOLERANCE:
            raise ValueError("midpoint must equal (bid + ask) / 2")
        if self.midpoint == 0:
            if self.relative_spread is not None:
                raise ValueError("relative_spread must be unavailable when midpoint is zero")
        else:
            expected_rel = (self.ask - self.bid) / self.midpoint
            if self.relative_spread is None:
                raise ValueError("relative_spread is required when midpoint is positive")
            if abs(self.relative_spread - expected_rel) > _MIDPOINT_TOLERANCE:
                raise ValueError("relative_spread must equal (ask - bid) / midpoint")
        return self

    @property
    def is_locked(self) -> bool:
        """Whether the quote is locked (bid equals ask)."""
        return self.bid == self.ask


class RejectedRecord(BaseModel):
    """Canonical record capturing why a source row was rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: _NonEmptyStr
    source: _NonEmptyStr
    source_dataset: _NonEmptyStr
    source_file_or_request: _NonEmptyStr
    event_timestamp: AwareUTCDatetime
    instrument_id: str | None
    reason_code: RejectionReason
    reason_detail: str
    filter_version: _NonEmptyStr
    payload_hash: _NonEmptyStr


# --- PyArrow storage schemas ---------------------------------------------------
# Prices and strikes are stored as decimal128 to preserve exact values.
_PRICE_TYPE = pa.decimal128(18, 6)


def underlying_daily_arrow_schema() -> pa.Schema:
    """PyArrow storage schema for normalized underlying daily bars."""
    return pa.schema(
        [
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("event_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("symbol", pa.string(), nullable=False),
            pa.field("open", _PRICE_TYPE, nullable=False),
            pa.field("high", _PRICE_TYPE, nullable=False),
            pa.field("low", _PRICE_TYPE, nullable=False),
            pa.field("close", _PRICE_TYPE, nullable=False),
            pa.field("volume", pa.int64(), nullable=False),
            pa.field("currency", pa.string(), nullable=False),
            pa.field("adjustment_status", pa.string(), nullable=False),
            pa.field("source", pa.string(), nullable=False),
            pa.field("source_dataset", pa.string(), nullable=False),
            pa.field("source_symbol", pa.string(), nullable=False),
            pa.field("schema_version", pa.string(), nullable=False),
        ]
    )


def option_definition_arrow_schema() -> pa.Schema:
    """PyArrow storage schema for normalized point-in-time option definitions."""
    return pa.schema(
        [
            pa.field("definition_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("instrument_id", pa.string(), nullable=False),
            pa.field("option_symbol", pa.string(), nullable=False),
            pa.field("raw_symbol", pa.string(), nullable=False),
            pa.field("underlying_symbol", pa.string(), nullable=False),
            pa.field("expiration_date", pa.date32(), nullable=False),
            pa.field("strike", _PRICE_TYPE, nullable=False),
            pa.field("option_type", pa.string(), nullable=False),
            pa.field("exercise_style", pa.string(), nullable=False),
            pa.field("settlement_style", pa.string(), nullable=False),
            pa.field("contract_multiplier", _PRICE_TYPE, nullable=False),
            pa.field("currency", pa.string(), nullable=False),
            pa.field("source", pa.string(), nullable=False),
            pa.field("source_dataset", pa.string(), nullable=False),
            pa.field("schema_version", pa.string(), nullable=False),
        ]
    )


def underlying_quote_arrow_schema() -> pa.Schema:
    """PyArrow storage schema for normalized underlying BBO snapshots."""
    return pa.schema(
        [
            pa.field("event_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("symbol", pa.string(), nullable=False),
            pa.field("bid", _PRICE_TYPE, nullable=False),
            pa.field("ask", _PRICE_TYPE, nullable=False),
            pa.field("bid_size", pa.int64(), nullable=False),
            pa.field("ask_size", pa.int64(), nullable=False),
            pa.field("midpoint", _PRICE_TYPE, nullable=False),
            pa.field("relative_spread", _PRICE_TYPE, nullable=True),
            pa.field("currency", pa.string(), nullable=False),
            pa.field("source", pa.string(), nullable=False),
            pa.field("source_dataset", pa.string(), nullable=False),
            pa.field("source_symbol", pa.string(), nullable=False),
            pa.field("schema_version", pa.string(), nullable=False),
        ]
    )


def option_quote_arrow_schema() -> pa.Schema:
    """PyArrow storage schema for normalized option quote snapshots."""
    return pa.schema(
        [
            pa.field("event_timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
            pa.field("session_date", pa.date32(), nullable=False),
            pa.field("instrument_id", pa.string(), nullable=False),
            pa.field("option_symbol", pa.string(), nullable=False),
            pa.field("underlying_symbol", pa.string(), nullable=False),
            pa.field("expiration_date", pa.date32(), nullable=False),
            pa.field("strike", _PRICE_TYPE, nullable=False),
            pa.field("option_type", pa.string(), nullable=False),
            pa.field("bid", _PRICE_TYPE, nullable=False),
            pa.field("ask", _PRICE_TYPE, nullable=False),
            pa.field("bid_size", pa.int64(), nullable=False),
            pa.field("ask_size", pa.int64(), nullable=False),
            pa.field("currency", pa.string(), nullable=False),
            pa.field("source", pa.string(), nullable=False),
            pa.field("source_dataset", pa.string(), nullable=False),
            pa.field("schema_version", pa.string(), nullable=False),
        ]
    )


# --- JSON Schema derivation ----------------------------------------------------

CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "underlying_daily": UnderlyingDailyBar,
    "underlying_quote_snapshot": UnderlyingQuoteSnapshot,
    "option_definition": OptionDefinition,
    "option_quote_snapshot": OptionQuoteSnapshot,
    "rejected_record": RejectedRecord,
}


def json_schema_for(model: type[BaseModel]) -> dict[str, Any]:
    """Derive a stable JSON Schema document from a typed contract model.

    Args:
        model: A contract Pydantic model class.

    Returns:
        A JSON-Schema-compatible dictionary with a stable ``$id`` and title.
    """
    schema = model.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"neuralmarket:contract:{model.__name__}:{SCHEMA_VERSION}"
    schema["x-schema-version"] = SCHEMA_VERSION
    return schema
