# Amendment 099 — V5 Empirical 95% CVaR Estimator Freeze

Date: 2026-08-25
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-CVAR-ESTIMATOR-REPAIR-195`
Risk: `R4`
Branch: `main`
Starting HEAD: `22540dc4b771de01749463edcd4c5a10195c386a`
Safety branch: `safety/pre-v5-harness-cvar-repair-22540dc` at `22540dc4b771de01749463edcd4c5a10195c386a`
Prerequisite: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-AUDIT-194` — `VALIDATED_EXCEPT_CVAR_ESTIMATOR_PRECISION`
Harness v1 preserved: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v1.md` at canonical SHA `f12490e310b6d23431b09425296c49c7a943090c925f5a9b5a6334ace89cacdc` Git blob `b7c24126e8e070e745fed01a6122fe6d2bc51d2c`
Harness v2 preserved: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v2.md` at canonical SHA `7a28cb149e58804919babdcb70d19e6c960d97634776ea592bb67acb67ec7ec6` Git blob `676c5932ee4ee38db56d37b6c80a8943b0025237`
H2 state: `H2_NOT_SUPPORTED` preserved (WGAN comparator campaign COMPLETE, 5 valid WGAN members including reserve, NSDE not no-worse per Amendment 095)
Status: APPEND-ONLY CVaR-ESTIMATOR REPAIR — one-issue prospective contract repair; no training, no generator execution, no hedger execution, no Gate, no inference execution, no bootstrap execution, no validation, no external validation, no network, no push, no final-test row access

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, primary endpoint Delta_CVaR with `L=-P&L` and 95% CVaR, experimental governance, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, final-test prerequisite checklist Strategy B, gating rule)
- H2 Amendment 095: `reports/protocol/research_protocol_amendment_095.md` at `fa28687` (H2_NOT_SUPPORTED adjudication)
- SAP v1: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at canonical SHA `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` (defines Delta_CVaR with `CVaR_0.95`, alpha 0.95, `L=-P&L`, success rule, missingness contract, but does not pin finite-sample CVaR estimator interpolation/tie convention beyond label)
- Harness v1: `structured_vol_v5_final_test_single_access_harness_v1.md` at `f12490e310b6.../b7c24126...` (CVaR estimator not explicitly pinned beyond label)
- Amendment 097: `research_protocol_amendment_097.md` at `2b85791803b5.../dbfd2eff...` (preserved)
- Harness v2: `structured_vol_v5_final_test_single_access_harness_v2.md` at `7a28cb149e58.../676c5932...` (CVaR estimator residual noted as non-blocking in Task-194, now promoted)
- Amendment 098: `research_protocol_amendment_098.md` at `487a666f1093.../40666ace...` (preserved)
- Task-194 audit evidence: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-REPAIR-AUDIT-194` — `VALIDATED_EXCEPT_CVAR_ESTIMATOR_PRECISION` (CVaR finite-sample convention promoted to load-bearing reproducibility requirement)

Conflicts: None — SAP/harness v1/v2 all define `alpha=0.95`, `L=-P&L`, `Delta_CVaR = (CVaR_Deep - CVaR_BS)/CVaR_BS`, cost grid `0/10/50`, CBB `L=20 B=10000 PCG64(9491)`, but none pins the empirical quantile/tail fractional-weighting convention; this repair adds it without contradicting source.

## 2. Source CVaR contract status

- Alpha: `0.95` (95% CVaR / Expected Shortfall, tail mass `0.05`)
- Exact prior definition: `CVaR_0.95` of hedging loss `L=-P&L` per `research_protocol_v1.md` Primary endpoint (95% CVaR primary, entropic secondary) and `Delta_CVaR` formula per v1 lines 70-72; SAP v1 repeats `primary risk endpoint 95% CVaR` and `Delta_CVaR` with `alpha=0.95`; no finite-sample estimator (sorting, fractional tail, tie, interpolation, VaR membership, NaN handling) is pinned in any committed source
- Source-native estimator found: NONE — exhaustive read of `research_protocol_v1.md`, Amendment 020, SAP v1, harness v1, harness v2, Amendment 098 confirms only the label `CVaR_0.95` and `L=-P&L` are frozen; no empirical Expected Shortfall algorithm (e.g., top-k mean, fractional weighting, quantile+conditional mean, scipy helper) is committed
- Source location: `research_protocol_v1.md` lines 37, 53, 67-72; SAP v1 lines 37-39; harness v1 Section 3/4; harness v2 Section 3/4 — all label-only
- Repair needed: YES — one prospective deterministic estimator frozen now before hedger training or final-test access (Section 3)

## 3. Exact empirical CVaR algorithm (frozen prospectively)

For finite loss vector `x = [x_1,...,x_N]` with all invalid/missing episodes already removed under the already-frozen missingness contract (so `N` is count of valid hedging losses for that policy/cost level/replicate).

Sort ascending stable numeric order: `x_(1) <= ... <= x_(N)` using stable sort (preserves input order for ties).

Let `alpha = 0.95`.

Let `tail_mass = (1 - alpha) * N = 0.05 * N`.

Let `k = floor(tail_mass)`.

Let `f = tail_mass - k` (fractional part, `0 <= f < 1`).

Define `ES_0.95` / `CVaR_0.95` as:

- if `tail_mass <= 0`: `INSUFFICIENT_SAMPLE` (requires N>=1 with alpha<1; with alpha=0.95 this only at N=0; already handled by N>=40 precondition).

- if `k == 0` and `f > 0` (i.e., `0 < tail_mass < 1`, occurs at N < 20): `CVaR = x_(N)` (single largest loss). With frozen minimum N=40 this branch is not reached for valid samples, but deterministically defined.

- if `k >= 1` and `f == 0`: `CVaR = mean of the k largest losses = ( sum_{i=N-k+1}^{N} x_(i) ) / k`.

- if `k >= 0` and `f > 0`: `CVaR = [ sum_{i=N-k+1}^{N} x_(i) + f * x_(N-k) ] / tail_mass`, where the sum over k largest losses is empty (0) when k=0. The boundary observation `x_(N-k)` is the next observation just below the top k, fractionally weighted by f. This gives exactly 5% empirical tail mass with fractional weight on the boundary observation.

Example at `N=40`: `tail_mass=2.0`, `k=2`, `f=0`, `CVaR = mean of 2 largest losses`. At `N=41`: `tail_mass=2.05`, `k=2`, `f=0.05`, `CVaR = (sum of 2 largest + 0.05*x_(39)) / 2.05`.

Properties frozen:

- Sort: ascending stable numeric order (Python sorted / NumPy sort stable kind, deterministic).

- Ties: retained as distinct episode observations; equal losses ordered by stable sort and counted as separate empirical mass; fractional boundary weighting is by ordered empirical mass, not by unique value.

- NaN/inf: excluded only under already-frozen episode missingness rules BEFORE CVaR (Section 5.5 and harness v2 Section 4.1). CVaR never sees NaN/inf as input; if all N removed, N=0 => INSUFFICIENT_SAMPLE.

- Weights: equal episode weight `1/N`. No observation weighting.

- Interpolation: NONE beyond the explicit fractional boundary mass above. No `np.quantile`, no linear interpolation of VaR, no scipy helper.

- VaR role: `VaR_0.95` is report-only boundary value not separately used to redefine membership. When `f==0`, `VaR = x_(N-k+1)` is the smallest loss among the k largest; when `f>0`, `VaR = x_(N-k)` is the boundary observation. VaR is not used to define a separate strict `>VaR` vs `>=VaR` membership; membership is exactly the fractional tail-mass rule above.

- Deterministic: estimator deterministic for all N given same valid loss vector and sort. No randomness.

No alternative CVaR estimator permitted (`np.quantile`+conditional mean, top-ceil tail mean, strict `>VaR` tail, `>=VaR` tail, scipy expected-shortfall helper, or another estimator).

## 4. Binding into Delta_CVaR and every bootstrap replicate

The exact SAME estimator from Section 3 is used for:

- `CVaR_Deep(g,h)` per cost level per NSDE member per hedger seed,
- `CVaR_BS(g,h)` per cost level per policy (BS loss vector is policy-independent but evaluated per replicate with same estimator),
- the unresampled point estimate,
- and every CBB replicate.

For each CBB replicate `b`:

- Apply synchronized `I_b` (synchronized CBB index sequence length N from harness v2 Section 4.2) to construct resampled Deep loss vector for each `(g,h)` and BS loss vector.

- Apply the exact Section-3 CVaR estimator independently to each resampled Deep and BS loss vector to obtain `CVaR_Deep^{g,h,b}` and `CVaR_BS^{g,h,b}`.

- Then compute `Delta(g,h,b) = (CVaR_Deep^{g,h,b} - CVaR_BS^{g,h,b}) / CVaR_BS^{g,h,b}` with denominator rule `|CVaR_BS| >= 1e-12` and finite else replicate/level invalid under existing contract.

- Then `mean_h` per generator member and `mean_g` primary `Delta_primary^{b}` per harness v2 Section 4.2 hierarchy.

No implementation may switch estimator between point estimate and bootstrap replicates, or between cost levels / NSDE members / hedger seeds.

## 5. Sample-size and failure semantics

- Minimum N: `40` (preserved from CBB precondition `N >= 2*L = 40`). At `alpha=0.95` and `N=40`, `tail_mass=2.0`, so two effective tail observations are represented; this is sufficient for the fractional-tail estimator and no stricter minimum is required by committed source. Preserve `N>=40` as frozen minimum.

- Missing/nonfinite episode rate rules unchanged (no imputation, `>0.1%` nonfinite triggers failure), no silent denominator change, no alternative fallback CVaR.

- For a bootstrap replicate with valid resampled N (after filtering to valid per missingness contract): CVaR must be deterministic via Section 3. If Deep or BS CVaR becomes nonfinite or denominator invalid (`|CVaR_BS|<1e-12` or nonfinite), that replicate becomes invalid according to existing `B_valid` semantics.

- Existing bootstrap validity requirement `B_valid == 10000` (all 10000 replicates finite) remains unchanged (Section 4.4 default prospective threshold `1.0`), unless committed source proves otherwise (none does).

## 6. Preservation

All other harness-v2 scientific constants remain exactly as frozen in v2 and are not altered by this one-issue repair:

- P&L timeline: short-option convention, premium Included `P0=(bid+ask)/2` consolidated final valid quote at or before 15:59 America/New_York max age 5 minutes, `delta_{-1}=0`, daily rebalance at close with `cost_t=c*|delta_t-delta_{t-1}|*S_t`, underlying P&L `delta_{t-1}*(S_t-S_{t-1})`, payoff `max(S_T-K,0)`/`max(K-S_T,0)` cash-settled, terminal unwind Yes `cost_unwind=c*|0-delta_T|*S_T` at `S_T` final position 0, cash `r=0`.

- Transaction costs: `0 bps (0.0000), 10 bps (0.0010), 50 bps (0.0050)` proportional.

- Black-Scholes: `r=0`, `q=0` (continuous dividend yield, limitation stated), `T_t = remaining XNYS trading sessions /252.0`, `sigma` bounds `[0.01,2.0]`, `scipy.optimize.brentq` else bisection fallback, tolerance `xtol=1e-8`, price tolerance `1e-6*S`, max iter `1000`, arbitrage bounds, no-solution invalid not clipped, call `C=S*N(d1)-K*N(d2)` put `P=K*N(-d2)-S*N(-d1)` delta `N(d1)` / `N(d1)-1`, `T=0` handling, static IV fixed at inception, dynamic daily recalibration with carry-forward and persistent failure threshold, cash settlement, costs identical.

- Paired CBB: `L=20`, `B=10000`, `PCG64(9491)`, single synchronized target `I_b` applied to all `5x3` policies, mean_h then mean_g hierarchy, denominator `|CVaR_BS|>=1e-12`.

- Percentile CI: `lower=np.quantile(S,0.025,method='linear')` `upper=np.quantile(S,0.975,method='linear')` with `method='linear'` (NumPy 2.4.6 default).

- Inclusive two-tail p-value: `q_minus=count(Delta_primary^{b}<=0)/B_valid` `q_plus=count(Delta_primary^{b}>=0)/B_valid` ties at zero inclusive both, `p_raw=min(1.0,2*min(q_minus,q_plus))` continuity NONE, failed replicate excluded.

- Holm `{H3}` with `p_Holm(H3)=p_raw(H3)`, H2 no p-value.

- Five NSDE members `seed-01` `5bdbaabd2fb257a7` `452f70058.../6820d07...`, `seed-02` `62c7406cb3a2c642` `9e6f8cd030.../592df5...`, `seed-04` `77e7de9efabb7ce3` `87d022152.../370188...`, `seed-05` `1e8aa171993a1aba` `3a71b12e.../808db0...`, `reserve-j01` `38c5113b27568e14` `50d14095.../38c9f8...` all `GATE_PASS_VALID`; hedger seeds `31001,31002,31003` fully crossed `5x3=15` expected per cost level as analysis hierarchy (training contract not yet frozen).

- H2 remains `H2_NOT_SUPPORTED`.

- Single-access state machine `SEALED -> AUTHORIZED_SINGLE_ACCESS -> CONSUMED` fail-closed, preflight 10 checks, marker/result persistence, failure-before-result, no retry/rerun/relaunch/second/network.

No other scientific constant changed in this repair.

## 7. Harness v3 record

Harness v3 path: `reports/protocol/structured_vol_v5_final_test_single_access_harness_v3.md`
Harness v3 canonical SHA-256: `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7`
Harness v3 Git blob: `8d8220c084425c902825e754b0c24a3069e08f2b`
Status: `CVAR_REPAIRED_PENDING_INDEPENDENT_AUDIT`
Task: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-CVAR-ESTIMATOR-REPAIR-195`
Supersedes for future authorization: `structured_vol_v5_final_test_single_access_harness_v2.md`
Sole reason: `Task-194 CVaR-estimator residual promoted to load-bearing reproducibility requirement before single-access confirmatory execution`
Harness v3 commit: `6505aba65c1fc8b55905771c8ccb9d1733aa0df5` (`docs(research): freeze exact v5 empirical cvar estimator`)

## 8. Final-test preservation

- Final test: `SEALED`
- Final-test access count: `0`
- Final-test entitlement: `NONE`
- Final-test authorization: `NOT GRANTED`
- Scientific final-test execution: `0`
- Deep hedging execution: `0`
- Deep-hedging training contract: `NOT FROZEN`
- Training: `0`
- Gate: `0`
- Model inference: `0`
- Bootstrap execution: `0`
- Validation: `0`
- External validation: `0`
- Network: `0`
- Push: `0`

No final-test scientific rows were read. Metadata inspection only. Harness v1, harness v2, Amendment 097, Amendment 098 remain byte-identical.

## 9. Commit record

- Harness v3 committed alone at `6505aba65c1fc8b55905771c8ccb9d1733aa0df5` (`docs(research): freeze exact v5 empirical cvar estimator`)
- This Amendment 099 commits separately at its own hash (see verification)

No amend, no rebase, no reset, no push.

This amendment is append-only, contains no self-referential hash.
