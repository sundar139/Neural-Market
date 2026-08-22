# Amendment 056 — V5 Reserve-j01 Post-execution Test Maintenance Closure

**Date:** 2026-08-22
**Task:** NM-R4-V5-POST-EXECUTION-WORKTREE-REPAIR-097
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `917e90a241349e9308b63d2fc66981b944000dbb`
**Prerequisite audit:** NM-R4-V5-RESERVE-J01-CUDA-EXECUTION-AUDIT-096
**Audit verdict:** REPAIR REQUIRED — scoped solely to the post-execution uncommitted test mutation.
**Status:** POST-EXECUTION TEST MAINTENANCE CLOSURE

## 1. Scope and frozen scientific state

Audit 096 identified one post-execution worktree repair scope: the expected
uncommitted mutation in
`tests/unit/research/test_v5_replicate_training_runner.py`. No scientific
repair was identified or authorized.

The already-validated scientific execution remains:

- classification: `GATE_PASS_VALID`;
- completed-model N: `5`;
- Gate-pass count: `5`;
- five-seed requirement: `SATISFIED`;
- reserve-j01 remains separately labelled `reserve-j01`;
- N=5 family analysis remains not performed;
- final test remains `SEALED`.

This amendment records only the test-maintenance closure. It does not change
the runner, authorization, scientific configuration, seed schedule, Gate-v2,
trainer, runtime identity, execution evidence, model artifacts, or
adjudication.

## 2. Exact chronology and mutation classification

The required chronology is:

1. Scientific process termination: `2026-08-22 13:27:28 -04:00`.
2. Post-execution evidence commit:
   `917e90a241349e9308b63d2fc66981b944000dbb`, at
   `2026-08-22 13:33:43 -04:00`.
3. Unauthorised test mutation: `2026-08-22 13:38:48 -04:00`.
4. Task-097 opened to close the scoped post-execution worktree mutation.
5. Test-maintenance commit:
   `05afed554a0cb529580880aa004d576f499c82b1`.

The mutation occurred after:

- scientific termination;
- Gate classification;
- creation and hashing of the scientific artifacts; and
- the post-execution evidence commit.

The mutation is classified as:

`POST_EXECUTION_TEST_MAINTENANCE_SCOPE_VIOLATION_NO_SCIENTIFIC_EFFECT`

No explicit frozen rule retroactively invalidates the completed scientific
execution because of this later, unrelated unit-test edit. Therefore
`GATE_PASS_VALID`, completed-model N=5, Gate-pass count 5, and the satisfied
five-seed requirement remain unchanged.

## 3. Preserved two-hunk test adaptation

The frozen maintenance decision was:

`PRESERVE THE EXISTING TWO-HUNK TEST ADAPTATION`

The committed diff is restricted to exactly two intended hunks:

1. `test_allowed_member_dry_run` now accepts `tmp_path` and `monkeypatch`, and
   redirects `derive_report_dir` and `derive_model_dir` to temporary paths.
   The dry-run overwrite preflight is therefore isolated from the legitimate
   completed reserve-j01 production namespace.
2. `test_positive_mocked_j01_traverses_to_pre_scientific_boundary` records
   whether the real reserve-j01 production `execution_started.json` marker
   existed before the mocked test and asserts that the same state remains
   afterward. It no longer requires the now-legitimate marker to be absent.

The adaptation preserves these invariants:

- production runner behavior is unchanged;
- scientific behavior is unchanged;
- authorization behavior is unchanged;
- real reserve-j01 execution artifacts are neither deleted nor modified;
- no surrounding helper refactor or opportunistic cleanup is included.

## 4. Test-file byte and line-ending identities

The test file identities are recorded as follows:

- pre-repair committed Git blob:
  `f76a166bd2825ae43c188a73f4774b6a19c8c8d2`;
- dirty worktree raw SHA-256:
  `36fab524230197411cfab2ec74c30b58c4fcf2c7e78f66338fb30f4cf4549e82`;
- dirty worktree line endings: CRLF, 1,104 CRLF line endings, no lone LF or
  lone CR line endings;
- staged/index Git blob:
  `f2d948082e5492260fbaf1d8120fd44778c24a8c`;
- post-repair committed Git blob:
  `f2d948082e5492260fbaf1d8120fd44778c24a8c`;
- post-repair worktree raw SHA-256:
  `36fab524230197411cfab2ec74c30b58c4fcf2c7e78f66338fb30f4cf4549e82`;
- post-repair worktree line endings: CRLF, 1,104 CRLF line endings, no lone
  LF or lone CR line endings.

Git normalized the CRLF worktree bytes to LF in the index/blob. The raw
worktree SHA and Git blob identity therefore differ by expected line-ending
normalization; this is not corruption. The working-tree bytes remained CRLF
through staging and commit.

## 5. Verification

The required focused command was:

```text
.venv/Scripts/python.exe -m pytest tests/unit/research/test_v5_replicate_training_runner.py -q
```

Observed result:

- collected: `55`;
- passed: `55`;
- skipped: `0`;
- failed: `0`;
- runtime: `15.96s`.

The full focused suite passed, including the dry-run adaptation, positive
mocked reserve-j01 path, refused reserve-j02 path, wrong-runner negative,
wrong-contract negative, stale-recipe negative, and runtime-mismatch negative
coverage.

The real reserve-j01 marker, checkpoints, final checkpoint, curve, training
report, Gate/adjudication, model artifacts, authorization, runner, and recipe
were re-hashed after the test run and remained unchanged.

## 6. Scientific and governance firewalls

Task-097 added:

- scientific invocations: `0`;
- training invocations: `0`;
- simulation: `0`;
- validation: `0`;
- external validation: `0`;
- final-test access: `0`;
- provider/scientific network: `0`;
- Git-remote network: `0`;
- push: `0`;
- amend: `0`;
- rebase: `0`;
- reset: `0`.

Protected identities remain unchanged:

- runner blob: `a79a79f477429d66cc7fc0c75db7c751726ee577`;
- authorization SHA-256:
  `8906285802c84617d37890dd50860066cf8aa31a9d29ee839703cc4b1d987e61`;
- authorization blob: `236ac739e346cdc559dd3704b0df37eb190110aa`;
- execution recipe head:
  `79325e0ccbc25a09b863461ab56b722e19f8df36`;
- reserve-j01 prefix: `38c5113b27568e14`.

Amendments 055 and all prior records remain byte-immutable. Amendment 056
does not embed its own future SHA-256 or Git blob.

**Next governed action:** Independent read-only audit of Task-097
post-execution worktree repair before the frozen N=5 family analysis.
