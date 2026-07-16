"""Provider adapters for guarded pilot execution.

The adapter is deliberately the only module that knows the shape of the
Databento historical client.  It is never constructed by preparation,
verification, recovery, CI, or this milestone's blocked CLI execution path.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neuralmarket.data.acquisition.executor import PaidHistoricalProvider, RawAcquisitionResult
from neuralmarket.data.acquisition.requests import AcquisitionRequest, verify_final_request
from neuralmarket.data.acquisition.storage import atomic_store_raw


class DatabentoMetadataProvider:
    """Capability-restricted metadata facade around a Databento root client.

    The root client is deliberately discarded after its ``metadata`` namespace
    is captured.  Callers cannot reach time-series, batch, or live APIs from
    this object.
    """

    def __init__(self, client: Any) -> None:
        """Capture the metadata capability and discard the root client."""
        metadata = client.metadata
        for name in ("get_record_count", "get_billable_size", "get_cost"):
            if not callable(getattr(metadata, name, None)):
                raise TypeError(f"Databento metadata endpoint missing: {name}")
        self._metadata = metadata
        self._close = getattr(client, "close", None)

    def list_publishers(self, **kwargs: object) -> object:
        """Return the approved metadata publisher listing."""
        return self._metadata.list_publishers(**kwargs)

    def list_unit_prices(self, **kwargs: object) -> object:
        """Return the approved historical unit-price listing for a dataset."""
        return self._metadata.list_unit_prices(**kwargs)

    def list_schemas(self, **kwargs: object) -> object:
        """Return the dataset-specific schema listing (metadata-only)."""
        return self._metadata.list_schemas(**kwargs)

    def get_record_count(self, **kwargs: object) -> object:
        """Return a metadata-only record count."""
        return self._metadata.get_record_count(**kwargs)

    def get_billable_size(self, **kwargs: object) -> object:
        """Return a metadata-only billable-size estimate."""
        return self._metadata.get_billable_size(**kwargs)

    def get_cost(self, **kwargs: object) -> object:
        """Return a metadata-only cost estimate."""
        return self._metadata.get_cost(**kwargs)

    def close(self) -> None:
        """Close the discarded root client without exposing its namespaces."""
        if callable(self._close):
            self._close()


class PaidProviderError(RuntimeError):
    """Classified provider failure with an explicit billing-completion state."""

    def __init__(self, category: str, message: str, *, uncertain_completion: bool) -> None:
        """Initialize a classified provider failure."""
        super().__init__(message)
        self.category = category
        self.uncertain_completion = uncertain_completion


def _classify_provider_error(exc: Exception, *, after_submission: bool) -> PaidProviderError:
    status = getattr(exc, "http_status", None)
    try:
        status_code = int(status) if status is not None else None
    except (TypeError, ValueError):
        status_code = None
    if status_code == 400:
        category = "provider_rejected_request"
    elif status_code == 401:
        category = "provider_authentication_failure"
    elif status_code == 403:
        category = "provider_entitlement_failure"
    elif status_code == 408:
        category = "provider_timeout"
    elif status_code == 429:
        category = "provider_rate_limit"
    elif isinstance(exc, TimeoutError):
        category = "provider_timeout"
    elif isinstance(exc, ConnectionError | OSError):
        category = "provider_network_failure"
    else:
        category = "unknown_provider_failure"
    return PaidProviderError(
        category,
        "paid historical provider operation failed",
        uncertain_completion=after_submission,
    )


class DatabentoPaidHistoricalProvider(PaidHistoricalProvider):
    """Guarded adapter for one finalized historical range request."""

    def __init__(
        self,
        *,
        client: Any,
        data_root: Path,
        validator: Callable[[Path, str, AcquisitionRequest], bool],
        chunk_size: int = 1024 * 1024,
    ) -> None:
        """Initialize the injected client and safe storage seam."""
        self._client = client
        self._data_root = data_root
        self._validator = validator
        self._chunk_size = chunk_size

    def _chunks(self, path: Path) -> Iterable[bytes]:
        with path.open("rb") as handle:
            while chunk := handle.read(self._chunk_size):
                yield chunk

    @staticmethod
    def _validate_store(store: object) -> None:
        for name in ("to_file", "to_df"):
            if not callable(getattr(store, name, None)):
                raise PaidProviderError(
                    "unexpected_provider_response",
                    "paid historical provider returned an unsupported response object",
                    uncertain_completion=True,
                )

    def acquire_range(self, request: AcquisitionRequest) -> RawAcquisitionResult:
        """Fetch and atomically persist one finalized request."""
        verify_final_request(request)
        try:
            store = self._client.timeseries.get_range(
                dataset=request.dataset,
                start=request.start,
                end=request.end_exclusive,
                symbols=list(request.symbols),
                schema=request.schema_name,
                stype_in=request.stype_in,
                stype_out=request.stype_out,
            )
        except Exception as exc:
            # Invocation itself may be billable.  Without an explicit provider
            # acknowledgement that nothing was delivered, fail closed.
            raise _classify_provider_error(exc, after_submission=True) from exc
        self._validate_store(store)

        self._data_root.mkdir(parents=True, exist_ok=True)
        fd, export_name = tempfile.mkstemp(
            prefix=f"{request.request_id}.",
            suffix=".provider.partial",
            dir=self._data_root,
        )
        os.close(fd)
        export_path = Path(export_name)
        try:
            try:
                store.to_file(export_path)
                record_count = len(store.to_df())
            except PaidProviderError:
                raise
            except Exception as exc:
                raise PaidProviderError(
                    "unexpected_provider_response",
                    "paid historical provider response could not be serialized",
                    uncertain_completion=True,
                ) from exc
            try:
                stored = atomic_store_raw(
                    request=request,
                    data_root=self._data_root,
                    chunks=self._chunks(export_path),
                    validator=lambda path, checksum: self._validator(path, checksum, request),
                )
            except Exception as exc:
                raise PaidProviderError(
                    "local_persistence_failure",
                    "paid historical provider response could not be persisted locally",
                    uncertain_completion=True,
                ) from exc
        finally:
            export_path.unlink(missing_ok=True)

        return RawAcquisitionResult(
            request_id=request.request_id,
            raw_path=str(stored.path),
            sha256=stored.sha256,
            record_count=record_count,
        )


@dataclass(frozen=True)
class PaidProviderReadiness:
    """Non-network readiness evidence checked before authorization reservation."""

    ready: bool
    dependency_installed: bool
    api_key_configured: bool
    adapter_importable: bool
    acquire_method_present: bool


def paid_provider_readiness() -> PaidProviderReadiness:
    """Check production wiring without constructing a client or touching the network."""
    import importlib.util

    dependency = importlib.util.find_spec("databento") is not None
    key = bool(os.environ.get("DATABENTO_API_KEY"))
    method = callable(getattr(DatabentoPaidHistoricalProvider, "acquire_range", None))
    return PaidProviderReadiness(
        ready=dependency and key and method,
        dependency_installed=dependency,
        api_key_configured=key,
        adapter_importable=True,
        acquire_method_present=method,
    )


def create_databento_paid_provider(
    *,
    data_root: Path,
    api_key: str | None = None,
) -> DatabentoPaidHistoricalProvider:
    """Construct the paid adapter without invoking or inspecting paid namespaces."""
    import databento

    from neuralmarket.data.raw.dbn import validate_dbn_file

    key = api_key or os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY is not configured")
    client = databento.Historical(key)

    def validate(path: Path, checksum: str, request: AcquisitionRequest) -> bool:
        return validate_dbn_file(
            path,
            expected_request=request,
            expected_sha256=checksum,
            dbn_store_factory=lambda item: databento.DBNStore.from_file(item),
        ).passed

    return DatabentoPaidHistoricalProvider(client=client, data_root=data_root, validator=validate)
