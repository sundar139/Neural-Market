# Amendment 063 — V5 WGAN Seed-01 Scientific Execution Authorization Freeze

Date: 2026-08-22
Status: APPEND-ONLY AUTHORIZATION FREEZE RECORD

## Task identity

- Task: NM-R4-V5-WGAN-SEED-01-AUTHORIZATION-FREEZE-114
- Risk: R4
- Prerequisite: NM-R2-V5-REMOTE-PUSH-PROVENANCE-INVESTIGATION-113
- Prerequisite verdict: REMOTE_WRITE_SOURCE_IDENTIFIED_AND_CONTROLLED
- Starting branch: main
- Starting HEAD: fccbf3c108b3feb543c50d4a5efed9d6caea6094
- Authorization commit: 30de7b32ff54670edbc07dec669f00445c518c8c
- WGAN source changes: 0
- WGAN test changes: 0

This amendment records authorization only. It does not authorize or report
scientific execution, validation, Gate, H2, or final-test activity.

## Target member and frozen seed tuple

- Member: wgan-seed-01
- Role: PRIMARY
- Reserve: false
- Replicate seed: 8281
- Model-init seed: 8281
- Data seed: 8282
- Evaluation seed: 8283

Only wgan-seed-01 is authorized by the committed artifact. No reserve or other
WGAN member authorization was created.

## Effective configuration identity

- Runtime configuration: configs/research/structured_vol_wgan_comparator_v1.yaml
- Runtime-config SHA-256: de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7
- Runtime-config Git blob: e0740afc24697f2eab3620a4243d04411aa508cb
- Canonical WGANTrainingConfig.config_hash(): 31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58
- Deterministic member run prefix: ebfbf915ec8316d8

The WGAN runner's required `effective_config_sha256` field binds the committed
runtime-config file SHA above. The member-specific canonical
`WGANTrainingConfig.config_hash()` is recorded separately as `full_config_hash`.
No config value or config-hashing implementation was changed.

Frozen scientific values include:

- Generator and critic hidden width: 64, bound by the implementation identity
- Latent dimension: 32
- Horizon: 63
- dt: 1/252
- Batch size: 64
- Optimizer: Adam
- Learning rate: 1e-4
- Adam betas: 0.0 / 0.9
- Gradient-penalty coefficient: 10
- Critic/generator update ratio: 5
- Maximum generator epochs: 400
- Patience: 40
- Internal-selection generated-path seed: 7777, bound by comparator identity and Amendment 062
- Real circular/moving-block bootstrap seed: 8801
- Future post-training evaluation/Gate seed: 8283
- Block length: 22
- Selection paths: 1024
- Real-reference paths: 1024
- Member model-init seed: 8281
- Member training/refit data seed: 8282

## Comparator methodology and implementation identities

No new methodology hash was invented. The comparator methodology is bound by
this immutable controlling identity set:

- Preregistration SHA-256: 6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037
- Preregistration Git blob: 72311888542ee83ff497b5f0adbbaf6429e8452a
- Amendment 060 SHA-256: 2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c
- Amendment 060 Git blob: a1ba052abe8b4a50887ec84b934e16a328e60596
- Amendment 062 SHA-256: 8befe31d08b52776fcf18fd15eacaed5fcc9ef90e06ac8b0e07a30d3aca96fa6
- Amendment 062 Git blob: 086e13f063fe79f07be8b4e0668d4a13e843a8d9
- Amendment 062 role: implementation-conformance provenance; not a methodology change

Current implementation bindings:

- WGAN model blob: 2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe
- WGAN comparator blob: 87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b
- WGAN runner blob: 2e87199a2237b4f23576fa181a38ba29807c8ae2

## Seed schedule, execution contract, and recipe identity

- Seed-schedule SHA-256: 8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0
- Seed-schedule Git blob: 558d08bfee98dbd0c170d65e6a9b1737700c9e98
- Execution contract: reports/research/structured_vol_v5_wgan_execution_contract_v1.json
- Execution-contract SHA-256: 4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4
- Execution-contract Git blob: 194b68797538010f35f5d48a2ec7c4cc4eee533f
- Execution-recipe head: fccbf3c108b3feb543c50d4a5efed9d6caea6094
- Execution-recipe identity: current committed execution-recipe head
- Separate WGAN recipe specification: none; none was created

The runner requires the `execution_recipe_head` field. The authorization binds
the current committed recipe head and does not invent a new recipe
specification. The current validator requires the field but does not compare it
to a separate recipe artifact.

## Fresh production CUDA runtime identity

Captured read-only from:

C:\Users\rohit\Documents\Personal Projects\Neural Market\.venv-gpu

- Python: 3.11.9
- PyTorch: 2.13.0+cu132
- torch.version.cuda: 13.2
- CUDA available: true
- GPU: NVIDIA GeForce RTX 4070 Laptop GPU
- Compute capability: 8.9
- cuDNN: 92000
- NVIDIA driver: 610.47
- Deterministic algorithms: true
- cuDNN benchmark: false
- cuDNN deterministic: true
- Requested device: cuda
- Resolved device: cuda
- Runtime identity schema: runtime-identity-v1
- Runtime identity SHA-256: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Relation to historical Neural-SDE runtime identity 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada: FRESHLY_RECOMPUTED_AND_EQUAL
- CPU fallback: prohibited

Runtime capture did not load market data, train, create a checkpoint, create an
execution marker, consume authorization, or run Gate.

## Authorization artifact

- Path: reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json
- Schema: structured-vol-v5-wgan-authorization-v1
- Authorization SHA-256: 8d889457b48e20b81bd2ef841cd347b1ecd9d79df48d789a03d1ea7c05ac02e8
- Authorization Git blob: c5e234e5a8efc31f9c882ba451c25d98a606ba9c
- Authorization status: FROZEN_PENDING_INDEPENDENT_AUDIT
- Maximum scientific invocations: 1
- Training authorized: true
- Validation authorized: false
- Final-test authorized: false
- Automatic reserve execution: false
- Overwrite: false
- Relaunch: false
- Self-authentication: false

The authorization binds the target member, seed tuple, canonical config hash,
runtime-config identity, methodology identity set, Amendment-062
implementation-repair provenance, seed schedule, implementation blobs, runner,
execution contract, execution-recipe head, and fresh CUDA runtime identity.

## Offline verification

- JSON syntax: PASS
- WGAN runner authorization validation: PASS
- Post-commit committed-artifact validation: PASS
- Read-only dry-run: PASS
- Dry-run classification: NON_SCIENTIFIC_TEST_ONLY
- Dry-run output: training=NOT_INVOKED; validation=PROHIBITED; final_test=PROHIBITED
- Market-data access: 0
- Training: 0
- Simulation: 0
- Execution marker: 0
- Checkpoint: 0
- WGAN scientific namespace: absent
- Gate: 0
- H2: 0
- Authorization consumed: 0
- Authorization bytes mutated by dry-run: 0
- Historical marker hashes mutated by dry-run: 0

The dry-run was the runner's single read-only dry-run invocation. It did not
consume the authorization or create scientific outputs.

## Task-113 publication provenance context

This is context only and does not establish a broad publication policy:

- Remote publication source: GitHub Desktop manual UI action
- Autonomous push path: none identified
- Task-114 push: 0

## Governance and firewall state

- Authorization creation: exactly 1 WGAN member artifact; wgan-seed-01 only
- Scientific training: 0
- Scientific simulation: 0
- Scientific checkpoint: 0
- Execution marker: 0
- Gate: 0
- H2 calculation: 0
- Validation: 0
- External validation: 0
- Final test: 0
- Data acquisition: 0
- Provider/scientific network: 0
- Git-remote network: 0
- Push: 0
- Amend: NO
- Rebase: NO
- Reset: NO

- WGAN comparator: IMPLEMENTATION_VALIDATED
- WGAN authorization: FROZEN_PENDING_INDEPENDENT_AUDIT
- WGAN scientific execution: NOT PERFORMED
- H2: UNRESOLVED_PENDING_WGAN_COMPARATOR
- Final test: SEALED

This amendment is append-only and does not self-hash. The amendment's own
SHA-256 and Git blob are intentionally recorded only after its bytes are
committed, in the governed task report or a later append-only record.
