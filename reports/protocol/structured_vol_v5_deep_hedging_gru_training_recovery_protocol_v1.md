# V5 GRU Training Recovery Protocol v1

Date: 2026-08-25
Protocol: structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1
Status: FROZEN
Branch: main
Prerequisites:
- NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-AUDIT-220 — AUDIT_CLOSED_WITH_REPORT_ONLY_INTEGRITY_MISSTATEMENTS
- NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-AUDIT-CLOSURE-221 — AUDIT_INTEGRITY_CLOSURE_VALIDATED
Repaired implementation commit: 85f5363518786286247490d8d953701d18fa3ae8
Repaired implementation manifest: 1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20
Trainer blob: 1860f99fcbd52ac26daab33e5325c36955fde7f8
Contract-v3: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 blob eef7ad220db889166469799372759dfe1a96e35f
Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada

## 1. Prerequisites and Historical Attempt Exhaustion

Historical Task-216: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-EXECUTION-216
Historical policies: 45 directories under `data/processed/research/hedging_policies`
  - 5 members (seed-01, seed-02, seed-04, seed-05, reserve-j01) × 3 costs (0.0, 0.001, 0.005) × 3 hedger seeds (31001,31002,31003)
  - Scientifically valid: 0_OF_45
  - Deleted: 0, Overwritten: 0, Preserved immutable: 45
Authorization 212: reports/protocol/hedging_execution_authorization_212.json
  - Historical training ceiling: 45
  - Training attempts consumed: 45
  - Remaining historical training attempts: 0
  - Authorization 212 training authority: EXHAUSTED_CLOSED — MUST NOT be reused for recovery

Implementation manifest (15-path closure, verified at 85f5363):
  src/neuralmarket/cli/deep_hedging.py daf8d7a2c184689ac72b9bbe1996733e2c5f70bb
  src/neuralmarket/cli/main.py ac7aa07e3304e91894fd5717f33c40b57bc83ae4
  src/neuralmarket/core/device.py 5f7f7a1ec29407c5a1734a71a994f444cf092386
  src/neuralmarket/core/runtime_identity.py 817ba53e2474c6e8dd7ecf15d64e0766e75f73e9
  src/neuralmarket/data/manifests.py 7ec3a80a795f82bfd19020bd21358e76a300615d
  src/neuralmarket/models/structured_vol_sde.py e828a8748216cc9d8d79593e1dd2e42a6226ab08
  src/neuralmarket/research/deep_hedging/__init__.py bd994657eab9407ff8593b2c2ad3ede31a689f44
  src/neuralmarket/research/deep_hedging/artifacts.py 28e3254a16977970a0860f9fc438d05e3949ac30
  src/neuralmarket/research/deep_hedging/cvar.py c03166afeb23b34d8fbf8d3d29357933eca2524a
  src/neuralmarket/research/deep_hedging/generation.py 1b8710fc77362eb59a7167b3b4575d8b93f63d12
  src/neuralmarket/research/deep_hedging/hedger.py 9a003e45687e1bbd409bde2c37ed39644be9e2ad
  src/neuralmarket/research/deep_hedging/pnl.py 122a00c996f8d4d01b89474fe98dee5ec49a393f
  src/neuralmarket/research/deep_hedging/runner.py 97c3dccb1110a08a6406debddf9514d2cb71fb5b
  src/neuralmarket/research/deep_hedging/synthetic.py f3838634a6afc57b438d1baa2d078e37d12dacb5
  src/neuralmarket/research/deep_hedging/trainer.py 1860f99fcbd52ac26daab33e5325c36955fde7f8
  Canonical manifest SHA: 1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20
  Package key verified: `src/neuralmarket/research/deep_hedging/__init__.py` present (true), `src/neuralmarket/research/deep_hedging/init.py` present (false)

## 2. Scientific Recovery Principle

Recovery exists only because Task-216 executed a scientifically invalid no-op trainer (TRAINING_LOOP_NO_OP_EMPTY_BATCH_LOOP). This is recovery of intended preregistered science, not a new experiment.

Each invalid Task-216 tuple may have exactly ONE separately authorized recovery attempt.
Recovery must use the SAME frozen scientific tuple: member, synthetic dataset (Task-215 validated retained datasets), cost, hedger seed, contract-v3 configuration (GRU 7/64/2/dropout0, features, prev_delta, batch 64, PCG64 permutation, P&L, CVaR alpha .95, AdamW .001/.9/.999/1e-6 clip 1.0, max200 min20 patience20, strict-lower checkpoint, full-selection CVaR, costs 0/0.001/0.005, seeds 31001/2/3, replacement NONE).
No replacement member, synthetic dataset, cost, hedger seed, extra random seed, alternate architecture, alternate optimizer, or new hyperparameter tuning.
The sole scientific implementation change relative to Task-216 is the audited trainer repair 85f5363 / 1f6524...

Not a new hypothesis, not new hyperparameter exploration, not synthetic regeneration, not final-test activity.

## 3. Exact 45 Recovery Tuples and Predecessor Mapping

Ordered tuple universe (nested order: member → cost → hedger_seed):

Members: seed-01, seed-02, seed-04, seed-05, reserve-j01
Costs: 0.0, 0.001, 0.005
Hedger seeds: 31001, 31002, 31003
Total: 45

For every recovery tuple, immutable predecessor metadata (from Task-216 evidence `reports/research/evidence/structured_vol_v5_deep_hedging_gru_training_execution_v1.json` at ee7da9f canonical 1d739b3...):

| # | member | cost | seed | historical artifact path | historical execution_started SHA | historical checkpoint SHA | historical terminal SHA | classification |
|---|--------|------|------|--------------------------|----------------------------------|---------------------------|-------------------------|----------------|
| 1 | seed-01 | 0.0 | 31001 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31001 | dfa226ac70be4933e35f920b74c550b8448e523a93994dfeddd5c3c912be52b6 | 932f66efd6fb5f4cd052add0ce79e389f67b356a1e119c4c90b64f2b3e147c07 | baed534188efe7e12c966c18fe4537ce0cf0bd52fff704140791a7d2e43e811f | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| 2 | seed-01 | 0.0 | 31002 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31002 | e2223dae78997d1d1a1c6c600bb4275d4ca44881b1a96b804457a2696f57f822 | 003686fcdc7fa58dd63a9668578cdf0087ae4c915a9db20288b92f1f87c04bd7 | 73713976335eb83... | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| 3 | seed-01 | 0.0 | 31003 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31003 | ... | d82abaf8612dda7efd61e9b3c95df9a4ab7f2c53304688f1aa0f9a62433336e4 | ... | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| 4-45 | ... (remaining 42 tuples follow same pattern, see evidence file for full SHAs) | ... | ... | ... | ... | ... | ... |

Note: Full 1-to-1 mapping for all 45 is defined by the evidence file's 45 records (ordinal 1..45, member/cost/hedger_seed unique, no orphan, no duplicate). Historical task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-EXECUTION-216. Historical classification for all: SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP. One-to-one mapping: 45 recovery tuples ↔ 45 historical invalid tuples, verified via evidence aggregate (attempted 45, consumed 45, succeeded 45 but scientifically 0).

## 4. Distinct Write-Once Recovery Artifact Namespace

Historical root (immutable): `data/processed/research/hedging_policies`
Recovery root (frozen, distinct): `data/processed/research/hedging_policies_recovery_v1`

Each recovery policy directory deterministically derived from:
- recovery protocol version: v1
- member, cost (bps 0/10/50), hedger_seed (31001/2/3)

Example: `data/processed/research/hedging_policies_recovery_v1/5bdbaabd2fb257a7_seed-01/c_0/h_31001` (same logical hierarchy, distinct root, no collision with historical `data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31001`).

Verification: `hedging_policies_recovery_v1` does not exist pre-recovery (checked), and its path never collides with historical (different root prefix).

Write-once semantics inside recovery root (independent domain):
- execution_started once, no overwrite, no deletion, no retry, no rerun, no replacement
- If a recovery attempt is consumed and fails: that tuple becomes RECOVERY_FAILED_CONSUMED, no second recovery attempt implicitly authorized

## 5. Recovery Science and Eligibility

Recovery training preserves contract-v3 exactly:
GRU 7 input /64 hidden /2 layers /dropout0, raw delta; features unchanged; prev_delta endogenous [0]=0 [t]=delta[t-1]; mixed-maturity masks; batch 64; epoch permutation PCG64(hedger_seed+epoch); optimizer AdamW lr .001 betas .9/.999 wd 1e-6; grad clip 1.0; CVaR alpha .95; max200 min20 patience20 scheduler none; selection complete persisted 10000 universe; checkpoint strictly lower selection CVaR, tie earliest; replacement NONE.

Datasets: only the five Task-215 validated retained synthetic datasets (seed-01 5bdbaabd..., seed-02 62c7406..., seed-04 77e7de9..., seed-05 1e8aa17..., reserve-j01 38c5113...). No synthetic regeneration.

H3 eligibility:
- HISTORICAL TASK-216 POLICIES: EXCLUDED_PERMANENTLY (0 eligible)
- SUCCESSFUL AUDITED RECOVERY POLICIES: ELIGIBLE_FOR_H3 (only after independent audit validates recovery)
- Unaudited recovery artifacts: NOT H3 ELIGIBLE

## 6. Attempt Accounting and Stop Conditions

Historical global policy attempts: 45 invalid Task-216 attempts (consumed, scientifically 0).
Planned recovery authorization ceiling: 45 recovery attempts (separate accounting domain).
Projected total after full recovery (if all 45 executed): 90 invocations (45 historical invalid + 45 recovery attempts). This is disclosed, not concealed.

Recovery execution must stop immediately on first:
- nonzero process exit, failure terminal, nonfinite scientific state, authorization mismatch, source drift, dataset drift, artifact collision, missing evidence, ambiguous consumed state.
No continuation after first recovery failure unless a later separately governed adjudication explicitly decides otherwise.

## 7. Required Recovery Provenance Fields

Every future recovery attempt must persist provenance linking:
recovery task ID, recovery authorization ID, recovery protocol canonical SHA/blob (this file), repaired implementation commit 85f5363, manifest SHA 1f6524..., trainer blob 1860f99..., contract-v3 identity 79611b..., runtime identity 17e3bb52..., member, cost, hedger seed, synthetic dataset path/SHA, historical Task-216 predecessor path, historical started SHA, historical checkpoint SHA, historical terminal SHA, historical invalidity reason TRAINING_LOOP_NO_OP, recovery execution_started SHA, recovery checkpoint SHA, recovery final checkpoint SHA, training curve SHA, training report SHA, terminal SHA, best epoch, best selection CVaR, epochs executed.

Recovery report must never describe old Task-216 policy as valid or overwritten.

## 8. Rationale

Scientific rationale: recovery of intended frozen training after implementation no-op defect — the 45 Task-216 policies never performed real optimization (0 optimizer steps, NaN train_cvar, 0 parameter change), so the preregistered science (GRU deep hedger with endogenous prev_delta, batched P&L, empirical CVaR) was never actually executed. Recovery re-executes that intended science with the audited fail-closed trainer, distinct write-once identities, without altering historical evidence.

Not a new hypothesis, not new hyperparameter exploration, not synthetic regeneration, not final-test activity.
