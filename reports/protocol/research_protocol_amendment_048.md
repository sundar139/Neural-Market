# Amendment 048 — V5 Fifth-Member Validity and Counting Semantics Correction

**Date:** 2026-08-22
**Task:** NM-R4-V5-FIFTH-MEMBER-SEMANTICS-REPAIR-079
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `265d2b2fc5cae9a6619ef4a6664de95be5d54288`
**Safety branch:** `safety/pre-v5-fifth-member-semantics-repair-265d2b2` (created without switching at 265d2b2)
**Repaired task:** NM-R4-V5-FIFTH-MEMBER-METHODOLOGY-DECISION-077
**Repaired amendment:** `reports/protocol/research_protocol_amendment_047.md` at `265d2b2fc5cae9a6619ef4a6664de95be5d54288`
**Independent audit:** NM-R4-V5-FIFTH-MEMBER-METHODOLOGY-AUDIT-078 — REPAIR REQUIRED
**Audit critical conclusion:** Selected methodology policy itself is VALID (`DETERMINISTIC_FIRST_RESERVE_PROMOTION` + `reserve-j01`). This repair preserves it.
**Status:** APPEND-ONLY SEMANTICS CORRECTION. No authorization, no --execute, no training/simulation/reserve execution, no j02/j03 decision, no validation/external/final/hedging. Prior Amendments 039–047 remain immutable except where this amendment explicitly supersedes clauses per audit 078.

## 1. Scope and preserved policy

Audit 078 validates the selected policy as contract-compliant. **This amendment does NOT re-decide the policy.**

- Selected policy remains: `DETERMINISTIC_FIRST_RESERVE_PROMOTION`
- Selected candidate remains: `reserve-j01` as `FIFTH_VALID_MEMBER_CANDIDATE` (`13281/13282/8283`, config `38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` prefix `38c5113b27568e14`, family `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`, selection reason `PRIMARY_SEED_03_GOVERNANCE_INVALIDITY`, performance `NONE`, execution NOT AUTHORIZED, `j02`/`j03` NOT AUTHORIZED)
- This task repairs only: future-status/N=5 counting semantics (A), fabricated contract quotation/provenance statement (B), directly verified documentation wording/identity-label defects (C). Audit 078 verdict is `REPAIR REQUIRED` (governance-record only), not a numerical finding.

No member was retrained, resimulated, or rerun. No reserve executed. No new threshold invented.

## 2. Authoritative distinctions (re-established)

Read as committed protocol (not terminal prose):

**PRIMARY ROSTER** — `primary_scheduled = 5` permanently: `v5-seed-01`/`02`/`03`/`04`/`05` (already attempted as `PRIMARY_COMPLETE`). `v5-seed-03` (`e333325c804d95d2`) remains `ATTEMPTED_FAILED_GOVERNANCE`/`DOUBLE_SCIENTIFIC_INVOCATION`/`GOVERNANCE_INVALID` forever — never deleted, renamed valid, converted to reserve, reclassified because Gate passed, or counted in valid N. A reserve NEVER retroactively becomes a successful primary, never erases `03`, never changes the historical `primary_attempted` roster (`01..05`).

**SEPARATELY:** the governed methodology may allow an independently valid reserve to contribute to the **completed-model comparison/estimator required to obtain at least five admissible trained realizations** — as a separately identified reserve member (not as a retroactive primary). This is the `completed-model analytical set` vs `primary roster` distinction (§4).

Source lineage for this distinction: v1 line 99 (`at least five`), Amendment 020 §4.1 (P0 requirement), Amendment 021 §§10–11, Amendment 022 §§10–11 (reserves do not retroactively fill primary count; reporting keeps `failed_in_primary` and valid counts separate; SAP defines reserve contribution), Amendment 039 §2 (hardware not frozen + later reserve decision anticipated), Amendment 041 §4 (three-way semantics), Amendment 047 §6/§8 as corrected §3–§4 below. No frozen state name beyond `primary_scheduled`/`PRIMARY_COMPLETE`/`PRIMARY_UNDERFILLED`/`valid N` vs `Gate-pass N` vs `completed-model analytical set`; descriptive accounting used where no name exists.

## 3. Corrected future-status counting rule (supersedes Amendment 047)

Supersedes ONLY the Amendment 047 clauses that state or imply `VALID_EXECUTION_NO_GATE_RESULT` increments the normative five-member requirement. Frozen corrected rule superseding Amendment 047 §8 (bullet `VALID_EXECUTION_NO_GATE_RESULT`) and its footer summary phrase ``GATE_PASS_VALID/GATE_FAIL_VALID/VALID_EXECUTION_NO_GATE_RESULT→count``:

- **`GATE_PASS_VALID`** — governance/protocol valid, valid checkpoint/result: **included** in numerical family summaries, **counts as Gate pass**, **MAY supply** the fifth admissible completed-model member.
- **`GATE_FAIL_VALID`** — governance/protocol valid, valid completed checkpoint/result: **included** in numerical family summaries, Gate failure disclosed, **does NOT count as Gate pass**, **MAY supply** the fifth admissible completed-model member (still governance/protocol valid admissible — per Amendment 041 §4 three-way semantics, valid-set inclusion is governance-validity not Gate outcome).
- **`VALID_EXECUTION_NO_GATE_RESULT`** — governance/protocol-valid execution state, retained permanently, include available frozen training scalars only, explicit Gate missingness, **included in failure-rate accounting**, but **does NOT count as Gate pass**, **DOES NOT satisfy the normative five-admissible-member requirement**, leaves the family **under-filled**, **DOES NOT authorize final progression** (five still UNRESOLVED, final remains SEALED).
- **`GOVERNANCE_INVALID`** — retained permanently, **excluded** from valid numerical family summaries, **does NOT count as Gate pass**, **DOES NOT satisfy** the normative five, leaves the family **under-filled**.

No other future-status wording in Amendment 047 is affected; `GATE_PASS_VALID`/`GATE_FAIL_VALID`→count semantics are retained (they were already correct). Only `VALID_EXECUTION_NO_GATE_RESULT`→count is superseded to →does-NOT-count.

## 4. Primary-vs-reserve accounting (frozen)

Record explicitly:

- **Current historical primary roster:** `01` `02` `03` `04` `05` (five permanent slots; `PRIMARY_COMPLETE` now true, `PRIMARY_UNDERFILLED` true because `4 < 5`).

- **Primary seed-03 remains:** `ATTEMPTED_FAILED_GOVERNANCE`/`DOUBLE_SCIENTIFIC_INVOCATION`/`GOVERNANCE_INVALID` (forensic + closure above).

- **Primary historical accounting must continue to report:** primary scheduled `5` / attempted `5` counts, primary `valid-completed 4`, `failed-in-primary 1` (only `03`). A future valid `reserve-j01` does NOT retroactively fill the primary roster; does NOT turn `03` into a successful primary; does NOT rename `primary_valid_completed` from its historical meaning (primary valid remains `4`; completed-model valid becomes `5` — different namespaces).

- If `reserve-j01` becomes `GATE_PASS_VALID` or `GATE_FAIL_VALID`: it **may contribute as a separately identified reserve member** to the governed completed-model five-member estimator/comparison, **subject to the real contract clauses frozen by Amendments 021/022 and this audited repair** (i.e., SAP/analysis must keep primary vs reserve lineage labelled, gate pass/fail disclosed, under-filled primary history retained). Always report primary history, reserve history, and completed-model analytical set **separately** — no silent merging.

- If `VALID_EXECUTION_NO_GATE_RESULT`: the completed-model admissible count **stays at four** (not five; under-filled).

- If `GOVERNANCE_INVALID`: the completed-model admissible count **stays at four** (not five; under-filled).

- Consistent counting example after a valid `j01 GATE_PASS_VALID`: valid numerical family `01/02/04/05` valid primaries + `j01` reserve valid → 5; but primary valid-completed stays `4` and failed-in-primary stays `1` — the fifth valid is a **reserve-contributed completed-model** member, not a repaired primary.

## 5. Fabricated contract quotation — withdrawn and superseded

### 5.1 Offending Amendment 047 text (verbatim, independently read)

Committed `reports/protocol/research_protocol_amendment_047.md` line at `§2` paragraph beginning `Critical supporting clause — Amendments 039 §2.3 + 022 §10:` reads (backticks in source preserved):

```
a sixth attempted execution is compatible with the original contract because the permanent attempted history may contain six attempted identities while the valid numerical family contains exactly five admissible members.
```

This text is presented in Amendment 047 as a `Critical supporting clause` backed by `Amendments 039 §2.3 + 022 §10`. Audit 078 found it is fabricated as a quoted clause.

### 5.2 Verbatim-existence check (independently verified)

Searched exact string and normalized variants across `research_protocol_v1.md` §1/§2, Amendments `020`/`021`/`022`/`039` committed bytes:

- `research_protocol_v1.md` at `349a5b3` — **NOT FOUND** (v1 contains `All neural comparisons use at least five` but not `sixth attempted`).
- `research_protocol_amendment_020.md` — **NOT FOUND** (contains five-seed P0 but not `sixth`)
- `research_protocol_amendment_021.md` — **NOT FOUND** (contains reserve-must-be-frozen-before-primary-batch but not `sixth attempted`)
- `research_protocol_amendment_022.md` — **NOT FOUND** (contains `reserve_replicate_seed(j)=12281+1000*j` but not the quoted clause)
- `research_protocol_amendment_039.md` — **NOT FOUND** (header `HARDWARE_NOT_FROZEN_IN_ORIGINAL_FAMILY_CONTRACT` but not the quoted sentence; contains no substring `sixth attempted`)

**Classification:** `NOT_A_VERBATIM_CONTRACT_CLAUSE`. Not a direct quote; mislabeled as a supporting clause quotation.

### 5.3 Replacement — reasoned synthesis (NOT a quote)

Label: `REASONED_CONTRACT_SYNTHESIS` (not a quote; synthesis from real citations only). Amends wording that counted on the fabricated line:

- **Real citations (quote only actual source text):**

  - `reports/protocol/research_protocol_v1.md` line 99: `"All neural comparisons use at least five independent seeds."` (verbatim).
  - `reports/protocol/research_protocol_v1.md` line 100: `"Failed seeds must be reported and may not be silently discarded."` (verbatim).
  - `reports/protocol/research_protocol_amendment_021.md` §10 (block quoting source §2 line above): `"Reserve seeds, if used at all, must themselves be frozen before the primary training batch begins (or via a separately pre-authorized deterministic reserve schedule with predeclared execution order). Reserves execute only in predeclared order and only if needed. A reserve never erases the failed primary."` (verbatim, Amendment 047 §2).
  - `reports/protocol/research_protocol_amendment_022.md` §10 (block): `"A primary failure remains in the roster forever... never silently discarded, never relabelled as reserve... No reserve counts as a successful primary."` (verbatim, Amendment 047 §2). And §11: `PRIMARY_COMPLETE` / `PRIMARY_UNDERFILLED` (`4 < 5`) consequence + `reserves reported separately and do not retroactively fill primary count` (paraphrase of committed §11 text; see §2).
  - `reports/protocol/research_protocol_amendment_039.md` §2.1 header: `"HARDWARE_NOT_FROZEN_IN_ORIGINAL_FAMILY_CONTRACT"` is the original contract did NOT contain same-hardware rule (verbatim header concept; see 039 §2.1 text).
  - `reports/protocol/research_protocol_amendment_022.md` §9: `reserve_replicate_seed(j) = 12281 + 1000*j` with `frozen_before_primary_training: true` and `numerical_execution_authorized: false` (committed `schedule v1` JSON).

- **Reasoned synthesis (non-quote, only those concepts):** original `at least five` is a lower bound; attempted and valid counts are distinct namespaces (attempted `5` primaries vs valid `4` after `03` failure); failed primaries remain forever; reserves were frozen before primary training in deterministic order `j=1 then 2 then 3` as needed; reserves do not retroactively fill the primary count; Amendment 022 §11 **reserved for a later governed SAP** the question of how reserves may contribute to the completed-model estimator/comparison; **Amendment 047, as repaired by this Amendment 048 and later independently audited, IS that separately governed methodological freezing** (deterministic `j01` as fifth valid candidate) — therefore the completed-model analytical set of `5` (four valid primaries + one valid reserve) with permanent attempted history of `6` is **permitted** (not as a verbatim `sixth attempted` line, but as a synthesis of the above).

Quote only actual source text (above). Do not quote the withdrawn clause again as if it were contractual.

Historical amendment changed: **false** — Amendment 047 remains byte-unchanged; this §5 supersession applies only as interpretive repair for counting/quotational defect.

## 6. Reserve-j01 identity preserved

- `reserve-j01` (`FIFTH_VALID_MEMBER_CANDIDATE`, NOT EXECUTED): `model/init 13281` `data 13282` `eval 8283` → `config 38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` prefix `38c5113b27568e14` family `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (recomputed via `V5ExperimentConfig.config_hash()` against `configs/research/structured_vol_neural_sde_v5.yaml`; schedule `report/structured_vol_v5_seed_schedule_v1.json` blob `558d08b...` provenance §3 in 047).
- Current status: `UNEXECUTED` (no `reports/research/structured_vol_v5_replicates/38c5113b27568e14/execution_started.json` etc.), `frozen_before_primary_training true`, `numerical_execution_authorized false`.
- Selection reason: `PRIMARY_SEED_03_GOVERNANCE_INVALIDITY` (not performance). No reserve scientific result exists; no `config_hash`/prefix preference.

If `j01` later becomes `GOVERNANCE_INVALID` or `VALID_EXECUTION_NO_GATE_RESULT`: **NO automatic `j02`** — a new governed methodology decision is required before any `j02` (see 047 §8 frozen rule, unchanged).

`j02`/`j03` remain `UNSELECTED NOT AUTHORIZED` (recomputed identities `423277df...`/`e89b0ac...` but not promoted here).

## 7. CUDA/runtime and future disclosure rules (unchanged)

Any eventual `reserve-j01` scientific execution remains `CUDA only` (`requested_device = cuda`, `resolved_device = cuda` required, CUDA unavailable = `fail closed` `RuntimeError` no fallback, `authorization-v2` runtime identity binding `c74958f2...`/`817ba53e...` at capture after `resolve_device`+`configure_device_determinism` before `execution_started`, all load-bearing PyTorch on CUDA, CPU at boundaries only).

Historical CPU members (`01`/`02`/`04` `GATE_PASS_VALID` + `03` invalid) remain immutable. If `j01` becomes admissible completed member: future analytical composition **MUST disclose** `CPU N=3 / CUDA N=2` (today's 045 four-member `N=3 CPU / N=1 CUDA` disclosure is frozen; not redesigned). Do NOT claim CPU/CUDA equivalence, causal CUDA effect, seed-only variation, hardware identity.

## 8. Verified documentation defects closed (only if independently observable with directly derivable correction)

- **8A. Amendment-047 CRLF mechanism — NOT superseded.** Verified committed wording §9 paragraph beginning `The result JSON's CRLF worktree representation (58394 bytes worktree CRLF...` reads verbatim as Amendment 047 §9 (quoted above): `arose from the analysis script's Windows Python text-mode write (Path.write_text(..., encoding="utf-8") without newline="\n")`. `Checkout itself is governed by eol=lf (.gitattributes * text=auto eol=lf, committed LF stored) and produces LF for that path on clean checkout`; `Git clean-filter normalization then converts the subsequently written CRLF form to LF on staging` — this IS exactly the task-specified correct mechanism (§8 prompt §2 `Additional members: seed-05 execution...`): `clean checkout is LF because eol=lf; Path.write_text subsequently created CRLF worktree; clean filtering normalized CRLF to LF on staging`. 047 does NOT call CRLF a checkout artifact (it calls it script-written). **DO NOT supersede unnecessarily** — no supersession done for this clause.

- **8B. FILE_SHA256 vs Git blob — independently verified and clarified.** Audit 078 reports Amendment 047 §10 uses `f9ca3e9b...` for config within prose describing blobs. Independent check: `reports/protocol/research_protocol_amendment_047.md` §10 paragraph beginning `Runtime-sensitivity script... Amendments 039–046, ... Gate-v2 ... f27e5cc.../d9705ef9..., config f9ca3e9b..., seed schedule 558d08b...` lists `f9ca3e9b...` inline among blobs (`016c9d17...`, `1b9ed4ed...`, `d9705ef9...`) but **without** labelling it as blob vs FILE_SHA256. Correct identities recomputed read-only (no edit to 047):

  - `configs/research/structured_vol_neural_sde_v5.yaml`: `FILE_SHA256 f9ca3e9b09fdaaf0a631ee1eb7e896ea2f0e2adf8c6b7b11a4206da4d5519972` (`sha256sum`/`hashlib.sha256(file_bytes)`) — full value, not truncated `f9ca3e9b...`.
  - Same file: `Git blob SHA1 405895cf4db417a7a50aeb78bcf3d06edb333f89` (`git hash-object`, SHA-1 over `blob <size>\0<bytes>`) — distinct system, MUST NOT be conflated.
  - Never call the file SHA a blob.

  This correction is a label clarification; no 047 byte edited, no statistic changed.

- **8C. Other Audit-078 non-blocking findings:** supplied audit output **may be truncated** per task prompt. Do NOT guess unavailable findings. No additional documentation wording/identity-label defect was **independently observable in committed bytes with a directly derivable correction** beyond §8B and the already-addressed §3/§5. Therefore nothing further repaired.

## 9. What this amendment does NOT do

- Does NOT re-decide methodology policy `DETERMINISTIC_FIRST_RESERVE_PROMOTION`.
- Does NOT change candidate `reserve-j01 13281` or choose `j02`/`j03` or any value outside the frozen reserve set.
- Does NOT perform or authorize execution (`reserve-j01` remains execution NOT AUTHORIZED, no authorization JSON, five-seed requirement still UNRESOLVED).
- Does NOT modify Amendment 047 or any earlier amendment byte (supersession only by reference for §3/§5/§8B).
- Does NOT embed Amendment 048's own future SHA/blob in itself (self-authentication paradox forbidden).

## 10. Git / firewall / acceptance discipline

One new tracked file only: `reports/protocol/research_protocol_amendment_048.md` (this file). No authorization JSON, training/simulation/reserve execution, validation/external/final/hedging, provider or network.

Verification before commit (bytes == HEAD, unchanged): Amendments 039–047 (blobs `4c8a24a...` through `8b6e64d...` unchanged), frozen schedule `558d08b...`/`8c471c...`, runtime sensitivity script `616c9d17...`/`f24f54c8...` and result `1b9ed4ed...`/`8276f0d3...`, all seed execution evidence, authorizations (`d777663...`/`bc68789...`), Gate-v2 `05af8d...`/`f27e5cc...`/`d9705ef9...`, config `f9ca3e9b...`/`405895cf...`, CUDA recipe `6a6b9f...`, runner `05b704b...`, trainer `85aabc67...`, runtime impl `817ba53e...`, external closure — all `git diff --quiet HEAD` clean. Final tracked tree clean (only pre-existing untracked `neural_sde_signature_v3/v4_report.json` + `structured_vol_v5_report.json` intentionally untracked).

Post-task: runtime sensitivity `VALIDATED_NUMERICALLY`, runtime sensitivity provenance `REPAIRED_PENDING_INDEPENDENT_AUDIT` (046), fifth-member policy `DECIDED_PENDING_INDEPENDENT_AUDIT` as repaired, fifth-member semantics `REPAIRED_PENDING_INDEPENDENT_AUDIT`, five-seed UNRESOLVED, reserve execution NOT AUTHORIZED, final SEALED.

## 11. Required next action

Independent read-only audit of this Amendment 048 (verify: policy/candidate unchanged, only AUTHORIZED semantics corrected per §3, fabricated quotation withdrawn per §5 with real citations and `REASONED_CONTRACT_SYNTHESIS`, CRLF mechanism correctly left alone per §8A, FILE_SHA vs blob clarified per §8B with full values, third audit findings not guessed, single append-only file, final sealed) before any authorization task for `reserve-j01` may be considered. The fifth-member authorization itself is a later separately governed task.

---

*Amendment 048 supersedes Amendment 047 only for: validity counting (only GATE_PASS_VALID/GATE_FAIL_VALID MAY supply the fifth admissible completed-model member; VALID_EXECUTION_NO_GATE_RESULT leaves N=4 under-filled and does NOT authorize final; GOVERNANCE_INVALID leaves N=4) and the fabricated clause `a sixth attempted execution is compatible...` (NOT_A_VERBATIM_CONTRACT_CLAUSE; replaced by REASONED_CONTRACT_SYNTHESIS of v1 line 99/100 + 021 §10 + 022 §§10–11 + 039 §2.1 + schedule 12281+1000*j), preserves DETERMINISTIC_FIRST_RESERVE_PROMOTION reserve-j01 13281/13282/8283 (38c5113b27568e14, 730475...) as FIFTH_VALID_MEMBER_CANDIDATE for reason PRIMARY_SEED_03_GOVERNANCE_INVALIDITY, and leaves CUDA-only composition disclosure, no j02/j03 chain, CRLF mechanism (not superseded), and five-seed UNRESOLVED/final SEALED unchanged.*
