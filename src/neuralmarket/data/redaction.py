"""Credential redaction and structured JSON secret classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

_REDACTED = "[REDACTED]"

# Representative secret formats: Databento keys (db-...), bearer tokens, generic
# long high-entropy tokens, and explicit KEY=value assignments.
_ASSIGNMENT = re.compile(r"(?i)\b(DATABENTO_API_KEY|api[_-]?key|token|secret)\b(\s*[=:]\s*)\S+")
_SUBSTITUTIONS: tuple[re.Pattern[str], ...] = (
    re.compile(r"db-[A-Za-z0-9]{6,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"\b[A-Za-z0-9]{32,}\b"),
)
_HEX_FIELDS = {
    "repository_head": (40, "repository commit"),
    "checkpoint_sha256": (64, "checkpoint SHA-256"),
    "plan_sha256": (64, "plan SHA-256"),
    "plan_hash": (64, "plan SHA-256"),
    "request_manifest_sha256": (64, "request-manifest SHA-256"),
    "request_specification_sha256": (64, "request-specification SHA-256"),
    "provider_response_sha256": (64, "provider-response SHA-256"),
    "evidence_sha256": (64, "evidence SHA-256"),
    "source_evidence_sha256": (64, "source-evidence SHA-256"),
    "artifact_sha256": (64, "artifact SHA-256"),
    "request_id": (16, "request identifier"),
    "run_id": (32, "run identifier"),
}
_CREDENTIAL_FIELDS = frozenset({"api_key", "token", "authorization", "password", "secret"})
_HASH_LIKE = re.compile(r"(?:[0-9a-fA-F]{16}|[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


@dataclass(frozen=True)
class SecretCandidate:
    """Sanitized classification of one credential-like JSON value."""

    json_path: str
    candidate_length: int
    candidate_sha256: str
    classification: Literal["confirmed_nonsecret_identifier", "possible_secret", "confirmed_secret"]
    known_category: str | None


def classify_json_secret_candidates(payload: object) -> list[SecretCandidate]:
    """Classify hash-like JSON values by field semantics without exposing values."""
    found: list[tuple[str, str, str, bool, str | None]] = []

    def visit(value: object, path: tuple[str, ...]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, (*path, str(key)))
        elif isinstance(value, list | tuple):
            for index, child in enumerate(value):
                visit(child, (*path, str(index)))
        elif isinstance(value, str) and _HASH_LIKE.fullmatch(value):
            field = path[-1] if path else ""
            recognized = _HEX_FIELDS.get(field)
            safe = recognized is not None and len(value) == recognized[0] and value == value.lower()
            category = recognized[1] if recognized is not None and safe else None
            found.append((".".join(path), field, value, safe, category))

    visit(payload, ())
    blocked_values = {value for _, _, value, safe, _ in found if not safe}
    return [
        SecretCandidate(
            json_path=path,
            candidate_length=len(value),
            candidate_sha256=sha256(value.encode()).hexdigest(),
            classification=(
                "confirmed_secret"
                if field.casefold() in _CREDENTIAL_FIELDS
                else "possible_secret"
                if value in blocked_values
                else "confirmed_nonsecret_identifier"
            ),
            known_category=category if value not in blocked_values else None,
        )
        for path, field, value, _, category in found
    ]


def validate_no_unresolved_json_secrets(payload: object) -> None:
    """Fail closed when structured JSON contains an unresolved secret candidate."""
    if any(
        item.classification != "confirmed_nonsecret_identifier"
        for item in classify_json_secret_candidates(payload)
    ):
        raise ValueError("JSON contains unresolved possible secret candidates")


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
