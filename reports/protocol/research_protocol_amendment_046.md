# Amendment 046 — V5 Runtime-Sensitivity Provenance Record Correction

**Date:** 2026-08-22
**Task:** NM-R4-V5-SENSITIVITY-RECORD-REPAIR-075
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `2cc758bcc92780e567264f4fc15b4f194bd4fce3`
**Safety branch:** `safety/pre-v5-sensitivity-record-repair-2cc758b` (created without switching at 2cc758b)
**Analysis task:** NM-R4-V5-RUNTIME-SENSITIVITY-ANALYSIS-073
**Independent audit:** NM-R4-V5-RUNTIME-SENSITIVITY-AUDIT-074
**Audit verdict:** REPAIR REQUIRED — GOVERNANCE RECORD ONLY
**Critical audit conclusion:** THE SENSITIVITY ANALYSIS ITSELF IS VALID. Audit 074 recomputed 777/777 analytical cells with zero numerical mismatches. **Do NOT rerun analysis, alter statistics, edit script/JSON/Amendment 045.**
**Status:** APPEND-ONLY PROVENANCE RECORD CORRECTION. No --execute, no training, no simulation, no Gate, no reserve/fifth-member, no validation/external/final/hedging. Prior Amendments 039–045 remain immutable except where this amendment explicitly supersedes incorrect provenance wording.

## 1. Scope and immutability

Analysis frozen at `368a5c329b0eb4a97edb0a0028ca8bd19e04d965` (script + result JSON) and `2cc758bcc92780e567264f4fc15b4f194bd4fce3` (Amendment 045) is numerically VALIDATED (`777/777` cells) and **byte-unchanged** in this amendment. Repair scope is governance-record/provenance only: four malformed artifact identities in Amendment 045 §9, result-JSON CRLF/LF provenance disambiguation, best_epoch LOMO annotation clarification, stdlib-only dependency wording, and 841 provenance supersession. No statistic, methodology, member inclusion, threshold, or scientific interpretation changes. Audit 074 total-checked 777 = 52 raw member/scalar + 78 full summaries + 468 LOMO + 179 CPU-vs-mixed cells, 0 mismatches.

## 2. Reverified task-073 artifacts (read-only, before mutation)

All recomputed from exact bytes (`sha256sum`/`hashlib.sha256(file_bytes)` for SHA-256 FILE_SHA256, `git hash-object`/`SHA-1` over `blob <size>\0<bytes>` for Git blob, `wc -c` for byte length, raw byte scan for line endings, `git cat-file blob HEAD:<path>` for committed form; worktree CRLF normalized via `b'\r\n' -> b'\n'` exact comparison).

- **Analysis script** `reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py`:

  - worktree SHA-256: `f24f54c8ef8a7867bd911c8778bbdadc54d50a55668274179c574cb760f0288a` (20638 bytes, LF-only, 333 LF, 0 CRLF)
  - committed-content SHA-256 (LF-normalized stored bytes): `f24f54c8ef8a7867bd911c8778bbdadc54d50a55668274179c574cb760f0288a` (20638 bytes, LF)
  - Git blob SHA-1: `616c9d17cb7d451fc72397e4fd6053b598068ad4`
  - line endings worktree: `LF`, committed: `LF` — identical, no normalization needed
  - worktree == committed bytes exactly (0 divergence)

- **Amendment 045** `reports/protocol/research_protocol_amendment_045.md`:

  - worktree SHA-256: `29220b1914b0e741641dc1e7d9159c3b1bd659a890033c240df4c5c8f099037b` (33162 bytes, LF-only, 263 LF, 0 CRLF)
  - committed-content SHA-256: `29220b1914b0e741641dc1e7d9159c3b1bd659a890033c240df4c5c8f099037b` (33162 bytes, LF)
  - Git blob SHA-1: `8e9f0e8355d76392223cb026d563d2776c5f15c7`
  - line endings: `LF` / `LF` identical

- **Result JSON** `reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json`:

  - RESULT_JSON_WORKTREE_FORM — line endings `CRLF` (1819 CRLF, 0 LF-only), byte count 58394, SHA-256 `9dec35fc8d434f927ad3d0d5168de30bb06df380cd5031c45fa1e57287833a1f`
  - RESULT_JSON_COMMITTED_CONTENT — line endings `LF` (0 CRLF), byte count 56575, SHA-256 `8276f0d3bf105d9ba482799973035f2295cc5e2d50af4896a27f06b496e49ef7`
  - RESULT_JSON_GIT_BLOB — `1b9ed4edc84b4111701a30e38bc16b86a9fe8166` (blob of committed LF form)
  - Verification: `worktree bytes CRLF -> LF (b'\r\n' replaced by b'\n') == committed bytes` — **exact equality** (56575 bytes match). If not exact, STOP — but it is exact here.
  - Mechanism: `.gitattributes` `* text=auto eol=lf` (plus `*.ps1 text eol=crlf`, binaries excluded) with `core.autocrlf=true` drives clean-filter LF normalization on commit; checkout produces CRLF worktree form on this `true` host. Committed SHA prefix independently observed as `8276f0d3...` and now full value above recomputed.

`.gitattributes` verified: `* text=auto eol=lf` (committed at HEAD), `core.autocrlf=true` (local config). The two text forms are semantically identical JSON; difference is checkout/clean-filter line-ending normalization, not analytical mutation; Git blob identity is representation-stable for the committed LF object; worktree SHA is checkout-form specific; a fresh LF checkout may not reproduce the `9dec35fc...` CRLF worktree SHA.

## 3. Amendment 045 §9 four defective identities (malformed, superseded)

Read directly from Amendment 045 §9 (lines around 226/228). Verify malformed lengths explicitly — SHA-256 MUST be 64 hex, Git blob MUST be 40 hex.

### 3.1 Incorrect values as historically written (malformed)

- incorrect analysis-script SHA-256: `7491e0f069afed3c18357031a762d318bf178babf77176a3170b337e8425` — **length 60 hex (malformed, truncated, MUST be 64)**
- incorrect analysis-script Git blob: `10e6d48e5172da6f73317bcee2abb6e4e2e073c11f1` — **length 43 hex (malformed, MUST be 40)**
- incorrect purported Amendment-045 SHA-256: `5f35be39006340466d0256c901ef8802ea38f22b9627ca2e33e0954df1ff026` — **length 63 hex (malformed, MUST be 64)**
- incorrect purported Amendment-045 Git blob: `33f0fd9f6e135f884f4061398ea864e0f06926e2c` — **length 41 hex (malformed, MUST be 40)**

All four fail hex-length validation and DO NOT match any reverified artifact hash in section 2.

### 3.2 Correct historical Amendment-045 identities (verified, superseding)

- correct analysis-script SHA-256: `f24f54c8ef8a7867bd911c8778bbdadc54d50a55668274179c574cb760f0288a` (64 hex, reverified §2, worktree == committed)
- correct analysis-script Git blob: `616c9d17cb7d451fc72397e4fd6053b598068ad4` (40 hex, reverified §2)
- correct historical Amendment-045 SHA-256: `29220b1914b0e741641dc1e7d9159c3b1bd659a890033c240df4c5c8f099037b` (64 hex, reverified §2)
- correct historical Amendment-045 Git blob: `8e9f0e8355d76392223cb026d563d2776c5f15c7` (40 hex, reverified §2)

**Important:** Amendment 046 records the verified identity of the *prior immutable* Amendment 045 (`29220b...`/`8e9f0e...`). Amendment 046 does NOT and MUST NOT attempt to record its own future SHA/blob inside itself — such a self-authenticating hash would be paradoxical.

Amendment 045 remains immutable; only §9 provenance wording is superseded by this section. No other Amendment 045 clause is superseded.

## 4. Result-JSON line-ending provenance (disambiguated)

Recorded separately per task 075 section 4 (verified §2):

- `RESULT_JSON_WORKTREE_FORM` — `CRLF` (1819 `\r\n`), 58394 bytes, `9dec35fc8d434f927ad3d0d5168de30bb06df380cd5031c45fa1e57287833a1f` (checkout-form specific, host/crlf-dependent)
- `RESULT_JSON_COMMITTED_CONTENT` — `LF` (0 CRLF), 56575 bytes, `8276f0d3bf105d9ba482799973035f2295cc5e2d50af4896a27f06b496e49ef7` (LF-normalized, audited prefix `8276f0d3...` now full value verified via `git cat-file blob`)
- `RESULT_JSON_GIT_BLOB` — `1b9ed4edc84b4111701a30e38bc16b86a9fe8166` (committed LF object, representation-stable)

State explicitly:

- the two text forms are semantically identical (JSON content byte-identical after CRLF->LF normalization);
- `CRLF -> LF` normalization reproduces committed bytes exactly (verified equality, section 2);
- difference is checkout/clean-filter normalization via `.gitattributes` `text=auto eol=lf` + `core.autocrlf=true`, not analytical mutation;
- Git blob identity is representation-stable for the committed LF object;
- worktree SHA `9dec35fc...` is checkout-form specific;
- a fresh LF checkout (e.g., `core.autocrlf=false` or `eol=lf` forced) may not reproduce the CRLF worktree SHA and yields the committed `8276f0d3...` form instead.

Do NOT mutate or reserialize the result JSON (committed LF remains authoritative for hashing; worktree CRLF is an ephemeral checkout artifact under the current config; JSON content is unchanged).

## 5. Validated analysis frozen (777/777)

Audit 074 independently recomputed and validated:

- raw member/scalar table: `52/52` values (4 members × 13 scalars)
- full summary cells: `78/78` (13 scalars × 6 summary fields N/mean/SD/median/min/max)
- LOMO compared cells: `468` (13×4 omissions × 9 numeric fields per omission where applicable)
- CPU-vs-mixed compared cells: `179` (13 scalars × CPU/mixed/absolute/relative rows)
- total independently checked: `777/777`
- numerical mismatches: `0`

Record unchanged:

- 13 frozen scalars unchanged (5 training including `selection_loss_improvement_absolute` with relative as secondary; 5 Gate; 3 report-only; RBF `initial_internal_rbf`/`best_internal_rbf` definitively excluded)
- N=4 mixed, N=3 CPU, LOMO N=3 each (52 rows), `ddof=1` via `statistics.stdev`, no imputation, no new threshold, no significance test, no causal backend estimate, no H2 proof
- All four members are `GATE_PASS_VALID` so inclusion is unconditional per 041 three-way semantics; seed-03 `GOVERNANCE_INVALID` disclosed only

Do NOT reproduce or recalculate the tables here unless necessary for the wording corrections below. Do NOT change any number. This task repairs provenance records only.

## 6. Wording defects superseded (documentation only, no bytes edited)

Do not edit historical files. This section supersedes only incorrect/ambiguous statements for documentation purposes.

### 6A. Amendment 045 best_epoch LOMO annotation (internally contradictory, result JSON correct)

Verify directly from committed result JSON `lomo.best_epoch`:

- full mean `56.25`, largest influence member **strict argmax** `v5-seed-04` with `|absolute_change| = 16.25`
- omit `v5-seed-01`: mean `72.33333333333333`, absolute `+16.08333333333333`, relative `+0.28592592592592586`
- omit `v5-seed-02`: mean `72.33333333333333`, absolute `+16.08333333333333`, relative same
- omit `v5-seed-04`: mean `40.0`, absolute `-16.25`, relative `-0.28888888888888886`
- omit `v5-seed-05`: mean `40.333333333333336`, absolute `-15.916666666666664`, relative `-0.2829629629629629`

Therefore **omit `v5-seed-04` is the strict argmax of `|absolute_change|`** (`16.25 > 16.0833 > 15.9166`). Amendment 045 §5.2 correctly bolds `omit 04` as the largest, but adds parenthetical `"(04 ≈ 01/02 tie within 0.17 gap; strict argmax is 01/02 at 16.083 < 16.25 — tie note in JSON shows strict; widest swing is 72.33 vs 40)"` whose prose clause `strict argmax is 01/02` contradicts its own bolded value and the result JSON. The contradiction is presentation-level only: the bolded `omit 04`, the underlying values (`16.083/16.083/-16.25/-15.916`), and the result JSON field `full_set_summaries.best_epoch.lomo_largest_influence_members = ["v5-seed-04"]` are all correct. Superseded: the parenthetical clause `strict argmax is 01/02`. Corrected reading: strict argmax is `v5-seed-04` at `16.25`; `01`/`02` are the near-second at `16.083`.

### 6B. Analysis-script dependency wording (stdlib-only)

Imports verified directly in committed `structured_vol_v5_runtime_sensitivity_analysis.py` lines 1–16: `hashlib`, `json`, `math`, `statistics`, `subprocess`, `Path` — all stdlib. No `import numpy`, `from numpy`, `import torch`, `import pandas`, nor any optional numpy codepath / try-import branch exists. Docstring phrase `stdlib only + numpy if available otherwise pure python` is imprecise for this committed revision (no numpy branch present). Clarification: **the analysis recipe is stdlib-only** (`statistics.stdev ddof=1`, no numpy, no torch, no path generation, no network). Do NOT edit the script docstring in this task because the exact audited recipe bytes (20638 LF, `f24f54c8...`/`616c9d17...`) must remain frozen for the `777/777` audit lineage.

### 6C. Amendment-044 / result-JSON 841 provenance wording (manifest has no such top-level field)

Actual source verified read-only: `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_execution_manifest.json` has **NO** top-level field `all_training_window_count` — checked key set contains `fit_window_count`, `selection_window_count`, etc., but not that name. Correct durable statement (unchanged in substance from Amendment 045 §8, reiterated here as superseding label):

- **seed-05 adjudication:** `all_training_derived_windows = 841`
- **derived from:** `672 fit + 107 selection + 62 embargo-gap = 841` (Amendment 044 §6.1 derivation; seed-05 adjudication `structured_vol_v5_seed_05_primary_adjudication_v2.json` field `all_training_derived_windows` / `all_training_derivation` string `672 fit + 107 selection + 62 embargo-gap = 841 derived training windows; 925 returns / 926 sessions`)

Result-JSON field `documentation_correction.amendment_044_all_training_window_provenance` as committed contains self-referential winding prose that restates the correction but buries the negated manifest claim inside a long sentence; for documentation purposes that prose is superseded by the concise three-line provenance above. Do NOT edit the result JSON or Amendment 044/045 bytes; supersession applies to description only.

### 6D. Additional independently verified wording (no guessing, durable only)

Audit 074 truncated inside non-blocking finding 4 while recommendation refers to findings 2–6, so findings 5–6 MUST NOT be guessed and were not guessed here. Independently inspected durable Task-073 artifacts for documentation-only contradictions of the same class (observable in committed bytes, independently derivable correction, no statistic/methodology/status/threshold/scientific-interpretation change):

- `reports/research/structured_vol_v5_runtime_sensitivity_analysis_v1.json` field `effective_preregistration.scalars_training_5` ordering vs actual `SCALAR_ORDER[0:5]` in the script is `initial/best/best_epoch/final_epoch/selection_loss_improvement_absolute` — the JSON's list is exactly those five and the member-table keys match — no correction needed, recorded as verified.

Therefore:

**NO_ADDITIONAL_DURABLE_WORDING_DEFECTS_ESTABLISHED** — no further documentation-only contradiction of the same class was independently observable in committed bytes beyond §6A–6C above. No redesign permitted; any future audit finding not durably verifiable here must be established by that later audit from its own evidence, not inferred here.

For each correction above: file `reports/protocol/research_protocol_amendment_045.md` §5.2/§9, `reports/research/evidence/structured_vol_v5_runtime_sensitivity_analysis.py` docstring line ~3-4, and `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_execution_manifest.json` key set / adjudication provenance — incorrect text vs correct text vs evidence as cited in §6A–6C.

## 7. What this amendment does NOT do

- Does NOT modify Amendment 045 bytes (only supersedes §9 provenance wording and §5.2 best_epoch parenthetical clause for documentation).
- Does NOT modify result JSON bytes or reserialize/normalize its committed CRLF->LF storage (both forms remain as committed; only description disambiguated in §4).
- Does NOT modify analysis script bytes (stdlib-only clarification is descriptive; docstring frozen).
- Does NOT modify any earlier amendment (039–044) bytes, execution artifacts, checkpoints/curves, authorizations, CUDA recipe/runner/trainer, Gate-v2, config, family, schedule, or external closure.
- Does NOT change any analytical value (777/777 validated), table, LOMO largest, member inclusion, five-seed requirement, or H2 interpretation.

## 8. Protected analysis / family / firewall state (verified unchanged)

Recomputed and verified before commit (bytes == HEAD, no divergence):

- analysis script blob: `616c9d17cb7d451fc72397e4fd6053b598068ad4` — unchanged (LF, 20638, `f24f54c8...`)
- result JSON blob: `1b9ed4edc84b4111701a30e38bc16b86a9fe8166` — unchanged (committed LF 56575, `8276f0d3...` / worktree CRLF 58394 `9dec35fc...`)
- Amendment 045 blob: `8e9f0e8355d76392223cb026d563d2776c5f15c7` — unchanged (LF, 33162, `29220b...`)
- Amendments 039–044: worktree == HEAD, LF, blobs unchanged (`040 8e9f0e...-related 040 is earlier; 044 blob b69ef0...` etc. — verified via `git diff --quiet` null)
- all execution artifacts (`1e8aa171993a1aba` six files, plus 02/04 replicates, 01 prod gate), authorizations (`d777663...` `bc68789...`), CUDA recipe `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a`, runner `05b704b...`, trainer `85aabc67...`, Gate-v2 `05af8d0d...`/`f27e5cc...`, config `f9ca3e9b...`, family `730475...`, schedule `558d08b...`, external closure — all unchanged (`git diff --stat` empty except this amendment file).

Family remains:

- `v5-seed-01` valid CPU (`GATE_PASS_VALID`), `v5-seed-02` valid CPU, `v5-seed-03` governance-invalid / retained / numerically excluded, `v5-seed-04` valid CPU, `v5-seed-05` valid CUDA (`GATE_PASS_VALID`).
- Valid count: `4`, Gate-pass count: `4`, five-seed requirement `UNRESOLVED`, reserve/fifth-member `NONE`.
- Training `0`, `--execute` `0`, simulation `0`, validation `0`, new external `0`, final `0`, provider/network `0`.

## 9. Git discipline

One new tracked file only: `reports/protocol/research_protocol_amendment_046.md` (this file). Analysis script commit `368a5c3` and result JSON `368a5c3` remain separate; Amendment 045 commit `2cc758b` remains separate; this amendment commits only its own markdown.

Commit: `docs(research): correct v5 runtime sensitivity provenance` — NO amend, NO rebase, NO reset, NO push. Final tracked tree clean (only pre-existing untracked signature reports `neural_sde_signature_v3/v4_report.json` + `structured_vol_v5_report.json` remain intentionally untracked per repo pattern).

Post-task: runtime sensitivity analysis `VALIDATED_NUMERICALLY` (777/777), runtime sensitivity provenance `REPAIRED_PENDING_INDEPENDENT_AUDIT`, five-seed requirement `UNRESOLVED`, reserve/fifth-member `NONE`, final `SEALED`.

## 10. Required next action

Independent read-only audit of this Amendment 046 sensitivity provenance repair (verify: only this file added, analysis/result/045 blobs exact, four malformed identities superseded correctly with hex-length corrected, full committed-content result SHA `8276f0d3...` recomputed not guessed, CRLF/LF provenance unambiguous with `.gitattributes` + `core.autocrlf`, no statistic changed, no member/accounting change, no scientific interpretation broadening, no execution/reserve/final access, final sealed) before any family inference task.

---

*Amendment 046 corrects only provenance/wording of the numerically validated (777/777) Task-073 sensitivity analysis (analysis `f24f54c8...`/`616c9d17...`, result committed LF `8276f0d3...` worktree CRLF `9dec35fc...` blob `1b9ed4ed...`, Amendment 045 `29220b...`/`8e9f0e...` superseding its §9 malformed `7491e0f069(60)`, `10e6d48e...(43)`, `5f35be3900(63)`, `33f0fd9f...(41)`), clarifies stdlib-only execution and `best_epoch` strict argmax `04` at `16.25`, fixes 841 provenance to adjudication `all_training_derived_windows 672+107+62=841`, records no additional durable wording defect, and leaves all 777 statistics, member accounting, five-seed UNRESOLVED and final SEALED unchanged.*
