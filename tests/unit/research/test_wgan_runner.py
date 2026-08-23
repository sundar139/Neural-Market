"""Focused fail-closed readiness tests for the future WGAN runner."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from neuralmarket.research import wgan_runner


def _identity() -> dict[str, object]:
    return {
        "runner_git_blob": "runner-blob",
        "implementation_source_git_blobs": {"model": "model-blob", "comparator": "comparator-blob"},
        "execution_contract_git_blob": "contract-blob",
        "effective_config_sha256": "config-sha",
        "effective_config_git_blob": "config-blob",
        "preregistration_sha256": wgan_runner.PREREGISTRATION_SHA256,
        "amendment_060_sha256": wgan_runner.AMENDMENT_060_SHA256,
        "runtime_identity_sha256": "runtime-sha",
    }


def _payload() -> dict[str, object]:
    return {
        "schema_version": "structured-vol-v5-wgan-authorization-v1",
        "member_id": "wgan-seed-01",
        "replicate_seed": 8281,
        "model_init_seed": 8281,
        "data_seed": 8282,
        "eval_seed": 8283,
        "effective_config_sha256": "config-sha",
        "effective_config_git_blob": "config-blob",
        "comparator_methodology_sha256": wgan_runner.PREREGISTRATION_SHA256,
        "amendment_060_sha256": wgan_runner.AMENDMENT_060_SHA256,
        "seed_schedule_sha256": wgan_runner.SEED_SCHEDULE_SHA256,
        "seed_schedule_git_blob": wgan_runner.SEED_SCHEDULE_BLOB,
        "execution_contract_git_blob": "contract-blob",
        "runner_git_blob": "runner-blob",
        "implementation_source_git_blobs": {"model": "model-blob", "comparator": "comparator-blob"},
        "execution_recipe_head": "0" * 40,
        "requested_device": "cuda",
        "expected_resolved_device": "cuda",
        "expected_runtime_identity_sha256": "runtime-sha",
        "max_scientific_invocations": 1,
        "training_authorized": True,
        "validation_authorized": False,
        "final_test_authorized": False,
    }


AUTHORIZATION_RELATIVE_PATH = Path(
    "reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _new_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "authorization-repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "Task 118 Tests")
    _git(repo, "config", "user.email", "task-118-tests@example.invalid")
    return repo


def _write_authorization(path: Path) -> None:
    path.write_text(json.dumps({"member_id": "wgan-seed-01"}) + "\n", encoding="utf-8")


def test_load_authorization_accepts_repository_relative_path() -> None:
    payload = wgan_runner._load_authorization(
        wgan_runner._normalize_authorization_path(AUTHORIZATION_RELATIVE_PATH)
    )
    assert payload["member_id"] == "wgan-seed-01"


def test_load_authorization_accepts_repository_absolute_path() -> None:
    payload = wgan_runner._load_authorization(
        wgan_runner._normalize_authorization_path(
            (wgan_runner.REPO / AUTHORIZATION_RELATIVE_PATH).resolve()
        )
    )
    assert payload["member_id"] == "wgan-seed-01"


def test_load_authorization_rejects_absolute_path_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="inside the repository"):
        wgan_runner._normalize_authorization_path(tmp_path / "outside.json")


def test_load_authorization_rejects_relative_traversal() -> None:
    with pytest.raises(RuntimeError, match="inside the repository"):
        wgan_runner._normalize_authorization_path(Path("..") / "outside.json")


def test_load_authorization_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    _write_authorization(outside)
    link = wgan_runner.REPO / ".agent-memory/task-118-authorization-link.json"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable in this environment: {exc}")
    try:
        with pytest.raises(RuntimeError, match="inside the repository"):
            wgan_runner._normalize_authorization_path(
                Path(".agent-memory/task-118-authorization-link.json")
            )
    finally:
        link.unlink(missing_ok=True)


def test_load_authorization_rejects_untracked_in_repository_artifact() -> None:
    relative = Path(".agent-memory/task-118-untracked-authorization.json")
    path = wgan_runner.REPO / relative
    _write_authorization(path)
    try:
        with pytest.raises(RuntimeError, match="tracked"):
            wgan_runner._load_authorization(
                wgan_runner._normalize_authorization_path(relative)
            )
    finally:
        path.unlink(missing_ok=True)


def test_load_authorization_rejects_tracked_but_uncommitted_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _new_git_repo(tmp_path)
    authorization = repo / "authorization.json"
    _write_authorization(authorization)
    _git(repo, "add", "authorization.json")
    monkeypatch.setattr(wgan_runner, "REPO", repo)
    with pytest.raises(RuntimeError, match="committed"):
        wgan_runner._load_authorization(
            wgan_runner._normalize_authorization_path(Path("authorization.json"))
        )


def test_load_authorization_rejects_dirty_tracked_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _new_git_repo(tmp_path)
    authorization = repo / "authorization.json"
    _write_authorization(authorization)
    _git(repo, "add", "authorization.json")
    _git(repo, "commit", "--quiet", "-m", "freeze authorization")
    authorization.write_text(json.dumps({"member_id": "mutated"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(wgan_runner, "REPO", repo)
    with pytest.raises(RuntimeError, match="clean and equal to HEAD"):
        wgan_runner._load_authorization(
            wgan_runner._normalize_authorization_path(Path("authorization.json"))
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows case-variant behavior")
def test_load_authorization_accepts_windows_case_variant() -> None:
    case_variant = Path(str((wgan_runner.REPO / AUTHORIZATION_RELATIVE_PATH).resolve()).upper())
    payload = wgan_runner._load_authorization(
        wgan_runner._normalize_authorization_path(case_variant)
    )
    assert payload["member_id"] == "wgan-seed-01"


def test_contract_binds_frozen_methodology_and_defers_implementation_blob() -> None:
    contract = json.loads(wgan_runner.EXECUTION_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["methodology"]["preregistration_sha256"] == wgan_runner.PREREGISTRATION_SHA256
    assert contract["methodology"]["amendment_060_sha256"] == wgan_runner.AMENDMENT_060_SHA256
    assert contract["implementation_binding"]["status"] == "DEFERRED_TO_LATER_AUTHORIZATION"
    assert "implementation_source_git_blobs" not in contract["implementation_binding"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("runner_git_blob", "wrong", "runner"),
        (
            "implementation_source_git_blobs",
            {"model": "wrong", "comparator": "comparator-blob"},
            "implementation",
        ),
        ("comparator_methodology_sha256", "wrong", "methodology"),
        ("amendment_060_sha256", "wrong", "Amendment-060"),
    ],
)
def test_wrong_identity_fails_closed(field: str, value: object, message: str) -> None:
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError, match=message):
        wgan_runner.validate_authorization_payload(payload, expected_identity=_identity())


def test_valid_identity_payload_and_authorization_flags() -> None:
    wgan_runner.validate_authorization_payload(_payload(), expected_identity=_identity())


def test_missing_authorization_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="authorization"):
        wgan_runner.require_authorization(None)


def test_cpu_scientific_execution_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="CUDA"):
        wgan_runner.require_scientific_cuda("cpu")


def test_dry_run_never_trains_or_creates_scientific_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wgan_runner, "WGAN_RUN_ROOT", tmp_path / "wgan-runs")
    monkeypatch.setattr(
        wgan_runner,
        "execute_authorized_wgan",
        lambda *args, **kwargs: pytest.fail("dry-run trained"),
    )
    assert wgan_runner.main(["--member-id", "wgan-seed-01"]) == 0
    assert not list(tmp_path.rglob("execution_started.json"))
    assert not list(tmp_path.rglob("*.pt"))


def _patch_execute_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, object]:
    auth_path = wgan_runner.REPO / AUTHORIZATION_RELATIVE_PATH
    auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(wgan_runner, "WGAN_RUN_ROOT", tmp_path / "wgan-runs")
    monkeypatch.setattr(
        wgan_runner,
        "resolve_device",
        lambda requested: SimpleNamespace(type="cuda"),
    )
    monkeypatch.setattr(wgan_runner, "configure_device_determinism", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        wgan_runner,
        "build_runtime_identity",
        lambda **kwargs: {
            "runtime_identity_sha256": auth_data["expected_runtime_identity_sha256"]
        },
    )
    def current_identity(*, runtime_sha: str) -> dict[str, object]:
        return {
            "runner_git_blob": auth_data["runner_git_blob"],
            "implementation_source_git_blobs": auth_data["implementation_source_git_blobs"],
            "execution_contract_git_blob": auth_data["execution_contract_git_blob"],
            "effective_config_sha256": auth_data["effective_config_sha256"],
            "effective_config_git_blob": auth_data["effective_config_git_blob"],
            "preregistration_sha256": wgan_runner.PREREGISTRATION_SHA256,
            "amendment_060_sha256": wgan_runner.AMENDMENT_060_SHA256,
            "runtime_identity_sha256": runtime_sha,
        }

    monkeypatch.setattr(wgan_runner, "_current_identity", current_identity)
    return auth_data


@pytest.mark.parametrize(
    "authorization_path",
    [
        AUTHORIZATION_RELATIVE_PATH,
        (wgan_runner.REPO / AUTHORIZATION_RELATIVE_PATH).resolve(),
    ],
    ids=["relative", "absolute"],
)
def test_execute_reaches_marker_boundary_with_canonical_authorization_path(
    authorization_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth_data = _patch_execute_boundary(monkeypatch, tmp_path)
    captured_payloads: list[dict[str, object]] = []
    executed: list[object] = []

    def capture_link(source: Path, destination: Path) -> None:
        captured_payloads.append(json.loads(source.read_text(encoding="utf-8")))
        raise RuntimeError("controlled marker filesystem boundary")

    monkeypatch.setattr(wgan_runner.os, "link", capture_link)
    monkeypatch.setattr(
        wgan_runner,
        "execute_authorized_wgan",
        lambda *args, **kwargs: executed.append((args, kwargs)) or {},
    )

    assert (
        wgan_runner.main(
            [
                "--member-id",
                "wgan-seed-01",
                "--authorization",
                str(authorization_path),
                "--execute",
            ]
        )
        == 2
    )
    assert len(captured_payloads) == 1
    payload = captured_payloads[0]
    assert payload["member_id"] == auth_data["member_id"]
    assert payload["authorization_path"] == AUTHORIZATION_RELATIVE_PATH.as_posix()
    assert payload["authorization_git_blob"] == wgan_runner._git_blob(
        (wgan_runner.REPO / AUTHORIZATION_RELATIVE_PATH).resolve()
    )
    assert payload["implementation_identity"]
    assert not executed
    assert not list(tmp_path.rglob("execution_started.json"))


def test_payload_refusal_before_marker_creation_leaves_no_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_execute_boundary(monkeypatch, tmp_path)
    auth_path = (wgan_runner.REPO / AUTHORIZATION_RELATIVE_PATH).resolve()
    real_git_blob = wgan_runner._git_blob
    authorization_blob_calls = 0
    executed: list[object] = []

    def fail_on_marker_payload(path: Path) -> str:
        nonlocal authorization_blob_calls
        if path.resolve() == auth_path:
            authorization_blob_calls += 1
            if authorization_blob_calls == 2:
                raise RuntimeError("controlled payload preparation failure")
        return real_git_blob(path)

    monkeypatch.setattr(wgan_runner, "_git_blob", fail_on_marker_payload)
    monkeypatch.setattr(
        wgan_runner,
        "execute_authorized_wgan",
        lambda *args, **kwargs: executed.append((args, kwargs)) or {},
    )

    assert (
        wgan_runner.main(
            [
                "--member-id",
                "wgan-seed-01",
                "--authorization",
                AUTHORIZATION_RELATIVE_PATH.as_posix(),
                "--execute",
            ]
        )
        == 2
    )
    assert authorization_blob_calls == 2
    assert not executed
    assert not (tmp_path / "wgan-runs").exists()
    assert not list(tmp_path.rglob("execution_started.json"))


def test_primary_and_reserve_rosters_are_fixed_without_automatic_chain() -> None:
    assert tuple(f"wgan-seed-0{i}" for i in range(1, 6)) == wgan_runner.PRIMARY_MEMBER_IDS
    assert wgan_runner.RESERVE_MEMBER_IDS == (
        "reserve-wgan-j01",
        "reserve-wgan-j02",
        "reserve-wgan-j03",
    )
    assert wgan_runner.AUTO_RESERVE_CHAIN is False
