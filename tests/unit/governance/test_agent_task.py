"""Tests for the repository governance task helper (tools/agent_task.py)."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
import tools.agent_task as agent_task


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def gov_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway git repository with one committed tracked file."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "gov@test")
    _git(tmp_path, "config", "user.name", "gov")
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "seed")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _start(**overrides: object) -> argparse.Namespace:
    opts = argparse.Namespace(
        id="T-1",
        objective="exercise the task helper",
        risk="R1",
        stop_condition=[],
        invariant=[],
        expected_file=[],
        allow_dirty=False,
    )
    opts.__dict__.update(overrides)
    return opts


def _state(repo: Path) -> dict:
    path = repo / ".agent-memory" / "state.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_init_creates_state_and_ignores_memory(gov_repo: Path) -> None:
    agent_task.cmd_init(argparse.Namespace())
    state = _state(gov_repo)
    assert state["current_gate"] == "READY"
    assert state["current_task"] is None
    assert ".agent-memory/" in (gov_repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    agent_task.cmd_init(argparse.Namespace())  # idempotent, no error on second run


def test_start_refuses_dirty_tracked_tree(gov_repo: Path) -> None:
    (gov_repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="Refusing to start"):
        agent_task.cmd_start(_start())
    # recovery path: an explicit allow-dirty proceeds and records state
    agent_task.cmd_start(_start(allow_dirty=True))
    assert _state(gov_repo)["current_task"] == "T-1"
    assert _state(gov_repo)["current_gate"] == "DISCOVER"


def test_invalid_risk_and_outcome_rejected(gov_repo: Path) -> None:
    with pytest.raises(SystemExit, match="risk must be one of"):
        agent_task.cmd_start(_start(risk="R9"))
    with pytest.raises(SystemExit, match="outcome must be one of"):
        agent_task.cmd_finish(
            argparse.Namespace(outcome="MADE_UP", summary="s", id=None, next_action=None)
        )


def test_full_lifecycle(gov_repo: Path) -> None:
    agent_task.cmd_start(_start(id="LIFE-1", risk="R0"))
    agent_task.cmd_gate(argparse.Namespace(name="decide"))
    agent_task.cmd_status(argparse.Namespace())
    agent_task.cmd_gate(argparse.Namespace(name="verify"))
    agent_task.cmd_finish(
        argparse.Namespace(outcome="IMPLEMENTED", summary="done", id=None, next_action="NONE")
    )
    state = _state(gov_repo)
    assert state["current_task"] is None
    assert state["current_gate"] == "READY"
    assert state["next_action"] == "NONE"
    task_path = gov_repo / ".agent-memory" / "tasks" / "LIFE-1.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    assert task["outcome"] == "IMPLEMENTED"
    assert task["final"]["tracked_status"] == ""
    assert (gov_repo / ".agent-memory" / "evidence" / "LIFE-1.md").exists()
