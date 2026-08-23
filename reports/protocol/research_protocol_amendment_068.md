# Amendment 068 — V5 WGAN Seed-01 Authorization V3 Identity Repair

Date: 2026-08-23
Status: APPEND-ONLY AUTHORIZATION V3 IDENTITY-REPAIR RECORD

## Task and governing boundary

- Task: `NM-R4-V5-WGAN-SEED-01-AUTHORIZATION-V3-IDENTITY-REPAIR-124`
- Risk: `R4`
- Branch: `main`
- Task starting HEAD: `922623b665663ce8791749e1916199af3548fc68`
- Prerequisite adjudication: `NM-R4-V5-WGAN-V2-AMENDMENT062-IDENTITY-ADJUDICATION-125`
- Adjudication result: `COMMITTED_V2_IDENTITY_MALFORMED_AUDIT123_CONFIRMED`
- V3 authorization commit: `e6b7b7cdbb79faf0d9548f8a5123e6cffc80d081`

This amendment records the corrected seed-01 authorization identity only. It
creates no scientific result and does not authorize execution by itself.

The governed transitions are:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

No `--execute`, real runner CLI, CLI dry-run, training, simulation, marker,
checkpoint, Gate, H2, scientific validation, external validation, final test,
seed-02 authorization, runner modification, network access, or push occurred.

## Adjudicated immutable defect

The defect was reproduced from immutable Git objects before mutation.

- V2 path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v2.json`
- V2 creation commit: `fe10ebfdf24268ec12206fab54edf0d347bd035d`
- V2 Git blob: `804d3b42cf9d19a3e27bb090e05cfe219039ceb3`
- Parsed field: `implementation_repair_provenance.amendment_062_sha256`
- Malformed committed value: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07d3aca96fa6`
- Malformed length: `61`
- Malformed SHA-256 shape: `false`
- Actual Amendment-062 SHA recomputed from committed bytes: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6`
- Actual length: `64`
- Actual SHA-256 shape: `true`
- Actual Amendment-062 Git blob: `086e13f063fe79f07be8b4e0668d4a13e843a8d9`
- Missing substring: `a30`
- Missing position: `52` (1-indexed)
- Equality: `false`

The parsed value came directly from the V2 Git object; it was not manually
constructed. Amendment 067 contains the same malformed 61-character value and
was not modified.

Task 124's earlier conclusion `BLOCKED_V3_DEFECT_NOT_REPRODUCED` is withdrawn
by Adjudication 125 and is not reused as evidence.

## V3 authorization

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v3.json`
- Schema: `structured-vol-v5-wgan-authorization-v1`
- Authorization artifact version: `v3`
- Authorization status: `FROZEN_PENDING_INDEPENDENT_AUDIT`
- V3 SHA-256: `19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690`
- V3 Git blob: `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`
- V3 commit: `e6b7b7cdbb79faf0d9548f8a5123e6cffc80d081`
- Self-authentication: `false`

V3 is a new artifact. V1 and V2 were not edited, replaced, renamed, deleted,
or consumed.

## Member, configuration, and randomness

- Member: `wgan-seed-01`
- Role: `PRIMARY`
- Reserve: `false`
- Replicate seed: `8281`
- Model-init seed: `8281`
- Data seed: `8282`
- Evaluation seed: `8283`
- Runtime-config path: `configs/research/structured_vol_wgan_comparator_v1.yaml`
- Runtime-config SHA-256: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`
- Runtime-config Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`
- Canonical `WGANTrainingConfig.config_hash()`: `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58`
- Deterministic run prefix: `ebfbf915ec8316d8`

The seven-role random-source map is:

- model initialization: `8281`;
- training latent/temporal noise: `8282`;
- training ordering: `8282`;
- WGAN-GP interpolation: `8282`;
- internal-selection generated paths: `7777`;
- bootstrap reference: `8801`;
- future post-training evaluation/Gate: `8283`.

No scientific configuration, architecture, optimizer, search, stopping,
checkpoint, seed, split, or Gate semantics changed.

## Frozen identities recomputed from source bytes

- Runner Git blob: `7e020ea937af9e2713451ae735d58c4cbb645289`
- Comparator Git blob: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`
- Model Git blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
- Execution-contract SHA-256: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4`
- Execution-contract Git blob: `194b68797538010f35f5d48a2ec7c4cc4eee533f`
- Execution-recipe head: `c42d14d85fe07d76bfd5551d3ff33dc90d1af704`
- Seed-schedule SHA-256: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`
- Seed-schedule Git blob: `558d08bfee98dbd0c170d65e6a9b1737700c9e98`
- Preregistration SHA-256: `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037`
- Preregistration Git blob: `72311888542ee83ff497b5f0adbbaf6429e8452a`
- Amendment-060 SHA-256: `2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c`
- Amendment-060 Git blob: `a1ba052abe8b4a50887ec84b934e16a328e60596`
- Corrected Amendment-062 SHA-256: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6`
- Corrected Amendment-062 Git blob: `086e13f063fe79f07be8b4e0668d4a13e843a8d9`
- Amendment-066 SHA-256: `c72c96100f760e66473c9e7494b7b7c8550b634008e9c48babf00d1e73bb8e74`
- Amendment-066 Git blob: `a3baab9341e92775616cf1bbd7a77301190cc1a8`

Every SHA-256 field used by V3 was recomputed from source bytes and verified as
64 lowercase hexadecimal characters. Every Git blob and commit/head identity
was verified as 40 lowercase hexadecimal characters.

## Fresh CUDA runtime identity

Captured with `.venv-gpu` using the repository runtime-identity implementation,
without loading scientific data:

- Python: `3.11.9`
- PyTorch: `2.13.0+cu132`
- CUDA runtime: `13.2`
- CUDA available: `true`
- Device: `NVIDIA GeForce RTX 4070 Laptop GPU`
- Compute capability: `8.9`
- cuDNN: `92000`
- Requested device: `cuda`
- Resolved device: `cuda`
- Runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- CPU fallback: `PROHIBITED`
- Relation: `FRESHLY_RECOMPUTED_AND_EQUAL_TO_V2`

## V1 and V2 lineage

### V1

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json`
- SHA-256: `8d889457b48e20b81bd2ef841cd347b1ecd9d79df48d789a03d1ea7c05ac02e8`
- Git blob: `c5e234e5a8efc31f9c882ba451c25d98a606ba9c`
- Technical consumption: `UNCONSUMED`
- Governance entitlement: `EXHAUSTED`
- Reusable: `NO`
- Task-116 result: `NO_RESULT_PRELAUNCH_BLOCK`
- Mutated: `NO`

### V2

- Path: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v2.json`
- SHA-256: `c5eed6098eb681d58ff42bfee7d9660b16da3922991990c1065b2af47fd838ad`
- Git blob: `804d3b42cf9d19a3e27bb090e05cfe219039ceb3`
- Scientific execution attempts: `0`
- Technical consumption: `UNCONSUMED`
- Defect: malformed 61-character Amendment-062 SHA
- Disposition: `SUPERSEDED_UNEXECUTED_IDENTITY_DEFECT`
- Reusable: `NO`
- Mutated: `NO`
- Task-124 former conclusion: `WITHDRAWN_BY_ADJUDICATION_125`

## Repair provenance and permissions

- Task 118: loader-side authorization-path normalization repair;
- Task 120: complete authorization-path propagation and marker-boundary repair;
- Audit 121: `PATH_REPAIR_VALIDATED`;
- Amendment-066: recorded above;
- Final runner identity: `7e020ea937af9e2713451ae735d58c4cbb645289`.

V3 permissions are unchanged:

- `max_scientific_invocations`: `1`;
- `training_authorized`: `true`;
- `validation_authorized`: `false`;
- `final_test_authorized`: `false`;
- `automatic_reserve_execution`: `false`;
- `overwrite`: `false`;
- `relaunch`: `false`;
- authorization consumed: `false`;
- scientific execution performed: `false`.

Runner hash-shape validator hardening: `DEFERRED OUT OF SCOPE TO PRESERVE FINAL RUNNER IDENTITY`.

## Committed V3 verification

V3 was read back from committed Git object `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`.
The current safe library-level functions were used specifically against V3:

- `_normalize_authorization_path`: `PASS`;
- `_load_authorization`: `PASS`;
- `validate_authorization_payload`: `PASS`;
- tracked: `PASS`;
- committed at HEAD: `PASS`;
- clean/equal to HEAD: `PASS`;
- JSON: `PASS`;
- schema: `PASS`;
- runner: `PASS`;
- implementation: `PASS`;
- config: `PASS`;
- methodology: `PASS`;
- execution contract: `PASS`;
- runtime: `PASS`;
- permissions: `PASS`;
- recursive hash-shape audit: `PASS`;
- SHA fields audited: `15`;
- Git blob fields audited: `12`;
- commit/head fields audited: `4`.

Parsed committed V3 Amendment-062 value:

- repr: `'8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6'`;
- length: `64`;
- shape: `true`;
- fresh recomputation: `8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6`;
- equality: `true`.

## Firewalls and state

- Scientific execution: `0`;
- marker: `0`;
- checkpoint: `0`;
- Gate: `0`;
- H2: `UNRESOLVED`;
- scientific validation: `0`;
- external validation: `0`;
- final test: `SEALED`;
- seed-02 authorization: `0`;
- network: `0`;
- push: `0`.

Amendment 067 was not modified. This Amendment 068 intentionally does not
self-hash; its SHA-256 and Git blob are recorded after its separate commit in
the governed report or a later append-only provenance record.

## Status and next governed action

WGAN COMPARATOR: `IMPLEMENTATION_VALIDATED`

WGAN RUNNER: `PATH_REPAIR_VALIDATED`

WGAN SEED-01 AUTHORIZATION V1: `TECHNICALLY_UNCONSUMED_BUT_GOVERNANCE_EXHAUSTED`

WGAN SEED-01 AUTHORIZATION V2: `SUPERSEDED_UNEXECUTED_IDENTITY_DEFECT`

WGAN SEED-01 AUTHORIZATION V3: `FROZEN_PENDING_INDEPENDENT_AUDIT`

WGAN SEED-01 SCIENTIFIC EXECUTION: `NOT PERFORMED`

WGAN SEED-01 EXECUTION READINESS: `NOT_READY_PENDING_V3_AUTHORIZATION_AUDIT`

WGAN SEED-02 AUTHORIZATION: `NOT CREATED`

H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`

FINAL TEST: `SEALED`

Next governed action: independent read-only audit of the corrected seed-01 V3
authorization before scientific execution.

---

*This amendment is append-only and records the identity repair without changing
scientific methodology, source, runner, configuration, or final controls.*
