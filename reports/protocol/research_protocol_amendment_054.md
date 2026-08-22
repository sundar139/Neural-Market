# Amendment 054 — V5 Reserve-j01 Executable Readiness Final Test Repair

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-READINESS-HYGIENE-REPAIR-091
**Risk:** R3
**Branch:** `main`
**Starting HEAD:** `74b87dcc271161c092b1f522155cf825c6ec95d6`
**Safety branch:** `safety/pre-v5-reserve-j01-readiness-final-repair-74b87dc`
**Repaired task:** NM-R4-V5-RESERVE-J01-READINESS-HYGIENE-REPAIR-089 (Amendment 053)
**Independent audit:** NM-R4-V5-RESERVE-J01-READINESS-HYGIENE-AUDIT-090
**Audit 090 verdict:** REPAIR REQUIRED
**Status:** Append-only final test-hygiene and identity-coverage repair. No runner change, no authorization, no execution, no network.

## 1. Audit-090 record and Amendment-053 correction

Audit 090 found that Task 089 failed the frozen zero-transit hygiene criterion. Amendment 053's claim that transient evidence/index staging satisfied the criterion was wrong.

Amendment 053 falsely claimed all of the following:

- five git-add fixture sites were removed;
- duplicate `_check_with_mock` was removed;
- positive contract/recipe identity was fully non-tautological;
- 56 tests were collected.

The actual Audit-090 result was:

- 56 test definitions;
- 54 unique test names;
- 54 tests collected;
- 52 passed;
- 2 skipped;
- 0 failed.

The two duplicate/shadowed test names caused the difference between 56 definitions and 54 unique names. The skipped identity negatives were not executing coverage of the required failure paths.

Task 089 also performed a prohibited governance operation in its reflog:

- timestamp: `2026-08-22 03:43:01 -0400` as displayed by Git;
- operation: `reset: moving to HEAD`;
- before: `4bb8479`;
- after: `4bb8479`;
- impact: no ref change and no byte change;
- classification: governance deviation, not scientific change.

Amendment 053 did not disclose this reset governance deviation. This Amendment 054 records it explicitly. Amendments 052 and 053 were not modified.

## 2. Task-091 repair

### 2.1 Fixture isolation and zero transit

Both `_make_auth` and `_make_auth_for_member` now write only beneath:

`tests/.pytest_cache/v5_replicate_auth/`

This root is repository-local, so the runner's `resolve().relative_to(REPO)` predicate can be exercised without changing the runner. It is outside `reports/`, `reports/research/`, the scientific evidence namespace, `data/`, and the production authorization directory. `git check-ignore` confirms the root is ignored by `.gitignore:4:.pytest_cache/`.

The five synthetic-fixture `git add` call sites were removed. Reset-based fixture cleanup was removed. Cleanup uses only ordinary ignored temporary-file and empty-directory removal.

Observed repair invariants:

- synthetic auth writes under `reports/research/`: 0;
- synthetic auth writes under the real authorization directory: 0;
- synthetic auth Git-index entries: 0;
- git-add fixture calls: 0;
- git-reset fixture cleanup calls: 0;
- evidence-namespace transit: 0;
- production authorization remained absent;
- the chosen ignored fixture root was empty after the authoritative suite.

The runner provenance predicates are patched only for the synthetic authorization path: `_is_tracked`, `_is_clean`, `_git_head_blob`, and `_git_blob`. All runner, contract, schedule, recipe, and other repository paths use their real implementations.

### 2.2 Independent positive identity coverage

The positive reserve-j01 test independently computes the runner-referenced execution-contract blob from repository bytes with `git hash-object`:

- execution contract: `84a59c4d966b349be705a8a29fad07f81282ebdc`;
- runner: `a79a79f477429d66cc7fc0c75db7c751726ee577`;
- schedule: `558d08bfee98dbd0c170d65e6a9b1737700c9e98`.

The authorization's `execution_contract_git_blob` is asserted equal to the independently computed contract value. The mocked Git boundary does not read that field from the authorization.

The positive recipe head is selected from real local Git ancestry at or after `5e28384be24c898b7a3b1182ad6d944307398db0` and is `74b87dcc271161c092b1f522155cf825c6ec95d6` for the authoritative run. The selected committed point contains the expected runner, execution-contract, and schedule blobs. The `_is_ancestor` test seam returns true only for the independently selected recipe head when the real Git ancestry relation also holds; it is false for any other head. Recipe containment blobs are independently read from the selected commit and are not read from authorization fields.

The positive test independently asserts:

- authorization runner blob equals the actual frozen runner blob;
- authorization contract blob equals the independently computed contract blob;
- recipe runner blob equals the expected runner blob;
- recipe contract blob equals the independently computed contract blob;
- recipe schedule blob equals the frozen schedule blob;
- runtime expected identity is `b` repeated 64 times and observed runtime identity is supplied independently by the runtime mock.

No positive identity comparison is authorization-to-itself, and no recipe identity is unconditionally bypassed.

### 2.3 Duplicate cleanup and negative coverage

Exactly one definition remains for each of:

- `_check_with_mock`;
- `test_reserve_j01_runner_eligible_via_eligible_constant`;
- `test_positive_mocked_j01_traverses_to_pre_scientific_boundary`.

The shadowed/dead helper and test copies were deleted. Executing non-skipped reserve-j01 negative coverage now includes:

- deliberately wrong runner blob versus the independently computed frozen runner blob;
- deliberately wrong execution-contract blob versus the independently computed real contract blob;
- stale recipe ancestry using the constrained ancestry seam;
- runtime identity mismatch using an independently supplied observed runtime value.

Each negative asserts refusal before `execution_started`, with marker calls equal to 0 and scientific calls equal to 0. The stale-recipe assertion matches only `execution_recipe_head invalid|not ancestor` and does not include unrelated `not committed` text.

## 3. Authoritative validation

The exact authoritative command was run once:

`python -m pytest tests/unit/research/test_v5_replicate_training_runner.py -q`

Using the project interpreter, the observed result was:

- collected: 55;
- passed: 55;
- skipped: 0;
- failed: 0;
- duration: 15.52 seconds.

Pre-run state recorded:

- `git status --porcelain` contained only the intended modified test file plus three pre-existing untracked report artifacts;
- `git diff --cached --name-only` was empty;
- the selected fixture root did not exist;
- `reports/research/structured_vol_v5_replicates/_test_auth` did not exist.

Post-run state verified:

- selected fixture root did not exist;
- scientific `_test_auth` path did not exist;
- cached index contained no synthetic fixture path;
- no scientific report/model namespace was created;
- no real authorization was created;
- no execution marker, checkpoint, curve, report, or adjudication was created.

Static checks were observational only and did not access the final test set:

- `py_compile`: pass;
- Ruff: 194 findings on the pre-repair test file versus 74 on the repaired test file; no Ruff broad-formatting pass was applied;
- mypy: 182 baseline errors versus 139 on the repaired test file, all within the existing dynamic-import/untyped test-file failure class; no production/runtime mypy error was introduced.

## 4. Protected production and scientific surfaces

- frozen runner remained byte-identical: `a79a79f477429d66cc7fc0c75db7c751726ee577`;
- scientific configuration unchanged;
- seed schedule unchanged;
- Gate-v2 unchanged;
- trainer unchanged;
- runtime identity implementation unchanged;
- authorization schema unchanged;
- existing authorizations unchanged;
- execution evidence unchanged;
- external closure unchanged;
- no eligibility change;
- no CUDA/runtime-production change;
- no production authorization change.

No authorization was created. Reserve-j01 execution remains not authorized. The five-seed requirement remains unresolved. The final test remains sealed.

## 5. Required next action

Independent read-only audit of Task 091's final reserve-j01 readiness repair, including runner byte identity, zero-transit fixture hygiene, duplicate removal, independent contract and recipe identity, executing negative coverage, exact final test count, and reset-governance disclosure, before any reserve-j01 authorization freeze task.

---

*Amendment 054 records the Audit-090 repair: zero-transit ignored fixtures, no index staging or reset cleanup, independent contract and recipe identity, constrained ancestry, executing wrong-runner/wrong-contract/stale-recipe/runtime negatives, 55/55/0/0 authoritative focused-suite results, unchanged runner bytes, no authorization, no execution, unresolved five-seed requirement, and sealed final test.*
