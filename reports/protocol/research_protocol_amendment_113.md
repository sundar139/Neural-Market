# Amendment 113 — V5 GRU Optimization Repair

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-REPAIR-218
Risk: R4
Type: IMPLEMENTATION_ONLY
Branch: main
Starting HEAD: ed0cb420951585ec66c01f1e588ee73d10768a7b
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-AUDIT-217 — REPAIR_REQUIRED
Safety branch: safety/pre-v5-gru-training-repair-ed0cb42 at ed0cb420951585ec66c01f1e588ee73d10768a7b

## 1. Prior adjudicated state

Task-215: SYNTHETIC_QUALITY_AUDIT_VALIDATED
Task-216: GRU_TRAINING_SCIENTIFICALLY_INVALID
Task-217: AUDIT_ACCEPTED_REPAIR_REQUIRED
Root cause: TRAINING_LOOP_NO_OP_EMPTY_BATCH_LOOP
Invalid historical policies: 45 (0_OF_45 scientifically valid)
Invalid historical cells: 15 (0_OF_15_CELLS_3_OF_3_VALID)
Historical artifacts: PRESERVED_IMMUTABLE — data/processed/research/hedging_policies/** 45 directories preserved, no delete/rename/overwrite/move/repair/reuse
Contract-v3: UNCHANGED_VALIDATED — 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 blob eef7ad220db889166469799372759dfe1a96e35f
SCIENTIFICALLY VALID POLICIES: 0_OF_45
POLICY COMPLETENESS: 0_OF_15_CELLS_3_OF_3_VALID
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED
FINAL-TEST ACCESS: 0

## 2. Root-cause verification (pre-mutation)

Frozen trainer blob: 26a0080686a40c722a1933f6f1dfaef5515486a2
Predecessor reference: blob 1073bcabd01d81b920fd8c49611f4c0a67b907d8 at 77f9fa3c6a6b9e2da8c754490293f597a42eec18 — contained hedger.train, optimizer.zero_grad, per-episode empirical_cvar, backward, clip_grad_norm_, optimizer.step
Current batched design preserved: one-time tensor materialization 40k train bundle, PCG64 perm hedger_seed+epoch, batch64 positional indexing, mixed-maturity padding/masks, autoregressive hedger.step with endogenous prev_delta, batched P&L, full-selection evaluation
Missing block: batched refactor retained `for start in range(...): S_padded = ...` but deleted optimization body beneath it
Verification before repair:
- optimizer constructed: true (AdamW)
- zero_grad calls in active training path: 0
- backward calls in active training path: 0
- optimizer.step calls in active training path: 0
- clip_grad_norm calls in active training path: 0
- epoch_train_losses: [] -> train_cvar NaN ×945

## 3. Repair (current batched trainer restored, no science change)

File: src/neuralmarket/research/deep_hedging/trainer.py
Repair: restore contract-exact minibatch optimization inside current batched loop for each consecutive frozen minibatch of 64 (or final partial):

- hedger.train()
- optimizer.zero_grad()
- batched autoregressive rollout using 7 frozen features (T_t, moneyness, log_moneyness, log_ret, prev_delta, cost_norm, opt), prev_delta[0]=0 prev_delta[t]=delta[t-1], mixed-maturity active masks, current tensorized paths
- per-episode loss vector via frozen P&L semantics — loss_vec shape [B] all finite
- empirical_cvar(loss_vec, alpha=0.95) scalar finite
- cvar.backward() with requires_grad true verified
- gradient finite verification before step (skip on nonfinite, log to stderr)
- torch.nn.utils.clip_grad_norm_(hedger.parameters(), max_norm=1.0)
- optimizer.step()
- append detached finite scalar minibatch CVaR to epoch_train_losses

No scheduler, no extra regularizer, no alternative objective, no optimizer change.
Fail-close: per-batch nonfinite loss/cvar logged and skipped; per-batch nonfinite grad skipped; if epoch_train_losses remains empty, stderr logged and train_cvar will be NaN then fail via no valid checkpoint — predecessor semantics preserved. For valid tiny fixtures, epoch_train_losses nonempty and train_cvar finite.

Preserved science exactly:
- GRU input 7 hidden 64 layers 2 dropout 0 raw delta output
- batch 64 optimizer AdamW lr 0.001 betas 0.9/0.999 weight_decay 1e-6 grad clip 1.0 alpha 0.95 max 200 min 20 patience 20
- selection universe complete persisted 10000 episodes, one full-set empirical CVaR, checkpoint strictly lower replaces, tie earliest remains
- costs 0/0.001/0.005 hedger seeds 31001/31002/31003 replacement NONE
- synthetic-generation, final-test, Authorization 212 unchanged

## 4. Implementation identity

Implementation repair commit: d8e10e9e1e3a9d57bd136fd8344786a15af99bee
Old trainer blob: 26a0080686a40c722a1933f6f1dfaef5515486a2
New trainer blob: c1c601e4ee614cc936a4231b30d7eb01267500b4
Manifest paths: 15 (same closure as Authorization 212)
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
- src/neuralmarket/research/deep_hedging/trainer.py c1c601e4ee614cc936a4231b30d7eb01267500b4
Manifest canonical payload: {"implementation_commit":"d8e10e9e1e3a9d57bd136fd8344786a15af99bee","source_blobs":{...sorted...}}
New implementation_manifest_sha256: c0cbf7331355003fd622cddf4e6cac66f70e85d607275a53ff14a1c78d751942
Old implementation_manifest_sha256: e3e7b6192881a06c81893973ad9c40d981e11e240a4af450d9185e4fa78622f4
No new execution authorization created in Task 218.

## 5. What was not done

- Real GRU retraining: 0
- Policy recovery execution: 0, NOT_AUTHORIZED
- Synthetic generation: 0, CLOSED
- Held-out evaluation/H3: 0, NOT_YET_ADJUDICATED
- Final-test access: 0, SEALED, no external/network/push

## 6. Reconciled state

TASK-216: GRU_TRAINING_SCIENTIFICALLY_INVALID
TASK-217: AUDIT_ACCEPTED_REPAIR_REQUIRED
TASK-218: GRU_TRAINING_IMPLEMENTATION_REPAIRED_PENDING_AUDIT
DEEP-HEDGING TRAINING IMPLEMENTATION: REPAIRED_PENDING_INDEPENDENT_AUDIT
TASK-216 INVALID ARTIFACTS: PRESERVED_IMMUTABLE
GRU RECOVERY TRAINING: NOT_AUTHORIZED
GRU TRAINING: NOT_VALIDATED
POLICY COMPLETENESS: NOT_SATISFIED
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-AUDIT-219
