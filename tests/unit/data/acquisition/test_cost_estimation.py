"""Unit tests for the fail-closed derived cost-estimation fallback."""

from __future__ import annotations

from decimal import Decimal

import pytest

from neuralmarket.data.acquisition.cost_estimation import (
    ACQUISITION_FEED_MODE,
    BYTES_PER_BILLING_GIB,
    CALCULATION_VERSION,
    CONSERVATIVE_MARGIN,
    CostSource,
    CrossValidationStatus,
    PlanCostEntry,
    ProviderCostSample,
    build_derived_estimate,
    conservative_cost,
    cross_validate,
    derive_cost,
    fallback_permitted,
    parse_unit_price_snapshot,
    summarize_plan,
)
from neuralmarket.data.errors import (
    AuthenticationError,
    CostEstimationError,
    EntitlementError,
    ProviderNetworkError,
    RateLimitError,
)

# Known OPRA cbbo-1m reference (checkpoint request e85df5d330c0ea18).
KNOWN_BILLABLE = 5209600
KNOWN_UNIT_PRICE = Decimal("2.0")
KNOWN_DERIVED = Decimal("0.00970363616943359375")
KNOWN_PROVIDER = Decimal("0.009703636169")

DATASET = "OPRA.PILLAR"
SCHEMA = "cbbo-1m"
ACCOUNT = "pilot-account-v1"


def _snapshot(price: object = "2.0", *, mode: str = ACQUISITION_FEED_MODE):
    return parse_unit_price_snapshot(
        [{"mode": mode, "schemas": {SCHEMA: price, "definition": "1.0"}}],
        dataset=DATASET,
        feed_mode=ACQUISITION_FEED_MODE,
        databento_client_version="0.81.0",
        retrieved_at_utc="2026-07-15T02:00:00+00:00",
        expires_at_utc="2026-07-16T02:00:00+00:00",
    )


def _sample(**overrides) -> ProviderCostSample:
    base = {
        "dataset": DATASET,
        "schema": SCHEMA,
        "feed_mode": ACQUISITION_FEED_MODE,
        "account_pricing_context": ACCOUNT,
        "billable_size_bytes": KNOWN_BILLABLE,
        "provider_cost_usd": KNOWN_PROVIDER,
    }
    base.update(overrides)
    return ProviderCostSample(**base)  # type: ignore[arg-type]


def _passing_xval(snapshot=None):
    return cross_validate(
        snapshot or _snapshot(),
        dataset=DATASET,
        schema=SCHEMA,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
        samples=[_sample()],
    )


# --- Formula -----------------------------------------------------------------


def test_known_value_reproduces_provider_get_cost() -> None:
    derived = derive_cost(KNOWN_BILLABLE, KNOWN_UNIT_PRICE)
    assert derived == KNOWN_DERIVED
    assert abs(derived - KNOWN_PROVIDER) <= Decimal("0.000000000001")


def test_divisor_is_two_to_the_thirty() -> None:
    assert BYTES_PER_BILLING_GIB == 2**30
    assert BYTES_PER_BILLING_GIB == 1_073_741_824


def test_gigabyte_divisor_rejected_by_regression() -> None:
    # Using 1e9 instead of 2**30 would not reproduce the provider quote.
    wrong = Decimal(KNOWN_BILLABLE) * KNOWN_UNIT_PRICE / Decimal(1_000_000_000)
    assert abs(wrong - KNOWN_PROVIDER) > Decimal("0.000000000001")


def test_derive_cost_requires_decimal_price() -> None:
    with pytest.raises(CostEstimationError):
        derive_cost(KNOWN_BILLABLE, 2.0)  # type: ignore[arg-type]


def test_derive_cost_rejects_negative_and_bool_size() -> None:
    with pytest.raises(CostEstimationError):
        derive_cost(-1, KNOWN_UNIT_PRICE)
    with pytest.raises(CostEstimationError):
        derive_cost(True, KNOWN_UNIT_PRICE)  # type: ignore[arg-type]


# --- Unit-price parsing ------------------------------------------------------


def test_snapshot_selects_exact_dataset_mode_schema() -> None:
    snap = _snapshot()
    assert snap.dataset == DATASET
    assert snap.feed_mode == ACQUISITION_FEED_MODE
    assert snap.price_for(SCHEMA) == Decimal("2.0")


def test_snapshot_missing_schema_rejected() -> None:
    snap = _snapshot()
    with pytest.raises(CostEstimationError):
        snap.price_for("bbo-1m")


def test_snapshot_missing_mode_rejected() -> None:
    with pytest.raises(CostEstimationError):
        parse_unit_price_snapshot(
            [{"mode": "historical", "schemas": {SCHEMA: "2.0"}}],
            dataset=DATASET,
            feed_mode=ACQUISITION_FEED_MODE,
            databento_client_version="0.81.0",
            retrieved_at_utc="2026-07-15T02:00:00+00:00",
            expires_at_utc="2026-07-16T02:00:00+00:00",
        )


def test_snapshot_duplicate_mode_rejected() -> None:
    with pytest.raises(CostEstimationError):
        parse_unit_price_snapshot(
            [
                {"mode": ACQUISITION_FEED_MODE, "schemas": {SCHEMA: "2.0"}},
                {"mode": ACQUISITION_FEED_MODE, "schemas": {SCHEMA: "3.0"}},
            ],
            dataset=DATASET,
            feed_mode=ACQUISITION_FEED_MODE,
            databento_client_version="0.81.0",
            retrieved_at_utc="2026-07-15T02:00:00+00:00",
            expires_at_utc="2026-07-16T02:00:00+00:00",
        )


@pytest.mark.parametrize("bad", ["-2.0", "0", 2.0, "abc"])
def test_snapshot_invalid_price_rejected(bad: object) -> None:
    with pytest.raises(CostEstimationError):
        _snapshot(bad)


def test_snapshot_hash_changes_with_price() -> None:
    assert _snapshot("2.0").snapshot_hash != _snapshot("2.5").snapshot_hash


# --- Cross-validation --------------------------------------------------------


def test_cross_validation_passes_for_known_opra() -> None:
    result = _passing_xval()
    assert result.passed
    assert result.status is CrossValidationStatus.PASSED
    assert result.sample_count == 1
    assert result.maximum_absolute_error <= Decimal("1e-9")
    assert result.maximum_relative_error <= Decimal("1e-6")


def test_cross_validation_prefers_two_samples() -> None:
    result = cross_validate(
        _snapshot(),
        dataset=DATASET,
        schema=SCHEMA,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
        samples=[
            _sample(),
            _sample(billable_size_bytes=5616000, provider_cost_usd=Decimal("0.010460615158")),
        ],
    )
    assert result.sample_count == 2
    assert result.passed


def test_cross_validation_no_samples_fails_closed() -> None:
    result = cross_validate(
        _snapshot(),
        dataset=DATASET,
        schema=SCHEMA,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
        samples=[],
    )
    assert not result.passed
    assert result.status is CrossValidationStatus.UNAVAILABLE


@pytest.mark.parametrize(
    "override",
    [
        {"schema": "definition"},
        {"dataset": "ARCX.PILLAR"},
        {"feed_mode": "historical"},
        {"account_pricing_context": "other-account"},
    ],
)
def test_cross_validation_incompatible_sample_rejected(override: dict[str, object]) -> None:
    result = cross_validate(
        _snapshot(),
        dataset=DATASET,
        schema=SCHEMA,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
        samples=[_sample(**override)],
    )
    assert result.sample_count == 0
    assert not result.passed


def test_cross_validation_error_above_tolerance_rejected() -> None:
    result = cross_validate(
        _snapshot(),
        dataset=DATASET,
        schema=SCHEMA,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
        samples=[_sample(provider_cost_usd=Decimal("0.05"))],
    )
    assert result.sample_count == 1
    assert not result.passed


# --- Fallback classification -------------------------------------------------


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_http_5xx_permits_fallback(status: int) -> None:
    assert fallback_permitted(http_status=status, failure_category=None)


@pytest.mark.parametrize("category", ["provider_timeout", "provider_network_timeout"])
def test_timeout_permits_fallback(category: str) -> None:
    assert fallback_permitted(http_status=None, failure_category=category)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 429, 501])
def test_disallowed_status_blocks_fallback(status: int) -> None:
    assert not fallback_permitted(http_status=status, failure_category=None)


@pytest.mark.parametrize(
    "category", ["entitlement", "authentication", "rate_limit", "request_contract"]
)
def test_disallowed_category_blocks_fallback(category: str) -> None:
    assert not fallback_permitted(http_status=None, failure_category=category)


@pytest.mark.parametrize(
    ("exc", "eligible"),
    [
        (AuthenticationError("x"), False),
        (EntitlementError("x"), False),
        (RateLimitError("x"), False),
        (ProviderNetworkError("timeout"), True),
    ],
)
def test_classify_exception_eligibility(exc: Exception, eligible: bool) -> None:
    status, category = None, None
    from neuralmarket.data.acquisition.cost_estimation import classify_exception

    status, category = classify_exception(exc)
    assert fallback_permitted(http_status=status, failure_category=category) is eligible


# --- Conservative pricing ----------------------------------------------------


def test_conservative_margin_is_25_percent() -> None:
    assert conservative_cost(KNOWN_DERIVED) == KNOWN_DERIVED * CONSERVATIVE_MARGIN
    assert Decimal("1.25") == CONSERVATIVE_MARGIN


def test_conservative_never_below_raw() -> None:
    assert conservative_cost(KNOWN_DERIVED) >= KNOWN_DERIVED


# --- build_derived_estimate + provenance -------------------------------------


def _estimate(**overrides):
    base = {
        "request_id": "d5352ffb04e4bc83",
        "request_specification_hash": (
            "85e856ad72676bc75f835047e36b58fc86253f8ab3004f456825564cd28d5e08"
        ),
        "dataset": DATASET,
        "schema": SCHEMA,
        "feed_mode": ACQUISITION_FEED_MODE,
        "billable_size_bytes": 5616000,
        "billable_size_response_hash": (
            "09eb21ca300d0ab7150b8917cbae4af68fc4eac9e42290f4826116fd5d2f2f5e"
        ),
        "snapshot": _snapshot(),
        "cross_validation": _passing_xval(),
        "failure_http_status": 504,
        "failure_category": None,
        "calculated_at": "2026-07-15T02:00:00+00:00",
    }
    base.update(overrides)
    return build_derived_estimate(**base)  # type: ignore[arg-type]


def test_build_derived_estimate_happy_path() -> None:
    est = _estimate()
    assert est.cost_source is CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE
    assert est.cost_usd == derive_cost(5616000, Decimal("2.0"))
    assert est.conservative_cost_usd == est.cost_usd * CONSERVATIVE_MARGIN
    assert est.cross_validation_status is CrossValidationStatus.PASSED
    assert est.estimate_hash == est.provenance_hash()


def test_build_blocked_on_ineligible_failure() -> None:
    with pytest.raises(CostEstimationError):
        _estimate(failure_http_status=403, failure_category="entitlement")


def test_build_blocked_on_failed_cross_validation() -> None:
    bad = cross_validate(
        _snapshot(),
        dataset=DATASET,
        schema=SCHEMA,
        feed_mode=ACQUISITION_FEED_MODE,
        account_pricing_context=ACCOUNT,
        samples=[],
    )
    with pytest.raises(CostEstimationError):
        _estimate(cross_validation=bad)


def test_build_blocked_on_wrong_feed_mode() -> None:
    with pytest.raises(CostEstimationError):
        _estimate(feed_mode="historical")


def _binding_inputs(est) -> dict[str, object]:
    return {
        "request_specification_hash": est.request_specification_hash,
        "billable_size_response_hash": est.billable_size_response_hash,
        "unit_price_snapshot_hash": est.unit_price_snapshot_hash,
        "cross_validation_evidence_hash": est.cross_validation_evidence_hash,
        "calculation_version": est.calculation_version,
    }


@pytest.mark.parametrize(
    "mutate",
    ["request_specification_hash", "billable_size_response_hash", "unit_price_snapshot_hash"],
)
def test_provenance_hash_changes_when_input_changes(mutate: str) -> None:
    from dataclasses import replace

    est = _estimate()
    tampered = replace(est, **{mutate: "deadbeef"})
    assert tampered.provenance_hash() != est.estimate_hash


def test_provenance_hash_changes_with_calculation_version() -> None:
    from dataclasses import replace

    est = _estimate()
    tampered = replace(est, calculation_version="derived-cost-v2")
    assert tampered.provenance_hash() != est.estimate_hash
    assert est.calculation_version == CALCULATION_VERSION


# --- Plan-level rollup -------------------------------------------------------


def test_plan_summary_counts_and_caps() -> None:
    entries = [
        PlanCostEntry("a", CostSource.PROVIDER_GET_COST, Decimal("0.24"), Decimal("0.24")),
        PlanCostEntry(
            "b",
            CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE,
            Decimal("0.010460615158"),
            conservative_cost(Decimal("0.010460615158")),
        ),
    ]
    summary = summarize_plan(entries, tracked_total_usd=Decimal("0.46"))
    assert summary.provider_cost_count == 1
    assert summary.derived_cost_count == 1
    assert summary.raw_total_usd == Decimal("0.24") + Decimal("0.010460615158")
    assert summary.within_all_gates


def test_plan_summary_per_request_cap_uses_conservative() -> None:
    # Raw 0.85 is under $1, but conservative 1.0625 exceeds the $1 per-request cap.
    entries = [
        PlanCostEntry(
            "big",
            CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE,
            Decimal("0.85"),
            conservative_cost(Decimal("0.85")),
        ),
    ]
    summary = summarize_plan(entries, tracked_total_usd=Decimal("0.85"))
    assert summary.largest_conservative_request_usd == Decimal("1.0625")
    assert not summary.within_per_request_cap


def test_plan_summary_total_cap_uses_conservative() -> None:
    entries = [
        PlanCostEntry(
            f"r{i}",
            CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE,
            Decimal("0.9"),
            conservative_cost(Decimal("0.9")),
        )
        for i in range(5)
    ]
    summary = summarize_plan(entries, tracked_total_usd=Decimal("4.5"))
    # raw total 4.5 within $5; conservative 5.625 exceeds it.
    assert summary.raw_total_usd == Decimal("4.5")
    assert summary.conservative_total_usd == Decimal("5.625")
    assert not summary.within_total_cap


def test_plan_summary_drift_ceiling_is_1_5x() -> None:
    entries = [
        PlanCostEntry(
            "r",
            CostSource.DERIVED_BILLABLE_SIZE_UNIT_PRICE,
            Decimal("0.30"),
            Decimal("0.375"),
        ),
    ]
    # tracked 0.20 -> ceiling 0.30; conservative 0.375 > 0.30 -> drift fails.
    summary = summarize_plan(entries, tracked_total_usd=Decimal("0.20"))
    assert not summary.within_drift_ceiling
    # tracked 0.30 -> ceiling 0.45; 0.375 <= 0.45 -> ok.
    ok = summarize_plan(entries, tracked_total_usd=Decimal("0.30"))
    assert ok.within_drift_ceiling
