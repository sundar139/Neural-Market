# Signature Neural-SDE v2 — Frozen Experiment Record

Status: SIGNATURE NEURAL SDE V2 READY (internal gate passed; evaluated once).
Date: 2026-08-17. Repository HEAD (start): `2f1ad35a06702865e513cb3ad9f1a1cb52088031`.
Safety branch: `safety/pre-signature-neural-sde-v2-2f1ad35` (points exactly at starting HEAD).

## Motivation (from v1, validated on training/internal evidence)

v1 (signature-neural-sde-v1) trained deterministically (best internal
truncated-signature loss 2.761415e-03 at epoch 29) but its objective was per-level
linear expected-signature MEAN matching, which cannot distinguish distributions
that share a mean signature vector but differ in per-path dispersion.  The v1
trainer therefore converged to a low-dispersion generator:

- generated daily variance ≈ 7.6e-07 vs empirical ≈ 1.68e-04 (≈ 0.45 % of real);
- terminal dispersion ratio ≈ 6.7 % of real, below the predeclared 10 % collapse
  threshold (protocol v1 line 114) → v1 FAILED non-degeneracy.

v2 fixes the objective (not the architecture): RBF-MMD over INDIVIDUAL
truncated-signature feature vectors plus one training-only log-variance
anti-collapse penalty.  No external-validation metric guided any v2 choice.

## Protocol trace

Same protocol as v1 (underspecified architecture; frozen fallback design).
v2 adds the predeclared internal anti-collapse gate (terminal dispersion ratio
>= 0.50 on the internal-selection subset) evaluated strictly before any
external validation is loaded.

## Frozen bindings (verified identical to v1; protected files untouched)

- inventory hash `371c1483…6d119`; benchmark hash `2b0dd31e…593d`;
  metric-spec hash `5e43a3a3…00eb3`; baseline-suite hash `445b1257…f0099`;
- training series SHA-256 `4863b2cc…68669c`; validation series SHA-256 `ec49994b…47edc8`
  (bound independently from benchmark and suite);
- v1 preserved (hashes below unchanged after all v2 runs):
  - v1 config (committed) `34bc951758dacdae30a060ef7c472a27b4e705d0cec810c7584c2e30fd9037a2`;
  - v1 checkpoint `01fce85964335e592da88f72fd23c54d878fa84acc3c4fd1d3e239632d0411e8`;
  - v1 experiment artifact `98167304c1096f6e670c82024e70be171d29560b36c26e6a325ff032fc75a3ff`;
  - v1 training curve `fdc6749a1e414081a0bc9db6c2daecf04f15c5f23be6532afbcc880a1a2d7c3f`.

## v2 objective (frozen)

- Kernel: RBF-MMD^2 (biased estimator, frozen form) over individual
  standardized truncated-signature feature vectors (level 3; augmented path
  dim 6 → feature dim 258).
- Standardization: per-dimension z-score from TRAINING-FIT real paths only
  (floor eps 1e-8 for near-zero standard deviations; non-finite rejected).
- Bandwidth: median pairwise squared distance over standardized training-fit
  real signature vectors (deterministic, max 512 vectors).
- Anti-collapse: L_var = (log var_gen - log var_real)^2 with coefficient
  λ = 1.0 and eps = 1e-12, target = log of TRAINING-fit target pooled variance.
- No kurtosis / leverage / ACF / baseline-rank / validation-score terms.

(Objective definition block and exact numbers are persisted in the sealed
v2 experiment artifact.)

## v2 config

- tracked: `configs/research/neural_sde_signature_v2.yaml`
  (file SHA-256 recorded in artifact; config hash recorded in artifact).
- Config-file byte note: the frozen v2 run read the pre-newline bytes
  (SHA-256 `0163256cbb36dda2631188263b211d65884183ef212d419723a9c647af2f9647`),
  recorded verbatim in the artifact. The committed copy gained a trailing
  newline from the mandatory `pre-commit` end-of-file-fixer (SHA-256
  `da3519393c25ba9822bca6835a802fd6b5822d3cc97b2c423e08b2ae5d1de4fe`), matching
  how the v1 config was normalized. This byte change does not alter
  `config_hash` (hash of the parsed configuration), so a fresh replay
  reproduces the identical experiment (identical checkpoint SHA and identity).
- Architecture retained from v1 exactly: state 2, Brownian 2, 4 context
  features, 2x64 SiLU drift/diffusion MLPs, softplus+1e-6 diffusion,
  Euler-Maruyama dt=1/252, 63 steps.
- Training: AdamW lr 1e-3, weight decay 1e-6, batch 64, max 400 epochs,
  patience 40, grad clip 1.0; seeds 4242 (init) / 4243 (data) / 5252 (v2 eval).

## Internal split (unchanged from v1, training-period only)

841 eligible windows; fit 672 (targets through 2021-05-03), selection 107
(from 2021-05-04), gap 62; no-target-overlap proof `756 > 755`.

## Training process (internal fit/selection only)

Frozen config run (400-epoch budget; early-stopped at patience 40):

- initial internal RBF-MMD: 0.92871767
- best internal RBF-MMD: 0.02707529 (97.08 % improvement)
- best epoch: 43; final epoch: 83 (early stop)
- parameter count: 9609; torch 2.13.0+cpu, device cpu, dtype float32.
- deterministic replay PROVEN: a second full run reproduced the identical
  checkpoint SHA-256 (262d8358…), artifact hash 321c042e…, and all identity
  content (only the provenance timestamp differs).

## Internal anti-collapse gate (selection subset; before any validation)

- generated daily variance: 1.019e-05; real selection daily variance: 5.374e-05;
  variance ratio: 0.190 (generated ~19 % of real on daily returns);
- generated terminal std: 0.1802; real terminal std: 0.02377;
  terminal dispersion ratio: 7.58 (gate threshold >= 0.50) → PASSED;
- path uniqueness fraction: 1.0; diffusion mean 0.0696, min 1.19e-05, max 0.476;
- RBF-MMD improvement condition: satisfied (best < initial).

The gate passed, so the milestone proceeded: best epoch frozen at 43, final
refit on ALL 841 training windows, checkpoint frozen
(SHA-256 `262d8358f4dfbb9615c39e16936ecc92475aa395d226c8661370c4ace92b1b32`),
and only then was external validation loaded.

## External validation (evaluated exactly once, no post-validation tuning)

1024 x 63 paths, v2 eval seed 5252, initial price 475.13, conditioning on the
final available training context.  Scored with unchanged research-metric-spec-v1.

v2 neural metrics: mean 5.889e-04 (empirical train 6.30e-04 / val 3.22e-04),
variance 2.54e-06 (train 1.68e-04 / val 1.70e-04), skewness -0.017,
excess kurtosis 0.030 (train 13.7 / val 1.58), return ACF(1) 0.979 (train -0.15 /
val -0.009), sq-return ACF(1) 0.974 (train 0.46), leverage(1) +0.448 (train -0.13).

Per-family comparison (nearest classical baseline; v1/v2 neural ranks among the
7 comparators: 5 classical baselines + v1 + v2):

| family | nearest (train) | nearest (val) | v1/v2 rank (train) | v1/v2 rank (val) |
|---|---|---|---|---|
| mean | heston | iid_bootstrap | 7/3 | 7/2 |
| variance | gbm | gbm | 7/6 | 7/6 |
| skewness | block_bootstrap | gbm | 7/5 | 1/3 |
| excess_kurtosis | iid_bootstrap | gbm | 5/6 | 1/2 |
| quantiles | iid_bootstrap | gjr_garch | 7/6 | 7/6 |
| return_acf | heston | heston | 7/6 | 6/7 |
| abs_return_acf | gjr_garch | iid_bootstrap | 7/6 | 7/6 |
| sq_return_acf | gjr_garch | iid_bootstrap | 7/6 | 7/6 |
| leverage_correlations | heston | gjr_garch | 7/6 | 7/6 |

Honest interpretation, no performance-gaming:

- v2 DOES fix the v1 collapse in the anti-collapse sense defined by the
  predeclared gate: paths are non-degenerate, unique (uniqueness 1.0), and
  terminal dispersion (7.6x real) is far above the 10 % collapse threshold.
- v2 DOES NOT produce realistic volatility or autocorrelation: daily variance
  is ~1.5 % of the empirical value at evaluation and the learned drift creates
  near-trending paths (return ACF(1) ≈ 0.98, positive leverage) because the
  RBF-MMD gradient is satisfied largely through drift structure instead of
  diffusion, and the daily log-variance penalty (coefficient 1.0) only partially
  corrected it (internal variance ratio 0.19).
- v2 improves over v1 on mean skewness and validation skewness/kurtosis ranks,
  but does not beat any classical baseline on distribution/tails, return ACF,
  abs-return ACF, sq-return ACF, or leverage.
- No post-validation tuning; changing the anti-collapse coefficient or adding
  volatility-structure terms requires a separately predeclared v3 protocol
  using training-only evidence.

## Data value-of-information recommendation (after v2)

The internal gate PASSED, so the mandatory audit path was not triggered.  The
honest recommendation after the v2 result:

- The corrected objective works (97 % RBF-MMD improvement, non-degenerate), but
  the generator is still far from realistic volatility/ACF.  This is evidence
  of conditioning/representation limitation rather than a need for more option
  data.
- Candidate A (extend SPY daily history backward before 2018-05-01) is
  scientifically the most relevant next step for a predeclared v3: it increases
  training windows ~+70 % for 2 extra years and keeps validation/final test
  intact, with no model-input contract change.
- Candidate B (SPY intraday RV context) is a secondary option that changes the
  model input contract.
- Candidate C (additional OPRA data) is rejected: the observed failure is
  underlying-path dispersion/volatility structure, not missing option
  observations.
- NO purchase is performed in this source milestone; ~102.46 USD credits remain
  available only as contingency for a later LIVE milestone with a precise
  preflight and risk assessment.

## Artifacts (gitignored)

- experiment id `ea7345021e11e7e45c0536045da3cd1f4920246e883f94ea8c45f09f4207b0a3`;
- canonical experiment hash `321c042e80fd329df096454b842166a79f3f7f29fd9a17301f09f9b9f132f7fb`;
- checkpoint: `data/processed/research/model/signature-neural-sde-v2/727520d44f381ba2/checkpoint.pt`
  SHA-256 `262d8358f4dfbb9615c39e16936ecc92475aa395d226c8661370c4ace92b1b32`;
- experiment artifact: same directory `neural_sde_signature_v2_experiment.json`;
- training curve: same directory `training_curve.json`;
- execution reports: `reports/data/execution/neural_sde_signature_v2_2f1ad35.local.json`
  and `…_2f1ad35_replay.local.json` (identical apart from provenance timestamp).

## Tests

- `tests/unit/models/test_signature_mmd.py` — RBF-MMD (identical/zero, shifted/
  positive, equal-mean/different-dispersion positive, deterministic, symmetric,
  non-negative, finite gradients, malformed rejection), bandwidth (deterministic,
  zero-median fail-closed, train-only API), standardizer (train-only, deterministic,
  near-zero dims safe, leakage impossible by API), variance penalty (zero at
  match, positive under collapse, finite gradients, train-only API);
- `tests/unit/research/test_neural_sde_trainer_v2.py` — internal gate
  (collapsed fails / reasonable passes / deterministic / no validation input),
  v2 training smoke (improvement, non-degenerate, reproducibility),
  objective config hash;
- `tests/integration/test_neural_sde_signature_v2.py` — production-shaped
  short run twice (identical), v1 preservation (hashes unchanged), frozen
  bindings, objective definition, gate diagnostics, validation-only-after-gate
  structure, final-test isolation, tamper rejection, zero-provider proof.
