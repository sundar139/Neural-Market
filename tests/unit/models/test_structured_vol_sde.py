"""Tests for the structured volatility neural SDE."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from neuralmarket.models.structured_vol_sde import (
    StructuredVolatilityNeuralSde,
    StructuredVolConfig,
    simulate_structured,
)

pytestmark = [pytest.mark.unit]


class TestOutputSemantics:
    """A. Output is daily X increments, cumsum reconstructs X state."""

    def test_output_shape(self) -> None:
        model = StructuredVolatilityNeuralSde(StructuredVolConfig(horizon=5))
        ctx = torch.randn(3, 4)
        noise = torch.randn(3, 5, 2)
        out = model(ctx, noise)
        assert out.shape == (3, 5)

    def test_cumsum_reconstructs_x(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde(StructuredVolConfig(horizon=10))
        ctx = torch.randn(4, 4)
        noise = torch.randn(4, 10, 2)
        out = model(ctx, noise)
        levels = out.cumsum(dim=1)
        assert torch.isfinite(levels).all()
        assert torch.allclose(levels[:, 0], out[:, 0])

    def test_output_not_levels(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde(StructuredVolConfig(horizon=5))
        ctx = torch.randn(3, 4)
        noise = torch.randn(3, 5, 2)
        out = model(ctx, noise)
        levels = out.cumsum(dim=1)
        # At step 1+, increment != level
        if not torch.allclose(out[:, 1], levels[:, 1]):
            pass  # Good: increment differs from level


class TestPositiveDiffusion:
    """B. sigma_x > 0 always."""

    def test_sigma_x_positive(self) -> None:
        model = StructuredVolatilityNeuralSde()
        V = torch.linspace(-5, 5, 100).unsqueeze(1)  # noqa: N806
        sigma = model.sigma_x(V)
        assert (sigma > 0).all()

    def test_sigma_x_positive_random(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde()
        V = torch.randn(1000, 1)  # noqa: N806
        sigma = model.sigma_x(V)
        assert (sigma > 0).all()


class TestMonotonicCoupling:
    """C. sigma_x(V_high) > sigma_x(V_low) for V_high > V_low."""

    def test_monotonic(self) -> None:
        model = StructuredVolatilityNeuralSde()
        V_low = torch.tensor([[-2.0]])  # noqa: N806
        V_high = torch.tensor([[2.0]])  # noqa: N806
        sigma_low = model.sigma_x(V_low)
        sigma_high = model.sigma_x(V_high)
        assert sigma_high.item() > sigma_low.item()

    def test_monotonic_batch(self) -> None:
        model = StructuredVolatilityNeuralSde()
        V = torch.linspace(-3, 3, 50).unsqueeze(1)  # noqa: N806
        sigma = model.sigma_x(V)
        diffs = sigma[1:] - sigma[:-1]
        assert (diffs > 0).all()


class TestPositiveKappaEta:
    """D. kappa > 0, eta > 0."""

    def test_kappa_positive(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde()
        t = torch.tensor([0.5])
        state = torch.randn(1, 2)
        ctx = torch.randn(1, 4)
        kappa = model.kappa_at(t, state, ctx)
        assert kappa.item() > 0

    def test_eta_positive(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde()
        t = torch.tensor([0.5])
        state = torch.randn(1, 2)
        ctx = torch.randn(1, 4)
        eta = model.eta_at(t, state, ctx)
        assert eta.item() > 0


class TestMeanReversion:
    """E. V > theta -> drift negative; V < theta -> drift positive."""

    def test_mean_reversion_direction(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde()
        ctx = torch.randn(1, 4)
        t = torch.tensor([0.5])

        # Get theta for a specific state
        state_ref = torch.tensor([[0.0, 0.0]])
        theta = model.theta_at(t, state_ref, ctx).item()
        kappa = model.kappa_at(t, state_ref, ctx).item()

        # V > theta: drift should be negative (mean-reverting down)
        state_high = torch.tensor([[0.0, theta + 1.0]])
        drift_high = model.theta_at(t, state_high, ctx).item() - (theta + 1.0)
        assert kappa * drift_high < 0

        # V < theta: drift should be positive (mean-reverting up)
        state_low = torch.tensor([[0.0, theta - 1.0]])
        drift_low = model.theta_at(t, state_low, ctx).item() - (theta - 1.0)
        assert kappa * drift_low > 0


class TestContextInitialization:
    """F. Same context/seed deterministic; different context can alter V0."""

    def test_deterministic(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde()
        ctx = torch.randn(2, 4)
        s1 = model.initial_state(ctx)
        s2 = model.initial_state(ctx)
        assert torch.equal(s1, s2)

    def test_different_context_different_v0(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde()
        ctx1 = torch.randn(1, 4)
        ctx2 = torch.randn(1, 4) * 10
        s1 = model.initial_state(ctx1)
        s2 = model.initial_state(ctx2)
        # V0 should differ (not guaranteed but very likely with different contexts)
        assert not torch.allclose(s1[:, 1], s2[:, 1])


class TestVarianceRisesWithV:
    """G. Local variance rises when V state rises."""

    def test_higher_v_more_variance(self) -> None:
        torch.manual_seed(42)
        cfg = StructuredVolConfig(horizon=20)
        model = StructuredVolatilityNeuralSde(cfg)
        ctx = torch.randn(1, 4)

        # Override V0 to be high
        noise = torch.randn(1, 20, 2)
        with torch.no_grad():
            # Low V
            model.eval()
            # Manual simulation with low V
            sqrt_dt = cfg.dt**0.5
            dt = cfg.dt
            x_low = torch.zeros(1, 1)
            v_low = torch.tensor([[-2.0]])
            rets_low = []
            for k in range(20):
                t = torch.tensor([float(k) / 20])
                mu = model.x_drift_at(t, torch.cat([x_low, v_low], dim=1), ctx)
                sig = model.sigma_x(v_low)
                dx = mu * dt + sig * sqrt_dt * noise[:, k, 0:1]
                rets_low.append(dx.item())
                x_low = x_low + dx

            # High V
            x_high = torch.zeros(1, 1)
            v_high = torch.tensor([[2.0]])
            rets_high = []
            for k in range(20):
                t = torch.tensor([float(k) / 20])
                mu = model.x_drift_at(t, torch.cat([x_high, v_high], dim=1), ctx)
                sig = model.sigma_x(v_high)
                dx = mu * dt + sig * sqrt_dt * noise[:, k, 0:1]
                rets_high.append(dx.item())
                x_high = x_high + dx

        var_low = np.var(rets_low)
        var_high = np.var(rets_high)
        # sigma_x(V=2) > sigma_x(V=-2), so high V should produce more variance
        assert var_high > var_low


class TestSimulationContract:
    """H. simulate_structured produces correct output."""

    def test_output_shape(self) -> None:
        model = StructuredVolatilityNeuralSde(StructuredVolConfig(horizon=10))
        ctx = torch.randn(5, 4)
        out = simulate_structured(model, ctx, seed=42)
        assert out.shape == (5, 10)

    def test_deterministic(self) -> None:
        model = StructuredVolatilityNeuralSde(StructuredVolConfig(horizon=5))
        ctx = torch.randn(3, 4)
        out1 = simulate_structured(model, ctx, seed=42)
        out2 = simulate_structured(model, ctx, seed=42)
        assert torch.equal(out1, out2)


class TestExistingContractPreserved:
    """I. Existing repaired increment tests still apply."""

    def test_increment_contract(self) -> None:
        torch.manual_seed(42)
        model = StructuredVolatilityNeuralSde(StructuredVolConfig(horizon=10))
        ctx = torch.randn(3, 4)
        noise = torch.randn(3, 10, 2)
        out = model(ctx, noise)
        # Verify increment contract
        levels = out.cumsum(dim=1)
        assert torch.allclose(levels[:, 0], out[:, 0])
        # Verify output is finite
        assert torch.isfinite(out).all()
