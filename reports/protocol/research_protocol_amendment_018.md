# Amendment 018 — Blinded External-Validation Identity Repair and Terminal Reauthorization Policy

The blocked governed task NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-015 constructed
the held-out validation series exactly once. Its `validation_series_series_sha256`
bound it to the frozen validation series; no validation metric was exposed as
a scientific result, and no model simulation/baseline comparison was performed.

Proven failure classification (task NM-R4-V5-EXTERNAL-VALIDATION-FAILURE-AUDIT-016):
the load-bearing `verify_frozen_target` byte-identity check used
`canonical_dumps(payload).encode("utf-8")` on two *semantically* identical
scorecards whose representations differed in mapping-key *type* alone:

  live recomputation (`src/neuralmarket/eval/scorecard.py`): `return_acf`,
  `abs_return_acf`, `sq_return_acf`, `leverage_correlations` keys are integers
  (`1`, `5`, `22`, `66`);

  JSON-round-tripped frozen `validation_empirical` (suite/benchmark artifacts):
  the same keys are strings (`"1"`, `"5"`, `"22"`, `"66"`).

`canonical_dumps(..., sort_keys=True)` therefore produces a different key order
in the region of those families — e.g. `1, 5, 22, 66` vs `"1", "22", "5", "66"`
— causing exact byte equality to fail on a *value-independent* basis; the
repository's existing `benchmark._family_errors` already normalizes this
asymmetry via `str(key)` comparison, proving the bytes-as-written provenance
contract is itself draconian. That is not validation drift, floating-point
drift, or a target-provenance contradiction.

Blinded/defect-evidence provenance (one governed construction consumed
but no validation values exposed):

  task: NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-015
  validation_series constructed: true
  model_simulation: false — failed before `verify_canonical_checkpoint`
  bounded failure point: `verify_frozen_target` (harness R run() line 520)
  transcript SHA-256: 5063b0f0eceaefb53657c869adc46bfaf8293737b9a8b717d9d75a27da58393d
  exit-code SHA-256: 6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b
  benchmark / baseline-suite target artifacts: *identical* before and after
  harness checkpoint SHA: still canonical `c7b9be5d...` — never touched

Value-independent semantics of the defect: it would occur for *every* series
even when every numeric value is identical; no held-out return or metric was
required to characterize it. The first attempted one-shot construction does not
consume scientific discretion.

Repair in task NM-R4-V5-EXTERNAL-VALIDATION-IDENTITY-REPAIR-017 (harness only;
no validation read, no MetricSpecification/scorecard/model change):

  every mapping in both `recomputed` and `frozen` payloads is recursively
  normalized to string-key representation
  (`_normalize_mapping_keys`: mapping → `{str(k): …}`, sequences recursed,
  scalars untouched/round-tripped identically), then `canonical_dumps`
  serialized and compared as exact byte equality — the same semantic-object
  equality.

No numerical tolerance: **no epsilon, no rtol, no atol**. A numeric difference
even at one [`nextafter`] ULP still FAILS. The identities verified are:
`sha256(canonical_dumps(_normalize_mapping_keys(payload)))` on each side.

Terminal reauthorization policy (freezes the contract without a threshold):

  If a future singly-reauthorized governed validation construction — necessarily
  the *second* governed construction under this arm — again reaches the
  corrected normalized identity check and exact equality still fails, the
  confirmatory v5 external-validation arm **stops**. No tolerance, no third
  governed construction, no target regeneration/editing to force agreement.

  Harness policy identifier:

    `MAX_GOVERNED_VALIDATION_CONSTRUCTIONS_FOR_THIS_ARM = 2`:
      1 = the consumed blinded mechanical failure (NM-R4-…-015),
      2 = at most one singly-reauthorized corrected attempt (later explicit
          authorization only — *not* granted by this repair task).

  The harness's own `build_validation_series_once` one-shot guard remains
  `≤ 1 valid construction per process`; the aggregate bound is enforced by
  governance — the second governed access requires a separate explicit
  authorization after independent audit of this repair + harness.

Future singly-reauthorized execution (not this task) will carry:

  `governance.prior_failed_attempt` provenance distinguishing cumulative from
  current-process counters:

    governor: task_id, validation_constructed, model_simulation,
    failure_classification, transcript_sha, exit_code_sha, blinded
    current_process: validation_constructions ≤ 1  (harness-enforced)
    cumulative governed constructions policy: exactly the `= 2` bound above
    (second access NOT authorized by this repair)

  and a policy footer alongside: second-attempt normalized identity still
  mismatched ⇒ terminal (no torque).

This amendment is append-only governance/clarification: it records the blinded
mechanical failure, the representation-only repair, the preserved exact-equality
contract, and the terminal no-tolerance/no-third-access policy.

  Amendment 017 remains the pre-access scientific contract — unchanged.
  Original contract YAML `configs/research/structured_vol_v5_external_validation_v1.yaml` — unchanged.
  Candidate checkpoint `c7b9be5d...` — unchanged.
  Frozen identities (`suite_hash`, metric spec, benchmark hash, etc.) — unchanged.
  Scientific semantics (`target validation_empirical`, `training_boundary`,
  22-lookback, 63 horizon, 1024 paths, seed 8283, `one_step_daily_log_return_increments`): all unchanged.
  Near-future `/tmp` diagnostics: ephemeral, do not persist in Git.

No held-out metric values appear here. Published SHAs are provenance, not
held-out results. No validation access, no model comparison, no final-test.
