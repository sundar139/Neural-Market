"""Budget-constrained OPRA acquisition planning orchestration.

Loads and verifies the accepted source and split manifests, samples
development-period cost windows deterministically from the XNYS calendar,
estimates costs via Databento metadata only, projects and ranks candidate
strategies against a hard budget, and builds a bounded pilot plan. No
time-series, batch, or live data is ever requested, and every future purchase
remains unauthorized.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, date, datetime
from decimal import ROUND_CEILING, Decimal
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from neuralmarket.core.configuration import config_sha256
from neuralmarket.core.environment import _git_commit, _git_dirty
from neuralmarket.data.acquisition.budget import round_usd
from neuralmarket.data.acquisition.calendar import (
    full_day_range_window,
    quarterly_sample_sessions,
    quote_window,
    select_pilot_month,
)
from neuralmarket.data.acquisition.configuration import AcquisitionConfig
from neuralmarket.data.acquisition.contracts import (
    AcquisitionPlanReport as AcquisitionPlanReportModel,
)
from neuralmarket.data.acquisition.contracts import (
    BudgetPolicySnapshot,
    CatalogWave,
    CatalogWaveEstimate,
    CostStatistics,
    MetadataEstimateModel,
    PilotPlan,
    PilotRequestSpec,
    StrategyProjection,
    TestReserveProjection,
)
from neuralmarket.data.acquisition.estimation import MetadataEstimate, MetadataEstimator
from neuralmarket.data.acquisition.strategies import (
    COST_STATUS_PENDING_CATALOG,
    COST_STATUS_PROJECTED,
    DEVELOPMENT_SAFETY_FACTOR,
    MAX_SYMBOLS_PER_REQUEST,
    STRATEGY_D,
    STRATEGY_DEFINITIONS,
    TEST_RESERVE_SAFETY_FACTOR,
    project_strategy_cost,
    project_test_reserve_cost,
    project_worst_case_cost,
    rank_strategies,
)
from neuralmarket.data.calendar import session_dates
from neuralmarket.data.contracts import SCHEMA_VERSION
from neuralmarket.data.errors import PlanValidationError
from neuralmarket.data.manifests import (
    SourceManifest,
    SplitManifest,
    load_manifest,
    parse_source_manifest,
    parse_split_manifest,
    verify_manifest_hash,
)

_REQUIRED_ANCESTOR_COMMIT = "81064f9"


def _usd(value: Decimal) -> str:
    return str(round_usd(value))


def _percentile(sorted_values: list[Decimal], pct: Decimal) -> Decimal:
    """Nearest-rank percentile: ``index = ceil(pct * n) - 1``, clamped to ``[0, n-1]``.

    A simple, fully deterministic quantile convention (no interpolation),
    documented explicitly so projections are reproducible across runs.
    """
    n = len(sorted_values)
    if n == 0:
        raise PlanValidationError("Cannot compute a percentile of an empty sample.")
    idx = int((pct * n).to_integral_value(rounding=ROUND_CEILING)) - 1
    idx = max(0, min(idx, n - 1))
    return sorted_values[idx]


def _cost_statistics(costs: list[Decimal]) -> CostStatistics:
    ordered = sorted(costs)
    n = len(ordered)
    mean = sum(ordered, Decimal(0)) / Decimal(n)
    return CostStatistics(
        sample_count=n,
        minimum_usd=_usd(ordered[0]),
        median_usd=_usd(_percentile(ordered, Decimal("0.5"))),
        mean_usd=_usd(mean),
        p75_usd=_usd(_percentile(ordered, Decimal("0.75"))),
        p95_usd=_usd(_percentile(ordered, Decimal("0.95"))),
        maximum_usd=_usd(ordered[-1]),
    )


def _verify_ancestor(root: Path, ancestor: str) -> bool:
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def _databento_client_version() -> str:
    try:
        return importlib_metadata.version("databento")
    except importlib_metadata.PackageNotFoundError:
        return "not installed"


def _load_and_verify_manifests(
    source_path: Path, split_path: Path
) -> tuple[SourceManifest, SplitManifest, str, str]:
    source_payload = load_manifest(source_path)
    split_payload = load_manifest(split_path)
    verify_manifest_hash(source_payload)
    verify_manifest_hash(split_payload)
    source = parse_source_manifest(source_payload)
    split = parse_split_manifest(split_payload)
    if split.final_test_access_status != "sealed":
        raise PlanValidationError("Split manifest final_test_access_status must be 'sealed'.")
    if source.qualification_status != "qualified":
        raise PlanValidationError("Source manifest qualification_status is not 'qualified'.")
    if source.options.validation_method != "chunked_symbology_resolution":
        raise PlanValidationError(
            "Options selector validation method is not the accepted chunked method."
        )
    stored_hash = source_payload["manifest_hash"]
    split_hash = split_payload["manifest_hash"]
    assert isinstance(stored_hash, str)
    assert isinstance(split_hash, str)
    return source, split, stored_hash, split_hash


def _development_sessions(split: SplitManifest) -> list[date]:
    training = session_dates(split.calendar_name, split.training_start, split.training_end)
    validation = session_dates(split.calendar_name, split.validation_start, split.validation_end)
    return sorted(set(training) | set(validation))


def _record_estimate(
    raw_estimates: list[MetadataEstimateModel], estimate: MetadataEstimate
) -> Decimal:
    raw_estimates.append(
        MetadataEstimateModel(
            dataset=estimate.dataset,
            schema_name=estimate.schema,
            symbol=estimate.symbol,
            stype_in=estimate.stype_in,
            window_start=estimate.window_start,
            window_end=estimate.window_end,
            record_count=estimate.record_count,
            billable_size_bytes=estimate.billable_size_bytes,
            cost_usd=_usd(estimate.cost_usd),
            retries=estimate.retries,
        )
    )
    return estimate.cost_usd


def _build_catalog_wave(
    estimator: MetadataEstimator,
    config: AcquisitionConfig,
    split: SplitManifest,
    raw_estimates: list[MetadataEstimateModel],
) -> CatalogWave:
    schemas = [
        (config.underlying.dataset, config.underlying.definition_schema, config.underlying.symbol),
        (config.underlying.dataset, config.underlying.daily_schema, config.underlying.symbol),
        (config.underlying.dataset, config.underlying.statistics_schema, config.underlying.symbol),
        (config.options.dataset, config.options.definition_schema, config.options.parent_symbol),
    ]
    periods = (
        ("training", split.training_start, split.training_end),
        ("validation", split.validation_start, split.validation_end),
        ("test_reserved", split.test_start, split.test_end),
    )
    stype_in_by_dataset = {
        config.underlying.dataset: config.underlying.symbol_type,
        config.options.dataset: config.options.symbol_type,
    }
    estimates: list[CatalogWaveEstimate] = []
    development_total = Decimal(0)
    test_total = Decimal(0)
    for dataset, schema, symbol in schemas:
        for period, start, end in periods:
            window_start, window_end = full_day_range_window(start, end)
            estimate = estimator.estimate(
                dataset=dataset,
                schema=schema,
                symbol=symbol,
                stype_in=stype_in_by_dataset[dataset],
                start=window_start,
                end=window_end,
            )
            cost = _record_estimate(raw_estimates, estimate)
            estimates.append(
                CatalogWaveEstimate(
                    dataset=dataset,
                    schema_name=schema,
                    period=period,
                    estimated_record_count=estimate.record_count,
                    estimated_billable_size_bytes=estimate.billable_size_bytes,
                    estimated_cost_usd=_usd(cost),
                )
            )
            if period == "test_reserved":
                test_total += cost
            else:
                development_total += cost
    return CatalogWave(
        estimates=estimates,
        development_total_cost_usd=_usd(development_total),
        test_reserved_total_cost_usd=_usd(test_total),
    )


def _build_pilot_plan(
    estimator: MetadataEstimator,
    config: AcquisitionConfig,
    split: SplitManifest,
    raw_estimates: list[MetadataEstimateModel],
) -> PilotPlan:
    month_label, month_sessions = select_pilot_month(
        split.calendar_name, config.pilot_candidate_year
    )
    for session in month_sessions:
        if not (split.training_start <= session <= split.training_end):
            raise PlanValidationError(
                f"Pilot session {session.isoformat()} falls outside the training split."
            )

    requests: list[PilotRequestSpec] = []
    total = Decimal(0)

    arcx_start, arcx_end = full_day_range_window(month_sessions[0], month_sessions[-1])
    arcx_estimate = estimator.estimate(
        dataset=config.underlying.dataset,
        schema=config.underlying.daily_schema,
        symbol=config.underlying.symbol,
        stype_in=config.underlying.symbol_type,
        start=arcx_start,
        end=arcx_end,
    )
    total += _record_estimate(raw_estimates, arcx_estimate)
    requests.append(
        PilotRequestSpec(
            dataset=arcx_estimate.dataset,
            schema_name=arcx_estimate.schema,
            symbol=arcx_estimate.symbol,
            stype_in=arcx_estimate.stype_in,
            window_start=arcx_estimate.window_start,
            window_end=arcx_estimate.window_end,
            estimated_record_count=arcx_estimate.record_count,
            estimated_billable_size_bytes=arcx_estimate.billable_size_bytes,
            estimated_cost_usd=_usd(arcx_estimate.cost_usd),
        )
    )

    opra_def_estimate = estimator.estimate(
        dataset=config.options.dataset,
        schema=config.options.definition_schema,
        symbol=config.options.parent_symbol,
        stype_in=config.options.symbol_type,
        start=arcx_start,
        end=arcx_end,
    )
    total += _record_estimate(raw_estimates, opra_def_estimate)
    requests.append(
        PilotRequestSpec(
            dataset=opra_def_estimate.dataset,
            schema_name=opra_def_estimate.schema,
            symbol=opra_def_estimate.symbol,
            stype_in=opra_def_estimate.stype_in,
            window_start=opra_def_estimate.window_start,
            window_end=opra_def_estimate.window_end,
            estimated_record_count=opra_def_estimate.record_count,
            estimated_billable_size_bytes=opra_def_estimate.billable_size_bytes,
            estimated_cost_usd=_usd(opra_def_estimate.cost_usd),
        )
    )

    for session in month_sessions:
        window_start, window_end = quote_window(split.calendar_name, session)
        quote_estimate = estimator.estimate(
            dataset=config.options.dataset,
            schema=config.options.quote_schema,
            symbol=config.options.parent_symbol,
            stype_in=config.options.symbol_type,
            start=window_start,
            end=window_end,
        )
        total += _record_estimate(raw_estimates, quote_estimate)
        requests.append(
            PilotRequestSpec(
                dataset=quote_estimate.dataset,
                schema_name=quote_estimate.schema,
                symbol=quote_estimate.symbol,
                stype_in=quote_estimate.stype_in,
                window_start=quote_estimate.window_start,
                window_end=quote_estimate.window_end,
                estimated_record_count=quote_estimate.record_count,
                estimated_billable_size_bytes=quote_estimate.billable_size_bytes,
                estimated_cost_usd=_usd(quote_estimate.cost_usd),
            )
        )

    within_cap = total <= config.budget.maximum_pilot_spend_usd
    return PilotPlan(
        selected_month=month_label,
        selected_sessions=month_sessions,
        requests=requests,
        estimated_total_cost_usd=_usd(total),
        maximum_allowed_total_usd=_usd(config.budget.maximum_pilot_spend_usd),
        within_cap=within_cap,
        storage_path_plan=f"data/raw/pilot/{month_label}/ (not created; planning only)",
        rejection_conditions=[
            "reject if the pilot total estimated cost exceeds maximum_pilot_spend_usd",
            "reject if any OPRA cbbo-1m session request returns a zero record count "
            "for a regular trading session",
            "reject if any required ARCX or OPRA schema is unavailable for the pilot month",
            "reject if the actual billed size diverges materially from the provider "
            "estimate for any request",
            "reject if any pilot request would require a time-series, batch, or live API call",
        ],
        manual_authorization_required=True,
        download_command_disabled=True,
    )


def _strategy_projection(
    strategy_id: str,
    name: str,
    scheduled_session_count: int,
    cost_stats: CostStatistics | None,
    config: AcquisitionConfig,
    catalog_dev_total: Decimal,
    pilot_total: Decimal,
    pilot_within_cap: bool,
    test_reserve_ok: bool,
) -> tuple[StrategyProjection, Decimal | None]:
    if cost_stats is None:
        return (
            StrategyProjection(
                strategy_id=strategy_id,
                name=name,
                scheduled_session_count=0,
                cost_status=COST_STATUS_PENDING_CATALOG,
                projected_quote_cost_usd=None,
                worst_case_quote_cost_usd=None,
                safety_factor=None,
                satisfies_project_cap=False,
                satisfies_unspent_reserve=False,
                satisfies_test_reserve=False,
                satisfies_development_cap=False,
                satisfies_pilot_cap=False,
                rank=None,
            ),
            None,
        )

    p95 = Decimal(cost_stats.p95_usd)
    maximum = Decimal(cost_stats.maximum_usd)
    projected = project_strategy_cost(scheduled_session_count, p95, DEVELOPMENT_SAFETY_FACTOR)
    worst_case = project_worst_case_cost(scheduled_session_count, maximum)

    total_committed = catalog_dev_total + pilot_total + projected
    unspent = config.budget.available_credit_usd - total_committed
    satisfies_project_cap = total_committed <= config.budget.maximum_project_spend_usd
    satisfies_unspent_reserve = unspent >= config.budget.minimum_unspent_reserve_usd
    satisfies_development_cap = projected <= config.budget.maximum_development_quote_spend_usd

    return (
        StrategyProjection(
            strategy_id=strategy_id,
            name=name,
            scheduled_session_count=scheduled_session_count,
            cost_status=COST_STATUS_PROJECTED,
            projected_quote_cost_usd=_usd(projected),
            worst_case_quote_cost_usd=_usd(worst_case),
            safety_factor=str(DEVELOPMENT_SAFETY_FACTOR),
            satisfies_project_cap=satisfies_project_cap,
            satisfies_unspent_reserve=satisfies_unspent_reserve,
            satisfies_test_reserve=test_reserve_ok,
            satisfies_development_cap=satisfies_development_cap,
            satisfies_pilot_cap=pilot_within_cap,
            rank=None,
        ),
        projected,
    )


def plan_acquisition(
    *,
    client: Any,
    config: AcquisitionConfig,
    source_manifest_path: Path,
    split_manifest_path: Path,
    config_path: Path,
    repo_root: Path,
    generated_at: str | None = None,
) -> tuple[AcquisitionPlanReportModel, dict[str, Any]]:
    """Build a complete, metadata-only, budget-bounded acquisition plan.

    Returns:
        A tuple of the validated :class:`AcquisitionPlanReport` and the
        un-hashed acquisition-policy-manifest payload (the caller finalizes
        and writes both).

    Raises:
        PlanValidationError: If the git ancestry, source/split manifests, or
            budget policy fail verification.
    """
    if not _verify_ancestor(repo_root, _REQUIRED_ANCESTOR_COMMIT):
        raise PlanValidationError(
            f"Current HEAD does not descend from required commit {_REQUIRED_ANCESTOR_COMMIT}."
        )

    source, split, source_hash, split_hash = _load_and_verify_manifests(
        source_manifest_path, split_manifest_path
    )
    config_hash = config_sha256(config_path)
    stamp = generated_at or datetime.now(UTC).isoformat()
    git_commit = _git_commit(repo_root)
    git_dirty = _git_dirty(repo_root)

    estimator = MetadataEstimator(client)
    raw_estimates: list[MetadataEstimateModel] = []
    warnings: list[str] = []
    blocking_failures: list[str] = []

    catalog_wave = _build_catalog_wave(estimator, config, split, raw_estimates)
    catalog_dev_total = Decimal(catalog_wave.development_total_cost_usd)

    dev_sessions = _development_sessions(split)
    sampled_sessions = quarterly_sample_sessions(dev_sessions)
    sampled_costs: list[Decimal] = []
    for session in sampled_sessions:
        window_start, window_end = quote_window(split.calendar_name, session)
        estimate = estimator.estimate(
            dataset=config.options.dataset,
            schema=config.options.quote_schema,
            symbol=config.options.parent_symbol,
            stype_in=config.options.symbol_type,
            start=window_start,
            end=window_end,
        )
        cost = _record_estimate(raw_estimates, estimate)
        sampled_costs.append(cost)
    cost_stats = _cost_statistics(sampled_costs)

    pilot_plan = _build_pilot_plan(estimator, config, split, raw_estimates)
    pilot_total = Decimal(pilot_plan.estimated_total_cost_usd)
    if not pilot_plan.within_cap:
        warnings.append(
            f"Pilot plan estimated cost {pilot_plan.estimated_total_cost_usd} exceeds "
            f"maximum_pilot_spend_usd {_usd(config.budget.maximum_pilot_spend_usd)}."
        )

    test_sessions = session_dates(split.calendar_name, split.test_start, split.test_end)
    p95 = Decimal(cost_stats.p95_usd)
    test_projected = project_test_reserve_cost(len(test_sessions), p95)
    test_reserve_ok = test_projected <= config.budget.minimum_final_test_quote_reserve_usd
    if not test_reserve_ok:
        warnings.append(
            "Projected final-test quote reserve exceeds minimum_final_test_quote_reserve_usd."
        )
    test_reserve_projection = TestReserveProjection(
        scheduled_session_count=len(test_sessions),
        sampled_p95_cost_usd=_usd(p95),
        safety_factor=str(TEST_RESERVE_SAFETY_FACTOR),
        projected_cost_usd=_usd(test_projected),
        test_estimate_method="sealed_development_projection",
    )

    projections: list[StrategyProjection] = []
    for definition in STRATEGY_DEFINITIONS:
        if definition.schedule_builder is None:
            projection, _cost = _strategy_projection(
                definition.strategy_id,
                definition.name,
                0,
                None,
                config,
                catalog_dev_total,
                pilot_total,
                pilot_plan.within_cap,
                test_reserve_ok,
            )
        else:
            schedule = definition.schedule_builder(dev_sessions)
            projection, _cost = _strategy_projection(
                definition.strategy_id,
                definition.name,
                len(schedule),
                cost_stats,
                config,
                catalog_dev_total,
                pilot_total,
                pilot_plan.within_cap,
                test_reserve_ok,
            )
        projections.append(projection)

    ranked = rank_strategies(projections)
    top = next((p for p in ranked if p.rank == 1), None)
    recommended_strategy_id = top.strategy_id if top else None
    recommendation_status = "recommended_not_authorized" if top else "no_feasible_plan"
    if recommendation_status == "no_feasible_plan":
        blocking_failures.append(
            "No candidate strategy satisfies every budget constraint; "
            "recommendation_status = no_feasible_plan."
        )

    budget_snapshot = BudgetPolicySnapshot(
        available_credit_usd=_usd(config.budget.available_credit_usd),
        maximum_project_spend_usd=_usd(config.budget.maximum_project_spend_usd),
        minimum_unspent_reserve_usd=_usd(config.budget.minimum_unspent_reserve_usd),
        maximum_pilot_spend_usd=_usd(config.budget.maximum_pilot_spend_usd),
        maximum_single_future_request_usd=_usd(config.budget.maximum_single_future_request_usd),
        maximum_development_quote_spend_usd=_usd(config.budget.maximum_development_quote_spend_usd),
        minimum_final_test_quote_reserve_usd=_usd(
            config.budget.minimum_final_test_quote_reserve_usd
        ),
        require_manual_purchase_approval=config.budget.require_manual_purchase_approval,
        purchase_authorized=False,
    )

    report = AcquisitionPlanReportModel(
        schema_version=SCHEMA_VERSION,
        generated_at=stamp,
        git_commit=git_commit,
        git_dirty=git_dirty,
        source_manifest_hash=source_hash,
        split_manifest_hash=split_hash,
        config_hash=config_hash,
        databento_client_version=_databento_client_version(),
        budget_policy=budget_snapshot,
        catalog_wave=catalog_wave,
        sampling_sessions=sampled_sessions,
        raw_estimates=raw_estimates,
        development_cost_statistics=cost_stats,
        candidate_strategies=ranked,
        test_reserve_projection=test_reserve_projection,
        recommended_strategy_id=recommended_strategy_id,
        recommendation_status=recommendation_status,
        pilot_plan=pilot_plan,
        metadata_call_count=estimator.metadata_call_count,
        retry_count=estimator.retry_count,
        download_attempts=0,
        downloaded_records=0,
        batch_jobs_submitted=0,
        live_connections_opened=0,
        warnings=warnings,
        blocking_failures=blocking_failures,
    )

    policy_payload: dict[str, Any] = {
        "manifest_version": SCHEMA_VERSION,
        "budget_ceiling_usd": _usd(config.budget.maximum_project_spend_usd),
        "minimum_unspent_reserve_usd": _usd(config.budget.minimum_unspent_reserve_usd),
        "minimum_final_test_quote_reserve_usd": _usd(
            config.budget.minimum_final_test_quote_reserve_usd
        ),
        "maximum_pilot_spend_usd": _usd(config.budget.maximum_pilot_spend_usd),
        "approved_datasets": [
            {
                "dataset": config.underlying.dataset,
                "schemas": [
                    config.underlying.definition_schema,
                    config.underlying.daily_schema,
                    config.underlying.statistics_schema,
                ],
            },
            {
                "dataset": config.options.dataset,
                "schemas": [config.options.definition_schema, config.options.quote_schema],
            },
        ],
        "quote_window_rule": (
            "final 10 minutes before the scheduled session close (regular or early), "
            "timezone-aware UTC, half-open [window_start, window_end)"
        ),
        "calendar_sampling_rule": (
            "deterministic quarterly sample: first Wednesday of the middle month, "
            "third Friday of the middle month (or preceding session), and the final "
            "session of the quarter; development sessions only"
        ),
        "candidate_strategy_ids": [d.strategy_id for d in STRATEGY_DEFINITIONS],
        "ranking_rule": (
            "feasible strategies ranked by highest inception-session frequency, then "
            "by lowest projected cost; infeasible or cost-pending strategies "
            f"(including {STRATEGY_D}) are unranked"
        ),
        "recommended_strategy_id": recommended_strategy_id,
        "recommendation_status": recommendation_status,
        "recommended_cost_range_usd": _recommended_cost_range(top),
        "test_projection_method": "sealed_development_projection",
        "symbol_batch_limit": MAX_SYMBOLS_PER_REQUEST,
        "purchase_authorized": False,
        "download_guard_enabled": True,
        "source_manifest_hash": source_hash,
        "split_manifest_hash": split_hash,
        "config_hash": config_hash,
        "generated_at": stamp,
        "git_commit": git_commit,
    }
    return report, policy_payload


def _recommended_cost_range(top: StrategyProjection | None) -> str | None:
    if top is None or top.projected_quote_cost_usd is None:
        return None
    value = Decimal(top.projected_quote_cost_usd)
    band = Decimal(5)
    low = (value // band) * band
    high = low + band
    return f"{low}-{high}"
