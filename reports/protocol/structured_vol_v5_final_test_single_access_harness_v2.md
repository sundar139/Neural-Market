# V5 Final-Test Single-Access Harness v2

Status: REPAIRED_PENDING_INDEPENDENT_AUDIT
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-193`
Risk: `R4`
Date: 2026-08-25
Branch: `main`
Starting HEAD: `ede2d4f57741cdf4a1e68309be7938be7a7c8032`
Safety branch: `safety/pre-v5-final-test-harness-repair-ede2d4f` at `ede2d4f57741cdf4a1e68309be7938be7a7c8032`
Prerequisite: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-AUDIT-192` — `REPAIR_REQUIRED`
Supersedes for future authorization: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md`
Reason: `Task-192 load-bearing harness defects` (BS risk-free rate conditional, BS dividend/solver/time/settlement unfrozen, inference CI type/p-value unfrozen, P&L terminal unwind/premium unfrozen, bootstrap-target equivocation)

This task is a bounded document/contract repair only. It preserves harness v1 and Amendment 097 unchanged. It grants no final-test access entitlement. No final-test row access, no training, no hedger execution, no generator execution, no Gate, no model inference, no bootstrap execution, no validation, no external validation, no network, no push.

## 1. Authoritative bindings

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, primary endpoint Delta_CVaR, experimental governance, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist Strategy B, gating rule)
- H2 adjudication: `reports/protocol/research_protocol_amendment_095.md` at `fa28687` — H2 `H2_NOT_SUPPORTED` (WGAN N=5 SATISFIED with reserve, NSDE 5 valid, WGAN worse on normalized epoch SD 0.171 vs 0.052)
- SAP v1: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9`
- Amendment 096 (SAP freeze): `reports/protocol/research_protocol_amendment_096.md` at canonical SHA `a80293300b14f06ae5a7f410088af96d32f82284de3fca1255adec26b1853c4b` Git blob `50340b489891d43284d8cadfd3452f43dfbebf75`
- Harness v1: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md` at canonical SHA `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc` Git blob `b7c24126e8e070e745fed01a6122fe6d2bc51d2c` — PRESERVED BYTE-IDENTICAL (not edited)
- Amendment 097: `reports/protocol/research_protocol_amendment_097.md` at canonical SHA `2b85791803b553a668a86ed464b5d44538a5eafee405c3f74b551caf090fec90` Git blob `dbfd2effc4022f9f916a3d5e2d60f83adb52efd2` — PRESERVED BYTE-IDENTICAL
- Split manifest: `data/manifests/split_manifest_v1.json` manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test `2023-11-22` through `2025-12-31`, 528 XNYS sessions, calendar XNYS `4.13.2` America/New_York, purge 90 + embargo 10, excluded boundary `2023-07-03` to `2023-11-21` 100 sessions, training `2018-05-01` to `2021-12-31` 926, validation `2022-05-26` to `2023-06-30` 275)
- Split policy: `docs/data/split_policy.md` (chronological, purging/embargoing, normalizers fit on training only)
- Engineering contract: `docs/engineering/agent-contract.md` (R4, DISCOVER->DECIDE->MUTATE->VERIFY->REPORT, final-test access requires explicit authorization)
- NSDE family source: `reports/research/structured_vol_v5_n5_family_analysis_v1.json` (5 valid members, 0 invalid)

H2 state: `H2_NOT_SUPPORTED` preserved. No retuning. No WGAN hedging role.

Final-test state at repair: `SEALED`, access count `0`, entitlement `NONE`, authorization `NOT GRANTED`, harness v1 `REPAIR_REQUIRED`, deep hedging `NOT READY`.

## 2. Preserved harness-v1 values (not redesigned)

The following remain exactly as frozen in v1 (not redesigned per bounded-repair scope):

- H3 endpoint `Delta_CVaR = (CVaR_0.95(Deep) - CVaR_0.95(BS)) / CVaR_0.95(BS)` per v1 lines 70-72
- Cost grid `0 bps (0.0000), 10 bps (0.0010), 50 bps (0.0050)` proportional per trade notional
- Paired CBB `L=20` episodes, `B=10000`, NumPy `PCG64(9491)`, two-sided 95%, alpha 0.05
- Five NSDE members seed-01, seed-02, seed-04, seed-05, reserve-j01 with audited checkpoint identities (Section 7)
- Three hedger seeds `31001, 31002, 31003` and expected fully crossed `5×3=15` analysis hierarchy
- Holm numeric set `{H3}` only (`H2` descriptive, excluded), H1 no p-value
- Single-access state machine `SEALED -> AUTHORIZED_SINGLE_ACCESS -> CONSUMED` fail-closed and all preflight/persistence semantics

This repair only resolves the five Task-192 defect groups without opportunistic redesign.

## 3. H3 endpoint (preserved)

```
Delta_CVaR = (CVaR_0.95(Deep) - CVaR_0.95(BS)) / CVaR_0.95(BS)
```

- Hedging loss `L = -P&L` per v1 Primary endpoint.
- Primary risk endpoint: 95% CVaR of hedging loss per v1.
- Sign convention: negative Delta_CVaR favors deep hedging.
- Success requires ALL SAP conditions (Delta<0, paired 95% CI excludes zero, improvement >=5% i.e. Delta <= -0.05, holds at both nonzero cost levels, no unacceptable deterioration in average loss, no pathological turnover/position, not driven by one seed or one market period).
- Relative improvement = `-Delta_CVaR * 100%` when negative.
- Computed per cost level; no composite across cost levels.

## 4. Exact inference, resampling, bootstrap target, CI, and p-value (REPAIRED)

### 4.1 Pairing and bootstrap geometry (preserved)

- Pairing unit: option episode. Both inception and expiration must fall in same split per v1 lines 94-95. Episodes are the paired unit for `(L_Deep, L_BS)`. Cross-boundary episodes invalid and excluded.
- Dependence-preserving method: paired circular block bootstrap over episodes sorted by inception date (chronological order). Each bootstrap replicate resamples blocks of consecutive episodes to preserve autocorrelation from overlapping market periods.
- Resampling method: paired circular block bootstrap (CBB) with replacement.
- Block construction: partition chronological episode sequence of length `N` into circular indices `0..N-1` with wrap-around. For each replicate, sample `ceil(N / L)` blocks of length `L` uniformly with replacement, concatenate blocks, truncate to `N`.
- Block length: fixed `L = 20` episodes. Deterministic before execution, not estimated from final data.
- Resample count: `B = 10000` paired bootstrap replicates.
- RNG seed: `9491` using NumPy `Generator(PCG64(9491))` for bootstrap resampling only. Distinct from model-init/data seeds for NSDE (`8281` series, `9281`, `11281`, `12281`, `13281`), evaluation seed `8283`, Gate seeds `7777`/`7778`/`8801`, and hedger seeds `31001`/`31002`/`31003`. Recorded in result artifact.
- Confidence level: `95%`.
- Sidedness: two-sided 95% CI for Delta_CVaR.
- Alpha: `0.05` per primary comparison; Holm-adjusted across numeric family at same alpha.
- Failure on insufficient effective sample: if `N < 2*L` (fewer than 40 episodes) or fewer than 2 distinct blocks or effective resampled CVaR denominator has >10% missing/nonfinite episodes, report `INSUFFICIENT_SAMPLE` and H3 not claimed. No fallback to i.i.d. bootstrap.
- Missing/nonfinite handling: no imputation. Episode with missing underlying/option price, missing BS inputs, nonfinite hedge position, or nonfinite hedging loss excluded from that cost level's CVaR and counted as missingness. If `>0.1%` of episodes at a cost level have nonfinite hedging loss, predeclared failure triggers (v1 lines 111-113). If BS CVaR zero or nonfinite at a cost level, Delta undefined (`nan`/`inf`).

### 4.2 Single bootstrap target (REPAIRED — equivocation removed)

For each cost level, the original point estimate and every bootstrap replicate use the SAME hierarchy. There is no alternative bootstrap target.

For each bootstrap replicate `b = 1..B`:

1. Draw one circular-block-bootstrap episode index sequence `I_b` of length `N` (blocks of length `L=20` sampled with replacement as above, concatenated and truncated).

2. Apply the SAME `I_b` to every paired Deep/BS episode-loss vector for all `5` generator members × `3` hedger seeds at that cost level. That is, all policies share the same resampled episode indices per replicate (paired and block-synchronized).

3. For each policy `(g,h)` where `g` in `{seed-01,seed-02,seed-04,seed-05,reserve-j01}` and `h` in `{31001,31002,31003}`, recompute on the resampled episode set `I_b`:
   - `CVaR_Deep^{g,h,b} = CVaR_0.95( { L_Deep^{g,h}[i] : i in I_b and i valid } )`
   - `CVaR_BS^{g,h,b} = CVaR_0.95( { L_BS[i] : i in I_b and i valid } )`  (BS loss is policy-independent; same BS vector applied per replicate)
   - `Delta^{g,h,b} = (CVaR_Deep^{g,h,b} - CVaR_BS^{g,h,b}) / CVaR_BS^{g,h,b}`  if `|CVaR_BS^{g,h,b}| >= 1e-12` and both CVaRs finite; otherwise `Delta^{g,h,b} = nan`.

4. For each generator member `g`: `Delta_g^{b} = mean_{h=1..3} Delta^{g,h,b}` where mean is arithmetic mean over finite `Delta^{g,h,b}` values; if any `Delta^{g,h,b}` is nan and would make member mean nan, report that member as `nan` for this replicate.

5. Primary bootstrap statistic: `Delta_primary^{b} = mean_{g=1..5} Delta_g^{b}` where mean is arithmetic mean over the 5 finite generator-member means; if any generator member Delta is nan, then Delta_primary^{b} is nan.

The original point estimate `Delta_primary` (unresampled) uses the identical hierarchy on the full episode set (`I_unresampled = 0..N-1`): per-policy CVaR, per-policy Delta, mean across hedger seeds per generator, mean across generators.

### 4.3 Percentile CBB interval (REPAIRED — type frozen)

Freeze CI as the percentile CBB interval using NumPy's explicitly frozen quantile method after checking repository runtime convention (NumPy `2.4.6`, default `method='linear'`):

- Let `S = { Delta_primary^{b} : b=1..B and Delta_primary^{b} finite }`.
- Let `B_valid = |S|`.
- If `B_valid == B` and all finite (see Section 4.4 tolerance, default requires all 10000 finite), compute:
  - `lower = np.quantile(S, 0.025, method='linear')`
  - `upper = np.quantile(S, 0.975, method='linear')`
  using NumPy `quantile` with `method='linear'` (linear interpolation, type 7, the documented NumPy default and the method checked in repository runtime at repair time).
- Interval is `[lower, upper]` inclusive of method definition. No bias correction, no acceleration, no studentization. If `B_valid < B` but meets tolerance, the same quantile is computed over `S` with `B_valid` valid replicates.

This is the sole interval construction. No BCa, no basic, no other method.

### 4.4 Bootstrap p-value (REPAIRED — formula frozen)

Freeze the H3 bootstrap p-value exactly:

- Valid replicate set: `S` as above, `B_valid = |S|`.
- Minimum valid-bootstrap fraction: prospectively freeze as `B_valid == B` (all `10000` replicates finite). If any Delta_primary^{b} is nan/inf, the replicate is excluded from `S` and counted in failure diagnostics. If `B_valid < B`, report `INSUFFICIENT_BOOTSTRAP` unless a future execution's pre-registered tolerance explicitly states otherwise; default prospective tolerance is `1.0` (all 10000 required). No fallback to partial-B p-value unless tolerance was frozen before execution.
- For valid case `B_valid == B`:
  - `q_minus = count(Delta_primary^{b} <= 0) / B_valid`
  - `q_plus = count(Delta_primary^{b} >= 0) / B_valid`
  - Ties at zero count in BOTH corresponding inclusive tails (a replicate with `Delta == 0` contributes to both `q_minus` and `q_plus`).
  - `p_raw = min(1.0, 2 * min(q_minus, q_plus))`
  - Continuity correction: `NONE`.
  - Failed/nonfinite bootstrap replicate: excluded from `B_valid` and counted in failure diagnostics; p-value denominator is `B_valid`, not `B`.
  - Test statistic: `Delta_primary` (mean-of-means Delta_CVaR across hedger seeds and generators per cost level).
  - Null: `Delta_CVaR = 0` (no reduction relative to BS).
  - Tails: two-sided via doubling of smaller inclusive one-sided tail; no alternative doubling or absolute-value tail.

Number of valid replicates, tie counts, and per-replicate failure reasons are reported in the result artifact. No H1/H2 p-values are fabricated. Numeric Holm set remains `{H3}` with `p_Holm(H3) = p_raw(H3)`.

### 4.5 Holm multiplicity (preserved)

- Conceptual primary family `{H1,H2,H3}` per v1 lines 47-52 and Amendment 020 section 2.1; H4 and H5 secondary/extension excluded.
- H1 p-value availability: `NONE` (descriptive per-family ranks, no inferential p-value).
- H2 p-value availability: `NONE` (descriptive stability, no test per preregistration significance section).
- H3 p-value availability: `VALID` (paired block-bootstrap p as frozen in Section 4.4).
- Numeric Holm set: `{H3}` only; `p_Holm(H3) = p_raw(H3)`.
- H2 numerical participation: `EXCLUDED` (recorded but excluded from numeric Holm).
- Method: Holm step-down at `alpha=0.05`.
- Ordering: ascending p-value; ties by `H1, H2, H3` then earliest task ID.
- H3 adjusted rule: confirmatory H3 requires Holm-adjusted `p < 0.05` (with `k=1` equals raw `p < 0.05`) plus CI excluding zero plus magnitude/cost/QC/seed robustness.

## 5. Exact transaction-cost, hedging P&L, and QC constants (REPAIRED)

### 5.1 Transaction costs (preserved)

- Cost model: proportional per v1 Core scope line 39. Not fixed, not quadratic, not market-impact.
- Exact cost levels (3 strata): `C0 = 0 bps (0.0000)`, `C1 = 10 bps (0.0010)`, `C2 = 50 bps (0.0050)` proportional per trade notional.
- Cost per rebalancing: `cost_t = c * |delta_t - delta_{t-1}| * S_t` where `c` is cost level (0, 0.0010, 0.0050), `S_t` underlying close at day `t`, `delta_t` hedge ratio at close of day `t`.
- Rebalance timing: daily hedge frequency, position held constant within session, rebalanced at close to target delta. No intraday rebalancing. Per v1 line 22.

### 5.2 Hedging P&L accounting (REPAIRED — previously unfrozen)

The following are prospectively frozen now (before any final-test hedging execution). Original protocol defines hedging loss `L = -P&L` per v1 Primary endpoint but does not pin premium/cash/unwind details beyond proportional costs; this repair freezes one deterministic convention before execution and documents it as prospective, not data-dependent.

- Sign convention: hedger is `SHORT` one European option per episode (short call or short put, per eligibility). All P&L statements are from the short perspective. Hedger receives premium at inception and pays payoff at expiration; hedging reduces risk of this short position. This convention matches standard deep-hedging literature and Task-192 repair preference.

- Underlying price source: `SPY` daily close `S_t` via XNYS calendar session closes; daily bars are `UnderlyingDailyBar` with `Decimal` prices and `adjustment_status` explicit.

- Option premium treatment: `INCLUDED`. At `t=0` (episode inception close), premium `P0 = mid_price_0` where `mid_price_0 = (bid_0 + ask_0)/2` consolidated quote at or before `15:59:00` America/New_York (max age 5 minutes per canonical contracts). `P0` is a cash inflow at `t=0` counted in P&L. Premium is not optional and not excluded. If `P0` is missing/invalid (no valid quote, crossed, stale), episode is invalid/missing for hedging evaluation.

- Initial cash: `cash_0 = P0 - cost_0` where `cost_0 = c * |delta_0 - delta_{-1}| * S_0` with `delta_{-1} = 0` (zero initial hedge position). That is, initial hedge `delta_0` is acquired at `S_0` paying proportional cost.

- Initial position: `delta_{-1} = 0` before inception; `delta_0` is first target hedge ratio at inception close (model output for Deep, BS delta for BS comparator).

- Cash-account initialization: `cash_0` as above. Cash account holds residual cash after premium, costs, and underlying trades.

- Cash-account accrual rule: `r_cash = 0.0` (zero accrual). Cash balance does not accrue interest between hedging days. This aligns with BS pricing `r=0.0` in Section 6 and simplifies discrete hedging P&L without risk-free carry.

- Transaction-cost debit timing: costs are debited from cash at the same close `t` at which the hedge adjustment from `delta_{t-1}` to `delta_t` occurs, using `S_t` at that close.

- Daily hedge dynamics: for `t = 1..T-1` where `T` is expiration session (maturity `5..30`), hold `delta_{t-1}` overnight, underlying P&L on day `t` is `delta_{t-1} * (S_t - S_{t-1})`, and hedge adjustment to `delta_t` at `S_t` costs `cost_t = c * |delta_t - delta_{t-1}| * S_t`. For `t=T` (expiration day), underlying P&L on last day is `delta_{T-1} * (S_T - S_{T-1})` still accrues, then unwind occurs (see below) and payoff settles.

- Option payoff at expiration: European payoff `Payoff_T = max(S_T - K, 0)` for calls, `max(K - S_T, 0)` for puts, cash-settled. As short hedger, this is a cash outflow at `T` (negative contribution to P&L) in the amount `Payoff_T` per unit notional. Settlement is cash; no physical delivery beyond underlying unwind.

- Terminal hedge unwind: `EXPLICITLY REQUIRED`. At expiration close `T`, after underlying P&L on `S_T`, the hedge position `delta_T` (which equals `delta_{T-1}` if no rebalancing at expiration, or `delta_T` if rebalanced) is liquidated to `0` at `S_T`. Cost `cost_unwind = c * |0 - delta_{T}| * S_T` is charged at `T` (or `c * |0 - delta_{T-1}| * S_T` if no rebalancing at T). The repaired harness freezes unwind as `YES` — always unwind to zero, and always charge unwind cost at `S_T`. Final underlying position after unwind is `0`.

- Final underlying position: `0` after unwind. Not carried beyond expiration.

- Final P&L formula (short perspective, per episode, per policy, per cost level):
  ```
  P&L = P0
        + sum_{t=1}^{T} delta_{t-1} * (S_t - S_{t-1})
        - Payoff_T
        - sum_{t=0}^{T} cost_t
  ```
  where `sum_{t=0}^{T} cost_t` includes `cost_0` (initial), all daily `cost_t` for `t=1..T-1`, and `cost_unwind` at `T` (equivalently `cost_T`). Underlying price changes are close-to-close. Premium `P0` is included, cash accrual is zero so no `exp(r)` term. This is the sole formula.

- Loss transformation: `L = -P&L` per v1 Primary endpoint. Smaller CVaR (more negative hedging loss) corresponds to larger P&L.

- No phrase equivalent to "depending on implementation", "if used", or "unless otherwise specified". One convention frozen above.

### 5.3 Turnover (preserved)

- Turnover formula per episode: `turnover_episode = sum_{t=1}^{T} |delta_t - delta_{t-1}|` with `delta_0` as above, `T` maturity. Reported mean/SD/max/median per cost level.
- Pathological turnover: per-episode `>10.0` flagged, mean `>4.0` flagged, `>5%` episodes flagged makes level pathological. Blocks H3 success.

### 5.4 Position / hedge-ratio definition (preserved)

- `delta_t` target holding per unit option notional (shares per underlying unit). For calls/puts this is model delta (BS) or GRU network output (Deep). Raw model output, not clipped before thresholding.
- Nonfinite hedge-position: any episode with nonfinite `delta_t` at any step is invalid-policy for that strategy, excluded and counted; `>0.1%` fails level.
- Pathological position: per-step `|delta_t|>2.0` flagged, per-episode `max_t|delta_t|>2.0` flagged, mean `|delta_t|>1.2` flagged, `>1%` episodes flagged makes level pathological.

### 5.5 CVaR denominator, missingness, alignment, eligibility (preserved, P&L linked)

- CVaR_BS zero/nonfinite: if `|CVaR_BS| < 1e-12` or nonfinite, `Delta` nan/inf, CI [nan,nan], p nan, level cannot count toward two-level success. Do not substitute epsilon.
- Missing-price rule: missing underlying close, option quote, IV input, or `RejectedRecord` (crossed, missing side, unadjusted misuse) => episode excluded, counted as missingness, not imputed.
- Nonfinite hedging-loss rule: `L` nonfinite => episode missing for that strategy/level, triggers invalid-policy per v1 108-120, `>0.1%` triggers failure.
- Episode-exclusion accounting: all excluded/invalid/missing/nonfinite episodes enumerated per cost level with counts/rates/by reason; no selective omission.
- Same-split requirement: inception and expiration must fall in same split (final test `2023-11-22` to `2025-12-31`); cross-boundary invalid; tolerance 0 sessions strictly using XNYS calendar.
- SPY option eligibility: `SPY` only, European calls/puts only, American/weekly excluded, point-in-time definition required.
- Maturity: `5` to `30` trading days inclusive.
- Moneyness: `0.90` to `1.10` inclusive as `S_inception/K`.
- Alignment tolerance: `0` sessions gap, `0` minutes beyond frozen snapshot policy (final valid consolidated quote at or before `15:59:00` America/New_York, max age 5 minutes per canonical contracts). Underlying daily bar required for every hedging day; missing bar excludes episode.

### 5.6 Implementation readiness distinction (preserved)

- Harness contract: REPAIRED and FROZEN by this v2.
- Pipeline implementation: PIPELINE IMPLEMENTATION VERIFIED remains `NOT_READY`. This harness does not claim operational pipeline audited; follow-up readiness audit must verify before execution.

## 6. Complete executable Black-Scholes contract (REPAIRED)

Primary comparator remains `cost-adjusted Black-Scholes delta`. Secondaries remain `static Black-Scholes delta` (vol fixed at inception) and `dynamic daily-IV Black-Scholes delta` (daily recalibration). No role change. This section now freezes one exact parameter contract. No BS parameter remains conditional.

Checks source first per bounded-repair instruction: repository protocol `research_protocol_v1.md`, Amendment 020, split_policy, canonical_contracts, and committed configs contain no committed risk-free rate, dividend yield, IV solver bounds, or time convention frozen for hedging; therefore prospectively freeze below as benchmark simplifications before final-test access and document as prospective (not data-dependent).

- Underlying price source: `SPY` daily close `S_t` via XNYS session calendar (same as hedging underlying). Price uses `Decimal` close, `adjustment_status` explicit per `docs/data/canonical_contracts.md`.

- Option price source: end-of-day consolidated option mid-price `mid_t = (bid_t + ask_t)/2` where `bid_t` and `ask_t` are the final valid consolidated quotes at or before `15:59:00` America/New_York with max age 5 minutes. No other price source. If no valid quote, option price is missing.

- Risk-free rate: `r = 0.0` (continuously compounded, per annum decimal 0.00) for BOTH pricing/delta calculation AND cash-account accrual (Section 5). Removes all conditional SOFR-vs-zero wording from v1. Documented as prospective benchmark simplification; reading source first confirmed no existing committed r was frozen elsewhere. Single frozen value.

- Dividend treatment: `q = 0.0` continuous dividend yield (no dividends). Documented as prospective benchmark simplification; SPY discrete dividends are ignored for BS pricing/delta in this hedging benchmark. No dividend data fetched. Limitation stated prospectively: BS pricing with q=0 underestimates SPY forward when dividends are non-zero, but benchmark is deterministic and applied identically to all episodes; any dividend handling extension would require new amendment before execution. Single frozen value.

- Time to expiry: `T_t = remaining XNYS trading sessions from current session inclusive of current to expiration exclusive / 252.0`. That is, `T_t = (expiration_session_index - current_session_index) / 252.0` where session indices count only valid XNYS sessions under calendar `4.13.2` America/New_York. Same chronological session calendar as splits. Day-count is trading `252` per annum. At expiration `T = 0`. No calendar-day/365 convention. Single frozen convention.

- European terminal settlement: consistent with repository's European-option research contract. Payoff cash-settled as in Section 5 at expiration close `S_T`. No early exercise. Settlement at `T` as cash outflow for short.

- Black-Scholes formulas (with `r=0.0`, `q=0.0`, `T` as above, `sigma = IV`):
  - `d1 = (ln(S/K) + 0.5*sigma^2*T) / (sigma*sqrt(T))` if `T>0` and `sigma>0`.
  - `d2 = d1 - sigma*sqrt(T)`.
  - Call price `C = S * N(d1) - K * N(d2)` (with `r=0`, discount factor 1).
  - Put price `P = K * N(-d2) - S * N(-d1)`.
  - Call delta `Delta_call = N(d1)`.
  - Put delta `Delta_put = N(d1) - 1`.
  - `N(.)` is standard normal CDF.
  - At `T=0`: Call price `max(S-K,0)`, Put price `max(K-S,0)`, Call delta `1` if `S>K` else `0` (if `S==K`, `0.5`), Put delta `-1` if `S<K` else `0` (if `S==K`, `-0.5`).
  - At `sigma=0` limit with `T>0`: price collapses to discounted intrinsic with `r=0`, delta as above at `T=0` limit.

- IV solver: deterministic bracketed solver using already-installed `scipy.optimize.brentq` if available, otherwise deterministic bisection fallback with identical bounds/tolerance. Solver inputs: mid_price to invert (call or put according to episode option type), S, K, T, r=0, q=0.

- IV bounds: `sigma_min = 0.01` (1% vol), `sigma_max = 2.0` (200% vol). These Task-192 suggested bounds are prospectively frozen now as benchmark choices (no source-native bounds existed). Bounds are absolute vol (annual decimal).

- IV absolute/relative tolerance: `xtol = 1e-8` on sigma, `rtol = 1e-8` on price error normalized by S. Maximum iterations `1000`. Solver must achieve `|model_price(sigma_iv) - mid_price| < xtol * max(1, mid_price)` or equivalent price tolerance `1e-6 * S`.

- Arbitrage-bound validation (calls and puts) before solver: for call, arbitrage bounds `lower_call = max(S*exp(-q*T) - K*exp(-r*T), 0)` and `upper_call = S*exp(-q*T)`; with `r=0,q=0,T>=0` simplifies to `lower_call = max(S-K,0)`, `upper_call = S`. For put, `lower_put = max(K*exp(-r*T) - S*exp(-q*T), 0) = max(K-S,0)`, `upper_put = K`. If mid_price is outside `[lower_bound, upper_bound]` inclusive (allowing tolerance `1e-12` for Decimal noise), episode/quote is `INVALID_IV_ARBITRAGE_BOUND_VIOLATION`, recorded as invalid/missing for BS evaluation on that day, not clipped.

- No-solution behavior: if solver fails to bracket a root within `[sigma_min, sigma_max]` or fails to converge within tolerance/iterations, episode/quote is `INVALID_IV_NO_SOLUTION`, recorded as invalid/missing for BS evaluation, NO clipping to an implied vol that does not solve the price. No fallback to historical vol.

- Static-IV rule: `IV_static = IV_t0` solved once at episode inception close using `mid_0`, `S_0`, `K`, `T_0` (as above). This `IV_static` is held constant for all `t` in the episode. If inception IV is invalid/missing, episode is invalid for static variant.

- Dynamic-IV recalibration rule: `IV_dynamic(t) = IV_t` solved daily at each hedging close `t` using `mid_t`, `S_t`, `K`, `T_t`. Applied to next day's delta: for hedging at `t`, use `IV_dynamic(t)` for delta calculation at `t` (or at inception for `delta_0`, then each subsequent day uses yesterday's or today's IV per daily-close timing below). If daily IV is invalid/missing on day `t`, that day's delta uses previous valid IV (carry-forward), but the missingness is counted; if more than `20%` of days in episode have invalid IV, episode flagged as `INVALID_IV_PERSISTENT`.

- Daily-close application timing: recalibrated IV and resulting delta are applied at the same close `t` for the hedge position `delta_t` held into next day. That is, `delta_t` uses `IV_t` and `T_t` computed from close `t` market data (`S_t`, `mid_t`). No lookahead; tomorrow's hedge uses today's calibrated vol.

- Transaction-cost application for BS: identical to Section 5. `cost_t = c * |delta_t - delta_{t-1}| * S_t` with `delta_{-1}=0`, daily rebalance at close, terminal unwind `Yes` with cost `c * |0 - delta_T| * S_T` at `T`.

- European settlement per above, consistent with P&L payoff and unwind.

- No BS parameter remains conditional. All parameters are single frozen values as above.

## 7. H3 generator, hedger-seed, and baseline hierarchy (REVERIFIED)

### 7.1 Generator family (preserved)

- H3 generator family: `signature-score NSDE ONLY`. Conditional neural SDE trained with non-adversarial signature-kernel score, frozen as finite level-3 lead-lag signature + RBF-MMD with log-variance penalty, Euler/Ito `dt=1/252`, horizon `63`, Brownian dim `2`, state dim `2`. Per Amendment 020 Strategy B and SAP Section 1.
- WGAN role: `NONE` in H3 training paths. WGAN is not used for H3 synthetic data generation, hedger training, or primary hedging comparison.

### 7.2 Five audited NSDE members (preserved, recomputed)

| Member | Canonical member ID | Run prefix | Selected checkpoint SHA-256 | Selected Git blob | Final checkpoint SHA-256 | Final Git blob |
|---|---|---|---|---|---|
| seed-01 | v5-seed-01 | `5bdbaabd2fb257a7` | `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f` | `6820d07c0fb253a02337190d7c8683b5c01cb3f3` | `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4` | `6d0ead19a92c9c93422ab2b9c38b3d4bbbc5d7c` |
| seed-02 | v5-seed-02 | `62c7406cb3a2c642` | `9e6f8cd030d073d59324514d5a1ef6e87be6e3dbfb16b8cec7aa13928fd84f7a` | `592df5d33f9342901a1c9e4b9cae4c52f29c6a1c` | `b867af03b7a00dce6f4b34bcaf31896ddb891c9ba18e722dd2abb02ddf18ac8a` | `feef0df2fc721db3e1aea4ca80ea1b985e436` |
| seed-04 | v5-seed-04 | `77e7de9efabb7ce3` | `87d022152ba28f881f454a76aee1b572061e288fd3eee31b1ca52f2ba88cc35` | `3701888ef57f20132c77633f6aca2d6e6e3861` | `4927e6b6b575e20a20fc5ee225ac3400ad7e9524871b155d0cdfbf8ec9d4c72` | `c029db1e272117d73b6d596c2d4933aaf90bb` |
| seed-05 | v5-seed-05 | `1e8aa171993a1aba` | `3a71b12e1c0af08ea2c254fa6e162a09dd32dd47b399d6dc7585b264e33abef` | `808db090fe34f15b22d8062866846cde4d829` | `4d3b9475fbc9adba09b20822bd5941e367b4dc5b278f1ffb8d5954276a0a9c99` | `de846f5c671f492e4d909c99e7a534a1faeba` |
| reserve-j01 | reserve-j01 | `38c5113b27568e14` | `50d14095d95386c0fb7e1ee5ab43175272f02bfa84fbec3ddc6c8fe2a97326` | `38c9f8a0c8f97c64ce82e2ad38a0fea754a6a9` | `a4713691abb886a8151a6efa98dc2163068e147d1ea98d11d2c9a28b0e9b219` | `19620280adef3ae6224300e18d9d63496d334` |

All five are `GATE_PASS_VALID` per `structured_vol_v5_n5_family_analysis_v1.json`. Primary checkpoint for hedging is the selected `checkpoint.pt` (`best_epoch` per member); `checkpoint_final.pt` pinned for audit but not used as hedging seed input.

Independently recomputed from `data/processed/research/model/structured-volatility-neural-sde-v5/*/{checkpoint.pt,checkpoint_final.pt}` SHA-256 and `git hash-object`; verified byte-identical to v1 bindings.

### 7.3 Hedger training seed schedule (preserved as expected analysis hierarchy, not as existing policies)

- Hedger seeds are distinct from generator seeds. Generator seeds are model-init/data seeds (`8281` series, `9281`, `11281`, `12281`, `13281`); hedger seeds are GRU seeds below, not reused.
- Number of hedger seeds: `3`.
- Exact hedger seed values: `31001`, `31002`, `31003` (integer seeds for GRU weight init and training shuffle).
- Mapping: fully crossed — every generator member paired with every hedger seed. Total expected GRU hedger policies: `5 generators x 3 hedger seeds = 15` independently trained deep hedgers per cost level. `YES` every combination is the expected analysis set.
- Hedger training data per combination: synthetic paths from the single generator member assigned to that row, not pooled. Training hyperparameters not frozen here (see Section 7.5).

### 7.4 Aggregation hierarchy (clarified with single bootstrap target)

- Aggregation hierarchy (exact, preserved):
  1. Per-episode paired loss `(L_Deep, L_BS)` per episode per hedger policy.
  2. Per-policy `CVaR` and `Delta_CVaR` per cost level.
  3. Per-generator-member: `mean_h Delta^{g,h}` across its 3 hedger seeds per cost level.
  4. Cross-generator primary: `mean_g Delta_g` across 5 generator members per cost level.
- Primary hedger-seed aggregation: mean across hedger seeds within each generator member.
- Primary unit for seed uncertainty: SD `ddof=1` across the 5 generator-member mean Delta values per cost level (plus t-based 95% CI across members report-only).
- Secondary/report-only: SD across all 15 individual policies and per-member hedger SD.
- Bootstrap hierarchy: Section 4.2 single target — same 4-step mean-of-means applied per bootstrap replicate with synchronized index `I_b`.

### 7.5 Downstream training-contract status (NOT YET FROZEN — recorded, not resolved here)

Clarify ONLY the harness-side interpretation (per bounded-repair instruction: do not pretend policies already exist, do not freeze GRU architecture opportunistically):

- `DEEP-HEDGING TRAINING CONTRACT: NOT YET FROZEN`
- `POLICY IDENTITIES: NOT YET AVAILABLE`
- `FINAL-TEST AUTHORIZATION: IMPOSSIBLE UNTIL THOSE IDENTITIES EXIST AND ARE AUDITED`

The later deep-hedging training contract (separate governed task) must freeze: GRU architecture, training objective (CVaR/entropic), training horizon, optimizer, early stopping/checkpoint selection, synthetic path sample budget per generator, and whether policies are trained separately per cost level or as cost-conditioned single policy. Do not resolve that downstream scientific design inside this bounded harness repair unless existing committed source already freezes it — it does not. The expected crossed hierarchy `5×3` in this harness is the analysis-set size, not a bypass of that training contract.

## 8. Single-access final-test state machine (preserved)

### 8.1 States and current assignment

- Minimum states: `SEALED` — sealed, no scientific final-test process created since governance began; `AUTHORIZED_SINGLE_ACCESS` — explicit authorization bound harness/SAP/manifest/NSDE/hedger/BS identities granting single-use entitlement but process not yet started; `CONSUMED` — single-access entitlement permanently consumed (exactly one scientific process created regardless of outcome).
- Current state at this repair: `SEALED`.
- Current access count: `0`.
- Current entitlement: `NONE`.
- Current authorization: `NOT GRANTED`.
- Task 193: MUST NOT transition state. This repair binds the contract only.

### 8.2 Future semantics (frozen)

- Authorization must bind exact harness v2 SHA/blob plus SAP SHA/blob plus manifest `877caee3...` plus five NSDE identities (Section 7.2) plus hedger seeds `31001,31002,31003` as expected hierarchy plus BS primary `r=0/q=0` contract (Section 6) plus cost grid plus hedging P&L contract (Section 5). Authorization without these bindings invalid.
- Scientific final-test process creation permanently consumes single-access entitlement: first process opening sealed rows under authorized harness transitions to `CONSUMED` atomically.
- Consumption occurs even if process later fails: failure/crash/nonfinite/empty still counts as consumed. No reset to `SEALED`.
- No automatic retry/rerun/relaunch/second process/alternate policy selection after access/no rewriting because unfavorable. Any second attempt requires new governed exploratory amendment.

### 8.3 Preflight checks BEFORE sealed rows opened

All must pass immediately before single-access process opens final-test scientific rows; any failure aborts and does not consume entitlement (rows not yet opened), except where noted:

1. `Git HEAD` matches authorizing HEAD that includes this harness v2 and its audit — mismatch abort.
2. Tracked tree clean — no uncommitted changes to `reports/protocol/*`, `configs/research/*`, `data/manifests/*`, `src/neuralmarket/*` — dirty abort.
3. SAP identity: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` canonical `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` — mismatch abort.
4. Harness v2 identity: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v2.md` canonical SHA and Git blob as frozen in Amendment 098 — mismatch abort.
5. Split-manifest identity: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`, range `2023-11-22` through `2025-12-31`, sessions `528`, calendar XNYS, `final_test_access_status==sealed` — mismatch abort.
6. Registered NSDE identities: five selected checkpoint SHAs/blobs as in Section 7.2 byte-identical — mismatch abort.
7. Runtime identity: no network, no provider acquisition, no new generator training before hedger phase; hedger training uses only bound generator members — violation abort.
8. Expected process count `0` and access count `0` — existing `reports/research/evidence/structured_vol_v5_final_test_*` marker/result files count `0`, manifest still `sealed`, prior markers `0` — non-zero abort (already consumed/leaked).
9. Authorization identity: authorizing task/amendment hash present and cites harness v2 SHA/blob — missing abort.
10. Network prohibited: outbound TCP/HTTP disabled for single-access process — violation abort and consume if rows already opened.

Checks 1-9 are preflight (before sealed-row opens). Check 10 is runtime invariant.

### 8.4 Result persistence and access-marker semantics

- Access-marker location WITHOUT creating it now: `reports/research/evidence/structured_vol_v5_final_test_single_access_marker.json` (JSON with fields `harness_path`, `harness_canonical_sha256`, `harness_git_blob`, `sap_canonical_sha256`, `sap_git_blob`, `manifest_hash`, `nsde_members`, `hedger_seeds`, `bs_primary`, `authorization_task`, `access_count` (`1` after), `consumed_at_utc`, `process_pid`, `git_head_at_access`). NOT created by Task 193.

- Result persistence: original execution output durably preserved exactly once at `reports/research/structured_vol_v5_final_test_hedging_report_v1.json` plus `reports/research/evidence/structured_vol_v5_final_test_stdout.log` / `stderr.log` / `exit_code.txt`; no post-hoc regeneration; first committed result is confirmatory; no overwrite with better run. Full failure/missingness accounting per cost level with `N_total`, `N_valid`, `N_missing`, `N_invalid`, reasons, turnover/position flags, bootstrap diagnostics (including `B_valid` and valid fraction), seed-SD, marker linkage. No selective omission.

### 8.5 Retry/rerun prohibition

- No automatic retry, rerun, relaunch, second process, alternate policy selection, or rewriting because unfavorable. Committed result stands even if Delta positive or CI includes zero; new analysis is exploratory and labelled as such.

## 9. Task and band

- Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-193` — `R4`.
- No source code change, no harness v1 edit, no hedging execution, no deferred values, no network, no push.
- This harness v2 plus Amendment 098 are `R4` protocol artifacts; they repair prerequisite #8 defects pending re-audit. Deep hedging training contract remains `NOT YET FROZEN`, policies `NOT YET AVAILABLE`.

## 10. Verification at repair

- SAP canonical `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` — verified.
- Harness v1 canonical `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc` Git blob `b7c24126e8e070e745fed01a6122fe6d2bc51d2c` — preserved, not edited.
- Amendment 097 canonical `2b85791803b553a668a86ed464b5d44538a5eafee405c3f74b551caf090fec90` Git blob `dbfd2effc4022f9f916a3d5e2d60f83adb52efd2` — preserved.
- Split manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — metadata only, SEALED, 528 sessions.
- H2 `H2_NOT_SUPPORTED` preserved.
- NSDE checkpoint identities recomputed and matches v1 (Section 7.2).
- Harness v2 contains zero deferred tokens, zero conditional BS parameters, zero unresolved inference formulas, zero bootstrap-target equivocation, zero conditional premium/unwind wording.
- Final test `SEALED` access `0` entitlement `NONE` authorization `NOT GRANTED`.
- Deep-hedging training contract `NOT YET FROZEN`, policy identities `NOT YET AVAILABLE` — correctly recorded as downstream blocker, not pretended.

## 11. What this harness does not do

- Does not authorize final-test access.
- Does not create single-access marker or result files.
- Does not claim pipeline implementation verified.
- Does not train hedgers or run generators or execute bootstrap.
- Does not freeze GRU architecture/optimizer/synthetic budget post hoc (that is downstream training-contract work).
- Does not change H3 cost grid, L, B, RNG, five NSDE members, three hedger seeds, H2, Gate thresholds, or single-access state machine.

*This harness is append-only. Any change requires new governed amendment, not silent edit. Next governed action is the independent repair-audit task NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-AUDIT-194.*
