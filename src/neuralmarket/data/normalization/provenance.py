"""Provenance column generation for normalized Parquet files (Task 7b)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

import neuralmarket
from neuralmarket.data.acquisition.requests import AcquisitionRequest


class ProvenanceColumns(BaseModel):
    """Provenance metadata columns to be added to normalized Parquet files."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_request_id: str
    source_dataset: str
    source_schema: str
    ingestion_timestamp: str
    raw_sha256: str
    pipeline_version: str


def provenance_columns_for(
    request: AcquisitionRequest, raw_checksum: str, ingested_at: datetime
) -> ProvenanceColumns:
    """Create provenance columns from an AcquisitionRequest and raw file metadata.

    Args:
        request: The AcquisitionRequest this normalization was derived from.
        raw_checksum: SHA-256 checksum of the raw DBN file.
        ingested_at: Timestamp when the raw file was ingested.

    Returns:
        ProvenanceColumns with source metadata and checksums.
    """
    return ProvenanceColumns(
        source_request_id=request.request_id,
        source_dataset=request.dataset,
        source_schema=request.schema_name,
        ingestion_timestamp=ingested_at.isoformat(),
        raw_sha256=raw_checksum,
        pipeline_version=neuralmarket.__version__,
    )
