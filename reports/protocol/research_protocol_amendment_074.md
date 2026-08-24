# Amendment 074 — V5 WGAN Prospective Training Diagnostic Persistence

Date: 2026-08-23
Task: `NM-R4-V5-WGAN-TRAINING-DIAGNOSTIC-PERSISTENCE-HARDENING-137`
Risk: `R4`
Branch: `main`
Starting HEAD: `57728b54b55c0d8eeeda747d2c7837a7f38ed552`
Prerequisite audit: `NM-R5-V5-WGAN-SEED-01-GATE-V2-EXECUTION-AUDIT-136`
Prerequisite result: seed-01 `VALID_COMPLETED_MEMBER`; Gate `GATE_FAIL_VALID`;
scientific result `GATE_FAIL_VALID`; WGAN family currently has one valid completed
member of fixed denominator five.

Status: APPEND-ONLY PROSPECTIVE ENGINEERING HARDENING — no WGAN training, Gate,
authorization, validation, H2 calculation, or final-test access.

## 1. Trigger and governing boundary

The trigger is Audit 136 carrying forward Audit-128's finding that the WGAN
training loop computed several Amendment-059 secondary diagnostics in process
memory but the Task-127 runner did not persist them in
`training_report.json`.

The governed transitions were:

`DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT`

Seed-01 already completed under the historical runner and is immutable. This
amendment changes only prospective persistence for future WGAN members. It does
not create an authorization and does not permit seed-02 or any other scientific
process.

## 2. Seed-01 historical semantics

Seed-01 remains:

- status: `VALID_COMPLETED_MEMBER`;
- Gate: `GATE_FAIL_VALID`;
- scientific result: `GATE_FAIL_VALID`;
- training diagnostics: `MISSING_BY_DESIGN_HISTORICAL`;
- historical runner Git blob: `7e020ea937af9e2713451ae735d58c4cbb645289`;
- training report: unchanged at its original 797-byte artifact;
- reconstruction: prohibited;
- imputation: prohibited;
- retraining/rerun: prohibited.

No seed-01 checkpoint, training marker, Gate marker, Task-127 evidence,
Task-135 evidence, Amendment 069, or Amendment 073 was modified. Future family
analysis must represent seed-01 diagnostic values as missing historical data and
must not include fabricated values in diagnostic summaries.

## 3. Discovery and availability map

The committed flow was traced from critic update, generator update, gradient
penalty, selection evaluation, early stopping, checkpoint selection, refit,
`WGANTrainingOutcome`, and the runner's `training_report.json` write.

| Amendment-059 diagnostic | Prior availability | Exact prospective source/semantics |
|---|---|---|
| `critic_loss_curve` | `ALREADY_COMPUTED_NOT_PERSISTED` | Existing `WGANTrainingOutcome.critic_loss_curve`, serialized without recomputation. |
| `generator_loss_curve` | `ALREADY_COMPUTED_NOT_PERSISTED` | Existing `WGANTrainingOutcome.generator_loss_curve`, serialized without recomputation. |
| `gradient_penalty_curve` | `ALREADY_COMPUTED_NOT_PERSISTED` | Existing `WGANTrainingOutcome.gradient_penalty_curve`, serialized without recomputation. |
| `selection_metric_curve` | `ALREADY_COMPUTED_NOT_PERSISTED` | Existing internal-selection history, serialized with selected epoch, selected metric, final epoch, and early-stop state. |
| `critic_update_count` | `DERIVABLE_EXACTLY_FROM_EXISTING_COUNTERS` | Exact count of successful critic optimizer steps, incremented only at the existing optimizer-step boundary. |
| `generator_update_count` | `DERIVABLE_EXACTLY_FROM_EXISTING_COUNTERS` | Exact count of successful generator optimizer steps, incremented only at the existing optimizer-step boundary. |
| training completion | `ALREADY_COMPUTED_NOT_PERSISTED` | Successful return of `train_wgan_internal` is serialized as `COMPLETED`. |
| finite/nonfinite diagnostic state | `ALREADY_COMPUTED_NOT_PERSISTED` | Existing fail-closed finite checks and successful outcome are serialized as `FINITE`; no failure value is fabricated. |
| checkpoint-selection stability | `ALREADY_COMPUTED_NOT_PERSISTED` | Existing selection curve and checkpoint state are serialized; no new metric is introduced. |
| `mode_collapse_indicator` | `NOT_CURRENTLY_AVAILABLE_WITHOUT_SCIENTIFIC_BEHAVIOR_CHANGE` | No committed definition or computation exists; serialized as unavailable with null value. |

The unavailable mode-collapse field is not inferred from path outputs, losses,
or selection values. Adding a scientific mode-collapse calculation would require
a separate governance decision and is outside this hardening.

## 4. Prospective report contract

Future successful WGAN reports at
`reports/research/wgan_comparator_runs/<member>/<run>/training_report.json` now
include `training_diagnostics` with schema:

`structured-vol-v5-wgan-training-diagnostics-v1`

The record contains, at full serialized floating-point precision:

- `critic_loss_curve`;
- `generator_loss_curve`;
- `gradient_penalty_curve`;
- exact `critic_update_count`;
- exact `generator_update_count`;
- `training_completion` with status, final generator epoch, and fit-window count;
- `finite_nonfinite` status;
- `checkpoint_selection` with selection curve, selected epoch, selected metric,
  final epoch, and early-stop state;
- `mode_collapse_indicator` with status
  `NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE` and value `null`;
- `historical_missingness.wgan-seed-01` with status
  `MISSING_BY_DESIGN_HISTORICAL` and value `null`;
- an availability map using `PRESENT`,
  `MISSING_BY_DESIGN_HISTORICAL`, and
  `NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE`.

The serializer is observational-only. It reads values already in the outcome,
performs no model forward pass, consumes no scientific RNG, performs no
optimizer step, changes no model state, and does not access data.

## 5. Scientific preservation

The following remain unchanged in byte or semantic behavior:

- WGAN model architecture and initialization;
- Adam optimizer, learning rate, betas, epsilon, and weight decay;
- critic/generator ratio `5:1`;
- batch size, batch order, and training data;
- model-init seed `8281` convention and training RNG semantics;
- temporal-noise, window-order, and gradient-penalty RNG streams;
- selection generated-path seed `7777`;
- bootstrap seed `8801`;
- future evaluation seed `8283`;
- finite checks;
- early stopping, patience, and `min_delta`;
- selection metric and checkpoint tie-breaking;
- selected epoch semantics;
- refit epoch count, data, seed, and model states;
- checkpoint scientific tensors and format;
- Gate evaluator and Gate-v2 methodology;
- scientific WGAN configuration.

No additional forward pass, update, optimizer step, RNG call, validation access,
final-test access, or Gate computation was introduced.

## 6. Source and test implementation

Only these tracked files changed:

- `src/neuralmarket/research/wgan_comparator.py` — outcome fields and exact
  optimizer-step counters at existing update boundaries;
- `src/neuralmarket/research/wgan_runner.py` — pure prospective diagnostic
  serialization and report integration;
- `tests/unit/research/test_wgan_runner.py` — exact serialization, precision,
  missingness, and no-scientific-operation regression checks.

Implementation commit:
`2e0adec7277ae19407976f3515c161e9096d04ba`

Source identities after the implementation commit:

- old runner blob: `7e020ea937af9e2713451ae735d58c4cbb645289`;
- new runner blob: `56a1370cb3b76d5849083c175a3d98bc6a390261`;
- old comparator blob: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`;
- new comparator blob: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`;
- model blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`;
- Gate evaluator blob: `f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`;
- test blob: `15469e43833386e2e61a0fb83bf6fc0125b5ceef`.

The WGAN scientific configuration remains unchanged:

- effective config hash: `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58`;
- runtime-config SHA-256: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`;
- runtime-config Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`.

## 7. Verification chronology and firewalls

Regression tests were written before source mutation and failed against the old
outcome/report contract. After implementation, the final focused command was:

`.venv/Scripts/python.exe -m pytest tests/unit/research/test_wgan_comparator.py tests/unit/research/test_wgan_runner.py -q`

Final focused result: `40 passed`.

Static checks:

- Ruff on the two changed source files and two affected test files: passed;
- mypy on the two changed source files: passed.

No real WGAN training was run. No Gate was run. No seed-02 or reserve
authorization was created. No checkpoint, training marker, Gate marker, training
report, Task-127 evidence, Task-135 evidence, Amendment 069, or Amendment 073
was edited. H2 remains unresolved and the final test remains sealed.

The remaining required full repository test run occurs after this amendment is
committed and is not represented as completed by this amendment text.

## 8. Required status and next action

`WGAN SEED-01: VALID_COMPLETED_MEMBER / GATE_FAIL_VALID / HISTORICAL_DIAGNOSTIC_MISSINGNESS`

`WGAN TRAINING DIAGNOSTIC PERSISTENCE: HARDENED_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-02 AUTHORIZATION: NOT CREATED`

`H2: UNRESOLVED_PENDING_WGAN_COMPARATOR`

`FINAL TEST: SEALED`

Next governed action: full repository verification followed by an independent
read-only audit of prospective WGAN training diagnostic persistence before any
seed-02 authorization freeze.

This amendment is append-only and intentionally contains no self-hash.
