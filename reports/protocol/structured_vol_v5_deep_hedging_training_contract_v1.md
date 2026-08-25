# V5 Deep-Hedging Training Contract v1

Status: FROZEN_PENDING_INDEPENDENT_AUDIT
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-FREEZE-197`
Risk: `R4`
Date: 2026-08-25
Branch: `main`
Starting HEAD: `3045a26faa74f4a354c37b9f110ac523509903d8`
Safety branch: `safety/pre-v5-deep-hedging-contract-3045a26` at `3045a26faa74f4a354c37b9f110ac523509903d8`
Prerequisite: `NM-R4-V5-FINAL-TEST-SINGLE-ACCESS-HARNESS-CVAR-ESTIMATOR-AUDIT-196` — `VALIDATED`

This task freezes the deep-hedging training contract only. No training, no GRU model creation, no generator execution, no scientific synthetic-path generation, no inference, no bootstrap, no validation, no final-test row access, no external validation, no network, no push.

## 1. Authoritative bindings

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger named, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily hedge, H3 cost-aware hedging, H4 CVaR vs entropic, H5 synthetic pretraining extension, failure criteria)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (five-seed P0, H1/H2/H3 semantics, Strategy B finite level-3 RBF-MMD Euler/Ito, H3 requires synthetic-NSDE GRU vs BS family, H4/H5 secondary)
- H2 adjudication: `reports/protocol/research_protocol_amendment_095.md` at `fa28687` — `H2_NOT_SUPPORTED`
- SAP v1: `reports/protocol/structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at canonical `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` (H3 endpoint Delta_CVaR, 95% CVaR primary, 5% improvement, paired 95% CI, Holm {H3}, costs 0/10/50, turnover/position QC, seed vs market reporting)
- Harness v1: `structured_vol_v5_final_test_single_access_harness_v1.md` at `f12490e310b6d23.../b7c24126...` (REPAIR_REQUIRED, preserved)
- Amendment 097: `research_protocol_amendment_097.md` at `2b85791803b5.../dbfd2eff...` (preserved)
- Harness v2: `structured_vol_v5_final_test_single_access_harness_v2.md` at `7a28cb149e58.../676c5932...` (VALIDATED_EXCEPT_CVAR_PRECISION, preserved, with P&L, BS, CBB, 5×3 hierarchy)
- Amendment 098: `research_protocol_amendment_098.md` at `487a666f1093.../40666ace...` (preserved)
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at canonical `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` blob `8d8220c084425c902825e754b0c24a3069e08f2b` — VALIDATED (CVaR estimator fractional-tail 5% via k=floor(0.05 N) f=tail-k, B_valid==10000, percentile CI method linear, p-value inclusive)
- Amendment 099: `research_protocol_amendment_099.md` at `983da31d51b2.../852718e5...` (preserved)
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (final test 2023-11-22 through 2025-12-31, 528 XNYS, sealed, metadata only)
- NSDE family: `reports/research/structured_vol_v5_n5_family_analysis_v1.json` with five valid members (seed-01, seed-02, seed-04, seed-05, reserve-j01) all GATE_PASS_VALID
- NSDE configs: `configs/research/structured_vol_neural_sde_v5.yaml` at `f9ca3e9b...` (state_dim 2, brownian_dim 2, hidden 2×64 SiLU, dt=1/252 horizon 63, AdamW lr 0.001)
- Current canonical training/runner conventions: `src/neuralmarket/core/reproducibility.py`, `src/neuralmarket/core/device.py`, `docs/engineering/agent-contract.md`
- AGENTS.md and agent-contract govern R4 workflow

Final-test state: `SEALED`, access `0`, entitlement `NONE`, authorization `NOT GRANTED`, harness v3 `VALIDATED`, deep-hedging training contract prior `NOT FROZEN`, policy identities `NOT YET AVAILABLE`.

## 2. Requirement matrix

| Requirement | Source status before 197 | Freeze in this contract | Rationale |
|---|---|---|---|
| GRU deep hedger named | SOURCE_FROZEN (v1 Core scope: GRU deep hedger) | preserved | v1 normative |
| SPY European calls/puts 5-30 moneyness 0.90-1.10 daily | SOURCE_FROZEN | preserved | v1 Core scope, SAP, harness |
| 95% CVaR primary / entropic secondary | SOURCE_FROZEN | preserved (evaluation), training objective prospectively chosen as CVaR 0.95 | v1 Primary endpoint |
| Proportional costs `c*|delta_t-delta_{t-1}|*S_t` incl. unwind | SOURCE_FROZEN for harness; training cost formula prospectively frozen consistently | `C0 0, C1 0.0010, C2 0.0050` with unwind Yes (v2 Section 5) | harness v3, v1 line 39 |
| Cost-policy per-cost vs cost-conditioned design | PROSPECTIVE_CHOICE_REQUIRED (harness v2/v3 expects 5×3×3 but leaves for training contract) | separate policy per cost level (45 total) | see Section 5.2 |
| GRU input features, tensor order, dim | PROSPECTIVE_CHOICE_REQUIRED (no source pins features) | frozen Section 4.1 | pre-final methodology |
| GRU layers/hidden/dropout/readout/action | PROSPECTIVE_CHOICE_REQUIRED | frozen Section 4.2 | pre-final methodology |
| Training objective (CVaR vs entropic vs other) | PROSPECTIVE_CHOICE_REQUIRED (SAP says H3 evaluation CVaR, training objective separately frozen) | empirical 95% CVaR via fractional-tail estimator (harness v3 Section 4B) | Section 5.1 |
| Synthetic paths: count/horizon/dt/context/option sampling/call-put/moneyness/split/RNG/persistence | PROSPECTIVE_CHOICE_REQUIRED | frozen Section 6 | pre-final methodology |
| Optimizer/lr/betas/weight decay/batch/epochs/clip/scheduler/early-stop/checkpoint metric | PROSPECTIVE_CHOICE_REQUIRED | frozen Section 7 | canonical conventions |
| Hedger seeds 31001-31003 | SOURCE_FROZEN (harness v3 Section 7.3) | preserved 31001,31002,31003 | harness v3 |
| Policy completeness 3/3 per generator/cost, replacement semantics | PROSPECTIVE_CHOICE_REQUIRED | frozen Section 7.4 as 3/3 required, replacement NONE | Task-195 audit requirement |
| Runtime/device, artifact path, SHA conventions | IMPLEMENTATION_ONLY (canonical conventions exist) | frozen Section 7.5/8 | repo canonical |
| WGAN, H2 thresholds, Gate | NOT_APPLICABLE (WGAN NONE, H2 preserved, Gate for NSDE only) | preserved WGAN NONE, H2_NOT_SUPPORTED | v1, Amendment 095 |

## 3. H3 generator family and checkpoint binding (SOURCE_FROZEN)

- H3 generator family: `signature-score NSDE ONLY`. Conditional neural SDE trained with non-adversarial signature-kernel score, frozen as finite level-3 lead-lag signature + RBF-MMD with log-variance penalty, Euler/Ito `dt=1/252`, horizon `63`, Brownian `2`, state `2`. Per Amendment 020 Strategy B, SAP, harness v1-3.
- WGAN role: `NONE` in H3 synthetic training paths and hedger training.

Bound five valid NSDE members exactly (audited selected checkpoint identities, all `GATE_PASS_VALID` per `structured_vol_v5_n5_family_analysis_v1.json`):

| Member | Canonical ID | Run prefix | Selected checkpoint SHA-256 | Selected Git blob | Final checkpoint SHA-256 | Final Git blob |
|---|---|---|---|---|---|---|
| seed-01 | v5-seed-01 | `5bdbaabd2fb257a7` | `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f` | `6820d07c0fb253a02337190d7c8683b5c01cb3f3` | `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4` | `6d0ead19a92c9c93422ab2b9c38b3d4bbbc5d7c` |
| seed-02 | v5-seed-02 | `62c7406cb3a2c642` | `9e6f8cd030d073d59324514d5a1ef6e87be6e3dbfb16b8cec7aa13928fd84f7a` | `592df5d33f9342901a1c9e4b9cae4c52f29c6a1c` | `b867af03b7a00dce6f4b34bcaf31896ddb891c9ba18e722dd2abb02ddf18ac8a` | `feef0df2fc721db3e1aea4ca80ea1b985e436` |
| seed-04 | v5-seed-04 | `77e7de9efabb7ce3` | `87d022152ba28f881f454a76aee1b572061e288fd3eee31b1ca52f2ba88cc35` | `3701888ef57f20132c77633f6aca2d6e6e3861` | `4927e6b6b575e20a20fc5ee225ac3400ad7e9524871b155d0cdfbf8ec9d4c72` | `c029db1e272117d73b6d596c2d4933aaf90bb` |
| seed-05 | v5-seed-05 | `1e8aa171993a1aba` | `3a71b12e1c0af08ea2c254fa6e162a09dd32dd47b399d6dc7585b264e33abef` | `808db090fe34f15b22d8062866846cde4d829` | `4d3b9475fbc9adba09b20822bd5941e367b4dc5b278f1ffb8d5954276a0a9c99` | `de846f5c671f492e4d909c99e7a534a1faeba` |
| reserve-j01 | reserve-j01 | `38c5113b27568e14` | `50d14095d95386c0fb7e1ee5ab43175272f02bfa84fbec3ddc6c8fe2a97326` | `38c9f8a0c8f97c64ce82e2ad38a0fea754a6a9` | `a4713691abb886a8151a6efa98dc2163068e147d1ea98d11d2c9a28b0e9b219` | `19620280adef3ae6224300e18d9d63496d334` |

Primary checkpoint for synthetic generation training is the selected `checkpoint.pt` (`best_epoch` per member); final checkpoint pinned for audit not used as hedging input.

## 4. Hedger input state, output, and model architecture

### 4.1 Input state (frozen prospectively)

No source pins exact hedger input features beyond SPY European option with maturity/moneyness/daily hedge. This contract freezes one deterministic feature set before hedger training, using development-only constraints, not final-test data.

Episode-level instrument state per hedging step `t` (at close `S_t`):

- `S_t` underlying close (SPY) — source for moneyness, returns — available at same close before choosing `delta_t`, no lookahead beyond `S_t`.
- `K` strike (fixed per episode, from inception sampling).
- `T_t` remaining XNYS trading sessions to expiration exclusive /252.0 (harness v3 Section 6, `T_t = (expiration_index - current_index)/252`).
- Option type: `call` or `put` (given per episode).
- Current cost level `c` in `{0.0,0.0010,0.0050}`.
- Previous hedge position `delta_{t-1}` (with `delta_{-1}=0` before inception, per harness v2 Section 5.2).

Derived per-step input features (7-dimensional, exact tensor ordering):

1. `f1 = T_t_norm = T_t / (30/252) = T_t * 252/30 = remaining_sessions /30` in `[0,1]` (time to expiry normalized to max maturity 30).
2. `f2 = moneyness = S_t / K` (spot moneyness at `t`, includes underlying moves).
3. `f3 = log_moneyness = ln(S_t / K)` (log transform of moneyness).
4. `f4 = log_return_from_inception = ln(S_t / S_0)` where `S_0` is inception close (cumulative underlying move).
5. `f5 = prev_delta = delta_{t-1}` (current hedge position before rebalancing).
6. `f6 = cost_norm = c /0.0050` in `{0.0,0.2,1.0}` for `c=0,0.0010,0.0050` respectively (cost level normalized to max 50 bps).
7. `f7 = option_type = +1` for `call`, `-1` for `put`.

No speculative features are added (no additional volatility/history state beyond what is above; no generator conditioning/context beyond synthetic path's spot dynamics; no separate dividend or rate feature because harness v3 freezes `r=0,q=0`).

Tensor ordering and dimensions:

- Input sequence per episode: shape `[T_episode, 7]` where `T_episode` is maturity length in trading days (5-30) for that episode's synthetic hedging simulation.
- Batching: shape `[batch, T_episode, 7]` with variable `T_episode` per batch element; batches are padded to `max_T_in_batch` with mask for loss computation (padded steps do not contribute to P&L).
- Dtype: `float32` for features, `float64` for S/K/T double precision before feature computation.
- Ordering is exactly as listed f1..f7; any implementation must follow this order to be byte-reproducible.

Input normalization: none beyond the explicit normalizations above (`T_t_norm`, `cost_norm`, log transforms). Features are used as raw float32 values above. No learned standardizer is applied to hedger inputs (unlike NSDE bandwidth).

### 4.2 Model architecture (frozen prospectively)

- Model family: `GRU` deep hedger (per v1 Core scope Primary hedging comparison: GRU deep hedger).

Exact architecture (single choice, no alternative):

- Architecture: `GRU` with `num_layers = 2` stacked GRU layers.

- Hidden dimension: `hidden_size = 64` per layer.

- Dropout: `0.0` between GRU layers (no dropout).

- Normalization: `none` (no LayerNorm, no BatchNorm on GRU).

- Initial hidden state: zeros (`h_0 = 0` for both layers, shape `[num_layers, batch, hidden_size]`).

- Readout layer: single linear layer `nn.Linear(64, 1)` from last-layer GRU output at each time step to scalar.

- Activation on readout: `none` (linear output); no tanh/sigmoid scaling.

- Output/action interpretation: `delta_t` target hedge ratio per unit short option (shares of SPY per 1 unit option notional). Raw linear output is `delta_t` exactly. No output clipping or squashing before thresholding; raw output may be any finite `float32`; pathological thresholding (`|delta|>2.0`) is applied only at evaluation/reporting, not at training forward.

- Action bounds/transformation: `NONE` — no bounds, no sigmoid, no `tanh *2`, no strike scaling. Hedge ratio is directly the linear readout value.

- Parameter count: deterministic from above (GRU 2×64 input 7).

No alternative architecture remains (e.g., no LSTM, no Transformer, no hidden 32/128 variant, no dropout variant, no LayerNorm variant, no MLP hedger).

## 5. Training objective, cost-level policy semantics, and loss

### 5.1 Training objective

H3 final evaluation uses `95% CVaR` per v1 and harness v3, but training objective is separately frozen here as required.

Frozen training objective: `empirical 95% CVaR` of hedging loss `L = -P&L` where `P&L` is per Section 5 hedging P&L and `CVaR_0.95` is the exact fractional-tail empirical Expected Shortfall estimator frozen in harness v3 Section 4B (alpha=0.95, tail_mass=0.05*N, k=floor, f fractional, mean of k largest with fractional boundary). No other objective.

Specifically, for each training batch of synthetic hedging episodes (N_episodes per batch, after filtering valid synthetic episodes under missingness rules), compute hedging loss vector `L` per episode via the frozen P&L formula (Section 5 hedging P&L with premium Included, cash r=0, unwind Yes, costs c*|delta_t - delta_{t-1}|*S_t). Then compute `CVaR_0.95(L)` via the harness v3 Section 4B fractional-tail estimator and minimize that scalar loss via backpropagation through the GRU unrolled hedging simulation (including transaction-cost and payoff terms as differentiable where applicable, with payoff and underlying moves as constants with respect to delta).

No `mean-plus-CVaR`, no `entropic risk`, no alternative pre-existing cost-aware objective is used for training. Entropic risk remains secondary report-only per v1, not training objective.

- Alpha/risk: `alpha = 0.95` (same as evaluation `CVaR_0.95`).

- Transaction costs: bound consistently with harness `cost_t = c * |delta_t - delta_{t-1}| * S_t` with `delta_{-1}=0`, including initial trade `c*|delta_0|*S_0` and terminal unwind `c*|0 - delta_T|*S_T` at `S_T`, `S_t` is synthetic underlying close at `t` (from NSDE-generated path). Same cost levels `0, 0.0010, 0.0050` as harness.

- Terminal unwind: YES (`EXPLICITLY REQUIRED`) — liquidate `delta_T` to `0` at `S_T` charging unwind cost, final position `0`, per harness v3 Section 5.2. Training simulation covers full expiry including final underlying move `delta_{T-1}*(S_T - S_{T-1})` then unwind and payoff.

- No comparator influence: training uses only synthetic paths from NSDE generators and the hedger's own hedging P&L; Black-Scholes comparator is not used at training time (evaluation comparison only).

### 5.2 Cost-policy semantics

Choose exactly ONE repository-supported design:

- `separate policy per cost level` — each cost level has its own GRU hedger model (no weight sharing across costs). This is the `repository-supported` design that matches the analysis hierarchy currently expects per Task-197 Section 5: `5 NSDE generators ×3 hedger seeds ×3 cost levels` and is the minimal change that gives cost-specific hedge ratios under different proportional costs.

No ambiguity may remain. The alternative `single cost-conditioned policy` (one GRU with cost as input feature f6 that spans all cost levels) is NOT selected.

- Expected trained policy count: `45` = `5` generator members × `3` hedger seeds (`31001,31002,31003`) × `3` cost levels (`0, 0.0010, 0.0050`). This is the number of independently trained GRU hedger policies that must exist before final-test authorization.

- If a generator member or cost level combination is invalid (fails), that specific `(g, h, c)` policy is missing; the primary H3 analysis expects separate policy per cost, so the analysis hierarchy `mean_h` per generator at each cost level is computed only when that cost level's 3 hedger seeds are all valid (see Section 7.4 completeness rule).

## 6. Synthetic training data and generator binding

### 6.1 Generator binding

- Generator family: `signature-score NSDE ONLY`, `WGAN NONE` (Section 3 above, same five members).

- Synthetic-path generation contract: for each generator member `g` in `{seed-01,seed-02,seed-04,seed-05,reserve-j01}`, generate a synthetic training dataset of `50,000` option hedging episodes (synthetic episodes) from that generator member's `selected checkpoint.pt` (best_epoch) simulation. This count is a prospective choice using development-only constraints (no final data; synthetic budget 50k balances coverage of 5-30 moneyness/maturity grid with compute comparable to NSDE training) and is not data-dependent.

- Horizon: `63` (maximum XNYS horizon per NSDE config `configs/research/structured_vol_neural_sde_v5.yaml` horizon 63).

- Time step: `dt = 1/252` (Euler/Ito simulation step, same as NSDE training).

- Context/lookback: NSDE simulation uses no additional conditioning context beyond its internal state (state_dim 2, Brownian 2, no extra context sequence beyond the NSDE's own initial state per `structured_vol_neural_sde_v5.yaml` sde config); synthetic paths are generated unconditionally from `x0=0` and `z0` from context-conditioned linear layer with zero context (or fixed zero), seeded per generator RNG schedule below. No lookback beyond NSDE's own simulation.

- Horizon vs maturity: synthetic price path length `63` covers maximum option maturity `30` plus additional path beyond expiry for simulation alignment; hedging episodes of maturity `T_epi` in `[5,30]` are evaluated on the first `T_epi` steps of the synthetic price path (spot series `S_t`).

### 6.2 Option inception construction for synthetic episodes

For each synthetic path (one price series of length `63` closes `S_0..S_62`), construct `one` synthetic option hedging episode with:

- Maturity sampling: `T_epi` uniform discrete integer in `[5,30]` inclusive (uniform `1/(30-5+1)` per value), trading sessions.

- Moneyness distribution: `m = S_0 / K` uniform continuous in `[0.90,1.10]` inclusive.

- Strike: `K = S_0 / m` where `S_0` is synthetic underlying close at inception (initial spot of the synthetic path, normalized; strike computed in same price scale).

- Call/put balance: `50%` calls (`option_type=+1`), `50%` puts (`option_type=-1`) independent Bernoulli `p=0.5` per episode, balanced across the 50k episodes.

- Moneyness/strike relation preserves call/put distribution within `0.90-1.10` band.

- Cost-level binding: each synthetic episode is replicated across the three cost levels for separate-policy training (i.e., the same synthetic spot path and option definition is hedged three times with different `c` values, but training loss is computed per cost-specific policy on its cost-specific hedging P&L). Training data generation does not bind `c` itself; `c` is the training cost input for the policy being trained.

- Train/selection split: `80%` train (`40,000` episodes) and `20%` selection (`10,000` episodes) per generator member, random split seeded by synthetic generation RNG (see below), stratified to preserve maturity/call-put balance if feasible but not required for determinism.

- Split for training vs validation selection: synthetic selection set is used for early stopping / checkpoint selection (validation CVaR on synthetic), not for final-test evaluation.

- Generation persistence: paths are generated once per generator member under the synthetic RNG schedule below and persisted deterministically as parquet at `data/processed/research/hedging_synthetic/<run_prefix>/synthetic_episodes_v1.parquet` (one file per generator member, containing columns `episode_id`, `T_epi`, `K`, `option_type`, `S_series` (array length `T_epi+1`), `S_0`). If file exists with matching synthetic RNG and generator checkpoint SHA, it is not regenerated; otherwise it is deterministically regenerated from the generator checkpoint with the frozen RNG seeds. No final-test rows are accessed at generation.

### 6.3 Generator RNG schedule

Distinct from NSDE model seeds (`8281` series, `9281`, etc.), Gate seeds (`7777`/`7778`/`8801`), evaluation seed `8283`, and hedger initialization seeds (`31001-31003`).

- For seed-01 (`5bdbaabd2fb257a7`): synthetic generation base seed `42001`
- For seed-02 (`62c7406cb3a2c642`): `42002`
- For seed-04 (`77e7de9efabb7ce3`): `42004`
- For seed-05 (`1e8aa171993a1aba`): `42005`
- For reserve-j01 (`38c5113b27568e14`): `42006`

Each synthetic dataset generation uses `torch.Generator.manual_seed(synthetic_seed)` and `numpy` PCG64 with same seed for price path simulation and option sampling (path noise and option parameter sampling both seeded). These are distinct per generator member and distinct from hedger seeds. Recorded in training report.

### 6.4 Synthetic-artifact identity convention

- Synthetic dataset per generator member: path `data/processed/research/hedging_synthetic/<run_prefix>_{member}/synthetic_episodes_v1.parquet` (run_prefix as in Section 3 table) with accompanying `synthetic_manifest_v1.json` containing `generator_member`, `run_prefix`, `checkpoint_selected_sha256`, `synthetic_seed`, `num_episodes (50000)`, `horizon (63)`, `dt (1/252)`, `option_sampling` (maturity/moneyness/call-put distributions), `train_selection_split (0.80/0.20)`, `cost_levels ([0,0.0010,0.0050])`, `parquet_sha256`.

- Training per-policy artifact: each `(g, h, c)` policy training writes to `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/` with `checkpoint.pt` (best), `checkpoint_final.pt`, `training_curve.json`, `training_report.json`.

## 7. Optimization, checkpoint selection, and policy completeness

### 7.1 Hedger seeds

Exact hedger seeds (integer seeds for GRU weight init, optimizer state, and training shuffle, distinct from all other RNGs):

- `31001`
- `31002`
- `31003`

These are the three preregistered hedger seeds from harness v3 Section 7.3. No other hedger seeds are used for primary H3.

### 7.2 Optimization

- Optimizer: `AdamW` (same canonical optimizer as NSDE per `configs/research/structured_vol_neural_sde_v5.yaml` training conventions).

- Learning rate: `0.001` (`1e-3`) initial.

- Optimizer betas/momentum: `beta1=0.9`, `beta2=0.999` (AdamW defaults).

- Weight decay: `1e-6` (`1.0e-6`) same as NSDE.

- Batch size: `64` episodes per batch.

- Maximum epochs: `200` (fewer than NSDE `400` because GRU hedging on synthetic paths converges faster; prospective choice, development-only).

- Gradient clipping: `grad_norm_clip = 1.0` (clip global norm to 1.0 if exceeds).

- Scheduler: `none` (constant learning rate `0.001`, no scheduler, no warmup, no decay).

- Early-stopping metric: `CVaR_0.95(L)` on the synthetic selection set (`10,000` episodes) computed via the exact fractional-tail estimator (harness v3 Section 4B) on the hedger's current checkpoint's hedging losses (with same P&L, costs including unwind, per selected cost level). Metric is `validation_selection_cvar`.

- Early-stopping patience: `20` epochs (no improvement in `validation_selection_cvar` for 20 epochs).

- Minimum epochs: `20` (must train at least 20 epochs before early stopping can trigger).

- Checkpoint-selection metric: `validation_selection_cvar` (lowest CVaR on selection set across training). Best checkpoint is `best_epoch` where `validation_selection_cvar` is minimal (smaller CVaR is better). Same metric as early stopping.

- Nonfinite failure behavior: if training loss or validation loss becomes nonfinite (`nan`/`inf`) at any epoch, that epoch is counted as invalid, training continues if possible but checkpoint for that epoch is not selected; if all epochs are nonfinite or no valid checkpoint exists, the policy's training report records `GATE_FAIL_NONFINITE_TRAINING_FAILURE` (analogous to WGAN training failure) and no valid `checkpoint.pt` is produced for that `(g,h,c)`; the policy is then `INVALID`.

- Runtime/device contract: training runs on `CUDA` if `torch.cuda.is_available()` else `CPU`; GPU paths use deterministic flags per `src/neuralmarket/core/reproducibility.py` (`deterministic=true`, `warn_on_nondeterminism=true`, seed `1337` package-level not hedger training). Mixed `CPU`/`CUDA` across members is allowed and labelled per run (as in NSDE family CPU for seed-01/02/04 and CUDA for seed-05/reserve-j01), but each policy training records `runtime` (`CPU` or `CUDA`) in its training report.

### 7.3 Policy completeness

For a generator member `g` to enter primary H3 at a given cost level `c`:

- `ALL THREE` preregistered hedger seeds must have valid selected checkpoints: `valid hedger count per generator per required cost level = 3/3`.

- No primary `mean_h` denominator may silently shrink from `3` to `2`. If a generator/cost stratum has only 2 valid hedger policies, that generator member at that cost level is `INVALID` for confirmatory H3; its `Delta_g` at that cost level is `nan` and the cost level's primary `Delta_primary = mean_g Delta_g` will be `nan` if any generator member is invalid (since primary is mean over 5 finite generator means). Therefore a single failed hedger policy blocks that generator/cost primary contribution, and because primary requires all 5 generators finite, a single failed policy with no replacement would block the entire cost level's confirmatory primary.

- Require: `valid hedger count per generator per required cost level: 3/3` or that generator/cost stratum is invalid for confirmatory H3.

- Do NOT use mean-over-finite to silently rescue a failed primary policy (i.e., no 2/3 rescue).

### 7.4 Replacement semantics

- Automatic replacement seeds: `NONE`.

- A failed preregistered policy remains a failed policy and blocks that generator/cost primary contribution.

- If replacement is scientifically permitted by existing governance (currently no governance permits replacement for hedging), the replacement would require exact ordered reserve seeds frozen now — but none are frozen here because `replacement: NONE` is the prospectively frozen choice per Task-194 repair instruction preferred unless existing source says otherwise (no source says otherwise).

- Therefore no reserve hedger seeds are defined for hedging; the three preregistered seeds `31001-31003` are the only valid hedger seeds for confirmatory H3.

### 7.5 Global failure criterion

- Member-level validity: per generator per cost level requires `3/3` valid as above.

- Cost-level primary validity: requires all `5` generator members valid at that cost level (each with `3/3`). If any generator member invalid at that cost level, the cost level's `Delta_primary` is invalid.

- Global failure criterion: separate from member-level validity: if more than `20%` of expected `45` policies fail (i.e., `10` or more of the 45 `(g,h,c)` policies are invalid/nonfinite/no valid checkpoint), then overall H3 confirmatory claim is blocked regardless of per-level success (analogous to NSDE training failure accounting). This global criterion is frozen here prospectively.

- Confirmatory implication: any cost level with at least one generator member invalid (i.e., not `3/3` per member or not all 5 members valid) cannot have primary H3 claimed at that cost level; since H3 success requires both nonzero cost levels (`10` and `50` bps) to succeed per harness, a single generator/cost invalid will block H3 at that cost and therefore block overall H3.

## 8. Artifact contract

### 8.1 Policy path, checkpoint identity, report, config, runtime identity

- Policy path convention per `(g,c,h)` (generator member `g`, cost `c`, hedger seed `h`):

  `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/checkpoint.pt` (best, selected by lowest `validation_selection_cvar`),

  `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/checkpoint_final.pt` (final epoch),

  `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/training_curve.json` (per-epoch train/validation CVaR and loss),

  `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/training_report.json` (metadata, SHAs, runtime, epochs, seeds, metrics).

  Where `<bps>` is `0`, `10`, `50` for `c=0,0.0010,0.0050` respectively, and `<run_prefix>_<member>` is as in Section 3 table (`5bdbaabd2fb257a7_seed-01`, etc.).

- Checkpoint SHA convention: SHA-256 of `checkpoint.pt` bytes (as for NSDE), Git blob via `git hash-object`, recorded in `training_report.json`.

- Report path: `training_report.json` contains `schema_version` (`hedging-gru-training-report-v1`), `member_id` (`seed-01` etc.), `cost_bps` (`0`/`10`/`50`), `hedger_seed` (`31001` etc.), `synthetic_seed` (per generator 42001-42006), `synthetic_manifest_sha256`, `optimizer` (`AdamW lr 0.001 betas 0.9/0.999 wd 1e-6`), `batch_size` (`64`), `max_epochs` (`200`), `early_stopping` (`patience 20 min_epochs 20 metric validation_selection_cvar`), `best_epoch`, `best_validation_cvar`, `runtime` (`CPU`/`CUDA`), `git_head`, `checkpoint_sha256`, `checkpoint_git_blob`, `training_curve_sha256`.

- Config identity: this contract path `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v1.md` with its canonical SHA and Git blob, plus the training hyper-parameters above frozen in the same file, constitute the config identity for all 45 trainings.

- Runtime identity: per-policy `training_report.json` records `runtime` and `device` (`torch.cuda.is_available()` and `cuda:0` vs `cpu`), and `deterministic` flag from `src/neuralmarket/core/reproducibility.py`.

- Overwrite semantics: `checkpoint.pt` and `training_report.json` are `write-once` per `(g,c,h)` — if the path already exists, no overwrite; training for that identity is not rerun. No `checkpoint` overwrite to improve CVaR after seeing final-test.

- Retry semantics: `NONE` — a failed training (nonfinite/no valid checkpoint) for `(g,h,c)` is not automatically retried with same or different seed; failed remains failed.

- Rerun semantics: `NONE` — no automatic rerun on nonfinite CVaR or missingness; no relaunch with different cost level to obtain significance.

### 8.2 Future authorization prohibition

- This contract does not authorize further training, generation, inference, or final-test access beyond the 45 expected policies.

- Future authorization (granting final-test H3 evaluation) must bind this training contract's canonical SHA and Git blob plus the 45 policy checkpoint identities (each `checkpoint.pt` SHA/blob) as actually produced; if any of the 45 expected policies is invalid (`not 3/3` per member or not all 5 members valid at a required cost level), final-test authorization is impossible until governance addresses the failure (not by silent denominator shrink).

- No training report may be overwritten to rescue a failed primary policy.

## 9. Task and band

- Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-FREEZE-197` — `R4` — `FREEZE_ONLY`.

- No training, no GRU model creation, no generator execution, no scientific synthetic-path generation, no inference, no bootstrap, no validation, no final-test row access, no external, no network, no push.

- This contract plus Amendment 100 are `R4` protocol artifacts; they satisfy deep-hedging training-contract prerequisite pending independent audit. Synthetic generation, inference, validation, bootstrap, and final-test scientific execution remain `0` at this freeze.

## 10. Verification at freeze

- SAP canonical `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` Git blob `8ffe6d96c758f29471db3b97b9ae07a181427db9` — verified (recomputed, HEAD==worktree).
- Harness v3 canonical `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` Git blob `8d8220c084425c902825e754b0c24a3069e08f2b` — verified, preserved.
- Amendment 099 canonical `983da31d51b203c9dfc939e4f6742448b259ae7ae71d01861da657a924b099d0` Git blob `852718e5ca9149d5fda60e25de1b33c523b7c2fa` — verified.
- Split manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — metadata only, SEALED, 528 sessions, 2023-11-22 through 2025-12-31.
- H2 `H2_NOT_SUPPORTED` preserved.
- NSDE checkpoint identities recomputed and matches Section 3 (5 members, all GATE_PASS_VALID).
- Final test `SEALED` access `0` entitlement `NONE` authorization `NOT GRANTED`.
- Deep-hedging training contract: `FROZEN_PENDING_INDEPENDENT_AUDIT` via this contract (not `NOT FROZEN`).
- Policy identities `NOT YET AVAILABLE` correctly recorded (no policies trained yet).
- Training: `0` (no GRU training execution), generator execution `0` (no synthetic-path generation execution), inference `0`, bootstrap `0`, validation `0`, external `0`, final access `0`, network `0`, push `0`.

## 11. What this contract does not do

- Does not train any hedger (no GRU training execution).
- Does not generate synthetic paths (no generator execution).
- Does not authorize final-test H3 evaluation or single-access process creation.
- Does not create policy checkpoints, reports, or synthetic datasets.
- Does not claim deep hedging is ready for execution beyond contract freeze (deep hedging remains `NOT READY FOR EXECUTION PENDING AUDIT`).
- Does not change SAP, harness v1/v2/v3, H2_NOT_SUPPORTED, or single-access state machine.

*This contract is append-only. Any change requires new governed amendment, not silent edit. Next governed action is the independent audit task NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-AUDIT-198.*
