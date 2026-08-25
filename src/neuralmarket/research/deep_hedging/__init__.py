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
from neuralmarket.research.deep_hedging.hedger import GRUHedger
from neuralmarket.research.deep_hedging.pnl import build_features, hedging_pnl
from neuralmarket.research.deep_hedging.runner import (
    ArtifactExistsError,
    AuthorizationError,
    check_artifact_nonexistence,
    preflight_checks,
    require_authorization_or_refuse,
)
from neuralmarket.research.deep_hedging.synthetic import (
    HORIZON,
    S_INCEPTION,
    SIGMA_SYNTH,
    black_scholes_p0,
    construct_episode,
    price_levels_from_increments,
)

__all__ = [
    "COST_BPS",
    "COST_LEVELS",
    "EXPECTED_POLICIES",
    "HEDGER_SEEDS",
    "HORIZON",
    "MEMBERS",
    "RUN_PREFIXES",
    "S_INCEPTION",
    "SIGMA_SYNTH",
    "SYNTHETIC_SEEDS",
    "GRUHedger",
    "build_features",
    "hedging_pnl",
    "empirical_cvar",
    "cvar_full_set_selection",
    "price_levels_from_increments",
    "black_scholes_p0",
    "construct_episode",
    "completeness_check",
    "global_failure_check",
    "overall_validity",
    "policy_checkpoint_path",
    "policy_dir",
    "synthetic_dataset_path",
    "synthetic_manifest_path",
    "ArtifactExistsError",
    "AuthorizationError",
    "check_artifact_nonexistence",
    "preflight_checks",
    "require_authorization_or_refuse",
]
