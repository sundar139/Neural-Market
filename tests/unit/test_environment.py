from pathlib import Path

import pytest

from neuralmarket.core.configuration import load_config
from neuralmarket.core.environment import (
    EnvironmentValidationError,
    collect_snapshot,
    find_repository_root,
    validate_python,
)

_CONFIG_PATH = Path("configs/reproducibility/default.yaml")


@pytest.fixture
def config():  # type: ignore[no-untyped-def]
    return load_config(_CONFIG_PATH)


@pytest.mark.unit
def test_find_repository_root_has_pyproject() -> None:
    root = find_repository_root()
    assert (root / "pyproject.toml").is_file()


@pytest.mark.unit
def test_find_repository_root_missing(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentValidationError, match="repository root"):
        find_repository_root(tmp_path)


@pytest.mark.unit
def test_validate_python_passes(config) -> None:  # type: ignore[no-untyped-def]
    validate_python(config)


@pytest.mark.unit
def test_validate_python_mismatch(config) -> None:  # type: ignore[no-untyped-def]
    mismatched = config.model_copy(update={"expected_python_minor": 99})
    with pytest.raises(EnvironmentValidationError, match="required"):
        validate_python(mismatched)


@pytest.mark.unit
def test_snapshot_contains_required_fields(config) -> None:  # type: ignore[no-untyped-def]
    snapshot = collect_snapshot(config, _CONFIG_PATH)
    for key in (
        "schema_version",
        "generated_at_utc",
        "package",
        "python",
        "platform",
        "repository",
        "reproducibility",
        "dependencies",
        "optional",
        "environment_variables",
    ):
        assert key in snapshot

    assert snapshot["reproducibility"]["seed"] == 1337
    assert len(snapshot["reproducibility"]["config_sha256"]) == 64
    assert snapshot["python"]["version"].startswith("3.11")
    assert snapshot["optional"]["pytorch"]["status"] in {"deferred", "installed"}


@pytest.mark.unit
def test_snapshot_excludes_env_values(monkeypatch, config) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("NEURALMARKET_LOG_LEVEL", "SECRET_SENTINEL_VALUE")
    snapshot = collect_snapshot(config, _CONFIG_PATH)
    serialized = str(snapshot)
    assert "SECRET_SENTINEL_VALUE" not in serialized
    assert snapshot["environment_variables"]["NEURALMARKET_LOG_LEVEL"] == {"configured": True}
