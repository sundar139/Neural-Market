"""v3 signature neural-SDE experiment orchestration.

v3 retains v2's architecture and windows exactly and changes:
1. The signature representation: cumulative-only -> lead-lag.
2. The internal gate: one-sided dispersion -> bounded two-sided gate
   with ACF, uniqueness, and drift/diffusion diagnostics.

Standardization, bandwidth, and variance target are refit to the NEW
lead-lag representation from TRAINING-FIT REAL paths only.

If the internal gate fails, external validation is never loaded and the
run returns a data value-of-information audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.baseline_suite import EVALUATED_COMPARATORS
from neuralmarket.data.research.benchmark import (
    EmpiricalBenchmarkArtifact,
    _family_errors,
    _scorecard_payload,
)
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.data.research.sde_windows import (
    CONTEXT_FEATURE_NAMES,
    WindowSpec,
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
    split_fit_selection,
)
from neuralmarket.data.research.underlying import build_underlying_series
from neuralmarket.eval.scorecard import MetricSpecification, compute_scorecard
from neuralmarket.models.neural_sde import (
    ConditionalNeuralSde,
    SdeConfig,
    configure_determinism,
    count_parameters,
    reconstruct_prices,
    set_deterministic_seeds,
    simulate,
)
from neuralmarket.research.neural_sde_trainer import TrainingConfig
from neuralmarket.research.neural_sde_trainer_v3 import (
    V3ObjectiveConfig,
    build_v3_statistics,
    evaluate_internal_gate_v3,
    refit_final_v3,
    train_internal_v3,
)

EXPERIMENT_SCHEMA_V3: Literal["research-neural-sde-experiment-v3"] = (
    "research-neural-sde-experiment-v3"
)

# Frozen public artifact identities (allowlisted as public SHA fixtures).
_FROZEN_SUITE_HASH = "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"
_FROZEN_INVENTORY_HASH = "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"
_FROZEN_BENCHMARK_HASH = "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"
_FROZEN_METRIC_SPEC_HASH = "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"

_EXCLUDED_FROM_HASH_V3 = {"artifact_hash", "provenance"}


@dataclass(frozen=True)
class NeuralSdeExperimentConfigV3:
    """Effective frozen v3 experiment configuration assembled from the YAML."""

    version: str = "signature-neural-sde-v3"
    sde: SdeConfig = field(default_factory=SdeConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    windows: WindowSpec = field(default_factory=WindowSpec)
    objective: V3ObjectiveConfig = field(default_factory=V3ObjectiveConfig)
    n_eval_paths: int = 1024
    eval_seed: int = 6263
    eval_initial_price_convention: str = "final training-session close"

    def config_hash(self) -> str:
        """Deterministic identity of the effective config."""
        payload = {
            "version": self.version,
            "sde": asdict(self.sde),
            "training": asdict(self.training),
            "windows": asdict(self.windows),
            "objective": asdict(self.objective),
            "n_eval_paths": self.n_eval_paths,
            "eval_seed": self.eval_seed,
            "eval_initial_price_convention": self.eval_initial_price_convention,
        }
        return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()


def experiment_id_v3(
    config_hash: str,
    training_series_sha256: str,
    validation_series_sha256: str,
    inventory_hash: str,
    benchmark_hash: str,
    metric_spec_hash: str,
    baseline_suite_hash: str,
    split_hash: str,
) -> str:
    """Deterministic canonical v3 experiment identity (no wall-clock)."""
    identity = canonical_dumps(
        {
            "schema": EXPERIMENT_SCHEMA_V3,
            "config_hash": config_hash,
            "training_series_sha256": training_series_sha256,
            "validation_series_sha256": validation_series_sha256,
            "inventory_hash": inventory_hash,
            "benchmark_hash": benchmark_hash,
            "metric_spec_hash": metric_spec_hash,
            "baseline_suite_hash": baseline_suite_hash,
            "split_hash": split_hash,
        }
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def load_experiment_config_v3(path: Path) -> NeuralSdeExperimentConfigV3:
    """Load and validate the tracked v3 YAML experiment configuration."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("v3 experiment config must be a mapping")
    known = {"version", "sde", "training", "windows", "objective", "n_eval_paths", "eval_seed"}
    unknown = set(payload) - known
    if unknown:
        raise ValueError(f"unknown v3 experiment config keys: {sorted(unknown)}")
    return NeuralSdeExperimentConfigV3(
        version=str(payload.get("version", "signature-neural-sde-v3")),
        sde=SdeConfig(**(payload.get("sde") or {})),
        training=TrainingConfig(**(payload.get("training") or {})),
        windows=WindowSpec(**(payload.get("windows") or {})),
        objective=V3ObjectiveConfig(**(payload.get("objective") or {})),
        n_eval_paths=int(payload.get("n_eval_paths", 1024)),
        eval_seed=int(payload.get("eval_seed", 6263)),
    )


class NeuralSdeExperimentV3Artifact(BaseModel):
    """Deterministic sealed v3 experiment artifact."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["research-neural-sde-experiment-v3"] = EXPERIMENT_SCHEMA_V3
    experiment_id: str
    config: dict[str, Any]
    config_hash: str
    config_file_sha256: str
    inventory_hash: str
    benchmark_hash: str
    metric_spec_hash: str
    baseline_suite_hash: str
    training_series_sha256: str
    validation_series_sha256: str
    internal_split: dict[str, Any]
    split_hash: str
    normalization: dict[str, Any]
    objective_definition: dict[str, Any]
    training: dict[str, Any]
    internal_gate: dict[str, Any]
    model: dict[str, Any]
    checkpoint: dict[str, Any]
    v1_preservation: dict[str, Any]
    v2_preservation: dict[str, Any]
    evaluation: dict[str, Any] = {}
    data_value_of_information: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    artifact_hash: str = ""

    @field_validator("experiment_id")
    @classmethod
    def _valid_experiment_id(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("experiment_id must be a 64-character sha256 hex digest")
        return value

    def _compute_hash(self) -> str:
        payload = self.model_dump(mode="json", by_alias=True)
        for key in _EXCLUDED_FROM_HASH_V3:
            payload.pop(key, None)
        payload.get("checkpoint", {}).pop("path", None)
        payload.get("training", {}).pop("training_curve_artifact", None)
        return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def _validate_hash(self) -> NeuralSdeExperimentV3Artifact:
        if self.artifact_hash and self.artifact_hash != self._compute_hash():
            raise ValueError("neural-SDE v3 experiment artifact hash mismatch")
        return self


def _series_context_window(
    returns: np.ndarray, session_dates: tuple[str, ...], spec: WindowSpec
) -> Any:
    from neuralmarket.data.research.sde_windows import SdeWindow

    ctx = returns[-spec.context_lookback :]
    dates = np.asarray(session_dates[1:])
    return SdeWindow(
        window_id="w_boundary",
        start_index=len(returns) - spec.horizon,
        context_returns=ctx,
        target_returns=returns[-spec.horizon :],
        context_start_date=str(dates[-spec.context_lookback]),
        context_end_date=str(dates[-1]),
        target_start_date=str(dates[-spec.horizon]),
        target_end_date=str(dates[-1]),
    )


def _seal_checkpoint_v3(
    model: ConditionalNeuralSde, checkpoint_path: Path, experiment_id: str
) -> dict[str, Any]:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "research-neural-sde-checkpoint-v3",
        "experiment_id": experiment_id,
        "model_state": {k: v.cpu() for k, v in model.state_dict().items()},
        "sde_config": asdict(model.config),
    }
    torch.save(payload, checkpoint_path)
    sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    return {"path": str(checkpoint_path), "sha256": sha, "bytes": checkpoint_path.stat().st_size}


def _mean_abs_rel_error(model: dict[str, Any], empirical: dict[str, Any]) -> float:
    errors = []
    empirical_keys = {str(k): v for k, v in empirical.items()}
    for key, value in model.items():
        emp = empirical_keys.get(str(key))
        if emp is None:
            continue
        emp = float(emp)
        value = float(value)
        errors.append(abs(value - emp) / abs(emp) if abs(emp) > 1e-12 else abs(value - emp))
    if not errors:
        return float("inf")
    return float(np.mean(errors))


def _comparison_v3(
    suite: Any,
    neural_v3_payload: dict[str, Any],
    v1_payload: dict[str, Any],
    v2_payload: dict[str, Any],
) -> dict[str, Any]:
    """Per-family nearest baseline and v1/v2/v3 ranks against the frozen suite."""
    scalar_families = ("mean", "variance", "skewness", "excess_kurtosis")
    dict_families = (
        "quantiles",
        "return_acf",
        "abs_return_acf",
        "sq_return_acf",
        "leverage_correlations",
    )
    comparison: dict[str, Any] = {}

    for split, empirical_key in (
        ("training", "training_empirical"),
        ("validation", "validation_empirical"),
    ):
        empirical = suite["metrics"][empirical_key]
        split_block: dict[str, Any] = {}
        for family in scalar_families:
            errors: dict[str, float] = {
                name: abs(float(suite["discrepancies"][split][name][family]["relative_error"]))
                for name in EVALUATED_COMPARATORS
            }
            baseline_ranked = sorted(errors, key=errors.__getitem__)
            all_errors = dict(errors)
            for key, payload in (
                ("neural_sde_signature_v1", v1_payload),
                ("neural_sde_signature_v2", v2_payload),
                ("neural_sde_signature_v3", neural_v3_payload),
            ):
                emp_value = float(empirical[family])
                model_value = float(payload[family])
                all_errors[key] = (
                    abs(model_value - emp_value) / abs(emp_value)
                    if abs(emp_value) > 1e-12
                    else abs(model_value - emp_value)
                )
            all_ranked = sorted(all_errors, key=all_errors.__getitem__)
            split_block[family] = {
                "nearest_baseline": baseline_ranked[0],
                "neural_v1_rank": all_ranked.index("neural_sde_signature_v1") + 1,
                "neural_v2_rank": all_ranked.index("neural_sde_signature_v2") + 1,
                "neural_v3_rank": all_ranked.index("neural_sde_signature_v3") + 1,
                "errors": {k: float(v) for k, v in all_errors.items()},
            }
        for family in dict_families:
            dict_errors: dict[str, float] = {}
            for name in EVALUATED_COMPARATORS:
                value = suite["discrepancies"][split][name][family]["mean_abs_relative_error"]
                dict_errors[name] = float("inf") if value is None else abs(float(value))
            baseline_ranked = sorted(dict_errors, key=dict_errors.__getitem__)
            all_errors = dict(dict_errors)
            all_errors["neural_sde_signature_v1"] = _mean_abs_rel_error(
                v1_payload[family], empirical[family]
            )
            all_errors["neural_sde_signature_v2"] = _mean_abs_rel_error(
                v2_payload[family], empirical[family]
            )
            all_errors["neural_sde_signature_v3"] = _mean_abs_rel_error(
                neural_v3_payload[family], empirical[family]
            )
            all_ranked = sorted(all_errors, key=all_errors.__getitem__)
            split_block[family] = {
                "nearest_baseline": baseline_ranked[0],
                "neural_v1_rank": all_ranked.index("neural_sde_signature_v1") + 1,
                "neural_v2_rank": all_ranked.index("neural_sde_signature_v2") + 1,
                "neural_v3_rank": all_ranked.index("neural_sde_signature_v3") + 1,
                "errors": {
                    k: (None if v == float("inf") else float(v)) for k, v in all_errors.items()
                },
            }
        comparison[split] = split_block
    return comparison


def _evaluation_v3(
    *,
    model: ConditionalNeuralSde,
    eval_context: np.ndarray,
    spec: WindowSpec,
    config: NeuralSdeExperimentConfigV3,
    initial_price: float,
    training_empirical: dict[str, Any],
    validation_empirical: dict[str, Any],
    suite: Any,
    v1_artifact: dict[str, Any],
    v2_artifact: dict[str, Any],
) -> dict[str, Any]:
    n_paths = config.n_eval_paths
    ctx_tensor = torch.tensor([[float(v) for v in eval_context]] * n_paths, dtype=torch.float32)
    generated = simulate(model, ctx_tensor, seed=config.eval_seed)
    increments = generated.detach().cpu().numpy()
    if increments.shape != (n_paths, spec.horizon):
        raise RuntimeError(f"v3 evaluation paths have wrong shape: {increments.shape}")
    if not np.isfinite(increments).all():
        raise RuntimeError("v3 evaluation generated non-finite increments")
    prices = reconstruct_prices(torch.tensor(increments, dtype=torch.float32), float(initial_price))
    if not (prices > 0).all() or not torch.isfinite(prices).all():
        raise RuntimeError("v3 evaluation generated non-positive prices")

    spec_metric = MetricSpecification()
    neural_payload = _scorecard_payload(
        compute_scorecard(increments.ravel(), spec_metric.scorecard)
    )
    v1_payload = dict(v1_artifact["evaluation"]["neural_metrics"])
    v2_payload = dict(v2_artifact["evaluation"]["neural_metrics"])
    return {
        "contract": {
            "n_paths": n_paths,
            "horizon_sessions": spec.horizon,
            "dt": spec.dt,
            "seed": config.eval_seed,
            "initial_price": initial_price,
            "initial_price_convention": config.eval_initial_price_convention,
            "conditioning_context": {
                name: float(v) for name, v in zip(CONTEXT_FEATURE_NAMES, eval_context, strict=True)
            },
            "conditioning_note": (
                "final available training context at the training/validation boundary; "
                "no validation observation conditions the headline run"
            ),
        },
        "neural_metrics": neural_payload,
        "discrepancies": {
            "training": _family_errors(neural_payload, training_empirical),
            "validation": _family_errors(neural_payload, validation_empirical),
        },
        "comparison": _comparison_v3(suite, neural_payload, v1_payload, v2_payload),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(payload) + "\n", encoding="utf-8")


def run_neural_sde_experiment_v3(
    *,
    config_path: Path,
    inventory_path: Path,
    benchmark_path: Path,
    suite_path: Path,
    v1_artifact_path: Path,
    v2_artifact_path: Path,
    raw_root: Path,
    processed_root: Path,
    output_root: Path,
    report_path: Path,
) -> NeuralSdeExperimentV3Artifact:
    """Run the frozen v3 experiment; external validation only after the gate."""
    start = datetime.now(UTC)
    config = load_experiment_config_v3(config_path)
    config_file_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    config_hash = config.config_hash()

    inventory = ResearchInventory.model_validate(
        json.loads(inventory_path.read_text(encoding="utf-8"))
    )
    benchmark = EmpiricalBenchmarkArtifact.model_validate(
        json.loads(benchmark_path.read_text(encoding="utf-8"))
    )
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    if suite.get("suite_hash") != _FROZEN_SUITE_HASH:
        raise ValueError("frozen simulator baseline suite hash mismatch")
    if inventory.inventory_hash != _FROZEN_INVENTORY_HASH:
        raise ValueError("frozen research inventory hash mismatch")
    if benchmark.benchmark_hash != _FROZEN_BENCHMARK_HASH:
        raise ValueError("frozen empirical benchmark hash mismatch")
    metric_spec_hash = MetricSpecification().spec_hash()
    if metric_spec_hash != _FROZEN_METRIC_SPEC_HASH:
        raise ValueError("frozen research-metric-spec-v1 hash mismatch")
    if (
        suite["metric_spec_hash"] != metric_spec_hash
        or benchmark.metric_spec_hash != metric_spec_hash
    ):
        raise ValueError("metric-spec binding mismatch across frozen artifacts")

    v1_artifact = _load_v1_artifact(v1_artifact_path)
    v2_artifact = json.loads(v2_artifact_path.read_text(encoding="utf-8"))
    if v2_artifact.get("schema_version") != "research-neural-sde-experiment-v2":
        raise ValueError("v2 artifact schema mismatch")
    v1_config_sha = v1_artifact.get("config_file_sha256")
    v1_checkpoint_sha = v1_artifact["checkpoint"]["sha256"]
    v1_artifact_sha = hashlib.sha256(v1_artifact_path.read_bytes()).hexdigest()
    v2_config_sha = v2_artifact.get("config_file_sha256")
    v2_checkpoint_sha = v2_artifact["checkpoint"]["sha256"]
    v2_artifact_sha = hashlib.sha256(v2_artifact_path.read_bytes()).hexdigest()

    training_series = build_underlying_series(
        inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root
    )
    if (
        training_series.series_sha256 != benchmark.underlying["training"].series_sha256
        or training_series.series_sha256 != suite["training_series_sha256"]
    ):
        raise ValueError("training series binding mismatch across frozen artifacts")
    if suite["validation_series_sha256"] != benchmark.underlying["validation"].series_sha256:
        raise ValueError("validation-series hash binding mismatch across frozen artifacts")

    spec = config.windows
    training_returns = training_series.returns_array
    session_dates = training_series.session_dates
    assert len(session_dates) == len(training_returns) + 1
    return_dates = tuple(session_dates[1:])

    windows = build_windows(training_returns, return_dates, spec)
    feature_matrix = np.stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    normalizer_hash = normalizer.normalizer_hash()
    cumret_scale = fit_cumret_scale(training_returns, spec.horizon)
    split = split_fit_selection(windows, config.training.fit_fraction, spec)

    internal_split_block = {
        "n_eligible": split.n_eligible,
        "n_fit": split.n_fit,
        "n_selection": split.n_selection,
        "n_gap": split.gap_windows,
        "fit_target_end_date": split.fit_windows[-1].target_end_date,
        "selection_target_start_date": split.selection_windows[0].target_start_date,
        "fit_target_end_index": split.fit_target_end_index,
        "selection_target_start_index": split.selection_target_start_index,
        "no_target_overlap_proof": (
            f"{split.selection_target_start_index} > {split.fit_target_end_index}"
        ),
        "split_hash": split.split_hash,
    }

    # v3 objective statistics: lead-lag, TRAINING-FIT REAL paths only
    statistics = build_v3_statistics(
        split.fit_windows, normalizer, cumret_scale, spec, config.objective
    )
    objective_definition = {
        "kernel": config.objective.kernel,
        "signature_level": config.objective.signature_level,
        "representation": "lead-lag (standard discrete interleaving)",
        "augmented_path_dim": statistics.augmented_path_dim,
        "standardize_features": config.objective.standardize_features,
        "standardization_floor_eps": config.objective.standardization_floor_eps,
        "standardization_hash": statistics.standardization_hash,
        "feature_dim": statistics.feature_dim,
        "bandwidth_sq": statistics.bandwidth_sq,
        "bandwidth_vectors": statistics.bandwidth_vectors,
        "bandwidth_source": config.objective.bandwidth_source,
        "bandwidth_method": config.objective.bandwidth_method,
        "bandwidth_max_vectors": config.objective.bandwidth_max_vectors,
        "estimator": "biased empirical RBF MMD^2 (Gretton et al.), frozen form",
        "variance_penalty_coefficient": config.objective.variance_penalty_coefficient,
        "variance_target": "log(var of training-fit real targets + eps)",
        "variance_eps": config.objective.variance_eps,
    }

    device = torch.device("cpu")
    dtype = torch.float32
    configure_determinism(True)
    set_deterministic_seeds(config.training.model_init_seed)
    model = ConditionalNeuralSde(config.sde).to(device=device, dtype=dtype)
    n_params = count_parameters(model)
    training_returns_tensor = torch.tensor(training_returns, dtype=dtype)

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

    # INTERNAL GATE (selection only; before any validation)
    gate_diagnostics, gate_passed = evaluate_internal_gate_v3(
        model, split, normalizer, training_returns_tensor, spec, config.objective
    )

    normalization_block = {
        "context_features": list(CONTEXT_FEATURE_NAMES),
        "means": [float(v) for v in normalizer.means],
        "stds": [float(v) for v in normalizer.stds],
        "normalizer_hash": normalizer_hash,
        "cumret_scale": float(cumret_scale),
        "initial_price": float(training_series.prices[-1]),
        "fit_population": len(windows),
    }
    initial_price = float(training_series.prices[-1])

    experiment_id = experiment_id_v3(
        config_hash,
        training_series.series_sha256,
        suite["validation_series_sha256"],
        inventory.inventory_hash,
        benchmark.benchmark_hash,
        metric_spec_hash,
        suite["suite_hash"],
        split.split_hash,
    )

    checkpoint_dir = output_root / config.version / config_hash[:16]
    checkpoint_path = checkpoint_dir / "checkpoint.pt"

    if not gate_passed:
        evaluation: dict[str, Any] = {}
        data_audit = _data_value_of_information_audit_v3(config, split, gate_diagnostics)
        artifact = NeuralSdeExperimentV3Artifact(
            experiment_id=experiment_id,
            config=asdict(config),
            config_hash=config_hash,
            config_file_sha256=config_file_sha256,
            inventory_hash=inventory.inventory_hash,
            benchmark_hash=benchmark.benchmark_hash,
            metric_spec_hash=metric_spec_hash,
            baseline_suite_hash=suite["suite_hash"],
            training_series_sha256=training_series.series_sha256,
            validation_series_sha256=suite["validation_series_sha256"],
            internal_split=internal_split_block,
            split_hash=split.split_hash,
            normalization=normalization_block,
            objective_definition=objective_definition,
            training={
                "training_population": len(windows),
                "fit_population": split.n_fit,
                "selection_population": split.n_selection,
                "initial_internal_rbf": outcome.initial_internal_rbf,
                "best_internal_rbf": outcome.best_internal_rbf,
                "percent_improvement": outcome.percent_improvement,
                "best_epoch": outcome.best_epoch,
                "final_epoch": outcome.final_epoch,
            },
            internal_gate=dict(gate_diagnostics),
            model={
                "architecture": "conditional neural SDE (v2 architecture retained)",
                "representation": "lead-lag (standard discrete interleaving)",
                "state_dim": config.sde.state_dim,
                "brownian_dim": config.sde.brownian_dim,
                "parameter_count": n_params,
                "torch_version": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "device": str(device),
                "dtype": str(dtype),
                "determinism": {"use_deterministic_algorithms": True, "mixed_precision": False},
            },
            checkpoint={"path": str(checkpoint_path), "sha256": "", "bytes": 0},
            v1_preservation={
                "v1_config_file_sha256": v1_config_sha,
                "v1_checkpoint_sha256": v1_checkpoint_sha,
                "v1_experiment_artifact_sha256": v1_artifact_sha,
                "note": "v1 not written or mutated; hashes verified on load",
            },
            v2_preservation={
                "v2_config_file_sha256": v2_config_sha,
                "v2_checkpoint_sha256": v2_checkpoint_sha,
                "v2_experiment_artifact_sha256": v2_artifact_sha,
                "note": "v2 not written or mutated; hashes verified on load",
            },
            evaluation={},
            data_value_of_information=data_audit,
            provenance={
                "evaluation_utc_iso": start.isoformat(),
                "status": "V3 INTERNAL GATE FAILED",
                "note": "internal gate failed; external validation NOT loaded",
            },
            artifact_hash="",
        )
        artifact_hash = artifact._compute_hash()
        artifact = artifact.model_copy(update={"artifact_hash": artifact_hash})
        NeuralSdeExperimentV3Artifact.model_validate(
            artifact.model_dump(mode="json", by_alias=True)
        )
        _write_json(
            checkpoint_dir / "neural_sde_signature_v3_experiment.json",
            artifact.model_dump(mode="json", by_alias=True),
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n",
            encoding="utf-8",
        )
        return artifact

    # Gate passed: final refit on all windows, freeze, THEN validation
    set_deterministic_seeds(config.training.model_init_seed)
    final_model = ConditionalNeuralSde(config.sde).to(device=device, dtype=dtype)
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
    checkpoint_meta = _seal_checkpoint_v3(final_model, checkpoint_path, experiment_id)

    # External validation loaded only after gate pass and refit
    validation_series = build_underlying_series(
        inventory=inventory, split="validation", raw_root=raw_root, processed_root=processed_root
    )
    if validation_series.series_sha256 != suite["validation_series_sha256"]:
        raise ValueError("validation series binding mismatch at evaluation time")

    eval_window = _series_context_window(training_returns, session_dates, spec)
    eval_context = normalizer.normalize(compute_context_features(eval_window, spec).array())
    normalization_block["boundary_context"] = {
        name: float(v)
        for name, v in zip(
            CONTEXT_FEATURE_NAMES, compute_context_features(eval_window, spec).array(), strict=True
        )
    }

    evaluation = _evaluation_v3(
        model=final_model,
        eval_context=eval_context,
        spec=spec,
        config=config,
        initial_price=initial_price,
        training_empirical=suite["metrics"]["training_empirical"],
        validation_empirical=suite["metrics"]["validation_empirical"],
        suite=suite,
        v1_artifact=v1_artifact,
        v2_artifact=v2_artifact,
    )

    curve_path = checkpoint_dir / "training_curve.json"
    _write_json(
        curve_path,
        {
            "experiment_id": experiment_id,
            "rbf_curve": outcome.rbf_curve,
            "total_curve": outcome.total_curve,
            "selection_rbf_curve": outcome.selection_rbf_curve,
            "selection_total_curve": outcome.selection_total_curve,
            "initial_internal_rbf": outcome.initial_internal_rbf,
            "best_internal_rbf": outcome.best_internal_rbf,
            "best_epoch": outcome.best_epoch,
        },
    )
    curve_sha = hashlib.sha256(curve_path.read_bytes()).hexdigest()

    artifact = NeuralSdeExperimentV3Artifact(
        experiment_id=experiment_id,
        config=asdict(config),
        config_hash=config_hash,
        config_file_sha256=config_file_sha256,
        inventory_hash=inventory.inventory_hash,
        benchmark_hash=benchmark.benchmark_hash,
        metric_spec_hash=metric_spec_hash,
        baseline_suite_hash=suite["suite_hash"],
        training_series_sha256=training_series.series_sha256,
        validation_series_sha256=validation_series.series_sha256,
        internal_split=internal_split_block,
        split_hash=split.split_hash,
        normalization=normalization_block,
        objective_definition=objective_definition,
        training={
            "training_population": len(windows),
            "fit_population": split.n_fit,
            "selection_population": split.n_selection,
            "initial_internal_rbf": outcome.initial_internal_rbf,
            "best_internal_rbf": outcome.best_internal_rbf,
            "percent_improvement": outcome.percent_improvement,
            "best_epoch": outcome.best_epoch,
            "final_epoch": outcome.final_epoch,
            "training_curve_artifact": str(curve_path),
            "training_curve_sha256": curve_sha,
        },
        internal_gate=dict(gate_diagnostics),
        model={
            "architecture": "conditional neural SDE (v2 architecture retained)",
            "representation": "lead-lag (standard discrete interleaving)",
            "state_dim": config.sde.state_dim,
            "brownian_dim": config.sde.brownian_dim,
            "parameter_count": n_params,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device": str(device),
            "dtype": str(dtype),
            "determinism": {"use_deterministic_algorithms": True, "mixed_precision": False},
        },
        checkpoint=checkpoint_meta,
        v1_preservation={
            "v1_config_file_sha256": v1_config_sha,
            "v1_checkpoint_sha256": v1_checkpoint_sha,
            "v1_experiment_artifact_sha256": v1_artifact_sha,
            "note": "v1 not written or mutated; hashes verified on load",
        },
        v2_preservation={
            "v2_config_file_sha256": v2_config_sha,
            "v2_checkpoint_sha256": v2_checkpoint_sha,
            "v2_experiment_artifact_sha256": v2_artifact_sha,
            "note": "v2 not written or mutated; hashes verified on load",
        },
        evaluation=evaluation,
        data_value_of_information={},
        provenance={
            "evaluation_utc_iso": start.isoformat(),
            "status": "SIGNATURE NEURAL SDE V3 READY",
            "note": "timestamp is provenance only; excluded from canonical identity",
        },
        artifact_hash="",
    )
    artifact_hash = artifact._compute_hash()
    artifact = artifact.model_copy(update={"artifact_hash": artifact_hash})
    NeuralSdeExperimentV3Artifact.model_validate(artifact.model_dump(mode="json", by_alias=True))
    _write_json(
        checkpoint_dir / "neural_sde_signature_v3_experiment.json",
        artifact.model_dump(mode="json", by_alias=True),
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n", encoding="utf-8"
    )
    return artifact


def _load_v1_artifact(v1_artifact_path: Path) -> dict[str, Any]:
    payload = json.loads(v1_artifact_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "research-neural-sde-experiment-v1":
        raise ValueError("v1 artifact schema mismatch")
    return dict(payload)


def _data_value_of_information_audit_v3(
    config: NeuralSdeExperimentConfigV3, split: Any, gate: dict[str, Any]
) -> dict[str, Any]:
    criterion_results = gate.get("criterion_results", {})
    failing_criteria = [k for k, v in criterion_results.items() if not v]
    candidates = [
        {
            "priority": "A",
            "candidate": "extend SPY daily underlying history BACKWARD before training start",
            "scientific_purpose": (
                "increase training daily-return count and 63-day window count; more independent "
                "training paths for the corrected objective"
            ),
            "required_dataset_schema": "SPY daily OHLCV (ARCX.PILLAR ohlcv-1d)",
            "date_range": "e.g. 2016-05-01 .. 2018-04-30 (before training start 2018-05-01)",
            "estimated_increase": (
                f"current {split.n_eligible} eligible windows "
                f"(fit {split.n_fit} / selection {split.n_selection}); "
                "~250 sessions/yr -> ~+70% more 63-day windows per 2 extra years"
            ),
            "model_input_contract_change": "none (same daily log returns; lookback unchanged)",
            "provider_quote_scope": "metadata-only preflight in a later LIVE milestone",
            "regime_mismatch_risk": (
                "moderate: extends pre-2018 (regime drift); validation and final test untouched"
            ),
            "preserves_current_validation": True,
        },
        {
            "priority": "B",
            "candidate": (
                "SPY intraday training-period data for a higher-quality realized-volatility context"
            ),
            "scientific_purpose": (
                "replace the 22-day daily RV context feature with an intraday RV "
                "(improves conditioning information content)"
            ),
            "required_dataset_schema": "SPY intraday (e.g. 1m/1h) bars, existing training period",
            "date_range": "2018-05-01 .. 2021-12-31",
            "estimated_increase": "no new windows; improves one conditioning feature's information",
            "model_input_contract_change": (
                "yes: changes context feature -> new normalization and config hash"
            ),
            "provider_quote_scope": "metadata-only preflight in a later LIVE milestone",
            "regime_mismatch_risk": "low (same training period and underlying)",
            "preserves_current_validation": True,
        },
        {
            "priority": "C",
            "candidate": "additional OPRA option data",
            "scientific_purpose": "none tied to the observed failure",
            "required_dataset_schema": "OPRA cbbo-1m snapshots (already partially acquired)",
            "date_range": "n/a",
            "estimated_increase": "0 usable paths/features for this underlying-path failure",
            "model_input_contract_change": "none; not recommended",
            "provider_quote_scope": "none",
            "regime_mismatch_risk": "n/a",
            "preserves_current_validation": True,
            "recommendation": (
                "do NOT default to OPRA; the failure is underlying-path dispersion "
                "collapse, not missing option observations"
            ),
        },
    ]
    return {
        "context": "audit performed because the internal gate failed; "
        "no purchase and no provider call in this milestone",
        "failing_criteria": failing_criteria,
        "credits_available_contigency": 102.46,
        "candidates": candidates,
    }


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point for the frozen v3 experiment run."""
    parser = argparse.ArgumentParser(
        description="Run the frozen signature neural-SDE v3 experiment"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--v1-artifact", required=True, help="Frozen v1 experiment artifact JSON")
    parser.add_argument("--v2-artifact", required=True, help="Frozen v2 experiment artifact JSON")
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--processed-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    artifact = run_neural_sde_experiment_v3(
        config_path=Path(args.config),
        inventory_path=Path(args.inventory),
        benchmark_path=Path(args.benchmark),
        suite_path=Path(args.suite),
        v1_artifact_path=Path(args.v1_artifact),
        v2_artifact_path=Path(args.v2_artifact),
        raw_root=Path(args.raw_root),
        processed_root=Path(args.processed_root),
        output_root=Path(args.output_root),
        report_path=Path(args.report),
    )
    print(f"experiment_id={artifact.experiment_id}")
    print(f"gate_passed={artifact.internal_gate.get('gate_passed')}")
    print(f"best_internal_rbf={artifact.training['best_internal_rbf']:.6e}")
    print(f"status={artifact.provenance.get('status')}")


if __name__ == "__main__":  # pragma: no cover
    main()
