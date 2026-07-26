from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import neuralmarket.data.acquisition.recovery as recovery_module
from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    AuthorizationError,
    PilotAuthorization,
    compute_authorization_hash,
    validate_authorization,
)
from neuralmarket.data.acquisition.billing_reconciliation import (
    apply_billing_reconciliation,
    build_reconciliation_artifact,
)
from neuralmarket.data.acquisition.executor import (
    ExecutorGuardError,
    PilotExecutionCoordinator,
    RawAcquisitionResult,
    RecoveryPurchasePackage,
    validate_recovery_purchase_package,
)
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.live_cost_recheck import recheck_costs
from neuralmarket.data.acquisition.metadata_runner import IsolatedMetadataResult
from neuralmarket.data.acquisition.purchase_review import (
    AUTHORIZATION_STATEMENT_TEMPLATE,
    ExpectedPurchaseBindings,
    _recovery_quote_rejections,
    compute_portal_attestation_hash,
    compute_review_hash,
)
from neuralmarket.data.acquisition.recovery import (
    RecoveryPlan,
    RecoveryPlanError,
    prepare_recovery_plan,
    validate_recovery_plan,
)
from neuralmarket.data.acquisition.requests import load_pilot_config, plan_hash_metadata
from neuralmarket.data.raw.integrity import sha256_of_file

pytestmark = pytest.mark.unit

_PARENT_PLAN = (
    "9654fe1c2dfe98946560e27c6f51f110"  # pragma: allowlist secret
    "038613060461fdf75936edf1a7d0ae77"  # pragma: allowlist secret
)
_PRIOR_AUTHORIZATION = (
    "db2cde39f5a5e96c7301b9d289fc0c8"  # pragma: allowlist secret
    "e5412b60d2b69faae30f12a7b99dd885e"  # pragma: allowlist secret
)
_PRIOR_EXECUTION = "132078783c31dcab22cb90d95c967c9c"  # pragma: allowlist secret
_REQUEST_ID = "2750995e515e4f1a"  # pragma: allowlist secret
_REQUEST_HASH = (
    "b8b0a410ace7a8a5d710b8bc04e37560"  # pragma: allowlist secret
    "ab7b08ceb9aa316a4a3334b6b0980d7a"  # pragma: allowlist secret
)


def _seed_reconciled_request(tmp_path: Path) -> tuple[Path, Path, Path]:
    journal_path = tmp_path / "journal.sqlite"
    now = datetime.now(UTC).isoformat()
    with RequestJournal(journal_path) as journal:
        journal.upsert(
            JournalEntry(
                request_id=_REQUEST_ID,
                request_hash=_REQUEST_HASH,
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
            authorization_hash=_PRIOR_AUTHORIZATION,
            plan_hash=_PARENT_PLAN,
            execution_id=_PRIOR_EXECUTION,
            reserved_at=now,
        )
        assert journal.consume_reserved_authorization(
            authorization_hash=_PRIOR_AUTHORIZATION,
            execution_id=_PRIOR_EXECUTION,
            consumed_at=now,
        )
        unknown = build_reconciliation_artifact(
            execution_id=_PRIOR_EXECUTION,
            request_id=_REQUEST_ID,
            plan_hash=_PARENT_PLAN,
            authorization_hash=_PRIOR_AUTHORIZATION,
            portal_review_status="UNKNOWN",
            observed_usage_usd="UNKNOWN",
            journal_state_before="uncertain_billing",
            execution_attempt_status_before="running",
            reviewed_at=now,
        )
        apply_billing_reconciliation(journal=journal, artifact=unknown)
        not_billed = build_reconciliation_artifact(
            execution_id=_PRIOR_EXECUTION,
            request_id=_REQUEST_ID,
            plan_hash=_PARENT_PLAN,
            authorization_hash=_PRIOR_AUTHORIZATION,
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
        apply_billing_reconciliation(journal=journal, artifact=not_billed)

    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(unknown.model_dump_json(indent=2), encoding="utf-8")
    reconciliation_path = tmp_path / "not_billed.json"
    reconciliation_path.write_text(not_billed.model_dump_json(indent=2), encoding="utf-8")
    return journal_path, reconciliation_path, unknown_path


def test_valid_reconciled_request_produces_distinct_one_request_plan(tmp_path: Path) -> None:
    journal_path, reconciliation_path, _ = _seed_reconciled_request(tmp_path)
    parent_path = Path("data/manifests/pilot_request_plan_v1.json")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))

    recovery = prepare_recovery_plan(
        parent_plan_path=parent_path,
        journal_path=journal_path,
        reconciliation_path=reconciliation_path,
        request_id=_REQUEST_ID,
    )
    payload = recovery.model_dump(mode="json", by_alias=True)

    assert payload["plan_hash"] != _PARENT_PLAN
    assert payload["request_count"] == 1
    assert [request["request_id"] for request in payload["requests"]] == [_REQUEST_ID]
    assert payload["requests"][0] == next(
        request for request in parent["requests"] if request["request_id"] == _REQUEST_ID
    )
    assert payload["manifest_version"] == "pilot-recovery-plan-v2"
    assert payload["recovery"] == {
        "parent_plan_hash": _PARENT_PLAN,
        "prior_execution_id": _PRIOR_EXECUTION,
        "prior_authorization_hash": _PRIOR_AUTHORIZATION,
        "request_id": _REQUEST_ID,
        "request_hash": _REQUEST_HASH,
        "reconciliation_artifact_hash": not_billed_hash(reconciliation_path),
        "parent_bindings": parent["bindings"],
        "required_prior_resolution": "confirmed_not_billed",
        "required_journal_state": "retry_eligible_after_manual_nonbilling_confirmation",
        "automatic_retry_allowed": False,
    }


def not_billed_hash(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["artifact_hash"])


def _prepare(tmp_path: Path) -> tuple[RecoveryPlan, Path, Path, Path]:
    journal, reconciliation, unknown = _seed_reconciled_request(tmp_path)
    recovery = prepare_recovery_plan(
        parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
        journal_path=journal,
        reconciliation_path=reconciliation,
        request_id=_REQUEST_ID,
    )
    return recovery, journal, reconciliation, unknown


def _update(journal: Path, sql: str, parameters: tuple[object, ...] = ()) -> None:
    connection = sqlite3.connect(journal)
    connection.execute(sql, parameters)
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()


def test_operational_recovery_plan_revalidates_current_journal(tmp_path: Path) -> None:
    recovery, journal, _, _ = _prepare(tmp_path)

    validated = validate_recovery_plan(
        recovery.model_dump(mode="json", by_alias=True), journal_path=journal
    )

    assert validated == recovery
    _update(journal, "UPDATE requests SET state = 'uncertain_billing'")
    with pytest.raises(RecoveryPlanError, match="not retry eligible"):
        validate_recovery_plan(
            recovery.model_dump(mode="json", by_alias=True), journal_path=journal
        )


def test_recovery_purchase_review_requires_fresh_exact_quote(tmp_path: Path) -> None:
    recovery, journal, _, _ = _prepare(tmp_path)
    now = datetime.now(UTC)
    evidence = _cost_evidence(recovery, now)

    assert (
        _recovery_quote_rejections(
            recovery_plan=recovery,
            cost_evidence=evidence,
            checkpoint_sha256="c" * 64,
            request_manifest_sha256="m" * 64,
            repository_head="0" * 40,
            now=now,
            journal_path=journal,
        )
        == []
    )

    for field, value in (
        ("plan_hash", recovery.recovery.parent_plan_hash),
        ("checkpoint_sha256", "d" * 64),
        ("request_manifest_sha256", "n" * 64),
        ("repository_head", "1" * 40),
        ("expires_at", (now - timedelta(seconds=1)).isoformat()),
        ("expires_at", (now + timedelta(hours=10)).isoformat()),
    ):
        changed = json.loads(json.dumps(evidence))
        changed[field] = value
        assert (
            _recovery_quote_rejections(
                recovery_plan=recovery,
                cost_evidence=changed,
                checkpoint_sha256="c" * 64,
                request_manifest_sha256="m" * 64,
                repository_head="0" * 40,
                now=now,
                journal_path=journal,
            )[0].code
            == "invalid_cost_evidence"
        )

    changed = json.loads(json.dumps(evidence))
    changed["quotes"][0]["request_id"] = "f" * 16
    assert (
        _recovery_quote_rejections(
            recovery_plan=recovery,
            cost_evidence=changed,
            checkpoint_sha256="c" * 64,
            request_manifest_sha256="m" * 64,
            repository_head="0" * 40,
            now=now,
            journal_path=journal,
        )[0].code
        == "invalid_cost_evidence"
    )


class _Metadata:
    def get_record_count(self, **kwargs: object) -> int:
        return 10

    def get_billable_size(self, **kwargs: object) -> int:
        return 100

    def get_cost(self, **kwargs: object) -> float:
        return 0.000112652779


class _Lifecycle:
    def __init__(self, root: Path) -> None:
        self.root = root

    def inspect(self, request, entry):
        return False, False, False, False

    def normalize(self, request, raw):
        path = self.root / f"{request.request_id}.parquet"
        path.write_bytes(Path(raw.raw_path).read_bytes())
        return str(path), sha256_of_file(path), path.stat().st_size

    def quality(self, request, normalized_path):
        return True


def _cost_evidence(recovery: RecoveryPlan, now: datetime) -> dict[str, object]:
    cost = recovery.estimated_total_cost_usd
    result = recheck_costs(
        requests=list(recovery.requests),
        repository_head="0" * 40,
        checkpoint_sha256="c" * 64,
        plan_hash=recovery.plan_hash,
        request_manifest_sha256="m" * 64,
        sdk_version="0.81.0",
        now=now,
        schema_lister=lambda dataset: [recovery.requests[0].schema_name],
        quoter=lambda request, attempt, timeout: IsolatedMetadataResult(
            endpoint_values={"cost": cost},
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        ),
        timeout_seconds=30,
        prior_raw_total_usd=Decimal(cost),
        prior_conservative_total_usd=Decimal(cost),
        tracked_total_usd=Decimal(cost),
        max_attempts=1,
        recovery_plan=recovery,
    )
    return json.loads(json.dumps({"schema_version": "pilot-cost-recheck-v2", **asdict(result)}))


def _purchase_package(
    recovery: RecoveryPlan, journal_path: Path, now: datetime
) -> RecoveryPurchasePackage:
    evidence = _cost_evidence(recovery, now)
    cost = Decimal(recovery.estimated_total_cost_usd)
    expected = ExpectedPurchaseBindings(
        repository_head="0" * 40,
        plan_hash=recovery.plan_hash,
        completed_checkpoint_sha256="c" * 64,
        request_manifest_sha256="m" * 64,
        source_manifest_hash=recovery.bindings["source_manifest_hash"],
        split_manifest_hash=recovery.bindings["split_manifest_hash"],
        acquisition_policy_hash=recovery.bindings["acquisition_policy_hash"],
        raw_total_usd=cost,
        conservative_total_usd=cost,
        maximum_ceiling_usd=Decimal("5.00"),
    )
    authorization: dict[str, Any] = {
        "schema_version": "pilot-purchase-authorization-v1",
        "template_only": False,
        "authorized": True,
        "consumed": False,
        "repository_head": expected.repository_head,
        "plan_hash": recovery.plan_hash,
        "completed_checkpoint_sha256": expected.completed_checkpoint_sha256,
        "request_manifest_sha256": expected.request_manifest_sha256,
        "source_manifest_hash": expected.source_manifest_hash,
        "split_manifest_hash": expected.split_manifest_hash,
        "acquisition_policy_hash": expected.acquisition_policy_hash,
        "configuration_compatibility": {
            "checkpoint_stored_pilot_config_hash": "a" * 64,
            "current_config_sha256": "a" * 64,
            "compatible": True,
        },
        "databento_client_version": "0.81.0",
        "raw_total_usd": str(cost),
        "conservative_total_usd": str(cost),
        "authorized_ceiling_usd": "5.00",
        "scope": {
            "pilot_month": "2019-01",
            "datasets": [recovery.requests[0].dataset],
            "schemas": [recovery.requests[0].schema_name],
            "symbols": list(recovery.requests[0].symbols),
            "window_start": recovery.requests[0].start.isoformat(),
            "window_end": recovery.requests[0].end_exclusive.isoformat(),
            "logical_request_count": 1,
        },
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "authorized_by": "test-operator",
        "authorization_statement": AUTHORIZATION_STATEMENT_TEMPLATE.format(amount="5.00"),
    }
    authorization["review_hash"] = compute_review_hash(authorization)
    attestation: dict[str, Any] = {
        "schema_version": "pilot-portal-attestation-v1",
        "template_only": False,
        "attested": True,
        "repository_head": expected.repository_head,
        "dataset_scope": [recovery.requests[0].dataset],
        "schema_scope": [recovery.requests[0].schema_name],
        "symbol_scope": list(recovery.requests[0].symbols),
        "window_start": recovery.requests[0].start.isoformat(),
        "window_end": recovery.requests[0].end_exclusive.isoformat(),
        "portal_estimate_usd": str(cost),
        "currency": "USD",
        "observed_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=20)).isoformat(),
        "completed_checkpoint_sha256": expected.completed_checkpoint_sha256,
        "request_manifest_sha256": expected.request_manifest_sha256,
        "operator_confirmation": "reviewed exact recovery scope",
    }
    attestation["attestation_hash"] = compute_portal_attestation_hash(attestation)
    return RecoveryPurchasePackage(
        authorization=authorization,
        attestation=attestation,
        expected=expected,
        cost_evidence=evidence,
        journal_path=journal_path,
        consumption_marker=journal_path.with_suffix(".purchase-consumed.json"),
    )


def _authorization(plan_hash: str, bindings: dict[str, str]) -> PilotAuthorization:
    now = datetime.now(UTC)
    payload = {
        "authorization_version": "pilot-authorization-v1",
        "pilot_plan_hash": plan_hash,
        "source_manifest_hash": bindings["source_manifest_hash"],
        "split_manifest_hash": bindings["split_manifest_hash"],
        "acquisition_policy_hash": bindings["acquisition_policy_hash"],
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
        "authorized_by": "test-operator",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
    }
    return PilotAuthorization.model_validate(
        {**payload, "authorization_hash": compute_authorization_hash(payload)}
    )


def _execute_recovery(
    tmp_path: Path,
    *,
    uncertain: bool = False,
    include_unrelated: bool = False,
    authorization_hash: str | None = None,
    purchase_review: bool = True,
    invalidate_before_reservation: bool = False,
    construction_failure: bool = False,
    constructions: list[str] | None = None,
):
    recovery, journal_path, _, _ = _prepare(tmp_path)
    if include_unrelated:
        parent = json.loads(
            Path("data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8")
        )
        now = datetime.now(UTC).isoformat()
        with RequestJournal(journal_path) as journal:
            for item in parent["requests"]:
                if item["request_id"] == _REQUEST_ID:
                    continue
                journal.upsert(
                    JournalEntry(
                        request_id=item["request_id"],
                        request_hash=item["request_hash"],
                        state="preflight_validated",
                        attempt_count=0,
                        estimated_cost_usd=item["estimated_cost"],
                        actual_billed_cost_usd=None,
                        raw_path=None,
                        raw_checksum=None,
                        normalized_path=None,
                        normalized_checksum=None,
                        failure_category=None,
                        failure_message=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
    authorization = _authorization(recovery.plan_hash, recovery.bindings)
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_text(authorization.model_dump_json(), encoding="utf-8")
    now = datetime.now(UTC)
    purchase_package = _purchase_package(recovery, journal_path, now)
    calls: list[str] = []

    class Paid:
        def __init__(self) -> None:
            if constructions is not None:
                constructions.append("constructed")
            if construction_failure:
                raise RuntimeError("local construction failed")

        def acquire_range(self, request):
            calls.append(request.request_id)
            if uncertain:
                raise RuntimeError("provider outcome unknown")
            raw = tmp_path / f"{request.request_id}.dbn"
            raw.write_bytes(request.request_id.encode())
            return RawAcquisitionResult(
                request_id=request.request_id,
                raw_path=str(raw),
                sha256=sha256_of_file(raw),
                record_count=1,
            )

    class Journal(RequestJournal):
        def reserve_recovery_authorization(self, **kwargs: Any) -> bool:
            if invalidate_before_reservation:
                with self.connection:
                    self.connection.execute(
                        "UPDATE requests SET state = 'uncertain_billing' WHERE request_id = ?",
                        (_REQUEST_ID,),
                    )
            return super().reserve_recovery_authorization(**kwargs)

    result = PilotExecutionCoordinator().execute_paid(
        requests=list(recovery.requests),
        config=load_pilot_config(Path("configs/data/acquisition/pilot_january_2019.yaml")),
        plan_hash=recovery.plan_hash,
        plan_bindings=recovery.bindings,
        plan_metadata=plan_hash_metadata(recovery.model_dump(mode="json", by_alias=True)),
        authorization_path=authorization_path,
        authorization_hash=authorization_hash or authorization.authorization_hash,
        portal_attestation_hash="t" * 64,
        confirm_plan_hash=recovery.plan_hash,
        metadata_provider_factory=_Metadata,
        paid_provider_factory=Paid,
        journal_factory=lambda: Journal(journal_path),
        lifecycle=_Lifecycle(tmp_path),
        now=now,
        recovery_plan=recovery,
        recovery_purchase_package=purchase_package if purchase_review else None,
    )
    return recovery, journal_path, authorization_path, authorization, calls, result


def test_guarded_recovery_execution_reuses_request_and_consumes_once(tmp_path: Path) -> None:
    recovery, journal_path, authorization_path, authorization, calls, result = _execute_recovery(
        tmp_path
    )

    with RequestJournal(journal_path) as journal:
        entry = journal.get(_REQUEST_ID)
        assert entry is not None
        assert entry.attempt_count == 2
        assert entry.state == "quality_validated"
        assert recovery.plan_hash in journal.consumed_authorization_ids()
        reconciliation_count = journal.connection.execute(
            "SELECT COUNT(*) FROM billing_reconciliations WHERE request_id = ?", (_REQUEST_ID,)
        ).fetchone()[0]
        recovery_execution = journal.connection.execute(
            "SELECT plan_hash FROM execution_attempts WHERE plan_hash = ?", (recovery.plan_hash,)
        ).fetchone()
    assert calls == [_REQUEST_ID]
    assert result.requests_completed == 1
    assert result.paid_request_calls == 1
    assert reconciliation_count == 2
    assert recovery_execution == (recovery.plan_hash,)

    with pytest.raises(ExecutorGuardError):
        PilotExecutionCoordinator().execute_paid(
            requests=list(recovery.requests),
            config=load_pilot_config(Path("configs/data/acquisition/pilot_january_2019.yaml")),
            plan_hash=recovery.plan_hash,
            plan_bindings=recovery.bindings,
            plan_metadata=plan_hash_metadata(recovery.model_dump(mode="json", by_alias=True)),
            authorization_path=authorization_path,
            authorization_hash=authorization.authorization_hash,
            portal_attestation_hash="t" * 64,
            confirm_plan_hash=recovery.plan_hash,
            metadata_provider_factory=_Metadata,
            paid_provider_factory=lambda: (_ for _ in ()).throw(AssertionError()),
            journal_factory=lambda: RequestJournal(journal_path),
            lifecycle=_Lifecycle(tmp_path),
            now=datetime.now(UTC),
            recovery_plan=recovery,
            recovery_purchase_package=_purchase_package(recovery, journal_path, datetime.now(UTC)),
        )


def test_guarded_recovery_requires_purchase_review(tmp_path: Path) -> None:
    with pytest.raises(ExecutorGuardError, match="missing_recovery_purchase_review"):
        _execute_recovery(tmp_path, purchase_review=False)


def test_recovery_purchase_review_bindings_match_plan(tmp_path: Path) -> None:
    recovery, journal_path, _, _ = _prepare(tmp_path)
    now = datetime.now(UTC)
    package = _purchase_package(recovery, journal_path, now)
    changed = replace(
        package,
        expected=replace(package.expected, plan_hash=recovery.recovery.parent_plan_hash),
    )
    with pytest.raises(ExecutorGuardError, match="binding_mismatch"):
        validate_recovery_purchase_package(changed, recovery_plan=recovery, now=now)


def test_recovery_eligibility_cas_precedes_provider_construction(tmp_path: Path) -> None:
    constructions: list[str] = []
    with pytest.raises(ExecutorGuardError, match="no longer eligible"):
        _execute_recovery(
            tmp_path,
            invalidate_before_reservation=True,
            constructions=constructions,
        )
    assert constructions == []


def test_recovery_provider_construction_failure_releases_claim(tmp_path: Path) -> None:
    with pytest.raises(ExecutorGuardError, match="local construction failed"):
        _execute_recovery(tmp_path, construction_failure=True)
    with RequestJournal(tmp_path / "journal.sqlite") as journal:
        entry = journal.get(_REQUEST_ID)
        reservations = journal.connection.execute(
            "SELECT COUNT(*) FROM authorization_reservations WHERE state = 'reserved'"
        ).fetchone()[0]
    assert entry is not None
    assert entry.state == "retry_eligible_after_manual_nonbilling_confirmation"
    assert entry.attempt_count == 1
    assert reservations == 0


def test_guarded_recovery_leaves_24_parent_requests_unchanged(tmp_path: Path) -> None:
    recovery, journal_path, _, _, calls, result = _execute_recovery(
        tmp_path, include_unrelated=True
    )
    parent = json.loads(
        Path("data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8")
    )
    expected = {
        item["request_id"]: item["request_hash"]
        for item in parent["requests"]
        if item["request_id"] != _REQUEST_ID
    }

    with RequestJournal(journal_path) as journal:
        unrelated = [entry for entry in journal.all() if entry.request_id in expected]

    assert len(unrelated) == 24
    assert {entry.request_id: entry.request_hash for entry in unrelated} == expected
    assert all(entry.state == "preflight_validated" for entry in unrelated)
    assert all(entry.attempt_count == 0 for entry in unrelated)
    assert all(entry.raw_path is None and entry.normalized_path is None for entry in unrelated)
    assert calls == [_REQUEST_ID]
    assert result.plan_hash == recovery.plan_hash
    assert result.requests_completed == 1


def test_guarded_recovery_rejects_reported_authorization_hash_mismatch(tmp_path: Path) -> None:
    with pytest.raises(ExecutorGuardError, match="artifact hash does not match"):
        _execute_recovery(tmp_path, authorization_hash="x" * 64)


def test_guarded_recovery_uncertainty_consumes_and_blocks(tmp_path: Path) -> None:
    recovery, journal_path, _, _, calls, result = _execute_recovery(tmp_path, uncertain=True)

    with RequestJournal(journal_path) as journal:
        entry = journal.get(_REQUEST_ID)
        assert entry is not None
        assert entry.attempt_count == 2
        assert entry.state == "uncertain_billing"
        assert recovery.plan_hash in journal.consumed_authorization_ids()
    assert calls == [_REQUEST_ID]
    assert result.blocking_state == "block_uncertain_billing"
    assert result.requests_uncertain == 1


def test_recovery_hash_is_deterministic_and_preparation_is_read_only(tmp_path: Path) -> None:
    recovery, journal, reconciliation, _ = _prepare(tmp_path)
    before = {path.name: path.read_bytes() for path in journal.parent.glob("journal.sqlite*")}

    repeated = prepare_recovery_plan(
        parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
        journal_path=journal,
        reconciliation_path=reconciliation,
        request_id=_REQUEST_ID,
    )

    after = {path.name: path.read_bytes() for path in journal.parent.glob("journal.sqlite*")}
    assert repeated.plan_hash == recovery.plan_hash
    assert after == before


def test_uncheckpointed_wal_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    Path(f"{journal}-wal").write_bytes(b"uncheckpointed")

    with pytest.raises(RecoveryPlanError, match="uncheckpointed WAL state"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_journal_change_during_preparation_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    real_connect = sqlite3.connect

    def racing_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        connection = real_connect(*args, **kwargs)
        with real_connect(journal) as writer:
            writer.execute(
                "UPDATE requests SET state = 'uncertain_billing' WHERE request_id = ?",
                (_REQUEST_ID,),
            )
        return connection

    monkeypatch.setattr(recovery_module.sqlite3, "connect", racing_connect)
    with pytest.raises(RecoveryPlanError, match="changed during recovery preparation"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_unsupported_journal_schema_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE schema_meta SET version = 9")

    with pytest.raises(RecoveryPlanError, match="journal schema version"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_non_consumed_reservation_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE authorization_reservations SET state = 'reserved'")

    with pytest.raises(RecoveryPlanError, match="reservation binding mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_inconsistent_reconciled_execution_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE execution_attempts SET blocking_request = 'other-request'")

    with pytest.raises(RecoveryPlanError, match="reconciled execution state mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_broken_reconciliation_chain_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(
        journal,
        "UPDATE billing_reconciliations SET supersedes_reconciliation_hash = NULL "
        "WHERE supersession_sequence = 2",
    )

    with pytest.raises(RecoveryPlanError, match="reconciliation chain mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_missing_reconciliation_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "DELETE FROM billing_reconciliations")

    with pytest.raises(RecoveryPlanError, match="effective reconciliation is missing"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_superseded_unknown_reconciliation_fails_closed(tmp_path: Path) -> None:
    _, journal, _, unknown = _prepare(tmp_path)

    with pytest.raises(RecoveryPlanError, match="not the effective NOT_BILLED"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=unknown,
            request_id=_REQUEST_ID,
        )


def test_effective_billed_reconciliation_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(
        journal,
        "UPDATE billing_reconciliations SET portal_review_status = 'BILLED', "
        "billing_resolution = 'confirmed_billed' WHERE supersession_sequence = 2",
    )

    with pytest.raises(RecoveryPlanError, match="not the effective NOT_BILLED"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


@pytest.mark.parametrize(
    ("assignment", "message"),
    [
        ("state = 'uncertain_billing'", "not retry eligible"),
        ("attempt_count = 0", "exactly one prior attempt"),
        ("attempt_count = 2", "exactly one prior attempt"),
        ("actual_billed_cost_usd = '0.01'", "has billed cost"),
        ("request_completed_at = '2026-07-16T00:00:00+00:00'", "is completed"),
        ("raw_path = 'data/raw/recovery.dbn'", "has registered artifacts"),
        ("normalized_path = 'data/normalized/recovery.parquet'", "has registered artifacts"),
    ],
)
def test_ineligible_request_state_fails_closed(
    tmp_path: Path, assignment: str, message: str
) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, f"UPDATE requests SET {assignment} WHERE request_id = ?", (_REQUEST_ID,))

    with pytest.raises(RecoveryPlanError, match=message):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_wrong_request_hash_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(journal, "UPDATE requests SET request_hash = ?", ("0" * 64,))

    with pytest.raises(RecoveryPlanError, match="request hash mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_wrong_prior_execution_id_fails_closed(tmp_path: Path) -> None:
    _, journal, reconciliation, _ = _prepare(tmp_path)
    _update(
        journal,
        "UPDATE consumed_authorizations SET execution_id = 'wrong-execution' WHERE plan_hash = ?",
        (_PARENT_PLAN,),
    )

    with pytest.raises(RecoveryPlanError, match="reservation binding mismatch"):
        prepare_recovery_plan(
            parent_plan_path=Path("data/manifests/pilot_request_plan_v1.json"),
            journal_path=journal,
            reconciliation_path=reconciliation,
            request_id=_REQUEST_ID,
        )


def test_recovery_model_rejects_a_second_request(tmp_path: Path) -> None:
    recovery, _, _, _ = _prepare(tmp_path)
    payload = recovery.model_dump(mode="json", by_alias=True)
    parent = json.loads(
        Path("data/manifests/pilot_request_plan_v1.json").read_text(encoding="utf-8")
    )
    payload["requests"].append(parent["requests"][1])

    with pytest.raises(ValueError, match="at most 1 item|exactly one request"):
        RecoveryPlan.model_validate(payload)


def test_parent_reauthorization_stays_blocked_but_recovery_identity_is_available(
    tmp_path: Path,
) -> None:
    recovery, journal, _, _ = _prepare(tmp_path)
    with sqlite3.connect(journal) as connection:
        consumed = {
            row[0] for row in connection.execute("SELECT plan_hash FROM consumed_authorizations")
        }
    parent_auth = _authorization(_PARENT_PLAN, recovery.bindings)
    recovery_auth = _authorization(recovery.plan_hash, recovery.bindings)
    expected = {
        "expected_source_manifest_hash": recovery.bindings["source_manifest_hash"],
        "expected_split_manifest_hash": recovery.bindings["split_manifest_hash"],
        "expected_acquisition_policy_hash": recovery.bindings["acquisition_policy_hash"],
        "now": datetime.now(UTC),
        "consumed_ids": consumed,
        "expected_maximum_spend_usd": Decimal("5.00"),
        "expected_maximum_single_request_usd": Decimal("1.00"),
    }

    with pytest.raises(AuthorizationError, match="already consumed"):
        validate_authorization(parent_auth, expected_plan_hash=_PARENT_PLAN, **expected)
    validate_authorization(recovery_auth, expected_plan_hash=recovery.plan_hash, **expected)
