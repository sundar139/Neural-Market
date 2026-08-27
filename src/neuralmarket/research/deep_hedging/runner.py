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
RECOVERY_ROOT = "data/processed/research/hedging_policies_recovery_v2"
RECOVERY_AUTHORIZATION_TYPE = "GRU_TRAINING_RECOVERY_V1"

SUCCESSOR_ROOT = "data/processed/research/hedging_policies_recovery_v3"
SUCCESSOR_PREREQUISITE_PATH = Path("reports/protocol/hedging_recovery_successor_authorization_prerequisites_264.json")
SUCCESSOR_PREREQUISITE_COMMIT = "0d4489fe1880a4cfed9752bf3cc32aa19953adae"
SUCCESSOR_PREREQUISITE_CANONICAL = "fe5983662d4e8b1269c6d305a5a2741c7c171e38c4e92f9bf8c8e8e77b491496"
SUCCESSOR_PREREQUISITE_RAW = "55675fbb78c1e20df1a130aa23ab9cb31bb4683bb40d8fd7fa82bc74719e14b7"
SUCCESSOR_PREREQUISITE_BLOB = "24cfc59af40a80f51f5e3d4bc2b3297607f754d4"
SUCCESSOR_HEDGER_SEEDS = (60999, 53804, 89356)

PREREQUISITE_PATH = Path("reports/protocol/hedging_recovery_v2_authorization_prerequisites_246.json")
PREREQUISITE_COMMIT = "d4813d60002128c898fe88e40fd846dde80b5c3d"
PREREQUISITE_CANONICAL = "c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0"
PREREQUISITE_RAW = "88b51be4822c23c6c608fc75cd3cb4299d96afc1f2a18b7d4e53b929df296224"
PREREQUISITE_BLOB = "a9d74c8a9fdc325d7e0f99b8a382c4bf8b3428d3"

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


def _get_authenticated_prerequisite_values() -> dict[str, str]:
    """Independently authenticate the frozen Task-246 prerequisite artifact.

    Verifies tracked exact path, commit existence/ancestry, commit→path blob exact,
    current bytes unchanged, canonical LF SHA exact, raw SHA exact, git blob exact.
    Returns dict of trusted values for payload equality check.
    Fail-closed on any mismatch.
    """
    # Tracked exact path
    if not PREREQUISITE_PATH.exists():
        raise AuthorizationError(f"prerequisite artifact not found: {PREREQUISITE_PATH}")
    ls = subprocess.run(["git", "ls-files", "--", str(PREREQUISITE_PATH)], capture_output=True, text=True, check=True)
    if not ls.stdout.strip():
        raise AuthorizationError(f"prerequisite artifact not tracked: {PREREQUISITE_PATH}")
    # No staged/unstaged modification
    for cmd in (["git", "diff", "--name-only", "--", str(PREREQUISITE_PATH)], ["git", "diff", "--cached", "--name-only", "--", str(PREREQUISITE_PATH)]):
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            raise AuthorizationError(f"prerequisite artifact has staged/unstaged modification: {PREREQUISITE_PATH}")
    raw = PREREQUISITE_PATH.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    canon = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    canonical_sha = hashlib.sha256(canon).hexdigest()
    blob = subprocess.run(["git", "hash-object", str(PREREQUISITE_PATH)], capture_output=True, text=True, check=True).stdout.strip()
    if raw_sha != PREREQUISITE_RAW:
        raise AuthorizationError(f"prerequisite raw mismatch: got {raw_sha} expected {PREREQUISITE_RAW}")
    if canonical_sha != PREREQUISITE_CANONICAL:
        raise AuthorizationError(f"prerequisite canonical mismatch: got {canonical_sha} expected {PREREQUISITE_CANONICAL}")
    if blob != PREREQUISITE_BLOB:
        raise AuthorizationError(f"prerequisite blob mismatch: got {blob} expected {PREREQUISITE_BLOB}")
    # Commit existence
    res = subprocess.run(["git", "cat-file", "-e", PREREQUISITE_COMMIT], capture_output=True)
    if res.returncode != 0:
        raise AuthorizationError(f"prerequisite commit {PREREQUISITE_COMMIT} does not exist locally")
    # Commit → path blob exact
    ls_tree = subprocess.run(["git", "ls-tree", PREREQUISITE_COMMIT, "--", str(PREREQUISITE_PATH)], capture_output=True, text=True, check=True)
    if not ls_tree.stdout.strip():
        raise AuthorizationError(f"prerequisite commit {PREREQUISITE_COMMIT} missing path {PREREQUISITE_PATH}")
    commit_blob = ls_tree.stdout.strip().split()[2]
    if commit_blob != PREREQUISITE_BLOB:
        raise AuthorizationError(f"prerequisite commit blob mismatch: got {commit_blob} expected {PREREQUISITE_BLOB}")
    # Commit ancestry
    cur_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    res = subprocess.run(["git", "merge-base", "--is-ancestor", PREREQUISITE_COMMIT, cur_head])
    if res.returncode != 0:
        raise AuthorizationError(f"prerequisite commit {PREREQUISITE_COMMIT} is not ancestor of current HEAD {cur_head}")
    return {
        "prerequisite_artifact_path": PREREQUISITE_PATH.as_posix(),
        "prerequisite_commit": PREREQUISITE_COMMIT,
        "prerequisite_canonical_sha256": PREREQUISITE_CANONICAL,
        "prerequisite_raw_sha256": PREREQUISITE_RAW,
        "prerequisite_blob": PREREQUISITE_BLOB,
    }


def _get_authenticated_successor_prerequisite_values() -> dict[str, str]:
    """Authenticate successor prerequisite 264 — file-level only, no execution authority."""
    if not SUCCESSOR_PREREQUISITE_PATH.exists():
        raise AuthorizationError(f"successor prerequisite not found: {SUCCESSOR_PREREQUISITE_PATH}")
    ls = subprocess.run(["git", "ls-files", "--", str(SUCCESSOR_PREREQUISITE_PATH)], capture_output=True, text=True, check=True)
    if not ls.stdout.strip():
        raise AuthorizationError(f"successor prerequisite not tracked: {SUCCESSOR_PREREQUISITE_PATH}")
    for cmd in (["git", "diff", "--name-only", "--", str(SUCCESSOR_PREREQUISITE_PATH)], ["git", "diff", "--cached", "--name-only", "--", str(SUCCESSOR_PREREQUISITE_PATH)]):
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stdout.strip():
            raise AuthorizationError(f"successor prerequisite has staged/unstaged modification: {SUCCESSOR_PREREQUISITE_PATH}")
    raw = SUCCESSOR_PREREQUISITE_PATH.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    canon = raw.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    canonical_sha = hashlib.sha256(canon).hexdigest()
    blob = subprocess.run(["git", "hash-object", str(SUCCESSOR_PREREQUISITE_PATH)], capture_output=True, text=True, check=True).stdout.strip()
    if raw_sha != SUCCESSOR_PREREQUISITE_RAW:
        raise AuthorizationError(f"successor prerequisite raw mismatch: got {raw_sha} expected {SUCCESSOR_PREREQUISITE_RAW}")
    if canonical_sha != SUCCESSOR_PREREQUISITE_CANONICAL:
        raise AuthorizationError(f"successor prerequisite canonical mismatch: got {canonical_sha} expected {SUCCESSOR_PREREQUISITE_CANONICAL}")
    if blob != SUCCESSOR_PREREQUISITE_BLOB:
        raise AuthorizationError(f"successor prerequisite blob mismatch: got {blob} expected {SUCCESSOR_PREREQUISITE_BLOB}")
    res = subprocess.run(["git", "cat-file", "-e", SUCCESSOR_PREREQUISITE_COMMIT], capture_output=True)
    if res.returncode != 0:
        raise AuthorizationError(f"successor prerequisite commit {SUCCESSOR_PREREQUISITE_COMMIT} does not exist locally")
    ls_tree = subprocess.run(["git", "ls-tree", SUCCESSOR_PREREQUISITE_COMMIT, "--", str(SUCCESSOR_PREREQUISITE_PATH)], capture_output=True, text=True, check=True)
    if not ls_tree.stdout.strip():
        raise AuthorizationError(f"successor prerequisite commit {SUCCESSOR_PREREQUISITE_COMMIT} missing path {SUCCESSOR_PREREQUISITE_PATH}")
    commit_blob = ls_tree.stdout.strip().split()[2]
    if commit_blob != SUCCESSOR_PREREQUISITE_BLOB:
        raise AuthorizationError(f"successor prerequisite commit blob mismatch: got {commit_blob} expected {SUCCESSOR_PREREQUISITE_BLOB}")
    cur_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    res = subprocess.run(["git", "merge-base", "--is-ancestor", SUCCESSOR_PREREQUISITE_COMMIT, cur_head])
    if res.returncode != 0:
        raise AuthorizationError(f"successor prerequisite commit {SUCCESSOR_PREREQUISITE_COMMIT} is not ancestor of current HEAD {cur_head}")
    return {
        "successor_prerequisite_path": SUCCESSOR_PREREQUISITE_PATH.as_posix(),
        "successor_prerequisite_commit": SUCCESSOR_PREREQUISITE_COMMIT,
        "successor_prerequisite_canonical": SUCCESSOR_PREREQUISITE_CANONICAL,
        "successor_prerequisite_raw": SUCCESSOR_PREREQUISITE_RAW,
        "successor_prerequisite_blob": SUCCESSOR_PREREQUISITE_BLOB,
    }


def validate_successor_prerequisite(payload: dict) -> None:
    """Validate successor prerequisite 264 contents — evidence only, never execution-authorized.

    Fail-closed on any mismatch. Must not be usable as execution authorization.
    Enforces all eight frozen tuple fields, frozen member/cost/seed universes,
    exact 45-tuple ledger, 45 unique successor paths, and exact Task216
    predecessor map equality with recovery_v1/v2/v3 rejection.
    """
    if payload.get("authorization_type"):
        raise AuthorizationError("successor prerequisite must not have authorization_type (would be execution-authorized)")
    if payload.get("authorization_task_id"):
        if "SUCCESSOR-AUTHORIZATION-PREREQUISITES" not in str(payload.get("task_id")) and "RECOVERY_SUCCESSOR" not in str(payload.get("task_id")):
            raise AuthorizationError("successor prerequisite task_id mismatch")
    if payload.get("artifact_type") != "GRU_TRAINING_RECOVERY_SUCCESSOR_AUTHORIZATION_PREREQUISITES_V2":
        raise AuthorizationError(f"successor artifact_type must be GRU_TRAINING_RECOVERY_SUCCESSOR_AUTHORIZATION_PREREQUISITES_V2, got {payload.get('artifact_type')!r}")
    _get_authenticated_successor_prerequisite_values()
    tc = payload.get("training_contract") or {}
    if tc.get("canonical_sha256") != "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01":
        raise AuthorizationError("successor training contract canonical mismatch")
    if tc.get("blob") != "eef7ad220db889166469799372759dfe1a96e35f":
        raise AuthorizationError("successor training contract blob mismatch")
    sp = payload.get("successor_protocol") or {}
    if sp.get("canonical_sha256") != "922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418":
        raise AuthorizationError("successor protocol canonical mismatch")
    if sp.get("blob") != "8715db1c76bd8457eca29ff523e54b2d9ce573ef":
        raise AuthorizationError("successor protocol blob mismatch")
    sup = payload.get("training_contract_supersession") or {}
    clauses = sup.get("superseded_clauses") or []
    if len(clauses) != 5:
        raise AuthorizationError(f"successor superseded_clauses must be 5, got {len(clauses)}")
    impl = payload.get("implementation_authority") or {}
    if impl.get("implementation_commit") != "d762e5a18a1552d34fce79ea5d765a66c042d9c1":
        raise AuthorizationError("successor implementation_commit mismatch")
    if impl.get("implementation_manifest_sha256") != "9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a":
        raise AuthorizationError("successor implementation_manifest mismatch")
    if payload.get("runtime_identity_sha256") != "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada":
        raise AuthorizationError("successor runtime mismatch")
    ds = payload.get("datasets") or {}
    if set(ds.keys()) != {"seed-01","seed-02","seed-04","seed-05","reserve-j01"}:
        raise AuthorizationError("successor datasets must be exactly 5")
    expected_ds_sha = {
        "seed-01": "cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287",
        "seed-02": "20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7",
        "seed-04": "60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8",
        "seed-05": "8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204",
        "reserve-j01": "60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc",
    }
    for k, v in ds.items():
        if not isinstance(v, dict) or v.get("sha256") != expected_ds_sha.get(k):
            raise AuthorizationError(f"successor dataset {k} sha256 mismatch")
    if payload.get("successor_root") != SUCCESSOR_ROOT:
        raise AuthorizationError(f"successor_root must be {SUCCESSOR_ROOT!r}")
    seeds = payload.get("successor_hedger_seeds") or []
    if set(seeds) != set(SUCCESSOR_HEDGER_SEEDS):
        raise AuthorizationError(f"successor_hedger_seeds must be {SUCCESSOR_HEDGER_SEEDS}")
    for s in seeds:
        if s in (31001,31002,31003):
            raise AuthorizationError(f"successor seed {s} must not be old seed")
    FROZEN_MEMBERS = ("seed-01", "seed-02", "seed-04", "seed-05", "reserve-j01")
    FROZEN_COSTS = (0.0, 0.001, 0.005)
    FROZEN_SEEDS = SUCCESSOR_HEDGER_SEEDS
    FROZEN_MEMBER_SET = set(FROZEN_MEMBERS)
    FROZEN_COST_SET = set(FROZEN_COSTS)
    FROZEN_SEED_SET = set(FROZEN_SEEDS)
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES, COST_BPS
    expected_tuples_by_key: dict[tuple[str, float, int], dict[str, object]] = {}
    expected_paths: set[str] = set()
    for m in FROZEN_MEMBERS:
        rp = RUN_PREFIXES[m]
        for c in FROZEN_COSTS:
            bps = COST_BPS[c]
            for s in FROZEN_SEEDS:
                dataset_path = f"data/processed/research/hedging_synthetic/{rp}_{m}/synthetic_episodes_v1.parquet"
                dataset_sha = expected_ds_sha[m]
                expected_artifact_path = f"{SUCCESSOR_ROOT}/{rp}_{m}/c_{bps}/h_{s}"
                key = (m, float(c), int(s))
                expected_tuples_by_key[key] = {
                    "member": m,
                    "run_prefix": rp,
                    "cost": float(c),
                    "cost_bps": int(bps),
                    "hedger_seed": int(s),
                    "dataset_path": dataset_path,
                    "dataset_sha256": dataset_sha,
                    "expected_artifact_path": expected_artifact_path,
                }
                expected_paths.add(expected_artifact_path)
    tuples = payload.get("successor_prospective_tuples") or payload.get("successor_tuples") or []
    if len(tuples) != 45:
        raise AuthorizationError(f"successor tuples must be 45, got {len(tuples)}")
    seen_keys: set[tuple[str, float, int]] = set()
    seen_paths: set[str] = set()
    for t in tuples:
        if not isinstance(t, dict):
            raise AuthorizationError("successor tuple must be dict")
        for field in ("member","run_prefix","cost","cost_bps","hedger_seed","dataset_path","dataset_sha256","expected_artifact_path"):
            if field not in t:
                alt = t.get("expected_successor_artifact_path") if field == "expected_artifact_path" else None
                if field == "expected_artifact_path" and alt is not None:
                    pass
                else:
                    raise AuthorizationError(f"successor tuple missing field {field}: {t}")
        member = t.get("member")
        cost = t.get("cost")
        hedger_seed = t.get("hedger_seed")
        run_prefix = t.get("run_prefix")
        cost_bps = t.get("cost_bps")
        dataset_path = t.get("dataset_path")
        dataset_sha256 = t.get("dataset_sha256")
        expected_artifact_path = t.get("expected_artifact_path") or t.get("expected_successor_artifact_path")
        try:
            norm_cost = float(cost)  # type: ignore[arg-type]
            norm_seed = int(hedger_seed)  # type: ignore[arg-type]
        except Exception:
            raise AuthorizationError(f"successor tuple cost/seed type invalid: {t}")
        key = (str(member), norm_cost, norm_seed)
        if member not in FROZEN_MEMBER_SET:
            raise AuthorizationError(f"successor tuple member {member!r} not in frozen universe {sorted(FROZEN_MEMBER_SET)}")
        if norm_cost not in FROZEN_COST_SET:
            raise AuthorizationError(f"successor tuple cost {cost!r} not in frozen universe {sorted(FROZEN_COST_SET)}")
        if norm_seed not in FROZEN_SEED_SET:
            raise AuthorizationError(f"successor tuple hedger_seed {hedger_seed!r} not in frozen universe {sorted(FROZEN_SEED_SET)}")
        if norm_seed in (31001,31002,31003):
            raise AuthorizationError(f"successor tuple {key} uses old seed")
        if key in seen_keys:
            raise AuthorizationError(f"duplicate successor tuple {key}")
        seen_keys.add(key)
        exp = expected_tuples_by_key.get(key)
        if exp is None:
            raise AuthorizationError(f"successor tuple {key} not in frozen 45 universe")
        if run_prefix != exp["run_prefix"]:
            raise AuthorizationError(f"successor tuple {key} run_prefix mismatch: got {run_prefix!r} expected {exp['run_prefix']!r}")
        if int(cost_bps) != int(exp["cost_bps"]):  # type: ignore[arg-type]
            raise AuthorizationError(f"successor tuple {key} cost_bps mismatch: got {cost_bps!r} expected {exp['cost_bps']!r}")
        if float(cost) != float(exp["cost"]):  # type: ignore[arg-type]
            raise AuthorizationError(f"successor tuple {key} cost mismatch: got {cost!r} expected {exp['cost']!r}")
        if dataset_path != exp["dataset_path"]:
            raise AuthorizationError(f"successor tuple {key} dataset_path mismatch: got {dataset_path!r} expected {exp['dataset_path']!r}")
        if dataset_sha256 != exp["dataset_sha256"]:
            raise AuthorizationError(f"successor tuple {key} dataset_sha256 mismatch: got {dataset_sha256!r} expected {exp['dataset_sha256']!r}")
        if expected_artifact_path != exp["expected_artifact_path"]:
            raise AuthorizationError(f"successor tuple {key} expected_artifact_path mismatch: got {expected_artifact_path!r} expected {exp['expected_artifact_path']!r}")
        exp_path_norm = str(expected_artifact_path).replace("\\","/")
        if not exp_path_norm.startswith(SUCCESSOR_ROOT + "/"):
            raise AuthorizationError(f"successor tuple {key} expected path must start with {SUCCESSOR_ROOT!r}, got {expected_artifact_path!r}")
        if "hedging_policies_recovery_v2" in exp_path_norm or "hedging_policies_recovery_v1" in exp_path_norm:
            raise AuthorizationError(f"successor tuple {key} uses wrong recovery root {expected_artifact_path!r}")
        if exp_path_norm == SUCCESSOR_ROOT or (exp_path_norm.startswith("data/processed/research/hedging_policies/") and not exp_path_norm.startswith(SUCCESSOR_ROOT + "/")):
            raise AuthorizationError(f"successor tuple {key} uses historical root {expected_artifact_path!r}")
        if exp_path_norm in seen_paths:
            raise AuthorizationError(f"duplicate successor path {exp_path_norm!r}")
        seen_paths.add(exp_path_norm)
    if seen_keys != set(expected_tuples_by_key.keys()):
        raise AuthorizationError(f"successor tuple set mismatch: got {seen_keys} expected {set(expected_tuples_by_key.keys())}")
    if len(seen_paths) != 45:
        raise AuthorizationError(f"successor unique paths must be 45, got {len(seen_paths)}")
    if seen_paths != expected_paths:
        raise AuthorizationError("successor path universe mismatch")
    pred = payload.get("predecessor_identities") or {}
    if not isinstance(pred, dict) or len(pred) != 45:
        raise AuthorizationError("successor predecessor_identities must be dict of 45")
    trusted = _get_trusted_predecessor_map()
    if set(pred.keys()) != set(trusted.keys()):
        raise AuthorizationError(f"successor predecessor_identities keys mismatch: expected {sorted(trusted.keys())[:3]}... got {sorted(pred.keys())[:3]}...")
    for key, expected in trusted.items():
        actual = pred.get(key)
        if actual is None:
            raise AuthorizationError(f"predecessor {key} missing in payload")
        if not isinstance(actual, dict):
            raise AuthorizationError(f"predecessor {key} must be dict")
        for field in ("historical_artifact_path","historical_execution_started_sha","historical_checkpoint_sha","historical_terminal_sha","historical_classification"):
            if field not in actual:
                raise AuthorizationError(f"predecessor {key} missing {field}")
            if actual.get(field) != expected.get(field):
                raise AuthorizationError(f"predecessor {key} field {field} mismatch: expected {expected.get(field)!r} got {actual.get(field)!r}")
        hist_path = str(actual.get("historical_artifact_path") or "").replace("\\","/")
        if not hist_path.startswith("data/processed/research/hedging_policies/"):
            raise AuthorizationError(f"predecessor {key} historical_artifact_path must start with hedging_policies/, got {hist_path!r}")
        if "hedging_policies_recovery_v1" in hist_path or "hedging_policies_recovery_v2" in hist_path or "hedging_policies_recovery_v3" in hist_path:
            raise AuthorizationError(f"predecessor {key} historical path must not be recovery root, got {hist_path!r}")
        if actual.get("historical_classification") != "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP":
            raise AuthorizationError(f"predecessor {key} historical_classification must be SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP")
    if int(payload.get("task253_import_count", 0)) != 0:
        raise AuthorizationError("successor task253_import_count must be 0")
    if int(payload.get("training_ceiling", 0)) != 45:
        raise AuthorizationError("successor training_ceiling must be 45")
    if int(payload.get("prospective_consumed", 0)) != 0:
        raise AuthorizationError("successor prospective_consumed must be 0")
    if int(payload.get("prospective_remaining", 0)) != 45:
        raise AuthorizationError("successor prospective_remaining must be 45")
    if int(payload.get("generation_ceiling", payload.get("generation", 0))) != 0:
        raise AuthorizationError("successor generation must be 0")
    for k in ("retry_permitted","rerun_permitted","replacement_permitted"):
        v = payload.get(k)
        if v is None or int(v) != 0:
            raise AuthorizationError(f"successor {k} must be 0")
        if isinstance(v, bool):
            raise AuthorizationError(f"successor {k} must be int 0 not bool")
    if payload.get("network") is not False or payload.get("final_test_access") is not False:
        raise AuthorizationError("successor network/final must be false")
    if payload.get("execution_authority") == "GRANTED" or payload.get("execution_authorization") == "GRANTED":
        raise AuthorizationError("successor prerequisite must not have execution authority granted")


def get_successor_campaign_config() -> dict[str, object]:
    """Production successor seam — authenticated file + validated campaign config, no execution authority.

    Reads successor prerequisite bytes from SUCCESSOR_PREREQUISITE_PATH itself,
    calls the existing authenticated loader/validator, binds SUCCESSOR_ROOT,
    SUCCESSOR_HEDGER_SEEDS, validated tuple universe and validated predecessor
    universe, and makes trainer.SUCCESSOR_ROOT_PATH load-bearing in successor
    artifact-path resolution. Returns only validated configuration, never
    execution authority.
    """
    _get_authenticated_successor_prerequisite_values()
    payload = json.loads(SUCCESSOR_PREREQUISITE_PATH.read_bytes().decode("utf-8"))
    validate_successor_prerequisite(payload)
    from neuralmarket.research.deep_hedging.trainer import SUCCESSOR_ROOT_PATH as _TRAINER_ROOT
    if _TRAINER_ROOT.as_posix() != SUCCESSOR_ROOT:
        raise AuthorizationError(f"trainer SUCCESSOR_ROOT_PATH {_TRAINER_ROOT.as_posix()!r} != {SUCCESSOR_ROOT!r}")
    if payload.get("successor_root") != _TRAINER_ROOT.as_posix():
        raise AuthorizationError("successor_root payload does not match trainer SUCCESSOR_ROOT_PATH")
    tuples = payload.get("successor_prospective_tuples") or payload.get("successor_tuples") or []
    for t in tuples:
        p = str(t.get("expected_artifact_path") or "").replace("\\","/")
        if not p.startswith(_TRAINER_ROOT.as_posix() + "/"):
            raise AuthorizationError(f"successor path not under trainer root {p!r}")
        if "hedging_policies_recovery_v2" in p or "hedging_policies_recovery_v1" in p:
            raise AuthorizationError(f"successor path uses wrong recovery root {p!r}")
    trusted = _get_trusted_predecessor_map()
    return {
        "successor_root": _TRAINER_ROOT,
        "successor_hedger_seeds": tuple(SUCCESSOR_HEDGER_SEEDS),
        "successor_tuples": tuples,
        "predecessor_identities": payload.get("predecessor_identities"),
        "trusted_predecessor_map": trusted,
        "validated": True,
        "execution_authority": "NOT_GRANTED",
    }


def resolve_successor_artifact_path(member: str, cost: float, hedger_seed: int) -> Path:
    """Resolve one validated successor artifact path under trainer SUCCESSOR_ROOT_PATH.

    Production path-resolution seam — uses authenticated config, rejects arbitrary
    roots and caller-supplied prerequisite dicts, resolves exactly under
    data/processed/research/hedging_policies_recovery_v3.
    """
    cfg = get_successor_campaign_config()
    from neuralmarket.research.deep_hedging.trainer import SUCCESSOR_ROOT_PATH as _TRAINER_ROOT
    tuples = cfg.get("successor_tuples") or []
    for t in tuples:  # type: ignore[union-attr]
        if str(t.get("member")) == str(member) and float(t.get("cost")) == float(cost) and int(t.get("hedger_seed")) == int(hedger_seed):  # type: ignore[arg-type]
            p = Path(str(t.get("expected_artifact_path")))
            if not p.as_posix().startswith(_TRAINER_ROOT.as_posix() + "/"):
                raise AuthorizationError(f"resolved successor path not under {_TRAINER_ROOT.as_posix()!r}: {p.as_posix()!r}")
            return p
    raise AuthorizationError(f"successor tuple {(member, cost, hedger_seed)} not in validated successor universe")



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
    # Independent Task-246 prerequisite authentication — must be before implementation binding so tamper is not masked
    authenticated = _get_authenticated_prerequisite_values()
    for field in ("prerequisite_artifact_path", "prerequisite_commit", "prerequisite_canonical_sha256", "prerequisite_raw_sha256", "prerequisite_blob"):
        if field not in payload:
            raise AuthorizationError(f"recovery {field} missing")
        val = payload.get(field)
        if not isinstance(val, str) or not val:
            raise AuthorizationError(f"recovery {field} must be non-empty string, got {repr(val)}")
        if field == "prerequisite_artifact_path":
            if val.replace("\\", "/") != authenticated[field].replace("\\", "/"):
                raise AuthorizationError(f"recovery {field} mismatch: got {val!r} expected {authenticated[field]!r}")
        elif val != authenticated[field]:
            raise AuthorizationError(f"recovery {field} mismatch: got {val!r} expected {authenticated[field]!r}")
    for key in ("retry_permitted", "rerun_permitted", "replacement_permitted"):
        if key not in payload:
            raise AuthorizationError(f"recovery {key} missing — must be explicitly 0")
        val = payload[key]
        if val is None:
            raise AuthorizationError(f"recovery {key} must not be None, must be  int 0")
        if isinstance(val, bool):
            raise AuthorizationError(f"recovery {key} must be int 0, not bool {val!r}")
        if not isinstance(val, int):
            raise AuthorizationError(f"recovery {key} must be int 0, got {type(val).__name__} {val!r}")
        if val != 0:
            raise AuthorizationError(f"recovery {key} must be 0, got {val!r}")
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
    if payload.get("schema_version") not in ("hedging-execution-authorization-v1", "hedging-recovery-authorization-v1"):
        raise AuthorizationError(f"recovery schema_version {payload.get('schema_version')!r} invalid")
