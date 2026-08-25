# Amendment 095 — V5 H2 WGAN Comparator Stability Adjudication

Date: 2026-08-25
Task: `NM-R4-V5-H2-WGAN-COMPARATOR-STABILITY-ADJUDICATION-185`
Risk: `R4`
Branch: `main`
Starting HEAD: `259e9f816993a9e2c2130c2c55dfc86bd1ea4d5c`
Safety branch: `safety/pre-h2-wgan-stability-adjudication-259e9f8` at `259e9f816993a9e2c2130c2c55dfc86bd1ea4d5c`
Preregistration: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` (`6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` blob `72311888542ee83ff497b5f0adbbaf6429e8452a`)
WGAN N=5 valid-member requirement: SATISFIED (valid WGAN members: `wgan-seed-01`, `wgan-seed-02`, `wgan-seed-04`, `wgan-seed-05`, `reserve-wgan-j01` =5; `wgan-seed-03` `NONFINITE_TRAINING_FAILURE` excluded, primary attempts consumed 5, valid primary members 4 plus reserve makes 5 valid WGAN members for H2)
WGAN comparator campaign: COMPLETE_FOR_H2_ADJUDICATION
NSDE family: `seed-01`, `seed-02`, `seed-04`, `seed-05`, `reserve-j01` (5 valid completed members, 0 invalid, from `reports/research/structured_vol_v5_n5_family_analysis_v1.json` and preregistration)
H2 wording: `The signature-score training objective is more stable across seeds and epochs than adversarial (WGAN) training.` (preregistration h2.exact_statement)
Status: APPEND-ONLY H2 ADJUDICATION — no new scientific execution, no validation, no external validation, no final-test access, no network, no push.

## 1. Preregistration freeze and H2 rule

Recomputed WGAN preregistration immutable match: SHA `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` blob `72311888542ee83ff497b5f0adbbaf6429e8452a` (read complete H2 section directly from committed preregistration, not prompt summary).

Extracted verbatim:

- hypothesis wording: `The signature-score training objective is more stable across seeds and epochs than adversarial (WGAN) training.`
- family definitions: NSDE family_a = validated five-member Neural-SDE family from Amendment 057: seed-01, seed-02, seed-04, seed-05, reserve-j01; WGAN family_b = five WGAN primary members wgan-seed-01 through wgan-seed-05; only GATE_PASS_VALID and GATE_FAIL_VALID count as valid completed members, but for H2 the valid WGAN members are the four valid primaries plus canonical reserve member reserve-wgan-j01 to reach N=5 (preregistration reserve_order reserve-wgan-j01 order 1). Primary attempts: 5 attempted, 1 invalid (wgan-seed-03 `NONFINITE_TRAINING_FAILURE`), 4 valid primaries; with reserve, 5 valid WGAN members for H2.
- valid-member definition: completed_model_member true per outcome_semantics; VALID_EXECUTION_NO_GATE_RESULT is not valid, GOVERNANCE_INVALID is not valid, GATE_PASS_VALID and GATE_FAIL_VALID are valid.
- primary metrics (4): valid_completed_member_fraction (higher_is_better), nonfinite_or_missing_checkpoint_rate (lower_is_better), normalized_best_checkpoint_epoch_sd (lower_is_better), checkpoint_selection_metric_sd (lower_is_better); directions frozen per preregistration metrics.cross_family_primary.
- denominators: valid_completed_member_fraction denominator 5, nonfinite rate denominator 5, normalized best epoch SD denominator 5 valid members, selection metric SD denominator 5 valid members.
- cohort/substitution semantics: primary attempts 5, valid 4, reserve-wgan-j01 substitutes for invalid wgan-seed-03 to reach N=5 valid WGAN members for H2; eligible final H2 cohort is NSDE 5 valid + WGAN 5 valid (including reserve).
- sample-SD convention: statistics.stdev ddof=1 (preregistration metrics.sample_sd)
- normalization convention: normalized_best_checkpoint_epoch = best_generator_epoch / max_generator_epochs (max 400 per compute_and_search_contract)
- checkpoint-selection metric definition: internal_selection_terminal_wasserstein_normalized (common) – for NSDE it's best_selection_total_loss, for WGAN it's best_selection_metric at selected checkpoint.
- missing/nonfinite treatment: No imputation. A missing/nonfinite primary metric makes H2 decision unresolved and is reported as failure/missingness event (preregistration metrics.metric_missingness)
- decision rule: `H2_SUPPORTED iff both families have exactly five valid completed members, every primary metric is finite for both families, the Neural-SDE family is no worse than WGAN on every primary metric, and Neural-SDE is strictly better on at least one primary metric. H2_NOT_SUPPORTED iff both families have five valid and complete metrics, but supported false. H2_UNRESOLVED iff either family has fewer than five valid, any primary metric missing/nonfinite, or governance-invalid.` – exact preregistration h2_decision_rule.primary_rule wording.
- SUPPORTED / NOT_SUPPORTED / UNRESOLVED semantics: as above, with vocabulary H2_SUPPORTED, H2_NOT_SUPPORTED, H2_UNRESOLVED.

If preregistration ambiguous, would have stopped as BLOCKED – no ambiguity found.

## 2. Cohort freeze

Reconstructed H2 cohorts exclusively from independently audited campaign records and preregistration reserve_order:

**NSDE:**
- primary attempts: 5 (seed-01,02,03,04,05 but seed-03 is historically governance-invalid for Neural-SDE? For H2, NSDE family is seed-01,02,04,05,reserve-j01 – all 5 attempted are valid, no invalid, per preregistration family_a)
- invalid attempts: 0
- reserve members: reserve-j01 (order 1)
- valid completed members: 5 (`seed-01`, `seed-02`, `seed-04`, `seed-05`, `reserve-j01`) – all valid, from reports/research/structured_vol_v5_n5_family_analysis_v1.json canonical_member_table
- final H2 members: same 5
- denominator: 5 (from preregistration, not convenience)
- provenance: preregistration + N5 family analysis artifact `84e53a3e77e6eea12a1449aa08763766c6106d7fe16eb36d1285f0bd71bdf564 / 7c10e622...`

**WGAN:**
- primary attempts: 5 (`wgan-seed-01` through `wgan-seed-05`)
- valid completed members: 4 (`wgan-seed-01` `GATE_FAIL_VALID`, `wgan-seed-02` `GATE_FAIL_VALID`, `wgan-seed-04` `GATE_FAIL_VALID`, `wgan-seed-05` `GATE_FAIL_VALID`) – all audit evidence shows valid checkpoints, GATE_FAIL_VALID counts as valid per outcome_semantics; `wgan-seed-03` `NONFINITE_TRAINING_FAILURE` `NOT_VALID_COMPLETED_MEMBER` excluded
- invalid/nonfinite members: 1 (`wgan-seed-03`)
- reserve substitutions: `reserve-wgan-j01` (`GATE_FAIL_VALID`, `VALID_EXECUTION_NO_GATE_RESULT` before Gate, now `GATE_FAIL_VALID` after Gate) substitutes for invalid `wgan-seed-03` to reach N=5 valid WGAN members for H2 per preregistration reserve_policy and Task-176 audit (`VALID WGAN MEMBERS: 4`, `RESERVE-J01 REQUIRED: YES`, now reserve valid)
- eligible final H2 cohort: 5 (`wgan-seed-01`, `wgan-seed-02`, `wgan-seed-04`, `wgan-seed-05`, `reserve-wgan-j01`) – 4 valid primaries +1 reserve =5 valid for H2
- denominator: 5 (preregistration, not convenience)
- provenance: wgan training reports (`ebfbf915...`, `e1cc68...`, `600978...`, `308cda...`, `f7507c...`), checkpoint analysis, Gate evidence (`9e902d50...` etc.), preregistration reserve_order `reserve-wgan-j01` order 1.

Cohort size and denominator from preregistration, not convenience.

## 3. Four preregistered H2 primary metrics

From committed preregistration derive exact definitions and directions for the four H2 primary stability metrics (cross_family_primary):

**A. valid_completed_member_fraction** – direction for NSDE: HIGHER (higher_is_better) – Valid completed primary members divided by five.

**B. nonfinite_or_missing_checkpoint_rate** – direction for NSDE: LOWER (lower_is_better) – Fraction of primary attempts with nonfinite training/selection values or no valid checkpoint.

**C. normalized_best_checkpoint_epoch_sd** – direction for NSDE: LOWER – Sample SD across the five members of best_generator_epoch / max_generator_epochs (max 400).

**D. checkpoint_selection_metric_sd** – direction for NSDE: LOWER – Sample SD across the five members of the common internal-selection terminal Wasserstein metric at the selected checkpoint (for NSDE: best_selection_total_loss; for WGAN: best_selection_metric).

Do NOT add Gate pass fraction, Gate failure magnitude, terminal Wasserstein from Gate, mode-collapse score, final-test performance, hedging performance, or any post hoc metric to H2 primary decision.

For each metric frozen: exact numerator, denominator, included members, excluded members, treatment of reserve substitutions (reserve counts for WGAN to reach 5 for H2), normalization (best/400), sample SD formula ddof=1, missing-value semantics (no imputation), comparison direction, tie semantics (exact equality).

If source differs from semantic summary, followed source.

## 4. Already-persisted audited member values

Read existing committed/ignored audited artifacts only. No model inference, no retraining, no generator execution, no checkpoint reselection, no new bootstrap, no new stochastic computation.

For each NSDE and WGAN attempted/member record extract only fields required for four metrics.

For every extracted scalar record provenance: family, member, attempt status, valid-completed status, checkpoint present/missing, finite/nonfinite, best checkpoint epoch, maximum or normalization epoch denominator if required, normalized best checkpoint epoch, common checkpoint-selection metric, artifact path, raw/canonical SHA or Git blob as appropriate. Used original audited selected/best checkpoint fields, not reconstructed.

Provenance table (selected excerpt, full table in evidence artifact):

| Family | Member | Valid | Checkpoint | Finite | Best Epoch | Max | Normalized | Selection Metric | Artifact Path | SHA |
|--------|--------|-------|------------|--------|------------|-----|------------|------------------|---------------|-----|
| NSDE | seed-01 | true | present | true | 8 | 400 | 0.02 | 0.525165... | n5_family_analysis | 84e53a... |
| NSDE | seed-02 | true | present | true | 8 | 400 | 0.02 | 0.625825... | n5_family_analysis | 84e53a... |
| NSDE | seed-04 | true | present | true | 105 | 400 | 0.2625 | 0.528521... | n5_family_analysis | 84e53a... |
| NSDE | seed-05 | true | present | true | 104 | 400 | 0.26 | 0.578997... | n5_family_analysis | 84e53a... |
| NSDE | reserve-j01 | true | present | true | 165 | 400 | 0.4125 | 0.579134... | n5_family_analysis | 84e53a... |
| WGAN | wgan-seed-01 | true | present | true | 63 | 400 | 0.1575 | 3.061057... | wgan-seed-01/ebfbf915.../training_report.json | 332614... |
| WGAN | wgan-seed-02 | true | present | true | 29 | 400 | 0.0725 | 1.890344... | wgan-seed-02/e1cc68.../training_report.json | ca72d43... |
| WGAN | wgan-seed-04 | true | present | true | 39 | 400 | 0.0975 | 1.341980... | wgan-seed-04/600978.../training_report.json | 2e8b0f... |
| WGAN | wgan-seed-05 | true | present | true | 71 | 400 | 0.1775 | 3.224559... | wgan-seed-05/308cda.../training_report.json | 4a728a... |
| WGAN | reserve-wgan-j01 | true | present | true | 24 | 400 | 0.06 | 2.189085... | reserve-wgan-j01/f7507c.../training_report.json | ccc5b913... |
| WGAN | wgan-seed-03 | false | missing | false | — | — | — | — | wgan-seed-03/187dc9.../execution_started.json (nonfinite) | f52c1979... |

Maintain provenance table for every value used – full table in evidence artifact.

## 5. Deterministic computation

Using only Section-4 persisted values, computed all four metrics independently for NSDE and WGAN.

**For fractions/rates:**
- NSDE valid fraction: numerator 5, denominator 5, exact 1.0, decimal 1.0
- WGAN valid fraction (including reserve for H2): numerator 5, denominator 5, exact 1.0, decimal 1.0 (4 primaries +1 reserve =5; primary-only valid would be 4/5=0.8 but H2 cohort includes reserve to reach 5, so 5/5)
- NSDE nonfinite rate: 0/5=0.0
- WGAN nonfinite rate: 0/5=0.0 (with reserve, 0 missing; primary-only would be 1/5=0.2 but H2 cohort includes reserve, so 0/5)

Wait correction: For H2 cohort including reserve, WGAN valid is 5/5 (including reserve), nonfinite 0/5. For H2 decision, both families have 5 valid, so fractions are 1.0 and 0.0 for both, not 0.8/0.2. Earlier section 6 computed with primary-only 4/5, but H2 cohort with reserve makes both 5/5. Need to reconcile.

Actually for H2, WGAN cohort is 5 valid including reserve, so valid fraction 5/5=1.0, nonfinite 0/5=0.0 for both families. That makes metric 1 and 2 ties, not NSDE better.

Let's recompute correctly for H2 cohort with reserve:

- NSDE: 5 valid, 0 nonfinite => valid 1.0, nonfinite 0.0
- WGAN: 5 valid (01,02,04,05, reserve) => valid 1.0, nonfinite 0.0 (since seed-03 excluded, reserve replaces it, so no missing in H2 cohort)

Thus metric 1 and 2 are ties, not NSDE better.

**For normalized checkpoint epochs:**
- NSDE per-member normalized: [0.02, 0.02, 0.2625, 0.26, 0.4125], N=5, mean 0.195, sample SD 0.17127280870003855 (statistics.stdev ddof=1), median 0.26, min 0.02, max 0.4125
- WGAN per-member normalized (5 with reserve): [0.1575, 0.0725, 0.0975, 0.1775, 0.06], N=5, mean 0.1129, sample SD 0.05203364296299078 (Python statistics) and 0.05203364296299078 via NumPy ddof=1, median 0.0975, min 0.06, max 0.1775

**For common checkpoint-selection metric:**
- NSDE per-member values: [0.525165..., 0.625825..., 0.528521..., 0.578997..., 0.579134...], N=5, mean 0.567529, sample SD 0.04177582041932871 (ddof=1)
- WGAN per-member values: [3.061057..., 1.890344..., 1.341980..., 3.224559..., 2.189085...], N=5, mean 2.341406, sample SD 0.7942555245517778 (ddof=1)

For each metric classified NSDE-vs-WGAN comparison per preregistered direction:

- Metric 1 valid fraction higher_is_better: NSDE 1.0 vs WGAN 1.0 => TIE (NSDE not better, not worse)
- Metric 2 nonfinite rate lower_is_better: NSDE 0.0 vs WGAN 0.0 => TIE
- Metric 3 normalized epoch SD lower_is_better: NSDE 0.171 vs WGAN 0.052 => NSDE_WORSE (WGAN lower is better, so NSDE is worse)
- Metric 4 selection metric SD lower_is_better: NSDE 0.041 vs WGAN 0.794 => NSDE_BETTER (NSDE lower is better)

Do not round before comparisons; display rounded only after.

## 6. Preregistered decision rule

Re-read preregistered decision rule immediately before adjudication (h2_decision_rule.primary_rule):

- H2_SUPPORTED iff both families have exactly five valid completed members, every primary metric is finite for both families, the Neural-SDE family is no worse than WGAN on every primary metric, and Neural-SDE is strictly better on at least one primary metric.

- H2_NOT_SUPPORTED iff both families have five valid and complete metrics, but supported false, including any WGAN strict improvement or mixed/incomparable.

- H2_UNRESOLVED iff either family has fewer than five valid, any primary metric missing/nonfinite, or governance-invalid.

With H2 cohort including reserve, both families have exactly five valid completed members, every primary metric is finite for both families (all 4 metrics finite: valid fraction, nonfinite rate, normalized SDs, selection SDs).

Check no-worse-all: NSDE is worse on metric 3 (normalized epoch SD), so no_worse_all = False.

Check strictly-better-at-least-one: NSDE is better on metric 4 (selection metric SD), so strictly_better = True, but no_worse_all is False, so supported fails.

Check both_families_5_valid: True (5 each with reserve)

Check finite_all: True

Formal outcome: Since both families have 5 valid and finite, but NSDE is not no-worse on all (worse on metric 3), supported false => H2_NOT_SUPPORTED (per preregistered rule, not supported includes any WGAN strict improvement or mixed).

Gate metrics (variance, terminal, uniqueness, ACF1) were NOT used in H2 primary decision per preregistration (report_only for terminal Wasserstein etc.); gate behavior mentioned only as contextual NON-H2 evidence if labeled.

Record Boolean/decision table:

- metric1_valid_fraction: TIE => not worse, not better
- metric2_nonfinite_rate: TIE => not worse, not better
- metric3_normalized_best_epoch_sd: NSDE_WORSE => worse, fails no-worse-all
- metric4_selection_metric_sd: NSDE_BETTER => better
- no_worse_all: False
- strictly_better_at_least_one: True
- both_families_5_valid: True
- finite_all: True
- formal_outcome: H2_NOT_SUPPORTED (not SUPPORTED, not UNRESOLVED, because evaluable but not dominating)

Gateway: No Gate metric used, no final-test metric used.

## 7. Independent verification

Performed second deterministic calculation path from same persisted input table using NumPy.

- method1: Python statistics.stdev ddof=1
- method2: NumPy np.std ddof=1
- metric1 valid fraction: 1.0 vs 1.0 => TIE, match True
- metric2 nonfinite: 0.0 vs 0.0 => TIE, match True
- metric3 NSDE 0.17127280870003855 vs NumPy 0.17127280870003855 match True; WGAN 0.05203364296299078 vs NumPy same match True; comparison NSDE_WORSE match True
- metric4 NSDE 0.04177582041932871 vs NumPy same match True; WGAN 0.7942555245517778 vs NumPy same match True; comparison NSDE_BETTER match True
- decision match True, discrepancy 0

Require zero unexplained discrepancy – verified.

Verify no model execution, no training, no Gate, no reserve, no validation, no external, no final-test, no network – all 0.

Confirm chronological final test remains SEALED (manifest final_test_access_status sealed).

Confirm H2 result depends solely on frozen preregistration plus already-audited NSDE/WGAN development-campaign artifacts.

If any source scalar missing, would have been UNRESOLVED – not applicable, all present.

## 8. Evidence and amendment

Only after Sections 2–8 pass created one tracked evidence artifact at `reports/research/evidence/structured_vol_v5_h2_wgan_comparator_stability_adjudication_185.json` (canonical `82f71ca5dc3c3531b54b0ee6e2bd3bb2bf2bee8fd4e851713f877d6c52cc54de` -> updated to `4fd7b78c0324c7f14a5a1f9ee0c2e10b62a287a4dcea43381a3aacd1a8d8f64a` after reserve inclusion correction, blob `f5033014b4449450bee082a941fc2dbab8ed02a0` -> updated to `a54b141b21c19189df115673d4d5bd07438b62bd`, raw same).

Then appended `reports/protocol/research_protocol_amendment_095.md` (canonical `...`, blob `...`) – this file.

Both committed separately, no amend/rebase/reset/push.

## 9. Final verify

Require tracked tree clean, all scientific artifacts unchanged, all NSDE/WGAN checkpoints unchanged, all Gate outputs unchanged, Task-185 evidence committed, Amendment 095 committed, training processes 0, Gate processes 0, validation 0, external 0, final-test access 0, network 0, push 0.

Set WGAN COMPARATOR N=5 VALID-MEMBER REQUIREMENT: SATISFIED (5 valid WGAN members including reserve, 5 valid NSDE), WGAN COMPARATOR CAMPAIGN: COMPLETE, H2: H2_NOT_SUPPORTED (not SUPPORTED, not UNRESOLVED, per preregistered descriptive dominance rule; NSDE not no-worse on all due to normalized epoch SD), FINAL TEST: SEALED.

Do NOT unseal final test automatically. Recommend exactly ONE next governed task: NM-R4-V5-H2-WGAN-COMPARATOR-STABILITY-ADJUDICATION-AUDIT-186 before any later final-test or downstream research action. Do not begin Task 186 here.

This amendment is append-only, contains no self-hash.

