"""Frozen pre-neural simulator comparator suite.

Completes the protocol's classical generator baseline list on top of the
accepted empirical benchmark. GBM and Heston results are copied verbatim from
``empirical_benchmark_v1.json`` (which is never mutated and whose self-hash is
revalidated on load); the IID bootstrap, circular block bootstrap, and
GJR-GARCH comparators are fitted on the frozen TRAINING split only, simulated
with dedicated frozen seeds, and scored with the same frozen
``research-metric-spec-v1`` scorecard used for GBM and Heston.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

from neuralmarket.baselines import simulated_prices
from neuralmarket.baselines.bootstrap import (
    BLOCK_BOOTSTRAP_BLOCK_LENGTH,
    BLOCK_BOOTSTRAP_BOUNDARY_POLICY,
    BLOCK_BOOTSTRAP_METHOD,
    sample_block_bootstrap,
    sample_iid_bootstrap,
)
from neuralmarket.baselines.garch import calibrate_gjr_garch, sample_gjr_garch
from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.benchmark import (
    EmpiricalBenchmarkArtifact,
    _family_errors,
    _scorecard_payload,
)
from neuralmarket.data.research.inventory import ResearchInventory
from neuralmarket.data.research.underlying import build_underlying_series
from neuralmarket.eval.scorecard import MetricSpecification, compute_scorecard

BASELINE_SUITE_SCHEMA_VERSION: Literal["research-simulator-baseline-suite-v1"] = (
    "research-simulator-baseline-suite-v1"
)

_PROTOCOL_SOURCE = "reports/protocol/research_protocol_v1.md"

COMPARATOR_NAMES: tuple[str, ...] = (
    "iid_bootstrap",
    "block_bootstrap",
    "stationary_bootstrap",
    "gbm",
    "gjr_garch",
    "egarch",
    "heston",
)

EVALUATED_COMPARATORS: tuple[str, ...] = (
    "iid_bootstrap",
    "block_bootstrap",
    "gbm",
    "gjr_garch",
    "heston",
)

_SCALAR_FAMILIES: tuple[str, ...] = ("mean", "variance", "skewness", "excess_kurtosis")
_DICT_FAMILIES: tuple[str, ...] = (
    "quantiles",
    "return_acf",
    "abs_return_acf",
    "sq_return_acf",
    "leverage_correlations",
)


@dataclass(frozen=True)
class BaselineSuiteSpec:
    """Frozen, versioned configuration of the new comparator baselines.

    Seeds and the block-bootstrap convention are fixed here before any
    baseline is evaluated. The frozen ``research-metric-spec-v1`` metric
    specification is intentionally NOT extended, so its hash is unaffected.
    """

    version: str = "research-baseline-suite-spec-v1"
    iid_bootstrap_seed: int = 2027
    block_bootstrap_seed: int = 2029
    gjr_garch_seed: int = 2039
    block_bootstrap_method: str = BLOCK_BOOTSTRAP_METHOD
    block_bootstrap_block_length: int = BLOCK_BOOTSTRAP_BLOCK_LENGTH
    block_bootstrap_boundary_policy: str = BLOCK_BOOTSTRAP_BOUNDARY_POLICY
    garch_grid_points: int = 9
    garch_refinement_passes: int = 6

    def spec_hash(self) -> str:
        """Deterministic identity of the suite configuration (no wall clock)."""
        return hashlib.sha256(canonical_dumps(asdict(self)).encode("utf-8")).hexdigest()


class ComparatorEntry(BaseModel):
    """One protocol comparator and its explicit disposition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    protocol_requirement: str
    protocol_source: str
    status: Literal["implemented", "accepted_prior", "not_selected"]
    implementation: str | None = None
    seed: int | None = None
    reason: str


class ComparatorRegistry(BaseModel):
    """Frozen accounting of every protocol comparator before neural-SDE work."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["research-comparator-registry-v1"] = "research-comparator-registry-v1"
    protocol_source: str = _PROTOCOL_SOURCE
    entries: tuple[ComparatorEntry, ...]
    suite_spec: dict[str, Any]
    registry_hash: str = ""

    @model_validator(mode="after")
    def _validate_registry(self) -> ComparatorRegistry:
        names = [entry.name for entry in self.entries]
        if len(names) != len(set(names)):
            raise ValueError("comparator registry contains duplicate comparators")
        if set(names) != set(COMPARATOR_NAMES):
            missing = sorted(set(COMPARATOR_NAMES) - set(names))
            extra = sorted(set(names) - set(COMPARATOR_NAMES))
            raise ValueError(
                f"comparator registry accounting mismatch: missing={missing} extra={extra}"
            )
        if self.registry_hash and self.registry_hash != self._compute_hash():
            raise ValueError("comparator registry hash mismatch")
        return self

    def _compute_hash(self) -> str:
        return hashlib.sha256(
            canonical_dumps(
                self.model_dump(mode="json", by_alias=True, exclude={"registry_hash"})
            ).encode("utf-8")
        ).hexdigest()


def build_comparator_registry(suite_spec: BaselineSuiteSpec) -> ComparatorRegistry:
    """Build the frozen comparator registry with the GJR/EGARCH decision recorded."""
    entries = (
        ComparatorEntry(
            name="iid_bootstrap",
            protocol_requirement="IID historical bootstrap",
            protocol_source=f"{_PROTOCOL_SOURCE}:27",
            status="implemented",
            implementation="neuralmarket.baselines.bootstrap.sample_iid_bootstrap",
            seed=suite_spec.iid_bootstrap_seed,
            reason="Required classical generator baseline; resamples training returns only.",
        ),
        ComparatorEntry(
            name="block_bootstrap",
            protocol_requirement="stationary or block bootstrap",
            protocol_source=f"{_PROTOCOL_SOURCE}:28",
            status="implemented",
            implementation="neuralmarket.baselines.bootstrap.sample_block_bootstrap",
            seed=suite_spec.block_bootstrap_seed,
            reason=(
                "Selected side of the protocol's 'stationary or block bootstrap' alternative:"
                f" {suite_spec.block_bootstrap_method} with a fixed"
                f" {suite_spec.block_bootstrap_block_length}-session block length"
                " (approximately one trading month), frozen before evaluation."
            ),
        ),
        ComparatorEntry(
            name="stationary_bootstrap",
            protocol_requirement="stationary or block bootstrap",
            protocol_source=f"{_PROTOCOL_SOURCE}:28",
            status="not_selected",
            reason=(
                "Alternative to the block bootstrap, not a second mandatory comparator."
                " The block bootstrap satisfies the requirement with a fixed, declared"
                " block length; the stationary bootstrap's geometric block length adds a"
                " tuning degree of freedom with no protocol mandate."
            ),
        ),
        ComparatorEntry(
            name="gbm",
            protocol_requirement="geometric Brownian motion (GBM)",
            protocol_source=f"{_PROTOCOL_SOURCE}:29",
            status="accepted_prior",
            implementation="neuralmarket.baselines.gbm.sample_gbm",
            seed=MetricSpecification().gbm_seed,
            reason="Accepted in empirical_benchmark_v1.json; copied verbatim, not recalibrated.",
        ),
        ComparatorEntry(
            name="gjr_garch",
            protocol_requirement="GJR-GARCH or EGARCH",
            protocol_source=f"{_PROTOCOL_SOURCE}:30",
            status="implemented",
            implementation="neuralmarket.baselines.garch.sample_gjr_garch",
            seed=suite_spec.gjr_garch_seed,
            reason=(
                "Selected side of the protocol's 'GJR-GARCH or EGARCH' alternative."
                " Smallest scientifically defensible implementation: the level-variance"
                " recursion admits closed-form positivity and stationarity constraints and"
                " an exact hand-checkable recursion, and it captures the leverage effect"
                " the protocol's stylized-fact scorecard measures."
            ),
        ),
        ComparatorEntry(
            name="egarch",
            protocol_requirement="GJR-GARCH or EGARCH",
            protocol_source=f"{_PROTOCOL_SOURCE}:30",
            status="not_selected",
            reason=(
                "Protocol line 30 expresses 'GJR-GARCH or EGARCH' as alternatives, not two"
                " mandatory comparators. GJR-GARCH was selected on specification grounds"
                " before any baseline result was inspected; no validation metric entered"
                " the choice."
            ),
        ),
        ComparatorEntry(
            name="heston",
            protocol_requirement="Heston",
            protocol_source=f"{_PROTOCOL_SOURCE}:31",
            status="accepted_prior",
            implementation="neuralmarket.baselines.heston.sample_heston",
            seed=MetricSpecification().heston_seed,
            reason="Accepted in empirical_benchmark_v1.json; copied verbatim, not recalibrated.",
        ),
    )
    registry = ComparatorRegistry(entries=entries, suite_spec=asdict(suite_spec))
    return registry.model_copy(update={"registry_hash": registry._compute_hash()})


class SimulatorBaselineSuiteArtifact(BaseModel):
    """Deterministic frozen comparator suite (no wall-clock identity)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["research-simulator-baseline-suite-v1"] = BASELINE_SUITE_SCHEMA_VERSION
    benchmark_hash: str
    metric_spec_hash: str
    inventory_hash: str
    plan_hash: str
    training_series_sha256: str
    validation_series_sha256: str
    suite_spec: dict[str, Any]
    suite_spec_hash: str
    comparator_registry: dict[str, Any]
    registry_hash: str
    calibrations: dict[str, dict[str, Any]]
    simulations: dict[str, Any]
    metrics: dict[str, dict[str, Any]]
    discrepancies: dict[str, dict[str, Any]]
    rankings: dict[str, dict[str, list[str]]]
    limitations: list[str]
    suite_hash: str

    @model_validator(mode="after")
    def _validate_suite(self) -> SimulatorBaselineSuiteArtifact:
        for split in ("training", "validation"):
            evaluated = set(self.discrepancies[split])
            if evaluated != set(EVALUATED_COMPARATORS):
                raise ValueError(
                    f"baseline suite {split} comparator set is incomplete: {evaluated}"
                )
        for name in EVALUATED_COMPARATORS:
            if name not in self.metrics:
                raise ValueError(f"baseline suite is missing metrics for {name}")
        if self.suite_hash:
            expected = hashlib.sha256(
                canonical_dumps(
                    self.model_dump(mode="json", by_alias=True, exclude={"suite_hash"})
                ).encode("utf-8")
            ).hexdigest()
            if self.suite_hash != expected:
                raise ValueError("baseline suite hash mismatch")
        return self


def load_accepted_benchmark(path: Path) -> EmpiricalBenchmarkArtifact:
    """Load and revalidate the accepted empirical benchmark (read-only)."""
    return EmpiricalBenchmarkArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _rankings(split_discrepancies: dict[str, Any]) -> dict[str, list[str]]:
    """Order comparators by error magnitude within each metric family."""
    ordering: dict[str, list[str]] = {}
    for family in _SCALAR_FAMILIES:
        scored = [
            (abs(float(split_discrepancies[name][family]["relative_error"])), name)
            for name in EVALUATED_COMPARATORS
        ]
        ordering[family] = [name for _, name in sorted(scored)]
    for family in _DICT_FAMILIES:
        scored = []
        for name in EVALUATED_COMPARATORS:
            value = split_discrepancies[name][family]["mean_abs_relative_error"]
            scored.append((float("inf") if value is None else abs(float(value)), name))
        ordering[family] = [name for _, name in sorted(scored)]
    return ordering


def build_baseline_suite(
    *,
    inventory: ResearchInventory,
    raw_root: Path,
    processed_root: Path,
    benchmark_path: Path,
    spec: MetricSpecification | None = None,
    suite_spec: BaselineSuiteSpec | None = None,
) -> SimulatorBaselineSuiteArtifact:
    """Build the deterministic simulator baseline suite bound to the benchmark.

    Args:
        inventory: Frozen research inventory.
        raw_root: Root of the checksum-verified raw acquisition tree.
        processed_root: Root of the validated normalized tree.
        benchmark_path: Path to the accepted ``empirical_benchmark_v1.json``.
        spec: Frozen metric specification (defaults to ``research-metric-spec-v1``).
        suite_spec: Frozen baseline-suite configuration.

    Returns:
        The sealed suite artifact.

    Raises:
        ValueError: If the metric specification, empirical series, or simulation
            contract do not match the accepted benchmark.
    """
    spec = MetricSpecification() if spec is None else spec
    suite_spec = BaselineSuiteSpec() if suite_spec is None else suite_spec
    benchmark = load_accepted_benchmark(benchmark_path)

    spec_hash = spec.spec_hash()
    if spec_hash != benchmark.metric_spec_hash:
        raise ValueError("metric specification does not match the accepted empirical benchmark")

    training = build_underlying_series(
        inventory=inventory, split="training", raw_root=raw_root, processed_root=processed_root
    )
    validation = build_underlying_series(
        inventory=inventory, split="validation", raw_root=raw_root, processed_root=processed_root
    )
    for series in (training, validation):
        if series.series_sha256 != benchmark.underlying[series.split].series_sha256:
            raise ValueError(
                f"{series.split} empirical series does not match the accepted benchmark"
            )

    training_returns = training.returns_array
    initial_price = float(training.prices[-1])
    if initial_price != float(benchmark.simulations["initial_price"]):
        raise ValueError("initial price does not match the accepted benchmark simulation contract")

    # ── fitting: TRAINING ONLY ─────────────────────────────────────────
    garch_fit = calibrate_gjr_garch(
        training_returns,
        grid_points=suite_spec.garch_grid_points,
        refinement_passes=suite_spec.garch_refinement_passes,
    )

    # ── seeded simulations under the frozen shared contract ────────────
    paths = spec.simulation_paths
    horizon = spec.simulation_horizon_sessions
    increments = {
        "iid_bootstrap": sample_iid_bootstrap(
            training_returns, paths, horizon, seed=suite_spec.iid_bootstrap_seed
        ),
        "block_bootstrap": sample_block_bootstrap(
            training_returns,
            paths,
            horizon,
            block_length=suite_spec.block_bootstrap_block_length,
            seed=suite_spec.block_bootstrap_seed,
        ),
        "gjr_garch": sample_gjr_garch(
            paths,
            horizon,
            mu=garch_fit.parameters.mu,
            omega=garch_fit.parameters.omega,
            alpha=garch_fit.parameters.alpha,
            gamma=garch_fit.parameters.gamma,
            beta=garch_fit.parameters.beta,
            seed=suite_spec.gjr_garch_seed,
        ),
    }
    for name, values in increments.items():
        if values.shape != (paths, horizon):
            raise ValueError(f"{name} simulation has the wrong shape")
        if np.any(~np.isfinite(values)):
            raise ValueError(f"{name} simulation produced non-finite increments")
        if not np.all(simulated_prices(values, initial_price=initial_price) > 0):
            raise ValueError(f"{name} simulation produced non-positive prices")

    # ── evaluation with the identical frozen scorecard ─────────────────
    metrics: dict[str, dict[str, Any]] = {
        "training_empirical": benchmark.metrics["training_empirical"],
        "validation_empirical": benchmark.metrics["validation_empirical"],
        "gbm": benchmark.metrics["gbm"],
        "heston": benchmark.metrics["heston"],
    }
    for name, values in increments.items():
        metrics[name] = _scorecard_payload(compute_scorecard(values.ravel(), spec.scorecard))

    discrepancies: dict[str, dict[str, Any]] = {}
    for split, empirical_key in (
        ("training", "training_empirical"),
        ("validation", "validation_empirical"),
    ):
        block: dict[str, Any] = {
            "gbm": benchmark.discrepancies[split]["gbm"],
            "heston": benchmark.discrepancies[split]["heston"],
        }
        for name in increments:
            block[name] = _family_errors(metrics[name], metrics[empirical_key])
        discrepancies[split] = block

    registry = build_comparator_registry(suite_spec)
    artifact = SimulatorBaselineSuiteArtifact(
        benchmark_hash=benchmark.benchmark_hash,
        metric_spec_hash=spec_hash,
        inventory_hash=inventory.inventory_hash,
        plan_hash=inventory.plan_hash,
        training_series_sha256=training.series_sha256,
        validation_series_sha256=validation.series_sha256,
        suite_spec=asdict(suite_spec),
        suite_spec_hash=suite_spec.spec_hash(),
        comparator_registry=registry.model_dump(mode="json", by_alias=True),
        registry_hash=registry.registry_hash,
        calibrations={
            "gjr_garch": asdict(garch_fit),
            "gbm": benchmark.calibrations["gbm"],
            "heston": benchmark.calibrations["heston"],
        },
        simulations={
            "dt": spec.simulation_dt,
            "horizon_sessions": horizon,
            "n_paths": paths,
            "initial_price": initial_price,
            "initial_price_convention": spec.initial_price_convention,
            "training_population_size": int(training_returns.size),
            "seeds": {
                "gbm": spec.gbm_seed,
                "heston": spec.heston_seed,
                "iid_bootstrap": suite_spec.iid_bootstrap_seed,
                "block_bootstrap": suite_spec.block_bootstrap_seed,
                "gjr_garch": suite_spec.gjr_garch_seed,
            },
            "block_bootstrap": {
                "method": suite_spec.block_bootstrap_method,
                "block_length": suite_spec.block_bootstrap_block_length,
                "boundary_policy": suite_spec.block_bootstrap_boundary_policy,
                "blocks_per_path": -(-horizon // suite_spec.block_bootstrap_block_length),
            },
        },
        metrics=metrics,
        discrepancies=discrepancies,
        rankings={split: _rankings(discrepancies[split]) for split in discrepancies},
        limitations=[
            "All resampling and fitting use the training split only; validation is"
            " evaluation-only and the sealed final-test block is never read",
            "GBM and Heston results are copied verbatim from the accepted"
            " empirical_benchmark_v1.json and are not recalibrated here",
            "Bootstrap comparators cannot generate returns outside the training"
            " empirical support, so their tails are bounded by the training sample",
            "The IID bootstrap destroys all temporal dependence by construction",
            "The block bootstrap preserves dependence only within a 22-session block;"
            " block joins break dependence and the block length was frozen a priori,"
            " not tuned",
            "GJR-GARCH uses a two-step estimator (sample-mean mu, variance targeting"
            " for omega) and a bounded deterministic grid search rather than joint"
            " numerical MLE, because no optimizer dependency is installed",
            "GJR-GARCH innovations are Gaussian; conditional fat tails come only from"
            " the volatility recursion",
            "GJR-GARCH paths start at the model unconditional variance, matching the"
            " Heston v0=theta long-run initialization, so they are not conditional"
            " forecasts from the last training session",
            "EGARCH and the stationary bootstrap are recorded as unselected protocol"
            " alternatives, not omissions",
            "No annualization: all metrics are on raw daily log returns",
        ],
        suite_hash="",
    )
    suite_hash = hashlib.sha256(
        canonical_dumps(
            artifact.model_dump(mode="json", by_alias=True, exclude={"suite_hash"})
        ).encode("utf-8")
    ).hexdigest()
    return artifact.model_copy(update={"suite_hash": suite_hash})


def write_baseline_suite_artifact(path: Path, artifact: SimulatorBaselineSuiteArtifact) -> None:
    """Persist the canonical deterministic baseline-suite artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        canonical_dumps(artifact.model_dump(mode="json", by_alias=True)) + "\n",
        encoding="utf-8",
    )
