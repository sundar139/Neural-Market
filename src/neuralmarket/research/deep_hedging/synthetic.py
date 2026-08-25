"""Contract-exact synthetic episode construction — v3 indexing.

Implements exactly:
  dx shape [batch,63] -> 64 levels S[0]..S[63] with S[0]=100.0
  S[j]=S[0]*exp(sum_{i=0}^{j-1} dx_i) for j>=1
  Maturity M 5-30 uses M increments, M+1 levels
  Strike K=S[0]/m, Black-Scholes P0 sigma=0.20 r0 q0 multiplier 1
"""

from __future__ import annotations

import math

import torch
from torch import Tensor


# Frozen synthetic seeds per generator member — contract v3 Section 6.3
SYNTHETIC_SEEDS: dict[str, int] = {
    "seed-01": 42001,
    "seed-02": 42002,
    "seed-04": 42004,
    "seed-05": 42005,
    "reserve-j01": 42006,
}

RUN_PREFIXES: dict[str, str] = {
    "seed-01": "5bdbaabd2fb257a7",
    "seed-02": "62c7406cb3a2c642",
    "seed-04": "77e7de9efabb7ce3",
    "seed-05": "1e8aa171993a1aba",
    "reserve-j01": "38c5113b27568e14",
}

SIGMA_SYNTH: float = 0.20
R_SYNTH: float = 0.0
Q_SYNTH: float = 0.0
S_INCEPTION: float = 100.0
HORIZON: int = 63
DT: float = 1.0 / 252.0


def price_levels_from_increments(
    dx: Tensor,
    *,
    s0: float = S_INCEPTION,
) -> Tensor:
    """Deterministic transformation dx -> S levels.

    Args:
        dx: (batch, 63) daily log-return increments dx_0..dx_62, finite.
        s0: inception price, frozen at 100.0.

    Returns:
        (batch, 64) price levels S[0]..S[63] where S[0]=s0 and
        S[j]=s0*exp(sum_{i=0}^{j-1} dx_i) for j>=1.
        Dtype float64 during cumsum/exp then preserved (caller may cast to float32).
        Device preserved from dx (expected cuda:0 per contract, but CPU allowed in tests).
        Positivity via exp, no clipping.
    """
    if dx.ndim != 2 or dx.shape[1] != HORIZON:
        raise ValueError(f"dx must have shape (batch, {HORIZON}), got {tuple(dx.shape)}")
    if not torch.isfinite(dx).all():
        raise ValueError("dx must be finite")
    # Use float64 for cumsum/exp as contract specifies
    dx64 = dx.to(dtype=torch.float64)
    # Pad S[0] inception then compute S[1..63]
    # X_j = sum_{i=0}^{j-1} dx_i for j>=1, X_0=0
    # S[j] = s0 * exp(X_j)
    cumsum = torch.cumsum(dx64, dim=1)  # (batch,63) where cumsum[:,j-1]=sum_{i=0}^{j-1} dx_i for j>=1
    # S[0] = s0
    s0_col = torch.full((dx.shape[0], 1), float(s0), dtype=torch.float64, device=dx.device)
    s_levels = torch.cat(
        [s0_col, s0_col * torch.exp(cumsum)],
        dim=1,
    )  # (batch,64)
    if not torch.isfinite(s_levels).all():
        raise RuntimeError("non-finite price levels")
    if torch.any(s_levels <= 0):
        raise RuntimeError("non-positive price level (exp positivity violated)")
    return s_levels


def episode_price_series(
    dx: Tensor,
    maturity: Tensor | int,
    *,
    s0: float = S_INCEPTION,
) -> Tensor:
    """Slice M+1 levels for episode maturity M.

    Args:
        dx: (batch,63) or (63,) increments
        maturity: scalar or (batch,) M in [5,30]
        s0: inception 100.0

    Returns:
        If dx is (batch,63) and maturity is (batch,): returns list of tensors
        each (M+1,) variable length (caller handles padding). For simplicity
        this helper returns (batch, max_M+1) padded with nan for batch case.
        For scalar maturity, returns (batch, M+1) or (M+1,) .
    """
    # This helper is intentionally minimal; training loop slices directly.
    raise NotImplementedError("episode slicing is done inline in runner to keep API minimal")


def black_scholes_p0(
    *,
    s0: float | Tensor = S_INCEPTION,
    strike: Tensor,
    maturity: Tensor | int,
    option_type: Tensor,  # +1 call, -1 put
    sigma: float = SIGMA_SYNTH,
    r: float = R_SYNTH,
    q: float = Q_SYNTH,
) -> Tensor:
    """Black-Scholes synthetic P0 — contract v3 Section 6.1.

    Call: C = S*exp(-qT)*N(d1) - K*exp(-rT)*N(d2)
    Put : P = K*exp(-rT)*N(-d2) - S*exp(-qT)*N(-d1)
    With r=0,q=0 discount 1: C = S*N(d1)-K*N(d2), P=K*N(-d2)-S*N(-d1)
    d1 = (ln(S/K) + 0.5 sigma^2 T)/(sigma sqrt(T)), d2=d1 - sigma sqrt(T)
    At T=0: C=max(S-K,0), P=max(K-S,0).

    All per multiplier 1. Deterministic, finite for sigma=0.20, T>0, m in [0.90,1.10].

    Args:
        s0: 100.0 inception
        strike: (batch,) K
        maturity: scalar or (batch,) M in [5,30] -> T=M/252
        option_type: (batch,) +1/-1
        sigma: 0.20
        r: 0.0
        q: 0.0

    Returns:
        (batch,) P0 premium, finite, deterministic.
    """
    if isinstance(maturity, int):
        # broadcast to strike shape
        maturity_t = torch.full_like(strike, float(maturity), dtype=torch.float64)
    elif isinstance(maturity, Tensor) and maturity.ndim == 0:
        maturity_t = torch.full_like(strike, float(maturity.item()), dtype=torch.float64)
    elif isinstance(maturity, Tensor):
        maturity_t = maturity.to(dtype=torch.float64)
        if maturity_t.shape != strike.shape:
            # scalar per batch but strike is (batch,) -> maturity must broadcast
            if maturity_t.numel() == 1:
                maturity_t = maturity_t.expand_as(strike)
    else:
        raise ValueError(f"unsupported maturity type {type(maturity)}")

    s0_t = torch.as_tensor(s0, dtype=torch.float64, device=strike.device).expand_as(strike)
    k = strike.to(dtype=torch.float64)
    opt = option_type.to(dtype=torch.float64)
    t = maturity_t / 252.0  # T = M/252

    # Handle T==0 case (should not occur for M>=5, but included for completeness)
    p0 = torch.empty_like(k, dtype=torch.float64)

    # T>0 mask
    mask_pos = t > 0
    mask_zero = ~mask_pos

    if mask_pos.any():
        s_pos = s0_t[mask_pos]
        k_pos = k[mask_pos]
        t_pos = t[mask_pos]
        # sigma>0 always (0.20)
        sqrt_t = torch.sqrt(t_pos)
        d1 = (torch.log(s_pos / k_pos) + 0.5 * sigma * sigma * t_pos) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t
        # Normal CDF via erf
        def norm_cdf(x: Tensor) -> Tensor:
            return 0.5 * (1.0 + torch.erf(x / math.sqrt(2.0)))

        n_d1 = norm_cdf(d1)
        n_d2 = norm_cdf(d2)
        n_minus_d1 = norm_cdf(-d1)
        n_minus_d2 = norm_cdf(-d2)
        call = s_pos * n_d1 - k_pos * n_d2  # r=0 q=0
        put = k_pos * n_minus_d2 - s_pos * n_minus_d1
        is_call = opt[mask_pos] > 0
        p0_pos = torch.where(is_call, call, put)
        p0[mask_pos] = p0_pos

    if mask_zero.any():
        s_z = s0_t[mask_zero]
        k_z = k[mask_zero]
        is_call_z = opt[mask_zero] > 0
        p0_z = torch.where(is_call_z, torch.clamp(s_z - k_z, min=0), torch.clamp(k_z - s_z, min=0))
        p0[mask_zero] = p0_z

    if not torch.isfinite(p0).all():
        raise RuntimeError("non-finite P0 (check K>0)")

    return p0


def construct_episode(
    *,
    dx: Tensor,  # (63,) single path increments
    maturity: int,  # M in [5,30]
    moneyness: float,  # m = S[0]/K in [0.90,1.10]
    option_type: int,  # +1 call, -1 put
) -> dict[str, Tensor | float | int]:
    """Construct single synthetic episode from increments (deterministic fixture).

    Not used for real 50k campaign; used for tiny deterministic fixtures in tests.
    Returns dict with S_series (M+1,), K, P0, etc.

    Args:
        dx: (63,) increments
        maturity: M
        moneyness: m
        option_type: +1/-1

    Returns:
        dict with keys: s_series (Tensor M+1), s0, k, m, maturity, option_type, p0
    """
    if dx.shape != (HORIZON,):
        raise ValueError(f"dx must be (63,), got {tuple(dx.shape)}")
    if not 5 <= maturity <= 30:
        raise ValueError(f"maturity must be in [5,30], got {maturity}")
    if not 0.90 <= moneyness <= 1.10:
        raise ValueError(f"moneyness out of range {moneyness}")
    if option_type not in (1, -1):
        raise ValueError(f"option_type must be +1/-1, got {option_type}")

    s0 = S_INCEPTION
    k = s0 / moneyness
    # Price levels
    levels = price_levels_from_increments(dx.unsqueeze(0), s0=s0).squeeze(0)  # (64,)
    s_series = levels[: maturity + 1]  # S[0]..S[M] inclusive, M+1 levels
    # P0
    p0 = black_scholes_p0(
        s0=s0,
        strike=torch.tensor([k], dtype=torch.float64),
        maturity=torch.tensor([maturity], dtype=torch.float64),
        option_type=torch.tensor([option_type], dtype=torch.float64),
    ).item()
    return {
        "s_series": s_series,
        "s0": s0,
        "k": k,
        "moneyness": moneyness,
        "maturity": maturity,
        "option_type": option_type,
        "p0": p0,
    }
