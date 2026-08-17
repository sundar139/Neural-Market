"""Window/context construction: geometry, leakage, determinism, features."""

from __future__ import annotations

import numpy as np
import pytest

from neuralmarket.data.research.sde_windows import (
    CONTEXT_FEATURE_NAMES,
    SdeWindow,
    WindowSpec,
    build_windows,
    compute_context_features,
    fit_cumret_scale,
    fit_feature_normalizer,
    split_fit_selection,
)

pytestmark = pytest.mark.unit

_SPEC = WindowSpec()


def _returns(n: int = 400, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 0.01, size=n)


def _dates(n: int, start: str = "2020-01-02") -> list[str]:
    from datetime import date, timedelta

    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def _train_dates() -> list[str]:
    # 2018-05-01 .. 2021-12-31 weekdays-like (plain sequential labels, distinct).
    from datetime import date, timedelta

    d0 = date(2018, 5, 1)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(500)]


class TestWindowGeometry:
    def test_context_strictly_precedes_target(self) -> None:
        returns = _returns(400)
        windows = build_windows(returns, _dates(400), _SPEC)
        for w in windows:
            assert w.start_index >= _SPEC.context_lookback
            ctx_end = w.start_index - 1
            trg_start = w.start_index
            assert ctx_end < trg_start
            assert np.array_equal(
                w.context_returns, returns[w.start_index - _SPEC.context_lookback : w.start_index]
            )
            assert np.array_equal(
                w.target_returns, returns[w.start_index : w.start_index + _SPEC.horizon]
            )

    def test_target_length_is_exactly_horizon(self) -> None:
        windows = build_windows(_returns(400), _dates(400), _SPEC)
        for w in windows:
            assert len(w.target_returns) == 63

    def test_context_lookback_is_exactly_22(self) -> None:
        windows = build_windows(_returns(400), _dates(400), _SPEC)
        for w in windows:
            assert len(w.context_returns) == 22

    def test_eligible_count_is_derived_not_hardcoded(self) -> None:
        returns = _returns(400)
        windows = build_windows(returns, _dates(400), _SPEC)
        expected = 400 - _SPEC.context_lookback - _SPEC.horizon + 1
        assert len(windows) == expected  # 316 here, but derived from the series length
        larger = build_windows(_returns(800), _dates(800), _SPEC)
        larger_expected = 800 - _SPEC.context_lookback - _SPEC.horizon + 1
        assert len(larger) == larger_expected

    def test_chronological_ordering_and_deterministic_ids(self) -> None:
        returns = _returns(400)
        windows = build_windows(returns, _dates(400), _SPEC)
        starts = [w.start_index for w in windows]
        assert starts == sorted(starts)
        assert [w.window_id for w in windows] == [f"w{s:04d}" for s in starts]
        windows2 = build_windows(returns, _dates(400), _SPEC)
        assert [w.window_id for w in windows2] == [w.window_id for w in windows]

    def test_no_training_period_leakage(self) -> None:
        # Dates are the training split only; every window lies inside them.
        dates = _train_dates()[:299]
        returns = _returns(299)
        windows = build_windows(returns, dates, _SPEC)
        assert dates[0] <= windows[0].context_start_date
        assert windows[-1].target_end_date <= dates[-1]
        assert all(d <= "2021-12-31" for w in windows for d in (w.target_end_date,))

    def test_sealed_test_dates_rejected(self) -> None:
        dates = [*_train_dates()[:300], "2023-07-01", "2023-07-03"]
        returns = _returns(302)
        with pytest.raises(ValueError, match="sealed final-test"):
            build_windows(returns, dates, _SPEC)

    def test_dates_must_match_returns(self) -> None:
        with pytest.raises(ValueError, match="match returns"):
            build_windows(_returns(400), _dates(399), _SPEC)

    def test_non_finite_returns_rejected(self) -> None:
        bad = _returns(400)
        bad[10] = np.nan
        with pytest.raises(ValueError, match="NaN or infinity"):
            build_windows(bad, _dates(400), _SPEC)


class TestContextFeatures:
    def test_features_are_correct_lag_statistics(self) -> None:
        returns = _returns(400)
        window = build_windows(returns, _dates(400), _SPEC)[0]
        ctx = window.context_returns
        feats = compute_context_features(window, _SPEC)
        assert feats.prev_daily_return == pytest.approx(float(ctx[-1]))
        assert feats.prev_5d_cumulative_return == pytest.approx(float(np.sum(ctx[-5:])))
        assert feats.prev_22d_cumulative_return == pytest.approx(float(np.sum(ctx)))
        assert feats.prev_22d_realized_volatility == pytest.approx(float(np.sqrt(np.sum(ctx**2))))
        assert feats.array().shape == (4,)
        assert list(CONTEXT_FEATURE_NAMES) == [
            "prev_daily_return",
            "prev_5d_cumulative_return",
            "prev_22d_cumulative_return",
            "prev_22d_realized_volatility",
        ]

    def test_context_width_mismatch_rejected(self) -> None:
        window = SdeWindow(
            window_id="w",
            start_index=22,
            context_returns=np.zeros(21),
            target_returns=np.zeros(63),
            context_start_date="2020-01-01",
            context_end_date="2020-02-01",
            target_start_date="2020-02-02",
            target_end_date="2020-05-01",
        )
        with pytest.raises(ValueError, match="context length"):
            compute_context_features(window, _SPEC)

    def test_non_finite_context_rejected(self) -> None:
        returns = _returns(400)
        window = build_windows(returns, _dates(400), _SPEC)[0]
        bad = SdeWindow(
            window_id=window.window_id,
            start_index=window.start_index,
            context_returns=np.full(22, np.inf),
            target_returns=window.target_returns,
            context_start_date=window.context_start_date,
            context_end_date=window.context_end_date,
            target_start_date=window.target_start_date,
            target_end_date=window.target_end_date,
        )
        with pytest.raises(ValueError, match="NaN or infinity"):
            compute_context_features(bad, _SPEC)


class TestNormalization:
    def test_fit_from_training_matrix_and_reject_non_finite(self) -> None:
        rng = np.random.default_rng(3)
        matrix = rng.normal(size=(100, 4))
        norm = fit_feature_normalizer(matrix)
        assert norm.means.shape == (4,) and norm.stds.shape == (4,)
        assert np.all(norm.stds > 0)
        z = norm.normalize(matrix)
        assert np.allclose(z.mean(axis=0), 0.0, atol=1e-12)
        assert np.allclose(z.std(axis=0), 1.0, atol=1e-12)
        assert len(norm.normalizer_hash()) == 64

    def test_zero_std_fails_closed(self) -> None:
        matrix = np.zeros((10, 4))
        matrix[:, 0] = 1.0  # column 1 constant -> zero std
        with pytest.raises(ValueError, match="positive"):
            fit_feature_normalizer(matrix)

    def test_normalize_rejects_non_finite_and_wrong_width(self) -> None:
        norm = fit_feature_normalizer(np.random.default_rng(1).normal(size=(50, 4)))
        with pytest.raises(ValueError, match="must be finite"):
            norm.normalize(np.array([[np.nan, 0, 0, 0]]))
        with pytest.raises(ValueError, match="width"):
            norm.normalize(np.zeros((1, 3)))

    def test_cumret_scale_positive_and_training_only_shape(self) -> None:
        scale = fit_cumret_scale(_returns(925), 63)
        assert scale > 0 and np.isfinite(scale)
        with pytest.raises(ValueError, match="NaN or infinity"):
            fit_cumret_scale(np.array([1.0, np.inf]), 63)


class TestInternalSplit:
    def test_fit_selection_target_intervals_do_not_overlap(self) -> None:
        returns = _returns(400)
        windows = build_windows(returns, _dates(400), _SPEC)
        split = split_fit_selection(windows, 0.8, _SPEC)
        assert split.n_eligible == len(windows)
        assert split.n_fit + split.n_selection + split.gap_windows == split.n_eligible
        # Interval proof: selection starts after fit ends, with a gap.
        assert split.selection_target_start_index > split.fit_target_end_index
        fit_targets = sorted({(w.start_index, w.start_index + 62) for w in split.fit_windows})
        sel_targets = sorted({(w.start_index, w.start_index + 62) for w in split.selection_windows})
        assert fit_targets[-1][1] < sel_targets[0][0]

    def test_split_is_chronological(self) -> None:
        windows = build_windows(_returns(400), _dates(400), _SPEC)
        split = split_fit_selection(windows, 0.8, _SPEC)
        fit_starts = [w.start_index for w in split.fit_windows]
        sel_starts = [w.start_index for w in split.selection_windows]
        assert fit_starts == sorted(fit_starts)
        assert sel_starts == sorted(sel_starts)
        assert fit_starts[-1] < sel_starts[0]

    def test_split_hash_deterministic_and_sensitive(self) -> None:
        windows = build_windows(_returns(400), _dates(400), _SPEC)
        s1 = split_fit_selection(windows, 0.8, _SPEC)
        s2 = split_fit_selection(windows, 0.8, _SPEC)
        s3 = split_fit_selection(windows, 0.7, _SPEC)
        assert s1.split_hash == s2.split_hash
        assert s1.split_hash != s3.split_hash
        assert len(s1.split_hash) == 64

    def test_invalid_fraction_rejected(self) -> None:
        windows = build_windows(_returns(400), _dates(400), _SPEC)
        with pytest.raises(ValueError, match="strictly between"):
            split_fit_selection(windows, 1.0, _SPEC)
