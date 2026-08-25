# Amendment 106 — V5 Synthetic Split Stratification Repair Record

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-SYNTHETIC-SPLIT-STRATIFICATION-REPAIR-205`
Risk: `R4`
Branch: `main`
Starting HEAD: `0a853dd149f78653e724ba88417127a3bd1f8aac`
Safety branch: `safety/pre-v5-hedging-split-repair-0a853dd` at `0a853dd149f78653e724ba88417127a3bd1f8aac`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-BINDING-REPAIR-204` — `VALID_EXCEPT_SPLIT_STRATIFICATION`
Repair commit: `f63e3f8eb7d93fb25e9e575c1e617f7959438f9e`
Amendment-105 commit: `0a853dd149f78653e724ba88417127a3bd1f8aac`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — VALIDATED
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f...` — REPAIR_REQUIRED_PRESERVED
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9...` — SUPERSEDED_FOR_INDEXING_PRECISION
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED (80% train 40k, 20% selection 10k, random split seeded by synthetic RNG, stratified to preserve maturity/call-put balance if feasible, Section 6.2)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54...`
- Amendment 102: `research_protocol_amendment_102.md` at `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` / `aed93e484933dd54b84aff5890a98eff9ea010f7`
- Amendment 103: `research_protocol_amendment_103.md` at `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` / `a6fc42444413140226e6cd35ef44372f9accff1e`
- Amendment 104: `research_protocol_amendment_104.md` at `001202de1f702a2ef36a6ab8c172cf2dcc49d2942f276f02f51aca34e92b957e` / `c48584b8a2aad2566144b68aadcd4b47f8356282`
- Amendment 105: `research_protocol_amendment_105.md` at `92c9f06cac4255a0865ade860adf2f683825372b5cd1e6e3359c3c6c48b98a0b` / `563a9d86348d6704cfb9144eaf78556f58e1b72c` — VALID_EXCEPT_SPLIT_STRATIFICATION (pre-repair)
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-204 provenance

Task-204 `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-BINDING-REPAIR-204` repaired binding defects (checkpoint identity, authorization artifact, implementation manifest, production/test separation) but left split stratification as `VALID_EXCEPT_SPLIT_STRATIFICATION`:

- Repair commit: `e4137453c9b8351db1721e0e6a257f05964f192d` (`fix(research): harden v5 hedging execution bindings` — 4 files, 611 insertions, runner authorization and generation production hardening)
- Amendment-105 commit: `0a853dd149f78653e724ba88417127a3bd1f8aac` (`docs(research): record v5 hedging binding repair` — adds `research_protocol_amendment_105.md` alone, 166 insertions, `92c9f06cac...`/`563a9d86...`)
- Contract v3 `79611b6b...`/`eef7ad...` VALIDATED, but Task-204 generation used global `np_gen.permutation(N)` split (simple 80/20 random, not stratified), not the frozen stratified `maturity × option_type` requirement.

Task-204 adjudicated state: `VALID_EXCEPT_SPLIT_STRATIFICATION`, `DEEP-HEDGING IMPLEMENTATION: REPAIR_REQUIRED_FOR_FROZEN_SPLIT_CONTRACT` (see Task-204 Amendment 105 Section 10)

This Task-205 repairs only the one-issue split stratification; all other Task-204 bindings are preserved byte-identically unless split helper is in same file and requires minimal local edit.

## 3. Frozen stratification requirement

Read contract v3 Section 6.2 exact source language:

> `Train/selection split: 80% train (40,000 episodes) and 20% selection (10,000 episodes) per generator member, random split seeded by synthetic generation RNG (see below), stratified to preserve maturity/call-put balance if feasible but not required for determinism.`

- Stratification: `stratified to preserve maturity/call-put balance if feasible`
- Dimensions: `maturity` (M integer 5..30, 26 values) and `option_type` (call/put, canonical numeric encoding `+1` call / `-1` put from dataset, stored as `option_type` column)
- Feasible: `YES` — for real 50,000-episode dataset, maximum possible strata `26 × 2 = 52` (maturities × option types), each stratum expected ~961-962 episodes (50000/52), all 52 strata feasible without empty-stratum error; no moneyness bins (moneyness remains continuously sampled `uniform [0.90,1.10]` exactly as frozen, no new bins)
- Moneyness stratification: `Do not introduce moneyness bins` — moneyness remains continuous as already frozen

If contract text did NOT in fact require feasible maturity/call-put stratification, Task-205 would have STOPped and reported `BLOCKED` rather than inventing a new split. It does require it, so repair proceeds.

## 4. Stratum definition and order

Define one stratum per `(maturity, option_type)`:

- Stratum key: `maturity` integer `5..30`, `option_type` existing canonical numeric encoding `+1`/`-1` from dataset (`option_type` column, `+1` call, `-1` put)
- Use stored canonical episode values after stochastic metadata generation (after `ms`, `moneynesses`, `call_put` draws, before split)
- Freeze processing order: `maturity` ascending (`5` to `30`), then `option_type` ascending by its existing numeric encoding (`-1` before `+1` because `-1 < +1`). Do not consume any RNG merely to determine stratum order. Example: `(5,-1)` then `(5,1)` then `(6,-1)` then `(6,1)` etc.
- Ignore empty strata (if a particular maturity/option_type combination has zero episodes in the 50k sample, skip it; for 50k with 52 strata, all 52 are expected nonempty, but for tiny fixtures some may be empty)
- Episode IDs remain `0..N-1` (deterministic, from generation order). Do not reorder persisted rows; only assign `split` labels (`train`/`selection`) per episode ID, then keep original `episode_id` ascending order in parquet.

## 5. Proportional 80/20 stratified quotas — largest remainder

For total `N` (50,000 real, or tiny N for tests):

- `target_train = floor(0.80 * N)` (for N=50000, `40000`), `target_selection = N - target_train` (10000)
- For each nonempty stratum `s` with count `n_s`: `ideal_train_s = 0.80 * n_s`, `base_train_s = floor(ideal_train_s)`, `remainder_s = ideal_train_s - base_train_s` (fractional part 0 <= `remainder_s` <1)
- Compute `remaining = target_train - sum(base_train_s)`, require `remaining >=0` (should be 0 <= remaining < number of nonempty strata)
- Allocate one additional training slot to exactly `remaining` strata ordered by: 1. `remainder_s` descending, 2. `maturity` ascending, 3. `option_type` ascending. Thus `train_quota_s = base_train_s` or `base_train_s + 1`.
- Require `sum(train_quota_s) == target_train` and `sum(n_s - train_quota_s) == target_selection`
- For real N=50,000 require exactly `40,000` train and `10,000` selection (verified via `int(0.80*50000)==40000`)
- This is deterministic largest-remainder apportionment, no random quota rounding.

## 6. Same frozen NumPy RNG stream within strata

Preserve Task-204 metadata draw order (already frozen, using `np_gen = np.random.Generator(PCG64(synthetic_seed))`):

1. `maturity` draws for all N episodes (`np_gen.integers(5,31, size=N)`)
2. `moneyness` draws for all N episodes (`np_gen.uniform(0.90,1.10, size=N)`)
3. `call/put` draws for all N episodes (`np_gen.integers(0,2, size=N)` -> `option_types`)

Then, using the SAME existing `np_gen` object (already advanced after those three draws), continue the already-advanced RNG stream:

- For each nonempty stratum in canonical order from Section 4: `indices_s = episode IDs in that stratum, ascending before permutation` (sorted `strata[key]`), `permuted_s = np_gen.permutation(indices_s)` (single call per stratum, using same `np_gen`), assign `first train_quota_s: train`, remaining: `selection`.

Do NOT: reinitialize `np_gen`, use `synthetic_seed+999`, derive a child seed, create a second split RNG (`split_gen = Generator(PCG64(...))`), run one global permutation (`np_gen.permutation(N)`).

Persist split labels in original `episode_id` row order (`df.sort_values("episode_id")` before and after, `df["split"] = df["episode_id"].map(split_map)`).

## 7. Manifest binding

Update synthetic manifest/split metadata minimally so exact algorithm is auditable (in `generation.py` manifest dict):

- `split_method: "maturity_option_type_stratified_largest_remainder_v1"`
- `train_fraction: 0.80`
- `target_train_count: 40000` (or `int(0.80*N)` for N)
- `target_selection_count: 10000`
- `stratum_keys: ["maturity", "option_type"]`
- `stratum_order: "maturity ascending, option_type ascending"`
- `quota_method: "largest_remainder"`
- `RNG: "same member PCG64(synthetic_seed) stream after metadata draws"`
- Preserve `train_selection_split: "80/20"`, `train_count`, `selection_count`, `cost_levels`, `parquet_sha256`, `contract_v3` SHA/blob, `runtime_identity`, etc.
- Do not self-hash (manifest does not contain its own SHA)
- Preserve dataset SHA behavior (`parquet_sha256` computed after `df.to_parquet`, verified on load via `load_synthetic_dataset` if manifest provided)
- On load, continue validating dataset SHA and persisted `split` column; do NOT resplit during policy training (trainer uses `load_synthetic_dataset` with `split` filter, no recomputation)

## 8. Tests

Preserve all existing 49 tests (21 `test_deep_hedging.py` + 15 `test_deep_hedging_execution.py` + 13 `test_deep_hedging_binding.py`):

- 49 passed before repair (`python -m pytest ... -q` -> 49 passed)
- After repair, update one existing test `test_split_uses_same_rng_not_plus_999` to verify stratified same-stream (instead of global) and keep other 48 unchanged (they only check counts/determinism, not exact global permutation, so they still pass with stratified)

Add only split-specific tests via `tests/unit/research/test_deep_hedging_split_stratification.py` (13 new, total 62, tiny fixtures <=16, temp dirs, no CUDA):

- `test_real_shaped_metadata_can_support_all_52_strata` — 52 strata feasible without error
- `test_same_seed_same_metadata_gives_identical_split` (same seed + same metadata -> identical `split`)
- `test_different_seed_can_change_within_stratum_membership` (different seed can change)
- `test_exact_train_selection_total_for_representative_n` (N=16->12/4, 10->8/2, 100->80/20, 52->41/11 via floor)
- `test_n_50000_quota_arithmetic_gives_40000_10000_without_paths` (without generating 50k paths, `int(0.80*50000)==40000` and tiny imbalanced fixture quota logic)
- `test_each_stratum_train_quota_is_floor_or_ceil` (per stratum `train_quota` equals `floor(0.8*n_s)` or `ceil`)
- `test_largest_remainder_tie_break_is_deterministic` (same remainder tie broken by maturity then option_type, canonical order)
- `test_canonical_stratum_order_is_maturity_then_option_type` (manifest `stratum_order` and `stratum_keys`)
- `test_same_np_gen_stream_is_used_after_metadata_draws` (no `+999`, no second Generator, `np_gen.permutation(indices_s)` per stratum, no global `np_gen.permutation(num_episodes)`)
- `test_no_plus_999_no_second_generator_global_permutation` (grep `generation.py` for `+ 999`, `PCG64(synthetic_seed` count ==1, `np_gen.permutation(num_episodes)` not present, `np_gen.permutation(indices_s)` present)
- `test_persisted_row_order_remains_episode_id_ascending` (df sorted by `episode_id`)
- `test_training_loader_uses_persisted_split_and_does_not_resplit` (trainer uses `load_synthetic_dataset` with persisted `split`, not recomputed; checks manifest `train_count` and report `synthetic_manifest_sha256`)
- `test_imbalanced_fixture_preserves_stratum_proportions` (deliberately imbalanced maturity/call-put, e.g., N=20 with known strata, both train and selection approximately preserve proportions via quota)

No CUDA, no real NSDE checkpoint, no 50k path generation.

## 9. Verification at repair

- Branch `main`, HEAD `f63e3f8eb7d93fb25e9e575c1e617f7959438f9e` (repair commit `fix(research): stratify v5 synthetic hedging split` — 3 files, 508 insertions+28 deletions), parent `0a853dd...`, origin/main at `0a853dd...` (1 ahead before amendment, 2 after), no push
- Safety branch `safety/pre-v5-hedging-split-repair-0a853dd` at `0a853dd...` created without switching, verified `git rev-parse safety/...` == `0a853dd...`
- Contract v3 `79611b6b...`/`eef7ad...` — `hashlib.sha256(LF-canonical)` and `git hash-object`/`ls-tree`/`cat-file -t blob` verified, filtered worktree == HEAD, `git diff HEAD -- contract_v3` -> 0, unchanged
- Amendment 105 `92c9f06cac...`/`563a9d86...` — verified, filtered worktree == HEAD, unchanged
- Amendment 106 `reports/protocol/research_protocol_amendment_106.md` — no self-hash, canonical/raw/blob to be computed at next audit (commit separately)
- Files changed in repair: `src/neuralmarket/research/deep_hedging/generation.py` (split RNG + stratified quotas, 87 lines), `tests/unit/research/test_deep_hedging_binding.py` (updated `test_split_uses_same_rng_not_plus_999` to stratified), `tests/unit/research/test_deep_hedging_split_stratification.py` (new 13 tests) — 3 files, minimal
- Tests: 49 prior preserved, plus 13 new = 62 passed, 0 failed, no scientific execution
- `synthetic_seed + 999`: 0 executable occurrences (`grep -rn "999" src/.../generation.py` shows only comment `No +999, no child seed, no second split RNG`, no code `+ 999`)
- Second split `PCG64`: 0 (`grep -rn "PCG64" src/.../generation.py` shows only one `PCG64(synthetic_seed` in `_make_rngs`, not second for split; `text.count("PCG64(synthetic_seed") ==1`)
- Global split `np_gen.permutation(N)`: 0 for production split logic (`grep -n "permutation" src/.../generation.py` shows only `np_gen.permutation(indices_s)` per stratum, not `np_gen.permutation(num_episodes)` global)
- Real generation: 0 (`ls data/processed/research/hedging_synthetic` -> no such file)
- Scientific NSDE execution: 0 (no `simulate_structured` with real checkpoint)
- Scientific training: 0 (no `hedging_policies` real checkpoints)
- Network: 0 (no `git fetch`/`pull`/`push`/`ls-remote`/`curl` during Task 205; only `git rev-parse`/`log`/`status`/`branch`/`add`/`commit`/`hash-object`/`ls-tree`/`diff`/`merge-base`/`ls-files` for artifact/commit checks)
- Push: 0 (no `git push`; HEAD `f63e3f8` is locally 1 ahead of `origin/main` at `0a853dd`, not pushed)

## 10. What this task does not do

- Does not execute real 50,000-episode generation per member (tests use `increment_provider` fake with 8/10/16/20 episodes, `num_episodes` <=16, `verify_contract_runtime=False`, no NSDE checkpoint instantiation on cuda:0 beyond mocked boundary)
- Does not run 45-policy scientific training on real campaign data (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu, no `simulate_structured` with real checkpoint)
- Does not access final-test rows (split manifest metadata only, SEALED)
- Does not external, network, or push
- Does not create real execution authorization (schema hardened in Task-204, preserved, but no file exists; Task 205 `NOT GRANTED`)

