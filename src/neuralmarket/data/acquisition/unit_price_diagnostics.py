"""Sanitized, bounded structural diagnostics for unit-price parsing failures.

A failed ``list_unit_prices`` probe must be diagnosable from one authorized live
call without ever exposing prices, credentials, account identifiers, raw
responses, or arbitrary object representations. This module builds a typed,
versioned diagnostic that carries only the *structure* of the response — types,
key names, lengths, and truncation flags — plus a deterministic fingerprint of
that structure.

Parser acceptance/rejection is unchanged: the classification helpers here mirror
the sanitizer/parser rules structurally to name a stable failure code; they do
not decide whether a response succeeds.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

DIAGNOSTIC_SCHEMA_VERSION = "unit-price-diagnostic-v1"

# Structural-summary bounds (constants, never scattered literals).
MAX_SEQUENCE_ITEMS = 16
MAX_MAPPING_KEYS = 32
MAX_DEPTH = 3
MAX_KEY_LENGTH = 128
MAX_DIAGNOSTIC_BYTES = 32 * 1024


class UnitPriceFailureStage(str, Enum):
    """Pipeline stage at which a unit-price probe failed."""

    PROVIDER_CALL = "provider_call"
    RESPONSE_SUMMARIZATION = "response_summarization"
    SANITIZATION = "sanitization"
    SNAPSHOT_PARSING = "snapshot_parsing"
    SNAPSHOT_VALIDATION = "snapshot_validation"
    CHILD_TRANSPORT = "child_transport"
    CHILD_TIMEOUT = "child_timeout"


class UnitPriceFailureCode(str, Enum):
    """Stable machine-readable failure reasons.

    Some values are reserved for validation boundaries that cannot currently be
    reached by the production flow (dataset/client-version/hash/schema binding
    never fails independently today); they exist so the vocabulary is stable as
    the parser evolves and are never emitted unless actually reachable.
    """

    PROVIDER_ERROR = "provider_error"
    UNSUPPORTED_TOP_LEVEL_TYPE = "unsupported_top_level_type"
    EMPTY_TOP_LEVEL_MAPPING = "empty_top_level_mapping"
    EMPTY_TOP_LEVEL_SEQUENCE = "empty_top_level_sequence"
    SEQUENCE_ITEM_NOT_MAPPING = "sequence_item_not_mapping"
    INVALID_CANONICAL_BLOCK = "invalid_canonical_block"
    EMPTY_MODE_NAME = "empty_mode_name"
    SCHEMAS_NOT_MAPPING = "schemas_not_mapping"
    SCHEMAS_EMPTY = "schemas_empty"
    UNSUPPORTED_MAPPING_ENTRY = "unsupported_mapping_entry"
    MIXED_RESPONSE_FORMS = "mixed_response_forms"
    TARGET_MODE_MISSING = "target_mode_missing"
    TARGET_MODE_DUPLICATE = "target_mode_duplicate"
    TARGET_SCHEMA_MISSING = "target_schema_missing"
    TARGET_PRICE_INVALID = "target_price_invalid"
    DATASET_BINDING_FAILED = "dataset_binding_failed"
    CLIENT_VERSION_BINDING_FAILED = "client_version_binding_failed"
    SNAPSHOT_HASH_FAILED = "snapshot_hash_failed"
    SNAPSHOT_SCHEMA_FAILED = "snapshot_schema_failed"
    CHILD_NO_RESULT = "child_no_result"
    CHILD_TIMEOUT = "child_timeout"
    UNEXPECTED_INTERNAL_ERROR = "unexpected_internal_error"


class UnitPriceFailureDiagnostic(BaseModel):
    """A sanitized, versioned diagnostic for one unit-price failure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    diagnostic_schema_version: str = DIAGNOSTIC_SCHEMA_VERSION
    failure_stage: UnitPriceFailureStage
    failure_code: UnitPriceFailureCode
    failure_type: str | None = None
    safe_message: str
    response_shape_summary: dict[str, Any] | None = None
    response_shape_fingerprint: str | None = None


# --- Structural summary (price-free, bounded) --------------------------------


def _type_name(value: object) -> str:
    """Categorize a value by type only — never its content, never ``repr``."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, Mapping):
        return "mapping"
    if isinstance(value, list | tuple):
        return "sequence"
    return "object"


def _safe_key(key: object) -> str:
    """Return a bounded string form of a structural key name."""
    try:
        text = key if isinstance(key, str) else _type_name(key)
    except Exception:
        return "<unrenderable-key>"
    if len(text) > MAX_KEY_LENGTH:
        return text[:MAX_KEY_LENGTH] + "…"
    return text


def _summarize_node(value: object, depth: int, seen: frozenset[int]) -> dict[str, Any]:
    node: dict[str, Any] = {"type": _type_name(value)}
    if depth >= MAX_DEPTH:
        node["truncated_depth"] = True
        return node
    if isinstance(value, Mapping | list | tuple):
        identity = id(value)
        if identity in seen:
            node["truncated_cycle"] = True
            return node
        seen = seen | {identity}
    if isinstance(value, Mapping):
        keys = list(value.keys())
        node["length"] = len(keys)
        shown = keys[:MAX_MAPPING_KEYS]
        if len(keys) > MAX_MAPPING_KEYS:
            node["truncated_keys"] = True
        node["children"] = [
            {"key": _safe_key(key), "value": _summarize_node(value[key], depth + 1, seen)}
            for key in shown
        ]
    elif isinstance(value, list | tuple):
        node["length"] = len(value)
        shown = list(value)[:MAX_SEQUENCE_ITEMS]
        if len(value) > MAX_SEQUENCE_ITEMS:
            node["truncated_items"] = True
        node["items"] = [
            {"index": index, "value": _summarize_node(item, depth + 1, seen)}
            for index, item in enumerate(shown)
        ]
    # Scalars (null/bool/number/string/object) contribute their type only.
    return node


def summarize_response_shape(raw: object) -> dict[str, Any]:
    """Return a bounded, price-free structural summary of a raw response."""
    try:
        summary = _summarize_node(raw, 0, frozenset())
    except Exception:
        return {"type": "object", "truncated_error": True}
    encoded = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_DIAGNOSTIC_BYTES:
        return {"type": summary.get("type", "object"), "truncated_size": True}
    return summary


def structural_fingerprint(summary: Mapping[str, Any]) -> str:
    """SHA-256 over the canonical structural summary (no values, no prices)."""
    encoded = json.dumps(summary, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --- Structural failure classification (mirrors sanitizer/parser rules) -------


def _mode_issue(mode: object, schemas: object) -> UnitPriceFailureCode | None:
    if not isinstance(mode, str) or not mode.strip():
        return UnitPriceFailureCode.EMPTY_MODE_NAME
    if not isinstance(schemas, Mapping):
        return UnitPriceFailureCode.SCHEMAS_NOT_MAPPING
    if not schemas:
        return UnitPriceFailureCode.SCHEMAS_EMPTY
    return None


def _list_item_code(item: Mapping[Any, Any]) -> UnitPriceFailureCode | None:
    """Mirror ``_sanitize_list_item`` to name the failure of one list item."""
    has_mode = "mode" in item
    has_schemas = "schemas" in item
    has_unit_prices = "unit_prices" in item
    if has_mode and has_schemas and has_unit_prices:
        return UnitPriceFailureCode.MIXED_RESPONSE_FORMS
    if has_mode and (has_schemas or has_unit_prices):
        wrapper = "schemas" if has_schemas else "unit_prices"
        if set(item.keys()) - {"mode", wrapper}:
            return UnitPriceFailureCode.UNSUPPORTED_MAPPING_ENTRY
        return _mode_issue(item["mode"], item[wrapper])
    if has_mode or has_unit_prices:
        return UnitPriceFailureCode.INVALID_CANONICAL_BLOCK
    for mode, schemas in item.items():
        code = _mode_issue(mode, schemas)
        if code is not None:
            return code
    return None


def classify_sanitization_code(raw: object) -> UnitPriceFailureCode:
    """Name the first structural reason a raw response fails sanitization."""
    if isinstance(raw, Mapping):
        if not raw:
            return UnitPriceFailureCode.EMPTY_TOP_LEVEL_MAPPING
        for mode, schemas in raw.items():
            code = _mode_issue(mode, schemas)
            if code is not None:
                return code
        return UnitPriceFailureCode.UNEXPECTED_INTERNAL_ERROR
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                return UnitPriceFailureCode.SEQUENCE_ITEM_NOT_MAPPING
            code = _list_item_code(item)
            if code is not None:
                return code
        return UnitPriceFailureCode.UNEXPECTED_INTERNAL_ERROR
    return UnitPriceFailureCode.UNSUPPORTED_TOP_LEVEL_TYPE


def classify_parsing_code(
    blocks: Sequence[Mapping[str, Any]], *, feed_mode: str, schema: str
) -> UnitPriceFailureCode:
    """Name the failure reason when sanitized blocks fail snapshot parsing."""
    matching = [block for block in blocks if block.get("mode") == feed_mode]
    if not matching:
        return UnitPriceFailureCode.TARGET_MODE_MISSING
    if len(matching) > 1:
        return UnitPriceFailureCode.TARGET_MODE_DUPLICATE
    schemas = matching[0].get("schemas")
    if isinstance(schemas, Mapping) and schema not in schemas:
        return UnitPriceFailureCode.TARGET_SCHEMA_MISSING
    # A single matching block that still fails parsing means a price in it was
    # rejected downstream; the invalid value is never captured.
    return UnitPriceFailureCode.TARGET_PRICE_INVALID


# --- Diagnostic builders -----------------------------------------------------


def _safe_message(
    stage: UnitPriceFailureStage,
    code: UnitPriceFailureCode,
    *,
    dataset: str,
    feed_mode: str,
    schema: str,
) -> str:
    return (
        f"unit-price {stage.value} failed ({code.value}) for "
        f"dataset={dataset} mode={feed_mode} schema={schema}"
    )


def build_diagnostic(
    *,
    stage: UnitPriceFailureStage,
    code: UnitPriceFailureCode,
    dataset: str,
    feed_mode: str,
    schema: str,
    failure_type: str | None = None,
    summary: dict[str, Any] | None = None,
    fingerprint: str | None = None,
) -> UnitPriceFailureDiagnostic:
    """Assemble a sanitized diagnostic from fixed internal text and structure."""
    return UnitPriceFailureDiagnostic(
        failure_stage=stage,
        failure_code=code,
        failure_type=failure_type,
        safe_message=_safe_message(
            stage, code, dataset=dataset, feed_mode=feed_mode, schema=schema
        ),
        response_shape_summary=summary,
        response_shape_fingerprint=fingerprint,
    )
