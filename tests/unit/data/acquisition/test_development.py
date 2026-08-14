from __future__ import annotations

import hashlib
import importlib
import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from neuralmarket.data.acquisition.requests import (
    AcquisitionRequest,
    plan_hash,
    plan_hash_metadata,
    validate_canonical_pilot_plan,
    verify_final_request,
)
from neuralmarket.data.errors import PlanValidationError
from neuralmarket.data.manifests import canonical_dumps

pytestmark = pytest.mark.unit

_ROOT = Path(".")
_ACQUISITION_CONFIG = _ROOT / "configs/data/acquisition/spy_daily_budgeted.yaml"
_DATA_CONFIG = _ROOT / "configs/data/spy_daily_databento.yaml"
_SOURCE = _ROOT / "data/manifests/source_manifest_v1.json"
_SPLIT = _ROOT / "data/manifests/split_manifest_v1.json"
_POLICY = _ROOT / "data/manifests/acquisition_policy_v1.json"
_PILOT_PLAN = _ROOT / "data/manifests/pilot_request_plan_v1.json"
_DEVELOPMENT_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_TS_RECV_POLICY = (
    "Future close/snapshot construction must use raw DBN ts_recv as authoritative "
    "observation time. Normalized ts_event is not a receive-time fallback."
)


def _development() -> Any:
    return importlib.import_module("neuralmarket.data.acquisition.development")


def _build() -> Any:
    return _development().build_development_plan_from_files(
        acquisition_config_path=_ACQUISITION_CONFIG,
        data_config_path=_DATA_CONFIG,
        source_manifest_path=_SOURCE,
        split_manifest_path=_SPLIT,
        policy_manifest_path=_POLICY,
    )


@pytest.fixture(scope="module")
def plan() -> Any:
    return _build()


def _quotes(plan: Any) -> list[Any]:
    return [request for request in plan.requests if request.schema_name == "cbbo-1m"]


def _catalog(plan: Any) -> list[Any]:
    return [request for request in plan.requests if request.schema_name != "cbbo-1m"]


def test_strategy_b_plan_has_exact_authoritative_schedule(plan: Any) -> None:
    quotes = _quotes(plan)
    assert plan.strategy_id == "B"
    assert plan.logical_requirement_count == 499
    assert plan.catalog_request_count == 8
    assert plan.cbbo_request_count == 491
    assert len(quotes) == 491
    assert sum(request.expected_split == "training" for request in quotes) == 377
    assert sum(request.expected_split == "validation" for request in quotes) == 114
    assert len({request.session_date for request in quotes}) == 491
    assert all(
        request.session_date and request.session_date.weekday() in (1, 3) for request in quotes
    )
    assert plan.duplicate_request_count == 0
    assert plan.sealed_test_overlap_count == 0
    assert plan.excluded_boundary_overlap_count == 0


def test_strategy_b_omits_holiday_and_uses_actual_close(plan: Any) -> None:
    by_date = {request.session_date: request for request in _quotes(plan)}
    assert date(2019, 1, 1) not in by_date  # Tuesday holiday, not shifted
    assert date(2019, 1, 2) not in by_date  # adjacent Wednesday is not substituted

    winter = by_date[date(2019, 1, 8)]
    summer = by_date[date(2019, 7, 2)]
    early = by_date[date(2018, 7, 3)]
    assert winter.end_exclusive == datetime(2019, 1, 8, 21, tzinfo=UTC)
    assert summer.end_exclusive == datetime(2019, 7, 2, 20, tzinfo=UTC)
    assert early.end_exclusive == datetime(2018, 7, 3, 17, tzinfo=UTC)
    assert all(
        request.end_exclusive - request.start == timedelta(minutes=10) for request in _quotes(plan)
    )


def test_catalog_has_exact_split_specific_products_and_ranges(plan: Any) -> None:
    catalog = _catalog(plan)
    assert len(catalog) == 8
    expected_products = {
        ("ARCX.PILLAR", "definition", ("SPY",), "raw_symbol"),
        ("ARCX.PILLAR", "ohlcv-1d", ("SPY",), "raw_symbol"),
        ("ARCX.PILLAR", "statistics", ("SPY",), "raw_symbol"),
        ("OPRA.PILLAR", "definition", ("SPY.OPT",), "parent"),
    }
    assert {
        (request.dataset, request.schema_name, request.symbols, request.stype_in)
        for request in catalog
        if request.expected_split == "training"
    } == expected_products
    assert {
        (request.dataset, request.schema_name, request.symbols, request.stype_in)
        for request in catalog
        if request.expected_split == "validation"
    } == expected_products

    ranges = {request.expected_split: (request.start, request.end_exclusive) for request in catalog}
    assert ranges["training"] == (
        datetime(2018, 5, 1, tzinfo=UTC),
        datetime(2022, 1, 1, tzinfo=UTC),
    )
    assert ranges["validation"] == (
        datetime(2022, 5, 26, tzinfo=UTC),
        datetime(2023, 7, 1, tzinfo=UTC),
    )
    assert len({request.request_id for request in catalog}) == 8


def test_requests_have_stable_complete_identity_and_no_collisions(plan: Any) -> None:
    assert len({request.request_id for request in plan.requests}) == 499
    assert len({request.specification_hash for request in plan.requests}) == 499
    assert len({request.request_hash for request in plan.requests}) == 499
    assert len({request.logical_output_path.lower() for request in plan.requests}) == 499
    for request in plan.requests:
        assert len(request.request_id) == 16
        int(request.request_id, 16)
        assert len(request.specification_hash) == 64
        int(request.specification_hash, 16)
        assert len(request.request_hash) == 64
        int(request.request_hash, 16)
        assert request.start.tzinfo is not None
        assert request.end_exclusive.tzinfo is not None
        assert request.start < request.end_exclusive


def test_cbbo_records_raw_retention_and_ts_recv_contract(plan: Any) -> None:
    assert plan.timestamp_policy == _TS_RECV_POLICY
    for request in _quotes(plan):
        assert request.dataset == "OPRA.PILLAR"
        assert request.symbols == ("SPY.OPT",)
        assert request.stype_in == "parent"
        assert request.encoding == "dbn"
        assert request.raw_dbn_retention_required is True
        assert request.observation_time_source == "ts_recv"
        assert request.normalized_event_time_receive_fallback_allowed is False


def test_generation_is_byte_and_hash_deterministic(plan: Any, tmp_path: Path) -> None:
    development = _development()
    second = _build()
    assert plan == second
    assert plan.plan_hash == second.plan_hash

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    development.write_development_plan(first_path, plan)
    development.write_development_plan(second_path, second)
    assert first_path.read_bytes() == second_path.read_bytes()
    assert (
        hashlib.sha256(first_path.read_bytes()).hexdigest()
        == hashlib.sha256(second_path.read_bytes()).hexdigest()
    )


def test_verifier_accepts_exact_plan_and_rejects_tamper(plan: Any) -> None:
    development = _development()
    development.verify_development_plan_from_files(
        plan,
        acquisition_config_path=_ACQUISITION_CONFIG,
        data_config_path=_DATA_CONFIG,
        source_manifest_path=_SOURCE,
        split_manifest_path=_SPLIT,
        policy_manifest_path=_POLICY,
    )
    first = plan.requests[0]
    tampered = first.model_copy(update={"dataset": "TAMPERED"})
    malformed = plan.model_copy(update={"requests": (tampered, *plan.requests[1:])})
    with pytest.raises(PlanValidationError, match="hash|mismatch"):
        development.verify_development_plan_from_files(
            malformed,
            acquisition_config_path=_ACQUISITION_CONFIG,
            data_config_path=_DATA_CONFIG,
            source_manifest_path=_SOURCE,
            split_manifest_path=_SPLIT,
            policy_manifest_path=_POLICY,
        )


def test_duplicate_request_is_rejected(plan: Any) -> None:
    development = _development()
    payload = plan.model_dump(mode="json", by_alias=True)
    payload["requests"][-1] = payload["requests"][-2]
    with pytest.raises(ValueError, match="duplicate"):
        development.DevelopmentPlan.model_validate(payload)


def test_wrong_split_and_sealed_test_requests_are_rejected(plan: Any) -> None:
    development = _development()
    first_quote_index = next(
        index for index, request in enumerate(plan.requests) if request.schema_name == "cbbo-1m"
    )
    first_quote = plan.requests[first_quote_index]
    wrong_split = development.build_development_request(
        wave=first_quote.wave,
        purpose=first_quote.purpose,
        dataset=first_quote.dataset,
        schema_name=first_quote.schema_name,
        symbols=first_quote.symbols,
        stype_in=first_quote.stype_in,
        window=(first_quote.start, first_quote.end_exclusive),
        expected_split="validation",
        session_date=first_quote.session_date,
        calendar_name=first_quote.calendar,
        raw_dbn_retention_required=True,
        observation_time_source="ts_recv",
    )
    requests = list(plan.requests)
    requests[first_quote_index] = wrong_split
    malformed = plan.model_copy(update={"requests": tuple(requests)})
    with pytest.raises(PlanValidationError, match="canonical|expected|split|hash"):
        development.verify_development_plan_from_files(
            malformed,
            acquisition_config_path=_ACQUISITION_CONFIG,
            data_config_path=_DATA_CONFIG,
            source_manifest_path=_SOURCE,
            split_manifest_path=_SPLIT,
            policy_manifest_path=_POLICY,
        )

    sealed_session = date(2023, 11, 23)
    sealed = development.build_development_request(
        wave="opra_closing_quotes",
        purpose="strategy_b_closing_quote",
        dataset="OPRA.PILLAR",
        schema_name="cbbo-1m",
        symbols=("SPY.OPT",),
        stype_in="parent",
        window=(
            datetime(2023, 11, 23, 20, 50, tzinfo=UTC),
            datetime(2023, 11, 23, 21, 0, tzinfo=UTC),
        ),
        expected_split="validation",
        session_date=sealed_session,
        calendar_name="XNYS",
        raw_dbn_retention_required=True,
        observation_time_source="ts_recv",
    )
    malformed = plan.model_copy(update={"requests": (*plan.requests, sealed)})
    with pytest.raises(PlanValidationError, match="canonical|expected|sealed|count"):
        development.verify_development_plan_from_files(
            malformed,
            acquisition_config_path=_ACQUISITION_CONFIG,
            data_config_path=_DATA_CONFIG,
            source_manifest_path=_SOURCE,
            split_manifest_path=_SPLIT,
            policy_manifest_path=_POLICY,
        )


def test_pilot_manifest_bytes_and_hash_remain_accepted() -> None:
    before = _PILOT_PLAN.read_bytes()
    payload = json.loads(before)
    requests = [AcquisitionRequest.model_validate(item) for item in payload["requests"]]
    for request in requests:
        verify_final_request(request)
    validate_canonical_pilot_plan(requests)
    recomputed = plan_hash(
        requests,
        payload.get("bindings", {}),
        plan_hash_metadata(payload),
    )
    expected_file_hash = (
        "8b74ddf96873ffd8f08ace7e287eb24df"  # pragma: allowlist secret
        "130eb2483ac85a6f9af75355c66aafd"  # pragma: allowlist secret
    )
    expected_plan_hash = (
        "9654fe1c2dfe98946560e27c6f51f110"  # pragma: allowlist secret
        "038613060461fdf75936edf1a7d0ae77"  # pragma: allowlist secret
    )
    _build()
    assert _PILOT_PLAN.read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == expected_file_hash
    assert recomputed == expected_plan_hash


def test_tracked_development_manifest_matches_the_frozen_builder(plan: Any) -> None:
    development = _development()
    raw = _DEVELOPMENT_PLAN.read_bytes()
    payload = json.loads(raw)
    assert raw == (canonical_dumps(payload) + "\n").encode("utf-8")
    assert len(raw) < 500 * 1024
    tracked = development.load_development_plan(_DEVELOPMENT_PLAN)
    development.verify_development_plan_from_files(
        tracked,
        acquisition_config_path=_ACQUISITION_CONFIG,
        data_config_path=_DATA_CONFIG,
        source_manifest_path=_SOURCE,
        split_manifest_path=_SPLIT,
        policy_manifest_path=_POLICY,
    )
    assert tracked == plan


def _pilot_for(request: Any, request_id: str, *, end_delta: timedelta = timedelta()) -> Any:
    return AcquisitionRequest(
        request_id=request_id,
        wave=request.wave,
        dataset=request.dataset,
        schema=request.schema_name,
        symbols=request.symbols,
        stype_in=request.stype_in,
        stype_out=request.stype_out,
        start=request.start,
        end_exclusive=request.end_exclusive + end_delta,
        encoding=request.encoding,
        compression=request.compression,
        expected_split="training",
        session_date=request.session_date,
        calendar=request.calendar,
        logical_output_path=f"data/raw/databento/pilot/{request_id}.dbn",
        specification_hash="a" * 64,
        currency="USD",
        request_hash="b" * 64,
    )


def _state(request_id: str, state: str, request_hash: str = "b" * 64) -> Any:
    return _development().PilotJournalState(
        request_id=request_id,
        request_hash=request_hash,
        state=state,
        raw_path=(f"data/raw/pilot/{request_id}.dbn" if state == "quality_validated" else None),
        raw_checksum="c" * 64 if state == "quality_validated" else None,
        normalized_path=(
            f"data/processed/pilot/{request_id}.parquet" if state == "quality_validated" else None
        ),
        normalized_checksum="d" * 64 if state == "quality_validated" else None,
    )


def _reusable(request: Any, suffix: int, repository_root: Path) -> Any:
    source_id = f"source-{suffix:04d}"
    raw_relative = Path(f"data/raw/development/{source_id}.dbn")
    normalized_relative = Path(f"data/processed/development/{source_id}.parquet")
    quality_relative = Path(f"reports/data/quality/{source_id}.json")
    raw = repository_root / raw_relative
    normalized = repository_root / normalized_relative
    quality = repository_root / quality_relative
    raw.parent.mkdir(parents=True, exist_ok=True)
    normalized.parent.mkdir(parents=True, exist_ok=True)
    quality.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(f"raw-{suffix}".encode())
    normalized.write_bytes(f"normalized-{suffix}".encode())
    quality.write_text(
        json.dumps(
            {
                "normalized_path": normalized_relative.as_posix(),
                "request_id": source_id,
                "status": "passed",
            }
        ),
        encoding="utf-8",
    )
    return _development().DevelopmentDisposition(
        development_request_id=request.request_id,
        development_request_hash=request.request_hash,
        disposition="reusable",
        source_kind="development",
        source_request_id=source_id,
        source_request_hash=f"{suffix + 1:064x}",
        source_state="quality_validated",
        raw_artifact_path=raw_relative.as_posix(),
        raw_checksum=hashlib.sha256(raw.read_bytes()).hexdigest(),
        normalized_artifact_path=normalized_relative.as_posix(),
        normalized_checksum=hashlib.sha256(normalized.read_bytes()).hexdigest(),
        quality_report_path=quality_relative.as_posix(),
    )


def test_exact_quality_validated_pilot_overlap_requires_artifact_verification(plan: Any) -> None:
    development = _development()
    request = _quotes(plan)[0]
    pilot = _pilot_for(request, "pilot-quality")
    with pytest.raises(PlanValidationError, match="artifact verification"):
        development.derive_pilot_development_dispositions(
            plan,
            [pilot],
            {pilot.request_id: _state(pilot.request_id, "quality_validated")},
        )


def test_reusable_pilot_artifacts_are_verified_and_bound_by_actual_path(
    tmp_path: Path,
    plan: Any,
) -> None:
    development = _development()
    request = _quotes(plan)[0]
    pilot = _pilot_for(request, "pilot-verified-artifacts")
    raw = tmp_path / "data/raw/pilot/payload.dbn.zst"
    normalized = tmp_path / "data/processed/pilot/payload.parquet"
    quality = tmp_path / f"reports/data/quality/{pilot.request_id}.json"
    raw.parent.mkdir(parents=True)
    normalized.parent.mkdir(parents=True)
    quality.parent.mkdir(parents=True)
    raw.write_bytes(b"raw artifact")
    normalized.write_bytes(b"normalized artifact")
    quality.write_text(
        json.dumps(
            {
                "normalized_path": str(normalized),
                "request_id": pilot.request_id,
                "status": "passed",
            }
        ),
        encoding="utf-8",
    )
    states = {
        pilot.request_id: development.PilotJournalState(
            request_id=pilot.request_id,
            request_hash=pilot.request_hash,
            state="quality_validated",
            raw_path=str(raw),
            raw_checksum=hashlib.sha256(raw.read_bytes()).hexdigest(),
            normalized_path=str(normalized),
            normalized_checksum=hashlib.sha256(normalized.read_bytes()).hexdigest(),
        )
    }
    result = development.derive_pilot_development_dispositions(
        plan,
        [pilot],
        states,
        repository_root=tmp_path,
    )
    binding = result.dispositions[0]
    assert binding.raw_artifact_path == "data/raw/pilot/payload.dbn.zst"
    assert binding.normalized_artifact_path == "data/processed/pilot/payload.parquet"
    assert binding.quality_report_path == f"reports/data/quality/{pilot.request_id}.json"


def test_reusable_pilot_artifact_checksum_mismatch_is_rejected(
    tmp_path: Path,
    plan: Any,
) -> None:
    development = _development()
    request = _quotes(plan)[0]
    pilot = _pilot_for(request, "pilot-tampered-artifact")
    raw = tmp_path / "raw.dbn.zst"
    normalized = tmp_path / "normalized.parquet"
    quality = tmp_path / f"reports/data/quality/{pilot.request_id}.json"
    raw.write_bytes(b"raw")
    normalized.write_bytes(b"normalized")
    quality.parent.mkdir(parents=True)
    quality.write_text(
        json.dumps(
            {
                "normalized_path": str(normalized),
                "request_id": pilot.request_id,
                "status": "passed",
            }
        ),
        encoding="utf-8",
    )
    state = development.PilotJournalState(
        request_id=pilot.request_id,
        request_hash=pilot.request_hash,
        state="quality_validated",
        raw_path=str(raw),
        raw_checksum="0" * 64,
        normalized_path=str(normalized),
        normalized_checksum=hashlib.sha256(normalized.read_bytes()).hexdigest(),
    )
    with pytest.raises(PlanValidationError, match="raw artifact checksum"):
        development.derive_pilot_development_dispositions(
            plan,
            [pilot],
            {pilot.request_id: state},
            repository_root=tmp_path,
        )


def test_exact_uncertain_pilot_overlap_remains_unavailable_and_accounted(plan: Any) -> None:
    development = _development()
    request = _quotes(plan)[0]
    pilot = _pilot_for(request, "pilot-uncertain")
    result = development.derive_pilot_development_dispositions(
        plan,
        [pilot],
        {pilot.request_id: _state(pilot.request_id, "uncertain_billing")},
    )
    scope = development.derive_current_development_scope(plan, result.dispositions)
    assert result.dispositions[0].disposition == "unavailable"
    assert result.dispositions[0].raw_checksum is None
    assert request.request_id not in {item.request_id for item in scope.requests}
    assert request.request_id in {item.development_request_id for item in scope.unavailable}
    assert request.request_id in {item.request_id for item in plan.requests}
    assert scope.new_request_count == 498
    assert scope.unavailable_request_count == 1


def test_reconciled_billed_pilot_overlap_remains_unavailable(plan: Any) -> None:
    development = _development()
    request = _quotes(plan)[0]
    pilot = _pilot_for(request, "pilot-reconciled-billed")
    result = development.derive_pilot_development_dispositions(
        plan,
        [pilot],
        {pilot.request_id: _state(pilot.request_id, "billed_without_validated_artifact")},
    )
    scope = development.derive_current_development_scope(plan, result.dispositions)
    assert result.dispositions[0].disposition == "unavailable"
    assert scope.unavailable[0].source_state == "billed_without_validated_artifact"
    assert request.request_id not in {item.request_id for item in scope.requests}


@pytest.mark.parametrize("state", ["request_started", "raw_validated", "normalized"])
def test_in_flight_or_local_resume_overlap_cannot_reenter_provider_scope(
    plan: Any,
    state: str,
) -> None:
    development = _development()
    quote = next(request for request in plan.requests if request.schema_name == "cbbo-1m")
    pilot = _pilot_for(quote, "cccccccccccccccc")
    result = development.derive_pilot_development_dispositions(
        plan,
        [pilot],
        {pilot.request_id: _state(pilot.request_id, state)},
    )
    scope = development.derive_current_development_scope(
        plan,
        result.dispositions,
        other_quarantined_source_request_ids=result.other_quarantined_request_ids,
    )
    assert scope.unavailable_request_count == 1
    assert scope.unavailable[0].source_state == state
    assert quote.request_id not in {request.request_id for request in scope.requests}


def test_similar_but_nonidentical_pilot_request_is_not_reused(plan: Any) -> None:
    development = _development()
    request = _quotes(plan)[0]
    pilot = _pilot_for(request, "pilot-similar", end_delta=timedelta(minutes=1))
    result = development.derive_pilot_development_dispositions(
        plan,
        [pilot],
        {pilot.request_id: _state(pilot.request_id, "quality_validated")},
    )
    scope = development.derive_current_development_scope(plan, result.dispositions)
    assert result.dispositions == ()
    assert scope.new_request_count == 499
    assert request.request_id in {item.request_id for item in scope.requests}


def test_unmatched_uncertain_pilot_request_is_explicit_but_never_scoped(plan: Any) -> None:
    development = _development()
    catalog = _catalog(plan)[0]
    unrelated = _pilot_for(catalog, "pilot-other-uncertain", end_delta=timedelta(days=1))
    result = development.derive_pilot_development_dispositions(
        plan,
        [unrelated],
        {unrelated.request_id: _state(unrelated.request_id, "uncertain_billing")},
    )
    scope = development.derive_current_development_scope(
        plan,
        result.dispositions,
        other_quarantined_source_request_ids=result.other_quarantined_request_ids,
    )
    assert result.dispositions == ()
    assert result.other_quarantined_request_ids == (unrelated.request_id,)
    assert unrelated.request_id not in {item.request_id for item in scope.requests}
    assert scope.other_quarantined_source_request_ids == (unrelated.request_id,)


def test_scope_is_deterministic_exact_and_shrinks_without_source_change(
    plan: Any,
    tmp_path: Path,
) -> None:
    development = _development()
    first_disposition = _reusable(plan.requests[0], 0, tmp_path)
    second_disposition = _reusable(plan.requests[1], 1, tmp_path)
    first = development.derive_current_development_scope(
        plan, [first_disposition], repository_root=tmp_path
    )
    repeat = development.derive_current_development_scope(
        plan, [first_disposition], repository_root=tmp_path
    )
    smaller = development.derive_current_development_scope(
        plan,
        [first_disposition, second_disposition],
        repository_root=tmp_path,
    )
    assert first == repeat
    assert first.scope_hash == repeat.scope_hash
    assert first.new_request_count == 498
    assert smaller.new_request_count == 497
    assert [item.request_id for item in first.requests] == [
        item.request_id for item in plan.requests[1:]
    ]
    assert [item.request_hash for item in first.requests] == [
        item.request_hash for item in plan.requests[1:]
    ]
    assert not {item.development_request_id for item in first.reusable} & {
        item.request_id for item in first.requests
    }


def test_scope_cannot_subtract_unverified_reusable_artifacts(
    plan: Any,
    tmp_path: Path,
) -> None:
    development = _development()
    disposition = _reusable(plan.requests[0], 0, tmp_path).model_copy(
        update={"raw_artifact_path": "data/raw/development/does-not-exist.dbn"}
    )
    with pytest.raises(PlanValidationError, match="raw artifact"):
        development.derive_current_development_scope(
            plan,
            [disposition],
            repository_root=tmp_path,
        )


def test_scope_rejects_duplicate_unknown_and_tampered_dispositions(
    plan: Any,
    tmp_path: Path,
) -> None:
    development = _development()
    disposition = _reusable(plan.requests[0], 0, tmp_path)
    with pytest.raises(PlanValidationError, match="duplicate"):
        development.derive_current_development_scope(plan, [disposition, disposition])
    unknown = disposition.model_copy(update={"development_request_id": "unknown"})
    with pytest.raises(PlanValidationError, match="canonical"):
        development.derive_current_development_scope(plan, [unknown])
    wrong_hash = disposition.model_copy(update={"development_request_hash": "0" * 64})
    with pytest.raises(PlanValidationError, match="hash"):
        development.derive_current_development_scope(plan, [wrong_hash])


def test_scope_round_trip_detects_tamper(plan: Any, tmp_path: Path) -> None:
    development = _development()
    scope = development.derive_current_development_scope(
        plan,
        [_reusable(plan.requests[0], 0, tmp_path)],
        repository_root=tmp_path,
    )
    path = tmp_path / "scope.json"
    development.write_development_scope(path, scope)
    assert development.load_development_scope(path, plan, repository_root=tmp_path) == scope
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scope_hash"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PlanValidationError, match="scope hash"):
        development.load_development_scope(path, plan)


def test_pilot_journal_reader_is_read_only(tmp_path: Path) -> None:
    development = _development()
    journal = tmp_path / "journal.sqlite"
    with sqlite3.connect(journal) as database:
        database.execute(
            """
            CREATE TABLE requests (
                request_id TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                raw_path TEXT,
                raw_checksum TEXT,
                normalized_path TEXT,
                normalized_checksum TEXT
            )
            """
        )
        database.execute(
            "INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "pilot",
                "b" * 64,
                "quality_validated",
                "raw.dbn",
                "c" * 64,
                "normalized.parquet",
                "d" * 64,
            ),
        )
    before = hashlib.sha256(journal.read_bytes()).hexdigest()
    states = development.load_pilot_journal_states(journal)
    after = hashlib.sha256(journal.read_bytes()).hexdigest()
    assert states["pilot"].state == "quality_validated"
    assert before == after
    assert not journal.with_name(f"{journal.name}-wal").exists()
    assert not journal.with_name(f"{journal.name}-shm").exists()


def test_pilot_journal_reader_rejects_uncheckpointed_wal(tmp_path: Path) -> None:
    development = _development()
    journal = tmp_path / "journal.sqlite"
    writer = sqlite3.connect(journal)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute(
            """
            CREATE TABLE requests (
                request_id TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                raw_path TEXT,
                raw_checksum TEXT,
                normalized_path TEXT,
                normalized_checksum TEXT
            )
            """
        )
        writer.commit()
        writer.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        writer.execute(
            "INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("pending-wal", "b" * 64, "uncertain_billing", None, None, None, None),
        )
        writer.commit()
        wal = journal.with_name(f"{journal.name}-wal")
        assert wal.stat().st_size > 0
        with pytest.raises(PlanValidationError, match="WAL"):
            development.load_pilot_journal_states(journal)
    finally:
        writer.close()


def test_builder_rejects_calendar_library_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    development = _development()
    monkeypatch.setattr(
        development,
        "calendar_library_version",
        lambda: "drifted-calendar-version",
        raising=False,
    )
    with pytest.raises(PlanValidationError, match="calendar.*version"):
        _build()


def test_plan_and_scope_never_construct_a_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from neuralmarket.data.acquisition import providers

    constructions: list[str] = []

    def reject_construction(*args: object, **kwargs: object) -> None:
        del args, kwargs
        constructions.append("provider")
        raise AssertionError("offline development planning constructed a provider")

    monkeypatch.setattr(providers.DatabentoMetadataProvider, "__init__", reject_construction)
    monkeypatch.setattr(providers, "create_databento_paid_provider", reject_construction)
    plan = _build()
    _development().derive_current_development_scope(plan, [])
    assert constructions == []
