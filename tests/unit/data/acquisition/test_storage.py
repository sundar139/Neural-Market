from datetime import UTC, date, datetime

import pytest

from neuralmarket.data.acquisition.requests import AcquisitionRequest
from neuralmarket.data.acquisition.storage import (
    PathSafetyError,
    atomic_write_plan,
    logical_raw_path,
    resolve_under_data_root,
    validate_logical_path,
)


@pytest.mark.parametrize(
    "bad_path",
    [
        "C:/absolute/path.dbn",
        "../escape/path.dbn",
        "data/raw/../../etc/passwd",
        "data/raw/CON.dbn",
        "data/raw/file<name>.dbn",
        "~/escape.dbn",
    ],
)
def test_rejects_unsafe_paths(bad_path: str) -> None:
    with pytest.raises(PathSafetyError):
        validate_logical_path(bad_path)


def test_accepts_safe_relative_path() -> None:
    validate_logical_path("data/raw/databento/pilot_january_2019/ARCX.PILLAR/definition/req-1.dbn")


def test_rejects_case_insensitive_collision() -> None:
    seen = {"data/raw/x.dbn"}
    with pytest.raises(PathSafetyError):
        validate_logical_path("data/raw/X.DBN", seen=seen)


def test_resolve_under_data_root_blocks_escape(tmp_path) -> None:
    with pytest.raises(PathSafetyError):
        resolve_under_data_root("../outside.dbn", tmp_path)


def test_resolve_under_data_root_blocks_symlink_escape(tmp_path) -> None:
    # Layer (a) -- validate_logical_path -- only rejects literal ".."
    # segments. A symlink inside data_root that points outside it contains
    # no ".." in the logical path string at all, so this exercises layer
    # (b): the resolve()-based check must independently catch the escape.
    outside = tmp_path / "outside"
    outside.mkdir()
    data_root = tmp_path / "root"
    data_root.mkdir()
    link = data_root / "link_dir"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable in this environment: {exc}")

    with pytest.raises(PathSafetyError):
        resolve_under_data_root("link_dir/escaped.dbn", data_root)


def test_logical_raw_path_uses_session_date_segment() -> None:
    request = AcquisitionRequest(
        request_id="abc123",
        wave="opra_closing_quotes",
        dataset="OPRA.PILLAR",
        schema="cmbp-1",
        symbols=("SPY",),
        stype_in="parent",
        stype_out="instrument_id",
        start=datetime(2019, 1, 2, 20, 45, tzinfo=UTC),
        end_exclusive=datetime(2019, 1, 2, 21, 0, tzinfo=UTC),
        encoding="dbn",
        compression="zstd",
        expected_split="training",
        session_date=date(2019, 1, 2),
        calendar="XNYS",
        estimated_record_count=0,
        estimated_billable_size=0,
        estimated_cost="0.00",
        currency="USD",
        request_hash="deadbeef",
    )

    path = logical_raw_path(request)

    assert path == (
        "data/raw/databento/pilot_january_2019/OPRA.PILLAR/cmbp-1/"
        "session_date=2019-01-02/abc123.dbn"
    )
    # logical_raw_path calls validate_logical_path internally; if the path
    # were unsafe, the call above would already have raised.
    validate_logical_path(path)


def test_atomic_write_plan_has_eight_ordered_steps(tmp_path) -> None:
    plan = atomic_write_plan(tmp_path / "final.dbn")
    assert len(plan.steps) == 8
    assert plan.steps[0].startswith("write")
    assert plan.steps[-1] == "update_journal_after_rename"
    assert plan.temp_suffix == ".partial"
