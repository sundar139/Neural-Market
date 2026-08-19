"""Synthetic/mocked tests for the frozen v5 external-validation harness.

Never touches real validation artifacts or numerics: every series, suite,
target, and checkpoint input is synthetic or monkeypatched. Verifies the
harness's fail-closed one-shot access, frozen geometry, byte-identity target
check, per-family comparison semantics, write-once result mechanics, and the
prohibition guards.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from neuralmarket.data.research.benchmark import _family_errors
from neuralmarket.data.research.sde_windows import WindowSpec
from neuralmarket.eval.scorecard import MetricSpecification

# The harness lives outside `src`; import it by absolute path after inserting its
# own sys.path patch (the module inserts <repo>/src itself on import).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HARNESS_PATH = (
    _REPO_ROOT / "reports/research/evidence/structured_vol_v5_external_validation_harness.py"
)
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("v5_extval_harness_test", _HARNESS_PATH)
_h_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_h_module)  # type: ignore[union-attr]
h = _h_module

pytestmark = [pytest.mark.unit]

_V5_YAML = _REPO_ROOT / "configs/research/structured_vol_neural_sde_v5.yaml"
# Suite canonical (self-referential) hash, pinned as content.
_FROZEN_SUITE_HASH = (
    "445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099"  # pragma: allowlist secret
)
_ZERO_COUNTERS = dict.fromkeys(h._COUNTERS, 0)


@pytest.fixture(autouse=True)
def _reset_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(h, "_COUNTERS", dict(_ZERO_COUNTERS))


# ── synthetic fixtures ─────────────────────────────────────────────────────


def _synthetic_series(
    split: str, n_returns: int, seed: int, marker: float = 0.0
) -> SimpleNamespace:
    rng = np.random.default_rng(seed)
    if marker:  # validation marker: unmistakable, non-degenerate value range
        returns = rng.uniform(marker, marker + 0.5, size=n_returns)
    else:
        returns = rng.normal(0.0, 0.01, size=n_returns)
    prices = [100.0 + i * 0.01 for i in range(n_returns + 1)]
    dates = [
        f"20{i // 252:02d}-{(i % 252) // 21 + 1:02d}-{i % 21 + 1:02d}" for i in range(n_returns + 1)
    ]
    return SimpleNamespace(
        split=split,
        log_returns=tuple(float(v) for v in returns),
        returns_array=returns,
        prices=tuple(prices),
        session_dates=tuple(dates),
        n_observations=n_returns,
        series_sha256=f"synthetic-{split}-{n_returns}",
    )


TRAIN_SERIES = _synthetic_series("training", 400, 101)
VAL_SERIES = _synthetic_series("validation", 274, 202, marker=9.9)


def _synthetic_scorecard(seed: int, prefix: float = 0.0) -> dict:
    rng = np.random.default_rng(seed)
    lags = [1, 5, 22, 66]
    quantiles = ["0.01", "0.05", "0.10", "0.90", "0.95", "0.99"]
    return {
        "mean": prefix + float(rng.normal()),
        "variance": prefix + float(rng.uniform(0.5, 2.0)),
        "skewness": prefix + float(rng.normal()),
        "excess_kurtosis": prefix + float(rng.uniform(0.0, 5.0)),
        "quantiles": {q: prefix + float(rng.normal()) for q in quantiles},
        "return_acf": {lag: prefix + float(rng.normal(scale=0.1)) for lag in lags},
        "abs_return_acf": {lag: prefix + float(rng.normal(scale=0.1)) for lag in lags},
        "sq_return_acf": {lag: prefix + float(rng.normal(scale=0.1)) for lag in lags},
        "leverage_correlations": {lag: prefix + float(rng.normal(scale=0.1)) for lag in lags},
    }


def _synthetic_discrepancies(rng: np.random.Generator) -> dict:
    scalar = ("mean", "variance", "skewness", "excess_kurtosis")
    dictf = ("quantiles", "return_acf", "abs_return_acf", "sq_return_acf", "leverage_correlations")
    discrepancies: dict = {}
    for name in h.EVALUATED_COMPARATORS:
        block: dict = {}
        for family in scalar:
            block[family] = {"relative_error": float(rng.uniform(-2.0, 2.0))}
        for family in dictf:
            block[family] = {"mean_abs_relative_error": float(rng.uniform(0.0, 2.0))}
        discrepancies[name] = block
    return discrepancies


def _synthetic_suite(rng: np.random.Generator | None = None) -> SimpleNamespace:
    rng = rng or np.random.default_rng(7)
    validation_empirical = _synthetic_scorecard(11, prefix=1.0)
    discrepancies = {split: _synthetic_discrepancies(rng) for split in ("training", "validation")}
    rankings = {
        split: {
            family: list(h.EVALUATED_COMPARATORS)
            for family in list(h._SCALAR_FAMILIES) + list(h._DICT_FAMILIES)
        }
        for split in ("training", "validation")
    }
    return SimpleNamespace(
        metrics={
            "training_empirical": _synthetic_scorecard(10, prefix=0.0),
            "validation_empirical": validation_empirical,
        },
        discrepancies=discrepancies,
        rankings=rankings,
        suite_hash="synthetic-suite-hash",
        metric_spec_hash="synthetic-spec-hash",
        benchmark_hash="synthetic-bench-hash",
        validation_series_sha256=VAL_SERIES.series_sha256,
        training_series_sha256=TRAIN_SERIES.series_sha256,
    )


def _fake_report_builder(calls: list[str]) -> object:
    def _builder(*, inventory, split: str, raw_root: Path, processed_root: Path):
        calls.append(split)
        if split == "training":
            return TRAIN_SERIES
        if split == "validation":
            return VAL_SERIES
        raise ValueError(split)

    return _builder


# 1. module import purity (no validation load, no new output creation)
def test_module_import_is_pure() -> None:
    assert all(v == 0 for v in h.counters().values())


# 1b. pre-execution collision guard (output-absence) — tested against a clean
# synthetic directory; the real post-execution transcript/exit evidence may
# already exist and must never be deleted to satisfy this test.
def test_output_collision_guard_fails_on_existing_file(tmp_path) -> None:
    occupied = tmp_path / "confirmatory.json"
    occupied.write_bytes(b"existing")
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        h.write_result_once({"status": "different"}, occupied)


# 2. contract identities are pinned correctly and bound to the real frozen files
def test_contract_identities_pinned() -> None:
    from neuralmarket.research.structured_vol_experiment import load_v5_config

    assert h.CONTRACT_VERSION == "structured-vol-v5-external-validation-v1"
    assert load_v5_config(_V5_YAML).config_hash() == h.CANDIDATE_CONFIG_HASH
    assert MetricSpecification().spec_hash() == h.METRIC_SPEC_HASH
    assert hashlib.sha256(h.CHECKPOINT_PATH.read_bytes()).hexdigest() == h.CHECKPOINT_SHA256
    assert hashlib.sha256(h.AMENDMENT_PATH.read_bytes()).hexdigest() == h.AMENDMENT_SHA256
    assert hashlib.sha256(h.CONTRACT_YAML_PATH.read_bytes()).hexdigest() == h.CONTRACT_YAML_SHA256
    assert hashlib.sha256(h.SUITE_PATH.read_bytes()).hexdigest() == h.SUITE_FILE_SHA256
    # SUITE_HASH is the suite's self-referential canonical hash (not its file-bytes
    # hash); pinned as a frozen literal, shielded as content.
    assert h.SUITE_HASH == _FROZEN_SUITE_HASH


# 3. canonical checkpoint substitution is rejected
def test_checkpoint_substitution_rejected(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    imposter = tmp_path / "imposter.pt"
    imposter.write_bytes(b"not the canonical checkpoint")
    monkeypatch.setattr(h, "CHECKPOINT_PATH", imposter)
    with pytest.raises(RuntimeError, match="substitution"):
        h.verify_canonical_checkpoint()
    assert h._COUNTERS["checkpoint_substitution_attempts"] == 1

    missing = tmp_path / "missing.pt"
    monkeypatch.setattr(h, "CHECKPOINT_PATH", missing)
    with pytest.raises(RuntimeError, match="missing"):
        h.verify_canonical_checkpoint()
    assert h._COUNTERS["checkpoint_substitution_attempts"] == 2


# 4. training-boundary context contains no validation data
def test_training_boundary_context_has_no_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))
    spec = WindowSpec()
    boundary = h.build_boundary_context(TRAIN_SERIES, spec)
    assert boundary["eval_window"].window_id == "w_boundary"
    assert np.array_equal(boundary["eval_window"].context_returns, TRAIN_SERIES.returns_array[-22:])
    assert not np.any(np.isin(boundary["eval_window"].context_returns, VAL_SERIES.returns_array))
    assert np.isfinite(boundary["eval_context"]).all()
    assert len(boundary["eval_context"]) == 4  # frozen 4-feature context vector
    assert h._COUNTERS["validation_series_attempts"] == 0


# 5. first synthetic validation construction succeeds
def test_first_validation_construction_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))
    series = h.build_validation_series_once(
        inventory=object(), raw_root=Path("."), processed_root=Path(".")
    )
    assert series is VAL_SERIES
    assert h._COUNTERS["validation_series_attempts"] == 1
    assert h._COUNTERS["validation_series_constructions"] == 1
    assert calls == ["validation"]


# 6. second validation construction fails before the builder runs
def test_second_validation_construction_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))
    h.build_validation_series_once(inventory=object(), raw_root=Path("."), processed_root=Path("."))
    with pytest.raises(RuntimeError, match="one-shot"):
        h.build_validation_series_once(
            inventory=object(), raw_root=Path("."), processed_root=Path(".")
        )
    assert calls == ["validation"]  # builder executed exactly once


# 7. unexpected split fails closed
def test_unexpected_split_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))
    with pytest.raises(ValueError, match="validation"):
        h.build_validation_series_once(
            inventory=object(), raw_root=Path("."), processed_root=Path("."), split="final_test"
        )
    assert calls == []
    assert h._COUNTERS["validation_series_attempts"] == 0


# 8. synthetic frozen-target byte match succeeds
def test_frozen_target_byte_match_succeeds() -> None:
    payload = h.recompute_validation_target(VAL_SERIES, MetricSpecification())
    verification = h.verify_frozen_target(payload, payload)
    assert verification["match"] is True
    assert verification["recomputed_identity"] == verification["frozen_identity"]


# 9. synthetic target mismatch fails closed
def test_frozen_target_mismatch_fails_closed() -> None:
    payload = h.recompute_validation_target(VAL_SERIES, MetricSpecification())
    mutated = dict(payload)
    mutated["mean"] = float(payload["mean"]) + 1e-9
    with pytest.raises(RuntimeError, match="does not match"):
        h.verify_frozen_target(payload, mutated)


# 10. generated-shape mismatch rejected
def test_generated_shape_mismatch_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(h, "simulate_structured", lambda *a, **k: torch.zeros((4, 3)))
    with pytest.raises(RuntimeError, match="shape"):
        h.generate_paths(object(), np.zeros(4))
    assert h._COUNTERS["model_simulation_calls"] == 1


# 11. generated NaN/Inf rejected before any scoring
def test_generated_nan_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        h, "simulate_structured", lambda *a, **k: torch.full((1024, 63), float("nan"))
    )
    with pytest.raises(RuntimeError, match="NaN"):
        h.generate_paths(object(), np.zeros(4))
    assert h._COUNTERS["generated_scorecard_calls"] == 0


# 12. family-error NaN rejected
def test_family_error_nan_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        h, "_family_errors", lambda *a, **k: {"mean": {"relative_error": float("nan")}}
    )
    with pytest.raises(RuntimeError, match="non-finite"):
        h.compute_family_errors({"mean": 0.0}, {"mean": 0.0})
    assert h._COUNTERS["family_error_calls"] == 1


# 13. comparator output uses exactly the frozen metric families
def test_comparator_uses_exactly_frozen_families() -> None:
    suite = _synthetic_suite()
    neural_payload = _synthetic_scorecard(5)
    neural_family = _family_errors(neural_payload, suite.metrics["validation_empirical"])
    comparison = h.validation_family_comparison(suite, neural_family)
    expected = set(list(h._SCALAR_FAMILIES) + list(h._DICT_FAMILIES))
    assert set(comparison) == expected
    keys = {
        "candidate_error",
        "nearest_baseline_name",
        "nearest_baseline_error",
        "candidate_rank_among_6",
        "baseline_reference_ranking",
        "all_errors",
    }
    for family in comparison:
        assert set(comparison[family]) == keys


# 14. baseline comparator set is exactly the five frozen names
def test_baseline_comparator_set_exactly_five() -> None:
    assert list(h.EVALUATED_COMPARATORS) == [
        "iid_bootstrap",
        "block_bootstrap",
        "gbm",
        "gjr_garch",
        "heston",
    ]
    assert len(h.EVALUATED_COMPARATORS) == 5


# 15. candidate-insertion ranking matches the frozen _comparison_block semantics
def test_ranking_matches_comparison_block() -> None:
    from neuralmarket.research.neural_sde_experiment import _comparison_block

    suite = _synthetic_suite()
    neural_payload = _synthetic_scorecard(5)
    neural_family = _family_errors(neural_payload, suite.metrics["validation_empirical"])
    mine = h.validation_family_comparison(suite, neural_family)
    reference = _comparison_block(suite, neural_payload)["validation"]

    for family in mine:
        ref = reference[family]
        assert mine[family]["nearest_baseline_name"] == ref["nearest_baseline"]
        assert mine[family]["candidate_rank_among_6"] == ref["neural_rank"]
        mine_err = mine[family]["candidate_error"]
        ref_err = ref["errors"]["neural_sde_signature"]
        if ref_err != float("inf"):
            assert math.isclose(mine_err, float(ref_err), rel_tol=0.0, abs_tol=1e-12)
        for name, value in ref["errors"].items():
            if name == "neural_sde_signature":
                continue  # candidate key differs (presentational only); compared above
            mine_value = mine[family]["all_errors"][name]
            assert (value is None and mine_value is None) or math.isclose(
                mine_value, float(value), rel_tol=0.0, abs_tol=1e-12
            )


# 16. exact tie places v5 after an equal-error baseline
def test_tie_places_candidate_after_equal_baseline() -> None:
    suite = _synthetic_suite()
    for name in suite.discrepancies["validation"]:
        for family in h._SCALAR_FAMILIES:
            suite.discrepancies["validation"][name][family] = {"relative_error": 10.0}
    suite.discrepancies["validation"]["gbm"]["variance"] = {"relative_error": 5.0}

    neural_family = {family: {"relative_error": 10.0} for family in h._SCALAR_FAMILIES}
    neural_family["variance"] = {"relative_error": 5.0}
    for family in h._DICT_FAMILIES:
        neural_family[family] = {"mean_abs_relative_error": 3.0}

    comparison = h.validation_family_comparison(suite, neural_family)
    block = comparison["variance"]
    assert block["candidate_error"] == 5.0
    assert block["nearest_baseline_name"] == "gbm"
    assert block["nearest_baseline_error"] == 5.0
    assert block["candidate_rank_among_6"] == 2  # gbm first (equal error, inserted first); v5 after


# 17. no aggregate / overall winner emitted
def test_no_aggregate_or_overall_winner() -> None:
    suite = _synthetic_suite()
    neural_family = _family_errors(_synthetic_scorecard(5), suite.metrics["validation_empirical"])
    comparison = h.validation_family_comparison(suite, neural_family)
    top = set(comparison) | {k for family in comparison for k in comparison[family]}
    assert not {"aggregate", "overall", "winner", "overall_winner", "total_rank"} & top


# 18. training/refit/tuning/final-test counters are zero on the real path
def test_prohibition_counters_zero_on_synthetic_run(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _run_synthetic_e2e(tmp_path, monkeypatch)
    for key in (
        "training_calls",
        "refit_calls",
        "tuning_calls",
        "final_test_attempts",
        "provider_calls",
        "network_calls",
    ):
        assert result["counters"][key] == 0
    assert result["counters"]["validation_series_attempts"] == 1
    assert result["counters"]["validation_series_constructions"] == 1
    assert result["counters"]["external_validation_evaluations"] == 1
    assert result["counters"]["checkpoint_substitution_attempts"] == 0


def test_guard_layer_raises_for_forbidden_actions() -> None:
    for guard, key in (
        (h.guard_training, "training_calls"),
        (h.guard_refit, "refit_calls"),
        (h.guard_tuning, "tuning_calls"),
        (h.guard_final_test, "final_test_attempts"),
        (h.guard_provider, "provider_calls"),
        (h.guard_network, "network_calls"),
    ):
        with pytest.raises(h.ForbiddenActionError):
            guard()
        assert h._COUNTERS[key] >= 1


# 19. result write-once succeeds once
def test_result_write_once_succeeds(tmp_path) -> None:
    path = tmp_path / "confirmatory.json"
    h.write_result_once({"status": h.COMPLETION_LABEL}, path)
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == h.COMPLETION_LABEL


# 20. second result write fails without changing first bytes
def test_result_write_once_second_fails(tmp_path) -> None:
    path = tmp_path / "confirmatory.json"
    h.write_result_once({"status": h.COMPLETION_LABEL, "v": 1}, path)
    first_bytes = path.read_bytes()
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        h.write_result_once({"status": "DIFFERENT"}, path)
    assert path.read_bytes() == first_bytes


# 21-31. identity repair proofs — normalization is representation-only


def test_int_key_vs_string_key_equivalent() -> None:
    live = {"mean": 41.0, "return_acf": {1: 0.9, 5: 0.8, 22: 0.4, 66: 0.2}}
    frozen = {"mean": 41.0, "return_acf": {"1": 0.9, "5": 0.8, "22": 0.4, "66": 0.2}}
    assert h.verify_frozen_target(live, frozen)["match"] is True


def test_nested_int_string_key_mismatch_passes_after_normalization() -> None:
    live = {
        "mean": 0.0,
        "quantiles": {"0.01": 1.0, "0.99": 2.0},
        "return_acf": {1: 0.1, 22: 0.2},
        "abs_return_acf": {1: 0.3},
        "sq_return_acf": {5: 0.4, 66: 0.5},
        "leverage_correlations": {22: 0.6},
    }
    frozen = {
        "mean": 0.0,
        "quantiles": {"0.01": 1.0, "0.99": 2.0},
        "return_acf": {"1": 0.1, "22": 0.2},
        "abs_return_acf": {"1": 0.3},
        "sq_return_acf": {"5": 0.4, "66": 0.5},
        "leverage_correlations": {"22": 0.6},
    }
    assert h.verify_frozen_target(live, frozen)["match"] is True


def test_numeric_mismatch_still_rejected() -> None:
    live = {"mean": 0.1, "return_acf": {1: 0.9, 5: 0.8, 22: 0.4, 66: 0.2}}
    frozen = {"mean": 0.2, "return_acf": {"1": 0.9, "5": 0.8, "22": 0.4, "66": 0.2}}
    with pytest.raises(RuntimeError, match="does not match"):
        h.verify_frozen_target(live, frozen)


def test_normalization_does_not_alter_numeric_values() -> None:
    live = {"return_acf": {1: 1e-9, 22: -2.5}}
    normalized = h._normalize_mapping_keys(live)
    assert normalized["return_acf"]["1"] == 1e-9
    assert normalized["return_acf"]["22"] == -2.5


def test_normalization_does_not_mutate_inputs() -> None:
    live = {"return_acf": {1: 0.9}}
    frozen = {"return_acf": {"1": 0.9}}
    live_keys = list(live["return_acf"].keys())
    frozen_keys = list(frozen["return_acf"].keys())
    h.verify_frozen_target(live, frozen)
    assert list(live["return_acf"].keys()) == live_keys  # still int
    assert list(frozen["return_acf"].keys()) == frozen_keys  # still str
    assert isinstance(live_keys[0], int)


def test_normalized_canonical_sha_is_deterministic() -> None:
    live = {"return_acf": {22: 0.4, 1: 0.9}}
    frozen = {"return_acf": {"22": 0.4, "1": 0.9}}
    a = h.verify_frozen_target(live, frozen)
    b = h.verify_frozen_target(live, frozen)
    assert a["recomputed_identity"] == b["recomputed_identity"]
    assert a["frozen_identity"] == b["frozen_identity"]


def test_mismatch_diagnostics_expose_hashes_and_path_not_values() -> None:
    live = {"mean": 0.0}
    frozen = {"mean": 1.0}
    with pytest.raises(RuntimeError) as exc_info:
        h.verify_frozen_target(live, frozen)
    message = str(exc_info.value)
    assert "recomputed=" in message
    assert "frozen=" in message
    assert "path=" in message
    assert "0.0" not in message and "1.0" not in message  # values never emitted


def test_json_round_trip_equivalent() -> None:
    live = h.recompute_validation_target(VAL_SERIES, MetricSpecification())
    frozen = json.loads(json.dumps(live))  # int keys -> str keys
    assert h.verify_frozen_target(live, frozen)["match"] is True


def test_nextafter_difference_still_rejected() -> None:
    spec = MetricSpecification()
    live = h.recompute_validation_target(VAL_SERIES, spec)
    payload = json.loads(json.dumps(live))
    mean_value = float(payload["mean"])
    payload["mean"] = float(np.nextafter(mean_value, mean_value + 1.0))
    with pytest.raises(RuntimeError):
        h.verify_frozen_target(live, payload)


def test_second_access_guard_unchanged_after_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))
    h.build_validation_series_once(inventory=object(), raw_root=Path("."), processed_root=Path("."))
    with pytest.raises(RuntimeError, match="one-shot"):
        h.build_validation_series_once(
            inventory=object(), raw_root=Path("."), processed_root=Path(".")
        )
    assert calls == ["validation"]


def test_target_mismatch_prevents_simulation(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))
    suite = _synthetic_suite()
    suite_path = tmp_path / "synthetic_suite.json"
    wrong_target = h.recompute_validation_target(VAL_SERIES, MetricSpecification())
    suite.metrics["validation_empirical"] = json.loads(json.dumps(wrong_target))
    suite.metrics["validation_empirical"]["mean"] = 999.0  # mutate value
    suite_payload = {
        "validation_series_sha256": VAL_SERIES.series_sha256,
        "metrics": suite.metrics,
        "discrepancies": {
            "training": suite.discrepancies["training"],
            "validation": suite.discrepancies["validation"],
        },
        "rankings": suite.rankings,
        "suite_hash": suite.suite_hash,
    }
    suite_path.write_text(json.dumps(suite_payload), encoding="utf-8")
    suite_ns = SimpleNamespace(
        metrics=suite.metrics,
        discrepancies=suite.discrepancies,
        rankings=suite.rankings,
        suite_hash=suite.suite_hash,
        metric_spec_hash=suite.metric_spec_hash,
        benchmark_hash=suite.benchmark_hash,
        validation_series_sha256=VAL_SERIES.series_sha256,
    )

    def fake_verify_identities(
        *, config_path, benchmark_path, suite_path, suite_hash, suite_file_sha256
    ):
        from neuralmarket.research.structured_vol_experiment import load_v5_config

        return (load_v5_config(config_path), {"benchmark_hash": "x"}, suite_ns)

    monkeypatch.setattr(h, "verify_contract_identities", fake_verify_identities)
    monkeypatch.setattr(h.ResearchInventory, "model_validate", lambda payload: payload)
    for p in ("inventory.json", "benchmark.json"):
        (tmp_path / p).write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        h.run(
            config_path=_V5_YAML,
            inventory_path=tmp_path / "inventory.json",
            benchmark_path=tmp_path / "benchmark.json",
            suite_path=suite_path,
            raw_root=tmp_path,
            processed_root=tmp_path,
            task_id="NM-R4-V5-EXTERNAL-VALIDATION-EXEC-SYNTHETIC-MISMATCH",
            result_path=tmp_path / "confirmatory.json",
        )
    path = tmp_path / "confirmatory.json"
    h.write_result_once({"status": h.COMPLETION_LABEL, "v": 1}, path)
    first_bytes = path.read_bytes()
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        h.write_result_once({"status": "DIFFERENT"}, path)
    assert path.read_bytes() == first_bytes


def _run_synthetic_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Full synthetic run(): fake series + suite + inventory, real frozen checkpoint."""
    calls: list[str] = []
    monkeypatch.setattr(h, "build_underlying_series", _fake_report_builder(calls))

    suite = _synthetic_suite()
    suite_path = tmp_path / "synthetic_suite.json"
    # The frozen validation target must be the actual recomputed synthetic payload
    # so run()'s byte-identity verification passes.
    frozen_target = h.recompute_validation_target(VAL_SERIES, MetricSpecification())
    suite.metrics["validation_empirical"] = frozen_target
    suite.discrepancies = _synthetic_discrepancies(np.random.default_rng(13))
    suite.discrepancies = {"training": suite.discrepancies, "validation": suite.discrepancies}
    suite_payload = {
        "validation_series_sha256": VAL_SERIES.series_sha256,
        "metrics": suite.metrics,
        "discrepancies": suite.discrepancies,
        "rankings": suite.rankings,
        "suite_hash": suite.suite_hash,
    }
    suite_path.write_text(json.dumps(suite_payload), encoding="utf-8")

    suite_ns = SimpleNamespace(
        metrics=suite.metrics,
        discrepancies=suite.discrepancies,
        rankings=suite.rankings,
        suite_hash=suite.suite_hash,
        metric_spec_hash=suite.metric_spec_hash,
        benchmark_hash=suite.benchmark_hash,
        validation_series_sha256=VAL_SERIES.series_sha256,
    )
    real_config_path = _V5_YAML

    def fake_verify_identities(
        *, config_path, benchmark_path, suite_path, suite_hash, suite_file_sha256
    ):
        from neuralmarket.research.structured_vol_experiment import load_v5_config

        return (load_v5_config(config_path), {"benchmark_hash": "x"}, suite_ns)

    monkeypatch.setattr(h, "verify_contract_identities", fake_verify_identities)
    monkeypatch.setattr(h.ResearchInventory, "model_validate", lambda payload: payload)

    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text("{}", encoding="utf-8")
    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text("{}", encoding="utf-8")
    result_path = tmp_path / "confirmatory.json"

    result = h.run(
        config_path=real_config_path,
        inventory_path=inventory_path,
        benchmark_path=benchmark_path,
        suite_path=suite_path,
        raw_root=tmp_path,
        processed_root=tmp_path,
        task_id="NM-R4-V5-EXTERNAL-VALIDATION-EXEC-SYNTHETIC",
        result_path=result_path,
    )
    assert result_path.exists()
    assert result["status"] == h.COMPLETION_LABEL
    assert result["governance"]["mode"] == "report_only"
    loaded = json.loads(result_path.read_text(encoding="utf-8"))
    assert loaded["status"] == h.COMPLETION_LABEL
    assert set(loaded) == set(result)
    return result
