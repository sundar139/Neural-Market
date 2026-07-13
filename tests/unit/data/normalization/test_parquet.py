"""Tests for Parquet conversion plan design (Task 7b)."""

import inspect
from datetime import UTC, datetime

from neuralmarket.data.normalization.parquet import build_conversion_plan, reconcile_row_counts
from neuralmarket.data.normalization.provenance import ProvenanceColumns, provenance_columns_for


def test_conversion_plan_column_order_is_deterministic_and_includes_provenance(
    arcx_request,
) -> None:
    """Test that column order is deterministic and includes provenance columns."""
    provenance = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    plan_a = build_conversion_plan(
        dbn_columns=("ts_event", "price", "size"), provenance=provenance
    )
    plan_b = build_conversion_plan(
        dbn_columns=("ts_event", "price", "size"), provenance=provenance
    )
    assert plan_a.column_order == plan_b.column_order
    assert set(ProvenanceColumns.model_fields).issubset(set(plan_a.column_order))
    assert plan_a.compression == "zstd"


def test_conversion_plan_never_accepts_a_raw_file_argument() -> None:
    """Test that build_conversion_plan does not accept raw_file or raw_path arguments."""
    params = inspect.signature(build_conversion_plan).parameters
    assert "raw_path" not in params
    assert "raw_file" not in params


def test_reconcile_row_counts() -> None:
    """Test that row count reconciliation works for matching and non-matching counts."""
    assert reconcile_row_counts(100, 100) is True
    assert reconcile_row_counts(100, 99) is False
