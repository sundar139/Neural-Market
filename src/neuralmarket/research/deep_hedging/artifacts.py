"""Artifact and completeness contract — v3 Section 8.

Future paths:
  synthetic: data/processed/research/hedging_synthetic/<run_prefix>_<member>/synthetic_episodes_v1.parquet
             + synthetic_manifest_v1.json
  policy:    data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<seed>/checkpoint.pt
             + training_report.json etc.

Completeness:
  expected 45, per generator/cost 3/3 required, 2/3 invalid, replacement NONE
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


SYNTHETIC_SEEDS: dict[str, int] = {
    "seed-01": 42001,
    "seed-02": 42002,
    "seed-04": 42004,
    "seed-05": 42005,
    "reserve-j01": 42006,
}

RUN_PREFIXES: dict[str, str] = {
    "seed-01": "5bdbaabd2fb257a7",
    "seed-02": "62c7406cb3a2c642",
    "seed-04": "77e7de9efabb7ce3",
    "seed-05": "1e8aa171993a1aba",
    "reserve-j01": "38c5113b27568e14",
}

COST_BPS: dict[float, int] = {0.0: 0, 0.0010: 10, 0.0050: 50}
COST_LEVELS: list[float] = [0.0, 0.0010, 0.0050]
HEDGER_SEEDS: list[int] = [31001, 31002, 31003]
MEMBERS: list[str] = ["seed-01", "seed-02", "seed-04", "seed-05", "reserve-j01"]
EXPECTED_POLICIES: int = 45


def synthetic_dataset_path(run_prefix: str, member: str) -> Path:
    """Future synthetic dataset path per v3 Section 6.4."""
    return Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_episodes_v1.parquet")


def synthetic_manifest_path(run_prefix: str, member: str) -> Path:
    """Future synthetic manifest path."""
    return Path(f"data/processed/research/hedging_synthetic/{run_prefix}_{member}/synthetic_manifest_v1.json")


def policy_checkpoint_path(run_prefix: str, member: str, cost: float, hedger_seed: int) -> Path:
    """Future policy checkpoint path per v3 Section 8.1."""
    bps = COST_BPS[cost]
    return Path(f"data/processed/research/hedging_policies/{run_prefix}_{member}/c_{bps}/h_{hedger_seed}/checkpoint.pt")


def policy_dir(run_prefix: str, member: str, cost: float, hedger_seed: int) -> Path:
    """Future policy directory."""
    return policy_checkpoint_path(run_prefix, member, cost, hedger_seed).parent


def completeness_check(
    valid_policies: dict[tuple[str, float], int],
) -> dict[tuple[str, float], Literal["VALID", "INVALID"]]:
    """Check per-generator/cost completeness 3/3.

    Args:
        valid_policies: mapping (member, cost) -> valid count (0..3)

    Returns:
        mapping (member, cost) -> VALID if 3/3 else INVALID
        No shrink to 2/3. Replacement NONE.
    """
    result: dict[tuple[str, float], Literal["VALID", "INVALID"]] = {}
    for member in MEMBERS:
        for cost in COST_LEVELS:
            key = (member, cost)
            count = valid_policies.get(key, 0)
            result[key] = "VALID" if count == 3 else "INVALID"
    return result


def overall_validity(stati: dict[tuple[str, float], Literal["VALID", "INVALID"]]) -> Literal["VALID", "INVALID"]:
    """Cost-level primary validity requires all 5 members VALID at that cost.

    Global failure >20% (10+ of 45) also blocks, but this helper reports
    per-cost-level validity.
    """
    for cost in COST_LEVELS:
        for member in MEMBERS:
            if stati[(member, cost)] != "VALID":
                return "INVALID"
    return "VALID"


def global_failure_check(total_valid: int) -> bool:
    """Global failure if >20% of 45 fail (10+ invalid)."""
    return (EXPECTED_POLICIES - total_valid) >= 10


def sha256_bytes(data: bytes) -> str:
    """SHA-256 hex of bytes for checkpoint/manifest reporting."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """SHA-256 hex of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
