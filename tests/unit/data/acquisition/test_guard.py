from typing import Any

import pytest

from neuralmarket.data.acquisition.guard import AcquisitionGuardedClient
from neuralmarket.data.errors import AcquisitionNotAuthorizedError


class _Metadata:
    def get_record_count(self, **kwargs: Any) -> int:
        return 1

    def get_billable_size(self, **kwargs: Any) -> int:
        return 1

    def get_cost(self, **kwargs: Any) -> float:
        return 0.01

    def list_schemas(self, **kwargs: Any) -> list[str]:
        return ["definition"]


class _Client:
    def __init__(self) -> None:
        self.metadata = _Metadata()
        self.symbology = object()
        self.timeseries = object()
        self.batch = object()
        self.live = object()
        self.get_range = lambda **_: None
        self.submit_job = lambda **_: None
        self.download = lambda **_: None


@pytest.mark.unit
@pytest.mark.parametrize("namespace", ["timeseries", "batch", "live"])
def test_forbidden_namespace_raises(namespace: str) -> None:
    guarded = AcquisitionGuardedClient(_Client())
    with pytest.raises(AcquisitionNotAuthorizedError):
        getattr(guarded, namespace)


@pytest.mark.unit
@pytest.mark.parametrize(
    "method", ["get_range", "get_range_async", "submit_job", "download", "download_async"]
)
def test_forbidden_method_raises(method: str) -> None:
    guarded = AcquisitionGuardedClient(_Client())
    with pytest.raises(AcquisitionNotAuthorizedError):
        getattr(guarded, method)


@pytest.mark.unit
def test_allowed_metadata_methods_pass_through() -> None:
    guarded = AcquisitionGuardedClient(_Client())
    assert guarded.metadata.get_record_count() == 1
    assert guarded.metadata.get_billable_size() == 1
    assert guarded.metadata.get_cost() == 0.01


@pytest.mark.unit
def test_disallowed_metadata_method_raises() -> None:
    guarded = AcquisitionGuardedClient(_Client())
    with pytest.raises(AcquisitionNotAuthorizedError):
        guarded.metadata.list_schemas()


@pytest.mark.unit
def test_other_attributes_pass_through() -> None:
    guarded = AcquisitionGuardedClient(_Client())
    assert guarded.symbology is not None
