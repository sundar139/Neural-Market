# Research Protocol Amendment 022

## V5 Five-Replicate Numerical Schedule and Under-Filled-Family Policy

**Date:** 2026-08-19
**Status:** SCHEDULE — append-only numerical schedule. No training. No validation. No final-test access.
**Task:** NM-R4-V5-SEED-SCHEDULE-026
**Prior:** NM-R4-V5-REPLICATE-SEED-CONTRACT-024 → contract commit `421508f2502e363c0a6573c445ab9bd3e056a5b6`; Amendment 021 `4ad94bceed70bb70a282bc472b97bc5fd0aad8bffb856d18bad3743c4bd822c2`; replicate seed contract `c28eb6d8d8de89381de9ff28b697c8190d1910af87612a57bbe9df768aa0c98f`; family methodology identity `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`. Audit 025 — VALIDATED WITH NON-BLOCKING FINDINGS, five-seed numerical schedule AUTHORIZED. External validation CLOSED 2/2, third FORBIDDEN.
**Authority:** Amendment 021 remains unchanged; this amendment freezes only schedule-level details.

---

## 1. Purpose

Freeze the prospective numerical five-member v5 training schedule — the four `replicate_seed` values for members #2–#5 — before any additional training, plus the under-filled-family consequence and the reserve branch derivation, all without training, validation, or final-test data. No outcome from members #2–#5 was observed when this schedule was chosen.

## 2. Audit-025 authorization

Independent audit NM-R4-V5-REPLICATE-SEED-CONTRACT-AUDIT-025: contract VALIDATED WITH NON-BLOCKING FINDINGS; numerical schedule AUTHORIZED; training NOT AUTHORIZED; reserve execution NOT AUTHORIZED; validation/final-test/hedging NOT AUTHORIZED. This amendment exercises only the numerical-schedule authorization.

## 3. Frozen replicate contract (unchanged)

- Load-bearing contract: `reports/protocol/research_protocol_amendment_021.md` (`4ad94bceed70bb70a282bc472b97bc5fd0aad8bffb856d18bad3743c4bd822c2`) and `reports/research/structured_vol_v5_replicate_seed_contract_v1.json` (`c28eb6d8d8de89381de9ff28b697c8190d1910af87612a57bbe9df768aa0c98f`).
- Minimum varying training set: `{model_init_seed, data_seed}` (§4 of Amendment 021, traced to `set_deterministic_seeds` + `noise_gen/order_gen` data_seed generators).
- Canonical derivation: `model_init_seed = replicate_seed`, `data_seed = replicate_seed + 1` (§5).
- Evaluation policy: `eval_seed = 8283` `COMMON_FIXED_POST_TRAINING` (§8); gate seeds `7777/7778/8801` fixed COMMON (§8).
- Family methodology invariants: architecture `StructuredVolatilityNeuralSde` state 2 / brownian 2, level-3 lead-lag, RBF-MMD with training-fit standardizer/bandwidth, `dt 1/252 horizon 63`, same splits/optimizer/gate (Amendment 021 §9).
- Failed-seed and reserve ordering policy per Amendment 021 §§10–11.
- This schedule adds no new methodology and changes no scientific code.

## 4. Seed-domain bound

```
replicate_seed_min = 0
replicate_seed_max = 4294967295   # NumPy binding
model_init_seed    = replicate_seed
data_seed          = replicate_seed + 1
```

All scheduled primaries are far inside the range. For this v1 family, all derived training seeds must be accepted by actual Python / NumPy / PyTorch entry points before training authorization (verified §12: all 10 seeds accepted by `random.seed`, `numpy.random.seed`, `torch.Generator.manual_seed`). No seed may be changed after schedule commit merely because a later run performs poorly.

## 5. Primary numerical schedule (prospective, outcome-independent)

Chosen before members #2–#5 were trained, before any seed #2–#5 Gate-v2 outcome, before final-test access, after Audit 025, without validation reopening, without observing any future-member outcome.

**Derivation rule:** `replicate_seed(k) = 8281 + 1000 * (k - 1)` for `k = 1..5`. The rule is descriptive of the frozen five — it does not authorize automatic extension to more primaries.

| member | replicate_seed | model_init_seed | data_seed | eval_seed | eval policy | role | status |
|--------|---------------|-----------------|-----------|-----------|-------------|------|--------|
| v5-seed-01 | 8281 | 8281 | 8282 | 8283 | COMMON_FIXED | PRIMARY | EXISTING_FROZEN |
| v5-seed-02 | 9281 | 9281 | 9282 | 8283 | COMMON_FIXED | PRIMARY | SCHEDULED_NOT_RUN |
| v5-seed-03 | 10281 | 10281 | 10282 | 8283 | COMMON_FIXED | PRIMARY | SCHEDULED_NOT_RUN |
| v5-seed-04 | 11281 | 11281 | 11282 | 8283 | COMMON_FIXED | PRIMARY | SCHEDULED_NOT_RUN |
| v5-seed-05 | 12281 | 12281 | 12282 | 8283 | COMMON_FIXED | PRIMARY | SCHEDULED_NOT_RUN |

No `v5-seed-02..05` has been trained. Schedule rationale: simple arithmetic spacing of 1000 from historical `8281` to avoid all cross-role training-seed collisions. The values are not scientifically privileged.

Member #1 identity (unchanged):
`checkpoint_final.pt` SHA `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4`, selected `checkpoint.pt` SHA `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f`, training curve `e29f2afcdff75e151ca6a85f3c77e7a209a3c1827b6d1abcb191ce36c6d30a2d`, config_hash `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157`.

## 6. Collision proof

Derived training-seed multiset (10 values):

```
8281, 8282, 9281, 9282, 10281, 10282, 11281, 11282, 12281, 12282
```

- Count 10, unique 10 — PASS.
- No `model_init_seed` equals any other member's `data_seed` — empty intersection, PASS.
- No derived training seed equals `eval_seed 8283`, `gate 7777`, `diagnostic 7778`, `bootstrap 8801` — PASS.

All seeds verified accepted by Python/NumPy/PyTorch generators (§12).

## 7. Common evaluation policy

`eval_seed = 8283` — classification `COMMON_FIXED_POST_TRAINING` (all five members same). This does not make training dependent; training independence is carried by `{model_init_seed, data_seed}` per §5. It does not create five independent evaluation-noise realizations; later SAP must not treat the common draw as an independent replicate dimension.

Gate-v2 seeds remain common and fixed for all members: `7777` model paths / `7778` diagnostic / `8801` bootstrap. They are evaluation/gate randomness, not training independence.

## 8. Fixed Gate-v2 randomness

Common and fixed across the family: `7777 / 7778 / 8801` (Amendment 016 provenance). No member changes them.

## 9. Reserve derivation frozen before training

Audit 025 requires any reserve values or derivation algorithm frozen before any primary training. No reserve execution authorized here.

**Frozen deterministic algorithm:**

```
reserve_replicate_seed(j) = 12281 + 1000 * j   for positive integer j
```

Initial reserve capacity for this family: `j = 1,2,3`

| reserve slot | replicate_seed | model_init_seed | data_seed | eval_seed | order |
|--------------|---------------|-----------------|-----------|-----------|-------|
| reserve-j01 | 13281 | 13281 | 13282 | 8283 | 1st |
| reserve-j02 | 14281 | 14281 | 14282 | 8283 | 2nd |
| reserve-j03 | 15281 | 15281 | 15282 | 8283 | 3rd |

No reserve artifacts created. No reserves trained. No manual substitution allowed. For every reserve, if ever separately authorized: derive `model_init_seed = reserve_replicate_seed(j)`, `data_seed = reserve_replicate_seed(j)+1`, `eval_seed = 8283`. Before any reserve execution, a later governed task must materialize and verify the exact tuple and confirm no collisions with primary seeds or earlier reserves.

Reserve execution order is strictly `j=1, then 2, then 3` only as needed. No skipping. No outcome-based selection.

## 10. Primary failure semantics

The five primary members are permanent. A primary failure remains in the roster forever, keeps its exact seed tuple, is counted in `primary_attempted` and `failed_in_primary`, is never silently discarded, never relabelled as a reserve, never erased if a reserve later completes.

Required primary counters (frozen definitions):

- `primary_scheduled = 5`
- `primary_attempted` (runs actually attempted; increases only after attempt starts)
- `primary_valid_completed` (valid checkpoints per frozen failure criteria; 0..5)
- `failed_in_primary = primary_attempted intersect not valid` ultimately `5 - primary_valid_completed` once PRIMARY_COMPLETE

No reserve counts as a successful primary.

## 11. Under-filled-family policy

Definitions:

- `PRIMARY_COMPLETE`: all five primary runs have been attempted.
- `PRIMARY_FULLY_VALID`: `primary_valid_completed == 5`.
- `PRIMARY_UNDERFILLED`: `PRIMARY_COMPLETE` and `primary_valid_completed < 5`.

Frozen consequence if `PRIMARY_UNDERFILLED`:

- H2 remains NOT PROVEN.
- H3 / final-test authorization remains BLOCKED.
- No result may silently use only valid primaries and call that the original five-seed primary family.
- Reserve models, if later separately authorized, are reported separately from the primary roster and do not retroactively fill the primary count.
- A later SAP must explicitly define whether reserves can contribute to a completed-model estimator while retaining primary failure-rate reporting.
- No decision may be made after seeing failures about whether to ignore them. No post-hoc narrowing allowed.

Therefore no final-test authorization is possible from an under-filled primary family until that treatment is independently frozen and audited.

## 12. Prospective config identities

Without training and without editing the frozen base config (`configs/research/structured_vol_neural_sde_v5.yaml`), effective in-memory configs differing only in `training.model_init_seed` / `training.data_seed` (eval stays `8283`) were constructed and hashed via `V5ExperimentConfig.config_hash()`:

| member | replicate | model_init | data | full config_hash | run prefix (16) |
|--------|-----------|------------|------|------------------|-----------------|
| v5-seed-01 | 8281 | 8281 | 8282 | `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157` | `5bdbaabd2fb257a7` |
| v5-seed-02 | 9281 | 9281 | 9282 | `62c7406cb3a2c64237d39559370d70a27f8111f7dd1dc7ee581da9bd475cf00b` | `62c7406cb3a2c642` |
| v5-seed-03 | 10281 | 10281 | 10282 | `e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955` | `e333325c804d95d2` |
| v5-seed-04 | 11281 | 11281 | 11282 | `77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b` | `77e7de9efabb7ce3` |
| v5-seed-05 | 12281 | 12281 | 12282 | `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897` | `1e8aa171993a1aba` |

- Each full config_hash unique — PASS (5/5 distinct).
- Each 16-char run prefix unique — PASS (5/5 distinct).
- `family_methodology_identity` remains `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` for all five (verified per-member recomputation; RNG-stripped canonical hash).
- No checkpoint directories created merely to test this.

Reserve prospective identities (derivation only, not scheduled primaries): `j=1 13281 → hash pending at reserve task; j=2 14281; j=3 15281` (algorithm frozen; hashes not persisted until needed).

## 13. Completed-family manifest requirement

A later completed-family manifest must have its own separately versioned schema (not this schedule's `structured-vol-v5-seed-schedule-v1`). It will aggregate five per-member records (selected checkpoint, curve, final-refit checkpoint, Gate-v2 six metrics, failure status, counters, evidence hashes) plus family counts `primary_valid_completed/failed_in_primary` and `family_methodology_identity`.

Execution-provenance mandate (from Audit 025 minor finding): every future member execution must freeze/record the exact runner or execution-harness SHA/blob **before interpreter start**. Do not create that runner here.

No training harness is implemented in this amendment.

## 14. External-validation firewall

`external_validation_state: CLOSED`, `construction_count: 2`, `effective_max: 2`, `third_construction_permitted: false` (Amendments 018/019, closure `fd142ada...`).

- Member #1: existing report-only external evidence (`reports/research/structured_vol_v5_external_validation_confirmatory.json` `a28345587989ea1d91d46ed7c9b332151b84af98c0d4918f0fc281d03ba4ca38`).
- Members #2–#5: no external evidence.
- Reserves: no external evidence.
- Transfer: forbidden (no statement may imply member #1 evidence transfers to family members #2–#5 or reserves).
- No validation reconstruction.

## 15. Authorization state after schedule freeze

- numerical_schedule: **FROZEN**
- members_2_to_5_training: **NOT_AUTHORIZED**
- reserve_training: **NOT_AUTHORIZED**
- validation: **NOT_AUTHORIZED**
- final_test: **NOT_AUTHORIZED**
- hedging: **NOT_AUTHORIZED**

Next required step: independent read-only audit of this numerical schedule and prospective config identities before any training authorization.

## 16. Prohibited actions (this schedule)

- Training any scheduled member or reserve.
- Mutating trainer/model, frozen base config, or existing checkpoint.
- Selecting future seeds outside the frozen five or skipping to a later reserve.
- Outcome-based seed substitution or post-hoc under-filled reinterpretation.
- Any validation construction, final-test access, or hedging.
- Changing family methodology or member #1.

---

*Amendment 022 is append-only schedule details. Amendment 021 remains unchanged. Any future training requires a separately authorized task after independent audit of this schedule. No training harness is implemented here.*
