"""V2 recovery authorization validator hardening — Task 249 adversarial tests."""
from __future__ import annotations

import copy

import pytest

from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    RECOVERY_AUTHORIZATION_TYPE,
    RECOVERY_PROTOCOL_BLOB,
    RECOVERY_PROTOCOL_CANONICAL,
    RECOVERY_PROTOCOL_PATH,
    RECOVERY_ROOT,
    _get_authenticated_prerequisite_values,
    _get_trusted_predecessor_map,
    build_implementation_manifest,
    validate_recovery_authorization_schema,
)
from neuralmarket.research.deep_hedging.artifacts import COST_LEVELS, HEDGER_SEEDS, MEMBERS


def _valid_hardened_payload():
    tuples = []
    for m in MEMBERS:
        for c in COST_LEVELS:
            for s in HEDGER_SEEDS:
                tuples.append({"member": m, "cost": c, "hedger_seed": s})
    pred = _get_trusted_predecessor_map()
    mani = build_implementation_manifest()
    prereq = _get_authenticated_prerequisite_values()
    return {
        "schema_version": "hedging-execution-authorization-v1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-223",
        "authorization_type": RECOVERY_AUTHORIZATION_TYPE,
        "recovery_protocol_path": str(RECOVERY_PROTOCOL_PATH),
        "recovery_protocol_canonical": RECOVERY_PROTOCOL_CANONICAL,
        "recovery_protocol_blob": RECOVERY_PROTOCOL_BLOB,
        "prerequisite_artifact_path": prereq["prerequisite_artifact_path"],
        "prerequisite_commit": prereq["prerequisite_commit"],
        "prerequisite_canonical_sha256": prereq["prerequisite_canonical_sha256"],
        "prerequisite_raw_sha256": prereq["prerequisite_raw_sha256"],
        "prerequisite_blob": prereq["prerequisite_blob"],
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


def test_valid_hardened_passes():
    payload = _valid_hardened_payload()
    validate_recovery_authorization_schema(payload)


def test_wrong_prerequisite_path():
    payload = _valid_hardened_payload()
    payload["prerequisite_artifact_path"] = "reports/protocol/wrong.json"
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_wrong_prerequisite_commit():
    payload = _valid_hardened_payload()
    payload["prerequisite_commit"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_wrong_prerequisite_canonical():
    payload = _valid_hardened_payload()
    payload["prerequisite_canonical_sha256"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_wrong_prerequisite_raw():
    payload = _valid_hardened_payload()
    payload["prerequisite_raw_sha256"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_wrong_prerequisite_blob():
    payload = _valid_hardened_payload()
    payload["prerequisite_blob"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_missing_prerequisite_path():
    payload = _valid_hardened_payload()
    del payload["prerequisite_artifact_path"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_missing_prerequisite_commit():
    payload = _valid_hardened_payload()
    del payload["prerequisite_commit"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_missing_prerequisite_canonical():
    payload = _valid_hardened_payload()
    del payload["prerequisite_canonical_sha256"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_missing_prerequisite_blob():
    payload = _valid_hardened_payload()
    del payload["prerequisite_blob"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_missing_prerequisite_raw():
    payload = _valid_hardened_payload()
    del payload["prerequisite_raw_sha256"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_malformed_prerequisite_blob_type():
    payload = _valid_hardened_payload()
    payload["prerequisite_blob"] = 12345  # wrong type
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_retry_1_rejected():
    payload = _valid_hardened_payload()
    payload["retry_permitted"] = 1
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_rerun_1_rejected():
    payload = _valid_hardened_payload()
    payload["rerun_permitted"] = 1
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_replacement_1_rejected():
    payload = _valid_hardened_payload()
    payload["replacement_permitted"] = 1
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_retry_missing_rejected():
    payload = _valid_hardened_payload()
    del payload["retry_permitted"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_rerun_missing_rejected():
    payload = _valid_hardened_payload()
    del payload["rerun_permitted"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_replacement_missing_rejected():
    payload = _valid_hardened_payload()
    del payload["replacement_permitted"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_retry_wrong_type_string():
    payload = _valid_hardened_payload()
    payload["retry_permitted"] = "0"
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_rerun_wrong_type_bool():
    payload = _valid_hardened_payload()
    payload["rerun_permitted"] = False  # bool should be rejected
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_replacement_wrong_type_none():
    payload = _valid_hardened_payload()
    payload["replacement_permitted"] = None
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_retry_negative():
    payload = _valid_hardened_payload()
    payload["retry_permitted"] = -1
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


# Rerun existing adversarial cases
def test_wrong_implementation_rejected():
    payload = _valid_hardened_payload()
    payload["implementation_commit"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_wrong_manifest_rejected():
    payload = _valid_hardened_payload()
    payload["implementation_manifest_sha256"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_wrong_source_blob_rejected():
    payload = _valid_hardened_payload()
    # tamper one blob
    first = next(iter(payload["implementation_source_blobs"]))
    payload["implementation_source_blobs"][first] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_v1_root_rejected():
    payload = _valid_hardened_payload()
    payload["recovery_root"] = "data/processed/research/hedging_policies_recovery_v1"
    payload["artifact_roots"] = ["data/processed/research/hedging_synthetic", "data/processed/research/hedging_policies_recovery_v1"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_arbitrary_root_rejected():
    payload = _valid_hardened_payload()
    payload["recovery_root"] = "data/processed/research/hedging_policies_recovery_v3"
    payload["artifact_roots"] = ["data/processed/research/hedging_synthetic", "data/processed/research/hedging_policies_recovery_v3"]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_ceiling44_rejected():
    payload = _valid_hardened_payload()
    payload["max_training_invocations"] = 44
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_ceiling46_rejected():
    payload = _valid_hardened_payload()
    payload["max_training_invocations"] = 46
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_generation1_rejected():
    payload = _valid_hardened_payload()
    payload["max_generation_invocations"] = 1
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_network_true_rejected():
    payload = _valid_hardened_payload()
    payload["network"] = True
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_final_true_rejected():
    payload = _valid_hardened_payload()
    payload["final_test_access"] = True
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_missing_tuple_rejected():
    payload = _valid_hardened_payload()
    payload["recovery_tuples"] = payload["recovery_tuples"][:-1]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_extra_tuple_rejected():
    payload = _valid_hardened_payload()
    payload["recovery_tuples"] = payload["recovery_tuples"] + [{"member": "seed-01", "cost": 0.0, "hedger_seed": 99999}]
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)


def test_predecessor_tamper_rejected():
    payload = _valid_hardened_payload()
    key = next(iter(payload["predecessor_identities"]))
    payload["predecessor_identities"][key]["historical_checkpoint_sha"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_recovery_authorization_schema(payload)
