"""Internal gate v2: bootstrap-based terminal diagnostics + multi-lag ACF.

Replaces the overlapping-window terminal estimator with a
dependence-preserving block-bootstrap reference distribution.
All inputs are training-period internal data only.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import yaml

from neuralmarket.baselines.bootstrap import sample_block_bootstrap
from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.research.sde_windows import (
    FeatureNormalizer,
    FitSelectionSplit,
    WindowSpec,
    fit_cumret_scale,
)
from neuralmarket.models.neural_sde import ConditionalNeuralSde


@dataclass(frozen=True)
class GateSpecV2:
    """Frozen gate specification loaded from YAML."""

    bootstrap_method: str = "block"
    block_length: int = 22
    terminal_path_count: int = 1024
    generated_path_count: int = 1024
    horizon: int = 63
    bootstrap_seed: int = 8801
    dispersion_band_lo: float = 0.50
    dispersion_band_hi: float = 2.00
    acf_lags: tuple[int, ...] = (1, 2, 3, 5, 10, 20)
    acf_max_lag_error: float = 0.25
    acf_rmse_threshold: float = 0.15
    variance_ratio_lo: float = 0.50
    variance_ratio_hi: float = 2.00
    uniqueness_min: float = 0.99
    drift_diffusion_max: float = 0.50
    gate_seed: int = 7777

    def spec_hash(self) -> str:
        """Deterministic canonical hash of the gate specification."""
        return hashlib.sha256(
            canonical_dumps(
                {
                    "bootstrap_method": self.bootstrap_method,
                    "block_length": self.block_length,
                    "terminal_path_count": self.terminal_path_count,
                    "generated_path_count": self.generated_path_count,
                    "horizon": self.horizon,
                    "bootstrap_seed": self.bootstrap_seed,
                    "dispersion_band_lo": self.dispersion_band_lo,
                    "dispersion_band_hi": self.dispersion_band_hi,
                    "acf_lags": list(self.acf_lags),
                    "acf_max_lag_error": self.acf_max_lag_error,
                    "acf_rmse_threshold": self.acf_rmse_threshold,
                    "variance_ratio_lo": self.variance_ratio_lo,
                    "variance_ratio_hi": self.variance_ratio_hi,
                    "uniqueness_min": self.uniqueness_min,
                    "drift_diffusion_max": self.drift_diffusion_max,
                    "gate_seed": self.gate_seed,
                }
            ).encode()
        ).hexdigest()


def load_gate_spec_v2(path: str | None = None) -> GateSpecV2:
    """Load gate spec from YAML, or return defaults."""
    if path is None:
        return GateSpecV2()
    with open(path) as f:
        data = yaml.safe_load(f)
    bs = data.get("bootstrap", {})
    td = data.get("terminal_dispersion", {})
    sd = data.get("serial_dependence", {})
    vr = data.get("variance_ratio", {})
    pu = data.get("path_uniqueness", {})
    dd = data.get("drift_diffusion_ratio", {})
    return GateSpecV2(
        bootstrap_method=bs.get("method", "block"),
        block_length=bs.get("block_length", 22),
        terminal_path_count=bs.get("terminal_path_count", 1024),
        generated_path_count=bs.get("generated_path_count", 1024),
        horizon=bs.get("horizon", 63),
        bootstrap_seed=bs.get("seed", 8801),
        dispersion_band_lo=td.get("band_lo", 0.50),
        dispersion_band_hi=td.get("band_hi", 2.00),
        acf_lags=tuple(sd.get("lags", [1, 2, 3, 5, 10, 20])),
        acf_max_lag_error=sd.get("max_lag_error_threshold", 0.25),
        acf_rmse_threshold=sd.get("rmse_threshold", 0.15),
        variance_ratio_lo=vr.get("band_lo", 0.50),
        variance_ratio_hi=vr.get("band_hi", 2.00),
        uniqueness_min=pu.get("min_fraction", 0.99),
        drift_diffusion_max=dd.get("max_ratio", 0.50),
        gate_seed=data.get("terminal_dispersion", {}).get("gate_seed", 7777) if False else 7777,
    )


def _acf(x: np.ndarray, lag: int) -> float:
    """Sample autocorrelation at a given lag."""
    if lag <= 0 or lag >= len(x):
        return float("nan")
    xc = x - np.mean(x)
    return float(np.corrcoef(xc[:-lag], xc[lag:])[0, 1])


def _multi_lag_acf(returns_flat: np.ndarray, lags: tuple[int, ...]) -> dict[int, float]:
    """ACF at multiple lags."""
    return {lag: _acf(returns_flat, lag) for lag in lags}


def _acf_rmse(real_acf: dict[int, float], gen_acf: dict[int, float]) -> float:
    """RMSE of ACF differences across lags."""
    errors = []
    for lag in real_acf:
        r = real_acf[lag]
        g = gen_acf[lag]
        if math.isfinite(r) and math.isfinite(g):
            errors.append((r - g) ** 2)
    if not errors:
        return float("nan")
    return float(np.sqrt(np.mean(errors)))


def _acf_max_error(real_acf: dict[int, float], gen_acf: dict[int, float]) -> float:
    """Max absolute ACF difference across lags."""
    errors = []
    for lag in real_acf:
        r = real_acf[lag]
        g = gen_acf[lag]
        if math.isfinite(r) and math.isfinite(g):
            errors.append(abs(r - g))
    return float(max(errors)) if errors else float("nan")


def _wasserstein_1d(a: np.ndarray, b: np.ndarray) -> float:
    """1-Wasserstein distance between two 1-D samples."""
    a_sorted = np.sort(a)
    b_sorted = np.sort(b)
    n = max(len(a_sorted), len(b_sorted))
    a_interp = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a_sorted)), a_sorted)
    b_interp = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(b_sorted)), b_sorted)
    return float(np.mean(np.abs(a_interp - b_interp)))


def evaluate_gate_v2(
    model: ConditionalNeuralSde,
    split: FitSelectionSplit,
    normalizer: FeatureNormalizer,
    training_returns: torch.Tensor,
    spec: WindowSpec | None = None,
    gate_spec: GateSpecV2 | None = None,
    selection_returns_real: np.ndarray | None = None,
    sel_ctx_tensor: torch.Tensor | None = None,
) -> tuple[dict[str, Any], bool]:
    """Evaluate the v2 internal gate on selection data.

    Uses bootstrap-based terminal reference and multi-lag ACF.

    Args:
        model: Best-epoch internal model.
        split: Internal fit/selection split.
        normalizer: Training-fitted context normalizer.
        training_returns: Training returns tensor.
        spec: Window geometry.
        gate_spec: Frozen gate specification.
        selection_returns_real: Optional pre-computed selection real returns.
        sel_ctx_tensor: Optional pre-computed selection context tensor.

    Returns:
        (diagnostics, passed) tuple.
    """
    from neuralmarket.research.neural_sde_trainer_v2 import (
        _window_tensors,
    )
    from neuralmarket.research.neural_sde_trainer_v3 import (
        _drift_diffusion_rms,
    )

    spec = WindowSpec() if spec is None else spec
    gate_spec = GateSpecV2() if gate_spec is None else gate_spec
    cumret_scale = fit_cumret_scale(training_returns.detach().cpu().numpy(), spec.horizon)

    # Get selection real returns and context
    if selection_returns_real is None or sel_ctx_tensor is None:
        sel_ctx, sel_targets, _ = _window_tensors(
            split.selection_windows, normalizer, cumret_scale, spec
        )
        selection_returns_real = sel_targets.cpu().numpy()
        sel_ctx_tensor = sel_ctx
    else:
        sel_ctx = sel_ctx_tensor

    n_sel = selection_returns_real.shape[0]
    n_gen = gate_spec.generated_path_count
    n_real_boot = gate_spec.terminal_path_count

    # Generate model paths
    gate_gen = torch.Generator().manual_seed(gate_spec.gate_seed)
    model.eval()
    with torch.no_grad():
        noise = torch.randn(n_gen, spec.horizon, model.config.brownian_dim, generator=gate_gen)
        # Use first n_gen contexts (cycled if needed)
        gen_ctx = (
            sel_ctx_tensor[:n_gen]
            if n_gen <= n_sel
            else sel_ctx_tensor.repeat((n_gen // n_sel) + 1, 1)[:n_gen]
        )
        generated = model(gen_ctx, noise)

    gen_returns = generated.cpu().numpy()

    # Bootstrap real reference distribution
    real_flat = selection_returns_real.ravel()
    real_boot_returns = sample_block_bootstrap(
        real_flat,
        n_real_boot,
        spec.horizon,
        block_length=gate_spec.block_length,
        seed=gate_spec.bootstrap_seed,
    )

    # Terminal returns
    gen_terminal = gen_returns.sum(axis=1)
    real_boot_terminal = real_boot_returns.sum(axis=1)

    # --- Terminal dispersion ---
    gen_terminal_std = float(np.std(gen_terminal))
    real_boot_terminal_std = float(np.std(real_boot_terminal))
    dispersion_ratio = (
        gen_terminal_std / real_boot_terminal_std if real_boot_terminal_std > 0.0 else float("nan")
    )

    # --- Terminal Wasserstein ---
    raw_wasserstein = _wasserstein_1d(gen_terminal, real_boot_terminal)
    norm_wasserstein = (
        raw_wasserstein / real_boot_terminal_std if real_boot_terminal_std > 0.0 else float("nan")
    )

    # --- Daily variance ratio ---
    gen_var = float(np.var(gen_returns))
    real_var = float(np.var(selection_returns_real))
    variance_ratio = gen_var / real_var if real_var > 0.0 else float("nan")

    # --- Multi-lag ACF ---
    gen_flat = gen_returns.ravel()
    real_sel_flat = selection_returns_real.ravel()
    gen_acf = _multi_lag_acf(gen_flat, gate_spec.acf_lags)
    real_acf = _multi_lag_acf(real_sel_flat, gate_spec.acf_lags)
    acf_rmse = _acf_rmse(real_acf, gen_acf)
    acf_max_err = _acf_max_error(real_acf, gen_acf)

    # --- Volatility clustering diagnostics ---
    gen_abs_acf = _multi_lag_acf(np.abs(gen_flat), gate_spec.acf_lags)
    real_abs_acf = _multi_lag_acf(np.abs(real_sel_flat), gate_spec.acf_lags)
    gen_sq_acf = _multi_lag_acf(gen_flat**2, gate_spec.acf_lags)
    real_sq_acf = _multi_lag_acf(real_sel_flat**2, gate_spec.acf_lags)

    # --- Path uniqueness ---
    fingerprints = {
        tuple(float(v) for v in row.round(6))
        for row in gen_returns[: min(gen_returns.shape[0], 2048)]
    }
    uniqueness = len(fingerprints) / min(gen_returns.shape[0], 2048)

    # --- Drift/diffusion ratio ---
    drift_gen = torch.Generator().manual_seed(gate_spec.gate_seed + 1)
    drift_rms, diff_rms = _drift_diffusion_rms(model, sel_ctx, spec, 64, drift_gen)
    dd_ratio = drift_rms / diff_rms if diff_rms > 0.0 else float("inf")

    # --- Conditional variance diagnostic (matched path count) ---
    n_match = min(gen_returns.shape[0], selection_returns_real.shape[0])
    gen_per_path_var = np.var(gen_returns[:n_match], axis=1)
    real_per_path_var = np.var(selection_returns_real[:n_match], axis=1)
    log_gen_var = np.log(gen_per_path_var + 1e-12)
    log_real_var = np.log(real_per_path_var + 1e-12)
    corr_log_var = float(np.corrcoef(log_gen_var, log_real_var)[0, 1])

    # --- Gate criteria ---
    criterion_results: dict[str, bool] = {}
    criterion_results["variance_ratio"] = bool(
        math.isfinite(variance_ratio)
        and gate_spec.variance_ratio_lo <= variance_ratio <= gate_spec.variance_ratio_hi
    )
    criterion_results["terminal_dispersion"] = bool(
        math.isfinite(dispersion_ratio)
        and gate_spec.dispersion_band_lo <= dispersion_ratio <= gate_spec.dispersion_band_hi
    )
    criterion_results["uniqueness"] = bool(uniqueness >= gate_spec.uniqueness_min)
    criterion_results["acf_rmse"] = bool(
        math.isfinite(acf_rmse) and acf_rmse <= gate_spec.acf_rmse_threshold
    )
    criterion_results["acf_max_error"] = bool(
        math.isfinite(acf_max_err) and acf_max_err <= gate_spec.acf_max_lag_error
    )
    criterion_results["drift_diffusion_ratio"] = bool(
        math.isfinite(dd_ratio) and dd_ratio <= gate_spec.drift_diffusion_max
    )

    gate_passed = all(criterion_results.values())

    diagnostics: dict[str, Any] = {
        "gate_spec_hash": gate_spec.spec_hash(),
        "bootstrap_method": gate_spec.bootstrap_method,
        "bootstrap_block_length": gate_spec.block_length,
        "bootstrap_seed": gate_spec.bootstrap_seed,
        "n_real_bootstrap": n_real_boot,
        "n_generated": n_gen,
        # Terminal dispersion
        "real_bootstrap_terminal_std": real_boot_terminal_std,
        "generated_terminal_std": gen_terminal_std,
        "terminal_dispersion_ratio": dispersion_ratio,
        # Terminal distribution
        "terminal_wasserstein_raw": raw_wasserstein,
        "terminal_wasserstein_normalized": norm_wasserstein,
        # Daily variance
        "real_daily_variance": real_var,
        "generated_daily_variance": gen_var,
        "variance_ratio": variance_ratio,
        # Multi-lag ACF
        "acf_lags": list(gate_spec.acf_lags),
        "real_acf": {k: float(v) for k, v in real_acf.items()},
        "generated_acf": {k: float(v) for k, v in gen_acf.items()},
        "acf_rmse": acf_rmse,
        "acf_max_error": acf_max_err,
        # Volatility clustering (report-only)
        "real_abs_return_acf": {k: float(v) for k, v in real_abs_acf.items()},
        "generated_abs_return_acf": {k: float(v) for k, v in gen_abs_acf.items()},
        "real_sq_return_acf": {k: float(v) for k, v in real_sq_acf.items()},
        "generated_sq_return_acf": {k: float(v) for k, v in gen_sq_acf.items()},
        # Conditional variance (report-only)
        "cond_var_log_correlation": corr_log_var,
        "generated_per_path_var_max": float(np.max(gen_per_path_var)),
        "generated_per_path_var_min": float(np.min(gen_per_path_var)),
        "real_per_path_var_max": float(np.max(real_per_path_var)),
        "real_per_path_var_min": float(np.min(real_per_path_var)),
        "conditional_variance_matched_paths": n_match,
        # Other
        "path_uniqueness_fraction": uniqueness,
        "drift_increment_rms": drift_rms,
        "diffusion_increment_rms": diff_rms,
        "drift_diffusion_rms_ratio": dd_ratio,
        "gate_seed": gate_spec.gate_seed,
        "criterion_results": criterion_results,
        "gate_passed": gate_passed,
    }
    return diagnostics, gate_passed
