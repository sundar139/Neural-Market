"""Typer subcommands for market-data contracts, splits, and qualification."""

from __future__ import annotations

import hashlib
import hmac
import importlib.metadata
import json
import subprocess
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import typer
from dotenv import load_dotenv
from jsonschema.exceptions import SchemaError
from jsonschema.protocols import Validator
from jsonschema.validators import Draft202012Validator
from pydantic import BaseModel

from neuralmarket.core.configuration import ConfigurationError, config_sha256
from neuralmarket.core.environment import _git_commit, _git_dirty, find_repository_root
from neuralmarket.core.logging import configure_logging, get_logger
from neuralmarket.data.acquisition.attestation import (
    PortalAttestationError,
    load_portal_attestation,
    validate_portal_attestation,
)
from neuralmarket.data.acquisition.authorization import (
    AuthorizationError,
    load_authorization,
    validate_authorization,
)
from neuralmarket.data.acquisition.billing_reconciliation import (
    BillingReconciliationError,
    apply_billing_reconciliation,
    load_reconciliation_artifact,
)
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.acquisition.checkpoint_compatibility import (
    is_pilot_config_hash_compatible,
    is_valid_sha256,
)
from neuralmarket.data.acquisition.configuration import load_acquisition_config
from neuralmarket.data.acquisition.contracts import (
    AcquisitionPlanReport,
    AcquisitionPolicyManifest,
    acquisition_report_to_json,
)
from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.executor import (
    ExecutorGuardError,
    LifecycleHooks,
    PilotExecutionCoordinator,
    RawAcquisitionResult,
)
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
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
from neuralmarket.data.acquisition.metadata_runner import (
    Endpoint,
    MetadataCheckpoint,
    MetadataEndpointResult,
    MetadataOperationEvent,
    UnitPriceSnapshotCache,
    build_provider_cost_samples,
    checkpoint_client_version,
    cost_fallback_trigger,
    derive_cost_endpoint_result,
    endpoint_response_hash,
    load_checkpoint,
    plan_cost_rollup,
    run_isolated_metadata_request,
    run_isolated_unit_price_request,
    write_checkpoint,
)
from neuralmarket.data.acquisition.planner import plan_acquisition
from neuralmarket.data.acquisition.preflight import PreflightResult
from neuralmarket.data.acquisition.providers import (
    DatabentoMetadataProvider,
    create_databento_paid_provider,
    paid_provider_readiness,
)
from neuralmarket.data.acquisition.recovery import RecoveryReport, run_recovery
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    build_pilot_request_plan,
    finalize_request,
    load_pilot_config,
    verify_final_request,
)
from neuralmarket.data.acquisition.requests import (
    plan_hash as compute_plan_hash,
)
from neuralmarket.data.acquisition.storage import validate_logical_path
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
    canonical_summary_hash,
    load_manifest,
    parse_source_manifest,
    parse_split_manifest,
    verify_manifests,
    write_manifest,
)
from neuralmarket.data.normalization.parquet import normalize_dbn_store_to_parquet
from neuralmarket.data.normalization.provenance import provenance_columns_for
from neuralmarket.data.raw.integrity import verify_checksum
from neuralmarket.data.redaction import redact
from neuralmarket.data.sources.base import (
    CostPeriod,
    QualificationResult,
    QualificationStatus,
)
from neuralmarket.data.sources.databento import DatabentoSource

_logger = get_logger(__name__)

_run_isolated_metadata = run_isolated_metadata_request

#: Single-account pricing context bound to the pilot's derived cross-validation.
_PILOT_ACCOUNT_PRICING_CONTEXT = "pilot-databento-historical-v1"
#: Unit-price snapshot freshness for a single preflight generation.
_UNIT_PRICE_SNAPSHOT_TTL_MINUTES = 30


def _pilot_unit_price_snapshot_loader(dataset: str) -> Any:
    """Load one dataset's unit-price snapshot through the isolated child boundary.

    Never invoked in metadata-free runs; overridable seam for fake injection.
    """
    now = datetime.now(UTC)
    result = run_isolated_unit_price_request(
        dataset=dataset,
        client_version=checkpoint_client_version(),
        retrieved_at_utc=now.isoformat(),
        expires_at_utc=(now + timedelta(minutes=_UNIT_PRICE_SNAPSHOT_TTL_MINUTES)).isoformat(),
        timeout_seconds=120.0,
    )
    if result.snapshot is None:
        raise MarketDataError(f"unit-price snapshot unavailable: {result.failure_type}")
    return result.snapshot


def _maybe_derive_cost_fallback(
    *,
    request: AcquisitionRequest,
    endpoint: Endpoint,
    isolated: Any,
    state: MetadataCheckpoint,
    request_results: dict[Endpoint, MetadataEndpointResult],
    snapshot_cache: UnitPriceSnapshotCache,
) -> MetadataEndpointResult | None:
    """Attempt a fail-closed derived cost after a bounded provider get_cost failure.

    Returns a completed derived cost endpoint result, or ``None`` when the
    failure is ineligible or the evidence is incompatible (caller then fails
    closed exactly as before). Only reached after get_cost exhausts its attempts.
    """
    if endpoint != "cost":
        return None
    trigger = cost_fallback_trigger(isolated)
    if trigger is None:
        return None
    billable = request_results.get("billable-size")
    if billable is None:
        return None
    http_status, category = trigger
    try:
        samples = build_provider_cost_samples(
            state,
            dataset=request.dataset,
            schema=request.schema_name,
            feed_mode="historical-streaming",
            account_pricing_context=_PILOT_ACCOUNT_PRICING_CONTEXT,
        )
        snapshot = snapshot_cache.get(request.dataset)
        return derive_cost_endpoint_result(
            request=request,
            billable_size_result=billable,
            snapshot=snapshot,
            samples=samples,
            account_pricing_context=_PILOT_ACCOUNT_PRICING_CONTEXT,
            failure_http_status=http_status,
            failure_category=category,
            now_utc=datetime.now(UTC).isoformat(),
        )
    except MarketDataError as exc:
        _logger.warning("Derived cost fallback declined for %s: %s", request.request_id, exc)
        return None


app = typer.Typer(help="Market-data contracts, splits, and source qualification.")
acquisition_app = typer.Typer(help="Budget-constrained, metadata-only OPRA acquisition planning.")
pilot_app = typer.Typer(help="Guarded pilot data acquisition: prepare, verify, execute, recover.")
app.add_typer(acquisition_app, name="acquisition")
app.add_typer(pilot_app, name="pilot")

_DEFAULT_REQUEST_MANIFEST = Path("data/manifests/pilot_request_plan_v1.json")
_DEFAULT_SOURCE_MANIFEST = Path("data/manifests/source_manifest_v1.json")
_DEFAULT_SPLIT_MANIFEST = Path("data/manifests/split_manifest_v1.json")
_DEFAULT_POLICY_MANIFEST = Path("data/manifests/acquisition_policy_v1.json")
_DEFAULT_PILOT_CONFIG = Path("configs/data/acquisition/pilot_january_2019.yaml")
_DEFAULT_JOURNAL_PATH = Path("data/state/pilot_acquisition_journal.sqlite")
_PILOT_REQUEST_PLAN_SCHEMA = "data_contracts/pilot_request_plan.schema.json"
_HARD_PILOT_SPEND_CAP_USD = Decimal("5.00")
_ACCEPTED_PILOT_PLANNER_ESTIMATE_USD = Decimal("0.46")
_METADATA_TIMEOUT_SECONDS = 30

_CONTRACT_DIR = "data_contracts"


def _pilot_execution_coordinator() -> PilotExecutionCoordinator:
    return PilotExecutionCoordinator()


def _pilot_metadata_provider_factory() -> DatabentoMetadataProvider:
    return DatabentoMetadataProvider(_raw_databento_client())


def _pilot_paid_provider_factory(root: Path) -> Callable[[], Any]:
    return lambda: create_databento_paid_provider(data_root=root)


class _PilotCliLifecycle:
    def __init__(self, *, data_root: Path) -> None:
        self._data_root = data_root

    def inspect(
        self, request: AcquisitionRequest, entry: JournalEntry | None
    ) -> tuple[bool, bool, bool, bool]:
        raw = bool(
            entry
            and entry.raw_path
            and entry.raw_checksum
            and Path(entry.raw_path).is_file()
            and verify_checksum(Path(entry.raw_path), entry.raw_checksum)
        )
        normalized = bool(
            entry
            and entry.normalized_path
            and entry.normalized_checksum
            and Path(entry.normalized_path).is_file()
            and verify_checksum(Path(entry.normalized_path), entry.normalized_checksum)
        )
        quality = bool(entry and self._quality_path(request).is_file())
        partial = any(self._data_root.glob(f"**/{request.request_id}*.partial"))
        return raw, normalized, quality, partial

    def normalize(
        self, request: AcquisitionRequest, raw: RawAcquisitionResult
    ) -> tuple[str, str, int]:
        import databento

        output = (
            self._data_root
            / "data/processed/pilot_january_2019"
            / request.dataset
            / request.schema_name
            / f"{request.request_id}.parquet"
        )
        result = normalize_dbn_store_to_parquet(
            dbn_store=databento.DBNStore.from_file(Path(raw.raw_path)),
            output_path=output,
            provenance=provenance_columns_for(request, raw.sha256, datetime.now(UTC)),
            expected_raw_record_count=raw.record_count,
        )
        return result.path, result.sha256, Path(result.path).stat().st_size

    def quality(self, request: AcquisitionRequest, normalized_path: str) -> bool:
        if not Path(normalized_path).is_file():
            return False
        report = self._quality_path(request)
        report.parent.mkdir(parents=True, exist_ok=True)
        write_acquisition_json(
            report,
            {
                "request_id": request.request_id,
                "normalized_path": normalized_path,
                "status": "passed",
                "validated_at": datetime.now(UTC).isoformat(),
            },
        )
        return True

    def _quality_path(self, request: AcquisitionRequest) -> Path:
        return self._data_root / "reports/data/quality" / f"{request.request_id}.json"


def _pilot_lifecycle(root: Path) -> LifecycleHooks:
    return _PilotCliLifecycle(data_root=root)


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

    client = databento.Historical(key)
    client.metadata.TIMEOUT = _METADATA_TIMEOUT_SECONDS
    return client


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
    """Render one finalized request without changing its canonical field names."""
    return request.model_dump(mode="json", by_alias=True)


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
    """Recompute the canonical pilot hash and validate every finalized request."""
    requests = [AcquisitionRequest.model_validate(item) for item in manifest_payload["requests"]]
    for request in requests:
        verify_final_request(request)
    return compute_plan_hash(
        requests,
        manifest_payload.get("bindings", {}),
        _pilot_plan_hash_metadata(manifest_payload),
    )


def _resolve_under_root(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _pilot_plan_hash_metadata(manifest_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "estimated_total_cost_usd": manifest_payload["estimated_total_cost_usd"],
        "estimated_maximum_single_request_usd": manifest_payload[
            "estimated_maximum_single_request_usd"
        ],
        "maximum_allowed_total_usd": manifest_payload["maximum_allowed_total_usd"],
        "maximum_allowed_single_request_usd": manifest_payload[
            "maximum_allowed_single_request_usd"
        ],
        "authorization": manifest_payload["authorization"],
        "purchase_authorized": manifest_payload["purchase_authorized"],
    }


def _required_manifest_hash(payload: dict[str, Any], label: str) -> str:
    value = payload.get("manifest_hash")
    if not isinstance(value, str) or len(value) != 64:
        raise PlanValidationError(f"{label} is missing a SHA-256 manifest_hash.")
    return value


def _validate_pilot_plan_artifacts(
    *,
    root: Path,
    request_manifest: Path,
    config: Path,
    source_manifest: Path,
    split_manifest: Path,
    policy_manifest: Path,
) -> tuple[dict[str, Any], list[AcquisitionRequest], dict[str, str]]:
    """Validate a finalized plan against its canonical local dependencies."""
    plan_payload = load_acquisition_json(request_manifest)
    _validate_pilot_request_plan_schema(root, plan_payload)
    pilot_config = load_pilot_config(config)
    source_payload = load_manifest(source_manifest)
    split_payload = load_manifest(split_manifest)
    verify_manifests(source_payload, split_payload)
    source = parse_source_manifest(source_payload)
    split = parse_split_manifest(split_payload)
    policy_payload = load_acquisition_json(policy_manifest)
    verify_policy_hash(policy_payload)
    policy = parse_policy_manifest(policy_payload)
    if policy.purchase_authorized or not policy.download_guard_enabled:
        raise PlanValidationError(
            "Acquisition policy must remain unauthorized with download guard enabled."
        )
    expected_bindings = {
        "source_manifest_hash": _required_manifest_hash(source_payload, "source manifest"),
        "split_manifest_hash": _required_manifest_hash(split_payload, "split manifest"),
        "acquisition_policy_hash": _required_manifest_hash(policy_payload, "acquisition policy"),
        "pilot_config_hash": config_sha256(config),
    }
    bindings = plan_payload["bindings"]
    if any(bindings[key] != value for key, value in expected_bindings.items()):
        raise PlanValidationError("Pilot plan dependency hash mismatch.")
    if (
        policy.source_manifest_hash != expected_bindings["source_manifest_hash"]
        or policy.split_manifest_hash != expected_bindings["split_manifest_hash"]
    ):
        raise PlanValidationError("Acquisition policy dependency hash mismatch.")
    if plan_payload["plan_hash"] != _recompute_pilot_plan_hash(plan_payload):
        raise PlanValidationError("plan_hash_mismatch: canonical plan contents differ")

    if source.qualification_status != "qualified":
        raise PlanValidationError("Source manifest is not qualified for pilot execution.")
    if source.underlying.dataset != pilot_config.underlying.dataset:
        raise PlanValidationError("Source manifest underlying dataset does not match pilot config.")
    if source.underlying.symbol != pilot_config.underlying.symbol:
        raise PlanValidationError("Source manifest underlying symbol does not match pilot config.")
    if source.options.dataset != pilot_config.options.dataset:
        raise PlanValidationError("Source manifest options dataset does not match pilot config.")
    if source.options.parent_symbol != pilot_config.options.symbol:
        raise PlanValidationError("Source manifest options symbol does not match pilot config.")
    underlying_available = set(source.underlying.schemas) | {
        schema
        for schema, status in source.underlying.optional_schemas.items()
        if status == "available"
    }
    if any(schema not in underlying_available for schema in pilot_config.underlying.schemas):
        raise PlanValidationError("Pilot underlying schema is unavailable in source manifest.")
    if pilot_config.options.definition_schema not in source.options.schemas:
        raise PlanValidationError(
            "Pilot options definition schema is unavailable in source manifest."
        )
    if pilot_config.options.quote_schema not in source.options.schemas:
        raise PlanValidationError("Pilot options quote schema is unavailable in source manifest.")
    approved = {
        (item.dataset, schema) for item in policy.approved_datasets for schema in item.schemas
    }
    for dataset, schemas in (
        (pilot_config.underlying.dataset, pilot_config.underlying.schemas),
        (
            pilot_config.options.dataset,
            [pilot_config.options.definition_schema, pilot_config.options.quote_schema],
        ),
    ):
        for schema in schemas:
            if (dataset, schema) not in approved:
                raise PlanValidationError(
                    "Pilot config uses a dataset/schema outside the policy approval."
                )
    if to_decimal(policy.budget_ceiling_usd) < to_decimal(
        plan_payload["maximum_allowed_total_usd"]
    ):
        raise PlanValidationError("Acquisition policy budget ceiling is below the pilot plan cap.")
    if policy.maximum_pilot_spend_usd != plan_payload["maximum_allowed_total_usd"]:
        raise PlanValidationError("Acquisition policy pilot cap does not match the pilot plan cap.")

    requests = [AcquisitionRequest.model_validate(item) for item in plan_payload["requests"]]
    expected_requests = build_pilot_request_plan(pilot_config)
    if [request.specification_hash for request in requests] != [
        request.specification_hash for request in expected_requests
    ]:
        raise PlanValidationError("Pilot request identities do not match the configured pilot.")
    if plan_payload["request_count"] != len(requests):
        raise PlanValidationError("Pilot request_count does not match the request list.")
    if any(
        request.start.date() < split.training_start
        or request.end_exclusive.date() > split.training_end
        for request in requests
    ):
        raise PlanValidationError("Pilot request window is outside the training split.")

    costs = [to_decimal(request.estimated_cost or "0") for request in requests]
    computed_total = sum(costs, Decimal("0"))
    computed_maximum = max(costs, default=Decimal("0"))
    if computed_total != to_decimal(plan_payload["estimated_total_cost_usd"]):
        raise PlanValidationError("Pilot request costs do not sum to the manifest total.")
    if computed_maximum != to_decimal(plan_payload["estimated_maximum_single_request_usd"]):
        raise PlanValidationError("Pilot maximum request cost does not match the manifest.")
    if to_decimal(plan_payload["maximum_allowed_total_usd"]) != pilot_config.maximum_spend_usd:
        raise PlanValidationError("Pilot total spend cap does not match the configuration.")
    if (
        to_decimal(plan_payload["maximum_allowed_single_request_usd"])
        != pilot_config.maximum_single_request_usd
    ):
        raise PlanValidationError("Pilot per-request spend cap does not match the configuration.")
    if computed_total > pilot_config.maximum_spend_usd:
        raise PlanValidationError("Pilot request plan exceeds its total spend cap.")
    if any(cost > pilot_config.maximum_single_request_usd for cost in costs):
        raise PlanValidationError("Pilot request plan exceeds its per-request spend cap.")
    comparison = plan_payload.get("estimate_comparison")
    if not isinstance(comparison, dict):
        raise PlanValidationError("Pilot estimate_comparison is missing.")
    accepted = to_decimal(comparison.get("accepted_planner_estimate_usd"))
    fresh = to_decimal(comparison.get("fresh_metadata_estimate_usd"))
    difference = to_decimal(comparison.get("difference_usd"))
    tolerance = to_decimal(comparison.get("tolerance_usd"))
    expected_tolerance = (
        _ACCEPTED_PILOT_PLANNER_ESTIMATE_USD * pilot_config.estimate_increase_tolerance_fraction
    )
    if accepted != _ACCEPTED_PILOT_PLANNER_ESTIMATE_USD or fresh != computed_total:
        raise PlanValidationError("Pilot estimate comparison does not match manifest costs.")
    if fresh - accepted != difference:
        raise PlanValidationError("Pilot estimate comparison difference is not exact.")
    if expected_tolerance != tolerance:
        raise PlanValidationError("Pilot estimate comparison tolerance is not exact.")
    if (difference <= tolerance) is not comparison.get("within_tolerance"):
        raise PlanValidationError("Pilot estimate comparison tolerance flag is not exact.")
    if (
        sum(request.estimated_record_count or 0 for request in requests)
        != plan_payload["estimated_record_count"]
    ):
        raise PlanValidationError("Pilot estimated record count does not match its requests.")
    if (
        sum(request.estimated_billable_size or 0 for request in requests)
        != plan_payload["estimated_billable_size_bytes"]
    ):
        raise PlanValidationError("Pilot estimated byte count does not match its requests.")
    return plan_payload, requests, expected_bindings


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


#: Age ceiling used only after an explicit, hash-authorized stale resume. Large
#: enough to bypass the freshness window while leaving every other check intact.
_STALE_RESUME_MAX_AGE_MINUTES = 10**9


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    """Return the current commit SHA, or ``"unknown"`` outside a git checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip()


def _resolve_checkpoint_state(
    *,
    checkpoint: Path,
    expected: dict[str, object],
    current_config_hash: str,
    normal_max_age_minutes: int,
    resume: bool,
    allow_stale_sha256: str | None,
    now: str,
    request_ids: list[str],
) -> MetadataCheckpoint:
    """Load a resumable checkpoint fail-closed, or build a fresh one for non-resume.

    Explicit ``--resume`` never silently starts a new generation: a missing,
    stale (without authorization), or otherwise-invalid checkpoint exits nonzero.
    ``allow_stale_sha256`` bypasses the age window only, and only when it equals
    the checkpoint's exact bytes; every other integrity, plan, endpoint-hash, and
    configuration-compatibility check remains mandatory.
    """
    if not resume:
        return MetadataCheckpoint.model_validate(
            {
                **expected,
                "pilot_config_hash": current_config_hash,
                "created_at": now,
                "updated_at": now,
                "pending_request_ids": request_ids,
            }
        )
    if not checkpoint.exists():
        _logger.error("Resume requested but checkpoint does not exist: %s", checkpoint)
        raise typer.Exit(code=1)
    maximum_age_minutes = normal_max_age_minutes
    if allow_stale_sha256 is not None:
        if not is_valid_sha256(allow_stale_sha256) or allow_stale_sha256 != _sha256_file(
            checkpoint
        ):
            _logger.error("Stale-checkpoint authorization hash did not match the checkpoint bytes.")
            raise typer.Exit(code=1)
        maximum_age_minutes = _STALE_RESUME_MAX_AGE_MINUTES
    try:
        state = load_checkpoint(
            checkpoint, expected=expected, maximum_age_minutes=maximum_age_minutes
        )
    except ValueError as exc:
        _logger.error("Metadata checkpoint rejected: %s", exc)
        raise typer.Exit(code=1) from exc
    if not is_pilot_config_hash_compatible(state.pilot_config_hash, current_config_hash):
        _logger.error("Checkpoint configuration hash is not operationally compatible.")
        raise typer.Exit(code=1)
    return state


@pilot_app.command("prepare")
def pilot_prepare(
    config: Path = typer.Option(..., "--config", help="Path to the pilot-execution YAML config."),
    output: Path = typer.Option(
        ..., "--output", help="Path to write the local pilot preflight report."
    ),
    request_manifest: Path = typer.Option(
        _DEFAULT_REQUEST_MANIFEST,
        "--request-manifest",
        help="Path to atomically write the authorization-ready request-plan manifest.",
    ),
    source_manifest: Path = typer.Option(
        _DEFAULT_SOURCE_MANIFEST, "--source-manifest", help="Path to the accepted source manifest."
    ),
    split_manifest: Path = typer.Option(
        _DEFAULT_SPLIT_MANIFEST, "--split-manifest", help="Path to the sealed split manifest."
    ),
    policy_manifest: Path = typer.Option(
        _DEFAULT_POLICY_MANIFEST,
        "--policy-manifest",
        help="Path to the accepted acquisition policy manifest.",
    ),
    checkpoint: Path = typer.Option(
        Path("reports/data/pilot_metadata_checkpoint.local.json"),
        "--checkpoint",
        help="Ignored atomic metadata checkpoint.",
    ),
    resume: bool = typer.Option(False, "--resume", help="Resume a matching fresh checkpoint."),
    allow_stale_checkpoint_sha256: str | None = typer.Option(
        None,
        "--allow-stale-checkpoint-sha256",
        help=(
            "Authorize resuming a stale (past freshness window) checkpoint whose exact "
            "bytes hash to this 64-lowercase-hex value. Bypasses age only; valid with "
            "--resume; all other integrity checks remain mandatory."
        ),
    ),
    max_requests: int | None = typer.Option(
        None, "--max-requests", min=1, help="Attempt at most this many pending requests."
    ),
    only_request_id: str | None = typer.Option(
        None, "--only-request-id", help="Attempt only one canonical request ID."
    ),
    only_endpoint: str | None = typer.Option(
        None,
        "--only-endpoint",
        help="Diagnostic endpoint: record-count, billable-size, or cost.",
    ),
) -> None:
    """Build and metadata-preflight an authorization-ready January 2019 plan."""
    configure_logging("INFO")
    root = find_repository_root()
    config = _resolve_under_root(root, config)
    source_manifest = _resolve_under_root(root, source_manifest)
    split_manifest = _resolve_under_root(root, split_manifest)
    policy_manifest = _resolve_under_root(root, policy_manifest)
    request_manifest = _resolve_under_root(root, request_manifest)
    output = _resolve_under_root(root, output)
    checkpoint = _resolve_under_root(root, checkpoint)

    try:
        pilot_config = load_pilot_config(config)
        source_payload = load_manifest(source_manifest)
        split_payload = load_manifest(split_manifest)
        verify_manifests(source_payload, split_payload)
        policy_payload = load_acquisition_json(policy_manifest)
        verify_policy_hash(policy_payload)
        policy = parse_policy_manifest(policy_payload)
        source_hash = _required_manifest_hash(source_payload, "source manifest")
        split_hash = _required_manifest_hash(split_payload, "split manifest")
        policy_hash = _required_manifest_hash(policy_payload, "acquisition policy")
        if policy.source_manifest_hash != source_hash or policy.split_manifest_hash != split_hash:
            raise PlanValidationError(
                "Acquisition policy dependency hashes do not match the source and split manifests."
            )
        requests = build_pilot_request_plan(pilot_config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc
    except (ManifestValidationError, PlanValidationError, ValueError) as exc:
        _logger.error("Pilot dependency or plan validation failed: %s", exc)
        raise typer.Exit(code=1) from exc

    if only_endpoint not in {None, "record-count", "billable-size", "cost"}:
        raise typer.BadParameter("invalid --only-endpoint")
    if only_request_id and only_request_id not in {item.request_id for item in requests}:
        raise typer.BadParameter("unknown --only-request-id")
    _load_dotenv(root)
    if not __import__("os").environ.get("DATABENTO_API_KEY"):
        raise typer.Exit(code=2)

    if allow_stale_checkpoint_sha256 is not None and not resume:
        raise typer.BadParameter("--allow-stale-checkpoint-sha256 requires --resume")

    calendar_version = _distribution_version("exchange-calendars")
    only_endpoint_value = cast(Endpoint | None, only_endpoint)
    current_config_hash = config_sha256(config)
    # ``pilot_config_hash`` is validated separately for operational compatibility,
    # so it is not part of the strict expected-binding equality check.
    expected_checkpoint: dict[str, object] = {
        "source_manifest_hash": source_hash,
        "split_manifest_hash": split_hash,
        "acquisition_policy_hash": policy_hash,
        "calendar_version": calendar_version,
        "databento_client_version": checkpoint_client_version(),
        "estimator_version": "pilot-metadata-process-v1",
        "ordered_request_specification_hashes": [item.request_hash for item in requests],
    }
    now = datetime.now(UTC).isoformat()
    state = _resolve_checkpoint_state(
        checkpoint=checkpoint,
        expected=expected_checkpoint,
        current_config_hash=current_config_hash,
        normal_max_age_minutes=pilot_config.metadata_execution.checkpoint_max_age_minutes,
        resume=resume,
        allow_stale_sha256=allow_stale_checkpoint_sha256,
        now=now,
        request_ids=[item.request_id for item in requests],
    )
    write_checkpoint(checkpoint, state)

    diagnostic = root / "reports/data/metadata_timeout_diagnostic.local.json"

    def record_event(event: MetadataOperationEvent) -> None:
        diagnostic.parent.mkdir(parents=True, exist_ok=True)
        with diagnostic.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n")
            handle.flush()
            __import__("os").fsync(handle.fileno())

    selected = [item for item in requests if item.request_id in state.pending_request_ids]
    if only_request_id:
        selected = [item for item in selected if item.request_id == only_request_id]
    if max_requests is not None:
        selected = selected[:max_requests]
    run_started = __import__("time").monotonic()
    endpoint_calls = retries = timeouts = attempted = 0
    snapshot_cache = UnitPriceSnapshotCache(lambda ds: _pilot_unit_price_snapshot_loader(ds))
    for request in selected:
        if (
            __import__("time").monotonic() - run_started
            >= pilot_config.metadata_execution.total_run_deadline_seconds
        ):
            break
        attempted += 1
        endpoints = ("record-count", "billable-size", "cost")
        request_results = state.endpoint_results.setdefault(request.request_id, {})
        selected_endpoints = (only_endpoint_value,) if only_endpoint_value else endpoints
        for endpoint in selected_endpoints:
            assert endpoint is not None
            if endpoint in request_results:
                continue
            for attempt in range(1, pilot_config.metadata_execution.maximum_timeout_attempts + 1):
                remaining_run_seconds = (
                    pilot_config.metadata_execution.total_run_deadline_seconds
                    - (__import__("time").monotonic() - run_started)
                )
                if remaining_run_seconds <= 0:
                    break
                isolated = _run_isolated_metadata(
                    request=request,
                    run_id=state.run_id,
                    request_index=requests.index(request) + 1,
                    request_count=len(requests),
                    attempt=attempt,
                    timeout_seconds=min(
                        pilot_config.metadata_execution.hard_request_timeout_seconds,
                        remaining_run_seconds,
                    ),
                    event_sink=record_event,
                    only_endpoint=cast(Endpoint, endpoint),
                )
                endpoint_calls += sum(event.outcome == "succeeded" for event in isolated.events)
                state.attempt_history.append(isolated.model_dump(mode="json", exclude={"estimate"}))
                if not isolated.failure_type:
                    value = isolated.endpoint_values[cast(Endpoint, endpoint)]
                    completed_at = datetime.now(UTC).isoformat()
                    request_results[cast(Endpoint, endpoint)] = MetadataEndpointResult(
                        value=value,
                        completed_at=completed_at,
                        response_hash=endpoint_response_hash(cast(Endpoint, endpoint), value),
                        cost_source="provider_response" if endpoint == "cost" else None,
                    )
                    state.updated_at = completed_at
                    write_checkpoint(checkpoint, state)
                    break
                if isolated.failure_type == "metadata_hard_timeout":
                    timeouts += 1
                last = isolated.events[-1] if isolated.events else None
                retryable = isolated.failure_type == "metadata_hard_timeout" or bool(
                    last
                    and (
                        last.http_status in {429, 500, 502, 503, 504}
                        or last.exception_class
                        in {"TimeoutError", "ConnectionError", "ConnectionResetError"}
                    )
                )
                if (
                    not retryable
                    or attempt == pilot_config.metadata_execution.maximum_timeout_attempts
                ):
                    derived = _maybe_derive_cost_fallback(
                        request=request,
                        endpoint=cast(Endpoint, endpoint),
                        isolated=isolated,
                        state=state,
                        request_results=request_results,
                        snapshot_cache=snapshot_cache,
                    )
                    if derived is not None:
                        request_results[cast(Endpoint, endpoint)] = derived
                        state.failed_request_id = state.failed_endpoint = None
                        state.last_failure = None
                        state.updated_at = derived.completed_at
                        write_checkpoint(checkpoint, state)
                        break
                    state.failed_request_id = request.request_id
                    state.failed_endpoint = isolated.failed_endpoint
                    state.last_failure = isolated.failure_type
                    state.updated_at = datetime.now(UTC).isoformat()
                    write_checkpoint(checkpoint, state)
                    typer.echo(json.dumps(isolated.model_dump(mode="json"), sort_keys=True))
                    raise typer.Exit(code=1)
                retries += 1
            if endpoint not in request_results:
                break
        if only_endpoint_value is not None:
            typer.echo(
                json.dumps({"status": "complete", "endpoint": only_endpoint_value}, sort_keys=True)
            )
            return
        if any(endpoint not in request_results for endpoint in endpoints):
            break
        estimate = MetadataEstimate(
            dataset=request.dataset,
            schema=request.schema_name,
            symbol=request.symbols[0],
            stype_in=request.stype_in,
            window_start=request.start,
            window_end=request.end_exclusive,
            record_count=int(request_results["record-count"].value),
            billable_size_bytes=int(request_results["billable-size"].value),
            cost_usd=Decimal(str(request_results["cost"].value)),
            retries=0,
        )
        state.completed_estimates[request.request_id] = {
            **estimate.__dict__,
            "window_start": estimate.window_start.isoformat(),
            "window_end": estimate.window_end.isoformat(),
            "cost_usd": str(estimate.cost_usd),
        }
        state.pending_request_ids.remove(request.request_id)
        state.failed_request_id = state.failed_endpoint = state.last_failure = None
        state.updated_at = datetime.now(UTC).isoformat()
        write_checkpoint(checkpoint, state)
        typer.echo(
            f"metadata preflight {len(state.completed_estimates)}/{len(requests)}: "
            f"{request.request_id} {request.dataset}/{request.schema_name} cost={estimate.cost_usd}"
        )

    if state.pending_request_ids:
        typer.echo(
            json.dumps(
                {
                    "status": "checkpointed_incomplete",
                    "completed": len(state.completed_estimates),
                    "pending": len(state.pending_request_ids),
                    "attempted": attempted,
                    "endpoint_calls": endpoint_calls,
                    "retries": retries,
                    "timeouts": timeouts,
                },
                sort_keys=True,
            )
        )
        return

    estimates = []
    finalized_requests = []
    for request in requests:
        payload = state.completed_estimates[request.request_id]
        estimate = MetadataEstimate(
            **{
                **payload,
                "window_start": datetime.fromisoformat(str(payload["window_start"])),
                "window_end": datetime.fromisoformat(str(payload["window_end"])),
                "cost_usd": Decimal(str(payload["cost_usd"])),
            }
        )
        estimates.append(estimate)
        finalized_requests.append(
            finalize_request(request, estimate, datetime.fromisoformat(state.updated_at))
        )
    fresh_total = sum((estimate.cost_usd for estimate in estimates), Decimal("0"))
    maximum_request = max((estimate.cost_usd for estimate in estimates), default=Decimal("0"))
    cost_summary = plan_cost_rollup(state, tracked_total_usd=_ACCEPTED_PILOT_PLANNER_ESTIMATE_USD)
    rejections: list[Any] = []
    if (
        cost_summary.conservative_total_usd > pilot_config.maximum_spend_usd
        or cost_summary.largest_conservative_request_usd > pilot_config.maximum_single_request_usd
        or not cost_summary.within_drift_ceiling
    ):
        _logger.error("Pilot preflight rejected metadata estimates over configured caps.")
        raise typer.Exit(code=1)
    elapsed = __import__("time").monotonic() - run_started
    result = PreflightResult(
        fresh_estimates={
            request.request_id: str(estimate.cost_usd)
            for request, estimate in zip(requests, estimates, strict=True)
        },
        planned_total_usd=str(
            sum((to_decimal(request.estimated_cost or "0") for request in requests), Decimal("0"))
        ),
        fresh_total_usd=str(fresh_total),
        increase_fraction="0",
        within_single_request_cap=True,
        within_total_cap=True,
        within_increase_tolerance=True,
        rejections=rejections,
        passed=True,
        metadata_call_count=len(estimates),
        metadata_endpoint_call_count=sum(
            event.get("outcome") == "succeeded"
            for attempt in state.attempt_history
            for event in attempt.get("events", [])
        ),
        retry_count=sum(
            max(0, int(item["events"][0].get("attempt", 1)) - 1)
            for item in state.attempt_history
            if item.get("events")
        ),
        estimated_requests=finalized_requests,
        started_at=state.created_at,
        completed_at=state.updated_at,
        elapsed_seconds=elapsed,
    )

    generated_at = _now()
    bindings = {
        "source_manifest_hash": source_hash,
        "split_manifest_hash": split_hash,
        "acquisition_policy_hash": policy_hash,
        "pilot_config_hash": config_sha256(config),
        "calendar_name": pilot_config.calendar_name,
        "calendar_library": "exchange-calendars",
        "calendar_library_version": _distribution_version("exchange-calendars"),
        "provider_client": "databento",
        "provider_client_version": _distribution_version("databento"),
        "implementation_revision": (
            f"neuralmarket-{_distribution_version('neuralmarket')}:pilot-request-plan-v1"
        ),
    }
    finalized_requests = result.estimated_requests
    phash = compute_plan_hash(finalized_requests, bindings)
    fresh_total = to_decimal(result.fresh_total_usd)
    maximum_request = max(
        (to_decimal(request.estimated_cost) for request in finalized_requests),
        default=Decimal("0"),
    )
    planner_difference = fresh_total - _ACCEPTED_PILOT_PLANNER_ESTIMATE_USD
    planner_tolerance = (
        _ACCEPTED_PILOT_PLANNER_ESTIMATE_USD * pilot_config.estimate_increase_tolerance_fraction
    )
    estimate_comparison = {
        "accepted_planner_estimate_usd": str(_ACCEPTED_PILOT_PLANNER_ESTIMATE_USD),
        "fresh_metadata_estimate_usd": result.fresh_total_usd,
        "difference_usd": str(planner_difference),
        "tolerance_usd": str(planner_tolerance),
        "within_tolerance": planner_difference <= planner_tolerance,
        "explanation": (
            "Fresh get_record_count/get_billable_size/get_cost metadata replaced the "
            "earlier aggregate planning estimate; no market records were requested."
        ),
    }
    manifest_payload: dict[str, Any] = {
        "manifest_version": "1.0",
        "plan_hash": phash,
        "generated_at": generated_at,
        "bindings": bindings,
        "waves": _ordered_waves(finalized_requests),
        "request_count": len(finalized_requests),
        "requests": [_pilot_request_manifest_json(r) for r in finalized_requests],
        "estimated_total_cost_usd": result.fresh_total_usd,
        "estimated_maximum_single_request_usd": str(maximum_request),
        "estimated_record_count": sum(
            request.estimated_record_count or 0 for request in finalized_requests
        ),
        "estimated_billable_size_bytes": sum(
            request.estimated_billable_size or 0 for request in finalized_requests
        ),
        "maximum_allowed_total_usd": str(pilot_config.maximum_spend_usd),
        "maximum_allowed_single_request_usd": str(pilot_config.maximum_single_request_usd),
        "estimate_comparison": estimate_comparison,
        "authorization": {
            "required": True,
            "exact_plan_hash_required": pilot_config.require_exact_plan_hash,
            "authorization_file_required": pilot_config.require_authorization_file,
            "operator_confirmation_required": True,
            "coverage": [
                "plan_hash",
                "source_manifest_hash",
                "split_manifest_hash",
                "acquisition_policy_hash",
                "maximum_total_cost_usd",
                "maximum_single_request_cost_usd",
            ],
        },
        "purchase_authorized": False,
        "download_attempts": 0,
        "batch_jobs_submitted": 0,
        "live_connections_opened": 0,
    }

    phash = compute_plan_hash(
        finalized_requests,
        bindings,
        _pilot_plan_hash_metadata(manifest_payload),
    )
    manifest_payload["plan_hash"] = phash

    fallback_request_ids = sorted(
        request_id
        for request_id, endpoints in state.endpoint_results.items()
        if (cost := endpoints.get("cost")) is not None and cost.cost_source == "derived_response"
    )
    snapshot_hashes = sorted(
        {
            cost.unit_price_snapshot_hash
            for endpoints in state.endpoint_results.values()
            if (cost := endpoints.get("cost")) is not None and cost.unit_price_snapshot_hash
        }
    )
    cost_source_summary = {
        "provider_cost_count": cost_summary.provider_cost_count,
        "derived_cost_count": cost_summary.derived_cost_count,
        "portal_cost_count": cost_summary.portal_cost_count,
        "unavailable_cost_count": cost_summary.unavailable_cost_count,
        "raw_total_usd": str(cost_summary.raw_total_usd),
        "conservative_total_usd": str(cost_summary.conservative_total_usd),
        "largest_raw_request_usd": str(cost_summary.largest_raw_request_usd),
        "largest_conservative_request_usd": str(cost_summary.largest_conservative_request_usd),
        "within_total_cap": cost_summary.within_total_cap,
        "within_per_request_cap": cost_summary.within_per_request_cap,
        "within_drift_ceiling": cost_summary.within_drift_ceiling,
        "fallback_request_ids": fallback_request_ids,
        "unit_price_snapshot_hashes": snapshot_hashes,
        "pilot_cross_validation_sample_count": 1,
        "full_acquisition_minimum_sample_count": 2,
    }
    report_payload = {
        "generated_at": generated_at,
        "plan_hash": phash,
        "config_hash": config_sha256(config),
        "bindings": bindings,
        "preflight": result.model_dump(mode="json", exclude={"estimated_requests"}),
        "estimate_comparison": estimate_comparison,
        "cost_source_summary": cost_source_summary,
        "purchase_authorized": False,
        "download_attempts": 0,
        "batch_jobs_submitted": 0,
        "live_connections_opened": 0,
        "request_manifest": str(request_manifest),
    }
    write_acquisition_json(output, report_payload)

    if (
        not result.passed
        or fresh_total > _HARD_PILOT_SPEND_CAP_USD
        or not estimate_comparison["within_tolerance"]
    ):
        _logger.error("Pilot preflight rejected the plan; request manifest was not written.")
        raise typer.Exit(code=1)

    try:
        _validate_pilot_request_plan_schema(root, manifest_payload)
    except MarketDataError as exc:
        _logger.error("%s", exc)
        raise typer.Exit(code=1) from exc
    write_acquisition_json(request_manifest, manifest_payload)

    typer.echo(
        json.dumps(
            {
                "plan_hash": phash,
                "passed": result.passed,
                "fresh_total_usd": result.fresh_total_usd,
                "provider_cost_count": cost_summary.provider_cost_count,
                "derived_cost_count": cost_summary.derived_cost_count,
                "conservative_total_usd": str(cost_summary.conservative_total_usd),
                "fallback_request_ids": fallback_request_ids,
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


def _pilot_schema_lister(provider: DatabentoMetadataProvider) -> Callable[[str], list[str]]:
    """Return a per-dataset schema lister backed by one metadata provider."""

    def lister(dataset: str) -> list[str]:
        raw = provider.list_schemas(dataset=dataset)
        return [str(schema) for schema in cast(Iterable[Any], raw)]

    return lister


def _pilot_cost_quoter(
    *, run_id: str, request_count: int, requests: list[AcquisitionRequest]
) -> Callable[[AcquisitionRequest, int, float], Any]:
    """Return a per-request quoter that isolates each get_cost call in a child."""

    def quoter(request: AcquisitionRequest, attempt: int, timeout_seconds: float) -> Any:
        return _run_isolated_metadata(
            request=request,
            run_id=run_id,
            request_index=requests.index(request) + 1,
            request_count=request_count,
            attempt=attempt,
            timeout_seconds=timeout_seconds,
            only_endpoint="cost",
        )

    return quoter


@pilot_app.command("recheck-cost")
def pilot_recheck_cost(
    config: Path = typer.Option(
        _DEFAULT_PILOT_CONFIG, "--config", help="Path to the pilot-execution YAML config."
    ),
    checkpoint: Path = typer.Option(
        ..., "--checkpoint", help="Path to the completed metadata checkpoint."
    ),
    request_manifest: Path = typer.Option(
        _DEFAULT_REQUEST_MANIFEST,
        "--request-manifest",
        help="Path to the frozen pilot request-plan manifest.",
    ),
    expected_checkpoint_sha256: str = typer.Option(
        ...,
        "--expected-checkpoint-sha256",
        help="Exact 64-lowercase-hex SHA-256 the completed checkpoint bytes must match.",
    ),
    output: Path = typer.Option(..., "--output", help="Local fresh-cost evidence path."),
    attempt_manifest: Path = typer.Option(
        ..., "--attempt-manifest", help="Local per-attempt sanitized quote history path."
    ),
    source_manifest: Path = typer.Option(
        _DEFAULT_SOURCE_MANIFEST, "--source-manifest", help="Path to the accepted source manifest."
    ),
    split_manifest: Path = typer.Option(
        _DEFAULT_SPLIT_MANIFEST, "--split-manifest", help="Path to the sealed split manifest."
    ),
    policy_manifest: Path = typer.Option(
        _DEFAULT_POLICY_MANIFEST,
        "--policy-manifest",
        help="Path to the accepted acquisition policy manifest.",
    ),
) -> None:
    """Fresh-quote the exact frozen pilot requests via metadata.get_cost.

    Provider-only, fail-closed cost recheck to run immediately before a manual
    purchase authorization (and again whenever authorization, scope, SDK, or
    pricing changes). Quotes only the frozen 25-request plan, validates each
    dataset's schemas, and never acquires data or authorizes a purchase.
    """
    from neuralmarket.data.acquisition.live_cost_recheck import CostRecheckError, recheck_costs

    configure_logging("INFO")
    root = find_repository_root()
    config = _resolve_under_root(root, config)
    checkpoint = _resolve_under_root(root, checkpoint)
    request_manifest = _resolve_under_root(root, request_manifest)
    source_manifest = _resolve_under_root(root, source_manifest)
    split_manifest = _resolve_under_root(root, split_manifest)
    policy_manifest = _resolve_under_root(root, policy_manifest)
    output = _resolve_under_root(root, output)
    attempt_manifest = _resolve_under_root(root, attempt_manifest)

    if not is_valid_sha256(expected_checkpoint_sha256):
        raise typer.BadParameter("--expected-checkpoint-sha256 must be 64 lowercase hex")
    if not checkpoint.exists():
        _logger.error("Checkpoint not found: %s", checkpoint)
        raise typer.Exit(code=1)
    actual_sha = _sha256_file(checkpoint)
    if actual_sha != expected_checkpoint_sha256:
        _logger.error("Checkpoint SHA-256 mismatch; refusing.")
        raise typer.Exit(code=1)

    try:
        pilot_config = load_pilot_config(config)
        source_payload = load_manifest(source_manifest)
        split_payload = load_manifest(split_manifest)
        verify_manifests(source_payload, split_payload)
        policy_payload = load_acquisition_json(policy_manifest)
        verify_policy_hash(policy_payload)
        source_hash = _required_manifest_hash(source_payload, "source manifest")
        split_hash = _required_manifest_hash(split_payload, "split manifest")
        policy_hash = _required_manifest_hash(policy_payload, "acquisition policy")
        requests = build_pilot_request_plan(pilot_config)
    except ConfigurationError as exc:
        _logger.error("Configuration error: %s", exc)
        raise typer.Exit(code=2) from exc
    except (ManifestValidationError, PlanValidationError, ValueError) as exc:
        _logger.error("Pilot dependency or plan validation failed: %s", exc)
        raise typer.Exit(code=1) from exc

    expected_checkpoint: dict[str, object] = {
        "source_manifest_hash": source_hash,
        "split_manifest_hash": split_hash,
        "acquisition_policy_hash": policy_hash,
        "calendar_version": _distribution_version("exchange-calendars"),
        "databento_client_version": checkpoint_client_version(),
        "estimator_version": "pilot-metadata-process-v1",
        "ordered_request_specification_hashes": [item.request_hash for item in requests],
    }
    try:
        # Frozen-scope agreement: the checkpoint must bind exactly this plan.
        load_checkpoint(checkpoint, expected=expected_checkpoint, maximum_age_minutes=10**9)
    except ValueError as exc:
        _logger.error("Checkpoint rejected against frozen plan: %s", exc)
        raise typer.Exit(code=1) from exc

    manifest_payload = load_acquisition_json(request_manifest)
    frozen_plan_hash = str(manifest_payload.get("plan_hash", ""))
    request_manifest_sha = _sha256_file(request_manifest)

    _load_dotenv(root)
    if not __import__("os").environ.get("DATABENTO_API_KEY"):
        raise typer.Exit(code=2)

    provider = _pilot_metadata_provider_factory()
    run_id = uuid.uuid4().hex
    try:
        result = recheck_costs(
            requests=requests,
            repository_head=_git_head(root),
            checkpoint_sha256=actual_sha,
            plan_hash=frozen_plan_hash,
            request_manifest_sha256=request_manifest_sha,
            sdk_version=checkpoint_client_version(),
            now=datetime.now(UTC),
            schema_lister=_pilot_schema_lister(provider),
            quoter=_pilot_cost_quoter(
                run_id=run_id, request_count=len(requests), requests=requests
            ),
            timeout_seconds=float(pilot_config.metadata_execution.hard_request_timeout_seconds),
            prior_raw_total_usd=Decimal("0.460514456032759765625"),
            prior_conservative_total_usd=Decimal("0.46298506855869970703125"),
            tracked_total_usd=Decimal("0.460514456033"),
            max_attempts=pilot_config.metadata_execution.maximum_timeout_attempts,
        )
    except CostRecheckError as exc:
        _logger.error("Fresh cost recheck failed closed: %s", exc)
        raise typer.Exit(code=1) from exc
    finally:
        provider.close()

    evidence = {
        "schema_version": "pilot-fresh-cost-recheck-v1",
        "status": result.status,
        "authorization_ready": result.authorization_ready,
        "observed_at": result.observed_at,
        "expires_at": result.expires_at,
        "sdk_version": result.sdk_version,
        "repository_head": result.repository_head,
        "checkpoint_sha256": result.checkpoint_sha256,
        "plan_hash": result.plan_hash,
        "request_manifest_sha256": result.request_manifest_sha256,
        "provider_quote_count": result.provider_quote_count,
        "unavailable_quote_count": result.unavailable_quote_count,
        "fresh_raw_total_usd": result.fresh_raw_total_usd,
        "fresh_conservative_total_usd": result.fresh_conservative_total_usd,
        "prior_raw_total_usd": result.prior_raw_total_usd,
        "prior_conservative_total_usd": result.prior_conservative_total_usd,
        "absolute_delta_usd": result.absolute_delta_usd,
        "relative_delta": result.relative_delta,
        "largest_request_usd": result.largest_request_usd,
        "within_total_cap": result.within_total_cap,
        "within_per_request_cap": result.within_per_request_cap,
        "within_drift_ceiling": result.within_drift_ceiling,
        "schema_validation": result.schema_validation,
        "provider_call_inventory": result.provider_call_inventory,
        "quotes": [
            {
                "request_id": q.request_id,
                "dataset": q.dataset,
                "schema": q.schema,
                "symbols": list(q.symbols),
                "stype_in": q.stype_in,
                "start": q.start,
                "end": q.end,
                "status": q.status,
                "cost_usd": q.cost_usd,
                "attempts": q.attempts,
                "last_failure_class": q.last_failure_class,
                "last_http_status": q.last_http_status,
                "remaining_children": q.remaining_children,
            }
            for q in result.quotes
        ],
        "purchase_authorized": False,
    }
    write_acquisition_json(output, evidence)
    write_acquisition_json(
        attempt_manifest,
        {"schema_version": "pilot-fresh-cost-attempts-v1", "attempts": result.attempt_history},
    )

    typer.echo(
        json.dumps(
            {
                "status": result.status,
                "authorization_ready": result.authorization_ready,
                "provider_quote_count": result.provider_quote_count,
                "unavailable_quote_count": result.unavailable_quote_count,
                "fresh_conservative_total_usd": result.fresh_conservative_total_usd,
                "largest_request_usd": result.largest_request_usd,
                "within_total_cap": result.within_total_cap,
                "within_per_request_cap": result.within_per_request_cap,
                "within_drift_ceiling": result.within_drift_ceiling,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    if not result.authorization_ready:
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
    config: Path = typer.Option(
        _DEFAULT_PILOT_CONFIG, "--config", help="Path to the pilot-execution YAML config."
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
    root = find_repository_root()
    request_manifest = _resolve_under_root(root, request_manifest)
    authorization_template = _resolve_under_root(root, authorization_template)
    config = _resolve_under_root(root, config)
    source_manifest = _resolve_under_root(root, source_manifest)
    split_manifest = _resolve_under_root(root, split_manifest)
    policy_manifest = _resolve_under_root(root, policy_manifest)
    try:
        plan_payload, _, expected_bindings = _validate_pilot_plan_artifacts(
            root=root,
            request_manifest=request_manifest,
            config=config,
            source_manifest=source_manifest,
            split_manifest=split_manifest,
            policy_manifest=policy_manifest,
        )
        stored_plan_hash = str(plan_payload["plan_hash"])
    except Exception as exc:
        _logger.error("Pilot request-plan verification failed: %s", redact(str(exc)))
        raise typer.Exit(code=1) from exc

    template_usable_for_execution = False
    authorization_rejection_reason: str | None = None
    try:
        auth = load_authorization(authorization_template)
        validate_authorization(
            auth,
            expected_plan_hash=str(stored_plan_hash or ""),
            expected_source_manifest_hash=expected_bindings["source_manifest_hash"],
            expected_split_manifest_hash=expected_bindings["split_manifest_hash"],
            expected_acquisition_policy_hash=expected_bindings["acquisition_policy_hash"],
            expected_maximum_spend_usd=to_decimal(plan_payload["maximum_allowed_total_usd"]),
            expected_maximum_single_request_usd=to_decimal(
                plan_payload["maximum_allowed_single_request_usd"]
            ),
            now=datetime.now(UTC),
            consumed_ids=set(),
        )
        template_usable_for_execution = True
    except AuthorizationError as exc:
        authorization_rejection_reason = exc.reason
    except Exception as exc:  # fail closed: any parse/schema/model failure rejects the template
        authorization_rejection_reason = f"unparseable: {exc}"

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
    mode: str = typer.Option("paid", "--mode", help="Execution mode: validate-only or paid."),
    plan: Path = typer.Option(
        ..., "--plan", help="Path to the tracked pilot request-plan manifest."
    ),
    authorization: Path = typer.Option(
        ..., "--authorization", help="Path to the signed pilot authorization artifact."
    ),
    portal_attestation: Path | None = typer.Option(
        None,
        "--portal-attestation",
        help="Time-limited, local manual portal-limit attestation.",
    ),
    confirm_plan_hash: str = typer.Option(
        ...,
        "--confirm-plan-hash",
        help="Operator-confirmed plan hash; must exactly match the plan under review.",
    ),
    config: Path = typer.Option(
        _DEFAULT_PILOT_CONFIG, "--config", help="Path to the pilot-execution YAML config."
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
    output: Path | None = typer.Option(
        None, "--output", help="Local execution or validation report path."
    ),
) -> None:
    """Validate a pilot or run the guarded paid execution path.

    Validation-only delegates to the coordinator's metadata-only path. Paid
    mode delegates to the coordinator-owned execution lifecycle.
    """
    configure_logging("INFO")
    root = find_repository_root()
    plan = _resolve_under_root(root, plan)
    authorization = _resolve_under_root(root, authorization)
    portal_attestation = (
        _resolve_under_root(root, portal_attestation) if portal_attestation is not None else None
    )
    config = _resolve_under_root(root, config)
    source_manifest = _resolve_under_root(root, source_manifest)
    split_manifest = _resolve_under_root(root, split_manifest)
    policy_manifest = _resolve_under_root(root, policy_manifest)
    try:
        if mode not in {"validate-only", "paid"}:
            raise ValueError("mode must be validate-only or paid")
        plan_payload, authorized_requests, expected_bindings = _validate_pilot_plan_artifacts(
            root=root,
            request_manifest=plan,
            config=config,
            source_manifest=source_manifest,
            split_manifest=split_manifest,
            policy_manifest=policy_manifest,
        )
        plan_hash_value = str(plan_payload["plan_hash"])
        source_hash = expected_bindings["source_manifest_hash"]
        split_hash = expected_bindings["split_manifest_hash"]
        policy_hash = expected_bindings["acquisition_policy_hash"]
        auth = load_authorization(authorization)
        validate_authorization(
            auth,
            expected_plan_hash=plan_hash_value,
            expected_source_manifest_hash=source_hash,
            expected_split_manifest_hash=split_hash,
            expected_acquisition_policy_hash=policy_hash,
            expected_maximum_spend_usd=to_decimal(plan_payload["maximum_allowed_total_usd"]),
            expected_maximum_single_request_usd=to_decimal(
                plan_payload["maximum_allowed_single_request_usd"]
            ),
            now=datetime.now(UTC),
            consumed_ids=set(),
        )
        if not hmac.compare_digest(confirm_plan_hash, plan_hash_value):
            raise AuthorizationError(
                "plan_hash_confirmation_mismatch",
                "confirm_plan_hash does not match the plan under review",
            )
        if portal_attestation is None:
            raise PortalAttestationError("portal attestation is required")
        attestation = load_portal_attestation(portal_attestation)
        validate_portal_attestation(attestation, plan_hash=plan_hash_value, now=datetime.now(UTC))
        seen_paths: set[str] = set()
        for request in authorized_requests:
            validate_logical_path(request.logical_output_path or "", seen_paths)
            seen_paths.add((request.logical_output_path or "").replace(chr(92), "/").lower())
    except Exception as exc:
        message = f"Pilot execution blocked: authorization guard rejected: {redact(str(exc))}"
        typer.echo(message, err=True)
        raise typer.Exit(code=1) from exc

    if mode == "validate-only":
        _load_dotenv(root)
        try:
            validation = _pilot_execution_coordinator().validate_only(
                requests=authorized_requests,
                config=load_pilot_config(config),
                plan_bindings=plan_payload["bindings"],
                plan_metadata=_pilot_plan_hash_metadata(plan_payload),
                metadata_provider_factory=_pilot_metadata_provider_factory,
            )
        except Exception as exc:
            message = f"Pilot validation-only preflight failed: {redact(str(exc))}"
            typer.echo(message, err=True)
            raise typer.Exit(code=1) from exc
        report = {
            "status": "ok",
            **validation.model_dump(),
            "paid_client_constructed": validation.paid_provider_constructed,
            "plan_hash": plan_hash_value,
            "request_count": len(authorized_requests),
            "fresh_total_cost": validation.estimated_total_cost,
            "authorization_status": "validated_unconsumed",
            "recovery_status": "journal_not_opened",
            "blocking_failures": [],
        }
        if output is not None:
            write_acquisition_json(_resolve_under_root(root, output), report)
        typer.echo(json.dumps(report, sort_keys=True))
        if not validation.ready_for_paid_execution:
            raise typer.Exit(code=1)
        return

    _load_dotenv(root)
    readiness = paid_provider_readiness()
    if not readiness.ready:
        typer.echo(f"Pilot execution blocked: paid provider unavailable: {readiness}", err=True)
        raise typer.Exit(code=1)

    journal_full_path = _resolve_under_root(root, journal_path)

    def journal_factory() -> RequestJournal:
        journal_full_path.parent.mkdir(parents=True, exist_ok=True)
        return RequestJournal(journal_full_path)

    try:
        result = _pilot_execution_coordinator().execute_paid(
            requests=authorized_requests,
            config=load_pilot_config(config),
            plan_hash=plan_hash_value,
            plan_bindings=plan_payload["bindings"],
            plan_metadata=_pilot_plan_hash_metadata(plan_payload),
            authorization_path=authorization,
            authorization_hash=auth.authorization_hash,
            portal_attestation_hash=attestation.attestation_hash,
            confirm_plan_hash=confirm_plan_hash,
            metadata_provider_factory=_pilot_metadata_provider_factory,
            paid_provider_factory=lambda: _pilot_paid_provider_factory(root)(),
            journal_factory=journal_factory,
            lifecycle=_pilot_lifecycle(root),
            now=datetime.now(UTC),
        )
    except ExecutorGuardError as exc:
        message = f"Pilot execution blocked: execution coordinator rejected ({exc.reason}): {exc}"
        typer.echo(message, err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        message = f"Pilot execution failed closed: {redact(str(exc))}"
        typer.echo(message, err=True)
        raise typer.Exit(code=1) from exc

    report = {"status": "ok" if result.blocking_state is None else "blocked", **result.model_dump()}
    if output is not None:
        write_acquisition_json(_resolve_under_root(root, output), report)
    typer.echo(json.dumps(report, sort_keys=True))
    if result.blocking_state is not None:
        raise typer.Exit(code=1)


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
    root = find_repository_root()
    plan = _resolve_under_root(root, plan)
    output = _resolve_under_root(root, output)
    journal_full_path = _resolve_under_root(root, journal_path)
    resolved_data_root = _resolve_under_root(root, data_root) if data_root is not None else root
    try:
        load_acquisition_json(plan)
    except PlanValidationError as exc:
        _logger.error("Pilot request-plan manifest could not be read: %s", exc)
        raise typer.Exit(code=1) from exc

    if journal_full_path.exists():
        with RequestJournal(journal_full_path) as journal:
            report = run_recovery(journal=journal, data_root=resolved_data_root)
    else:
        report = RecoveryReport(
            generated_at=datetime.now(UTC).isoformat(),
            findings=[],
            uncertain_billing_count=0,
            billed_without_validated_artifact_count=0,
            confirmed_not_billed_count=0,
            retry_eligible_count=0,
            stale_running_attempt_count=0,
            automatic_retry_allowed=False,
            retry_eligible_under_new_authorization=False,
            quarantine_recommended=[],
            manual_recovery_required=[],
            stale_running_attempts=[],
            retried=0,
            deleted=0,
        )

    write_acquisition_json(output, json.loads(report.model_dump_json()))
    typer.echo(
        json.dumps(
            {"retried": report.retried, "deleted": report.deleted, "output": str(output)},
            sort_keys=True,
        )
    )


@pilot_app.command("reconcile-billing")
def pilot_reconcile_billing(
    journal_path: Path = typer.Option(
        _DEFAULT_JOURNAL_PATH,
        "--journal",
        help="Path to the pilot acquisition journal SQLite file.",
    ),
    reconciliation: Path = typer.Option(
        ..., "--reconciliation", help="Local billing reconciliation artifact."
    ),
    output: Path = typer.Option(..., "--output", help="Path to write reconciliation result."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without mutating journal."),
) -> None:
    """Apply a manual Databento billing reconciliation without provider activity."""
    configure_logging("INFO")
    root = find_repository_root()
    journal_full_path = _resolve_under_root(root, journal_path)
    reconciliation = _resolve_under_root(root, reconciliation)
    output = _resolve_under_root(root, output)
    try:
        artifact = load_reconciliation_artifact(reconciliation)
        with RequestJournal(journal_full_path) as journal:
            result = apply_billing_reconciliation(
                journal=journal, artifact=artifact, dry_run=dry_run
            )
    except (BillingReconciliationError, ValueError, OSError) as exc:
        typer.echo(f"Billing reconciliation blocked: {redact(str(exc))}", err=True)
        raise typer.Exit(code=1) from exc
    payload = result.model_dump()
    payload["reconciliation_artifact_hash"] = artifact.artifact_hash
    write_acquisition_json(output, payload)
    typer.echo(json.dumps(payload, sort_keys=True))
