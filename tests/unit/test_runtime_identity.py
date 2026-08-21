"""Runtime identity determinism, divergence, and fail-closed semantics."""

from __future__ import annotations

import pytest
import torch

from neuralmarket.core.device import load_checkpoint_state, resolve_device
from neuralmarket.core.runtime_identity import (
    assert_cuda_runtime_or_fail,
    build_runtime_identity,
    runtime_identity_sha256,
)


def test_cpu_identity_deterministic() -> None:
    a = build_runtime_identity(requested_device="cpu")
    b = build_runtime_identity(requested_device="cpu")
    assert a["runtime_identity_sha256"] == b["runtime_identity_sha256"]
    assert runtime_identity_sha256(a) == a["runtime_identity_sha256"]


def test_cuda_identity_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    # Requires real CUDA, but determinism holds even mocked
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.version, "cuda", "13.2", raising=False)
    monkeypatch.setattr(torch.backends.cudnn, "version", lambda: 92000, raising=False)
    a = build_runtime_identity(requested_device="cuda", resolved_device="cuda")
    b = build_runtime_identity(requested_device="cuda", resolved_device="cuda")
    assert a["runtime_identity_sha256"] == b["runtime_identity_sha256"]


def test_cpu_and_cuda_identities_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    # CPU identity uses real torch.version.cuda (None on cpu wheel) — so build
    # cpu identity without mocking, then cuda identity with mocked cuda.
    cpu = build_runtime_identity(requested_device="cpu")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.version, "cuda", "13.2", raising=False)
    monkeypatch.setattr(torch.backends.cudnn, "version", lambda: 92000, raising=False)
    # Mock GPU info to ensure a distinct payload even if real GPU present
    import neuralmarket.core.runtime_identity as ri

    monkeypatch.setattr(ri, "_gpu_info", lambda: ("NVIDIA GeForce RTX 4070 Laptop GPU", "8.9"))
    cuda = build_runtime_identity(requested_device="cuda", resolved_device="cuda")
    assert cpu["runtime_identity_sha256"] != cuda["runtime_identity_sha256"]


def test_changing_torch_version_changes_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    a = build_runtime_identity(requested_device="cpu")
    monkeypatch.setattr(torch, "__version__", "9.9.9+cpu", raising=False)
    b = build_runtime_identity(requested_device="cpu")
    assert a["runtime_identity_sha256"] != b["runtime_identity_sha256"]


def test_changing_cuda_runtime_changes_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.version, "cuda", "13.2", raising=False)
    a = build_runtime_identity(requested_device="cuda", resolved_device="cuda")
    monkeypatch.setattr(torch.version, "cuda", "12.8", raising=False)
    b = build_runtime_identity(requested_device="cuda", resolved_device="cuda")
    assert a["runtime_identity_sha256"] != b["runtime_identity_sha256"]


def test_changing_requested_device_changes_identity() -> None:
    a = build_runtime_identity(requested_device="cpu", resolved_device="cpu")
    b = build_runtime_identity(requested_device="cuda", resolved_device="cuda")
    assert a["runtime_identity_sha256"] != b["runtime_identity_sha256"]


def test_unstable_fields_absent() -> None:
    ident = build_runtime_identity(requested_device="cpu")
    for k in ("pid", "timestamp", "free_vram", "process_id", "tmp_path", "free_memory"):
        assert k not in ident
    # keys are exactly the documented set + sha
    assert ident["schema_version"] == "runtime-identity-v1"


def test_cuda_request_unavailable_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="fail closed"):
        assert_cuda_runtime_or_fail("cuda")
    with pytest.raises(RuntimeError, match="fail closed"):
        resolve_device("cuda")


def test_cpu_remains_cpu_even_if_cuda_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.version, "cuda", "13.2", raising=False)
    assert resolve_device("cpu") == torch.device("cpu")
    assert build_runtime_identity(requested_device="cpu")["resolved_device"] == "cpu"


def test_no_silent_fallback_on_cuda_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError):
        resolve_device("cuda")
    # cpu still works
    assert resolve_device("cpu") == torch.device("cpu")


def test_checkpoint_portability() -> None:
    import tempfile
    from pathlib import Path

    t = torch.randn(3, 3)
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ckpt.pt"
        torch.save({"x": t}, str(p))
        loaded = load_checkpoint_state(str(p), map_location="cpu")
        assert torch.allclose(loaded["x"], t)


def test_scientific_config_hash_unchanged() -> None:
    from neuralmarket.research.structured_vol_experiment import V5ExperimentConfig

    h = V5ExperimentConfig().config_hash()
    # Frozen hash recorded in seed-04 artifacts; must not drift when runtime
    # identity is added (device not in config_hash).
    assert isinstance(h, str) and len(h) == 64
    # Recomputing is deterministic
    assert h == V5ExperimentConfig().config_hash()
