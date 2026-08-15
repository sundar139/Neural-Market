"""Production-shaped empirical benchmark: determinism, isolation, provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuralmarket.data.research.benchmark import (
    EmpiricalBenchmarkArtifact,
    build_empirical_benchmark,
    write_benchmark_artifact,
)
from neuralmarket.data.research.inventory import build_research_inventory
from neuralmarket.eval.scorecard import MetricSpecification

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_SCOPE_SRC = _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_JOURNAL = _ROOT / "data/state/development_acquisition_journal.sqlite"
_CONFIG = _ROOT / "configs/data/spy_daily_databento.yaml"
_HEAD = "70544a482dcf5762a968e3f0c7df35bb7c9a5db8"


def _inventory():
    if not _JOURNAL.is_file():
        pytest.skip("development acquisition journal is not present in this checkout")
    return build_research_inventory(
        plan_path=_PLAN,
        manifest_path=_MANIFEST,
        scope_source_path=_SCOPE_SRC,
        journal_path=_JOURNAL,
        config_path=_CONFIG,
        repository_root=_ROOT,
        source_head=_HEAD,
    )


def _benchmark():
    return build_empirical_benchmark(
        inventory=_inventory(),
        raw_root=_ROOT / "data/raw/databento",
        processed_root=_ROOT / "data/processed",
        spec=MetricSpecification(),
    )


class TestBenchmarkDeterminism:
    def test_two_builds_are_byte_identical(self) -> None:
        first = _benchmark()
        second = _benchmark()
        assert first.model_dump_json() == second.model_dump_json()
        assert first.benchmark_hash == second.benchmark_hash

    def test_artifact_writes_and_reloads(self, tmp_path: Path) -> None:
        from neuralmarket.data.manifests import canonical_dumps

        artifact = _benchmark()
        target = tmp_path / "empirical_benchmark_v1.json"
        write_benchmark_artifact(target, artifact)
        payload = json.loads(target.read_text(encoding="utf-8"))
        reloaded = EmpiricalBenchmarkArtifact.model_validate(payload)
        assert reloaded.benchmark_hash == artifact.benchmark_hash
        assert target.read_text(encoding="utf-8") == (
            canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n"
        )

    def test_benchmark_hash_covers_content(self) -> None:
        artifact = _benchmark()
        tampered = artifact.model_copy(update={"plan_hash": "f" * 64})
        with pytest.raises(ValueError, match="hash mismatch"):
            EmpiricalBenchmarkArtifact.model_validate(
                tampered.model_dump(mode="json", by_alias=True)
            )


class TestBenchmarkContract:
    def test_underlying_coverage(self) -> None:
        artifact = _benchmark()
        training = artifact.underlying["training"]
        validation = artifact.underlying["validation"]
        assert training.first_session == "2018-05-01"
        assert training.last_session == "2021-12-31"
        assert validation.first_session == "2022-05-26"
        assert validation.last_session == "2023-06-30"
        assert training.n_returns == training.n_sessions - 1
        assert validation.n_returns == validation.n_sessions - 1
        assert training.n_returns == 925
        assert validation.n_returns == 274

    def test_calibration_uses_training_only(self) -> None:
        artifact = _benchmark()
        gbm = artifact.calibrations["gbm"]
        heston = artifact.calibrations["heston"]
        assert gbm["n_observations"] == artifact.underlying["training"].n_returns
        assert artifact.metrics["training_empirical"]["n_observations"] == 925
        # Heston objective moments match the TRAINING empirical moments.
        empirical = artifact.metrics["training_empirical"]
        heston_moments = heston["empirical_moments"]
        assert heston_moments["std"] == pytest.approx(float(empirical["variance"]) ** 0.5, rel=1e-9)
        assert heston_moments["skewness"] == pytest.approx(float(empirical["skewness"]), rel=1e-9)
        assert heston_moments["excess_kurtosis"] == pytest.approx(
            float(empirical["excess_kurtosis"]), rel=1e-9
        )

    def test_validation_never_influences_calibration(self) -> None:
        artifact = _benchmark()
        # The calibration blocks record only training-derived sample sizes:
        assert artifact.calibrations["gbm"]["n_observations"] == 925
        assert artifact.calibrations["heston"]["calibration_paths"] == 2048

    def test_simulation_dimensions_and_seeds(self) -> None:
        artifact = _benchmark()
        simulations = artifact.simulations
        assert simulations["n_paths"] == 1024
        assert simulations["horizon_sessions"] == 63
        assert simulations["gbm_seed"] == 1337
        assert simulations["heston_seed"] == 1729
        assert simulations["initial_price"] > 0
        # GBM/Heston metrics sample size = paths * horizon.
        assert artifact.metrics["gbm"]["n_observations"] == 1024 * 63
        assert artifact.metrics["heston"]["n_observations"] == 1024 * 63

    def test_fat_tails_and_leverage_measured(self) -> None:
        artifact = _benchmark()
        empirical = artifact.metrics["training_empirical"]
        assert empirical["excess_kurtosis"] > 0  # SPY daily returns are fat-tailed
        assert "0.01" in empirical["quantiles"]
        assert empirical["leverage_correlations"]
        assert empirical["return_acf"] and empirical["abs_return_acf"]

    def test_discrepancies_reported_per_family(self) -> None:
        artifact = _benchmark()
        for split in ("training", "validation"):
            for baseline in ("gbm", "heston"):
                families = artifact.discrepancies[split][baseline]
                assert "excess_kurtosis" in families
                assert "quantiles" in families
                assert "sq_return_acf" in families
                for family in ("quantiles", "sq_return_acf"):
                    assert families[family]["mean_abs_relative_error"] is not None

    def test_no_final_test_access(self) -> None:
        artifact = _benchmark()
        payload = artifact.model_dump_json()
        for split_block in artifact.underlying.values():
            assert all(
                d <= "2023-06-30" for d in (split_block.first_session, split_block.last_session)
            )
        assert "2023-07" not in payload

    def test_missing_cbbo_sessions_not_substituted(self) -> None:
        artifact = _benchmark()
        limitations = " ".join(artifact.limitations)
        assert "2019-01-03" in limitations
        assert "2019-06-25" in limitations
        assert "not substituted" in limitations or "not consumed" in limitations

    def test_heston_underidentification_documented(self) -> None:
        artifact = _benchmark()
        assert artifact.calibrations["heston"]["parameters"]["kappa"] == 2.0
        assert (
            artifact.calibrations["heston"]["parameters"]["v0"]
            == artifact.calibrations["heston"]["parameters"]["theta"]
        )
        assert "uniquely identified" in " ".join(artifact.limitations)


class TestMissingDataBehavior:
    def test_uncertain_underlying_request_cannot_build_series(self) -> None:
        # A hypothetical uncertain underlying-daily requirement fails closed
        # instead of fabricating prices from another source.
        inventory = _inventory()
        entries = list(inventory.requirements)
        mutated = []
        for entry in entries:
            if entry.purpose == "underlying_daily_reference":
                entry = entry.model_copy(update={"disposition": "uncertain_billing"})
            mutated.append(entry)
        tampered = inventory.model_copy(update={"requirements": tuple(mutated)})
        from neuralmarket.data.errors import CoverageError
        from neuralmarket.data.research.underlying import build_underlying_series

        with pytest.raises(CoverageError, match="exactly one paid"):
            build_underlying_series(
                inventory=tampered,
                split="training",
                raw_root=_ROOT / "data/raw/databento",
                processed_root=_ROOT / "data/processed",
            )


class TestZeroProviderProof:
    def test_benchmark_modules_never_touch_provider(self) -> None:
        import inspect

        import neuralmarket.baselines.gbm as gbm_module
        import neuralmarket.baselines.heston as heston_module
        import neuralmarket.data.research.benchmark as benchmark_module
        import neuralmarket.data.research.underlying as underlying_module

        for module in (gbm_module, heston_module, benchmark_module, underlying_module):
            source = inspect.getsource(module)
            assert "dotenv" not in source
            assert "DATABENTO_API_KEY" not in source
            assert "databento.Historical" not in source
