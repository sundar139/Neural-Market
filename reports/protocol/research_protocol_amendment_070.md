# Amendment 070 — V5 WGAN Gate-v2 Evaluator Implementation

Date: 2026-08-23
Status: APPEND-ONLY IMPLEMENTATION RECORD

## Task and governing boundary

- Task: `NM-R4-V5-WGAN-SEED-01-GATE-V2-EVALUATOR-IMPLEMENTATION-129`
- Risk: `R4`
- Branch: `main`
- Required starting HEAD: `1181185940fa42b3e6b2c6809fa1d258a1aed36b`
- Prerequisite audit: `NM-R5-V5-WGAN-SEED-01-V3-EXECUTION-AUDIT-128`
- Prerequisite verdict: `VALIDATED WITH NON-BLOCKING FINDINGS`
- Governed transitions: `DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT`
- Safety branch, created without switching: `safety/pre-wgan-gate-v2-implementation-1181185`

Audit 128 confirmed valid completed seed-01 training, no WGAN Gate execution
entry point, and no Gate result. This amendment records implementation only.
It creates no Gate authorization, performs no Gate evaluation, retrains no
model, creates no seed-02 authorization, calculates no H2, and does not access
the sealed final test.

## Frozen seed-01 training provenance

- Member: `wgan-seed-01`.
- Checkpoint path:
  `data/processed/research/model/wgan-comparator/wgan-seed-01/ebfbf915ec8316d8/checkpoint.pt`.
- Checkpoint SHA-256:
  `332614157e2c1d30e6a5fd043cb893b36c508e4ab2603b07642e0d66ddb7718e`.
- Checkpoint size: `338677` bytes.
- Selected checkpoint epoch: `63`.
- Training authorization: `wgan-seed-01-v3`.
- Training authorization SHA-256:
  `19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690`.
- Training authorization Git blob:
  `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`.
- Execution marker path:
  `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/execution_started.json`.
- Execution marker SHA-256:
  `18d246aa4d3146092a3df5ee243492f7e9859f2fb61c7b82d8f6d1f84d907be1`.
- Task-127 execution evidence:
  `reports/research/evidence/structured_vol_v5_wgan_seed01_execution_v3_127.json`.
- Task-127 evidence commit:
  `710aabe1837ae1cd84b946d0e1c76fedc301f48d`.
- Task-127 evidence Git blob:
  `21bcd88957ad69e8aef7b9675d308daf697b2ac7`.
- Task-127 evidence SHA-256:
  `96489abe4f2c0ca7b2c460b70ecbd2d881fcb5dd6ebea9e62643fe0c36f30e6f`.
- Training report path:
  `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/training_report.json`.
- Training report SHA-256:
  `bd8e4dd5fc656d50933d7200b93b392636fbd644a19225b41a48b61e457840dc`.
- Amendment 069 governing record: commit
  `1181185940fa42b3e6b2c6809fa1d258a1aed36b`, Git blob
  `54232360c6b6dff09c8eb18bb05b3e806449098e`, worktree SHA-256
  `fb3f7321eec39e1214c11cf83be9bf30794e64028cfd5cf38e9c81de22f80461`.

The training runner, comparator, model, checkpoint, execution marker, and
training report are consumed provenance and are not modified by this task.

## Governing Gate-v2 contract

The governing records are Amendment 059, Amendment 060, Amendment 069, the
WGAN execution contract, the WGAN seed schedule, the WGAN comparator
preregistration, the committed Gate-v2 configuration, and the Task-127
execution evidence. Amendment 069 explicitly separates the internal-selection
generated-path seed `7777` from the future post-training evaluation/Gate seed
`8283`; this evaluator uses the latter as required for post-training Gate
execution. The contract is therefore not ambiguous for this task.

- Gate configuration:
  `configs/research/neural_sde_internal_gate_v2.yaml`.
- Gate configuration SHA-256:
  `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`.
- Gate configuration Git blob:
  `d9705ef9a11da3e21760015bb2a27fa408018bb5`.
- Loaded Gate specification hash:
  `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469`.
- WGAN scientific/runtime config:
  `configs/research/structured_vol_wgan_comparator_v1.yaml`.
- WGAN scientific config SHA-256:
  `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`.
- WGAN scientific config Git blob:
  `e0740afc24697f2eab3620a4243d04411aa508cb`.
- Data split: frozen training-only internal fit/selection split; official
  validation, external validation, and final test are not accessed.
- Generated evaluation paths: `1024`.
- Bootstrap reference paths: `1024`.
- Path horizon: `63`.
- Bootstrap method: circular moving block.
- Bootstrap seed: `8801`.
- Bootstrap block length: `22`.
- Evaluation seed: `8283`.
- ACF lags: `[1, 2, 3, 5, 10, 20]`.

### WGAN Gate adaptation

The evaluator reuses the committed Gate-v2 loader, bootstrap helper, ACF
helpers, and one-dimensional Wasserstein helper. The WGAN-eligible
architecture-neutral pass/fail criteria are evaluated exactly once:

1. `finite_output`: generated paths must be finite and have the frozen count
   and horizon; nonfinite or structurally invalid output fails closed.
2. `variance_ratio`: generated/reference daily variance ratio in `[0.50, 2.00]`.
3. `terminal_dispersion`: generated terminal standard deviation divided by the
   bootstrap-reference terminal standard deviation in `[0.50, 2.00]`.
4. `uniqueness`: rounded generated-path uniqueness fraction at least `0.99`.
5. `acf1_agreement`: absolute lag-1 ACF difference at most `0.25`.

Report-only architecture-neutral metrics are:

- `terminal_wasserstein_normalized`;
- `acf_rmse`;
- `acf_max_error`;
- absolute-return ACF at the frozen lags;
- squared-return ACF at the frozen lags;
- conditional-variance log-correlation.

The following Neural-SDE-only or objective-specific criteria are excluded from
WGAN Gate pass/fail and are not fabricated by the evaluator:

- selection-loss improvement and total-loss quantities;
- initial/best internal RBF quantities;
- `drift_diffusion_rms_ratio` and any drift/diffusion decomposition.

The WGAN implementation has no scientifically meaningful Neural-SDE
drift/diffusion decomposition. The evaluator contains no such criterion.

A valid Gate failure is retained as a completed member. The only terminal
member statuses emitted by a structurally valid evaluation are
`GATE_PASS_VALID` and `GATE_FAIL_VALID`; both set `numerically_valid` and
`completed_model_member` true. A valid poor result never retries, relaunches,
retrains, replaces a checkpoint, tunes parameters, executes a reserve, creates
seed-02 authorization, calculates H2, or aggregates a family.

## Implemented evaluator boundary

- Evaluator path: `src/neuralmarket/research/wgan_gate_evaluator.py`.
- Training runner path: `src/neuralmarket/research/wgan_runner.py`.
- Training runner modified: `false`.
- Checkpoint loading: SHA-256 bound, `torch.load(..., weights_only=True)`,
  read-only, reconstructed with the frozen WGAN scientific configuration.
- Scientific device: requested and resolved device must be `cuda`; CPU
  scientific fallback is rejected before model/tensor/generation work.
- Model generation: frozen sample count and evaluation seed `8283`.
- Reference construction: frozen 1024-path block bootstrap, seed `8801`,
  block length `22`.
- Result: deterministic structured provenance, criteria, report-only metrics,
  status, and firewall fields.
- Authorization: required for actual evaluation; validator is fail-closed and
  accepts no training authorization as Gate authorization.
- H2, final-test, validation, reserve, retry, relaunch, overwrite, and
  authorization-creation paths are absent from the scientific evaluator.

## Future Gate authorization contract

No Gate authorization artifact was created. The validator requires a separately
committed future artifact with at least the following bindings:

- schema version and member `wgan-seed-01` (or an explicitly frozen WGAN
  roster member);
- training checkpoint path and SHA-256;
- training execution marker path and SHA-256;
- training authorization path, SHA-256, and Git blob;
- Task-127 execution evidence path, SHA-256, and Git blob;
- training runner Git blob;
- WGAN scientific config SHA-256 and Git blob;
- model Git blob;
- comparator Git blob;
- Gate evaluator Git blob;
- Gate-v2 config path, SHA-256, and Git blob;
- evaluation seed `8283`;
- bootstrap seed `8801`;
- generated and bootstrap sample counts `1024`;
- block length `22`;
- ACF lags `[1, 2, 3, 5, 10, 20]`;
- requested device `cuda`;
- expected resolved device `cuda`;
- expected production CUDA runtime identity;
- `max_scientific_invocations: 1`;
- `training_authorized: false`;
- `gate_execution_authorized: true`;
- `validation_authorized: false`;
- `final_test_authorized: false`;
- `overwrite: false`;
- `relaunch: false`.

The validator rejects missing or malformed artifacts, member/checkpoint/SHA/
identity/config/seed/device mismatches, CPU execution, and any permission flag
that would authorize training, validation, final-test access, overwrite, or
relaunch. It does not create, self-authenticate, or consume an authorization.

## Implementation identity and firewalls

- Source/test implementation commit:
  `5c2d07a53e143480a87000a43ae09bc31870e481`.
- Post-commit status-field correction commit:
  `95352342df4fa1e3e758b967ada9ef7cccd3da64`.
- Evaluator Git blob (final committed bytes):
  `f60429d30307accce2fc743881d68637c9933011`.
- Regression test path:
  `tests/unit/research/test_wgan_gate_evaluator.py`.
- Regression test Git blob:
  `781fe589512934426836fe03af1090be0f1eb237`.
- Training runner blob preserved:
  `7e020ea937af9e2713451ae735d58c4cbb645289`.
- Comparator blob preserved:
  `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`.
- Model blob preserved:
  `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`.

Counts for this implementation task:

- real seed-01 Gate executions: `0`;
- training executions: `0`;
- runner CLI executions: `0`;
- scientific checkpoint mutation: `0`;
- Gate authorization created: `0`;
- seed-02 authorization created: `0`;
- H2 calculation: `0`;
- final-test access: `0`;
- Git network: `0`;
- push: `0`.

## Deferred Audit-128 findings

The Audit-128 secondary-diagnostic finding is recorded as:

`DEFERRED — does not invalidate seed-01 and is outside this Gate evaluator task.`

The Audit-128 CRLF/artifact-tracking/data-provenance/hash-shape findings are
also `DEFERRED` and are not repaired by this implementation. No Amendment 069
bytes are modified. This amendment is append-only and contains no self-hash.

## Status

- Gate execution: `0`.
- Training: `0`.
- Seed-02 authorization: `0`.
- H2: `UNRESOLVED`.
- Final: `SEALED`.
- WGAN seed-01 Gate evaluator: `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`.
- WGAN seed-01 Gate authorization: `NOT CREATED`.
- WGAN seed-01 Gate execution: `NOT PERFORMED`.

Next governed action: independent read-only audit of the WGAN Gate-v2 evaluator
implementation before freezing the seed-01 Gate authorization.

---

*Amendment 070 records the bounded, fail-closed WGAN Gate-v2 evaluator
implementation while preserving the consumed seed-01 training provenance and
all no-execution, no-H2, seed-02, validation, and final-test firewalls.*
