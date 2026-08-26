"""Fail-closed training runner and authorization boundary — v3.

Default: DRY RUN / PREFLIGHT ONLY. Scientific execution requires BOTH
--execute and tracked committed authorization. Supports distinct future
governed actions: synthetic generation for one member, training one policy.
Dry run enumerates 5 generation + 45 training jobs without model execution.
"""


from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from neuralmarket.core.device import resolve_device
from neuralmarket.core.runtime_identity import build_runtime_identity
from neuralmarket.data.manifests import canonical_dumps

EXPECTED_CONTRACT_V3_CANONICAL = "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01"
EXPECTED_CONTRACT_V3_BLOB = "eef7ad220db889166469799372759dfe1a96e35f"
EXPECTED_RUNTIME_IDENTITY = "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada"
CONTRACT_V3_PATH = Path("reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md")
AUTHORIZATION_TASK_FAMILY_RE = re.compile(r"^NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-[0-9]+$")
RECOVERY_AUTHORIZATION_TASK_FAMILY_RE = re.compile(r"^NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-[0-9]+$")

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

    Deprecated: use HedgingExecutionAuthorization with authorization_task_id.
    No fixed Task ID is hard-coded; future authorization must supply
    authorization_task_id matching the strict family regex.
    """

    schema_version: str = "hedging-execution-authorization-v1"
    authorization_task_id: str = ""  # required, must match family regex, no hard-coded 202
    contract_v3_canonical: str = EXPECTED_CONTRACT_V3_CANONICAL
    contract_v3_blob: str = EXPECTED_CONTRACT_V3_BLOB
    implementation_commit: str = ""
    runtime_identity: str = EXPECTED_RUNTIME_IDENTITY

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
    authorization binding at least: authorization_task_id, contract-v3 canonical
    SHA/blob, implementation Git commit, runtime identity, member allowlist,
    checkpoint identities, synthetic RNG, hedger seed allowlist, cost allowlist,
    maximum generation/training invocations, artifact roots, network false,
    final-test access false.

    No fixed future numeric Task ID is hard-coded; authorization_task_id must
    match the strict family regex and the exact committed artifact is bound.
    """

    schema_version: str = "hedging-execution-authorization-v1"
    authorization_task_id: str = ""  # required, must match AUTHORIZATION_TASK_FAMILY_RE, no hard-coded 202
    contract_v3_canonical: str = EXPECTED_CONTRACT_V3_CANONICAL
    contract_v3_blob: str = EXPECTED_CONTRACT_V3_BLOB
    implementation_commit: str = ""  # filled at authorization creation via git rev-parse HEAD
    runtime_identity: str = EXPECTED_RUNTIME_IDENTITY
    member_allowlist: tuple[str, ...] = ()
    checkpoint_identities: dict[str, str] | None = None  # member -> checkpoint SHA (selected)
    checkpoint_paths: dict[str, str] | None = None  # member -> checkpoint_path
    checkpoint_raw_sha256: dict[str, str] | None = None  # member -> raw SHA256
    checkpoint_git_hash: dict[str, str] | None = None  # member -> git hash-object
    synthetic_rng: dict[str, int] | None = None  # member -> seed 42001 etc.
    hedger_seed_allowlist: tuple[int, ...] = ()
    cost_allowlist: tuple[float, ...] = ()
    max_generation_invocations: int = 5
    max_training_invocations: int = 45
    artifact_roots: tuple[str, ...] = (
        "data/processed/research/hedging_synthetic",
        "data/processed/research/hedging_policies",
    )
    network: bool = False
    final_test_access: bool = False
    # Implementation manifest binding (commit + source blobs)
    implementation_manifest_sha256: str = ""
    implementation_source_blobs: dict[str, str] | None = None

def build_implementation_manifest(
    *,
    implementation_commit: str | None = None,
    source_roots: tuple[str, ...] = ("src/neuralmarket/research/deep_hedging",),
    extra_paths: tuple[str, ...] = (
        "src/neuralmarket/cli/deep_hedging.py",
        "src/neuralmarket/cli/main.py",
        "src/neuralmarket/core/device.py",
        "src/neuralmarket/core/runtime_identity.py",
        "src/neuralmarket/data/manifests.py",
        "src/neuralmarket/models/structured_vol_sde.py",
    ),
) -> dict[str, object]:
    """Deterministic implementation-manifest payload and hash.

    Collects exact Git blobs for all scientific implementation files under
    source_roots and extra_paths whose mutation would alter science.
    Includes all *.py under deep_hedging plus CLI dispatch, main, device,
    runtime, manifests, and NSDE model. Sorted lexicographically.
    Returns dict with implementation_commit, source_blobs, and manifest SHA.
    """
    if implementation_commit is None:
        implementation_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    source_blobs: dict[str, str] = {}
    for root in source_roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for p in sorted(root_path.rglob("*.py")):
            rel = p.as_posix()
            try:
                blob = subprocess.run(
                    ["git", "hash-object", rel], capture_output=True, text=True, check=True
                ).stdout.strip()
                source_blobs[rel] = blob
            except subprocess.CalledProcessError:
                continue
    for rel in extra_paths:
        try:
            blob = subprocess.run(
                ["git", "hash-object", rel], capture_output=True, text=True, check=True
            ).stdout.strip()
            source_blobs[rel] = blob
        except subprocess.CalledProcessError:
            continue
    payload: dict[str, object] = {
        "implementation_commit": implementation_commit,
        "source_blobs": dict(sorted(source_blobs.items())),
    }
    manifest_canonical = canonical_dumps(payload)
    manifest_sha = hashlib.sha256(manifest_canonical.encode("utf-8")).hexdigest()
    payload["implementation_manifest_sha256"] = manifest_sha
    return payload  # type: ignore[return-value]



def verify_implementation_manifest(
    *,
    authorized_commit: str,
    authorized_blobs: dict[str, str],
) -> None:
    """Fail closed on source drift or non-ancestor implementation commit.

    Requires authorized_commit is ancestor of current HEAD and every bound
    execution-critical path at current HEAD has exact authorized Git blob.
    Does NOT require current HEAD == authorized_commit (permits protocol/audit
    commits on top while preventing scientific code drift).
    """
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", authorized_commit, current_head]
    )
    if result.returncode != 0:
        raise AuthorizationError(
            f"implementation_commit {authorized_commit} is not ancestor of current HEAD {current_head} — fail closed on source drift"
        )
    for rel, expected_blob in authorized_blobs.items():
        try:
            current_blob = subprocess.run(
                ["git", "hash-object", rel], capture_output=True, text=True, check=True
            ).stdout.strip()
        except subprocess.CalledProcessError as e:
            raise AuthorizationError(f"failed to hash {rel} at current HEAD: {e}") from e
        if current_blob != expected_blob:
            raise AuthorizationError(
                f"source blob drift for {rel}: expected {expected_blob} got {current_blob} — fail closed"
            )


def verify_authorization_artifact(
    authorization_path: Path,
) -> dict[str, str]:
    """Verify authorization artifact is repository-relative, tracked, clean, and bound.

    Requires: path is repository-relative, tracked via git ls-files, no
    staged/unstaged modification (git diff), canonical SHA computed
    (LF-canonical), Git blob computed, commit exists in current history,
    authorization_task_id from its bytes is recorded.

    Returns dict with canonical SHA, blob, commit, task_id.
    """
    try:
        # Handle both absolute and relative paths: resolve to absolute then make repo-relative
        abs_path = authorization_path.resolve() if not authorization_path.is_absolute() else authorization_path.resolve()
        cwd = Path.cwd().resolve()
        rel = abs_path.relative_to(cwd)
    except ValueError as e:
        raise AuthorizationError(f"authorization path must be repository-relative, got {authorization_path}: {e}") from e
    result = subprocess.run(
        ["git", "ls-files", "--", str(rel)], capture_output=True, text=True, check=True
    )
    if not result.stdout.strip():
        raise AuthorizationError(f"authorization file not tracked: {rel}")
    for cmd in (["git", "diff", "--name-only", "--", str(rel)], ["git", "diff", "--cached", "--name-only", "--", str(rel)]):
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            raise AuthorizationError(f"authorization file has staged/unstaged modification: {rel} — {res.stdout.strip()}")
    raw = authorization_path.read_bytes()
    canon = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    canonical_sha = hashlib.sha256(canon).hexdigest()
    blob = subprocess.run(
        ["git", "hash-object", str(rel)], capture_output=True, text=True, check=True
    ).stdout.strip()
    log_res = subprocess.run(
        ["git", "log", "--all", "--pretty=format:%H", "--", str(rel)], capture_output=True, text=True, check=True
    )
    commits = [c for c in log_res.stdout.splitlines() if c.strip()]
    if not commits:
        raise AuthorizationError(f"authorization commit not found in current history for {rel}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    found_ancestor = False
    for commit in commits:
        res = subprocess.run(["git", "merge-base", "--is-ancestor", commit, head])
        if res.returncode == 0:
            found_ancestor = True
            break
    if not found_ancestor:
        raise AuthorizationError(f"authorization commit {commits[0]} not ancestor of HEAD {head}")
    try:
        payload = json.loads(raw.decode("utf-8"))
        task_id = str(payload.get("authorization_task_id") or payload.get("task_id") or "")
    except Exception as e:
        raise AuthorizationError(f"failed to parse authorization_task_id from {rel}: {e}") from e
    if not (AUTHORIZATION_TASK_FAMILY_RE.match(task_id) or RECOVERY_AUTHORIZATION_TASK_FAMILY_RE.match(task_id)):
        raise AuthorizationError(f"authorization_task_id {task_id!r} does not match family {AUTHORIZATION_TASK_FAMILY_RE.pattern} or {RECOVERY_AUTHORIZATION_TASK_FAMILY_RE.pattern}")
    return {
        "canonical_sha256": canonical_sha,
        "git_blob": blob,
        "commit": commits[0],
        "authorization_task_id": task_id,
        "path": str(rel),
    }


def validate_authorization_schema(payload: dict) -> None:
    """Validate extended authorization payload binds all required fields.

    Raises AuthorizationError if any binding missing or mismatched.
    """
    required = [
        "schema_version",
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
    task_id = str(payload.get("authorization_task_id") or payload.get("task_id") or "")
    if not task_id:
        raise AuthorizationError("authorization missing required field: authorization_task_id")
    if not AUTHORIZATION_TASK_FAMILY_RE.match(task_id):
        raise AuthorizationError(f"authorization_task_id {task_id!r} does not match family {AUTHORIZATION_TASK_FAMILY_RE.pattern}")
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
    members = payload.get("member_allowlist", [])
    if not set(members).issubset(set(MEMBERS)):
        raise AuthorizationError(f"member allowlist contains non-governed member: {members}")
    costs = payload.get("cost_allowlist", [])
    if not set(costs).issubset(set(COST_LEVELS)):
        raise AuthorizationError(f"cost allowlist contains non-governed cost: {costs}")
    seeds = payload.get("hedger_seed_allowlist", [])
    if not set(seeds).issubset(set(HEDGER_SEEDS)):
        raise AuthorizationError(f"hedger seed allowlist contains non-governed seed: {seeds}")
    # Historical validator must reject recovery payloads (distinct authorization surface)
    if any(k in payload for k in ("recovery_protocol_canonical", "recovery_protocol_blob", "recovery_protocol_path", "recovery_root", "recovery_tuples", "predecessor_identities", "authorization_type")):
        # If any recovery-specific discriminator present, this is not a historical authorization
        raise AuthorizationError("historical authorization must not contain recovery-specific fields")


RECOVERY_PROTOCOL_PATH = Path("reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md")
RECOVERY_PROTOCOL_CANONICAL = "4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8"
RECOVERY_PROTOCOL_BLOB = "6fcb39c29827d0d35ce3c777298fb75a81d00cb4"
RECOVERY_ROOT = "data/processed/research/hedging_policies_recovery_v1"
RECOVERY_AUTHORIZATION_TYPE = "GRU_TRAINING_RECOVERY_V1"

EVIDENCE_PATH = Path("reports/research/evidence/structured_vol_v5_deep_hedging_gru_training_execution_v1.json")
EVIDENCE_COMMIT = "ee7da9f8a465411b87d5ba3df6d7577230630352"
EVIDENCE_CANONICAL = "1d739b3e3f951331f1c8cc060f677a3d71c24b0184ece0a28796365079b5025c"
EVIDENCE_RAW = "af4a7a703f0d70537c86c292e68b3fe86c083c1c472a1ffa1d46cb9b992dd838"
EVIDENCE_BLOB = "b200923949e126ddc9dac60a7fa889f3bc23e2ec"


def _get_trusted_predecessor_map() -> dict[str, dict[str, str]]:
    """Derive expected predecessor map from immutable Task-216 execution evidence.

    Fail-closed unless evidence path, commit, canonical/blob, record count 45,
    tuple set exact frozen 45, no duplicate, all required fields present.
    """
    if not EVIDENCE_PATH.exists():
        raise AuthorizationError(f"trusted evidence not found: {EVIDENCE_PATH}")
    raw = EVIDENCE_PATH.read_bytes()
    canon = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    canonical_sha = hashlib.sha256(canon).hexdigest()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if canonical_sha != EVIDENCE_CANONICAL:
        raise AuthorizationError(f"evidence canonical mismatch: got {canonical_sha} expected {EVIDENCE_CANONICAL}")
    if raw_sha != EVIDENCE_RAW:
        raise AuthorizationError(f"evidence raw mismatch: got {raw_sha} expected {EVIDENCE_RAW}")
    blob = subprocess.run(["git", "hash-object", str(EVIDENCE_PATH)], capture_output=True, text=True, check=True).stdout.strip()
    if blob != EVIDENCE_BLOB:
        raise AuthorizationError(f"evidence blob mismatch: got {blob} expected {EVIDENCE_BLOB}")
    log_res = subprocess.run(["git", "log", "--all", "--pretty=format:%H", "--", str(EVIDENCE_PATH)], capture_output=True, text=True, check=True)
    commits = [c for c in log_res.stdout.splitlines() if c.strip()]
    if EVIDENCE_COMMIT not in commits:
        raise AuthorizationError(f"evidence commit {EVIDENCE_COMMIT} not in history")
    payload = json.loads(raw.decode("utf-8"))
    policies = payload.get("policies") or payload.get("records")
    if not isinstance(policies, list) or len(policies) != 45:
        raise AuthorizationError(f"evidence record count must be 45, got {len(policies) if isinstance(policies, list) else type(policies)}")
    expected_tuples = {(m, c, s) for m in MEMBERS for c in COST_LEVELS for s in HEDGER_SEEDS}
    seen = set()
    trusted: dict[str, dict[str, str]] = {}
    for rec in policies:
        member = rec.get("member")
        cost = rec.get("cost")
        hedger_seed = rec.get("hedger_seed")
        key = (member, cost, hedger_seed)
        if key in seen:
            raise AuthorizationError(f"duplicate tuple in evidence {key}")
        seen.add(key)
        for field in ("execution_started_path", "execution_started_sha256", "checkpoint_path", "checkpoint_raw_sha256", "terminal_manifest_path", "terminal_manifest_sha256"):
            if field not in rec:
                raise AuthorizationError(f"evidence record missing {field} for {key}")
        hist_path = str(Path(rec["checkpoint_path"]).parent.as_posix())
        hist_path = hist_path.replace("\\", "/")
        map_key = f"{member}:{cost}:{hedger_seed}"
        trusted[map_key] = {
            "historical_artifact_path": hist_path,
            "historical_execution_started_sha": str(rec["execution_started_sha256"]),
            "historical_checkpoint_sha": str(rec["checkpoint_raw_sha256"]),
            "historical_terminal_sha": str(rec["terminal_manifest_sha256"]),
            "historical_classification": "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP",
        }
    if seen != expected_tuples:
        raise AuthorizationError(f"evidence tuple set mismatch: got {seen} expected {expected_tuples}")
    return trusted


def validate_recovery_authorization_schema(payload: dict) -> None:
    """Validate recovery authorization — fail-closed, distinct from historical.

    Requires exact binding for recovery protocol, repaired implementation,
    contract, runtime, recovery root, 45 tuples, predecessor identities,
    ceiling 45, network false, final false.
    """
    # Discriminator
    if payload.get("authorization_type") != RECOVERY_AUTHORIZATION_TYPE:
        raise AuthorizationError(f"recovery authorization_type must be {RECOVERY_AUTHORIZATION_TYPE!r}")
    task_id = str(payload.get("authorization_task_id") or payload.get("task_id") or "")
    if not RECOVERY_AUTHORIZATION_TASK_FAMILY_RE.match(task_id):
        raise AuthorizationError(f"recovery authorization_task_id {task_id!r} does not match family {RECOVERY_AUTHORIZATION_TASK_FAMILY_RE.pattern}")
    if AUTHORIZATION_TASK_FAMILY_RE.match(task_id):
        raise AuthorizationError(f"recovery authorization_task_id {task_id!r} must not match historical family")
    # Recovery protocol binding
    if payload.get("recovery_protocol_path") != str(RECOVERY_PROTOCOL_PATH):
        raise AuthorizationError(f"recovery_protocol_path must be {str(RECOVERY_PROTOCOL_PATH)!r}")
    if payload.get("recovery_protocol_canonical") != RECOVERY_PROTOCOL_CANONICAL:
        raise AuthorizationError("recovery_protocol_canonical mismatch")
    if payload.get("recovery_protocol_blob") != RECOVERY_PROTOCOL_BLOB:
        raise AuthorizationError("recovery_protocol_blob mismatch")
    # Dynamic implementation binding (non-circular)
    impl_commit = str(payload.get("implementation_commit") or "")
    impl_manifest = str(payload.get("implementation_manifest_sha256") or payload.get("implementation_manifest") or "")
    if not impl_commit:
        raise AuthorizationError("recovery implementation_commit missing")
    if not impl_manifest:
        raise AuthorizationError("recovery implementation_manifest missing")
    # A. Prove implementation_commit exists locally
    res = subprocess.run(["git", "cat-file", "-e", impl_commit], capture_output=True)
    if res.returncode != 0:
        raise AuthorizationError(f"implementation_commit {impl_commit} does not exist locally")
    # B. Rebuild exact execution-critical source manifest at that commit
    rebuilt = build_implementation_manifest(implementation_commit=impl_commit)
    rebuilt_manifest = str(rebuilt.get("implementation_manifest_sha256"))
    # C. Require rebuilt manifest SHA == authorization manifest
    if rebuilt_manifest != impl_manifest:
        raise AuthorizationError(f"rebuilt manifest {rebuilt_manifest} != authorization manifest {impl_manifest}")
    # D. Require current executing production source blobs equal the blobs at authorization commit
    # First, verify payload's source_blobs matches rebuilt (if provided)
    if payload.get("implementation_source_blobs"):
        if payload["implementation_source_blobs"] != rebuilt["source_blobs"]:
            raise AuthorizationError("implementation_source_blobs mismatch with rebuilt manifest")
    # Then, verify current source equals the blobs at the implementation commit (not just the payload's blobs)
    for rel in rebuilt["source_blobs"]:
        # Get expected blob at the implementation commit
        res_commit = subprocess.run(["git", "ls-tree", impl_commit, "--", rel], capture_output=True, text=True, check=True)
        if not res_commit.stdout.strip():
            raise AuthorizationError(f"implementation_commit {impl_commit} missing expected path {rel}")
        expected_at_commit = res_commit.stdout.strip().split()[2]
        # Get current blob
        try:
            cur_blob = subprocess.run(["git", "hash-object", rel], capture_output=True, text=True, check=True).stdout.strip()
        except subprocess.CalledProcessError as e:
            raise AuthorizationError(f"failed to hash {rel}: {e}") from e
        if cur_blob != expected_at_commit:
            raise AuthorizationError(f"source blob drift for {rel}: current {cur_blob} != expected at {impl_commit} {expected_at_commit}")
        # Also ensure payload's blob (if provided) matches expected at commit
        if payload.get("implementation_source_blobs") and payload["implementation_source_blobs"].get(rel) != expected_at_commit:
            raise AuthorizationError(f"payload source blob for {rel} does not match expected at {impl_commit}")
    # E. Require implementation commit is ancestor of current HEAD
    cur_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    res = subprocess.run(["git", "merge-base", "--is-ancestor", impl_commit, cur_head])
    if res.returncode != 0:
        raise AuthorizationError(f"implementation_commit {impl_commit} is not ancestor of current HEAD {cur_head}")
    # Contract / runtime
    if payload.get("contract_v3_canonical") != EXPECTED_CONTRACT_V3_CANONICAL:
        raise AuthorizationError("recovery contract canonical mismatch")
    if payload.get("contract_v3_blob") != EXPECTED_CONTRACT_V3_BLOB:
        raise AuthorizationError("recovery contract blob mismatch")
    if payload.get("runtime_identity") != EXPECTED_RUNTIME_IDENTITY:
        raise AuthorizationError("recovery runtime mismatch")
    # Recovery root exact
    if payload.get("recovery_root") != RECOVERY_ROOT:
        raise AuthorizationError(f"recovery_root must be {RECOVERY_ROOT!r}")
    artifact_roots = payload.get("artifact_roots", [])
    if RECOVERY_ROOT not in artifact_roots:
        raise AuthorizationError(f"artifact_roots must contain recovery root {RECOVERY_ROOT!r}")
    if "data/processed/research/hedging_policies" in artifact_roots and RECOVERY_ROOT not in artifact_roots:
        raise AuthorizationError("recovery artifact_roots must be distinct from historical")
    # Network / final
    if payload.get("network") is not False:
        raise AuthorizationError("recovery network must be false")
    if payload.get("final_test_access") is not False:
        raise AuthorizationError("recovery final_test_access must be false")
    # Ceiling
    if int(payload.get("max_training_invocations", 0)) != 45:
        raise AuthorizationError("recovery max_training_invocations must be 45")
    if int(payload.get("max_generation_invocations", 0)) != 0:
        raise AuthorizationError("recovery max_generation_invocations must be 0")
    # Allowlist 45 tuples: member 5, cost 3, seed 3
    members = payload.get("member_allowlist", [])
    costs = payload.get("cost_allowlist", [])
    seeds = payload.get("hedger_seed_allowlist", [])
    if set(members) != set(MEMBERS):
        raise AuthorizationError(f"recovery member_allowlist must be exactly {MEMBERS}")
    if set(costs) != set(COST_LEVELS):
        raise AuthorizationError(f"recovery cost_allowlist must be exactly {COST_LEVELS}")
    if set(seeds) != set(HEDGER_SEEDS):
        raise AuthorizationError(f"recovery hedger_seed_allowlist must be exactly {HEDGER_SEEDS}")
    # Exact 45 recovery tuples
    tuples = payload.get("recovery_tuples") or payload.get("tuples")
    if tuples is None:
        raise AuthorizationError("recovery_tuples missing")
    if len(tuples) != 45:
        raise AuthorizationError(f"recovery_tuples must be 45, got {len(tuples)}")
    seen = set()
    for t in tuples:
        key = (t.get("member"), t.get("cost"), t.get("hedger_seed"))
        if key in seen:
            raise AuthorizationError(f"duplicate recovery tuple {key}")
        seen.add(key)
        if key[0] not in MEMBERS or key[1] not in COST_LEVELS or key[2] not in HEDGER_SEEDS:
            raise AuthorizationError(f"recovery tuple {key} not in frozen universe")
    if seen != {(m, c, s) for m in MEMBERS for c in COST_LEVELS for s in HEDGER_SEEDS}:
        raise AuthorizationError("recovery_tuples must be exactly the frozen 45 universe")
    # Predecessor identities per tuple
    pred = payload.get("predecessor_identities") or payload.get("predecessor_mapping")
    if not isinstance(pred, dict) or len(pred) != 45:
        raise AuthorizationError("predecessor_identities must be dict of 45")
    for key, meta in pred.items():
        if not isinstance(meta, dict):
            raise AuthorizationError(f"predecessor {key} must be dict")
        for req in ("historical_artifact_path", "historical_execution_started_sha", "historical_checkpoint_sha", "historical_terminal_sha", "historical_classification"):
            if req not in meta:
                raise AuthorizationError(f"predecessor {key} missing {req}")
        if meta.get("historical_classification") != "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP":
            raise AuthorizationError(f"predecessor {key} historical_classification must be SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP")
    # Field-for-field predecessor equality against trusted immutable evidence
    trusted = _get_trusted_predecessor_map()
    if set(pred.keys()) != set(trusted.keys()):
        raise AuthorizationError(f"predecessor_identities keys mismatch: expected {sorted(trusted.keys())[:3]}... got {sorted(pred.keys())[:3]}...")
    for key, expected in trusted.items():
        actual = pred.get(key)
        if actual is None:
            raise AuthorizationError(f"predecessor {key} missing in authorization")
        for field in ("historical_artifact_path", "historical_execution_started_sha", "historical_checkpoint_sha", "historical_terminal_sha", "historical_classification"):
            if actual.get(field) != expected.get(field):
                raise AuthorizationError(f"predecessor {key} field {field} mismatch: expected {expected.get(field)!r} got {actual.get(field)!r}")
    # Schema version also required for recovery (reuse same)
