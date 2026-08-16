"""Deterministic empirical resampling baselines: IID and circular block bootstrap.

Both simulators resample the frozen TRAINING log-return population only; the
validation split is never a sampling population. The block convention is
frozen before any evaluation: a circular (wrap-around) moving block bootstrap
with a 22-trading-day block length, which corresponds to roughly one trading
month and preserves local volatility clustering. Blocks are concatenated and
the tail is truncated deterministically to the requested horizon.
"""

from __future__ import annotations

import numpy as np

BLOCK_BOOTSTRAP_METHOD = "circular_moving_block"
BLOCK_BOOTSTRAP_BLOCK_LENGTH = 22
BLOCK_BOOTSTRAP_BOUNDARY_POLICY = "circular_wrap_with_deterministic_tail_truncation"


def _validate_population(returns: np.ndarray, n_paths: int, horizon: int) -> np.ndarray:
    population = np.asarray(returns, dtype=np.float64)
    if population.ndim != 1 or population.size < 2:
        raise ValueError("returns must be a 1-D array with >= 2 observations")
    if np.any(~np.isfinite(population)):
        raise ValueError("returns must be finite")
    if n_paths < 1 or horizon < 1:
        raise ValueError("n_paths and horizon must be >= 1")
    return population


def sample_iid_bootstrap(
    returns: np.ndarray,
    n_paths: int,
    horizon: int,
    *,
    seed: int,
) -> np.ndarray:
    """Sample IID-with-replacement log-return paths from an empirical population.

    Args:
        returns: 1-D training log-return population.
        n_paths: Number of independent paths.
        horizon: Number of steps per path.
        seed: Dedicated deterministic seed.

    Returns:
        Log-return increments of shape ``(n_paths, horizon)``.

    Raises:
        ValueError: If the population or dimensions are invalid.
    """
    population = _validate_population(returns, n_paths, horizon)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, population.size, size=(n_paths, horizon))
    drawn: np.ndarray = population[indices]
    return drawn


def sample_block_bootstrap(
    returns: np.ndarray,
    n_paths: int,
    horizon: int,
    *,
    block_length: int = BLOCK_BOOTSTRAP_BLOCK_LENGTH,
    seed: int,
) -> np.ndarray:
    """Sample circular moving-block bootstrap paths from an empirical population.

    Each path concatenates ``ceil(horizon / block_length)`` contiguous blocks
    drawn with replacement from uniformly random start indices; blocks wrap
    around the end of the population, and the concatenation is truncated to
    exactly ``horizon`` steps.

    Args:
        returns: 1-D training log-return population.
        n_paths: Number of independent paths.
        horizon: Number of steps per path.
        block_length: Contiguous block length in observations.
        seed: Dedicated deterministic seed.

    Returns:
        Log-return increments of shape ``(n_paths, horizon)``.

    Raises:
        ValueError: If the population, dimensions, or block length are invalid.
    """
    population = _validate_population(returns, n_paths, horizon)
    if block_length < 1:
        raise ValueError("block_length must be >= 1")
    if block_length > population.size:
        raise ValueError("block_length must not exceed the population size")
    n_blocks = -(-horizon // block_length)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, population.size, size=(n_paths, n_blocks))
    offsets = np.arange(block_length)
    indices = (starts[:, :, None] + offsets[None, None, :]) % population.size
    drawn: np.ndarray = population[indices.reshape(n_paths, n_blocks * block_length)][:, :horizon]
    return drawn
