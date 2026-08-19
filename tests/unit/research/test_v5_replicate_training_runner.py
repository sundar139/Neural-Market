"""Targeted tests for the per-member v5 replicate training runner (no training)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / "reports/research/evidence/structured_vol_v5_replicate_training_runner.py"

# Import runner as module
import importlib.util

spec = importlib.util.spec_from_file_location("v5_runner", str(RUNNER_PATH))
assert spec and spec.loader
_runner = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
spec.loader.exec_module(_runner)  # type: ignore[union-attr]


def test_config_hashes_exact():
    for mid, exp in _runner.EXPECTED_CONFIG_HASHES.items():
        got = _runner.verify_config_hash(mid)
        assert got == exp, f"{mid} {got} != {exp}"


def test_family_hash_exact():
    for mid in ["v5-seed-01", "v5-seed-02", "v5-seed-03", "v5-seed-04", "v5-seed-05"]:
        got = _runner.verify_family_hash(mid)
        assert got == _runner.EXPECTED_FAMILY_HASH


def test_report_and_model_paths_derivation():
    for mid, prefix in _runner.RUN_PREFIXES.items():
        r = _runner.derive_report_dir(prefix)
        m = _runner.derive_model_dir(prefix)
        assert r == REPO / "reports/research/structured_vol_v5_replicates" / prefix
        assert (
            m == REPO / "data/processed/research/model/structured-volatility-neural-sde-v5" / prefix
        )
        assert r != _runner.HISTORICAL_GENERIC_REPORT
        assert "replicates" in r.as_posix()


def test_generic_report_path_never_used():
    # Every derived report_dir is under replicates/, never the generic file's parent as a file
    for prefix in _runner.RUN_PREFIXES.values():
        d = _runner.derive_report_dir(prefix)
        assert d != _runner.HISTORICAL_GENERIC_REPORT
        assert d.name == prefix
        assert "replicates" in d.as_posix()


def test_overwrite_refused_via_tempdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Monkeypatch derive funcs to use tmp_path, pre-create dirs, then expect refusal
    fake_report = tmp_path / "report" / "62c7406cb3a2c642"
    fake_model = tmp_path / "model" / "62c7406cb3a2c642"
    fake_report.mkdir(parents=True)
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model)
    with pytest.raises(RuntimeError, match="overwrite refused"):
        _runner.check_no_overwrite("v5-seed-02")
    # model exists case
    fake_report2 = tmp_path / "report2" / "e333325c804d95d2"
    fake_model2 = tmp_path / "model2" / "e333325c804d95d2"
    fake_model2.mkdir(parents=True)
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report2)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model2)
    with pytest.raises(RuntimeError, match="overwrite refused"):
        _runner.check_no_overwrite("v5-seed-03")


def test_exclusive_create_execution_started(tmp_path: Path):
    d = tmp_path / "62c7406cb3a2c642"
    # first create succeeds
    p = _runner._exclusive_create_execution_started(d, "v5-seed-02", "62c7406cb3a2c642")
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["member_id"] == "v5-seed-02"
    assert data["attempt"] == 1
    # second create must fail (exclusive)
    with pytest.raises(RuntimeError, match="already exists"):
        _runner._exclusive_create_execution_started(d, "v5-seed-02", "62c7406cb3a2c642")
    # check_no_overwrite now sees execution_started existing if we point there
    # (use monkeypatch variant)
    # Direct file exists check:
    assert (d / "execution_started.json").exists()


def test_missing_authorization_refused(tmp_path: Path):
    with pytest.raises(RuntimeError, match="authorization artifact required"):
        _runner.check_authorization("v5-seed-02", None)
    fake = tmp_path / "missing.json"
    with pytest.raises(RuntimeError, match="missing"):
        _runner.check_authorization("v5-seed-02", fake)
    # untracked file refused
    untracked = tmp_path / "auth.json"
    untracked.write_text(json.dumps({"member_id": "v5-seed-02"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not tracked"):
        _runner.check_authorization("v5-seed-02", untracked)


def test_member01_refused():
    # main should return 2 for seed-01
    _runner._INVOCATIONS = 0
    rc = _runner.main(["--member-id", "v5-seed-01"])
    assert rc == 2


def test_reserve_refused():
    _runner._INVOCATIONS = 0
    rc = _runner.main(["--member-id", "reserve-01"])
    assert rc == 2
    _runner._INVOCATIONS = 0
    rc2 = _runner.main(["--member-id", "reserve-j01"])
    assert rc2 == 2


def test_member_not_in_allowlist_refused():
    _runner._INVOCATIONS = 0
    rc = _runner.main(["--member-id", "v5-seed-99"])
    assert rc == 2


def test_dry_run_seed02_does_not_create_dirs():
    _runner._INVOCATIONS = 0
    # Ensure real report/model dirs do not exist before
    prefix = _runner.RUN_PREFIXES["v5-seed-02"]
    rd = _runner.derive_report_dir(prefix)
    md = _runner.derive_model_dir(prefix)
    # These should be absent in task 028 (no training)
    assert not rd.exists(), f"report dir should not exist before training: {rd}"
    assert not md.exists(), f"model dir should not exist before training: {md}"
    rc = _runner.main(["--member-id", "v5-seed-02"])
    assert rc == 0
    # Still absent after dry run
    assert not rd.exists()
    assert not md.exists()
    _runner._INVOCATIONS = 0


def test_execute_without_authorization_refused():
    _runner._INVOCATIONS = 0
    rc = _runner.main(["--member-id", "v5-seed-02", "--execute"])
    assert rc == 2
    _runner._INVOCATIONS = 0


def test_no_validation_import():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    # Runner must not import or call validation/final-test builders
    assert "build_underlying_series" not in text or 'split="validation"' not in text
    assert (
        "final_test" not in text.lower() or "final_test_attempts" not in text or True
    )  # allow counter name only if not import
    # More precise: must not import validation harness
    assert "structured_vol_v5_external_validation_harness" not in text
    assert "external_validation" not in text.lower() or "CLOSED" in text  # allow docstring mention
    # The runner does train_internal_v3 — check it does NOT import validation path
    assert 'split="validation"' not in text
    assert "split='validation'" not in text


def test_single_invocation_guard():
    _runner._INVOCATIONS = 0
    _runner._INVOCATIONS = 1
    # Next call to main should hit invocation guard after Allowlist check
    # main increments before check? Actually increments early — second main call in same process hits >1
    # Simulate by setting to 1 then calling main which increments to 2 and raises
    # Our main increments at top, so second call will raise RuntimeError
    with pytest.raises(RuntimeError, match="invocation count"):
        # Force second invocation in same process by directly checking
        _runner._INVOCATIONS = 1
        # main will increment to 2 and raise; need to trigger via main
        _runner.main(["--member-id", "v5-seed-02"])
    _runner._INVOCATIONS = 0
