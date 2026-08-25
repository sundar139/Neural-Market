# Amendment 114 — V5 GRU Fail-Close Repair

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-NONFINITE-FAIL-CLOSE-REPAIR-219
Risk: R4
Type: IMPLEMENTATION_ONLY
Branch: main
Starting HEAD: 2b76203f968b264cd9a55aedb3f95170e0fe100d
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-REPAIR-218 — CORE_OPTIMIZER_REPAIR_IMPLEMENTED_BUT_NONFINITE_FAIL_CLOSE_DEFECT_REMAINS
Safety branch: safety/pre-v5-gru-training-repair-ed0cb42 at ed0cb420951585ec66c01f1e588ee73d10768a7b

## 1. Prior state (Task-218)

Task-216: GRU_TRAINING_SCIENTIFICALLY_INVALID (45 invalid policies, 15 invalid cells preserved immutable)
Task-217: AUDIT_ACCEPTED_REPAIR_REQUIRED — TRAINING_LOOP_NO_OP_EMPTY_BATCH_LOOP
Task-218: CORE_OPTIMIZER_REPAIR_IMPLEMENTED_BUT_NONFINITE_FAIL_CLOSE_DEFECT_REMAINS at d8e10e9e1e3a9d57bd136fd8344786a15af99bee trainer c1c601e4ee614cc936a4231b30d7eb01267500b4 manifest c0cbf7331355003fd622cddf4e6cac66f70e85d607275a53ff14a1c78d751942
Remaining defect: NONFINITE_SKIP_AND_CONTINUE — active minibatch path skipped nonfinite loss/cvar/gradient and continued
Contract-v3: UNCHANGED_VALIDATED 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 blob eef7ad220db889166469799372759dfe1a96e35f
Historical invalid policies: 45 preserved immutable
GRU RECOVERY TRAINING: NOT_AUTHORIZED
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
FINAL TEST: SEALED 0 ACCESS NOT GRANTED

## 2. Defect verification (pre-mutation, 2b76203)

Trainer blob: c1c601e4ee614cc936a4231b30d7eb01267500b4
Active minibatch path at c1c601:
- nonfinite loss vector: `stderr_log.append(... nonfinite loss, skipping); continue`
- nonfinite minibatch CVaR: `stderr_log.append(... nonfinite cvar, skipping); continue`
- nonfinite gradient: `stderr_log.append(... nonfinite grad ..., skipping step); optimizer.zero_grad(); continue`
- empty epoch_train_losses: `stderr_log.append(... no finite minibatch CVaR — train_cvar will be NaN)` — no raise, would persist NaN as success
This violates fail-closed numerical invariant (skip/continue instead of fatal).

## 3. Fail-closed invariant (frozen)

For every real or fixture policy-training minibatch:
- loss_vec must be finite ([B] shape)
- minibatch empirical CVaR must be finite
- CVaR must require gradients
- every intended trainable parameter must have a gradient after backward (unless explicitly unused)
- every present gradient must be finite
- clipped gradient norm must be finite
If ANY fails: raise deterministic training exception immediately — no skip, no continue, no next minibatch, no successful terminal.

## 4. Repair (fail-closed, no science change)

File: src/neuralmarket/research/deep_hedging/trainer.py
Preserved exact sequence:
`hedger.train()` → `optimizer.zero_grad()` → batched autoregressive loss (7 features, endogenous prev_delta, mixed-maturity masks) → finite loss check → `empirical_cvar(alpha=.95)` → finite CVaR check → requires_grad check → `backward()` → gradient presence/finiteness check → `clip_grad_norm_(...,1.0)` → finite clipped-norm check → `optimizer.step()` → `epoch_train_losses.append(cvar.detach())`

For each failed check: `raise RuntimeError(f"... member {member} cost {cost} hedger_seed {hedger_seed} epoch {epoch} batch {start} ...")` with member/cost/seed/epoch/batch/failure class. No new abstraction.
Empty training evidence: `if not epoch_train_losses: raise RuntimeError(f"empty epoch_train_losses member ... epoch {epoch} ...")` — never persist NaN as success.
No scientific parameter changes (GRU 7/64/2/dropout0, batch64, AdamW lr .001 betas .9/.999 wd 1e-6 clip 1.0, alpha .95, max200 min20 patience20, strict-lower checkpoint, full-selection CVaR, costs 0/0.001/0.005, seeds 31001/2/3, replacement NONE).

## 5. Implementation identity

Repair commit: 85f5363518786286247490d8d953701d18fa3ae8
Previous trainer blob: c1c601e4ee614cc936a4231b30d7eb01267500b4
New trainer blob: 1860f99fcbd52ac26daab33e5325c36955fde7f8
Manifest paths: 15 (same closure)
Source blobs (sorted):
- src/neuralmarket/cli/deep_hedging.py daf8d7a2c184689ac72b9bbe1996733e2c5f70bb
- src/neuralmarket/cli/main.py ac7aa07e3304e91894fd5717f33c40b57bc83ae4
- src/neuralmarket/core/device.py 5f7f7a1ec29407c5a1734a71a994f444cf092386
- src/neuralmarket/core/runtime_identity.py 817ba53e2474c6e8dd7ecf15d64e0766e75f73e9
- src/neuralmarket/data/manifests.py 7ec3a80a795f82bfd19020bd21358e76a300615d
- src/neuralmarket/models/structured_vol_sde.py e828a8748216cc9d8d79593e1dd2e42a6226ab08
- src/neuralmarket/research/deep_hedging/__init__.py bd994657eab9407ff8593b2c2ad3ede31a689f44
- src/neuralmarket/research/deep_hedging/artifacts.py 28e3254a16977970a0860f9fc438d05e3949ac30
- src/neuralmarket/research/deep_hedging/cvar.py c03166afeb23b34d8fbf8d3d29357933eca2524a
- src/neuralmarket/research/deep_hedging/generation.py 1b8710fc77362eb59a7167b3b4575d8b93f63d12
- src/neuralmarket/research/deep_hedging/hedger.py 9a003e45687e1bbd409bde2c37ed39644be9e2ad
- src/neuralmarket/research/deep_hedging/pnl.py 122a00c996f8d4d01b89474fe98dee5ec49a393f
- src/neuralmarket/research/deep_hedging/runner.py 97c3dccb1110a08a6406debddf9514d2cb71fb5b
- src/neuralmarket/research/deep_hedging/synthetic.py f3838634a6afc57b438d1baa2d078e37d12dacb5
- src/neuralmarket/research/deep_hedging/trainer.py 1860f99fcbd52ac26daab33e5325c36955fde7f8
Manifest canonical: {"implementation_commit":"85f5363518786286247490d8d953701d18fa3ae8","source_blobs":{...sorted...}}
New implementation_manifest_sha256: 1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20
Previous manifest: c0cbf7331355003fd622cddf4e6cac66f70e85d607275a53ff14a1c78d751942
No recovery authorization created.

## 6. What was not done

- Real retraining: 0
- Recovery execution: 0 NOT_AUTHORIZED
- Generation: 0 CLOSED
- Held-out evaluation/H3: 0 NOT_YET_ADJUDICATED
- Final-test access: 0 SEALED

## 7. Reconciled state

TASK-216: GRU_TRAINING_SCIENTIFICALLY_INVALID
TASK-217: AUDIT_ACCEPTED_REPAIR_REQUIRED
TASK-218: CORE_OPTIMIZER_REPAIR_PRESERVED
TASK-219: GRU_TRAINING_FAIL_CLOSE_REPAIRED_PENDING_AUDIT
GRU RECOVERY TRAINING: NOT_AUTHORIZED
GRU TRAINING: NOT_VALIDATED
POLICY COMPLETENESS: NOT_SATISFIED
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-AUDIT-220 (R4 STRICT_READ_ONLY_IMPLEMENTATION_AUDIT)
