from datetime import UTC, date, datetime

import pytest

from neuralmarket.data.acquisition.contracts import (
    AcquisitionPlanReport,
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
from neuralmarket.data.acquisition.manifests import (
    canonical_policy_hash,
    finalize_policy_manifest,
    load_json,
    parse_plan_report,
    parse_policy_manifest,
    verify_plan_and_policy,
    verify_policy_hash,
    write_json,
)
from neuralmarket.data.errors import PlanValidationError

_TS = datetime(2019, 1, 2, 20, 50, tzinfo=UTC)
_TE = datetime(2019, 1, 2, 21, 0, tzinfo=UTC)


def _report(**overrides: object) -> AcquisitionPlanReport:
    fields: dict[str, object] = {
        "generated_at": "2020-01-01T00:00:00+00:00",
        "git_commit": "abc123",
        "git_dirty": False,
        "source_manifest_hash": "h1",
        "split_manifest_hash": "h2",
        "config_hash": "h3",
        "databento_client_version": "0.1.0",
        "budget_policy": BudgetPolicySnapshot(
            available_credit_usd="125.00",
            maximum_project_spend_usd="95.00",
            minimum_unspent_reserve_usd="30.00",
            maximum_pilot_spend_usd="5.00",
            maximum_single_future_request_usd="10.00",
            maximum_development_quote_spend_usd="45.00",
            minimum_final_test_quote_reserve_usd="25.00",
            require_manual_purchase_approval=True,
            purchase_authorized=False,
        ),
        "catalog_wave": CatalogWave(
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
        ),
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
        "development_cost_statistics": CostStatistics(
            sample_count=5,
            minimum_usd="0.01",
            median_usd="0.02",
            mean_usd="0.02",
            p75_usd="0.03",
            p95_usd="0.04",
            maximum_usd="0.05",
        ),
        "candidate_strategies": [
            StrategyProjection(
                strategy_id="A",
                name="Daily",
                scheduled_session_count=100,
                cost_status="provider_estimate_projection",
                projected_quote_cost_usd="5.00",
                worst_case_quote_cost_usd="6.00",
                safety_factor="1.25",
                satisfies_project_cap=True,
                satisfies_unspent_reserve=True,
                satisfies_test_reserve=True,
                satisfies_development_cap=True,
                satisfies_pilot_cap=True,
                rank=1,
            )
        ],
        "test_reserve_projection": TestReserveProjection(
            scheduled_session_count=100,
            sampled_p95_cost_usd="0.04",
            safety_factor="1.50",
            projected_cost_usd="6.00",
            test_estimate_method="sealed_development_projection",
        ),
        "recommended_strategy_id": "A",
        "recommendation_status": "recommended_not_authorized",
        "pilot_plan": PilotPlan(
            selected_month="2019-01",
            selected_sessions=[date(2019, 1, 2)],
            requests=[
                PilotRequestSpec(
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
            ],
            estimated_total_cost_usd="0.01",
            maximum_allowed_total_usd="5.00",
            within_cap=True,
            storage_path_plan="data/raw/pilot/2019-01/",
            rejection_conditions=["reject if over cap"],
            manual_authorization_required=True,
            download_command_disabled=True,
        ),
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


def _policy_raw() -> dict:
    return {
        "manifest_version": "1.0",
        "budget_ceiling_usd": "95.00",
        "minimum_unspent_reserve_usd": "30.00",
        "minimum_final_test_quote_reserve_usd": "25.00",
        "maximum_pilot_spend_usd": "5.00",
        "approved_datasets": [{"dataset": "ARCX.PILLAR", "schemas": ["definition"]}],
        "quote_window_rule": "final 10 minutes",
        "calendar_sampling_rule": "quarterly",
        "candidate_strategy_ids": ["A", "B", "C", "D"],
        "ranking_rule": "frequency then cost",
        "recommended_strategy_id": "A",
        "recommendation_status": "recommended_not_authorized",
        "recommended_cost_range_usd": "0-5",
        "test_projection_method": "sealed_development_projection",
        "symbol_batch_limit": 2000,
        "purchase_authorized": False,
        "download_guard_enabled": True,
        "source_manifest_hash": "h1",
        "split_manifest_hash": "h2",
        "config_hash": "h3",
        "generated_at": "2020-01-01T00:00:00+00:00",
        "git_commit": "abc123",
    }


@pytest.mark.unit
def test_canonical_policy_hash_excludes_volatile_fields() -> None:
    a = _policy_raw()
    b = dict(a, generated_at="2099-01-01T00:00:00+00:00")
    assert canonical_policy_hash(a) == canonical_policy_hash(b)


@pytest.mark.unit
def test_finalize_and_verify_hash_round_trip() -> None:
    payload = finalize_policy_manifest(_policy_raw())
    verify_policy_hash(payload)  # must not raise


@pytest.mark.unit
def test_verify_policy_hash_detects_tamper() -> None:
    payload = finalize_policy_manifest(_policy_raw())
    payload["budget_ceiling_usd"] = "9999.00"
    with pytest.raises(PlanValidationError, match="hash mismatch"):
        verify_policy_hash(payload)


@pytest.mark.unit
def test_parse_policy_manifest_invalid_raises() -> None:
    with pytest.raises(PlanValidationError):
        parse_policy_manifest({"bogus": True})


@pytest.mark.unit
def test_parse_plan_report_invalid_raises() -> None:
    with pytest.raises(PlanValidationError):
        parse_plan_report({"bogus": True})


def _matching_pair() -> tuple[dict, dict]:
    report = _report(source_manifest_hash="h1", split_manifest_hash="h2", config_hash="h3")
    plan_payload = report.model_dump(mode="json")
    policy_payload = finalize_policy_manifest(_policy_raw())
    return plan_payload, policy_payload


@pytest.mark.unit
def test_verify_plan_and_policy_happy_path() -> None:
    plan_payload, policy_payload = _matching_pair()
    verify_plan_and_policy(plan_payload, policy_payload)  # must not raise


@pytest.mark.unit
def test_verify_plan_and_policy_detects_hash_disagreement() -> None:
    plan_payload, policy_payload = _matching_pair()
    plan_payload["source_manifest_hash"] = "different"
    with pytest.raises(PlanValidationError, match="source-manifest hash"):
        verify_plan_and_policy(plan_payload, policy_payload)


@pytest.mark.unit
def test_verify_plan_and_policy_detects_strategy_disagreement() -> None:
    plan_payload, policy_payload = _matching_pair()
    policy_payload = finalize_policy_manifest(dict(_policy_raw(), recommended_strategy_id="B"))
    with pytest.raises(PlanValidationError, match="recommended strategy"):
        verify_plan_and_policy(plan_payload, policy_payload)


@pytest.mark.unit
def test_verify_plan_and_policy_rejects_purchase_authorized() -> None:
    plan_payload, policy_payload = _matching_pair()
    policy_payload = finalize_policy_manifest(dict(_policy_raw(), purchase_authorized=True))
    with pytest.raises(Exception, match="purchase_authorized"):
        verify_plan_and_policy(plan_payload, policy_payload)


@pytest.mark.unit
def test_verify_plan_and_policy_rejects_nonzero_downloads() -> None:
    # AcquisitionPlanReport's own validator rejects this at parse time, before
    # verify_plan_and_policy's own redundant check would run; both raise
    # PlanValidationError, which is what matters here.
    plan_payload, policy_payload = _matching_pair()
    plan_payload["download_attempts"] = 1
    with pytest.raises(PlanValidationError, match="acqui"):
        verify_plan_and_policy(plan_payload, policy_payload)


@pytest.mark.unit
def test_verify_policy_hash_missing_hash_raises() -> None:
    with pytest.raises(PlanValidationError, match="manifest_hash"):
        verify_policy_hash({"a": 1})


@pytest.mark.unit
def test_load_json_missing_file_raises(tmp_path):  # type: ignore[no-untyped-def]
    with pytest.raises(PlanValidationError, match="not found"):
        load_json(tmp_path / "missing.json")


@pytest.mark.unit
def test_load_json_malformed_raises(tmp_path):  # type: ignore[no-untyped-def]
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(PlanValidationError, match="Unable to read"):
        load_json(path)


@pytest.mark.unit
def test_load_json_non_object_raises(tmp_path):  # type: ignore[no-untyped-def]
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(PlanValidationError, match="must be a JSON object"):
        load_json(path)


@pytest.mark.unit
def test_write_and_load_json_round_trip(tmp_path):  # type: ignore[no-untyped-def]
    path = tmp_path / "out.json"
    write_json(path, {"b": 1, "a": 2})
    assert load_json(path) == {"a": 2, "b": 1}
    assert path.read_text(encoding="utf-8").endswith("\n")


@pytest.mark.unit
def test_verify_plan_and_policy_detects_config_hash_disagreement() -> None:
    plan_payload, policy_payload = _matching_pair()
    plan_payload["config_hash"] = "different"
    with pytest.raises(PlanValidationError, match="configuration hash"):
        verify_plan_and_policy(plan_payload, policy_payload)


@pytest.mark.unit
def test_verify_plan_and_policy_detects_split_hash_disagreement() -> None:
    plan_payload, policy_payload = _matching_pair()
    plan_payload["split_manifest_hash"] = "different"
    with pytest.raises(PlanValidationError, match="split-manifest hash"):
        verify_plan_and_policy(plan_payload, policy_payload)


@pytest.mark.unit
def test_verify_plan_and_policy_detects_recommendation_status_disagreement() -> None:
    plan_payload, policy_payload = _matching_pair()
    policy_payload = finalize_policy_manifest(
        dict(_policy_raw(), recommendation_status="no_feasible_plan")
    )
    with pytest.raises(PlanValidationError, match="recommendation status"):
        verify_plan_and_policy(plan_payload, policy_payload)
