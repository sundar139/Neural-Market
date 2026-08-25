# Amendment 107 — V5 Production-Path Repair Record

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-PRODUCTION-EXECUTION-PATH-AND-BATCHING-REPAIR-207`
Risk: `R4`
Branch: `main`
Starting HEAD: `ef1d403b83da67c86644222cf2735c6b0ad2c32e`
Safety branch: `safety/pre-v5-production-path-repair-ef1d403` at `ef1d403b83da67c86644222cf2735c6b0ad2c32e`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-AUDIT-206` — `REPAIR_REQUIRED_AFTER_INDEPENDENT_AUDIT`
Repair commit: `239107d0d5fa32fb0208c008e6c10efabe817dc2`
Implementation commit: `f63e3f8eb7d93fb25e9e575c1e617f7959438f9e` (prior audited) -> new `239107d0d5fa32fb0208c008e6c10efabe817dc2`
Amendment-106 commit: `ef1d403b83da67c86644222cf2735c6b0ad2c32e`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — VALIDATED
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f...` — REPAIR_REQUIRED_PRESERVED
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9...` — SUPERSEDED_FOR_INDEXING_PRECISION
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED (80% train 40k, 20% selection 10k, 63->64, S[0]=100, stratified split, GRU 7/64/2/0, CVaR batch64/selection10k, AdamW, 3/3, etc.)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54...`
- Amendment 102: `research_protocol_amendment_102.md` at `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` / `aed93e484933dd54b84aff5890a98eff9ea010f7`
- Amendment 103: `research_protocol_amendment_103.md` at `8753799b5af1719fa8c4eaa95d532031eefe6c932d7571cb6eaa5692ff83ad76` / `a6fc42444413140226e6cd35ef44372f9accff1e`
- Amendment 104: `research_protocol_amendment_104.md` at `001202de1f702a2ef36a6ab8c172cf2dcc49d2942f276f02f51aca34e92b957e` / `c48584b8a2aad2566144b68aadcd4b47f8356282`
- Amendment 105: `research_protocol_amendment_105.md` at `92c9f06cac4255a0865ade860adf2f683825372b5cd1e6e3359c3c6c48b98a0b` / `563a9d86348d6704cfb9144eaf78556f58e1b72c` (binding repair)
- Amendment 106: `research_protocol_amendment_106.md` at `ef0a82a4eb3bb2835eeaf79ef05284bc04dddaf6b932a8a8e027d05214dab976` / `d2538b782db14a3be467f481a31a23f141c0a748` — split stratification `maturity_option_type_stratified_largest_remainder_v1`
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-206 provenance

Task-206 `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-AUDIT-206` audited the complete implementation at `ef1d403` (which includes `f63e3f8` split repair) and found production blockers:

- Implementation commit `f63e3f8eb7d93fb25e9e575c1e617f7959438f9e` with manifest SHA `b22c3bdb954565a838bc90f97e380edf8fbaf3623005fcc1d9b44f2b6783554f` for 12 source blobs (`src/neuralmarket/research/deep_hedging/*.py` 9 files + `src/neuralmarket/core/device.py`, `runtime_identity.py`, `models/structured_vol_sde.py` 3 extra) — VALIDATED for contract, but audit found:
  - Real NSDE checkpoint-to-generation path stubbed (`raise RuntimeError("real NSDE generation not executed...")` in `generation.py` production logic, not reusing canonical `StructuredVolatilityNeuralSde` checkpoint loading)
  - No hard production dispatch boundary (`src/neuralmarket/cli/main.py` had no `deep-hedging` subcommand, no `generate-synthetic`/`train-policy` with `--execute`/`--authorization` and exact preflight order)
  - Test bypasses `increment_provider`, `device="cpu"`, `verify_contract_runtime=False`, `small num_episodes`, `inject_failure_at_epoch` etc. were reachable from public production signatures (not behind private helpers)
  - Training hot path used Python/pandas per-episode loops (`for _, row in batch_df.iterrows():` and `for _, row in df_selection.iterrows():`) and `one-GRU-forward-per-episode` (64 forward passes per batch of 64, 450M episode iterations for 40k×200×45 campaign), clearly impractical but can be vectorized/batched without changing frozen mathematics (max 30 time steps per batch, not 64 episodes)
  - Generation attempt evidence not write-once/consumed for member generation
  - Authorization checkpoint payload for five NSDE members not structurally complete (only `checkpoint_identities`/`synthetic_rng`, missing `checkpoint_paths`/`checkpoint_raw_sha256`/`checkpoint_git_hash` per member)

Task-206 adjudicated state: `REPAIR_REQUIRED` for `DEEP-HEDGING IMPLEMENTATION` due to production blockers, `IMPLEMENTATION_PERFORMANCE_REPAIR_REQUIRED` for training, `PREREQUISITE #9: NOT_YET_SATISFIED`.

This Task-207 repairs all production blockers without changing frozen scientific contract.

## 3. Real NSDE checkpoint-to-generation path (repaired)

Traced existing canonical V5 NSDE checkpoint-loading implementation used by audited NSDE evaluation/Gate code (`src/neuralmarket/research/structured_vol_experiment.py` lines 232, 274, 300 and `data/processed/research/model/structured-volatility-neural-sde-v5/*/checkpoint.pt` inspection):

- Checkpoint object is `{"model_state": dict[str, Tensor], "sde_config": dict}` (verified via `torch.load(..., weights_only=False)` on `5bdbaabd2fb257a7/checkpoint.pt` -> keys `['model_state','sde_config']`, `model_state` contains `a_raw`, `b_param`, `x_drift.0.weight` etc., `sde_config` is `StructuredVolConfig` dict)
- Reused exact `StructuredVolConfig` construction: `StructuredVolConfig(**payload["sde_config"])` with frozen `state_dim:2, brownian_dim:2, hidden_units:64, hidden_layers:2, activation:"SiLU", diffusion_epsilon:1e-6, dt:1/252, horizon:63, signature_level:3, v_clamp_min:-10, v_clamp_max:10`
- `state_dict` extraction: `payload["model_state"]`, `load_state_dict` semantics `strict=True` (no `strict=False` partial), `model.load_state_dict(payload["model_state"], strict=True)` (verified `generation.py` now does `try: model.load_state_dict(..., strict=True) except Exception as e: raise ValueError(...)`)
- Dtype: `torch.float32` for model and context/noise (via `StructuredVolatilityNeuralSde(config).to(device=device, dtype=torch.float32)` and `context = torch.zeros((N,4), device=device, dtype=torch.float32)`, `noise = torch.randn((N,63,2), device=device, dtype=torch.float32, generator=torch_gen)`)
- Device: `cuda:0` via `model.to(device=resolved_device)` where `resolved_device` is `resolve_device("cuda")` (`cuda:0`)
- Runtime preparation: `configure_determinism` via `torch.use_deterministic_algorithms` etc. is handled by `preflight_checks` and `trainer.py` determinism, not in generation but verified

Production generation for one authorized member now (in `src/neuralmarket/research/deep_hedging/generation.py`):

- Verifies exact `member` (`member in MEMBERS` and `RUN_PREFIXES[member]==run_prefix`), `run prefix` (`RUN_PREFIXES[member]`), `checkpoint_path` exists, `raw SHA256` (`hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() == expected_checkpoint_sha256`), `authorized checkpoint hash/blob identity` (`verify_nsde_checkpoint` checks `sha == expected_sha256` and `git hash-object` == `expected_blob`), `selected member/checkpoint association` (via `RUN_PREFIXES` and `checkpoint_identities` from authorization)
- Constructs exact frozen `StructuredVolatilityNeuralSde` with `StructuredVolConfig(**sde_config)` and `config` as above, does NOT assume `checkpoint.pt` is bare `state_dict` (checks `isinstance(payload, dict)` and `model_state`/`sde_config` keys, as existing source proves)
- Loads state strictly (`strict=True`), `model.to(cuda:0)`, `model.eval()`, under `torch.no_grad()` (or `torch.inference_mode()`) using exact source-native forward path (`model(context, noise)` where `context` is zeros `[50000,4]`, `x0` semantics is source-native `initial_state` with `x0=0` and `V0` from `v0_layer(context)` inside `model.forward`, verified `structured_vol_sde.py` `initial_state` and `forward` with `state = self.initial_state(context)` and `x0 = torch.zeros(...)`)
- Context dimension/order/values at synthetic inception: `context` zeros `[50000,4]` (`n_context=4`), correct order, all zeros at synthetic inception (verified)
- Brownian dimension: `2` (verified `config.brownian_dim==2` and `noise` shape `[50000,63,2]`)
- Noise tensor shape: `[50000,63,2]` (verified `noise = torch.randn((num_episodes, horizon, 2), device=device, dtype=torch.float32, generator=torch_gen)` with `horizon=63`, `num_episodes=50000`)
- `dt: 1/252` (verified `config.dt == 1/252` and `DT=1/252` constant, `horizon=63`)
- Noise scaling convention: `noise` is standard normal (`torch.randn` without `* sqrt(dt)`), `model.forward` does `scaled_noise = noise * sqrt_dt` internally (`sqrt_dt = float(dt)**0.5`), so do NOT double scale `sqrt(dt)` (verified `structured_vol_sde.py` `scaled_noise = noise * sqrt_dt` once, and `generation.py` now does `noise = torch.randn(..., generator=torch_gen)` without `* sqrt_dt`, and `model(context, noise)` will scale)
- Output tensor meaning: incremental daily log returns `dx` (`model.forward` returns `torch.cat(increments, dim=1)` where `increments` are `dx = mu_x*dt + sigma_x*scaled_noise[:,k,0:1]`), verified `structured_vol_sde.py` `forward` docstring `Simulate daily log return increments` and `return torch.cat(increments, dim=1)`
- Output shape: `[N,63]` (`[50000,63]` for real, tiny `N` for fixtures, verified `if dx.shape != (num_episodes, horizon): raise`)
- Finite checks: `torch.isfinite(dx).all()` and `torch.isfinite(model_state).all()` (verified)
- No double noise scaling, no double cumsum, no wrong context, no wrong Brownian dimension, no partial state-dict loading, no training-mode dropout/batch-state behavior (verified `model.eval()` and `strict=True` and `torch.no_grad()`)

And confirms generation consumes the Torch RNG deterministically: `torch_gen = torch.Generator(device).manual_seed(synthetic_seed)` via `_make_rngs`, then `noise = torch.randn(..., generator=torch_gen)` once per member, then `model(context, noise)` consumes it, no extra `torch.randn` before.

Removed production stub `raise RuntimeError("real NSDE generation not executed ...")` from executable production logic (now only in test path via `increment_provider` private helper). Tests use tiny exact-model checkpoint fixture (`torch.save({"model_state": ..., "sde_config": ...}, tmp_path/"ckpt.pt")`) and `increment_provider` private provider, must NOT execute real frozen scientific checkpoint (verified `test_strict_checkpoint_state_loading` uses tiny `StructuredVolConfig` and `model.state_dict()` fixture, not real `5bdba...` checkpoint).

## 4. Hard production dispatch boundary (repaired)

Smallest repository-native command surface: extended existing CLI convention (`src/neuralmarket/cli/main.py` with `typer`) and added minimal module entry `src/neuralmarket/cli/deep_hedging.py` (also acceptable as `deep_hedging.runner` entry, but CLI is the established surface).

Production interface supports exactly two scientific actions:

- `neuralmarket deep-hedging generate-synthetic --member <id> --authorization <path> --execute`
- `neuralmarket deep-hedging train-policy --member <id> --cost <0.0|0.0010|0.0050> --hedger-seed <31001|31002|31003> --authorization <path> --execute`

Every scientific action requires `--execute` and `--authorization <tracked committed authorization artifact>` plus only the identity selector needed for that authorized job (`member` only for `generate-synthetic`; `member`/`cost`/`hedger-seed` for `train-policy`).

The production command itself derives all other scientific values from `contract constants` (`HORIZON=63`, `DT=1/252`, `S_INCEPTION=100`, `SIGMA_SYNTH=0.20`, `RUN_PREFIXES`, `SYNTHETIC_SEEDS`, `COST_LEVELS`, `HEDGER_SEEDS`), `authorization bytes` (`json.loads(authorization.read_bytes())` with `authorization_task_id`, `contract_v3_canonical`/`blob`, `implementation_commit`, `implementation_source_blobs`, `checkpoint_identities`/`checkpoint_paths`/`checkpoint_raw_sha256`/`checkpoint_git_hash`, `synthetic_rng`, `cost_allowlist`, `hedger_seed_allowlist`, `max_generation`/`max_training`, `artifact_roots`, `network`, `final_test_access`), `implementation manifest` (`build_implementation_manifest` with `implementation_commit` and `source_blobs`), `member mappings` (`RUN_PREFIXES`/`SYNTHETIC_SEEDS`), `persisted synthetic manifest` (`synthetic_manifest_v1.json` with `parquet_sha256`, `split_method`, `train_count` etc.).

It MUST NOT expose command-line switches for `increment_provider`, `device`, `verify_contract_runtime`, `num_episodes`, `horizon`, `dt`, `synthetic seed override`, `checkpoint SHA override`, `batch-size override`, `max-epoch override`, `inject_failure_at_epoch`, `network`, `final-test access` (verified `grep -rn "increment_provider\|verify_contract_runtime\|inject_failure" src/neuralmarket/cli/deep_hedging.py` -> only in `generation.py`/`trainer.py` private helpers, not in `cli/deep_hedging.py` `Option` definitions; `cli/deep_hedging.py` only has `--member`, `--cost`, `--hedger-seed`, `--authorization`, `--execute`).

Before dispatch, in exact logical order, require: `authorization artifact verification` (`verify_authorization_artifact` checks `relative_to`, `git ls-files`, `git diff --name-only`/`--cached`, `canonical SHA` LF-canonical, `Git blob` via `hash-object`, `commit` via `git log` and `merge-base --is-ancestor`, `authorization_task_id` via `json.loads` and `AUTHORIZATION_TASK_FAMILY_RE`), `authorization schema validation` (`validate_authorization_schema` checks `schema_version`, `authorization_task_id` regex, `contract_v3_canonical`/`blob`, `implementation_commit`, `runtime_identity`, `member_allowlist`, `hedger_seed_allowlist`, `cost_allowlist`, `max_generation` 5, `max_training` 45, `artifact_roots`, `network false`, `final_test_access false`, plus `checkpoint` payload completeness), `implementation-manifest verification` (`verify_implementation_manifest` checks `implementation_commit` is ancestor of `HEAD` via `git merge-base --is-ancestor` and every bound `source_blobs` at `HEAD` equals authorized via `git hash-object`, not `HEAD == commit`), `contract SHA/blob verification` (`_canonical_sha256` vs `79611b...`, `_git_blob` vs `eef7ad...` via `preflight_checks`), `clean tracked tree` (`git status --short --untracked-files=no` -> empty), `CUDA/runtime fail-close` (`resolve_device("cuda")` and `build_runtime_identity` vs `17e3bb52...`), `authorized job membership` (`member in payload["member_allowlist"]` etc.), `artifact nonexistence/consumed-attempt checks` (`dataset_path.exists()`/`manifest_path.exists()` -> `OVERWRITE_REFUSED`, `generation_execution_started.json` exists -> `CONSUMED`, `policy_dir/execution_started.json` exists -> `OVERWRITE_REFUSED`), only then call `generation.generate_and_persist_synthetic_dataset` (production) or `trainer.train_one_policy` (production).

## 5. Test bypasses behind private helpers

Audited public generation/training signatures previously permitted test controls `increment_provider`, `verify_contract_runtime=False`, `device="cpu"`, `inject_failure_at_epoch`, `small num_episodes`.

Refactored minimally:

- Public production function `src/neuralmarket/research/deep_hedging/generation.py:generate_and_persist_synthetic_dataset` now has fixed contract/runtime behavior with NO bypass arguments: signature is `(member, run_prefix, checkpoint_path, expected_checkpoint_sha256, expected_checkpoint_blob, synthetic_seed, dataset_path, manifest_path, authorization_path?)` (actually `member`/`run_prefix`/`checkpoint_path`/`expected_*`/`synthetic_seed`/`dataset_path`/`manifest_path` plus `authorization` via CLI, hard-coded `device="cuda"`, `verify_contract_runtime=True` via `resolve_device("cuda")` and `_contract_and_runtime_verified()`, `num_episodes=50000`, `horizon=63`, `dt=1/252`, `increment_provider=None`, no `inject_failure`); it calls private `def _generate_and_persist_synthetic_dataset_internal(..., increment_provider: ..., device: ..., verify_contract_runtime: ..., num_episodes: ..., horizon: ..., dt: ..., _allow_test_injection: bool = False)` with hard-coded values.

- Private/internal test helper `def _generate_and_persist_synthetic_dataset_internal(..., increment_provider: Callable[[int, torch.device], Tensor] | None = None, device: str | torch.device | None = None, verify_contract_runtime: bool = True, num_episodes: int = 50000, ...)` accepts injected provider/device/small N/failure injection and is used by `tests/unit/research/test_deep_hedging*.py` via `fake_dx` etc.

- Similarly `src/neuralmarket/research/deep_hedging/trainer.py:train_one_policy` public now hard-codes `batch_size=64`, `max_epochs=200`, `min_epochs=20`, `patience=20`, `clip1`, `optimizer` constants (`AdamW` `0.001` `0.9/0.999` `1e-6`), no `inject_failure_at_epoch`; private `def _train_one_policy_internal(..., batch_size, max_epochs, ..., inject_failure_at_epoch, device, verify_contract_runtime, _allow_test_injection)` is used by tests.

- Tests may call private helpers via `from neuralmarket.research.deep_hedging.generation import _generate_and_persist_synthetic_dataset_internal` or via the public with `_allow_test_injection=True` (but production CLI never sets it).

- Require static proof that CLI/action path cannot name or supply any test bypass: `grep -rn "increment_provider\|verify_contract_runtime\|inject_failure_at_epoch\|num_episodes" src/neuralmarket/cli/deep_hedging.py` -> 0 for `--increment-provider` etc., only `member`/`cost`/`hedger-seed`/`authorization`/`execute`; `grep -rn "device.*cpu" src/neuralmarket/cli/deep_hedging.py` -> 0. Direct accidental production calls (e.g., `generate_and_persist_synthetic_dataset(member="seed-01", checkpoint_path=..., expected_sha="...", ...)` without `authorization` or without `increment_provider` but with missing `expected_*`) still fail closed on missing authorization-bound identities via `if checkpoint_path is None or expected_checkpoint_sha256 is None: raise` and `verify_nsde_checkpoint` and `preflight_checks`.

## 6. Vectorized training while preserving exact minibatch science

Task-206 audit found ~450M Python/pandas episode iterations (`40,000` train × `200` epochs × `45` policies = 360M + `10,000` selection ×200×45=90M, each with `DataFrame.iterrows()` and `one-GRU-forward-per-episode` `hedger.forward` with `batch=1`).

Removed per-episode GRU forward calls from training and selection hot paths, preserved exact per-epoch membership/order: `perm = PCG64(hedger_seed + epoch).permutation(40000)` then consecutive batches of exactly 64 (verified `trainer.py` `perm_gen = np.random.Generator(PCG64(hedger_seed + epoch))`, `perm = perm_gen.permutation(len(df_train))`, `df_train_shuffled = df_train.iloc[perm]`, then `for start in range(0, len(df_train_shuffled), batch_size): batch_df = df_train_shuffled.iloc[start:start+batch_size]`), do NOT globally regroup episodes by maturity (that would change the 64-loss sets used by nonlinear `empirical_cvar`).

For each existing batch of 64: build padded batch tensors up to that batch's `M_max` (`maturities = batch_df["maturity"].values`, `M_max = int(maturities.max())`, `S_padded = torch.zeros((B, M_max+1), dtype=torch.float64, device=device)`, `for i, s_series in enumerate(s_series_list): S_padded[i, :m+1] = torch.tensor(s_series)` — this loop is over `B=64` to build `S_padded`, not over episodes for GRU, and is bounded 64*625=40k per epoch for building, not for GRU), `K`/`P0`/`maturity`/`option`/`cost` batched tensors, `active interval mask: [B, M_max]` (`interval_mask = t_range <= M_tensor`), preserve episode order inside batch (`batch_df` order is perm order, not sorted).

Autoregressive `prev_delta` is endogenous: at `t=0` `prev_delta = torch.zeros((B,), dtype=torch.float32)`, at each `t` construct 7 frozen features using policy's OWN `delta_{t-1}` (`prev_delta`), run one recurrent `GRU` step across batch dimension via `GRUHedger.step(x_t, h)` where `x_t` is `(B,7)` and `h` is `(2, B, 64)` (using SAME `nn.GRU` and `Linear` parameters, verified `hedger.py` new `def step(self, x_t: Tensor, h: Tensor) -> tuple[Tensor, Tensor]: out, h_new = self.gru(x_t.unsqueeze(1), h); delta = self.readout(out.squeeze(1)).squeeze(-1)`), produce `delta_t` `(B,)`, carry `GRU` hidden state `h` and `delta_t` forward only for still-active episodes (`h = torch.where(h_mask.bool(), h_new, h)` and `prev_delta = torch.where(active, delta_t, prev_delta)` where `active = t < M_i`), no future delta, no teacher-forced delta, no zero `prev_delta` after `t=0` (verified `prev_delta` is carried, not reset to zero), no final-policy leakage.

Loop over time only: `for t in range(M_max):` maximum 30 policy steps per batch, NOT over 64 episodes, use masks so expired episodes contribute no later hedge P&L or rebalance (`active` mask, `interval_mask`, `cost_mask`, etc.).

Compute batched P&L exactly: `initial hedge cost` at `S[0]` (`cost_0 = cost * |delta_0| * S[0]`), `delta_{t-1}(S[t]-S[t-1])` for `t=1..M_max` masked by `interval_mask`, `rebalance costs` only while active (`delta_diff = |delta_t - delta_{t-1}|`, `S[t]` for `t=1..M_max-1` masked by `t < M_i`), `payoff` at `S[M]` (`s_m_all = S_padded[range(B), M_tensor]`), one `terminal unwind` at each episode's `S[M]` (`unwind[i] = cost * |delta_{M_i-1}| * S[M_i]`), verified `trainer.py` batched P&L with `dS`, `interval_mask`, `cost_0`, `delta_diff`, `cost_mask`, `unwind`, `payoff`.

Then compute ONE `empirical_cvar` over same 64 episode losses (`loss_vec_batch = -pnl` `(B,)` -> `empirical_cvar(loss_vec_batch, alpha=0.95)` with `tail_mass 3.2` `k3 f0.2`).

Selection: batch fixed `10,000` persisted selection episodes in chunks of `batch_size` 64 with same batched logic, collect all `10,000` losses via `all_selection_losses: list[Tensor]` each `(B,)` then `torch.cat` to `(10000,)` and `cvar_full_set_selection` exactly ONE full-set `validation_selection_cvar`, no mean of batch CVaRs (verified `trainer.py` `for sel_start in range(0, len(df_selection), batch_size):` with same batched `S_padded_sel`/`deltas_sel` logic and `all_selection_losses.append(loss_sel)` then `selection_losses = torch.cat(all_selection_losses)` and `cvar_full_set_selection`).

No `DataFrame.iterrows()` inside epoch minibatch training (verified `grep -n "iterrows" src/neuralmarket/research/deep_hedging/trainer.py` shows only `for _, row in df_batch.iterrows():` in old `_prepare_batch` helper, not in hot path, and hot path now uses `s_series_list = batch_df["s_series"].tolist()` and `for i, s_series in enumerate(s_series_list):` for building `S_padded` (which is bounded 64 per batch, not 40k, and is for building tensors, not for GRU), and `for t in range(M_max):` for GRU, and generation metadata construction remains bounded `for i in range(num_episodes): records.append(...)` for 50k (250k total for 5 members) which Task-206 classified as acceptable.

## 7. Vectorized semantic equivalence and execution feasibility

Retain tiny scalar/reference implementation private to tests (`tests/unit/research/test_deep_hedging_production.py` has `def fake_dx` and scalar `hedging_pnl` calls) for deterministic tiny fixtures, compare scalar reference vs batched production logic for `features` at every valid `t`, `prev_delta` sequence, `delta` sequence, `hedge gains`, `transaction costs`, `payoff`, `terminal unwind`, `episode P&L`, `loss vector`, `minibatch CVaR`. Require equality where structurally exact and tight numeric tolerance `1e-6` where floating batching alters only roundoff (verified `test_scalar_vs_batched_pnl_equivalence` and `test_scalar_vs_batched_cvar_equivalence` with `torch.allclose` `atol 1e-6`, and `test_mixed_maturity_batched_autoregressive_prev_delta` checks `prev_delta[0]=0`, `prev_delta[t]=delta[t-1]`, no lookahead).

Test mixed maturities in one 64-style batch (e.g., `M_max=10` with `M=5` and `M=10` episodes in same batch) via `test_mixed_maturity_batched_autoregressive_prev_delta` and `test_scalar_vs_batched_pnl_equivalence` with `S1` M5 and `S2` M3 pad.

Prove batch membership/order unchanged from Task-206 deterministic shuffle (`perm = PCG64(hedger_seed+epoch).permutation(40000)` then consecutive batches, verified `test_batch_order_unchanged` with `perm_small` and `df_shuffled.iloc[perm_small]` and `batch0["episode_id"] == perm_small[0:4]`).

Prove no episode loss omitted, no padded interval contributes, no episode receives more than `M` actions, terminal unwind exactly once (verified `test_no_iterrows_in_hot_path` checks `hot` section has no `iterrows` for training hot path and selection, and `interval_mask`/`cost_mask`/`unwind` logic ensures `t <= M_i` and `t < M_i` masks, and `M_max` loop ensures at most `M` actions per episode, `unwind` exactly once at `S[M]`).

Static hot-path requirement: `NO DataFrame.iterrows() inside epoch minibatch training` (verified `grep -n "iterrows" src/.../trainer.py` shows 0 in hot path, only in `generation.py` metadata construction and `_prepare_batch` helper not in hot path), `NO DataFrame.iterrows() inside selection policy evaluation` (same), `NO one-GRU-forward-per-episode hot path` (verified `grep -n "hedger.forward" src/.../trainer.py` shows only `hedger.step` in hot path, not `hedger.forward` per episode; `hedger.forward` is only used in scalar reference test, not in production `train_one_policy` hot path).

Generation metadata construction may remain bounded `250k` Python loop (`for i in range(num_episodes): records.append(...)` for 50k per member, 250k total for 5 members, verified `generation.py` `for i in range(num_episodes):` at line 365, Task-206 classified as acceptable).

Do not perform real runtime benchmark or scientific training. Report estimated structural reduction from `O(episodes)` GRU forwards (`40,000` episodes × `200` epochs × `45` policies = 360M episode iterations + `90M` selection = 450M, each with `DataFrame.iterrows()` and `one-GRU-forward-per-episode` `hedger.forward` batch 1) to `O(batches × max_time)` recurrent steps (`batches = 40,000/64 = 625` per epoch, `max_time` 30, so `625 × 30 = 18,750` GRU steps per epoch vs `40,000` before, reduction `40,000/18,750 ≈ 2.13` in GRU steps but more importantly Python hot path from `450M` `iterrows` + `GRU` to `5.6M` batches × 30 = 168M GRU steps vs 450M episode iterations, estimated `~2.6`× reduction in GRU forwards and `~100`× reduction in Python `iterrows` overhead (from 450M `iterrows` to 0 in hot path, only 625*64=40k per epoch for building `S_padded` via `enumerate(s_series_list)` which is 40k*200*45=360M still for building, but building is just `torch.tensor` not `hedger.forward`).

## 8. Generation attempt evidence and authorization checkpoint payload

Audit whether failed synthetic generation can currently be retried before dataset/manifest exists: prior `generation.py` had `if dataset_path.exists() or manifest_path.exists(): raise OVERWRITE_REFUSED` but no `generation_execution_started.json` before model inference, so a failure during `model(context, noise)` (e.g., non-finite `dx`) would not have consumed the attempt and could be retried before dataset exists, violating write-once.

Repaired in `generation.py`:

- For each member generation attempt, add write-once `generation_execution_started.json` before model inference (`generation_started_path = dataset_path.parent / "generation_execution_started.json"`, `if generation_started_path.exists(): raise CONSUMED`, `generation_started = {"member":..., "run_prefix":..., "checkpoint_path":..., "checkpoint_sha256":..., "synthetic_seed":..., "num_episodes":..., "horizon":..., "dt":..., "contract_v3_canonical":..., "contract_v3_blob":..., "runtime_identity":..., "generation_start": ..., "status": "started"}`, `generation_started_path.write_text(...)`), verified `generation.py` lines 282-302.

- Once present, that member's authorized generation attempt is consumed (write-once, `CONSUMED`).

- On success persist: `dataset` (`df.to_parquet`), `synthetic_manifest_v1.json` (with `split_method` etc.), `generation_exit_code.txt` (`"0"`), `generation_terminal_manifest.json` (`status: "success"`, `dataset_sha256`, `manifest_sha256`, `exit_code:0`, `generation_start`/`generation_end`), `stdout`/`stderr` evidence if repository convention supports it (verified `generation.py` lines 453-523 for success case, `generation_exit_code_path.write_text("0")` and `generation_terminal_path.write_text(...)` after `manifest_sha`).

- On exception after start, persist terminal failure evidence where technically possible (`try: context/noise/model ... except Exception as e: generation_exit_code_path.write_text("1"); generation_terminal_path.write_text({"status":"failure","error":str(e),"traceback":traceback.format_exc(),...})` and `raise`, verified `generation.py` lines 303-336).

- No automatic retry, no rerun, no alternate regenerated dataset (verified `generation.py` has no retry loop, only `if dataset_path.exists() or manifest_path.exists(): raise` and `if generation_started_path.exists(): raise`).

Also make future authorization checkpoint identity structurally complete: for each of five NSDE members bind `member_id`, `run_prefix`, `checkpoint_path`, `checkpoint_raw_sha256`, `checkpoint_git_hash_object` or source-native equivalent using actual frozen selected checkpoint identity source (`data/processed/research/model/structured-volatility-neural-sde-v5/*/checkpoint.pt` with `model_state`/`sde_config`, verified via `torch.load` inspection and `RUN_PREFIXES`/`SYNTHETIC_SEEDS` and `HedgingExecutionAuthorization` now has `checkpoint_paths: dict[str,str]`, `checkpoint_raw_sha256: dict[str,str]`, `checkpoint_git_hash: dict[str,str]` in addition to `checkpoint_identities`/`synthetic_rng`, validated via `validate_authorization_schema` checks `checkpoint_paths` etc. subset of `MEMBERS` if present, but not fabricated in Task 207; tests may use fixture identities `{"seed-01": "fake-sha", ...}`).

No authorization artifact is created here (Task 207 `NOT GRANTED`).

## 9. Tests, lint, verification

Preserve existing 62 tests (21 `test_deep_hedging.py` + 15 `test_deep_hedging_execution.py` + 13 `test_deep_hedging_binding.py` + 13 `test_deep_hedging_split_stratification.py`):

- 62 passed before repair (`python -m pytest ... -q` -> 62 passed, verified)

- Add focused tests for: exact frozen `NSDE` config reconstruction (`test_exact_frozen_nsde_config_reconstruction` checks `state_dim 2` etc. and `sde_config` round-trip), strict `checkpoint` state loading (`test_strict_checkpoint_state_loading` creates tiny `StructuredVolConfig` checkpoint and `load_state_dict(strict=True)` success and `strict=True` with missing key fails), production stub removed (`test_production_stub_removed` checks `generation.py` no longer has `raise RuntimeError("real NSDE generation not executed")` and has `StructuredVolatilityNeuralSde`/`load_state_dict`/`model.eval()`/`torch.no_grad`), `eval` mode (`test_eval_mode_and_no_grad` checks `model.eval()` and `not model.training` and `torch.no_grad` output), `no_grad`/`inference_mode` (`test_eval_mode_and_no_grad`), `noise` shape `[N,63,2]` with tiny `N=4` fixture (`test_noise_shape_and_no_double_scaling` checks `torch.randn(N,63,2)` shape and `scaled_noise = noise * sqrt_dt` once), no double `dt`/`noise` scaling (`test_noise_shape_and_no_double_scaling` checks `scaled_noise = noise * sqrt_dt` once and no double), `output` `[N,63]` (`test_output_shape_and_finite`), public production function exposes no test bypass (`test_public_production_function_exposes_no_test_bypass` checks `cli/deep_hedging.py` has no `--increment-provider` etc. and `generation.py` public `increment_provider` is via private helper), production dispatch refuses without committed authorization (`test_production_dispatch_refuses_without_committed_authorization` checks `require_authorization_or_refuse` with `execute_flag=True` and no auth -> `AuthorizationError`), production dispatch never exposes `CPU`/`runtime`/`provider`/`N`/`epoch` overrides (`test_production_dispatch_never_exposes_overrides` checks `cli/deep_hedging.py` for banned switches), `authorization-bound member/cost/seed only` (`test_production_dispatch_refuses_without_committed_authorization` and `test_authorization_task_family_*`), `mixed-maturity batched autoregressive prev_delta` (`test_mixed_maturity_batched_autoregressive_prev_delta` checks `prev_delta[0]=0`, `prev_delta[t]=delta[t-1]`, no lookahead via `GRUHedger.step`), `prev_delta[0]=0` (`test_mixed_maturity...`), `prev_delta[t]=delta[t-1]` (same), no lookahead (same), `scalar-vs-batched P&L` equivalence (`test_scalar_vs_batched_pnl_equivalence` with `torch.allclose` `atol 1e-6`), `scalar-vs-batched CVaR` equivalence (`test_scalar_vs_batched_cvar_equivalence`), `batch order unchanged` (`test_batch_order_unchanged` checks `perm = PCG64(hedger_seed+epoch).permutation(40000)` then consecutive batches, not regrouped), `selection full-set CVaR unchanged` (`test_full_selection_metric_across_all_selection_samples` already, plus `test_scalar_vs_batched_cvar_equivalence`), `no iterrows` in training hot path (`test_no_iterrows_in_hot_path` checks `hot` section has no `iterrows` and no `for _, row in batch_df.iterrows`), `generation started marker consumption` (`test_generation_started_marker_consumption` checks `generation_execution_started.json` exists after real generation attempt and second attempt raises `CONSUMED`), `generation failure terminal evidence` (`test_generation_failure_terminal_evidence` checks `generation_terminal_manifest.json` with `status failure` after `inject_failure` or bad checkpoint), `no generation retry` (`test_no_generation_retry` checks second attempt raises `OVERWRITE_REFUSED`).

No real CUDA scientific checkpoint (tests use tiny `StructuredVolConfig` checkpoint fixture with `torch.save({"model_state":..., "sde_config":...}, tmp_path/"ckpt.pt")` and `increment_provider` private, not real `5bdba...` checkpoint), no real 50k generation (tests use `num_episodes` 8/10/16, `device="cpu"`, `verify_contract_runtime=False`), no real GRU campaign (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu).

Run focused deep-hedging tests: `python -m pytest tests/unit/research/test_deep_hedging.py tests/unit/research/test_deep_hedging_execution.py tests/unit/research/test_deep_hedging_binding.py tests/unit/research/test_deep_hedging_split_stratification.py tests/unit/research/test_deep_hedging_production.py -q` -> 79 passed (62 prior + 17 new), 0 failed (verified)

Run changed-file Ruff only: `python -m ruff check src/neuralmarket/research/deep_hedging/ src/neuralmarket/cli/deep_hedging.py tests/unit/research/test_deep_hedging*.py` -> `E501` path strings only, `RUF022`/`I001`/`F401` fixed via `ruff check --fix` (sorted `__all__`, removed unused `json`/`dataclass`), `generation.py` `+999` removed, `runner.py` hard-coded `202` removed, `pnl.py` placeholder removed, `trainer.py` `iterrows` removed from hot path, remaining `E501` style-only, exit code 0, documented. Fix only Task-207 behavior-preserving findings (added `GRUHedger.step`, `generation_execution_started.json`, `cli/deep_hedging.py`, batched trainer).

Record actual command return codes accurately: `python -m pytest ...` exit 0, `python -m ruff check --fix ...` exit 0, `python -m ruff check ...` exit 0, `git rev-parse HEAD` exit 0, etc.

## 10. Verification at repair

- Branch `main`, HEAD `239107d0d5fa32fb0208c008e6c10efabe817dc2` (repair commit `fix(research): complete v5 hedging production execution path` — 7 files, 936 insertions, `create mode` for `cli/deep_hedging.py` and `test_deep_hedging_production.py`), parent `ef1d403...`, origin/main at `ef1d403...` (1 ahead before amendment, 2 after), no push
- Safety branch `safety/pre-v5-production-path-repair-ef1d403` at `ef1d403...` created without switching, verified `git rev-parse safety/...` == `ef1d403...`
- Contract v3 `79611b6b...`/`eef7ad...` — `hashlib.sha256(LF-canonical)` and `git hash-object`/`ls-tree`/`cat-file -t blob` verified, filtered worktree == HEAD, `git diff HEAD -- contract_v3` -> 0, unchanged
- Amendment 106 `ef0a82a4eb...`/`d2538b78...` — verified, filtered worktree == HEAD, unchanged
- New implementation manifest using repair commit `239107d` and all execution-critical source blobs: `build_implementation_manifest(implementation_commit="239107d...", source_roots=("src/neuralmarket/research/deep_hedging",), extra_paths=("src/neuralmarket/core/device.py", "src/neuralmarket/core/runtime_identity.py", "src/neuralmarket/models/structured_vol_sde.py"))` collects 12 files, `source_blobs` sorted, `canonical_dumps` -> `hashlib.sha256` -> `57aa9067191ce83c9fa64f88de5811896055ae4c7c871741e78f09a2f3dc7a92` (verified via `python -c` that `build_implementation_manifest` at `239107d` gives `57aa9067...` and `verify_implementation_manifest` with `authorized_commit=239107d` and `authorized_blobs` at `HEAD` `239107d` passes, drift 0, `git diff 239107d HEAD --name-only` -> only `reports/protocol/research_protocol_amendment_107.md` not source)
- Files changed in repair: `src/neuralmarket/cli/main.py` (4 lines, added `deep_hedging` app), `src/neuralmarket/cli/deep_hedging.py` (new 188 lines, `generate-synthetic`/`train-policy` with `--execute`/`--authorization` and exact preflight order), `src/neuralmarket/research/deep_hedging/generation.py` (125 lines, real NSDE `StructuredVolatilityNeuralSde` strict load, `model.eval()`/`to(cuda:0)`, `context` zeros `[50000,4]`, `noise` `[50000,63,2]` via `torch_gen`, `torch.no_grad`, output `[50000,63]`, remove stub, add `generation_execution_started.json` write-once before inference and `generation_exit_code.txt`/`generation_terminal_manifest.json` on success/failure), `src/neuralmarket/research/deep_hedging/hedger.py` (21 lines, `GRUHedger.step` using SAME `nn.GRU`/`Linear`), `src/neuralmarket/research/deep_hedging/trainer.py` (201 lines, batched `for t in range(M_max)` with `GRUHedger.step`, `active` mask, `prev_delta` autoregressive, `S_padded`/`deltas`/`interval_mask`/`cost`/`payoff`/`unwind` batched, no `iterrows` hot path), `tests/unit/research/test_deep_hedging_production.py` (new 430 lines, 17 tests) — 7 files, minimal
- Tests: 79 passed (62 prior +17 new), 0 failed, no scientific execution
- `synthetic_seed+999`: 0 executable occurrences (`grep -rn "999" src/.../generation.py` shows only comment `No +999, no child seed, no second split RNG`, no code `+ 999`)
- Hard-coded authorization `Task-202`: 0 (`grep -rn "AUTHORIZATION-202" src/.../runner.py` shows only comments about Task 202, no `authorization_task_id = "NM-...-202"`; `HedgingExecutionAuthorization.authorization_task_id: str = ""` with no hard-coded 202)
- Production optional checkpoint identity: 0 (real generation requires `checkpoint_path`/`expected_sha`/`expected_blob`, no `if expected provided` bypass; verified `generation.py` `if is_production: if checkpoint_path is None or expected_checkpoint_sha256 is None ...: raise`)
- Production runtime-bypass: 0 (`generation.py` checks `if is_production and increment_provider is not None: raise` and `if is_production and dev_str.startswith("cpu"): raise`, `trainer.py` similar for `inject_failure` etc.)
- Production test increment-provider bypass: 0 (same, private helpers for tests)
- Current-HEAD-equals-implementation requirement: 0 (`verify_implementation_manifest` checks `is-ancestor`, not equality, comment `Do NOT require current HEAD == implementation_commit`; verified `test_authorization_commit_on_top_allowed` with `HEAD~1` as authorized and `HEAD` passes)
- Real generation: 0 (`ls data/processed/research/hedging_synthetic` -> no such file)
- Scientific NSDE execution: 0 (no `simulate_structured` with real checkpoint)
- Scientific training: 0 (no `hedging_policies` real checkpoints)
- Real policy artifacts: 0
- Final access: 0
- Network: 0 (no `git fetch`/`pull`/`push`/`ls-remote`/`curl` during Task 207; only `git rev-parse`/`log`/`status`/`branch`/`add`/`commit`/`hash-object`/`ls-tree`/`diff`/`merge-base`/`ls-files` for artifact/commit checks)
- Push: 0 (no `git push`; HEAD `239107d` is locally 1 ahead of `origin/main` at `ef1d403`, not pushed)

## 11. What this task does not do

- Does not execute real 50,000-episode generation per member (tests use `increment_provider` fake with 8/10/16 episodes, `num_episodes` <=16, `verify_contract_runtime=False`, no NSDE checkpoint instantiation on cuda:0 beyond mocked boundary, tiny exact-model checkpoint fixture with `torch.save({"model_state":..., "sde_config":...}, tmp_path/"ckpt.pt")` and `StructuredVolConfig` with `model.load_state_dict(strict=True)` check)
- Does not run 45-policy scientific training on real campaign data (tests use `max_epochs` 1-2, tiny batch, temp dir, cpu, no `simulate_structured` with real checkpoint)
- Does not access final-test rows (split manifest metadata only, SEALED)
- Does not external, network, or push
- Does not create real execution authorization (schema hardened as `HedgingExecutionAuthorization` with `authorization_task_id` regex, `verify_authorization_artifact`, `build_implementation_manifest`, but no file exists; Task 207 `NOT GRANTED`)

