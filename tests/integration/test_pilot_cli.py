import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app

runner = CliRunner()

_PILOT_CONFIG = "configs/data/acquisition/pilot_january_2019.yaml"
_REQUEST_MANIFEST = "data/manifests/pilot_request_plan_v1.json"
_AUTH_TEMPLATE = "configs/data/acquisition/pilot_authorization.template.json"


class _ZeroCostMetadata:
    """Metadata client stub whose costs match the plan's zero placeholder exactly.

    Preflight compares fresh estimates to the plan's already-written estimate
    within a tolerance; returning zero keeps the very first preflight pass
    clean so this test exercises the happy path (manifest written, still
    unauthorized) rather than the tolerance-rejection path.
    """

    def get_record_count(self, **kwargs: Any) -> int:
        return 10

    def get_billable_size(self, **kwargs: Any) -> int:
        return 100

    def get_cost(self, **kwargs: Any) -> float:
        return 0.0


class _Client:
    def __init__(self) -> None:
        self.metadata = _ZeroCostMetadata()
        self.timeseries = object()
        self.batch = object()
        self.live = object()


@pytest.mark.integration
def test_pilot_prepare_help() -> None:
    assert runner.invoke(app, ["data", "pilot", "prepare", "--help"]).exit_code == 0


@pytest.mark.integration
def test_pilot_verify_help() -> None:
    assert runner.invoke(app, ["data", "pilot", "verify", "--help"]).exit_code == 0


@pytest.mark.integration
def test_pilot_execute_help() -> None:
    assert runner.invoke(app, ["data", "pilot", "execute", "--help"]).exit_code == 0


@pytest.mark.integration
def test_pilot_recover_help() -> None:
    assert runner.invoke(app, ["data", "pilot", "recover", "--help"]).exit_code == 0


@pytest.mark.integration
def test_pilot_prepare_generates_manifest_and_stays_unauthorized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", lambda: _Client())

    output_path = tmp_path / "pilot_preflight.local.json"
    request_manifest_path = tmp_path / "pilot_request_plan_v1.json"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "prepare",
            "--config",
            _PILOT_CONFIG,
            "--output",
            str(output_path),
            "--request-manifest",
            str(request_manifest_path),
        ],
    )
    assert result.exit_code == 0, result.stdout

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["purchase_authorized"] is False
    assert report["download_attempts"] == 0
    assert report["batch_jobs_submitted"] == 0
    assert report["live_connections_opened"] == 0

    manifest = json.loads(request_manifest_path.read_text(encoding="utf-8"))
    assert manifest["purchase_authorized"] is False
    assert isinstance(manifest["plan_hash"], str)
    assert len(manifest["plan_hash"]) == 64


@pytest.mark.integration
def test_pilot_prepare_without_key_exit_two(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "prepare",
            "--config",
            _PILOT_CONFIG,
            "--output",
            str(tmp_path / "preflight.json"),
            "--request-manifest",
            str(tmp_path / "plan.json"),
        ],
    )
    assert result.exit_code == 2


@pytest.mark.integration
def test_pilot_verify_is_fully_offline_and_rejects_template() -> None:
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "verify",
            "--request-manifest",
            _REQUEST_MANIFEST,
            "--authorization-template",
            _AUTH_TEMPLATE,
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["template_usable_for_execution"] is False


@pytest.mark.integration
def test_pilot_execute_fails_with_invalid_confirm_hash() -> None:
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "execute",
            "--plan",
            _REQUEST_MANIFEST,
            "--authorization",
            _AUTH_TEMPLATE,
            "--confirm-plan-hash",
            "INVALID",
        ],
    )
    assert result.exit_code != 0
    assert "authoriz" in result.stdout.lower()


@pytest.mark.integration
def test_pilot_recover_reports_no_downloads(tmp_path: Path) -> None:
    output_path = tmp_path / "pilot_recovery.local.json"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "recover",
            "--plan",
            _REQUEST_MANIFEST,
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["retried"] == 0
    assert report["deleted"] == 0
