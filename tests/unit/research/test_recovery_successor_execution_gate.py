"""Adversarial tests for successor execution gate — Task 278/280 hardened."""
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
    _gate_successor_execution_with_root,
    _check_successor_campaign_state_with_root,
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
        "successor_final_prerequisite_path": "reports/protocol/hedging_recovery_successor_final_execution_authorization_prerequisites_286.json",
        "successor_final_prerequisite_commit": "5b8e6d03de6c88f56dadc5a4e9609870946926e4",
        "successor_final_prerequisite_canonical": "08d148fbce45848d16533b072d4baba47dd1347563580a77561d2bb61310a249",
        "successor_final_prerequisite_raw": "f5fba315c62d9c287c17fb5cb121613553957500d16bdea68c83b949c76638c7",
        "successor_final_prerequisite_blob": "a743c1d98c50ca37e6c7fa343c7867dabccdc444",
        "successor_final_prerequisite_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-FINAL-AUTHORIZATION-PREREQUISITE-FREEZE-286",
        "successor_final_prerequisite_artifact_type": "GRU_TRAINING_RECOVERY_SUCCESSOR_FINAL_EXECUTION_AUTHORIZATION_PREREQUISITES_V1",
    }


def _write_auth(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "synthetic_successor_auth.json"
    p.write_text(json.dumps(payload))
    return p


def _mock_verify_ok():
    return {"canonical_sha256": "abc", "git_blob": "blob123", "commit": "commit123", "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-EXECUTION-AUTHORIZATION-278", "path": "tmp"}


def test_correct_synthetic_reaches_mocked_boundary(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    member = first["member"]
    cost = first["cost"]
    seed = first["hedger_seed"]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
            mock_train.return_value = {"ok": "mocked"}
            ctx = _gate_successor_execution_with_root(authorization_path=auth_path, member=member, cost=cost, hedger_seed=seed, policy_root=tmp_path)
            assert ctx["ordinal"] == 0
            assert ctx["expected_artifact_path"].as_posix().startswith(tmp_path.as_posix() + "/") or ctx["expected_artifact_path"].as_posix().startswith("data/processed/research/hedging_policies_recovery_v3/")
            # trainer private helper with same root
            from neuralmarket.research.deep_hedging.trainer import _train_one_policy_successor_with_root

            with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train2:
                mock_train2.return_value = {"trained": "yes"}
                result = _train_one_policy_successor_with_root(member=member, cost=cost, hedger_seed=seed, authorization_path=auth_path, policy_root=tmp_path)
                assert mock_train2.called


def test_invalid_auth_never_reaches_model(tmp_path: Path):
    payload = _valid_payload()
    payload["authorization_type"] = "GRU_TRAINING_RECOVERY_V1"  # wrong
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
            with pytest.raises(AuthorizationError):
                _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
            assert not mock_train.called


def test_task276_prerequisite_never_reaches_execution(tmp_path: Path):
    prereq_path = Path("reports/protocol/hedging_recovery_successor_execution_authorization_prerequisites_276.json")
    first_payload = _valid_payload()
    first = first_payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as mock_train:
        with pytest.raises(AuthorizationError):
            gate_successor_execution(authorization_path=prereq_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"])
        assert not mock_train.called


def test_ordinal1_can_reach_once(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    first = ordered[0]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp0 = RUN_PREFIXES[first["member"]]
    dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir0.mkdir(parents=True, exist_ok=True)
    (dir0 / "execution_started.json").write_text("{}")
    (dir0 / "terminal_manifest.json").write_text("{}")
    second = ordered[1]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        ctx = _gate_successor_execution_with_root(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)
        assert ctx["ordinal"] == 1


def test_same_tuple_cannot_reach_twice(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    member, cost, seed = first["member"], first["cost"], first["hedger_seed"]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        _gate_successor_execution_with_root(authorization_path=auth_path, member=member, cost=cost, hedger_seed=seed, policy_root=tmp_path)
        from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

        rp = RUN_PREFIXES[member]
        dir_path = tmp_path / f"{rp}_{member}/c_{first['cost_bps']}/h_{seed}"
        dir_path.mkdir(parents=True, exist_ok=True)
        (dir_path / "execution_started.json").write_text("{}")
        with pytest.raises(AuthorizationError, match="already consumed"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=member, cost=cost, hedger_seed=seed, policy_root=tmp_path)


def test_later_ordinal_blocked_after_failure(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    first = ordered[0]
    second = ordered[1]
    third = ordered[2]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp0 = RUN_PREFIXES[first["member"]]
    dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir0.mkdir(parents=True, exist_ok=True)
    (dir0 / "execution_started.json").write_text("{}")
    (dir0 / "execution_failed.json").write_text("{}")
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="campaign stopped"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)
        with pytest.raises(AuthorizationError, match="campaign stopped"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=third["member"], cost=third["cost"], hedger_seed=third["hedger_seed"], policy_root=tmp_path)


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
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="campaign stopped|nonterminal|not yet completed"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)


def test_wrong_ordinal_blocked(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member="seed-01", cost=0.0, hedger_seed=99999, policy_root=tmp_path)


def test_artifact_collision_blocked(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp = RUN_PREFIXES[first["member"]]
    dir_path = tmp_path / f"{rp}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "checkpoint.pt").write_text("fake")
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="already consumed|collision"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_v2_path_blocked(tmp_path: Path):
    payload = _valid_payload()
    payload["successor_tuples"][0]["expected_artifact_path"] = payload["successor_tuples"][0]["expected_artifact_path"].replace("hedging_policies_recovery_v3", "hedging_policies_recovery_v2")
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_successor_tuples_must_be_list(tmp_path: Path):
    payload = _valid_payload()
    payload["successor_tuples"] = 45
    auth_path = _write_auth(tmp_path, payload)
    first = _valid_payload()["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
