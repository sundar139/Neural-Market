"""Databento source-qualification adapter with explicit staged sequencing.

Qualification runs in stages: authentication and dataset discovery, schema
discovery, coverage decision, symbology, cost estimation, and conclusion. A
coverage failure stops the later stages so out-of-range symbology or cost errors
are never misreported as independent root causes.

Uses only metadata, symbology, and cost-estimation requests. Time-series
retrieval, batch submission, downloads, and live subscriptions are prohibited by
an internal guard. Vendor errors are translated into domain errors and all
messages are credential-redacted.
"""

from __future__ import annotations

import os
import re
import time
from datetime import date, timedelta
from typing import Any, Protocol

from neuralmarket.core.logging import get_logger
from neuralmarket.data.calendar import session_dates
from neuralmarket.data.configuration import DataConfig
from neuralmarket.data.errors import (
    AuthenticationError,
    CostEstimationError,
    CoverageError,
    CredentialMissingError,
    DatasetUnavailableError,
    DownloadProhibitedError,
    EntitlementError,
    MarketDataError,
    ProviderNetworkError,
    PublisherError,
    RateLimitError,
    SchemaUnavailableError,
    SymbolResolutionError,
)
from neuralmarket.data.redaction import redact
from neuralmarket.data.sources.base import (
    CostEstimate,
    CostPeriod,
    CoverageResult,
    DatasetRange,
    HalfOpenDateRange,
    ParentChunkResult,
    ParentSelectorResolution,
    ProviderDiagnostic,
    PublisherInfo,
    QualificationResult,
    QualificationStatus,
    StageStatus,
    SymbolMappingInterval,
    SymbolResolution,
    compute_session_coverage,
    merge_mapping_intervals,
)
from neuralmarket.data.sources.symbology import normalize_status, status_acceptable

_logger = get_logger(__name__)

_API_KEY_ENV = "DATABENTO_API_KEY"
_FORBIDDEN_ATTRS = frozenset({"timeseries", "batch", "live"})
_CURRENCY = "USD"


class _DatabentoClient(Protocol):
    """Minimal structural interface for the injected provider client."""

    metadata: Any
    symbology: Any


class GuardedClient:
    """Wrap a provider client and hard-fail on any download-capable namespace."""

    def __init__(self, inner: _DatabentoClient) -> None:
        """Store the wrapped provider client."""
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access, blocking download-capable namespaces."""
        if name in _FORBIDDEN_ATTRS:
            raise DownloadProhibitedError(
                f"Access to '{name}' is prohibited during source qualification."
            )
        return getattr(self._inner, name)


def _to_date(value: Any) -> date:
    """Coerce a provider date/datetime/ISO string to a calendar date."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _translate(exc: Exception) -> MarketDataError:
    """Translate a vendor exception into a redacted domain error."""
    message = redact(str(exc)).lower()
    if any(token in message for token in ("api key", "unauthor", "401", "invalid credential")):
        return AuthenticationError("Provider rejected the credential.")
    if any(token in message for token in ("entitl", "403", "not permitted", "forbidden")):
        return EntitlementError("Account is not entitled for the requested dataset or schema.")
    if "schema" in message:
        return SchemaUnavailableError("Requested schema is unavailable.")
    if any(token in message for token in ("symbol", "resolve", "not found")):
        return SymbolResolutionError("Symbol could not be resolved.")
    if "dataset" in message:
        return DatasetUnavailableError("Requested dataset is unavailable.")
    if any(token in message for token in ("rate limit", "429", "too many")):
        return RateLimitError("Provider rate limit reached.")
    if any(token in message for token in ("network", "connection", "timeout", "temporarily")):
        return ProviderNetworkError("Network failure contacting provider.")
    return MarketDataError("Provider request failed.")


def _status_for(exc: MarketDataError) -> QualificationStatus:
    """Map a domain error to a single root qualification status."""
    mapping = {
        AuthenticationError: QualificationStatus.FAILED_AUTHENTICATION,
        EntitlementError: QualificationStatus.FAILED_ENTITLEMENT,
        SchemaUnavailableError: QualificationStatus.FAILED_SCHEMA,
        DatasetUnavailableError: QualificationStatus.FAILED_SCHEMA,
        SymbolResolutionError: QualificationStatus.FAILED_SYMBOLOGY,
        PublisherError: QualificationStatus.FAILED_PUBLISHER,
        CoverageError: QualificationStatus.FAILED_COVERAGE,
        CostEstimationError: QualificationStatus.FAILED_COST_ESTIMATION,
        ProviderNetworkError: QualificationStatus.FAILED_NETWORK,
        RateLimitError: QualificationStatus.FAILED_NETWORK,
    }
    return mapping.get(type(exc), QualificationStatus.FAILED_INTERNAL_VALIDATION)


_PARENT_VALIDATION_METHOD = "chunked_symbology_resolution"
_PROVIDER_CODE_RE = re.compile(r"\b([a-z]+(?:_[a-z]+)+)\b")

# Transient categories are retried during the long chunked parent sweep so a
# single provider hiccup does not discard a multi-minute qualification.
_TRANSIENT_CATEGORIES = frozenset({"network", "rate_limit", "provider_server_error"})
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 2.0


def _provider_error_code(message: str) -> str | None:
    """Extract a provider snake_case error code from a message, if present."""
    match = _PROVIDER_CODE_RE.search(message)
    return match.group(1) if match else None


def _categorize_provider_error(
    http_status: int | None, lowered_message: str
) -> tuple[str, MarketDataError]:
    """Map an HTTP status and message to a failure category and domain error."""
    msg = lowered_message
    if http_status == 401 or "unauthor" in msg or "invalid api key" in msg:
        return "authentication", AuthenticationError("Provider rejected the credential.")
    if http_status == 403 or "not entitled" in msg or "forbidden" in msg or "entitl" in msg:
        return "entitlement", EntitlementError(
            "Account is not entitled for the requested dataset or schema."
        )
    if http_status == 429 or "rate limit" in msg or "too many" in msg:
        return "rate_limit", RateLimitError("Provider rate limit reached.")
    if (
        http_status == 422
        and "symbolog" in msg
        and ("unable to process" in msg or "unsupported" in msg or "not support" in msg)
    ):
        return "unsupported_symbology_combination", SymbolResolutionError(
            "Parent-to-instrument symbology is unsupported for this dataset."
        )
    if "not found" in msg or "unknown symbol" in msg or "invalid symbol" in msg:
        return "invalid_symbol", SymbolResolutionError("Symbol could not be resolved.")
    if http_status == 413 or "too large" in msg:
        return "request_too_large", MarketDataError(
            "Provider reported the request is too large; use smaller chunks."
        )
    if "timeout" in msg or "connection" in msg or "network" in msg or "temporarily" in msg:
        return "network", ProviderNetworkError("Network failure contacting provider.")
    if http_status is not None and 500 <= http_status < 600:
        return "provider_server_error", ProviderNetworkError("Provider server error.")
    if http_status is not None and 400 <= http_status < 500:
        return "provider_client_error", MarketDataError("Provider client error.")
    return "malformed_response", MarketDataError("Provider request failed.")


def _classify_provider_exception(
    exc: Exception,
    *,
    dataset: str,
    symbol: str,
    stype_in: str,
    stype_out: str,
    chunk: HalfOpenDateRange,
    operation: str,
) -> tuple[ProviderDiagnostic, MarketDataError]:
    """Build a sanitized diagnostic and a domain error for a provider exception."""
    raw_status = getattr(exc, "http_status", None)
    try:
        http_status = int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError):
        http_status = None
    raw_message = getattr(exc, "message", None) or str(exc)
    safe_message = redact(str(raw_message))
    category, domain = _categorize_provider_error(http_status, safe_message.lower())
    diagnostic = ProviderDiagnostic(
        exception_class=type(exc).__name__,
        failure_category=category,
        http_status_code=http_status,
        provider_error_code=_provider_error_code(safe_message),
        safe_provider_message=safe_message[:300],
        dataset=dataset,
        input_symbol=symbol,
        stype_in=stype_in,
        stype_out=stype_out,
        request_start=chunk.start,
        request_end_exclusive=chunk.end_exclusive,
        request_duration_days=(chunk.end_exclusive - chunk.start).days,
        operation=operation,
    )
    return diagnostic, domain


def _month_chunks(rng: HalfOpenDateRange) -> list[HalfOpenDateRange]:
    """Split a half-open range into deterministic calendar-month chunks.

    The first chunk begins at the range start; each subsequent chunk begins on the
    first of the next month; the final chunk ends at the range's exclusive end. No
    gap or overlap is produced between chunks.
    """
    chunks: list[HalfOpenDateRange] = []
    cursor = rng.start
    while cursor < rng.end_exclusive:
        next_month = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        end = min(next_month, rng.end_exclusive)
        chunks.append(HalfOpenDateRange(cursor, end))
        cursor = end
    return chunks


def _parse_child_mapping(item: Any) -> tuple[date, date, str]:
    """Parse one child mapping entry into ``(start, end_exclusive, instrument_id)``."""
    if not isinstance(item, dict):
        raise ValueError("child mapping entry is not an object")
    start = item.get("d0", item.get("start_date"))
    end = item.get("d1", item.get("end_date"))
    output = item.get("s", item.get("symbol"))
    if start is None or end is None:
        raise ValueError("child mapping is missing an interval bound")
    if output is None or str(output) == "":
        raise ValueError("child mapping is missing an instrument id")
    start_date = _to_date(start)
    end_date = _to_date(end)
    if end_date <= start_date:
        raise ValueError("child mapping interval is empty or reversed")
    return start_date, end_date, str(output)


class DatabentoSource:
    """Adapter implementing metadata-only, staged Databento source qualification."""

    def __init__(self, client: _DatabentoClient) -> None:
        """Wrap an already-constructed provider client in a download guard."""
        self._client = GuardedClient(client)

    @classmethod
    def from_env(cls) -> DatabentoSource:
        """Build an adapter using ``DATABENTO_API_KEY`` from the environment.

        Raises:
            CredentialMissingError: If the API key is not set.
        """
        key = os.environ.get(_API_KEY_ENV)
        if not key:
            raise CredentialMissingError(
                f"{_API_KEY_ENV} is not set; add it to a local .env to qualify the source."
            )
        try:
            import databento
        except ImportError as exc:  # pragma: no cover - data extra guarantees presence
            raise MarketDataError("The 'data' extra is required for provider access.") from exc
        return cls(databento.Historical(key))

    # --- Low-level metadata calls ---------------------------------------------

    def get_dataset_range(self, dataset: str) -> DatasetRange:
        """Return the available inclusive date range for a dataset."""
        raw = self._call(lambda: self._client.metadata.get_dataset_range(dataset=dataset))
        start = raw.get("start") or raw.get("start_date")
        end = raw.get("end") or raw.get("end_date")
        if start is None or end is None:
            raise DatasetUnavailableError(f"No range returned for dataset {dataset}.")
        return DatasetRange(dataset=dataset, start_date=_to_date(start), end_date=_to_date(end))

    def list_schemas(self, dataset: str) -> list[str]:
        """Return the schemas available for a dataset."""
        schemas = self._call(lambda: self._client.metadata.list_schemas(dataset=dataset))
        return [str(s) for s in schemas]

    def list_publishers(self, dataset: str) -> list[PublisherInfo]:
        """Return public publisher metadata for a dataset (no account details)."""
        raw = self._call(lambda: self._client.metadata.list_publishers())
        publishers: list[PublisherInfo] = []
        for entry in raw:
            if str(entry.get("dataset")) != dataset:
                continue
            venue = str(entry.get("venue", ""))
            description = str(entry.get("description", ""))
            publishers.append(
                PublisherInfo(
                    dataset=dataset,
                    publisher_id=int(entry.get("publisher_id", 0)),
                    venue=venue,
                    description=description,
                    consolidated=_is_consolidated(dataset, venue, description),
                )
            )
        return publishers

    def resolve_symbols(
        self, dataset: str, symbols: list[str], stype_in: str, start: date, end: date
    ) -> list[SymbolResolution]:
        """Resolve symbols over an inclusive research range using a half-open API range."""
        requested = HalfOpenDateRange.from_inclusive(start, end)
        raw = self._call(
            lambda: self._client.symbology.resolve(
                dataset=dataset,
                symbols=symbols,
                stype_in=stype_in,
                stype_out="instrument_id",
                start_date=requested.start.isoformat(),
                end_date=requested.end_exclusive.isoformat(),
            ),
            context=f"Symbology resolution for {dataset}",
        )
        if not isinstance(raw, dict):
            raise MarketDataError(
                f"Malformed symbology response for {dataset}: expected an object."
            )
        resolved_map = raw.get("result", {})
        if not isinstance(resolved_map, dict):
            raise MarketDataError(
                f"Malformed symbology response for {dataset}: result is not an object."
            )
        partial_symbols = _symbol_set(raw.get("partial", []), "partial", dataset)
        not_found_symbols = _symbol_set(raw.get("not_found", []), "not_found", dataset)
        raw_status = raw.get("status", 0)
        provider_status = str(raw_status)
        try:
            normalized_status = normalize_status(raw_status)
        except ValueError as exc:
            raise MarketDataError(
                f"Malformed symbology status for {dataset}: {redact(str(exc))}."
            ) from exc
        provider_message = str(raw["message"]) if raw.get("message") is not None else None
        response_range = _response_range(raw, requested, dataset)
        if response_range != requested:
            raise MarketDataError(
                f"Malformed symbology response for {dataset}: response interval differs "
                "from request."
            )
        results: list[SymbolResolution] = []
        for symbol in symbols:
            mappings = resolved_map.get(symbol, [])
            if not isinstance(mappings, list):
                raise MarketDataError(
                    f"Malformed symbology response for {dataset}/{symbol}: mappings are not a list."
                )
            try:
                intervals = tuple(_parse_mapping(item) for item in mappings)
                merged, uncovered = merge_mapping_intervals(intervals, requested)
            except (KeyError, TypeError, ValueError) as exc:
                raise MarketDataError(
                    f"Malformed symbology mapping for {dataset}/{symbol}: {redact(str(exc))}."
                ) from exc
            partial = symbol in partial_symbols
            not_found = symbol in not_found_symbols
            if not_found:
                failure_reason = "provider_not_found"
            elif partial:
                failure_reason = "provider_partial"
            elif not intervals:
                failure_reason = "empty_mappings"
            elif uncovered:
                failure_reason = "provider_contradiction"
            elif not status_acceptable(normalized_status, parent_expansion=False):
                failure_reason = "provider_status_failure"
            else:
                failure_reason = None
            ok = failure_reason is None
            if ok:
                detail = "resolved throughout interval"
            elif failure_reason == "provider_contradiction":
                detail = "mapping gap contradicts provider complete status"
            else:
                assert failure_reason is not None
                detail = failure_reason.replace("_", " ")
            results.append(
                SymbolResolution(
                    dataset=dataset,
                    symbol=symbol,
                    symbol_type=stype_in,
                    stype_out="instrument_id",
                    requested_range=requested,
                    response_range=response_range,
                    provider_status=provider_status,
                    provider_message=provider_message,
                    partial=partial,
                    not_found=not_found,
                    raw_intervals=intervals,
                    merged_intervals=merged,
                    uncovered_intervals=uncovered,
                    resolved=ok,
                    detail=detail,
                    failure_reason=failure_reason,
                )
            )
        return results

    def resolve_parent_selector(
        self,
        dataset: str,
        parent_symbol: str,
        stype_in: str,
        calendar: str,
        start: date,
        end: date,
        diagnostics: list[ProviderDiagnostic],
    ) -> ParentSelectorResolution:
        """Validate a one-to-many parent selector by deterministic monthly chunks.

        Direct ``parent`` to ``instrument_id`` symbology is requested per calendar
        month. The parent expands into many child-contract keys, so the response is
        validated as a whole rather than by looking up the input symbol. A chunk is
        valid when the selector expands to at least one SPY child contract active on
        every market session in the chunk. Partial child resolution, daily
        instrument-id rotation, and contracts listing or expiring mid-chunk are
        expected and recorded only as diagnostics. Processing stops at the first
        failing chunk.
        """
        root = parent_symbol.split(".", 1)[0]
        requested = HalfOpenDateRange.from_inclusive(start, end)
        chunks = _month_chunks(requested)
        # Fetch the market sessions once and slice per chunk (deterministic and
        # far cheaper than rebuilding the calendar for every month).
        all_sessions = session_dates(calendar, start, end)
        results: list[ParentChunkResult] = []
        resolved = True
        failure_reason: str | None = None
        for chunk in chunks:
            chunk_sessions = [s for s in all_sessions if chunk.start <= s < chunk.end_exclusive]
            chunk_result = self._resolve_parent_chunk(
                dataset, parent_symbol, root, stype_in, chunk_sessions, chunk, diagnostics
            )
            results.append(chunk_result)
            if not chunk_result.ok:
                resolved = False
                month = chunk.start.isoformat()[:7]
                failure_reason = f"{chunk_result.failure_reason} in {month}"
                break
        return ParentSelectorResolution(
            dataset=dataset,
            parent_symbol=parent_symbol,
            symbol_type=stype_in,
            stype_out="instrument_id",
            requested_range=requested,
            validation_method=_PARENT_VALIDATION_METHOD,
            chunks=tuple(results),
            resolved=resolved,
            failure_reason=failure_reason,
        )

    def _resolve_chunk_with_retry(
        self,
        dataset: str,
        parent_symbol: str,
        stype_in: str,
        chunk: HalfOpenDateRange,
        diagnostics: list[ProviderDiagnostic],
    ) -> Any:
        """Resolve one chunk, retrying only transient provider failures."""
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return self._client.symbology.resolve(
                    dataset=dataset,
                    symbols=[parent_symbol],
                    stype_in=stype_in,
                    stype_out="instrument_id",
                    start_date=chunk.start.isoformat(),
                    end_date=chunk.end_exclusive.isoformat(),
                )
            except DownloadProhibitedError:
                raise
            except Exception as exc:
                diagnostic, domain = _classify_provider_exception(
                    exc,
                    dataset=dataset,
                    symbol=parent_symbol,
                    stype_in=stype_in,
                    stype_out="instrument_id",
                    chunk=chunk,
                    operation="parent_symbology_resolution",
                )
                if (
                    diagnostic.failure_category in _TRANSIENT_CATEGORIES
                    and attempt < _MAX_ATTEMPTS - 1
                ):
                    time.sleep(_BACKOFF_SECONDS * (attempt + 1))
                    continue
                diagnostics.append(diagnostic)
                raise domain from exc
        raise MarketDataError("Parent symbology retry attempts were exhausted.")

    def _resolve_parent_chunk(
        self,
        dataset: str,
        parent_symbol: str,
        root: str,
        stype_in: str,
        sessions: list[date],
        chunk: HalfOpenDateRange,
        diagnostics: list[ProviderDiagnostic],
    ) -> ParentChunkResult:
        raw = self._resolve_chunk_with_retry(dataset, parent_symbol, stype_in, chunk, diagnostics)

        if not isinstance(raw, dict):
            raise MarketDataError(
                f"Malformed parent symbology response for {dataset}: expected an object."
            )
        result_map = raw.get("result", {})
        if not isinstance(result_map, dict):
            raise MarketDataError(
                f"Malformed parent symbology response for {dataset}: result is not an object."
            )
        try:
            status = normalize_status(raw.get("status", 0))
        except ValueError as exc:
            raise MarketDataError(
                f"Malformed parent symbology status for {dataset}: {redact(str(exc))}."
            ) from exc
        not_found = _symbol_set(raw.get("not_found", []), "not_found", dataset)
        partial = _symbol_set(raw.get("partial", []), "partial", dataset)

        intervals: list[tuple[date, date]] = []
        instrument_ids: set[str] = set()
        mapping_count = 0
        listing = expiring = overlapping = 0
        foreign = False
        for child_symbol, mappings in result_map.items():
            if str(child_symbol).split(" ", 1)[0] != root:
                foreign = True
                break
            if not isinstance(mappings, list):
                raise MarketDataError(
                    f"Malformed parent symbology mapping for {dataset}/{child_symbol}: not a list."
                )
            try:
                parsed = [_parse_child_mapping(item) for item in mappings]
            except (KeyError, TypeError, ValueError) as exc:
                raise MarketDataError(
                    f"Malformed parent symbology mapping for {dataset}: {redact(str(exc))}."
                ) from exc
            if not parsed:
                continue
            parsed.sort()
            if parsed[0][0] > chunk.start:
                listing += 1
            if max(entry[1] for entry in parsed) < chunk.end_exclusive:
                expiring += 1
            previous_end: date | None = None
            for entry in parsed:
                if previous_end is not None and entry[0] < previous_end:
                    overlapping += 1
                    break
                previous_end = entry[1]
            for entry in parsed:
                # Clamp to the chunk: the provider returns a contract's true mapping
                # dates, which may extend past the requested window when a contract
                # is active across the boundary. Coverage only concerns sessions in
                # the chunk, so a spanning interval still covers them. Listing and
                # expiring diagnostics above use the raw (unclamped) dates.
                clamp_start = max(entry[0], chunk.start)
                clamp_end = min(entry[1], chunk.end_exclusive)
                if clamp_end > clamp_start:
                    intervals.append((clamp_start, clamp_end))
                instrument_ids.add(entry[2])
            mapping_count += len(parsed)

        uncovered: tuple[date, ...] = ()
        calendar_gap_count = 0
        if foreign:
            failure_reason: str | None = "foreign_underlying"
        else:
            try:
                _merged, calendar_gaps, uncovered = compute_session_coverage(
                    intervals, chunk, sessions
                )
            except ValueError as exc:
                raise MarketDataError(
                    f"Parent symbology mapping outside chunk for {dataset}: {redact(str(exc))}."
                ) from exc
            calendar_gap_count = len(calendar_gaps)
            if not status_acceptable(status, parent_expansion=True):
                failure_reason = "status_not_found"
            elif parent_symbol in not_found:
                failure_reason = "not_found"
            elif mapping_count == 0:
                failure_reason = "empty_mappings"
            elif uncovered:
                failure_reason = "uncovered_sessions"
            else:
                failure_reason = None

        return ParentChunkResult(
            chunk=chunk,
            status=int(status),
            session_count=len(sessions),
            child_symbol_count=len(result_map),
            child_mapping_count=mapping_count,
            distinct_instrument_id_count=len(instrument_ids),
            partial_child_count=len(partial),
            listing_mid_chunk_count=listing,
            expiring_mid_chunk_count=expiring,
            overlapping_child_count=overlapping,
            calendar_gap_count=calendar_gap_count,
            uncovered_sessions=uncovered,
            ok=failure_reason is None,
            failure_reason=failure_reason,
        )

    def _call(self, thunk: Any, *, context: str | None = None) -> Any:
        try:
            return thunk()
        except DownloadProhibitedError:
            raise
        except Exception as exc:
            translated = _translate(exc)
            if context and type(translated) is MarketDataError:
                raise MarketDataError(
                    f"{context} failed due to an invalid provider response."
                ) from exc
            raise translated from exc

    def _optional_int(self, thunk: Any) -> int | None:
        try:
            value = thunk()
        except DownloadProhibitedError:
            raise
        except Exception:
            return None
        return int(value) if value is not None else None

    def _cost(
        self,
        dataset: str,
        schema: str,
        symbol: str,
        stype_in: str,
        start: date,
        end_exclusive: date,
        period: CostPeriod,
    ) -> CostEstimate:
        cost = self._call(
            lambda: self._client.metadata.get_cost(
                dataset=dataset,
                symbols=[symbol],
                schema=schema,
                start=start.isoformat(),
                end=end_exclusive.isoformat(),
                stype_in=stype_in,
            )
        )
        size = self._optional_int(
            lambda: self._client.metadata.get_billable_size(
                dataset=dataset,
                symbols=[symbol],
                schema=schema,
                start=start.isoformat(),
                end=end_exclusive.isoformat(),
                stype_in=stype_in,
            )
        )
        count = self._optional_int(
            lambda: self._client.metadata.get_record_count(
                dataset=dataset,
                symbols=[symbol],
                schema=schema,
                start=start.isoformat(),
                end=end_exclusive.isoformat(),
                stype_in=stype_in,
            )
        )
        return CostEstimate(
            request_label=f"{dataset}/{schema}/{period.value}",
            dataset=dataset,
            schema=schema,
            symbol=symbol,
            symbol_type=stype_in,
            period=period,
            cost=float(cost),
            currency=_CURRENCY,
            size_bytes=size,
            record_count=count,
            exact=True,
            estimate_method="databento_metadata",
        )

    # --- Staged qualification --------------------------------------------------

    def qualify_source(self, config: DataConfig) -> QualificationResult:
        """Qualify the configured Databento source using metadata-only requests."""
        state = _QualifyState(config)
        try:
            self._stage_a_discovery(state)
            self._stage_b_schemas(state)
            self._stage_c_coverage(state)
            self._stage_d_symbology(state)
            self._stage_e_cost(state)
        except MarketDataError as exc:
            for stage, status in state.stages.items():
                if status is StageStatus.RUNNING:
                    state.mark(stage, StageStatus.FAILED)
            state.fail(_status_for(exc), redact(str(exc)))
        return state.result()

    def _stage_a_discovery(self, state: _QualifyState) -> None:
        provider = state.config.provider
        for dataset in (provider.underlying.dataset, provider.options.dataset):
            state.dataset_ranges.append(self.get_dataset_range(dataset))
        state.mark("A_discovery", StageStatus.PASSED)

    def _stage_b_schemas(self, state: _QualifyState) -> None:
        discovered = {
            dataset: self.list_schemas(dataset)
            for dataset in {
                state.config.provider.underlying.dataset,
                state.config.provider.options.dataset,
            }
        }
        for dataset, schema in state.required_schemas():
            schemas = discovered[dataset]
            if schema not in schemas:
                state.mark("B_schemas", StageStatus.FAILED)
                raise SchemaUnavailableError(f"Schema {schema} unavailable for {dataset}.")
        optional = state.config.provider.underlying.optional_statistics_schema
        if optional in discovered[state.config.provider.underlying.dataset]:
            state.optional_schemas[optional] = "available"
        else:
            state.optional_schemas[optional] = "unavailable"
            state.warnings.append(
                f"Optional schema {optional} is unavailable; qualification continues."
            )
        state.mark("B_schemas", StageStatus.PASSED)

    def _stage_c_coverage(self, state: _QualifyState) -> None:
        ranges = {r.dataset: r for r in state.dataset_ranges}
        required_start = state.config.study.start_date
        required_end = state.config.study.end_date
        complete = True
        for dataset, schema in state.required_schemas():
            drange = ranges[dataset]
            covers_start = drange.start_date <= required_start
            covers_end = drange.end_date >= required_end
            gap = _coverage_gap_days(
                drange.start_date, drange.end_date, required_start, required_end
            )
            ok = covers_start and covers_end
            complete = complete and ok
            state.coverage_results.append(
                CoverageResult(
                    dataset=dataset,
                    schema=schema,
                    available_start=drange.start_date,
                    available_end=drange.end_date,
                    required_start=required_start,
                    required_end=required_end,
                    range_semantics="inclusive_session_dates",
                    covers_start=covers_start,
                    covers_end=covers_end,
                    covers_complete_window=ok,
                    coverage_gap_days=gap,
                    status=StageStatus.PASSED if ok else StageStatus.FAILED,
                )
            )
            if not ok:
                state.blocking_failures.append(
                    f"{dataset}/{schema} covers [{drange.start_date}, {drange.end_date}], "
                    f"which does not include [{required_start}, {required_end}]."
                )
        if not complete:
            state.mark("C_coverage", StageStatus.FAILED)
            raise CoverageError("One or more schemas do not cover the study window.")
        state.mark("C_coverage", StageStatus.PASSED)

    def _stage_d_symbology(self, state: _QualifyState) -> None:
        provider = state.config.provider
        study = state.config.study
        state.mark("D_symbology", StageStatus.RUNNING)

        # Publisher validation for the underlying dataset.
        state.publishers = self.list_publishers(provider.underlying.dataset)
        publisher = next(
            (
                p
                for p in state.publishers
                if p.venue.upper() == "ARCX" or "NYSE ARCA" in p.description.upper()
            ),
            None,
        )
        if publisher is None:
            state.mark("D_symbology", StageStatus.FAILED)
            state.blocking_failures.append(
                f"ARCX publisher not found for {provider.underlying.dataset}."
            )
            raise PublisherError("ARCX publisher identity could not be verified.")
        state.underlying_publisher = publisher

        # Underlying: single raw-symbol resolution requiring status 0 throughout.
        state.symbol_resolutions.extend(
            self.resolve_symbols(
                provider.underlying.dataset,
                [provider.underlying.symbol],
                provider.underlying.symbol_type,
                study.start_date,
                study.end_date,
            )
        )
        underlying_unresolved = [s for s in state.symbol_resolutions if not s.resolved]
        if underlying_unresolved:
            state.mark("D_symbology", StageStatus.FAILED)
            for resolution in underlying_unresolved:
                state.blocking_failures.append(f"Symbol {resolution.symbol}: {resolution.detail}.")
            if any(
                resolution.failure_reason in {"provider_contradiction", "empty_mappings"}
                for resolution in underlying_unresolved
            ):
                raise MarketDataError("Provider symbology response contradicts computed coverage.")
            raise SymbolResolutionError("One or more symbols did not resolve.")

        # Options: one-to-many parent selector validated by deterministic monthly
        # chunks. The parent expands into many child-contract keys, so it is never
        # looked up as an input symbol.
        state.parent_selector = self.resolve_parent_selector(
            provider.options.dataset,
            provider.options.parent_symbol,
            provider.options.symbol_type,
            study.calendar,
            study.start_date,
            study.end_date,
            state.provider_diagnostics,
        )
        if not state.parent_selector.resolved:
            state.mark("D_symbology", StageStatus.FAILED)
            state.blocking_failures.append(
                f"Parent selector {provider.options.parent_symbol}: "
                f"{state.parent_selector.failure_reason}."
            )
            raise SymbolResolutionError(
                "Options parent selector did not maintain active-child session coverage."
            )
        state.mark("D_symbology", StageStatus.PASSED)

    def _stage_e_cost(self, state: _QualifyState) -> None:
        study = state.config.study
        start = study.start_date
        one_session_end = start + timedelta(days=1)
        one_month_end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        full_end = HalfOpenDateRange.from_inclusive(start, study.end_date).end_exclusive
        for dataset, schema, symbol, stype in state.cost_plans():
            for period, end in (
                (CostPeriod.ONE_SESSION, one_session_end),
                (CostPeriod.ONE_MONTH, one_month_end),
                (CostPeriod.FULL_STUDY, full_end),
            ):
                state.cost_estimates.append(
                    self._cost(dataset, schema, symbol, stype, start, end, period)
                )
        state.mark("E_cost", StageStatus.PASSED)


def _is_consolidated(dataset: str, venue: str, description: str) -> bool:
    """Heuristically identify a dataset's consolidated publisher from public metadata."""
    normalized_venue = venue.upper()
    return (
        dataset == "DBEQ.BASIC"
        and (normalized_venue in {"DBEQ", "XDBP"} or "consolidat" in description.lower())
    ) or (dataset.startswith("EQUS.") or "consolidat" in description.lower())


def _symbol_set(value: Any, field: str, dataset: str) -> set[str]:
    if not isinstance(value, list):
        raise MarketDataError(f"Malformed symbology response for {dataset}: {field} is not a list.")
    return {str(item) for item in value}


def _response_range(
    raw: dict[str, Any], requested: HalfOpenDateRange, dataset: str
) -> HalfOpenDateRange:
    start = raw.get("start_date", raw.get("start"))
    end = raw.get("end_date", raw.get("end"))
    if start is None and end is None:
        return requested
    if start is None or end is None:
        raise MarketDataError(f"Malformed symbology response for {dataset}: incomplete interval.")
    try:
        return HalfOpenDateRange(_to_date(start), _to_date(end))
    except ValueError as exc:
        raise MarketDataError(
            f"Malformed symbology response for {dataset}: invalid response interval."
        ) from exc


def _parse_mapping(item: Any) -> SymbolMappingInterval:
    if not isinstance(item, dict):
        raise TypeError("mapping entry is not an object")
    start = item.get("d0", item.get("start_date"))
    end = item.get("d1", item.get("end_date"))
    output = item.get("s", item.get("symbol"))
    if start is None:
        raise ValueError("mapping start is missing")
    if end is None:
        raise ValueError("mapping exclusive end is missing")
    if output is None or str(output) == "":
        raise ValueError("mapping output symbol is missing")
    return SymbolMappingInterval(_to_date(start), _to_date(end), str(output))


def _coverage_gap_days(
    available_start: date, available_end: date, required_start: date, required_end: date
) -> int:
    """Return the size of the coverage gap in days, or 0 when fully covered."""
    if available_start > required_start:
        return (available_start - required_start).days
    if available_end < required_end:
        return (required_end - available_end).days
    return 0


class _QualifyState:
    """Mutable accumulator threaded through the qualification stages."""

    _STAGE_ORDER = ("A_discovery", "B_schemas", "C_coverage", "D_symbology", "E_cost")

    def __init__(self, config: DataConfig) -> None:
        self.config = config
        self.stages: dict[str, StageStatus] = dict.fromkeys(
            self._STAGE_ORDER, StageStatus.NOT_RUN_DUE_TO_PRIOR_FAILURE
        )
        self.dataset_ranges: list[DatasetRange] = []
        self.coverage_results: list[CoverageResult] = []
        self.publishers: list[PublisherInfo] = []
        self.underlying_publisher: PublisherInfo | None = None
        self.optional_schemas: dict[str, str] = {}
        self.symbol_resolutions: list[SymbolResolution] = []
        self.parent_selector: ParentSelectorResolution | None = None
        self.provider_diagnostics: list[ProviderDiagnostic] = []
        self.cost_estimates: list[CostEstimate] = []
        self.blocking_failures: list[str] = []
        self.warnings: list[str] = []
        self._status = QualificationStatus.QUALIFIED
        self._entitlement_ok = True

    def required_schemas(self) -> list[tuple[str, str]]:
        u = self.config.provider.underlying
        o = self.config.provider.options
        return [
            (u.dataset, u.definition_schema),
            (u.dataset, u.daily_schema),
            (u.dataset, u.quote_schema),
            (o.dataset, o.definition_schema),
            (o.dataset, o.quote_schema),
        ]

    def cost_plans(self) -> list[tuple[str, str, str, str]]:
        u = self.config.provider.underlying
        o = self.config.provider.options
        plans = [
            (u.dataset, u.definition_schema, u.symbol, u.symbol_type),
            (u.dataset, u.daily_schema, u.symbol, u.symbol_type),
            (u.dataset, u.quote_schema, u.symbol, u.symbol_type),
            (o.dataset, o.definition_schema, o.parent_symbol, o.symbol_type),
            (o.dataset, o.quote_schema, o.parent_symbol, o.symbol_type),
        ]
        if self.optional_schemas.get(u.optional_statistics_schema) == "available":
            plans.append((u.dataset, u.optional_statistics_schema, u.symbol, u.symbol_type))
        return plans

    def mark(self, stage: str, status: StageStatus) -> None:
        self.stages[stage] = status

    def fail(self, status: QualificationStatus, message: str) -> None:
        self._status = status
        if status is QualificationStatus.FAILED_ENTITLEMENT:
            self._entitlement_ok = False
        if not self.blocking_failures and message not in self.blocking_failures:
            self.blocking_failures.append(message)

    def result(self) -> QualificationResult:
        return QualificationResult(
            provider=self.config.provider.name,
            status=self._status,
            stages=dict(self.stages),
            dataset_ranges=self.dataset_ranges,
            coverage_results=self.coverage_results,
            publishers=self.publishers,
            underlying_publisher=self.underlying_publisher,
            optional_schemas=dict(self.optional_schemas),
            symbol_resolutions=self.symbol_resolutions,
            cost_estimates=self.cost_estimates,
            cost_currency=_CURRENCY,
            entitlement_ok=self._entitlement_ok,
            parent_selector=self.parent_selector,
            provider_diagnostics=self.provider_diagnostics,
            downloads_attempted=0,
            downloaded_records=0,
            warnings=self.warnings,
            blocking_failures=self.blocking_failures,
        )
