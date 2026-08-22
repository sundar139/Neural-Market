# Amendment 049 — V5 Reserve-j01 Runner Eligibility

**Date:** 2026-08-22
**Task:** NM-R4-V5-RESERVE-J01-RUNNER-ELIGIBILITY-081
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `c2f2ff34142acc6d31016db8631288f32480a10b`
**Safety branch:** `safety/pre-v5-reserve-j01-runner-eligibility-c2f2ff3` (created without switching at c2f2ff3)
**Prior audit:** NM-R4-V5-FIFTH-MEMBER-SEMANTICS-REPAIR-AUDIT-080 — VALIDATED WITH NON-BLOCKING FINDINGS (047/048 chain validated; policy `DETERMINISTIC_FIRST_RESERVE_PROMOTION` with `reserve-j01` as `FIFTH_VALID_MEMBER_CANDIDATE` validated)
**Status:** ELIGIBILITY ONLY — smallest prospective runner/test change to admit exactly `reserve-j01` on the existing governed CUDA training surface. No authorization, no --execute, no training/simulation/checkpoint/curve/Gate, no j02/j03 enablement, no validation/external/final/hedging.

## 1. Purpose and prior validation

Audit 080 validated the frozen policy chain (Amendment 047 `DETERMINISTIC_FIRST_RESERVE_PROMOTION` with `reserve-j01` `13281/13282/8283` `38c5113b...` as `FIFTH_VALID_MEMBER_CANDIDATE` at `265d2b2...` and its semantics repair Amendment 048 at `c2f2ff3...`, both `DECIDED_PENDING`/`REPAIRED_PENDING`) and reported the known prerequisite:

> The committed training runner currently hard-refuses reserve members and its current allowlist does not admit `reserve-j01` — `reserve-j01 is currently rejected before scientific execution.`

This amendment closes that prerequisite by the smallest prospective change necessary for the *existing* governed CUDA training surface to admit *exactly* `reserve-j01` — the already selected fifth-member candidate — while keeping all other reserves hard-refused. No authorization is created and no scientific execution is authorized or performed.

## 2. Pre-change runner inspection (read-only before edit)

Inspected `reports/research/evidence/structured_vol_v5_replicate_training_runner.py` at `c2f2ff3...` (runner blob `05b704b...` line lineage):

- `ALLOWLIST = {"v5-seed-02", "v5-seed-03", "v5-seed-04", "v5-seed-05"}` (line 44)
- `RESERVE_MEMBERS = {"reserve-01","reserve-02","reserve-03","reserve-j01","reserve-j02","reserve-j03"}` (lines 59–66) — includes `reserve-j01`
- `EXPECTED_CONFIG_HASHES` (lines 50–56) — five entries `v5-seed-01..05` only (`38c5113b...` for `reserve-j01` absent)
- `get_member(schedule, member_id)` — searches `schedule["primary_members"]` only; no `reserve_policy` branch
- `derive_effective_config(member_id)` → `get_member` + `load_v5_config` → `V5ExperimentConfig`; fails for `reserve-j01` (`not in primary_members`)
- `verify_config_hash` / `verify_family_hash` / `check_no_overwrite` — all via `derive_effective_config` and `EXPECTED_CONFIG_HASHES`
- Main control flow: `RESERVE_MEMBERS` hard-refuse (line 728 `if member_id in RESERVE_MEMBERS: REFUSED`) → `ALLOWLIST` check → `_runner_self_check` → `load_schedule`/`get_member`/`verify_config_hash`/`verify_family_hash` → `derive_report_dir`/`derive_model_dir` → overwrite check → dry-run or `check_authorization` → device `resolve_device` (fail-closed) → `configure_device_determinism` → `build_runtime_identity` at normative capture → runtime binding → `_exclusive_create_execution_started` → `_run_scientific_training`

Exact control flow from CLI member argument: `CLI member arg` → `RESERVE_MEMBERS in check (hard refuse)` → `ALLOWLIST in check` → `runner self-identity (tracked/HEAD/clean)` → `authorization check (v2 required)` → `config_hash (derive + EXPECTED)` → `family_identity` → `runtime/device (resolve + determinism + identity capture + binding)` → `irreversible marker (exclusive hard-link)` → `one-shot invocation accounting (_SCIENTIFIC_INVOCATIONS >=1)`.

Confirming Audit 080's finding directly (inspection, no `--execute` needed): `reserve-j01` was rejected at the first `RESERVE_MEMBERS` branch (`line 728`) before any authorization/config/runtime/marker logic — `REFUSED: reserve execution not authorized: reserve-j01` (pre-change). Exact source file/symbol/branch: `reports/research/evidence/structured_vol_v5_replicate_training_runner.py` lines `59–66 RESERVE_MEMBERS` containing `reserve-j01`, matched at line `728 if member_id in RESERVE_MEMBERS` returning `2`.

## 3. Reserve-j01 is the only member this task may enable (verified)

Amendments 047 (`265d2b2...`) and 048 (`c2f2ff3...`) plus frozen seed schedule `reports/research/structured_vol_v5_seed_schedule_v1.json` (blob `558d08b...`, SHA `8c471c...`):

- Selected policy: `DETERMINISTIC_FIRST_RESERVE_PROMOTION` (047 §5 chosen, 048 preserved)
- Selected candidate: **only** `reserve-j01` — `reserve-j02`, `reserve-j03` are `UNSELECTED NOT AUTHORIZED` (047 §9/048 §6/§10, no automatic `j02`/`j03` chain)
- Exact `reserve-j01` identity verified from committed schedule `reserve_policy.reserves[0]` and recomputed `V5ExperimentConfig.config_hash()`: `replicate 13281` / `model/init 13281` / `data 13282` / `eval 8283` (COMMON_FIXED) → `config 38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` prefix `38c5113b27568e14` family `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (identical RNG-stripped family to primaries; recomputed via `canonical_dumps` stripping `model_init_seed`/`data_seed`).
- `j02 14281/14282` → `423277df...` and `j03 15281/15282` → `e89b0ac...` remain NOT ELIGIBLE.
- This task MUST NOT generically enable all reserves and does not: `startswith("reserve-")` and `member in all schedule members` were inspected and are **absent** from the change; identification uses the same exact-identity discipline as primaries (single pinned constant `ELIGIBLE_RESERVE_J01`).

A broader abstraction making j01-only impossible was not needed — narrow exception succeeded — so task reports `BLOCKED` does not apply.

## 4. Minimal runner eligibility change (lazy-senior ladder — YAGNI → reuse existing runner patterns → stdlib → minimum diff)

Only the governed v5 training runner was changed, by the smallest explicit diff carrying the eligibility through the two load-bearing stages:

- **(a) Identity constants:** added one pinned constant `ELIGIBLE_RESERVE_J01 = "reserve-j01"` (Amendments 047/048) and **removed** `reserve-j01` from `RESERVE_MEMBERS` (`reserve-01/02/03/j02/j03` remain refused). `RESERVE_MEMBERS` now has 5 entries, not 6. The hard-refuse guard `if member_id in RESERVE_MEMBERS` now excludes `reserve-j01` by omission — the same narrow allowlist discipline.

- **(b) Expected-hash registry:** extended `EXPECTED_CONFIG_HASHES` with one entry `[ELIGIBLE_RESERVE_J01]: "38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605"` (frozen schedule-derived; `RUN_PREFIXES` follows via `{k: v[:16] for k, v in EXPECTED_CONFIG_HASHES.items()}`). Expected tuple `EXPECTED_RESERVE_J01_TUPLE = ("reserve-j01", 13281, 13282, 8283)` added for family-check symmetry. No new abstraction introduced beyond using the existing `EXPECTED_CONFIG_HASHES` key pattern.

- **(c) Schedule lookup:** `get_member(schedule, member_id)` now falls through to `schedule["reserve_policy"]["reserves"]` slot lookup **only when `member_id == ELIGIBLE_RESERVE_J01`** — returning `{member_id,replicate_seed,model_init_seed,data_seed,eval_seed}` from the frozen `reserve_policy` JSON. No generic `member_id in reserves` widening.

- **(d) Main allow path:** `ALLOWLIST` remains unchanged (`v5-seed-02..05`); gate becomes `if member_id != ELIGIBLE_RESERVE_J01 and member_id not in ALLOWLIST` with error message `sorted(ALLOWLIST | {ELIGIBLE_RESERVE_J01})` for clarity. No allowlist removed; no reserve safety concept replaced; no permissive pattern.

Result: existing primary members unchanged; `reserve-j01` becomes eligible prospectively via the same exact identity discipline (config-hash via `derive_effective_config` now succeeding through the reserve_policy branch, family check `730475...`, prefix `38c5113b...`); all other reserves (`j02`/`j03`/legacy) and unknown members (`v5-seed-99`, `reserve-j01o`, etc.) remain `REFUSED` (`rc=2`). No `startswith` or config-prefix-only authorization path was introduced.

## 5. Authorization-v2 and identity fail-closed behaviour preserved

Schema `reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json` (`structured-vol-v5-primary-training-authorization-v2`, amendment 036, extends `v1` with `requested_device`/`expected_resolved_device`/`expected_runtime_identity_sha256`): member `reserve-j01` is **representable without schema modification** — `member_id` is free string type (no allowlist constraint), `full_config_hash` any 64 hex, `family_methodology_identity` any 64 hex. Can bind `training_authorized/max_training_invocations/reserve/restMethodologyDevice-immutable` with every `REQUIRED_AUTH_FIELDS_V2` field including `family_methodology_identity expected_runtime_identity_sha256` and device pair.

Do NOT create an authorization artifact in this task — verified `reports/research/authorizations/structured_vol_v5_primary_training/reserve*` absent, no `v2` JSON emitted for `reserve-j01`. Do NOT edit the authorization schema — schema inspection confirmed representation without migration; `BLOCKED_SCHEMA_PREREQUISITE` does not apply.

Runner remains fail-closed on: missing authorization, wrong authorization version (`v1` historical-only), wrong member (`member_id mismatch`), wrong config (`full_config_hash mismatch` against `EXPECTED_CONFIG_HASHES[reserve-j01]`), wrong family (`730475...` mismatch), wrong runtime (`expected_runtime_identity_sha256` mismatch), wrong requested/resolved device (`must be cuda==cuda`), `CUDA unavailable` (resolve `fail closed`), authorization already consumed (hard-link exclusive marker), invocation count exceeded (`_SCIENTIFIC_INVOCATIONS >=1`). The `eligible_reserve_j01` verifier helpers (`verify_config_hash`/`verify_family_hash`) enforce the same discipline as primaries.

## 6. CUDA-only current-science policy preserved

For `reserve-j01` eligibility, preserved (no change to algorithm/config):

- `requested_device = cuda`, `resolved_device = cuda`, `CUDA unavailable = fail closed` (no CPU fallback for current-science)
- `runtime identity` algorithm `src/neuralmarket/core/runtime_identity.py` (`runtime-identity-v1` at capture `after resolve_device + configure_device_determinism before execution_started`), determinism `configure_determinism(True)` + `configure_device_determinism(device)`, CUDA recipe (`6a6b9f...` lineage), trainer device policy (`train_internal_v3` device-threaded), Gate-v2 device policy — **all unchanged**
- Historical CPU members (`01`/`02`/`04` `GATE_PASS_VALID` CPU `2.13.0+cpu` plus `03` invalid) remain immutable
- No new CPU execution path for `reserve-j01` was created
- Test: any prospective `reserve-j01` request `requested_device=cpu`/`expected_resolved_device=cpu` is **rejected before marker creation** at authorization layer (`check_authorization` → `authorize_execution` validates `requested==cuda and expected==cuda`, raises `must be cuda` — verified via `test_j01_cpu_requested_rejected`)

## 7. Minimum test coverage (reused existing runner test file, no new architecture)

Extended `tests/unit/research/test_v5_replicate_training_runner.py` (existing file, no new test architecture). Focused coverage proving at minimum:

- **A.** `reserve-j01` recognized as eligible at member eligibility layer — `test_reserve_refused` now asserts `reserve-j01 not in RESERVE_MEMBERS` and `ELIGIBLE_RESERVE_J01 == "reserve-j01"`; `test_allowed_member_dry_run` now exercises `reserve-j01` dry-run (the only reserve without a replicate dir; all primaries `1e8aa...` now exist) with `DRY RUN OK reserve-j01` `38c5113b...` verified.
- **B.** `reserve-j02` remains rejected — `test_reserve_refused` keeps `reserve-j02` in refusal list; `test_j02_j03_and_unknown_remain_rejected` asserts `reserve-j02 -> 2`.
- **C.** `reserve-j03` remains rejected — same two tests.
- **D.** Unknown reserve/member remains rejected — `test_unknown_member_refused` plus `test_j02_j03_and_unknown_remain_rejected` (`reserve-02`, `reserve-99`, `v5-seed-99`, `reserve-j01o` → 2).
- **E.** `reserve-j01` without authorization remains fail-closed before marker — `test_j01_without_authorization_fail_closed` (`None` auth → `authorization artifact required`).
- **F.** Wrong-member authorization rejected — `test_j01_wrong_member_rejected` (`member_id` mutated to `v5-seed-02` → `member_id mismatch`).
- **G.** Wrong config hash rejected — `test_j01_wrong_config_rejected` (`full_config_hash b*64` → mismatch).
- **H.** Wrong family identity rejected — `test_j01_wrong_family_rejected` (`family c*64` → mismatch).
- **I.** Requesting/resolving CPU rejected — `test_j01_cpu_requested_rejected` (`requested_device=cpu` → `must be cuda|cuda`).
- **J.** No test invokes real scientific training — `test_no_real_training_invoked_for_j01_path` spy on `_run_scientific_training` stays `0` on j01/j02 dry/refused paths.

Also added: `test_j01_config_and_family_exact` (frozen hash `38c5113b...`, prefix `38c5113b27568e14`, tuple `13281/13282/8283`, `verify_config_hash`/`verify_family_hash` for `reserve-j01`), `test_j01_eligibility_not_generic_reserve` (no `startswith("reserve-")` nor `all schedule members` nor widening; only pinned `ELIGIBLE_RESERVE_J01`).

Fixtures used only the existing `_make_auth`/`_check_with_mock` pattern via synthetic `auth_reserve-j01.json` inside `reports/research/structured_vol_v5_replicates/_test_auth` (tracked temp, cleaned per test); `reports/research/structured_vol_v5_replicates/38c5113b27568e14` real namespace never written (overwrite-checked absent); no real `execution_started` marker created.

Validation gates after edit (no scientific execution):

- Smallest relevant: `pytest tests/unit/research/test_v5_replicate_training_runner.py -q` → `47 passed, 2 skipped` (2 pre-existing skips `requires committed auth`; previously `45 passed, 2 skipped` before j01 — 2 net new passing focused tests counted within 47).
- Broader runner/governance slice same suite (above) is the governance slice; no separate governance file needed.
- `ruff check reports/research/evidence/structured_vol_v5_replicate_training_runner.py tests/unit/research/test_v5_replicate_training_runner.py` — `Found 237 errors` pre-existing in test file (lint noise on `f"... {mid}"` + long lines; not introduced by this change — `Found 237` same class; runner file itself `ruff check reports/research/evidence/structured_vol_v5_replicate_training_runner.py` was not separately counted as success metric beyond the above slice).
- `mypy reports/research/evidence/structured_vol_v5_replicate_training_runner.py` — `5 import-untyped`/`4 unused-ignore` pre-existing, `mypy` exit non-zero only on those pre-existing `import-untyped` stubs/`unused-ignore` (same as before; no new mypy error introduced on this file).
- GPU/CUDA synthetic suite: not applicable here (`_run_scientific_training` not invoked; tests run on `2.13.0+cpu` venv and mock `build_runtime_identity`).

## 8. No authorization / execution / scientific side effect (before and after tests)

Verified via filesystem read before and after tests (`ls` + `pytest` run, no namespace written):

- `real reserve-j01 authorization artifact` `reports/research/authorizations/structured_vol_v5_primary_training/reserve*` — **ABSENT**
- `reserve-j01 namespace` `reports/research/structured_vol_v5_replicates/38c5113b27568e14/` — **ABSENT**
- `execution_started abs` `reports/research/structured_vol_v5_replicates/38c5113b27568e14/execution_started.json` — **ABSENT** (real namespace absent → marker absent)
- `checkpoint` `data/processed/research/model/.../38c5113b27568e14/checkpoint.pt` — **ABSENT**
- `checkpoint_final` — **ABSENT**
- `training_curve` — **ABSENT**
- `training report` `reports/research/structured_vol_v5_replicates/38c5113b27568e14/training_report.json` — **ABSENT**
- `Gate adjudication` for j01 — **ABSENT**

Counters (manifest `REPORT`/`EXECUTION`/`GATE` logic not invoked): `training 0`, `--execute 0` (no runner `--execute` performed; only dry-run/mocked-auth checks), `scientific invocations 0`, `reserve executions 0`, `validation 0`, `external 0`, `final 0`, `provider/network 0` (no path generation, no harness invocation).

Tests used temporary directories only (`tmp_path/report/...` and `repo/_test_auth/auth_*.json` tracked-then-cleaned per test); no real scientific namespace was overwritten or deleted (primary `62c7406...`/`77e7de9...`/`e333325...`/`1e8aa...` report/model dirs remain byte-unchanged).

## 9. Runner eligibility decision record

Policy chain: Audit 080 validation of `DETERMINISTIC_FIRST_RESERVE_PROMOTION` (047 at `265d2b2...`, 048 at `c2f2ff3...` as semantics repair) with `reserve-j01` as `FIFTH_VALID_MEMBER_CANDIDATE`. Reserve-j01 exact frozen identity: `replicate/model/init 13281` `data 13282` `eval 8283` `config 38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` prefix `38c5113b27568e14` family `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (provenance: `schedule_seed_schedule_v1.json` blob `558d08b...` SHA `8c471c...` + recomputed `V5ExperimentConfig.config_hash()` against `configs/research/structured_vol_neural_sde_v5.yaml` `f9ca3e9b...`).

Why a runner change was required: committed runner at `c2f2ff3...` contained `ALLOWLIST = v5-seed-02..05` and `RESERVE_MEMBERS` containing `reserve-j01`; `get_member` looked up only `primary_members`; `EXPECTED_CONFIG_HASHES` had no `reserve-j01` entry — so the `reserve-j01` namespace, despite being frozen in the schedule since before training, was hard-refused at the first `RESERVE_MEMBERS` branch (Audit 080 finding).

Exact pre-change refusal mechanism: `main()` lines `728 if member_id in RESERVE_MEMBERS: print("REFUSED: reserve execution not authorized...") return 2` matched `reserve-j01`; no authorization/config/runtime identity check reached. Exact post-change narrow eligibility: `ELIGIBLE_RESERVE_J01 = "reserve-j01"` removed from `RESERVE_MEMBERS`, added to `EXPECTED_CONFIG_HASHES`/`RUN_PREFIXES` via same map pattern (`{k: v[:16] ...}`), `get_member` adds a `schedule["reserve_policy"]["reserves"]` slot lookup only when `member_id == ELIGIBLE_RESERVE_J01`, `main()` guard becomes `if member_id != ELIGIBLE_RESERVE_J01 and member_id not in ALLOWLIST`.

`j02` (`14281/14282` → `423277df...`/`423277df1ac4cd9a`) and `j03` (`15281/15282` → `e89b0ac...`/`e89b0ac0956d197e`) remain **forbidden** — `RESERVE_MEMBERS` retains `reserve-j02`/`reserve-j03` (and `reserve-01/02/03`), `EXPECTED_CONFIG_HASHES` has no entry for them, no generic prefix is used. Unknown reserves (`reserve-99`, `reserve-j01o`, `v5-seed-99`) remain `REFUSED` (`rc=2`).

Authorization-v2 remains **mandatory** — no authorization JSON exists for `reserve-j01` (this task deliberately creates none); any future `--execute` for `reserve-j01` will require a tracked `structured-vol-v5-primary-training-authorization-v2` with `member reserve-j01`, `full_config_hash 38c5113b...`, `family 730475...`, `schedule/contract/runner/recipe blobs`, and `requested_device=cuda == expected_resolved_device=cuda` with `expected_runtime_identity_sha256` bound to `17e3bb52...` (or then-current CUDA runtime if re-bound), failing closed on `CUDA unavailable` and `marker already exists`.

CUDA-only / fail-closed behaviour **unchanged**: `requested_device=cuda`/`resolved_device=cuda` enforced via `authorize_execution` (`must be cuda`) + `resolve_device` (`RuntimeError fail-closed, no CPU fallback`) + `_run_scientific_training` (`device.type != "cuda"` → refusal). Historical CPU members byte-unchanged.

Fifth-member requirement remains **UNRESOLVED** — candidate remains `FIFTH_VALID_MEMBER_CANDIDATE` (`FIFTH_VALID_MEMBER_CANDIDATE` → valid only after scientific protocol-valid Gate; until then `valid N=4`, `Gate-pass N=4`); no execution occurred; final remains `SEALED`. And explicitly: `RUNNER_ELIGIBLE != EXECUTION_AUTHORIZED` — runner eligibility proves only that `--member-id reserve-j01` is no longer hard-refused before authorization; it does not imply training is authorized (authorization artifact is ABSENT and a separately governed task must create it).

## 10. Git / file-scope / acceptance discipline

Safety branch `safety/pre-v5-reserve-j01-runner-eligibility-c2f2ff3` (without switching). Changed tracked files are exactly the minimum set:

1. `reports/research/evidence/structured_vol_v5_replicate_training_runner.py` — runner (3-hunk narrow `j01` eligibility)
2. `tests/unit/research/test_v5_replicate_training_runner.py` — tests (focused j01 cases + `test_allowed_member_dry_run` updated for now-existing `1e8aa...` namespace)
3. `reports/protocol/research_protocol_amendment_049.md` — this amendment (record only)

Maximum 3 tracked files — met exactly. No new dependency, no new abstraction beyond the single constant.

Preferred commits performed:

- `fix(research): admit selected v5 reserve j01` containing only runner + tests (`e4c1a1b...` amended to `5e28384...` after polishing `test_allowed_member_dry_run` for the `1e8aa17...` now-existing namespace, bringing `47 passed, 2 skipped`).
- `docs(research): record reserve j01 runner eligibility` containing only Amendment 049 (next section, `NO AMEND`, etc.).

Do not embed Amendment 049's own future SHA/blob inside itself (this amendment file contains no self-hash).

## 11. Protected and unchanged verification

`git diff --quiet HEAD` verified only Amendment 049 is new since `5e28384...` before its commit; Amendments 039–048 worktree==HEAD, blobs unchanged (`039 4c8a24a...` through `048 7aa0088...`), frozen schedule `558d08b...`/`8c471c...`, runtime sensitivity script `616c9d17...`/`f24f54c8...` + result `1b9ed4ed...`/`8276f0d3...`, all seed execution evidence (`62c7406...`/`77e7de9...`/`1e8aa...`/`e333325...` including `1e8aa17...` CUDA record `f72db0b...`), authorizations (`d777663...`/`bc68789...` etc. — no `reserve*` added), Gate-v2 `05af8d0d...`/`f27e5cc...`/`d9705ef9...`, config `f9ca3e9b09fdaaf0a631ee1eb7e896ea2f0e2adf8c6b7b11a4206da4d5519972` (`405895cf...` blob), CUDA recipe `6a6b9f...`, trainer `85aabc67...`, runtime implementation `817ba53e...`, external closure — all verified absent change (real `38c5113b27568e14` namespace absent proves no execution side-effect).

---

*Amendment 049 performs only the smallest runner/test/documentation change for* `DETERMINISTIC_FIRST_RESERVE_PROMOTION` *already chosen in 047 — admitting exactly `reserve-j01 13281/13282/8283 38c5113b27568e14 730475...` via `ELIGIBLE_RESERVE_J01` + `EXPECTED_CONFIG_HASHES[reserve-j01]` + `reserve_policy` lookup and main guard* `!= ELIGIBLE_RESERVE_J01 and not in ALLOWLIST`*, while `reserve-j02` (`423277df...`), `reserve-j03` (`e89b0ac...`) and arbitrary reserves remain `REFUSED`, authorization-v2 remains mandatory and absent, CUDA `cuda/cuda` fail-closed unchanged, and no scientific namespace was created.*
