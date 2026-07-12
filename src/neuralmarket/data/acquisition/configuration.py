"""Typed configuration for budget-constrained acquisition planning."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from neuralmarket.core.configuration import ConfigurationError
from neuralmarket.data.acquisition.budget import BudgetPolicy


class AcquisitionUnderlyingConfig(BaseModel):
    """Approved ARCX underlying dataset/schemas for the catalog wave."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    symbol: str
    symbol_type: str
    definition_schema: str
    daily_schema: str
    statistics_schema: str


class AcquisitionOptionsConfig(BaseModel):
    """Approved OPRA options dataset/schemas and parent selector."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    definition_schema: str
    quote_schema: str
    parent_symbol: str
    symbol_type: str


class AcquisitionConfig(BaseModel):
    """Top-level acquisition-planning configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    underlying: AcquisitionUnderlyingConfig
    options: AcquisitionOptionsConfig
    pilot_candidate_year: int = Field(ge=1900)
    budget: BudgetPolicy


def load_acquisition_config(path: Path) -> AcquisitionConfig:
    """Load and validate an acquisition-planning configuration from YAML.

    Raises:
        ConfigurationError: If the file is missing, is not valid YAML, is not a
            mapping, or fails schema validation.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Acquisition configuration file not found: {path}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Unable to read acquisition configuration {path}: {exc}") from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Malformed YAML in acquisition configuration {path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"Acquisition configuration {path} must contain a mapping, got {type(raw).__name__}."
        )

    try:
        return AcquisitionConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid acquisition configuration in {path}: {exc}") from exc
