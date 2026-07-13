"""Shared execution-state machine for the acquisition pipeline.

Split out from ``journal.py`` and ``executor.py`` (Task 8) so both can import
the same transition table without a circular import.
"""

from __future__ import annotations

from typing import Literal

ExecutionState = Literal[
    "planned",
    "preflight_validated",
    "authorized",
    "requesting",
    "downloaded",
    "raw_validated",
    "normalized",
    "quality_validated",
    "failed",
    "quarantined",
]

ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("planned", "preflight_validated"),
        ("preflight_validated", "authorized"),
        ("authorized", "requesting"),
        ("requesting", "downloaded"),
        ("requesting", "failed"),
        ("downloaded", "raw_validated"),
        ("downloaded", "quarantined"),
        ("raw_validated", "normalized"),
        ("raw_validated", "quarantined"),
        ("normalized", "quality_validated"),
        ("normalized", "quarantined"),
    }
)
