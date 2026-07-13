"""Shared fixtures for raw DBN validation tests (Task 7a)."""

from datetime import UTC, datetime

import pytest

from neuralmarket.data.acquisition.requests import AcquisitionRequest


@pytest.fixture
def arcx_request() -> AcquisitionRequest:
    """A single, fully-formed ARCX AcquisitionRequest for validation tests."""
    now = datetime(2019, 1, 2, tzinfo=UTC)
    return AcquisitionRequest(
        request_id="r1",
        wave="arcx_catalog",
        dataset="ARCX.PILLAR",
        schema="definition",
        symbols=("SPY",),
        stype_in="raw_symbol",
        stype_out="instrument_id",
        start=now,
        end_exclusive=now,
        encoding="dbn",
        compression="zstd",
        expected_split="training",
        session_date=None,
        calendar="XNYS",
        estimated_record_count=10,
        estimated_billable_size=1000,
        estimated_cost="0.10",
        currency="USD",
        request_hash="f" * 64,
    )
