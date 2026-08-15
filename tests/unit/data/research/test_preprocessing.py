"""Raw ts_recv adapter, close-window construction, and snapshot selection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from neuralmarket.data.acquisition.calendar import quote_window
from neuralmarket.data.research.preprocessing import (
    MissingResearchSourceError,
    load_cbbo_ts_recv_frame,
    select_final_quotes,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[4]

_CBbo_COLUMNS = [
    "ts_event",
    "rtype",
    "publisher_id",
    "instrument_id",
    "side",
    "price",
    "size",
    "flags",
    "bid_px_00",
    "ask_px_00",
    "bid_sz_00",
    "ask_sz_00",
    "bid_pb_00",
    "ask_pb_00",
    "symbol",
]


def _frame(
    rows: list[tuple[datetime, datetime | None, int, float, float]],
) -> pd.DataFrame:
    """Build a synthetic cbbo-1m frame with ts_recv as the index."""
    records = []
    for _ts_recv, ts_event, instrument, bid, ask in rows:
        records.append(
            {
                "ts_event": ts_event,
                "rtype": 193,
                "publisher_id": 30,
                "instrument_id": instrument,
                "side": "N",
                "price": np.nan,
                "size": 0,
                "flags": 0,
                "bid_px_00": bid,
                "ask_px_00": ask,
                "bid_sz_00": 100,
                "ask_sz_00": 100,
                "bid_pb_00": 0,
                "ask_pb_00": 0,
                "symbol": f"SPY {instrument}",
            }
        )
    frame = pd.DataFrame(records, columns=_CBbo_COLUMNS)
    frame.index = pd.DatetimeIndex([ts_recv for ts_recv, *_ in rows], name="ts_recv", tz=UTC)
    return frame.reset_index()


class TestRawTsRecvAdapter:
    def test_real_raw_dbn_loads_with_ts_recv_column(self) -> None:
        from neuralmarket.data.acquisition.journal import RequestJournal

        journal_path = _ROOT / "data/state/development_acquisition_journal.sqlite"
        if not journal_path.is_file():
            pytest.skip("development acquisition journal is not present in this checkout")
        journal = RequestJournal(journal_path)
        cbbo_entries = [
            entry
            for entry in journal.all()
            if entry.state == "quality_validated" and entry.raw_path and "cbbo-1m" in entry.raw_path
        ]
        assert cbbo_entries
        entry = cbbo_entries[0]
        raw_path = Path(entry.raw_path)
        if not raw_path.is_file():
            pytest.skip("development raw CBBO DBN is not present in this checkout")
        frame = load_cbbo_ts_recv_frame(raw_path, str(entry.raw_checksum))
        assert "ts_recv" in frame.columns
        assert str(frame["ts_recv"].dtype) == "datetime64[ns, UTC]"
        assert "ts_event" in frame.columns
        assert not frame["ts_recv"].isna().any()

    def test_checksum_mismatch_fails_before_decode(self) -> None:
        raw = _ROOT / "data/raw/databento/development_strategy_b/training/OPRA.PILLAR"
        files = sorted(raw.rglob("cbbo-1m/*/*.dbn")) if raw.exists() else []
        if not files:
            pytest.skip("development raw CBBO DBN is not present in this checkout")
        with pytest.raises(MissingResearchSourceError, match="checksum mismatch"):
            load_cbbo_ts_recv_frame(files[0], "0" * 64)

    def test_malformed_ts_recv_fails(self) -> None:
        from neuralmarket.data.research.preprocessing import require_ts_recv

        frame = _frame([(datetime(2018, 5, 1, 19, 55, tzinfo=UTC), None, 1, 84.5, 84.6)])
        frame["ts_recv"] = "not-a-timestamp"
        with pytest.raises(MissingResearchSourceError, match="malformed"):
            require_ts_recv(frame)

    def test_nat_ts_recv_fails(self) -> None:
        from neuralmarket.data.research.preprocessing import require_ts_recv

        frame = _frame([(datetime(2018, 5, 1, 19, 55, tzinfo=UTC), None, 1, 84.5, 84.6)])
        frame.loc[0, "ts_recv"] = pd.NaT
        with pytest.raises(MissingResearchSourceError, match="NaT"):
            require_ts_recv(frame)

    def test_missing_ts_recv_column_fails_even_with_ts_event(self) -> None:
        from neuralmarket.data.research.preprocessing import require_ts_recv

        frame = _frame([(datetime(2018, 5, 1, 19, 55, tzinfo=UTC), None, 1, 84.5, 84.6)])
        frame = frame.drop(columns=["ts_recv"])
        assert "ts_event" in frame.columns
        with pytest.raises(MissingResearchSourceError, match="not a receive-time fallback"):
            require_ts_recv(frame)


class TestWindowConstruction:
    def test_regular_edt_close_is_2000_utc(self) -> None:
        start, end = quote_window("XNYS", pd.Timestamp("2018-05-01").date())
        assert (end - start).total_seconds() == 600
        assert end == datetime(2018, 5, 1, 20, 0, tzinfo=UTC)
        assert start == datetime(2018, 5, 1, 19, 50, tzinfo=UTC)

    def test_regular_est_close_is_2100_utc(self) -> None:
        start, end = quote_window("XNYS", pd.Timestamp("2018-12-11").date())
        assert end == datetime(2018, 12, 11, 21, 0, tzinfo=UTC)
        assert start == datetime(2018, 12, 11, 20, 50, tzinfo=UTC)

    def test_early_close_july3_2018_is_1700_utc(self) -> None:
        start, end = quote_window("XNYS", pd.Timestamp("2018-07-03").date())
        assert end == datetime(2018, 7, 3, 17, 0, tzinfo=UTC)
        assert start == datetime(2018, 7, 3, 16, 50, tzinfo=UTC)

    def test_no_hardcoded_close_variants(self) -> None:
        closes = {
            pd.Timestamp(d).date(): quote_window("XNYS", pd.Timestamp(d).date())[1]
            for d in ("2018-05-01", "2018-12-11", "2018-07-03", "2021-11-26")
        }
        assert len({close.time() for close in closes.values()}) >= 2


class TestSnapshotSelection:
    def test_last_valid_quote_by_ts_recv_wins(self) -> None:
        frame = _frame(
            [
                (
                    datetime(2018, 5, 1, 19, 55, 0, tzinfo=UTC),
                    datetime(2018, 5, 1, 19, 54, tzinfo=UTC),
                    1,
                    84.5,
                    84.6,
                ),
                (
                    datetime(2018, 5, 1, 19, 56, 0, tzinfo=UTC),
                    datetime(2018, 5, 1, 19, 55, tzinfo=UTC),
                    1,
                    84.7,
                    84.8,
                ),
            ]
        )
        rows, _ = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert len(rows) == 1
        assert rows.iloc[0]["bid_px"] == 84.7
        assert rows.iloc[0]["ts_recv"] == datetime(2018, 5, 1, 19, 56, tzinfo=UTC)

    def test_tie_on_ts_recv_uses_file_position(self) -> None:
        stamp = datetime(2018, 5, 1, 19, 56, tzinfo=UTC)
        frame = _frame(
            [
                (stamp, stamp, 1, 84.5, 84.6),
                (stamp, stamp, 1, 84.9, 85.0),
            ]
        )
        rows, _ = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert len(rows) == 1
        assert rows.iloc[0]["bid_px"] == 84.9  # later file position wins

    def test_old_ts_event_does_not_reorder_observation(self) -> None:
        frame = _frame(
            [
                (
                    datetime(2018, 5, 1, 19, 56, tzinfo=UTC),
                    datetime(2018, 5, 1, 19, 20, tzinfo=UTC),
                    1,
                    84.7,
                    84.8,
                ),
                (
                    datetime(2018, 5, 1, 19, 55, tzinfo=UTC),
                    datetime(2018, 5, 1, 19, 54, tzinfo=UTC),
                    1,
                    84.5,
                    84.6,
                ),
            ]
        )
        rows, _ = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert rows.iloc[0]["ts_recv"] == datetime(2018, 5, 1, 19, 56, tzinfo=UTC)

    def test_nat_ts_event_keeps_valid_observation(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 1, 84.7, 84.8),
            ]
        )
        rows, _ = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert len(rows) == 1
        assert pd.isna(rows.iloc[0]["ts_event"])

    def test_crossed_quote_rejected(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 1, 85.0, 84.5),  # crossed
            ]
        )
        with pytest.raises(MissingResearchSourceError, match="no valid"):
            select_final_quotes(
                frame,
                datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
                datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
            )

    def test_locked_quote_retained_and_flagged(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 1, 85.0, 85.0),  # locked
            ]
        )
        rows, counts = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert len(rows) == 1
        assert bool(rows.iloc[0]["locked"])
        assert counts["locked_retained"] == 1

    def test_missing_side_rejected(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 1, 0.0, 84.5),  # no bid
            ]
        )
        with pytest.raises(MissingResearchSourceError, match="no valid"):
            select_final_quotes(
                frame,
                datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
                datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
            )

    def test_records_outside_window_excluded(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 49, 59, tzinfo=UTC), None, 1, 84.5, 84.6),
                (datetime(2018, 5, 1, 20, 0, 0, tzinfo=UTC), None, 2, 84.7, 84.8),
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 3, 84.9, 85.0),
            ]
        )
        rows, counts = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert counts["record_count_in_window"] == 1
        assert rows["instrument_id"].tolist() == [3]

    def test_record_at_start_included_at_close_excluded(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 50, 0, tzinfo=UTC), None, 1, 84.5, 84.6),
                (datetime(2018, 5, 1, 20, 0, 0, tzinfo=UTC), None, 2, 84.7, 84.8),
            ]
        )
        rows, counts = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert counts["record_count_in_window"] == 1
        assert rows["instrument_id"].tolist() == [1]

    def test_per_instrument_selection_and_sort_order(self) -> None:
        frame = _frame(
            [
                (datetime(2018, 5, 1, 19, 55, tzinfo=UTC), None, 10, 84.5, 84.6),
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 10, 84.7, 84.8),
                (datetime(2018, 5, 1, 19, 56, tzinfo=UTC), None, 2, 74.7, 74.8),
            ]
        )
        rows, _ = select_final_quotes(
            frame,
            datetime(2018, 5, 1, 19, 50, tzinfo=UTC),
            datetime(2018, 5, 1, 20, 0, tzinfo=UTC),
        )
        assert rows["instrument_id"].tolist() == [2, 10]


class TestNormalizedParquetIrrelevance:
    def test_consumer_reads_raw_only(self) -> None:
        # The preprocessing path consumes raw DBN exclusively; normalized
        # parquet (which lacks ts_recv) is never opened here.
        import inspect

        import neuralmarket.data.research.preprocessing as module

        source = inspect.getsource(module)
        assert "read_parquet" not in source
        assert "data/processed" not in source
