# Research Protocol Amendment 017

## External Validation Contract for Structured-Volatility Neural-SDE v5

**Date:** 2026-08-19
**Commit:** (pending)
**Status:** ACCEPTED — methodology / pre-registration only. No execution authorized by this amendment.

---

## 1. Motivation / task-010 blocker

Task NM-R4-V5-EXTERNAL-VALIDATION-010 ended BLOCKED BEFORE VALIDATION ACCESS.
Source inspection of `src/neuralmarket/research/structured_vol_experiment.py`
confirms the v5 `run_v5_experiment` external-validation tail is NOT a genuine
held-out validation procedure:

- `build_validation_identity` (lines 112-157) loads `split="validation"` only to
  record identity/hash provenance;
- the summary run conditions on the frozen training-boundary context
  `w_boundary` (lines 311-320);
- it simulates generated paths with `simulate_structured` (line 326);
- it computes a generated-only scorecard payload
  (`compute_scorecard(increments.ravel(), ...)`, lines 329-335);
- it never compares the generated scorecard against held-out validation
  observations / `validation_empirical`; no `_family_errors` call exists in the
  file. The `spec_metric` section is identical to the v1-era comparison
  machinery but the validation arm (`_family_errors(payload, validation_empirical)`)
  was never wired into the v5 path.

The protected validation opportunity therefore remains unconsumed. This
amendment freezes the scientific contract for a genuine one-shot held-out
external-validation procedure BEFORE any validation construction, any
validation-data read, any evaluator implementation, or any execution.

## 2. Candidate identity

- Candidate: structured-volatility neural-SDE v5 (module
  `neuralmarket.models.structured_vol_sde.StructuredVolatilityNeuralSde`).
- Frozen experiment config:
  `configs/research/structured_vol_neural_sde_v5.yaml`.
- Model config hash (candidate run identity, Amendment 016 §3):
  `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157`
  (verified in this task by recomputing `V5ExperimentConfig.config_hash()`
  from the tracked YAML).
- Canonical final checkpoint:
  `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint_final.pt`
  SHA-256 `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4`
  (verified byte-for-byte in this task).
- Scientific source commit: `357971a67c68492fc0c4f5bf31f94f9685639f65`
  (independently validated v5 source; `fix(research): persist v5 source identity`).
- The checkpoint embeds `sde_config` identical to the frozen YAML `sde` block
  (verified in this task).

## 3. Held-out target definition

The held-out target is the **frozen validation empirical scorecard** computed
once, at benchmark-milestone time, from the chronological validation split
under the unchanged frozen metric specification:

- representation: `validation_empirical` scorecard payload of
  `MetricSpecification` (`research-metric-spec-v1`);
- identity pins (structural provenance, not outcome values):
  - artifact: `data/processed/research/benchmark/empirical_benchmark_v1.json`
    → `metrics.validation_empirical`;
  - copied verbatim into `simulator_baseline_suite_v1.json`
    → `metrics.validation_empirical`;
  - metric-spec hash: `5e43a3a3242271802ee7057405836ffb6d12d0ce732d3256dbd362ce5a400eb3`;
  - benchmark hash: `2b0dd31e59a3e8becc638e432ca9274d7ab8b2b8829038407cbbfc1700d1593d`;
  - baseline-suite hash: `445b1257210f34d9a9b29fbdf2ac4e9b64265f9b3f21e7084f97e4bd935f0099`;
  - split identity: `"validation"`, bound to
    `benchmark.underlying["validation"].series_sha256` and
    `suite.validation_series_sha256` (the suite validator enforces the binding).
- Observed metric values of `validation_empirical` are NOT used anywhere in
  this amendment and were NOT inspected during its creation.

## 4. Conditioning semantics

**TRAINING-BOUNDARY CONTEXT ONLY** (frozen, one option, no rolling origin).

Justification from protocol and existing design, not from outcomes:

- Research Protocol v1 mandates chronological splitting only, normalizers fit on
  training data only, and final-test access only after models, metrics,
  baselines, costs, and statistical procedures are frozen.
- The v1 experiment design (`neural_sde_experiment.py` `_evaluation_block`)
  conditions the headline run on "the final available TRAINING context (forward
  looking at the training/validation boundary)" — the same `w_boundary` construct.
- The v5 production path already conditions on `w_boundary` built from training
  returns only (`structured_vol_experiment.py` lines 311-320).
- The frozen initial-price convention is "final training-session close"
  (`MetricSpecification.initial_price_convention`; `V5ExperimentConfig`).

Consequently the frozen candidate is a genuine future-distribution forecast
from the end of training: no held-out validation observation alters or advances
the model context; the validation split supplies the held-out TARGET only. This
cannot leak validation into the conditioning, so it is also the only
leakage-safe option consistent with the protocol.

## 5. Generation semantics

- Checkpoint: canonical `checkpoint_final.pt` only (identity in §2).
- Model configuration: frozen v5 config (identity in §2), unchanged.
- Load semantics: checkpoint `model_state` only; `torch.no_grad()` eval
  simulation; deterministic configuration on; no training, no gradient, no
  refit.
- Context: final eligible training context (`w_boundary`; last
  `context_lookback = 22` training returns) normalized by the training-fit
  `FeatureNormalizer`.
- Horizon: 63 sessions (`sde.horizon` / `windows.horizon`, frozen).
- Number of generated paths: `n_eval_paths = 1024` (frozen).
- Evaluation seed: `eval_seed = 8283` (frozen).
- Return representation: one-step daily log-return increments (the public
  output contract of `StructuredVolatilityNeuralSde`, Amendment 013-corrected).
- Initial price (level checks): final training-session close.

No post-validation change to any of the above is permitted.

## 6. Metric specification

Unchanged frozen `MetricSpecification` (`research-metric-spec-v1`,
`src/neuralmarket/eval/scorecard.py`):

- `ScorecardConfig`: lags (1, 5, 22, 66); aggregation horizons (5, 22);
  tail quantiles (0.01, 0.05, 0.10, 0.90, 0.95, 0.99); Hill sample fraction 0.1;
  min observations 252.
- Scalar families: mean, variance, skewness, excess_kurtosis.
- Distribution family: quantiles.
- Temporal-dependence families: return ACF, absolute-return ACF, squared-return
  ACF, leverage correlations.
- Scorecard implementation: `neuralmarket.eval.scorecard.compute_scorecard`.
- No metric is added, removed, or reweighted after this contract or after
  validation access.

## 7. Baseline comparison semantics

Frozen baseline suite `data/processed/research/benchmark/simulator_baseline_suite_v1.json`
(identity: suite_hash `445b1257...efd9`, file SHA-256
`28a10b1d23ee225b07a94c2f12a01fa08b627e443f1da5eee1329541b9aa139a`) already
contains, under the identical `MetricSpecification` and family-error semantics,
validation comparisons for every evaluated classical comparator:

`GBM`, `Heston` (accepted_prior), `iid_bootstrap`, `block_bootstrap`,
`gjr_garch` — each recorded as
`suite.discrepancies["validation"][name] = _family_errors(metrics[name], validation_empirical)`.

Contract:

- v5 external error vector:
  `_family_errors(generated_scorecard_payload, validation_empirical)` using the
  generic comparison `neuralmarket.data.research.benchmark._family_errors`.
- v5 vs baselines: report per-family v5 errors against the already-frozen
  per-family baseline error vectors for the SAME metric families.
- Existing per-family baseline rankings (`suite.rankings["validation"]`) are
  reused verbatim as the reference ordering; the v1 `_comparison_block`
  convention (per-family nearest baseline and neural rank, no collapse) is
  adopted.
- NO new weighted aggregate and NO overall winner score is invented: this
  amendment reports per-family values and per-family baseline ranks only.

## 8. Result-classification policy

No pre-existing frozen binary external-validation gate exists for v5 (the
frozen gate-v2 is an internal training/selection gate; its thresholds are not
external-validation acceptance thresholds). Therefore:

- `external_validation_status = EXTERNAL_VALIDATION_COMPLETED`
- Mode: **REPORT-ONLY / CONFIRMATORY**. No PASS/FAIL.

This contract creates no binary acceptance threshold and freezes none.

## 9. One-shot access semantics

- `top_level_external_validation_evaluations = 1` (one held-out comparison run).
- `validation_series_constructions = 1` (one construction of the validation
  series in the execution harness, used to recompute/verify the pinned
  validation identity and scorecard).
- The future execution harness MUST fail closed before a second validation
  construction, MUST expose instrumented access counters, MUST refuse
  training/refit/tuning/final-test/checkpoint substitution, and MUST verify the
  recomputed validation scorecard against the pinned `validation_empirical`
  (byte-identical) before reporting.

## 10. Leakage / tuning prohibitions

- No validation observation may be used to alter the model, its context, the
  metrics, the thresholds, or the methodology.
- No hyperparameter, metric, or threshold tuning after validation access.
- No checkpoint substitution.
- No production training, no refit, no replay.
- The methodology in this amendment was frozen independently of validation
  results.

## 11. Final-test prohibition

- No sealed final-test access is authorized or performed by this contract.
- This amendment does not authorize final-test access, and a completed external
  validation does not automatically authorize final-test access.

## 12. Permitted claims

After execution the following REPORT-ONLY statements are permitted:

- v5 generalized better/worse than its internal-selection behavior on metric family X;
- v5 outperformed/underperformed baseline Y on metric family X;
- v5 showed specific held-out strengths/weaknesses.

NOT permitted: changing v5; selecting a new threshold; retraining from the
result; calling final H1/H2 proven; authorizing final test automatically.

## 13. No validation inspection during contract creation

In creating this amendment and its machine-readable companion
(`configs/research/structured_vol_v5_external_validation_v1.yaml`) NO
validation data was constructed, NO raw validation observations were read, NO
`validation_empirical` numerical values were inspected, NO baseline validation
rankings were inspected, and NO validation-error values influenced any decision
here. Only schemas, field names, source code, metric-spec definitions,
baseline-suite structure, and identity hashes were examined.

## 14. Execution gate

This amendment authorizes NO execution. The exact external-validation run may
occur ONLY after:

1. independent (read-only) audit of this amendment and the machine-readable
   frozen contract, and
2. a separately precommitted, governed implementation of the execution harness
   that satisfies the fail-closed access semantics of §9.

Machine-readable contract: `configs/research/structured_vol_v5_external_validation_v1.yaml`
(schema version `structured-vol-v5-external-validation-v1`).

---

## Amendment log

- 2026-08-19 — Amendment 017 ACCEPTED (methodology contract only; no validation
  access, no execution).
