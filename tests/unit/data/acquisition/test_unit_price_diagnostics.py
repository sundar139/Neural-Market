"""Sanitized unit-price failure-diagnostic tests: redaction, bounds, fingerprint."""

from __future__ import annotations

import json
from typing import Any

import pytest

from neuralmarket.data.acquisition.metadata_runner import (
    process_unit_price_response,
    run_isolated_unit_price_request,
)
from neuralmarket.data.acquisition.unit_price_diagnostics import (
    DIAGNOSTIC_SCHEMA_VERSION,
    MAX_MAPPING_KEYS,
    MAX_SEQUENCE_ITEMS,
    UnitPriceFailureCode,
    UnitPriceFailureDiagnostic,
    UnitPriceFailureStage,
    classify_sanitization_code,
    structural_fingerprint,
    summarize_response_shape,
)

pytestmark = pytest.mark.unit

FEED_MODE = "historical-streaming"
CBBO = "cbbo-1m"

# Distinctive values that must never leak into any diagnostic output.
SECRET_NUMBERS = [987654.321987, 0.000000123456, -7654321]
SECRET_STRINGS = [
    "FAKE_API_KEY_SHOULD_NOT_APPEAR",
    "Bearer FAKE_AUTHORIZATION",
    "ACCOUNT_IDENTIFIER_SHOULD_NOT_APPEAR",
]

_PARSE_KW = {
    "dataset": "OPRA.PILLAR",
    "client_version": "0.81.0",
    "retrieved_at_utc": "2026-07-15T02:00:00+00:00",
    "expires_at_utc": "2026-07-16T02:00:00+00:00",
}


@pytest.fixture(autouse=True)
def _forbid_real_databento(monkeypatch: pytest.MonkeyPatch) -> None:
    import databento

    def _boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("real Databento client construction attempted in an offline test")

    monkeypatch.setattr(databento, "Historical", _boom)


def _fail(raw: object) -> UnitPriceFailureDiagnostic:
    kind, payload = process_unit_price_response(raw, **_PARSE_KW)
    assert kind == "failure", payload
    return UnitPriceFailureDiagnostic.model_validate(payload)


# --- Redaction ---------------------------------------------------------------


def test_prices_and_secrets_never_appear_in_diagnostics() -> None:
    raw = [
        {
            FEED_MODE: {
                CBBO: SECRET_NUMBERS[0],
                "trades": SECRET_STRINGS[0],
            },
            "historical": {"definition": SECRET_NUMBERS[1], "x": SECRET_STRINGS[1]},
        },
        {"live": {"y": SECRET_NUMBERS[2], "z": SECRET_STRINGS[2]}},
    ]
    summary = summarize_response_shape(raw)
    blob = json.dumps(summary) + json.dumps(_fail(raw).model_dump(mode="json"))
    for marker in SECRET_STRINGS:
        assert marker not in blob
    for number in SECRET_NUMBERS:
        assert str(number) not in blob
        assert repr(number) not in blob
    # Mode/schema key names ARE preserved as structural signal.
    assert FEED_MODE in blob
    assert CBBO in blob


def test_summary_contains_only_types_and_keys() -> None:
    summary = summarize_response_shape([{FEED_MODE: {CBBO: 2.0, "trades": 1.0}}])
    node = summary["items"][0]["value"]["children"][0]["value"]
    assert node["type"] == "mapping"
    assert set(node["children"][0]) == {"key", "value"}
    assert node["children"][0]["value"]["type"] == "number"  # type only, not 2.0


def test_repr_is_never_invoked() -> None:
    class Boom:
        def __repr__(self) -> str:
            raise RuntimeError("repr must not be called")

    raw = [{FEED_MODE: {CBBO: Boom()}}]
    summary = summarize_response_shape(raw)  # must not raise (no repr call)
    text = json.dumps(summary)
    assert "object" in text  # Boom categorized by type only
    assert "repr must not be called" not in text


# --- Bounds and cycles -------------------------------------------------------


def test_recursive_structure_is_truncated_safely() -> None:
    node: dict[str, Any] = {}
    node["self"] = node
    summary = summarize_response_shape(node)  # must terminate
    assert json.dumps(summary)  # serializable


def test_breadth_truncation_flags() -> None:
    wide_map = {f"k{i}": {} for i in range(MAX_MAPPING_KEYS + 5)}
    summary = summarize_response_shape(wide_map)
    assert summary["truncated_keys"] is True
    assert len(summary["children"]) == MAX_MAPPING_KEYS
    wide_list = list(range(MAX_SEQUENCE_ITEMS + 5))
    lsummary = summarize_response_shape(wide_list)
    assert lsummary["truncated_items"] is True
    assert len(lsummary["items"]) == MAX_SEQUENCE_ITEMS


def test_depth_truncation() -> None:
    deep = {"a": {"b": {"c": {"d": {"e": 1}}}}}
    summary = summarize_response_shape(deep)
    text = json.dumps(summary)
    assert "truncated_depth" in text


# --- Structural fingerprint --------------------------------------------------


def test_fingerprint_ignores_prices() -> None:
    a = summarize_response_shape([{FEED_MODE: {CBBO: 2.0}}])
    b = summarize_response_shape([{FEED_MODE: {CBBO: 9999.99}}])
    assert structural_fingerprint(a) == structural_fingerprint(b)


def test_fingerprint_changes_with_key() -> None:
    a = summarize_response_shape([{FEED_MODE: {CBBO: 2.0}}])
    b = summarize_response_shape([{FEED_MODE: {"trades": 2.0}}])
    c = summarize_response_shape([{"historical": {CBBO: 2.0}}])
    assert structural_fingerprint(a) != structural_fingerprint(b)
    assert structural_fingerprint(a) != structural_fingerprint(c)


# --- Stage and code classification -------------------------------------------


def test_sanitization_stage_codes() -> None:
    assert _fail(5).failure_code is UnitPriceFailureCode.UNSUPPORTED_TOP_LEVEL_TYPE
    assert _fail([5]).failure_code is UnitPriceFailureCode.SEQUENCE_ITEM_NOT_MAPPING
    assert _fail([{FEED_MODE: "x"}]).failure_code is UnitPriceFailureCode.SCHEMAS_NOT_MAPPING
    assert _fail([{FEED_MODE: {}}]).failure_code is UnitPriceFailureCode.SCHEMAS_EMPTY
    assert _fail([{"": {CBBO: 2.0}}]).failure_code is UnitPriceFailureCode.EMPTY_MODE_NAME
    for diag in (_fail(5), _fail([5]), _fail([{FEED_MODE: {}}])):
        assert diag.failure_stage is UnitPriceFailureStage.SANITIZATION


def test_malformed_sibling_fails_closed_and_is_diagnosable() -> None:
    raw = [{FEED_MODE: {CBBO: 2.0}}, {"historical": {}}]
    diag = _fail(raw)
    assert diag.failure_stage is UnitPriceFailureStage.SANITIZATION
    assert diag.failure_code is UnitPriceFailureCode.SCHEMAS_EMPTY
    text = json.dumps(diag.model_dump(mode="json"))
    assert FEED_MODE in text and CBBO in text and "historical" in text
    assert "2.0" not in text


def test_target_mode_missing() -> None:
    diag = _fail([{"historical": {CBBO: 2.0}}])
    assert diag.failure_stage is UnitPriceFailureStage.SNAPSHOT_PARSING
    assert diag.failure_code is UnitPriceFailureCode.TARGET_MODE_MISSING


def test_target_mode_duplicate() -> None:
    diag = _fail([{FEED_MODE: {CBBO: 2.0}}, {FEED_MODE: {CBBO: 3.0}}])
    assert diag.failure_code is UnitPriceFailureCode.TARGET_MODE_DUPLICATE


def test_target_schema_missing() -> None:
    diag = _fail([{FEED_MODE: {"trades": "bad"}}])
    assert diag.failure_code is UnitPriceFailureCode.TARGET_SCHEMA_MISSING


def test_invalid_target_price_hides_value() -> None:
    diag = _fail([{FEED_MODE: {CBBO: "-987654.321"}}])
    assert diag.failure_code is UnitPriceFailureCode.TARGET_PRICE_INVALID
    assert "987654.321" not in json.dumps(diag.model_dump(mode="json"))


def test_reserved_codes_reachable_via_classifier() -> None:
    assert classify_sanitization_code({}) is UnitPriceFailureCode.EMPTY_TOP_LEVEL_MAPPING


def test_diagnostic_is_versioned_and_serializable() -> None:
    diag = _fail([{"historical": {CBBO: 2.0}}])
    dumped = diag.model_dump(mode="json")
    assert dumped["diagnostic_schema_version"] == DIAGNOSTIC_SCHEMA_VERSION
    assert UnitPriceFailureDiagnostic.model_validate(dumped) == diag


# --- Child integration -------------------------------------------------------


def _diag_success_worker(output, dataset, client_version, retrieved_at_utc, expires_at_utc) -> None:
    from neuralmarket.data.acquisition.metadata_runner import process_unit_price_response

    output.put(
        process_unit_price_response(
            [{"historical-streaming": {"cbbo-1m": 2.0}}],
            dataset=dataset,
            client_version=client_version,
            retrieved_at_utc=retrieved_at_utc,
            expires_at_utc=expires_at_utc,
        )
    )


def _diag_failure_worker(output, dataset, client_version, retrieved_at_utc, expires_at_utc) -> None:
    from neuralmarket.data.acquisition.metadata_runner import process_unit_price_response

    output.put(
        process_unit_price_response(
            [{"historical": {"cbbo-1m": 2.0}}],
            dataset=dataset,
            client_version=client_version,
            retrieved_at_utc=retrieved_at_utc,
            expires_at_utc=expires_at_utc,
        )
    )


def _diag_timeout_worker(output, *_args) -> None:
    import time

    time.sleep(60)


def _run(worker, timeout: float = 10.0):
    return run_isolated_unit_price_request(
        dataset="OPRA.PILLAR",
        client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
        timeout_seconds=timeout,
        worker=worker,
    )


def test_child_success() -> None:
    result = _run(_diag_success_worker)
    assert result.snapshot is not None
    assert result.diagnostic is None
    assert result.child_joined is True
    assert result.child_terminated is False
    assert result.child_exit_code == 0
    assert result.remaining_children == 0


def test_child_handled_failure_reports_diagnostic_with_exit_zero() -> None:
    result = _run(_diag_failure_worker)
    assert result.snapshot is None
    assert result.diagnostic is not None
    assert result.diagnostic.failure_stage is UnitPriceFailureStage.SNAPSHOT_PARSING
    assert result.diagnostic.failure_code is UnitPriceFailureCode.TARGET_MODE_MISSING
    assert result.diagnostic.response_shape_fingerprint
    assert result.child_joined is True
    assert result.child_terminated is False
    assert result.child_exit_code == 0
    assert result.remaining_children == 0


def test_child_timeout() -> None:
    result = _run(_diag_timeout_worker, timeout=3.0)
    assert result.snapshot is None
    assert result.failure_type == "unit_price_hard_timeout"
    assert result.diagnostic is not None
    assert result.diagnostic.failure_stage is UnitPriceFailureStage.CHILD_TIMEOUT
    assert result.child_terminated is True
    assert result.remaining_children == 0
