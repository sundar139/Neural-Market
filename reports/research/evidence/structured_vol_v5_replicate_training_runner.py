"""Per-member v5 replicate training runner — orchestration/evidence only.

Fail-closed: allowlist is exactly v5-seed-02..05, member #1 and reserves are
refused, namespaces are hash-derived, overwrite and retry are refused,
execution_started is exclusive-create, and --execute requires a tracked/
committed authorization artifact binding runner + contract v5 identities.
Exactly one scientific training invocation is reachable and only after the
irreversible start. Terminal evidence is always persisted. No scientific
model/trainer logic is duplicated beyond orchestration glue.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]

# Frozen identities (content, not secrets)
FROZEN_SCHEDULE_PATH = REPO / "reports/research/structured_vol_v5_seed_schedule_v1.json"
FROZEN_SCHEDULE_SHA = (
    "8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0"  # pragma: allowlist secret
)
FROZEN_SCHEDULE_BLOB = "558d08bfee98dbd0c170d65e6a9b1737700c9e98"  # pragma: allowlist secret
EXPECTED_FAMILY_HASH = (
    "730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719"  # pragma: allowlist secret
)
EXPECTED_EVAL_SEED = 8283
FIXED_GATE_SEEDS = {"gate_seed": 7777, "drift_diffusion_seed": 7778, "bootstrap_seed": 8801}
ALLOWLIST = {"v5-seed-02", "v5-seed-03", "v5-seed-04", "v5-seed-05"}
HISTORICAL_GENERIC_REPORT = REPO / "reports/research/structured_vol_v5_report.json"
HARNESS_PATH = REPO / "reports/research/evidence/structured_vol_v5_replicate_training_runner.py"
EXEC_CONTRACT_PATH = REPO / "reports/research/structured_vol_v5_training_execution_contract_v5.json"

# Schedule-derived expected hashes (frozen at 89fcc9c)
EXPECTED_CONFIG_HASHES: dict[str, str] = {
    "v5-seed-01": "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157",
    "v5-seed-02": "62c7406cb3a2c64237d39559370d70a27f8111f7dd1dc7ee581da9bd475cf00b",
    "v5-seed-03": "e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955",
    "v5-seed-04": "77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b",
    "v5-seed-05": "1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897",
}
RUN_PREFIXES: dict[str, str] = {k: v[:16] for k, v in EXPECTED_CONFIG_HASHES.items()}

RESERVE_MEMBERS = {
    "reserve-01",
    "reserve-02",
    "reserve-03",
    "reserve-j01",
    "reserve-j02",
    "reserve-j03",
}

_SCIENTIFIC_INVOCATIONS = 0


def _git_blob(path: Path) -> str:
    r = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git hash-object failed for {path}: {r.stderr.strip()}")
    return r.stdout.strip()


def _git_head_blob(path: Path) -> str:
    rel = path.relative_to(REPO).as_posix()
    r = subprocess.run(
        ["git", "rev-parse", f"HEAD:{rel}"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def _is_tracked(path: Path) -> bool:
    try:
        rel = path.relative_to(REPO).as_posix() if path.is_absolute() else path.as_posix()
    except ValueError:
        return False
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode == 0


def _is_clean(path: Path) -> bool:
    try:
        rel = path.relative_to(REPO).as_posix() if path.is_absolute() else path.as_posix()
    except ValueError:
        return False
    # Working tree vs index only; staged new files are considered clean (tracked, no working edits)
    r1 = subprocess.run(["git", "diff", "--quiet", "--", rel], cwd=str(REPO), capture_output=True, check=False)
    return r1.returncode == 0


def _is_ancestor(ancestor: str, head: str | None = None) -> bool:
    if head is None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip()
    r = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, head], cwd=str(REPO), capture_output=True, check=False)
    return r.returncode == 0


def load_schedule() -> dict[str, Any]:
    if not FROZEN_SCHEDULE_PATH.exists():
        raise RuntimeError(f"frozen schedule missing: {FROZEN_SCHEDULE_PATH}")
    blob = _git_blob(FROZEN_SCHEDULE_PATH)
    if blob != FROZEN_SCHEDULE_BLOB:
        raise RuntimeError(f"schedule blob mismatch: got {blob} expected {FROZEN_SCHEDULE_BLOB}")
    return json.loads(FROZEN_SCHEDULE_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def get_member(schedule: dict[str, Any], member_id: str) -> dict[str, Any]:
    for m in schedule.get("primary_members", []):
        if m.get("member_id") == member_id:
            return m  # type: ignore[return-value]
    raise RuntimeError(f"member {member_id!r} not in primary_members")


def derive_effective_config(member_id: str):  # type: ignore[no-untyped-def]
    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.data.research.sde_windows import WindowSpec
    from neuralmarket.models.structured_vol_sde import StructuredVolConfig
    from neuralmarket.research.neural_sde_trainer import TrainingConfig
    from neuralmarket.research.neural_sde_trainer_v3 import V3ObjectiveConfig
    from neuralmarket.research.structured_vol_experiment import V5ExperimentConfig, load_v5_config

    schedule = load_schedule()
    member = get_member(schedule, member_id)
    base = load_v5_config(REPO / "configs/research/structured_vol_neural_sde_v5.yaml")
    return V5ExperimentConfig(
        version=base.version,
        sde=StructuredVolConfig(**asdict(base.sde)),
        training=TrainingConfig(
            optimizer=base.training.optimizer,
            learning_rate=base.training.learning_rate,
            weight_decay=base.training.weight_decay,
            batch_size=base.training.batch_size,
            max_epochs=base.training.max_epochs,
            patience=base.training.patience,
            grad_norm_clip=base.training.grad_norm_clip,
            model_init_seed=int(member["model_init_seed"]),
            data_seed=int(member["data_seed"]),
            eval_seed=int(member["eval_seed"]),
            fit_fraction=base.training.fit_fraction,
        ),
        windows=WindowSpec(**asdict(base.windows)),
        objective=V3ObjectiveConfig(**asdict(base.objective)),
        n_eval_paths=base.n_eval_paths,
        eval_seed=int(member["eval_seed"]),
        eval_initial_price_convention=base.eval_initial_price_convention,
    )


def verify_config_hash(member_id: str) -> str:
    eff = derive_effective_config(member_id)
    h: str = eff.config_hash()
    exp = EXPECTED_CONFIG_HASHES.get(member_id)
    if exp is None:
        raise RuntimeError(f"no expected hash for {member_id}")
    if h != exp:
        raise RuntimeError(f"config_hash mismatch for {member_id}: got {h} expected {exp}")
    return h


def verify_family_hash(member_id: str) -> str:
    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.data.manifests import canonical_dumps

    eff = derive_effective_config(member_id)
    fam_payload = {
        "version": eff.version,
        "sde": asdict(eff.sde),
        "training": {k: v for k, v in asdict(eff.training).items() if k not in ("model_init_seed", "data_seed")},
        "windows": asdict(eff.windows),
        "objective": asdict(eff.objective),
        "n_eval_paths": eff.n_eval_paths,
        "eval_seed": EXPECTED_EVAL_SEED,
        "eval_initial_price_convention": eff.eval_initial_price_convention,
    }
    h = hashlib.sha256(canonical_dumps(fam_payload).encode()).hexdigest()
    if h != EXPECTED_FAMILY_HASH:
        raise RuntimeError(f"family_methodology_identity mismatch: got {h}")
    return h


def derive_report_dir(run_prefix: str) -> Path:
    if not run_prefix or len(run_prefix) != 16 or any(c not in "0123456789abcdef" for c in run_prefix):
        raise RuntimeError(f"run_prefix must be 16 hex chars: {run_prefix!r}")
    return REPO / "reports/research/structured_vol_v5_replicates" / run_prefix


def derive_model_dir(run_prefix: str) -> Path:
    if not run_prefix or len(run_prefix) != 16 or any(c not in "0123456789abcdef" for c in run_prefix):
        raise RuntimeError(f"run_prefix must be 16 hex chars: {run_prefix!r}")
    return REPO / "data/processed/research/model/structured-volatility-neural-sde-v5" / run_prefix


def check_no_overwrite(member_id: str) -> tuple[Path, Path]:
    eff = derive_effective_config(member_id)
    prefix = eff.config_hash()[:16]
    if prefix != RUN_PREFIXES[member_id]:
        raise RuntimeError(f"prefix mismatch for {member_id}: {prefix} vs {RUN_PREFIXES[member_id]}")
    report_dir = derive_report_dir(prefix)
    model_dir = derive_model_dir(prefix)
    if member_id == "v5-seed-01":
        raise RuntimeError("member v5-seed-01 is EXISTING_FROZEN and cannot be executed")
    if HISTORICAL_GENERIC_REPORT.exists():
        if report_dir == HISTORICAL_GENERIC_REPORT.parent:
            raise RuntimeError("derived report_dir collides with historical generic report parent")
    if report_dir.exists() or model_dir.exists():
        raise RuntimeError(f"overwrite refused: report_dir or model_dir already exists ({report_dir}, {model_dir})")
    if (report_dir / "execution_started.json").exists():
        raise RuntimeError(f"execution_started already exists: {report_dir / 'execution_started.json'}")
    return report_dir, model_dir


REQUIRED_AUTH_FIELDS_V1: list[str] = [
    "schema_version",
    "authorization_task_id",
    "member_id",
    "replicate_seed",
    "model_init_seed",
    "data_seed",
    "eval_seed",
    "full_config_hash",
    "run_prefix",
    "family_methodology_identity",
    "schedule_git_blob",
    "schedule_sha256",
    "execution_contract_git_blob",
    "runner_git_blob",
    "execution_recipe_head",
    "training_authorized",
    "validation_authorized",
    "final_test_authorized",
    "reserve",
    "max_training_invocations",
]
REQUIRED_AUTH_FIELDS_V2: list[str] = REQUIRED_AUTH_FIELDS_V1 + [
    "requested_device",
    "expected_resolved_device",
    "expected_runtime_identity_sha256",
]
# Backwards compat alias for existing tests that import REQUIRED_AUTH_FIELDS
REQUIRED_AUTH_FIELDS: list[str] = REQUIRED_AUTH_FIELDS_V1
ALLOWED_AUTH_SCHEMAS = {
    "structured-vol-v5-primary-training-authorization-v1",
    "structured-vol-v5-primary-training-authorization-v2",
}
EXPECTED_SCHEMA_VERSION = "structured-vol-v5-primary-training-authorization-v1"
EXPECTED_SCHEMA_VERSION_V2 = "structured-vol-v5-primary-training-authorization-v2"
_AUTH_TASK_RE = re.compile(r"^NM-R4-[A-Z0-9][A-Z0-9_\-]*-\d+$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_RUNTIME_SCHEMA_V1 = "runtime-identity-v1"


def check_authorization(member_id: str, auth_path: Path | None) -> dict[str, Any]:
    if auth_path is None:
        raise RuntimeError("authorization artifact required for --execute; none provided")
    if not auth_path.exists():
        raise RuntimeError(f"authorization artifact missing: {auth_path}")
    # Must be inside repository
    try:
        auth_path.resolve().relative_to(REPO.resolve())
    except ValueError:
        raise RuntimeError(f"authorization outside repository: {auth_path}")
    if not _is_tracked(auth_path):
        raise RuntimeError(f"authorization artifact not tracked: {auth_path}")
    # Require HEAD blob exists (committed)
    head_blob = _git_head_blob(auth_path)
    if not head_blob:
        raise RuntimeError(f"authorization not committed (no HEAD blob): {auth_path}")
    # Worktree and index must be clean
    try:
        rel = auth_path.relative_to(REPO).as_posix() if auth_path.is_absolute() else auth_path.as_posix()
    except ValueError:
        rel = auth_path.as_posix()
    r1 = subprocess.run(["git", "diff", "--quiet", "--", rel], cwd=str(REPO), capture_output=True, check=False)
    if r1.returncode != 0:
        raise RuntimeError(f"authorization has unstaged modification: {auth_path}")
    r2 = subprocess.run(["git", "diff", "--cached", "--quiet", "--", rel], cwd=str(REPO), capture_output=True, check=False)
    if r2.returncode != 0:
        raise RuntimeError(f"authorization has staged modification: {auth_path}")
    work_blob = _git_blob(auth_path)
    if work_blob != head_blob:
        raise RuntimeError(f"authorization worktree blob != HEAD blob: {auth_path}")
    data: dict[str, Any] = json.loads(auth_path.read_text(encoding="utf-8"))
    schema = str(data.get("schema_version", ""))
    if schema not in ALLOWED_AUTH_SCHEMAS:
        raise RuntimeError(f"authorization schema_version must be one of {sorted(ALLOWED_AUTH_SCHEMAS)!r}, got {schema!r}")
    is_v2 = schema == EXPECTED_SCHEMA_VERSION_V2
    required = REQUIRED_AUTH_FIELDS_V2 if is_v2 else REQUIRED_AUTH_FIELDS_V1
    for f in required:
        if f not in data:
            raise RuntimeError(f"authorization missing required field: {f}")
    # v1 must not carry v2 device/runtime fields (fail closed — no accidental CUDA opt-in)
    if not is_v2:
        for extra in ("requested_device", "expected_resolved_device", "expected_runtime_identity_sha256"):
            if extra in data:
                raise RuntimeError(f"v1 authorization must not contain {extra}")
    else:
        # v2 device/runtime validation
        req_dev = str(data["requested_device"]).strip().lower()
        exp_res = str(data["expected_resolved_device"]).strip().lower()
        if req_dev not in ("cpu", "cuda"):
            raise RuntimeError(f"requested_device must be cpu or cuda, got {data['requested_device']!r}")
        if exp_res not in ("cpu", "cuda"):
            raise RuntimeError(f"expected_resolved_device must be cpu or cuda, got {data['expected_resolved_device']!r}")
        if req_dev != exp_res:
            raise RuntimeError(f"requested_device {req_dev!r} != expected_resolved_device {exp_res!r}")
        rt_hash = str(data["expected_runtime_identity_sha256"]).strip().lower()
        if not _HEX64_RE.match(rt_hash):
            raise RuntimeError("expected_runtime_identity_sha256 must be 64 lowercase hex")
        # Normalise for downstream comparison
        data["requested_device"] = req_dev
        data["expected_resolved_device"] = exp_res
        data["expected_runtime_identity_sha256"] = rt_hash
        # Optional provenance field, if present must equal runtime-identity-v1
        if "expected_runtime_identity_schema" in data:
            if str(data["expected_runtime_identity_schema"]) != _RUNTIME_SCHEMA_V1:
                raise RuntimeError("expected_runtime_identity_schema must be runtime-identity-v1")
    task_id = data["authorization_task_id"]
    if not isinstance(task_id, str) or not task_id.strip() or not _AUTH_TASK_RE.match(task_id.strip()):
        raise RuntimeError("authorization_task_id must be nonempty and match NM-R4-*-NNN pattern")
    # Type/value checks
    if data["member_id"] != member_id:
        raise RuntimeError("authorization member_id mismatch")
    if data["full_config_hash"] != EXPECTED_CONFIG_HASHES[member_id]:
        raise RuntimeError("authorization full_config_hash mismatch")
    if data["run_prefix"] != RUN_PREFIXES[member_id]:
        raise RuntimeError("authorization run_prefix mismatch")
    if data["family_methodology_identity"] != EXPECTED_FAMILY_HASH:
        raise RuntimeError("authorization family_methodology_identity mismatch")
    # Seed tuple must match schedule
    schedule = load_schedule()
    m = get_member(schedule, member_id)
    if int(data["replicate_seed"]) != int(m["replicate_seed"]):
        raise RuntimeError("authorization replicate_seed mismatch")
    if int(data["model_init_seed"]) != int(m["model_init_seed"]):
        raise RuntimeError("authorization model_init_seed mismatch")
    if int(data["data_seed"]) != int(m["data_seed"]):
        raise RuntimeError("authorization data_seed mismatch")
    if int(data["eval_seed"]) != int(m["eval_seed"]):
        raise RuntimeError("authorization eval_seed mismatch")
    # Blob checks
    if data["schedule_git_blob"] != FROZEN_SCHEDULE_BLOB:
        raise RuntimeError("authorization schedule_git_blob mismatch")
    # Runner blob must match current tracked runner blob
    current_runner_blob = _git_blob(HARNESS_PATH)
    if data["runner_git_blob"] != current_runner_blob:
        raise RuntimeError(f"authorization runner_git_blob mismatch: auth {data['runner_git_blob']} vs current {current_runner_blob}")
    head_runner_blob = _git_head_blob(HARNESS_PATH)
    if not head_runner_blob:
        raise RuntimeError("runner has no HEAD blob (not committed)")
    if current_runner_blob != head_runner_blob:
        raise RuntimeError("runner blob mismatch: working vs HEAD (commit first)")
    # Contract v5 blob must match current tracked contract v5 (unconditional)
    if not EXEC_CONTRACT_PATH.exists():
        raise RuntimeError(f"current execution contract missing: {EXEC_CONTRACT_PATH}")
    if not _is_tracked(EXEC_CONTRACT_PATH):
        raise RuntimeError(f"current execution contract not tracked: {EXEC_CONTRACT_PATH}")
    head_contract_blob = _git_head_blob(EXEC_CONTRACT_PATH)
    if not head_contract_blob:
        raise RuntimeError(f"current execution contract not committed: {EXEC_CONTRACT_PATH}")
    if not _is_clean(EXEC_CONTRACT_PATH):
        raise RuntimeError(f"current execution contract not clean: {EXEC_CONTRACT_PATH}")
    current_contract_blob = _git_blob(EXEC_CONTRACT_PATH)
    if current_contract_blob != head_contract_blob:
        raise RuntimeError(f"current execution contract worktree != HEAD: {EXEC_CONTRACT_PATH}")
    if data["execution_contract_git_blob"] != current_contract_blob:
        raise RuntimeError("authorization execution_contract_git_blob mismatch")
    # Schedule SHA check (allow local_worktree_sha256 alias)
    sched_sha_key = "schedule_sha256" if "schedule_sha256" in data else "local_worktree_sha256" if "local_worktree_sha256" in data else None
    if sched_sha_key is None:
        raise RuntimeError("authorization missing schedule_sha256 / local_worktree_sha256")
    if data[sched_sha_key] != FROZEN_SCHEDULE_SHA:
        raise RuntimeError("authorization schedule_sha256 mismatch")
    # Recipe head must be ancestor of current HEAD and must be non-empty
    recipe_head: str = str(data["execution_recipe_head"])
    if not recipe_head or len(recipe_head) != 40 or any(c not in "0123456789abcdef" for c in recipe_head):
        raise RuntimeError("authorization execution_recipe_head invalid")
    if not _is_ancestor(recipe_head):
        raise RuntimeError("authorization execution_recipe_head is not ancestor of HEAD")
    # Recipe must contain runner, contract v5, and schedule at their authorized blobs
    for rel_path, expected_blob_key in [
        (HARNESS_PATH.relative_to(REPO).as_posix(), "runner_git_blob"),
        (EXEC_CONTRACT_PATH.relative_to(REPO).as_posix(), "execution_contract_git_blob"),
        (FROZEN_SCHEDULE_PATH.relative_to(REPO).as_posix(), "schedule_git_blob"),
    ]:
        r = subprocess.run(
            ["git", "rev-parse", f"{recipe_head}:{rel_path}"],
            cwd=str(REPO), capture_output=True, text=True, check=False,
        )
        if r.returncode != 0:
            raise RuntimeError(f"recipe commit missing {rel_path}")
        if r.stdout.strip() != str(data[expected_blob_key]):
            raise RuntimeError(f"recipe {rel_path} blob mismatch")
    # Firewall fields
    if data["training_authorized"] is not True:
        raise RuntimeError("authorization training_authorized must be true")
    if data["validation_authorized"] is not False:
        raise RuntimeError("authorization validation_authorized must be false")
    if data["final_test_authorized"] is not False:
        raise RuntimeError("authorization final_test_authorized must be false")
    if data["reserve"] is not False:
        raise RuntimeError("authorization reserve must be false")
    if data["max_training_invocations"] != 1:
        raise RuntimeError("authorization max_training_invocations must be 1")
    return data


def _runner_self_check() -> None:
    if not _is_tracked(HARNESS_PATH):
        raise RuntimeError("runner not tracked (git ls-files)")
    head_blob = _git_head_blob(HARNESS_PATH)
    if not head_blob:
        raise RuntimeError("runner has no HEAD blob (commit first)")
    blob = _git_blob(HARNESS_PATH)
    if blob != head_blob:
        raise RuntimeError(f"runner blob mismatch: working {blob} vs HEAD {head_blob} (commit first)")
    if not _is_clean(HARNESS_PATH):
        raise RuntimeError("runner has working-tree diff; commit first")


def _exclusive_create_execution_started(
    report_dir: Path,
    member_id: str,
    prefix: str,
    auth_data: dict[str, Any],
    auth_path: Path,
    *,
    requested_device: str = "cpu",
    resolved_device: str = "cpu",
    runtime_identity: dict[str, Any] | None = None,
) -> Path:
    # Build complete payload in memory first (complete-or-absent semantics)
    ec_blob = _git_blob(EXEC_CONTRACT_PATH)
    # Normalise device fields for evidence
    req_dev = str(requested_device).strip().lower() if requested_device else "cpu"
    res_dev = str(resolved_device).strip().lower() if resolved_device else req_dev
    rt_payload = runtime_identity if runtime_identity is not None else {}
    rt_sha = str(rt_payload.get("runtime_identity_sha256", "")) if rt_payload else ""
    rt_schema = str(rt_payload.get("schema_version", _RUNTIME_SCHEMA_V1)) if rt_payload else _RUNTIME_SCHEMA_V1
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "member_id": member_id,
        "replicate_seed": int(auth_data["replicate_seed"]),
        "model_init_seed": int(auth_data["model_init_seed"]),
        "data_seed": int(auth_data["data_seed"]),
        "eval_seed": int(auth_data["eval_seed"]),
        "full_config_hash": EXPECTED_CONFIG_HASHES[member_id],
        "run_prefix": prefix,
        "family_methodology_identity": EXPECTED_FAMILY_HASH,
        "runner_git_blob": _git_blob(HARNESS_PATH),
        "execution_contract_git_blob": ec_blob,
        "schedule_git_blob": FROZEN_SCHEDULE_BLOB,
        "schedule_sha256": FROZEN_SCHEDULE_SHA,
        "execution_recipe_head": str(auth_data["execution_recipe_head"]),
        "authorization_path": auth_path.relative_to(REPO).as_posix() if auth_path.is_absolute() else auth_path.as_posix(),
        "authorization_git_blob": _git_blob(auth_path),
        "authorization_schema_version": str(auth_data.get("schema_version", "")),
        "requested_device": req_dev,
        "resolved_device": res_dev,
        "runtime_identity_schema": rt_schema,
        "runtime_identity_sha256": rt_sha,
        "runtime_identity": rt_payload if rt_payload else None,
        "start_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "attempt_number": 1,
        "training_invocations_before_start": _SCIENTIFIC_INVOCATIONS,
        "validation_authorized": False,
        "final_test_authorized": False,
        "reserve": False,
    }
    serialized = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    # Create report directory, then atomically publish via temp file + hard link
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / "execution_started.json"
    if p.exists():
        raise RuntimeError(f"execution_started already exists: {p}")
    tmp_path = report_dir / f".execution_started.tmp.{os.getpid()}"
    try:
        tmp_path.write_bytes(serialized)
        tmp_path.chmod(0o644)
        # Flush and fsync before publish
        with tmp_path.open("r+b") as f:
            f.flush()
            os.fsync(f.fileno())
        # Atomic exclusive publish: hard link (fails if dest exists)
        try:
            os.link(str(tmp_path), str(p))
        except FileExistsError as e:
            raise RuntimeError(f"execution_started already exists (exclusive-create refused): {p}") from e
        except OSError:
            # Hard link not available (cross-device) — fail closed rather than overwrite
            raise RuntimeError(f"atomic publish unavailable for {p}")
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
    return p


def _run_scientific_training(
    member_id: str,
    report_dir: Path,
    model_dir: Path,
    *,
    device: torch.device | None = None,
) -> dict[str, Any]:
    """Single reachable scientific training orchestration (thin glue over existing helpers).

    Calls the accepted training-only flow: training series -> windows/normalizer ->
    statistics -> train_internal_v3 -> checkpoint/curve -> refit -> Gate-v2.
    Must be called exactly once per process and only after execution_started.
    """
    global _SCIENTIFIC_INVOCATIONS
    if _SCIENTIFIC_INVOCATIONS >= 1:
        raise RuntimeError("scientific_training_invocations exceeded 1")
    _SCIENTIFIC_INVOCATIONS += 1

    # Lazy imports — reuse existing production helpers, no duplication
    sys.path.insert(0, str(REPO / "src"))
    import numpy as np
    import torch
    from neuralmarket.data.manifests import canonical_dumps
    from neuralmarket.data.research.inventory import ResearchInventory
    from neuralmarket.data.research.sde_windows import (
        build_windows,
        compute_context_features,
        fit_cumret_scale,
        fit_feature_normalizer,
        split_fit_selection,
    )
    from neuralmarket.data.research.underlying import build_underlying_series
    from neuralmarket.models.neural_sde import configure_determinism, count_parameters, set_deterministic_seeds
    from neuralmarket.models.structured_vol_sde import StructuredVolatilityNeuralSde

    from neuralmarket.research.neural_sde_internal_gate import evaluate_gate_v2, load_gate_spec_v2
    from neuralmarket.research.neural_sde_trainer_v3 import build_v3_statistics, refit_final_v3, train_internal_v3

    eff = derive_effective_config(member_id)
    config_hash: str = eff.config_hash()
    prefix = config_hash[:16]

    # Paths
    inventory_path = REPO / "data/manifests/research_development_inventory_v1.json"
    raw_root = REPO / "data/raw/databento"
    processed_root = REPO / "data/processed"
    gate_yaml = REPO / "configs/research/neural_sde_internal_gate_v2.yaml"

    inventory = ResearchInventory.model_validate(json.loads(inventory_path.read_text(encoding="utf-8")))
    training_series = build_underlying_series(inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root)
    training_returns = training_series.returns_array
    training_series_sha = training_series.series_sha256
    session_dates = training_series.session_dates
    return_dates = tuple(session_dates[1:])
    spec = eff.windows
    windows = build_windows(training_returns, return_dates, spec)
    feature_matrix = __import__("numpy").stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    cumret_scale = fit_cumret_scale(training_returns, spec.horizon)
    split = split_fit_selection(windows, eff.training.fit_fraction, spec)
    fit_count = split.n_fit
    sel_count = split.n_selection
    statistics = build_v3_statistics(split.fit_windows, normalizer, cumret_scale, spec, eff.objective)

    # Device is threaded from the runner — single resolved device, no scatter
    if device is None:
        device = torch.device("cpu")
    dtype = torch.float32
    configure_determinism(True)
    # Reuse device helper determinism as well (idempotent)
    try:
        from neuralmarket.core.device import configure_device_determinism as _cfg_dev_det

        _cfg_dev_det(device, enabled=True)
    except Exception:
        pass
    set_deterministic_seeds(int(eff.training.model_init_seed))
    model = StructuredVolatilityNeuralSde(eff.sde).to(device=device, dtype=dtype)
    _ = count_parameters(model)
    training_returns_tensor = torch.tensor(training_returns, dtype=dtype, device=device)
    training_start_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    outcome = train_internal_v3(
        model, eff.training, split, normalizer, training_returns_tensor, statistics, spec, eff.objective, device=device
    )
    training_end_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    gate_spec = load_gate_spec_v2(str(gate_yaml))
    gate_diagnostics, gate_passed = evaluate_gate_v2(model, split, normalizer, training_returns_tensor, spec, gate_spec)

    # Persist selected checkpoint + curve into model_dir/report_dir
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = model_dir / "checkpoint.pt"
    torch.save({"model_state": {k: v.cpu() for k, v in model.state_dict().items()}, "sde_config": asdict(eff.sde)}, checkpoint_path)
    checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()

    curve_path = model_dir / "training_curve.json"
    curve_data = {
        "rbf_curve": outcome.rbf_curve,
        "total_curve": outcome.total_curve,
        "selection_rbf_curve": outcome.selection_rbf_curve,
        "selection_total_curve": outcome.selection_total_curve,
        "initial_internal_rbf": outcome.initial_internal_rbf,
        "best_internal_rbf": outcome.best_internal_rbf,
        "best_epoch": outcome.best_epoch,
    }
    curve_path.write_text(canonical_dumps(curve_data) + "\n", encoding="utf-8")
    curve_sha = hashlib.sha256(curve_path.read_bytes()).hexdigest()

    if gate_passed:
        set_deterministic_seeds(int(eff.training.model_init_seed))
        final_model = StructuredVolatilityNeuralSde(eff.sde).to(device=device, dtype=dtype)
        refit_final_v3(
            final_model,
            eff.training,
            windows,
            normalizer,
            training_returns_tensor,
            outcome.best_epoch,
            statistics,
            spec,
            eff.objective,
            device=device,
        )
        final_path = model_dir / "checkpoint_final.pt"
        torch.save(
            {"model_state": {k: v.cpu() for k, v in final_model.state_dict().items()}, "sde_config": asdict(eff.sde)}, final_path
        )
        final_sha = hashlib.sha256(final_path.read_bytes()).hexdigest()
    else:
        final_path = None
        final_sha = None

    return {
        "config_hash": config_hash,
        "run_prefix": prefix,
        "training_series_sha256": training_series_sha,
        "fit_window_count": fit_count,
        "selection_window_count": sel_count,
        "all_training_window_count": len(windows),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "curve_path": str(curve_path),
        "curve_sha256": curve_sha,
        "final_checkpoint_path": str(final_path) if final_path else None,
        "final_checkpoint_sha256": final_sha,
        "gate_diagnostics": gate_diagnostics,
        "gate_passed": gate_passed,
        "best_epoch": outcome.best_epoch,
        "final_epoch": outcome.final_epoch,
        "initial_internal_rbf": outcome.initial_internal_rbf,
        "best_internal_rbf": outcome.best_internal_rbf,
        "initial_selection_total": float(outcome.selection_total_curve[0]) if outcome.selection_total_curve else None,
        "best_selection_total": float(outcome.selection_total_curve[outcome.best_epoch - 1]) if outcome.best_epoch > 0 and len(outcome.selection_total_curve) >= outcome.best_epoch else None,
        "training_start_utc": training_start_utc,
        "training_end_utc": training_end_utc,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Per-member v5 replicate training runner (fail-closed)")
    parser.add_argument("--member-id", required=True, help="v5-seed-02..05 only")
    parser.add_argument("--authorization", type=str, default=None, help="path to tracked authorization JSON")
    parser.add_argument("--execute", action="store_true", help="execute (default is dry-run)")
    args = parser.parse_args(argv)

    member_id: str = args.member_id

    # Hard refuse: reserves and seed-01
    if member_id in RESERVE_MEMBERS:
        print(f"REFUSED: reserve execution not authorized: {member_id}", file=sys.stderr)
        return 2
    if member_id == "v5-seed-01":
        print("REFUSED: v5-seed-01 is EXISTING_FROZEN", file=sys.stderr)
        return 2
    if member_id not in ALLOWLIST:
        print(f"REFUSED: member not in allowlist {sorted(ALLOWLIST)}: {member_id!r}", file=sys.stderr)
        return 2

    # Runner self-identity check (must be tracked, has HEAD blob, clean)
    try:
        _runner_self_check()
    except RuntimeError as e:
        print(f"REFUSED: runner identity: {e}", file=sys.stderr)
        return 2

    # Load schedule and derive config
    try:
        schedule = load_schedule()
        _ = get_member(schedule, member_id)
        cfg_hash = verify_config_hash(member_id)
        verify_family_hash(member_id)
        prefix = cfg_hash[:16]
        report_dir = derive_report_dir(prefix)
        model_dir = derive_model_dir(prefix)
    except RuntimeError as e:
        print(f"REFUSED: preflight: {e}", file=sys.stderr)
        return 2

    # Overwrite refusal (must be absent)
    if report_dir.exists() or model_dir.exists():
        print(f"REFUSED: overwrite: report_dir or model_dir exists ({report_dir}, {model_dir})", file=sys.stderr)
        return 2
    if (report_dir / "execution_started.json").exists():
        print("REFUSED: execution_started already exists", file=sys.stderr)
        return 2

    # Dry run
    if not args.execute:
        print(
            f"DRY RUN OK: {member_id} prefix {prefix} hash {cfg_hash} report_dir {report_dir} model_dir {model_dir}"
        )
        print(f"family {EXPECTED_FAMILY_HASH} eval {EXPECTED_EVAL_SEED} gate {FIXED_GATE_SEEDS}")
        return 0

    # Execute requires authorization — enforce all fields (v1: 20, v2: 23)
    auth_path = Path(args.authorization) if args.authorization else None
    try:
        auth_data = check_authorization(member_id, auth_path)
    except RuntimeError as e:
        print(f"REFUSED: authorization: ***", file=sys.stderr)
        return 2

    # Prospective v2 pre-marker device/runtime enforcement (ordering is load-bearing)
    # 1. Read requested_device (v1 defaults to cpu, never CUDA)
    auth_schema = str(auth_data.get("schema_version", ""))
    is_v2 = auth_schema == EXPECTED_SCHEMA_VERSION_V2
    if is_v2:
        requested_device = str(auth_data["requested_device"]).strip().lower()
        expected_resolved = str(auth_data["expected_resolved_device"]).strip().lower()
        expected_rt_sha = str(auth_data["expected_runtime_identity_sha256"]).strip().lower()
    else:
        requested_device = "cpu"
        expected_resolved = "cpu"
        expected_rt_sha = ""

    # 2. Resolve device (fail closed, no CPU fallback)
    try:
        sys.path.insert(0, str(REPO / "src"))
        from neuralmarket.core.device import configure_device_determinism, resolve_device
        from neuralmarket.core.runtime_identity import build_runtime_identity

        resolved = resolve_device(requested_device)
        resolved_str = str(resolved)
        # Normalise torch.device str: 'cuda' may resolve to 'cuda' (not 'cuda:0')
        # Keep as returned by resolve_device.
    except (RuntimeError, ValueError) as e:
        print(f"REFUSED: device preflight: {e}", file=sys.stderr)
        return 2

    # 3. Configure determinism for the resolved device
    try:
        configure_device_determinism(resolved, enabled=True)
    except Exception as e:
        print(f"REFUSED: determinism preflight: {e}", file=sys.stderr)
        return 2

    # 4. Build observed runtime identity at the single normative capture point
    try:
        observed_rt = build_runtime_identity(requested_device=requested_device, resolved_device=resolved_str)
        observed_sha = str(observed_rt.get("runtime_identity_sha256", ""))
        observed_resolved = str(observed_rt.get("resolved_device", "")).strip().lower()
    except Exception as e:
        print(f"REFUSED: runtime identity preflight: {e}", file=sys.stderr)
        return 2

    # 5. Enforce v2 binding before any irreversible publication
    if is_v2:
        if observed_resolved != expected_resolved:
            print(
                f"REFUSED: resolved device mismatch: observed {observed_resolved!r} != expected {expected_resolved!r}",
                file=sys.stderr,
            )
            return 2
        if observed_sha.lower() != expected_rt_sha.lower():
            print("REFUSED: runtime identity mismatch", file=sys.stderr)
            return 2
    else:
        # v1 is CPU-only: if observed resolved is cuda, something is wrong — but v1
        # without requested CUDA should have resolved to cpu. Guard anyway.
        if observed_resolved == "cuda" and requested_device == "cpu":
            # This cannot happen if resolve_device was given 'cpu', but guard for
            # any future path that might mis-resolve. Fail closed.
            print("REFUSED: v1 authorization cannot resolve to cuda", file=sys.stderr)
            return 2

    # Exclusive create execution_started (irreversible start) — only after every check
    try:
        execution_started_path = _exclusive_create_execution_started(
            report_dir,
            member_id,
            prefix,
            auth_data,
            auth_path,  # type: ignore[arg-type]
            requested_device=requested_device,
            resolved_device=resolved_str,
            runtime_identity=observed_rt,
        )
    except RuntimeError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"REFUSED: execution_started failed: {e}", file=sys.stderr)
        return 2

    # From here, member is ATTEMPTED — terminal evidence must always be persisted
    stdout_buf = io.StringIO()
    start_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status: str | None = None
    failure_category: str | None = None
    exit_code: int | None = None
    exc_info: str | None = None
    exc_class: str | None = None
    training_result: dict[str, Any] | None = None
    _terminal_success = False

    # Capture stdout/stderr into buffer while training runs
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stdout_buf  # type: ignore[assignment]
    sys.stderr = stdout_buf  # type: ignore[assignment]
    # Use a helper to guarantee terminal evidence even for BaseException,
    # without returning from inside finally (which would swallow BaseException).
    def _persist_terminal(exit_code_val: int, status_val: str) -> int:
        end_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        transcript = stdout_buf.getvalue()
        try:
            (report_dir / "training_stdout.log").write_text(transcript, encoding="utf-8")
        except Exception:
            pass
        try:
            (report_dir / "training_exit_code.txt").write_text(str(exit_code_val) + "\n", encoding="utf-8")
        except Exception:
            pass
        manifest: dict[str, Any] = {
            "schema_version": "1.0",
            "member_id": member_id,
            "run_prefix": prefix,
            "config_hash": EXPECTED_CONFIG_HASHES[member_id],
            "family_methodology_identity": EXPECTED_FAMILY_HASH,
            "runner_git_blob": _git_blob(HARNESS_PATH),
            "runner_head_blob": _git_head_blob(HARNESS_PATH),
            "execution_contract_git_blob": _git_blob(EXEC_CONTRACT_PATH),
            "schedule_git_blob": FROZEN_SCHEDULE_BLOB,
            "authorization_path": auth_path.relative_to(REPO).as_posix() if auth_path and auth_path.is_absolute() else (str(auth_path) if auth_path else None),
            "authorization_git_blob": _git_blob(auth_path) if auth_path and auth_path.exists() else None,
            "authorization_schema_version": str(auth_data.get("schema_version", "")),
            "requested_device": str(observed_rt.get("requested_device", requested_device)) if "observed_rt" in locals() else requested_device,
            "resolved_device": str(observed_rt.get("resolved_device", resolved_str)) if "observed_rt" in locals() else resolved_str,
            "runtime_identity_schema": str(observed_rt.get("schema_version", _RUNTIME_SCHEMA_V1)) if "observed_rt" in locals() and observed_rt else _RUNTIME_SCHEMA_V1,
            "runtime_identity_sha256": str(observed_rt.get("runtime_identity_sha256", "")) if "observed_rt" in locals() and observed_rt else "",
            "runtime_identity": observed_rt if "observed_rt" in locals() else None,
            "execution_started_path": str(execution_started_path),
            "start_utc": start_utc,
            "end_utc": end_utc,
            "terminal_status": status_val,
            "failure_category": failure_category,
            "exit_code": exit_code_val,
            "exception_class": exc_class,
            "failure_reason": exc_info,
            "scientific_training_invocations": _SCIENTIFIC_INVOCATIONS,
            "validation_constructions": 0,
            "external_evaluations": 0,
            "final_test_accesses": 0,
            "provider_calls": 0,
            "network_calls": 0,
        }
        for name in ["training_stdout.log", "training_exit_code.txt", "execution_started.json"]:
            p2 = report_dir / name
            if p2.exists():
                try:
                    manifest[f"{name}_sha256"] = hashlib.sha256(p2.read_bytes()).hexdigest()
                except Exception:
                    pass
        if training_result is not None:
            # Always persist scientific evidence, even on GATE_V2_FAILED
            for k in ["checkpoint_path", "checkpoint_sha256", "curve_path", "curve_sha256", "final_checkpoint_path", "final_checkpoint_sha256", "gate_diagnostics", "gate_passed", "best_epoch", "final_epoch", "initial_internal_rbf", "best_internal_rbf", "initial_selection_total", "best_selection_total", "training_series_sha256", "fit_window_count", "selection_window_count", "training_start_utc", "training_end_utc"]:
                if k in training_result and training_result[k] is not None:
                    manifest[k] = training_result[k]
            # Gate seeds always
            manifest["gate_seed"] = FIXED_GATE_SEEDS["gate_seed"]
            manifest["drift_diffusion_seed"] = FIXED_GATE_SEEDS["drift_diffusion_seed"]
            manifest["bootstrap_seed"] = FIXED_GATE_SEEDS["bootstrap_seed"]
            if status_val == "COMPLETED":
                report_path = report_dir / "training_report.json"
                try:
                    # Full member evidence per Amendment 025 §6 — no invented values
                    eff2 = derive_effective_config(member_id)
                    repo_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip()
                    report: dict[str, Any] = {
                        "schema_version": "1.0",
                        "member_id": member_id,
                        "replicate_seed": int(auth_data["replicate_seed"]),
                        "model_init_seed": int(auth_data["model_init_seed"]),
                        "data_seed": int(auth_data["data_seed"]),
                        "eval_seed": int(auth_data["eval_seed"]),
                        "execution_head": repo_head,
                        "scientific_source_commit": "357971a67c68492fc0c4f5bf31f94f9685639f65",
                        "runner_git_blob": _git_blob(HARNESS_PATH),
                        "execution_contract_git_blob": _git_blob(EXEC_CONTRACT_PATH),
                        "authorization_git_blob": _git_blob(auth_path) if auth_path and auth_path.exists() else None,
                        "authorization_schema_version": str(auth_data.get("schema_version", "")),
                        "requested_device": str(observed_rt.get("requested_device", requested_device)) if "observed_rt" in locals() else requested_device,
                        "resolved_device": str(observed_rt.get("resolved_device", resolved_str)) if "observed_rt" in locals() else resolved_str,
                        "runtime_identity_schema": str(observed_rt.get("schema_version", _RUNTIME_SCHEMA_V1)) if "observed_rt" in locals() and observed_rt else _RUNTIME_SCHEMA_V1,
                        "runtime_identity_sha256": str(observed_rt.get("runtime_identity_sha256", "")) if "observed_rt" in locals() and observed_rt else "",
                        "runtime_identity": observed_rt if "observed_rt" in locals() else None,
                        "execution_recipe_head": str(auth_data["execution_recipe_head"]),
                        "python_version": sys.version,
                        "pytorch_version": __import__("torch").__version__,
                        "device": str(observed_rt.get("resolved_device", resolved_str)) if "observed_rt" in locals() else resolved_str,
                        "determinism": {"torch_deterministic": True, "cudnn_benchmark": False, "cudnn_deterministic": True},
                        "effective_config": {
                            "version": eff2.version,
                            "sde": asdict(eff2.sde),
                            "training": asdict(eff2.training),
                            "windows": asdict(eff2.windows),
                            "objective": asdict(eff2.objective),
                            "n_eval_paths": eff2.n_eval_paths,
                            "eval_seed": eff2.eval_seed,
                            "eval_initial_price_convention": eff2.eval_initial_price_convention,
                        },
                        "full_config_hash": EXPECTED_CONFIG_HASHES[member_id],
                        "run_prefix": prefix,
                        "family_methodology_identity": EXPECTED_FAMILY_HASH,
                        "training_series_sha256": training_result.get("training_series_sha256"),
                        "fit_window_count": training_result.get("fit_window_count"),
                        "selection_window_count": training_result.get("selection_window_count"),
                        "training_report_created_utc": end_utc,
                        "gate_diagnostics": training_result.get("gate_diagnostics"),
                        "gate_passed": training_result.get("gate_passed"),
                        "gate_seed": FIXED_GATE_SEEDS["gate_seed"],
                        "drift_diffusion_seed": FIXED_GATE_SEEDS["drift_diffusion_seed"],
                        "bootstrap_seed": FIXED_GATE_SEEDS["bootstrap_seed"],
                        "terminal_status": status_val,
                        "failure_category": failure_category,
                        "manifest_path": str(report_dir / "training_execution_manifest.json"),
                    }
                    for k2 in ["initial_internal_rbf", "best_internal_rbf", "initial_selection_total", "best_selection_total", "best_epoch", "final_epoch", "checkpoint_path", "checkpoint_sha256", "curve_path", "curve_sha256", "final_checkpoint_path", "final_checkpoint_sha256", "training_start_utc", "training_end_utc"]:
                        if k2 in training_result and training_result[k2] is not None:
                            report[k2] = training_result[k2]
                    report["scientific_training_invocations"] = _SCIENTIFIC_INVOCATIONS
                    report["validation_constructions"] = 0
                    report["external_evaluations"] = 0
                    report["final_test_accesses"] = 0
                    report["provider_calls"] = 0
                    report["network_calls"] = 0
                    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                    manifest["training_report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
                except Exception as e:
                    manifest["training_report_error"] = str(e)[:500]
        manifest_path = report_dir / "training_execution_manifest.json"
        try:
            with manifest_path.open("x", encoding="utf-8") as fp:
                fp.write(json.dumps(manifest, indent=2) + "\n")
        except FileExistsError:
            try:
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass
        except Exception:
            try:
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass
        return exit_code_val

    pending_exc: BaseException | None = None
    try:
        training_result = _run_scientific_training(member_id, report_dir, model_dir, device=resolved)
        # Gate-v2 failure is terminal FAILED (not COMPLETED) — exit 3
        gate_passed = bool(training_result.get("gate_passed", True)) if training_result else True
        if not gate_passed:
            failure_category = "GATE_V2_FAILED"
            status = "FAILED"
            exit_code = 3
            exc_class = "GateV2Failed"
            exc_info = "frozen Gate-v2 returned gate_passed=false"
        else:
            status = "COMPLETED"
            failure_category = None
            exit_code = 0
    except BaseException as e:
        # Capture BaseException (including KeyboardInterrupt/SystemExit) without swallowing
        if isinstance(e, Exception):
            exc_class = type(e).__name__
            exc_info = "".join(traceback.format_exception_only(type(e), e)).strip()[:2000]
            failure_category = "EXCEPTION"
        else:
            exc_class = type(e).__name__
            exc_info = str(e)[:2000] if str(e) else type(e).__name__
            failure_category = "BASE_EXCEPTION"
        status = "FAILED"
        exit_code = 1
        print(f"FAILURE: {exc_class}: {exc_info}", file=stdout_buf)
        # For BaseException, re-raise after persisting terminal evidence
        if not isinstance(e, Exception):
            pending_exc = e
    finally:
        # Restore std streams before persisting (so manifest writes go to real stdout)
        sys.stdout = old_stdout  # type: ignore[assignment]
        sys.stderr = old_stderr  # type: ignore[assignment]
        # Best-effort terminal persistence; never swallow pending BaseException
        try:
            exit_code_to_persist = exit_code if exit_code is not None else 1
            status_to_persist = status if status is not None else "FAILED"
            _persist_terminal(exit_code_to_persist, status_to_persist)
        except BaseException:
            if pending_exc is None:
                raise
        if pending_exc is not None:
            raise pending_exc

    return exit_code if exit_code is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
