"""Governed CUDA execution repair — authorization, runtime, and device tests.

No scientific training, no --execute of seed-05, no validation/final.
Covers the NM-R4-GPU-GOVERNED-EXECUTION-REPAIR-053 contract.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNNER_PATH = REPO / "reports/research/evidence/structured_vol_v5_replicate_training_runner.py"

spec = importlib.util.spec_from_file_location("v5_runner_053", str(RUNNER_PATH))
assert spec and spec.loader
_runner = importlib.util.module_from_spec(spec)  # type: ignore[attr-defined]
spec.loader.exec_module(_runner)  # type: ignore[union-attr]


def _reset() -> None:
    _runner._SCIENTIFIC_INVOCATIONS = 0


def _make_v1_auth(member_id: str = "v5-seed-02") -> Path:
    """Create a minimal v1 auth JSON tracked in REPO (for parsing tests)."""
    auth_dir = REPO / "reports/research/structured_vol_v5_replicates" / "_test_auth_053"
    auth_dir.mkdir(parents=True, exist_ok=True)
    p = auth_dir / f"auth_v1_{member_id}.json"
    v2_blob = subprocess.run(
        ["git", "hash-object", str(REPO / "reports/research/structured_vol_v5_training_execution_contract_v5.json")],
        capture_output=True, text=True, check=True
    ).stdout.strip()
    runner_blob = subprocess.run(
        ["git", "hash-object", str(RUNNER_PATH)], capture_output=True, text=True, check=True
    ).stdout.strip()
    data = {
        "schema_version": "structured-vol-v5-primary-training-authorization-v1",
        "authorization_task_id": "NM-R4-TEST-AUTH-053",
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
        "runner_git_blob": runner_blob,
        "execution_recipe_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip(),
        "training_authorized": True,
        "validation_authorized": False,
        "final_test_authorized": False,
        "reserve": False,
        "max_training_invocations": 1,
    }
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(p)], cwd=str(REPO), capture_output=True, check=False)
    return p


def _make_v2_auth(
    member_id: str = "v5-seed-02",
    requested_device: str = "cuda",
    expected_resolved: str = "cuda",
    expected_sha: str = "a" * 64,
) -> Path:
    p = _make_v1_auth(member_id)
    data = json.loads(p.read_text(encoding="utf-8"))
    data["schema_version"] = "structured-vol-v5-primary-training-authorization-v2"
    data["requested_device"] = requested_device
    data["expected_resolved_device"] = expected_resolved
    data["expected_runtime_identity_sha256"] = expected_sha
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(p)], cwd=str(REPO), capture_output=True, check=False)
    return p


def _cleanup(p: Path) -> None:
    subprocess.run(["git", "reset", "HEAD", "--", str(p)], cwd=str(REPO), capture_output=True, check=False)
    try:
        p.unlink()
    except FileNotFoundError:
        pass
    try:
        p.parent.rmdir()
    except OSError:
        pass


def _check_with_mocked_git(auth_path: Path, member_id: str, should_raise: bool = True, match: str | None = None):
    """Run check_authorization with mocked git to isolate parsing logic."""
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    blob = subprocess.run(["git", "hash-object", str(auth_path)], capture_output=True, text=True, check=True).stdout.strip()
    rb = data.get("runner_git_blob", "")
    cb = data.get("execution_contract_git_blob", "")
    sb = data.get("schedule_git_blob", "")

    def _mb(path):
        s = str(path)
        if s == str(auth_path):
            return blob
        if "replicate_training_runner" in s:
            return rb or blob
        if "training_execution_contract" in s:
            return cb or blob
        if "seed_schedule" in s:
            return sb or blob
        return blob

    def _mh(path):
        s = str(path)
        if "replicate_training_runner" in s:
            return rb or blob
        if "training_execution_contract" in s:
            return cb or blob
        if "seed_schedule" in s:
            return sb or blob
        return blob

    _orig = subprocess.run

    def _mr(cmd, *a, **kw):
        if isinstance(cmd, list) and "rev-parse" in str(cmd):
            ac = str(cmd[-1]) if cmd else ""
            if "replicate_training_runner" in ac:
                return type("R", (), {"returncode": 0, "stdout": rb + "\n", "stderr": ""})()
            if "training_execution_contract" in ac:
                return type("R", (), {"returncode": 0, "stdout": cb + "\n", "stderr": ""})()
            if "seed_schedule" in ac:
                return type("R", (), {"returncode": 0, "stdout": sb + "\n", "stderr": ""})()
        if isinstance(cmd, list) and "diff" in str(cmd):
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if isinstance(cmd, list) and "merge-base" in str(cmd):
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return _orig(cmd, *a, **kw)

    with patch.object(_runner, "_is_tracked", return_value=True), \
         patch.object(_runner, "_is_clean", return_value=True), \
         patch.object(_runner, "_git_head_blob", side_effect=_mh), \
         patch.object(_runner, "_git_blob", side_effect=_mb), \
         patch.object(_runner, "_is_ancestor", return_value=True), \
         patch("subprocess.run", side_effect=_mr):
        if should_raise:
            with pytest.raises(RuntimeError, match=match or ""):
                _runner.check_authorization(member_id, auth_path)
        else:
            return _runner.check_authorization(member_id, auth_path)


# --- Authorization v1/v2 parsing ---

def test_v1_remains_cpu_only(tmp_path: Path):
    _reset()
    auth = _make_v1_auth("v5-seed-02")
    try:
        data = _check_with_mocked_git(auth, "v5-seed-02", should_raise=False)
        assert data["schema_version"] == "structured-vol-v5-primary-training-authorization-v1"
    finally:
        _cleanup(auth)


def test_v1_cannot_request_cuda(tmp_path: Path):
    _reset()
    auth = _make_v1_auth("v5-seed-02")
    data = json.loads(auth.read_text(encoding="utf-8"))
    data["requested_device"] = "cuda"
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(auth)], cwd=str(REPO), capture_output=True, check=False)
    try:
        _check_with_mocked_git(auth, "v5-seed-02", should_raise=True, match="v1 authorization must not contain")
    finally:
        _cleanup(auth)


def test_v2_cuda_parses_correctly(tmp_path: Path):
    _reset()
    auth = _make_v2_auth("v5-seed-03", "cuda", "cuda", "b" * 64)
    try:
        data = _check_with_mocked_git(auth, "v5-seed-03", should_raise=False)
        assert data["requested_device"] == "cuda"
        assert data["expected_resolved_device"] == "cuda"
        assert data["expected_runtime_identity_sha256"] == "b" * 64
    finally:
        _cleanup(auth)


def test_v2_missing_runtime_identity_fails_closed(tmp_path: Path):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "cuda", "cuda", "c" * 64)
    data = json.loads(auth.read_text(encoding="utf-8"))
    del data["expected_runtime_identity_sha256"]
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(auth)], cwd=str(REPO), capture_output=True, check=False)
    try:
        _check_with_mocked_git(auth, "v5-seed-02", should_raise=True, match="missing required field")
    finally:
        _cleanup(auth)


def test_v2_bad_runtime_identity_fails_closed(tmp_path: Path):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "cuda", "cuda", "not-hex")
    try:
        _check_with_mocked_git(auth, "v5-seed-02", should_raise=True, match="64 lowercase hex")
    finally:
        _cleanup(auth)


def test_v2_requested_resolved_mismatch_fails_closed(tmp_path: Path):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "cuda", "cpu", "a" * 64)
    try:
        _check_with_mocked_git(auth, "v5-seed-02", should_raise=True, match="requested_device.*!= expected_resolved")
    finally:
        _cleanup(auth)


def test_v2_unknown_device_fails_closed(tmp_path: Path):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "tpu", "tpu", "a" * 64)
    try:
        _check_with_mocked_git(auth, "v5-seed-02", should_raise=True, match="must be cpu or cuda")
    finally:
        _cleanup(auth)


def test_v1_unknown_schema_fails_closed(tmp_path: Path):
    _reset()
    auth = _make_v1_auth("v5-seed-02")
    data = json.loads(auth.read_text(encoding="utf-8"))
    data["schema_version"] = "structured-vol-v5-primary-training-authorization-v99"
    auth.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(auth)], cwd=str(REPO), capture_output=True, check=False)
    try:
        _check_with_mocked_git(auth, "v5-seed-02", should_raise=True, match="schema_version must be one of")
    finally:
        _cleanup(auth)


# --- Pre-marker refusal ---

def _main_with_mocked_v2(auth_path: Path, member_id: str, fake_report_dir: Path, fake_model_dir: Path, monkeypatch):
    """Run main with mocked dirs and git; returns rc."""
    monkeypatch.setattr(_runner, "derive_report_dir", lambda p: fake_report_dir if p == _runner.RUN_PREFIXES[member_id] else _runner.derive_report_dir(p))
    monkeypatch.setattr(_runner, "derive_model_dir", lambda p: fake_model_dir if p == _runner.RUN_PREFIXES[member_id] else _runner.derive_model_dir(p))
    # Mock git to accept auth regardless of real blob (for pre-marker tests we want to reach device check)
    data = json.loads(auth_path.read_text(encoding="utf-8"))
    blob = subprocess.run(["git", "hash-object", str(auth_path)], capture_output=True, text=True, check=True).stdout.strip()
    rb = data.get("runner_git_blob", "")
    cb = data.get("execution_contract_git_blob", "")
    sb = data.get("schedule_git_blob", "")

    def _mb(path):
        s = str(path)
        if s == str(auth_path):
            return blob
        if "replicate_training_runner" in s:
            return rb
        if "training_execution_contract" in s:
            return cb
        if "seed_schedule" in s:
            return sb
        return blob

    def _mh(path):
        s = str(path)
        if "replicate_training_runner" in s:
            return rb
        if "training_execution_contract" in s:
            return cb
        if "seed_schedule" in s:
            return sb
        return blob

    _orig = subprocess.run

    def _mr(cmd, *a, **kw):
        if isinstance(cmd, list) and "rev-parse" in str(cmd):
            ac = str(cmd[-1]) if cmd else ""
            if "replicate_training_runner" in ac:
                return type("R2", (), {"returncode": 0, "stdout": rb + "\n", "stderr": ""})()
            if "training_execution_contract" in ac:
                return type("R2", (), {"returncode": 0, "stdout": cb + "\n", "stderr": ""})()
            if "seed_schedule" in ac:
                return type("R2", (), {"returncode": 0, "stdout": sb + "\n", "stderr": ""})()
            if "rev-parse" in str(cmd) and "HEAD" in str(cmd) and ":" not in str(cmd):
                return _orig(cmd, *a, **kw)
        if isinstance(cmd, list) and "diff" in str(cmd):
            return type("R2", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if isinstance(cmd, list) and "merge-base" in str(cmd):
            return type("R2", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if isinstance(cmd, list) and "ls-files" in str(cmd):
            # For auth path, pretend tracked
            return type("R2", (), {"returncode": 0, "stdout": str(auth_path), "stderr": ""})()
        if isinstance(cmd, list) and "hash-object" in str(cmd):
            return _orig(cmd, *a, **kw)
        if isinstance(cmd, list) and "rev-parse" in str(cmd) and ":" in str(cmd):
            return _orig(cmd, *a, **kw)
        return _orig(cmd, *a, **kw)

    with patch("subprocess.run", side_effect=_mr), \
         patch.object(_runner, "_is_tracked", return_value=True), \
         patch.object(_runner, "_is_clean", return_value=True), \
         patch.object(_runner, "_git_head_blob", side_effect=_mh), \
         patch.object(_runner, "_git_blob", side_effect=_mb), \
         patch.object(_runner, "_is_ancestor", return_value=True):
        return _runner.main(["--member-id", member_id, "--authorization", str(auth_path), "--execute"])


def test_wrong_runtime_fails_before_marker(tmp_path: Path, monkeypatch):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "cuda", "cuda", "0" * 64)
    fake_report = tmp_path / "report" / _runner.RUN_PREFIXES["v5-seed-02"]
    fake_model = tmp_path / "model" / _runner.RUN_PREFIXES["v5-seed-02"]
    # Prevent actual training from running if we unexpectedly pass
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("should not train")))
    try:
        rc = _main_with_mocked_v2(auth, "v5-seed-02", fake_report, fake_model, monkeypatch)
        # On CPU env, cuda requested but unavailable => device preflight fails before marker
        # On GPU env, sha mismatch => runtime mismatch fails before marker
        # Either way, must refuse (2) and not create execution_started
        assert rc == 2, f"expected refusal, got {rc}"
        assert not (fake_report / "execution_started.json").exists()
        assert _runner._SCIENTIFIC_INVOCATIONS == 0
    finally:
        _cleanup(auth)
        _reset()


def test_execution_started_not_created_on_preflight_mismatch(tmp_path: Path, monkeypatch):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "cuda", "cuda", "f" * 64)
    fake_report = tmp_path / "report2" / _runner.RUN_PREFIXES["v5-seed-02"]
    fake_model = tmp_path / "model2" / _runner.RUN_PREFIXES["v5-seed-02"]
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("should not train")))
    try:
        rc = _main_with_mocked_v2(auth, "v5-seed-02", fake_report, fake_model, monkeypatch)
        assert rc == 2
        assert not (fake_report / "execution_started.json").exists()
    finally:
        _cleanup(auth)
        _reset()


def test_invocation_zero_on_mismatch(tmp_path: Path, monkeypatch):
    _reset()
    auth = _make_v2_auth("v5-seed-02", "cuda", "cuda", "e" * 64)
    fake_report = tmp_path / "report3" / _runner.RUN_PREFIXES["v5-seed-02"]
    fake_model = tmp_path / "model3" / _runner.RUN_PREFIXES["v5-seed-02"]
    monkeypatch.setattr(_runner, "_run_scientific_training", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("should not train")))
    try:
        _main_with_mocked_v2(auth, "v5-seed-02", fake_report, fake_model, monkeypatch)
        assert _runner._SCIENTIFIC_INVOCATIONS == 0
    finally:
        _cleanup(auth)
        _reset()


def test_runner_report_device_not_hardcoded_cpu(tmp_path: Path):
    """Check that runner source no longer hardcodes device cpu in report fields."""
    text = RUNNER_PATH.read_text(encoding="utf-8")
    # The old line:  \"device\": \"cpu\",  must be gone
    assert text.count('\"device\": \"cpu\"') == 0, "runner still hardcodes device cpu"
    # New path must use resolved device
    assert "resolved_str" in text or "resolved_device" in text


def test_report_device_propagates_from_runtime_identity(tmp_path: Path, monkeypatch):
    """Integration: successful v1 run should write requested/resolved + runtime identity."""
    _reset()
    auth = _make_v1_auth("v5-seed-05")
    fake_report = tmp_path / "report_ok" / _runner.RUN_PREFIXES["v5-seed-05"]
    fake_model = tmp_path / "model_ok" / _runner.RUN_PREFIXES["v5-seed-05"]

    def fake_ok(member_id, report_dir, model_dir, device=None):
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
            "best_epoch": 1,
            "initial_internal_rbf": 1.0,
            "best_internal_rbf": 0.5,
        }

    monkeypatch.setattr(_runner, "_run_scientific_training", fake_ok)
    with patch.object(_runner, "derive_report_dir", lambda p: fake_report if p == _runner.RUN_PREFIXES["v5-seed-05"] else _runner.derive_report_dir(p)), \
         patch.object(_runner, "derive_model_dir", lambda p: fake_model if p == _runner.RUN_PREFIXES["v5-seed-05"] else _runner.derive_model_dir(p)):
        data = json.loads(auth.read_text(encoding="utf-8"))
        blob = subprocess.run(["git", "hash-object", str(auth)], capture_output=True, text=True, check=True).stdout.strip()
        rb = data.get("runner_git_blob", "")
        cb = data.get("execution_contract_git_blob", "")
        sb = data.get("schedule_git_blob", "")

        def _mb(path):
            s = str(path)
            if s == str(auth):
                return blob
            if "replicate_training_runner" in s:
                return rb
            if "training_execution_contract" in s:
                return cb
            if "seed_schedule" in s:
                return sb
            return blob

        def _mh(path):
            s = str(path)
            if "replicate_training_runner" in s:
                return rb
            if "training_execution_contract" in s:
                return cb
            if "seed_schedule" in s:
                return sb
            return blob

        _orig = subprocess.run

        def _mr(cmd, *a, **kw):
            if isinstance(cmd, list) and "rev-parse" in str(cmd):
                ac = str(cmd[-1]) if cmd else ""
                if "replicate_training_runner" in ac:
                    return type("R2", (), {"returncode": 0, "stdout": rb + "\n", "stderr": ""})()
                if "training_execution_contract" in ac:
                    return type("R2", (), {"returncode": 0, "stdout": cb + "\n", "stderr": ""})()
                if "seed_schedule" in ac:
                    return type("R2", (), {"returncode": 0, "stdout": sb + "\n", "stderr": ""})()
                if "HEAD" in str(cmd) and ":" not in str(cmd):
                    return _orig(cmd, *a, **kw)
            if isinstance(cmd, list) and "diff" in str(cmd):
                return type("R2", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if isinstance(cmd, list) and "merge-base" in str(cmd):
                return type("R2", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            if isinstance(cmd, list) and "ls-files" in str(cmd):
                return type("R2", (), {"returncode": 0, "stdout": str(auth), "stderr": ""})()
            if isinstance(cmd, list) and "hash-object" in str(cmd):
                return _orig(cmd, *a, **kw)
            return _orig(cmd, *a, **kw)

        with patch("subprocess.run", side_effect=_mr), \
             patch.object(_runner, "_is_tracked", return_value=True), \
             patch.object(_runner, "_is_clean", return_value=True), \
             patch.object(_runner, "_git_head_blob", side_effect=_mh), \
             patch.object(_runner, "_git_blob", side_effect=_mb), \
             patch.object(_runner, "_is_ancestor", return_value=True):
            rc = _runner.main(["--member-id", "v5-seed-05", "--authorization", str(auth), "--execute"])
            assert rc == 0, f"expected success, got {rc}"
            started = json.loads((fake_report / "execution_started.json").read_text())
            assert "requested_device" in started
            assert "resolved_device" in started
            assert "runtime_identity_sha256" in started
            assert "runtime_identity" in started
            manifest = json.loads((fake_report / "training_execution_manifest.json").read_text())
            assert "requested_device" in manifest
            assert "resolved_device" in manifest
            report = json.loads((fake_report / "training_report.json").read_text())
            # device field must exist and be resolved (cpu on this env)
            assert "device" in report
            assert report["device"] in ("cpu", "cuda")
            assert "runtime_identity_sha256" in report

    _cleanup(auth)
    _reset()


# --- Trainer device propagation ---

def test_trainer_device_propagation_cpu():
    import torch

    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.core.trainer_device import make_generator

    device = torch.device("cpu")
    gen = make_generator(device, 42)
    # Generator should be usable for randn on cpu
    t = torch.randn(2, 3, generator=gen, device=device)
    assert t.shape == (2, 3)
    assert str(t.device) == "cpu"


def test_trainer_cuda_generator_uses_cuda_device():
    import torch

    if not torch.cuda.is_available():
        pytest.skip("CUDA not available")

    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.core.trainer_device import make_generator

    device = torch.device("cuda")
    gen = make_generator(device, 123)
    t = torch.randn(2, 3, generator=gen, device=device)
    assert str(t.device) == "cuda" or str(t.device).startswith("cuda:")


def test_trainer_randn_tensor_full_use_resolved_device():
    import torch

    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.core.trainer_device import full_on_device, randn_on_device, tensor_on_device

    for dev_str in ["cpu"]:
        device = torch.device(dev_str)
        t1 = randn_on_device(2, 3, device=device)
        assert str(t1.device) == dev_str
        t2 = tensor_on_device([1.0, 2.0], device=device)
        assert str(t2.device) == dev_str
        t3 = full_on_device((2, 2), 0.5, device=device)
        assert str(t3.device) == dev_str
        assert float(t3[0, 0].item()) == pytest.approx(0.5)


def test_checkpoint_portability_intact():
    """Checkpoints are saved with .cpu() — portable regardless of device."""
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "v.cpu()" in text


def test_runtime_identity_capture_deterministic():
    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.core.device import configure_device_determinism, resolve_device
    from neuralmarket.core.runtime_identity import build_runtime_identity

    dev = resolve_device("cpu")
    configure_device_determinism(dev)
    a = build_runtime_identity(requested_device="cpu", resolved_device=str(dev))
    configure_device_determinism(dev)
    b = build_runtime_identity(requested_device="cpu", resolved_device=str(dev))
    assert a["runtime_identity_sha256"] == b["runtime_identity_sha256"]


@pytest.mark.skipif(
    __import__("torch").cuda.is_available() is False, reason="CUDA not available"
)
def test_cuda_smoke_device_plumbing():
    """Real CUDA smoke: proves model/tensor/generator compatibility with synthetic data.

    Does NOT perform governed scientific training, creates no markers.
    """
    import torch
    sys.path.insert(0, str(REPO / "src"))
    from neuralmarket.core.device import configure_device_determinism, resolve_device
    from neuralmarket.core.runtime_identity import build_runtime_identity
    from neuralmarket.core.trainer_device import make_generator
    from neuralmarket.models.structured_vol_sde import StructuredVolatilityNeuralSde

    device = resolve_device("cuda")
    configure_device_determinism(device, enabled=True)
    rt = build_runtime_identity(requested_device="cuda", resolved_device=str(device))
    assert rt["resolved_device"] == "cuda"
    assert len(rt["runtime_identity_sha256"]) == 64

    # Synthetic forward/backward on CUDA
    model = StructuredVolatilityNeuralSde().to(device=device)
    model.train()
    batch, horizon = 4, model.config.horizon
    # Synthetic context/normalizer not needed — just test device plumbing
    ctx = torch.randn(batch, model.config.n_context, device=device)
    gen = make_generator(device, 999)
    noise = torch.randn(batch, horizon, model.config.brownian_dim, generator=gen, device=device)
    out = model(ctx, noise)
    assert out.shape == (batch, horizon)
    assert str(out.device).startswith("cuda")
    loss = out.sum()
    loss.backward()
    # Verify gradients are finite
    for p in model.parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all()


def test_no_seed05_gpu_authorization_created():
    """Task must not create a seed-05 GPU authorization."""
    for p in (REPO / "reports/research/authorizations/structured_vol_v5_primary_training").glob("*.json"):
        if "seed-05" in p.name.lower() or "seed_05" in p.name.lower():
            data = json.loads(p.read_text(encoding="utf-8"))
            # Must remain v1; must not have been rewritten to cuda
            assert data.get("schema_version") == "structured-vol-v5-primary-training-authorization-v1", f"{p} was rewritten to v2"
            assert "requested_device" not in data
            assert "expected_runtime_identity_sha256" not in data
    # Also check no GPU auth file was created at repo root or nearby
    for pat in ["**/*gpu*auth*.json", "**/*seed-05*gpu*.json"]:
        for p in REPO.glob(pat):
            if "authorizations" in str(p):
                continue
            pytest.fail(f"unexpected GPU auth file created: {p}")
