"""Typer subcommands for market-data contracts, splits, and qualification."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv
from jsonschema.exceptions import SchemaError
from jsonschema.protocols import Validator
from jsonschema.validators import Draft202012Validator
from pydantic import BaseModel

from neuralmarket.core.configuration import ConfigurationError, config_sha256
from neuralmarket.core.environment import _git_commit, _git_dirty, find_repository_root
from neuralmarket.core.logging import configure_logging, get_logger
from neuralmarket.data.calendar import compute_splits, session_dates
from neuralmarket.data.configuration import DataConfig, load_data_config
from neuralmarket.data.contracts import CONTRACT_MODELS, json_schema_for
from neuralmarket.data.errors import (
    CoverageError,
    CredentialMissingError,
    ManifestValidationError,
    MarketDataError,
)
from neuralmarket.data.manifests import (
    DateRange,
    build_source_manifest,
    build_split_manifest,
    canonical_summary_hash,
    load_manifest,
    parse_source_manifest,
    parse_split_manifest,
    verify_manifests,
    write_manifest,
)
from neuralmarket.data.redaction import redact
from neuralmarket.data.sources.base import (
    CostPeriod,
    QualificationResult,
    QualificationStatus,
)
from neuralmarket.data.sources.databento import DatabentoSource

_logger = get_logger(__name__)

app = typer.Typer(help="Market-data contracts, splits, and source qualification.")

_CONTRACT_DIR = "data_contracts"

# Fixtures validated against derived JSON Schemas by `data contracts validate`.
_FIXTURE_FILES = {
    "underlying_daily": "underlying_daily_valid.json",
    "underlying_quote_snapshot": "underlying_quote_valid.json",
    "option_definition": "option_definition_valid.json",
    "option_quote_snapshot": "option_quote_valid.json",
}

# Documented outcomes of the two earlier, rejected underlying-source attempts.
_REJECTED_ATTEMPTS = [
    {
        "name": "EQUS.SUMMARY",
        "dataset": "EQUS.SUMMARY",
        "schema": "ohlcv-1d",
        "available_start": "2024-07-01",
        "outcome": "failed_coverage",
        "root_failure": "insufficient historical coverage",
        "data_request": False,
        "downloaded_records": 0,
        "detail": "EQUS.SUMMARY / ohlcv-1d history began 2024-07-01; no records downloaded.",
    },
    {
        "name": "EQUS.MINI",
        "dataset": "EQUS.MINI",
        "schema": "ohlcv-1d",
        "available_start": "2023-03-28",
        "outcome": "failed_coverage",
        "root_failure": "insufficient historical coverage",
        "data_request": False,
        "downloaded_records": 0,
        "detail": "EQUS.MINI schemas began 2023-03-28; no records downloaded.",
    },
    {
        "name": "DBEQ.BASIC",
        "dataset": "DBEQ.BASIC",
        "schema": "bbo-1m",
        "available_start": "2023-03-28",
        "outcome": "failed_schema",
        "root_failure": "required bbo-1m schema unavailable",
        "data_request": False,
        "downloaded_records": 0,
        "detail": (
            "DBEQ.BASIC lacked bbo-1m and history began 2023-03-28; coverage was not "
            "executed after the earlier schema gate; no records downloaded."
        ),
    },
    {
        "name": "ARCX.PILLAR attempt 1",
        "dataset": "ARCX.PILLAR",
        "schema": "symbology",
        "timestamp": "2026-07-12T06:44:29.011712+00:00",
        "outcome": "failed_internal_validation",
        "root_failure": "incorrect inclusive/end-exclusive symbology handling",
        "data_request": False,
        "downloaded_records": 0,
        "detail": (
            "Coverage and publisher checks passed; Stage D diagnostics were incomplete and "
            "no records were downloaded."
        ),
    },
    {
        "name": "ARCX.PILLAR attempt 2",
        "dataset": "ARCX.PILLAR",
        "schema": "symbology",
        "outcome": "failed_internal_validation",
        "root_failure": "status-zero parser defect and opaque OPRA parent-selector error",
        "data_request": False,
        "downloaded_records": 0,
        "detail": (
            "Interval handling was corrected but a status parser rejected the successful "
            "ARCX status 0, and the OPRA parent request produced an opaque error before "
            "normalization; no records were downloaded."
        ),
    },
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load_dotenv(root: Path) -> None:
    """Load repository-root ``.env`` via python-dotenv without overriding the process env.

    Precedence is process environment > ``.env`` > defaults (``override=False``).
    Quoted values, whitespace, and comments are handled by python-dotenv. Values
    are never logged.
    """
    load_dotenv(dotenv_path=root / ".env", override=False)


def _git_meta(root: Path) -> tuple[str | None, bool | None]:
    return _git_commit(root), _git_dirty(root)


def _all_models() -> dict[str, type[BaseModel]]:
    from neuralmarket.data.manifests import SourceManifest, SplitManifest

    models: dict[str, type[BaseModel]] = dict(CONTRACT_MODELS)
    models["source_manifest"] = SourceManifest
    models["split_manifest"] = SplitManifest
    return models


@app.callback()
def _root() -> None:
    """Market-data commands."""


@app.command("contracts")
def contracts(action: str = typer.Argument(..., help="Action to perform (validate).")) -> None:
    """Validate canonical contract schemas and their agreement with typed models."""
    configure_logging("INFO")
    if action != "validate":
        _logger.error("Unknown contracts action: %s", action)
        raise typer.Exit(code=2)

    root = find_repository_root()
    contract_dir = root / _CONTRACT_DIR
    failures: list[str] = []

    for name, model in _all_models().items():
        derived = json_schema_for(model)
        try:
            Draft202012Validator.check_schema(derived)
        except SchemaError as exc:
            failures.append(f"{name}: derived schema is not a valid JSON Schema: {exc}")
            continue
        committed_path = contract_dir / f"{name}.schema.json"
        if not committed_path.is_file():
            failures.append(f"{name}: committed schema file is missing.")
            continue
        committed = json.loads(committed_path.read_text(encoding="utf-8"))
        if committed != derived:
            failures.append(f"{name}: committed schema diverges from the typed model.")

    failures.extend(_validate_fixtures(root))

    if failures:
        for failure in failures:
            _logger.error("Contract validation failure: %s", failure)
        raise typer.Exit(code=1)
    typer.echo(json.dumps({"status": "ok", "contracts": sorted(_all_models())}, sort_keys=True))


def _validate_fixtures(root: Path) -> list[str]:
    failures: list[str] = []
    fixture_dir = root / "tests" / "fixtures" / "data"
    for name, filename in _FIXTURE_FILES.items():
        path = fixture_dir / filename
        if not path.is_file():
            continue
        validator: Validator = Draft202012Validator(json_schema_for(CONTRACT_MODELS[name]))
        for row in json.loads(path.read_text(encoding="utf-8")):
            errors = sorted(validator.iter_errors(row), key=str)
            if errors:
                failures.append(f"{name} fixture row failed JSON Schema: {errors[0].message}")
    return failures


@app.command("split")
def split(
    action: str = typer.Argument(..., help="Action to perform (freeze)."),
    config: Path = typer.Option(..., "--config", help="Path to the data configuration YAML."),
    output: Path = typer.Option(..., "--output", help="Path to write the split manifest JSON."),
) -> None:
    """Freeze a deterministic, NYSE-session-aware chronological split manifest."""
    configure_logging("INFO")
    if action != "freeze":
        _logger.error("Unknown split action: %s", action)
        raise typer.Exit(code=2)
    try:
        data_config = load_data_config(config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc

    root = find_repository_root()
    try:
        sessions = session_dates(
            data_config.study.calendar,
            data_config.study.start_date,
            data_config.study.end_date,
        )
        result = compute_splits(data_config, sessions)
    except CoverageError as exc:
        _logger.error("Split computation failed: %s", exc)
        raise typer.Exit(code=1) from exc

    commit, _ = _git_meta(root)
    payload = build_split_manifest(
        data_config,
        result,
        config_hash=config_sha256(config),
        git_commit=commit,
        generated_at=_now(),
    )
    write_manifest(output, payload)
    parse_split_manifest(payload)
    _logger.info(
        "Split frozen: train %s..%s, val %s..%s, test %s..%s (sealed)",
        result.training_start,
        result.training_end,
        result.validation_start,
        result.validation_end,
        result.test_start,
        result.test_end,
    )
    typer.echo(json.dumps({"manifest_hash": payload["manifest_hash"], "output": str(output)}))


@app.command("qualify")
def qualify(
    config: Path = typer.Option(..., "--config", help="Path to the data configuration YAML."),
    output: Path = typer.Option(
        ..., "--output", help="Path to write the local qualification report."
    ),
    source_manifest: Path = typer.Option(
        ..., "--source-manifest", help="Path to write the tracked source manifest."
    ),
) -> None:
    """Qualify the configured source using metadata-only requests (needs a credential)."""
    configure_logging("INFO")
    try:
        data_config = load_data_config(config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc

    root = find_repository_root()
    _load_dotenv(root)
    try:
        source = DatabentoSource.from_env()
        result = source.qualify_source(data_config)
    except CredentialMissingError as exc:
        _logger.error("%s", redact(str(exc)))
        raise typer.Exit(code=2) from exc
    except MarketDataError as exc:
        _logger.error("Qualification failed: %s", redact(str(exc)))
        raise typer.Exit(code=1) from exc

    commit, dirty = _git_meta(root)
    qualified_at = _now()
    report = _qualification_report(data_config, result, config, commit, dirty, qualified_at)
    write_manifest(output, report)

    if result.status is QualificationStatus.QUALIFIED:
        manifest = _build_source_manifest(data_config, result, config, commit, qualified_at, _now())
        write_manifest(source_manifest, manifest)
        parse_source_manifest(manifest)
        _logger.info("Source qualified; manifest written to %s", source_manifest)
        typer.echo(json.dumps({"status": result.status.value, "report": str(output)}))
        return

    for failure in result.blocking_failures:
        _logger.error("Blocking qualification failure: %s", redact(failure))
    typer.echo(json.dumps({"status": result.status.value, "report": str(output)}))
    raise typer.Exit(code=1)


def _ranges_for(result: QualificationResult, dataset: str) -> dict[str, DateRange]:
    ranges: dict[str, DateRange] = {}
    for cov in result.coverage_results:
        if cov.dataset == dataset and cov.available_start and cov.available_end:
            ranges[f"{cov.dataset}/{cov.schema}"] = DateRange(
                start_date=cov.available_start, end_date=cov.available_end
            )
    return ranges


def _resolution_text(result: QualificationResult, symbol: str) -> str:
    for res in result.symbol_resolutions:
        if res.symbol == symbol:
            return res.detail
    return "not evaluated"


def _options_resolution_text(result: QualificationResult) -> str:
    sel = result.parent_selector
    if sel is None:
        return "not evaluated"
    if sel.resolved:
        return (
            f"parent selector expanded to active SPY children on every market "
            f"session across {sel.chunk_count} monthly chunks"
        )
    return f"parent selector failed: {sel.failure_reason}"


def _parent_selector_summary(result: QualificationResult) -> dict[str, Any]:
    """Build the account-neutral aggregate summary with a canonical hash."""
    sel = result.parent_selector
    if sel is None:
        raise MarketDataError("Cannot summarize an absent parent-selector resolution.")
    summary: dict[str, Any] = {
        "validation_method": sel.validation_method,
        "chunk_count": sel.chunk_count,
        "successful_chunk_count": sel.successful_chunk_count,
        "failed_chunk_count": sel.failed_chunk_count,
        "empty_chunk_count": sel.empty_chunk_count,
        "total_mapping_count": sel.total_mapping_count,
        "distinct_output_count": sel.distinct_output_count,
        "distinct_child_symbol_count": sel.distinct_child_symbol_count,
        "session_gap_count": sel.session_gap_count,
        "first_valid_date": sel.first_valid_date.isoformat(),
        "end_exclusive": sel.end_exclusive.isoformat(),
    }
    summary["canonical_summary_hash"] = canonical_summary_hash(summary)
    return summary


def _parent_chunk_detail(result: QualificationResult) -> list[dict[str, Any]]:
    """Per-chunk detail for the ignored local report (no per-child mappings)."""
    sel = result.parent_selector
    if sel is None:
        return []
    return [
        {
            "chunk_start": c.chunk.start.isoformat(),
            "chunk_end_exclusive": c.chunk.end_exclusive.isoformat(),
            "status": c.status,
            "session_count": c.session_count,
            "child_symbol_count": c.child_symbol_count,
            "child_mapping_count": c.child_mapping_count,
            "distinct_instrument_id_count": c.distinct_instrument_id_count,
            "partial_child_count": c.partial_child_count,
            "listing_mid_chunk_count": c.listing_mid_chunk_count,
            "expiring_mid_chunk_count": c.expiring_mid_chunk_count,
            "overlapping_child_count": c.overlapping_child_count,
            "calendar_gap_count": c.calendar_gap_count,
            "uncovered_session_count": len(c.uncovered_sessions),
            "uncovered_sessions": [d.isoformat() for d in c.uncovered_sessions],
            "ok": c.ok,
            "failure_reason": c.failure_reason,
        }
        for c in sel.chunks
    ]


def _provider_diagnostic_json(result: QualificationResult) -> list[dict[str, Any]]:
    return [
        {
            "exception_class": d.exception_class,
            "failure_category": d.failure_category,
            "http_status_code": d.http_status_code,
            "provider_error_code": d.provider_error_code,
            "safe_provider_message": redact(d.safe_provider_message),
            "dataset": d.dataset,
            "input_symbol": d.input_symbol,
            "stype_in": d.stype_in,
            "stype_out": d.stype_out,
            "request_start": d.request_start.isoformat(),
            "request_end_exclusive": d.request_end_exclusive.isoformat(),
            "request_duration_days": d.request_duration_days,
            "operation": d.operation,
        }
        for d in result.provider_diagnostics
    ]


def _range_json(value: Any) -> dict[str, str]:
    return {"start": value.start.isoformat(), "end_exclusive": value.end_exclusive.isoformat()}


def _resolution_json(resolution: Any) -> dict[str, Any]:
    return {
        "dataset": resolution.dataset,
        "input_symbol": resolution.symbol,
        "stype_in": resolution.symbol_type,
        "stype_out": resolution.stype_out,
        "request_start": resolution.requested_range.start.isoformat(),
        "request_end_exclusive": resolution.requested_range.end_exclusive.isoformat(),
        "response_start": resolution.response_range.start.isoformat(),
        "response_end_exclusive": resolution.response_range.end_exclusive.isoformat(),
        "provider_status": resolution.provider_status,
        "provider_message": redact(resolution.provider_message or ""),
        "partial": resolution.partial,
        "not_found": resolution.not_found,
        "mapping_count": resolution.mapping_count,
        "distinct_output_symbol_count": resolution.distinct_output_count,
        "mapping_intervals": [
            {
                "start": interval.start.isoformat(),
                "end_exclusive": interval.end_exclusive.isoformat(),
                "output_symbol": interval.output_symbol,
            }
            for interval in resolution.raw_intervals
        ],
        "merged_coverage_intervals": [
            _range_json(interval) for interval in resolution.merged_intervals
        ],
        "uncovered_intervals": [
            _range_json(interval) for interval in resolution.uncovered_intervals
        ],
        "resolved": resolution.resolved,
        "failure_reason": resolution.failure_reason,
    }


def _build_source_manifest(
    config: DataConfig,
    result: QualificationResult,
    config_path: Path,
    commit: str | None,
    qualified_at: str,
    generated_at: str,
) -> dict[str, Any]:
    pub = result.underlying_publisher
    publisher_json = {
        "publisher_id": pub.publisher_id if pub else 0,
        "venue": pub.venue if pub else "",
        "description": pub.description if pub else "",
    }
    sel = result.parent_selector
    return build_source_manifest(
        config,
        underlying_ranges=_ranges_for(result, config.provider.underlying.dataset),
        options_ranges=_ranges_for(result, config.provider.options.dataset),
        publisher=publisher_json,
        optional_schemas=result.optional_schemas,
        underlying_symbol_resolution=_resolution_text(result, config.provider.underlying.symbol),
        options_symbol_resolution=_options_resolution_text(result),
        options_validation_method=sel.validation_method if sel else "",
        options_selector_summary=_parent_selector_summary(result),
        qualification_status=result.status.value,
        qualification_timestamp=qualified_at,
        config_hash=config_sha256(config_path),
        git_commit=commit,
        generated_at=generated_at,
    )


def _cost_total(result: QualificationResult, datasets: set[str]) -> float | None:
    values = [
        c.cost
        for c in result.cost_estimates
        if c.dataset in datasets and c.period is CostPeriod.FULL_STUDY
    ]
    if not values or any(v is None for v in values):
        return None
    return round(sum(v for v in values if v is not None), 6)


def _qualification_report(
    config: DataConfig,
    result: QualificationResult,
    config_path: Path,
    commit: str | None,
    dirty: bool | None,
    qualified_at: str,
) -> dict[str, Any]:
    stage_d = result.stages["D_symbology"]
    sel = result.parent_selector
    if result.symbol_resolutions and stage_d.value == "not_run_due_to_prior_failure":
        raise MarketDataError("Invalid qualification state: Stage D ran but is marked not run.")
    if stage_d.value == "passed" and any(not item.resolved for item in result.symbol_resolutions):
        raise MarketDataError(
            "Invalid qualification state: Stage D passed with unresolved symbols."
        )
    if stage_d.value == "passed" and (sel is None or not sel.resolved):
        raise MarketDataError(
            "Invalid qualification state: Stage D passed without a resolved parent selector."
        )
    if sel is not None and sel.validation_method != "chunked_symbology_resolution":
        # The metadata_parent_selector_preflight branch is not implemented in this
        # milestone; only chunked direct resolution may ever be reported.
        raise MarketDataError(
            "Invalid qualification state: unsupported OPRA validation method "
            f"'{sel.validation_method}' reported."
        )
    if sel is not None and sel.resolved and sel.chunk_count < 1:
        raise MarketDataError(
            "Invalid qualification state: chunked resolution reported with no chunks."
        )
    if result.status is QualificationStatus.FAILED_SYMBOLOGY and stage_d.value != "failed":
        raise MarketDataError("Invalid qualification state: symbology failed but Stage D did not.")
    underlying_ds = {config.provider.underlying.dataset}
    options_ds = {config.provider.options.dataset}
    combined = underlying_ds | options_ds
    underlying_total = _cost_total(result, underlying_ds)
    options_total = _cost_total(result, options_ds)
    combined_total = _cost_total(result, combined)
    current_attempt = {
        "name": config.provider.underlying.dataset,
        "timestamp": qualified_at,
        "config_hash": config_sha256(config_path),
        "datasets": [config.provider.underlying.dataset, config.provider.options.dataset],
        "schema_ranges": [
            {
                "dataset": c.dataset,
                "schema": c.schema,
                "available_start": c.available_start.isoformat() if c.available_start else None,
                "available_end": c.available_end.isoformat() if c.available_end else None,
            }
            for c in result.coverage_results
        ],
        "outcome": result.status.value,
        "root_status": result.status.value,
        "root_failure": None
        if result.status is QualificationStatus.QUALIFIED
        else result.status.value,
        "data_request": False,
        "downloads_attempted": result.downloads_attempted,
        "downloaded_records": result.downloaded_records,
        "stage_outcomes": {name: status.value for name, status in result.stages.items()},
        "skipped_stages": [
            name
            for name, status in result.stages.items()
            if status.value == "not_run_due_to_prior_failure"
        ],
    }
    pub = result.underlying_publisher
    return {
        "schema_version": "1.0",
        "generated_at": qualified_at,
        "git_commit": commit,
        "git_dirty": dirty,
        "config_hash": config_sha256(config_path),
        "provider": result.provider,
        "study": {
            "start": config.study.start_date.isoformat(),
            "end": config.study.end_date.isoformat(),
        },
        "attempts": [*_REJECTED_ATTEMPTS, current_attempt],
        "stages": {name: status.value for name, status in result.stages.items()},
        "underlying_publisher": {
            "publisher_id": pub.publisher_id if pub else None,
            "venue": pub.venue if pub else None,
            "description": pub.description if pub else None,
        },
        "publishers": [
            {"publisher_id": p.publisher_id, "venue": p.venue, "consolidated": p.consolidated}
            for p in result.publishers
        ],
        "coverage_table": [
            {
                "dataset": c.dataset,
                "schema": c.schema,
                "available_start": c.available_start.isoformat() if c.available_start else None,
                "available_end": c.available_end.isoformat() if c.available_end else None,
                "required_start": c.required_start.isoformat(),
                "required_end": c.required_end.isoformat(),
                "range_semantics": c.range_semantics,
                "covers_start": c.covers_start,
                "covers_end": c.covers_end,
                "covers_complete_window": c.covers_complete_window,
                "coverage_gap_days": c.coverage_gap_days,
                "status": c.status.value,
            }
            for c in result.coverage_results
        ],
        "symbol_resolution": [_resolution_json(s) for s in result.symbol_resolutions],
        "options_parent_selector": {
            "validation_method": sel.validation_method if sel else None,
            "resolved": sel.resolved if sel else None,
            "failure_reason": sel.failure_reason if sel else None,
            "summary": _parent_selector_summary(result) if sel else None,
            "chunk_detail": _parent_chunk_detail(result),
        },
        "provider_diagnostics": _provider_diagnostic_json(result),
        "cost_table": [
            {
                "dataset": c.dataset,
                "schema": c.schema,
                "symbol": c.symbol,
                "symbol_type": c.symbol_type,
                "period": c.period.value,
                "cost": c.cost,
                "currency": c.currency,
                "size_bytes": c.size_bytes,
                "record_count": c.record_count,
                "exact": c.exact,
                "estimate_method": c.estimate_method,
            }
            for c in result.cost_estimates
        ],
        "cost_totals": {
            "underlying_full_study": underlying_total,
            "options_full_study": options_total,
            "combined_full_study": combined_total,
            "currency": result.cost_currency,
        },
        "entitlement_status": result.entitlement_ok,
        "downloads_attempted": result.downloads_attempted,
        "downloaded_records": result.downloaded_records,
        "warnings": [redact(w) for w in result.warnings],
        "optional_schemas": dict(result.optional_schemas),
        "blocking_failures": [redact(b) for b in result.blocking_failures],
        "qualification_status": result.status.value,
    }


@app.command("manifests")
def manifests(
    action: str = typer.Argument(..., help="Action to perform (verify)."),
    source: Path = typer.Option(..., "--source", help="Path to the source manifest JSON."),
    split_path: Path = typer.Option(..., "--split", help="Path to the split manifest JSON."),
) -> None:
    """Verify source and split manifests offline: schemas, hashes, coverage, sealing."""
    configure_logging("INFO")
    if action != "verify":
        _logger.error("Unknown manifests action: %s", action)
        raise typer.Exit(code=2)
    try:
        verify_manifests(load_manifest(source), load_manifest(split_path))
    except ManifestValidationError as exc:
        _logger.error("Manifest verification failed: %s", exc)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps({"status": "ok"}))
