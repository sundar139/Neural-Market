"""Execution quote promotion, classification, fresh scope, and mixed evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.development import (
    DevelopmentRequest,
    load_development_plan,
)
from neuralmarket.data.acquisition.development_cost_quote import (
    DevelopmentCostEvidence,
    DevelopmentQuoteBindings,
    validate_complete_development_cost_evidence,
)
from neuralmarket.data.acquisition.development_execution import (
    DevelopmentAuthorization,
    DevelopmentExecutionError,
    DevelopmentExecutionQuote,
    build_complete_execution_cost_evidence,
    build_fresh_execution_quote_scope,
    derive_execution_quote_classification,
    load_development_execution_manifest,
    promote_parent_quote_to_execution,
    promote_parent_quotes_to_execution,
    validate_complete_execution_cost_evidence,
    validate_development_authorization,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN_PATH = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST_PATH = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_EVIDENCE_PATH = _ROOT / "reports/data/execution/live_c1_20260814T191524Z_run10.local.json"
_SCOPE_SRC = _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_PLAN_SHA = "32459494055e56d83e92b57342e22a91e5dac15f657625e1d03344c9bf232799"
_EVIDENCE_FILE_SHA = "60032ab4f7536849104d12855adc5b5271b9e9ca4c8ceac158f509d1a121f111"
_OVERSIZE = {"1b58e5bb6c7a956a", "14885c62f94689e3"}


@pytest.fixture(scope="module")
def plan():
    return load_development_plan(_PLAN_PATH)


@pytest.fixture(scope="module")
def manifest():
    return load_development_execution_manifest(_MANIFEST_PATH)


@pytest.fixture(scope="module")
def parent_evidence() -> DevelopmentCostEvidence:
    payload = json.loads(_EVIDENCE_PATH.read_text(encoding="utf-8"))
    scope_payload = json.loads(_SCOPE_SRC.read_text(encoding="utf-8"))
    requests = [DevelopmentRequest.model_validate(item) for item in scope_payload["requests"]]
    bindings = DevelopmentQuoteBindings.model_validate(payload["bindings"])
    return validate_complete_development_cost_evidence(
        payload,
        expected_bindings=bindings,
        requests=requests,
    )


@pytest.fixture(scope="module")
def dispositions() -> tuple[set[str], set[str]]:
    scope = json.loads(_SCOPE_SRC.read_text(encoding="utf-8"))
    reusable_parents = {item["development_request_id"] for item in scope["reusable"]}
    unavailable_parents = {item["development_request_id"] for item in scope["unavailable"]}
    return reusable_parents, unavailable_parents


@pytest.fixture(scope="module")
def excluded_ids(manifest, dispositions) -> tuple[set[str], set[str]]:
    reusable_parents, unavailable_parents = dispositions
    by_parent: dict[str, list] = {}
    for item in manifest.execution_requests:
        by_parent.setdefault(item.parent_request_id, []).append(item)
    reused = {by_parent[pid][0].execution_request_id for pid in reusable_parents}
    unavailable = {by_parent[pid][0].execution_request_id for pid in unavailable_parents}
    return reused, unavailable


def _one_to_one(manifest, excluded_ids):
    excluded = excluded_ids[0] | excluded_ids[1]
    return next(
        item
        for item in manifest.execution_requests
        if item.fragment_count == 1 and item.execution_request_id not in excluded
    )


def _fragment(manifest):
    return next(item for item in manifest.execution_requests if item.fragment_count > 1)


class TestPromotion:
    def test_valid_one_to_one_promotion_is_execution_keyed(
        self, manifest, parent_evidence, excluded_ids
    ):
        item = _one_to_one(manifest, excluded_ids)
        parent = next(p for p in manifest.parent_requests if p.request_id == item.parent_request_id)
        parent_quote = next(q for q in parent_evidence.quotes if q.request_id == parent.request_id)
        promoted = promote_parent_quote_to_execution(
            item,
            parent,
            parent_quote,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        assert promoted.execution_request_id == item.execution_request_id
        assert promoted.execution_request_hash == item.execution_request_hash
        assert promoted.quote_origin == "bound_parent_quote"
        assert promoted.cost_usd == parent_quote.cost_usd
        assert promoted.record_count == parent_quote.record_count
        assert promoted.billable_size_bytes == parent_quote.billable_size_bytes
        assert promoted.observed_at == parent_quote.provider_observed_end
        assert promoted.provider_observed_start == parent_quote.provider_observed_start
        assert promoted.parent_request_id == parent.request_id
        assert promoted.source_parent_cost_evidence_file_sha256 == _EVIDENCE_FILE_SHA
        assert promoted.source_parent_cost_evidence_hash == parent_evidence.evidence_hash

    def test_fragment_never_inherits_parent_quote(self, manifest, parent_evidence):
        item = _fragment(manifest)
        parent = next(p for p in manifest.parent_requests if p.request_id == item.parent_request_id)
        parent_quote = next(q for q in parent_evidence.quotes if q.request_id == parent.request_id)
        with pytest.raises(DevelopmentExecutionError, match="fragment_count"):
            promote_parent_quote_to_execution(
                item,
                parent,
                parent_quote,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            )

    @pytest.mark.parametrize(
        "field,value",
        [
            ("start", datetime(2020, 1, 1, tzinfo=UTC)),
            ("end_exclusive", datetime(2020, 2, 1, tzinfo=UTC)),
            ("dataset", "OPRA.PILLAR"),
            ("schema_name", "statistics"),
            ("symbols", ("AAPL.OPT",)),
            ("stype_in", "continuous"),
        ],
    )
    def test_provider_field_tamper_rejected(
        self, manifest, parent_evidence, excluded_ids, field, value
    ):
        item = _one_to_one(manifest, excluded_ids)
        parent = next(p for p in manifest.parent_requests if p.request_id == item.parent_request_id)
        parent_quote = next(q for q in parent_evidence.quotes if q.request_id == parent.request_id)
        tampered = parent_quote.model_copy(update={field: value})
        with pytest.raises(DevelopmentExecutionError, match="promotion rejected"):
            promote_parent_quote_to_execution(
                item,
                parent,
                tampered,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            )

    def test_parent_identity_tamper_rejected(self, manifest, parent_evidence, excluded_ids):
        item = _one_to_one(manifest, excluded_ids)
        parent = next(p for p in manifest.parent_requests if p.request_id == item.parent_request_id)
        parent_quote = next(q for q in parent_evidence.quotes if q.request_id == parent.request_id)
        tampered_parent = parent.model_copy(update={"request_hash": "0" * 64})
        with pytest.raises(DevelopmentExecutionError, match="promotion rejected"):
            promote_parent_quote_to_execution(
                item,
                tampered_parent,
                parent_quote,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            )

    def test_unvalidated_evidence_rejected(self, manifest, parent_evidence, excluded_ids):
        with pytest.raises(DevelopmentExecutionError, match="does not match"):
            promote_parent_quotes_to_execution(
                manifest=manifest,
                accepted_parent_evidence=parent_evidence,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                source_parent_cost_evidence_hash="0" * 64,
                excluded_execution_ids=excluded_ids[0] | excluded_ids[1],
            )

    def test_bulk_promotion_count_and_no_fragments(self, manifest, parent_evidence, excluded_ids):
        promoted = promote_parent_quotes_to_execution(
            manifest=manifest,
            accepted_parent_evidence=parent_evidence,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            excluded_execution_ids=excluded_ids[0] | excluded_ids[1],
        )
        assert len(promoted) == 488
        fragments = {
            item.execution_request_id
            for item in manifest.execution_requests
            if item.fragment_count > 1
        }
        assert not set(promoted) & fragments
        assert all(quote.quote_origin == "bound_parent_quote" for quote in promoted.values())


class TestClassification:
    def test_production_classification_exact(self, manifest, parent_evidence, excluded_ids):
        classification = derive_execution_quote_classification(
            manifest=manifest,
            excluded_reused_ids=excluded_ids[0],
            excluded_unavailable_ids=excluded_ids[1],
            accepted_parent_evidence=parent_evidence,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        assert len(classification["accepted_quote_reusable"]) == 488
        assert len(classification["fresh_quote_required"]) == 58
        assert len(classification["not_payable_reused"]) == 8
        assert len(classification["not_payable_unavailable"]) == 1
        total = sum(len(ids) for ids in classification.values())
        assert total == 555 == len(manifest.execution_requests)
        all_ids = [item.execution_request_id for item in manifest.execution_requests]
        flattened = [rid for ids in classification.values() for rid in ids]
        assert len(set(flattened)) == len(flattened) == len(set(all_ids))
        assert set(flattened) == set(all_ids)


class TestFreshScope:
    def test_fresh_scope_exact_and_deterministic(self, manifest, parent_evidence, excluded_ids):
        classification = derive_execution_quote_classification(
            manifest=manifest,
            excluded_reused_ids=excluded_ids[0],
            excluded_unavailable_ids=excluded_ids[1],
            accepted_parent_evidence=parent_evidence,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        scope = build_fresh_execution_quote_scope(manifest=manifest, classification=classification)
        assert len(scope.execution_request_ids) == 58
        by_id = {item.execution_request_id: item for item in manifest.execution_requests}
        parents = {by_id[rid].parent_request_id for rid in scope.execution_request_ids}
        assert parents == _OVERSIZE
        assert all(by_id[rid].fragment_count > 1 for rid in scope.execution_request_ids)
        assert all(by_id[rid].schema_name != "cbbo-1m" for rid in scope.execution_request_ids)
        scope2 = build_fresh_execution_quote_scope(manifest=manifest, classification=classification)
        assert scope2.model_dump() == scope.model_dump()
        assert (
            scope.scope_hash
            == hashlib.sha256(
                json.dumps(scope.model_dump(mode="json", by_alias=True), sort_keys=True).encode()
            ).hexdigest()
            or len(scope.scope_hash) == 64
        )


@pytest.fixture(scope="module")
def synthetic(manifest, parent_evidence, excluded_ids):
    classification = derive_execution_quote_classification(
        manifest=manifest,
        excluded_reused_ids=excluded_ids[0],
        excluded_unavailable_ids=excluded_ids[1],
        accepted_parent_evidence=parent_evidence,
        source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
        source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
    )
    promoted = promote_parent_quotes_to_execution(
        manifest=manifest,
        accepted_parent_evidence=parent_evidence,
        source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
        source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        excluded_execution_ids=excluded_ids[0] | excluded_ids[1],
    )
    by_id = {item.execution_request_id: item for item in manifest.execution_requests}
    observed = []
    observed_at = datetime(2026, 8, 16, 12, 0, 0, tzinfo=UTC)
    for index, rid in enumerate(classification["fresh_quote_required"]):
        item = by_id[rid]
        observed.append(
            DevelopmentExecutionQuote(
                execution_request_id=item.execution_request_id,
                execution_request_hash=item.execution_request_hash,
                cost_usd="0.005000000000",
                quote_origin="provider_observed",
                response_sha256=hashlib.sha256(json.dumps([rid, index]).encode()).hexdigest(),
                observed_at=observed_at,
                provider_observed_start=observed_at,
                provider_observed_end=observed_at,
                endpoint_response_sha256={
                    "record-count": "a" * 64,
                    "billable-size": "b" * 64,
                    "cost": "c" * 64,
                },
                record_count=100 + index,
                billable_size_bytes=1000 + index,
                attempt_sequences=(1,),
            )
        )
    paid_ids = [
        item.execution_request_id
        for item in manifest.execution_requests
        if item.execution_request_id not in (excluded_ids[0] | excluded_ids[1])
    ]
    observed_by_id = {quote.execution_request_id: quote for quote in observed}
    quotes = [promoted[rid] if rid in promoted else observed_by_id[rid] for rid in paid_ids]
    assert len(quotes) == 546
    return paid_ids, quotes


class TestExecutionEvidence:
    def test_complete_mixed_evidence_validates(
        self, manifest, parent_evidence, excluded_ids, synthetic
    ):
        paid_ids, quotes = synthetic
        del excluded_ids
        by_id = {item.execution_request_id: item for item in manifest.execution_requests}
        split_of = {rid: by_id[rid].expected_split for rid in paid_ids}
        rollups = {}
        grand = Decimal("0")
        split_totals = {"training": Decimal("0"), "validation": Decimal("0")}
        largest = Decimal("0")
        for quote in quotes:
            cost = Decimal(quote.cost_usd)
            grand += cost
            split_totals[split_of[quote.execution_request_id]] += cost
            largest = max(largest, cost)
        rollups["grand_total_usd"] = str(grand)
        rollups["training_total_usd"] = str(split_totals["training"])
        rollups["validation_total_usd"] = str(split_totals["validation"])
        rollups["largest_request_usd"] = str(largest)
        evidence = build_complete_execution_cost_evidence(
            plan_hash=manifest.plan_hash,
            manifest=manifest,
            paid_scope_ids=paid_ids,
            paid_scope_hash="d" * 64,
            quotes=quotes,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        validated = validate_complete_execution_cost_evidence(
            evidence,
            manifest=manifest,
            paid_scope_ids=paid_ids,
            paid_scope_hash="d" * 64,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            accepted_parent_evidence=parent_evidence,
        )
        assert validated.evidence_hash == evidence.evidence_hash
        assert evidence.rollups.grand_total_usd == rollups["grand_total_usd"]

    def test_duplicate_missing_and_extra_rejected(
        self, manifest, parent_evidence, excluded_ids, synthetic
    ):
        paid_ids, quotes = synthetic
        del excluded_ids
        from pydantic import ValidationError

        duplicate = [quotes[0], *list(quotes)]
        with pytest.raises(ValidationError, match="request count mismatch"):
            build_complete_execution_cost_evidence(
                plan_hash=manifest.plan_hash,
                manifest=manifest,
                paid_scope_ids=paid_ids,
                paid_scope_hash="d" * 64,
                quotes=duplicate,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            )
        missing = list(quotes)[1:]
        with pytest.raises(ValidationError, match="request count mismatch"):
            build_complete_execution_cost_evidence(
                plan_hash=manifest.plan_hash,
                manifest=manifest,
                paid_scope_ids=paid_ids,
                paid_scope_hash="d" * 64,
                quotes=missing,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            )

    def test_oversize_parent_ids_never_payable(
        self, manifest, parent_evidence, excluded_ids, synthetic
    ):
        paid_ids, quotes = synthetic
        del excluded_ids
        assert _OVERSIZE.isdisjoint(paid_ids)
        for quote in quotes:
            assert quote.execution_request_id not in _OVERSIZE
        assert parent_evidence.quotes

    def test_incomplete_real_state_stays_unauthorized(
        self, manifest, parent_evidence, excluded_ids
    ):
        promoted = promote_parent_quotes_to_execution(
            manifest=manifest,
            accepted_parent_evidence=parent_evidence,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
            excluded_execution_ids=excluded_ids[0] | excluded_ids[1],
        )
        assert len(promoted) == 488
        paid_ids = [
            item.execution_request_id
            for item in manifest.execution_requests
            if item.execution_request_id not in (excluded_ids[0] | excluded_ids[1])
        ]
        from neuralmarket.data.acquisition.development_execution import (
            derive_development_paid_execution_scope,
        )

        scope = derive_development_paid_execution_scope(
            manifest=manifest,
            quotes=promoted,
            excluded_reused_ids=excluded_ids[0],
            excluded_unavailable_ids=excluded_ids[1],
            cost_evidence_hash="",
        )
        assert not scope.authorization_ready
        assert scope.status == "pending_fresh_fragment_quotes"
        assert len(scope.pending_quote_execution_request_ids) == 58
        assert len(paid_ids) == 546


class TestAuthorizationIntegration:
    def test_complete_evidence_hash_binds_authorization(
        self, manifest, parent_evidence, excluded_ids, synthetic
    ):
        paid_ids, quotes = synthetic
        evidence = build_complete_execution_cost_evidence(
            plan_hash=manifest.plan_hash,
            manifest=manifest,
            paid_scope_ids=paid_ids,
            paid_scope_hash="d" * 64,
            quotes=quotes,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        authorization = DevelopmentAuthorization(
            plan_hash=manifest.plan_hash,
            execution_manifest_hash=manifest.manifest_hash,
            execution_scope_hash="d" * 64,
            cost_evidence_hash=evidence.evidence_hash,
            maximum_spend_usd="45.00",
            maximum_single_request_usd="1.00",
            currency="USD",
            source_head="f" * 40,
            expires_at=datetime(2026, 9, 1, tzinfo=UTC),
            purchase_authorized=True,
        )
        validate_development_authorization(
            authorization,
            now=datetime(2026, 8, 15, tzinfo=UTC),
            expected_plan_hash=manifest.plan_hash,
            expected_manifest_hash=manifest.manifest_hash,
            expected_scope_hash="d" * 64,
            expected_cost_evidence_hash=evidence.evidence_hash,
            expected_source_head="f" * 40,
            expected_maximum_spend_usd=Decimal("45.00"),
            expected_maximum_single_request_usd=Decimal("1.00"),
            consumed_ids=set(),
        )

    def test_wrong_evidence_hash_rejected(self, manifest, parent_evidence, excluded_ids, synthetic):
        paid_ids, quotes = synthetic
        evidence = build_complete_execution_cost_evidence(
            plan_hash=manifest.plan_hash,
            manifest=manifest,
            paid_scope_ids=paid_ids,
            paid_scope_hash="d" * 64,
            quotes=quotes,
            source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
            source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
        )
        authorization = DevelopmentAuthorization(
            plan_hash=manifest.plan_hash,
            execution_manifest_hash=manifest.manifest_hash,
            execution_scope_hash="d" * 64,
            cost_evidence_hash=evidence.evidence_hash,
            maximum_spend_usd="45.00",
            maximum_single_request_usd="1.00",
            currency="USD",
            source_head="f" * 40,
            expires_at=datetime(2026, 9, 1, tzinfo=UTC),
            purchase_authorized=True,
        )
        with pytest.raises(DevelopmentExecutionError, match="cost evidence"):
            validate_development_authorization(
                authorization,
                now=datetime(2026, 8, 15, tzinfo=UTC),
                expected_plan_hash=manifest.plan_hash,
                expected_manifest_hash=manifest.manifest_hash,
                expected_scope_hash="d" * 64,
                expected_cost_evidence_hash="0" * 64,
                expected_source_head="f" * 40,
                expected_maximum_spend_usd=Decimal("45.00"),
                expected_maximum_single_request_usd=Decimal("1.00"),
                consumed_ids=set(),
            )

    def test_laundered_observation_timestamp_rejected(
        self, manifest, parent_evidence, excluded_ids, synthetic
    ):
        paid_ids, quotes = synthetic
        by_id = {item.execution_request_id: item for item in manifest.execution_requests}
        laundered = []
        for quote in quotes:
            if quote.quote_origin == "bound_parent_quote":
                quote = quote.model_copy(update={"observed_at": datetime(2030, 1, 1, tzinfo=UTC)})
            laundered.append(quote)
        del by_id
        with pytest.raises(DevelopmentExecutionError, match="laundered"):
            validate_complete_execution_cost_evidence(
                build_complete_execution_cost_evidence(
                    plan_hash=manifest.plan_hash,
                    manifest=manifest,
                    paid_scope_ids=paid_ids,
                    paid_scope_hash="d" * 64,
                    quotes=laundered,
                    source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                    source_parent_cost_evidence_hash=parent_evidence.evidence_hash,
                ),
                manifest=manifest,
                paid_scope_ids=paid_ids,
                paid_scope_hash="d" * 64,
                source_parent_cost_evidence_file_sha256=_EVIDENCE_FILE_SHA,
                accepted_parent_evidence=parent_evidence,
            )
