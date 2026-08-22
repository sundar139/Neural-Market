"""Focused checks for the generalized frozen N=5 sensitivity helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PATH = (
    ROOT / "reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py"
)


def load_canonical():
    spec = importlib.util.spec_from_file_location("v5_runtime_sensitivity_test", CANONICAL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generalized_lomo_preserves_frozen_n5_dimensions_and_cv_exclusions():
    module = load_canonical()
    members = {
        member: {
            "scalars": {
                scalar: float(index + 1)
                for index, scalar in enumerate(module.SCALAR_ORDER)
            }
        }
        for member in ("seed-01", "seed-02", "seed-04", "seed-05", "reserve-j01")
    }
    order = list(members)

    full, lomo = module.compute_full_and_lomo(members, order_ids=order)

    assert list(full) == module.SCALAR_ORDER
    assert all(summary["N"] == 5 for summary in full.values())
    assert len(lomo) == 13
    assert all(list(omissions) == order for omissions in lomo.values())
    assert sum(len(omissions) for omissions in lomo.values()) == 65
    assert full["path_uniqueness_fraction"]["CV"] is None
    assert full["return_acf1_abs_diff"]["CV"] is None
    assert full["drift_diffusion_rms_ratio"]["CV"] is None
    assert full["initial_selection_total_loss"]["CV"] is not None
