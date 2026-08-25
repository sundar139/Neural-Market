# Amendment 093 — V5 WGAN Reserve-J01 Gate-v2 Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-RESERVE-J01-GATE-V2-AUTHORIZATION-FREEZE-181`
Risk: `R4`
Branch: `main`
Starting HEAD: `e5ff3221f8a875ba9cced78ace07baf40513ae6c`
Prerequisite: `NM-R5-V5-WGAN-RESERVE-J01-TRAINING-EXECUTION-AUDIT-180` — `VALIDATED` (reserve training `VALID_EXECUTION_NO_GATE_RESULT` 24/2.189..., member `NOT_YET_COMPLETED_PENDING_GATE`)
Safety branch: `safety/pre-wgan-reserve-j01-gate-auth-e5ff322` at `e5ff3221f8a875ba9cced78ace07baf40513ae6c`
Campaign state: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, reserve-j01 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE` (checkpoint `ccc5b913...` 338677, report `0ab246ce...` final 64 stopped_early true), valid primary members `4` (seed-01,02,04,05), primary attempts consumed `5`, valid WGAN members `4`, reserve required, H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`
Status: APPEND-ONLY RESERVE GATE AUTHORIZATION FREEZE — no Gate execution, no training rerun, no H2, no final-test, no network, no push.

## 1. Campaign and training predecessor

Reserve-j01 training remains `VALID_EXECUTION_NO_GATE_RESULT` (marker `c9012cde8cc110ebc9b8a732cc130296036c7ee16a3d55a694157fc83d45f659` 1882, checkpoint `ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef` 338677 32 tensors finite, selected 24 / 2.18908573311753, report `0ab246ce6315f917512e0c89faf1d05534f35041b86d2eeaf35db2a31cc94471` final 64 stopped_early true, Task-179 evidence canonical `d7d55c0ac45f71b68937c7a44bc8c334bfdc48b3de8bbec369ed212324a81a5b` blob `fb666a399d2549788dc9db232b9858b7de9f1748` raw `53bca72327...`, Amendment 092 canonical `9adf86cf17e09c57ba5301caf48fecafd9a2ed8f4ea72a737d8f247f1e089e5a` blob `daf8810cf7c3fac63cf6eac01642e5e932b80008`).

Primary campaign is permanently `5 attempts consumed / 4 valid completed members` (seed-03 failed remains `NOT_VALID_COMPLETED_MEMBER`). Preregistered WGAN N=5 valid-member requirement requires one reserve valid member; reserve-j01 is the first reserve.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

This task freezes exactly one Gate-v2 authorization for `reserve-wgan-j01` on its audited checkpoint, without executing Gate.

## 2. Reserve Gate-v2 authorization contract

Reconstructed from CURRENT source (wgan_gate_evaluator.py, wgan_runner.py, wgan_comparator.py, wgan_cde.py, Gate-v2 configuration, Gate authorization schema/validator, seed-05 Gate-v2 authorization as structural precedent, WGAN comparator preregistration, Task-180 audit):

- Current prospective implementation identities if unchanged:
  - Gate evaluator canonical SHA: `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9`, Git blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` (HEAD:src/neuralmarket/research/wgan_gate_evaluator.py)
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261`
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
  - WGAN training config SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7` blob `e0740afc24697f2eab3620a4243d04411aa508cb`
  - Gate-v2 config canonical SHA: `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`, Git blob `d9705ef9a11da3e21760015bb2a27fa408018bb5` (configs/research/neural_sde_internal_gate_v2.yaml)

Derived fields recomputed from HEAD bytes, not copied mechanically from seed-05 JSON; every identity verified via require_tracked_artifact_at_head.

No source/config/schema was altered in this task.

## 3. Reserve-J01 Gate-v2 scientific contract

- Member: `reserve-wgan-j01`
- Role: `RESERVE`
- Checkpoint: `data/processed/research/model/wgan-comparator/reserve-wgan-j01/f7507c38d9e3f204/checkpoint.pt` SHA `ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef` size `338677` selected `24 / 2.18908573311753`
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
- Report-only diagnostics remain exactly: normalized terminal Wasserstein, multi-lag raw ACF RMSE, raw ACF maximum absolute error, abs-return ACF, squared-return ACF, conditional variance
- No threshold changes, no reserve-specific criteria, no mode-collapse criterion, no final-test access.
- Reserve purpose: `replace invalid primary seed-03 and supply fifth valid WGAN member` (as bound in authorization).

## 4. Runtime, data binding, and Gate provenance

Use `.venv-gpu`. Rebuild current Gate runtime using evaluator's actual deterministic ordering (resolve_device -> configure_device_determinism -> build_runtime_identity):

- Python `3.11.9`, PyTorch `2.13.0+cu132`, CUDA `13.2`, available `true`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` cap `8.9`, cuDNN `92000`, deterministic `true`, runtime `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`, CPU fallback `PROHIBITED`.

WGAN real-path/training-data binding remains preregistered contract: training identity `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605`, real source `internal_selection` bootstrap 1024, generated 1024, horizon 63, block 22, lags 1,2,3,5,10,20 – verified no scientific-contract drift.

Gate configuration: eval seed `8283`, bootstrap `8801`, generated `1024`, MBB `1024`, horizon `63`, block `22`, lags `1,2,3,5,10,20` – verified from committed Gate config source.

## 5. Reserve-J01 Gate-v2 authorization V1

Verified before creation reserve-j01 Gate authorization count 0, marker 0, result 0, process 0.

Created exactly one Gate authorization using current source convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_gate/reserve-wgan-j01-gate-v2-v1.json`
- Canonical SHA: `b995f1c3ea15dd9d8f7b568e13e77174d5e240a9ec1c8dd3d44d1c6597115030` (committed Git-object SHA)
- Raw worktree SHA: `202c6fcebddcaa6e5e4fba88efcc6bb76b0ca5088981f8d904c9d2aa622cfab9` (file read_bytes with CRLF)
- Git blob: `c45df0c4cc8b8397aeba3dfcac9a4943954af618`
- Filtered worktree == HEAD PASS, recursive object count `3`, total key occurrences `55` (one extra `reserve_purpose` vs primary gate 54), duplicate count `0`
- Schema: `structured-vol-v5-wgan-gate-authorization-v1`

Authorization binds, at minimum where required:

- member `reserve-wgan-j01`, role `RESERVE` (where supported), checkpoint `data/processed/research/model/wgan-comparator/reserve-wgan-j01/f7507c38d9e3f204/checkpoint.pt` SHA `ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef` size `338677`, training authorization `6d0c8474bd28d152f200920ae4e4cb058efa4cf95be7bac3b7d7f562030217c7 / 20e538035f441fe807e10169f85e1f2f929cc043`, training execution marker `c9012cde8cc110ebc9b8a732cc130296036c7ee16a3d55a694157fc83d45f659`, training report `0ab246ce6315f917512e0c89faf1d05534f35041b86d2eeaf35db2a31cc94471`, Task-179 execution evidence canonical `d7d55c0ac45f71b68937c7a44bc8c334bfdc48b3de8bbec369ed212324a81a5b` blob `fb666a399d2549788dc9db232b9858b7de9f1748` raw `53bca723...`, Amendment 092 canonical `9adf86cf17e09c57ba5301caf48fecafd9a2ed8f4ea72a737d8f247f1e089e5a` blob `daf8810cf7c3fac63cf6eac01642e5e932b80008`
- Gate evaluator canonical `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9` blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625 / d9705ef9a11da3e21760015bb2a27fa408018bb5`, runtime `17e3bb52...`
- evaluation seed `8283`, bootstrap `8801`, generated/bootstrap `1024/1024`, horizon/block `63/22`, lags `1,2,3,5,10,20`
- reserve purpose `replace invalid primary seed-03 and supply fifth valid WGAN member`
- future task `NM-R5-V5-WGAN-RESERVE-J01-GATE-V2-EXECUTION-183`, future marker `reports/research/wgan_gate_runs/reserve-wgan-j01/gate-v2-execution-183/execution_started.json`
- Permissions: `max_scientific_invocations: 1`, `Gate: true`, `training: false`, `validation: false`, `final: false`, `overwrite: false`, `retry: false`, `rerun: false`, `relaunch: false`. One future Gate process creation permanently spends entitlement.

Committed authorization ALONE at `58e8bdb76031a980729b7005be79d67b81565527` (`docs(research): freeze wgan reserve-j01 gate-v2 authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `b995f1c3ea15dd9d8f7b568e13e77174d5e240a9ec1c8dd3d44d1c6597115030` (committed), raw `202c6fcebddcaa6e5e4fba88efcc6bb76b0ca5088981f8d904c9d2aa622cfab9`, blob `c45df0c4cc8b8397aeba3dfcac9a4943954af618`, filtered worktree == HEAD PASS, duplicate `0`, recursive `3`, total keys `55`, schema `structured-vol-v5-wgan-gate-authorization-v1`

Safe-validated committed authorization using existing helpers only (no Gate CLI, no --execute):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate 0 PASS
- member/checkpoint PASS (`ccc5b913...` 338677 24/2.189...), training predecessor PASS, Gate evaluator `243750a...` PASS, runner `56a1370...` PASS, comparator `78a9da57...` PASS, model `2f5cf1dd...` PASS, Gate config `8e70ad.../d9705ef9...` PASS, runtime `17e3bb52...` PASS, seeds `8283/8801` PASS, sample sizes `1024/1024` PASS, horizon `63` block `22` lags `1,2,3,5,10,20` PASS
- reserve purpose PASS
- future task `NM-R5-V5-WGAN-RESERVE-J01-GATE-V2-EXECUTION-183` PASS, future marker `.../gate-v2-execution-183/execution_started.json` ABSENT PASS
- Gate result ABSENT PASS, Gate process 0 PASS, training process 0 PASS

If validation had failed, would have stopped without amendment.

## 7. Preservation and pre-Gate accounting

Preserved exactly:

- seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`
- seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- reserve-j01 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE` (checkpoint `ccc5b913...`, report `0ab246ce...`, Task-179 evidence `d7d55c0a.../fb666a...` raw `53bca723...`, Amendment 092 `9adf86.../daf8810...`)

Preserved:

- reserve training authorization `6d0c8474.../20e53803...` raw `d35181...`
- training marker `c9012cde...`
- checkpoint `ccc5b913...`
- training report `0ab246ce...`
- Task-179 evidence `d7d55c0a.../fb666a...`
- Amendment 092 `9adf86.../daf8810...`

Campaign remains `VALID WGAN MEMBERS: 4` (seed-01,02,04,05), `PRIMARY ATTEMPTS CONSUMED: 5` (all primaries attempted, seed-03 failed, reserve does not increment primary attempts). Gate authorization freeze alone does NOT promote reserve-j01.

H2 remains `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, Gate authorization count exactly 1, marker absent, result absent):

- tracked tree clean
- reserve-j01 Gate authorization count: exactly 1 (`reserve-wgan-j01-gate-v2-v1.json` at `b995f1c3.../c45df0c4...` raw `202c6f...`)
- reserve-j01 Gate marker: ABSENT (`reports/research/wgan_gate_runs/reserve-wgan-j01/gate-v2-execution-183/execution_started.json` absent)
- reserve-j01 Gate result: ABSENT
- reserve-j01 Gate process: 0, reserve training: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

If all pass:

`WGAN RESERVE-J01 GATE-V2 AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN RESERVE-J01 GATE: NOT PERFORMED`

Valid WGAN members remains `4`, primary attempts `5`.

Next governed task must be `NM-R4-V5-WGAN-RESERVE-J01-GATE-V2-AUTHORIZATION-AUDIT-182` before any reserve Gate process. Do NOT execute Gate. Do NOT calculate H2.

This amendment is append-only, contains no self-hash.

