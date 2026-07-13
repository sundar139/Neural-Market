import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app

runner = CliRunner()

_PILOT_CONFIG = "configs/data/acquisition/pilot_january_2019.yaml"
_AUTH_TEMPLATE = "configs/data/acquisition/pilot_authorization.template.json"


class _ZeroCostMetadata:
    """Metadata client stub with deterministic nonzero estimates."""

    def get_record_count(self, **kwargs: Any) -> int:
        return 10

    def get_billable_size(self, **kwargs: Any) -> int:
        return 100

    def get_cost(self, **kwargs: Any) -> float:
        return 0.01001


class _Client:
    def __init__(self) -> None:
        self.metadata = _ZeroCostMetadata()
        self.timeseries = object()
        self.batch = object()
        self.live = object()


class _HighCostMetadata(_ZeroCostMetadata):
    def get_cost(self, **kwargs: Any) -> float:
        return 0.03


class _HighCostClient(_Client):
    def __init__(self) -> None:
        super().__init__()
        self.metadata = _HighCostMetadata()


@pytest.fixture
def pilot_manifest_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Build a fresh, unauthorized pilot request-plan manifest for tests to consume.

    Task 10's tracked ``data/manifests/pilot_request_plan_v1.json`` was removed as
    out-of-scope (Task 11 owns generating that file for real); tests that need a
    manifest on disk now build their own throwaway copy via the same CLI path
    exercised by ``test_pilot_prepare_generates_manifest_and_stays_unauthorized``.
    """
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", lambda: _Client())

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
            str(tmp_path / "pilot_preflight.local.json"),
            "--request-manifest",
            str(request_manifest_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    return request_manifest_path


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
    assert manifest["bindings"]["source_manifest_hash"]
    assert manifest["bindings"]["split_manifest_hash"]
    assert manifest["bindings"]["acquisition_policy_hash"]
    assert all(request["estimated_cost"] != "0.00" for request in manifest["requests"])
    assert Decimal(manifest["estimated_total_cost_usd"]) == sum(
        (Decimal(request["estimated_cost"]) for request in manifest["requests"]),
        Decimal("0"),
    )
    assert all(
        not Path(request["logical_output_path"]).is_absolute() for request in manifest["requests"]
    )


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
def test_pilot_prepare_rejects_aggregate_estimate_increase(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", _HighCostClient)
    manifest = tmp_path / "plan.json"
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
            str(manifest),
        ],
    )
    assert result.exit_code != 0
    assert not manifest.exists()


@pytest.mark.integration
def test_pilot_verify_is_fully_offline_and_rejects_template(
    pilot_manifest_path: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "verify",
            "--request-manifest",
            str(pilot_manifest_path),
            "--authorization-template",
            _AUTH_TEMPLATE,
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["template_usable_for_execution"] is False


@pytest.mark.integration
def test_pilot_verify_rejects_plan_bound_to_different_config(
    pilot_manifest_path: Path, tmp_path: Path
) -> None:
    config_path = tmp_path / "pilot.yaml"
    config_path.write_text(
        Path(_PILOT_CONFIG)
        .read_text(encoding="utf-8")
        .replace('maximum_spend_usd: "5.00"', 'maximum_spend_usd: "4.99"'),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "verify",
            "--request-manifest",
            str(pilot_manifest_path),
            "--authorization-template",
            _AUTH_TEMPLATE,
            "--config",
            str(config_path),
        ],
    )
    assert result.exit_code != 0


@pytest.mark.integration
def test_pilot_execute_rejects_incorrect_cost_summary_before_journal(
    pilot_manifest_path: Path, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    plan["estimated_total_cost_usd"] = "0.00"
    tampered_plan = tmp_path / "tampered-plan.json"
    tampered_plan.write_text(json.dumps(plan), encoding="utf-8")
    journal_path = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "execute",
            "--plan",
            str(tampered_plan),
            "--authorization",
            _AUTH_TEMPLATE,
            "--confirm-plan-hash",
            plan["plan_hash"],
            "--journal",
            str(journal_path),
        ],
    )
    assert result.exit_code != 0
    assert "plan_hash" in result.output.lower()
    assert not journal_path.exists()


@pytest.mark.integration
def test_pilot_execute_rejects_tampered_dependency_before_journal(
    pilot_manifest_path: Path, tmp_path: Path
) -> None:
    source = json.loads(Path("data/manifests/source_manifest_v1.json").read_text(encoding="utf-8"))
    source["provider"] = "tampered"
    tampered_source = tmp_path / "source.json"
    tampered_source.write_text(json.dumps(source), encoding="utf-8")
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    journal_path = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "execute",
            "--plan",
            str(pilot_manifest_path),
            "--authorization",
            _AUTH_TEMPLATE,
            "--confirm-plan-hash",
            plan["plan_hash"],
            "--source-manifest",
            str(tampered_source),
            "--journal",
            str(journal_path),
        ],
    )
    assert result.exit_code != 0
    assert "manifest" in result.output.lower()
    assert not journal_path.exists()


@pytest.mark.integration
def test_pilot_execute_fails_with_invalid_confirm_hash(
    pilot_manifest_path: Path, tmp_path: Path
) -> None:
    journal_path = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "execute",
            "--plan",
            str(pilot_manifest_path),
            "--authorization",
            _AUTH_TEMPLATE,
            "--confirm-plan-hash",
            "INVALID",
            "--journal",
            str(journal_path),
        ],
    )
    assert result.exit_code != 0
    assert "authoriz" in result.output.lower()
    assert not journal_path.exists()


@pytest.mark.integration
def test_pilot_recover_reports_no_downloads(pilot_manifest_path: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "pilot_recovery.local.json"
    journal_path = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "recover",
            "--plan",
            str(pilot_manifest_path),
            "--output",
            str(output_path),
            "--journal",
            str(journal_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["retried"] == 0
    assert report["deleted"] == 0
