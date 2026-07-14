"""Pilot executor: state machine, provider isolation, and the dual money guard.

This is the central safety module of the guarded pilot acquisition feature. A
real paid Databento request must be *structurally impossible* without BOTH:

1. a valid, single-use, hash-bound authorization artifact (Task 5), and
2. an explicit CLI plan-hash confirmation that matches the plan under review.

Provider isolation is enforced at the type level: :class:`PilotExecutor` has no
paid-provider constructor parameter, so a paid client cannot exist as an
attribute on it. The only way to obtain one is the guarded return value of
:meth:`PilotExecutor.guard_execute`, which constructs it via an injected
factory *only after both guards pass*. Every failure mode fails closed -- it
raises :class:`ExecutorGuardError` and never calls the factory.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.authorization import (
    AuthorizationError,
    load_authorization,
    validate_authorization,
)
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.acquisition.estimation import MetadataEstimator
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.preflight import run_preflight
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    PilotExecutionConfig,
    validate_canonical_pilot_plan,
    verify_final_request,
)
from neuralmarket.data.acquisition.requests import (
    plan_hash as compute_plan_hash,
)
from neuralmarket.data.acquisition.states import ALLOWED_TRANSITIONS


class MetadataProvider(Protocol):
    """Metadata-only provider (record counts / sizes / cost), never paid data.

    A metadata provider is freely constructible during planning and preflight;
    it can never trigger a billable time-series download.
    """

    def get_record_count(self, **kwargs: object) -> object:
        """Return the metadata-estimated record count for a query window."""
        ...

    def get_billable_size(self, **kwargs: object) -> object:
        """Return the metadata-estimated billable size in bytes."""
        ...

    def get_cost(self, **kwargs: object) -> object:
        """Return the metadata-estimated cost for a query window."""
        ...


class RawAcquisitionResult(BaseModel):
    """Result of a single billable range download from a paid provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    raw_path: str
    sha256: str
    record_count: int


class ValidationOnlyResult(BaseModel):
    """Evidence that metadata preflight completed without paid capabilities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ready_for_paid_execution: bool
    fresh_preflight_hash: str
    estimated_total_cost: str
    largest_request_cost: str
    metadata_client_constructed: bool = True
    paid_provider_constructed: bool = False
    timeseries_namespace_accessed: bool = False
    batch_namespace_accessed: bool = False
    live_client_constructed: bool = False
    journal_created: bool = False
    authorization_reserved: bool = False
    authorization_consumed: bool = False
    paid_request_calls: int = 0
    download_attempts: int = 0
    downloaded_records: int = 0
    portal_limit_status: str = "operator_attested"


class PilotExecutionResult(BaseModel):
    """Typed, conservative report for one paid execution attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    plan_hash: str
    authorization_hash: str
    portal_attestation_hash: str
    fresh_preflight_hash: str
    requests_planned: int
    requests_completed: int
    requests_skipped: int
    requests_failed: int
    requests_uncertain: int
    last_completed_request: str | None
    blocking_request: str | None
    blocking_state: str | None
    safe_resume_possible: bool
    manual_action_required: bool
    estimated_total_cost: str
    actual_provider_cost_status: str = "unavailable_pending_portal_reconciliation"
    raw_bytes: int
    normalized_bytes: int
    quality_summary: dict[str, int]
    metadata_client_constructed: bool = True
    paid_provider_constructed: bool
    paid_request_calls: int
    download_attempts: int
    downloaded_records: int


RecoveryAction = Literal[
    "skip",
    "resume_normalization",
    "resume_quality",
    "execute_provider",
    "block_uncertain_billing",
    "quarantine",
    "manual_recovery_required",
]


def select_recovery_action(
    entry: JournalEntry | None,
    *,
    raw_valid: bool,
    normalized_valid: bool,
    quality_valid: bool,
    partial_present: bool,
) -> RecoveryAction:
    """Choose the only safe next action from durable state and artifacts."""
    if partial_present:
        return "manual_recovery_required"
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


class LifecycleHooks(Protocol):
    """Existing storage/normalization/quality operations used by the coordinator."""

    def inspect(
        self, request: AcquisitionRequest, entry: JournalEntry | None
    ) -> tuple[bool, bool, bool, bool]:
        """Report raw, normalized, quality, and partial artifact validity."""
        ...

    def normalize(
        self, request: AcquisitionRequest, raw: RawAcquisitionResult
    ) -> tuple[str, str, int]:
        """Reopen raw data and return normalized path, checksum, and bytes."""
        ...

    def quality(self, request: AcquisitionRequest, normalized_path: str) -> bool:
        """Persist quality evidence and return whether mandatory checks passed."""
        ...


class PaidHistoricalProvider(Protocol):
    """A provider that issues real, billable historical-data requests.

    An instance of this can only be produced through the guarded factory in
    :meth:`PilotExecutor.guard_execute`.
    """

    def acquire_range(self, request: AcquisitionRequest) -> RawAcquisitionResult:
        """Issue one real, billable historical-data range download."""
        ...


class _GuardedPaidHistoricalProvider:
    """Runtime wrapper limiting paid acquisition to authorized request hashes."""

    def __init__(
        self,
        inner: PaidHistoricalProvider,
        *,
        authorized_request_hashes: set[str],
        maximum_single_request_usd: Decimal,
        before_first_paid_call: Callable[[], None],
    ) -> None:
        self._inner = inner
        self._authorized_request_hashes = authorized_request_hashes
        self._maximum_single_request_usd = maximum_single_request_usd
        self._before_first_paid_call = before_first_paid_call
        self._first_call_started = False
        self._acquired_request_hashes: set[str] = set()
        self._lock = Lock()

    def acquire_range(self, request: AcquisitionRequest) -> RawAcquisitionResult:
        verify_final_request(request)
        if request.request_hash not in self._authorized_request_hashes:
            raise ExecutorGuardError(
                "request_not_authorized",
                f"request is not in the authorized plan: {request.request_id}",
            )
        if to_decimal(request.estimated_cost) > self._maximum_single_request_usd:
            raise ExecutorGuardError(
                "request_cap_exceeded",
                f"request exceeds authorized cap: {request.request_id}",
            )
        with self._lock:
            if request.request_hash in self._acquired_request_hashes:
                raise ExecutorGuardError(
                    "request_already_acquired",
                    f"request already acquired under this authorization: {request.request_id}",
                )
            self._acquired_request_hashes.add(request.request_hash)
            if not self._first_call_started:
                self._before_first_paid_call()
                self._first_call_started = True
        return self._inner.acquire_range(request)


class ExecutorGuardError(RuntimeError):
    """Raised when a guarded paid execution is blocked. Fails closed.

    ``reason`` is a short machine-readable code, one of:
    ``"missing_authorization"``, ``"invalid_authorization"``,
    ``"plan_hash_confirmation_mismatch"``, ``"preflight_not_passed"``.
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        """Store the machine-readable ``reason`` alongside the message."""
        self.reason = reason
        super().__init__(message or reason)


class PilotExecutor:
    """Drives request lifecycle state and gates all paid execution.

    Note the constructor takes *no* paid-provider argument: provider isolation
    is the whole point. A paid provider only ever materializes as the return
    value of :meth:`guard_execute`, after both guards pass.
    """

    def __init__(
        self, *, journal: RequestJournal, metadata_estimator: MetadataEstimator | None = None
    ) -> None:
        """Bind the executor to a request journal and a metadata-only estimator."""
        self._journal = journal
        self._metadata_estimator = metadata_estimator

    def prepare(self, requests: list[AcquisitionRequest]) -> None:
        """Write every request to the journal in the ``planned`` state."""
        if any(request.estimated_cost is None for request in requests):
            raise ValueError("cannot journal an acquisition request without a fresh estimate")
        now = datetime.now(UTC).isoformat()
        for request in requests:
            assert request.estimated_cost is not None
            self._journal.upsert(
                JournalEntry(
                    request_id=request.request_id,
                    request_hash=request.request_hash,
                    state="planned",
                    attempt_count=0,
                    estimated_cost_usd=request.estimated_cost,
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

    def transition(self, request_id: str, new_state: str, **journal_fields: object) -> None:
        """Move ``request_id`` to ``new_state``, rejecting illegal transitions.

        Legality is checked against the shared ``ALLOWED_TRANSITIONS`` table
        from :mod:`neuralmarket.data.acquisition.states` (the same table the
        journal enforces), so an executor bug fails loudly rather than
        corrupting state.
        """
        entry = self._journal.get(request_id)
        if entry is None:
            raise ValueError(f"no journal entry for request {request_id}")
        if entry.state != new_state and (entry.state, new_state) not in ALLOWED_TRANSITIONS:
            raise ValueError(f"illegal state transition: {entry.state} -> {new_state}")
        updated = entry.model_copy(
            update={
                "state": new_state,
                "updated_at": datetime.now(UTC).isoformat(),
                **journal_fields,
            }
        )
        self._journal.upsert(updated)

    def guard_execute(
        self,
        *,
        plan_hash: str,
        authorization_path: Path,
        confirm_plan_hash: str,
        source_manifest_hash: str,
        split_manifest_hash: str,
        acquisition_policy_hash: str,
        now: datetime,
        paid_provider_factory: Callable[[], PaidHistoricalProvider],
        authorized_requests: list[AcquisitionRequest] | None = None,
        plan_bindings: dict[str, object] | None = None,
        plan_metadata: dict[str, Any] | None = None,
        preflight_passed: bool = False,
        expected_maximum_spend_usd: Decimal = Decimal("5.00"),
        expected_maximum_single_request_usd: Decimal = Decimal("1.00"),
        resume_consumed: bool = False,
    ) -> PaidHistoricalProvider:
        """Construct a paid provider ONLY if both money guards pass.

        Guard 1 (authorization): load and fully validate the authorization
        artifact against the live plan/manifest/policy hashes, expiry,
        single-use consumption, currency, confirmation phrase and explicit
        purchase flag. Guard 2 (confirmation): the caller-supplied
        ``confirm_plan_hash`` must equal ``plan_hash`` (constant-time compare).

        The injected ``paid_provider_factory`` is called *only after both
        guards pass*. Every failure path raises :class:`ExecutorGuardError`
        and never touches the factory.

        Raises:
            ExecutorGuardError: ``missing_authorization`` if the file is
                absent, ``invalid_authorization`` on any parse/schema/model/
                validation failure, ``plan_hash_confirmation_mismatch`` if the
                confirmation hash does not match the plan hash.
        """
        if not preflight_passed:
            raise ExecutorGuardError(
                "preflight_not_passed",
                "fresh metadata preflight has not passed for this finalized plan",
            )

        # --- Guard 1: authorization artifact -----------------------------
        try:
            auth = load_authorization(authorization_path)
        except FileNotFoundError as exc:
            raise ExecutorGuardError(
                "missing_authorization", f"authorization file not found: {authorization_path}"
            ) from exc
        except Exception as exc:  # fail closed on any parse/schema/model failure
            raise ExecutorGuardError(
                "invalid_authorization", f"authorization file could not be loaded: {exc}"
            ) from exc

        try:
            validate_authorization(
                auth,
                expected_plan_hash=plan_hash,
                expected_source_manifest_hash=source_manifest_hash,
                expected_split_manifest_hash=split_manifest_hash,
                expected_acquisition_policy_hash=acquisition_policy_hash,
                expected_maximum_spend_usd=expected_maximum_spend_usd,
                expected_maximum_single_request_usd=expected_maximum_single_request_usd,
                now=now,
                consumed_ids=(
                    set() if resume_consumed else self._journal.consumed_authorization_ids()
                ),
            )
        except AuthorizationError as exc:
            raise ExecutorGuardError(
                "invalid_authorization", f"authorization rejected: {exc.reason}"
            ) from exc

        # --- Guard 2: explicit plan-hash confirmation --------------------
        if not hmac.compare_digest(confirm_plan_hash, plan_hash):
            raise ExecutorGuardError(
                "plan_hash_confirmation_mismatch",
                "confirm_plan_hash does not match the plan under review",
            )

        if not authorized_requests:
            raise ExecutorGuardError(
                "missing_authorized_requests",
                "finalized request list is required before paid provider construction",
            )
        authorized_hashes: set[str] = set()
        authorized_total = Decimal("0")
        authorized_maximum = Decimal("0")
        for request in authorized_requests:
            try:
                verify_final_request(request)
                cost = to_decimal(request.estimated_cost)
            except Exception as exc:
                raise ExecutorGuardError(
                    "invalid_authorized_request",
                    f"authorized request rejected: {request.request_id}",
                ) from exc
            authorized_hashes.add(request.request_hash)
            authorized_total += cost
            authorized_maximum = max(authorized_maximum, cost)
        if authorized_total > expected_maximum_spend_usd:
            raise ExecutorGuardError(
                "plan_cap_exceeded", "authorized request plan exceeds total cap"
            )
        if authorized_maximum > expected_maximum_single_request_usd:
            raise ExecutorGuardError(
                "request_cap_exceeded", "authorized request plan exceeds per-request cap"
            )
        if plan_bindings is None:
            raise ExecutorGuardError(
                "missing_plan_bindings",
                "plan dependency bindings are required before paid provider construction",
            )
        expected_bindings = {
            "source_manifest_hash": source_manifest_hash,
            "split_manifest_hash": split_manifest_hash,
            "acquisition_policy_hash": acquisition_policy_hash,
        }
        if any(plan_bindings.get(key) != value for key, value in expected_bindings.items()):
            raise ExecutorGuardError(
                "plan_dependency_mismatch",
                "plan dependency bindings do not match the authorized dependencies",
            )
        if not hmac.compare_digest(
            compute_plan_hash(authorized_requests, plan_bindings, plan_metadata), plan_hash
        ):
            raise ExecutorGuardError(
                "authorized_requests_plan_mismatch",
                "authorized requests do not match the authorized plan hash",
            )

        resumable_states = {
            "preflight_validated",
            "raw_validated",
            "normalized",
            "quality_validated",
        }
        for request in authorized_requests:
            entry = self._journal.get(request.request_id)
            if entry is None or entry.state not in resumable_states:
                raise ExecutorGuardError(
                    "preflight_not_passed",
                    f"request is not preflight validated: {request.request_id}",
                )

        execution_id = hashlib.sha256(
            f"{plan_hash}:{auth.authorization_hash}".encode()
        ).hexdigest()[:32]
        if not resume_consumed and not self._journal.reserve_authorization(
            plan_hash=plan_hash,
            authorization_hash=auth.authorization_hash,
            execution_id=execution_id,
            reserved_at=now.isoformat(),
        ):
            raise ExecutorGuardError(
                "invalid_authorization", "authorization rejected: unavailable_or_reserved"
            )

        # A local factory failure is nonbillable: release the reservation.  The
        # authorization is consumed only by the wrapper immediately before the
        # first call into the paid provider.
        try:
            inner = paid_provider_factory()
        except Exception as exc:
            if not resume_consumed:
                self._journal.release_reservation(
                    authorization_hash=auth.authorization_hash,
                    execution_id=execution_id,
                    message="paid provider construction failed",
                )
            raise ExecutorGuardError("provider_construction_failed", str(exc)) from exc

        def consume_before_first_call() -> None:
            if resume_consumed:
                return
            if not self._journal.consume_reserved_authorization(
                authorization_hash=auth.authorization_hash,
                execution_id=execution_id,
                consumed_at=datetime.now(UTC).isoformat(),
            ):
                raise ExecutorGuardError(
                    "authorization_consumption_failed",
                    "authorization reservation could not be consumed",
                )

        return _GuardedPaidHistoricalProvider(
            inner,
            authorized_request_hashes=authorized_hashes,
            maximum_single_request_usd=expected_maximum_single_request_usd,
            before_first_paid_call=consume_before_first_call,
        )


class PilotExecutionCoordinator:
    """Own the security-critical preflight, authorization, and request order."""

    def validate_only(
        self,
        *,
        requests: list[AcquisitionRequest],
        config: PilotExecutionConfig,
        plan_bindings: dict[str, object],
        plan_metadata: dict[str, Any] | None,
        metadata_provider_factory: Callable[[], MetadataProvider],
    ) -> ValidationOnlyResult:
        """Run sequential fresh metadata preflight without durable execution state."""
        validate_canonical_pilot_plan(requests)
        provider = metadata_provider_factory()
        try:
            retry = config.retry
            preflight = run_preflight(
                estimator=MetadataEstimator(
                    provider,
                    maximum_attempts=retry.maximum_attempts,
                    initial_delay_seconds=float(retry.initial_delay_seconds),
                    multiplier=float(retry.multiplier),
                    maximum_delay_seconds=float(retry.maximum_delay_seconds),
                    deterministic_jitter=retry.jitter == "deterministic_seeded",
                ),
                requests=requests,
                config=config,
                maximum_workers=1,
            )
        finally:
            closer = getattr(provider, "close", None)
            if callable(closer):
                closer()
        fresh = preflight.estimated_requests
        return ValidationOnlyResult(
            ready_for_paid_execution=preflight.passed,
            fresh_preflight_hash=compute_plan_hash(fresh, plan_bindings, plan_metadata),
            estimated_total_cost=preflight.fresh_total_usd,
            largest_request_cost=str(
                max((to_decimal(request.estimated_cost) for request in fresh), default=Decimal("0"))
            ),
        )

    def execute_paid(
        self,
        *,
        requests: list[AcquisitionRequest],
        config: PilotExecutionConfig,
        plan_hash: str,
        plan_bindings: dict[str, object],
        plan_metadata: dict[str, Any] | None,
        authorization_path: Path,
        authorization_hash: str,
        portal_attestation_hash: str,
        confirm_plan_hash: str,
        metadata_provider_factory: Callable[[], MetadataProvider],
        paid_provider_factory: Callable[[], PaidHistoricalProvider],
        journal_factory: Callable[[], RequestJournal],
        lifecycle: LifecycleHooks,
        now: datetime,
    ) -> PilotExecutionResult:
        """Execute or safely resume requests, stopping at the first unresolved state."""
        if not hmac.compare_digest(
            compute_plan_hash(requests, plan_bindings, plan_metadata), plan_hash
        ):
            raise ExecutorGuardError("plan_hash_mismatch")
        validation = self.validate_only(
            requests=requests,
            config=config,
            plan_bindings=plan_bindings,
            plan_metadata=plan_metadata,
            metadata_provider_factory=metadata_provider_factory,
        )
        if not validation.ready_for_paid_execution:
            raise ExecutorGuardError("preflight_not_passed")

        with journal_factory() as journal:
            executor = PilotExecutor(journal=journal)
            if not journal.all():
                executor.prepare(requests)
                for request in requests:
                    executor.transition(request.request_id, "preflight_validated")

            actions: list[tuple[AcquisitionRequest, RecoveryAction]] = []
            for request in requests:
                entry = journal.get(request.request_id)
                raw, normalized, quality, partial = lifecycle.inspect(request, entry)
                action = select_recovery_action(
                    entry,
                    raw_valid=raw,
                    normalized_valid=normalized,
                    quality_valid=quality,
                    partial_present=partial,
                )
                actions.append((request, action))
                if action in {"block_uncertain_billing", "quarantine", "manual_recovery_required"}:
                    return self._report(
                        requests=requests,
                        plan_hash=plan_hash,
                        authorization_hash=authorization_hash,
                        portal_attestation_hash=portal_attestation_hash,
                        validation=validation,
                        journal=journal,
                        skipped=sum(previous == "skip" for _, previous in actions),
                        paid_calls=0,
                        downloaded_records=0,
                        blocking_request=request.request_id,
                        blocking_state=action,
                        paid_provider_constructed=False,
                    )

            needs_provider = any(action == "execute_provider" for _, action in actions)
            provider: PaidHistoricalProvider | None = None
            if needs_provider:
                provider = executor.guard_execute(
                    plan_hash=plan_hash,
                    authorization_path=authorization_path,
                    confirm_plan_hash=confirm_plan_hash,
                    source_manifest_hash=str(plan_bindings["source_manifest_hash"]),
                    split_manifest_hash=str(plan_bindings["split_manifest_hash"]),
                    acquisition_policy_hash=str(plan_bindings["acquisition_policy_hash"]),
                    now=now,
                    paid_provider_factory=paid_provider_factory,
                    authorized_requests=requests,
                    plan_bindings=plan_bindings,
                    plan_metadata=plan_metadata,
                    preflight_passed=True,
                    expected_maximum_spend_usd=config.maximum_spend_usd,
                    expected_maximum_single_request_usd=config.maximum_single_request_usd,
                    resume_consumed=plan_hash in journal.consumed_authorization_ids(),
                )

            paid_calls = downloaded_records = skipped = 0
            blocking_request = blocking_state = None
            for request, action in actions:
                entry = journal.get(request.request_id)
                assert entry is not None
                if action == "skip":
                    skipped += 1
                    continue
                try:
                    if action == "execute_provider":
                        assert provider is not None
                        executor.transition(
                            request.request_id,
                            "request_started",
                            attempt_count=entry.attempt_count + 1,
                            request_started_at=datetime.now(UTC).isoformat(),
                        )
                        paid_calls += 1
                        raw_result = provider.acquire_range(request)
                        downloaded_records += raw_result.record_count
                        executor.transition(request.request_id, "response_received")
                        executor.transition(request.request_id, "raw_persisting")
                        executor.transition(
                            request.request_id,
                            "raw_validated",
                            raw_path=raw_result.raw_path,
                            raw_checksum=raw_result.sha256,
                            raw_record_count=raw_result.record_count,
                            raw_byte_count=Path(raw_result.raw_path).stat().st_size,
                            request_completed_at=datetime.now(UTC).isoformat(),
                        )
                    else:
                        assert (
                            entry.raw_path
                            and entry.raw_checksum
                            and entry.raw_record_count is not None
                        )
                        raw_result = RawAcquisitionResult(
                            request_id=request.request_id,
                            raw_path=entry.raw_path,
                            sha256=entry.raw_checksum,
                            record_count=entry.raw_record_count,
                        )
                    if action in {"execute_provider", "resume_normalization"}:
                        path, checksum, _ = lifecycle.normalize(request, raw_result)
                        executor.transition(
                            request.request_id,
                            "normalized",
                            normalized_path=path,
                            normalized_checksum=checksum,
                        )
                    normalized_path = journal.get(request.request_id).normalized_path  # type: ignore[union-attr]
                    assert normalized_path
                    if not lifecycle.quality(request, normalized_path):
                        blocking_request, blocking_state = request.request_id, "quality_rejected"
                        break
                    executor.transition(request.request_id, "quality_validated")
                except Exception as exc:
                    current = journal.get(request.request_id)
                    if current is not None and current.state == "request_started":
                        executor.transition(
                            request.request_id,
                            "uncertain_billing",
                            failure_category=getattr(exc, "category", "paid_invocation_failed"),
                            failure_message=str(exc),
                        )
                        blocking_state = "block_uncertain_billing"
                    else:
                        blocking_state = "local_processing_failure"
                    blocking_request = request.request_id
                    break

            return self._report(
                requests=requests,
                plan_hash=plan_hash,
                authorization_hash=authorization_hash,
                portal_attestation_hash=portal_attestation_hash,
                validation=validation,
                journal=journal,
                skipped=skipped,
                paid_calls=paid_calls,
                downloaded_records=downloaded_records,
                blocking_request=blocking_request,
                blocking_state=blocking_state,
                paid_provider_constructed=provider is not None,
            )

    @staticmethod
    def _report(
        *,
        requests: list[AcquisitionRequest],
        plan_hash: str,
        authorization_hash: str,
        portal_attestation_hash: str,
        validation: ValidationOnlyResult,
        journal: RequestJournal,
        skipped: int,
        paid_calls: int,
        downloaded_records: int,
        blocking_request: str | None,
        blocking_state: str | None,
        paid_provider_constructed: bool,
    ) -> PilotExecutionResult:
        entries = journal.all()
        complete = [entry for entry in entries if entry.state == "quality_validated"]
        uncertain = [entry for entry in entries if entry.state == "uncertain_billing"]
        raw_bytes = sum(entry.raw_byte_count or 0 for entry in entries)
        normalized_bytes = sum(
            Path(entry.normalized_path).stat().st_size
            for entry in entries
            if entry.normalized_path and Path(entry.normalized_path).exists()
        )
        execution_id = hashlib.sha256(f"{plan_hash}:{authorization_hash}".encode()).hexdigest()[:32]
        safe_resume_possible = blocking_state in {None, "local_processing_failure"}
        manual_action_required = blocking_state not in {None, "local_processing_failure"}
        if blocking_state is None:
            attempt_status = "completed"
        elif blocking_state == "block_uncertain_billing":
            attempt_status = "blocked_uncertain_billing"
        elif blocking_state == "local_processing_failure":
            attempt_status = "failed_local_processing"
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
            downloaded_records=downloaded_records,
            manual_action_required=manual_action_required,
        )
        return PilotExecutionResult(
            execution_id=execution_id,
            plan_hash=plan_hash,
            authorization_hash=authorization_hash,
            portal_attestation_hash=portal_attestation_hash,
            fresh_preflight_hash=validation.fresh_preflight_hash,
            requests_planned=len(requests),
            requests_completed=len(complete),
            requests_skipped=skipped,
            requests_failed=int(blocking_request is not None and not uncertain),
            requests_uncertain=len(uncertain),
            last_completed_request=complete[-1].request_id if complete else None,
            blocking_request=blocking_request,
            blocking_state=blocking_state,
            safe_resume_possible=safe_resume_possible,
            manual_action_required=manual_action_required,
            estimated_total_cost=validation.estimated_total_cost,
            raw_bytes=raw_bytes,
            normalized_bytes=normalized_bytes,
            quality_summary={
                "passed": len(complete),
                "failed": int(blocking_state == "quality_rejected"),
            },
            paid_provider_constructed=paid_provider_constructed,
            paid_request_calls=paid_calls,
            download_attempts=paid_calls,
            downloaded_records=downloaded_records,
        )
