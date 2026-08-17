"""Truncated signature features and expected-signature MMD for neural-SDE training.

Implements the FROZEN FALLBACK signature representation for the
signature-score neural SDE: a basepoint- and time-augmented path whose
truncated signature (levels 1..3) is computed exactly for piecewise-linear
paths using Chen's identity.  This is a finite-level signature-kernel
approximation -- NOT the exact infinite-level signature kernel -- and is
labelled as such in code and reports.

Path augmentation
----------------
Each generated or real target path is lifted from (horizon,) returns to
``(n_points, 1 + 1 + n_context)`` coordinates:

1. a leading origin/basepoint (all zeros);
2. a context point at time 0 that carries the normalized conditioning vector
   (normalized by training-fitted parameters) and stays constant for the rest
   of the path;
3. the time-augmented, scale-normalized cumulative log return: coordinate 0
   is normalized time in ``[0, 1]`` and coordinate 1 is the cumulative log
   return divided by a training-derived scale.

The constant context channel is made visible to the signature by placing it in
the initial path point (after the origin), so the first segment's increment
carries the context into every level of the signature.
"""

from __future__ import annotations

import torch
from torch import Tensor

from neuralmarket.data.research.sde_windows import WindowSpec


def augment_path(
    returns: Tensor,
    normalized_context: Tensor,
    cumret_scale: float,
    spec: WindowSpec | None = None,
) -> Tensor:
    """Lift batched returns into basepoint+context+time augmented path points.

    Args:
        returns: Shape ``(batch, horizon)`` daily log returns (or increments).
        normalized_context: Shape ``(batch, n_context)`` training-normalized
            conditioning features, constant along each path.
        cumret_scale: Positive training-derived scale for the cumulative
            log-return channel.
        spec: Window geometry (uses ``dt`` and ``horizon``).

    Returns:
        Augmented path points of shape ``(batch, horizon + 2, 2 + n_context)``.

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

    t = torch.arange(1, horizon + 1, device=device, dtype=dtype).unsqueeze(0) / float(horizon)
    t = t.expand(batch, horizon)
    cumret = returns.cumsum(dim=1) / cumret_scale
    ctx = normalized_context.unsqueeze(1).expand(batch, horizon, n_context)

    origin = torch.zeros(batch, 1, 2 + n_context, device=device, dtype=dtype)
    context_point = torch.zeros(batch, 1, 2 + n_context, device=device, dtype=dtype)
    context_point[:, :, 2:] = normalized_context.unsqueeze(1)
    body = torch.cat((t.unsqueeze(-1), cumret.unsqueeze(-1), ctx), dim=2)
    return torch.cat((origin, context_point, body), dim=1)


def truncated_signature_features(points: Tensor, level: int = 3) -> dict[int, Tensor]:
    """Exact truncated signature (levels 1..level) of piecewise-linear paths.

    Uses the segment exponential ``exp(dx) = sum_k dx^k / k!`` for each linear
    segment and composes segments with Chen's identity (concatenation product
    in the truncated tensor algebra).  Because the algebra product truncated
    at a fixed level depends only on factors' components up to that level,
    the result equals the exact level-``level`` truncation of each path's
    signature.

    Args:
        points: Shape ``(batch, n_points, dim)`` path coordinates.
        level: Maximum signature level (1-3).

    Returns:
        Mapping ``{k: tensor of shape (batch, dim**k)}`` for ``k = 1..level``.

    Raises:
        ValueError: If the level is unsupported or the input is malformed.
    """
    if level not in (1, 2, 3):
        raise ValueError("truncated signature supports levels 1..3")
    if points.ndim != 3 or points.shape[1] < 2:
        raise ValueError("points must have shape (batch, n_points >= 2, dim)")
    if not torch.isfinite(points).all():
        raise ValueError("points must be finite")

    dx = torch.diff(points, dim=1)
    batch, n_segments, dim = dx.shape
    device, dtype = dx.device, dx.dtype

    # Segment exponentials truncated at `level`.
    seg1 = dx  # (B, N, d)
    seg2 = torch.einsum("bni,bnj->bnij", dx, dx) / 2.0
    seg3 = torch.einsum("bni,bnj,bnk->bnijk", dx, dx, dx) / 6.0

    # Running truncated signature accumulator (starts at the identity).
    acc1 = torch.zeros(batch, dim, device=device, dtype=dtype)
    acc2 = torch.zeros(batch, dim, dim, device=device, dtype=dtype)
    acc3 = torch.zeros(batch, dim, dim, dim, device=device, dtype=dtype)

    for t_seg in range(n_segments):
        b1 = seg1[:, t_seg, :]
        b2 = seg2[:, t_seg, :, :]
        b3 = seg3[:, t_seg, :, :, :]
        # Chen / concatenation product: (ab)^I = sum over prefixes J of I.
        c1 = acc1 + b1
        c2 = acc2 + torch.einsum("bi,bj->bij", acc1, b1) + b2
        c3 = (
            acc3
            + torch.einsum("bi,bjk->bijk", acc1, b2)
            + torch.einsum("bij,bk->bijk", acc2, b1)
            + b3
        )
        acc1, acc2, acc3 = c1, c2, c3

    features: dict[int, Tensor] = {1: acc1.reshape(batch, -1)}
    if level >= 2:
        features[2] = acc2.reshape(batch, -1)
    if level >= 3:
        features[3] = acc3.reshape(batch, -1)
    return features


def signature_mmd(real: dict[int, Tensor], generated: dict[int, Tensor]) -> Tensor:
    """Expected-signature MMD with a finite-level linear signature kernel.

    For each level, computes the mean signature feature over the batch for the
    real and generated paths, takes the squared Euclidean distance between the
    two means, and sums the per-level losses with equal weight.  The empty
    (level-0) term is omitted because both sides always start at the same
    basepoint, so it contributes zero.

    Args:
        real: Truncated signature features of the real batch.
        generated: Truncated signature features of the generated batch.

    Returns:
        A scalar tensor with ``grad_fn`` into the generated paths.

    Raises:
        ValueError: If the two feature dicts disagree on levels or batch size.
    """
    if set(real) != set(generated):
        raise ValueError("signature feature level sets must match")
    batch = next(iter(real.values())).shape[0]
    dtype0 = next(iter(real.values())).dtype
    device0 = next(iter(real.values())).device
    total = torch.zeros((), dtype=dtype0, device=device0)
    for level in sorted(real):
        r = real[level]
        g = generated[level]
        if r.shape[0] != batch or g.shape[0] != batch:
            raise ValueError("signature feature batch sizes must match")
        total = total + torch.mean((r.mean(dim=0) - g.mean(dim=0)) ** 2)
    return total
