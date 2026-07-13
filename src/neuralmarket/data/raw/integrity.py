"""Content-hash integrity checks for downloaded raw files."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1 << 20  # 1 MiB


def sha256_of_file(path: Path) -> str:
    """Return the hex-encoded SHA-256 digest of a file's contents."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    """Return True iff the file's SHA-256 digest equals `expected_sha256`."""
    return sha256_of_file(path) == expected_sha256
