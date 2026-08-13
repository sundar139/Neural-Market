"""Tests for the pilot executor state machine and dual authorization guard.

The centerpiece is proving the dual guard: a real paid provider is only ever
constructed when BOTH a valid, hash-bound authorization artifact AND an
explicit matching plan-hash confirmation are present. Every failure path
asserts the injected ``paid_provider_factory`` is never called.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from neuralmarket.data.acquisition.authorization import (
    CONFIRMATION_PHRASE,
    build_remaining_scope,
    compute_authorization_hash,
)
from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.executor import (
    ExecutorGuardError,
    PilotExecutionCoordinator,
    PilotExecutor,
    select_recovery_action,
)
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.providers import PaidProviderError
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    build_pilot_request_plan,
    finalize_request,
    load_pilot_config,
    plan_hash,
)

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).resolve().parents[4] / "configs/data/acquisition/pilot_january_2019.yaml"
)


def _default_scope(plan_hash: str = "p" * 64):
    """Mirror the scope _write_valid_auth_file mints when none is supplied."""
    return build_remaining_scope(
        source_plan_hash=plan_hash,
        completed_request_ids=["completed-00000000001"],
        completed_request_hashes=["b" * 64],
        remaining_request_ids=[f"remaining-{i:08x}" for i in range(24)],
        remaining_request_hashes=[f"{i:064x}" for i in range(24)],
    )


def _write_valid_auth_file(
    path: Path, *, plan_hash: str = "p" * 64, scope: object = None, **overrides: object
) -> str:
    import json

    now = datetime.now(UTC)
    if scope is None:
        scope = build_remaining_scope(
            source_plan_hash=plan_hash,
            completed_request_ids=["completed-00000000001"],
            completed_request_hashes=["b" * 64],
            remaining_request_ids=[f"remaining-{i:08x}" for i in range(24)],
            remaining_request_hashes=[f"{i:064x}" for i in range(24)],
        )
    payload = {
        "authorization_version": "2.0",
        "pilot_plan_hash": plan_hash,
        "source_manifest_hash": "s" * 64,
        "split_manifest_hash": "v" * 64,
        "acquisition_policy_hash": "a" * 64,
        "maximum_spend_usd": "5.00",
        "maximum_single_request_usd": "1.00",
        "authorized_currency": "USD",
        "authorized_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "authorized_by": "Test User",
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "purchase_authorized": True,
        "remaining_scope_hash": scope.scope_hash,
        "cost_evidence": {
            "evidence_type": "cost_recheck",
            "evidence_sha256": "c" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
        },
        "portal_evidence": {
            "evidence_type": "portal_attestation",
            "evidence_sha256": "d" * 64,
            "observed_at": (now - timedelta(minutes=5)).isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
        },
        "portal_source_evidence_sha256": "e" * 64,
    }
    payload.update(overrides)
    payload["authorization_hash"] = compute_authorization_hash(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(payload["authorization_hash"])


def _finalize(draft):
    estimate = MetadataEstimate(
        dataset=draft.dataset,
        schema=draft.schema_name,
        symbol=draft.symbols[0],
        stype_in=draft.stype_in,
        window_start=draft.start,
        window_end=draft.end_exclusive,
        record_count=10,
        billable_size_bytes=1000,
        cost_usd=Decimal("0.10"),
        retries=0,
    )
    return finalize_request(draft, estimate, datetime(2026, 1, 1, tzinfo=UTC))


def _finalized_request():
    return _finalize(build_pilot_request_plan(load_pilot_config(CONFIG_PATH))[0])


def _authorized_plan() -> tuple[str, list, dict[str, object], object]:
    """Return the finalized 25-request plan, its bindings, and its 24-request scope."""
    requests = [
        _finalize(draft) for draft in build_pilot_request_plan(load_pilot_config(CONFIG_PATH))
    ]
    bindings: dict[str, object] = {
        "source_manifest_hash": "s" * 64,
        "split_manifest_hash": "v" * 64,
        "acquisition_policy_hash": "a" * 64,
    }
    computed = plan_hash(requests, bindings)
    scope = build_remaining_scope(
        source_plan_hash=computed,
        completed_request_ids=[requests[0].request_id],
        completed_request_hashes=[requests[0].request_hash],
        remaining_request_ids=[request.request_id for request in requests[1:]],
        remaining_request_hashes=[request.request_hash for request in requests[1:]],
    )
    return computed, requests, bindings, scope


def _mark_preflight_validated(journal: RequestJournal, requests: list) -> None:
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare(requests)
    for request in requests:
        executor.transition(request.request_id, "preflight_validated")


def test_guard_execute_blocks_when_authorization_file_missing(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=tmp_path / "missing.json",
            confirm_plan_hash="p" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            preflight_passed=True,
            execution_scope=_default_scope(),
        )
    assert exc.value.reason == "missing_authorization"
    factory.assert_not_called()
    assert journal.all() == []
    assert journal.consumed_authorization_ids() == set()


def test_guard_execute_blocks_before_authorization_when_preflight_failed(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=tmp_path / "missing.json",
            confirm_plan_hash="p" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            preflight_passed=False,
        )
    assert exc.value.reason == "preflight_not_passed"
    factory.assert_not_called()
    assert journal.consumed_authorization_ids() == set()


def test_guard_execute_blocks_when_confirm_plan_hash_mismatched(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash="p" * 64)
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=auth_path,
            confirm_plan_hash="WRONG_HASH",
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            preflight_passed=True,
            execution_scope=_default_scope(),
        )
    assert exc.value.reason == "plan_hash_confirmation_mismatch"
    factory.assert_not_called()


def test_guard_execute_blocks_invalid_authorization(tmp_path) -> None:
    # A structurally valid file whose plan hash does not match the live plan.
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash="p" * 64)
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="q" * 64,  # live plan differs from the authorized plan
            authorization_path=auth_path,
            confirm_plan_hash="q" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            preflight_passed=True,
            execution_scope=_default_scope(),
        )
    assert exc.value.reason == "invalid_authorization"
    factory.assert_not_called()


def test_guard_execute_blocks_template_authorization(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    # parents[4] is the repository root (acquisition/data/unit/tests/<root>).
    repo_root = Path(__file__).resolve().parents[4]
    template_path = repo_root / "configs/data/acquisition/pilot_authorization.template.json"
    assert template_path.exists(), f"template not found at {template_path}"
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=template_path,
            confirm_plan_hash="p" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            preflight_passed=True,
            execution_scope=_default_scope(),
        )
    assert exc.value.reason == "invalid_authorization"
    factory.assert_not_called()


def test_guard_execute_binds_authorization_to_live_plan_caps(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path)
    factory = Mock()
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash="p" * 64,
            authorization_path=auth_path,
            confirm_plan_hash="p" * 64,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            preflight_passed=True,
            execution_scope=_default_scope(),
            expected_maximum_spend_usd=Decimal("4.99"),
            expected_maximum_single_request_usd=Decimal("0.99"),
        )
    assert exc.value.reason == "invalid_authorization"
    factory.assert_not_called()


def test_guard_execute_succeeds_only_with_both_valid_guards(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    sentinel_provider = Mock()
    factory = Mock(return_value=sentinel_provider)
    result = executor.guard_execute(
        plan_hash=plan,
        authorization_path=auth_path,
        confirm_plan_hash=plan,
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        now=datetime.now(UTC),
        paid_provider_factory=factory,
        authorized_requests=requests,
        plan_bindings=bindings,
        preflight_passed=True,
        execution_scope=scope,
    )
    assert result.acquire_range
    factory.assert_called_once()
    assert journal.consumed_authorization_ids() == set()
    result.acquire_range(requests[1])
    assert journal.consumed_authorization_ids() == {plan}


def test_provider_factory_failure_releases_authorization_reservation(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    with pytest.raises(ExecutorGuardError, match="construction"):
        executor.guard_execute(
            plan_hash=plan,
            authorization_path=auth_path,
            confirm_plan_hash=plan,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=Mock(side_effect=RuntimeError("construction failed")),
            authorized_requests=requests,
            plan_bindings=bindings,
            preflight_passed=True,
            execution_scope=scope,
        )
    assert journal.consumed_authorization_ids() == set()


def test_guarded_provider_rejects_duplicate_acquire(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    inner = Mock()
    result = executor.guard_execute(
        plan_hash=plan,
        authorization_path=auth_path,
        confirm_plan_hash=plan,
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        now=datetime.now(UTC),
        paid_provider_factory=Mock(return_value=inner),
        authorized_requests=requests,
        plan_bindings=bindings,
        preflight_passed=True,
        execution_scope=scope,
    )
    result.acquire_range(requests[1])
    with pytest.raises(ExecutorGuardError, match="already acquired"):
        result.acquire_range(requests[1])
    inner.acquire_range.assert_called_once()


def test_guard_execute_rejects_requests_not_bound_to_plan_hash(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash=plan,
            authorization_path=auth_path,
            confirm_plan_hash=plan,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=Mock(),
            authorized_requests=[*requests, *requests],
            plan_bindings=bindings,
            preflight_passed=True,
            execution_scope=scope,
        )
    assert exc.value.reason == "authorized_requests_plan_mismatch"


def test_guard_execute_rejects_plan_bindings_that_do_not_match_authorization_inputs(
    tmp_path,
) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash=plan,
            authorization_path=auth_path,
            confirm_plan_hash=plan,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=Mock(),
            authorized_requests=requests,
            plan_bindings={**bindings, "source_manifest_hash": "x" * 64},
            preflight_passed=True,
            execution_scope=scope,
        )
    assert exc.value.reason == "plan_dependency_mismatch"


def test_guard_execute_requires_journal_preflight_for_each_request(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash=plan,
            authorization_path=auth_path,
            confirm_plan_hash=plan,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=Mock(),
            authorized_requests=requests,
            plan_bindings=bindings,
            preflight_passed=True,
            execution_scope=scope,
        )
    assert exc.value.reason == "preflight_not_passed"


def test_guard_execute_rejects_consumed_authorization_after_reopen(tmp_path) -> None:
    db_path = tmp_path / "journal.sqlite"
    auth_path = tmp_path / "auth.json"
    plan, requests, bindings, scope = _authorized_plan()
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    with RequestJournal(db_path) as journal:
        _mark_preflight_validated(journal, requests)
        executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
        executor.guard_execute(
            plan_hash=plan,
            authorization_path=auth_path,
            confirm_plan_hash=plan,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=Mock(),
            authorized_requests=requests,
            plan_bindings=bindings,
            preflight_passed=True,
            execution_scope=scope,
        )

    factory = Mock()
    with RequestJournal(db_path) as reopened:
        executor = PilotExecutor(journal=reopened, metadata_estimator=Mock())
        with pytest.raises(ExecutorGuardError) as exc:
            executor.guard_execute(
                plan_hash=plan,
                authorization_path=auth_path,
                confirm_plan_hash=plan,
                source_manifest_hash="s" * 64,
                split_manifest_hash="v" * 64,
                acquisition_policy_hash="a" * 64,
                now=datetime.now(UTC),
                paid_provider_factory=factory,
                authorized_requests=requests,
                plan_bindings=bindings,
                preflight_passed=True,
                execution_scope=scope,
            )
    assert exc.value.reason == "invalid_authorization"
    factory.assert_not_called()


def test_prepare_writes_planned_state_for_every_request(tmp_path, arcx_request) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare([arcx_request])
    entry = journal.get(arcx_request.request_id)
    assert entry is not None
    assert entry.state == "planned"


def test_transition_rejects_illegal_jump(tmp_path, arcx_request) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare([arcx_request])
    with pytest.raises(ValueError):
        executor.transition(arcx_request.request_id, "downloaded")


def test_transition_allows_legal_step(tmp_path, arcx_request) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    executor.prepare([arcx_request])
    executor.transition(arcx_request.request_id, "preflight_validated")
    entry = journal.get(arcx_request.request_id)
    assert entry is not None
    assert entry.state == "preflight_validated"


def test_metadata_provider_can_be_constructed_during_preparation() -> None:
    # A MetadataEstimator (already-existing metadata-only provider) is freely constructible.
    from neuralmarket.data.acquisition.estimation import MetadataEstimator

    estimator = MetadataEstimator(client=Mock())
    assert estimator is not None


def test_init_has_no_paid_provider_parameter() -> None:
    # Structural guarantee: a paid provider cannot exist as a constructor attribute.
    import inspect

    params = set(inspect.signature(PilotExecutor.__init__).parameters)
    assert not any("paid" in p or "provider" in p for p in params)


@pytest.mark.parametrize(
    ("state", "raw", "normalized", "quality", "partial", "expected"),
    [
        (None, False, False, False, False, "execute_provider"),
        ("quality_validated", True, True, True, False, "skip"),
        ("raw_validated", True, False, False, False, "resume_normalization"),
        ("normalized", True, True, False, False, "resume_quality"),
        ("request_started", False, False, False, False, "block_uncertain_billing"),
        ("quality_validated", False, True, True, False, "quarantine"),
        ("preflight_validated", False, False, False, True, "manual_recovery_required"),
    ],
)
def test_select_recovery_action_fails_closed(
    state, raw, normalized, quality, partial, expected
) -> None:
    entry = (
        None
        if state is None
        else JournalEntry(
            request_id="request",
            request_hash="h" * 64,
            state=state,
            attempt_count=0,
            estimated_cost_usd="0.01",
            actual_billed_cost_usd=None,
            raw_path=None,
            raw_checksum=None,
            normalized_path=None,
            normalized_checksum=None,
            failure_category=None,
            failure_message=None,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
    )
    assert (
        select_recovery_action(
            entry,
            raw_valid=raw,
            normalized_valid=normalized,
            quality_valid=quality,
            partial_present=partial,
        )
        == expected
    )


# ── consumption identity ─────────────────────────────────────────────


def _consume(
    journal: RequestJournal, *, authorization_hash: str, plan: str, execution: str
) -> None:
    now = datetime.now(UTC).isoformat()
    assert journal.reserve_authorization(
        authorization_hash=authorization_hash,
        plan_hash=plan,
        execution_id=execution,
        reserved_at=now,
    )
    assert journal.consume_reserved_authorization(
        authorization_hash=authorization_hash, execution_id=execution, consumed_at=now
    )


def _guard(executor: PilotExecutor, auth_path: Path, plan: str, requests, bindings, factory, scope):
    return executor.guard_execute(
        plan_hash=plan,
        authorization_path=auth_path,
        confirm_plan_hash=plan,
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        now=datetime.now(UTC),
        paid_provider_factory=factory,
        authorized_requests=requests,
        plan_bindings=bindings,
        preflight_passed=True,
        execution_scope=scope,
    )


def test_distinct_authorization_not_blocked_by_settled_plan_sibling(tmp_path) -> None:
    """A consumed authorization must not conflate with a distinct one for the same plan."""
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    _consume(journal, authorization_hash="1" * 64, plan=plan, execution="exec-settled")

    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope, purchase_authorized=False)
    factory = Mock()
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    with pytest.raises(ExecutorGuardError) as exc:
        _guard(executor, auth_path, plan, requests, bindings, factory, scope)
    assert "purchase_not_authorized" in str(exc.value)
    factory.assert_not_called()


def test_exact_authorization_replay_remains_rejected(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    auth_path = tmp_path / "auth.json"
    authorization_hash = _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    _consume(journal, authorization_hash=authorization_hash, plan=plan, execution="exec-first")

    factory = Mock()
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    with pytest.raises(ExecutorGuardError) as exc:
        _guard(executor, auth_path, plan, requests, bindings, factory, scope)
    assert "already_consumed" in str(exc.value)
    factory.assert_not_called()


def test_legacy_consumption_without_authorization_hash_fails_closed(tmp_path) -> None:
    """A legacy row whose authorization identity is unusable still blocks the plan."""
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    with journal._connection:  # simulating a pre-identity journal row
        journal._connection.execute(
            "INSERT INTO consumed_authorizations (plan_hash, authorization_hash, consumed_at) "
            "VALUES (?, '', ?)",
            (plan, datetime.now(UTC).isoformat()),
        )

    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    factory = Mock()
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    with pytest.raises(ExecutorGuardError) as exc:
        _guard(executor, auth_path, plan, requests, bindings, factory, scope)
    assert "already_consumed" in str(exc.value)
    factory.assert_not_called()


# ── scoped paid execution ────────────────────────────────────────────


def test_guard_execute_requires_an_explicit_execution_scope(tmp_path) -> None:
    """Paid execution must fail closed rather than fall back to a synthetic scope."""
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    factory = Mock()
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    with pytest.raises(ExecutorGuardError) as exc:
        executor.guard_execute(
            plan_hash=plan,
            authorization_path=auth_path,
            confirm_plan_hash=plan,
            source_manifest_hash="s" * 64,
            split_manifest_hash="v" * 64,
            acquisition_policy_hash="a" * 64,
            now=datetime.now(UTC),
            paid_provider_factory=factory,
            authorized_requests=requests,
            plan_bindings=bindings,
            preflight_passed=True,
        )
    assert exc.value.reason == "missing_execution_scope"
    factory.assert_not_called()


def test_guard_execute_rejects_scoped_cost_above_the_authorization_ceiling(tmp_path) -> None:
    """A $0.45 ceiling must reject a scoped plan that costs more than $0.45."""
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope, maximum_spend_usd="0.45")
    factory = Mock()
    executor = PilotExecutor(journal=journal, metadata_estimator=Mock())
    with pytest.raises(ExecutorGuardError) as exc:
        _guard(executor, auth_path, plan, requests, bindings, factory, scope)
    assert exc.value.reason == "authorization_ceiling_exceeded"
    factory.assert_not_called()


def test_guard_execute_pays_only_the_scoped_requests(tmp_path) -> None:
    """The paid hash set equals the scope exactly; the completed request is absent."""
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    auth_path = tmp_path / "auth.json"
    # 24 scoped requests at 0.10 each: a 2.40 ceiling is exact, 2.39 is not.
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope, maximum_spend_usd="2.40")
    sentinel = Mock()
    provider = _guard(
        PilotExecutor(journal=journal, metadata_estimator=Mock()),
        auth_path,
        plan,
        requests,
        bindings,
        Mock(return_value=sentinel),
        scope,
    )
    assert len(scope.remaining_request_hashes) == 24
    assert requests[0].request_id not in set(scope.remaining_request_ids)
    with pytest.raises(ExecutorGuardError) as exc:
        provider.acquire_range(requests[0])
    assert "not in the authorized plan" in str(exc.value)


def test_consumption_persists_the_exact_authorization_ceiling(tmp_path) -> None:
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    _mark_preflight_validated(journal, requests)
    auth_path = tmp_path / "auth.json"
    _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope, maximum_spend_usd="2.40")
    provider = _guard(
        PilotExecutor(journal=journal, metadata_estimator=Mock()),
        auth_path,
        plan,
        requests,
        bindings,
        Mock(return_value=Mock()),
        scope,
    )
    provider.acquire_range(requests[1])
    row = journal.connection.execute(
        "SELECT maximum_authorized_spend_usd, currency FROM consumed_authorizations"
    ).fetchone()
    assert row == ("2.40", "USD")


def test_validate_only_requires_preflight_to_equal_the_execution_scope(tmp_path) -> None:
    """Preflight covers the scoped requests, never the whole canonical plan."""
    journal = RequestJournal(tmp_path / "journal.sqlite")
    plan, requests, bindings, scope = _authorized_plan()
    coordinator = PilotExecutionCoordinator()
    config = load_pilot_config(CONFIG_PATH)

    with pytest.raises(ExecutorGuardError) as exc:
        coordinator.validate_only(
            requests=requests,  # the canonical 25
            config=config,
            plan_bindings=bindings,
            plan_metadata=None,
            metadata_provider_factory=Mock(
                side_effect=AssertionError("provider must not be built on a scope mismatch")
            ),
            execution_scope=scope,
        )
    assert exc.value.reason == "execution_scope_request_mismatch"
    assert journal.consumed_authorization_ids() == set()


def test_scoped_preflight_excludes_the_completed_request(tmp_path) -> None:
    plan, requests, bindings, scope = _authorized_plan()
    scoped = [r for r in requests if r.request_id in set(scope.remaining_request_ids)]
    assert len(scoped) == 24
    assert requests[0].request_id not in {r.request_id for r in scoped}
    assert [r.request_id for r in scoped] == scope.remaining_request_ids
    assert [r.request_hash for r in scoped] == scope.remaining_request_hashes


def test_validate_only_offline_preflight_never_constructs_provider() -> None:
    """Complete hash-bound evidence runs the paid preflight with zero metadata calls."""
    plan, requests, bindings, scope = _authorized_plan()
    scoped = [r for r in requests if r.request_id in set(scope.remaining_request_ids)]
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

    result = PilotExecutionCoordinator().validate_only(
        requests=scoped,
        config=load_pilot_config(CONFIG_PATH),
        plan_bindings=bindings,
        plan_metadata=None,
        metadata_provider_factory=Mock(
            side_effect=AssertionError("provider must not be constructed for offline preflight")
        ),
        execution_scope=scope,
        preflight_estimates=estimates,
    )

    assert result.ready_for_paid_execution is True
    assert Decimal(result.estimated_total_cost) == Decimal("0.24")


def test_execute_paid_persistence_failure_blocks_uncertain_billing_without_retry(
    tmp_path: Path,
) -> None:
    """A post-response persistence failure stops paid execution with no retry."""
    plan, requests, bindings, scope = _authorized_plan()
    journal_path = tmp_path / "journal.sqlite"
    with RequestJournal(journal_path) as journal:
        _mark_preflight_validated(journal, requests)
        # The scope excludes requests[0]; reflect that in the journal state.
        journal.connection.execute(
            "UPDATE requests SET state = 'quality_validated' WHERE request_id = ?",
            (requests[0].request_id,),
        )
        journal.connection.commit()
    auth_path = tmp_path / "auth.json"
    auth_hash = _write_valid_auth_file(auth_path, plan_hash=plan, scope=scope)
    scoped = [r for r in requests if r.request_id in set(scope.remaining_request_ids)]
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
    paid_calls: list[str] = []

    class FailingPaidProvider:
        def acquire_range(self, request: AcquisitionRequest) -> object:
            paid_calls.append(request.request_id)
            raise PaidProviderError(
                "local_persistence_failure",
                "paid historical provider response could not be persisted locally"
                " (OSError: simulated write failure)",
                uncertain_completion=True,
            )

        def close(self) -> None:
            return None

    class NoResumeLifecycle:
        def inspect(self, request: object, entry: object) -> tuple[bool, bool, bool, bool]:
            return (False, False, False, False)

        def normalize(self, request: object, raw: object) -> object:
            raise AssertionError("normalization must not run after a persistence failure")

        def quality(self, request: object, path: object) -> bool:
            raise AssertionError("quality validation must not run after a persistence failure")

    result = PilotExecutionCoordinator().execute_paid(
        requests=requests,
        config=load_pilot_config(CONFIG_PATH),
        plan_hash=plan,
        plan_bindings=bindings,
        plan_metadata=None,
        authorization_path=auth_path,
        authorization_hash=auth_hash,
        portal_attestation_hash="t" * 64,
        confirm_plan_hash=plan,
        metadata_provider_factory=Mock(
            side_effect=AssertionError("metadata provider must not be constructed")
        ),
        paid_provider_factory=lambda: FailingPaidProvider(),
        journal_factory=lambda: RequestJournal(journal_path),
        lifecycle=NoResumeLifecycle(),
        now=datetime.now(UTC),
        execution_scope=scope,
        preflight_estimates=estimates,
    )

    with RequestJournal(journal_path) as journal:
        entry = journal.get(paid_calls[0])
    assert result.blocking_state == "block_uncertain_billing"
    assert result.manual_action_required is True
    assert result.paid_request_calls == 1
    assert result.requests_uncertain == 1
    assert paid_calls == [scoped[0].request_id]  # exactly one provider call, no retry
    assert entry is not None and entry.state == "uncertain_billing"
    assert entry.failure_category == "local_persistence_failure"
    assert "OSError: simulated write failure" in (entry.failure_message or "")
    assert entry.actual_billed_cost_usd is None  # no synthetic billing value
