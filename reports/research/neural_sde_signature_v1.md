# Signature Neural-SDE v1 — Frozen Experiment Record

Status: **BLOCKED (degenerate generator)** — see "Outcome" below.
Date: 2026-08-17. Repository HEAD (start): `745d342118249d9908a98db1189e50bbd3bd27ba`.
Safety branch: `safety/pre-signature-neural-sde-745d342` (points exactly at starting HEAD).

## Protocol trace (neural-SDE / signature objective)

`reports/protocol/research_protocol_v1.md` defines the research question only:

- primary generator comparison includes a **signature-score neural SDE**
  (line 8 and line 24);
- the required classical baselines are IID bootstrap, stationary/block
  bootstrap, GBM, GJR-GARCH or EGARCH, Heston (lines 26–31);
- governance rules: chronological splits, purging/embargo, normalizers fitted
  on training only, no hyperparameter selection on the final test, five-seed
  comparisons, failed seeds reported (lines 87–105);
- failure criteria: a run is predeclared **failed** if generated terminal-return
  dispersion collapses below 10% of the corresponding real-data dispersion
  (lines 107–120).

Amendments 001–012 govern acquisition/ops only and impose no architecture,
state dimension, conditioning variables, network layout, integrator,
signature level, signature kernel, optimizer, or schedule. The protocol is
therefore **underspecified** for the network design; the milestone's **frozen
fallback design** was used, and the fallback was frozen before any
external-validation observation.

## Frozen bindings (all verified before training)

- research inventory hash `371c1483…6d119` (embedded in
  `data/manifests/research_development_inventory_v1.json`);
- empirical benchmark hash `2b0dd31e…593d` (embedded in
  `data/processed/research/benchmark/empirical_benchmark_v1.json`);
- metric-spec hash `5e43a3a3…00eb3` (`research-metric-spec-v1`);
- baseline-suite hash `445b1257…f0099`
  (`data/processed/research/benchmark/simulator_baseline_suite_v1.json`);
- training series SHA-256 `4863b2cc…68669c` (925 returns, 2018-05-02 … 2021-12-31)
  bound independently from the benchmark underlying block and the suite;
- validation series SHA-256 `ec49994b…47edc8` (274 returns,
  2022-05-26 … 2023-06-30) bound independently the same way;
- inherited provenance limitation recorded, not repaired: the accepted
  empirical benchmark embeds a historical inventory hash
  (`5603459c…31ff`) that differs from the current frozen inventory hash
  because `source_head` changed when the inventory was rebuilt.

Protected artifacts were not mutated (SHA-256 of each file verified before and
after all runs).

## Environment

- Offline. No provider client, no `.env` load, no credentials, no billing,
  no final-test reads. `provider calls = 0`, `final-test accesses = 0`.
- torch `2.13.0+cpu` (the pre-installed PyTorch; PyTorch remains an undeclared
  dependency per `pyproject.toml` mypy-override comment — "intentionally
  deferred"). `torch.cuda.is_available() = False`; device `cpu`,
  dtype `float32`. No mixed precision.
- Windows DLL-order fix shipped with this milestone: pyarrow bundles its own
  `msvcp140.dll` which made torch's `c10.dll` fail to initialize
  (WinError 1114) when pandas/pyarrow imported first. The package
  `__init__.py` (and `tests/conftest.py`) now preload the SYSTEM runtime at
  import time so torch loads reliably in any import order.
- Determinism: `torch.use_deterministic_algorithms(True)`,
  `cudnn.benchmark = False`; seeds: model-init `4242`, data/noise `4243`,
  evaluation `4244`. Deterministic replay proven by a byte-identical
  re-run (identical checkpoint SHA, artifact hash, and all identity content).
- no torchsde / signatory / signature / esig package was installed → the
  milestone's minimal **truncated-signature feature map** was implemented
  from scratch with tensor ops and Chen's identity (labelled accurately as a
  finite-level signature-kernel approximation).

## Frozen fallback design (used)

- Target process: daily SPY cumulative log return.
- State dim 2: `x` observable cumulative log return, `z` latent state.
  Brownian dim 2. Context: 4 past-only features (previous daily return,
  previous 5-day cumulative return, previous 22-day cumulative return,
  previous 22-day realized volatility) over a 22-trading-day lookback.
  Normalization fitted from training windows only; no future target return
  enters its context; no validation data enters normalization.
- Neural drift and diagonal diffusion: MLP over (normalized time, state,
  normalized context), 2 hidden layers × 64 SiLU units; diffusion
  `softplus(raw) + 1e-6`. `x_0 = 0`; `z_0` from a small
  context-conditioned linear layer. No attention/transformers/RNNs.
- Integrator: Euler-Maruyama, `dt = 1/252`, 63 steps → exactly 63 daily
  returns per path; fails closed on non-finite state.
- Signature level 3; basepoint- and time-augmented path; normalized-time
  channel in `[0,1]`; cumulative-return channel scaled by a training-derived
  scale (`std_train * sqrt(63) = 0.102848…`); context made visible by
  prepending an origin then a context point at time 0, with the context
  constant through the path.
- Objective: truncated-signature MMD (expected signature matching) — per level
  1..3, mean-squared difference of mean signature features over real vs
  generated batches, summed with equal weights. Primary distributional loss
  only; numerical regularization limited to AdamW weight decay `1e-6` and
  gradient-norm clip `1.0`. No direct stylized-fact optimization, no
  adversarial/GAN objective, no deep hedging.
- Optimizer AdamW lr `1e-3`, batch 64, max 400 epochs, patience 40.
  Config frozen in `configs/research/neural_sde_signature_v1.yaml`
  (file SHA-256 recorded in the experiment artifact).

## Training windows and internal split (training period only)

- 841 eligible windows derived from 925 training returns
  (`925 − 22 − 63 + 1`), chronological, deterministic IDs `w0022…w0862`.
- Internal split at 80%: fit = 672 windows (targets through 2021-05-03),
  selection = 107 windows (targets from 2021-05-04), embargo gap = 62 windows;
  proof of no target overlap recorded as `756 > 755` (selection target start
  index strictly after fit target end index).

## Training outcome (internal fit/selection, training-period data only)

- initial internal signature loss ≈ `2.0567e+08`;
- best internal signature loss ≈ `2.7614e-03` (epoch 29);
- percent improvement ≈ 99.9999999987 %; early stop at epoch 69;
- parameter count 9609; finite losses/gradients/parameters throughout;
- final refit on ALL 841 training windows for exactly 29 epochs with a fresh
  deterministic reinitialization (seed 4242); the resulting checkpoint is
  frozen before any external-validation observation.

## Evaluation (performed only after the checkpoint was frozen)

- 1024 paths × 63 days, seed 4244, initial price 475.13 (final training-session
  close; benchmark convention), conditioning on the final available TRAINING
  context (normalized features recorded in the artifact) — forward looking at
  the training/validation boundary only.
- Scored with unchanged `research-metric-spec-v1` through the same scorecard;
  compared against the frozen suite (`iid_bootstrap`, `block_bootstrap`, `gbm`,
  `gjr_garch`, `heston`) per family, no baseline-specific scoring branch,
  no baseline recalibration, no rewritten baseline rankings.

## Outcome — BLOCKED (degenerate generator)

The model trains correctly, is deterministic and reproducible, and minimizes
the signature objective — but the frozen protocol's predeclared failure
criterion (protocol v1 line 114) is triggered:

- generated daily variance ≈ `7.60e-07` vs training empirical ≈ `1.68e-04`
  (≈ 0.45 % of real dispersion) and validation empirical ≈ `1.70e-04`;
- generated terminal-return dispersion ≈ **6.7 % of the real-data dispersion,
  below the 10 % collapse threshold** → the run is predeclared **failed** by
  the frozen protocol.

The expected-signature MMD matches mean signature features; it does not by
itself constrain per-path dispersion, and under the frozen v1 design the
optimizer found a low-dispersion solution. This is reported honestly.
Per the no-performance-gaming rule, the v1 config/checkpoint is FROZEN and is
not retrained or re-tuned in this milestone. Any improvement requires a
separately predeclared v2 training protocol using training-period /
internal-selection evidence only.

Per-family comparison summary (neural rank among 6 = 5 baselines + neural):

| family | training nearest baseline | neural rank (trn) | validation nearest baseline | neural rank (val) |
|---|---|---|---|---|
| mean | heston | 6 | iid_bootstrap | 6 |
| variance | gbm | 6 | gbm | 6 |
| skewness | block_bootstrap | 6 | gbm | 1 |
| excess_kurtosis | iid_bootstrap | 5 | gbm | 1 |
| quantiles | iid_bootstrap | 6 | gjr_garch | 6 |
| return_acf | heston | 6 | heston | 6 |
| abs_return_acf | gjr_garch | 6 | iid_bootstrap | 6 |
| sq_return_acf | gjr_garch | 6 | iid_bootstrap | 6 |
| leverage_correlations | heston | 6 | gjr_garch | 6 |

The neural SDE does **not** improve over GBM/Heston/GJR-GARCH on
distribution/tails, return ACF, absolute-return ACF, squared-return ACF, or
leverage in the headline conditional run; its only relative wins are
validation skewness and excess kurtosis (rank 1), reflecting that the
validation regime is thin-tailed. All comparisons are per-family; no aggregate
"winner" claim is made.

## Artifacts (gitignored)

- checkpoint: `data/processed/research/model/signature-neural-sde-v1/3857055bb83bea7b/checkpoint.pt`
  SHA-256 `01fce85964335e592da88f72fd23c54d878fa84acc3c4fd1d3e239632d0411e8`;
- experiment artifact:
  `data/processed/research/model/signature-neural-sde-v1/3857055bb83bea7b/neural_sde_signature_v1_experiment.json`;
- training curve: same directory `training_curve.json`;
- execution reports: `reports/data/execution/neural_sde_signature_v1_745d342.local.json`
  and `…_745d342_replay.local.json` (identical apart from the provenance timestamp);
- experiment id `dddaf09b0015d5fe73ceb10a632885011506df7e095aaf3716583863561444c0`;
  canonical experiment hash `a56a804fe57de3836f4686553c9699523790d1a99a431b0a501468d5380d4406`
  (identity excludes the provenance timestamp and storage paths only).

## Tests

- `tests/unit/data/research/test_sde_windows.py` — window geometry, leakage,
  features, normalization, internal split;
- `tests/unit/models/test_signature.py` — analytic level-k, Chen composition,
  concatenation property, zero path, context visibility, shape/dtype,
  autograd, MMD identically-zero/shifted/deterministic, metric-spec independence;
- `tests/unit/models/test_neural_sde.py` — determinism, dimensions, positivity,
  Euler-Maruyama constant-coefficient analytic moments, conditioning sensitivity;
- `tests/unit/research/test_neural_sde_trainer.py` — learning, reproducibility,
  fail-closed paths, clipping, refit, provenance/identity;
- `tests/integration/test_neural_sde_signature.py` — production-shaped real-data
  run twice (identical results), protected hashes, evaluation contract,
  comparison, freeze, zero-provider proof.