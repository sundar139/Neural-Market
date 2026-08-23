# Amendment 060 — V5 WGAN H2 Primary-Metric Denominator Clarification

**Date:** 2026-08-22
**Task:** `NM-R4-V5-WGAN-H2-DENOMINATOR-CLARIFICATION-107`
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `7ce14265008093941ce7a7764ec30dde74958961`
**Prerequisite audit:** `NM-R2-V5-STALE-SEED05-AUTHORIZATION-TEST-AUDIT-106`
**Prerequisite verdict:** `VALIDATED WITH NON-BLOCKING FINDINGS`
**Trigger:** Audit-104 non-blocking finding 1, carried forward by Audit 106 as a required pre-implementation clarification.
**Status:** APPEND-ONLY METHODOLOGY CLARIFICATION — frozen before WGAN implementation or any WGAN result.

## 1. Purpose and governing boundary

This amendment resolves one prospective ambiguity in the preregistered H2
comparison. It clarifies the population and denominator for the two
attempt-level primary metrics without changing the H2 decision rule, secondary
metrics, completed-member statistics, architecture, compute budget, or any
scientific artifact.

The governing transitions are:

`DISCOVER -> DECIDE -> FREEZE -> VERIFY -> REPORT`

The frozen state before this clarification is:

- repository test baseline: `GREEN`;
- WGAN comparator: `PREREGISTRATION_VALIDATED`;
- WGAN implementation: `NOT_STARTED`;
- WGAN execution: `0`;
- H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`;
- final chronological test: `SEALED`.

This amendment creates no WGAN source, implementation, configuration, runner,
authorization, training invocation, simulation, Gate result, validation result,
external-validation result, final-test access, N4/N5 recomputation, or WGAN
result. The five WGAN primary identities remain `SCHEDULED_NOT_RUN`, and the
three reserve identities remain frozen but not authorized.

## 2. Frozen records and ambiguity reconstruction

The controlling records are:

- `reports/protocol/research_protocol_v1.md`, lines 99–100 and 105, requiring at least five independent neural seeds, failed-seed reporting, and separate training-seed and market-period uncertainty;
- `reports/protocol/research_protocol_amendment_020.md`, §§2.4, 4.1, 4.4, and 8, requiring a five-member stability family before an H2 claim;
- `reports/protocol/research_protocol_amendment_021.md`, §§10–14, requiring separate attempted and valid-completed counts and reserving denominator choice for the later SAP;
- `reports/protocol/research_protocol_amendment_022.md`, §§9–13, preserving permanent primary failures, separate reserve accounting, and the under-filled-family rule;
- `reports/protocol/research_protocol_amendment_029.md`, §Six-Criterion Rule, stating that a failed primary stays in the denominator;
- `reports/protocol/research_protocol_amendment_048.md`, §§2–4, distinguishing the permanent primary roster from a separately identified completed-model analytical set that may include reserve-j01;
- `reports/protocol/research_protocol_amendment_055.md`, §§7–8, freezing the completed-member status semantics and five-member family convention;
- `reports/protocol/research_protocol_amendment_059.md`, §§6–7, and the machine-readable preregistration `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json`.

The direct metric wording in Amendment 059 §7.1 and the machine-readable
contract names the first two metrics as completion/finite stability metrics:

1. `valid_completed_member_fraction` — “Valid completed primary members divided by five.”
2. `nonfinite_or_missing_checkpoint_rate` — “Fraction of primary attempts with nonfinite training/selection values or no valid checkpoint.”

The same preregistration also contains a generic family-aggregation sentence:

> For each family and each metric, use the five valid completed member values in fixed roster order; report arithmetic mean, sample SD with `ddof=1`, median, minimum, and maximum.

That generic sentence is explicit for completed-member values and summaries, but
it does not say whether it overrides the direct “primary attempts” wording for
`nonfinite_or_missing_checkpoint_rate`, or whether it changes the denominator
of `valid_completed_member_fraction`. Consequently, two readings were
plausible before this amendment:

- **Interpretation A — fixed primary-attempt reading:** the two completion/finite stability metrics are evaluated over the five preregistered primary identities. Primary failures remain observations for the attempt-level metrics, and the denominator is five.
- **Interpretation B — generic completed-member reading:** the generic aggregation clause is applied to all four primary metrics. Only governance-valid completed-member values are used, so an excluded primary attempt is absent from the metric population rather than contributing an attempt-level failure; the effective denominator for the finite/checkpoint rate follows the completed-member population or becomes unavailable when that population is incomplete.

The readings can produce different H2 comparisons because Interpretation A records
an excluded primary attempt as an event in the failure-rate metric, while
Interpretation B can remove that attempt from the metric population. No
hypothetical WGAN values or H2 outcome were calculated here.

No earlier explicit frozen rule contradicts Interpretation A. The earlier
records instead require failed primary attempts to remain in the roster and
state that the later SAP must define denominators by claim. Amendment 060 is that
pre-result definition for the H2 comparator.

## 3. Controlling attempt-level roster and denominator

For H2 attempt-level primary metrics, the fixed primary roster is exactly five
identities for each family.

### 3.1 Neural-SDE primary roster

- `v5-seed-01`
- `v5-seed-02`
- `v5-seed-03`
- `v5-seed-04`
- `v5-seed-05`

### 3.2 WGAN primary roster

- `wgan-seed-01`
- `wgan-seed-02`
- `wgan-seed-03`
- `wgan-seed-04`
- `wgan-seed-05`

### 3.3 Controlling denominator

The denominator for both attempt-level primary metrics is:

`5 preregistered primary identities`.

The denominator is not the number of valid completed members, the number of
Gate-passing members, the number of available checkpoints, or a reserve-adjusted
family size.

Reserve members do not replace, erase, renumber, overwrite, or retroactively
rewrite an original primary-attempt entry for either attempt-level metric. A
reserve remains separately labelled and separately governed.

## 4. `valid_completed_member_fraction`

`valid_completed_member_fraction` is an attempt-level metric over the fixed five
primary identities.

### 4.1 Numerator

The numerator is the number of the five preregistered primary identities that
produced a governance-valid completed model.

A governance-valid completed model has exactly one of these existing frozen
statuses:

- `GATE_PASS_VALID`;
- `GATE_FAIL_VALID`.

### 4.2 Denominator

The denominator is exactly `5`, the number of preregistered primary identities.

### 4.3 Excluded statuses

The following statuses are not counted in the numerator:

- `VALID_EXECUTION_NO_GATE_RESULT`;
- `GOVERNANCE_INVALID`.

They remain in the primary roster and failure accounting. Their exclusion from
the numerator does not delete the corresponding primary attempt.

### 4.4 Reserve effect and completed-model distinction

A later reserve execution does not alter this fraction and does not change the
historical primary-attempt denominator. A reserve-contributed completed member
may satisfy a separately governed completed-model family-size requirement, but
it does not rewrite primary-attempt stability or become a primary member.

Therefore this metric is distinct from `completed-model N`:

- `valid_completed_member_fraction` reports valid completed members among the five primary attempts;
- `completed-model N` reports the separately governed numerical completed-model comparison roster, which may include a separately labelled valid reserve when the frozen H2 completeness rule permits it.

**Verdict:** `ATTEMPT_LEVEL_PRIMARY_DENOMINATOR_FROZEN_AT_5`.

## 5. `nonfinite_or_missing_checkpoint_rate`

`nonfinite_or_missing_checkpoint_rate` is an attempt-level metric over the same
fixed five primary identities and uses no imputation or reserve substitution.

### 5.1 Per-primary indicator

For each primary identity, set its indicator to `1` if and only if at least one
of the following holds:

1. the primary attempt has no governance-admissible valid selected checkpoint suitable for the preregistered comparison; or
2. a governed training or selection quantity required to establish that checkpoint contains a disqualifying non-finite value under the frozen failure rules.

Otherwise, set the indicator to `0`.

A valid selected checkpoint must remain suitable for the preregistered
comparison under the frozen checkpoint-selection and governance rules. No
replacement value is imputed when the checkpoint is absent or disqualified.

### 5.2 Rate

The rate is:

`sum of the five primary indicators / 5`.

The denominator is therefore exactly `5` for both Neural-SDE and WGAN.

### 5.3 Failure-reason taxonomy

The binary metric records whether a governance-admissible comparable checkpoint
exists. The underlying reason must be preserved separately and must not be
collapsed into a numerical-instability label. At minimum, the reason taxonomy
retains the applicable distinction among:

- scientific non-finite failure;
- missing checkpoint;
- governance-invalid execution;
- other applicable frozen failure category.

A `GOVERNANCE_INVALID` outcome may contribute an indicator of `1` because it lacks
a governance-admissible comparable checkpoint, but it must remain labelled as a
governance failure. It must not be relabelled as a scientific non-finite failure
unless the evidence independently establishes that scientific reason.

### 5.4 Reserve effect

A reserve cannot replace an affected primary identity for this rate. A reserve
cannot erase a primary failure, change its indicator to `0`, or change the
five-attempt denominator. Reserve evidence is reported separately.

**Verdict:** `ATTEMPT_LEVEL_PRIMARY_DENOMINATOR_FROZEN_AT_5_WITH_REASON_TAXONOMY_PRESERVED`.

## 6. Completed-member metrics remain separate

The following remain completed-member metrics:

- `normalized_best_checkpoint_epoch_sd`;
- `checkpoint_selection_metric_sd`.

They are computed only when the frozen H2 completeness rule permits a valid
five-member comparison roster. A separately identified valid reserve may be part
of that completed-model roster only under the already frozen reserve/completed-
model policy; it is never retroactively relabelled as a primary member.

Amendment 060 does not alter the numerical definitions of these metrics:

- `normalized_best_checkpoint_epoch_sd` remains the sample SD of the selected best checkpoint epoch normalized by the frozen maximum generator epochs;
- `checkpoint_selection_metric_sd` remains the sample SD of the common internal-selection checkpoint metric at the selected checkpoint;
- normalization is unchanged;
- `ddof=1` is unchanged;
- the checkpoint-selection metric is unchanged;
- fixed member ordering is unchanged;
- the missingness rule is unchanged.

The generic five-member aggregation clause in Amendment 059 applies to these
completed-member metrics and does not override the fixed primary-attempt
denominator for `valid_completed_member_fraction` or
`nonfinite_or_missing_checkpoint_rate`.

**Verdict:** `COMPLETED_MEMBER_METRICS_UNCHANGED_AND_SCOPED_SEPARATELY`.

## 7. H2 decision logic preserved

Amendment 060 preserves the existing H2 decision logic and does not redesign
the comparison.

The status vocabulary remains:

- `H2_SUPPORTED`;
- `H2_NOT_SUPPORTED`;
- `H2_UNRESOLVED`.

The existing pre-result dominance rule remains controlling. The four
preregistered primary metrics remain the same. Only the population and
denominator semantics of the two attempt-level primary metrics are clarified.

This clarification:

- does not change secondary metrics;
- does not introduce significance testing;
- does not introduce weights, ranks, composites, or thresholds;
- does not change the architecture or compute budget;
- does not change the singleton WGAN configuration or five-primary schedule;
- does not authorize implementation, training, Gate execution, validation, or final-test access;
- does not use hypothetical WGAN outcomes;
- was frozen before any WGAN implementation or result.

Any downstream H2 conclusion produced under this clarification must be accepted
under the frozen rule even if it is less favorable to Neural-SDE. No result may
be used to revise this denominator choice.

**Verdict:** `H2_DECISION_RULE_PRESERVED; ATTEMPT_LEVEL_SEMANTICS_CLARIFIED_PRE_RESULT`.

## 8. Relationship to Amendment 059

Amendment 059 remains historically valid and is not rewritten. Its generic
aggregation wording is prospectively clarified by Amendment 060 only for the
scope of the two attempt-level metrics:

- `valid_completed_member_fraction`;
- `nonfinite_or_missing_checkpoint_rate`.

The completed-member aggregation wording remains controlling for
`normalized_best_checkpoint_epoch_sd` and `checkpoint_selection_metric_sd`.
No Amendment-059 hash, Git blob, preregistration field, WGAN model contract,
seed schedule, or H2 status is changed by this clarification.

## 9. Scientific and execution firewalls

Task 107 performs methodology clarification only. Required zero counts are:

- WGAN implementation: `0`;
- source changes: `0`;
- test changes: `0`;
- configuration changes: `0`;
- WGAN authorization: `0`;
- training: `0`;
- simulation: `0`;
- Gate execution: `0`;
- N4/N5 recomputation: `0`;
- validation: `0`;
- external validation: `0`;
- final-test access: `0`;
- H2 numerical calculation: `0`;
- provider/scientific network: `0`;
- Git-remote network: `0`;
- push: `0`.

No WGAN result exists before this clarification. If a WGAN execution or result
artifact is discovered before the clarification is independently audited, the
state must be classified as:

`BLOCKED_COMPARATOR_RESULT_EXISTS_BEFORE_CLARIFICATION`.

## 10. Preservation and append-only identity rule

The following remain unchanged from the Task-107 starting state:

- WGAN preregistration;
- Amendment 059;
- validated N5 family analysis;
- reserve-j01 `GATE_PASS_VALID` execution and adjudication state;
- final-test controls and `SEALED` status;
- repository test baseline `GREEN`;
- H2 `UNRESOLVED_PENDING_WGAN_COMPARATOR`.

This amendment is append-only. It does not embed its own future FILE SHA-256 or
Git blob. Its identity is determined only after the final bytes are committed.
No earlier amendment is rewritten.

## 11. Required next action

Independent read-only audit of Amendment 060, including:

- ambiguity reconstruction and prior-record chronology;
- fixed primary rosters and denominator `5`;
- exact numerator and indicator definitions;
- reserve non-substitution;
- preservation of failure-reason taxonomy;
- completed-member metric scope and unchanged numerical conventions;
- H2 decision-rule preservation;
- Amendment-059 relationship;
- no-result and no-execution firewalls;
- append-only and self-authentication rules.

No WGAN implementation may begin until this clarification is independently
audited. The final test remains sealed.

---

*Amendment 060 freezes the attempt-level denominator semantics for the two H2
completion/finite-stability metrics before any WGAN implementation or result,
keeps completed-member aggregation separate for the two checkpoint-stability
metrics, preserves primary failure taxonomy and reserve lineage, and leaves the
scientific and final-test state unchanged.*
