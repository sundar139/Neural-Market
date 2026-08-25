"""Contract-exact GRU deep hedger — v3 INDEXING_REPAIRED.

Implements exactly:
  torch.nn.GRU(input_size=7, hidden_size=64, num_layers=2, dropout=0.0, batch_first=True)
  + nn.Linear(64,1)

Inputs f1..f7 per contract v3 Section 4.1 in exact order.
Action is raw unbounded target delta (no clipping/squashing).
"""

from __future__ import annotations

import torch
from torch import Tensor, nn


class GRUHedger(nn.Module):
    """GRU hedger per v3 contract Section 4.2.

    Architecture frozen prospectively: standard PyTorch GRU semantics
    (sigmoid reset/update, tanh candidate), no custom SiLU gates.
    """

    def __init__(self) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=7,
            hidden_size=64,
            num_layers=2,
            dropout=0.0,
            batch_first=True,
        )
        self.readout = nn.Linear(64, 1)

    def forward(self, x: Tensor) -> Tensor:
        """Forward pass returning raw delta per step.

        Args:
            x: (batch, T, 7) float32 feature sequence, T is maturity M (5-30),
               batch_first True. Variable T handled via caller padding/mask.

        Returns:
            (batch, T) raw target hedge ratio per unit short option, multiplier 1.
            No clipping, no squashing, no tanh*2.
        """
        if x.ndim != 3 or x.shape[2] != 7:
            raise ValueError(f"x must have shape (batch, T, 7), got {tuple(x.shape)}")
        if not torch.isfinite(x).all():
            raise ValueError("input features must be finite")
        # GRU: h0 zeros implicitly (nn.GRU defaults to zeros)
        out, _ = self.gru(x)  # (batch, T, 64)
        delta = self.readout(out).squeeze(-1)  # (batch, T)
        if not torch.isfinite(delta).all():
            raise RuntimeError("non-finite delta produced")
        return delta

    def step(self, x_t: Tensor, h: Tensor) -> tuple[Tensor, Tensor]:
        """Single autoregressive GRU step using SAME nn.GRU and Linear parameters.

        Args:
            x_t: (batch, 7) input at time t
            h: (num_layers, batch, hidden_size) hidden state

        Returns:
            delta_t: (batch,) raw delta at time t
            h_new: (num_layers, batch, hidden_size) new hidden state
        """
        if x_t.ndim != 2 or x_t.shape[1] != 7:
            raise ValueError(f"x_t must have shape (batch, 7), got {tuple(x_t.shape)}")
        if h.ndim != 3 or h.shape[0] != 2 or h.shape[2] != 64:
            raise ValueError(f"h must have shape (2, batch, 64), got {tuple(h.shape)}")
        out, h_new = self.gru(x_t.unsqueeze(1), h)  # (batch,1,7) -> (batch,1,64)
        delta = self.readout(out.squeeze(1)).squeeze(-1)  # (batch,)
        if not torch.isfinite(delta).all():
            raise RuntimeError("non-finite delta produced in step")
        return delta, h_new

    def count_parameters(self) -> int:
        """Deterministic parameter count for artifact reporting."""
        return sum(p.numel() for p in self.parameters())


def build_hedger_features(
    *,
    S: Tensor,  # (batch, M+1) price levels including S[0] inception, float64 or float32
    K: Tensor,  # (batch,) strike
    T_remaining: Tensor | None = None,  # (batch, M) remaining sessions /252 or None to compute
    maturity: Tensor,  # (batch,) M in [5,30]
    prev_delta: Tensor | None = None,  # (batch, M) previous delta, or None for delta_{t-1} with delta_{-1}=0
    cost_level: Tensor,  # (batch,) c in {0.0,0.0010,0.0050}
    option_type: Tensor,  # (batch,) +1 call / -1 put
    delta_sequence: Tensor | None = None,  # (batch, M) current delta for prev_delta derivation
) -> Tensor:
    """Build 7-dim hedger input features f1..f7 per contract v3 Section 4.1.

    This helper is not part of the hedger forward but is used by the runner
    training loop to construct inputs before calling hedger. It is kept here
    for YAGNI reuse and testability.

    Exact ordering: f1 T_t_norm, f2 moneyness, f3 log_moneyness,
    f4 log_return_from_inception, f5 prev_delta, f6 cost_norm, f7 option_type.

    Uses float64 for S/K/T before casting to float32 for features.
    """
    raise NotImplementedError("build_hedger_features is implemented in pnl module to avoid circular import")
