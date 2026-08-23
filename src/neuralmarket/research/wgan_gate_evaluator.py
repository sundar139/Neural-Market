"""Fail-closed, CUDA-only WGAN Gate-v2 evaluation boundary.

This module evaluates an already-frozen WGAN refit checkpoint only.  Training,
refit, authorization creation, reserve execution, validation, H2 aggregation,
and final-test access are deliberately outside this boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import torch

from neuralmarket.baselines.bootstrap import sample_block_bootstrap
from neuralmarket.core.device import configure_device_determinism, resolve_device
from neuralmarket.core.runtime_identity import build_runtime_identity
from neuralmarket.models.wgan_cde import HORIZON, LATENT_DIM, WGANGenerator
from neuralmarket.research.neural_sde_internal_gate import (
    GateSpecV2,
    _acf_max_error,
    _acf_rmse,
    _multi_lag_acf,
    _wasserstein_1d,
    load_gate_spec_v2,
)
from neuralmarket.research.wgan_comparator import (
    WGANTrainingConfig,
    prepare_wgan_training_data,
)

REPO = Path(__file__).resolve().parents[3]
GATE_CONFIG_RELATIVE_PATH = "configs/research/neural_sde_internal_gate_v2.yaml"
GATE_CONFIG_PATH = REPO / GATE_CONFIG_RELATIVE_PATH
WGAN_CONFIG_RELATIVE_PATH = "configs/research/structured_vol_wgan_comparator_v1.yaml"
WGAN_CONFIG_PATH = REPO / WGAN_CONFIG_RELATIVE_PATH
MODEL_SOURCE_PATH = REPO / "src/neuralmarket/models/wgan_cde.py"
COMPARATOR_SOURCE_PATH = REPO / "src/neuralmarket/research/wgan_comparator.py"
TRAINING_RUNNER_SOURCE_PATH = REPO / "src/neuralmarket/research/wgan_runner.py"
EVALUATOR_SOURCE_PATH = REPO / "src/neuralmarket/research/wgan_gate_evaluator.py"

GATE_CONFIG_SHA256 = "8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625"
GATE_CONFIG_GIT_BLOB = "d9705ef9a11da3e21760015bb2a27fa408018bb5"
WGAN_CONFIG_SHA256 = "de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7"
WGAN_CONFIG_GIT_BLOB = "e0740afc24697f2eab3620a4243d04411aa508cb"
MODEL_GIT_BLOB = "2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe"
COMPARATOR_GIT_BLOB = "87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b"
TRAINING_RUNNER_GIT_BLOB = "7e020ea937af9e2713451ae735d58c4cbb645289"
GATE_AUTHORIZATION_SCHEMA = "structured-vol-v5-wgan-gate-authorization-v1"
GATE_RESULT_SCHEMA = "structured-vol-v5-wgan-gate-result-v1"
GATE_MARKER_SCHEMA = "structured-vol-v5-wgan-gate-execution-start-v1"
GATE_RUN_ROOT_RELATIVE_PATH = "reports/research/wgan_gate_runs"
EVALUATION_SEED = 8283
BOOTSTRAP_SEED = 8801
BLOCK_LENGTH = 22
SAMPLE_COUNT = 1024
ACF_LAGS = (1, 2, 3, 5, 10, 20)
WGAN_GATE_CRITERIA = (
    "finite_output",
    "variance_ratio",
    "terminal_dispersion",
    "uniqueness",
    "acf1_agreement",
)
WGAN_REPORT_ONLY_METRICS = (
    "terminal_wasserstein_normalized",
    "acf_rmse",
    "acf_max_error",
    "abs_return_acf",
    "sq_return_acf",
    "cond_var_log_correlation",
)

_MEMBER_SEEDS: dict[str, tuple[int, int, int, int]] = {
    "wgan-seed-01": (8281, 8281, 8282, 8283),
    "wgan-seed-02": (9281, 9281, 9282, 8283),
    "wgan-seed-03": (10281, 10281, 10282, 8283),
    "wgan-seed-04": (11281, 11281, 11282, 8283),
    "wgan-seed-05": (12281, 12281, 12282, 8283),
    "reserve-wgan-j01": (13281, 13281, 13282, 8283),
    "reserve-wgan-j02": (14281, 14281, 14282, 8283),
    "reserve-wgan-j03": (15281, 15281, 15282, 8283),
}

_REQUIRED_AUTH_FIELDS = {
    "schema_version",
    "gate_task_id",
    "gate_execution_marker_path",
    "member_id",
    "checkpoint_path",
    "checkpoint_sha256",
    "training_execution_marker_path",
    "training_execution_marker_sha256",
    "training_authorization_path",
    "training_authorization_sha256",
    "training_authorization_git_blob",
    "training_execution_evidence_path",
    "training_execution_evidence_sha256",
    "training_execution_evidence_git_blob",
    "training_runner_git_blob",
    "scientific_config_sha256",
    "scientific_config_git_blob",
    "model_git_blob",
    "comparator_git_blob",
    "evaluator_git_blob",
    "gate_config_path",
    "gate_config_sha256",
    "gate_config_git_blob",
    "evaluation_seed",
    "bootstrap_seed",
    "generated_path_count",
    "bootstrap_path_count",
    "block_length",
    "acf_lags",
    "requested_device",
    "expected_resolved_device",
    "expected_runtime_identity_sha256",
    "max_scientific_invocations",
    "training_authorized",
    "gate_execution_authorized",
    "validation_authorized",
    "final_test_authorized",
    "overwrite",
    "relaunch",
}


@dataclass(frozen=True)
class FrozenGeneratorCheckpoint:
    """A generator reconstructed from a frozen checkpoint without writes."""

    model: WGANGenerator
    metadata: dict[str, Any]


def _sha256(path: Path) -> str:
    """Return the SHA-256 of one local artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob(path: Path) -> str:
    """Return the filtered working-tree Git blob identity for one artifact."""
    relative = path.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "hash-object", f"--path={relative}", str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git hash-object failed for {path}")
    return result.stdout.strip()


def _git_worktree_blob(path: Path) -> str:
    """Return the current worktree blob after Git path filters are applied."""
    return _git_blob(path)


def _git_head_blob(path: Path) -> str:
    """Return the committed HEAD blob identity for one repository path."""
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
    """Return whether a path is tracked by Git."""
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
    """Return whether a tracked path equals its index/worktree state."""
    relative = path.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", relative],
        cwd=str(REPO),
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _normalize_repo_path(path: str | Path) -> Path:
    """Resolve a path and reject repository escapes."""
    repo = REPO.resolve()
    candidate = Path(path)
    candidate = (repo / candidate if not candidate.is_absolute() else candidate).resolve()
    try:
        candidate.relative_to(repo)
    except ValueError as exc:
        raise RuntimeError("artifact path must be inside the repository") from exc
    return candidate


def require_tracked_artifact_at_head(path: str | Path, label: str) -> str:
    """Require a tracked worktree artifact to resolve to its committed HEAD blob."""
    normalized = _normalize_repo_path(path)
    if not normalized.is_file() or not _is_tracked(normalized):
        raise RuntimeError(f"{label} must be tracked and present")
    head_blob = _git_head_blob(normalized)
    if not head_blob:
        raise RuntimeError(f"{label} must be present at HEAD")
    if _git_worktree_blob(normalized) != head_blob:
        raise RuntimeError(f"{label} must match HEAD Git blob")
    return head_blob


def canonical_tracked_sha256(path: str | Path) -> str:
    """Hash committed Git-object bytes for one tracked artifact."""
    normalized = _normalize_repo_path(path)
    head_blob = require_tracked_artifact_at_head(normalized, "tracked artifact")
    relative = normalized.relative_to(REPO).as_posix()
    result = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{relative}"],
        cwd=str(REPO),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cannot read committed Git object {head_blob}")
    return hashlib.sha256(result.stdout).hexdigest()


def require_tracked_artifact_identity(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_git_blob: str,
    label: str,
) -> str:
    """Require canonical committed SHA and Git blob identity for one artifact."""
    head_blob = require_tracked_artifact_at_head(path, label)
    if head_blob != expected_git_blob:
        raise ValueError(f"{label} Git blob mismatch")
    if canonical_tracked_sha256(path) != expected_sha256:
        raise ValueError(f"{label} SHA mismatch")
    return head_blob


def _validate_gate_marker_path(path: Path, member_id: str) -> Path:
    """Require the marker to live in the deterministic member/run namespace."""
    root = _normalize_repo_path(GATE_RUN_ROOT_RELATIVE_PATH)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Gate execution marker must be inside the Gate run root") from exc
    if len(relative.parts) != 3 or relative.parts[0] != member_id:
        raise RuntimeError("Gate execution marker namespace mismatch")
    if relative.parts[2] != "execution_started.json" or not relative.parts[1]:
        raise RuntimeError("Gate execution marker filename mismatch")
    return path


def require_gate_authorization(auth_path: str | Path | None) -> Path:
    """Require a separately supplied Gate authorization artifact."""
    if auth_path is None:
        raise RuntimeError("Gate authorization artifact required for evaluation")
    path = _normalize_repo_path(auth_path)
    if not path.is_file():
        raise RuntimeError(f"Gate authorization artifact missing: {path}")
    return path


def load_gate_authorization(auth_path: str | Path | None) -> tuple[Path, dict[str, Any]]:
    """Load only a committed, tracked, clean future Gate authorization."""
    path = require_gate_authorization(auth_path)
    require_tracked_artifact_at_head(path, "Gate authorization artifact")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Gate authorization artifact must contain a JSON object")
    return path, payload


def _require_equal(payload: dict[str, Any], field: str, expected: object, label: str) -> None:
    if payload[field] != expected:
        raise ValueError(f"{label} mismatch")


def validate_gate_authorization_payload(
    payload: dict[str, Any], *, expected_identity: dict[str, object]
) -> None:
    """Validate the future Gate authorization schema and all frozen bindings."""
    missing = sorted(_REQUIRED_AUTH_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"Gate authorization missing required field: {missing[0]}")
    _require_equal(
        payload,
        "schema_version",
        GATE_AUTHORIZATION_SCHEMA,
        "Gate authorization schema",
    )
    if not isinstance(payload["gate_task_id"], str) or not payload["gate_task_id"]:
        raise ValueError("Gate task identity is required")
    _require_equal(
        payload,
        "member_id",
        expected_identity.get("member_id", "wgan-seed-01"),
        "member",
    )
    if str(payload["member_id"]) not in _MEMBER_SEEDS:
        raise ValueError("member is not a frozen WGAN primary or reserve")
    marker_path = _normalize_repo_path(str(payload["gate_execution_marker_path"]))
    _validate_gate_marker_path(marker_path, str(payload["member_id"]))
    _require_equal(
        payload,
        "checkpoint_path",
        expected_identity["checkpoint_path"],
        "checkpoint path",
    )
    _require_equal(
        payload,
        "checkpoint_sha256",
        expected_identity["checkpoint_sha256"],
        "checkpoint SHA",
    )
    for field, label in (
        ("training_execution_marker_path", "training execution marker path"),
        ("training_authorization_path", "training authorization path"),
        ("training_execution_evidence_path", "training execution evidence path"),
    ):
        _require_equal(payload, field, expected_identity[field], label)
    _require_equal(
        payload,
        "training_execution_marker_sha256",
        expected_identity["training_execution_marker_sha256"],
        "training execution marker",
    )
    expected_runtime_identity = expected_identity.get(
        "expected_runtime_identity_sha256", expected_identity.get("runtime_identity_sha256")
    )
    for field, label in (
        ("training_authorization_sha256", "training authorization SHA"),
        ("training_authorization_git_blob", "training authorization blob"),
        ("training_execution_evidence_sha256", "training execution evidence SHA"),
        ("training_execution_evidence_git_blob", "training execution evidence blob"),
        ("training_runner_git_blob", "training runner identity"),
        ("scientific_config_sha256", "WGAN scientific config SHA"),
        ("scientific_config_git_blob", "WGAN scientific config blob"),
        ("model_git_blob", "model identity"),
        ("comparator_git_blob", "comparator identity"),
        ("evaluator_git_blob", "evaluator identity"),
        ("gate_config_sha256", "Gate config SHA"),
        ("gate_config_git_blob", "Gate config blob"),
        ("expected_runtime_identity_sha256", "runtime identity"),
    ):
        expected = (
            expected_runtime_identity
            if field == "expected_runtime_identity_sha256"
            else expected_identity[field]
        )
        _require_equal(payload, field, expected, label)
    _require_equal(
        payload,
        "gate_config_path",
        GATE_CONFIG_RELATIVE_PATH,
        "Gate config path",
    )
    _require_equal(payload, "evaluation_seed", EVALUATION_SEED, "evaluation seed")
    _require_equal(payload, "bootstrap_seed", BOOTSTRAP_SEED, "bootstrap seed")
    _require_equal(payload, "generated_path_count", SAMPLE_COUNT, "generated path count")
    _require_equal(payload, "bootstrap_path_count", SAMPLE_COUNT, "bootstrap path count")
    _require_equal(payload, "block_length", BLOCK_LENGTH, "bootstrap block length")
    _require_equal(payload, "acf_lags", list(ACF_LAGS), "ACF lags")
    _require_equal(payload, "requested_device", "cuda", "requested device")
    _require_equal(payload, "expected_resolved_device", "cuda", "resolved device")
    _require_equal(payload, "max_scientific_invocations", 1, "maximum scientific invocations")
    for field, expected in (
        ("training_authorized", False),
        ("gate_execution_authorized", True),
        ("validation_authorized", False),
        ("final_test_authorized", False),
        ("overwrite", False),
        ("relaunch", False),
    ):
        _require_equal(payload, field, expected, field)


def require_cuda_device(device: torch.device | str) -> torch.device:
    """Reject CPU before any scientific WGAN model/tensor operation."""
    resolved = torch.device(device)
    if resolved.type != "cuda":
        raise RuntimeError(
            "scientific WGAN Gate evaluation requires CUDA; CPU fallback is prohibited"
        )
    return resolved


def effective_config_for_gate(member_id: str) -> WGANTrainingConfig:
    """Reconstruct the frozen member configuration without entering training."""
    if member_id not in _MEMBER_SEEDS:
        raise ValueError(f"unknown frozen WGAN member {member_id!r}")
    replicate_seed, model_init_seed, data_seed, eval_seed = _MEMBER_SEEDS[member_id]
    return WGANTrainingConfig(
        replicate_seed=replicate_seed,
        model_init_seed=model_init_seed,
        data_seed=data_seed,
        eval_seed=eval_seed,
    )


def load_frozen_generator_checkpoint(
    checkpoint_path: str | Path,
    *,
    checkpoint_sha256: str,
    config: WGANTrainingConfig,
    map_location: str | torch.device,
) -> FrozenGeneratorCheckpoint:
    """Load a frozen generator checkpoint read-only and verify its identity."""
    path = Path(checkpoint_path)
    if not path.is_file():
        raise RuntimeError(f"checkpoint missing: {path}")
    actual_sha = _sha256(path)
    if actual_sha != checkpoint_sha256:
        raise ValueError("checkpoint SHA mismatch")
    payload = torch.load(path, map_location=map_location, weights_only=True)
    if not isinstance(payload, dict):
        raise ValueError("checkpoint payload must be an object")
    if payload.get("config_hash") != config.config_hash():
        raise ValueError("checkpoint WGAN scientific config mismatch")
    state = payload.get("generator_state")
    if not isinstance(state, dict):
        raise ValueError("checkpoint generator_state is missing")
    epoch = payload.get("best_generator_epoch")
    metric = payload.get("best_selection_metric")
    if not isinstance(epoch, int) or epoch < 1:
        raise ValueError("checkpoint best_generator_epoch is invalid")
    if not isinstance(metric, int | float) or not math.isfinite(float(metric)):
        raise ValueError("checkpoint best_selection_metric is nonfinite")
    model = WGANGenerator(dt=config.dt)
    model.load_state_dict(state)
    model.to(map_location)
    model.eval()
    metadata: dict[str, Any] = {
        "best_generator_epoch": epoch,
        "best_selection_metric": float(metric),
        "config_hash": config.config_hash(),
    }
    return FrozenGeneratorCheckpoint(model=model, metadata=metadata)


def generate_wgan_evaluation_paths(
    model: WGANGenerator,
    contexts: torch.Tensor,
    *,
    sample_count: int = SAMPLE_COUNT,
    evaluation_seed: int = EVALUATION_SEED,
    device: torch.device,
) -> np.ndarray:
    """Generate the frozen post-training WGAN paths on CUDA only."""
    resolved = require_cuda_device(device)
    if sample_count != SAMPLE_COUNT:
        raise ValueError("WGAN Gate sample count is frozen at 1024")
    if evaluation_seed != EVALUATION_SEED:
        raise ValueError("WGAN Gate evaluation seed is frozen at 8283")
    if contexts.ndim != 2 or contexts.shape[1] != 4:
        raise ValueError("Gate contexts must have shape (batch, 4)")
    contexts = contexts.to(resolved)
    if contexts.shape[0] == 0:
        raise ValueError("Gate contexts must be non-empty")
    generator = torch.Generator(device=resolved)
    generator.manual_seed(evaluation_seed)
    context = contexts.repeat((sample_count + len(contexts) - 1) // len(contexts), 1)[:sample_count]
    with torch.no_grad():
        static_latent = torch.randn(
            sample_count, LATENT_DIM, device=resolved, generator=generator
        )
        temporal_noise = torch.randn(
            sample_count, HORIZON, 2, device=resolved, generator=generator
        )
        generated = model(context, static_latent, temporal_noise)
    if generated.device.type != "cuda":
        raise RuntimeError("scientific WGAN generation left CUDA")
    result = generated.detach().cpu().numpy()
    if not np.isfinite(result).all():
        raise ValueError("generated WGAN Gate paths are nonfinite")
    return cast(np.ndarray, result)


def _as_path_matrix(name: str, values: np.ndarray, expected_rows: int | None = None) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != HORIZON:
        raise ValueError(f"{name} must have shape (n, {HORIZON})")
    if expected_rows is not None and matrix.shape[0] != expected_rows:
        raise ValueError(f"{name} must contain exactly {expected_rows} paths")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{name} must be finite")
    return matrix


def compute_wgan_gate_metrics(
    generated_paths: np.ndarray,
    selection_daily_returns: np.ndarray,
    *,
    evaluation_seed: int = EVALUATION_SEED,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    selection_target_paths: np.ndarray | None = None,
    gate_spec: GateSpecV2 | None = None,
) -> dict[str, Any]:
    """Compute WGAN-eligible Gate-v2 criteria once plus report-only metrics."""
    if evaluation_seed != EVALUATION_SEED:
        raise ValueError("WGAN Gate evaluation seed is frozen at 8283")
    if bootstrap_seed != BOOTSTRAP_SEED:
        raise ValueError("WGAN Gate bootstrap seed is frozen at 8801")
    spec = GateSpecV2() if gate_spec is None else gate_spec
    if (
        spec.generated_path_count != SAMPLE_COUNT
        or spec.terminal_path_count != SAMPLE_COUNT
        or spec.horizon != HORIZON
        or spec.block_length != BLOCK_LENGTH
        or spec.bootstrap_seed != BOOTSTRAP_SEED
        or tuple(spec.acf_lags) != ACF_LAGS
    ):
        raise ValueError("Gate-v2 sample, block, seed, or ACF contract mismatch")
    generated = _as_path_matrix("generated paths", generated_paths, SAMPLE_COUNT)
    selection = np.asarray(selection_daily_returns, dtype=np.float64)
    if selection.ndim != 1 or len(selection) <= HORIZON or not np.isfinite(selection).all():
        raise ValueError(
            "selection daily returns must be a finite 1-D series longer than the horizon"
        )
    real_bootstrap = sample_block_bootstrap(
        selection,
        SAMPLE_COUNT,
        HORIZON,
        block_length=BLOCK_LENGTH,
        seed=BOOTSTRAP_SEED,
    )
    real_bootstrap = _as_path_matrix("real bootstrap paths", real_bootstrap, SAMPLE_COUNT)

    gen_terminal = generated.sum(axis=1)
    real_terminal = real_bootstrap.sum(axis=1)
    gen_terminal_std = float(np.std(gen_terminal))
    real_terminal_std = float(np.std(real_terminal))
    dispersion_ratio = (
        gen_terminal_std / real_terminal_std if real_terminal_std > 0.0 else float("nan")
    )
    generated_variance = float(np.var(generated))
    real_variance = float(np.var(selection))
    variance_ratio = generated_variance / real_variance if real_variance > 0.0 else float("nan")
    raw_wasserstein = _wasserstein_1d(gen_terminal, real_terminal)
    normalized_wasserstein = (
        raw_wasserstein / real_terminal_std if real_terminal_std > 0.0 else float("nan")
    )

    generated_flat = generated.ravel()
    selection_flat = selection.ravel()
    generated_acf = _multi_lag_acf(generated_flat, ACF_LAGS)
    real_acf = _multi_lag_acf(selection_flat, ACF_LAGS)
    acf_rmse = _acf_rmse(real_acf, generated_acf)
    acf_max_error = _acf_max_error(real_acf, generated_acf)
    acf1_diff = abs(real_acf[1] - generated_acf[1])
    generated_abs_acf = _multi_lag_acf(np.abs(generated_flat), ACF_LAGS)
    real_abs_acf = _multi_lag_acf(np.abs(selection_flat), ACF_LAGS)
    generated_sq_acf = _multi_lag_acf(generated_flat**2, ACF_LAGS)
    real_sq_acf = _multi_lag_acf(selection_flat**2, ACF_LAGS)
    fingerprints = {
        tuple(float(value) for value in row.round(6))
        for row in generated[: min(len(generated), 2048)]
    }
    uniqueness = len(fingerprints) / min(len(generated), 2048)

    cond_var_corr: float | None = None
    if selection_target_paths is not None:
        target_paths = _as_path_matrix("selection target paths", selection_target_paths)
        n_match = min(len(generated), len(target_paths))
        if n_match < 2:
            raise ValueError("conditional-variance diagnostic needs two matched paths")
        generated_path_variance = np.var(generated[:n_match], axis=1)
        target_path_variance = np.var(target_paths[:n_match], axis=1)
        cond_var_corr = float(
            np.corrcoef(
                np.log(generated_path_variance + 1e-12),
                np.log(target_path_variance + 1e-12),
            )[0, 1]
        )

    finite_output = bool(np.isfinite(generated).all())
    criterion_results = {
        "finite_output": finite_output,
        "variance_ratio": bool(
            math.isfinite(variance_ratio)
            and spec.variance_ratio_lo <= variance_ratio <= spec.variance_ratio_hi
        ),
        "terminal_dispersion": bool(
            math.isfinite(dispersion_ratio)
            and spec.dispersion_band_lo <= dispersion_ratio <= spec.dispersion_band_hi
        ),
        "uniqueness": bool(math.isfinite(uniqueness) and uniqueness >= spec.uniqueness_min),
        "acf1_agreement": bool(
            math.isfinite(acf1_diff) and acf1_diff <= spec.acf1_max_diff
        ),
    }
    report_only = {
        "terminal_wasserstein_normalized": normalized_wasserstein,
        "acf_rmse": acf_rmse,
        "acf_max_error": acf_max_error,
        "abs_return_acf": {
            "real": {str(k): float(v) for k, v in real_abs_acf.items()},
            "generated": {str(k): float(v) for k, v in generated_abs_acf.items()},
        },
        "sq_return_acf": {
            "real": {str(k): float(v) for k, v in real_sq_acf.items()},
            "generated": {str(k): float(v) for k, v in generated_sq_acf.items()},
        },
        "cond_var_log_correlation": cond_var_corr,
    }
    diagnostics: dict[str, Any] = {
        "gate_spec_hash": spec.spec_hash(),
        "evaluation_seed": evaluation_seed,
        "bootstrap_seed": bootstrap_seed,
        "bootstrap_block_length": BLOCK_LENGTH,
        "generated_path_count": SAMPLE_COUNT,
        "real_bootstrap_path_count": SAMPLE_COUNT,
        "horizon": HORIZON,
        "acf_lags": list(ACF_LAGS),
        "finite_output": finite_output,
        "generated_daily_variance": generated_variance,
        "real_daily_variance": real_variance,
        "variance_ratio": variance_ratio,
        "generated_terminal_std": gen_terminal_std,
        "real_bootstrap_terminal_std": real_terminal_std,
        "terminal_dispersion_ratio": dispersion_ratio,
        "terminal_wasserstein_raw": raw_wasserstein,
        "terminal_wasserstein_normalized": normalized_wasserstein,
        "generated_acf": {str(k): float(v) for k, v in generated_acf.items()},
        "real_acf": {str(k): float(v) for k, v in real_acf.items()},
        "return_acf1_abs_diff": acf1_diff,
        "acf_rmse": acf_rmse,
        "acf_max_error": acf_max_error,
        "abs_return_acf": report_only["abs_return_acf"],
        "sq_return_acf": report_only["sq_return_acf"],
        "cond_var_log_correlation": cond_var_corr,
        "path_uniqueness_fraction": uniqueness,
        "criterion_results": criterion_results,
        "report_only": report_only,
        "gate_passed": all(criterion_results.values()),
    }
    return diagnostics


def classify_valid_gate_result(
    *,
    member_id: str,
    checkpoint_sha256: str,
    authorization_identity: str,
    evaluator_identity: str,
    gate_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Classify one finite completed member without retry or result filtering."""
    criterion_results = gate_diagnostics.get("criterion_results")
    if not isinstance(criterion_results, dict) or tuple(criterion_results) != WGAN_GATE_CRITERIA:
        raise ValueError("WGAN Gate criteria are incomplete or out of order")
    if not all(isinstance(value, bool) for value in criterion_results.values()):
        raise ValueError("WGAN Gate criteria must be boolean")
    passed = all(criterion_results.values())
    status = "GATE_PASS_VALID" if passed else "GATE_FAIL_VALID"
    return {
        "schema_version": GATE_RESULT_SCHEMA,
        "member_id": member_id,
        "classification": status,
        "member_classification": status,
        "overall_gate_result": status,
        "checkpoint": {"sha256": checkpoint_sha256},
        "authorization_identity": authorization_identity,
        "evaluator_identity": evaluator_identity,
        "gate_config_identity": gate_diagnostics["gate_spec_hash"],
        "seeds": {
            "evaluation_seed": gate_diagnostics["evaluation_seed"],
            "bootstrap_seed": gate_diagnostics["bootstrap_seed"],
        },
        "sample_sizes": {
            "generated_paths": gate_diagnostics["generated_path_count"],
            "bootstrap_paths": gate_diagnostics["real_bootstrap_path_count"],
            "horizon": gate_diagnostics["horizon"],
            "block_length": gate_diagnostics["bootstrap_block_length"],
            "acf_lags": gate_diagnostics["acf_lags"],
        },
        "criteria": criterion_results,
        "report_only_metrics": gate_diagnostics["report_only"],
        "metrics": {
            "criteria": criterion_results,
            "report_only": gate_diagnostics["report_only"],
        },
        "gate_diagnostics": gate_diagnostics,
        "numerically_valid": True,
        "numerically_included": True,
        "completed_model_member": True,
        "poor_performance_discarded": False,
        "retry": False,
        "relaunch": False,
        "firewalls": {
            "training": 0,
            "refit": 0,
            "validation": 0,
            "final_test": 0,
            "h2": 0,
            "seed_02_authorization": 0,
            "automatic_reserve": 0,
        },
    }


def _current_identity(
    *,
    payload: dict[str, Any],
    checkpoint_path: Path,
    runtime_identity_sha256: str,
) -> dict[str, object]:
    """Collect current identities that a future authorization must bind."""
    marker_path = _normalize_repo_path(str(payload["training_execution_marker_path"]))
    training_auth_path = _normalize_repo_path(str(payload["training_authorization_path"]))
    evidence_path = _normalize_repo_path(str(payload["training_execution_evidence_path"]))
    for path, label in (
        (marker_path, "training execution marker"),
        (training_auth_path, "training authorization"),
        (evidence_path, "training execution evidence"),
        (checkpoint_path, "checkpoint"),
    ):
        if not path.is_file():
            raise RuntimeError(f"{label} missing: {path}")
    tracked_blobs = {
        "training_authorization": require_tracked_artifact_at_head(
            training_auth_path, "training authorization"
        ),
        "training_execution_evidence": require_tracked_artifact_at_head(
            evidence_path, "training execution evidence"
        ),
        "evaluator": require_tracked_artifact_at_head(EVALUATOR_SOURCE_PATH, "evaluator source"),
    }
    frozen_blobs = (
        (MODEL_SOURCE_PATH, MODEL_GIT_BLOB, "model"),
        (COMPARATOR_SOURCE_PATH, COMPARATOR_GIT_BLOB, "comparator"),
        (TRAINING_RUNNER_SOURCE_PATH, TRAINING_RUNNER_GIT_BLOB, "training runner"),
        (WGAN_CONFIG_PATH, WGAN_CONFIG_GIT_BLOB, "WGAN scientific config"),
        (GATE_CONFIG_PATH, GATE_CONFIG_GIT_BLOB, "Gate config"),
    )
    for path, expected_blob, label in frozen_blobs:
        actual_blob = require_tracked_artifact_at_head(path, label)
        if actual_blob != expected_blob:
            raise RuntimeError(f"{label} committed identity drifted")
    if canonical_tracked_sha256(WGAN_CONFIG_PATH) != WGAN_CONFIG_SHA256:
        raise RuntimeError("WGAN scientific config SHA drifted")
    if canonical_tracked_sha256(GATE_CONFIG_PATH) != GATE_CONFIG_SHA256:
        raise RuntimeError("Gate config SHA drifted")
    return {
        "member_id": str(payload["member_id"]),
        "checkpoint_path": checkpoint_path.relative_to(REPO.resolve()).as_posix(),
        "checkpoint_sha256": _sha256(checkpoint_path),
        "training_execution_marker_path": marker_path.relative_to(REPO.resolve()).as_posix(),
        "training_execution_marker_sha256": _sha256(marker_path),
        "training_authorization_path": training_auth_path.relative_to(REPO.resolve()).as_posix(),
        "training_authorization_sha256": canonical_tracked_sha256(training_auth_path),
        "training_authorization_git_blob": tracked_blobs["training_authorization"],
        "training_execution_evidence_path": evidence_path.relative_to(REPO.resolve()).as_posix(),
        "training_execution_evidence_sha256": canonical_tracked_sha256(evidence_path),
        "training_execution_evidence_git_blob": tracked_blobs["training_execution_evidence"],
        "training_runner_git_blob": _git_head_blob(TRAINING_RUNNER_SOURCE_PATH),
        "scientific_config_sha256": canonical_tracked_sha256(WGAN_CONFIG_PATH),
        "scientific_config_git_blob": _git_head_blob(WGAN_CONFIG_PATH),
        "model_git_blob": _git_head_blob(MODEL_SOURCE_PATH),
        "comparator_git_blob": _git_head_blob(COMPARATOR_SOURCE_PATH),
        "evaluator_git_blob": tracked_blobs["evaluator"],
        "gate_config_sha256": canonical_tracked_sha256(GATE_CONFIG_PATH),
        "gate_config_git_blob": _git_head_blob(GATE_CONFIG_PATH),
        "runtime_identity_sha256": runtime_identity_sha256,
    }


_GATE_MARKER_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "gate_task_id",
        "member_id",
        "authorization_path",
        "authorization_git_blob",
        "authorization_canonical_sha256",
        "checkpoint_path",
        "checkpoint_sha256",
        "training_execution_marker_path",
        "training_execution_marker_sha256",
        "training_authorization_path",
        "training_authorization_sha256",
        "training_authorization_git_blob",
        "training_execution_evidence_path",
        "training_execution_evidence_sha256",
        "training_execution_evidence_git_blob",
        "evaluator_git_blob",
        "gate_config_sha256",
        "gate_config_git_blob",
        "evaluation_seed",
        "bootstrap_seed",
        "runtime_identity_sha256",
        "max_scientific_invocations",
    }
)


def create_gate_execution_marker(
    marker_path: str | Path, payload: dict[str, Any]
) -> Path:
    """Create the one immutable Gate-start marker without overwrite or retry."""
    marker = _normalize_repo_path(marker_path)
    member_id = str(payload.get("member_id", ""))
    _validate_gate_marker_path(marker, member_id)
    missing = sorted(_GATE_MARKER_REQUIRED_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"Gate execution marker missing required field: {missing[0]}")
    if payload["schema_version"] != GATE_MARKER_SCHEMA:
        raise ValueError("Gate execution marker schema mismatch")
    if payload["max_scientific_invocations"] != 1:
        raise ValueError("Gate execution marker max scientific invocations must be 1")
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        with marker.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise RuntimeError("Gate execution marker already exists; overwrite refused") from exc
    return marker


def _build_gate_execution_marker_payload(
    *,
    authorization_path: Path,
    authorization_payload: dict[str, Any],
    checkpoint_path: Path,
    checkpoint_sha256: str,
    expected_identity: dict[str, object],
) -> dict[str, Any]:
    """Bind all preflight identities before the scientific boundary."""
    return {
        "schema_version": GATE_MARKER_SCHEMA,
        "gate_task_id": str(authorization_payload["gate_task_id"]),
        "member_id": str(authorization_payload["member_id"]),
        "authorization_path": authorization_path.relative_to(REPO.resolve()).as_posix(),
        "authorization_git_blob": require_tracked_artifact_at_head(
            authorization_path, "Gate authorization artifact"
        ),
        "authorization_canonical_sha256": canonical_tracked_sha256(authorization_path),
        "checkpoint_path": checkpoint_path.relative_to(REPO.resolve()).as_posix(),
        "checkpoint_sha256": checkpoint_sha256,
        "training_execution_marker_path": expected_identity["training_execution_marker_path"],
        "training_execution_marker_sha256": expected_identity["training_execution_marker_sha256"],
        "training_authorization_path": expected_identity["training_authorization_path"],
        "training_authorization_sha256": expected_identity["training_authorization_sha256"],
        "training_authorization_git_blob": expected_identity["training_authorization_git_blob"],
        "training_execution_evidence_path": expected_identity["training_execution_evidence_path"],
        "training_execution_evidence_sha256": expected_identity[
            "training_execution_evidence_sha256"
        ],
        "training_execution_evidence_git_blob": expected_identity[
            "training_execution_evidence_git_blob"
        ],
        "evaluator_git_blob": expected_identity["evaluator_git_blob"],
        "gate_config_sha256": expected_identity["gate_config_sha256"],
        "gate_config_git_blob": expected_identity["gate_config_git_blob"],
        "evaluation_seed": int(authorization_payload["evaluation_seed"]),
        "bootstrap_seed": int(authorization_payload["bootstrap_seed"]),
        "runtime_identity_sha256": expected_identity["runtime_identity_sha256"],
        "max_scientific_invocations": int(authorization_payload["max_scientific_invocations"]),
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "process_id": os.getpid(),
    }


def evaluate_frozen_wgan_checkpoint(
    *,
    member_id: str,
    checkpoint_path: str | Path,
    checkpoint_sha256: str,
    authorization_identity: str,
    authorization_payload: dict[str, Any],
    training_returns: np.ndarray,
    return_dates: Sequence[str],
    device: torch.device,
) -> dict[str, Any]:
    """Evaluate one authorized frozen checkpoint using training-only data."""
    resolved = require_cuda_device(device)
    if authorization_payload["member_id"] != member_id:
        raise ValueError("Gate authorization member mismatch")
    config = effective_config_for_gate(member_id)
    gate_spec = load_gate_spec_v2(str(GATE_CONFIG_PATH))
    frozen = load_frozen_generator_checkpoint(
        checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
        config=config,
        map_location=resolved,
    )
    prepared = prepare_wgan_training_data(
        training_returns,
        return_dates,
        fit_fraction=config.fit_fraction,
        device=resolved,
    )
    generated = generate_wgan_evaluation_paths(
        frozen.model,
        prepared.selection_context,
        sample_count=gate_spec.generated_path_count,
        evaluation_seed=int(authorization_payload["evaluation_seed"]),
        device=resolved,
    )
    diagnostics = compute_wgan_gate_metrics(
        generated,
        prepared.selection_daily_returns,
        evaluation_seed=int(authorization_payload["evaluation_seed"]),
        bootstrap_seed=int(authorization_payload["bootstrap_seed"]),
        selection_target_paths=prepared.selection_targets.detach().cpu().numpy(),
        gate_spec=gate_spec,
    )
    result = classify_valid_gate_result(
        member_id=member_id,
        checkpoint_sha256=checkpoint_sha256,
        authorization_identity=authorization_identity,
        evaluator_identity=str(authorization_payload["evaluator_git_blob"]),
        gate_diagnostics=diagnostics,
    )
    result["checkpoint"]["path"] = (
        Path(checkpoint_path).resolve().relative_to(REPO.resolve()).as_posix()
    )
    result["checkpoint"]["metadata"] = frozen.metadata
    result["runtime"] = {"requested_device": "cuda", "resolved_device": str(resolved)}
    result["scientific_config"] = {
        "path": WGAN_CONFIG_RELATIVE_PATH,
        "sha256": str(authorization_payload["scientific_config_sha256"]),
        "effective_config_hash": config.config_hash(),
    }
    return result


def _load_training_returns() -> tuple[np.ndarray, tuple[str, ...]]:
    """Load only the frozen training split for a future authorized evaluation."""
    from neuralmarket.data.research.inventory import ResearchInventory
    from neuralmarket.data.research.underlying import build_underlying_series

    inventory_path = REPO / "data/manifests/research_development_inventory_v1.json"
    inventory = ResearchInventory.model_validate(
        json.loads(inventory_path.read_text(encoding="utf-8"))
    )
    series = build_underlying_series(
        inventory=inventory,
        split="training",
        raw_root=REPO / "data/raw/databento",
        processed_root=REPO / "data/processed",
    )
    returns = np.asarray(series.returns_array, dtype=np.float64)
    dates = tuple(str(value) for value in series.session_dates[1:])
    return returns, dates


def evaluate_authorized_wgan_gate(
    *,
    member_id: str,
    checkpoint_path: str | Path,
    checkpoint_sha256: str,
    authorization_path: str | Path | None,
) -> dict[str, Any]:
    """Resolve identities and execute exactly one future authorized Gate evaluation."""
    auth_path, payload = load_gate_authorization(authorization_path)
    if payload.get("member_id") != member_id:
        raise ValueError("Gate authorization member mismatch")
    requested = str(payload.get("requested_device", ""))
    require_cuda_device(requested)
    resolved = resolve_device(requested)
    require_cuda_device(resolved)
    configure_device_determinism(resolved, enabled=True)
    runtime = build_runtime_identity(requested_device=requested, resolved_device=str(resolved))
    normalized_checkpoint = _normalize_repo_path(checkpoint_path)
    expected = _current_identity(
        payload=payload,
        checkpoint_path=normalized_checkpoint,
        runtime_identity_sha256=str(runtime["runtime_identity_sha256"]),
    )
    validate_gate_authorization_payload(payload, expected_identity=expected)
    if checkpoint_sha256 != expected["checkpoint_sha256"]:
        raise ValueError("checkpoint SHA mismatch")
    marker_path = _normalize_repo_path(str(payload["gate_execution_marker_path"]))
    marker_payload = _build_gate_execution_marker_payload(
        authorization_path=auth_path,
        authorization_payload=payload,
        checkpoint_path=normalized_checkpoint,
        checkpoint_sha256=checkpoint_sha256,
        expected_identity=expected,
    )
    marker = create_gate_execution_marker(marker_path, marker_payload)
    training_returns, return_dates = _load_training_returns()
    result = evaluate_frozen_wgan_checkpoint(
        member_id=member_id,
        checkpoint_path=normalized_checkpoint,
        checkpoint_sha256=checkpoint_sha256,
        authorization_identity=canonical_tracked_sha256(auth_path),
        authorization_payload=payload,
        training_returns=training_returns,
        return_dates=return_dates,
        device=resolved,
    )
    result["authorization"] = {
        "path": auth_path.relative_to(REPO.resolve()).as_posix(),
        "sha256": canonical_tracked_sha256(auth_path),
        "git_blob": _git_head_blob(auth_path),
    }
    result["execution_marker"] = {
        "path": marker.relative_to(REPO.resolve()).as_posix(),
        "sha256": _sha256(marker),
    }
    result["runtime"] = runtime
    return result


def main(argv: list[str] | None = None) -> int:
    """Run a future Gate evaluation only when a committed authorization is supplied."""
    parser = argparse.ArgumentParser(description="Authorized WGAN Gate-v2 evaluator")
    parser.add_argument("--member-id", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--authorization", default=None)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print("DRY RUN — Gate execution NOT INVOKED; no authorization consumed")
        return 0
    try:
        result = evaluate_authorized_wgan_gate(
            member_id=str(args.member_id),
            checkpoint_path=str(args.checkpoint),
            checkpoint_sha256=str(args.checkpoint_sha256),
            authorization_path=args.authorization,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"REFUSED: Gate evaluation: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


__all__ = [
    "ACF_LAGS",
    "BLOCK_LENGTH",
    "BOOTSTRAP_SEED",
    "EVALUATION_SEED",
    "GATE_AUTHORIZATION_SCHEMA",
    "GATE_CONFIG_GIT_BLOB",
    "GATE_CONFIG_RELATIVE_PATH",
    "GATE_CONFIG_SHA256",
    "GATE_MARKER_SCHEMA",
    "GATE_RESULT_SCHEMA",
    "SAMPLE_COUNT",
    "WGAN_GATE_CRITERIA",
    "WGAN_REPORT_ONLY_METRICS",
    "canonical_tracked_sha256",
    "classify_valid_gate_result",
    "compute_wgan_gate_metrics",
    "create_gate_execution_marker",
    "effective_config_for_gate",
    "evaluate_authorized_wgan_gate",
    "evaluate_frozen_wgan_checkpoint",
    "generate_wgan_evaluation_paths",
    "load_frozen_generator_checkpoint",
    "load_gate_authorization",
    "main",
    "require_cuda_device",
    "require_gate_authorization",
    "require_tracked_artifact_at_head",
    "require_tracked_artifact_identity",
    "validate_gate_authorization_payload",
]


if __name__ == "__main__":
    raise SystemExit(main())
