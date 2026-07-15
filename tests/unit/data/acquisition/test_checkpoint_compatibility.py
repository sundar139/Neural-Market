"""Tests for operational config compatibility and stale-checkpoint resume safety."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from neuralmarket.data.acquisition.checkpoint_compatibility import (
    OPERATIONALLY_COMPATIBLE_PRIOR_CONFIG_HASHES,
    diff_config_compatibility,
    is_pilot_config_hash_compatible,
    is_valid_sha256,
)
from neuralmarket.data.acquisition.metadata_runner import (
    MetadataCheckpoint,
    MetadataEndpointResult,
    endpoint_response_hash,
    load_checkpoint,
    write_checkpoint,
)

pytestmark = pytest.mark.unit

_PRIOR_HASH = next(iter(OPERATIONALLY_COMPATIBLE_PRIOR_CONFIG_HASHES))


# --- sha256 hex validation ---------------------------------------------------


@pytest.mark.parametrize(
    ("value", "ok"),
    [
        ("a" * 64, True),
        ("0123456789abcdef" * 4, True),
        ("A" * 64, False),  # uppercase
        ("a" * 63, False),  # short
        ("a" * 65, False),  # long
        ("0x" + "a" * 62, False),  # prefixed
        ("g" * 64, False),  # non-hex
        ("", False),
    ],
)
def test_is_valid_sha256(value: str, ok: bool) -> None:
    assert is_valid_sha256(value) is ok


# --- config compatibility diff -----------------------------------------------


def _config(deadline: int) -> dict:
    return {
        "options": {"dataset": "OPRA.PILLAR", "quote_schema": "cbbo-1m"},
        "pilot_execution": {"maximum_spend_usd": "5.00"},
        "metadata_execution": {
            "hard_request_timeout_seconds": 120,
            "maximum_timeout_attempts": 2,
            "checkpoint_max_age_minutes": 30,
            "total_run_deadline_seconds": deadline,
        },
    }


def test_operational_only_difference_is_compatible() -> None:
    report = diff_config_compatibility(_config(540), _config(7200))
    assert report.compatible
    assert report.differing_fields == ("metadata_execution.total_run_deadline_seconds",)
    assert report.disallowed_fields == ()


def test_identical_config_is_compatible() -> None:
    assert diff_config_compatibility(_config(7200), _config(7200)).compatible


def test_scientific_difference_is_incompatible() -> None:
    bound = _config(540)
    current = _config(7200)
    current["options"]["quote_schema"] = "cbbo-1s"
    report = diff_config_compatibility(bound, current)
    assert not report.compatible
    assert "options.quote_schema" in report.disallowed_fields


def test_budget_difference_is_incompatible() -> None:
    bound = _config(540)
    current = _config(540)
    current["pilot_execution"]["maximum_spend_usd"] = "6.00"
    report = diff_config_compatibility(bound, current)
    assert not report.compatible
    assert "pilot_execution.maximum_spend_usd" in report.disallowed_fields


# --- pilot config hash compatibility -----------------------------------------


def test_hash_compatibility_exact_prior_and_unknown() -> None:
    assert is_pilot_config_hash_compatible("abc", "abc")  # exact
    assert is_pilot_config_hash_compatible(_PRIOR_HASH, "different-current")  # prior allowlist
    assert not is_pilot_config_hash_compatible("f" * 64, "e" * 64)  # unknown


# --- stale-resume preserves completed progress -------------------------------


def _checkpoint(updated: datetime) -> MetadataCheckpoint:
    cp = MetadataCheckpoint(
        created_at=(updated - timedelta(hours=7)).isoformat(),
        updated_at=updated.isoformat(),
        source_manifest_hash="s" * 64,
        split_manifest_hash="v" * 64,
        acquisition_policy_hash="a" * 64,
        pilot_config_hash="c" * 64,
        calendar_version="1",
        databento_client_version="0.81.0",
        ordered_request_specification_hashes=["r" * 64],
        pending_request_ids=["pending-1"],
    )
    cp.endpoint_results["done-1"] = {
        "record-count": MetadataEndpointResult(
            value=10,
            completed_at=updated.isoformat(),
            response_hash=endpoint_response_hash("record-count", 10),
        ),
        "cost": MetadataEndpointResult(
            value="0.01",
            completed_at=updated.isoformat(),
            response_hash=endpoint_response_hash("cost", "0.01"),
            cost_source="provider_response",
        ),
    }
    cp.completed_estimates["done-1"] = {
        "dataset": "OPRA.PILLAR",
        "schema": "cbbo-1m",
        "symbol": "SPY.OPT",
        "stype_in": "parent",
        "window_start": "2019-01-02T00:00:00+00:00",
        "window_end": "2019-01-03T00:00:00+00:00",
        "record_count": 10,
        "billable_size_bytes": 100,
        "cost_usd": "0.01",
        "retries": 0,
    }
    return cp


def _expected(cp: MetadataCheckpoint) -> dict[str, object]:
    return {
        key: getattr(cp, key)
        for key in (
            "source_manifest_hash",
            "split_manifest_hash",
            "acquisition_policy_hash",
            "pilot_config_hash",
            "calendar_version",
            "databento_client_version",
            "estimator_version",
            "ordered_request_specification_hashes",
        )
    }


def test_stale_checkpoint_rejected_at_normal_age_but_loads_with_age_bypass(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    cp = _checkpoint(datetime.now(UTC) - timedelta(hours=7))
    write_checkpoint(path, cp)
    expected = _expected(cp)

    # Normal freshness window: stale checkpoint rejected.
    with pytest.raises(ValueError, match="expired"):
        load_checkpoint(path, expected=expected, maximum_age_minutes=30)

    # Age bypass (as used by hash-authorized stale resume): loads, progress intact.
    loaded = load_checkpoint(path, expected=expected, maximum_age_minutes=10**9)
    assert set(loaded.endpoint_results["done-1"]) == {"record-count", "cost"}
    assert loaded.completed_estimates["done-1"]["cost_usd"] == "0.01"
    assert loaded.pending_request_ids == ["pending-1"]
    # The age bypass did not weaken other integrity checks: a tampered plan hash
    # is still rejected.
    with pytest.raises(ValueError, match="mismatch"):
        load_checkpoint(
            path,
            expected={**expected, "source_manifest_hash": "z" * 64},
            maximum_age_minutes=10**9,
        )


# --- one-invocation deadline feasibility (deterministic accounting) ----------


def test_new_deadline_covers_worst_case_and_old_deadline_does_not() -> None:
    # ponytail: deterministic sizing check, not a real-clock CLI harness. Worst case
    # is the frozen plan's 21 OPRA cbbo-1m cost endpoints each exhausting bounded
    # timeouts before deriving, plus their record-count/billable-size endpoints.
    hard_timeout = 120
    attempts = 2
    pending_cost_requests = 21
    worst_case_cost_seconds = pending_cost_requests * hard_timeout * attempts  # 5040
    # A bounded margin for record-count/billable-size, child startup, persistence.
    other_overhead = pending_cost_requests * 60  # generous per-request overhead
    required = worst_case_cost_seconds + other_overhead  # 6300
    assert worst_case_cost_seconds == 5040
    assert required <= 7200  # new deadline is sufficient
    assert required > 540  # the old deadline could not complete one invocation
