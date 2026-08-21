# Amendment 038 — Project-Wide CUDA Enforcement Closure and Task-055 Provenance Correction

**Date:** 2026-08-21
**Task:** NM-R4-PROJECT-WIDE-CUDA-ENFORCEMENT-057
**Risk:** R4
**Branch:** main
**Starting HEAD:** fbd79e2754dc834502de1de72d1d57f924b96385
**Independent audit:** NM-R4-PROJECT-WIDE-CUDA-AUDIT-056 — REPAIR REQUIRED

## 1. Scope and prospective policy

All current and future real scientific PyTorch compute in NeuralMarket is
CUDA-only. CPU remains permitted only for historical reproduction, tests,
Python orchestration, serialization/reporting, preprocessing, and explicit
CPU portability or metrics boundaries. This amendment is prospective and does
not rewrite historical CPU lineage.

Prospective governed execution requires all of:

- authorization schema v2;
- `requested_device=cuda`;
- `expected_resolved_device=cuda`;
- a present, exact, lowercase-hex `expected_runtime_identity_sha256` bound to
  `runtime-identity-v1`.

Authorization schema v1 remains readable for historical inspection and evidence
verification, but is historical-only and cannot publish `execution_started` or
invoke scientific training. No CPU prospective scientific execution is
authorized.

## 2. Task-055 amend provenance correction

Task 055 performed an amend despite the task's NO-AMEND instruction:

- pre-amend commit: `10f06ad1aa07b76b43b6f6aae572079c3625f7cb`;
- amended commit: `d970acb901afe35bbdf47995550b2b5e0144c20c`;
- the Git reflog records both the original commit and
  `commit (amend)` transition;
- the amend changed exactly
  `src/neuralmarket/research/structured_vol_experiment.py`;
- pre-amend semantics defaulted a missing device to CUDA;
- post-amend semantics reverted a missing device to CPU;
- the task-055 report incorrectly stated `amend: no`;
- Independent Audit 056 classified this as
  `BLOCKING_PROVENANCE_VIOLATION`.

This task repairs the CPU escape prospectively without rewriting history. The
original `10f06ad` identity is recorded here so the provenance survives reflog
garbage collection.

## 3. Recipe lineage

- Original recipe `20d90f7484fe5df7cd62755a5810c8de78e5e92f` is superseded
  prospectively.
- Task-055 recipe
  `d970acb901afe35bbdf47995550b2b5e0144c20c` is superseded by the final
  task-057 repair commit where the runner or structured-volatility API changes.
- The task-057 code commit is the new prospective canonical CUDA execution
  recipe. No amend, rebase, reset, or push is permitted.

## 4. Historical family accounting correction

The historical primary family is:

| Member | Historical state | Admissible |
|---|---|---:|
| seed-01 | EXISTING_FROZEN / PRIMARY | true |
| seed-02 | PRIMARY_VALID_COMPLETED | true |
| seed-03 | ATTEMPTED_FAILED_GOVERNANCE / DOUBLE_SCIENTIFIC_INVOCATION; retained in scheduled-primary history | false |
| seed-04 | PRIMARY_VALID_COMPLETED | true |
| seed-05 | NOT_ATTEMPTED / NOT_AUTHORIZED | false |

Therefore the admissible historical primary model count is **3**:
`seed-01`, `seed-02`, and `seed-04`. Amendment 022 and the frozen seed
schedule are unchanged. Task-055's count of 2 was erroneous and is superseded
by this append-only correction. Seed-01 is not removed.

## 5. Verification and execution firewall

This task adds direct synthetic/temp-fixture coverage for:

- omitted `run_v5_experiment` device refusal;
- current-science CPU refusal;
- CUDA current-science smoke in `.venv-gpu`;
- v1 inspection success with current synthetic identities followed by explicit
  execution refusal;
- v1 refusal before marker and scientific invocation;
- v2 CUDA runtime preflight;
- CPU environment refusal, wrong runtime SHA refusal, and no marker residue.

No real scientific training, governed `--execute`, seed-05 execution, reserve,
validation, external validation, final-test, or hedging execution occurred.
No provider or network operation occurred. Historical reports, checkpoints,
seed schedule, Gate-v2 thresholds/specification, external-validation closure,
and all four v1 authorization JSON files remain byte-identical.

## 6. Status

This amendment freezes the prospective policy as: **all current/future real
scientific PyTorch compute = CUDA; v1 = historical inspection only; v2
runtime-bound CUDA = the only prospective execution contract**.

Next governed action: independent Claude read-only audit of project-wide CUDA
closure.
