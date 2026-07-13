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

import hmac
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.authorization import (
    AuthorizationError,
    load_authorization,
    validate_authorization,
)
from neuralmarket.data.acquisition.budget import to_decimal
from neuralmarket.data.acquisition.estimation import MetadataEstimator
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
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

    def get_record_count(self, **kwargs: object) -> int:
        """Return the metadata-estimated record count for a query window."""
        ...

    def get_billable_size(self, **kwargs: object) -> int:
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
    ) -> None:
        self._inner = inner
        self._authorized_request_hashes = authorized_request_hashes
        self._maximum_single_request_usd = maximum_single_request_usd
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

    def __init__(self, *, journal: RequestJournal, metadata_estimator: MetadataEstimator) -> None:
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
                consumed_ids=self._journal.consumed_authorization_ids(),
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

        for request in authorized_requests:
            entry = self._journal.get(request.request_id)
            if entry is None or entry.state != "preflight_validated":
                raise ExecutorGuardError(
                    "preflight_not_passed",
                    f"request is not preflight validated: {request.request_id}",
                )

        execution_id = uuid4().hex
        if not self._journal.consume_authorization_and_create_execution(
            plan_hash=plan_hash,
            authorization_hash=auth.authorization_hash,
            consumed_at=now.isoformat(),
            execution_id=execution_id,
            maximum_authorized_spend_usd=str(expected_maximum_spend_usd),
            currency=auth.authorized_currency,
        ):
            raise ExecutorGuardError(
                "invalid_authorization", "authorization rejected: already_consumed"
            )

        # --- Both guards passed and consumption is durable: provider may exist.
        return _GuardedPaidHistoricalProvider(
            paid_provider_factory(),
            authorized_request_hashes=authorized_hashes,
            maximum_single_request_usd=expected_maximum_single_request_usd,
        )
