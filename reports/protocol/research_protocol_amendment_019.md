# Research Protocol Amendment 019

## V5 External-Validation Closure and Interpretation Boundary

**Date:** 2026-08-19
**Status:** CLOSED — append-only provenance/interpretation closure. No scientific computation.
**Task:** NM-R4-V5-EXTERNAL-VALIDATION-CLOSURE-021
**Prior tasks:** NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-015 (blinded failure), NM-R4-V5-EXTERNAL-VALIDATION-FAILURE-AUDIT-016 (PROVEN HARNESS IDENTITY-CHECK DEFECT), NM-R4-V5-EXTERNAL-VALIDATION-IDENTITY-REPAIR-017 (representation-only repair), NM-R4-V5-EXTERNAL-VALIDATION-IDENTITY-REPAIR-AUDIT-018 (VALIDATED), NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-019 (construction #2, EXTERNAL_VALIDATION_COMPLETED), NM-R4-V5-EXTERNAL-VALIDATION-EVIDENCE-AUDIT-020 (VALIDATED WITH NON-BLOCKING FINDINGS, external-validation evidence VALIDATED).

---

## 1. Purpose

This amendment closes the v5 external-validation arm. It is append-only. It does not modify Amendment 017 or 018, does not change any result, does not change any metric, and does not authorize any further scientific action. It freezes the interpretation boundary under which the single immutable construction-2 result may be cited.

## 2. External-validation closure

```
external_validation_state: CLOSED
external_validation_evidence: VALIDATED
governed_validation_constructions: 2
effective_max_governed_validation_constructions: 2
third_construction_permitted: false
final_test_authorized: false
tuning_authorized: false
retraining_authorized: false
hedging_authorized_from_this_task: false
```

No mechanism exists for reopening validation under this arm. A third governed validation construction is permanently forbidden. The v5 external-validation arm is CLOSED.

## 3. Governed construction history

Construction #1 — task NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-015:

- status: BLINDED_MECHANICAL_FAILURE
- validation_constructed: true (validation series bound, SHA passed)
- model_simulation: false — failed at `verify_frozen_target` before `verify_canonical_checkpoint`
- scientific outcome exposed: false
- failure: PROVEN_HARNESS_IDENTITY_CHECK_DEFECT — `canonical_dumps(..., sort_keys=True)` on int-key live scorecard vs string-key JSON-round-tripped frozen target; value-independent (would occur for every series)
- evidence SHA: transcript `5063b0f0eceaefb53657c869adc46bfaf8293737b9a8b717d9d75a27da58393d`, exit-code `6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b` (exit `1`)

Construction #2 — task NM-R4-V5-EXTERNAL-VALIDATION-EXECUTE-019:

- status: EXTERNAL_VALIDATION_COMPLETED
- validation_constructed: true
- model_simulation: true (once)
- normalized exact target match: true (no tolerance)
- result SHA: `a28345587989ea1d91d46ed7c9b332151b84af98c0d4918f0fc281d03ba4ca38` (status EXTERNAL_VALIDATION_COMPLETED, mode report_only)
- manifest SHA: `549056a1ceccc7b238d73b71b50390fd4e7ad603cb627eb6147516bad7124046`

Construction #3: FORBIDDEN — `MAX_GOVERNED_VALIDATION_CONSTRUCTIONS_FOR_THIS_ARM = 2` (Amendment 018); no epsilon, no retry, no regeneration, no alternate environment.

Cumulative governed validation constructions for this arm: exactly 2 of 2, now frozen.

## 4. Independently validated evidence

Evidence-audit task NM-R4-V5-EXTERNAL-VALIDATION-EVIDENCE-AUDIT-020: VALIDATED WITH NON-BLOCKING FINDINGS; external-validation evidence VALIDATED. All immutable evidence re-hashed and byte-identical:

- confirmatory result: `a28345587989ea1d91d46ed7c9b332151b84af98c0d4918f0fc281d03ba4ca38`
- attempt2 transcript: `132ecca481d8eb37d4a908c1a129f02da48f14758809103b4c7e7d4f4abaf6ef`
- attempt2 exit-code: `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` (exit `0`)
- attempt2 manifest: `549056a1ceccc7b238d73b71b50390fd4e7ad603cb627eb6147516bad7124046`
- attempt1 transcript/exit: `5063b0f0...` / `6b86b273...` unchanged
- repaired harness: `726f885a5f0590b542dc4ba989bc5ea0a97afd3f05bb4c06ad9f9c51e1c1e143` (blob `e77db7b5a99f17d9c55b332f6f81f8fe6ede3b43`)
- Amendment 017: `9ff02f54c2264ef3b563062738e3d15e5802f6c92d56e88a284e8caae7c12abd`
- Amendment 018: `c5ecf9829e5177bd608cbb00e1ec70652b3fe8266c4315b785723b915adc1e40`
- contract YAML: `c7544e5b7cd70ab93e5c6b0ac747ad5eb882536faefca1f575834f2713658363`

This amendment does not re-validate those hashes; it records them as the frozen closure basis.

## 5. Correct production artifact identities

Accurate, non-confusable identification (do not conflate):

- Scientific source: `357971a67c68492fc0c4f5bf31f94f9685639f65`
- Selected production checkpoint (best/selected from production selection):
  path `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint.pt`
  SHA `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f`
- Canonical production training curve:
  path `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/training_curve.json`
  SHA `e29f2afcdff75e151ca6a85f3c77e7a209a3c1827b6d1abcb191ce36c6d30a2d`
- Final-refit / external-validation candidate checkpoint (evaluated, distinct from selected):
  path `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint_final.pt`
  SHA `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4`
  config_hash `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157`
- Canonical production Gate-v2 report (the authoritative production gate):
  path `reports/research/structured_vol_v5_production_gate_v2.json`
  SHA `4604231cfc5d26f61808b65ce9269a120ccb44c2c96a590853341e31c9f14bc6`

Do not call `checkpoint_final.pt` (SHA `c7b9be5d...`) the selected checkpoint. Do not call `reports/research/structured_vol_v5_report.json` the canonical production Gate-v2 report — it is historical/non-canonical evidence.

## 6. Immutable-manifest metadata clarification

The frozen construction-2 manifest (`reports/research/structured_vol_v5_external_validation_attempt2_manifest.json`, SHA `549056a1ce...`) is immutable historical evidence and is not edited by this closure.

Known non-blocking reporting-metadata findings (evidenced by audit, not corrected by editing the manifest):

- canonical_selected_checkpoint label in the manifest actually points to the final_refit checkpoint (`c7b9be5d...`), not the true selected checkpoint (`452f7005...`);
- canonical production Gate-v2 report anchor is omitted.

Manifest status: `immutable_historical_evidence` — classification NON_BLOCKING_REPORTING_METADATA.

Authoritative supplementary labels live here (Amendment 019) and in the machine-readable closure supplement `reports/research/structured_vol_v5_external_validation_closure.json`. Do not treat the manifest as corrected.

## 7. Report-only interpretation boundary

The immutable external-validation result (`a28345587989ea...`) is:

```
REPORT-ONLY
PER-FAMILY
BASELINE-RELATIVE
NO binary threshold
NO aggregate
NO overall model rank
NO overall winner
NO direct H1 acceptance
NO direct H2 acceptance
```

Allowed descriptive statements (baseline-relative, per-family, for the six-member comparison set `{structured_vol_v5, iid_bootstrap, block_bootstrap, gbm, gjr_garch, heston}`):

- structured_vol_v5 ranks 1/6 on mean (candidate_error `0.1407...`, nearest `iid_bootstrap` `0.773...`);
- 2/6 on excess_kurtosis (`3.836...` vs nearest `gbm` `1.000...`);
- 2/6 on skewness (`1.351...` vs nearest `gbm` `1.175...`);
- 4/6 on return_acf (`0.961...` vs nearest `heston` `0.780...`);
- 4/6 on sq_return_acf (`1.348...` vs nearest `iid_bootstrap` `0.981...`);
- 4/6 on leverage_correlations (`0.896...` vs nearest `gjr_garch` `0.595...`);
- 5/6 on quantiles (`0.183...` vs nearest `gjr_garch` `0.092...`);
- 5/6 on variance (`0.305...` vs nearest `gbm` `1.5e-05...`);
- 6/6 on abs_return_acf (`3.486...` vs nearest `iid_bootstrap` `0.969...`).

These are descriptive. Do not compute an average rank. Do not count wins as a pre-registered success measure. Do not collapse the nine families into a single claim.

## 8. Signed family-error semantics

Scalar family_errors carry signed `relative_error`; the ranking comparator uses magnitude (as defined by the frozen `_family_errors` / comparison algorithm). Therefore observed pairs are consistent, not contradictory:

- variance: family_errors `relative_error = -0.3050747405615484`, ranking `candidate_error = 0.3050747405615484` (absolute);
- skewness: family_errors `relative_error = -1.351250398451968`, ranking `candidate_error = 1.351250398451968` (absolute);
- likewise for other signed scalars where `candidate_error == abs(relative_error)`.

This note is for write-up correctness; do not edit the result.

## 9. Lag-66 / horizon-63 caveat

MetricSpecification includes temporal lag `66`; generated-path horizon is `63`; generated scorecards are flattened over `1024 x 63` paths. Consequently lag-66 simulated temporal pairs cross independent path boundaries. This convention is shared identically across structured_vol_v5 and the five classical comparators.

Permitted: baseline-relative comparisons under the frozen metric convention remain valid.

Not permitted: claim that the lag-66 statistic demonstrates genuine within-path 66-session dependence of the generator.

Do not change the metric specification. Do not remove lag 66 retroactively.

## 10. Validation identity (source-derived only, from immutable evidence)

- validation_series SHA: `ec49994bf262b6cd29f8a3ed772f00cfcb901ef04181c14e9ccefb908f47edc8` (split `validation`, 2022-05-26 to 2023-06-30, 274 observations)
- normalized target SHA (both sides): `56b3ba15c0c95d6a89eb59ead89ab5dc669327245bb5f383666a384f3fd3c5b9`
- recomputed == frozen: true
- exact_match: true
- tolerance: none (no epsilon, no rtol, no atol; pending `nextafter` differences still fail per frozen harness tests)

Read from immutable evidence only; no validation reconstruction in this task.

## 11. Final-test status

`final_test_authorized: false`. No final-test construction, no final-test data access, no tuning, no retraining, no hedging is authorized by or within this closure task.

## 12. Prohibited actions

From this closure forward, under the v5 external-validation arm:

- no third validation construction;
- no validation data access beyond that already consumed;
- no model simulation under this arm;
- no final-test access;
- no source/model/checkpoint/config/scorecard/MetricSpecification/baseline changes via this arm;
- no edit to the immutable construction-2 result or attempt2 manifest;
- no aggregate/overall-winner/H1/H2 claim from the external-validation result alone;
- no push.

## 13. Next scientific decision boundary

Recommended next scientific action is governed reconciliation of the original research contract before any final-test consideration, including but not limited to:

- five-independent-seed requirement;
- current finite level-3 lead-lag signature + RBF-MMD versus intended true signature-PDE / sigkernel methodology;
- current Euler/Itô integration versus intended Stratonovich / torchsde reversible-Heun semantics.

Those issues are not resolved inside this closure task and are not to be resolved by editing v5 external-validation evidence.

## 14. Amendments 017 and 018 remain unchanged

Amendment 019 is append-only closure/provenance. It does not modify Amendment 017 (the pre-access scientific contract) or Amendment 018 (the blinded repair and terminal reauthorization policy). No frozen target, conditioning, seed, paths, horizon, checkpoint, MetricSpecification, baseline set, ranking, or threshold is changed.

---

*No held-out metric values beyond those already published in the immutable construction-2 result are reproduced here except the per-family rank summary necessary to freeze the interpretation boundary. SHAs are provenance, not held-out results.*
