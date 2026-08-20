# Research Protocol Amendment 030

## V5 Seed-02 Primary Adjudication Evidence Correction

**Date:** 2026-08-20
**Task:** NM-R4-V5-SEED-02-ADJUDICATION-REPAIR-041
**Independent audit:** NM-R4-V5-PRIMARY-SEED-02-AUDIT-040
**Audit verdict:** REPAIR REQUIRED
**Supersedes adjudication:** `reports/research/structured_vol_v5_seed_02_primary_adjudication.json` (v1, preserved)
**Corrected adjudication:** `reports/research/structured_vol_v5_seed_02_primary_adjudication_v2.json`
**Adjudicator helper:** `reports/research/evidence/structured_vol_v5_primary_adjudicator.py`

## Audit finding

Independent audit 040 found the derived seed-02 adjudication artifact v1 contained
evidence-mapping defects while the raw scientific execution itself remained sound.
The defect is confined to the derived adjudication artifact and its generation logic;
no training, replay, or seed-03 execution is involved in this correction.

## Raw scientific status

The raw seed-02 scientific execution remains **PRIMARY_VALID_COMPLETED**. The single
real execution (training invocations = 1, terminal status COMPLETED) and all raw
Gate diagnostic bytes are byte-identical and frozen. No raw runner evidence was
modified, re-executed, or re-derived in this repair.

Independently recomputed six-criterion result remains **PASS** (all six criteria pass
on the frozen raw Gate values).

## v1 adjudication preservation

The v1 adjudication at `reports/research/structured_vol_v5_seed_02_primary_adjudication.json`
is **SUPERSEDED but PRESERVED** as defective historical evidence. It was not overwritten,
renamed, deleted, or silently fixed. The corrected v2 artifact explicitly records
`supersedes` pointing to the v1 path/SHA/blob and `supersession_reason`.

## Exact defects in v1

1. **Criteria 4, 5, 6 wrong values.** The three criteria did not derive from their
   required Gate diagnostic keys:
   - criterion 4 emitted `value: "not_in_diagnostics"` instead of `path_uniqueness_fraction = 1.0`;
   - criterion 5 emitted `value: 6.282044341787696e-05` (which is `real_daily_variance`) instead of `return_acf1_abs_diff = 0.053962308505563134`;
   - criterion 6 emitted `value: "f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469"` (which is `gate_spec_hash`) instead of `drift_diffusion_rms_ratio = 0.028829878414236947`.
   Pass booleans were pre-filled `true` rather than computed from values and thresholds.

2. **Final epoch 8 instead of 48.** v1 recorded `final_epoch: 8` (copying `best_epoch`).
   The raw `training_report.json` and `training_execution_manifest.json` both record
   `best_epoch: 8, final_epoch: 48` and the training curve has 48 entries. Correct
   interpretation: best epoch 8 + patience 40 = final epoch 48.

3. **Missing family-comparison provenance.** v1 omitted runtime and data provenance
   needed for cross-member comparison (effective config, window construction,
   training-series SHA context, determinism flags).

## Corrected v2 identity

The v2 artifact at `reports/research/structured_vol_v5_seed_02_primary_adjudication_v2.json`
uses schema `structured-vol-v5-primary-adjudication-v2` and records:

- supersedes v1 (path, SHA-256, committed Git blob) and supersession reason;
- full seed tuple (9281/9281/9282/8283), full config hash, run prefix, family methodology;
- authorization path/SHA/blob, runner blob, contract-v5 blob, schedule blob, canonical recipe;
- Amendment 029 identity (path/SHA/blob);
- raw marker/transcript/exit/manifest/training-report paths, SHAs, and committed blobs;
- raw runner terminal status COMPLETED, exit 0, scientific invocation count 1;
- training_series SHA-256, fit 672, selection 107, derived all-training windows 841;
- for each criterion 1-6: metric/gate-key, exact numeric value, operator/threshold, computed pass;
- report-only Wasserstein (normalized 0.6040767839981898) explicitly marked REPORT_ONLY;
- untracked model artifacts (selected checkpoint, training curve, final checkpoint) by path/SHA/size only, without committed Git blob;
- mechanically derived `governed_primary_status = PRIMARY_VALID_COMPLETED`.

No raw runner evidence changed. No training occurred.

## Prose correction from task 039

Task 039 prose used `925` as an all-training window count. `925` is the training
return count (926 session dates minus one) established by the frozen training split,
not the derived window count. The correct derived all-training window count is:

```
672 fit + 107 selection + 62 embargo-gap = 841 derived windows
```

Task 039 raw evidence was not modified to make this prose discrepancy disappear;
the correction is recorded here and in the v2 artifact's `window_counts`.

## Authorization

- seed-02 raw execution: **FROZEN** (byte-identical).
- seed-02 adjudication v1: **SUPERSEDED_PRESERVED**.
- seed-02 adjudication v2: **FROZEN_PENDING_INDEPENDENT_AUDIT**.
- seed-02 scientific status: **PRIMARY_VALID_COMPLETED**.
- seed-03: **NOT AUTHORIZED** pending independent audit of v2.
- seed-04, seed-05, reserves, validation, external validation, final test, hedging: **NOT AUTHORIZED / CLOSED** as before.

Next task must be one independent Claude read-only audit of the corrected adjudication v2
before seed-03 execution can be considered.
