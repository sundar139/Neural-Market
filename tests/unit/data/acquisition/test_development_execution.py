"""Plan-bound execution-fragment layer: contract, coverage, quotes, scope, authorization."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from neuralmarket.data.acquisition.development import DevelopmentPlan, load_development_plan
from neuralmarket.data.acquisition.development_execution import (
    DevelopmentAuthorization,
    DevelopmentExecutionError,
    DevelopmentExecutionManifest,
    DevelopmentExecutionQuote,
    DevelopmentExecutionRequest,
    build_development_execution_manifest,
    build_development_execution_request,
    derive_development_paid_execution_scope,
    development_execution_quote_gate,
    load_development_execution_manifest,
    validate_development_authorization,
    write_development_execution_manifest,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN_PATH = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_SCOPE_PATH = (
    _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
)
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_SCOPE_HASH = "cf08cd6ced5dec00bbb142fb9daa41e1f1070f281fbce5f29ce58c6e95fdd035"
_OVERSIZE = ("1b58e5bb6c7a956a", "14885c62f94689e3")


def _plan() -> DevelopmentPlan:
    return load_development_plan(_PLAN_PATH)


def _manifest() -> DevelopmentExecutionManifest:
    return build_development_execution_manifest(
        plan=_plan(),
        plan_file_sha256=_PLAN_SHA,
        source_scope_hash=_SCOPE_HASH,
        oversize_parent_request_ids=set(_OVERSIZE),
    )


def _parent(request_id: str) -> DevelopmentExecutionRequest:
    plan = _plan()
    request = next(item for item in plan.requests if item.request_id == request_id)
    return (
        build_development_execution_manifest(
            plan=plan,
            plan_file_sha256=_PLAN_SHA,
            source_scope_hash=_SCOPE_HASH,
            oversize_parent_request_ids=set(_OVERSIZE),
        ).execution_requests_by_parent[request.request_id][0]
        if False
        else _manifest_children(request)[0]
    )


def _manifest_children(parent):
    manifest = _manifest()
    return [
        item for item in manifest.execution_requests if item.parent_request_id == parent.request_id
    ]


def _quote(request: DevelopmentExecutionRequest, cost: str) -> DevelopmentExecutionQuote:
    return DevelopmentExecutionQuote(
        execution_request_id=request.execution_request_id,
        execution_request_hash=request.execution_request_hash,
        cost_usd=cost,
        currency="USD",
        quote_source="provider_response",
        response_sha256="a" * 64,
        observed_at=datetime(2026, 8, 15, tzinfo=UTC),
    )


class TestFragmentContract:
    def test_deterministic_identity_and_parent_binding(self) -> None:
        first, second = _manifest(), _manifest()
        assert first.manifest_hash == second.manifest_hash
        assert first.execution_requests == second.execution_requests
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        children = _manifest_children(parent)
        assert len(children) == 44
        for index, child in enumerate(children, start=1):
            assert child.parent_request_id == parent.request_id
            assert child.parent_request_hash == parent.request_hash
            assert child.parent_specification_hash == parent.specification_hash
            assert child.fragment_index == index
            assert child.fragment_count == 44
            assert child.fresh_quote_required is True

    def test_wall_clock_independence(self) -> None:
        assert _manifest().manifest_hash == _manifest().manifest_hash

    def test_tampered_execution_hash_rejected(self) -> None:
        manifest = _manifest()
        child = manifest.execution_requests[0]
        payload = child.model_dump(mode="json", by_alias=True)
        payload["execution_request_hash"] = "0" * 64
        with pytest.raises(ValidationError):
            DevelopmentExecutionRequest.model_validate(payload)


class TestParentCoverage:
    def _fragments(self, request_id: str) -> list[DevelopmentExecutionRequest]:
        parent = next(item for item in _plan().requests if item.request_id == request_id)
        return _manifest_children(parent)

    def test_training_parent_exact_contiguous_coverage(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        fragments = self._fragments(parent.request_id)
        assert fragments[0].start == parent.start
        assert fragments[-1].end_exclusive == parent.end_exclusive
        for previous, current in itertools.pairwise(fragments):
            assert previous.end_exclusive == current.start
            assert current.start < current.end_exclusive
        assert all(
            parent.start <= item.start < item.end_exclusive <= parent.end_exclusive
            for item in fragments
        )

    def test_validation_parent_exact_contiguous_coverage(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[1])
        fragments = self._fragments(parent.request_id)
        assert fragments[0].start == parent.start
        assert fragments[-1].end_exclusive == parent.end_exclusive
        for previous, current in itertools.pairwise(fragments):
            assert previous.end_exclusive == current.start
        assert len(fragments) == 14

    def test_gap_overlap_duplicate_and_out_of_bounds_rejected(self) -> None:
        from datetime import timedelta

        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        children = self._fragments(parent.request_id)
        cases: list[tuple[dict[str, Any], int, str]] = [
            (
                build_development_execution_request(
                    parent=parent,
                    fragment_index=3,
                    fragment_count=len(children),
                    window=(
                        children[1].end_exclusive + timedelta(days=1),
                        children[2].end_exclusive,
                    ),
                ).model_dump(mode="json", by_alias=True),
                3,
                "contiguous",
            ),
            (
                build_development_execution_request(
                    parent=parent,
                    fragment_index=3,
                    fragment_count=len(children),
                    window=(children[1].start, children[2].end_exclusive),
                ).model_dump(mode="json", by_alias=True),
                3,
                "contiguous",
            ),
            (
                build_development_execution_request(
                    parent=parent,
                    fragment_index=1,
                    fragment_count=len(children),
                    window=(
                        parent.start - timedelta(days=1),
                        children[0].end_exclusive,
                    ),
                ).model_dump(mode="json", by_alias=True),
                1,
                "bounds",
            ),
            (children[0].model_dump(mode="json", by_alias=True), 2, "duplicate"),
        ]
        for payload, fragment_index, message in cases:
            manifest_payload = _manifest().model_dump(mode="json", by_alias=True)
            execution_requests = list(manifest_payload["execution_requests"])
            index = next(
                position
                for position, item in enumerate(execution_requests)
                if item["parent_request_id"] == parent.request_id
                and item["fragment_index"] == fragment_index
            )
            execution_requests[index] = payload
            manifest_payload["execution_requests"] = execution_requests
            with pytest.raises(ValidationError, match=message):
                DevelopmentExecutionManifest.model_validate(manifest_payload)

    def test_wrong_semantic_fields_rejected(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        for field, value in (
            ("dataset", "ARCX.PILLAR"),
            ("schema_name", "statistics"),
            ("expected_split", "validation"),
            ("purpose", "strategy_b_closing_quote"),
        ):
            tampered_parent = parent.model_copy(update={field: value})
            children = self._fragments(parent.request_id)
            child = build_development_execution_request(
                parent=tampered_parent,
                fragment_index=1,
                fragment_count=len(children),
                window=(children[0].start, children[0].end_exclusive),
            )
            manifest_payload = _manifest().model_dump(mode="json", by_alias=True)
            execution_requests = list(manifest_payload["execution_requests"])
            index = next(
                position
                for position, item in enumerate(execution_requests)
                if item["parent_request_id"] == parent.request_id
            )
            execution_requests[index] = child.model_dump(mode="json", by_alias=True)
            manifest_payload["execution_requests"] = execution_requests
            with pytest.raises(ValidationError, match="parent"):
                DevelopmentExecutionManifest.model_validate(manifest_payload)


class TestCurrentFragmentation:
    def test_only_two_oversize_definition_parents_fragmented(self) -> None:
        manifest = _manifest()
        by_parent: dict[str, list[DevelopmentExecutionRequest]] = {}
        for item in manifest.execution_requests:
            by_parent.setdefault(item.parent_request_id, []).append(item)
        assert set(manifest.fragmented_parent_request_ids) == set(_OVERSIZE)
        assert len(by_parent) == 499
        assert sum(1 for children in by_parent.values() if len(children) > 1) == 2
        assert manifest.execution_request_count == 555

    def test_no_cbbo_fragmentation(self) -> None:
        manifest = _manifest()
        cbbo_children = [
            item for item in manifest.execution_requests if item.schema_name == "cbbo-1m"
        ]
        assert len(cbbo_children) == 491
        assert all(item.fragment_count == 1 for item in cbbo_children)

    def test_unfragmented_requests_map_one_to_one(self) -> None:
        manifest = _manifest()
        plan = _plan()
        for request in plan.requests:
            if request.request_id in _OVERSIZE:
                continue
            children = [
                item
                for item in manifest.execution_requests
                if item.parent_request_id == request.request_id
            ]
            assert len(children) == 1
            child = children[0]
            assert child.fragment_index == 1 and child.fragment_count == 1
            assert child.start == request.start
            assert child.end_exclusive == request.end_exclusive
            assert child.dataset == request.dataset
            assert child.schema_name == request.schema_name
            assert child.expected_split == request.expected_split
            assert child.purpose == request.purpose

    def test_manifest_preserves_canonical_plan_hash(self) -> None:
        assert (
            _plan().plan_hash == "1902157e61360897eb8cdb5a07f16877b15c0f56301f8584bfa03d0e95be25b5"
        )
        manifest = _manifest()
        assert manifest.plan_hash == _plan().plan_hash


class TestFragmentQuoteGate:
    def test_no_fresh_quote_means_not_authorization_ready(self) -> None:
        scope = derive_development_paid_execution_scope(
            manifest=_manifest(),
            quotes={},
            excluded_reused_ids=set(),
            excluded_unavailable_ids=set(),
        )
        assert scope.status == "pending_fresh_fragment_quotes"
        assert scope.authorization_ready is False

    def test_parent_quote_cannot_authorize_child(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        child = _manifest_children(parent)[0]
        forged = _quote(child, "0.5").model_copy(
            update={"execution_request_hash": parent.request_hash}
        )
        with pytest.raises(DevelopmentExecutionError, match="hash"):
            development_execution_quote_gate(
                child, {child.execution_request_id: forged}, Decimal("1.00")
            )

    def test_exact_child_quote_accepted_and_over_cap_rejected(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        child = _manifest_children(parent)[0]
        accepted = _quote(child, "0.75")
        assert development_execution_quote_gate(
            child, {child.execution_request_id: accepted}, Decimal("1.00")
        ) == Decimal("0.75")
        with pytest.raises(DevelopmentExecutionError, match="cap"):
            development_execution_quote_gate(
                child, {child.execution_request_id: _quote(child, "1.01")}, Decimal("1.00")
            )

    def test_stale_and_missing_quotes_rejected(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        child = _manifest_children(parent)[0]
        with pytest.raises(DevelopmentExecutionError, match="quote"):
            development_execution_quote_gate(child, {}, Decimal("1.00"))
        other = _manifest_children(parent)[1]
        with pytest.raises(DevelopmentExecutionError, match="hash"):
            development_execution_quote_gate(
                child,
                {child.execution_request_id: _quote(other, "0.5")},
                Decimal("1.00"),
            )

    def test_decimal_only_and_nonfinite_rejected(self) -> None:
        parent = next(item for item in _plan().requests if item.request_id == _OVERSIZE[0])
        child = _manifest_children(parent)[0]
        for value in ("0.5",):
            DevelopmentExecutionQuote.model_validate(
                _quote(child, value).model_dump(mode="json", by_alias=True)
            )
        for value in ("NaN", "Infinity", "-0.1"):
            with pytest.raises(ValidationError):
                DevelopmentExecutionQuote.model_validate(
                    _quote(child, value).model_dump(mode="json", by_alias=True)
                )
        with pytest.raises((ValidationError, TypeError)):
            DevelopmentExecutionQuote.model_validate(
                {
                    **_quote(child, "0.5").model_dump(mode="json", by_alias=True),
                    "cost_usd": 0.5,
                }
            )


class TestCanonicalPlanPreservation:
    def test_plan_file_bytes_unchanged_and_manifest_regen_identical(self, tmp_path: Path) -> None:
        before = _PLAN_PATH.read_bytes()
        manifest = _manifest()
        write_development_execution_manifest(tmp_path / "execution_manifest.json", manifest)
        loaded = load_development_execution_manifest(tmp_path / "execution_manifest.json")
        assert loaded.manifest_hash == manifest.manifest_hash
        assert _PLAN_PATH.read_bytes() == before
        regenerated = _manifest()
        assert regenerated.manifest_hash == manifest.manifest_hash
        assert regenerated.model_dump(mode="json", by_alias=True) == manifest.model_dump(
            mode="json", by_alias=True
        )


class TestAuthorization:
    def _scope_and_auth(self):
        manifest = _manifest()
        quotes: dict[str, DevelopmentExecutionQuote] = {}
        for item in manifest.execution_requests:
            quotes[item.execution_request_id] = _quote(item, "0.25")
        scope = derive_development_paid_execution_scope(
            manifest=manifest,
            quotes=quotes,
            excluded_reused_ids=set(),
            excluded_unavailable_ids=set(),
        )
        assert scope.authorization_ready is True
        auth = DevelopmentAuthorization(
            plan_hash=manifest.plan_hash,
            execution_manifest_hash=manifest.manifest_hash,
            execution_scope_hash=scope.scope_hash,
            cost_evidence_hash="b" * 64,
            maximum_spend_usd="45.00",
            maximum_single_request_usd="1.00",
            currency="USD",
            source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
            expires_at=datetime(2026, 9, 1, tzinfo=UTC),
            purchase_authorized=True,
        )
        return manifest, scope, auth

    def test_bindings_expiry_and_purchase_flag(self) -> None:
        manifest, scope, auth = self._scope_and_auth()
        now = datetime(2026, 8, 15, tzinfo=UTC)
        validate_development_authorization(
            auth,
            now=now,
            expected_plan_hash=manifest.plan_hash,
            expected_manifest_hash=manifest.manifest_hash,
            expected_scope_hash=scope.scope_hash,
            expected_cost_evidence_hash="b" * 64,
            expected_source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
            expected_maximum_spend_usd=Decimal("45.00"),
            expected_maximum_single_request_usd=Decimal("1.00"),
            consumed_ids=set(),
        )
        with pytest.raises(DevelopmentExecutionError, match="hash"):
            validate_development_authorization(
                auth,
                now=now,
                expected_plan_hash="0" * 64,
                expected_manifest_hash=manifest.manifest_hash,
                expected_scope_hash=scope.scope_hash,
                expected_cost_evidence_hash="b" * 64,
                expected_source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
                expected_maximum_spend_usd=Decimal("45.00"),
                expected_maximum_single_request_usd=Decimal("1.00"),
                consumed_ids=set(),
            )
        with pytest.raises(DevelopmentExecutionError, match="expire"):
            validate_development_authorization(
                auth,
                now=datetime(2026, 10, 1, tzinfo=UTC),
                expected_plan_hash=manifest.plan_hash,
                expected_manifest_hash=manifest.manifest_hash,
                expected_scope_hash=scope.scope_hash,
                expected_cost_evidence_hash="b" * 64,
                expected_source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
                expected_maximum_spend_usd=Decimal("45.00"),
                expected_maximum_single_request_usd=Decimal("1.00"),
                consumed_ids=set(),
            )
        unauthorized = auth.model_copy(update={"purchase_authorized": False})
        with pytest.raises(DevelopmentExecutionError, match="purchase"):
            validate_development_authorization(
                unauthorized,
                now=now,
                expected_plan_hash=manifest.plan_hash,
                expected_manifest_hash=manifest.manifest_hash,
                expected_scope_hash=scope.scope_hash,
                expected_cost_evidence_hash="b" * 64,
                expected_source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
                expected_maximum_spend_usd=Decimal("45.00"),
                expected_maximum_single_request_usd=Decimal("1.00"),
                consumed_ids=set(),
            )
        with pytest.raises(DevelopmentExecutionError, match="consumed"):
            validate_development_authorization(
                auth,
                now=now,
                expected_plan_hash=manifest.plan_hash,
                expected_manifest_hash=manifest.manifest_hash,
                expected_scope_hash=scope.scope_hash,
                expected_cost_evidence_hash="b" * 64,
                expected_source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
                expected_maximum_spend_usd=Decimal("45.00"),
                expected_maximum_single_request_usd=Decimal("1.00"),
                consumed_ids={auth.authorization_hash},
            )

    def test_single_request_cap_never_exceeds_one_usd(self) -> None:
        with pytest.raises(ValidationError):
            DevelopmentAuthorization(
                plan_hash="a" * 64,
                execution_manifest_hash="b" * 64,
                execution_scope_hash="c" * 64,
                cost_evidence_hash="d" * 64,
                maximum_spend_usd="45.00",
                maximum_single_request_usd="1.01",
                currency="USD",
                source_head="f7031386d5f47996fc5e0ed65970bf5cb0462e57",
                expires_at=datetime(2026, 9, 1, tzinfo=UTC),
                purchase_authorized=True,
            )


class TestProductionShapedOfflineInitialization:
    def test_real_plan_scope_and_evidence(self) -> None:
        manifest = _manifest()
        plan = _plan()
        assert plan.logical_requirement_count == 499
        assert set(manifest.fragmented_parent_request_ids) == set(_OVERSIZE)
        assert manifest.execution_request_count == 555
        assert manifest.source_scope_hash == _SCOPE_HASH
        ids = [item.execution_request_id for item in manifest.execution_requests]
        assert "ebefaaae3b198092" not in ids
        assert "d5352ffb04e4bc83" not in ids
        assert all(item.fresh_quote_required for item in manifest.execution_requests)
        scope = derive_development_paid_execution_scope(
            manifest=manifest, quotes={}, excluded_reused_ids=set(), excluded_unavailable_ids=set()
        )
        assert scope.authorization_ready is False
        assert scope.status == "pending_fresh_fragment_quotes"
        training = next(item for item in plan.requests if item.request_id == _OVERSIZE[0])
        fragments = _manifest_children(training)
        assert [item.start for item in fragments[:2]] == [
            datetime(2018, 5, 1, tzinfo=UTC),
            datetime(2018, 6, 1, tzinfo=UTC),
        ]
        assert fragments[-1].end_exclusive == datetime(2022, 1, 1, tzinfo=UTC)
        validation = next(item for item in plan.requests if item.request_id == _OVERSIZE[1])
        validation_fragments = _manifest_children(validation)
        assert validation_fragments[0].start == datetime(2022, 5, 26, tzinfo=UTC)
        assert validation_fragments[-1].end_exclusive == datetime(2023, 7, 1, tzinfo=UTC)
        assert len(validation_fragments) == 14
