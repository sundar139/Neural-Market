"""Tests for provenance column generation (Task 7b)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from neuralmarket.data.normalization.provenance import provenance_columns_for

pytestmark = pytest.mark.unit


def test_provenance_columns_for(arcx_request) -> None:
    """Test that provenance columns populate correctly from request + checksum + timestamp."""
    columns = provenance_columns_for(
        arcx_request, raw_checksum="a" * 64, ingested_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    assert columns.source_request_id == arcx_request.request_id
    assert columns.raw_sha256 == "a" * 64


def test_provenance_normalizes_checksum_and_timestamp_to_utc(arcx_request) -> None:
    columns = provenance_columns_for(
        arcx_request,
        "A" * 64,
        datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2))),
    )
    assert columns.raw_sha256 == "a" * 64
    assert columns.ingestion_timestamp == "2025-12-31T22:00:00+00:00"


@pytest.mark.parametrize(
    ("checksum", "timestamp"),
    [
        ("not-a-checksum", datetime.now(UTC)),
        ("a" * 64, datetime(2026, 1, 1)),
    ],
)
def test_provenance_rejects_invalid_inputs(
    arcx_request, checksum: str, timestamp: datetime
) -> None:
    with pytest.raises(ValueError):
        provenance_columns_for(arcx_request, checksum, timestamp)
