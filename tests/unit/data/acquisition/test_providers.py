from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.providers import (
    DatabentoMetadataProvider,
    DatabentoPaidHistoricalProvider,
    PaidProviderError,
    _classify_provider_error,
    create_databento_paid_provider,
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
        validator=lambda _path, _checksum, _request: True,
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
        validator=lambda _path, _checksum, _request: True,
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


def test_metadata_facade_never_accesses_paid_namespaces() -> None:
    class Metadata:
        def get_record_count(self, **kwargs: object) -> int:
            return 1

        def get_billable_size(self, **kwargs: object) -> int:
            return 2

        def get_cost(self, **kwargs: object) -> str:
            return "0.01"

    class HostileRoot:
        metadata = Metadata()

        @property
        def timeseries(self) -> object:
            raise AssertionError("timeseries namespace accessed")

        @property
        def batch(self) -> object:
            raise AssertionError("batch namespace accessed")

        @property
        def live(self) -> object:
            raise AssertionError("live namespace accessed")

    provider = DatabentoMetadataProvider(HostileRoot())
    assert provider.get_record_count() == 1
    assert provider.get_billable_size() == 2
    assert provider.get_cost() == "0.01"


def test_paid_factory_constructs_without_namespace_or_network_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    import databento

    calls: list[str] = []

    class HostileRoot:
        def __init__(self, key: str) -> None:
            assert key
            calls.append("constructed")

        @property
        def timeseries(self):
            raise AssertionError("timeseries accessed during construction")

        @property
        def batch(self):
            raise AssertionError("batch accessed during construction")

        @property
        def live(self):
            raise AssertionError("live accessed during construction")

    monkeypatch.setattr(databento, "Historical", HostileRoot)
    provider = create_databento_paid_provider(data_root=tmp_path, api_key="test-key")

    assert isinstance(provider, DatabentoPaidHistoricalProvider)
    assert calls == ["constructed"]
