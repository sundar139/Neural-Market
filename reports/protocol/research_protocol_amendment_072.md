# Amendment 072 — V5 WGAN Seed-01 Gate-v2 Authorization Freeze

Date: 2026-08-23
Status: APPEND-ONLY AUTHORIZATION FREEZE RECORD

## Task and governing boundary

- Task: `NM-R4-V5-WGAN-SEED-01-GATE-V2-AUTHORIZATION-FREEZE-133`
- Risk: `R4`
- Branch: `main`
- Starting HEAD: `1ead13849714340475656ad278755de83cc914d6`
- Prerequisite audit: `NM-R4-V5-WGAN-GATE-V2-FAIL-CLOSED-HARDENING-AUDIT-132`
- Prerequisite verdict: `VALIDATED_HARDENED`
- Governed transitions: `DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`
- Safety branch, created without switching: `safety/pre-wgan-seed01-gate-auth-1ead138`
- Safety branch ref: `1ead13849714340475656ad278755de83cc914d6`

This amendment records exactly one separately frozen future Gate-v2
execution entitlement for the existing valid seed-01 WGAN checkpoint. It does
not execute the Gate, create the execution marker, train or retrain, mutate a
checkpoint, authorize seed-02, reserve an authorization, calculate H2, access
validation or final-test data, or push to any remote.

## Frozen Gate authorization

- Authorization path:
  `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-01-gate-v2-v1.json`
- Authorization schema: `structured-vol-v5-wgan-gate-authorization-v1`
- Authorization artifact version: `v1`
- Authorization commit:
  `2eca5816bd37fdc7faa4dec63c57b8e4da13dd7f`
- Authorization canonical SHA-256 of committed Git-object bytes:
  `215c307028e5f8a5cf7f25e4277cbf965a81d85aed0c6dfd71164e1439c06a32`
- Authorization Git blob: `b6960813f843160f4eadd05cce05cf069f0cf0e1`
- Member: `wgan-seed-01`
- Role: `PRIMARY`
- Future Gate task ID:
  `NM-R5-V5-WGAN-SEED-01-GATE-V2-EXECUTION-135`
- Gate execution marker path:
  `reports/research/wgan_gate_runs/wgan-seed-01/gate-v2-execution-135/execution_started.json`
- Gate marker preexisting at freeze: `false`
- Gate marker path validation: `VALID`

The authorization licenses exactly one Gate scientific invocation. Its
`max_scientific_invocations` value is `1`; `overwrite`, `relaunch`, and retry
are prohibited. Creation of the frozen marker is the irreversible
scientific-start boundary and permanently consumes the entitlement. There is
no retry, relaunch, rerun, overwrite, or automatic second Gate authorization.
Marker exclusivity is scoped to this frozen authorization and run path. Any
future replacement authorization would require a separate explicit governed
decision and may not revive this entitlement.

## Seed-01 training provenance bound by the authorization

- Current scientific result: `VALID_EXECUTION_NO_GATE_RESULT`
- Checkpoint:
  `data/processed/research/model/wgan-comparator/wgan-seed-01/ebfbf915ec8316d8/checkpoint.pt`
- Checkpoint raw SHA-256:
  `332614157e2c1d30e6a5fd043cb893b36c508e4ab2603b07642e0d66ddb7718e`
- Selected epoch: `63`
- Best internal-selection metric: `3.0610572388897204`
- Canonical WGAN config hash:
  `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58`
- Training execution marker:
  `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/`\
  `execution_started.json`
- Training execution marker raw SHA-256:
  `18d246aa4d3146092a3df5ee243492f7e9859f2fb61c7b82d8f6d1f84d907be1`
- Training authorization v3:
  `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v3.json`
- Training authorization v3 canonical SHA-256:
  `19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690`
- Training authorization v3 Git blob: `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`
- Task-127 execution evidence:
  `reports/research/evidence/structured_vol_v5_wgan_seed01_execution_v3_127.json`
- Task-127 evidence canonical SHA-256:
  `96489abe4f2c0ca7b2c460b70ecbd2d881fcb5dd6ebea9e62643fe0c36f30e6f`
- Task-127 evidence Git blob: `21bcd88957ad69e8aef7b9675d308daf697b2ac7`
- Training report:
  `reports/research/wgan_comparator_runs/wgan-seed-01/ebfbf915ec8316d8/training_report.json`
- Training report raw SHA-256:
  `bd8e4dd5fc656d50933d7200b93b392636fbd644a19225b41a48b61e457840dc`

## Source and configuration identities

The following identities were recomputed from their actual current sources at
freeze time and bound into the authorization:

- Final Gate evaluator Git blob:
  `f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`
- WGAN model Git blob:
  `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
- WGAN comparator Git blob:
  `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`
- Consumed training runner Git blob:
  `7e020ea937af9e2713451ae735d58c4cbb645289`
- WGAN scientific config:
  `configs/research/structured_vol_wgan_comparator_v1.yaml`
- WGAN scientific config canonical SHA-256:
  `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`
- WGAN scientific config Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`
- Gate-v2 config:
  `configs/research/neural_sde_internal_gate_v2.yaml`
- Gate-v2 config canonical SHA-256:
  `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`
- Gate-v2 config Git blob: `d9705ef9a11da3e21760015bb2a27fa408018bb5`
- Loaded Gate-v2 specification hash:
  `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469`

## Gate-v2 contract

- Evaluation seed: `8283`
- Bootstrap seed: `8801`
- Generated paths: `1024`
- Bootstrap paths: `1024`
- Horizon: `63`
- Circular moving-block length: `22`
- ACF lags: `[1, 2, 3, 5, 10, 20]`
- Requested device: `cuda`
- Expected resolved device: `cuda`
- Finiteness: validity prerequisite; nonfinite or structurally invalid output
  fails closed.
- Discriminating architecture-neutral criteria:
  - variance ratio in `[0.50, 2.00]`;
  - terminal dispersion ratio in `[0.50, 2.00]`;
  - rounded path uniqueness `>= 0.99`;
  - absolute lag-1 ACF difference `<= 0.25`.
- Report-only metrics:
  - normalized terminal Wasserstein distance;
  - ACF RMSE;
  - maximum ACF error;
  - absolute-return ACF at the frozen lags;
  - squared-return ACF at the frozen lags;
  - conditional-variance log-correlation.
- Explicitly excluded from WGAN pass/fail:
  - selection-loss criteria;
  - internal-RBF criteria;
  - `drift_diffusion_rms_ratio`;
  - any fabricated WGAN drift/diffusion decomposition.

A finite structurally valid Gate evaluation may end only as
`GATE_PASS_VALID` or `GATE_FAIL_VALID`. Both are numerically valid and
included completed model members. A valid poor result may not be discarded and
may not trigger retry, relaunch, rerun, retraining, checkpoint replacement,
reserve execution, seed-02 authorization, H2, or final-test access.

## Fresh CUDA runtime identity

The repository runtime-identity builder was run in `.venv-gpu` after applying
the evaluator's deterministic CUDA configuration and before authorization
construction:

- Python: `3.11.9`
- PyTorch: `2.13.0+cu132`
- CUDA: `13.2`
- CUDA available: `true`
- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
- Capability: `8.9`
- cuDNN: `92000`
- Requested: `cuda`
- Resolved: `cuda`
- Deterministic algorithms: `true`
- cuDNN benchmark: `false`
- cuDNN deterministic: `true`
- Runtime identity:
  `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- CPU fallback: `PROHIBITED`

## Identity convention and v3 distinction

For tracked artifacts:

- canonical SHA-256 is SHA-256 of the exact committed Git-object bytes at
  `HEAD:<path>`;
- Git identity is the `HEAD` Git blob;
- the path-filtered worktree Git blob must equal the `HEAD` blob.

For untracked or ignored scientific artifacts, SHA-256 is SHA-256 of raw file
bytes. The checkpoint and training execution marker use this raw-file rule.

The v3 training authorization's raw Windows worktree SHA-256
`7beec8f279bbd9d56f3bc08d46ee404df770823641ab36f0e851005e8f0499d8` is **not**
the canonical authorization identity. The canonical v3 identity is SHA-256
`19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690` with Git
blob `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`.

## Verification and firewalls

The authorization was read back from its committed Git object and validated
read-only with the hardened evaluator helpers. The committed artifact passed
schema, member, checkpoint, training-marker, training-authorization,
Task-127-evidence, source-identity, evaluator, Gate-config, seed,
sample-parameter, runtime, permission, and marker-path checks. The Gate CLI
was not invoked and no Gate marker or Gate result was created.

Audit-132 caveat preserved: marker exclusivity is authorization/run-path
scoped. No second Gate authorization is an automatic retry mechanism.

Counts at this freeze:

- Gate execution: `0`
- Gate marker: absent
- Gate result: absent
- Training execution: `0`
- Checkpoint mutation: `0`
- Seed-02 authorization: `0`
- Reserve authorization: `0`
- H2: `0`; status `UNRESOLVED_PENDING_WGAN_COMPARATOR`
- Validation: `0`
- External validation: `0`
- Final-test access: `0`
- Git network: `0`
- Push: `0`

Amendments 069, 070, and 071 remain unchanged. This amendment is append-only
and intentionally contains no self-hash.

## Status

- WGAN comparator: `IMPLEMENTATION_VALIDATED`
- WGAN training runner: `PATH_REPAIR_VALIDATED`
- WGAN Seed-01 scientific training: `VALID_COMPLETED_TRAINING`
- WGAN Seed-01 scientific result: `VALID_EXECUTION_NO_GATE_RESULT`
- WGAN Seed-01 Gate evaluator: `VALIDATED_HARDENED`
- WGAN Seed-01 Gate authorization: `FROZEN_PENDING_INDEPENDENT_AUDIT`
- WGAN Seed-01 Gate execution: `NOT PERFORMED`
- WGAN Seed-02 authorization: `NOT CREATED`
- H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`
- Final test: `SEALED`
- Push: `0`

Next governed action: `NM-R4-V5-WGAN-SEED-01-GATE-V2-AUTHORIZATION-AUDIT-134`
(strictly read-only). Seed-02 remains unauthorized.
