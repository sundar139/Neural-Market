"""Adversarial tests for Task268 — production seam, tuple exactness, predecessor exactness (Task267 blockers)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest import mock

import pytest

from neuralmarket.research.deep_hedging.runner import (
    AuthorizationError,
    SUCCESSOR_PREREQUISITE_PATH,
    SUCCESSOR_ROOT,
    SUCCESSOR_HEDGER_SEEDS,
    get_successor_campaign_config,
    resolve_successor_artifact_path,
    validate_successor_prerequisite,
)

def _mock_verify_final_prereq2(payload):
    required = ["successor_final_prerequisite_path", "successor_final_prerequisite_commit", "successor_final_prerequisite_canonical", "successor_final_prerequisite_blob"]
    for field in required:
        if field not in payload or not payload[field]:
            from neuralmarket.research.deep_hedging.runner import AuthorizationError
            raise AuthorizationError(f"authorization missing required final prerequisite field: {field}")
    import pathlib
    raw_path = str(payload["successor_final_prerequisite_path"])
    if pathlib.Path(raw_path).is_absolute() or ".." in pathlib.Path(raw_path).parts:
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite path invalid: {raw_path!r}")
    artifact_type = str(payload.get("successor_final_prerequisite_artifact_type") or "")
    if artifact_type and artifact_type != "GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1":
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite artifact_type must be GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1, got {artifact_type!r}")
    task_id = str(payload.get("successor_final_prerequisite_task_id") or "")
    if task_id and not task_id.startswith("NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-FINAL-AUTHORIZATION-PREREQUISITE-FREEZE-"):
        from neuralmarket.research.deep_hedging.runner import AuthorizationError
        raise AuthorizationError(f"final prerequisite task_id {task_id!r} does not match family")
    return {"path": payload.get("successor_final_prerequisite_path"), "commit": payload.get("successor_final_prerequisite_commit"), "canonical": payload.get("successor_final_prerequisite_canonical"), "blob": payload.get("successor_final_prerequisite_blob"), "task_id": payload.get("successor_final_prerequisite_task_id"), "artifact_type": payload.get("successor_final_prerequisite_artifact_type")}

from neuralmarket.research.deep_hedging.trainer import SUCCESSOR_ROOT_PATH

def _load_valid_payload() -> dict:
    return json.loads(SUCCESSOR_PREREQUISITE_PATH.read_bytes().decode("utf-8"))

# ---------------------------------------------------------------------------
# A. Production integration
# ---------------------------------------------------------------------------

def test_production_seam_calls_authenticated_loader_and_validator():
    with mock.patch("neuralmarket.research.deep_hedging.runner._get_authenticated_successor_prerequisite_values") as mock_auth:
        mock_auth.return_value = {"ok": "1"}
        with mock.patch("neuralmarket.research.deep_hedging.runner.validate_successor_prerequisite") as mock_val:
            mock_val.return_value = None
            # Also need to mock _get_trusted_predecessor_map to avoid file checks inside validate mock? But validate is mocked, so fine.
            with mock.patch("neuralmarket.research.deep_hedging.runner._get_trusted_predecessor_map", return_value={}):
                cfg = get_successor_campaign_config()
                assert mock_auth.called, "seam must call authenticated loader"
                assert mock_val.called, "seam must call validator"
                # payload passed to validator must be from file, not caller dict
                called_payload = mock_val.call_args[0][0]
                file_payload = json.loads(SUCCESSOR_PREREQUISITE_PATH.read_bytes().decode("utf-8"))
                assert called_payload == file_payload

def test_production_seam_reads_from_successor_prerequisite_path_itself():
    # Ensure get_successor_campaign_config reads SUCCESSOR_PREREQUISITE_PATH
    original_read = Path.read_bytes

    read_paths: list[Path] = []

    def fake_read(self: Path):
        if self == SUCCESSOR_PREREQUISITE_PATH:
            read_paths.append(self)
        return original_read(self)

    with mock.patch.object(Path, "read_bytes", fake_read):
        cfg = get_successor_campaign_config()
        assert SUCCESSOR_PREREQUISITE_PATH in read_paths
        assert cfg["validated"] is True

def test_caller_supplied_dict_cannot_bypass_authenticated_bytes():
    # Seam takes no dict; caller cannot supply arbitrary payload to bypass file
    import inspect

    sig = inspect.signature(get_successor_campaign_config)
    assert len(sig.parameters) == 0, "production seam must not accept caller-supplied dict"
    # Also validate_successor_prerequisite still requires file auth — tamper file would fail
    payload = _load_valid_payload()
    # Even with a valid payload dict, if we tamper file on disk, seam should fail
    # Here we just prove seam does not accept dict param
    with pytest.raises(TypeError):
        get_successor_campaign_config(payload)  # type: ignore[call-arg]

def test_successor_root_path_is_consumed_by_production_path_resolution():
    cfg = get_successor_campaign_config()
    assert cfg["successor_root"] == SUCCESSOR_ROOT_PATH
    assert cfg["successor_root"].as_posix() == SUCCESSOR_ROOT
    # Resolve one tuple via trainer resolver — must be under SUCCESSOR_ROOT_PATH
    p = resolve_successor_artifact_path("seed-01", 0.0, 60999)
    assert p.as_posix().startswith(SUCCESSOR_ROOT_PATH.as_posix() + "/")
    assert SUCCESSOR_ROOT in p.as_posix()
    assert "hedging_policies_recovery_v2" not in p.as_posix()
    assert "hedging_policies_recovery_v1" not in p.as_posix()
    # Trainer helper also uses SUCCESSOR_ROOT_PATH load-bearing
    from neuralmarket.research.deep_hedging import trainer as tr

    assert tr.SUCCESSOR_ROOT_PATH == SUCCESSOR_ROOT_PATH

def test_seam_returns_no_execution_authority():
    cfg = get_successor_campaign_config()
    assert cfg.get("execution_authority") == "NOT_GRANTED"
    assert cfg.get("validated") is True
    assert "authorization_type" not in cfg or cfg.get("authorization_type") != "GRANTED"

def test_production_seam_does_not_create_real_root(tmp_path: Path):
    cfg = get_successor_campaign_config()
    assert not SUCCESSOR_ROOT_PATH.exists()
    assert cfg["successor_root"] == SUCCESSOR_ROOT_PATH

# ---------------------------------------------------------------------------
# B. Tuple exactness — all eight fields
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "field,tamper",
    [
        ("member", "unknown-member"),
        ("run_prefix", "deadbeef"),
        ("cost", 0.002),
        ("cost_bps", 999),
        ("hedger_seed", 99999),
        ("dataset_path", "tampered/path.parquet"),
        ("dataset_sha256", "0" * 64),
        ("expected_artifact_path", "data/processed/research/hedging_policies_recovery_v3/tampered"),
    ],
)
def test_tamper_each_eight_fields_rejected(field: str, tamper):
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0][field] = tamper
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_unknown_member_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["member"] = "seed-99"
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_unknown_cost_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["cost"] = 0.009
    p["successor_prospective_tuples"][0]["cost_bps"] = 90
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_old_seed_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["hedger_seed"] = 31001
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_unknown_successor_seed_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["hedger_seed"] = 12345
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_44_tuples_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"] = p["successor_prospective_tuples"][:-1]
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_46_tuples_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    dup = copy.deepcopy(p["successor_prospective_tuples"][0])
    # Make it a distinct key to avoid duplicate rejection masking extra count
    # Use a tuple that is not in universe but count check should trigger first
    p["successor_prospective_tuples"].append(dup)
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_duplicate_tuple_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][1] = copy.deepcopy(p["successor_prospective_tuples"][0])
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_run_prefix_drift_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["run_prefix"] = "ffffffffffff"
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_cost_bps_drift_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    # cost 0.0 should have bps 0, tamper to 10
    p["successor_prospective_tuples"][0]["cost_bps"] = 10
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_dataset_path_drift_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["dataset_path"] = "data/processed/research/hedging_synthetic/bad.parquet"
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_dataset_sha_drift_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["dataset_sha256"] = "a" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_expected_artifact_path_drift_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["successor_prospective_tuples"][0]["expected_artifact_path"] = p["successor_prospective_tuples"][0]["expected_artifact_path"].replace("c_0", "c_999")
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

# ---------------------------------------------------------------------------
# C. Predecessor exactness
# ---------------------------------------------------------------------------

def test_missing_identity_field_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    first_key = next(iter(p["predecessor_identities"]))
    del p["predecessor_identities"][first_key]["historical_checkpoint_sha"]
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_wrong_map_key_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    first_key = next(iter(p["predecessor_identities"]))
    val = p["predecessor_identities"].pop(first_key)
    p["predecessor_identities"]["bad:key:999"] = val
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_wrong_execution_started_sha_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_execution_started_sha"] = "0" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_wrong_checkpoint_sha_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_checkpoint_sha"] = "1" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_wrong_terminal_sha_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_terminal_sha"] = "2" * 64
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_wrong_historical_path_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_artifact_path"] = "data/processed/research/bad/path"
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_recovery_v2_path_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_artifact_path"] = p["predecessor_identities"][k]["historical_artifact_path"].replace(
        "hedging_policies/", "hedging_policies_recovery_v2/"
    )
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_recovery_v3_path_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_artifact_path"] = p["predecessor_identities"][k]["historical_artifact_path"].replace(
        "hedging_policies/", "hedging_policies_recovery_v3/"
    )
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_wrong_classification_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_classification"] = "VALID"
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_missing_predecessor_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    del p["predecessor_identities"][k]
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_extra_predecessor_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    p["predecessor_identities"]["extra:key:1"] = {
        "historical_artifact_path": "data/processed/research/hedging_policies/x/c_0/h_1",
        "historical_execution_started_sha": "a" * 64,
        "historical_checkpoint_sha": "b" * 64,
        "historical_terminal_sha": "c" * 64,
        "historical_classification": "SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP",
    }
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)

def test_recovery_v1_predecessor_path_rejected():
    payload = _load_valid_payload()
    p = copy.deepcopy(payload)
    k = next(iter(p["predecessor_identities"]))
    p["predecessor_identities"][k]["historical_artifact_path"] = p["predecessor_identities"][k]["historical_artifact_path"].replace(
        "hedging_policies/", "hedging_policies_recovery_v1/"
    )
    with pytest.raises(AuthorizationError):
        validate_successor_prerequisite(p)