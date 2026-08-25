# V5 Final-Test Single-Access Harness v1

Status: FROZEN_PENDING_INDEPENDENT_AUDIT
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-FREEZE-191`
Risk: `R4`
Date: 2026-08-25
Branch: `main`
Starting HEAD: `31226fcfc89f090eb1952f65ab37bddaf72fddca`
Safety branch: `safety/pre-v5-final-test-harness-31226fc` at `31226fcfc89f090eb1952f65ab37bddaf72fddca`
Prerequisite: `NM-R4-V5-STATISTICAL-ANALYSIS-PLAN-AUDIT-190` — prerequisite #7 SATISFIED

This task freezes the single-access harness contract only. It grants no final-test access entitlement. No final-test row access, no training, no hedger execution, no generator execution, no gate, no model inference, no scientific bootstrap/resampling execution, no validation, no external validation, no network, no push.

## 1. Authoritative bindings

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, primary endpoint Delta_CVaR, experimental governance, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist Strategy B, gating rule)
- H2 adjudication: `reports/protocol/research_protocol_amendment_095.md` at `fa28687` — H2 `H2_NOT_SUPPORTED` (WGAN N=5 SATISFIED with reserve, NSDE 5 valid, WGAN worse on normalized epoch SD)
- SAP v1: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9`
- Amendment 096 (SAP freeze): `reports/protocol/research_protocol_amendment_096.md` at canonical SHA `a80293300b14f06ae5a7f410088af96d32f82284de3fca1255adec26b1853c4b` Git blob `50340b489891d43284d8cadfd3452f43dfbebf75`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test `2023-11-22` through `2025-12-31`, 528 XNYS sessions, calendar XNYS `4.13.2` America/New_York, purge 90 + embargo 10, excluded boundary `2023-07-03` to `2023-11-21` 100 sessions, training `2018-05-01` to `2021-12-31` 926, validation `2022-05-26` to `2023-06-30` 275)
- Split policy: `docs/data/split_policy.md` (chronological, purging/embargoing, normalizers fit on training only)
- Engineering contract: `docs/engineering/agent-contract.md` (R4, DISCOVER->DECIDE->MUTATE->VERIFY->REPORT, final-test access requires explicit authorization)
- NSDE family source: `reports/research/structured_vol_v5_n5_family_analysis_v1.json` (5 valid members, 0 invalid)

H2 state: `H2_NOT_SUPPORTED` preserved. No retuning. No WGAN hedging role.

Final-test state at freeze: `SEALED`, access count `0`, entitlement `NONE`, authorization `NOT GRANTED`, harness prior `NOT FROZEN`, deep hedging `NOT READY`.

## 2. Harness-deferred field matrix

Every Task-190 harness-deferred field is now bound. Source-frozen vs prospectively frozen:

| Field | Source status before 191 | Frozen value in this harness | Rationale |
|---|---|---|---|
| Transaction-cost model | Source-frozen (proportional) | proportional per v1 line 39 | v1 normative |
| Exact transaction-cost levels | Deferred (at least two nonzero + zero ref) | `0 bps` (`0.0000`), `10 bps` (`0.0010`), `50 bps` (`0.0050`) proportional per trade notional | Exactly two nonzero levels, zero reference; 10 bps institutional baseline, 50 bps stressed; uses pre-final methodology literature, no final-data inspection |
| CI algorithm | Deferred (paired dependence-aware only) | Paired circular block bootstrap (CBB) over chronological episodes for Delta_CVaR | Preserves episode dependence from overlapping market periods, paired per episode |
| Resampling algorithm | Deferred (illustrative 1000 versus 10000) | Paired circular block bootstrap | Single concrete choice |
| Dependence/block rule | Deferred | Block-coupled: each resampled block draws paired `(L_Deep, L_BS)` per episode; blocks preserve chronological adjacency | Paired dependence preservation per v1 line 103 |
| Block construction | Deferred | Circular block bootstrap (wrap-around), blocks sampled with replacement, concatenated and truncated to N_episodes | Standard for stationary dependence; deterministic construction |
| Block length | Deferred | Fixed `L = 20` episodes (deterministic) | Covers max maturity 30 sessions plus overlap; ~1 month XNYS; not data-dependent; frozen before access |
| Resample count | Deferred (illustrative 1000 versus 10000) | `B = 10000` paired bootstrap replicates | Stable 95% tail quantiles |
| RNG seed (resampling) | Deferred (illustrative 7777) | `9491` (Python/NumPy Generator) | Distinct from training/eval/Gate seeds |
| Turnover threshold | Deferred (to be frozen before access) | Episode turnover `> 10.0` flagged; mean turnover `> 4.0` per cost level pathological | See Section 5 |
| Position threshold | Deferred (illustrative |delta| greater than 2) | `|delta| > 2.0` per-step flagged; episode max `|delta| > 2.0` pathological; mean `|delta| > 1.2` pathological | See Section 5 |
| Zero/nonfinite CVaR_BS denominator handling | Implicit | See Section 5: `CVaR_BS == 0` or nonfinite => Delta_CVaR undefined, report as `inf`/`nan` and treat episode/level as failure/missingness, not success; CI not computed for that level | No division-by-zero success |
| Missing-price behavior | Deferred (not imputed per SAP) | Exclude episode from H3 evaluation, count as missingness, report | Per SAP no imputation |
| Option/underlying alignment checks | Frozen as rule, pipeline NOT READY | Strict: inception and expiration must fall in same split, no cross-boundary episodes; tolerance `0` sessions; alignment violation => excluded as invalid-policy | v1 lines 94-95 |
| Maturity/moneyness filters | Frozen (5-30, 0.90-1.10) | Maturity `5` to `30` trading days inclusive; moneyness `0.90` to `1.10` inclusive; European calls/puts only; underlying SPY only | v1 Core scope |
| Generator-member aggregation | Deferred | Per-member policies: 5 independent NSDE synthetic path pools, each generator member yields its own hedger set; primary Delta_CVaR is mean across 5 generator members (each member collapsed as mean over its hedger seeds) | One concrete design, preserves seed uncertainty |
| Hedger seed schedule | Deferred | `3` hedger seeds: `31001`, `31002`, `31003` | Distinct from generator/model seeds |
| Hedger-seed aggregation | Deferred | Fully crossed: every generator member paired with every hedger seed => `5 x 3 = 15` GRU hedger policies; within-member mean over 3 hedger seeds, then cross-member mean |  |
| Generator-vs-hedger uncertainty hierarchy | Deferred | Primary seed uncertainty = SD across 5 generator-member Delta_CVaR means; secondary/report-only = SD across 15 individual policies and within-member hedger SD | Two-way separation |
| Market-period aggregation | Deferred | Market-period uncertainty = block-bootstrap 95% CI and SD across resampled chronological blocks (Section 4); reported separately from seed uncertainty per v1 line 105 |  |
| Black-Scholes comparator variants | Frozen family, primary deferred | Primary: `cost-adjusted Black-Scholes delta` (proportional costs same as deep hedger); secondary/report-only: `static Black-Scholes delta` (vol fixed at inception) and `dynamically updated Black-Scholes delta` (daily IV recalibration) | Section 7 |
| Numerical Holm set | Frozen family, numeric membership deferred | Numeric Holm set is `{H3}` only; H1 has no valid inferential p-value, H2 has no inferential p-value | Section 4 |
| Single-access state machine | Not frozen | `SEALED -> AUTHORIZED_SINGLE_ACCESS -> CONSUMED` fail-closed, see Section 8 |  |
| Failure-before-result semantics | Not frozen | Failure before result still consumes entitlement, see Section 8 |  |
| Retry/rerun semantics | Not frozen | No automatic retry/rerun/relaunch/second process/alternate policy, see Section 8 |  |
| Artifact/result persistence | Not frozen | Original execution output durably preserved, no post-hoc regeneration, full missingness accounting | Section 8 |

All harness constants are bound. No deferred values remain.

## 3. H3 endpoint

```
Delta_CVaR = (CVaR_0.95(Deep) - CVaR_0.95(BS)) / CVaR_0.95(BS)
```

- Hedging loss `L = -P&L` per v1 Primary endpoint.
- Primary risk endpoint: 95% CVaR of hedging loss per v1.
- Sign convention: negative Delta_CVaR favors deep hedging.
- Success requires ALL of SAP Section 2 conditions (Delta_CVaR <0, paired 95% CI excludes zero, improvement at least 5% i.e. Delta_CVaR <= -0.05, holds at both nonzero cost levels, no unacceptable deterioration in average loss, no pathological turnover or position behavior, not driven by one seed or one market period).
- Relative improvement = `-Delta_CVaR * 100%` when Delta_CVaR negative.
- Computed per cost level; no composite across cost levels.

## 4. Exact inference, resampling, and multiplicity implementation

### 4.1 Pairing and CI

- Pairing unit: option episode. Both inception and expiration must fall in same split per v1 lines 94-95. Episodes are the paired unit for `(L_Deep, L_BS)`. Episodes that cross split boundaries are invalid and excluded.
- Dependence-preserving CI method: paired circular block bootstrap over episodes sorted by inception date (chronological order). Each bootstrap replicate resamples blocks of consecutive episodes to preserve autocorrelation from overlapping market periods and shared underlying path dependence.
- Resampling method: paired circular block bootstrap (CBB) with replacement.
- Block construction: partition chronological episode sequence of length `N` into circular indices `0..N-1` with wrap-around. For each replicate, sample `ceil(N / L)` blocks of length `L` uniformly with replacement, concatenate blocks, truncate to `N` episodes. The paired Deep/BS losses move together per episode.
- Block length: fixed `L = 20` episodes. Deterministic before execution, not estimated from final data. Rationale: exceeds maximum option maturity (30 sessions) overlap window when mapped to episodes; captures market-period dependence without data snooping.
- Resample count: `B = 10000` paired bootstrap replicates. No alternative count.
- RNG seed: `9491` using NumPy `Generator(PCG64(9491))` for the bootstrap resampling only. Distinct from: model-init/data seeds for NSDE (`8281` series, `9281`, `11281`, `12281`, `13281`), evaluation seed `8283`, Gate seeds `7777`/`7778`/`8801`, and hedger seeds `31001`/`31002`/`31003`. Frozen before execution, recorded in result artifact.
- Confidence level: `95%`.
- Sidedness: two-sided 95% CI for Delta_CVaR. CI excludes zero is the success condition. Equivalent two-sided p-value computed from bootstrap distribution (proportion of replicates with Delta_CVaR >=0 or <=0, two-sided).
- Alpha: `0.05` per primary comparison; Holm-adjusted across numeric family at same alpha.
- Failure on insufficient effective sample: if `N < 2*L` (i.e., fewer than 40 episodes) or fewer than `2` distinct blocks or effective resampled CVaR denominator has >10% missing/nonfinite episodes, the CI procedure reports `INSUFFICIENT_SAMPLE` and H3 is not claimed. No fallback to i.i.d. bootstrap.
- Missing/nonfinite handling: no imputation. An episode with missing underlying/option price, missing BS inputs, nonfinite hedge position, or nonfinite hedging loss is excluded from that cost level's CVaR and counted as missingness. If `>0.1%` of episodes at a cost level have nonfinite hedging loss, predeclared failure criterion triggers (v1 lines 111-113). If BS CVaR is zero or nonfinite at a cost level, Delta_CVaR is undefined (`nan`/`inf`) and that level cannot satisfy success.

### 4.2 Holm multiplicity

- Conceptual primary family: `{H1, H2, H3}` per v1 lines 47-52 and Amendment 020 section 2.1. H4 (CVaR vs entropic) and H5 (synthetic pretraining) are secondary/extension and not in the primary Holm family.
- H1 p-value availability: NONE. H1 (generator fidelity) was evaluated descriptively on external validation with per-family ranks, no preregistered inferential p-value, no significance test. No valid H1 inferential p-value exists for hedging final-test Holm.
- H2 p-value availability: NONE. H2 was descriptive stability comparison per preregistration `6c4a2725...` section `significance`: no significance test, no p-value, no CI. H2_NOT_SUPPORTED is descriptive. H2 has no inferential p-value and must not receive one after the fact.
- H3 p-value availability: VALID. Paired block-bootstrap p-value for Delta_CVaR is the sole preregistered inferential p-value available for the hedging confirmatory analysis.
- Numeric Holm set: `{H3}` only. Adjusted p-value equals raw p-value (`p_Holm(H3) = p_raw(H3)`).
- H2 numerical participation: H2 is descriptive primary hypothesis, recorded in family reporting but excluded from numeric Holm adjustment. H2 does not enter the Holm ordering or alpha calculation.
- Method: Holm step-down at family alpha `0.05`.
- Ordering: p-values ordered ascending. Ties: if p-values tie, Holm ordering is by preregistered hypothesis order `H1, H2, H3` then by earliest task ID. With singleton set, ordering is trivial.
- Adjusted-alpha procedure: for ordered p-values `p(1) <= p(2) <= ... <= p(k)`, Holm threshold for rank `i` is `alpha / (k - i + 1)`. With `k=1`, threshold is `0.05`. Step-down stops at first non-rejection.
- H3 adjusted rule: confirmatory H3 claim requires Holm-adjusted `p < 0.05` (with `k=1` this equals raw `p < 0.05`) in addition to CI excluding zero, magnitude, cost-level, QC, and seed/market robustness checks.
- Do not invent missing H1/H2 p-values. Numeric report must state H1/H2 p-values as `NOT_AVAILABLE_DESCRIPTIVE_ONLY`.

## 5. Exact transaction-cost, QC, and eligibility constants

### 5.1 Transaction costs

- Cost model: proportional costs per v1 Core scope line 39. Not fixed, not quadratic, not market-impact.
- Exact cost levels (3 strata):
  - `C0 = 0 bps` = `0.0000` per unit notional per trade (zero-cost reference)
  - `C1 = 10 bps` = `0.0010`
  - `C2 = 50 bps` = `0.0050`
  Requires both `C1` and `C2` nonzero levels to satisfy success; `C0` is reference stratum.
- Cost application: proportional cost incurred on absolute change in hedge position `|delta_t - delta_{t-1}|` times underlying price at `t`, accumulated per episode. Same cost accounting for Deep and BS comparators at each level.
- Rebalance rule: daily hedge frequency. Position held constant within session, rebalanced at close to target delta. No intraday rebalancing. Alignment with v1 line 22.
- Cost handling for BS: primary cost-adjusted BS delta applies same proportional cost model and daily rebalance as Deep. Secondary BS variants use same costs for comparability.

### 5.2 Turnover

- Turnover formula per episode:
  ```
  turnover_episode = sum_{t=1}^{T} |delta_t - delta_{t-1}|
  ```
  where `delta_0 = 0` before inception, `delta_t` is hedge ratio at close of day `t`, `T` is number of hedging days in episode (maturity length). Reported per cost level as mean, sample SD (ddof=1), max, median across episodes.
- Pathological-turnover threshold (prospectively frozen):
  - Per-episode flag: `turnover_episode > 10.0` (more than 10 notional-equivalent absolute delta changes in a 5-30 day episode, indicating excessive churn).
  - Per-level flag: `mean(turnover_episode) > 4.0` at any cost level.
  - If `>5%` of episodes at a cost level exceed the per-episode threshold, that level is flagged pathological.
  Pathological turnover at any cost level blocks H3 success regardless of Delta_CVaR.

### 5.3 Position / hedge-ratio definition

- Position/hedge-ratio definition: `delta_t` is the hedging strategy's target holding in underlying per unit option notional (shares per option underlying unit). For calls/puts this is the model delta; for BS it is Black-Scholes delta; for Deep it is GRU network output. Bounded reporting as raw model output, not clipped before thresholding.
- Nonfinite hedge-position rule: any episode containing a nonfinite `delta_t` at any hedging step is an invalid-policy episode for that strategy, excluded from CVaR for that level and counted as failure/missingness. If nonfinite positions affect `>0.1%` of episodes for a strategy, that strategy's level is failed.
- Pathological-position threshold (prospectively frozen):
  - Per-step flag: `|delta_t| > 2.0` at any time step (leverage beyond 2x notional).
  - Per-episode flag: `max_t |delta_t| > 2.0`.
  - Per-level flag: `mean_t mean(|delta_t|) > 1.2` across episodes (average leverage >1.2).
  - If `>1%` of episodes have a per-episode flag, that level is flagged pathological.
- No post hoc clipping to hide pathological positions.

### 5.4 CVaR denominator, missingness, alignment, eligibility

- CVaR_BS zero/nonfinite denominator rule: if `CVaR_0.95(BS)` is `0`, `nan`, `inf`, `-inf`, or absolute value `< 1e-12` at a cost level, then `Delta_CVaR` is undefined for that level. Report `Delta_CVaR = nan`, `CI = [nan, nan]`, `p = nan`, and that level cannot count toward the "two or more nonzero cost levels" success condition. Do not substitute a small epsilon to obtain a significant ratio.
- Missing-price rule: any episode with a missing underlying close, missing option quote, missing implied-vol input, or `RejectedRecord` (crossed quote, `ask < bid`, missing side, unadjusted price misuse) is excluded from hedging evaluation for that strategy/level. Counted as missingness, not imputed, not carried forward. Missingness rate reported per cost level.
- Nonfinite hedging-loss rule: hedging loss `L = -P&L`. If `L` is nonfinite (`nan`/`inf`) for an episode, that episode is missing for that strategy/level and triggers the invalid-policy criteria per v1 lines 108-120. If `>0.1%` of episodes are nonfinite for a strategy/level, the predeclared failure criterion triggers and H3 cannot be claimed at that level.
- Episode-exclusion/failure-accounting rule: all excluded, invalid, missing, or nonfinite episodes are enumerated per cost level with counts and rates, by reason (alignment violation, missing price, nonfinite position, nonfinite loss, threshold breach). No selective omission. Full denominator `N` and valid count reported.
- Same-split inception/expiration requirement: both option episode inception date and expiration date must fall within the same split (final test `2023-11-22` to `2025-12-31`). Episodes crossing split boundaries (`training <-> validation <-> final`) are invalid and excluded. Tolerance `0` sessions; strict calendar containment using XNYS session membership.
- SPY option eligibility: underlying `SPY` only. Option type `call` or `put`, European-style only. American/weekly non-standard exercise styles excluded even if SPY-listed. Point-in-time option definition must exist at inception.
- Maturity filter: `5` to `30` trading days inclusive (`T` in `[5, 30]` XNYS sessions from inception to expiration inclusive of inception, exclusive of expiration hedging end). Episodes outside this range excluded.
- Moneyness filter: `0.90` to `1.10` inclusive, defined as `S_inception / K` where `S_inception` is underlying close at inception, `K` is strike. Both ITM/OTM within band are eligible; outside excluded.
- Underlying/option alignment tolerance: `0` sessions gap, `0` minutes quote age beyond the frozen quote snapshot policy (final valid consolidated quote at or before `15:59:00` America/New_York, max age `5` minutes per canonical contracts). Underlying daily bar must exist for every hedging day in the episode; missing bar => episode excluded.
- Contracts and schemas: prices as `Decimal`, OHLC relationships enforced, `adjustment_status` explicit, per `docs/data/canonical_contracts.md`. No unadjusted price may be used as adjusted.

### 5.5 Implementation readiness distinction

- Harness contract: FROZEN by this document (statistical rules above).
- Pipeline implementation: PIPELINE IMPLEMENTATION VERIFIED remains `NOT_READY`. This harness freezes the statistical contract only; it does not claim that hedging policy code (GRU deep hedger vs BS variants under proportional costs), data pipelines, or option/underlying alignment operational verification have been audited and found ready. A follow-up readiness audit must verify implementation before final-test execution.

## 6. H3 generator, hedger-seed, and baseline hierarchy

### 6.1 Generator family

- H3 generator family: signature-score NSDE ONLY. Conditional neural SDE trained with non-adversarial signature-kernel score, frozen as finite level-3 lead-lag signature + RBF-MMD with log-variance penalty, Euler/Itô `dt=1/252`, horizon `63`, Brownian dim `2`, state dim `2`. Per Amendment 020 Strategy B and SAP Section 1 Scope.
- WGAN role: `NONE` in H3 training paths. WGAN is not used for H3 synthetic data generation, hedger training, or primary hedging comparison. WGAN remains contextual for H2 only and must not influence generator selection.
- Bound five valid NSDE members exactly (audited immutable checkpoint identities):

| Member | Canonical member ID | Run prefix | Selected checkpoint SHA-256 | Selected Git blob | Final checkpoint SHA-256 | Final Git blob |
|---|---|---|---|---|---|---|
| seed-01 | v5-seed-01 | `5bdbaabd2fb257a7` | `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f` | `6820d07c0fb253a02337190d7c8683b5c01cb3f3` | `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4` | `6d0ead19a92c9c93422ab2b9c38b3d4bbbc5d7c` |
| seed-02 | v5-seed-02 | `62c7406cb3a2c642` | `9e6f8cd030d073d59324514d5a1ef6e87be6e3dbfb16b8cec7aa13928fd84f7a` | `592df5d33f9342901a1c9e4b9cae4c52f29c6a1c` | `b867af03b7a00dce6f4b34bcaf31896ddb891c9ba18e722dd2abb02ddf18ac8a` | `feef0df2fc721db3e1aea4ca80ea1b985e436` |
| seed-04 | v5-seed-04 | `77e7de9efabb7ce3` | `87d022152ba28f881f454a76aee1b572061e288fd3eee31b1ca52f2ba88cc35` | `3701888ef57f20132c77633f6aca2d6e6e3861` | `4927e6b6b575e20a20fc5ee225ac3400ad7e9524871b155d0cdfbf8ec9d4c72` | `c029db1e272117d73b6d596c2d4933aaf90bb` |
| seed-05 | v5-seed-05 | `1e8aa171993a1aba` | `3a71b12e1c0af08ea2c254fa6e162a09dd32dd47b399d6dc7585b264e33abef` | `808db090fe34f15b22d8062866846cde4d829` | `4d3b9475fbc9adba09b20822bd5941e367b4dc5b278f1ffb8d5954276a0a9c99` | `de846f5c671f492e4d909c99e7a534a1faeba` |
| reserve-j01 | reserve-j01 | `38c5113b27568e14` | `50d14095d95386c0fb7e1ee5ab43175272f02bfa84fbec3ddc6c8fe2a97326` | `38c9f8a0c8f97c64ce82e2ad38a0fea754a6a9` | `a4713691abb886a8151a6efa98dc2163068e147d1ea98d11d2c9a28b0e9b219` | `19620280adef3ae6224300e18d9d63496d334` |

All five are `GATE_PASS_VALID` per `structured_vol_v5_n5_family_analysis_v1.json`. Primary checkpoint for hedging is the selected `checkpoint.pt` (`best_epoch` per member); `checkpoint_final.pt` identity is pinned for audit but not used as hedging seed input unless preregistered hedger design explicitly states final vs selected (it states selected).

### 6.2 Generator aggregation

- Exactly ONE aggregation design (choose among per-member policies / ensemble / pooled synthetic paths):
  - **Per-member policies** — each of the five generators produces its own synthetic path pool independently (same geometry: `dt=1/252`, horizon `63`, `n_eval_paths=1024` per synthetic batch, seeded per member) and trains its own hedger set. No pooling of paths across generators. No ensemble averaging of model weights.
  - Primary Delta_CVaR point estimate is the **mean across the five generator members**, where each member's Delta_CVaR is first averaged over its hedger seeds. This preserves the five-seed uncertainty per v1 line 99 and lines 77-86 "not driven by one seed".
  - Reporting includes per-member Delta_CVaR at each cost level plus the cross-member mean, SD, and min/max.

### 6.3 Hedger training seed schedule

- Hedger seeds are distinct conceptually and numerically from generator seeds. Generator seeds are model-init/data seeds (`8281` series / `9281` etc.); hedger seeds are GRU optimizer/init seeds below, not reused.
- Number of hedger seeds: `3`.
- Exact hedger seed values: `31001`, `31002`, `31003` (integer seeds for GRU weight init and training shuffle).
- Mapping of hedger seeds to generator members: fully crossed — every generator member is paired with every hedger seed. Total GRU hedger policies: `5 generators x 3 hedger seeds = 15` independently trained deep hedgers per cost level (same cost level used in hedging loss).
- Whether every generator x hedger combination is trained: YES — fully crossed, all 15 combinations are trained. No 1:1 restriction.
- Hedger training data per combination: synthetic paths from the single generator member assigned to that row, not pooled. Training hyperparameters frozen from pre-final design (GRU architecture, optimizer, epochs) — implementation readiness is NOT claimed here, but the seed schedule is.
- Failure handling: any hedger combination that fails (nonfinite loss, no valid checkpoint) is reported as `HEDGER_TRAINING_FAILED` with its generator x hedger identity, counted in failure accounting, and excluded from that member's mean. If `>20%` of combinations fail, H3 is not claimed.

### 6.4 Aggregation hierarchy

- Aggregation hierarchy (exact):
  1. Per-episode paired loss `(L_Deep, L_BS)` per episode per hedger policy.
  2. Per-policy CVaR and Delta_CVaR per cost level.
  3. Per-generator-member: mean Delta_CVaR across its 3 hedger seeds at each cost level.
  4. Cross-generator primary: mean Delta_CVaR across 5 generator members at each cost level.
- Primary hedger-seed aggregation: mean across hedger seeds within each generator member.
- Primary unit for seed uncertainty: sample SD (ddof=1) across the 5 generator-member mean Delta_CVaR values at each cost level. Also report 95% CI across generator members (t-based with 4 df, reported alongside bootstrap market-period CI but not used as primary).
- Secondary/report-only seed summaries: SD across all 15 individual hedger policies at each cost level, and per-member hedger SD (3 seeds) to expose within-member variation.

### 6.5 Market-period uncertainty and two-way reporting hierarchy

- Market-period uncertainty unit: dependence-aware paired block bootstrap 95% CI and bootstrap SD over chronological market periods (Section 4). Computed on the cross-generator primary mean Delta_CVaR series (or equivalently on the episode-level paired differences averaged over seed hierarchy — deterministic before execution).
- Exact two-way reporting hierarchy:
  - Dimension A — Generator/hedger seed variation: per-member and cross-member SD per Section 6.4, at each cost level.
  - Dimension B — Market-period variation: block-bootstrap 95% CI, bootstrap SD, and p-value per Section 4, at each cost level.
  Reported separately per v1 line 105. No composite score mixing seed and market variance. Decomposed via two-way reporting table: seed-SD column and market-period CI column per cost level.

## 7. Black-Scholes comparator contract

- Source-native comparator family: Black-Scholes delta hedging family per v1 Core scope lines 34-36 — Black-Scholes delta, dynamically updated Black-Scholes delta, cost-adjusted delta — all under same SPY, maturity `5-30`, moneyness `0.90-1.10`, daily hedging, proportional costs, 95% CVaR.
- Which BS strategy is PRIMARY for H3: `cost-adjusted Black-Scholes delta` — i.e., Black-Scholes delta hedging with the same proportional cost model and daily rebalance rule as the deep hedger, evaluated at each of the three cost levels (`0`, `10`, `50` bps). This is the sole primary comparator for Delta_CVaR success.
- Which BS variants are secondary/report-only: 
  - `static Black-Scholes delta` — implied volatility calibrated once at episode inception from mid-quote, held constant through episode, same costs.
  - `dynamically updated Black-Scholes delta` — implied volatility recalibrated daily from mid-quote, same costs.
  Both reported at each cost level but not used for primary H3 decision.
- Parameter source: implied volatility inverted from end-of-day consolidated option mid-price (`(bid+ask)/2`) at inception (static) or daily (dynamic) via Black-Scholes formula, underlying price is SPY close, risk-free rate per frozen source (SOFR or `0` if frozen to `0` — must be prospectively frozen; choose `r = 0` for hedging P&L unless source freezes otherwise; document choice). No realized-vol plug-in unless frozen.
- Recalibration rule: static variant — no recalibration within episode; dynamic variant — recalibrate IV at each daily close using that day's mid-quote, applied to next day's delta. No intraday recalibration.
- Cost handling: all BS variants bear the same proportional costs as deep hedger at each cost level. Costs applied to `|delta_t - delta_{t-1}| * S_t` per rebalancing.
- Post-final selection: no baseline selection after observing final results. Primary comparator is frozen now as cost-adjusted delta. No switching to static or dynamic variant after seeing Delta_CVaR even if primary is unfavorable. Alternative BS variants remain secondary/report-only.
- Underlying alignment: SPY daily bars via XNYS calendar; no lookahead.

## 8. Single-access final-test state machine

### 8.1 States and current assignment

- Minimum states:
  - `SEALED` — final test sealed, no scientific final-test process has been created since single-access harness governance began.
  - `AUTHORIZED_SINGLE_ACCESS` — explicit authorization amendment/task has bound the exact harness SHA/blob and all required model/policy identities and granted single-use entitlement, but scientific final-test process not yet started.
  - `CONSUMED` — single-access entitlement has been permanently consumed (exactly one scientific final-test process has been created, regardless of outcome).
- Current state at this freeze: `SEALED`.
- Current final-test access count: `0`.
- Current final-test entitlement: `NONE`.
- Current final-test authorization: `NOT GRANTED`.
- Task 191: MUST NOT transition state. This freeze binds the contract only.

### 8.2 Future semantics (frozen now, enacted later)

- Authorization must bind exact harness SHA/blob and all required model/policy identities: a future final-test authorization task must cite this harness path `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md` with its canonical SHA and Git blob, plus the five NSDE checkpoint identities (Section 6.1) and hedger seed schedule (Section 6.3) and the BS primary comparator (Section 7) and the split-manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`. Authorization without these bindings is invalid.
- Scientific final-test process creation permanently consumes single-access entitlement: the first process that opens sealed rows under the authorized harness (any read of `data/processed/research/development` vs final-test scientific rows beyond metadata) transitions to `CONSUMED` atomically.
- Consumption occurs even if process later fails: failure, crash, nonfinite CVaR, missing aligned options, or timeout still counts as consumed. No reset to `SEALED`.
- No automatic retry: a failed final-test process does not auto-retry. No automatic rerun, no relaunch, no second process, no alternate policy selection after access, no rewriting result because scientific outcome is unfavorable. Any second attempt requires a new governance amendment explicitly labeling itself exploratory and stating it is not the confirmatory single-access construction.

### 8.3 Preflight checks that occur BEFORE sealed rows are opened

All must pass immediately before the single-access process opens final-test scientific rows; any failure aborts and does not consume entitlement (since rows not yet opened), except where noted:

1. `Git HEAD == 31226fcfc89f090eb1952f65ab37bddaf72fddca` or the authorizing successor HEAD that includes this harness and its audit — mismatch => abort.
2. Tracked tree clean — no uncommitted changes to `reports/protocol/*`, `configs/research/*`, `data/manifests/*`, `src/neuralmarket/*` — dirty => abort.
3. SAP identity replay: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` — mismatch => abort.
4. Harness identity replay: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md` canonical SHA and Git blob as frozen in Amendment 097 — mismatch => abort.
5. Split-manifest identity replay: `data/manifests/split_manifest_v1.json` manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`, range `2023-11-22` through `2025-12-31`, sessions `528`, calendar XNYS, `final_test_access_status == sealed` — mismatch => abort.
6. Registered policy/checkpoint identities: five NSDE selected checkpoint SHAs/blobs as in Section 6.1 present and byte-identical — mismatch => abort.
7. Runtime identity: no network, no provider acquisition, no new generator training before hedger phase; hedger training uses only this harness's generator members — violation => abort.
8. Expected process count `0` and access count `0` — existing `reports/research/evidence/structured_vol_v5_final_test_*` marker/result files count `0`, `data/manifests/split_manifest_v1.json` still `sealed`, prior final-test access markers count `0` — non-zero => abort (entitlement already consumed or leaked).
9. Authorization identity: authorizing task/amendment hash present and cites this harness SHA/blob — missing => abort.
10. Network prohibited: outbound TCP/HTTP disabled for the single-access process — violation => abort and consume if rows already opened.

Checks 1-9 are preflight (before sealed-row opens). Check 10 is runtime invariant. If checks 1-9 fail before any sealed-row read, entitlement is not consumed. If any sealed-row read has occurred, entitlement is `CONSUMED`.

### 8.4 Result persistence and access-marker semantics

- Access-marker semantics and location using repository-native convention WITHOUT creating the marker now: the single-access entitlement consumption is recorded at `reports/research/evidence/structured_vol_v5_final_test_single_access_marker.json` (JSON with fields `harness_path`, `harness_canonical_sha256`, `harness_git_blob`, `sap_canonical_sha256`, `sap_git_blob`, `manifest_hash`, `nsde_members`, `hedger_seeds`, `bs_primary`, `authorization_task`, `access_count` (`1` after consumption), `consumed_at_utc`, `process_pid`, `git_head_at_access`). This marker is NOT created by Task 191.
- Result persistence: original execution output must be durably preserved exactly once:
  - `reports/research/structured_vol_v5_final_test_hedging_report_v1.json` (canonical report with per-cost-level Delta_CVaR, CI, Holm, QC, seed/market breakdown, missingness).
  - `reports/research/evidence/structured_vol_v5_final_test_stdout.log` and `reports/research/evidence/structured_vol_v5_final_test_stderr.log` (transcripts).
  - `reports/research/evidence/structured_vol_v5_final_test_exit_code.txt`.
  No post hoc regeneration after seeing results. The first committed result is the confirmatory record. No overwriting with a "better" run.
- Full failure/missingness accounting: the report must contain per-cost-level `N_total`, `N_valid`, `N_missing`, `N_invalid_policy`, failure reasons, turnover/position flags, bootstrap diagnostics, seed-SD, and marker linkage. No selective omission even if H3 fails.
- No post hoc regeneration: if result file exists, any future attempt to regenerate without an exploratory-labeled amendment is a governance violation.

### 8.5 Retry/rerun prohibition

- No automatic retry on process failure.
- No automatic rerun on nonfinite CVaR or empty eligible episode set.
- No relaunch with different cost levels, block length, or hedger seeds.
- No second process creating a competing confirmatory claim.
- No alternate policy selection after access (no switching to secondary BS variants or changing generator aggregation to obtain significance).
- No rewriting result because scientific outcome is unfavorable. The committed result stands as confirmatory even if Delta_CVaR is positive or CI includes zero; any new analysis is exploratory and must be labelled as such.

## 9. Task and band

- Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-FREEZE-191` — `R4`.
- No source code, no harness execution, no deferred values, no network, no push.
- This harness plus Amendment 097 are `R4` protocol artifacts; they satisfy prerequisite #8 pending independent audit. Deep hedging execution, Gate, inference, scientific resampling execution remain `0` at this freeze.

## 10. Verification at freeze

- SAP canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` — verified.
- Amendment 096 canonical SHA `a80293300b14f06ae5a7f410088af96d32f82284de3fca1255adec26b1853c4b` Git blob `50340b489891d43284d8cadfd3452f43dfbebf75` — verified.
- Split manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — verified metadata only, no final-test rows read.
- H2 `H2_NOT_SUPPORTED` preserved.
- Final test `SEALED` access `0` entitlement `NONE` authorization `NOT GRANTED`.
- NSDE checkpoint identities pinned above.
- Harness contains zero deferred entries, zero remaining constants, and no self-referential hash.

## 11. What this harness does not do

- Does not authorize final-test access.
- Does not create the single-access marker or result files.
- Does not claim pipeline implementation verified.
- Does not train hedgers or run generators.
- Does not execute the paired block bootstrap; it freezes the RNG and procedure for a future execution.
- Does not grant WGAN any H3 role.
- Does not change the SAP endpoint or success threshold.

*This harness is append-only. Any change requires a new governed amendment, not a silent edit. The next governed action is the independent audit task NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-AUDIT-192.*
