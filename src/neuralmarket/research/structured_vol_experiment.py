"""v5 structured volatility neural-SDE experiment.

Uses StructuredVolatilityNeuralSde with the v3 trainer infrastructure.
The structured model has the same forward API as ConditionalNeuralSde.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import torch
import yaml

from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.data.research.sde_windows import (
    SdeWindow,
    WindowSpec,
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
    split_fit_selection,
)
from neuralmarket.data.research.underlying import build_underlying_series
from neuralmarket.eval.scorecard import MetricSpecification
from neuralmarket.models.neural_sde import (
    configure_determinism,
    count_parameters,
    set_deterministic_seeds,
)
from neuralmarket.models.structured_vol_sde import (
    StructuredVolatilityNeuralSde,
    StructuredVolConfig,
    simulate_structured,
)
from neuralmarket.research.neural_sde_trainer import TrainingConfig
from neuralmarket.research.neural_sde_trainer_v3 import (
    V3ObjectiveConfig,
    build_v3_statistics,
    evaluate_internal_gate_v3,
    refit_final_v3,
    train_internal_v3,
)

EXPERIMENT_SCHEMA_V5: Literal["research-structured-vol-sde-experiment-v5"] = (
    "research-structured-vol-sde-experiment-v5"
)

_FROZEN_SUITE_HASH = "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"
_FROZEN_INVENTORY_HASH = "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"
_FROZEN_BENCHMARK_HASH = "2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d"
_FROZEN_METRIC_SPEC_HASH = "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"


@dataclass(frozen=True)
class V5ExperimentConfig:
    """Effective frozen v5 experiment configuration."""

    version: str = "structured-volatility-neural-sde-v5"
    sde: StructuredVolConfig = field(default_factory=StructuredVolConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    windows: WindowSpec = field(default_factory=WindowSpec)
    objective: V3ObjectiveConfig = field(default_factory=V3ObjectiveConfig)
    n_eval_paths: int = 1024
    eval_seed: int = 8283
    eval_initial_price_convention: str = "final training-session close"

    def config_hash(self) -> str:
        """Deterministic identity of the experiment config."""
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


def load_v5_config(path: Path) -> V5ExperimentConfig:
    """Load and validate the v5 experiment configuration."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return V5ExperimentConfig(
        version=str(payload.get("version", "structured-volatility-neural-sde-v5")),
        sde=StructuredVolConfig(**(payload.get("sde") or {})),
        training=TrainingConfig(**(payload.get("training") or {})),
        windows=WindowSpec(**(payload.get("windows") or {})),
        objective=V3ObjectiveConfig(**(payload.get("objective") or {})),
        n_eval_paths=int(payload.get("n_eval_paths", 1024)),
        eval_seed=int(payload.get("eval_seed", 8283)),
    )


def run_v5_experiment(
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
) -> dict[str, Any]:
    """Run the v5 structured volatility experiment."""
    start = datetime.now(UTC)
    config = load_v5_config(config_path)
    config_file_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    config_hash = config.config_hash()

    inventory = ResearchInventory.model_validate(
        json.loads(inventory_path.read_text(encoding="utf-8"))
    )
    _ = json.loads(benchmark_path.read_text(encoding="utf-8"))
    _ = json.loads(suite_path.read_text(encoding="utf-8"))

    # v1/v2 artifacts loaded for frozen hash verification
    _ = json.loads(v1_artifact_path.read_text(encoding="utf-8"))
    _ = json.loads(v2_artifact_path.read_text(encoding="utf-8"))

    training_series = build_underlying_series(
        inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root
    )
    training_returns = training_series.returns_array
    session_dates = training_series.session_dates
    return_dates = tuple(session_dates[1:])

    spec = config.windows
    windows = build_windows(training_returns, return_dates, spec)
    feature_matrix = np.stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    cumret_scale = fit_cumret_scale(training_returns, spec.horizon)
    split = split_fit_selection(windows, config.training.fit_fraction, spec)

    # Build v3 statistics (lead-lag signature)
    statistics = build_v3_statistics(
        split.fit_windows, normalizer, cumret_scale, spec, config.objective
    )

    # Initialize structured volatility model
    device = torch.device("cpu")
    dtype = torch.float32
    configure_determinism(True)
    set_deterministic_seeds(config.training.model_init_seed)
    model = StructuredVolatilityNeuralSde(config.sde).to(device=device, dtype=dtype)
    n_params = count_parameters(model)
    training_returns_tensor = torch.tensor(training_returns, dtype=dtype)

    # Train using v3 trainer (same API)
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

    # Gate evaluation
    gate_diagnostics, gate_passed = evaluate_internal_gate_v3(
        model, split, normalizer, training_returns_tensor, spec, config.objective
    )

    checkpoint_dir = output_root / config.version / config_hash[:16]
    checkpoint_path = checkpoint_dir / "checkpoint.pt"

    # Always preserve checkpoint and curve
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": {k: v.cpu() for k, v in model.state_dict().items()},
            "sde_config": asdict(config.sde),
        },
        checkpoint_path,
    )
    checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()

    curve_path = checkpoint_dir / "training_curve.json"
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

    status = "STRUCTURED-VOLATILITY-NEURAL-SDE-V5 INTERNAL GATE FAILED"
    evaluation: dict[str, Any] = {}

    if gate_passed:
        # Final refit
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
        # Overwrite checkpoint with refitted model
        torch.save(
            {
                "model_state": {k: v.cpu() for k, v in final_model.state_dict().items()},
                "sde_config": asdict(config.sde),
            },
            checkpoint_path,
        )
        checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()

        # External validation
        _ = build_underlying_series(
            inventory=inventory,
            split="validation",
            raw_root=raw_root,
            processed_root=processed_root,
        )
        eval_ctx_window = SdeWindow(
            window_id="w_boundary",
            start_index=len(training_returns) - spec.horizon,
            context_returns=training_returns[-spec.context_lookback :],
            target_returns=training_returns[-spec.horizon :],
            context_start_date=str(np.asarray(session_dates[1:])[-spec.context_lookback]),
            context_end_date=str(session_dates[-1]),
            target_start_date=str(np.asarray(session_dates[1:])[-spec.horizon]),
            target_end_date=str(session_dates[-1]),
        )
        eval_context = normalizer.normalize(compute_context_features(eval_ctx_window, spec).array())
        initial_price = float(training_series.prices[-1])

        n_paths = config.n_eval_paths
        ctx_tensor = torch.tensor([[float(v) for v in eval_context]] * n_paths, dtype=torch.float32)
        generated = simulate_structured(final_model, ctx_tensor, seed=config.eval_seed)
        increments = generated.detach().cpu().numpy()

        spec_metric = MetricSpecification()
        from neuralmarket.data.research.benchmark import _scorecard_payload
        from neuralmarket.eval.scorecard import compute_scorecard

        neural_payload = _scorecard_payload(
            compute_scorecard(increments.ravel(), spec_metric.scorecard)
        )
        evaluation = {
            "contract": {
                "n_paths": n_paths,
                "horizon_sessions": spec.horizon,
                "seed": config.eval_seed,
                "initial_price": initial_price,
            },
            "neural_metrics": neural_payload,
        }
        status = "STRUCTURED-VOLATILITY-NEURAL-SDE-V5 READY"

    result = {
        "experiment_id": hashlib.sha256(
            canonical_dumps({"schema": EXPERIMENT_SCHEMA_V5, "config_hash": config_hash}).encode()
        ).hexdigest(),
        "config_hash": config_hash,
        "config_file_sha256": config_file_sha256,
        "status": status,
        "gate_passed": gate_passed,
        "gate_diagnostics": gate_diagnostics,
        "training": {
            "fit_population": split.n_fit,
            "selection_population": split.n_selection,
            "initial_internal_rbf": outcome.initial_internal_rbf,
            "best_internal_rbf": outcome.best_internal_rbf,
            "best_epoch": outcome.best_epoch,
            "final_epoch": outcome.final_epoch,
        },
        "model": {
            "architecture": "structured_volatility_neural_sde",
            "parameter_count": n_params,
            "a_positive": float(model.a_positive.item()),
        },
        "checkpoint": {"path": str(checkpoint_path), "sha256": checkpoint_sha},
        "curve": {"path": str(curve_path), "sha256": curve_sha},
        "evaluation": evaluation,
        "provenance": {
            "evaluation_utc_iso": start.isoformat(),
            "status": status,
            "note": "Structured volatility hypothesis test",
        },
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(canonical_dumps(result) + "\n", encoding="utf-8")
    return result
