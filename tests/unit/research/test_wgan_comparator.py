"""Focused tests for the frozen WGAN objective, selection, and H2 metrics."""
from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from neuralmarket.models.wgan_cde import HORIZON, LATENT_DIM, WGANCritic
from neuralmarket.research import wgan_comparator
from neuralmarket.research.wgan_comparator import (
    AMENDMENT_060_SHA256,
    INTERNAL_SELECTION_GENERATED_PATH_SEED,
    WGAN_PREREGISTRATION_SHA256,
    WGAN_PRIMARY_MEMBER_IDS,
    AttemptOutcome,
    CheckpointCandidate,
    EarlyStoppingState,
    WGANTrainingConfig,
    compute_attempt_metrics,
    compute_completed_member_metrics,
    critic_wgan_gp_loss,
    generator_wgan_loss,
    gradient_penalty,
    non_scientific_cpu_smoke,
    normalized_terminal_wasserstein,
    select_checkpoint,
)


def _outcome(
    member_id: str,
    status: str,
    *,
    role: str = "PRIMARY",
    checkpoint: bool = True,
    nonfinite: bool = False,
    epoch: int | None = 100,
    metric: float | None = 0.25,
) -> AttemptOutcome:
    return AttemptOutcome(
        member_id=member_id,
        role=role,
        status=status,
        valid_checkpoint=checkpoint,
        nonfinite_training_or_selection=nonfinite,
        best_generator_epoch=epoch,
        checkpoint_selection_metric=metric,
    )


def test_frozen_wgan_objective_signs_lambda_and_ratio() -> None:
    config = WGANTrainingConfig()
    assert config.lambda_gp == 10.0
    assert config.critic_generator_update_ratio == 5
    assert config.optimizer == "Adam"
    assert config.learning_rate == 1e-4
    assert config.betas == (0.0, 0.9)
    assert config.weight_decay == 0.0
    assert config.gradient_clipping is False
    assert critic_wgan_gp_loss(torch.tensor([2.0]), torch.tensor([1.0]), torch.tensor(0.5)) == 4.0
    assert generator_wgan_loss(torch.tensor([1.0])) == -1.0


def test_gradient_penalty_is_finite_and_uses_full_path_input() -> None:
    torch.manual_seed(1)
    critic = WGANCritic(cumulative_return_scale=1.0)
    real = torch.randn(4, 63)
    fake = torch.randn(4, 63)
    context = torch.randn(4, 4)
    penalty = gradient_penalty(critic, real, fake, context, cumulative_return_scale=1.0)
    assert penalty.ndim == 0
    assert torch.isfinite(penalty)
    penalty.backward()
    assert any(parameter.grad is not None for parameter in critic.parameters())


def test_checkpoint_selection_lower_metric_then_earliest_then_identity() -> None:
    candidates = [
        CheckpointCandidate(identity="z", epoch=4, metric=0.1),
        CheckpointCandidate(identity="b", epoch=3, metric=0.1),
        CheckpointCandidate(identity="a", epoch=3, metric=0.1),
        CheckpointCandidate(identity="q", epoch=1, metric=0.2),
    ]
    selected = select_checkpoint(candidates)
    assert selected == CheckpointCandidate(identity="a", epoch=3, metric=0.1)


def test_early_stopping_patience_and_zero_min_delta() -> None:
    state = EarlyStoppingState(patience=2, min_delta=0.0)
    assert state.consider(epoch=1, metric=1.0)
    assert state.consider(epoch=2, metric=1.0) is False
    assert state.should_stop is False
    assert state.consider(epoch=3, metric=1.1) is False
    assert state.should_stop is True
    assert state.best_epoch == 1


def test_attempt_metrics_use_denominator_five_and_preserve_reasons() -> None:
    outcomes = [
        _outcome("wgan-seed-01", "GATE_PASS_VALID"),
        _outcome("wgan-seed-02", "GATE_FAIL_VALID", epoch=200, metric=0.3),
        _outcome(
            "wgan-seed-03",
            "VALID_EXECUTION_NO_GATE_RESULT",
            checkpoint=False,
            epoch=None,
            metric=None,
        ),
        _outcome("wgan-seed-04", "GOVERNANCE_INVALID", checkpoint=False, epoch=None, metric=None),
        _outcome(
            "wgan-seed-05",
            "GATE_FAIL_VALID",
            checkpoint=False,
            nonfinite=True,
            epoch=None,
            metric=None,
        ),
    ]
    metrics = compute_attempt_metrics(outcomes)
    assert tuple(f"wgan-seed-0{i}" for i in range(1, 6)) == WGAN_PRIMARY_MEMBER_IDS
    assert metrics["valid_completed_member_fraction"]["numerator"] == 3
    assert metrics["valid_completed_member_fraction"]["denominator"] == 5
    assert metrics["valid_completed_member_fraction"]["value"] == pytest.approx(0.6)
    rate = metrics["nonfinite_or_missing_checkpoint_rate"]
    assert rate["numerator"] == 3
    assert rate["denominator"] == 5
    assert rate["value"] == pytest.approx(0.6)
    by_id = {item["member_id"]: item for item in rate["attempts"]}
    assert by_id["wgan-seed-04"]["reason"] == "GOVERNANCE_INVALID"
    assert by_id["wgan-seed-05"]["reason"] == "NONFINITE_TRAINING_OR_SELECTION"
    assert by_id["wgan-seed-03"]["reason"] == "MISSING_VALID_CHECKPOINT"


def test_attempt_metrics_reject_missing_primary_without_imputation() -> None:
    outcomes = [
        _outcome(member_id, "GATE_PASS_VALID")
        for member_id in WGAN_PRIMARY_MEMBER_IDS[:-1]
    ]
    with pytest.raises(ValueError, match="exactly the five"):
        compute_attempt_metrics(outcomes)


def test_completed_metrics_sample_sd_ddof_one_and_reserve_role_is_retained() -> None:
    outcomes = [
        _outcome("wgan-seed-01", "GATE_PASS_VALID", epoch=100, metric=0.2),
        _outcome("wgan-seed-02", "GATE_FAIL_VALID", epoch=200, metric=0.4),
        _outcome("reserve-wgan-j01", "GATE_PASS_VALID", role="RESERVE", epoch=300, metric=0.8),
    ]
    metrics = compute_completed_member_metrics(outcomes, max_generator_epochs=400)
    assert metrics["normalized_best_checkpoint_epoch_sd"] == pytest.approx(0.25)
    assert metrics["checkpoint_selection_metric_sd"] == pytest.approx(math.sqrt(7.0 / 75.0))
    assert metrics["members"][-1]["member_id"] == "reserve-wgan-j01"
    assert metrics["members"][-1]["role"] == "RESERVE"


def test_completed_metrics_return_missing_without_imputation() -> None:
    outcomes = [_outcome("wgan-seed-01", "GATE_PASS_VALID", epoch=100, metric=0.2)]
    metrics = compute_completed_member_metrics(outcomes, max_generator_epochs=400)
    assert metrics["normalized_best_checkpoint_epoch_sd"] is None
    assert metrics["checkpoint_selection_metric_sd"] is None
    assert metrics["missingness"] == "NO_IMPUTATION"


def test_normalized_terminal_wasserstein_is_finite_and_fail_closed() -> None:
    real = torch.tensor([0.0, 1.0, 2.0])
    fake = torch.tensor([0.0, 1.0, 3.0])
    assert normalized_terminal_wasserstein(fake, real) >= 0.0
    with pytest.raises(ValueError, match="finite"):
        normalized_terminal_wasserstein(torch.tensor([float("nan")]), real)


def test_metric_provenance_is_pinned_to_both_frozen_records() -> None:
    assert WGAN_PREREGISTRATION_SHA256 == (
        "6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037"
    )
    assert AMENDMENT_060_SHA256 == (
        "2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c"
    )


def test_cpu_smoke_is_labeled_and_does_not_train() -> None:
    result = non_scientific_cpu_smoke()
    assert result["classification"] == "NON_SCIENTIFIC_TEST_ONLY"
    assert result["generator_shape"] == (2, 63)
    assert result["critic_shape"] == (2,)
    assert result["critic_loss_finite"] is True
    assert result["generator_loss_finite"] is True
    assert result["gradient_penalty_finite"] is True


def _training_random_streams(data_seed: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    config = WGANTrainingConfig(data_seed=data_seed)
    device = torch.device("cpu")
    data_generator, order_generator = wgan_comparator._make_seeded_data_generators(
        device, config
    )
    static, temporal = wgan_comparator._draw_noise(8, device, data_generator)
    order = torch.randperm(128, generator=order_generator, device=device)
    return static, temporal, order


def test_training_noise_varies_with_data_seed_and_reproduces() -> None:
    first = _training_random_streams(8282)
    second = _training_random_streams(9282)
    repeat = _training_random_streams(8282)

    assert not torch.equal(first[0], second[0])
    assert not torch.equal(first[1], second[1])
    assert torch.equal(first[0], repeat[0])
    assert torch.equal(first[1], repeat[1])


def test_training_window_order_varies_with_data_seed_and_reproduces() -> None:
    first = _training_random_streams(8282)[2]
    second = _training_random_streams(9282)[2]
    repeat = _training_random_streams(8282)[2]

    assert not torch.equal(first, second)
    assert torch.equal(first, repeat)


def test_refit_noise_and_order_use_data_seed_without_scientific_refit() -> None:
    first = _training_random_streams(1729)
    second = _training_random_streams(1730)

    assert not torch.equal(first[0], second[0])
    assert not torch.equal(first[1], second[1])
    assert not torch.equal(first[2], second[2])


def _capture_selection_randomness(
    monkeypatch: pytest.MonkeyPatch, config: WGANTrainingConfig
) -> dict[str, object]:
    captured: dict[str, object] = {}

    def capture_noise(
        batch_size: int, device: torch.device, generator: torch.Generator
    ) -> tuple[torch.Tensor, torch.Tensor]:
        static = torch.randn(batch_size, LATENT_DIM, device=device, generator=generator)
        temporal = torch.randn(batch_size, HORIZON, 2, device=device, generator=generator)
        captured["static"] = static
        captured["temporal"] = temporal
        return static, temporal

    def capture_bootstrap(
        returns: np.ndarray,
        n_paths: int,
        horizon: int,
        *,
        block_length: int,
        seed: int,
    ) -> np.ndarray:
        captured["bootstrap_seed"] = seed
        assert block_length == 22
        assert returns.size > horizon
        return np.ones((n_paths, horizon), dtype=np.float64)

    class ZeroGenerator:
        def __call__(
            self, context: torch.Tensor, static: torch.Tensor, temporal: torch.Tensor
        ) -> torch.Tensor:
            return torch.zeros((context.shape[0], HORIZON), dtype=context.dtype)

    monkeypatch.setattr(wgan_comparator, "_draw_noise", capture_noise)
    monkeypatch.setattr(wgan_comparator, "_circular_block_bootstrap", capture_bootstrap)
    monkeypatch.setattr(
        wgan_comparator,
        "normalized_terminal_wasserstein",
        lambda fake, real: 0.0,
    )
    wgan_comparator._selection_metric(
        ZeroGenerator(),
        torch.zeros(4, 4),
        np.ones(64, dtype=np.float64),
        cumulative_return_scale=1.0,
        config=config,
    )
    return captured


def test_selection_draw_is_member_invariant_and_frozen_at_7777(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _capture_selection_randomness(
        monkeypatch, WGANTrainingConfig(selection_paths=8, real_reference_paths=4, data_seed=8282)
    )
    second = _capture_selection_randomness(
        monkeypatch, WGANTrainingConfig(selection_paths=8, real_reference_paths=4, data_seed=9282)
    )

    assert INTERNAL_SELECTION_GENERATED_PATH_SEED == 7777
    assert torch.equal(first["static"], second["static"])
    assert torch.equal(first["temporal"], second["temporal"])

    expected = torch.Generator(device="cpu")
    expected.manual_seed(7777)
    expected_static = torch.randn(8, LATENT_DIM, generator=expected)
    expected_temporal = torch.randn(8, HORIZON, 2, generator=expected)
    assert torch.equal(first["static"], expected_static)
    assert torch.equal(first["temporal"], expected_temporal)

    eval_generator = torch.Generator(device="cpu")
    eval_generator.manual_seed(8283)
    eval_static = torch.randn(8, LATENT_DIM, generator=eval_generator)
    assert not torch.equal(first["static"], eval_static)


def test_real_selection_bootstrap_reference_remains_8801(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_selection_randomness(
        monkeypatch, WGANTrainingConfig(selection_paths=8, real_reference_paths=4)
    )

    assert captured["bootstrap_seed"] == 8801
    assert WGANTrainingConfig().eval_seed == 8283
