"""Provider adapters for guarded pilot execution.

The adapter is deliberately the only module that knows the shape of the
Databento historical client.  It is never constructed by preparation,
verification, recovery, CI, or this milestone's blocked CLI execution path.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterable
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
    if status_code == 401:
        category = "authentication"
    elif status_code == 403:
        category = "entitlement"
    elif status_code == 429:
        category = "rate_limit"
    elif status_code is not None and 500 <= status_code < 600:
        category = "provider_server_error"
    elif isinstance(exc, TimeoutError | ConnectionError | OSError):
        category = "network"
    else:
        category = "provider_error"
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
        validator: Callable[[Path, str], bool],
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
                encoding="dbn",
            )
        except Exception as exc:
            # Invocation itself may be billable.  Without an explicit provider
            # acknowledgement that nothing was delivered, fail closed.
            raise _classify_provider_error(exc, after_submission=True) from exc

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
            except Exception as exc:
                raise _classify_provider_error(exc, after_submission=True) from exc
            stored = atomic_store_raw(
                request=request,
                data_root=self._data_root,
                chunks=self._chunks(export_path),
                validator=self._validator,
            )
        finally:
            export_path.unlink(missing_ok=True)

        return RawAcquisitionResult(
            request_id=request.request_id,
            raw_path=str(stored.path),
            sha256=stored.sha256,
            record_count=record_count,
        )


def validate_paid_adapter_factory(factory: Callable[[], DatabentoPaidHistoricalProvider]) -> None:
    """Check an injected adapter factory without invoking any provider method."""
    adapter = factory()
    if not isinstance(adapter, DatabentoPaidHistoricalProvider):
        raise TypeError("paid adapter factory must return DatabentoPaidHistoricalProvider")
    if not callable(getattr(adapter, "acquire_range", None)):
        raise TypeError("paid adapter must expose acquire_range")
