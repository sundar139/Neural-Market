# Amendment 059 — V5 WGAN Comparator Preregistration

**Date:** 2026-08-22
**Task:** `NM-R4-V5-WGAN-COMPARATOR-PREREGISTRATION-103`
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `42cfe4412880c044d721635ef6ab7e4d65d17c73`
**Prerequisite audit:** `NM-R4-V5-N4-IMPLEMENTATION-PROVENANCE-AUDIT-102`
**Prerequisite verdict:** `VALIDATED WITH NON-BLOCKING FINDINGS`
**Status:** PREREGISTRATION ONLY — no WGAN source, implementation, model construction, training, simulation, Gate execution, authorization, validation, external validation, final-test access, N4/N5 recomputation, j02/j03 decision, network, or push.

## 1. Purpose and governing boundary

This amendment freezes the future WGAN comparator methodology before any WGAN
result exists. The machine-readable contract is:

`reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json`

The governing transitions are:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

The accepted Neural-SDE state is unchanged:

- reserve-j01: `GATE_PASS_VALID`;
- completed-model N: `5`;
- Gate-pass count: `5`;
- N4 historical result: `IMMUTABLE`;
- N5 family analysis: `VALIDATED`;
- H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`;
- final chronological test: `SEALED`.

This amendment creates no WGAN implementation, configuration used by live
training, runner, authorization, or scientific artifact. Future implementation,
authorization, audit, and execution remain separate governed tasks.

## 2. Controlling H2 contract

The exact frozen H2 statement is:

> The signature-score training objective is more stable across seeds and epochs than adversarial (WGAN) training.

The original protocol records the primary generator comparison as:

- signature-score neural SDE;
- WGAN neural-CDE neural SDE.

The original experimental governance also requires:

- at least five independent neural seeds;
- failed seeds reported and not silently discarded;
- comparable compute and hyperparameter-search budgets between signature and adversarial models;
- chronological splitting with purge and embargo;
- training-only normalizers;
- no final-test hyperparameter selection;
- separate market-period and training-seed uncertainty.

The exact failure criteria remain the frozen v1 criteria: nonfinite training or
validation loss, no valid checkpoint, more than 0.1% nonfinite generated paths,
terminal dispersion collapse below 10% of real data, excessive volatility,
leakage, or unreconciled accounting.

### 2.1 Source reconciliation

The controlling records were read before any methodological choice:

- `reports/protocol/research_protocol_v1.md`, H2, core scope, experimental governance, and failure criteria;
- `reports/protocol/research_protocol_amendment_020.md` §§2.1, 2.4, 2.5, 4.4, and 8;
- `reports/protocol/research_protocol_amendment_055.md` §§7–9;
- `reports/protocol/research_protocol_amendment_057.md` §§2–3, 7, and 9;
- `reports/protocol/research_protocol_amendment_058.md` §§1, 6, and 8;
- `reports/protocol/research_protocol_amendment_037.md` §2;
- `reports/research/original_research_contract_reconciliation_v1.json`.

No material contract conflict was found. The following classification was
frozen:

| Comparator item | Classification | Resolution |
|---|---|---|
| WGAN comparator family | ALREADY_FROZEN | Retain the adversarial WGAN neural-CDE family. |
| Architecture class | ALREADY_FROZEN | Use a Neural-CDE generator and conditional path critic; exact widths and controls were previously underspecified. |
| Conditioning | IMPLIED_BY_EXISTING_CONTRACT | Reuse the four past-only v5 context features; exact WGAN wiring was previously underspecified. |
| Path representation | IMPLIED_BY_EXISTING_CONTRACT | Reuse 63 daily log-return outputs and the v5 window regime; exact WGAN control representation was previously underspecified. |
| WGAN objective | ALREADY_FROZEN | Use adversarial WGAN training; WGAN-GP details were previously underspecified. |
| Horizon | IMPLIED_BY_EXISTING_CONTRACT | Freeze context lookback 22, horizon 63, and `dt=1/252`. |
| Data and splits | ALREADY_FROZEN | Use the frozen chronological manifest and training-only internal fit/selection data. |
| Five independent seeds | ALREADY_FROZEN | Freeze five WGAN primary identities. |
| Compute/search comparability | ALREADY_FROZEN | Use a singleton configuration and equal generator update-equivalent proxy; disclose the unavoidable critic-update cost difference. |
| Metrics | IMPLIED_BY_EXISTING_CONTRACT | Use cross-family path diagnostics already frozen where supported and operationalize H2 stability metrics without comparing incompatible losses. |
| H2 decision rule | PREVIOUSLY_UNDERSPECIFIED | Freeze the descriptive dominance rule in §7. |

## 3. Frozen WGAN model contract

The future comparator is a conditional WGAN-GP with a Neural-CDE generator and
a conditional Neural-CDE path critic. This is the minimum executable contract
consistent with the existing WGAN neural-CDE family label; no exotic architecture
or post-result redesign is permitted.

### 3.1 Generator

- Hidden state: 64.
- Initial state: two hidden layers, 64 SiLU units each, mapping the four normalized context features plus a 32-dimensional static latent vector to the hidden state.
- Control: three channels — normalized time and two cumulative standard-normal noise channels.
- Per-step control increment: `[dt, sqrt(dt) * epsilon_1, sqrt(dt) * epsilon_2]` over 63 intervals.
- Vector field: two hidden layers, 64 SiLU units each, producing a 64-by-3 control-vector field.
- Solver: fixed explicit Euler controlled differential update; 63 intervals; `dt=1/252`; no adaptive solver and no hidden-state clamp.
- Readout: two hidden layers, 64 SiLU units each, mapping hidden state plus context to one unconstrained daily log-return increment.
- Output: 63 raw daily log-return increments. Cumulative returns are derived only for path encoding and diagnostics.

### 3.2 Critic

- Conditional path critic implemented as a Neural-CDE encoder.
- Input control: normalized time, cumulative return divided by the training-fit cumulative-return scale, and the four broadcast normalized context features.
- Control dimension: 6.
- Initial state: two hidden layers, 64 SiLU units each, mapping context to a 64-dimensional hidden state.
- Vector field: two hidden layers, 64 SiLU units each, producing a 64-by-6 control-vector field.
- Solver: the same fixed explicit Euler grid and `dt=1/252`.
- Output: one terminal scalar; no sigmoid, softmax, or probability interpretation.

### 3.3 Conditioning, noise, and normalization

The conditioning features are exactly:

1. `prev_daily_return`;
2. `prev_5d_cumulative_return`;
3. `prev_22d_cumulative_return`;
4. `prev_22d_realized_volatility`.

They use only the strictly preceding 22 returns. The per-feature z-score
normalizer is fitted from training-derived windows only. The cumulative-return
scale is also fit from training data only. There is no batch normalization, layer
normalization, spectral normalization, or learned output normalization.

The static latent dimension is 32 with independent standard-normal values per
path. Temporal control noise has dimension 2 with independent standard-normal
increments per interval. Training noise is bound to `data_seed`; post-training
evaluation uses common fixed `eval_seed=8283` and does not count as an independent
training replicate.

### 3.4 Objective and optimization

The adversarial objective is WGAN-GP:

- critic maximizes `mean(D(real)) - mean(D(fake)) - lambda_gp * gradient_penalty`;
- generator minimizes `-mean(D(fake))`;
- gradient penalty is the squared deviation of the full path-input gradient L2 norm from 1 on uniformly interpolated real/fake paths with context held fixed;
- `lambda_gp=10.0`;
- weight clipping is disabled;
- critic/generator update ratio is `5:1`.

The optimizer is Adam with:

- learning rate `1e-4`;
- betas `(0.0, 0.9)`;
- epsilon `1e-8`;
- weight decay `0`;
- no gradient clipping.

All Linear layers use PyTorch default `reset_parameters` semantics. There is no
result-dependent initialization.

### 3.5 Training, selection, and checkpoint

- Batch size: `64`.
- Maximum: `400` generator epochs.
- Critic updates: five per generator batch update.
- Early stopping: 40 generator epochs without improvement.
- Selection metric: the existing Gate-v2 `terminal_wasserstein_normalized` diagnostic computed on the internal selection tail only.
- Direction: lower is better.
- Tie-break: earliest generator epoch, then lexicographically smallest identity.
- Real reference: 1024 circular moving-block-bootstrap paths, block length 22, bootstrap seed 8801.
- Generated selection paths: 1024, generated-path seed 7777.
- Refit: after checkpoint selection, refit the selected contract on all eligible training windows for exactly the selected best generator epoch, with no new validation observation or hyperparameter choice.

CUDA determinism is fail-closed: requested device `cuda`, expected resolved
device `cuda`, deterministic algorithms enabled, cuDNN benchmark disabled,
cuDNN deterministic enabled, and no CPU fallback.

## 4. Frozen data, split, and compute fairness

The data contract is the unchanged `data/manifests/split_manifest_v1.json`:

- manifest hash field: `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`;
- training: 2018-05-01 through 2021-12-31, 926 sessions, identity hash `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605`;
- internal fit/selection: training-only, `fit_fraction=0.8`, non-overlapping target intervals, chronological embargo gap;
- context lookback: 22 sessions;
- path horizon: 63 sessions;
- `dt=1/252`;
- official validation: identity retained but not accessed for WGAN search, checkpoint selection, or H2;
- external validation: CLOSED and no new construction;
- final test: 2023-11-22 through 2025-12-31, 528 sessions, SEALED and inaccessible.

The Neural-SDE family uses one fixed scientific configuration rather than a
hyperparameter-search phase. Therefore the WGAN search space is the singleton
configuration `wgan-gp-default-v1`:

- generator hidden state 64;
- critic hidden state 64;
- latent dimension 32;
- learning rate `1e-4`;
- gradient penalty coefficient 10;
- critic/generator ratio 5:1;
- batch 64;
- maximum 400 generator epochs;
- patience 40;
- Adam `(0.0,0.9)`, epsilon `1e-8`, zero weight decay;
- SiLU hidden activation and no network normalization.

Search configuration count is exactly one. Search-run count is zero: there is no
exploratory or adaptive search phase. The five primary seed tuples execute the
singleton contract directly. No configuration, range, ratio, budget, or stopping
rule may be added or changed after a result exists.

The compute parity proxy is frozen as equal generator update-equivalents,
training examples per epoch, batch size, fit/selection windows, maximum generator
epochs, patience, and five-member primary count. Exact FLOP or wall-clock parity
is impossible because the WGAN performs five critic updates and has a different
path-network cost. Critic updates are counted and reported separately. The v1
protocol defines no wall-clock/GPU-time cap, so wall-clock is not a selection or
stopping rule.

## 5. Primary and reserve seed schedule

The schedule reuses the established deterministic convention from
`structured_vol_v5_seed_schedule_v1.json`:

`replicate_seed(k) = 8281 + 1000 * (k - 1)`
`model_init_seed = replicate_seed`
`data_seed = replicate_seed + 1`
`eval_seed = 8283`.

Primary WGAN members, all `SCHEDULED_NOT_RUN`:

| Member | Replicate/model-init | Data | Evaluation |
|---|---:|---:|---:|
| `wgan-seed-01` | 8281 | 8282 | 8283 |
| `wgan-seed-02` | 9281 | 9282 | 8283 |
| `wgan-seed-03` | 10281 | 10282 | 8283 |
| `wgan-seed-04` | 11281 | 11282 | 8283 |
| `wgan-seed-05` | 12281 | 12282 | 8283 |

`wgan-seed-03` is a new WGAN primary identity and is not the historically
governance-invalid Neural-SDE seed-03 record.

Reserve order is deterministic and prospective only:

| Reserve | Order | Replicate/model-init | Data | Evaluation |
|---|---:|---:|---:|---:|
| `reserve-wgan-j01` | 1 | 13281 | 13282 | 8283 |
| `reserve-wgan-j02` | 2 | 14281 | 14282 | 8283 |
| `reserve-wgan-j03` | 3 | 15281 | 15282 | 8283 |

Reserves are not primary members, are not authorized here, are not automatically
executed, and cannot be selected by performance. A later governed decision may
consider the next reserve only if frozen valid-completed-member semantics require
replacement of a non-completed slot. No automatic j01/j02/j03 chain exists.

## 6. Outcome semantics

The existing status meanings are reused:

- `GATE_PASS_VALID`: finite completed WGAN with valid checkpoint and all frozen architecture-neutral comparator Gate criteria passing; included numerically.
- `GATE_FAIL_VALID`: finite completed WGAN with valid checkpoint but one or more frozen architecture-neutral Gate criteria failing; included numerically and not discarded for poor performance.
- `VALID_EXECUTION_NO_GATE_RESULT`: governance-valid execution without a valid Gate result; not a completed member and numerically excluded.
- `GOVERNANCE_INVALID`: governance/protocol-invalid execution; not a completed member and numerically excluded, with failure history retained.

Every attempted primary remains in its roster with its exact seed tuple and
outcome. There is no silent discard, rerun, retune, automatic replacement, or
performance-based reserve selection.

## 7. Metrics and H2 decision rule

### 7.1 Cross-family primary metrics

The only primary H2 metrics are:

1. `valid_completed_member_fraction` — higher is better;
2. `nonfinite_or_missing_checkpoint_rate` — lower is better;
3. sample SD across members of `best_generator_epoch / 400` — lower is better;
4. sample SD across members of the common internal-selection `terminal_wasserstein_normalized` checkpoint metric — lower is better.

The first two measure completion/finite stability. The latter two measure
cross-seed checkpoint and selection stability without comparing incompatible
training losses.

### 7.2 Cross-family secondary diagnostics

The following existing architecture-neutral path diagnostics are reported but do
not independently determine H2 status:

- `variance_ratio`, target band `[0.50, 2.00]`;
- `terminal_dispersion_ratio`, target band `[0.50, 2.00]`;
- `path_uniqueness_fraction`, minimum 0.99;
- `return_acf1_abs_diff`, maximum 0.25;
- `terminal_wasserstein_normalized`;
- `acf_rmse`;
- `acf_max_error`.

ACF lags are exactly `[1, 2, 3, 5, 10, 20]`. The existing v2 bootstrap, path
counts, and seeds are reused where supported.

The WGAN-specific diagnostic record includes critic loss, generator loss,
gradient penalty, finite/nonfinite status, mode-collapse indicators, training
completion, checkpoint-selection stability, and critic/generator update counts.
These quantities never masquerade as cross-family metrics.

The following Neural-SDE quantities are excluded from direct WGAN comparison:

- `initial_selection_total_loss`;
- `best_selection_total_loss`;
- `selection_loss_improvement_absolute`;
- `initial_internal_rbf`;
- `best_internal_rbf`;
- `drift_diffusion_rms_ratio`.

The first five are signature-MMD/objective-specific. The drift/diffusion ratio
has a defined Neural-SDE drift/diffusion decomposition but no same scientific
definition for a Neural-CDE WGAN generator. Historical Neural-SDE values remain
in the frozen N5 record and are not modified.

### 7.3 Family aggregation and status

The validated Neural-SDE family is exactly the Amendment-057 five-member set:
`seed-01`, `seed-02`, `seed-04`, `seed-05`, and `reserve-j01`. The WGAN family is
the five WGAN primary members, with only `GATE_PASS_VALID` and `GATE_FAIL_VALID`
counting as valid completed members.

For each family and metric, use fixed roster order and report arithmetic mean,
sample SD with `ddof=1`, median, minimum, and maximum. No weights, composite
score, ranking, post-hoc metric subset, imputation, or replacement is allowed.

The preregistered descriptive decision is:

- `H2_SUPPORTED` iff both families have exactly five valid completed members, all four primary metrics are finite for both families, the Neural-SDE family is no worse than WGAN on every primary metric, and Neural-SDE is strictly better on at least one primary metric;
- `H2_NOT_SUPPORTED` iff both families are complete with finite primary metrics but the support condition is false, including any WGAN strict improvement or mixed/incomparable primary direction;
- `H2_UNRESOLVED` iff either family is underfilled, a primary metric is missing/nonfinite, or governance validity prevents the required summary.

A valid poor WGAN is not discarded. A comparator execution failure is not
converted automatically into proof of H2. No significance test, p-value,
confidence interval, Holm procedure, or inferential threshold is introduced for
this n=5 descriptive H2 stability comparison. No CPU/CUDA causal attribution or
seed-only attribution is permitted.

## 8. CUDA and future authorization contract

Future WGAN scientific execution is CUDA-only:

- requested device: `cuda`;
- expected resolved device: `cuda`;
- CPU fallback: prohibited;
- runtime identity: captured from the actual production CUDA runtime and rebound if implementation/software identity changes.

Every future authorization must bind, at minimum:

- member identity and seed tuple;
- effective singleton configuration hash;
- comparator methodology identity;
- seed-schedule identity;
- implementation Git blob;
- execution-contract identity;
- execution recipe head;
- requested/resolved CUDA;
- captured production runtime identity;
- one invocation maximum;
- training authorization true;
- validation authorization false;
- final-test authorization false.

Future execution must begin in the background, use one scientific CLI invocation,
and preserve durable prelaunch and post-execution evidence. Relaunch, rerun,
overwrite, automatic reserve chaining, validation, and final-test access are
prohibited. Task 103 creates no authorization.

## 9. Audit-102 push provenance disclosure

Audit 102 found this local Git provenance event, disclosed without attribution:

- timestamp: `2026-08-22 16:42:45 -0400`;
- local remote-tracking transition: `6e4789c1...` -> `42cfe4412880c044d721635ef6ab7e4d65d17c73`;
- reflog label: `update by push`;
- remote set-head: `2026-08-22 16:42:46 -0400`;
- `FETCH_HEAD`: updated to `42cfe4412880c044d721635ef6ab7e4d65d17c73`;
- scope: Tasks 093–101 / nine commits carried in the observed push;
- initiating process: `OBSERVED_PUSH_PROCESS_UNATTRIBUTED`;
- attribution to Hermes, Claude, IDE, or user: not made without evidence;
- scientific effect: `0`;
- N4/N5-result effect: `0`.

This is a provenance disclosure only. Task 103 itself performs no Git-remote
network and no push.

## 10. Audit-102 stale-docstring disclosure

The shared analysis module
`reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py`
contains the historical docstring wording:

> stdlib only + numpy if available otherwise pure python

Audit 102 classified this as:

`STALE_DOCSTRING_DOCUMENTATION_ONLY`

The current module has no NumPy import and no NumPy execution branch. Its actual
summary implementation uses Python standard-library `statistics`, including
`statistics.mean`, `statistics.stdev` with sample `ddof=1`, and
`statistics.median`, plus standard-library JSON/hash/path handling. The stale
wording has no runtime or scientific effect. The source module is not edited by
Task 103.

## 11. Firewalls and preservation

Task 103 required zero counts are:

- WGAN implementations created: `0`;
- source changes: `0`;
- test changes: `0`;
- training: `0`;
- simulation: `0`;
- Gate: `0`;
- authorization: `0`;
- validation: `0`;
- external validation: `0`;
- final-test access: `0`;
- N4/N5 recomputation: `0`;
- j02 decision: `0`;
- j03 decision: `0`;
- provider/scientific network: `0`;
- Git-remote network: `0`;
- push: `0`.

The historical N4 result remains immutable. The validated N5 artifact remains
unchanged with SHA-256
`84e53a3e77e6eea12a1449aa08763766c6106d7fe16eb36d1285f0bd71bdf564` and Git
blob `7c10e622db3415cae53fb9547d6ebef15decbb76`. The final test remains sealed.

## 12. Append-only and self-authentication rule

This amendment is append-only. It does not embed its own future FILE SHA-256 or
Git blob. The machine-readable preregistration has the same rule. Each identity
is recorded only after the corresponding bytes are final and committed.

The only permitted tracked changes for Task 103 are:

1. `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json`;
2. `reports/protocol/research_protocol_amendment_059.md`.

No source, test, live-training config, runner, authorization, scientific result,
N4 artifact, or N5 artifact is modified.

## 13. Final status and next action

`N4 HISTORICAL RESULT: IMMUTABLE`
`N5 FAMILY ANALYSIS: VALIDATED`
`WGAN COMPARATOR: PREREGISTERED_PENDING_INDEPENDENT_AUDIT`
`H2: UNRESOLVED_PENDING_WGAN_COMPARATOR`
`FINAL TEST: SEALED`

**Next governed action:** Independent read-only audit of the WGAN comparator
preregistration, including the machine-readable contract, singleton budget,
seed schedule, metrics, H2 rule, CUDA policy, push provenance, stale docstring,
and all firewalls.

---

*Amendment 059 freezes the WGAN neural-CDE comparator methodology before any
comparator result, preserves the validated Neural-SDE and sealed final-test
state, records the Audit-102 provenance findings without attribution, and creates
no scientific execution authority.*
