"""Typed reproducibility configuration loading with strict validation."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigurationError(Exception):
    """Raised when a reproducibility configuration cannot be loaded or validated."""


class ReproducibilityConfig(BaseModel):
    """Typed reproducibility settings frozen for a research run.

    Attributes:
        seed: Default research seed applied across random number generators.
        expected_python_major: Required Python major version.
        expected_python_minor: Required Python minor version.
        deterministic: Whether deterministic algorithm settings are requested.
        warn_on_nondeterminism: Whether to warn when determinism cannot be guaranteed.
        log_level: Logging verbosity for application utilities.
        package_name: Expected distribution name used for provenance checks.
        schema_version: Version of the environment-report JSON schema.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    seed: int = Field(ge=0)
    expected_python_major: int = Field(ge=3, le=3)
    expected_python_minor: int = Field(ge=0)
    deterministic: bool = True
    warn_on_nondeterminism: bool = True
    log_level: str = "INFO"
    package_name: str = "neuralmarket"
    schema_version: str


def _read_config_text(path: Path) -> str:
    """Read configuration text as UTF-8, raising a clear error when missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Unable to read configuration file {path}: {exc}") from exc


def config_sha256(path: Path) -> str:
    """Return the SHA-256 hash of a configuration file's raw bytes.

    Args:
        path: Path to the configuration file.

    Returns:
        The hexadecimal SHA-256 digest of the file contents.
    """
    text = _read_config_text(path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_config(path: Path) -> ReproducibilityConfig:
    """Load and validate a reproducibility configuration from YAML.

    Args:
        path: Path to a YAML configuration file.

    Returns:
        A validated :class:`ReproducibilityConfig`.

    Raises:
        ConfigurationError: If the file is missing, is not valid YAML, is not a
            mapping, or fails schema validation.
    """
    text = _read_config_text(path)
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Malformed YAML in configuration file {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"Configuration file {path} must contain a mapping, got {type(raw).__name__}."
        )

    try:
        return ReproducibilityConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid configuration in {path}: {exc}") from exc
