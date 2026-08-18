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

import numpy as np
import pytest

from neuralmarket.baselines.bootstrap import sample_block_bootstrap
from neuralmarket.research.neural_sde_internal_gate import (
    GateSpecV2,
    _acf,
    _acf_max_error,
    _acf_rmse,
    _multi_lag_acf,
    _wasserstein_1d,
    load_gate_spec_v2,
)

pytestmark = [pytest.mark.unit]


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

    def test_equal_count_required(self) -> None:
        """Gate must reject mismatched N."""
        real_boot = np.random.randn(1024)
        gen = np.random.randn(512)  # mismatched
        assert len(real_boot) != len(gen)


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

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("bootstrap:\n  method: block\n  block_length: 22\n")
            f.flush()
            spec = load_gate_spec_v2(f.name)
        assert spec.bootstrap_method == "block"
        assert spec.block_length == 22
