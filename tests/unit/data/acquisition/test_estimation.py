from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from neuralmarket.data.acquisition.estimation import MetadataEstimator
from neuralmarket.data.errors import (
    AuthenticationError,
    EntitlementError,
    MarketDataError,
    ProviderNetworkError,
)

_START = datetime(2019, 1, 2, 20, 50, tzinfo=UTC)
_END = datetime(2019, 1, 2, 21, 0, tzinfo=UTC)


class _FakeError(Exception):
    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


class _Metadata:
    def __init__(
        self,
        count: Any = 100,
        size: Any = 1000,
        cost: Any = 0.01,
        fail_times: int = 0,
        error: Exception | None = None,
    ) -> None:
        self._count = count
        self._size = size
        self._cost = cost
        self._fail_times = fail_times
        self._error = error
        self.calls = 0

    def get_record_count(self, **kwargs: Any) -> Any:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise self._error or _FakeError(500, "internal error")
        return self._count

    def get_billable_size(self, **kwargs: Any) -> Any:
        return self._size

    def get_cost(self, **kwargs: Any) -> Any:
        return self._cost


class _Client:
    def __init__(self, **kwargs: Any) -> None:
        self.metadata = _Metadata(**kwargs)
        self.timeseries = object()
        self.batch = object()
        self.live = object()


@pytest.mark.unit
def test_successful_estimate() -> None:
    estimator = MetadataEstimator(_Client(count=100, size=1000, cost="0.05"))
    result = estimator.estimate(
        dataset="OPRA.PILLAR",
        schema="cbbo-1m",
        symbol="SPY.OPT",
        stype_in="parent",
        start=_START,
        end=_END,
    )
    assert result.record_count == 100
    assert result.billable_size_bytes == 1000
    assert result.cost_usd == Decimal("0.05")
    assert result.retries == 0
    assert estimator.metadata_call_count == 1


@pytest.mark.unit
def test_zero_cost_and_count_accepted() -> None:
    estimator = MetadataEstimator(_Client(count=0, size=0, cost=0))
    result = estimator.estimate(
        dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
    )
    assert result.record_count == 0
    assert result.cost_usd == Decimal(0)


@pytest.mark.unit
def test_negative_record_count_raises() -> None:
    estimator = MetadataEstimator(_Client(count=-5))
    with pytest.raises(MarketDataError, match="negative"):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )


@pytest.mark.unit
def test_negative_cost_raises() -> None:
    estimator = MetadataEstimator(_Client(cost=-1))
    with pytest.raises(MarketDataError, match="negative"):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )


@pytest.mark.unit
def test_malformed_cost_raises() -> None:
    estimator = MetadataEstimator(_Client(cost="not-a-number"))
    with pytest.raises(MarketDataError, match="Malformed"):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )


@pytest.mark.unit
def test_malformed_record_count_raises() -> None:
    estimator = MetadataEstimator(_Client(count="oops"))
    with pytest.raises(MarketDataError, match="Malformed"):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )


@pytest.mark.unit
def test_transient_5xx_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    import neuralmarket.data.acquisition.estimation as est

    monkeypatch.setattr(est.time, "sleep", lambda _seconds: None)
    estimator = MetadataEstimator(_Client(fail_times=2, error=_FakeError(500, "internal error")))
    result = estimator.estimate(
        dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
    )
    assert result.retries == 2


@pytest.mark.unit
def test_persistent_5xx_raises_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import neuralmarket.data.acquisition.estimation as est

    monkeypatch.setattr(est.time, "sleep", lambda _seconds: None)
    estimator = MetadataEstimator(_Client(fail_times=10, error=_FakeError(500, "internal error")))
    with pytest.raises(ProviderNetworkError):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )


@pytest.mark.unit
def test_authentication_error_is_not_retried() -> None:
    estimator = MetadataEstimator(_Client(fail_times=10, error=_FakeError(401, "invalid API key")))
    with pytest.raises(AuthenticationError):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )
    assert estimator.retry_count == 0


@pytest.mark.unit
def test_entitlement_error_is_not_retried() -> None:
    estimator = MetadataEstimator(_Client(fail_times=10, error=_FakeError(403, "not entitled")))
    with pytest.raises(EntitlementError):
        estimator.estimate(
            dataset="d", schema="s", symbol="x", stype_in="raw_symbol", start=_START, end=_END
        )
    assert estimator.retry_count == 0
