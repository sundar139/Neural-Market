from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

import neuralmarket.data.sources.databento as databento_source
from neuralmarket.data.configuration import load_data_config
from neuralmarket.data.errors import (
    AuthenticationError,
    CredentialMissingError,
    DatasetUnavailableError,
    DownloadProhibitedError,
    EntitlementError,
    ProviderNetworkError,
    RateLimitError,
    SchemaUnavailableError,
    SymbolResolutionError,
)
from neuralmarket.data.sources.base import QualificationStatus, StageStatus
from neuralmarket.data.sources.databento import DatabentoSource, _translate

_CONFIG = load_data_config(Path("configs/data/spy_daily_databento.yaml"))

_FULL = {"start": "2013-04-01", "end": "2026-07-11"}
_SCHEMAS = {
    "ARCX.PILLAR": ["definition", "ohlcv-1d", "bbo-1m", "statistics", "trades"],
    "OPRA.PILLAR": ["definition", "cbbo-1m", "mbp-1"],
}
_PUBLISHERS = [
    {
        "dataset": "ARCX.PILLAR",
        "publisher_id": 2,
        "venue": "ARCX",
        "description": "NYSE Arca Pillar",
    },
    {"dataset": "OPRA.PILLAR", "publisher_id": 9, "venue": "OPRA", "description": "OPRA"},
]


def _iso(value: str) -> date:
    return date.fromisoformat(value)


# --- Parent-expansion response builders (result keyed by child symbols) --------
ParentBuilder = Callable[[date, date], dict[str, Any]]


def _healthy_parent(start: date, end: date) -> dict[str, Any]:
    """One child spanning the whole chunk: every session has an active contract."""
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": ["SPY   250101C00500000"],
        "not_found": [],
        "result": {
            "SPY   250101C00500000": [{"d0": start.isoformat(), "d1": end.isoformat(), "s": "100"}]
        },
    }


def _rotating_ids_parent(start: date, end: date) -> dict[str, Any]:
    """Two adjacent intervals with distinct instrument ids; full coverage."""
    mid = start + timedelta(days=(end - start).days // 2)
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": [],
        "not_found": [],
        "result": {
            "SPY   250101C00500000": [
                {"d0": start.isoformat(), "d1": mid.isoformat(), "s": "1"},
                {"d0": mid.isoformat(), "d1": end.isoformat(), "s": "2"},
            ]
        },
    }


def _spanning_parent(start: date, end: date) -> dict[str, Any]:
    """One child whose true mapping dates extend past both chunk boundaries.

    The provider returns a contract's real listing/expiry dates, which can span
    the requested window; the resolver must clamp rather than reject.
    """
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": [],
        "not_found": [],
        "result": {
            "SPY   250101C00500000": [
                {
                    "d0": (start - timedelta(days=15)).isoformat(),
                    "d1": (end + timedelta(days=15)).isoformat(),
                    "s": "1",
                }
            ]
        },
    }


def _overlapping_parent(start: date, end: date) -> dict[str, Any]:
    """Two overlapping intervals for one child; still full coverage."""
    mid = start + timedelta(days=(end - start).days // 2)
    overlap = mid - timedelta(days=1)
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": [],
        "not_found": [],
        "result": {
            "SPY   250101C00500000": [
                {"d0": start.isoformat(), "d1": mid.isoformat(), "s": "1"},
                {"d0": overlap.isoformat(), "d1": end.isoformat(), "s": "2"},
            ]
        },
    }


def _uncovered_parent(start: date, end: date) -> dict[str, Any]:
    """Coverage only for the first calendar day; later sessions are uncovered."""
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": [],
        "not_found": [],
        "result": {
            "SPY   250101C00500000": [
                {"d0": start.isoformat(), "d1": (start + timedelta(days=1)).isoformat(), "s": "1"}
            ]
        },
    }


def _foreign_parent(start: date, end: date) -> dict[str, Any]:
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": [],
        "not_found": [],
        "result": {
            "AAPL  250101C00500000": [{"d0": start.isoformat(), "d1": end.isoformat(), "s": "1"}]
        },
    }


def _not_found_parent(start: date, end: date) -> dict[str, Any]:
    return {
        "status": 1,
        "message": "Partially resolved",
        "partial": [],
        "not_found": ["SPY.OPT"],
        "result": {
            "SPY   250101C00500000": [{"d0": start.isoformat(), "d1": end.isoformat(), "s": "1"}]
        },
    }


def _empty_parent(start: date, end: date) -> dict[str, Any]:
    return {"status": 1, "message": "OK", "partial": [], "not_found": [], "result": {}}


def _status_two_parent(start: date, end: date) -> dict[str, Any]:
    return {"status": 2, "message": "Not found", "partial": [], "not_found": [], "result": {}}


def _malformed_parent(start: date, end: date) -> dict[str, Any]:
    return {"status": 1, "message": "OK", "partial": [], "not_found": [], "result": "nope"}


class _FakeBentoError(Exception):
    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


def _unsupported_parent(start: date, end: date) -> dict[str, Any]:
    raise _FakeBentoError(
        422,
        "422 symbology_invalid_request\nUnable to process symbology with parameters: "
        "stype_in=parent, stype_out=instrument_id. Unsupported combination for this dataset.",
    )


def _always_server_error(start: date, end: date) -> dict[str, Any]:
    raise _FakeBentoError(500, "500 internal_error transient server failure")


class _FlakyParent:
    """Raises a transient 5xx on the first ``fails`` calls, then resolves cleanly."""

    def __init__(self, fails: int) -> None:
        self.fails = fails
        self.calls = 0

    def __call__(self, start: date, end: date) -> dict[str, Any]:
        self.calls += 1
        if self.calls <= self.fails:
            raise _FakeBentoError(500, "500 internal_error transient server failure")
        return _healthy_parent(start, end)


class _Metadata:
    def __init__(
        self,
        ranges: dict[str, Any],
        schemas: dict[str, list[str]],
        error: str | None,
        publishers: list[dict[str, Any]],
    ):
        self._ranges = ranges
        self._schemas = schemas
        self._error = error
        self._publishers = publishers
        self.cost_calls: list[dict[str, Any]] = []

    def get_dataset_range(self, dataset: str) -> dict[str, str]:
        if self._error:
            raise RuntimeError(self._error)
        return self._ranges[dataset]

    def list_schemas(self, dataset: str) -> list[str]:
        return self._schemas[dataset]

    def list_publishers(self) -> list[dict[str, Any]]:
        return self._publishers

    def get_cost(self, **kwargs: Any) -> float:
        self.cost_calls.append(kwargs)
        return 2.5

    def get_billable_size(self, **kwargs: Any) -> int:
        return 1024

    def get_record_count(self, **kwargs: Any) -> int:
        return 42


class _Symbology:
    def __init__(
        self,
        not_found: set[str],
        mappings: dict[str, list[dict[str, str]]] | None,
        response: dict[str, Any] | None,
        parent_builder: ParentBuilder,
    ):
        self._not_found = not_found
        self._mappings = mappings
        self._response = response
        self._parent_builder = parent_builder
        self.calls: list[dict[str, Any]] = []

    def resolve(self, *, symbols: list[str], **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"symbols": symbols, **kwargs})
        if kwargs.get("stype_in") == "parent":
            return self._parent_builder(_iso(kwargs["start_date"]), _iso(kwargs["end_date"]))
        if self._response is not None:
            return self._response
        mappings = self._mappings or {
            s: [{"d0": "2018-05-01", "d1": "2026-01-01", "s": "1"}]
            for s in symbols
            if s not in self._not_found
        }
        return {
            "result": mappings,
            "status": 0,
            "partial": [],
            "not_found": sorted(self._not_found),
        }


class _FakeClient:
    def __init__(
        self,
        ranges: dict[str, Any] | None = None,
        schemas: dict[str, list[str]] | None = None,
        error: str | None = None,
        not_found: set[str] | None = None,
        publishers: list[dict[str, Any]] | None = None,
        mappings: dict[str, list[dict[str, str]]] | None = None,
        symbology_response: dict[str, Any] | None = None,
        parent_builder: ParentBuilder = _healthy_parent,
    ):
        rng = ranges or {"ARCX.PILLAR": _FULL, "OPRA.PILLAR": _FULL}
        pubs = _PUBLISHERS if publishers is None else publishers
        self.metadata = _Metadata(rng, schemas or _SCHEMAS, error, pubs)
        self.symbology = _Symbology(
            not_found or set(), mappings, symbology_response, parent_builder
        )
        self.timeseries = object()
        self.batch = object()
        self.live = object()


@pytest.mark.unit
def test_download_namespaces_blocked() -> None:
    source = DatabentoSource(_FakeClient())
    for name in ("timeseries", "batch", "live"):
        with pytest.raises(DownloadProhibitedError):
            getattr(source._client, name)


@pytest.mark.unit
def test_qualify_happy_path() -> None:
    result = DatabentoSource(_FakeClient()).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    assert result.entitlement_ok is True
    assert result.downloads_attempted == 0
    assert not result.blocking_failures
    assert all(s is StageStatus.PASSED for s in result.stages.values())
    assert len(result.coverage_results) == 5
    assert all(c.covers_complete_window for c in result.coverage_results)
    assert len(result.cost_estimates) == 18
    assert all(c.cost == 2.5 and c.currency == "USD" and c.exact for c in result.cost_estimates)
    assert all(r.resolved for r in result.symbol_resolutions)
    assert result.underlying_publisher is not None
    assert result.underlying_publisher.venue == "ARCX"
    assert result.optional_schemas["statistics"] == "available"
    assert result.downloaded_records == 0


@pytest.mark.unit
def test_parent_selector_qualifies_with_full_session_coverage() -> None:
    result = DatabentoSource(_FakeClient()).qualify_source(_CONFIG)
    sel = result.parent_selector
    assert sel is not None
    assert sel.validation_method == "chunked_symbology_resolution"
    assert sel.resolved is True
    assert sel.chunk_count == 92
    assert sel.successful_chunk_count == 92
    assert sel.failed_chunk_count == 0
    assert sel.session_gap_count == 0
    assert sel.first_valid_date == date(2018, 5, 1)
    assert sel.end_exclusive == date(2026, 1, 1)
    # Chunks are contiguous, half-open, and gapless.
    for previous, following in zip(sel.chunks, sel.chunks[1:], strict=False):
        assert previous.chunk.end_exclusive == following.chunk.start
    assert sel.chunks[0].chunk.start == date(2018, 5, 1)
    assert sel.chunks[-1].chunk.end_exclusive == date(2026, 1, 1)


@pytest.mark.unit
def test_parent_status_one_is_accepted_for_expansion() -> None:
    result = DatabentoSource(_FakeClient()).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    assert all(c.status == 1 for c in result.parent_selector.chunks)  # type: ignore[union-attr]


@pytest.mark.unit
def test_parent_changing_instrument_ids_accepted() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_rotating_ids_parent)).qualify_source(
        _CONFIG
    )
    assert result.status is QualificationStatus.QUALIFIED
    sel = result.parent_selector
    assert sel is not None
    assert all(c.distinct_instrument_id_count == 2 for c in sel.chunks)
    assert all(c.overlapping_child_count == 0 for c in sel.chunks)


@pytest.mark.unit
def test_parent_overlapping_child_intervals_are_diagnostic_only() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_overlapping_parent)).qualify_source(
        _CONFIG
    )
    assert result.status is QualificationStatus.QUALIFIED
    assert all(c.overlapping_child_count == 1 for c in result.parent_selector.chunks)  # type: ignore[union-attr]


@pytest.mark.unit
def test_parent_boundary_spanning_intervals_are_clamped() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_spanning_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    sel = result.parent_selector
    assert sel is not None and sel.resolved is True
    # Spanning both boundaries means the child is neither listing nor expiring.
    assert all(c.listing_mid_chunk_count == 0 for c in sel.chunks)
    assert all(c.expiring_mid_chunk_count == 0 for c in sel.chunks)


@pytest.mark.unit
def test_parent_uncovered_session_fails_symbology() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_uncovered_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.stages["D_symbology"] is StageStatus.FAILED
    assert result.stages["E_cost"] is StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE
    sel = result.parent_selector
    assert sel is not None and sel.resolved is False
    assert sel.chunks[-1].failure_reason == "uncovered_sessions"


@pytest.mark.unit
def test_parent_foreign_underlying_fails() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_foreign_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.parent_selector.chunks[-1].failure_reason == "foreign_underlying"  # type: ignore[union-attr]


@pytest.mark.unit
def test_parent_not_found_fails() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_not_found_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.parent_selector.chunks[-1].failure_reason == "not_found"  # type: ignore[union-attr]


@pytest.mark.unit
def test_parent_empty_month_fails() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_empty_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.parent_selector.chunks[-1].failure_reason == "empty_mappings"  # type: ignore[union-attr]


@pytest.mark.unit
def test_parent_status_two_fails() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_status_two_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.parent_selector.chunks[-1].failure_reason == "status_not_found"  # type: ignore[union-attr]


@pytest.mark.unit
def test_parent_malformed_result_fails_internal_validation() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_malformed_parent)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_INTERNAL_VALIDATION
    assert result.stages["D_symbology"] is StageStatus.FAILED


@pytest.mark.unit
def test_parent_unsupported_combination_fails_symbology_with_diagnostic() -> None:
    result = DatabentoSource(_FakeClient(parent_builder=_unsupported_parent)).qualify_source(
        _CONFIG
    )
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.provider_diagnostics
    diag = result.provider_diagnostics[-1]
    assert diag.failure_category == "unsupported_symbology_combination"
    assert diag.http_status_code == 422
    assert diag.provider_error_code == "symbology_invalid_request"
    assert "[REDACTED]" not in diag.safe_provider_message  # nothing secret to redact
    assert diag.operation == "parent_symbology_resolution"


@pytest.mark.unit
def test_parent_transient_server_error_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(databento_source.time, "sleep", lambda _seconds: None)
    result = DatabentoSource(_FakeClient(parent_builder=_FlakyParent(2))).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    assert not result.provider_diagnostics


@pytest.mark.unit
def test_parent_persistent_server_error_fails_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(databento_source.time, "sleep", lambda _seconds: None)
    result = DatabentoSource(_FakeClient(parent_builder=_always_server_error)).qualify_source(
        _CONFIG
    )
    assert result.status is QualificationStatus.FAILED_NETWORK
    assert result.provider_diagnostics[-1].failure_category == "provider_server_error"


@pytest.mark.unit
def test_wrong_arcx_publisher_fails() -> None:
    only_venue = [
        {"dataset": "ARCX.PILLAR", "publisher_id": 1, "venue": "XNAS", "description": "Nasdaq"},
    ]
    result = DatabentoSource(_FakeClient(publishers=only_venue)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_PUBLISHER
    assert result.stages["E_cost"] is StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE
    assert result.underlying_publisher is None


@pytest.mark.unit
def test_coverage_gap_stops_later_stages() -> None:
    ranges = {"ARCX.PILLAR": {"start": "2019-06-01", "end": "2026-01-01"}, "OPRA.PILLAR": _FULL}
    result = DatabentoSource(_FakeClient(ranges=ranges)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_COVERAGE
    assert result.stages["D_symbology"] is StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE
    assert result.stages["E_cost"] is StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE
    assert result.symbol_resolutions == []
    assert result.parent_selector is None
    assert result.cost_estimates == []


@pytest.mark.unit
def test_missing_schema_fails_before_coverage() -> None:
    schemas = {"ARCX.PILLAR": ["definition", "bbo-1m"], "OPRA.PILLAR": ["definition", "cbbo-1m"]}
    result = DatabentoSource(_FakeClient(schemas=schemas)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SCHEMA
    assert result.stages["C_coverage"] is StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE


@pytest.mark.unit
def test_underlying_symbol_not_found_fails_symbology() -> None:
    result = DatabentoSource(_FakeClient(not_found={"SPY"})).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.stages["C_coverage"] is StageStatus.PASSED
    assert result.stages["E_cost"] is StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE


@pytest.mark.unit
def test_missing_optional_statistics_warns_without_failing() -> None:
    schemas = {
        "ARCX.PILLAR": ["definition", "ohlcv-1d", "bbo-1m"],
        "OPRA.PILLAR": ["definition", "cbbo-1m"],
    }
    result = DatabentoSource(_FakeClient(schemas=schemas)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    assert result.optional_schemas["statistics"] == "unavailable"
    assert result.warnings
    assert len(result.cost_estimates) == 15


@pytest.mark.unit
def test_underlying_mapping_gap_fails() -> None:
    mappings = {
        "SPY": [
            {"d0": "2018-05-01", "d1": "2020-01-01", "s": "1"},
            {"d0": "2020-02-01", "d1": "2026-01-01", "s": "1"},
        ],
    }
    result = DatabentoSource(_FakeClient(mappings=mappings)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_INTERNAL_VALIDATION
    assert "gap" in result.blocking_failures[-1].lower()


@pytest.mark.unit
def test_underlying_half_open_end_and_changing_ids() -> None:
    mappings = {
        "SPY": [
            {"d0": "2018-05-01", "d1": "2020-01-01", "s": "1"},
            {"d0": "2020-01-01", "d1": "2026-01-01", "s": "2"},
        ],
    }
    client = _FakeClient(mappings=mappings)
    result = DatabentoSource(client).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    raw_calls = [c for c in client.symbology.calls if c.get("stype_in") == "raw_symbol"]
    assert all(call["end_date"] == "2026-01-01" for call in raw_calls)
    assert result.symbol_resolutions[0].distinct_output_count == 2
    assert not result.symbol_resolutions[0].uncovered_intervals


@pytest.mark.unit
def test_underlying_status_one_partial_fails_symbology() -> None:
    response = {
        "result": {"SPY": [{"d0": "2018-05-01", "d1": "2026-01-01", "s": "1"}]},
        "status": 1,
        "partial": ["SPY"],
        "not_found": [],
    }
    result = DatabentoSource(_FakeClient(symbology_response=response)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_SYMBOLOGY
    assert result.stages["D_symbology"] is StageStatus.FAILED


@pytest.mark.unit
def test_underlying_status_zero_is_accepted() -> None:
    # The successful ARCX status "0" (string) must qualify, not be rejected.
    response = {
        "result": {"SPY": [{"d0": "2018-05-01", "d1": "2026-01-01", "s": "1"}]},
        "status": "0",
        "message": "OK",
        "partial": [],
        "not_found": [],
    }
    result = DatabentoSource(_FakeClient(symbology_response=response)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    assert result.symbol_resolutions[0].resolved is True


@pytest.mark.unit
def test_underlying_malformed_status_fails_internal_validation() -> None:
    response = {
        "result": {"SPY": [{"d0": "2018-05-01", "d1": "2026-01-01", "s": "1"}]},
        "status": "OK",
        "partial": [],
        "not_found": [],
    }
    result = DatabentoSource(_FakeClient(symbology_response=response)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_INTERNAL_VALIDATION
    assert result.stages["D_symbology"] is StageStatus.FAILED


@pytest.mark.unit
@pytest.mark.parametrize(
    "entry",
    [
        {"d1": "2026-01-01", "s": "1"},
        {"d0": "2018-05-01", "s": "1"},
        {"d0": "2018-05-01", "d1": "2018-05-01", "s": "1"},
        {"d0": "2018-04-30", "d1": "2026-01-01", "s": "1"},
    ],
)
def test_malformed_mapping_fails_internal_validation(entry: dict[str, str]) -> None:
    response = {"result": {"SPY": [entry]}, "status": 0, "partial": [], "not_found": []}
    result = DatabentoSource(_FakeClient(symbology_response=response)).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_INTERNAL_VALIDATION
    assert result.stages["D_symbology"] is StageStatus.FAILED


@pytest.mark.unit
def test_full_study_cost_uses_exclusive_end() -> None:
    client = _FakeClient()
    result = DatabentoSource(client).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.QUALIFIED
    full_calls = [call for call in client.metadata.cost_calls if call["end"] == "2026-01-01"]
    assert len(full_calls) == 6


@pytest.mark.unit
def test_authentication_failure() -> None:
    result = DatabentoSource(_FakeClient(error="Invalid API key")).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_AUTHENTICATION


@pytest.mark.unit
def test_entitlement_failure() -> None:
    result = DatabentoSource(_FakeClient(error="not entitled 403")).qualify_source(_CONFIG)
    assert result.status is QualificationStatus.FAILED_ENTITLEMENT
    assert result.entitlement_ok is False


@pytest.mark.unit
def test_from_env_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    with pytest.raises(CredentialMissingError):
        DatabentoSource.from_env()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Invalid API key", AuthenticationError),
        ("not entitled 403", EntitlementError),
        ("schema not available", SchemaUnavailableError),
        ("could not resolve symbol", SymbolResolutionError),
        ("dataset missing", DatasetUnavailableError),
        ("rate limit 429", RateLimitError),
        ("network connection timeout", ProviderNetworkError),
    ],
)
def test_translate_branches(message: str, expected: type[Exception]) -> None:
    assert isinstance(_translate(RuntimeError(message)), expected)


@pytest.mark.unit
def test_cost_records_size_and_count() -> None:
    result = DatabentoSource(_FakeClient()).qualify_source(_CONFIG)
    sample = result.cost_estimates[0]
    assert sample.size_bytes == 1024
    assert sample.record_count == 42
