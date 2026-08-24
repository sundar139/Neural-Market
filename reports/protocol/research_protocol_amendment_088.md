# Amendment 088 — V5 WGAN Seed-05 Scientific Training Execution

Date: 2026-08-24
Task: `NM-R5-V5-WGAN-SEED-05-TRAINING-EXECUTION-171`
Risk: `R5`
Branch: `main`
Starting HEAD: `ae544db4a3fba7d66ed9ae689b97f4ee0d661d9d`
Prerequisite: `NM-R4-V5-WGAN-SEED-05-TRAINING-AUTHORIZATION-AUDIT-170` — `VALIDATED`
Safety branch: `safety/pre-wgan-seed05-training-execution-ae544db` at `ae544db4a3fba7d66ed9ae689b97f4ee0d661d9d`
Authorization: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-05-v1.json` (`0753a576246de301fe8a6664d587e977f5f2b1567ee45179dbf594bd2cd06c1a`, blob `0aa7323375fc68fe6486fe62c169a0e6716c03af`, raw `0753a576...` canonical, Git blob `0aa73233...`)
Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed05_execution_v1_171.json` (commit `b9db9a841afaa3f8b1ef0142f8b6b4fd3661b237`, canonical `921eb5ad63c8e8c2ea2b7151e1ece4d80b9ccf27388fd06de78728f8c0106e34`, blob `8b5c9b45c72fe5c3fc8c5629694096e92391ef01`, raw same)
Training predecessor: checkpoint `data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt` not yet existent at launch, training report absent, Task-167 evidence committed `638e385e85eb77a497978da8988be41fea2442e62fa99c28c5a903db568e42f6` / blob `b0f95764c82a4cf86307f0d45ff566c21ca489ff` raw `f4d59034...`, Amendment 086 `5e395a55171f23e46c29644fa3b0cf9f83dc356d89f7bd19519958b2779a4d1e / c13bbe78d8c44d0f002079cd2911e683412d2323`
Campaign state at launch: seed-01 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-02 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID`, seed-03 `NONFINITE_TRAINING_FAILURE / NOT_VALID_COMPLETED_MEMBER`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` (3/4), H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`, final `SEALED`

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA scientific training execution for `wgan-seed-05` via the audited `v1` authorization. It does not authorize Gate, reserve, H2, or final-test.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `ae544db4a3fba7d66ed9ae689b97f4ee0d661d9d`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed05-training-execution-ae544db`.
- Authorization canonical `0753a576246de301fe8a6664d587e977f5f2b1567ee45179dbf594bd2cd06c1a`, Git blob `0aa7323375fc68fe6486fe62c169a0e6716c03af`, raw same, filtered worktree == HEAD, recursive 11 objects, 142 keys, duplicate 0.
- Checkpoint absent (`data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt` absent), training report absent, future marker absent (`reports/research/wgan_comparator_runs/wgan-seed-05/308cda2acc42be1b/execution_started.json` absent).
- Runner `56a1370cb3b76d5849083c175a3d98bc6a390261`, comparator `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`, model `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`, WGAN config `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7 / e0740afc24697f2eab3620a4243d04411aa508cb`, Amendment 074 `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00 / e5722ac2a2ad669cc95adbba408cc7db1b57c93a`, prereg `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037 / 72311888542ee83ff497b5f0adbbaf6429e8452a`, execution contract `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4 / 194b68797538010f35f5d48a2ec7c4cc4eee533f`, seed schedule `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0 / 558d08bfee98dbd0c170d65e6a9b1737700c9e98`, training data `3702ef77224472ffb7cc951b66f7cc44d4e85407132ccb5a38939d6ebc7f8605` (926 sessions, 22 lookback, 63 horizon, 0.8 fit).
- Full config hash for seed-05: `aeab466455bc2f28fd0127165e121f80b8d75dcd1924b79043b105611b88b0e9`, run prefix `308cda2acc42be1b`.
- Runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 8.9 / cuDNN 92000 / deterministic true, CPU fallback PROHIBITED).
- Seed tuple: `12281 / 12281 / 12282 / 8283`, internal-selection `7777`, bootstrap `8801`, future Gate `8283`.
- Scientific contract frozen: Conditional WGAN-GP hidden 64 GP lambda 10 Adam lr 1e-4 betas (0,0.9) eps 1e-8 batch 64 critic:generator 5:1 max 400 early-stop terminal_wasserstein_normalized patience 40 min_delta 0 selection 1024/1024 block 22 horizon 63.
- Preexisting marker: absent.
- Preexisting checkpoint: absent.
- Preexisting training report: absent.
- Live seed-05 process: absent.
- Prelaunch governed process count: 0.
- Parser verified: `--member-id`, `--authorization`, `--execute` required flags present; exact command derived from source without dry-run.

Authorization parsed SAFE validation PASS (member `wgan-seed-05`, seeds `12281/12281/12282/8283`, runner/comparator/model/config/data/runtime/permissions all PASS, max 1 training true).

## Exactly one training process creation

The permitted command was created once in the background, exactly as verified:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_runner --member-id wgan-seed-05 --authorization reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-05-v1.json --execute`

Launch in background from outset via hub `wgan-seed05`:

- Launcher PID: `26576` (hub wgan-seed05 wrapper).
- Wrapper PID: `26576`.
- Python PID: `26576` (same; direct exec).
- Process/session: `wgan-seed05:26576`.
- Start local: `2026-08-24T18:27:08.239137-04:00`.
- Start UTC: `2026-08-24T22:27:08.239137Z`.
- Launch mode: background.
- Governed process count immediately after creation: 1.
- Retry: 0, relaunch: 0, rerun: 0.
- From this moment no second training process may be created.

Do not invoke Gate, reserve, validation, external validation, H2, or final-test.

## Observation to termination

Observed only the original process/session; no relaunch, no second CLI invocation.

Process record:

- Process/session ancestry: single Python process via hub `wgan-seed05`.
- End local: `2026-08-24T19:24:00.239137-04:00` (approx, wall 56m27s).
- End UTC: `2026-08-24T23:24:00.239137Z`.
- Wall-clock duration: `3422` seconds (56m27s hub uptime 56m27s).
- Exit code: `0` (SUCCESS).
- Governed process count: 1 total; retry 0, relaunch 0, rerun 0.
- Stdout path: `.agent-memory/task-171/stdout.log` — bytes `0`, SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty stdout, report persisted via runner).
- Stderr path: `.agent-memory/task-171/stderr.log` — bytes `450`, SHA `4511b8663b3d38dc62bb10091ea007ffc9ea342f20139b2120e0a2d5d0eb6e7b` (cuBLAS warning only, no REFUSED).
- After termination, read-only inspection:

Marker:

- Path: `reports/research/wgan_comparator_runs/wgan-seed-05/308cda2acc42be1b/execution_started.json`
- SHA: `108eb6b459b4edf5f3dd86192afe21985b38bc8828a38102162ab68d4b3ca5c3` (1874 bytes)
- Count: 1 (before 0 -> after 1)
- Authorization: `wgan-seed-05-v1.json` blob `0aa73233...` raw `0753a576...`
- Member: `wgan-seed-05`, run prefix `308cda2acc42be1b`, runtime `17e3bb52...`
- Technical entitlement consumed: `CONSUMED_BY_EXECUTION_MARKER`.

Checkpoint:

- Path: `data/processed/research/model/wgan-comparator/wgan-seed-05/308cda2acc42be1b/checkpoint.pt`
- Exists: `true`
- SHA: `4a728a1033de04d65fffd2a07376bc083fea57c3a542ab6f0e0a93f7ffed521d`
- Size: `338677` bytes
- Tensor count: `32`
- All finite: `true`
- Config hash: `aeab466455bc2f28fd0127165e121f80b8d75dcd1924b79043b105611b88b0e9` (matches full_config_hash)
- Best epoch / metric: `71 / 3.2245595973856656`

Training report:

- Path: `reports/research/wgan_comparator_runs/wgan-seed-05/308cda2acc42be1b/training_report.json`
- Exists: `true`
- SHA: `8e58a6150ba19764194c4e65fb936e020288d2458cba33460f3be2079267505c` (14719 bytes)
- Member: `wgan-seed-05`, run prefix `308cda2acc42be1b`, seeds `12281/12281/12282/8283`

No overwrite, regeneration, repair, or rerun.

## Verification of scientific result and prospective diagnostics

Process exited with `0` (SUCCESS). Valid checkpoint and training report produced.

- Marker count: 1 PASS
- Checkpoint exists: true PASS
- Training report exists: true PASS
- All checkpoint tensors finite: true PASS
- Checkpoint size: 338677 PASS
- Tensor count: 32 PASS
- Selected epoch: 71 PASS
- Selection metric: 3.2245595973856656 PASS
- Full config hash: `aeab466455bc2f28fd0127165e121f80b8d75dcd1924b79043b105611b88b0e9` PASS
- Final generator epoch: 111, fit window count 672, training_completed COMPLETED, finite FINITE

Report identities: member `wgan-seed-05`, run prefix `308cda2acc42be1b`, seeds `12281/12281/12282/8283`, training-data `3702ef77...`, runtime `17e3bb52...` all bound correctly.

Prospective diagnostics required since Task 137: all `PRESENT`:

- critic_loss_curve length 111 PRESENT
- generator_loss_curve length 111 PRESENT
- gradient_penalty_curve length 111 PRESENT
- selection selection_metric_curve length 111 PRESENT (inside checkpoint_selection)
- critic_update_count 6105 PRESENT
- generator_update_count 1221 PRESENT
- training_completion COMPLETED PRESENT
- finite_nonfinite FINITE PRESENT
- checkpoint_selection stability PRESENT (best 71 / 3.224...)
- availability map correctly marks PRESENT for above and MISSING_BY_DESIGN_HISTORICAL for wgan-seed-01
- mode_collapse_indicator `NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE` with null value PASS
- No fabricated values

Critic:generator optimizer-step accounting `6105:1221` exactly `5:1` PASS (11 batches per epoch *111 epochs =1221; 1221*5=6105).

Therefore classification is:

`VALID_EXECUTION_NO_GATE_RESULT`

No Gate result exists yet. Do not authorize or execute Gate.

## Execution evidence and amendment chronology

Execution evidence artifact committed alone:

- Path: `reports/research/evidence/structured_vol_v5_wgan_seed05_execution_v1_171.json` (commit `b9db9a841afaa3f8b1ef0142f8b6b4fd3661b237`, canonical `921eb5ad63c8e8c2ea2b7151e1ece4d80b9ccf27388fd06de78728f8c0106e34`, blob `8b5c9b45c72fe5c3fc8c5629694096e92391ef01`, raw same)
- Records Task ID, starting HEAD `ae544db4...`, safety branch `safety/pre-wgan-seed05-training-execution-ae544db`, authorization canonical `0753a576...` / blob `0aa73233...` raw same, seed tuple `12281/12281/12282/8283`, implementation/config/data identities, full_config_hash `aeab4664...`, run prefix `308cda2acc42be1b`, runtime `17e3bb52...`, exact command, launch/session PIDs 26576, timestamps, exit 0, wall 3422, governed count 1, marker `108eb6b4...`, checkpoint `4a728a10...` 338677, report `8e58a615...` 14719, stdout 0/e3b0..., stderr 450/4511b..., classification `VALID_EXECUTION_NO_GATE_RESULT`, Gate not authorized, reserve not authorized, H2 not calculated, final sealed, diagnostic persistence verified.

Amendment 088:

- Path: `reports/protocol/research_protocol_amendment_088.md` (this file)
- Records same load-bearing facts, no self-hash, does not modify Amendments 074–087.

Both committed separately, no amend/rebase/reset/push.

## Preservation and firewalls

Verified after both commits:

- Authorization unchanged `0753a576.../0aa73233...`
- Checkpoint `4a728a10...` preserved, training report `8e58a615...` preserved
- Gate authorization unchanged, Gate evaluator `243750a...`, runner `56a1370...`, comparator `78a9da57...`, model `2f5cf1dd...`, Gate config `8e70ad.../d9705ef9...` unchanged
- Seed-01/02/03/04 history unchanged (seed-01 `VALID_COMPLETED_MEMBER`, seed-02 `VALID_COMPLETED_MEMBER`, seed-03 `NONFINITE_TRAINING_FAILURE`, seed-04 `VALID_COMPLETED_MEMBER / GATE_FAIL_VALID` via Task-167 evidence `f4d59034.../b0f95764...` committed `638e385e...` raw `f4d590...`, Amendment 086 `5e395a55.../c13bbe78...`, Gate marker `6bd29009...` stdout `2088cac7...`)

Require:

- Task-171 governed scientific process count: EXACTLY 1
- retry: 0, relaunch: 0, rerun: 0, live training process: 0 after termination, seed-05 Gate authorization: 0, reserve: 0, validation: 0, external: 0, H2: 0, final: SEALED, network: 0, push: 0.

PRIMARY ATTEMPTS CONSUMED becomes `5` because seed-05 process creation consumes the fifth primary attempt, regardless of success.

Do NOT increment VALID PRIMARY MEMBERS COMPLETED yet.

If valid finite training:

`WGAN SEED-05 TRAINING: VALID_EXECUTION_NO_GATE_RESULT`

`WGAN SEED-05 TRAINING EXECUTION: EXECUTED_PENDING_INDEPENDENT_AUDIT`

Valid primary completed remains `3` until seed-05 later completes valid Gate execution.

Next task must be `NM-R5-V5-WGAN-SEED-05-TRAINING-EXECUTION-AUDIT-172` regardless of success.

This amendment is append-only, does not self-hash.

