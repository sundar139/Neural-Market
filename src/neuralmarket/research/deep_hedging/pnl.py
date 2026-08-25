"""Contract-exact hedging P&L — v3 Section 5.1 and 6.1.

Implements:
  P&L = P0 + sum_{t=1}^{M} delta_{t-1}*(S[t]-S[t-1]) - Payoff_M - sum costs
  costs: c*|delta_t - delta_{t-1}|*S[t] with delta_{-1}=0, includes
  initial hedge cost at S[0], daily rebalance, single terminal unwind at S[M].
  Final position 0.
  Multiplier 1 everywhere.
"""

from __future__ import annotations

import torch
from torch import Tensor


def hedging_pnl(
    *,
    delta: Tensor,  # (batch, M) hedge ratios delta_0..delta_{M-1} (or (M,) single)
    s_levels: Tensor,  # (batch, M+1) or (batch,M+1) S[0]..S[M] including inception
    p0: Tensor,  # (batch,) synthetic premium
    strike: Tensor,  # (batch,) K
    option_type: Tensor,  # (batch,) +1 call / -1 put
    cost_level: Tensor | float,  # (batch,) c in {0,0.0010,0.0050} or scalar
) -> Tensor:
    """Differentiable hedging P&L per episode.

    All inputs are per episode. `delta` is the GRU raw output (requires_grad).
    Transaction costs use `torch.abs` which is differentiable except at 0 (ok).
    Payoff and underlying moves are constants w.r.t. delta (no grad needed).

    Single terminal unwind: liquidate delta_{M-1} to 0 at S[M] charging
    c*|0 - delta_{M-1}|*S[M]. No extra ordinary rebalance at M beyond holding
    delta_{M-1} into final interval.

    Args:
        delta: (batch, M) or (M,) hedge ratios. If 1-D, treated as single episode.
        s_levels: (batch, M+1) or (M+1,) price levels S[0]..S[M]. S[0]=100.0 inception.
        p0: (batch,) or scalar premium.
        strike: (batch,) K
        option_type: (batch,) +1/-1
        cost_level: (batch,) or scalar c

    Returns:
        (batch,) P&L per episode (differentiable w.r.t. delta).

    Raises:
        ValueError if shapes inconsistent or non-finite.
    """
    # Normalize to batch dim
    is_single = delta.ndim == 1
    if is_single:
        delta = delta.unsqueeze(0)  # (1,M)
        s_levels = s_levels.unsqueeze(0) if s_levels.ndim == 1 else s_levels
        # p0 etc. will be broadcast

    if delta.ndim != 2 or s_levels.ndim != 2:
        raise ValueError(f"delta {tuple(delta.shape)} s_levels {tuple(s_levels.shape)} must be 2-D batch")
    b, m = delta.shape
    if s_levels.shape != (b, m + 1):
        raise ValueError(f"s_levels must be (batch, M+1) with M={m}, got {tuple(s_levels.shape)}")
    if not torch.isfinite(delta).all() or not torch.isfinite(s_levels).all():
        raise ValueError("delta and s_levels must be finite")

    # Cost level tensor
    if isinstance(cost_level, (float, int)):
        c = torch.full((b,), float(cost_level), dtype=s_levels.dtype, device=s_levels.device)
    else:
        c = cost_level.to(dtype=s_levels.dtype, device=s_levels.device)
        if c.ndim == 0:
            c = c.expand(b)
        if c.shape != (b,):
            raise ValueError(f"cost_level shape {tuple(c.shape)} != (batch,)")
    # p0, strike, option_type
    def to_batch(t: Tensor | float, name: str) -> Tensor:
        if isinstance(t, (float, int)):
            return torch.full((b,), float(t), dtype=s_levels.dtype, device=s_levels.device)
        t = torch.as_tensor(t, dtype=s_levels.dtype, device=s_levels.device)
        if t.ndim == 0:
            return t.expand(b)
        if t.shape != (b,):
            raise ValueError(f"{name} shape {tuple(t.shape)} != (batch,)")
        return t

    p0_b = to_batch(p0, "p0")
    k_b = to_batch(strike, "strike")
    opt_b = to_batch(option_type, "option_type")

    # Underlying P&L: sum_{t=1}^{M} delta_{t-1}*(S[t]-S[t-1])
    # delta_{t} corresponds to position held from S[t] to S[t+1] ???
    # Contract v3: initial hedge delta_0 at S[0], first interval delta_0*(S[1]-S[0]),
    # final interval delta_{M-1}*(S[M]-S[M-1]). So delta[t-1] pairs with S[t]-S[t-1].
    ds = s_levels[:, 1:] - s_levels[:, :-1]  # (batch, M) where ds[:,t-1]=S[t]-S[t-1]
    underlying_pnl = (delta * ds).sum(dim=1)  # (batch,)

    # Payoff at S[M]
    s_m = s_levels[:, -1]  # (batch,)
    is_call = opt_b > 0
    payoff = torch.where(is_call, torch.clamp(s_m - k_b, min=0.0), torch.clamp(k_b - s_m, min=0.0))

    # Transaction costs: c*|delta_t - delta_{t-1}|*S[t] with delta_{-1}=0
    # delta_0 - 0 at S[0], delta_t - delta_{t-1} at S[t] for t>=1, unwind at S[M]
    # We have delta shape (batch,M) for t=0..M-1, and s_levels shape (batch,M+1)
    # Costs: for t=0: c*|delta_0|*S[0]
    #        for t=1..M-1: c*|delta_t - delta_{t-1}|*S[t]
    #        unwind: c*|0 - delta_{M-1}|*S[M]
    # Combined: sum_{t=0}^{M-1} c*|delta_t - delta_{t-1}|*S[t] + c*|delta_{M-1}|*S[M] where delta_{-1}=0
    # Note S[t] for t=0..M-1 corresponds to s_levels[:,t], S[M] is s_levels[:,-1]
    costs = torch.zeros(b, dtype=s_levels.dtype, device=s_levels.device)
    prev = torch.zeros(b, dtype=s_levels.dtype, device=s_levels.device)
    for t in range(m):
        ct = c * torch.abs(delta[:, t] - prev) * s_levels[:, t]
        costs = costs + ct
        prev = delta[:, t]
    # Unwind
    unwind = c * torch.abs(prev) * s_levels[:, -1]  # |0 - delta_{M-1}|*S[M]
    costs = costs + unwind

    pnl = p0_b + underlying_pnl - payoff - costs
    if not torch.isfinite(pnl).all():
        raise RuntimeError("non-finite P&L")
    if is_single:
        return pnl.squeeze(0) if pnl.numel() == 1 else pnl
    return pnl


def build_features(
    *,
    s_levels: Tensor,  # (batch, M+1) S[0]..S[M]
    strike: Tensor,  # (batch,)
    maturity: Tensor,  # (batch,) M
    cost_level: Tensor,  # (batch,) c
    option_type: Tensor,  # (batch,) +1/-1
    delta_prev: Tensor | None = None,  # unused; kept for API
    delta_sequence: Tensor | None = None,  # not needed for feature build before hedging
) -> Tensor:
    """Build GRU input features f1..f7 for each step t=0..M-1.

    Uses S[t] at step t (S[0] for delta_0, ..., S[M-1] for delta_{M-1}).
    T_t = remaining sessions to expiry /252 = (M - t)/252? Actually
    T_t = (M - t)/252 for t=0..M-1 where at t=M-1 remaining is 1 session
    before expiry, at expiry T=0 but hedging ends at M. For simplicity
    contracts define T_t = remaining /252 with remaining = M - t.

    f1 = T_t_norm = T_t *252/30 = (M - t)/30
    f2 = S[t]/K
    f3 = ln(S[t]/K)
    f4 = ln(S[t]/S[0])
    f5 = prev_delta (delta_{t-1} with delta_{-1}=0)
    f6 = c/0.0050
    f7 = option_type

    This function returns features for hedging loop; delta feedback for f5
    is handled by caller iteratively or pre-filled with zeros for
    initial step (training loop feeds previous delta).

    Args:
        s_levels: (batch, M+1) S[0]..S[M]
        strike: (batch,)
        maturity: (batch,) M
        cost_level: (batch,) c
        option_type: (batch,) +1/-1

    Returns:
        (batch, M, 7) float32 features.
    """
    b, mp1 = s_levels.shape
    m = mp1 - 1
    if strike.shape != (b,) or maturity.shape != (b,) or cost_level.shape != (b,) or option_type.shape != (b,):
        raise ValueError("batch shapes mismatch")
    # Expand per-step S[t] for t=0..M-1
    s_t = s_levels[:, :-1]  # (batch, M) S[0]..S[M-1]
    s0 = s_levels[:, 0:1]  # (batch,1) S[0]
    k = strike.unsqueeze(1)  # (batch,1)
    # T_t_norm = (M - t)/30
    t_idx = torch.arange(m, device=s_levels.device, dtype=s_levels.dtype)  # (M,)
    # maturity (batch,) -> (batch,M)
    m_exp = maturity.unsqueeze(1).to(dtype=s_levels.dtype)  # (batch,1)
    t_t_norm = (m_exp - t_idx) / 30.0  # (batch,M) where t=0 -> M/30, t=M-1 ->1/30
    # Clamp to [0,1] (max M=30 -> 1.0, min 5 -> ~0.033)
    # f2,f3,f4 via S[t]
    moneyness = s_t / k  # (batch,M)
    log_moneyness = torch.log(moneyness)
    log_return = torch.log(s_t / s0)  # (batch,M), at t=0 log(1)=0
    # f5 prev_delta: delta_{-1}=0 for t=0, else caller fills; here we return 0 for all t
    # Actual training loop will autoregressively fill f5.
    prev_delta = torch.zeros_like(s_t)  # placeholder
    cost_norm = (cost_level / 0.0050).unsqueeze(1).expand(-1, m)  # (batch,M)
    opt_type = option_type.unsqueeze(1).expand(-1, m).to(dtype=s_levels.dtype)  # (batch,M)

    feats = torch.stack(
        [t_t_norm, moneyness, log_moneyness, log_return, prev_delta, cost_norm, opt_type],
        dim=-1,
    )  # (batch,M,7)
    # Cast to float32 for hedger (contract says float32 features, float64 for S/K/T before)
    feats = feats.to(dtype=torch.float32)
    if not torch.isfinite(feats).all():
        raise ValueError("non-finite features")
    return feats
