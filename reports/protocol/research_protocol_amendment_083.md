# Amendment 083 — V5 WGAN Seed-04 Training Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-04-TRAINING-AUTHORIZATION-FREEZE-161`
Risk: `R4`
Branch: `main`
Starting HEAD: `7d7eddf5bc9bee0e1a46df09e1a72d0d3cd96f4d`
Prerequisite: `NM-R4-V5-WGAN-SEED-03-TRAINING-ARTIFACT-PROVENANCE-ADJUDICATION-160` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed04-training-auth-7d7eddf` at `7d7eddf5bc9bee0e1a46df09e1a72d0d3cd96f4d`
Campaign predecessor: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, valid primary members completed `2` (Task-160 validated), Task-158 evidence `0dd819903338ab9e828dd7309cd3f1f96b946557b45184e313991ff17388b41a / 2db5aa7f9ee8132965b1b79f2b6d0b6099ca8ca6`, Amendment 082 `5250f16cb082cc20f098160bf5c38a4ccf74a51bfcfdd7b57f906fa887a3fbdf / 1b901697138d1707ad221669c61e14273a986214`
Status: APPEND-ONLY TRAINING AUTHORIZATION FREEZE — no training, no Gate, no seed-05, no reserve, no H2, no final-test, no network, no push.

## 1. Campaign state

Seed-01 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT`, Gate `GATE_FAIL_VALID`).

Seed-02 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT`, Gate `GATE_FAIL_VALID`).

Seed-03 remains `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER` (authorization `VALIDATED_CONSUMED` at `afd4d8457b6dd599942d5db3f2d1d330e60bbea72bede027720cf309659265e4 / cdc3df7b11e20031869d199d79f24ada41acfe20`, execution `EXECUTED_AUDITED` with marker `f52c19799af6f1ffaa0c5b401d2620228f772699640a5050ba651c6df28daeed`, no checkpoint, no training report, stderr `002785f473b9679803409a552b4a1921af4a8075871532d68574a94f92b2512f` nonfinite `REFUSED: execution: non-finite model parameter`).

Primary valid completed count remains `2` and primary attempts consumed remains `3` until seed-04 later completes both valid training and valid Gate execution (per WGAN comparator preregistration and H2 denominator Amendment 060).

This task freezes exactly one training authorization for the next primary member `wgan-seed-04` under the current frozen identities, preserving 2 valid members and the failed seed-03 as a non-completing attempt.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

## 2. Training authorization contract

Reconstructed from current source (wgan_runner.py, wgan_comparator.py, wgan_cde.py, training config, authorization schema/loader/validator, seed-03-v1 as structural precedent, preregistration, Amendments 074, 081–082, relevant tests):

- Current prospective implementation identities if unchanged:
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261` (HEAD:src/neuralmarket/research/wgan_runner.py, filtered worktree == HEAD)
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166` (HEAD:src/neuralmarket/research/wgan_comparator.py)
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe` (HEAD:src/neuralmarket/models/wgan_cde.py)
  - training config canonical SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`, blob `e0740afc24697f2eab3620a4243d04411aa508cb` (HEAD:configs/research/structured_vol_wgan_comparator_v1.yaml, filtered worktree == HEAD)
  - diagnostic persistence provenance: Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a` (prospective diagnostics PRESENT)
  - preregistration: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` SHA `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` blob `72311888542ee83ff497b5f0adbbaf6429e8452a`
  - execution contract SHA `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4` blob `194b68797538010f35f5d48a2ec7c4cc4eee533f`
  - seed schedule SHA `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`

Current source/schema requires fields and naming conventions were derived, not copied mechanically from seed-03 JSON; every identity was recomputed from HEAD bytes and .venv-gpu deterministic ordering.

No source/config/schema was altered in this task.

## 3. Seed-04 member and seed semantics

- Member: `wgan-seed-04`
- Role: `PRIMARY`
- Frozen seed tuple: `replicate_seed: 11281`, `model_init_seed: 11281`, `data_seed: 11282`, `eval_seed: 8283`
- Training seed semantics:
  - model weights initialization: `11281`
  - training static latent: `11282`
  - training temporal noise: `11282`
  - training window sampling: `11282`
  - refit noise: `11282`
  - gradient-penalty interpolation alpha: `11282`
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

Constructed exact seed-04 `WGANTrainingConfig` via `effective_config_for_member('wgan-seed-04')`:

- `full_config_hash`: `019dcb85a5b26ba6d9930dd68345123ee8788f2c0702a94485ffc95eaea6448d`
- `run prefix`: `6009789e9e8645df` (sha256("wgan-seed-04")[:16])

Do NOT invent either value. Both computed, not hardcoded.

## 5. Seed-04 training authorization V1

Created exactly one new authorization using current repository convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-04-v1.json`
- Canonical SHA: `e866e5170c2d6d51accd453c0cfa2d1fa2d7f4e61bf277c8f1d02f22d02fa229`
- Git blob: `de597ccaa7cb8ec4617922e0812a3b6ad42a7c56`
- Filtered worktree == HEAD PASS, recursive object count `11`, duplicate count `0`, total key occurrences `142`

Before creation verified no seed-04 authorization exists (0).

Authorization binds, where required by current schema:

- member `wgan-seed-04`, role `PRIMARY`, seed tuple `11281 / 11281 / 11282 / 8283`, internal-selection `7777`, bootstrap `8801`
- runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, training config SHA/blob `de0b4fe7.../e0740afc...`, `full_config_hash` `019dcb85a5b26ba6d9930dd68345123ee8788f2c0702a94485ffc95eaea6448d`, `run prefix` `6009789e9e8645df`, training-data identity `3702ef77...`, runtime `17e3bb52...`, diagnostic-persistence provenance `ef171da.../e5722ac...` (Amendment 074), preregistration `6c4a2725.../72311888...`, execution contract `4f2ab91c.../194b6879...`, seed schedule `8c471c33.../558d08bf...`, max generator epochs `400`, batch `64`, critic:generator `5`, future scientific task `NM-R5-V5-WGAN-SEED-04-TRAINING-EXECUTION-163`, future technical execution marker `reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/execution_started.json` (derived from current runner and computed run prefix)
- Permissions: `max_scientific_invocations: 1`, `training: true`, `Gate: false`, `validation: false`, `final: false`, `overwrite: false`, `retry/rerun: false`, `relaunch: false`. One future process creation spends governance entitlement regardless of marker or execution success. Do not authorize Gate, seed-05 or reserve.

Committed authorization ALONE at `b898936b0586ab8326f147282f064b7252ff1d08` (`docs(research): freeze wgan seed04 training authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `e866e5170c2d6d51accd453c0cfa2d1fa2d7f4e61bf277c8f1d02f22d02fa229`, blob `de597ccaa7cb8ec4617922e0812a3b6ad42a7c56`, filtered worktree == HEAD PASS, recursive duplicate `0`, recursive object count `11`, total key occurrences `142`

Read authorization from committed Git object and ran SAFE authorization validation helpers only (no --execute):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate keys 0 PASS
- member/role/seed tuple/internal-selection/bootstrap PASS
- implementation (runner/comparator/model) PASS
- config (training config SHA/blob, full_config_hash, run prefix, training-data identity) PASS
- runtime PASS
- diagnostic-persistence provenance PASS
- preregistration PASS
- permissions/future task/future marker PASS
- future marker `reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/execution_started.json` ABSENT PASS
- checkpoint/report ABSENT PASS (data/processed/research/model/wgan-comparator/wgan-seed-04/... absent, reports/research/wgan_comparator_runs/wgan-seed-04/... absent)
- scientific training process: 0 PASS

If safe validation had failed, would have stopped without rewrite — none failed.

## 7. Preservation and exact-once campaign state

Require byte-identical preservation of seed-01, seed-02, and failed seed-03.

- Seed-01 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (authorization V3 `c42d14d8.../922623b6...`, marker/run `ebfbf915ec8316d8`, checkpoint, training report diagnostics missing historical, Gate V2 `b6960813...`, etc.)
- Seed-02 remains `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (authorization V2 `c282bc43.../747a1d8a...` full hash `5c223604...`, marker `e1cc68218d9eef71`, checkpoint `ca72d43...`, report `c123724...`, Gate V2 `610b5e.../8f609f78...`, evidence `70e4aad393.../c28a4862...`, Amendment 080 `f0985d09.../2fd2335e...`)
- Seed-03 remains `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER` (authorization `afd4d845.../cdc3df7b...` hash `911898b3...` prefix `187dc9e00bd21c79`, marker `f52c1979...`, no checkpoint, no report, evidence `0dd81990.../2db5aa7f...`, Amendment 082 `5250f16c.../1b901697...`)
- Preserved exactly Task-158 evidence `0dd819903338ab9e828dd7309cd3f1f96b946557b45184e313991ff17388b41a / 2db5aa7f9ee8132965b1b79f2b6d0b6099ca8ca6` and Amendment 082 `5250f16cb082cc20f098160bf5c38a4ccf74a51bfcfdd7b57f906fa887a3fbdf / 1b901697138d1707ad221669c61e14273a986214`
- No seed-01/02/03 artifact was rewritten to accommodate seed-04.
- Primary valid completed remains `2`, primary attempts consumed `3` until seed-04 later completes both valid training and valid Gate execution.
- Runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, training config `de0b4fe7.../e0740afc...` unchanged.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, seed-04 training authorization count exactly 1, seed-04 marker absent, checkpoint absent, training report absent, Gate authorization absent, Gate result absent):

- tracked tree clean
- seed-04 training authorization count: exactly 1 (`wgan-seed-04-v1.json` at `e866e517.../de597cca...`)
- seed-04 marker: ABSENT (`reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/execution_started.json` absent)
- seed-04 checkpoint: ABSENT (`data/processed/research/model/wgan-comparator/wgan-seed-04/...` absent)
- seed-04 training report: ABSENT
- seed-04 Gate authorization: ABSENT
- seed-04 Gate result: ABSENT
- seed-04 training process: 0, seed-05 authorization: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

No repository-wide test suite is required because no production source/tests changed.

If all pass:

`WGAN SEED-04 TRAINING AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-04 TRAINING: NOT PERFORMED`

Next task must be `NM-R4-V5-WGAN-SEED-04-TRAINING-AUTHORIZATION-AUDIT-162` before any seed-04 scientific process. Do NOT execute training.

This amendment is append-only, contains no self-hash.

