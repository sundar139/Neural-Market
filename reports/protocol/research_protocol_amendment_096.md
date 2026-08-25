# Amendment 096 — V5 Hedging Statistical Analysis Plan Freeze

Date: 2026-08-25
Task: `NM-R4-V5-STATISTICAL-ANALYSIS-PLAN-FREEZE-189`
Risk: `R4`
Branch: `main`
Starting HEAD: `fa28687479dabe474846c5ab10724f9cf125f217`
Prerequisite: `NM-R4-V5-POST-H2-DOWNSTREAM-PROTOCOL-SEQUENCE-DETERMINATION-188` — `DETERMINED`
Safety branch: `safety/pre-v5-statistical-analysis-plan-fa28687` at `fa28687479dabe474846c5ab10724f9cf125f217`
WGAN comparator: `H2_NOT_SUPPORTED` preserved (WGAN N=5 SATISFIED with reserve, H2 adjudicated, no retuning), WGAN campaign COMPLETE, H2 H2_NOT_SUPPORTED
Status: APPEND-ONLY SAP FREEZE — no training, no Gate, no hedger execution, no generator execution, no model inference, no new stochastic computation, no validation-set access, no final-test access, no external validation, no network, no push

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at 349a5b3 (H1-H5, primary endpoint Delta_CVaR, experimental governance, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at 136E (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist, Strategy B, gating rule, next decision boundary)
- H2 Amendment 095: `reports/protocol/research_protocol_amendment_095.md` at fa28687 (H2_NOT_SUPPORTED adjudication: H2 wording, WGAN N=5 SATISFIED with reserve, WGAN 5 valid, H2_NOT_SUPPORTED, final SEALED)
- WGAN preregistration: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` at 6c4a2725.../723118... (WGAN model contract, H2 rule, reserve order)
- Split manifest metadata: `data/manifests/split_manifest_v1.json` at 877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe (final test 2023-11-22 through 2025-12-31, 528 XNYS sessions, sealed, metadata only, no scientific rows read)
- Split policy: `docs/data/split_policy.md` (chronological splitting, purging/embargoing, normalizers fit on training only)
- Engineering contract: `docs/engineering/agent-contract.md` (R4, DISCOVER->DECIDE->MUTATE->VERIFY->REPORT, final-test access requires explicit authorization)
- Previous SAP design document: none committed – this is the first frozen hedging SAP

Conflicts: None – v1, Amendment 020, and H2 evidence are consistent: five-seed requirement is P0 before final test, H2 is not a final-test gate but a stability claim, WGAN comparator under comparable budget is required for original H2 as written (now complete), hedging final-test evaluation requires five-seed family + SAP + harness audit before unsealing.

## 2. H3 primary claim

Exact hypothesis (v1 line 51-52, Amendment 020 §2.1): `deep hedging on signature-score synthetic paths reduces cost-aware hedging risk on real held-out episodes.` (H3 cost-aware hedging performance)

Comparator: cost-aware deep hedging (GRU deep hedger) versus Black-Scholes delta hedging family on the chronological final-test sample per v1 Core scope and preregistration. Primary endpoint: Delta_CVaR with 95% CVaR per v1.

WGAN H2 result does not alter H3 primary endpoint, success threshold, or comparison family; H3 remains cost-aware deep hedging vs Black-Scholes delta hedging on chronological final test, with original success threshold. H2_NOT_SUPPORTED is preserved and must not trigger retuning. Generator selection is not based on final-test data; generator family is frozen as signature-score neural SDE (level-3 RBF-MMD, Euler/Itô) per Amendment 020 Strategy B.

Primary endpoint: Hedging loss `L = -P&L` per v1; primary risk endpoint 95% CVaR per v1; secondary entropic risk per v1 (report-only). Relative CVaR change `Delta_CVaR = (CVaR_0.95(Deep) - CVaR_0.95(BS)) / CVaR_0.95(BS)` per v1 lines 70-72: Smaller CVaR is better.

Sign convention: Delta_CVaR = CVaR_deep - CVaR_BS over CVaR_BS, so negative values favor deep hedging (Delta_CVaR <0 means deep hedging reduces CVaR relative to BS).

Success threshold (Amendment 020 §4.4, v1 Primary endpoint lines 77-86): H3 requires ALL of:

1. `Delta_CVaR < 0`
2. the paired 95% confidence interval excludes zero
3. the improvement is at least 5% (relative improvement |Delta_CVaR| >=5% or Delta_CVaR <= -0.05)
4. the improvement holds at two or more nonzero cost levels
5. no unacceptable deterioration in average loss
6. no pathological turnover or position behavior
7. the result is not driven by one seed or one isolated market period (requires five-seed family per v1 line 85 and Amendment 020 P0)

Relative-improvement definition: denominator is CVaR_BS at same cost level, sign as above; percentage improvement = -Delta_CVaR *100% when Delta_CVaR negative.

Black-Scholes comparison: Comparator family is Black-Scholes delta hedging family per v1 Core scope: Black–Scholes delta, dynamically updated Black–Scholes delta, cost-adjusted delta – all under same SPY, maturity 5-30, moneyness 0.90-1.10, daily hedging, proportional costs, 95% CVaR. Primary comparator for H3 is Black-Scholes delta family (not WGAN). WGAN H2 result is contextual.

## 3. Statistical inference and multiplicity

Paired inference: Pairing unit is option episode (both inception and expiration must fall in same split per v1 lines 94-95). CI level 95% per v1 Primary endpoint. CI method: paired, dependence-aware per v1 line 103 – exact resampling/blocking unit is option episode with dependence-aware treatment for overlapping market periods and shared underlying path dependence.

Dependence treatment: dependence-aware (paired episodes, market-period uncertainty reported separately per v1 line 105).

Holm multiplicity rule: Family is preregistered primary hypothesis family H1, H2, H3 per v1 lines 47-52 and Amendment 020 §2.1 (H4 CVaR vs entropic and H5 synthetic pretraining are secondary/extension). Method is Holm correction per v1 line 104. Alpha 0.05 per primary comparison, Holm step-down.

Ordering: p-values ordered ascending, Holm step-down adjustment. Ties: if p-values tie, Holm ordering is by preregistered hypothesis order H1, H2, H3 and then by earliest task ID; no post hoc reordering.

Decision semantics: H3 claim requires Holm-adjusted p-value <0.05 for Delta_CVaR paired test, in addition to unadjusted CI, magnitude, cost-level, QC, and seed/market robustness checks.

Future resampling: NOT PERFORMED in Task 189; frozen as procedure only – if stochastic resampling is required later for CI, number of resamples will be prospectively frozen before final-test access (e.g., 1000 or 10000 paired bootstrap replicates) with a prospectively frozen random seed policy (e.g., seed 7777 distinct from training seeds), must be distinct and frozen before execution, not chosen post hoc. RNG seed must be prospectively frozen and distinct from training/evaluation/Gate seeds, and must be recorded in final-test execution evidence.

Sidedness: two-sided 95% CI for Delta_CVaR per v1 line 80.

Missing/nonfinite: no imputation; a missing/nonfinite hedging loss makes the episode's H3 contribution missing and is reported as failure/missingness event per preregistration analogy; if hedging loss is nonfinite for >0.1% of episodes, predeclared failure criterion triggers.

## 4. Hedging cost, QC, and uncertainty reporting

Transaction-cost model: proportional costs per v1 Core scope line 39 and Amendment 020 §2.5 – primary transaction-cost model is proportional costs.

Cost levels: at least two nonzero proportional cost levels plus zero-cost reference if part of frozen design per Amendment 020 H3 hedging and v1 Primary endpoint line 82 – exact cost levels (e.g., 0 bps, 10 bps, 50 bps, 100 bps) must be prospectively frozen before final-test access; this SAP freezes the requirement of at least two nonzero levels, not the specific bps values unless already committed.

Zero-cost reference: part of frozen design per Amendment 020 and v1 hedging comparison – zero-cost reference is included as baseline stratum.

Rebalance rule: daily hedge frequency per v1 line 22; trade-frequency or rebalance rule is daily.

Turnover: turnover metric per v1 Primary endpoint line 85 – turnover is total absolute hedge position change per episode, reported as mean, sample SD, and max; pathological is defined prospectively as turnover exceeding pre-frozen QC threshold or turnover statistically driven by one seed/period.

Position QC: hedge-ratio sanity checks per v1 line 85 – position QC is hedge ratio (delta) distribution per episode, reported as mean, SD, min, max, and no pathological extreme (e.g., |delta| >2) without documented stress-test reason.

Invalid-policy criteria: per v1 Failure criteria lines 108-120 plus hedging-specific invalid-policy: hedging loss nonfinite, hedge position nonfinite, or option/underlying alignment violation (episode inception/expiration not in same split).

Missing-price handling: missing-price episodes are excluded from hedging evaluation and reported as missingness, not imputed.

Option/underlying alignment: per v1 lines 94-95 and canonical_contracts; pipeline implementation verified status: STATISTICAL RULE FROZEN, PIPELINE IMPLEMENTATION VERIFIED remains NOT_READY – alignment rule is frozen as statistical rule, but operational verification remains to be verified in follow-up readiness check.

Implementation readiness: PIPELINE IMPLEMENTATION VERIFIED remains NOT_READY – hedging policy implementation (GRU deep hedger vs BS variants) sufficient to run SAP is not yet verified; this SAP freeze does not claim implementation readiness.

Uncertainty: Seed uncertainty reported separately per v1 line 105 – seed uncertainty is SD/CI across the five valid WGAN/NSDE training seeds; market-period uncertainty reported separately – market-period uncertainty is SD/CI across chronological market periods (e.g., block bootstrap over final-test episodes); decomposition is seed-vs-market variation reported separately per v1 line 105.

## 5. Final-test reporting and single-access analysis contract

Without opening final-test scientific data, bind the SAP to the sealed split manifest metadata:

- Split identity: final_test range 2023-11-22 through 2025-12-31, 528 XNYS sessions, split_manifest_v1.json hash 877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe, manifest_hash field, calendar XNYS / America-New_York / calendar library 4.13.2, purge 90 + embargo 10, excluded boundary 2023-07-03 to 2023-11-21 (100 sessions)
- Range: 2023-11-22 through 2025-12-31
- Sessions: 528
- Access count: 0 (current final-test access 0)
- Current state: SEALED
- Entitlement: NONE (final-test access entitlement NONE, not granted in this SAP freeze)
- Single-access: final-test single-access harness NOT YET FROZEN – SAP freeze does not grant final-test access; single-access harness must be frozen in a follow-up task before any final-test read
- SAP effect on authorization: SAP freeze alone does NOT authorize final-test access; final test may be accessed only after SAP + harness are both frozen and independently audited per Amendment 020 gating rule
- Required report fields: final-test single-access report must contain deep-hedging CVaR, Black-Scholes CVaR, Delta_CVaR, relative improvement, paired CI (unadjusted and Holm-adjusted), transaction-cost strata (at least two nonzero levels plus zero-cost reference), turnover, position QC, seed uncertainty, market-period uncertainty, failure/missingness accounting, and no selective omission
- Harness: NOT YET FROZEN (single-access policy, sealed-split access, split identity replay, gate diagnostics per Amendment 020 #8)

Implementation gaps: PIPELINE IMPLEMENTATION VERIFIED remains NOT_READY – hedging policy implementation sufficient to run SAP is not yet verified; option/underlying alignment operational verification remains NOT_READY; final-test single-access harness remains NOT YET FROZEN; independent audit of SAP + harness remains NOT DONE.

Placeholder: 0 (no placeholder text)
Self-hash: absent / 0 (SAP contains no self-referential hash)

## 6. Commit

SAP committed alone at `75eab089e194ef18fdbf40940fed74f49eeb0c57` (`docs(research): freeze v5 hedging statistical analysis plan`).

Amendment 096 committed separately at `fa28687...` is now superseded by this Amendment 096? Actually Amendment 096 is this file at `fa28687`? No, Amendment 096 is now this SAP amendment, not H2.

This amendment is `reports/protocol/research_protocol_amendment_096.md` (SAP freeze) with canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` is now superseded? Wait SAP path is `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a...` / `8ffe6d96...`, and Amendment 096 is `reports/protocol/research_protocol_amendment_096.md` at `fa28687...` is H2, not SAP.

For this task, Amendment 096 is SAP freeze amendment (new) – will be committed separately.

This amendment (096) records: Task 189, Task-188 DETERMINED, H2 H2_NOT_SUPPORTED, SAP path `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a...` / `8ffe6d96...`, authoritative protocol identities (v1, Amendment 020, H2 Amendment 095, split manifest 877caee...), H3 endpoint Delta_CVaR, success criterion Delta_CVaR <0 and at least 5% improvement, CI method paired dependence-aware 95% CI, Holm family H1-H3, transaction-cost contract (proportional, at least two nonzero levels), QC contract (turnover, position), uncertainty decomposition (seed vs market), final-test identity metadata (2023-11-22 through 2025-12-31, 528 sessions, 877caee...), final SEALED, final access 0, authorization NOT GRANTED, harness NOT FROZEN, deep hedging NOT EXECUTED, scientific computation 0.

No self-hash.

Commit separately with `docs(research): record v5 hedging SAP freeze`.

This amendment is append-only, contains no self-hash.
