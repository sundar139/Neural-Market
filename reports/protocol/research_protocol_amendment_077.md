# Amendment 077 — V5 WGAN Seed-02 Scientific Training Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-SEED-02-TRAINING-EXECUTION-144`
Risk: `R5`
Branch: `main`
Starting HEAD: `41f95ad5765d4dd2fe6a25094c02328ac8313c49`
Prerequisite audit: `NM-R4-V5-WGAN-SEED-02-V2-TRAINING-AUTHORIZATION-AUDIT-143` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed02-v2-training-execution-41f95ad` at `41f95ad5765d4dd2fe6a25094c02328ac8313c49`
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed02_execution_v2_144.json`
Execution-evidence commit: `00107a0a50b3f95de2da685998658af44d9f04a2`
Authorization: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v2.json` (`c282bc433905641e9413db28aa135cbfda60dac92d59b87cdaf68f766dae4491`, blob `747a1d8a11a1a4d97605cad154d870dca196022c`)

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA scientific training execution for `wgan-seed-02` via the source-derived unique-key `v2` authorization. `v1` was never used. It does not authorize seed-03/04/05, reserve, Gate, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `41f95ad5765d4dd2fe6a25094c02328ac8313c49`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed02-v2-training-execution-41f95ad`.
- V2 authorization SHA: `c282bc433905641e9413db28aa135cbfda60dac92d59b87cdaf68f766dae4491`, blob `747a1d8a11a1a4d97605cad154d870dca196022c`, filtered worktree == HEAD PASS, recursive duplicate 0, diagnostic occurrence 1.
- V1 disposition: `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` (SHA `8dee7f132a5a5a610e97c9cf7ab774cfc362141226f4bc017db2cee9c483c75b`, blob `3a4d1977255e1eebbbeaf6a8e774e7fc6f3de4da`, divergent placeholder `d4f9a7c9.../7E0D` adjudicated source-derived; never used).
- Runner Git blob: `56a1370cb3b76d5849083c175a3d98bc6a390261`.
- Comparator Git blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`.
- Model Git blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`.
- Runtime-config SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`, blob `e0740afc24697f2eab3620a4243d04411aa508cb`.
- Execution-contract SHA: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4`, blob `194b68797538010f35f5d48a2ec7c4cc4eee533f`.
- Canonical config hash (seed-02): `5c223604327df9bcc61debaa8743db2d8f8101faadbf1dc9192b86d7bff3ee2f`, run prefix `e1cc68218d9eef71`.
- Amendment 074: `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00` / `e5722ac2a2ad669cc95adbba408cc7db1b57c93a`.
- Amendment 076: `2f8baf2f429abb337771d6cfa41ee113d64e28373d68d5941269d8155ce1f869` / `64aecbacad733fec3fc961c4756477cd3ce3e738`.
- Runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / cuda/cuda deterministic true, CPU fallback PROHIBITED).
- Preexisting marker: absent (`reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/execution_started.json` absent).
- Preexisting checkpoint: absent (`data/processed/research/model/wgan-comparator/wgan-seed-02/e1cc68218d9eef71/checkpoint.pt` absent).
- Preexisting training report: absent.
- Live seed-02 runner process: absent.
- Prelaunch governed process count: 0.
- Parser verified: `--member-id`, `--authorization`, `--execute` required flags present; exact command derived from source without dry-run.

V2 parsed SAFE validation PASS (member `wgan-seed-02`, seeds `9281/9281/9282/8283`, runner/comparator/model/config/data/methodology/runtime/permissions all PASS, max 1 / training true / validation false / final false).

## Exactly one process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_runner --member-id wgan-seed-02 --authorization reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v2.json --execute`

Launch in background from the outset:

- Launcher PID: `1440` (hub wgan-seed02 wrapper).
- Terminal/wrapper PID: `1440`.
- Python runner PID: `1440` (same process; no intermediate shell).
- Process/session: `wgan-seed02:1440`.
- Start local: `2026-08-24T02:41:31.295387-04:00`.
- Start UTC: `2026-08-24T06:41:31.295387Z`.
- Launch mode: background.
- Governed process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second training process may be created, even if marker remains absent.

Do not invoke v1 authorization, another seed-02 command, seed-03/04/05, reserve, Gate, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process chain; no relaunch, no second CLI invocation.

Process record:

- Actual Python runner PID: `1440`.
- Process ancestry: single Python process via hub `wgan-seed02` (no fork chain beyond hub wrapper).
- End local: `2026-08-24T03:16:24.949248-04:00`.
- End UTC: `2026-08-24T07:16:24.949248Z`.
- Wall-clock duration to artifact: `2080.653861` seconds (34m40s hub uptime).
- Exit code: `0`.
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-144/stdout.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Stderr path: `.agent-memory/task-144/stderr.log` — bytes `448`, SHA `e24f63b66493ed2d6eb867c0b6d8594a9be5a03cae8ba7ac48122b86bccac88d` (nonfatal cuBLAS warning about primary CUDA context; not a failure).

After termination, read-only inspection:

- Execution marker: created.
  - Path: `reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/execution_started.json`
  - SHA: `175fcad9a3ce590e86e4a8cb6e8dbbbba05a1031e630d790dc4a70e0960390c4`
  - Count: 1 (marker_count_before 0 -> marker_count_after 1)
  - Authorization: `wgan-seed-02-v2.json` blob `747a1d8a11a1a4d97605cad154d870dca196022c`
  - Member: `wgan-seed-02`, run prefix `e1cc68218d9eef71`, seeds `9281/9281/9282/8283`, runner `56a1370...`, comparator `78a9da57...`, runtime `17e3bb52...`
  - PID/timestamp: marker contains implementation_identity and runtime; marker creation is atomic via `os.link` exclusive.
  - Technical entitlement consumed: `CONSUMED_BY_EXECUTION_MARKER` (governance entitlement permanently spent).

- Training report: created.
  - Path: `reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/training_report.json`
  - SHA: `c123724afe8a88a5370414c40cdb503818015846549d50c284179898a0672fc2`
  - Size: `10047` bytes.
  - Scientific boundary entered: true, market data loaded true, model constructed true, training entered true, training completed true.

- Checkpoint: created.
  - Path: `data/processed/research/model/wgan-comparator/wgan-seed-02/e1cc68218d9eef71/checkpoint.pt`
  - SHA: `ca72d43abd4ad1fc2899583be9d7d3a5a206e0ddba21d99b67d01763d046193b`
  - Size: `338677` bytes.
  - Tensor count: 32 (generator 18 + critic 14), nonfinite 0, finite true, config hash `5c223604...` matches.

No repair, deletion, replacement, retraining, or checkpoint reselection.

## Classification and prospective diagnostics

The process produced a valid finite completed checkpoint and training report. No Gate was run. Classification therefore is the frozen implementation's applicable status:

`VALID_EXECUTION_NO_GATE_RESULT` — valid finite completed training member without Gate result. No more specific status emitted.

Recorded:

- Selected epoch: `29`
- Best selection metric (terminal_wasserstein_normalized): `1.8903446799783874`
- Checkpoint path/SHA/size: as above, tensor finite PASS.
- Training report SHA/size: as above, classification retained even if metric is scientifically poor — valid poor result retained, not rejected or rerun.

Prospective diagnostic-persistence contract verified present in seed-02 training report (new runner 56a1370):

- `critic_loss_curve: PRESENT` length `69`
- `generator_loss_curve: PRESENT` length `69`
- `gradient_penalty_curve: PRESENT` length `69`
- `selection_metric_curve/checkpoint history: PRESENT` length `69` (selection_metric_curve in checkpoint_selection), best `29`, final `69`, stopped_early `true`
- `critic_update_count: PRESENT` `3795`
- `generator_update_count: PRESENT` `759`
- `training_completion: PRESENT` (`COMPLETED`, final `69`, fit_window_count `672`)
- `finite_nonfinite: PRESENT` (`FINITE`)
- `checkpoint_selection_stability: PRESENT`
- `diagnostic availability map: PRESENT` (all 7 PRESENT plus wgan-seed-01 MISSING_BY_DESIGN_HISTORICAL)
- `mode_collapse_indicator: NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE` value `null` (no fabrication)
- `historical seed-01 diagnostics: MISSING_BY_DESIGN_HISTORICAL` (value null, not rebound)
- Curve lengths finite: true, all 69 == final_generator_epoch.
- Fabricated diagnostics: 0.

Not calculated: H2, Gate. Poor-result retention policy: valid poor result retained.

If the process had failed before valid completed member, the factual state (1 process, marker/checkpoint/report as observed, no retry) would have been retained — no retry in this execution; success case here.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_seed02_execution_v2_144.json` (commit `00107a0...`, SHA `b69c6fbbe74f0e6549c5e30cd46815eb45b36f36d84630527552548fc5c83cc1`, blob via Git object)
- Records Task ID, starting HEAD `41f95ad...`, safety branch, V2 authorization path/SHA `c282bc43...`/blob `747a1d8a...`, V1 prohibited disposition `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` and `v1_used: false`, member/seeds, runner/comparator/model/config/data/methodology identities, runtime, exact command, PIDs, start/end, exit `0`, governed count `1`, retry/relaunch/rerun `0/0/0`, marker path/SHA `175fcad9...`, checkpoint path/SHA `ca72d43...`, training report path/SHA `c123724...`, selected epoch/metric `29 / 1.890...`, diagnostic findings PRESENT, Gate NOT RUN, H2 NOT CALCULATED, final SEALED.

Amendment 077:

- Path: `reports/protocol/research_protocol_amendment_077.md` (this file)
- v1 never used, v2 authorization identity bound, exactly one scientific process via `wgan-seed-02-v2.json`, technical marker state CONSUMED, checkpoint/report identities recorded, training classification `VALID_EXECUTION_NO_GATE_RESULT`, diagnostic persistence verified, poor-result retained, Gate NOT RUN, seed-03/04/05 NOT AUTHORIZED, reserve NOT AUTHORIZED, H2 UNRESOLVED, final SEALED, no self-hash.
- No self-hash, does not modify Amendments 074–076.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- V1 byte-identical `8dee7f13.../3a4d1977...` (not mutated, not used).
- V2 byte-identical `c282bc43.../747a1d8a...` (now consumed by marker, but file not mutated).
- Runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, WGAN config `de0b4fe7.../e0740afc...` unchanged.
- Amendments 074 `ef171da...`, 075 `6da76064...`, 076 `2f8baf2f...` unchanged.
- Seed-01 artifacts: authorizations v1 `c5e234e5`, v2 `804d3b42`, v3 `c261b15c`, Gate `b6960813`, checkpoint `332614...`, marker `18d246aa...`, reports unchanged.
- Task-144 governed process count: EXACTLY 1, retry 0, relaunch 0, rerun 0, live seed-02 training process 0 after termination.
- Gate: 0, seed-03/04/05 authorization 0, reserve 0, validation 0, external validation 0, H2 0, final-test access 0, network 0, push 0.

No repository-wide suite merely because training completed; Gate not yet authorized.

Next task must be `NM-R5-V5-WGAN-SEED-02-TRAINING-EXECUTION-AUDIT-145` regardless of success.

This amendment is append-only, does not self-hash.

