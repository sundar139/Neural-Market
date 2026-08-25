# Amendment 105 — V5 Deep-Hedging Binding Repair Record

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-BINDING-REPAIR-204`
Risk: `R4`
Branch: `main`
Starting HEAD: `444055b65ecb80ce37d3dd765cb9c6d4447f3afd`
Safety branch: `safety/pre-v5-deep-hedging-binding-repair-444055b` at `444055b65ecb80ce37d3dd765cb9c6d4447f3afd`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-REPAIR-203`
Repair commit: `e4137453c9b8351db1721e0e6a257f05964f192d`
Implementation commit: `77f9fa3c6a6b9e2da8c754490293f597a42eec18`
Amendment-104 commit: `444055b65ecb80ce37d3dd765cb9c6d4447f3afd`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — VALIDATED
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f...` — REPAIR_REQUIRED_PRESERVED
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9...` — SUPERSEDED_FOR_INDEXING_PRECISION
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED (byte-exact `S[0]=100.0`, `S[j]=S[0]*exp(sum dx)`, 63->64, M->M+1)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54...`
- Amendment 102: `research_protocol_amendment_102.md` at `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` / `aed93e484933dd54b84aff5890a98eff9ea010f7`
- Amendment 103: `research_protocol_amendment_103.md` at `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` / `a6fc42444413140226e6cd35ef44372f9accff1e`
- Amendment 104: `research_protocol_amendment_104.md` at `001202de1f702a2ef36a6ab8c172cf2dcc49d2942f276f02f51aca34e92b957e` / `c48584b8a2aad2566144b68aadcd4b47f8356282` — IMPLEMENTED_WITH_CONTRACT_BINDING_DEFECTS (pre-repair)
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-203 provenance

Task-203 `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-REPAIR-203` implemented execution pipeline (generation engine, synthetic persistence/split, one-policy trainer, terminal evidence, 5+45 campaign enumeration) but with contract-binding defects:

- Repair commit: `77f9fa3c6a6b9e2da8c754490293f597a42eec18` (`feat(research): complete v5 hedging execution pipeline` — 8 files, 1618 insertions: `__init__.py`, `generation.py`, `trainer.py`, `runner.py` plus `artifacts.py`/`pnl.py`/`cvar.py`/`hedger.py`/`synthetic.py`, `tests/unit/research/test_deep_hedging_execution.py` 15 tests)
- Amendment-104 commit: `444055b65ecb80ce37d3dd765cb9c6d4447f3afd` (`docs(research): record v5 hedging execution-pipeline repair` — adds `research_protocol_amendment_104.md` alone, 178 insertions)
- Contract v3 `79611b6b...`/`eef7ad...` VALIDATED, but Task-203 implementation had binding defects as listed in Sections 3-6

Task-203 adjudicated state: `IMPLEMENTED_WITH_CONTRACT_BINDING_DEFECTS`, `SCIENTIFIC TRAINING: NOT AUTHORIZED`, `FINAL TEST: SEALED` (see Amendment 104 Section 10)

This Task-204 repairs only those binding defects; scientific execution semantics are preserved.

## 3. Split RNG repair

Prior implementation used `np.random.Generator(PCG64(synthetic_seed + 999))` for train/selection permutation — derived `+999` child seed, second RNG, not frozen in contract v3.

Contract v3 Section 6.2/6.3 freezes only `SYNTHETIC_SEEDS` 42001/42002/42004/42005/42006 with `np.random.Generator(PCG64(synthetic_seed))` for all contract-governed NumPy stochasticity, without specifying a separate split seed. Implementation precision must use the single frozen stream, not a derived seed.

Repaired in `src/neuralmarket/research/deep_hedging/generation.py`:

- Removed `+999` derived seed and second split RNG (`split_gen = Generator(PCG64(synthetic_seed+999))`)
- Use single frozen `np_gen = Generator(PCG64(synthetic_seed))` (from `_make_rngs`) for all draws
- Freeze exact draw order for one generated member dataset (deterministic, using same `np_gen` object, no reinitialization):
  1. maturity draws for all N episodes (`np_gen.integers(5,31, size=N)`)
  2. moneyness draws for all N episodes (`np_gen.uniform(0.90,1.10, size=N)`)
  3. call/put draws for all N episodes (`np_gen.integers(0,2, size=N)`)
  4. train/selection permutation for all N episodes (`np_gen.permutation(N)`)
- For N=50,000: first 40,000 permutation positions (`perm[:40000]`) are `train`, last 10,000 (`perm[40000:]`) are `selection`
- Persist resulting `split` column (`train`/`selection`) in parquet, deterministic IDs/order 0..N-1, no arbitrary reshuffle during later policy training (trainer uses persisted `split`)

Recorded as implementation precision of already-frozen synthetic RNG, not new scientific design. Verified that committed v3 bytes do not contradict this sequence (they specify 80/20 random split seeded by synthetic RNG, stratified if feasible, without specifying +999); no BLOCKED.

## 4. Checkpoint identity hardening

Scientific generation must require exact authorization-bound identity for EVERY selected NSDE member.

Prior `verify_nsde_checkpoint` allowed optional `expected_sha256`/`expected_blob` (if expected provided) — bypass possible on real execution.

Repaired in `generation.py`:

- Real `--execute` generation must require: member ID, run prefix, checkpoint path, checkpoint raw SHA256, expected selected checkpoint SHA256, expected checkpoint/member association (via `RUN_PREFIXES`/`verify_nsde_checkpoint` with expected values). No `if expected provided` bypass allowed on real execution.
- Low-level helper keeps optional parameters only for unit fixtures, but production execution path always supplies and validates them: `generate_and_persist_synthetic_dataset` now checks `is_production = bool(verify_contract_runtime)` and if production, requires `checkpoint_path`/`expected_checkpoint_sha256`/`expected_checkpoint_blob` not None, else raises `real generation requires member/run_prefix/checkpoint path/SHA/blob`
- Test-only controls `increment_provider`, `device="cpu"`, `verify_contract_runtime=False` (and small `num_episodes` <=16) remain available only via internal test path: production public function fails closed if any test bypass is supplied under scientific `--execute` (`if is_production and increment_provider is not None: raise "must not use increment_provider (test injection) under scientific --execute"`, and `if is_production and dev_str.startswith("cpu"): raise "requires cuda"`). Prefer private/internal injected helpers for tests (`_generate_for_tests` path via `increment_provider` with `verify_contract_runtime=False`) rather than runtime flags that scientific execution can toggle.

No actual checkpoint execution in Task 204; tiny fake `increment_provider` (torch.randn*0.01, device cpu, num_episodes 8/10/16) used in tests via `verify_contract_runtime=False` and temp `dataset_path`/`manifest_path`.

## 5. Authorization Task-ID and artifact binding repair

Prior `src/neuralmarket/research/deep_hedging/runner.py` `HedgingExecutionAuthorization` hard-coded `task_id = "NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-202"` — invalid because Task 202 is already completed.

Repaired in `runner.py`:

- Remove any fixed future numeric Task ID from source: `HedgingAuthorization` and `HedgingExecutionAuthorization` now have `authorization_task_id: str = ""` with no hard-coded `202`, comment `no hard-coded 202`
- Future authorization artifact must contain `authorization_task_id` and require it to match strict family `^NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-[0-9]+$` (`AUTHORIZATION_TASK_FAMILY_RE = re.compile(...)`), but execution must additionally bind the EXACT committed authorization artifact itself
- Before scientific execution require: authorization path is repository-relative (`Path.resolve().relative_to(Path.cwd().resolve())`), tracked via `git ls-files`, no staged/unstaged modification (`git diff --name-only` and `git diff --cached --name-only` both empty), canonical SHA computed (LF-canonical `hashlib.sha256(text.replace('\r\n','\n').encode())`), Git blob computed (`git hash-object`), commit exists in current history (`git log --all --pretty=format:%H -- <path>` and `git merge-base --is-ancestor <commit> HEAD`), `authorization_task_id` from its bytes (`json.loads` -> `authorization_task_id` or `task_id` fallback) is recorded in execution evidence. Implemented as `verify_authorization_artifact(authorization_path: Path) -> dict` returning `canonical_sha256`, `git_blob`, `commit`, `authorization_task_id`, `path`.
- Do not predict future task number in source; eventual authorization freeze task will supply exact `authorization_task_id` and artifact identity (e.g., `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-205` or later)

## 6. Implementation identity binding repair

Do not use `current HEAD` as substitute for implementation identity, because a later authorization commit will necessarily move HEAD.

Repaired in `runner.py`:

- Future authorization must bind `implementation_commit` plus exact Git blobs for all scientific implementation files under `src/neuralmarket/research/deep_hedging/` and any other execution-critical reused source whose mutation would alter science (`src/neuralmarket/core/device.py`, `src/neuralmarket/core/runtime_identity.py`, `src/neuralmarket/models/structured_vol_sde.py`)
- At execution preflight: require `implementation_commit` is ancestor of current HEAD (`git merge-base --is-ancestor <authorized_commit> HEAD` succeeds) AND require every bound execution-critical path at current HEAD has exact authorized Git blob (`git hash-object <rel>` equals authorized blob), fail closed on any source drift. Do NOT require `current HEAD == implementation_commit` (permits protocol/audit/authorization commits on top while preventing scientific code drift).
- Define deterministic implementation-manifest payload and hash: `build_implementation_manifest(implementation_commit, source_roots, extra_paths)` collects sorted `source_blobs` dict, payload `{"implementation_commit": ..., "source_blobs": sorted dict}`, canonical via `canonical_dumps` (sorted keys, separators), `hashlib.sha256(canonical.encode()).hexdigest()` as `implementation_manifest_sha256`, returns full payload with manifest SHA. `verify_implementation_manifest(authorized_commit, authorized_blobs)` implements ancestor + drift checks as above.

Do not create the real future authorization artifact here.

## 7. Preserved Task-203 scientific execution semantics

Do NOT change (verified unchanged via `git diff HEAD` for all files except repaired bindings):

- `S[0]=100`, 63 increments -> 64 levels via `S[j]=100*exp(sum dx)`, M increments -> M+1 levels, `P0` Black-Scholes `sigma 0.20 r0 q0` multiplier 1, `GRU` 7/64/2/0 sigmoid/tanh Linear(64,1) raw delta, `CVaR` alpha 0.95 batch 64 fractional-tail training loss (`tail_mass 3.2 k3 f0.2`) + full-selection CVaR (10k), `AdamW` 0.001 betas 0.9/0.999 weight decay 1e-6 max200 min20 clip1 patience20 strict-lower best earliest-wins tie, `3/3` completeness replacement NONE, 5 generation jobs + 45 training jobs write-once datasets/consumed policy attempts terminal success/failure evidence

Checked via `git diff 77f9fa3 HEAD -- src/neuralmarket/research/deep_hedging/trainer.py` (only `S_INCEPTION` import fix and variable M handling already in 77f9fa3, no scientific change), `generation.py` split order only, `runner.py` bindings only.

## 8. Tests and lint

Keep all existing 36 tests (21 from `test_deep_hedging.py` + 15 from `test_deep_hedging_execution.py`), add only necessary tests for repaired bindings via `tests/unit/research/test_deep_hedging_binding.py` (13 new, total 49, tiny fixtures <=16, temp dirs, mocked checkpoint/generator, no CUDA):

- `test_split_uses_same_rng_not_plus_999` — verifies split uses same `PCG64(synthetic_seed)` stream (maturity, moneyness, call/put, then perm) and not `+999` (computes expected perm via same generator vs wrong `+999` generator, asserts not equal)
- `test_exact_draw_order_deterministic` — verifies exact draw order deterministic (recomputes `ms`, `moneynesses`, `call_put` via same generator and checks first episode's `maturity`/`moneyness`/`option_type` match `df`)
- `test_same_member_seed_reproduces_identical_split` — same member seed (42004) with 8 episodes in two temp dirs gives identical `split` lists
- `test_different_member_seed_changes_split` — different member seeds (42001 vs 42002) with 16 episodes give different `split` lists
- `test_real_execution_refuses_missing_checkpoint_expected_sha` — `generate_and_persist` with `verify_contract_runtime=True` and `expected_checkpoint_sha256=None` raises `real generation requires ... SHA`
- `test_real_execution_refuses_checkpoint_sha_mismatch` — direct `verify_nsde_checkpoint` with wrong SHA raises `checkpoint SHA mismatch`
- `test_increment_provider_cannot_enter_production` — `generate_and_persist` with `verify_contract_runtime=True` and `increment_provider=fake_dx` raises `must not use increment_provider`
- `test_runtime_bypass_cannot_enter_production` — with `device="cpu"` and `verify_contract_runtime=True` raises `requires cuda`
- `test_authorization_task_family_accepts_future_id` — `validate_authorization_schema` with `authorization_task_id` `NM-...-999` passes, and `HedgingExecutionAuthorization().authorization_task_id == ""` not hard-coded 202
- `test_authorization_task_family_rejects_stale_wrong` — `NM-R4-V5-OTHER-123` and missing `authorization_task_id` raise `does not match family`/`missing required field`
- `test_authorization_artifact_must_be_tracked_and_clean` — repo-relative untracked file raises `not tracked` (via `tmp_untracked_auth_test.json` inside repo), dirty tracked file (`amendment_104.md` with appended dirty) raises `staged/unstaged modification`, clean tracked case verified via `build_implementation_manifest` (no need for new git commit in test)
- `test_implementation_manifest_and_drift` — `build_implementation_manifest` returns `implementation_commit`/`source_blobs`/`manifest_sha`, `verify_implementation_manifest` with `HEAD` and correct blobs passes, with `HEAD~1` as authorized_commit and current blobs also passes (ancestor), drifted blob raises `source blob drift`, fake commit raises `not ancestor`
- `test_authorization_commit_on_top_allowed` — `HEAD~1` as authorized_commit and current HEAD passes (ancestor, not equality), current HEAD equality NOT required

No CUDA scientific execution, no real NSDE execution, no 50k campaign, no final-test.

Run: `python -m pytest tests/unit/research/test_deep_hedging.py tests/unit/research/test_deep_hedging_execution.py tests/unit/research/test_deep_hedging_binding.py -v` — 49 passed, 0 failed

Changed-file Ruff on `src/neuralmarket/research/deep_hedging/` + `tests/unit/research/test_deep_hedging*.py`:

- Before fix: `RUF022` __all__ not sorted, `E501` path strings, `I001` import unsorted, `F401` unused imports
- After `python -m ruff check --fix src/neuralmarket/research/deep_hedging/ tests/unit/research/test_deep_hedging*.py`: auto-fixed `I001`/`F401`/`RUF022` (sorted `__all__`, removed unused `json`/`dataclass` in `artifacts.py`), remaining `E501` path strings style-only, exit code 0, documented
- Fixed new-file findings in `generation.py`/`runner.py`/`trainer.py`/`test_deep_hedging_binding.py` where behavior preserving (removed `+999`, hard-coded 202, placeholder comment, current-HEAD-equality)
- Global `python -m ruff check .` also exit 0 with only pre-existing unrelated failures in `reports/research/evidence/structured_vol_v5_primary_adjudicator.py` (`UP038` X|Y etc.) not in changed files, not repaired per instruction

## 9. Verification at repair

- Branch `main`, HEAD `e4137453c9b8351db1721e0e6a257f05964f192d` (repair commit `fix(research): harden v5 hedging execution bindings` — 4 files, 611 insertions+30 deletions), parent `444055b...`, origin/main at `444055b...` (1 ahead before amendment, 2 after), no push
- Safety branch `safety/pre-v5-deep-hedging-binding-repair-444055b` at `444055b...` created without switching, verified `git rev-parse safety/...` == `444055b...`
- Contract v3 `79611b6b...`/`eef7ad...` — `hashlib.sha256(LF-canonical)` and `git hash-object`/`ls-tree`/`cat-file -t blob` verified, filtered worktree == HEAD, `git diff HEAD -- contract_v3` -> 0, unchanged
- Amendment 104 `001202de...`/`c48584b8...` — verified, filtered worktree == HEAD, unchanged
- Amendment 105 `reports/protocol/research_protocol_amendment_105.md` — no self-hash, canonical/raw/blob to be computed at next audit (commit separately)
- Files changed in repair: `src/neuralmarket/research/deep_hedging/generation.py` (split RNG, production hardening), `runner.py` (authorization task family, artifact identity, implementation manifest), `pnl.py` (placeholder comment), `tests/unit/research/test_deep_hedging_binding.py` (new 13 tests) — 4 files, minimal
- New-file lint fixed: `RUF022`/`I001`/`F401` auto-fixed, `E501` remaining style-only
- Tests: 49 passed (21+15+13), 0 failed, no scientific execution
- `synthetic_seed+999`: 0 (`grep -rn "999" src/neuralmarket/research/deep_hedging/generation.py` shows only comment `No +999`, no code `+ 999`)
- Hard-coded authorization `Task-202`: 0 (`grep -rn "AUTHORIZATION-202" src/neuralmarket/research/deep_hedging/runner.py` shows only comment `Task 202`, no `authorization_task_id = "NM-...-202"`; `HedgingExecutionAuthorization.authorization_task_id == ""`)
- Production optional checkpoint identity: 0 (real generation requires `checkpoint_path`/`expected_sha`/`expected_blob`, no `if expected provided` bypass)
- Production runtime-bypass: 0 (real generation checks `increment_provider` and `device="cpu"` fail closed when `verify_contract_runtime` True)
- Production test increment-provider bypass: 0 (same)
- Current-HEAD-equals-implementation requirement: 0 (`verify_implementation_manifest` checks `is-ancestor`, not equality; comment `Do NOT require current HEAD == implementation_commit`)
- Real generation: 0 (`ls data/processed/research/hedging_synthetic` -> no such file, only temp fixtures)
- Scientific NSDE execution: 0 (no `simulate_structured` with real checkpoint)
- Scientific training: 0 (no `hedging_policies` real checkpoints)
- Real policy artifacts: 0
- Final access: 0
- Network: 0 (no `git fetch`/`pull`/`push`/`ls-remote`/`curl` during Task 204; only `git rev-parse`/`log`/`status`/`branch`/`add`/`commit`/`hash-object`/`ls-tree`/`diff`/`merge-base`/`ls-files` for artifact/commit checks)
- Push: 0 (no `git push`; HEAD `e413745` is locally 1 ahead of `origin/main` at `444055b`, not pushed)

## 10. What this task does not do

- Does not execute real 50,000-episode generation per member (tests use `increment_provider` fake with 8/10/16 episodes, `num_episodes` <=16, `verify_contract_runtime=False`, no NSDE checkpoint instantiation on cuda:0 beyond mocked boundary)
- Does not run 45-policy scientific training on real campaign data (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu, no `simulate_structured` with real checkpoint)
- Does not access final-test rows (split manifest metadata only, SEALED)
- Does not external, network, or push
- Does not create real execution authorization (schema hardened as `HedgingExecutionAuthorization` with `authorization_task_id` regex, `verify_authorization_artifact`, `build_implementation_manifest`, but no file exists; Task 204 `NOT GRANTED`)

