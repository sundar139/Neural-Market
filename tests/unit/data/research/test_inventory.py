"""Research inventory: dispositions, fragment reconstruction, missingness, seals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.development_execution import (
    load_development_execution_manifest,
)
from neuralmarket.data.errors import CoverageError
from neuralmarket.data.research.inventory import (
    ResearchInventory,
    build_research_inventory,
    verify_fragment_parent_coverage,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]
_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_SCOPE_SRC = _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_JOURNAL = _ROOT / "data/state/development_acquisition_journal.sqlite"
_CONFIG = _ROOT / "configs/data/spy_daily_databento.yaml"


def _production_inputs() -> tuple:
    if not _JOURNAL.is_file():
        pytest.skip("development acquisition journal is not present in this checkout")
    return (
        _PLAN,
        _MANIFEST,
        _SCOPE_SRC,
        _JOURNAL,
        _CONFIG,
        _ROOT,
        "e5066c14be1fc6ac940372dc247e1b9b3e9ed721",
    )


def _build() -> ResearchInventory:
    return build_research_inventory(
        plan_path=_PLAN,
        manifest_path=_MANIFEST,
        scope_source_path=_SCOPE_SRC,
        journal_path=_JOURNAL,
        config_path=_CONFIG,
        repository_root=_ROOT,
        source_head="e5066c14be1fc6ac940372dc247e1b9b3e9ed721",
    )


@dataclass(frozen=True)
class _Window:
    start: datetime
    end_exclusive: datetime


def _windows(start: datetime, pieces: list[tuple[int, int]]) -> list[_Window]:
    import datetime as _dt

    return [
        _Window(start + _dt.timedelta(days=a), start + _dt.timedelta(days=b)) for a, b in pieces
    ]


class TestFragmentParentCoverage:
    def test_exact_tiling_accepted(self) -> None:
        start = datetime(2018, 5, 1, tzinfo=UTC)
        children = _windows(start, [(0, 30), (30, 60), (60, 90)])
        verify_fragment_parent_coverage(children, start, start.replace(year=2018, month=7, day=30))

    def test_gap_rejected(self) -> None:
        start = datetime(2018, 5, 1, tzinfo=UTC)
        children = _windows(start, [(0, 30), (31, 60)])
        with pytest.raises(CoverageError, match="gap or overlap"):
            verify_fragment_parent_coverage(children, start, start.replace(month=7))

    def test_overlap_rejected(self) -> None:
        start = datetime(2018, 5, 1, tzinfo=UTC)
        children = _windows(start, [(0, 30), (29, 60)])
        with pytest.raises(CoverageError, match="gap or overlap"):
            verify_fragment_parent_coverage(children, start, start.replace(month=7))

    def test_short_tail_rejected(self) -> None:
        start = datetime(2018, 5, 1, tzinfo=UTC)
        children = _windows(start, [(0, 30), (30, 59)])
        with pytest.raises(CoverageError, match="end_exclusive"):
            verify_fragment_parent_coverage(children, start, start.replace(month=7))

    def test_real_opra_definition_fragments_tile_exactly(self) -> None:
        manifest = load_development_execution_manifest(_MANIFEST)
        fragments = [item for item in manifest.execution_requests if item.fragment_count > 1]
        assert len(fragments) == 58
        by_parent: dict[str, list] = {}
        for item in fragments:
            by_parent.setdefault(item.parent_request_id, []).append(item)
        assert sorted(len(v) for v in by_parent.values()) == [14, 44]
        for parent_id, children in by_parent.items():
            parent = next(p for p in manifest.parent_requests if p.request_id == parent_id)
            verify_fragment_parent_coverage(children, parent.start, parent.end_exclusive)


class TestInventorySealing:
    def test_hash_is_deterministic(self) -> None:
        first = _build()
        second = _build()
        assert first.inventory_hash == second.inventory_hash
        assert first.model_dump(mode="json", by_alias=True) == second.model_dump(
            mode="json", by_alias=True
        )

    def test_hash_covers_content(self) -> None:
        inventory = _build()
        tampered = inventory.model_copy(update={"source_head": "f" * 40})
        with pytest.raises(ValueError, match="hash mismatch"):
            ResearchInventory.model_validate(tampered.model_dump(mode="json", by_alias=True))

    def test_duplicate_requirement_rejected(self) -> None:
        inventory = _build()
        payload = inventory.model_dump(mode="json", by_alias=True)
        payload.pop("inventory_hash", None)
        payload["requirements"].append(payload["requirements"][0])
        with pytest.raises(ValueError, match="duplicate requirement"):
            ResearchInventory.model_validate(payload)

    def test_sealed_final_test_session_rejected(self) -> None:
        # The final-test block starts after the validation anchor plus the
        # purge/embargo boundary; any session on or after 2023-07-01 is sealed.
        inventory = _build()
        sealed_dates = {
            entry.session_date
            for entry in inventory.requirements
            if entry.session_date and entry.session_date >= "2023-07-01"
        }
        assert sealed_dates == set(), sealed_dates

    def test_every_requirement_has_explicit_disposition(self) -> None:
        inventory = _build()
        assert len(inventory.requirements) == 499
        counts: dict[str, int] = {}
        for entry in inventory.requirements:
            counts[entry.disposition] = counts.get(entry.disposition, 0) + 1
        assert sum(counts.values()) == 499
        assert counts == {
            "quality_validated_paid": 488,
            "quality_validated_reused": 8,
            "unavailable": 1,
            "uncertain_billing": 2,
        }


class TestMissingnessPolicy:
    def test_uncertain_cbbo_session_stays_missing(self) -> None:
        inventory = _build()
        uncertain = [
            entry for entry in inventory.requirements if entry.disposition == "uncertain_billing"
        ]
        assert len(uncertain) == 2
        cbbo_uncertain = [
            entry for entry in uncertain if entry.purpose == "strategy_b_closing_quote"
        ]
        assert len(cbbo_uncertain) == 1
        assert cbbo_uncertain[0].session_date in inventory.coverage.missing_session_dates

    def test_unavailable_cbbo_session_stays_missing(self) -> None:
        inventory = _build()
        unavailable = [
            entry for entry in inventory.requirements if entry.disposition == "unavailable"
        ]
        assert len(unavailable) == 1
        assert unavailable[0].session_date in inventory.coverage.missing_session_dates

    def test_planned_available_missing_reconcile(self) -> None:
        inventory = _build()
        coverage = inventory.coverage
        for planned, available, missing in (
            (
                coverage.training_planned,
                coverage.training_available,
                coverage.training_missing,
            ),
            (
                coverage.validation_planned,
                coverage.validation_available,
                coverage.validation_missing,
            ),
        ):
            assert planned == available + missing
            assert missing >= 0
        assert coverage.validation_missing == 0
        assert coverage.training_missing == 2
        assert coverage.training_planned == 377
        assert coverage.training_available == 375
        assert coverage.validation_planned == 114
        assert coverage.validation_available == 114
        assert coverage.missing_session_dates == ("2019-01-03", "2019-06-25")

    def test_arcx_statistics_training_is_uncertain_never_synthesized(self) -> None:
        inventory = _build()
        statistics = [
            entry for entry in inventory.requirements if entry.purpose == "underlying_statistics"
        ]
        assert len(statistics) == 2
        by_split = {entry.expected_split: entry.disposition for entry in statistics}
        assert by_split == {"training": "uncertain_billing", "validation": "quality_validated_paid"}

    def test_arcx_statistics_has_no_downstream_consumer(self) -> None:
        # The research preprocessing consumer only reads cbbo-1m raw DBNs; no
        # module reads ARCX statistics data, so its absence cannot fabricate
        # values anywhere in the pipeline.
        import inspect

        import neuralmarket.data.research.preprocessing as module

        source = inspect.getsource(module)
        assert "statistics" not in source

    def test_reusable_pilot_cbbo_bound_to_artifacts(self) -> None:
        inventory = _build()
        reused = [
            entry
            for entry in inventory.requirements
            if entry.disposition == "quality_validated_reused"
        ]
        assert len(reused) == 8
        assert all(entry.pilot_source_request_id for entry in reused)


class TestInventoryManifestWriting:
    def test_write_round_trip(self, tmp_path: Path) -> None:
        from neuralmarket.data.research.inventory import write_research_inventory

        inventory = _build()
        target = tmp_path / "research_development_inventory_v1.json"
        write_research_inventory(target, inventory)
        payload = json.loads(target.read_text(encoding="utf-8"))
        reloaded = ResearchInventory.model_validate(payload)
        assert reloaded.inventory_hash == inventory.inventory_hash
        assert hashlib.sha256(target.read_bytes()).hexdigest()
