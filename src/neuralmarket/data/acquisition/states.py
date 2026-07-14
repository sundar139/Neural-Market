"""Shared execution-state machine for the acquisition pipeline.

Split out from ``journal.py`` and ``executor.py`` (Task 8) so both can import
the same transition table without a circular import.
"""

from __future__ import annotations

from typing import Literal

ExecutionState = Literal[
    "not_started",
    "planned",
    "preflight_validated",
    "authorized",
    "request_started",
    "requesting",
    "response_received",
    "downloaded",
    "raw_persisting",
    "raw_validated",
    "normalized",
    "quality_validated",
    "uncertain_billing",
    "failed_safe",
    "failed",
    "quarantined",
]

ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("not_started", "planned"),
        ("planned", "preflight_validated"),
        ("preflight_validated", "authorized"),
        ("authorized", "requesting"),
        ("requesting", "downloaded"),
        ("requesting", "failed"),
        ("downloaded", "raw_validated"),
        ("downloaded", "quarantined"),
        ("preflight_validated", "request_started"),
        ("request_started", "response_received"),
        ("request_started", "uncertain_billing"),
        ("request_started", "failed_safe"),
        ("response_received", "raw_persisting"),
        ("response_received", "uncertain_billing"),
        ("raw_persisting", "raw_validated"),
        ("raw_persisting", "quarantined"),
        ("raw_validated", "normalized"),
        ("raw_validated", "quarantined"),
        ("normalized", "quality_validated"),
        ("normalized", "quarantined"),
    }
)
