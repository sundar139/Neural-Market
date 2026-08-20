"""Targeted adjudication tests for v5 primary adjudication helper.

No training, simulation, refit, Gate evaluation, validation, or final-test access.
All fixtures are raw gate diagnostics or synthetic dicts.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from reports.research.evidence.structured_vol_v5_primary_adjudicator import (
    _is_finite_numeric,
    adjudicate_from_report,
    evaluate_criteria,
)

REPO = Path(__file__).resolve().parents[2]
REPORT_PATH = (
    REPO / "reports/research/structured_vol_v5_replicates/62c7406cb3a2c642/training_report.json"
)
V2_PATH = REPO / "reports/research/structured_vol_v5_seed_02_primary_adjudication_v2.json"

# Frozen expected Gate values from raw evidence
EXPECTED = {
    "variance_ratio": 1.604621208120106,
    "terminal_dispersion_ratio": 1.7490240367051637,
    "path_uniqueness_fraction": 1.0,
    "return_acf1_abs_diff": 0.053962308505563134,
    "drift_diffusion_rms_ratio": 0.028829878414236947,
}


def _base_gate() -> dict:
    return {
        "variance_ratio": EXPECTED["variance_ratio"],
        "terminal_dispersion_ratio": EXPECTED["terminal_dispersion_ratio"],
        "path_uniqueness_fraction": EXPECTED["path_uniqueness_fraction"],
        "return_acf1_abs_diff": EXPECTED["return_acf1_abs_diff"],
        "drift_diffusion_rms_ratio": EXPECTED["drift_diffusion_rms_ratio"],
        "terminal_wasserstein_normalized": 0.6040767839981898,
    }


def _ok_totals():
    return (9.447866439819336, 0.6258251070976257)


# --- raw fixture exact values ---


def test_seed02_raw_fixture_produces_all_six_exact_values():
    report = json.loads(REPORT_PATH.read_text())
    result = adjudicate_from_report(report)
    assert result["criterion_2"]["value"] == EXPECTED["variance_ratio"]
    assert result["criterion_3"]["value"] == EXPECTED["terminal_dispersion_ratio"]
    assert result["criterion_4"]["value"] == EXPECTED["path_uniqueness_fraction"]
    assert result["criterion_5"]["value"] == EXPECTED["return_acf1_abs_diff"]
    assert result["criterion_6"]["value"] == EXPECTED["drift_diffusion_rms_ratio"]
    assert result["governed_six_criterion_pass"] is True
    # each criterion passes with correct thresholds
    assert result["criterion_1"]["pass"] is True
    for k in ("criterion_2", "criterion_3", "criterion_4", "criterion_5", "criterion_6"):
        assert result[k]["pass"] is True
        assert result[k]["value_ok"] is True


def test_criterion_1_calculation():
    init, best = _ok_totals()
    r = evaluate_criteria(_base_gate(), init, best)
    assert r["criterion_1"]["pass"] is True
    # failing direction
    r2 = evaluate_criteria(_base_gate(), 0.5, 1.0)
    assert r2["criterion_1"]["pass"] is False
    assert r2["governed_six_criterion_pass"] is False


def test_uniqueness_maps_from_path_uniqueness_fraction():
    init, best = _ok_totals()
    # correct key passes
    r = evaluate_criteria(_base_gate(), init, best)
    assert r["criterion_4"]["gate_key"] == "path_uniqueness_fraction"
    assert r["criterion_4"]["value"] == 1.0
    # old wrong key real_daily_variance must NOT satisfy criterion 4
    gd_wrong = dict(_base_gate())
    del gd_wrong["path_uniqueness_fraction"]
    gd_wrong["real_daily_variance"] = 6.28e-05  # placeholder from v1 defect
    r2 = evaluate_criteria(gd_wrong, init, best)
    assert r2["criterion_4"]["pass"] is False  # missing key fails closed


def test_acf1_maps_from_return_acf1_abs_diff():
    init, best = _ok_totals()
    r = evaluate_criteria(_base_gate(), init, best)
    assert r["criterion_5"]["gate_key"] == "return_acf1_abs_diff"
    assert r["criterion_5"]["value"] == EXPECTED["return_acf1_abs_diff"]
    # wrong key real_daily_variance must fail
    gd_wrong = dict(_base_gate())
    gd_wrong["return_acf1_abs_diff"] = 6.28e-05
    r2 = evaluate_criteria(gd_wrong, init, best)
    # value 6.28e-05 is <=0.25 so it would pass, but the point is the helper
    # reads return_acf1_abs_diff specifically. Remove it and only leave the wrong key:
    gd_missing = {k: v for k, v in _base_gate().items() if k != "return_acf1_abs_diff"}
    gd_missing["real_daily_variance"] = 6.28e-05
    r3 = evaluate_criteria(gd_missing, init, best)
    assert r3["criterion_5"]["pass"] is False


def test_drift_diffusion_maps_from_drift_diffusion_rms_ratio():
    init, best = _ok_totals()
    r = evaluate_criteria(_base_gate(), init, best)
    assert r["criterion_6"]["gate_key"] == "drift_diffusion_rms_ratio"
    assert r["criterion_6"]["value"] == EXPECTED["drift_diffusion_rms_ratio"]
    # wrong key gate_spec_hash must fail
    gd_missing = {k: v for k, v in _base_gate().items() if k != "drift_diffusion_rms_ratio"}
    gd_missing["gate_spec_hash"] = "f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469"
    r2 = evaluate_criteria(gd_missing, init, best)
    assert r2["criterion_6"]["pass"] is False


def test_missing_uniqueness_fails_closed():
    init, best = _ok_totals()
    gd = {k: v for k, v in _base_gate().items() if k != "path_uniqueness_fraction"}
    r = evaluate_criteria(gd, init, best)
    assert r["criterion_4"]["pass"] is False
    assert r["criterion_4"]["value_ok"] is False
    assert r["governed_six_criterion_pass"] is False


def test_missing_acf1_fails_closed():
    init, best = _ok_totals()
    gd = {k: v for k, v in _base_gate().items() if k != "return_acf1_abs_diff"}
    r = evaluate_criteria(gd, init, best)
    assert r["criterion_5"]["pass"] is False
    assert r["governed_six_criterion_pass"] is False


def test_missing_drift_diffusion_fails_closed():
    init, best = _ok_totals()
    gd = {k: v for k, v in _base_gate().items() if k != "drift_diffusion_rms_ratio"}
    r = evaluate_criteria(gd, init, best)
    assert r["criterion_6"]["pass"] is False
    assert r["governed_six_criterion_pass"] is False


def test_string_in_numeric_criterion_fails_closed():
    init, best = _ok_totals()
    for key in (
        "variance_ratio",
        "terminal_dispersion_ratio",
        "path_uniqueness_fraction",
        "return_acf1_abs_diff",
        "drift_diffusion_rms_ratio",
    ):
        gd = dict(_base_gate())
        gd[key] = "not_in_diagnostics"
        r = evaluate_criteria(gd, init, best)
        crit_map = {
            "variance_ratio": "criterion_2",
            "terminal_dispersion_ratio": "criterion_3",
            "path_uniqueness_fraction": "criterion_4",
            "return_acf1_abs_diff": "criterion_5",
            "drift_diffusion_rms_ratio": "criterion_6",
        }
        assert r[crit_map[key]]["pass"] is False, f"{key} string should fail closed"
        assert r["governed_six_criterion_pass"] is False


def test_nan_inf_fails_closed():
    init, best = _ok_totals()
    for bad in (float("nan"), float("inf"), float("-inf")):
        gd = dict(_base_gate())
        gd["variance_ratio"] = bad
        r = evaluate_criteria(gd, init, best)
        assert r["criterion_2"]["pass"] is False
        assert r["governed_six_criterion_pass"] is False
        # also test c1 with NaN
        r2 = evaluate_criteria(_base_gate(), bad, best)
        assert r2["criterion_1"]["pass"] is False


def test_bool_does_not_count_as_numeric():
    assert _is_finite_numeric(True) is False
    assert _is_finite_numeric(False) is False
    init, best = _ok_totals()
    gd = dict(_base_gate())
    gd["variance_ratio"] = True
    r = evaluate_criteria(gd, init, best)
    assert r["criterion_2"]["pass"] is False


def test_no_placeholder_value_can_be_emitted():
    init, best = _ok_totals()
    # Missing keys produce the raw missing marker, not a placeholder string
    gd: dict = {}
    r = evaluate_criteria(gd, init, best)
    for k in ("criterion_2", "criterion_3", "criterion_4", "criterion_5", "criterion_6"):
        val = r[k]["value"]
        assert val not in ("not_in_diagnostics", None), f"{k} emitted placeholder"
        assert r[k]["pass"] is False
    # Explicit placeholder value must fail, not be passed through as ok
    gd2 = dict(_base_gate())
    gd2["path_uniqueness_fraction"] = "not_in_diagnostics"
    r2 = evaluate_criteria(gd2, init, best)
    assert r2["criterion_4"]["pass"] is False


def test_final_epoch_comes_from_raw_final_epoch_not_best_epoch():
    report = json.loads(REPORT_PATH.read_text())
    assert report["best_epoch"] == 8
    assert report["final_epoch"] == 48
    v2 = json.loads(V2_PATH.read_text())
    assert v2["best_epoch"] == 8
    assert v2["final_epoch"] == 48
    assert v2["optimization"]["training_curve_last_epoch"] == 48
    assert v2["final_epoch"] != v2["best_epoch"]


def test_all_training_window_count_is_841():
    report = json.loads(REPORT_PATH.read_text())
    assert report["fit_window_count"] == 672
    assert report["selection_window_count"] == 107
    # 672 + 107 + 62 embargo = 841
    v2 = json.loads(V2_PATH.read_text())
    assert v2["all_training_window_count"] == 841
    assert v2["window_counts"]["all_training_derived_window_count"] == 841
    assert v2["window_counts"]["embargo_gap_windows"] == 62
    assert v2["fit_window_count"] == 672
    assert v2["selection_window_count"] == 107
    # 925 is returns, not windows
    assert v2["training_return_count"] == 925
    assert v2["training_session_count"] == 926
    assert v2["all_training_window_count"] != 925


def test_wasserstein_cannot_affect_pass():
    init, best = _ok_totals()
    gd = dict(_base_gate())
    # insanely bad Wasserstein should not affect governed pass
    gd["terminal_wasserstein_normalized"] = 999.0
    report = {"gate_diagnostics": gd, "initial_selection_total": init, "best_selection_total": best}
    r = adjudicate_from_report(report)  # type: ignore[arg-type]
    assert r["governed_six_criterion_pass"] is True
    assert r["wasserstein_report_only"]["acceptance_role"] == "REPORT_ONLY"
    # v2 top-level also marks it report-only
    v2 = json.loads(V2_PATH.read_text())
    assert v2["terminal_wasserstein"]["acceptance_role"] == "REPORT_ONLY"


def test_single_criterion_failure_makes_governed_false():
    init, best = _ok_totals()
    failing_cases = [
        ("variance_ratio", 99.0),
        ("terminal_dispersion_ratio", 99.0),
        ("path_uniqueness_fraction", 0.0),
        ("return_acf1_abs_diff", 1.0),
        ("drift_diffusion_rms_ratio", 0.99),
    ]
    crit_map = {
        "variance_ratio": "criterion_2",
        "terminal_dispersion_ratio": "criterion_3",
        "path_uniqueness_fraction": "criterion_4",
        "return_acf1_abs_diff": "criterion_5",
        "drift_diffusion_rms_ratio": "criterion_6",
    }
    for key, bad_val in failing_cases:
        gd = dict(_base_gate())
        gd[key] = bad_val
        r = evaluate_criteria(gd, init, best)
        assert r[crit_map[key]]["pass"] is False, f"{key} should fail at {bad_val}"
        assert r["governed_six_criterion_pass"] is False, f"governed should be False when {key} fails"
    # also criterion 1 failure
    r2 = evaluate_criteria(_base_gate(), 0.1, 999.0)
    assert r2["criterion_1"]["pass"] is False
    assert r2["governed_six_criterion_pass"] is False
