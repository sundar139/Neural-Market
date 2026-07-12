"""Deterministic source and split manifests with canonical hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from neuralmarket.data.calendar import SplitResult
from neuralmarket.data.configuration import DataConfig
from neuralmarket.data.contracts import SCHEMA_VERSION
from neuralmarket.data.errors import ManifestValidationError

# Fields excluded from a manifest's own hash input (volatile or self-referential).
_HASH_EXCLUDED = ("manifest_hash", "generated_at", "qualification_timestamp")

_LICENSE_WARNING = (
    "Market data is licensed and commercial. Raw and normalized records must not "
    "be redistributed through Git. Users must independently comply with vendor terms."
)
_QUOTE_SNAPSHOT_POLICY = (
    "Use the final valid consolidated quote at or before 15:59:00 America/New_York, "
    "subject to a maximum quote age of five minutes."
)
_UNDERLYING_SNAPSHOT_POLICY = (
    "Use ARCX.PILLAR BBO only as an NYSE Arca venue-liquidity proxy; it is not official NBBO."
)
_OPTIONS_LIMITATIONS = ["OPRA.PILLAR is limited to SPY options selected through SPY.OPT."]
_UNDERLYING_LIMITATIONS = [
    "ARCX.PILLAR is venue-specific NYSE Arca data, not SIP or consolidated equities.",
    "ARCX BBO is not official NBBO and ARCX volume is not full-market SPY volume.",
    "Acceptance is conditional on later row-level quality, corporate-action, and "
    "venue-proxy validation.",
    "The primary-listing-venue exception applies only to SPY; other underlyings "
    "require qualification.",
]
_TRANSACTION_COST_POLICY = {
    "primary": "explicit_modeled_costs",
    "arcx_spread_role": "auxiliary",
}


def canonical_dumps(payload: dict[str, Any]) -> str:
    """Serialize a mapping to canonical JSON: UTF-8, sorted keys, tight separators."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(payload: dict[str, Any]) -> str:
    """Return the SHA-256 over canonical JSON of a payload minus volatile fields."""
    reduced = {k: v for k, v in payload.items() if k not in _HASH_EXCLUDED}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


def canonical_summary_hash(summary: dict[str, Any]) -> str:
    """Return the SHA-256 over canonical JSON of an aggregate summary mapping.

    The ``canonical_summary_hash`` field itself is excluded so the hash is a stable
    fingerprint of the aggregate parent-selector validation independent of storage.
    """
    reduced = {k: v for k, v in summary.items() if k != "canonical_summary_hash"}
    return hashlib.sha256(canonical_dumps(reduced).encode("utf-8")).hexdigest()


class DateRange(BaseModel):
    """An inclusive date range."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date


class BoundaryRange(BaseModel):
    """An excluded boundary block recorded in a split manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date
    session_count: int
    session_hash: str


class Publisher(BaseModel):
    """Public publisher metadata (no account details)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    publisher_id: int
    venue: str
    description: str


class UnderlyingSourceBlock(BaseModel):
    """Accepted underlying source metadata for the source manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    venue: str
    source_class: str
    symbol: str
    schemas: list[str]
    optional_schemas: dict[str, str]
    schema_ranges: dict[str, DateRange]
    publisher: Publisher
    symbol_resolution: str
    price_role: str
    quote_role: str
    venue_specific: bool
    consolidated_equities: bool
    sip: bool
    official_nbbo: bool
    full_market_volume: bool
    limitations: list[str]
    required_future_validations: list[str]

    @model_validator(mode="after")
    def _validate_arcx_governance(self) -> UnderlyingSourceBlock:
        if self.dataset == "ARCX.PILLAR" and (
            self.source_class != "primary_listing_venue"
            or self.price_role != "underlying_reference_path"
            or self.quote_role != "venue_liquidity_proxy"
            or not self.venue_specific
            or self.consolidated_equities
            or self.sip
            or self.official_nbbo
            or self.full_market_volume
            or "arcx_vs_equs_mini_development_overlap" not in self.required_future_validations
        ):
            raise ValueError("ARCX source manifest contradicts venue-specific governance")
        return self


class OptionsSelectorSummary(BaseModel):
    """Account-neutral aggregate of the chunked parent-selector validation.

    Detailed child mappings are never stored here; only counts and a canonical
    hash of the aggregate are preserved in the tracked manifest.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    validation_method: str
    chunk_count: int
    successful_chunk_count: int
    failed_chunk_count: int
    empty_chunk_count: int
    total_mapping_count: int
    distinct_output_count: int
    distinct_child_symbol_count: int
    session_gap_count: int
    first_valid_date: date
    end_exclusive: date
    canonical_summary_hash: str

    @model_validator(mode="after")
    def _validate_selector(self) -> OptionsSelectorSummary:
        if self.validation_method != "chunked_symbology_resolution":
            raise ValueError(
                "options selector_summary.validation_method must be "
                "'chunked_symbology_resolution'; the metadata parent-selector "
                "preflight branch is not implemented in this milestone"
            )
        if self.chunk_count < 1:
            raise ValueError("chunked resolution requires at least one chunk")
        if self.successful_chunk_count != self.chunk_count or self.failed_chunk_count != 0:
            raise ValueError("a qualified selector requires every chunk to pass")
        if self.session_gap_count != 0:
            raise ValueError("a qualified selector requires zero uncovered sessions")
        return self


class OptionsSourceBlock(BaseModel):
    """Accepted options source metadata for the source manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    source_class: str
    parent_symbol: str
    schemas: list[str]
    schema_ranges: dict[str, DateRange]
    symbol_resolution: str
    validation_method: str
    selector_summary: OptionsSelectorSummary
    limitations: list[str]


class SourceManifest(BaseModel):
    """Tracked, account-neutral research metadata for a qualified source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: str
    provider: str
    study_start: date
    study_end: date
    underlying: UnderlyingSourceBlock
    options: OptionsSourceBlock
    snapshot_rules: dict[str, str]
    transaction_cost_source_policy: dict[str, str]
    license_notice: str
    qualification_status: str
    qualification_timestamp: str
    config_hash: str
    code_commit: str | None
    generated_at: str
    manifest_hash: str

    @model_validator(mode="after")
    def _validate_cost_policy(self) -> SourceManifest:
        policy = self.transaction_cost_source_policy
        for required in ("primary", "arcx_spread_role"):
            if required not in policy:
                raise ValueError(f"transaction_cost_source_policy missing '{required}'")
        if policy["primary"] != "explicit_modeled_costs":
            raise ValueError("transaction cost policy must use explicit modeled costs as primary")
        if policy["arcx_spread_role"] != "auxiliary":
            raise ValueError("ARCX spread role must be auxiliary")
        return self


class SplitManifest(BaseModel):
    """Frozen chronological split manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: str
    calendar_name: str
    calendar_library_version: str
    calendar_timezone: str
    study_start: date
    study_end: date
    lookback_sessions: int
    maximum_maturity_sessions: int
    purge_sessions: int
    embargo_sessions: int
    training_start: date
    training_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    excluded_boundary_ranges: list[BoundaryRange]
    training_sessions: int
    validation_sessions: int
    test_sessions: int
    training_hash: str
    validation_hash: str
    test_hash: str
    calendar_hash: str
    config_hash: str
    git_commit: str | None
    final_test_access_status: str
    generated_at: str
    manifest_hash: str


def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Compute and attach the canonical manifest hash."""
    payload["manifest_hash"] = canonical_hash(payload)
    return payload


def build_split_manifest(
    config: DataConfig,
    result: SplitResult,
    *,
    config_hash: str,
    git_commit: str | None,
    generated_at: str,
) -> dict[str, Any]:
    """Build a deterministic split-manifest payload with a canonical hash.

    Args:
        config: Validated market-data configuration.
        result: Computed split boundaries.
        config_hash: SHA-256 of the configuration file.
        git_commit: Current Git commit or ``None``.
        generated_at: UTC ISO timestamp (excluded from the hash).

    Returns:
        A JSON-serializable manifest payload including ``manifest_hash``.
    """
    payload: dict[str, Any] = {
        "manifest_version": SCHEMA_VERSION,
        "calendar_name": config.study.calendar,
        "calendar_library_version": _calendar_lib_version(),
        "calendar_timezone": config.study.timezone,
        "study_start": config.study.start_date.isoformat(),
        "study_end": config.study.end_date.isoformat(),
        "lookback_sessions": config.episodes.conditioning_lookback_sessions,
        "maximum_maturity_sessions": config.episodes.maximum_maturity_sessions,
        "purge_sessions": config.splits.purge_sessions,
        "embargo_sessions": config.splits.embargo_sessions,
        "training_start": result.training_start.isoformat(),
        "training_end": result.training_end.isoformat(),
        "validation_start": result.validation_start.isoformat(),
        "validation_end": result.validation_end.isoformat(),
        "test_start": result.test_start.isoformat(),
        "test_end": result.test_end.isoformat(),
        "excluded_boundary_ranges": [
            {
                "start_date": excl.start_date.isoformat(),
                "end_date": excl.end_date.isoformat(),
                "session_count": excl.session_count,
                "session_hash": excl.session_hash,
            }
            for excl in result.boundary_exclusions
        ],
        "training_sessions": result.training_sessions,
        "validation_sessions": result.validation_sessions,
        "test_sessions": result.test_sessions,
        "training_hash": result.training_hash,
        "validation_hash": result.validation_hash,
        "test_hash": result.test_hash,
        "calendar_hash": result.calendar_hash,
        "config_hash": config_hash,
        "git_commit": git_commit,
        "final_test_access_status": config.splits.final_test_access_status.value,
        "generated_at": generated_at,
    }
    return _finalize(payload)


def _calendar_lib_version() -> str:
    from neuralmarket.data.calendar import calendar_library_version

    return calendar_library_version()


def _ranges_json(ranges: dict[str, DateRange]) -> dict[str, dict[str, str]]:
    return {
        key: {"start_date": rng.start_date.isoformat(), "end_date": rng.end_date.isoformat()}
        for key, rng in sorted(ranges.items())
    }


def build_source_manifest(
    config: DataConfig,
    *,
    underlying_ranges: dict[str, DateRange],
    options_ranges: dict[str, DateRange],
    publisher: dict[str, Any],
    optional_schemas: dict[str, str],
    underlying_symbol_resolution: str,
    options_symbol_resolution: str,
    options_validation_method: str,
    options_selector_summary: dict[str, Any],
    qualification_status: str,
    qualification_timestamp: str,
    config_hash: str,
    git_commit: str | None,
    generated_at: str,
) -> dict[str, Any]:
    """Build an account-neutral source-manifest payload for the accepted source.

    Args:
        config: Validated market-data configuration.
        underlying_ranges: Mapping of underlying ``dataset/schema`` to available range.
        options_ranges: Mapping of options ``dataset/schema`` to available range.
        publisher: Public underlying publisher metadata.
        optional_schemas: Optional-schema qualification statuses.
        underlying_symbol_resolution: Human-readable underlying symbology result.
        options_symbol_resolution: Human-readable options symbology result.
        options_validation_method: Parent-selector validation method identifier.
        options_selector_summary: Aggregate parent-selector summary with hash.
        qualification_status: Root qualification status string.
        qualification_timestamp: UTC ISO time of qualification (excluded from hash).
        config_hash: SHA-256 of the configuration file.
        git_commit: Current Git commit or ``None``.
        generated_at: UTC ISO timestamp (excluded from the hash).

    Returns:
        A JSON-serializable manifest payload including ``manifest_hash``.
    """
    u = config.provider.underlying
    o = config.provider.options
    payload: dict[str, Any] = {
        "manifest_version": SCHEMA_VERSION,
        "provider": config.provider.name,
        "study_start": config.study.start_date.isoformat(),
        "study_end": config.study.end_date.isoformat(),
        "underlying": {
            "dataset": u.dataset,
            "venue": u.venue,
            "source_class": u.source_class,
            "symbol": u.symbol,
            "schemas": [u.definition_schema, u.daily_schema, u.quote_schema],
            "optional_schemas": optional_schemas,
            "schema_ranges": _ranges_json(underlying_ranges),
            "publisher": publisher,
            "symbol_resolution": underlying_symbol_resolution,
            "price_role": u.price_role,
            "quote_role": u.quote_role,
            "venue_specific": u.venue_specific,
            "consolidated_equities": u.consolidated_equities,
            "sip": u.sip,
            "official_nbbo": u.official_nbbo,
            "full_market_volume": u.full_market_volume,
            "limitations": list(_UNDERLYING_LIMITATIONS),
            "required_future_validations": list(u.required_future_validations),
        },
        "options": {
            "dataset": o.dataset,
            "source_class": o.source_class,
            "parent_symbol": o.parent_symbol,
            "schemas": [o.definition_schema, o.quote_schema],
            "schema_ranges": _ranges_json(options_ranges),
            "symbol_resolution": options_symbol_resolution,
            "validation_method": options_validation_method,
            "selector_summary": options_selector_summary,
            "limitations": list(_OPTIONS_LIMITATIONS),
        },
        "snapshot_rules": {
            "underlying": _UNDERLYING_SNAPSHOT_POLICY,
            "option": _QUOTE_SNAPSHOT_POLICY,
        },
        "transaction_cost_source_policy": dict(_TRANSACTION_COST_POLICY),
        "license_notice": _LICENSE_WARNING,
        "qualification_status": qualification_status,
        "qualification_timestamp": qualification_timestamp,
        "config_hash": config_hash,
        "code_commit": git_commit,
        "generated_at": generated_at,
    }
    return _finalize(payload)


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    """Write a manifest payload as indented, sorted, UTF-8 JSON with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a manifest JSON file into a dictionary."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestValidationError(f"Manifest not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"Unable to read manifest {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"Manifest {path} must be a JSON object.")
    return raw


def verify_manifest_hash(payload: dict[str, Any]) -> None:
    """Raise if a manifest's stored hash does not match its canonical payload."""
    stored = payload.get("manifest_hash")
    if not isinstance(stored, str):
        raise ManifestValidationError("Manifest is missing a string manifest_hash.")
    recomputed = canonical_hash(payload)
    if stored != recomputed:
        raise ManifestValidationError(
            f"Manifest hash mismatch: stored {stored}, recomputed {recomputed}."
        )


def parse_source_manifest(payload: dict[str, Any]) -> SourceManifest:
    """Validate a payload as a :class:`SourceManifest`."""
    try:
        return SourceManifest.model_validate(payload)
    except ValidationError as exc:
        raise ManifestValidationError(f"Invalid source manifest: {exc}") from exc


def parse_split_manifest(payload: dict[str, Any]) -> SplitManifest:
    """Validate a payload as a :class:`SplitManifest`."""
    try:
        return SplitManifest.model_validate(payload)
    except ValidationError as exc:
        raise ManifestValidationError(f"Invalid split manifest: {exc}") from exc


def verify_manifests(source_payload: dict[str, Any], split_payload: dict[str, Any]) -> None:
    """Cross-validate source and split manifests offline.

    Verifies each manifest's schema and hash, that the source availability range
    covers every split boundary date, and that the final-test split is sealed.

    Args:
        source_payload: Loaded source-manifest dictionary.
        split_payload: Loaded split-manifest dictionary.

    Raises:
        ManifestValidationError: If any check fails.
    """
    verify_manifest_hash(source_payload)
    verify_manifest_hash(split_payload)
    source = parse_source_manifest(source_payload)
    split = parse_split_manifest(split_payload)

    if split.final_test_access_status != "sealed":
        raise ManifestValidationError("Split manifest final_test_access_status must be 'sealed'.")

    all_ranges = [
        *source.underlying.schema_ranges.values(),
        *source.options.schema_ranges.values(),
    ]
    if not all_ranges:
        raise ManifestValidationError("Source manifest has no available schema ranges.")

    # Every required schema must cover the splits, so use the range intersection.
    intersection_start = max(r.start_date for r in all_ranges)
    intersection_end = min(r.end_date for r in all_ranges)
    if split.training_start < intersection_start or split.test_end > intersection_end:
        raise ManifestValidationError(
            "Source availability does not cover all split dates: "
            f"splits [{split.training_start}, {split.test_end}] vs "
            f"source intersection [{intersection_start}, {intersection_end}]."
        )
