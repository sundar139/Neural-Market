# Amendment 057 — V5 Five-member Family Analysis

**Date:** 2026-08-22
**Task:** `NM-R4-V5-N5-FAMILY-ANALYSIS-099`
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `5491346d1845d6f7ac701e44f307139afa6a2400`
**Analysis commit:** `b194cfc` — `analysis(research): compute frozen v5 n5 family analysis`
**Prerequisite audit:** `NM-R4-V5-POST-EXECUTION-WORKTREE-AUDIT-098`
**Prerequisite verdict:** VALIDATED WITH NON-BLOCKING FINDINGS
**Status:** COMPLETED PENDING INDEPENDENT AUDIT. Read-only numerical analysis of committed artifacts only. No execution, training, simulation, Gate rerun, validation, network, push, or final-test access.

## 1. Purpose and governing contract

This amendment records the prospectively frozen five-member completed-model family analysis required by Amendment 055 §8. It is an extension from the historical valid completed-model N=4 sensitivity artifact to N=5, not a redesign.

The effective frozen sources were read before computation:

- `reports/protocol/research_protocol_amendment_040.md` — scalar, summary, CV, LOMO, and runtime-sensitivity preregistration;
- `reports/protocol/research_protocol_amendment_041.md` — corrected three-way validity semantics, seed-01 aliases, definitive RBF exclusion, and formula preservation;
- `reports/protocol/research_protocol_amendment_048.md` — reserve/completed-model counting semantics and primary-versus-reserve distinction;
- `reports/protocol/research_protocol_amendment_055.md` §8 — prospective post-j01 N=5 family contract;
- `reports/protocol/research_protocol_amendment_056.md` — post-execution worktree repair closure; no scientific contract change.

The exact analysis implementation was reused:

- historical implementation: `reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py`;
- N=5 driver: `reports/research/evidence/structured_vol_v5_n5_family_analysis.py`;
- historical N=4 result: `reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json`.

The N=4 result remains historical and byte-immutable. The N=5 driver reused the canonical scalar order, `statistics.mean`, `statistics.stdev` with `ddof=1`, `statistics.median`, min/max, frozen CV exclusions, and unconditional LOMO formulas. No historical N=4 result was overwritten.

## 2. Frozen family membership and accounting

Completed-model N is exactly `5` and Gate-pass count is exactly `5`.

Numerically included completed members, in frozen order:

1. `seed-01` — role `primary`, runtime `CPU`, normalized analytical status `GATE_PASS_VALID`;
2. `seed-02` — role `primary`, runtime `CPU`, normalized analytical status `GATE_PASS_VALID`;
3. `seed-04` — role `primary`, runtime `CPU`, normalized analytical status `GATE_PASS_VALID`;
4. `seed-05` — role `primary`, runtime `CUDA`, normalized analytical status `GATE_PASS_VALID`;
5. `reserve-j01` — role `reserve-contributed completed member`, runtime `CUDA`, committed status `GATE_PASS_VALID`.

The normalization preserves source terminology:

- seed-01 committed production status: `INTERNAL_GATE_PASSED_FINAL_REFIT_FROZEN` with `internal_gate_passed=true`, mapped under Amendment 041 §6.1 to the frozen analytical `GATE_PASS_VALID` status;
- seed-02 committed adjudication: `PRIMARY_VALID_COMPLETED`, with committed training report `gate_passed=true`, mapped to `GATE_PASS_VALID`;
- seed-04 committed adjudication: `PRIMARY_VALID_COMPLETED`, with committed training report `gate_passed=true`, mapped to `GATE_PASS_VALID`;
- seed-05 committed adjudication: `PRIMARY_VALID_COMPLETED`, with committed training report `gate_passed=true`, mapped to `GATE_PASS_VALID`;
- reserve-j01 committed adjudication: `GATE_PASS_VALID` directly.

Primary seed-03 remains permanently retained in history and failure accounting:

- raw closure status: `ATTEMPTED_FAILED_GOVERNANCE`;
- protocol violation: `DOUBLE_SCIENTIFIC_INVOCATION`;
- analytical status: `GOVERNANCE_INVALID`;
- `primary_family_admissible=false`;
- numerical inclusion: `NO`.

Reserve-j01 contributes to the completed-model estimator as a separately labelled reserve member. It does not become a primary seed, does not erase seed-03, and does not alter permanent primary-roster accounting.

The five-seed requirement is `SATISFIED` through the completed-model analytical set. Final-test controls remain sealed.

## 3. Exact frozen 13 scalars

The analysis contains exactly these 13 cross-member scalars, in this order, with no additions or substitutions:

### Training

1. `initial_selection_total_loss`
2. `best_selection_total_loss`
3. `best_epoch`
4. `final_epoch`
5. `selection_loss_improvement_absolute`

### Gate

6. `variance_ratio`
7. `terminal_dispersion_ratio`
8. `path_uniqueness_fraction`
9. `return_acf1_abs_diff`
10. `drift_diffusion_rms_ratio`

### Report-only

11. `terminal_wasserstein_normalized`
12. `acf_rmse`
13. `acf_max_error`

ACF diagnostic lags remain exactly `[1, 2, 3, 5, 10, 20]`. RBF internal diagnostics, including `initial_internal_rbf` and `best_internal_rbf`, remain excluded from cross-member scalar analysis. Abs-return ACF, squared-return ACF, conditional variance, and RBF diagnostics were not promoted into the 13-scalar family analysis.

## 4. Input provenance and raw matrix

The authoritative value/status artifacts were read-only and unchanged relative to the starting HEAD. The result artifact records each value source, source field, SHA-256, and Git blob.

| Member | Value artifact SHA-256 | Value Git blob | Status artifact SHA-256 | Status Git blob |
|---|---|---|---|---|
| seed-01 production Gate | `4604231cfc5d26f61808b65ce9269a120ccb44c2c96a590853341e31c9f14bc6` | `b84c4b81401f9fa89d775a161b14f0f782e6e38e` | same artifact | same blob |
| seed-02 training report | `f1c998f4ed4bf117ec61131f9d4ca113235bc48fbc11855164d07235efe0c34f` | `d62ca14261c907f21901742e98da2cbc6cb61c40` | seed-02 adjudication `5ce2170fc6caf6d0aab07ad576caa93b432281c72482e9b2675488f2d60ccac1` | `657e1afe7e80639b16bbcfecd0efc48bd1e7574d` |
| seed-04 training report | `40c2389c649132c819c82c7398589b3d6f4eb6f47ae9411b3813a23ca9f87364` | `816eff3d75ffdc54050de4571fada172958e86f2` | seed-04 adjudication `502cce04bd0774baa6ebbaa6bc10bd8434e553c4cf01a60db1eeb886d924feef` | `4d574c045379d8b19ef0d4ef47ac46e22d6ed38c` |
| seed-05 training report | `86bf6c0fe605643a2bd9a04811ad39911ad7ed9e96da9671b8fb6b29bc3dcdcd` | `4727d5138cfe50105b78ec51b75561b1f4ca5b8a` | seed-05 adjudication `74a8c4c7196bd1227db78548f764085fa72637bddc6efe850912e6948349ee00` | `581079adcdc3191cef9ae5d95c3b9da0652d6879` |
| reserve-j01 training report | `74017ec4ff8a8798b7eb369904d0a126594f55f3c3bda2bd259b4e90d673b615` | `8f43d3c5931b6a46ca274f7a7e55a22dfe0c66fe` | reserve-j01 adjudication `50135d8a472ec45c167b3d8115305bc34874eaafe93623a9d703f7eda9013c32` | `c2f03002b72ddeffc93279127f1feb6606754240` |

Reserve-j01 identity was independently verified as:

- prefix: `38c5113b27568e14`;
- full config: `38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605`;
- adjudication SHA-256: `50135d8a472ec45c167b3d8115305bc34874eaafe93623a9d703f7eda9013c32`;
- family methodology identity: `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`.

The raw matrix contains exactly 5 members × 13 scalars = 65 expected cells, 65 populated finite cells, and zero missing/non-finite cells. No imputation or replacement policy was invoked.

## 5. Summary statistics

For each of the 13 scalars over exactly the five included members, the result contains:

- arithmetic mean;
- sample standard deviation with `ddof=1`;
- median;
- minimum;
- maximum;
- CV only where the frozen meaningfulness rule permits.

The frozen CV rule is: `CV = sample SD / mean` only for a nonzero ratio-scale mean. CV is omitted for bounded `path_uniqueness_fraction`, near-zero `return_acf1_abs_diff`, and near-zero `drift_diffusion_rms_ratio`, with the omission reason carried in the artifact. Epoch-valued scalars retain the historical N=4 numeric treatment.

No confidence intervals, p-values, hypothesis tests, effect sizes, ranks, weighted means, wins/losses, composite scores, or new thresholds were added.

The artifact contains 13 summary rows and records the exact serialized values.

## 6. Unconditional LOMO

LOMO is unconditional and uses every included numerical member exactly once as the omitted member:

- omitted `seed-01`;
- omitted `seed-02`;
- omitted `seed-04`;
- omitted `seed-05`;
- omitted `reserve-j01`.

For every scalar and omission, the remaining four valid completed members were used. The result contains:

- 13 scalar groups;
- 5 omitted-member cases per group;
- 65 expected scalar/omission analyses;
- 65 completed analyses;
- no conditional omission;
- no missing group or member.

The formulas are unchanged from the historical implementation:

- `absolute_change = LOMO_mean - full_mean`;
- `relative_change = absolute_change / |full_mean|` only where meaningful under the frozen CV/near-zero rule.

LOMO is reported quantitatively and is not used to make an influence-significance claim or define a new acceptance threshold.

## 7. Runtime heterogeneity disclosure

Runtime composition is recorded exactly:

- historical CPU members: `seed-01`, `seed-02`, `seed-04`;
- CPU N: `3`;
- CUDA members: `seed-05`, `reserve-j01`;
- CUDA N: `2`.

The analysis discloses runtime/backend heterogeneity as a limitation and source of variation. Backend is a labelled execution covariate, not a causal explanation. This task performs no CPU-vs-CUDA significance test, no regression, no causal backend-effect estimate, no claim of CPU/CUDA numerical identity, and no seed-only attribution. No new hardware-sensitivity methodology was created.

H2 remains `UNRESOLVED_PENDING_WGAN_COMPARATOR`.

## 8. Durable result artifact

The durable result is:

`reports/research/structured_vol_v5_n5_family_analysis_v1.json`

Measured after final bytes and after the analysis commit:

- FILE SHA-256 (Windows worktree bytes): `84e53a3e77e6eea12a1449aa08763766c6106d7fe16eb36d1285f0bd71bdf564`;
- Git blob after final bytes: `7c10e622db3415cae53fb9547d6ebef15decbb76`;
- analysis commit: `b194cfc`.

The artifact schema contains the task ID, source HEAD, family methodology identity, member roles, excluded seed-03 history, runtime labels, authoritative source identities, 5×13 raw matrix, N=5 summaries, CV flags, complete 13×5 LOMO output, ACF lag disclosure, RBF exclusion, CPU N=3/CUDA N=2 disclosure, no-causal-backend and no-significance restrictions, no-new-threshold restriction, H2 unresolved status, and final-test sealed status.

The historical N=4 artifact remains unchanged:

`reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json`

Its Git blob remains `1b9ed4edc84b4111701a30e38bc16b86a9fe8166`.

## 9. Scientific preservation and firewalls

No scientific execution or analysis input mutation occurred. Task-099 performed:

- runner invocations: `0`;
- training: `0`;
- simulation: `0`;
- Gate reruns: `0`;
- validation: `0`;
- external validation: `0`;
- final-test access: `0`;
- provider/scientific network: `0`;
- Git-remote network: `0`;
- j02 decisions: `0`;
- j03 decisions: `0`.

Protected identities remain unchanged:

- reserve-j01 classification: `GATE_PASS_VALID`;
- completed-model N: `5`;
- Gate-pass count: `5`;
- runner Git blob: `a79a79f477429d66cc7fc0c75db7c751726ee577`;
- authorization Git blob: `236ac739e346cdc559dd3704b0df37eb190110aa`;
- recipe: `79325e0ccbc25a09b863461ab56b722e19f8df36`;
- j01 adjudication SHA-256: `50135d8a472ec45c167b3d8115305bc34874eaafe93623a9d703f7eda9013c32`.

The final chronological test remains `SEALED`.

## 10. Verification and append-only status

Independent verification produced:

- input gate: 5 members, 13 scalars, 65 finite cells;
- focused analysis test: `1 passed`;
- targeted Ruff: passed for the N=5 driver and focused test;
- targeted mypy: passed for the N=5 driver;
- independent summary/LOMO recomputation: zero discrepancies;
- summaries: 13;
- LOMO: 13 × 5 = 65 complete cells;
- source artifacts: unchanged;
- N=4 artifact: byte-immutable;
- scientific execution: none.

Amendments 040, 041, 048, 055, and 056 remain immutable. This Amendment 057 is append-only and intentionally does not embed its own future SHA-256 or Git blob.

## 11. Required next action

Independent read-only audit of the frozen N=5 family analysis, artifact provenance, source immutability, and firewalls. No scientific execution is authorized or implied by this amendment. The final test remains sealed.

---

*Amendment 057 records the frozen five-member completed-model family analysis: five valid numerical members including separately labelled reserve-j01, seed-03 retained as governance-invalid history, exactly 13 scalars, unconditional 13×5 LOMO, descriptive CPU N=3/CUDA N=2 disclosure without causal inference, H2 unresolved pending the WGAN comparator, and final test sealed.*
