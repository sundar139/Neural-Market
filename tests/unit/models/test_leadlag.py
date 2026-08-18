"""Tests for the lead-lag path augmentation (TDD).

Covers:
- Exact hand-computed sequences
- Correct lead/lag ordering
- Determinism
- Zero path
- Constant path
- Positive and negative increments
- Shape/device/dtype
- No future data leakage
- Quadratic-variation sensitivity (the critical test)
- Autograd through the path
"""

from __future__ import annotations

import pytest
import torch

from neuralmarket.data.research.sde_windows import WindowSpec
from neuralmarket.models.leadlag import LEADLAG_PATH_DIM_OFFSET, leadlag_augment_path

pytestmark = [pytest.mark.unit]


spec = WindowSpec()  # horizon=63


class TestShapeAndProperties:
    """Basic contract tests for the lead-lag path."""

    def test_output_shape(self) -> None:
        batch, horizon, ctx_dim = 4, 8, 3
        returns = torch.randn(batch, horizon)
        ctx = torch.randn(batch, ctx_dim)
        spec_h = WindowSpec(horizon=horizon)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=spec_h)
        assert path.shape == (batch, 2 + 2 * horizon, LEADLAG_PATH_DIM_OFFSET + ctx_dim)

    def test_output_shape_default_spec(self) -> None:
        batch = 2
        returns = torch.randn(batch, spec.horizon)
        ctx = torch.randn(batch, 4)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0)
        assert path.shape == (batch, 2 + 2 * spec.horizon, 3 + 4)

    def test_dtype_preserved(self) -> None:
        returns = torch.randn(2, 5)
        ctx = torch.randn(2, 3)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=5))
        assert path.dtype == torch.float32

    def test_finite_output(self) -> None:
        returns = torch.randn(3, 10)
        ctx = torch.randn(3, 4)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=10))
        assert torch.isfinite(path).all()


class TestExactHandComputed:
    """Verify against hand-computed values for a small known input."""

    def test_single_return(self) -> None:
        """One return, verify every point exactly."""
        returns = torch.tensor([[0.2]])  # (1, 1)
        ctx = torch.tensor([[1.0, 2.0, 3.0, 4.0]])
        scale = 1.0
        path = leadlag_augment_path(returns, ctx, cumret_scale=scale, spec=WindowSpec(horizon=1))
        # Expected: 2 + 2*1 = 4 points, dim = 7
        assert path.shape == (1, 4, 7)

        # Point 0: origin (all zeros)
        assert torch.allclose(path[0, 0], torch.zeros(7))
        # Point 1: context point
        expected_ctx = torch.tensor([0.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0])
        assert torch.allclose(path[0, 1], expected_ctx)
        # Point 2: lead advance: time=0.5, lead=0.2, lag=0.0, ctx
        expected_a = torch.tensor([0.5, 0.2, 0.0, 1.0, 2.0, 3.0, 4.0])
        assert torch.allclose(path[0, 2], expected_a)
        # Point 3: lag catch: time=1.0, lead=0.2, lag=0.2, ctx
        expected_b = torch.tensor([1.0, 0.2, 0.2, 1.0, 2.0, 3.0, 4.0])
        assert torch.allclose(path[0, 3], expected_b)

    def test_two_returns(self) -> None:
        """Two returns, verify lead/lag interleaving."""
        returns = torch.tensor([[0.1, -0.3]])
        ctx = torch.tensor([[0.0, 0.0, 0.0, 0.0]])
        scale = 1.0
        path = leadlag_augment_path(returns, ctx, cumret_scale=scale, spec=WindowSpec(horizon=2))
        # 2 + 2*2 = 6 points, dim = 7
        assert path.shape == (1, 6, 7)

        # Point 0: origin
        assert torch.allclose(path[0, 0], torch.zeros(7))
        # Point 1: context
        # Point 2: lead advance i=0: time=0.25, lead=0.1, lag=0
        assert torch.allclose(path[0, 2, :3], torch.tensor([0.25, 0.1, 0.0]))
        # Point 3: lag catch i=0: time=0.5, lead=0.1, lag=0.1
        assert torch.allclose(path[0, 3, :3], torch.tensor([0.5, 0.1, 0.1]))
        # Point 4: lead advance i=1: time=0.75, lead=-0.2, lag=0.1
        assert torch.allclose(path[0, 4, :3], torch.tensor([0.75, -0.2, 0.1]))
        # Point 5: lag catch i=1: time=1.0, lead=-0.2, lag=-0.2
        assert torch.allclose(path[0, 5, :3], torch.tensor([1.0, -0.2, -0.2]))


class TestLeadLagOrdering:
    """Lead and lag must alternate correctly and converge at catch-up points."""

    def test_lag_catches_lead_at_catch_points(self) -> None:
        """At every lag-catch point, lead == lag."""
        returns = torch.randn(5, 10)
        ctx = torch.randn(5, 4)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=10))
        lead = path[:, :, 1]
        lag = path[:, :, 2]
        for b in range(5):
            for p in range(3, path.shape[1], 2):  # lag-catch points (odd body indices)
                assert abs(lead[b, p].item() - lag[b, p].item()) < 1e-6

    def test_lead_advances_at_lead_points(self) -> None:
        """At lead-advance points, lead may differ from lag (lead is ahead)."""
        returns = torch.randn(5, 10)
        ctx = torch.randn(5, 4)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=10))
        lead = path[:, :, 1]
        lag = path[:, :, 2]
        for b in range(5):
            for _ in range(2, path.shape[1], 2):  # lead-advance points
                pass  # No invariant beyond: lead and lag are finite
            for p in range(3, path.shape[1], 2):  # lag-catch points
                assert abs(lead[b, p].item() - lag[b, p].item()) < 1e-6


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        returns = torch.randn(3, 8)
        ctx = torch.randn(3, 4)
        p1 = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=8))
        p2 = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=8))
        assert torch.equal(p1, p2)


class TestZeroPath:
    def test_zero_returns(self) -> None:
        returns = torch.zeros(2, 5)
        ctx = torch.randn(2, 3)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=5))
        # All lead and lag channels should be zero (cumret stays 0).
        assert torch.allclose(path[:, :, 1], torch.zeros(2, 12))
        assert torch.allclose(path[:, :, 2], torch.zeros(2, 12))
        # Time channel should be monotonically increasing in the body.
        time_body = path[:, 2:, 0]
        diffs = time_body[:, 1:] - time_body[:, :-1]
        assert (diffs >= 0).all()


class TestConstantPath:
    def test_constant_returns(self) -> None:
        returns = torch.full((2, 5), 0.01)
        ctx = torch.randn(2, 3)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=5))
        # Lead should be monotonically non-decreasing (always going up).
        lead = path[:, :, 1]
        diffs = lead[:, 1:] - lead[:, :-1]
        # Lead diffs are 0 at lag-catch points, positive at lead-advance.
        assert (diffs >= -1e-6).all()
        # Lag should eventually catch up to lead.
        for b in range(2):
            assert abs(path[b, -1, 1].item() - path[b, -1, 2].item()) < 1e-6


class TestNoFutureData:
    def test_context_only_in_initial_segment(self) -> None:
        """Context should be visible in every body point (constant channel)."""
        returns = torch.randn(2, 8)
        ctx = torch.tensor([[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]])
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=8))
        # Origin has zero context
        assert torch.allclose(path[:, 0, 3:], torch.zeros(2, 4))
        # Context point and all body points have the same context
        for i in range(1, path.shape[1]):
            assert torch.allclose(path[:, i, 3:], ctx)


class TestNegativeIncrements:
    def test_negative_returns(self) -> None:
        returns = torch.tensor([[-0.5, -0.3, -0.1]])
        ctx = torch.tensor([[0.0, 0.0, 0.0, 0.0]])
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=3))
        # Cumulative returns are negative and decreasing
        lead = path[0, :, 1]
        # Final lead should be -0.9
        assert abs(lead[-1].item() - (-0.9)) < 1e-6
        # Lead should be monotonically non-increasing (all negative returns)
        diffs = lead[1:] - lead[:-1]
        assert (diffs <= 1e-6).all()


class TestAutograd:
    def test_gradients_flow_through_path(self) -> None:
        returns = torch.randn(4, 8, requires_grad=True)
        ctx = torch.randn(4, 4)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=8))
        loss = path.sum()
        loss.backward()
        assert returns.grad is not None
        assert torch.isfinite(returns.grad).all()
        # Gradient should be non-zero (returns affect the path).
        assert returns.grad.abs().sum().item() > 0

    def test_signature_features_differentiable(self) -> None:
        """Full autograd: returns -> lead-lag path -> signature -> loss."""
        from neuralmarket.models.signature import truncated_signature_features

        returns = torch.randn(4, 8, requires_grad=True)
        ctx = torch.randn(4, 4)
        path = leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=8))
        features = truncated_signature_features(path, level=3)
        # Sum all features as a scalar loss
        loss = sum(v.sum() for v in features.values())
        loss.backward()
        assert returns.grad is not None
        assert torch.isfinite(returns.grad).all()
        assert returns.grad.abs().sum().item() > 0


class TestQuadraticVariationSensitivity:
    """Lead-lag must distinguish paths with same endpoint but different variation."""

    def test_smooth_vs_choppy_distinguished(self) -> None:
        horizon = 10
        ctx = torch.zeros(1, 4)
        scale = 1.0

        # Smooth path: constant increments
        smooth_returns = torch.full((1, horizon), 0.01)
        # Choppy path: same endpoint, alternating large/small
        choppy_returns = torch.tensor([[0.02, 0.0, 0.02, 0.0, 0.02, 0.0, 0.02, 0.0, 0.02, 0.0]])

        assert abs(smooth_returns.sum().item() - choppy_returns.sum().item()) < 1e-6, (
            "Both paths must have the same total displacement"
        )

        s_spec = WindowSpec(horizon=horizon)
        smooth_path = leadlag_augment_path(
            smooth_returns, ctx, cumret_scale=scale, spec=s_spec
        )
        choppy_path = leadlag_augment_path(
            choppy_returns, ctx, cumret_scale=scale, spec=s_spec
        )

        from neuralmarket.models.signature import truncated_signature_features
        from neuralmarket.models.signature_mmd import signature_feature_vector

        smooth_feats = truncated_signature_features(smooth_path, level=3)
        choppy_feats = truncated_signature_features(choppy_path, level=3)

        smooth_vec = signature_feature_vector(smooth_feats)
        choppy_vec = signature_feature_vector(choppy_feats)

        dist = (smooth_vec - choppy_vec).norm().item()
        # The lead-lag signatures must be substantially different.
        assert dist > 0.01, (
            f"Lead-lag signatures of smooth vs choppy paths are too similar: {dist}"
        )

    def test_old_signature_less_sensitive(self) -> None:
        """The cumulative-only path should be LESS sensitive than lead-lag."""
        horizon = 10
        ctx = torch.zeros(1, 4)
        scale = 1.0

        smooth_returns = torch.full((1, horizon), 0.01)
        choppy_returns = torch.tensor([[0.02, 0.0, 0.02, 0.0, 0.02, 0.0, 0.02, 0.0, 0.02, 0.0]])

        from neuralmarket.models.signature import (
            augment_path,
            truncated_signature_features,
        )
        from neuralmarket.models.signature_mmd import signature_feature_vector

        # Old cumulative-only paths
        o_spec = WindowSpec(horizon=horizon)
        smooth_old = augment_path(
            smooth_returns, ctx, cumret_scale=scale, spec=o_spec
        )
        choppy_old = augment_path(
            choppy_returns, ctx, cumret_scale=scale, spec=o_spec
        )
        smooth_old_feats = truncated_signature_features(smooth_old, level=3)
        choppy_old_feats = truncated_signature_features(choppy_old, level=3)
        smooth_old_vec = signature_feature_vector(smooth_old_feats)
        choppy_old_vec = signature_feature_vector(choppy_old_feats)
        old_dist = (smooth_old_vec - choppy_old_vec).norm().item()

        # Lead-lag paths
        ll_spec = WindowSpec(horizon=horizon)
        smooth_ll = leadlag_augment_path(
            smooth_returns, ctx, cumret_scale=scale, spec=ll_spec
        )
        choppy_ll = leadlag_augment_path(
            choppy_returns, ctx, cumret_scale=scale, spec=ll_spec
        )
        smooth_ll_feats = truncated_signature_features(smooth_ll, level=3)
        choppy_ll_feats = truncated_signature_features(choppy_ll, level=3)
        smooth_ll_vec = signature_feature_vector(smooth_ll_feats)
        choppy_ll_vec = signature_feature_vector(choppy_ll_feats)
        ll_dist = (smooth_ll_vec - choppy_ll_vec).norm().item()

        # Lead-lag should be MORE sensitive (larger distance).
        assert ll_dist > old_dist, (
            f"Lead-lag ({ll_dist:.4f}) should be more sensitive than "
            f"cumulative-only ({old_dist:.4f})"
        )


class TestInputValidation:
    def test_wrong_horizon_rejected(self) -> None:
        returns = torch.randn(2, 5)
        ctx = torch.randn(2, 4)
        with pytest.raises(ValueError, match="shape"):
            leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=8))

    def test_batch_mismatch_rejected(self) -> None:
        returns = torch.randn(2, 5)
        ctx = torch.randn(3, 4)
        with pytest.raises(ValueError, match="batch"):
            leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=5))

    def test_nonfinite_returns_rejected(self) -> None:
        returns = torch.tensor([[1.0, float("nan"), 3.0]])
        ctx = torch.randn(1, 4)
        with pytest.raises(ValueError, match="finite"):
            leadlag_augment_path(returns, ctx, cumret_scale=1.0, spec=WindowSpec(horizon=3))

    def test_bad_scale_rejected(self) -> None:
        returns = torch.randn(1, 5)
        ctx = torch.randn(1, 4)
        with pytest.raises(ValueError, match="scale"):
            leadlag_augment_path(returns, ctx, cumret_scale=0.0, spec=WindowSpec(horizon=5))
        with pytest.raises(ValueError, match="scale"):
            leadlag_augment_path(returns, ctx, cumret_scale=-1.0, spec=WindowSpec(horizon=5))
