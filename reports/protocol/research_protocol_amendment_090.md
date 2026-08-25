# Amendment 090 — V5 WGAN Seed-05 Gate-v2 Scientific Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-SEED-05-GATE-V2-EXECUTION-175`
Risk: `R5`
Branch: `main`
Starting HEAD: `d2f02b61f4fe529af2256ddc8b201593323417c9`
Prerequisite: `NM-R4-V5-WGAN-SEED-05-GATE-V2-AUTHORIZATION-AUDIT-174` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed05-gate-execution-d2f02b6` at `d2f02b61f4fe529af2256ddc8b201593323417c9`
Gate authorization: `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-05-gate-v2-v1.json` (canonical `d34445eff07b59a8654bdef0ae016e06714c1d8170792f760ecd9d958e3fd570`, raw `14b0d2db50a45522d81a61f1feb5381c02c8e34cd8df7a1c82db7ad6d25eed15`, blob `a3dc095b63df7de320d4cb35dfaf666cdea92de3`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed05_gate_v2_execution_175.json` (commit `fa7d4616c2832420ce83b3a69639c1d0628f8c94`, canonical `e4f8c8941795ea18a1561634981e82be84a292c8e843485b6b8021913512c0cc`, blob `a22ef8f23f899019dcc1c23e6cd1846026d16932`, raw same)
Training predecessor: checkpoint `data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt` (`4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d` 338677 32 tensors finite, selected 71 / 3.2245595973856656), training report `8e58a6150ba19764194c4e65fb936e020288d2458cba33460f3be2079267505c` (final 111 stopped_early true), Task-171 evidence canonical `2d2c0baa0ed886f7c4ca018c35bcbf4325c2b43a4b96594299e95e06823b80ae` blob `8b5c9b45c72fe5c3fc8c5629694096e92391ef01` raw `921eb5ad63c8e8c2ea2b7151e1ece4d80b9ccf27388fd06de78728f8c0106e34`, Amendment 088 `3fa52ebfca6aeeb9fbeac24430e89bc96618e5f53fcb3424a20db9abb3007c33 / 02fd05447b4e17f210ce46afa9bc80bb07280efd`
Campaign state at launch: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-05 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED`, valid primary members `3`, attempts consumed `5`, H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA Gate-v2 evaluation for `wgan-seed-05` via the audited Gate authorization. It does not authorize training, reserve, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `d2f02b61f4fe529af2256ddc8b201593323417c9`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed05-gate-execution-d2f02b6`.
- Gate authorization canonical `d34445eff07b59a8654bdef0ae016e06714c1d8170792f760ecd9d958e3fd570` (raw `14b0d2db50a45522d81a61f1feb5381c02c8e34cd8df7a1c82db7ad6d25eed15`) blob `a3dc095b63df7de320d4cb35dfaf666cdea92de3`, filtered worktree == HEAD, recursive 3 objects, 54 keys, duplicate 0.
- Checkpoint `4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d` 338677 finite true, training report `8e58a615...`, Task-171 evidence canonical `2d2c0baa...` / raw `921eb5...` blob `8b5c9b45...`, Amendment 088 `3fa52e.../02fd054...` all preserved.
- Gate evaluator canonical `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9` blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config canonical `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625` blob `d9705ef9a11da3e21760015bb2a27fa408018bb5`.
- Runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / deterministic true, CPU fallback PROHIBITED).
- Evaluation seed `8283`, bootstrap `8801`, generated `1024`, bootstrap `1024`, horizon `63`, block `22`, lags `1,2,3,5,10,20`.
- Scientific contract: variance ratio [0.50,2.00] PASS, terminal-dispersion [0.50,2.00] PASS, uniqueness >=0.99 PASS, ACF1 <=0.25 PASS, drift/diffusion EXCLUDED, report-only diagnostics unchanged.
- Preexisting Gate marker: absent (`reports/research/wgan_gate_runs/wgan-seed-05/gate-v2-execution-175/execution_started.json` absent).
- Preexisting Gate result: absent (dedicated gate_result.json not required; evaluator prints to stdout by design).
- Live Gate process: absent.
- Prelaunch governed Gate process count: 0.
- Parser verified: `--member-id`, `--checkpoint`, `--checkpoint-sha256`, `--authorization`, `--execute` required flags present; exact command derived from source and precedent without dry-run.

Authorization parsed SAFE validation PASS (member `wgan-seed-05`, checkpoint `4a728a...`, Gate evaluator `243750a...`, Gate config `8e70ad...`, runtime `17e3bb52...`, max 1 Gate true).

## Exactly one Gate process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_gate_evaluator --member-id wgan-seed-05 --checkpoint data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt --checkpoint-sha256 4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d --authorization reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-05-gate-v2-v1.json --execute`

Launch in background from outset via hub `wgan-gate-seed05`:

- Launcher PID: `52656` (hub wgan-gate-seed05 wrapper).
- Wrapper PID: `52656`.
- Python PID: `52656` (same; direct exec) / evaluator internal PID `39972` as recorded in marker process_id.
- Process/session: `wgan-gate-seed05:52656` (wrapper) with child `39972`.
- Start local: `2026-08-24T23:02:01.802904-04:00`.
- Start UTC: `2026-08-25T03:02:01.802904Z`.
- Launch mode: background.
- Governed Gate process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second Gate process may be created.

Do not invoke training, reserve, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process/session; no relaunch, no second CLI invocation.

Process record:

- Process/session ancestry: single hub wrapper 52656 with one evaluator child 39972 (exactly one scientific Gate process).
- End local: `2026-08-25T03:02:11.330229-04:00` (hub exit).
- End UTC: `2026-08-25T03:02:11.330229Z`.
- Wall-clock duration: `9` seconds (hub uptime 9.5s).
- Exit code: `0` (SUCCESS).
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-175/stdout.log` — bytes `3142`, SHA `5b8c71251f5abbc30f57c4a8f46c473ebe023ac633d2628af079a94fb086f069` (canonical original stdout JSON, classification GATE_FAIL_VALID).
- Stderr path: `.agent-memory/task-175/stderr.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty).
- After termination, read-only inspection:

Gate marker:

- Path: `reports/research/wgan_gate_runs/wgan-seed-05/gate-v2-execution-175/execution_started.json`
- SHA: `31eac04cfc5abf05ffbf667b196e86a66d1f7171bdf702ecedfe1495df513fbe` (2013 bytes)
- Count: 1 (before 0 -> after 1)
- Raw fields: schema_version `structured-vol-v5-wgan-gate-execution-start-v1`, member_id `wgan-seed-05`, gate_task_id `NM-R5-V5-WGAN-SEED-05-GATE-V2-EXECUTION-175`, authorization `wgan-seed-05-gate-v2-v1.json` (d34445.../a3dc09... raw 14b0d2...), checkpoint `4a728a...`, evaluation_seed `8283`, bootstrap `8801`, evaluator `243750a...`, Gate config `8e70ad.../d9705ef9...`, runtime `17e3bb52...`, process_id `39972`, timestamp_utc `2026-08-25T03:02:02.882672+00:00`
- Technical entitlement consumed: `CONSUMED_BY_GATE_MARKER`.

Gate result persistence contract:

- Current audited evaluator prints the canonical successful Gate result JSON to stdout (`print(json.dumps(result, sort_keys=True))` in wgan_gate_evaluator.py line 1056) and does NOT persist a dedicated `gate_result.json` file. This is intentional by design (verified via source read-only: no `open(..., "w")` for gate_result.json, only marker creation). Therefore absence of `reports/research/wgan_gate_runs/wgan-seed-05/gate-v2-execution-175/gate_result.json` is EXPECTED_BY_CURRENT_EVALUATOR_CONTRACT, not MISSING_EXPECTED_SCIENTIFIC_ARTIFACT.
- Original stdout verbatim preserved under `.agent-memory/task-175/stdout.log` (3142 bytes, SHA `5b8c71251f5abbc30f57c4a8f46c473ebe023ac633d2628af079a94fb086f069`) – this IS the canonical Gate result.
- No synthetic gate_result.json created; no regeneration after termination.

No overwrite, regeneration, repair, or rerun.

## Verification of numerical result and classification

Process exited with `0` and produced a valid finite canonical stdout JSON.

Persisted original stdout JSON extracted (from `.agent-memory/task-175/stdout.log`):

- evaluation seed: `8283` PASS
- bootstrap seed: `8801` PASS
- generated: `1024` PASS
- bootstrap: `1024` PASS
- horizon: `63` PASS
- block: `22` PASS
- variance ratio: `973.9974799562466` threshold [0.50,2.00] => FAIL (false)
- terminal-dispersion ratio: `31.176306283804113` threshold [0.50,2.00] => FAIL (false)
- path uniqueness: `1.0` threshold >=0.99 => PASS (true)
- ACF1 absolute error: `0.9726028384324048` (0.907...-(-0.065...)) threshold <=0.25 => FAIL (false)
- drift/diffusion: `EXCLUDED / NOT_APPLICABLE`
- All four required Gate criteria reapplied independently: variance FAIL, terminal FAIL, uniqueness PASS, ACF1 FAIL => at least one fails
- Report-only diagnostics:
  - normalized terminal Wasserstein: `214.82030603413176`
  - raw ACF RMSE: `0.6878903324024522`
  - raw ACF max: `0.9726028384324048`
  - raw ACF by lag: real `{"1":-0.065..., "2":-0.032..., "3":-0.134..., "5":0.012..., "10":0.003..., "20":-0.020...}` generated `{"1":0.907..., "2":0.817..., "3":0.730..., "5":0.566..., "10":0.206..., "20":-0.289...}`
  - abs-return ACF: real `{"1":0.345..., "2":0.260..., "3":0.154..., "5":-0.034..., "10":0.034..., "20":-0.037...}` generated `{"1":0.966..., "2":0.927..., "3":0.882..., "5":0.777..., "10":0.443..., "20":-0.347...}`
  - squared-return ACF: real `{"1":0.308..., "2":0.201..., "3":0.051..., "5":-0.045..., "10":-0.004..., "20":0.025...}` generated `{"1":0.934..., "2":0.866..., "3":0.797..., "5":0.655..., "10":0.299..., "20":-0.294...}`
  - conditional variance log correlation: `-0.05935776710918978`
  - All finite where expected, no fabricated mode-collapse, no drift/diffusion applied, final test not accessed.

Classification per source:

`GATE_FAIL_VALID` (governance-valid, completed, finite/numerical, but 3 of 4 required criteria fail)

A valid Gate result does NOT yet promote seed-05 until Task 176 audit; seed-05 remains `NOT_YET_COMPLETED_PENDING_GATE_AUDIT`.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_seed05_gate_v2_execution_175.json` (commit `fa7d4616c2832420ce83b3a69639c1d0628f8c94`, canonical `e4f8c894...` / raw same, blob `a22ef8f23f899019dcc1c23e6cd1846026d16932`, raw same)
- Records Task 175, starting HEAD `d2f02b61...`, safety branch `safety/pre-wgan-seed05-gate-execution-d2f02b6`, Gate authorization canonical `d34445...` raw `14b0d2...` blob `a3dc09...`, training predecessor, checkpoint `4a728a...`, evaluator `b7c7cd.../243750a...`, implementation/config/runtime, seeds/sample sizes, exact command, process/session PIDs 52656/39972, governed count 1, marker `31eac04c...`, canonical original stdout `5b8c7125...` 3142 bytes, all four Gate metrics independently derived PASS/FAIL as above, report-only diagnostics, Gate classification `GATE_FAIL_VALID`, reserve NOT AUTHORIZED, H2 NOT CALCULATED, final SEALED.

Amendment 090:

- Path: `reports/protocol/research_protocol_amendment_090.md` (this file)
- Records same load-bearing facts, no self-hash, does not modify Amendments 074–089.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Gate authorization unchanged `d34445.../a3dc09...` raw `14b0d2...`
- Checkpoint unchanged `4a728a...` 338677
- Training report unchanged `8e58a615...`
- Gate evaluator `243750a...`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad.../d9705ef9...` unchanged
- Seed-01/02/03/04 history unchanged (seed-01 `VALID_COMPLETED_MEMBER`, seed-02 `VALID_COMPLETED_MEMBER`, seed-03 `NONFINITE_TRAINING_FAILURE`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` via Task-167 evidence `f4d59034.../b0f95764...` committed `638e385e...` raw `f4d590...`, Amendment 086 `5e395a55.../c13bbe78...`, Gate marker `31eac04c...` stdout `5b8c7125...`)
- No Gate artifacts overwritten besides the one new marker.

Require:

- Task-175 governed Gate process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live Gate process: 0 after termination, training: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

If Gate had been PASS:

`GATE_PASS_VALID`

would have been classified; here `GATE_FAIL_VALID` is the valid numerical failure, not a technical failure. Do not increment `VALID PRIMARY MEMBERS COMPLETED` until Task-176 audit confirms Gate.

This amendment is append-only, does not self-hash.

