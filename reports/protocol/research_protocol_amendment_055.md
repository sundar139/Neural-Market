# Amendment 055 — V5 Reserve-j01 CUDA Training Authorization Contract

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-AUTHORIZATION-FREEZE-093
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `6e4789c1479a4417184e0191b1f8dce475cf115f`
**Safety branch:** `safety/pre-v5-reserve-j01-auth-freeze-6e4789c`
**Prerequisite audit:** NM-R4-V5-RESERVE-J01-READINESS-FINAL-AUDIT-092
**Prerequisite verdict:** VALIDATED WITH NON-BLOCKING FINDINGS
**Status:** PROSPECTIVE AUTHORIZATION CONTRACT — authorization may be created, but no execution is performed or implied. No `--execute`, training, simulation, marker, checkpoint, Gate execution, validation, external validation, final-test access, network, push, or reset.

## 1. Readiness closure and protected basis

Audit 092 validated every load-bearing pre-authorization gate for reserve-j01:

- fifth-member methodology;
- fifth-member semantics;
- narrow reserve-j01 runner eligibility;
- runner provenance;
- network provenance;
- executable readiness;
- literal zero-transit fixture hygiene;
- independent identity coverage;
- 55/55 focused tests.

The current reserve-j01 state at the starting HEAD is:

- `ELIGIBLE`;
- `NOT AUTHORIZED` before the authorization artifact created by Task 093;
- `NOT EXECUTED`.

The final chronological test remains `SEALED`. No final-test access is authorized by this amendment.

The frozen production runner is:

`a79a79f477429d66cc7fc0c75db7c751726ee577`

The runner source, scientific configuration, seed schedule, Gate-v2, trainer, runtime-identity implementation, authorization schema, existing authorization artifacts, execution evidence, and external-validation closure are not changed by this amendment.

## 2. Exact reserve-j01 identity

The authorization binds exactly one prospective reserve member:

| Field | Frozen value |
|---|---|
| `member_id` | `reserve-j01` |
| `replicate_seed` | `13281` |
| `model_init_seed` | `13281` |
| `data_seed` | `13282` |
| `eval_seed` | `8283` |
| `full_config_hash` | `38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` |
| `run_prefix` | `38c5113b27568e14` |
| `family_methodology_identity` | `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` |
| `schedule_git_blob` | `558d08bfee98dbd0c170d65e6a9b1737700c9e98` |
| `schedule_sha256` | `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` |
| `execution_contract_git_blob` | `84a59c4d966b349be705a8a29fad07f81282ebdc` |
| `runner_git_blob` | `a79a79f477429d66cc7fc0c75db7c751726ee577` |

The reserve schedule remains ordered and frozen. `reserve-j02` and `reserve-j03` remain unselected, unauthorized, and not permitted by this amendment. There is no automatic reserve-chain progression.

## 3. Real CUDA runtime contract

The production `.venv-gpu` runtime was inspected without training or simulation after resolving and configuring the requested device:

- Python: `3.11.9`;
- PyTorch: `2.13.0+cu132`;
- PyTorch CUDA build: `13.2`;
- requested device: `cuda`;
- resolved device: `cuda`;
- CUDA available: `true`;
- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`;
- compute capability: `8.9`;
- NVIDIA driver: `610.47`;
- deterministic algorithms: `true`;
- cuDNN benchmark: `false`;
- cuDNN deterministic: `true`;
- observed runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`.

The frozen authorization runtime identity is exactly:

`17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`

CUDA is fail-closed. No CPU fallback is permitted. A runtime identity mismatch requires a separately governed rebind and blocks authorization creation.

## 4. Authorization-v2 policy

The only permitted authorization artifact is an authorization-v2 JSON for `reserve-j01` using the exact field names and semantics in:

`reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json`

The schema Git blob is:

`c74958f2c5d99753b05bf64c9b6880ee9bd37d94`

The authorization policy is frozen as follows:

- `schema_version`: `structured-vol-v5-primary-training-authorization-v2`;
- `training_authorized`: `true`;
- `max_training_invocations`: `1`;
- `requested_device`: `cuda`;
- `expected_resolved_device`: `cuda`;
- `expected_runtime_identity_sha256`: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`;
- `validation_authorized`: `false`;
- `final_test_authorized`: `false`;
- `reserve`: `false`, as required by the current runner's authorization firewall field; this does not grant any other reserve slot;
- no external-validation permission;
- no final-test permission;
- no general reserve-chain permission;
- no `reserve-j02` or `reserve-j03` permission;
- no automatic fallback;
- no multiple invocation;
- no rerun;
- no relaunch;
- no overwrite;
- no deletion/recreation of an execution namespace.

Background-from-outset is mandatory for the eventual separate execution task. That future task may make at most one CLI scientific invocation. Authorization creation and inspection must never invoke the runner with `--execute`.

The authorization artifact must not contain a self-authentication field for its own future SHA or Git blob. It is complete-or-absent until committed, and it is `FROZEN_PENDING_INDEPENDENT_AUDIT`, not `READY_TO_EXECUTE`.

## 5. Amendment-055 recipe freeze

This amendment is committed before the authorization artifact. The full Git commit that adds this Amendment 055 is the selected `execution_recipe_head` for the authorization artifact. The commit's own future SHA and Git blob are intentionally not embedded in this file.

After commit, the selected recipe commit must be verified as:

- at or after `5e28384be24c898b7a3b1182ad6d944307398db0`;
- containing runner blob `a79a79f477429d66cc7fc0c75db7c751726ee577`;
- containing execution-contract blob `84a59c4d966b349be705a8a29fad07f81282ebdc`;
- containing schedule blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`.

The recipe must be a real local ancestor of the current execution HEAD at authorization inspection time. Recipe ancestry and containment are independently checked from Git; no authorization field is used as its own identity oracle.

## 6. Task-091 push provenance

Audit 092 found the following local durable Git evidence in the Task-091 window:

- timestamp: `2026-08-22 04:55:17 -0400`;
- local remote-tracking transition:
  `74b87dcc271161c092b1f522155cf825c6ec95d6` → `6e4789c1479a4417184e0191b1f8dce475cf115f`;
- local reflog label: `update by push`;
- Task-091 directive: `NO PUSH`;
- initiating process: `OBSERVED_PUSH_PROCESS_UNATTRIBUTED`;
- scientific bytes affected: `0`;
- authorization effect: `0`;
- execution effect: `0`.

No attribution to Hermes, Claude, an IDE, or the user is made without local evidence. This is a governance/provenance deviation, not a scientific-integrity defect. Amendment 054 remains byte-immutable. Task 093 also requires `NO PUSH`.

## 7. Prospective outcome classification

The following classification is frozen before any reserve-j01 result exists:

### GATE_PASS_VALID

A governance-valid and protocol-valid reserve-j01 execution with a valid completed model and a passing Gate-v2 result.

- valid completed-model member;
- completed-model admissible N becomes 5;
- Gate-pass count becomes 5;
- reserve-j01 remains labelled `reserve-j01` and does not become a primary seed.

### GATE_FAIL_VALID

A governance-valid and protocol-valid reserve-j01 execution with a valid completed model and one or more failed Gate-v2 criteria.

- valid completed-model member;
- completed-model admissible N becomes 5;
- Gate-pass count remains 4;
- reserve-j01 remains included numerically under the frozen family analysis contract;
- the failed Gate criteria remain reported and are not an exclusion filter.

### VALID_EXECUTION_NO_GATE_RESULT

A governance-valid execution that does not produce a valid Gate result.

- does not satisfy completed-model N=5;
- completed-model admissible N remains 4;
- only available frozen training scalars, missingness, and failure accounting apply;
- no automatic reserve-j02 is permitted.

### GOVERNANCE_INVALID

An execution invalid because a governance or protocol requirement failed.

- does not satisfy completed-model N=5;
- completed-model admissible N remains 4;
- excluded from valid numerical family summaries;
- failure history is retained;
- no automatic reserve-j02 is permitted.

No result-contingent rerun, retuning, discard, replacement, threshold modification, Gate modification, or analysis redesign is permitted. No result may trigger automatic progression to j02 or j03.

## 8. Prospective post-j01 family analysis

If and only if reserve-j01 is `GATE_PASS_VALID` or `GATE_FAIL_VALID`, the valid completed-model family is exactly:

- `seed-01`;
- `seed-02`;
- `seed-04`;
- `seed-05`;
- `reserve-j01`.

The numerical family size is N=5. Primary `seed-03` remains permanently `GOVERNANCE_INVALID` and is excluded numerically. Reserve-j01 remains labelled `reserve-j01` and does not retroactively become a successful primary seed.

The post-j01 analysis reuses exactly the existing Amendment-040/041 frozen 13 scalars:

### Training

1. `initial_selection_total_loss`;
2. `best_selection_total_loss`;
3. `best_epoch`;
4. `final_epoch`;
5. `selection_loss_improvement_absolute`.

### Gate

6. `variance_ratio`;
7. `terminal_dispersion_ratio`;
8. `path_uniqueness_fraction`;
9. `return_acf1_abs_diff`;
10. `drift_diffusion_rms_ratio`.

### Report-only

11. `terminal_wasserstein_normalized`;
12. `acf_rmse`;
13. `acf_max_error`.

ACF lags remain exactly `[1, 2, 3, 5, 10, 20]`. RBF internal diagnostics remain excluded from cross-member scalar analysis.

For valid N=5, each scalar requires arithmetic mean, sample SD with `ddof=1`, median, minimum, maximum, and CV when meaningful. LOMO is unconditional and mandatory: 13 scalars × 5 members. The previous N=4 sensitivity analysis remains historical and immutable; the N=5 analysis is a prospectively frozen extension, not a redesign.

Runtime composition must be disclosed as:

- historical CPU members: `seed-01`, `seed-02`, `seed-04`;
- CUDA members: `seed-05`, `reserve-j01`;
- CPU N=3;
- CUDA N=2.

No causal backend-effect estimate, significance testing, new threshold, or seed-only attribution is permitted. Backend is a labelled execution covariate, not a causal explanation. H2 remains unresolved without the WGAN comparator. If j01 does not produce a valid Gate result, the N=5 completed-model analysis must not be fabricated.

## 9. Firewalls and execution boundary

This amendment creates only the prospective contract for one future reserve-j01 training invocation and does not execute it.

Required zero counts for Task 093:

- training: `0`;
- `--execute`: `0`;
- simulation: `0`;
- Gate execution: `0`;
- authorization consumption: `0`;
- validation: `0`;
- external validation: `0`;
- final-test access: `0`;
- provider/scientific network: `0`;
- Git-remote network: `0`.

Before and after authorization creation, the following must remain absent:

- reserve-j01 `execution_started.json`;
- reserve-j01 checkpoints;
- reserve-j01 training curve;
- reserve-j01 training report;
- reserve-j01 adjudication;
- reserve-j01 model namespace;
- any j02/j03 authorization or execution artifact.

## 10. Append-only status and next action

Amendments 040, 041, 052, 053, and 054 are not modified. Amendment 054 remains byte-immutable. This Amendment 055 is append-only and does not self-authenticate with its own future hash/blob.

The final chronological test remains `SEALED`. Reserve-j01 execution remains `NOT AUTHORIZED` until the separately committed authorization artifact is independently audited. The resulting authorization state is `FROZEN_PENDING_INDEPENDENT_AUDIT`.

**Next governed action:** Independent read-only audit of the reserve-j01 authorization freeze, including Amendment 055, recipe containment, v2 schema binding, real CUDA runtime identity, authorization non-consumption, and all execution/network firewalls.

---

*Amendment 055 freezes the reserve-j01 CUDA authorization contract, exact identity binding, one-invocation and no-validation policy, post-j01 outcome classification, N=5 family analysis, Task-091 push provenance, and zero-execution firewalls before any reserve-j01 result exists.*
