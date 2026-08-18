# Research Protocol Amendment 016

## V5 Preproduction Closure: Historical Invalidation, Gate Seed Formalization, and Config-Identity Classification

**Date:** 2026-08-18
**Status:** ACCEPTED

---

## 1. Background

The structured-volatility neural-SDE v5 development arm (finite level-3
lead-lag signature features, RBF-MMD, Euler/Itô simulation, state dim 2,
Brownian dim 2) reached the preproduction closure gate. This amendment
records: (a) the invalidation of gate/external-validation evidence produced in
the `a126f9c` lineage, (b) the formalization of previously implicit frozen
gate stochastic seeds, (c) the repair of the gate-v2 YAML loading path, (d)
the classification of structured-vol configuration identity, and (e) the
run-identity correction. It changes no frozen pass/fail numerical values, no
dataset, no provider state, and no historical artifact bytes.

## 2. Historical invalidation

1. Commit `a126f9ceb189b2060db1a1c91dc80a2506a8333b` claimed a v5 gate-v2
   PASS, but the production path did not actually use the frozen gate-v2 YAML.
   Root cause: `run_v5_experiment` resolved the gate-v2 file as
   `<repo>/src/configs/research/neural_sde_internal_gate_v2.yaml` (a
   non-existent path), so it could not load the frozen specification. Any gate
   result claimed from that lineage is **NOT ACCEPTED** scientific evidence.
   Repaired by resolving the authoritative path at the repository root
   (`parents[3]`).

2. `reports/research/structured_vol_v5_external_validation.json` produced in
   that lineage is **NON-CONFIRMATORY** and MUST NOT be used for generator
   selection, H1/H2 claims, or model tuning. Its tracked SHA-256 is
   `a85df830624e731eb3468e47e712d1fa2cef068a6a64de5bf498f6dd2352628e`.

3. The old bytes are preserved unchanged for historical reproducibility. No
   historical checkpoint, training curve, result, or report is rewritten.

## 3. Run identity correction

- Old historical run identity: `69623a82f91ff0dbc5b092863e8394724cb41e3f07144004810220856ad2d513`
  (prefix `69623a82f91ff0db`).
- Corrected current preproduction run identity (verified identical both before
  and after this closure, because this closure changes no material config
  value): `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157`
  (prefix `5bdbaabd2fb257a7`).
- No further identity field changed in this closure, so the final prospective
  run hash remains `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157`.

## 4. Gate stochastic seed formalization (provenance, not a change)

The accepted frozen gate-v2 implementation at
`c5105331ccea35ce7c3de835599ec58d4d1b9038` established, without any YAML key:

- generated-path seed `7777` (loader hardcoded `gate_seed=7777`; dataclass
  default `gate_seed=7777`);
- drift/diffusion diagnostic seed `7778` (= accepted `gate_seed + 1`).

A later loader change introduced `gate_seed = bootstrap.get("gate_seed",
bootstrap["seed"])`, silently switching generated paths to the bootstrap seed
`8801` and the diagnostic to `8802`. That is a scientific change made without
protocol approval and is rejected.

The gate YAML now declares these explicitly (`bootstrap.gate_seed: 7777` and
`bootstrap.drift_diffusion_seed: 7778`) and the loader requires them
fail-closed with no fallback. This is a provenance formalization of the
accepted semantics with **no semantic change**:

- gate-v2 YAML SHA-256: before `7080db9be42020ea7049e5a240048116c7a80b017545dcd66fc5dc5a2ac71bda`,
  after `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`.
- GateSpecV2 canonical hash: before `d1d40c6a62b347b7a593bd868340749d4b4122aa79604e77f270f72154358d6b`,
  after `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469`
  (hash now includes the explicit seeds).

Frozen pass/fail criteria are byte-identical to the accepted values:
1. best selection total loss < initial selection total loss;
2. variance ratio in [0.50, 2.00];
3. terminal dispersion ratio in [0.50, 2.00];
4. path uniqueness >= 0.99;
5. ACF(1) absolute error <= 0.25;
6. drift/diffusion RMS ratio <= 0.50.

Report-only metrics remain report-only.

## 5. Gate-v2 schema fail-closed repair

The loader now requires every pass/fail input fail-closed, including the ACF(1)
threshold (`serial_dependence.acf1.threshold` and `status`) and the explicit
seed fields. The report-only max-lag error is bound to
`serial_dependence.max_error.diagnostic_reference` (it had incorrectly reused
the ACF(1) threshold). The production bootstrap population is the
chronological selection tail via `selection_returns_series(...)`; overlapping
selection windows are never raveled.

## 6. Structured-vol configuration identity classification

For the structured-volatility scheduler constants:

| Constant | Classification |
|---|---|
| `diffusion_epsilon` (return-diffusion floor and kappa/eta floors) | A — config-identity already represented |
| `v_clamp_min`, `v_clamp_max` (latent-V clamp) | A — config-identity already represented |
| `a_positive` softplus floor | A — now bound to `config.diffusion_epsilon` (value `1e-6` unchanged); previously a hardcoded source literal |
| `a_raw` init `0.5`, `b_param` init `0.0` | B — deterministic source-bound initialization scheme; reproducible via model-init seed + commit |
| `dt`, `horizon`, `signature_level`, architecture fields | A — config-identity already represented |

No new config field was required (YAGNI). No historical run directory is
modified. Material config changes alter `config_hash`; purely representational
changes do not (unit-proven).

## 7. External validation / sealed-test governance

- No external validation may be executed again until the corrected production
  gate result is valid AND the governing protocol authorizes continuation.
- No sealed final-test outcome was accessed in this closure.
- The future external-validation report schema now records validation-series
  SHA, split name, date range, observation count, context/window identity,
  final checkpoint SHA, baseline-suite SHA, model config hash, and gate spec
  hash, derived from the actual objects/files at run time (no hardcoded
  values).

## 8. Historical artifact anchors (unchanged)

- `checkpoint.pt` (old run dir): `a092f5c5dc8c4d318a0a7c5c0a81ac6f42bd02054296c4bebb7eeaf13b9149c3`
- `training_curve.json` (old run dir): `4025b2699431b255851eb4a6ace11cfe01b67e521ca5eb87ad1dcbe72d04210a`
- `checkpoint_final.pt` (old run dir): `6a98b04da9be8ff53ae4c13570e96683f045a350a62682b9f43c22d9ccfd3a6b`
- Untracked historical reports (anchored by path + SHA-256; intentionally left
  untracked per repository artifact policy):
  - `reports/research/neural_sde_signature_v3_report.json`: `585ecd886a3619c0ee95242bd8cf668fe529e48e67d42b41676133519645a312`
  - `reports/research/neural_sde_signature_v4_report.json`: `cb4610d08e9545562d78d8c72b1a7d01381bc33ae1ac35e0a564397e70ece29c`
  - `reports/research/structured_vol_v5_report.json`: `c5ed284fe44af3cd2a04d8553d97b5830042c7cfbf1404a453ea084b23512548`

None of these bytes were modified.
