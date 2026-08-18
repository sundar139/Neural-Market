"""Lead-lag path augmentation for variation-sensitive signature features.

Implements a standard discrete lead-lag construction that lifts a scalar
cumulative-return path into a two-channel (lead, lag) path whose local
increments and cross-variation become visible to the truncated signature.

Convention
----------
Given daily log returns r_1, ..., r_H (H values), cumulative returns are::

    c_0 = 0,  c_i = sum(r_1 .. r_i)

The lead-lag augmented path has ``2 + 2H`` points of dimension
``3 + n_context`` (time, lead, lag, context channels):

1. **Origin** — all zeros.
2. **Context point** — time=0, lead=0, lag=0, context channels set to
   the normalised conditioning vector (visible through the first segment
   increment, same mechanism as v2).
3. For each step ``i = 0 .. H-1``:

   a. **Lead advance** — time ``(2i+1)/(2H)``, lead ``c_{i+1}/scale``,
      lag ``c_i/scale``.
   b. **Lag catch** — time ``(2i+2)/(2H)``, lead ``c_{i+1}/scale``,
      lag ``c_{i+1}/scale``.

The lag channel trails the lead channel by one step, so the signature
sees the *difference* between successive cumulative-return values as a
spatial increment rather than a temporal one.  Paths with the same
cumulative displacement but different local variation produce different
lead-lag signatures.
"""

from __future__ import annotations

import torch
from torch import Tensor

from neuralmarket.data.research.sde_windows import WindowSpec

# Path dimension for the lead-lag representation.
# 3 core channels (time, lead, lag) + n_context conditioning channels.
LEADLAG_PATH_DIM_OFFSET = 3  # time + lead + lag


def leadlag_augment_path(
    returns: Tensor,
    normalized_context: Tensor,
    cumret_scale: float,
    spec: WindowSpec | None = None,
) -> Tensor:
    """Lift batched returns into a lead-lag augmented path.

    Args:
        returns: Shape ``(batch, horizon)`` daily log returns.
        normalized_context: Shape ``(batch, n_context)`` training-normalised
            conditioning features.
        cumret_scale: Positive training-derived scale for the cumulative
            log-return channels.
        spec: Window geometry (uses ``horizon``).

    Returns:
        Augmented lead-lag path points of shape
        ``(batch, 2 + 2*horizon, 3 + n_context)``.

    Raises:
        ValueError: If shapes or finite-ness checks fail.
    """
    spec = WindowSpec() if spec is None else spec
    if returns.ndim != 2 or returns.shape[1] != spec.horizon:
        raise ValueError(
            f"returns must have shape (batch, {spec.horizon}), got {tuple(returns.shape)}"
        )
    if normalized_context.ndim != 2 or normalized_context.shape[0] != returns.shape[0]:
        raise ValueError("normalized_context must share the batch dimension with returns")
    if not torch.isfinite(returns).all():
        raise ValueError("returns must be finite")
    if not torch.isfinite(normalized_context).all():
        raise ValueError("normalized_context must be finite")
    if not torch.isfinite(torch.as_tensor(cumret_scale, dtype=returns.dtype)) or cumret_scale <= 0:
        raise ValueError("cumret_scale must be positive and finite")

    batch, horizon = returns.shape
    n_context = normalized_context.shape[1]
    device, dtype = returns.device, returns.dtype
    dim = 3 + n_context
    half = 2 * horizon
    n_points = 2 + half  # origin + context + 2*horizon body points

    path = torch.zeros(batch, n_points, dim, device=device, dtype=dtype)

    # Context point (index 1): set context channels.
    path[:, 1, 3:] = normalized_context

    # Cumulative returns: c_0=0, c_i = cumsum(r)[i-1].
    cumret = torch.cat(
        [torch.zeros(batch, 1, device=device, dtype=dtype), returns.cumsum(dim=1)],
        dim=1,
    )  # (batch, horizon+1)

    half_h = float(half)  # 2 * horizon for time normalization to [0, 1]
    ctx = normalized_context  # (batch, n_context)

    body_start = 2  # first body point index
    for i in range(horizon):
        # Lead advance (odd body index): lead -> c_{i+1}, lag stays at c_i
        idx_a = body_start + 2 * i
        t_a = (2 * i + 1) / half_h
        path[:, idx_a, 0] = t_a
        path[:, idx_a, 1] = cumret[:, i + 1] / cumret_scale
        path[:, idx_a, 2] = cumret[:, i] / cumret_scale
        path[:, idx_a, 3:] = ctx

        # Lag catch (even body index): both at c_{i+1}
        idx_b = body_start + 2 * i + 1
        t_b = (2 * i + 2) / half_h
        path[:, idx_b, 0] = t_b
        path[:, idx_b, 1] = cumret[:, i + 1] / cumret_scale
        path[:, idx_b, 2] = cumret[:, i + 1] / cumret_scale
        path[:, idx_b, 3:] = ctx

    return path
