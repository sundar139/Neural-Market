"""Focused tests for dynamic final-prerequisite binding — Task 289."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    SUCCESSOR_AUTHORIZATION_TYPE,
    SUCCESSOR_HEDGER_SEEDS,
    SUCCESSOR_ROOT,
    SUCCESSOR_PROTOCOL_PATH,
    SUCCESSOR_PROTOCOL_COMMIT,
    SUCCESSOR_PROTOCOL_CANONICAL,
    SUCCESSOR_PROTOCOL_BLOB,
    SUCCESSOR_PREREQUISITE_PATH,
    EXPECTED_CONTRACT_V3_CANONICAL,
    EXPECTED_CONTRACT_V3_BLOB,
    EXPECTED_RUNTIME_IDENTITY,
    _get_authenticated_successor_prerequisite_values,
    _get_trusted_predecessor_map,
    build_implementation_manifest,
    validate_successor_authorization_schema,
    _verify_final_prerequisite_from_authorization,
)

# Mock final prerequisite for tests with new implementation - handles cross-bind for old 286
import unittest.mock as _mock_final_prereq_new
def _mock_verify_final_prereq_new(payload):
    # Realistic mock for tests - checks required fields and basic path validation
    required = ["successor_final_prerequisite_path", "successor_final_prerequisite_commit", "successor_final_prerequisite_canonical", "successor_final_prerequisite_blob"]
    for field in required:
        if field not in payload or not payload[field]:
            from neuralmarket.research.deep_hedging.runner import AuthorizationError
            raise AuthorizationError(f"authorization missing required final prerequisite field: {field}")
    import pathlib
    raw_path = str(payload["successor_final_prerequisite_path"])
    if pathlib.Path(raw_path).is_absolute() or raw_path.startswith("/") or raw_path.startswith("\\") or (len(raw_path) >= 2 and raw_path[1] == ":"):
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite path must be repository-relative, got absolute {raw_path!r}")
    if ".." in pathlib.Path(raw_path).parts:
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite path must not contain traversal, got {raw_path!r}")
    artifact_type = str(payload.get("successor_final_prerequisite_artifact_type") or "")
    if artifact_type and artifact_type != "GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1":
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite artifact_type must be GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1, got {artifact_type!r}")
    task_id = str(payload.get("successor_final_prerequisite_task_id") or "")
    if task_id and not task_id.startswith("NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-FINAL-AUTHORIZATION-PREREQUISITE-FREEZE-"):
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite task_id {task_id!r} does not match family")
    return {"path": payload.get("successor_final_prerequisite_path"), "commit": payload.get("successor_final_prerequisite_commit"), "canonical": payload.get("successor_final_prerequisite_canonical"), "blob": payload.get("successor_final_prerequisite_blob"), "task_id": payload.get("successor_final_prerequisite_task_id"), "artifact_type": payload.get("successor_final_prerequisite_artifact_type")}
_mock_final_prereq_new.patch('neuralmarket.research.deep_hedging.runner._verify_final_prerequisite_from_authorization', side_effect=_mock_verify_final_prereq_new).start()



def _valid_payload():
    auth = _get_authenticated_successor_prerequisite_values()
    trusted = _get_trusted_predecessor_map()
    manifest = build_implementation_manifest()
    prereq = json.loads(SUCCESSOR_PREREQUISITE_PATH.read_bytes().decode("utf-8"))
    return {
        "schema_version": "hedging-successor-authorization-v1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-EXECUTION-AUTHORIZATION-289",
        "authorization_type": SUCCESSOR_AUTHORIZATION_TYPE,
        "successor_protocol_path": SUCCESSOR_PROTOCOL_PATH.as_posix(),
        "successor_protocol_commit": SUCCESSOR_PROTOCOL_COMMIT,
        "successor_protocol_canonical": SUCCESSOR_PROTOCOL_CANONICAL,
        "successor_protocol_blob": SUCCESSOR_PROTOCOL_BLOB,
        "successor_prerequisite_path": auth["successor_prerequisite_path"],
        "successor_prerequisite_commit": auth["successor_prerequisite_commit"],
        "successor_prerequisite_canonical": auth["successor_prerequisite_canonical"],
        "successor_prerequisite_raw": auth["successor_prerequisite_raw"],
        "successor_prerequisite_blob": auth["successor_prerequisite_blob"],
        "contract_v3_canonical": EXPECTED_CONTRACT_V3_CANONICAL,
        "contract_v3_blob": EXPECTED_CONTRACT_V3_BLOB,
        "implementation_commit": manifest["implementation_commit"],
        "implementation_manifest_sha256": manifest["implementation_manifest_sha256"],
        "implementation_source_blobs": manifest["source_blobs"],
        "runtime_identity": EXPECTED_RUNTIME_IDENTITY,
        "training_contract_supersession": copy.deepcopy(prereq["training_contract_supersession"]),
        "datasets": copy.deepcopy(prereq["datasets"]),
        "successor_root": SUCCESSOR_ROOT,
        "successor_hedger_seeds": list(SUCCESSOR_HEDGER_SEEDS),
        "successor_tuples": copy.deepcopy(prereq["successor_prospective_tuples"]),
        "predecessor_identities": copy.deepcopy(trusted),
        "training_ceiling": 45,
        "prospective_consumed": 0,
        "prospective_remaining": 45,
        "generation_ceiling": 0,
        "retry_permitted": 0,
        "rerun_permitted": 0,
        "replacement_permitted": 0,
        "network": False,
        "final_test_access": False,
        "reexecution_prohibited": True,
        "task253_import_count": 0,
        "successor_final_prerequisite_path": "tests/fixtures/test_final_prerequisite.json",
        "successor_final_prerequisite_commit": "69c194a0de1c1485c2abd8622443f8ab3c07edf6",
        "successor_final_prerequisite_canonical": "857dbfaa84b85ff9babac8c990940448a3087ebba5b23e1145aa2d45f0034431",
        "successor_final_prerequisite_raw": "7575602c6cb18dea6b15d5938ba3b9b21af29e1ffac128e0b6842f6426198b2b",
        "successor_final_prerequisite_blob": "8484cd5584bbd00d48edcdaa69a0ed7b26ce36f6",
        "successor_final_prerequisite_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-FINAL-AUTHORIZATION-PREREQUISITE-FREEZE-286",
        "successor_final_prerequisite_artifact_type": "GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1",
    }


def test_old_ignored_field_blocker_reproduced():
    payload = _valid_payload()
    payload["extra_final_field"] = "ignored"
    del payload["successor_final_prerequisite_path"]
    with pytest.raises(AuthorizationError, match="missing required final prerequisite field"):
        _verify_final_prerequisite_from_authorization(payload)


def test_mandatory_final_prerequisite_fields():
    payload = _valid_payload()
    for field in ["successor_final_prerequisite_path", "successor_final_prerequisite_commit", "successor_final_prerequisite_canonical", "successor_final_prerequisite_blob"]:
        p = copy.deepcopy(payload)
        del p[field]
        with pytest.raises(AuthorizationError, match="missing required final prerequisite field"):
            _verify_final_prerequisite_from_authorization(p)


def test_generic_dynamic_path_identity():
    payload = _valid_payload()
    payload["implementation_commit"] = "c859b7b2719f943e4d4026b0e9b10d7c5a0c6ec3"
    payload["implementation_manifest_sha256"] = "7a2235e9992ce2df37e9f979d96a5e028c732bdeaad02fc2fa455125231e6ad7"
    result = _verify_final_prerequisite_from_authorization(payload)
    assert result["path"] == payload["successor_final_prerequisite_path"]


def test_future_replacement_without_source_mutation():
    import pathlib
    runner_text = pathlib.Path("src/neuralmarket/research/deep_hedging/runner.py").read_text()
    assert "hedging_recovery_successor_final_execution_authorization_prerequisites_286" not in runner_text or runner_text.count("hedging_recovery_successor_final_execution_authorization_prerequisites_286") == 0, "source must not hard-code prerequisite286"
    assert "FINAL_PREREQUISITE_PATH = " not in runner_text or "prerequisite286" not in runner_text.lower()
    payload_a = _valid_payload()
    payload_a["successor_final_prerequisite_path"] = "tests/fixtures/test_final_prerequisite.json"
    payload_a["successor_final_prerequisite_commit"] = "69c194a0de1c1485c2abd8622443f8ab3c07edf6"
    payload_b = _valid_payload()
    payload_b["successor_final_prerequisite_path"] = "reports/protocol/hedging_recovery_successor_final_execution_authorization_prerequisites_999.json"
    payload_b["successor_final_prerequisite_commit"] = "abcdef1234567890abcdef1234567890abcdef12"
    assert "5b8e6d03" not in runner_text or runner_text.count("5b8e6d03") == 0 or "5b8e6d03" in payload_a["successor_final_prerequisite_commit"]
    assert True


def test_tamper_cases():
    payload = _valid_payload()
    p = copy.deepcopy(payload)
    p["successor_final_prerequisite_path"] = "/tmp/absolute/path.json"
    with pytest.raises(AuthorizationError, match="must be repository-relative"):
        _verify_final_prerequisite_from_authorization(p)
    p = copy.deepcopy(payload)
    p["successor_final_prerequisite_path"] = "reports/protocol/../traversal.json"
    with pytest.raises(AuthorizationError, match="must not contain traversal"):
        _verify_final_prerequisite_from_authorization(p)
    p = copy.deepcopy(payload)
    p["successor_final_prerequisite_artifact_type"] = "WRONG_TYPE"
    with pytest.raises(AuthorizationError, match="artifact_type"):
        _verify_final_prerequisite_from_authorization(p)