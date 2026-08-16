"""Production-shaped simulator baseline suite: determinism, binding, isolation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.baseline_suite import (
    EVALUATED_COMPARATORS,
    BaselineSuiteSpec,
    SimulatorBaselineSuiteArtifact,
    build_baseline_suite,
    load_accepted_benchmark,
    write_baseline_suite_artifact,
)
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.eval.scorecard import MetricSpecification

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
_INVENTORY = _ROOT / "data/manifests/research_development_inventory_v1.json"
_BENCHMARK = _ROOT / "data/processed/research/benchmark/empirical_benchmark_v1.json"
_SUITE = _ROOT / "data/processed/research/benchmark/simulator_baseline_suite_v1.json"
_RAW_ROOT = _ROOT / "data/raw/databento"
_PROCESSED_ROOT = _ROOT / "data/processed"


def _inventory() -> ResearchInventory:
    if not _INVENTORY.is_file():
        pytest.skip("frozen research inventory is not present in this checkout")
    return ResearchInventory.model_validate(json.loads(_INVENTORY.read_text(encoding="utf-8")))


def _suite() -> SimulatorBaselineSuiteArtifact:
    if not (_RAW_ROOT.is_dir() and _BENCHMARK.is_file()):
        pytest.skip("frozen research inputs are not present in this checkout")
    return build_baseline_suite(
        inventory=_inventory(),
        raw_root=_RAW_ROOT,
        processed_root=_PROCESSED_ROOT,
        benchmark_path=_BENCHMARK,
    )


class TestSuiteDeterminism:
    def test_two_builds_are_byte_identical(self) -> None:
        first, second = _suite(), _suite()
        assert first.model_dump_json() == second.model_dump_json()
        assert first.suite_hash == second.suite_hash

    def test_committed_artifact_matches_a_fresh_build(self) -> None:
        if not _SUITE.is_file():
            pytest.skip("baseline suite artifact has not been written yet")
        artifact = _suite()
        assert _SUITE.read_text(encoding="utf-8") == (
            canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n"
        )

    def test_artifact_writes_and_reloads(self, tmp_path: Path) -> None:
        artifact = _suite()
        target = tmp_path / "simulator_baseline_suite_v1.json"
        write_baseline_suite_artifact(target, artifact)
        reloaded = SimulatorBaselineSuiteArtifact.model_validate(
            json.loads(target.read_text(encoding="utf-8"))
        )
        assert reloaded.suite_hash == artifact.suite_hash

    def test_suite_hash_covers_content(self) -> None:
        artifact = _suite()
        tampered = artifact.model_copy(update={"registry_hash": "f" * 64})
        with pytest.raises(ValueError, match="hash mismatch"):
            SimulatorBaselineSuiteArtifact.model_validate(
                tampered.model_dump(mode="json", by_alias=True)
            )


class TestAcceptedBenchmarkBinding:
    def test_binds_the_accepted_benchmark_identities(self) -> None:
        artifact = _suite()
        benchmark = load_accepted_benchmark(_BENCHMARK)
        assert artifact.benchmark_hash == benchmark.benchmark_hash
        assert artifact.metric_spec_hash == benchmark.metric_spec_hash
        assert artifact.metric_spec_hash == MetricSpecification().spec_hash()
        assert artifact.training_series_sha256 == benchmark.underlying["training"].series_sha256
        assert artifact.validation_series_sha256 == benchmark.underlying["validation"].series_sha256
        assert artifact.inventory_hash == _inventory().inventory_hash

    def test_accepted_gbm_and_heston_records_are_copied_verbatim(self) -> None:
        artifact = _suite()
        benchmark = load_accepted_benchmark(_BENCHMARK)
        for name in ("gbm", "heston"):
            assert artifact.metrics[name] == benchmark.metrics[name]
            assert artifact.calibrations[name] == benchmark.calibrations[name]
            for split in ("training", "validation"):
                assert artifact.discrepancies[split][name] == benchmark.discrepancies[split][name]

    def test_empirical_reference_metrics_are_copied_verbatim(self) -> None:
        artifact = _suite()
        benchmark = load_accepted_benchmark(_BENCHMARK)
        for key in ("training_empirical", "validation_empirical"):
            assert artifact.metrics[key] == benchmark.metrics[key]

    def test_accepted_benchmark_file_is_not_mutated(self) -> None:
        before = _BENCHMARK.read_bytes()
        _suite()
        assert _BENCHMARK.read_bytes() == before

    def test_mismatched_metric_spec_is_rejected(self) -> None:
        from dataclasses import replace

        with pytest.raises(ValueError, match="metric specification does not match"):
            build_baseline_suite(
                inventory=_inventory(),
                raw_root=_RAW_ROOT,
                processed_root=_PROCESSED_ROOT,
                benchmark_path=_BENCHMARK,
                spec=replace(MetricSpecification(), gbm_seed=4242),
            )


class TestSuiteContract:
    def test_shared_simulation_contract(self) -> None:
        artifact = _suite()
        benchmark = load_accepted_benchmark(_BENCHMARK)
        simulations = artifact.simulations
        assert simulations["n_paths"] == 1024
        assert simulations["horizon_sessions"] == 63
        assert simulations["initial_price"] == benchmark.simulations["initial_price"]
        assert simulations["initial_price_convention"] == "final training-session close"
        assert simulations["training_population_size"] == 925
        assert simulations["seeds"] == {
            "gbm": 1337,
            "heston": 1729,
            "iid_bootstrap": 2027,
            "block_bootstrap": 2029,
            "gjr_garch": 2039,
        }
        assert simulations["block_bootstrap"]["block_length"] == 22
        assert simulations["block_bootstrap"]["blocks_per_path"] == 3
        for name in EVALUATED_COMPARATORS:
            assert artifact.metrics[name]["n_observations"] == 1024 * 63

    def test_garch_is_fitted_on_training_only(self) -> None:
        artifact = _suite()
        garch = artifact.calibrations["gjr_garch"]
        assert garch["n_observations"] == 925
        assert garch["n_observations"] == artifact.metrics["training_empirical"]["n_observations"]
        assert 0.0 < garch["persistence"] < 1.0
        assert garch["parameters"]["omega"] > 0
        assert garch["innovation_distribution"] == "gaussian"
        assert garch["convergence"]
        assert garch["log_likelihood"] == -garch["objective"]

    def test_every_comparator_is_scored_on_both_splits(self) -> None:
        artifact = _suite()
        for split in ("training", "validation"):
            assert set(artifact.discrepancies[split]) == set(EVALUATED_COMPARATORS)
            for name in EVALUATED_COMPARATORS:
                families = artifact.discrepancies[split][name]
                for family in (
                    "mean",
                    "variance",
                    "excess_kurtosis",
                    "quantiles",
                    "return_acf",
                    "abs_return_acf",
                    "sq_return_acf",
                    "leverage_correlations",
                ):
                    assert family in families

    def test_rankings_cover_every_family_without_a_single_headline_winner(self) -> None:
        artifact = _suite()
        for split in ("training", "validation"):
            rankings = artifact.rankings[split]
            assert set(rankings) == {
                "mean",
                "variance",
                "skewness",
                "excess_kurtosis",
                "quantiles",
                "return_acf",
                "abs_return_acf",
                "sq_return_acf",
                "leverage_correlations",
            }
            for order in rankings.values():
                assert sorted(order) == sorted(EVALUATED_COMPARATORS)

    def test_missing_comparator_is_rejected(self) -> None:
        artifact = _suite()
        payload = artifact.model_dump(mode="json", by_alias=True)
        del payload["discrepancies"]["validation"]["gjr_garch"]
        with pytest.raises(ValueError, match="comparator set is incomplete"):
            SimulatorBaselineSuiteArtifact.model_validate(payload)

    def test_registry_is_frozen_in_the_artifact(self) -> None:
        artifact = _suite()
        registry = artifact.comparator_registry
        assert registry["registry_hash"] == artifact.registry_hash
        assert artifact.suite_spec_hash == BaselineSuiteSpec().spec_hash()
        statuses = {entry["name"]: entry["status"] for entry in registry["entries"]}
        assert statuses == {
            "iid_bootstrap": "implemented",
            "block_bootstrap": "implemented",
            "stationary_bootstrap": "not_selected",
            "gbm": "accepted_prior",
            "gjr_garch": "implemented",
            "egarch": "not_selected",
            "heston": "accepted_prior",
        }

    def test_limitations_are_explicit(self) -> None:
        limitations = " ".join(_suite().limitations)
        assert "training split only" in limitations
        assert "variance targeting" in limitations
        assert "EGARCH" in limitations
        assert "empirical support" in limitations


class TestFinalTestIsolation:
    def test_no_sealed_dates_reach_the_suite(self) -> None:
        payload = _suite().model_dump_json()
        assert "2023-07" not in payload
        assert "2023-08" not in payload
        assert "2024-" not in payload
