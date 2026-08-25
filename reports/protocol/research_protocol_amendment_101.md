# Amendment 101 — V5 Deep-Hedging Training Contract Repair

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-REPAIR-198`
Risk: `R4`
Branch: `main`
Starting HEAD: `5082392d6c59cc60d4387959538673b96e4e30fc`
Safety branch: `safety/pre-v5-deep-hedging-contract-repair-5082392` at `5082392d6c59cc60d4387959538673b96e4e30fc`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-FREEZE-197` — `REPAIR_REQUIRED`
Task-197: `FROZEN_WITH_LOAD_BEARING_CONTRACT_DEFECTS`
Training contract v1 preserved: `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v1.md` at canonical SHA `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` Git blob `2d8f5ad21f6af30d54f8897075a4e69734ffa56f` — byte-identical, not edited
Training contract v2 path: `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v2.md`
Training contract v2 canonical SHA-256: `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7`
Training contract v2 Git blob: `4a37528eb9d8f8f6ead0d2b471e3c16c99e33b5e`
Training contract v2 commit: `6f367c8` (actual commit `6f367c8d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0`; see Section 10)
Status: APPEND-ONLY TRAINING-CONTRACT REPAIR — contract repair only; no training, no GRU model training, no scientific synthetic-path generation, no generator inference, no bootstrap, no validation, no external validation, no network, no push, no final-test row access

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger named, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily, H3 synthetic NSDE vs BS 95% CVaR, H4/H5 secondary)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, Strategy B level-3 RBF-MMD Euler/Ito, H3 synthetic-NSDE GRU vs BS family)
- H2 Amendment 095: `research_protocol_amendment_095.md` at `fa28687` (H2_NOT_SUPPORTED)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` (VALIDATED, CVaR fractional-tail, P&L, BS r=0/q=0 T XNYS/252, CBB L=20 B=10000 PCG64(9491))
- Amendment 099: `research_protocol_amendment_099.md` at `983da31d51b2.../852718e5...` (preserved)
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f6...` (FROZEN_WITH_DEFECTS, preserved)
- Amendment 100: `research_protocol_amendment_100.md` at `8605139d9c9d71c0815edd57692034944ba6e5ad704452d03203a0f04d998825` / `50dccb37d64f...` (preserved)
- Runtime sources: `AGENTS.md`, `docs/engineering/agent-contract.md`, `src/neuralmarket/core/runtime_identity.py` (`build_runtime_identity` `runtime-identity-v1`), `src/neuralmarket/core/device.py` (`resolve_device` fail-closed), `src/neuralmarket/core/reproducibility.py` (`seed_everything`), `.venv-gpu` conventions (Python 3.11.9 torch 2.13.0+cu132 CUDA 13.2 cuDNN 92000), NSDE `src/neuralmarket/models/structured_vol_sde.py` (`StructuredVolatilityNeuralSde.forward` emits log-return increments), `reports/protocol/research_protocol_amendment_035.md` (runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`)
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test 2023-11-22 through 2025-12-31, 528 XNYS, sealed)

## 2. Defect closure scope

Task-197 training contract v1 preserved byte-identically (not edited). Task-197 defects were:

- CUDA scientific runtime not explicitly CUDA-only with fail-closed no CPU fallback
- GRU recurrent gate activation misstated as SiLU instead of standard sigmoid/tanh
- NSDE output to tradable price-path transformation not executable (latent vs price, x0=0 / normalized scale incomplete)
- Synthetic option premium P0 not frozen (pricing model, vol, r, q, T, call/put, failure)
- Unit/notional multiplier ambiguity (1 vs 100, mixed premium/payoff/delta/P&L)

All five are repaired in v2 with prospective deterministic choices using repository-native sources only, no design invention beyond already-frozen harness assumptions.

## 3. Repaired training contract v2

Training contract v2 path: `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v2.md`
Training contract v2 canonical SHA-256: `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7`
Training contract v2 Git blob: `4a37528eb9d8f8f6ead0d2b471e3c16c99e33b5e`
Training contract v2 commit: `6f367c8` (`docs(research): repair v5 deep-hedging training contract`) — actual commit `6f367c8d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0` as recorded here (see verification Section 10)
Supersedes for future training authorization: `structured_vol_v5_deep_hedging_training_contract_v1.md`

### 3.1 CUDA-only scientific runtime (no CPU fallback)

- All scientific PyTorch model/tensor/source/RNG execution: `CUDA` (`cuda:0` via `torch.device("cuda")`).
- Scientific CPU fallback: `PROHIBITED` — `resolve_device("cuda")` fail-closes with `RuntimeError` if `torch.cuda.is_available()` is False or `torch.version.cuda is None`; no silent fallback to `cpu`.
- Expected runtime identity: Python `3.11.9`, torch `2.13.0+cu132`, CUDA runtime `13.2`, cuDNN `92000`, GPU `NVIDIA GeForce RTX 4070 Laptop GPU` 8GB, compute capability `8.9`, `runtime_identity_sha256` `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (`runtime-identity-v1` over canonical JSON sans hash, via `src/neuralmarket/core/runtime_identity.py`).
- Failure mode: if required CUDA/runtime identity is unavailable or mismatched, fail closed `BEFORE` scientific process (no synthetic generation, no GRU training, no checkpoint).

### 3.2 Correct standard GRU recurrence semantics

- Module: `torch.nn.GRU` with standard recurrence: reset `r_t=sigmoid(W_ir x_t + b_ir + W_hr h_{t-1}+b_hr)`, update `z_t=sigmoid(W_iz x_t + b_iz + W_hz h_{t-1}+b_hz)`, candidate `n_t=tanh(W_in x_t + b_in + r_t*(W_hn h_{t-1}+b_hn))`, hidden `h_t=(1-z_t)*n_t + z_t*h_{t-1}`. No custom SiLU recurrent gates; no extra recurrent activation choice. v1's SiLU gate statement corrected.

- Constructor: `nn.GRU(input_size=7, hidden_size=64, num_layers=2, dropout=0.0, batch_first=True)` followed by `nn.Linear(64,1)` (`torch.nn.GRU` / `torch.nn.Linear`).

- Hidden `64`, layers `2`, dropout `0.0`, normalization `none`, initial hidden zeros `[2,batch,64]`, readout linear `64->1` with no activation, action `delta_t` target hedge ratio per unit short option (multiplier 1), no bounds.

### 3.3 Synthetic price-path transformation (NSDE output → S_t)

- Generator output meaning: selected V5 NSDE checkpoint `StructuredVolatilityNeuralSde.forward` emits daily log-return increments `dx_t` shape `[batch, horizon]` (log-return per day), not latent state, not price level. `X_t` is cumulative log-return (`x0=0`, `X_t = cumsum dx`), `V_t` is internal latent log-volatility driving `sigma_x(V)` but not tradable.

- Selected checkpoint: `checkpoint.pt` (best_epoch) per five members (seed-01 5bdbaabd2fb257a7 etc.) is the simulation source.

- Initial state: `x0=0` cumulative log-return and `V0` from `v0_layer(context)` with zero context `context=torch.zeros(batch,4)` per `initial_state`.

- Inverse transform: none beyond `exp(cumsum)` (NSDE already operates on unnormalized log-returns per `structured_vol_sde.py`; no per-dimension z-score inverse on `S_t`).

- S0: `S_0 = 100.0` normalized initial reference level (prospectively frozen, development-only).

- Recurrence/path transform: `S_t = S_0 * exp(X_t)` where `X_t = cumsum_{i=0}^{t} dx_i` with `X_{-1}=0`, `X_t` for `t=0..62`, `S_0=100.0`, `horizon=63`, `dt=1/252` per XNYS session. Horizon 63 covers max maturity 30. No clipping or floor on `S_t`/`X_t` beyond `V` clamp `[-10,10]` already in NSDE. Positivity guarantee via `exp()`.

- Dtype: `float64` during cumsum/exp then cast to `float32` for hedger; device `cuda:0` (CUDA-only per Section 3.1) with deterministic `torch.Generator.manual_seed(synthetic_seed)` per generator.

- Calendar step: `dt=1/252` per XNYS trading session, horizon 63 sessions, `T=1/252` per step matches harness v3.

### 3.4 Synthetic option premium contract

- Premium `P0`: `INCLUDED` for synthetic training episode. For each synthetic episode (`S_0=100`, `K=S_0/m` where `m=S_0/K` is sampled moneyness `[0.90,1.10]`, `T_0 = T_epi/252.0` where `T_epi` is maturity 5-30 sessions, call/put type per 50/50), premium is Black-Scholes price using same benchmark machinery as harness v3 with fixed synthetic vol.

- Pricing rule: Black-Scholes with `r=0.0` (`r=0` continuously compounded) and `q=0.0` (continuous dividend, limitation stated, same as harness v3) and `vol = sigma_synth = 0.20` (20% fixed benchmark volatility, prospectively frozen, development-only). `sigma_synth=0.20` is deterministic synthetic premium volatility, not market IV.

- Volatility: `0.20` fixed.

- r: `0.0`, q: `0.0`, maturity `T_0 = T_epi/252.0`, calls/puts `C=S0*N(d1)-K*N(d2)` `P=K*N(-d2)-S0*N(-d1)` with `d1=(ln(S0/K)+0.5*sigma_synth^2*T0)/(sigma_synth*sqrt(T0))` `d2=d1 - sigma_synth*sqrt(T0)` at `T>0`, at `T=0` `C=max(S0-K,0)` `P=max(K-S0,0)` (same as harness v3).

- Failure: `P0` always finite for `sigma_synth=0.20` and `T0>0` within moneyness `[0.90,1.10]`; if nonfinite due to `K<=0`, episode `INVALID` and excluded.

- Synthetic data does not use chronological final-test prices and does not fetch external option data; `P0` reproducible entirely from synthetic episode state (`S0, K, T_epi, option_type, sigma_synth=0.20, r=0, q=0`).

- P&L consistency: synthetic hedging P&L uses same formula as evaluation `P&L = P0 + sum delta_{t-1}*(S_t - S_{t-1}) - Payoff_T - sum costs` where `Payoff_T` is intrinsic at synthetic `S_T` (`max(S_T-K,0)`/`max(K-S_T,0)`), costs are `c*|delta_t - delta_{t-1}|*S_t` including unwind Yes at synthetic `S_T`.

### 3.5 Unit/notional convention

- Unit: one option unit with multiplier `1` (not `100`). Premium `P0`, payoff `Payoff_T`, hedge position `delta_t` (shares per 1 unit spot notional), underlying P&L `delta_{t-1}*(S_t - S_{t-1})`, transaction cost `c*|delta_t - delta_{t-1}|*S_t` are all per `1` unit spot notional with multiplier `1`. Research normalization is one option unit with multiplier `1`, not one listed SPY contract with multiplier `100`. No mixed units; evaluation H3 convention is same (one unit, multiplier 1).

## 4. Preserved Task-197 training constants

All following remain exactly as frozen in v1 and are not opportunistically altered (preserved unless directly contradicted by Sections 3.1-3.5, which they are not):

- 7 input features and order `T_t_norm, moneyness, log_moneyness, log_return_from_inception, prev_delta, cost_norm, option_type` tensor `[batch, T_episode,7]` padded with mask, `float32` features, `float64` for S/K/T, ordering exactly f1..f7

- GRU hidden `64`, 2 layers, dropout `0`, linear readout `64->1`, raw target delta per unit short option (now corrected to standard GRU semantics per Section 3.2, otherwise preserved)

- Empirical CVaR 0.95 objective via harness v3 fractional-tail estimator (`alpha=0.95`)

- Separate policy per cost level, expected policies `45 =5×3×3` (`5` generators × `3` hedger seeds `31001,31002,31003` × `3` cost levels `0,0.0010,0.0050`)

- Five NSDE members seed-01/02/04/05/reserve-j01 with checkpoint SHAs as in v1 Section 3, WGAN NONE

- 50,000 synthetic episodes/member 40k/10k train-selection split maturity 5-30 moneyness 0.90-1.10 call/put 50/50, synthetic RNG schedule 42001/42002/42004/42005/42006 with torch.Generator.manual_seed + numpy PCG64, persisted as parquet per `<run_prefix>_<member>/synthetic_episodes_v1.parquet` with manifest

- Hedger seeds `31001,31002,31003`

- AdamW `lr 0.001` betas `0.9/0.999` weight decay `1e-6` batch `64` max epochs `200` grad clip `1.0` no scheduler early-stop patience `20` minimum epochs `20` checkpoint metric `validation_selection_cvar` (lowest CVaR), nonfinite epoch invalid, runtime CUDA/CPU deterministic flag, per-policy training reports

- 3/3 completeness per generator per cost (no denominator shrink from 3 to 2, if not 3/3 then generator/cost stratum `INVALID` and cost level primary `nan`), replacement `NONE` (no reserve hedger seeds), global failure `>20%` of 45 policies fail (10+ invalid) blocks H3

- Write-once artifact semantics per `(g,c,h)` at `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/checkpoint.pt` etc., no overwrite/retry/rerun, future authorization must bind contract SHA/blob plus 45 checkpoint identities

Preserved constants verified via byte comparison of v1 and v2 for those sections.

## 5. Commit record

- Training contract v2 committed alone at `6f367c8` (`docs(research): repair v5 deep-hedging training contract`) — actual commit `6f367c8d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0` as recorded here (see verification Section 6)

- This Amendment 101 commits separately at its own hash (see verification Section 6)

No amend, no rebase, no reset, no push.

This amendment is append-only, contains no self-referential hash.

## 6. Verification at repair

- Training contract v1 canonical `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` Git blob `2d8f5ad21f6af30d54f8897075a4e69734ffa56f` — preserved, not edited (recomputed, HEAD==worktree)

- Amendment 100 canonical `8605139d9c9d71c0815edd57692034944ba6e5ad704452d03203a0f04d998825` Git blob `50dccb37d64faf46f6a1be9f12b6be93ab348c42` — preserved

- Harness v3 canonical `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` Git blob `8d8220c084425c902825e754b0c24a3069e08f2b` — preserved

- SAP canonical `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` — preserved

- Split manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — metadata only, SEALED, 528 sessions

- H2 `H2_NOT_SUPPORTED` preserved

- Training contract v2 canonical `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` Git blob `4a37528eb9d8f8f6ead0d2b471e3c16c99e33b5e` — verified

- Amendment 101 canonical and Git blob as computed in verification Section 6 (see commit)

- Scientific CPU fallback: `0` (no fallback, CUDA-only fail-closed)

- GRU SiLU-gate misstatement: `0` (corrected to sigmoid/tanh)

- Unresolved generated-price mapping: `0` (S_t = S_0*exp(cumsum dx) with S_0=100 frozen)

- Unresolved synthetic premium: `0` (P0 Black-Scholes r=0 q=0 sigma_synth=0.20 frozen)

- Unit ambiguity: `0` (multiplier 1 frozen)

- Training: `0`, generator execution: `0`, policies `NOT AVAILABLE`, H2 `NOT_SUPPORTED`, final `SEALED` access `0` authorization `NOT GRANTED`

## 7. Final-test preservation

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

No final-test scientific rows were read. No hedging execution occurred. Training contract repair only.
