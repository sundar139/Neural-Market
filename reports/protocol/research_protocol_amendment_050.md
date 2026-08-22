# Amendment 050 — V5 Reserve-j01 Runner Provenance Correction

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-RUNNER-PROVENANCE-REPAIR-083
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `fe6d4a31fbb2daa9f04acabdfb5f43156826e78d`
**Safety branch:** `safety/pre-v5-reserve-j01-runner-provenance-fe6d4a3` (created without switching at fe6d4a3)
**Repaired task:** NM-R4-V5-RESERVE-J01-RUNNER-ELIGIBILITY-081
**Independent audit:** NM-R4-V5-RESERVE-J01-RUNNER-ELIGIBILITY-AUDIT-082 — REPAIR REQUIRED — GOVERNANCE/PROVENANCE ONLY
**Critical audit conclusion:** THE FINAL RUNNER IMPLEMENTATION IS TECHNICALLY VALID (Audit 082 validates `reserve-j01` narrow eligibility, `j02`/`j03` rejection, `authorization-v2` mandatory, `CUDA-only`). Only the git provenance of how the final source commit was obtained violates history governance.
**Status:** APPEND-ONLY PROVENANCE CORRECTION. No source change, no test change, no authorization, no --execute, no training/simulation/reserve execution, no validation/external/final/hedging.

## 1. Scope and classification

The only blocking defect is Task 081's use of `git commit --amend` despite an explicit `NO AMEND` requirement, and Amendment 049's durable description of that operation being incomplete (abbreviated commit, only one of two modified tests, no reflog evidence, no explicit `VIOLATED` classification). Final runner bytes `a79a79f477429d66cc7fc0c75db7c751726ee577` are TECHNICALLY VALID — no production logic, config, or scientific byte changes across the amend. Do NOT modify `reports/research/evidence/structured_vol_v5_replicate_training_runner.py`, `tests/unit/research/test_v5_replicate_training_runner.py`, or any scientific/config/runtime artifact in this task. Exact delta is independently reconstructable; proper repair is append-only documentation, not rewriting history again.

## 2. Reverified history (read-only before writing)

Independent inspection (`git log --graph --decorate --oneline --all`, `git reflog --date=iso`, `refs/heads/main` reflog `.git/logs/refs/heads/main`, `git cat-file -t`, `git diff --stat/--numstat/--` between the two source commits, `git ls-remote origin main`).

Require exact history:

- Pre-task HEAD: `c2f2ff34142acc6d31016db8631288f32480a10b` — `docs(research): correct v5 fifth-member semantics` (parent `265d2b2...`).

- Initial source commit: `e4c1a1bb9535badf5b97bf0e2d141a007e718262` — parent `c2f2ff34142acc6d31016db8631288f32480a10b` — `commit: fix(research): admit selected v5 reserve j01` — **ordinary source commit** timestamp `2026-08-22T02:07:01-04:00` (reflog: `e4c1a1b HEAD@{2026-08-22 02:07:01 -0400}: commit: fix(research): admit selected v5 reserve j01`).

- Final amended source commit: `5e28384be24c898b7a3b1182ad6d944307398db0` — parent also `c2f2ff34142acc6d31016db8631288f32480a10b` — created through **`git commit --amend`** — timestamp in reflog `2026-08-22T02:08:13-04:00` (`HEAD@{2026-08-22 02:08:13 -0400}: commit (amend): fix(research): admit selected v5 reserve j01`) — raw committer timestamp `1787378893` (reflog as evidence; the raw author `1787378821` carries the original moment).

- Amendment-049 commit: `fe6d4a31fbb2daa9f04acabdfb5f43156826e78d` — `docs(research): record reserve j01 runner eligibility` — parent `5e28384...` (reflog `fe6d4a3 HEAD@{2026-08-22 02:09:20 -0400}: commit: docs(research): record reserve j01 runner eligibility`).

- `git cat-file -t` for both source commits: both `commit` (verified).

Require reflog evidence equivalent to (reworded timing exact):

```
e4c1a1b ... commit: fix(research): admit selected v5 reserve j01
5e28384 ... commit (amend): fix(research): admit selected v5 reserve j01
```

Verified reflog `HEAD@{...}: commit: ...` vs `HEAD@{...}: commit (amend): ...` with the `(amend)` qualifier distinguishing the rewrite — exact as above (see §1).

Verify no `reset`, `rebase`, `push`:

- `reset`: `NONE` — no reflog `reset:` entry, no `branch -m`/`reset --hard`/`checkout -B` rewriting.
- `rebase`: `NONE` — no `rebase` reflog line, history repoints directly `c2f2ff3 -> e4c1a1b -> 5e28384 -> fe6d4a3` linear.
- `push`: `NONE` — `origin/main` remained `c2f2ff34142acc6d31016db8631288f32480a10b` for the window (verified `git ls-remote origin main` still `c2f2ff3...`, reflog origin never updated past `c2f2ff3...`, `.git/logs/refs/remotes/origin/main` unchanged).

State explicitly: **TASK-081 NO-AMEND REQUIREMENT: VIOLATED.** Do not rationalize the violation away because the commit was local/unpushed. An explicit governance `NO AMEND` is violated by any `git commit --amend` regardless of push status — the history rewrite is durable (abandoned commit `e4c1a1b...` remains recoverable) and must be recorded.

## 3. Exact pre-amend → post-amend delta

Diff `e4c1a1bb9535badf5b97bf0e2d141a007e718262` against `5e28384be24c898b7a3b1182ad6d944307398db0` (`git diff --stat/--numstat`):

- Files differing: **exactly one** — `tests/unit/research/test_v5_replicate_training_runner.py` — `1 file changed, 5 insertions(+), 6 deletions(-)` (`git diff --numstat: 5\t6\ttests/unit/research/test_v5_replicate_training_runner.py`). **Production runner difference: NONE** (`git diff ... -- reports/research/evidence/structured_vol_v5_replicate_training_runner.py` is `0 bytes`, `diff --stat` shows no runner file).

Both changed test functions exactly (hunk-level verbatim):

A. `test_allowed_member_dry_run` — pre-amend target `v5-seed-05` → post-amend target `reserve-j01` — reason observable from repository state: `v5-seed-05`'s namespace `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba` and `data/processed/research/model/structured-volatility-neural-sde-v5/1e8aa171993a1aba` now exist after its completed execution `f72db0b...` (all primaries `62c7406...`/`e333325...`/`77e7de...`/`1e8aa...` now present, so every `v5-seed-02..05` dry-run hits `overwrite refusal`); `reserve-j01` (`38c5113b27568e14`) is the selected eligible member whose real namespace does NOT exist (verified `ls reports/research/structured_vol_v5_replicates/38c5113b27568e14 → No such file` and model `38c5113b... → No such file`). Dry-run pivot is provenance-correct.

B. `test_j01_cpu_requested_rejected` — pre-amend: `direct pytest.raises around check_authorization, failing earlier on the untracked-file/git boundary` (the test created a tracked temp auth but without `git add`/`_check_with_mock` staging boundary, so it hit `authorization not committed` before reaching `authorize_execution`). Post-amend: `uses _check_with_mock(..., "reserve-j01", "must be cuda|cuda")` so the test reaches the intended `authorize_execution` CUDA pair check (`requested_device == expected_resolved_device == "cuda"` required; `cpu/cpu` → `must be cuda|cuda`). Patch narration reduced three comment lines to one mock-boundary comment.

Record:

- runner production-source difference: **0 bytes** (verified `git diff -- .../structured_vol_v5_replicate_training_runner.py` empty).
- scientific code difference: **0 bytes** (no `src/neuralmarket/...`, `configs/...`, `data/...` change).
- config difference: **0 bytes** (no `configs/research/structured_vol_neural_sde_v5.yaml` change).
- eligibility-semantic difference: **NONE** — narrow `reserve-j01` (ELIGIBLE_RESERVE_J01, `EXPECTED_CONFIG_HASHES[reserve-j01] 38c5113b...`, `reserve_policy` lookup) vs `reserve-j02`/`reserve-j03`/unknown `REFUSED` semantics identical across the amend; the amend only polishes test reachability.

Do not call the amend a one-test change — it touched two tests (`test_allowed_member_dry_run` + `test_j01_cpu_requested_rejected`).

## 4. Governance violation classification

Freeze Audit 082's classification (this amendment adopts it verbatim):

> **B — GOVERNANCE/PROVENANCE DEFECT WITH FINAL BYTES TECHNICALLY VALID.**

Why this classification is bounded (independent verifications supporting the bound):

- explicit `NO-AMEND` requirement was violated (Task 081 §10 `NO AMEND` — see §6 for incomplete disclosure);
- abandoned commit `e4c1a1bb9535badf5b97bf0e2d141a007e718262` remains fully recoverable via `git cat-file -p`/`git reflog`/`git log --all` (reachable as `5e28384^` predecessor);
- exact delta is independently reconstructable in 11 lines of `git diff` (see §3 above);
- delta touched **tests only** (`tests/unit/research/test_v5_replicate_training_runner.py` single file, 5+/6-), **no production runner** bytes changed (0 bytes);
- final production runner logic (`ELIGIBLE_RESERVE_J01`, `EXPECTED_CONFIG_HASHES[reserve-j01]`, `get_member reserve_policy branch`, `main` guard `!= ELIGIBLE and not in ALLOWLIST`) did **not** change across the amend (identical in both commits);
- **no reset** (no `reset:` reflog, no detached history rewrite beyond `amend`);
- **no rebase** (linear history, no `rebase` reflog);
- **neither source commit was pushed** (origin/main remained `c2f2ff3...` through both; `git ls-remote origin main` still `c2f2ff3...`);
- **no scientific execution** occurred (no `--execute`, no runner `execution_started`, no checkpoint/curve/Gate);
- **no `reserve-j01` authorization existed** before or after the amend (authorizations `reserve*` absent);
- **no scientific/checkpoint/config bytes changed** (verified `diff --stat` only-test file);

What this classification does NOT mean (explicitly supersede any implicit broadening):

- it does **not** make the amend compliant — `NO-AMEND VIOLATED` is durable;
- it does **not** erase the history rewrite — `e4c1a1b...` remains an abandoned commit in reflog and `git log --all` (not garbage-collected);
- it does **not** authorize `reserve-j01` (authorization artifact still `ABSENT`; `RUNNER_ELIGIBLE != EXECUTION_AUTHORIZED`);
- it does **not** change technical eligibility conclusions (`reserve-j01` ELIGIBLE, `j02`/`j03`/unknown REFUSED, `CUDA-only` unchanged remain validated);
- it does **not** permit future `amend`/`rebase`/`reset` shortcuts — every future task must obey its `NO AMEND`/`NO REBASE`/`NO RESET`/`NO PUSH` directly.

The proper repair is append-only documentation (this amendment), not rewriting history again by `reset --hard`/`rebase --onto` to hide the abandoned commit.

## 5. Amendment 049's incomplete history description — superseded

Read Amendment 049 §10 paragraph `Preferred commits performed:` directly (committed `fe6d4a3...`, §10 lines):

```
- `fix(research): admit selected v5 reserve j01` containing only runner + tests
  (`e4c1a1b...` amended to `5e28384...` after polishing
  `test_allowed_member_dry_run`).
- `docs(research): record reserve j01 runner eligibility` containing only
  Amendment 049 (next section, `NO AMEND`, etc.).
```

Current **amend** disclosure (exactly as committed): `e4c1a1b... amended to 5e28384... after polishing test_allowed_member_dry_run.` (abbreviated 7-char prefix, single-test narration, no reflog chronology, no explicit `VIOLATED` label).

Record precisely why that disclosure is incomplete (independent read from committed `reports/protocol/research_protocol_amendment_049.md` at `fe6d4a3...`):

- abandoned commit is **abbreviated** (`e4c1a1b...`) rather than full `e4c1a1bb9535badf5b97bf0e2d141a007e718262`;
- it does **not reproduce** the independent reflog evidence (`HEAD@{2026-08-22 02:07:01 -0400}: commit: fix(research): ...` → `HEAD@{2026-08-22 02:08:13 -0400}: commit (amend): fix(research): ...`) proving the `amend` path;
- it **describes only one modified test** (`test_allowed_member_dry_run`); it **omits** the `test_j01_cpu_requested_rejected` change (`direct pytest.raises` → `_check_with_mock(..., "must be cuda|cuda")`);
- it **does not clearly classify** the explicit Task-081 `NO-AMEND` requirement as `VIOLATED` — the phrase `amended to` is used without the normative label `TASK-081 NO-AMEND REQUIREMENT: VIOLATED`.

Do NOT edit Amendment 049 (remains byte-immutable at `f551493e501b643ef5a5dae5b40ad1a6126c26b2`). Amendment 050 supersedes ONLY this incomplete governance/history record (this §5 and §§2–4 fuller chronology). Keep Amendment 049's valid conclusions about: `reserve-j01` narrow eligibility (`ELIGIBLE_RESERVE_J01`), `j02`/`j03` rejection, authorization mandatory, `CUDA-only`, no execution, five-seed UNRESOLVED, final SEALED — all unchanged.

## 6. Final runner identity and authorization consequence

Independently recomputed from committed bytes (`git hash-object reports/research/evidence/structured_vol_v5_replicate_training_runner.py` at `fe6d4a3...` and at `5e28384...` — identical):

- Historical pre-Task-081 runner blob (committed at `c2f2ff3...`): `05b704b254387d8f5ffdf1d847dd4289303b565c`.
- Final runner blob (committed after Task 081 at `5e28384...` and carried into `fe6d4a3...`): `a79a79f477429d66cc7fc0c75db7c751726ee577` (verified `git hash-object` = `a79a79f...`).

As a historical identity only, state the transition explicitly:

> **RUNNER_BLOB:** `05b704b254387d8f5ffdf1d847dd4289303b565c` → `a79a79f477429d66cc7fc0c75db7c751726ee577`.

Freeze the consequence (authorization-v2 binding for any future `reserve-j01` authorization artifact):

- ANY future `reserve-j01` `authorization-v2` artifact MUST bind `runner_git_blob = a79a79f477429d66cc7fc0c75db7c751726ee577` (the final committed runner at `5e28384...`/`fe6d4a3...` containing `ELIGIBLE_RESERVE_J01` + `EXPECTED_CONFIG_HASHES[reserve-j01]` + `reserve_policy` branch), not the historical `05b704b...`.
- And `execution_recipe_head` MUST be a valid ancestor point containing the `reserve-j01` runner eligibility change, therefore **at or after** `5e28384be24c898b7a3b1182ad6d944307398db0` (the amended source commit), subject to the existing `authorization-v2` ancestry checks (`_is_ancestor(recipe_head)` and `recipe commit must contain runner/contract/schedule at correct blobs`).

Do NOT create that authorization in this task. Do NOT mutate the runner to preserve compatibility with old authorizations (historical consumed `v5-seed-05` authorization `d777663...` remains historical, `c937742...` authorized before `j01` eligibility — not reused for `j01`).

## 7. Open test-readiness gap (record without fixing)

Audit 082 independently found:

> `test_no_real_training_invoked_for_j01_path` does NOT execute a `reserve-j01` path. It invokes `reserve-j02` and proves only that an early-refused `reserve-j02` does not reach training.

Verified directly `tests/unit/research/test_v5_replicate_training_runner.py` function `test_no_real_training_invoked_for_j01_path` (lines ~1006–1024): body is `_runner.main(["--member-id", "reserve-j02"])` with `assert called["n"] == 0` — name says `j01` but member exercised is `reserve-j02` (hard-refused `RESERVE_MEMBERS` path, never reaches `_run_scientific_training`).

Record the mismatch exactly: **the test name overstates its actual coverage** — it proves the generic `non-eligible reserve early refusal ⇒ no training` invariant, not the `eligible reserve-j01 with valid authorization ⇒ traverses eligibility→config→authorization-v2→CUDA/runtime preflight to the immediate pre-scientific boundary without real science` path.

Also record: **there is currently NO positive synthetic/mock test that supplies a fully valid `reserve-j01` authorization (checked via `_check_with_mock`/`_main_with_mocked_auth` pattern) and proves `reserve-j01` can traverse `member eligibility → schedule/config/family identity → authorization-v2 validation → CUDA/runtime preflight` to the immediate pre-scientific-training boundary while `_run_scientific_training` is mocked and never performs real science.**

Classification (Audit 082 language): **NOT A DEFECT IN `reserve-j01` ELIGIBILITY** but **EXECUTABLE_READINESS TEST GAP.** Eligibility itself is VALIDATED (dry-run `reserve-j01` OK at `38c5113b...`, config/family re-verified, `j02`/`j03` refused).

Freeze: this gap **MUST be closed in a separate governed source/test task after Amendment 050 is independently audited and BEFORE the real `reserve-j01` authorization freeze** (so that the next authorization task can assert readiness without inventing tests inline). Do NOT add/fix/rename tests in Task 083. Do NOT create an authorization. A non-mocked `--execute` is never permitted in a test.

## 8. Only independently verified documentation findings

Audit 082's supplied transcript may not expose every numbered non-blocking finding referenced by its recommendation. Do NOT guess missing findings. Independently record only defects directly supported by committed bytes or Audit-082 evidence available here.

At minimum (independently verified, see §2–§7):

- Amendment 049 amend history is incomplete (see §5 — abbreviated commit, single-test narration, no reflog, no `VIOLATED` label).
- `test_no_real_training_invoked_for_j01_path` name/content mismatch (j01-named but j02-exercised; §7).
- Amendment 049 repeats the same `j01`/`j02` no-training overstatement in §11 narrative (`Protected and unchanged verification` includes no-training claim; inherits the test's gap — same class, not a separate finding).
- Final runner blob `a79a79f...` must be distinguished from historical `05b704b...` (see §6) — Amendment 049 §11 lists runner blob only at final value without contrasting the historical `05b704b...` identity (label completeness, not eligibility change).
- Pre-existing Ruff/mypy baseline remains unrelated to this repair (`ruff check ... --line-length 700 ... Found 237 errors` and `mypy import-untyped/unused-ignore 5+4` in runner — same before/after; unrelated to amend).

Do **no** repository-wide cleanup beyond this correction.

If no additional directly verifiable findings exist beyond 039–049 blobs/schedule/sensitivity distinction: state **NO_ADDITIONAL_DURABLE_FINDINGS_ESTABLISHED.** For this amendment, the above four are the independently verified set; nothing additional is independently established beyond them without guessing.

## 9. Append-only Amendment 050 (this file)

Create exactly `reports/protocol/research_protocol_amendment_050.md` (this file) with the content above. It must record: Audit 082 verdict; runner technical status VALIDATED; Task-081 `NO-AMEND` violation; full abandoned commit `e4c1a1bb9535badf5b97bf0e2d141a007e718262`; full amended commit `5e28384be24c898b7a3b1182ad6d944307398db0`; exact reflog chronology `02:07:01 -0400` → `02:08:13 -0400` → `02:09:20 -0400` with `(amend)` qualifier; no `reset`/`rebase`/`push` (`origin/main` stayed `c2f2ff3...`); exact one-file/two-test amend delta (see §3); production runner unchanged across amend (`0 bytes`); scientific/config bytes unchanged (`0 bytes`/`0 bytes`); classification B; Amendment 049 history-description supersession (§5); historical vs current runner blobs (`05b704b...` → `a79a79f...`); future authorization runner-binding consequence (`runner_git_blob = a79a79f...` at or after `5e28384...`); open positive mocked `reserve-j01` executable-readiness test gap (name/content mismatch); no source/test mutation in Task 083; no authorization; no execution; `reserve-j01` remains `FIFTH_VALID_MEMBER_CANDIDATE`; `j02`/`j03` remain unselected/not authorized; five-seed UNRESOLVED; final SEALED.

Do NOT embed Amendment 050's own future SHA/blob inside itself — future identity is `git hash-object` / `sha256sum` after commit (see §10 report).

## 10. Git / file-scope / firewall discipline

Create safety branch without switching: `safety/pre-v5-reserve-j01-runner-provenance-fe6d4a3` (done). Create exactly one tracked file: `reports/protocol/research_protocol_amendment_050.md` — commit `docs(research): record reserve j01 runner provenance` — `NO AMEND`, `NO REBASE`, `NO RESET`, `NO PUSH`. After commit verify runner/test bytes remain exactly unchanged from `fe6d4a31fbb2daa9f04acabdfb5f43156826e78d` (`git hash-object` and `git diff --quiet HEAD` checks in §10 report). No authorization artifact (`reserve*` absent), no `reserve-j01` namespace (`38c5113b...` absent), no marker/checkpoint/curve/report/adjudication created. Require `training 0 --execute 0 simulation 0 reserve execution 0 authorization creation 0 validation 0 new external 0 final access 0 provider/network 0` — all verified before commit (no `--execute` performed; only read-only `git`/`sha256sum`/`ls`/`file` and committed-byte scans).

Final tracked tree clean — only pre-existing untracked `neural_sde_signature_v3/v4_report.json` + `structured_vol_v5_report.json` remain intentionally untracked per repo pattern.

## 11. Required next action

Independent read-only audit of Amendment 050 runner provenance repair (verify: §2 history exact, §3 delta one-file/two-tests production-zero, §4 B classification bounded, §5 Amendment 049 supersession narrowed, §6 runner blobs and future authorization binding exact, §7 open positive `reserve-j01` test gap recorded without fixing, §8 no guerrilla findings, single append-only file, final sealed) before any authorization task for `reserve-j01` may be considered. The `reserve-j01` authorization itself is a later separately governed task, now executable-readiness-gated by the closing of the §7 gap first.

---

*Amendment 050 corrects only Task-081 provenance — Task-081 violated its explicit NO AMEND by turning* `e4c1a1bb9535badf5b97bf0e2d141a007e718262 (2026-08-22T02:07:01-04:00 commit) into 5e28384be24c898b7a3b1182ad6d944307398db0 via git commit --amend (reflog 02:07:01 → 02:08:13 (amend) → fe6d4a3 02:09:20, no reset/rebase/push, origin/main stayed c2f2ff3...) touching only tests (5+/6- test_allowed_member_dry_run v5-seed-05→reserve-j01 and test_j01_cpu_requested_rejected direct→_check_with_mock, runner production 0 bytes), classified B (governance/provenance defect with final bytes valid, abandoned commit recoverable, delta reconstructable, no science changed), supersedes Amendment 049's incomplete amend disclosure (abbreviated, single-test, no reflog, no VIOLATED label), freezes current runner a79a79f477429d66cc7fc0c75db7c751726ee577 (from 05b704b...) as future authorization binding at or after 5e28384..., notes the j02-exercising misnamed test as an executable-readiness gap (not eligibility defect) to be closed next, and leaves reserve-j01 FIFTH_VALID_MEMBER_CANDIDATE / j02/j03 not authorized / five-seed UNRESOLVED / final SEALED unchanged.*
