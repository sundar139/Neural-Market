"""Targeted tests for the per-member v5 replicate training runner (no training)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from contextlib import contextmanager, suppress
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / "reports/research/evidence/structured_vol_v5_replicate_training_runner.py"
AUTH_FIXTURE_ROOT = REPO / "tests/.pytest_cache/v5_replicate_auth"
RECIPE_BASE = "5e28384be24c898b7a3b1182ad6d944307398db0"

spec = importlib.util.spec_from_file_location("v5_runner", str(RUNNER_PATH))
assert spec and spec.loader
_runner = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
spec.loader.exec_module(_runner)  # type: ignore[union-attr]


# Independent identity values for non-tautological runtime/contract testing.
EXPECTED_RUNTIME_SHA_VALID = "b" * 64
EXPECTED_RUNTIME_SHA_MISMATCH = "c" * 64


def _independent_blob(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _independent_contract_blob():
    """Compute the real runner-referenced contract blob from repository bytes."""
    return _independent_blob(_runner.EXEC_CONTRACT_PATH)


def _recipe_blob(commit: str, path: Path) -> str:
    rel = path.relative_to(REPO).as_posix()
    return subprocess.run(
        ["git", "rev-parse", f"{commit}:{rel}"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _select_recipe_head() -> str:
    """Select the newest local commit after the frozen j01 recipe base."""
    commits = subprocess.run(
        ["git", "rev-list", "--ancestry-path", "--reverse", f"{RECIPE_BASE}..HEAD"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    expected = {
        RUNNER_PATH: _independent_blob(RUNNER_PATH),
        _runner.EXEC_CONTRACT_PATH: _independent_contract_blob(),
        _runner.FROZEN_SCHEDULE_PATH: _runner.FROZEN_SCHEDULE_BLOB,
    }
    for commit in reversed(commits):
        if all(_recipe_blob(commit, path) == blob for path, blob in expected.items()):
            return commit
    raise AssertionError(
        "no local recipe commit contains the frozen runner, contract, and schedule"
    )


EXPECTED_RUNNER_BLOB = _independent_blob(RUNNER_PATH)
EXPECTED_CONTRACT_BLOB = _independent_contract_blob()
EXPECTED_RECIPE_HEAD = _select_recipe_head()


def _same_auth_path(path: Path, auth_path: Path) -> bool:
    return Path(path).resolve() == auth_path.resolve()


@contextmanager
def _synthetic_auth_provenance(auth_path: Path):
    """Patch only the ignored synthetic auth path; all production paths use real Git."""
    real_is_tracked = _runner._is_tracked
    real_is_clean = _runner._is_clean
    real_git_head_blob = _runner._git_head_blob
    real_git_blob = _runner._git_blob
    real_is_ancestor = _runner._is_ancestor

    def is_tracked(path):
        return True if _same_auth_path(path, auth_path) else real_is_tracked(path)

    def is_clean(path):
        return True if _same_auth_path(path, auth_path) else real_is_clean(path)

    def git_head_blob(path):
        if _same_auth_path(path, auth_path):
            return real_git_blob(auth_path)
        return real_git_head_blob(path)

    def git_blob(path):
        return real_git_blob(path)

    def is_ancestor(ancestor, head=None):
        return ancestor == EXPECTED_RECIPE_HEAD and real_is_ancestor(ancestor, head)

    with patch.object(_runner, "_is_tracked", side_effect=is_tracked), \
         patch.object(_runner, "_is_clean", side_effect=is_clean), \
         patch.object(_runner, "_git_head_blob", side_effect=git_head_blob), \
         patch.object(_runner, "_git_blob", side_effect=git_blob), \
         patch.object(_runner, "_is_ancestor", side_effect=is_ancestor):
        yield

def _reset_invocations():
    _runner._SCIENTIFIC_INVOCATIONS = 0
    # also reset _INVOCATIONS if old version had it; new runner uses _SCIENTIFIC_INVOCATIONS
    if hasattr(_runner, "_INVOCATIONS"):
        _runner._INVOCATIONS = 0


def _make_auth(tmp_path: Path, member_id: str = "v5-seed-02", **overrides) -> Path:
    """Create an ignored synthetic authorization under the repository test cache."""
    auth_dir = AUTH_FIXTURE_ROOT
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_path = auth_dir / f"auth_{member_id}.json"
    seed_map = {
        "v5-seed-02": (9281, 9282),
        "v5-seed-03": (10281, 10282),
        "v5-seed-04": (11281, 11282),
        "v5-seed-05": (12281, 12282),
        "reserve-j01": (13281, 13282),
    }
    replicate_seed, data_seed = seed_map[member_id]
    base = {
        "schema_version": "structured-vol-v5-primary-training-authorization-v2",
        "authorization_task_id": "NM-R4-TEST-AUTH-001",
        "member_id": member_id,
        "replicate_seed": replicate_seed,
        "model_init_seed": replicate_seed,
        "data_seed": data_seed,
        "eval_seed": 8283,
        "full_config_hash": _runner.EXPECTED_CONFIG_HASHES[member_id],
        "run_prefix": _runner.RUN_PREFIXES[member_id],
        "family_methodology_identity": _runner.EXPECTED_FAMILY_HASH,
        "schedule_git_blob": _runner.FROZEN_SCHEDULE_BLOB,
        "schedule_sha256": _runner.FROZEN_SCHEDULE_SHA,
        "execution_contract_git_blob": EXPECTED_CONTRACT_BLOB,
        "runner_git_blob": EXPECTED_RUNNER_BLOB,
        "execution_recipe_head": EXPECTED_RECIPE_HEAD,
        "training_authorized": True,
        "validation_authorized": False,
        "final_test_authorized": False,
        "reserve": False,
        "max_training_invocations": 1,
        "requested_device": "cuda",
        "expected_resolved_device": "cuda",
        "expected_runtime_identity_sha256": EXPECTED_RUNTIME_SHA_VALID,
    }
    base.update(overrides)
    auth_path.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")

    return auth_path


def _cleanup_auth(auth_path: Path):

    with suppress(FileNotFoundError):
        auth_path.unlink()
    with suppress(OSError):
        auth_path.parent.rmdir()


# 1. allowed member dry-run — reserve-j01 is the only reserve without a replicate dir (all primaries now exist)
def test_allowed_member_dry_run():
    _reset_invocations()
    # Use reserve-j01 as the dry-run eligible member post-081 (j01 has no report/model dir)
    rc = _runner.main(["--member-id", "reserve-j01"])
    assert rc == 0
    _reset_invocations()


# 2. member #1 refusal
def test_member01_refused():
    _reset_invocations()
    rc = _runner.main(["--member-id", "v5-seed-01"])
    assert rc == 2
    _reset_invocations()


# 3. reserve refusal — all non-j01 reserves refused; reserve-j01 is admitted per 047/048
def test_reserve_refused():
    _reset_invocations()
    for mid in ["reserve-01", "reserve-02", "reserve-j02", "reserve-j03"]:
        rc = _runner.main(["--member-id", mid])
        assert rc == 2, mid
    # reserve-j01 is no longer in this bucket — it passes eligibility (commit-required blob check later)
    # Test it at the pre-commit stage: it must not be refused as RESERVE at RESERVE_MEMBERS layer.
    assert "reserve-j01" not in _runner.RESERVE_MEMBERS, "reserve-j01 must be removed from RESERVE_MEMBERS"
    assert _runner.ELIGIBLE_RESERVE_J01 == "reserve-j01"
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
    with pytest.raises(RuntimeError, match="outside repository|not tracked"):
        _runner.check_authorization("v5-seed-02", untracked)


# 11. dirty authorization refusal
def test_dirty_auth_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02")
    auth.write_text(auth.read_text(encoding="utf-8") + "\n# dirty\n", encoding="utf-8")
    real_git_head_blob = _runner._git_head_blob
    try:
        with _synthetic_auth_provenance(auth), patch.object(
            _runner,
            "_git_head_blob",
            side_effect=lambda path: "0" * 40 if _same_auth_path(path, auth) else real_git_head_blob(path),
        ):
            with pytest.raises(RuntimeError, match="worktree blob != HEAD blob"):
                _runner.check_authorization("v5-seed-02", auth)
    finally:
        _cleanup_auth(auth)


# 12. incomplete authorization refusal (missing field)
def test_incomplete_auth_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02")
    data = json.loads(auth.read_text(encoding="utf-8"))
    del data["schedule_git_blob"]
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    try:
        _check_with_mock(auth, "v5-seed-02", "missing required field")
    finally:
        _cleanup_auth(auth)


def _check_with_mock(auth_path: Path, member_id: str, expected_match: str) -> str:
    with _synthetic_auth_provenance(auth_path), pytest.raises(
        RuntimeError, match=expected_match
    ) as exc_info:
        _runner.check_authorization(member_id, auth_path)
    return str(exc_info.value)



def _main_with_mocked_auth(
    member_id: str,
    auth_path: Path,
    runtime_sha: str = EXPECTED_RUNTIME_SHA_VALID,
):
    """Run the real main/auth path with provenance patched only for synthetic auth."""
    with _synthetic_auth_provenance(auth_path), \
         patch("neuralmarket.core.device.resolve_device", return_value=torch.device("cuda")), \
         patch("neuralmarket.core.device.configure_device_determinism"), \
         patch(
             "neuralmarket.core.runtime_identity.build_runtime_identity",
             return_value={
                 "schema_version": "runtime-identity-v1",
                 "requested_device": "cuda",
                 "resolved_device": "cuda",
                 "runtime_identity_sha256": runtime_sha,
             },
         ):
        return _runner.main(
            ["--member-id", member_id, "--authorization", str(auth_path), "--execute"]
        )


# 13. hostile validation_authorized=true refused
def test_hostile_validation_true_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", validation_authorized=True)
    try:
        _check_with_mock(auth, "v5-seed-02", "validation_authorized must be false")
    finally:
        _cleanup_auth(auth)


# 14. hostile final_test_authorized=true refused
def test_hostile_final_test_true_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", final_test_authorized=True)
    try:
        _check_with_mock(auth, "v5-seed-02", "final_test_authorized must be false")
    finally:
        _cleanup_auth(auth)


# 15. reserve=true refused
def test_hostile_reserve_true_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", reserve=True)
    try:
        _check_with_mock(auth, "v5-seed-02", "reserve must be false")
    finally:
        _cleanup_auth(auth)


# 16. max_training_invocations != 1 refused
def test_hostile_max_invocations_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", max_training_invocations=2)
    try:
        _check_with_mock(auth, "v5-seed-02", "max_training_invocations must be 1")
    finally:
        _cleanup_auth(auth)


# 17. wrong seed tuple refused
def test_wrong_seed_tuple_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", model_init_seed=9999)
    try:
        _check_with_mock(auth, "v5-seed-02", "model_init_seed mismatch")
    finally:
        _cleanup_auth(auth)


# 18. wrong runner blob refused

def test_wrong_runner_blob_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", runner_git_blob="deadbeef" * 5)
    try:
        _check_with_mock(auth, "v5-seed-02", "runner_git_blob mismatch")
    finally:
        _cleanup_auth(auth)


# 19. wrong contract-v2 blob refused
def test_wrong_contract_blob_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02", execution_contract_git_blob="deadbeef" * 5)
    try:
        _check_with_mock(auth, "v5-seed-02", "execution_contract_git_blob mismatch")
    finally:
        _cleanup_auth(auth)

# 20. stale/wrong recipe HEAD refused
def test_stale_recipe_head_refused(tmp_path: Path):
    auth = _make_auth(tmp_path, "v5-seed-02")
    data = json.loads(auth.read_text(encoding="utf-8"))
    data["execution_recipe_head"] = "0" * 40
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    try:
        _check_with_mock(auth, "v5-seed-02", "execution_recipe_head invalid|not ancestor")
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
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    # Mock _run_scientific_training to succeed without touching disk/model
    call_count = {"n": 0}

    def fake_run(member_id, report_dir, model_dir, *args, **kwargs):
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
        rc = _main_with_mocked_auth("v5-seed-02", auth)
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
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")

    def fake_run_fail(member_id, report_dir, model_dir, *args, **kwargs):
        raise RuntimeError("synthetic training failure for test")

    monkeypatch.setattr(_runner, "_run_scientific_training", fake_run_fail)
    prefix = _runner.RUN_PREFIXES["v5-seed-03"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))

    auth = _make_auth(tmp_path, "v5-seed-03")
    try:
        rc = _main_with_mocked_auth("v5-seed-03", auth)
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
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-04"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-04")
    try:
        _main_with_mocked_auth("v5-seed-04", auth)
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
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-02"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-02")
    try:
        rc = _main_with_mocked_auth("v5-seed-02", auth)
        assert rc != 0
        assert (fake_report / "training_exit_code.txt").read_text().strip() != "0"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 29. failure writes transcript
def test_failure_writes_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("transcript fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-03"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-03")
    try:
        _main_with_mocked_auth("v5-seed-03", auth)
        assert (fake_report / "training_stdout.log").exists()
        assert len((fake_report / "training_stdout.log").read_text()) > 0
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 30. failure writes FAILED manifest
def test_failure_manifest_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("manifest fail")))
    prefix = _runner.RUN_PREFIXES["v5-seed-04"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-04")
    try:
        _main_with_mocked_auth("v5-seed-04", auth)
        m = json.loads((fake_report / "training_execution_manifest.json").read_text())
        assert m["terminal_status"] == "FAILED"
        assert m["exception_class"] == "RuntimeError"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 31. failure does not emit false-success report
def test_failure_no_false_success_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no success")))
    prefix = _runner.RUN_PREFIXES["v5-seed-05"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-05")
    try:
        _main_with_mocked_auth("v5-seed-05", auth)
        # Either no report, or not COMPLETED
        if (fake_report / "training_report.json").exists():
            assert json.loads((fake_report / "training_report.json").read_text()).get("terminal_status") != "COMPLETED"
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 32. second attempt refused after failure
def test_second_attempt_refused_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail once")))
    prefix = _runner.RUN_PREFIXES["v5-seed-02"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    auth = _make_auth(tmp_path, "v5-seed-02")
    try:
        _main_with_mocked_auth("v5-seed-02", auth)
        # Second attempt must refuse (overwrite or execution_started exists)
        # Need to keep report dir existing
        rc2 = _main_with_mocked_auth("v5-seed-02", auth)
        assert rc2 == 2
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 33. success emits all five required evidence files
def test_success_all_five_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")

    def fake_ok(member_id, report_dir, model_dir, *args, **kwargs):
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
        rc = _main_with_mocked_auth("v5-seed-04", auth)
        assert rc == 0
        for name in ["execution_started.json", "training_stdout.log", "training_exit_code.txt", "training_execution_manifest.json", "training_report.json"]:
            assert (fake_report / name).exists(), name
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


# 34. success manifest hashes coherent
def test_success_manifest_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _reset_invocations()
    if not _runner.EXEC_CONTRACT_PATH.exists():
        pytest.skip("contract v2 not yet created")

    def fake_ok(member_id, report_dir, model_dir, *args, **kwargs):
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
        _main_with_mocked_auth("v5-seed-05", auth)
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
        _runner._run_scientific_training("v5-seed-02", Path("/tmp/a"), Path("/tmp/b"), device=torch.device("cuda"))
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


# === ADDITIONAL FOCUSED TESTS FOR reserve-j01 NARROW ELIGIBILITY (task 081) ===

def test_j01_config_and_family_exact():
    """reserve-j01 config hash and family are the frozen eligible values."""
    assert _runner.EXPECTED_CONFIG_HASHES["reserve-j01"] == "38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605"  # pragma: allowlist secret
    assert _runner.RUN_PREFIXES["reserve-j01"] == "38c5113b27568e14"
    assert _runner.EXPECTED_RESERVE_J01_TUPLE == ("reserve-j01", 13281, 13282, 8283)
    got_cfg = _runner.verify_config_hash("reserve-j01")
    assert got_cfg == _runner.EXPECTED_CONFIG_HASHES["reserve-j01"]
    got_fam = _runner.verify_family_hash("reserve-j01")
    assert got_fam == _runner.EXPECTED_FAMILY_HASH
    # Reserve-derived primary report/model dirs are 16-hex
    assert len(_runner.RUN_PREFIXES["reserve-j01"]) == 16
    assert all(c in "0123456789abcdef" for c in _runner.RUN_PREFIXES["reserve-j01"])


def test_j01_eligibility_not_generic_reserve():
    """Only j01 is eligible; no generic prefix, no startswith, no schedule-wide member allow."""
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert 'startswith("reserve-")' not in text
    assert "startswith('reserve-')" not in text
    assert "all schedule members" not in text.lower()
    # Must not have introduced a non-pinned generic like `in _runner.RESERVE_MEMBERS` widening to include j01 elsewhere
    # Reserve set must exclude j01
    assert "reserve-j01" not in _runner.RESERVE_MEMBERS
    # And the allow path is exactly the ELIGIBLE_RESERVE_J01 constant, not a pattern
    assert _runner.ELIGIBLE_RESERVE_J01 == "reserve-j01"


def _make_auth_for_member(tmp_path: Path, member_id: str, **overrides) -> Path:
    """Create a reserve-j01 synthetic authorization in the ignored test cache."""
    return _make_auth(tmp_path, member_id, **overrides)


def test_j01_without_authorization_fail_closed(tmp_path: Path):
    _reset_invocations()
    with pytest.raises(RuntimeError, match="authorization artifact required"):
        _runner.check_authorization("reserve-j01", None)  # no auth -> fail-closed
    _reset_invocations()


def test_j01_wrong_member_rejected(tmp_path: Path):
    auth = _make_auth_for_member(tmp_path, "reserve-j01")
    # Modify member_id to mismatch
    data = json.loads(auth.read_text(encoding="utf-8"))
    data["member_id"] = "v5-seed-02"
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    try:
        _check_with_mock(auth, "reserve-j01", "member_id mismatch")
    finally:
        _cleanup_auth(auth)


def test_j01_wrong_config_rejected(tmp_path: Path):
    auth = _make_auth_for_member(tmp_path, "reserve-j01", full_config_hash="b" * 64)
    try:
        _check_with_mock(auth, "reserve-j01", "full_config_hash mismatch")
    finally:
        _cleanup_auth(auth)


def test_j01_wrong_family_rejected(tmp_path: Path):
    auth = _make_auth_for_member(tmp_path, "reserve-j01", family_methodology_identity="c" * 64)
    try:
        _check_with_mock(auth, "reserve-j01", "family_methodology_identity mismatch")
    finally:
        _cleanup_auth(auth)


def test_j01_cpu_requested_rejected(tmp_path: Path):
    auth = _make_auth_for_member(tmp_path, "reserve-j01", requested_device="cpu", expected_resolved_device="cpu")
    try:
        # Use mocked git boundary so we reach the authorize_execution cuda==cuda check, not the untracked check
        _check_with_mock(auth, "reserve-j01", "must be cuda|cuda")
    finally:
        _cleanup_auth(auth)


def test_j02_j03_and_unknown_remain_rejected():
    _reset_invocations()
    for mid in ["reserve-j02", "reserve-j03", "reserve-02", "reserve-99", "v5-seed-99", "reserve-j01o"]:
        rc = _runner.main(["--member-id", mid])
        assert rc == 2, f"expected refused for {mid} got {rc}"
    _reset_invocations()


def test_refused_j02_never_invokes_scientific_training(monkeypatch: pytest.MonkeyPatch):
    """Refused reserve-j02 path never reaches scientific training."""
    # The runner's _run_scientific_training must not be called in any j01 dry-run path
    called = {"n": 0}
    orig = _runner._run_scientific_training

    def spy(*a, **kw):
        called["n"] += 1
        return orig(*a, **kw)

    monkeypatch.setattr(_runner, "_run_scientific_training", spy)
    _reset_invocations()
    _runner.main(["--member-id", "reserve-j02"])
    assert called["n"] == 0
    _reset_invocations()


def test_reserve_j01_runner_eligible_via_eligible_constant():
    assert _runner.EXPECTED_RESERVE_J01_TUPLE == ("reserve-j01", 13281, 13282, 8283)


def test_positive_mocked_j01_traverses_to_pre_scientific_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Positive reserve-j01 auth traverses independent identity checks to the boundary."""
    _reset_invocations()
    auth = _make_auth_for_member(tmp_path, "reserve-j01")
    auth_data = json.loads(auth.read_text(encoding="utf-8"))
    independent_contract = _independent_contract_blob()
    assert auth_data["runner_git_blob"] == EXPECTED_RUNNER_BLOB == "a79a79f477429d66cc7fc0c75db7c751726ee577"
    assert auth_data["execution_contract_git_blob"] == independent_contract
    assert auth_data["execution_recipe_head"] == EXPECTED_RECIPE_HEAD
    assert _recipe_blob(EXPECTED_RECIPE_HEAD, RUNNER_PATH) == EXPECTED_RUNNER_BLOB
    assert _recipe_blob(EXPECTED_RECIPE_HEAD, _runner.EXEC_CONTRACT_PATH) == independent_contract
    assert _recipe_blob(EXPECTED_RECIPE_HEAD, _runner.FROZEN_SCHEDULE_PATH) == _runner.FROZEN_SCHEDULE_BLOB
    assert auth_data["expected_runtime_identity_sha256"] == EXPECTED_RUNTIME_SHA_VALID

    prefix = _runner.RUN_PREFIXES["reserve-j01"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    marker_calls = {"n": 0}

    def fake_marker(report_dir, member_id, prefix_arg, authorization, auth_path, **kw):
        marker_calls["n"] += 1
        assert member_id == "reserve-j01"
        assert prefix_arg == prefix
        assert authorization["execution_contract_git_blob"] == independent_contract
        return fake_report / "execution_started.json"

    sci_calls = {"n": 0}

    def fake_sci(member_id, report_dir, model_dir, *args, **kwargs):
        sci_calls["n"] += 1
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
            "training_series_sha256": "4863b2cc63a09ffb03bbe455c7859c46b521b6f7bef8212e0e3876ac8488669c",
            "fit_window_count": 672,
            "selection_window_count": 107,
            "training_start_utc": "2026-08-22T00:00:00+00:00",
            "training_end_utc": "2026-08-22T01:00:00+00:00",
        }

    monkeypatch.setattr(_runner, "_exclusive_create_execution_started", fake_marker)
    monkeypatch.setattr(_runner, "_run_scientific_training", fake_sci)
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    try:
        rc = _main_with_mocked_auth("reserve-j01", auth)
        assert rc == 0
        assert marker_calls["n"] == 1
        assert sci_calls["n"] == 1
        assert not (REPO / "reports/research/structured_vol_v5_replicates" / prefix / "execution_started.json").exists()
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


def test_j01_runtime_identity_mismatch_refused_before_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Runtime observed-vs-expected mismatch refuses before marker and science."""
    _reset_invocations()
    auth = _make_auth_for_member(tmp_path, "reserve-j01")
    prefix = _runner.RUN_PREFIXES["reserve-j01"]
    fake_report = tmp_path / "report" / prefix
    fake_model = tmp_path / "model" / prefix
    marker_calls = {"n": 0}
    sci_calls = {"n": 0}

    monkeypatch.setattr(_runner, "_exclusive_create_execution_started", lambda *a, **k: marker_calls.__setitem__("n", marker_calls["n"] + 1))
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: sci_calls.__setitem__("n", sci_calls["n"] + 1))
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report if p == prefix else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model if p == prefix else _runner.derive_model_dir(p))
    try:
        rc = _main_with_mocked_auth("reserve-j01", auth, EXPECTED_RUNTIME_SHA_MISMATCH)
        assert rc == 2
        assert marker_calls["n"] == 0
        assert sci_calls["n"] == 0
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


def test_j01_wrong_runner_blob_rejected_before_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Wrong runner blob refuses before marker and science against the frozen runner blob."""
    auth = _make_auth_for_member(tmp_path, "reserve-j01", runner_git_blob="e" * 64)
    prefix = _runner.RUN_PREFIXES["reserve-j01"]
    marker_calls = {"n": 0}
    sci_calls = {"n": 0}
    monkeypatch.setattr(_runner, "_exclusive_create_execution_started", lambda *a, **k: marker_calls.__setitem__("n", marker_calls["n"] + 1))
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: sci_calls.__setitem__("n", sci_calls["n"] + 1))
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: tmp_path / "report" / prefix)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: tmp_path / "model" / prefix)
    try:
        rc = _main_with_mocked_auth("reserve-j01", auth)
        assert rc == 2
        assert marker_calls["n"] == 0
        assert sci_calls["n"] == 0
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


def test_j01_wrong_contract_blob_rejected_before_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Wrong contract blob refuses before marker and science against the real contract blob."""
    real_contract = _independent_contract_blob()
    wrong_contract = "d" * 64
    assert wrong_contract != real_contract
    auth = _make_auth_for_member(tmp_path, "reserve-j01", execution_contract_git_blob=wrong_contract)
    prefix = _runner.RUN_PREFIXES["reserve-j01"]
    marker_calls = {"n": 0}
    sci_calls = {"n": 0}
    monkeypatch.setattr(_runner, "_exclusive_create_execution_started", lambda *a, **k: marker_calls.__setitem__("n", marker_calls["n"] + 1))
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: sci_calls.__setitem__("n", sci_calls["n"] + 1))
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: tmp_path / "report" / prefix)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: tmp_path / "model" / prefix)
    try:
        rc = _main_with_mocked_auth("reserve-j01", auth)
        assert rc == 2
        assert marker_calls["n"] == 0
        assert sci_calls["n"] == 0
    finally:
        _cleanup_auth(auth)
        _reset_invocations()


def test_j01_stale_recipe_rejected_before_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Stale recipe ancestry refuses before marker and science without unrelated errors."""
    auth = _make_auth_for_member(tmp_path, "reserve-j01", execution_recipe_head="0" * 40)
    prefix = _runner.RUN_PREFIXES["reserve-j01"]
    marker_calls = {"n": 0}
    sci_calls = {"n": 0}
    monkeypatch.setattr(_runner, "_exclusive_create_execution_started", lambda *a, **k: marker_calls.__setitem__("n", marker_calls["n"] + 1))
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **k: sci_calls.__setitem__("n", sci_calls["n"] + 1))
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: tmp_path / "report" / prefix)
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: tmp_path / "model" / prefix)
    try:
        message = _check_with_mock(auth, "reserve-j01", "execution_recipe_head invalid|not ancestor")
        assert "not committed" not in message
        rc = _main_with_mocked_auth("reserve-j01", auth)
        assert rc == 2
        assert marker_calls["n"] == 0
        assert sci_calls["n"] == 0
    finally:
        _cleanup_auth(auth)
        _reset_invocations()
