from __future__ import annotations

import pytest

from neuralmarket.data.research import baseline_suite as suite_module
from neuralmarket.data.research import benchmark as benchmark_module
from neuralmarket.data.research.baseline_suite import (
    COMPARATOR_NAMES,
    EVALUATED_COMPARATORS,
    BaselineSuiteSpec,
    ComparatorEntry,
    ComparatorRegistry,
    build_comparator_registry,
)
from neuralmarket.eval import scorecard as scorecard_module
from neuralmarket.eval.scorecard import MetricSpecification

pytestmark = pytest.mark.unit

_ACCEPTED_METRIC_SPEC_HASH = "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"


class TestSuiteSpec:
    def test_seeds_are_frozen_and_distinct_from_existing_baselines(self) -> None:
        spec = BaselineSuiteSpec()
        metric = MetricSpecification()
        seeds = [spec.iid_bootstrap_seed, spec.block_bootstrap_seed, spec.gjr_garch_seed]
        assert seeds == [2027, 2029, 2039]
        assert len(set(seeds)) == 3
        assert not set(seeds) & {metric.gbm_seed, metric.heston_seed}

    def test_block_convention_is_frozen(self) -> None:
        spec = BaselineSuiteSpec()
        assert spec.block_bootstrap_method == "circular_moving_block"
        assert spec.block_bootstrap_block_length == 22
        assert "circular_wrap" in spec.block_bootstrap_boundary_policy

    def test_spec_hash_is_deterministic_and_config_sensitive(self) -> None:
        assert BaselineSuiteSpec().spec_hash() == BaselineSuiteSpec().spec_hash()
        assert (
            BaselineSuiteSpec(iid_bootstrap_seed=1).spec_hash() != BaselineSuiteSpec().spec_hash()
        )


class TestComparatorRegistry:
    def test_hash_is_deterministic(self) -> None:
        first = build_comparator_registry(BaselineSuiteSpec())
        second = build_comparator_registry(BaselineSuiteSpec())
        assert first.registry_hash == second.registry_hash
        assert len(first.registry_hash) == 64

    def test_changed_comparator_config_changes_hash(self) -> None:
        changed = build_comparator_registry(BaselineSuiteSpec(block_bootstrap_seed=999))
        assert changed.registry_hash != build_comparator_registry(BaselineSuiteSpec()).registry_hash

    def test_complete_protocol_accounting(self) -> None:
        registry = build_comparator_registry(BaselineSuiteSpec())
        names = {entry.name for entry in registry.entries}
        assert names == set(COMPARATOR_NAMES)
        assert set(EVALUATED_COMPARATORS) < names
        for entry in registry.entries:
            assert entry.reason
            assert entry.protocol_source.startswith("reports/protocol/research_protocol_v1.md")

    def test_gjr_egarch_decision_recorded_explicitly(self) -> None:
        entries = {
            entry.name: entry for entry in build_comparator_registry(BaselineSuiteSpec()).entries
        }
        assert entries["gjr_garch"].status == "implemented"
        assert entries["gjr_garch"].protocol_source.endswith(":30")
        assert entries["egarch"].status == "not_selected"
        assert entries["egarch"].protocol_source.endswith(":30")
        assert "alternatives" in entries["egarch"].reason
        assert "validation" in entries["egarch"].reason

    def test_unselected_bootstrap_alternative_recorded(self) -> None:
        entries = {
            entry.name: entry for entry in build_comparator_registry(BaselineSuiteSpec()).entries
        }
        assert entries["stationary_bootstrap"].status == "not_selected"
        assert entries["block_bootstrap"].status == "implemented"
        assert entries["block_bootstrap"].seed == 2029

    def test_accepted_prior_comparators_carry_frozen_seeds(self) -> None:
        entries = {
            entry.name: entry for entry in build_comparator_registry(BaselineSuiteSpec()).entries
        }
        assert entries["gbm"].status == "accepted_prior"
        assert entries["gbm"].seed == MetricSpecification().gbm_seed
        assert entries["heston"].seed == MetricSpecification().heston_seed

    def test_duplicate_comparator_rejected(self) -> None:
        registry = build_comparator_registry(BaselineSuiteSpec())
        duplicated = (*registry.entries, registry.entries[0])
        with pytest.raises(ValueError, match="duplicate"):
            ComparatorRegistry(entries=duplicated, suite_spec=registry.suite_spec)

    def test_missing_comparator_rejected(self) -> None:
        registry = build_comparator_registry(BaselineSuiteSpec())
        with pytest.raises(ValueError, match="accounting mismatch"):
            ComparatorRegistry(entries=registry.entries[:-1], suite_spec=registry.suite_spec)

    def test_unknown_comparator_rejected(self) -> None:
        registry = build_comparator_registry(BaselineSuiteSpec())
        extra = ComparatorEntry(
            name="rough_volatility",
            protocol_requirement="extension",
            protocol_source="reports/protocol/research_protocol_v1.md:41",
            status="not_selected",
            reason="out of confirmatory scope",
        )
        with pytest.raises(ValueError, match="accounting mismatch"):
            ComparatorRegistry(entries=(*registry.entries, extra), suite_spec=registry.suite_spec)

    def test_tampered_registry_hash_rejected(self) -> None:
        registry = build_comparator_registry(BaselineSuiteSpec())
        with pytest.raises(ValueError, match="registry hash mismatch"):
            ComparatorRegistry(
                entries=registry.entries,
                suite_spec=registry.suite_spec,
                registry_hash="f" * 64,
            )


class TestMetricInvariance:
    def test_metric_specification_hash_unchanged(self) -> None:
        assert MetricSpecification().spec_hash() == _ACCEPTED_METRIC_SPEC_HASH
        assert MetricSpecification().version == "research-metric-spec-v1"

    def test_metric_specification_fields_unchanged(self) -> None:
        spec = MetricSpecification()
        assert spec.scorecard.lags == (1, 5, 22, 66)
        assert spec.scorecard.tail_quantiles == (0.01, 0.05, 0.10, 0.90, 0.95, 0.99)
        assert spec.scorecard.min_observations == 252
        assert spec.leverage_convention == "corr(r_t, r2_{t+k}) for k in lags with k > 0"
        assert spec.simulation_horizon_sessions == 63
        assert spec.simulation_paths == 1024
        assert spec.gbm_seed == 1337
        assert spec.heston_seed == 1729

    def test_suite_reuses_the_identical_scorecard_functions(self) -> None:
        assert suite_module.compute_scorecard is scorecard_module.compute_scorecard
        assert suite_module._family_errors is benchmark_module._family_errors
        assert suite_module._scorecard_payload is benchmark_module._scorecard_payload

    def test_no_baseline_specific_scoring_branch(self) -> None:
        import inspect

        source = inspect.getsource(suite_module)
        scoring = source[source.index("# ── evaluation") : source.index("registry = build")]
        for name in EVALUATED_COMPARATORS:
            assert f'== "{name}"' not in scoring
        assert scoring.count("compute_scorecard(") == 1
        assert scoring.count("_family_errors(") == 1


class TestFinalTestIsolation:
    def test_sealed_dates_are_rejected_by_the_shared_series_guard(self) -> None:
        import pandas as pd

        from neuralmarket.data.errors import CoverageError
        from neuralmarket.data.research.underlying import _sealed_test_guard

        _sealed_test_guard(pd.DatetimeIndex(["2023-06-30"], tz="UTC"))
        with pytest.raises(CoverageError, match="sealed final-test"):
            _sealed_test_guard(pd.DatetimeIndex(["2023-07-03"], tz="UTC"))

    def test_suite_module_never_touches_a_provider(self) -> None:
        import inspect

        for module in (
            suite_module,
            __import__("neuralmarket.baselines.bootstrap", fromlist=["x"]),
            __import__("neuralmarket.baselines.garch", fromlist=["x"]),
        ):
            source = inspect.getsource(module)
            assert "dotenv" not in source
            assert "DATABENTO_API_KEY" not in source
            assert "databento.Historical" not in source
