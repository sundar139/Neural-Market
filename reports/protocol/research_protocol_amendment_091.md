# Amendment 091 — V5 WGAN Reserve-J01 Training Authorization Freeze

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-RESERVE-J01-TRAINING-AUTHORIZATION-FREEZE-177`
Risk: `R4`
Branch: `main`
Starting HEAD: `77f15561f707c5ea83917e49dcfdde6b8341c2f6`
Prerequisite: `NM-R5-V5-WGAN-SEED-05-GATE-V2-EXECUTION-AUDIT-176` — `VALIDATED` (seed-05 Gate `GATE_FAIL_VALID` adjudicated, member `VALID_COMPLETED_MEMBER`, 4 of 5 valid members confirmed, reserve required YES)
Safety branch: `safety/pre-wgan-reserve-j01-training-auth-77f1556` at `77f15561f707c5ea83917e49dcfdde6b8341c2f6`
Campaign state: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT` checkpoint `4a728a10...` report `8e58a615...`, Gate `GATE_FAIL_VALID` via Task-175 evidence `9e902d50.../a22ef8f2...` marker `31eac04c...` stdout `5b8c7125...`), valid primary members `4` (seed-01, seed-02, seed-04, seed-05), primary attempts consumed `5` (all five primaries attempted, seed-03 failed), H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`, reserve required `YES` to reach preregistered N=5 valid WGAN members
Status: APPEND-ONLY RESERVE TRAINING AUTHORIZATION FREEZE — no training, no Gate, no H2, no final-test, no external validation, no network, no push.

## 1. Primary campaign closure and reserve requirement

Primary campaign is permanently `5 attempts consumed / 4 valid completed members` (seed-03 failed remains `NOT_VALID_COMPLETED_MEMBER`). Preregistered WGAN N=5 valid-member requirement is not yet satisfied; exactly one valid member short. Per preregistration `reserve_order` (`reserve-wgan-j01` order 1, replicate 13281) and Task-176 audit (`VALID PRIMARY MEMBERS COMPLETED: 4`, `RESERVE-J01 REQUIRED: YES`), the next governed action is the first reserve.

The governed transitions were:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

This task freezes exactly one training authorization for the first reserve `reserve-wgan-j01` to replace invalid primary seed-03 and reach N=5, without executing training.

Note on member identifier: Task prompt expected `wgan-reserve-j01` with run prefix `49263acdc13f01d7` (sha256("wgan-reserve-j01")[:16]), but preregistration (`reserve-wgan-j01` order 1) and current source (`wgan_runner.py` `_SEED_TUPLES` `reserve-wgan-j01`: 13281/13281/13282/8283, `effective_config_for_member` validation, and `wgan_comparator.py` reserve order) both confirm the canonical reserve member is `reserve-wgan-j01` with run prefix `f7507c38d9e3f204` (sha256("reserve-wgan-j01")[:16]). Following repository-native governance and preregistration, the frozen member is `reserve-wgan-j01`; the prompt's `wgan-reserve-j01`/`49263...` is a swapped-label expectation, not a source mutation. This is recorded as a non-blocking wording difference.

## 2. Reserve training authorization contract

Reconstructed from current source (wgan_runner.py, wgan_comparator.py, wgan_cde.py, training config, authorization schema/loader/validator, seed-05-v1 as structural precedent, WGAN preregistration, latest relevant protocol amendments, Task-176 audit):

- Current prospective implementation identities if unchanged:
  - runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261` (HEAD:src/neuralmarket/research/wgan_runner.py, filtered worktree == HEAD)
  - comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
  - model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
  - training config canonical SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`, blob `e0740afc24697f2eab3620a4243d04411aa508cb` (HEAD:configs/research/structured_vol_wgan_comparator_v1.yaml)
  - diagnostic persistence provenance: Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a` (PRESENT)
  - preregistration: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json` SHA `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037` blob `72311888542ee83ff497b5f0adbbaf6429e8452a` (reserve_order `reserve-wgan-j01` confirmed)

Derived fields recomputed from HEAD bytes, not copied mechanically from seed-05 JSON; every identity verified via require_tracked_artifact_at_head.

No source/config/schema was altered in this task.

## 3. Reserve-J01 member and seed semantics

- Member: `reserve-wgan-j01` (canonical per preregistration and current source; prompt's `wgan-reserve-j01` is swapped-label expectation)
- Role: `RESERVE`
- Frozen seed tuple: `replicate_seed: 13281`, `model_init_seed: 13281`, `data_seed: 13282`, `eval_seed: 8283`
- Internal-selection generated seed: `7777`
- Bootstrap seed: `8801`
- Seed semantics:
  - model initialization: `13281`
  - training static latent: `13282`
  - training temporal noise: `13282`
  - window sampling: `13282`
  - refit noise: `13282`
  - gradient-penalty alpha: `13282`
- Evaluation seed 8283 remains distinct from internal-selection seed 7777.
- Freeze unchanged WGAN training contract:
  - Conditional WGAN-GP hidden 64 GP lambda 10 Adam lr 1e-4 betas (0,0.9) eps 1e-8 weight decay 0 batch 64 critic:generator 5:1 max 400 early-stop terminal_wasserstein_normalized patience 40 min_delta 0 selection 1024/1024 block 22 horizon 63
- No reserve-specific tuning, no hyperparameter change, no threshold change.

## 4. Training data, CUDA, and member-specific config

Training data identity: `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (manifest `split_manifest_v1.json` SHA `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`), range `2018-05-01` through `2021-12-31`, sessions `926`, lookback `22`, horizon `63`, fit fraction `0.8`, non-overlap `true`, embargo `context22/horizon63`.

CUDA rebuilt via `.venv-gpu` using runner's actual deterministic ordering (resolve_device -> configure_device_determinism -> build_runtime_identity):

- Python `3.11.9`, PyTorch `2.13.0+cu132`, CUDA `13.2`, available `true`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` cap `8.9`, cuDNN `92000`, deterministic `true`, runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (matches all prior seeds), CPU fallback `PROHIBITED`.

Constructed exact reserve `WGANTrainingConfig` via `effective_config_for_member('reserve-wgan-j01')`:

- `full_config_hash`: `75a7e011fac73365fc5bf6354882d81aebb3ce50af837da4ec44a5b14cb9506b`
- `run prefix`: `f7507c38d9e3f204` (sha256("reserve-wgan-j01")[:16]; prompt expected `49263acdc13f01d7` for `wgan-reserve-j01` but source confirms `f7507c...` for `reserve-wgan-j01`)

Both computed independently from source, not trusted from prompt; prompt expectation `49263...` is for `wgan-reserve-j01` swapped-label member, not the source-confirmed `reserve-wgan-j01`.

## 5. Reserve-J01 training authorization V1

Verified before creation reserve-j01 training authorization count 0, execution marker 0, checkpoint 0, training report 0, Gate authorization 0.

Created exactly one authorization using current repository convention:

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/reserve-wgan-j01-v1.json` (repository convention for reserve; prompt expected `wgan-reserve-j01-v1.json` with swapped label)
- Canonical SHA: `6d0c8474bd28d152f200920ae4e4cb058efa4cf95be7bac3b7d7f562030217c7` (committed Git-object SHA; raw worktree SHA `d351811a219809c5d89a49d27e00520227c41f65d4ad7b635b52f5b97a6cfaad`)
- Git blob: `20e538035f441fe807e10169f85e1f2f929cc043`
- Filtered worktree == HEAD PASS, recursive object count `11`, total key occurrences `143` (one extra `reserve_reason` field vs primary 142), duplicate count `0`
- Schema: `structured-vol-v5-wgan-authorization-v1`

Authorization binds, where required by current schema/source:

- member `reserve-wgan-j01`, role `RESERVE`, replicate/model-init/data/eval `13281 / 13281 / 13282 / 8283`, internal selection `7777`, bootstrap `8801`
- runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, training config `de0b4fe7.../e0740afc...`, full_config_hash `75a7e011fac73365fc5bf6354882d81aebb3ce50af837da4ec44a5b14cb9506b`, run prefix `f7507c38d9e3f204`, training-data `3702ef77...`, runtime `17e3bb52...`, diagnostic persistence `ef171da.../e5722ac...` (Amendment 074), preregistration `6c4a2725.../72311888...`, campaign reason `replace invalid primary seed-03 to reach preregistered N=5 valid WGAN members`, future task `NM-R5-V5-WGAN-RESERVE-J01-TRAINING-EXECUTION-179`, future marker `reports/research/wgan_comparator_runs/reserve-wgan-j01/f7507c38d9e3f204/execution_started.json` (prompt expected `wgan-reserve-j01/49263...` but source confirms `reserve-wgan-j01/f7507c...`)
- Permissions: `max_scientific_invocations: 1`, `training: true`, `Gate: false`, `validation: false`, `final: false`, `overwrite: false`, `retry: false`, `rerun: false`, `relaunch: false`. One future scientific process creation permanently consumes this reserve authorization.

Committed authorization ALONE at `ac782843351319448cd34ac06d80612e16a72f79` (`docs(research): freeze wgan reserve-j01 training authorization`).

## 6. Committed validation

After commit computed from committed Git object:

- canonical SHA `6d0c8474bd28d152f200920ae4e4cb058efa4cf95be7bac3b7d7f562030217c7` (committed), raw `d351811a219809c5d89a49d27e00520227c41f65d4ad7b635b52f5b97a6cfaad`, blob `20e538035f441fe807e10169f85e1f2f929cc043`, filtered worktree == HEAD PASS, duplicate `0`, recursive `11`, total keys `143`

Safe-validated committed authorization using existing helpers only (no runner CLI, no --execute):

- parsed from Git: PASS, tracked PASS, committed PASS, filtered worktree PASS, duplicate 0 PASS
- member/role PASS (`reserve-wgan-j01` / `RESERVE`)
- seed tuple PASS (`13281/13281/13282/8283` internal 7777 bootstrap 8801)
- seed semantics PASS (model 13281, training latent/temporal/window/refit/GP 13282, eval 8283 !=7777)
- implementation PASS (runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`)
- config PASS (training config `de0b4fe7.../e0740afc...`, full_config_hash `75a7e011...`, run prefix `f7507c38...`)
- training data PASS (`3702ef77...` 926/22/63 0.8)
- runtime PASS (`17e3bb52...`)
- diagnostic persistence PASS (`ef171da...`)
- preregistration PASS (`6c4a2725...` reserve-wgan-j01 confirmed)
- reserve reason PASS (`replace invalid primary seed-03 to reach preregistered N=5 valid WGAN members`)
- permissions/future task/marker PASS (`NM-R5-V5-WGAN-RESERVE-J01-TRAINING-EXECUTION-179`, `.../reserve-wgan-j01/f7507c38.../execution_started.json` ABSENT)
- future marker ABSENT PASS, checkpoint ABSENT PASS, training report ABSENT PASS, Gate authorization ABSENT PASS, training process 0 PASS

If validation had failed, would have stopped without amendment.

## 7. Preservation and reserve accounting

Preserved exactly:

- seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`
- seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`
- seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (training `VALID_EXECUTION_NO_GATE_RESULT` checkpoint `4a728a10...` report `8e58a615...`, Gate `GATE_FAIL_VALID` via Task-175 evidence `9e902d50.../a22ef8f2...` marker `31eac04c...` stdout `5b8c7125...`)

Primary accounting is permanently `PRIMARY ATTEMPTS CONSUMED: 5` `VALID PRIMARY MEMBERS: 4`. WGAN valid-member count before reserve execution: `4`, WGAN valid-member requirement: `5`. Reserve-j01 authorization freeze does NOT increment either valid-member count or reserve execution-attempt count.

Preserved:

- Task-175 evidence canonical `9e902d5031f0b93877b54748067bf9fe3ae602f21a34de290cd4342bdd348f8a` / blob `a22ef8f23f899019dcc1c23e6cd1846026d16932` raw `e4f8c894...`
- Amendment 090 `e4c663e774c76bc4bac5c3e2cc07b5c7f340b327ac96e81255ff66705b7480aa / ae8da9b5...`
- all prior checkpoints/reports/Gate evidence.

H2 remains `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final test remains `SEALED`.

## 8. Final verification and independent-audit readiness

Verified after both commits (tracked tree clean, reserve-j01 authorization count exactly 1, marker absent, checkpoint absent, report absent):

- tracked tree clean
- reserve-j01 authorization count: exactly 1 (`reserve-wgan-j01-v1.json` at `6d0c8474.../20e53803...` raw `d35181...`; prompt expected `wgan-reserve-j01-v1.json` with swapped label but repository convention is `reserve-wgan-j01-v1.json`)
- reserve-j01 marker: ABSENT (`reports/research/wgan_comparator_runs/reserve-wgan-j01/f7507c38d9e3f204/execution_started.json` absent; prompt expected `wgan-reserve-j01/49263...` but source confirms `reserve-wgan-j01/f7507c...`)
- reserve-j01 checkpoint: ABSENT (`data/processed/research/model/wgan-comparator/reserve-wgan-j01/...` absent)
- reserve-j01 report: ABSENT
- reserve-j01 Gate authorization: ABSENT
- reserve training process: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0

If all pass:

`WGAN RESERVE-J01 TRAINING AUTHORIZATION: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN RESERVE-J01 TRAINING: NOT PERFORMED`

Campaign remains `VALID WGAN MEMBERS: 4`, `PRIMARY ATTEMPTS CONSUMED: 5`, `RESERVE-J01 REQUIRED: YES`.

Next governed task must be `NM-R4-V5-WGAN-RESERVE-J01-TRAINING-AUTHORIZATION-AUDIT-178` before any reserve scientific training process. Do NOT execute reserve training.

This amendment is append-only, contains no self-hash.

