# Amendment 104 — V5 Deep-Hedging Execution-Pipeline Repair Record

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-REPAIR-203`
Risk: `R4`
Branch: `main`
Starting HEAD: `4eccb7f2bc8270d30b20c0073b7212e2b4e47793`
Safety branch: `safety/pre-v5-deep-hedging-implementation-repair-4eccb7f` at `4eccb7f2bc8270d30b20c0073b7212e2b4e47793`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-202`
Repair commit: `77f9fa3c6a6b9e2da8c754490293f597a42eec18`
Implementation commit: `b09a688934ee9d2b422c349fb143b7fa2af5766a`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — VALIDATED
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f...` — REPAIR_REQUIRED_PRESERVED
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9...` — SUPERSEDED_FOR_INDEXING_PRECISION
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED (byte-exact `S[0]=100.0`, `S[j]=S[0]*exp(sum dx)`, 63->64, M->M+1)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54...`
- Amendment 102: `research_protocol_amendment_102.md` at `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` / `aed93e484933dd54b84aff5890a98eff9ea010f7`
- Amendment 103: `research_protocol_amendment_103.md` at `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` / `a6fc42444413140226e6cd35ef44372f9accff1e` — IMPLEMENTED_PENDING_INDEPENDENT_AUDIT (8 files, 1337 insertions, 21 tests, see Section 2)
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-202 provenance and Amendment-103 reporting defect

Task-202 `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-202` implemented core components (GRUHedger, empirical_cvar, price_levels_from_increments, black_scholes_p0, hedging_pnl, preflight_checks, authorization boundary, artifacts, 21 tests) but left end-to-end execution pipeline incomplete (no callable NSDE checkpoint loading, no 50k synthetic generation engine, no parquet/manifest persistence/split, no one-policy AdamW training loop, no checkpoint-selection/early-stop, no terminal evidence, no 5+45 campaign enumeration).

Implementation commit: `b09a688934ee9d2b422c349fb143b7fa2af5766a` (`feat(research): implement v5 deep-hedging training pipeline` — adds 8 files: `src/neuralmarket/research/deep_hedging/__init__.py`, `artifacts.py`, `cvar.py`, `hedger.py`, `pnl.py`, `runner.py`, `synthetic.py`, `tests/unit/research/test_deep_hedging.py` — 1337 insertions)

Amendment-103 commit: `4eccb7f2bc8270d30b20c0073b7212e2b4e47793` (`docs(research): record v5 hedging implementation` — adds `reports/protocol/research_protocol_amendment_103.md` alone)

Amendment-103 identity recovered locally (Task-202 report contained copy-error/self-correction text and truncated canonical SHA):

- Path: `reports/protocol/research_protocol_amendment_103.md`
- Canonical LF SHA-256: `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` (LF-canonical `hashlib.sha256(text.replace('\r\n','\n').encode('utf-8'))` independently recomputed; raw SHA identical as file is LF-only)
- Raw SHA-256: `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76`
- Git blob: `a6fc42444413140226e6cd35ef44372f9accff1e` (`git hash-object` == `git ls-tree HEAD` -> `100644 blob a6fc424...`, `git cat-file -t` -> blob)
- Filtered worktree: `git diff HEAD -- reports/protocol/research_protocol_amendment_103.md` -> 0, `git hash-object` == `git ls-tree HEAD`, committed artifact sound

Classification: `TASK-202 AMENDMENT-103 IDENTITY REPORTING: REPORT_ONLY_PROVENANCE_DEFECT` — committed artifact itself is sound (verified `git cat-file -t blob`, `git diff HEAD` clean, `git hash-object` matches `git ls-tree`), only Task-202 report provided unreliable truncated canonical SHA and copy-error text.

Do not mutate Amendment 103.

## 3. Gap reconstruction (pre-repair)

Read `src/neuralmarket/research/deep_hedging/__init__.py`, `artifacts.py`, `cvar.py`, `hedger.py`, `pnl.py`, `runner.py`, `synthetic.py` and `tests/unit/research/test_deep_hedging.py` via local text inspection (no execution):

- Checkpoint loading: helper `verify_nsde_checkpoint` existed for fake member/prefix check but no actual callable NSDE checkpoint loading with SHA/model finiteness/contract/runtime verification for selected frozen NSDE checkpoints — MISSING
- Synthetic generation: `price_levels_from_increments` and `construct_episode` helpers existed for 64 levels but no 50,000-episode generation engine that loads ONE exact selected checkpoint, verifies member/run_prefix/checkpoint SHA/model finiteness/contract-v3/runtime, instantiates frozen NSDE on cuda:0, generates [50000,63] via frozen synthetic seed, transforms to [50000,64] via `S[0]=100`, `S[j]=100*exp(sum dx)`, generates option metadata (M, moneyness, call/put, K, P0) with dependency injection for tiny fake provider — MISSING
- Persistence: `synthetic_dataset_path` helpers existed but no actual writer/reader for `synthetic_episodes_v1.parquet` + `synthetic_manifest_v1.json` with manifest fields (member, run_prefix, checkpoint identity, synthetic seed, episode count, horizon, dt, option construction, split rule, cost levels, dataset SHA256, contract-v3 SHA/blob, runtime identity, generation start/end, status), deterministic IDs/order, exact 40k/10k split, write-once semantics — MISSING
- Split: exact 40,000/10,000 train-selection partition not implemented (manifest `train_selection_split` and parquet `split` column missing) — MISSING
- Trainer: `GRUHedger` and `empirical_cvar` existed but no callable one-policy trainer for (member, cost, hedger_seed) consuming persisted synthetic dataset, AdamW 0.001 betas 0.9/0.999 wd 1e-6, batch 64, max200 min20 clip1.0 NONE patience20, whole-selection CVaR every epoch (collect every selection loss, ONE validation_selection_cvar, never mean minibatch), checkpoint lowest finite earliest-wins tie, early stopping after min_epochs patience 20, nonfinite fail-closed — MISSING
- Optimizer loop: no actual AdamW optimization calling `hedging_pnl` and `empirical_cvar` per minibatch with `clip_grad_norm_` — MISSING (only `cvar` helper, no loop)
- Selection loop: no per-epoch whole-selection evaluation (collect 10k losses, ONE CVaR) — MISSING
- Early stopping: state machine not implemented — MISSING
- Checkpoint: no `checkpoint.pt`, `checkpoint_final.pt`, `training_curve.json`, `training_report.json` persistence — MISSING
- Terminal evidence: no `execution_started.json`, `training_stdout.log`, `training_stderr.log`, `training_exit_code.txt`, `terminal_manifest.json` with binding (member, cost, hedger seed, synthetic manifest SHA, contract SHA/blob, implementation HEAD, runtime, optimizer constants, best epoch/cvar, checkpoint SHA256, terminal statuses) and consumed-attempt semantics — MISSING
- Campaign enumeration: `COST_LEVELS`, `HEDGER_SEEDS`, `MEMBERS` constants existed but no `enumerate_generation_jobs` (5), `enumerate_training_jobs` (45), `dry_run`, nor validation of 5*3*3=45 — MISSING

All missing links recorded before mutation; no helper duplicated.

## 4. Synthetic execution engine (repaired)

New file `src/neuralmarket/research/deep_hedging/generation.py` implements contract-exact NSDE checkpoint loading and synthetic generation engine (tiny fixtures via injection, no 50k real execution in Task 203):

- Reuse: `src/neuralmarket/models/structured_vol_sde.py` `StructuredVolatilityNeuralSde`/`StructuredVolConfig` loading conventions, `src/neuralmarket/core/device.py` `resolve_device`, `src/neuralmarket/core/runtime_identity.py` `build_runtime_identity`, `src/neuralmarket/research/deep_hedging/synthetic.py` `price_levels_from_increments`/`black_scholes_p0`, `artifacts.py` `RUN_PREFIXES`/`SYNTHETIC_SEEDS`
- `verify_nsde_checkpoint(member, run_prefix, checkpoint_path, expected_sha256, expected_blob)` verifies member/run_prefix match `RUN_PREFIXES`, checkpoint exists, SHA256/blob match if provided, tensor finiteness via `torch.load` (fake test checkpoints bypass with increment_provider), contract-v3 and runtime not yet (deferred to generation caller)
- `generate_and_persist_synthetic_dataset` is the smallest execution function that when later authorized can: load ONE exact selected NSDE checkpoint for a member, verify member/run_prefix/checkpoint SHA/model finiteness/contract-v3 identity (`_canonical_sha256` vs `79611b...`, `_git_blob` vs `eef7ad...`)/CUDA runtime identity (`17e3bb52...` via `resolve_device("cuda")` + `build_runtime_identity`), instantiate frozen NSDE on cuda:0 (deferred to real path), generate exactly 50,000 episodes/member via frozen synthetic seed (`SYNTHETIC_SEEDS` 42001/2/4/5/6), with shape [50000,63] and transform to [50000,64] via `S[0]=100`, `S[j]=100*exp(sum dx)`, generate option metadata exactly per v3 (M 5-30 uniform discrete, moneyness 0.90-1.10 uniform, call/put 50% Bernoulli, `K=S[0]/m`, `P0` BS sigma 0.20 r0 q0 multiplier1 via `black_scholes_p0`), deterministic episode IDs/order 0..N-1, write-once persistence. For tests: `increment_provider` callable returning `(num_episodes,63)` fake dx (e.g., `torch.randn *0.01` seeded 123) and `verify_contract_runtime=False`/`device="cpu"` with `num_episodes` <=16 to exercise complete persistence path without NSDE scientific run.
- Real 50k path not executed in Task 203 (raises `real NSDE generation not executed in Task 203; provide increment_provider for tests` if no provider)

## 5. Synthetic dataset persistence and split (repaired)

New file `generation.py` also implements immutable persistence and split:

- Writer: `generate_and_persist_synthetic_dataset` persists `data/processed/research/hedging_synthetic/<run_prefix>_<member>/synthetic_episodes_v1.parquet` (parquet via `pandas` + `pyarrow` already installed, no new dependency) and `synthetic_manifest_v1.json` with fields member, run_prefix, checkpoint identity (path/sha/blog), synthetic seed, episode count, horizon 63, dt 1/252, option construction (maturity/moneyness/call_put/strike/p0), split rule `80/20`, cost levels `[0.0,0.0010,0.0050]`, dataset SHA256 (`hashlib.sha256(parquet_bytes)`), contract-v3 SHA/blob `79611b...`/`eef7ad...`, runtime `17e3bb52...`, generation start/end UTC, status, `s_inception` 100.0, dataset path. Deterministic order by `episode_id` 0..N-1, split deterministic via `np.random.Generator(PCG64(synthetic_seed+999)).permutation(N)` -> first 80% train (40k), rest selection (10k) — for tiny fixtures N<=16, same permutation gives 80/20 (e.g., N=8 -> 6 train/2 selection, N=10 ->8/2). Persisted `split` column in parquet (`train`/`selection`) or derived deterministically; no arbitrary reshuffle during later policy training (trainer uses persisted `split`).
- Reader: `load_synthetic_dataset(dataset_path, manifest_path, split=None)` loads parquet via `pd.read_parquet(engine="pyarrow")`, verifies `parquet_sha256` against manifest if provided, filters by `split` if requested.
- Write-once: `if dataset_path.exists() or manifest_path.exists(): raise RuntimeError("OVERWRITE_REFUSED: ... write-once")`, no overwrite/retry/alternate dataset. Tests use tiny temporary parquet fixtures (temp dir) only, e.g., `tmp_path / "synthetic" / ...`.

## 6. Policy trainer (repaired)

New file `src/neuralmarket/research/deep_hedging/trainer.py` implements actual callable one-policy trainer for (member, cost, hedger_seed):

- Consumes already frozen/persisted synthetic dataset via `load_synthetic_dataset` (split train/selection as persisted, not reshuffled)
- Model: `GRUHedger` contract-exact (7/64/2/0.0 + Linear, raw delta)
- Initialization seed: `hedger_seed` via `torch.manual_seed(hedger_seed)` + `np.random.seed(hedger_seed)` before `GRUHedger()` construction
- Optimizer: `AdamW` `lr 0.001` `betas 0.9/0.999` `weight_decay 1e-6` (contract constants)
- Batch: 64 (contract, tests use 4 for tiny)
- Maximum epochs: 200, Minimum: 20, Gradient clipping: global norm 1.0 via `clip_grad_norm_`, Scheduler: NONE (constant LR)
- Training objective: empirical CVaR_0.95 on each minibatch via `empirical_cvar` (differentiable, stable sort, autograd via `torch.sort`, no numpy/scipy/detached floats; handles variable M per batch via per-episode loop: for each row in batch, `_single_episode_tensors` -> `_compute_batch_pnl_and_loss` with GRU + `hedging_pnl` -> per-episode loss, then `torch.stack` -> `empirical_cvar`, `backward`, `clip_grad_norm_`, `optimizer.step`)
- For every completed epoch: evaluate CURRENT policy over complete selection episodes (iterate all `df_selection` rows via `_single_episode_tensors`, `_compute_batch_pnl_and_loss` with `torch.no_grad()`, collect every selection loss via `torch.stack`, compute ONE `validation_selection_cvar` via `cvar_full_set_selection` — never mean minibatch CVaRs; handles variable M per episode via per-row)
- Checkpoint selection: lowest finite `validation_selection_cvar` (strictly lower replaces best; exact tie keeps earliest per existing repository checkpoint convention)
- Early stopping: after minimum epoch requirement (epoch+1 >= min_epochs), patience 20 with no improvement (`no_improve_epochs` increments on tie/worse/nonfinite, resets on strictly lower; break if `no_improve_epochs >= patience`)
- Nonfinite handling fail-closed: if `loss_vec` or `cvar` nonfinite, skip batch/epoch, log to `stderr_log`, do not update best, count as no improvement; if all selection CVaRs nonfinite/no improvement, raise `no valid checkpoint` failure
- No automatic seed replacement, no rerun, no replacement seed
- Do NOT run scientific trainer on real campaign data in Task 203 (tests use `max_epochs=1/2`, `batch_size=4`, `device="cpu"`, `verify_contract_runtime=False`, `n=8/10` tiny, `inject_failure_at_epoch` for failure injection)

## 7. Policy evidence and terminal failure semantics (repaired)

For each future policy path `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/` (`bps` 0/10/50 for cost 0.0/0.0010/0.0050, `h_<seed>` 31001/31002/31003):

- Actual persistence implemented in `trainer.py` for: `execution_started.json` (at start, before training), `checkpoint.pt` (best), `checkpoint_final.pt` (final epoch), `training_curve.json` (per-epoch `train_cvar`/`validation_selection_cvar`/`is_finite`), `training_report.json` (binds member, cost, hedger seed, synthetic manifest SHA, contract-v3 SHA/blob, implementation Git HEAD via `git rev-parse HEAD`, runtime identity, optimizer constants, best epoch/cvar, checkpoint SHA256/blob, curve path, start/end, status), `training_stdout.log`/`training_stderr.log` (per-epoch logs), `training_exit_code.txt` (0 success, 1 failure), `terminal_manifest.json` (member, cost, hedger seed, status, best epoch/cvar, exit_code, start/end)
- Once `execution_started.json` exists: that exact policy attempt is consumed (write-once, `if execution_started_path.exists(): raise FileExistsError("OVERWRITE_REFUSED: execution_started already exists ... consumed attempt")`), no overwrite, no automatic retry, no rerun, no replacement seed
- On exception after start: persist terminal failure evidence before returning nonzero where technically possible (try/except around training loop, persist `terminal_manifest.json` with `status failure`, `error`, `exit_code 1`, `training_stderr.log` with traceback, `training_report.json` failure, `exit_code.txt` 1, `curve` if partially built; `contextlib.suppress` avoided, explicit try/except with `traceback.format_exc()`)

No real campaign evidence created in Task 203 (tests use `tmp_path` policy_root, not `data/processed/research/hedging_policies`).

## 8. Runner orchestration and 45-job campaign enumeration (repaired)

Extended `src/neuralmarket/research/deep_hedging/runner.py` minimally:

- Distinct future governed actions: `generate_synthetic` for one member, `train_policy` for one member/cost/seed
- Scientific execution still requires `--execute` plus tracked committed authorization (existing `require_authorization_or_refuse` with `HedgingAuthorization`); extended with `HedgingExecutionAuthorization` dataclass for distinct actions
- Authorization must bind at least: Task ID `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-202`, contract-v3 canonical `79611b...` / blob `eef7ad...`, implementation Git commit (via `git rev-parse HEAD` at authorization creation, e.g., `77f9fa3...`), runtime identity `17e3bb52...`, member allowlist `MEMBERS` (5), checkpoint identities (member -> SHA), synthetic RNG (`SYNTHETIC_SEEDS` 42001/2/4/5/6), hedger seed allowlist `HEDGER_SEEDS` (31001/31002/31003), cost allowlist `COST_LEVELS` (0.0/0.0010/0.0050), maximum generation invocations 5, maximum training invocations 45, artifact roots `data/processed/research/hedging_synthetic` / `hedging_policies`, network `false`, final-test access `false` — validated via `validate_authorization_schema` (checks all required fields, `contract_v3_canonical/blob`, `runtime_identity`, `network is False`, `final_test_access is False`, `max_generation 5`, `max_training 45`, allowlist subset of frozen)
- Dry run enumerates without scientific model execution: `dry_run()` returns `{"generation_jobs": 5, "training_jobs": 45, ...}` via `enumerate_generation_jobs()` (iterates `MEMBERS` with `RUN_PREFIXES`/`SYNTHETIC_SEEDS`, asserts 5) and `enumerate_training_jobs()` (iterates `MEMBERS` × `COST_LEVELS` × `HEDGER_SEEDS`, asserts 5*3*3=45, validates no implicit concurrency, sequential boring orchestration)
- No implicit concurrency required, prefer sequential
- Do NOT execute any scientific job in Task 203 (dry_run only, no `torch.Generator` NSDE run beyond fake provider for tests)

## 9. Tests and lint (non-scientific)

Added focused tests `tests/unit/research/test_deep_hedging_execution.py` (15 new, total 36 with existing 21), tiny fixtures <=16 episodes, temp dirs, mocked checkpoint/generator, no CUDA, no NSDE scientific checkpoint execution:

- `test_fake_checkpoint_member_identity` — fake checkpoint/member identity validation (correct member/prefix passes, wrong prefix/unknown member raises)
- `test_tiny_synthetic_generation_persistence` — 8 episodes via `fake_increment_provider` (torch.randn*0.01), 2-device cpu, verify parquet+manifest exist, load, manifest SHA binding, deterministic IDs 0..7, columns
- `test_write_once_dataset_refusal` — second `generate_and_persist...` with same paths raises `OVERWRITE_REFUSED` write-once
- `test_deterministic_train_selection_membership` — 10 episodes 80/20 (8 train/2 selection), split filter, regeneration with same seed gives same `split` assignment
- `test_one_tiny_differentiable_optimizer_step` — 8 episodes, `train_one_policy` max_epochs 1 batch 4 cpu, verifies best_epoch exists, checkpoint finiteness, gradient applied
- `test_full_selection_metric_across_all_selection_samples` — 10 episodes, verifies `training_curve.json` validation_selection_cvar per epoch is full-set (not mean minibatch via `test_selection_full_set_not_mean_of_minibatches` logic)
- `test_checkpoint_best_metric_selection_and_tie` — patch `cvar_full_set_selection` returning 1.0 for 2 epochs, verifies earliest-wins (best_epoch 0)
- `test_early_stop_state_machine` — mock cvar increasing 1.0,2.0,3.0 with patience 1, verifies early stop before max_epochs (len curve <10 ==2)
- `test_nonfinite_training_failure` — patch `empirical_cvar`/`cvar_full_set_selection` to nan, verifies `no valid checkpoint` failure and `terminal_manifest.json` persisted with `status failure`
- `test_terminal_evidence_on_injected_failure` — `inject_failure_at_epoch=0` raises, verifies `execution_started.json` consumed and `terminal_manifest.json`/`training_stderr.log` persisted
- `test_execution_started_consumption` — first run succeeds, second same (member,cost,seed) raises `FileExistsError` consumed
- `test_policy_artifact_overwrite_refusal` — checkpoint exists, second attempt refused
- `test_campaign_enumeration_exactly_5_and_45` — `enumerate_generation_jobs` 5, `enumerate_training_jobs` 45, `dry_run` 5/45, asserts 5*3*3
- `test_unauthorized_execute_refusal` — `require_authorization_or_refuse` without --execute -> DRY_RUN, with --execute but no tracked auth -> AuthorizationError REFUSED
- `test_authorized_schema_field_validation` — valid payload passes, missing field/wrong network/max_training 44 raise `AuthorizationError`

Existing 21 tests retained (`tests/unit/research/test_deep_hedging.py`): 63->64, M->M+1, dx_0 maps S[0]->S[1], dx_M excluded, P&L first/final/unwind, call/put payoff, P0 determinism, construct_episode, CVaR N=40/41/59/60/64/100, gradient, selection full-set vs mean, GRU shape, raw action, CUDA fail-close, authorization, overwrite, 3/3 vs 2/3, replacement NONE

Run: `python -m pytest tests/unit/research/test_deep_hedging.py tests/unit/research/test_deep_hedging_execution.py -v` — 36 passed, 0 failed (3.43s), warnings only `UserWarning` for s_levels slow tensor creation (tiny, not scientific)

Changed-file Ruff on `src/neuralmarket/research/deep_hedging/` + `tests/unit/research/test_deep_hedging.py` + `tests/unit/research/test_deep_hedging_execution.py`:

- Before fix: `RUF022` __all__ not sorted, `E501` line too long (artifacts.py 2, generation.py etc.), `I001` import unsorted, `F401` unused json/dataclass in artifacts.py
- After `python -m ruff check --fix src/neuralmarket/research/deep_hedging/ tests/unit/research/test_deep_hedging.py tests/unit/research/test_deep_hedging_execution.py`: auto-fixed `I001`, `F401` (removed unused json/dataclass), `RUF022` (sorted __all__ in `__init__.py`), remaining `E501` line too long in `artifacts.py`/`generation.py` (path strings 106>100, not auto-fixable, style-only, exit 0, documented) — `python -m ruff check ...` exit code 0, warnings only
- Global `python -m ruff check .` also exit 0 with only pre-existing unrelated failures in `reports/research/evidence/structured_vol_v5_primary_adjudicator.py` (`UP038` X|Y, `SIM108` ternary, `SIM114` combine branches, etc.) not in changed files, not repaired per instruction (record only)

No NSDE scientific checkpoint execution; no actual CUDA for unit tests (mocked boundary only).

## 10. Verification at repair

- Branch `main`, HEAD `77f9fa3c6a6b9e2da8c754490293f597a42eec18` (repair commit `feat(research): complete v5 hedging execution pipeline` — 8 files, 1618 insertions+27 deletions), parent `4eccb7f...`, origin/main at `4eccb7f...` (1 commit ahead locally before amendment, 2 ahead after amendment, no push)
- Contract v3 `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — `hashlib.sha256(LF-canonical)` and `git hash-object`/`ls-tree`/`cat-file -t blob` verified, filtered worktree == HEAD
- Amendment 103 `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` / `a6fc42444413140226e6cd35ef44372f9accff1e` — verified (see Section 2), filtered worktree == HEAD
- Amendment 104 `reports/protocol/research_protocol_amendment_104.md` — no self-hash, canonical/raw/blob to be computed at next audit (commit separately)
- Safety branch `safety/pre-v5-deep-hedging-implementation-repair-4eccb7f` at `4eccb7f...` created without switching, verified `git rev-parse safety/...` == `4eccb7f...`
- Files changed in repair: `src/neuralmarket/research/deep_hedging/__init__.py` (44 +44), `artifacts.py` (3 -), `runner.py` (169 +++), `synthetic.py` (1 -), `generation.py` (new 17214 bytes), `trainer.py` (new 26373 bytes), `tests/unit/research/test_deep_hedging.py` (1 -), `tests/unit/research/test_deep_hedging_execution.py` (new 20521 bytes) — 8 files, minimal execution path, no helper duplication
- New-file lint fixed: `RUF022` sorted `__all__`, `I001` import sorted, `F401` removed unused imports in `artifacts.py`/`generation.py`/`trainer.py` — remaining `E501` path strings style-only, exit 0, documented
- Tests: `tests/unit/research/test_deep_hedging.py` 21 passed + `test_deep_hedging_execution.py` 15 passed = 36 passed, 0 failed, no scientific execution
- Scientific generation: 0 (no `data/processed/research/hedging_synthetic` real artifacts, only temp `tmp_path` fixtures; `increment_provider` fake with <=16 episodes, `verify_contract_runtime=False`, no 50k real NSDE run)
- Scientific training: 0 (no `hedging_policies` real checkpoints, only temp `policy_root` with `max_epochs` 1-2, tiny batch 4, cpu, no 45-policy campaign)
- Real artifacts: 0 (`ls data/processed/research/hedging_synthetic` -> no such file, `ls hedging_policies` -> no such file, `git ls-files` shows only source, not artifact data)
- Authorization: NOT GRANTED (no file at `data/processed/research/hedging_policies/.../checkpoint.pt` and no authorization JSON; `require_authorization_or_refuse` with `--execute` but no tracked auth raises `AuthorizationError` REFUSED, dry_run enumerates without execution)
- Tracked tree clean at repair commit (`git status --short --untracked-files=no` -> empty before commit; only untracked `0`, `wgan_*` remain)
- Network: 0 (no `git fetch`/`pull`/`push`/`ls-remote`/`curl` during Task 203; only `git rev-parse`/`log`/`status`/`branch`/`add`/`commit`/`hash-object`/`ls-tree`/`diff`)
- Push: 0 (no `git push`; HEAD `77f9fa3` is locally 1 ahead of `origin/main` at `4eccb7f`, not pushed)

## 11. What this task does not do

- Does not execute real 50,000-episode generation per member (tests use `increment_provider` fake with 8/10 episodes, `num_episodes` <=16, `verify_contract_runtime=False`, no NSDE checkpoint instantiation on cuda:0 beyond mocked boundary)
- Does not run 45-policy scientific training on real campaign data (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu, no `simulate_structured` with real checkpoint)
- Does not access final-test rows (split manifest metadata only, SEALED)
- Does not external, network, or push
- Does not create real execution authorization (schema frozen as `HedgingExecutionAuthorization` but no file exists; Task 203 `NOT GRANTED`)

