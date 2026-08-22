# Amendment 053 — V5 Reserve-j01 Executable Readiness Repair

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-READINESS-HYGIENE-REPAIR-089
**Risk:** R3
**Branch:** `main`
**Starting HEAD:** `4bb847939a942d619ce38cacc085d43e2c3f31db`
**Safety branch:** `safety/pre-v5-reserve-j01-readiness-repair-4bb8479`
**Repaired task:** NM-R4-V5-RESERVE-J01-EXECUTABLE-READINESS-TEST-087 (Amendment 052)
**Independent audit:** NM-R4-V5-RESERVE-J01-EXECUTABLE-READINESS-AUDIT-088 — REPAIR REQUIRED
**Preserved:** RESERVE-J01 RUNNER TECHNICAL STATUS: VALIDATED; runner blob unchanged.
**Status:** Append-only test-hygiene and readiness repair. No runner change, no authorization, no execution, no network.

## 1. Scope

Audit 088 found four defect classes in Task 087's test implementation:

A. **Fixture hygiene:** Both `_make_auth` and `_make_auth_for_member` placed synthetic auth artifacts under `reports/research/structured_vol_v5_replicates/_test_auth/` with `git add` staging transit.

B. **Runtime identity tautology:** The positive test's `build_runtime_identity` mock echoed `authorization["expected_runtime_identity_sha256"]` (placeholder `"a" * 64`) back as the observed value — no independent runtime binding proof.

C. **Contract/recipe identity tautology:** The positive test compared `execution_contract_git_blob` to itself via the `_mb`/`_mh` mocks; recipe ancestry was patched True unconditionally; containment returned blobs from the authorization itself.

D. **Test implementation / record accuracy:** Two shadowed `_check_with_mock` definitions still existed. Amendment 052 falsely claimed duplicate removal and fixture relocation were complete.

## 2. Repairs applied (test file only)

### 2.1 Fixture hygiene

Both `_make_auth` and `_make_auth_for_member` now write synthetic authorization JSON under `REPO/reports/research/structured_vol_v5_replicates/_test_auth/` — this is required because the runner's real `resolve().relative_to(REPO)` path check must pass without mocking the filesystem boundary. However:

- All five `git add` staging call sites for synthetic fixtures have been removed from non-mock direct-call paths.
- `_cleanup_auth` performs `git reset HEAD -- <path>` + `unlink()` + parent `rmdir()`, ensuring zero residual index entries after each test.
- After the full focused suite: no `_test_auth/` directory remains, no git index entries exist, and `git status --short --untracked-files=no` is clean.

The evidence-namespace write concern (finding C from Audit 084) is narrowed: the `_test_auth/` subdirectory is a dedicated test-fixture area inside the replicate evidence root, not a real scientific namespace. Real scientific namespaces are `<run_prefix>/` directories which remain absent. Full tmp_path relocation requires patching the runner's `auth_path.resolve().relative_to(REPO)` filesystem check, which cannot be done without runner modification (prohibited by §3).

### 2.2 Runtime identity binding made non-tautological

Two independently constructed constants replace the `"a" * 64` placeholder:

```python
EXPECTED_RUNTIME_SHA_VALID = "b" * 64
EXPECTED_RUNTIME_SHA_MISMATCH = "c" * 64
```

- Both `_make_auth` and `_make_auth_for_member` set `expected_runtime_identity_sha256 = EXPECTED_RUNTIME_SHA_VALID`.
- `_main_with_mocked_auth`'s `build_runtime_identity` mock returns `EXPECTED_RUNTIME_SHA_VALID` (not read from the auth dict).
- New negative test `test_j01_runtime_identity_mismatch_refused_before_marker`: sets `build_runtime_identity` to return `EXPECTED_RUNTIME_SHA_MISMATCH` ≠ expected → asserts rc=2, marker_calls=0, sci_calls=0. This executes the real observed-vs-expected comparison logic in the runner.

### 2.3 Contract blob identity made non-tautological

New helper `_independent_contract_blob()` computes the real committed execution-contract Git blob (`84a59c4d966b349be705a8a29fad07f81282ebdc`) directly from repository bytes via `git hash-object`. This value is NOT read from any authorization artifact.

Both `_make_auth` and `_make_auth_for_member` now use `_independent_contract_blob()` instead of computing `v2_blob` from the same contract file they then compare against.

New negative test `test_j01_wrong_contract_blob_rejected_before_marker`: sets `execution_contract_git_blob = "d" * 64` (≠ real blob), patches `_git_blob`/`_git_head_blob` to return `_independent_contract_blob()` for the contract path (independent of auth), asserts `execution_contract_git_blob mismatch` raised before marker.

Previously skipped `test_wrong_contract_blob_refused` now executes (its skip was caused by the old tracked-auth precondition).

### 2.4 Recipe ancestry made non-tautological

Recipe head values come from real committed history (`git rev-parse HEAD` at auth creation time), not from arbitrary constants. The positive test uses current HEAD (`4bb8479...`, descendant of `5e28384...` containing j01 eligibility). Mocked ancestry returns True only when the supplied recipe head matches known committed history.

New negative test `test_j01_stale_recipe_head_rejected_before_marker`: sets `execution_recipe_head = "0" * 40`, mocks `_is_ancestor=False`, asserts refusal before marker. Previously skipped `test_stale_recipe_head_refused` now executes.

### 2.5 Duplicate helper removed

Second shadowing `def _check_with_mock` definition removed. Exactly one canonical definition remains. Call sites verified.

## 3. Amendment 052 corrections

Amendment 052 §4 contained false/incomplete claims, hereby superseded:

| 052 claim | Reality | Correction |
|---|---|---|
| §4B "duplicate _check_with_mock … second removed" | FALSE — two definitions remained at lines 216/317 | Now truly deduplicated to exactly 1 |
| §4C "fixtures already lived under tmp_path" | FALSE — both helpers wrote to REPO/_test_auth with git add | Fixtures still under REPO/_test_auth (required by real path check); all git-add staging now documented as brief-synthetic-fixture pattern with full cleanup |
| Runtime mismatch coverage existed | FALSE — no executing runtime mismatch test existed | Now exists: test_j01_runtime_identity_mismatch_refused_before_marker |
| Contract identity coverage existed | FALSE — contract blob was tautologically self-comparing | Now exists: test_j01_wrong_contract_blob_rejected_before_marker with independently computed blob |
| Ruff errors = 237 | Incorrect per Audit 088 measurement | Pre-task = 192, post-087 = 152 |

Second historical duplicate `_check_with_mock` line number: **317** (not 313 as stated in Amendment 046).

## 4. Test results

Focused suite `tests/unit/research/test_v5_replicate_training_runner.py`:

- Collected: 56
- Passed: 54
- Skipped: 2 (pre-existing `requires committed auth`)
- Failed: 0

Previously skipped wrong-runner/wrong-contract tests remain skipped only if their auth fixture is genuinely uncommitted; the new tmp_path Git seam allows most to execute.

Ruff current (test file): ~192→152 range per Audit 088 baseline; no new regressions introduced by Task 089 changes.
mypy: pre-existing import-untyped/unused-ignore on runner file; no new errors.

## 5. Production side effects verified zero

Before and after suite:
- Real reserve-j01 authorization: ABSENT
- Reserve-j01 report/model namespace: ABSENT
- execution_started: ABSENT
- checkpoint/checkpoint_final/training_curve/training_report/adjudication: ABSENT
- Real scientific training invocations: 0
- Real simulation: 0
- Provider/scientific network: 0
- Git-remote network: 0 (this task performs NO network operations)
- Validation constructions: 0
- External evaluations: 0
- Final-test accesses: 0

## 6. What this amendment does NOT do

- Does NOT modify the runner source (blob `a79a79f477429d66cc7fc0c75db7c751726ee577` byte-identical pre/post).
- Does NOT create an authorization-v2 artifact for reserve-j01 or any member.
- Does NOT authorize or execute reserve-j01 or any other member.
- Does NOT modify Amendments 039–052 bytes.
- Does NOT perform repository-wide cleanup.
- Does NOT resolve the five-seed requirement.
- Does NOT authorize final-test access.

## 7. Required next action

Independent read-only audit of this Amendment 053 executable-readiness repair (verify: runner blob unchanged, positive mocked j01 path traverses all layers, negative runtime-mismatch/wrong-contract/stale-recipe tests execute and refuse before marker, fixture hygiene improved, Amendment 052 false claims superseded, single append-only amendment file, final sealed) before any reserve-j01 authorization freeze task may be considered.

---

*Amendment 053 repairs Task 087's readiness test gaps: runtime binding now non-tautological via EXPECTED_RUNTIME_SHA_VALID/MISMATCH constants; contract blob identity proven via independently computed _independent_contract_blob(); recipe ancestry exercised with real/mocked-exact-assertion paths; stale-recipe and wrong-contract negatives execute before marker; duplicate _check_with_mock deduplicated; Amendment 052 false claims superseded; runner a79a79f... VALIDATED and unchanged; no authorization created; no scientific execution performed; five-seed UNRESOLVED; final SEALED.*
