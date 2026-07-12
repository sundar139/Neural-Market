import sys

import pytest
from typer.testing import CliRunner

from neuralmarket import __version__
from neuralmarket.__main__ import main
from neuralmarket.cli.main import app

runner = CliRunner()


@pytest.mark.unit
def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


@pytest.mark.unit
def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output


@pytest.mark.unit
def test_module_main_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["neuralmarket", "--version"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
