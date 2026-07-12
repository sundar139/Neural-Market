from pathlib import Path

import pytest

from neuralmarket.core.configuration import (
    ConfigurationError,
    ReproducibilityConfig,
    config_sha256,
    load_config,
)

_VALID = """
seed: 1337
expected_python_major: 3
expected_python_minor: 11
deterministic: true
warn_on_nondeterminism: true
log_level: INFO
package_name: neuralmarket
schema_version: "1.0"
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.unit
def test_load_valid_config(tmp_path: Path) -> None:
    config = load_config(_write(tmp_path, _VALID))
    assert isinstance(config, ReproducibilityConfig)
    assert config.seed == 1337
    assert config.expected_python_minor == 11
    assert config.schema_version == "1.0"


@pytest.mark.unit
def test_default_config_file_matches_schema() -> None:
    config = load_config(Path("configs/reproducibility/default.yaml"))
    assert config.seed == 1337


@pytest.mark.unit
def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_config(tmp_path / "missing.yaml")


@pytest.mark.unit
def test_malformed_yaml_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Malformed YAML"):
        load_config(_write(tmp_path, "seed: [unterminated"))


@pytest.mark.unit
def test_non_mapping_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="must contain a mapping"):
        load_config(_write(tmp_path, "- just\n- a\n- list\n"))


@pytest.mark.unit
def test_invalid_value_rejected(tmp_path: Path) -> None:
    bad = _VALID.replace("seed: 1337", "seed: -1")
    with pytest.raises(ConfigurationError, match="Invalid configuration"):
        load_config(_write(tmp_path, bad))


@pytest.mark.unit
def test_extra_field_rejected(tmp_path: Path) -> None:
    bad = _VALID + "surprise: true\n"
    with pytest.raises(ConfigurationError):
        load_config(_write(tmp_path, bad))


@pytest.mark.unit
def test_config_sha256_stable(tmp_path: Path) -> None:
    path = _write(tmp_path, _VALID)
    assert config_sha256(path) == config_sha256(path)
    assert len(config_sha256(path)) == 64
