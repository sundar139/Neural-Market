# Research Protocol Amendment 014

## Neural-SDE Internal Gate Contract Repair: Bootstrap Terminal Estimator

**Date:** 2026-08-18
**Status:** ACCEPTED

---

## Background

The v4 internal gate failed on the terminal-dispersion criterion (ratio 2.99
vs threshold 2.00). Independent audit revealed the estimator was invalid:

- The real-sample denominator used 107 heavily overlapping 63-day windows
  spanning only 169 daily returns (~2.68 non-overlapping blocks).
- The generated numerator used 1024 independent simulated paths.
- The estimator was therefore incommensurable: a small overlapping real
  sample vs a large independent generated sample.
- Across training-history slices, the real 63-day terminal-std estimator
  changed by approximately 9.78x, confirming statistical instability.

## Changes

### 1. Terminal Dispersion Estimator (RETIRED → REPLACED)

**Old:** std of 107 overlapping empirical 63-day sums vs 1024 generated paths.

**New:** Block-bootstrap reference distribution:
- Source: internal-selection real daily returns only.
- Method: circular moving-block bootstrap (block_length=22, matching frozen
  baseline suite convention).
- Count: 1024 real bootstrap paths = 1024 generated paths (equal N).
- Both produce 63-day terminal returns.
- Dispersion metric: std_generated / std_real_bootstrap.
- Band: [0.50, 2.00] (unchanged threshold, new estimator).

### 2. Terminal Distribution Metric (NEW)

- 1-Wasserstein distance between generated and bootstrap-real terminal returns.
- Normalized by real bootstrap std.
- Status: REPORT-ONLY (no frozen threshold yet).
- May become pass/fail through a future protocol amendment.

### 3. Serial Dependence Gate (EXPANDED)

**Old:** ACF(1) only, threshold 0.25.

**New:** Multi-lag ACF with lags (1, 2, 3, 5, 10, 20):
- RMSE across lags as aggregate statistic.
- Per-lag max absolute error.
- Both are pass/fail with frozen thresholds.
- ACF(1) still reported for transparency.

### 4. Volatility Clustering Diagnostics (NEW)

- Absolute-return ACF and squared-return ACF at the same lags.
- Status: REPORT-ONLY (no pass/fail threshold).
- Purpose: v5 model-development evidence.

### 5. Conditional Variance Diagnostic (NEW)

- Per-path log-variance correlation between generated and real.
- Correlation with 22-day realized volatility.
- Status: REPORT-ONLY.

## Governance

- New thresholds are NOT derived from v4 results.
- Terminal dispersion band [0.50, 2.00] is retained from existing protocol.
- ACF thresholds are derived from analytical reasoning (white noise baseline).
- Report-only metrics will require independent justification before becoming
  pass/fail criteria.

## Historical Experiments

v4 remains FAIL under its original frozen gate specification (research
protocol amendment 013). This amendment applies prospectively only.
v4 may be re-evaluated diagnostically under the new gate for QA purposes,
but this does NOT change its historical PASS/FAIL status.
