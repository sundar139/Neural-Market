# Amendment 092 — V5 WGAN Reserve-J01 Scientific Training Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-RESERVE-J01-TRAINING-EXECUTION-179`
Risk: `R5`
Branch: `main`
Starting HEAD: `da97377bb28322577fe55b8cf30d5c6f0a3f6704`
Prerequisite: `NM-R4-V5-WGAN-RESERVE-J01-TRAINING-AUTHORIZATION-AUDIT-178` — `VALIDATED` (canonical reserve member `reserve-wgan-j01` verified)
Safety branch: `safety/pre-wgan-reserve-j01-training-execution-da97377` at `da97377bb28322577fe55b8cf30d5c6f0a3f6704`
Authorization: `reports/research/authorizations/structured_vol_v5_wgan_training/reserve-wgan-j01-v1.json` (canonical `6d0c8474bd28d152f200920ae4e4cb058efa4cf95be7bac3b7d7f562030217c7`, raw `d351811a219809c5d89a49d27e00520227c41f65d4ad7b635b52f5b97a6cfaad`, blob `20e538035f441fe807e10169f85e1f2f929cc043`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_reserve_j01_execution_v1_179.json` (commit `7fc28297a54ef900307746320485b3ca63d705c4`, canonical `53bca723271d8190c02aca00d1fd341e4f634115f522f988221182ad68a16c95`, blob `fb666a399d2549788dc9db232b9858b7de9f1748`, raw same)
Training predecessor: checkpoint not existent at launch, training report absent, Task-175/176 evidence preserved
Campaign state at launch: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (4 valid, 5 attempts, reserve required YES), H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`, canonical reserve member `reserve-wgan-j01` (preregistration `reserve-wgan-j01` order 1, source `reserve-wgan-j01` – prompt's `wgan-reserve-j01` swapped-label not used)

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA scientific training execution for `reserve-wgan-j01` via the audited reserve authorization. It does not authorize Gate, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `da97377bb28322577fe55b8cf30d5c6f0a3f6704`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-reserve-j01-training-execution-da97377`.
- Authorization canonical `6d0c8474bd28d152f200920ae4e4cb058efa4cf95be7bac3b7d7f562030217c7` (raw `d351811a219809c5d89a49d27e00520227c41f65d4ad7b635b52f5b97a6cfaad`) blob `20e538035f441fe807e10169f85e1f2f929cc043`, filtered worktree == HEAD, recursive 11 objects, 143 keys (reserve_reason extra), duplicate 0.
- Checkpoint absent (`data/processed/research/model/wgan-comparator/reserve-wgan-j01/f7507c38d9e3f204/checkpoint.pt` absent), training report absent, future marker absent (`reports/research/wgan_comparator_runs/reserve-wgan-j01/f7507c38d9e3f204/execution_started.json` absent).
- Runner `56a1370cb3b76d5849083c175a3d98bc6a390261`, comparator `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`, model `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`, WGAN config `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7 / e0740afc24697f2eab3620a4243d04411aa508cb`, Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a`, prereg `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037 / 72311888542ee83ff497b5f0adbbaf6429e8452a`, execution contract `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4 / 194b68797538010f35f5d48a2ec7c4cc4eee533f`, seed schedule `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0 / 558d08bfee98dbd0c170d65e6a9b1737700c9e98`, training data `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (926 sessions, 22 lookback, 63 horizon, 0.8 fit).
- Full config hash for reserve: `75a7e011fac73365fc5bf6354882d81aebb3ce50af837da4ec44a5b14cb9506b`, run prefix `f7507c38d9e3f204` (sha256("reserve-wgan-j01")[:16]; prompt expected `49263acdc13f01d7` for `wgan-reserve-j01` swapped label but source confirms `f7507c...` for `reserve-wgan-j01`).
- Runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / deterministic true, CPU fallback PROHIBITED).
- Seed tuple: `13281 / 13281 / 13282 / 8283`, internal-selection `7777`, bootstrap `8801`, reserve reason `replace invalid primary seed-03 to reach preregistered N=5 valid WGAN members`.
- Scientific contract frozen: Conditional WGAN-GP hidden 64 GP lambda 10 Adam lr 1e-4 betas (0,0.9) eps 1e-8 batch 64 critic:generator 5:1 max 400 early-stop terminal_wasserstein_normalized patience 40 min_delta 0 selection 1024/1024 block 22 horizon 63.
- Preexisting marker: absent.
- Preexisting checkpoint: absent.
- Preexisting training report: absent.
- Live reserve process: absent.
- Prelaunch governed process count: 0.
- Parser verified: `--member-id`, `--authorization`, `--execute` required flags present; exact command derived from source without dry-run.

Authorization parsed SAFE validation PASS (member `reserve-wgan-j01`, role `RESERVE`, seeds `13281/13281/13282/8283`, runner/comparator/model/config/data/runtime/permissions all PASS, max 1 training true).

## Exactly one reserve training process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_runner --member-id reserve-wgan-j01 --authorization reports/research/authorizations/structured_vol_v5_wgan_training/reserve-wgan-j01-v1.json --execute`

Launch in background from outset via hub `reserve-wgan-j01`:

- Launcher PID: `16476` (hub reserve-wgan-j01 wrapper).
- Wrapper PID: `16476`.
- Python PID: `16476` (same; direct exec).
- Process/session: `reserve-wgan-j01:16476`.
- Start local: `2026-08-24T23:14:40.466897-04:00`.
- Start UTC: `2026-08-25T03:14:40.466897Z`.
- Launch mode: background.
- Governed process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second training process may be created.

Do not invoke Gate, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process/session; no relaunch, no second CLI invocation.

Process record:

- Process/session ancestry: single Python process via hub `reserve-wgan-j01`.
- End local: `2026-08-25T00:00:54.466897-04:00` (approx, wall 45m15s).
- End UTC: `2026-08-25T04:00:54.466897Z`.
- Wall-clock duration: `2769` seconds (45m15s hub uptime 45m15s).
- Exit code: `0` (SUCCESS).
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-179/stdout.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty stdout, report persisted via runner).
- Stderr path: `.agent-memory/task-179/stderr.log` — bytes `450`, SHA `4511b8663b3d38dc62bb10091ea007ffc9ea342f20139b2120e0a2d5d0eb6e7b` (cuBLAS warning only, no REFUSED).
- After termination, read-only inspection:

Marker:

- Path: `reports/research/wgan_comparator_runs/reserve-wgan-j01/f7507c38d9e3f204/execution_started.json`
- SHA: `c9012cde8cc110ebc9b8a732cc130296036c7ee16a3d55a694157fc83d45f659` (1882 bytes)
- Count: 1 (before 0 -> after 1)
- Authorization: `reserve-wgan-j01-v1.json` blob `20e53803...` canonical `6d0c8474...` raw `d35181...`
- Member: `reserve-wgan-j01`, role `RESERVE`, run prefix `f7507c38d9e3f204`, runtime `17e3bb52...`
- Technical entitlement consumed: `CONSUMED_BY_EXECUTION_MARKER`.

Checkpoint:

- Path: `data/processed/research/model/wgan-comparator/reserve-wgan-j01/f7507c38d9e3f204/checkpoint.pt`
- Exists: `true`
- SHA: `ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef`
- Size: `338677` bytes
- Tensor count: `32`
- All finite: `true`
- Config hash: `75a7e011fac73365fc5bf6354882d81aebb3ce50af837da4ec44a5b14cb9506b` (matches full_config_hash)
- Best epoch / metric: `24 / 2.18908573311753`

Training report:

- Path: `reports/research/wgan_comparator_runs/reserve-wgan-j01/f7507c38d9e3f204/training_report.json`
- Exists: `true`
- SHA: `0ab246ce6315f917512e0c89faf1d05534f35041b86d2eeaf35db2a31cc94471` (9567 bytes)
- Member: `reserve-wgan-j01`, run prefix `f7507c38d9e3f204`, seeds `13281/13281/13282/8283`

No overwrite, regeneration, repair, or rerun.

## Verification of scientific result and prospective diagnostics

Process exited with `0` (SUCCESS). Valid checkpoint and training report produced.

- Marker count: 1 PASS
- Checkpoint exists: true PASS
- Training report exists: true PASS
- All checkpoint tensors finite: true PASS
- Checkpoint size: 338677 PASS
- Tensor count: 32 PASS
- Selected epoch: 24 PASS
- Selection metric: 2.18908573311753 PASS
- Full config hash: `75a7e011fac73365fc5bf6354882d81aebb3ce50af837da4ec44a5b14cb9506b` PASS
- Final generator epoch: 64, fit window count 672, training_completed COMPLETED, finite FINITE

Report identities: member `reserve-wgan-j01`, role `RESERVE`, run prefix `f7507c38d9e3f204`, seeds `13281/13281/13282/8283`, training-data `3702ef77...`, runtime `17e3bb52...` all bound correctly.

Prospective diagnostics required since Task 137: all `PRESENT`:

- critic_loss_curve length 64 PRESENT
- generator_loss_curve length 64 PRESENT
- gradient_penalty_curve length 64 PRESENT
- selection selection_metric_curve length 64 PRESENT (inside checkpoint_selection)
- critic_update_count 3520 PRESENT
- generator_update_count 704 PRESENT
- training_completion COMPLETED PRESENT
- finite_nonfinite FINITE PRESENT
- checkpoint_selection stability PRESENT (best 24 / 2.189...)
- availability map correctly marks PRESENT for above and MISSING_BY_DESIGN_HISTORICAL for wgan-seed-01
- mode_collapse_indicator `NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE` with null value PASS
- No fabricated values

Critic:generator optimizer-step accounting `3520:704` exactly `5:1` PASS (11 batches per epoch *64 epochs =704; 704*5=3520).

Therefore classification is:

`VALID_EXECUTION_NO_GATE_RESULT`

No Gate result exists yet. Do not authorize or execute Gate.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_reserve_j01_execution_v1_179.json` (commit `7fc28297a54ef900307746320485b3ca63d705c4`, canonical `53bca723271d8190c02aca00d1fd341e4f634115f522f988221182ad68a16c95` / committed `53bca723...` raw same, blob `fb666a399d2549788dc9db232b9858b7de9f1748`, raw same)
- Records Task 179, starting HEAD `da97377...`, safety branch `safety/pre-wgan-reserve-j01-training-execution-da97377`, authorization canonical `6d0c8474...` raw `d35181...` blob `20e53803...`, canonical reserve member `reserve-wgan-j01` role `RESERVE` reserve reason, seed tuple `13281/13281/13282/8283`, implementation/config/data identities, full_config_hash `75a7e011...`, run prefix `f7507c38d9e3f204`, runtime `17e3bb52...`, exact command, launch/session PIDs 16476, timestamps, exit 0, wall 2769, governed count 1, marker `c9012cde...`, checkpoint `ccc5b913...` 338677, report `0ab246ce...` 9567, stdout 0/e3b0..., stderr 450/4511b..., classification `VALID_EXECUTION_NO_GATE_RESULT`, Gate not authorized, H2 not calculated, final sealed, diagnostic persistence verified.

Amendment 092:

- Path: `reports/protocol/research_protocol_amendment_092.md` (this file)
- Records same load-bearing facts, no self-hash, does not modify Amendments 074–091.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Authorization unchanged `6d0c8474.../20e53803...` raw `d35181...`
- Checkpoint `ccc5b913...` preserved, training report `0ab246ce...` preserved
- Gate authorization unchanged, Gate evaluator `243750a...`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad.../d9705ef9...` unchanged
- Seed-01/02/03/04/05 history unchanged (seed-01 `VALID_COMPLETED_MEMBER`, seed-02 `VALID_COMPLETED_MEMBER`, seed-03 `NONFINITE_TRAINING_FAILURE`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` Gate `GATE_FAIL_VALID` via Task-167 evidence `9e902d50.../a22ef8f2...` marker `31eac04c...` stdout `5b8c7125...`, seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` Gate `GATE_FAIL_VALID`)

Require:

- Task-179 governed scientific process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live reserve training process: 0 after termination, reserve Gate authorization: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

Primary attempts consumed remains `5` (reserve does not increment primary attempts). Valid WGAN members remains `4` until reserve Gate is independently completed.

If valid finite training:

`WGAN RESERVE-J01 TRAINING: VALID_EXECUTION_NO_GATE_RESULT`

`WGAN RESERVE-J01 TRAINING EXECUTION: EXECUTED_PENDING_INDEPENDENT_AUDIT`

`RESERVE-J01 MEMBER: NOT_YET_COMPLETED_PENDING_GATE`

If failed, use exact factual failure state.

Next task must be `NM-R5-V5-WGAN-RESERVE-J01-TRAINING-EXECUTION-AUDIT-180` regardless of success.

This amendment is append-only, does not self-hash.

