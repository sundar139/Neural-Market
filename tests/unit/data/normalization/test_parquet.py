"""Tests for Parquet conversion plan design (Task 7b)."""

import inspect
from datetime import UTC, datetime

import pytest

from neuralmarket.data.normalization.parquet import (
    build_conversion_plan,
    normalize_dbn_store_to_parquet,
    normalize_frame_to_parquet,
    reconcile_row_counts,
)
from neuralmarket.data.normalization.provenance import ProvenanceColumns, provenance_columns_for
from neuralmarket.data.raw.integrity import sha256_of_file

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


def test_normalize_frame_to_parquet_preserves_existing_raw_symbol(tmp_path, arcx_request) -> None:
    import pandas as pd

    output = tmp_path / "existing-raw-symbol.parquet"
    normalize_frame_to_parquet(
        frame=pd.DataFrame(
            {
                "raw_symbol": ["EXISTING"],
                "symbol": ["PROVIDER"],
                "instrument_id": [15144],
            }
        ),
        output_path=output,
        provenance=provenance_columns_for(
            arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        expected_raw_record_count=1,
    )

    normalized = pd.read_parquet(output)
    assert normalized["raw_symbol"].tolist() == ["EXISTING"]
    assert normalized["symbol"].tolist() == ["PROVIDER"]
    assert normalized["instrument_id"].tolist() == [15144]


def test_normalize_frame_to_parquet_maps_provider_symbols_row_for_row(
    tmp_path, arcx_request
) -> None:
    import pandas as pd

    output = tmp_path / "provider-symbols.parquet"
    normalize_frame_to_parquet(
        frame=pd.DataFrame(
            {
                "symbol": ["SPY", "QQQ", "SPY"],
                "instrument_id": [15144, 23456, 15144],
            }
        ),
        output_path=output,
        provenance=provenance_columns_for(
            arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        expected_raw_record_count=3,
    )

    normalized = pd.read_parquet(output)
    assert normalized["raw_symbol"].tolist() == ["SPY", "QQQ", "SPY"]
    assert normalized["instrument_id"].tolist() == [15144, 23456, 15144]


@pytest.mark.parametrize("invalid_symbol", [None, "", "   ", 15144])
def test_normalize_frame_to_parquet_rejects_invalid_provider_symbol(
    tmp_path, arcx_request, invalid_symbol
) -> None:
    with pytest.raises(ValueError, match="provider symbol must contain non-empty strings"):
        normalize_frame_to_parquet(
            frame={"symbol": [invalid_symbol], "instrument_id": [15144]},
            output_path=tmp_path / "invalid-provider-symbol.parquet",
            provenance=provenance_columns_for(
                arcx_request,
                raw_checksum="a" * 64,
                ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            expected_raw_record_count=1,
        )


def test_normalize_frame_to_parquet_rejects_missing_symbol_identity(tmp_path, arcx_request) -> None:
    with pytest.raises(ValueError, match="must retain raw_symbol and instrument_id"):
        normalize_frame_to_parquet(
            frame={"instrument_id": [15144]},
            output_path=tmp_path / "missing-symbol.parquet",
            provenance=provenance_columns_for(
                arcx_request,
                raw_checksum="a" * 64,
                ingested_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            expected_raw_record_count=1,
        )


def test_real_paid_dbn_normalizes_offline_with_identity_and_provenance(
    tmp_path,
) -> None:
    import json
    from pathlib import Path

    import databento
    import pandas as pd
    import pyarrow.parquet as pq

    from neuralmarket.data.acquisition.requests import AcquisitionRequest

    root = Path(__file__).resolve().parents[4]
    raw_path = (
        root
        / "data/raw/databento/pilot_january_2019/ARCX.PILLAR/ohlcv-1d"
        / "start_date=2019-01-02/end_date=2019-02-01/6b46de651d2cf921.dbn"
    )
    if not raw_path.is_file():
        pytest.skip("protected paid DBN is not present in this checkout")
    expected_raw_sha256 = (
        "e70e6ab053b44834f0f9b67543544fda"  # pragma: allowlist secret
        "0179fb9c19dcd656188d59af1fde8f79"  # pragma: allowlist secret
    )
    assert raw_path.stat().st_size == 950
    assert sha256_of_file(raw_path) == expected_raw_sha256
    manifest = json.loads(
        (root / "data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8")
    )
    request = AcquisitionRequest.model_validate(
        next(item for item in manifest["requests"] if item["request_id"] == "6b46de651d2cf921")
    )
    decoded = databento.DBNStore.from_file(raw_path).to_df()
    output = tmp_path / "paid-dbn.parquet"

    result = normalize_dbn_store_to_parquet(
        dbn_store=databento.DBNStore.from_file(raw_path),
        output_path=output,
        provenance=provenance_columns_for(
            request, expected_raw_sha256, datetime(2026, 8, 12, tzinfo=UTC)
        ),
        expected_raw_record_count=21,
    )

    normalized = pd.read_parquet(output)
    metadata = pq.read_metadata(output)
    assert result.row_count == len(decoded) == len(normalized) == metadata.num_rows == 21
    assert {"raw_symbol", "instrument_id"}.issubset(normalized.columns)
    assert normalized["raw_symbol"].tolist() == decoded["symbol"].tolist()
    assert normalized["instrument_id"].tolist() == decoded["instrument_id"].tolist()
    assert normalized["raw_symbol"].unique().tolist() == ["SPY"]
    assert normalized["instrument_id"].unique().tolist() == [15144]
    assert normalized["source_request_id"].unique().tolist() == ["6b46de651d2cf921"]
    assert normalized["source_dataset"].unique().tolist() == ["ARCX.PILLAR"]
    assert normalized["source_schema"].unique().tolist() == ["ohlcv-1d"]
    assert normalized["raw_sha256"].unique().tolist() == [expected_raw_sha256]
    assert set(ProvenanceColumns.model_fields).issubset(normalized.columns)


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
