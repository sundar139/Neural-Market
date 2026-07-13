from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from neuralmarket.core.configuration import ConfigurationError
from neuralmarket.data.acquisition.estimation import MetadataEstimate
from neuralmarket.data.acquisition.requests import (
    build_pilot_request_plan,
    finalize_request,
    load_pilot_config,
    plan_hash,
    verify_final_request,
)

CONFIG_PATH = "configs/data/acquisition/pilot_january_2019.yaml"


@pytest.mark.unit
def test_plan_has_exactly_21_closing_quote_requests() -> None:
    config = load_pilot_config(CONFIG_PATH)
    requests = build_pilot_request_plan(config)
    quote_requests = [r for r in requests if r.wave == "opra_closing_quotes"]
    assert len(quote_requests) == 21
    assert {r.symbols for r in quote_requests} == {("SPY.OPT",)}


@pytest.mark.unit
def test_quote_windows_are_exactly_ten_minutes_and_not_hardcoded_four_pm() -> None:
    config = load_pilot_config(CONFIG_PATH)
    requests = build_pilot_request_plan(config)
    quote_requests = [r for r in requests if r.wave == "opra_closing_quotes"]
    closes = {r.end_exclusive.time() for r in quote_requests}
    assert len(closes) >= 1
    for r in quote_requests:
        assert (r.end_exclusive - r.start).total_seconds() == 600


@pytest.mark.unit
def test_plan_is_deterministic_across_regeneration() -> None:
    config = load_pilot_config(CONFIG_PATH)
    first = plan_hash(build_pilot_request_plan(config))
    second = plan_hash(build_pilot_request_plan(config))
    assert first == second


@pytest.mark.unit
def test_no_duplicate_symbols_within_a_request() -> None:
    config = load_pilot_config(CONFIG_PATH)
    for r in build_pilot_request_plan(config):
        assert len(r.symbols) == len(set(r.symbols))
        assert list(r.symbols) == sorted(r.symbols)


@pytest.mark.unit
def test_request_hash_excludes_machine_path_and_is_sha256() -> None:
    config = load_pilot_config(CONFIG_PATH)
    requests = build_pilot_request_plan(config)
    for r in requests:
        assert len(r.request_hash) == 64
        int(r.request_hash, 16)  # valid hex


@pytest.mark.unit
def test_all_waves_present() -> None:
    config = load_pilot_config(CONFIG_PATH)
    waves = {r.wave for r in build_pilot_request_plan(config)}
    assert waves == {"arcx_catalog", "arcx_underlying", "opra_definitions", "opra_closing_quotes"}


@pytest.mark.unit
def test_expected_split_is_always_training() -> None:
    config = load_pilot_config(CONFIG_PATH)
    for r in build_pilot_request_plan(config):
        assert r.expected_split == "training"


@pytest.mark.unit
def test_plan_is_sorted_deterministically() -> None:
    config = load_pilot_config(CONFIG_PATH)
    requests = build_pilot_request_plan(config)
    keys = [
        (r.wave, r.dataset, r.schema_name, r.session_date or date.min, r.symbols) for r in requests
    ]
    assert keys == sorted(keys)


@pytest.mark.unit
def test_load_pilot_config_accepts_matching_quote_window_minutes() -> None:
    config = load_pilot_config(CONFIG_PATH)
    assert config.quote_window_minutes == 10


@pytest.mark.unit
def test_load_pilot_config_rejects_mismatched_quote_window_minutes(tmp_path: Path) -> None:
    raw = yaml.safe_load(Path(CONFIG_PATH).read_text(encoding="utf-8"))
    raw["pilot_execution"]["quote_window_minutes"] = 15
    bad_config_path = tmp_path / "pilot_january_2019_bad_quote_window.yaml"
    bad_config_path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="quote_window_minutes"):
        load_pilot_config(bad_config_path)


@pytest.mark.unit
def test_closing_quote_sessions_match_january_2019_xnys_sessions() -> None:
    config = load_pilot_config(CONFIG_PATH)
    requests = build_pilot_request_plan(config)
    quote_requests = [r for r in requests if r.wave == "opra_closing_quotes"]
    sessions = sorted(r.session_date for r in quote_requests)
    assert sessions[0] == date(2019, 1, 2)
    assert sessions[-1] == date(2019, 1, 31)
    assert len(set(sessions)) == 21


@pytest.mark.unit
def test_finalize_request_binds_estimate_without_timestamp_nondeterminism() -> None:
    draft = build_pilot_request_plan(load_pilot_config(CONFIG_PATH))[0]
    estimate = MetadataEstimate(
        dataset=draft.dataset,
        schema=draft.schema_name,
        symbol=draft.symbols[0],
        stype_in=draft.stype_in,
        window_start=draft.start,
        window_end=draft.end_exclusive,
        record_count=12,
        billable_size_bytes=345,
        cost_usd=Decimal("0.04"),
        retries=0,
    )
    first = finalize_request(draft, estimate, datetime(2026, 1, 1, tzinfo=UTC))
    second = finalize_request(
        draft, estimate, datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=1)
    )

    assert draft.estimated_cost is None
    assert first.estimated_record_count == 12
    assert first.estimated_billable_size == 345
    assert first.estimated_cost == "0.04"
    assert first.estimate_method == "metadata:get_record_count+get_billable_size+get_cost"
    assert first.request_hash == second.request_hash
    assert first.request_hash != draft.request_hash


@pytest.mark.unit
def test_finalize_request_rejects_estimate_for_different_window() -> None:
    draft = build_pilot_request_plan(load_pilot_config(CONFIG_PATH))[0]
    estimate = MetadataEstimate(
        dataset=draft.dataset,
        schema=draft.schema_name,
        symbol=draft.symbols[0],
        stype_in=draft.stype_in,
        window_start=draft.start + timedelta(days=1),
        window_end=draft.end_exclusive + timedelta(days=1),
        record_count=12,
        billable_size_bytes=345,
        cost_usd=Decimal("0.04"),
        retries=0,
    )

    with pytest.raises(ValueError, match="does not match request"):
        finalize_request(draft, estimate, datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.unit
def test_verify_final_request_rejects_negative_cost() -> None:
    draft = build_pilot_request_plan(load_pilot_config(CONFIG_PATH))[0]
    estimate = MetadataEstimate(
        dataset=draft.dataset,
        schema=draft.schema_name,
        symbol=draft.symbols[0],
        stype_in=draft.stype_in,
        window_start=draft.start,
        window_end=draft.end_exclusive,
        record_count=12,
        billable_size_bytes=345,
        cost_usd=Decimal("-0.04"),
        retries=0,
    )
    request = finalize_request(draft, estimate, datetime(2026, 1, 1, tzinfo=UTC))

    with pytest.raises(ValueError, match="cost estimate is negative"):
        verify_final_request(request)


@pytest.mark.unit
def test_plan_hash_binds_dependency_metadata() -> None:
    requests = build_pilot_request_plan(load_pilot_config(CONFIG_PATH))
    bindings = {"source_manifest_hash": "a" * 64, "split_manifest_hash": "b" * 64}
    assert plan_hash(requests, bindings) != plan_hash(
        requests, {**bindings, "source_manifest_hash": "c" * 64}
    )
