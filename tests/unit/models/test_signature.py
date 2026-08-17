"""Truncated signature and signature MMD: analytic, shape, autograd tests."""

from __future__ import annotations

import math

import pytest
import torch

from neuralmarket.models.signature import (
    augment_path,
    signature_mmd,
    truncated_signature_features,
)

pytestmark = pytest.mark.unit


def _points_1d(values: list[float], device: torch.device | None = None) -> torch.Tensor:
    return torch.tensor([[[float(v)] for v in values]], device=device)


def _sig_levels(points: torch.Tensor, level: int = 3):
    return truncated_signature_features(points, level)


class TestAnalyticSignatures:
    def test_single_segment_levels_equal_dx_power_over_factorial(self) -> None:
        dx = 0.3
        points = torch.tensor([[[0.0], [dx]]], dtype=torch.float64)
        sig = _sig_levels(points)
        assert sig[1][0, 0] == pytest.approx(dx, rel=1e-12)
        assert sig[2][0, 0] == pytest.approx(dx**2 / 2.0, rel=1e-12)
        assert sig[3][0, 0] == pytest.approx(dx**3 / 6.0, rel=1e-12)

    def test_two_segment_chen_matches_hand_calculation(self) -> None:
        # 1-D segments a then b: signature level k is (a+b)^k / k!.
        a, b = 0.4, -0.2
        points = torch.tensor([[[0.0], [a], [a + b]]], dtype=torch.float64)
        sig = _sig_levels(points)
        assert sig[1][0, 0] == pytest.approx(a + b, rel=1e-12)
        assert sig[2][0, 0] == pytest.approx((a + b) ** 2 / 2.0, rel=1e-12)
        assert sig[3][0, 0] == pytest.approx((a + b) ** 3 / 6.0, rel=1e-12)

    def test_two_segment_2d_non_commutative(self) -> None:
        # Segments (a,0) then (0,b): level-2 [1,2] = a*b, [2,1] = 0.
        a, b = 0.5, 0.25
        points = torch.tensor([[[0.0, 0.0], [a, 0.0], [a, b]]], dtype=torch.float64)
        sig = _sig_levels(points)
        l2 = sig[2].view(1, 2, 2)
        l3 = sig[3].view(1, 2, 2, 2)
        assert l2[0, 0, 1] == pytest.approx(a * b, rel=1e-12)
        assert l2[0, 1, 0] == pytest.approx(0.0, abs=1e-12)
        assert l2[0, 0, 0] == pytest.approx(a**2 / 2.0, rel=1e-12)
        assert l2[0, 1, 1] == pytest.approx(b**2 / 2.0, rel=1e-12)
        assert l3[0, 0, 0, 1] == pytest.approx(a**2 * b / 2.0, rel=1e-12)

    def test_zero_path_signature_is_zero(self) -> None:
        points = torch.zeros(4, 3, 2)
        sig = _sig_levels(points)
        assert torch.allclose(sig[1], torch.zeros_like(sig[1]), atol=1e-12)
        assert torch.allclose(sig[2], torch.zeros_like(sig[2]), atol=1e-12)
        assert torch.allclose(sig[3], torch.zeros_like(sig[3]), atol=1e-12)

    def test_concatenation_property(self) -> None:
        # Signature of X*Y equals product of signatures: check level 1 and 2
        # against the standalone composition for a 2-D example.
        p1 = torch.tensor([[[0.0, 0.0], [1.0, 0.3]]], dtype=torch.float64)
        p2 = torch.tensor([[[1.0, 0.3], [1.0, 1.3], [0.7, 1.9]]], dtype=torch.float64)
        p12 = torch.cat((p1, p2[:, 1:, :]), dim=1)
        s1 = _sig_levels(p1)
        s2 = _sig_levels(p2)
        s12 = _sig_levels(p12)
        assert torch.allclose(s12[1], s1[1] + s2[1], atol=1e-12)
        # level 2: s12 = s1*s2 with Chen: outer sums plus own level-2 terms.
        expected = (
            s1[2].view(1, 2, 2)
            + torch.einsum("bi,bj->bij", s1[1].view(1, 2), s2[1].view(1, 2))
            + s2[2].view(1, 2, 2)
        ).reshape(1, 4)
        assert torch.allclose(s12[2], expected, atol=1e-12)

    def test_basepoint_context_changes_signature_terms(self) -> None:
        # Augmented paths with different context must differ in signature.
        horizon = 8
        spec = type("Spec", (), {"horizon": horizon, "dt": 1 / 252})()
        returns = torch.ones(2, horizon) * 0.01
        ctx_a = torch.zeros(2, 4)
        ctx_b = torch.ones(2, 4) * 0.5
        pa = augment_path(returns, ctx_a, cumret_scale=0.1, spec=spec)
        pb = augment_path(returns, ctx_b, cumret_scale=0.1, spec=spec)
        sa = _sig_levels(pa)
        sb = _sig_levels(pb)
        assert not torch.allclose(sa[1], sb[1])
        assert not torch.allclose(sa[2], sb[2])
        # Context enters the level-1 coordinates 3..6 directly.
        assert sb[1][0, 4] != pytest.approx(0.0, abs=1e-9)

    def test_shape_dtype_device(self) -> None:
        points = torch.randn(5, 10, 6, dtype=torch.float64)
        sig = truncated_signature_features(points, level=3)
        assert sig[1].shape == (5, 6)
        assert sig[2].shape == (5, 36)
        assert sig[3].shape == (5, 216)
        assert sig[1].dtype == torch.float64
        assert sig[3].device == points.device

    def test_unsupported_level_rejected(self) -> None:
        with pytest.raises(ValueError, match="levels 1..3"):
            truncated_signature_features(torch.randn(2, 3, 2), level=4)

    def test_differentiable_and_finite_gradients(self) -> None:
        points = torch.randn(3, 20, 4, requires_grad=True)
        sig = _sig_levels(points)
        loss = sum(sig[k].pow(2).sum() for k in (1, 2, 3))
        loss.backward()
        assert points.grad is not None
        assert torch.isfinite(points.grad).all()
        assert points.grad.abs().sum() > 0


class TestSignatureMmd:
    def test_identical_samples_give_zero(self) -> None:
        points = torch.randn(16, 12, 3)
        ref = truncated_signature_features(points)
        gen = truncated_signature_features(points.clone())
        loss = signature_mmd(ref, gen)
        assert float(loss) == pytest.approx(0.0, abs=1e-12)

    def test_shifted_distribution_is_positive(self) -> None:
        base = torch.randn(16, 12, 2)
        ref = truncated_signature_features(base)
        shifted = truncated_signature_features(base + 1.0)
        loss = signature_mmd(ref, shifted)
        assert float(loss) > 0

    def test_deterministic(self) -> None:
        points = torch.randn(8, 10, 2)
        a = signature_mmd(
            truncated_signature_features(points), truncated_signature_features(points + 0.1)
        )
        b = signature_mmd(
            truncated_signature_features(points), truncated_signature_features(points + 0.1)
        )
        assert float(a) == float(b)

    def test_gradients_reach_generated_path(self) -> None:
        points = torch.randn(8, 10, 2, requires_grad=True)
        ref_points = torch.randn(8, 10, 2)
        loss = signature_mmd(
            truncated_signature_features(ref_points), truncated_signature_features(points)
        )
        loss.backward()
        assert points.grad is not None
        assert torch.isfinite(points.grad).all()
        assert points.grad.abs().sum() > 0

    def test_mismatched_levels_rejected(self) -> None:
        points = torch.randn(4, 6, 2)
        with pytest.raises(ValueError, match="level sets"):
            signature_mmd(
                truncated_signature_features(points),
                truncated_signature_features(points, level=2),
            )

    def test_no_metric_spec_dependence(self) -> None:
        import inspect

        import neuralmarket.models.signature as sig_module

        source = inspect.getsource(sig_module)
        assert "scorecard" not in source
        assert "MetricSpecification" not in source


class TestAugmentPath:
    def test_shape_and_constant_context(self) -> None:
        horizon = 63
        spec = type("Spec", (), {"horizon": horizon, "dt": 1 / 252})()
        returns = torch.randn(4, horizon)
        ctx = torch.randn(4, 4)
        pts = augment_path(returns, ctx, cumret_scale=0.2, spec=spec)
        assert pts.shape == (4, horizon + 2, 6)
        # Context coordinates constant across the path body.
        assert torch.allclose(pts[:, 1:, 2:], ctx.unsqueeze(1), atol=1e-6)
        # Origin: all zeros at point 0.
        assert torch.allclose(pts[:, 0, :], torch.zeros(4, 6), atol=1e-12)
        # Context point at time 0 carries the context.
        assert torch.allclose(pts[:, 1, 2:], ctx, atol=1e-6)

    def test_bad_inputs_rejected(self) -> None:
        spec = type("Spec", (), {"horizon": 63, "dt": 1 / 252})()
        with pytest.raises(ValueError, match="shape"):
            augment_path(torch.randn(4, 62), torch.randn(4, 4), cumret_scale=0.2, spec=spec)
        with pytest.raises(ValueError, match="batch"):
            augment_path(torch.randn(4, 63), torch.randn(5, 4), cumret_scale=0.2, spec=spec)
        bad = torch.randn(4, 63)
        bad[0, 0] = math.nan
        with pytest.raises(ValueError, match="finite"):
            augment_path(bad, torch.randn(4, 4), cumret_scale=0.2, spec=spec)
        with pytest.raises(ValueError, match="positive"):
            augment_path(torch.randn(4, 63), torch.randn(4, 4), cumret_scale=-1.0, spec=spec)
