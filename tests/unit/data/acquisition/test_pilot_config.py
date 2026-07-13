import json
from pathlib import Path

import jsonschema
import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_pilot_config_loads_and_matches_expected_values() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "configs/data/acquisition/pilot_january_2019.yaml").read_text(encoding="utf-8")
    )
    assert config["pilot_execution"]["pilot_month"] == "2019-01"
    assert config["pilot_execution"]["maximum_spend_usd"] == "5.00"
    assert config["pilot_execution"]["purchase_authorized"] is False
    assert config["options"]["stype_in"] == "parent"


def test_authorization_template_is_schema_valid_but_unusable() -> None:
    template = json.loads(
        (REPO_ROOT / "configs/data/acquisition/pilot_authorization.template.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (REPO_ROOT / "data_contracts/pilot_authorization.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(template, schema)
    assert template["purchase_authorized"] is False
    assert template["confirmation_phrase"] == "REPLACE_ME"


def test_all_four_schemas_are_valid_json_schema() -> None:
    for name in (
        "pilot_request_plan",
        "pilot_authorization",
        "pilot_execution",
        "pilot_quality_report",
    ):
        schema = json.loads(
            (REPO_ROOT / f"data_contracts/{name}.schema.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator.check_schema(schema)
