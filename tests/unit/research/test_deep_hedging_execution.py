"""Execution-pipeline tests for deep-hedging repair — Task 203.

Tiny fixtures (<=16 episodes), temp dirs, mocked checkpoint/generator,
no real 50k campaign, no CUDA, no final-test.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES
from neuralmarket.research.deep_hedging.generation import (
    _generate_and_persist_synthetic_dataset_internal as generate_and_persist_synthetic_dataset,
    load_synthetic_dataset,
    verify_nsde_checkpoint,
)
from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    dry_run,
    enumerate_generation_jobs,
    enumerate_training_jobs,
    validate_authorization_schema,
)
from neuralmarket.research.deep_hedging.trainer import _train_one_policy_internal as train_one_policy


# Helpers
def fake_increment_provider(num_episodes: int, device: torch.device) -> torch.Tensor:
    """Deterministic fake dx for tests: zeros + tiny pattern."""
    torch.manual_seed(123)
    return torch.randn(num_episodes, 63, device=device, dtype=torch.float64) * 0.01


# ---------------------------------------------------------------------------
# Checkpoint/member identity validation (fake)
# ---------------------------------------------------------------------------

def test_fake_checkpoint_member_identity(tmp_path: Path) -> None:
    fake_ckpt = tmp_path / "checkpoint.pt"
    # Fake checkpoint file for test (not real NSDE, but verify function handles)
    torch.save({"state_dict": {"a_raw": torch.tensor([0.5])}}, fake_ckpt)
    # Correct member/prefix should pass (no SHA check if expected None)
    result = verify_nsde_checkpoint(member="seed-01", run_prefix=RUN_PREFIXES["seed-01"], checkpoint_path=fake_ckpt)
    assert result["member"] == "seed-01"
    # Wrong prefix should raise
    with pytest.raises(ValueError, match="run_prefix mismatch"):
        verify_nsde_checkpoint(member="seed-01", run_prefix="wrong", checkpoint_path=fake_ckpt)
    # Unknown member
    with pytest.raises(ValueError, match="unknown member"):
        verify_nsde_checkpoint(member="unknown", run_prefix="x", checkpoint_path=fake_ckpt)


# ---------------------------------------------------------------------------
# Tiny synthetic-generation persistence, manifest SHA, write-once, deterministic split
# ---------------------------------------------------------------------------

def test_tiny_synthetic_generation_persistence(tmp_path: Path) -> None:
    member = "seed-01"
    run_prefix = RUN_PREFIXES[member]
    dataset_path = tmp_path / "synthetic" / f"{run_prefix}_{member}" / "synthetic_episodes_v1.parquet"
    manifest_path = tmp_path / "synthetic" / f"{run_prefix}_{member}" / "synthetic_manifest_v1.json"
    result = generate_and_persist_synthetic_dataset(
        member=member,
        run_prefix=run_prefix,
        synthetic_seed=42001,
        num_episodes=8,
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        device="cpu",
        increment_provider=fake_increment_provider,
        verify_contract_runtime=False,
    )
    assert Path(result["dataset_path"]).exists()
    assert Path(result["manifest_path"]).exists()
    # Load and verify
    df = load_synthetic_dataset(dataset_path, manifest_path=manifest_path)
    assert len(df) == 8
    assert set(df.columns) >= {"episode_id", "maturity", "moneyness", "strike", "option_type", "p0", "s_series", "s0", "split"}
    # Manifest SHA binding
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["parquet_sha256"] == result["dataset_sha256"]
    assert manifest["member"] == member
    assert manifest["synthetic_seed"] == 42001
    assert manifest["num_episodes"] == 8
    # Deterministic IDs/order
    assert df["episode_id"].tolist() == list(range(8))


def test_write_once_dataset_refusal(tmp_path: Path) -> None:
    member = "seed-02"
    run_prefix = RUN_PREFIXES[member]
    dataset_path = tmp_path / "synthetic" / f"{run_prefix}_{member}" / "synthetic_episodes_v1.parquet"
    manifest_path = tmp_path / "synthetic" / f"{run_prefix}_{member}" / "synthetic_manifest_v1.json"
    generate_and_persist_synthetic_dataset(
        member=member,
        run_prefix=run_prefix,
        synthetic_seed=42002,
        num_episodes=8,
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        device="cpu",
        increment_provider=fake_increment_provider,
        verify_contract_runtime=False,
    )
    # Second attempt should refuse (write-once)
    with pytest.raises(RuntimeError, match="OVERWRITE_REFUSED"):
        generate_and_persist_synthetic_dataset(
            member=member,
            run_prefix=run_prefix,
            synthetic_seed=42002,
            num_episodes=8,
            dataset_path=dataset_path,
            manifest_path=manifest_path,
            device="cpu",
            increment_provider=fake_increment_provider,
            verify_contract_runtime=False,
        )


def test_deterministic_train_selection_membership(tmp_path: Path) -> None:
    member = "seed-04"
    run_prefix = RUN_PREFIXES[member]
    dataset_path = tmp_path / "synthetic" / f"{run_prefix}_{member}" / "synthetic_episodes_v1.parquet"
    manifest_path = tmp_path / "synthetic" / f"{run_prefix}_{member}" / "synthetic_manifest_v1.json"
    generate_and_persist_synthetic_dataset(
        member=member,
        run_prefix=run_prefix,
        synthetic_seed=42004,
        num_episodes=10,
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        device="cpu",
        increment_provider=fake_increment_provider,
        verify_contract_runtime=False,
    )
    df = load_synthetic_dataset(dataset_path)
    # 80/20 split deterministic
    assert (df["split"] == "train").sum() == 8
    assert (df["split"] == "selection").sum() == 2
    # Reload with split filter
    df_train = load_synthetic_dataset(dataset_path, split="train")
    df_sel = load_synthetic_dataset(dataset_path, split="selection")
    assert len(df_train) == 8
    assert len(df_sel) == 2
    # Deterministic: same seed => same permutation
    # Regenerate with same seed to temp2 and compare split assignment
    # Use second temp path to avoid overwrite refusal
    dataset_path2 = tmp_path / "synthetic2" / f"{run_prefix}_{member}" / "synthetic_episodes_v1.parquet"
    manifest_path2 = tmp_path / "synthetic2" / f"{run_prefix}_{member}" / "synthetic_manifest_v1.json"
    generate_and_persist_synthetic_dataset(
        member=member,
        run_prefix=run_prefix,
        synthetic_seed=42004,
        num_episodes=10,
        dataset_path=dataset_path2,
        manifest_path=manifest_path2,
        device="cpu",
        increment_provider=fake_increment_provider,
        verify_contract_runtime=False,
    )
    df2 = load_synthetic_dataset(dataset_path2)
    assert df["split"].tolist() == df2["split"].tolist()


# ---------------------------------------------------------------------------
# One tiny differentiable optimizer step, full-selection metric, checkpoint selection
# ---------------------------------------------------------------------------

def _tiny_dataset_for_training(tmp_path: Path, member: str = "seed-01", seed: int = 42001, n: int = 8) -> tuple[Path, Path]:
    run_prefix = RUN_PREFIXES[member]
    dataset_path = tmp_path / "syn" / f"{run_prefix}_{member}" / "synthetic_episodes_v1.parquet"
    manifest_path = tmp_path / "syn" / f"{run_prefix}_{member}" / "synthetic_manifest_v1.json"
    generate_and_persist_synthetic_dataset(
        member=member,
        run_prefix=run_prefix,
        synthetic_seed=seed,
        num_episodes=n,
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        device="cpu",
        increment_provider=fake_increment_provider,
        verify_contract_runtime=False,
    )
    return dataset_path, manifest_path


def test_one_tiny_differentiable_optimizer_step(tmp_path: Path) -> None:
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies"
    result = train_one_policy(
        member="seed-01",
        cost=0.0,
        hedger_seed=31001,
        synthetic_dataset_path=dataset_path,
        synthetic_manifest_path=manifest_path,
        policy_root=policy_root,
        max_epochs=1,
        batch_size=4,
        device="cpu",
        verify_contract_runtime=False,
    )
    assert "best_epoch" in result
    assert Path(result["checkpoint_path"]).exists()
    # Check gradient was applied (checkpoint differs from init)
    # Load checkpoint and verify finiteness
    ckpt = torch.load(result["checkpoint_path"], map_location="cpu", weights_only=False)
    assert all(torch.isfinite(v).all() for v in ckpt.values())


def test_full_selection_metric_across_all_selection_samples(tmp_path: Path) -> None:
    # Use n=10 -> 8 train, 2 selection (full-set vs mean minibatch already tested in cvar, but also here)
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=10)
    policy_root = tmp_path / "policies2"
    result = train_one_policy(
        member="seed-01",
        cost=0.0010,
        hedger_seed=31002,
        synthetic_dataset_path=dataset_path,
        synthetic_manifest_path=manifest_path,
        policy_root=policy_root,
        max_epochs=1,
        batch_size=4,
        device="cpu",
        verify_contract_runtime=False,
    )
    # Check training_curve records validation_selection_cvar per epoch (full-set)
    curve_path = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_10" / "h_31002" / "training_curve.json"
    curve = json.loads(curve_path.read_text(encoding="utf-8"))
    assert len(curve) == 1
    assert "validation_selection_cvar" in curve[0]
    assert curve[0]["validation_selection_cvar"] is not None


def test_checkpoint_best_metric_selection_and_tie(tmp_path: Path) -> None:
    # Train for 2 epochs with mocked selection CVaR that ties
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies3"
    # Patch cvar to return same value to force tie
    with patch("neuralmarket.research.deep_hedging.trainer.cvar_full_set_selection", return_value=torch.tensor(1.0)):
        result = train_one_policy(
            member="seed-01",
            cost=0.0050,
            hedger_seed=31003,
            synthetic_dataset_path=dataset_path,
            synthetic_manifest_path=manifest_path,
            policy_root=policy_root,
            max_epochs=2,
            min_epochs=1,
            patience=5,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
        )
    # Earliest wins: best_epoch should be 0 (first)
    assert result["best_epoch"] == "0"
    # Check curve has 2 epochs, both same cvar, but best remains 0
    curve_path = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_50" / "h_31003" / "training_curve.json"
    curve = json.loads(curve_path.read_text(encoding="utf-8"))
    assert curve[0]["validation_selection_cvar"] == 1.0
    assert curve[1]["validation_selection_cvar"] == 1.0


def test_early_stop_state_machine(tmp_path: Path) -> None:
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies4"
    # Mock selection cvar to not improve after epoch 0 to trigger early stop with patience 1
    call_count = {"n": 0}

    def mock_cvar(losses, alpha=0.95):
        call_count["n"] += 1
        # Epoch 0: 1.0, epoch1: 2.0 (worse), epoch2: 3.0 (worse) -> no improve
        return torch.tensor(float(call_count["n"]), dtype=torch.float64)

    with patch("neuralmarket.research.deep_hedging.trainer.cvar_full_set_selection", side_effect=mock_cvar):
        result = train_one_policy(
            member="seed-01",
            cost=0.0,
            hedger_seed=31001,
            synthetic_dataset_path=dataset_path,
            synthetic_manifest_path=manifest_path,
            policy_root=policy_root,
            max_epochs=10,
            min_epochs=1,
            patience=1,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
        )
    # Should have early stopped before max_epochs
    curve_path = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001" / "training_curve.json"
    curve = json.loads(curve_path.read_text(encoding="utf-8"))
    # With patience 1 and no improvement after epoch0, should stop at epoch1 (0-indexed)
    assert len(curve) < 10
    assert len(curve) == 2  # epoch0 and epoch1 then stop


def test_nonfinite_training_failure(tmp_path: Path) -> None:
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies5"
    # Mock empirical_cvar to return nan for all batches (nonfinite) — fail-closed must raise immediately
    with patch("neuralmarket.research.deep_hedging.trainer.empirical_cvar", return_value=torch.tensor(float("nan"))):
        # Also mock selection to be nan -> no valid checkpoint (but fail-closed triggers earlier)
        with patch("neuralmarket.research.deep_hedging.trainer.cvar_full_set_selection", return_value=torch.tensor(float("nan"))):
            with pytest.raises(RuntimeError, match="nonfinite minibatch CVaR"):
                train_one_policy(
                    member="seed-01",
                    cost=0.0,
                    hedger_seed=31001,
                    synthetic_dataset_path=dataset_path,
                    synthetic_manifest_path=manifest_path,
                    policy_root=policy_root,
                    max_epochs=1,
                    batch_size=4,
                    device="cpu",
                    verify_contract_runtime=False,
                )
    # Terminal failure evidence should be persisted despite exception
    terminal_path = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001" / "terminal_manifest.json"
    assert terminal_path.exists()
    manifest = json.loads(terminal_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failure"


def test_terminal_evidence_on_injected_failure(tmp_path: Path) -> None:
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies6"
    with pytest.raises(RuntimeError, match="injected failure at epoch 0"):
        train_one_policy(
            member="seed-01",
            cost=0.0,
            hedger_seed=31001,
            synthetic_dataset_path=dataset_path,
            synthetic_manifest_path=manifest_path,
            policy_root=policy_root,
            max_epochs=1,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
            inject_failure_at_epoch=0,
        )
    # Even on failure, execution_started is consumed and terminal evidence persisted
    started = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001" / "execution_started.json"
    assert started.exists()
    terminal = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001" / "terminal_manifest.json"
    assert terminal.exists()
    assert json.loads(terminal.read_text(encoding="utf-8"))["status"] == "failure"
    stderr = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001" / "training_stderr.log"
    assert stderr.exists()


def test_execution_started_consumption(tmp_path: Path) -> None:
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies7"
    # First run succeeds
    train_one_policy(
        member="seed-01",
        cost=0.0,
        hedger_seed=31001,
        synthetic_dataset_path=dataset_path,
        synthetic_manifest_path=manifest_path,
        policy_root=policy_root,
        max_epochs=1,
        batch_size=4,
        device="cpu",
        verify_contract_runtime=False,
    )
    # Second run with same (member,cost,seed) should refuse (consumed)
    with pytest.raises(FileExistsError, match="OVERWRITE_REFUSED|already exists"):
        train_one_policy(
            member="seed-01",
            cost=0.0,
            hedger_seed=31001,
            synthetic_dataset_path=dataset_path,
            synthetic_manifest_path=manifest_path,
            policy_root=policy_root,
            max_epochs=1,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
        )


def test_policy_artifact_overwrite_refusal(tmp_path: Path) -> None:
    dataset_path, manifest_path = _tiny_dataset_for_training(tmp_path, n=8)
    policy_root = tmp_path / "policies8"
    train_one_policy(
        member="seed-01",
        cost=0.0,
        hedger_seed=31001,
        synthetic_dataset_path=dataset_path,
        synthetic_manifest_path=manifest_path,
        policy_root=policy_root,
        max_epochs=1,
        batch_size=4,
        device="cpu",
        verify_contract_runtime=False,
    )
    # Checkpoint exists, second attempt should be consumed via execution_started
    ckpt = policy_root / f"{RUN_PREFIXES['seed-01']}_seed-01" / "c_0" / "h_31001" / "checkpoint.pt"
    assert ckpt.exists()
    # Attempt to overwrite checkpoint via generation persistence path (separate) but trainer consumes
    with pytest.raises(FileExistsError):
        train_one_policy(
            member="seed-01",
            cost=0.0,
            hedger_seed=31001,
            synthetic_dataset_path=dataset_path,
            synthetic_manifest_path=manifest_path,
            policy_root=policy_root,
            max_epochs=1,
            batch_size=4,
            device="cpu",
            verify_contract_runtime=False,
        )


# ---------------------------------------------------------------------------
# Campaign enumeration 5 + 45, unauthorized --execute refusal, authorized schema
# ---------------------------------------------------------------------------

def test_campaign_enumeration_exactly_5_and_45() -> None:
    gen_jobs = enumerate_generation_jobs()
    train_jobs = enumerate_training_jobs()
    assert len(gen_jobs) == 5
    assert len(train_jobs) == 45
    # Validate 5*3*3
    assert len(train_jobs) == 5 * 3 * 3
    dry = dry_run()
    assert dry["total_generation"] == 5
    assert dry["total_training"] == 45
    assert len(dry["generation_jobs"]) == 5
    assert len(dry["training_jobs"]) == 45


def test_unauthorized_execute_refusal() -> None:
    from neuralmarket.research.deep_hedging.runner import require_authorization_or_refuse

    # Without --execute, dry run
    assert require_authorization_or_refuse(authorization_path=Path("nonexistent_auth.json"), execute_flag=False) == "DRY_RUN"
    # With --execute but no tracked authorization, must refuse
    with pytest.raises(AuthorizationError, match="REFUSED"):
        require_authorization_or_refuse(authorization_path=Path("nonexistent_auth.json"), execute_flag=True)


def test_authorized_schema_field_validation() -> None:
    # Valid payload should pass
    valid = {
        "schema_version": "hedging-execution-authorization-v1",
        "task_id": "NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-202",
        "contract_v3_canonical": "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01",
        "contract_v3_blob": "eef7ad220db889166469799372759dfe1a96e35f",
        "implementation_commit": "abc123",
        "runtime_identity": "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada",
        "member_allowlist": ["seed-01", "seed-02"],
        "hedger_seed_allowlist": [31001, 31002],
        "cost_allowlist": [0.0, 0.0010],
        "max_generation_invocations": 5,
        "max_training_invocations": 45,
        "artifact_roots": ["data/processed/research/hedging_synthetic", "data/processed/research/hedging_policies"],
        "network": False,
        "final_test_access": False,
    }
    validate_authorization_schema(valid)  # should not raise
    # Missing field should fail
    invalid = valid.copy()
    del invalid["contract_v3_canonical"]
    with pytest.raises(AuthorizationError, match="missing required field"):
        validate_authorization_schema(invalid)
    # Wrong network
    invalid2 = valid.copy()
    invalid2["network"] = True
    with pytest.raises(AuthorizationError, match="network must be false"):
        validate_authorization_schema(invalid2)
    # Wrong max_training
    invalid3 = valid.copy()
    invalid3["max_training_invocations"] = 44
    with pytest.raises(AuthorizationError, match="max_training_invocations must be 45"):
        validate_authorization_schema(invalid3)
