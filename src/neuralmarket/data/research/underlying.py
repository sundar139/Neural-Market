"""Deterministic empirical SPY underlying series contract.

The neural-SDE underlying is SPY itself (research protocol core scope). The
accepted development source is the validated ARCX.PILLAR ohlcv-1d acquisition:
session dates are bound from the checksum-verified raw DBN (ts_event index),
prices come from the quality-validated normalized parquet, and returns are
conventional close-to-close log returns. Both artifacts are acquisition
evidence and are never modified.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from neuralmarket.data.errors import CoverageError
from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.raw.integrity import sha256_of_file
from neuralmarket.data.research.inventory import ResearchInventory

UNDERLYING_SCHEMA_VERSION: Literal["research-underlying-daily-v1"] = "research-underlying-daily-v1"

_PRICE_FIELD: Literal["close"] = "close"


class EmpiricalUnderlyingSeries(BaseModel):
    """One deterministic SPY daily series with full source binding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["research-underlying-daily-v1"] = UNDERLYING_SCHEMA_VERSION
    split: Literal["training", "validation"]
    price_field: Literal["close"] = _PRICE_FIELD
    parent_request_id: str
    execution_request_id: str
    raw_sha256: str
    normalized_sha256: str
    inventory_hash: str
    plan_hash: str
    session_dates: tuple[str, ...]
    prices: tuple[float, ...]
    log_returns: tuple[float, ...]
    n_observations: int
    series_sha256: str

    @property
    def returns_array(self) -> np.ndarray:
        """Log returns as a float64 array."""
        return np.asarray(self.log_returns, dtype=np.float64)


def _require_clean_prices(dates: pd.DatetimeIndex, prices: np.ndarray) -> None:
    if len(dates) != len(prices):
        raise CoverageError("underlying date/price length mismatch")
    if len(dates) == 0:
        raise CoverageError("underlying series is empty")
    if not dates.is_unique:
        raise CoverageError("underlying series contains duplicate session dates")
    if not dates.is_monotonic_increasing:
        raise CoverageError("underlying series is not chronologically ordered")
    if np.any(~np.isfinite(prices)):
        raise CoverageError("underlying series contains non-finite prices")
    if np.any(prices <= 0):
        raise CoverageError("underlying series contains non-positive prices")


def _sealed_test_guard(dates: pd.DatetimeIndex) -> None:
    """Reject any observation at or after the sealed final-test block start.

    The split design ends validation at 2023-06-30; the purge/embargo boundary
    pushes the final-test block later, so any date past the validation anchor
    is sealed and must never enter research artifacts.
    """
    sealed_boundary = pd.Timestamp("2023-07-01", tz="UTC")
    if len(dates) and dates.max() >= sealed_boundary:
        raise CoverageError("sealed final-test dates entered the underlying series")


def build_underlying_series(
    *,
    inventory: ResearchInventory,
    split: Literal["training", "validation"],
    raw_root: Path,
    processed_root: Path,
) -> EmpiricalUnderlyingSeries:
    """Load and bind one split's empirical SPY daily series from frozen artifacts."""
    matches = [
        entry
        for entry in inventory.requirements
        if entry.purpose == "underlying_daily_reference"
        and entry.expected_split == split
        and entry.disposition == "quality_validated_paid"
    ]
    if len(matches) != 1:
        raise CoverageError(
            f"expected exactly one paid underlying daily requirement for {split}, "
            f"found {len(matches)}"
        )
    entry = matches[0]
    if entry.session_date is not None:
        raise CoverageError("underlying daily requirement must not be session-scoped")
    execution_id = entry.execution_request_ids[0]
    raw_sha256 = entry.raw_sha256s[0]
    raw_tree = raw_root / Path("development_strategy_b") / split / "ARCX.PILLAR" / "ohlcv-1d"
    normalized_tree = (
        processed_root
        / Path("databento")
        / "development_strategy_b"
        / split
        / "ARCX.PILLAR"
        / "ohlcv-1d"
    )
    raw_candidates = list(raw_tree.rglob(f"{execution_id}.dbn"))
    normalized_candidates = list(normalized_tree.rglob(f"{execution_id}.parquet"))
    if len(raw_candidates) != 1 or len(normalized_candidates) != 1:
        raise CoverageError(
            f"underlying artifacts must be uniquely located for {split}: "
            f"{len(raw_candidates)} raw / {len(normalized_candidates)} parquet"
        )
    raw_path, normalized_path = raw_candidates[0], normalized_candidates[0]
    if sha256_of_file(raw_path) != raw_sha256:
        raise CoverageError(f"underlying raw checksum mismatch: {raw_path}")

    import databento

    try:
        raw_frame = databento.DBNStore.from_file(raw_path).to_df()
    except Exception as exc:
        raise CoverageError(f"underlying raw DBN could not be decoded: {exc}") from exc
    if raw_frame.index.name != "ts_event":
        raise CoverageError(
            f"underlying raw DBN lacks ts_event index (found {raw_frame.index.name!r})"
        )
    dates = pd.DatetimeIndex(raw_frame.index).tz_convert("UTC").normalize()
    if len(dates) != len(set(dates)):
        raise CoverageError("underlying raw DBN contains duplicate session dates")

    normalized = pd.read_parquet(normalized_path)
    required = {"open", "high", "low", "close"}
    if not required.issubset(normalized.columns):
        missing = required - set(normalized.columns)
        raise CoverageError(f"underlying normalized parquet lacks required fields: {missing}")
    if len(normalized) != len(dates):
        raise CoverageError(
            f"underlying raw/normalized row count mismatch: {len(dates)} vs {len(normalized)}"
        )
    prices = normalized[_PRICE_FIELD].to_numpy(dtype=np.float64)

    _require_clean_prices(dates, prices)
    _sealed_test_guard(dates)

    returns = np.log(prices[1:] / prices[:-1])
    if np.any(~np.isfinite(returns)):
        raise CoverageError("underlying log returns contain non-finite values")

    series_identity = canonical_dumps(
        {
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "prices": [float(p) for p in prices],
            "returns": [float(r) for r in returns],
        }
    )
    return EmpiricalUnderlyingSeries(
        split=split,
        parent_request_id=entry.development_request_id,
        execution_request_id=execution_id,
        raw_sha256=raw_sha256,
        normalized_sha256=sha256_of_file(normalized_path),
        inventory_hash=inventory.inventory_hash,
        plan_hash=inventory.plan_hash,
        session_dates=tuple(d.strftime("%Y-%m-%d") for d in dates),
        prices=tuple(float(p) for p in prices),
        log_returns=tuple(float(r) for r in returns),
        n_observations=len(returns),
        series_sha256=hashlib.sha256(series_identity.encode("utf-8")).hexdigest(),
    )


def underlying_returns(
    series: EmpiricalUnderlyingSeries,
) -> np.ndarray:
    """Return the series log-returns as a float64 array."""
    return series.returns_array
