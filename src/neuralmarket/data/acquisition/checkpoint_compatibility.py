"""Operational-vs-scientific configuration compatibility for checkpoint resume.

Changing an *operational* control (the metadata run deadline) alters the whole
pilot-config file hash, which would otherwise invalidate a checkpoint bound to
the prior hash. This module separates operational controls from the frozen
scientific/data/budget semantics: a checkpoint may resume across a config whose
only differences are in an explicit operational allowlist, and never across a
change to request definitions, budgets, or cost arithmetic.

Nothing here loosens age, integrity, plan, or billing checks; it governs the
configuration-hash comparison only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: Dotted config paths that are operational controls only. They may differ
#: between a checkpoint's bound config and the current config without blocking
#: resume, because they do not change request definitions, datasets, schemas,
#: windows, symbols, splits, budgets, or cost arithmetic.
OPERATIONAL_FIELD_ALLOWLIST: frozenset[str] = frozenset(
    {"metadata_execution.total_run_deadline_seconds"}
)

#: Prior pilot-config file hashes hand-verified (see research protocol amendment
#: 009) to differ from the current frozen config only in approved operational
#: fields. Auditable, explicit, and never a wildcard.
OPERATIONALLY_COMPATIBLE_PRIOR_CONFIG_HASHES: dict[str, str] = {
    "b490b3a11d89707d8a9ab6d154eb6c03ee5d312e247a9d936e1caca4d2621426": (
        "configs/data/acquisition/pilot_january_2019.yaml with "
        "total_run_deadline_seconds=540; frozen scientific plan, budgets, and cost "
        "policy identical to the current total_run_deadline_seconds=7200 config"
    ),
}

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def is_valid_sha256(value: str) -> bool:
    """Return whether ``value`` is exactly 64 lowercase hex characters."""
    return bool(_SHA256_RE.fullmatch(value))


@dataclass(frozen=True)
class ConfigCompatibilityReport:
    """Sanitized field-level compatibility outcome (no values, no secrets)."""

    compatible: bool
    differing_fields: tuple[str, ...]
    disallowed_fields: tuple[str, ...]


def _flatten(mapping: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in mapping.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def diff_config_compatibility(
    bound: Mapping[str, Any], current: Mapping[str, Any]
) -> ConfigCompatibilityReport:
    """Compare two configs; only operational-allowlist fields may differ.

    Returns the sanitized set of differing dotted paths and any that fall outside
    the operational allowlist. Field *names* only are reported, never values.
    """
    flat_bound, flat_current = _flatten(bound), _flatten(current)
    differing = sorted(
        key
        for key in set(flat_bound) | set(flat_current)
        if flat_bound.get(key) != flat_current.get(key)
    )
    disallowed = tuple(key for key in differing if key not in OPERATIONAL_FIELD_ALLOWLIST)
    return ConfigCompatibilityReport(
        compatible=not disallowed,
        differing_fields=tuple(differing),
        disallowed_fields=disallowed,
    )


def is_pilot_config_hash_compatible(stored_hash: str, current_hash: str) -> bool:
    """Accept an exact hash match or a hand-verified operationally-compatible prior hash."""
    if stored_hash == current_hash:
        return True
    return stored_hash in OPERATIONALLY_COMPATIBLE_PRIOR_CONFIG_HASHES
