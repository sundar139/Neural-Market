"""Device-aware helpers for trainer tensor/generator construction.

Centralises the single rule: every factory that creates storage must
receive the resolved torch.device explicitly. No per-call .cuda().

Generator handling
------------------
torch.Generator(device) is the correct form on CUDA. On CPU the same
call works but is equivalent to the no-arg constructor. This helper
keeps one canonical path so audits have a single grep target.

Tensor factories
----------------
Only the factories that actually appear on the governed training path
are wrapped here. Each wrapper forces the caller to supply device.
"""

from __future__ import annotations

import torch
from torch import Tensor


def make_generator(device: torch.device, seed: int) -> torch.Generator:
    """Create a seeded generator bound to ``device``.

    Args:
        device: Resolved device (cpu or cuda).
        seed: Deterministic seed.

    Returns:
        Seeded torch.Generator on ``device``.
    """
    # torch.Generator(device=...) is supported for both cpu and cuda
    # on modern PyTorch; fall back gracefully for older CPU-only builds.
    try:
        gen = torch.Generator(device=device)
    except Exception:
        gen = torch.Generator()
    gen.manual_seed(seed)
    return gen


def randn_on_device(
    *size: int,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
    generator: torch.Generator | None = None,
) -> Tensor:
    """torch.randn with explicit device + dtype, no silent default."""
    if generator is not None:
        return torch.randn(*size, device=device, dtype=dtype, generator=generator)
    return torch.randn(*size, device=device, dtype=dtype)


def tensor_on_device(
    data: object,
    *,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> Tensor:
    """torch.tensor with explicit device + dtype."""
    return torch.tensor(data, device=device, dtype=dtype)


def full_on_device(
    size: tuple[int, ...] | list[int],
    fill_value: float,
    *,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> Tensor:
    """torch.full with explicit device + dtype."""
    return torch.full(size, fill_value, device=device, dtype=dtype)


def zeros_on_device(
    *size: int,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> Tensor:
    """torch.zeros with explicit device + dtype."""
    return torch.zeros(*size, device=device, dtype=dtype)


def ones_on_device(
    *size: int,
    device: torch.device,
    dtype: torch.dtype = torch.float32,
) -> Tensor:
    """torch.ones with explicit device + dtype."""
    return torch.ones(*size, device=device, dtype=dtype)
