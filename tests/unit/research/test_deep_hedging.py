"""Non-scientific unit tests for v3 deep-hedging implementation — Task 202.

Uses tiny deterministic synthetic fixtures only. No real 50k campaign, no final-test.
"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from neuralmarket.research.deep_hedging.artifacts import (
    completeness_check,
    global_failure_check,
    policy_checkpoint_path,
    synthetic_dataset_path,
)
from neuralmarket.research.deep_hedging.cvar import cvar_full_set_selection, empirical_cvar
from neuralmarket.research.deep_hedging.hedger import GRUHedger
from neuralmarket.research.deep_hedging.pnl import hedging_pnl
from neuralmarket.research.deep_hedging.runner import (
    ArtifactExistsError,
    AuthorizationError,
    check_artifact_nonexistence,
    require_authorization_or_refuse,
)
from neuralmarket.research.deep_hedging.synthetic import (
    S_INCEPTION,
    black_scholes_p0,
    construct_episode,
    price_levels_from_increments,
)


# ---------------------------------------------------------------------------
# Synthetic indexing: 63 -> 64, M -> M+1, dx_0 maps, dx_M excluded
# ---------------------------------------------------------------------------

def test_price_levels_63_to_64() -> None:
    dx = torch.zeros(2, 63, dtype=torch.float64)
    levels = price_levels_from_increments(dx)
    assert levels.shape == (2, 64)
    assert torch.allclose(levels[:, 0], torch.full((2,), S_INCEPTION, dtype=torch.float64))
    # all 100 when dx=0
    assert torch.allclose(levels, torch.full((2, 64), 100.0, dtype=torch.float64))


def test_m_increments_to_m_plus_one_levels() -> None:
    for m in [5, 10, 30]:
        dx = torch.randn(1, 63, dtype=torch.float64)
        levels = price_levels_from_increments(dx)  # (1,64)
        s_series = levels[0, : m + 1]
        assert s_series.shape == (m + 1,)
        assert s_series[0].item() == 100.0
        # Verify S[1] = 100*exp(dx_0)
        expected_s1 = 100.0 * math.exp(dx[0, 0].item())
        assert math.isclose(s_series[1].item(), expected_s1, rel_tol=1e-12)


def test_dx0_maps_s0_to_s1() -> None:
    dx = torch.tensor([[0.05] + [0.0] * 62], dtype=torch.float64)
    levels = price_levels_from_increments(dx)
    assert math.isclose(levels[0, 1].item(), 100.0 * math.exp(0.05), rel_tol=1e-12)
    assert levels[0, 0].item() == 100.0


def test_dx_m_excluded() -> None:
    # For M=5, use dx_5..dx_62 should not affect S[0]..S[5]
    dx = torch.zeros(1, 63, dtype=torch.float64)
    dx[0, 5] = 0.5  # should be excluded for M=5
    levels = price_levels_from_increments(dx)
    s_5 = levels[0, :6]  # M=5 -> 6 levels S[0]..S[5]
    # S[5] uses sum dx_0..dx_4, not dx_5
    assert math.isclose(s_5[5].item(), 100.0, rel_tol=1e-12)  # since dx_0..dx_4 are 0
    # but S[6] would include dx_5
    assert not math.isclose(levels[0, 6].item(), 100.0)


# ---------------------------------------------------------------------------
# P&L first/final interval, single terminal unwind, payoff, P0 determinism
# ---------------------------------------------------------------------------

def test_pnl_first_final_interval_and_unwind() -> None:
    # Tiny fixture: M=5, batch 1, S[0]=100, linear price
    s_levels = torch.tensor([[100.0, 101.0, 102.0, 103.0, 104.0, 105.0]], dtype=torch.float64)
    delta = torch.tensor([[0.5, 0.5, 0.5, 0.5, 0.5]], dtype=torch.float64)  # M=5
    p0 = torch.tensor([5.0], dtype=torch.float64)
    strike = torch.tensor([100.0], dtype=torch.float64)
    opt_type = torch.tensor([1.0], dtype=torch.float64)  # call
    cost = 0.0
    pnl = hedging_pnl(delta=delta, s_levels=s_levels, p0=p0, strike=strike, option_type=opt_type, cost_level=cost)
    # Manual: underlying = 0.5*(1+1+1+1+1)=2.5, payoff = max(105-100)=5, costs 0, p0 5 => pnl=5+2.5-5=2.5
    assert math.isclose(pnl.item(), 2.5, rel_tol=1e-12)


def test_pnl_single_terminal_unwind_no_double_charge() -> None:
    # No unwind double count: costs should be c*|delta_0|*S0 + ... + c*|delta_M-1|*S[M] (unwind)
    s_levels = torch.tensor([[100.0, 100.0, 100.0]], dtype=torch.float64)  # M=2
    delta = torch.tensor([[1.0, 1.0]], dtype=torch.float64)
    p0 = torch.tensor([0.0], dtype=torch.float64)
    strike = torch.tensor([100.0], dtype=torch.float64)
    opt_type = torch.tensor([1.0], dtype=torch.float64)
    c = 0.001
    pnl = hedging_pnl(delta=delta, s_levels=s_levels, p0=p0, strike=strike, option_type=opt_type, cost_level=c)
    # underlying 0, payoff 0, costs: |1|*100*0.001=0.1 at S0, |0|*100*0.001=0 at S1, unwind |1|*100*0.001=0.1 at S2 => total 0.2
    # pnl = -0.2
    assert math.isclose(pnl.item(), -0.2, rel_tol=1e-12)


def test_call_put_payoff() -> None:
    # Call payoff
    s_levels = torch.tensor([[100.0, 110.0]], dtype=torch.float64)  # M=1
    delta = torch.tensor([[0.0]], dtype=torch.float64)
    p0 = torch.tensor([0.0], dtype=torch.float64)
    strike = torch.tensor([100.0], dtype=torch.float64)
    for opt, expected_payoff in [(1, 10.0), (-1, 0.0)]:
        opt_t = torch.tensor([float(opt)], dtype=torch.float64)
        pnl = hedging_pnl(delta=delta, s_levels=s_levels, p0=p0, strike=strike, option_type=opt_t, cost_level=0.0)
        assert math.isclose(-pnl.item(), expected_payoff, rel_tol=1e-12)  # pnl = -payoff
    # Put payoff
    s_levels2 = torch.tensor([[100.0, 90.0]], dtype=torch.float64)
    for opt, expected_payoff in [(1, 0.0), (-1, 10.0)]:
        opt_t = torch.tensor([float(opt)], dtype=torch.float64)
        pnl = hedging_pnl(delta=delta, s_levels=s_levels2, p0=p0, strike=strike, option_type=opt_t, cost_level=0.0)
        assert math.isclose(-pnl.item(), expected_payoff, rel_tol=1e-12)


def test_synthetic_p0_determinism() -> None:
    strike = torch.tensor([95.0, 105.0], dtype=torch.float64)
    opt = torch.tensor([1.0, -1.0], dtype=torch.float64)
    mat = torch.tensor([10, 20], dtype=torch.float64)
    p1 = black_scholes_p0(strike=strike, maturity=mat, option_type=opt)
    p2 = black_scholes_p0(strike=strike, maturity=mat, option_type=opt)
    assert torch.allclose(p1, p2)
    # Different moneyness gives different P0
    strike2 = torch.tensor([90.0, 110.0], dtype=torch.float64)
    p3 = black_scholes_p0(strike=strike2, maturity=mat, option_type=opt)
    assert not torch.allclose(p1, p3)


def test_construct_episode_levels() -> None:
    dx = torch.randn(63, dtype=torch.float64)
    ep = construct_episode(dx=dx, maturity=10, moneyness=1.0, option_type=1)
    assert ep["s_series"].shape == (11,)  # M+1
    assert ep["s_series"][0].item() == 100.0
    assert ep["maturity"] == 10


# ---------------------------------------------------------------------------
# CVaR fractional tail, gradient, selection full-set
# ---------------------------------------------------------------------------

def test_cvar_fractional_tail_various_n() -> None:
    # Test harness expectations for various N at alpha 0.95
    # For N=40, tail 2.0 k=2 f=0 -> mean 2 largest
    losses = torch.arange(1, 41, dtype=torch.float64)  # 1..40
    c = empirical_cvar(losses, alpha=0.95)
    assert math.isclose(c.item(), (40 + 39) / 2.0, rel_tol=1e-12)
    # N=41 tail 2.05 k2 f0.05 -> (40+41 +0.05*39)/2.05
    losses41 = torch.arange(1, 42, dtype=torch.float64)
    c41 = empirical_cvar(losses41, alpha=0.95)
    expected41 = (41 + 40 + 0.05 * 39) / 2.05
    assert math.isclose(c41.item(), expected41, rel_tol=1e-12)
    # N=64 tail 3.2 k3 f0.2
    losses64 = torch.arange(1, 65, dtype=torch.float64)
    c64 = empirical_cvar(losses64, alpha=0.95)
    expected64 = (64 + 63 + 62 + 0.2 * 61) / 3.2
    assert math.isclose(c64.item(), expected64, rel_tol=1e-12)
    # N=60 tail 3.0 k3 f0 -> mean 3 largest
    losses60 = torch.arange(1, 61, dtype=torch.float64)
    c60 = empirical_cvar(losses60, alpha=0.95)
    assert math.isclose(c60.item(), (60 + 59 + 58) / 3.0, rel_tol=1e-12)
    # N=59 tail 2.95 k2 f0.95
    losses59 = torch.arange(1, 60, dtype=torch.float64)
    c59 = empirical_cvar(losses59, alpha=0.95)
    expected59 = (59 + 58 + 0.95 * 57) / 2.95
    assert math.isclose(c59.item(), expected59, rel_tol=1e-12)
    # N=100 tail 5 k5 f0
    losses100 = torch.arange(1, 101, dtype=torch.float64)
    c100 = empirical_cvar(losses100, alpha=0.95)
    assert math.isclose(c100.item(), (100 + 99 + 98 + 97 + 96) / 5.0, rel_tol=1e-12)


def test_cvar_gradient_exists() -> None:
    losses = torch.randn(64, dtype=torch.float64, requires_grad=True)
    c = empirical_cvar(losses)
    c.backward()
    assert losses.grad is not None
    assert torch.isfinite(losses.grad).all()
    # Gradient should be sparse on tail only, but at least some non-zero
    assert (losses.grad != 0).any()


def test_selection_full_set_not_mean_of_minibatches() -> None:
    # Full 10k set vs mean of 64-batch CVaRs should differ
    torch.manual_seed(0)
    losses = torch.randn(10000, dtype=torch.float64)
    full = cvar_full_set_selection(losses)
    # Mean of minibatch CVaRs (156 batches of 64 + remainder)
    batch_cvars = []
    for i in range(0, 10000, 64):
        batch = losses[i : i + 64]
        if batch.numel() == 64:
            batch_cvars.append(empirical_cvar(batch).item())
    mean_batch = sum(batch_cvars) / len(batch_cvars)
    # They should not be equal (different semantics)
    assert not math.isclose(full.item(), mean_batch, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# GRU shape, raw action shape
# ---------------------------------------------------------------------------

def test_gru_shape() -> None:
    hedger = GRUHedger()
    x = torch.randn(2, 10, 7, dtype=torch.float32)
    delta = hedger(x)
    assert delta.shape == (2, 10)
    # Parameter count deterministic
    assert hedger.count_parameters() > 0


def test_raw_action_no_clipping() -> None:
    hedger = GRUHedger()
    # Force large output via large bias
    with torch.no_grad():
        hedger.readout.bias.fill_(10.0)
        hedger.readout.weight.fill_(1.0)
    x = torch.ones(1, 5, 7, dtype=torch.float32) * 10
    delta = hedger(x)
    # Raw action may be large, not clipped to [-1,1] or [-2,2]
    assert (delta.abs() > 2.0).any()


# ---------------------------------------------------------------------------
# CUDA authorization fail-close, authorization absent refusal, overwrite refusal
# ---------------------------------------------------------------------------

def test_cuda_authorization_fail_close_via_mock() -> None:
    from neuralmarket.research.deep_hedging.runner import preflight_checks

    with patch("neuralmarket.research.deep_hedging.runner.resolve_device", side_effect=RuntimeError("CUDA requested but unavailable - fail closed, no CPU fallback")):
        with pytest.raises(RuntimeError, match="fail closed"):
            preflight_checks(require_clean_tree=False)


def test_authorization_absent_refusal() -> None:
    with pytest.raises(AuthorizationError, match="REFUSED"):
        require_authorization_or_refuse(
            authorization_path=Path("data/processed/research/hedging_policies/fake_authorization.json"),
            execute_flag=True,
        )
    # Dry run without execute should not raise
    result = require_authorization_or_refuse(
        authorization_path=Path("data/processed/research/hedging_policies/fake_authorization.json"),
        execute_flag=False,
    )
    assert result == "DRY_RUN"


def test_artifact_overwrite_refusal(tmp_path: Path) -> None:
    fake = tmp_path / "checkpoint.pt"
    fake.write_bytes(b"fake")
    with pytest.raises(ArtifactExistsError, match="OVERWRITE_REFUSED"):
        check_artifact_nonexistence(fake)
    # Non-existent should not raise
    check_artifact_nonexistence(tmp_path / "nonexistent.pt")


# ---------------------------------------------------------------------------
# Completeness 3/3, 2/3 invalidity, replacement NONE
# ---------------------------------------------------------------------------

def test_completeness_3_of_3_valid() -> None:
    valid = {("seed-01", 0.0): 3, ("seed-01", 0.0010): 3}
    result = completeness_check(valid)
    assert result[("seed-01", 0.0)] == "VALID"
    # Missing entries are 0 -> INVALID
    assert result[("seed-02", 0.0)] == "INVALID"


def test_completeness_2_of_3_invalid() -> None:
    valid = {("seed-01", 0.0): 2}
    result = completeness_check(valid)
    assert result[("seed-01", 0.0)] == "INVALID"
    # No shrink to 2/3 allowed


def test_replacement_none_and_global_failure() -> None:
    # Global failure >20% (10+ of 45 invalid -> valid <=35)
    assert global_failure_check(35) is True  # 10 invalid
    assert global_failure_check(36) is False  # 9 invalid


def test_artifact_paths() -> None:
    p = synthetic_dataset_path("5bdbaabd2fb257a7", "seed-01")
    assert "hedging_synthetic" in str(p)
    q = policy_checkpoint_path("5bdbaabd2fb257a7", "seed-01", 0.0, 31001)
    assert "hedging_policies" in str(q)
    assert "c_0" in str(q)
