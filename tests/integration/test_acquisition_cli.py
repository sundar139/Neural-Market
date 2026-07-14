import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app

runner = CliRunner()

_CONFIG = "configs/data/acquisition/spy_daily_budgeted.yaml"
_SOURCE_MANIFEST = "data/manifests/source_manifest_v1.json"
_SPLIT_MANIFEST = "data/manifests/split_manifest_v1.json"


class _Metadata:
    def __init__(self) -> None:
        self.calls = 0

    def get_record_count(self, **kwargs: Any) -> int:
        self.calls += 1
        return 10

    def get_billable_size(self, **kwargs: Any) -> int:
        self.calls += 1
        return 100

    def get_cost(self, **kwargs: Any) -> float:
        self.calls += 1
        return 0.001


class _Client:
    def __init__(self) -> None:
        self.metadata = _Metadata()
        self.timeseries = object()
        self.batch = object()
        self.live = object()


@pytest.mark.integration
def test_acquisition_plan_help() -> None:
    assert runner.invoke(app, ["data", "acquisition", "plan", "--help"]).exit_code == 0


@pytest.mark.integration
def test_acquisition_verify_help() -> None:
    assert runner.invoke(app, ["data", "acquisition", "verify", "--help"]).exit_code == 0


@pytest.mark.integration
def test_acquisition_plan_without_key_exit_two(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    result = runner.invoke(
        app,
        [
            "data",
            "acquisition",
            "plan",
            "--config",
            _CONFIG,
            "--source-manifest",
            _SOURCE_MANIFEST,
            "--split-manifest",
            _SPLIT_MANIFEST,
            "--output",
            str(tmp_path / "plan.json"),
            "--policy-manifest",
            str(tmp_path / "policy.json"),
        ],
    )
    assert result.exit_code == 2


@pytest.mark.integration
def test_acquisition_plan_and_verify_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "neuralmarket.data.acquisition.planner._verify_ancestor",
        lambda repo_root, required_commit: True,
    )
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", lambda: _Client())

    plan_output = tmp_path / "plan.json"
    policy_output = tmp_path / "policy.json"
    result = runner.invoke(
        app,
        [
            "data",
            "acquisition",
            "plan",
            "--config",
            _CONFIG,
            "--source-manifest",
            _SOURCE_MANIFEST,
            "--split-manifest",
            _SPLIT_MANIFEST,
            "--output",
            str(plan_output),
            "--policy-manifest",
            str(policy_output),
        ],
    )
    assert result.exit_code == 0
    plan_data = json.loads(plan_output.read_text(encoding="utf-8"))
    assert plan_data["recommendation_status"] == "recommended_not_authorized"
    assert plan_data["download_attempts"] == 0
    assert plan_data["downloaded_records"] == 0
    assert "DATABENTO_API_KEY" not in plan_output.read_text(encoding="utf-8")

    policy_data = json.loads(policy_output.read_text(encoding="utf-8"))
    assert policy_data["purchase_authorized"] is False
    assert policy_data["download_guard_enabled"] is True
    assert policy_data["manifest_hash"]

    verify_result = runner.invoke(
        app,
        [
            "data",
            "acquisition",
            "verify",
            "--plan",
            str(plan_output),
            "--policy-manifest",
            str(policy_output),
        ],
    )
    assert verify_result.exit_code == 0
    assert json.loads(verify_result.stdout) == {"status": "ok"}


@pytest.mark.integration
def test_acquisition_plan_rejects_missing_ancestry_without_metadata_or_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    client = _Client()
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", lambda: client)
    monkeypatch.setattr(
        "neuralmarket.data.acquisition.planner._verify_ancestor",
        lambda repo_root, required_commit: False,
    )

    plan_output = tmp_path / "plan.json"
    policy_output = tmp_path / "policy.json"
    result = runner.invoke(
        app,
        [
            "data",
            "acquisition",
            "plan",
            "--config",
            _CONFIG,
            "--source-manifest",
            _SOURCE_MANIFEST,
            "--split-manifest",
            _SPLIT_MANIFEST,
            "--output",
            str(plan_output),
            "--policy-manifest",
            str(policy_output),
        ],
    )

    assert result.exit_code == 1
    assert "81064f9" in caplog.text
    assert client.metadata.calls == 0
    assert not plan_output.exists()
    assert not policy_output.exists()


@pytest.mark.integration
def test_acquisition_verify_detects_tamper(tmp_path: Path) -> None:
    plan_output = tmp_path / "plan.json"
    policy_output = tmp_path / "policy.json"
    policy_output.write_text(
        json.dumps({"manifest_hash": "not-a-real-hash", "purchase_authorized": False}),
        encoding="utf-8",
    )
    plan_output.write_text(json.dumps({}), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "data",
            "acquisition",
            "verify",
            "--plan",
            str(plan_output),
            "--policy-manifest",
            str(policy_output),
        ],
    )
    assert result.exit_code == 1
