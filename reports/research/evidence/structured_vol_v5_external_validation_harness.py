r"""Frozen one-shot external-validation harness for structured-volatility neural-SDE v5.

Implements EXACTLY the scientific contract frozen in
``reports/protocol/research_protocol_amendment_017.md`` and
``configs/research/structured_vol_v5_external_validation_v1.yaml`` (schema
``structured-vol-v5-external-validation-v1``).

This module is a TRACKED, methodology-free implementation: at future execution
it performs EXACTLY ONE held-out external validation of the canonical frozen
candidate, as a genuine future-distribution forecast from the end of training.

Authorized at future execution (and only then):
- build the TRAINING series and the training-boundary ``w_boundary`` context;
- construct the VALIDATION series exactly once through the guarded wrapper;
- recompute the validation scorecard and byte-verify it against the frozen
  ``validation_empirical`` target;
- load ONLY the canonical frozen checkpoint, simulate 1024x63 paths with the
  frozen seed, score them under the frozen metric spec, compute family errors
  with ``_family_errors``, and compare per-family against the frozen baseline
  suite reference ordering;
- write the immutable confirmatory result exactly once.

NEVER authorized, and IMPOSSIBLE through this module:
- training, refit, replay, tuning, checkpoint substitution, candidate switching;
- final-test access;
- provider / network access;
- any read of raw validation returns other than the single guarded construction
  and the single frozen-target recomputation;
- any second validation-series construction (fails closed before the builder).

Importing this module has NO side effects: no validation load, no artifact
load, no output creation, no evaluation. Only ``main()`` (guarded by
``if __name__ == \"__main__\"``) executes the evaluation.
"""
# ruff: noqa: E501  # pinned 64-hex frozen-id literals + long absolute path literals

from __future__ import annotations

import argparse
import hashlib
import json
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
from neuralmarket.data.research.baseline_suite import (  # noqa: E402
    _DICT_FAMILIES,
    _SCALAR_FAMILIES,
    EVALUATED_COMPARATORS,
    SimulatorBaselineSuiteArtifact,
)
from neuralmarket.data.research.benchmark import (  # noqa: E402
    _family_errors,
    _scorecard_payload,
)
from neuralmarket.data.research.inventory import ResearchInventory  # noqa: E402
from neuralmarket.data.research.sde_windows import (  # noqa: E402
    SdeWindow,
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
)
from neuralmarket.data.research.underlying import build_underlying_series  # noqa: E402
from neuralmarket.eval.scorecard import MetricSpecification, compute_scorecard  # noqa: E402
from neuralmarket.models.structured_vol_sde import (  # noqa: E402
    StructuredVolatilityNeuralSde,
    simulate_structured,
)
from neuralmarket.research.structured_vol_experiment import load_v5_config  # noqa: E402

# ── frozen candidate / contract identity (pinned, content not secret) ───────
CANDIDATE_NAME = "structured-volatility-neural-sde-v5"
CANDIDATE_SOURCE_COMMIT = "357971a67c68492fc0c4f5bf31f94f9685639f65"  # pragma: allowlist secret
CANDIDATE_CONFIG_HASH = (
    "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157"  # pragma: allowlist secret
)
CHECKPOINT_PATH = (
    REPO
    / "data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint_final.pt"
)
CHECKPOINT_SHA256 = (
    "c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4"  # pragma: allowlist secret
)
CONTRACT_VERSION = "structured-vol-v5-external-validation-v1"
AMENDMENT_PATH = REPO / "reports/protocol/research_protocol_amendment_017.md"
AMENDMENT_SHA256 = (
    "9ff02f54c2264ef3b563062738e3d15e5802f6c92d56e88a284e8caae7c12abd"  # pragma: allowlist secret
)
CONTRACT_YAML_PATH = REPO / "configs/research/structured_vol_v5_external_validation_v1.yaml"
CONTRACT_YAML_SHA256 = (
    "c7544e5b7cd70ab93e5c6b0ac747ad5eb882536faefca1f575834f2713658363"  # pragma: allowlist secret
)

METRIC_SPEC = "research-metric-spec-v1"
METRIC_SPEC_HASH = (
    "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"  # pragma: allowlist secret
)
BENCHMARK_HASH = (
    "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"  # pragma: allowlist secret
)
SUITE_PATH = REPO / "data/processed/research/benchmark/simulator_baseline_suite_v1.json"
SUITE_HASH = (
    "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"  # pragma: allowlist secret
)
SUITE_FILE_SHA256 = (
    "28a10b1d23ee225b07a94c2f12a01fa08b627e443f1da5eee1329541b9aa139a"  # pragma: allowlist secret
)

# ── frozen generation semantics ──────────────────────────────────────────────
GENERATION_PATHS = 1024
GENERATION_HORIZON = 63
GENERATION_SEED = 8283
CANDIDATE_KEY = "structured_vol_v5"
MAX_GOVERNED_VALIDATION_CONSTRUCTIONS_FOR_THIS_ARM = 2

# Blinded first governed construction (proven harness identity-check defect;
# value-independent — no validation metrics exposed).
PRIOR_FAILED_ATTEMPT: dict[str, Any] = {
    "task_id": "NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-015",
    "validation_constructed": True,
    "model_simulation": False,
    "failure_classification": "PROVEN_HARNESS_IDENTITY_CHECK_DEFECT",
    "failure_transcript_sha256": (
        "5063b0f0eceaefb53657c869adc46bfaf8293737b9a8b717d9d75a27da58393d"  # pragma: allowlist secret
    ),
    "exit_code_sha256": (
        "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"  # pragma: allowlist secret
    ),
    "blinded": True,
}

# ── future immutable evidence paths (NOT created by this harness) ─────────────
RESULT_PATH = REPO / "reports/research/structured_vol_v5_external_validation_confirmatory.json"
TRANSCRIPT_PATH = REPO / "reports/research/structured_vol_v5_external_validation_stdout.log"
EXIT_CODE_PATH = REPO / "reports/research/structured_vol_v5_external_validation_exit_code.txt"
MANIFEST_PATH = REPO / "reports/research/structured_vol_v5_external_validation_manifest.json"

COMPLETION_LABEL = "EXTERNAL_VALIDATION_COMPLETED"


class ForbiddenActionError(RuntimeError):
    """Raised when a prohibition guard is invoked."""


# ── instrumented counters ────────────────────────────────────────────────────
_COUNTERS: dict[str, int] = {
    "training_series_constructions": 0,
    "validation_series_attempts": 0,
    "validation_series_constructions": 0,
    "external_validation_evaluations": 0,
    "model_simulation_calls": 0,
    "generated_scorecard_calls": 0,
    "validation_scorecard_calls": 0,
    "family_error_calls": 0,
    "baseline_comparison_calls": 0,
    "checkpoint_substitution_attempts": 0,
    "training_calls": 0,
    "refit_calls": 0,
    "tuning_calls": 0,
    "final_test_attempts": 0,
    "provider_calls": 0,
    "network_calls": 0,
}


def counters() -> dict[str, int]:
    """Snapshot of the instrumented counters (copy, not a mutable handle)."""
    return dict(_COUNTERS)


def _forbidden(name: str, message: str) -> None:
    _COUNTERS[name] += 1
    raise ForbiddenActionError(
        f"{name} forbidden by the frozen external-validation contract: {message}"
    )


def guard_training() -> None:
    """Fail-closed guard: training is forbidden by the frozen contract."""
    _forbidden("training_calls", "no training is authorized")


def guard_refit() -> None:
    """Fail-closed guard: refit is forbidden by the frozen contract."""
    _forbidden("refit_calls", "no refit is authorized")


def guard_tuning() -> None:
    """Fail-closed guard: tuning is forbidden by the frozen contract."""
    _forbidden("tuning_calls", "no tuning is authorized")


def guard_final_test() -> None:
    """Fail-closed guard: final-test access is forbidden by the frozen contract."""
    _forbidden("final_test_attempts", "no final-test access is authorized")


def guard_provider() -> None:
    """Fail-closed guard: provider access is forbidden by the frozen contract."""
    _forbidden("provider_calls", "no provider access is authorized")


def guard_network() -> None:
    """Fail-closed guard: network access is forbidden by the frozen contract."""
    _forbidden("network_calls", "no network access is authorized")


# ── canonical checkpoint verification (substitution fails closed) ────────────
def verify_canonical_checkpoint() -> Path:
    """Require the canonical frozen checkpoint path and SHA; substitution raises."""
    if not CHECKPOINT_PATH.is_file():
        _COUNTERS["checkpoint_substitution_attempts"] += 1
        raise RuntimeError(f"canonical checkpoint missing: {CHECKPOINT_PATH}")
    digest = hashlib.sha256(CHECKPOINT_PATH.read_bytes()).hexdigest()
    if digest != CHECKPOINT_SHA256:
        _COUNTERS["checkpoint_substitution_attempts"] += 1
        raise RuntimeError(
            "checkpoint substitution: SHA-256 mismatch "
            f"(got {digest}, expected {CHECKPOINT_SHA256})"
        )
    return CHECKPOINT_PATH


# ── guarded one-shot validation access ───────────────────────────────────────
def build_validation_series_once(
    *,
    inventory: Any,
    raw_root: Path,
    processed_root: Path,
    split: str = "validation",
) -> Any:
    """The ONLY path that constructs the held-out validation series. One shot.

    ``split`` must be exactly ``"validation"``. A second call fails closed
    BEFORE the underlying builder executes.
    """
    if _COUNTERS["validation_series_attempts"] >= 1:
        raise RuntimeError(
            "one-shot validation access violated: a second validation-series construction "
            "was attempted (fails closed before the builder runs)"
        )
    if split != "validation":
        raise ValueError(f"held-out series must be split='validation', got {split!r}")
    _COUNTERS["validation_series_attempts"] += 1
    series = build_underlying_series(
        inventory=inventory, split=split, raw_root=raw_root, processed_root=processed_root
    )
    _COUNTERS["validation_series_constructions"] += 1
    return series


def build_training_series_once(*, inventory: Any, raw_root: Path, processed_root: Path) -> Any:
    """Build the TRAINING series only (instrumented)."""
    _COUNTERS["training_series_constructions"] += 1
    return build_underlying_series(
        inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root
    )


# ── training-boundary context (w_boundary), mirrors frozen v5 production path ─
def build_boundary_context(training_series: Any, spec: Any) -> dict[str, Any]:
    """Deterministic training-boundary context; no validation observation touches it.

    Mirrors ``structured_vol_experiment.run_v5_experiment`` lines 311-321 exactly.
    """
    returns = training_series.returns_array
    session_dates = training_series.session_dates
    return_dates = tuple(session_dates[1:])
    windows = build_windows(returns, return_dates, spec)
    feature_matrix = np.stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    dates = np.asarray(return_dates)
    eval_window = SdeWindow(
        window_id="w_boundary",
        start_index=len(returns) - spec.horizon,
        context_returns=returns[-spec.context_lookback :],
        target_returns=returns[-spec.horizon :],
        context_start_date=str(dates[-spec.context_lookback]),
        context_end_date=str(session_dates[-1]),
        target_start_date=str(dates[-spec.horizon]),
        target_end_date=str(session_dates[-1]),
    )
    context_hash = hashlib.sha256(
        canonical_dumps(
            {
                "window_id": eval_window.window_id,
                "start_index": eval_window.start_index,
                "context_returns": [float(v) for v in eval_window.context_returns],
                "target_returns": [float(v) for v in eval_window.target_returns],
            }
        ).encode("utf-8")
    ).hexdigest()
    return {
        "eval_context": normalizer.normalize(compute_context_features(eval_window, spec).array()),
        "eval_window": eval_window,
        "normalizer": normalizer,
        "normalizer_hash": normalizer.normalizer_hash(),
        "cumret_scale": float(fit_cumret_scale(returns, spec.horizon)),
        "initial_price": float(training_series.prices[-1]),
        "context_hash": context_hash,
    }


# ── frozen-target recomputation and byte-identity verification ───────────────
def _normalize_mapping_keys(value: Any) -> Any:
    """Recursively normalize mapping keys to strings; values are never altered."""
    if isinstance(value, dict):
        return {str(key): _normalize_mapping_keys(child) for key, child in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_mapping_keys(child) for child in value]
    return value


def recompute_validation_target(
    validation_series: Any, spec_metric: MetricSpecification
) -> dict[str, Any]:
    """Recompute the validation scorecard exactly once, under the frozen spec."""
    _COUNTERS["validation_scorecard_calls"] += 1
    returns = validation_series.returns_array
    return _scorecard_payload(compute_scorecard(returns, spec_metric.scorecard))


def _canonical_identity(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()


def verify_frozen_target(
    recomputed: dict[str, Any], frozen: dict[str, Any]
) -> dict[str, str | bool]:
    """Byte-identity check against the frozen validation_empirical target.

    Both payloads are first normalized to a common string-key representation so
    value-independent integer-vs-string mapping-key ordering does not affect
    identity. No numerical tolerance — exact equality required. On mismatch,
    non-sensitive structural diagnostics (hashes, JSON path) are computed before
    failing closed.
    """

    def _first_mismatch_path(a: Any, b: Any, prefix: str = "") -> str | None:
        if type(a) is not type(b):
            return prefix or "/"
        if isinstance(a, dict):
            a_keys = set(a)
            b_keys = set(b)
            if a_keys != b_keys:
                return prefix or "/"
            for key in a_keys:
                suspect = _first_mismatch_path(
                    a[key], b[key], f"{prefix}/{key}" if prefix else f"/{key}"
                )
                if suspect is not None:
                    return suspect
            return None
        if isinstance(a, list | tuple):
            if len(a) != len(b):
                return prefix or "/"
            for i in range(len(a)):
                suspect = _first_mismatch_path(a[i], b[i], f"{prefix}[{i}]")
                if suspect is not None:
                    return suspect
            return None
        return None if a == b else prefix or "/"

    normalized_recomputed = _normalize_mapping_keys(recomputed)
    normalized_frozen = _normalize_mapping_keys(frozen)
    recomputed_bytes = canonical_dumps(normalized_recomputed).encode("utf-8")
    frozen_bytes = canonical_dumps(normalized_frozen).encode("utf-8")
    match = recomputed_bytes == frozen_bytes
    if not match:
        recomputed_identity = hashlib.sha256(recomputed_bytes).hexdigest()
        frozen_identity = hashlib.sha256(frozen_bytes).hexdigest()
        mismatch_path = _first_mismatch_path(normalized_recomputed, normalized_frozen)
        raise RuntimeError(
            "validation target does not match the frozen validation_empirical "
            "(byte/canonical identity mismatch); refusing to compare ["
            f"recomputed={recomputed_identity} frozen={frozen_identity}"
            f" path={mismatch_path}]"
        )
    recomputed_identity = hashlib.sha256(recomputed_bytes).hexdigest()
    frozen_identity = hashlib.sha256(frozen_bytes).hexdigest()
    return {
        "recomputed_identity": recomputed_identity,
        "frozen_identity": frozen_identity,
        "match": True,
    }


# ── generation: frozen geometry, shape and nonfinite fail-closed guards ──────
def generate_paths(model: Any, eval_context: np.ndarray, seed: int = GENERATION_SEED) -> np.ndarray:
    """Forward simulation from the frozen training-boundary context only."""
    _COUNTERS["model_simulation_calls"] += 1
    ctx_tensor = torch.tensor(
        [[float(v) for v in eval_context]] * GENERATION_PATHS, dtype=torch.float32
    )
    with torch.no_grad():
        generated = simulate_structured(model, ctx_tensor, seed=seed)
    increments = generated.detach().cpu().numpy()
    if increments.shape != (GENERATION_PATHS, GENERATION_HORIZON):
        raise RuntimeError(
            f"generated shape {increments.shape} != frozen ({GENERATION_PATHS}, {GENERATION_HORIZON})"
        )
    if not np.isfinite(increments).all():
        raise RuntimeError("generated increments contain NaN/Inf; refusing to score")
    return increments


def compute_generated_scorecard(
    increments: np.ndarray, spec_metric: MetricSpecification
) -> dict[str, Any]:
    """Scored exactly as the frozen baseline convention (ravel, frozen config)."""
    _COUNTERS["generated_scorecard_calls"] += 1
    return _scorecard_payload(compute_scorecard(increments.ravel(), spec_metric.scorecard))


def _all_numbers_finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_all_numbers_finite(v) for v in value.values())
    if isinstance(value, list | tuple):
        return all(_all_numbers_finite(v) for v in value)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return bool(np.isfinite(float(value)))
    return True


def compute_family_errors(
    generated_scorecard: dict[str, Any], verified_target: dict[str, Any]
) -> dict[str, Any]:
    """Generic family-error comparison; refuses non-finite output."""
    _COUNTERS["family_error_calls"] += 1
    errors = _family_errors(generated_scorecard, verified_target)
    if not _all_numbers_finite(errors):
        raise RuntimeError("family-error comparison produced non-finite values; refusing to report")
    return errors


# ── validation-only family comparison (exact mirror of frozen _comparison_block) ─
def _family_block(baseline_errors: dict[str, float], candidate_error: float) -> dict[str, Any]:
    baseline_ranked = sorted(baseline_errors, key=baseline_errors.__getitem__)
    all_errors = dict(baseline_errors)
    all_errors[CANDIDATE_KEY] = candidate_error
    all_ranked = sorted(all_errors, key=all_errors.__getitem__)
    return {
        "candidate_error": float(candidate_error),
        "nearest_baseline_name": baseline_ranked[0],
        "nearest_baseline_error": float(baseline_errors[baseline_ranked[0]]),
        "candidate_rank_among_6": all_ranked.index(CANDIDATE_KEY) + 1,
        "baseline_reference_ranking": baseline_ranked,
        "all_errors": {k: (None if v == float("inf") else float(v)) for k, v in all_errors.items()},
    }


def validation_family_comparison(
    suite: Any, neural_family: dict[str, Any], *, candidate_key: str = CANDIDATE_KEY
) -> dict[str, dict[str, Any]]:
    """Per-family v5-vs-baseline comparison on the VALIDATION split only.

    Mirrors ``neural_sde_experiment._comparison_block`` (validation arm) with the
    candidate presented under ``candidate_key``; no aggregate, no overall winner.
    """
    _COUNTERS["baseline_comparison_calls"] += 1
    discrepancies = suite.discrepancies["validation"]
    comparison: dict[str, dict[str, Any]] = {}
    for family in _SCALAR_FAMILIES:
        errors = {
            name: abs(float(discrepancies[name][family]["relative_error"]))
            for name in EVALUATED_COMPARATORS
        }
        candidate_error = abs(float(neural_family[family]["relative_error"]))
        comparison[family] = _family_block(errors, candidate_error)
    for family in _DICT_FAMILIES:
        errors: dict[str, float] = {}
        for name in EVALUATED_COMPARATORS:
            value = discrepancies[name][family]["mean_abs_relative_error"]
            errors[name] = float("inf") if value is None else abs(float(value))
        candidate_value = neural_family[family]["mean_abs_relative_error"]
        candidate_error = float("inf") if candidate_value is None else abs(float(candidate_value))
        comparison[family] = _family_block(errors, candidate_error)
    return comparison


# ── write-once immutable result ───────────────────────────────────────────────
def write_result_once(result: dict[str, Any], path: Path) -> str:
    """Exclusive-create immutable result write; an existing file is never touched."""
    if path.exists():
        raise RuntimeError(f"refusing to overwrite existing result: {path}")
    payload = canonical_dumps(result) + "\n"
    with open(path, "x", encoding="utf-8") as handle:  # O_CREAT|O_EXCL: atomic fail-closed
        handle.write(payload)
    return str(path)


# ── contract-identity gate (before any validation construction) ──────────────
def verify_contract_identities(
    *,
    config_path: Path,
    benchmark_path: Path,
    suite_path: Path,
    suite_hash: str,
    suite_file_sha256: str,
) -> tuple[Any, Any, Any]:
    """Fail-closed verification of every frozen identity before the boundary."""
    config = load_v5_config(config_path)
    if config.config_hash() != CANDIDATE_CONFIG_HASH:
        raise RuntimeError("model config hash does not match the frozen candidate")
    if hashlib.sha256(AMENDMENT_PATH.read_bytes()).hexdigest() != AMENDMENT_SHA256:
        raise RuntimeError("Amendment 017 bytes do not match the frozen amendment SHA")
    if hashlib.sha256(CONTRACT_YAML_PATH.read_bytes()).hexdigest() != CONTRACT_YAML_SHA256:
        raise RuntimeError("external-validation contract YAML bytes do not match the frozen SHA")
    spec = MetricSpecification()
    if spec.spec_hash() != METRIC_SPEC_HASH:
        raise RuntimeError("metric specification hash does not match the frozen spec")
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if benchmark["benchmark_hash"] != BENCHMARK_HASH:
        raise RuntimeError("empirical benchmark hash does not match the frozen binding")
    if hashlib.sha256(suite_path.read_bytes()).hexdigest() != suite_file_sha256:
        raise RuntimeError("baseline suite file bytes do not match the frozen file SHA")
    suite = SimulatorBaselineSuiteArtifact.model_validate(
        json.loads(suite_path.read_text(encoding="utf-8"))
    )
    if suite.suite_hash != suite_hash:
        raise RuntimeError("baseline suite hash does not match the frozen binding")
    if suite.metric_spec_hash != METRIC_SPEC_HASH or suite.benchmark_hash != BENCHMARK_HASH:
        raise RuntimeError(
            "baseline suite metric/benchmark bindings do not match the frozen contract"
        )
    return config, benchmark, suite


# ── orchestration ─────────────────────────────────────────────────────────────
def run(
    *,
    config_path: Path,
    inventory_path: Path,
    benchmark_path: Path,
    suite_path: Path,
    raw_root: Path,
    processed_root: Path,
    task_id: str,
    result_path: Path = RESULT_PATH,
) -> dict[str, Any]:
    """Execute the one-shot external validation; returns and freezes the result."""
    if _COUNTERS["external_validation_evaluations"] >= 1:
        raise RuntimeError("one-shot evaluation already performed; refusing a second evaluation")
    _COUNTERS["external_validation_evaluations"] += 1

    config, benchmark, suite = verify_contract_identities(
        config_path=config_path,
        benchmark_path=benchmark_path,
        suite_path=suite_path,
        suite_hash=SUITE_HASH,
        suite_file_sha256=SUITE_FILE_SHA256,
    )
    source_identity = repository_source_identity()
    spec_metric = MetricSpecification()

    training_series = build_training_series_once(
        inventory=ResearchInventory.model_validate(
            json.loads(inventory_path.read_text(encoding="utf-8"))
        ),
        raw_root=raw_root,
        processed_root=processed_root,
    )
    boundary = build_boundary_context(training_series, config.windows)

    validation_series = build_validation_series_once(
        inventory=ResearchInventory.model_validate(
            json.loads(inventory_path.read_text(encoding="utf-8"))
        ),
        raw_root=raw_root,
        processed_root=processed_root,
    )
    if validation_series.series_sha256 != suite.validation_series_sha256:
        raise RuntimeError("validation series SHA does not match the frozen suite binding")

    # Reconstruct the held-out target once; byte-verify against the frozen target.
    validation_target = recompute_validation_target(validation_series, spec_metric)
    frozen_target = suite.metrics["validation_empirical"]
    target_verification = verify_frozen_target(validation_target, frozen_target)

    # Canonical checkpoint only. weights_only=True is safe: the frozen checkpoint
    # payload is a dict of tensors + plain sde_config scalars (no arbitrary objects).
    checkpoint_path = verify_canonical_checkpoint()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if set(checkpoint.keys()) != {"model_state", "sde_config"}:
        _COUNTERS["checkpoint_substitution_attempts"] += 1
        raise RuntimeError("checkpoint payload does not match the frozen schema")
    if checkpoint["sde_config"] != asdict(config.sde):
        _COUNTERS["checkpoint_substitution_attempts"] += 1
        raise RuntimeError("checkpoint sde_config does not match the frozen v5 config")

    model = StructuredVolatilityNeuralSde(config.sde)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    increments = generate_paths(model, boundary["eval_context"], seed=GENERATION_SEED)
    generated_scorecard = compute_generated_scorecard(increments, spec_metric)
    neural_family = compute_family_errors(generated_scorecard, frozen_target)
    comparison = validation_family_comparison(suite, neural_family)

    validation_returns = validation_series.returns_array
    result = {
        "governance": {
            "task_id": task_id,
            "risk": "R4",
            "status": COMPLETION_LABEL,
            "mode": "report_only",
        },
        "candidate": {
            "name": CANDIDATE_NAME,
            "source_commit": CANDIDATE_SOURCE_COMMIT,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": CHECKPOINT_SHA256,
            "config_hash": CANDIDATE_CONFIG_HASH,
        },
        "contract": {
            "version": CONTRACT_VERSION,
            "amendment_sha256": hashlib.sha256(AMENDMENT_PATH.read_bytes()).hexdigest(),
            "yaml_sha256": hashlib.sha256(CONTRACT_YAML_PATH.read_bytes()).hexdigest(),
        },
        "validation_identity": {
            "series_sha256": validation_series.series_sha256,
            "split": validation_series.split,
            "first_date": str(validation_series.session_dates[0]),
            "last_date": str(validation_series.session_dates[-1]),
            "observation_count": len(validation_returns),
        },
        "target_verification": target_verification,
        "conditioning": {
            "mode": "training_boundary",
            "context_window_id": boundary["eval_window"].window_id,
            "context_source": "final eligible training context (w_boundary; last 22 training returns)",
            "context_first_date": boundary["eval_window"].context_start_date,
            "context_last_date": boundary["eval_window"].context_end_date,
            "context_hash": boundary["context_hash"],
        },
        "generation": {
            "seed": GENERATION_SEED,
            "paths": GENERATION_PATHS,
            "horizon": GENERATION_HORIZON,
            "shape": [GENERATION_PATHS, GENERATION_HORIZON],
        },
        "metric": {
            "spec_hash": METRIC_SPEC_HASH,
            "scorecard_implementation": "neuralmarket.eval.scorecard.compute_scorecard",
            "family_error_method": "neuralmarket.data.research.benchmark._family_errors",
        },
        "baseline": {
            "suite_file_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
            "suite_hash": suite.suite_hash,
            "comparators": list(EVALUATED_COMPARATORS),
            "reference_ranking": suite.rankings["validation"],
        },
        "external_metrics": {
            "generated_scorecard": generated_scorecard,
            "family_errors": neural_family,
            "comparison": comparison,
        },
        "effective_max_governed_validations": MAX_GOVERNED_VALIDATION_CONSTRUCTIONS_FOR_THIS_ARM,
        "terminal_no_tolerance_policy": True,
        "counters": counters(),
        "runtime_source": {
            "git_commit": source_identity["git_commit"],
            "git_dirty": source_identity["git_dirty"],
        },
        "prior_failed_attempt": dict(PRIOR_FAILED_ATTEMPT),
        "status": COMPLETION_LABEL,
    }
    write_result_once(result, result_path)
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (only executed as a script; importing has no side effects)."""
    parser = argparse.ArgumentParser(description="Run the frozen v5 one-shot external validation")
    parser.add_argument("--config", required=True, help="frozen v5 experiment YAML")
    parser.add_argument("--inventory", required=True, help="frozen research inventory JSON")
    parser.add_argument("--benchmark", required=True, help="accepted empirical benchmark JSON")
    parser.add_argument("--suite", required=True, help="frozen simulator baseline suite JSON")
    parser.add_argument("--raw-root", required=True, help="checksum-verified raw tree root")
    parser.add_argument("--processed-root", required=True, help="validated normalized tree root")
    parser.add_argument("--task-id", required=True, help="governed execution task id")
    parser.add_argument("--result", default=str(RESULT_PATH), help="immutable result path")
    args = parser.parse_args(argv)

    result = run(
        config_path=Path(args.config),
        inventory_path=Path(args.inventory),
        benchmark_path=Path(args.benchmark),
        suite_path=Path(args.suite),
        raw_root=Path(args.raw_root),
        processed_root=Path(args.processed_root),
        task_id=args.task_id,
        result_path=Path(args.result),
    )
    stage = [
        "v5 external-validation stage complete",
        f"status={result['status']}",
        f"validation_attempts={result['counters']['validation_series_attempts']} "
        f"constructions={result['counters']['validation_series_constructions']}",
        f"evaluations={result['counters']['external_validation_evaluations']}",
        "prohibitions: "
        + ", ".join(
            f"{k}={result['counters'][k]}"
            for k in (
                "training_calls",
                "refit_calls",
                "tuning_calls",
                "final_test_attempts",
                "provider_calls",
                "network_calls",
            )
        ),
    ]
    print("\n".join(stage))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
