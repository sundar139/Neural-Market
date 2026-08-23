# V5 WGAN Gate-v2 Evaluator Fail-Closed Authorization Hardening

## Task

- Task ID: `NM-R4-V5-WGAN-GATE-V2-EVALUATOR-FAIL-CLOSED-HARDENING-131`
- Risk: R4
- Expected branch: `main`
- Starting HEAD: `156acafb631f799f01791dbe96b931a5bfdd0d94`
- Prerequisite: `NM-R4-V5-WGAN-GATE-V2-EVALUATOR-IMPLEMENTATION-AUDIT-130`
- Scope: pre-authorization enforcement hardening only.

This amendment is append-only protocol history. Amendments 069 and 070 are
not modified by this task. No Gate authorization was created and no scientific
Gate evaluation was executed.

## Audit-130 findings reproduced

The independent Audit-130 findings were reproducible from the committed
implementation before mutation:

1. Frozen source and configuration identities were read from `HEAD` blobs, but
   the evaluator did not prove that the executable worktree files resolved to
   those same `HEAD` blobs before scientific use. Authorization and evidence
   paths had a narrower check; evaluator, model, comparator, runner, and
   scientific/Gate configuration worktree enforcement was incomplete.
2. `max_scientific_invocations == 1` was validated as a payload value only.
   The Gate evaluator had no exclusive execution-start marker or idempotence
   boundary.
3. SHA-256 values for tracked authorization, evidence, and configuration files
   used raw worktree bytes in identity collection. This made identity depend on
   CRLF/LF materialization.

The findings were reproduced by source tracing and by recomputing tracked
artifact identities from both worktree bytes and committed Git-object bytes.

## Canonical tracked-artifact identity convention

For every tracked committed artifact:

- Canonical SHA-256 is SHA-256 of the bytes returned by `git cat-file blob
  HEAD:<path>`.
- The Git blob ID from `git rev-parse HEAD:<path>` is the primary Git identity.
- Before any scientific Gate work, the current worktree path must be tracked,
  present at `HEAD`, and its filtered Git worktree blob must equal the `HEAD`
  blob. This is checked directly and does not rely only on `git status`.
- Raw CRLF/LF worktree SHA-256 is not the canonical tracked-artifact identity.

For untracked or ignored scientific artifacts, SHA-256 remains SHA-256 of raw
file bytes. This applies to the consumed checkpoint and training execution
marker.

The implementation uses Git path-filtered `hash-object --path` for worktree
blob equivalence, so legitimate CRLF/LF worktree materialization does not
create a false rejection when the Git blob is equivalent.

### Recomputed identities

The training authorization v3 artifact was recomputed from Git object bytes:

- Canonical Git-object-content SHA-256:
  `19c50306ef6849ab2153eaeaec0c7bf80dbcc634aeb58048e0c47dacd77f4690`
- Git blob: `c261b15c8f3ecb99dd1e0a382c1f648b470103fa`
- Current Windows raw-worktree SHA-256:
  `7beec8f279bbd9d56f3bc08d46ee404df770823641ab36f0e851005e8f0499d8`

The raw value `7beec8f2...` is not the canonical future Gate-authorization
identity. The canonical value is `19c50306...` together with blob
`c261b15c...`.

The Task-127 execution evidence was independently recomputed:

- Canonical Git-object-content SHA-256:
  `96489abe4f2c0ca7b2c460b70ecbd2d881fcb5dd6ebea9e62643fe0c36f30e6f`
- Current raw-worktree SHA-256:
  `96489abe4f2c0ca7b2c460b70ecbd2d881fcb5dd6ebea9e62643fe0c36f30e6f`
- Git blob: `21bcd88957ad69e8aef7b9675d308daf697b2ac7`

The equality of the two Task-127 SHA values is observed output, not an
assumption copied from a historical record.

## Worktree enforcement

Before checkpoint loading, CUDA generation, Gate computation, or Gate-start
marker creation, the evaluator now requires Git worktree-to-HEAD equivalence
for:

- evaluator source;
- WGAN model source;
- WGAN comparator source;
- WGAN training runner source;
- WGAN scientific configuration;
- Gate-v2 configuration;
- training authorization v3;
- Task-127 execution evidence.

The tracked WGAN and Gate configuration SHA values are computed from committed
Git-object bytes. Checkpoint, training execution marker, and other untracked
scientific artifacts continue to use raw-file SHA-256. Repository containment
checks remain in force and use resolved paths plus `Path.relative_to`; no
string-prefix containment check is used.

Semantic edits to each tracked executable/configuration input fail closed.
Filtered CRLF/LF-only materialization is accepted when the Git blob equals
`HEAD`. Wrong canonical tracked SHA and wrong tracked Git blob are rejected.

## Exclusive Gate execution boundary

The evaluator now defines an immutable Gate-start marker contract:

- Marker schema: `structured-vol-v5-wgan-gate-execution-start-v1`
- Namespace root: `reports/research/wgan_gate_runs/<member>/<run>/execution_started.json`
- Creation: exclusive `Path.open("x")`, non-overwriting, no retry or relaunch
- Boundary: marker creation occurs after all identity/schema/CUDA preflight and
  before training-split loading, checkpoint scientific use, path generation, or
  Gate metric computation.

The marker payload binds at minimum:

- Gate task and member identity;
- Gate authorization path, Git blob, and canonical Git-object SHA-256;
- checkpoint path and raw SHA-256;
- training execution marker path and raw SHA-256;
- training authorization v3 path, canonical SHA-256, and Git blob;
- Task-127 evidence path, canonical SHA-256, and Git blob;
- evaluator Git blob;
- Gate configuration canonical SHA-256 and Git blob;
- evaluation seed, bootstrap seed, runtime identity, and
  `max_scientific_invocations == 1`;
- UTC timestamp and process identity when available.

A second creation in the same governed namespace fails before scientific work
and cannot overwrite the original marker. No real Seed-01 Gate marker was
created by this task; marker tests use temporary synthetic paths only.

## Scientific contract preservation

The validated WGAN Gate-v2 scientific implementation and math are unchanged.
The following remain frozen:

- evaluation seed: `8283`;
- bootstrap seed: `8801`;
- generated paths: `1024`;
- bootstrap paths/samples: `1024`;
- circular moving-block length: `22`;
- horizon: `63`;
- ACF lags: `[1, 2, 3, 5, 10, 20]`;
- training-only reference/source and context construction;
- WGAN reconstruction and checkpoint semantics;
- finiteness prerequisite;
- variance-ratio, terminal-dispersion, path-uniqueness, and ACF(1)
  agreement criteria;
- report-only metric math;
- `GATE_PASS_VALID` and `GATE_FAIL_VALID` status semantics.

No drift/diffusion decomposition, H2 calculation, automatic reserve behavior,
training, retraining, refit, final-test access, or scientific Gate execution was
added.

## Verification record

Source/test repair commit:

- `fix(research): harden wgan gate authorization boundary`
- Commit: `0cade7701a029a7e757c2a03d5a6d1807e8fc94d`

Implementation identities after the repair commit:

- evaluator Git blob: `f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`;
- evaluator test Git blob: `77b667330daac90fc3bf3833233cc0d855d38308`;
- training runner Git blob: `7e020ea937af9e2713451ae735d58c4cbb645289` (unchanged).

Focused evaluator verification after repair:

- command: `.venv/Scripts/python.exe -m pytest tests/unit/research/test_wgan_gate_evaluator.py`;
- result: `30 passed in 4.19s`;
- exit: `0`.

Ruff passed for the evaluator and tests. Mypy passed for the evaluator.
Regression coverage includes semantic dirty rejection for evaluator/model/
comparator/runner/config inputs, CRLF tolerance, canonical SHA/blob binding,
exclusive first/second marker behavior, max-invocation validation, marker
ordering before scientific work, and preservation firewalls. All Gate tests
remain synthetic/mock-only.

## Governed statuses

- WGAN comparator: `IMPLEMENTATION_VALIDATED`
- WGAN training runner: `PATH_REPAIR_VALIDATED`
- WGAN Seed-01 scientific training: `VALID_COMPLETED_TRAINING`
- WGAN Seed-01 scientific result: `VALID_EXECUTION_NO_GATE_RESULT`
- WGAN Seed-01 Gate evaluator: `HARDENED_PENDING_INDEPENDENT_AUDIT`
- WGAN Seed-01 Gate authorization: `NOT CREATED`
- WGAN Seed-01 Gate execution: `NOT PERFORMED`
- WGAN Seed-02 authorization: `NOT CREATED`
- H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`
- Final test: `SEALED`

Amendment self-identity is intentionally not recorded in this amendment.
The amendment is committed separately from the source/test repair and must not
be self-hashed.
