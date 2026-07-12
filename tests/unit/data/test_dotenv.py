import os
from pathlib import Path

import pytest

from neuralmarket.cli.data import _load_dotenv


@pytest.mark.unit
def test_dotenv_loads_quoted_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("NM_TEST_TOKEN", raising=False)
    (tmp_path / ".env").write_text('# a comment\nNM_TEST_TOKEN = "abc 123"\n', encoding="utf-8")
    _load_dotenv(tmp_path)
    assert os.environ["NM_TEST_TOKEN"] == "abc 123"


@pytest.mark.unit
def test_process_env_overrides_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NM_TEST_PRECEDENCE", "from_process")
    (tmp_path / ".env").write_text("NM_TEST_PRECEDENCE=from_dotenv\n", encoding="utf-8")
    _load_dotenv(tmp_path)
    assert os.environ["NM_TEST_PRECEDENCE"] == "from_process"


@pytest.mark.unit
def test_malformed_lines_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("NM_TEST_OK", raising=False)
    (tmp_path / ".env").write_text("this_is_not_valid\nNM_TEST_OK=fine\n", encoding="utf-8")
    _load_dotenv(tmp_path)
    assert os.environ["NM_TEST_OK"] == "fine"


@pytest.mark.unit
def test_missing_dotenv_is_noop(tmp_path: Path) -> None:
    # No .env in tmp_path; must not raise and must not read the real project .env.
    _load_dotenv(tmp_path)
