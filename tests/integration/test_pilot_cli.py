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
    build_remaining_scope,
    compute_authorization_hash,
)
from neuralmarket.data.acquisition.billing_reconciliation import build_reconciliation_artifact
from neuralmarket.data.acquisition.executor import (
    ExecutorGuardError,
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


def _integration_scope(plan: dict[str, Any]) -> Any:
    """Build the real remaining scope: every planned request but the first."""
    from neuralmarket.data.acquisition.authorization import build_remaining_scope

    requests = plan["requests"]
    return build_remaining_scope(
        source_plan_hash=plan["plan_hash"],
        completed_request_ids=[requests[0]["request_id"]],
        completed_request_hashes=[requests[0]["request_hash"]],
        remaining_request_ids=[item["request_id"] for item in requests[1:]],
        remaining_request_hashes=[item["request_hash"] for item in requests[1:]],
    )


def _write_scope_file(plan: dict[str, Any], tmp_path: Path) -> tuple[Path, str]:
    scope = _integration_scope(plan)
    path = tmp_path / "scope.json"
    path.write_text(scope.model_dump_json(), encoding="utf-8")
    return path, sha256_of_file(path)


def _seed_journal(journal_path: Path, plan: dict[str, Any]) -> None:
    """Seed a RequestJournal whose states match the fixture execution scope."""
    from unittest.mock import Mock

    from neuralmarket.data.acquisition.executor import PilotExecutor
    from neuralmarket.data.acquisition.journal import RequestJournal

    scope = _integration_scope(plan)
    excluded = set(scope.completed_request_ids)
    with RequestJournal(journal_path) as journal:
        executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
        executor.prepare([AcquisitionRequest.model_validate(item) for item in plan["requests"]])
        for item in plan["requests"]:
            if item["request_id"] not in excluded:
                executor.transition(item["request_id"], "preflight_validated")
        for request_id in excluded:
            journal.connection.execute(
                "UPDATE requests SET state = 'quality_validated' WHERE request_id = ?",
                (request_id,),
            )
        journal.connection.commit()


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


def _fallback_isolated(cbbo_cost: str):
    """Succeed everywhere except the 2nd cbbo-1m cost, which fails with HTTP 504."""
    seen_cbbo: list[str] = []

    def run(**kwargs):
        request = kwargs["request"]
        endpoint = kwargs["only_endpoint"]
        schema = request.schema_name
        values = {
            "record-count": 10,
            "billable-size": 5209600 if schema == "cbbo-1m" else 100,
            "cost": cbbo_cost if schema == "cbbo-1m" else "0.01001",
        }
        fail = False
        if endpoint == "cost" and schema == "cbbo-1m":
            if request.request_id not in seen_cbbo:
                seen_cbbo.append(request.request_id)
            fail = len(seen_cbbo) >= 2 and request.request_id == seen_cbbo[1]
        if fail:
            event = MetadataOperationEvent(
                run_id="run",
                request_index=1,
                request_count=25,
                request_id=request.request_id,
                dataset=request.dataset,
                schema_name=request.schema_name,
                session_date=request.session_date.isoformat() if request.session_date else None,
                endpoint="cost",
                attempt=kwargs["attempt"],
                started_at=datetime.now(UTC).isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=60.0,
                outcome="failed",
                exception_class="BentoServerError",
                http_status=504,
                child_pid=1,
            )
            return IsolatedMetadataResult(
                endpoint_values={},
                events=[event],
                failure_type="BentoServerError",
                failed_endpoint="cost",
                child_pid=1,
                child_exitcode=0,
                child_joined=True,
                remaining_children=0,
            )
        return IsolatedMetadataResult(
            endpoint_values={endpoint: values[endpoint]},
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    return run


@pytest.mark.integration
def test_pilot_prepare_derived_cost_fallback_on_504(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from neuralmarket.data.acquisition.cost_estimation import (
        ACQUISITION_FEED_MODE,
        parse_unit_price_snapshot,
    )

    cbbo_cost = str(Decimal(5209600) * Decimal("2.0") / Decimal(2**30))

    def loader(dataset: str):
        return parse_unit_price_snapshot(
            [{"mode": ACQUISITION_FEED_MODE, "schemas": {"cbbo-1m": "2.0"}}],
            dataset=dataset,
            feed_mode=ACQUISITION_FEED_MODE,
            databento_client_version="0.81.0",
            retrieved_at_utc=datetime.now(UTC).isoformat(),
            expires_at_utc=(datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
        )

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", lambda: _Client())
    monkeypatch.setattr(data_module, "_run_isolated_metadata", _fallback_isolated(cbbo_cost))
    monkeypatch.setattr(data_module, "_pilot_unit_price_snapshot_loader", loader)
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")

    output_path = tmp_path / "preflight.json"
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
            str(tmp_path / "plan.json"),
            "--checkpoint",
            str(tmp_path / "checkpoint.local.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(output_path.read_text(encoding="utf-8"))
    summary = report["cost_source_summary"]
    assert summary["derived_cost_count"] == 1
    assert summary["provider_cost_count"] == 24
    assert len(summary["fallback_request_ids"]) == 1
    assert len(summary["unit_price_snapshot_hashes"]) == 1
    assert summary["pilot_cross_validation_sample_count"] == 1
    assert summary["full_acquisition_minimum_sample_count"] == 2
    assert Decimal(summary["conservative_total_usd"]) > Decimal(summary["raw_total_usd"])


@pytest.mark.integration
def test_pilot_prepare_blocks_fallback_on_403(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def isolated(**kwargs):
        request = kwargs["request"]
        endpoint = kwargs["only_endpoint"]
        if endpoint == "cost" and request.schema_name == "cbbo-1m":
            event = MetadataOperationEvent(
                run_id="run",
                request_index=1,
                request_count=25,
                request_id=request.request_id,
                dataset=request.dataset,
                schema_name=request.schema_name,
                session_date=request.session_date.isoformat() if request.session_date else None,
                endpoint="cost",
                attempt=kwargs["attempt"],
                started_at=datetime.now(UTC).isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=1.0,
                outcome="failed",
                exception_class="BentoClientError",
                http_status=403,
                child_pid=1,
            )
            return IsolatedMetadataResult(
                endpoint_values={},
                events=[event],
                failure_type="BentoClientError",
                failed_endpoint="cost",
                child_pid=1,
                child_exitcode=0,
                child_joined=True,
                remaining_children=0,
            )
        return _isolated()(**kwargs)

    loader_calls = {"n": 0}

    def loader(dataset: str):
        loader_calls["n"] += 1
        raise AssertionError("snapshot must not load for a prohibited failure")

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", lambda: _Client())
    monkeypatch.setattr(data_module, "_run_isolated_metadata", isolated)
    monkeypatch.setattr(data_module, "_pilot_unit_price_snapshot_loader", loader)
    monkeypatch.setenv("DATABENTO_API_KEY", "test-only")

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
            "--checkpoint",
            str(tmp_path / "checkpoint.local.json"),
        ],
    )
    assert result.exit_code == 1
    assert loader_calls["n"] == 0


@pytest.mark.integration
def test_pilot_prepare_stale_checkpoint_resume_is_fail_closed_and_authorizable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import hashlib

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

    # Make the checkpoint stale (past the 30-minute freshness window).
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["updated_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")
    stale_bytes = checkpoint.read_bytes()
    good_hash = hashlib.sha256(stale_bytes).hexdigest()

    # Ordinary --resume on a stale checkpoint fails closed; no silent restart.
    calls.clear()
    result = runner.invoke(app, [*args, "--resume"])
    assert result.exit_code == 1
    assert calls == []
    assert checkpoint.read_bytes() == stale_bytes

    # Wrong authorization hash fails closed before any provider activity.
    result = runner.invoke(app, [*args, "--resume", "--allow-stale-checkpoint-sha256", "0" * 64])
    assert result.exit_code == 1
    assert calls == []
    assert checkpoint.read_bytes() == stale_bytes

    # The override requires --resume.
    result = runner.invoke(app, [*args, "--allow-stale-checkpoint-sha256", good_hash])
    assert result.exit_code != 0

    # Correct authorization hash resumes the exact stale checkpoint.
    completed_before = len(payload["completed_estimates"])
    result = runner.invoke(app, [*args, "--resume", "--allow-stale-checkpoint-sha256", good_hash])
    assert result.exit_code == 0
    resumed = json.loads(checkpoint.read_text(encoding="utf-8"))
    # Completed work was preserved, not reset to zero.
    assert len(resumed["completed_estimates"]) >= completed_before


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
    _scope = _integration_scope(plan)
    auth_payload: dict[str, object] = {
        "authorization_version": "2.0",
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
        "remaining_scope_hash": _scope.scope_hash,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_source_evidence_sha256": "e" * 64,
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
    _write_scope_file(plan, tmp_path)
    return auth_path, attestation_path


def _write_fake_preflight_evidence(plan_path: Path, auth_path: Path, tmp_path: Path) -> Path:
    """Write complete, hash-bound offline-preflight evidence and rebind the authorization."""
    from neuralmarket.data.acquisition.live_cost_recheck import _provider_response_sha256

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scope = _integration_scope(plan)
    by_id = {item["request_id"]: item for item in plan["requests"]}
    now = data_module.datetime.now(data_module.UTC)
    quotes = []
    for request_id in scope.remaining_request_ids:
        request = AcquisitionRequest.model_validate(by_id[request_id])
        cost = "0.00000001"
        record_count = 1
        billable_size = 1
        quotes.append(
            {
                "request_id": request_id,
                "dataset": request.dataset,
                "schema": request.schema_name,
                "symbols": list(request.symbols),
                "stype_in": request.stype_in,
                "start": request.start.isoformat(),
                "end": request.end_exclusive.isoformat(),
                "status": "quoted",
                "cost_usd": cost,
                "attempts": 1,
                "last_failure_class": None,
                "last_http_status": None,
                "remaining_children": 0,
                "request_specification_sha256": request.specification_hash,
                "quote_source": "provider_response",
                "provider_response_sha256": _provider_response_sha256(
                    request_id, request.specification_hash, cost, record_count, billable_size
                ),
                "provider_observed_at": now.isoformat(),
                "record_count": record_count,
                "billable_size_bytes": billable_size,
            }
        )
    total = str(sum(Decimal(quote["cost_usd"]) for quote in quotes))
    largest = max(Decimal(quote["cost_usd"]) for quote in quotes)
    payload: dict[str, Any] = {
        "schema_version": "pilot-cost-recheck-v2",
        "status": "complete",
        "authorization_ready": True,
        "purchase_authorized": False,
        "observed_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
        "checkpoint_sha256": "c" * 64,
        "plan_hash": plan["plan_hash"],
        "request_manifest_sha256": sha256_of_file(plan_path),
        "quotes": quotes,
        "provider_quote_count": len(quotes),
        "unavailable_quote_count": 0,
        "fresh_raw_total_usd": total,
        "fresh_conservative_total_usd": total,
        "prior_raw_total_usd": total,
        "prior_conservative_total_usd": total,
        "absolute_delta_usd": "0",
        "relative_delta": "0",
        "largest_request_usd": str(largest),
        "schema_validation": {},
        "attempt_history": [],
    }
    evidence_path = tmp_path / "preflight_evidence.json"
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    evidence_sha = sha256_of_file(evidence_path)
    auth_payload = json.loads(auth_path.read_text(encoding="utf-8"))
    auth_payload["cost_evidence"]["evidence_sha256"] = evidence_sha
    auth_payload["authorization_hash"] = compute_authorization_hash(auth_payload)
    auth_path.write_text(json.dumps(auth_payload, indent=2, sort_keys=True), encoding="utf-8")
    return evidence_path


def _execute_args(
    *,
    plan_path: Path,
    plan_hash: str,
    auth_path: Path,
    attestation_path: Path,
    journal_path: Path,
    output_path: Path | None = None,
    mode: str = "paid",
    scope_path: Path | None = None,
    frozen_config: str | None = _PILOT_CONFIG,
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
    if mode == "paid" and frozen_config is not None:
        args.extend(["--frozen-pilot-config", frozen_config])
    if mode == "paid":
        args.extend(
            [
                "--preflight-evidence",
                str(_write_fake_preflight_evidence(plan_path, auth_path, auth_path.parent)),
            ]
        )
    scope_path = scope_path or auth_path.parent / "scope.json"
    if scope_path.exists():
        args.extend(
            [
                "--remaining-scope",
                str(scope_path),
                "--expected-remaining-scope-sha256",
                sha256_of_file(scope_path),
            ]
        )
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
def test_prepare_recovery_plan_cli_is_offline_read_only_and_one_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent_hash = (
        "9654fe1c2dfe98946560e27c6f51f110"  # pragma: allowlist secret
        "038613060461fdf75936edf1a7d0ae77"  # pragma: allowlist secret
    )
    authorization_hash = (
        "db2cde39f5a5e96c7301b9d289fc0c8"  # pragma: allowlist secret
        "e5412b60d2b69faae30f12a7b99dd885e"  # pragma: allowlist secret
    )
    execution_id = "132078783c31dcab22cb90d95c967c9c"  # pragma: allowlist secret
    request_id = "2750995e515e4f1a"  # pragma: allowlist secret
    request_hash = (
        "b8b0a410ace7a8a5d710b8bc04e37560"  # pragma: allowlist secret
        "ab7b08ceb9aa316a4a3334b6b0980d7a"  # pragma: allowlist secret
    )
    now = datetime.now(UTC).isoformat()
    journal_path = tmp_path / "journal.sqlite"
    with RequestJournal(journal_path) as journal:
        journal.upsert(
            JournalEntry(
                request_id=request_id,
                request_hash=request_hash,
                state="uncertain_billing",
                attempt_count=1,
                estimated_cost_usd="0.000112652779",
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
            authorization_hash=authorization_hash,
            plan_hash=parent_hash,
            execution_id=execution_id,
            reserved_at=now,
        )
        assert journal.consume_reserved_authorization(
            authorization_hash=authorization_hash,
            execution_id=execution_id,
            consumed_at=now,
        )
        unknown = build_reconciliation_artifact(
            execution_id=execution_id,
            request_id=request_id,
            plan_hash=parent_hash,
            authorization_hash=authorization_hash,
            portal_review_status="UNKNOWN",
            observed_usage_usd="UNKNOWN",
            journal_state_before="uncertain_billing",
            execution_attempt_status_before="running",
            reviewed_at=now,
        )
        data_module.apply_billing_reconciliation(journal=journal, artifact=unknown)
        not_billed = build_reconciliation_artifact(
            execution_id=execution_id,
            request_id=request_id,
            plan_hash=parent_hash,
            authorization_hash=authorization_hash,
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
        data_module.apply_billing_reconciliation(journal=journal, artifact=not_billed)

    reconciliation_path = tmp_path / "not_billed.json"
    reconciliation_path.write_text(not_billed.model_dump_json(indent=2), encoding="utf-8")
    output_path = tmp_path / "pilot_recovery_plan.local.json"
    before = {path.name: path.read_bytes() for path in tmp_path.glob("journal.sqlite*")}
    monkeypatch.setattr(
        data_module,
        "_raw_databento_client",
        lambda: (_ for _ in ()).throw(AssertionError("Databento construction forbidden")),
    )
    monkeypatch.setattr(
        data_module,
        "_load_dotenv",
        lambda root: (_ for _ in ()).throw(AssertionError("dotenv load forbidden")),
    )

    cli = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "prepare-recovery-plan",
            "--request-id",
            request_id,
            "--journal",
            str(journal_path),
            "--reconciliation",
            str(reconciliation_path),
            "--output",
            str(output_path),
        ],
    )

    assert cli.exit_code == 0, cli.output
    recovery = json.loads(output_path.read_text(encoding="utf-8"))
    after = {path.name: path.read_bytes() for path in tmp_path.glob("journal.sqlite*")}
    assert recovery["plan_hash"] != parent_hash
    assert recovery["request_count"] == 1
    assert [request["request_id"] for request in recovery["requests"]] == [request_id]
    assert recovery["recovery"]["parent_plan_hash"] == parent_hash
    assert recovery["recovery"]["prior_execution_id"] == execution_id
    assert recovery["recovery"]["prior_authorization_hash"] == authorization_hash
    assert recovery["recovery"]["reconciliation_artifact_hash"] == not_billed.artifact_hash
    assert after == before
    with sqlite3.connect(journal_path) as connection:
        consumed = connection.execute(
            "SELECT authorization_hash, execution_id FROM consumed_authorizations "
            "WHERE plan_hash = ?",
            (parent_hash,),
        ).fetchone()
    assert consumed == (authorization_hash, execution_id)


@pytest.mark.integration
@pytest.mark.parametrize(
    "output_name", ["journal.sqlite", "journal.sqlite-wal", "journal.sqlite-shm"]
)
def test_prepare_recovery_plan_cli_rejects_journal_output_collision(
    tmp_path: Path, output_name: str
) -> None:
    journal_path = tmp_path / "journal.sqlite"
    cli = runner.invoke(
        app,
        [
            "data",
            "pilot",
            "prepare-recovery-plan",
            "--request-id",
            "request",
            "--journal",
            str(journal_path),
            "--reconciliation",
            str(tmp_path / "reconciliation.json"),
            "--output",
            str(tmp_path / output_name),
        ],
    )

    assert cli.exit_code == 1
    assert not journal_path.exists()


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
    scope_path, scope_sha = _write_scope_file(plan, tmp_path)
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
            "--frozen-pilot-config",
            _PILOT_CONFIG,
            "--remaining-scope",
            str(scope_path),
            "--expected-remaining-scope-sha256",
            scope_sha,
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
            "--frozen-pilot-config",
            _PILOT_CONFIG,
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
            "--frozen-pilot-config",
            _PILOT_CONFIG,
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
        "authorization_version": "2.0",
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
        "remaining_scope_hash": _integration_scope(plan).scope_hash,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_source_evidence_sha256": "e" * 64,
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
    scope_path, scope_sha = _write_scope_file(plan, tmp_path)
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "_raw_databento_client", HostileClient)
    journal = tmp_path / "journal.sqlite"
    _seed_journal(journal, plan)
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
            "--frozen-pilot-config",
            _PILOT_CONFIG,
            "--remaining-scope",
            str(scope_path),
            "--expected-remaining-scope-sha256",
            scope_sha,
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


@pytest.mark.integration
def test_pilot_execute_paid_delegates_to_coordinator_once(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    _seed_journal(tmp_path / "journal.sqlite", plan)
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
    _seed_journal(tmp_path / "journal.sqlite", plan)
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
    _seed_journal(journal, plan)
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
    # 24 completed this run plus the pre-seeded settled request.
    assert payload["requests_completed"] == 25
    assert payload["paid_provider_constructed"] is True
    assert payload["paid_request_calls"] == 24
    assert constructions == 1
    assert paid.consumed_before_first_call is True
    assert len(list((tmp_path / "raw").glob("*.dbn"))) == 24
    assert len(list((tmp_path / "normalized").glob("*.parquet"))) == 24
    assert len(list((tmp_path / "quality").glob("*.json"))) == 24

    # A stale-scope resume after full completion fails closed: the journal no
    # longer derives the historical 24-request scope, so nothing may re-run.
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
    assert result.exit_code == 1
    assert "expected 0, got 24" in result.output
    assert paid.calls == []


@pytest.mark.integration
def test_pilot_execute_incomplete_preflight_evidence_creates_no_journal_or_paid_provider(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Incomplete offline preflight evidence fails closed before any provider or journal."""
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    journal = tmp_path / "journal.sqlite"
    _seed_journal(journal, plan)
    paid_factory_calls = 0

    def metadata_factory():
        raise AssertionError("metadata provider must not be constructed on bad evidence")

    def paid_factory(root: Path):
        nonlocal paid_factory_calls
        paid_factory_calls += 1
        raise AssertionError("paid provider factory must not be requested")

    args = _execute_args(
        plan_path=pilot_manifest_path,
        plan_hash=plan["plan_hash"],
        auth_path=auth_path,
        attestation_path=attestation_path,
        journal_path=journal,
    )
    evidence_path = Path(args[args.index("--preflight-evidence") + 1])
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    for quote in payload["quotes"]:
        quote.pop("record_count", None)
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(data_module, "paid_provider_readiness", lambda: SimpleNamespace(ready=True))
    monkeypatch.setattr(data_module, "_pilot_metadata_provider_factory", metadata_factory)
    monkeypatch.setattr(data_module, "_pilot_paid_provider_factory", paid_factory)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "generate a fresh complete recheck" in result.output
    with sqlite3.connect(journal) as conn:
        assert conn.execute("SELECT COUNT(*) FROM consumed_authorizations").fetchone()[0] == 0
    assert paid_factory_calls == 0


@pytest.mark.integration
def test_pilot_execute_provider_construction_failure_releases_reservation(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    journal = tmp_path / "journal.sqlite"
    _seed_journal(journal, plan)
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
        "authorization_version": "2.0",
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
        "remaining_scope_hash": _integration_scope(plan).scope_hash,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_source_evidence_sha256": "e" * 64,
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
    _seed_journal(journal_path, plan)
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
        execution_scope=_integration_scope(plan),
    )
    with RequestJournal(journal_path) as journal:
        assert len(journal.consumed_authorization_ids()) == 1

    # 24 completed this run plus the pre-seeded settled request.
    assert result.requests_completed == 25
    assert result.paid_request_calls == 24
    assert paid.calls == [request.request_id for request in requests[1:]]
    assert len(list((tmp_path / "raw").glob("*.dbn"))) == 24
    assert len(list((tmp_path / "normalized").glob("*.parquet"))) == 24
    assert len(list((tmp_path / "quality").glob("*.json"))) == 24

    # A stale-scope resume after completion fails closed: the journal now
    # derives zero eligible requests, so the historical scope must not re-run.
    with pytest.raises(ExecutorGuardError, match="scope_eligible_set_mismatch") as exc:
        PilotExecutionCoordinator().execute_paid(
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
            execution_scope=_integration_scope(plan),
        )
    assert exc.value.reason == "invalid_execution_scope"
    assert paid.calls == [request.request_id for request in requests[1:]]

    # The current-state scope (empty: nothing left eligible) executes safely
    # with zero paid calls.
    empty_scope = build_remaining_scope(
        source_plan_hash=plan["plan_hash"],
        completed_request_ids=[request.request_id for request in requests],
        completed_request_hashes=[request.request_hash for request in requests],
        remaining_request_ids=[],
        remaining_request_hashes=[],
    )
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
        execution_scope=empty_scope,
    )
    assert resumed.paid_request_calls == 0
    assert resumed.requests_completed == 25  # nothing new to do; prior state persists
    assert resumed.paid_provider_constructed is False
    assert paid.calls == [request.request_id for request in requests[1:]]


@pytest.mark.integration
def test_coordinator_executes_exact_current_scope_with_excluded_states(
    pilot_manifest_path: Path, tmp_path: Path
) -> None:
    """Current production shape: 20 scoped requests plus excluded canonical states.

    4 quality-validated and 1 uncertain-billing excluded canonical requests.
    """
    from unittest.mock import Mock

    from neuralmarket.data.acquisition.estimation import MetadataEstimate
    from neuralmarket.data.acquisition.executor import PilotExecutor

    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    requests = [AcquisitionRequest.model_validate(item) for item in plan["requests"]]
    now = data_module.datetime.now(data_module.UTC)
    quality = requests[:4]
    uncertain = requests[4]
    scoped = requests[5:]
    assert len(scoped) == 20

    def _scope_for(remaining: list[AcquisitionRequest]) -> Any:
        completed = [r for r in requests if r not in remaining]
        return build_remaining_scope(
            source_plan_hash=plan["plan_hash"],
            completed_request_ids=[r.request_id for r in completed],
            completed_request_hashes=[r.request_hash for r in completed],
            remaining_request_ids=[r.request_id for r in remaining],
            remaining_request_hashes=[r.request_hash for r in remaining],
        )

    def _seed(journal_path: Path) -> None:
        if journal_path.exists():
            journal_path.unlink()
        with RequestJournal(journal_path) as journal:
            executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
            executor.prepare(requests)
            for request in requests:
                executor.transition(request.request_id, "preflight_validated")
            for request in quality:
                journal.connection.execute(
                    "UPDATE requests SET state = 'quality_validated' WHERE request_id = ?",
                    (request.request_id,),
                )
            journal.connection.execute(
                "UPDATE requests SET state = 'uncertain_billing' WHERE request_id = ?",
                (uncertain.request_id,),
            )
            journal.connection.commit()

    valid_scope = _scope_for(scoped)
    auth: dict[str, object] = {
        "authorization_version": "2.0",
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
        "remaining_scope_hash": valid_scope.scope_hash,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        },
        "portal_source_evidence_sha256": "e" * 64,
    }
    auth["authorization_hash"] = compute_authorization_hash(auth)
    auth_path = tmp_path / "authorization.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")

    estimates = [
        MetadataEstimate(
            dataset=request.dataset,
            schema=request.schema_name,
            symbol=request.symbols[0],
            stype_in=request.stype_in,
            window_start=request.start,
            window_end=request.end_exclusive,
            record_count=10,
            billable_size_bytes=1000,
            cost_usd=Decimal("0.01"),
            retries=0,
        )
        for request in scoped
    ]

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

    def execute_with(scope: Any, journal_path_arg: Path) -> PilotExecutionResult:
        return PilotExecutionCoordinator().execute_paid(
            requests=requests,
            config=load_pilot_config(Path(_PILOT_CONFIG)),
            plan_hash=plan["plan_hash"],
            plan_bindings=plan["bindings"],
            plan_metadata=data_module._pilot_plan_hash_metadata(plan),
            authorization_path=auth_path,
            authorization_hash=str(auth["authorization_hash"]),
            portal_attestation_hash="t" * 64,
            confirm_plan_hash=plan["plan_hash"],
            metadata_provider_factory=lambda: (_ for _ in ()).throw(
                AssertionError("metadata provider must not be constructed for offline preflight")
            ),
            paid_provider_factory=lambda: paid,
            journal_factory=lambda: RequestJournal(journal_path_arg),
            lifecycle=lifecycle,
            now=now,
            execution_scope=scope,
            preflight_estimates=estimates,
        )

    journal_path = tmp_path / "journal.sqlite"
    _seed(journal_path)
    result = execute_with(valid_scope, journal_path)
    assert result.paid_provider_constructed is True
    assert result.paid_request_calls == 20
    assert paid.calls == [request.request_id for request in scoped]
    with RequestJournal(journal_path) as journal:
        assert journal.get(uncertain.request_id).state == "uncertain_billing"  # type: ignore[union-attr]
        assert journal.get(quality[0].request_id).state == "quality_validated"  # type: ignore[union-attr]
        assert len(journal.consumed_authorization_ids()) == 1

    # Reintroducing any excluded request, dropping one eligible request, or an
    # arbitrary same-sized subset all fail before any provider construction.
    invalid_scopes = [
        _scope_for([*scoped, quality[0]]),  # quality-validated reintroduced
        _scope_for([*scoped, uncertain]),  # uncertain-billing reintroduced
        _scope_for(scoped[:-1]),  # 19 of 20 eligible
        _scope_for([*scoped[1:], quality[0]]),  # arbitrary same-sized subset
    ]
    invalid_path = tmp_path / "invalid_journal.sqlite"
    for bad_scope in invalid_scopes:
        _seed(invalid_path)
        with pytest.raises(ExecutorGuardError) as exc:
            execute_with(bad_scope, invalid_path)
        assert exc.value.reason == "invalid_execution_scope"
    assert paid.calls == [request.request_id for request in scoped]


@pytest.mark.integration
def test_pilot_execute_help_documents_the_scope_arguments() -> None:
    result = runner.invoke(app, ["data", "pilot", "execute", "--help"])
    assert result.exit_code == 0
    # Typer truncates long option names in the help table, so match the prefix.
    collapsed = " ".join(result.output.split())
    assert "--remaining-scope" in collapsed
    assert "--expected-remaining-scope" in collapsed


@pytest.mark.integration
def test_pilot_execute_paid_requires_a_remaining_scope(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Paid execution without a scope stops before credentials or a provider."""
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not be loaded without a scope")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    journal_path = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal_path,
            scope_path=tmp_path / "absent.json",
        ),
    )
    assert result.exit_code != 0
    assert "remaining-scope" in result.output
    assert not journal_path.exists()


@pytest.mark.integration
def test_pilot_execute_rejects_scope_sha_mismatch_before_provider(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not be loaded on a scope mismatch")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    journal_path = tmp_path / "journal.sqlite"
    args = _execute_args(
        plan_path=pilot_manifest_path,
        plan_hash=plan["plan_hash"],
        auth_path=auth_path,
        attestation_path=attestation_path,
        journal_path=journal_path,
    )
    args[args.index("--expected-remaining-scope-sha256") + 1] = "f" * 64
    result = runner.invoke(app, args)
    assert result.exit_code != 0
    assert "SHA-256 mismatch" in result.output
    assert not journal_path.exists()


# ── frozen plan configuration vs runtime deadline ────────────────────

_FROZEN_PILOT_CONFIG = "configs/data/acquisition/pilot_january_2019.frozen_plan_v1.yaml"
_FROZEN_PILOT_CONFIG_HASH = "b490b3a11d89707d8a9ab6d154eb6c03ee5d312e247a9d936e1caca4d2621426"


@pytest.mark.integration
def test_frozen_snapshot_matches_the_plan_config_binding() -> None:
    """The immutable snapshot is exactly what the frozen plan was built from."""
    from neuralmarket.core.configuration import config_sha256

    plan = json.loads(Path("data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8"))
    assert config_sha256(Path(_FROZEN_PILOT_CONFIG)) == _FROZEN_PILOT_CONFIG_HASH
    assert plan["bindings"]["pilot_config_hash"] == _FROZEN_PILOT_CONFIG_HASH
    # The mutable working config has drifted and must not satisfy the binding.
    assert config_sha256(Path(_PILOT_CONFIG)) != _FROZEN_PILOT_CONFIG_HASH


@pytest.mark.integration
def test_paid_execution_rejects_the_drifted_working_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The stale-config failure that blocked execution, reproduced on the real plan."""
    pilot_manifest_path = Path("data/manifests/pilot_request_plan_v1.json")
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not be loaded on a config mismatch")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    journal_path = tmp_path / "journal.sqlite"
    args = _execute_args(
        plan_path=pilot_manifest_path,
        plan_hash=plan["plan_hash"],
        auth_path=auth_path,
        attestation_path=attestation_path,
        journal_path=journal_path,
    )
    result = runner.invoke(app, args)
    assert result.exit_code != 0
    assert "dependency hash mismatch" in result.output
    assert not journal_path.exists()


@pytest.mark.integration
def test_paid_execution_requires_a_frozen_pilot_config(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not be loaded without a frozen config")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    journal_path = tmp_path / "journal.sqlite"
    result = runner.invoke(
        app,
        _execute_args(
            plan_path=pilot_manifest_path,
            plan_hash=plan["plan_hash"],
            auth_path=auth_path,
            attestation_path=attestation_path,
            journal_path=journal_path,
            frozen_config=None,
        ),
    )
    assert result.exit_code != 0
    assert "frozen-pilot-config" in result.output
    assert not journal_path.exists()


@pytest.mark.integration
@pytest.mark.parametrize("deadline", ["0", "-1"])
def test_paid_execution_rejects_nonpositive_runtime_deadline(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, deadline: str
) -> None:
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not be loaded on a bad deadline")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    journal_path = tmp_path / "journal.sqlite"
    args = _execute_args(
        plan_path=pilot_manifest_path,
        plan_hash=plan["plan_hash"],
        auth_path=auth_path,
        attestation_path=attestation_path,
        journal_path=journal_path,
    )
    args.extend(
        ["--frozen-pilot-config", _FROZEN_PILOT_CONFIG, "--total-run-deadline-seconds", deadline]
    )
    result = runner.invoke(app, args)
    assert result.exit_code != 0
    assert not journal_path.exists()


@pytest.mark.integration
def test_runtime_deadline_cannot_change_request_or_plan_identity() -> None:
    """540 vs 7200 changes no request ID, canonical hash, plan hash, or cap."""
    from neuralmarket.data.acquisition.requests import build_pilot_request_plan, load_pilot_config

    frozen = load_pilot_config(Path(_FROZEN_PILOT_CONFIG))
    assert frozen.metadata_execution.total_run_deadline_seconds == 540
    runtime = data_module._runtime_pilot_config(frozen, 7200)
    assert runtime.metadata_execution.total_run_deadline_seconds == 7200

    frozen_requests = build_pilot_request_plan(frozen)
    runtime_requests = build_pilot_request_plan(runtime)
    assert [r.request_id for r in frozen_requests] == [r.request_id for r in runtime_requests]
    assert [r.request_hash for r in frozen_requests] == [r.request_hash for r in runtime_requests]
    assert frozen.maximum_spend_usd == runtime.maximum_spend_usd
    assert frozen.maximum_single_request_usd == runtime.maximum_single_request_usd
    # The frozen object itself is never mutated, so its hash binding still holds.
    from neuralmarket.core.configuration import config_sha256

    assert config_sha256(Path(_FROZEN_PILOT_CONFIG)) == _FROZEN_PILOT_CONFIG_HASH


@pytest.mark.integration
def test_paid_execution_requires_preflight_evidence_before_credentials(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Paid mode without complete evidence stops before any credential access."""
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    _seed_journal(tmp_path / "journal.sqlite", plan)
    args = _execute_args(
        plan_path=pilot_manifest_path,
        plan_hash=plan["plan_hash"],
        auth_path=auth_path,
        attestation_path=attestation_path,
        journal_path=tmp_path / "journal.sqlite",
    )
    args = [arg for arg in args if arg != "--preflight-evidence"]
    evidence_arg = next(a for a in args if a.endswith("preflight_evidence.json"))
    args.pop(args.index(evidence_arg))

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not load without preflight evidence")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    result = runner.invoke(app, args)
    assert result.exit_code != 0
    assert "preflight-evidence" in result.output


@pytest.mark.integration
def test_paid_execution_rejects_tampered_preflight_evidence_before_credentials(
    pilot_manifest_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Tampered evidence fails closed with zero provider or credential access."""
    plan = json.loads(pilot_manifest_path.read_text(encoding="utf-8"))
    auth_path, attestation_path = _write_execution_inputs(plan, tmp_path)
    _seed_journal(tmp_path / "journal.sqlite", plan)
    args = _execute_args(
        plan_path=pilot_manifest_path,
        plan_hash=plan["plan_hash"],
        auth_path=auth_path,
        attestation_path=attestation_path,
        journal_path=tmp_path / "journal.sqlite",
    )
    evidence_path = Path(args[args.index("--preflight-evidence") + 1])
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    payload["quotes"][0]["record_count"] = 11
    evidence_path.write_text(json.dumps(payload), encoding="utf-8")

    def _no_credentials(root: Any) -> None:
        raise AssertionError("credentials must not load on tampered evidence")

    monkeypatch.setattr(data_module, "_load_dotenv", _no_credentials)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "preflight evidence" in result.output
    assert "generate a fresh complete recheck" in result.output
