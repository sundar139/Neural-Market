from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from neuralmarket.data.acquisition.contracts import (
    AcquisitionPlanReport,
    AcquisitionPolicyManifest,
    ApprovedDataset,
    BudgetPolicySnapshot,
    CatalogWave,
    CatalogWaveEstimate,
    CostStatistics,
    MetadataEstimateModel,
    PilotPlan,
    PilotRequestSpec,
    StrategyProjection,
    TestReserveProjection,
    acquisition_report_to_json,
)

_TS = datetime(2019, 1, 2, 20, 50, tzinfo=UTC)
_TE = datetime(2019, 1, 2, 21, 0, tzinfo=UTC)


def _budget_snapshot(**overrides: object) -> BudgetPolicySnapshot:
    fields = {
        "available_credit_usd": "125.00",
        "maximum_project_spend_usd": "95.00",
        "minimum_unspent_reserve_usd": "30.00",
        "maximum_pilot_spend_usd": "5.00",
        "maximum_single_future_request_usd": "10.00",
        "maximum_development_quote_spend_usd": "45.00",
        "minimum_final_test_quote_reserve_usd": "25.00",
        "require_manual_purchase_approval": True,
        "purchase_authorized": False,
    }
    fields.update(overrides)
    return BudgetPolicySnapshot(**fields)


def _pilot_plan(**overrides: object) -> PilotPlan:
    request = PilotRequestSpec(
        dataset="OPRA.PILLAR",
        schema_name="cbbo-1m",
        symbol="SPY.OPT",
        stype_in="parent",
        window_start=_TS,
        window_end=_TE,
        estimated_record_count=10,
        estimated_billable_size_bytes=100,
        estimated_cost_usd="0.01",
    )
    fields: dict[str, object] = {
        "selected_month": "2019-01",
        "selected_sessions": [date(2019, 1, 2)],
        "requests": [request],
        "estimated_total_cost_usd": "0.01",
        "maximum_allowed_total_usd": "5.00",
        "within_cap": True,
        "storage_path_plan": "data/raw/pilot/2019-01/",
        "rejection_conditions": ["reject if over cap"],
        "manual_authorization_required": True,
        "download_command_disabled": True,
    }
    fields.update(overrides)
    return PilotPlan(**fields)


def _cost_stats() -> CostStatistics:
    return CostStatistics(
        sample_count=5,
        minimum_usd="0.01",
        median_usd="0.02",
        mean_usd="0.02",
        p75_usd="0.03",
        p95_usd="0.04",
        maximum_usd="0.05",
    )


def _catalog_wave() -> CatalogWave:
    return CatalogWave(
        estimates=[
            CatalogWaveEstimate(
                dataset="ARCX.PILLAR",
                schema_name="definition",
                period="training",
                estimated_record_count=1,
                estimated_billable_size_bytes=1,
                estimated_cost_usd="0.01",
            )
        ],
        development_total_cost_usd="0.01",
        test_reserved_total_cost_usd="0.00",
    )


def _test_reserve() -> TestReserveProjection:
    return TestReserveProjection(
        scheduled_session_count=100,
        sampled_p95_cost_usd="0.04",
        safety_factor="1.50",
        projected_cost_usd="6.00",
        test_estimate_method="sealed_development_projection",
    )


def _strategy(**overrides: object) -> StrategyProjection:
    fields: dict[str, object] = {
        "strategy_id": "A",
        "name": "Daily",
        "scheduled_session_count": 100,
        "cost_status": "provider_estimate_projection",
        "projected_quote_cost_usd": "5.00",
        "worst_case_quote_cost_usd": "6.00",
        "safety_factor": "1.25",
        "satisfies_project_cap": True,
        "satisfies_unspent_reserve": True,
        "satisfies_test_reserve": True,
        "satisfies_development_cap": True,
        "satisfies_pilot_cap": True,
        "rank": 1,
    }
    fields.update(overrides)
    return StrategyProjection(**fields)


def _report(**overrides: object) -> AcquisitionPlanReport:
    fields: dict[str, object] = {
        "generated_at": "2020-01-01T00:00:00+00:00",
        "git_commit": "abc123",
        "git_dirty": False,
        "source_manifest_hash": "h1",
        "split_manifest_hash": "h2",
        "config_hash": "h3",
        "databento_client_version": "0.1.0",
        "budget_policy": _budget_snapshot(),
        "catalog_wave": _catalog_wave(),
        "sampling_sessions": [date(2019, 1, 2)],
        "raw_estimates": [
            MetadataEstimateModel(
                dataset="OPRA.PILLAR",
                schema_name="cbbo-1m",
                symbol="SPY.OPT",
                stype_in="parent",
                window_start=_TS,
                window_end=_TE,
                record_count=1,
                billable_size_bytes=1,
                cost_usd="0.01",
                retries=0,
            )
        ],
        "development_cost_statistics": _cost_stats(),
        "candidate_strategies": [_strategy()],
        "test_reserve_projection": _test_reserve(),
        "recommended_strategy_id": "A",
        "recommendation_status": "recommended_not_authorized",
        "pilot_plan": _pilot_plan(),
        "metadata_call_count": 10,
        "retry_count": 0,
        "download_attempts": 0,
        "downloaded_records": 0,
        "batch_jobs_submitted": 0,
        "live_connections_opened": 0,
        "warnings": [],
        "blocking_failures": [],
    }
    fields.update(overrides)
    return AcquisitionPlanReport(**fields)


@pytest.mark.unit
def test_budget_snapshot_rejects_purchase_authorized() -> None:
    with pytest.raises(ValidationError):
        _budget_snapshot(purchase_authorized=True)


@pytest.mark.unit
def test_test_reserve_projection_rejects_wrong_method() -> None:
    with pytest.raises(ValidationError, match="sealed_development_projection"):
        TestReserveProjection(
            scheduled_session_count=1,
            sampled_p95_cost_usd="0.01",
            safety_factor="1.50",
            projected_cost_usd="0.01",
            test_estimate_method="direct_query",
        )


@pytest.mark.unit
def test_pilot_plan_rejects_enabled_download_command() -> None:
    with pytest.raises(ValidationError, match="download command"):
        _pilot_plan(download_command_disabled=False)


@pytest.mark.unit
def test_plan_report_rejects_nonzero_download_attempts() -> None:
    with pytest.raises(ValidationError, match="never acquire"):
        _report(download_attempts=1)


@pytest.mark.unit
def test_plan_report_rejects_nonzero_downloaded_records() -> None:
    with pytest.raises(ValidationError, match="never acquire"):
        _report(downloaded_records=5)


@pytest.mark.unit
def test_plan_report_rejects_nonzero_batch_jobs() -> None:
    with pytest.raises(ValidationError, match="never acquire"):
        _report(batch_jobs_submitted=1)


@pytest.mark.unit
def test_plan_report_rejects_nonzero_live_connections() -> None:
    with pytest.raises(ValidationError, match="never acquire"):
        _report(live_connections_opened=1)


@pytest.mark.unit
def test_plan_report_valid_serializes_to_json() -> None:
    report = _report()
    payload = acquisition_report_to_json(report)
    assert payload["recommended_strategy_id"] == "A"
    round_tripped = AcquisitionPlanReport.model_validate(payload)
    assert round_tripped == report


@pytest.mark.unit
def test_policy_manifest_rejects_purchase_authorized() -> None:
    with pytest.raises(ValidationError, match="purchase_authorized"):
        AcquisitionPolicyManifest(
            budget_ceiling_usd="95.00",
            minimum_unspent_reserve_usd="30.00",
            minimum_final_test_quote_reserve_usd="25.00",
            maximum_pilot_spend_usd="5.00",
            approved_datasets=[ApprovedDataset(dataset="ARCX.PILLAR", schemas=["definition"])],
            quote_window_rule="final 10 minutes",
            calendar_sampling_rule="quarterly",
            candidate_strategy_ids=["A", "B", "C", "D"],
            ranking_rule="frequency then cost",
            recommended_strategy_id="A",
            recommendation_status="recommended_not_authorized",
            recommended_cost_range_usd="0-5",
            test_projection_method="sealed_development_projection",
            symbol_batch_limit=2000,
            purchase_authorized=True,
            download_guard_enabled=True,
            source_manifest_hash="h1",
            split_manifest_hash="h2",
            config_hash="h3",
            generated_at="2020-01-01T00:00:00+00:00",
            git_commit="abc123",
            manifest_hash="deadbeef",
        )


@pytest.mark.unit
def test_policy_manifest_rejects_disabled_download_guard() -> None:
    with pytest.raises(ValidationError, match="download_guard_enabled"):
        AcquisitionPolicyManifest(
            budget_ceiling_usd="95.00",
            minimum_unspent_reserve_usd="30.00",
            minimum_final_test_quote_reserve_usd="25.00",
            maximum_pilot_spend_usd="5.00",
            approved_datasets=[ApprovedDataset(dataset="ARCX.PILLAR", schemas=["definition"])],
            quote_window_rule="final 10 minutes",
            calendar_sampling_rule="quarterly",
            candidate_strategy_ids=["A", "B", "C", "D"],
            ranking_rule="frequency then cost",
            recommended_strategy_id="A",
            recommendation_status="recommended_not_authorized",
            recommended_cost_range_usd=None,
            test_projection_method="sealed_development_projection",
            symbol_batch_limit=2000,
            purchase_authorized=False,
            download_guard_enabled=False,
            source_manifest_hash="h1",
            split_manifest_hash="h2",
            config_hash="h3",
            generated_at="2020-01-01T00:00:00+00:00",
            git_commit="abc123",
            manifest_hash="deadbeef",
        )
