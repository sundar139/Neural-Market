# Amendment 084 — V5 WGAN Seed-04 Scientific Training Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-SEED-04-TRAINING-EXECUTION-163`
Risk: `R5`
Branch: `main`
Starting HEAD: `5de400db07d6b79afbbd7db7a0ab6f44cf98bbd9`
Prerequisite audit: `NM-R4-V5-WGAN-SEED-04-TRAINING-AUTHORIZATION-AUDIT-162` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed04-training-execution-5de400d` at `5de400db07d6b79afbbd7db7a0ab6f44cf98bbd9`
Authorization: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-04-v1.json` (`e866e5170c2d6d51accd453c0cfa2d1fa2d7f4e61bf277c8f1d02f22d02fa229`, blob `de597ccaa7cb8ec4617922e0812a3b6ad42a7c56`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed04_execution_v1_163.json` (commit `4e88ec6ac6525df82acb3da7210359f7a2a435d7`)
Campaign state at launch: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, valid primary members `2`, attempts consumed `3`, seed-04 authorization `VALIDATED` `e866e517.../de597cca...`, H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA scientific training execution for `wgan-seed-04` via the audited `v1` authorization. It does not authorize Gate, seed-05, reserve, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `5de400db07d6b79afbbd7db7a0ab6f44cf98bbd9`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed04-training-execution-5de400d`.
- Authorization SHA: `e866e5170c2d6d51accd453c0cfa2d1fa2d7f4e61bf277c8f1d02f22d02fa229`, blob `de597ccaa7cb8ec4617922e0812a3b6ad42a7c56`, filtered worktree == HEAD, recursive 11 objects, 142 keys, duplicate 0.
- Seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (both valid completed members, 2 of 5).
- Seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, Task-158 evidence `0dd819903338ab9e828dd7309cd3f1f96b946557b45184e313991ff17388b41a / 2db5aa7f9ee8132965b1b79f2b6d0b6099ca8ca6`, Amendment 082 `5250f16cb082cc20f098160bf5c38a4ccf74a51bfcfdd7b57f906fa887a3fbdf / 1b901697138d1707ad221669c61e14273a986214` preserved.
- Runner `56a1370cb3b76d5849083c175a3d98bc6a390261`, comparator `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`, model `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`, WGAN config `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7 / e0740afc24697f2eab3620a4243d04411aa508cb`, Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a`, prereg `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037 / 72311888542ee83ff497b5f0adbbaf6429e8452a`, execution contract `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4 / 194b68797538010f35f5d48a2ec7c4cc4eee533f`, seed schedule `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0 / 558d08bfee98dbd0c170d65e6a9b1737700c9e98`, training data `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (926 sessions, 22 lookback, 63 horizon, 0.8 fit).
- Full config hash for seed-04: `019dcb85a5b26ba6d9930dd68345123ee8788f2c0702a94485ffc95eaea6448d`, run prefix `6009789e9e8645df`.
- Runtime identity (via training runner ordering): `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / cuda/cuda deterministic true, CPU fallback PROHIBITED).
- Seed tuple: `11281 / 11281 / 11282 / 8283`, internal-selection `7777`, bootstrap `8801`, future Gate `8283`.
- Scientific contract frozen: Conditional WGAN-GP hidden 64 GP lambda 10 Adam lr 1e-4 betas (0,0.9) eps 1e-8 batch 64 critic:generator 5:1 max 400 early-stop terminal_wasserstein_normalized patience 40 min_delta 0 selection 1024/1024 block 22 horizon 63.
- Preexisting marker: absent (`reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/execution_started.json` absent).
- Preexisting checkpoint: absent.
- Preexisting training report: absent.
- Live seed-04 process: absent.
- Prelaunch governed process count: 0.
- Parser verified: `--member-id`, `--authorization`, `--execute` required flags present; exact command derived from source without dry-run.

Authorization parsed SAFE validation PASS (member `wgan-seed-04`, seeds `11281/11281/11282/8283`, runner/comparator/model/config/data/runtime/permissions all PASS, max 1 / training true).

## Exactly one training process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_runner --member-id wgan-seed-04 --authorization reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-04-v1.json --execute`

Launch in background from outset via hub `wgan-seed04`:

- Launcher PID: `40924` (hub wgan-seed04 wrapper).
- Wrapper PID: `40924`.
- Python PID: `40924` (same; direct exec).
- Process/session: `wgan-seed04:40924`.
- Start local: `2026-08-24T17:22:04.889380-04:00`.
- Start UTC: `2026-08-24T21:22:04.889380Z`.
- Launch mode: background.
- Governed process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second training process may be created.

Do not invoke Gate, seed-05, reserve, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process/session; no relaunch, no second CLI invocation.

Process record:

- Process/session ancestry: single Python process via hub `wgan-seed04`.
- End local: `2026-08-24T17:59:46.671531-04:00`.
- End UTC: `2026-08-24T21:59:46.671531Z`.
- Wall-clock duration: `2278` seconds (37m58s, hub uptime 37m23s).
- Exit code: `0` (SUCCESS).
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-163/stdout.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty stdout, no direct report; report persisted via runner).
- Stderr path: `.agent-memory/task-163/stderr.log` — bytes `450`, SHA `e24f63b66493ed2d6eb867c0b6d8594a9be5a03cae8ba7ac48122b86bccac88d` (cuBLAS warning only, no REFUSED).
- After termination, read-only inspection:

Marker:

- Path: `reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/execution_started.json`
- SHA: `adac53e0cba5410c2afa2272a182289e5109e56c30fb71ee751c88989990a54b` (1.9K)
- Count: 1 (before 0 -> after 1)
- Authorization: `wgan-seed-04-v1.json` blob `de597cca...`
- Member: `wgan-seed-04`, run prefix `6009789e9e8645df`, runtime `17e3bb52...`
- Technical entitlement consumed: `CONSUMED_BY_EXECUTION_MARKER` (governance entitlement permanently spent).

Checkpoint:

- Path: `data/processed/research/model/wgan-comparator/wgan-seed-04/6009789e9e8645df/checkpoint.pt`
- Exists: `true`
- SHA: `2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6`
- Size: `338677` bytes
- Tensor count: `32` (generator_state + critic_state)
- All finite: `true`
- Config hash inside checkpoint: `019dcb85a5b26ba6d9930dd68345123ee8788f2c0702a94485ffc95eaea6448d` (matches full_config_hash)
- Best epoch / metric from checkpoint: `39 / 1.3419804686113015`

Training report:

- Path: `reports/research/wgan_comparator_runs/wgan-seed-04/6009789e9e8645df/training_report.json`
- Exists: `true`
- SHA: `46c3bcd32f2738054a1de595689ec02e5312395c4a82bfeba207369b328d4871` (11213 bytes)
- Member: `wgan-seed-04`, run prefix `6009789e9e8645df`, seeds `11281/11281/11282/8283`

No overwrite, regeneration, repair, or rerun.

## Verification of scientific result and prospective diagnostics

Process exited with `0` (SUCCESS). Valid checkpoint and training report produced.

- Marker count: 1 PASS
- Checkpoint exists: true PASS
- Training report exists: true PASS
- All checkpoint tensors finite: true PASS
- Checkpoint size: 338677 PASS
- Tensor count: 32 PASS
- Selected epoch: 39 PASS
- Selection metric: 1.3419804686113015 PASS
- Full config hash: `019dcb85a5b26ba6d9930dd68345123ee8788f2c0702a94485ffc95eaea6448d` PASS
- Final generator epoch: 79, fit window count 672, training_completed COMPLETED, finite FINITE

Report identities: member `wgan-seed-04`, run prefix `6009789e9e8645df`, seeds `11281/11281/11282/8283`, training-data `3702ef77...`, runtime `17e3bb52...` all bound correctly.

Prospective diagnostics required since Task 137: all `PRESENT` (except historical missingness):

- critic_loss_curve length 79 PRESENT
- generator_loss_curve length 79 PRESENT
- gradient_penalty_curve length 79 PRESENT
- selection selection_metric_curve length 79 PRESENT (inside checkpoint_selection)
- critic_update_count 4345 PRESENT
- generator_update_count 869 PRESENT
- training_completion COMPLETED PRESENT
- finite_nonfinite FINITE PRESENT
- checkpoint_selection stability PRESENT (best 39 / 1.341...)
- availability map correctly marks PRESENT for above and MISSING_BY_DESIGN_HISTORICAL for wgan-seed-01
- mode_collapse_indicator `NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE` with null value PASS
- No fabricated values

Critic:generator optimizer-step accounting `4345:869` exactly `5:1` PASS.

Therefore classification is:

`VALID_EXECUTION_NO_GATE_RESULT`

No Gate result exists yet. Do not authorize or execute Gate.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_seed04_execution_v1_163.json` (commit `4e88ec6ac6525df82acb3da7210359f7a2a435d7`, SHA `computed from committed bytes`, blob via Git object)
- Records Task ID, starting HEAD `5de400db07...`, safety branch `safety/pre-wgan-seed04-training-execution-5de400d`, authorization SHA/blob `e866e517.../de597cca...`, seed tuple `11281/11281/11282/8283`, implementation/config/data identities, full_config_hash `019dcb85...`, run prefix `6009789e9e8645df`, runtime `17e3bb52...`, exact command, launch mode, PIDs, timestamps, exit 0, governed count 1, retry/relaunch/rerun 0/0/0, marker path/SHA `adac53e0...`, checkpoint path/SHA `2e8b0f4c...` 338677, report path/SHA `46c3bcd3...` 11213, stdout 0/e3b0c44..., stderr 450/e24f63b..., classification `VALID_EXECUTION_NO_GATE_RESULT`, Gate not authorized, seed-05 not authorized, reserve not authorized, H2 unresolved, final sealed, diagnostic persistence verified.

Amendment 084:

- Path: `reports/protocol/research_protocol_amendment_084.md` (this file)
- Records same load-bearing execution facts, no self-hash, does not modify Amendments 074–083.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Authorization unchanged `e866e517.../de597cca...`
- Training config unchanged `de0b4fe7.../e0740afc...`
- Runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...` unchanged
- Seed-01/02 artifacts unchanged (seed-01 `c5e234e5.../804d3b42.../c261b15...`, seed-02 `c282bc43.../747a1d8a...`, Gate markers, evidence `70e4aad3.../f52c1979...`, etc.)
- Seed-03 failed attempt unchanged `0dd81990.../2db5aa7f...`, Amendment 082 `5250f16c.../1b901697...`
- Seed-04 training produced exactly one marker, one checkpoint, one report; no Gate artifacts created.

Require:

- Task-163 governed scientific process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live seed-04 training process: 0 after termination, seed-04 Gate authorization: 0, seed-04 Gate: 0, seed-05 authorization: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

If training had failed:

`NONFINITE_TRAINING_FAILURE`

would have been classified; here training succeeded, so:

`WGAN SEED-04 TRAINING: VALID_EXECUTION_NO_GATE_RESULT`

`WGAN SEED-04 TRAINING EXECUTION: EXECUTED_PENDING_INDEPENDENT_AUDIT`

Valid primary completed count remains `2` until seed-04 later completes valid Gate execution (training alone does not yet advance completed count per WGAN comparator preregistration).

This amendment is append-only, does not self-hash.

