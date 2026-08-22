# Amendment 051 — V5 Reserve-j01 Provenance Network Accounting Correction

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-PROVENANCE-NETWORK-REPAIR-085
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `797889f56ed2c4901ba7140b9dd97b45e954d89c`
**Safety branch:** `safety/pre-v5-reserve-j01-network-repair-797889f`
**Repaired task:** NM-R4-V5-RESERVE-J01-RUNNER-PROVENANCE-REPAIR-083
**Independent audit:** NM-R4-V5-RESERVE-J01-RUNNER-PROVENANCE-AUDIT-084 — REPAIR REQUIRED — NETWORK ACCOUNTING ONLY
**Critical conclusion:** Amendment 050 correctly closes Task-081 prohibited-amend provenance. Runner technically VALID. Only blocking defect is Task 083 performed/recorded a Git-remote network op while Amendment 050 asserts unqualified provider/network=0.
**Status:** APPEND-ONLY NETWORK ACCOUNTING CORRECTION. No runner/test change, no authorization, no execution, no validation/external/final, no network in this task.

## 1. Reverified Task-083 network evidence (local state only, no network)

No `git ls-remote`/`fetch`/`pull`/`push`/`remote update`/`curl` operation executed in this task. Inspection is local:

- Amendment 050 records use of `git ls-remote origin main` at §2 (§2 line `Independent inspection (git log... git ls-remote origin main)`) and §2 push verification (`verified git ls-remote origin main still c2f2ff3...`). Verified verbatim via `grep -n ls-remote` on `reports/protocol/research_protocol_amendment_050.md` (lines 20/47).

- Local remote URL from `git config --get remote.origin.url` / `.git/config`: `https://github.com/sundar139/Neural-Market.git` (no network query).

- Classify `git ls-remote` against that HTTPS endpoint = **Git-remote network operation** (Git transport over HTTPS).

Also inspected local evidence reported by Audit 084:

- `.git/FETCH_HEAD` (102 bytes, `stat` Modify `2026-08-22 02:23:41.216062800 -0400`, content `c2f2ff34142acc6d31016db8631288f32480a10b branch 'main' of https://github.com/sundar139/Neural-Market`) — a remote contact occurred in that window.

- `.git/logs/refs/remotes/origin/HEAD` shows at `2026-08-22 02:23:41` an entry transitioning `c2f2ff3... c2f2ff3...` (`1787379821 -0400  remote set-head`) adjacent to the `02:23:41` `FETCH_HEAD` mtime. Same timestamp is within the Task-083 window (Task 083 ran `2026-08-22 02:23`-`02:31` region, see origin/HEAD log). This entry type is `remote set-head`, not the `update by push` type used for pushes to `refs/heads/main` (which logs `update by push` in `.git/logs/refs/remotes/origin/main`). Therefore `FETCH_HEAD`/remote set-head evidence is **NOT mechanically attributable to a bare `git ls-remote`**.

- The initiating process for that `02:23:41` contact is therefore **OBSERVED_BUT_UNATTRIBUTED** — filesystem artifacts prove a remote contact, not the process that caused it. Do not claim Hermes caused the additional contact without evidence.

Posterior note: `git ls-remote` itself is not supposed to write `FETCH_HEAD`; the `02:23:41` contact is a *second* observed remote interaction proximate to Task 083 but distinct from `ls-remote`.
## 2. Network accounting repair (supersedes Amendment 050 unqualified zero)

Supersede ONLY Amendment 050's unqualified provider/network = 0 wording (050 section 10 Require ... provider/network 0 unqualified). Freeze corrected accounting:

- provider/scientific-data network: 0
- market-data/provider API calls: 0, external-validation provider calls: 0
- Git-remote ref query explicitly performed by Task 083: 1 (via git ls-remote origin main, verified local)
- operation: git ls-remote origin main, remote: https://github.com/sundar139/Neural-Market.git
- scientific/authorization/execution effect: NONE (no external data, no auth, no --execute)
- additional Git remote contact observed at 02:23:41: YES (FETCH_HEAD 102 bytes + origin/HEAD set-head at 02:23:41) — attribution UNATTRIBUTED, DO NOT ASSIGN to Hermes, reason: filesystem proves contact not process.

## 3. Preserved Task-081 provenance repair

Amendment 050 correctly closes Task-081 prohibited-amend provenance. Preserve: pre-task HEAD c2f2ff34142acc6d31016db8631288f32480a10b, abandoned e4c1a1bb9535badf5b97bf0e2d141a007e718262 (02:07:01), amended 5e28384be24c898b7a3b1182ad6d944307398db0 (via git commit --amend at 02:08:13), Amendment-049 fe6d4a31fbb2daa9f04acabdfb5f43156826e78d. Classification B — GOVERNANCE/PROVENANCE DEFECT WITH FINAL BYTES TECHNICALLY VALID. Exact delta: one file, two tests, zero runner production (0 bytes). Preserve TASK-081 NO-AMEND VIOLATED.

## 4. Preserved runner identity

Recomputed: historical 05b704b254387d8f5ffdf1d847dd4289303b565c -> current a79a79f477429d66cc7fc0c75db7c751726ee577 (git hash-object at 797889f). Future reserve-j01 auth must bind runner_git_blob = a79a79f... at/after 5e28384... per ancestry checks. No authorization created.

## 5. Narrowed pre-amend CPU-test narration

Amendment 050 section 3B states pre-amend failure as verified fact though partly inferred. Verified: pre-amend used direct check_authorization(...), post-amend uses _check_with_mock(..., "must be cuda|cuda") reaching authorize_execution cuda|cuda. If exact pre-amend failure boundary not proven without replay, label INFERRED_NOT_REPLAYED. This task narrows to verified form above.

## 6. Residual findings (verified only, no guessing)

All five A-E verified locally (no source/test mutation):

A. dead EXPECTED_RESERVE_J01_TUPLE = ("reserve-j01", 13281, 13282, 8283) in runner — defined line 66, zero refs.
B. duplicate _check_with_mock at lines 216/316 (second shadows first).
C. _test_auth inside reports/research/structured_vol_v5_replicates/_test_auth/ — ephemeral, cleaned.
D. corrupted restMethodologyDevice-immutable in 049 line 64.
E. blob range mislabel 039 4c8a24a... is actually 047 blob; 039 blob is 53a6aac4...

All OPEN_NONBLOCKING_DOCUMENTATION_OR_TEST_HYGIENE.

## 7. Executable-readiness gate preserved

reserve-j01 runner eligibility VALIDATED, executable-readiness NOT YET VALIDATED. test_no_real_training_invoked_for_j01_path exercises reserve-j02 not j01. No positive mocked j01 path exists. Gap pending separate task before authorization. No tests changed.

## 8. Amendment 051 is this file

Records: Audit 084 verdict, 050 provenance valid, network=0 superseded by section 2, provider 0 / Git-remote 1, 02:23:41 observed-but-unattributed, runner unchanged, CPU-test narrowed, findings A-E, readiness pending, five-seed UNRESOLVED, final SEALED. No self-authentication.

## 9. Git / firewall discipline

Safety branch pre-v5-reserve-j01-network-repair-797889f done. Exactly one new tracked file: 051.md — commit docs(research): correct reserve j01 network provenance — NO AMEND/REBASE/RESET/PUSH, NO NETWORK in this task. No authorization/namespace created. Require training 0 --execute 0 simulation 0 reserve 0 auth 0 validation 0 new external 0 final 0 provider/scientific 0 Git-remote in Task 085 0. Tracked clean.
