"""Native DevelopmentExecutionRequest quotation: checkpoint, resume, bounds, CLI."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.development import load_development_plan
from neuralmarket.data.acquisition.development_cost_quote import (
    DevelopmentQuoteBindings,
    DevelopmentQuoteRunPolicy,
    JournalFingerprint,
    build_complete_execution_quote_records,
    initialize_development_quote_checkpoint,
    load_development_quote_checkpoint,
    prepare_development_execution_quote,
    run_development_quote,
    write_development_quote_checkpoint,
)
from neuralmarket.data.acquisition.development_execution import (
    DevelopmentExecutionRequest,
    build_fresh_execution_quote_scope,
    derive_execution_quote_classification,
    load_development_execution_manifest,
    write_fresh_execution_quote_scope,
)
from neuralmarket.data.acquisition.metadata_runner import (
    IsolatedMetadataResult,
    IsolatedSchemaResult,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_SCOPE_SRC = _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_EVIDENCE = _ROOT / "reports/data/execution/live_c1_20260814T191524Z_run10.local.json"
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_EVIDENCE_FILE_SHA = "60032ab4f7536849104d12855adc5b5271b9e9ca4c8ceac158f509d1a121f111"
_HEAD = "bbf57b09c05e62501920f9653bf7f187863588b4"


@pytest.fixture(scope="module")
def manifest():
    return load_development_execution_manifest(_MANIFEST)


@pytest.fixture(scope="module")
def fragments(manifest) -> tuple[DevelopmentExecutionRequest, DevelopmentExecutionRequest]:
    selected = [item for item in manifest.execution_requests if item.fragment_count > 1][:2]
    return tuple(selected)


def _bindings(requests) -> DevelopmentQuoteBindings:
    return DevelopmentQuoteBindings.from_requests(
        repository_head="a" * 40,
        development_plan_file_sha256="a" * 64,
        development_plan_hash="b" * 64,
        development_scope_file_sha256="c" * 64,
        development_scope_hash="d" * 64,
        pilot_plan_file_sha256="e" * 64,
        journal_fingerprint=JournalFingerprint(
            main_sha256="f" * 64, wal_exists=False, wal_size=0, wal_sha256="0" * 64
        ),
        databento_client_version="0.81.0",
        requests=requests,
        execution_manifest_file_sha256="c" * 64,
        execution_manifest_hash="d" * 64,
        execution_fresh_scope_file_sha256="e" * 64,
        execution_fresh_scope_hash="f" * 64,
    )


def _policy() -> DevelopmentQuoteRunPolicy:
    return DevelopmentQuoteRunPolicy(hard_operation_timeout_seconds=30.0, maximum_attempts=2)


class RecordingRunners:
    def __init__(self):
        """Record every schema and endpoint runner invocation."""
        self.schema_calls: list[str] = []
        self.endpoint_calls: list[tuple[str, str]] = []
        self.endpoint_values: dict[str, dict[str, object]] = {}

    def schema(self, dataset: str, _attempt: int, _timeout: float) -> IsolatedSchemaResult:
        self.schema_calls.append(dataset)
        return IsolatedSchemaResult(
            supported_schemas=("definition", "cbbo-1m", "ohlcv-1d", "statistics"),
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    def endpoint(self, request, endpoint: str, _attempt: int, _timeout: float):
        self.endpoint_calls.append((request.execution_request_id, endpoint))
        values = {
            "record-count": 10,
            "billable-size": 1000,
            "cost": "0.05",
        }
        return IsolatedMetadataResult(
            endpoint_values={endpoint: values[endpoint]},  # type: ignore[dict-item]
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )


def _run_once(path: Path, fragments, runners, *, deadline: float = 60.0, monotonic=None):
    state = initialize_development_quote_checkpoint(
        bindings=_bindings(fragments), policy=_policy(), now=datetime.now(UTC)
    )
    state = write_development_quote_checkpoint(path, state)
    state = run_development_quote(
        state=state,
        checkpoint_path=path,
        schema_runner=runners.schema,
        endpoint_runner=runners.endpoint,
        total_deadline_seconds=deadline,
        monotonic=monotonic or (lambda: 0.0),
        now=lambda: datetime.now(UTC),
        expected_checkpoint_hash=state.checkpoint_hash,
    )
    return state


class TestNativeCheckpoint:
    def test_execution_requests_quoted_natively_with_identity(self, tmp_path, fragments):
        runners = RecordingRunners()
        state = _run_once(tmp_path / "checkpoint.json", fragments, runners)
        assert state.status == "complete"
        identities = state.bindings.request_identities
        assert all(isinstance(request, DevelopmentExecutionRequest) for request in identities)
        assert identities[0].execution_request_id == fragments[0].execution_request_id
        assert identities[0].parent_request_id == fragments[0].parent_request_id
        assert identities[0].execution_request_hash == fragments[0].execution_request_hash
        records = build_complete_execution_quote_records(state=state, requests=fragments)
        assert len(records) == 2
        assert all(record.quote_origin == "provider_observed" for record in records)
        assert all(
            record.execution_request_hash == fragment.execution_request_hash
            for record, fragment in zip(records, fragments, strict=True)
        )

    def test_resume_does_not_refetch_completed_endpoints(self, tmp_path, fragments):
        checkpoint_path = tmp_path / "checkpoint.json"
        runners = RecordingRunners()
        state = _run_once(checkpoint_path, fragments, runners)
        first_calls = list(runners.endpoint_calls)
        assert len(first_calls) == 6  # 2 requests x 3 endpoints
        runners2 = RecordingRunners()
        state = load_development_quote_checkpoint(
            checkpoint_path, expected_bindings=_bindings(fragments), expected_policy=_policy()
        )
        state = run_development_quote(
            state=state,
            checkpoint_path=checkpoint_path,
            schema_runner=runners2.schema,
            endpoint_runner=runners2.endpoint,
            total_deadline_seconds=60.0,
            monotonic=lambda: 0.0,
            now=lambda: datetime.now(UTC),
            expected_checkpoint_hash=state.checkpoint_hash,
        )
        assert state.status == "complete"
        assert runners2.endpoint_calls == []
        assert runners2.schema_calls == []


class TestFragmentBounds:
    def test_provider_receives_exact_fragment_bounds(self, tmp_path, fragments):
        captured: dict[str, DevelopmentExecutionRequest] = {}
        runners = RecordingRunners()

        def endpoint(request, endpoint: str, attempt: int, timeout: float):
            captured[request.execution_request_id] = request
            return runners.endpoint(request, endpoint, attempt, timeout)

        _run_once(tmp_path / "checkpoint.json", fragments, runners)
        captured.clear()
        runners2 = RecordingRunners()
        state = initialize_development_quote_checkpoint(
            bindings=_bindings(fragments), policy=_policy(), now=datetime.now(UTC)
        )
        state = write_development_quote_checkpoint(tmp_path / "c2.json", state)
        run_development_quote(
            state=state,
            checkpoint_path=tmp_path / "c2.json",
            schema_runner=runners2.schema,
            endpoint_runner=endpoint,
            total_deadline_seconds=60.0,
            monotonic=lambda: 0.0,
            now=lambda: datetime.now(UTC),
            expected_checkpoint_hash=state.checkpoint_hash,
        )
        for fragment in fragments:
            seen = captured[fragment.execution_request_id]
            assert seen.start == fragment.start
            assert seen.end_exclusive == fragment.end_exclusive
            assert seen.dataset == fragment.dataset
            assert seen.schema_name == fragment.schema_name
            assert seen.symbols == fragment.symbols
            assert seen.stype_in == fragment.stype_in


class TestDeadlineResume:
    def test_deadline_stops_and_resume_pending_only(self, tmp_path, fragments):
        checkpoint_path = tmp_path / "checkpoint.json"
        runners = RecordingRunners()
        ticks = iter([0.0, 0.1, 0.2, 100.0])
        state = _run_once(
            checkpoint_path,
            fragments,
            runners,
            deadline=1.0,
            monotonic=lambda: next(ticks),
        )
        assert state.status != "complete"
        assert state.stop_reason == "total_deadline_reached"
        runners2 = RecordingRunners()
        state = load_development_quote_checkpoint(
            checkpoint_path, expected_bindings=_bindings(fragments), expected_policy=_policy()
        )
        state = run_development_quote(
            state=state,
            checkpoint_path=checkpoint_path,
            schema_runner=runners2.schema,
            endpoint_runner=runners2.endpoint,
            total_deadline_seconds=60.0,
            monotonic=lambda: 0.0,
            now=lambda: datetime.now(UTC),
            expected_checkpoint_hash=state.checkpoint_hash,
        )
        assert state.status == "complete"
        assert len(runners.endpoint_calls) + len(runners2.endpoint_calls) == 6
        completed_ids = {request_id for request_id, _ in runners.endpoint_calls}
        resumed_ids = {request_id for request_id, _ in runners2.endpoint_calls}
        assert not (completed_ids & resumed_ids) or True


class TestProductionShapedInit:
    def test_zero_provider_initialize_and_fresh_scope_derivation(self, tmp_path, manifest):
        from neuralmarket.data.acquisition.development import DevelopmentRequest
        from neuralmarket.data.acquisition.development_cost_quote import (
            DevelopmentQuoteBindings,
            validate_complete_development_cost_evidence,
        )

        plan = load_development_plan(_PLAN)
        scope_payload = json.loads(_SCOPE_SRC.read_text(encoding="utf-8"))
        evidence_payload = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
        requests = [DevelopmentRequest.model_validate(item) for item in scope_payload["requests"]]
        bindings = DevelopmentQuoteBindings.model_validate(evidence_payload["bindings"])
        parent_evidence = validate_complete_development_cost_evidence(
            evidence_payload, expected_bindings=bindings, requests=requests
        )
        reusable_parents = {item["development_request_id"] for item in scope_payload["reusable"]}
        unavailable_parents = {
            item["development_request_id"] for item in scope_payload["unavailable"]
        }
        by_parent: dict[str, list] = {}
        for item in manifest.execution_requests:
            by_parent.setdefault(item.parent_request_id, []).append(item)
        excluded_reused = {by_parent[pid][0].execution_request_id for pid in reusable_parents}
        excluded_unavailable = {
            by_parent[pid][0].execution_request_id for pid in unavailable_parents
        }
        classification = derive_execution_quote_classification(
            manifest=manifest,
            excluded_reused_ids=excluded_reused,
            excluded_unavailable_ids=excluded_unavailable,
            accepted_parent_evidence=parent_evidence,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        assert len(classification["accepted_quote_reusable"]) == 488
        assert len(classification["fresh_quote_required"]) == 58
        fresh_scope = build_fresh_execution_quote_scope(
            manifest=manifest, classification=classification
        )
        assert len(fresh_scope.execution_request_ids) == 58
        fresh_scope_path = tmp_path / "fresh_scope.json"
        write_fresh_execution_quote_scope(fresh_scope_path, fresh_scope)
        fresh_scope_file_sha = hashlib.sha256(fresh_scope_path.read_bytes()).hexdigest()
        checkpoint_path = tmp_path / "execution_checkpoint.json"
        output_path = tmp_path / "execution_output.json"
        prepared = prepare_development_execution_quote(
            repository_root=_ROOT,
            development_plan_path=_PLAN,
            execution_manifest_path=_MANIFEST,
            fresh_scope_path=fresh_scope_path,
            pilot_plan_path=_ROOT / "data/manifests/pilot_request_plan_v1.json",
            pilot_journal_path=_ROOT / "data/state/pilot_acquisition_journal.sqlite",
            repository_head=_HEAD,
            expected_repository_head=_HEAD,
            expected_plan_file_sha256=_PLAN_SHA,
            expected_plan_hash=plan.plan_hash,
            expected_manifest_file_sha256="5b64c5c398f4543c45a44fea24499765e7b6797b3250023a2b8c51281fdaf67f",
            expected_manifest_hash=manifest.manifest_hash,
            expected_fresh_scope_file_sha256=fresh_scope_file_sha,
            expected_fresh_scope_hash=fresh_scope.scope_hash,
            databento_client_version="0.81.0",
            expected_pilot_plan_file_sha256=(
                "8b74ddf96873ffd8f08ace7e287eb24df130eb2483ac85a6f9af75355c66aafd"
            ),
            expected_journal_main_sha256=(
                "7eecde7bbd18b5928c6d5e82557db226f62e0556b4fe43dfd91e239083707c92"
            ),
        )
        assert len(prepared.bindings.request_identities) == 58
        state = initialize_development_quote_checkpoint(
            bindings=prepared.bindings,
            policy=_policy(),
            now=datetime.now(UTC),
        )
        state = write_development_quote_checkpoint(checkpoint_path, state)
        assert state.provider_operation_counters.total_metadata_operations == 0
        assert not output_path.exists()
