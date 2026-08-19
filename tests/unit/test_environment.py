from pathlib import Path

import pytest

from neuralmarket.core.configuration import load_config
from neuralmarket.core.environment import (
    EnvironmentValidationError,
    collect_snapshot,
    find_repository_root,
    repository_source_identity,
    scan_production_artifacts,
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
def test_find_repository_root_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = Path.is_file
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: False if path.name == "pyproject.toml" else original(path),
    )
    with pytest.raises(EnvironmentValidationError, match="repository root"):
        find_repository_root(tmp_path)


@pytest.mark.unit
def test_artifact_scan_excludes_only_explicit_test_root(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    test_owned = root / "test-owned"
    unauthorized = root / "data" / "raw" / "production.dbn"
    test_owned.mkdir(parents=True)
    unauthorized.parent.mkdir(parents=True)
    (test_owned / "fixture.parquet").write_bytes(b"fixture")
    unauthorized.write_bytes(b"market")
    assert scan_production_artifacts(root, excluded_roots=(test_owned,)) == [unauthorized]


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


@pytest.mark.unit
def test_repository_source_identity_shape() -> None:
    identity = repository_source_identity()
    assert set(identity) == {"git_commit", "git_dirty"}
    if identity["git_commit"] is not None:
        assert len(identity["git_commit"]) == 40
    assert identity["git_dirty"] in (None, False, True)


@pytest.mark.unit
def test_repository_source_identity_tracked_only_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """git_dirty reflects TRACKED drift only; untracked files are not dirty."""
    import subprocess

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "seed")

    clean = repository_source_identity(tmp_path)
    assert clean["git_dirty"] is False

    # An untracked file must NOT make a tracked-clean source tree appear dirty.
    (tmp_path / "scratch.txt").write_text("untracked\n", encoding="utf-8")
    untracked_only = repository_source_identity(tmp_path)
    assert untracked_only["git_dirty"] is False
    assert untracked_only["git_commit"] == clean["git_commit"]

    # A tracked modification IS dirty.
    (tmp_path / "tracked.txt").write_text("v2\n", encoding="utf-8")
    tracked_dirty = repository_source_identity(tmp_path)
    assert tracked_dirty["git_dirty"] is True
    assert tracked_dirty["git_commit"] == clean["git_commit"]
