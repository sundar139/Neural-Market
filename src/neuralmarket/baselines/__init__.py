"""Deterministic baselines for generator evaluation."""

from __future__ import annotations

import numpy as np


def simulated_prices(increments: np.ndarray, *, initial_price: float) -> np.ndarray:
    """Convert simulated log-return increments to strictly positive price paths.

    Shared representation for every simulator baseline: increments have shape
    ``(n_paths, horizon)`` and prices have shape ``(n_paths, horizon + 1)`` with
    the initial price in column 0.

    Args:
        increments: Log-return increments of shape ``(n_paths, horizon)``.
        initial_price: Strictly positive starting price for every path.

    Returns:
        Price paths of shape ``(n_paths, horizon + 1)``.

    Raises:
        ValueError: If the inputs are not a finite 2-D array and a positive price.
    """
    increments = np.asarray(increments, dtype=np.float64)
    if increments.ndim != 2:
        raise ValueError("increments must be 2-D (n_paths, horizon)")
    if np.any(~np.isfinite(increments)):
        raise ValueError("increments must be finite")
    if not np.isfinite(initial_price) or initial_price <= 0:
        raise ValueError("initial_price must be positive and finite")
    log_prices = np.concatenate(
        [np.zeros((increments.shape[0], 1)), np.cumsum(increments, axis=1)], axis=1
    )
    prices: np.ndarray = initial_price * np.exp(log_prices)
    return prices


__all__ = ["simulated_prices"]
