"""Native development paid acquisition execution with durable anti-repurchase state.

The development executor consumes :class:`DevelopmentExecutionRequest`
fragments directly -- never a lossy ``AcquisitionRequest`` conversion -- and
reuses the transactional SQLite :class:`RequestJournal`, the shared execution
state machine, and the pilot guard ordering (authorization -> reservation ->
consumption -> provider call).  Paid progress is journal-authoritative:
completed requests are skipped on resume, and any ambiguous outcome after a
possible paid delivery becomes ``uncertain_billing`` with zero automatic
retry.

No provider is constructed unless a validated authorization exists, the paid
scope is authorization-ready, and every execution request carries an exact
fresh quote within the per-request ceiling.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Literal, Protocol

from pydantic import ValidationError

from neuralmarket.data.acquisition.development_execution import (
    DevelopmentAuthorization,
    DevelopmentExecutionError,
    DevelopmentExecutionManifest,
    DevelopmentExecutionQuote,
    DevelopmentExecutionRequest,
    DevelopmentPaidExecutionScope,
    compute_development_authorization_hash,
    development_execution_quote_gate,
    validate_development_authorization,
)
from neuralmarket.data.acquisition.executor import RawAcquisitionResult
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.manifests import load_json
from neuralmarket.data.acquisition.states import ALLOWED_TRANSITIONS

#: Development paid progress is journal/SQLite authoritative.  The production
#: pilot journal must never be reused for development execution.
DEVELOPMENT_JOURNAL_NAME = "development_acquisition_journal.sqlite"

_ONE_USD = Decimal("1.00")


class PaidDevelopmentProvider(Protocol):
    """A provider that issues real, billable development historical requests."""

    def acquire_range(self, request: DevelopmentExecutionRequest) -> RawAcquisitionResult:
        """Issue one billable development execution request."""
        ...


class DevelopmentLifecycleHooks(Protocol):
    """Raw/normalized/quality operations bound to execution + parent identity."""

    def inspect(
        self, request: DevelopmentExecutionRequest, entry: JournalEntry | None
    ) -> tuple[bool, bool, bool, bool]:
        """Report raw, normalized, quality, and partial artifact validity."""
        ...

    def normalize(
        self, request: DevelopmentExecutionRequest, raw: RawAcquisitionResult
    ) -> tuple[str, str, int]:
        """Reopen raw data and return normalized path, checksum, and bytes."""
        ...

    def quality(self, request: DevelopmentExecutionRequest, normalized_path: str) -> bool:
        """Persist quality evidence and return whether mandatory checks passed."""
        ...


DevelopmentAction = Literal[
    "execute_provider",
    "resume_normalization",
    "resume_quality",
    "skip",
    "block_uncertain_billing",
    "quarantine",
]


@dataclass(frozen=True)
class DevelopmentExecutionResult:
    """Journal-backed summary of one bounded development execution run."""

    execution_id: str
    plan_hash: str
    requests_total: int
    requests_completed: int
    requests_skipped: int
    requests_uncertain: int
    blocking_request: str | None
    blocking_state: str | None
    paid_request_calls: int
    safe_resume_possible: bool
    manual_action_required: bool
    paid_provider_constructed: bool


def _transition(
    journal: RequestJournal, entry: JournalEntry, new_state: str, **fields: object
) -> None:
    current = journal.get(entry.request_id)
    if current is None:
        raise DevelopmentExecutionError(f"journal entry missing: {entry.request_id}")
    if current.state != new_state and (current.state, new_state) not in ALLOWED_TRANSITIONS:
        raise DevelopmentExecutionError(f"illegal state transition: {current.state} -> {new_state}")
    updated = current.model_copy(
        update={
            "state": new_state,
            "updated_at": datetime.now(UTC).isoformat(),
            **fields,
        }
    )
    journal.upsert(updated)


def select_development_execution_action(
    entry: JournalEntry | None,
    *,
    raw_valid: bool,
    normalized_valid: bool,
    quality_valid: bool,
    partial_present: bool,
) -> DevelopmentAction:
    """Choose the only safe next action from durable journal state and artifacts."""
    if partial_present:
        return "quarantine"
    if entry is None:
        return "execute_provider"
    if entry.state in {"request_started", "uncertain_billing"}:
        return "block_uncertain_billing"
    if entry.state == "quality_validated":
        return "skip" if raw_valid and normalized_valid and quality_valid else "quarantine"
    if entry.state == "normalized":
        if not raw_valid or not normalized_valid:
            return "quarantine"
        return "skip" if quality_valid else "resume_quality"
    if entry.state == "raw_validated":
        return "resume_normalization" if raw_valid else "quarantine"
    if entry.state in {"planned", "preflight_validated"}:
        return "execute_provider"
    return "quarantine"


def load_development_authorization(path: Path) -> DevelopmentAuthorization:
    """Load and self-hash-validate a development authorization artifact."""
    try:
        payload = load_json(path)
    except Exception as exc:  # fail closed on any read/parse failure
        raise DevelopmentExecutionError(
            f"development authorization could not be loaded: {exc}"
        ) from exc
    stored_hash = str(payload.get("authorization_hash", ""))
    if not stored_hash:
        stored_hash = compute_development_authorization_hash(
            {key: value for key, value in payload.items() if key != "authorization_hash"}
        )
        payload["authorization_hash"] = stored_hash
    try:
        authorization = DevelopmentAuthorization.model_validate(payload)
    except ValidationError as exc:
        raise DevelopmentExecutionError(f"invalid development authorization: {exc}") from exc
    if not hmac.compare_digest(authorization.authorization_hash, stored_hash):
        raise DevelopmentExecutionError("development authorization hash mismatch")
    return authorization


class _GuardedDevelopmentPaidProvider:
    """Runtime wrapper: exact-scope, per-request cost guard, consume-before-first-call."""

    def __init__(
        self,
        inner: PaidDevelopmentProvider,
        *,
        authorized_execution_hashes: set[str],
        quotes: Mapping[str, DevelopmentExecutionQuote],
        maximum_single_request_usd: Decimal,
        before_first_paid_call: Callable[[], None],
    ) -> None:
        """Bind the guarded provider to the authorized scope and quote evidence."""
        self._inner = inner
        self._authorized_execution_hashes = authorized_execution_hashes
        self._quotes = quotes
        self._maximum_single_request_usd = maximum_single_request_usd
        self._before_first_paid_call = before_first_paid_call
        self._first_call_started = False
        self._acquired_execution_hashes: set[str] = set()
        self._lock = Lock()

    def acquire_range(self, request: DevelopmentExecutionRequest) -> RawAcquisitionResult:
        """Issue one guarded, quote-checked, consume-once paid development request."""
        if request.execution_request_hash not in self._authorized_execution_hashes:
            raise DevelopmentExecutionError(
                f"execution request is not authorized: {request.execution_request_id}"
            )
        development_execution_quote_gate(request, self._quotes, self._maximum_single_request_usd)
        with self._lock:
            if request.execution_request_hash in self._acquired_execution_hashes:
                raise DevelopmentExecutionError(
                    f"execution request already acquired: {request.execution_request_id}"
                )
            self._acquired_execution_hashes.add(request.execution_request_hash)
            if not self._first_call_started:
                self._before_first_paid_call()
                self._first_call_started = True
        return self._inner.acquire_range(request)


class DevelopmentExecutionGuard:
    """Authorization -> reservation -> provider construction with exact bindings."""

    def __init__(self, journal: RequestJournal) -> None:
        """Bind the guard to the transactional development journal."""
        self._journal = journal

    def guard_execute(
        self,
        *,
        plan_hash: str,
        manifest: DevelopmentExecutionManifest,
        scope: DevelopmentPaidExecutionScope,
        authorization_path: Path,
        source_head: str,
        now: datetime,
        quotes: Mapping[str, DevelopmentExecutionQuote],
        maximum_single_request_usd: Decimal = _ONE_USD,
        paid_provider_factory: Callable[[], PaidDevelopmentProvider],
        resume_consumed: bool = False,
    ) -> PaidDevelopmentProvider:
        """Validate, reserve, construct, and wrap a paid development provider."""
        if not scope.authorization_ready:
            raise DevelopmentExecutionError(
                "development paid scope is not authorization-ready; fresh fragment quotes required"
            )
        if scope.plan_hash != plan_hash or scope.execution_manifest_hash != manifest.manifest_hash:
            raise DevelopmentExecutionError("development paid scope binding mismatch")
        authorization = load_development_authorization(authorization_path)
        consumed = (
            self._journal.consumed_authorization_identities() if not resume_consumed else set()
        )
        validate_development_authorization(
            authorization,
            now=now,
            expected_plan_hash=plan_hash,
            expected_manifest_hash=manifest.manifest_hash,
            expected_scope_hash=scope.scope_hash,
            expected_cost_evidence_hash=scope.cost_evidence_hash,
            expected_source_head=source_head,
            expected_maximum_spend_usd=_strict_decimal(
                authorization.maximum_spend_usd, "authorization maximum spend"
            ),
            expected_maximum_single_request_usd=maximum_single_request_usd,
            consumed_ids=consumed,
        )
        execution_id = hashlib.sha256(
            f"{plan_hash}:{authorization.authorization_hash}".encode()
        ).hexdigest()[:32]
        reserved = True
        if not resume_consumed:
            reserved = self._journal.reserve_authorization(
                plan_hash=plan_hash,
                authorization_hash=authorization.authorization_hash,
                execution_id=execution_id,
                reserved_at=now.isoformat(),
            )
        if not reserved:
            raise DevelopmentExecutionError(
                "development authorization rejected: unavailable_or_reserved"
            )
        try:
            inner = paid_provider_factory()
        except Exception as exc:
            if not resume_consumed:
                self._journal.release_reservation(
                    authorization_hash=authorization.authorization_hash,
                    execution_id=execution_id,
                    message="development paid provider construction failed",
                )
            raise DevelopmentExecutionError("development provider construction failed") from exc

        def consume_before_first_call() -> None:
            if resume_consumed:
                return
            if not self._journal.consume_reserved_authorization(
                authorization_hash=authorization.authorization_hash,
                execution_id=execution_id,
                consumed_at=datetime.now(UTC).isoformat(),
                maximum_authorized_spend_usd=str(authorization.maximum_spend_usd),
            ):
                raise DevelopmentExecutionError("development authorization consumption failed")

        return _GuardedDevelopmentPaidProvider(
            inner,
            authorized_execution_hashes=_authorized_hashes(manifest, scope),
            quotes=quotes,
            maximum_single_request_usd=maximum_single_request_usd,
            before_first_paid_call=consume_before_first_call,
        )


def _authorized_hashes(
    manifest: DevelopmentExecutionManifest, scope: DevelopmentPaidExecutionScope
) -> set[str]:
    by_id = {item.execution_request_id: item for item in manifest.execution_requests}
    return {by_id[request_id].execution_request_hash for request_id in scope.execution_request_ids}


def _strict_decimal(value: str, label: str) -> Decimal:
    parsed = Decimal(value)
    if not parsed.is_finite() or parsed < 0:
        raise DevelopmentExecutionError(f"{label} must be a finite non-negative decimal")
    return parsed


class DevelopmentExecutionCoordinator:
    """Own the security-critical development execution order and resume semantics."""

    def execute_paid(
        self,
        *,
        execution_requests: list[DevelopmentExecutionRequest],
        journal_factory: Callable[[], RequestJournal],
        authorization_path: Path,
        plan_hash: str,
        manifest: DevelopmentExecutionManifest,
        scope: DevelopmentPaidExecutionScope,
        quotes: Mapping[str, DevelopmentExecutionQuote],
        lifecycle: DevelopmentLifecycleHooks,
        paid_provider_factory: Callable[[], PaidDevelopmentProvider],
        source_head: str,
        now: datetime,
        deadline_seconds: float,
        monotonic: Callable[[], float] = time.monotonic,
        maximum_single_request_usd: Decimal = _ONE_USD,
    ) -> DevelopmentExecutionResult:
        """Execute or safely resume bounded development paid acquisition."""
        if deadline_seconds <= 0:
            raise DevelopmentExecutionError("development execution deadline must be positive")
        if not scope.authorization_ready:
            raise DevelopmentExecutionError(
                "development paid scope is not authorization-ready; fresh fragment quotes required"
            )
        if scope.plan_hash != plan_hash or scope.execution_manifest_hash != manifest.manifest_hash:
            raise DevelopmentExecutionError("development paid scope binding mismatch")
        with journal_factory() as journal:
            self._prepare(journal, execution_requests, quotes)
            actions: list[tuple[DevelopmentExecutionRequest, DevelopmentAction]] = []
            for request in execution_requests:
                entry = journal.get(request.execution_request_id)
                raw, normalized, quality, partial = lifecycle.inspect(request, entry)
                action = select_development_execution_action(
                    entry,
                    raw_valid=raw,
                    normalized_valid=normalized,
                    quality_valid=quality,
                    partial_present=partial,
                )
                actions.append((request, action))
            blocking = next(
                (
                    (request, action)
                    for request, action in actions
                    if action in {"block_uncertain_billing", "quarantine"}
                ),
                None,
            )
            if blocking is not None:
                return self._report(
                    journal=journal,
                    plan_hash=plan_hash,
                    requests=execution_requests,
                    actions=actions,
                    paid_calls=0,
                    blocking_request=blocking[0].execution_request_id,
                    blocking_state=blocking[1],
                    paid_provider_constructed=False,
                    start_monotonic=monotonic(),
                    deadline=deadline_seconds,
                )

            provider: PaidDevelopmentProvider | None = None
            needs_provider = any(action == "execute_provider" for _, action in actions)
            if needs_provider:
                resume_authorization = load_development_authorization(authorization_path)
                resume_consumed = (
                    resume_authorization.authorization_hash
                    in journal.consumed_authorization_identities()
                )
                provider = DevelopmentExecutionGuard(journal).guard_execute(
                    plan_hash=plan_hash,
                    manifest=manifest,
                    scope=scope,
                    authorization_path=authorization_path,
                    source_head=source_head,
                    now=now,
                    quotes=quotes,
                    maximum_single_request_usd=maximum_single_request_usd,
                    paid_provider_factory=paid_provider_factory,
                    resume_consumed=resume_consumed,
                )

            started = monotonic()
            paid_calls = 0
            for request, action in actions:
                remaining = deadline_seconds - (monotonic() - started)
                if action == "execute_provider" and remaining <= 0:
                    return self._report(
                        journal=journal,
                        plan_hash=plan_hash,
                        requests=execution_requests,
                        actions=actions,
                        paid_calls=paid_calls,
                        blocking_request=None,
                        blocking_state="total_deadline_reached",
                        paid_provider_constructed=provider is not None,
                        start_monotonic=started,
                        deadline=deadline_seconds,
                    )
                entry = journal.get(request.execution_request_id)
                assert entry is not None
                if action == "skip":
                    continue
                try:
                    if action == "execute_provider":
                        assert provider is not None
                        _transition(
                            journal,
                            entry,
                            "request_started",
                            attempt_count=entry.attempt_count + 1,
                            request_started_at=datetime.now(UTC).isoformat(),
                        )
                        paid_calls += 1
                        raw_result = provider.acquire_range(request)
                        _transition(journal, entry, "response_received")
                        _transition(journal, entry, "raw_persisting")
                        _transition(
                            journal,
                            entry,
                            "raw_validated",
                            raw_path=raw_result.raw_path,
                            raw_checksum=raw_result.sha256,
                            raw_record_count=raw_result.record_count,
                            raw_byte_count=Path(raw_result.raw_path).stat().st_size,
                            request_completed_at=datetime.now(UTC).isoformat(),
                        )
                    else:
                        assert entry.raw_path and entry.raw_checksum
                        raw_result = RawAcquisitionResult(
                            request_id=request.execution_request_id,
                            raw_path=entry.raw_path,
                            sha256=entry.raw_checksum,
                            record_count=entry.raw_record_count or 0,
                        )
                    if action in {"execute_provider", "resume_normalization"}:
                        path, checksum, _ = lifecycle.normalize(request, raw_result)
                        _transition(
                            journal,
                            entry,
                            "normalized",
                            normalized_path=path,
                            normalized_checksum=checksum,
                        )
                    normalized_entry = journal.get(request.execution_request_id)
                    assert normalized_entry is not None and normalized_entry.normalized_path
                    if not lifecycle.quality(request, normalized_entry.normalized_path):
                        return self._report(
                            journal=journal,
                            plan_hash=plan_hash,
                            requests=execution_requests,
                            actions=actions,
                            paid_calls=paid_calls,
                            blocking_request=request.execution_request_id,
                            blocking_state="quality_rejected",
                            paid_provider_constructed=provider is not None,
                            start_monotonic=started,
                            deadline=deadline_seconds,
                        )
                    _transition(journal, entry, "quality_validated")
                except Exception as exc:
                    current = journal.get(request.execution_request_id)
                    if current is not None and current.state == "request_started":
                        _transition(
                            journal,
                            current,
                            "uncertain_billing",
                            failure_category=getattr(exc, "category", "paid_invocation_failed"),
                            failure_message=str(exc),
                        )
                        blocking_state = "block_uncertain_billing"
                    else:
                        blocking_state = "local_processing_failure"
                        if current is not None:
                            _transition(
                                journal,
                                current,
                                current.state,
                                failure_category=type(exc).__name__,
                                failure_message=str(exc),
                            )
                    return self._report(
                        journal=journal,
                        plan_hash=plan_hash,
                        requests=execution_requests,
                        actions=actions,
                        paid_calls=paid_calls,
                        blocking_request=request.execution_request_id,
                        blocking_state=blocking_state,
                        paid_provider_constructed=provider is not None,
                        start_monotonic=started,
                        deadline=deadline_seconds,
                    )
            return self._report(
                journal=journal,
                plan_hash=plan_hash,
                requests=execution_requests,
                actions=actions,
                paid_calls=paid_calls,
                blocking_request=None,
                blocking_state=None,
                paid_provider_constructed=provider is not None,
                start_monotonic=started,
                deadline=deadline_seconds,
            )

    @staticmethod
    def _prepare(
        journal: RequestJournal,
        execution_requests: list[DevelopmentExecutionRequest],
        quotes: Mapping[str, DevelopmentExecutionQuote],
    ) -> None:
        timestamp = datetime.now(UTC).isoformat()
        for request in execution_requests:
            existing = journal.get(request.execution_request_id)
            if existing is not None:
                continue
            quote = quotes.get(request.execution_request_id)
            if quote is None:
                raise DevelopmentExecutionError(
                    f"execution request has no fresh quote: {request.execution_request_id}"
                )
            journal.upsert(
                JournalEntry(
                    request_id=request.execution_request_id,
                    request_hash=request.execution_request_hash,
                    state="planned",
                    attempt_count=0,
                    estimated_cost_usd=quote.cost_usd,
                    actual_billed_cost_usd=None,
                    raw_path=None,
                    raw_checksum=None,
                    normalized_path=None,
                    normalized_checksum=None,
                    failure_category=None,
                    failure_message=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
            entry = journal.get(request.execution_request_id)
            assert entry is not None
            _transition(journal, entry, "preflight_validated")

    @staticmethod
    def _report(
        *,
        journal: RequestJournal,
        plan_hash: str,
        requests: list[DevelopmentExecutionRequest],
        actions: list[tuple[DevelopmentExecutionRequest, DevelopmentAction]],
        paid_calls: int,
        blocking_request: str | None,
        blocking_state: str | None,
        paid_provider_constructed: bool,
        start_monotonic: float,
        deadline: float,
    ) -> DevelopmentExecutionResult:
        del start_monotonic, deadline
        entries = [
            entry
            for request in requests
            if (entry := journal.get(request.execution_request_id)) is not None
        ]
        complete = [entry for entry in entries if entry.state == "quality_validated"]
        uncertain = [entry for entry in entries if entry.state == "uncertain_billing"]
        skipped = sum(action == "skip" for _, action in actions)
        execution_id = hashlib.sha256(plan_hash.encode()).hexdigest()[:32]
        safe_resume_possible = blocking_state in {
            None,
            "local_processing_failure",
            "total_deadline_reached",
        }
        manual_action_required = blocking_state not in {
            None,
            "local_processing_failure",
            "total_deadline_reached",
        }
        if blocking_state is None:
            attempt_status = "completed"
        elif blocking_state == "block_uncertain_billing":
            attempt_status = "blocked_uncertain_billing"
        elif blocking_state == "total_deadline_reached":
            attempt_status = "deadline_reached"
        else:
            attempt_status = "blocked"
        journal.finalize_execution_attempt(
            execution_id=execution_id,
            status=attempt_status,
            finished_at=datetime.now(UTC).isoformat(),
            blocking_request=blocking_request,
            blocking_state=blocking_state,
            requests_completed=len(complete),
            requests_uncertain=len(uncertain),
            paid_request_calls=paid_calls,
            downloaded_records=sum(entry.raw_record_count or 0 for entry in entries),
            manual_action_required=manual_action_required,
        )
        return DevelopmentExecutionResult(
            execution_id=execution_id,
            plan_hash=plan_hash,
            requests_total=len(requests),
            requests_completed=len(complete),
            requests_skipped=skipped,
            requests_uncertain=len(uncertain),
            blocking_request=blocking_request,
            blocking_state=blocking_state,
            paid_request_calls=paid_calls,
            safe_resume_possible=safe_resume_possible,
            manual_action_required=manual_action_required,
            paid_provider_constructed=paid_provider_constructed,
        )
