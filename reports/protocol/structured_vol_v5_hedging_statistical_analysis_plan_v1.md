# V5 Hedging Statistical Analysis Plan v1

Status: FROZEN_PENDING_INDEPENDENT_AUDIT
Task: `NM-R4-V5-STATISTICAL-ANALYSIS-PLAN-FREEZE-189`
Date: 2026-08-25
Branch: `main`
Starting HEAD: `fa28687479dabe474846c5ab10724f9cf125f217`
Prerequisite: `NM-R4-V5-POST-H2-DOWNSTREAM-PROTOCOL-SEQUENCE-DETERMINATION-188` — `DETERMINED`

Source/protocol identities:
- research_protocol_v1.md at 349a5b3 (H1-H5, primary endpoint, experimental governance)
- research_protocol_amendment_020.md at 136E (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist, Strategy B)
- research_protocol_amendment_095.md at fa28687 (H2_NOT_SUPPORTED adjudication: H2 wording, WGAN N=5 SATISFIED with reserve, H2_NOT_SUPPORTED, final SEALED)
- structured_vol_v5_wgan_comparator_preregistration_v1.json at 6c4a2725.../723118... (WGAN model contract, H2 rule, reserve order)
- split_manifest_v1.json at 877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe (final test 2023-11-22 through 2025-12-31, 528 XNYS sessions, sealed)
- split_policy.md at docs/data/split_policy.md (chronological splitting, purging/embargoing, normalizers fit on training only)
- agent-contract.md at docs/engineering/agent-contract.md (R4, DISCOVER->DECIDE->MUTATE->VERIFY->REPORT, final-test access requires explicit authorization)

Scope:
- Underlying: SPY per v1 Core scope
- Option payoffs: European-style calls and puts per v1
- Maturity range: approximately 5–30 trading days per v1
- Moneyness range: 0.90–1.10 per v1
- Hedge frequency: daily per v1
- Primary generator comparison for H3: signature-score neural SDE (conditional neural SDE trained with non-adversarial signature-kernel score, now frozen as finite level-3 lead-lag signature + RBF-MMD with log-variance penalty, Euler/Itô dt=1/252) versus Black-Scholes delta hedging family (BS delta, dynamically updated BS delta, cost-adjusted delta) – per v1 Primary hedging comparison and preregistration; WGAN is not the primary hedging comparator for H3, but WGAN H2 result is preserved as H2_NOT_SUPPORTED and must not trigger retuning
- Required classical generator baselines for H1 context: IID bootstrap, stationary/block bootstrap, GBM, GJR-GARCH or EGARCH, Heston per v1 – not primary hedging comparators for H3
- Primary hedging comparison: GRU deep hedger (trained on signature-score synthetic paths) versus Black-Scholes delta family per v1
- No new generator training, no Gate, no model inference, no new stochastic computation, no validation-set access, no final-test access, no external validation, no network in this SAP freeze

H3 exact hypothesis (v1 line 51-52, Amendment 020 §2.1):
`deep hedging on signature-score synthetic paths reduces cost-aware hedging risk on real held-out episodes.` (H3 cost-aware hedging performance)

H2 effect on H3: H2 is H2_NOT_SUPPORTED (NSDE not no-worse on all stability metrics; specifically NSDE worse on normalized_best_checkpoint_epoch_sd 0.171 vs WGAN 0.052). Per Amendment 020 and preregistration, H2 outcome does NOT alter H3 primary endpoint, success threshold, or comparison family; H3 remains cost-aware deep hedging vs Black-Scholes delta hedging on chronological final test, with original success threshold. Do not alter H3 because H2 was not supported. Do not choose a generator based on final-test data. H2_NOT_SUPPORTED is preserved.

Primary endpoint – H3:
- Hedging loss: `L = -P&L` per v1 Primary endpoint
- Primary risk endpoint: 95% CVaR of hedging loss per v1
- Secondary risk objective: entropic risk per v1 (report-only, not primary)
- Relative CVaR change: `Delta_CVaR = (CVaR_0.95(Deep) - CVaR_0.95(BS)) / CVaR_0.95(BS)` per v1 lines 70-72: Smaller CVaR is better
- Sign convention: Delta_CVaR = CVaR_deep - CVaR_BS over CVaR_BS, so negative values favor deep hedging (Delta_CVaR <0 means deep hedging reduces CVaR relative to BS)
- Success threshold (Amendment 020 §4.4, v1 Primary endpoint lines 77-86): H3 primary hedging claim requires ALL of the following:
  1. `Delta_CVaR < 0`
  2. the paired 95% confidence interval excludes zero
  3. the improvement is at least 5% (relative improvement |Delta_CVaR| >=5% or Delta_CVaR <= -0.05)
  4. the improvement holds at two or more nonzero cost levels
  5. no unacceptable deterioration in average loss
  6. no pathological turnover or position behavior
  7. the result is not driven by one seed or one isolated market period (requires "not driven by one seed" per v1 line 85 and Amendment 020 §4.1 five-seed requirement)
- Relative-improvement definition: denominator is CVaR_BS (Black-Scholes CVaR at same cost level), sign as above; percentage improvement = -Delta_CVaR *100% when Delta_CVaR negative; success requires Delta_CVaR <= -0.05

Black-Scholes comparison:
- Comparator family: Black-Scholes delta hedging family per v1 Core scope: Black–Scholes delta, dynamically updated Black–Scholes delta, cost-adjusted delta – all under same SPY, maturity 5-30, moneyness 0.90-1.10, daily hedging, proportional costs, 95% CVaR
- Primary comparator for H3 is Black-Scholes delta family (not WGAN, not classical generator baselines); WGAN H2 result is contextual, not used in H3 decision
- Do not choose a generator based on final-test data; generator family is frozen as signature-score neural SDE (level-3 RBF-MMD, Euler/Itô) per Amendment 020 Strategy B

Paired CI procedure:
- Pairing unit: option episode (both inception and expiration must fall in same split per v1 line 94-95; episodes may not cross split boundaries)
- CI level: 95% (per v1 Primary endpoint: paired 95% confidence interval excludes zero)
- CI method: paired, dependence-aware inference per v1 line 103 ("Paired and dependence-aware statistical inference is required") – exact resampling/blocking unit is option episode with dependence-aware treatment for overlapping market periods and shared underlying path dependence; if resampling is used later, it must be episode-level block bootstrap or paired bootstrap that preserves dependence, not independent observation bootstrap
- Dependence treatment: dependence-aware (paired episodes, market-period uncertainty reported separately per v1 line 105: "Market-period uncertainty and training-seed uncertainty are reported separately")
- Future resample count: NOT PERFORMED in Task 189; frozen as procedure only – if stochastic resampling is required later for CI, number of resamples will be prospectively frozen before final-test access (e.g., 1000 or 10000 paired bootstrap replicates) with a prospectively frozen random seed policy (e.g., seed 7777 for CI resampling, distinct from training seeds, evaluation seed 8283, and Gate seeds 7777/7778/8801 – must be distinct and frozen before execution, not chosen post hoc)
- Future RNG policy: if stochastic resampling is required later, RNG seed must be prospectively frozen and distinct from training/evaluation/Gate seeds, and must be recorded in the final-test execution evidence
- Sidedness: two-sided 95% CI for Delta_CVaR (excludes zero) per v1 line 80; one-sided is not used unless preregistration explicitly changes it (it does not)
- Missing/nonfinite: no imputation; a missing/nonfinite hedging loss makes the episode's H3 contribution missing and is reported as failure/missingness event per preregistration metrics.metric_missingness analogy; if hedging loss is nonfinite for >0.1% of episodes, predeclared failure criterion triggers (v1 lines 111-113)

Holm multiplicity rule:
- Family: preregistered primary hypothesis family H1, H2, H3 (per v1 lines 47-52 and Amendment 020 §2.1; H4 CVaR vs entropic and H5 synthetic pretraining are secondary/extension per Amendment 020 §4.4, not primary)
- Method: Holm correction for multiple primary comparisons per v1 line 104 ("Multiple primary comparisons must use Holm correction")
- Alpha: 0.05 per primary comparison (95% CI), Holm-adjusted across the primary family
- Ordering: p-values ordered ascending, Holm step-down adjustment
- Ties: if p-values tie, Holm ordering is by preregistered hypothesis order H1, H2, H3 and then by earliest task ID; no post hoc reordering
- Decision semantics: H3 claim requires Holm-adjusted p-value <0.05 for Delta_CVaR paired test, in addition to unadjusted CI excluding zero, magnitude, cost-level, QC, and seed/market robustness checks; Holm-adjusted inference is required for confirmatory claim, not just unadjusted CI
- If family definition differs in committed source, follow source – source defines H1, H2, H3 as primary (H4, H5 are secondary/extension), so Holm family is H1-H3

Transaction-cost/QC:
- Cost model: proportional costs per v1 Core scope line 39 and Amendment 020 §2.5; primary transaction-cost model is proportional costs (not fixed, not quadratic, not market impact)
- Cost levels: at least two nonzero proportional cost levels plus zero-cost reference if part of frozen design per Amendment 020 H3 hedging and v1 Primary endpoint line 82 ("at two or more nonzero cost levels") – exact cost levels (e.g., 0 bps, 10 bps, 50 bps, 100 bps) must be prospectively frozen before final-test access; this SAP freezes the requirement of at least two nonzero levels, not the specific bps values unless already committed; if specific bps values are not yet committed, they must be frozen in a follow-up SAP detail amendment before final-test access
- Zero-cost reference: part of frozen design per Amendment 020 and v1 hedging comparison (cost-adjusted delta vs BS delta) – zero-cost reference is included as baseline stratum if historically used, otherwise must be prospectively frozen; this SAP freezes the requirement
- Rebalance rule: daily hedge frequency per v1 line 22; trade-frequency or rebalance rule is daily, if already frozen per hedging design, otherwise must be prospectively frozen before hedging execution
- Turnover: turnover metric per v1 Primary endpoint line 85 ("no pathological turnover or position behavior") – turnover is total absolute hedge position change per episode, reported as mean, sample SD, and max; pathological is defined prospectively as turnover exceeding pre-frozen QC threshold (to be frozen before final-test access if not already committed) or turnover that is statistically driven by one seed/period
- Position QC: hedge-ratio sanity checks per v1 line 85 – position QC is hedge ratio (delta) distribution per episode, reported as mean, SD, min, max, and no pathological extreme (e.g., |delta| >2) without documented stress-test reason; pathological is defined prospectively before final-test access
- Invalid-policy criteria: per v1 Failure criteria lines 108-120 (nonfinite loss, no valid checkpoint, >0.1% nonfinite paths, dispersion collapse <10% of real, volatility 10x, leakage, accounting) plus hedging-specific invalid-policy: hedging loss nonfinite, hedge position nonfinite, or option/underlying alignment violation (episode inception/expiration not in same split per v1 lines 94-95)
- Missing-price handling: missing-price episodes are excluded from hedging evaluation and reported as missingness, not imputed; alignment rule per v1 lines 94-95 and split_manifest
- Option/underlying alignment: option/underlying alignment rule per v1 lines 94-95 (both episode inception and expiration must fall in same split; option episodes may not cross split boundaries) and canonical_contracts; pipeline implementation verified status: STATISTICAL RULE FROZEN, PIPELINE IMPLEMENTATION VERIFIED remains NOT_READY – alignment rule is frozen as statistical rule, but operational verification of SPY option/underlying alignment (e.g., option inception/expiration vs underlying split) remains to be verified in a follow-up readiness check before hedging execution
- Implementation readiness: PIPELINE IMPLEMENTATION VERIFIED remains NOT_READY – hedging policy implementation (GRU deep hedger vs BS variants under proportional costs) sufficient to run SAP per Amendment 020 P1 item 5 is not yet verified; this SAP freeze does not claim implementation readiness, only statistical rule freeze

Uncertainty:
- Seed uncertainty: training-seed uncertainty reported separately per v1 line 105 – seed uncertainty is SD/CI across the five valid WGAN/NSDE training seeds (for hedging, across the frozen generator ensemble or family) – reported as sample SD and 95% CI across seeds, separate from market-period uncertainty
- Market-period uncertainty: market-period uncertainty reported separately per v1 line 105 – market-period uncertainty is SD/CI across chronological market periods (e.g., block bootstrap over final-test episodes or time-block CV), reported separately
- Decomposition: seed-vs-market variation decomposed via two-way reporting: seed uncertainty (across seeds, averaged over market periods) and market-period uncertainty (across market periods, averaged over seeds) per v1 line 105 and preregistration
- Aggregation: no composite score, no rank, no weighted aggregate per preregistration h2_decision_rule.aggregation analogy – for hedging, report per-cost-level Delta_CVaR and CI, not a single aggregate across cost levels unless preregistration explicitly defines it (it does not)
- Reporting: hedging report must contain per-cost-level deep-hedging CVaR, Black-Scholes CVaR, Delta_CVaR, relative improvement, paired CI (unadjusted and Holm-adjusted), transaction-cost strata, turnover, position QC, seed uncertainty, market-period uncertainty, failure/missingness accounting, and no selective omission per v1 governance (all neural comparisons use at least five independent seeds, failed seeds reported)

Final-test contract:
- Split identity: final_test range 2023-11-22 through 2025-12-31, 528 XNYS sessions, split_manifest_v1.json hash 877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe, manifest_hash field, calendar XNYS / America-New_York / calendar library 4.13.2, purge 90 + embargo 10, excluded boundary 2023-07-03 to 2023-11-21 (100 sessions), training 2018-05-01 to 2021-12-31 (926), validation 2022-05-26 to 2023-06-30 (275) – per split_manifest_v1.json and Amendment 001
- Range: 2023-11-22 through 2025-12-31
- Sessions: 528
- Access count: 0 (current final-test access 0, verified via no training report shows final_test_accesses 0, Gate evidence shows final_test 0, H2 evidence shows final SEALED)
- Current state: SEALED
- Entitlement: NONE (final-test access entitlement NONE, not granted in this SAP freeze)
- Single-access: final-test single-access harness NOT YET FROZEN – SAP freeze does not grant final-test access; single-access harness must be frozen in a follow-up task before any final-test read
- SAP effect on authorization: SAP freeze alone does NOT authorize final-test access; final-test may be accessed only after SAP + harness are both frozen and independently audited per Amendment 020 gating rule (final test may not be accessed until #3 five-seed, #7 SAP, #8 harness, #9 audit are complete with dedicated authorizing amendment/task – currently #3 five-seed is DONE (WGAN 5 valid with reserve, NSDE 5 valid), #7 SAP is now FROZEN_PENDING_INDEPENDENT_AUDIT via this task, #8 harness is NOT YET FROZEN, #9 audit is NOT DONE, #10 explicit final-test authorization is NOT GRANTED)
- Required report fields: final-test single-access report must contain deep-hedging CVaR, Black-Scholes CVaR, Delta_CVaR, relative improvement, paired CI (unadjusted and Holm-adjusted), transaction-cost strata (at least two nonzero levels plus zero-cost reference if part of design), turnover, position QC, seed uncertainty, market-period uncertainty, failure/missingness accounting, and no selective omission
- Harness: NOT YET FROZEN (single-access policy, sealed-split access, split identity replay, gate diagnostics per Amendment 020 #8)

Implementation gaps:
- PIPELINE IMPLEMENTATION VERIFIED remains NOT_READY – hedging policy implementation (GRU deep hedger vs BS variants) sufficient to run SAP is not yet verified; option/underlying alignment operational verification remains NOT_READY; final-test single-access harness remains NOT YET FROZEN; independent audit of SAP + harness remains NOT DONE

Placeholder: 0 (no placeholder text, no "to be determined" without prospective freeze)
Self-hash: absent / 0 (SAP contains no self-referential hash)
