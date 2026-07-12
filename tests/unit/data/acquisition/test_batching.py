import hashlib

import pytest

from neuralmarket.data.acquisition.batching import (
    MAX_SYMBOLS_PER_CHUNK,
    build_symbol_chunks,
    reconstruct_symbol_set,
)


@pytest.mark.unit
def test_empty_input_yields_no_chunks() -> None:
    assert build_symbol_chunks([]) == ()


@pytest.mark.unit
def test_dedup_and_sorted_stable_order() -> None:
    chunks = build_symbol_chunks(["B", "A", "A", "C", "B"])
    assert len(chunks) == 1
    assert chunks[0].symbols == ("A", "B", "C")


@pytest.mark.unit
def test_max_symbols_per_chunk_respected() -> None:
    symbols = [f"SYM{i:05d}" for i in range(MAX_SYMBOLS_PER_CHUNK + 1)]
    chunks = build_symbol_chunks(symbols)
    assert len(chunks) == 2
    assert len(chunks[0].symbols) == MAX_SYMBOLS_PER_CHUNK
    assert len(chunks[1].symbols) == 1
    assert all(len(c.symbols) > 0 for c in chunks)


@pytest.mark.unit
def test_chunk_ids_deterministic() -> None:
    symbols = [f"SYM{i:05d}" for i in range(MAX_SYMBOLS_PER_CHUNK + 1)]
    chunks = build_symbol_chunks(symbols)
    assert chunks[0].chunk_id == "chunk-0000"
    assert chunks[1].chunk_id == "chunk-0001"


@pytest.mark.unit
def test_chunk_hash_matches_manual_sha256() -> None:
    chunks = build_symbol_chunks(["B", "A"])
    expected = hashlib.sha256(b"A\nB").hexdigest()
    assert chunks[0].chunk_hash == expected


@pytest.mark.unit
def test_reconstruct_symbol_set_exact_round_trip() -> None:
    symbols = {f"SYM{i:05d}" for i in range(MAX_SYMBOLS_PER_CHUNK + 250)}
    chunks = build_symbol_chunks(symbols)
    assert reconstruct_symbol_set(chunks) == symbols


@pytest.mark.unit
def test_no_empty_chunks_for_nonempty_input() -> None:
    chunks = build_symbol_chunks(["ONE"])
    assert len(chunks) == 1
    assert len(chunks[0].symbols) == 1
