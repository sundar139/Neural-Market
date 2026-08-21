"""Execution runtime identity — separate from scientific config hash.

Captures the execution environment deterministically so CPU and CUDA
provenance do not collide. Scientific V5ExperimentConfig.config_hash
remains device-free; this module provides the orthogonal execution axis.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess

import torch

RUNTIME_IDENTITY_SCHEMA = "runtime-identity-v1"


def _driver_version() -> str | None:
    """Return NVIDIA driver version when available, else None."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            text=True,
            timeout=5,
        )
        line = out.strip().splitlines()[0].strip() if out.strip() else ""
        return line or None
    except Exception:
        return None


def _gpu_info() -> tuple[str | None, str | None]:
    """Return (gpu_name, compute_capability) when CUDA available."""
    if not torch.cuda.is_available():
        return None, None
    try:
        props = torch.cuda.get_device_properties(0)
        name: str | None = props.name
        cap: str | None = f"{props.major}.{props.minor}"
        return name, cap
    except Exception:
        return None, None


def _cuda_runtime() -> str | None:
    v = getattr(torch.version, "cuda", None)
    return str(v) if v is not None else None


def _cudnn_version() -> int | None:
    try:
        v = torch.backends.cudnn.version()  # type: ignore[no-untyped-call]
        return int(v) if v is not None else None
    except Exception:
        return None


def build_runtime_identity(
    *,
    requested_device: str = "cpu",
    resolved_device: str | None = None,
) -> dict[str, object]:
    """Build a deterministic runtime identity payload.

    Args:
        requested_device: What the caller asked for (cpu/cuda).
        resolved_device: What was actually resolved; defaults to
            requested_device.lower(). No probing or fallback here —
            fail-closed is enforced by resolve_device, not here.

    Returns:
        Dict containing stable fields + runtime_identity_sha256.
    """
    req = requested_device.strip().lower()
    res = (resolved_device.strip().lower() if resolved_device is not None else req)

    cuda_rt = _cuda_runtime()
    cudnn_v = _cudnn_version()
    gpu_name, gpu_cc = _gpu_info()
    driver = _driver_version()

    # Deterministic algorithms / cudnn flags as observed at build time.
    det_algos = bool(torch.are_deterministic_algorithms_enabled())
    cudnn_benchmark = bool(torch.backends.cudnn.benchmark)
    cudnn_deterministic = bool(torch.backends.cudnn.deterministic)

    payload: dict[str, object] = {
        "schema_version": RUNTIME_IDENTITY_SCHEMA,
        "python_version": platform.python_version(),
        "torch_version": str(torch.__version__),
        "requested_device": req,
        "resolved_device": res,
        "cuda_runtime_version": cuda_rt,
        "cudnn_version": cudnn_v,
        "gpu_name": gpu_name,
        "gpu_compute_capability": gpu_cc,
        "deterministic_algorithms": det_algos,
        "cudnn_benchmark": cudnn_benchmark,
        "cudnn_deterministic": cudnn_deterministic,
        "nvidia_driver_version": driver,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload["runtime_identity_sha256"] = sha
    return payload


def runtime_identity_sha256(payload: dict[str, object]) -> str:
    """Recompute the SHA from a payload (excluding the stored sha field)."""
    reduced = {k: v for k, v in payload.items() if k != "runtime_identity_sha256"}
    canonical = json.dumps(reduced, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assert_cuda_runtime_or_fail(requested_device: str) -> None:
    """Fail closed if CUDA requested but unavailable."""
    if requested_device.strip().lower() == "cuda" and not torch.cuda.is_available():
        msg = "CUDA requested but unavailable — fail closed, no CPU fallback"
        raise RuntimeError(msg)
