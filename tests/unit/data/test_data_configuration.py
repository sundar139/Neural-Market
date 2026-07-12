from datetime import date
from pathlib import Path

import pytest

from neuralmarket.core.configuration import ConfigurationError
from neuralmarket.data.configuration import FinalTestAccessStatus, load_data_config

_CONFIG = Path("configs/data/spy_daily_databento.yaml")


@pytest.mark.unit
def test_load_default_data_config() -> None:
    config = load_data_config(_CONFIG)
    assert config.provider.underlying.dataset == "ARCX.PILLAR"
    assert config.provider.underlying.venue == "NYSE_ARCA"
    assert config.provider.underlying.source_class == "primary_listing_venue"
    assert config.provider.underlying.price_role == "underlying_reference_path"
    assert config.provider.underlying.quote_role == "venue_liquidity_proxy"
    assert config.provider.underlying.optional_statistics_schema == "statistics"
    assert config.provider.underlying.venue_specific is True
    assert config.provider.underlying.consolidated_equities is False
    assert config.provider.underlying.sip is False
    assert config.provider.underlying.official_nbbo is False
    assert config.provider.underlying.full_market_volume is False
    assert config.provider.underlying.quote_schema == "bbo-1m"
    assert config.provider.options.dataset == "OPRA.PILLAR"
    assert config.provider.options.source_class == "consolidated_options_feed"
    assert config.study.start_date == date(2018, 5, 1)
    assert config.splits.final_test_access_status is FinalTestAccessStatus.SEALED
    assert config.splits.boundary_exclusion_sessions == 100


@pytest.mark.unit
def test_no_obsolete_datasets() -> None:
    text = _CONFIG.read_text(encoding="utf-8")
    assert "EQUS.SUMMARY" not in text
    assert "EQUS.MINI" not in text
    assert "DBEQ.BASIC" not in text


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("venue_specific", "false"),
        ("consolidated_equities", "true"),
        ("sip", "true"),
        ("official_nbbo", "true"),
        ("full_market_volume", "true"),
    ],
)
def test_contradictory_arcx_claim_rejected(tmp_path: Path, field: str, bad_value: str) -> None:
    good_value = "true" if field == "venue_specific" else "false"
    text = _CONFIG.read_text(encoding="utf-8").replace(
        f"{field}: {good_value}", f"{field}: {bad_value}"
    )
    bad = tmp_path / "bad.yaml"
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_data_config(bad)


@pytest.mark.unit
def test_missing_config_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_data_config(tmp_path / "missing.yaml")


@pytest.mark.unit
def test_malformed_yaml_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("provider: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Malformed YAML"):
        load_data_config(bad)


@pytest.mark.unit
def test_non_mapping_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "list.yaml"
    bad.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must contain a mapping"):
        load_data_config(bad)


@pytest.mark.unit
def test_bad_moneyness_rejected(tmp_path: Path) -> None:
    text = _CONFIG.read_text(encoding="utf-8").replace(
        "minimum_moneyness: 0.90", "minimum_moneyness: 1.50"
    )
    bad = tmp_path / "bad.yaml"
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_data_config(bad)


@pytest.mark.unit
def test_anchor_window_mismatch_rejected(tmp_path: Path) -> None:
    text = _CONFIG.read_text(encoding="utf-8").replace(
        "training_start: 2018-05-01", "training_start: 2019-01-02"
    )
    bad = tmp_path / "bad.yaml"
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_data_config(bad)
