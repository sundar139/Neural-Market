"""V5 primary adjudicator — deterministic evidence derivation for seed-02..05.

Consumes ONLY existing raw runner evidence (training_report.json gate_diagnostics).
Never trains, simulates, refits, Gate-evaluates, or accesses validation/external/final data.
All six criteria derive from recorded raw values with fail-closed numeric validation.
"""
from __future__ import annotations

import math
from typing import Any

# Frozen thresholds (Amendment 029 + task 041)
CRITERION_2_RANGE = (0.50, 2.00)
CRITERION_3_RANGE = (0.50, 2.00)
CRITERION_4_MIN = 0.99
CRITERION_5_MAX = 0.25
CRITERION_6_MAX = 0.50

# Required Gate diagnostic key mappings
GATE_KEYS = {
    "criterion_2": "variance_ratio",
    "criterion_3": "terminal_dispersion_ratio",
    "criterion_4": "path_uniqueness_fraction",
    "criterion_5": "return_acf1_abs_diff",
    "criterion_6": "drift_diffusion_rms_ratio",
}

# Forbidden placeholder values that must never be emitted
FORBIDDEN_VALUES = {"not_in_diagnostics", None, "null"}


def _is_finite_numeric(value: Any) -> bool:
    """Strict numeric check: int/float, not bool, finite."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _check_range(value: float, lo: float, hi: float) -> bool:
    return lo <= value <= hi


def evaluate_criteria(
    gate_diagnostics: dict[str, Any],
    initial_selection_total: Any,
    best_selection_total: Any,
) -> dict[str, Any]:
    """Evaluate all six criteria from raw gate_diagnostics.

    Fail-closed: any missing/malformed/non-finite value => that criterion fails.
    Never emits placeholder strings, nulls, or dummy zeros.
    """
    result: dict[str, Any] = {}
    all_pass = True

    # Criterion 1: best_selection_total < initial_selection_total
    c1_value_ok = _is_finite_numeric(initial_selection_total) and _is_finite_numeric(
        best_selection_total
    )
    if c1_value_ok:
        c1_pass = float(best_selection_total) < float(initial_selection_total)
    else:
        c1_pass = False
    result["criterion_1"] = {
        "metric": "best_selection_total < initial_selection_total",
        "initial_selection_total": float(initial_selection_total)
        if _is_finite_numeric(initial_selection_total)
        else initial_selection_total,
        "best_selection_total": float(best_selection_total)
        if _is_finite_numeric(best_selection_total)
        else best_selection_total,
        "operator": "<",
        "threshold": "best < initial",
        "value_ok": c1_value_ok,
        "pass": c1_pass,
    }
    if not c1_pass:
        all_pass = False
    # If values malformed, still fail closed already via c1_pass=False

    # Criteria 2-6 from gate_diagnostics
    criteria_spec = [
        ("criterion_2", "variance_ratio", CRITERION_2_RANGE, "range"),
        ("criterion_3", "terminal_dispersion_ratio", CRITERION_3_RANGE, "range"),
        ("criterion_4", "path_uniqueness_fraction", CRITERION_4_MIN, "ge"),
        ("criterion_5", "return_acf1_abs_diff", CRITERION_5_MAX, "le"),
        ("criterion_6", "drift_diffusion_rms_ratio", CRITERION_6_MAX, "le"),
    ]

    for crit_name, gate_key, threshold, op in criteria_spec:
        raw_value = gate_diagnostics.get(gate_key, "__MISSING__")
        # Fail-closed checks
        if raw_value == "__MISSING__":
            crit_pass = False
            value_ok = False
        elif raw_value in FORBIDDEN_VALUES:
            crit_pass = False
            value_ok = False
        elif not _is_finite_numeric(raw_value):
            crit_pass = False
            value_ok = False
        else:
            value_ok = True
            v = float(raw_value)
            if op == "range":
                lo, hi = threshold  # type: ignore
                crit_pass = _check_range(v, lo, hi)
            elif op == "ge":
                crit_pass = v >= float(threshold)
            elif op == "le":
                crit_pass = v <= float(threshold)
            else:
                crit_pass = False

        entry: dict[str, Any] = {
            "metric": gate_key,
            "gate_key": gate_key,
            "value": float(raw_value) if value_ok else raw_value,
            "value_ok": value_ok,
            "operator": op,
            "threshold": threshold,
            "pass": crit_pass,
        }
        # Attach human-readable threshold string
        if op == "range":
            entry["threshold_str"] = f"{threshold[0]:.2f} <= {gate_key} <= {threshold[1]:.2f}"  # type: ignore
        elif op == "ge":
            entry["threshold_str"] = f"{gate_key} >= {threshold}"
        else:
            entry["threshold_str"] = f"{gate_key} <= {threshold}"

        result[crit_name] = entry
        if not crit_pass:
            all_pass = False

    result["governed_six_criterion_pass"] = all_pass
    return result


def adjudicate_from_report(report: dict[str, Any]) -> dict[str, Any]:
    """Top-level adjudication from a loaded training_report.json dict.

    Extracts required fields and evaluates criteria.
    Does NOT access validation/external/final data.
    """
    gate_diagnostics = report.get("gate_diagnostics", {})
    if not isinstance(gate_diagnostics, dict):
        gate_diagnostics = {}

    initial = report.get("initial_selection_total")
    best = report.get("best_selection_total")

    criteria = evaluate_criteria(gate_diagnostics, initial, best)

    # Report-only Wasserstein must not affect pass
    wasserstein = gate_diagnostics.get("terminal_wasserstein_normalized")
    criteria["wasserstein_report_only"] = {
        "metric": "terminal_wasserstein_normalized",
        "value": wasserstein,
        "acceptance_role": "REPORT_ONLY",
    }

    return criteria
