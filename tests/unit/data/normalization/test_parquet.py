"""Tests for Parquet conversion plan design (Task 7b)."""

import inspect
from datetime import UTC, datetime

import pytest

from neuralmarket.data.normalization.parquet import (
    build_conversion_plan,
    normalize_frame_to_parquet,
    reconcile_row_counts,
)
from neuralmarket.data.normalization.provenance import ProvenanceColumns, provenance_columns_for

pytestmark = pytest.mark.unit


def test_conversion_plan_column_order_is_deterministic_and_includes_provenance(
    arcx_request,
) -> None:
    """Test that column order is deterministic and includes provenance columns."""
    provenance = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    plan_a = build_conversion_plan(dbn_columns=("ts_event", "price", "size"), provenance=provenance)
    plan_b = build_conversion_plan(dbn_columns=("ts_event", "price", "size"), provenance=provenance)
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


def test_normalize_frame_to_parquet_is_atomic_and_preserves_provenance(
    tmp_path, arcx_request
) -> None:
    import pandas as pd

    provenance = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    output = tmp_path / "normalized.parquet"
    result = normalize_frame_to_parquet(
        frame=pd.DataFrame(
            {
                "ts_event": ["2019-01-02T00:00:00Z"],
                "raw_symbol": ["SPY"],
                "instrument_id": [1],
                "price": [100.0],
            }
        ),
        output_path=output,
        provenance=provenance,
        expected_raw_record_count=1,
    )
    normalized = pd.read_parquet(output)
    assert result.row_count == 1
    assert normalized.loc[0, "source_request_id"] == arcx_request.request_id
    assert str(normalized["ts_event"].dtype) == "datetime64[ns, UTC]"
    assert (tmp_path / "normalized.parquet.json").is_file()


def test_normalize_frame_to_parquet_removes_partial_on_accounting_mismatch(
    tmp_path, arcx_request
) -> None:
    provenance = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    output = tmp_path / "normalized.parquet"
    with pytest.raises(ValueError, match="accounting mismatch"):
        normalize_frame_to_parquet(
            frame={
                "ts_event": ["2019-01-02T00:00:00Z"],
                "raw_symbol": ["SPY"],
                "instrument_id": [1],
            },
            output_path=output,
            provenance=provenance,
            expected_raw_record_count=2,
        )
    assert not output.exists()
    assert not (tmp_path / "normalized.parquet.partial").exists()


def test_normalize_frame_to_parquet_refuses_existing_artifact(tmp_path, arcx_request) -> None:
    output = tmp_path / "normalized.parquet"
    output.write_bytes(b"existing")
    provenance = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        normalize_frame_to_parquet(
            frame={"raw_symbol": ["SPY"], "instrument_id": [1]},
            output_path=output,
            provenance=provenance,
            expected_raw_record_count=1,
        )
    assert output.read_bytes() == b"existing"


def test_normalize_frame_to_parquet_does_not_publish_primary_when_sidecar_publish_fails(
    tmp_path, arcx_request, monkeypatch
) -> None:
    import pandas as pd

    from neuralmarket.data.normalization import parquet

    output = tmp_path / "normalized.parquet"
    provenance = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    real_rename = parquet.os.rename

    def fail_sidecar(source, destination) -> None:
        if destination == output.with_suffix(output.suffix + ".json"):
            raise OSError("publish failed")
        real_rename(source, destination)

    monkeypatch.setattr(parquet.os, "rename", fail_sidecar)
    with pytest.raises(OSError, match="publish failed"):
        normalize_frame_to_parquet(
            frame=pd.DataFrame({"raw_symbol": ["SPY"], "instrument_id": [1]}),
            output_path=output,
            provenance=provenance,
            expected_raw_record_count=1,
        )
    assert not output.exists()
    assert not output.with_suffix(output.suffix + ".json").exists()
