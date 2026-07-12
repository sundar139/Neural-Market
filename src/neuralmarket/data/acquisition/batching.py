"""Deterministic symbol-batching model for future raw-symbol acquisition.

Databento permits at most 2,000 explicit symbols per request. This module only
plans batches from a symbol set; it never resolves, downloads, or previews
actual option symbols.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

MAX_SYMBOLS_PER_CHUNK = 2000


@dataclass(frozen=True)
class SymbolChunk:
    """One deterministic, bounded batch of symbols for a future request."""

    chunk_id: str
    symbols: tuple[str, ...]
    chunk_hash: str


def _chunk_hash(symbols: tuple[str, ...]) -> str:
    payload = "\n".join(symbols)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_symbol_chunks(symbols: Iterable[str]) -> tuple[SymbolChunk, ...]:
    """Split a symbol set into stable, deduplicated, bounded chunks.

    Args:
        symbols: Raw option symbols to batch.

    Returns:
        Chunks in stable sorted-symbol order, each at most
        :data:`MAX_SYMBOLS_PER_CHUNK` symbols, with a deterministic
        ``chunk_id`` and a SHA-256 ``chunk_hash`` over its symbols. Empty
        input yields no chunks.
    """
    deduped_sorted = sorted(set(symbols))
    chunks: list[SymbolChunk] = []
    for index in range(0, len(deduped_sorted), MAX_SYMBOLS_PER_CHUNK):
        batch = tuple(deduped_sorted[index : index + MAX_SYMBOLS_PER_CHUNK])
        chunk_index = index // MAX_SYMBOLS_PER_CHUNK
        chunks.append(
            SymbolChunk(
                chunk_id=f"chunk-{chunk_index:04d}",
                symbols=batch,
                chunk_hash=_chunk_hash(batch),
            )
        )
    return tuple(chunks)


def reconstruct_symbol_set(chunks: Iterable[SymbolChunk]) -> set[str]:
    """Return the union of symbols across a set of chunks."""
    result: set[str] = set()
    for chunk in chunks:
        result.update(chunk.symbols)
    return result
