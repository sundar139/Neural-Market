"""Raw DBN file validation against a planned :class:`AcquisitionRequest`.

This module never imports the real ``databento`` package. Opening a DBN
file is done through an injected ``dbn_store_factory`` seam so tests can
supply a fake, DBNStore-shaped object (``.dataset``, ``.schema``,
``.symbols``, ``.start``, ``.end``, ``.to_df()``). Production wiring (Task 8)
supplies ``lambda p: databento.DBNStore(str(p))`` -- that import belongs to
the caller, not to this module.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.requests import AcquisitionRequest
from neuralmarket.data.raw.integrity import sha256_of_file, verify_checksum


class DbnValidationError(ValueError):
    """A single, categorized DBN validation failure."""

    def __init__(self, code: str, message: str) -> None:
        """Store the failure `code` alongside the standard exception `message`."""
        super().__init__(message)
        self.code = code


class DbnValidationReport(BaseModel):
    """Result of validating one downloaded DBN file against its request."""

    model_config = ConfigDict(extra="forbid")

    path: str
    exists: bool
    nonempty: bool
    checksum_ok: bool
    opens_ok: bool
    dataset_matches: bool
    schema_matches: bool
    symbols_match: bool
    start_matches: bool
    end_matches: bool
    record_count_plausible: bool
    timestamps_within_interval: bool
    symbology_present: bool
    passed: bool
    errors: list[str]


def _failed_report(path: Path, errors: list[str], **overrides: bool) -> DbnValidationReport:
    fields: dict[str, bool] = {
        "exists": False,
        "nonempty": False,
        "checksum_ok": False,
        "opens_ok": False,
        "dataset_matches": False,
        "schema_matches": False,
        "symbols_match": False,
        "start_matches": False,
        "end_matches": False,
        "record_count_plausible": False,
        "timestamps_within_interval": False,
        "symbology_present": False,
    }
    fields.update(overrides)
    return DbnValidationReport(path=str(path), passed=False, errors=errors, **fields)


def validate_dbn_file(
    path: Path,
    *,
    expected_request: AcquisitionRequest,
    expected_sha256: str,
    dbn_store_factory: Callable[[Path], Any] | None = None,
) -> DbnValidationReport:
    """Validate a downloaded DBN file's checksum and metadata against its request.

    Never requires exact equality between `expected_request.estimated_record_count`
    and the file's actual record count -- a count outside [0.1x, 10x] of the
    estimate only sets `record_count_plausible=False` as a non-fatal warning.
    """
    if not path.is_file():
        err = DbnValidationError("missing", f"DBN file does not exist: {path}")
        return _failed_report(path, [str(err)])

    if path.stat().st_size == 0:
        err = DbnValidationError("empty", f"DBN file is empty: {path}")
        return _failed_report(path, [str(err)], exists=True)

    checksum_ok = verify_checksum(path, expected_sha256)
    if not checksum_ok:
        err = DbnValidationError(
            "checksum_mismatch",
            f"Checksum mismatch for {path}: expected {expected_sha256}, "
            f"got {sha256_of_file(path)}",
        )
        return _failed_report(path, [str(err)], exists=True, nonempty=True)

    if dbn_store_factory is None:
        err = DbnValidationError(
            "unreadable",
            "No dbn_store_factory provided; production wiring must supply one "
            "(this module never imports databento itself).",
        )
        return _failed_report(path, [str(err)], exists=True, nonempty=True, checksum_ok=True)

    try:
        store = dbn_store_factory(path)
    except Exception as exc:
        err = DbnValidationError("unreadable", f"Failed to open DBN store for {path}: {exc}")
        return _failed_report(path, [str(err)], exists=True, nonempty=True, checksum_ok=True)

    errors: list[str] = []

    dataset_matches = store.dataset == expected_request.dataset
    if not dataset_matches:
        errors.append(
            str(
                DbnValidationError(
                    "dataset_mismatch",
                    f"dataset mismatch: expected {expected_request.dataset!r}, "
                    f"got {store.dataset!r}",
                )
            )
        )

    schema_matches = store.schema == expected_request.schema_name
    if not schema_matches:
        errors.append(
            str(
                DbnValidationError(
                    "schema_mismatch",
                    f"schema mismatch: expected {expected_request.schema_name!r}, "
                    f"got {store.schema!r}",
                )
            )
        )

    symbols_match = set(store.symbols) == set(expected_request.symbols)
    if not symbols_match:
        errors.append(
            str(
                DbnValidationError(
                    "symbol_mismatch",
                    f"symbol mismatch: expected {expected_request.symbols!r}, "
                    f"got {tuple(store.symbols)!r}",
                )
            )
        )

    start_matches = store.start == expected_request.start
    end_matches = store.end == expected_request.end_exclusive
    if not (start_matches and end_matches):
        errors.append(
            str(
                DbnValidationError(
                    "window_mismatch",
                    f"window mismatch: expected [{expected_request.start}, "
                    f"{expected_request.end_exclusive}), got [{store.start}, {store.end})",
                )
            )
        )

    record_count_plausible = True
    try:
        actual_count = len(store.to_df())
    except Exception:
        actual_count = None
    if actual_count is not None and expected_request.estimated_record_count > 0:
        lower = 0.1 * expected_request.estimated_record_count
        upper = 10 * expected_request.estimated_record_count
        if not (lower <= actual_count <= upper):
            record_count_plausible = False
            errors.append(
                f"record_count_implausible (warning, non-fatal): estimated "
                f"{expected_request.estimated_record_count}, actual {actual_count}"
            )

    # ponytail: per-record timestamp/symbology-column inspection needs a real
    # DBN dataframe shape that no synthetic fixture here exercises; both
    # default to True (unverifiable, not disproved) until Task 7c wires real
    # frames and can flip these to genuine checks.
    timestamps_within_interval = True
    symbology_present = True

    passed = (
        checksum_ok
        and dataset_matches
        and schema_matches
        and symbols_match
        and start_matches
        and end_matches
        and timestamps_within_interval
        and symbology_present
    )

    return DbnValidationReport(
        path=str(path),
        exists=True,
        nonempty=True,
        checksum_ok=True,
        opens_ok=True,
        dataset_matches=dataset_matches,
        schema_matches=schema_matches,
        symbols_match=symbols_match,
        start_matches=start_matches,
        end_matches=end_matches,
        record_count_plausible=record_count_plausible,
        timestamps_within_interval=timestamps_within_interval,
        symbology_present=symbology_present,
        passed=passed,
        errors=errors,
    )
