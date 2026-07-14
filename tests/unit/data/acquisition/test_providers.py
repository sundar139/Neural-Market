from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
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


class _StrictTimeseries:
    _expected_keys: ClassVar[frozenset[str]] = frozenset(
        {
            "dataset",
            "start",
            "end",
            "symbols",
            "schema",
            "stype_in",
            "stype_out",
        }
    )

    def __init__(self, store: object | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._store = _FakeStore() if store is None else store

    def get_range(self, **kwargs: object) -> object:
        assert set(kwargs) == self._expected_keys
        assert kwargs["dataset"] == "ARCX.PILLAR"
        assert kwargs["schema"] == "definition"
        assert kwargs["symbols"] == ["SPY"]
        assert kwargs["stype_in"] == "raw_symbol"
        assert kwargs["stype_out"] == "instrument_id"
        assert kwargs["start"].isoformat() == "2019-01-02T00:00:00+00:00"
        assert kwargs["end"].isoformat() == "2019-02-01T00:00:00+00:00"
        self.calls.append(kwargs)
        return self._store


class _ForbiddenNamespace:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"forbidden namespace accessed: {name}")


class _StrictClient:
    def __init__(self, store: object | None = None) -> None:
        self.timeseries = _StrictTimeseries(store)
        self.batch = _ForbiddenNamespace()
        self.live = _ForbiddenNamespace()


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


def test_paid_adapter_uses_exact_first_request_databento_contract(tmp_path: Path) -> None:
    request = _finalized_request()
    client = _StrictClient()
    provider = DatabentoPaidHistoricalProvider(
        client=client,
        data_root=tmp_path,
        validator=lambda _path, _checksum, _request: True,
    )

    result = provider.acquire_range(request)

    assert result.request_id == "2750995e515e4f1a"
    assert result.record_count == 1
    assert len(client.timeseries.calls) == 1
    assert not list(tmp_path.glob("*.provider.partial"))


def test_paid_adapter_rejects_draft_before_client_call() -> None:
    config = load_pilot_config("configs/data/acquisition/pilot_january_2019.yaml")
    draft = build_pilot_request_plan(config)[0]
    client = SimpleNamespace(timeseries=SimpleNamespace(get_range=Mock()))
    provider = DatabentoPaidHistoricalProvider(
        client=client,
        data_root=Path("data"),
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
    assert error.category == "unknown_provider_failure"
    assert error.uncertain_completion is True


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (400, "provider_rejected_request"),
        (401, "provider_authentication_failure"),
        (403, "provider_entitlement_failure"),
        (408, "provider_timeout"),
        (429, "provider_rate_limit"),
        (503, "unknown_provider_failure"),
    ],
)
def test_paid_provider_error_classifies_http_statuses(status: int, category: str) -> None:
    class ProviderStatusError(Exception):
        http_status = status

    error = _classify_provider_error(ProviderStatusError(), after_submission=True)

    assert error.category == category
    assert error.uncertain_completion is True


@pytest.mark.parametrize(
    ("exc", "category"),
    [
        (TimeoutError("slow"), "provider_timeout"),
        (ConnectionError("down"), "provider_network_failure"),
        (OSError("socket"), "provider_network_failure"),
    ],
)
def test_paid_provider_error_classifies_local_exception_types(
    exc: Exception, category: str
) -> None:
    error = _classify_provider_error(exc, after_submission=True)

    assert error.category == category
    assert error.uncertain_completion is True


def test_paid_adapter_rejects_unexpected_store_shape_after_provider_response(
    tmp_path: Path,
) -> None:
    request = _finalized_request()
    client = _StrictClient(store=object())
    provider = DatabentoPaidHistoricalProvider(
        client=client,
        data_root=tmp_path,
        validator=lambda _path, _checksum, _request: True,
    )

    with pytest.raises(PaidProviderError) as error:
        provider.acquire_range(request)

    assert error.value.category == "unexpected_provider_response"
    assert error.value.uncertain_completion is True
    assert len(client.timeseries.calls) == 1


def test_paid_adapter_classifies_local_persistence_failure_after_response(tmp_path: Path) -> None:
    request = _finalized_request()
    client = _StrictClient()
    provider = DatabentoPaidHistoricalProvider(
        client=client,
        data_root=tmp_path,
        validator=lambda _path, _checksum, _request: False,
    )

    with pytest.raises(PaidProviderError) as error:
        provider.acquire_range(request)

    assert error.value.category == "local_persistence_failure"
    assert error.value.uncertain_completion is True
    assert len(client.timeseries.calls) == 1


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
