"""Deterministic conversion planning and atomic Parquet normalization."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.storage import _fsync_parent
from neuralmarket.data.normalization.provenance import ProvenanceColumns
from neuralmarket.data.raw.integrity import sha256_of_file


class ParquetConversionPlan(BaseModel):
    """Plan for converting raw DBN data to normalized Parquet format."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    column_order: tuple[str, ...]
    compression: Literal["zstd"]
    timestamp_columns: tuple[str, ...]
    row_count_source: Literal["dbn_record_count"]
    schema_fingerprint: str


def build_conversion_plan(
    *, dbn_columns: tuple[str, ...], provenance: ProvenanceColumns
) -> ParquetConversionPlan:
    """Build a deterministic conversion plan for DBN to Parquet normalization.

    Deterministic column order:
    dbn_columns + ("raw_symbol", "instrument_id") + tuple(ProvenanceColumns.model_fields),
    deduplicated while preserving first occurrence.

    Args:
        dbn_columns: Column names from the raw DBN file.
        provenance: Provenance metadata to be added to the Parquet file.

    Returns:
        ParquetConversionPlan with column order, compression, and schema fingerprint.
    """
    # Build column order: dbn_columns + raw_symbol/instrument_id + provenance fields
    # Deduplicate while preserving first occurrence
    base_columns = (*dbn_columns, "raw_symbol", "instrument_id")
    provenance_fields = tuple(ProvenanceColumns.model_fields.keys())

    seen = set()
    column_order_list: list[str] = []
    for col in base_columns + provenance_fields:
        if col not in seen:
            seen.add(col)
            column_order_list.append(col)

    column_order = tuple(column_order_list)

    # Compute schema fingerprint as SHA-256 of comma-separated column names
    schema_fingerprint = hashlib.sha256(",".join(column_order).encode("utf-8")).hexdigest()

    # Extract timestamp columns (columns with "ts" in the name)
    timestamp_columns = tuple(col for col in column_order if "ts" in col.lower())

    return ParquetConversionPlan(
        column_order=column_order,
        compression="zstd",
        timestamp_columns=timestamp_columns,
        row_count_source="dbn_record_count",
        schema_fingerprint=schema_fingerprint,
    )


def reconcile_row_counts(dbn_record_count: int, parquet_row_count: int) -> bool:
    """Check if raw DBN and normalized Parquet row counts reconcile.

    This is a pure equality check - both counts must be identical.

    Args:
        dbn_record_count: Number of records in the raw DBN file.
        parquet_row_count: Number of rows in the normalized Parquet file.

    Returns:
        True if counts match exactly, False otherwise.
    """
    return dbn_record_count == parquet_row_count


class ParquetNormalizationResult(BaseModel):
    """Verified outputs from one atomic DBN-frame to Parquet normalization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sidecar_path: str
    row_count: int
    sha256: str
    schema_fingerprint: str


def normalize_frame_to_parquet(
    *,
    frame: Any,
    output_path: Path,
    provenance: ProvenanceColumns,
    expected_raw_record_count: int,
) -> ParquetNormalizationResult:
    """Normalize a DBN-derived frame to atomic zstd Parquet plus provenance sidecar."""
    import pandas as pd
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    normalized = pd.DataFrame(frame).copy()
    if not {"raw_symbol", "instrument_id"}.issubset(normalized.columns):
        raise ValueError("normalized data must retain raw_symbol and instrument_id")
    for column in normalized.columns:
        if "ts" in str(column).lower() or "timestamp" in str(column).lower():
            normalized[column] = pd.to_datetime(normalized[column], utc=True)
    for field, value in provenance.model_dump().items():
        normalized[field] = value

    plan = build_conversion_plan(
        dbn_columns=tuple(
            str(column)
            for column in normalized.columns
            if column not in ProvenanceColumns.model_fields
        ),
        provenance=provenance,
    )
    normalized = normalized.loc[:, list(plan.column_order)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_name(output_path.name + ".partial")
    sidecar_path = output_path.with_suffix(output_path.suffix + ".json")
    sidecar_partial = sidecar_path.with_name(sidecar_path.name + ".partial")
    existing = [
        path for path in (output_path, partial_path, sidecar_path, sidecar_partial) if path.exists()
    ]
    if existing:
        raise FileExistsError(f"refusing to overwrite normalization artifact: {existing[0]}")
    try:
        with partial_path.open("xb") as handle:
            normalized.to_parquet(handle, engine="pyarrow", compression="zstd", index=False)
            os.fsync(handle.fileno())
        metadata = pq.read_metadata(partial_path)
        if not reconcile_row_counts(expected_raw_record_count, metadata.num_rows):
            raise ValueError(
                "DBN/Parquet accounting mismatch: "
                f"raw={expected_raw_record_count}, parquet={metadata.num_rows}"
            )
        schema_fingerprint = hashlib.sha256(str(metadata.schema).encode()).hexdigest()
        checksum = sha256_of_file(partial_path)
        sidecar = {
            **provenance.model_dump(),
            "normalized_sha256": checksum,
            "normalized_row_count": metadata.num_rows,
            "schema_fingerprint": schema_fingerprint,
        }
        with sidecar_partial.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(sidecar, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.rename(partial_path, output_path)
        except Exception:
            raise
        try:
            os.rename(sidecar_partial, sidecar_path)
        except Exception:
            output_path.unlink(missing_ok=True)
            raise
        partial_path.unlink(missing_ok=True)
        sidecar_partial.unlink(missing_ok=True)
        _fsync_parent(output_path.parent)
        return ParquetNormalizationResult(
            path=str(output_path),
            sidecar_path=str(sidecar_path),
            row_count=metadata.num_rows,
            sha256=checksum,
            schema_fingerprint=schema_fingerprint,
        )
    finally:
        partial_path.unlink(missing_ok=True)
        sidecar_partial.unlink(missing_ok=True)


def normalize_dbn_store_to_parquet(
    *,
    dbn_store: Any,
    output_path: Path,
    provenance: ProvenanceColumns,
    expected_raw_record_count: int,
) -> ParquetNormalizationResult:
    """Normalize an injected DBNStore-shaped object without mutating its source."""
    if not hasattr(dbn_store, "to_df"):
        raise TypeError("dbn_store must expose to_df()")
    return normalize_frame_to_parquet(
        frame=dbn_store.to_df(),
        output_path=output_path,
        provenance=provenance,
        expected_raw_record_count=expected_raw_record_count,
    )
