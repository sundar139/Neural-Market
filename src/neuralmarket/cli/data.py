"""Typer subcommands for market-data contracts, splits, and qualification."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
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
from neuralmarket.data.acquisition.authorization import (
    AuthorizationError,
    load_authorization,
    validate_authorization,
)
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.acquisition.configuration import load_acquisition_config
from neuralmarket.data.acquisition.contracts import (
    AcquisitionPlanReport,
    AcquisitionPolicyManifest,
    acquisition_report_to_json,
)
from neuralmarket.data.acquisition.estimation import MetadataEstimator
from neuralmarket.data.acquisition.executor import ExecutorGuardError, PilotExecutor
from neuralmarket.data.acquisition.journal import RequestJournal
from neuralmarket.data.acquisition.manifests import (
    finalize_policy_manifest,
    parse_policy_manifest,
    verify_plan_and_policy,
    verify_policy_hash,
)
from neuralmarket.data.acquisition.manifests import (
    load_json as load_acquisition_json,
)
from neuralmarket.data.acquisition.manifests import (
    write_json as write_acquisition_json,
)
from neuralmarket.data.acquisition.planner import plan_acquisition
from neuralmarket.data.acquisition.preflight import run_preflight
from neuralmarket.data.acquisition.recovery import run_recovery
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    build_pilot_request_plan,
    load_pilot_config,
)
from neuralmarket.data.acquisition.requests import (
    plan_hash as compute_plan_hash,
)
from neuralmarket.data.calendar import compute_splits, session_dates
from neuralmarket.data.configuration import DataConfig, load_data_config
from neuralmarket.data.contracts import CONTRACT_MODELS, json_schema_for
from neuralmarket.data.errors import (
    CoverageError,
    CredentialMissingError,
    ManifestValidationError,
    MarketDataError,
    PlanValidationError,
)
from neuralmarket.data.manifests import (
    DateRange,
    build_source_manifest,
    build_split_manifest,
    canonical_dumps,
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
acquisition_app = typer.Typer(help="Budget-constrained, metadata-only OPRA acquisition planning.")
pilot_app = typer.Typer(help="Guarded pilot data acquisition: prepare, verify, execute, recover.")
app.add_typer(acquisition_app, name="acquisition")
app.add_typer(pilot_app, name="pilot")

_DEFAULT_REQUEST_MANIFEST = Path("data/manifests/pilot_request_plan_v1.json")
_DEFAULT_SOURCE_MANIFEST = Path("data/manifests/source_manifest_v1.json")
_DEFAULT_SPLIT_MANIFEST = Path("data/manifests/split_manifest_v1.json")
_DEFAULT_POLICY_MANIFEST = Path("data/manifests/acquisition_policy_v1.json")
_DEFAULT_JOURNAL_PATH = Path("data/state/pilot_acquisition_journal.sqlite")
_PILOT_REQUEST_PLAN_SCHEMA = "data_contracts/pilot_request_plan.schema.json"
_HARD_PILOT_SPEND_CAP_USD = Decimal("5.00")

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
    models["acquisition_policy"] = AcquisitionPolicyManifest
    models["acquisition_plan"] = AcquisitionPlanReport
    return models


def _raw_databento_client() -> Any:
    """Build an unwrapped Databento client from ``DATABENTO_API_KEY``.

    The acquisition planner applies its own metadata-only guard, so this
    returns the raw provider client rather than a :class:`DatabentoSource`.

    Raises:
        CredentialMissingError: If the API key is not set.
    """
    import os

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise CredentialMissingError(
            "DATABENTO_API_KEY is not set; add it to a local .env to plan acquisition."
        )
    import databento

    return databento.Historical(key)


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


@acquisition_app.command("plan")
def acquisition_plan(
    config: Path = typer.Option(
        ..., "--config", help="Path to the acquisition-planning configuration YAML."
    ),
    source_manifest: Path = typer.Option(
        ..., "--source-manifest", help="Path to the accepted source manifest JSON."
    ),
    split_manifest: Path = typer.Option(
        ..., "--split-manifest", help="Path to the accepted split manifest JSON."
    ),
    output: Path = typer.Option(
        ..., "--output", help="Path to write the local acquisition plan report."
    ),
    policy_manifest: Path = typer.Option(
        ..., "--policy-manifest", help="Path to write the tracked acquisition policy manifest."
    ),
) -> None:
    """Plan budget-constrained OPRA acquisition using metadata-only requests.

    Never downloads, batches, or streams market records, and never authorizes
    a purchase.
    """
    configure_logging("INFO")
    try:
        acq_config = load_acquisition_config(config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc

    root = find_repository_root()
    _load_dotenv(root)
    try:
        client = _raw_databento_client()
    except CredentialMissingError as exc:
        _logger.error("%s", redact(str(exc)))
        raise typer.Exit(code=2) from exc

    try:
        report, policy_raw = plan_acquisition(
            client=client,
            config=acq_config,
            source_manifest_path=source_manifest,
            split_manifest_path=split_manifest,
            config_path=config,
            repo_root=root,
        )
    except (PlanValidationError, MarketDataError) as exc:
        _logger.error("Acquisition planning failed: %s", redact(str(exc)))
        raise typer.Exit(code=1) from exc

    policy_payload = finalize_policy_manifest(policy_raw)
    parse_policy_manifest(policy_payload)
    write_acquisition_json(output, acquisition_report_to_json(report))
    write_acquisition_json(policy_manifest, policy_payload)

    typer.echo(
        json.dumps(
            {
                "recommendation_status": report.recommendation_status,
                "recommended_strategy_id": report.recommended_strategy_id,
                "report": str(output),
                "policy_manifest": str(policy_manifest),
            }
        )
    )
    if report.recommendation_status != "recommended_not_authorized":
        raise typer.Exit(code=1)


@acquisition_app.command("verify")
def acquisition_verify(
    plan: Path = typer.Option(..., "--plan", help="Path to the local acquisition plan report."),
    policy_manifest: Path = typer.Option(
        ..., "--policy-manifest", help="Path to the tracked acquisition policy manifest."
    ),
) -> None:
    """Verify an acquisition plan and policy manifest offline: hashes, budget, agreement."""
    configure_logging("INFO")
    try:
        plan_payload = load_acquisition_json(plan)
        policy_payload = load_acquisition_json(policy_manifest)
        verify_plan_and_policy(plan_payload, policy_payload)
    except PlanValidationError as exc:
        _logger.error("Acquisition verification failed: %s", exc)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps({"status": "ok"}))


def _ordered_waves(requests: list[AcquisitionRequest]) -> list[str]:
    """Return the distinct wave names in first-occurrence (plan) order."""
    seen: list[str] = []
    for request in requests:
        if request.wave not in seen:
            seen.append(request.wave)
    return seen


def _pilot_request_manifest_json(request: AcquisitionRequest) -> dict[str, Any]:
    """Render one request for the tracked manifest.

    The contract schema requires the key ``estimated_cost_usd``; the model
    field is ``estimated_cost`` (no alias), so it is renamed here rather than
    in the frozen model itself. The value is left as the request's own
    (placeholder) ``estimated_cost`` -- the same value ``plan_hash`` was
    computed over -- so the manifest can always re-verify its own plan_hash.
    Freshly preflighted per-request costs live in the local preflight report;
    the refreshed aggregate is surfaced here via ``estimated_total_cost_usd``.
    """
    payload = request.model_dump(mode="json", by_alias=True)
    payload["estimated_cost_usd"] = payload.pop("estimated_cost")
    return payload


def _validate_pilot_request_plan_schema(root: Path, payload: dict[str, Any]) -> None:
    schema = json.loads((root / _PILOT_REQUEST_PLAN_SCHEMA).read_text(encoding="utf-8"))
    validator: Validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=str)
    if errors:
        raise MarketDataError(
            f"Pilot request-plan manifest failed schema validation: {errors[0].message}"
        )


def _pilot_manifest_sort_key(request_json: dict[str, Any]) -> tuple[Any, ...]:
    return (
        request_json.get("wave", ""),
        request_json.get("dataset", ""),
        request_json.get("schema", ""),
        request_json.get("session_date") or "0001-01-01",
        tuple(request_json.get("symbols", ())),
    )


def _recompute_pilot_plan_hash(manifest_payload: dict[str, Any]) -> str:
    """Recompute the pilot ``plan_hash`` directly from a written manifest's contents.

    Mirrors ``requests.plan_hash()``'s canonicalization exactly, but operates on
    the manifest's own stored request dicts (which use the schema's
    ``estimated_cost_usd`` key) instead of reconstructing ``AcquisitionRequest``
    objects, so a manifest can verify itself without a lossy round-trip.
    """
    ordered = sorted(manifest_payload.get("requests", []), key=_pilot_manifest_sort_key)
    reconstructed = []
    for item in ordered:
        reduced = dict(item)
        reduced["estimated_cost"] = reduced.pop("estimated_cost_usd")
        reconstructed.append(reduced)
    canonical = canonical_dumps({"requests": reconstructed})
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_under_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _manifest_hash_or_empty(path: Path) -> str:
    try:
        value = load_manifest(path).get("manifest_hash")
    except ManifestValidationError:
        return ""
    return value if isinstance(value, str) else ""


@pilot_app.command("prepare")
def pilot_prepare(
    config: Path = typer.Option(..., "--config", help="Path to the pilot-execution YAML config."),
    output: Path = typer.Option(
        ..., "--output", help="Path to write the local pilot preflight report."
    ),
    request_manifest: Path = typer.Option(
        _DEFAULT_REQUEST_MANIFEST,
        "--request-manifest",
        help="Path to write the tracked pilot request-plan manifest.",
    ),
) -> None:
    """Build the deterministic pilot request plan and cost-preflight it.

    Never downloads, batches, or streams market records, and never authorizes
    a purchase: the written manifest and report always report
    ``purchase_authorized: false`` with zero download/batch/live attempts.
    """
    configure_logging("INFO")
    try:
        pilot_config = load_pilot_config(config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc

    root = find_repository_root()
    _load_dotenv(root)
    try:
        client = _raw_databento_client()
    except CredentialMissingError as exc:
        _logger.error("%s", redact(str(exc)))
        raise typer.Exit(code=2) from exc

    try:
        requests = build_pilot_request_plan(pilot_config)
    except ValueError as exc:
        _logger.error("Pilot request-plan generation failed: %s", exc)
        raise typer.Exit(code=1) from exc

    phash = compute_plan_hash(requests)
    estimator = MetadataEstimator(client)
    try:
        result = run_preflight(estimator=estimator, requests=requests, config=pilot_config)
    except MarketDataError as exc:
        _logger.error("Pilot preflight failed: %s", redact(str(exc)))
        raise typer.Exit(code=1) from exc

    generated_at = _now()
    manifest_payload: dict[str, Any] = {
        "plan_hash": phash,
        "generated_at": generated_at,
        "waves": _ordered_waves(requests),
        "requests": [_pilot_request_manifest_json(r) for r in requests],
        "estimated_total_cost_usd": result.fresh_total_usd,
        "maximum_allowed_total_usd": str(pilot_config.maximum_spend_usd),
        "purchase_authorized": False,
    }
    try:
        _validate_pilot_request_plan_schema(root, manifest_payload)
    except MarketDataError as exc:
        _logger.error("%s", exc)
        raise typer.Exit(code=1) from exc

    write_acquisition_json(request_manifest, manifest_payload)

    report_payload = {
        "generated_at": generated_at,
        "plan_hash": phash,
        "config_hash": config_sha256(config),
        "preflight": json.loads(result.model_dump_json()),
        "purchase_authorized": False,
        "download_attempts": 0,
        "batch_jobs_submitted": 0,
        "live_connections_opened": 0,
        "request_manifest": str(request_manifest),
    }
    write_acquisition_json(output, report_payload)

    typer.echo(
        json.dumps(
            {
                "plan_hash": phash,
                "passed": result.passed,
                "fresh_total_usd": result.fresh_total_usd,
                "purchase_authorized": False,
                "download_attempts": 0,
                "batch_jobs_submitted": 0,
                "live_connections_opened": 0,
                "request_manifest": str(request_manifest),
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    if not result.passed or to_decimal(result.fresh_total_usd) > _HARD_PILOT_SPEND_CAP_USD:
        raise typer.Exit(code=1)


@pilot_app.command("verify")
def pilot_verify(
    request_manifest: Path = typer.Option(
        ..., "--request-manifest", help="Path to the tracked pilot request-plan manifest."
    ),
    authorization_template: Path = typer.Option(
        ...,
        "--authorization-template",
        help="Path to a pilot authorization artifact/template, confirmed to be rejected.",
    ),
    source_manifest: Path = typer.Option(
        _DEFAULT_SOURCE_MANIFEST, "--source-manifest", help="Path to the accepted source manifest."
    ),
    split_manifest: Path = typer.Option(
        _DEFAULT_SPLIT_MANIFEST, "--split-manifest", help="Path to the accepted split manifest."
    ),
    policy_manifest: Path = typer.Option(
        _DEFAULT_POLICY_MANIFEST,
        "--policy-manifest",
        help="Path to the tracked acquisition policy manifest.",
    ),
) -> None:
    """Verify the pilot request plan and authorization template fully offline.

    Never constructs a Databento client and never makes a network call: this
    command only reads and re-hashes local JSON files.
    """
    configure_logging("INFO")
    try:
        plan_payload = load_acquisition_json(request_manifest)
    except PlanValidationError as exc:
        _logger.error("Pilot request-plan manifest could not be read: %s", exc)
        raise typer.Exit(code=1) from exc

    stored_plan_hash = plan_payload.get("plan_hash")
    recomputed_plan_hash = _recompute_pilot_plan_hash(plan_payload)
    if stored_plan_hash != recomputed_plan_hash:
        _logger.error(
            "Pilot request-plan manifest plan_hash does not match its own contents (tampered)."
        )
        raise typer.Exit(code=1)

    template_usable_for_execution = False
    authorization_rejection_reason: str | None = None
    try:
        auth = load_authorization(authorization_template)
        validate_authorization(
            auth,
            expected_plan_hash=str(stored_plan_hash or ""),
            expected_source_manifest_hash=_manifest_hash_or_empty(source_manifest),
            expected_split_manifest_hash=_manifest_hash_or_empty(split_manifest),
            expected_acquisition_policy_hash=_manifest_hash_or_empty(policy_manifest),
            now=datetime.now(UTC),
            consumed_ids=set(),
        )
        template_usable_for_execution = True
    except AuthorizationError as exc:
        authorization_rejection_reason = exc.reason
    except Exception as exc:  # fail closed: any parse/schema/model failure rejects the template
        authorization_rejection_reason = f"unparseable: {exc}"

    try:
        verify_manifests(load_manifest(source_manifest), load_manifest(split_manifest))
        policy_payload = load_acquisition_json(policy_manifest)
        verify_policy_hash(policy_payload)
        parse_policy_manifest(policy_payload)
    except (ManifestValidationError, PlanValidationError) as exc:
        _logger.error("Manifest verification failed: %s", exc)
        raise typer.Exit(code=1) from exc

    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "plan_hash_verified": True,
                "template_usable_for_execution": template_usable_for_execution,
                "authorization_rejection_reason": authorization_rejection_reason,
            },
            sort_keys=True,
        )
    )


@pilot_app.command("execute")
def pilot_execute(
    plan: Path = typer.Option(
        ..., "--plan", help="Path to the tracked pilot request-plan manifest."
    ),
    authorization: Path = typer.Option(
        ..., "--authorization", help="Path to the signed pilot authorization artifact."
    ),
    confirm_plan_hash: str = typer.Option(
        ...,
        "--confirm-plan-hash",
        help="Operator-confirmed plan hash; must exactly match the plan under review.",
    ),
    source_manifest: Path = typer.Option(
        _DEFAULT_SOURCE_MANIFEST, "--source-manifest", help="Path to the accepted source manifest."
    ),
    split_manifest: Path = typer.Option(
        _DEFAULT_SPLIT_MANIFEST, "--split-manifest", help="Path to the accepted split manifest."
    ),
    policy_manifest: Path = typer.Option(
        _DEFAULT_POLICY_MANIFEST,
        "--policy-manifest",
        help="Path to the tracked acquisition policy manifest.",
    ),
    journal_path: Path = typer.Option(
        _DEFAULT_JOURNAL_PATH,
        "--journal",
        help="Path to the pilot acquisition journal SQLite file.",
    ),
) -> None:
    """Attempt guarded pilot execution. Structurally cannot succeed in this milestone.

    Both money guards (a valid, single-use authorization artifact and an
    explicit plan-hash confirmation) are enforced by
    :meth:`PilotExecutor.guard_execute` before any paid provider could ever be
    constructed. Even in the hypothetical case both guards passed, the
    ``paid_provider_factory`` injected here always raises
    ``NotImplementedError``: no real Databento paid client exists anywhere in
    this codebase yet.
    """
    configure_logging("INFO")
    try:
        plan_payload = load_acquisition_json(plan)
    except PlanValidationError as exc:
        _logger.error("Pilot request-plan manifest could not be read: %s", exc)
        raise typer.Exit(code=1) from exc

    plan_hash_value = plan_payload.get("plan_hash")
    if not isinstance(plan_hash_value, str):
        _logger.error("Pilot request-plan manifest is missing a string plan_hash.")
        raise typer.Exit(code=1)

    root = find_repository_root()
    journal_full_path = _resolve_under_root(root, journal_path)
    journal_full_path.parent.mkdir(parents=True, exist_ok=True)

    def _unreachable_paid_provider_factory() -> Any:
        # No real Databento paid client exists anywhere in this codebase yet;
        # this milestone permits metadata-only planning, never a live purchase.
        raise NotImplementedError("live Databento execution is out of scope for this milestone")

    with RequestJournal(journal_full_path) as journal:
        executor = PilotExecutor(journal=journal, metadata_estimator=MetadataEstimator(object()))
        try:
            executor.guard_execute(
                plan_hash=plan_hash_value,
                authorization_path=authorization,
                confirm_plan_hash=confirm_plan_hash,
                source_manifest_hash=_manifest_hash_or_empty(source_manifest),
                split_manifest_hash=_manifest_hash_or_empty(split_manifest),
                acquisition_policy_hash=_manifest_hash_or_empty(policy_manifest),
                now=datetime.now(UTC),
                paid_provider_factory=_unreachable_paid_provider_factory,
            )
        except ExecutorGuardError as exc:
            message = f"Pilot execution blocked: authorization guard rejected ({exc.reason}): {exc}"
            _logger.error(message)
            typer.echo(message, err=True)
            raise typer.Exit(code=1) from exc

    # Unreachable in this milestone: no code path lets both guards pass, and
    # the paid_provider_factory above always raises NotImplementedError.
    typer.echo(json.dumps({"status": "unexpectedly_executed"}, sort_keys=True))


@pilot_app.command("recover")
def pilot_recover(
    plan: Path = typer.Option(
        ..., "--plan", help="Path to the pilot request-plan manifest (read for context only)."
    ),
    output: Path = typer.Option(
        ..., "--output", help="Path to write the local, read-only recovery report."
    ),
    journal_path: Path = typer.Option(
        _DEFAULT_JOURNAL_PATH,
        "--journal",
        help="Path to the pilot acquisition journal SQLite file.",
    ),
    data_root: Path | None = typer.Option(
        None,
        "--data-root",
        help="Root directory to scan for raw/partial files (defaults to the repository root).",
    ),
) -> None:
    """Offline, read-only recovery inspection. Never retries or deletes anything.

    Delegates entirely to :func:`run_recovery`, which only reads the journal
    and filesystem: it never mutates the journal and never deletes or renames
    anything on disk, including stale ``.partial`` files.
    """
    configure_logging("INFO")
    try:
        load_acquisition_json(plan)
    except PlanValidationError as exc:
        _logger.error("Pilot request-plan manifest could not be read: %s", exc)
        raise typer.Exit(code=1) from exc

    root = find_repository_root()
    journal_full_path = _resolve_under_root(root, journal_path)
    journal_full_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_data_root = data_root if data_root is not None else root

    with RequestJournal(journal_full_path) as journal:
        report = run_recovery(journal=journal, data_root=resolved_data_root)

    write_acquisition_json(output, json.loads(report.model_dump_json()))
    typer.echo(
        json.dumps(
            {"retried": report.retried, "deleted": report.deleted, "output": str(output)},
            sort_keys=True,
        )
    )
