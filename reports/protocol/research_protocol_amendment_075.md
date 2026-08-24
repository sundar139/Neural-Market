# Amendment 075 — V5 WGAN Seed-02 Training Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-02-TRAINING-AUTHORIZATION-FREEZE-139`
Risk: `R4`
Branch: `main`
Starting HEAD: `1aed3c6efd73b18b36d6bc1b276d39a69ec1e055`
Prerequisite audit: `NM-R4-V5-WGAN-TRAINING-DIAGNOSTIC-PERSISTENCE-AUDIT-138`
Prerequisite verdict: `WGAN SEED-01 VALID_COMPLETED_MEMBER / GATE_FAIL_VALID / MISSING_BY_DESIGN_HISTORICAL; DIAGNOSTIC PERSISTENCE VALIDATED; SEED-02 READY_FOR_SEPARATE_AUTHORIZATION_FREEZE`
Status: APPEND-ONLY AUTHORIZATION FREEZE — no WGAN training, Gate, seed-03/04/05, reserve, H2, final-test, network, or push.

## 1. Purpose and governing boundary

This amendment freezes exactly one prospective CUDA training authorization for the next WGAN primary member under the new audited diagnostic-persistence runner. It creates no scientific execution, Gate execution, or comparative result.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

The frozen prior state was:

- seed-01: `VALID_COMPLETED_MEMBER`;
- seed-01 Gate: `GATE_FAIL_VALID`;
- seed-01 training diagnostics: `MISSING_BY_DESIGN_HISTORICAL` (Amendment 074);
- diagnostic persistence: `VALIDATED` (runner `56a1370`, comparator `78a9da57`);
- seed-02 authorization: `NOT CREATED`;
- H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`;
- final test: `SEALED`.

THIS TASK FREEZES AUTHORIZATION ONLY. No training, no runner `--execute`, no Gate, no later member authorization, no H2, no final-test, no push.

## 2. Discovery — current contract traced

The following committed records were read before any freeze:

- `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` (`6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037`, blob `72311888542ee83ff497b5f0adbbaf6429e8452a`);
- `reports/protocol/research_protocol_amendment_059.md` and `060.md` (prereg and H2 denominator clarification);
- `reports/protocol/research_protocol_amendment_074.md` (`ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00`, blob `e5722ac2a2ad669cc95adbba408cc7db1b57c93a` — prospective diagnostic persistence);
- `reports/research/structured_vol_v5_seed_schedule_v1.json` (`8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`, blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`);
- `reports/research/structured_vol_v5_wgan_execution_contract_v1.json` (`4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4`, blob `194b68797538010f35f5d48a2ec7c4cc4eee533f`);
- `configs/research/structured_vol_wgan_comparator_v1.yaml` (`de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`, blob `e0740afc24697f2eab3620a4243d04411aa508cb`);
- `src/neuralmarket/research/wgan_runner.py` (blob `56a1370cb3b76d5849083c175a3d98bc6a390261`);
- `src/neuralmarket/research/wgan_comparator.py` (blob `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`);
- `src/neuralmarket/models/wgan_cde.py` (blob `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`);
- `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json` through `v3.json` (v3 blob `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`);
- `src/neuralmarket/research/wgan_runner.py:validate_authorization_payload` required-field set;
- `reports/research/evidence/structured_vol_v5_wgan_seed01_execution_v3_127.json` (Task-127) and `*_gate_v2_execution_135.json` (Task-135) where useful.

The runner-validated field set is exactly:

`schema_version, member_id, replicate_seed, model_init_seed, data_seed, eval_seed, effective_config_sha256, effective_config_git_blob, comparator_methodology_sha256, amendment_060_sha256, seed_schedule_sha256, seed_schedule_git_blob, execution_contract_git_blob, runner_git_blob, implementation_source_git_blobs, execution_recipe_head, requested_device, expected_resolved_device, expected_runtime_identity_sha256, max_scientific_invocations, training_authorized, validation_authorized, final_test_authorized`

Repository-native path/name convention for seed-02 (compatible with implementation):

`reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v1.json`

No unsupported field was invented. No seed-01 v3 field was copied mechanically; every identity was recomputed from HEAD bytes.

## 3. Tracked identities recomputed — canonical convention

For TRACKED artifacts: canonical SHA-256 is SHA-256 of exact committed Git-object bytes at `HEAD`; Git identity is the `HEAD` Git blob; worktree safety requires `git hash-object` equals `HEAD` blob. For UNTRACKED scientific artifacts: raw file SHA-256 (not applicable here).

Fresh recomputation at `1aed3c6` before freeze:

- WGAN runner: `56a1370cb3b76d5849083c175a3d98bc6a390261` — `git rev-parse HEAD:src/neuralmarket/research/wgan_runner.py` equals `git hash-object src/neuralmarket/research/wgan_runner.py`;
- WGAN comparator: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166` — matches filtered worktree;
- WGAN model: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe` — matches filtered worktree;
- WGAN scientific config Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb` — matches filtered worktree;
- WGAN scientific config canonical SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7` — SHA-256 of `git cat-file -p HEAD:configs/research/structured_vol_wgan_comparator_v1.yaml`;
- Canonical WGAN config hash (WGANTrainingConfig) for `wgan-seed-02` tuple: `5c223604327df9bcc61debaa8743db2d8f8101faadbf1dc9192b86d7bff3ee2f` (`wgan-seed-01` reference `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58` preserved for historical comparison; seed-specific hash differs by replicate/data seeds, not scientific configuration);
- Preregistration SHA: `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` (blob `72311888542ee83ff497b5f0adbbaf6429e8452a`);
- Amendment-060 SHA: `2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c` (blob `a1ba052abe8b4a50887ec84b934e16a328e60596`);
- Seed schedule SHA/blob: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` / `558d08bfee98dbd0c170d65e6a9b1737700c9e98`;
- Execution contract SHA/blob: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4` / `194b68797538010f35f5d48a2ec7c4cc4eee533f`;
- Run prefix for `wgan-seed-02`: `e1cc68218d9eef71` (`sha256("wgan-seed-02")[:16]`).

All expected audited identities matched; no `BLOCKED_SEED02_AUTHORIZATION_INPUT_DRIFT`.

## 4. Frozen seed-02 scientific identity

- Member: `wgan-seed-02`
- Role: `PRIMARY` (`reserve: false`)
- Frozen seed tuple (per `_SEED_TUPLES` and seed schedule):
  - `replicate_seed: 9281`
  - `model_init_seed: 9281`
  - `data_seed: 9282`
  - `eval_seed: 8283` (also `evaluation_seed: 8283`)
- Preserved common family semantics (per prereg and Amendment-062 provenance):
  - internal-selection generated seed: `7777`
  - bootstrap seed: `8801`
  - future post-training Gate evaluation seed: `8283`
- Training design: frozen singleton WGAN-GP (per `configs/research/structured_vol_wgan_comparator_v1.yaml`):
  - batch size: `64`
  - critic:generator ratio: `5:1`
  - Adam lr: `1e-4`
  - betas: `(0.0, 0.9)`
  - epsilon: `1e-8`
  - max generator epochs: `400`
  - early stopping patience: `40`
  - min_delta: `0`
  - selection metric: `terminal_wasserstein_normalized` (direction lower_is_better; tie earliest epoch then lexicographically smallest identity)
  - CUDA-only; no scientific CPU fallback

No value was altered.

## 5. Diagnostic-persistence contract bound

Seed-02 runs under the new audited persistence implementation (`56a1370`/`78a9da57`, Amendment 074). Prospective `training_report.json` at `reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/training_report.json` will persist, where available, via `serialize_wgan_training_diagnostics` observational-only serialization (no extra forward pass, RNG, or data access):

- `critic_loss_curve`
- `generator_loss_curve`
- `gradient_penalty_curve`
- `selection_metric_curve` plus `checkpoint_selection` (selected epoch/metric, final epoch, early-stop state)
- `critic_update_count` and `generator_update_count` (exact optimizer-step counters)
- `training_completion` (final epoch + fit-window count)
- `finite_nonfinite` status
- diagnostic availability map (`PRESENT` for above)

Mode-collapse semantics: `status: NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE`, `value: null` (no committed definition exists; Amendment 074). Historical seed-01 is recorded as `MISSING_BY_DESIGN_HISTORICAL` in the availability map and `historical_missingness.wgan-seed-01`; seed-01 artifacts were not bound or modified and the authorization does not imply seed-01 used the new runner.

## 6. CUDA runtime rebuilt deterministically

Via `.venv-gpu` and the repository runtime identity builder in runner order (`resolve_device("cuda")` → `configure_device_determinism` → `build_runtime_identity`):

- requested device: `cuda`
- resolved device: `cuda`
- CUDA available: `true`
- CPU fallback: `false`/`PROHIBITED`
- Environment (recomputed fresh, matches Audit-138 expected):
  - Python: `3.11.9`
  - PyTorch: `2.13.0+cu132`
  - CUDA: `13.2`
  - GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
  - capability: `8.9`
  - cuDNN: `92000`
  - deterministic algorithms: `true`; `cudnn_benchmark: false`; `cudnn_deterministic: true`
  - driver: `610.47`
- Runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (SHA of canonical JSON `runtime-identity-v1`)

No `BLOCKED_SEED02_AUTHORIZATION_RUNTIME_DRIFT`.

## 7. Authorization artifact — exactly one

Safety branch (without switching): `safety/pre-wgan-seed02-training-auth-1aed3c6` at `1aed3c6efd73b18b36d6bc1b276d39a69ec1e055`

Exactly one artifact created using the current validated schema:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v1.json`
- Schema: `structured-vol-v5-wgan-authorization-v1`, artifact version `v1`
- Authorization commit: `5f98bc8dd90879304260118dc3f42f47c6672605`
- Canonical authorization SHA (SHA-256 of `git cat-file -p HEAD:path`): `8dee7f132a5a5a610e97c9cf7ab774cfc362141226f4bc017db2cee9c483c75b`
- Authorization Git blob: `3a4d1977255e1eebbbeaf6a8e774e7fc6f3de4da`

Every field required by the current runner was bound:

- `member: wgan-seed-02`, `role: PRIMARY`, `reserve: false`
- seed tuple `9281 / 9281 / 9282 / 8283`
- `runner_git_blob: 56a1370cb3b76d5849083c175a3d98bc6a390261`
- `implementation_source_git_blobs: {model: 2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe, comparator: 78a9da57ffb297a0f5ec71f740fa590f4ad7d166}`
- `model` / `comparator` / `WGAN scientific config` / canonical config hash / run prefix / `effective_config_git_blob` / `effective_config_sha256` / training-data identity via frozen training-only manifest hash `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` referenced by config)
- `runtime_config_path / sha / blob` and `expected_runtime_identity_sha256: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- CUDA requirement `requested_device: cuda / expected_resolved_device: cuda`
- Permissions: `max_scientific_invocations: 1`, `training_authorized: true`, `validation_authorized: false`, `final_test_authorized: false`; `overwrite: false`, `relaunch: false`, `rerun: false`, `automatic_reserve_execution: false`; `authorization_consumed: false`, `scientific_execution_performed: false`
- Gate permission remains `false` (not authorized within training authorization)
- No other member authorized

The authorization artifact was the sole file in its commit.

## 8. Committed authorization verification — no training

The authorization was read back from the committed Git object via SAFE library functions only (`_normalize_authorization_path`, `_load_authorization`, `validate_authorization_payload`); no CLI `--execute`, no training marker, no Gate:

- Parsed from Git object: `true`
- Tracked: `PASS`
- Committed: `PASS`
- Filtered worktree blob == HEAD: `PASS` (`3a4d1977255e1eebbbeaf6a8e774e7fc6f3de4da`)
- Schema: `PASS` (`structured-vol-v5-wgan-authorization-v1`)
- Member: `wgan-seed-02`
- Seed tuple: `9281 / 9281 / 9282 / 8283`
- Source identities: `PASS` (runner `56a1370`, comparator `78a9da57`, model `2f5cf1dd2cc...`, prereg `6c4a27…`, Amd-060 `2f9bb1…`, seed schedule `8c471c…`, execution contract `194b68…`)
- Config: `PASS` (`de0b4fe7…` + `e0740afc…` + `5c223604…` + `e1cc68218d9eef71`)
- Data: `PASS` (training-only manifest; `git cat-file -p` identity preserved)
- Runtime: `PASS` (`17e3bb52…`, `cuda/cuda`, `92000`, `8.9`)
- Permissions: `PASS` (`1` / `true` / `false` / `false`; retry/relaunch/overwrite `false`)
- Training CLI: `NOT INVOKED`
- Training marker (`reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/execution_started.json`): `absent`
- Training execution: `0`

No `BLOCKED_COMMITTED_SEED02_AUTHORIZATION_VERIFICATION_FAILURE`.

## 9. Preservation and firewalls

This amendment is append-only and does not self-hash.

Verified after the freeze commit (tracked tree clean at each commit; safety branch preserved):

- seed-01 training authorizations `v1/v2/v3`: unchanged
- seed-01 Gate authorization (`structured_vol_v5_wgan_gate/wgan-seed-01-gate-v2-v1.json`): unchanged
- seed-01 checkpoint: historical artifact preserved; no new checkpoint for seed-02
- seed-01 training marker (`…/wgan-seed-01/ebfbf915ec8316d8/execution_started.json`): preserved; seed-02 marker absent
- seed-01 Gate marker: preserved; seed-02 Gate not executed
- seed-01 training report (`…/wgan-seed-01/ebfbf915ec8316d8/training_report.json`): unchanged (797 bytes, `bd8e4dd5…`)
- Task-127 evidence (`structured_vol_v5_wgan_seed01_execution_v3_127.json`): unchanged
- Task-135 evidence (`structured_vol_v5_wgan_seed01_gate_v2_execution_135.json`): unchanged
- Gate evaluator (`f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`): unchanged
- Amendments 069–074: unchanged (added 075 only)

Firewalls:

- real WGAN training: `0`
- real Gate: `0`
- seed-03/04/05 authorization: `0`
- reserve authorization: `0`
- H2: `0` (`UNRESOLVED_PENDING_WGAN_COMPARATOR`)
- final-test access: `0` (`SEALED`)
- network: `0`
- push: `0`

Amendment 074 prospective hardening preserved; no self-hash introduced.

## 10. Status and next governed action

`WGAN SEED-01: VALID_COMPLETED_MEMBER`

`WGAN SEED-01 GATE: GATE_FAIL_VALID`

`WGAN SEED-01 TRAINING DIAGNOSTICS: MISSING_BY_DESIGN_HISTORICAL`

`WGAN TRAINING DIAGNOSTIC PERSISTENCE: VALIDATED`

`WGAN SEED-02 TRAINING AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-02 TRAINING: NOT EXECUTED`

`WGAN SEED-02 GATE: NOT EXECUTED`

`SEED-03/04/05: NOT AUTHORIZED`

`RESERVE: NOT AUTHORIZED`

`H2: UNRESOLVED_PENDING_WGAN_COMPARATOR`

`FINAL TEST: SEALED`

Next governed action: independent read-only audit of seed-02 training authorization before any scientific execution. Do NOT execute seed-02.
