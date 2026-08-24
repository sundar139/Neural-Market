# Amendment 079 — V5 WGAN Seed-02 Gate-v2 Replacement Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-02-GATE-V2-V2-AUTHORIZATION-FREEZE-150`
Risk: `R4`
Branch: `main`
Starting HEAD: `042a383b9bbe18b24f461e50d203e4c51f504c36`
Prerequisites: `NM-R4-V5-WGAN-GATE-V2-PROVENANCE-IDENTITY-UPDATE-AUDIT-148` (VALIDATED) and `NM-R4-V5-WGAN-AMENDMENT-078-PROVENANCE-ADJUDICATION-149` (VALIDATED)
Prerequisite evaluator: `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9 / 243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` (repaired prospective)
Prerequisite Amendment-078 true: `6ef7faf21af130ba58c8227abfb3b6aac9030c9c1567c1fd2537170ca460c16f / 4093a01deb8ab57253053029746ea6e1baf3cd03` (canonical SHA / Git blob, filtered worktree == HEAD)
Status: APPEND-ONLY REPLACEMENT AUTHORIZATION FREEZE — no Gate execution, no training, no source/test edit, no seed-03/reserve, no H2, no final-test, no network, no push.

## 1. Prerequisites

Task-148 validated the Gate evaluator prospective training provenance refresh (runner `56a1370...`, comparator `78a9da57...`, evaluator `243750a...`), and Task-149 adjudicated Amendment-078's true immutable identity:

- actual Amendment-078 canonical SHA: `6ef7faf21af130ba58c8227abfb3b6aac9030c9c1567c1fd2537170ca460c16f`
- actual Amendment-078 blob: `4093a01deb8ab57253053029746ea6e1baf3cd03`
- filtered worktree == HEAD PASS
- vs Amendment-076 `2f8baf2f.../64aecbac...` — distinct; Audit-148's reported blob `64aecbac...` was REPORT_ONLY_CROSS_AMENDMENT_TRANSCRIPTION_ERROR, not committed defect.

Seed-02 training remains `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED` (checkpoint `ca72d43... 338677` epoch 29 metric 1.890..., marker `175fcad9...`, evidence `bf7c7c89.../a4bd4557...`, report `c123724...`, diagnostics PRESENT).

WGAN Gate-v2 prospective provenance is now `VALIDATED`.

WGAN Seed-02 Gate authorization V1 `512ccb1be94ac06964c927e5f9745659c1dda826917905fa3d377b6e51d0a583 / e8e1303d61d6183bcc8d03f325fda210734df34c` is `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` (binds stale evaluator `f74eaa...`), Gate marker `ABSENT`, Gate `0`.

H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`.

This task freezes exactly one replacement Gate authorization V2 that supersedes V1 and binds the repaired evaluator and true Amendment-078 provenance.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

## 2. Recomputed training-to-Gate lineage

Independently recomputed and bound (canonical SHA = SHA-256 of git cat-file -p HEAD:path, blob = git rev-parse HEAD:path, filtered worktree == HEAD required; untracked raw SHA for checkpoint/marker/report):

- Training authorization V2: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v2.json` SHA `c282bc433905641e9413db28aa135cbfda60dac92d59b87cdaf68f766dae4491` blob `747a1d8a11a1a4d97605cad154d870dca196022c`
- Training marker: `reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/execution_started.json` raw SHA `175fcad9a3ce590e86e4a8cb6e8dbbbba05a1031e630d790dc4a70e0960390c4`
- Task-144 evidence: `reports/research/evidence/structured_vol_v5_wgan_seed02_execution_v2_144.json` canonical SHA `bf7c7c8954ee1f8fce53de5d3e3759c31aed61fb5d04602698406ea1d6ab5d58` blob `a4bd4557b99be44ccc40eb0d49ae9ef31afe890c` (not b69c6f... worktree pre-commit)
- Checkpoint: `data/processed/research/model/wgan-comparator/wgan-seed-02/e1cc68218d9eef71/checkpoint.pt` raw SHA `ca72d43abd4ad1fc2899583be9d7d3a5a206e0ddba21d99b67d01763d046193b` size 338677 selected epoch 29 metric 1.8903446799783874 config hash 5c223604...
- Training report: `reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/training_report.json` raw SHA `c123724afe8a88a5370414c40cdb503818015846549d50c284179898a0672fc2` classification VALID_EXECUTION_NO_GATE_RESULT
- Amendment 077: `387bf9d774772559557430e30b31353129eb6f08e372d83c09b6ee9bcd0a7deb / f5b10bfaf67549772de212cd65cb456797980a12`

If any predecessor identity differed, would have blocked as `BLOCKED_SEED02_GATE_V2_V2_PREDECESSOR_DRIFT` — none did.

## 3. Repaired Gate implementation

Bound current repaired evaluator:

- path `src/neuralmarket/research/wgan_gate_evaluator.py` canonical SHA `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9` blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` (filtered worktree == HEAD)
- prospective constants `TRAINING_RUNNER_GIT_BLOB: 56a1370cb3b76d5849083c175a3d98bc6a390261`, `COMPARATOR_GIT_BLOB: 78a9da57ffb297a0f5ec71f740fa590f4ad7d166` (updated from historical 7e020.../87f9ad...)

Bound true Amendment 078:

- path `reports/protocol/research_protocol_amendment_078.md` canonical SHA `6ef7faf21af130ba58c8227abfb3b6aac9030c9c1567c1fd2537170ca460c16f` blob `4093a01deb8ab57253053029746ea6e1baf3cd03` (filtered worktree == HEAD)

Bound Gate config:

- path `configs/research/neural_sde_internal_gate_v2.yaml` canonical SHA `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625` blob `d9705ef9a11da3e21760015bb2a27fa408018bb5` (filtered worktree == HEAD)

Scientific Gate contract unchanged (member wgan-seed-02 predecessor VALID_EXECUTION_NO_GATE_RESULT, generated 1024 bootstrap 1024 horizon 63 MBB 22 lags [1,2,3,5,10,20] evaluation 8283 bootstrap 8801 finite prerequisite, variance 0.50-2.00, terminal 0.50-2.00, uniqueness >=0.99, ACF1 <=0.25, report-only diagnostics, valid outcomes GATE_PASS_VALID/GATE_FAIL_VALID, excluded criteria unchanged).

## 4. CUDA runtime

Rebuilt fresh via repaired Gate evaluator's deterministic prelaunch order using `.venv-gpu`:

- Python 3.11.9, PyTorch 2.13.0+cu132, CUDA 13.2, available true, GPU NVIDIA GeForce RTX 4070 Laptop GPU capability 8.9, cuDNN 92000, requested cuda, resolved cuda, deterministic true, cuDNN benchmark false, cuDNN deterministic true, runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`, CPU fallback PROHIBITED.

If material drift, would have blocked as `BLOCKED_SEED02_GATE_V2_V2_RUNTIME_DRIFT` — none.

## 5. Replacement Gate authorization V2

Created exactly one Gate authorization using current validated Gate schema, superseding V1:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-02-gate-v2-v2.json`
- Canonical SHA: `8f609f78c86f2c6f2b40028a899fda8b617390aacdc4df54c87cc9180f67c85d`
- Git blob: `610b5e939183f2392a5553745a39084306bfb2ed`
- Filtered worktree == HEAD PASS, duplicate keys 0 (49 keys, 4 objects recursively)

Explicit supersedes `wgan-seed-02-gate-v2-v1.json` disposition `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` (512ccb1.../e8e1303d...).

New authorization binds:

- member wgan-seed-02, predecessor VALID_EXECUTION_NO_GATE_RESULT
- training V2 authorization SHA/blob `c282bc43.../747a1d8a...`
- training marker SHA `175fcad9...`
- Task-144 canonical evidence SHA/blob `bf7c7c89.../a4bd4557...` (true committed, not b69c6f...)
- checkpoint path/SHA/size/epoch/metric/config hash `ca72d43.../338677/29/1.890.../5c223604...`
- training report path/SHA `c123724...`
- Amendment-077 SHA/blob `387bf9d7.../f5b10bf...`
- repaired evaluator SHA/blob `b7c7cd84.../243750a...`
- Amendment-078 SHA/blob `6ef7faf.../4093a01...` (true, not Audit-148's 64aecbac...)
- Gate config SHA/blob `8e70ad15.../d9705ef9...`
- runner/comparator/model identities `56a1370.../78a9da57.../2f5cf1dd...`
- evaluation/bootstrap seeds 8283/8801 and runtime `17e3bb52...`

Future Gate execution task `NM-R5-V5-WGAN-SEED-02-GATE-V2-EXECUTION-152`, future exclusive marker `reports/research/wgan_gate_runs/wgan-seed-02/gate-v2-execution-152/execution_started.json` — verified absent before freeze.

Permissions: `max_scientific_invocations: 1`, `training_authorized: false`, `gate_authorized: true`, `validation_authorized: false`, `final_test_authorized: false`, `overwrite: false`, `retry/rerun: false`, `relaunch: false`. One future Gate process spends governance entitlement even if technical marker not reached; no automatic replacement after creation.

## 6. Committed V2 validation

After authorization commit, from committed Git object:

- canonical SHA `8f609f78c86f2c6f2b40028a899fda8b617390aacdc4df54c87cc9180f67c85d`, blob `610b5e...`, filtered worktree == HEAD PASS, recursively no duplicate keys, SAFE Gate helpers only (no CLI, no --execute, no marker): schema/member/predecessor/training V2/training marker/evidence/checkpoint/report/Amendment077/runner/comparator/model/evaluator/Amendment078/Gate config/seeds/runtime/permissions/supersedes V1 lineage/future task/future marker all PASS, future marker ABSENT, Gate result ABSENT, Gate execution 0. No modification/recreation on failure.

## 7. Authorization disposition

- Gate-v2-v1 path `wgan-seed-02-gate-v2-v1.json` SHA `512ccb1...` blob `e8e1303d...` preserved YES, consumed NO, marker ABSENT, Gate 0, execution eligibility `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION`.
- Gate-v2-v2 preserved after commit YES, consumed NO, future marker ABSENT, Gate 0, execution eligibility `FROZEN_PENDING_INDEPENDENT_AUDIT`.

Historical seed-01 Gate provenance preserved, not reinterpreted.

## 8. Final verification and next-gate readiness

Verified after both commits (tracked tree clean, Gate V1 byte-identical `512ccb1.../e8e1303d...`, Gate V2 `8f609f78.../610b5e...` exists exactly once and validates, repaired evaluator `243750a...`, Amendment-078 `4093a01...`, Gate config `d9705ef9...`, training V2 `747a1d8a...`, training marker `175fcad9...`, checkpoint `ca72d43...`, training report `c123724...`, Task-144 evidence `a4bd4557...`, Amendment-077 `f5b10bf...`, seed-01 artifacts unchanged):

- future Gate marker ABSENT, Gate result ABSENT, Gate execution 0, training 0, seed-03/04/05 0, reserve 0, validation 0, external 0, H2 0, final SEALED, network 0, push 0.

No source/tests change in this freeze, so no repository-wide suite required.

If all pass:

`WGAN SEED-02 GATE AUTHORIZATION V1: SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION`

`WGAN SEED-02 GATE AUTHORIZATION V2: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-02 GATE: NOT PERFORMED`

Next task must be `NM-R4-V5-WGAN-SEED-02-GATE-V2-V2-AUTHORIZATION-AUDIT-151` before any Gate execution. Do NOT execute Gate.

This amendment is append-only, contains no self-hash, does not modify Amendments 074–077.

