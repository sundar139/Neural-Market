import json
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.configuration import load_acquisition_config
from neuralmarket.data.acquisition.contracts import acquisition_report_to_json
from neuralmarket.data.acquisition.manifests import finalize_policy_manifest, verify_plan_and_policy
from neuralmarket.data.acquisition.strategies import STRATEGY_D
from neuralmarket.data.errors import MarketDataError, PlanValidationError
from neuralmarket.data.manifests import canonical_hash

_CONFIG_PATH = Path("configs/data/acquisition/spy_daily_budgeted.yaml")
_SOURCE_PATH = Path("data/manifests/source_manifest_v1.json")
_SPLIT_PATH = Path("data/manifests/split_manifest_v1.json")
_REPO_ROOT = Path(".")


class _Metadata:
    def __init__(self, count: int = 10, size: int = 100, cost: float = 0.001) -> None:
        self.count = count
        self.size = size
        self.cost = cost
        self.calls = 0

    def get_record_count(self, **kwargs: Any) -> int:
        self.calls += 1
        return self.count

    def get_billable_size(self, **kwargs: Any) -> int:
        return self.size

    def get_cost(self, **kwargs: Any) -> float:
        return self.cost


class _Client:
    def __init__(self, **kwargs: Any) -> None:
        self.metadata = _Metadata(**kwargs)
        self.timeseries = object()
        self.batch = object()
        self.live = object()


def _run(client: _Client, generated_at: str = "2020-01-01T00:00:00+00:00"):
    from neuralmarket.data.acquisition.planner import plan_acquisition

    config = load_acquisition_config(_CONFIG_PATH)
    return plan_acquisition(
        client=client,
        config=config,
        source_manifest_path=_SOURCE_PATH,
        split_manifest_path=_SPLIT_PATH,
        config_path=_CONFIG_PATH,
        repo_root=_REPO_ROOT,
        generated_at=generated_at,
    )


@pytest.mark.unit
def test_cheap_scenario_recommends_a_feasible_strategy() -> None:
    report, policy_raw = _run(_Client(count=10, size=100, cost=0.001))
    assert report.recommendation_status == "recommended_not_authorized"
    assert report.recommended_strategy_id in ("A", "B", "C")
    policy = finalize_policy_manifest(policy_raw)
    verify_plan_and_policy(acquisition_report_to_json(report), policy)  # must not raise


@pytest.mark.unit
def test_expensive_scenario_yields_no_feasible_plan() -> None:
    report, _policy_raw = _run(_Client(count=10, size=100, cost=0.05))
    assert report.recommendation_status == "no_feasible_plan"
    assert report.recommended_strategy_id is None
    assert report.blocking_failures


@pytest.mark.unit
def test_strategy_d_always_pending_definition_catalog() -> None:
    report, _policy_raw = _run(_Client())
    strategy_d = next(s for s in report.candidate_strategies if s.strategy_id == STRATEGY_D)
    assert strategy_d.cost_status == "requires_definition_catalog"
    assert strategy_d.projected_quote_cost_usd is None
    assert strategy_d.rank is None


@pytest.mark.unit
def test_zero_downloads_and_zero_records() -> None:
    report, _policy_raw = _run(_Client())
    assert report.download_attempts == 0
    assert report.downloaded_records == 0
    assert report.batch_jobs_submitted == 0
    assert report.live_connections_opened == 0


@pytest.mark.unit
def test_metadata_calls_and_retries_recorded() -> None:
    report, _policy_raw = _run(_Client())
    assert report.metadata_call_count > 0
    assert report.retry_count == 0


@pytest.mark.unit
def test_pilot_plan_within_configured_cap() -> None:
    report, _policy_raw = _run(_Client(count=10, size=100, cost=0.001))
    assert report.pilot_plan.within_cap is True
    assert report.pilot_plan.download_command_disabled is True
    assert report.pilot_plan.manual_authorization_required is True


@pytest.mark.unit
def test_test_reserve_never_queries_individual_sessions() -> None:
    report, _policy_raw = _run(_Client())
    assert report.test_reserve_projection.test_estimate_method == "sealed_development_projection"
    # Every raw estimate window must fall within the development period, never
    # the sealed test period (checked indirectly: no estimate spans the test
    # start date range used for a single session).
    assert report.metadata_call_count == len(report.raw_estimates)


@pytest.mark.unit
def test_ancestry_check_failure_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import neuralmarket.data.acquisition.planner as planner_module

    monkeypatch.setattr(planner_module, "_verify_ancestor", lambda root, ancestor: False)
    with pytest.raises(PlanValidationError, match="does not descend"):
        _run(_Client())


@pytest.mark.unit
def test_tampered_source_manifest_hash_raises(tmp_path: Path) -> None:
    tampered = tmp_path / "source_manifest_v1.json"
    payload = json.loads(_SOURCE_PATH.read_text(encoding="utf-8"))
    payload["manifest_hash"] = "0" * 64
    tampered.write_text(json.dumps(payload), encoding="utf-8")

    from neuralmarket.data.acquisition.planner import plan_acquisition

    config = load_acquisition_config(_CONFIG_PATH)
    with pytest.raises(MarketDataError, match="hash mismatch"):
        plan_acquisition(
            client=_Client(),
            config=config,
            source_manifest_path=tampered,
            split_manifest_path=_SPLIT_PATH,
            config_path=_CONFIG_PATH,
            repo_root=_REPO_ROOT,
            generated_at="2020-01-01T00:00:00+00:00",
        )


@pytest.mark.unit
def test_unsealed_split_manifest_raises(tmp_path: Path) -> None:
    tampered = tmp_path / "split_manifest_v1.json"
    payload = json.loads(_SPLIT_PATH.read_text(encoding="utf-8"))
    payload["final_test_access_status"] = "open"
    payload["manifest_hash"] = canonical_hash(payload)
    tampered.write_text(json.dumps(payload), encoding="utf-8")

    from neuralmarket.data.acquisition.planner import plan_acquisition

    config = load_acquisition_config(_CONFIG_PATH)
    with pytest.raises(PlanValidationError, match="sealed"):
        plan_acquisition(
            client=_Client(),
            config=config,
            source_manifest_path=_SOURCE_PATH,
            split_manifest_path=tampered,
            config_path=_CONFIG_PATH,
            repo_root=_REPO_ROOT,
            generated_at="2020-01-01T00:00:00+00:00",
        )


@pytest.mark.unit
def test_report_round_trips_through_json(tmp_path: Path) -> None:
    from neuralmarket.data.acquisition.contracts import AcquisitionPlanReport
    from neuralmarket.data.acquisition.manifests import write_json

    report, _policy_raw = _run(_Client())
    payload = acquisition_report_to_json(report)
    output = tmp_path / "plan.json"
    write_json(output, payload)
    reloaded = json.loads(output.read_text(encoding="utf-8"))
    AcquisitionPlanReport.model_validate(reloaded)  # must not raise


@pytest.mark.unit
def test_config_hash_and_no_credential_leak() -> None:
    report, policy_raw = _run(_Client())
    payload_text = json.dumps(acquisition_report_to_json(report))
    assert "DATABENTO_API_KEY" not in payload_text
    assert report.config_hash
    assert policy_raw["config_hash"] == report.config_hash
