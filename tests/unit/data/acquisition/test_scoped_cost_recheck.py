"""Offline fail-closed tests for the scoped 24-request cost recheck.

Every rejection path must be proven to cost zero provider calls: the quoter and
schema lister used here record every invocation, so a leaked call fails the test.
No test constructs a real provider or touches the network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from neuralmarket.data.acquisition.authorization import (
    AuthorizationError,
    RemainingRequestScope,
    build_remaining_scope,
    validate_remaining_scope,
)
from neuralmarket.data.acquisition.live_cost_recheck import CostRecheckError, recheck_costs
from neuralmarket.data.acquisition.metadata_runner import IsolatedMetadataResult
from neuralmarket.data.acquisition.requests import AcquisitionRequest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_MANIFEST = _ROOT / "data/manifests/pilot_request_plan_v1.json"

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)
COMPLETED_ID = "2750995e515e4f1a"  # pragma: allowlist secret
_SUPPORTED = {
    "ARCX.PILLAR": ["definition", "ohlcv-1d", "statistics"],
    "OPRA.PILLAR": ["definition", "cbbo-1m"],
}


def _manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def _canonical() -> list[AcquisitionRequest]:
    return [AcquisitionRequest.model_validate(item) for item in _manifest()["requests"]]


def _plan_hash() -> str:
    return str(_manifest()["plan_hash"])


def _remaining(requests: list[AcquisitionRequest]) -> list[AcquisitionRequest]:
    return [request for request in requests if request.request_id != COMPLETED_ID]


def _scope(
    *,
    completed: list[AcquisitionRequest] | None = None,
    remaining: list[AcquisitionRequest] | None = None,
    source_plan_hash: str | None = None,
) -> RemainingRequestScope:
    requests = _canonical()
    completed = (
        completed
        if completed is not None
        else [r for r in requests if r.request_id == COMPLETED_ID]
    )
    remaining = remaining if remaining is not None else _remaining(requests)
    return build_remaining_scope(
        source_plan_hash=source_plan_hash if source_plan_hash is not None else _plan_hash(),
        completed_request_ids=[r.request_id for r in completed],
        completed_request_hashes=[r.request_hash for r in completed],
        remaining_request_ids=[r.request_id for r in remaining],
        remaining_request_hashes=[r.request_hash for r in remaining],
    )


class _Recorder:
    """Provider stand-in that records every call it receives."""

    def __init__(self) -> None:
        self.quoted: list[str] = []
        self.listed: list[str] = []

    def quoter(self, request: AcquisitionRequest, attempt: int, timeout: float) -> Any:
        self.quoted.append(request.request_id)
        return IsolatedMetadataResult(
            endpoint_values={"cost": "0.01"},
            events=[],
            child_pid=1,
            child_exitcode=0,
            child_joined=True,
            remaining_children=0,
        )

    def lister(self, dataset: str) -> list[str]:
        self.listed.append(dataset)
        return list(_SUPPORTED.get(dataset, []))

    @property
    def provider_calls(self) -> int:
        return len(self.quoted) + len(self.listed)


def _run(
    recorder: _Recorder,
    *,
    requests: list[AcquisitionRequest],
    scope: RemainingRequestScope | None,
    plan_hash: str | None = None,
) -> Any:
    prior = sum((Decimal(r.estimated_cost or "0") for r in requests), Decimal(0))
    return recheck_costs(
        requests=requests,
        repository_head="0" * 40,
        checkpoint_sha256="e" * 64,
        plan_hash=plan_hash if plan_hash is not None else _plan_hash(),
        request_manifest_sha256="8" * 64,
        sdk_version="0.81.0",
        now=NOW,
        schema_lister=recorder.lister,
        quoter=recorder.quoter,
        timeout_seconds=30.0,
        prior_raw_total_usd=prior,
        prior_conservative_total_usd=prior,
        tracked_total_usd=prior,
        remaining_scope=scope,
    )


# ── Scope validation (provider-free) ─────────────────────────────────


def test_validated_remaining_scope_is_accepted() -> None:
    validate_remaining_scope(
        _scope(), canonical_requests=_canonical(), source_plan_hash=_plan_hash()
    )


def test_scope_hash_mismatch_is_rejected() -> None:
    tampered = _scope().model_copy(update={"scope_hash": "0" * 64})
    with pytest.raises(AuthorizationError) as exc:
        validate_remaining_scope(
            tampered, canonical_requests=_canonical(), source_plan_hash=_plan_hash()
        )
    assert exc.value.reason == "scope_hash_mismatch"


def test_source_plan_hash_mismatch_is_rejected() -> None:
    with pytest.raises(AuthorizationError) as exc:
        validate_remaining_scope(
            _scope(source_plan_hash="a" * 64),
            canonical_requests=_canonical(),
            source_plan_hash=_plan_hash(),
        )
    assert exc.value.reason == "scope_plan_hash_mismatch"


def test_a_23_request_remaining_scope_is_rejected() -> None:
    """Two completed + 23 remaining still totals 25, so the model admits it."""
    requests = _canonical()
    with pytest.raises(AuthorizationError) as exc:
        validate_remaining_scope(
            _scope(completed=requests[:2], remaining=requests[2:]),
            canonical_requests=requests,
            source_plan_hash=_plan_hash(),
        )
    assert exc.value.reason == "scope_request_count"
    assert len(requests[2:]) == 23


def test_a_25_request_remaining_scope_is_rejected_by_the_model() -> None:
    """A scope that excludes nothing cannot total 25, so it never reaches validation."""
    requests = _canonical()
    completed = next(r for r in requests if r.request_id == COMPLETED_ID)
    with pytest.raises(ValidationError, match="exactly 25 total requests"):
        _scope(completed=[completed], remaining=requests)


def test_duplicate_request_id_is_rejected_by_the_model() -> None:
    requests = _canonical()
    remaining = _remaining(requests)
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        _scope(remaining=[*remaining[:-1], remaining[0]])


def test_duplicate_request_hash_is_rejected() -> None:
    requests = _canonical()
    remaining = _remaining(requests)
    scope = _scope().model_copy(
        update={
            "remaining_request_hashes": [
                *[r.request_hash for r in remaining[:-1]],
                remaining[0].request_hash,
            ]
        }
    )
    with pytest.raises(AuthorizationError) as exc:
        validate_remaining_scope(scope, canonical_requests=requests, source_plan_hash=_plan_hash())
    assert exc.value.reason in {"scope_hash_mismatch", "scope_duplicate_hash"}


def test_completed_request_inside_remaining_scope_is_rejected() -> None:
    """Swap one remaining request for the completed one: 25 total, but they overlap."""
    requests = _canonical()
    completed = next(r for r in requests if r.request_id == COMPLETED_ID)
    remaining = _remaining(requests)
    with pytest.raises(ValidationError, match="must not overlap"):
        _scope(completed=[completed], remaining=[completed, *remaining[1:]])


def test_completed_request_hash_inside_remaining_scope_is_rejected() -> None:
    requests = _canonical()
    completed = next(r for r in requests if r.request_id == COMPLETED_ID)
    remaining = _remaining(requests)
    scope = _scope().model_copy(
        update={
            "remaining_request_hashes": [
                completed.request_hash,
                *[r.request_hash for r in remaining[1:]],
            ]
        }
    )
    with pytest.raises(AuthorizationError) as exc:
        validate_remaining_scope(scope, canonical_requests=requests, source_plan_hash=_plan_hash())
    assert exc.value.reason in {"scope_hash_mismatch", "scope_completed_included"}


def test_request_outside_the_canonical_plan_is_rejected() -> None:
    requests = _canonical()
    remaining = _remaining(requests)
    scope = build_remaining_scope(
        source_plan_hash=_plan_hash(),
        completed_request_ids=[COMPLETED_ID],
        completed_request_hashes=[
            next(r.request_hash for r in requests if r.request_id == COMPLETED_ID)
        ],
        remaining_request_ids=["deadbeefdeadbeef", *[r.request_id for r in remaining[1:]]],
        remaining_request_hashes=["f" * 64, *[r.request_hash for r in remaining[1:]]],
    )
    with pytest.raises(AuthorizationError) as exc:
        validate_remaining_scope(scope, canonical_requests=requests, source_plan_hash=_plan_hash())
    assert exc.value.reason == "scope_unknown_request"


# ── Scoped recheck (provider inventory) ──────────────────────────────


def test_scoped_recheck_quotes_exactly_the_24_remaining_requests() -> None:
    requests = _canonical()
    remaining = _remaining(requests)
    recorder = _Recorder()
    result = _run(recorder, requests=remaining, scope=_scope())

    assert len(recorder.quoted) == 24
    assert recorder.quoted == [r.request_id for r in remaining]
    assert COMPLETED_ID not in recorder.quoted
    assert result.provider_call_inventory["get_cost"] == 24
    assert len(result.quotes) == 24
    assert result.status == "complete"


def test_scoped_recheck_rejects_an_inventory_that_differs_from_the_scope() -> None:
    requests = _canonical()
    recorder = _Recorder()
    # Hand the runtime the full 25 while claiming the validated 24-request scope.
    with pytest.raises(CostRecheckError, match="does not equal the remaining scope"):
        _run(recorder, requests=requests, scope=_scope())
    assert recorder.provider_calls == 0


def test_scoped_recheck_rejects_a_reordered_inventory() -> None:
    remaining = _remaining(_canonical())
    recorder = _Recorder()
    reordered = [remaining[1], remaining[0], *remaining[2:]]
    with pytest.raises(CostRecheckError, match="does not equal the remaining scope"):
        _run(recorder, requests=reordered, scope=_scope())
    assert recorder.provider_calls == 0


def test_scoped_recheck_rejects_a_scope_bound_to_another_plan() -> None:
    remaining = _remaining(_canonical())
    recorder = _Recorder()
    with pytest.raises(CostRecheckError, match="bound to a different plan"):
        _run(recorder, requests=remaining, scope=_scope(), plan_hash="c" * 64)
    assert recorder.provider_calls == 0


def test_scoped_recheck_rejects_the_completed_request() -> None:
    requests = _canonical()
    completed = next(r for r in requests if r.request_id == COMPLETED_ID)
    remaining = _remaining(requests)
    swapped = [completed, *remaining[1:]]
    scope = _scope().model_copy(update={"remaining_request_ids": [r.request_id for r in swapped]})
    recorder = _Recorder()
    with pytest.raises(CostRecheckError):
        _run(recorder, requests=swapped, scope=scope)
    assert recorder.provider_calls == 0


def test_canonical_25_request_recheck_is_unaffected() -> None:
    requests = _canonical()
    recorder = _Recorder()
    result = _run(recorder, requests=requests, scope=None)
    assert len(recorder.quoted) == 25
    assert result.provider_call_inventory["get_cost"] == 25


def test_a_23_request_inventory_is_still_rejected_without_a_scope() -> None:
    recorder = _Recorder()
    with pytest.raises(ValueError, match="request_count"):
        _run(recorder, requests=_canonical()[:23], scope=None)
    assert recorder.provider_calls == 0
