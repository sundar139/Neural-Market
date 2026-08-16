from __future__ import annotations

import numpy as np
import pytest

from neuralmarket.baselines import simulated_prices
from neuralmarket.baselines.bootstrap import (
    BLOCK_BOOTSTRAP_BLOCK_LENGTH,
    sample_block_bootstrap,
    sample_iid_bootstrap,
)

pytestmark = pytest.mark.unit


def _training() -> np.ndarray:
    rng = np.random.default_rng(11)
    return rng.normal(0.0005, 0.01, size=925)


def _validation_only() -> np.ndarray:
    # Deliberately disjoint from the training population: every value is
    # negative-and-huge, so any leakage is detectable by membership alone.
    return np.full(274, -7.5)


class TestIidBootstrap:
    def test_shape_and_determinism(self) -> None:
        population = _training()
        first = sample_iid_bootstrap(population, 1024, 63, seed=2027)
        second = sample_iid_bootstrap(population, 1024, 63, seed=2027)
        assert first.shape == (1024, 63)
        assert np.array_equal(first, second)

    def test_different_seed_changes_draw(self) -> None:
        population = _training()
        assert not np.array_equal(
            sample_iid_bootstrap(population, 32, 63, seed=2027),
            sample_iid_bootstrap(population, 32, 63, seed=2028),
        )

    def test_samples_only_from_population(self) -> None:
        population = _training()
        drawn = sample_iid_bootstrap(population, 256, 63, seed=2027)
        assert np.isin(drawn, population).all()

    def test_validation_returns_never_sampled(self) -> None:
        population = _training()
        drawn = sample_iid_bootstrap(population, 256, 63, seed=2027)
        assert not np.isin(drawn, _validation_only()).any()

    def test_reconstructed_prices_are_positive(self) -> None:
        drawn = sample_iid_bootstrap(_training(), 64, 63, seed=2027)
        prices = simulated_prices(drawn, initial_price=430.0)
        assert prices.shape == (64, 64)
        assert (prices > 0).all()
        assert np.allclose(prices[:, 0], 430.0)

    def test_one_step_distribution_converges(self) -> None:
        population = np.array([-0.02, -0.01, 0.0, 0.01, 0.03], dtype=np.float64)
        drawn = sample_iid_bootstrap(population, 20000, 20, seed=99).ravel()
        assert drawn.mean() == pytest.approx(population.mean(), abs=2e-4)
        assert drawn.std(ddof=1) == pytest.approx(population.std(ddof=0), rel=5e-3)
        counts = np.array([(drawn == value).mean() for value in population])
        assert np.abs(counts - 0.2).max() < 5e-3

    def test_rejects_invalid_inputs(self) -> None:
        with pytest.raises(ValueError, match="1-D"):
            sample_iid_bootstrap(np.zeros((3, 3)), 4, 4, seed=1)
        with pytest.raises(ValueError, match=">= 1"):
            sample_iid_bootstrap(_training(), 0, 63, seed=1)
        with pytest.raises(ValueError, match="finite"):
            sample_iid_bootstrap(np.array([0.1, np.nan, 0.2]), 4, 4, seed=1)


class TestBlockBootstrap:
    def test_frozen_convention(self) -> None:
        assert BLOCK_BOOTSTRAP_BLOCK_LENGTH == 22

    def test_shape_and_determinism(self) -> None:
        population = _training()
        first = sample_block_bootstrap(population, 1024, 63, block_length=22, seed=2029)
        second = sample_block_bootstrap(population, 1024, 63, block_length=22, seed=2029)
        assert first.shape == (1024, 63)
        assert np.array_equal(first, second)

    def test_exact_horizon_when_not_a_block_multiple(self) -> None:
        # 63 = 2 full blocks of 22 plus a deterministically truncated 19.
        drawn = sample_block_bootstrap(_training(), 8, 63, block_length=22, seed=2029)
        assert drawn.shape == (8, 63)

    def test_blocks_are_contiguous_and_wrap_circularly(self) -> None:
        population = np.arange(100, dtype=np.float64)
        drawn = sample_block_bootstrap(population, 200, 63, block_length=22, seed=5)
        for path in drawn:
            for start in (0, 22, 44):
                block = path[start : start + 22]
                if len(block) < 2:
                    continue
                steps = np.diff(block) % 100
                assert np.all(steps == 1.0)

    def test_wrap_occurs_for_some_path(self) -> None:
        population = np.arange(100, dtype=np.float64)
        drawn = sample_block_bootstrap(population, 500, 63, block_length=22, seed=5)
        assert np.any(np.diff(drawn[:, :22], axis=1) < 0)

    def test_samples_only_from_population(self) -> None:
        population = _training()
        drawn = sample_block_bootstrap(population, 128, 63, block_length=22, seed=2029)
        assert np.isin(drawn, population).all()
        assert not np.isin(drawn, _validation_only()).any()

    def test_preserves_dependence_that_iid_destroys(self) -> None:
        # Synthetic clustered series: alternating 50-observation vol regimes.
        rng = np.random.default_rng(7)
        regimes = np.repeat([0.002, 0.02], 50)
        population = rng.normal(0.0, np.tile(regimes, 10))
        block = sample_block_bootstrap(population, 512, 63, block_length=22, seed=2029)
        iid = sample_iid_bootstrap(population, 512, 63, seed=2027)
        assert _abs_acf1(block) > 5 * _abs_acf1(iid)
        assert _abs_acf1(block) > 0.1

    def test_reconstructed_prices_are_positive(self) -> None:
        drawn = sample_block_bootstrap(_training(), 64, 63, block_length=22, seed=2029)
        assert (simulated_prices(drawn, initial_price=430.0) > 0).all()

    def test_rejects_invalid_block_length(self) -> None:
        with pytest.raises(ValueError, match="block_length"):
            sample_block_bootstrap(_training(), 4, 63, block_length=0, seed=1)
        with pytest.raises(ValueError, match="block_length"):
            sample_block_bootstrap(np.zeros(10) + 0.01, 4, 63, block_length=22, seed=1)


def _abs_acf1(paths: np.ndarray) -> float:
    """Mean within-path lag-1 autocorrelation of absolute increments."""
    values = []
    for path in paths:
        absolute = np.abs(path)
        centered = absolute - absolute.mean()
        denominator = float(np.dot(centered, centered))
        if denominator > 0:
            values.append(float(np.dot(centered[:-1], centered[1:]) / denominator))
    return float(np.mean(values))
