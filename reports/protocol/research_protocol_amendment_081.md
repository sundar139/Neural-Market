# Amendment 081 — V5 WGAN Seed-03 Training Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-03-TRAINING-AUTHORIZATION-FREEZE-156`
Risk: `R4`
Branch: `main`
Starting HEAD: `fbc4e97e815723f7e73407d8aef4ca70b3e4b13c`
Prerequisite: `NM-R4-V5-WGAN-SEED-02-GATE-V2-ARTIFACT-PROVENANCE-ADJUDICATION-155` — `VALIDATED`
Campaign predecessor: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, valid primary members completed `2` (Task-155 validated), Task-152 Gate evidence `70e4aad393151ea2762a145fd64143ec2421288b3f1ed707200536efa2955e21 / c28a4862a8dd0295f9a38d7a9bd153b781734558`, Amendment 080 `f0985d097315caeb4181a6e446a30d168d2b241d9b725130c79f05103780244d / 2fd2335e255340b3e5d8ec1c8bc9eedd6f1792d8`
Status: APPEND-ONLY TRAINING AUTHORIZATION FREEZE — no training, no Gate, no seed-04/05, no reserve, no H2, no final-test, no network, no push.

## 1. Campaign state

Seed-01 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT` at 63/3.06..., Gate `GATE_FAIL_VALID`).

Seed-02 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT` at 29/1.89..., Gate `GATE_FAIL_VALID` with variance 1.94 PASS, terminal 15.69 FAIL, uniqueness 1.0 PASS, ACF1 1.04 FAIL, both valid completed members).

Primary completed count remains `2` until seed-03 later completes both valid training and valid Gate execution (per WGAN comparator preregistration and H2 denominator Amendment 060).

This task freezes exactly one training authorization for the next primary member `wgan-seed-03` under the current repaired Gate evaluator `243750a...` and true Amendment 078 `6ef7faf21af130ba58c8227abfb3b6aac9030c9c1567c1fd2537170ca460c16f / 4093a01...`, preserving 2 valid members.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

## 2. Training authorization contract

Reconstructed from current source (wgan_runner.py, wgan_comparator.py, model source, training config, authorization schema/loader/validator, seed-02-v2 as precedent, preregistration, Amendments 074, 076–080, relevant tests):

- Current prospective implementation identities if unchanged:
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261` (HEAD:src/neuralmarket/research/wgan_runner.py, filtered worktree == HEAD)
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166` (HEAD:src/neuralmarket/research/wgan_comparator.py)
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
  - training config canonical SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`, blob `e0740afc24697f2eab3620a4243d04411aa508cb` (HEAD:configs/research/structured_vol_wgan_comparator_v1.yaml, filtered worktree == HEAD)
  - diagnostic persistence provenance: Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a` (prospective diagnostics PRESENT)
  - preregistration: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` SHA `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` blob `72311888542ee83ff497b5f0adbbaf6429e8452a`

Current source/schema requires fields and naming conventions were derived, not copied mechanically from seed-02 JSON; every identity was recomputed from HEAD bytes.

No source/config/schema was altered in this task.

## 3. Seed-03 member and seed semantics

- Member: `wgan-seed-03`
- Role: `PRIMARY`
- Frozen seed tuple: `replicate_seed: 10281`, `model_init_seed: 10281`, `data_seed: 10282`, `eval_seed: 8283`
- Training seed semantics:
  - model weights initialization: `10281`
  - training static latent: `10282`
  - training temporal noise: `10282`
  - training window sampling: `10282`
  - refit noise: `10282`
  - gradient-penalty interpolation alpha: `10282`
- Common internal-selection generated seed: `7777`
- Common bootstrap seed: `8801`
- Do NOT use eval_seed `8283` for internal-selection generated paths.
- Training remains frozen:
  - Conditional WGAN-GP, Neural-CDE-style generator, conditional Neural-CDE path critic
  - lambda GP `10`, Adam `lr 1e-4` betas `(0,0.9)` eps `1e-8` weight decay `0`
  - batch `64`, critic:generator `5:1`, max generator epochs `400`, early-stop metric `terminal_wasserstein_normalized`, patience `40`, min_delta `0`, selection generated `1024`, selection MBB `1024`, block `22`, horizon `63`
- No hyperparameter search.

## 4. Training data, CUDA, and member-specific config

Training data identity: `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (manifest `split_manifest_v1.json` SHA `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`), training range `2018-05-01` through `2021-12-31`, sessions `926`, lookback `22`, horizon `63`, selection `fit_fraction: 0.8`, non-overlap `true`, embargo `context 22 / horizon 63`.

CUDA rebuilt via `.venv-gpu` using training runner's deterministic ordering (resolve_device -> configure_device_determinism -> build_runtime_identity):

- Python `3.11.9`, PyTorch `2.13.0+cu132`, CUDA `13.2`, CUDA available `true`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` capability `8.9`, cuDNN `92000`, deterministic `true`, CPU fallback `PROHIBITED`, runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (recomputed fresh, matches expected).

Constructed exact seed-03 `WGANTrainingConfig` via `effective_config_for_member('wgan-seed-03')`:

- `full_config_hash`: `911898b3bb5e4d1c2913a6b46d7440ba3c8faae2a127c63827543db5276d825b`
- `run prefix`: `187dc9e00bd21c79` (sha256("wgan-seed-03")[:16])

Do NOT invent either value.

## 5. Seed-03 training authorization V1

Created exactly one new authorization using current repository convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-03-v1.json`
- Canonical SHA: `afd4d8457b6dd599942d5db3f2d1d330e60bbea72bede027720cf309659265e4`
- Git blob: `cdc3df7b11e20031869d199d79f24ada41acfe20`
- Filtered worktree == HEAD PASS, recursive object count `11`, duplicate count `0`, diagnostic occurrence not applicable

Before creation verified no seed-03 authorization exists (0).

Authorization binds, where required by current schema:

- member `wgan-seed-03`, role `PRIMARY`, seed tuple `10281 / 10281 / 10282 / 8283`, internal-selection `7777`, bootstrap `8801`
- runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, training config SHA/blob `de0b4fe7.../e0740afc...`, `full_config_hash` `911898b3...`, `run prefix` `187dc9e00bd21c79`, training-data identity `3702ef77...`, runtime `17e3bb52...`, diagnostic-persistence provenance `ef171da.../e5722ac...` (Amendment 074), preregistration `6c4a2725.../72311888...`, max generator epochs `400`, batch `64`, critic:generator `5`, future scientific task `NM-R5-V5-WGAN-SEED-03-TRAINING-EXECUTION-158`, future technical execution marker `reports/research/wgan_comparator_runs/wgan-seed-03/187dc9e00bd21c79/execution_started.json` (derived from current runner and computed run prefix)
- Permissions: `max_scientific_invocations: 1`, `training: true`, `Gate: false`, `validation: false`, `final: false`, `overwrite: false`, `retry/rerun: false`, `relaunch: false`. One future process creation spends governance entitlement regardless of marker or execution success. Do not authorize Gate, seed-04/05 or reserve.

Committed authorization ALONE at `407617e22c33cbd05b208957cadabb8aeff18dc0` (`docs(research): freeze wgan seed03 training authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `afd4d8457b6dd599942d5db3f2d1d330e60bbea72bede027720cf309659265e4`, blob `cdc3df7b11e20031869d199d79f24ada41acfe20`, filtered worktree == HEAD PASS, recursive duplicate `0`

Read authorization from committed Git object and ran SAFE authorization validation helpers only (no --execute):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate keys 0 PASS
- member/role/seed tuple/internal-selection/bootstrap PASS
- implementation (runner/comparator/model) PASS
- config (training config SHA/blob, full_config_hash, run prefix, training-data identity) PASS
- runtime PASS
- diagnostic-persistence provenance PASS
- preregistration PASS
- permissions/future task/future marker PASS
- future marker `reports/research/wgan_comparator_runs/wgan-seed-03/187dc9e00bd21c79/execution_started.json` ABSENT PASS
- checkpoint/report ABSENT PASS (data/processed/research/model/wgan-comparator/wgan-seed-03/... absent, reports/research/wgan_comparator_runs/wgan-seed-03/... absent)
- scientific training process: 0 PASS

If safe validation had failed, would have stopped without rewrite — none failed.

## 7. Preservation and exact-once campaign state

Require byte-identical preservation of seed-01 and seed-02 scientific history.

- Seed-01 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- Seed-02 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (`EXECUTED_AUDITED` at 29/1.89... and Gate `GATE_FAIL_VALID` variance 1.94 PASS, terminal 15.69 FAIL, uniqueness 1.0 PASS, ACF1 1.04 FAIL)
- Preserved seed-02: training authorization V2 `c282bc43.../747a1d8a...`, training marker `175fcad9...` (1), checkpoint `ca72d43... 338677`, training report `c123724...` (diagnostics PRESENT), Task-144 evidence `bf7c7c89.../a4bd4557...`, Gate V2 authorization `610b5e.../8f609f78...`, Gate marker `d7846e8f...` (1), Task-152 Gate evidence `70e4aad393.../c28a4862...`, Amendment 080 `f0985d09.../2fd2335e...`
- No seed-01/02 artifact was rewritten to accommodate seed-03.
- Primary completed count remains `2` until seed-03 later completes both valid training and valid Gate execution.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, seed-03 training authorization count exactly 1, seed-03 marker absent, checkpoint absent, training report absent, Gate authorization absent, Gate result absent):

- tracked tree clean
- seed-03 training authorization count: exactly 1 (`wgan-seed-03-v1.json` at `afd4d845.../cdc3df7b...`)
- seed-03 marker: ABSENT (`reports/research/wgan_comparator_runs/wgan-seed-03/187dc9e00bd21c79/execution_started.json` absent)
- seed-03 checkpoint: ABSENT (`data/processed/research/model/wgan-comparator/wgan-seed-03/...` absent)
- seed-03 training report: ABSENT
- seed-03 Gate authorization: ABSENT
- seed-03 Gate result: ABSENT
- seed-03 training process: 0, seed-04/05 authorization: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

No repository-wide test suite is required because no production source/tests changed.

If all pass:

`WGAN SEED-03 TRAINING AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-03 TRAINING: NOT PERFORMED`

Next task must be `NM-R4-V5-WGAN-SEED-03-TRAINING-AUTHORIZATION-AUDIT-157` before any seed-03 scientific process. Do NOT execute training.

This amendment is append-only, contains no self-hash.

