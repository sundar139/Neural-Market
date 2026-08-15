"""Deterministic empirical benchmark: empirical series, baselines, and scoring.

Builds the frozen research benchmark artifact: SPY training/validation
empirical series, GBM and Heston baselines calibrated on TRAINING data only,
seeded simulations, and per-metric discrepancies against both splits under
the frozen metric specification. Validation is evaluated only after
calibration is frozen; sealed final-test data never enters.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

from neuralmarket.baselines.gbm import calibrate_gbm, sample_gbm
from neuralmarket.baselines.heston import (
    calibrate_heston,
    sample_heston,
)
from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.data.research.underlying import (
    build_underlying_series,
)
from neuralmarket.eval.scorecard import (
    MetricSpecification,
    ScorecardResult,
    compute_scorecard,
)

BENCHMARK_SCHEMA_VERSION: Literal["research-empirical-benchmark-v1"] = (
    "research-empirical-benchmark-v1"
)


def _scorecard_payload(result: ScorecardResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["config"] = asdict(result.config)
    return payload


def _relative_error(model: float, empirical: float) -> float:
    if abs(empirical) > 1e-12:
        return (model - empirical) / empirical
    return model - empirical


def _family_errors(model: dict[str, Any], empirical: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-metric relative errors plus a documented mean-|error| per family."""
    families: dict[str, dict[str, Any]] = {}
    scalar_keys = ["mean", "variance", "skewness", "excess_kurtosis"]
    for name in scalar_keys:
        families[name] = {
            "model": float(model[name]),
            "empirical": float(empirical[name]),
            "relative_error": _relative_error(float(model[name]), float(empirical[name])),
        }
    for family in ("return_acf", "abs_return_acf", "sq_return_acf", "leverage_correlations"):
        empirical_family = {str(key): value for key, value in empirical[family].items()}
        errors = {
            str(lag): _relative_error(float(model[family][lag]), float(empirical_family[str(lag)]))
            for lag in model[family]
            if str(lag) in empirical_family
        }
        families[family] = {
            "model": {str(key): value for key, value in model[family].items()},
            "empirical": empirical_family,
            "relative_errors": errors,
            "mean_abs_relative_error": float(np.mean([abs(e) for e in errors.values()]))
            if errors
            else None,
        }
    quantile_errors = {
        q: _relative_error(float(model["quantiles"][q]), float(empirical["quantiles"][q]))
        for q in model["quantiles"]
        if q in empirical["quantiles"]
    }
    families["quantiles"] = {
        "model": model["quantiles"],
        "empirical": empirical["quantiles"],
        "relative_errors": quantile_errors,
        "mean_abs_relative_error": float(np.mean([abs(e) for e in quantile_errors.values()]))
        if quantile_errors
        else None,
    }
    return families


class UnderlyingBlock(BaseModel):
    """Serialized empirical-series evidence for one split."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    split: Literal["training", "validation"]
    price_field: str
    parent_request_id: str
    execution_request_id: str
    raw_sha256: str
    normalized_sha256: str
    first_session: str
    last_session: str
    n_sessions: int
    n_returns: int
    series_sha256: str


class EmpiricalBenchmarkArtifact(BaseModel):
    """Deterministic research benchmark artifact (no wall-clock identity)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["research-empirical-benchmark-v1"] = BENCHMARK_SCHEMA_VERSION
    inventory_hash: str
    plan_hash: str
    metric_spec: dict[str, Any]
    metric_spec_hash: str
    underlying: dict[str, UnderlyingBlock]
    metrics: dict[str, dict[str, Any]]
    calibrations: dict[str, dict[str, Any]]
    simulations: dict[str, Any]
    discrepancies: dict[str, dict[str, Any]]
    limitations: list[str]
    benchmark_hash: str

    @model_validator(mode="after")
    def _validate_benchmark(self) -> EmpiricalBenchmarkArtifact:
        if self.benchmark_hash:
            expected = hashlib.sha256(
                canonical_dumps(
                    self.model_dump(mode="json", by_alias=True, exclude={"benchmark_hash"})
                ).encode("utf-8")
            ).hexdigest()
            if self.benchmark_hash != expected:
                raise ValueError("research benchmark hash mismatch")
        return self


def build_empirical_benchmark(
    *,
    inventory: ResearchInventory,
    raw_root: Path,
    processed_root: Path,
    spec: MetricSpecification,
) -> EmpiricalBenchmarkArtifact:
    """Run the full deterministic benchmark pipeline and seal the artifact."""
    training = build_underlying_series(
        inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root
    )
    validation = build_underlying_series(
        inventory=inventory,
        split="validation",
        raw_root=raw_root,
        processed_root=processed_root,
    )
    training_returns = training.returns_array
    validation_returns = validation.returns_array

    spec_hash = spec.spec_hash()

    # ── calibration: TRAINING ONLY ─────────────────────────────────────
    gbm_fit = calibrate_gbm(training_returns, dt=spec.simulation_dt)
    heston_fit = calibrate_heston(
        training_returns,
        dt=spec.simulation_dt,
        seed=spec.heston_seed,
        kappa=spec.heston_kappa_annualized,
        calibration_paths=spec.calibration_paths,
        horizon=spec.simulation_horizon_sessions,
    )

    # ── seeded baseline simulations ────────────────────────────────────
    initial_price = float(training.prices[-1])
    gbm_increments = sample_gbm(
        spec.simulation_paths,
        spec.simulation_horizon_sessions,
        mu=gbm_fit.mu,
        sigma=gbm_fit.sigma,
        initial_price=initial_price,
        dt=spec.simulation_dt,
        seed=spec.gbm_seed,
    )
    heston_increments = sample_heston(
        spec.simulation_paths,
        spec.simulation_horizon_sessions,
        mu=heston_fit.parameters.mu,
        kappa=heston_fit.parameters.kappa,
        theta=heston_fit.parameters.theta,
        xi=heston_fit.parameters.xi,
        rho=heston_fit.parameters.rho,
        v0=heston_fit.parameters.v0,
        dt=spec.simulation_dt,
        seed=spec.heston_seed,
    )
    if np.any(~np.isfinite(gbm_increments)) or np.any(~np.isfinite(heston_increments)):
        raise ValueError("baseline simulations produced non-finite increments")

    # ── evaluation under the same frozen scorecard ─────────────────────
    training_result = compute_scorecard(training_returns, spec.scorecard)
    validation_result = compute_scorecard(validation_returns, spec.scorecard)
    gbm_result = compute_scorecard(gbm_increments.ravel(), spec.scorecard)
    heston_result = compute_scorecard(heston_increments.ravel(), spec.scorecard)
    metrics = {
        "training_empirical": _scorecard_payload(training_result),
        "validation_empirical": _scorecard_payload(validation_result),
        "gbm": _scorecard_payload(gbm_result),
        "heston": _scorecard_payload(heston_result),
    }

    discrepancies = {
        "training": {
            "gbm": _family_errors(metrics["gbm"], metrics["training_empirical"]),
            "heston": _family_errors(metrics["heston"], metrics["training_empirical"]),
        },
        "validation": {
            "gbm": _family_errors(metrics["gbm"], metrics["validation_empirical"]),
            "heston": _family_errors(metrics["heston"], metrics["validation_empirical"]),
        },
    }

    underlying_blocks: dict[str, UnderlyingBlock] = {
        series.split: UnderlyingBlock(
            schema_version=series.schema_version,
            split=series.split,
            price_field=series.price_field,
            parent_request_id=series.parent_request_id,
            execution_request_id=series.execution_request_id,
            raw_sha256=series.raw_sha256,
            normalized_sha256=series.normalized_sha256,
            first_session=series.session_dates[0],
            last_session=series.session_dates[-1],
            n_sessions=len(series.session_dates),
            n_returns=series.n_observations,
            series_sha256=series.series_sha256,
        )
        for series in (training, validation)
    }

    artifact = EmpiricalBenchmarkArtifact(
        inventory_hash=inventory.inventory_hash,
        plan_hash=inventory.plan_hash,
        metric_spec=asdict(spec),
        metric_spec_hash=spec_hash,
        underlying=underlying_blocks,
        metrics=metrics,
        calibrations={
            "gbm": asdict(gbm_fit),
            "heston": asdict(heston_fit),
        },
        simulations={
            "dt": spec.simulation_dt,
            "horizon_sessions": spec.simulation_horizon_sessions,
            "n_paths": spec.simulation_paths,
            "initial_price": initial_price,
            "initial_price_convention": spec.initial_price_convention,
            "gbm_seed": spec.gbm_seed,
            "heston_seed": spec.heston_seed,
        },
        discrepancies=discrepancies,
        limitations=[
            "GBM/Heston baselines calibrated on training split only",
            "Heston kappa fixed and v0=theta; parameters are not uniquely identified",
            "Heston calibration is a bounded deterministic grid search (no scipy dependency)",
            "ARCX statistics training remains uncertain_billing and is unused",
            "Missing training CBBO sessions (2019-01-03, 2019-06-25) are not substituted;"
            " option snapshots are not consumed by this benchmark",
            "Underlying session dates are bound from the raw DBN ts_event index;"
            " prices come from the validated normalized parquet",
            "No annualization: all metrics are on raw daily log returns",
        ],
        benchmark_hash="",
    )
    benchmark_hash = hashlib.sha256(
        canonical_dumps(
            artifact.model_dump(mode="json", by_alias=True, exclude={"benchmark_hash"})
        ).encode("utf-8")
    ).hexdigest()
    return artifact.model_copy(update={"benchmark_hash": benchmark_hash})


def write_benchmark_artifact(path: Path, artifact: EmpiricalBenchmarkArtifact) -> None:
    """Persist the canonical deterministic benchmark artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n",
        encoding="utf-8",
    )
