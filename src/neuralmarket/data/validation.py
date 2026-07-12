"""Record- and table-level validation against canonical contracts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from neuralmarket.data.contracts import (
    OptionDefinition,
    OptionQuoteSnapshot,
    UnderlyingDailyBar,
)
from neuralmarket.data.errors import ContractValidationError

TModel = TypeVar("TModel", bound=BaseModel)

# Primary keys used to detect duplicates in normalized tables.
DUPLICATE_KEYS: dict[type[BaseModel], tuple[str, ...]] = {
    UnderlyingDailyBar: ("symbol", "session_date"),
    OptionDefinition: ("instrument_id", "definition_timestamp"),
    OptionQuoteSnapshot: ("instrument_id", "session_date"),
}


def validate_record(model: type[TModel], payload: dict[str, Any]) -> TModel:
    """Validate a single payload against a contract model.

    Args:
        model: A canonical contract model class.
        payload: A mapping of field values.

    Returns:
        The validated model instance.

    Raises:
        ContractValidationError: If the payload violates the contract.
    """
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ContractValidationError(f"{model.__name__} validation failed: {exc}") from exc


def validate_records(
    model: type[TModel], payloads: Iterable[dict[str, Any]]
) -> tuple[list[TModel], list[tuple[int, ContractValidationError]]]:
    """Validate many payloads, separating valid rows from rejected ones.

    Args:
        model: A canonical contract model class.
        payloads: Payload mappings.

    Returns:
        A tuple of (valid models, list of (index, error) for rejected payloads).
    """
    valid: list[TModel] = []
    rejected: list[tuple[int, ContractValidationError]] = []
    for index, payload in enumerate(payloads):
        try:
            valid.append(validate_record(model, payload))
        except ContractValidationError as exc:
            rejected.append((index, exc))
    return valid, rejected


def _key_of(row: BaseModel, key_fields: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(getattr(row, field) for field in key_fields)


def duplicate_keys(rows: Sequence[BaseModel]) -> list[tuple[Any, ...]]:
    """Return duplicate primary keys present in a homogeneous row sequence.

    Args:
        rows: Validated contract rows of a single model type.

    Returns:
        The duplicated key tuples, if any.

    Raises:
        ContractValidationError: If the model type has no configured primary key.
    """
    if not rows:
        return []
    model_type = type(rows[0])
    key_fields = DUPLICATE_KEYS.get(model_type)
    if key_fields is None:
        raise ContractValidationError(f"No duplicate key configured for {model_type.__name__}")
    counts = Counter(_key_of(row, key_fields) for row in rows)
    return [key for key, count in counts.items() if count > 1]


def ensure_unique(rows: Sequence[BaseModel]) -> None:
    """Raise if a normalized table contains duplicate primary keys.

    Args:
        rows: Validated contract rows of a single model type.

    Raises:
        ContractValidationError: If any duplicate primary key is found.
    """
    dupes = duplicate_keys(rows)
    if dupes:
        raise ContractValidationError(f"Duplicate primary keys detected: {dupes}")


def ensure_quote_matches_definition(
    quote: OptionQuoteSnapshot, definition: OptionDefinition
) -> None:
    """Raise if a quote's contract terms disagree with its point-in-time definition.

    Args:
        quote: A validated option quote snapshot.
        definition: The associated point-in-time option definition.

    Raises:
        ContractValidationError: If contract terms do not agree.
    """
    if not quote.agrees_with_definition(definition):
        raise ContractValidationError(
            "Quote contract terms do not match the point-in-time definition."
        )
