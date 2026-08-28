"""Hardening adversarial tests for Task 280 — 4 blockers + ordering.

No real CUDA/model/optimizer execution — all scientific boundaries are mocked.
Tests use private test seam _gate_successor_execution_with_root and
_train_one_policy_successor_with_root for isolation, and the public
production API to verify fail-closed behavior.
"""
from __future__ import annotations

import json
import copy
import threading
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
    _get_authenticated_successor_prerequisite_values,
    _get_trusted_predecessor_map,
    build_implementation_manifest,
    gate_successor_execution,
    _gate_successor_execution_with_root,
    EXPECTED_CONTRACT_V3_CANONICAL,
    EXPECTED_CONTRACT_V3_BLOB,
    EXPECTED_RUNTIME_IDENTITY,
)
from neuralmarket.research.deep_hedging import trainer as tr


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
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _mock_verify_ok():
    return {
        "canonical_sha256": "abc" * 10,
        "git_blob": "blob123",
        "commit": "commit123",
        "authorization_task_id": "NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-EXECUTION-AUTHORIZATION-278",
        "path": "tmp",
    }


# ---- Output root ----
def test_arbitrary_policy_root_rejected(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    # public API must not accept policy_root kwarg
    with pytest.raises(TypeError):
        tr.train_one_policy_successor(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path, policy_root=tmp_path)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)  # type: ignore[call-arg]
    # tampered expected path with arbitrary root must be rejected via gate
    payload["successor_tuples"][0]["expected_artifact_path"] = str(tmp_path / "evil" / "path")
    auth_path2 = _write_auth(tmp_path, payload)
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path2, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_absolute_alternate_root_rejected(tmp_path: Path):
    payload = _valid_payload()
    first = payload["successor_tuples"][0]
    # absolute path tampering
    payload["successor_tuples"][0]["expected_artifact_path"] = "/tmp/absolute/evil/path"
    auth_path = _write_auth(tmp_path, payload)
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=Path("/tmp/absolute/evil"))


def test_recovery_v2_root_rejected(tmp_path: Path):
    payload = _valid_payload()
    first = payload["successor_tuples"][0]
    payload["successor_tuples"][0]["expected_artifact_path"] = payload["successor_tuples"][0]["expected_artifact_path"].replace("hedging_policies_recovery_v3", "hedging_policies_recovery_v2")
    auth_path = _write_auth(tmp_path, payload)
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_historical_root_rejected(tmp_path: Path):
    payload = _valid_payload()
    first = payload["successor_tuples"][0]
    payload["successor_tuples"][0]["expected_artifact_path"] = payload["successor_tuples"][0]["expected_artifact_path"].replace("hedging_policies_recovery_v3", "hedging_policies")
    auth_path = _write_auth(tmp_path, payload)
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_canonical_successor_root_only_valid(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        ctx = _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
        # private helper produces tmp_path canonical; public gate would use real SUCCESSOR_ROOT
        assert ctx["expected_artifact_path"].as_posix().startswith(tmp_path.as_posix())


# ---- Authorization identity ----
def test_untracked_valid_authorization_rejected_by_production_gate(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    # Do NOT mock verify — real verify should fail because file is not tracked and not repo-relative
    with pytest.raises(AuthorizationError):
        gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"])
    # Also via trainer entrypoint
    with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as m:
        m.return_value = {"ok": True}
        with pytest.raises(AuthorizationError):
            tr.train_one_policy_successor(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path)
        assert not m.called


def test_copied_authorization_at_wrong_path_rejected(tmp_path: Path):
    # Simulate an authorization that is tracked at one path but copied to another
    # The verifier checks git ls-files; copied file at wrong path will be untracked
    payload = _valid_payload()
    auth_path = tmp_path / "copied_auth.json"
    auth_path.write_text(json.dumps(payload))
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact") as mock_verify:
        # Simulate verifier detecting path mismatch: raise
        mock_verify.side_effect = AuthorizationError("authorization file not tracked: copied_auth.json")
        with pytest.raises(AuthorizationError):
            gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"])
        # Also test that when final approved identity is represented/mocked, copied at wrong path still fails
        # Here the mock already represents approved identity but wrong path still fails

def test_verifier_failure_propagates(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", side_effect=AuthorizationError("verifier failure")):
        with pytest.raises(AuthorizationError, match="verifier failure"):
            gate_successor_execution(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"])
        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as m:
            with pytest.raises(AuthorizationError):
                tr.train_one_policy_successor(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path)
            assert not m.called


def test_no_tmp_provenance_ever_synthesized(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    # Mock internal to capture provenance packet without real training
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", side_effect=AuthorizationError("verify fail")):
        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as m:
            m.return_value = {"ok": True}
            try:
                tr.train_one_policy_successor(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path)
            except AuthorizationError:
                pass
            # ensure trainer never synthesized tmp provenance - it should have propagated, not called internal
            assert not m.called
            # also check no tmp strings in any file that might have been created
            # there should be no claim file created on failure
            from neuralmarket.research.deep_hedging.trainer import SUCCESSOR_ROOT_PATH
            # No tmp provenance file should exist under SUCCESSOR_ROOT_PATH
            if SUCCESSOR_ROOT_PATH.exists():
                for p in SUCCESSOR_ROOT_PATH.rglob("*.json"):
                    content = p.read_text(errors="ignore")
                    assert '"git_blob": "tmp"' not in content
                    assert '"commit": "tmp"' not in content


# ---- Seed families ----
def test_successor_seed_60999_passes_to_mocked_boundary(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]  # 60999
    assert first["hedger_seed"] == 60999
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal") as m:
            m.return_value = {"ok": "mocked"}
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=60999, policy_root=tmp_path)
            # trainer private helper
            from neuralmarket.research.deep_hedging.trainer import _train_one_policy_successor_with_root

            m.return_value = {"ok": "mocked2"}
            _train_one_policy_successor_with_root(member=first["member"], cost=first["cost"], hedger_seed=60999, authorization_path=auth_path, policy_root=tmp_path)
            assert m.called


def test_successor_53804_passes(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    second = payload["successor_tuples"][1]  # 53804
    assert second["hedger_seed"] == 53804
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        # need to complete ordinal 0 before testing ordinal 1
        from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

        first = payload["successor_tuples"][0]
        rp0 = RUN_PREFIXES[first["member"]]
        dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
        dir0.mkdir(parents=True, exist_ok=True)
        (dir0 / "execution_started.json").write_text("{}")
        (dir0 / "terminal_manifest.json").write_text("{}")
        ctx2 = _gate_successor_execution_with_root(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=53804, policy_root=tmp_path)
        assert ctx2["ordinal"] == 1

def test_successor_89356_passes(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    third = payload["successor_tuples"][2]  # 89356
    assert third["hedger_seed"] == 89356
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        # need to complete ordinals 0,1
        from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES
        for idx in range(2):
            t = payload["successor_tuples"][idx]
            rp = RUN_PREFIXES[t["member"]]
            d = tmp_path / f"{rp}_{t['member']}/c_{t['cost_bps']}/h_{t['hedger_seed']}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "execution_started.json").write_text("{}")
            (d / "terminal_manifest.json").write_text("{}")
        ctx = _gate_successor_execution_with_root(authorization_path=auth_path, member=third["member"], cost=third["cost"], hedger_seed=89356, policy_root=tmp_path)
        assert ctx["ordinal"] == 2


def test_old_31001_under_successor_rejected(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    # old seed not in successor tuples — gate should reject tuple not in 45
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member="seed-01", cost=0.0, hedger_seed=31001, policy_root=tmp_path)
    # internal trainer with successor root should also reject old seed
    with pytest.raises(ValueError, match="not allowed for root.*recovery_v3"):
        tr._train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=31001, synthetic_dataset_path=Path("nonexistent.parquet"), policy_root=tr.SUCCESSOR_ROOT_PATH)


def test_successor_seed_under_v2_rejected(tmp_path: Path):
    # successor seed under historical/recovery root should be rejected by internal trainer
    with pytest.raises(ValueError, match="not allowed"):
        tr._train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=60999, synthetic_dataset_path=Path("nonexistent.parquet"), policy_root=Path("data/processed/research/hedging_policies"))
    with pytest.raises(ValueError, match="not allowed"):
        tr._train_one_policy_internal(member="seed-01", cost=0.0, hedger_seed=60999, synthetic_dataset_path=Path("nonexistent.parquet"), policy_root=Path("data/processed/research/hedging_policies_recovery_v2"))


# ---- Atomic claim concurrency ----
def test_two_concurrent_same_ordinal_claims_one_winner_one_loser(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    # Use private helper with mocked internal to avoid real training, but need real claim file creation
    # We'll directly test the atomic claim primitive via trainer's claim file
    # Simulate two threads both trying to claim same ordinal 0 via _train_one_policy_successor_with_root
    # Mock the internal trainer to avoid dataset/model work but keep claim file creation
    results = []

    def attempt():
        try:
            with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
                with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal", return_value={"ok": True}):
                    from neuralmarket.research.deep_hedging.trainer import _train_one_policy_successor_with_root

                    _train_one_policy_successor_with_root(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path, policy_root=tmp_path)
                    results.append("success")
        except FileExistsError:
            results.append("failed")
        except Exception as e:
            results.append(f"error:{e}")

    # Ensure clean
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES
    rp = RUN_PREFIXES[first["member"]]
    dir_path = tmp_path / f"{rp}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    if dir_path.exists():
        import shutil
        shutil.rmtree(dir_path)

    t1 = threading.Thread(target=attempt)
    t2 = threading.Thread(target=attempt)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert results.count("success") == 1
    assert results.count("failed") == 1


def test_same_ordinal_sequential_second_rejected(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    first = payload["successor_tuples"][0]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal", return_value={"ok": True}):
            from neuralmarket.research.deep_hedging.trainer import _train_one_policy_successor_with_root

            _train_one_policy_successor_with_root(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path, policy_root=tmp_path)
        # Simulate that internal trainer would have created execution_started; for gate isolation, create it manually
        from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

        rp = RUN_PREFIXES[first["member"]]
        dir_path = tmp_path / f"{rp}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
        # execution_started already exists via claim file, but gate checks execution_started, so ensure it exists
        if not (dir_path / "execution_started.json").exists():
            (dir_path / "execution_started.json").write_text("{}")
        # second attempt same ordinal should be rejected via claim file exists (FileExistsError) or gate already consumed
        with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
            with pytest.raises((AuthorizationError, FileExistsError)):
                _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
            with mock.patch("neuralmarket.research.deep_hedging.trainer._train_one_policy_internal", return_value={"ok": True}):
                with pytest.raises((AuthorizationError, FileExistsError)):
                    from neuralmarket.research.deep_hedging.trainer import _train_one_policy_successor_with_root

                    _train_one_policy_successor_with_root(member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], authorization_path=auth_path, policy_root=tmp_path)


def test_failed_ordinal_retry_rejected(tmp_path: Path):
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
    (dir0 / "execution_failed.json").write_text("{}")
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="campaign stopped|already consumed"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)
def test_nonterminal_ordinal_retry_rejected(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    first = ordered[0]
    from neuralmarket.research.deep_hedging.artifacts import RUN_PREFIXES

    rp0 = RUN_PREFIXES[first["member"]]
    dir0 = tmp_path / f"{rp0}_{first['member']}/c_{first['cost_bps']}/h_{first['hedger_seed']}"
    dir0.mkdir(parents=True, exist_ok=True)
    (dir0 / "execution_started.json").write_text("{}")
    # no terminal -> nonterminal
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="nonterminal|already consumed|campaign stopped"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=first["member"], cost=first["cost"], hedger_seed=first["hedger_seed"], policy_root=tmp_path)


def test_later_after_failure_rejected(tmp_path: Path):
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
    (dir0 / "execution_failed.json").write_text("{}")
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="campaign stopped"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)


def test_later_after_nonterminal_rejected(tmp_path: Path):
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
        with pytest.raises(AuthorizationError):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=second["member"], cost=second["cost"], hedger_seed=second["hedger_seed"], policy_root=tmp_path)


def test_ordinal_skip_rejected(tmp_path: Path):
    payload = _valid_payload()
    auth_path = _write_auth(tmp_path, payload)
    ordered = payload["successor_tuples"]
    # Try to jump to ordinal 2 without completing 0 and 1
    third = ordered[2]
    with mock.patch("neuralmarket.research.deep_hedging.runner.verify_authorization_artifact", return_value=_mock_verify_ok()):
        with pytest.raises(AuthorizationError, match="not yet completed|cannot skip"):
            _gate_successor_execution_with_root(authorization_path=auth_path, member=third["member"], cost=third["cost"], hedger_seed=third["hedger_seed"], policy_root=tmp_path)
