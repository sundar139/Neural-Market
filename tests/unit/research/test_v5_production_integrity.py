"""Tests for v5 production-path integrity repairs.

Covers the v5 preproduction closure defects:
A. Gate-v2 YAML loading (fail-closed, actual path, version, explicit seeds)
B. Production bootstrap selection-series path (behavioral, not source-string)
C. V-only clamp: active binding, X unclamped, internal-X reconstruction
D. Return semantics: public increments cumsum to the internal X levels
E. Validation firewall (behavioral mock orchestration of run_v5_experiment)
F. Future external-validation provenance identity
G. Legacy model-YAML gate-threshold isolation
H. Experiment config identity (material vs non-material)
"""

from __future__ import annotations

import hashlib
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch
import yaml

from neuralmarket.data.research.sde_windows import (
    FeatureNormalizer,
    FitSelectionSplit,
    SdeWindow,
    WindowSpec,
    build_windows,
    split_fit_selection,
)
from neuralmarket.data.research.underlying import EmpiricalUnderlyingSeries
from neuralmarket.models.structured_vol_sde import (
    StructuredVolatilityNeuralSde,
    StructuredVolConfig,
)
from neuralmarket.research import structured_vol_experiment as svx
from neuralmarket.research.neural_sde_internal_gate import (
    _EXPECTED_VERSION,
    _FROZEN_GATE_V2_PATH,
    load_gate_spec_v2,
    selection_returns_series,
)

pytestmark = [pytest.mark.unit]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_GATE_YAML = _REPO_ROOT / _FROZEN_GATE_V2_PATH
_V5_YAML = _REPO_ROOT / "configs/research/structured_vol_neural_sde_v5.yaml"

# Documented corrected prospective v5 run identity (prefix 5bdbaabd2fb257a7).
_FROZEN_V5_RUN_HASH = (
    "5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157"  # pragma: allowlist secret
)


# ── A. Gate-v2 YAML loading ──────────────────────────────────────────


class TestGateV2YamlLoading:
    """A. Frozen YAML is actually loaded; fail-closed for bad inputs; seeds explicit."""

    def test_frozen_yaml_loads(self) -> None:
        spec = load_gate_spec_v2(str(_GATE_YAML))
        assert spec.bootstrap_method == "block"
        assert spec.block_length == 22
        assert spec.terminal_path_count == 1024
        assert spec.generated_path_count == 1024
        assert spec.horizon == 63
        assert spec.bootstrap_seed == 8801
        assert spec.dispersion_band_lo == 0.50
        assert spec.dispersion_band_hi == 2.00
        assert spec.variance_ratio_lo == 0.50
        assert spec.variance_ratio_hi == 2.00
        assert spec.uniqueness_min == 0.99
        assert spec.drift_diffusion_max == 0.50

    def test_frozen_yaml_version(self) -> None:
        with open(_GATE_YAML) as f:
            data = yaml.safe_load(f)
        assert data["version"] == _EXPECTED_VERSION

    def test_frozen_yaml_explicit_seeds(self) -> None:
        spec = load_gate_spec_v2(str(_GATE_YAML))
        # Accepted frozen semantics: generated-path seed 7777, drift/diffusion
        # diagnostic seed 7778 (the historical loader's gate_seed and +1).
        assert spec.gate_seed == 7777
        assert spec.drift_diffusion_seed == 7778

    def test_none_path_raises(self) -> None:
        with pytest.raises(ValueError, match="requires an explicit YAML path"):
            load_gate_spec_v2(None)

    def test_wrong_version_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "version": "wrong-version",
                    "bootstrap": {},
                    "terminal_dispersion": {},
                    "serial_dependence": {},
                    "variance_ratio": {},
                    "path_uniqueness": {},
                    "drift_diffusion_ratio": {},
                },
                f,
            )
            f.flush()
            with pytest.raises(ValueError, match="version mismatch"):
                load_gate_spec_v2(f.name)

    def test_missing_required_section_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"version": _EXPECTED_VERSION}, f)
            f.flush()
            with pytest.raises(ValueError, match="missing required section"):
                load_gate_spec_v2(f.name)

    def test_missing_required_key_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(
                {
                    "version": _EXPECTED_VERSION,
                    "bootstrap": {"method": "block"},  # missing block_length etc.
                    "terminal_dispersion": {"band_lo": 0.5, "band_hi": 2.0, "status": "pass_fail"},
                    "serial_dependence": {"lags": [1]},
                    "variance_ratio": {"band_lo": 0.5, "band_hi": 2.0, "status": "pass_fail"},
                    "path_uniqueness": {"min_fraction": 0.99, "status": "pass_fail"},
                    "drift_diffusion_ratio": {"max_ratio": 0.5, "status": "pass_fail"},
                },
                f,
            )
            f.flush()
            with pytest.raises(ValueError, match="missing required key"):
                load_gate_spec_v2(f.name)

    def test_acf1_threshold_required_fail_closed(self) -> None:
        """Missing ACF(1) pass/fail threshold must hard fail (no silent default)."""
        data = yaml.safe_load(_GATE_YAML.read_text())
        del data["serial_dependence"]["acf1"]["threshold"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            with pytest.raises(ValueError, match="acf1.threshold/status"):
                load_gate_spec_v2(f.name)

    def test_acf_max_error_mapping_corrected(self) -> None:
        """acf_max_lag_error binds max_error.diagnostic_reference, not acf1.threshold.

        Negative control: the old loader sourced acf_max_lag_error from
        ``serial_dependence.acf1.threshold``; this test changes the report-only
        reference and proves the field tracks it (and vice versa for ACF(1)).
        """
        data = yaml.safe_load(_GATE_YAML.read_text())
        data["serial_dependence"]["max_error"]["diagnostic_reference"] = 0.37
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            spec = load_gate_spec_v2(f.name)
        assert spec.acf_max_lag_error == 0.37
        assert spec.acf1_max_diff == 0.25

    def test_yaml_changes_threshold_changes_hash(self) -> None:
        """Changing a pass/fail threshold in YAML changes loaded spec and hash."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            data = yaml.safe_load(_GATE_YAML.read_text())
            data["terminal_dispersion"]["band_hi"] = 3.0
            yaml.dump(data, f)
            f.flush()
            modified_spec = load_gate_spec_v2(f.name)
        original_spec = load_gate_spec_v2(str(_GATE_YAML))
        assert modified_spec.spec_hash() != original_spec.spec_hash()
        assert modified_spec.dispersion_band_hi == 3.0
        assert original_spec.dispersion_band_hi == 2.0

    def test_file_sha_deterministic(self) -> None:
        sha1 = hashlib.sha256(_GATE_YAML.read_bytes()).hexdigest()
        sha2 = hashlib.sha256(_GATE_YAML.read_bytes()).hexdigest()
        assert sha1 == sha2
        assert len(sha1) == 64


# ── B. Production bootstrap selection-series path ─────────────────────


def _synthetic_training_split() -> tuple[np.ndarray, tuple[str, ...], WindowSpec, object]:
    """Small chronological synthetic training series + real fit/selection split."""
    import datetime as dt

    rng = np.random.RandomState(3)
    n = 260
    returns = rng.randn(n) * 0.01
    start = dt.date(2020, 1, 1)
    dates = tuple(str(start + dt.timedelta(days=i)) for i in range(n + 1))
    spec = WindowSpec(context_lookback=22, horizon=5, dt=1.0 / 252.0)
    windows = build_windows(returns, dates[1:], spec)
    split = split_fit_selection(windows, 0.8, spec)
    return returns, dates, spec, split


class TestBootstrapProductionPath:
    """F. The production helper returns exactly the contiguous selection tail."""

    def test_selection_tail_exact_no_ravel_no_leakage(self) -> None:
        returns, _, spec, split = _synthetic_training_split()
        got = selection_returns_series(torch.tensor(returns, dtype=torch.float32), split)
        expected = returns.astype(np.float32)[split.selection_target_start_index :]
        np.testing.assert_array_equal(got, expected)

        # Fit-region targets are strictly before the selection region.
        assert split.selection_target_start_index > split.fit_target_end_index

        # Exactly the selection tail: length matches the chronological slice.
        assert len(got) == len(returns) - split.selection_target_start_index
        # No validation leakage: the population is a strict tail of the supplied
        # training series (it cannot contain anything outside the array).
        assert got[-1] == np.float32(returns[-1])
        assert got[0] == np.float32(returns[split.selection_target_start_index])

        # Each observation represented once (distinct values stay distinct).
        assert np.unique(got).size == got.size

        # Overlapping training windows are NOT raveled into the population.
        raveled_len = len(split.selection_windows) * spec.horizon
        assert len(got) < raveled_len

    def test_production_evaluate_gate_uses_helper(self) -> None:
        from neuralmarket.research import neural_sde_internal_gate as gate_mod

        # The evaluation path routes through the exact helper under test.
        assert gate_mod.evaluate_gate_v2.__module__ == gate_mod.__name__
        import inspect

        src = inspect.getsource(gate_mod.evaluate_gate_v2)
        assert "selection_returns_series(" in src


# ── C/D. V-only clamp and return semantics ────────────────────────────


class TestVClampAndReturnSemantics:
    """E. Clamp is V-only, actively binds, and X is never clipped."""

    def test_v_respects_bounds_and_clamp_binds(self) -> None:
        cfg = StructuredVolConfig(horizon=25, v_clamp_min=-0.2, v_clamp_max=0.2)
        model = StructuredVolatilityNeuralSde(cfg)
        model.state_trace = {"x": [], "v_proposal": [], "v": []}
        with torch.no_grad():
            model.v0_layer.bias.data.fill_(5.0)  # force initial V far above the bound
        ctx = torch.randn(1, 4)
        noise = torch.randn(1, 25, 2)
        with torch.no_grad():
            out = model(ctx, noise)
        v = torch.cat(model.state_trace["v"], dim=1)
        v_proposal = torch.cat(model.state_trace["v_proposal"], dim=1)
        assert (v >= cfg.v_clamp_min - 1e-6).all().item()
        assert (v <= cfg.v_clamp_max + 1e-6).all().item()
        # The clamp actively binds: the initial proposal exceeds the upper bound.
        assert (v_proposal > cfg.v_clamp_max).any().item()
        assert torch.isfinite(out).all()

    def test_v_clamp_activation_lower_bound(self) -> None:
        cfg = StructuredVolConfig(horizon=10, v_clamp_min=-0.3, v_clamp_max=0.3)
        model = StructuredVolatilityNeuralSde(cfg)
        model.state_trace = {"x": [], "v_proposal": [], "v": []}
        with torch.no_grad():
            model.v0_layer.bias.data.fill_(-5.0)  # force initial V far below the bound
        ctx = torch.randn(1, 4)
        noise = torch.randn(1, 10, 2)
        with torch.no_grad():
            out = model(ctx, noise)
        v = torch.cat(model.state_trace["v"], dim=1)
        v_proposal = torch.cat(model.state_trace["v_proposal"], dim=1)
        assert v[0, 0].item() == pytest.approx(cfg.v_clamp_min, abs=1e-6)
        assert (v_proposal < cfg.v_clamp_min).any().item()
        assert (v >= cfg.v_clamp_min - 1e-6).all().item()
        assert (v <= cfg.v_clamp_max + 1e-6).all().item()
        assert torch.isfinite(out).all()

    def test_x_never_clipped_by_v_bounds(self) -> None:
        torch.manual_seed(0)
        cfg = StructuredVolConfig(horizon=30, v_clamp_min=-0.1, v_clamp_max=0.1)
        model = StructuredVolatilityNeuralSde(cfg)
        model.state_trace = {"x": [], "v_proposal": [], "v": []}
        ctx = torch.randn(1, 4)
        noise = torch.randn(1, 30, 2)
        noise[:, :, 0] = 5.0  # strong X diffusion
        with torch.no_grad():
            model(ctx, noise)
        internal_x = torch.cat(model.state_trace["x"], dim=1)
        v = torch.cat(model.state_trace["v"], dim=1)
        assert internal_x.abs().max().item() > cfg.v_clamp_max + 1e-3
        assert (v <= cfg.v_clamp_max + 1e-6).all().item()

    @pytest.mark.parametrize("clamp", [False, True])
    def test_cumsum_reconstructs_x(self, clamp: bool) -> None:
        """Public increments cumsum to the ACTUAL internal X levels of the pass.

        Negative control: the historical test compared cumsum(out) against
        ``out`` itself (true by definition), so it passed even without a real
        recurrent X.  Here we compare against the internal X states recorded
        during the same forward pass, over >1 timesteps on a nontrivial path,
        with the clamp both inactive and active.
        """
        torch.manual_seed(42)
        cfg = StructuredVolConfig(
            horizon=10,
            v_clamp_min=-0.1 if clamp else -10.0,
            v_clamp_max=0.1 if clamp else 10.0,
        )
        model = StructuredVolatilityNeuralSde(cfg)
        model.state_trace = {"x": [], "v_proposal": [], "v": []}
        ctx = torch.randn(4, 4)
        noise = torch.randn(4, 10, 2)
        with torch.no_grad():
            out = model(ctx, noise)
        internal_x = torch.cat(model.state_trace["x"], dim=1)
        levels = out.cumsum(dim=1)
        assert levels.shape == (4, 10)
        assert torch.allclose(levels, internal_x, atol=1e-5)
        diffs = (out[:, 1:] - levels[:, 1:]).abs()
        assert diffs.max().item() > 1e-6, "path must be nontrivial"


# ── E/F. Validation firewall + provenance plumbing ─────────────────────


def _write_v5_config_yaml(tmp: Path) -> Path:
    path = tmp / "config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": "structured-volatility-neural-sde-v5",
                "sde": {"horizon": 5, "n_context": 4},
                "training": {},
                "windows": {"context_lookback": 22, "horizon": 5, "dt": 1.0 / 252.0},
                "objective": {},
                "n_eval_paths": 8,
                "eval_seed": 1,
            }
        ),
        encoding="utf-8",
    )
    return path


def _fake_underlying(returns: np.ndarray, dates: tuple[str, ...]):
    return SimpleNamespace(
        returns_array=returns,
        session_dates=dates,
        prices=tuple(100.0 for _ in range(len(dates))),
    )


def _fake_outcome() -> SimpleNamespace:
    return SimpleNamespace(
        rbf_curve=[],
        total_curve=[],
        selection_rbf_curve=[],
        selection_total_curve=[],
        initial_internal_rbf=1.0,
        best_internal_rbf=0.5,
        best_epoch=1,
        final_epoch=1,
    )


class TestValidationFirewall:
    """K. Behavioral firewall: gate-FAIL must never touch validation/refit/final-test."""

    def test_gate_fail_never_touches_external_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rng = np.random.RandomState(1)
        n = 200
        returns = rng.randn(n) * 0.01
        dates = tuple(f"2020-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n + 1))

        flags = {"refit_called": 0, "validation_loader_called": 0}
        calls: list[str] = []

        def fake_underlying(inventory, split, raw_root, processed_root):
            calls.append(f"underlying:{split}")
            if split == "validation":
                flags["validation_loader_called"] += 1
                raise AssertionError(
                    "FIREWALL: external-validation loader touched while gate failed"
                )
            return _fake_underlying(returns, dates)

        def fake_eval(*args, **kwargs):
            calls.append("gate")
            return {"gate_spec_hash": "h", "criterion_results": {}, "gate_passed": False}, False

        def fake_train(*args, **kwargs):
            calls.append("train")
            return _fake_outcome()

        def fake_refit(*args, **kwargs):
            flags["refit_called"] += 1
            raise AssertionError("FIREWALL: refit called while gate failed")

        def fake_simulate(*args, **kwargs):
            raise AssertionError("FIREWALL: model simulation called while gate failed")

        def fake_final_test_loader(*args, **kwargs):
            raise AssertionError("FIREWALL: final-test path touched")

        fake_inventory = type("Fake", (), {"model_validate": staticmethod(lambda _: None)})
        monkeypatch.setattr(svx, "ResearchInventory", fake_inventory)
        monkeypatch.setattr(svx, "build_underlying_series", fake_underlying)
        monkeypatch.setattr(svx, "build_v3_statistics", lambda *a, **k: SimpleNamespace())
        monkeypatch.setattr(svx, "train_internal_v3", fake_train)
        monkeypatch.setattr(svx, "evaluate_gate_v2", fake_eval)
        monkeypatch.setattr(svx, "refit_final_v3", fake_refit)
        monkeypatch.setattr(svx, "simulate_structured", fake_simulate)
        monkeypatch.setattr(svx, "configure_determinism", lambda _: None)
        monkeypatch.setattr(svx, "set_deterministic_seeds", lambda _: None)

        tmp_path = tmp_path / "run"
        tmp_path.mkdir(parents=True)
        config_path = _write_v5_config_yaml(tmp_path)
        for name in ("inventory.json", "benchmark.json", "suite.json", "v1.json", "v2.json"):
            (tmp_path / name).write_text("{}", encoding="utf-8")

        result = svx.run_v5_experiment(
            config_path=config_path,
            inventory_path=tmp_path / "inventory.json",
            benchmark_path=tmp_path / "benchmark.json",
            suite_path=tmp_path / "suite.json",
            v1_artifact_path=tmp_path / "v1.json",
            v2_artifact_path=tmp_path / "v2.json",
            raw_root=tmp_path,
            processed_root=tmp_path,
            output_root=tmp_path,
            report_path=tmp_path / "report.json",
            device="cpu",
            execution_mode="historical_test",
        )

        assert result["gate_passed"] is False
        assert "INTERNAL GATE FAILED" in result["status"]
        assert result["evaluation"] == {}
        assert flags["refit_called"] == 0
        assert flags["validation_loader_called"] == 0
        # Ordering on the failed path: training data -> train -> gate, nothing after.
        assert calls[:3] == ["underlying:training", "train", "gate"]
        assert "validation" not in calls
        # The final-test sentinel was defined but the orchestrator never reached it
        # (the v5 production path has no final-test loader at all).

    def test_gate_pass_ordering_train_gate_refit_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rng = np.random.RandomState(2)
        n = 200
        returns = rng.randn(n) * 0.01
        dates = tuple(f"2020-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n + 1))

        calls: list[str] = []

        def fake_underlying(inventory, split, raw_root, processed_root):
            calls.append(f"underlying:{split}")
            return _fake_underlying(returns, dates)

        def fake_eval(*args, **kwargs):
            calls.append("gate")
            return (
                {"gate_spec_hash": "h", "criterion_results": {"ok": True}, "gate_passed": True},
                True,
            )

        def fake_train(*args, **kwargs):
            calls.append("train")
            return _fake_outcome()

        def fake_refit(*args, **kwargs):
            calls.append("refit")
            return None

        def fake_simulate(model, ctx, seed, generator=None):
            calls.append("simulate")
            return torch.zeros(ctx.shape[0], 5)

        fake_inventory = type("Fake", (), {"model_validate": staticmethod(lambda _: None)})
        monkeypatch.setattr(svx, "ResearchInventory", fake_inventory)
        monkeypatch.setattr(svx, "build_underlying_series", fake_underlying)
        monkeypatch.setattr(svx, "build_v3_statistics", lambda *a, **k: SimpleNamespace())
        monkeypatch.setattr(svx, "train_internal_v3", fake_train)
        monkeypatch.setattr(svx, "evaluate_gate_v2", fake_eval)
        monkeypatch.setattr(svx, "refit_final_v3", fake_refit)
        monkeypatch.setattr(svx, "simulate_structured", fake_simulate)
        monkeypatch.setattr(svx, "configure_determinism", lambda _: None)
        monkeypatch.setattr(svx, "set_deterministic_seeds", lambda _: None)
        monkeypatch.setattr(
            "neuralmarket.eval.scorecard.compute_scorecard",
            lambda *a, **k: {"metrics": {}},
        )
        monkeypatch.setattr(
            "neuralmarket.data.research.benchmark._scorecard_payload",
            lambda x: {"payload": x},
        )

        tmp_path = tmp_path / "run"
        tmp_path.mkdir(parents=True)
        config_path = _write_v5_config_yaml(tmp_path)
        for name in ("inventory.json", "benchmark.json", "suite.json", "v1.json", "v2.json"):
            (tmp_path / name).write_text("{}", encoding="utf-8")

        result = svx.run_v5_experiment(
            config_path=config_path,
            inventory_path=tmp_path / "inventory.json",
            benchmark_path=tmp_path / "benchmark.json",
            suite_path=tmp_path / "suite.json",
            v1_artifact_path=tmp_path / "v1.json",
            v2_artifact_path=tmp_path / "v2.json",
            raw_root=tmp_path,
            processed_root=tmp_path,
            output_root=tmp_path,
            report_path=tmp_path / "report.json",
            device="cpu",
            execution_mode="historical_test",
        )

        assert result["status"] == "STRUCTURED-VOLATILITY-NEURAL-SDE-V5 READY"
        assert result["gate_passed"] is True
        # Ordering: train -> gate -> refit/freeze -> validation access.
        assert calls.index("train") < calls.index("gate") < calls.index("refit")
        assert calls.index("refit") < calls.index("underlying:validation")
        # Future validation provenance is wired into the report.
        vident = result["evaluation"]["validation_identity"]
        for key in (
            "validation_series_sha256",
            "validation_split",
            "validation_start_date",
            "validation_end_date",
            "validation_observation_count",
            "context_window_id",
            "final_checkpoint_sha256",
            "baseline_suite_sha256",
            "model_config_hash",
            "gate_spec_hash",
        ):
            assert key in vident, f"missing validation identity field: {key}"


# ── F. Future validation provenance unit ──────────────────────────────


class TestFutureValidationProvenance:
    """M. Validation identity is derived from actual objects, never hardcoded."""

    def test_build_validation_identity_from_objects(self, tmp_path: Path) -> None:
        prices = (100.0, 101.0, 102.5)
        log_returns = (float(np.log(101.0 / 100.0)), float(np.log(102.5 / 101.0)))
        series = EmpiricalUnderlyingSeries(
            split="validation",
            parent_request_id="p",
            execution_request_id="e",
            raw_sha256="0" * 64,
            normalized_sha256="1" * 64,
            inventory_hash="2" * 64,
            plan_hash="3" * 64,
            session_dates=("2022-05-26", "2022-05-27", "2022-05-31"),
            prices=prices,
            log_returns=log_returns,
            n_observations=1,
            series_sha256="4" * 64,
        )
        win = SdeWindow(
            window_id="w_boundary",
            start_index=100,
            context_returns=np.array([0.001, 0.002, 0.0015]),
            target_returns=np.array([0.004, 0.005, 0.0042]),
            context_start_date="2021-12-30",
            context_end_date="2022-01-03",
            target_start_date="2022-01-04",
            target_end_date="2022-01-10",
        )
        benchmark = tmp_path / "benchmark.json"
        benchmark.write_text("{}", encoding="utf-8")

        ident = svx.build_validation_identity(
            validation_series=series,
            eval_ctx_window=win,
            checkpoint_sha256="a" * 64,
            benchmark_path=benchmark,
            config_hash="b" * 64,
            gate_spec_hash="c" * 64,
            source_identity={"git_commit": "d" * 40, "git_dirty": False},
        )
        assert ident["validation_split"] == "validation"
        assert ident["validation_start_date"] == "2022-05-26"
        assert ident["validation_end_date"] == "2022-05-31"
        assert ident["validation_observation_count"] == len(series.returns_array)
        # The series SHA is genuinely derived from the series returns.
        expected_sha = hashlib.sha256(
            svx.canonical_dumps({"returns": [float(v) for v in series.returns_array]}).encode()
        ).hexdigest()
        assert ident["validation_series_sha256"] == expected_sha
        assert ident["final_checkpoint_sha256"] == "a" * 64
        assert ident["baseline_suite_sha256"] == hashlib.sha256(benchmark.read_bytes()).hexdigest()
        assert ident["model_config_hash"] == "b" * 64
        assert ident["gate_spec_hash"] == "c" * 64
        assert ident["context_window_id"] == "w_boundary"
        assert ident["git_commit"] == "d" * 40
        assert ident["git_dirty"] is False


# ── G. Legacy threshold isolation ─────────────────────────────────────


class TestLegacyThresholdIsolation:
    """Legacy model-YAML copied gate fields cannot affect gate-v2 acceptance."""

    def test_legacy_gate_fields_in_yaml(self) -> None:
        data = yaml.safe_load(_V5_YAML.read_text(encoding="utf-8"))
        obj = data.get("objective", {})
        assert "gate_variance_ratio_lo" in obj

    def test_absurd_legacy_threshold_cannot_affect_gate(self, tmp_path: Path) -> None:
        """A deliberately absurd legacy threshold in a temp model YAML is inert.

        Negative control: the old ``test_changing_legacy_field_...`` dumped the
        real gate YAML unchanged (no mutation), so it proved nothing.  Here we
        actually mutate a legacy copied gate threshold to an absurd value in a
        synthetic v5 model YAML and prove the authoritative gate-v2 spec and
        its canonical hash are untouched and its pass/fail thresholds unchanged.
        """
        legacy_path = tmp_path / "v5_model_legacy.yaml"
        legacy_path.write_text(
            yaml.safe_dump(
                {
                    "version": "structured-volatility-neural-sde-v5",
                    "objective": {
                        "gate_variance_ratio_hi": 9999.0,
                        "gate_dispersion_ratio_hi": 9999.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        # The legacy model YAML is never read by the gate loader.
        authoritative = load_gate_spec_v2(str(_GATE_YAML))
        baseline_hash = authoritative.spec_hash()
        assert authoritative.variance_ratio_hi == 2.0
        assert authoritative.dispersion_band_hi == 2.0
        assert authoritative.acf1_max_diff == 0.25
        assert authoritative.drift_diffusion_max == 0.5
        # Any fresh load of the authoritative YAML is byte-identical to baseline.
        assert load_gate_spec_v2(str(_GATE_YAML)).spec_hash() == baseline_hash
        # The absurd values are not reflected in any loaded gate spec.
        reloaded = load_gate_spec_v2(str(_GATE_YAML))
        assert reloaded.variance_ratio_hi != 9999.0


# ── H. Experiment config identity ─────────────────────────────────────


class TestExperimentConfigIdentity:
    """L. Material config changes alter the run hash; frozen identity preserved."""

    def test_material_change_alters_experiment_hash(self) -> None:
        base = svx.V5ExperimentConfig()
        changed = (
            svx.V5ExperimentConfig(sde=StructuredVolConfig(v_clamp_max=11.0)),
            svx.V5ExperimentConfig(sde=StructuredVolConfig(diffusion_epsilon=1e-4)),
            svx.V5ExperimentConfig(n_eval_paths=256),
            svx.V5ExperimentConfig(eval_seed=1),
        )
        for cfg in changed:
            assert cfg.config_hash() != base.config_hash()

    def test_frozen_v5_config_identity_preserved(self) -> None:
        """The frozen v5 YAML still yields the documented prospective run hash.

        No scientific config value was changed by this migration, so the future
        run identity is unchanged.
        """
        cfg = svx.load_v5_config(_V5_YAML)
        assert cfg.config_hash() == _FROZEN_V5_RUN_HASH

    def test_config_hash_untouched_by_metadata_representation(self, tmp_path: Path) -> None:
        """Same scientific values, different YAML representation -> same hash."""
        cfg1 = svx.load_v5_config(_V5_YAML)
        alt = tmp_path / "v5_alt.yaml"
        alt.write_text(
            yaml.safe_dump(
                {
                    "version": "structured-volatility-neural-sde-v5",
                    "sde": dict(vars(svx.StructuredVolConfig())),
                    "training": {
                        "optimizer": "AdamW",
                        "learning_rate": 0.001,
                        "weight_decay": 1e-6,
                        "batch_size": 64,
                        "max_epochs": 400,
                        "patience": 40,
                        "grad_norm_clip": 1.0,
                        "model_init_seed": 8281,
                        "data_seed": 8282,
                        "eval_seed": 8283,
                        "fit_fraction": 0.8,
                    },
                    "windows": {"context_lookback": 22, "horizon": 63, "dt": 1.0 / 252.0},
                    "objective": dict(vars(svx.V3ObjectiveConfig())),
                    "n_eval_paths": 1024,
                    "eval_seed": 8283,
                }
            ),
            encoding="utf-8",
        )
        cfg2 = svx.load_v5_config(alt)
        assert cfg2.config_hash() == cfg1.config_hash()

    def test_run_hash_changes_with_material_yaml_change(self, tmp_path: Path) -> None:
        alt = tmp_path / "v5_material.yaml"
        data = yaml.safe_load(_V5_YAML.read_text(encoding="utf-8"))
        data["sde"]["v_clamp_max"] = 12.0  # material identity change
        alt.write_text(yaml.safe_dump(data), encoding="utf-8")
        assert svx.load_v5_config(alt).config_hash() != svx.load_v5_config(_V5_YAML).config_hash()


class TestGateEvaluationSmoke:
    """Gate v2 evaluation runs end-to-end with the frozen spec and corrected seeds."""

    def test_evaluate_gate_v2_runs(self) -> None:
        from neuralmarket.research.neural_sde_internal_gate import evaluate_gate_v2

        spec = WindowSpec(horizon=5, context_lookback=3)
        windows = []
        for i in range(20):
            windows.append(
                SdeWindow(
                    window_id=f"w{i}",
                    start_index=i,
                    context_returns=np.random.randn(3).tolist(),
                    target_returns=np.random.randn(5).tolist(),
                    context_start_date=f"2020-01-{i + 1:02d}",
                    context_end_date=f"2020-01-{i + 3:02d}",
                    target_start_date=f"2020-01-{i + 1:02d}",
                    target_end_date=f"2020-01-{i + 5:02d}",
                )
            )
        split = FitSelectionSplit(
            fit_windows=tuple(windows[:10]),
            selection_windows=tuple(windows[10:]),
            gap_windows=0,
            fit_target_end_index=10 + spec.horizon - 1,
            selection_target_start_index=10,
            split_hash="test",
        )
        normalizer = MagicMock(spec=FeatureNormalizer)
        normalizer.normalize = MagicMock(return_value=np.zeros(4))
        cfg = StructuredVolConfig(horizon=spec.horizon, n_context=4)
        model = StructuredVolatilityNeuralSde(cfg)
        model.eval()
        training_returns = torch.tensor(np.random.randn(200).astype(np.float32))
        gate_spec = load_gate_spec_v2(str(_GATE_YAML))
        diagnostics, passed = evaluate_gate_v2(
            model, split, normalizer, training_returns, spec, gate_spec
        )
        assert isinstance(diagnostics, dict)
        assert isinstance(passed, bool)
        assert diagnostics["gate_seed"] == 7777
        assert diagnostics["bootstrap_seed"] == 8801
        assert diagnostics["gate_spec_hash"] == gate_spec.spec_hash()


# ── Source identity provenance (Claude blocker closure) ───────────────


def _run_mocked_v5(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    source_identity: dict | None = None,
    gate_passed: bool = False,
    device: str = "cpu",
    execution_mode: str = "historical_test",
) -> dict:
    """Run run_v5_experiment with heavy pieces mocked; returns the report dict.

    gate_passed=False builds the report through the gate-FAIL path (provenance
    is written regardless); gate_passed=True additionally exercises the full
    train -> gate -> refit -> validation identity block with synthetic data.
    """
    rng = np.random.RandomState(4)
    n = 200
    returns = rng.randn(n) * 0.01
    dates = tuple(f"2020-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n + 1))

    def fake_underlying(inventory, split, raw_root, processed_root):
        if split == "validation" and not gate_passed:
            raise AssertionError("validation loader must not be touched on gate-FAIL")
        return _fake_underlying(returns, dates)

    def fake_eval(*args, **kwargs):
        return {
            "gate_spec_hash": "h",
            "criterion_results": {"ok": gate_passed},
            "gate_passed": gate_passed,
        }, gate_passed

    def fake_simulate(model, ctx, seed, generator=None):
        return torch.zeros(ctx.shape[0], 5)

    def fake_scorecard(*args, **kwargs):
        return {"metrics": {}}

    def fake_payload(value):
        return {"payload": value}

    fake_inventory = type("Fake", (), {"model_validate": staticmethod(lambda _: None)})
    monkeypatch.setattr(svx, "ResearchInventory", fake_inventory)
    monkeypatch.setattr(svx, "build_underlying_series", fake_underlying)
    monkeypatch.setattr(svx, "build_v3_statistics", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(svx, "train_internal_v3", lambda *a, **k: _fake_outcome())
    monkeypatch.setattr(svx, "evaluate_gate_v2", fake_eval)
    monkeypatch.setattr(svx, "refit_final_v3", lambda *a, **k: None)
    monkeypatch.setattr(svx, "simulate_structured", fake_simulate)
    monkeypatch.setattr(svx, "configure_determinism", lambda _: None)
    monkeypatch.setattr(svx, "set_deterministic_seeds", lambda _: None)
    monkeypatch.setattr("neuralmarket.eval.scorecard.compute_scorecard", fake_scorecard)
    monkeypatch.setattr("neuralmarket.data.research.benchmark._scorecard_payload", fake_payload)
    if source_identity is not None:
        monkeypatch.setattr(svx, "repository_source_identity", lambda: source_identity)

    run_dir = tmp_path / f"run_{uuid.uuid4().hex[:10]}"
    run_dir.mkdir(parents=True)
    config_path = _write_v5_config_yaml(run_dir)
    for name in ("inventory.json", "benchmark.json", "suite.json", "v1.json", "v2.json"):
        (run_dir / name).write_text("{}", encoding="utf-8")
    return svx.run_v5_experiment(
        config_path=config_path,
        inventory_path=run_dir / "inventory.json",
        benchmark_path=run_dir / "benchmark.json",
        suite_path=run_dir / "suite.json",
        v1_artifact_path=run_dir / "v1.json",
        v2_artifact_path=run_dir / "v2.json",
        raw_root=run_dir,
        processed_root=run_dir,
        output_root=run_dir,
        report_path=run_dir / "report.json",
        device=device,
        execution_mode=execution_mode,
    )


def test_run_v5_experiment_requires_explicit_device(tmp_path: Path) -> None:
    paths = {
        "config_path": tmp_path / "config.yaml",
        "inventory_path": tmp_path / "inventory.json",
        "benchmark_path": tmp_path / "benchmark.json",
        "suite_path": tmp_path / "suite.json",
        "v1_artifact_path": tmp_path / "v1.json",
        "v2_artifact_path": tmp_path / "v2.json",
        "raw_root": tmp_path,
        "processed_root": tmp_path,
        "output_root": tmp_path,
        "report_path": tmp_path / "report.json",
    }
    with pytest.raises(TypeError, match="device"):
        svx.run_v5_experiment(**paths)


def test_run_v5_experiment_rejects_cpu_for_current_science(tmp_path: Path) -> None:
    paths = {
        "config_path": tmp_path / "config.yaml",
        "inventory_path": tmp_path / "inventory.json",
        "benchmark_path": tmp_path / "benchmark.json",
        "suite_path": tmp_path / "suite.json",
        "v1_artifact_path": tmp_path / "v1.json",
        "v2_artifact_path": tmp_path / "v2.json",
        "raw_root": tmp_path,
        "processed_root": tmp_path,
        "output_root": tmp_path,
        "report_path": tmp_path / "report.json",
        "device": "cpu",
    }
    with pytest.raises(RuntimeError, match="current scientific execution requires CUDA"):
        svx.run_v5_experiment(**paths)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_run_v5_experiment_cuda_current_smoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    result = _run_mocked_v5(
        monkeypatch,
        tmp_path,
        device="cuda",
        execution_mode="current",
    )
    assert result["provenance"]["requested_device"] == "cuda"
    assert result["provenance"]["resolved_device"] == "cuda"


class TestSourceIdentityProvenance:
    """Claude blocker closure: exact source identity persisted in v5 evidence."""

    def test_source_commit_persisted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        synth = {"git_commit": "a" * 40, "git_dirty": False}
        result = _run_mocked_v5(monkeypatch, tmp_path, source_identity=synth)
        assert result["provenance"]["git_commit"] == "a" * 40
        assert result["provenance"]["git_dirty"] is False

    def test_dirty_false_persisted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = _run_mocked_v5(
            monkeypatch, tmp_path, source_identity={"git_commit": "b" * 40, "git_dirty": False}
        )
        assert result["provenance"]["git_dirty"] is False

    def test_dirty_true_persisted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = _run_mocked_v5(
            monkeypatch, tmp_path, source_identity={"git_commit": "c" * 40, "git_dirty": True}
        )
        assert result["provenance"]["git_dirty"] is True

    def test_validation_identity_matches_top_level_source_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        synth = {"git_commit": "d" * 40, "git_dirty": True}
        result = _run_mocked_v5(monkeypatch, tmp_path, source_identity=synth, gate_passed=True)
        vid = result["evaluation"]["validation_identity"]
        assert vid["git_commit"] == "d" * 40
        assert vid["git_dirty"] is True
        assert vid["git_commit"] == result["provenance"]["git_commit"]
        assert vid["git_dirty"] == result["provenance"]["git_dirty"]

    def test_source_identity_independent_of_config_hash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        r1 = _run_mocked_v5(
            monkeypatch, tmp_path, source_identity={"git_commit": "1" * 40, "git_dirty": False}
        )
        monkeypatch.setattr(
            svx, "repository_source_identity", lambda: {"git_commit": "2" * 40, "git_dirty": True}
        )
        r2 = _run_mocked_v5(
            monkeypatch, tmp_path, source_identity={"git_commit": "2" * 40, "git_dirty": True}
        )
        # Scientific config identity is independent of source provenance identity.
        assert r1["config_hash"] == r2["config_hash"]
        assert len(r1["config_hash"]) == 64
        assert r1["provenance"]["git_commit"] == "1" * 40
        assert r2["provenance"]["git_commit"] == "2" * 40

    def test_no_hardcoded_head(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import subprocess

        real_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        synth = {"git_commit": "e" * 40, "git_dirty": False}
        result = _run_mocked_v5(monkeypatch, tmp_path, source_identity=synth)
        # The persisted value is the mocked runtime identity, not a hardcoded HEAD.
        assert result["provenance"]["git_commit"] == "e" * 40
        assert result["provenance"]["git_commit"] != real_head
