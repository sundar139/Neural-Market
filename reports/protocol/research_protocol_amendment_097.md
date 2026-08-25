# Amendment 097 — V5 Final-Test Single-Access Harness Freeze

Date: 2026-08-25
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-FREEZE-191`
Risk: `R4`
Branch: `main`
Starting HEAD: `31226fcfc89f090eb1952f65ab37bddaf72fddca`
Prerequisite: `NM-R4-V5-STATISTICAL-ANALYSIS-PLAN-AUDIT-190` — `VALIDATED`
Safety branch: `safety/pre-v5-final-test-harness-31226fc` at `31226fcfc89f090eb1952f65ab37bddaf72fddca`
SAP prerequisite #7: `SATISFIED`
H2 state: `H2_NOT_SUPPORTED` preserved (WGAN comparator campaign COMPLETE, 5 valid WGAN members including reserve, NSDE not no-worse on all per Amendment 095)
H2 wording: `The signature-score training objective is more stable across seeds and epochs than adversarial (WGAN) training.` — adjudicated `H2_NOT_SUPPORTED`
Status: APPEND-ONLY HARNESS FREEZE — single-access harness contract frozen; no training, no Gate, no hedger execution, no generator execution, no model inference, no scientific bootstrap/resampling execution, no validation, no external validation, no network, no push, no final-test row access

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, primary endpoint Delta_CVaR, experimental governance, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist, Strategy B, gating rule)
- H2 Amendment 095: `reports/protocol/research_protocol_amendment_095.md` at `fa28687` (H2_NOT_SUPPORTED adjudication, WGAN N=5 SATISFIED with reserve, WGAN 5 valid)
- SAP v1: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9`
- Amendment 096 (SAP freeze): `reports/protocol/research_protocol_amendment_096.md` at canonical SHA `a80293300b14f06ae5a7f410088af96d32f82284de3fca1255adec26b1853c4b` Git blob `50340b489891d43284d8cadfd3452f43dfbebf75`
- Split manifest metadata: `data/manifests/split_manifest_v1.json` at manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test `2023-11-22` through `2025-12-31`, 528 XNYS sessions, calendar XNYS `4.13.2` America/New_York, purge 90 + embargo 10, excluded boundary `2023-07-03` to `2023-11-21` 100 sessions, training `2018-05-01` to `2021-12-31` 926, validation `2022-05-26` to `2023-06-30` 275, metadata only)
- Split policy: `docs/data/split_policy.md` (chronological splitting, purging/embargoing, normalizers fit on training only)
- Engineering contract: `docs/engineering/agent-contract.md` (R4, DISCOVER->DECIDE->MUTATE->VERIFY->REPORT, final-test access requires explicit authorization)
- NSDE family source: `reports/research/structured_vol_v5_n5_family_analysis_v1.json` (5 valid members: seed-01, seed-02, seed-04, seed-05, reserve-j01)

Conflicts: None — SAP, Amendment 096, and Amendment 095 are consistent: SAP deferred exact cost levels, resampling constants, QC thresholds, and harness bindings; this harness binds them without altering SAP endpoint or H2 state.

## 2. Harness freeze

Harness path: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md`
Harness canonical SHA-256: `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc`
Harness Git blob: `b7c24126e8e070e745fed01a6122fe6d2bc51d2c`

Harness status: `FROZEN_PENDING_INDEPENDENT_AUDIT`
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-FREEZE-191`

Harness commit: `153e6536ea44612276edfd2ab2696fc0578646b1` (`docs(research): freeze v5 final-test single-access harness`)

## 3. Exact inference and resampling constants (frozen)

Paired endpoint: `Delta_CVaR = (CVaR_0.95(Deep) - CVaR_0.95(BS)) / CVaR_0.95(BS)` per v1 lines 70-72; paired by option episode (inception and expiration in same split).

- Pairing unit: option episode (chronological, sorted by inception date)
- CI algorithm: paired circular block bootstrap (CBB) over episodes
- Resampling algorithm: paired circular block bootstrap with replacement, blocks concatenated and truncated to N_episodes, paired losses move together
- Dependence/block rule: block-coupled paired resampling; preserves chronological adjacency and overlapping-period dependence per v1 line 103
- Block construction: circular wrap-around, uniform block sampling with replacement
- Block length: fixed `L = 20` episodes (deterministic, not data-dependent)
- Resample count: `B = 10000` paired bootstrap replicates
- RNG seed: `9491` (NumPy Generator PCG64), distinct from training/eval/Gate/hedger seeds, recorded in result artifact
- Confidence level: `95%`
- Sidedness: two-sided 95% CI for Delta_CVaR (excludes zero)
- Alpha: `0.05`
- Failure on insufficient effective sample: `INSUFFICIENT_SAMPLE` if `N < 40` episodes or `<2` distinct blocks or `>10%` missing/nonfinite, then H3 not claimed; no fallback to i.i.d. bootstrap
- Missing/nonfinite handling: no imputation; missing/nonfinite hedging loss makes episode missing for that level, reported as failure/missingness; `>0.1%` nonfinite triggers predeclared failure criterion; `CVaR_BS == 0` or nonfinite makes Delta_CVaR undefined (`nan`/`inf`) and that level cannot satisfy success

No future RNG alternative. No alternative count.

## 4. Exact Holm numerical-membership semantics (frozen)

- Conceptual primary family: `{H1, H2, H3}` per v1 lines 47-52 and Amendment 020 section 2.1; H4 and H5 are secondary/extension, not primary
- H1 p-value availability: `NONE` — H1 external validation was descriptive per-family ranks, no preregistered inferential p-value, no significance test
- H2 p-value availability: `NONE` — H2 descriptive per preregistration `6c4a2725...` significance section: no test, no p-value; `H2_NOT_SUPPORTED` is descriptive
- H3 p-value availability: `VALID` — paired block-bootstrap p-value for Delta_CVaR is the sole preregistered inferential p-value
- Numeric Holm set: `{H3}` only; `p_Holm(H3) = p_raw(H3)`
- H2 numerical participation: `EXCLUDED` — H2 is descriptive primary hypothesis, recorded in family reporting but excluded from numeric Holm adjustment
- Method: Holm step-down at `alpha = 0.05`
- Ordering: ascending p-value; ties by preregistered order `H1, H2, H3` then earliest task ID
- H3 adjusted rule: confirmatory H3 claim requires Holm-adjusted `p < 0.05` (with `k=1` equals raw `p < 0.05`) plus unadjusted CI, magnitude, cost-level, QC, and seed/market robustness checks
- Do not invent missing H1/H2 p-values; report as `NOT_AVAILABLE_DESCRIPTIVE_ONLY`

## 5. Exact transaction-cost levels and QC thresholds (frozen)

- Cost model: proportional per v1 Core scope line 39
- Exact cost levels: `0 bps` (`0.0000`), `10 bps` (`0.0010`), `50 bps` (`0.0050`) proportional per trade notional per `|delta_t - delta_{t-1}| * S_t`; exactly two nonzero levels (`10`, `50`) plus zero reference
- Zero-cost reference: included as baseline stratum `0 bps`
- Daily rebalance rule: daily hedge frequency, position held within session, rebalanced at close to target delta
- Turnover formula: `turnover_episode = sum_{t=1}^{T} |delta_t - delta_{t-1}|` with `delta_0 = 0`
- Exact pathological-turnover threshold: per-episode `> 10.0` flagged; per-level mean `> 4.0` flagged; `>5%` episodes exceeding per-episode threshold flags level as pathological
- Position/hedge-ratio definition: `delta_t` is target holding in underlying per unit option notional
- Exact pathological-position threshold: per-step `|delta_t| > 2.0` flagged; per-episode `max_t |delta_t| > 2.0` flagged; per-level mean `|delta_t| > 1.2` flagged; `>1%` episodes with per-episode flag flags level as pathological
- Nonfinite hedge-position rule: any episode with nonfinite delta is invalid-policy for that strategy/level, excluded and counted; `>0.1%` nonfinite triggers failure criterion
- Nonfinite hedging-loss rule: `L = -P&L` nonfinite makes episode missing; `>0.1%` nonfinite triggers failure criterion per v1 lines 108-120
- CVaR_BS zero/nonfinite denominator rule: `|CVaR_BS| < 1e-12` or nonfinite makes Delta_CVaR undefined (`nan`/`inf`), level cannot count toward two-level success
- Missing-price rule: episodes with missing underlying/option price, missing BS input, or `RejectedRecord` excluded, counted as missingness, not imputed
- Episode-exclusion/failure-accounting rule: all excluded/missing/invalid episodes enumerated per cost level with counts, rates, and reasons; no selective omission
- Same-split inception/expiration requirement: both inception and expiration must fall in same split; cross-boundary episodes invalid; tolerance `0` sessions
- SPY option eligibility: underlying `SPY` only; European calls/puts only; point-in-time definition required
- Maturity: `5` to `30` trading days inclusive
- Moneyness: `0.90` to `1.10` inclusive as `S_inception / K`
- Option/underlying alignment checks: zero tolerance; underlying daily bar required for every hedging day; missing bar excludes episode; quote snapshot per canonical contracts (`15:59:00` America/New_York, max age `5` minutes)
- Distinction: HARNESS CONTRACT FROZEN; PIPELINE IMPLEMENTATION VERIFIED remains `NOT READY` — this harness does not claim operational implementation has been audited

## 6. H3 generator, hedger-seed, and baseline hierarchy (frozen)

- Generator family: signature-score NSDE ONLY; WGAN role `NONE` in H3 training paths
- Bound five valid NSDE members (audited immutable checkpoint identities):
  - seed-01 (`v5-seed-01`, prefix `5bdbaabd2fb257a7`, selected `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f` blob `6820d07c0fb253a02337190d7c8683b5c01cb3f3`, final `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4` blob `6d0ead19a92c9c93422ab2b9c38b3d4bbbc5d7c`)
  - seed-02 (`v5-seed-02`, prefix `62c7406cb3a2c642`, selected `9e6f8cd030d073d59324514d5a1ef6e87be6e3dbfb16b8cec7aa13928fd84f7a` blob `592df5d33f9342901a1c9e4b9ca2d6e6e3861`, final `b867af03b7a00dce6f4b34bcaf31896ddb891c9ba18e722dd2abb02ddf18ac8a` blob `feef0df2fc721db3e1aea4ca80ea1b985e436`)
  - seed-04 (`v5-seed-04`, prefix `77e7de9efabb7ce3`, selected `87d022152ba28f881f454a76aee1b572061e288fd3eee31b1ca52f2ba88cc35` blob `3701888ef57f20132c77633f6aca2d6e6e3861`, final `4927e6b6b575e20a20fc5ee225ac3400ad7e9524871b155d0cdfbf8ec9d4c72` blob `c029db1e272117d73b6d596c2d4933aaf90bb`)
  - seed-05 (`v5-seed-05`, prefix `1e8aa171993a1aba`, selected `3a71b12e1c0af08ea2c254fa6e162a09dd32dd47b399d6dc7585b264e33abef` blob `808db090fe34f15b22d8062866846cde4d829`, final `4d3b9475fbc9adba09b20822bd5941e367b4dc5b278f1ffb8d5954276a0a9c99` blob `de846f5c671f492e4d909c99e7a534a1faeba`)
  - reserve-j01 (`reserve-j01`, prefix `38c5113b27568e14`, selected `50d14095d95386c0fb7e1ee5ab43175272f02bfa84fbec3ddc6c8fe2a97326` blob `38c9f8a0c8f97c64ce82e2ad38a0fea754a6a9`, final `a4713691abb886a8151a6efa98dc2163068e147d1ea98d11d2c9a28b0e9b219` blob `19620280adef3ae6224300e18d9d63496d334`)
- Generator aggregation: per-member policies — each generator produces its own synthetic path pool, trains its own hedger set; primary Delta_CVaR is mean across 5 generator members (each member mean over its hedger seeds); per-member values also reported
- Hedger training seed schedule: `3` hedger seeds, values `31001`, `31002`, `31003`, distinct from generator/model seeds
- Generator x hedger mapping: fully crossed — every generator member paired with every hedger seed; total `5 x 3 = 15` GRU hedger policies per cost level; `YES` every combination is trained
- Hedger-seed aggregation: within-member mean across 3 hedger seeds, then cross-member mean across 5 generators
- Primary unit for seed uncertainty: SD (ddof=1) across 5 generator-member mean Delta_CVaR values
- Secondary/report-only hedger summaries: SD across all 15 individual policies and per-member hedger SD
- Market-period unit: block-bootstrap 95% CI and bootstrap SD over chronological market periods (Section 3)
- Two-way reporting hierarchy: generator/hedger seed variation (SD across members/policies) and market-period variation (block-bootstrap CI/SD) reported separately per v1 line 105; no composite

## 7. Black-Scholes comparator contract (frozen)

- Comparator family: Black-Scholes delta hedging family per v1 Core scope lines 34-36: Black-Scholes delta, dynamically updated Black-Scholes delta, cost-adjusted delta; all under same SPY, maturity `5-30`, moneyness `0.90-1.10`, daily hedging, proportional costs, 95% CVaR
- Primary comparator for H3: `cost-adjusted Black-Scholes delta` at each cost level (`0`, `10`, `50` bps)
- Secondary/report-only comparators: `static Black-Scholes delta` (vol fixed at inception) and `dynamically updated Black-Scholes delta` (daily IV recalibration); reported at each cost level, not used for primary decision
- Parameter source: implied volatility inverted from end-of-day consolidated mid-price `(bid+ask)/2` at inception (static) or daily (dynamic) via Black-Scholes formula; underlying SPY close; risk-free rate `r = 0` for hedging P&L unless source freezes otherwise
- Recalibration rule: static — no recalibration within episode; dynamic — recalibrate IV at each daily close, applied next day
- Cost handling: same proportional costs as deep hedger at each level
- Post-final selection: prohibited — primary comparator frozen now; no switching to secondary variants after observing final results

## 8. Single-access final-test state machine (frozen)

- Current state: `SEALED`
- Current final-test access count: `0`
- Current final-test entitlement: `NONE`
- Current final-test authorization: `NOT GRANTED`
- Future states:
  - `SEALED -> AUTHORIZED_SINGLE_ACCESS -> CONSUMED` (fail-closed)
  - Task 191 does not transition state
- Future semantics:
  - Authorization must bind exact harness SHA/blob `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc / b7c24126e8e070e745fed01a6122fe6d2bc51d2c` plus the five NSDE checkpoint identities plus hedger seeds `31001,31002,31003` plus BS primary plus split-manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`
  - Scientific final-test process creation permanently consumes single-access entitlement
  - Consumption occurs even if process later fails
  - No automatic retry, no automatic rerun, no relaunch, no second process, no alternate policy selection after access, no rewriting result because scientific outcome is unfavorable
- Preflight checks before sealed rows are opened (all must pass):
  1. `Git HEAD` matches harness-authorizing HEAD
  2. Tracked tree clean
  3. SAP identity `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa / 8ffe6d96c758f29471db3b97b9ae07a181427db9`
  4. Harness identity `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc / b7c24126e8e070e745fed01a6122fe6d2bc51d2c`
  5. Split-manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` range `2023-11-22` through `2025-12-31` sessions `528` calendar XNYS, `final_test_access_status == sealed`
  6. Registered policy/checkpoint identities (five NSDE selected checkpoint SHAs/blobs)
  7. Runtime identity: no network, no provider acquisition, hedger training uses only bound generator members
  8. Expected process count `0` and access count `0` (no prior marker/result files)
  9. Authorization identity present and cites harness SHA/blob
  10. Network prohibited
- Access-marker semantics and location using repository-native convention without creating marker now: `reports/research/evidence/structured_vol_v5_final_test_single_access_marker.json` with fields `harness_path`, `harness_canonical_sha256`, `harness_git_blob`, `sap_canonical_sha256`, `sap_git_blob`, `manifest_hash`, `nsde_members`, `hedger_seeds`, `bs_primary`, `authorization_task`, `access_count` (`1` after consumption), `consumed_at_utc`, `process_pid`, `git_head_at_access`; not created by Task 191
- Result persistence: original execution output durably preserved at `reports/research/structured_vol_v5_final_test_hedging_report_v1.json` plus `reports/research/evidence/structured_vol_v5_final_test_stdout.log` / `stderr.log` / `exit_code.txt`; no post-hoc regeneration; full failure/missingness accounting; no selective omission

## 9. Final-test preservation

- Final test: `SEALED`
- Final-test access count: `0`
- Final-test entitlement: `NONE`
- Final-test authorization: `NOT GRANTED`
- Scientific final-test execution: `0`
- Deep hedging execution: `0`
- Training: `0`
- Gate: `0`
- Model inference: `0`
- Scientific bootstrap/resampling execution: `0`
- Validation: `0`
- External validation: `0`
- Network: `0`
- Push: `0`

No final-test scientific rows were read. Metadata inspection only.

## 10. Commit record

- Harness artifact committed alone at `153e6536ea44612276edfd2ab2696fc0578646b1` (`docs(research): freeze v5 final-test single-access harness`)
- This Amendment 097 commits separately at its own hash (see verification)

No amend, no rebase, no reset, no push.

This amendment is append-only, contains no self-referential hash.
