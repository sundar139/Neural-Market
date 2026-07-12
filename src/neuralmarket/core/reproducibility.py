"""Deterministic seeding across Python, NumPy, and optional PyTorch."""

from __future__ import annotations

import os
import random

import numpy as np

from neuralmarket.core.logging import get_logger

_logger = get_logger(__name__)

DEFAULT_SEED = 1337


def seed_everything(seed: int = DEFAULT_SEED, *, deterministic: bool = True) -> int:
    """Seed all available random number generators for reproducible runs.

    Seeds Python's :mod:`random`, NumPy, and PyTorch when it is installed. This
    function must not fail merely because PyTorch is absent. Bitwise
    reproducibility on GPUs cannot be guaranteed and a warning is emitted when
    deterministic mode is requested with CUDA present.

    Args:
        seed: Non-negative seed value.
        deterministic: Whether to request deterministic algorithm settings where
            supported.

    Returns:
        The seed that was applied.

    Raises:
        ValueError: If ``seed`` is negative.
    """
    if seed < 0:
        raise ValueError(f"Seed must be non-negative, got {seed}.")

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    _seed_torch(seed, deterministic=deterministic)
    return seed


def _seed_torch(seed: int, *, deterministic: bool) -> None:
    """Seed PyTorch if importable, warning where GPU determinism is not guaranteed."""
    try:
        import torch
    except ImportError:
        _logger.debug("PyTorch not installed; skipping torch seeding.")
        return

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            _logger.warning(
                "CUDA is available; bitwise GPU reproducibility cannot be guaranteed "
                "even with deterministic settings enabled."
            )

    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)
