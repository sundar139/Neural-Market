"""Deep hedging training pipeline — v3 VALIDATED contract implementation.

Exports are the minimal contract-exact surface needed for future scientific
execution and for non-scientific unit tests in Task 202.
"""

from neuralmarket.research.deep_hedging.artifacts import (
    COST_BPS,
    COST_LEVELS,
    EXPECTED_POLICIES,
    HEDGER_SEEDS,
    MEMBERS,
    RUN_PREFIXES,
    SYNTHETIC_SEEDS,
    completeness_check,
    global_failure_check,
    overall_validity,
    policy_checkpoint_path,
    policy_dir,
    synthetic_dataset_path,
    synthetic_manifest_path,
)
from neuralmarket.research.deep_hedging.cvar import cvar_full_set_selection, empirical_cvar
from neuralmarket.research.deep_hedging.generation import (
    generate_and_persist_synthetic_dataset,
    load_synthetic_dataset,
    verify_nsde_checkpoint,
)
from neuralmarket.research.deep_hedging.hedger import GRUHedger
from neuralmarket.research.deep_hedging.pnl import build_features, hedging_pnl
from neuralmarket.research.deep_hedging.runner import (
    ArtifactExistsError,
    AuthorizationError,
    HedgingExecutionAuthorization,
    check_artifact_nonexistence,
    dry_run,
    enumerate_generation_jobs,
    enumerate_training_jobs,
    preflight_checks,
    require_authorization_or_refuse,
    validate_authorization_schema,
)
from neuralmarket.research.deep_hedging.synthetic import (
    HORIZON,
    S_INCEPTION,
    SIGMA_SYNTH,
    black_scholes_p0,
    construct_episode,
    price_levels_from_increments,
)
from neuralmarket.research.deep_hedging.trainer import train_one_policy

__all__ = [
    "COST_BPS",
    "COST_LEVELS",
    "EXPECTED_POLICIES",
    "HEDGER_SEEDS",
    "HORIZON",
    "MEMBERS",
    "RUN_PREFIXES",
    "SIGMA_SYNTH",
    "SYNTHETIC_SEEDS",
    "S_INCEPTION",
    "ArtifactExistsError",
    "AuthorizationError",
    "GRUHedger",
    "HedgingExecutionAuthorization",
    "black_scholes_p0",
    "build_features",
    "check_artifact_nonexistence",
    "completeness_check",
    "construct_episode",
    "cvar_full_set_selection",
    "dry_run",
    "empirical_cvar",
    "enumerate_generation_jobs",
    "enumerate_training_jobs",
    "generate_and_persist_synthetic_dataset",
    "global_failure_check",
    "hedging_pnl",
    "load_synthetic_dataset",
    "overall_validity",
    "policy_checkpoint_path",
    "policy_dir",
    "preflight_checks",
    "price_levels_from_increments",
    "require_authorization_or_refuse",
    "synthetic_dataset_path",
    "synthetic_manifest_path",
    "train_one_policy",
    "validate_authorization_schema",
    "verify_nsde_checkpoint",
]
