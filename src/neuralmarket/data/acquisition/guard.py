"""Metadata-only download guard for acquisition planning.

Wraps a Databento client so acquisition-planning code can reach only the three
metadata estimation methods (``get_record_count``, ``get_billable_size``,
``get_cost``). Any attempt to reach a download-capable namespace or method —
``timeseries``, ``batch``, ``live``, ``get_range``, ``get_range_async``,
``submit_job``, ``download`` — raises :class:`AcquisitionNotAuthorizedError`.
This milestone permits metadata planning only.
"""

from __future__ import annotations

from typing import Any

from neuralmarket.data.errors import AcquisitionNotAuthorizedError

_FORBIDDEN_NAMESPACES = frozenset({"timeseries", "batch", "live"})
_FORBIDDEN_METHODS = frozenset(
    {"get_range", "get_range_async", "submit_job", "download", "download_async"}
)
_ALLOWED_METADATA_METHODS = frozenset({"get_record_count", "get_billable_size", "get_cost"})


class _GuardedMetadata:
    """Expose only the metadata estimation methods used for cost planning."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        if name not in _ALLOWED_METADATA_METHODS:
            raise AcquisitionNotAuthorizedError(
                f"Metadata method '{name}' is not permitted during acquisition "
                "planning; this milestone permits metadata planning only."
            )
        return getattr(self._inner, name)


class AcquisitionGuardedClient:
    """Wrap a provider client, exposing only metadata estimation methods."""

    def __init__(self, inner: Any) -> None:
        """Store the wrapped provider client."""
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access, blocking every download-capable surface."""
        if name in _FORBIDDEN_NAMESPACES or name in _FORBIDDEN_METHODS:
            raise AcquisitionNotAuthorizedError(
                f"Access to '{name}' is prohibited: this milestone permits "
                "metadata planning only, not data acquisition."
            )
        attr = getattr(self._inner, name)
        if name == "metadata":
            return _GuardedMetadata(attr)
        return attr
