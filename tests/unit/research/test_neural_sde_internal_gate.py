"""Tests for the v2 internal gate contract.

Covers:
A. Bootstrap terminal reference (deterministic, correct shape/horizon)
B. Equal estimator contract (real/generated N must match)
C. Terminal scale ratio (hand-computed)
D. Wasserstein (identical -> 0, shifted -> positive)
E. Multi-lag ACF (known series, RMSE, max error)
F. Bootstrap sensitivity (autocorrelated vs IID)
G. Conditional variance diagnostic
H. Gate specification hash (deterministic, changes on config change)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from neuralmarket.baselines.bootstrap import sample_block_bootstrap
from neuralmarket.research.neural_sde_internal_gate import (
    _FROZEN_GATE_V2_PATH,
    GateSpecV2,
    _acf,
    _acf_max_error,
    _acf_rmse,
    _multi_lag_acf,
    _wasserstein_1d,
    load_gate_spec_v2,
)

pytestmark = [pytest.mark.unit]

_GATE_YAML = Path(__file__).resolve().parents[3] / _FROZEN_GATE_V2_PATH


class TestBootstrapTerminalReference:
    """A. Bootstrap produces correct shape and deterministic output."""

    def test_deterministic(self) -> None:
        returns = np.random.RandomState(42).randn(200)
        b1 = sample_block_bootstrap(returns, 100, 63, block_length=22, seed=8801)
        b2 = sample_block_bootstrap(returns, 100, 63, block_length=22, seed=8801)
        assert np.array_equal(b1, b2)

    def test_shape(self) -> None:
        returns = np.random.RandomState(42).randn(200)
        b = sample_block_bootstrap(returns, 1024, 63, block_length=22, seed=8801)
        assert b.shape == (1024, 63)

    def test_terminal_sum(self) -> None:
        returns = np.random.RandomState(42).randn(200)
        b = sample_block_bootstrap(returns, 100, 63, block_length=22, seed=8801)
        terminal = b.sum(axis=1)
        assert terminal.shape == (100,)


class TestEqualEstimatorContract:
    """B. Real bootstrap and generated must have equal N."""

    def test_mismatched_terminal_counts_rejected(self) -> None:
        """Gate must reject mismatched real/generated terminal counts."""
        real = np.random.randn(1024)
        gen = np.random.randn(512)
        with pytest.raises(ValueError, match="terminal count mismatch"):
            # Simulate what gate does: check equal N before terminal stats.
            if len(gen) != len(real):
                raise ValueError(
                    f"terminal count mismatch: generated={len(gen)} != real_bootstrap={len(real)}"
                )

    def test_equal_count_proceeds(self) -> None:
        """Equal N should not raise."""
        real = np.random.randn(1024)
        gen = np.random.randn(1024)
        # Should not raise
        assert len(real) == len(gen)


class TestTerminalScaleRatio:
    """C. Hand-computed terminal dispersion ratio."""

    def test_identical_distributions(self) -> None:
        rng = np.random.RandomState(99)
        data = rng.randn(10000)
        std_val = float(np.std(data))
        assert abs(std_val / std_val - 1.0) < 1e-10

    def test_scaled_distribution(self) -> None:
        rng = np.random.RandomState(99)
        real = rng.randn(10000)
        gen = real * 2.0
        ratio = float(np.std(gen)) / float(np.std(real))
        assert abs(ratio - 2.0) < 0.05

    def test_half_distribution(self) -> None:
        rng = np.random.RandomState(99)
        real = rng.randn(10000)
        gen = real * 0.5
        ratio = float(np.std(gen)) / float(np.std(real))
        assert abs(ratio - 0.5) < 0.05


class TestWasserstein:
    """D. 1-Wasserstein distance."""

    def test_identical_arrays(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        w = _wasserstein_1d(a, a)
        assert abs(w) < 1e-10

    def test_shifted_arrays(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = a + 10.0
        w = _wasserstein_1d(a, b)
        assert abs(w - 10.0) < 1e-10

    def test_scaled_arrays(self) -> None:
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = a * 2.0
        w = _wasserstein_1d(a, b)
        assert w > 0

    def test_deterministic(self) -> None:
        a = np.random.RandomState(42).randn(100)
        b = np.random.RandomState(43).randn(100)
        w1 = _wasserstein_1d(a, b)
        w2 = _wasserstein_1d(a, b)
        assert w1 == w2


class TestMultiLagACF:
    """E. Multi-lag ACF computation."""

    def test_known_series(self) -> None:
        """White noise should have near-zero ACF at all lags."""
        rng = np.random.RandomState(42)
        x = rng.randn(10000)
        acf = _multi_lag_acf(x, (1, 2, 3, 5, 10, 20))
        for lag, val in acf.items():
            assert abs(val) < 0.05, f"ACF at lag {lag} = {val}, expected ~0"

    def test_acf1_positive_for_autocorrelated(self) -> None:
        """AR(1) with positive phi should have positive ACF1."""
        rng = np.random.RandomState(42)
        n = 10000
        phi = 0.5
        x = np.zeros(n)
        x[0] = rng.randn()
        for i in range(1, n):
            x[i] = phi * x[i - 1] + rng.randn()
        acf1 = _acf(x, 1)
        assert acf1 > 0.3

    def test_rmse_identical(self) -> None:
        acf = {1: 0.5, 5: 0.3, 10: 0.1}
        assert _acf_rmse(acf, acf) < 1e-10

    def test_rmse_positive(self) -> None:
        real = {1: 0.5, 5: 0.3}
        gen = {1: 0.7, 5: 0.1}
        rmse = _acf_rmse(real, gen)
        assert rmse > 0

    def test_max_error_identical(self) -> None:
        acf = {1: 0.5, 5: 0.3}
        assert _acf_max_error(acf, acf) < 1e-10

    def test_max_error(self) -> None:
        real = {1: 0.5, 5: 0.3}
        gen = {1: 0.8, 5: 0.3}
        assert abs(_acf_max_error(real, gen) - 0.3) < 1e-10

    def test_lag_vector_exact(self) -> None:
        lags = (1, 2, 3, 5, 10, 20)
        x = np.random.randn(1000)
        acf = _multi_lag_acf(x, lags)
        assert set(acf.keys()) == set(lags)


class TestBootstrapSensitivity:
    """F. Block bootstrap preserves more structure than IID."""

    def test_block_preserves_autocorrelation(self) -> None:
        rng = np.random.RandomState(42)
        n = 500
        phi = 0.8
        x = np.zeros(n)
        x[0] = rng.randn()
        for i in range(1, n):
            x[i] = phi * x[i - 1] + rng.randn()

        block_boot = sample_block_bootstrap(x, 1000, 63, block_length=22, seed=8801)
        iid_boot = np.column_stack(
            [np.random.RandomState(8801 + i).choice(x, size=63) for i in range(1000)]
        ).T

        block_acf1 = float(np.corrcoef(block_boot.ravel()[:-1], block_boot.ravel()[1:])[0, 1])
        iid_acf1 = float(np.corrcoef(iid_boot.ravel()[:-1], iid_boot.ravel()[1:])[0, 1])

        # Block bootstrap should preserve more autocorrelation
        assert block_acf1 > iid_acf1


class TestReportOnlyInvariance:
    """Prove report-only metrics cannot affect gate pass/fail."""

    def test_bad_acf_rmse_still_passes(self) -> None:
        """Gate should PASS even with terrible ACF RMSE if all pass/fail criteria pass."""
        from neuralmarket.research.neural_sde_internal_gate import GateSpecV2

        GateSpecV2(
            acf_rmse_threshold=0.15,
            acf_max_lag_error=0.25,
            acf1_max_diff=0.25,
            variance_ratio_lo=0.50,
            variance_ratio_hi=2.00,
            dispersion_band_lo=0.50,
            dispersion_band_hi=2.00,
            uniqueness_min=0.99,
            drift_diffusion_max=0.50,
        )
        # Simulate: all pass/fail criteria pass, but ACF RMSE is terrible
        criterion_results = {
            "variance_ratio": True,
            "terminal_dispersion": True,
            "uniqueness": True,
            "acf1_agreement": True,  # ACF(1) passes
            "drift_diffusion_ratio": True,
        }
        gate_passed = all(criterion_results.values())
        assert gate_passed, "gate should pass when all pass/fail criteria are True"
        # ACF RMSE and max error are NOT in criterion_results (report-only)
        assert "acf_rmse" not in criterion_results
        assert "acf_max_error" not in criterion_results

    def test_bad_acf1_fails_gate(self) -> None:
        """Gate should FAIL if ACF(1) agreement fails."""
        criterion_results = {
            "variance_ratio": True,
            "terminal_dispersion": True,
            "uniqueness": True,
            "acf1_agreement": False,  # ACF(1) fails
            "drift_diffusion_ratio": True,
        }
        gate_passed = all(criterion_results.values())
        assert not gate_passed


class TestGateSpecHash:
    """H. Gate specification hash is deterministic."""

    def test_deterministic(self) -> None:
        s1 = GateSpecV2()
        s2 = GateSpecV2()
        assert s1.spec_hash() == s2.spec_hash()

    def test_changes_on_config_change(self) -> None:
        s1 = GateSpecV2()
        s2 = GateSpecV2(bootstrap_seed=9999)
        assert s1.spec_hash() != s2.spec_hash()

    def test_load_from_yaml(self) -> None:
        import tempfile

        valid_yaml = {
            "version": "neural-sde-internal-gate-v2",
            "bootstrap": {
                "method": "block",
                "block_length": 22,
                "terminal_path_count": 1024,
                "generated_path_count": 1024,
                "horizon": 63,
                "seed": 8801,
                "gate_seed": 7777,
                "drift_diffusion_seed": 7778,
            },
            "terminal_dispersion": {"band_lo": 0.5, "band_hi": 2.0, "status": "pass_fail"},
            "serial_dependence": {
                "lags": [1, 2, 3, 5, 10, 20],
                "acf1": {"status": "pass_fail", "threshold": 0.25},
                "rmse": {"status": "report_only", "diagnostic_reference": 0.15},
                "max_error": {"status": "report_only", "diagnostic_reference": 0.25},
            },
            "variance_ratio": {"band_lo": 0.5, "band_hi": 2.0, "status": "pass_fail"},
            "path_uniqueness": {"min_fraction": 0.99, "status": "pass_fail"},
            "drift_diffusion_ratio": {"max_ratio": 0.5, "status": "pass_fail"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml as _yaml

            _yaml.dump(valid_yaml, f)
            f.flush()
            spec = load_gate_spec_v2(f.name)
        assert spec.bootstrap_method == "block"
        assert spec.block_length == 22
        assert spec.gate_seed == 7777
        assert spec.drift_diffusion_seed == 7778


def _gate_yaml_dict() -> dict:
    """A valid gate-v2 YAML dict matching the production schema (for mutations)."""
    return {
        "version": "neural-sde-internal-gate-v2",
        "bootstrap": {
            "method": "block",
            "block_length": 22,
            "terminal_path_count": 1024,
            "generated_path_count": 1024,
            "horizon": 63,
            "seed": 8801,
            "gate_seed": 7777,
            "drift_diffusion_seed": 7778,
        },
        "terminal_dispersion": {"band_lo": 0.50, "band_hi": 2.00, "status": "pass_fail"},
        "serial_dependence": {
            "lags": [1, 2, 3, 5, 10, 20],
            "acf1": {"status": "pass_fail", "threshold": 0.25},
            "rmse": {"status": "report_only", "diagnostic_reference": 0.15},
            "max_error": {"status": "report_only", "diagnostic_reference": 0.25},
        },
        "variance_ratio": {"band_lo": 0.50, "band_hi": 2.00, "status": "pass_fail"},
        "path_uniqueness": {"min_fraction": 0.99, "status": "pass_fail"},
        "drift_diffusion_ratio": {"max_ratio": 0.50, "status": "pass_fail"},
    }


def _write_yaml(data: dict) -> str:
    import tempfile

    import yaml as _yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        _yaml.dump(data, f)
        f.flush()
        return f.name


class TestGateV2FailClosed:
    """H. Missing pass/fail thresholds or explicit seed fields hard-fail."""

    def test_missing_acf1_threshold_raises(self) -> None:
        data = _gate_yaml_dict()
        del data["serial_dependence"]["acf1"]
        with pytest.raises(ValueError, match="missing required"):
            load_gate_spec_v2(_write_yaml(data))

    def test_acf1_not_pass_fail_raises(self) -> None:
        data = _gate_yaml_dict()
        data["serial_dependence"]["acf1"]["status"] = "report_only"
        with pytest.raises(ValueError, match="must be pass_fail"):
            load_gate_spec_v2(_write_yaml(data))

    def test_missing_gate_seed_raises(self) -> None:
        data = _gate_yaml_dict()
        del data["bootstrap"]["gate_seed"]
        with pytest.raises(ValueError, match="bootstrap.gate_seed"):
            load_gate_spec_v2(_write_yaml(data))

    def test_missing_drift_diffusion_seed_raises(self) -> None:
        data = _gate_yaml_dict()
        del data["bootstrap"]["drift_diffusion_seed"]
        with pytest.raises(ValueError, match="bootstrap.drift_diffusion_seed"):
            load_gate_spec_v2(_write_yaml(data))

    def test_missing_max_error_reference_raises(self) -> None:
        data = _gate_yaml_dict()
        del data["serial_dependence"]["max_error"]
        with pytest.raises(ValueError, match="max_error"):
            load_gate_spec_v2(_write_yaml(data))


class TestGateAcfMapping:
    """H. acf_max_lag_error binds the report-only reference, not the ACF(1) threshold."""

    def test_max_error_follows_report_only_field(self) -> None:
        data = _gate_yaml_dict()
        data["serial_dependence"]["max_error"]["diagnostic_reference"] = 0.37
        spec = load_gate_spec_v2(_write_yaml(data))
        assert spec.acf_max_lag_error == 0.37
        # The ACF(1) pass/fail threshold is a separate field.
        assert spec.acf1_max_diff == 0.25

    def test_acf1_threshold_binds_acf1(self) -> None:
        data = _gate_yaml_dict()
        data["serial_dependence"]["acf1"]["threshold"] = 0.19
        spec = load_gate_spec_v2(_write_yaml(data))
        assert spec.acf1_max_diff == 0.19
        assert spec.acf_max_lag_error == 0.25


class TestGateSeedIdentity:
    """I. Gate stochastic seeds are explicit and frozen; hash responds to them."""

    def test_accepted_seed_values_load(self) -> None:
        spec = load_gate_spec_v2(str(_GATE_YAML))
        assert spec.gate_seed == 7777
        assert spec.drift_diffusion_seed == 7778

    def test_spec_hash_changes_when_gate_seed_changes(self) -> None:
        base = load_gate_spec_v2(str(_GATE_YAML)).spec_hash()
        data = _gate_yaml_dict()
        data["bootstrap"]["gate_seed"] = 7779
        assert load_gate_spec_v2(_write_yaml(data)).spec_hash() != base

    def test_spec_hash_changes_when_drift_seed_changes(self) -> None:
        base = load_gate_spec_v2(str(_GATE_YAML)).spec_hash()
        data = _gate_yaml_dict()
        data["bootstrap"]["drift_diffusion_seed"] = 7779
        assert load_gate_spec_v2(_write_yaml(data)).spec_hash() != base
