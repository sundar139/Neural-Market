# Research Protocol Amendment 020

## Original Research Contract Reconciliation Before Final-Test Authorization

**Date:** 2026-08-19
**Status:** DECISION — append-only reconciliation. No scientific code change. No validation construction. No final-test authorization.
**Task:** NM-R4-ORIGINAL-CONTRACT-RECONCILIATION-022
**Prior closure:** NM-R4-V5-EXTERNAL-VALIDATION-CLOSURE-021 (final closure commit `9764bc2c6c42603b90c5537480885b977f7693b9`; external-validation state CLOSED, evidence VALIDATED, governed constructions 2/2, third FORBIDDEN, final test NOT AUTHORIZED).
**Evidence-audit:** NM-R4-V5-EXTERNAL-VALIDATION-EVIDENCE-AUDIT-020 (VALIDATED WITH NON-BLOCKING FINDINGS).

---

## 1. Purpose and governing rule

This amendment reconciles the original research plan against the current implemented v5 methodology to determine whether the frozen v5 candidate can scientifically proceed toward the sealed final chronological test. It authorizes no model change, no retraining, no external-validation reconstruction, no final-test access, and no hedging. Every numerical result it cites is sourced from already-immutable frozen evidence; it performs only hashes and identity checks.

The governing rule is: do not automatically treat a divergence as requiring implementation, and do not automatically treat it as implying an amended methodology — decide based on whether the original hypothesis depends materially on the requirement.

## 2. Original research contract — grounded sources

**Earliest authoritative source:** `reports/protocol/research_protocol_v1.md` at commit `349a5b3` (chore: initialize reproducible research foundation). No hypothesis, endpoint, or success metric has been silently changed since v1; hypotheses H1–H5 and all governance rules below are normative in the original contract.

**Exact chronological splits (Amendment 001, base `349a5b3`, frozen at `81064f9`):** `data/manifests/split_manifest_v1.json` hash `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` (generated via `neuralmarket data split freeze` on XNYS calendar 4.13.2). Frozen splits:

| Split | Dates | Sessions |
|-------|-------|----------|
| Training | 2018-05-01 — 2021-12-31 | 926 |
| Excluded boundary | 2022-01-03 — 2022-05-25 | 100 (90 purge + 10 embargo) |
| Validation | 2022-05-26 — 2023-06-30 | 275 |
| Excluded boundary | 2023-07-03 — 2023-11-21 | 100 |
| Final test (sealed) | 2023-11-22 — 2025-12-31 | 528 |

Purge rationale and `final_test_access_status = "sealed"` are part of the frozen contract (Amendment 001).

### 2.1 Hypotheses — exact language (v1)

- **H1 (generator fidelity):** "the signature-score neural SDE reproduces financial path structure more faithfully than classical and adversarial baselines."
- **H2 (training stability):** "the signature-score training objective is more stable across seeds and epochs than adversarial (WGAN) training."
- **H3 (cost-aware hedging):** "deep hedging on signature-score synthetic paths reduces cost-aware hedging risk on real held-out episodes."
- **H4 (CVaR versus entropic risk):** "the relative behavior of 95% CVaR and entropic-risk objectives is characterized and compared."
- **H5 (synthetic pretraining then real fine-tuning):** "synthetic pretraining followed by real fine-tuning improves held-out hedging risk over training on real data alone."

**Canonical model family under test:** signature-score neural SDE (the conditional neural SDE trained with a non-adversarial signature-kernel score). Primary generator comparison is signature-score neural SDE vs WGAN neural-CDE neural SDE (v1 Core scope lines 23–25). Required classical generator baselines are IID bootstrap, stationary/block bootstrap, GBM, GJR-GARCH or EGARCH, Heston. Hedging comparison and risk endpoints (95% CVaR primary, entropic secondary, proportional costs) are as written in v1 and have not been changed by Amendments 001–019.

### 2.2 Original signature methodology — exact statement

V1 research question (line 8): "trained with a non-adversarial signature-kernel score" — the term is **signature-kernel**, not "finite truncated-signature + RBF." Early milestone `reports/research/neural_sde_signature_v1.md` records at commit lineage `745d342` that "no torchsde / signatory / signature / esig package was installed" and that the implemented fallback was a "minimal truncated-signature feature map … from scratch with tensor ops and Chen's identity (labelled accurately as a finite-level signature-kernel approximation)." The package `__init__.py` and tests reused the same label. V1 is therefore **underspecified** for architecture/state dimension/context/optimizer/schedule: Amendments 001–012 impose no such fields, and the v1 milestone's frozen fallback design was explicitly declared as a fallback before any external-validation observation (source: `neural_sde_signature_v1.md` Protocol trace section, lines 9–27).

**Holding:** the original intent is a signature-kernel method, but v1 does not pin a PDE kernel identity, expected-signature vs individual-vector form, or level/bandwidth/penalty values. The current finite level-3 method is a disciplined fallback, not a silent substitution.

### 2.3 Original SDE / solver semantics — exact statement

No file in the tracked protocol commits contains the strings `torchsde`, `Stratonovich`, `reversible-Heun`, `sigkernel`, or `signature-PDE` prior to the closure artifacts themselves (verified via `search_files` over all `*.md`/`*.py`/`*.yaml` at `9764bc2`). The v1 model equations are not committed anywhere; the v1 report and all accepted model code use Euler–Maruyama / Itô-style discretization (source: `src/neuralmarket/models/structured_vol_sde.py` `forward()` lines 238–267 and `src/neuralmarket/models/neural_sde.py` / `signature.py` — no Stratonovich correction, no torchsde import, no solver package).

**Holding:** the Stratonovich/torchsde/reversible-Heun requirement stated in task 022 §1 is real as later research intent but is not grounded as a normative v1 line-item. It is treated as original design preference, not as a committed confirmatory threshold.

### 2.4 Original five-seed requirement — exact language

V1 Experimental governance rule (line 99): "All neural comparisons use at least five independent seeds." Companion rule (line 100): "Failed seeds must be reported and may not be silently discarded." Companion rule (line 105): "Market-period uncertainty and training-seed uncertainty are reported separately."

**Applies to:** H1 and H2 jointly, and to every neural family compared — most load-bearing is H2 ("more stable across seeds and epochs than adversarial (WGAN) training") and the primary hedging claim clause (lines 77–86) "the result is not driven by one seed or one isolated market period" (requires "all of the following" — see v1 Primary endpoint). The requirement is normative ("use at least"), not aspirational.

**What counts:** an independent seed is an independently initialized and trained neural model (independent weight init + independent shuffled training trajectory). Evaluation/bootstrap seeds, gate seeds, and MMD bandwidth standardizer reuse do not count toward it unless the protocol explicitly permits that (it does not).

### 2.5 Other v1 governance rules materially bearing on final test

- Chronological splitting only; purging/embargoing required (lines 91–92).
- Normalizers fit on training data only (line 93).
- Option episodes may not cross split boundaries; inception and expiration in same split (lines 94–95).
- Hyperparameters may not be selected using the final test period (line 96).
- Final test may be accessed only after models, metrics, baselines, costs, and statistical procedures are frozen (line 97) — satisfied in structure (v5 is frozen), not yet in seed count.
- Compute/search budgets comparable between signature and adversarial models (lines 101–102).
- Paired, dependence-aware inference; Holm correction for multiple primary comparisons (lines 103–104).
- Failure criteria (lines 108–120): nonfinite loss, no valid checkpoint, >0.1% nonfinite paths, dispersion collapse below 10% of real, volatility 10×, leakage, accounting — H2 stability and failure reporting depend on these.

**Final test is the confirmatory endpoint** for H3–H5 (hedging claims) and for H1/H2 under held-out evaluation; external validation (Amendment 017 onward) is a report-only generator-fidelity check, not the hedging endpoint.

## 3. Current implemented v5 methodology — traced from accepted code and frozen evidence (no modification)

**Model:** `src/neuralmarket/models/structured_vol_sde.py` — `StructuredVolatilityNeuralSde`. State dim 2 (X cumulative log-return observable; V latent log-volatility), Brownian dim 2 (`brownian_dim: 2`), return dynamics `dX = mu_x(t,X,V,ctx) dt + sigma_x(V) dW1` with `sigma_x(V)=softplus(a*V+b)+eps`, volatility dynamics `dV = kappa(t,ctx)*(theta(t,ctx)-V) dt + eta(t,ctx) dW2` with `kappa,eta>0` via softplus+eps. MLP over `(normalized time, state, normalized context)`, 2 hidden × 64 SiLU, diffusion floor `1e-6`, softplus-constrained positive slope `a_positive`, V clamp `[-10,10]`, x0=0 and `z0` from a small context-conditioned linear layer. `config_hash = 5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157`.

**Training (current frozen config `configs/research/structured_vol_neural_sde_v5.yaml`, SHA `f9ca3e9b...`):** objective `rbf` over individual truncated-signature vectors (level 3), per-dimension z-score standardizer and RBF bandwidth fitted from training-fit real paths only (`bandwidth_source: train_fit_real_standardized`, `median_pairwise_squared_distance`, `max_vectors: 512`, `floor_eps: 1e-8`), plus a training-only anti-collapse log-variance penalty (`variance_penalty_coefficient: 1.0`, `variance_eps: 1e-12`). Implementations: `src/neuralmarket/models/signature.py` (Chen composition) and `src/neuralmarket/models/signature_mmd.py` (biased MMD², Gretton et al., frozen form). Optimizer AdamW `lr 1e-3`, `weight_decay 1e-6`, `batch 64`, `max_epochs 400`, `patience 40`, `grad_norm_clip 1.0`. Seeds in this file `model_init_seed: 8281`, `data_seed: 8282`, `eval_seed: 8283` — three distinct experiment *purposes*, not three independently trained model realizations. Internal fit/selection `fit_fraction: 0.8` (80% fit / embargo gap / tail, comparable to v1 80/20 split). Model selection via internal gate v2 (Amendments 013–016 lineage).

**Integration / simulation:** Euler–Maruyama, `dt = 1/252`, `horizon: 63`, `n_eval_paths: 1024`. Code: `StructuredVolatilityNeuralSde.forward()` loop (lines 215–266) with `dx = mu_x*dt + sigma_x*sqrt_dt*noise` and volatility Euler step, explicit finite/positivity fail-closed checks, and `torch.clamp` only on latent V. Simulator: `simulate_structured(model, context, seed)` with `torch.Generator.manual_seed(seed)` and `torch.randn` noise (see `structured_vol_sde.py` lines 270–288). No torchsde import exists anywhere at `9764bc2`.

**Randomness / seeds currently available:** exactly one independently trained and evaluated v5 realization is frozen and externally validated: `data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint_final.pt` SHA `c7b9be5d666ae24fe208cdc9241eab1cbca0cbe95e5576d562fca0bd73ea2be4` (selected/best `checkpoint.pt` SHA `452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f`, training curve `e29f2afcdff75e151ca6a85f3c77e7a209a3c1827b6d1abcb191ce36c6d30a2d`). Directory count is one prefix `5bdbaabd2fb257a7`; the only other sibling `69623a82f91ff0db` is the historic v5 run invalidated by Amendment 016. No second independently trained v5 candidate exists. Internal seeds 7777/7778 (gate generation/diagnostics) and 8801/8802 legacy bootstrap confusion are not training seeds and do not count (Amendment 016 formalized 7777/7778 as explicit YAML fields with no semantic change).

**Evaluation:** Gate v2 (commit `c510533` lineage, pass/fail criteria frozen in Amendment 016 §4) passed for the current run; classical baselines GBM/GJR-GARCH/Heston + iid/block bootstrap are copied verbatim from the empirical benchmark (Amendment 017 suite hash `445b1257...`). External validation is CLOSED at `b203471`/`9764bc2`: normalized exact target match true (both `56b3ba15c0c9...`), per-family report-only, no aggregate/threshold/H1-H2 (Amendment 019). Final test remains sealed (100-session boundary `2023-07-03` to `2023-11-21`; final test `2023-11-22` to `2025-12-31`, 528 sessions — per split_manifest_v1). Hedging claims (H3–H5) have not been evaluated.

## 4. Reconciliation by requirement

### 4.1 Five independent seeds — REQUIRED BEFORE FINAL TEST (P0)

**Classification: A — REQUIRED BEFORE FINAL TEST.**

- Original requirement is normative (v1 line 99 "at least five independent seeds" + line 100 reporting + line 105 uncertainty decomposition + hedging primary-endpoint clause "not driven by one seed"). It applies to H1 and H2 jointly, and most acutely to H2 which is literally a claim about stability *across seeds*.
- `8281/8282/8283` are three experiment-purpose seeds, not three independently trained models — the repository contains exactly one frozen, externally validated trained v5 model at a single model-init seed. No representation can turn one training realization into five.
- Evaluation/bootstrap seeds (1024 paths, 8801-style gates) are not independent training seeds and cannot satisfy the rule.
- Scientific necessity: a single seed cannot support a stability claim, cannot support "not driven by one seed," and cannot support separated training-seed vs market-period uncertainty. Proceeding on one seed would be a scope reduction, not a defense of the original confirmatory threshold.
- **Final-test consequence:** neither H2 nor the primary hedging claim (H3) can be confirmed on one seed. A hedging final-test claim would require five independent neural realizations as a confirmatory input; the current single-seed external-validation evidence cannot be retroactively turned into a five-seed result.
- **Remaining work:** train four additional v5 instances under the identical frozen methodology (same `StructuredVolConfig`, same objective/bandwidth contract, same `dt/horizon/signature_level`, same gate), each from a fresh independent model-init seed, report any failures honestly (including collapse/dispersion/V-clamp/NaN failure reporting per v1 failure criteria), and freeze a multi-seed candidate family identity (e.g. five-member ensemble or per-seed family) **before** any final-test design is accessed. The current single-seed `checkpoint_final.pt` (`c7b9be5d...`) remains one member but does not carry the family claim alone.

### 4.2 Signature methodology: sigkernel vs finite level-3 RBF-MMD — ORIGINAL DESIGN PREFERENCE, SCIENTIFICALLY REPLACEABLE (P1) — with hard transfer rule

**Classification: B — ORIGINAL DESIGN PREFERENCE, SCIENTIFICALLY REPLACEABLE.**

- Original v1 says "signature-kernel" (line 8) but pins no PDE kernel identity, no level/bandwidth, and no expected-signature vs per-vector form. Early fallback design (`neural_sde_signature_v1.md` lines 67–70) explicitly labels Chen-based truncation as a "finite-level signature-kernel approximation" *before* any external validation.
- Current `signature.py`/`signature_mmd.py` + objective contract (`signature_feature_vector` + `fit_signature_standardizer` + `fit_rbf_bandwidth_sq` + `rbf_mmd_sq` + `log_variance_penalty_per_path`) is a disciplined, frozen, no-new-dependency choice that materially expanded the training diagnostic beyond v1 (per-family comparison under `research-metric-spec-v1`, no aggregate).
- Theoretical substitutability is limited: truncated expected-signature MMD can mask dispersion collapse (proven by v1 failure at 6.7% dispersion despite loss minimization), and RBF-MMD over per-vector signatures was introduced precisely to fix that (cf. `signature_mmd.py` module doc, lines 1–8). True sigkernel (PDE/semikernel infinite-level) would be a different kernel, not a trivial parameter change.
- **Final-test consequence:** a final-test claim under current v5 can remain confirmatory *if* the claim is frozen as "finite level-3 lead-lag signature + RBF-MMD (with per-path variance penalty) neural SDE" and the manuscript labels truncation accurately (it already does). No silent upgrade to sigkernel after closure.
- **New candidate rule:** installing sigkernel / switching to an exact PDE kernel creates a new candidate identity (new `config_hash`, new training run, new internal gate, new external-validation requirement). Because external validation is CLOSED (2/2 consumed, third FORBIDDEN), that new candidate cannot inherit `a2834558...` evidence. This closure does not add sigkernel.
- **Remaining work if the project later wants the original kernel:** implement sigkernel as a *separate* candidate family with its own training/validation lineage; do not reuse validation.

### 4.3 SDE semantics: Stratonovich/torchsde/reversible-Heun vs Euler/Itô — ORIGINAL DESIGN PREFERENCE, SCIENTIFICALLY REPLACEABLE (P1) — with hard transfer rule

**Classification: B — ORIGINAL DESIGN PREFERENCE, SCIENTIFICALLY REPLACEABLE.**

- No normative v1 line or tracked protocol imposes Stratonovich or torchsde at `9764bc2` (verified absent). The current Euler–Maruyama / Itô-style discretization with `dt=1/252` is the accepted, frozen simulation path (see §3 Integration).
- Whether the SDE is "written as" Itô or Stratonovich is not pinned in v1; the training loss is pathwise signature-MMD over generated increments, not a Girsanov likelihood that would hinge on a specific correction term. The solver was therefore an implementation preference, not a confirmatory threshold like the five-seed rule.
- **Final-test consequence:** same as §4.2 — a claim under current v5 can remain confirmatory if frozen as "Euler/Itô discretization at dt=1/252 via PyTorch" without claiming Stratonovich semantics. No silent solver upgrade after closure.
- **New candidate rule:** converting the trained `c7b9be5d...` weights to another solver, or adding a Stratonovich correction / torchsde reversible-Heun integrator, would change simulation numerics and constitutes a new candidate identity requiring fresh training and, if claimed, a new (now-unavailable) validation arm. Current external-validation evidence does not transfer to that solver.
- **Remaining work if the project later wants Stratonovich/torchsde:** implement as a separate candidate family; do not mutate the validated `c7b9be5d...` artifact.

### 4.4 H1/H2 claim semantics — what actually remains

| Hypothesis | Original comparator / metric (v1) | Current evidence at `9764bc2` | Unresolved requirements | Claim consequence |
|---|---|---|---|---|
| H1 generator fidelity — v1 lines 47–48 | Signature-score neural SDE vs WGAN neural-CDE + required 5 classical baselines (iid/block bootstrap, GBM, GJR-GARCH/EGARCH, Heston); metrics: stylized-fact scorecard families under `research-metric-spec-v1` (Amendment 017). Final test is *not* the primary fidelity endpoint; hedging is. | Single-seed report-only external-validation result `a2834558...` (Amendment 019 §§7–11): per-family baseline-relative ranks only — 1/6 mean, 2/6 excess_kurtosis & skewness, 4/6 return_acf/sq_return_acf/leverage, 5/6 quantiles/variance, 6/6 abs_return_acf. No aggregate, no threshold, no H1. `GJR-GARCH or EGARCH` satisfied via deterministic GJR-GARCH (Amendment 016 classification); Heston/WGAN adversary baseline for training stability not provided. | Five-seed replication; adversarial WGAN comparator (see §4.1); manuscript fidelity labels must stay per-family. | D — CLAIM-SCOPE REDUCTION REQUIRED: current v5 supports a per-family, baseline-relative, single-seed external-validation report, not a confirmatory "H1 proven" threshold claim. Broader H1 would require five seeds + adversarial comparator. |
| H2 training stability — v1 lines 49–50 + experimental governance lines 99–105 | Signature-score objective vs adversarial (WGAN) training, across seeds and epochs; reporting of failed seeds, separated market-period vs training-seed uncertainty. | No adversarial model trained; no five-seed stability curve; one training curve `e29f2afc...` at one seed. Reproducibility is proven differently (`structured_vol_v5_reproducibility.json` `f27e5cca...` accepted), but reproducibility is not stability. | Five-seed family; WGAN comparator under comparable budgets; stability metrics from multiple seeds. | A — REQUIRED BEFORE FINAL TEST for any H2 claim; no H2 acceptance from current single-seed evidence. |
| H3 hedging (deep vs BS CVaR under proportional costs) — v1 lines 51–52 + Primary endpoint lines 62–86 | GRU deep hedger vs BS delta family; 95% CVaR primary with paired dependence-aware CI, ≥5% magnitude, ≥2 cost levels, turnover/position QC, Holm correction, and "not driven by one seed or one isolated market period." Hedging is the confirmatory downstream test, not external validation. | Not evaluated; final test sealed. | Hedging policy, CVaR statistical procedure, five-seed requirement (same P0), and proportionality assumptions must all be frozen before final-test access. | A — final-test claim requires §4.1 five-seed prerequisite + hedging procedure freeze; external-validation evidence is not a substitute. |
| H4 CVaR vs entropic — v1 line 53 | Characterization/comparison of entropic risk vs CVaR. | Not evaluated. | Same hedging freeze prerequisites. | P1 — publication-grade claim, does not alone block generator identity, but must be pre-registered before final test if claimed. |
| H5 synthetic pretraining — v1 lines 55–56 | Synthetic pretraining then real fine-tuning vs real alone on held-out risk. | Not evaluated. | Same freeze prerequisites + pretraining design. | P2 — extension, not a current-claim blocker. |

**Current overall H1/H2 status:** NOT PROVEN (and H1 cannot be proven from a single-seed per-family rank table under the original five-seed normative rule). This closure declares no H1/H2 acceptance.

### 4.5 Post-validation methodology-change risk — hard boundary

External validation is CLOSED: constructions consumed 2/2, `effective_max_governed_validation_constructions = 2`, `third_construction_permitted = false`, `terminal_no_tolerance_policy = true` (Amendments 018/019, closure `fd142ada...`). Any change to signature objective/kernel/level/bandwidth/penalty, SDE solver/stochastic semantics, architecture (`state_dim/brownian_dim/hidden_*`), training objective (optimizer/loss weights), data/splits, or hyperparameters creates a scientifically different candidate **unless proven otherwise with a controlled bridging argument**, which must itself be pre-registered and validated outside this arm.

- Signature objective change (level, kernel, bandwidth source, penalty) → new config_hash → new candidate → retraining → new internal gate → would have required new external validation (now impossible under this arm) → cannot inherit `a2834558...`.
- Solver/stochastic-interpretation change (Euler→Heun, Itô→Stratonovich, adding torchsde) → new numerics → new candidate → same consequence.
No loophole exists around the closed validation arm. This is why §4.2/§4.3 classify those divergences as replaceable *without* changing the current candidate, but hard-block transferring validation to a changed one.

## 5. Whether the current v5 can proceed to final test

**Answer: YES, BUT ONLY AFTER A SPECIFIC NON-MODEL REQUIREMENT — and only under a narrowed claim. Practically D/A: the existing frozen checkpoint can proceed only after the five-seed prerequisite is satisfied. It cannot proceed to a full original-contract H1/H2/H3 confirmatory claim on today's single seed.**

- The frozen `checkpoint_final.pt` (`c7b9be5d...`) is scientifically eligible as **one member** of a future final-test candidate family, but it alone does not satisfy v1 line 99 or the hedging endpoint's "not driven by one seed" threshold. External-validation evidence for this checkpoint is CLOSED and report-only; hedging final-test evidence must be generated on the **sealed** final split (`2023-11-22` onward), not reusing validation.
- If five independently trained seeds under the identical frozen methodology are produced and frozen, the current v5 family (including this checkpoint as one member) can proceed to final-test consideration under an amended claim:
  - generator fidelity as **per-family, baseline-relative, five-seed-family** external-validation descriptive context plus hedging;
  - methodology explicitly frozen as **finite level-3 lead-lag signature + RBF-MMD with log-variance penalty, Euler/Itô dt=1/252**.
- If five seeds are not produced, no full original-contract H1/H2/H3 confirmatory claim may use the final test; a publication would be limited to D — a narrowed claim ("single-seed v5 hedging exploratory / generator exploratory") with internal-selection evidence only. That is not a pathway to "H1 proven."

**This answer is not a final-test authorization.**

## 6. Multi-seed without reopening validation

Validation is CLOSED and cannot be repeated. The five-seed requirement can be satisfied without reopening it:

- **Training replicate requirement** (five independent model-init seeds): satisfy on internal fit/selection data only — train four additional `StructuredVolatilityNeuralSde` instances under the byte-identical frozen config, data splits, scorecard, and gate procedure. Record every replicate's checkpoint/training curve and any failed seeds per v1 failure criteria. This does not touch validation or final splits.
- **External-validation repeat requirement:** none — do not re-execute external validation. The frozen single-seed external-validation result `a2834558...` remains the closed validation evidence for *this* seed. A five-seed family is a multi-model summary; its variability is characterized on internal non-held-out evidence (fit/selection tails) or on hedging held-out episodes *after* final-test authorization. No validation reconstruction is needed because external validation is per-candidate descriptively, not a family hypothesis test.
- **Hedging final-test requirement:** the GRU hedger evaluation on the sealed final test (after all prerequisites are frozen) will consume all five generator seeds as an ensemble or family — still one final-test construction, not a validation repeat.

No additional validation construction is authorized under the CLOSED v5 arm regardless.

## 7. Final-test prerequisite checklist (none is implemented here)

| # | Prerequisite | Source | Current status at `9764bc2` |
|---|---|---|---|
| 1 | External-validation closure complete (report-only, rank-boundary, lag caveat) | Amendments 017–019, closure `fd142ada...` | DONE |
| 2 | Current candidate identity frozen (config_hash, selected vs final checkpoint, training curve) | `5bdbaabd2fb257a...` + `452f7005...`/`c7b9be5d...`/`e29f2afc...` | DONE |
| 3 | Five-seed requirement satisfied OR formally amended with narrowed claim | v1 line 99, hedging endpoint line 85, Amendment 020 §4.1 | NOT DONE — P0 |
| 4 | Signature methodology frozen as amended claim (finite level-3 RBF-MMD) | Amendment 020 §§4.2, 4.5 | DONE (if no sigkernel installed) |
| 5 | Solver/stochastic semantics frozen as Euler/Itô | Amendment 020 §4.3 | DONE (if no torchsde swap) |
| 6 | H1/H2 claim scope frozen (per-family baseline-relative vs confirmatory threshold) | v1 H1/H2 + Amendment 019 §7 | DONE by this amendment (report-only for current evidence; broader claim requires #3) |
| 7 | Statistical analysis plan (SAP) frozen — CVaR paired CI, Holm, dependence-aware, turnover/position QC, cost levels, seed-uncertainty decomposition | v1 Primary endpoint + Experimental governance | NOT DONE |
| 8 | Final-test evaluation harness frozen (single-access policy, sealed-split access, split identity replay, gate diagnostics) | v1 line 97 + split_manifest_v1 | NOT DONE |
| 9 | Independent audit of SAP + harness + seed family complete | Governance | NOT DONE |
| 10 | Explicit final-test authorization (separate R4/R5 decision, NOT this amendment) | Agent contract risk classes | NOT AUTHORIZED (explicitly FALSE in this amendment) |

**Gating rule:** final test may not be accessed until #3, #7, #8, #9 are complete with a dedicated authorizing amendment/task.

## 8. Prioritization by scientific necessity

- **P0 — blocks final-test consideration:**
  1. Five-seed family completion (four additional independent trainings under frozen config; see §4.1).
  2. SAP freeze for primary hedging claim (CVaR threshold set, CI method, Holm, turnover/position checks, cost-level set, seed/market decomposition).
  3. Final-test single-access harness freeze + independent audit.

- **P1 — required for publication-grade claim, does not alone block current candidate's identity:**
  4. Adversarial WGAN comparator under comparable budget (required for original H2 as written; without it H2 remains not proven).
  5. Hedging policy implementation (GRU deep hedger vs BS variants under proportional costs) sufficient to run SAP.

- **P2 — desirable robustness / extension:**
  6. Separate sigkernel candidate family (true PDE kernel) as extension study.
  7. Separate Stratonovich/torchsde solver candidate family as extension study.
  8. H4 (CVaR vs entropic) and H5 (synthetic pretraining) extensions.

- **P3 — historical / implementation preference only:**
  9. Alternate scoring caveats (e.g. lag-66/horizon-63 already documented in Amendment 019 §9), DVC/data-state bookkeeping, README copy edits.

Ordering is by scientific consequence (confirmatory threshold vs narrative), not by coding effort.

## 9. Recommendation — chosen primary strategy

**STRATEGY B — Freeze a defensible amended methodology around current v5 and narrow claims — hybridized by deferring A as a parallel extension.**

- The only strategy that preserves the current frozen, externally validated single-seed artifact `c7b9be5d...` as valid *seed-1* evidence, respects the closed validation arm (no new validation construction needed to freeze claims), and satisfies the original normative five-seed threshold through a bounded, pre-registered extension (P0 item 1). Installing sigkernel or torchsde now (pure Strategy A) would destroy the candidate identity that holds the only closed external-validation evidence; that evidence cannot be transferred.

- **What Strategy B means in practice:**
  1. Keep current v5 exactly as is — finite level-3 lead-lag signature + RBF-MMD with log-variance penalty, Euler/Itô `dt=1/252` — and freeze manuscript methodology to that description (label truncation honestly, as it already does).
  2. Complete P0 before hedging final-test authorization: train four more seeds under the identical frozen config (proposal: axes `model_init_seed = 8281 ± {100,200,300,400}` or a committed five-seed schedule at the next amendment; value choice is immaterial — independence and frozen config are).
  3. Keep sigkernel and Stratonovich/torchsde as **parallel new candidate families** (Strategy C deferred): implement each as a separate model identity with its own training/validation lineage and its own funding, not as mutations of `5bdbaabd2fb257a...`. Their results do not overwrite v5.

- **Why not pure C as primary:** C is compatible but puts sigkernel/Stratonovich ahead of fixing the P0 seeder blocker — the fastest path to *any* final-test eligibility is B (seeds), and seeding does not require new packages. C is therefore the correct extension after P0.

- **Why not pure A:** A requires completing the original signature-PDE + Stratonovich design before any final test. That is scientifically maximalist, abandons the only closed validation evidence, and turns a documentation/prefix gap into a mandatory dependency install (`sigkernel`, `torchsde`) with new stochastic semantics that would itself require a now-impossible re-validation. It is not required by the normative v1 text as a threshold (v1's confirmatory thresholds are the five-seed + CVaR magnitude/CI/cost-level + per-split governance rules, not a PDE-kernel string match).

- **Why not D:** Evidence is sufficient — original H1/H2/seed/split/cost texts are anchored at `349a5b3` / Amendment 001, current numerics and infrastructure at `9764bc2`; no final-test inspection is needed to decide.

**Tradeoff summary:** B narrows the archival claim from "true infinite-level sigkernel SDE beats all baselines on all metrics" to "finite level-3 RBF-MMD neural SDE (Euler/Itô, single seed externally validated; five-seed family required for hedging confirmatory claim) ranks per-family as externally reported, with any hedging claim conditional on the five-seed SAP." That is honest, defendable, and compatible with a later sigkernel/Stratonovich extension paper without invalidating this one.

## 10. Preservation and immutability statement

Verified `SHA-256` identity after drafting (no protected byte change; see `original_research_contract_reconciliation_v1.json` `protected_integrity`):

- external result `a28345587989ea1d91d46ed7c9b332151b84af98c0d4918f0fc281d03ba4ca38`
- external closure `fd142ad47006513bbd831019e30701d64356945a048ccf13959acf2a63ad5c20`
- Amendments 017 `9ff02f54c2...`, 018 `c5ecf9829e...`, 019 `ce851f5aa6ed7f9e...`, 020 this file
- contract YAML `c7544e5b7cd7...`, harness `726f885a5f...` (blob `e77db7b...`)
- selected checkpoint `452f7005...`, training curve `e29f2afc...`, final checkpoint `c7b9be5d...`, production Gate-v2 report `4604231cfc5d...`, reproducibility `6d182d668f...` (accepted)
- manifest `549056a1ce...`, validation identities `ec49994b...` (validation split `ec49994b...`, 274 obs, 2022-05-26–2023-06-30) and target `56b3ba15c0c...` exact_match true

No protected file was edited.

## 11. What this amendment does not do

- Does not authorize final test.
- Does not reopen external validation (still CLOSED, 2/2).
- Does not change scientific code, model identity, or data.
- Does not declare H1/H2 accepted or rejected.
- Does not create a hedging result.

## 12. Next scientific decision boundary

The next governed task must be exactly one implementation or decision step from §8 P0: either (a) a frozen five-seed schedule amendment that pins the four additional `model_init_seed` values and the family identity before training, or (b) a frozen hedging SAP amendment. No training or final-test access until that schedule and its audit are complete.

---

*Amendment 020 is append-only closure reasoning. Amendments 017, 018, and 019 remain unchanged. Any future final-test access requires a separate, explicitly authorized task.*
