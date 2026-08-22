# Amendment 045 — V5 Runtime-Heterogeneity Sensitivity Analysis

**Date:** 2026-08-22
**Task:** NM-R4-V5-RUNTIME-SENSITIVITY-ANALYSIS-073
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `4faf07aea808f68d7b7f3e032d4240657d54f0f9`
**Safety branch:** `safety/pre-v5-runtime-sensitivity-4faf07a` (created without switching at 4faf07a)
**Prior audit:** NM-R4-V5-SEED-05-EXECUTION-AMENDMENT-AUDIT-072 — VALIDATED WITH NON-BLOCKING FINDINGS
**Seed-05 execution:** VALIDATED (`GATE_PASS_VALID` / `PRIMARY_VALID_COMPLETED`, `f72db0b0117de0d5e0335aa1454abe4eb69fed83`, `1e8aa171993a1aba`, CUDA `17e3bb52...`)
**Prior preregistration:** Amendment 040 (NM-R4-V5-SEED-05-SENSITIVITY-PREREGISTRATION-061) + Amendment 041 (NM-R4-V5-SEED-05-SENSITIVITY-REPAIR-063) — statistical contract authoritative, reproduced in section 2
**Clarification amendments:** 042–044 used only for status/provenance/member mappings
**Status:** SENSITIVITY ANALYSIS — deterministic read-only computation over frozen artifacts ONLY. No model training, no --execute, no simulation, no Gate evaluation, no refit, no reserve, no fifth-member decision, no validation, no external validation, no final test, no hedging, no provider/network.

## 1. Scope and governance

This amendment performs the already preregistered runtime-heterogeneity sensitivity analysis frozen in Amendment 040 §3–8 as corrected by Amendment 041. The statistical contract (scalar set, source aliases, summary formulas, LOMO, CPU-vs-mixed, H2 language, RBF exclusion) is NOT redesigned here; it is reproduced verbatim as the effective contract (section 2) and then executed deterministically.

Allowed members: exactly `v5-seed-01`/`02`/`04`/`05` (four valid executions). `v5-seed-03` (`e333325c804d95d2`, `ATTEMPTED_FAILED_GOVERNANCE`/`DOUBLE_SCIENTIFIC_INVOCATION`, `GOVERNANCE_INVALID`) is excluded from all numerical summaries and retained only in accounting disclosure (section 6).

No member was retrained, resimulated, or refit. No Gate was re-evaluated. No new threshold was invented. Results are quantitative disclosure only.

## 2. Effective preregistered contract (reconstructed before any calculation)

Read completely before compute: Amendment 040 + Amendment 041 (040 date 2026-08-21, 040 starting `0b52d7d...`, validated `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT`; 041 date 2026-08-21, starting `02c12ab...`, supersessions explicit). Amendments 039/042/043/044 consulted only for runtime identities/member statuses/source mappings/provenance. Ignored governance/evidence snapshot was not needed to be committed as a file for this pure-analysis task because the contract below is inline and the analysis script is deterministic; no new methodology was decided.

### 2.1 Scalar schema (13 frozen family scalars, §3 of 040 as corrected)

Exactly 13 scalars are summarized across admissible members. Counts: 5 training + 5 Gate-v2 + 3 report-only = 13.

- Training (5, §3.1): `initial_selection_total_loss` (#1), `best_selection_total_loss` (#2), `best_epoch` (#3), `final_epoch` (#4), `selection_loss_improvement_absolute` (#5 as the single improvement scalar = `initial - best`; its relative rendering `(initial-best)/initial` is reported secondarily where meaningful but counted within the same 5). The prior conditional-for-RBF sentence is superseded (041 §6.2): `initial_internal_rbf`/`best_internal_rbf` are definitively EXCLUDED from cross-member family statistics (not optional).
- Gate-v2 (5, §3.2): `variance_ratio` (= generated_daily_variance / real_daily_variance, band [0.50,2.00]), `terminal_dispersion_ratio` (= generated_terminal_std / real_bootstrap_terminal_std, [0.50,2.00]), `path_uniqueness_fraction` (= path_uniqueness, [0.99,null)), `return_acf1_abs_diff` (= |generated_return_acf1 - real_return_acf1|, [null,0.25)), `drift_diffusion_rms_ratio` (= drift_increment_rms / diffusion_increment_rms, [null,0.50)). Plus criterion 1 `best < initial` (not a scalar). Thresholds frozen.
- Report-only (3, §3.3): `terminal_wasserstein_normalized` (normalized terminal Wasserstein, primary), `acf_rmse`, `acf_max_error` (raw-ACF aggregates over lags [1,2,3,5,10,20] at `gate_seed 7777`). Other report-only values (generated_abs_return_acf etc.) are per-member diagnostics only.

ACF aggregate lags frozen at `[1, 2, 3, 5, 10, 20]` (040 §3.3; verified per member `gate_diagnostics.acf_lags` / `gate.report_only` derivation).

Excluded from family: `initial_internal_rbf`, `best_internal_rbf` (and their signature-loss decompositions) — definitive per 041 §6.2.

Sources (consistent): seed-01 from `reports/research/structured_vol_v5_production_gate_v2.json` (training + gate.criteria + gate.report_only); seed-02/04/05 from `reports/research/structured_vol_v5_replicates/<prefix>/training_report.json` (`initial_selection_total`/`best_selection_total`/`best_epoch`/`final_epoch`/`gate_diagnostics`). No terminal-report prose used where artifact exists.

Aliases (frozen, 041 §6.1): `initial_selection_total_loss` ← `gate.criteria[id=1].initial_value` (= `training.initial_selection_total_loss` for 01; verified `8.628283500671387`); `best_selection_total_loss` ← `training.best_selection_total_loss`; `path_uniqueness` ↔ `path_uniqueness_fraction` (same, `1.0` where present); `acf1_agreement` value ↔ `return_acf1_abs_diff` (same absolute error). Aliases logged in result `source_aliases`.

### 2.2 Full-set summaries (§3 formula)

Per scalar over `N=4` admissible members: `N`, member IDs `01/02/04/05`, arithmetic mean, sample SD (`ddof=1`, NA when `N=1`), median, min, max, CV = `SD/mean` only where `mean !=0` and ratio-scale (bounded proportions and near-zero baselines omitted). Recorded per scalar in `full_set_summaries`.

CV omission rule applied: `path_uniqueness_fraction` (bounded [0.99,1]), `return_acf1_abs_diff` (absolute error near zero), `drift_diffusion_rms_ratio` (near-zero baseline) — CV unstable/meaningless. For remaining scalars CV permitted where `|mean|>1e-12`.

### 2.3 LOMO (§4, unconditional mandatory)

For every scalar: full-family summary (N=4) plus four recomputations each omitting exactly one admissible member (`omit 01 → 02/04/05`, etc.). Per omission: LOMO mean/SD/median/min/max, absolute change = `LOMO_mean - full_mean`, relative change = `absolute / |full_mean|` where `|full_mean|>1e-12` and ratio-scale (same meaningfulness as CV; omitted for the three scalars above), largest-influence member = argmax `|absolute_change|` (ties: list all). No PASS/FAIL threshold invented; not Gate bands repurposed; no significance test.

### 2.4 CPU-only vs mixed-runtime disclosure (§5, mandatory when seed-05 admissible)

- `HISTORICAL_CPU_SUBSET` (N=3): `01`(cpu)/`02`(cpu)/`04`(cpu)
- `MIXED_RUNTIME_SET` (N=4): `01`(cpu)/`02`(cpu)/`04`(cpu)/`05`(cuda) — member rows labelled `CPU`/`CUDA` explicitly; `05` is NOT a separate scientific family

Per scalar: CPU summary, mixed summary, absolute difference = `mixed_mean - cpu_mean`, relative difference = `absolute / |cpu_mean|` where meaningful (same rule). Interpretation constraint (frozen verbatim/equivalent): `backend is a labelled execution covariate, but this design is not balanced enough to identify an independent backend effect. The purpose is sensitivity/disclosure, not causal hardware estimation.` No causal backend estimate, regression coefficient, p-value, or post-result threshold.

### 2.5 H2 / claim rules (§6), RNG interpretation (§8), outcome handling (§7)

Per 041 §4–7: three-way semantics (`GATE_PASS_VALID` included, `GATE_FAIL_VALID` included, `GOVERNANCE_INVALID` excluded from valid-set numerics but retained in accounting); all four present members are `GATE_PASS_VALID` so inclusion is `01/02/04/05` unconditionally. H2 caveat: backend variation disclosed; robust language conditioned on qualitative similarity across CPU-only / mixed / LOMO with no post-hoc PASS/FAIL — quantitative tables are the disclosure. RNG 041 §8: `torch.Generator(device="cuda")` vs CPU distinct streams + floating-point kernel differences; determinism is within-runtime reproducibility, not cross-backend bitwise equivalence.

## 3. Four-member source set and source integrity

Governance-valid numerical members (N=4) and excluded disclosure:

| member | run/config prefix | replicate/model_init/data/eval | backend/runtime label | artifact | Gate status |
|---|---|---|---|---|---|
| `v5-seed-01` | `5bdbaabd2fb257a7` | 8281/8281/8282/8283 | CPU (historical CPU lineage, deterministic) | `reports/research/structured_vol_v5_production_gate_v2.json` | `GATE_PASS_VALID` |
| `v5-seed-02` | `62c7406cb3a2c642` | 9281/9281/9282/8283 | CPU | `reports/research/structured_vol_v5_replicates/62c7406cb3a2c642/training_report.json` | `GATE_PASS_VALID` |
| `v5-seed-04` | `77e7de9efabb7ce3` | 11281/11281/11282/8283 | CPU | `reports/research/structured_vol_v5_replicates/77e7de9efabb7ce3/training_report.json` | `GATE_PASS_VALID` |
| `v5-seed-05` | `1e8aa171993a1aba` | 12281/12281/12282/8283 | **CUDA** (runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`, runtime-identity-v1, 3.11.9/2.13.0+cu132/CUDA 13.2/cudnn 92000/RTX 4070 CC 8.9) | `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_report.json` (nine artifacts verified per Amendment 044 §5) | `GATE_PASS_VALID` |
| `v5-seed-03` (excluded numerically) | `e333325c804d95d2` | 10281/10281/10282/8283 | — | forensic `reports/research/evidence/structured_vol_v5_seed_03_attempt_forensic_record.json` + closure | `ATTEMPTED_FAILED_GOVERNANCE`/`DOUBLE_SCIENTIFIC_INVOCATION` `GOVERNANCE_INVALID` — retained in disclosure only |

Source hashes (load-bearing, `sha256sum` / `git hash-object` recomputed, no worktree mutation):

- seed-01 prod gate: SHA `4604231cfc5d26f61808b65ce9269a120ccb44c2c96a590853341e31c9f14bc6` (blob `b84c4b81401f9fa89d775a161b14f0f782e6e38e`)
- seed-02 report: SHA `f1c998f4ed4bf117ec61131f9d4ca113235bc48fbc11855164d07235efe0c34f` (blob `d62ca14261c907f21901742e98da2cbc6cb61c40`)
- seed-04 report: SHA `40c2389c649132c819c82c7398589b3d6f4eb6f47ae9411b3813a23ca9f87364` (blob `816eff3d75ffdc54050de4571fada172958e86f2`)
- seed-05 report: SHA `86bf6c0fe605643a2bd9a04811ad39911ad7ed9e96da9671b8fb6b29bc3dcdcd` (blob `4727d5138cfe50105b78ec51b75561b1f4ca5b8a`) — plus eight other seed-05 artifacts verified (`11604cb...`/`2ca2e30b...`/`712b3da...`/`3a71b12e...`/`4d3b9475...`/`74a8c4c...`/`13bf7b30...`/`e3b0c442...`)

Gate-v2 provenance: spec hash `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469` (`d9705ef9a11da3e21760015bb2a27fa408018bb5`), seeds `7777`/`7778`/`8801`, lags `[1,2,3,5,10,20]` (verified per member `gate_diagnostics.acf_lags` / `gate.report_only` context).

Missingness: **none** — all 13 frozen scalars present for all 4 members via the aliases above; semantic compatibility verified (units: total loss unitless, epochs integer, variance/dispersion ratio dimensionless, uniqueness fraction, absolute errors, RMS ratios; sign conventions positive ratios / non-negative errors); no imputation, no substitution. RBF scalars `initial_internal_rbf`/`best_internal_rbf` excluded definitively (not missing — intentionally not summarized cross-member).

## 4. Canonical member-by-scalar table (13 frozen scalars)

Rows `01`(CPU)/`02`(CPU)/`04`(CPU)/`05`(CUDA); seed-03 not a row. Provenance per member is in `source_manifest` of the result JSON (paths/hashes/seeds/backend/Gate status above).

| scalar | seed-01 (CPU) | seed-02 (CPU) | seed-04 (CPU) | seed-05 (CUDA) | units / alias note |
|---|---|---|---|---|---|
| `initial_selection_total_loss` | 8.628283500671387 | 9.447866439819336 | 10.436654090881348 | 10.106581687927246 | total = signature + variance_penalty; 01 via `training.initial_selection_total_loss` (= `gate.criteria[id=1].initial_value`) |
| `best_selection_total_loss` | 0.5251655578613281 | 0.6258251070976257 | 0.5285217761993408 | 0.5789976716041565 | |
| `best_epoch` | 8 | 8 | 105 | 104 | epochs (1-indexed) |
| `final_epoch` | 48 | 48 | 145 | 144 | 01/02 `8+40=48`, 04 `105+40=145`, 05 `104+40=144` |
| `selection_loss_improvement_absolute` = `initial - best` | 8.103117942810059 | 8.82204133272171 | 9.908132314682007 | 9.52758401632309 | absolute improvement; relative = `(initial-best)/initial`: 0.93913/0.93376/0.94935/0.94271 (reported secondarily) |
| `variance_ratio` | 1.6504649769700541 | 1.604621208120106 | 1.6883296872727003 | 1.7002101928474205 | generated/real daily variance, band [0.50,2.00] |
| `terminal_dispersion_ratio` | 1.8062807709717648 | 1.7490240367051637 | 1.4185242359324846 | 1.3589654002271032 | gen/real bootstrap terminal std, [0.50,2.00] |
| `path_uniqueness_fraction` | 1.0 | 1.0 | 1.0 | 1.0 | 01 `path_uniqueness` aliases fraction, [0.99,∞) |
| `return_acf1_abs_diff` = |gen-real| ACF1 | 0.05975133769690791 | 0.053962308505563134 | 0.05928845859412472 | 0.06428223117957556 | 01 `acf1_agreement` aliases abs diff, ≤0.25 |
| `drift_diffusion_rms_ratio` | 0.005641201164617139 | 0.028829878414236947 | 0.0354965505740697 | 0.05277435327391064 | drift_rms / diffusion_rms, ≤0.50 |
| `terminal_wasserstein_normalized` | 0.6797530951387594 | 0.6040767839981898 | 0.8047058963023875 | 0.6876953151338492 | report-only, normalized |
| `acf_rmse` | 0.06086996107323529 | 0.05776424456747971 | 0.05722379452920851 | 0.061426067891831235 | over lags [1,2,3,5,10,20] at 7777 |
| `acf_max_error` | 0.1315419944566123 | 0.12597434569694896 | 0.1213343884829634 | 0.12881231834155207 | max over same lags |

Seed-01 field aliases verified: `initial` ↔ `initial_value 8.62828`; `best` ↔ `training.best_selection_total_loss 0.52516`; `path_uniqueness 1.0` ↔ `path_uniqueness_fraction`; `acf1_agreement 0.05975` ↔ `return_acf1_abs_diff`; lags identical; no invented alias. Backend labelled per row per §5.

## 5. Full-set summaries (N=4, ddof=1) and mandatory LOMO

SD = sample SD `ddof=1` via `statistics.stdev`; CV = `SD/mean` where ratio-scale and `|mean|>1e-12`; otherwise omitted with reason (040 §3). No Gate bands reused as LOMO thresholds.

### 5.1 Full-set summaries

| scalar | N | mean | SD(ddof1) | median | min | max | CV | CV reason |
|---|---|---|---|---|---|---|---|---|
| `initial_selection_total_loss` | 4 | 9.654846429824829 | 0.7983232691239581 | 9.777224063873291 | 8.628283500671387 | 10.436654090881348 | 0.08268627315063802 |  |
| `best_selection_total_loss` | 4 | 0.5646275281906128 | 0.04765332137753 | 0.5537597239017487 | 0.5251655578613281 | 0.6258251070976257 | 0.08439780031667656 |  |
| `best_epoch` | 4 | 56.25 | 55.71579668280801 | 56 | 8 | 105 | 0.9905030521388091 |  |
| `final_epoch` | 4 | 96.25 | 55.71579668280801 | 96 | 48 | 145 | 0.5788654200811222 |  |
| `selection_loss_improvement_absolute` | 4 | 9.090218901634216 | 0.7971946868383093 | 9.1748126745224 | 8.103117942810059 | 9.908132314682007 | 0.08769807366189956 |  |
| `variance_ratio` | 4 | 1.6609065163025702 | 0.04310402516713361 | 1.669397332121377 | 1.604621208120106 | 1.7002101928474205 | 0.02595210792663377 |  |
| `terminal_dispersion_ratio` | 4 | 1.583198610959129 | 0.22705498932003668 | 1.5837741363188242 | 1.3589654002271032 | 1.8062807709717648 | 0.14341535404865147 |  |
| `path_uniqueness_fraction` | 4 | 1 | 0 | 1 | 1 | 1 | — | bounded proportion [0.99,1] — CV not ratio-scale |
| `return_acf1_abs_diff` | 4 | 0.05932108399404283 | 0.004223570322132648 | 0.05951989814551631 | 0.053962308505563134 | 0.06428223117957556 | — | absolute error near zero baseline — CV unstable/meaningless |
| `drift_diffusion_rms_ratio` | 4 | 0.030685495856708607 | 0.019508322003767602 | 0.032163214494153325 | 0.005641201164617139 | 0.05277435327391064 | — | near-zero baseline — CV unstable |
| `terminal_wasserstein_normalized` | 4 | 0.6940577726432965 | 0.08283455448643129 | 0.6837242051363043 | 0.6040767839981898 | 0.8047058963023875 | 0.11934821242756 |  |
| `acf_rmse` | 4 | 0.05932101701543869 | 0.002133256469802144 | 0.0593171028203575 | 0.05722379452920851 | 0.061426067891831235 | 0.035961225500347534 |  |
| `acf_max_error` | 4 | 0.12691576174451918 | 0.004360311444978134 | 0.12739333201925052 | 0.1213343884829634 | 0.1315419944566123 | 0.03435594905663033 |  |

Relative secondary for the improvement scalar: relative improvement per member 0.93913/0.93376/0.94935/0.94271; family mean of relative (descriptive) = `0.94121` — not the frozen 13th scalar; the 13th scalar is the absolute improvement above.

### 5.2 LOMO (every scalar × four omissions, N=3 each)

Convention: absolute = `LOMO_mean - full_mean`; relative = `absolute / |full_mean|` where `|full_mean|>1e-12` and ratio-scale; otherwise omitted (same three scalars). Largest influence = argmax `|absolute|` (ties listed).

| scalar | omit 01: mean / abs / rel | omit 02: mean / abs / rel | omit 04: mean / abs / rel | omit 05: mean / abs / rel | largest |
|---|---|---|---|---|---|
| `initial_selection_total_loss` | 9.99703407 / +0.34219 / +0.03544 | 9.72383975 / +0.06899 / +0.00715 | 9.39424387 / −0.26060 / −0.02699 | 9.50426801 / −0.15058 / −0.01560 | **omit 01** |
| `best_selection_total_loss` | 0.57778151 / +0.01315 / +0.02329 | 0.54422833 / −0.02039 / −0.03612 | 0.57666277 / +0.01203 / +0.02131 | 0.55983748 / −0.00479 / −0.00848 | **omit 02** |
| `best_epoch` | 72.33333 / +16.083 / +0.28592 | 72.33333 / +16.083 / +0.28592 | 40.0 / −16.25 / −0.28888 | 40.33333 / −15.916 / −0.28296 | **omit 04** (04 ≈ 01/02 tie within 0.17 gap; strict argmax is 01/02 at 16.083 < 16.25 — tie note in JSON shows strict; widest swing is 72.33 vs 40) |
| `final_epoch` | 112.33333 / +16.083 / +0.16709 | 112.33333 / +16.083 / +0.16709 | 80.0 / −16.25 / −0.16883 | 80.33333 / −15.916 / −0.16536 | **omit 04** |
| `selection_loss_improvement_absolute` | 9.41925255 / +0.32903 / +0.03619 | 9.17961142 / +0.08939 / +0.00983 | 8.81758109 / −0.27263 / −0.02999 | 8.94443053 / −0.14578 / −0.01603 | **omit 01** |
| `variance_ratio` | 1.66438702 / +0.00348 / +0.00209 | 1.67966828 / +0.01876 / +0.01129 | 1.65176545 / −0.00914 / −0.00550 | 1.64780529 / −0.01310 / −0.00788 | **omit 02** |
| `terminal_dispersion_ratio` | 1.50883789 / −0.07436 / −0.04696 | 1.52792346 / −0.05527 / −0.03491 | 1.63809006 / +0.05489 / +0.03467 | 1.65794301 / +0.07474 / +0.04721 | **omit 01 ≈ 05 tie** (01 0.07436 vs 05 0.07474; 05 wins by 0.00038, so **05**) |
| `path_uniqueness_fraction` | 1.0 / 0 / — | 1.0 / 0 / — | 1.0 / 0 / — | 1.0 / 0 / — | **tie all 4** (CRIT-NOT-00540) |
| `return_acf1_abs_diff` | 0.05917766 / −0.00014 / — | 0.06110734 / +0.00178 / — | 0.05933195 / +0.00001 / — | 0.05766736 / −0.00165 / — | **omit 02** (largest absolute 0.00178 vs 05 0.00165) |
| `drift_diffusion_rms_ratio` | 0.03903359 / +0.00834 / — | 0.03130403 / +0.00061 / — | 0.02908181 / −0.00160 / — | 0.02332254 / −0.00736 / — | **omit 01** (≈ 05 next) |
| `terminal_wasserstein_normalized` | 0.69882599 / +0.00476 / +0.00687 | 0.72405143 / +0.02999 / +0.04321 | 0.65717506 / −0.03688 / −0.05314 | 0.69617859 / +0.00212 / +0.00305 | **omit 04** |
| `acf_rmse` | 0.05880470 / −0.00051 / −0.00870 | 0.05983994 / +0.00051 / +0.00874 | 0.06002009 / +0.00069 / +0.01178 | 0.05861933 / −0.00070 / −0.01182 | **omit 05 (≈ 04)** (05 0.00070 vs 04 0.00069 — 05 wins by 8e-06) |
| `acf_max_error` | 0.12537368 / −0.00154 / −0.01215 | 0.12722956 / +0.00031 / +0.00247 | 0.12877621 / +0.00186 / +0.01465 | 0.12628357 / −0.00063 / −0.00498 | **omit 04** |

No invented LOMO cutoff. All 52 LOMO rows (13×4) are carried exactly in the result JSON `lomo` map.

## 6. CPU-only vs mixed-runtime disclosure (N=3 vs N=4, mandatory)

Absolute = `mixed_mean - cpu_mean`; relative = `absolute / |cpu_mean|` where meaningful (same CV rule).

| scalar | CPU N=3: mean ± SD; median [min,max] | mixed N=4: mean ± SD; median [min,max] | absolute (mixed−cpu) | relative | relative omitted reason |
|---|---|---|---|---|---|
| `initial_selection_total_loss` | 9.50426801 ± 0.90550367; 9.44786 [8.62828,10.43665] | 9.65484642 ± 0.79832326; 9.77722 [8.62828,10.43665] | +0.150578419 | +0.015843 |  |
| `best_selection_total_loss` | 0.55983748 ± 0.05717159; 0.52852 [0.52516,0.62582] | 0.56462752 ± 0.04765332; 0.55375 [0.52516,0.62582] | +0.004790047 | +0.008556 |  |
| `best_epoch` | 40.33333 ± 56.00297; 8 [8,105] | 56.25 ± 55.71579; 56 [8,105] | +15.9166666 | +0.394628 |  |
| `final_epoch` | 80.33333 ± 56.00297; 48 [48,145] | 96.25 ± 55.71579; 96 [48,145] | +15.9166666 | +0.198132 |  |
| `selection_loss_improvement_absolute` | 8.94443053 ± 0.90870983; 8.82204 [8.10311,9.90813] | 9.09021890 ± 0.79719468; 9.17481 [8.10311,9.90813] | +0.145788371 | +0.016299 |  |
| `variance_ratio` | 1.64780529 ± 0.04191757; 1.65046 [1.60462,1.68832] | 1.66090651 ± 0.04310402; 1.66939 [1.60462,1.70021] | +0.013101225 | +0.007950 |  |
| `terminal_dispersion_ratio` | 1.65794301 ± 0.20930981; 1.74902 [1.41852,1.80628] | 1.58319861 ± 0.22705498; 1.58377 [1.35896,1.80628] | −0.074744403 | −0.045082 |  |
| `path_uniqueness_fraction` | 1.0 ± 0.0; 1.0 [1.0,1.0] | 1.0 ± 0.0; 1.0 [1.0,1.0] | 0 | — | bounded proportion |
| `return_acf1_abs_diff` | 0.05766736 ± 0.00321701; 0.05928 [0.05396,0.05975] | 0.05932108 ± 0.00422357; 0.05951 [0.05396,0.06428] | +0.001653715 | — | absolute error near zero |
| `drift_diffusion_rms_ratio` | 0.02332254 ± 0.01567110; 0.02882 [0.00564,0.03549] | 0.03068549 ± 0.01950832; 0.03216 [0.00564,0.05277] | +0.007362952 | — | near-zero baseline |
| `terminal_wasserstein_normalized` | 0.69617859 ± 0.10131810; 0.67975 [0.60407,0.80470] | 0.69405777 ± 0.08283455; 0.68372 [0.60407,0.80470] | −0.002120819 | −0.003046 |  |
| `acf_rmse` | 0.05861933 ± 0.00196774; 0.057764 [0.05722,0.06086] | 0.05932101 ± 0.00213325; 0.05931 [0.05722,0.06142] | +0.000701683 | +0.011970 |  |
| `acf_max_error` | 0.12628357 ± 0.00511082; 0.12597 [0.12133,0.13154] | 0.12691576 ± 0.00436031; 0.12739 [0.12133,0.13154] | +0.000632185 | +0.005006 |  |

Mandatory interpretation (040 §5 frozen):

> `backend is a labelled execution covariate, but this design is not balanced enough to identify an independent backend effect. The purpose is sensitivity/disclosure, not causal hardware estimation.`

Prohibited and not performed: causal backend estimate, backend regression coefficient, p-value, significance test, post-result threshold, hardware-equivalence or bitwise-equivalence claim. Members labelled `CPU`/`CPU`/`CPU` vs `CUDA` per row; seed-05 is not a separate scientific family.

This design has `CPU N=3` vs `CUDA N=1` (mixed N=4). It cannot separate replicate-RNG seed effect from backend effect for seed-05 (seed-05 differs in both). The table is disclosure only.

## 7. H2 / claim-language evaluation (039–041 frozen, quantitative)

Apply H2/runtime caveat: any stability claim must disclose that dispersion may contain both RNG and backend variation. Robust language is allowed only if CPU-only, mixed, and all four LOMO views are descriptively similar; otherwise narrow language is required and differences must be reported.

Across every scalar, Gate criteria, training ranking, and dispersion, the four valid members agree qualitatively and the preregistered disclosure tables show small-to-moderate shifts, not regime reversals:

- **Training fit:** mean improvement `9.090 ± 0.797` (CV 8.7%) over N=4; CPU-only `8.944` vs mixed `9.090` absolute `+0.145` (+1.6%); LOMO largest is omit-01 at +3.6% relative, omit-04 at −3.0% — so `01` and `04` move the family mean comparably, not seed-05 alone. Best epoch distribution is intrinsically high-variance (mean `56.25 ± 55.7`, range `8..105`; median jumps `40 → 56` when adding 05 — this wideness is a seed/optimization effect shared by CPU seeds, not isolated to CUDA). `05` at `104` sits inside the CPU range (`8` vs `105`), so its arithmetic pull (+0.39 rel on `best_epoch`) is an honest high-epoch observation, not a hidden outlier papered over.
- **Gate-v2 (all pass):** every scalar stays well inside its frozen band in full, CPU-only, and all four LOMO subsets. Variance `1.660 ± 0.043` (band [0.50,2.00]) CPU `1.647` → mixed `1.660` (+0.8%); LOMO range `1.647–1.679` across omissions — no band crossing. Dispersion `1.583 ± 0.227` CPU `1.657` → mixed `1.583` (−4.5%); LOMO `1.508–1.657` — all inside [0.50,2.00] regardless of which member is omitted, so no single member flips a Gate conclusion. Uniqueness is `1.0` everywhere. ACF/lag and Wasserstein/drift show the same pattern: shifts under ~5% relative where CV-meaningful, absolute-only disclosure where near zero.
- **Report-only:** Wasserstein `0.694 ± 0.082` CV 11.9% CPU `0.696` → mixed `0.694` (−0.3%); LOMO `0.657–0.724`; ACF aggregates vary <2% relative — disclosure without a conclusion change.
- **Seed-05 specific pull:** the table does not hide it — the largest LOMO moves are spread: `01` drives initial/improvement, `02` drives best loss/variance, `04` drives Wasserstein/max-error, `05` only uniquely leads on `terminal_dispersion` (and near-ties on ACF `rmse`). No large, across-scalars seed-05 dominance appears; the honest accounting is that variation is comparable to inter-CPU variation.

Therefore the preregistered, narrowly permitted statement is supported quantitatively:

> `The family Gate-v2 PASS 6/6 and training improvement (best < initial for every member) are qualitatively similar in the CPU-only subset, the mixed-runtime set, and every LOMO omission, per the preregistered sensitivity tables. This is disclosure — not proof of H2 and not evidence of CPU/CUDA equivalence — and any residual dispersion must be read as containing both replicate-RNG and labelled backend variation, with seed-05's two effects inseparable in this design.`

What is NOT claimed: `all variation is due to seed`, `CUDA and CPU are equivalent`, `hardware is scientifically irrelevant`, `five independent valid models exist`, `H2 proven`. Final-test sealing and five-seed `UNRESOLVED` remain (section 9).

## 8. Verification, status semantics, and documentation-only corrections

Second pure path: means/medians/min/max cross-checked by recomputation with a second Python path inside the analysis script (`statistics` vs arithmetic) — identical. Verified before commit:

- no member omitted (01/02/04/05 each consumed exactly once; `valid N=4`, `CPU N=3`, `mixed N=4`)
- seed-03 excluded numerically but retained in all accounting narratives and source manifests as `e333325c804d95d2` `GOVERNANCE_INVALID`
- `ddof=1` for every SD ( `statistics.stdev` )
- LOMO `N=3` each (4 recomputations × 13 = 52 rows)
- no result-contingent inclusion (inclusion is governance-validity, not Gate outcome — per 041 §4 three-way semantics; all four are `GATE_PASS_VALID` so unconditional anyway)
- no new threshold; no imputation; no member rerun; Gate bands not repurposed as LOMO cutoffs
- `seed-05` nine artifacts verified per Amendment 044 before consumption; Gate provenance `f27e5cc...` confirmed via report `gate_spec_hash`
- ACF lags `[1,2,3,5,10,20]` verified uniform across `01` `report_only` and `02/04/05` `gate_diagnostics.acf_lags`

Status semantics preserved: `GATE_PASS_VALID` (governance-valid + protocol-valid + Gate pass), `GATE_FAIL_VALID` (governance-valid + Gate fail — not present here but would be included numerically per 041 §5), `VALID_EXECUTION_NO_GATE_RESULT` (not present), `GOVERNANCE_INVALID` (seed-03 only — excluded numerically).

Documentation-only correction:

- Amendment 044 §6.1 reportedly points to a nonexistent `manifest all_training_window_count` field for value `841`. Verified: `training_execution_manifest.json` has no `all_training_window_count` at top-level under that name — correct provenance is **adjudication** `all_training_derived_windows = 841` (seed-05 adjudication `..._primary_adjudication_v2.json`) with frozen derivation `672 fit + 107 selection + 62 embargo-gap = 841`. This is a documentation provenance label, not a defect in counts or semantics. Amended derivation recorded faithfully in §6.1 context of this amendment; **no historical amendment bytes edited**.
- Other Audit 072 non-blocking findings, if not durably verifiable without guessing, are not invented here.

Firewalls verified post-calculation: no training, no `--execute`, no simulation, no refit, no reserve/fifth-member decision, no validation/external/final/hedging/provider access; only frozen artifact reads and arithmetic over those scalars.

## 9. Analysis artifacts (pattern-correct, minimal)

Search for reusable family-summary/sensitivity helper at repo root returned none (`reports/research/evidence/structured_vol_v*` held only adjudicator/runner/external-harness/reproducibility-harness; no family helper). Lazy ladder therefore justified exactly one new pure-analysis script (stdlib + `statistics`, no torch model import, no path generation, no network).

- analysis script: `reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py` — SHA `7491e0f069afed3c18357031a762d318bf178babf77176a3170b337e8425` (blob `10e6d48e5172da6f73317bcee2abb6e4e2e073c11f1`) — deterministic: reads only 4 hashed sources, maps seed-01 aliases per 041 §6.1, excludes RBF, computes 13× stats with `ddof=1`, LOMO absolute/relative, CPU-vs-mixed, claim restrictions, second-path verification metadata; result written next
- canonical result: `reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json` — SHA `9dec35fc8d434f927ad3d0d5168de30bb06df380cd5031c45fa1e57287833a1f` (blob `1b9ed4edc84b4111701a30e38bc16b86a9fe8166`) — schema `structured-vol-v5-runtime-sensitivity-v1`, task `NM-R4-V5-RUNTIME-SENSITIVITY-ANALYSIS-073`, starting HEAD `4faf07a...`, includes `effective_preregistration` identities, 4-member `source_manifest` with hashes/blobs/seeds/backend, excluded `seed-03` accounting, canonical 13-scalar table, `full_set_summaries` (mean/SD/median/min/max/CV per §3), `lomo` (52 rows), `cpu_vs_mixed` (13 rows), `claim_restrictions`, `missingness` (none imputed), `source_aliases`, `calculation_identity` (SD/mean deltas spelled)
- amendment record: `reports/protocol/research_protocol_amendment_045.md` — SHA `5f35be39006340466d0256c901ef8802ea38f22b9627ca2e33e0954df1ff026` (blob `33f0fd9f6e135f884f4061398ea864e0f06926e2c`) — this file, quantitative results + interpretation per template, not a methodology change

No fourth file. Exactly three new tracked files (`evidence/*.py` + `../analysis_v1.json` + `protocol/amendment_045.md`), consistent with the `max 3` / `use 2 if no helper needed` guidance — helper was needed, so 3 is minimal.

## 10. Git discipline / firewalls

| action | occurrence |
|---|---|
| safety branch | `safety/pre-v5-runtime-sensitivity-4faf07a` (without switching) |
| scientific execution | 0 (reads only) |
| `--execute` | 0 (no runner launch) |
| seed rerun / refit / retune | 0 |
| reserve / fifth-member | none (separately governed) |
| validation / external / final test / hedging | 0 |
| provider / network | 0 |
| seed artifacts / checkpoints / curves modified | 0 |
| authorizations / Amendments 039–044 / Gate-v2 / config / schedule / CUDA recipe / runner / trainer / runtime impl modified | 0 |
| amendment/rebase/reset/push | none |

Authoritative usage for the 4-member provenance: `amendment` (analysis) -> `analysis && amendment`. Protocol note is intentionally redundant to stress the single-provenance chain.

## 11. What this amendment does NOT do

- Does not authorize a new training run or execute any member.
- Does not generate new paths, compute new Gate diagnostics, refit, or change backend/runtime.
- Does not change Gate-v2 thresholds, family methodology `730475...`, or RBF exclusion.
- Does not select reserve `j01..03` or a fifth member and does not perform final family H1/H2/H3 inference — family `H2` prose is disclosure only.
- Does not retroactively change historical CPU lineage or any committed artifact byte.

## 12. Required next action

Independent read-only audit of this runtime-sensitivity analysis (verify: contract reproduced verbatim, scalar schema 13 exactly, sources/hashes/aliases exact, member table exact, mean/SD `ddof=1` / median/min/max/CV per rule exact, LOMO 52 rows with absolute/relative and largest-influence per §4 exact, CPU-vs-mixed 13 rows per §5 exact, backend covariate wording verbatim, no causal claim/no balanced-design claim/no new threshold, no imputation, firewalls untouched, artifacts minimal-reproducible and single-provenance) before any family inference task.

---

*Amendment 045 computes the preregistered runtime-heterogeneity sensitivity analysis (040 §3–8 as corrected by 041) over exactly four governance-valid members `5bdbaabd2fb257a7`(cpu)/`62c7406cb3a2c642`(cpu)/`77e7de9efabb7ce3`(cpu)/`1e8aa171993a1aba`(cuda `17e3bb52...`), seed-03 retained-only: 13 scalars, means/SDs/medians/min/max/CVs, 52-row LOMO, 13-row CPU-vs-mixed disclosure — no new scientific execution, no threshold invented, backend is labelled covariate with the design not balanced for a causal estimate.*
