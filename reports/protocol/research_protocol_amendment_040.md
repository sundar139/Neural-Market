# Amendment 040 — V5 Seed-05 Runtime-Heterogeneity Sensitivity Preregistration

**Date:** 2026-08-21
**Task:** NM-R4-V5-SEED-05-SENSITIVITY-PREREGISTRATION-061
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `0b52d7dfc197ff3bbb50c097b342edfc301b28f3`
**Safety branch:** `safety/pre-v5-seed05-sensitivity-prereg-0b52d7d`
**Prior task:** NM-R4-V5-SEED-05-EXECUTION-DECISION-059 (Amendment 039)
**Prior audit:** NM-R4-V5-SEED-05-METHODOLOGY-AUDIT-060 — VALIDATED WITH NON-BLOCKING FINDINGS
**Validated decision:** `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT`
**Status:** PREREGISTRATION — unconditional, frozen BEFORE seed-05 authorization/execution/result. No training, no --execute, no authorization artifact, no validation, no final-test access.

## 1. Purpose and timing

This amendment pre-registers the exact runtime-heterogeneity sensitivity analysis that MUST be applied after seed-05 if it is later authorized and executed. It is unconditional and frozen BEFORE any of: seed-05 authorization, execution, Gate result, training curve, checkpoint, or scientific result is observed.

Methodology decision `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT` (Amendment 039) is not reopened. Audit 060 validated it with non-blocking findings. This amendment only freezes prospective sensitivity/disclosure obligations.

Seed-05 remains NOT_AUTHORIZED, NOT_ATTEMPTED at this commit. No authorization artifact is created here.

## 2. Baseline (authoritative, not re-decided)

- Historical admissible: seed-01 (CPU, EXISTING_FROZEN, 5bdbaabd2fb257a7), seed-02 (CPU, PRIMARY_VALID_COMPLETED, 62c7406cb3a2c642), seed-04 (CPU, PRIMARY_VALID_COMPLETED, 77e7de9efabb7ce3). All on CPU lineage, deterministic enabled.
- Inadmissible retained: seed-03 (ATTEMPTED_FAILED_GOVERNANCE / DOUBLE_SCIENTIFIC_INVOCATION, e333325c804d95d2) — not counted in any family summary.
- Prospective: seed-05 (replicate 12281, model_init 12281, data 12282, eval 8283 COMMON_FIXED, config 1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897, prefix 1e8aa171993a1aba) — NOT_AUTHORIZED, expected CUDA with runtime identity 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada (runtime-identity-v1, .venv-gpu CUDA 13.2 / torch 2.13.0+cu132 / driver 610.47 / RTX 4070 CC 8.9 / determinism enabled).
- Current admissible count 3; if seed-05 succeeds admissibly then 4. Five-seed requirement still not met; extra-member decision remains separately governed.
- Hardware/runtime not frozen in original family contract (Amendment 039 section 2.1); scientific family identity 730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719 unchanged; runtime identity is separate execution provenance.

Original protocol gate: research_protocol_v1 line 99 (five seeds), Amendments 020-022, 039. Gate-v2 spec hash f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469, gate_yaml blob d9705ef9a11da3e21760015bb2a27fa408018bb5, seeds 7777/7778/8801 COMMON_FIXED.

## 3. Frozen family-level statistics

Reported after seed-05 (if admissible) across admissible members only. Each scalar below gets: N, member IDs included, arithmetic mean, sample SD (unbiased, ddof=1; SD=NA when N=1), median, min, max, CV (= SD/mean) only where mean !=0 and statistic is ratio-scale (not bounded proportions or near-zero baselines); otherwise CV omitted with reason.

Sources (consistent per member):
- seed-01: reports/research/structured_vol_v5_production_gate_v2.json (training + gate.criteria + gate.report_only)
- seed-02/04/05: reports/research/structured_vol_v5_replicates/<prefix>/training_report.json (initial_selection_total, best_selection_total, best_epoch, final_epoch, gate_diagnostics)

### 3.1 Training (selection-phase, frozen objective: level-3 lead-lag + RBF-MMD + variance penalty)

Every member provides consistently:

1. initial_selection_total_loss (initial_selection_total)
2. best_selection_total_loss (best_selection_total)
3. best_epoch
4. final_epoch
5. selection_loss_improvement = initial_selection_total - best_selection_total (absolute) and relative improvement = (initial - best)/initial where initial !=0

If any component (e.g., initial_internal_rbf / best_internal_rbf) is not consistently available for seed-01, it is excluded from family summary or reported only for members where available with explicit N.

### 3.2 Gate-v2 (six criteria; thresholds FROZEN, not changed)

From gate_diagnostics / gate.criteria under fixed seeds 7777/7778/8801:

- variance_ratio (= generated_daily_variance / real_daily_variance)
- terminal_dispersion_ratio (= generated_terminal_std / real_bootstrap_terminal_std)
- path_uniqueness = path_uniqueness_fraction (criterion 4)
- return_ACF1_absolute_error = return_acf1_abs_diff = |generated_return_acf1 - real_return_acf1| (criterion 5, band [null, 0.25])
- drift_diffusion_RMS_ratio = drift_diffusion_rms_ratio (criterion 6, band [null, 0.5])

Pass/fail bands: [0.5,2.0], [0.5,2.0], [0.99,null], [null,0.25], [null,0.5] respectively, plus criterion 1 selection_loss_improvement (best < initial). No threshold change, no composite PASS score invented, no aggregation of unlike criteria.

### 3.3 Report-only (frozen, consistently available)

- normalized_terminal_Wasserstein = terminal_wasserstein_normalized (primary report-only scalar)
- raw-ACF aggregates where consistently available: acf_rmse, acf_max_error (computed over lags [1,2,3,5,10,20] at gate seed 7777), and retained per-lag raw ACF diagnostics (real_acf / generated_acf) as carried in gate_diagnostics — reported descriptively if needed but family summary scalars are the two aggregates above plus Wasserstein.

Additional report-only values (generated_abs_return_acf, generated_sq_return_acf, cond_var_log_correlation, etc.) are not family-summary scalars; they remain per-member diagnostics and are not summarized as formal family statistics unless amendment explicitly adds them prospectively.

No new composite score is created.

## 4. Mandatory leave-one-member-out (LOMO)

Unconditional and mandatory regardless of seed-05 outcome.

For EVERY scalar in section 3, after seed-05 completes:

A. Compute full-family summary (section 3 summaries) using all admissible members (N=3 if seed-05 fails/inadmissible; N=4 if seed-05 admissible).

B. Recompute the same summary N times, each time excluding exactly one admissible member. Omitted-member set is {seed-01, seed-02, seed-04} plus seed-05 if admissible.

Per statistic report:

- full-family value (mean; also median/min/max/SD as per section 3 — delta reported on mean as primary, others shown side-by-side)
- each LOMO value
- absolute change = LOMO_mean - full_mean
- relative change = absolute / |full_mean| where |full_mean| > 1e-12 and statistic is ratio-scale; otherwise relative omitted with note "not meaningful"
- largest-influence member = argmax absolute change (tie: list all)

No post-result threshold defines "acceptable" change (no binary PASS/FAIL is invented). Sensitivity is described quantitatively. If a frozen threshold already existed for a statistic (Gate bands), it is not repurposed as a LOMO acceptability cutoff.

LOMO is required even if seed-05 Gate fails, is atypical, or best_epoch/final_epoch is extreme (see section 7).

## 5. CPU-only vs mixed-runtime comparison

Because seed-01/02/04 are CPU and prospective seed-05 is CUDA, the following comparison is mandatory when seed-05 succeeds and is admissible:

- HISTORICAL_CPU_SUBSET (N=3): seed-01 (cpu), seed-02 (cpu), seed-04 (cpu)
- MIXED_RUNTIME_SET (N=4): seed-01 (cpu), seed-02 (cpu), seed-04 (cpu), seed-05 (cuda)

For every family scalar in section 3 report side-by-side:

- CPU-only summary (mean, SD, median, min, max per section 3)
- mixed-runtime summary (same)
- absolute difference = mixed_mean - cpu_mean
- relative difference = absolute / |cpu_mean| where meaningful (same meaningfulness rule as section 4)

Each member row labels backend explicitly: seed-01 cpu, seed-02 cpu, seed-04 cpu, seed-05 cuda.

Interpretation constraint (frozen):

- Backend is a labelled execution covariate.
- This design (3 CPU vs 1 CUDA) is NOT balanced enough to identify an independent backend effect.
- Do NOT estimate or claim a statistically identified backend effect.
- Do NOT fit a regression coefficient and interpret it causally.
- Required disclosure verbatim or equivalent: "backend is a labelled execution covariate, but this design is not balanced enough to identify an independent backend effect. The purpose is sensitivity/disclosure, not causal hardware estimation."

## 6. H2 / stability claim rules (frozen interpretation)

Before any seed-05 result, the following are frozen:

Prohibited unless a later separately governed balanced experiment directly supports them:

- "all observed variation is due to seed"
- "CUDA and CPU are equivalent" / "CPU/CUDA deterministic numerical equivalence is claimed"

Required disclosure for ANY later H2-style statement about stability across seeds / variance across seeds / epoch stability / family robustness:

- Observed dispersion may contain both replicate RNG variation AND execution backend variation.

Robust-language condition:

- If conclusions remain qualitatively similar in CPU-only subset, mixed-runtime set, AND LOMO analysis, language equivalent to "the conclusion is robust to inclusion of the CUDA member under the pre-registered sensitivity analysis" is allowed.
- If conclusions materially differ (e.g., a Gate criterion median/mean shifts across a frozen band, H2 variance conclusion reverses, or the mixed set materially changes min/max or SD relative to CPU-only), require narrowed language and explicit reporting of the difference — do NOT paper over it.

Absent an already frozen binary threshold for "materially differ", use quantitative disclosure rather than post-hoc PASS/FAIL. Do NOT define "materially differ" after seeing the result. Quantitative tables from sections 4-5 are the disclosure mechanism.

## 7. Seed-05 outcome handling (unconditional)

Sensitivity design does not change regardless of seed-05 result:

- passes all six Gate-v2 criteria
- fails one or more Gate-v2 criteria
- unusually high/low selection loss or improvement
- extreme best_epoch / final_epoch
- any other atypical diagnostic

Do NOT:

- remove seed-05 because it looks inconvenient
- rerun seed-05
- change the seed
- change the backend (remains CUDA)
- change Gate thresholds or bands
- change family statistics or sensitivity statistics
- add/remove analyses selectively

If seed-05 execution is protocol-valid but scientifically fails (Gate FAIL or v1 failure criteria: nonfinite loss, no valid checkpoint, >0.1% nonfinite paths, dispersion collapse <10% real, vol >10x, leakage, accounting mismatch), retain and report it per frozen family contract (failed_in_primary counted, not silently discarded, not relabelled).

If seed-05 execution itself is governance/protocol-invalid (e.g., DOUBLE_SCIENTIFIC_INVOCATION, invocation count >1, device/runtime mismatch, missing authorization), follow existing failure-retention contract: ATTEMPTED_FAILED_GOVERNANCE, retained, inadmissible.

Never silently discard. Under-filled-family policy (Amendment 022 section 11) still governs final-test blocking.

## 8. RNG / runtime interpretation (frozen)

Why backend heterogeneity matters:

- torch.Generator(device="cuda") and CPU generators do not produce an assumed identical random stream for equal integer seeds. Device-aware generators are distinct.
- CUDA and CPU kernels may differ in floating-point operation/reduction order, libraries, and hardware, so even with determinism flags numerics can differ.
- Deterministic execution means reproducibility within the specified runtime contract, not cross-backend bitwise equivalence. Hardware/runtime equivalence is NOT claimed.

Actual frozen call paths (as repaired in Amendment 036, runner blob 7b46e0f6c805687977cd685ebb97741bd4243cbe, execution_contract v5 blob 84a59c4d966b349be705a8a29fad07f81282ebdc):

- Global RNG: src/neuralmarket/models/neural_sde.py:26 set_deterministic_seeds(seed) -> random.seed / np.random.seed / torch.manual_seed / torch.cuda.manual_seed_all ; also src/neuralmarket/research/structured_vol_experiment.py:213,279 set_deterministic_seeds(model_init_seed) at train start and refit. model_init_seed is the global-RNG control.
- Per-device generators: src/neuralmarket/research/neural_sde_trainer_v3.py:218-219,367-368 (and v1/v2 equivalents) make_generator -> torch.Generator(device=device).manual_seed(data_seed). Used for: noise_gen (training Brownian noise), order_gen (randperm minibatch/window order), selection_loss stochastic paths (noise_gen), refit noise+perm. simulation: src/neuralmarket/models/structured_vol_sde.py:270-283 simulate_structured(model, context, seed=eval_seed) via torch.Generator.manual_seed(eval_seed).
- Where the CUDA setup uses torch.cuda.manual_seed_all: it is via the global set_deterministic_seeds path (model_init_seed) — that seeds both CPU and CUDA global RNGs. Per-device training stochasticity is via explicit torch.Generator(device=...) instances seeded with data_seed (not via manual_seed_all alias alone). Do not overstate torch.cuda.manual_seed_all as the per-generator mechanism where explicit Generators are used.
- Runtime identity (orthogonal to config_hash): schema runtime-identity-v1 (src/neuralmarket/research/runtime_identity.py blob 817ba53e2474c6e8dd7ecf15d64e0766e75f73e9), built after resolve_device + configure_device_determinism, before execution_started, before any scientific compute. Prospective CUDA identity 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada is authoritative prospectively (Amendment 036 + schema v2 known_runtime_identities).

Runtime identity remains 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada for the currently validated prospective CUDA environment; a driver/CUDA/cuDNN change intentionally drifts the identity and requires a newly bound authorization.

## 9. Preregistration timing and append-only

- This sensitivity protocol is frozen BEFORE seed-05 authorization, execution, Gate result, training curve, checkpoint, or any seed-05 scientific result is observed. Evidence: starting HEAD 0b52d7d has zero seed-05 authorizations (reports/research/authorizations/structured_vol_v5_primary_training lists only seed-02..04 historic v1; no 12281/1e8aa... v2 auth), zero seed-05 execution markers (no reports/research/structured_vol_v5_replicates/1e8aa171993a1aba), zero training invocations for 12281.
- If seed-05 execution is protocol-valid but Gate-fails: retained per section 7.
- If seed-05 execution is governance-invalid: ATTEMPTED_FAILED_GOVERNANCE, retained.
- Seed-03 remains inadmissible and retained (structured_vol_v5_seed_03_primary_closure.json).
- Successful seed-05 yields only four admissible members; fifth-member decision remains separately governed.
- Final test remains sealed (sealed split 2023-11-22 onward per split_manifest_v1); no final-test access by this amendment.

This amendment is append-only; prior amendments unchanged.

## 10. What this amendment does NOT do

- Does not authorize seed-05, create an authorization artifact, or permit --execute.
- No scientific training, no validation, no external validation, no final-test, no hedging, no reserve execution, no provider/network call.
- Does not change Gate thresholds, model/scientific code, schedule, or determinism.
- Does not retroactively change historical CPU lineage.

## 11. Required next action and audit

Next task MUST independently audit Amendment 040 (read-only) before any seed-05 authorization artifact can be created. No execution may be inferred from this amendment alone.

Audit must verify: explicit/unconditional statistics, LOMO mandatory, CPU-only vs mixed mandatory, backend labelled, no causal backend claim, no post-result threshold invention, no result-contingent redesign permitted, and zero seed-05 authorization/training/execution markers.

---
*Amendment 040 is append-only sensitivity preregistration. It freezes unconditional runtime-heterogeneity disclosure before seed-05 results and does not authorize execution.*
