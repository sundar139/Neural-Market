# Amendment 069 — V5 WGAN Seed-01 V3 Scientific Execution

Date: 2026-08-23
Status: APPEND-ONLY SCIENTIFIC EXECUTION RECORD

## Task and governing boundary

- Task: `NM-R5-V5-WGAN-SEED-01-CUDA-TRAINING-EXECUTION-V3-127`
- Risk: `R5`
- Branch: `main`
- Required starting HEAD: `7db4aca879986411a42488259918d10861d6ca84`
- Prerequisite audit: `NM-R4-V5-WGAN-SEED-01-AUTHORIZATION-V3-AUDIT-126`
- Prerequisite verdict: `VALIDATED WITH NON-BLOCKING FINDINGS`
- Safety branch: `safety/pre-wgan-seed01-v3-execution-7db4aca`
- Safety branch ref: `7db4aca879986411a42488259918d10861d6ca84`
- Execution-evidence path: `reports/research/evidence/structured_vol_v5_wgan_seed01_execution_v3_127.json`
- Execution-evidence commit: `710aabe1837ae1cd84b946d0e1c76fedc301f48d`

The governed transitions were:

`DISCOVER -> DECIDE -> EXECUTE -> VERIFY -> REPORT`

This amendment records the one separately authorized CUDA scientific process.
It does not authorize seed-02, reserve execution, validation, external
validation, H2 calculation, final-test access, or any additional WGAN process.

## Prelaunch freeze

The prelaunch gate passed before process creation:

- Branch: `main`.
- Starting HEAD: `7db4aca879986411a42488259918d10861d6ca84`.
- Tracked tree: clean.
- Safety branch created without switching: `safety/pre-wgan-seed01-v3-execution-7db4aca`.
- Runner Git blob: `7e020ea937af9e2713451ae735d58c4cbb645289`.
- Comparator Git blob: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`.
- Model Git blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`.
- Runtime-config SHA-256: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`.
- Runtime-config Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`.
- Execution-contract SHA-256: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4`.
- Execution-contract Git blob: `194b68797538010f35f5d48a2ec7c4cc4eee533f`.
- Canonical config hash: `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58`.
- Run prefix: `ebfbf915ec8316d8`.
- V1, V2, and V3 were committed and unchanged.
- Preexisting Task-127 marker: absent.
- Preexisting checkpoint: absent.
- Preexisting WGAN report/model namespaces: absent.
- Prelaunch governed process count: `0`.
- Prelaunch evidence: `.agent-memory/task-127/prelaunch.json`.

The exact selected authorization was resolved and inspected rather than
inferred from its filename:

- Selected path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v3.json`.
- Resolved filename: `wgan-seed-01-v3.json`.
- Artifact version: `v3`.
- V3 SHA-256: `19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690`.
- V3 Git blob: `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`.
- Member: `wgan-seed-01`.
- Role: `PRIMARY`.
- Replicate/model-init/data/evaluation seeds: `8281 / 8281 / 8282 / 8283`.
- Parsed Amendment-062 SHA: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6`.
- Parsed Amendment-062 SHA length: `64`.
- Fresh recomputation from committed Amendment-062 bytes: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6`.
- Parsed/recomputed equality: `true`.
- V2 selected: `false`.

The frozen random-source map was preserved:

- Model initialization: `8281`.
- Training latent/temporal noise: `8282`.
- Training window order: `8282`.
- WGAN-GP interpolation: `8282`.
- Internal-selection generated paths: `7777`.
- Bootstrap reference: `8801`.
- Future post-training evaluation/Gate: `8283`.

The fresh `.venv-gpu` runtime identity passed:

- Python: `3.11.9`.
- PyTorch: `2.13.0+cu132`.
- CUDA: `13.2`.
- CUDA available: `true`.
- Device: `NVIDIA GeForce RTX 4070 Laptop GPU`.
- Capability: `8.9`.
- cuDNN: `92000`.
- Requested/resolved device: `cuda / cuda`.
- Runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`.
- CPU fallback: `PROHIBITED`.

## Exactly one process creation

The permitted command was created once in the background:

`.venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_runner --member-id wgan-seed-01 --authorization reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v3.json --execute`

Process record:

- Session: `proc_e96b9a88fc82`.
- PID reported by the process tool: `45348`.
- Launch mode: `background`.
- Start observed: `2026-08-23T17:36:24+00:00`.
- Artifact completion observed: `2026-08-23T18:28:13.100176+00:00`.
- Process termination observed: `2026-08-23T18:28:33+00:00`.
- Wall-clock duration to artifact completion: `3109.100176` seconds.
- Exit code: `0`.
- Governed process invocation count: `1`.
- Retry: `0`.
- Relaunch: `0`.
- Rerun: `0`.
- stdout path: `.agent-memory/task-127/stdout.log`.
- stdout bytes/SHA-256: `0` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- stderr path: `.agent-memory/task-127/stderr.log`.
- stderr bytes/SHA-256: `450` / `4511b8663b3d38dc62bb10091ea007ffc9ea342f20139b2120e0a2d5d0eb6e7b`.

The stderr contained one nonfatal PyTorch cuBLAS warning about establishing a
primary CUDA context. The process exited successfully. No second runner
process was created, including during observation or verification.

## Scientific execution outcome

The process crossed the scientific boundary and completed training:

- Execution-started marker: present.
- Marker path: `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/execution_started.json`.
- Marker SHA-256: `18d246aa4d3146092a3df5ee243492f7e9859f2fb61c7b82d8f6d1f84d907be1`.
- Marker-bound V3 authorization blob: `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`.
- Market data loaded: `true`, from the authorized local research data path.
- Model constructed: `true`.
- Training entered: `true`.
- Training completed: `true`.
- Checkpoint: present.
- Checkpoint path: `data/processed/research/model/wgan-comparator/wgan-seed-01/ebfbf915ec8316d8/checkpoint.pt`.
- Checkpoint SHA-256: `332614157e2c1d30e6a5fd043cb893b36c508e4ab2603b07642e0d66ddb7718e`.
- Checkpoint size: `338677` bytes.
- Selected checkpoint epoch: `63`.
- Selected internal-selection metric: `3.0610572388897204`.
- Training result/report: present.
- Training report path: `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/training_report.json`.
- Training report SHA-256: `bd8e4dd5fc656d50933d7200b93b392636fbd644a19225b41a48b61e457840dc`.
- Training report size: `797` bytes.
- Checkpoint tensors inspected: `32`.
- Nonfinite checkpoint tensors: `0`.
- Finite status: `true`.
- Critic diagnostics: `NOT_RECORDED_BY_RUNNER`.
- Generator diagnostics: `NOT_RECORDED_BY_RUNNER`.
- Gradient-penalty diagnostics: `NOT_RECORDED_BY_RUNNER`.
- Generator/critic update counts: `NOT_RECORDED_BY_RUNNER`.
- Validation accesses: `0`.
- Final-test accesses: `0`.
- Model artifact: checkpoint present.
- Result artifact: training report present.
- Diagnostic output: none produced.
- Gate result output: none produced.

The authorized runner performs training and writes the checkpoint/report but
does not execute the downstream Gate-v2 evaluation. Therefore no Gate value is
inferred from the training metric.

## Classification

- Gate executed: `false`.
- Gate criteria 1–6: `NOT_EXECUTED`.
- Overall Gate result: `NO_GATE_RESULT`.
- Frozen scientific classification: `VALID_EXECUTION_NO_GATE_RESULT`.
- Technical authorization consumption: `CONSUMED_BY_EXECUTION_MARKER`.
- Authorization artifact mutation: `false`.
- H2: `NOT CALCULATED`.
- Final test: `SEALED`.

This is a completed valid training execution with no Gate result, not a Gate
pass, Gate fail, or numerical scientific comparison. The selected checkpoint
and metric are recorded without tuning, rerun, or favorable reinterpretation.

## Firewalls and preserved state

- V1: unchanged; not used; governance-exhausted.
- V2: unchanged; not used; superseded unexecuted identity defect.
- V3: unchanged; selected and consumed by the single execution marker.
- Runner: unchanged; final blob `7e020ea937af9e2713451ae735d58c4cbb645289`.
- Comparator: unchanged; blob `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`.
- Model: unchanged; blob `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`.
- Runtime config: unchanged; SHA/blob preserved.
- Execution contract: unchanged; SHA/blob preserved.
- Historical Neural-SDE markers: untouched.
- Task-127 process count: exactly `1` created; `0` additional.
- Retry/relaunch/rerun: `0 / 0 / 0`.
- Reserve authorization: not created.
- Seed-02 authorization: not created.
- Automatic reserve: `0`.
- Validation: `0`.
- External validation: `0`.
- H2 calculation: `0`.
- Final-test access: `0`.
- Provider/scientific network calls: `0`.
- Git-remote network: `0`.
- Push: `0`.

The generated scientific marker, checkpoint, and training report remain in the
working tree and were not deleted or altered. The three pre-existing untracked
Neural-SDE/structured-vol report files remain untouched. Only the Task-127
execution-evidence artifact was staged for its first commit.

## Status and next governed action

WGAN COMPARATOR: `IMPLEMENTATION_VALIDATED`

WGAN RUNNER: `PATH_REPAIR_VALIDATED`

WGAN SEED-01 AUTHORIZATION V1: `TECHNICALLY_UNCONSUMED_BUT_GOVERNANCE_EXHAUSTED`

WGAN SEED-01 AUTHORIZATION V2: `SUPERSEDED_UNEXECUTED_IDENTITY_DEFECT`

WGAN SEED-01 AUTHORIZATION V3: `VALIDATED_CONSUMED`

WGAN SEED-01 SCIENTIFIC RESULT: `VALID_EXECUTION_NO_GATE_RESULT`

WGAN SEED-01 EXECUTION READINESS: `EXECUTED_AWAITING_INDEPENDENT_AUDIT`

WGAN SEED-02 AUTHORIZATION: `NOT CREATED`

H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`

FINAL TEST: `SEALED`

Next governed action: independent read-only audit of Task-127 execution before
any seed-02 authorization or additional WGAN scientific execution.

This amendment is append-only, does not self-hash, and does not modify
Amendments 063–068, authorization V1/V2/V3, source, runner, comparator, model,
configuration, or final controls.
