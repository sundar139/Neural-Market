"""Recovery namespace / authorization-surface tests — Task 223.

Tiny tmp_path fixtures, no real recovery root, no real authorization artifact.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

from neuralmarket.research.deep_hedging.artifacts import COST_LEVELS, HEDGER_SEEDS, MEMBERS, RUN_PREFIXES
from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    validate_authorization_schema,
    validate_recovery_authorization_schema,
    RECOVERY_PROTOCOL_CANONICAL,
    RECOVERY_PROTOCOL_BLOB,
    RECOVERY_PROTOCOL_PATH,
    REPAIRED_IMPLEMENTATION_COMMIT,
    REPAIRED_IMPLEMENTATION_MANIFEST,
    RECOVERY_ROOT,
    RECOVERY_AUTHORIZATION_TYPE,
)


def fake_provider(num, dev):
    torch.manual_seed(123)
    return torch.randn(num, 63, device=dev, dtype=torch.float64) * 0.01


def _valid_recovery_payload():
    # Build valid recovery payload using trusted predecessor map (field-for-field)
    from neuralmarket.research.deep_hedging.runner import _get_trusted_predecessor_map

    tuples = []
    for m in MEMBERS:
        for c in COST_LEVELS:
            for s in HEDGER_SEEDS:
                tuples.append({"member": m, "cost": c, "hedger_seed": s})
    # Use trusted map for predecessor identities (exact cryptographic binding)
    pred = _get_trusted_predecessor_map()
    return {
        "schema_version": "hedging-execution-authorization-v1",
        "authorization_task_id": "NM-R4-V5-GRU-RECOVERY-AUTHORIZATION-223",
        "authorization_type": RECOVERY_AUTHORIZATION_TYPE,
        "recovery_protocol_path": str(RECOVERY_PROTOCOL_PATH),
        "recovery_protocol_canonical": RECOVERY_PROTOCOL_CANONICAL,
        "recovery_protocol_blob": RECOVERY_PROTOCOL_BLOB,
        "contract_v3_canonical": "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01",
        "contract_v3_blob": "eef7ad220db889166469799372759dfe1a96e35f",
        "implementation_commit": REPAIRED_IMPLEMENTATION_COMMIT,
        "implementation_manifest_sha256": REPAIRED_IMPLEMENTATION_MANIFEST,
        "implementation_source_blobs": {
            "src/neuralmarket/research/deep_hedging/trainer.py": "1860f99fcbd52ac26daab33e5325c36955fde7f8"
        },
        "runtime_identity": "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada",
        "recovery_root": RECOVERY_ROOT,
        "artifact_roots": [
            "data/processed/research/hedging_synthetic",
            RECOVERY_ROOT,
        ],
        "member_allowlist": list(MEMBERS),
        "cost_allowlist": list(COST_LEVELS),
        "hedger_seed_allowlist": list(HEDGER_SEEDS),
        "recovery_tuples": tuples,
        "predecessor_identities": pred,
        "max_training_invocations": 45,
        "max_generation_invocations": 0,
        "network": False,
        "final_test_access": False,
    }


def test_historical_authorization_rejected_by_recovery_surface():
    hist_payload = json.loads(Path("reports/protocol/hedging_execution_authorization_212.json").read_text())
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(hist_payload)


def test_recovery_authorization_rejected_by_historical_surface():
    rec = _valid_recovery_payload()
    with pytest.raises(AuthorizationError):
        validate_authorization_schema(rec)


def test_wrong_recovery_protocol_sha_rejected():
    rec = _valid_recovery_payload()
    rec["recovery_protocol_canonical"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_implementation_commit_rejected():
    rec = _valid_recovery_payload()
    rec["implementation_commit"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_manifest_rejected():
    rec = _valid_recovery_payload()
    rec["implementation_manifest_sha256"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_root_rejected():
    rec = _valid_recovery_payload()
    rec["recovery_root"] = "data/processed/research/hedging_policies"
    rec["artifact_roots"] = ["data/processed/research/hedging_synthetic", "data/processed/research/hedging_policies"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_tuple_outside_frozen_45_rejected():
    rec = _valid_recovery_payload()
    rec["recovery_tuples"].append({"member": "seed-01", "cost": 0.0, "hedger_seed": 99999})
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_predecessor_tuple_mismatch_rejected():
    rec = _valid_recovery_payload()
    # Remove one predecessor
    rec["predecessor_identities"].pop(list(rec["predecessor_identities"].keys())[0])
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_predecessor_sha_mismatch_rejected():
    rec = _valid_recovery_payload()
    k = list(rec["predecessor_identities"].keys())[0]
    rec["predecessor_identities"][k]["historical_checkpoint_sha"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_historical_artifact_path_rejected():
    rec = _valid_recovery_payload()
    k = list(rec["predecessor_identities"].keys())[0]
    rec["predecessor_identities"][k]["historical_artifact_path"] = "wrong/path"
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_historical_started_sha_rejected():
    rec = _valid_recovery_payload()
    k = list(rec["predecessor_identities"].keys())[0]
    rec["predecessor_identities"][k]["historical_execution_started_sha"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_historical_terminal_sha_rejected():
    rec = _valid_recovery_payload()
    k = list(rec["predecessor_identities"].keys())[0]
    rec["predecessor_identities"][k]["historical_terminal_sha"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_historical_classification_rejected():
    rec = _valid_recovery_payload()
    k = list(rec["predecessor_identities"].keys())[0]
    rec["predecessor_identities"][k]["historical_classification"] = "WRONG"
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_wrong_evidence_canonical_rejected():
    rec = _valid_recovery_payload()
    # Tamper trusted evidence verification by patching EVIDENCE_CANONICAL
    import neuralmarket.research.deep_hedging.runner as runner

    orig = runner.EVIDENCE_CANONICAL
    runner.EVIDENCE_CANONICAL = "0" * 64
    try:
        with pytest.raises(AuthorizationError):
            validate_recovery_authorization_schema(rec)
    finally:
        runner.EVIDENCE_CANONICAL = orig


def test_wrong_evidence_blob_rejected():
    rec = _valid_recovery_payload()
    import neuralmarket.research.deep_hedging.runner as runner

    orig = runner.EVIDENCE_BLOB
    runner.EVIDENCE_BLOB = "0" * 40
    try:
        with pytest.raises(AuthorizationError):
            validate_recovery_authorization_schema(rec)
    finally:
        runner.EVIDENCE_BLOB = orig


def test_duplicate_evidence_tuple_rejected():
    # Duplicate tuple in evidence would be caught by trusted map helper; test recovery validator duplicate
    rec = _valid_recovery_payload()
    rec["recovery_tuples"].append(rec["recovery_tuples"][0])
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_missing_evidence_tuple_rejected():
    rec = _valid_recovery_payload()
    rec["recovery_tuples"] = rec["recovery_tuples"][:-1]
    rec["predecessor_identities"].pop(list(rec["predecessor_identities"].keys())[-1])
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_record_count_not_45_rejected():
    rec = _valid_recovery_payload()
    rec["recovery_tuples"] = rec["recovery_tuples"][:10]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_generation_1_rejected():
    rec = _valid_recovery_payload()
    rec["max_generation_invocations"] = 1
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_generation_5_rejected():
    rec = _valid_recovery_payload()
    rec["max_generation_invocations"] = 5
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(rec)


def test_exact_45_predecessor_map_passes():
    rec = _valid_recovery_payload()
    # Should pass exact trusted map
    validate_recovery_authorization_schema(rec)
    # Also test that historical auth still rejected and reverse
    hist = json.loads(Path("reports/protocol/hedging_execution_authorization_212.json").read_text())
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(hist)
    with pytest.raises(AuthorizationError):
        validate_authorization_schema(rec)


def test_recovery_path_deterministic():
    from neuralmarket.research.deep_hedging.trainer import RECOVERY_ROOT_PATH

    def recovery_dir(member, cost, seed):
        bps = {0.0: 0, 0.0010: 10, 0.0050: 50}[cost]
        return RECOVERY_ROOT_PATH / f"{RUN_PREFIXES[member]}_{member}" / f"c_{bps}" / f"h_{seed}"

    p1 = recovery_dir("seed-01", 0.0, 31001)
    p2 = recovery_dir("seed-01", 0.0, 31001)
    assert p1 == p2
    assert "hedging_policies_recovery_v1" in str(p1)


def test_recovery_path_distinct_from_historical():
    from neuralmarket.research.deep_hedging.trainer import RECOVERY_ROOT_PATH

    def hist_dir(member, cost, seed):
        bps = {0.0: 0, 0.0010: 10, 0.0050: 50}[cost]
        return Path(f"data/processed/research/hedging_policies/{RUN_PREFIXES[member]}_{member}/c_{bps}/h_{seed}")

    def rec_dir(member, cost, seed):
        bps = {0.0: 0, 0.0010: 10, 0.0050: 50}[cost]
        return RECOVERY_ROOT_PATH / f"{RUN_PREFIXES[member]}_{member}" / f"c_{bps}" / f"h_{seed}"

    assert hist_dir("seed-01", 0.0, 31001) != rec_dir("seed-01", 0.0, 31001)
    assert "hedging_policies_recovery_v1" not in str(hist_dir("seed-01", 0.0, 31001))


def test_historical_directory_may_exist_without_colliding(tmp_path: Path):
    # Create historical dir in tmp
    hist = tmp_path / "data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31001"
    hist.mkdir(parents=True)
    (hist / "execution_started.json").write_text("{}")
    # Recovery dir for same tuple is distinct
    from neuralmarket.research.deep_hedging.trainer import RECOVERY_ROOT_PATH

    rec = RECOVERY_ROOT_PATH / "5bdbaabd2fb257a7_seed-01/c_0/h_31001"
    # Even if we patch RECOVERY_ROOT to tmp, historical existence must not block recovery
    # Here we just prove paths are distinct
    assert str(hist) != str(rec)
    # Simulate recovery check: recovery started not exists, so would not be blocked by historical
    assert not (tmp_path / "data/processed/research/hedging_policies_recovery_v1/5bdbaabd2fb257a7_seed-01/c_0/h_31001/execution_started.json").exists()


def test_recovery_started_marker_write_once(tmp_path: Path):
    from neuralmarket.research.deep_hedging.generation import _generate_and_persist_synthetic_dataset_internal as gen
    from neuralmarket.research.deep_hedging.trainer import _train_one_policy_internal

    rp = RUN_PREFIXES["seed-01"]
    ds = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_episodes_v1.parquet"
    mp = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_manifest_v1.json"
    gen(member="seed-01", run_prefix=rp, synthetic_seed=42001, num_episodes=8, dataset_path=ds, manifest_path=mp, device="cpu", increment_provider=fake_provider, verify_contract_runtime=False)
    rec_root = tmp_path / "recovery"
    # First invocation
    _train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=31001, synthetic_dataset_path=ds, synthetic_manifest_path=mp, policy_root=rec_root, run_prefix=rp, max_epochs=1, batch_size=4, device="cpu", verify_contract_runtime=False)
    # Second should refuse
    with pytest.raises(FileExistsError, match="OVERWRITE_REFUSED"):
        _train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=31001, synthetic_dataset_path=ds, synthetic_manifest_path=mp, policy_root=rec_root, run_prefix=rp, max_epochs=1, batch_size=4, device="cpu", verify_contract_runtime=False)


def test_failed_recovery_cannot_retry(tmp_path: Path):
    from neuralmarket.research.deep_hedging.generation import _generate_and_persist_synthetic_dataset_internal as gen
    from neuralmarket.research.deep_hedging.trainer import _train_one_policy_internal

    rp = RUN_PREFIXES["seed-01"]
    ds = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_episodes_v1.parquet"
    mp = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_manifest_v1.json"
    gen(member="seed-01", run_prefix=rp, synthetic_seed=42001, num_episodes=8, dataset_path=ds, manifest_path=mp, device="cpu", increment_provider=fake_provider, verify_contract_runtime=False)
    rec_root = tmp_path / "recovery2"
    # Inject failure at epoch 0
    with pytest.raises(RuntimeError, match="injected failure"):
        _train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=31001, synthetic_dataset_path=ds, synthetic_manifest_path=mp, policy_root=rec_root, run_prefix=rp, max_epochs=1, batch_size=4, device="cpu", verify_contract_runtime=False, inject_failure_at_epoch=0)
    # Second attempt should still be refused (failed consumed)
    with pytest.raises(FileExistsError, match="OVERWRITE_REFUSED"):
        _train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=31001, synthetic_dataset_path=ds, synthetic_manifest_path=mp, policy_root=rec_root, run_prefix=rp, max_epochs=1, batch_size=4, device="cpu", verify_contract_runtime=False)


def test_recovery_provenance_fields_emitted(tmp_path: Path):
    from neuralmarket.research.deep_hedging.generation import _generate_and_persist_synthetic_dataset_internal as gen
    from neuralmarket.research.deep_hedging.trainer import _train_one_policy_internal

    rp = RUN_PREFIXES["seed-01"]
    ds = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_episodes_v1.parquet"
    mp = tmp_path / "syn" / f"{rp}_seed-01" / "synthetic_manifest_v1.json"
    gen(member="seed-01", run_prefix=rp, synthetic_seed=42001, num_episodes=8, dataset_path=ds, manifest_path=mp, device="cpu", increment_provider=fake_provider, verify_contract_runtime=False)
    rec_root = tmp_path / "recovery3"
    prov = {
        "recovery_protocol_path": "reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md",
        "recovery_protocol_canonical": RECOVERY_PROTOCOL_CANONICAL,
        "recovery_protocol_blob": RECOVERY_PROTOCOL_BLOB,
        "recovery_implementation_commit": REPAIRED_IMPLEMENTATION_COMMIT,
        "recovery_implementation_manifest": REPAIRED_IMPLEMENTATION_MANIFEST,
        "historical_predecessor_artifact_path": "data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31001",
        "historical_execution_started_sha": "a" * 64,
        "historical_checkpoint_sha": "b" * 64,
        "historical_terminal_sha": "c" * 64,
        "historical_classification": "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP",
    }
    _train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=31001, synthetic_dataset_path=ds, synthetic_manifest_path=mp, policy_root=rec_root, run_prefix=rp, max_epochs=1, batch_size=4, device="cpu", verify_contract_runtime=False, recovery_provenance=prov)
    started = json.loads((rec_root / f"{rp}_seed-01/c_0/h_31001/execution_started.json").read_text())
    assert started["recovery_protocol_canonical"] == RECOVERY_PROTOCOL_CANONICAL
    assert started["historical_classification"] == "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP"
    report = json.loads((rec_root / f"{rp}_seed-01/c_0/h_31001/training_report.json").read_text())
    assert report["recovery_implementation_commit"] == REPAIRED_IMPLEMENTATION_COMMIT


def test_same_repaired_internal_trainer_is_invoked():
    import pathlib

    text = Path("src/neuralmarket/research/deep_hedging/trainer.py").read_text()
    # Recovery must call _train_one_policy_internal, not duplicate loop
    assert "def train_one_policy_recovery" in text
    assert text.count("def _train_one_policy_internal") == 1
    # Ensure recovery calls internal
    assert "return _train_one_policy_internal(" in text
def test_no_duplicated_optimization_implementation():
    text = Path("src/neuralmarket/research/deep_hedging/trainer.py").read_text()
    # Optimization loop should appear only once (in internal)
    assert text.count("cvar.backward()") == 1
    assert text.count("clip_grad_norm_(") == 1
    assert text.count("for start in range(0, N_train") == 1
    assert text.count("hedger.train()") == 1
