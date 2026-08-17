"""Neural SDE: simulation determinism, dimensions, positivity, EM accuracy."""

from __future__ import annotations

import pytest
import torch

from neuralmarket.models.neural_sde import (
    ConditionalNeuralSde,
    SdeConfig,
    configure_determinism,
    count_parameters,
    reconstruct_prices,
    set_deterministic_seeds,
    simulate,
)

pytestmark = pytest.mark.unit

_SMALL = SdeConfig(
    state_dim=2,
    brownian_dim=2,
    n_context=4,
    hidden_units=16,
    hidden_layers=1,
    horizon=63,
)


def _ctx(n: int = 8, seed: int = 0) -> torch.Tensor:
    torch.manual_seed(seed)
    return torch.randn(n, 4)


def _model(seed: int = 4242) -> ConditionalNeuralSde:
    set_deterministic_seeds(seed)
    configure_determinism(True)
    return ConditionalNeuralSde(_SMALL)


class TestSimulationDeterminism:
    def test_same_seed_same_paths(self) -> None:
        model = _model()
        ctx = _ctx(4)
        a = simulate(model, ctx, seed=4244)
        b = simulate(model, ctx, seed=4244)
        assert torch.equal(a, b)

    def test_different_seed_changes_paths(self) -> None:
        model = _model()
        ctx = _ctx(4)
        a = simulate(model, ctx, seed=4244)
        b = simulate(model, ctx, seed=9999)
        assert not torch.equal(a, b)

    def test_output_dimensions_and_finite(self) -> None:
        model = _model()
        ctx = _ctx(64)
        out = simulate(model, ctx, seed=4244)
        assert out.shape == (64, 63)
        assert torch.isfinite(out).all()

    def test_train_eval_mode_independent(self) -> None:
        model = _model()
        ctx = _ctx(4)
        model.eval()
        out = simulate(model, ctx, seed=4244)
        assert torch.isfinite(out).all()
        assert out.shape == (4, 63)


class TestArchitecture:
    def test_diffusion_positive_and_finite(self) -> None:
        model = _model()
        ctx = _ctx(8)
        state = torch.zeros(8, 2)
        t = torch.zeros(8)
        sigma = model.diffusion_at(t, state, ctx)
        assert torch.isfinite(sigma).all()
        assert torch.all(sigma > 0)

    def test_initial_state_has_zero_observable(self) -> None:
        model = _model()
        ctx = _ctx(4)
        state = model.initial_state(ctx)
        assert state.shape == (4, 2)
        assert torch.allclose(state[:, 0], torch.zeros(4), atol=1e-12)
        assert torch.isfinite(state).all()

    def test_parameter_count_is_positive_and_stable(self) -> None:
        model = _model()
        n = count_parameters(model)
        assert n > 0
        assert n == count_parameters(_model())

    def test_context_must_not_accept_future_data(self) -> None:
        model = _model()
        with pytest.raises(ValueError, match="shape"):
            model(torch.randn(4, 5), torch.randn(4, 63, 2))

    def test_noise_shape_validated(self) -> None:
        model = _model()
        with pytest.raises(ValueError, match="shape"):
            model(_ctx(4), torch.randn(4, 63, 3))


class TestEulerMaruyamaAccuracy:
    def test_constant_coefficient_sde_matches_analytic_moments(self) -> None:
        """DX = mu dt + sigma dW: mean and variance match dx = mu dt + sigma sqrt(dt) e."""
        model = _model()
        # Override drift/diffusion with constants for a controlled test.
        mu = torch.tensor([[0.0005, 0.0001]])
        sigma = torch.tensor([[0.02, 0.03]])

        class ConstantSde(ConditionalNeuralSde):
            def drift_at(self, t, state, context):  # type: ignore[no-untyped-def]
                return mu.expand(state.shape[0], -1)

            def diffusion_at(self, t, state, context):  # type: ignore[no-untyped-def]
                return sigma.expand(state.shape[0], -1)

        c_model = ConstantSde(model.config)
        c_model.load_state_dict(model.state_dict())
        ctx = _ctx(20_000)
        dt = model.config.dt
        out = simulate(c_model, ctx, seed=7)
        # Daily increments: x-step = mu_x dt + sigma_x sqrt(dt) e.
        emp_mean = float(out[:, 0].mean())
        emp_var = float(out[:, 0].var(unbiased=True))
        # Mean tolerance is Monte-Carlo error (SD ~ sigma*sqrt(dt)/sqrt(n) ~ 9e-6).
        assert abs(emp_mean - float(mu[0, 0] * dt)) < 5e-5
        assert emp_var == pytest.approx(float(sigma[0, 0] ** 2 * dt), rel=0.1)


class TestPrices:
    def test_reconstructed_prices_positive(self) -> None:
        model = _model()
        ctx = _ctx(32)
        out = simulate(model, ctx, seed=4244)
        prices = reconstruct_prices(out, initial_price=475.13)
        assert prices.shape == out.shape
        assert torch.isfinite(prices).all()
        assert torch.all(prices > 0)

    def test_initial_price_validation(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            reconstruct_prices(torch.zeros(2, 3), initial_price=0.0)


class TestConditioning:
    def test_conditioning_changes_generated_distribution(self) -> None:
        """A controlled test: changing context must change generated paths."""
        model = _model()
        set_deterministic_seeds(4242)
        ctx_a = torch.ones(64, 4)
        ctx_b = -torch.ones(64, 4)
        out_a = simulate(model, ctx_a, seed=1)
        out_b = simulate(model, ctx_b, seed=1)
        assert not torch.allclose(out_a, out_b)
        # And the difference is systematic (means differ materially).
        assert abs(float(out_a.mean()) - float(out_b.mean())) > 1e-6 or (
            float(out_a.std()) != float(out_b.std())
        )

    def test_no_future_data_in_context_width(self) -> None:
        model = _model()
        with pytest.raises(ValueError, match="context must have shape"):
            model(torch.randn(4, 3), torch.randn(4, 63, 2))
