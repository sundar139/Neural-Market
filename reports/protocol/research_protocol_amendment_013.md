# Research Protocol Amendment 013

## Neural-SDE Source Contract Repair: Return Semantics and Variance Objective

**Date:** 2026-08-17
**Commit:** (pending)
**Status:** ACCEPTED

---

## Background

During investigation of v1/v2/v3 neural-SDE training failures, three source
defects were identified that corrupted the model output contract and training
objectives. These defects affected all neural-SDE experiments (v1, v2, v3).

## Defect 1: Cumulative Levels Returned as Increments

**Root cause:** `ConditionalNeuralSde.forward()` returned `state[:, 0]`
(cumulative x-level) instead of `step[:, 0]` (one-step x-increment).

**Impact:** Every downstream consumer (signature construction, variance
objective, terminal-return calculation, ACF, stylized-fact evaluation)
received cumulative levels disguised as daily returns.

**Fix:** Changed line 213 of `neural_sde.py` from
`increments.append(state[:, 0].unsqueeze(1))` to
`increments.append(step[:, 0].unsqueeze(1))`.

**Regression tests added:** Multi-step increment verification, cumsum
reconstruction, constant-coefficient SDE analytic moments, white-noise ACF.

## Defect 2: Pooled Variance Conflating Path Variation

**Root cause:** `log_variance_penalty()` used `generated.var(dim=None)`
which pools ALL values across ALL paths and ALL timesteps, conflating
within-path and between-path variation.

**Impact:** The training variance target was computed from a pooled statistic
of fit windows, while the gate used a different pooled statistic of selection
windows. This created an inherent ~3.9x contradiction that could cause the
gate to fail by construction.

**Fix:** Added `per_path_variance()` and `log_variance_penalty_per_path()`
to `signature_mmd.py`. Training, selection, and gate now all use the same
per-path statistic.

## Defect 3: Checkpoint Selection Used RBF-MMD Only

**Root cause:** Early stopping and best-epoch selection used `sel_rbf`
(RBF-MMD component only) instead of `sel_total` (RBF-MMD + variance penalty).

**Impact:** The selected model could have poor variance calibration if the
variance penalty dominated the total loss.

**Fix:** Changed checkpoint selection to use `sel_total < best_total`.

## Historical Experiment Supersession

v1, v2, and v3 neural-SDE results were generated with cumulative x-levels
consumed as if they were daily return increments. Their:

- Neural generator performance metrics
- Stylized-fact rankings
- Collapse/drift interpretations
- Comparisons to classical baselines

**cannot support scientific claims.**

Their artifacts remain preserved as historical debugging/reproducibility
evidence. Classical baseline results (GBM, GJR-GARCH, Heston, bootstrap)
are **NOT invalidated** by this repair.

The corrected neural research lineage begins only after this source repair.
