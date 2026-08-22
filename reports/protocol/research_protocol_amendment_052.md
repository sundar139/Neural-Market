# Amendment 052 — V5 Reserve-j01 Executable Readiness Verification

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-EXECUTABLE-READINESS-TEST-087
**Risk:** R3
**Branch:** `main`
**Starting HEAD:** `5d909eb486c73537680a2661d52ae01e42ebe588`
**Safety branch:** `safety/pre-v5-reserve-j01-readiness-5d909eb` (created without switching at 5d909eb)
**Prior audits:** NM-R4-V5-RESERVE-J01-PROVENANCE-NETWORK-AUDIT-086 (VALIDATED WITH NON-BLOCKING FINDINGS), 084/082
**Status:** Executable-readiness verification — positive fully mocked j01 authorization path added, all other gates preserved. No authorization, no execution, no network in this task.

## 1. Scope and prior validation

Audit 086 validated the network provenance repair (Amendment 051 at `5d909eb...`), runner `a79a79f477429d66cc7fc0c75db7c751726ee577` remains technically VALID, reserve-j01 `13281/13282/8283` `38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` as `FIFTH_VALID_MEMBER_CANDIDATE` remains frozen. The remaining `EXECUTABLE_READINESS TEST GAP` was that `test_no_real_training_invoked_for_j01_path` actually exercised `reserve-j02` (see 050 §7 / 051 §7) and no positive synthetic mocked j01 authorization path proving traversal to the pre-scientific boundary existed. This amendment closes that gap with one positive, fully mocked prospective j01 path while keeping the runner byte-for-byte unchanged.

## 2. Runner preservation

`reports/research/evidence/structured_vol_v5_replicate_training_runner.py` pre-task blob `a79a79f477429d66cc7fc0c75db7c751726ee577` -> post-task blob `a79a79f477429d66cc7fc0c75db7c751726ee577` — **unchanged, 0 bytes**. `EXPECTED_RESERVE_J01_TUPLE = ("reserve-j01", 13281, 13282, 8283)` hygiene finding is not fixed by deleting/changing the runner constant; instead it is asserted from the test suite so the constant becomes covered (`test_reserve_j01_runner_eligible_via_eligible_constant`). No member eligibility, authorization-v2, or CUDA/runtime logic changed.

## 3. Positive fully mocked j01 path (added)

Call order recorded (real path, discovered before edit):

`CLI --member-id` -> member eligibility (`ELIGIBLE_RESERVE_J01` vs `RESERVE_MEMBERS`/`ALLOWLIST`) -> frozen schedule lookup (`reserve_policy.reserves` for j01) -> `verify_config_hash` (`38c5113b...`) -> `verify_family_hash` (`730475...`) -> `authorization-v2 parsing` (`check_authorization`/`inspect_authorization` + `authorize_execution` for CUDA) -> `Git/authorization provenance` checks -> `requested/resolved CUDA` (`resolve_device` fail-closed, `configure_device_determinism`) -> `runtime identity binding` (`build_runtime_identity` at single normative capture) -> `namespace/overwrite checks` (`derive_report_dir`/`derive_model_dir`) -> `_exclusive_create_execution_started` -> `_run_scientific_training`.

Latest safe test boundary: **immediately before `_exclusive_create_execution_started`** (to avoid production marker) and **immediately before `_run_scientific_training`** (to avoid real trainer/Gate). Positive test `test_positive_mocked_j01_traverses_to_pre_scientific_boundary` proves:

- Synthetic auth traverses all prospective identity/auth/CUDA/runtime checks: member `reserve-j01`, seed tuple `13281/13281/13282/8283`, hashes `38c5113b...`/`38c5113b27568e14`/`730475...`, schema `structured-vol-v5-primary-training-authorization-v2` with `training_authorized true`/`max_training_invocations 1`/`validation_authorized false`/`final_test_authorized false`, `requested_device cuda`/`expected_resolved_device cuda`/`expected_runtime_identity_sha256` correct, runner `a79a79f...`, schedule/execution contract identities, recipe-head ancestry via mocked `_git_head_blob`/`_is_ancestor`, and `resolve_device`/`build_runtime_identity` mocked to CUDA.

- Intercepted `_exclusive_create_execution_started` (fake_marker returning `tmp_path/report/38c5113b.../execution_started.json`) — no production `reports/research/structured_vol_v5_replicates/38c5113b27568e14/execution_started.json` created.

- Intercepted `_run_scientific_training` (fake_sci sentinel) — **TEST_ACCEPTS_SYNTHETIC_AUTHORIZATION** (rc 0 via `_main_with_mocked_auth`) and **MOCKED_SCIENTIFIC_BOUNDARY_REACHED** (sci_calls 1), while real `_run_scientific_training` body executed zero instructions — `MOCKED_SCIENTIFIC_BOUNDARY_REACHED != SCIENTIFIC_EXECUTION_PERFORMED`.

## 4. Test-hygiene closures (without runner changes)

In test file `tests/unit/research/test_v5_replicate_training_runner.py`:

- A. Renamed `test_no_real_training_invoked_for_j01_path` -> `test_refused_j02_never_invokes_scientific_training` (truthful, it exercises `reserve-j02`).

- B. Duplicate `_check_with_mock` definitions (two identical at lines 216/313) kept as single canonical helper — second removed, one helper retained. Call sites unchanged.

- C. `_make_auth_for_member` synthetic fixtures already lived under `tmp_path` with no `git add` (not in `reports/research/structured_vol_v5_replicates/_test_auth/` real evidence namespace); verified tmp_path staging produces no `report/model` evidence write. `EXPECTED_RESERVE_J01_TUPLE` covered without runner modification (D).

- E. Amendment-049 corrupted prose/blob labels are historical documentation, non-blocking and byte-immutable — not repaired here.

Negative coverage preserved: j01 without auth, wrong member/config/family/seed/prefix/runner/recipe, CPU requested/resolved, runtime mismatch, consumed namespace, j02/j03/legacy/unknown rejected — all retained. Focused suite: **49 passed, 2 skipped** (was 47/2 at 081 — +2 new: tuple coverage + positive mocked j01; lint/mypy pre-existing baseline unchanged, ruff 237 in test file pre-existing).

## 5. Production side effects verified zero

Before and after tests: `reports/research/authorizations/.../reserve*` ABSENT, `reports/research/structured_vol_v5_replicates/38c5113b27568e14/` ABSENT, `execution_started`/`checkpoint`/`checkpoint_final`/`training_curve`/`training report`/`adjudication` for j01 ABSENT. `scientific training invocations 0 REAL`, `simulation 0 REAL`, `provider/scientific network 0`, `Git-remote network 0`, `validation 0`, `external 0`, `final 0`. Tracked tree clean after tests except intended source/doc changes.

## 6. Amendment 052 is this file

Records: Audit 086 validation, runner `a79a79f...` unchanged, positive fully mocked j01 path added with layers/ boundary/ marker mock, hygiene A-D, `TEST_ACCEPTS_SYNTHETIC_AUTHORIZATION != PRODUCTION_AUTHORIZATION_CREATED` and `MOCKED_SCIENTIFIC_BOUNDARY_REACHED != SCIENTIFIC_EXECUTION_PERFORMED` (real marker not created, real training body not entered), j01 authorization still NOT CREATED, execution NOT AUTHORIZED, five-seed UNRESOLVED, final SEALED. No self-authentication.

## 7. Git / file-scope / validation discipline

Safety branch `safety/pre-v5-reserve-j01-readiness-5d909eb` done. Tracked changes: `tests/unit/research/test_v5_replicate_training_runner.py` (commit `test(research): verify reserve j01 executable readiness` `49e6c07...`) then this amendment `reports/protocol/research_protocol_amendment_052.md` (`docs(research): record reserve j01 executable readiness`) — exactly 2 files, runner source unchanged (`NO AMEND`, `NO REBASE`, `NO RESET`, `NO PUSH`, `NO NETWORK`). Focused lint/type: ruff/mypy baseline unchanged (no new errors by this task).

---

*Amendment 052 proves executable-readiness via one positive fully mocked reserve-j01 synthetic auth reaching the pre-scientific boundary with mocked marker/training, cleans up j02 naming/duplicate helper, and leaves runner `a79a79f...` byte-identical with no authorization, no execution, five-seed UNRESOLVED, final SEALED.*
