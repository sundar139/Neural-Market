# Amendment 064 — V5 WGAN Seed-01 Scientific Training Execution

Date: 2026-08-23
Status: APPEND-ONLY EXECUTION RECORD

## Task and authorization

- Task: NM-R5-V5-WGAN-SEED-01-CUDA-TRAINING-EXECUTION-116
- Risk: R5
- Prerequisite audit: NM-R4-V5-WGAN-SEED-01-AUTHORIZATION-AUDIT-115
- Prerequisite verdict: VALIDATED WITH NON-BLOCKING FINDINGS
- Pre-execution branch: main
- Pre-execution HEAD: 2543c13f12f8b8c3e261a51b421b27f84bd4fdde
- Safety branch: safety/pre-wgan-seed01-execution-2543c13
- Authorization path: reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json
- Authorization SHA-256: 8d889457b48e20b81bd2ef841cd347b1ecd9d79df48d789a03d1ea7c05ac02e8
- Authorization Git blob: c5e234e5a8efc31f9c882ba451c25d98a606ba9c
- Authorization audit status: VALIDATED
- Authorization before/after: byte-identical
- Authorization consumed: NO

Exactly one authorized scientific invocation was created. No second process,
retry, relaunch, overwrite, reserve, or additional authorization was used.

## Execution identity

- Member: wgan-seed-01
- Role: PRIMARY
- Replicate seed: 8281
- Model-init seed: 8281
- Data seed: 8282
- Evaluation seed: 8283
- Internal-selection generated-path seed: 7777
- Real bootstrap seed: 8801
- Canonical WGANTrainingConfig hash: 31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58
- Deterministic run prefix: ebfbf915ec8316d8
- Runtime-config SHA-256: de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7
- Runtime-config Git blob: e0740afc24697f2eab3620a4243d04411aa508cb
- Comparator Git blob: 87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b
- Model Git blob: 2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe
- Runner Git blob: 2e87199a2237b4f23576fa181a38ba29807c8ae2
- Execution-contract SHA-256: 4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4
- Execution-contract Git blob: 194b68797538010f35f5d48a2ec7c4cc4eee533f
- Execution-recipe head: fccbf3c108b3feb543c50d4a5efed9d6caea6094
- Seed schedule SHA-256: 8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0
- Seed schedule Git blob: 558d08bfee98dbd0c170d65e6a9b1737700c9e98

## CUDA runtime

- Environment: .venv-gpu
- Python: 3.11.9
- PyTorch: 2.13.0+cu132
- CUDA runtime: 13.2
- CUDA available: true
- Requested device: cuda
- Resolved device: cuda
- GPU: NVIDIA GeForce RTX 4070 Laptop GPU
- Compute capability: 8.9
- cuDNN: 92000
- Runtime identity: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Deterministic algorithms: true
- cuDNN benchmark: false
- cuDNN deterministic: true
- CPU fallback: prohibited

## Single invocation

- Exact command:

  .venv-gpu/Scripts/python.exe -m neuralmarket.research.wgan_runner --member-id wgan-seed-01 --authorization reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json --execute

- Launch mode: background
- Process session: proc_9c8a07adbb79
- PID: 35076
- Process start observed: 2026-08-23T04:39:25.734584+00:00, based on stdout redirect creation
- Process end observed: 2026-08-23T04:39:30.140260+00:00, based on stderr final modification
- File-timestamp elapsed interval: 4.405676 seconds
- Process driver reported uptime: 10 seconds
- Exit code: 2
- Invocation count: 1
- Retry: 0
- Relaunch: 0
- Overwrite: 0
- Automatic reserve: 0

The runner refused execution before publishing its exclusive marker. The exact
stderr was:

`REFUSED: execution: 'reports\\research\\authorizations\\structured_vol_v5_wgan_training\\wgan-seed-01-v1.json' is not in the subpath of 'C:\\Users\\rohit\\Documents\\Personal Projects\\Neural Market' OR one path is relative and the other is absolute.`

The runner's authorization loader received the exact relative authorization
path required by this task and called `Path.relative_to(REPO)` before marker
creation. The path mismatch caused a prelaunch refusal. The runner was not
changed, and the command was not retried with an absolute path.

## Process logs and artifacts

- Stdout path: .agent-memory/task-116/stdout.log
- Stdout SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
- Stdout bytes: 0
- Stderr path: .agent-memory/task-116/stderr.log
- Stderr SHA-256: 65ebdbe9e6e6091426722e2b4e87f4b0b26a20db0e22b1a69b19f4c33df617f4
- Marker: NOT CREATED
- Marker count before/after: 0 / 0
- Checkpoint: NOT CREATED
- Run/report artifacts: NONE
- WGAN scientific namespace: NOT CREATED
- Scientific data access: 0
- Scientific training: 0
- Scientific simulation: 0
- Refit: 0
- Gate result produced by runner: NONE

No scientific training diagnostics, selected epoch, checkpoint metric,
critic diagnostics, generator diagnostics, gradient-penalty diagnostics, or
internal-selection metric were produced. No values are synthesized here.

## Committed execution evidence

- Execution evidence path: reports/research/evidence/structured_vol_v5_wgan_seed01_execution_116.json
- Execution commit: fe223d3b8fd9076bd65aaf5037ced520c1aff050
- Execution evidence SHA-256: 3a3f82058054abf068f67ec26f668b743133f104c4a8e0b1e49b260dc3737402
- Execution evidence Git blob: a8de52fb6279f55ac1c5b7469dec7d3ec79f3cd6

## Governance and firewalls

- Additional authorization: 0
- Additional member: 0
- Seed-02 execution: 0
- Automatic reserve: 0
- Separate Gate invocation: 0
- H2 calculation: 0
- Validation: 0
- External validation: 0
- Final test: 0
- Provider/scientific network: 0
- Git-remote network: 0
- Push: 0
- Amend: NO
- Rebase: NO
- Reset: NO

- WGAN comparator: IMPLEMENTATION_VALIDATED
- WGAN seed-01 authorization: VALIDATED_NOT_CONSUMED_IF_PRELAUNCH_BLOCKED
- WGAN seed-01 scientific execution: BLOCKED_PRELAUNCH
- WGAN seed-01 outcome: NOT_APPLICABLE_PRELAUNCH_BLOCK
- H2: UNRESOLVED_PENDING_WGAN_COMPARATOR
- Final test: SEALED

This amendment is append-only and intentionally does not self-hash. Its own
SHA-256 and Git blob are recorded only after commit in the governed report or
later append-only provenance.
