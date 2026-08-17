"""Signature neural-SDE v1 experiment orchestration.

Builds training windows from frozen TRAINING returns only, fits the context
normalizer and cumulative-return scale on the same training data, runs the
internal fit/selection training, refits on all eligible training windows for
the frozen best epoch count, freezes the checkpoint with a deterministic
provenance manifest, and ONLY THEN evaluates on the frozen external
validation split with the unchanged ``research-metric-spec-v1`` scorecard.

External validation is never an input to any training decision; the
evaluation timestamp is recorded as provenance only and is excluded from the
canonical experiment identity.
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
from neuralmarket.data.research.baseline_suite import (
    EVALUATED_COMPARATORS,
    SimulatorBaselineSuiteArtifact,
)
from neuralmarket.data.research.benchmark import (
    EmpiricalBenchmarkArtifact,
    _family_errors,
    _scorecard_payload,
)
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.data.research.sde_windows import (
    CONTEXT_FEATURE_NAMES,
    SdeWindow,
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
from neuralmarket.research.neural_sde_trainer import (
    TrainingConfig,
    refit_final,
    train_internal,
)

EXPERIMENT_SCHEMA_VERSION: Literal["research-neural-sde-experiment-v1"] = (
    "research-neural-sde-experiment-v1"
)

_EXCLUDED_FROM_HASH = {"artifact_hash", "provenance"}


@dataclass(frozen=True)
class NeuralSdeExperimentConfig:
    """Effective frozen experiment configuration assembled from the YAML."""

    version: str = "signature-neural-sde-v1"
    sde: SdeConfig = field(default_factory=SdeConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    windows: WindowSpec = field(default_factory=WindowSpec)
    n_eval_paths: int = 1024
    eval_seed: int = 4244
    eval_initial_price_convention: str = "final training-session close"

    def config_hash(self) -> str:
        """Deterministic identity of the effective config (no wall clock)."""
        payload = {
            "version": self.version,
            "sde": asdict(self.sde),
            "training": asdict(self.training),
            "windows": asdict(self.windows),
            "n_eval_paths": self.n_eval_paths,
            "eval_seed": self.eval_seed,
            "eval_initial_price_convention": self.eval_initial_price_convention,
        }
        return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()


class NeuralSdeExperimentArtifact(BaseModel):
    """Deterministic sealed experiment artifact (no wall-clock identity)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research-neural-sde-experiment-v1"] = EXPERIMENT_SCHEMA_VERSION
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
    training: dict[str, Any]
    model: dict[str, Any]
    checkpoint: dict[str, Any]
    evaluation: dict[str, Any]
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
        for key in _EXCLUDED_FROM_HASH:
            payload.pop(key, None)
        # Output paths are storage locations, not identity; the canonical hash
        # must not depend on where the artifact happens to be written.
        payload.get("checkpoint", {}).pop("path", None)
        payload.get("training", {}).pop("training_curve_artifact", None)
        return hashlib.sha256(canonical_dumps(payload).encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def _validate_hash(self) -> NeuralSdeExperimentArtifact:
        if self.artifact_hash and self.artifact_hash != self._compute_hash():
            raise ValueError("neural-SDE experiment artifact hash mismatch")
        return self


def experiment_id_for(
    config_hash: str,
    training_series_sha256: str,
    validation_series_sha256: str,
    inventory_hash: str,
    benchmark_hash: str,
    metric_spec_hash: str,
    baseline_suite_hash: str,
    split_hash: str,
) -> str:
    """Deterministic canonical experiment identity (no wall-clock dependence)."""
    identity = canonical_dumps(
        {
            "schema": EXPERIMENT_SCHEMA_VERSION,
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


def load_experiment_config(path: Path) -> NeuralSdeExperimentConfig:
    """Load and validate the tracked YAML experiment configuration.

    Args:
        path: Path to the tracked ``neural_sde_signature_v1.yaml``.

    Returns:
        The effective frozen configuration.

    Raises:
        ValueError: If the YAML is malformed or contains unknown keys.
    """
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("experiment config must be a mapping")
    known = {"version", "sde", "training", "windows", "n_eval_paths", "eval_seed"}
    unknown = set(payload) - known
    if unknown:
        raise ValueError(f"unknown experiment config keys: {sorted(unknown)}")

    sde_kwargs = payload.get("sde") or {}
    training_kwargs = payload.get("training") or {}
    window_kwargs = payload.get("windows") or {}
    return NeuralSdeExperimentConfig(
        version=str(payload.get("version", "signature-neural-sde-v1")),
        sde=SdeConfig(**sde_kwargs),
        training=TrainingConfig(**training_kwargs),
        windows=WindowSpec(**window_kwargs),
        n_eval_paths=int(payload.get("n_eval_paths", 1024)),
        eval_seed=int(payload.get("eval_seed", 4244)),
    )


def _series_context_window(
    returns: np.ndarray, session_dates: tuple[str, ...], spec: WindowSpec
) -> SdeWindow:
    """The last available strictly-past context before the series boundary."""
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


def _seal_checkpoint(
    model: ConditionalNeuralSde, checkpoint_path: Path, experiment_id: str
) -> dict[str, Any]:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "research-neural-sde-checkpoint-v1",
        "experiment_id": experiment_id,
        "model_state": {k: v.cpu() for k, v in model.state_dict().items()},
        "sde_config": asdict(model.config),
    }
    torch.save(payload, checkpoint_path)
    sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    return {"path": str(checkpoint_path), "sha256": sha, "bytes": checkpoint_path.stat().st_size}


def _evaluation_block(
    *,
    model: ConditionalNeuralSde,
    eval_context: np.ndarray,
    normalization: dict[str, Any],
    spec: WindowSpec,
    config: NeuralSdeExperimentConfig,
    initial_price: float,
    training_empirical: dict[str, Any],
    validation_empirical: dict[str, Any],
    suite: SimulatorBaselineSuiteArtifact,
) -> dict[str, Any]:
    """Generate 1024x63 evaluation paths and score them against both splits.

    Conditioning uses only the final available TRAINING context (forward
    looking at the training/validation boundary) as the primary frozen
    baseline-comparison run.  A context-marginalized training diagnostic is
    additionally reported as secondary evidence only.
    """
    n_paths = config.n_eval_paths
    ctx_tensor = torch.tensor([[float(v) for v in eval_context]] * n_paths, dtype=torch.float32)
    generated = simulate(model, ctx_tensor, seed=config.eval_seed)
    increments = generated.detach().cpu().numpy()
    if increments.shape != (n_paths, spec.horizon):
        raise RuntimeError(f"evaluation paths have wrong shape: {increments.shape}")

    prices = reconstruct_prices(torch.tensor(increments, dtype=torch.float32), float(initial_price))
    if not np.isfinite(increments).all():
        raise RuntimeError("evaluation generated non-finite increments")
    if not (prices > 0).all() or not torch.isfinite(prices).all():
        raise RuntimeError("evaluation generated non-positive prices")

    spec_metric = MetricSpecification()
    neural_payload = _scorecard_payload(
        compute_scorecard(increments.ravel(), spec_metric.scorecard)
    )
    neural_families_train = _family_errors(neural_payload, training_empirical)
    neural_families_valid = _family_errors(neural_payload, validation_empirical)

    evaluation: dict[str, Any] = {
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
                "final available training context at the training/validation "
                "boundary; no validation observation conditions the headline run"
            ),
        },
        "neural_metrics": neural_payload,
        "discrepancies": {
            "training": neural_families_train,
            "validation": neural_families_valid,
        },
        "comparison": _comparison_block(suite, neural_payload),
        "improvement_check": _improvement_check(neural_families_train, neural_families_valid),
    }
    return evaluation


def _comparison_block(
    suite: SimulatorBaselineSuiteArtifact, neural_payload: dict[str, Any]
) -> dict[str, Any]:
    """Per-family nearest-baseline and neural rank against the frozen suite."""
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
        empirical = suite.metrics[empirical_key]
        split_block: dict[str, Any] = {}
        for family in scalar_families:
            errors = {
                name: abs(float(suite.discrepancies[split][name][family]["relative_error"]))
                for name in EVALUATED_COMPARATORS
            }
            emp_value = float(empirical[family])
            model_value = float(neural_payload[family])
            neural_error = (
                abs(model_value - emp_value) / abs(emp_value)
                if abs(emp_value) > 1e-12
                else abs(model_value - emp_value)
            )
            baseline_ranked = sorted(errors, key=errors.__getitem__)
            all_errors = dict(errors)
            all_errors["neural_sde_signature"] = neural_error
            all_ranked = sorted(all_errors, key=all_errors.__getitem__)
            split_block[family] = {
                "nearest_baseline": baseline_ranked[0],
                "neural_rank": all_ranked.index("neural_sde_signature") + 1,
                "errors": {k: float(v) for k, v in all_errors.items()},
            }
        for family in dict_families:
            dict_errors: dict[str, float] = {}
            for name in EVALUATED_COMPARATORS:
                value = suite.discrepancies[split][name][family]["mean_abs_relative_error"]
                dict_errors[name] = float("inf") if value is None else abs(float(value))
            neural_value = _mean_abs_rel_error(neural_payload[family], empirical[family])
            baseline_ranked = sorted(dict_errors, key=dict_errors.__getitem__)
            all_errors = dict(dict_errors)
            all_errors["neural_sde_signature"] = neural_value
            all_ranked = sorted(all_errors, key=all_errors.__getitem__)
            split_block[family] = {
                "nearest_baseline": baseline_ranked[0],
                "neural_rank": all_ranked.index("neural_sde_signature") + 1,
                "errors": {
                    k: (None if v == float("inf") else float(v)) for k, v in all_errors.items()
                },
            }
        comparison[split] = split_block
    return comparison


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


def _improvement_check(
    neural_train: dict[str, Any], neural_valid: dict[str, Any]
) -> dict[str, Any]:
    """Honest neural-vs-classical improvement summary WITHOUT collapsing families."""
    checks: dict[str, Any] = {}
    for split, families in (("training", neural_train), ("validation", neural_valid)):
        split_checks: dict[str, Any] = {}
        for family in (
            "excess_kurtosis",
            "return_acf",
            "abs_return_acf",
            "sq_return_acf",
            "leverage_correlations",
        ):
            if family not in families:
                continue
            if family == "excess_kurtosis":
                value = families[family]["relative_error"]
            else:
                value = families[family]["mean_abs_relative_error"]
            split_checks[family] = None if value is None else float(value)
        checks[split] = split_checks
    return checks


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    """Write a canonical JSON artifact with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(payload) + "\n", encoding="utf-8")


def run_neural_sde_experiment(
    *,
    config_path: Path,
    inventory_path: Path,
    benchmark_path: Path,
    suite_path: Path,
    raw_root: Path,
    processed_root: Path,
    output_root: Path,
    report_path: Path,
) -> NeuralSdeExperimentArtifact:
    """Run the full frozen experiment: train, freeze, evaluate, seal.

    Args:
        config_path: Tracked experiment YAML.
        inventory_path: Frozen research development inventory JSON.
        benchmark_path: Accepted empirical benchmark JSON.
        suite_path: Frozen simulator baseline suite JSON.
        raw_root: Root of the checksum-verified raw acquisition tree.
        processed_root: Root of the validated normalized tree.
        output_root: gitignored artifact root for checkpoints/results.
        report_path: gitignored report JSON path for the execution record.

    Returns:
        The sealed experiment artifact.

    Raises:
        RuntimeError: If training does not learn or any non-finite value appears.
        ValueError: If any frozen binding is violated.
    """
    start = datetime.now(UTC)
    config = load_experiment_config(config_path)
    config_file_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    config_hash = config.config_hash()

    inventory = ResearchInventory.model_validate(
        json.loads(inventory_path.read_text(encoding="utf-8"))
    )
    benchmark = EmpiricalBenchmarkArtifact.model_validate(
        json.loads(benchmark_path.read_text(encoding="utf-8"))
    )
    suite = SimulatorBaselineSuiteArtifact.model_validate(
        json.loads(suite_path.read_text(encoding="utf-8"))
    )

    if (
        inventory.inventory_hash
        != "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"
    ):
        raise ValueError("frozen research inventory hash does not match the milestone binding")
    if (
        benchmark.benchmark_hash
        != "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"
    ):
        raise ValueError("frozen empirical benchmark hash does not match the milestone binding")
    if suite.suite_hash != "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099":
        raise ValueError(
            "frozen simulator baseline suite hash does not match the milestone binding"
        )
    metric_spec_hash = MetricSpecification().spec_hash()
    if metric_spec_hash != "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3":
        raise ValueError("frozen research-metric-spec-v1 hash does not match the milestone binding")
    if metric_spec_hash != benchmark.metric_spec_hash or metric_spec_hash != suite.metric_spec_hash:
        raise ValueError("metric-spec binding mismatch across frozen artifacts")
    if suite.training_series_sha256 != benchmark.underlying["training"].series_sha256:
        raise ValueError("suite/benchmark training-series binding mismatch")
    if suite.validation_series_sha256 != benchmark.underlying["validation"].series_sha256:
        raise ValueError("suite/benchmark validation-series binding mismatch")

    training_series = build_underlying_series(
        inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root
    )
    validation_series = build_underlying_series(
        inventory=inventory, split="validation", raw_root=raw_root, processed_root=processed_root
    )
    if training_series.series_sha256 != benchmark.underlying["training"].series_sha256:
        raise ValueError("training series does not match the accepted benchmark binding")
    if validation_series.series_sha256 != benchmark.underlying["validation"].series_sha256:
        raise ValueError("validation series does not match the accepted benchmark binding")
    if training_series.series_sha256 != suite.training_series_sha256:
        raise ValueError("training series does not match the baseline suite binding")
    if validation_series.series_sha256 != suite.validation_series_sha256:
        raise ValueError("validation series does not match the baseline suite binding")

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

    device = torch.device("cpu")
    dtype = torch.float32
    configure_determinism(True)
    set_deterministic_seeds(config.training.model_init_seed)

    model = ConditionalNeuralSde(config.sde).to(device=device, dtype=dtype)
    n_params = count_parameters(model)

    training_returns_tensor = torch.tensor(training_returns, dtype=dtype)
    outcome = train_internal(
        model, config.training, split, normalizer, training_returns_tensor, spec
    )

    # Final refit: deterministic reinitialization, ALL eligible windows,
    # exactly the frozen best epoch count.
    set_deterministic_seeds(config.training.model_init_seed)
    final_model = ConditionalNeuralSde(config.sde).to(device=device, dtype=dtype)
    refit_final(
        final_model,
        config.training,
        windows,
        normalizer,
        training_returns_tensor,
        outcome.best_epoch,
        spec,
    )

    initial_price = float(training_series.prices[-1])
    if initial_price != float(benchmark.simulations["initial_price"]):
        raise ValueError("initial price does not match the accepted benchmark simulation contract")

    experiment_id = experiment_id_for(
        config_hash,
        training_series.series_sha256,
        validation_series.series_sha256,
        inventory.inventory_hash,
        benchmark.benchmark_hash,
        metric_spec_hash,
        suite.suite_hash,
        split.split_hash,
    )

    # Freeze the checkpoint BEFORE any external-validation observation.
    checkpoint_dir = output_root / config.version / config_hash[:16]
    checkpoint_path = checkpoint_dir / "checkpoint.pt"
    checkpoint_meta = _seal_checkpoint(final_model, checkpoint_path, experiment_id)

    normalization_block = {
        "context_features": list(CONTEXT_FEATURE_NAMES),
        "means": [float(v) for v in normalizer.means],
        "stds": [float(v) for v in normalizer.stds],
        "normalizer_hash": normalizer_hash,
        "cumret_scale": float(cumret_scale),
        "cumret_scale_convention": (
            "training daily-return std * sqrt(horizon); fitted on training returns only"
        ),
        "initial_price": float(initial_price),
        "fit_population": len(windows),
    }

    # Conditioning context: the final available TRAINING context.
    eval_window = _series_context_window(training_returns, session_dates, spec)
    eval_context_raw = compute_context_features(eval_window, spec).array()
    eval_context = normalizer.normalize(eval_context_raw)
    normalization_block["boundary_context"] = {
        name: float(v) for name, v in zip(CONTEXT_FEATURE_NAMES, eval_context_raw, strict=True)
    }

    evaluation = _evaluation_block(
        model=final_model,
        eval_context=eval_context,
        normalization=normalization_block,
        spec=spec,
        config=config,
        initial_price=initial_price,
        training_empirical=suite.metrics["training_empirical"],
        validation_empirical=suite.metrics["validation_empirical"],
        suite=suite,
    )

    curve_path = checkpoint_dir / "training_curve.json"
    curve_payload = {
        "experiment_id": experiment_id,
        "training_loss": outcome.loss_curve,
        "internal_selection_loss": outcome.selection_curve,
        "initial_internal_loss": outcome.initial_internal_loss,
        "best_internal_loss": outcome.best_internal_loss,
        "best_epoch": outcome.best_epoch,
    }
    write_json_artifact(curve_path, curve_payload)
    curve_sha = hashlib.sha256(curve_path.read_bytes()).hexdigest()

    internal_split_block = {
        "n_eligible": split.n_eligible,
        "n_fit": split.n_fit,
        "n_selection": split.n_selection,
        "n_gap": split.gap_windows,
        "fit_window_ids": [w.window_id for w in split.fit_windows],
        "selection_window_ids": [w.window_id for w in split.selection_windows],
        "fit_target_start_date": split.fit_windows[0].target_start_date,
        "fit_target_end_date": split.fit_windows[-1].target_end_date,
        "selection_target_start_date": split.selection_windows[0].target_start_date,
        "selection_target_end_date": split.selection_windows[-1].target_end_date,
        "fit_target_end_index": split.fit_target_end_index,
        "selection_target_start_index": split.selection_target_start_index,
        "no_target_overlap_proof": (
            f"{split.selection_target_start_index} > {split.fit_target_end_index}"
        ),
        "split_hash": split.split_hash,
    }

    artifact = NeuralSdeExperimentArtifact(
        experiment_id=experiment_id,
        config=asdict(config),
        config_hash=config_hash,
        config_file_sha256=config_file_sha256,
        inventory_hash=inventory.inventory_hash,
        benchmark_hash=benchmark.benchmark_hash,
        metric_spec_hash=metric_spec_hash,
        baseline_suite_hash=suite.suite_hash,
        training_series_sha256=training_series.series_sha256,
        validation_series_sha256=validation_series.series_sha256,
        internal_split=internal_split_block,
        split_hash=split.split_hash,
        normalization=normalization_block,
        training={
            "training_population": len(windows),
            "fit_population": split.n_fit,
            "selection_population": split.n_selection,
            "initial_internal_loss": outcome.initial_internal_loss,
            "best_internal_loss": outcome.best_internal_loss,
            "percent_improvement": outcome.percent_improvement,
            "best_epoch": outcome.best_epoch,
            "final_epoch": outcome.final_epoch,
            "training_curve_artifact": str(curve_path),
            "training_curve_sha256": curve_sha,
        },
        model={
            "architecture": "conditional neural SDE (fallback design)",
            "state_dim": config.sde.state_dim,
            "brownian_dim": config.sde.brownian_dim,
            "context_fields": list(CONTEXT_FEATURE_NAMES),
            "network": {
                "hidden_units": config.sde.hidden_units,
                "hidden_layers": config.sde.hidden_layers,
                "activation": config.sde.activation,
                "diffusion_transform": f"softplus(raw) + {config.sde.diffusion_epsilon}",
            },
            "integrator": "Euler-Maruyama",
            "dt": config.sde.dt,
            "signature_level": config.sde.signature_level,
            "signature_objective": (
                "truncated-signature MMD (finite-level linear signature-kernel approximation)"
            ),
            "parameter_count": n_params,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device": str(device),
            "dtype": str(dtype),
            "determinism": {
                "use_deterministic_algorithms": True,
                "cudnn_benchmark": False,
                "mixed_precision": False,
            },
        },
        checkpoint={
            "path": str(checkpoint_path),
            "sha256": checkpoint_meta["sha256"],
            "bytes": checkpoint_meta["bytes"],
        },
        evaluation=evaluation,
        provenance={
            "evaluation_utc_iso": start.isoformat(),
            "evaluation_note": "timestamp is provenance only; excluded from canonical identity",
            "known_limitations": [
                "The accepted empirical_benchmark_v1.json embeds a historical "
                "inventory_hash differing from the current frozen research "
                "inventory; recorded, not repaired.",
                "Training/evaluation series hashes are bound to the benchmark "
                "and baseline-suite artifacts independently.",
                "Network baseline comparisons reuse the frozen suite values; "
                "no baseline is recalibrated.",
                "Truncated signature (level 3) is a finite-level signature-kernel "
                "approximation, not the exact infinite-level signature kernel.",
            ],
        },
        artifact_hash="",
    )
    artifact_hash = artifact._compute_hash()
    artifact = artifact.model_copy(update={"artifact_hash": artifact_hash})
    NeuralSdeExperimentArtifact.model_validate(artifact.model_dump(mode="json", by_alias=True))

    artifact_dir = checkpoint_dir
    artifact_path_out = artifact_dir / "neural_sde_signature_v1_experiment.json"
    write_json_artifact(artifact_path_out, artifact.model_dump(mode="json", by_alias=True))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n",
        encoding="utf-8",
    )
    return artifact


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point for the frozen experiment run."""
    parser = argparse.ArgumentParser(description="Run the frozen signature neural-SDE experiment")
    parser.add_argument("--config", required=True, help="Tracked experiment YAML path")
    parser.add_argument("--inventory", required=True, help="Frozen inventory JSON path")
    parser.add_argument("--benchmark", required=True, help="Accepted empirical benchmark JSON path")
    parser.add_argument("--suite", required=True, help="Frozen baseline suite JSON path")
    parser.add_argument("--raw-root", required=True, help="Root of the raw acquisition tree")
    parser.add_argument("--processed-root", required=True, help="Root of the normalized tree")
    parser.add_argument("--output-root", required=True, help="Gitignored artifact output root")
    parser.add_argument("--report", required=True, help="Gitignored report JSON path")
    args = parser.parse_args(argv)
    artifact = run_neural_sde_experiment(
        config_path=Path(args.config),
        inventory_path=Path(args.inventory),
        benchmark_path=Path(args.benchmark),
        suite_path=Path(args.suite),
        raw_root=Path(args.raw_root),
        processed_root=Path(args.processed_root),
        output_root=Path(args.output_root),
        report_path=Path(args.report),
    )
    print(f"experiment_id={artifact.experiment_id}")
    print(f"best_internal_loss={artifact.training['best_internal_loss']:.6e}")
    print(f"checkpoint_sha256={artifact.checkpoint['sha256']}")


if __name__ == "__main__":  # pragma: no cover
    main()
