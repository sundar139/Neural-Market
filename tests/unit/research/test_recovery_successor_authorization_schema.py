"""Adversarial tests for successor execution-authorization schema — Task 270."""
from __future__ import annotations

import copy
import json
import hashlib
import subprocess
from pathlib import Path

import pytest

from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    SUCCESSOR_AUTHORIZATION_TYPE,
    SUCCESSOR_HEDGER_SEEDS,
    SUCCESSOR_PROTOCOL_BLOB,
    SUCCESSOR_PROTOCOL_CANONICAL,
    SUCCESSOR_PROTOCOL_COMMIT,
    SUCCESSOR_PROTOCOL_PATH,
    SUCCESSOR_ROOT,
    SUCCESSOR_PREREQUISITE_PATH,
    _get_authenticated_successor_prerequisite_values,
    _get_trusted_predecessor_map,
    build_implementation_manifest,
    validate_successor_authorization_schema,
    EXPECTED_CONTRACT_V3_CANONICAL,
    EXPECTED_CONTRACT_V3_BLOB,
    EXPECTED_RUNTIME_IDENTITY,
)


def _valid_payload():
    auth = _get_authenticated_successor_prerequisite_values()
    trusted = _get_trusted_predecessor_map()
    manifest = build_implementation_manifest()
    prereq = json.loads(SUCCESSOR_PREREQUISITE_PATH.read_bytes().decode("utf-8"))
    datasets = prereq["datasets"]
    tuples = copy.deepcopy(prereq["successor_prospective_tuples"])
    supersession = copy.deepcopy(prereq["training_contract_supersession"])
    return {
        "schema_version": "hedging-successor-authorization-v1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-EXECUTION-AUTHORIZATION-270",
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
        "training_contract_supersession": supersession,
        "datasets": copy.deepcopy(datasets),
        "successor_root": SUCCESSOR_ROOT,
        "successor_hedger_seeds": list(SUCCESSOR_HEDGER_SEEDS),
        "successor_tuples": tuples,
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
        "successor_final_prerequisite_path": "reports/protocol/hedging_recovery_successor_final_execution_authorization_prerequisites_286.json",
        "successor_final_prerequisite_commit": "5b8e6d03de6c88f56dadc5a4e9609870946926e4",
        "successor_final_prerequisite_canonical": "08d148fbce45848d16533b072d4baba47dd1347563580a77561d2bb61310a249",
        "successor_final_prerequisite_raw": "f5fba315c62d9c287c17fb5cb121613553957500d16bdea68c83b949c76638c7",
        "successor_final_prerequisite_blob": "a743c1d98c50ca37e6c7fa343c7867dabccdc444",
        "successor_final_prerequisite_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-FINAL-AUTHORIZATION-PREREQUISITE-FREEZE-286",
        "successor_final_prerequisite_artifact_type": "GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1",
    }

def test_valid_payload_passes():
    payload = _valid_payload()
    validate_successor_authorization_schema(payload)
    # Must not have created real authorization artifact or recovery_v3 root
    assert not Path("reports/protocol/hedging_recovery_successor_execution_authorization_270.json").exists()
    assert not Path("data/processed/research/hedging_policies_recovery_v3").exists()


# ---- discriminator ----
def test_wrong_authorization_type_rejected():
    p = _valid_payload()
    p["authorization_type"] = "GRU_TRAINING_RECOVERY_V1"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_task_family_rejected():
    p = _valid_payload()
    p["authorization_task_id"] = "NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-212"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_recovery_family_rejected():
    p = _valid_payload()
    p["authorization_task_id"] = "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-223"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_prerequisite_as_auth_rejected():
    p = _valid_payload()
    p["artifact_type"] = "GRU_TRAINING_RECOVERY_SUCCESSOR_AUTHORIZATION_PREREQUISITES_V2"
    p["task_id"] = "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-AUTHORIZATION-PREREQUISITES-264"
    # Also change auth type to prerequisite-like? our validator checks artifact_type
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_authorization_251_rejected():
    p = _valid_payload()
    # Load real 251 payload type and try to validate as successor
    try:
        auth251 = json.loads(Path("reports/protocol/hedging_recovery_v2_execution_authorization_251.json").read_bytes().decode("utf-8"))
        # Use its type
        p["authorization_type"] = auth251.get("authorization_type", "GRU_TRAINING_RECOVERY_V1")
        p["authorization_task_id"] = auth251.get("authorization_task_id", "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-251")
    except Exception:
        p["authorization_type"] = "GRU_TRAINING_RECOVERY_V1"
        p["authorization_task_id"] = "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-251"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_authorization_248_rejected():
    p = _valid_payload()
    p["authorization_type"] = "GRU_TRAINING_RECOVERY_V1"
    p["authorization_task_id"] = "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-248"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


# ---- prerequisite identity ----
def test_wrong_prerequisite_path_rejected():
    p = _valid_payload()
    p["successor_prerequisite_path"] = "reports/protocol/wrong.json"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_prerequisite_commit_rejected():
    p = _valid_payload()
    p["successor_prerequisite_commit"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_prerequisite_canonical_rejected():
    p = _valid_payload()
    p["successor_prerequisite_canonical"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_prerequisite_blob_rejected():
    p = _valid_payload()
    p["successor_prerequisite_blob"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


# ---- successor protocol / contract ----
def test_wrong_successor_protocol_rejected():
    p = _valid_payload()
    p["successor_protocol_canonical"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_contract_rejected():
    p = _valid_payload()
    p["contract_v3_canonical"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_supersession_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = {"superseded_clauses": []}
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


# ---- implementation binding ----
def test_stale_implementation_d762_rejected():
    p = _valid_payload()
    p["implementation_commit"] = "d762e5a18a1552d34fce79ea5d765a66c042d9c1"
    p["implementation_manifest_sha256"] = "9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a"
    with pytest.raises(AuthorizationError, match="stale"):
        validate_successor_authorization_schema(p)


def test_stale_implementation_aa3f81_rejected():
    p = _valid_payload()
    p["implementation_commit"] = "aa3f81ddeb6bce3b66c264c49caee82f79a5dccf"
    p["implementation_manifest_sha256"] = "7e848b0696eb55f805992794df48703d5434491cb57b428f92e2cf5242ba651e"
    with pytest.raises(AuthorizationError, match="stale"):
        validate_successor_authorization_schema(p)


def test_stale_manifest_rejected():
    p = _valid_payload()
    p["implementation_manifest_sha256"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_current_source_drift_rejected():
    p = _valid_payload()
    # Tamper one source blob
    first = next(iter(p["implementation_source_blobs"]))
    p["implementation_source_blobs"][first] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_per_path_blob_rejected():
    p = _valid_payload()
    # Change one blob to mismatch commit's blob
    key = "src/neuralmarket/research/deep_hedging/runner.py"
    if key in p["implementation_source_blobs"]:
        p["implementation_source_blobs"][key] = "a" * 40
        with pytest.raises(AuthorizationError):
            validate_successor_authorization_schema(p)
    else:
        pytest.skip("runner key missing")


def test_wrong_runtime_rejected():
    p = _valid_payload()
    p["runtime_identity"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_dataset_identity_rejected():
    p = _valid_payload()
    first = next(iter(p["datasets"]))
    p["datasets"][first]["sha256"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_root_rejected():
    p = _valid_payload()
    p["successor_root"] = "data/processed/research/hedging_policies"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_old_seed_rejected():
    p = _valid_payload()
    p["successor_hedger_seeds"] = [31001, 31002, 31003]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_unknown_seed_rejected():
    p = _valid_payload()
    p["successor_hedger_seeds"] = [60999, 53804, 99999]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_tuple_field_drift_rejected():
    p = _valid_payload()
    p["successor_tuples"][0]["run_prefix"] = "deadbeef"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_missing_tuple_rejected():
    p = _valid_payload()
    p["successor_tuples"] = p["successor_tuples"][:-1]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_extra_tuple_rejected():
    p = _valid_payload()
    p["successor_tuples"].append(copy.deepcopy(p["successor_tuples"][0]))
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_duplicate_tuple_rejected():
    p = _valid_payload()
    p["successor_tuples"][1] = copy.deepcopy(p["successor_tuples"][0])
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_predecessor_key_rejected():
    p = _valid_payload()
    k = next(iter(p["predecessor_identities"]))
    v = p["predecessor_identities"].pop(k)
    p["predecessor_identities"]["bad:key"] = v
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_wrong_predecessor_field_rejected():
    p = _valid_payload()
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_checkpoint_sha"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_recovery_v2_predecessor_rejected():
    p = _valid_payload()
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_artifact_path"] = p["predecessor_identities"][k]["historical_artifact_path"].replace("hedging_policies/", "hedging_policies_recovery_v2/")
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_task253_import_rejected():
    p = _valid_payload()
    p["task253_import_count"] = 1
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_ceiling_drift_rejected():
    p = _valid_payload()
    p["training_ceiling"] = 44
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_consumed_drift_rejected():
    p = _valid_payload()
    p["prospective_consumed"] = 1
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_remaining_drift_rejected():
    p = _valid_payload()
    p["prospective_remaining"] = 44
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_retry_drift_rejected():
    p = _valid_payload()
    p["retry_permitted"] = 1
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_rerun_drift_rejected():
    p = _valid_payload()
    p["rerun_permitted"] = 1
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_replacement_drift_rejected():
    p = _valid_payload()
    p["replacement_permitted"] = 1
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_generation_gt0_rejected():
    p = _valid_payload()
    p["generation_ceiling"] = 1
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_network_true_rejected():
    p = _valid_payload()
    p["network"] = True
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_final_true_rejected():
    p = _valid_payload()
    p["final_test_access"] = True
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_reexecution_allowed_rejected():
    p = _valid_payload()
    p["reexecution_prohibited"] = False
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_bool_as_int_rejected():
    p = _valid_payload()
    p["retry_permitted"] = True  # bool
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_missing_field_rejected():
    p = _valid_payload()
    del p["training_ceiling"]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)
def test_supersession_missing_rejected():
    p = _valid_payload()
    del p["training_contract_supersession"]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_none_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = None
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_type_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = "wrong"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_empty_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = {}
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_five_nulls_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = {"superseded_clauses": [None, None, None, None, None]}
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_five_empty_maps_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = {"superseded_clauses": [{}, {}, {}, {}, {}]}
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_five_arbitrary_strings_rejected():
    p = _valid_payload()
    p["training_contract_supersession"] = {"superseded_clauses": ["a", "b", "c", "d", "e"]}
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_four_clauses_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["superseded_clauses"] = p["training_contract_supersession"]["superseded_clauses"][:4]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_six_clauses_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["superseded_clauses"] = p["training_contract_supersession"]["superseded_clauses"] + [copy.deepcopy(p["training_contract_supersession"]["superseded_clauses"][0])]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_location_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["superseded_clauses"][0]["location"] = "wrong:location"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_clause_text_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["superseded_clauses"][0]["clause"] = "wrong clause text"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_classification_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["superseded_clauses"][0]["classification"] = "WRONG"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_historical_family_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["historical_hedger_seed_family"] = [1, 2, 3]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_successor_family_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["successor_hedger_seed_family"] = [1, 2, 3]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_scope_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["supersession_scope"] = "wrong scope"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_derivation_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["successor_seed_source"] = "WRONG_DERIVATION"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_wrong_audit_rejected():
    p = _valid_payload()
    p["training_contract_supersession"]["successor_seed_audit"] = "WRONG_AUDIT"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_swapped_clauses_rejected():
    p = _valid_payload()
    clauses = p["training_contract_supersession"]["superseded_clauses"]
    clauses[0], clauses[1] = clauses[1], clauses[0]
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_missing_other_family_rejected():
    p = _valid_payload()
    # Remove or corrupt OTHER_SEED_FAMILY
    if "other_seed_family_occurrence" in p["training_contract_supersession"]:
        p["training_contract_supersession"]["other_seed_family_occurrence"]["classification"] = "WRONG"
    else:
        p["training_contract_supersession"]["other_seed_family_occurrence"] = {"classification": "WRONG"}
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_missing_example_only_rejected():
    p = _valid_payload()
    if "example_only_occurrence" in p["training_contract_supersession"]:
        p["training_contract_supersession"]["example_only_occurrence"]["classification"] = "WRONG"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_decoy_commit_rejected():
    p = _valid_payload()
    del p["training_contract_supersession"]
    p["successor_supersession_commit"] = "deadbeef"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_supersession_legacy_field_rejected():
    p = _valid_payload()
    # Try legacy fallback name
    p["successor_supersession_commit"] = "deadbeef"
    # Keep correct supersession too — but decoy alone should cause rejection per validator
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_canonical_posix_passes():
    p = _valid_payload()
    # Ensure canonical forward-slash passes
    assert p["successor_protocol_path"] == SUCCESSOR_PROTOCOL_PATH.as_posix()
    validate_successor_authorization_schema(p)


def test_protocol_backslash_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = str(SUCCESSOR_PROTOCOL_PATH)  # Windows backslash on win32
    # On Windows str() is backslash, which differs from canonical POSIX
    if p["successor_protocol_path"] != SUCCESSOR_PROTOCOL_PATH.as_posix():
        with pytest.raises(AuthorizationError):
            validate_successor_authorization_schema(p)
    else:
        pytest.skip("platform uses POSIX already — backslash equals POSIX")


def test_protocol_pathlib_native_str_rejected_when_differs():
    p = _valid_payload()
    # Use native Path str — on Windows this is backslash, should be rejected
    native = str(SUCCESSOR_PROTOCOL_PATH)
    if native != SUCCESSOR_PROTOCOL_PATH.as_posix():
        p["successor_protocol_path"] = native
        with pytest.raises(AuthorizationError):
            validate_successor_authorization_schema(p)
    else:
        pytest.skip("native str equals POSIX — no difference on this platform")


def test_protocol_absolute_windows_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = "C:\\reports\\protocol\\structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_absolute_posix_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = "/reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_dot_prefix_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = "./reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_duplicate_separator_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = "reports//protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_parent_traversal_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = "reports/protocol/../protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_wrong_filename_rejected():
    p = _valid_payload()
    p["successor_protocol_path"] = "reports/protocol/wrong_protocol.md"
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_commit_still_required():
    p = _valid_payload()
    p["successor_protocol_commit"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_canonical_still_required():
    p = _valid_payload()
    p["successor_protocol_canonical"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)


def test_protocol_blob_still_required():
    p = _valid_payload()
    p["successor_protocol_blob"] = "0" * 40
    with pytest.raises(AuthorizationError):
        validate_successor_authorization_schema(p)

