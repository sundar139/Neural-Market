# Amendment 100 — V5 Deep-Hedging Training Contract Freeze

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-FREEZE-197`
Risk: `R4`
Branch: `main`
Starting HEAD: `3045a26faa74f4a354c37b9f110ac523509903d8`
Safety branch: `safety/pre-v5-deep-hedging-contract-3045a26` at `3045a26faa74f4a354c37b9f110ac523509903d8`
Prerequisite: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-CVAR-ESTIMATOR-AUDIT-196` — `VALIDATED`
Harness prerequisite #8: `SATISFIED` (harness v3 VALIDATED)
Task-196: `VALIDATED`
SAP: `VALIDATED`
H2 state: `H2_NOT_SUPPORTED` preserved
Status: APPEND-ONLY TRAINING-CONTRACT FREEZE — contract freeze only; no training, no GRU model creation, no generator execution, no scientific synthetic-path generation, no inference, no bootstrap, no validation, no external validation, no network, no push, no final-test row access

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily, H3 synthetic-NSDE vs BS, 95% CVaR primary, entropic secondary, proportional costs)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, Strategy B, gating rule)
- H2 Amendment 095: `research_protocol_amendment_095.md` at `fa28687` (H2_NOT_SUPPORTED)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v1: `structured_vol_v5_final_test_single_access_harness_v1.md` at `f12490e310b6.../b7c24126...` (REPAIR_REQUIRED, preserved)
- Amendment 097: `research_protocol_amendment_097.md` at `2b85791803b5.../dbfd2eff...` (preserved)
- Harness v2: `structured_vol_v5_final_test_single_access_harness_v2.md` at `7a28cb149e58.../676c5932...` (VALIDATED_EXCEPT_CVAR_PRECISION, preserved)
- Amendment 098: `research_protocol_amendment_098.md` at `487a666f1093.../40666ace...` (preserved)
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at canonical `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084425c902825e754b0c24a3069e08f2b` — VALIDATED (CVaR fractional-tail estimator, P&L, BS r=0/q=0, CBB L=20 B=10000 PCG64(9491))
- Amendment 099: `research_protocol_amendment_099.md` at `983da31d51b2.../852718e5...` (preserved)
- NSDE family: `reports/research/structured_vol_v5_n5_family_analysis_v1.json` (five valid members seed-01,02,04,05,reserve-j01)
- NSDE config: `configs/research/structured_vol_neural_sde_v5.yaml` (state_dim 2, Brownian 2, hidden 2×64 SiLU, dt 1/252 horizon 63, AdamW lr 0.001)
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test 2023-11-22 through 2025-12-31, 528 XNYS, sealed, metadata only)

Conflicts: None — all sources consistent on GRU named, SPY European, 95% CVaR, proportional costs, synthetic NSDE, five NSDE members.

## 2. Training contract

Training-contract path: `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v1.md`
Training-contract canonical SHA-256: `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea`
Training-contract Git blob: `2d8f5ad21f6af30d54f8897075a4e69734ffa56f`
Training-contract commit: `7064069e4dcdf67cf204dbc7cbe692ed132c7ccf` (`docs(research): freeze v5 deep-hedging training contract`)
Status: `FROZEN_PENDING_INDEPENDENT_AUDIT`
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-FREEZE-197`

## 3. NSDE cohort (bound)

- seed-01 `v5-seed-01` `5bdbaabd2fb257a7` selected `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f` blob `6820d07c0fb253a02337190d7c8683b5c01cb3f3` final `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4` blob `6d0ead19a92c9c93422ab2b9c38b3d4bbbc5d7c`
- seed-02 `v5-seed-02` `62c7406cb3a2c642` selected `9e6f8cd030d073d59324514d5a1ef6e87be6e3dbfb16b8cec7aa13928fd84f7a` blob `592df5d33f9342901a1c9e4b9cae4c52f29c6a1c` final `b867af03b7a00dce6f4b34bcaf31896ddb891c9ba18e722dd2abb02ddf18ac8a` blob `feef0df2fc721db3e1aea4ca80ea1b985e436`
- seed-04 `v5-seed-04` `77e7de9efabb7ce3` selected `87d022152ba28f881f454a76aee1b572061e288fd3eee31b1ca52f2ba88cc35` blob `3701888ef57f20132c77633f6aca2d6e6e3861` final `4927e6b6b575e20a20fc5ee225ac3400ad7e9524871b155d0cdfbf8ec9d4c72` blob `c029db1e272117d73b6d596c2d4933aaf90bb`
- seed-05 `v5-seed-05` `1e8aa171993a1aba` selected `3a71b12e1c0af08ea2c254fa6e162a09dd32dd47b399d6dc7585b264e33abef` blob `808db090fe34f15b22d8062866846cde4d829` final `4d3b9475fbc9adba09b20822bd5941e367b4dc5b278f1ffb8d5954276a0a9c99` blob `de846f5c671f492e4d909c99e7a534a1faeba`
- reserve-j01 `reserve-j01` `38c5113b27568e14` selected `50d14095d95386c0fb7e1ee5ab43175272f02bfa84fbec3ddc6c8fe2a97326` blob `38c9f8a0c8f97c64ce82e2ad38a0fea754a6a9` final `a4713691abb886a8151a6efa98dc2163068e147d1ea98d11d2c9a28b0e9b219` blob `19620280adef3ae6224300e18d9d63496d334`

All `GATE_PASS_VALID`.

## 4. GRU architecture and input/action contract

Input features per hedging step `t` (7-dimensional, exact order `f1..f7`):

1. `f1 = T_t_norm = remaining_sessions /30` (`T_t = remaining XNYS sessions /252.0`, normalized to `[0,1]`)
2. `f2 = moneyness = S_t / K`
3. `f3 = log_moneyness = ln(S_t / K)`
4. `f4 = log_return_from_inception = ln(S_t / S_0)`
5. `f5 = prev_delta = delta_{t-1}` (`delta_{-1}=0`)
6. `f6 = cost_norm = c /0.0050` (`0,0.2,1.0` for `0,0.0010,0.0050`)
7. `f7 = option_type = +1` call, `-1` put

Tensor ordering: input sequence per episode shape `[T_episode,7]` where `T_episode` in `[5,30]`; batch shape `[batch,T_episode,7]` padded to `max_T_in_batch` with mask; `float32` features, `float64` for `S/K/T` before feature computation; ordering exactly `f1..f7`.

GRU: `num_layers=2`, `hidden_size=64`, `dropout=0.0` between layers, `normalization=none`, initial hidden zeros `[2,batch,64]`, readout `nn.Linear(64,1)` linear (no activation), output is `delta_t` target hedge ratio per unit short option (shares of SPY per option), no bounds/transformation (raw linear).

## 5. Training objective and cost-policy semantics

- Objective: empirical `95% CVaR` of hedging loss `L=-P&L` where `P&L` is per Section 5 hedging P&L (`P0 + sum delta_{t-1}*(S_t - S_{t-1}) - Payoff_T - sum costs` with premium Included, cash r=0, unwind Yes) and `CVaR_0.95` is the exact fractional-tail estimator from harness v3 Section 4B (`alpha=0.95, tail_mass=0.05*N, k=floor, f fractional, mean of k largest + f*x_(N-k) /tail_mass`). No mean-plus-CVaR, no entropic, no alternative.

- Transaction costs at training: `cost_t = c*|delta_t - delta_{t-1}|*S_t` with `delta_{-1}=0`, including initial `c*|delta_0|*S_0` and terminal unwind `c*|0 - delta_T|*S_T` at `S_T`, same as evaluation. Cost levels `0,0.0010,0.0050`.

- Cost-policy design: `separate policy per cost level` — each cost level has its own GRU model. Expected trained policy count: `45 = 5` generators × `3` hedger seeds × `3` cost levels.

## 6. Synthetic training data

- Paths/member: `50,000` synthetic option hedging episodes per generator member from its selected checkpoint simulation.

- Horizon: `63`, `dt=1/252` (Euler/Ito, same as NSDE).

- Context: NSDE simulation unconditionally from `x0=0` and `z0` with zero context, no extra lookback beyond NSDE internal state.

- Option construction per synthetic path: one episode per path, maturity `T_epi` uniform discrete `[5,30]`, moneyness `m = S_0/K` uniform continuous `[0.90,1.10]`, strike `K=S_0/m`, call/put balance `50%` calls `50%` puts (`p=0.5` Bernoulli), balanced across 50k.

- Split: `80%` train (`40,000`) / `20%` selection (`10,000`) per generator, stratified, seeded by synthetic RNG.

- Generator RNG: per generator distinct: seed-01 `42001`, seed-02 `42002`, seed-04 `42004`, seed-05 `42005`, reserve-j01 `42006` (torch.Generator.manual_seed + numpy PCG64 same seed). Distinct from hedger seeds and all other RNGs.

- Persistence: generated once per generator member and persisted at `data/processed/research/hedging_synthetic/<run_prefix>_<member>/synthetic_episodes_v1.parquet` with `synthetic_manifest_v1.json` containing generator member, checkpoint SHA, synthetic seed, num_episodes, horizon, dt, sampling distributions, split, cost levels, parquet SHA.

## 7. Optimization, checkpoint selection, and completeness

- Hedger seeds: `31001, 31002, 31003` (integer, GRU init/optimizer/shuffle, distinct).

- Optimizer: `AdamW`, `lr=0.001`, `beta1=0.9`, `beta2=0.999`, `weight_decay=1e-6`.

- Batch size: `64`.

- Maximum epochs: `200`.

- Gradient clipping: `grad_norm_clip=1.0`.

- Scheduler: `none` (constant lr).

- Early-stopping metric: `CVaR_0.95(L)` on synthetic selection set (`10,000` episodes) via harness v3 fractional-tail estimator, smaller CVaR better.

- Early-stopping patience: `20` epochs.

- Minimum epochs: `20` before early stopping can trigger.

- Checkpoint-selection metric: `validation_selection_cvar` (lowest CVaR on selection set); best checkpoint is best_epoch where metric minimal.

- Nonfinite failure: training or validation loss `nan/inf` at an epoch => epoch invalid, not selected; if all epochs nonfinite or no valid checkpoint, policy `INVALID` (`GATE_FAIL_NONFINITE_TRAINING_FAILURE`).

- Runtime/device: `CUDA` if `torch.cuda.is_available()` else `CPU`; GPU paths use deterministic flags (`deterministic=true`); each report records `runtime` (`CPU`/`CUDA`) and `deterministic`.

- Policy completeness: for a generator member `g` to enter primary H3 at cost `c`: `ALL THREE` preregistered hedger seeds must have valid selected checkpoints: `valid hedger count per generator per required cost level = 3/3`. No silent mean_h denominator shrink from 3 to 2. If not `3/3`, that `g/c` stratum is `INVALID` for confirmatory H3 and its `Delta_g` is `nan`, making cost level primary `nan`.

- Replacement seeds: `NONE` — failed preregistered policy remains failed and blocks that generator/cost primary; no automatic replacement seed.

- Global failure: if `>20%` of expected `45` policies fail (10 or more invalid), overall H3 confirmatory claim blocked.

## 8. Artifact contract

- Policy path per `(g,c,h)`: `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/checkpoint.pt` (best), `checkpoint_final.pt` (final), `training_curve.json`, `training_report.json`; `<bps>` `0`/`10`/`50` for `c=0/0.0010/0.0050`.

- Checkpoint identity: SHA-256 of `checkpoint.pt` bytes and Git blob via `git hash-object`, recorded in training report.

- Report path: `training_report.json` contains `schema_version` (`hedging-gru-training-report-v1`), `member_id`, `cost_bps`, `hedger_seed`, `synthetic_seed`, `synthetic_manifest_sha256`, `optimizer` (`AdamW lr 0.001 betas 0.9/0.999 wd 1e-6`), `batch_size 64`, `max_epochs 200`, `early_stopping` (`patience 20 min_epochs 20 metric validation_selection_cvar`), `best_epoch`, `best_validation_cvar`, `runtime`, `git_head`, `checkpoint_sha256`, `checkpoint_git_blob`, `training_curve_sha256`.

- Config identity: this contract path `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v1.md` canonical SHA and Git blob plus hyperparameters frozen herein.

- Runtime identity: per-policy report records `runtime` and `device`, deterministic flag.

- Overwrite semantics: write-once per `(g,c,h)` — if path exists, no overwrite; training not rerun.

- Retry/rerun semantics: `NONE`.

## 9. Final-test preservation

- Final test: `SEALED`
- Final-test access count: `0`
- Final-test entitlement: `NONE`
- Final-test authorization: `NOT GRANTED`
- Scientific final-test execution: `0`
- Deep hedging execution: `0`
- Deep-hedging training execution: `0`
- Training: `0`
- Gate: `0`
- Model inference: `0`
- Bootstrap execution: `0`
- Validation: `0`
- External validation: `0`
- Network: `0`
- Push: `0`

No final-test scientific rows were read. No hedging execution occurred.

## 10. Commit record

- Training contract committed alone at `7064069e4dcdf67cf204dbc7cbe692ed132c7ccf` (`docs(research): freeze v5 deep-hedging training contract`)
- This Amendment 100 commits separately at its own hash (see verification)

No amend, no rebase, no reset, no push.

This amendment is append-only, contains no self-referential hash.
