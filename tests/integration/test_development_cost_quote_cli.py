"""Offline integration tests for ``data development quote-cost``."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app

pytestmark = pytest.mark.integration

runner = CliRunner()
_ROOT = Path(__file__).resolve().parents[2]
_EXECUTION_DIR = _ROOT / "reports/data/execution"
_SCOPE = _EXECUTION_DIR / "f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_HEAD = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    check=True,
    capture_output=True,
    text=True,
    cwd=_ROOT,
).stdout.strip()
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_PLAN_HASH = "1902157e61360897eb8cdb5a07f16877b15c0f56301f8584bfa03d0e95be25b5"
_SCOPE_SHA = "0c2f0d42eeb8349533010f8bc8aeb5a8413e889376399c21971ec9b31b829ac1"
_SCOPE_HASH = "cf08cd6ced5dec00bbb142fb9daa41e1f1070f281fbce5f29ce58c6e95fdd035"
_PILOT_PLAN_SHA = "8b74ddf96873ffd8f08ace7e287eb24df130eb2483ac85a6f9af75355c66aafd"
_JOURNAL_SHA = "7eecde7bbd18b5928c6d5e82557db226f62e0556b4fe43dfd91e239083707c92"


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Isolated, ignored output area under reports/data/execution."""
    execution = _EXECUTION_DIR / f"test_development_quote_cli_{tmp_path.name}"
    execution.mkdir(parents=True, exist_ok=True)
    yield execution
    shutil.rmtree(execution, ignore_errors=True)


def _paths(workdir: Path) -> tuple[Path, Path]:
    return (
        workdir / "development-checkpoint.json",
        workdir / "development-progress.json",
    )


def _args(workdir: Path) -> list[str]:
    checkpoint, output = _paths(workdir)
    return [
        "data",
        "development",
        "quote-cost",
        "--initialize-only",
        "--scope",
        str(_SCOPE),
        "--checkpoint",
        str(checkpoint),
        "--output",
        str(output),
        "--hard-timeout-seconds",
        "30",
        "--maximum-attempts",
        "2",
        "--total-deadline-seconds",
        "60",
        "--expected-repository-head",
        _HEAD,
        "--expected-plan-sha256",
        _PLAN_SHA,
        "--expected-plan-hash",
        _PLAN_HASH,
        "--expected-scope-sha256",
        _SCOPE_SHA,
        "--expected-scope-hash",
        _SCOPE_HASH,
        "--expected-pilot-plan-sha256",
        _PILOT_PLAN_SHA,
        "--expected-journal-sha256",
        _JOURNAL_SHA,
    ]


def test_development_quote_help_exposes_bounded_resume_contract() -> None:
    result = runner.invoke(
        app,
        ["data", "development", "quote-cost", "--help"],
        terminal_width=240,
    )
    assert result.exit_code == 0, result.output
    normalized_help = "".join(result.output.split())
    for option in (
        "--scope",
        "--checkpoint",
        "--output",
        "--resume",
        "--initialize-only",
    ):
        assert option in normalized_help


def test_initialize_only_verifies_exact_production_scope_without_provider(
    monkeypatch: pytest.MonkeyPatch, workdir: Path
) -> None:
    imported_before = "databento" in sys.modules
    monkeypatch.setattr(
        data_module,
        "_load_dotenv",
        lambda *_: pytest.fail("initialize-only loaded .env"),
    )
    result = runner.invoke(app, _args(workdir))
    assert result.exit_code == 0, result.output
    checkpoint_path, progress_path = _paths(workdir)
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    assert checkpoint["schema_version"] == "development-cost-checkpoint-v1"
    assert checkpoint["bindings"]["development_scope_hash"] == _SCOPE_HASH
    assert checkpoint["policy"] == {
        "hard_operation_timeout_seconds": 30.0,
        "maximum_attempts": 2,
    }
    assert len(checkpoint["pending_endpoints"]) == 490
    assert progress["schema_version"] == "development-cost-progress-v1"
    assert progress["status"] == "incomplete"
    assert progress["resume_eligible"] is True
    assert progress["provider_operation_counters"] == {
        "list_schemas": 0,
        "get_record_count": 0,
        "get_billable_size": 0,
        "get_cost": 0,
        "timeseries_get_range": 0,
        "batch": 0,
        "live": 0,
        "symbology": 0,
    }
    request_ids = set(checkpoint["pending_endpoints"])
    assert "ebefaaae3b198092" not in request_ids
    assert "d5352ffb04e4bc83" not in request_ids
    assert not ("databento" in sys.modules and not imported_before)


def test_scope_gate_fails_before_dotenv_or_checkpoint_write(
    monkeypatch: pytest.MonkeyPatch, workdir: Path
) -> None:
    monkeypatch.setattr(
        data_module,
        "_load_dotenv",
        lambda *_: pytest.fail("failed scope gate loaded .env"),
    )
    args = _args(workdir)
    args[args.index("--expected-scope-hash") + 1] = "0" * 64
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "scope hash" in result.output.lower()
    checkpoint_path, progress_path = _paths(workdir)
    assert not checkpoint_path.exists()
    assert not progress_path.exists()


def test_output_path_outside_execution_dir_is_rejected(tmp_path: Path, workdir: Path) -> None:
    outside = tmp_path / "elsewhere.json"
    args = _args(workdir)
    args[args.index("--output") + 1] = str(outside)
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "reports/data/execution" in result.output


def test_output_path_cannot_overwrite_protected_scope(workdir: Path) -> None:
    args = _args(workdir)
    args[args.index("--output") + 1] = str(_SCOPE)
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "protected" in result.output
    assert _SCOPE.exists() and _SCOPE.read_text(encoding="utf-8").strip().startswith("{")


def test_live_run_rejects_dirty_working_tree_before_dotenv(
    monkeypatch: pytest.MonkeyPatch, workdir: Path
) -> None:
    monkeypatch.setattr(data_module, "_git_dirty", lambda _: True)
    monkeypatch.setattr(
        data_module,
        "_load_dotenv",
        lambda *_: pytest.fail("dirty tree reached dotenv"),
    )
    args = _args(workdir)
    args.remove("--initialize-only")
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "clean" in result.output
