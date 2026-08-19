# Research Protocol Amendment 021

## Five-Replicate RNG Independence and Family Evidence Contract

**Date:** 2026-08-19
**Status:** CONTRACT — append-only seed-independence repair. No training. No validation. No final-test access.
**Task:** NM-R4-V5-REPLICATE-SEED-CONTRACT-024
**Supersedes:** One operational sentence in Amendment 020 (model_init_seed-only variation). Amendment 020 otherwise remains intact.
**Audit basis:** NM-R4-ORIGINAL-CONTRACT-RECONCILIATION-AUDIT-023 — REPAIR REQUIRED (reconciliation reasoning validated; single load-bearing defect: replicate independence requires {model_init_seed, data_seed}).
**Prior lineage:** NM-R4-ORIGINAL-CONTRACT-RECONCILIATION-022 → reconciliation commit `4610ede77e066356ea076f368f965b9ac80eb930`; Amendment 020 SHA `43243dd345c5f98b92591174349ee3f42236b08ce689330f5a82c4a8d7c08ba4`; closure `9764bc2` (CLOSED 2/2, third FORBIDDEN).

---

## 1. Purpose

This amendment repairs the five-seed operational contract **before** any of the four additional v5 training replicates is selected or executed. It freezes what constitutes one independent training replicate, how one canonical `replicate_seed` deterministically produces the required training seeds, and how the five-member family will be evidenced. No numeric seed values for members #2–#5 are chosen here. No model code is changed. The frozen v5 config used by member #1 is untouched.

## 2. Audit finding requiring correction

Amendment 020 §4.1 and §6 operationally prescribed:

> "train four additional v5 instances under the identical frozen methodology … each from a fresh independent model_init_seed"

An independent audit (023) traced the repository RNG wiring and proved that sentence is incorrect: `model_init_seed` controls only initialization, while `data_seed` controls the stochastic training trajectory itself. Changing only `model_init_seed` leaves minibatch order, Brownian noise, selection-loss stochasticity, and refit stochasticity shared.

**Correction was made before any additional replicate training. No scientific outcome from future seeds influenced it. Amendment 020's broader reconciliation (H1/H2 mapping, Strategy B, sigkernel/solver classifications, priority ordering) remains valid.**

## 3. Original five-seed requirement (recap)

Source: `reports/protocol/research_protocol_v1.md` line 99 at commit `349a5b3` — normative: "All neural comparisons use at least five independent seeds" (governance threshold, not preference). Companion rules: failed seeds reported not silently discarded (line 100); training-seed vs market-period uncertainty reported separately (line 105); hedging primary endpoint requires "not driven by one seed or one isolated market period" (lines 77–86, all required). Applies to H1 and H2 jointly, load-bearing for H2 and H3. See Amendment 020 §2.4.

## 4. Actual RNG wiring (traced at 4610ede, no execution)

Verified from frozen config `configs/research/structured_vol_neural_sde_v5.yaml` (8281/8282/8283) and sources:

- `src/neuralmarket/models/neural_sde.py:26` `set_deterministic_seeds(seed)` → `random.seed`, `np.random.seed`, `torch.manual_seed`, `torch.cuda.manual_seed_all`.
- `src/neuralmarket/research/structured_vol_experiment.py:213` and `:279` — `set_deterministic_seeds(config.training.model_init_seed)` at train start and at refit reinit. Therefore **model_init_seed** controls: Python random, NumPy, torch global (CPU/CUDA) seeds, and thus **parameter initialization** (and any other global RNG draw before training generators are created).
- `src/neuralmarket/research/neural_sde_trainer_v3.py:218-219` and `367-368` (and identically `neural_sde_trainer.py:188-189, 320-321` and `neural_sde_trainer_v2.py:265-266, 419-420`): `noise_gen = torch.Generator().manual_seed(config.data_seed)` and `order_gen = torch.Generator().manual_seed(config.data_seed)`. Used as: `torch.randperm(n_fit, generator=order_gen)` (minibatch/window permutation, §4 line 207/325), `torch.randn(..., generator=noise_gen)` (training Brownian noise, line 213/330), `selection_loss()` which calls `evaluate_signature_loss(..., noise_gen)` (selection-loss stochastic paths, line 192/268), and refit loop identical (lines 320-326, 330-337). Therefore **data_seed** controls: **training Brownian noise, minibatch/window permutation, epoch-wise selection-loss stochasticity, refit batch order, refit Brownian noise**.
- `src/neuralmarket/models/structured_vol_sde.py:270-283` `simulate_structured(model, context, seed)` — `torch.Generator.manual_seed(seed)` + `torch.randn(..., generator=gen)` for post-hoc generation. Config `eval_seed` and top-level `n_eval_paths/eval_seed` (`structured_vol_experiment.py:80, 105-108`) are read only at evaluation time (lines 324-326: `simulate_structured(final_model, ctx_tensor, seed=config.eval_seed)`). **eval_seed** is post-training/post-hoc evaluation only; it participates in no training-time or Gate-v2 computation.
- Gate-v2: `configs/research/neural_sde_internal_gate_v2.yaml` gate seeds `7777` (model paths) and `7778` (drift/diffusion diagnostic), formalized in Amendment 016 §4 with no semantic change; bootstrap `8801` lineage (external validation harness and Amendment 016 bootstrap seed `8801`, diagnostic `8802` rejected — gate now 7777/7778). Gate seeds are fixed, not training replicate seeds.

### Minimum varying TRAINING RNG set

```
{ model_init_seed, data_seed }
```

Both must vary for a fully independent stochastic training replicate. Shared `data_seed` across members does **not** produce independent replicates.

## 5. Canonical replicate identity and deterministic derivation

Each family member has exactly one canonical `replicate_seed`. The two training seeds are derived deterministically:

```
model_init_seed = replicate_seed
data_seed       = replicate_seed + 1
```

Properties verified for member #1 before adoption:

- `replicate_seed = 8281` reproduces the historical training tuple exactly: `model_init_seed = 8281`, `data_seed = 8282` (as committed in `configs/research/structured_vol_neural_sde_v5.yaml` training 8281/8282).
- Derivation is minimal, bijective, and monotone; no hidden constraint makes it unsafe (seeds are valid for `random`, `numpy`, and `torch.Generator.manual_seed`; addition by 1 stays within generator range; no sibling uses these values yet).
- No member's `model_init_seed` may equal another member's `data_seed` — the `+1` rule guarantees the sets interleave but the explicit schedule constraint below forbids cross-member collision (each member's `+1` must not match another member's base).

Future schedule constraints (enforced before training, not after outcomes):

- All `replicate_seed` values unique.
- All `model_init_seed` values unique.
- All `data_seed` values unique.
- No member's `model_init_seed` equals any member's `data_seed` (i.e., the 10 derived seeds across the family are pairwise distinct).
- Derived seeds valid for Python/NumPy/PyTorch generators.
- Schedule frozen before any member #2–#5 training begins.
- Schedule not selected based on training outcomes.

No `replicate_seed` values for members #2–#5 are chosen in this amendment.

## 6. Existing member #1 (no retraining)

- member_id: `v5-seed-01`
- replicate_seed: `8281`
- model_init_seed: `8281`
- data_seed: `8282`
- eval_seed: `8283` (per §7 COMMON/FIXED policy)
- existing: `true`
- checkpoint_final: `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint_final.pt` SHA `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4`
- selected checkpoint: `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint.pt` SHA `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f`
- training curve: `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/training_curve.json` SHA `e29f2afcdff75e151ca6a85f3c77e7a209a3c1827b6d1abcb191ce36c6d30a2d`
- config_hash: `5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157` (replicate-specific; see §8 for family methodology identity)
- training-series SHA and Gate-v2 evidence as already frozen for this member; not recomputed here

## 7. Future members #2–#5

For members #2–#5 this amendment records only placeholders:

```
v5-seed-02  UNSCHEDULED  (no replicate_seed, no derived seeds)
v5-seed-03  UNSCHEDULED
v5-seed-04  UNSCHEDULED
v5-seed-05  UNSCHEDULED
```

No numeric `replicate_seed` for #2–#5. The next governed task after independent audit of this contract will freeze the actual five-member seed schedule deterministically.

## 8. Evaluation-seed policy (frozen)

`eval_seed` participates in **no** training-time or Gate-v2 computation (verified §4). It is post-hoc simulation only (generation `1024 × 63`, horizon 63, initial price `final training-session close`).

**Policy: `eval_seed = 8283` COMMON/FIXED across all five family members.**

Rationale:

- Training independence is carried entirely by `{model_init_seed, data_seed}`.
- A common evaluation seed provides common-random-number comparability across training replicates (same post-hoc Monte Carlo draw for scoring), so inter-replicate score differences isolate training variability.
- Evaluation Monte Carlo noise is not confounded with training-seed uncertainty.

If later evidence contradicted post-hoc-only status, the simplest evidence-supported alternative would be documented via a new amendment — but current wiring makes the common-eval policy the evidence-supported choice.

Gate seeds remain fixed for all members: `7777` (model paths) / `7778` (drift/diffusion diagnostic) / `8801` (bootstrap reference, validated). No member changes them.

## 9. Scientific methodology invariants for all five members

Every future member MUST use the SAME scientific methodology as member #1 — only replicate RNG identity may vary:

- Architecture: `StructuredVolatilityNeuralSde` — `state_dim 2`, `brownian_dim 2`, `n_context 4`, `hidden_units 64`, `hidden_layers 2`, `SiLU`, `diffusion_epsilon 1e-6`
- Objective: finite level-3 lead-lag truncated signature via Chen identity + per-vector RBF-MMD (`signature.py` + `signature_mmd.py`, biased MMD² Gretton) with training-fit standardizer (`floor_eps 1e-8`) and `median_pairwise_squared_distance` bandwidth (`max_vectors 512`), plus anti-collapse `log_variance_penalty_per_path` (`coeff 1.0`, `eps 1e-12`)
- Simulator: Euler–Maruyama / Itô-style, `dt 1/252`, `horizon 63`, `n_eval_paths 1024`, `eval_initial_price_convention final training-session close`
- Data: same `training` split identity (926 sessions), same `split_fit_selection` `fit_fraction 0.8`, same `WindowSpec` (context_lookback 22)
- Training: same optimizer `AdamW lr 1e-3 weight_decay 1e-6 batch 64 max_epochs 400 patience 40 grad_norm_clip 1.0`, same model-selection rule, same final-refit procedure (`epochs = best_epoch`)
- Gate-v2: same six exact criteria (Amendment 016 §4) under same gate seeds `7777/7778/8801`
- No hyperparameter change between members.

`V5ExperimentConfig.config_hash` includes `sde + training + windows + objective + n_eval_paths + eval_seed`, so a seed-derived copy naturally gets a new replicate-specific `config_hash`/run prefix — that is expected and identifies the replicate.

A separate **family_methodology_identity** is defined for the family manifest: the canonical hash of the scientific config with replicate-RNG fields (`training.model_init_seed`, `training.data_seed`, top-level `eval_seed` if kept replicate-specific — here fixed) stripped/replaced by a placeholder. The remaining scientific fields must be byte-identical across all five members. Do not modify `V5ExperimentConfig.config_hash` semantics; the family hash is computed only inside the replicate-family contract/manifest.

## 10. Failed-seed policy

Grounded in original protocol:

> "Failed seeds must be reported and may not be silently discarded." — `reports/protocol/research_protocol_v1.md` line 100 (normative).

Failure criteria are the already-frozen criteria (v1 lines 108–120 and Gate-v2 governance), at minimum:

- nonfinite training or validation/selection loss;
- no valid checkpoint;
- nonfinite generated paths above frozen `>0.1%` tolerance (v1 line 113);
- terminal-dispersion collapse below 10% of real-data dispersion (v1 line 114–115);
- generated volatility exceeding `10×` training reference without documented stress-test reason (v1 lines 116–117);
- unresolved data-leakage violation;
- unreconciled accounting/provenance error.

No outcome-dependent new failure criteria may be invented after seeing results.

**Primary family:** exactly five pre-scheduled primary replicate slots (`v5-seed-01` … `v5-seed-05`). A failed primary member remains permanently recorded — retains member ID and unique seed tuple, is included in failed-seed reporting, is never deleted/relabelled, never replaced silently, never dropped from the family roster.

**Replacement/reserve policy:**

- No reserve seed values are chosen in this amendment.
- Reserve seeds, if used at all, must themselves be frozen **before** the primary training batch begins (or via a separately pre-authorized deterministic reserve schedule with predeclared execution order).
- Reserves execute only in predeclared order and only if needed.
- A reserve never erases the failed primary; the failed member's record stays.
- Failure count/rate continues to include every failed primary.
- Replacement cannot be selected based on favorable/unfavorable outcomes (no outcome-picking).

**Does "five" mean five attempted or five valid?** The original text does not decide explicitly. This contract requires both counts to be recorded separately:

- `primary_attempted = 5` (always five scheduled)
- `primary_valid_completed = 0..5`
- `failed_in_primary = 5 - completed`

The later hedging SAP must state which denominator is used for each claim. Ambiguity must not be resolved by hiding failures.

## 11. Required per-member evidence (all five replicates)

Every future training replicate must persist, at minimum (no validation or final-test metrics):

- member ID, `replicate_seed`, `model_init_seed`, `data_seed`, `eval_seed` and the frozen eval policy flag (`COMMON_FIXED`)
- starting Git HEAD, scientific source commit (`357971a67c68492fc0c4f5bf31f94f9685639f65` for current lineage), Python version, PyTorch version, device (`cpu`), determinism state
- full effective `V5ExperimentConfig` (as dict), replicate-specific `config_hash`, and `family_methodology_identity` (RNG-stripped methodology hash)
- `training-series SHA` (`4863b2cc…68669c` lineage) / fit/selection window identities (split derived from `training` returns + `WindowSpec`)
- `selected checkpoint` path + SHA, `training curve` path + SHA, `final-refit checkpoint` path + SHA (final-refit persisted separately from selection checkpoint)
- `initial selection loss`, `best selection loss`, `best_epoch`, `final_epoch` (from `train_internal_v3` outcome)
- **Gate-v2** six exact metrics and per-criterion pass/fail (Amendment 016 §4) under fixed gate seeds
- failure status and failure reason if any (per §10)
- training start/end UTC, process exit code, training invocation count
- forbidden-operation counters if available (validation/final-test counts must remain zero — external validation is CLOSED)

No raw validation values. No final-test metrics.

## 12. Family-level evidence structure

Machine-readable companion contract/schema for the eventual family manifest:

Preferred artifact: `reports/research/structured_vol_v5_replicate_seed_contract_v1.json` (JSON chosen for consistency with existing closure/manifest artifacts `structured_vol_v5_external_validation_closure.json` and reproducibility evidence).

Required top-level fields:

- `schema_version` / `version`
- `task_lineage` (`4610ede` → `NM-R4-V5-REPLICATE-SEED-CONTRACT-024` → `Amendment 021`)
- `original_protocol_source` (`reports/protocol/research_protocol_v1.md @ 349a5b3`, five-seed line 99)
- `amendment_020_reference` (SHA `43243dd345c5f98b92591174349ee3f42236b08ce689330f5a82c4a8d7c08ba4`)
- `amendment_021_reference` (this file)
- `family_size: 5`
- `methodology_identity` (family_methodology_identity, RNG-stripped)
- `replicate_derivation_rule` (`model_init_seed = replicate_seed`, `data_seed = replicate_seed + 1`)
- `eval_seed_policy` (`COMMON_FIXED 8283`)
- `fixed_gate_seeds` (`7777 / 7778 / 8801`)
- `member_01` complete identity (§6)
- `members_02_to_05: UNSCHEDULED` (no numeric seeds)
- `primary_vs_reserve_semantics` + `failed_seed_policy` (§10)
- `required_evidence_fields` (§11)
- `family_aggregation_boundary` (§13)
- `uncertainty_separation` (§14)
- `external_validation_policy` (CLOSED 2/2, third FORBIDDEN)
- `final_test_policy` (NOT AUTHORIZED)
- `hedging_SAP_dependencies` (SAP must exist before final-test access)

No future numerical seeds are populated here.

## 13. Family aggregation boundary (generator-family evidence before hedging SAP)

Allowed before the hedging SAP:

- per-member metrics (training loss curves, Gate-v2 diagnostics, stylized-fact families if computed on fit/selection only);
- `failed_in_primary` / `completed_in_primary` counts;
- descriptive family summaries already needed for diagnostics: median, IQR, range, per-family rank distribution — reported descriptively, not as a hypothesis test.

Not allowed yet:

- overall `H1 PASS` / `H2 PASS`;
- family winner;
- post-hoc weighted score;
- dropping failed runs from denominator;
- external-validation aggregation.

The later hedging SAP must choose the family estimator design **before** final-test access (one hedger per generator seed vs pooled synthetic paths vs another pre-registered design). That estimator is a mandatory SAP decision, not defined here. Sibling Amendment 019's external-validation rank boundary (no aggregate H1/H2) remains in force.

## 14. Training-seed vs market-period uncertainty separation

Original protocol `reports/protocol/research_protocol_v1.md` line 105 (normative): "Market-period uncertainty and training-seed uncertainty are reported separately."

- **Training-seed dimension:** five primary replicate identities/outcomes (`v5-seed-01` … `v5-seed-05`), with failures preserved, under the common eval seed so Monte Carlo noise does not contaminate the estimate.
- **Market-period dimension:** handled only by the later frozen hedging SAP using its dependence-aware procedure (paired, block/dependence-aware, Holm, turnover/position QC — per v1), not by mixing training replicates into a single pooled bootstrap.

Never pool the two into a single bootstrap dimension. Do not define the final inferential estimator here unless already normative; instead require the later SAP to consume the family manifest and state the exact estimator before final-test access.

## 15. Closed external-validation relationship

- External validation is CLOSED — `external_validation_state: CLOSED`, `external_validation_evidence: VALIDATED`, constructions `2/2`, `effective_max_governed_validation_constructions: 2`, `third_construction_permitted: false` (Amendments 018/019, closure `fd142ada...`).
- **Member #1** has the existing report-only external-validation evidence: `reports/research/structured_vol_v5_external_validation_confirmatory.json` (`a28345587989ea1d91d46ed7c9b332151b84af98c0d4918f0fc281d03ba4ca38`) — per-family baseline-relative ranks, no aggregate.
- **Members #2–#5 will have NO external-validation evidence.** Training robustness for the family is established from training/selection, Gate-v2, and later separately governed analyses — not from validation reuse.
- No statement in any report or manuscript may imply member #1's external-validation result transfers to members #2–#5. A per-member validation would be member-specific and, under the closed arm, cannot be constructed. A family-level external-validation claim from single-member evidence is forbidden.

No construction #3. No validation reopening.

## 16. Final-test status

`final_test_authorized: false`. No final-test construction, no final-test data access, no SAP execution on held-out data, and no hedging evaluation is authorized by or within this contract. The five-seed prerequisite (§5–§11) and the hedging SAP (Amendment 020 §7 / this amendment §13–§14) must both be frozen and independently audited before any final-test access decision.

## 17. What this amendment does not do

- Does not choose numeric `replicate_seed` values for members #2–#5 — next governed task after audit of this contract will freeze the actual five-member schedule.
- Does not authorize training, validation, simulation, or hedging.
- Does not modify scientific code, frozen v5 config (`configs/research/structured_vol_neural_sde_v5.yaml`), checkpoint bytes, model identity, or data.
- Does not install `sigkernel`, `torchsde`, or any dependency.
- Does not declare H1/H2 accepted or rejected.

## 18. Next governed decision

The next governed task must be exactly one implementation/decision step from the ordered roadmap after independent audit of this contract: **freeze the actual five-member `replicate_seed` schedule** (four numeric values for #2–#5 respecting §5 uniqueness + their derived `model_init_seed`/`data_seed` pairs and family methodology identity) before any training authorization. No training or final-test access until that schedule and its audit are complete.

## 19. Prohibited actions (this contract)

- Varying only `model_init_seed` for independence — corrected to `{model_init_seed, data_seed}`.
- Selecting future `replicate_seed` values inside this task.
- Outcome-dependent failure replacement or silent rerolling.
- Implying external-validation evidence transfers to members #2–#5.
- Any scientific execution (training, validation construction, final-test access, simulation, hedging, dependency install).

---

*Amendment 021 is append-only. Amendments 017, 018, 019, and 020 remain unchanged except for the explicit supersession of the single sentence identified in §2. Any future final-test access requires a separate, explicitly authorized task.*
