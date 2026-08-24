# Amendment 073 — V5 WGAN Seed-01 Gate-v2 Scientific Execution

Date: 2026-08-23
Status: APPEND-ONLY SCIENTIFIC EXECUTION RECORD

## Task and governing boundary

- Task: `NM-R5-V5-WGAN-SEED-01-GATE-V2-EXECUTION-135`
- Risk: `R5`
- Branch: `main`
- Starting HEAD: `76ebe914586314055782bede8e0574b807702f67`
- Starting gate: `NM-R4-V5-WGAN-SEED-01-GATE-V2-AUTHORIZATION-AUDIT-134`
- Starting gate result: `VALIDATED`
- Governed transitions: `DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`
- Safety branch, created without switching:
  `safety/pre-wgan-seed01-gate-execution-76ebe91`
- Safety branch ref: `76ebe914586314055782bede8e0574b807702f67`

This amendment records the one and only authorized WGAN seed-01 Gate-v2
scientific process. The entitlement was consumed by the immutable Gate-start
marker. There was no retry, relaunch, rerun, overwrite, second process,
training invocation, validation, external validation, H2 calculation,
seed-02 authorization, reserve authorization, final-test access, Git network,
or push.

## Prelaunch freeze and provenance

The tracked worktree was clean before execution. Pre-existing untracked files
were preserved and not staged. The following committed Git-object identities
and path-filtered worktree blobs matched the frozen authorization:

- Gate authorization:
  `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-01-gate-v2-v1.json`
  canonical SHA-256 `215c307028e5f8a5cf7f25e4277cbf965a81d85aed0c6dfd71164e1439c06a32`;
  Git blob `b6960813f843160f4eadd05cce05cf069f0cf0e1`.
- Final evaluator blob: `f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`.
- Training runner blob: `7e020ea937af9e2713451ae735d58c4cbb645289`.
- Model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`.
- Comparator blob: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`.
- WGAN config canonical SHA-256
  `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`;
  Git blob `e0740afc24697f2eab3620a4243d04411aa508cb`.
- Gate config canonical SHA-256
  `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`;
  Git blob `d9705ef9a11da3e21760015bb2a27fa408018bb5`.
- Task-127 evidence canonical SHA-256
  `96489abe4f2c0ca7b2c460b70ecbd2d881fcb5dd6ebea9e62643fe0c36f30e6f`;
  Git blob `21bcd88957ad69e8aef7b9675d308daf697b2ac7`.
- Training authorization v3 canonical SHA-256
  `19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690`;
  Git blob `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`.
- Frozen checkpoint:
  `data/processed/research/model/wgan-comparator/wgan-seed-01/ebfbf915ec8316d8/checkpoint.pt`;
  raw SHA-256 `332614157e2c1d30e6a5fd043cb893b36c508e4ab2603b07642e0d66ddb7718e`.
- Training execution marker:
  `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/execution_started.json`;
  raw SHA-256 `18d246aa4d3146092a3df5ee243492f7e9859f2fb61c7b82d8f6d1f84d907be1`.

The Gate authorization parsed as schema
`structured-vol-v5-wgan-gate-authorization-v1`, member `wgan-seed-01`,
Gate task `NM-R5-V5-WGAN-SEED-01-GATE-V2-EXECUTION-135`, marker path
`reports/research/wgan_gate_runs/wgan-seed-01/gate-v2-execution-135/execution_started.json`,
`max_scientific_invocations: 1`, `training_authorized: false`,
`gate_execution_authorized: true`, `validation_authorized: false`,
`final_test_authorized: false`, `overwrite: false`, and `relaunch: false`.
Exactly one seed-01 Gate-v2 authorization existed; no alternate existed. The
Task-135 marker and Gate result were absent before process creation.

The frozen checkpoint was read with CPU map location and `weights_only=True`,
without mutation. It confirmed:

- `best_generator_epoch: 63`;
- `best_selection_metric: 3.0610572388897204`;
- `config_hash: 31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58`.

## Runtime identity

The evaluator-order runtime sequence was independently reproduced exactly:

1. `require_cuda_device(requested_device)`;
2. `resolve_device(requested_device)`;
3. `require_cuda_device(resolved_device)`;
4. `configure_device_determinism(resolved_device, enabled=True)`;
5. `build_runtime_identity(requested_device, resolved_device)`.

Observed runtime:

- Python `3.11.9`;
- PyTorch `2.13.0+cu132`;
- CUDA `13.2`, available `true`;
- GPU `NVIDIA GeForce RTX 4070 Laptop GPU`, capability `8.9`;
- cuDNN `92000`;
- requested/resolved `cuda/cuda`;
- deterministic algorithms `true`;
- cuDNN benchmark `false`;
- cuDNN deterministic `true`;
- runtime identity
  `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`.

The pre-determinism identity
`35d07adc53bebe974457f2e87e8af0b4ff9d3f0cb19791f6370f8cf98d82ffbd` was not
accepted. CPU fallback remained prohibited.

## Scientific invocation chronology

The exact parser-derived command was:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_gate_evaluator --member-id wgan-seed-01 --checkpoint data/processed/research/model/wgan-comparator/wgan-seed-01/ebfbf915ec8316d8/checkpoint.pt --checkpoint-sha256 332614157e2c1d30e6a5fd043cb893b36c508e4ab2603b07642e0d66ddb7718e --authorization reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-01-gate-v2-v1.json --execute`

It was launched in the background exactly once:

- terminal session: `proc_530ec4eaad2e`;
- terminal process PID: `31688`;
- launcher PID recorded in the launch evidence: `2670`;
- evaluator PID recorded in the immutable Gate marker: `25276`;
- start UTC: `2026-08-24T00:45:41.617592400+0000`;
- start local: `2026-08-23T20:45:41.638126500-0400`;
- end observed at stdout close: `2026-08-24T00:45:48.647223+00:00`;
- wall time: `7.029631` seconds;
- exit code: `0`;
- governed process count: `1`;
- retry/relaunch/rerun: `0/0/0`;
- stdout: `.agent-memory/task-135/stdout.log`, `7710` bytes,
  SHA-256 `6d96c1f792c4a1ce73a06014684a81ef5c74fd53b977f05a0be8c90d4697ed48`;
- stderr: `.agent-memory/task-135/stderr.log`, `0` bytes,
  SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The original process alone was observed to termination. No second Gate CLI
invocation was used for inspection.

## Gate marker and result

The evaluator created exactly one immutable marker:

- path:
  `reports/research/wgan_gate_runs/wgan-seed-01/gate-v2-execution-135/execution_started.json`;
- raw SHA-256:
  `4a1d4dd600d3506cfc839f2bf8da571a9603b2b7af9a08347761e54428cc863a`;
- schema: `structured-vol-v5-wgan-gate-execution-start-v1`;
- marker timestamp UTC: `2026-08-24T00:45:46.811556+00:00`;
- marker count: `1`;
- Gate task: `NM-R5-V5-WGAN-SEED-01-GATE-V2-EXECUTION-135`;
- member: `wgan-seed-01`;
- authorization canonical SHA/blob:
  `215c307028e5f8a5cf7f25e4277cbf965a81d85aed0c6dfd71164e1439c06a32` /
  `b6960813f843160f4eadd05cce05cf069f0cf0e1`;
- checkpoint SHA:
  `332614157e2c1d30e6a5fd043cb893b36c508e4ab2603b07642e0d66ddb7718e`;
- training marker SHA:
  `18d246aa4d3146092a3df5ee243492f7e9859f2fb61c7b82d8f6d1f84d907be1`;
- training authorization, Task-127 evidence, evaluator, Gate config, seeds,
  runtime identity, and PID were bound exactly as recorded above.

The finite scientific Gate evaluation produced a valid poor result. The frozen
Gate criteria were:

- finite output: `true` (pass);
- variance ratio: `40.51914294429684` (fail; required `[0.50, 2.00]`);
- terminal dispersion ratio: `5.884726691292518` (fail; required `[0.50, 2.00]`);
- path uniqueness: `1.0` (pass; minimum `0.99`);
- absolute lag-1 ACF difference: `0.9724993480217599` (fail; maximum `0.25`).

Report-only outputs were:

- normalized terminal Wasserstein: `41.83150998600351`;
- raw-return ACF RMSE: `0.6877704458613763`;
- raw-return ACF maximum error: `0.9724993480217599`;
- conditional-variance log-correlation: `-0.06406967637484266`;
- absolute-return ACF, lags `[1, 2, 3, 5, 10, 20]`:
  - real: `{1: 0.3450408666836692, 2: 0.2603867592009751, 3: 0.1546991199179677, 5: -0.034484678950656385, 10: 0.034676842472670485, 20: -0.037932909482695794}`;
  - generated: `{1: 0.9713642064215674, 2: 0.9356676381145105, 3: 0.8933652742065923, 5: 0.791022819407289, 10: 0.4537705375742863, 20: -0.3634004242756069}`;
- squared-return ACF:
  - real: `{1: 0.30897858687059576, 2: 0.20100656884555976, 3: 0.05184692982603987, 5: -0.04593829130076654, 10: -0.004108221958416775, 20: 0.02556645050472458}`;
  - generated: `{1: 0.9412321024102481, 2: 0.8789460523306485, 3: 0.8135984501900332, 5: 0.6761642465520054, 10: 0.3136399948609311, 20: -0.324209414235325}`.

The evaluator did not compute selection-loss Gate criteria, internal-RBF
criteria, `drift_diffusion_rms_ratio`, or a WGAN drift/diffusion decomposition.
The structured Gate result was emitted to stdout; no separate tracked Gate
result report was created. The result classification is exactly
`GATE_FAIL_VALID`, with `numerically_valid: true`,
`completed_model_member: true`, and `poor_performance_discarded: false`.
The valid poor result is retained and does not authorize any follow-up
execution.

## Evidence and preservation

The execution evidence artifact was committed alone:

- path:
  `reports/research/evidence/structured_vol_v5_wgan_seed01_gate_v2_execution_135.json`;
- evidence commit: `e4c1ace25d7240d5c208bf57ae6734fe9c4b1c32`;
- committed Git blob: `67a56e16da807489e10435410b62536545b499a9`;
- canonical SHA-256 of committed Git-object content:
  `e38db9634e309e5ae830d49f82cba57dd88626fcb4b6d100028ee9e2c318968e`;
- no self-hash is included in this amendment.

The checkpoint and training execution marker remained byte-identical after
execution. The valid Gate marker and poor Gate result were retained; no
artifact was deleted, overwritten, replaced, or repaired.

## Status and firewalls

- WGAN comparator: `IMPLEMENTATION_VALIDATED`.
- WGAN training runner: `PATH_REPAIR_VALIDATED`.
- WGAN seed-01 scientific training: `VALID_COMPLETED_TRAINING`.
- WGAN seed-01 Gate evaluator: `VALIDATED_HARDENED`.
- WGAN seed-01 Gate authorization: `VALIDATED_CONSUMED`.
- WGAN seed-01 Gate: `GATE_FAIL_VALID`.
- WGAN seed-01 scientific result: `GATE_FAIL_VALID`.
- Valid poor result retained: `true`.
- Seed-02 authorization: `NOT CREATED`.
- Reserve authorization: `NOT CREATED`.
- Training after Task-135: `0`.
- Validation: `0`.
- External validation: `0`.
- H2: `NOT CALCULATED`; status remains `UNRESOLVED_PENDING_WGAN_COMPARATOR`.
- Final test: `SEALED`.
- Git network: `0`.
- Push: `0`.

This amendment is append-only and intentionally contains no self-hash.

Next governed action: `NM-R5-V5-WGAN-SEED-01-GATE-V2-EXECUTION-AUDIT-136`
(strictly read-only), regardless of the valid Gate-fail result.
