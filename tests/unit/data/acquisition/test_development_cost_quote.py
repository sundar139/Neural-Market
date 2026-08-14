from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from neuralmarket.data.acquisition.development import DevelopmentRequest, load_development_plan
from neuralmarket.data.acquisition.development_cost_quote import (
    CheckpointGenerationMismatchError,
    DevelopmentQuoteBindings,
    DevelopmentQuoteError,
    DevelopmentQuoteRunPolicy,
    JournalFingerprint,
    build_complete_development_cost_evidence,
    build_partial_development_quote_evidence,
    initialize_development_quote_checkpoint,
    load_development_quote_checkpoint,
    prepare_development_quote,
    run_development_quote,
    validate_complete_development_cost_evidence,
    write_development_quote_checkpoint,
)
from neuralmarket.data.acquisition.metadata_runner import (
    IsolatedMetadataResult,
    IsolatedSchemaResult,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN_PATH = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_SCOPE_PATH = (
    _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
)
_PILOT_PLAN_PATH = _ROOT / "data/manifests/pilot_request_plan_v1.json"
_JOURNAL_PATH = _ROOT / "data/state/pilot_acquisition_journal.sqlite"
_HEAD = "f4c1dd11e2a19687f8602e945c5479e50762fd69"
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_PLAN_HASH = "1902157e61360897eb8cdb5a07f16877b15c0f56301f8584bfa03d0e95be25b5"
_SCOPE_SHA = "0c2f0d42eeb8349533010f8bc8aeb5a8413e889376399c21971ec9b31b829ac1"
_SCOPE_HASH = "cf08cd6ced5dec00bbb142fb9daa41e1f1070f281fbce5f29ce58c6e95fdd035"
NOW = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def canonical_plan() -> Any:
    return load_development_plan(_PLAN_PATH)


@pytest.fixture(autouse=True)
def _no_real_databento_import() -> Any:
    before = "databento" in sys.modules
    yield
    assert not ("databento" in sys.modules and not before), "offline tests imported databento"


def _requests(plan: Any) -> tuple[DevelopmentRequest, DevelopmentRequest]:
    catalog = next(
        request
        for request in plan.requests
        if request.schema_name != "cbbo-1m" and request.expected_split == "training"
    )
    quote = next(
        request
        for request in plan.requests
        if request.schema_name == "cbbo-1m" and request.expected_split == "validation"
    )
    return catalog, quote


def _bindings(requests: tuple[DevelopmentRequest, ...]) -> DevelopmentQuoteBindings:
    return DevelopmentQuoteBindings.from_requests(
        repository_head=_HEAD,
        development_plan_file_sha256="a" * 64,
        development_plan_hash="b" * 64,
        development_scope_file_sha256="c" * 64,
        development_scope_hash="d" * 64,
        pilot_plan_file_sha256="e" * 64,
        journal_fingerprint=JournalFingerprint(
            main_sha256="f" * 64,
            wal_exists=False,
            wal_size=0,
            wal_sha256="0" * 64,
        ),
        databento_client_version="0.81.0",
        requests=requests,
    )


def _policy(*, attempts: int = 2, timeout: float = 30.0) -> DevelopmentQuoteRunPolicy:
    return DevelopmentQuoteRunPolicy(
        hard_operation_timeout_seconds=timeout,
        maximum_attempts=attempts,
    )


def _schema_ok(dataset: str, *_args: object) -> IsolatedSchemaResult:
    supported = {
        "ARCX.PILLAR": ("definition", "ohlcv-1d", "statistics"),
        "OPRA.PILLAR": ("definition", "cbbo-1m"),
    }
    return IsolatedSchemaResult(
        supported_schemas=supported[dataset],
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _endpoint_ok(
    _request: DevelopmentRequest,
    endpoint: str,
    _attempt: int,
    _timeout: float,
) -> IsolatedMetadataResult:
    values: dict[str, object] = {
        "record-count": 10,
        "billable-size": 1000,
        "cost": "0.10",
    }
    return IsolatedMetadataResult(
        endpoint_values={endpoint: values[endpoint]},  # type: ignore[dict-item]
        events=[],
        child_pid=1,
        child_exitcode=0,
        child_joined=True,
        remaining_children=0,
    )


def _state(
    path: Path,
    requests: tuple[DevelopmentRequest, ...],
    *,
    policy: DevelopmentQuoteRunPolicy | None = None,
) -> Any:
    selected_policy = policy or _policy()
    state = initialize_development_quote_checkpoint(
        bindings=_bindings(requests),
        policy=selected_policy,
        now=NOW,
    )
    return write_development_quote_checkpoint(path, state)


def _load(
    path: Path,
    requests: tuple[DevelopmentRequest, ...],
    *,
    policy: DevelopmentQuoteRunPolicy | None = None,
) -> Any:
    return load_development_quote_checkpoint(
        path,
        expected_bindings=_bindings(requests),
        expected_policy=policy or _policy(),
    )


def _complete(
    tmp_path: Path,
    requests: tuple[DevelopmentRequest, ...],
    *,
    endpoint_runner: Callable[..., IsolatedMetadataResult] = _endpoint_ok,
) -> tuple[Any, Path]:
    checkpoint = tmp_path / "checkpoint.json"
    state = _state(checkpoint, requests)
    state = run_development_quote(
        state=state,
        checkpoint_path=checkpoint,
        schema_runner=_schema_ok,
        endpoint_runner=endpoint_runner,
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW,
    )
    return state, checkpoint


def test_checkpoint_accepts_native_development_request_identity(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = _requests(canonical_plan)
    state = _state(tmp_path / "checkpoint.json", requests)
    first = state.bindings.request_identities[0]
    request = requests[0]
    assert first.request_id == request.request_id
    assert first.specification_hash == request.specification_hash
    assert first.request_hash == request.request_hash
    assert first.expected_split == request.expected_split
    assert first.purpose == request.purpose
    assert first.raw_dbn_retention_required is request.raw_dbn_retention_required
    assert first.observation_time_source == request.observation_time_source
    assert (
        first.normalized_event_time_receive_fallback_allowed
        is request.normalized_event_time_receive_fallback_allowed
    )


def test_tampered_development_identity_is_rejected(canonical_plan: Any) -> None:
    request = _requests(canonical_plan)[1]
    with pytest.raises(DevelopmentQuoteError, match="identity"):
        DevelopmentQuoteBindings.from_requests(
            **{
                key: value
                for key, value in _bindings((request,)).model_dump().items()
                if key != "request_identities"
            },
            requests=(request.model_copy(update={"request_hash": "0" * 64}),),
        )


def test_record_count_survives_parent_interruption_and_is_not_refetched(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = (_requests(canonical_plan)[0],)
    checkpoint = tmp_path / "checkpoint.json"
    state = _state(checkpoint, requests)
    first_calls: list[str] = []

    def interrupt_after_record(
        request: DevelopmentRequest, endpoint: str, attempt: int, timeout: float
    ) -> IsolatedMetadataResult:
        del request, attempt, timeout
        first_calls.append(endpoint)
        if endpoint == "billable-size":
            raise KeyboardInterrupt
        return _endpoint_ok(requests[0], endpoint, 1, 1)

    with pytest.raises(KeyboardInterrupt):
        run_development_quote(
            state=state,
            checkpoint_path=checkpoint,
            schema_runner=_schema_ok,
            endpoint_runner=interrupt_after_record,
            total_deadline_seconds=60,
            monotonic=lambda: 0.0,
            now=lambda: NOW,
        )
    persisted = _load(checkpoint, requests)
    assert set(persisted.endpoint_results[requests[0].request_id]) == {"record-count"}

    resumed_calls: list[str] = []

    def resumed(
        request: DevelopmentRequest, endpoint: str, attempt: int, timeout: float
    ) -> IsolatedMetadataResult:
        resumed_calls.append(endpoint)
        return _endpoint_ok(request, endpoint, attempt, timeout)

    final = run_development_quote(
        state=persisted,
        checkpoint_path=checkpoint,
        schema_runner=_schema_ok,
        endpoint_runner=resumed,
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW + timedelta(minutes=1),
    )
    assert first_calls == ["record-count", "billable-size"]
    assert resumed_calls == ["billable-size", "cost"]
    assert final.status == "complete"


def test_billable_size_survives_interruption_and_complete_request_is_never_requoted(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = (_requests(canonical_plan)[1],)
    checkpoint = tmp_path / "checkpoint.json"
    state = _state(checkpoint, requests)

    def interrupt_before_cost(
        request: DevelopmentRequest, endpoint: str, attempt: int, timeout: float
    ) -> IsolatedMetadataResult:
        if endpoint == "cost":
            raise KeyboardInterrupt
        return _endpoint_ok(request, endpoint, attempt, timeout)

    with pytest.raises(KeyboardInterrupt):
        run_development_quote(
            state=state,
            checkpoint_path=checkpoint,
            schema_runner=_schema_ok,
            endpoint_runner=interrupt_before_cost,
            total_deadline_seconds=60,
            monotonic=lambda: 0.0,
            now=lambda: NOW,
        )
    persisted = _load(checkpoint, requests)
    assert set(persisted.endpoint_results[requests[0].request_id]) == {
        "record-count",
        "billable-size",
    }
    calls: list[str] = []
    final = run_development_quote(
        state=persisted,
        checkpoint_path=checkpoint,
        schema_runner=_schema_ok,
        endpoint_runner=lambda request, endpoint, attempt, timeout: (
            calls.append(endpoint) or _endpoint_ok(request, endpoint, attempt, timeout)
        ),
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW,
    )
    assert calls == ["cost"]
    assert final.status == "complete"

    run_development_quote(
        state=_load(checkpoint, requests),
        checkpoint_path=checkpoint,
        schema_runner=lambda *_: pytest.fail("completed schema was refetched"),
        endpoint_runner=lambda *_: pytest.fail("completed request was requoted"),
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW,
    )


def test_checkpoint_rejects_truncation_tamper_and_binding_drift(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = (_requests(canonical_plan)[0],)
    path = tmp_path / "checkpoint.json"
    state = _state(path, requests)
    assert not list(tmp_path.glob(".*.partial"))

    original = path.read_bytes()
    path.write_bytes(original[: len(original) // 2])
    with pytest.raises(DevelopmentQuoteError, match="checkpoint"):
        _load(path, requests)

    write_development_quote_checkpoint(path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["updated_at"] = (NOW + timedelta(days=1)).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DevelopmentQuoteError, match="hash"):
        _load(path, requests)

    write_development_quote_checkpoint(path, state)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["checkpoint_hash"] = ""
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DevelopmentQuoteError, match="hash"):
        _load(path, requests)

    write_development_quote_checkpoint(path, state)
    wrong = _bindings(requests).model_copy(update={"repository_head": "0" * 40})
    with pytest.raises(DevelopmentQuoteError, match="binding"):
        load_development_quote_checkpoint(path, expected_bindings=wrong, expected_policy=_policy())


def test_total_deadline_preserves_progress_and_resume_completes(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = (_requests(canonical_plan)[0],)
    checkpoint = tmp_path / "checkpoint.json"
    state = _state(checkpoint, requests)
    elapsed = 0.0
    calls: list[str] = []

    def monotonic() -> float:
        return elapsed

    def slow(
        request: DevelopmentRequest, endpoint: str, attempt: int, timeout: float
    ) -> IsolatedMetadataResult:
        nonlocal elapsed
        calls.append(endpoint)
        elapsed += 2.0
        return _endpoint_ok(request, endpoint, attempt, timeout)

    partial = run_development_quote(
        state=state,
        checkpoint_path=checkpoint,
        schema_runner=_schema_ok,
        endpoint_runner=slow,
        total_deadline_seconds=1.0,
        monotonic=monotonic,
        now=lambda: NOW,
    )
    assert calls == ["record-count"]
    assert partial.status == "incomplete"
    assert partial.stop_reason == "total_deadline_reached"
    assert partial.pending_endpoints[requests[0].request_id] == ("billable-size", "cost")

    resumed: list[str] = []
    complete = run_development_quote(
        state=_load(checkpoint, requests),
        checkpoint_path=checkpoint,
        schema_runner=_schema_ok,
        endpoint_runner=lambda request, endpoint, attempt, timeout: (
            resumed.append(endpoint) or _endpoint_ok(request, endpoint, attempt, timeout)
        ),
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW + timedelta(minutes=1),
    )
    assert resumed == ["billable-size", "cost"]
    assert complete.status == "complete"


def test_retry_is_bounded_and_successful_endpoint_is_not_retried(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = (_requests(canonical_plan)[0],)
    checkpoint = tmp_path / "checkpoint.json"
    policy = _policy(attempts=2)
    state = _state(checkpoint, requests, policy=policy)
    attempts: dict[str, int] = {}

    def flaky(
        request: DevelopmentRequest, endpoint: str, attempt: int, timeout: float
    ) -> IsolatedMetadataResult:
        del timeout
        attempts[endpoint] = attempts.get(endpoint, 0) + 1
        if endpoint == "record-count" and attempt == 1:
            return IsolatedMetadataResult(
                events=[],
                failure_type="metadata_hard_timeout",
                failed_endpoint="record-count",
                child_pid=1,
                child_exitcode=-15,
                child_terminated=True,
                child_joined=True,
                remaining_children=0,
            )
        return _endpoint_ok(request, endpoint, attempt, 1)

    complete = run_development_quote(
        state=state,
        checkpoint_path=checkpoint,
        schema_runner=_schema_ok,
        endpoint_runner=flaky,
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW,
    )
    assert attempts == {"record-count": 2, "billable-size": 1, "cost": 1}
    assert complete.provider_operation_counters.get_record_count == 2
    assert complete.retry_count == 1

    exhausted_path = tmp_path / "exhausted.json"
    exhausted = _state(exhausted_path, requests, policy=policy)
    failed_calls = 0

    def always_timeout(*_args: object) -> IsolatedMetadataResult:
        nonlocal failed_calls
        failed_calls += 1
        return IsolatedMetadataResult(
            events=[],
            failure_type="metadata_hard_timeout",
            failed_endpoint="record-count",
            child_pid=1,
            child_exitcode=-15,
            child_terminated=True,
            child_joined=True,
            remaining_children=0,
        )

    failed = run_development_quote(
        state=exhausted,
        checkpoint_path=exhausted_path,
        schema_runner=_schema_ok,
        endpoint_runner=always_timeout,
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW,
    )
    assert failed_calls == 2
    assert failed.status == "incomplete"
    assert failed.stop_reason == "endpoint_attempts_exhausted"
    assert failed.pending_endpoints[requests[0].request_id][0] == "record-count"


def test_schema_list_retry_is_bounded_and_checkpointed(canonical_plan: Any, tmp_path: Path) -> None:
    requests = (_requests(canonical_plan)[1],)
    checkpoint = tmp_path / "schema-retry.json"
    state = _state(checkpoint, requests, policy=_policy(attempts=2))
    calls = 0

    def flaky_schema(dataset: str, attempt: int, timeout: float) -> IsolatedSchemaResult:
        nonlocal calls
        del timeout
        calls += 1
        if attempt == 1:
            return IsolatedSchemaResult(
                failure_type="schema_list_hard_timeout",
                child_pid=1,
                child_exitcode=-15,
                child_terminated=True,
                child_joined=True,
                remaining_children=0,
            )
        return _schema_ok(dataset)

    complete = run_development_quote(
        state=state,
        checkpoint_path=checkpoint,
        schema_runner=flaky_schema,
        endpoint_runner=_endpoint_ok,
        total_deadline_seconds=60,
        monotonic=lambda: 0.0,
        now=lambda: NOW,
    )
    assert calls == 2
    assert complete.status == "complete"
    assert complete.provider_operation_counters.list_schemas == 2
    assert complete.retry_count == 1
    assert complete.timeout_count == 1


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("repository_head", "0" * 40),
        ("development_plan_hash", "0" * 64),
        ("development_scope_hash", "0" * 64),
        (
            "journal_fingerprint",
            JournalFingerprint(
                main_sha256="0" * 64,
                wal_exists=False,
                wal_size=0,
                wal_sha256="0" * 64,
            ),
        ),
    ],
)
def test_checkpoint_rejects_each_immutable_binding_drift(
    canonical_plan: Any, tmp_path: Path, field: str, replacement: object
) -> None:
    requests = (_requests(canonical_plan)[0],)
    path = tmp_path / f"binding-{field}.json"
    _state(path, requests)
    wrong = _bindings(requests).model_copy(update={field: replacement})
    with pytest.raises(DevelopmentQuoteError, match="binding"):
        load_development_quote_checkpoint(
            path,
            expected_bindings=wrong,
            expected_policy=_policy(),
        )


def test_complete_evidence_preserves_identity_and_has_exact_decimal_rollups(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = _requests(canonical_plan)

    def priced(
        request: DevelopmentRequest, endpoint: str, attempt: int, timeout: float
    ) -> IsolatedMetadataResult:
        result = _endpoint_ok(request, endpoint, attempt, timeout)
        if endpoint == "cost":
            value = "0.10" if request.schema_name != "cbbo-1m" else "0.20"
            return result.model_copy(update={"endpoint_values": {"cost": value}})
        return result

    state, checkpoint = _complete(tmp_path, requests, endpoint_runner=priced)
    evidence = build_complete_development_cost_evidence(
        state=state,
        checkpoint_file_sha256="9" * 64,
        requests=requests,
    )
    assert evidence.schema_version == "development-cost-evidence-v1"
    assert evidence.evidence_kind == "provider_cost_estimates"
    assert evidence.authorization_ready is False
    assert evidence.purchase_authorized is False
    assert evidence.rollups.cbbo_total_usd == "0.20"
    assert evidence.rollups.catalog_total_usd == "0.10"
    assert evidence.rollups.training_total_usd == "0.10"
    assert evidence.rollups.validation_total_usd == "0.20"
    assert evidence.rollups.grand_total_usd == "0.30"
    assert evidence.rollups.smallest_request_usd == "0.10"
    assert evidence.rollups.largest_request_usd == "0.20"
    assert evidence.rollups.median_request_usd == "0.10"
    assert evidence.rollups.p95_request_usd == "0.20"
    cbbo = next(quote for quote in evidence.quotes if quote.schema_name == "cbbo-1m")
    request = requests[1]
    assert cbbo.request_hash == request.request_hash
    assert cbbo.expected_split == "validation"
    assert cbbo.purpose == "strategy_b_closing_quote"
    assert cbbo.raw_dbn_retention_required is True
    assert cbbo.observation_time_source == "ts_recv"
    assert cbbo.normalized_event_time_receive_fallback_allowed is False
    assert checkpoint.exists()

    validated = validate_complete_development_cost_evidence(
        evidence.model_dump(mode="json"),
        expected_bindings=state.bindings,
        requests=requests,
    )
    assert validated.evidence_hash == evidence.evidence_hash


def test_complete_evidence_rejects_float_nonfinite_missing_duplicate_and_extra(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = _requests(canonical_plan)
    state, _ = _complete(tmp_path, requests)
    evidence = build_complete_development_cost_evidence(
        state=state,
        checkpoint_file_sha256="9" * 64,
        requests=requests,
    )
    base = evidence.model_dump(mode="json")

    float_cost = json.loads(json.dumps(base))
    float_cost["quotes"][0]["cost_usd"] = 0.1
    with pytest.raises((DevelopmentQuoteError, ValidationError), match="Decimal|string|cost"):
        validate_complete_development_cost_evidence(
            float_cost, expected_bindings=state.bindings, requests=requests
        )

    nonfinite = json.loads(json.dumps(base))
    nonfinite["quotes"][0]["cost_usd"] = "NaN"
    with pytest.raises((DevelopmentQuoteError, ValidationError), match="finite|cost|hash"):
        validate_complete_development_cost_evidence(
            nonfinite, expected_bindings=state.bindings, requests=requests
        )

    empty_evidence_hash = json.loads(json.dumps(base))
    empty_evidence_hash["evidence_hash"] = ""
    with pytest.raises(DevelopmentQuoteError, match="hash"):
        validate_complete_development_cost_evidence(
            empty_evidence_hash,
            expected_bindings=state.bindings,
            requests=requests,
        )

    empty_quote_hash = json.loads(json.dumps(base))
    empty_quote_hash["quotes"][0]["quote_sha256"] = ""
    with pytest.raises(DevelopmentQuoteError, match="hash"):
        validate_complete_development_cost_evidence(
            empty_quote_hash,
            expected_bindings=state.bindings,
            requests=requests,
        )

    missing = json.loads(json.dumps(base))
    missing["quotes"].pop()
    with pytest.raises(DevelopmentQuoteError, match="coverage"):
        validate_complete_development_cost_evidence(
            missing, expected_bindings=state.bindings, requests=requests
        )

    duplicate = json.loads(json.dumps(base))
    duplicate["quotes"][1] = duplicate["quotes"][0]
    with pytest.raises(DevelopmentQuoteError, match="duplicate|coverage"):
        validate_complete_development_cost_evidence(
            duplicate, expected_bindings=state.bindings, requests=requests
        )

    extra = json.loads(json.dumps(base))
    extra["quotes"].append({**extra["quotes"][0], "request_id": "extra"})
    with pytest.raises(DevelopmentQuoteError, match="coverage"):
        validate_complete_development_cost_evidence(
            extra, expected_bindings=state.bindings, requests=requests
        )


def test_partial_evidence_is_explicit_resumable_and_never_authorization_ready(
    canonical_plan: Any, tmp_path: Path
) -> None:
    requests = _requests(canonical_plan)
    state = _state(tmp_path / "checkpoint.json", requests)
    partial = build_partial_development_quote_evidence(
        state=state,
        checkpoint_file_sha256="9" * 64,
    )
    assert partial.schema_version == "development-cost-progress-v1"
    assert partial.status == "incomplete"
    assert partial.authorization_ready is False
    assert partial.purchase_authorized is False
    assert partial.resume_eligible is True
    assert partial.completed_request_ids == ()
    assert set(partial.pending_endpoints) == {request.request_id for request in requests}
    assert partial.provider_operation_counters.timeseries_get_range == 0
    assert partial.provider_operation_counters.batch == 0
    assert partial.provider_operation_counters.live == 0
    assert partial.provider_operation_counters.symbology == 0


def test_production_shaped_gate_and_zero_call_initialization(canonical_plan: Any) -> None:
    prepared = prepare_development_quote(
        repository_root=_ROOT,
        development_plan_path=_PLAN_PATH,
        development_scope_path=_SCOPE_PATH,
        pilot_plan_path=_PILOT_PLAN_PATH,
        pilot_journal_path=_JOURNAL_PATH,
        repository_head=_HEAD,
        expected_repository_head=_HEAD,
        expected_plan_file_sha256=_PLAN_SHA,
        expected_plan_hash=_PLAN_HASH,
        expected_scope_file_sha256=_SCOPE_SHA,
        expected_scope_hash=_SCOPE_HASH,
        databento_client_version="0.81.0",
    )
    assert prepared.plan == canonical_plan
    assert prepared.scope.new_request_count == 490
    assert prepared.scope.new_cbbo_request_count == 482
    assert prepared.scope.new_catalog_request_count == 8
    assert prepared.scope.scope_hash == _SCOPE_HASH
    new_ids = {request.request_id for request in prepared.scope.requests}
    assert "ebefaaae3b198092" not in new_ids
    assert "d5352ffb04e4bc83" not in new_ids
    assert any(
        disposition.source_request_id == "ebefaaae3b198092"
        for disposition in prepared.scope.unavailable
    )
    assert "d5352ffb04e4bc83" in prepared.scope.other_quarantined_source_request_ids
    state = initialize_development_quote_checkpoint(
        bindings=prepared.bindings,
        policy=_policy(),
        now=NOW,
    )
    assert len(state.pending_endpoints) == 490
    assert state.provider_operation_counters.total_metadata_operations == 0


def test_gate_rejects_scope_hash_and_artifact_backed_journal_drift(tmp_path: Path) -> None:
    kwargs = {
        "repository_root": _ROOT,
        "development_plan_path": _PLAN_PATH,
        "development_scope_path": _SCOPE_PATH,
        "pilot_plan_path": _PILOT_PLAN_PATH,
        "pilot_journal_path": _JOURNAL_PATH,
        "repository_head": _HEAD,
        "expected_repository_head": _HEAD,
        "expected_plan_file_sha256": _PLAN_SHA,
        "expected_plan_hash": _PLAN_HASH,
        "expected_scope_file_sha256": _SCOPE_SHA,
        "expected_scope_hash": _SCOPE_HASH,
        "databento_client_version": "0.81.0",
    }
    with pytest.raises(DevelopmentQuoteError, match="plan hash"):
        prepare_development_quote(**{**kwargs, "expected_plan_hash": "0" * 64})
    with pytest.raises(DevelopmentQuoteError, match="scope.*hash"):
        prepare_development_quote(**{**kwargs, "expected_scope_hash": "0" * 64})

    drifted = tmp_path / "journal.sqlite"
    shutil.copy2(_JOURNAL_PATH, drifted)
    with sqlite3.connect(drifted) as database:
        database.execute(
            "UPDATE requests SET state = 'planned' WHERE request_id = ?",
            ("ebefaaae3b198092",),
        )
        database.commit()
    with pytest.raises(DevelopmentQuoteError, match="scope|state|journal"):
        prepare_development_quote(**{**kwargs, "pilot_journal_path": drifted})


def test_checkpoint_write_compare_and_swap_rejects_concurrent_generation(
    canonical_plan: Any, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "checkpoint.json"
    requests = (_requests(canonical_plan)[0],)
    state = _state(checkpoint, requests)
    before_bytes = checkpoint.read_bytes()
    with pytest.raises(CheckpointGenerationMismatchError, match="concurrently"):
        write_development_quote_checkpoint(
            checkpoint,
            state,
            expected_checkpoint_hash="0" * 64,
        )
    assert checkpoint.read_bytes() == before_bytes
    written = write_development_quote_checkpoint(
        checkpoint,
        state,
        expected_checkpoint_hash=state.checkpoint_hash,
    )
    assert written.status == state.status
    persisted = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert persisted["checkpoint_hash"] == written.checkpoint_hash
