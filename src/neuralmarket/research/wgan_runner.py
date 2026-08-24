"""Fail-closed future runner boundary for the frozen WGAN comparator.

Dry-run performs readiness checks only.  The execute path requires a later
committed authorization, CUDA, matching implementation/provenance identities,
and one exclusive execution marker before any scientific training call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from neuralmarket.core.device import configure_device_determinism, resolve_device
from neuralmarket.core.runtime_identity import build_runtime_identity
from neuralmarket.research.wgan_comparator import (
    AMENDMENT_060_SHA256,
    WGAN_PREREGISTRATION_SHA256,
    WGANTrainingConfig,
    WGANTrainingOutcome,
    prepare_wgan_training_data,
    refit_wgan,
    train_wgan_internal,
)

PREREGISTRATION_SHA256 = WGAN_PREREGISTRATION_SHA256

REPO = Path(__file__).resolve().parents[3]
PREREGISTRATION_PATH = REPO / (
    "reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json"
)
AMENDMENT_060_PATH = REPO / "reports/protocol/research_protocol_amendment_060.md"
RUNTIME_CONFIG_PATH = REPO / "configs/research/structured_vol_wgan_comparator_v1.yaml"
EXECUTION_CONTRACT_PATH = REPO / (
    "reports/research/structured_vol_v5_wgan_execution_contract_v1.json"
)
SEED_SCHEDULE_PATH = REPO / "reports/research/structured_vol_v5_seed_schedule_v1.json"
MODEL_SOURCE_PATH = REPO / "src/neuralmarket/models/wgan_cde.py"
COMPARATOR_SOURCE_PATH = REPO / "src/neuralmarket/research/wgan_comparator.py"
RUNNER_SOURCE_PATH = REPO / "src/neuralmarket/research/wgan_runner.py"
WGAN_RUN_ROOT = REPO / "reports/research/wgan_comparator_runs"
PREREGISTRATION_BLOB = "72311888542ee83ff497b5f0adbbaf6429e8452a"
AMENDMENT_060_BLOB = "a1ba052abe8b4a50887ec84b934e16a328e60596"
SEED_SCHEDULE_SHA256 = "8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0"
SEED_SCHEDULE_BLOB = "558d08bfee98dbd0c170d65e6a9b1737700c9e98"
PRIMARY_MEMBER_IDS = tuple(f"wgan-seed-0{i}" for i in range(1, 6))
RESERVE_MEMBER_IDS = ("reserve-wgan-j01", "reserve-wgan-j02", "reserve-wgan-j03")
AUTO_RESERVE_CHAIN = False
WGAN_TRAINING_DIAGNOSTIC_SCHEMA = "structured-vol-v5-wgan-training-diagnostics-v1"
DIAGNOSTIC_PRESENT = "PRESENT"
DIAGNOSTIC_MISSING_BY_DESIGN_HISTORICAL = "MISSING_BY_DESIGN_HISTORICAL"
DIAGNOSTIC_NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE = (
    "NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE"
)

_SEED_TUPLES: dict[str, tuple[int, int, int, int]] = {
    "wgan-seed-01": (8281, 8281, 8282, 8283),
    "wgan-seed-02": (9281, 9281, 9282, 8283),
    "wgan-seed-03": (10281, 10281, 10282, 8283),
    "wgan-seed-04": (11281, 11281, 11282, 8283),
    "wgan-seed-05": (12281, 12281, 12282, 8283),
    "reserve-wgan-j01": (13281, 13281, 13282, 8283),
    "reserve-wgan-j02": (14281, 14281, 14282, 8283),
    "reserve-wgan-j03": (15281, 15281, 15282, 8283),
}


def _git_blob(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git hash-object failed for {path}")
    return result.stdout.strip()


def _git_head_blob(path: Path) -> str:
    relative = path.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "rev-parse", f"HEAD:{relative}"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _is_tracked(path: Path) -> bool:
    relative = path.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _is_clean(path: Path) -> bool:
    relative = path.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", relative], cwd=str(REPO), capture_output=True, check=False
    )
    return result.returncode == 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_execution_contract() -> dict[str, Any]:
    """Load and verify the tracked frozen execution contract inputs."""
    if not EXECUTION_CONTRACT_PATH.is_file():
        raise RuntimeError(f"execution contract missing: {EXECUTION_CONTRACT_PATH}")
    contract: dict[str, Any] = json.loads(EXECUTION_CONTRACT_PATH.read_text(encoding="utf-8"))
    methodology = contract.get("methodology", {})
    if methodology.get("preregistration_sha256") != WGAN_PREREGISTRATION_SHA256:
        raise RuntimeError("execution contract preregistration identity mismatch")
    if methodology.get("amendment_060_sha256") != AMENDMENT_060_SHA256:
        raise RuntimeError("execution contract Amendment-060 identity mismatch")
    if _sha256(PREREGISTRATION_PATH) != WGAN_PREREGISTRATION_SHA256:
        raise RuntimeError("preregistration bytes drifted")
    if _sha256(AMENDMENT_060_PATH) != AMENDMENT_060_SHA256:
        raise RuntimeError("Amendment-060 bytes drifted")
    return contract


def load_runtime_config() -> dict[str, Any]:
    """Load the singleton runtime configuration without scientific data access."""
    payload = yaml.safe_load(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("version") != "structured-vol-v5-wgan-comparator-v1"
    ):
        raise RuntimeError("WGAN runtime config version mismatch")
    provenance = payload.get("provenance", {})
    if provenance.get("preregistration_sha256") != WGAN_PREREGISTRATION_SHA256:
        raise RuntimeError("WGAN runtime config preregistration identity mismatch")
    if provenance.get("amendment_060_sha256") != AMENDMENT_060_SHA256:
        raise RuntimeError("WGAN runtime config Amendment-060 identity mismatch")
    return payload


def effective_config_for_member(member_id: str) -> WGANTrainingConfig:
    """Build the singleton effective config with the frozen member seed tuple."""
    if member_id not in _SEED_TUPLES:
        raise ValueError(f"unknown WGAN member {member_id!r}")
    replicate_seed, model_init_seed, data_seed, eval_seed = _SEED_TUPLES[member_id]
    return WGANTrainingConfig(
        replicate_seed=replicate_seed,
        model_init_seed=model_init_seed,
        data_seed=data_seed,
        eval_seed=eval_seed,
    )


def serialize_wgan_training_diagnostics(
    outcome: WGANTrainingOutcome,
    *,
    config: WGANTrainingConfig,
    fit_window_count: int,
) -> dict[str, Any]:
    """Serialize diagnostics already produced by the frozen training loop."""
    if fit_window_count < 1:
        raise ValueError("fit_window_count must be positive")
    curve_length = outcome.final_generator_epoch
    curves = (
        outcome.critic_loss_curve,
        outcome.generator_loss_curve,
        outcome.gradient_penalty_curve,
        outcome.selection_metric_curve,
    )
    if curve_length < 1 or any(len(curve) != curve_length for curve in curves):
        raise ValueError("WGAN diagnostic curves must match final_generator_epoch")
    if outcome.critic_update_count < 0 or outcome.generator_update_count < 0:
        raise ValueError("WGAN update counts must be non-negative")
    return {
        "schema_version": WGAN_TRAINING_DIAGNOSTIC_SCHEMA,
        "availability": {
            "critic_loss_curve": DIAGNOSTIC_PRESENT,
            "generator_loss_curve": DIAGNOSTIC_PRESENT,
            "gradient_penalty_curve": DIAGNOSTIC_PRESENT,
            "selection_metric_curve": DIAGNOSTIC_PRESENT,
            "critic_update_count": DIAGNOSTIC_PRESENT,
            "generator_update_count": DIAGNOSTIC_PRESENT,
            "training_completion": DIAGNOSTIC_PRESENT,
            "finite_nonfinite": DIAGNOSTIC_PRESENT,
            "checkpoint_selection_stability": DIAGNOSTIC_PRESENT,
            "mode_collapse_indicator": DIAGNOSTIC_NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE,
            "wgan-seed-01": DIAGNOSTIC_MISSING_BY_DESIGN_HISTORICAL,
        },
        "critic_loss_curve": list(outcome.critic_loss_curve),
        "generator_loss_curve": list(outcome.generator_loss_curve),
        "gradient_penalty_curve": list(outcome.gradient_penalty_curve),
        "critic_update_count": outcome.critic_update_count,
        "generator_update_count": outcome.generator_update_count,
        "training_completion": {
            "status": "COMPLETED" if outcome.training_completed else "INCOMPLETE",
            "final_generator_epoch": outcome.final_generator_epoch,
            "fit_window_count": fit_window_count,
        },
        "finite_nonfinite": {
            "status": "FINITE" if outcome.finite_diagnostics else "NONFINITE",
        },
        "checkpoint_selection": {
            "status": DIAGNOSTIC_PRESENT,
            "selection_metric_curve": list(outcome.selection_metric_curve),
            "best_generator_epoch": outcome.best_generator_epoch,
            "best_selection_metric": outcome.best_selection_metric,
            "final_generator_epoch": outcome.final_generator_epoch,
            "stopped_early": outcome.final_generator_epoch < config.max_generator_epochs,
        },
        "mode_collapse_indicator": {
            "status": DIAGNOSTIC_NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE,
            "value": None,
        },
        "historical_missingness": {
            "wgan-seed-01": {
                "status": DIAGNOSTIC_MISSING_BY_DESIGN_HISTORICAL,
                "value": None,
            }
        },
    }


def require_authorization(auth_path: str | Path | None) -> Path:
    """Require a later authorization path without creating one."""
    if auth_path is None:
        raise RuntimeError("authorization artifact required for scientific execution")
    path = Path(auth_path)
    if not path.is_file():
        raise RuntimeError(f"authorization artifact missing: {path}")
    return path


def _normalize_authorization_path(path: Path) -> Path:
    """Return one canonical absolute authorization path inside the repository."""
    repo = REPO.resolve()
    candidate = path if path.is_absolute() else repo / path
    candidate = candidate.resolve()
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise RuntimeError("authorization artifact must be inside the repository") from exc
    return candidate


def require_scientific_cuda(requested_device: str) -> None:
    """Reject every future scientific CPU request before data access."""
    if requested_device.strip().lower() != "cuda":
        raise RuntimeError(
            "scientific WGAN execution requires CUDA; "
            "CPU is NON_SCIENTIFIC_TEST_ONLY"
        )


def validate_authorization_payload(
    payload: dict[str, Any], *, expected_identity: dict[str, Any]
) -> None:
    """Validate a later authorization's identity and fail-closed permissions."""
    required = {
        "schema_version",
        "member_id",
        "replicate_seed",
        "model_init_seed",
        "data_seed",
        "eval_seed",
        "effective_config_sha256",
        "effective_config_git_blob",
        "comparator_methodology_sha256",
        "amendment_060_sha256",
        "seed_schedule_sha256",
        "seed_schedule_git_blob",
        "execution_contract_git_blob",
        "runner_git_blob",
        "implementation_source_git_blobs",
        "execution_recipe_head",
        "requested_device",
        "expected_resolved_device",
        "expected_runtime_identity_sha256",
        "max_scientific_invocations",
        "training_authorized",
        "validation_authorized",
        "final_test_authorized",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"authorization missing required field: {missing[0]}")
    if payload["schema_version"] != "structured-vol-v5-wgan-authorization-v1":
        raise ValueError("authorization schema_version mismatch")
    member_id = str(payload["member_id"])
    if member_id not in _SEED_TUPLES:
        raise ValueError("authorization member_id is not a frozen primary or reserve")
    expected_seeds = _SEED_TUPLES[member_id]
    actual_seeds = tuple(
        int(payload[key])
        for key in ("replicate_seed", "model_init_seed", "data_seed", "eval_seed")
    )
    if actual_seeds != expected_seeds:
        raise ValueError("authorization seed tuple mismatch")
    if payload["effective_config_sha256"] != expected_identity["effective_config_sha256"]:
        raise ValueError("authorization effective config SHA mismatch")
    if payload["effective_config_git_blob"] != expected_identity["effective_config_git_blob"]:
        raise ValueError("authorization effective config blob mismatch")
    if payload["comparator_methodology_sha256"] != expected_identity["preregistration_sha256"]:
        raise ValueError("authorization comparator methodology identity mismatch")
    if payload["amendment_060_sha256"] != expected_identity["amendment_060_sha256"]:
        raise ValueError("authorization Amendment-060 identity mismatch")
    if payload["seed_schedule_sha256"] != SEED_SCHEDULE_SHA256:
        raise ValueError("authorization seed schedule SHA mismatch")
    if payload["seed_schedule_git_blob"] != SEED_SCHEDULE_BLOB:
        raise ValueError("authorization seed schedule blob mismatch")
    if payload["execution_contract_git_blob"] != expected_identity["execution_contract_git_blob"]:
        raise ValueError("authorization execution contract blob mismatch")
    if payload["runner_git_blob"] != expected_identity["runner_git_blob"]:
        raise ValueError("authorization runner identity mismatch")
    if (
        payload["implementation_source_git_blobs"]
        != expected_identity["implementation_source_git_blobs"]
    ):
        raise ValueError("authorization implementation identity mismatch")
    if payload["requested_device"] != "cuda" or payload["expected_resolved_device"] != "cuda":
        raise ValueError("authorization CUDA device binding mismatch")
    if payload["expected_runtime_identity_sha256"] != expected_identity["runtime_identity_sha256"]:
        raise ValueError("authorization runtime identity mismatch")
    if payload["max_scientific_invocations"] != 1:
        raise ValueError("authorization max_scientific_invocations must be 1")
    if payload["training_authorized"] is not True:
        raise ValueError("authorization training_authorized must be true")
    if payload["validation_authorized"] is not False:
        raise ValueError("authorization validation_authorized must be false")
    if payload["final_test_authorized"] is not False:
        raise ValueError("authorization final_test_authorized must be false")


def _load_authorization(path: Path) -> dict[str, Any]:
    """Load a normalized, tracked, committed, clean authorization artifact."""
    repo = REPO.resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise RuntimeError("authorization artifact must be inside the repository") from exc
    if not _is_tracked(path):
        raise RuntimeError("authorization artifact must be tracked")
    head_blob = _git_head_blob(path)
    if not head_blob:
        raise RuntimeError("authorization artifact must be committed")
    if not _is_clean(path) or _git_blob(path) != head_blob:
        raise RuntimeError("authorization artifact must be clean and equal to HEAD")
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _current_identity(*, runtime_sha: str) -> dict[str, Any]:
    """Collect current committed implementation identities for authorization binding."""
    source_blobs: dict[str, str] = {}
    for name, path in (("model", MODEL_SOURCE_PATH), ("comparator", COMPARATOR_SOURCE_PATH)):
        if not _is_tracked(path):
            raise RuntimeError(f"{name} source is not tracked")
        head_blob = _git_head_blob(path)
        if not head_blob or not _is_clean(path) or _git_blob(path) != head_blob:
            raise RuntimeError(f"{name} source must be committed and clean before authorization")
        source_blobs[name] = head_blob
    runner_blob = _git_head_blob(RUNNER_SOURCE_PATH)
    if (
        not runner_blob
        or not _is_clean(RUNNER_SOURCE_PATH)
        or _git_blob(RUNNER_SOURCE_PATH) != runner_blob
    ):
        raise RuntimeError("runner must be committed and clean before authorization")
    return {
        "runner_git_blob": runner_blob,
        "implementation_source_git_blobs": source_blobs,
        "execution_contract_git_blob": _git_head_blob(EXECUTION_CONTRACT_PATH),
        "effective_config_sha256": _sha256(RUNTIME_CONFIG_PATH),
        "effective_config_git_blob": _git_head_blob(RUNTIME_CONFIG_PATH),
        "preregistration_sha256": WGAN_PREREGISTRATION_SHA256,
        "amendment_060_sha256": AMENDMENT_060_SHA256,
        "runtime_identity_sha256": runtime_sha,
    }


def _exclusive_create_execution_started(
    report_dir: Path, member_id: str, auth_path: Path, identity: dict[str, Any]
) -> Path:
    """Publish one complete exclusive execution marker after all preflight."""
    destination = report_dir / "execution_started.json"
    payload = {
        "schema_version": "structured-vol-v5-wgan-execution-start-v1",
        "member_id": member_id,
        "authorization_path": auth_path.relative_to(REPO.resolve()).as_posix(),
        "authorization_git_blob": _git_blob(auth_path),
        "implementation_identity": identity,
        "validation_accesses": 0,
        "final_test_accesses": 0,
        "provider_calls": 0,
        "network_calls": 0,
    }
    temporary = report_dir / f".execution_started.{os.getpid()}.tmp"
    report_dir.mkdir(parents=True, exist_ok=True)
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise RuntimeError("execution_started already exists; overwrite refused") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def execute_authorized_wgan(
    member_id: str,
    auth_data: dict[str, Any],
    report_dir: Path,
    model_dir: Path,
    *,
    device: Any,
) -> dict[str, Any]:
    """Future CUDA-only scientific path; never called by Task 109 tests."""
    if getattr(device, "type", str(device)) != "cuda":
        raise RuntimeError("scientific WGAN execution requires CUDA")
    import numpy as np
    import torch

    from neuralmarket.data.research.inventory import ResearchInventory
    from neuralmarket.data.research.underlying import build_underlying_series
    from neuralmarket.models.neural_sde import set_deterministic_seeds
    from neuralmarket.models.wgan_cde import WGANCritic, WGANGenerator

    inventory_path = REPO / "data/manifests/research_development_inventory_v1.json"
    inventory = ResearchInventory.model_validate(
        json.loads(inventory_path.read_text(encoding="utf-8"))
    )
    training_series = build_underlying_series(
        inventory=inventory,
        split="training",
        raw_root=REPO / "data/raw/databento",
        processed_root=REPO / "data/processed",
    )
    returns = np.asarray(training_series.returns_array, dtype=np.float64)
    return_dates = tuple(training_series.session_dates[1:])
    config = effective_config_for_member(member_id)
    set_deterministic_seeds(config.model_init_seed)
    prepared = prepare_wgan_training_data(
        returns,
        return_dates,
        fit_fraction=config.fit_fraction,
        device=device,
    )
    generator_model = WGANGenerator()
    critic_model = WGANCritic(
        cumulative_return_scale=prepared.cumulative_return_scale
    )
    outcome = train_wgan_internal(
        prepared,
        config=config,
        generator_model=generator_model,
        critic_model=critic_model,
        device=device,
    )
    refit_generator, refit_critic = refit_wgan(
        prepared,
        epochs=outcome.best_generator_epoch,
        config=config,
        device=device,
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = model_dir / "checkpoint.pt"
    generator_state = {
        key: value.detach().cpu() for key, value in refit_generator.state_dict().items()
    }
    critic_state = {
        key: value.detach().cpu() for key, value in refit_critic.state_dict().items()
    }
    torch.save(
        {
            "generator_state": generator_state,
            "critic_state": critic_state,
            "best_generator_epoch": outcome.best_generator_epoch,
            "best_selection_metric": outcome.best_selection_metric,
            "config_hash": config.config_hash(),
        },
        checkpoint,
    )
    return {
        "member_id": member_id,
        "report_dir": str(report_dir),
        "checkpoint_path": str(checkpoint),
        "checkpoint_sha256": _sha256(checkpoint),
        "best_generator_epoch": outcome.best_generator_epoch,
        "best_selection_metric": outcome.best_selection_metric,
        "training_diagnostics": serialize_wgan_training_diagnostics(
            outcome,
            config=config,
            fit_window_count=int(prepared.fit_context.shape[0]),
        ),
        "validation_accesses": 0,
        "final_test_accesses": 0,
    }


def main(argv: list[str] | None = None) -> int:
    """Run readiness validation or a later separately authorized execution."""
    parser = argparse.ArgumentParser(description="Frozen WGAN comparator runner")
    parser.add_argument("--member-id", required=True)
    parser.add_argument("--authorization", default=None)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    member_id = str(args.member_id)
    if member_id not in PRIMARY_MEMBER_IDS + RESERVE_MEMBER_IDS:
        print(f"REFUSED: unknown frozen WGAN member {member_id!r}", file=sys.stderr)
        return 2
    try:
        load_execution_contract()
        load_runtime_config()
        config = effective_config_for_member(member_id)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"REFUSED: readiness: {exc}", file=sys.stderr)
        return 2
    if not args.execute:
        print(
            "DRY RUN OK — NON_SCIENTIFIC_TEST_ONLY; "
            f"member={member_id} config_hash={config.config_hash()} "
            "training=NOT_INVOKED validation=PROHIBITED final_test=PROHIBITED"
        )
        return 0
    try:
        if args.authorization is None:
            require_authorization(None)
        auth_path = _normalize_authorization_path(Path(args.authorization))
        auth_path = require_authorization(auth_path)
        auth_data = _load_authorization(auth_path)
        require_scientific_cuda(str(auth_data.get("requested_device", "")))
        resolved = resolve_device("cuda")
        configure_device_determinism(resolved, enabled=True)
        runtime = build_runtime_identity(requested_device="cuda", resolved_device=str(resolved))
        identity = _current_identity(runtime_sha=str(runtime["runtime_identity_sha256"]))
        identity["runtime_identity"] = runtime
        validate_authorization_payload(auth_data, expected_identity=identity)
        prefix = hashlib.sha256(member_id.encode("utf-8")).hexdigest()[:16]
        report_dir = WGAN_RUN_ROOT / member_id / prefix
        model_dir = REPO / "data/processed/research/model/wgan-comparator" / member_id / prefix
        marker = _exclusive_create_execution_started(report_dir, member_id, auth_path, identity)
        result = execute_authorized_wgan(
            member_id, auth_data, report_dir, model_dir, device=resolved
        )
        result["execution_started_path"] = str(marker)
        (report_dir / "training_report.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        return 0
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"REFUSED: execution: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
