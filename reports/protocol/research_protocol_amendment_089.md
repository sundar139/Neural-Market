# Amendment 089 — V5 WGAN Seed-05 Gate-v2 Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-05-GATE-V2-AUTHORIZATION-FREEZE-173`
Risk: `R4`
Branch: `main`
Starting HEAD: `abe81d27a98f6638c2aae3db00c8c03d272c647d`
Prerequisite: `NM-R5-V5-WGAN-SEED-05-TRAINING-EXECUTION-AUDIT-172` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed05-gate-auth-abe81d2` at `abe81d27a98f6638c2aae3db00c8c03d272c647d`
Campaign state: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE`, valid primary members `3`, attempts consumed `5`, H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`
Status: APPEND-ONLY GATE AUTHORIZATION FREEZE — no Gate execution, no training rerun, no reserve, no H2, no final-test, no network, no push.

## 1. Campaign and training predecessor

Seed-05 training remains `VALID_EXECUTION_NO_GATE_RESULT` (marker `108eb6b459b4edf5f3dd86192afe21985b38bc8828a38102162ab68d4b3ca5c3` 1874, checkpoint `4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d` 338677 32 tensors finite, selected 71 / 3.2245595973856656, report `8e58a6150ba19764194c4e65fb936e020288d2458cba33460f3be2079267505c` final 111 stopped_early true, Task-171 evidence canonical `2d2c0baa0ed886f7c4ca018c35bcbf4325c2b43a4b96594299e95e06823b80ae` blob `8b5c9b45c72fe5c3fc8c5629694096e92391ef01` raw `921eb5ad63c8e8c2ea2b7151e1ece4d80b9ccf27388fd06de78728f8c0106e34`, Amendment 088 `3fa52ebfca6aeeb9fbeac24430e89bc96618e5f53fcb3424a20db9abb3007c33 / 02fd05447b4e17f210ce46afa9bc80bb07280efd`).

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

This task freezes exactly one Gate-v2 authorization for `wgan-seed-05` on its audited checkpoint, without executing Gate.

## 2. Gate-v2 authorization contract

Reconstructed from current source (wgan_gate_evaluator.py, wgan_runner.py, wgan_comparator.py, wgan_cde.py, Gate-v2 config, Gate authorization schema/validator, seed-04 Gate authorization as structural precedent, WGAN comparator preregistration, relevant Gate protocol amendments, Task-172 audit):

- Current prospective implementation identities if unchanged:
  - Gate evaluator canonical SHA: `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9`, Git blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` (HEAD:src/neuralmarket/research/wgan_gate_evaluator.py)
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261`
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
  - WGAN training config SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7` blob `e0740afc24697f2eab3620a4243d04411aa508cb`
  - Gate-v2 config canonical SHA: `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`, Git blob `d9705ef9a11da3e21760015bb2a27fa408018bb5` (configs/research/neural_sde_internal_gate_v2.yaml)

Derived fields recomputed from HEAD bytes, not copied mechanically from seed-04 JSON; every identity verified via require_tracked_artifact_at_head.

No source/config/schema was altered in this task.

## 3. Seed-05 Gate-v2 scientific contract

- Member: `wgan-seed-05`
- Checkpoint: `data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt` SHA `4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d` size `338677` selected `71 / 3.2245595973856656`
- Evaluation seed: `8283`
- Bootstrap seed: `8801`
- Generated paths: `1024`
- Real circular-MBB paths: `1024`
- Horizon: `63`
- Block: `22`
- Lags: `1,2,3,5,10,20`
- Required Gate criteria:
  - variance ratio PASS iff 0.50 <= ratio <= 2.00
  - terminal-dispersion ratio PASS iff 0.50 <= ratio <= 2.00
  - path uniqueness PASS iff >=0.99
  - ACF1 absolute error PASS iff <=0.25
- WGAN drift/diffusion: EXCLUDED / NOT_APPLICABLE
- Report-only diagnostics remain exactly: normalized terminal Wasserstein, multi-lag raw ACF RMSE, raw ACF max absolute error, abs-return ACF, squared-return ACF, conditional variance
- No threshold changes, no mode-collapse science, no final-test access.

## 4. Runtime, data binding, and Gate provenance

Use `.venv-gpu`. Rebuild current Gate runtime using evaluator's actual deterministic ordering (resolve_device -> configure_device_determinism -> build_runtime_identity):

- Python `3.11.9`, PyTorch `2.13.0+cu132`, CUDA `13.2`, available `true`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` cap `8.9`, cuDNN `92000`, deterministic `true`, runtime `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`, CPU fallback `PROHIBITED`.

WGAN real-path/training-data binding remains preregistered contract: training identity `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605`, real source `internal_selection` bootstrap 1024, generated 1024, horizon 63, block 22, lags 1,2,3,5,10,20 – verified no scientific-contract drift.

Gate configuration: eval seed `8283`, bootstrap `8801`, generated `1024`, MBB `1024`, horizon `63`, block `22`, lags `1,2,3,5,10,20` – verified from committed Gate config source.

## 5. Seed-05 Gate-v2 authorization V1

Verified before creation seed-05 Gate authorization count 0, marker 0, result 0.

Created exactly one Gate authorization using current source convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-05-gate-v2-v1.json`
- Canonical SHA: `d34445eff07b59a8654bdef0ae016e06714c1d8170792f760ecd9d958e3fd570`
- Git blob: `a3dc095b63df7de320d4cb35dfaf666cdea92de3`
- Filtered worktree == HEAD PASS, recursive object count `3`, total key occurrences `54`, duplicate count `0`
- Schema: `structured-vol-v5-wgan-gate-authorization-v1`

Authorization binds, at minimum where required:

- member `wgan-seed-05`, checkpoint `data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt` SHA `4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d` size `338677`, training authorization `0753a576246de301fe8a6664d587e977f5f2b1567ee45179dbf594bd2cd06c1a / 0aa7323375fc68fe6486fe62c169a0e6716c03af`, training execution marker `108eb6b459b4edf5f3dd86192afe21985b38bc8828a38102162ab68d4b3ca5c3`, training report `8e58a6150ba19764194c4e65fb936e020288d2458cba33460f3be2079267505c`, Task-171 evidence canonical `2d2c0baa0ed886f7c4ca018c35bcbf4325c2b43a4b96594299e95e06823b80ae` blob `8b5c9b45c72fe5c3fc8c5629694096e92391ef01` raw `921eb5ad63c8e8c2ea2b7151e1ece4d80b9ccf27388fd06de78728f8c0106e34`, Amendment 088 `3fa52ebfca6aeeb9fbeac24430e89bc96618e5f53fcb3424a20db9abb3007c33 / 02fd05447b4e17f210ce46afa9bc80bb07280efd`
- Gate evaluator `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9 / 243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625 / d9705ef9a11da3e21760015bb2a27fa408018bb5`, runtime `17e3bb52...`
- evaluation seed `8283`, bootstrap `8801`, generated/bootstrap `1024/1024`, horizon/block `63/22`, lags `1,2,3,5,10,20`
- future task `NM-R5-V5-WGAN-SEED-05-GATE-V2-EXECUTION-175`, future marker `reports/research/wgan_gate_runs/wgan-seed-05/gate-v2-execution-175/execution_started.json`
- Permissions: `max_scientific_invocations: 1`, `Gate: true`, `training: false`, `validation: false`, `final: false`, `overwrite: false`, `retry: false`, `rerun: false`, `relaunch: false`. One future Gate process creation permanently spends entitlement.

Committed authorization ALONE at `93daf98a9649b361166891ca0b1213a2d2017334` (`docs(research): freeze wgan seed05 gate-v2 authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `d34445eff07b59a8654bdef0ae016e06714c1d8170792f760ecd9d958e3fd570`, blob `a3dc095b63df7de320d4cb35dfaf666cdea92de3`, filtered worktree == HEAD PASS, duplicate `0`, recursive `3`, total keys `54`, schema `structured-vol-v5-wgan-gate-authorization-v1`

Safe-validated committed authorization using existing helpers only (no Gate CLI, no --execute):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate 0 PASS
- member/checkpoint PASS (`4a728a10...` 338677 71/3.224...), training predecessor PASS, Gate evaluator `243750a...` PASS, runner `56a1370...` PASS, comparator `78a9da57...` PASS, model `2f5cf1dd...` PASS, Gate config `8e70ad.../d9705ef9...` PASS, runtime `17e3bb52...` PASS, seeds `8283/8801` PASS, sample sizes `1024/1024` PASS, horizon `63` block `22` lags `1,2,3,5,10,20` PASS
- future task `NM-R5-V5-WGAN-SEED-05-GATE-V2-EXECUTION-175` PASS, future marker `.../gate-v2-execution-175/execution_started.json` ABSENT PASS
- Gate result ABSENT PASS, Gate process 0 PASS, training process 0 PASS

If validation had failed, would have stopped without amendment.

## 7. Preservation and exact-once campaign history

Preserved exactly:

- seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`
- seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-05 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE` (checkpoint `4a728a10...` report `8e58a615...` Task-171 evidence `2d2c0baa.../8b5c9b45...` raw `921eb5...` Amendment 088 `3fa52ebf.../02fd0544...`)

Campaign remains `VALID PRIMARY MEMBERS COMPLETED: 3` (seed-01, seed-02, seed-04), `PRIMARY ATTEMPTS CONSUMED: 5` (seed-05 is 5th attempt, training valid but Gate pending). H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, Gate authorization count exactly 1, marker absent, result absent):

- tracked tree clean
- seed-05 Gate authorization count: exactly 1 (`wgan-seed-05-gate-v2-v1.json` at `d34445ef.../a3dc095b...`)
- seed-05 Gate marker: ABSENT (`reports/research/wgan_gate_runs/wgan-seed-05/gate-v2-execution-175/execution_started.json` absent)
- seed-05 Gate result: ABSENT
- Gate process: 0, training: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

If all pass:

`WGAN SEED-05 GATE-V2 AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-05 GATE: NOT PERFORMED`

Next governed task must be `NM-R4-V5-WGAN-SEED-05-GATE-V2-AUTHORIZATION-AUDIT-174` before any seed-05 Gate process. Do NOT execute Gate.

This amendment is append-only, contains no self-hash.

