"""Consistency checks for the frozen v5 external-validation contract.

Checks that the machine-readable contract
(``configs/research/structured_vol_v5_external_validation_v1.yaml``) is
internally coherent and stays bound to the frozen v5 candidate and metric
specification. Methodology/preregistration only: this module never constructs
or reads any validation data and never executes the external validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from neuralmarket.eval.scorecard import MetricSpecification
from neuralmarket.research.structured_vol_experiment import load_v5_config

pytestmark = [pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT_YAML = _REPO_ROOT / "configs/research/structured_vol_v5_external_validation_v1.yaml"
_V5_YAML = _REPO_ROOT / "configs/research/structured_vol_neural_sde_v5.yaml"

# Documented frozen v5 candidate identity.
_FROZEN_CONFIG_HASH = (
    "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157"  # pragma: allowlist secret
)
_FROZEN_CHECKPOINT_HASH = (
    "c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4"  # pragma: allowlist secret
)
_FROZEN_METRIC_SPEC_HASH = (
    "5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3"  # pragma: allowlist secret
)
_FROZEN_SOURCE_COMMIT = "357971a67c68492fc0c4f5bf31f94f9685639f65"  # pragma: allowlist secret


def _load_contract() -> dict:
    return yaml.safe_load(_CONTRACT_YAML.read_text(encoding="utf-8"))


def test_contract_parses_and_candidate_pinned() -> None:
    contract = _load_contract()
    assert contract["version"] == "structured-vol-v5-external-validation-v1"
    candidate = contract["candidate"]
    assert candidate["name"] == "structured-volatility-neural-sde-v5"
    assert candidate["config_hash"] == _FROZEN_CONFIG_HASH
    assert candidate["checkpoint_sha256"] == _FROZEN_CHECKPOINT_HASH
    assert candidate["source_commit"] == _FROZEN_SOURCE_COMMIT
    assert candidate["load_semantics"] == "checkpoint_state_only_no_training"


def test_contract_bound_to_frozen_v5_config() -> None:
    contract = _load_contract()
    v5 = load_v5_config(_V5_YAML)
    assert contract["candidate"]["config_hash"] == v5.config_hash()
    assert contract["generation"]["horizon_sessions"] == v5.windows.horizon == v5.sde.horizon
    assert contract["generation"]["path_count"] == v5.n_eval_paths == 1024
    assert contract["generation"]["evaluation_seed"] == v5.eval_seed == 8283


def test_contract_bound_to_frozen_metric_spec() -> None:
    contract = _load_contract()
    spec_hash = MetricSpecification().spec_hash()
    assert spec_hash == _FROZEN_METRIC_SPEC_HASH
    assert contract["target"]["metric_spec_hash"] == spec_hash
    assert contract["target"]["metric_spec"] == "research-metric-spec-v1"
    assert contract["comparison"]["metric_spec"] == "research-metric-spec-v1"


def test_contract_append_report_only_no_threshold() -> None:
    contract = _load_contract()
    assert contract["classification"]["mode"] == "report_only"
    assert contract["classification"]["success_label"] == "EXTERNAL_VALIDATION_COMPLETED"
    assert "threshold" not in contract["classification"]


def test_contract_one_shot_access_and_prohibitions() -> None:
    contract = _load_contract()
    access = contract["access"]
    assert access["max_top_level_external_validation_evaluations"] == 1
    assert access["max_validation_series_constructions"] == 1
    for key, value in contract["prohibitions"].items():
        assert value is True, f"prohibition {key} must be true"


def test_contract_conditioning_is_training_boundary_only() -> None:
    contract = _load_contract()
    assert contract["conditioning"]["mode"] == "training_boundary"
    assert contract["conditioning"]["validation_targets_touch_context"] is False


def test_contract_comparison_refers_to_existing_implementation() -> None:
    contract = _load_contract()
    from neuralmarket.data.research.benchmark import _family_errors
    from neuralmarket.eval.scorecard import compute_scorecard

    assert contract["comparison"]["family_error_method"] == (
        "neuralmarket.data.research.benchmark._family_errors"
    )
    assert contract["comparison"]["scorecard_implementation"] == (
        "neuralmarket.eval.scorecard.compute_scorecard"
    )
    assert callable(_family_errors)
    assert callable(compute_scorecard)
    assert contract["comparison"]["aggregation"].startswith("none")
