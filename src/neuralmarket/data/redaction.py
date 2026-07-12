"""Credential redaction for logs, reports, and exception messages."""

from __future__ import annotations

import re

_REDACTED = "[REDACTED]"

# Representative secret formats: Databento keys (db-...), bearer tokens, generic
# long high-entropy tokens, and explicit KEY=value assignments.
_ASSIGNMENT = re.compile(r"(?i)\b(DATABENTO_API_KEY|api[_-]?key|token|secret)\b(\s*[=:]\s*)\S+")
_SUBSTITUTIONS: tuple[re.Pattern[str], ...] = (
    re.compile(r"db-[A-Za-z0-9]{6,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"\b[A-Za-z0-9]{32,}\b"),
)


def redact(text: str) -> str:
    """Redact credential-like substrings from arbitrary text.

    Args:
        text: Text that may contain a credential.

    Returns:
        The text with credential-like substrings replaced by ``[REDACTED]``,
        preserving assignment key names (for example ``DATABENTO_API_KEY``).
    """
    redacted = _ASSIGNMENT.sub(rf"\1\2{_REDACTED}", text)
    for pattern in _SUBSTITUTIONS:
        redacted = pattern.sub(_REDACTED, redacted)
    return redacted
