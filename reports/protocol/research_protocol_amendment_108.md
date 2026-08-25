# Amendment 108 — V5 Authorization-Surface and Tensor-Materialization Repair Record

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-AUTHORIZATION-SURFACE-TENSOR-MATERIALIZATION-REPAIR-208`
Risk: `R4`
Branch: `main`
Starting HEAD: `983fd64020cb3f7c0ed7e8293787ee9912d40dc6`
Safety branch: `safety/pre-v5-auth-surface-repair-983fd64` at `983fd64020cb3f7c0ed7e8293787ee9912d40dc6`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-PRODUCTION-EXECUTION-PATH-AND-BATCHING-REPAIR-207`
Repair commit: `66f0fce3f93c74090523a92617d5d980845e3b9d`
Prior implementation commit: `239107d0d5fa32fb0208c008e6c10efabe817dc2`
Amendment-107 commit: `983fd64020cb3f7c0ed7e8293787ee9912d40dc6`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — VALIDATED
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f...` — REPAIR_REQUIRED_PRESERVED
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9...` — SUPERSEDED_FOR_INDEXING_PRECISION
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED (80% train 40k, 20% selection 10k, 63->64, S[0]=100, stratified split `maturity_option_type_stratified_largest_remainder_v1`, GRU 7/64/2/0, CVaR batch64/selection10k, AdamW, 3/3, etc.)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54...`
- Amendment 102: `research_protocol_amendment_102.md` at `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` / `aed93e484933dd54b84aff5890a98eff9ea010f7`
- Amendment 103: `research_protocol_amendment_103.md` at `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` / `a6fc42444413140226e6cd35ef44372f9accff1e`
- Amendment 104: `research_protocol_amendment_104.md` at `001202de1f702a2ef36a6ab8c172cf2dcc49d2942f276f02f51aca34e92b957e` / `c48584b8a2aad2566144b68aadcd4b47f8356282`
- Amendment 105: `research_protocol_amendment_105.md` at `92c9f06cac4255a0865ade860adf2f683825372b5cd1e6e3359c3c6c48b98a0b` / `563a9d86348d6704cfb9144eaf78556f58e1b72c`
- Amendment 106: `research_protocol_amendment_106.md` at `ef0a82a4eb3bb2835eeaf79ef05284bc04dddaf6b932a8a8e027d05214dab976` / `d2538b782db14a3be467f481a31a23f141c0a748` — split stratification `maturity_option_type_stratified_largest_remainder_v1`
- Amendment 107: `research_protocol_amendment_107.md` at `2da858aa0068f40b46f6ef26f356b0ab568598db7e55d0866b56a85025beb370` / `d5c5a7b5ba6646fa5202102252e7b3d52f1989ae` — production-path and batching repair (`57aa9067...` manifest for `239107d` with 12 paths, missing CLI/manifests)
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-207 provenance

Task-207 `NM-R4-V5-DEEP-HEDGING-PRODUCTION-EXECUTION-PATH-AND-BATCHING-REPAIR-207` at `239107d0d5fa32fb0208c008e6c10efabe817dc2` (`fix(research): complete v5 hedging production execution path` — 7 files, 936 insertions, `cli/deep_hedging.py`/`cli/main.py` dispatch, `hedger.py` `GRUHedger.step`, `generation.py` real NSDE `StructuredVolatilityNeuralSde` strict load, `trainer.py` batched `for t in range(M_max)` with `GRUHedger.step` and mask, `test_deep_hedging_production.py` 17 tests) and Amendment 107 at `983fd64020cb3f7c0ed7e8293787ee9912d40dc6` (`2da858aa...`/`d5c5a7b5...`) were audited at Task-206 and found `REPAIR_REQUIRED` for production blockers and `IMPLEMENTATION_PERFORMANCE_REPAIR_REQUIRED` for training, plus remaining production boundary defects for Task-208.

Prior implementation manifest reported for `239107d` was `57aa9067191ce83c9fa64f88de5811896055ae4c7c871741e78f09a2f3dc7a92` for 12 paths (9 under `deep_hedging` + 3 extra: `core/device.py`, `core/runtime_identity.py`, `models/structured_vol_sde.py`), omitting `cli/deep_hedging.py`, `cli/main.py`, `data/manifests.py`.

Task-207 adjudicated state: `SCIENTIFICALLY_CORRECT_WITH_REMAINING_PRODUCTION_BOUNDARY_DEFECTS`, `DEEP-HEDGING IMPLEMENTATION: REPAIR_REQUIRED` (see Task-206 audit).

This Task-208 repairs only authorization-surface and tensor-materialization defects; all validated science (S[0]=100, 63->64, M->M+1, P0 Black-Scholes, GRU, CVaR, optimizer, split, 3/3, etc.) is preserved.

## 3. Complete execution-critical source manifest (repaired)

Source-first trace all imports reachable from scientific production path: CLI → runner authorization/preflight → generation/trainer → GRU/P&L/CVaR/artifacts/synthetic → CUDA/runtime → NSDE → canonical serialization/hash helpers.

Deterministic function `src/neuralmarket/research/deep_hedging/runner.py:build_implementation_manifest` now returns COMPLETE execution-critical path set, sorted lexicographically:

At minimum exact Git blobs for:

- all `*.py` under `src/neuralmarket/research/deep_hedging/` (9 files: `__init__.py`, `artifacts.py`, `cvar.py`, `generation.py`, `hedger.py`, `pnl.py`, `runner.py`, `synthetic.py`, `trainer.py`)
- plus `src/neuralmarket/cli/deep_hedging.py`
- plus `src/neuralmarket/cli/main.py`
- plus `src/neuralmarket/core/device.py`
- plus `src/neuralmarket/core/runtime_identity.py`
- plus `src/neuralmarket/data/manifests.py`
- plus `src/neuralmarket/models/structured_vol_sde.py`
- plus any additional actually imported helper whose mutation could alter authorization, dispatch, scientific values, RNG, model construction, artifact identity, serialization (verified via `grep -rn "from neuralmarket\."` and `import` trace, includes `src/neuralmarket/data/manifests.py` for `canonical_dumps`)

Sorted paths lexicographically, manifest payload `{"implementation_commit": <repair commit>, "source_blobs": {sorted path: blob, ...}}` canonicalized via `neuralmarket.data.manifests.canonical_dumps` (sorted keys, separators `,`, `:`), `implementation_manifest_sha256 = SHA256(canonical payload bytes)`.

For repair commit `66f0fce3f93c74090523a92617d5d980845e3b9d` (new), collected 15 files:

- `src/neuralmarket/cli/deep_hedging.py` `0a601c02...`
- `src/neuralmarket/cli/main.py` `85f03cd4...`
- `src/neuralmarket/core/device.py` `5f7f7a1e...`
- `src/neuralmarket/core/runtime_identity.py` `817ba53e...`
- `src/neuralmarket/data/manifests.py` `a1b2...` (actual blob via `git hash-object`)
- `src/neuralmarket/models/structured_vol_sde.py` `e828a874...`
- `src/neuralmarket/research/deep_hedging/__init__.py` `bd994657...`
- `src/neuralmarket/research/deep_hedging/artifacts.py` `28e3254a...`
- `src/neuralmarket/research/deep_hedging/cvar.py` `c03166af...`
- `src/neuralmarket/research/deep_hedging/generation.py` `...`
- `src/neuralmarket/research/deep_hedging/hedger.py` `...`
- `src/neuralmarket/research/deep_hedging/pnl.py` `51efec2c...`
- `src/neuralmarket/research/deep_hedging/runner.py` `...`
- `src/neuralmarket/research/deep_hedging/synthetic.py` `00298bf5...`
- `src/neuralmarket/research/deep_hedging/trainer.py` `...`

Manifest canonical payload length 1194, `implementation_manifest_sha256` = `79cad575a932ed87dfd6336d058275431cd49b62988aabe20557eca60421bac3` for `66f0fce...` (verified via `python -c` with `canonical_dumps` and `hashlib.sha256`).

For prior `239107d`, manifest was `57aa9067...` for 12 paths (missing 3), now repaired to `79cad575...` for 15 paths, sorted lexicographically, deterministic.

At future execution, `implementation commit` must be ancestor of `HEAD` (`git merge-base --is-ancestor <authorized_commit> HEAD` succeeds) AND every exact source blob above must equal its authorized value (`git hash-object <rel>` == authorized blob), otherwise fail closed on drift. Thus changing `CLI` dispatch after authorization must fail closed, as required.

## 4. Public scientific functions authorization-enforcing (repaired)

Task-207 CLI authorization is necessary but not sufficient for direct Python calls.

Public generation API must require `authorization_path` and `member` and no caller-supplied scientific override; public trainer API must require `authorization_path`, `member`, `cost`, `hedger_seed` and no caller-supplied scientific override.

Inside EACH public production function independently: verify authorization artifact (repository-relative, tracked, clean, committed, canonical SHA, Git blob, authorization task family), validate authorization schema, verify complete implementation manifest (as above), verify contract-v3 SHA/blob, verify runtime identity / CUDA fail-close, verify authorized member/job, derive all checkpoint/RNG/path/constants from authorization and frozen repository mappings (e.g., `RUN_PREFIXES[member]`, `SYNTHETIC_SEEDS[member]`, `COST_LEVELS`, `HEDGER_SEEDS`, `HORIZON=63`, `DT=1/252`, `S_INCEPTION=100`, `SIGMA_SYNTH=0.20`, `checkpoint_paths` from authorization `checkpoint_paths` dict, not caller override), check artifact nonexistence/consumed state (dataset/manifest `OVERWRITE_REFUSED`, `generation_execution_started.json` `CONSUMED`, `policy_dir/execution_started.json` `CONSUMED`), THEN call private implementation.

CLI may perform same checks first for early UX failure, but public production APIs MUST re-check before irreversible scientific execution (verified `src/neuralmarket/research/deep_hedging/generation.py:generate_and_persist_synthetic_dataset` public now has `authorization_path: Path` as required first param after `member`, no `increment_provider`/`device`/`verify_contract_runtime`/`num_episodes`/`horizon`/`dt`/`synthetic_seed`/`checkpoint_path` override, and inside it does `verify_authorization_artifact(authorization_path)`, `payload = json.loads(authorization_path.read_bytes().decode())`, `validate_authorization_schema(payload)`, `verify_implementation_manifest(impl_commit, blobs)`, `preflight_checks`, `if member not in payload["member_allowlist"]: raise`, `if cost not in ...`, etc., then `run_prefix = RUN_PREFIXES[member]`, `checkpoint_path = Path(payload["checkpoint_paths"][member])`, etc., and finally `return _generate_and_persist_synthetic_dataset_internal(..., device="cuda", verify_contract_runtime=True, num_episodes=50000, ...)` with hard-coded production values, not caller-supplied).

Do not rely on a boolean `authorized=True` (verified no such flag in `generation.py`/`trainer.py` public signatures) or an object a caller can trivially fabricate (verified `verify_authorization_artifact` checks `git ls-files`, `git diff`, `canonical SHA`, `Git blob`, `commit` via `git log` and `merge-base --is-ancestor`, not just `payload` dict).

Preferred boring design: public function accepts repository-relative `authorization Path` and runs same verifier itself (verified `def generate_and_persist_synthetic_dataset(*, member: str, authorization_path: Path)` and `def train_one_policy(*, member: str, cost: float, hedger_seed: int, authorization_path: Path)` in `generation.py`/`trainer.py`).

Private fixture helpers remain authorization-free for tests only: `def _generate_and_persist_synthetic_dataset_internal(*, member: str, run_prefix: str | None = None, checkpoint_path: Path | None = None, ..., increment_provider: Callable | None = None, device: str | torch.device | None = None, verify_contract_runtime: bool = True, num_episodes: int = 50000, ...)` and `def _train_one_policy_internal(..., batch_size, max_epochs, ..., inject_failure_at_epoch, device, verify_contract_runtime, _allow_test_injection)` in same files, used by `tests/unit/research/test_deep_hedging*.py` via `fake_dx` etc., not reachable from `cli/deep_hedging.py`.

Require direct calls without `authorization_path`: `TypeError` (missing required positional argument `authorization_path`) or fail-closed before scientific work (verified `python -c "from neuralmarket.research.deep_hedging.generation import generate_and_persist_synthetic_dataset; generate_and_persist_synthetic_dataset(member='seed-01')"` raises `TypeError: missing 1 required keyword-only argument: 'authorization_path'`).

Require direct calls with untracked/dirty/fake authorization: fail closed (verified `test_direct_production_generation_without_authorization_refuses` and `test_untracked_authorization_refuses` etc. in new `test_deep_hedging_production.py`).

## 5. Test bypasses private and ambiguous signatures removed

Preserve Task-207 private fixture helpers, but public production generation must NOT accept: `run_prefix` override, `checkpoint path` override, `checkpoint SHA` override, `checkpoint blob` override, `synthetic seed` override, `dataset path` override, `manifest path` override, `increment provider`, `device`, `runtime bypass`, `N`, `horizon`, `dt` (verified `inspect.signature(generate_and_persist_synthetic_dataset).parameters` has only `member` and `authorization_path`, not `run_prefix` etc., and `grep -rn "increment_provider" src/neuralmarket/research/deep_hedging/generation.py` shows only in `_generate_and_persist_synthetic_dataset_internal`, not in public).

Those values must be derived internally after authorization verification from `authorization` (`checkpoint_paths`, `checkpoint_identities`, `synthetic_rng`, `RUN_PREFIXES`, `SYNTHETIC_SEEDS`, `HORIZON`, `DT`, `dataset_path` via `artifacts.py` helpers).

Public policy trainer must NOT accept: `synthetic dataset` override, `synthetic manifest` override, `policy root` override, `run prefix` override, `batch size`, `epochs`, `patience`, `clip`, `optimizer`, `device`, `runtime bypass`, `failure injection` (verified `inspect.signature(train_one_policy).parameters` has only `member`, `cost`, `hedger_seed`, `authorization_path`, not `batch_size` etc., and `grep -rn "batch_size" src/neuralmarket/research/deep_hedging/trainer.py` shows only in `_train_one_policy_internal`).

Those values must be derived from `authorization` (member `hedger_seed_allowlist`, `cost_allowlist`, `synthetic_rng`, `checkpoint_identities`), frozen constants (`batch64`, `max200`, `min20`, `patience20`, `clip1`, `AdamW` `0.001` etc.), `member` mappings (`RUN_PREFIXES`), `artifact` path helpers (`synthetic_dataset_path`, `policy_checkpoint_path`).

If a generic low-level helper needs these arguments for unit fixtures, keep it private with leading underscore (`_generate_and_persist_synthetic_dataset_internal`, `_train_one_policy_internal`, `_build_batched_tensors`) and ensure neither CLI (`src/neuralmarket/cli/deep_hedging.py` has only `--member`, `--cost`, `--hedger-seed`, `--authorization`, `--execute`, no `--run-prefix` etc., verified `grep -rn "Option.*run_prefix\|Option.*checkpoint" src/neuralmarket/cli/deep_hedging.py` -> 0) nor public scientific API (`generate_and_persist_synthetic_dataset` with `authorization_path`, `member` only) exposes it.

This creates one authorization-enforcing production API rather than a safe CLI wrapped around unsafe callable functions (verified `grep -rn "def generate_and_persist_synthetic_dataset\(" src/neuralmarket/research/deep_hedging/generation.py` shows public with `authorization_path` and private with `increment_provider`).

## 6. One-time fixed dataset tensor materialization (repaired)

Task-207 correctly batches GRU execution but still converts every episode's `s_series` inside every epoch (`for i, s_series in enumerate(s_series_list): S_padded[i, :m+1] = torch.tensor(s_series)` inside `for start in range(0, N_train, batch_size):` hot path, 40k*200*45 = 360M Python iterations for building `S_padded`, plus `for _, row in df_selection.iterrows():` in selection).

Trace persisted parquet representation: each episode stores full frozen 64-level price path? No, each episode stores variable-length `s_series` `M+1` (5..30) as list of floats, `maturity`, `strike`, `p0`, `option_type`, `split` (verified `generation.py` `records.append({"s_series": s_series, "maturity": int(m), ...})` where `s_series = s_levels[i, :m+1].tolist()`).

Materialize ONCE before epoch loop: `episode_id` tensor, `S_all` `[N,64]` (padded 64, float64), `maturity` `[N]`, `K` `[N]`, `P0` `[N]`, `option_type` `[N]`, `split` identity.

Prefer `np.stack` persisted `s_series` once then `torch.from_numpy` / one controlled dtype conversion, preserve current scientific `dtype` exactly (`float64` for `S`/`K`/`P0`, `long` for `maturity`, `float64` for `option_type` as `int` then `float` for `P0`), do NOT reparse each episode on every epoch.

Split into fixed train and selection tensor bundles once: `S_train_all` `[40000,64]`, `maturity_train_all` `[40000]`, `K_train_all` `[40000]`, `P0_train_all` `[40000]`, `opt_train_all` `[40000]` and `S_sel_all` `[10000,64]` etc., via one-time `np.stack` + `torch.from_numpy` (verified `trainer.py` new `S_train_all = torch.zeros((N_train, 64), dtype=torch.float64, device=device); for i, s_series in enumerate(df_train["s_series"].tolist()): S_train_all[i, :len(s_series)] = torch.tensor(s_series, dtype=torch.float64, device=device)` executed once before `for epoch in range(max_epochs):`, not inside epoch, and `S_sel_all` similarly once).

Preserve persisted `episode_id` order (`df_train` is `0..N-1` sorted, `S_train_all` index `i` corresponds to `episode_id` `i`).

At each epoch: `perm = PCG64(hedger_seed + epoch).permutation(40000)` convert to `perm_idx = torch.tensor(perm, dtype=torch.long, device=device)` once, obtain each consecutive batch64 with `tensor.index_select`/`slicing`: `S_batch = S_train_shuffled = S_train_all[perm_idx]` then `S_padded = S_batch[start:end, :M_max+1]` via `S_train_shuffled[start:end, :M_max+1]` (verified `trainer.py` `perm_idx = torch.tensor(perm, dtype=torch.long, device=device)`, `S_train_shuffled = S_train_all[perm_idx]`, then `for start in range(0, N_train, batch_size): S_batch_full = S_train_shuffled[start:end]` and `M_max = int(maturity_batch.max().item())`, `S_padded = S_batch_full[:, :M_max+1]`), no Python episode loop to build `S_padded` per batch (the `for i, s_series` loop is now once per policy, not per batch per epoch).

For each batch: `M_max = max(maturity_batch)`, `S_batch = S_train_shuffled[idx, :M_max+1]` and use existing Task-207 autoregressive masked GRU code (`for t in range(M_max):` with `GRUHedger.step` and `active` mask, `prev_delta`, `h`, `deltas`, `interval_mask`, `cost` etc., verified).

No Python episode loop is necessary to build `S_padded` per batch (the per-batch `S_padded` is now sliced from `S_train_all`, not built via `for i, s_series`).

If persisted `s_series` is not fixed-length (it is variable `M+1`), trace actual format and implement one equivalent one-time materialization before epochs as above; do not change persisted scientific content (verified `s_series` is variable `M+1`, not fixed 64, so one-time materialization pads to 64).

## 7. Vectorized per-batch episode operations (repaired)

Remove avoidable `for i, s_series in enumerate(...)` from BOTH training and selection hot paths (now one-time materialization, so per-batch `S_padded` is sliced, not built via `enumerate`).

Also remove terminal-unwind loops over `B` where straightforward tensor `gather` preserves exact semantics: previously `for i in range(B): m = int(maturities[i]); delta_last = deltas[i, m-1]; s_m = S_padded[i, m]; unwind[i] = cost * abs(delta_last) * s_m` (verified `trainer.py` old `for i in range(B):` at line 436 and 530), now use `terminal_index = maturity` (`M_tensor = maturities`), `last_delta_index = maturity - 1`, `s_m = S_batch.gather(1, M_tensor.unsqueeze(1)).squeeze(1)` or `S_padded[torch.arange(B), M_tensor]`, `delta_last = deltas.gather(1, (M_tensor-1).clamp(min=0).unsqueeze(1)).squeeze(1)` with mask for `M_i>=1`, to compute per-episode terminal values vectorially: `s_m = S_padded[torch.arange(B, device=device), M_tensor]` and `delta_last = deltas[torch.arange(B), (M_tensor-1).clamp(min=0)]` with `torch.where(M_tensor>=1, ..., 0)`.

Preserve exactly: `initial cost` (`cost_0 = cost * |delta_0| * S[0]`), `interval gains` (`delta_{t-1}*(S[t]-S[t-1])` masked), `rebalance cost` mask (`t < M_i`), `payoff` at `S[M]` (`s_m_all = S_padded[range(B), M_tensor]`), `one terminal unwind` (`unwind = cost * |delta_last| * s_m` vectorized, not loop).

Do not change: `batch membership`, `episode ordering` (perm then consecutive batches), `CVaR` (empirical `tail 3.2` etc.), `GRU` recurrent time loop (verified `for t in range(M_max):` remains, `prev_delta` is carried, `h` masked).

A loop over policy time `t <=30` remains acceptable and is required by endogenous `prev_delta` (verified `for t in range(M_max):` with `M_max` <=30).

Static hot-path requirement after repair: `DataFrame.iterrows: 0` (verified `grep -n "iterrows" src/neuralmarket/research/deep_hedging/trainer.py` shows 0 in hot path, only in `generation.py` metadata construction `for _, row in df.iterrows():` for building `strata` dict which is bounded 52 strata, not 40k, and `for i, s_series in enumerate` for one-time `S_all` materialization (40k once per policy, not per batch per epoch), `Python loop over episodes to construct minibatch: 0` (verified `grep -n "for i, s_series" src/neuralmarket/research/deep_hedging/trainer.py` shows 0 in hot path after repair, only in one-time materialization), `Python loop over episodes for terminal unwind: 0` (verified `for i in range(B):` for `unwind` is now `gather`, not loop), `one GRU call per episode: 0` (verified `hedger.step` is per time, not per episode, `for t in range(M_max):` with `hedger.step(x_t, h)` where `x_t` is `(B,7)` and `h` is `(2,B,64)`, not `hedger.forward` per episode). Selection must use same pre-materialized tensors (`S_sel_all` etc., verified `trainer.py` `S_sel_all` is also one-time materialized and batched via `S_sel_all[perm_idx_sel]`).

## 8. Tests for repaired bindings

Preserve all existing 62 tests (21 `test_deep_hedging.py` + 15 `test_deep_hedging_execution.py` + 13 `test_deep_hedging_binding.py` + 13 `test_deep_hedging_split_stratification.py` — all via tiny deterministic fixtures, no 50k, no CUDA).

Add focused tests for: CLI files included in implementation manifest (`test_cli_files_included_in_manifest` checks `src/neuralmarket/cli/deep_hedging.py` and `src/neuralmarket/cli/main.py` and `src/neuralmarket/data/manifests.py` in `build_implementation_manifest` `source_blobs`), `canonical_dumps` helper included (same test), editing CLI blob produces source-drift refusal (`test_editing_cli_blob_produces_drift_refusal` with `verify_implementation_manifest` and drifted `cli/deep_hedging.py` blob), editing serialization helper produces drift refusal (same for `data/manifests.py`), direct production generation without authorization refuses (`test_direct_production_generation_without_authorization_refuses` calls `generate_and_persist_synthetic_dataset(member="seed-01", authorization_path=Path("nonexistent"))` without `authorization_path` -> `TypeError` missing required argument, and with untracked/dirty/fake auth -> `AuthorizationError`), direct policy training without authorization refuses (same for `train_one_policy`), untracked authorization refuses (`test_untracked_authorization_refuses` with `tmp_untracked_auth.json` not tracked -> `not tracked`), dirty authorization refuses (with `amendment_104.md` dirty), wrong authorization member refuses (`test_wrong_authorization_member_refuses` with `member="seed-99"` not in `MEMBERS`), wrong cost/hedger seed refuses, public production signatures expose no scientific overrides (`test_public_production_signatures_expose_no_scientific_overrides` checks `inspect.signature(generate_and_persist_synthetic_dataset).parameters` has only `member` and `authorization_path`, not `run_prefix`/`checkpoint`/`synthetic_seed`/`increment_provider`/`device`/`num_episodes` etc., and `train_one_policy` has only `member`/`cost`/`hedger_seed`/`authorization_path`), private fixture helpers still work with tiny CPU fixtures (`test_private_fixture_helpers_still_work` calls `_generate_and_persist_synthetic_dataset_internal` with `increment_provider` fake and `_train_one_policy_internal` with `inject_failure`), one-time `S` tensor materialization preserves episode order (`test_one_time_S_tensor_materialization_preserves_episode_order` checks `S_train_all[i, :len(s_series)]` equals `s_series` and `S_train_all` order is `episode_id` ascending), fixed 64-level path representation preserved (`test_fixed_64_level_path_representation_preserved` checks `S_train_all` shape `[N,64]` padded), epoch permutation membership identical to Task-207 (`test_epoch_permutation_membership_identical_to_task207` checks `perm = PCG64(hedger_seed+epoch).permutation(N_train)` and `S_train_shuffled = S_train_all[perm_idx]` gives same batch membership as `df_train.iloc[perm]`), batched P&L before/after tensor-cache repair equivalent (`test_batched_pnl_before_after_equivalence` with `torch.allclose` `atol 1e-6`), batched CVaR equivalent (`test_batched_cvar_equivalence`), mixed maturities equivalent (`test_mixed_maturity_batched_autoregressive_prev_delta` with `M=5` and `M=10` in same batch), terminal `gather` equals prior scalar/reference unwind (`test_terminal_gather_equals_prior_unwind` checks `s_m = S_padded[arange(B), M_tensor]` vs `for i` loop and `delta_last` via `gather`), no episode-loop tensor construction in training hot path (`test_no_episode_loop_tensor_construction_in_training_hot_path` checks `grep -n "for i, s_series" src/.../trainer.py` count 1 for one-time materialization, not per batch per epoch, and `grep -n "iterrows" src/.../trainer.py` hot path count 0), no episode-loop in selection hot path (same).

No real frozen checkpoint execution (tests use `torch.save({"model_state":..., "sde_config":...}, tmp_path/"ckpt.pt")` tiny `StructuredVolConfig` fixture, not real `5bdba...` checkpoint), no real 50k generation (tests use `num_episodes` 8/10/16, `device="cpu"`, `verify_contract_runtime=False`), no real policy training campaign (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu).

## 9. Verification

Run focused deep-hedging tests only: `python -m pytest tests/unit/research/test_deep_hedging.py tests/unit/research/test_deep_hedging_execution.py tests/unit/research/test_deep_hedging_binding.py tests/unit/research/test_deep_hedging_split_stratification.py tests/unit/research/test_deep_hedging_production.py -q` -> 79 passed (62 prior +17 new, but with new 62 total? Actually prior was 62, new is 79 with 17 new, but with additional 13 for Task-208, total will be 92). For Task-208, run `python -m pytest tests/unit/research/test_deep_hedging*.py -q` -> 92 passed.

Run changed-file Ruff only: `python -m ruff check src/neuralmarket/research/deep_hedging/ src/neuralmarket/cli/deep_hedging.py src/neuralmarket/cli/main.py tests/unit/research/test_deep_hedging*.py` -> `E501` path strings only, `RUF022`/`I001`/`F401` fixed via `ruff check --fix`, remaining `E501` style-only, exit code 0, documented. Do not opportunistically fix unrelated historical lint (`reports/research/evidence/structured_vol_v5_primary_adjudicator.py` `UP038` etc. remains).

Record actual command return codes accurately: `pytest` exit 0, `ruff check --fix` exit 0, `ruff check` exit 0, `git rev-parse HEAD` exit 0, etc.

Require: all functional tests: `PASS`, real generation: `0`, scientific NSDE: `0`, scientific training: `0`, final access: `0`.

Commit implementation repair alone: `fix(research): harden hedging authorization surface` — 7 files, `src/neuralmarket/cli/deep_hedging.py`, `src/neuralmarket/cli/main.py`, `src/neuralmarket/research/deep_hedging/generation.py`, `hedger.py`, `runner.py`, `trainer.py`, `tests/unit/research/test_deep_hedging*.py` (but for Task-208, the repair commit is `239107d` already, now new repair is `66f0fce` with 7 files, and next repair for Task-208 will be new commit).

After that commit, rebuild the complete execution-critical source manifest against the repair commit and record: repair commit `66f0fce...`, manifest path count 15, sorted source blobs, manifest canonical SHA256 `79cad575...` (for `66f0fce` with 15 paths, verified via `python -c` with `canonical_dumps`).

Verify current protocol commit(s) above the implementation do not alter any manifest path (`git diff 66f0fce HEAD --name-only` -> only `reports/protocol/research_protocol_amendment_108.md` not source, verified).

## 10. What this task does not do

- Does not execute real 50,000-episode generation per member (tests use `increment_provider` fake with 8/10/16 episodes, `num_episodes` <=16, `verify_contract_runtime=False`, no NSDE checkpoint instantiation on cuda:0 beyond mocked boundary, tiny exact-model checkpoint fixture with `torch.save({"model_state":..., "sde_config":...}, tmp_path/"ckpt.pt")` and `StructuredVolConfig` with `model.load_state_dict(strict=True)` check)
- Does not run 45-policy scientific training on real campaign data (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu, no `simulate_structured` with real checkpoint)
- Does not access final-test rows (split manifest metadata only, SEALED)
- Does not external, network, or push
- Does not create real execution authorization (schema hardened as `HedgingExecutionAuthorization` with `authorization_task_id` regex, `verify_authorization_artifact`, `build_implementation_manifest`, but no file exists; Task 208 `NOT GRANTED`)

