"""Direct success-path regression for trainer.py authorized_commit bug — Task 259."""
from __future__ import annotations

import inspect
from pathlib import Path
from unittest import mock

import pytest

from neuralmarket.research.deep_hedging.runner import build_implementation_manifest

def test_build_manifest_signature_has_implementation_commit():
    sig = inspect.signature(build_implementation_manifest)
    assert "implementation_commit" in sig.parameters
    # no compatibility alias
    assert "authorized_commit" not in sig.parameters

def test_build_manifest_rejects_authorized_commit():
    with pytest.raises(TypeError, match="unexpected keyword argument 'authorized_commit'"):
        build_implementation_manifest(authorized_commit="abc")  # type: ignore[call-arg]

def test_recovery_provenance_success_path_reaches_formerly_broken_call(tmp_path):
    # This test proves the formerly broken manifest rebuild now succeeds
    # without monkey patch, and provenance proceeds beyond that line.
    # Use a temporary authorization that is valid for current HEAD to avoid manifest drift.
    from neuralmarket.research.deep_hedging.trainer import train_one_policy_recovery
    from neuralmarket.research.deep_hedging.runner import build_implementation_manifest, _get_trusted_predecessor_map, RECOVERY_PROTOCOL_PATH, RECOVERY_PROTOCOL_CANONICAL, RECOVERY_PROTOCOL_BLOB, RECOVERY_ROOT, RECOVERY_AUTHORIZATION_TYPE
    from neuralmarket.research.deep_hedging.artifacts import MEMBERS, COST_LEVELS, HEDGER_SEEDS
    import json

    # Build a valid payload for current HEAD
    tuples = [{"member": m, "cost": c, "hedger_seed": s} for m in MEMBERS for c in COST_LEVELS for s in HEDGER_SEEDS]
    pred = _get_trusted_predecessor_map()
    mani = build_implementation_manifest()
    # Use the same prerequisite as 251 but need to get it
    import pathlib, hashlib, subprocess
    prereq_path = pathlib.Path("reports/protocol/hedging_recovery_v2_authorization_prerequisites_246.json")
    prereq_data = prereq_path.read_bytes()
    prereq_canonical = hashlib.sha256(prereq_data.replace(b"\r\n", b"\n")).hexdigest()
    prereq_raw = hashlib.sha256(prereq_data).hexdigest()
    prereq_blob = subprocess.check_output(["git", "hash-object", str(prereq_path)]).decode().strip()
    payload = {
        "schema_version": "hedging-recovery-authorization-v1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-999",
        "authorization_type": RECOVERY_AUTHORIZATION_TYPE,
        "recovery_protocol_path": str(RECOVERY_PROTOCOL_PATH),
        "recovery_protocol_canonical": RECOVERY_PROTOCOL_CANONICAL,
        "recovery_protocol_blob": RECOVERY_PROTOCOL_BLOB,
        "prerequisite_artifact_path": str(prereq_path.as_posix()),
        "prerequisite_commit": "d4813d60002128c898fe88e40fd846dde80b5c3d",
        "prerequisite_canonical_sha256": prereq_canonical,
        "prerequisite_raw_sha256": prereq_raw,
        "prerequisite_blob": prereq_blob,
        "retry_permitted": 0,
        "rerun_permitted": 0,
        "replacement_permitted": 0,
        "contract_v3_canonical": "79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01",
        "contract_v3_blob": "eef7ad220db889166469799372759dfe1a96e35f",
        "implementation_commit": mani["implementation_commit"],
        "implementation_manifest_sha256": mani["implementation_manifest_sha256"],
        "implementation_source_blobs": mani["source_blobs"],
        "runtime_identity": "17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada",
        "recovery_root": RECOVERY_ROOT,
        "artifact_roots": ["data/processed/research/hedging_synthetic", RECOVERY_ROOT],
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
    # Write to a temp file that we will mock as tracked
    tmp_auth = tmp_path / "tmp_auth.json"
    tmp_auth.write_text(json.dumps(payload))
    # Mock verify_authorization_artifact to return info matching our payload, and validate to pass
    fake_info = {
        "canonical_sha256": "a" * 64,
        "git_blob": "b" * 40,
        "commit": mani["implementation_commit"],
        "authorization_task_id": payload["authorization_task_id"],
        "path": str(tmp_auth),
    }
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=fake_info):
        with mock.patch("neuralmarket.research.deep_hedging.runner.validate_recovery_authorization_schema"):
            with mock.patch("neuralmarket.research.deep_hedging.runner.verify_implementation_manifest"):
                with mock.patch("neuralmarket.research.deep_hedging.runner.preflight_checks"):
                    with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
                        mock_train.return_value = {"best_epoch": 11, "mocked": True}
                        result = train_one_policy_recovery(member="seed-01", cost=0.0, hedger_seed=31001, authorization_path=tmp_auth)
                        assert mock_train.called
                        assert mock_train.call_count == 1

    # Ensure no alias was added to runner
    import neuralmarket.research.deep_hedging.runner as runner
    assert "authorized_commit" not in inspect.signature(runner.build_implementation_manifest).parameters

def test_recovery_still_fail_closed_on_wrong_authorization():
    from neuralmarket.research.deep_hedging.trainer import train_one_policy_recovery

    auth = Path("reports/protocol/hedging_recovery_v2_execution_authorization_251.json")
    # tamper by using a different member not in allowlist should still fail before provenance
    with pytest.raises(Exception):
        train_one_policy_recovery(member="invalid-member", cost=0.0, hedger_seed=31001, authorization_path=auth)

def test_recovery_still_fail_closed_on_wrong_implementation_via_validator():
    from neuralmarket.research.deep_hedging.runner import validate_recovery_authorization_schema
    import json

    auth = Path("reports/protocol/hedging_recovery_v2_execution_authorization_251.json")
    payload = json.loads(auth.read_bytes().decode())
    payload["implementation_commit"] = "0" * 40
    with pytest.raises(Exception):
        validate_recovery_authorization_schema(payload)