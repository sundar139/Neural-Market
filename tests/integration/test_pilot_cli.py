import json
import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
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
from neuralmarket.data.acquisition.billing_reconciliation import build_reconciliation_artifact
from neuralmarket.data.acquisition.executor import (
    PilotExecutionCoordinator,
    PilotExecutionResult,
    RawAcquisitionResult,
    ValidationOnlyResult,
)
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.metadata_runner import (
    IsolatedMetadataResult,
    MetadataOperationEvent,
)
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
        endpoint = kwargs.get("only_endpoint")
        values = {"record-count": 10, "billable-size": 100, "cost": cost}
        return IsolatedMetadataResult(
            endpoint_values={endpoint: values[endpoint]} if endpoint else values,
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    return run


@pytest.mark.integration
@pytest.mark.parametrize(
    ("failed_endpoint", "resumed_calls"),
    [("billable-size", ["billable-size", "cost"]), ("cost", ["cost"])],
)
def test_pilot_prepare_resumes_only_failed_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failed_endpoint: str,
    resumed_calls: list[str],
) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    plan = tmp_path / "plan.json"
    calls: list[str] = []
    failing = True

    def isolated(**kwargs):
        nonlocal failing
        request = kwargs["request"]
        endpoint = kwargs["only_endpoint"]
        calls.append(endpoint)
        failed = failing and endpoint == failed_endpoint
        event = MetadataOperationEvent(
            run_id="run",
            request_index=1,
            request_count=25,
            request_id=request.request_id,
            dataset=request.dataset,
            schema_name=request.schema_name,
            session_date=request.session_date.isoformat() if request.session_date else None,
            endpoint=endpoint,
            attempt=kwargs["attempt"],
            started_at=datetime.now(UTC).isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            elapsed_seconds=0.01,
            outcome="failed" if failed else "succeeded",
            exception_class="ConnectionError" if failed else None,
            child_pid=1,
        )
        return IsolatedMetadataResult(
            endpoint_values={}
            if failed
            else {
                endpoint: {"record-count": 10, "billable-size": 100, "cost": "0.01001"}[endpoint]
            },
            events=[event],
            failure_type="ConnectionError" if failed else None,
            failed_endpoint=endpoint if failed else None,
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_run_isolated_metadata", isolated)
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")
    args = [
        "data",
        "pilot",
        "prepare",
        "--config",
        _PILOT_CONFIG,
        "--output",
        str(tmp_path / "report.json"),
        "--request-manifest",
        str(plan),
        "--checkpoint",
        str(checkpoint),
        "--max-requests",
        "1",
    ]
    assert runner.invoke(app, args).exit_code == 1
    failing = False
    calls.clear()
    assert runner.invoke(app, [*args, "--resume"]).exit_code == 0
    assert calls == resumed_calls


@pytest.mark.integration
def test_pilot_prepare_expired_checkpoint_repeats_all_endpoints(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    def isolated(**kwargs):
        endpoint = kwargs["only_endpoint"]
        calls.append(endpoint)
        return _isolated()(**kwargs)

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_run_isolated_metadata", isolated)
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")
    checkpoint = tmp_path / "checkpoint.json"
    args = [
        "data",
        "pilot",
        "prepare",
        "--config",
        _PILOT_CONFIG,
        "--output",
        str(tmp_path / "report.json"),
        "--request-manifest",
        str(tmp_path / "plan.json"),
        "--checkpoint",
        str(checkpoint),
        "--max-requests",
        "1",
    ]
    assert runner.invoke(app, args).exit_code == 0
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["updated_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")
    calls.clear()
    assert runner.invoke(app, [*args, "--resume"]).exit_code == 0
    assert calls == ["record-count", "billable-size", "cost"]


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


def _write_execution_inputs(plan: dict[str, Any], tmp_path: Path) -> tuple[Path, Path]:
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
    return auth_path, attestation_path


def _execute_args(
    *,
    plan_path: Path,
    plan_hash: str,
    auth_path: Path,
    attestation_path: Path,
    journal_path: Path,
    output_path: Path | None = None,
    mode: str = "paid",
) -> list[str]:
    args = [
        "data",
        "pilot",
        "execute",
        "--mode",
        mode,
        "--plan",
        str(plan_path),
        "--authorization",
        str(auth_path),
        "--portal-attestation",
        str(attestation_path),
        "--confirm-plan-hash",
        plan_hash,
        "--journal",
        str(journal_path),
    ]
    if output_path is not None:
        args.extend(["--output", str(output_path)])
    return args


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
def test_pilot_reconcile_billing_help() -> None:
    assert runner.invoke(app, ["data", "pilot", "reconcile-billing", "--help"]).exit_code == 0


@pytest.mark.integration
def test_pilot_reconcile_billing_cli_applies_supersession_without_provider(tmp_path: Path) -> None:
    journal_path = tmp_path / "journal.sqlite"
    journal = RequestJournal(journal_path)
    now = datetime.now(UTC).isoformat()
    journal.upsert(
        JournalEntry(
            request_id="request-1",
            request_hash="r" * 64,
            state="uncertain_billing",
            attempt_count=1,
            estimated_cost_usd="0.01",
            actual_billed_cost_usd=None,
            raw_path=None,
            raw_checksum=None,
            normalized_path=None,
            normalized_checksum=None,
            failure_category="provider_error",
            failure_message="paid historical provider operation failed",
            created_at=now,
            updated_at=now,
        )
    )
    assert journal.reserve_authorization(
        authorization_hash="a" * 64,
        plan_hash="p" * 64,
        execution_id="execution-1",
        reserved_at=now,
    )
    assert journal.consume_reserved_authorization(
        authorization_hash="a" * 64,
        execution_id="execution-1",
        consumed_at=now,
    )
    unknown = build_reconciliation_artifact(
        execution_id="execution-1",
        request_id="request-1",
        plan_hash="p" * 64,
        authorization_hash="a" * 64,
        portal_review_status="UNKNOWN",
        observed_usage_usd="UNKNOWN",
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="running",
        reviewed_at=now,
    )
    result = data_module.apply_billing_reconciliation(journal=journal, artifact=unknown)
    assert result.status == "ok"
    superseding = build_reconciliation_artifact(
        execution_id="execution-1",
        request_id="request-1",
        plan_hash="p" * 64,
        authorization_hash="a" * 64,
        portal_review_status="NOT_BILLED",
        observed_usage_usd="0.00",
        journal_state_before="uncertain_billing",
        execution_attempt_status_before="blocked_uncertain_billing",
        reviewed_at=now,
        supersedes_reconciliation_hash=unknown.artifact_hash,
        supersession_reason="operator obtained definitive portal nonbilling evidence",
        supersession_evidence_method="manual_databento_portal_review",
        supersession_sequence=2,
    )
    artifact_path = tmp_path / "not_billed.json"
    artifact_path.write_text(superseding.model_dump_json(), encoding="utf-8")
    output_path = tmp_path / "result.json"

    cli = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "reconcile-billing",
            "--journal",
            str(journal_path),
            "--reconciliation",
            str(artifact_path),
            "--output",
            str(output_path),
        ],
    )

    assert cli.exit_code == 0, cli.output
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["request_state_after"] == "retry_eligible_after_manual_nonbilling_confirmation"
    assert payload["new_authorization_required"] is True
    assert payload["paid_provider_constructed"] is False
    assert payload["metadata_calls"] == 0
    assert payload["downloaded_records"] == 0


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
def test_pilot_execute_paid_delegates_to_coordinator_once(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    calls = {"execute_paid": 0, "validate_only": 0}

    class SpyCoordinator:
        def validate_only(self, **kwargs: Any) -> ValidationOnlyResult:
            calls["validate_only"] += 1
            raise AssertionError("validate_only should not be called for paid mode")

        def execute_paid(self, **kwargs: Any) -> PilotExecutionResult:
            calls["execute_paid"] += 1
            return PilotExecutionResult(
                execution_id="e" * 32,
                plan_hash=plan["plan_hash"],
                authorization_hash="a" * 64,
                portal_attestation_hash="t" * 64,
                fresh_preflight_hash=plan["plan_hash"],
                requests_planned=25,
                requests_completed=25,
                requests_skipped=0,
                requests_failed=0,
                requests_uncertain=0,
                last_completed_request="done",
                blocking_request=None,
                blocking_state=None,
                safe_resume_possible=True,
                manual_action_required=False,
                estimated_total_cost="0.25025",
                raw_bytes=25,
                normalized_bytes=25,
                quality_summary={"passed": 25, "failed": 0},
                paid_provider_constructed=True,
                paid_request_calls=25,
                download_attempts=25,
                downloaded_records=25,
            )

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "paid_provider_readiness", lambda: SimpleNamespace(ready=True))
    monkeypatch.setattr(data_module, "_pilot_execution_coordinator", SpyCoordinator)
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=tmp_path / "journal.sqlite",
        ),
    )
    assert result.exit_code == 0, result.output
    assert calls == {"execute_paid": 1, "validate_only": 0}


@pytest.mark.integration
def test_pilot_execute_validate_only_delegates_without_paid_factory_or_journal(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    calls = {"execute_paid": 0, "validate_only": 0, "paid_factory": 0}

    class SpyCoordinator:
        def validate_only(self, **kwargs: Any) -> ValidationOnlyResult:
            calls["validate_only"] += 1
            return ValidationOnlyResult(
                ready_for_paid_execution=True,
                fresh_preflight_hash=plan["plan_hash"],
                estimated_total_cost="0.25025",
                largest_request_cost="0.01001",
            )

        def execute_paid(self, **kwargs: Any) -> PilotExecutionResult:
            calls["execute_paid"] += 1
            raise AssertionError("execute_paid should not be called for validate-only")

    def paid_factory(root: Path):
        calls["paid_factory"] += 1
        raise AssertionError("paid factory should not be built")

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_pilot_execution_coordinator", SpyCoordinator)
    monkeypatch.setattr(data_module, "_pilot_paid_provider_factory", paid_factory)
    journal = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal,
            mode="validate-only",
        ),
    )
    assert result.exit_code == 0, result.output
    assert calls == {"execute_paid": 0, "validate_only": 1, "paid_factory": 0}
    assert not journal.exists()


@pytest.mark.integration
def test_pilot_execute_source_has_no_direct_guard_execute_call() -> None:
    assert ".guard_execute(" not in Path(data_module.__file__).read_text(encoding="utf-8")


class _FakePaid:
    def __init__(self, tmp_path: Path, journal_path: Path | None = None) -> None:
        self.tmp_path = tmp_path
        self.journal_path = journal_path
        self.calls: list[str] = []
        self.consumed_before_first_call = False

    def acquire_range(self, request: AcquisitionRequest) -> RawAcquisitionResult:
        if not self.calls and self.journal_path is not None:
            with sqlite3.connect(self.journal_path) as conn:
                state = conn.execute("SELECT state FROM authorization_reservations").fetchone()
            self.consumed_before_first_call = state == ("consumed",)
        self.calls.append(request.request_id)
        path = self.tmp_path / "raw" / f"{request.request_id}.dbn"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(request.request_id.encode())
        return RawAcquisitionResult(
            request_id=request.request_id,
            raw_path=str(path),
            sha256=sha256_of_file(path),
            record_count=1,
        )


class _FakeLifecycle:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.quality_ids: set[str] = set()

    def inspect(self, request, entry):
        return (
            bool(entry and entry.raw_path and Path(entry.raw_path).exists()),
            bool(entry and entry.normalized_path and Path(entry.normalized_path).exists()),
            request.request_id in self.quality_ids,
            False,
        )

    def normalize(self, request, raw):
        path = self.tmp_path / "normalized" / f"{request.request_id}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Path(raw.raw_path).read_bytes())
        checksum = sha256_of_file(path)
        return str(path), checksum, path.stat().st_size

    def quality(self, request, normalized_path):
        self.quality_ids.add(request.request_id)
        (self.tmp_path / "quality").mkdir(exist_ok=True)
        (self.tmp_path / "quality" / f"{request.request_id}.json").write_text(
            json.dumps({"status": "passed"}), encoding="utf-8"
        )
        return True


@pytest.mark.integration
def test_pilot_execute_cli_fake_paid_lifecycle_and_dry_resume(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    journal = tmp_path / "journal.sqlite"
    paid = _FakePaid(tmp_path, journal)
    lifecycle = _FakeLifecycle(tmp_path)
    constructions = 0

    def paid_factory(root: Path):
        def build():
            nonlocal constructions
            constructions += 1
            return paid

        return build

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "paid_provider_readiness", lambda: SimpleNamespace(ready=True))
    monkeypatch.setattr(data_module, "_pilot_metadata_provider_factory", _ZeroCostMetadata)
    monkeypatch.setattr(data_module, "_pilot_paid_provider_factory", paid_factory)
    monkeypatch.setattr(data_module, "_pilot_lifecycle", lambda root: lifecycle)
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal,
            output_path=tmp_path / "paid.json",
        ),
    )
    assert result.exit_code == 0, result.output
    payload = json.loads((tmp_path / "paid.json").read_text(encoding="utf-8"))
    assert payload["requests_planned"] == 25
    assert payload["requests_completed"] == 25
    assert payload["paid_provider_constructed"] is True
    assert payload["paid_request_calls"] == 25
    assert constructions == 1
    assert paid.consumed_before_first_call is True
    assert len(list((tmp_path / "raw").glob("*.dbn"))) == 25
    assert len(list((tmp_path / "normalized").glob("*.parquet"))) == 25
    assert len(list((tmp_path / "quality").glob("*.json"))) == 25

    paid.calls.clear()
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal,
            output_path=tmp_path / "resume.json",
        ),
    )
    assert result.exit_code == 0, result.output
    resumed = json.loads((tmp_path / "resume.json").read_text(encoding="utf-8"))
    assert resumed["requests_skipped"] == 25
    assert resumed["paid_provider_constructed"] is False
    assert resumed["paid_request_calls"] == 0
    assert paid.calls == []


@pytest.mark.integration
def test_pilot_execute_fresh_preflight_failure_creates_no_journal_or_paid_provider(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    journal = tmp_path / "journal.sqlite"
    paid_factory_calls = 0

    class FailingMetadata(_ZeroCostMetadata):
        def get_cost(self, **kwargs: Any) -> float:
            raise RuntimeError("metadata failed")

    def paid_factory(root: Path):
        nonlocal paid_factory_calls
        paid_factory_calls += 1
        raise AssertionError("paid provider factory must not be requested")

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "paid_provider_readiness", lambda: SimpleNamespace(ready=True))
    monkeypatch.setattr(data_module, "_pilot_metadata_provider_factory", FailingMetadata)
    monkeypatch.setattr(data_module, "_pilot_paid_provider_factory", paid_factory)
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal,
        ),
    )
    assert result.exit_code != 0
    assert not journal.exists()
    assert paid_factory_calls == 0


@pytest.mark.integration
def test_pilot_execute_provider_construction_failure_releases_reservation(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    journal = tmp_path / "journal.sqlite"
    attempts = 0

    def paid_factory(root: Path):
        def build():
            nonlocal attempts
            attempts += 1
            raise RuntimeError("construction failed")

        return build

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "paid_provider_readiness", lambda: SimpleNamespace(ready=True))
    monkeypatch.setattr(data_module, "_pilot_metadata_provider_factory", _ZeroCostMetadata)
    monkeypatch.setattr(data_module, "_pilot_paid_provider_factory", paid_factory)
    monkeypatch.setattr(data_module, "_pilot_lifecycle", lambda root: _FakeLifecycle(tmp_path))
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal,
        ),
    )
    assert result.exit_code != 0
    assert attempts == 1
    with sqlite3.connect(journal) as conn:
        reservations = conn.execute("SELECT state FROM authorization_reservations").fetchall()
        consumed = conn.execute("SELECT * FROM consumed_authorizations").fetchall()
        request_started = conn.execute(
            "SELECT count(*) FROM requests WHERE state = 'request_started'"
        ).fetchone()[0]
    assert reservations == []
    assert consumed == []
    assert request_started == 0


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
    journal_path = tmp_path / "journal.sqlite"
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
        journal_factory=lambda: RequestJournal(journal_path),
        lifecycle=lifecycle,
        now=now,
    )
    with RequestJournal(journal_path) as journal:
        assert len(journal.consumed_authorization_ids()) == 1

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
        journal_factory=lambda: RequestJournal(journal_path),
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
