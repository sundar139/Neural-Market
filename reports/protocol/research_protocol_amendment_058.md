# Amendment 058 — V5 Shared Analysis Implementation Provenance Update

**Date:** 2026-08-22
**Task:** `NM-R4-V5-N4-IMPLEMENTATION-PROVENANCE-REPAIR-101`
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `774f531f0c588476a4f24c80423b26e2ab84936d`
**Prerequisite audit:** `NM-R4-V5-N5-FAMILY-ANALYSIS-AUDIT-100`
**Prerequisite verdict:** `VALIDATED WITH NON-BLOCKING FINDINGS`
**Trigger:** Audit 100 non-blocking implementation-provenance finding.
**Status:** APPEND-ONLY DOCUMENTATION / PROVENANCE REPAIR ONLY.

This amendment supplies the current shared-analysis implementation identity and
reconciles it with the historical N=4 provenance record. It does not rewrite
Amendment 046, the historical N=4 result, the N=5 result, or any source,
test, runner, training, simulation, Gate, validation, external-validation,
final-test, WGAN, j02, or j03 state.

## 1. Scope, frozen state, and firewalls

The governing transitions for this task are:

`DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT`

The scientifically accepted state remains:

- reserve-j01: `GATE_PASS_VALID`;
- completed-model N: `5`;
- Gate-pass count: `5`;
- five-seed requirement: `SATISFIED`;
- N5 family analysis: `VALIDATED`;
- H2: `UNRESOLVED_PENDING_WGAN_COMPARATOR`;
- final test: `SEALED`.

This task performs static code/provenance inspection and byte-identity hashing
only. It does not recompute the N=4 or N=5 analysis. It does not execute the
analysis implementation, train, simulate, rerun Gate, validate, access the
final test, execute WGAN, decide j02/j03, access a provider, or use a
scientific or Git-remote network.

## 2. Task-099 implementation transition

The historical/shared implementation is:

`reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py`

Task-099 is commit
`b194cfcd117237b8bbce9c834bcc1ad761800ce7`, whose parent is
`5491346d1845d6f7ac701e44f307139afa6a2400`.

Independent blob verification for this file:

- pre-Task-099 Git blob: `616c9d17cb7d451fc72397e4fd6053b598068ad4`;
- post-Task-099/current Git blob: `bab4af9c719c3ff0db26b982f5083d27d9ee010b`.

Independent FILE SHA-256 verification:

- pre-Task-099 committed LF file, 20,638 bytes: `f24f54c8ef8a7867bd911c8778bbdadc54d50a55668274179c574cb760f0288a`;
- post-Task-099/current committed/worktree LF file, 20,687 bytes: `915d8f1cd9941ecb5dc75d85ee5390eec85284af52fddcc5a181bee8bb42056d`.

Both forms are LF-only with 333 LF line endings. The current worktree bytes
match the current committed bytes exactly; no line-ending normalization
ambiguity exists for this implementation file.

The exact zero-context diff reported by Git is:

```diff
diff --git a/reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py b/reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py
index 616c9d1..bab4af9 100644
@@ -175,2 +175,2 @@ def cv_value(mean: float, sd: float | None) -> tuple[float | None, str | None]:
-def compute_full_and_lomo(members: dict) -> tuple[dict, dict]:
-    order_ids = ["v5-seed-01", "v5-seed-02", "v5-seed-04", "v5-seed-05"]
+def compute_full_and_lomo(members: dict, order_ids: list[str] | None = None) -> tuple[dict, dict]:
+    order_ids = order_ids or ["v5-seed-01", "v5-seed-02", "v5-seed-04", "v5-seed-05"]
```

This is exactly a two-line behavioral generalization involving `order_ids`;
no broader change exists in this file. The original N=4 `main()` caller remains
`compute_full_and_lomo(members)` with no `order_ids` override. The new default
therefore retains the original hard-coded order:

`["v5-seed-01", "v5-seed-02", "v5-seed-04", "v5-seed-05"]`

The N=5 driver explicitly passes its separate order
`["seed-01", "seed-02", "seed-04", "seed-05", "reserve-j01"]`. Thus the
new parameter is used for the generalized N=5 path while the historical N=4
caller follows the unchanged default path. No empty-list override exists in
the historical N=4 path.

**Verdict:** `N4_BEHAVIOR_PRESERVED`.

## 3. Historical N=4 contract and result identity

The historical N=4 implementation contract, recorded in Amendment 045 §§2.1–
2.4 and retained in the result artifact, is unchanged in substance:

- four admissible members in the original order: `v5-seed-01`, `v5-seed-02`,
  `v5-seed-04`, `v5-seed-05`;
- exactly 13 frozen scalars with the historical scalar ordering;
- arithmetic mean, sample SD with `ddof=1`, median, minimum, maximum, and CV
  only where the frozen ratio-scale meaningfulness rule permits;
- unconditional leave-one-member-out calculations;
- CPU-only versus mixed-runtime disclosure without a causal backend estimate;
- seed-03 retained in accounting but excluded numerically.

The historical result artifact is:

`reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json`

Its independently recomputed identities are:

- RESULT_JSON_WORKTREE_FORM: CRLF, 58,394 bytes, FILE SHA-256
  `9dec35fc8d434f927ad3d0d5168de30bb06df380cd5031c45fa1e57287833a1f`;
- RESULT_JSON_COMMITTED_CONTENT: LF, 56,575 bytes, FILE SHA-256
  `8276f0d3bf105d9ba482799973035f2295cc5e2d50af4896a27f06b496e49ef7`;
- RESULT_JSON_GIT_BLOB:
  `1b9ed4edc84b4111701a30e38bc16b86a9fe8166`.

The pre-Task-099 parent and post-Task-099 commit both contain exactly the
same 56,575-byte committed LF content, with the same committed FILE SHA-256
`8276f0d3bf105d9ba482799973035f2295cc5e2d50af4896a27f06b496e49ef7` and the
same Git blob `1b9ed4edc84b4111701a30e38bc16b86a9fe8166`. The current CRLF
worktree form normalizes byte-for-byte to that committed LF content. The
line-ending distinction is checkout/clean-filter representation, not
analytical mutation.

**Historical N4 result:** byte-immutable.
**Recomputed:** yes, for file/blob identity and normalized-byte equality only;
no N4 analysis recomputation was performed.
**Verdict:** `N4_BEHAVIOR_PRESERVED`; `N4_HISTORICAL_RESULT_IMMUTABLE`.

## 4. Amendment 046 §3.2 reconciliation

Amendment 046 §3.2 recorded the historical Task-073 implementation identity:

- historical analysis-script FILE SHA-256:
  `f24f54c8ef8a7867bd911c8778bbdadc54d50a55668274179c574cb760f0288a`;
- historical analysis-script Git blob:
  `616c9d17cb7d451fc72397e4fd6053b598068ad4`.

Those identities were historically correct at Amendment 046's own commit and
remain valid as the original N=4 implementation provenance. Task-099 later
changed the shared implementation file, so that identity is now
**prospectively superseded for the CURRENT shared-implementation identity**.
Amendment 046 was not false when written and is not modified by this
amendment.

Amendment 058 supplies the current identity:

- current implementation FILE SHA-256:
  `915d8f1cd9941ecb5dc75d85ee5390eec85284af52fddcc5a181bee8bb42056d`;
- current implementation Git blob:
  `bab4af9c719c3ff0db26b982f5083d27d9ee010b`.

The historical N=4 RESULT remains immutable; its original implementation
provenance remains historically valid; the current shared implementation
identity changed during Task-099; and that change is behavior-preserving for
the N=4 default `order_ids` path. No retroactive rewrite is made.

## 5. Audit-100 test-coverage truth

Test:

`tests/unit/research/test_v5_runtime_sensitivity_analysis.py`

Audit 100 independently classified the N=5 calculation coverage as
`PARTIAL`.

The focused test DOES cover:

- generalized N=5 LOMO dimensional behavior;
- the frozen CV exclusion set.

The focused test DOES NOT cover:

- exact N=5 member selection;
- seed-03 numerical exclusion;
- 65-cell extraction from authoritative source artifacts;
- seed-01 historical alias mapping;
- numerical N=5 summary values;
- numerical 65-entry LOMO values.

This is **NON-BLOCKING FOR THE CURRENT VALIDATED N5 RESULT** because Audit 100
independently reconstructed all 65 raw cells, all 13 summaries, and all 65
LOMO calculations. No test was added or modified in Task-101, and coverage is
not represented as sufficient; it remains `PARTIAL`.

## 6. N5 identity and scientific preservation

The validated N5 family-analysis artifact remains:

`reports/research/structured_vol_v5_n5_family_analysis_v1.json`

- FILE SHA-256, Windows worktree form:
  `84e53a3e77e6eea12a1449aa08763766c6106d7fe16eb36d1285f0bd71bdf564`;
- Git blob: `7c10e622db3415cae53fb9547d6ebef15decbb76`;
- analysis status: `VALIDATED`;
- recomputed in Task-101: `0`;
- modified in Task-101: `0`.

The accepted N5 family state remains five completed analytical members with
five Gate-pass members, including reserve-j01 as `GATE_PASS_VALID`, with
seed-03 retained historically and excluded numerically. H2 remains
`UNRESOLVED_PENDING_WGAN_COMPARATOR`; the final test remains `SEALED`.

## 7. Numerical convention

The frozen shared implementation uses the Python standard-library
`statistics` conventions directly:

```python
mean = statistics.mean(values)
sd = statistics.stdev(values) if n > 1 else None
med = statistics.median(values)
```

Therefore:

- mean: `statistics.mean`;
- SD: `statistics.stdev`;
- median: `statistics.median`;
- `ddof`: `1` for the sample SD produced by `statistics.stdev`.

The implementation's summary path converts source values with `float(v)`
before calling `summary_stats`, then serializes the result through the
standard-library `json.dumps(result, indent=2)`. Audit-100's serialization
convention is therefore the native Python numeric serialization of these
standard-library results: no NumPy replacement, forced decimal formatting,
output-precision alteration, or numerical coercion beyond the existing
`float(v)` conversion was introduced. Any JSON token formatting such as
`1.0` for an integral-valued mean is serialization representation, not a
scientific value change.

**Implementation changed for this convention:** no.
**Verdict:** frozen standard-library convention preserved.

## 8. Task-101 mutation and firewalls

Task-101 changes exactly one tracked file:

`reports/protocol/research_protocol_amendment_058.md`

No source change, test change, analysis artifact change, runner change,
training, simulation, Gate rerun, validation, external validation, final-test
access, WGAN execution, j02 decision, j03 decision, provider/scientific
network, Git-remote network, amend, rebase, reset, or push occurred.

The following protected identities remain unchanged:

- reserve-j01: `GATE_PASS_VALID`;
- completed-model N: `5`;
- Gate-pass count: `5`;
- runner Git blob: `a79a79f477429d66cc7fc0c75db7c751726ee577`;
- authorization Git blob: `236ac739e346cdc559dd3704b0df37eb190110aa`;
- recipe: `79325e0ccbc25a09b863461ab56b722e19f8df36`;
- j01 adjudication SHA-256:
  `50135d8a472ec45c167b3d8115305bc34874eaafe93623a9d703f7eda9013c32`.

## 9. Append-only and self-authentication rule

Amendment 058 records the implementation transition, exact diff, preserved
N4 default path, immutable N4 result identity, Amendment-046 supersession
status, N5 identity, partial coverage, and numerical conventions. It does not
embed its own future FILE SHA-256 or Git blob. Its own identity is determined
only after the append-only file is committed.

## 10. Required next action

Independent read-only audit of Amendment 058 provenance repair, including the
exact Task-099 diff, current and historical implementation identities, N4
artifact immutability, Amendment-046 §3.2 prospective supersession, Audit-100
partial coverage statement, N5 artifact identity, and all firewalls. No
scientific execution is authorized or implied. The final test remains sealed.

---

*Amendment 058 records only the current shared-analysis implementation
provenance: Task-099 generalized `order_ids` for N=5 while preserving the
historical N=4 default path; the historical N=4 result remains immutable; the
validated N5 analysis remains unchanged; H2 remains unresolved pending WGAN;
and the final test remains sealed.*
