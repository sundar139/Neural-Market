"""Metadata-only cost/size/count estimation adapter for acquisition planning.

Every estimate is produced from Databento's ``get_record_count``,
``get_billable_size``, and ``get_cost`` metadata endpoints only. No time-series,
batch, or live data is ever requested. Transient provider failures (5xx, rate
limiting, network errors) are retried with backoff; authentication,
entitlement, schema, and symbol failures are not retried.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock
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
_logger = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class MetadataCallRecord:
    """Safe timing evidence for one metadata endpoint invocation."""

    operation_id: str
    request_id: str
    dataset: str
    schema: str
    request_start: str
    request_end: str
    started_at: str
    completed_at: str
    elapsed_seconds: float
    attempt: int
    operation: str
    retry_category: str


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
    if status is not None and 500 <= status < 600:
        return ProviderNetworkError("Provider server error.")
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
    if not parsed.is_finite():
        raise MarketDataError(f"Malformed {label} estimate: nonfinite value {parsed}")
    if parsed < 0:
        raise MarketDataError(f"Malformed {label} estimate: negative value {parsed}")
    return parsed


class MetadataEstimator:
    """Adapter producing typed :class:`MetadataEstimate` results, metadata-only."""

    def __init__(
        self,
        client: Any,
        *,
        maximum_attempts: int = _MAX_ATTEMPTS,
        initial_delay_seconds: float = _BACKOFF_SECONDS,
        multiplier: float = 2.0,
        maximum_delay_seconds: float = 10.0,
        deterministic_jitter: bool = True,
    ) -> None:
        """Wrap an already-constructed provider client in the acquisition guard."""
        guarded = AcquisitionGuardedClient(client)
        self._metadata = (
            client
            if all(
                callable(getattr(client, name, None))
                for name in ("get_record_count", "get_billable_size", "get_cost")
            )
            else guarded.metadata
        )
        self._maximum_attempts = maximum_attempts
        self._initial_delay_seconds = initial_delay_seconds
        self._multiplier = multiplier
        self._maximum_delay_seconds = maximum_delay_seconds
        self._deterministic_jitter = deterministic_jitter
        self._counter_lock = Lock()
        self.metadata_call_count = 0
        self.endpoint_call_count = 0
        self.retry_count = 0
        self.call_records: list[MetadataCallRecord] = []

    def _delay(self, operation_id: str, attempt: int) -> float:
        delay = min(
            self._initial_delay_seconds * self._multiplier**attempt,
            self._maximum_delay_seconds,
        )
        if not self._deterministic_jitter:
            return delay
        digest = hashlib.sha256(f"{operation_id}:{attempt}".encode()).digest()
        return delay * (0.75 + int.from_bytes(digest[:2], "big") / 65535 * 0.5)

    def _call(self, operation_id: str, name: str, attempt: int, **kwargs: object) -> object:
        started = time.monotonic()
        started_at = datetime.now(UTC).isoformat()
        request_id = operation_id
        dataset = str(kwargs.get("dataset", ""))
        schema = str(kwargs.get("schema", ""))
        request_start = str(kwargs.get("start", ""))
        request_end = str(kwargs.get("end", ""))
        _logger.info(
            "metadata_start_detail operation_id=%s request_id=%s dataset=%s schema=%s "
            "request_start=%s request_end=%s attempt=%d",
            operation_id,
            request_id,
            dataset,
            schema,
            request_start,
            request_end,
            attempt,
        )
        with self._counter_lock:
            self.endpoint_call_count += 1
        _logger.info(
            "metadata_start operation_id=%s operation=%s attempt=%d started_at=%s",
            operation_id,
            name,
            attempt,
            datetime.now().astimezone().isoformat(),
        )
        try:
            result = getattr(self._metadata, name)(**kwargs)
        except Exception:
            completed_at = datetime.now(UTC).isoformat()
            elapsed = time.monotonic() - started
            self.call_records.append(
                MetadataCallRecord(
                    operation_id,
                    operation_id,
                    dataset,
                    schema,
                    request_start,
                    request_end,
                    started_at,
                    completed_at,
                    elapsed,
                    attempt,
                    name,
                    "provider_error",
                )
            )
            _logger.warning(
                "metadata_complete operation_id=%s operation=%s attempt=%d status=error "
                "completed_at=%s elapsed_seconds=%.3f",
                operation_id,
                name,
                attempt,
                datetime.now().astimezone().isoformat(),
                time.monotonic() - started,
            )
            raise
        else:
            completed_at = datetime.now(UTC).isoformat()
            elapsed = time.monotonic() - started
            self.call_records.append(
                MetadataCallRecord(
                    operation_id,
                    operation_id,
                    dataset,
                    schema,
                    request_start,
                    request_end,
                    started_at,
                    completed_at,
                    elapsed,
                    attempt,
                    name,
                    "none",
                )
            )
            _logger.info(
                "metadata_complete operation_id=%s operation=%s attempt=%d status=ok "
                "completed_at=%s elapsed_seconds=%.3f",
                operation_id,
                name,
                attempt,
                datetime.now().astimezone().isoformat(),
                time.monotonic() - started,
            )
            return result

    def estimate(
        self,
        *,
        dataset: str,
        schema: str,
        symbol: str,
        stype_in: str,
        start: datetime,
        end: datetime,
        request_id: str | None = None,
    ) -> MetadataEstimate:
        """Estimate record count, billable size, and cost for one request window."""
        operation_id = request_id or f"{dataset}:{schema}:{start.isoformat()}"
        kwargs = {
            "dataset": dataset,
            "symbols": [symbol],
            "schema": schema,
            "stype_in": stype_in,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        for attempt in range(self._maximum_attempts):
            try:
                with self._counter_lock:
                    self.metadata_call_count += 1
                raw_count = self._call(operation_id, "get_record_count", attempt + 1, **kwargs)
                raw_size = self._call(operation_id, "get_billable_size", attempt + 1, **kwargs)
                raw_cost = self._call(operation_id, "get_cost", attempt + 1, **kwargs)
            except AcquisitionNotAuthorizedError:
                raise
            except Exception as exc:
                domain = _translate(exc)
                if _is_transient(exc, domain) and attempt < self._maximum_attempts - 1:
                    with self._counter_lock:
                        self.retry_count += 1
                    _logger.warning(
                        "metadata_retry operation_id=%s attempt=%d category=%s",
                        operation_id,
                        attempt + 1,
                        type(domain).__name__,
                    )
                    time.sleep(self._delay(operation_id, attempt))
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
