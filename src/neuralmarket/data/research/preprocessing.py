"""Raw-DBN ts_recv close-window snapshot preprocessing (Strategy B CBBO).

The first real consumer of the deferred timestamp adapter: raw DBN ``ts_recv``
is the authoritative observation time. ``ts_event`` is never a receive-time
fallback and is retained only as a separately labeled event-time field. The
final-ten-minute window is derived from the scheduled XNYS session close, so
DST and early closes come from exchange-calendar data, never hardcoded UTC
times. Missing sessions are never synthesized or substituted.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from neuralmarket.data.acquisition.calendar import quote_window
from neuralmarket.data.acquisition.development_execution import (
    DevelopmentExecutionManifest,
)
from neuralmarket.data.manifests import canonical_dumps
from neuralmarket.data.raw.integrity import sha256_of_file
from neuralmarket.data.research.inventory import ResearchInventory

SNAPSHOT_SCHEMA_VERSION: Literal["research-cbbo-close-snapshot-v1"] = (
    "research-cbbo-close-snapshot-v1"
)

_BID_COL = "bid_px_00"
_ASK_COL = "ask_px_00"
_BID_SIZE_COL = "bid_sz_00"
_ASK_SIZE_COL = "ask_sz_00"
_OBSERVATION_COL = "ts_recv"
_EVENT_COL = "ts_event"


class MissingResearchSourceError(ValueError):
    """A required research input is unavailable and must not be synthesized."""


class CbboCloseSnapshotSummary(BaseModel):
    """Deterministic per-session snapshot provenance and accounting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["research-cbbo-close-snapshot-v1"] = SNAPSHOT_SCHEMA_VERSION
    session_date: str
    split: Literal["training", "validation"]
    parent_request_id: str
    parent_request_hash: str
    execution_request_id: str
    execution_request_hash: str
    raw_dbn_sha256: str
    window_start: str
    window_end: str
    scheduled_close: str
    record_count_in_window: int
    earliest_ts_recv: str
    latest_ts_recv: str
    snapshot_row_count: int
    crossed_rejected: int
    locked_retained: int
    missing_side_rejected: int
    plan_hash: str
    inventory_hash: str
    source_head: str
    parquet_sha256: str


def require_ts_recv(frame: pd.DataFrame) -> pd.DataFrame:
    """Require a valid, non-NaT, timezone-aware ts_recv column.

    ts_event is never a receive-time fallback: a frame whose observation
    column is missing or malformed fails closed.
    """
    if _OBSERVATION_COL not in frame.columns:
        raise MissingResearchSourceError(
            "raw DBN lacks a ts_recv column; ts_event is not a receive-time fallback"
        )
    try:
        converted = pd.to_datetime(frame[_OBSERVATION_COL], utc=True, errors="raise")
    except (TypeError, ValueError) as exc:
        raise MissingResearchSourceError(f"raw DBN ts_recv is malformed: {exc}") from exc
    if converted.isna().any():
        raise MissingResearchSourceError("raw DBN contains NaT ts_recv values")
    frame = frame.copy()
    frame[_OBSERVATION_COL] = converted
    return frame


def load_cbbo_ts_recv_frame(path: Path, expected_sha256: str) -> pd.DataFrame:
    """Load a validated raw CBBO DBN with ts_recv materialized as a column.

    Fails closed when ts_recv is absent, malformed, or the raw checksum does
    not match. ts_event is present only as an event-time column and is never
    used to derive observation time.
    """
    if not path.is_file():
        raise MissingResearchSourceError(f"raw DBN missing: {path}")
    if sha256_of_file(path) != expected_sha256:
        raise MissingResearchSourceError(f"raw DBN checksum mismatch: {path}")
    import databento

    try:
        store = databento.DBNStore.from_file(path)
        frame = store.to_df()
    except Exception as exc:
        raise MissingResearchSourceError(f"raw DBN could not be decoded: {path}: {exc}") from exc
    if frame.index.name != _OBSERVATION_COL:
        raise MissingResearchSourceError(
            f"raw DBN lacks a ts_recv index (found {frame.index.name!r}); "
            "ts_event is not a receive-time fallback"
        )
    return require_ts_recv(frame.reset_index())


def select_final_quotes(
    frame: pd.DataFrame, window_start: datetime, window_end: datetime
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Select the deterministic final valid quote per instrument in the window.

    Ordering key is ``(ts_recv, original file position)``; the last row per
    instrument wins. Crossed quotes are rejected, missing sides are rejected,
    locked quotes are retained and flagged. ts_event (even NaT) never removes
    a valid observation.
    """
    window_start = window_start.astimezone(UTC)
    window_end = window_end.astimezone(UTC)
    working = frame.copy()
    working["_position"] = np.arange(len(working), dtype=np.int64)
    working = working[
        (working[_OBSERVATION_COL] >= window_start) & (working[_OBSERVATION_COL] < window_end)
    ]
    in_window = len(working)
    bid = working[_BID_COL]
    ask = working[_ASK_COL]
    missing_side = (bid <= 0) | (ask <= 0) | bid.isna() | ask.isna()
    crossed = bid > ask
    locked = bid == ask
    valid = working[~missing_side & ~crossed].copy()
    valid["locked"] = locked[valid.index].astype(bool)
    counts = {
        "record_count_in_window": int(in_window),
        "crossed_rejected": int(crossed.sum()),
        "missing_side_rejected": int(missing_side.sum()),
        "locked_retained": int(locked[valid.index].sum()),
    }
    if valid.empty:
        raise MissingResearchSourceError(
            "close window contains no valid quote records; snapshot cannot be synthesized"
        )
    ordered = valid.sort_values([_OBSERVATION_COL, "_position"], kind="stable").drop_duplicates(
        "instrument_id", keep="last"
    )
    ordered = ordered.sort_values("instrument_id", kind="stable")
    output = ordered[
        [
            "instrument_id",
            "symbol",
            _OBSERVATION_COL,
            _EVENT_COL,
            "rtype",
            "publisher_id",
            _BID_COL,
            _ASK_COL,
            _BID_SIZE_COL,
            _ASK_SIZE_COL,
            "flags",
            "locked",
            "_position",
        ]
    ].rename(
        columns={
            _OBSERVATION_COL: "ts_recv",
            _EVENT_COL: "ts_event",
            _BID_COL: "bid_px",
            _ASK_COL: "ask_px",
            _BID_SIZE_COL: "bid_sz",
            _ASK_SIZE_COL: "ask_sz",
            "_position": "window_position",
        }
    )
    return output.reset_index(drop=True), counts


def _write_snapshot_parquet(rows: pd.DataFrame, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(rows, preserve_index=False)
    with pq.ParquetWriter(output_path, table.schema, version="2.6") as writer:
        writer.write_table(table)
    return sha256_of_file(output_path)


def build_session_snapshot(
    *,
    raw_path: Path,
    expected_sha256: str,
    parent_request_id: str,
    parent_request_hash: str,
    execution_request_id: str,
    execution_request_hash: str,
    session_date: date,
    split: Literal["training", "validation"],
    inventory: ResearchInventory,
    source_head: str,
    output_root: Path,
) -> CbboCloseSnapshotSummary:
    """Build and persist one deterministic per-session close snapshot artifact."""
    window_start, window_end = quote_window("XNYS", session_date)
    frame = load_cbbo_ts_recv_frame(raw_path, expected_sha256)
    rows, counts = select_final_quotes(frame, window_start, window_end)
    earliest = str(rows["ts_recv"].min())
    latest = str(rows["ts_recv"].max())
    partition = output_root / "cbbo_close" / split / f"session_date={session_date.isoformat()}"
    parquet_sha256 = _write_snapshot_parquet(rows, partition / "snapshot.parquet")
    summary = CbboCloseSnapshotSummary(
        session_date=session_date.isoformat(),
        split=split,
        parent_request_id=parent_request_id,
        parent_request_hash=parent_request_hash,
        execution_request_id=execution_request_id,
        execution_request_hash=execution_request_hash,
        raw_dbn_sha256=expected_sha256,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        scheduled_close=window_end.isoformat(),
        record_count_in_window=counts["record_count_in_window"],
        earliest_ts_recv=earliest,
        latest_ts_recv=latest,
        snapshot_row_count=len(rows),
        crossed_rejected=counts["crossed_rejected"],
        locked_retained=counts["locked_retained"],
        missing_side_rejected=counts["missing_side_rejected"],
        plan_hash=inventory.plan_hash,
        inventory_hash=inventory.inventory_hash,
        source_head=source_head,
        parquet_sha256=parquet_sha256,
    )
    (partition / "summary.json").write_text(
        canonical_dumps(summary.model_dump(mode="json", by_alias=True)) + "\n",
        encoding="utf-8",
    )
    return summary


def build_all_cbbo_snapshots(
    *,
    inventory: ResearchInventory,
    manifest: DevelopmentExecutionManifest,
    raw_root: Path,
    output_root: Path,
    source_head: str,
    only_sessions: set[str] | None = None,
) -> list[CbboCloseSnapshotSummary]:
    """Run deterministic snapshot preprocessing over paid CBBO requirements.

    Missing (unavailable/uncertain) CBBO requirements are skipped explicitly
    and reported; no substitution or interpolation occurs.
    """
    execution_by_id = {item.execution_request_id: item for item in manifest.execution_requests}
    summaries: list[CbboCloseSnapshotSummary] = []
    for entry in inventory.requirements:
        if entry.purpose != "strategy_b_closing_quote":
            continue
        if only_sessions is not None and entry.session_date not in only_sessions:
            continue
        if entry.disposition != "quality_validated_paid":
            continue
        assert entry.session_date is not None
        execution = execution_by_id[entry.execution_request_ids[0]]
        raw_path = (
            raw_root
            / "development_strategy_b"
            / entry.expected_split
            / "OPRA.PILLAR"
            / "cbbo-1m"
            / f"session_date={entry.session_date}"
            / f"{entry.execution_request_ids[0]}.dbn"
        )
        summary = build_session_snapshot(
            raw_path=raw_path,
            expected_sha256=entry.raw_sha256s[0],
            parent_request_id=entry.development_request_id,
            parent_request_hash=entry.development_request_hash,
            execution_request_id=entry.execution_request_ids[0],
            execution_request_hash=execution.execution_request_hash,
            session_date=date.fromisoformat(entry.session_date),
            split=entry.expected_split,
            inventory=inventory,
            source_head=source_head,
            output_root=output_root,
        )
        summaries.append(summary)
    return summaries
