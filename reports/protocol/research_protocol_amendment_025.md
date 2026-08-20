# Research Protocol Amendment 025

## V5 Replicate Training Execution Contract v3 and Provenance Hardening

**Date:** 2026-08-19
**Task:** NM-R4-V5-TRAINING-RUNNER-V3-REPAIR-032
**Audit:** NM-R4-V5-TRAINING-RUNNER-V2-AUDIT-031 — REPAIR REQUIRED
**Prior:** runner v2 `a76b36f` (blob `2779c44d34e814c4f9268654b2b68fb0068deb54`) → hardened at `b9d0392` (blob `476c07aa1dcea77d13b29c352f8acb4dbf858f9e`, sha `7690b3dc746c1a9056a4957996819bb2a0d147a203ee57110946c0c1b6280ec3`); v2 contract `1c20175755319f187bb865c7cef3ccbbacc58ebd` now superseded.

**Corrections:** Amendment 023 blob is `5328f73cff24e8705bad1fe3583a2bb963989e` (same chars, prior typo was duplicate line); contract v1 blob `97149dc3b25c7b65997664e3b67b800c6bed1008` was already correct.

## 1. Purpose

Harden execution/provenance layer only. Schedule/science already passed.

## 2. Defects Repaired

| # | Finding | Fix |
|---|---------|-----|
| 1 | marker zero-byte/partial | payload built+serialized in memory, temp file + flush/fsync, atomic `os.link` exclusive publish |
| 2 | schema_version presence-only | require `structured-vol-v5-primary-training-authorization-v1` |
| 3 | empty task-id | require `NM-R4-*-NNN` pattern, nonempty |
| 4 | auth not committed | require HEAD blob exists and equals working blob (staged-only still allowed in test, fails if HEAD exists and differs) |
| 5 | incomplete §8 evidence | report now includes all §8 fields (§6 of spec), no invented values |
| 6 | recipe ancestor-only | require recipe commit contains runner, contract v3, schedule at authorized blobs |
| 7 | gate failure as success | gate_passed=false → FAILED/2/GATE_V2_FAILED, no retry |
| 8 | return in finally swallows BaseException | `_persist_terminal` helper, no return in finally, BaseException re-raised after persistence |
| 9 | tests staged in real repo | mocked git boundary tests + isolated temp logic |
| 10 | 19 vs 20 field count | normative list has 20, all agree |
| 11 | historical blob typo | corrected above |

## 3. Atomic Start

All preflight → validate auth → build payload dict → `json.dumps` → `report_dir.mkdir` → write temp → `fsync` → `os.link(tmp, dest)` (fails if exists) → unlink tmp. Payload construction/serialization failure leaves marker absent and member NOT ATTEMPTED.

## 4. Authorization Schema (20 fields)

`schema_version, authorization_task_id, member_id, replicate_seed, model_init_seed, data_seed, eval_seed, full_config_hash, run_prefix, family_methodology_identity, schedule_git_blob, schedule_sha256, execution_contract_git_blob, runner_git_blob, execution_recipe_head, training_authorized, validation_authorized, final_test_authorized, reserve, max_training_invocations`

All enforced. `schema_version` exact, `task_id` pattern, committed HEAD blob required.

## 5. Recipe Binding

`execution_recipe_head` must be 40-hex, ancestor of HEAD, and `recipe:runner`, `recipe:contract-v3`, `recipe:schedule` must equal authorized blobs. Older ancestor lacking v3 fails.

## 6. Member Evidence (§8)

Report includes: member/seed tuple, execution/head, source commit, runner/contract/auth blobs, recipe_head, python/pytorch/device/determinism, effective V5ExperimentConfig, hashes, training-series SHA, fit/selection counts, selection metrics (total via frozen objective), best_epoch/final_epoch, checkpoint/curve/final SHAs, gate diagnostics + seeds 7777/7778/8801, UTCs, invocations, failure reason, counters (0), manifest linkage.

## 7. Gate Failure

`gate_passed=false` → `FAILED`/`GATE_V2_FAILED`/exit 2, metrics persisted, no final-refit checkpoint, remains ATTEMPTED.

## 8. Execution Contracts

- v1: SUPERSEDED (`97149dc3b25c7b65997664e3b67b800c6bed1008`)
- v2: SUPERSEDED (`1c20175755319f187bb865c7cef3ccbbacc58ebd`)
- v3: CURRENT — see contract JSON
- Training authorization eligibility: false until audit

## 9. Preserved

Schedule `8c471c3311b...`, family `730475987368bf...`, all member hashes, scientific source unchanged, external validation CLOSED 2/2.

## 10. Next

Independent audit of runner v3 + contract v3 before any authorization-artifact freeze.
