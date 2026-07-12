"""Typed market-data source and split configuration."""

from __future__ import annotations

from datetime import date, time
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from neuralmarket.core.configuration import ConfigurationError, config_sha256


class CrossedQuotePolicy(str, Enum):
    """Policy for consolidated quotes whose bid exceeds their ask."""

    REJECT = "reject"


class LockedQuotePolicy(str, Enum):
    """Policy for quotes whose bid equals their ask."""

    RETAIN_AND_FLAG = "retain_and_flag"


class MissingSidePolicy(str, Enum):
    """Policy for quotes missing a bid or ask side."""

    REJECT = "reject"


class FinalTestAccessStatus(str, Enum):
    """Access state for the sealed final-test split."""

    SEALED = "sealed"


class UnderlyingProviderConfig(BaseModel):
    """Underlying dataset, schemas, symbology, and venue-specific governance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    venue: str
    source_class: str
    definition_schema: str
    daily_schema: str
    quote_schema: str
    optional_statistics_schema: str
    symbol: str
    symbol_type: str
    price_role: str
    quote_role: str
    venue_specific: bool
    consolidated_equities: bool
    sip: bool
    official_nbbo: bool
    full_market_volume: bool
    required_future_validations: list[str]

    @model_validator(mode="after")
    def _validate_arcx_governance(self) -> UnderlyingProviderConfig:
        if self.dataset == "ARCX.PILLAR" and (
            self.venue != "NYSE_ARCA"
            or self.source_class != "primary_listing_venue"
            or self.price_role != "underlying_reference_path"
            or self.quote_role != "venue_liquidity_proxy"
            or not self.venue_specific
            or self.consolidated_equities
            or self.sip
            or self.official_nbbo
            or self.full_market_volume
            or "arcx_vs_equs_mini_development_overlap" not in self.required_future_validations
        ):
            raise ValueError(
                "ARCX.PILLAR configuration contradicts approved venue-specific governance"
            )
        return self


class OptionsProviderConfig(BaseModel):
    """Options dataset, schemas, and parent symbology."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    source_class: str
    definition_schema: str
    quote_schema: str
    parent_symbol: str
    symbol_type: str


class ProviderConfig(BaseModel):
    """Provider with distinct underlying and options source blocks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    underlying: UnderlyingProviderConfig
    options: OptionsProviderConfig


class StudyConfig(BaseModel):
    """Study window and market-calendar configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_date: date
    end_date: date
    calendar: str
    timezone: str
    regular_session_only: bool

    @model_validator(mode="after")
    def _check_order(self) -> StudyConfig:
        if self.end_date <= self.start_date:
            raise ValueError("study end_date must be after start_date")
        return self


class EpisodesConfig(BaseModel):
    """Option-episode scope constraints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_maturity_sessions: int = Field(ge=1)
    maximum_maturity_sessions: int = Field(ge=1)
    minimum_moneyness: float = Field(gt=0)
    maximum_moneyness: float = Field(gt=0)
    conditioning_lookback_sessions: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_ranges(self) -> EpisodesConfig:
        if self.maximum_maturity_sessions < self.minimum_maturity_sessions:
            raise ValueError("maximum_maturity_sessions must be >= minimum_maturity_sessions")
        if self.maximum_moneyness <= self.minimum_moneyness:
            raise ValueError("maximum_moneyness must be > minimum_moneyness")
        return self


class QuotesConfig(BaseModel):
    """End-of-day quote snapshot policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_time: time
    maximum_age_minutes: int = Field(ge=1)
    crossed_quote_policy: CrossedQuotePolicy
    locked_quote_policy: LockedQuotePolicy
    missing_side_policy: MissingSidePolicy


class SplitsConfig(BaseModel):
    """Chronological split anchors and purge/embargo sizes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    training_start: date
    training_anchor_end: date
    validation_anchor_end: date
    test_anchor_end: date
    purge_sessions: int = Field(ge=0)
    embargo_sessions: int = Field(ge=0)
    final_test_access_status: FinalTestAccessStatus

    @model_validator(mode="after")
    def _check_order(self) -> SplitsConfig:
        anchors = [
            self.training_start,
            self.training_anchor_end,
            self.validation_anchor_end,
            self.test_anchor_end,
        ]
        if anchors != sorted(anchors) or len(set(anchors)) != len(anchors):
            raise ValueError("split anchors must be strictly increasing in time")
        return self

    @property
    def boundary_exclusion_sessions(self) -> int:
        """Total sessions excluded at each development boundary (purge + embargo)."""
        return self.purge_sessions + self.embargo_sessions


class DataConfig(BaseModel):
    """Top-level market-data configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ProviderConfig
    study: StudyConfig
    episodes: EpisodesConfig
    quotes: QuotesConfig
    splits: SplitsConfig

    @model_validator(mode="after")
    def _check_anchor_window(self) -> DataConfig:
        if self.splits.training_start != self.study.start_date:
            raise ValueError("splits.training_start must equal study.start_date")
        if self.splits.test_anchor_end != self.study.end_date:
            raise ValueError("splits.test_anchor_end must equal study.end_date")
        return self


def load_data_config(path: Path) -> DataConfig:
    """Load and validate a market-data configuration from YAML.

    Args:
        path: Path to a YAML configuration file.

    Returns:
        A validated :class:`DataConfig`.

    Raises:
        ConfigurationError: If the file is missing, is not valid YAML, is not a
            mapping, or fails schema validation.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Data configuration file not found: {path}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Unable to read data configuration {path}: {exc}") from exc

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Malformed YAML in data configuration {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"Data configuration {path} must contain a mapping, got {type(raw).__name__}."
        )

    try:
        return DataConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid data configuration in {path}: {exc}") from exc


def data_config_sha256(path: Path) -> str:
    """Return the SHA-256 hash of a data configuration file's raw bytes."""
    return config_sha256(path)
