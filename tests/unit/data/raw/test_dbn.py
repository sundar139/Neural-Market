from pathlib import Path
from unittest.mock import Mock

import pytest

from neuralmarket.data.raw.dbn import DbnValidationError, validate_dbn_file
from neuralmarket.data.raw.integrity import sha256_of_file, verify_checksum


def _fake_store(request, **overrides):
    fields = {
        "dataset": request.dataset,
        "schema": request.schema_name,
        "symbols": list(request.symbols),
        "start": request.start,
        "end": request.end_exclusive,
    }
    fields.update(overrides)
    return Mock(**fields)


def test_sha256_of_file_matches_known_value(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"hello")
    digest = sha256_of_file(file_path)
    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_verify_checksum_true_and_false(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"hello")
    digest = sha256_of_file(file_path)
    assert verify_checksum(file_path, digest) is True
    assert verify_checksum(file_path, "0" * 64) is False


def test_validate_dbn_file_missing_file(tmp_path, arcx_request) -> None:
    report = validate_dbn_file(
        tmp_path / "missing.dbn", expected_request=arcx_request, expected_sha256="0" * 64
    )
    assert report.passed is False
    assert report.exists is False


def test_validate_dbn_file_empty_file(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"")
    report = validate_dbn_file(file_path, expected_request=arcx_request, expected_sha256="0" * 64)
    assert report.passed is False
    assert report.exists is True
    assert report.nonempty is False


def test_validate_dbn_file_checksum_mismatch(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    report = validate_dbn_file(file_path, expected_request=arcx_request, expected_sha256="0" * 64)
    assert report.checksum_ok is False
    assert report.passed is False


def test_validate_dbn_file_no_factory_is_unreadable(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    report = validate_dbn_file(file_path, expected_request=arcx_request, expected_sha256=digest)
    assert report.checksum_ok is True
    assert report.opens_ok is False
    assert report.passed is False


def test_validate_dbn_file_factory_raises_is_unreadable(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)

    def _boom(_path: Path) -> None:
        raise OSError("corrupt frame")

    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=_boom,
    )
    assert report.opens_ok is False
    assert report.passed is False


def test_validate_dbn_file_passes_with_matching_fake_store(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    fake_store = _fake_store(arcx_request)
    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=lambda _path: fake_store,
    )
    assert report.passed is True
    assert report.errors == []


def test_validate_dbn_file_dataset_mismatch(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    fake_store = _fake_store(arcx_request, dataset="WRONG.DATASET")
    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=lambda _path: fake_store,
    )
    assert report.dataset_matches is False
    assert report.passed is False


def test_validate_dbn_file_schema_mismatch(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    fake_store = _fake_store(arcx_request, schema="ohlcv-1d")
    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=lambda _path: fake_store,
    )
    assert report.schema_matches is False
    assert report.passed is False


def test_validate_dbn_file_symbol_mismatch(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    fake_store = _fake_store(arcx_request, symbols=["QQQ"])
    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=lambda _path: fake_store,
    )
    assert report.symbols_match is False
    assert report.passed is False


def test_validate_dbn_file_window_mismatch(tmp_path, arcx_request) -> None:
    from datetime import UTC, datetime

    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    fake_store = _fake_store(arcx_request, end=datetime(2020, 1, 1, tzinfo=UTC))
    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=lambda _path: fake_store,
    )
    assert report.end_matches is False
    assert report.passed is False


def test_validate_dbn_file_implausible_record_count_is_nonfatal(tmp_path, arcx_request) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"data")
    digest = sha256_of_file(file_path)
    fake_store = _fake_store(arcx_request)
    fake_store.to_df = Mock(return_value=[object()] * 10_000)  # wildly over 10x estimate of 10
    report = validate_dbn_file(
        file_path,
        expected_request=arcx_request,
        expected_sha256=digest,
        dbn_store_factory=lambda _path: fake_store,
    )
    assert report.record_count_plausible is False
    assert report.passed is True  # non-fatal: does not block passing


def test_dbn_validation_error_has_code() -> None:
    err = DbnValidationError("missing", "boom")
    assert err.code == "missing"
    with pytest.raises(DbnValidationError):
        raise err
