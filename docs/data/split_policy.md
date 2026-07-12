# Split Policy

## Why not a random split

Financial series are autocorrelated and non-stationary. A random train/test split
leaks future information into training and grossly overstates performance. Only
chronological splitting with purging and embargoing is permitted.

## Calendar

Splits are computed on the XNYS (NYSE) trading calendar via `exchange-calendars`.
Every split boundary is a real trading session. The calendar library version and a
hash of the full session list are recorded in the manifest for reproducibility.

## Algorithm

Given the study window and anchors:

1. Generate all valid XNYS sessions for the study range.
2. Training ends on the final session on or before the training anchor.
3. Exclude the next `purge + embargo` sessions (90 + 10 = 100).
4. Validation begins on the next session; it ends on the final session on or
   before the validation anchor.
5. Exclude the next 100 sessions.
6. The final test begins on the next session and ends on or before the test anchor.

Splits never overlap; each excluded boundary block is recorded with its date
range, session count, and a session-list hash.

## Frozen boundaries (2018–2025 window)

| Split | Start | End |
| --- | --- | --- |
| Training | 2018-01-02 | 2021-12-31 |
| (excluded 100 sessions) | 2022-01-03 | 2022-05-25 |
| Validation | 2022-05-26 | 2023-06-30 |
| (excluded 100 sessions) | 2023-07-03 | 2023-11-21 |
| Final test (sealed) | 2023-11-22 | 2025-12-31 |

Regenerate with `neuralmarket data split freeze`; the canonical `manifest_hash`
is deterministic across runs with unchanged code, config, and calendar version.

## Sealed final test

The manifest sets `final_test_access_status = "sealed"`. Final-test market values
are never queried or downloaded during model development, selection, or tuning.
The seal may be broken only after models, metrics, baselines, transaction costs,
and statistical procedures are frozen.

## Purge and embargo rationale

- **Purge (90 sessions):** removes training/evaluation overlap from the maximum
  conditioning lookback (60) and maximum option maturity (30), so no evaluation
  episode shares information with a training episode.
- **Embargo (10 sessions):** an additional buffer against residual serial
  correlation near the boundary.
