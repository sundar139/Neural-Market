"""RBF signature MMD, standardizer, bandwidth, and anti-collapse penalty tests."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from neuralmarket.models.signature_mmd import (
    fit_rbf_bandwidth_sq,
    fit_signature_standardizer,
    log_variance_penalty,
    rbf_mmd_sq,
    signature_feature_dim,
    signature_feature_vector,
)

pytestmark = pytest.mark.unit


def _vecs(
    n: int, dim: int = 8, seed: int = 0, scale: float = 1.0, shift: float = 0.0
) -> torch.Tensor:
    rng = np.random.default_rng(seed)
    return torch.tensor(rng.normal(shift, scale, size=(n, dim)), dtype=torch.float32)


class TestRbfMmd:
    def test_identical_sample_sets_near_zero(self) -> None:
        a = _vecs(64, seed=1)
        bw = fit_rbf_bandwidth_sq(a)
        mmd = float(rbf_mmd_sq(a, a.clone(), bw))
        assert abs(mmd) < 1e-6

    def test_shifted_distributions_positive(self) -> None:
        a = _vecs(64, seed=2)
        b = _vecs(64, seed=3, shift=2.0)
        bw = fit_rbf_bandwidth_sq(torch.cat((a, b), dim=0))
        assert float(rbf_mmd_sq(a, b, bw)) > 0.0

    def test_equal_mean_different_dispersion_detectable(self) -> None:
        # THE v1 failure mode: identical mean vector, different per-path spread.
        # v1's mean-matching loss is ~0 here; RBF-MMD must detect the spread.
        mean = torch.tensor([0.5, -0.3, 0.2, 1.0, -0.1, 0.7, 0.0, 0.4])
        z = torch.randn(64, 8)
        z = z - z.mean(dim=0)  # exactly centered noise (sample mean 0)
        tight = mean.unsqueeze(0) + 0.001 * z
        spread = mean.unsqueeze(0) + 4.0 * 0.001 * z  # same mean, 16x larger variance
        assert torch.norm(tight.mean(dim=0) - spread.mean(dim=0)) < 1e-5
        bw = fit_rbf_bandwidth_sq(torch.cat((tight, spread), dim=0))
        mmd = float(rbf_mmd_sq(tight, spread, bw))
        assert mmd > 1e-4

    def test_deterministic(self) -> None:
        a = _vecs(48, seed=4)
        b = _vecs(48, seed=5, shift=1.0)
        bw = fit_rbf_bandwidth_sq(a)
        assert float(rbf_mmd_sq(a, b, bw)) == float(rbf_mmd_sq(a, b, bw))

    def test_symmetric(self) -> None:
        a = _vecs(48, seed=6)
        b = _vecs(48, seed=7, shift=0.5)
        bw = fit_rbf_bandwidth_sq(torch.cat((a, b), dim=0))
        assert abs(float(rbf_mmd_sq(a, b, bw)) - float(rbf_mmd_sq(b, a, bw))) < 1e-6

    def test_non_negative_within_tolerance(self) -> None:
        rng = np.random.default_rng(8)
        a = torch.tensor(rng.normal(size=(32, 8)), dtype=torch.float32)
        b = torch.tensor(rng.normal(size=(32, 8)), dtype=torch.float32)
        bw = fit_rbf_bandwidth_sq(a)
        value = float(rbf_mmd_sq(a, b, bw))
        assert value > -1e-6

    def test_finite_gradients_to_generated(self) -> None:
        real = _vecs(16, seed=9)
        gen = torch.tensor(
            np.random.default_rng(10).normal(size=(16, 8)), dtype=torch.float32, requires_grad=True
        )
        bw = fit_rbf_bandwidth_sq(real)
        loss = rbf_mmd_sq(real, gen, bw)
        loss.backward()
        assert gen.grad is not None
        assert torch.isfinite(gen.grad).all()
        assert gen.grad.abs().sum() > 0

    def test_malformed_inputs_rejected(self) -> None:
        a = _vecs(16, seed=11)
        bw = fit_rbf_bandwidth_sq(a)
        with pytest.raises(ValueError, match="same_dim"):
            rbf_mmd_sq(a, torch.zeros(8, 5), bw)
        bad = torch.tensor([[1.0, np.nan, 0.0, 0, 0, 0, 0, 0]])
        with pytest.raises(ValueError, match="finite"):
            rbf_mmd_sq(a, bad, bw)
        with pytest.raises(ValueError, match="positive and finite"):
            rbf_mmd_sq(a, a, 0.0)


class TestBandwidth:
    def test_bandwidth_from_real_features_and_deterministic(self) -> None:
        a = _vecs(40, dim=8, seed=12)
        bw1 = fit_rbf_bandwidth_sq(a)
        bw2 = fit_rbf_bandwidth_sq(a)
        assert bw1 == bw2
        assert bw1 > 0 and np.isfinite(bw1)
        # Larger spread -> larger bandwidth.
        wide = _vecs(40, dim=8, seed=13, scale=4.0)
        assert fit_rbf_bandwidth_sq(wide) > bw1

    def test_zero_median_fails_closed(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            fit_rbf_bandwidth_sq(torch.zeros(20, 8))

    def test_non_finite_fails_closed(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            fit_rbf_bandwidth_sq(torch.tensor([[np.nan, 1.0]] * 5))
        with pytest.raises(ValueError, match="at least two"):
            fit_rbf_bandwidth_sq(torch.ones(1, 8))


class TestStandardizer:
    def test_fit_and_standardize(self) -> None:
        matrix = _vecs(64, dim=16, seed=14, scale=3.0)
        stdz = fit_signature_standardizer(matrix)
        z = stdz.standardize(matrix)
        assert torch.allclose(z.mean(dim=0), torch.zeros(16), atol=1e-5)
        assert torch.allclose(z.std(dim=0, unbiased=True), torch.ones(16), atol=1e-2)
        assert len(stdz.standardization_hash()) == 64

    def test_near_zero_dimensions_handled_safely(self) -> None:
        # Near-constant coordinate: floored std must keep standardization finite
        # and bounded (no NaN/inf from a divide by zero).
        matrix = torch.randn(32, 8)
        matrix[:, 3] = 0.42 + 1e-9 * torch.randn(32)
        stdz = fit_signature_standardizer(matrix)
        assert stdz.stds[3] > 0.0
        z = stdz.standardize(matrix)
        assert torch.isfinite(z).all()
        # Value stays small: (1e-9 noise) / (1e-8 floor) ~ O(0.1).
        assert z[:, 3].abs().max() < 5.0

    def test_validation_leakage_impossible_by_api(self) -> None:
        import inspect

        from neuralmarket.models import signature_mmd as module

        for fn in ("fit_signature_standardizer", "fit_rbf_bandwidth_sq"):
            sig = inspect.signature(getattr(module, fn))
            assert "validation" not in sig.parameters

    def test_non_finite_and_width_mismatch_rejected(self) -> None:
        stdz = fit_signature_standardizer(_vecs(32, dim=4, seed=15))
        with pytest.raises(ValueError, match="finite"):
            stdz.standardize(torch.tensor([[np.nan, 0.0, 0.0, 0.0]]))
        with pytest.raises(ValueError, match="width"):
            stdz.standardize(torch.zeros(1, 3))


class TestVariancePenalty:
    def test_zero_when_variance_matches_target(self) -> None:
        generated = torch.randn(64, 63) * 0.02
        target_log_var = float(torch.log(generated.var(dim=None, unbiased=False) + 1e-12))
        value = float(log_variance_penalty(generated, target_log_var))
        assert abs(value) < 1e-6

    def test_positive_under_collapse(self) -> None:
        # Real variance from a spread-out target; generated collapsed.
        target = torch.randn(64, 63) * 0.02
        collapsed = torch.zeros_like(target) + 1e-6
        target_log_var = float(torch.log(target.var(dim=None, unbiased=False) + 1e-12))
        value = float(log_variance_penalty(collapsed, target_log_var))
        assert value > 1e-4

    def test_finite_gradient(self) -> None:
        gen = torch.randn(16, 63, requires_grad=True)  # leaf, ~N(0,1)
        target = torch.randn(16, 63)
        target_log_var = float(torch.log(target.var(dim=None, unbiased=False) + 1e-12))
        loss = log_variance_penalty(gen, target_log_var)
        loss.backward()
        assert gen.grad is not None and torch.isfinite(gen.grad).all()
        assert gen.grad.abs().sum() > 0

    def test_train_only_target_api(self) -> None:
        import inspect

        from neuralmarket.models import signature_mmd as module

        assert "validation" not in inspect.signature(module.log_variance_penalty).parameters


class TestFeatureVector:
    def test_concatenation_and_dimension(self) -> None:
        features = {
            1: torch.randn(4, 2),
            2: torch.randn(4, 4),
            3: torch.randn(4, 8),
        }
        vector = signature_feature_vector(features)
        assert vector.shape == (4, 2 + 4 + 8)
        assert signature_feature_dim(2, 3) == 2 + 4 + 8
        assert signature_feature_dim(2, 1) == 2

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            signature_feature_vector({})
