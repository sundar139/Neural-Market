# Research Protocol Amendment 015

## Neural-SDE Gate v2 Governance: Multi-Lag ACF Threshold Downgrade

**Date:** 2026-08-18
**Status:** ACCEPTED

---

## Background

Amendment 014 introduced a new multi-lag ACF gate with RMSE threshold 0.15
and max-error threshold 0.25. These thresholds lacked sufficient independent
statistical derivation — they were not established before v4 training and
their values were not justified by analytical reasoning or pre-existing
protocol.

The governing rule requires: if a defensible new threshold cannot be
established independently of v4, keep the metric REPORT-ONLY.

## Changes

### 1. Multi-Lag ACF Thresholds Downgraded

- ACF RMSE: status changed from pass_fail → report_only
- ACF max error: status changed from pass_fail → report_only
- Diagnostic reference values retained for informational use
- Neither affects gate pass/fail

### 2. ACF(1) Retained as Pass/Fail

- |acf_real(1) - acf_gen(1)| <= 0.25
- This threshold has pre-v4 provenance (existed in the v3 gate as
  `gate_return_acf1_max_diff`)
- Not derived from v4 results

### 3. Equal-N Enforcement Added

- Production gate now explicitly rejects mismatched real/generated terminal
  sample counts with ValueError
- This was a missing contract enforcement in amendment 014

### 4. Gate Pass/Fail Criteria (Complete List)

The following criteria control gate pass/fail:

1. best_selection_total_loss < initial_selection_total_loss
2. 0.50 <= variance_ratio <= 2.00
3. 0.50 <= terminal_dispersion_ratio <= 2.00 (bootstrap reference)
4. path_uniqueness >= 0.99
5. |acf_real(1) - acf_gen(1)| <= 0.25
6. drift_rms / diffusion_rms <= 0.50

Report-only (do NOT affect pass/fail):
- Terminal Wasserstein distance
- ACF RMSE across lags
- ACF max error across lags
- Absolute-return ACF
- Squared-return ACF
- Conditional variance correlation

## Historical Experiments

v4 remains historically FAIL under its original frozen gate (amendment 013).
v4 post-hoc QA under gate v2 (amendment 014) remains QA only — not a
status reclassification.
