"""Adversarial provenance fail-close tests for Task-239."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest import mock

import pytest
import torch

from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES
from neuralmarket.research.deep_hedging.generation import (
    _generate_and_persist_synthetic_dataset_internal as generate_synthetic,
)
from neuralmarket.research.deep_hedging.trainer import _train_one_policy_internal


def fake_provider(num: int, dev: torch.device) -> torch.Tensor:
    torch.manual_seed(123)
    return torch.randn(num, 63, device=dev, dtype=torch.float64) * 0.01


def _tiny_dataset(tmp_path: Path, n: int = 8):
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


def _valid_provenance(tmp_path: Path, ds: Path) -> dict:
    return {
        "recovery_protocol_path": "reports\\protocol\\structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md",
        "recovery_protocol_canonical": "4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8",
        "recovery_protocol_blob": "6fcb39c29827d0d35ce3c777298fb75a81d00cb4",
        "recovery_authorization_path": str(tmp_path / "auth.json"),
        "recovery_authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-233",
        "recovery_authorization_commit": "a" * 40,
        "recovery_authorization_canonical": "b" * 64,
        "recovery_authorization_blob": "c" * 40,
        "recovery_implementation_commit": "d" * 40,
        "recovery_implementation_manifest": "e" * 64,
        "recovery_root": "data/processed/research/hedging_policies_recovery_v1",
        "runtime_identity": "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada",
        "dataset_path": str(ds),
        "dataset_sha256": hashlib.sha256(ds.read_bytes()).hexdigest(),
        "historical_predecessor_artifact_path": "data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31001",
        "historical_execution_started_sha": "a" * 64,
        "historical_checkpoint_sha": "b" * 64,
        "historical_terminal_sha": "c" * 64,
        "historical_classification": "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP",
    }


def test_a_verified_authorization_exact_provenance(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "a", n=8)
    rp = RUN_PREFIXES["seed-01"]
    policy_root = tmp_path / "policies"
    prov = _valid_provenance(tmp_path, ds)
    _train_one_policy_internal(
        member="seed-01", cost=0.0, hedger_seed=31001,
        synthetic_dataset_path=ds, synthetic_manifest_path=mp,
        policy_root=policy_root, run_prefix=rp,
        max_epochs=2, min_epochs=1, patience=1, batch_size=4, device="cpu",
        recovery_provenance=prov,
    )
    started = json.loads((policy_root / f"{rp}_seed-01" / "c_0" / "h_31001" / "execution_started.json").read_text())
    for k, v in prov.items():
        assert started.get(k) == v


def _expect_fail(tmp_path: Path, prov: dict):
    ds, mp = _tiny_dataset(tmp_path, n=8)
    rp = RUN_PREFIXES["seed-01"]
    policy_root = tmp_path / "policies_fail"
    policy_dir = policy_root / f"{rp}_seed-01" / "c_0" / "h_31001"
    assert not policy_dir.exists()
    with pytest.raises(RuntimeError, match="fail-closed"):
        _train_one_policy_internal(
            member="seed-01", cost=0.0, hedger_seed=31001,
            synthetic_dataset_path=ds, synthetic_manifest_path=mp,
            policy_root=policy_root, run_prefix=rp,
            max_epochs=2, min_epochs=1, patience=1, batch_size=4, device="cpu",
            recovery_provenance=prov,
        )
    assert not policy_dir.exists()
    assert not (policy_dir / "execution_started.json").exists()


def test_b_canonical_missing(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "b0", n=8)
    prov = _valid_provenance(tmp_path / "b", ds)
    prov["recovery_authorization_canonical"] = ""
    _expect_fail(tmp_path / "b", prov)


def test_c_canonical_null(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "c0", n=8)
    prov = _valid_provenance(tmp_path / "c", ds)
    prov["recovery_authorization_canonical"] = None  # type: ignore
    _expect_fail(tmp_path / "c", prov)


def test_d_wrong_auth_commit(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "d0", n=8)
    prov = _valid_provenance(tmp_path / "d", ds)
    prov["recovery_authorization_commit"] = ""
    _expect_fail(tmp_path / "d", prov)


def test_e_wrong_auth_blob(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "e0", n=8)
    prov = _valid_provenance(tmp_path / "e", ds)
    prov["recovery_authorization_blob"] = ""
    _expect_fail(tmp_path / "e", prov)


def test_f_wrong_implementation_commit(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "f0", n=8)
    prov = _valid_provenance(tmp_path / "f", ds)
    prov["recovery_implementation_commit"] = ""
    _expect_fail(tmp_path / "f", prov)


def test_g_wrong_implementation_manifest(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "g0", n=8)
    prov = _valid_provenance(tmp_path / "g", ds)
    prov["recovery_implementation_manifest"] = None  # type: ignore
    _expect_fail(tmp_path / "g", prov)


def test_h_source_drift(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "h0", n=8)
    prov = _valid_provenance(tmp_path / "h", ds)
    prov["recovery_implementation_commit"] = ""
    _expect_fail(tmp_path / "h", prov)


def test_i_runtime_mismatch(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "i0", n=8)
    prov = _valid_provenance(tmp_path / "i", ds)
    prov["runtime_identity"] = ""
    _expect_fail(tmp_path / "i", prov)


def test_j_dataset_mismatch(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "j0", n=8)
    prov = _valid_provenance(tmp_path / "j", ds)
    prov["dataset_path"] = ""
    _expect_fail(tmp_path / "j", prov)


def test_k_authorization226_substitution(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "k0", n=8)
    auth = tmp_path / "auth_226.json"
    payload = {
        "schema_version": "1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-226",
        "authorization_type": "GRU_TRAINING_RECOVERY_V1",
        "contract_v3_canonical": "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01",
        "contract_v3_blob": "eef7ad220db889166469799372759dfe1a96e35f",
        "implementation_commit": "5a9e9c59c8f24bd8dcaadb1fa4ec3fbf2faa287d",
        "implementation_manifest_sha256": "86a8efea2bef1fc770c3e69dda9e66a7a67c117e3460e112a68c2db0ae7d3077",
        "implementation_source_blobs": {},
        "source_blobs": {},
        "runtime_identity": "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada",
        "member_allowlist": ["seed-01", "seed-02", "seed-04", "seed-05", "reserve-j01"], "cost_allowlist": [0.0, 0.001, 0.005], "hedger_seed_allowlist": [31001, 31002, 31003],
        "max_generation_invocations": 0, "max_training_invocations": 45,
        "artifact_roots": ["data/processed/research/hedging_policies_recovery_v1"],
        "recovery_root": "data/processed/research/hedging_policies_recovery_v1",
        "network": False, "final_test_access": False,
        "recovery_tuples": [{"member": "seed-01", "cost": 0.0, "hedger_seed": 31001}],
        "predecessor_identities": {"seed-01:0.0:31001": {"historical_artifact_path": "x", "historical_execution_started_sha": "a"*64, "historical_checkpoint_sha": "b"*64, "historical_terminal_sha": "c"*64, "historical_classification": "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP", "member": "seed-01", "cost": 0.0, "hedger_seed": 31001}},
        "recovery_protocol_path": "reports\\protocol\\structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md",
        "recovery_protocol_canonical": "4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8",
        "recovery_protocol_blob": "6fcb39c29827d0d35ce3c777298fb75a81d00cb4",
    }
    auth.write_text(json.dumps(payload), encoding="utf-8")
    info = {"canonical_sha256": "a"*64, "git_blob": "b"*40, "commit": "c"*40, "authorization_task_id": payload["authorization_task_id"], "path": str(auth)}
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=info):
        from neuralmarket.research.deep_hedging.trainer import train_one_policy_recovery
        with mock.patch("neuralmarket.research.deep_hedging.runner.validate_recovery_authorization_schema", return_value=None), \
             mock.patch("neuralmarket.research.deep_hedging.runner.verify_implementation_manifest", return_value=None), \
             mock.patch("neuralmarket.research.deep_hedging.runner.build_implementation_manifest", return_value={"implementation_manifest_sha256": payload["implementation_manifest_sha256"], "source_blobs": {}}), \
             mock.patch("neuralmarket.research.deep_hedging.runner.preflight_checks", return_value=None):
            with pytest.raises((RuntimeError, Exception), match="226|substitution|fail-closed"):
                train_one_policy_recovery(member="seed-01", cost=0.0, hedger_seed=31001, authorization_path=auth)


def test_l_authorization212_substitution(tmp_path: Path):
    auth = tmp_path / "auth_212.json"
    payload = {
        "schema_version": "1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-212",
        "authorization_type": "TRAINING_V1",
        "contract_v3_canonical": "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01",
        "contract_v3_blob": "eef7ad220db889166469799372759dfe1a96e35f",
        "implementation_commit": "5a9e9c59c8f24bd8dcaadb1fa4ec3fbf2faa287d",
        "implementation_manifest_sha256": "86a8efea2bef1fc770c3e69dda9e66a7a67c117e3460e112a68c2db0ae7d3077",
        "implementation_source_blobs": {},
        "source_blobs": {},
        "runtime_identity": "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada",
        "member_allowlist": ["seed-01"], "cost_allowlist": [0.0], "hedger_seed_allowlist": [31001],
        "max_generation_invocations": 5, "max_training_invocations": 45,
        "artifact_roots": ["data/processed/research/hedging_policies_recovery_v1"],
        "recovery_root": "data/processed/research/hedging_policies_recovery_v1",
        "network": False, "final_test_access": False,
    }
    auth.write_text(json.dumps(payload), encoding="utf-8")
    info = {"canonical_sha256": "a"*64, "git_blob": "b"*40, "commit": "c"*40, "authorization_task_id": payload["authorization_task_id"], "path": str(auth)}
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=info):
        from neuralmarket.research.deep_hedging.trainer import train_one_policy_recovery
        with mock.patch("neuralmarket.research.deep_hedging.runner.preflight_checks", return_value=None):
            with pytest.raises((RuntimeError, Exception), match="212|historical|fail-closed"):
                train_one_policy_recovery(member="seed-01", cost=0.0, hedger_seed=31001, authorization_path=auth)


def test_m_marker_fields_exact(tmp_path: Path):
    ds, mp = _tiny_dataset(tmp_path / "m", n=8)
    rp = RUN_PREFIXES["seed-01"]
    policy_root = tmp_path / "policies_m"
    prov = _valid_provenance(tmp_path, ds)
    _train_one_policy_internal(
        member="seed-01", cost=0.0, hedger_seed=31001,
        synthetic_dataset_path=ds, synthetic_manifest_path=mp,
        policy_root=policy_root, run_prefix=rp,
        max_epochs=2, min_epochs=1, patience=1, batch_size=4, device="cpu",
        recovery_provenance=prov,
    )
    started = json.loads((policy_root / f"{rp}_seed-01" / "c_0" / "h_31001" / "execution_started.json").read_text())
    required = [
        "recovery_authorization_path", "recovery_authorization_task_id", "recovery_authorization_commit",
        "recovery_authorization_canonical", "recovery_authorization_blob",
        "recovery_implementation_commit", "recovery_implementation_manifest",
        "runtime_identity", "dataset_path", "dataset_sha256",
        "historical_predecessor_artifact_path", "historical_execution_started_sha",
        "historical_checkpoint_sha", "historical_terminal_sha", "historical_classification",
    ]
    for k in required:
        assert k in started
        assert started[k] is not None
        assert isinstance(started[k], str) and started[k].strip() != ""
        assert started[k] == prov[k]
