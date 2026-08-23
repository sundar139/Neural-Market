"""Focused tests for the frozen WGAN objective, selection, and H2 metrics."""
from __future__ import annotations

import math

import pytest
import torch

from neuralmarket.models.wgan_cde import WGANCritic
from neuralmarket.research.wgan_comparator import (
    AMENDMENT_060_SHA256,
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
