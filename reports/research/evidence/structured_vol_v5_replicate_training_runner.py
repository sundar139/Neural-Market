"""Per-member v5 replicate training runner — orchestration/evidence only.

Fail-closed: allowlist is exactly v5-seed-02..05, member #1 and reserves are
refused, historical generic report path is never used, namespaces are
hash-derived, overwrite and retry are refused, execution_started is
exclusive-create, and --execute requires a tracked/committed authorization
artifact (none exists in task 028, so this runner cannot train even
accidentally). No scientific model/trainer logic is duplicated.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
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

# Schedule-derived expected hashes (frozen at 89fcc9c)
EXPECTED_CONFIG_HASHES = {
    "v5-seed-01": "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157",
    "v5-seed-02": "62c7406cb3a2c64237d39559370d70a27f8111f7dd1dc7ee581da9bd475cf00b",
    "v5-seed-03": "e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955",
    "v5-seed-04": "77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b",
    "v5-seed-05": "1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897",
}
RUN_PREFIXES = {k: v[:16] for k, v in EXPECTED_CONFIG_HASHES.items()}

# Reserve identities (prospective only, unauthorized)
RESERVE_ALLOWLIST: set[str] = set()  # never executable; explicit refuse list below
RESERVE_MEMBERS = {
    "reserve-01",
    "reserve-02",
    "reserve-03",
    "reserve-j01",
    "reserve-j02",
    "reserve-j03",
}

_INVOCATIONS = 0


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
        # untracked file has no HEAD blob
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
    r1 = subprocess.run(
        ["git", "diff", "--quiet", "--", rel], cwd=str(REPO), capture_output=True, check=False
    )
    r2 = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", rel],
        cwd=str(REPO),
        capture_output=True,
        check=False,
    )
    return r1.returncode == 0 and r2.returncode == 0


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_schedule() -> dict[str, Any]:
    if not FROZEN_SCHEDULE_PATH.exists():
        raise RuntimeError(f"frozen schedule missing: {FROZEN_SCHEDULE_PATH}")
    # Verify schedule byte identity via blob (authoritative for tracked text)
    blob = _git_blob(FROZEN_SCHEDULE_PATH)
    if blob != FROZEN_SCHEDULE_BLOB:
        raise RuntimeError(f"schedule blob mismatch: got {blob} expected {FROZEN_SCHEDULE_BLOB}")
    data: dict[str, Any] = json.loads(FROZEN_SCHEDULE_PATH.read_text(encoding="utf-8"))
    return data


def get_member(schedule: dict[str, Any], member_id: str) -> dict[str, Any]:
    for m in schedule.get("primary_members", []):
        if m.get("member_id") == member_id:
            return m  # type: ignore[return-value]
    raise RuntimeError(f"member {member_id!r} not in primary_members")


def derive_effective_config(member_id: str):  # type: ignore[no-untyped-def]
    """Derive effective V5ExperimentConfig for member via frozen derivation."""
    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.data.research.sde_windows import WindowSpec
    from neuralmarket.models.structured_vol_sde import StructuredVolConfig
    from neuralmarket.research.neural_sde_trainer import TrainingConfig
    from neuralmarket.research.neural_sde_trainer_v3 import V3ObjectiveConfig
    from neuralmarket.research.structured_vol_experiment import (
        V5ExperimentConfig,
        load_v5_config,
    )

    schedule = load_schedule()
    member = get_member(schedule, member_id)
    base = load_v5_config(REPO / "configs/research/structured_vol_neural_sde_v5.yaml")
    eff = V5ExperimentConfig(
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
    return eff


def verify_config_hash(member_id: str) -> str:
    eff = derive_effective_config(member_id)
    h = eff.config_hash()
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
        "training": {
            k: v
            for k, v in asdict(eff.training).items()
            if k not in ("model_init_seed", "data_seed")
        },
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
    if (
        not run_prefix
        or len(run_prefix) != 16
        or any(c not in "0123456789abcdef" for c in run_prefix)
    ):
        raise RuntimeError(f"run_prefix must be 16 hex chars: {run_prefix!r}")
    return REPO / "reports/research/structured_vol_v5_replicates" / run_prefix


def derive_model_dir(run_prefix: str) -> Path:
    if (
        not run_prefix
        or len(run_prefix) != 16
        or any(c not in "0123456789abcdef" for c in run_prefix)
    ):
        raise RuntimeError(f"run_prefix must be 16 hex chars: {run_prefix!r}")
    return REPO / "data/processed/research/model/structured-volatility-neural-sde-v5" / run_prefix


def check_no_overwrite(member_id: str) -> tuple[Path, Path]:
    eff = derive_effective_config(member_id)
    prefix = eff.config_hash()[:16]
    # Verify prefix matches scheduled
    if prefix != RUN_PREFIXES[member_id]:
        raise RuntimeError(
            f"prefix mismatch for {member_id}: {prefix} vs {RUN_PREFIXES[member_id]}"
        )
    report_dir = derive_report_dir(prefix)
    model_dir = derive_model_dir(prefix)
    if member_id == "v5-seed-01":
        raise RuntimeError("member v5-seed-01 is EXISTING_FROZEN and cannot be executed")
    if HISTORICAL_GENERIC_REPORT.exists():
        # Runner must never use generic path; this is informational, not a block on training,
        # but we enforce that derived report_dir is not the generic path's parent
        if report_dir == HISTORICAL_GENERIC_REPORT.parent:
            raise RuntimeError("derived report_dir collides with historical generic report parent")
    if report_dir.exists() or model_dir.exists():
        raise RuntimeError(
            f"overwrite refused: report_dir or model_dir already exists ({report_dir}, {model_dir})"
        )
    exec_started = report_dir / "execution_started.json"
    if exec_started.exists():
        raise RuntimeError(f"execution_started already exists: {exec_started}")
    return report_dir, model_dir


def check_authorization(member_id: str, auth_path: Path | None) -> dict[str, Any]:
    if auth_path is None:
        raise RuntimeError("authorization artifact required for --execute; none provided")
    if not auth_path.exists():
        raise RuntimeError(f"authorization artifact missing: {auth_path}")
    # Must be tracked and clean (authoritative blob identity)
    if not _is_tracked(auth_path):
        raise RuntimeError(f"authorization artifact not tracked: {auth_path}")
    if not _is_clean(auth_path):
        raise RuntimeError(f"authorization artifact not clean: {auth_path}")
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    # Minimal field checks
    if data.get("member_id") != member_id:
        raise RuntimeError("authorization member_id mismatch")
    if data.get("full_config_hash") != EXPECTED_CONFIG_HASHES[member_id]:
        raise RuntimeError("authorization full_config_hash mismatch")
    if data.get("run_prefix") != RUN_PREFIXES[member_id]:
        raise RuntimeError("authorization run_prefix mismatch")
    if data.get("family_methodology_identity") != EXPECTED_FAMILY_HASH:
        raise RuntimeError("authorization family_methodology_identity mismatch")
    if not data.get("training_authorized"):
        raise RuntimeError("authorization training_authorized is not true")
    return data


def _runner_self_check() -> None:
    blob = _git_blob(HARNESS_PATH)
    head_blob = _git_head_blob(HARNESS_PATH)
    if head_blob and blob != head_blob:
        raise RuntimeError(
            f"runner blob mismatch: working {blob} vs HEAD {head_blob} (commit first)"
        )
    if not _is_clean(HARNESS_PATH):
        raise RuntimeError("runner has working-tree diff; commit first")


def _exclusive_create_execution_started(report_dir: Path, member_id: str, prefix: str) -> Path:
    # report_dir may already exist from previous mkdir (test: directory exists, file does not)
    # Use file-level exclusive create, not directory creation
    report_dir.mkdir(parents=True, exist_ok=True)
    p = report_dir / "execution_started.json"
    try:
        fp = p.open("x", encoding="utf-8")
    except FileExistsError as e:
        raise RuntimeError(
            f"execution_started already exists (exclusive-create refused): {p}"
        ) from e
    with fp:
        payload = {
            "member_id": member_id,
            "run_prefix": prefix,
            "config_hash": EXPECTED_CONFIG_HASHES[member_id],
            "family_methodology_identity": EXPECTED_FAMILY_HASH,
            "runner_path": HARNESS_PATH.relative_to(REPO).as_posix(),
            "runner_blob": _git_blob(HARNESS_PATH),
            "runner_head_blob": _git_head_blob(HARNESS_PATH),
            "execution_recipe_head": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(REPO),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "start_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "attempt": 1,
        }
        fp.write(json.dumps(payload, indent=2) + "\n")
    return p


def main(argv: list[str] | None = None) -> int:
    global _INVOCATIONS
    parser = argparse.ArgumentParser(
        description="Per-member v5 replicate training runner (fail-closed)"
    )
    parser.add_argument("--member-id", required=True, help="v5-seed-02..05 only")
    parser.add_argument(
        "--authorization", type=str, default=None, help="path to tracked authorization JSON"
    )
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
        print(
            f"REFUSED: member not in allowlist {sorted(ALLOWLIST)}: {member_id!r}", file=sys.stderr
        )
        return 2
    # Historical generic path guard
    if member_id == "historical-generic":
        print("REFUSED: generic historical report path", file=sys.stderr)
        return 2

    _INVOCATIONS += 1
    if _INVOCATIONS > 1:
        raise RuntimeError("training invocation count exceeded 1 per process")

    # Runner self-identity check
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

    # Overwrite refusal
    if report_dir.exists() or model_dir.exists():
        print(
            f"REFUSED: overwrite: report_dir or model_dir exists ({report_dir}, {model_dir})",
            file=sys.stderr,
        )
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

    # Execute requires authorization
    auth_path = Path(args.authorization) if args.authorization else None
    try:
        check_authorization(member_id, auth_path)
    except RuntimeError as e:
        print(f"REFUSED: authorization: {e}", file=sys.stderr)
        return 2

    # Exclusive create execution_started
    try:
        _exclusive_create_execution_started(report_dir, member_id, prefix)
    except RuntimeError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2

    # At this point a future implementation would invoke the scientific training
    # flow exactly once via lower-level internal APIs that cannot touch
    # validation/final_test (train_internal_v3, refit_final_v3, evaluate_gate_v2).
    # That path is not executed in task 028 — we stop after execution_started.
    print(
        f"EXECUTION_STARTED created for {member_id}; scientific training would follow (not in task 028)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
