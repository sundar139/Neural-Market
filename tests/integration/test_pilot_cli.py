import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app
from neuralmarket.data.acquisition.attestation import compute_attestation_hash
from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    compute_authorization_hash,
)
from neuralmarket.data.acquisition.executor import (
    PilotExecutionCoordinator,
    RawAcquisitionResult,
)
from neuralmarket.data.acquisition.journal import RequestJournal
from neuralmarket.data.acquisition.metadata_runner import IsolatedMetadataResult
from neuralmarket.data.acquisition.requests import AcquisitionRequest, load_pilot_config
from neuralmarket.data.raw.integrity import sha256_of_file

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


def _isolated(cost: str = "0.01001"):
    def run(**kwargs):
        request = kwargs["request"]
        return IsolatedMetadataResult(
            estimate=data_module.MetadataEstimate(
                dataset=request.dataset,
                schema=request.schema_name,
                symbol=request.symbols[0],
                stype_in=request.stype_in,
                window_start=request.start,
                window_end=request.end_exclusive,
                record_count=10,
                billable_size_bytes=100,
                cost_usd=Decimal(cost),
                retries=0,
            ),
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    return run


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
    monkeypatch.setattr(data_module, "_run_isolated_metadata", _isolated())
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")

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
            "--checkpoint",
            str(tmp_path / "metadata_checkpoint.local.json"),
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
    monkeypatch.setattr(data_module, "_run_isolated_metadata", _isolated())
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")

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
            "--checkpoint",
            str(tmp_path / "metadata_checkpoint.local.json"),
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
    monkeypatch.setattr(data_module, "_run_isolated_metadata", _isolated("0.03"))
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")
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
            "--checkpoint",
            str(tmp_path / "metadata_checkpoint.local.json"),
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
def test_pilot_validate_only_uses_metadata_capability_without_paid_namespaces(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))

    class HostileClient:
        metadata = _ZeroCostMetadata()

        @property
        def timeseries(self) -> object:
            raise AssertionError("timeseries namespace accessed")

        @property
        def batch(self) -> object:
            raise AssertionError("batch namespace accessed")

        @property
        def live(self) -> object:
            raise AssertionError("live namespace accessed")

    now = data_module.datetime.now(data_module.UTC)
    auth_payload: dict[str, object] = {
        "authorization_version": "1.0",
        "pilot_plan_hash": plan["plan_hash"],
        "source_manifest_hash": plan["bindings"]["source_manifest_hash"],
        "split_manifest_hash": plan["bindings"]["split_manifest_hash"],
        "acquisition_policy_hash": plan["bindings"]["acquisition_policy_hash"],
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "authorized_by": "test_operator",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
    }
    auth_payload["authorization_hash"] = compute_authorization_hash(auth_payload)
    auth_path = tmp_path / "authorization.json"
    auth_path.write_text(json.dumps(auth_payload), encoding="utf-8")
    attestation_payload: dict[str, object] = {
        "attestation_version": "1.0",
        "portal_historical_limit_usd": "5.00",
        "portal_limit_confirmed": True,
        "portal_limit_confirmed_at": now.isoformat(),
        "portal_limit_confirmed_by": "test_operator",
        "confirmation_method": "manual_portal_review",
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "plan_hash": plan["plan_hash"],
    }
    attestation_payload["attestation_hash"] = compute_attestation_hash(attestation_payload)
    attestation_path = tmp_path / "attestation.json"
    attestation_path.write_text(json.dumps(attestation_payload), encoding="utf-8")
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", HostileClient)
    journal = tmp_path / "journal.sqlite"
    output = tmp_path / "validation.json"
    result = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "execute",
            "--mode",
            "validate-only",
            "--plan",
            str(pilot_manifest_path),
            "--authorization",
            str(auth_path),
            "--portal-attestation",
            str(attestation_path),
            "--confirm-plan-hash",
            plan["plan_hash"],
            "--journal",
            str(journal),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ready_for_paid_execution"] is True
    assert payload["metadata_client_constructed"] is True
    assert payload["paid_client_constructed"] is False
    assert payload["journal_created"] is False
    assert payload["timeseries_namespace_accessed"] is False
    assert not journal.exists()


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


@pytest.mark.integration
def test_coordinator_fake_25_request_lifecycle(pilot_manifest_path: Path, tmp_path: Path) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    requests = [AcquisitionRequest.model_validate(item) for item in plan["requests"]]
    now = data_module.datetime.now(data_module.UTC)
    auth: dict[str, object] = {
        "authorization_version": "1.0",
        "pilot_plan_hash": plan["plan_hash"],
        "source_manifest_hash": plan["bindings"]["source_manifest_hash"],
        "split_manifest_hash": plan["bindings"]["split_manifest_hash"],
        "acquisition_policy_hash": plan["bindings"]["acquisition_policy_hash"],
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "authorized_by": "test_operator",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
    }
    auth["authorization_hash"] = compute_authorization_hash(auth)
    auth_path = tmp_path / "authorization.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")

    class Paid:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def acquire_range(self, request: AcquisitionRequest) -> RawAcquisitionResult:
            self.calls.append(request.request_id)
            path = tmp_path / "raw" / f"{request.request_id}.dbn"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(request.request_id.encode())
            path.with_suffix(".dbn.sha256").write_text(sha256_of_file(path), encoding="utf-8")
            path.with_suffix(".dbn.json").write_text("{}", encoding="utf-8")
            return RawAcquisitionResult(
                request_id=request.request_id,
                raw_path=str(path),
                sha256=sha256_of_file(path),
                record_count=1,
            )

    class Lifecycle:
        def __init__(self) -> None:
            self.quality_ids: set[str] = set()

        def inspect(self, request, entry):
            return (
                bool(entry and entry.raw_path and Path(entry.raw_path).exists()),
                bool(entry and entry.normalized_path and Path(entry.normalized_path).exists()),
                request.request_id in self.quality_ids,
                False,
            )

        def normalize(self, request, raw):
            path = tmp_path / "normalized" / f"{request.request_id}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(Path(raw.raw_path).read_bytes())
            checksum = sha256_of_file(path)
            path.with_suffix(".parquet.sha256").write_text(checksum, encoding="utf-8")
            path.with_suffix(".parquet.json").write_text("{}", encoding="utf-8")
            return str(path), checksum, path.stat().st_size

        def quality(self, request, normalized_path):
            self.quality_ids.add(request.request_id)
            (tmp_path / "quality").mkdir(exist_ok=True)
            (tmp_path / "quality" / f"{request.request_id}.json").write_text(
                json.dumps({"status": "passed"}), encoding="utf-8"
            )
            return True

    paid = Paid()
    lifecycle = Lifecycle()
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        result = PilotExecutionCoordinator().execute_paid(
            requests=requests,
            config=load_pilot_config(Path(_PILOT_CONFIG)),
            plan_hash=plan["plan_hash"],
            plan_bindings=plan["bindings"],
            plan_metadata=data_module._pilot_plan_hash_metadata(plan),
            authorization_path=auth_path,
            authorization_hash=str(auth["authorization_hash"]),
            portal_attestation_hash="t" * 64,
            confirm_plan_hash=plan["plan_hash"],
            metadata_provider_factory=_ZeroCostMetadata,
            paid_provider_factory=lambda: paid,
            journal=journal,
            lifecycle=lifecycle,
            now=now,
        )
        assert len(journal.consumed_authorization_ids()) == 1

    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        resumed = PilotExecutionCoordinator().execute_paid(
            requests=requests,
            config=load_pilot_config(Path(_PILOT_CONFIG)),
            plan_hash=plan["plan_hash"],
            plan_bindings=plan["bindings"],
            plan_metadata=data_module._pilot_plan_hash_metadata(plan),
            authorization_path=auth_path,
            authorization_hash=str(auth["authorization_hash"]),
            portal_attestation_hash="t" * 64,
            confirm_plan_hash=plan["plan_hash"],
            metadata_provider_factory=_ZeroCostMetadata,
            paid_provider_factory=lambda: (_ for _ in ()).throw(AssertionError()),
            journal=journal,
            lifecycle=lifecycle,
            now=now,
        )

    assert result.requests_completed == 25
    assert result.paid_request_calls == 25
    assert resumed.requests_skipped == 25
    assert resumed.paid_request_calls == 0
    assert paid.calls == [request.request_id for request in requests]
    assert len(list((tmp_path / "raw").glob("*.dbn"))) == 25
    assert len(list((tmp_path / "normalized").glob("*.parquet"))) == 25
    assert len(list((tmp_path / "quality").glob("*.json"))) == 25
