# Amendment 047 — V5 Fifth-Admissible-Member Methodology Decision

**Date:** 2026-08-22
**Task:** NM-R4-V5-FIFTH-MEMBER-METHODOLOGY-DECISION-077
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `27e51c22886ab36b598bfd240d1d716f1ac9fbb3`
**Safety branch:** `safety/pre-v5-fifth-member-methodology-27e51c2` (created without switching at 27e51c2)
**Prior audit:** NM-R4-V5-SENSITIVITY-RECORD-REPAIR-AUDIT-076 — VALIDATED WITH NON-BLOCKING FINDINGS
**Current family state:** seed-01 VALID CPU, seed-02 VALID CPU, seed-03 GOVERNANCE_INVALID retained numerically inadmissible, seed-04 VALID CPU, seed-05 VALID CUDA — valid/admissible numerical N=4, Gate-pass valid N=4, normative requirement 5 independent valid, five-seed UNRESOLVED, reserve NONE, final SEALED
**Status:** DECISION ONLY — append-only methodology preregistration for resolving the under-filled five-seed family. No model execution, no --execute, no authorization artifact, no training/simulation/refit/Gate, no reserve execution, no validation/external/final/hedging.

## 1. Purpose and governance

This amendment makes and preregisters exactly ONE methodology decision for obtaining the fifth admissible numerical family member required by the normative five-independent-valid-member design (v1 line 99). It is decision-only: it selects a policy and — if policy permits — designates exactly one already-frozen reserve candidate as the sole `FIFTH_VALID_MEMBER_CANDIDATE` for future authorization/execution. It creates no authorization JSON, performs no scientific computation, and does not authorize execution; execution will require a separately governed authorization task.

Prior runtime-sensitivity analysis (Amendment 045, task 073) and its provenance repair (Amendment 046, audit 076) are treated as VALIDATED in this decision; no statistic is redesigned here.

## 2. Authoritative five-seed / reserve contract (reconstructed)

Read as committed protocol (not terminal summaries):

- **Original normative clause:** `reports/protocol/research_protocol_v1.md` line 99: `All neural comparisons use at least five independent seeds.` Line 100: `Failed seeds must be reported and may not be silently discarded.` Line 105: training-seed vs market-period uncertainty reported separately. Applies to H1/H2 jointly and the hedging primary claim's `not driven by one seed` clause (v1 lines 77–86). Requirement is `at least five` — normative, not aspirational.

- **Amendment 020** (§2.4, §4.1): five-seed requirement is `REQUIRED BEFORE FINAL TEST` (classification P0) for any full confirmatory claim; single-seed `8281/8282/8283` are experiment-purpose seeds, not five independently trained realizations; five independent replicas under identical frozen methodology required; failure reporting per v1 lines 108–120 remains.

- **Amendment 021** (§§4–11): minimum varying training set `{model_init_seed, data_seed}` (§4, derivation `model_init_seed = replicate_seed`, `data_seed = replicate_seed + 1`), fixed eval `COMMON_FIXED 8283` (§8), fixed Gate seeds `7777/7778/8801`, methodology invariants (§9, only RNG varies). **§10:** failed primary remains permanently recorded, retains member ID and unique tuple, never silently discarded/relabelled/replaced/erased. **§11:** required per-member evidence frozen; **§12–16:** closed external validation relation, final NOT AUTHORIZED. **§10 explicitly permits deterministic reserves** but requires them to be frozen before the primary batch (or via pre-authorized deterministic schedule with predeclared order), executed only in predeclared order as needed, never erasing the failed primary, failure count includes every failed primary, no outcome-picking.

  > Amendment 021 §10: `Reserve seeds, if used at all, must themselves be frozen before the primary training batch begins (or via a separately pre-authorized deterministic reserve schedule with predeclared execution order). Reserves execute only in predeclared order and only if needed. A reserve never erases the failed primary.`

- **Amendment 022** (§§5–15) — numerical schedule and under-filled-family policy:

  - §5: five primary replicates `replicate_seed(k) = 8281 + 1000*(k-1)` for `k=1..5` — 8281/9281/10281/11281/12281 — already executed as `01..05`.
  - §9: **deterministic reserve algorithm frozen before training:** `reserve_replicate_seed(j) = 12281 + 1000*j` for positive integer `j`, initial capacity `j=1,2,3` → 13281/14281/15281. `numerical_execution_authorized: false`, `execution_order: j=1 then 2 then 3 only as needed; no skipping`, `outcome_based_selection: false`, `frozen_before_primary_training: true`. Reserves not scheduled primaries; hashes pending until reserve task.
  - §10: `primary_scheduled=5`, `primary_attempted`, `primary_valid_completed`, `failed_in_primary = 5 - primary_valid_completed` once PRIMARY_COMPLETE; no reserve counts as successful primary.
  - §11: `PRIMARY_COMPLETE: all five primary runs attempted` (now true); `PRIMARY_UNDERFILLED: PRIMARY_COMPLETE and primary_valid_completed < 5` (now true: 4 < 5); **consequence:** H2 remains NOT PROVEN, H3/final-test authorization remains BLOCKED, no silent use of four valid as the five-seed primary family, reserves reported separately and do not retroactively fill primary count, SAP must define reserve contribution while retaining failure reporting.
  - §15: `numerical_schedule: FROZEN`, `reserve_training: NOT_AUTHORIZED`, `validation/final/hedging: NOT_AUTHORIZED`.
  - Audit 025 (referenced §2): contract VALIDATED WITH NON-BLOCKING FINDINGS, numerical schedule AUTHORIZED, reserve execution NOT AUTHORIZED.

- **Amendment 034 / 039:** original family contract does NOT require same CPU/GPU/hardware for all members (039 §2.1: `HARDWARE_NOT_FROZEN_IN_ORIGINAL_FAMILY_CONTRACT`); runtime identity is execution provenance separate from `config_hash`/`family_methodology_identity`; prospective CUDA-only policy now governs new execution; Amendment 034 governance: future mixed family requires separate decision — this amendment (now 047) is the extra-member governance.

  **Critical supporting clause — Amendments 039 §2.3 + 022 §10:** `a sixth attempted execution is compatible with the original contract because the permanent attempted history may contain six attempted identities while the valid numerical family contains exactly five admissible members.` Original `at least five` is a lower bound; Amendment 021 §10 and 022 §10 explicitly model failed-primaries retained while reserves produce a valid fifth. No contradiction — 5-attempted primary roster + 1 reserve-attempted (total 6 attempts) yielding 5 valid is permitted when reserves were frozen beforehand in schedule order. Amendment 039 §7 / 044 §8 already anticipated `valid N=4` post-seed-05 and declared `later separately governed extra/replacement/reserve methodological decision will still be required` — this decision satisfies that.

  > Amendment 039 §2.1: header `Original family contract did NOT contain same-hardware rule`; §2.3: `scheduled primary family has five permanent slots... A reserve never erases a failed primary... The original five-independent-seed requirement remains active. Seed-03 is not silently replaced. If seed-05 later succeeds, the admissible primary members will be exactly four...`
  > Amendment 022 §10: `A primary failure remains in the roster forever... never silently discarded, never relabelled as reserve... No reserve counts as a successful primary.`

- **Amendments 040–046:** runtime-sensitivity preregistration, correction, execution record `f72db0b` (GATE_PASS_VALID `1e8aa171993a1aba` CUDA `17e3bb52...`), 777/777 sensitivity validation, provenance corrections — family currently `valid N=4` `Gate-pass N=4` `UNRESOLVED`.

**Independently established answers to task 077 §2 bullet list:**

- five independent valid members is **normative** (v1 line 99 + 020 §4.1, before final test);
- governance-invalid primary members **DO NOT** count toward N=5 (021 §10, 022 §11, 039 §2.3);
- a reserve was **explicitly contemplated** (021 §10 + 022 §9) and **frozen before relevant results** (022 §9 `frozen_before_primary_training true`, schedule at `421508f...` before training);
- reserves are **contingency candidates**, not replacements that erase, not additions counting as primaries; they are unassigned until a governed decision promotes one;
- reserve promotion **requires a separately governed methodology decision** (039 §7, 040 §7, 044 §8 — each states `later separately governed decision`);
- an additional sixth attempted execution **IS compatible** with the original family contract when `N_valid=4` after 5 attempts and a pre-frozen reserve supplies the fifth valid (021 §10 + 022 §9 + 039 §2.3);
- valid family inference **CAN use five admissible members even though six attempts appear in permanent history** — permanent history = 5 primaries (one invalid) + 1 reserve attempt = 6 attempts; valid numerical set = 4 current primaries + 1 reserve valid = 5 (severity counts include the failed primary separately; valid set excludes it).

## 3. Frozen seed schedule (verified)

Schedule artifact `reports/research/structured_vol_v5_seed_schedule_v1.json` — path `reports/research/structured_vol_v5_seed_schedule_v1.json`, SHA-256 `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` (header `e333325c...` lineage), Git blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`, family `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (RNG-stripped canonical), `created_before_training: true` at `421508f...`.

Primary identities (verified via schedule + recomputed `V5ExperimentConfig.config_hash()` against frozen base config `configs/research/structured_vol_neural_sde_v5.yaml`):

- seed-01: `replicate 8281` `model/init 8281` `data 8282` `eval 8283` → `config 5bdbaabd2fb257a7a82b8c600403e638d860520aa4952055a1b153894caf4157` prefix `5bdbaabd2fb257a7`
- seed-02: `9281`/`9281`/`9282`/`8283` → `62c7406cb3a2c64237d39559370d70a27f8111f7dd1dc7ee581da9bd475cf00b` prefix `62c7406cb3a2c642`
- seed-03: `10281`/`10281`/`10282`/`8283` → `e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955` prefix `e333325c804d95d2`
- seed-04: `11281`/`11281`/`11282`/`8283` → `77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b` prefix `77e7de9efabb7ce3`
- seed-05: `12281`/`12281`/`12282`/`8283` → `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897` prefix `1e8aa171993a1aba`

Reserve candidates — derivation `reserve_replicate_seed(j) = 12281 + 1000*j`, frozen derivation verified and recomputed:

- `reserve-j01`: `replicate 13281` `model/init 13281` `data 13282` `eval 8283` → `config 38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` prefix `38c5113b27568e14`
- `reserve-j02`: `14281`/`14281`/`14282`/`8283` → `423277df1ac4cd9a4088141e4cc483561b29d4aa6ff2973e57d379cdbe3d2969` prefix `423277df1ac4cd9a`
- `reserve-j03`: `15281`/`15281`/`15282`/`8283` → `e89b0ac0956d197e8b335b28873e6d6802ff8176a21e18f35a5d3d7e88dbb2df` prefix `e89b0ac0956d197e`

`family_methodology_identity` recomputed for reserves = `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (identical to primaries — RNG fields stripped).

Execution status of all three reserves: **NOT EXECUTED** — `reports/research/structured_vol_v5_replicates/38c5113b27568e14` and `data/processed/research/model/.../38c5113b27568e14` and `j02`/`j03` siblings absent; no `execution_started`, no report, no curve. Identities existed / followed frozen deterministic derivation **before this task** and were **not selected in response to observed performance** (schedule predates all training results; selection reason below is `PRIMARY_SEED_03_GOVERNANCE_INVALIDITY`).

## 4. Three methodological paths evaluated (protocol/governance structure only)

Performance of seed-03 (governance-invalid) and seed-05 (valid) **NOT used**. Decision is protocol/governance-structure only.

### Policy A — DETERMINISTIC_FIRST_RESERVE_PROMOTION (frozen reserve as sole candidate)

- Original five-seed requirement: **compliant** — satisfies `at least five valid` via the already-contemplated reserve mechanism; no primary-count reinterpretation needed. Five valid after reserve success: `01/02/04/05` valid primaries + `j01` valid reserve = 5 (with permanent history 6 attempts documented separately — see §6).
- Frozen schedule: **compatible** — uses algorithm `12281+1000*j` (`reserve-j01` slot) frozen at `421508f...`/`022 §9`; `order 1` first eligible; identities verified §3.
- Post-result selection risk: **minimal** — deterministic first-eligible, `outcome_based_selection: false`, no scientific result exists for any reserve; choice cannot cherry-pick a favorable `config_hash`/prefix.
- RNG independence: independent `{model_init 13281, data 13282}` — distinct from all 10 primary derived seeds (8281/8282 ... 12281/12282) and Gate seeds 7777/7778/8801 (verified via `random.seed`/`numpy.random.seed`/`torch.Generator.manual_seed` acceptance); no per-candidate scientific data to bias RNG.
- Seed-03 treatment: preserved as `ATTEMPTED_FAILED_GOVERNANCE` retained; reserve is NOT a rerun of 03 but an independent scheduled identity (§6).
- CPU/CUDA policy: candidate executes CUDA-only (see §7); composition disclosure handled; no retroactive hardware reinterpretation.
- H2 interpretability: reserve adds one more valid point without claiming to isolate hardware; runtime-sensitivity disclosure for 5 valid will need the same `CPU N=3 / CUDA N=2` balance caveat — acceptable and governed.
- Provenance simplicity: **simplest** — refers to existing frozen schedule; no new methodology invention; derivation rule and third-party verifier are already committed.
- New inventions needed: **none**.
- Defensibility: highest — deterministic, pre-registered derivation, minimal degrees of freedom.

### Policy B — NEW_ADDITIONAL_PRIMARY_OUTSIDE_RESERVE

- Five-seed requirement: technically reachable but requires **inventing a sixth `replicate_seed` outside the frozen reserve set** (e.g., a new value not in `12281+1000*j` for `j=1..3`).
- Frozen schedule: **incompatible** — violates `022 §9` reserve derivation intent; requires ad hoc methodology addition after observing that `PRIMARY_UNDERFILLED` persists, increasing post-result degrees of freedom even if the value is chosen blind.
- Post-result selection risk: **non-zero** — any newly chosen outside value is a post-hoc design choice made knowing `N_valid=4`; even blind, it adds researcher discretion.
- RNG independence: any fresh value can be made independent, but the choice itself is less constrained.
- Seed-03/CPU/CUDA: same as A on substance, but provenance is weaker.
- Provenance: **invented** — needs new text binding a new seed outside the committed range.
- Defensibility: lower than A.

### Policy C — NO_ADDITIONAL_MEMBER_AND_NARROW_CLAIMS

- Five-seed requirement: **non-compliant as confirmatory** — leaves family permanently `PRIMARY_UNDERFILLED` (022 §11): H2 remains NOT PROVEN, H3/final-test authorization remains BLOCKED, no result may silently use four valid as the five-seed family. Publication would be limited to exploratory/narrowed claims; hedging SAP with final-test claim would be blocked indefinitely.
- Frozen schedule: compatible (does nothing) but **defeats the §1 normative design preserved by hierarchy FIRST**.
- Post-result risk: zero execution risk, but maximal **claim-narrowing cost**.
- H2 interpretability: permanently foreclosed as confirmatory.
- Provenance: trivial but at the cost of abandoning the original confirmatory scope.
- Defensibility: defensible only if reserve promotion were contract-forbidden — it is not.

## 5. Predeclared decision hierarchy and selected policy

Hierarchy applied (unless a committed contract directly forbids it):

- **FIRST:** Preserve the normative five-independent-valid-member design.
- **SECOND:** Use an already frozen deterministic reserve identity rather than inventing a new seed after observing results.
- **THIRD:** Choose the FIRST eligible reserve in frozen schedule order — with no performance, seed, hash, or characteristic preference.

No reserve scientific result exists and none may be generated in this task.

The committed contract **permits** reserve promotion (021 §10, 022 §9/§15, 039 §2.3/§7) and **does not forbid** the sixth attempt interpretation (021/022 primary-forever + reserve-as-contingency + original `at least five` lower bound). Therefore the hierarchy's default is admissible.

**Decision (frozen):**

> **Selected policy: `DETERMINISTIC_FIRST_RESERVE_PROMOTION`**

> **Selected candidate: exactly the first eligible frozen reserve `reserve-j01` as `FIFTH_VALID_MEMBER_CANDIDATE`.**

> **Selection reason: `PRIMARY_SEED_03_GOVERNANCE_INVALIDITY` — the under-filled state arises because primary `v5-seed-03` remains permanently `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` (`GOVERNANCE_INVALID`) and numerically inadmissible; the reserve is required to supply the fifth *admissible* member under the normative five-seed requirement. NOT `SCIENTIFIC_PERFORMANCE`, NOT `GATE_FAILURE` (no valid-member Gate failed), NOT `LOW_LOSS`, NOT `RUNTIME_RESULT`. No reserve result was observed or cherry-picked.**

If the contract had expressly forbidden reserve promotion, the next contract-compliant policy would have been `NO_ADDITIONAL_MEMBER_AND_NARROW_CLAIMS` (Policy C) — with permanent narrowing — but it does not, so `DETERMINISTIC_FIRST_RESERVE_PROMOTION` is retained without reinterpretation.

No automatic chain through `j02`/`j03` is authorized by this amendment (see §8). This task authorizes no execution; authorization is a later governed task.

## 6. Seed-03 and family counting (frozen)

Regardless of selected policy, freeze verbatim:

- `v5-seed-03` remains permanently `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` / `GOVERNANCE_INVALID` — retained in permanent history (forensic `reports/research/evidence/structured_vol_v5_seed_03_attempt_forensic_record.json`, closure `reports/research/structured_vol_v5_seed_03_primary_closure.json`, manifest `reports/research/structured_vol_v5_replicates/e333325c804d95d2/training_execution_manifest.json` if present). It must NEVER be deleted, renamed as valid, converted to reserve, reclassified because its numerical Gate passed, or counted in valid numerical `N`.

  - Current valid numerical set: `01/02/04/05` (N=4) — `valid_count=4`, `Gate-pass count=4`
  - Excluded: `03` — disclosed in every accounting table, not in any LOMO/CPU-vs-mixed valid mean

- If future reserve `reserve-j01` becomes governance/protocol valid (`GATE_PASS_VALID` or `GATE_FAIL_VALID` or `VALID_EXECUTION_NO_GATE_RESULT` with frozen missingness handling), the permanent attempted history will contain **six attempted identities** (`01..05` primaries + `j01` reserve) while the valid numerical family will contain **exactly five admissible members** (`01/02/04/05` valid primaries + `j01` valid reserve). This interpretation **IS supported** by the original contract:

  - v1 line 99 `at least five` — not `exactly five attempts`
  - Amendment 021 §10: failed primary never erased; reserve never erases failed primary; failure count retained
  - Amendment 022 §10–11: reserves do not retroactively fill primary count; reporting keeps `failed_in_primary` and valid counts separate; SAP must define whether reserves can contribute to a completed-model estimator
  - Amendment 039 §2.1: `HARDWARE_NOT_FROZEN_IN_ORIGINAL_FAMILY_CONTRACT` + runtime provenance separate — reserves as contingency are within scope
  - Amendment 021/022 derivation is `frozen_before_primary_training` — so the sixth attempt was contemplated deterministically before observation

- Do NOT call the reserve a `rerun of seed-03`. It is an **independent scheduled member** with its own frozen RNG identity `13281/13282/8283` (`38c5113b27568e14`), distinct `config_hash`, and its own Gate evaluation under `7777/7778/8801`.

## 7. Runtime / CUDA methodology for the candidate (frozen)

Current NeuralMarket scientific-compute policy is **CUDA-only for new scientific execution** (Amendments 034/039/044 execution record `f72db0b` at `17e3bb52...` / `.venv-gpu` `3.11.9/2.13.0+cu132/CUDA 13.2/cudnn 92000/RTX 4070 CC 8.9` validated). If `reserve-j01` is later authorized:

- Require `requested_device = cuda`, `resolved_device = cuda` required, `CUDA-unavailable = fail closed` (`RuntimeError`, no CPU fallback) — via `src/neuralmarket/core/device.py:resolve_device` and `src/neuralmarket/core/runtime_identity.py:build_runtime_identity` at normative capture point after `resolve_device` + `configure_device_determinism` before `execution_started`.
- Runtime identity MUST be separately captured and authorization-bound (`expected_runtime_identity_sha256` in `structured-vol-v5-primary-training-authorization-v2` schema, `c74958f2...`) before execution; all load-bearing PyTorch scientific computation on CUDA; CPU only at orchestration/reporting/serialization boundaries.
- Do NOT claim the new CUDA member is hardware-equivalent to historical CPU members (3× CPU `01/02/04`), that runtime variation is seed-only, or that CUDA causes differences. The existing runtime-sensitivity disclosure (Amendment 045) remains authoritative and frozen.
- If adding a second CUDA member (`05` already CUDA + `j01` future CUDA) yields composition `CPU N=3 / CUDA N=2` (mixed N=5), future family summaries **MUST disclose** that composition explicitly (and keep `CPU-only 01/02/04` n=3 vs mixed n=5 disclosure as in 045 §6, now with `N=2` CUDA labelled).
- Do NOT redo or redesign the already frozen seed-05 four-member sensitivity analysis (Amendment 045/046) in this task — that analysis is VALIDATED and PROVENANCE-REPAIRED and is complete for its four-member scope.

## 8. Future fifth-member success / failure semantics (preregistered before authorization/execution)

Possible future statuses for `reserve-j01` (pre-authorized, result-independent):

- **`GATE_PASS_VALID`** (governance/protocol valid + FAIL criteria none + all six Gate criteria PASS): **included** in valid family summaries, LOMO recomputation, and hedging SAP inputs as a valid fifth admissible member. Gate PASS disclosed.
- **`GATE_FAIL_VALID`** (governance/protocol valid + FAIL criteria none + one or more Gate criteria FAIL): **still governance/protocol valid and included** in numerical family summaries as a valid fifth member, per 041 §4 three-way semantics; scientific Gate failure disclosed with exact criterion. Must not be excluded or cherry-picked from summaries.
- **`VALID_EXECUTION_NO_GATE_RESULT`** (governance/protocol valid but Gate genuinely unavailable): **included only according to already frozen available-scalar/missingness rules** (Amendment 045 missingness: scalar missing → that scalar omitted for that member with note, not imputed); **does NOT count as Gate pass** (so not Gate-pass count, but valid for execution counting per 021/022 failure taxonomy).
- **`GOVERNANCE_INVALID`** (device/runtime mismatch, invocation count >1, missing authorization, double invocation, overwrite, etc.): **retained in attempt history, excluded from valid numerical family** (exactly like seed-03 today); excluded from LOMO/CPU-vs-mixed valid means; failure reporting retains it.

What counts toward satisfying `five independent valid members` (per existing contract 021/022):

- A member counts **only if** governance/protocol valid (i.e., any of the first three statuses above). Governance-invalid never counts.
- Valid count contributors after future `j01` attempt: if `j01` is any of the first three statuses, then `valid N` becomes `4 + 1 = 5` and Gate-pass count accrues only for `GATE_PASS_VALID`. If `j01` is `GOVERNANCE_INVALID`, `valid N` remains `4` and the family remains `PRIMARY_UNDERFILLED`.
- **No automatic second reserve promotion:** if `j01` itself becomes `GOVERNANCE_INVALID`, **NO** chain through `j02`/`j03` is authorized by this amendment. A **new governed methodology decision** is required before any `j02` execution (and again before `j03`, if needed). This amendment freezes ordering `j01 < j02 < j03` but does not pre-authorize their execution.

Do NOT invent success semantics after observing the future `j01` result; semantics here are frozen.

## 9. Amendment metadata and Git discipline

One new tracked file only: `reports/protocol/research_protocol_amendment_047.md` (this file). No `new reserve namespace`, no `model namespace`, no checkpoint/curve, no Gate result, no authorization JSON, no validation/external/final-test construction.

Recorded accordingly:

- Authoritative five-seed requirement: v1 line 99 + Amendments 020 §4.1/021 §4-11/022 §11/039 §2 — five independent valid required for full confirmatory claim; governance-invalid does not count.
- Current four-member state: `01` VALID CPU `5bdbaabd2fb257a7`, `02` VALID CPU `62c7406...`, `03` GOVERNANCE_INVALID retained `e333325c...`, `04` VALID CPU `77e7de9...`, `05` VALID CUDA `1e8aa171993a1aba`/`17e3bb52...`.
- Permanent seed-03 status: `ATTEMPTED_FAILED_GOVERNANCE`/`DOUBLE_SCIENTIFIC_INVOCATION` retained (above).
- Reserve schedule provenance: path/SHA/blob §3; three reserves `j01..j03` pre-frozen, NOT EXECUTED.
- Policies A/B/C evaluated (§4) and **selected A** with reason `PRIMARY_SEED_03_GOVERNANCE_INVALIDITY` (§5); no performance-based selection.
- Candidate: `reserve-j01` `13281/13282/8283` `38c5113b27568e14` `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` — deterministically derived, pre-frozen, `j01` first eligible.
- Future CUDA-only required (§7); future semantics preregistered (§8); no automatic `j02`/`j03` chain.
- Five-seed requirement remains **UNRESOLVED** until `j01` (or any future valid fifth) actually becomes contract-valid — not resolved by this decision alone.
- No execution authorization created; final remains `SEALED`.

Documentation clarification from Audit 076 (independently verified, documentation-only, no hash/statistic changed):

> The result JSON's CRLF worktree representation (58394 bytes worktree CRLF `9dec35fc...` vs committed LF 56575 `8276f0d3...` blob `1b9ed4ed...`) **arose from the analysis script's Windows Python text-mode write** (`Path.write_text(..., encoding="utf-8")` without `newline="\n"`). **Checkout itself is governed by `eol=lf`** (`.gitattributes` `* text=auto eol=lf`, committed LF stored) **and produces LF for that path on clean checkout**; **Git clean-filter normalization then converts the subsequently written CRLF form to LF on staging** (the CRLF bytes written by the script are normalized to LF in the committed blob by the `text=auto eol=lf` clean filter). This correction is documentation-only — no prior hash (`f24f54c8...`/`29220b...`/`9dec35fc...` worktree vs `8276f0d3...` committed), statistic (777/777), or analysis result changes.

Do NOT perform a broad repository-wide provenance cleanup in this task beyond the single clarification above.

## 10. Protected and unchanged

Runtime-sensitivity script `reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py` (blob `616c9d17...`), result `reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json` (blob `1b9ed4ed...`, committed LF `8276f0d3...`), Amendments 039–046, all seed execution evidence, authorizations, Gate-v2 `05af8d0d...`/`f27e5cc...`/`d9705ef9...`, config `f9ca3e9b...`, seed schedule `558d08b...`, CUDA recipe `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a`, runner `05b704b...`, trainer `85aabc67...`, runtime impl `817ba53e...`, external closure — all blobs `git diff --quiet HEAD` clean.

Task passes only if: one methodology policy selected (`A`), selection is contract-based (not result-based), no execution, selected candidate derives from frozen schedule (`reserve-j01` `38c5113b...`), no automatic `j02`/`j03` authorization, seed-03 permanently retained, future CUDA requirement explicit (§7), five-seed requirement still UNRESOLVED pending actual valid fifth member (this decision does not resolve it), final SEALED.

## 11. What this amendment does NOT do

- Does NOT perform or authorize execution of `reserve-j01` (or `j02`/`j03`); no `authorization-v2` JSON is created.
- Does NOT choose any seed value outside the frozen reserve set.
- Does NOT redo sensitivity analysis or change runtime-sensitivity provenance.
- Does NOT count reserves as having satisfied `N=5` — valid count remains `4` until a reserve actually executes validly.

## 12. Required next action

Independent read-only audit of this fifth-member methodology decision (verify: contract lineage correct, reserve identities recomputed exactly and pre-frozen before training, Policy evaluation complete with governance-only selection, `DETERMINISTIC_FIRST_RESERVE_PROMOTION` + `reserve-j01` exactly derivable from frozen schedule, no performance used, no automatic chain, seed-03 retained, CUDA-only for new member, Audit 076 wording clarified without hash/statistic change, single new file, final sealed) before any authorization task for `reserve-j01` may be considered. The fifth-member authorization itself is a later separately governed task.

---

*Amendment 047 preregisters `DETERMINISTIC_FIRST_RESERVE_PROMOTION` via frozen `reserve-j01` `13281/13282/8283` (`38c5113b27568e14`, `730475...`) as `FIFTH_VALID_MEMBER_CANDIDATE` for reason `PRIMARY_SEED_03_GOVERNANCE_INVALIDITY` — not performance — under CUDA-only (`cuda`/`cuda` fail-closed) with semantics `GATE_PASS_VALID`/`GATE_FAIL_VALID`/`VALID_EXECUTION_NO_GATE_RESULT`→count, `GOVERNANCE_INVALID`→retain/exclude, no `j02`/`j03` chain pre-authorized; reserves do NOT retroactively satisfy five-seed while sixth attempt is contract-compatible (021 §10, 022 §§9–11, v1 at least five); valid `4`/`Gate-pass 4`/`N_j01=1` pending execution, five-seed UNRESOLVED, final SEALED.*
