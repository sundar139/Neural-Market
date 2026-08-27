"""Adversarial tests for successor execution gate — Task 278."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest import mock

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
    gate_successor_execution,
    validate_successor_authorization_schema,
    EXPECTED_CONTRACT_V3_CANONICAL,
    EXPECTED_CONTRACT_V3_BLOB,
    EXPECTED_RUNTIME_IDENTITY,
)


def _valid_payload():
    auth = _get_authenticated_successor_prerequisite_values()
    trusted = _get_trusted_predecessor_map()
    manifest = build_implementation_manifest()
    prereq = json.loads(SUCCESSOR_PREREQUISITE_PATH.read_bytes().decode())
    return {
        "schema_version": "hedging-successor-authorization-v1",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-EXECUTION-AUTHORIZATION-278",
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
    }


def _write_auth(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "synthetic_successor_auth.json"
    p.write_text(json.dumps(payload))
    return p


def test_correct_synthetic_reaches_mocked_boundary(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    # First tuple in order
    first = payload["successor_tuples"][0]
    member = first["member"]
    cost = first["cost"]
    seed = first["hedger_seed"]
    # Mock trainer internal to prove gate reaches boundary without scientific execution
    with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
        mock_train.return_value = {"ok": "mocked"}
        ctx = gate_successor_execution(authorization_path=auth_path, member=member, cost=cost, hedger_seed=seed, policy_root=tmp_path)
        assert ctx["ordinal"] == 0
        assert ctx["expected_artifact_path"].as_posix().startswith("data/processed/research/hedging_policies_recovery_v3/")
        # Now test that actual trainer would be called (mocked)
        from neuralmarket.research.deep_hedging.trainer import train_one_policy_successor

        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train2:
            mock_train2.return_value = {"trained": "yes"}
            # trainer's train_one_policy_successor will synthesize verify info for tmp synthetic, no need to mock verify separately
            result = train_one_policy_successor(member=member, cost=cost, hedger_seed=seed, authorization_path=auth_path, policy_root=tmp_path)
            assert mock_train2.called


def test_invalid_auth_never_reaches_model(tmp_path: Path):
    payload = _valid_payload()
    payload["authorization_type"] = "GRU_TRAINING_RECOVERY_V1"  # wrong
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
        with pytest.raises(AuthorizationError):
            gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
        assert not mock_train.called
        # Also via trainer entrypoint
        from neuralmarket.research.deep_hedging.trainer import train_one_policy_successor

        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train2:
            with pytest.raises((AuthorizationError, RuntimeError)):
                train_one_policy_successor(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path, policy_root=tmp_path)
            assert not mock_train2.called


def test_task276_prerequisite_never_reaches_execution(tmp_path: Path):
    # Use the actual Task276 freeze artifact as authorization (should be rejected)
    prereq_path = Path("reports/protocol/hedging_recovery_successor_execution_authorization_prerequisites_276.json")
    first_payload = _valid_payload()
    first = first_payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
        with pytest.raises(AuthorizationError):
            gate_successor_execution(authorization_path=prereq_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
        assert not mock_train.called


def test_ordinal1_can_reach_once(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    # Complete ordinal 0 successfully (create terminal)
    first = ordered[0]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp0 = RUN_PREFIXES[first["member"]]
    dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir0.mkdir(parents=True, exist_ok=True)
    (dir0 / "execution_started.json").write_text("{}")
    (dir0 / "terminal_manifest.json").write_text("{}")
    # Now ordinal 1 should be reachable
    second = ordered[1]
    ctx = gate_successor_execution(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)
    assert ctx["ordinal"] == 1


def test_same_tuple_cannot_reach_twice(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    member, cost, seed = first["member"], first["cost"], first["hedger_seed"]
    # First invocation succeeds
    gate_successor_execution(authorization_path=auth_path, member=member, cost=cost, hedger_seed=seed, policy_root=tmp_path)
    # Simulate consumption by creating execution_started
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp = RUN_PREFIXES[member]
    dir_path = tmp_path / f"{rp}_{member}/c_{first['cost_bps']}/h_{seed}"
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "execution_started.json").write_text("{}")
    # Second invocation same tuple should fail (already consumed)
    with pytest.raises(AuthorizationError, match="already consumed"):
        gate_successor_execution(authorization_path=auth_path, member=member, cost=cost, hedger_seed=seed, policy_root=tmp_path)


def test_later_ordinal_blocked_after_failure(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    first = ordered[0]
    second = ordered[1]
    third = ordered[2]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    # Simulate ordinal 0 failed (execution_failed)
    rp0 = RUN_PREFIXES[first["member"]]
    dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir0.mkdir(parents=True, exist_ok=True)
    (dir0 / "execution_started.json").write_text("{}")
    (dir0 / "execution_failed.json").write_text("{}")
    # Later ordinal should be blocked due to campaign stop
    with pytest.raises(AuthorizationError, match="campaign stopped"):
        gate_successor_execution(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)
    with pytest.raises(AuthorizationError, match="campaign stopped"):
        gate_successor_execution(authorization_path=auth_path, member=third["member"], cost=third["cost"], hedger_seed=third["hedger_seed"], policy_root=tmp_path)


def test_later_ordinal_blocked_after_nonterminal(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    first = ordered[0]
    second = ordered[1]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp0 = RUN_PREFIXES[first["member"]]
    dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir0.mkdir(parents=True, exist_ok=True)
    (dir0 / "execution_started.json").write_text("{}")
    # No terminal -> nonterminal
    with pytest.raises(AuthorizationError, match="nonterminal"):
        gate_successor_execution(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)


def test_wrong_ordinal_blocked(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    # Try to execute ordinal 5 without completing 0-4
    ordered = payload["successor_tuples"]
    fifth = ordered[5]
    with pytest.raises(AuthorizationError, match="not yet completed|skip"):
        gate_successor_execution(authorization_path=auth_path, member=fifth["member"], cost=fifth["cost"], hedger_seed=fifth["hedger_seed"], policy_root=tmp_path)
    # Also try completely wrong tuple not in 45
    with pytest.raises(AuthorizationError):
        gate_successor_execution(authorization_path=auth_path, member="seed-01", cost=0.0, hedger_seed=99999, policy_root=tmp_path)


def test_artifact_collision_blocked(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp = RUN_PREFIXES[first["member"]]
    dir_path = tmp_path / f"{rp}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "checkpoint.pt").write_text("fake")
    with pytest.raises(AuthorizationError, match="already consumed|collision"):
        gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_v2_path_blocked(tmp_path: Path):
    payload = _valid_payload()
    # Tamper expected_artifact_path to v2 path — validator should already reject, but gate also blocks
    payload["successor_tuples"][0]["expected_artifact_path"] = payload["successor_tuples"][0]["expected_artifact_path"].replace("hedging_policies_recovery_v3", "hedging_policies_recovery_v2")
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with pytest.raises(AuthorizationError):
        gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_successor_tuples_must_be_list(tmp_path: Path):
    payload = _valid_payload()
    payload["successor_tuples"] = 45  # integer count, as in Task276 doc field
    auth_path = _write_auth(tmp_path, payload)
    first = _valid_payload()["successor_tuples"][0]  # get valid tuple for attempt
    with pytest.raises(AuthorizationError):
        gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
