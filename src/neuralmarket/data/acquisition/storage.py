"""Pilot raw-storage path safety and atomic DBN publication."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from neuralmarket.data.acquisition.requests import AcquisitionRequest

_FORBIDDEN_CHARS = set('<>:"|?*')
_RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


class PathSafetyError(ValueError):
    """Raised when a logical raw-storage path fails a safety check."""


def validate_logical_path(logical_path: str, seen: set[str] | None = None) -> None:
    """Raise :class:`PathSafetyError` if ``logical_path`` is unsafe.

    Rejects absolute paths (POSIX or Windows-style, including drive
    letters), ``..`` traversal segments, ``~`` home-escape segments,
    Windows-forbidden filename characters, Windows reserved device names
    (case-insensitively, ignoring any extension), and -- if ``seen`` is
    passed -- a case-insensitive collision with an already-seen path.
    """
    if not logical_path:
        raise PathSafetyError("logical path must not be empty")

    normalized = logical_path.replace("\\", "/")

    if PurePosixPath(normalized).is_absolute() or PureWindowsPath(normalized).is_absolute():
        raise PathSafetyError(f"logical path must be relative: {logical_path!r}")

    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        raise PathSafetyError(f"logical path contains a traversal segment: {logical_path!r}")
    if "~" in parts:
        raise PathSafetyError(f"logical path contains a home-escape segment: {logical_path!r}")

    for part in parts:
        if any(char in _FORBIDDEN_CHARS for char in part):
            raise PathSafetyError(f"logical path segment has forbidden characters: {part!r}")
        stem = part.split(".", 1)[0].upper()
        if stem in _RESERVED_NAMES:
            raise PathSafetyError(f"logical path segment is a reserved device name: {part!r}")

    if seen is not None and normalized.lower() in seen:
        raise PathSafetyError(f"logical path collides case-insensitively: {logical_path!r}")


def logical_raw_path(request: AcquisitionRequest) -> str:
    """Return the pilot's deterministic raw-storage path for ``request``.

    Session-scoped requests use ``session_date=YYYY-MM-DD``; range requests
    (``session_date is None``) use ``start_date=.../end_date=...`` derived
    from the request's UTC window.
    """
    if request.session_date is not None:
        date_segment = f"session_date={request.session_date.isoformat()}"
    else:
        start_date = request.start.date().isoformat()
        end_date = request.end_exclusive.date().isoformat()
        date_segment = f"start_date={start_date}/end_date={end_date}"

    logical_path = (
        f"data/raw/databento/pilot_january_2019/{request.dataset}/{request.schema_name}/"
        f"{date_segment}/{request.request_id}.dbn"
    )
    validate_logical_path(logical_path)
    return logical_path


def resolve_under_data_root(logical_path: str, data_root: Path) -> Path:
    """Join ``logical_path`` onto ``data_root`` and confirm it stays inside it.

    Validates the literal path first, then re-checks the *resolved*
    (symlink/``..``-collapsed) path is still under the resolved
    ``data_root`` -- defense in depth beyond the string-level check.
    """
    validate_logical_path(logical_path)

    root_resolved = data_root.resolve()
    candidate = (data_root / logical_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise PathSafetyError(
            f"resolved path escapes data_root: {candidate} not under {root_resolved}"
        ) from exc
    return candidate


@dataclass(frozen=True)
class AtomicWritePlan:
    """Design-only description of the pilot's atomic raw-file write sequence."""

    final_path: Path
    temp_path: Path
    temp_suffix: str
    steps: tuple[str, ...]


def atomic_write_plan(final_path: Path) -> AtomicWritePlan:
    """Return the 8-step atomic-write plan for ``final_path``.

    Design only: no file is created, opened, or renamed here.
    """
    temp_suffix = ".partial"
    temp_path = final_path.with_name(final_path.name + temp_suffix)
    steps = (
        "write_response_to_temp_file",
        "flush_temp_file",
        "fsync_temp_file",
        "compute_checksum_of_temp_file",
        "close_temp_file",
        "atomic_rename_temp_to_final",
        "fsync_parent_directory",
        "update_journal_after_rename",
    )
    return AtomicWritePlan(
        final_path=final_path,
        temp_path=temp_path,
        temp_suffix=temp_suffix,
        steps=steps,
    )


@dataclass(frozen=True)
class RawStorageResult:
    """Verified identity and locations of one atomically stored raw response."""

    path: Path
    sidecar_path: Path
    sha256: str
    byte_count: int


def _fsync_parent(path: Path) -> None:
    """Best-effort directory fsync after publication; unsupported on Windows."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _atomic_publish(source: Path, destination: Path) -> None:
    """Atomically publish a new file without replacing an existing artifact."""
    # os.rename fails if the destination appeared after the preflight check on
    # Windows, preserving the no-overwrite invariant.
    os.rename(source, destination)


def atomic_store_raw(
    *,
    request: AcquisitionRequest,
    data_root: Path,
    chunks: Iterable[bytes],
    validator: Callable[[Path, str], bool],
) -> RawStorageResult:
    """Write, fsync, hash, validate, and atomically publish one raw DBN response."""
    logical_path = request.logical_output_path or logical_raw_path(request)
    final_path = resolve_under_data_root(logical_path, data_root)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = final_path.with_name(final_path.name + ".partial")
    sidecar_path = final_path.with_suffix(final_path.suffix + ".json")
    sidecar_partial = sidecar_path.with_name(sidecar_path.name + ".partial")
    existing = [
        path for path in (final_path, partial_path, sidecar_path, sidecar_partial) if path.exists()
    ]
    if existing:
        raise FileExistsError(f"refusing to overwrite raw artifact: {existing[0]}")
    digest = hashlib.sha256()
    byte_count = 0
    try:
        with partial_path.open("xb") as handle:
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise TypeError("raw response chunks must be bytes")
                handle.write(chunk)
                digest.update(chunk)
                byte_count += len(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        checksum = digest.hexdigest()
        if byte_count == 0 or not validator(partial_path, checksum):
            raise ValueError("raw DBN validation failed before atomic publication")
        sidecar = {
            "request_id": request.request_id,
            "request_hash": request.request_hash,
            "logical_path": logical_path,
            "sha256": checksum,
            "byte_count": byte_count,
            "stored_at": datetime.now(UTC).isoformat(),
        }
        with sidecar_partial.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(sidecar, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            _atomic_publish(partial_path, final_path)
        except Exception:
            raise
        try:
            _atomic_publish(sidecar_partial, sidecar_path)
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        partial_path.unlink(missing_ok=True)
        sidecar_partial.unlink(missing_ok=True)
        _fsync_parent(final_path.parent)
        return RawStorageResult(final_path, sidecar_path, checksum, byte_count)
    finally:
        partial_path.unlink(missing_ok=True)
        sidecar_partial.unlink(missing_ok=True)
