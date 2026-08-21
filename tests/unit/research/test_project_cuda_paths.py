"""Project-wide CUDA enforcement: Gate-v2 and per-path coverage.

Gated by torch.cuda.is_available(); never performs governed --execute.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import torch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_gate_v2_real_cuda_synthetic():
    """Real evaluate_gate_v2 on cuda:0 with synthetic data — must stay on CUDA."""
    import datetime

    import numpy as np

    from neuralmarket.core.device import configure_device_determinism, resolve_device
    from neuralmarket.core.runtime_identity import build_runtime_identity
    from neuralmarket.data.research.sde_windows import (
        WindowSpec,
        build_windows,
        compute_context_features,
        fit_feature_normalizer,
        split_fit_selection,
    )
    from neuralmarket.models.structured_vol_sde import StructuredVolatilityNeuralSde
    from neuralmarket.research.neural_sde_internal_gate import evaluate_gate_v2, load_gate_spec_v2

    device = resolve_device("cuda")
    configure_device_determinism(device, enabled=True)
    rt = build_runtime_identity(requested_device="cuda", resolved_device=str(device))
    assert rt["resolved_device"] == "cuda"
    assert len(rt["runtime_identity_sha256"]) == 64

    model = StructuredVolatilityNeuralSde().to(device=device)
    np.random.seed(42)
    training_returns = np.random.randn(600).astype(np.float64) * 0.01
    spec = WindowSpec()
    dates = [datetime.date(2020, 1, 1) + datetime.timedelta(days=i) for i in range(601)]
    date_strs = [d.isoformat() for d in dates]
    windows = build_windows(training_returns, tuple(date_strs[1:]), spec)
    feature_matrix = np.stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    split = split_fit_selection(windows, 0.8, spec)
    training_returns_tensor = torch.tensor(training_returns, dtype=torch.float32, device=device)
    gate_spec = load_gate_spec_v2(str(REPO / "configs/research/neural_sde_internal_gate_v2.yaml"))
    diagnostics, passed = evaluate_gate_v2(
        model, split, normalizer, training_returns_tensor, spec, gate_spec, device=device
    )
    assert isinstance(diagnostics, dict)
    assert isinstance(passed, bool)
    assert "variance_ratio" in diagnostics
    assert "terminal_dispersion_ratio" in diagnostics
    assert "criterion_results" in diagnostics
    assert str(next(model.parameters()).device).startswith("cuda")
    # Noise/context must have been on CUDA — if Gate had used CPU, this would have raised
    assert "path_uniqueness_fraction" in diagnostics


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_trainer_v3_cuda_one_step_synthetic():
    """One CUDA train step via train_internal_v3 with tiny synthetic split."""
    import datetime

    import numpy as np

    from neuralmarket.core.device import resolve_device
    from neuralmarket.data.research.sde_windows import (
        WindowSpec,
        build_windows,
        compute_context_features,
        fit_cumret_scale,
        fit_feature_normalizer,
        split_fit_selection,
    )
    from neuralmarket.models.structured_vol_sde import StructuredVolatilityNeuralSde
    from neuralmarket.research.neural_sde_trainer import TrainingConfig
    from neuralmarket.research.neural_sde_trainer_v3 import build_v3_statistics, train_internal_v3

    device = resolve_device("cuda")
    np.random.seed(7)
    training_returns = np.random.randn(400).astype(np.float64) * 0.01
    spec = WindowSpec()
    dates = [datetime.date(2020, 1, 1) + datetime.timedelta(days=i) for i in range(401)]
    date_strs = [d.isoformat() for d in dates]
    windows = build_windows(training_returns, tuple(date_strs[1:]), spec)
    feature_matrix = np.stack([compute_context_features(w, spec).array() for w in windows], axis=0)
    normalizer = fit_feature_normalizer(feature_matrix)
    cumret_scale = fit_cumret_scale(training_returns, spec.horizon)
    split = split_fit_selection(windows, 0.8, spec)
    statistics = build_v3_statistics(split.fit_windows, normalizer, cumret_scale, spec, __import__("neuralmarket.research.neural_sde_trainer_v3", fromlist=["V3ObjectiveConfig"]).V3ObjectiveConfig())
    from neuralmarket.models.neural_sde import set_deterministic_seeds

    set_deterministic_seeds(1234)
    model = StructuredVolatilityNeuralSde().to(device=device)
    training_returns_tensor = torch.tensor(training_returns, dtype=torch.float32, device=device)
    cfg = TrainingConfig(max_epochs=2, patience=10, batch_size=16, model_init_seed=1234, data_seed=1235)
    outcome = train_internal_v3(model, cfg, split, normalizer, training_returns_tensor, statistics, spec, None, device=device)
    assert outcome.best_epoch >= 0
    assert str(next(model.parameters()).device).startswith("cuda")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_model_simulate_structured_cuda():
    from neuralmarket.core.device import resolve_device
    from neuralmarket.core.trainer_device import make_generator
    from neuralmarket.models.structured_vol_sde import StructuredVolatilityNeuralSde

    device = resolve_device("cuda")
    model = StructuredVolatilityNeuralSde().to(device=device)
    ctx = torch.randn(4, model.config.n_context, device=device)
    gen = make_generator(device, 999)
    noise = torch.randn(4, model.config.horizon, model.config.brownian_dim, generator=gen, device=device)
    out = model(ctx, noise)
    assert str(out.device).startswith("cuda")
    loss = out.sum()
    loss.backward()
    for p in model.parameters():
        if p.grad is not None:
            assert torch.isfinite(p.grad).all()
