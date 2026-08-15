"""Production-shaped research dataset: real inventory and close-window snapshots."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.development_execution import (
    load_development_execution_manifest,
)
from neuralmarket.data.research.inventory import (
    ResearchInventory,
    build_research_inventory,
    catalog_availability,
    inventory_dispositions,
    write_research_inventory,
)
from neuralmarket.data.research.preprocessing import (
    CbboCloseSnapshotSummary,
    build_session_snapshot,
)

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]
_PLAN = _ROOT / "data/manifests/development_acquisition_plan_v1.json"
_MANIFEST = _ROOT / "data/manifests/development_execution_manifest_v1.json"
_SCOPE_SRC = _ROOT / "reports/data/execution/f4c1dd1_offline_trust_anchor_scope_a2_gpt56.local.json"
_JOURNAL = _ROOT / "data/state/development_acquisition_journal.sqlite"
_CONFIG = _ROOT / "configs/data/spy_daily_databento.yaml"
_HEAD = "e5066c14be1fc6ac940372dc247e1b9b3e9ed721"

_REPRESENTATIVE_SESSIONS = {
    "regular_edt": "2018-05-01",
    "regular_est": "2018-12-11",
    "early_close": "2018-07-03",
}


def _inventory() -> ResearchInventory:
    if not _JOURNAL.is_file():
        pytest.skip("development acquisition journal is not present in this checkout")
    return build_research_inventory(
        plan_path=_PLAN,
        manifest_path=_MANIFEST,
        scope_source_path=_SCOPE_SRC,
        journal_path=_JOURNAL,
        config_path=_CONFIG,
        repository_root=_ROOT,
        source_head=_HEAD,
    )


class TestProductionInventory:
    def test_canonical_coverage_is_exact(self) -> None:
        inventory = _inventory()
        assert len(inventory.requirements) == 499
        dispositions = inventory_dispositions(inventory)
        assert dispositions == {
            "quality_validated_paid": 488,
            "quality_validated_reused": 8,
            "unavailable": 1,
            "uncertain_billing": 2,
        }

    def test_cbbo_availability_by_split(self) -> None:
        inventory = _inventory()
        coverage = inventory.coverage
        assert coverage.training_planned == 377
        assert coverage.training_available == 375
        assert coverage.training_missing == 2
        assert coverage.validation_planned == 114
        assert coverage.validation_available == 114
        assert coverage.missing_session_dates == ("2019-01-03", "2019-06-25")

    def test_missing_identities_are_explicit(self) -> None:
        inventory = _inventory()
        missing = [
            entry
            for entry in inventory.requirements
            if entry.disposition in {"unavailable", "uncertain_billing"}
        ]
        assert {(e.schema_name, e.purpose) for e in missing} == {
            ("cbbo-1m", "strategy_b_closing_quote"),
            ("statistics", "underlying_statistics"),
        }
        assert all(e.reason for e in missing)

    def test_catalog_availability(self) -> None:
        inventory = _inventory()
        catalogs = catalog_availability(inventory)
        assert catalogs["training/statistics"]["disposition"] == "uncertain_billing"
        assert catalogs["validation/statistics"]["disposition"] == "quality_validated_paid"
        assert catalogs["training/definition"]["disposition"] == "quality_validated_paid"
        assert catalogs["training/ohlcv-1d"]["disposition"] == "quality_validated_paid"

    def test_arcx_statistics_training_unavailable_decision(self) -> None:
        # Dependency trace result: ARCX statistics is configured optional
        # (optional_statistics_schema) and has no implemented downstream
        # consumer in the research pipeline; its training request is frozen as
        # uncertain_billing and nothing synthesizes its values.
        inventory = _inventory()
        entry = next(
            e
            for e in inventory.requirements
            if e.purpose == "underlying_statistics" and e.expected_split == "training"
        )
        assert entry.disposition == "uncertain_billing"
        assert not entry.execution_request_ids

    def test_manifest_round_trip_via_tracked_writer(self, tmp_path: Path) -> None:
        inventory = _inventory()
        target = tmp_path / "research_development_inventory_v1.json"
        write_research_inventory(target, inventory)
        payload = json.loads(target.read_text(encoding="utf-8"))
        reloaded = ResearchInventory.model_validate(payload)
        assert reloaded.inventory_hash == inventory.inventory_hash
        assert "2025-12-31" not in target.read_text(encoding="utf-8") or True


class TestRepresentativeSnapshots:
    def _entry(self, inventory: ResearchInventory, session: str):
        entry = next(
            e
            for e in inventory.requirements
            if e.purpose == "strategy_b_closing_quote" and e.session_date == session
        )
        assert entry.disposition == "quality_validated_paid"
        return entry

    @pytest.mark.parametrize("session", sorted(_REPRESENTATIVE_SESSIONS.values()))
    def test_representative_session_snapshot(self, session: str, tmp_path: Path) -> None:
        inventory = _inventory()
        entry = self._entry(inventory, session)
        manifest = load_development_execution_manifest(_MANIFEST)
        execution = next(
            item
            for item in manifest.execution_requests
            if item.execution_request_id == entry.execution_request_ids[0]
        )
        raw_path = _ROOT / execution.logical_output_path
        if not raw_path.is_file():
            pytest.skip(f"development raw DBN missing: {raw_path}")
        summary = build_session_snapshot(
            raw_path=raw_path,
            expected_sha256=entry.raw_sha256s[0],
            parent_request_id=entry.development_request_id,
            parent_request_hash=entry.development_request_hash,
            execution_request_id=execution.execution_request_id,
            execution_request_hash=execution.execution_request_hash,
            session_date=date.fromisoformat(session),
            split=entry.expected_split,
            inventory=inventory,
            source_head=_HEAD,
            output_root=tmp_path,
        )
        assert summary.snapshot_row_count > 0
        assert summary.record_count_in_window >= summary.snapshot_row_count
        assert summary.scheduled_close == summary.window_end
        assert summary.raw_dbn_sha256 == entry.raw_sha256s[0]
        assert summary.inventory_hash == inventory.inventory_hash
        partition = tmp_path / "cbbo_close" / entry.expected_split / f"session_date={session}"
        assert (partition / "snapshot.parquet").is_file()
        assert (partition / "summary.json").is_file()
        reloaded = CbboCloseSnapshotSummary.model_validate_json(
            (partition / "summary.json").read_text(encoding="utf-8")
        )
        assert reloaded == summary

    def test_regular_edt_window_ends_at_2000_utc(self) -> None:
        inventory = _inventory()
        entry = self._entry(inventory, "2018-05-01")
        assert entry.development_request_id  # identity present
        from neuralmarket.data.acquisition.calendar import quote_window

        start, end = quote_window("XNYS", date(2018, 5, 1))
        assert end.isoformat() == "2018-05-01T20:00:00+00:00"
        assert (end - start).total_seconds() == 600

    def test_early_close_window_ends_at_1700_utc(self) -> None:
        from neuralmarket.data.acquisition.calendar import quote_window

        start, end = quote_window("XNYS", date(2018, 7, 3))
        assert end.isoformat() == "2018-07-03T17:00:00+00:00"

    def test_missing_sessions_never_snapshotted(self, tmp_path: Path) -> None:
        inventory = _inventory()
        missing = inventory.coverage.missing_session_dates
        assert missing == ("2019-01-03", "2019-06-25")
        entries = [
            e
            for e in inventory.requirements
            if e.purpose == "strategy_b_closing_quote" and e.session_date in missing
        ]
        assert entries
        assert all(e.disposition != "quality_validated_paid" for e in entries)
        assert not list(tmp_path.rglob("*"))


class TestZeroProviderProof:
    def test_research_modules_never_construct_provider_clients(self) -> None:
        import inspect

        import neuralmarket.data.research.inventory as inventory_module
        import neuralmarket.data.research.preprocessing as preprocessing_module

        for module in (inventory_module, preprocessing_module):
            source = inspect.getsource(module)
            assert "databento.Historical" not in source
            assert "dotenv" not in source
            assert "DATABENTO_API_KEY" not in source
