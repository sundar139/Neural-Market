# Amendment 087 — V5 WGAN Seed-05 Training Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-05-TRAINING-AUTHORIZATION-FREEZE-169`
Risk: `R4`
Branch: `main`
Starting HEAD: `373c6dba3f869c8cdb241647051daa062b4993f5`
Prerequisite: `NM-R5-V5-WGAN-SEED-04-GATE-V2-EXECUTION-AUDIT-168` — `VALIDATED` (seed-04 Gate `GATE_FAIL_VALID` adjudicated, member `VALID_COMPLETED_MEMBER`)
Safety branch: `safety/pre-wgan-seed05-training-auth-373c6db` at `373c6dba3f869c8cdb241647051daa062b4993f5`
Campaign predecessor: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, valid primary members completed `3` (seed-01, seed-02, seed-04), primary attempts consumed `4` (Task-168 finalized seed-04 as VALID_COMPLETED_MEMBER), Task-167 evidence `f4d5903498387354ebe207bb931dc80ea0615d2bb271e3a5eae2256543437aec / b0f95764c82a4cf86307f0d45ff566c21ca489ff` (gate `GATE_FAIL_VALID`), Amendment 086 `5e395a55171f23e46c29644fa3b0cf9f83dc356d89f7bd19519958b2779a4d1e / c13bbe78d8c44d0f002079cd2911e683412d2323`, Gate marker `6bd290097d304cc49adfc944b0b275a711b51f1e69ef72e306f123efd481de41`, Gate stdout `2088cac717771894f4b06c9a3b326c7df13a40d0629934dc18e84c3e4aa73346`
Status: APPEND-ONLY TRAINING AUTHORIZATION FREEZE — no training, no Gate, no reserve, no H2, no final-test, no external validation, no network, no push.

## 1. Campaign state

Seed-04 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT` checkpoint `2e8b0f4c...` report `46c3bcd3...`, Gate `GATE_FAIL_VALID` via Task-167 evidence `f4d59034.../b0f95764...` marker `6bd29009...` stdout `2088cac7...`).

Seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER` remain preserved.

Valid primary completed remains `3` and attempts consumed `4` during this freeze; seed-05 will become the 5th primary attempt after training and Gate.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

This task freezes exactly one training authorization for the final primary member `wgan-seed-05` on the audited seed-04 completion, without executing training.

## 2. Training authorization contract

Reconstructed from current source (wgan_runner.py, wgan_comparator.py, wgan_cde.py, training config, authorization schema/loader/validator, seed-04-v1 as structural precedent, WGAN preregistration, Amendment 074, Amendments 083–086, Task-168 audit):

- Current prospective implementation identities if unchanged:
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261` (HEAD:src/neuralmarket/research/wgan_runner.py, filtered worktree == HEAD)
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
  - training config canonical SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`, blob `e0740afc24697f2eab3620a4243d04411aa508cb` (HEAD:configs/research/structured_vol_wgan_comparator_v1.yaml)
  - diagnostic persistence provenance: Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a` (PRESENT)
  - preregistration: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` SHA `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` blob `72311888542ee83ff497b5f0adbbaf6429e8452a`
  - execution contract: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4` blob `194b68797538010f35f5d48a2ec7c4cc4eee533f` (seed-04 training predecessor path)
  - seed schedule: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`

Derived fields recomputed from HEAD bytes, not copied mechanically from seed-04 JSON; every identity verified via require_tracked_artifact_at_head.

No source/config/schema was altered in this task.

## 3. Seed-05 member and seed semantics

- Member: `wgan-seed-05`
- Role: `PRIMARY`
- Frozen seed tuple: `replicate_seed: 12281`, `model_init_seed: 12281`, `data_seed: 12282`, `eval_seed: 8283`
- Internal-selection generated seed: `7777`
- Bootstrap seed: `8801`
- Training seed semantics:
  - model initialization: `12281`
  - training static latent: `12282`
  - training temporal noise: `12282`
  - window sampling: `12282`
  - refit noise: `12282`
  - gradient-penalty alpha: `12282`
- Evaluation seed 8283 is NOT internal-selection seed.
- Freeze unchanged training contract:
  - Conditional WGAN-GP hidden 64 GP lambda 10 Adam lr 1e-4 betas (0,0.9) eps 1e-8 weight decay 0 batch 64 critic:generator 5:1 max 400 early-stop terminal_wasserstein_normalized patience 40 min_delta 0 selection 1024/1024 block 22 horizon 63

No hyperparameter search, no seed-specific adjustment.

## 4. Training data, CUDA, and member-specific config

Training data identity: `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (manifest `split_manifest_v1.json` SHA `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`), range `2018-05-01` through `2021-12-31`, sessions `926`, lookback `22`, horizon `63`, fit fraction `0.8`, non-overlap `true`, embargo `context22/horizon63`.

CUDA rebuilt via `.venv-gpu` using runner's actual deterministic ordering (resolve_device -> configure_device_determinism -> build_runtime_identity):

- Python `3.11.9`, PyTorch `2.13.0+cu132`, CUDA `13.2`, available `true`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` cap `8.9`, cuDNN `92000`, deterministic `true`, runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (matches all prior seeds), CPU fallback `PROHIBITED`.

Constructed exact seed-05 `WGANTrainingConfig` via `effective_config_for_member('wgan-seed-05')`:

- `full_config_hash`: `aeab466455bc2f28fd0127165e121f80b8d75dcd1924b79043b105611b88b0e9`
- `run prefix`: `308cda2acc42be1b` (sha256("wgan-seed-05")[:16])

Both computed independently from source, not trusted from prompt; prompt expectation 308cda2acc42be1b verified via repository source.

## 5. Seed-05 training authorization V1

Verified before creation seed-05 authorization count 0, marker/report/checkpoint absent.

Created exactly one authorization using current repository convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-05-v1.json`
- Canonical SHA: `0753a576246de301fe8a6664d587e977f5f2b1567ee45179dbf594bd2cd06c1a`
- Git blob: `0aa7323375fc68fe6486fe62c169a0e6716c03af`
- Filtered worktree == HEAD PASS, recursive object count `11`, total key occurrences `142`, duplicate count `0`

Authorization binds, where required by current schema/source:

- member `wgan-seed-05`, role `PRIMARY`, replicate/model-init/data/eval `12281 / 12281 / 12282 / 8283`, internal selection `7777`, bootstrap `8801`
- runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, training config `de0b4fe7.../e0740afc...`, full_config_hash `aeab466455bc2f28fd0127165e121f80b8d75dcd1924b79043b105611b88b0e9`, run prefix `308cda2acc42be1b`, training-data `3702ef77...`, runtime `17e3bb52...`, diagnostic persistence `ef171da.../e5722ac...` (Amendment 074), preregistration `6c4a2725.../72311888...`, future task `NM-R5-V5-WGAN-SEED-05-TRAINING-EXECUTION-171`, future marker `reports/research/wgan_comparator_runs/wgan-seed-05/308cda2acc42be1b/execution_started.json`
- Permissions: `max_scientific_invocations: 1`, `training: true`, `Gate: false`, `validation: false`, `final: false`, `overwrite: false`, `retry: false`, `rerun: false`, `relaunch: false`. One future process creation permanently spends entitlement.

Committed authorization ALONE at `f52ec4a7c8776b929de9ceeb0044c81ce7a58c59` (`docs(research): freeze wgan seed05 training authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `0753a576246de301fe8a6664d587e977f5f2b1567ee45179dbf594bd2cd06c1a`, blob `0aa7323375fc68fe6486fe62c169a0e6716c03af`, filtered worktree == HEAD PASS, duplicate `0`, recursive `11`, total keys `142`

Safe-validated committed authorization using existing helpers only (no --execute, no runner CLI):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate 0 PASS
- member/role/seed tuple PASS (`12281/12281/12282/8283` internal 7777 bootstrap 8801)
- seed semantics PASS (model 12281, training latent/temporal/window/refit/GP 12282, eval 8283 !=7777)
- implementation PASS (runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`)
- config PASS (training config `de0b4fe7.../e0740afc...`, full_config_hash `aeab4664...`, run prefix `308cda2acc42be1b`)
- training data PASS (`3702ef77...` 926/22/63 0.8)
- runtime PASS (`17e3bb52...`)
- diagnostic persistence PASS (`ef171da...`)
- preregistration PASS (`6c4a2725...`)
- permissions/future task/marker PASS (`NM-R5-V5-WGAN-SEED-05-TRAINING-EXECUTION-171`, `.../308cda2acc42be1b/execution_started.json` ABSENT)
- future marker ABSENT PASS, checkpoint ABSENT PASS, training report ABSENT PASS, Gate authorization ABSENT PASS, training process 0 PASS

If validation had failed, would have stopped without amendment.

## 7. Preservation and exact-once campaign accounting

Preserved exactly:

- seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`
- seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (Task-167 evidence `f4d59034.../b0f95764...` marker `6bd29009...` stdout `2088cac7...`, Amendment 086 `5e395a55.../c13bbe78...`)

Campaign accounting remains during this freeze: valid primary members completed `3` (seed-01, seed-02, seed-04), primary attempts consumed `4`. Do not increment completed until seed-05 later completes both training and Gate.

No historical scientific artifacts were modified to accommodate seed-05.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, seed-05 authorization count exactly 1, marker absent, checkpoint absent, report absent):

- tracked tree clean
- seed-05 authorization count: exactly 1 (`wgan-seed-05-v1.json` at `0753a576.../0aa73233...`)
- seed-05 marker: ABSENT (`reports/research/wgan_comparator_runs/wgan-seed-05/308cda2acc42be1b/execution_started.json` absent)
- seed-05 checkpoint: ABSENT (`data/processed/research/model/wgan-comparator/wgan-seed-05/...` absent)
- seed-05 training report: ABSENT
- seed-05 Gate authorization: ABSENT
- seed-05 Gate result: ABSENT
- training process: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

If all pass:

`WGAN SEED-05 TRAINING AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-05 TRAINING: NOT PERFORMED`

Campaign remains `3` / `4`.

Next task must be `NM-R4-V5-WGAN-SEED-05-TRAINING-AUTHORIZATION-AUDIT-170` before any seed-05 scientific training process. Do NOT execute training.

This amendment is append-only, contains no self-hash.

