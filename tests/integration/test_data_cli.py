import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from neuralmarket.cli import data as data_module
from neuralmarket.cli.main import app
from neuralmarket.data.calendar import BoundaryExclusion, SplitResult
from neuralmarket.data.configuration import load_data_config
from neuralmarket.data.manifests import (
    DateRange,
    build_source_manifest,
    build_split_manifest,
    canonical_summary_hash,
    write_manifest,
)
from neuralmarket.data.sources.databento import DatabentoSource

runner = CliRunner()
_CONFIG = "configs/data/spy_daily_databento.yaml"


def _selector_summary() -> dict[str, object]:
    summary: dict[str, object] = {
        "validation_method": "chunked_symbology_resolution",
        "chunk_count": 92,
        "successful_chunk_count": 92,
        "failed_chunk_count": 0,
        "empty_chunk_count": 0,
        "total_mapping_count": 1000,
        "distinct_output_count": 500,
        "distinct_child_symbol_count": 400,
        "session_gap_count": 0,
        "first_valid_date": "2018-05-01",
        "end_exclusive": "2026-01-01",
    }
    summary["canonical_summary_hash"] = canonical_summary_hash(summary)
    return summary


_FULL = {"start": "2013-04-01", "end": "2026-07-11"}
_SCHEMAS = {
    "ARCX.PILLAR": ["definition", "ohlcv-1d", "bbo-1m", "statistics"],
    "OPRA.PILLAR": ["definition", "cbbo-1m"],
}
_PUBLISHERS = [
    {
        "dataset": "ARCX.PILLAR",
        "publisher_id": 2,
        "venue": "ARCX",
        "description": "NYSE Arca Pillar",
    },
    {"dataset": "OPRA.PILLAR", "publisher_id": 9, "venue": "OPRA", "description": "OPRA"},
]


class _Meta:
    def get_dataset_range(self, dataset: str) -> dict[str, str]:
        return _FULL

    def list_schemas(self, dataset: str) -> list[str]:
        return _SCHEMAS[dataset]

    def list_publishers(self) -> list[dict[str, Any]]:
        return _PUBLISHERS

    def get_cost(self, **kwargs: object) -> float:
        return 3.0

    def get_billable_size(self, **kwargs: object) -> int:
        return 2048

    def get_record_count(self, **kwargs: object) -> int:
        return 100


class _Sym:
    def resolve(self, *, symbols: list[str], **kwargs: Any) -> dict[str, Any]:
        if kwargs.get("stype_in") == "parent":
            start, end = kwargs["start_date"], kwargs["end_date"]
            return {
                "status": 1,
                "message": "Partially resolved",
                "partial": [],
                "not_found": [],
                "result": {"SPY   250101C00500000": [{"d0": start, "d1": end, "s": "1"}]},
            }
        return {
            "result": {
                symbol: [{"d0": "2018-05-01", "d1": "2026-01-01", "s": "1"}] for symbol in symbols
            },
            "status": 0,
            "partial": [],
            "not_found": [],
        }


class _Client:
    metadata = _Meta()
    symbology = _Sym()


@pytest.mark.integration
def test_data_help() -> None:
    assert runner.invoke(app, ["data", "--help"]).exit_code == 0


@pytest.mark.integration
def test_contracts_validate_exit_zero() -> None:
    assert runner.invoke(app, ["data", "contracts", "validate"]).exit_code == 0


@pytest.mark.integration
def test_contracts_bad_action_exit_two() -> None:
    assert runner.invoke(app, ["data", "contracts", "explode"]).exit_code == 2


@pytest.mark.integration
def test_split_freeze_deterministic(tmp_path: Path) -> None:
    out_a, out_b = tmp_path / "a.json", tmp_path / "b.json"
    for out in (out_a, out_b):
        result = runner.invoke(
            app, ["data", "split", "freeze", "--config", _CONFIG, "--output", str(out)]
        )
        assert result.exit_code == 0
    a = json.loads(out_a.read_text(encoding="utf-8"))
    b = json.loads(out_b.read_text(encoding="utf-8"))
    assert a["manifest_hash"] == b["manifest_hash"]
    assert a["final_test_access_status"] == "sealed"
    assert a["training_start"] == "2018-05-01"
    assert all(e["session_count"] == 100 for e in a["excluded_boundary_ranges"])


@pytest.mark.integration
def test_qualify_without_key_exit_two(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    result = runner.invoke(
        app,
        [
            "data",
            "qualify",
            "--config",
            _CONFIG,
            "--output",
            str(tmp_path / "report.json"),
            "--source-manifest",
            str(tmp_path / "source.json"),
        ],
    )
    assert result.exit_code == 2


@pytest.mark.integration
def test_qualify_happy_path_writes_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(data_module, "_load_dotenv", lambda root: None)
    monkeypatch.setattr(
        data_module.DatabentoSource,
        "from_env",
        classmethod(lambda cls: DatabentoSource(_Client())),
    )
    report = tmp_path / "report.json"
    source = tmp_path / "source.json"
    result = runner.invoke(
        app,
        [
            "data",
            "qualify",
            "--config",
            _CONFIG,
            "--output",
            str(report),
            "--source-manifest",
            str(source),
        ],
    )
    assert result.exit_code == 0
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["qualification_status"] == "qualified"
    assert len(data["attempts"]) == 6
    assert [a["name"] for a in data["attempts"]] == [
        "EQUS.SUMMARY",
        "EQUS.MINI",
        "DBEQ.BASIC",
        "ARCX.PILLAR attempt 1",
        "ARCX.PILLAR attempt 2",
        "ARCX.PILLAR",
    ]
    assert data["attempts"][2]["outcome"] == "failed_schema"
    assert data["underlying_publisher"]["venue"] == "ARCX"
    assert data["downloaded_records"] == 0
    assert data["cost_totals"]["combined_full_study"] is not None
    assert data["options_parent_selector"]["validation_method"] == "chunked_symbology_resolution"
    assert data["options_parent_selector"]["resolved"] is True
    assert data["options_parent_selector"]["summary"]["session_gap_count"] == 0
    assert "DATABENTO_API_KEY" not in report.read_text(encoding="utf-8")
    manifest = json.loads(source.read_text(encoding="utf-8"))
    assert manifest["options"]["validation_method"] == "chunked_symbology_resolution"
    assert manifest["options"]["selector_summary"]["chunk_count"] == 92
    assert manifest["underlying"]["dataset"] == "ARCX.PILLAR"
    assert manifest["underlying"]["source_class"] == "primary_listing_venue"
    assert manifest["underlying"]["venue_specific"] is True
    assert manifest["underlying"]["official_nbbo"] is False
    assert manifest["transaction_cost_source_policy"]["primary"] == "explicit_modeled_costs"
    assert manifest["manifest_hash"]


@pytest.mark.integration
def test_manifests_bad_action_exit_two() -> None:
    result = runner.invoke(
        app, ["data", "manifests", "boom", "--source", "x.json", "--split", "y.json"]
    )
    assert result.exit_code == 2


@pytest.mark.integration
def test_manifests_verify(tmp_path: Path) -> None:
    config = load_data_config(Path(_CONFIG))
    excl = BoundaryExclusion(date(2021, 1, 1), date(2021, 4, 1), 100, "h")
    result_obj = SplitResult(
        training_start=date(2018, 5, 1),
        training_end=date(2021, 12, 31),
        validation_start=date(2022, 5, 26),
        validation_end=date(2023, 6, 30),
        test_start=date(2023, 11, 22),
        test_end=date(2025, 12, 31),
        training_sessions=1000,
        validation_sessions=275,
        test_sessions=528,
        training_hash="t",
        validation_hash="v",
        test_hash="x",
        calendar_hash="c",
        boundary_exclusions=(excl, excl),
    )
    full = DateRange(start_date=date(2013, 4, 1), end_date=date(2026, 6, 30))
    split_path, source_path = tmp_path / "split.json", tmp_path / "source.json"
    write_manifest(
        split_path,
        build_split_manifest(
            config,
            result_obj,
            config_hash="h",
            git_commit="c",
            generated_at="2020-01-01T00:00:00+00:00",
        ),
    )
    write_manifest(
        source_path,
        build_source_manifest(
            config,
            underlying_ranges={"ARCX.PILLAR/ohlcv-1d": full, "ARCX.PILLAR/bbo-1m": full},
            options_ranges={"OPRA.PILLAR/cbbo-1m": full},
            publisher={"publisher_id": 2, "venue": "ARCX", "description": "NYSE Arca"},
            optional_schemas={"statistics": "available"},
            underlying_symbol_resolution="resolved",
            options_symbol_resolution="resolved",
            options_validation_method="chunked_symbology_resolution",
            options_selector_summary=_selector_summary(),
            qualification_status="qualified",
            qualification_timestamp="2020-01-01T00:00:00+00:00",
            config_hash="h",
            git_commit="c",
            generated_at="2020-01-01T00:00:00+00:00",
        ),
    )
    result = runner.invoke(
        app,
        ["data", "manifests", "verify", "--source", str(source_path), "--split", str(split_path)],
    )
    assert result.exit_code == 0
