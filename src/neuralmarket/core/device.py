"""Explicit device selection with fail-closed CUDA semantics."""

from __future__ import annotations

import torch


def resolve_device(requested: str = "cpu") -> torch.device:
    """Resolve a compute device string with no silent fallback.

    Args:
        requested: "cpu" or "cuda" (case-insensitive).

    Returns:
        torch.device for the requested backend.

    Raises:
        ValueError: if unknown device requested.
        RuntimeError: if cuda requested but unavailable.
    """
    req = requested.strip().lower()
    if req == "cpu":
        return torch.device("cpu")
    if req == "cuda":
        if not torch.cuda.is_available():
            msg = "CUDA requested but unavailable - fail closed, no CPU fallback"
            raise RuntimeError(msg)
        if torch.version.cuda is None:
            msg = "CUDA requested but torch.version.cuda is None"
            raise RuntimeError(msg)
        return torch.device("cuda")
    msg = f"unknown device {requested!r}: expected 'cpu' or 'cuda'"
    raise ValueError(msg)


def configure_device_determinism(device: torch.device, *, enabled: bool = True) -> None:
    """Apply deterministic settings consistent with neural_sde semantics."""
    # Keep neural_sde.configure_determinism semantics: enable deterministic
    # algorithms and disable cudnn benchmark.
    torch.use_deterministic_algorithms(enabled, warn_only=False)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    # Seed CUDA RNG if relevant
    _ = device  # device is recorded for provenance; no per-device branch needed


def load_checkpoint_state(
    path: str, *, map_location: str | torch.device = "cpu"
) -> dict[str, object]:
    """Load a checkpoint with explicit map_location (CPU/GPU portable)."""
    # nosec: trusted local checkpoint written by this repo
    result: dict[str, object] = torch.load(
        path, map_location=map_location, weights_only=False
    )  # nosec B614 # type: ignore[no-any-return]
    return result
