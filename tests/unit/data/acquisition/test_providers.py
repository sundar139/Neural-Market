from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.providers import (
    DatabentoPaidHistoricalProvider,
    PaidProviderError,
    _classify_provider_error,
)
from neuralmarket.data.acquisition.requests import (
    build_pilot_request_plan,
    finalize_request,
    load_pilot_config,
)

pytestmark = pytest.mark.unit


def _finalized_request():
    config = load_pilot_config("configs/data/acquisition/pilot_january_2019.yaml")
    draft = build_pilot_request_plan(config)[0]
    estimate = MetadataEstimate(
        dataset=draft.dataset,
        schema=draft.schema_name,
        symbol=draft.symbols[0],
        stype_in=draft.stype_in,
        window_start=draft.start,
        window_end=draft.end_exclusive,
        record_count=1,
        billable_size_bytes=4,
        cost_usd=Decimal("0.01"),
        retries=0,
    )
    return finalize_request(draft, estimate, datetime(2026, 1, 1, tzinfo=UTC))


class _FakeStore:
    dataset = "ARCX.PILLAR"
    schema = "definition"
    symbols = ("SPY",)

    def to_file(self, path):
        path.write_bytes(b"fake-dbn")

    def to_df(self):
        return [{"instrument_id": 1, "raw_symbol": "SPY"}]


def test_paid_adapter_writes_fake_store_atomically(tmp_path) -> None:
    request = _finalized_request()
    store = _FakeStore()
    client = SimpleNamespace(timeseries=SimpleNamespace(get_range=Mock(return_value=store)))
    provider = DatabentoPaidHistoricalProvider(
        client=client,
        data_root=tmp_path,
        validator=lambda _path, _checksum: True,
    )

    result = provider.acquire_range(request)

    assert result.request_id == request.request_id
    assert result.record_count == 1
    assert result.sha256
    assert result.raw_path.endswith(".dbn")
    client.timeseries.get_range.assert_called_once()
    assert not list(tmp_path.glob("*.provider.partial"))


def test_paid_adapter_rejects_draft_before_client_call() -> None:
    config = load_pilot_config("configs/data/acquisition/pilot_january_2019.yaml")
    draft = build_pilot_request_plan(config)[0]
    client = SimpleNamespace(timeseries=SimpleNamespace(get_range=Mock()))
    provider = DatabentoPaidHistoricalProvider(
        client=client,
        data_root=__import__("pathlib").Path("data"),
        validator=lambda _path, _checksum: True,
    )

    with pytest.raises(ValueError, match="not finalized"):
        provider.acquire_range(draft)
    client.timeseries.get_range.assert_not_called()


def test_paid_provider_error_classifies_uncertain_completion() -> None:
    class ServerError(Exception):
        http_status = 503

    error = _classify_provider_error(ServerError(), after_submission=True)

    assert isinstance(error, PaidProviderError)
    assert error.category == "provider_server_error"
    assert error.uncertain_completion is True
