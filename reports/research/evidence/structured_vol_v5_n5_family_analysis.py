"""Frozen N=5 family analysis from committed V5 member artifacts.

This driver reuses the historical N=4 sensitivity implementation for the exact
13-scalar order, summary statistics, CV meaningfulness, and LOMO formulas. It
performs no model import, simulation, Gate execution, training, validation, or
network access.
"""
# ruff: noqa: D103, E501
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any, cast

REPO = Path(__file__).resolve().parents[3]
EXPECTED_SOURCE_HEAD = "5491346d1845d6f7ac701e44f307139afa6a2400"
OUTPUT = REPO / "reports/research/structured_vol_v5_n5_family_analysis_v1.json"
CANONICAL_SCRIPT = REPO / "reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py"


def load_canonical() -> Any:
    spec = importlib.util.spec_from_file_location("v5_runtime_sensitivity", CANONICAL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load canonical analysis implementation: {CANONICAL_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CANONICAL = load_canonical()
SCALAR_ORDER = list(CANONICAL.SCALAR_ORDER)
ANALYSIS_ORDER = ["seed-01", "seed-02", "seed-04", "seed-05", "reserve-j01"]

VALUE_ARTIFACTS = {
    "seed-01": REPO / "reports/research/structured_vol_v5_production_gate_v2.json",
    "seed-02": REPO / "reports/research/structured_vol_v5_replicates/62c7406cb3a2c642/training_report.json",
    "seed-04": REPO / "reports/research/structured_vol_v5_replicates/77e7de9efabb7ce3/training_report.json",
    "seed-05": REPO / "reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_report.json",
    "reserve-j01": REPO / "reports/research/structured_vol_v5_replicates/38c5113b27568e14/training_report.json",
}
STATUS_ARTIFACTS = {
    "seed-01": VALUE_ARTIFACTS["seed-01"],
    "seed-02": REPO / "reports/research/structured_vol_v5_seed_02_primary_adjudication_v2.json",
    "seed-04": REPO / "reports/research/structured_vol_v5_seed_04_primary_adjudication_v2.json",
    "seed-05": REPO / "reports/research/structured_vol_v5_seed_05_primary_adjudication_v2.json",
    "reserve-j01": REPO / "reports/research/structured_vol_v5_reserve_j01_adjudication_v2.json",
}
SEED03_CLOSURE = REPO / "reports/research/structured_vol_v5_seed_03_primary_closure.json"


def load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def artifact_identity(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path), "git_blob": git_blob(path)}


def scalar_source(path: Path, fields: dict[str, str]) -> dict[str, Any]:
    return {"artifact": artifact_identity(path), "fields": fields}


def extract_seed01() -> tuple[dict[str, float | int], dict[str, Any]]:
    path = VALUE_ARTIFACTS["seed-01"]
    data = load(path)
    criteria = {item["name"]: item["value"] for item in data["gate"]["criteria"]}
    initial = data["training"]["initial_selection_total_loss"]
    best = data["training"]["best_selection_total_loss"]
    values = {
        "initial_selection_total_loss": initial,
        "best_selection_total_loss": best,
        "best_epoch": data["training"]["best_epoch"],
        "final_epoch": data["training"]["final_epoch"],
        "selection_loss_improvement_absolute": initial - best,
        "variance_ratio": criteria["variance_ratio"],
        "terminal_dispersion_ratio": criteria["terminal_dispersion_ratio"],
        "path_uniqueness_fraction": criteria["path_uniqueness"],
        "return_acf1_abs_diff": criteria["acf1_agreement"],
        "drift_diffusion_rms_ratio": criteria["drift_diffusion_rms_ratio"],
        "terminal_wasserstein_normalized": data["gate"]["report_only"]["terminal_wasserstein_normalized"],
        "acf_rmse": data["gate"]["report_only"]["acf_rmse"],
        "acf_max_error": data["gate"]["report_only"]["acf_max_error"],
    }
    fields = {
        "initial_selection_total_loss": "training.initial_selection_total_loss (equivalent to gate.criteria[id=1].initial_value)",
        "best_selection_total_loss": "training.best_selection_total_loss",
        "best_epoch": "training.best_epoch",
        "final_epoch": "training.final_epoch",
        "selection_loss_improvement_absolute": "training.initial_selection_total_loss - training.best_selection_total_loss",
        "variance_ratio": "gate.criteria[name=variance_ratio].value",
        "terminal_dispersion_ratio": "gate.criteria[name=terminal_dispersion_ratio].value",
        "path_uniqueness_fraction": "gate.criteria[name=path_uniqueness].value",
        "return_acf1_abs_diff": "gate.criteria[name=acf1_agreement].value",
        "drift_diffusion_rms_ratio": "gate.criteria[name=drift_diffusion_rms_ratio].value",
        "terminal_wasserstein_normalized": "gate.report_only.terminal_wasserstein_normalized",
        "acf_rmse": "gate.report_only.acf_rmse",
        "acf_max_error": "gate.report_only.acf_max_error",
    }
    if data["status"] != "INTERNAL_GATE_PASSED_FINAL_REFIT_FROZEN":
        raise ValueError("seed-01 committed production status is not the frozen passed status")
    if not data["gate"]["internal_gate_passed"]:
        raise ValueError("seed-01 internal Gate is not passed")
    return values, {"value_fields": scalar_source(path, fields), "raw_status": data["status"]}


def extract_replicate(member: str) -> tuple[dict[str, float | int], dict[str, Any]]:
    path = VALUE_ARTIFACTS[member]
    data = load(path)
    diagnostics = data["gate_diagnostics"]
    initial = data["initial_selection_total"]
    best = data["best_selection_total"]
    values = {
        "initial_selection_total_loss": initial,
        "best_selection_total_loss": best,
        "best_epoch": data["best_epoch"],
        "final_epoch": data["final_epoch"],
        "selection_loss_improvement_absolute": initial - best,
        "variance_ratio": diagnostics["variance_ratio"],
        "terminal_dispersion_ratio": diagnostics["terminal_dispersion_ratio"],
        "path_uniqueness_fraction": diagnostics["path_uniqueness_fraction"],
        "return_acf1_abs_diff": diagnostics["return_acf1_abs_diff"],
        "drift_diffusion_rms_ratio": diagnostics["drift_diffusion_rms_ratio"],
        "terminal_wasserstein_normalized": diagnostics["terminal_wasserstein_normalized"],
        "acf_rmse": diagnostics["acf_rmse"],
        "acf_max_error": diagnostics["acf_max_error"],
    }
    fields = {
        "initial_selection_total_loss": "initial_selection_total",
        "best_selection_total_loss": "best_selection_total",
        "best_epoch": "best_epoch",
        "final_epoch": "final_epoch",
        "selection_loss_improvement_absolute": "initial_selection_total - best_selection_total",
        "variance_ratio": "gate_diagnostics.variance_ratio",
        "terminal_dispersion_ratio": "gate_diagnostics.terminal_dispersion_ratio",
        "path_uniqueness_fraction": "gate_diagnostics.path_uniqueness_fraction",
        "return_acf1_abs_diff": "gate_diagnostics.return_acf1_abs_diff",
        "drift_diffusion_rms_ratio": "gate_diagnostics.drift_diffusion_rms_ratio",
        "terminal_wasserstein_normalized": "gate_diagnostics.terminal_wasserstein_normalized",
        "acf_rmse": "gate_diagnostics.acf_rmse",
        "acf_max_error": "gate_diagnostics.acf_max_error",
    }
    if not data["gate_passed"]:
        raise ValueError(f"{member} committed training report does not pass Gate")
    return values, {"value_fields": scalar_source(path, fields), "raw_gate_passed": data["gate_passed"]}


def extract_members() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    members: dict[str, dict[str, Any]] = {}
    source_details: dict[str, Any] = {}
    for member in ANALYSIS_ORDER:
        if member == "seed-01":
            values, details = extract_seed01()
        else:
            values, details = extract_replicate(member)
        if set(values) != set(SCALAR_ORDER):
            raise ValueError(f"{member} does not contain exactly the frozen 13 scalars")
        if not all(isinstance(value, int | float) and value == value and abs(float(value)) != float("inf") for value in values.values()):
            raise ValueError(f"{member} contains missing or non-finite frozen scalar")
        members[member] = {
            "member_id": member,
            "canonical_member_id": "v5-" + member if member != "reserve-j01" else "reserve-j01",
            "role": "reserve-contributed completed member" if member == "reserve-j01" else "primary",
            "runtime": "CUDA" if member in {"seed-05", "reserve-j01"} else "CPU",
            "scalars": values,
        }
        source_details[member] = details
    return members, source_details


def status_manifest(source_details: dict[str, Any]) -> dict[str, Any]:
    manifests: dict[str, Any] = {}
    raw_status = {
        "seed-01": "INTERNAL_GATE_PASSED_FINAL_REFIT_FROZEN",
        "seed-02": "PRIMARY_VALID_COMPLETED",
        "seed-04": "PRIMARY_VALID_COMPLETED",
        "seed-05": "PRIMARY_VALID_COMPLETED",
        "reserve-j01": "GATE_PASS_VALID",
    }
    normalization = {
        "seed-01": "Legacy frozen production-gate status plus internal_gate_passed=true maps to GATE_PASS_VALID under the Amendment-041 seed-01 mapping.",
        "seed-02": "PRIMARY_VALID_COMPLETED plus training_report.gate_passed=true maps to GATE_PASS_VALID.",
        "seed-04": "PRIMARY_VALID_COMPLETED plus training_report.gate_passed=true maps to GATE_PASS_VALID.",
        "seed-05": "PRIMARY_VALID_COMPLETED plus training_report.gate_passed=true maps to GATE_PASS_VALID.",
        "reserve-j01": "Committed adjudication governed_status is already GATE_PASS_VALID.",
    }
    for member in ANALYSIS_ORDER:
        status_path = STATUS_ARTIFACTS[member]
        manifests[member] = {
            "normalized_governed_status": "GATE_PASS_VALID",
            "raw_governed_status": raw_status[member],
            "status_normalization": normalization[member],
            "status_artifact": artifact_identity(status_path),
            "value_artifact": source_details[member]["value_fields"]["artifact"],
            "scalar_sources": source_details[member]["value_fields"]["fields"],
        }
    manifests["reserve-j01"]["required_identity"] = {
        "run_prefix": "38c5113b27568e14",
        "full_config_hash": "38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605",
        "adjudication_sha256": "50135d8a472ec45c167b3d8115305bc34874eaafe93623a9d703f7eda9013c32",
    }
    return manifests


def main() -> None:
    source_head = git_head()
    if source_head != EXPECTED_SOURCE_HEAD:
        raise RuntimeError(f"unexpected source HEAD: {source_head}")
    members, source_details = extract_members()
    if len(members) != 5 or len(SCALAR_ORDER) != 13 or len(members) * len(SCALAR_ORDER) != 65:
        raise RuntimeError("N5 input cardinality mismatch")

    seed03 = load(SEED03_CLOSURE)
    if seed03["governed_primary_status"] != "ATTEMPTED_FAILED_GOVERNANCE" or seed03["primary_family_admissible"] is not False:
        raise RuntimeError("seed-03 exclusion contract mismatch")

    full, lomo = CANONICAL.compute_full_and_lomo(
        members,
        order_ids=ANALYSIS_ORDER,
    )
    if len(full) != 13 or sum(len(entries) for entries in lomo.values()) != 65:
        raise RuntimeError("N5 output cardinality mismatch")

    raw_matrix = {member: members[member]["scalars"] for member in ANALYSIS_ORDER}
    result = {
        "schema_version": "structured-vol-v5-n5-family-analysis-v1",
        "task_id": "NM-R4-V5-N5-FAMILY-ANALYSIS-099",
        "source_head": source_head,
        "analysis_implementation": {
            "canonical_n4_script": artifact_identity(CANONICAL_SCRIPT),
            "n5_driver": {"path": Path(__file__).relative_to(REPO).as_posix(), "sha256": sha256(Path(__file__)), "git_blob": git_blob(Path(__file__))},
            "historical_n4_artifact": artifact_identity(REPO / "reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json"),
        },
        "frozen_contract": {
            "source_amendment": "reports/protocol/research_protocol_amendment_055.md §8",
            "amendments": [
                "reports/protocol/research_protocol_amendment_040.md",
                "reports/protocol/research_protocol_amendment_041.md",
                "reports/protocol/research_protocol_amendment_048.md",
                "reports/protocol/research_protocol_amendment_055.md",
                "reports/protocol/research_protocol_amendment_056.md",
            ],
            "scalar_order": SCALAR_ORDER,
            "scalar_count": 13,
            "training_scalars": SCALAR_ORDER[:5],
            "gate_scalars": SCALAR_ORDER[5:10],
            "report_only_scalars": SCALAR_ORDER[10:],
            "acf_lags": [1, 2, 3, 5, 10, 20],
            "rbf_excluded": ["initial_internal_rbf", "best_internal_rbf"],
            "summary_statistics": ["mean", "sample_sd", "median", "min", "max", "CV_when_meaningful"],
            "sample_sd": "statistics.stdev, ddof=1",
            "cv_rule": "CV = sample SD / mean only for nonzero ratio-scale means; omit for bounded path_uniqueness_fraction, near-zero return_acf1_abs_diff, and near-zero drift_diffusion_rms_ratio.",
            "lomo": "unconditional leave-one-member-out; absolute_change = LOMO_mean - full_mean; relative_change = absolute_change / |full_mean| only where meaningful",
            "historical_n4_immutable": True,
        },
        "family": {
            "included_members": ANALYSIS_ORDER,
            "member_roles": {member: members[member]["role"] for member in ANALYSIS_ORDER},
            "completed_model_N": 5,
            "gate_pass_count": 5,
            "excluded_seed-03": {
                "status": "GOVERNANCE_INVALID",
                "raw_status": seed03["governed_primary_status"],
                "protocol_violation": seed03["protocol_violation"],
                "numerical_inclusion": False,
                "retained_historically": True,
                "source_artifact": artifact_identity(SEED03_CLOSURE),
            },
            "five_seed_requirement": "SATISFIED",
        },
        "source_manifest": status_manifest(source_details),
        "canonical_member_table": members,
        "raw_scalar_matrix": {
            "member_order": ANALYSIS_ORDER,
            "scalar_order": SCALAR_ORDER,
            "member_count": len(ANALYSIS_ORDER),
            "scalar_count": len(SCALAR_ORDER),
            "expected_cells": 65,
            "populated_cells": sum(len(values) for values in raw_matrix.values()),
            "missing_nonfinite_cells": [],
            "values": raw_matrix,
        },
        "full_set_summaries": full,
        "cv_applicability": {
            scalar: {
                "applicable": full[scalar]["CV"] is not None,
                "CV": full[scalar]["CV"],
                "reason": full[scalar]["CV_omission_reason"],
            }
            for scalar in SCALAR_ORDER
        },
        "lomo": {
            "scalar_order": SCALAR_ORDER,
            "omitted_member_order": ANALYSIS_ORDER,
            "scalar_count": 13,
            "omission_count": 5,
            "expected_analyses": 65,
            "completed_analyses": sum(len(entries) for entries in lomo.values()),
            "conditional_omission": False,
            "values": lomo,
        },
        "runtime_heterogeneity": {
            "cpu_members": ["seed-01", "seed-02", "seed-04"],
            "cpu_N": 3,
            "cuda_members": ["seed-05", "reserve-j01"],
            "cuda_N": 2,
            "runtime_labels": {member: members[member]["runtime"] for member in ANALYSIS_ORDER},
            "disclosure_only": True,
            "no_causal_backend_estimate": True,
            "no_cpu_cuda_significance_test": True,
            "no_seed_only_attribution": True,
            "limitation": "runtime/backend heterogeneity is a limitation and source of variation; backend is a labelled execution covariate, not a causal explanation.",
        },
        "claim_restrictions": {
            "no_new_threshold": True,
            "no_composite_score": True,
            "no_ranks": True,
            "no_weighted_means": True,
            "no_effect_sizes": True,
            "no_hardware_equivalence_claim": True,
            "h2": "UNRESOLVED_PENDING_WGAN_COMPARATOR",
            "final_test": "SEALED",
        },
        "missingness": {"missing_frozen_scalars": [], "nonfinite_frozen_scalars": [], "imputation_performed": False},
        "calculation_identity": {
            "mean": "statistics.mean",
            "sample_sd": "statistics.stdev (ddof=1)",
            "median": "statistics.median",
            "lomo_absolute": "LOMO_mean - full_mean",
            "lomo_relative": "absolute_change / |full_mean| when meaningful; omitted under frozen CV meaningfulness exclusions",
            "epoch_treatment": "numeric treatment preserved from historical N=4 implementation",
        },
        "verification": {
            "input_matrix": "5 members x 13 scalars = 65 finite cells",
            "summary_rows": len(full),
            "lomo_groups": len(lomo),
            "lomo_cells": sum(len(entries) for entries in lomo.values()),
            "no_gate_rerun": True,
            "no_scientific_execution": True,
            "no_network": True,
        },
        "analysis_timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)} scalar_count=13 members=5 raw_cells=65 summaries=13 lomo=65")


if __name__ == "__main__":
    main()
