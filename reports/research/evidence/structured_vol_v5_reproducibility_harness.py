"""Deterministic reproducibility replay harness for NM-R4-V5-PRODUCTION-RERUN-008.

This is a REPRODUCIBILITY REPLAY ONLY. It creates NO new scientific candidate,
uses NO independent seed, and does NOT count toward the eventual five-seed
H1/H2 experiment. It executes the unchanged, independently validated frozen
v5 source/config/gate semantics exactly once into a NEW temporary output root
and tests whether the produced artifacts reproduce the canonical production
artifacts BYTE-FOR-BYTE.

Execution chain (identical to the canonical production run, NM-R4-V5-
PRODUCTION-RUN-006):

  frozen config -> training-only empirical series (instrumented boundary)
  -> frozen fit/selection split -> train_internal_v3 -> selected checkpoint
  -> evaluate_gate_v2 -> branch: FAIL => freeze + stop | PASS =>
  refit_final_v3 -> freeze final checkpoint -> compare bytes vs canonical.

This harness is TRACKED and must be committed to Git BEFORE execution. After
execution it MUST NEVER be edited. It contains no scientific constants copied
from memory: expected values are either loaded from the frozen config/gate/
data artifacts and the canonical durable report, or are pinned frozen
invariants (config/gate/data identity hashes) marked as content, not secrets.

Authorized: training split only, internal fit/selection training, the frozen
internal Gate-v2, conditional deterministic all-training refit, final-checkpoint
freeze, byte comparison against canonical artifacts.

NOT authorized and IMPOSSIBLE through this harness:
- build_underlying_series(split="validation") (guarded boundary raises)
- external validation data / scorecard / baseline comparison on validation
- sealed final-test access
- provider / network operations
- any write to canonical or historical artifact paths.
"""
# ruff: noqa: E501  # pinned 64-hex frozen-id literals + long absolute path literals

from __future__ import annotations

import datetime
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from neuralmarket.core.environment import repository_source_identity  # noqa: E402
from neuralmarket.data.manifests import canonical_dumps  # noqa: E402
from neuralmarket.data.research.inventory import ResearchInventory  # noqa: E402
from neuralmarket.data.research.sde_windows import (  # noqa: E402
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
    split_fit_selection,
)
from neuralmarket.data.research.underlying import build_underlying_series  # noqa: E402
from neuralmarket.models.neural_sde import (  # noqa: E402
    configure_determinism,
    count_parameters,
    set_deterministic_seeds,
)
from neuralmarket.models.structured_vol_sde import StructuredVolatilityNeuralSde  # noqa: E402
from neuralmarket.research.neural_sde_internal_gate import (  # noqa: E402
    evaluate_gate_v2,
    load_gate_spec_v2,
)
from neuralmarket.research.neural_sde_trainer_v2 import _window_tensors  # noqa: E402
from neuralmarket.research.neural_sde_trainer_v3 import (  # noqa: E402
    _evaluate_selection_v3,
    build_v3_statistics,
    refit_final_v3,
    train_internal_v3,
)
from neuralmarket.research.structured_vol_experiment import load_v5_config  # noqa: E402

# ---- Pinned frozen invariants (content identity, not secrets) ----
_VALIDATED_SOURCE_COMMIT = "357971a67c68492fc0c4f5bf31f94f9685639f65"
_EXPECTED_CONFIG_HASH = (
    "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157"  # pragma: allowlist secret
)
_EXPECTED_GATE_YAML_SHA = (
    "8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625"  # pragma: allowlist secret
)
_EXPECTED_GATE_SPEC_HASH = (
    "f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469"  # pragma: allowlist secret
)
_EXPECTED_INVENTORY_HASH = (
    "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"  # pragma: allowlist secret
)
_EXPECTED_TRAINING_SERIES_SHA = (
    "4863b2cc63a09ffb03bbe455c7859c46b521b6f7bef8212e0e3876ac8488669c"  # pragma: allowlist secret
)

CONFIG_PATH = REPO / "configs/research/structured_vol_neural_sde_v5.yaml"
GATE_YAML = REPO / "configs/research/neural_sde_internal_gate_v2.yaml"
INVENTORY_PATH = REPO / "data/manifests/research_development_inventory_v1.json"
BENCHMARK_PATH = REPO / "data/processed/research/benchmark/empirical_benchmark_v1.json"
SUITE_PATH = REPO / "data/processed/research/benchmark/simulator_baseline_suite_v1.json"
RAW_ROOT = REPO / "data/raw/databento"
PROCESSED_ROOT = REPO / "data/processed"

# Canonical production artifacts (READ ONLY for this harness).
CANONICAL_DIR = (
    REPO / "data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7"
)
CANONICAL_DURABLE_REPORT = REPO / "reports/research/structured_vol_v5_production_gate_v2.json"

# Replay output root (temporary, gitignored, must be absent before execution).
REPLAY_OUTPUT_ROOT = REPO / ".agent-memory/evidence/NM-R4-V5-PRODUCTION-RERUN-008/output"
REPLAY_TRANSCRIPT = (
    REPO / ".agent-memory/evidence/NM-R4-V5-PRODUCTION-RERUN-008/replay_stdout_stderr.log"
)
REPLAY_RESULT_PATH = REPO / "reports/research/structured_vol_v5_reproducibility.json"
HARNESS_PATH = REPO / "reports/research/evidence/structured_vol_v5_reproducibility_harness.py"

_COUNTERS = {
    "training_calls": 0,
    "gate_calls": 0,
    "refit_calls": 0,
    "training_series_calls": 0,
    "validation_series_attempts": 0,
    "other_split_attempts": 0,
    "external_validation_calls": 0,
    "final_test_calls": 0,
}


def _sha(path: Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_blob_sha(path: Path) -> str:
    """Git blob SHA of a tracked file (read-only git introspection)."""
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _die(message: str) -> None:
    """Fail-closed abort: record a BLOCKED marker and exit non-zero."""
    record = {"identity": {"task_id": "NM-R4-V5-PRODUCTION-RERUN-008"}, "blocked_reason": message}
    (REPO / ".agent-memory/evidence/NM-R4-V5-PRODUCTION-RERUN-008/blocked.json").write_text(
        canonical_dumps(record) + "\n", encoding="utf-8"
    )
    print(f"BLOCKED: {message}", flush=True)
    sys.exit(1)


def _guarded_underlying_series(
    *, inventory: Any, split: str, raw_root: Path, processed_root: Path
) -> Any:
    """Fail-closed boundary around the underlying-series construction.

    split="training" -> count and build. split="validation" or any other split
    -> count the attempt and RAISE immediately, making external-validation
    access technically impossible through this harness.
    """
    if split == "training":
        _COUNTERS["training_series_calls"] += 1
        return build_underlying_series(
            inventory=inventory, split=split, raw_root=raw_root, processed_root=processed_root
        )
    if split == "validation":
        _COUNTERS["validation_series_attempts"] += 1
        raise RuntimeError("validation split requested; replay boundary is fail-closed")
    _COUNTERS["other_split_attempts"] += 1
    raise RuntimeError(f"unexpected split requested: {split!r}")


def main() -> None:
    """Execute the deterministic replay exactly once and write the result JSON."""
    start_utc = datetime.datetime.now(datetime.UTC).isoformat()
    print(f"replay start UTC: {start_utc}", flush=True)

    # ---- Preconditions: identity (fail closed) ----
    ident = repository_source_identity()
    print(f"source identity: {json.dumps(ident)}", flush=True)
    gc = ident["git_commit"]
    gd = ident["git_dirty"]
    if gc is None or len(gc) != 40 or any(c not in "0123456789abcdef" for c in gc):
        _die("git_commit invalid/null")
    if gd is not False:
        _die(f"git_dirty {gd!r} not False")

    # ---- Preconditions: frozen config / gate / data identities ----
    config = load_v5_config(CONFIG_PATH)
    config_hash = config.config_hash()
    if config_hash != _EXPECTED_CONFIG_HASH:
        _die(f"config hash mismatch {config_hash}")
    config_file_sha = _sha(CONFIG_PATH)
    if _sha(GATE_YAML) != _EXPECTED_GATE_YAML_SHA:
        _die("gate YAML SHA mismatch")
    gate_spec = load_gate_spec_v2(str(GATE_YAML))
    if gate_spec.spec_hash() != _EXPECTED_GATE_SPEC_HASH:
        _die("gate canonical hash mismatch")

    # ---- Preconditions: canonical artifacts present + replay root absent ----
    canonical_ckpt = CANONICAL_DIR / "checkpoint.pt"
    canonical_curve = CANONICAL_DIR / "training_curve.json"
    canonical_final = CANONICAL_DIR / "checkpoint_final.pt"
    if not all(p.exists() for p in (canonical_ckpt, canonical_curve, canonical_final)):
        _die("canonical production artifacts missing")
    if not CANONICAL_DURABLE_REPORT.exists():
        _die("canonical durable report missing")
    if REPLAY_OUTPUT_ROOT.exists():
        _die(f"replay output root already exists: {REPLAY_OUTPUT_ROOT}")

    # ---- Training-only empirical series via the guarded boundary ----
    inventory = ResearchInventory.model_validate(
        json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    )
    if inventory.inventory_hash != _EXPECTED_INVENTORY_HASH:
        _die("inventory hash mismatch")
    training_series = _guarded_underlying_series(
        inventory=inventory, split="training", raw_root=RAW_ROOT, processed_root=PROCESSED_ROOT
    )
    if training_series.series_sha256 != _EXPECTED_TRAINING_SERIES_SHA:
        _die(f"training series SHA mismatch {training_series.series_sha256}")
    print(f"training series SHA: {training_series.series_sha256}", flush=True)

    training_returns = training_series.returns_array
    session_dates = training_series.session_dates
    return_dates = tuple(session_dates[1:])
    spec = config.windows
    windows = build_windows(training_returns, return_dates, spec)
    feature_matrix = np.stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    cumret_scale = fit_cumret_scale(training_returns, spec.horizon)
    split = split_fit_selection(windows, config.training.fit_fraction, spec)
    statistics = build_v3_statistics(
        split.fit_windows, normalizer, cumret_scale, spec, config.objective
    )
    print(
        f"windows: fit={split.n_fit} selection={split.n_selection} "
        f"selection_target_start={split.selection_target_start_index}",
        flush=True,
    )

    # ---- Deterministic model init (identical order to the canonical run) ----
    device = torch.device("cpu")
    dtype = torch.float32
    configure_determinism(True)
    set_deterministic_seeds(config.training.model_init_seed)
    model = StructuredVolatilityNeuralSde(config.sde).to(device=device, dtype=dtype)
    n_params = count_parameters(model)
    training_returns_tensor = torch.tensor(training_returns, dtype=dtype)

    # Initial selection total loss, computed exactly as the trainer does at
    # epoch 0 (fresh model, generator seeded with data_seed, no noise consumed).
    sel_ctx, sel_targets, _ = _window_tensors(
        split.selection_windows, normalizer, cumret_scale, spec
    )
    initial_sel_gen = torch.Generator().manual_seed(config.training.data_seed)
    init_sel_rbf, init_sel_total = _evaluate_selection_v3(
        model,
        sel_ctx,
        sel_targets,
        cumret_scale,
        spec,
        config.objective,
        statistics.standardizer,
        statistics.bandwidth_sq,
        initial_sel_gen,
    )
    initial_sel_total = float(init_sel_total)
    initial_sel_sig = float(init_sel_rbf)

    # ---- ONE training run ----
    _COUNTERS["training_calls"] += 1
    try:
        outcome = train_internal_v3(
            model,
            config.training,
            split,
            normalizer,
            training_returns_tensor,
            statistics,
            spec,
            config.objective,
        )
    except RuntimeError as exc:
        _die(f"train_internal_v3 runtime scientific failure: {exc}")
    print(
        f"training done: best_epoch={outcome.best_epoch} final_epoch={outcome.final_epoch}",
        flush=True,
    )

    # Selection criterion decomposition (total = signature + weight * variance).
    epoch1_sel_total = float(outcome.selection_total_curve[0])
    best_sel_total = float(outcome.selection_total_curve[outcome.best_epoch - 1])
    best_sel_sig = float(outcome.best_internal_rbf)
    variance_weight = float(config.objective.variance_penalty_coefficient)
    best_sel_var = (best_sel_total - best_sel_sig) / variance_weight
    criterion1_pass = best_sel_total < initial_sel_total
    print(
        f"selection: initial_total={initial_sel_total:.8e} epoch1_total={epoch1_sel_total:.8e} "
        f"best_total={best_sel_total:.8e} improved={criterion1_pass}",
        flush=True,
    )

    # ---- Frozen internal Gate-v2, exactly once ----
    _COUNTERS["gate_calls"] += 1
    gate_diagnostics, gate_passed = evaluate_gate_v2(
        model,
        split,
        normalizer,
        training_returns_tensor,
        spec,
        gate_spec,
    )
    print(f"gate evaluated (1x): gate_passed={gate_passed}", flush=True)

    # ---- Freeze selected checkpoint + curve into the replay output root ----
    REPLAY_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    checkpoint_path = REPLAY_OUTPUT_ROOT / "checkpoint.pt"
    torch.save(
        {
            "model_state": {k: v.cpu() for k, v in model.state_dict().items()},
            "sde_config": asdict(config.sde),
        },
        checkpoint_path,
    )
    curve_path = REPLAY_OUTPUT_ROOT / "training_curve.json"
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
    checkpoint_sha = _sha(checkpoint_path)
    curve_sha = _sha(curve_path)
    print(f"replay selected checkpoint sha={checkpoint_sha}", flush=True)

    # ---- Branch mechanically on the gate result ----
    refit = {"performed": False, "reason": "gate did not pass; replay stopped"}
    final_checkpoint_path = None
    if gate_passed and criterion1_pass:
        _COUNTERS["refit_calls"] += 1
        set_deterministic_seeds(config.training.model_init_seed)
        final_model = StructuredVolatilityNeuralSde(config.sde).to(device=device, dtype=dtype)
        refit_final_v3(
            final_model,
            config.training,
            windows,
            normalizer,
            training_returns_tensor,
            outcome.best_epoch,
            statistics,
            spec,
            config.objective,
        )
        final_checkpoint_path = REPLAY_OUTPUT_ROOT / "checkpoint_final.pt"
        torch.save(
            {
                "model_state": {k: v.cpu() for k, v in final_model.state_dict().items()},
                "sde_config": asdict(config.sde),
            },
            final_checkpoint_path,
        )
        refit = {
            "performed": True,
            "best_epoch_reused": outcome.best_epoch,
            "epoch_count": outcome.best_epoch,
            "all_training_window_count": len(windows),
        }
        print(f"refit frozen: final checkpoint sha={_sha(final_checkpoint_path)}", flush=True)

    # ---- Byte/SHA comparison vs canonical artifacts ----
    def _compare_pair(replay_path: Path, canonical_path: Path) -> dict[str, bool]:
        replay_bytes = replay_path.read_bytes() if replay_path.exists() else b""
        canonical_bytes = canonical_path.read_bytes() if canonical_path.exists() else b""
        return {
            "sha_match": hashlib.sha256(replay_bytes).hexdigest()
            == hashlib.sha256(canonical_bytes).hexdigest(),
            "byte_match": replay_bytes == canonical_bytes,
        }

    selected_cmp = _compare_pair(checkpoint_path, canonical_ckpt)
    curve_cmp = _compare_pair(curve_path, canonical_curve)
    final_cmp = _compare_pair(
        final_checkpoint_path
        if final_checkpoint_path is not None
        else REPLAY_OUTPUT_ROOT / "missing.pt",
        canonical_final,
    )

    # Load canonical gate criteria + artifact hashes from the durable report.
    canonical_report = json.loads(CANONICAL_DURABLE_REPORT.read_text(encoding="utf-8"))
    canonical_criteria = canonical_report["gate"]["criteria"]
    cr = gate_diagnostics["criterion_results"]
    replay_criteria = [
        {
            "id": 1,
            "name": "selection_loss_improvement",
            "value": best_sel_total,
            "result": bool(criterion1_pass),
        },
        {
            "id": 2,
            "name": "variance_ratio",
            "value": gate_diagnostics["variance_ratio"],
            "result": bool(cr["variance_ratio"]),
        },
        {
            "id": 3,
            "name": "terminal_dispersion_ratio",
            "value": gate_diagnostics["terminal_dispersion_ratio"],
            "result": bool(cr["terminal_dispersion"]),
        },
        {
            "id": 4,
            "name": "path_uniqueness",
            "value": gate_diagnostics["path_uniqueness_fraction"],
            "result": bool(cr["uniqueness"]),
        },
        {
            "id": 5,
            "name": "acf1_agreement",
            "value": gate_diagnostics["return_acf1_abs_diff"],
            "result": bool(cr["acf1_agreement"]),
        },
        {
            "id": 6,
            "name": "drift_diffusion_rms_ratio",
            "value": gate_diagnostics["drift_diffusion_rms_ratio"],
            "result": bool(cr["drift_diffusion_ratio"]),
        },
    ]
    gate_exact_match = True
    gate_pairs = []
    for rc, cc in zip(replay_criteria, canonical_criteria, strict=True):
        same = rc["result"] == bool(cc["result"]) and rc["value"] == cc["value"]
        gate_exact_match = gate_exact_match and same
        gate_pairs.append(
            {
                "id": rc["id"],
                "replay_value": rc["value"],
                "canonical_value": cc["value"],
                "exact": bool(same),
            }
        )
    gate_six_of_six = all(c["result"] for c in replay_criteria)

    replay_gate_passed = bool(gate_passed and criterion1_pass and gate_six_of_six)
    reproducibility_result = (
        "EXACT_MATCH"
        if (
            replay_gate_passed
            and selected_cmp["sha_match"]
            and selected_cmp["byte_match"]
            and curve_cmp["sha_match"]
            and curve_cmp["byte_match"]
            and final_cmp["sha_match"]
            and final_cmp["byte_match"]
        )
        else "MISMATCH"
    )

    harness_sha = _sha(HARNESS_PATH)
    result: dict[str, Any] = {
        "governance": {"task_id": "NM-R4-V5-PRODUCTION-RERUN-008", "risk": "R4"},
        "classification": {
            "reproducibility_replay_only": True,
            "new_candidate": False,
            "independent_seed": False,
            "counted_toward_five_seed_study": False,
        },
        "identity": {
            "original_scientific_source_commit": _VALIDATED_SOURCE_COMMIT,
            "original_evidence_commit": "e4b939f76845547c56a13254e783aa28150780e8",
            "replay_git_commit": gc,
            "harness_path": str(HARNESS_PATH),
            "harness_sha256": harness_sha,
            "harness_git_blob": _git_blob_sha(HARNESS_PATH),
            "config_hash": config_hash,
            "config_file_sha256": config_file_sha,
            "gate_spec_hash": gate_spec.spec_hash(),
            "gate_yaml_sha256": _sha(GATE_YAML),
            "training_series_sha256": training_series.series_sha256,
        },
        "original_artifact_hashes": {
            "checkpoint": {
                "sha256": canonical_report["training"]["checkpoint_sha256"],
                "path": str(canonical_ckpt),
            },
            "curve": {
                "sha256": canonical_report["training"]["curve_sha256"],
                "path": str(canonical_curve),
            },
            "final_checkpoint": {
                "sha256": canonical_report["refit"]["final_checkpoint_sha256"],
                "path": str(canonical_final),
            },
        },
        "replay_artifact_hashes": {
            "checkpoint": {"sha256": checkpoint_sha, "path": str(checkpoint_path)},
            "curve": {"sha256": curve_sha, "path": str(curve_path)},
            "final_checkpoint": {
                "sha256": _sha(final_checkpoint_path)
                if final_checkpoint_path is not None
                else None,
                "path": str(final_checkpoint_path) if final_checkpoint_path is not None else None,
            },
        },
        "byte_comparison": {
            "selected_checkpoint_sha_match": bool(selected_cmp["sha_match"]),
            "selected_checkpoint_byte_match": bool(selected_cmp["byte_match"]),
            "training_curve_sha_match": bool(curve_cmp["sha_match"]),
            "training_curve_byte_match": bool(curve_cmp["byte_match"]),
            "final_checkpoint_sha_match": bool(final_cmp["sha_match"]),
            "final_checkpoint_byte_match": bool(final_cmp["byte_match"]),
        },
        "training": {
            "initial_selection_total": initial_sel_total,
            "initial_selection_signature": initial_sel_sig,
            "epoch1_selection_total": epoch1_sel_total,
            "best_selection_total": best_sel_total,
            "best_epoch": outcome.best_epoch,
            "final_epoch": outcome.final_epoch,
            "signature_component": best_sel_sig,
            "variance_component": best_sel_var,
            "variance_weight": variance_weight,
            "objective_decomposition": "selection_total = selection_signature + variance_weight * selection_variance",
            "model_init_seed": config.training.model_init_seed,
            "data_seed": config.training.data_seed,
            "eval_seed": config.training.eval_seed,
            "device": str(device),
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "deterministic": True,
            "n_parameters": n_params,
        },
        "gate": {
            "replay_criteria": replay_criteria,
            "canonical_vs_replay": gate_pairs,
            "passed": gate_six_of_six,
            "total": len(replay_criteria),
            "gate_passed": replay_gate_passed,
            "exact_deterministic_match": bool(gate_exact_match),
            "evaluation_count": 1,
            "bootstrap_seed": gate_diagnostics["bootstrap_seed"],
            "gate_seed": gate_diagnostics["gate_seed"],
            "real_bootstrap_path_count": gate_diagnostics["n_real_bootstrap"],
            "generated_path_count": gate_diagnostics["n_generated"],
            "report_only": {
                "terminal_wasserstein_normalized": gate_diagnostics[
                    "terminal_wasserstein_normalized"
                ],
                "acf_rmse": gate_diagnostics["acf_rmse"],
                "acf_max_error": gate_diagnostics["acf_max_error"],
            },
        },
        "refit": refit,
        "counters": dict(_COUNTERS),
        "external": {
            "external_validation_calls": 0,
            "final_test_calls": 0,
            "validation_series_attempts": _COUNTERS["validation_series_attempts"],
            "other_split_attempts": _COUNTERS["other_split_attempts"],
        },
        "transcript": {"path": str(REPLAY_TRANSCRIPT)},
        "status": reproducibility_result,
    }
    if REPLAY_TRANSCRIPT.exists():
        result["transcript"]["sha256"] = _sha(REPLAY_TRANSCRIPT)

    REPLAY_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPLAY_RESULT_PATH.write_text(canonical_dumps(result) + "\n", encoding="utf-8")
    # Inner evidence copy (gitignored).
    (REPO / ".agent-memory/evidence/NM-R4-V5-PRODUCTION-RERUN-008/replay_result.json").write_text(
        canonical_dumps(result) + "\n", encoding="utf-8"
    )

    end_utc = datetime.datetime.now(datetime.UTC).isoformat()
    print(f"replay end UTC: {end_utc}", flush=True)
    print(f"RESULT STATUS: {reproducibility_result}", flush=True)
    print(f"gate passed: {gate_six_of_six}/{len(replay_criteria)}", flush=True)
    print(f"counters: {json.dumps(_COUNTERS)}", flush=True)
    print(f"result: {REPLAY_RESULT_PATH} sha={_sha(REPLAY_RESULT_PATH)}", flush=True)
    if reproducibility_result != "EXACT_MATCH":
        sys.exit(1)


if __name__ == "__main__":
    main()
