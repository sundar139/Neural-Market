"""Verification of the frozen v5 reproducibility replay harness (NM-R4-V5-PRODUCTION-RERUN-008).

The harness at reports/research/evidence/structured_vol_v5_reproducibility_harness.py
is a committed, one-shot execution recipe. It must NEVER be executed by a test
(a run is a scientific replay). This module statically verifies the frozen
harness: it dry-loads it with main() guarded, pins its frozen identity
invariants, and asserts the fail-closed validation boundary is present and that
no external-validation/final-test code paths exist in its executable source.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_HARNESS = _REPO / "reports/research/evidence/structured_vol_v5_reproducibility_harness.py"

# Expected frozen scientific identities (content, not secrets).
_EXPECTED_CONFIG_HASH = (
    "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157"  # pragma: allowlist secret
)
_EXPECTED_GATE_YAML_SHA = (
    "8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625"  # pragma: allowlist secret
)
_EXPECTED_GATE_SPEC_HASH = (
    "f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469"  # pragma: allowlist secret
)
_EXPECTED_INVENTORY_HASH = (
    "371c148315f2b7887f6e173587662f8ad31132bc6935e45a99cb9d0d4e76d119"  # pragma: allowlist secret
)
_EXPECTED_TRAINING_SERIES_SHA = (
    "4863b2cc63a09ffb03bbe455c7859c46b521b6f7bef8212e0e3876ac8488669c"  # pragma: allowlist secret
)

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="module")
def harness() -> object:
    """Dry-load the frozen harness module (main() is __main__-guarded)."""
    spec = importlib.util.spec_from_file_location("replay_harness", _HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.mark.unit
def test_harness_dry_loads_and_main_is_guarded(harness: object) -> None:
    """Import must not execute the replay, and main must be __main__ guarded."""
    source = _HARNESS.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in source
    assert hasattr(harness, "main")


@pytest.mark.unit
def test_frozen_identity_invariants(harness: object) -> None:
    """Pinned frozen scientific identities must be present and correct."""
    assert harness._EXPECTED_CONFIG_HASH == _EXPECTED_CONFIG_HASH
    assert harness._EXPECTED_GATE_YAML_SHA == _EXPECTED_GATE_YAML_SHA
    assert harness._EXPECTED_GATE_SPEC_HASH == _EXPECTED_GATE_SPEC_HASH
    assert harness._EXPECTED_INVENTORY_HASH == _EXPECTED_INVENTORY_HASH
    assert harness._EXPECTED_TRAINING_SERIES_SHA == _EXPECTED_TRAINING_SERIES_SHA


@pytest.mark.unit
def test_replay_output_root_is_ignored_temp_path(harness: object) -> None:
    """Replay artifacts must go only into the temporary, gitignored output root."""
    root = harness.REPLAY_OUTPUT_ROOT
    relative = str(root.relative_to(_REPO)).replace("\\", "/")
    assert relative == ".agent-memory/evidence/NM-R4-V5-PRODUCTION-RERUN-008/output"
    assert str(harness.CANONICAL_DIR).endswith("5bdbaabd2fb257a7")


@pytest.mark.unit
def test_fail_closed_validation_boundary_is_present(harness: object) -> None:
    """The guarded underlying-series boundary must raise on non-training splits."""
    source = _HARNESS.read_text(encoding="utf-8")
    assert "validation split requested; replay boundary is fail-closed" in source
    assert "unexpected split requested" in source


@pytest.mark.unit
def test_no_external_validation_or_final_test_code_paths(harness: object) -> None:
    """Executable source must never reference validator/scorecard/final-test code."""
    source = _HARNESS.read_text(encoding="utf-8")
    for forbidden in (
        "compute_scorecard",
        "_scorecard_payload",
        "build_validation_identity",
        "simulate_structured",
        "final_test_loader",
    ):
        assert forbidden not in source, f"forbidden symbol present: {forbidden}"
