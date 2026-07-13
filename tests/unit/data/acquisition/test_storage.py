import pytest

from neuralmarket.data.acquisition.storage import (
    PathSafetyError,
    atomic_write_plan,
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


def test_atomic_write_plan_has_eight_ordered_steps(tmp_path) -> None:
    plan = atomic_write_plan(tmp_path / "final.dbn")
    assert len(plan.steps) == 8
    assert plan.steps[0].startswith("write")
    assert plan.steps[-1] == "update_journal_after_rename"
    assert plan.temp_suffix == ".partial"
