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
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.authorization import (
    AuthorizationError,
    load_authorization,
    validate_authorization,
)
from neuralmarket.data.acquisition.estimation import MetadataEstimator
from neuralmarket.data.acquisition.journal import JournalEntry, RequestJournal
from neuralmarket.data.acquisition.requests import AcquisitionRequest
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
        # ponytail: in-memory single-use tracking only; cross-process persistence
        # of consumed authorizations is deferred to the recovery/CLI layer
        # (Tasks 9-10), which owns the durable consumed-id store.
        self._consumed_ids: set[str] = set()

    def prepare(self, requests: list[AcquisitionRequest]) -> None:
        """Write every request to the journal in the ``planned`` state."""
        now = datetime.now(UTC).isoformat()
        for request in requests:
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
                now=now,
                consumed_ids=self._consumed_ids,
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

        # --- Both guards passed: only now may a paid provider exist ------
        return paid_provider_factory()
