"""Focused non-scientific tests for the frozen WGAN-CDE model."""
from __future__ import annotations

import pytest
import torch

from neuralmarket.models.wgan_cde import (
    CONTEXT_DIM,
    CRITIC_CONTROL_DIM,
    GENERATOR_CONTROL_DIM,
    HORIZON,
    LATENT_DIM,
    WGANCritic,
    WGANGenerator,
    build_critic_control_increments,
    build_generator_control_increments,
    sample_generator_noise,
)


def test_generator_shape_horizon_context_and_finite_output() -> None:
    model = WGANGenerator()
    context = torch.zeros(3, CONTEXT_DIM)
    static_latent = torch.zeros(3, LATENT_DIM)
    temporal_noise = torch.zeros(3, HORIZON, 2)
    output = model(context, static_latent, temporal_noise)
    assert output.shape == (3, 63)
    assert torch.isfinite(output).all()


def test_generator_control_is_fixed_euler_and_uses_temporal_noise() -> None:
    noise = torch.ones(2, HORIZON, 2)
    controls = build_generator_control_increments(noise)
    assert controls.shape == (2, 63, GENERATOR_CONTROL_DIM)
    assert torch.allclose(controls[..., 0], torch.full((2, 63), 1.0 / 252.0))
    assert torch.allclose(controls[..., 1:], torch.full((2, 63, 2), (1.0 / 252.0) ** 0.5))

    torch.manual_seed(10)
    model = WGANGenerator().eval()
    context = torch.zeros(2, CONTEXT_DIM)
    latent = torch.zeros(2, LATENT_DIM)
    zero_noise = torch.zeros(2, HORIZON, 2)
    one_noise = torch.ones(2, HORIZON, 2)
    with torch.no_grad():
        zero_output = model(context, latent, zero_noise)
        one_output = model(context, latent, one_noise)
    assert not torch.equal(zero_output, one_output)


def test_seeded_generator_noise_is_reproducible() -> None:
    first = sample_generator_noise(batch_size=4, seed=8282)
    second = sample_generator_noise(batch_size=4, seed=8282)
    assert torch.equal(first.static_latent, second.static_latent)
    assert torch.equal(first.temporal_noise, second.temporal_noise)
    assert first.static_latent.shape == (4, LATENT_DIM)
    assert first.temporal_noise.shape == (4, HORIZON, 2)


def test_generator_rejects_bad_context_and_nonfinite_inputs() -> None:
    model = WGANGenerator()
    latent = torch.zeros(2, LATENT_DIM)
    noise = torch.zeros(2, HORIZON, 2)
    with pytest.raises(ValueError, match="context"):
        model(torch.zeros(2, 3), latent, noise)
    with pytest.raises(ValueError, match="finite"):
        model(torch.full((2, CONTEXT_DIM), float("nan")), latent, noise)


def test_critic_control_dimension_scalar_output_and_no_probability_head() -> None:
    critic = WGANCritic(cumulative_return_scale=2.0)
    paths = torch.zeros(3, HORIZON)
    context = torch.zeros(3, CONTEXT_DIM)
    controls = build_critic_control_increments(paths, context, cumulative_return_scale=2.0)
    assert controls.shape == (3, 63, CRITIC_CONTROL_DIM)
    output = critic(paths, context)
    assert output.shape == (3,)
    assert torch.isfinite(output).all()
    assert not any(isinstance(module, torch.nn.Sigmoid) for module in critic.modules())


def test_critic_uses_scaled_path_and_rejects_nonfinite_inputs() -> None:
    critic = WGANCritic(cumulative_return_scale=1.0).eval()
    context = torch.zeros(1, CONTEXT_DIM)
    zero_path = torch.zeros(1, HORIZON)
    nonzero_path = torch.zeros(1, HORIZON)
    nonzero_path[:, 0] = 1.0
    with torch.no_grad():
        zero_score = critic(zero_path, context)
        nonzero_score = critic(nonzero_path, context)
    assert not torch.equal(zero_score, nonzero_score)
    with pytest.raises(ValueError, match="finite"):
        critic(torch.full_like(zero_path, float("inf")), context)
