from pathlib import Path

import pytest

from neuralmarket.core.configuration import ConfigurationError
from neuralmarket.data.acquisition.configuration import load_acquisition_config

_VALID = Path("configs/data/acquisition/spy_daily_budgeted.yaml")


@pytest.mark.unit
def test_load_valid_config() -> None:
    config = load_acquisition_config(_VALID)
    assert config.underlying.dataset == "ARCX.PILLAR"
    assert config.options.parent_symbol == "SPY.OPT"
    assert config.pilot_candidate_year == 2019


@pytest.mark.unit
def test_missing_file_raises() -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_acquisition_config(Path("does/not/exist.yaml"))


@pytest.mark.unit
def test_malformed_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("underlying: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Malformed YAML"):
        load_acquisition_config(path)


@pytest.mark.unit
def test_non_mapping_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must contain a mapping"):
        load_acquisition_config(path)


@pytest.mark.unit
def test_invalid_schema_raises(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("underlying: {}\noptions: {}\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid acquisition configuration"):
        load_acquisition_config(path)
