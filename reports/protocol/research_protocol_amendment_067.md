# Amendment 067 — V5 WGAN Seed-01 Scientific Execution Authorization V2 Freeze

Date: 2026-08-23
Status: APPEND-ONLY AUTHORIZATION V2 FREEZE RECORD

## Task and governing boundary

- Task: NM-R4-V5-WGAN-SEED-01-AUTHORIZATION-V2-FREEZE-122
- Risk: R4
- Starting branch: `main`
- Starting HEAD: `c42d14d85fe07d76bfd5551d3ff33dc90d1af704`
- Prerequisite audit: NM-R4-V5-WGAN-RUNNER-MARKER-PATH-REPAIR-COMPLETION-AUDIT-121
- Prerequisite verdict: VALIDATED WITH NON-BLOCKING FINDINGS
- Target: `wgan-seed-01`
- Authorization artifact version: `v2`
- Authorization schema: `structured-vol-v5-wgan-authorization-v1`
- V2 authorization commit: `fe10ebfdf24268ec12206fab54edf0d347bd035d`

This amendment freezes one authorization artifact only. It does not authorize
or report scientific execution, runner CLI use, dry-run CLI use, market-data
access, training, simulation, checkpoint creation, marker creation, Gate, H2,
validation, external validation, final-test access, seed-02 authorization,
network access, or push.

The governing transitions are:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

## Target member and seed tuple

- Member: `wgan-seed-01`
- Role: `PRIMARY`
- Reserve: `false`
- Replicate seed: `8281`
- Model-init seed: `8281`
- Data seed: `8282`
- Evaluation seed: `8283`

The frozen random-source semantics remain:

- model initialization: member `model_init_seed=8281`;
- training latent and temporal noise: member `data_seed=8282`;
- training window ordering: member `data_seed=8282`;
- WGAN-GP interpolation randomness: member `data_seed=8282`;
- internal-selection generated paths: common fixed `7777`;
- real bootstrap reference: common fixed `8801`;
- future post-training evaluation/Gate: common fixed `8283`.

Architecture, objective, optimizer, batch size, critic ratio, early stopping,
selection metric, checkpoint rule, seed schedule, and data-split contract are
unchanged. No reserve authorization was created.

## Frozen authorization artifact

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v2.json`
- SHA-256: `c5eed6098eb681d58ff42bfee7d9660b16da3922991990c1065b2af47fd838ad`
- Git blob: `804d3b42cf9d19a3e27bb090e05cfe219039ceb3`
- Artifact version: `v2`
- Schema version: `structured-vol-v5-wgan-authorization-v1`
- Self-authentication: `false`

The v2 artifact reuses the validated v1 schema. Its optional provenance fields
record the v1 exhaustion lineage and the completed runner-repair lineage
without changing runner schema validation.

## Effective configuration identity

- Runtime-config path: `configs/research/structured_vol_wgan_comparator_v1.yaml`
- Runtime-config SHA-256: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`
- Runtime-config Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`
- Canonical `WGANTrainingConfig.config_hash()` for `wgan-seed-01`: `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58`
- Run prefix: `ebfbf915ec8316d8`

The current committed source was used to recompute the effective config. The
recomputed hash equals the required frozen identity. No configuration value or
config-hashing implementation changed.

## Methodology, implementation, and contract identities

- Preregistration path: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json`
- Preregistration SHA-256: `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037`
- Preregistration Git blob: `72311888542ee83ff497b5f0adbbaf6429e8452a`
- Amendment 060 path: `reports/protocol/research_protocol_amendment_060.md`
- Amendment 060 SHA-256: `2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c`
- Amendment 060 Git blob: `a1ba052abe8b4a50887ec84b934e16a328e60596`
- Amendment 062 path: `reports/protocol/research_protocol_amendment_062.md`
- Amendment 062 SHA-256: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07d3aca96fa6`
- Amendment 062 Git blob: `086e13f063fe79f07be8b4e0668d4a13e843a8d9`
- Model path: `src/neuralmarket/models/wgan_cde.py`
- Model Git blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
- Comparator path: `src/neuralmarket/research/wgan_comparator.py`
- Repaired comparator Git blob: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`
- Final repaired runner path: `src/neuralmarket/research/wgan_runner.py`
- Final repaired runner Git blob: `7e020ea937af9e2713451ae735d58c4cbb645289`
- Execution-contract path: `reports/research/structured_vol_v5_wgan_execution_contract_v1.json`
- Execution-contract SHA-256: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4`
- Execution-contract Git blob: `194b68797538010f35f5d48a2ec7c4cc4eee533f`
- Seed-schedule path: `reports/research/structured_vol_v5_seed_schedule_v1.json`
- Seed-schedule SHA-256: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`
- Seed-schedule Git blob: `558d08bfee98dbd0c170d65e6a9b1737700c9e98`

The execution-recipe head is bound to the pre-authorization executable/scientific
recipe state:

- Execution-recipe head: `c42d14d85fe07d76bfd5551d3ff33dc90d1af704`
- Separate WGAN recipe specification: none
- Future current-HEAD equality: not required by existing runner semantics

## Runner-repair provenance

- Task 118: loader-side authorization-path normalization repair.
- Task 120: complete normalized authorization-path propagation through the
  caller/callee graph and marker boundary; marker payload preparation moved
  before report-directory creation.
- Audit 121: `PATH_REPAIR_VALIDATED` with non-blocking findings.
- Amendment 066 SHA-256: `c72c96100f760e66473c9e7494b7b7c8550b634008e9c48babf00d1e73bb8e74`
- Amendment 066 Git blob: `a3baab9341e92775616cf1bbd7a77301190cc1a8`
- Task-120 repair commit: `78449c9a015a06233ee5a765b8a7fd2ee89d5d42`
- Final runner blob bound by v2: `7e020ea937af9e2713451ae735d58c4cbb645289`

The v2 authorization binds the final repaired runner, not the governance-
exhausted v1 runner identity.

## Fresh production CUDA runtime identity

Captured read-only from the repository's `.venv-gpu` environment using the
existing device-resolution and runtime-identity mechanisms, after enabling the
frozen deterministic settings:

- Environment: `.venv-gpu`
- Python: `3.11.9`
- PyTorch: `2.13.0+cu132`
- torch CUDA runtime: `13.2`
- CUDA available: `true`
- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
- Compute capability: `8.9`
- cuDNN: `92000`
- NVIDIA driver: `610.47`
- Deterministic algorithms: `true`
- cuDNN benchmark: `false`
- cuDNN deterministic: `true`
- Requested device: `cuda`
- Resolved device: `cuda`
- Runtime identity schema: `runtime-identity-v1`
- Runtime identity SHA-256: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Relation to v1 runtime: `FRESHLY_RECOMPUTED_AND_EQUAL_TO_V1`
- CPU fallback: `PROHIBITED`

The capture loaded no market data, did not invoke the runner CLI, did not train,
did not simulate, and did not create a marker, checkpoint, or scientific
namespace.

## Permissions and execution limits

The committed v2 artifact records:

- `max_scientific_invocations`: `1`;
- `training_authorized`: `true`;
- `validation_authorized`: `false`;
- `final_test_authorized`: `false`;
- `automatic_reserve_execution`: `false`;
- `overwrite`: `false`;
- `relaunch`: `false`;
- `rerun`: `false`;
- `authorization_consumed`: `false`;
- `scientific_execution_performed`: `false`.

## Authorization v1 lineage

- v1 exists: `YES`
- v1 path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json`
- v1 SHA-256: `8d889457b48e20b81bd2ef841cd347b1ecd9d79df48d789a03d1ea7c05ac02e8`
- v1 Git blob: `c5e234e5a8efc31f9c882ba451c25d98a606ba9c`
- v1 technical consumption: `UNCONSUMED`
- v1 governance entitlement: `EXHAUSTED`
- v1 reusable: `NO`
- v1 mutated: `NO`
- Task-116 result: `NO_RESULT_PRELAUNCH_BLOCK`
- Reason for v2: final runner changed after audited pre-scientific path repair.

V1 was not replaced, renamed, deleted, mutated, or superseded in place.

## Offline verification and firewalls

Library-level validation used the current `validate_authorization_payload`
function with a freshly recomputed runtime identity and current committed
implementation identities. It did not call `main()`, invoke the runner CLI,
perform a CLI dry-run, load market data, consume authorization, or create
scientific outputs.

- JSON syntax: PASS
- Schema version and required fields: PASS
- Member/seed tuple: PASS
- Runtime/CUDA identity: PASS
- Implementation and provenance identities: PASS
- Permissions: PASS
- Recipe head: PASS
- V1 unchanged after validation: PASS
- V2 unchanged after validation: PASS
- WGAN marker: absent
- Checkpoint: absent
- Report namespace: absent
- Model namespace: absent
- Runner CLI: 0
- CLI dry-run: 0
- Market-data access: 0
- Scientific training: 0
- Simulation: 0
- Authorization consumed: 0
- Authorization mutated: 0
- Provider/scientific network: 0
- Git-remote network: 0

No repository-wide test suite was run because Task 122 changes authorization
and append-only documentation only, and the repository baseline was already
GREEN. No source or test file changed.

## Governance state

- Scientific execution: `0`
- Marker: `0`
- Checkpoint: `0`
- Gate: `0`
- H2: `UNRESOLVED`
- Validation: `0`
- External validation: `0`
- Final: `SEALED`
- Push: `0`
- Amend: `NO`
- Rebase: `NO`
- Reset: `NO`
- Self-hash: absent by design; this amendment does not embed its own future SHA-256 or Git blob.

Amendments 059–066 were not modified. Amendment 067 is append-only.

## Status and next governed action

WGAN COMPARATOR:
`IMPLEMENTATION_VALIDATED`

WGAN RUNNER:
`PATH_REPAIR_VALIDATED`

WGAN SEED-01 AUTHORIZATION V1:
`TECHNICALLY_UNCONSUMED_BUT_GOVERNANCE_EXHAUSTED`

WGAN SEED-01 AUTHORIZATION V2:
`FROZEN_PENDING_INDEPENDENT_AUDIT`

WGAN SEED-01 SCIENTIFIC EXECUTION:
`NOT PERFORMED`

WGAN SEED-01 EXECUTION READINESS:
`NOT_READY_PENDING_V2_AUTHORIZATION_AUDIT`

WGAN SEED-02 AUTHORIZATION:
`NOT CREATED`

REPOSITORY TEST BASELINE:
`GREEN`

H2:
`UNRESOLVED_PENDING_WGAN_COMPARATOR`

FINAL TEST:
`SEALED`

Next governed action: independent read-only audit of the seed-01 v2
authorization before any scientific execution.

This amendment is append-only and intentionally does not self-hash. Its own
SHA-256 and Git blob are to be recorded only after commit in the governed task
report or a later append-only provenance record.
