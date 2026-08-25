"""Contract-exact empirical CVaR_0.95 — harness v3 Section 4B.

Reuse harness-v3 fractional-tail semantics. Differentiable via torch.sort
with autograd intact. No NumPy/SciPy/detached floats in training path.
"""

from __future__ import annotations

import torch
from torch import Tensor


def empirical_cvar(
    losses: Tensor,
    *,
    alpha: float = 0.95,
) -> Tensor:
    """Fractional-tail empirical CVaR / Expected Shortfall.

    Implements exactly harness v3 Section 4B:
      alpha=0.95, tail_mass=(1-alpha)*N, k=floor(tail_mass), f=tail_mass-k,
      CVaR = [sum_{i=N-k+1}^{N} x_(i) + f * x_(N-k)] / tail_mass
      where x_(i) are losses sorted ascending, 1-indexed.

    Cases:
      tail_mass <=0: insufficient (N=0) -> raises
      k==0 and f>0 (N<20): CVaR = max loss (single largest)
      k>=1 and f==0: mean of k largest
      k>=0 and f>0: weighted tail with fractional boundary

    Ties retained as distinct observations via stable sort.
    Autograd preserved (torch.sort is differentiable via gathering).

    Args:
        losses: (N,) 1-D tensor of hedging losses L = -P&L, finite, on any device.
        alpha: risk level, frozen at 0.95 for training/selection.

    Returns:
        scalar tensor CVaR_0.95 (differentiable, requires_grad follows inputs).
    """
    if losses.ndim != 1:
        raise ValueError(f"losses must be 1-D, got shape {tuple(losses.shape)}")
    n = losses.numel()
    if n == 0:
        raise ValueError("CVaR requires N>=1")
    if not torch.isfinite(losses).all():
        raise ValueError("CVaR losses must be finite (pre-filter nonfinite episodes)")
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0,1), got {alpha}")

    tail_mass = (1.0 - alpha) * float(n)
    if tail_mass <= 0:
        raise ValueError(f"insufficient tail mass {tail_mass} for N={n} alpha={alpha}")

    k = int(tail_mass // 1)  # floor
    f = tail_mass - float(k)

    # Stable sort ascending; ties retain empirical mass order
    sorted_losses, _ = torch.sort(losses, stable=True)

    # Use differentiable indexing
    if k == 0 and f > 0:
        # N < 20 case: tail_mass <1, single largest
        return sorted_losses[-1]
    if k >= 1 and f == 0:
        # Exact k tail
        tail = sorted_losses[n - k :]
        return tail.mean()
    # k>=0 and f>0: fractional boundary
    # sum of k largest (empty if k==0) + f * boundary
    if k == 0:
        # only fractional part of boundary (N-k == N, but we need x_(N)??)
        # Definition: CVaR = [sum_{k largest} + f * x_(N-k)] / tail_mass
        # When k==0, sum is empty, boundary is x_(N)?? Wait N-k = N, but indexing 1..N
        # For k==0, boundary is x_(N) (largest)?? No, x_(N-k)=x_(N) when k=0.
        # But then we have f * x_(N) / tail_mass with tail_mass=f, so = x_(N).
        # Consistent. For our N<20 branch we already handled k==0 and f>0 as max,
        # but this path would give same result. Keep unified formula:
        # boundary is sorted_losses[n - k -1] = sorted_losses[n-1] when k==0
        boundary = sorted_losses[n - k - 1]  # n-1 when k=0
        return boundary  # tail_mass == f, so f*boundary / tail_mass == boundary
    # k>=1 and f>0
    # boundary is x_(N-k) = sorted_losses[n - k -1] (0-indexed)
    boundary = sorted_losses[n - k - 1]
    tail = sorted_losses[n - k :]  # k largest
    tail_sum = tail.sum()
    # keep autograd: use tensor ops, not Python floats that detach
    # tail_mass, f are Python floats but multiplications are with tensors -> autograd ok
    # Use tensor scalar for division to preserve grad
    cvar = (tail_sum + f * boundary) / tail_mass
    return cvar


def cvar_full_set_selection(losses: Tensor, *, alpha: float = 0.95) -> Tensor:
    """Selection metric: ONE CVaR over complete 10,000 selection set.

    This is NOT mean of minibatch CVaRs. Caller must collect all
    `losses` for the full selection set (10,000) then call once.

    Args:
        losses: (N,) where N==10000 expected (but generic N supported for tests).
        alpha: 0.95

    Returns:
        scalar CVaR over complete set.
    """
    return empirical_cvar(losses, alpha=alpha)
