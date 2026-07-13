"""Parquet conversion plan design (Task 7b)."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.normalization.provenance import ProvenanceColumns


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
