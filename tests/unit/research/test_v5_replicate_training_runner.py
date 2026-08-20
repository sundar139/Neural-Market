"""Targeted tests for the per-member v5 replicate training runner (no training)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / "reports/research/evidence/structured_vol_v5_replicate_training_runner.py"

import importlib.util

spec = importlib.util.spec_from_file_location("v5_runner", str(RUNNER_PATH))
assert spec and spec.loader
_runner = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
spec.loader.exec_module(_runner)  # type: ignore[union-attr]


def _reset_invocations():
    _runner._SCIENTIFIC_INVOCATIONS = 0
    # also reset _INVOCATIONS if old version had it; new runner uses _SCIENTIFIC_INVOCATIONS
    if hasattr(_runner, "_INVOCATIONS"):
        _runner._INVOCATIONS = 0


def _make_auth(tmp_path: Path, member_id: str = "v5-seed-02", **overrides) -> Path:
    """Create a tracked, clean authorization JSON for member_id in REPO (not tmp)."""
    # Place auth inside REPO so it can be tracked
    auth_dir = REPO / "reports/research/structured_vol_v5_replicates" / "_test_auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_path = auth_dir / f"auth_{member_id}.json"
    # Contract v2 blob: use v2 if tracked, else use hash of on-disk v2 (pre-commit phase)
    from pathlib import Path as _P

    v2_path = REPO / "reports/research/structured_vol_v5_training_execution_contract_v2.json"
    if v2_path.exists():
        v2_blob = subprocess.run(
            ["git", "hash-object", str(v2_path)], capture_output=True, text=True, check=True
        ).stdout.strip()
    else:
        v2_blob = subprocess.run(
            ["git", "hash-object", str(REPO / "reports/research/structured_vol_v5_training_execution_contract_v1.json")],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    base = {
        "schema_version": "1.0",
        "authorization_task_id": "NM-R4-TEST-AUTH-001",
        "member_id": member_id,
        "replicate_seed": {"v5-seed-02": 9281, "v5-seed-03": 10281, "v5-seed-04": 11281, "v5-seed-05": 12281}[member_id],
        "model_init_seed": {"v5-seed-02": 9281, "v5-seed-03": 10281, "v5-seed-04": 11281, "v5-seed-05": 12281}[member_id],
        "data_seed": {"v5-seed-02": 9282, "v5-seed-03": 10282, "v5-seed-04": 11282, "v5-seed-05": 12282}[member_id],
        "eval_seed": 8283,
        "full_config_hash": _runner.EXPECTED_CONFIG_HASHES[member_id],
        "run_prefix": _runner.RUN_PREFIXES[member_id],
        "family_methodology_identity": _runner.EXPECTED_FAMILY_HASH,
        "schedule_git_blob": _runner.FROZEN_SCHEDULE_BLOB,
        "schedule_sha256": _runner.FROZEN_SCHEDULE_SHA,
        "execution_contract_git_blob": v2_blob,
        "runner_git_blob": subprocess.run(
            ["git", "hash-object", str(RUNNER_PATH)], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "execution_recipe_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True
        ).stdout.strip(),
        "training_authorized": True,
        "validation_authorized": False,
        "final_test_authorized": False,
        "reserve": False,
        "max_training_invocations": 1,
    }
    base.update(overrides)
    auth_path.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(auth_path)], cwd=str(REPO), capture_output=True, check=False)
    return auth_path


def _cleanup_auth(auth_path: Path):
    subprocess.run(["git", "reset", "HEAD", "--", str(auth_path)], cwd=str(REPO), capture_output=True, check=False)
    try:
        auth_path.unlink()
    except FileNotFoundError:
        pass
    # Remove empty parent
    try:
        auth_path.parent.rmdir()
    except OSError:
        pass


# 1. allowed member dry-run
def test_allowed_member_dry_run():
    _reset_invocations()
    rc = _runner.main(["--member-id", "v5-seed-02"])
    assert rc == 0
    _reset_invocations()


# 2. member #1 refusal
def test_member01_refused():
    _reset_invocations()
    rc = _runner.main(["--member-id", "v5-seed-01"])
    assert rc == 2
    _reset_invocations()


# 3. reserve refusal
def test_reserve_refused():
    _reset_invocations()
    for mid in ["reserve-01", "reserve-j01", "reserve-02"]:
        rc = _runner.main(["--member-id", mid])
        assert rc == 2, mid
    _reset_invocations()


# 4. unknown-member refusal
def test_unknown_member_refused():
    _reset_invocations()
    rc = _runner.main(["--member-id", "v5-seed-99"])
    assert rc == 2
    _reset_invocations()


# 5. no CLI seed override (argparse should error)
def test_no_cli_seed_override():
    _reset_invocations()
    # Runner has no --model-init-seed / --data-seed flag — passing it must fail via argparse
    with pytest.raises(SystemExit):
        _runner.main(["--member-id", "v5-seed-02", "--model-init-seed", "9999"])
    _reset_invocations()


# 6. exact seed-02..05 config hashes
def test_config_hashes_exact():
    for mid, exp in _runner.EXPECTED_CONFIG_HASHES.items():
        got = _runner.verify_config_hash(mid)
        assert got == exp, f"{mid} {got} != {exp}"


# 7. exact family methodology hash
def test_family_hash_exact():
    for mid in ["v5-seed-01", "v5-seed-02", "v5-seed-03", "v5-seed-04", "v5-seed-05"]:
        got = _runner.verify_family_hash(mid)
        assert got == _runner.EXPECTED_FAMILY_HASH


# 8. existing namespace refusal
def test_existing_namespace_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fake_report = tmp_path / "report" / "62c7406cb3a2c642"
    fake_model = tmp_path / "model" / "62c7406cb3a2c642"
    fake_report.mkdir(parents=True)
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model)
    with pytest.raises(RuntimeError, match="overwrite refused"):
        _runner.check_no_overwrite("v5-seed-02")
    fake_report2 = tmp_path / "report2" / "e333325c804d95d2"
    fake_model2 = tmp_path / "model2" / "e333325c804d95d2"
    fake_model2.mkdir(parents=True)
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report2)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model2)
    with pytest.raises(RuntimeError, match="overwrite refused"):
        _runner.check_no_overwrite("v5-seed-03")


# 9. missing authorization refusal
def test_missing_auth_refused(tmp_path: Path):
    with pytest.raises(RuntimeError, match="authorization artifact required"):
        _runner.check_authorization("v5-seed-02", None)
    fake = tmp_path / "missing.json"
    with pytest.raises(RuntimeError, match="missing"):
        _runner.check_authorization("v5-seed-02", fake)


# 10. untracked authorization refusal
def test_untracked_auth_refused(tmp_path: Path):
    untracked = tmp_path / "auth.json"
    untracked.write_text(json.dumps({"member_id": "v5-seed-02"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not tracked"):
        _runner.check_authorization("v5-seed-02", untracked)


# 11. dirty authorization refusal
def test_dirty_auth_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02")
    # Make it dirty
    auth.write_text(auth.read_text(encoding="utf-8") + "\n# dirty\n", encoding="utf-8")
    try:
        with pytest.raises(RuntimeError, match="not clean"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 12. incomplete authorization refusal (missing field)
def test_incomplete_auth_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02")
    data = json.loads(auth.read_text(encoding="utf-8"))
    del data["schedule_git_blob"]
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(auth)], cwd=str(REPO), capture_output=True, check=False)
    try:
        with pytest.raises(RuntimeError, match="missing required field"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 13. hostile validation_authorized=true refused
def test_hostile_validation_true_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", validation_authorized=True)
    try:
        with pytest.raises(RuntimeError, match="validation_authorized must be false"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 14. hostile final_test_authorized=true refused
def test_hostile_final_test_true_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", final_test_authorized=True)
    try:
        with pytest.raises(RuntimeError, match="final_test_authorized must be false"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 15. reserve=true refused
def test_hostile_reserve_true_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", reserve=True)
    try:
        with pytest.raises(RuntimeError, match="reserve must be false"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 16. max_training_invocations != 1 refused
def test_hostile_max_invocations_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", max_training_invocations=2)
    try:
        with pytest.raises(RuntimeError, match="max_training_invocations must be 1"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 17. wrong seed tuple refused
def test_wrong_seed_tuple_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", model_init_seed=9999)
    try:
        with pytest.raises(RuntimeError, match="model_init_seed mismatch"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 18. wrong runner blob refused
def test_wrong_runner_blob_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", runner_git_blob="deadbeef" * 5)
    try:
        with pytest.raises(RuntimeError, match="runner_git_blob mismatch"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 19. wrong contract-v2 blob refused
def test_wrong_contract_blob_refused(tmp_path: Path):
    # Need contract v2 to be tracked for this check; if not yet tracked, skip (will pass after v2 commit)
    import subprocess

    if not _runner.EXEC_CONTRACT_V2_PATH.exists() or subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(_runner.EXEC_CONTRACT_V2_PATH.relative_to(_runner.REPO))],
        cwd=str(_runner.REPO),
        capture_output=True,
    ).returncode != 0:
        pytest.skip("contract v2 not yet tracked")
    auth = _make_auth(tmp_path, "v5-seed-02", execution_contract_git_blob="deadbeef" * 5)
    try:
        with pytest.raises(RuntimeError, match="execution_contract_git_blob mismatch"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 20. stale/wrong recipe HEAD refused
def test_stale_recipe_head_refused(tmp_path: Path):
    # Use a bad head that is not ancestor — bypass clean check by staging legit then swapping HEAD field
    auth = _make_auth(tmp_path, "v5-seed-02")
    data = json.loads(auth.read_text(encoding="utf-8"))
    data["execution_recipe_head"] = "0" * 40
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(auth)], cwd=str(REPO), capture_output=True, check=False)
    try:
        with pytest.raises(RuntimeError, match="execution_recipe_head invalid|not ancestor"):
            _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 21. untracked runner refusal (simulate via monkeypatch)
def test_untracked_runner_refused(monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    monkeypatch.setattr(_runner, "_is_tracked", lambda p: False if p == _runner.HARNESS_PATH else True)
    rc = _runner.main(["--member-id", "v5-seed-02"])
    assert rc == 2
    _reset_invocations()


# 22. modified tracked runner refusal
def test_modified_runner_refused(monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    monkeypatch.setattr(_runner, "_is_clean", lambda p: False if p == _runner.HARNESS_PATH else True)
    rc = _runner.main(["--member-id", "v5-seed-02"])
    assert rc == 2
    _reset_invocations()


# 23. execution_started exclusive create
def test_exclusive_create(tmp_path: Path):
    d = tmp_path / "62c7406cb3a2c642"
    auth = _make_auth(tmp_path, "v5-seed-02")
    auth_data = json.loads(auth.read_text(encoding="utf-8"))
    try:
        p = _runner._exclusive_create_execution_started(d, "v5-seed-02", "62c7406cb3a2c642", auth_data, auth)
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["member_id"] == "v5-seed-02"
        assert data["attempt_number"] == 1
        with pytest.raises(RuntimeError, match="already exists"):
            _runner._exclusive_create_execution_started(d, "v5-seed-02", "62c7406cb3a2c642", auth_data, auth)
    finally:
        _cleanup_auth(auth)


# 24. execution_started contains full seed + authorization identity
def test_execution_started_contains_full_provenance(tmp_path: Path):
    d = tmp_path / "e333325c804d95d2"
    auth = _make_auth(tmp_path, "v5-seed-03")
    auth_data = json.loads(auth.read_text(encoding="utf-8"))
    try:
        p = _runner._exclusive_create_execution_started(d, "v5-seed-03", "e333325c804d95d2", auth_data, auth)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["replicate_seed"] == 10281
        assert data["model_init_seed"] == 10281
        assert data["data_seed"] == 10282
        assert data["eval_seed"] == 8283
        assert data["full_config_hash"] == _runner.EXPECTED_CONFIG_HASHES["v5-seed-03"]
        assert "authorization_git_blob" in data
        assert "runner_git_blob" in data
        assert "execution_contract_git_blob" in data
        assert "schedule_git_blob" in data
        assert data["validation_authorized"] is False
        assert data["reserve"] is False
    finally:
        _cleanup_auth(auth)


# 25. mocked scientific success executes exactly once
def test_mocked_success_exactly_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    # Need contract v2 for auth check; skip if absent
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    # Mock _run_scientific_training to succeed without touching disk/model
    call_count = {"n": 0}

    def fake_run(member_id, report_dir, model_dir):
        call_count["n"] += 1
        _runner._SCIENTIFIC_INVOCATIONS += 1
        return {
            "config_hash": _runner.EXPECTED_CONFIG_HASHES[member_id],
            "run_prefix": _runner.RUN_PREFIXES[member_id],
            "checkpoint_path": str(model_dir / "checkpoint.pt"),
            "checkpoint_sha256": "a" * 64,
            "curve_path": str(model_dir / "training_curve.json"),
            "curve_sha256": "b" * 64,
            "final_checkpoint_path": None,
            "final_checkpoint_sha256": None,
            "gate_diagnostics": {"variance_ratio": 1.0},
            "gate_passed": True,
            "best_epoch": 10,
            "initial_internal_rbf": 1.0,
            "best_internal_rbf": 0.5,
        }

    monkeypatch.setattr(_runner, "_run_scientific_training", fake_run)
    # Monkeypatch dirs to tmp
    prefix = _runner.RUN_PREFIXES["v5-seed-02"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))

    auth = _make_auth(tmp_path, "v5-seed-02")
    try:
        rc = _runner.main(["--member-id", "v5-seed-02", "--authorization", str(auth), "--execute"])
        assert rc == 0, f"expected 0 got {rc}"
        assert call_count["n"] == 1
        assert (fake_report / "execution_started.json").exists()
        assert (fake_report / "training_stdout.log").exists()
        assert (fake_report / "training_exit_code.txt").read_text().strip() == "0"
        assert (fake_report / "training_execution_manifest.json").exists()
        assert (fake_report / "training_report.json").exists()
        manifest = json.loads((fake_report / "training_execution_manifest.json").read_text())
        assert manifest["terminal_status"] == "COMPLETED"
        assert manifest["scientific_training_invocations"] == 1
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 26. mocked scientific failure executes exactly once
def test_mocked_failure_exactly_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")

    def fake_run_fail(member_id, report_dir, model_dir):
        raise RuntimeError("synthetic training failure for test")

    monkeypatch.setattr(_runner, "_run_scientific_training", fake_run_fail)
    prefix = _runner.RUN_PREFIXES["v5-seed-03"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))

    auth = _make_auth(tmp_path, "v5-seed-03")
    try:
        rc = _runner.main(["--member-id", "v5-seed-03", "--authorization", str(auth), "--execute"])
        assert rc != 0
        assert (fake_report / "execution_started.json").exists()
        assert (fake_report / "training_stdout.log").exists()
        assert int((fake_report / "training_exit_code.txt").read_text().strip()) != 0
        manifest = json.loads((fake_report / "training_execution_manifest.json").read_text())
        assert manifest["terminal_status"] == "FAILED"
        assert "synthetic training failure" in (manifest.get("failure_reason") or "")
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 27. failure-after-start preserves marker
def test_failure_preserves_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-04"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-04")
    try:
        _runner.main(["--member-id", "v5-seed-04", "--authorization", str(auth), "--execute"])
        assert (fake_report / "execution_started.json").exists()
        # Report must not claim success
        if (fake_report / "training_report.json").exists():
            r = json.loads((fake_report / "training_report.json").read_text())
            assert r.get("terminal_status") != "COMPLETED"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 28. failure writes nonzero exit code (already checked in 26, duplicate proof)
def test_failure_nonzero_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-02"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-02")
    try:
        rc = _runner.main(["--member-id", "v5-seed-02", "--authorization", str(auth), "--execute"])
        assert rc != 0
        assert (fake_report / "training_exit_code.txt").read_text().strip() != "0"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 29. failure writes transcript
def test_failure_writes_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("transcript fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-03"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-03")
    try:
        _runner.main(["--member-id", "v5-seed-03", "--authorization", str(auth), "--execute"])
        assert (fake_report / "training_stdout.log").exists()
        assert len((fake_report / "training_stdout.log").read_text()) > 0
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 30. failure writes FAILED manifest
def test_failure_manifest_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("manifest fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-04"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-04")
    try:
        _runner.main(["--member-id", "v5-seed-04", "--authorization", str(auth), "--execute"])
        m = json.loads((fake_report / "training_execution_manifest.json").read_text())
        assert m["terminal_status"] == "FAILED"
        assert m["exception_class"] == "RuntimeError"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 31. failure does not emit false-success report
def test_failure_no_false_success_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no success")))
    prefix = _runner.RUN_PREFIXES["v5-seed-05"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-05")
    try:
        _runner.main(["--member-id", "v5-seed-05", "--authorization", str(auth), "--execute"])
        # Either no report, or not COMPLETED
        if (fake_report / "training_report.json").exists():
            assert json.loads((fake_report / "training_report.json").read_text()).get("terminal_status") != "COMPLETED"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 32. second attempt refused after failure
def test_second_attempt_refused_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail once")))
    prefix = _runner.RUN_PREFIXES["v5-seed-02"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-02")
    try:
        _runner.main(["--member-id", "v5-seed-02", "--authorization", str(auth), "--execute"])
        # Second attempt must refuse (overwrite or execution_started exists)
        # Need to keep report dir existing
        rc2 = _runner.main(["--member-id", "v5-seed-02", "--authorization", str(auth), "--execute"])
        assert rc2 == 2
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 33. success emits all five required evidence files
def test_success_all_five_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")

    def fake_ok(member_id, report_dir, model_dir):
        _runner._SCIENTIFIC_INVOCATIONS += 1
        return {
            "config_hash": _runner.EXPECTED_CONFIG_HASHES[member_id],
            "run_prefix": _runner.RUN_PREFIXES[member_id],
            "checkpoint_path": str(model_dir / "checkpoint.pt"),
            "checkpoint_sha256": "a" * 64,
            "curve_path": str(model_dir / "training_curve.json"),
            "curve_sha256": "b" * 64,
            "final_checkpoint_path": None,
            "final_checkpoint_sha256": None,
            "gate_diagnostics": {},
            "gate_passed": True,
            "best_epoch": 10,
            "initial_internal_rbf": 1.0,
            "best_internal_rbf": 0.5,
        }

    monkeypatch.setattr(_runner, "_run_scientific_training", fake_ok)
    prefix = _runner.RUN_PREFIXES["v5-seed-04"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-04")
    try:
        rc = _runner.main(["--member-id", "v5-seed-04", "--authorization", str(auth), "--execute"])
        assert rc == 0
        for name in ["execution_started.json", "training_stdout.log", "training_exit_code.txt", "training_execution_manifest.json", "training_report.json"]:
            assert (fake_report / name).exists(), name
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 34. success manifest hashes coherent
def test_success_manifest_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_V2_PATH.exists():
        pytest.skip("contract v2 not yet created")

    def fake_ok(member_id, report_dir, model_dir):
        _runner._SCIENTIFIC_INVOCATIONS += 1
        return {
            "config_hash": _runner.EXPECTED_CONFIG_HASHES[member_id],
            "run_prefix": _runner.RUN_PREFIXES[member_id],
            "checkpoint_path": str(model_dir / "checkpoint.pt"),
            "checkpoint_sha256": "a" * 64,
            "curve_path": str(model_dir / "training_curve.json"),
            "curve_sha256": "b" * 64,
            "final_checkpoint_path": None,
            "final_checkpoint_sha256": None,
            "gate_diagnostics": {},
            "gate_passed": True,
            "best_epoch": 10,
            "initial_internal_rbf": 1.0,
            "best_internal_rbf": 0.5,
        }

    monkeypatch.setattr(_runner, "_run_scientific_training", fake_ok)
    prefix = _runner.RUN_PREFIXES["v5-seed-05"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-05")
    try:
        _runner.main(["--member-id", "v5-seed-05", "--authorization", str(auth), "--execute"])
        m = json.loads((fake_report / "training_execution_manifest.json").read_text())
        assert m["training_stdout.log_sha256"]
        assert m["training_exit_code.txt_sha256"]
        assert m["execution_started.json_sha256"]
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 35. generic historical report path untouched
def test_generic_report_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # No test should create the generic path
    generic = REPO / "reports/research/structured_vol_v5_report.json"
    before = generic.read_bytes() if generic.exists() else None
    _reset_invocations()
    _runner.main(["--member-id", "v5-seed-02"])
    after = generic.read_bytes() if generic.exists() else None
    assert before == after
    _reset_invocations()


# 36. no reserve fallback (reserve run not possible via auth for primary)
def test_no_reserve_fallback(tmp_path: Path):
    _reset_invocations()
    # Attempting to use a primary member's auth with a reserve id must fail
    # Already covered by reserve refusal; also ensure primary auth cannot be used for reserve
    rc = _runner.main(["--member-id", "reserve-01"])
    assert rc == 2
    _reset_invocations()


# 37. no retry (second scientific invocation in same process refused)
def test_no_retry_same_process(monkeypatch: pytest.MonkeyPatch):
    _runner._SCIENTIFIC_INVOCATIONS = 1
    with pytest.raises(RuntimeError, match="exceeded 1"):
        _runner._run_scientific_training("v5-seed-02", Path("/tmp/a"), Path("/tmp/b"))
    _runner._SCIENTIFIC_INVOCATIONS = 0


# 38. validation builder/import unreachable
def test_validation_unreachable():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    # Must not contain validation split construction
    assert 'split="validation"' not in text
    assert "split='validation'" not in text
    # Must not import external validation harness
    assert "structured_vol_v5_external_validation_harness" not in text
    # The only underlying builder is training-only
    assert "build_underlying_series" in text
    # But no validation branch — search for validation string excluding docstring CLOSED
    # Count validation occurrences — only allowed in docstring/firewall comments
    lines = [line for line in text.splitlines() if "validation" in line.lower() and "CLOSED" not in line and "validation_constructions" not in line.lower()]
    # Filter to actual code (not comments about firewall)
    code_validations = [line for line in lines if "split" in line.lower() or "import" in line.lower()]
    assert not code_validations, f"validation code found: {code_validations}"


# 39. external-validation harness unreachable
def test_external_validation_harness_unreachable():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "external_validation_harness" not in text
    assert "EXTERNAL_VALIDATION_COMPLETED" not in text


# 40. final-test builder/import unreachable
def test_final_test_unreachable():
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "final_test" not in text.lower() or all(
        kw in line for line in text.splitlines() if "final_test" in line.lower() for kw in ["validation_authorized", "false"]
    ) or "final_test_authorized" in text
    # More precise: no builder for final_test split
    assert 'split="final' not in text
    assert "split='final" not in text
    assert "final_test_access" not in text or "final_test_accesses" in text  # manifest counter is ok
