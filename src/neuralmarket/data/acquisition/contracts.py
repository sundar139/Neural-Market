"""Typed, account-neutral contracts for acquisition planning and policy.

Monetary fields are serialized as decimal strings (never binary floats) so JSON
round-trips exactly. These models back both the tracked
``acquisition_policy_v1.json`` manifest and the ignored local
``acquisition_plan.local.json`` report; each derives a JSON Schema via
:func:`neuralmarket.data.contracts.json_schema_for`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from neuralmarket.data.contracts import SCHEMA_VERSION, AwareUTCDatetime


class MetadataEstimateModel(BaseModel):
    """One account-neutral metadata estimate, as recorded in the local report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    schema_name: str
    symbol: str
    stype_in: str
    window_start: AwareUTCDatetime
    window_end: AwareUTCDatetime
    record_count: int = Field(ge=0)
    billable_size_bytes: int = Field(ge=0)
    cost_usd: str
    retries: int = Field(ge=0)


class CostStatistics(BaseModel):
    """Sampled per-window cost summary statistics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_count: int = Field(ge=1)
    minimum_usd: str
    median_usd: str
    mean_usd: str
    p75_usd: str
    p95_usd: str
    maximum_usd: str


class StrategyProjection(BaseModel):
    """Projected development-quote acquisition cost for one candidate strategy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str
    name: str
    scheduled_session_count: int = Field(ge=0)
    cost_status: str
    projected_quote_cost_usd: str | None
    worst_case_quote_cost_usd: str | None
    safety_factor: str | None
    satisfies_project_cap: bool
    satisfies_unspent_reserve: bool
    satisfies_test_reserve: bool
    satisfies_development_cap: bool
    satisfies_pilot_cap: bool
    rank: int | None


class TestReserveProjection(BaseModel):
    """Final-test quote cost projection, derived only from development sampling."""

    __test__ = False  # not a pytest test class, despite the name

    model_config = ConfigDict(extra="forbid", frozen=True)

    scheduled_session_count: int = Field(ge=0)
    sampled_p95_cost_usd: str
    safety_factor: str
    projected_cost_usd: str
    test_estimate_method: str

    @model_validator(mode="after")
    def _check_method(self) -> TestReserveProjection:
        if self.test_estimate_method != "sealed_development_projection":
            raise ValueError(
                "test_estimate_method must be 'sealed_development_projection'; "
                "final-test sessions are never queried individually"
            )
        return self


class PilotRequestSpec(BaseModel):
    """One planned (not executed) pilot-wave metadata request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    schema_name: str
    symbol: str
    stype_in: str
    window_start: AwareUTCDatetime
    window_end: AwareUTCDatetime
    estimated_record_count: int = Field(ge=0)
    estimated_billable_size_bytes: int = Field(ge=0)
    estimated_cost_usd: str


class PilotPlan(BaseModel):
    """The bounded, training-only pilot acquisition plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    selected_month: str
    selected_sessions: list[date]
    requests: list[PilotRequestSpec]
    estimated_total_cost_usd: str
    maximum_allowed_total_usd: str
    within_cap: bool
    storage_path_plan: str
    rejection_conditions: list[str]
    manual_authorization_required: bool
    download_command_disabled: bool = True

    @model_validator(mode="after")
    def _check_disabled(self) -> PilotPlan:
        if not self.download_command_disabled:
            raise ValueError("the pilot plan must never enable a callable download command")
        return self


class CatalogWaveEstimate(BaseModel):
    """One full-day-range definition/daily/statistics catalog cost estimate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    schema_name: str
    period: str
    estimated_record_count: int = Field(ge=0)
    estimated_billable_size_bytes: int = Field(ge=0)
    estimated_cost_usd: str


class CatalogWave(BaseModel):
    """Catalog-wave estimates: ARCX definitions/daily/statistics, OPRA definitions.

    Training and validation are estimated as development cost; the test period
    is estimated separately and reserved, never merged into development storage.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    estimates: list[CatalogWaveEstimate]
    development_total_cost_usd: str
    test_reserved_total_cost_usd: str


class BudgetPolicySnapshot(BaseModel):
    """JSON-serializable snapshot of a validated :class:`BudgetPolicy`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    available_credit_usd: str
    maximum_project_spend_usd: str
    minimum_unspent_reserve_usd: str
    maximum_pilot_spend_usd: str
    maximum_single_future_request_usd: str
    maximum_development_quote_spend_usd: str
    minimum_final_test_quote_reserve_usd: str
    require_manual_purchase_approval: bool
    purchase_authorized: bool

    @model_validator(mode="after")
    def _check_unauthorized(self) -> BudgetPolicySnapshot:
        if self.purchase_authorized:
            raise ValueError("purchase_authorized must be false for this milestone")
        return self


class AcquisitionPlanReport(BaseModel):
    """The full, account-specific acquisition plan (ignored local report)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    generated_at: str
    git_commit: str | None
    git_dirty: bool | None
    source_manifest_hash: str
    split_manifest_hash: str
    config_hash: str
    databento_client_version: str
    budget_policy: BudgetPolicySnapshot
    catalog_wave: CatalogWave
    sampling_sessions: list[date]
    raw_estimates: list[MetadataEstimateModel]
    development_cost_statistics: CostStatistics
    candidate_strategies: list[StrategyProjection]
    test_reserve_projection: TestReserveProjection
    recommended_strategy_id: str | None
    recommendation_status: str
    pilot_plan: PilotPlan
    metadata_call_count: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    download_attempts: int = Field(ge=0)
    downloaded_records: int = Field(ge=0)
    batch_jobs_submitted: int = Field(ge=0)
    live_connections_opened: int = Field(ge=0)
    warnings: list[str]
    blocking_failures: list[str]

    @model_validator(mode="after")
    def _check_zero_acquisition(self) -> AcquisitionPlanReport:
        if (
            self.download_attempts != 0
            or self.downloaded_records != 0
            or self.batch_jobs_submitted != 0
            or self.live_connections_opened != 0
        ):
            raise ValueError("acquisition planning must never acquire, batch, or stream records")
        return self


class ApprovedDataset(BaseModel):
    """One dataset/schema pairing approved for acquisition planning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    schemas: list[str]


class AcquisitionPolicyManifest(BaseModel):
    """Tracked, account-neutral acquisition governance manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_version: str = SCHEMA_VERSION
    budget_ceiling_usd: str
    minimum_unspent_reserve_usd: str
    minimum_final_test_quote_reserve_usd: str
    maximum_pilot_spend_usd: str
    approved_datasets: list[ApprovedDataset]
    quote_window_rule: str
    calendar_sampling_rule: str
    candidate_strategy_ids: list[str]
    ranking_rule: str
    recommended_strategy_id: str | None
    recommendation_status: str
    recommended_cost_range_usd: str | None
    test_projection_method: str
    symbol_batch_limit: int = Field(ge=1)
    purchase_authorized: bool
    download_guard_enabled: bool
    source_manifest_hash: str
    split_manifest_hash: str
    config_hash: str
    generated_at: str
    git_commit: str | None
    manifest_hash: str

    @model_validator(mode="after")
    def _check_governance(self) -> AcquisitionPolicyManifest:
        if self.purchase_authorized:
            raise ValueError("purchase_authorized must be false for this milestone")
        if not self.download_guard_enabled:
            raise ValueError("download_guard_enabled must remain true")
        return self


ACQUISITION_CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "acquisition_policy": AcquisitionPolicyManifest,
    "acquisition_plan": AcquisitionPlanReport,
}


def acquisition_report_to_json(report: AcquisitionPlanReport) -> dict[str, Any]:
    """Serialize an :class:`AcquisitionPlanReport` to a plain JSON-safe dict."""
    return report.model_dump(mode="json")
