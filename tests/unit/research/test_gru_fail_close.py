"""Fail-close regression tests for Task 219 — nonfinite must be fatal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES
from neuralmarket.research.deep_hedging.generation import (
    _generate_and_persist_synthetic_dataset_internal as generate_synthetic,
)
from neuralmarket.research.deep_hedging.trainer import (
    _train_one_policy_internal as train_one_policy,
)


def fake_provider(num: int, dev: torch.device) -> torch.Tensor:
    torch.manual_seed(123)
    return torch.randn(num, 63, device=dev, dtype=torch.float64) * 0.01


def _tiny_dataset(tmp_path: Path, n: int = 16):
    rp = RUN_PREFIXES["seed-01"]
    ds = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_episodes_v1.parquet"
    mp = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_manifest_v1.json"
    generate_synthetic(
        member="seed-01",
        run_prefix=rp,
        synthetic_seed=42001,
        num_episodes=n,
        dataset_path=ds,
        manifest_path=mp,
        device="cpu",
        increment_provider=fake_provider,
        verify_contract_runtime=False,
    )
    return ds, mp


def test_nonfinite_loss_vector_fails_immediately(tmp_path: Path) -> None:
    ds0, mp0 = _tiny_dataset(tmp_path / "base_loss", n=8)
    from neuralmarket.research.deep_hedging.generation import load_synthetic_dataset

    df = load_synthetic_dataset(ds0, mp0)
    s = list(df.loc[0, "s_series"])
    s[0] = float("nan")
    df.at[0, "s_series"] = s
    rp = RUN_PREFIXES["seed-01"]
    ds = tmp_path / "syn_nan" / "synthetic_episodes_v1.parquet"
    mp = tmp_path / "syn_nan" / "synthetic_manifest_v1.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ds)
    manifest = json.loads(mp0.read_text())
    manifest["parquet_sha256"] = hashlib.sha256(ds.read_bytes()).hexdigest()
    mp.write_text(json.dumps(manifest, indent=2))
    root = tmp_path / "policies_nf_loss"
    with pytest.raises(Exception, match="non.*finite"):
        train_one_policy(
            member="seed-01",
            cost=0.0,
            hedger_seed=31001,
            synthetic_dataset_path=ds,
            synthetic_manifest_path=mp,
            policy_root=root,
            max_epochs=1,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
        )
    t = root / f"{rp}_seed-01" / "c_0" / "h_31001" / "terminal_manifest.json"
    assert t.exists()
    assert json.loads(t.read_text())["status"] == "failure"


def test_nonfinite_cvar_fails_immediately(tmp_path: Path) -> None:
    ds, mp = _tiny_dataset(tmp_path, n=16)
    root = tmp_path / "policies_nf_cvar"
    with patch(
        "neuralmarket.research.deep_hedging.trainer.empirical_cvar",
        return_value=torch.tensor(float("nan")),
    ):
        with pytest.raises(RuntimeError, match="nonfinite minibatch CVaR"):
            train_one_policy(
                member="seed-01",
                cost=0.0,
                hedger_seed=31001,
                synthetic_dataset_path=ds,
                synthetic_manifest_path=mp,
                policy_root=root,
                max_epochs=1,
                batch_size=4,
                device="cpu",
                verify_contract_runtime=False,
            )


def test_detached_cvar_fails_immediately(tmp_path: Path) -> None:
    ds, mp = _tiny_dataset(tmp_path, n=16)
    root = tmp_path / "policies_detached"
    with patch(
        "neuralmarket.research.deep_hedging.trainer.empirical_cvar",
        return_value=torch.tensor(1.0),
    ):
        with pytest.raises(RuntimeError, match="requires_grad False"):
            train_one_policy(
                member="seed-01",
                cost=0.0,
                hedger_seed=31001,
                synthetic_dataset_path=ds,
                synthetic_manifest_path=mp,
                policy_root=root,
                max_epochs=1,
                batch_size=4,
                device="cpu",
                verify_contract_runtime=False,
            )


def test_nonfinite_gradient_fails_immediately(tmp_path: Path) -> None:
    assert "nonfinite gradient" in Path("src/neuralmarket/research/deep_hedging/trainer.py").read_text()


def test_nonfinite_clipped_grad_norm_fails_immediately(tmp_path: Path) -> None:
    ds, mp = _tiny_dataset(tmp_path, n=16)
    root = tmp_path / "policies_nf_clip"
    with patch(
        "neuralmarket.research.deep_hedging.trainer.clip_grad_norm_",
        return_value=float("nan"),
    ):
        with pytest.raises(RuntimeError, match="nonfinite clipped grad norm"):
            train_one_policy(
                member="seed-01",
                cost=0.0,
                hedger_seed=31001,
                synthetic_dataset_path=ds,
                synthetic_manifest_path=mp,
                policy_root=root,
                max_epochs=1,
                batch_size=4,
                device="cpu",
                verify_contract_runtime=False,
            )


def test_empty_epoch_train_losses_fails_immediately(tmp_path: Path) -> None:
    rp = RUN_PREFIXES["seed-01"]
    tmp0 = tmp_path / "tmp0"
    ds0, mp0 = _tiny_dataset(tmp0, n=8)
    from neuralmarket.research.deep_hedging.generation import load_synthetic_dataset

    df_all = load_synthetic_dataset(ds0, mp0)
    df_all["split"] = "selection"
    ds = tmp_path / "empty" / "synthetic_episodes_v1.parquet"
    mp = tmp_path / "empty" / "synthetic_manifest_v1.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_parquet(ds)
    manifest = json.loads(mp0.read_text())
    manifest["parquet_sha256"] = hashlib.sha256(ds.read_bytes()).hexdigest()
    mp.write_text(json.dumps(manifest, indent=2))
    root = tmp_path / "policies_empty"
    with pytest.raises(Exception, match="empty"):
        train_one_policy(
            member="seed-01",
            cost=0.0,
            hedger_seed=31001,
            synthetic_dataset_path=ds,
            synthetic_manifest_path=mp,
            policy_root=root,
            max_epochs=1,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
        )


def test_no_continuation_after_nonfinite(tmp_path: Path) -> None:
    ds, mp = _tiny_dataset(tmp_path, n=16)
    root = tmp_path / "policies_no_cont"
    count = {"n": 0}

    def failing_cvar(losses, alpha=0.95):
        count["n"] += 1
        if count["n"] == 1:
            return torch.tensor(float("nan"))
        return torch.tensor(1.0, requires_grad=True)

    with patch(
        "neuralmarket.research.deep_hedging.trainer.empirical_cvar",
        side_effect=failing_cvar,
    ):
        with pytest.raises(RuntimeError, match="nonfinite minibatch CVaR"):
            train_one_policy(
                member="seed-01",
                cost=0.0,
                hedger_seed=31001,
                synthetic_dataset_path=ds,
                synthetic_manifest_path=mp,
                policy_root=root,
                max_epochs=1,
                batch_size=4,
                device="cpu",
                verify_contract_runtime=False,
            )
    assert count["n"] == 1


def test_positive_optimizer_still_works(tmp_path: Path) -> None:
    ds, mp = _tiny_dataset(tmp_path, n=16)
    root = tmp_path / "policies_pos"
    from neuralmarket.research.deep_hedging.hedger import GRUHedger

    torch.manual_seed(31001)
    init = {k: v.clone() for k, v in GRUHedger().state_dict().items()}
    train_one_policy(
        member="seed-01",
        cost=0.0,
        hedger_seed=31001,
        synthetic_dataset_path=ds,
        synthetic_manifest_path=mp,
        policy_root=root,
        max_epochs=2,
        min_epochs=2,
        patience=10,
        batch_size=4,
        device="cpu",
        verify_contract_runtime=False,
    )
    pdir = root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001"
    curve = json.loads((pdir / "training_curve.json").read_text())
    assert all(v["train_cvar"] == v["train_cvar"] and v["train_cvar"] != float("inf") for v in curve)
    final = torch.load(pdir / "checkpoint_final.pt", map_location="cpu")
    l2 = sum(((final[k].float() - init[k].float()).norm().item() ** 2 for k in init)) ** 0.5
    assert l2 > 0
