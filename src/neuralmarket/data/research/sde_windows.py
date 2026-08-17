"""Deterministic train-only window and past-only context construction.

Builds sliding windows over a real or synthetic daily log-return series for
conditional neural-SDE training.  Every window is purely chronological:

* the *context* (the ``context_lookback`` returns immediately preceding the
  window start) lies strictly before the target path;
* the *target* (the next ``horizon`` returns) lies fully inside the supplied
  series, which is the training period only;
* context features are lagged statistics computed from the context returns
  only -- no target or future return may enter its own context.

Normalization parameters are intended to be fitted from training data only by
the caller; this module never sees validation data.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from neuralmarket.data.manifests import canonical_dumps

_SEALED_TEST_BOUNDARY = "2023-07-01"

CONTEXT_FEATURE_NAMES: tuple[str, ...] = (
    "prev_daily_return",
    "prev_5d_cumulative_return",
    "prev_22d_cumulative_return",
    "prev_22d_realized_volatility",
)


@dataclass(frozen=True)
class WindowSpec:
    """Window geometry shared by every constructed window."""

    context_lookback: int = 22
    horizon: int = 63
    dt: float = 1.0 / 252.0

    def spec_hash(self) -> str:
        """Deterministic identity of the window geometry (no wall clock)."""
        return hashlib.sha256(
            canonical_dumps(
                {
                    "context_lookback": self.context_lookback,
                    "horizon": self.horizon,
                    "dt": self.dt,
                }
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class SdeWindow:
    """One deterministic context-target window.

    Attributes:
        window_id: Deterministic chronological identifier.
        start_index: Index of the first TARGET return in the source series.
        context_returns: Float64 array of the strictly preceding returns.
        target_returns: Float64 array of the target returns (length ``horizon``).
        context_start_date: Session date of the first context return.
        context_end_date: Session date of the last context return.
        target_start_date: Session date of the first target return.
        target_end_date: Session date of the last target return.
    """

    window_id: str
    start_index: int
    context_returns: np.ndarray
    target_returns: np.ndarray
    context_start_date: str
    context_end_date: str
    target_start_date: str
    target_end_date: str


@dataclass(frozen=True)
class ContextFeatures:
    """Lag statistics computed strictly from a context window."""

    prev_daily_return: float
    prev_5d_cumulative_return: float
    prev_22d_cumulative_return: float
    prev_22d_realized_volatility: float

    def array(self) -> np.ndarray:
        """Feature vector ordered exactly as :data:`CONTEXT_FEATURE_NAMES`."""
        return np.asarray(
            [
                self.prev_daily_return,
                self.prev_5d_cumulative_return,
                self.prev_22d_cumulative_return,
                self.prev_22d_realized_volatility,
            ],
            dtype=np.float64,
        )


def _require_clean_returns(returns: np.ndarray) -> None:
    if returns.ndim != 1:
        raise ValueError("returns must be 1-D")
    if returns.size == 0:
        raise ValueError("returns must be non-empty")
    if np.any(~np.isfinite(returns)):
        raise ValueError("returns must not contain NaN or infinity")


def build_windows(
    returns: np.ndarray,
    session_dates: Sequence[str],
    spec: WindowSpec | None = None,
) -> tuple[SdeWindow, ...]:
    """Build all eligible sliding windows inside a training series.

    An eligible window starts at return index ``s`` with ``s >= lookback``
    (enough strictly-prior context) and ``s + horizon <= len(returns)``
    (target fully inside the supplied period).

    Args:
        returns: 1-D float64 daily log returns, chronologically ordered.
        session_dates: One session date per return (the date the return is
            realized on), same length as ``returns``.
        spec: Window geometry.

    Returns:
        Chronologically ordered windows, one per eligible start index.

    Raises:
        ValueError: If inputs are invalid, unordered, or non-finite.
    """
    spec = WindowSpec() if spec is None else spec
    returns = np.asarray(returns, dtype=np.float64)
    _require_clean_returns(returns)
    if len(session_dates) != len(returns):
        raise ValueError("session dates must match returns in length")
    if any(d > _SEALED_TEST_BOUNDARY for d in session_dates):
        raise ValueError(
            f"sealed final-test dates entered window construction ({_SEALED_TEST_BOUNDARY})"
        )

    windows: list[SdeWindow] = []
    for s in range(spec.context_lookback, len(returns) - spec.horizon + 1):
        context = returns[s - spec.context_lookback : s]
        target = returns[s : s + spec.horizon]
        windows.append(
            SdeWindow(
                window_id=f"w{s:04d}",
                start_index=s,
                context_returns=np.array(context, dtype=np.float64, copy=True),
                target_returns=np.array(target, dtype=np.float64, copy=True),
                context_start_date=str(session_dates[s - spec.context_lookback]),
                context_end_date=str(session_dates[s - 1]),
                target_start_date=str(session_dates[s]),
                target_end_date=str(session_dates[s + spec.horizon - 1]),
            )
        )
    if not windows:
        raise ValueError("no eligible windows fit inside the supplied series")
    return tuple(windows)


def compute_context_features(window: SdeWindow, spec: WindowSpec | None = None) -> ContextFeatures:
    """Compute strictly past-only conditioning features for one window.

    The features use only ``context_returns``: the last daily return, the
    trailing 5- and 22-day cumulative returns, and the 22-day realized
    volatility (square root of the sum of squared returns).

    Args:
        window: A constructed window.
        spec: Window geometry.

    Returns:
        The four lag features.

    Raises:
        ValueError: If the context length does not match the spec.
    """
    spec = WindowSpec() if spec is None else spec
    ctx = np.asarray(window.context_returns, dtype=np.float64)
    _require_clean_returns(ctx)
    if len(ctx) != spec.context_lookback:
        raise ValueError(
            f"context length {len(ctx)} does not match lookback {spec.context_lookback}"
        )
    return ContextFeatures(
        prev_daily_return=float(ctx[-1]),
        prev_5d_cumulative_return=float(np.sum(ctx[-5:])),
        prev_22d_cumulative_return=float(np.sum(ctx)),
        prev_22d_realized_volatility=float(math.sqrt(float(np.sum(ctx**2)))),
    )


@dataclass(frozen=True)
class FeatureNormalizer:
    """Per-feature z-score parameters fitted from a training-only matrix."""

    means: np.ndarray
    stds: np.ndarray

    def normalize(self, features: np.ndarray) -> np.ndarray:
        """Standardize features with fitted parameters; rejects non-finite."""
        features = np.asarray(features, dtype=np.float64)
        if features.shape[-1] != self.means.shape[0]:
            raise ValueError(
                f"feature width {features.shape[-1]} does not match normalizer width "
                f"{self.means.shape[0]}"
            )
        if np.any(~np.isfinite(features)):
            raise ValueError("normalizer input must be finite")
        return np.asarray((features - self.means) / self.stds, dtype=np.float64)

    def normalizer_hash(self) -> str:
        """Deterministic hash of the fitted parameters."""
        return hashlib.sha256(
            canonical_dumps(
                {
                    "means": [float(m) for m in self.means],
                    "stds": [float(s) for s in self.stds],
                }
            ).encode("utf-8")
        ).hexdigest()


def fit_feature_normalizer(feature_matrix: np.ndarray) -> FeatureNormalizer:
    """Fit per-feature mean/std from a training-derived feature matrix.

    Args:
        feature_matrix: Shape ``(n_windows, n_features)`` float64 matrix of
            context features over the training windows.

    Returns:
        Frozen normalizer.  A zero standard deviation fails closed: it would
        divide by zero in :meth:`FeatureNormalizer.normalize`.

    Raises:
        ValueError: If the matrix is empty or non-finite.
    """
    matrix = np.asarray(feature_matrix, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("feature matrix must be a non-empty 2-D array")
    if np.any(~np.isfinite(matrix)):
        raise ValueError("feature matrix must be finite")
    means = np.mean(matrix, axis=0)
    stds = np.std(matrix, axis=0)
    if np.any(stds <= 0.0):
        raise ValueError("feature standard deviation must be positive")
    return FeatureNormalizer(means=means, stds=stds)


def fit_cumret_scale(returns: np.ndarray, horizon: int) -> float:
    """Training-derived scale for the signature cumulative-return channel.

    The scale is the training daily-return standard deviation times the square
    root of the horizon, so a horizon-length cumulative return has roughly
    unit scale under a homoskedastic approximation.  Fit from training returns
    only; never from validation.

    Args:
        returns: 1-D float64 training log returns.
        horizon: Target horizon in sessions.

    Returns:
        A positive scalar.

    Raises:
        ValueError: If the scale is non-positive or the input is non-finite.
    """
    returns = np.asarray(returns, dtype=np.float64)
    _require_clean_returns(returns)
    scale = float(np.std(returns)) * math.sqrt(float(horizon))
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError("cumulative-return scale must be positive and finite")
    return scale


@dataclass(frozen=True)
class FitSelectionSplit:
    """Chronological internal split with non-overlapping target intervals.

    Attributes:
        fit_windows: Chronologically first ``fit_fraction`` of eligible windows.
        selection_windows: Remaining tail windows whose target intervals begin
            after the last fit target interval ends (an embargo gap in
            between keeps the two sets' target returns disjoint).
        gap_windows: Window count in the embargo gap (neither subset).
        fit_target_end_index: Last return index covered by fit targets.
        selection_target_start_index: First return index covered by selection targets.
        split_hash: Deterministic identity of the split.
    """

    fit_windows: tuple[SdeWindow, ...]
    selection_windows: tuple[SdeWindow, ...]
    gap_windows: int
    fit_target_end_index: int
    selection_target_start_index: int
    split_hash: str

    @property
    def n_fit(self) -> int:
        """Number of fit-subset windows."""
        return len(self.fit_windows)

    @property
    def n_selection(self) -> int:
        """Number of selection-subset windows."""
        return len(self.selection_windows)

    @property
    def n_eligible(self) -> int:
        """Total number of eligible windows."""
        return self.n_fit + self.n_selection + self.gap_windows


def split_fit_selection(
    windows: Sequence[SdeWindow],
    fit_fraction: float,
    spec: WindowSpec | None = None,
) -> FitSelectionSplit:
    """Split eligible windows chronologically into fit and selection subsets.

    The first ``floor(fit_fraction * n)`` windows form the fit subset.  The
    selection subset starts at the first window whose target interval begins
    after the fit subset's last target interval ends, so fit and selection
    TARGET return intervals never overlap.  Windows between the two subsets
    (the embargo gap) belong to neither.

    Args:
        windows: Chronologically ordered eligible windows.
        fit_fraction: Fraction of eligible windows used for the fit subset.
        spec: Window geometry (uses ``horizon`` for interval arithmetic).

    Returns:
        The frozen split with a deterministic split hash.

    Raises:
        ValueError: If the fraction is invalid or no valid split exists.
    """
    spec = WindowSpec() if spec is None else spec
    if not 0.0 < fit_fraction < 1.0:
        raise ValueError("fit_fraction must be strictly between 0 and 1")
    ordered = tuple(windows)
    n = len(ordered)
    if n < 2:
        raise ValueError("at least two eligible windows are required for a split")
    fit_count = max(1, math.floor(fit_fraction * n))
    fit = ordered[:fit_count]
    last_fit = fit[-1]
    fit_target_end_index = last_fit.start_index + spec.horizon - 1
    selection = tuple(w for w in ordered[fit_count:] if w.start_index > fit_target_end_index)
    if not selection:
        raise ValueError("no selection windows remain after the embargo gap")
    first_selection = selection[0]
    identity = canonical_dumps(
        {
            "fit_fraction": fit_fraction,
            "horizon": spec.horizon,
            "n_eligible": n,
            "n_fit": len(fit),
            "n_selection": len(selection),
            "fit_window_ids": [w.window_id for w in fit],
            "selection_window_ids": [w.window_id for w in selection],
            "fit_target_end_index": fit_target_end_index,
            "selection_target_start_index": first_selection.start_index,
        }
    )
    return FitSelectionSplit(
        fit_windows=fit,
        selection_windows=selection,
        gap_windows=n - len(fit) - len(selection),
        fit_target_end_index=fit_target_end_index,
        selection_target_start_index=first_selection.start_index,
        split_hash=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
    )
