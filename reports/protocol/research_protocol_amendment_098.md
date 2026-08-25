# Amendment 098 — V5 Final-Test Single-Access Harness Repair

Date: 2026-08-25
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-193`
Risk: `R4`
Branch: `main`
Starting HEAD: `ede2d4f57741cdf4a1e68309be7938be7a7c8032`
Safety branch: `safety/pre-v5-final-test-harness-repair-ede2d4f` at `ede2d4f57741cdf4a1e68309be7938be7a7c8032`
Prerequisite: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-AUDIT-192` — `REPAIR_REQUIRED`
Task-192: `REPAIR_REQUIRED` (four blocking groups plus bootstrap-target equivocation)
Harness v1 preserved: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md` at canonical SHA `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc` Git blob `b7c24126e8e070e745fed01a6122fe6d2bc51d2c` — byte-identical, not edited
H2 state: `H2_NOT_SUPPORTED` preserved (WGAN comparator campaign COMPLETE, 5 valid WGAN members including reserve, NSDE not no-worse per Amendment 095)
Status: APPEND-ONLY HARNESS REPAIR — bounded document repair; no training, no Gate, no hedger execution, no generator execution, no model inference, no bootstrap execution, no validation, no external validation, no network, no push, no final-test row access

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, primary endpoint Delta_CVaR, experimental governance, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist Strategy B, gating rule)
- H2 Amendment 095: `reports/protocol/research_protocol_amendment_095.md` at `fa28687` (H2_NOT_SUPPORTED adjudication, WGAN N=5 SATISFIED with reserve)
- SAP v1: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9`
- Amendment 096 (SAP freeze): `reports/protocol/research_protocol_amendment_096.md` at canonical SHA `a80293300b14f06ae5a7f410088af96d32f82284de3fca1255adec26b1853c4b` Git blob `50340b489891d43284d8cadfd3452f43dfbebf75`
- Harness v1: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md` at canonical SHA `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc` Git blob `b7c24126e8e070e745fed01a6122fe6d2bc51d2c` (REPAIR_REQUIRED, preserved)
- Amendment 097: `reports/protocol/research_protocol_amendment_097.md` at canonical SHA `2b85791803b553a668a86ed464b5d44538a5eafee405c3f74b551caf090fec90` Git blob `dbfd2effc4022f9f916a3d5e2d60f83adb52efd2` (preserved)
- Split manifest metadata: `data/manifests/split_manifest_v1.json` at manifest identity `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test `2023-11-22` through `2025-12-31`, 528 XNYS sessions, calendar XNYS `4.13.2` America/New_York, purge 90 + embargo 10, excluded boundary `2023-07-03` to `2023-11-21` 100 sessions, training `2018-05-01` to `2021-12-31` 926, validation `2022-05-26` to `2023-06-30` 275, metadata only)
- Split policy: `docs/data/split_policy.md` (chronological splitting, purging/embargoing, normalizers fit on training only)
- Engineering contract: `docs/engineering/agent-contract.md` (R4, DISCOVER->DECIDE->MUTATE->VERIFY->REPORT, final-test access requires explicit authorization)
- Task-192 audit evidence: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-AUDIT-192` `REPAIR_REQUIRED` (defects A-E)

Conflicts: None — SAP, v1, Amendment 097, and Task-192 audit are consistent on preserved values (cost grid 0/10/50, L=20, B=10000, RNG 9491, five NSDE members, three hedger seeds, H2_NOT_SUPPORTED).

## 2. Harness repair

Harness v2 path: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v2.md`
Harness v2 canonical SHA-256: `7a28cb149e58804919babdcb70d19e6c960d97634776ea592bb67acb67ec7ec6`
Harness v2 Git blob: `676c5932ee4ee38db56d37b6c80a8943b0025237`
Harness v2 status: `REPAIRED_PENDING_INDEPENDENT_AUDIT`
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-193`
Supersedes for future authorization: `structured_vol_v5_final_test_single_access_harness_v1.md`
Reason: `Task-192 load-bearing harness defects`
Harness v2 commit: `bf94850559526744f3df303aad2328bdb5477706` (`docs(research): repair v5 final-test single-access harness`)

Harness v1 remains byte-identical and is not superseded for archival audit trail; only future-authorization binding moves to v2.

## 3. Exact repaired contracts

### 3.1 Bootstrap target, CI, and p-value (repaired from defects C and E)

- Paired circular block bootstrap preserved `L=20`, `B=10000`, `PCG64(9491)`, two-sided 95%, alpha 0.05.
- Bootstrap target now SINGLE and exact: for each replicate `b`, draw one episode index sequence `I_b` of length `N` (circular blocks `L=20` with replacement, concatenated and truncated), apply same `I_b` to every paired Deep/BS loss vector for all `5×3` policies at that cost level; recompute per-policy `CVaR_Deep^{g,h,b}`, `CVaR_BS^{g,h,b}`, `Delta^{g,h,b} = (CVaR_Deep - CVaR_BS)/CVaR_BS` (nan if `|CVaR_BS|<1e-12` or nonfinite); per-generator `Delta_g^{b} = mean_h Delta^{g,h,b}`; primary `Delta_primary^{b} = mean_g Delta_g^{b}`. Original point estimate uses same mean-of-means hierarchy on unresampled set. No alternative equivalent target.
- CI is percentile CBB interval: `lower = np.quantile(S, 0.025, method='linear')`, `upper = np.quantile(S, 0.975, method='linear')` where `S = {Delta_primary^{b} finite}` and `B_valid = |S|`, using NumPy `2.4.6` default `method='linear'` (linear interpolation, type 7) checked in repository runtime.
- p-value exact: `q_minus = count(Delta_primary^{b} <= 0)/B_valid`, `q_plus = count(Delta_primary^{b} >= 0)/B_valid`, ties at zero count in both tails inclusive, `p_raw = min(1.0, 2*min(q_minus,q_plus))`, continuity `NONE`, failed/nonfinite replicate excluded from `B_valid` and counted in diagnostics, minimum valid-bootstrap fraction `B_valid == B` (`10000` all finite) as default prospective threshold (unless pre-registered tolerance frozen before execution). Null `Delta=0`, test statistic `Delta_primary`, two-sided via doubling smaller inclusive tail.
- Numeric Holm set remains `{H3}` with `p_Holm(H3)=p_raw(H3)`. No H1/H2 p-values fabricated.

### 3.2 Hedging P&L and transaction-cost accounting (repaired from defect D)

- Cost levels preserved `0 bps (0.0000), 10 bps (0.0010), 50 bps (0.0050)` with `cost_t = c * |delta_t - delta_{t-1}| * S_t`, `delta_{-1}=0`.
- Sign convention: hedger is `SHORT` one European option per episode (short call/put per eligibility). Premium `P0 = (bid_0+ask_0)/2` consolidated mid-price at inception (final valid quote at or before `15:59:00` America/New_York, max age 5 minutes) is `INCLUDED` as cash inflow at `t=0`. If `P0` missing/invalid, episode invalid/missing.
- Initial cash: `cash_0 = P0 - c*|delta_0 - 0|*S_0`.
- Cash-account accrual: `r_cash = 0.0` (no accrual).
- Daily hedge: `delta_t` at close `t`, cost `cost_t` at `S_t`, underlying P&L `delta_{t-1}*(S_t - S_{t-1})` for `t=1..T`.
- Payoff: `max(S_T-K,0)` calls, `max(K-S_T,0)` puts, cash-settled outflow for short at `T`.
- Terminal unwind: `EXPLICITLY REQUIRED` — liquidate `delta_T` to `0` at `S_T`, charge `cost_unwind = c*|0 - delta_T|*S_T` at `T`. Final underlying position `0`.
- Final P&L: `P&L = P0 + sum_{t=1}^{T} delta_{t-1}*(S_t - S_{t-1}) - Payoff_T - sum_{t=0}^{T} cost_t` where `sum` includes initial, daily, and unwind costs. Loss `L = -P&L`. No phrase "depending on implementation" remains.

### 3.3 Complete Black-Scholes contract (repaired from defects A and B)

- Primary `cost-adjusted Black-Scholes delta` and secondaries `static` and `dynamic daily-IV Black-Scholes delta` roles preserved.
- Underlying `SPY` close `S_t` via XNYS calendar.
- Option mid `mid_t = (bid_t+ask_t)/2` consolidated final valid quote at or before `15:59:00` America/New_York max age 5 minutes.
- Risk-free rate: `r = 0.0` for BOTH pricing/delta and cash accrual. All conditional SOFR-vs-zero wording removed. Read source first — no committed r was frozen elsewhere — so prospective `0.0` frozen now.
- Dividend: `q = 0.0` continuous yield (no dividends). Prospective benchmark simplification, limitation stated, no dividend data fetched.
- Time to expiry: `T_t = remaining XNYS trading sessions from current to expiration exclusive / 252.0` (expiration_session_index - current_session_index over 252, XNYS calendar `4.13.2`). At expiration `T=0`.
- Formulas with `r=0,q=0`: `d1 = (ln(S/K)+0.5*sigma^2*T)/(sigma*sqrt(T))`, `d2=d1-sigma*sqrt(T)`, `C=S*N(d1)-K*N(d2)`, `P=K*N(-d2)-S*N(-d1)`, `Delta_call=N(d1)`, `Delta_put=N(d1)-1`; at `T=0` call price `max(S-K,0)` etc.
- IV solver: deterministic bracketed `scipy.optimize.brentq` if available else bisection fallback, bounds `sigma_min=0.01` to `sigma_max=2.0` (prospective Task-192 suggested bounds frozen now), tolerance `xtol=1e-8` on sigma, price tolerance `1e-6*S`, max iter `1000`. Same solver for static and dynamic.
- Arbitrage bounds: call `lower=max(S-K,0)` `upper=S`, put `lower=max(K-S,0)` `upper=K` (with `r=0,q=0`). Violation => `INVALID_IV_ARBITRAGE_BOUND_VIOLATION`, episode/quote invalid/missing, not clipped.
- No-solution: `INVALID_IV_NO_SOLUTION`, invalid/missing, not clipped to non-solving vol.
- Static-IV: `IV_static` solved once at inception using `mid_0,S_0,K,T_0` held constant; missing => episode invalid for static variant.
- Dynamic-IV: `IV_t` solved daily at `t` using `mid_t,S_t,K,T_t`, applied to `delta_t` at same close `t` for next day's hedge; missing day carries forward previous valid IV but counted, >20% missing days flags `INVALID_IV_PERSISTENT`.
- Transaction-cost application identical to hedging (Section 3.2) including unwind at `T`.
- European cash settlement at expiration as above. No BS parameter remains conditional. Single frozen value for each field.

## 4. H3 seed hierarchy (reverified, training contract still not frozen)

- Generator family: `signature-score NSDE ONLY`, WGAN `NONE`.
- Five members: `seed-01` (`5bdbaabd2fb257a7` selected `452f70058...` blob `6820d07...` final `c7b9be5d...` blob `6d0ead...`), `seed-02` (`62c7406cb3a2c642` selected `9e6f8cd030...` blob `592df5...` final `b867af03...` blob `feef0df...`), `seed-04` (`77e7de9efabb7ce3` selected `87d022152...` blob `370188...` final `4927e6b6...` blob `c029db...`), `seed-05` (`1e8aa171993a1aba` selected `3a71b12e...` blob `808db0...` final `4d3b9475...` blob `de846f...`), `reserve-j01` (`38c5113b27568e14` selected `50d14095...` blob `38c9f8...` final `a4713691...` blob `196202...`) — all `GATE_PASS_VALID`, recomputed.
- Hedger seeds expected: `31001, 31002, 31003` (distinct from generator seeds). Fully crossed `5×3=15` per cost level is the intended analysis hierarchy for future execution.
- Training contract now recorded only: `DEEP-HEDGING TRAINING CONTRACT: NOT YET FROZEN` and `POLICY IDENTITIES: NOT YET AVAILABLE`. This repair does not pretend policies exist and does not freeze GRU architecture/optimizer/synthetic budget/early stopping opportunistically. That downstream training contract must decide whether policies are separately trained per cost level or cost-conditioned — not resolved here. `FINAL-TEST AUTHORIZATION: IMPOSSIBLE UNTIL THOSE IDENTITIES EXIST AND ARE AUDITED`.

## 5. Single-access state machine (preserved)

- Current: `SEALED`, access `0`, entitlement `NONE`, authorization `NOT GRANTED`.
- Future: `SEALED -> AUTHORIZED_SINGLE_ACCESS -> CONSUMED` fail-closed; authorization must bind harness v2 SHA/blob `7a28cb149e588.../676c5932...` plus SAP `76de0a1a.../8ffe6d96...` plus manifest `877caee...` plus five NSDE identities plus hedger seeds `31001-31003` as expected hierarchy plus BS contract `r=0/q=0` plus cost grid plus P&L contract; preflight 10 checks before sealed rows; marker at `reports/research/evidence/structured_vol_v5_final_test_single_access_marker.json` (not created); result persistence at `reports/research/structured_vol_v5_final_test_hedging_report_v1.json` plus stdout/stderr/exit; no retry/rerun/relaunch/second/network.

## 6. Final-test preservation

- Final test: `SEALED`
- Final-test access count: `0`
- Final-test entitlement: `NONE`
- Final-test authorization: `NOT GRANTED`
- Scientific final-test execution: `0`
- Deep hedging execution: `0`
- Deep-hedging training contract: `NOT YET FROZEN`
- Training: `0`
- Gate: `0`
- Model inference: `0`
- Bootstrap execution: `0`
- Validation: `0`
- External validation: `0`
- Network: `0`
- Push: `0`

No final-test scientific rows were read. Metadata inspection only. Harness v1 and Amendment 097 remain byte-identical.

## 7. Commit record

- Harness v2 committed alone at `bf94850559526744f3df303aad2328bdb5477706` (`docs(research): repair v5 final-test single-access harness`)
- This Amendment 098 commits separately at its own hash (see verification)

No amend, no rebase, no reset, no push.

This amendment is append-only, contains no self-referential hash.
