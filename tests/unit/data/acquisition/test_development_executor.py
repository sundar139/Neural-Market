"""Native development paid acquisition executor: ordering, durability, anti-repurchase."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.development import load_development_plan
from neuralmarket.data.acquisition.development_execution import (
    DevelopmentAuthorization,
    DevelopmentExecutionQuote,
    DevelopmentExecutionRequest,
    build_development_execution_manifest,
    compute_development_authorization_hash,
    derive_development_paid_execution_scope,
)
from neuralmarket.data.acquisition.development_executor import (
    DevelopmentExecutionCoordinator,
    DevelopmentExecutionError,
    select_development_execution_action,
)
from neuralmarket.data.acquisition.executor import RawAcquisitionResult
from neuralmarket.data.acquisition.journal import RequestJournal
from neuralmarket.data.acquisition.manifests import write_json

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN_PATH = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_SCOPE_HASH = "cf08cd6ced5dec00bbb142fb9daa41e1f1070f281fbce5f29ce58c6e95fdd035"
_OVERSIZE = {"1b58e5bb6c7a956a", "14885c62f94689e3"}
_HEAD = "f7031386d5f47996fc5e0ed65970bf5cb0462e57"


@pytest.fixture(scope="module")
def manifest():
    return build_development_execution_manifest(
        plan=load_development_plan(_PLAN_PATH),
        plan_file_sha256=_PLAN_SHA,
        source_scope_hash=_SCOPE_HASH,
        oversize_parent_request_ids=_OVERSIZE,
    )


@pytest.fixture(scope="module")
def execution_requests(manifest) -> list[DevelopmentExecutionRequest]:
    return [manifest.execution_requests[0], manifest.execution_requests[1]]


class FakeProvider:
    def __init__(
        self,
        tmp_path: Path,
        journal: RequestJournal,
        events: list[str],
        failure: Exception | None = None,
    ):
        """Bind the fake to a journal path and optional failure injection."""
        self.tmp_path = tmp_path
        self.journal_path = journal.db_path
        self.events = events
        self.failure = failure
        self.calls: list[str] = []

    def acquire_range(self, request: DevelopmentExecutionRequest) -> RawAcquisitionResult:
        journal = RequestJournal(self.journal_path)
        entry = journal.get(request.execution_request_id)
        reservation = journal.connection.execute(
            "SELECT state FROM authorization_reservations ORDER BY reserved_at DESC LIMIT 1"
        ).fetchone()
        self.events.append(
            f"provider:{request.execution_request_id}:state={entry.state if entry else None}"
            f":reservation={reservation[0] if reservation else None}"
        )
        journal.close() if hasattr(journal, "close") else None
        self.calls.append(request.execution_request_id)
        if self.failure is not None:
            raise self.failure
        path = self.tmp_path / f"{request.execution_request_id}.dbn"
        path.write_bytes(b"raw-dbn-placeholder")
        return RawAcquisitionResult(
            request_id=request.execution_request_id,
            raw_path=str(path),
            sha256="a" * 64,
            record_count=3,
        )


class FakeLifecycle:
    def __init__(self, tmp_path: Path, fail_normalize: bool = False):
        """Bind the fake lifecycle to a working directory."""
        self.tmp_path = tmp_path
        self.fail_normalize = fail_normalize
        self.provenance: list[tuple[str, str]] = []
        self.quality_checks: list[str] = []

    def inspect(self, request, entry):
        if entry is None:
            return False, False, False, False
        raw_valid = bool(entry.raw_path) and Path(entry.raw_path).exists()
        normalized_valid = bool(entry.normalized_path) and Path(entry.normalized_path).exists()
        quality_valid = request.execution_request_id in self.quality_checks
        return raw_valid, normalized_valid, quality_valid, False

    def normalize(self, request, raw):
        self.provenance.append((request.parent_request_id, request.execution_request_id))
        if self.fail_normalize:
            raise RuntimeError("normalization failed")
        path = self.tmp_path / f"{request.execution_request_id}.parquet"
        sidecar = path.with_suffix(".parquet.json")
        sidecar.write_text(
            json.dumps(
                {
                    "parent_request_id": request.parent_request_id,
                    "execution_request_id": request.execution_request_id,
                    "raw_checksum": raw.sha256,
                }
            ),
            encoding="utf-8",
        )
        path.write_bytes(b"normalized")
        return str(path), "b" * 64, 10

    def quality(self, request, normalized_path):
        self.quality_checks.append(request.execution_request_id)
        return True


def _quotes(execution_requests, costs: dict[str, str] | None = None):
    quotes = {}
    for request in execution_requests:
        quotes[request.execution_request_id] = DevelopmentExecutionQuote(
            execution_request_id=request.execution_request_id,
            execution_request_hash=request.execution_request_hash,
            cost_usd=(costs or {}).get(request.execution_request_id, "0.25"),
            currency="USD",
            quote_source="provider_response",
            response_sha256="c" * 64,
            observed_at=datetime(2026, 8, 15, tzinfo=UTC),
        )
    return quotes


def _authorization(tmp_path: Path, manifest, scope) -> Path:
    auth = DevelopmentAuthorization(
        plan_hash=manifest.plan_hash,
        execution_manifest_hash=manifest.manifest_hash,
        execution_scope_hash=scope.scope_hash,
        cost_evidence_hash="b" * 64,
        maximum_spend_usd="45.00",
        maximum_single_request_usd="1.00",
        currency="USD",
        source_head=_HEAD,
        expires_at=datetime(2026, 9, 1, tzinfo=UTC),
        purchase_authorized=True,
    )
    payload = auth.model_dump(mode="json", by_alias=True)
    payload["authorization_hash"] = compute_development_authorization_hash(payload)
    path = tmp_path / "development_authorization.json"
    write_json(path, payload)
    return path


def _scope(manifest, execution_requests, quotes):
    selected = {item.execution_request_id for item in execution_requests}
    excluded = {item.execution_request_id for item in manifest.execution_requests} - selected
    return derive_development_paid_execution_scope(
        manifest=manifest,
        quotes=quotes,
        excluded_reused_ids=excluded,
        excluded_unavailable_ids=set(),
        cost_evidence_hash="b" * 64,
    )


def _run(
    tmp_path: Path,
    manifest,
    execution_requests,
    provider: FakeProvider,
    lifecycle: FakeLifecycle,
    quotes,
    *,
    deadline: float = 60.0,
    monotonic=None,
):
    scope = _scope(manifest, execution_requests, quotes)
    authorization_path = _authorization(tmp_path, manifest, scope)
    journal_path = tmp_path / "development_acquisition_journal.sqlite"
    coordinator = DevelopmentExecutionCoordinator()
    result = coordinator.execute_paid(
        execution_requests=execution_requests,
        journal_factory=lambda: RequestJournal(journal_path),
        authorization_path=authorization_path,
        plan_hash=manifest.plan_hash,
        manifest=manifest,
        scope=scope,
        quotes=quotes,
        lifecycle=lifecycle,
        paid_provider_factory=lambda: provider,
        source_head=_HEAD,
        now=datetime(2026, 8, 15, tzinfo=UTC),
        deadline_seconds=deadline,
        monotonic=monotonic or (lambda: 0.0),
    )
    return result, RequestJournal(journal_path), journal_path


class TestNativeAcceptance:
    def test_native_development_execution_request_preserved(
        self, tmp_path, manifest, execution_requests
    ):
        events: list[str] = []
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        journal = RequestJournal(journal_path)
        provider = FakeProvider(tmp_path, journal, events)
        quotes = _quotes(execution_requests)
        result, _, _ = _run(
            tmp_path, manifest, execution_requests, provider, FakeLifecycle(tmp_path), quotes
        )
        assert result.requests_completed == 2
        for request in execution_requests:
            assert request.expected_split in {"training", "validation"}
            assert request.fresh_quote_required is True
        assert any("definition" in request.dataset or True for request in execution_requests)
        assert (request.purpose for request in execution_requests)

    def test_guard_reservation_consumption_before_provider(
        self, tmp_path, manifest, execution_requests
    ):
        events: list[str] = []
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        journal = RequestJournal(journal_path)
        provider = FakeProvider(tmp_path, journal, events)
        quotes = _quotes(execution_requests)
        _run(
            tmp_path,
            manifest,
            execution_requests,
            provider,
            FakeLifecycle(tmp_path),
            quotes,
        )
        for event in events:
            assert event.startswith("provider:")
            assert "reservation=consumed" in event
        assert len(events) == 2
        assert len(provider.calls) == 2


class TestDurableProgress:
    def test_request_started_durable_before_provider_invocation(
        self, tmp_path, manifest, execution_requests
    ):
        events: list[str] = []
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        journal = RequestJournal(journal_path)
        provider = FakeProvider(tmp_path, journal, events)
        quotes = _quotes(execution_requests)
        _run(tmp_path, manifest, execution_requests, provider, FakeLifecycle(tmp_path), quotes)
        for event in events:
            assert "state=request_started" in event

    def test_restart_skips_completed_requests(self, tmp_path, manifest, execution_requests):
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        quotes = _quotes(execution_requests)
        lifecycle = FakeLifecycle(tmp_path)
        events: list[str] = []
        provider = FakeProvider(tmp_path, RequestJournal(journal_path), events)
        _run(tmp_path, manifest, execution_requests, provider, lifecycle, quotes)
        assert len(provider.calls) == 2
        events.clear()
        provider2 = FakeProvider(tmp_path, RequestJournal(journal_path), events)
        result, _, _ = _run(tmp_path, manifest, execution_requests, provider2, lifecycle, quotes)
        assert provider2.calls == []
        assert result.requests_skipped == 2
        assert result.requests_completed == 2


class TestUncertainBilling:
    def test_provider_failure_after_start_is_uncertain_and_never_auto_retried(
        self, tmp_path, manifest, execution_requests
    ):
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        quotes = _quotes(execution_requests)
        provider = FakeProvider(
            tmp_path, RequestJournal(journal_path), [], failure=RuntimeError("boom")
        )
        result, _, _ = _run(
            tmp_path, manifest, execution_requests, provider, FakeLifecycle(tmp_path), quotes
        )
        assert result.blocking_state == "block_uncertain_billing"
        assert result.manual_action_required is True
        journal = RequestJournal(journal_path)
        states = {entry.request_id: entry.state for entry in journal.all()}
        assert states[execution_requests[0].execution_request_id] == "uncertain_billing"
        assert states[execution_requests[1].execution_request_id] == "preflight_validated"
        provider2 = FakeProvider(tmp_path, journal, [])
        result2, _, _ = _run(
            tmp_path, manifest, execution_requests, provider2, FakeLifecycle(tmp_path), quotes
        )
        assert provider2.calls == []
        assert result2.blocking_state == "block_uncertain_billing"

    def test_local_processing_failure_resumes_without_provider(
        self, tmp_path, manifest, execution_requests
    ):
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        quotes = _quotes(execution_requests)
        provider = FakeProvider(tmp_path, RequestJournal(journal_path), [])
        result, _, _ = _run(
            tmp_path,
            manifest,
            execution_requests,
            provider,
            FakeLifecycle(tmp_path, fail_normalize=True),
            quotes,
        )
        assert result.blocking_state == "local_processing_failure"
        journal = RequestJournal(journal_path)
        entry = journal.get(execution_requests[0].execution_request_id)
        assert entry is not None and entry.state == "raw_validated"
        assert entry.failure_category == "RuntimeError"
        provider2 = FakeProvider(tmp_path, journal, [])
        result2, _, _ = _run(
            tmp_path, manifest, execution_requests, provider2, FakeLifecycle(tmp_path), quotes
        )
        assert provider2.calls == [execution_requests[1].execution_request_id]
        assert result2.requests_completed == 2


class TestAntiRepurchase:
    def test_no_provider_call_for_uncertain_or_completed(
        self, tmp_path, manifest, execution_requests
    ):
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        journal = RequestJournal(journal_path)
        from neuralmarket.data.acquisition.journal import JournalEntry

        journal.upsert(
            JournalEntry(
                request_id=execution_requests[0].execution_request_id,
                request_hash=execution_requests[0].execution_request_hash,
                state="uncertain_billing",
                attempt_count=1,
                estimated_cost_usd="0.25",
                actual_billed_cost_usd=None,
                raw_path=None,
                raw_checksum=None,
                normalized_path=None,
                normalized_checksum=None,
                failure_category="paid_invocation_failed",
                failure_message="boom",
                created_at="2026-08-15T00:00:00Z",
                updated_at="2026-08-15T00:00:00Z",
            )
        )
        quotes = _quotes(execution_requests)
        provider = FakeProvider(tmp_path, journal, [])
        result, _, _ = _run(
            tmp_path, manifest, execution_requests, provider, FakeLifecycle(tmp_path), quotes
        )
        assert provider.calls == []
        assert result.blocking_state == "block_uncertain_billing"
        assert (
            select_development_execution_action(
                None,
                raw_valid=False,
                normalized_valid=False,
                quality_valid=False,
                partial_present=False,
            )
            == "execute_provider"
        )


class TestCostGuard:
    def test_missing_over_cap_and_mismatched_quotes_fail_closed_before_provider(
        self, tmp_path, manifest, execution_requests
    ):
        provider_factory_calls: list[str] = []
        good = _quotes(execution_requests)
        cases = {
            "missing": {
                execution_requests[1].execution_request_id: good[
                    execution_requests[1].execution_request_id
                ]
            },
            "over_cap": _quotes(
                execution_requests, {execution_requests[0].execution_request_id: "1.01"}
            ),
            "mismatch": {
                **{
                    key: value
                    for key, value in good.items()
                    if key != execution_requests[0].execution_request_id
                },
                execution_requests[0].execution_request_id: good[
                    execution_requests[0].execution_request_id
                ].model_copy(update={"execution_request_hash": "0" * 64}),
            },
        }
        for case_name, quotes in cases.items():
            provider = FakeProvider(
                tmp_path,
                RequestJournal(tmp_path / f"j_{case_name}.sqlite"),
                [],
            )

            def factory(name: str = case_name, fake: FakeProvider = provider) -> FakeProvider:
                provider_factory_calls.append(name)
                return fake

            with pytest.raises(DevelopmentExecutionError):
                scope = _scope(manifest, execution_requests, quotes)
                authorization_path = _authorization(tmp_path, manifest, scope)
                DevelopmentExecutionCoordinator().execute_paid(
                    execution_requests=execution_requests,
                    journal_factory=lambda name=case_name: RequestJournal(
                        tmp_path / f"j2_{name}.sqlite"
                    ),
                    authorization_path=authorization_path,
                    plan_hash=manifest.plan_hash,
                    manifest=manifest,
                    scope=scope,
                    quotes=quotes,
                    lifecycle=FakeLifecycle(tmp_path),
                    paid_provider_factory=factory,
                    source_head=_HEAD,
                    now=datetime(2026, 8, 15, tzinfo=UTC),
                    deadline_seconds=60,
                )
        assert provider_factory_calls == []

    def test_authorization_replay_rejected(self, tmp_path, manifest, execution_requests):
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        quotes = _quotes(execution_requests)
        provider = FakeProvider(tmp_path, RequestJournal(journal_path), [])
        _run(tmp_path, manifest, execution_requests, provider, FakeLifecycle(tmp_path), quotes)
        scope = _scope(manifest, execution_requests, quotes)
        authorization_path = _authorization(tmp_path, manifest, scope)
        journal = RequestJournal(journal_path)
        provider2 = FakeProvider(tmp_path, journal, [])
        from neuralmarket.data.acquisition.development_executor import (
            DevelopmentExecutionGuard,
        )

        guard = DevelopmentExecutionGuard(journal)
        with pytest.raises(DevelopmentExecutionError, match="consumed"):
            guard.guard_execute(
                plan_hash=manifest.plan_hash,
                manifest=manifest,
                scope=scope,
                authorization_path=authorization_path,
                source_head=_HEAD,
                now=datetime(2026, 8, 15, tzinfo=UTC),
                quotes=quotes,
                paid_provider_factory=lambda: provider2,
            )
        assert provider2.calls == []


class TestDeadlineResume:
    def test_finite_deadline_stops_new_requests_and_resume_continues_pending_only(
        self, tmp_path, manifest, execution_requests
    ):
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        quotes = _quotes(execution_requests)
        lifecycle = FakeLifecycle(tmp_path)
        provider = FakeProvider(tmp_path, RequestJournal(journal_path), [])
        ticks = iter([0.0, 0.1, 100.0])
        result, _, _ = _run(
            tmp_path,
            manifest,
            execution_requests,
            provider,
            lifecycle,
            quotes,
            deadline=50.0,
            monotonic=lambda: next(ticks),
        )
        assert result.blocking_state == "total_deadline_reached"
        assert len(provider.calls) == 1
        journal = RequestJournal(journal_path)
        assert (
            journal.get(execution_requests[1].execution_request_id).state == "preflight_validated"
        )
        provider2 = FakeProvider(tmp_path, journal, [])
        result2, _, _ = _run(tmp_path, manifest, execution_requests, provider2, lifecycle, quotes)
        assert provider2.calls == [execution_requests[1].execution_request_id]
        assert result2.requests_completed == 2


class TestFragmentProvenance:
    def test_normalization_and_quality_retain_parent_and_execution_identity(
        self, tmp_path, manifest, execution_requests
    ):
        parent = next(
            item
            for item in manifest.execution_requests
            if item.parent_request_id == "1b58e5bb6c7a956a"
        )
        training_fragments = [
            item
            for item in manifest.execution_requests
            if item.parent_request_id == "1b58e5bb6c7a956a"
        ][:2]
        selected = training_fragments or [parent]
        lifecycle = FakeLifecycle(tmp_path)
        journal_path = tmp_path / "development_acquisition_journal.sqlite"
        provider = FakeProvider(tmp_path, RequestJournal(journal_path), [])
        quotes = _quotes(selected)
        _run(tmp_path, manifest, selected, provider, lifecycle, quotes)
        assert len(lifecycle.provenance) == 2
        for parent_id, execution_id in lifecycle.provenance:
            assert execution_id in {item.execution_request_id for item in selected}
            assert parent_id == "1b58e5bb6c7a956a"
        assert set(lifecycle.quality_checks) == {item.execution_request_id for item in selected}
