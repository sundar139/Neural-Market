# Amendment 041 — V5 Seed-05 Sensitivity Preregistration Corrections

**Date:** 2026-08-21
**Task:** NM-R4-V5-SEED-05-SENSITIVITY-REPAIR-063
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `02c12ab474985205b6f677a1bf5f17bfcb62fc87`
**Safety branch:** `safety/pre-v5-seed05-sensitivity-repair-02c12ab`
**Audit triggering repair:** NM-R4-V5-SEED-05-SENSITIVITY-AUDIT-062 — REPAIR REQUIRED
**Task to repair:** NM-R4-V5-SEED-05-SENSITIVITY-PREREGISTRATION-061
**Existing preregistration:** `reports/protocol/research_protocol_amendment_040.md` — historically immutable, NOT modified
**Status:** CORRECTION/SUPERSESSION — append-only. No training, no --execute, no authorization artifact, no seed-05 execution, no reserve, no validation, no final-test access.

## 1. Scope

Amendment 040 remains historically immutable. This amendment corrects blocking defects A/B and closes non-blocking gaps C–E identified in Audit 062. All Amendment 040 clauses not explicitly superseded below remain normative and in force. Where text conflicts, this amendment governs.

No preregistered scalar, formula, threshold, or sensitivity design is reopened beyond the explicit supersessions listed.

## 2. Superseded clauses (exact)

The following Amendment 040 phrasing or citations are superseded:

1. Any citation of runner `7b46e0f6c805687977cd685ebb97741bd4243cbe` as the device-aware prospective CUDA execution basis, including Amendment 040 section 8 line "as repaired in Amendment 036, runner blob 7b46e0f..." and any implication that `7b46e0f6...` provides CUDA device-aware execution — SUPERSEDED by section 3 below.

2. Any implication that Amendment 036 produced runner `7b46e0f6c805687977cd685ebb97741bd4243cbe` — SUPERSEDED (036 predates CUDA repair; 7b46e0f6 is pre-CUDA CPU-era runner).

3. Amendment 040 sections 4–5 and 9 phrasing "admissible members only", "N=3 if seed-05 fails/inadmissible", "plus seed-05 if admissible", "when seed-05 succeeds and is admissible", and any text where scientific Gate outcome controls sensitivity inclusion — SUPERSEDED by sections 4–5 below (three-way semantics).

4. Amendment 040 section 8 source path `src/neuralmarket/research/runtime_identity.py` — SUPERSEDED by `src/neuralmarket/core/runtime_identity.py` per section 7.

5. Amendment 040 section 8 trainer line numbers `neural_sde_trainer_v3.py:218-219,367-368` and any line-number-pinned RNG/device references — SUPERSEDED by stable symbol references in section 7 (line numbers are fragile; symbol names govern).

6. Amendment 040 section 3.1 sentence "If any component (e.g., initial_internal_rbf / best_internal_rbf) is not consistently available for seed-01, it is excluded from family summary or reported only for members where available with explicit N." — SUPERSEDED by definitive exclusion in section 6 (no optional treatment remains).

No other Amendment 040 clause is superseded.

## 3. Historical vs prospective CUDA identities (blocking defect A — corrected)

### 3.1 Historical CPU lineage (execution provenance only)

- historical recipe (commit): `20d90f7484fe5df7cd62755a5810c8de78e5e92f`
- historical runner (blob): `7b46e0f6c805687977cd685ebb97741bd4243cbe`

These identities belong ONLY to historical CPU-era execution provenance (seed-01/02/04 lineage, pre-CUDA). They MUST NOT be cited as the prospective CUDA execution basis. Any prior citation of `7b46e0f6...` as a device-aware or prospective CUDA runner was incorrect and is superseded.

Do NOT claim Amendment 036 itself produced `7b46e0f6...`.

### 3.2 Prospective CUDA basis (normative for seed-05 and any future CUDA execution)

All identities below are validated and bound prospectively (no historical bytes are changed):

- recipe (commit): `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a` — "fix(runtime): close remaining CUDA execution escapes"
- runner (blob): `05b704b254387d8f5ffdf1d847dd4289303b565c` — `reports/research/evidence/structured_vol_v5_replicate_training_runner.py` (device-aware, runtime-bound)
- structured-vol experiment (blob): `16f5ec631eb71756084f3e74d006c31da2c6bcd8` — `src/neuralmarket/research/structured_vol_experiment.py`
- trainer (blob): `85aabc6798b22a60bd4d94d4ee86bfae81a8a172` — `src/neuralmarket/research/neural_sde_trainer_v3.py`
- Gate-v2 (blob): `05af8d0d864eddaae8c43e1cc3936d28e89abaf3` — Gate-v2 evaluator under spec `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469`
- authorization-v2 schema (blob): `c74958f2c5d99753b05bf64c9b6880ee9bd37d94` — `reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json`
- runtime-identity implementation (blob): `817ba53e2474c6e8dd7ecf15d64e0766e75f73e9` — `src/neuralmarket/core/runtime_identity.py`
- runtime-identity source path: `src/neuralmarket/core/runtime_identity.py` (canonical; not `src/neuralmarket/research/runtime_identity.py`)
- prospective runtime identity (SHA-256, runtime-identity-v1, normative capture point after `resolve_device` + `configure_device_determinism`, before `execution_started`): `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (`.venv-gpu` CUDA 13.2 / `torch 2.13.0+cu132` / driver `610.47` / `RTX 4070 Laptop GPU CC 8.9` / determinism enabled)

Effective combined contract after correction: exactly one unambiguous prospective CUDA basis (above) with historical CPU identities clearly separated.

## 4. Three-way member-inclusion semantics (blocking defect B — corrected)

Ambiguous use of "admissible" for sensitivity inclusion is replaced by three explicit statuses. Scientific Gate outcome is NOT an inclusion criterion; execution validity is.

### GATE_PASS_VALID

- governance-valid execution;
- protocol-valid execution;
- scientific Gate-v2 pass (all six criteria pass).

Required handling: INCLUDE in family summaries. INCLUDE in LOMO. INCLUDE in CPU-vs-mixed analysis. Report Gate result alongside member.

### GATE_FAIL_VALID

- governance-valid execution;
- protocol-valid execution;
- one or more scientific Gate-v2 criteria fail.

Required handling: INCLUDE in family summaries. INCLUDE in LOMO. INCLUDE in CPU-vs-mixed analysis. Report failed Gate criteria alongside member.

A scientifically poor result MUST NOT be an exclusion filter. Gate scientific outcome is not an inclusion criterion.

### GOVERNANCE_INVALID

- execution invalid because of governance/protocol failure (e.g., seed-03 `DOUBLE_SCIENTIFIC_INVOCATION` at `e333325c804d95d2`).

Required handling: retain permanently in scheduled-primary history and failure reporting; do NOT silently discard or relabel; exclude from VALID scientific-replicate numerical summaries because the execution itself is inadmissible. Reported separately in the family manifest per Amendments 021/022/032.

No post-result discretion is allowed. No scientific-outcome-dependent inclusion is permitted.

## 5. Family / LOMO / mixed-set wording (blocking defect B — corrected)

The following Amendment 040 phrasing equivalence is superseded:

- "N=3 if seed-05 fails/inadmissible"
- "plus seed-05 if admissible"
- "when seed-05 succeeds and is admissible"

wherever those phrases make scientific Gate outcome control inclusion.

Frozen replacement (unconditional, before results):

- If seed-05 is `GATE_PASS_VALID`: valid scientific set includes seed-05.
- If seed-05 is `GATE_FAIL_VALID`: valid scientific set STILL includes seed-05.
- If seed-05 is `GOVERNANCE_INVALID`: seed-05 is retained in failure history but excluded from valid-replicate numerical sensitivity summaries.

Thus after ANY governance-valid seed-05 execution, irrespective of Gate pass/fail:

- `VALID_RUNTIME_SENSITIVITY_SET`: seed-01 (cpu), seed-02 (cpu), seed-04 (cpu), seed-05 (cuda) — N=4
- `HISTORICAL_CPU_SUBSET`: seed-01 (cpu), seed-02 (cpu), seed-04 (cpu) — N=3

Mandatory LOMO after a governance-valid seed-05 execution: omit each of all four valid-execution members in turn (four LOMO recomputations per statistic). Mixed-runtime comparison after a governance-valid seed-05 execution: MUST include seed-05 even when its Gate result is scientifically poor. Section 5 of Amendment 040's "when seed-05 succeeds and is admissible" condition is removed; inclusion is unconditional on execution validity.

If seed-05 is `GOVERNANCE_INVALID`, the valid-replicate sensitivity set remains seed-01/02/04 (N=3) — governance-invalid seed-05 contributes only to failure-history reporting, not to sensitivity numerical summaries.

## 6. Seed-01 field mapping and RBF family-scalar exclusion (non-blocking gaps C/D — closed)

### 6.1 Explicit seed-01 mapping

Seed-01 evidence is `reports/research/structured_vol_v5_production_gate_v2.json`. For cross-member family scalars, map seed-01 as:

- `initial_selection_total_loss` ← `gate.criteria[id=1].initial_value` (historical value `8.628283500671387`) — verified equivalent to `training.initial_selection_total_loss` for seed-01.
- `best_selection_total_loss` ← `training.best_selection_total_loss` (verified value `0.5251655578613281` for seed-01).
- `best_epoch` ← `training.best_epoch`
- `final_epoch` ← `training.final_epoch`

Where naming translations are required across the gate/training_report schemas:

- `path_uniqueness` (Gate criterion 4) ↔ `path_uniqueness_fraction` in replicate `gate_diagnostics` — same criterion, verified value `1.0` where present.
- `acf1_agreement` criterion value (Gate criterion 5) ↔ `return_acf1_abs_diff` in replicate `gate_diagnostics` — same criterion value (`|generated_return_acf1 - real_return_acf1|`, band `[null,0.25]`).

Do not invent values. Any deviation in source field name across seeds is documented as an alias, not a new definition.

### 6.2 RBF decomposition exclusion (definitive)

Fields `initial_internal_rbf` / `best_internal_rbf` (and `initial_selection_signature_loss` / `best_selection_signature_loss` decompositions) are NOT comparable across seed-01/02/04:

- seed-01 production gate carries `initial_selection_signature_loss` / `best_selection_signature_loss` as internal-RBF-adjacent decompositions, but not `initial_internal_rbf` / `best_internal_rbf` as named in replicate training reports; seed-02/04 replicate reports carry `initial_internal_rbf` / `best_internal_rbf` as top-level keys.

Therefore:

- `initial_internal_rbf` / `best_internal_rbf` are EXCLUDED FROM CROSS-MEMBER FAMILY SUMMARY. No optional "exclude or member-specific with explicit N" choice remains; the exclusion is definitive and frozen now.
- Existing per-member decomposition fields may remain descriptive within individual evidence only (e.g., `training.best_selection_signature_loss` in seed-01 gate; `initial_internal_rbf` in replicate reports) but MUST NOT appear as family summary scalars in section 3 or in LOMO/CPU-vs-mixed tables.

Cross-member training summary scalars remain exactly the five in Amendment 040 section 3.1 (initial_selection_total_loss, best_selection_total_loss, best_epoch, final_epoch, selection_loss_improvement).

## 7. Runtime-identity source and stable RNG references (non-blocking gap E — corrected)

- Runtime-identity source path is `src/neuralmarket/core/runtime_identity.py` (blob `817ba53e2474c6e8dd7ecf15d64e0766e75f73e9`), not `src/neuralmarket/research/runtime_identity.py`. Schema remains `runtime-identity-v1`; SHA computation excludes the stored hash field; canonical JSON `sort_keys` / `separators (",", ":")`.

- For trainer RNG/device paths, reference stable symbol names rather than stale line numbers:

  `make_generator`, `train_internal_v3`, `refit_final_v3`, `evaluate_gate_v2`, `set_deterministic_seeds`, `resolve_device`, `configure_device_determinism`, `build_runtime_identity`

- Substantive RNG contract (unchanged, restated with stable references):

  Global seed path (`set_deterministic_seeds(model_init_seed)`) includes `random.seed`, `np.random.seed`, `torch.manual_seed`, `torch.cuda.manual_seed_all` — controls initialization and global RNG.

  Explicit per-device stochastic streams use `torch.Generator(device=device).manual_seed(data_seed)` via `make_generator` — used for training Brownian noise (`noise_gen`), minibatch/window permutation (`order_gen`), `selection_loss` stochastic paths (`noise_gen`), and refit noise/perm.

  Post-hoc simulation uses `simulate_structured(model, context, seed=eval_seed)` via `torch.Generator.manual_seed(eval_seed)`.

  Do NOT describe `torch.cuda.manual_seed_all` as the per-generator mechanism for per-device training streams; it is global RNG, while per-device streams use explicit `torch.Generator(device=...)` instances.

## 8. Combined effective contract verification

Amendment 040 plus this amendment 041 as a combined text have been inspected and contain before commit:

- one unambiguous prospective CUDA basis (section 3.2 identities) with historical CPU identities (`20d90f7...` / `7b46e0f6...`) clearly separated;
- `GATE_PASS_VALID` included in family summaries, LOMO, mixed-runtime;
- `GATE_FAIL_VALID` included in family summaries, LOMO, mixed-runtime;
- `GOVERNANCE_INVALID` retained in failure history and excluded from valid-replicate numerical summary;
- no scientific-outcome-dependent inclusion (search for "if admissible", "if seed-05 succeeds", "if seed-05 passes" confirms no remaining operative clause where Gate scientific outcome controls sensitivity inclusion; any historical occurrence in section 2 supersession list is explicitly marked superseded and non-operative);
- no optional RBF treatment;
- explicit seed-01 field mapping (section 6.1);
- unchanged frozen scalar set (section 3 of Amendment 040 per section 2 scope — same training 5 + Gate 5 + report-only 3);
- unchanged summary formulas (N/mean/SD-ddof1/median/min/max/CV-ratio-scale-only);
- unchanged LOMO formula (absolute = LOMO_mean - full_mean; relative = absolute/|full_mean| where meaningful);
- unchanged CPU-vs-mixed design (HISTORICAL_CPU_SUBSET N=3 vs VALID_RUNTIME_SENSITIVITY_SET N=4; backend-labelled; absolute/relative difference);
- unchanged no-causal-backend rule (3 vs 1 not balanced; no regression / causal claim);
- unchanged H2 caveat (backend variation disclosed; robust-language conditioned on qualitative similarity across CPU-only/mixed/LOMO; no post-hoc PASS/FAIL);
- unchanged no-rerun/discard/retune/redesign rules.

No Gate-v2 criterion, threshold, or statistic has been altered.

## 9. Preregistration timing and append-only

- This correction is frozen BEFORE seed-05 authorization, execution, Gate result, training curve, checkpoint, or any seed-05 scientific result is observed — same starting evidence as Amendment 040: starting HEAD `02c12ab` has no seed-05 v2 CUDA authorization (zero `authorization-v2` artifacts), no seed-05 execution markers (`reports/research/structured_vol_v5_replicates/1e8aa171993a1aba` absent), no training invocations for `12281`.
- No new seed-05 v2 authorization is created here; no `--execute`; no training; no validation; no external validation; no final-test access.
- Seed-03 remains `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` and retained.
- Successful seed-05 would still produce only four valid-replicate members (now under three-way semantics: `GATE_PASS_VALID` or `GATE_FAIL_VALID` both count toward the four); fifth admissible/member decision remains separately governed; under-filled-family policy (Amendment 022 section 11) still governs final-test blocking.
- Final test remains sealed (split `2023-11-22` onward per `split_manifest_v1`).

This amendment is append-only; Amendment 040 is unchanged.

## 10. What this amendment does NOT do

- Does not modify Amendment 040 file bytes.
- Does not change scientific source, model, hyperparameters, splits, loss, windowing, optimizer, Gate thresholds, or determinism.
- Does not create any authorization artifact or permit execution.
- Does not perform training, validation, external validation, final-test, hedging, reserve, provider, or network operation.
- Does not retroactively change historical CPU lineage bytes.

## 11. Required next action

Next task MUST independently audit Amendment 041 (read-only) before any seed-05 authorization artifact can be created. No execution may be inferred from this amendment alone. Audit must verify blocking defects A/B repaired (prospective CUDA basis and outcome-independent inclusion), scope not reopened, and zero new authorizations/executions.

---
*Amendment 041 is an append-only correction/supersession for Amendment 040. It repairs CUDA provenance, closes ambiguous inclusion wording via three-way member semantics with mandatory inclusion of governance-valid Gate-failing seed-05, and closes non-blocking seed-01 mapping and RBF exclusion gaps. All unaffected Amendment 040 clauses remain normative.*
