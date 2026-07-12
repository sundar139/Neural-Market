import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neuralmarket.cli.main import app

runner = CliRunner()
_CONFIG = "configs/reproducibility/default.yaml"


@pytest.mark.integration
def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "neuralmarket" in result.output.lower()


@pytest.mark.integration
def test_environment_check_help() -> None:
    result = runner.invoke(app, ["environment", "check", "--help"])
    assert result.exit_code == 0


@pytest.mark.integration
def test_environment_check_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["environment", "check", "--config", _CONFIG, "--output", str(out)])
    assert result.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["python"]["version"].startswith("3.11")
    assert data["reproducibility"]["seed"] == 1337


@pytest.mark.integration
def test_environment_check_bad_config_fails() -> None:
    result = runner.invoke(app, ["environment", "check", "--config", "does/not/exist.yaml"])
    assert result.exit_code == 2


@pytest.mark.integration
def test_environment_check_bad_output_path_fails(tmp_path: Path) -> None:
    # A path whose parent is an existing file cannot be created.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    bad_out = blocker / "report.json"
    result = runner.invoke(
        app, ["environment", "check", "--config", _CONFIG, "--output", str(bad_out)]
    )
    assert result.exit_code == 1
