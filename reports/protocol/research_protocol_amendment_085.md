# Amendment 085 — V5 WGAN Seed-04 Gate-v2 Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-04-GATE-V2-AUTHORIZATION-FREEZE-165`
Risk: `R4`
Branch: `main`
Starting HEAD: `bd2c5f00010143525cf9e8da90abd7157bd61532`
Prerequisite: `NM-R5-V5-WGAN-SEED-04-TRAINING-EXECUTION-AUDIT-164` — `VALIDATED` (report-only stopped_early transcription error non-blocking, raw true reconciled)
Safety branch: `safety/pre-wgan-seed04-gate-auth-bd2c5f0` at `bd2c5f00010143525cf9e8da90abd7157bd61532`
Campaign state: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE`, valid primary members `2`, attempts consumed `4`, H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`
Status: APPEND-ONLY GATE AUTHORIZATION FREEZE — no Gate execution, no training, no seed-05, no reserve, no H2, no final-test, no network, no push.

## 1. Campaign and training predecessor

Seed-04 training remains `VALID_EXECUTION_NO_GATE_RESULT` (marker `adac53e0cba5410c2afa2272a182289e5109e56c30fb71ee751c88989990a54b`, checkpoint `2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6` 338677 32 tensors finite, selected 39 / 1.34198..., report `46c3bcd32f2738054a1de595689ec02e5312395c4a82bfeba207369b328d4871` final 79 stopped_early true, Task-163 evidence `19d0e831ec63897d43c2c6f393b237ec0fe40e47260f06a2d7db0ade1314d13f / 934c3ba3d1d52374214c0de311909725c2d35c5d`, Amendment 084 `e883f72df62577c69a47cabc95baf628171dffb63f56da2a3f7457eb78ff28a4 / e4831b7e049c30b1c4168863c3113d891523f4ac`).

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

This task freezes exactly one Gate-v2 authorization for `wgan-seed-04` on its audited checkpoint, without executing Gate.

## 2. Gate-v2 authorization contract

Reconstructed from current source (wgan_gate_evaluator.py, wgan_runner.py, wgan_comparator.py, wgan_cde.py, Gate-v2 config, authorization schema/loader/validator, seed-02-gate-v2-v2 as structural precedent, WGAN preregistration, Amendments 078–080, 083–084, Task-164 audit):

- Current prospective implementation identities if unchanged:
  - Gate evaluator blob: `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` (HEAD:src/neuralmarket/research/wgan_gate_evaluator.py, SHA `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9`)
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261`
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
  - WGAN training config SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7` blob `e0740afc24697f2eab3620a4243d04411aa508cb`
  - Gate-v2 config SHA: `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625` blob `d9705ef9a11da3e21760015bb2a27fa408018bb5` (configs/research/neural_sde_internal_gate_v2.yaml)
  - scientific contract unchanged

Derived fields were recomputed from HEAD bytes, not copied mechanically from seed-02 JSON; every identity verified via require_tracked_artifact_at_head.

No source/config/schema was altered in this task.

## 3. Seed-04 Gate-v2 scientific contract

- Member: `wgan-seed-04`
- Checkpoint: `data/processed/research/model/wgan-comparator/wgan-seed-04/6009789e9e8645df/checkpoint.pt` SHA `2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6` size `338677` selected `39 / 1.3419804686113015`
- Evaluation seed: `8283`
- Bootstrap seed: `8801`
- Generated paths: `1024`
- Real MBB paths: `1024`
- Horizon: `63`
- Circular MBB block: `22`
- ACF lags: `1,2,3,5,10,20`
- Frozen Gate-v2 criteria exactly:
  1. variance ratio in [0.50, 2.00]
  2. MBB terminal-dispersion ratio in [0.50, 2.00]
  3. path uniqueness >=0.99
  4. ACF1 absolute error <=0.25
- Report-only: normalized terminal Wasserstein, multi-lag raw ACF RMSE, multi-lag raw ACF max error, abs-return ACF, squared-return ACF, conditional variance
- WGAN drift/diffusion criterion: EXCLUDED / NOT_APPLICABLE
- No threshold changes, no diagnostic additions, no mode-collapse addition, no final-test access.

## 4. Gate config, runtime, and data contract

Gate-v2 config identity: SHA `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625` blob `d9705ef9a11da3e21760015bb2a27fa408018bb5` (lags 1,2,3,5,10,20 block 22).

WGAN training data binding remains frozen research contract: training identity `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` via training report, real-path source `internal_selection` bootstrap 1024, generated 1024.

CUDA rebuilt via `.venv-gpu` using Gate evaluator's required ordering (resolve_device -> configure_device_determinism -> build_runtime_identity):

- Python `3.11.9`, PyTorch `2.13.0+cu132`, CUDA `13.2`, available `true`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` cap `8.9`, cuDNN `92000`, deterministic `true`, runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (matches training runtime), CPU fallback `PROHIBITED`.

No WGAN recomputation, no final-test access.

## 5. Seed-04 Gate-v2 authorization V1

Verified before creation seed-04 Gate authorization count 0, marker/result 0.

Created exactly one Gate-v2 authorization using current repository convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-04-gate-v2-v1.json`
- Canonical SHA: `9d845c2515684f0fc1cd2b97e5005f0df3227a3bffa30be3e9eb150039f68320`
- Git blob: `4eb418595d3ef3dbf27b85ccbdca775986a353a7`
- Filtered worktree == HEAD PASS, recursive object count `3`, total key occurrences `54`, duplicate count `0`

Authorization binds, where required by current schema/source:

- member `wgan-seed-04`, checkpoint `data/processed/research/model/wgan-comparator/wgan-seed-04/6009789e9e8645df/checkpoint.pt` SHA `2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6` size `338677`, selected `39 / 1.34198...`, canonical_wgan_config_hash `019dcb85a5b26ba6d9930dd68345123ee8788f2c0702a94485ffc95eaea6448d`
- training execution marker `reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/execution_started.json` SHA `adac53e0cba5410c2afa2272a182289e5109e56c30fb71ee751c88989990a54b`
- training authorization `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-04-v1.json` SHA `e866e5170c2d6d51accd453c0cfa2d1fa2d7f4e61bf277c8f1d02f22d02fa229` blob `de597ccaa7cb8ec4617922e0812a3b6ad42a7c56`
- training execution evidence `reports/research/evidence/structured_vol_v5_wgan_seed04_execution_v1_163.json` SHA `19d0e831ec63897d43c2c6f393b237ec0fe40e47260f06a2d7db0ade1314d13f` blob `934c3ba3d1d52374214c0de311909725c2d35c5d`
- training report `reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/training_report.json` SHA `46c3bcd32f2738054a1de595689ec02e5312395c4a82bfeba207369b328d4871`
- training runner `56a1370...`, scientific config `de0b4fe7.../e0740afc...`, model `2f5cf1dd...`, comparator `78a9da57...`, evaluator `243750a...`, Gate config `8e70ad.../d9705ef9...`, runtime `17e3bb52...`
- evaluation seed `8283`, bootstrap `8801`, generated `1024`, bootstrap `1024`, horizon `63`, block `22`, lags `1,2,3,5,10,20`
- future task `NM-R5-V5-WGAN-SEED-04-GATE-V2-EXECUTION-167`, future marker `reports/research/wgan_gate_runs/wgan-seed-04/gate-v2-execution-167/execution_started.json` (derived from current Gate evaluator and task binding)
- Permissions: `max_scientific_invocations: 1`, `gate_execution_authorized: true`, `training_authorized: false`, `validation_authorized: false`, `final_test_authorized: false`, `overwrite: false`, `relaunch: false`, `retry/rerun: false`. One future Gate process creation permanently spends entitlement.

Committed authorization ALONE at `969f3845c28c68ca84ec5a6c9cbe7ebb50c6934f` (`docs(research): freeze wgan seed04 gate-v2 authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `9d845c2515684f0fc1cd2b97e5005f0df3227a3bffa30be3e9eb150039f68320`, blob `4eb418595d3ef3dbf27b85ccbdca775986a353a7`, filtered worktree == HEAD PASS, duplicate `0`, recursive `3`, total keys `54`

Safe-validated committed authorization using existing helpers only (no --execute):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate 0 PASS
- member/checkpoint path/SHA/size PASS (`2e8b0f4c...` 338677 39/1.34198... 019dcb85...)
- training predecessor identities PASS (authorization `e866e517.../de597cca...`, marker `adac53e0...`, evidence `19d0e831.../934c3ba3...`, report `46c3bcd3...`)
- implementation Gate evaluator `243750a...` PASS, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...` PASS
- Gate config `8e70ad.../d9705ef9...` PASS
- runtime `17e3bb52...` PASS
- seeds `8283/8801` PASS, sample sizes `1024/1024` PASS, horizon `63` block `22` lags `1,2,3,5,10,20` PASS
- future task `NM-R5-V5-WGAN-SEED-04-GATE-V2-EXECUTION-167` PASS, future marker `reports/research/wgan_gate_runs/wgan-seed-04/gate-v2-execution-167/execution_started.json` ABSENT PASS
- Gate result ABSENT PASS, Gate process 0 PASS
- permissions max 1 Gate true training false PASS

If validation had failed, would have stopped without rewrite.

## 7. Preservation and exact-once state

Preserved seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / EXECUTED_AUDITED / NOT_VALID_COMPLETED_MEMBER`, seed-04 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE` (checkpoint `2e8b0f4c...` report `46c3bcd...` evidence `19d0e831.../934c3ba3...` Amendment 084 `e883f72d.../e4831b7e...`).

Campaign accounting remains valid primary members completed `2`, primary attempts consumed `4` (training success does not yet increment completed; Gate pending).

No Gate artifacts were overwritten.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, Gate authorization count exactly 1, marker absent, result absent):

- tracked tree clean
- seed-04 Gate authorization count: exactly 1 (`wgan-seed-04-gate-v2-v1.json` at `9d845c25.../4eb41859...`)
- seed-04 Gate marker: ABSENT (`reports/research/wgan_gate_runs/wgan-seed-04/gate-v2-execution-167/execution_started.json` absent)
- seed-04 Gate result: ABSENT
- Gate scientific process: 0, training process: 0, seed-05 auth: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

If all pass:

`WGAN SEED-04 GATE-V2 AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-04 GATE: NOT PERFORMED`

Next task must be `NM-R4-V5-WGAN-SEED-04-GATE-V2-AUTHORIZATION-AUDIT-166` before any Gate scientific process. Do NOT execute Gate.

This amendment is append-only, contains no self-hash.

