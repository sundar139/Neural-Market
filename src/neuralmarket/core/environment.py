"""Environment provenance collection for reproducible research runs.

Collects a redacted, machine-readable snapshot of the runtime environment. It
never serializes environment-variable values, credentials, or secrets: for
supported variables it records only whether they are configured.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

from neuralmarket.core.configuration import ReproducibilityConfig, config_sha256
from neuralmarket.core.logging import get_logger

_logger = get_logger(__name__)

# Direct runtime dependencies whose installed versions are recorded for provenance.
_DIRECT_DEPENDENCIES = (
    "numpy",
    "pydantic",
    "pydantic-settings",
    "PyYAML",
    "typer",
    "rich",
    "platformdirs",
)

# Supported environment variables. Only presence is reported, never the value.
_SUPPORTED_ENV_VARS = (
    "NEURALMARKET_LOG_LEVEL",
    "NEURALMARKET_DATA_ROOT",
    "NEURALMARKET_ARTIFACT_ROOT",
)

_MARKET_ARTIFACT_PATTERNS = ("*.dbn", "*.dbz", "*.parquet", "*.arrow", "*.sqlite")
_SCAN_EXCLUDED_NAMES = frozenset(
    {".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__"}
)


class EnvironmentValidationError(Exception):
    """Raised when the runtime environment fails a required validation check."""


def scan_production_artifacts(root: Path, *, excluded_roots: tuple[Path, ...] = ()) -> list[Path]:
    """Return unauthorized market artifacts, excluding only exact supplied subtrees."""
    resolved_exclusions = tuple(path.resolve() for path in excluded_roots)
    findings: list[Path] = []
    for pattern in _MARKET_ARTIFACT_PATTERNS:
        for path in root.rglob(pattern):
            resolved = path.resolve()
            if any(name in _SCAN_EXCLUDED_NAMES for name in path.parts):
                continue
            if any(
                resolved == excluded or excluded in resolved.parents
                for excluded in resolved_exclusions
            ):
                continue
            if path.name.endswith(".local.sqlite"):
                continue
            findings.append(path)
    return sorted(set(findings))


def find_repository_root(start: Path | None = None) -> Path:
    """Locate the repository root by walking up to the nearest ``pyproject.toml``.

    Args:
        start: Directory to begin the search from; defaults to this module's location.

    Returns:
        The resolved repository root path.

    Raises:
        EnvironmentValidationError: If no ``pyproject.toml`` is found in any parent.
    """
    origin = (start or Path(__file__)).resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise EnvironmentValidationError(
        "Could not resolve repository root: no pyproject.toml found in any parent directory."
    )


def _git(root: Path, *args: str) -> str | None:
    """Run a git command in ``root``, returning stripped stdout or ``None`` on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _git_commit(root: Path) -> str | None:
    """Return the current git commit hash when available."""
    return _git(root, "rev-parse", "HEAD")


def _git_dirty(root: Path) -> bool | None:
    """Return whether the working tree has uncommitted changes, or ``None`` if unknown."""
    status = _git(root, "status", "--porcelain")
    if status is None:
        return None
    return bool(status)


def _dependency_versions() -> dict[str, str]:
    """Return installed versions of direct dependencies, marking any that are absent."""
    versions: dict[str, str] = {}
    for name in _DIRECT_DEPENDENCIES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def _pytorch_status() -> dict[str, Any]:
    """Report optional PyTorch status, treating absence as intentionally deferred."""
    try:
        import torch
    except ImportError:
        return {"installed": False, "version": None, "status": "deferred"}
    return {"installed": True, "version": str(torch.__version__), "status": "installed"}


def _cuda_status() -> dict[str, Any]:
    """Report optional CUDA status, treating absence as intentionally deferred."""
    try:
        import torch
    except ImportError:
        return {"available": False, "device_count": 0, "status": "deferred"}
    available = bool(torch.cuda.is_available())
    return {
        "available": available,
        "device_count": torch.cuda.device_count() if available else 0,
        "status": "available" if available else "not available",
    }


def _env_var_presence() -> dict[str, dict[str, bool]]:
    """Report only whether supported environment variables are configured."""
    import os

    return {name: {"configured": name in os.environ} for name in _SUPPORTED_ENV_VARS}


def _package_version() -> str:
    """Return the installed package version, or a source-tree sentinel."""
    try:
        return metadata.version("neuralmarket")
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"


def validate_python(config: ReproducibilityConfig) -> None:
    """Validate that the running interpreter matches the configured Python version.

    Args:
        config: Loaded reproducibility configuration.

    Raises:
        EnvironmentValidationError: If the interpreter major/minor version differs
            from the configuration.
    """
    major, minor = sys.version_info[:2]
    if (major, minor) != (config.expected_python_major, config.expected_python_minor):
        raise EnvironmentValidationError(
            f"Python {config.expected_python_major}.{config.expected_python_minor} required, "
            f"but running {major}.{minor}."
        )


def collect_snapshot(config: ReproducibilityConfig, config_path: Path) -> dict[str, Any]:
    """Collect a redacted environment provenance snapshot.

    Args:
        config: Loaded reproducibility configuration.
        config_path: Path to the configuration file, used for the SHA-256 hash.

    Returns:
        A JSON-serializable dictionary with deterministic field names.
    """
    root = find_repository_root()
    snapshot: dict[str, Any] = {
        "schema_version": config.schema_version,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "package": {"name": config.package_name, "version": _package_version()},
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
        },
        "repository": {
            "root": str(root),
            "git_commit": _git_commit(root),
            "git_dirty": _git_dirty(root),
        },
        "reproducibility": {
            "seed": config.seed,
            "deterministic": config.deterministic,
            "config_sha256": config_sha256(config_path),
        },
        "dependencies": _dependency_versions(),
        "optional": {"pytorch": _pytorch_status(), "cuda": _cuda_status()},
        "environment_variables": _env_var_presence(),
    }
    return snapshot
