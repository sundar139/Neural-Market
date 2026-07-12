"""Provider symbology status normalization.

Databento reports a numeric symbology ``status`` alongside a human-readable
``message``. The numeric status is authoritative; the message is diagnostic text
only. Status codes are normalized into a typed enum with strict input handling so
that booleans, floats, empty strings, HTTP codes, and unknown values are rejected
rather than silently misread.

Acceptance depends on request context:

* raw-symbol resolution (for example ARCX/SPY) requires status ``0``;
* parent expansion (for example OPRA/SPY.OPT) permits status ``0`` or ``1``,
  because individual child contracts only span portions of a multi-day window, so
  the provider legitimately reports partial resolution while the selector remains
  valid;
* status ``2`` (not found) always fails.
"""

from __future__ import annotations

from enum import IntEnum


class SymbologyStatus(IntEnum):
    """Normalized provider symbology status."""

    OK = 0
    PARTIALLY_RESOLVED = 1
    NOT_FOUND = 2


def normalize_status(raw: object) -> SymbologyStatus:
    """Normalize a raw provider status value into a :class:`SymbologyStatus`.

    Accepts only the integers ``0``, ``1``, ``2`` and their exact decimal string
    forms ``"0"``, ``"1"``, ``"2"`` (surrounding whitespace allowed).

    Args:
        raw: The provider-supplied status value.

    Returns:
        The normalized status.

    Raises:
        ValueError: If the value is a boolean, a float, an empty or non-numeric
            string, an HTTP-style code such as ``200``, or any other unrecognized
            status. The authoritative numeric status must be unambiguous.
    """
    if isinstance(raw, bool):
        raise ValueError(f"boolean is not a valid symbology status: {raw!r}")
    if isinstance(raw, int):
        code = raw
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            raise ValueError("empty string is not a valid symbology status")
        try:
            code = int(stripped)
        except ValueError as exc:
            raise ValueError(f"non-numeric symbology status: {raw!r}") from exc
    else:
        raise ValueError(f"unsupported symbology status type: {type(raw).__name__}")
    try:
        return SymbologyStatus(code)
    except ValueError as exc:
        raise ValueError(f"unknown symbology status code: {code}") from exc


def status_acceptable(status: SymbologyStatus, *, parent_expansion: bool) -> bool:
    """Return whether a normalized status is acceptable for the request context.

    Args:
        status: The normalized status.
        parent_expansion: True for a one-to-many parent selector request, where
            partial resolution is expected; False for a single raw-symbol request.

    Returns:
        True when the status permits the request to proceed to coverage checks.
    """
    if status is SymbologyStatus.NOT_FOUND:
        return False
    if parent_expansion:
        return status in (SymbologyStatus.OK, SymbologyStatus.PARTIALLY_RESOLVED)
    return status is SymbologyStatus.OK
