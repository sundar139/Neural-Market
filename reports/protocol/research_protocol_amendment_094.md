# Amendment 094 — V5 WGAN Reserve-J01 Gate-v2 Scientific Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-RESERVE-J01-GATE-V2-EXECUTION-183`
Risk: `R5`
Branch: `main`
Starting HEAD: `794b1bb1e47ea44579e31ee661b26f968869340c`
Prerequisite: `NM-R4-V5-WGAN-RESERVE-J01-GATE-V2-AUTHORIZATION-AUDIT-182` — `VALIDATED`
Safety branch: `safety/pre-wgan-reserve-j01-gate-execution-794b1bb` at `794b1bb1e47ea44579e31ee661b26f968869340c`
Gate authorization: `reports/research/authorizations/structured_vol_v5_wgan_gate/reserve-wgan-j01-gate-v2-v1.json` (canonical `b995f1c3ea15dd9d8f7b568e13e77174d5e240a9ec1c8dd3d44d1c6597115030`, raw `202c6fcebddcaa6e5e4fba88efcc6bb76b0ca5088981f8d904c9d2aa622cfab9`, blob `c45df0c4cc8b8397aeba3dfcac9a4943954af618`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_reserve_j01_gate_v2_execution_183.json` (commit `231c2921cd01b6350020b933215360e71832267f`, canonical `e4ee157b05501b4597f1c9a4eb51e708da1b55dee8002209f8ae7dcb842fd2c5`, blob `c960471f23336588bfe8fc56755b57eecadf9abd`, raw same)
Training predecessor: checkpoint `data/processed/research/model/wgan-comparator/reserve-wgan-j01/f7507c38d9e3f204/checkpoint.pt` (`ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef` 338677 32 tensors finite, selected 24 / 2.18908573311753), training marker `c9012cde8cc110ebc9b8a732cc130296036c7ee16a3d55a694157fc83d45f659`, training report `0ab246ce6315f917512e0c89faf1d05534f35041b86d2eeaf35db2a31cc94471` (final 64 stopped_early true), Task-179 evidence canonical `d7d55c0ac45f71b68937c7a44bc8c334bfdc48b3de8bbec369ed212324a81a5b` blob `fb666a399d2549788dc9db232b9858b7de9f1748` raw `53bca723...`, Amendment 092 canonical `9adf86cf17e09c57ba5301caf48fecafd9a2ed8f4ea72a737d8f247f1e089e5a` blob `daf8810cf7c3fac63cf6eac01642e5e932b80008`
Campaign state at launch: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, reserve-j01 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED / NOT_YET_COMPLETED_PENDING_GATE` (4 valid, 5 attempts, reserve required), H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`, canonical reserve member `reserve-wgan-j01` (preregistration `reserve-wgan-j01` order 1, source `reserve-wgan-j01`)

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA Gate-v2 evaluation for `reserve-wgan-j01` via the audited Gate authorization. It does not authorize training rerun, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `794b1bb1e47ea44579e31ee661b26f968869340c`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-reserve-j01-gate-execution-794b1bb`.
- Gate authorization canonical `b995f1c3ea15dd9d8f7b568e13e77174d5e240a9ec1c8dd3d44d1c6597115030` (raw `202c6fcebddcaa6e5e4fba88efcc6bb76b0ca5088981f8d904c9d2aa622cfab9`) blob `c45df0c4cc8b8397aeba3dfcac9a4943954af618`, filtered worktree == HEAD, recursive 3 objects, 55 keys (reserve_purpose extra), duplicate 0.
- Checkpoint `ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef` 338677 finite true, training marker `c9012cde...`, training report `0ab246ce...`, Task-179 evidence canonical `d7d55c0a...` raw `53bca723...` blob `fb666a...`, Amendment 092 `9adf86.../daf881...` all preserved.
- Gate evaluator canonical `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9` blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config canonical `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625` blob `d9705ef9a11da3e21760015bb2a27fa408018bb5`.
- Runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / deterministic true, CPU fallback PROHIBITED).
- Evaluation seed `8283`, bootstrap `8801`, generated `1024`, bootstrap `1024`, horizon `63`, block `22`, lags `1,2,3,5,10,20`.
- Scientific contract: variance ratio [0.50,2.00] PASS, terminal-dispersion [0.50,2.00] PASS, uniqueness >=0.99 PASS, ACF1 <=0.25 PASS, drift/diffusion EXCLUDED, report-only diagnostics unchanged, reserve purpose `replace invalid primary seed-03 and supply fifth valid WGAN member`.
- Preexisting Gate marker: absent (`reports/research/wgan_gate_runs/reserve-wgan-j01/gate-v2-execution-183/execution_started.json` absent).
- Preexisting Gate result: absent (dedicated gate_result.json not required; evaluator prints to stdout by design).
- Live Gate process: absent.
- Prelaunch governed Gate process count: 0.
- Parser verified: `--member-id`, `--checkpoint`, `--checkpoint-sha256`, `--authorization`, `--execute` required flags present; exact command derived from source and precedent without dry-run.

Authorization parsed SAFE validation PASS (member `reserve-wgan-j01`, role `RESERVE`, checkpoint `ccc5b913...`, Gate evaluator `243750a...`, Gate config `8e70ad...`, runtime `17e3bb52...`, max 1 Gate true).

## Exactly one reserve Gate process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_gate_evaluator --member-id reserve-wgan-j01 --checkpoint data/processed/research/model/wgan-comparator/reserve-wgan-j01/f7507c38d9e3f204/checkpoint.pt --checkpoint-sha256 ccc5b913a5a129dd0d62738949fc5a7ab28ee20c262d3b31cf87ba13346840ef --authorization reports/research/authorizations/structured_vol_v5_wgan_gate/reserve-wgan-j01-gate-v2-v1.json --execute`

Launch in background from outset via hub `reserve-wgan-j01-gate`:

- Launcher PID: `41300` (hub reserve-wgan-j01-gate wrapper).
- Wrapper PID: `41300`.
- Python PID: `41300` (same; direct exec) / evaluator internal PID `54336` as recorded in marker process_id.
- Process/session: `reserve-wgan-j01-gate:41300` (wrapper) with child `54336`.
- Start local: `2026-08-25T00:19:24.060775-04:00`.
- Start UTC: `2026-08-25T04:19:24.060775Z`.
- Launch mode: background.
- Governed Gate process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second Gate process may be created.

Do not invoke training, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process/session; no relaunch, no second CLI invocation.

Process record:

- Process/session ancestry: single hub wrapper 41300 with one evaluator child 54336 (exactly one scientific Gate process).
- End local: `2026-08-25T04:19:35.060775Z` (hub exit).
- End UTC: `2026-08-25T04:19:35.060775Z`.
- Wall-clock duration: `10` seconds (hub uptime 10.5s).
- Exit code: `0` (SUCCESS).
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-183/stdout.log` — bytes `2645`, SHA `2d75f9c3c715394d59793adae57d8f1625ccffd1356442ffe86ff80cb6a056c6` (canonical original stdout JSON, classification GATE_FAIL_VALID).
- Stderr path: `.agent-memory/task-183/stderr.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty).
- After termination, read-only inspection:

Gate marker:

- Path: `reports/research/wgan_gate_runs/reserve-wgan-j01/gate-v2-execution-183/execution_started.json`
- SHA: `1582fa442104703b2d8e690c86da73f0081b0beff7aa976c70ecb8ae95ff1462` (2042 bytes, blob 693bb1... untracked)
- Count: 1 (before 0 -> after 1)
- Raw fields: schema_version `structured-vol-v5-wgan-gate-execution-start-v1`, member_id `reserve-wgan-j01`, gate_task_id `NM-R5-V5-WGAN-RESERVE-J01-GATE-V2-EXECUTION-183`, authorization `reserve-wgan-j01-gate-v2-v1.json` (b995f1.../c45df0... raw 202c6f...), checkpoint `ccc5b913...`, evaluation_seed `8283`, bootstrap `8801`, evaluator `243750a...`, Gate config `8e70ad.../d9705ef9...`, runtime `17e3bb52...`, process_id `54336`, timestamp_utc `2026-08-25T04:19:24.713924+00:00`
- Technical entitlement consumed: `CONSUMED_BY_GATE_MARKER`.

Gate result persistence contract:

- Current audited evaluator prints the canonical successful Gate result JSON to stdout (`print(json.dumps(result, sort_keys=True))` in wgan_gate_evaluator.py line 1056) and does NOT persist a dedicated `gate_result.json` file. This is intentional by design (verified via source read-only: no `open(..., "w")` for gate_result.json, only marker creation). Therefore absence of `reports/research/wgan_gate_runs/reserve-wgan-j01/gate-v2-execution-183/gate_result.json` is EXPECTED_BY_CURRENT_EVALUATOR_CONTRACT, not MISSING_EXPECTED_SCIENTIFIC_ARTIFACT.
- Original stdout verbatim preserved under `.agent-memory/task-183/stdout.log` (2645 bytes, SHA `2d75f9c3c715394d59793adae57d8f1625ccffd1356442ffe86ff80cb6a056c6`) – this IS the canonical Gate result.
- No synthetic gate_result.json created; no regeneration after termination.

No overwrite, regeneration, repair, or rerun.

## Verification of numerical result and classification

Process exited with `0` and produced a valid finite canonical stdout JSON.

Persisted original stdout JSON extracted (from `.agent-memory/task-183/stdout.log`):

- evaluation seed: `8283` PASS
- bootstrap seed: `8801` PASS
- generated: `1024` PASS
- bootstrap: `1024` PASS
- horizon: `63` PASS
- block: `22` PASS
- variance ratio: `3.256356970357127` threshold [0.50,2.00] => FAIL (false)
- terminal-dispersion ratio: `20.025066044813133` threshold [0.50,2.00] => FAIL (false)
- path uniqueness: `1.0` threshold >=0.99 => PASS (true)
- ACF1 absolute error: `1.046553687222934` threshold <=0.25 => FAIL (false)
- drift/diffusion: `EXCLUDED / NOT_APPLICABLE`
- All four required Gate criteria reapplied independently: variance FAIL, terminal FAIL, uniqueness PASS, ACF1 FAIL => at least one fails
- Report-only diagnostics:
  - normalized terminal Wasserstein: `317.27597811369907`
  - raw ACF RMSE: `0.928570344590513`
  - raw ACF max: `1.078839868093538`
  - raw ACF by lag: real `{"1":-0.065..., "2":-0.032..., "3":-0.134..., "5":0.012..., "10":0.003..., "20":-0.020...}` generated `{"1":0.981..., "2":0.962..., "3":0.944..., "5":0.907..., "10":0.819..., "20":0.655...}`
  - abs-return ACF: real `{"1":0.345..., "2":0.260..., "3":0.154..., "5":-0.034..., "10":0.034..., "20":-0.037...}` generated `{"1":0.981..., "2":0.962..., "3":0.944..., "5":0.907..., "10":0.819..., "20":0.655...}`
  - squared-return ACF: real `{"1":0.308..., "2":0.201..., "3":0.051..., "5":-0.045..., "10":-0.004..., "20":0.025...}` generated `{"1":0.981..., "2":0.962..., "3":0.944..., "5":0.907..., "10":0.819..., "20":0.656...}`
  - conditional variance log correlation: `0.1614067491766828`
  - All finite where expected, no fabricated mode-collapse, no drift/diffusion applied, final test not accessed.

Classification per source:

`GATE_FAIL_VALID` (governance-valid, completed, finite/numerical, but 3 of 4 required criteria fail)

A valid Gate result does NOT yet promote reserve-j01 until Task 184 audit; reserve-j01 remains `NOT_YET_COMPLETED_PENDING_GATE_AUDIT`.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_reserve_j01_gate_v2_execution_183.json` (commit `231c2921cd01b6350020b933215360e71832267f`, canonical `e4ee157b05501b4597f1c9a4eb51e708da1b55dee8002209f8ae7dcb842fd2c5` / raw same, blob `c960471f23336588bfe8fc56755b57eecadf9abd`, raw same)
- Records Task 183, starting HEAD `794b1bb...`, safety branch `safety/pre-wgan-reserve-j01-gate-execution-794b1bb`, Gate authorization canonical `b995f1c3...` raw `202c6f...` blob `c45df0c4...`, training predecessor, checkpoint `ccc5b913...`, evaluator `b7c7cd.../243750a...`, implementation/config/runtime, seeds/sample sizes, exact command, process/session PIDs 41300/54336, governed count 1, marker `1582fa44...`, canonical original stdout `2d75f9c3...` 2645 bytes, all four Gate metrics independently derived PASS/FAIL as above, report-only diagnostics, Gate classification `GATE_FAIL_VALID`, reserve NOT AUTHORIZED? Actually reserve purpose is training, Gate is for reserve, but evidence records reserve purpose and Gate classification, H2 NOT CALCULATED, final SEALED.

Amendment 094:

- Path: `reports/protocol/research_protocol_amendment_094.md` (this file)
- Records same load-bearing facts, no self-hash, does not modify Amendments 074–093.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Gate authorization unchanged `b995f1c3.../c45df0c4...` raw `202c6f...`
- Reserve checkpoint unchanged `ccc5b913...` 338677
- Reserve training report unchanged `0ab246ce...`
- Gate evaluator `243750a...`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad.../d9705ef9...` unchanged
- Seed-01/02/03/04/05 history unchanged (seed-01 `VALID_COMPLETED_MEMBER`, seed-02 `VALID_COMPLETED_MEMBER`, seed-03 `NONFINITE_TRAINING_FAILURE`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` via Task-175 evidence `9e902d50.../a22ef8f2...` marker `31eac04c...` stdout `5b8c7125...`, reserve training `VALID_EXECUTION_NO_GATE_RESULT` via Task-179 evidence `d7d55c0a.../fb666a...` raw `53bca723...`)

Require:

- Task-183 governed Gate process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live Gate process: 0 after termination, training: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

If Gate had been PASS:

`GATE_PASS_VALID`

would have been classified; here `GATE_FAIL_VALID` is the valid numerical failure, not a technical failure. Do not increment `VALID WGAN MEMBERS` until Task-184 audit confirms Gate.

This amendment is append-only, does not self-hash.

