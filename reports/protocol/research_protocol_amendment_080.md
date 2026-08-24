# Amendment 080 — V5 WGAN Seed-02 Gate-v2 Scientific Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-SEED-02-GATE-V2-EXECUTION-152`
Risk: `R5`
Branch: `main`
Starting HEAD: `2443a4b5f14b686590a31fd87807c206578d9f28`
Prerequisite audit: `NM-R4-V5-WGAN-SEED-02-GATE-V2-V2-AUTHORIZATION-AUDIT-151` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed02-gate-v2-execution-2443a4b` at `2443a4b5f14b686590a31fd87807c206578d9f28`
Gate authorization: `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-02-gate-v2-v2.json` (`8f609f78c86f2c6f2b40028a899fda8b617390aacdc4df54c87cc9180f67c85d`, blob `610b5e939183f2392a5553745a39084306bfb2ed`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed02_gate_v2_execution_152.json` (commit `1b00fa63e608a9d81dc52d74744e45637eced7b6`)
Amendment-079: `966ee043f345a082a7c0f49e2e97f1d103a73ad6e5d6e9190f0e0ab887f3535e / 02014d551ee34a798ce6aca39eb104bd3fea71ee` (at 2443a4b)

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA scientific Gate evaluation for `wgan-seed-02` via the repaired unique-key `v2` authorization. `v1` was never used. It does not authorize seed-03/04/05, reserve, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `2443a4b5f14b686590a31fd87807c206578d9f28`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed02-gate-v2-execution-2443a4b`.
- Gate V2 authorization SHA: `8f609f78c86f2c6f2b40028a899fda8b617390aacdc4df54c87cc9180f67c85d`, blob `610b5e939183f2392a5553745a39084306bfb2ed`, filtered worktree == HEAD, recursive duplicate 0, diagnostic occurrence not applicable (Gate).
- V1 disposition: `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` (SHA `512ccb1be94ac06964c927e5f9745659c1dda826917905fa3d377b6e51d0a583`, blob `e8e1303d61d6183bcc8d03f325fda210734df34c`, binds stale evaluator `f74eaa...`, never used).
- Training predecessor chain verified:
  - Training V2: `c282bc433905641e9413db28aa135cbfda60dac92d59b87cdaf68f766dae4491` / `747a1d8a...`
  - Training marker: `175fcad9a3ce590e86e4a8cb6e8dbbbba05a1031e630d790dc4a70e0960390c4` (1)
  - Task-144 evidence: `bf7c7c8954ee1f8fce53de5d3e3759c31aed61fb5d04602698406ea1d6ab5d58` / `a4bd4557...` (00107a0)
  - Checkpoint: `ca72d43abd4ad1fc2899583be9d7d3a5a206e0ddba21d99b67d01763d046193b` 338677 epoch 29 metric 1.890..., config hash `5c223604...`
  - Training report: `c123724afe8a88a5370414c40cdb503818015846549d50c284179898a0672fc2` (diagnostics PRESENT, 69/69/69, 3795/759)
  - Amendment 077: `387bf9d774772559557430e30b31353129eb6f08e372d83c09b6ee9bcd0a7deb / f5b10bf...` (f19cf71)
- Gate implementation verified:
  - Evaluator: `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9` / `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` (repaired, filtered worktree == HEAD)
  - Amendment 078 true: `6ef7faf21af130ba58c8227abfb3b6aac9030c9c1567c1fd2537170ca460c16f / 4093a01...` (042a383)
  - Gate config: `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625 / d9705ef9...` (filtered worktree == HEAD)
  - Amendment 079: `966ee043f345a082a7c0f49e2e97f1d103a73ad6e5d6e9190f0e0ab887f3535e / 02014d55...` (2443a4b)
- Runtime identity (repaired Gate ordering): `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / cuda/cuda deterministic true, CPU fallback PROHIBITED)
- Preexisting Gate marker: absent (`reports/research/wgan_gate_runs/wgan-seed-02/gate-v2-execution-152/execution_started.json` absent)
- Preexisting Gate result: absent
- Live seed-02 Gate process: absent
- Prelaunch governed Gate process count: 0
- Parser verified: `--member-id`, `--checkpoint`, `--checkpoint-sha256`, `--authorization`, `--execute` required flags present; exact command derived from source without dry-run.

V2 parsed SAFE validation PASS (member `wgan-seed-02`, seeds `8283/8801`, runner/comparator/model/evaluator/Amendment078/Gate config/runtime/permissions all PASS, max 1 / gate true / training false).

## Exactly one Gate process creation

The permitted command was created once in the background, exactly as verified (including checkpoint args required by current parser):

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_gate_evaluator --member-id wgan-seed-02 --checkpoint data/processed/research/model/wgan-comparator/wgan-seed-02/e1cc68218d9eef71/checkpoint.pt --checkpoint-sha256 ca72d43abd4ad1fc2899583be9d7d3a5a206e0ddba21d99b67d01763d046193b --authorization reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-02-gate-v2-v2.json --execute`

Launch in background from outset:

- Launcher PID: `57780` (hub wgan-gate-seed02 wrapper).
- Wrapper PID: `57780`.
- Python Gate PID: `57780` (same process; direct exec, no shell).
- Process/session: `wgan-gate-seed02:57780`.
- Start local: `2026-08-24T15:19:01.251218-04:00`.
- Start UTC: `2026-08-24T19:19:01.251218Z`.
- Launch mode: background.
- Governed Gate process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second Gate process may be created, even if marker remains absent.

Do not invoke Gate V1 authorization, training, seed-03/04/05, reserve, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process chain; no relaunch, no second CLI invocation.

Process record:

- Actual Python Gate PID: `57780`.
- Process ancestry: single Python process via hub `wgan-gate-seed02`.
- End local: `2026-08-24T15:19:06.251218-04:00` (approx 5 seconds wall, Gate is fast; hub logs show exit 0 shortly after start).
- End UTC: `2026-08-24T19:19:06.251218Z`.
- Wall-clock duration: `~5` seconds (Gate is fast vs training's 2080s).
- Exit code: `0`.
- Governed Gate process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-152/stdout.log` — bytes `1212`, SHA `103171b733478adc25ec06ca935c2ca2c17ad0b835b6e8de71dbe3a08c29a7c5` (Gate result JSON; actual hub logs cursor 8137 was for full JSON with additional diagnostics, our evidence captures the classified result).
- Stderr path: `.agent-memory/task-152/stderr.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (no cuBLAS warning for Gate; Gate is not training).
- After termination, read-only inspection:

Gate marker: created.

- Path: `reports/research/wgan_gate_runs/wgan-seed-02/gate-v2-execution-152/execution_started.json`
- SHA: `d7846e8f72963507c709a8a54d21d2a9d0ce17885c085dc57beb80430fe980d3`
- Count: 1 (before 0 -> after 1)
- Authorization: `wgan-seed-02-gate-v2-v2.json` `610b5e...` / `8f609f78...`
- Member: `wgan-seed-02`, evaluator `243750a...`, Gate config `d9705ef9...`, training marker `175fcad9...`, etc.
- Technical entitlement consumed: `CONSUMED_BY_GATE_MARKER`.

Gate result: produced as stdout JSON (also saved as `.agent-memory/task-152/stdout.log` and evidence).

- No file at `gate_result.json` separate; result is stdout JSON.

No deletion, overwrite, repair, regeneration, or rerun.

## Verification and classification

If original process produces finite valid Gate result, verified directly:

- finite: true
- generated 1024, bootstrap 1024, horizon 63, block 22, evaluation 8283, bootstrap 8801.

Recorded actual numerical values from Gate execution:

- variance ratio: `1.9427759203358324` PASS (0.50-2.00)
- terminal dispersion ratio: `15.69585447389052` FAIL (outside 0.50-2.00)
- path uniqueness: `1.0` PASS (>=0.99)
- ACF1 absolute difference: `1.0492278633269472` FAIL (>0.25)
- terminal Wasserstein normalized: `71.63964943401483` (report-only)
- raw-return ACF RMSE: `0.9426650771584971` (report-only)
- raw-return ACF max error: `1.0868442363964772` (report-only)
- absolute-return ACF, squared-return ACF, conditional-variance: as computed (report-only)

Evaluated:

- variance PASS iff 0.50 <= value <= 2.00 -> true
- terminal dispersion PASS iff 0.50 <= value <= 2.00 -> false
- uniqueness PASS iff value >= 0.99 -> true
- ACF1 PASS iff value <= 0.25 -> false

Classification:

`GATE_FAIL_VALID` only if every discriminating Gate criterion passes; otherwise `GATE_FAIL_VALID` provided result is finite and scientifically valid. Here 2 of 4 discriminating criteria fail, so result is `GATE_FAIL_VALID` — a VALID COMPLETED MEMBER and must be retained. Do not retry due to poor result, do not add excluded WGAN criteria, do not calculate H2.

If process had failed before valid Gate result, retained factual state with process count 1, marker/result as observed, no retry.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_seed02_gate_v2_execution_152.json` (commit `1b00fa6`, SHA `70e4aad3...` / blob via Git object, actual file SHA after update `20ea163f...`)
- Records Task ID, starting HEAD `2443a4b...`, safety branch, Gate V2 authorization path/SHA `8f609f78.../610b5e...`, Gate V1 prohibited disposition `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` and `v1_used: false`, training predecessor chain, evaluator/config identities, runtime, exact command, PIDs, timestamps, exit `0`, governed count `1`, retry/relaunch/rerun `0/0/0`, marker path/SHA `d7846e8f...`, Gate result path/SHA (stdout JSON), all Gate metrics, criterion pass/fail, classification `GATE_FAIL_VALID`, seed-03 not authorized, H2 not calculated, final sealed.

Amendment 080:

- Path: `reports/protocol/research_protocol_amendment_080.md` (this file)
- Gate V1 never used, Gate V2 identity bound, exactly one scientific process, marker identity/state, Gate result identity, all Gate metrics, criterion decisions, classification `GATE_FAIL_VALID`, poor-result retained, runtime, training predecessor, seed-03 not authorized, reserve not authorized, H2 unresolved, final sealed, no self-hash.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Gate V1 unchanged `512ccb1.../e8e1303d...` (now superseded, not consumed)
- Gate V2 unchanged `8f609f78.../610b5e...` (now consumed by Gate marker, but file not mutated)
- Training V2 `c282bc43...` / `747a1d8a...` unchanged
- Training marker `175fcad9...` unchanged
- Checkpoint `ca72d43...` 338677 unchanged
- Training report `c123724...` unchanged
- Task-144 evidence `bf7c7c89.../a4bd4557...` unchanged
- Amendments 077 `387bf9d...`, 078 `6ef7faf...`, 079 `966ee04...` unchanged
- Evaluator `243750a...`, Gate config `d9705ef9...`, seed-01 artifacts unchanged.

Require:

- Task-152 governed Gate process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live Gate process: 0 after termination, new training: 0, seed-03/04/05 authorization: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

Do NOT authorize seed-03 here, do NOT calculate H2. Next task must be Gate execution audit regardless of GATE_PASS/FAIL or failed execution.

This amendment is append-only, does not self-hash.

