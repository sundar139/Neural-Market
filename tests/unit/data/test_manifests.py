from datetime import date
from pathlib import Path

import pytest

from neuralmarket.data.calendar import BoundaryExclusion, SplitResult
from neuralmarket.data.configuration import load_data_config
from neuralmarket.data.errors import ManifestValidationError
from neuralmarket.data.manifests import (
    DateRange,
    build_source_manifest,
    build_split_manifest,
    canonical_dumps,
    canonical_hash,
    canonical_summary_hash,
    parse_source_manifest,
    verify_manifest_hash,
    verify_manifests,
)


def _selector_summary(**overrides: object) -> dict[str, object]:
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
    summary.update(overrides)
    summary["canonical_summary_hash"] = canonical_summary_hash(summary)
    return summary


_CONFIG = Path("configs/data/spy_daily_databento.yaml")


@pytest.fixture(scope="module")
def config():  # type: ignore[no-untyped-def]
    return load_data_config(_CONFIG)


def _split_result() -> SplitResult:
    excl = BoundaryExclusion(date(2021, 1, 1), date(2021, 4, 1), 100, "abc")
    return SplitResult(
        training_start=date(2018, 1, 2),
        training_end=date(2021, 12, 31),
        validation_start=date(2022, 5, 26),
        validation_end=date(2023, 6, 30),
        test_start=date(2023, 11, 22),
        test_end=date(2025, 12, 31),
        training_sessions=1008,
        validation_sessions=275,
        test_sessions=528,
        training_hash="t",
        validation_hash="v",
        test_hash="x",
        calendar_hash="c",
        boundary_exclusions=(excl, excl),
    )


_FULL = DateRange(start_date=date(2013, 4, 1), end_date=date(2026, 6, 30))


_PUBLISHER = {"publisher_id": 2, "venue": "ARCX", "description": "NYSE Arca Pillar"}


def _build_source(  # type: ignore[no-untyped-def]
    config,
    *,
    underlying=None,
    options=None,
    options_validation_method="chunked_symbology_resolution",
    options_selector_summary=None,
):
    return build_source_manifest(
        config,
        underlying_ranges=underlying
        or {
            "ARCX.PILLAR/ohlcv-1d": _FULL,
            "ARCX.PILLAR/bbo-1m": _FULL,
            "ARCX.PILLAR/definition": _FULL,
        },
        options_ranges=options or {"OPRA.PILLAR/definition": _FULL, "OPRA.PILLAR/cbbo-1m": _FULL},
        publisher=_PUBLISHER,
        optional_schemas={"statistics": "available"},
        underlying_symbol_resolution="resolved",
        options_symbol_resolution="resolved",
        options_validation_method=options_validation_method,
        options_selector_summary=options_selector_summary or _selector_summary(),
        qualification_status="qualified",
        qualification_timestamp="2020-01-01T00:00:00+00:00",
        config_hash="h",
        git_commit="c",
        generated_at="2020-01-01T00:00:00+00:00",
    )


@pytest.mark.unit
def test_canonical_dumps_sorted() -> None:
    assert canonical_dumps({"b": 1, "a": 2}) == '{"a":2,"b":1}'


@pytest.mark.unit
def test_source_manifest_carries_selector_summary(config) -> None:  # type: ignore[no-untyped-def]
    manifest = parse_source_manifest(_build_source(config))
    summary = manifest.options.selector_summary
    assert manifest.options.validation_method == "chunked_symbology_resolution"
    assert summary.chunk_count == 92
    assert summary.session_gap_count == 0
    assert summary.canonical_summary_hash


@pytest.mark.unit
def test_source_manifest_rejects_fallback_validation_method(config) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ManifestValidationError):
        parse_source_manifest(
            _build_source(
                config,
                options_validation_method="metadata_parent_selector_preflight",
                options_selector_summary=_selector_summary(
                    validation_method="metadata_parent_selector_preflight"
                ),
            )
        )


@pytest.mark.unit
def test_source_manifest_rejects_uncovered_sessions(config) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ManifestValidationError):
        parse_source_manifest(
            _build_source(
                config,
                options_selector_summary=_selector_summary(session_gap_count=3),
            )
        )


@pytest.mark.unit
def test_source_manifest_rejects_failed_chunks(config) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ManifestValidationError):
        parse_source_manifest(
            _build_source(
                config,
                options_selector_summary=_selector_summary(
                    successful_chunk_count=90, failed_chunk_count=2
                ),
            )
        )


@pytest.mark.unit
def test_hash_excludes_generated_at(config) -> None:  # type: ignore[no-untyped-def]
    a = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c1",
        generated_at="2020-01-01T00:00:00+00:00",
    )
    b = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c1",
        generated_at="2099-12-31T00:00:00+00:00",
    )
    assert a["manifest_hash"] == b["manifest_hash"]


@pytest.mark.unit
def test_split_manifest_hash_valid(config) -> None:  # type: ignore[no-untyped-def]
    payload = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c",
        generated_at="2020-01-01T00:00:00+00:00",
    )
    verify_manifest_hash(payload)
    assert payload["final_test_access_status"] == "sealed"


@pytest.mark.unit
def test_tamper_detected(config) -> None:  # type: ignore[no-untyped-def]
    payload = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c",
        generated_at="2020-01-01T00:00:00+00:00",
    )
    payload["training_start"] = "2010-01-01"
    with pytest.raises(ManifestValidationError, match="hash mismatch"):
        verify_manifest_hash(payload)


@pytest.mark.unit
def test_verify_manifests_success(config) -> None:  # type: ignore[no-untyped-def]
    split = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c",
        generated_at="2020-01-01T00:00:00+00:00",
    )
    source = _build_source(config)
    verify_manifests(source, split)


@pytest.mark.unit
def test_source_manifest_fields_and_validation(config) -> None:  # type: ignore[no-untyped-def]
    m = _build_source(config)
    assert m["underlying"]["source_class"] == "primary_listing_venue"
    assert m["underlying"]["quote_role"] == "venue_liquidity_proxy"
    assert m["underlying"]["venue_specific"] is True
    assert m["underlying"]["consolidated_equities"] is False
    assert m["underlying"]["official_nbbo"] is False
    assert m["underlying"]["publisher"]["venue"] == "ARCX"
    assert "arcx_vs_equs_mini_development_overlap" in m["underlying"]["required_future_validations"]
    assert m["transaction_cost_source_policy"]["primary"] == "explicit_modeled_costs"
    parse_source_manifest(m)


@pytest.mark.unit
def test_source_manifest_rejects_nbbo_claim(config) -> None:  # type: ignore[no-untyped-def]
    m = _build_source(config)
    m["underlying"]["official_nbbo"] = True
    with pytest.raises(ManifestValidationError):
        parse_source_manifest(m)


@pytest.mark.unit
def test_source_manifest_requires_cost_policy(config) -> None:  # type: ignore[no-untyped-def]
    m = _build_source(config)
    m["transaction_cost_source_policy"] = {"arcx_spread_role": "auxiliary"}
    with pytest.raises(ManifestValidationError):
        parse_source_manifest(m)


@pytest.mark.unit
def test_verify_manifests_coverage_gap(config) -> None:  # type: ignore[no-untyped-def]
    split = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c",
        generated_at="2020-01-01T00:00:00+00:00",
    )
    narrow = {
        "EQUS.MINI/ohlcv-1d": DateRange(start_date=date(2020, 1, 1), end_date=date(2021, 1, 1))
    }
    source = _build_source(config, underlying=narrow)
    with pytest.raises(ManifestValidationError, match="does not cover"):
        verify_manifests(source, split)


@pytest.mark.unit
def test_verify_manifests_unsealed_rejected(config) -> None:  # type: ignore[no-untyped-def]
    split = build_split_manifest(
        config,
        _split_result(),
        config_hash="h",
        git_commit="c",
        generated_at="2020-01-01T00:00:00+00:00",
    )
    split["final_test_access_status"] = "open"
    split["manifest_hash"] = canonical_hash(split)
    source = _build_source(config)
    with pytest.raises(ManifestValidationError, match="sealed"):
        verify_manifests(source, split)
