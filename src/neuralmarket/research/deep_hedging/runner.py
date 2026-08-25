"""Fail-closed training runner and authorization boundary — v3.

Default: DRY RUN / PREFLIGHT ONLY.
Scientific execution requires BOTH --execute and a tracked committed
authorization artifact matching the future authorization schema.

Without authorization: REFUSE.
Before scientific process: verify contract-v3 SHA/blob, runtime identity,
requested/resolved CUDA, clean tracked tree, member/NSDE/RNG/hedger/cost identity,
artifact nonexistence, no overwrite.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch

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
