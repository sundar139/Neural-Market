"""Fail-closed training runner and authorization boundary — v3.

Default: DRY RUN / PREFLIGHT ONLY. Scientific execution requires BOTH
--execute and tracked committed authorization. Supports distinct future
governed actions: synthetic generation for one member, training one policy.
Dry run enumerates 5 generation + 45 training jobs without model execution.
"""


from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from neuralmarket.core.device import resolve_device
from neuralmarket.core.runtime_identity import build_runtime_identity

EXPECTED_CONTRACT_V3_CANONICAL = "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01"
EXPECTED_CONTRACT_V3_BLOB = "eef7ad220db889166469799372759dfe1a96e35f"
EXPECTED_RUNTIME_IDENTITY = "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada"
CONTRACT_V3_PATH = Path("reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md")


class AuthorizationError(RuntimeError):
    """Raised when scientific execution is not authorized."""


class ArtifactExistsError(RuntimeError):
    """Raised when write-once artifact already exists (overwrite refused)."""


def _canonical_sha256(path: Path) -> str:
    """LF-canonical SHA-256 (matches Amendment 102 method)."""
    raw = path.read_bytes()
    canon = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(canon).hexdigest()


def _git_blob(path: Path) -> str:
    """Git blob hash via git hash-object."""
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _tracked_tree_clean() -> bool:
    """Check tracked tree clean (no modified tracked files)."""
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        capture_output=True,
        text=True,
        check=True,
    )
    # --untracked-files=no suppresses untracked; empty means clean
    return result.stdout.strip() == ""


def _authorization_exists(path: Path) -> bool:
    """Check if a future authorization artifact exists and is tracked.

    Authorization must be a tracked committed file (git ls-files).
    For Task 202, no such authorization exists by design.
    """
    if not path.exists():
        return False
    # Check if tracked (git ls-files)
    result = subprocess.run(
        ["git", "ls-files", "--", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def preflight_checks(
    *,
    contract_path: Path = CONTRACT_V3_PATH,
    expected_canonical: str = EXPECTED_CONTRACT_V3_CANONICAL,
    expected_blob: str = EXPECTED_CONTRACT_V3_BLOB,
    expected_runtime: str = EXPECTED_RUNTIME_IDENTITY,
    requested_device: str = "cuda",
    require_clean_tree: bool = True,
) -> dict[str, str]:
    """Run fail-closed preflight checks (no scientific execution).

    Checks:
      - contract-v3 canonical SHA and blob
      - runtime identity (build_runtime_identity with requested/resolved cuda)
      - CUDA availability via resolve_device
      - tracked tree clean (if required)

    Returns dict with verified identities on success.

    Raises:
        AuthorizationError / RuntimeError / ValueError on failure.
    """
    # Contract identity
    if not contract_path.exists():
        raise FileNotFoundError(f"contract not found: {contract_path}")
    canon = _canonical_sha256(contract_path)
    if canon != expected_canonical:
        raise ValueError(f"contract canonical mismatch: got {canon} expected {expected_canonical}")
    blob = _git_blob(contract_path)
    if blob != expected_blob:
        raise ValueError(f"contract blob mismatch: got {blob} expected {expected_blob}")

    # CUDA fail-closed
    device = resolve_device(requested_device)  # raises RuntimeError if no CUDA
    # Verify runtime identity matches expected (fail-closed before any scientific execution)
    # Build identity with requested=cuda, resolved=str(device) (cuda:0 or cuda)
    payload = build_runtime_identity(requested_device=requested_device, resolved_device=str(device))
    got_runtime = str(payload.get("runtime_identity_sha256"))
    if got_runtime != expected_runtime:
        # If runtime mismatched, fail closed (do not proceed)
        raise RuntimeError(
            f"runtime identity mismatch: got {got_runtime} expected {expected_runtime} "
            f"(payload={payload})"
        )

    if require_clean_tree and not _tracked_tree_clean():
        raise RuntimeError("tracked tree not clean — refuse to start scientific execution")

    return {
        "contract_canonical": canon,
        "contract_blob": blob,
        "runtime_identity": got_runtime,
        "device": str(device),
    }


@dataclass(frozen=True)
class HedgingAuthorization:
    """Future authorization schema (not created in Task 202).

    This schema is frozen for future Task-202+ authorization.
    Task 202 does NOT create a real execution authorization.
    """

    schema_version: str = "hedging-execution-authorization-v1"
    contract_v3_canonical: str = EXPECTED_CONTRACT_V3_CANONICAL
    contract_v3_blob: str = EXPECTED_CONTRACT_V3_BLOB
    runtime_identity: str = EXPECTED_RUNTIME_IDENTITY
    # Additional fields (member, synthetic RNG, hedger seed, cost, NSDE checkpoint etc.)
    # are per-policy and tracked in per-policy training reports, not here.


def require_authorization_or_refuse(
    *,
    authorization_path: Path,
    execute_flag: bool,
) -> Literal["DRY_RUN", "REFUSED", "AUTHORIZED"]:
    """Authorization boundary for future scientific execution.

    Default is DRY RUN / PREFLIGHT ONLY.
    Scientific execution requires BOTH --execute and a tracked committed
    authorization artifact.

    Without authorization: REFUSE.

    Args:
        authorization_path: Path to future authorization JSON (tracked, committed).
        execute_flag: True if --execute passed, False otherwise.

    Returns:
        DRY_RUN if execute_flag is False,
        REFUSED if execute_flag True but no authorization,
        AUTHORIZED if both present.

    Raises:
        AuthorizationError if refused.
    """
    if not execute_flag:
        return "DRY_RUN"
    if not _authorization_exists(authorization_path):
        raise AuthorizationError(
            f"REFUSED: scientific execution requires --execute and a tracked committed "
            f"authorization artifact at {authorization_path} matching schema "
            f"{HedgingAuthorization.schema_version} (contract {EXPECTED_CONTRACT_V3_CANONICAL} "
            f"blob {EXPECTED_CONTRACT_V3_BLOB}, runtime {EXPECTED_RUNTIME_IDENTITY}). "
            f"No such authorization exists."
        )
    # Additional binding checks (contract SHA etc.) would be done here for real authorization
    return "AUTHORIZED"


def check_artifact_nonexistence(path: Path) -> None:
    """Write-once helper: refuse if artifact already exists.

    Args:
        path: Future artifact path (e.g., checkpoint.pt)

    Raises:
        ArtifactExistsError if path already exists (overwrite refused).
    """
    if path.exists():
        raise ArtifactExistsError(f"OVERWRITE_REFUSED: artifact already exists at {path} (write-once)")

# ---------------------------------------------------------------------------
# Campaign enumeration — 5 generation + 45 training jobs
# ---------------------------------------------------------------------------

from neuralmarket.research.deep_hedging.artifacts import (
    COST_LEVELS,
    HEDGER_SEEDS,
    MEMBERS,
    RUN_PREFIXES,
    SYNTHETIC_SEEDS,
)


def enumerate_generation_jobs() -> list[dict[str, str | int]]:
    """Enumerate exactly 5 synthetic generation jobs (one per member)."""
    jobs: list[dict[str, str | int]] = []
    for member in MEMBERS:
        jobs.append(
            {
                "action": "generate_synthetic",
                "member": member,
                "run_prefix": RUN_PREFIXES[member],
                "synthetic_seed": SYNTHETIC_SEEDS[member],
                "expected_dataset": f"data/processed/research/hedging_synthetic/{RUN_PREFIXES[member]}_{member}/synthetic_episodes_v1.parquet",
            }
        )
    assert len(jobs) == 5, f"expected 5 generation jobs, got {len(jobs)}"
    return jobs


def enumerate_training_jobs() -> list[dict[str, str | int | float]]:
    """Enumerate exactly 45 policy training jobs (5×3×3)."""
    jobs: list[dict[str, str | int | float]] = []
    for member in MEMBERS:
        for cost in COST_LEVELS:
            for seed in HEDGER_SEEDS:
                bps = {0.0: 0, 0.0010: 10, 0.0050: 50}[cost]
                jobs.append(
                    {
                        "action": "train_policy",
                        "member": member,
                        "run_prefix": RUN_PREFIXES[member],
                        "cost": cost,
                        "cost_bps": bps,
                        "hedger_seed": seed,
                        "synthetic_seed": SYNTHETIC_SEEDS[member],
                        "expected_checkpoint": f"data/processed/research/hedging_policies/{RUN_PREFIXES[member]}_{member}/c_{bps}/h_{seed}/checkpoint.pt",
                    }
                )
    assert len(jobs) == 45, f"expected 45 training jobs, got {len(jobs)}"
    assert len(MEMBERS) * len(COST_LEVELS) * len(HEDGER_SEEDS) == 45
    return jobs


def dry_run() -> dict[str, list[dict]]:
    """Dry run must enumerate expected work without scientific model execution."""
    return {
        "generation_jobs": enumerate_generation_jobs(),
        "training_jobs": enumerate_training_jobs(),
        "total_generation": 5,
        "total_training": 45,
    }


# ---------------------------------------------------------------------------
# Extended authorization schema for distinct future governed actions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HedgingExecutionAuthorization:
    """Extended authorization for future governed actions (generation/training).

    Scientific execution must require --execute plus tracked committed
    authorization binding at least: Task ID, contract-v3 canonical SHA/blob,
    implementation Git commit, runtime identity, member allowlist, checkpoint
    identities, synthetic RNG, hedger seed allowlist, cost allowlist, maximum
    generation/training invocations, artifact roots, network false,
    final-test access false.

    This schema is frozen for future Task-202+ authorization; Task 203 does
    NOT create a real execution authorization.
    """

    schema_version: str = "hedging-execution-authorization-v1"
    task_id: str = "NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-202"
    contract_v3_canonical: str = EXPECTED_CONTRACT_V3_CANONICAL
    contract_v3_blob: str = EXPECTED_CONTRACT_V3_BLOB
    implementation_commit: str = ""  # filled at authorization creation via git rev-parse HEAD
    runtime_identity: str = EXPECTED_RUNTIME_IDENTITY
    member_allowlist: tuple[str, ...] = tuple(MEMBERS)
    checkpoint_identities: dict[str, str] | None = None  # member -> checkpoint SHA
    synthetic_rng: dict[str, int] | None = None  # member -> seed 42001 etc.
    hedger_seed_allowlist: tuple[int, ...] = tuple(HEDGER_SEEDS)
    cost_allowlist: tuple[float, ...] = tuple(COST_LEVELS)
    max_generation_invocations: int = 5
    max_training_invocations: int = 45
    artifact_roots: tuple[str, ...] = (
        "data/processed/research/hedging_synthetic",
        "data/processed/research/hedging_policies",
    )
    network: bool = False
    final_test_access: bool = False


def validate_authorization_schema(payload: dict) -> None:
    """Validate extended authorization payload binds all required fields.

    Raises AuthorizationError if any binding missing or mismatched.
    """
    required = [
        "schema_version",
        "task_id",
        "contract_v3_canonical",
        "contract_v3_blob",
        "implementation_commit",
        "runtime_identity",
        "member_allowlist",
        "hedger_seed_allowlist",
        "cost_allowlist",
        "max_generation_invocations",
        "max_training_invocations",
        "artifact_roots",
        "network",
        "final_test_access",
    ]
    for field in required:
        if field not in payload:
            raise AuthorizationError(f"authorization missing required field: {field}")
    if payload.get("contract_v3_canonical") != EXPECTED_CONTRACT_V3_CANONICAL:
        raise AuthorizationError("authorization contract canonical mismatch")
    if payload.get("contract_v3_blob") != EXPECTED_CONTRACT_V3_BLOB:
        raise AuthorizationError("authorization contract blob mismatch")
    if payload.get("runtime_identity") != EXPECTED_RUNTIME_IDENTITY:
        raise AuthorizationError("authorization runtime mismatch")
    if payload.get("network") is not False:
        raise AuthorizationError("authorization network must be false")
    if payload.get("final_test_access") is not False:
        raise AuthorizationError("authorization final_test_access must be false")
    if int(payload.get("max_generation_invocations", 0)) != 5:
        raise AuthorizationError("max_generation_invocations must be 5")
    if int(payload.get("max_training_invocations", 0)) != 45:
        raise AuthorizationError("max_training_invocations must be 45")
    # Allowlist sanity: must be subset of frozen allowlists
    members = payload.get("member_allowlist", [])
    if not set(members).issubset(set(MEMBERS)):
        raise AuthorizationError(f"member allowlist contains non-governed member: {members}")
    costs = payload.get("cost_allowlist", [])
    if not set(costs).issubset(set(COST_LEVELS)):
        raise AuthorizationError(f"cost allowlist contains non-governed cost: {costs}")
    seeds = payload.get("hedger_seed_allowlist", [])
    if not set(seeds).issubset(set(HEDGER_SEEDS)):
        raise AuthorizationError(f"hedger seed allowlist contains non-governed seed: {seeds}")
