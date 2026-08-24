# Amendment 086 — V5 WGAN Seed-04 Gate-v2 Scientific Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-SEED-04-GATE-V2-EXECUTION-167`
Risk: `R5`
Branch: `main`
Starting HEAD: `8c1d9090ee04044447f002bea49211d6e05cf50b`
Prerequisite: `NM-R4-V5-WGAN-SEED-04-GATE-V2-AUTHORIZATION-AUDIT-166` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed04-gate-execution-8c1d909` at `8c1d9090ee04044447f002bea49211d6e05cf50b`
Gate authorization: `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-04-gate-v2-v1.json` (`9d845c2515684f0fc1cd2b97e5005f0df3227a3bffa30be3e9eb150039f68320`, blob `4eb418595d3ef3dbf27b85ccbdca775986a353a7`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed04_gate_v2_execution_167.json` (commit `b7896d65c10ed8a3ae60b3f2bda091e7d9a794d8`)
Training predecessor: checkpoint `data/processed/research/model/wgan-comparator/wgan-seed-04/6009789e9e8645df/checkpoint.pt` (`2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6` 338677 32 tensors finite, selected 39 / 1.34198...), training report `46c3bcd32f2738054a1de595689ec02e5312395c4a82bfeba207369b328d4871` (final 79 stopped_early true), Task-163 evidence `19d0e831ec63897d43c2c6f393b237ec0fe40e47260f06a2d7db0ade1314d13f / 934c3ba3d1d52374214c0de311909725c2d35c5d`, Amendment 084 `e883f72df62577c69a47cabc95baf628171dffb63f56da2a3f7457eb78ff28a4 / e4831b7e049c30b1c4168863c3113d891523f4ac`
Campaign state at launch: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 training `VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED`, valid primary members `2`, attempts consumed `4`, H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA Gate-v2 evaluation for `wgan-seed-04` via the audited Gate authorization. It does not authorize training, seed-05, reserve, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `8c1d9090ee04044447f002bea49211d6e05cf50b`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed04-gate-execution-8c1d909`.
- Gate authorization SHA: `9d845c2515684f0fc1cd2b97e5005f0df3227a3bffa30be3e9eb150039f68320`, blob `4eb418595d3ef3dbf27b85ccbdca775986a353a7`, filtered worktree == HEAD, recursive 3 objects, 54 keys, duplicate 0.
- Checkpoint `2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6` 338677 finite true, training report `46c3bcd3...`, Task-163 evidence `19d0e831.../934c3ba3...`, Amendment 084 `e883f72d.../e4831b7e...` all preserved.
- Gate evaluator `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9 / 243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625 / d9705ef9a11da3e21760015bb2a27fa408018bb5`.
- Runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / deterministic true, CPU fallback PROHIBITED).
- Evaluation seed `8283`, bootstrap `8801`, generated `1024`, bootstrap `1024`, horizon `63`, block `22`, lags `1,2,3,5,10,20`.
- Scientific contract: variance ratio [0.50,2.00] PASS, terminal-dispersion [0.50,2.00] PASS, uniqueness >=0.99 PASS, ACF1 <=0.25 PASS, drift/diffusion EXCLUDED, report-only diagnostics unchanged.
- Preexisting Gate marker: absent (`reports/research/wgan_gate_runs/wgan-seed-04/gate-v2-execution-167/execution_started.json` absent).
- Preexisting Gate result: absent.
- Live Gate process: absent.
- Prelaunch governed Gate process count: 0.
- Parser verified: `--member-id`, `--checkpoint`, `--checkpoint-sha256`, `--authorization`, `--execute` required flags present; exact command derived from source and precedent without dry-run.

Authorization parsed SAFE validation PASS (member `wgan-seed-04`, checkpoint `2e8b0f4c...`, Gate evaluator `243750a...`, Gate config `8e70ad...`, runtime `17e3bb52...`, max 1 Gate true).

## Exactly one Gate process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_gate_evaluator --member-id wgan-seed-04 --checkpoint data/processed/research/model/wgan-comparator/wgan-seed-04/6009789e9e8645df/checkpoint.pt --checkpoint-sha256 2e8b0f4c827ad2693138b6409073dd761318b5bd320f3046c597f843bc0e7ee6 --authorization reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-04-gate-v2-v1.json --execute`

Launch in background from outset via hub `wgan-gate-seed04`:

- Launcher PID: `20772` (hub wgan-gate-seed04 wrapper).
- Wrapper PID: `20772`.
- Python PID: `20772` (same; direct exec).
- Process/session: `wgan-gate-seed04:20772`.
- Start local: `2026-08-24T18:13:16.045086-04:00`.
- Start UTC: `2026-08-24T22:13:16.045086Z`.
- Launch mode: background.
- Governed Gate process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second Gate process may be created.

Do not invoke training, seed-05, reserve, H2, or final-test.

## Observation to termination

Observed only the original process/session; no relaunch, no second CLI invocation.

Process record:

- Process/session ancestry: single Python process via hub `wgan-gate-seed04`.
- End local: `2026-08-24T18:13:24.661313-04:00` (marker timestamp) / `2026-08-24T18:13:24.045086-04:00` (hub exit).
- End UTC: `2026-08-24T22:13:24.661313Z`.
- Wall-clock duration: `8` seconds (hub uptime 8.4s).
- Exit code: `0` (SUCCESS).
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-167/stdout.log` — bytes `3878`, SHA `2088cac717771894f4b06c9a3b326c7df13a40d0629934dc18e84c3e4aa73346` (gate result JSON, classification GATE_FAIL_VALID).
- Stderr path: `.agent-memory/task-167/stderr.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty).
- After termination, read-only inspection:

Gate marker:

- Path: `reports/research/wgan_gate_runs/wgan-seed-04/gate-v2-execution-167/execution_started.json`
- SHA: `6bd290097d304cc49adfc944b0b275a711b51f1e69ef72e306f123efd481de41` (2013 bytes)
- Count: 1 (before 0 -> after 1)
- Authorization: `wgan-seed-04-gate-v2-v1.json` blob `4eb41859...`
- Member: `wgan-seed-04`, checkpoint `2e8b0f4c...`, runtime `17e3bb52...`
- Process ID: `21676` (evaluator internal), timestamp `2026-08-24T22:13:15.661313+00:00`
- Technical entitlement consumed: `CONSUMED_BY_GATE_MARKER`

Gate result:

- Path: `.agent-memory/task-167/stdout.log` (also available as hub stdout JSON; no separate file under wgan_gate_runs, count 0 at that path, at most 1 allowed)
- SHA: `2088cac717771894f4b06c9a3b326c7df13a40d0629934dc18e84c3e4aa73346` (3878 bytes)
- Classification: `GATE_FAIL_VALID`

No overwrite, regeneration, repair, or rerun.

## Verification of numerical Gate result and classification

Process exited with `0` and produced a valid finite Gate result.

Persisted result (from stdout JSON) extracted:

- variance ratio: `0.7829149014858177` criterion PASS (0.50-2.00)
- variance PASS: `true`
- terminal-dispersion ratio: `9.463095834611345` criterion FAIL (outside 0.50-2.00)
- terminal PASS: `false`
- path uniqueness: `1.0` criterion PASS (>=0.99)
- uniqueness PASS: `true`
- ACF1 absolute error: `1.0398916023687304` (real -0.065..., generated 0.974..., diff 1.039) criterion FAIL (<=0.25)
- ACF1 PASS: `false`
- drift/diffusion: `EXCLUDED / NOT_APPLICABLE` (report shows not evaluated)
- evaluation seed: `8283`, bootstrap `8801`, generated `1024`, bootstrap `1024`, horizon `63`, block `22` all PASS
- Report-only diagnostics:
  - normalized terminal Wasserstein: `48.09288306767447`
  - raw ACF RMSE: `0.8980517183225293`
  - raw ACF max error: `1.0597068045661677`
  - abs-return ACF real `0.345...,0.260...,0.154..., -0.034...,0.034..., -0.037...` generated `0.974...,0.949...,0.925...,0.877...,0.763...,0.566...`
  - squared-return ACF real `0.308...,0.201...,0.051..., -0.045..., -0.004...,0.025...` generated `0.974...,0.950...,0.926...,0.878...,0.765...,0.568...`
  - conditional variance log correlation: `0.07797168514736223`
  - fabricated: `0`

Classification per source:

`GATE_FAIL_VALID` (governance-valid, completed, numerical, but 2 of 4 required criteria fail: terminal-dispersion and ACF1)

A valid GATE_FAIL_VALID means seed-04 remains `NOT_YET_COMPLETED_PENDING_GATE` until independent Task-168 audit; it does not count as VALID_COMPLETED_MEMBER.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_seed04_gate_v2_execution_167.json` (commit `b7896d65c10ed8a3ae60b3f2bda091e7d9a794d8`, SHA `f4d5903498387354ebe207bb931dc80ea0615d2bb271e3a5eae2256543437aec`, blob `b7896d65...`)
- Records Task ID, starting HEAD `8c1d9090...`, safety branch `safety/pre-wgan-seed04-gate-execution-8c1d909`, Gate authorization `9d845c25.../4eb41859...`, training authorization `e866e517.../de597cca...`, checkpoint `2e8b0f4c...` 338677, training report `46c3bcd3...`, Task-163 evidence `19d0e831.../934c3ba3...`, Amendment 084 `e883f72d.../e4831b7e...`, evaluator `243750a...`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad.../d9705ef9...`, runtime `17e3bb52...`, seeds 8283/8801 sample 1024/1024 horizon 63 block 22, exact command, launch/session PIDs 20772, timestamps, exit 0, wall 8s, governed count 1, marker `6bd29009...`, gate result `2088cac7...` 3878, metrics as above, classification `GATE_FAIL_VALID`, seed-05 not authorized, reserve not authorized, H2 not calculated, final sealed.

Amendment 086:

- Path: `reports/protocol/research_protocol_amendment_086.md` (this file)
- Records same load-bearing facts, no self-hash, does not modify Amendments 074–085.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Gate authorization unchanged `9d845c25.../4eb41859...`
- Checkpoint unchanged `2e8b0f4c...` 338677
- Training report unchanged `46c3bcd3...`
- Gate evaluator `243750a...`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad.../d9705ef9...` unchanged
- Seed-01/02/03 history unchanged (seed-01 `VALID_COMPLETED_MEMBER`, seed-02 `VALID_COMPLETED_MEMBER`, seed-03 `NONFINITE_TRAINING_FAILURE`)
- No Gate artifacts overwritten besides the one new marker.

Require:

- Task-167 Gate process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live Gate process: 0 after termination, training process: 0, seed-05 authorization: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

If Gate had been PASS:

`GATE_PASS_VALID`

would have been classified; here `GATE_FAIL_VALID` is the valid numerical failure, not a technical failure.

Do not increment `VALID PRIMARY MEMBERS COMPLETED` until Task-168 audit confirms Gate.

This amendment is append-only, does not self-hash.

