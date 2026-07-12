"""Provider-neutral market-data source interface and result types.

All result objects are NeuralMarket-owned. Provider credentials, vendor response
structures, and vendor exceptions must not cross this boundary.

Range convention: provider dataset ranges are interpreted as *inclusive*
session-date bounds. A schema covers the study window only when its available
start is on or before the required start and its available end is on or after the
required end, so the full final session (for example 2025-12-31) is included.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Protocol

from neuralmarket.data.configuration import DataConfig


class QualificationStatus(str, Enum):
    """Single root outcome of a source qualification attempt."""

    QUALIFIED = "qualified"
    FAILED_AUTHENTICATION = "failed_authentication"
    FAILED_ENTITLEMENT = "failed_entitlement"
    FAILED_SCHEMA = "failed_schema"
    FAILED_COVERAGE = "failed_coverage"
    FAILED_PUBLISHER = "failed_publisher"
    FAILED_SYMBOLOGY = "failed_symbology"
    FAILED_COST_ESTIMATION = "failed_cost_estimation"
    FAILED_NETWORK = "failed_network"
    FAILED_INTERNAL_VALIDATION = "failed_internal_validation"


class StageStatus(str, Enum):
    """Per-stage outcome within a qualification attempt."""

    PASSED = "passed"
    RUNNING = "running"
    FAILED = "failed"
    NOT_RUN_DUE_TO_PRIOR_FAILURE = "not_run_due_to_prior_failure"


class CostPeriod(str, Enum):
    """Cost-estimate horizon."""

    ONE_SESSION = "one_session"
    ONE_MONTH = "one_month"
    FULL_STUDY = "full_study"


@dataclass(frozen=True, order=True)
class HalfOpenDateRange:
    """Calendar-date interval with ``[start, end_exclusive)`` semantics."""

    start: date
    end_exclusive: date

    def __post_init__(self) -> None:
        """Reject empty or reversed intervals."""
        if self.end_exclusive <= self.start:
            raise ValueError("end_exclusive must be after start")

    @classmethod
    def from_inclusive(cls, start: date, end_inclusive: date) -> HalfOpenDateRange:
        """Convert an inclusive configured range to a provider half-open range."""
        if end_inclusive < start:
            raise ValueError("end_inclusive must not be before start")
        try:
            end_exclusive = end_inclusive + timedelta(days=1)
        except OverflowError as exc:
            raise ValueError("inclusive end date cannot be converted to an exclusive end") from exc
        return cls(start=start, end_exclusive=end_exclusive)


@dataclass(frozen=True, order=True)
class SymbolMappingInterval:
    """One provider symbol mapping with half-open date bounds."""

    start: date
    end_exclusive: date
    output_symbol: str

    def __post_init__(self) -> None:
        """Reject invalid intervals and missing output symbols."""
        if self.end_exclusive <= self.start:
            raise ValueError("mapping end_exclusive must be after start")
        if not self.output_symbol:
            raise ValueError("mapping output_symbol is required")


def merge_mapping_intervals(
    intervals: tuple[SymbolMappingInterval, ...], requested: HalfOpenDateRange
) -> tuple[tuple[HalfOpenDateRange, ...], tuple[HalfOpenDateRange, ...]]:
    """Merge overlapping/adjacent mappings and return uncovered request intervals."""
    merged: list[HalfOpenDateRange] = []
    for interval in sorted(intervals, key=lambda item: (item.start, item.end_exclusive)):
        if interval.start < requested.start or interval.end_exclusive > requested.end_exclusive:
            raise ValueError("mapping interval lies outside requested range")
        if merged and interval.start <= merged[-1].end_exclusive:
            previous = merged[-1]
            merged[-1] = HalfOpenDateRange(
                previous.start, max(previous.end_exclusive, interval.end_exclusive)
            )
        else:
            merged.append(HalfOpenDateRange(interval.start, interval.end_exclusive))

    uncovered: list[HalfOpenDateRange] = []
    cursor = requested.start
    for coverage_interval in merged:
        if cursor < coverage_interval.start:
            uncovered.append(HalfOpenDateRange(cursor, coverage_interval.start))
        cursor = max(cursor, coverage_interval.end_exclusive)
    if cursor < requested.end_exclusive:
        uncovered.append(HalfOpenDateRange(cursor, requested.end_exclusive))
    return tuple(merged), tuple(uncovered)


@dataclass(frozen=True)
class DatasetRange:
    """Inclusive available session-date range for a dataset."""

    dataset: str
    start_date: date
    end_date: date


@dataclass(frozen=True)
class CoverageResult:
    """Coverage decision for one dataset/schema against the study window."""

    dataset: str
    schema: str
    available_start: date | None
    available_end: date | None
    required_start: date
    required_end: date
    range_semantics: str
    covers_start: bool
    covers_end: bool
    covers_complete_window: bool
    coverage_gap_days: int
    status: StageStatus


@dataclass(frozen=True)
class PublisherInfo:
    """A dataset publisher identified during qualification (public metadata only)."""

    dataset: str
    publisher_id: int
    venue: str
    description: str
    consolidated: bool


@dataclass(frozen=True)
class SymbolResolution:
    """Result of resolving a symbol across the requested interval."""

    dataset: str
    symbol: str
    symbol_type: str
    stype_out: str
    requested_range: HalfOpenDateRange
    response_range: HalfOpenDateRange
    provider_status: str
    provider_message: str | None
    partial: bool
    not_found: bool
    raw_intervals: tuple[SymbolMappingInterval, ...]
    merged_intervals: tuple[HalfOpenDateRange, ...]
    uncovered_intervals: tuple[HalfOpenDateRange, ...]
    resolved: bool
    detail: str
    failure_reason: str | None

    @property
    def mapping_count(self) -> int:
        """Return the number of raw provider mappings."""
        return len(self.raw_intervals)

    @property
    def distinct_output_count(self) -> int:
        """Return the count of distinct mapped output symbols."""
        return len({interval.output_symbol for interval in self.raw_intervals})


def compute_session_coverage(
    intervals: Sequence[tuple[date, date]],
    chunk: HalfOpenDateRange,
    sessions: Sequence[date],
) -> tuple[tuple[HalfOpenDateRange, ...], tuple[HalfOpenDateRange, ...], tuple[date, ...]]:
    """Merge child intervals and report coverage of a chunk.

    Every interval must be half-open and lie within ``chunk``. A calendar gap is a
    portion of the chunk covered by no interval. An uncovered session is a market
    session contained in no merged interval; only uncovered sessions gate selector
    availability.

    Args:
        intervals: Child ``(start, end_exclusive)`` date pairs for the chunk.
        chunk: The requested half-open chunk range.
        sessions: Market session dates within the chunk (inclusive).

    Returns:
        A tuple of (merged coverage intervals, calendar gaps, uncovered sessions).

    Raises:
        ValueError: If any interval is empty or falls outside the chunk.
    """
    for start, end in intervals:
        if end <= start:
            raise ValueError("child interval is empty or reversed")
        if start < chunk.start or end > chunk.end_exclusive:
            raise ValueError("child interval lies outside the requested chunk")

    merged: list[HalfOpenDateRange] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1].end_exclusive:
            previous = merged[-1]
            if end > previous.end_exclusive:
                merged[-1] = HalfOpenDateRange(previous.start, end)
        else:
            merged.append(HalfOpenDateRange(start, end))

    calendar_gaps: list[HalfOpenDateRange] = []
    cursor = chunk.start
    for interval in merged:
        if cursor < interval.start:
            calendar_gaps.append(HalfOpenDateRange(cursor, interval.start))
        cursor = max(cursor, interval.end_exclusive)
    if cursor < chunk.end_exclusive:
        calendar_gaps.append(HalfOpenDateRange(cursor, chunk.end_exclusive))

    uncovered = tuple(
        session
        for session in sessions
        if not any(m.start <= session < m.end_exclusive for m in merged)
    )
    return tuple(merged), tuple(calendar_gaps), uncovered


@dataclass(frozen=True)
class ParentChunkResult:
    """Validation outcome for one calendar-month parent-expansion chunk.

    Aggregate counts only; individual child mappings are never retained here.
    """

    chunk: HalfOpenDateRange
    status: int
    session_count: int
    child_symbol_count: int
    child_mapping_count: int
    distinct_instrument_id_count: int
    partial_child_count: int
    listing_mid_chunk_count: int
    expiring_mid_chunk_count: int
    overlapping_child_count: int
    calendar_gap_count: int
    uncovered_sessions: tuple[date, ...]
    ok: bool
    failure_reason: str | None


@dataclass(frozen=True)
class ParentSelectorResolution:
    """Chunked one-to-many parent-selector resolution over the study interval."""

    dataset: str
    parent_symbol: str
    symbol_type: str
    stype_out: str
    requested_range: HalfOpenDateRange
    validation_method: str
    chunks: tuple[ParentChunkResult, ...]
    resolved: bool
    failure_reason: str | None

    @property
    def chunk_count(self) -> int:
        """Return the number of requested chunks."""
        return len(self.chunks)

    @property
    def successful_chunk_count(self) -> int:
        """Return the number of chunks that passed selector validation."""
        return sum(1 for c in self.chunks if c.ok)

    @property
    def failed_chunk_count(self) -> int:
        """Return the number of chunks that failed selector validation."""
        return sum(1 for c in self.chunks if not c.ok)

    @property
    def empty_chunk_count(self) -> int:
        """Return the number of chunks with no child mappings."""
        return sum(1 for c in self.chunks if c.child_mapping_count == 0)

    @property
    def total_mapping_count(self) -> int:
        """Return the total child mappings across all chunks."""
        return sum(c.child_mapping_count for c in self.chunks)

    @property
    def distinct_output_count(self) -> int:
        """Return the per-chunk sum of distinct instrument ids.

        Instrument ids rotate each session, so a global distinct count is neither
        bounded nor meaningful; the per-chunk sum is the deterministic aggregate.
        """
        return sum(c.distinct_instrument_id_count for c in self.chunks)

    @property
    def distinct_child_symbol_count(self) -> int:
        """Return the per-chunk sum of distinct child symbols."""
        return sum(c.child_symbol_count for c in self.chunks)

    @property
    def session_gap_count(self) -> int:
        """Return the total number of uncovered market sessions."""
        return sum(len(c.uncovered_sessions) for c in self.chunks)

    @property
    def first_valid_date(self) -> date:
        """Return the first requested date."""
        return self.requested_range.start

    @property
    def end_exclusive(self) -> date:
        """Return the exclusive end of the requested interval."""
        return self.requested_range.end_exclusive


@dataclass(frozen=True)
class ProviderDiagnostic:
    """Sanitized provider-exception diagnostic for the local report only.

    Never contains credentials, headers, account identifiers, or raw response
    bodies. The original exception is chained internally at the raise site.
    """

    exception_class: str
    failure_category: str
    http_status_code: int | None
    provider_error_code: str | None
    safe_provider_message: str
    dataset: str
    input_symbol: str
    stype_in: str
    stype_out: str
    request_start: date
    request_end_exclusive: date
    request_duration_days: int
    operation: str


@dataclass(frozen=True)
class CostEstimate:
    """A single request cost estimate in a stated currency."""

    request_label: str
    dataset: str
    schema: str
    symbol: str
    symbol_type: str
    period: CostPeriod
    cost: float | None
    currency: str
    size_bytes: int | None
    record_count: int | None
    exact: bool
    estimate_method: str


@dataclass(frozen=True)
class QualificationResult:
    """Aggregated, account-neutral qualification outcome for one attempt."""

    provider: str
    status: QualificationStatus
    stages: dict[str, StageStatus]
    dataset_ranges: list[DatasetRange]
    coverage_results: list[CoverageResult]
    publishers: list[PublisherInfo]
    underlying_publisher: PublisherInfo | None
    optional_schemas: dict[str, str]
    symbol_resolutions: list[SymbolResolution]
    cost_estimates: list[CostEstimate]
    cost_currency: str
    entitlement_ok: bool
    parent_selector: ParentSelectorResolution | None = None
    provider_diagnostics: list[ProviderDiagnostic] = field(default_factory=list)
    downloads_attempted: int = 0
    downloaded_records: int = 0
    warnings: list[str] = field(default_factory=list)
    blocking_failures: list[str] = field(default_factory=list)


class MarketDataSource(Protocol):
    """Provider-neutral market-data source interface."""

    def get_dataset_range(self, dataset: str) -> DatasetRange:
        """Return the available inclusive date range for a dataset."""
        ...

    def list_schemas(self, dataset: str) -> list[str]:
        """Return the schemas available for a dataset."""
        ...

    def resolve_symbols(
        self, dataset: str, symbols: list[str], stype_in: str, start: date, end: date
    ) -> list[SymbolResolution]:
        """Resolve symbols within a dataset over a date range."""
        ...

    def qualify_source(self, config: DataConfig) -> QualificationResult:
        """Qualify the configured source using metadata-only requests."""
        ...
