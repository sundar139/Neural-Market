"""Empirical underlying series: loading, validation, isolation, provenance."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from neuralmarket.data.errors import CoverageError
from neuralmarket.data.research.inventory import build_research_inventory
from neuralmarket.data.research.underlying import (
    EmpiricalUnderlyingSeries,
    _require_clean_prices,
    _sealed_test_guard,
    build_underlying_series,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_SCOPE_SRC = _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_JOURNAL = _ROOT / "data/state/development_acquisition_journal.sqlite"
_CONFIG = _ROOT / "configs/data/spy_daily_databento.yaml"
_HEAD = "70544a482dcf5762a968e3f0c7df35bb7c9a5db8"  # pragma: allowlist secret


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


def _dates(values: list[str]) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True))


class TestPriceValidation:
    def test_clean_series_accepted(self) -> None:
        dates = _dates(["2018-05-01", "2018-05-02", "2018-05-03"])
        _require_clean_prices(dates, np.array([100.0, 101.0, 102.0]))

    def test_non_positive_price_rejected(self) -> None:
        dates = _dates(["2018-05-01", "2018-05-02"])
        with pytest.raises(CoverageError, match="non-positive"):
            _require_clean_prices(dates, np.array([100.0, 0.0]))

    def test_duplicate_dates_rejected(self) -> None:
        dates = _dates(["2018-05-01", "2018-05-01"])
        with pytest.raises(CoverageError, match="duplicate"):
            _require_clean_prices(dates, np.array([100.0, 101.0]))

    def test_non_monotonic_dates_rejected(self) -> None:
        dates = _dates(["2018-05-03", "2018-05-01"])
        with pytest.raises(CoverageError, match="chronologically"):
            _require_clean_prices(dates, np.array([100.0, 101.0]))

    def test_length_mismatch_rejected(self) -> None:
        dates = _dates(["2018-05-01", "2018-05-02"])
        with pytest.raises(CoverageError, match="length mismatch"):
            _require_clean_prices(dates, np.array([100.0]))

    def test_non_finite_rejected(self) -> None:
        dates = _dates(["2018-05-01", "2018-05-02"])
        with pytest.raises(CoverageError, match="non-finite"):
            _require_clean_prices(dates, np.array([100.0, np.nan]))

    def test_sealed_test_dates_rejected(self) -> None:
        with pytest.raises(CoverageError, match="sealed final-test"):
            _sealed_test_guard(_dates(["2023-06-30", "2023-07-03"]))

    def test_validation_anchor_dates_accepted(self) -> None:
        _sealed_test_guard(_dates(["2023-06-29", "2023-06-30"]))


class TestProductionSeries:
    def test_training_series_loads_deterministically(self) -> None:
        inventory = _inventory()
        first = build_underlying_series(
            inventory=inventory,
            split="training",
            raw_root=_ROOT / "data/raw/databento",
            processed_root=_ROOT / "data/processed",
        )
        second = build_underlying_series(
            inventory=inventory,
            split="training",
            raw_root=_ROOT / "data/raw/databento",
            processed_root=_ROOT / "data/processed",
        )
        assert first.model_dump() == second.model_dump()
        assert first.schema_version == "research-underlying-daily-v1"
        assert first.split == "training"
        assert first.n_observations == len(first.session_dates) - 1
        assert first.session_dates[0] == "2018-05-01"
        assert first.session_dates[-1] == "2021-12-31"
        assert first.inventory_hash == inventory.inventory_hash

    def test_validation_series_bounds(self) -> None:
        inventory = _inventory()
        series = build_underlying_series(
            inventory=inventory,
            split="validation",
            raw_root=_ROOT / "data/raw/databento",
            processed_root=_ROOT / "data/processed",
        )
        assert series.session_dates[0] == "2022-05-26"
        assert series.session_dates[-1] == "2023-06-30"
        assert series.n_observations == len(series.session_dates) - 1

    def test_series_binds_source_identities(self) -> None:
        inventory = _inventory()
        entry = next(
            e
            for e in inventory.requirements
            if e.purpose == "underlying_daily_reference" and e.expected_split == "training"
        )
        series = build_underlying_series(
            inventory=inventory,
            split="training",
            raw_root=_ROOT / "data/raw/databento",
            processed_root=_ROOT / "data/processed",
        )
        assert series.execution_request_id == entry.execution_request_ids[0]
        assert series.raw_sha256 == entry.raw_sha256s[0]
        assert len(series.normalized_sha256) == 64
        assert len(series.series_sha256) == 64

    def test_checksum_mismatch_fails_closed(self) -> None:
        inventory = _inventory()
        with pytest.raises(CoverageError, match="checksum mismatch"):
            build_underlying_series(
                inventory=inventory.model_copy(
                    update={
                        "requirements": tuple(
                            entry.model_copy(
                                update={
                                    "raw_sha256s": ("0" * 64,)
                                    if entry.purpose == "underlying_daily_reference"
                                    and entry.expected_split == "training"
                                    else entry.raw_sha256s
                                }
                            )
                            for entry in inventory.requirements
                        )
                    }
                ),
                split="training",
                raw_root=_ROOT / "data/raw/databento",
                processed_root=_ROOT / "data/processed",
            )

    def test_returns_are_close_to_close_log(self) -> None:
        inventory = _inventory()
        series = build_underlying_series(
            inventory=inventory,
            split="training",
            raw_root=_ROOT / "data/raw/databento",
            processed_root=_ROOT / "data/processed",
        )
        prices = np.asarray(series.prices)
        expected = np.log(prices[1:] / prices[:-1])
        assert np.allclose(series.returns_array, expected, rtol=0, atol=1e-15)

    def test_no_final_test_dates_in_either_split(self) -> None:
        inventory = _inventory()
        for split in ("training", "validation"):
            series = build_underlying_series(
                inventory=inventory,
                split=split,
                raw_root=_ROOT / "data/raw/databento",
                processed_root=_ROOT / "data/processed",
            )
            assert all(d <= "2023-06-30" for d in series.session_dates)

    def test_serialized_round_trip(self) -> None:
        inventory = _inventory()
        series = build_underlying_series(
            inventory=inventory,
            split="validation",
            raw_root=_ROOT / "data/raw/databento",
            processed_root=_ROOT / "data/processed",
        )
        payload = json.loads(series.model_dump_json())
        reloaded = EmpiricalUnderlyingSeries.model_validate(payload)
        assert reloaded == series
        assert reloaded.series_sha256 == series.series_sha256
