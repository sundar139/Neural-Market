"""Tests for provenance column generation (Task 7b)."""

from datetime import UTC, datetime

from neuralmarket.data.normalization.provenance import provenance_columns_for


def test_provenance_columns_for(arcx_request) -> None:
    """Test that provenance columns populate correctly from request + checksum + timestamp."""
    columns = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert columns.source_request_id == arcx_request.request_id
    assert columns.raw_sha256 == "a" * 64
