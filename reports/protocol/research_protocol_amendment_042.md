# Amendment 042 — V5 Seed-05 CUDA Training Authorization Freeze

**Date:** 2026-08-21
**Task:** NM-R4-V5-SEED-05-AUTHORIZATION-FREEZE-065
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `e39678b33576b91b69503f232bb26620fb1d9117`
**Safety branch:** `safety/pre-v5-seed05-authorization-freeze-e39678b`
**Prior sensitivity:** Amendments 040 + 041 (effective sensitivity contract, Audit 064 VALIDATED WITH NON-BLOCKING FINDINGS)
**Methodology:** `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT` (Amendment 039)
**Authorization commit:** `c937742` (v2 artifact `v5-seed-05-v2.json`); this amendment `e39678b → c937742 → <this>`
**Status:** AUTHORIZATION FREEZE — one prospective v2 CUDA authorization committed and documented; no --execute, no training, no execution_started, no checkpoint/curve/Gate result, no reserve/validation/final/hedging.

## 1. Audit 064 and effective sensitivity contract

Audit 064 validated the repaired sensitivity preregistration (Amendments 040 + 041) with non-blocking findings. Amendments 040 + 041 remain the effective pre-result sensitivity contract (unconditional runtime-heterogeneity sensitivity, three-way member semantics, mandatory LOMO, mandatory CPU-vs-mixed, no causal backend claim, H2 caveat, no rerun/discard/retune/redesign, outcome-independent inclusion). This amendment does not alter any sensitivity rule.

Methodology `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT` (Amendment 039) remains validated; five-seed requirement remains unresolved (currently 3 valid historical members: seed-01/02/04).

## 2. Authorization artifact (prospective, frozen, not executed)

### 2.1 Path and hashes

- path: `reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-05-v2.json`
- schema: `structured-vol-v5-primary-training-authorization-v2`
- SHA-256: `29d11cf53da65429327623ec1211b9b7b35b46e5cf7025d53a47d7f3e7fe49c2` (verify via `sha256sum` / `Get-FileHash`)
- Git blob: `d77766320792c459df7566cdcf6ec12806e0da91`
- committed: YES (`HEAD:reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-05-v2.json` exists, worktree == HEAD, `git ls-files --error-unmatch` passes, tracked, no staged/working diff)
- authorization commit: `c937742 docs(research): freeze v5 seed-05 CUDA authorization` (contains ONLY the v2 artifact; 25 insertions)
- historical `v5-seed-05.json` preserved: YES (blob `dcfb2c188c5155111e5dcfc39ca331b49ce2f80b`, `structured-vol-v5-primary-training-authorization-v1` from `NM-R4-V5-PRIMARY-AUTHORIZATION-FREEZE-037`, inspection-only; now coexists with `v5-seed-05-v2.json`)
- prospective v2 count: exactly 1 (`v5-seed-05-v2.json`); no other `authorization-v2` artifacts exist

Directory after freeze contains both: `v5-seed-05.json` (historical inspection-only) and `v5-seed-05-v2.json` (sole prospective execution authorization). No ambiguity about which can execute — runner `authorize_execution` requires `authorization-v2` with `requested_device=cuda`/`expected_resolved_device=cuda` and exact runtime identity; v1 reports "schema v1 is historical-only; new scientific execution requires schema v2 with CUDA runtime binding".

### 2.2 Scientific identity (frozen, recomputed via real codepath)

- member: `v5-seed-05`
- replicate_seed: `12281`
- model_init_seed: `12281`
- data_seed: `12282`
- eval_seed: `8283` (COMMON_FIXED, Gate seeds `7777/7778/8801` frozen separately per Amendments 021/022)
- full_config_hash: `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897` (verified via `derive_effective_config("v5-seed-05").config_hash()` == expected; run_prefix `1e8aa171993a1aba`)
- family_methodology_identity: `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (RNG-stripped family hash, verified)
- gate evaluation seeds: `7777` (selection), `7778` (drift/diffusion), `8801` (bootstrap) — unchanged, common-fixed
- architecture/loss/optimizer/hyperparameters/windowing/Gate criteria/thresholds: unchanged (frozen `configs/research/structured_vol_neural_sde_v5.yaml`, Gate spec `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469`)

### 2.3 Prospective CUDA binding

- recipe (commit): `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a` (`execution_recipe_head`; ancestor of HEAD, contains runner/contract/schedule at correct blobs)
- runner blob: `05b704b254387d8f5ffdf1d847dd4289303b565c` (`reports/research/evidence/structured_vol_v5_replicate_training_runner.py`, device-aware, runtime-bound)
- structured-vol experiment blob: `16f5ec631eb71756084f3e74d006c31da2c6bcd8` (`src/neuralmarket/research/structured_vol_experiment.py`)
- trainer blob: `85aabc6798b22a60bd4d94d4ee86bfae81a8a172` (`src/neuralmarket/research/neural_sde_trainer_v3.py`)
- Gate-v2 blob: `05af8d0d864eddaae8c43e1cc3936d28e89abaf3` (Gate-v2 evaluator)
- auth-v2 schema blob: `c74958f2c5d99753b05bf64c9b6880ee9bd37d94` (`reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json`)
- execution-contract blob: `84a59c4d966b349be705a8a29fad07f81282ebdc` (`reports/research/structured_vol_v5_training_execution_contract_v5.json`, CURRENT per `structured_vol_v5_training_execution_contract_v5.json`)
- schedule blob: `558d08bfee98dbd0c170d65e6a9b1737700c9e98` (`reports/research/structured_vol_v5_seed_schedule_v1.json`, SHA-256 `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`)
- runtime-identity implementation blob: `817ba53e2474c6e8dd7ecf15d64e0766e75f73e9` (`src/neuralmarket/core/runtime_identity.py`)
- runtime path: `src/neuralmarket/core/runtime_identity.py` (canonical)
- requested_device: `cuda`
- expected_resolved_device: `cuda`
- expected_runtime_identity_sha256: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (`runtime-identity-v1`, normative capture after `resolve_device` + `configure_device_determinism` before `execution_started`)
- runtime schema: `runtime-identity-v1` (implicit via `expected_runtime_identity_sha256`; explicit `expected_runtime_identity_schema` omitted — optional per schema, canonical `runtime-identity-v1`)
- historical CPU identities `20d90f7...` / `7b46e0f6...` NOT cited as prospective basis (explicitly historical-only per Amendment 041)

### 2.4 Authorization semantics

- training_authorized: `true`
- max_training_invocations: `1`
- validation_authorized: `false`
- external/validation firewall: `false` (no external evaluation authorized)
- final_test_authorized: `false` (no final access)
- reserve: `false`
- other schema firewalls: all satisfied (REQUIRED_AUTH_FIELDS_V2 = 23 fields present, no extras; `requested_device == expected_resolved_device == cuda`; `expected_runtime_identity_sha256` is 64 lowercase hex)
- authorization_task_id: `NM-R4-V5-SEED-05-AUTHORIZATION-FREEZE-065`

### 2.5 Preflight verification (read-only/synthetic, no --execute of real member)

- schema/config/family/runner/recipe checks: PASS (inspect_authorization + check_authorization structural checks pass; config hash / family / blobs / schedule / recipe containment verified)
- CPU environment (`.venv`, torch without CUDA): CUDA execution preflight REFUSES before marker (rc=2, "CUDA requested but unavailable — fail closed, no CPU fallback"); marker count 0, invocation count 0, report/model residue 0
- GPU runtime (`.venv-gpu`, torch 2.13.0+cu132, CUDA 13.2, RTX 4070 Laptop): `build_runtime_identity(requested_device="cuda", resolved_device="cuda")` reproduces `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`; authorization/runtime checks reach scientific-call boundary ONLY when intercepted/spied before science (patched `_run_scientific_training` intercepted invocation count 1, marker not persisted to real filesystem; real execution not performed)
- no real member execution: verified (no `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/execution_started.json`; no checkpoint/curve/Gate result created)

## 3. Sensitivity interaction (unchanged by authorization)

Authorization creation does NOT alter the preregistered sensitivity contract (040 + 041). Effective rules remain:

- GATE_PASS_VALID (governance-valid + protocol-valid + Gate PASS): INCLUDED in family summaries, LOMO, CPU-vs-mixed.
- GATE_FAIL_VALID (governance-valid + protocol-valid + Gate FAIL): INCLUDED in family summaries, LOMO, CPU-vs-mixed. Scientific poor performance never silently excluded.
- VALID_EXECUTION_NO_GATE_RESULT (governance-valid + protocol-valid execution that yields no Gate result because the Gate evaluation itself is unavailable/incomplete — e.g., crash before Gate, missing diagnostics, or explicitly Gate-missing evidence bundle; NOT a scientific Gate verdict): DEFINED for completeness. Required handling (from existing failed-seed contract, Amendments 021 section 10 / 022 section 11): the execution is governance-valid and protocol-valid, so it is INCLUDED in valid-replicate numerical summaries for any training scalar that is available (initial_selection_total_loss, best_selection_total_loss, best_epoch, final_epoch, improvement) and contributes to failure-rate accounting; the missing Gate outcome is recorded as `Gate result: unavailable` and excluded only from Gate-criterion numerical summaries that require the missing value. This status MUST NOT become an outcome-based discard mechanism — inclusion is by execution validity, not by Gate verdict.
- GOVERNANCE_INVALID (execution invalid because of governance/protocol failure, e.g., DOUBLE_SCIENTIFIC_INVOCATION; enumeration closed to governance/protocol failures, NOT broadened to scientific poor performance such as Gate FAIL, high loss, or extreme epoch): retained permanently in scheduled-primary history and failure reporting; excluded from valid scientific-replicate numerical sensitivity summaries because execution itself is inadmissible.

No post-result sensitivity redesign, no rerun/retune/backend-switch/Gate-threshold/seed change, no authorization retry/replacement merely because the eventual result is poor. Authorization does not increase training invocation count, execution_started count, or valid primary count — seed-05 remains `NOT_ATTEMPTED` after this task.

## 4. Audit 064 documentation-only findings closed

Non-blocking findings from Audit 064 are closed conservatively:

1. Section attribution correction: Amendment 041 section 2 supersession list attribution "section attribution identified by Audit 064" is clarified — the supersession of 040's RBF sentence and line-number-pinned references originates from 041 sections 6 and 7 respectively, not from a mis-attributed section 2. This clarification does not reopen any supersession scope.

2. Remaining "(if admissible)" historical wording: all operative occurrences of "if admissible" / "if seed-05 succeeds" / "if seed-05 passes" where Gate scientific outcome controlled sensitivity inclusion are enumerated as superseded in Amendment 041 sections 2–5 & 8. Any residual verbatim string in 040's historical text is marked superseded and non-operative per 041 section 2 items 3–6 and section 8 verification search. No undisclosed outcome-contingent inclusion remains operative.

3. GOVERNANCE_INVALID enumeration: closed without broadening — defined as governance/protocol failure (e.g., DOUBLE_SCIENTIFIC_INVOCATION, invocation count >1, device/runtime mismatch, missing authorization) and explicitly NOT expanded to scientific poor performance (Gate FAIL, high/low selection loss, extreme epoch). The valid-execution/no-Gate status in section 3 above is prospectively defined without creating a new discard path.

## 5. No execution and final-test status

No --execute, no scientific training, no execution_started artifact (verified: `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/` absent), no checkpoint/curve/Gate result, no reserve/validation/external/final/hedging, no provider/network. Final test remains sealed (split `2023-11-22` onward per `split_manifest_v1`; `final_test_accesses == 0`).

Seed-05 remains `NOT_ATTEMPTED` and authorization is `FROZEN_PENDING_INDEPENDENT_AUDIT` — not authorized for execution until audit.

## 6. What this amendment does NOT do

Does not modify Amendments 040/041; does not change scientific source, model, hyperparameters, splits, loss, windowing, optimizer, Gate thresholds, determinism, recipe, or schedule; does not create a second authorization or execution; does not broaden GOVERNANCE_INVALID to scientific failure.

## 7. Required next action

Next task MUST independently audit the committed `v5-seed-05-v2.json` authorization (read-only) before any execution task exists. No execution may be inferred from this amendment alone.

---
*Amendment 042 freezes the one prospective v2 CUDA authorization for v5-seed-05 (c937742, blob d7776632...) with exact CUDA binding (6a6b9f8.../05b704b2.../17e3bb52...) and documents Audit 064 closure. Amendments 040/041 remain the effective pre-result sensitivity contract.*
