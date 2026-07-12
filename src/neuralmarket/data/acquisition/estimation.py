"""Metadata-only cost/size/count estimation adapter for acquisition planning.

Every estimate is produced from Databento's ``get_record_count``,
``get_billable_size``, and ``get_cost`` metadata endpoints only. No time-series,
batch, or live data is ever requested. Transient provider failures (5xx, rate
limiting, network errors) are retried with backoff; authentication,
entitlement, schema, and symbol failures are not retried.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from neuralmarket.data.acquisition.guard import AcquisitionGuardedClient
from neuralmarket.data.errors import (
    AcquisitionNotAuthorizedError,
    AuthenticationError,
    CostEstimationError,
    DatasetUnavailableError,
    EntitlementError,
    MarketDataError,
    ProviderNetworkError,
    RateLimitError,
    SchemaUnavailableError,
    SymbolResolutionError,
)
from neuralmarket.data.redaction import redact

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 2.0


@dataclass(frozen=True)
class MetadataEstimate:
    """A single account-neutral metadata-only cost/size/count estimate."""

    dataset: str
    schema: str
    symbol: str
    stype_in: str
    window_start: datetime
    window_end: datetime
    record_count: int
    billable_size_bytes: int
    cost_usd: Decimal
    retries: int


def _http_status(exc: Exception) -> int | None:
    status = getattr(exc, "http_status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _translate(exc: Exception) -> MarketDataError:
    """Translate a vendor exception into a redacted domain error."""
    message = redact(str(exc)).lower()
    status = _http_status(exc)
    if status == 401 or any(
        token in message for token in ("api key", "unauthor", "401", "invalid credential")
    ):
        return AuthenticationError("Provider rejected the credential.")
    if status == 403 or any(
        token in message for token in ("entitl", "403", "not permitted", "forbidden")
    ):
        return EntitlementError("Account is not entitled for the requested dataset or schema.")
    if "schema" in message:
        return SchemaUnavailableError("Requested schema is unavailable.")
    if any(token in message for token in ("symbol", "resolve", "not found")):
        return SymbolResolutionError("Symbol could not be resolved.")
    if "dataset" in message:
        return DatasetUnavailableError("Requested dataset is unavailable.")
    if status == 429 or any(token in message for token in ("rate limit", "429", "too many")):
        return RateLimitError("Provider rate limit reached.")
    if any(token in message for token in ("network", "connection", "timeout", "temporarily")):
        return ProviderNetworkError("Network failure contacting provider.")
    if status is not None and 500 <= status < 600:
        return ProviderNetworkError("Provider server error.")
    return CostEstimationError("Provider metadata estimation request failed.")


def _is_transient(exc: Exception, domain: MarketDataError) -> bool:
    if isinstance(domain, ProviderNetworkError | RateLimitError):
        return True
    status = _http_status(exc)
    return status is not None and 500 <= status < 600


def _nonneg_int(value: Any, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise MarketDataError(f"Malformed {label} estimate: {value!r}") from exc
    if parsed < 0:
        raise MarketDataError(f"Malformed {label} estimate: negative value {parsed}")
    return parsed


def _nonneg_decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise MarketDataError(f"Malformed {label} estimate: {value!r}")
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise MarketDataError(f"Malformed {label} estimate: {value!r}") from exc
    if parsed < 0:
        raise MarketDataError(f"Malformed {label} estimate: negative value {parsed}")
    return parsed


class MetadataEstimator:
    """Adapter producing typed :class:`MetadataEstimate` results, metadata-only."""

    def __init__(self, client: Any) -> None:
        """Wrap an already-constructed provider client in the acquisition guard."""
        self._client = AcquisitionGuardedClient(client)
        self.metadata_call_count = 0
        self.retry_count = 0

    def estimate(
        self,
        *,
        dataset: str,
        schema: str,
        symbol: str,
        stype_in: str,
        start: datetime,
        end: datetime,
    ) -> MetadataEstimate:
        """Estimate record count, billable size, and cost for one request window."""
        for attempt in range(_MAX_ATTEMPTS):
            try:
                self.metadata_call_count += 1
                raw_count = self._client.metadata.get_record_count(
                    dataset=dataset,
                    symbols=[symbol],
                    schema=schema,
                    stype_in=stype_in,
                    start=start.isoformat(),
                    end=end.isoformat(),
                )
                raw_size = self._client.metadata.get_billable_size(
                    dataset=dataset,
                    symbols=[symbol],
                    schema=schema,
                    stype_in=stype_in,
                    start=start.isoformat(),
                    end=end.isoformat(),
                )
                raw_cost = self._client.metadata.get_cost(
                    dataset=dataset,
                    symbols=[symbol],
                    schema=schema,
                    stype_in=stype_in,
                    start=start.isoformat(),
                    end=end.isoformat(),
                )
            except AcquisitionNotAuthorizedError:
                raise
            except Exception as exc:
                domain = _translate(exc)
                if _is_transient(exc, domain) and attempt < _MAX_ATTEMPTS - 1:
                    self.retry_count += 1
                    time.sleep(_BACKOFF_SECONDS * (attempt + 1))
                    continue
                raise domain from exc
            return MetadataEstimate(
                dataset=dataset,
                schema=schema,
                symbol=symbol,
                stype_in=stype_in,
                window_start=start,
                window_end=end,
                record_count=_nonneg_int(raw_count, "record_count"),
                billable_size_bytes=_nonneg_int(raw_size, "billable_size"),
                cost_usd=_nonneg_decimal(raw_cost, "cost"),
                retries=attempt,
            )
        raise CostEstimationError("Metadata estimation retry attempts were exhausted.")
