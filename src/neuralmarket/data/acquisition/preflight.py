"""Cost preflight: the last check before a pilot is allowed to spend anything.

Refreshes every planned request's cost via metadata-only calls to
:class:`~neuralmarket.data.acquisition.estimation.MetadataEstimator` and
enforces, in ``Decimal`` throughout (never ``float``):

- no single request may exceed ``maximum_single_request_usd``;
- the fresh total may not exceed ``maximum_spend_usd``;
- no individual request's fresh estimate may exceed its originally planned
  estimate by more than ``estimate_increase_tolerance_fraction`` (checked
  per request, not on the aggregate, so one request's spike can never hide
  inside another request's underrun).

Only :class:`MetadataEstimator` is used here -- no paid/executing provider
type is imported into this module.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.budget import round_usd, to_decimal
from neuralmarket.data.acquisition.estimation import MetadataEstimator
from neuralmarket.data.acquisition.requests import AcquisitionRequest, PilotExecutionConfig


class PilotPreflightConfig(BaseModel):
    """The three cap fields preflight needs, independent of the full pilot YAML shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    maximum_spend_usd: Decimal
    maximum_single_request_usd: Decimal
    estimate_increase_tolerance_fraction: Decimal

    @classmethod
    def from_pilot_execution_config(cls, cfg: PilotExecutionConfig) -> PilotPreflightConfig:
        """Narrow a full :class:`PilotExecutionConfig` to just the cap fields."""
        return cls(
            maximum_spend_usd=cfg.maximum_spend_usd,
            maximum_single_request_usd=cfg.maximum_single_request_usd,
            estimate_increase_tolerance_fraction=cfg.estimate_increase_tolerance_fraction,
        )


class PreflightRejection(BaseModel):
    """One reason a pilot preflight failed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    reason: Literal[
        "single_request_cap_exceeded", "total_cap_exceeded", "unexplained_increase"
    ]
    detail: str


class PreflightResult(BaseModel):
    """The outcome of refreshing and cap-checking every request in a pilot plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fresh_estimates: dict[str, str]
    planned_total_usd: str
    fresh_total_usd: str
    increase_fraction: str
    within_single_request_cap: bool
    within_total_cap: bool
    within_increase_tolerance: bool
    rejections: list[PreflightRejection]
    passed: bool
    metadata_call_count: int
    retry_count: int


def run_preflight(
    *,
    estimator: MetadataEstimator,
    requests: list[AcquisitionRequest],
    config: PilotPreflightConfig | PilotExecutionConfig,
) -> PreflightResult:
    """Refresh cost estimates for every request and enforce spend caps.

    Calls ``estimator.estimate(...)`` once per request (metadata-only, no
    paid download), then compares the fresh totals and per-request deltas
    against ``config`` in ``Decimal`` throughout.
    """
    if not isinstance(config, PilotPreflightConfig):
        config = PilotPreflightConfig.from_pilot_execution_config(config)

    rejections: list[PreflightRejection] = []
    fresh_estimates: dict[str, str] = {}
    fresh_total = Decimal("0")
    planned_total = Decimal("0")
    tolerance_multiplier = Decimal("1") + config.estimate_increase_tolerance_fraction

    for request in requests:
        estimate = estimator.estimate(
            dataset=request.dataset,
            schema=request.schema_name,
            symbol=request.symbols[0],
            stype_in=request.stype_in,
            start=request.start,
            end=request.end_exclusive,
        )
        fresh_cost = to_decimal(estimate.cost_usd)
        planned_cost = to_decimal(request.estimated_cost)

        fresh_estimates[request.request_id] = str(fresh_cost)
        fresh_total += fresh_cost
        planned_total += planned_cost

        if fresh_cost > config.maximum_single_request_usd:
            rejections.append(
                PreflightRejection(
                    request_id=request.request_id,
                    reason="single_request_cap_exceeded",
                    detail=(
                        f"fresh estimate {fresh_cost} exceeds single-request cap "
                        f"{config.maximum_single_request_usd}"
                    ),
                )
            )

        allowed_cost = planned_cost * tolerance_multiplier
        if fresh_cost > allowed_cost:
            rejections.append(
                PreflightRejection(
                    request_id=request.request_id,
                    reason="unexplained_increase",
                    detail=(
                        f"fresh estimate {fresh_cost} exceeds planned {planned_cost} by more "
                        f"than tolerance {config.estimate_increase_tolerance_fraction} "
                        f"(allowed up to {allowed_cost})"
                    ),
                )
            )

    within_single_request_cap = not any(
        r.reason == "single_request_cap_exceeded" for r in rejections
    )
    within_increase_tolerance = not any(r.reason == "unexplained_increase" for r in rejections)
    within_total_cap = fresh_total <= config.maximum_spend_usd
    if not within_total_cap:
        rejections.append(
            PreflightRejection(
                request_id="__total__",
                reason="total_cap_exceeded",
                detail=(
                    f"fresh total {fresh_total} exceeds total spend cap "
                    f"{config.maximum_spend_usd}"
                ),
            )
        )

    increase_fraction = (
        (fresh_total - planned_total) / planned_total if planned_total != 0 else Decimal("0")
    )

    return PreflightResult(
        fresh_estimates=fresh_estimates,
        planned_total_usd=str(round_usd(planned_total)),
        fresh_total_usd=str(round_usd(fresh_total)),
        increase_fraction=str(increase_fraction),
        within_single_request_cap=within_single_request_cap,
        within_total_cap=within_total_cap,
        within_increase_tolerance=within_increase_tolerance,
        rejections=rejections,
        passed=not rejections,
        metadata_call_count=estimator.metadata_call_count,
        retry_count=estimator.retry_count,
    )
