# Research Protocol Amendment 024

## V5 Replicate Training Runner Repair and Execution Contract v2

**Date:** 2026-08-19
**Status:** CONTRACT — repaired runner and v2 execution contract. No training. No validation. No final-test access.
**Task:** NM-R4-V5-TRAINING-RUNNER-REPAIR-030
**Audit:** NM-R4-V5-TRAINING-RUNNER-AUDIT-029 — REPAIR REQUIRED (7 blocking runner defects).
**Prior chain:** runner `3091dd5d7bd89ed9cdfee36fed97d197418c70e8` (blob `abdfbbcce829f5069746a1b5b3a59ebb0e2bcf79`, `6559ee7ad5bed0eec949547f8131f97d8201282ee1be359a55a9d578a37dcb85`) → audit 029 → repair commit `fd24c538a15d69ef2d27cecd878d2c31e8e7312e` (blob `8e3dadc2ee5a5c078ee3241995708e56ec8ed7c1`, sha `cd5cc6d74b59da82c797e45db2889b0a69e60ff8ffd076cb3bd25c437a6341ca`); execution contract v1 `97149dc3b25c7b65997664e3b67b800c6bed1008` (sha `9318e6e74061b193ea00f9711ebd1758c14335c9182f53351644e61d94fa0ee6`) now **SUPERSEDED**; new contract v2 below. Amendment 023 `869fb2a46a69b48fd1e08a78e24f2281086c24f08972a90142df8a0a49926b7b` (blob `5328f73cff24e8705bad1fe3583a2bb963989e`) and v1 contract blob `97149dc3b25c7b65997664e3b67b800c6bed1008` contained transcription errors in prior prompt — actual blobs above are authoritative.

---

## 1. Purpose and scope

Repair the seven blocking defects in the execution runner so that later training — when separately authorized — is mechanically fail-closed, cryptographically bound to runner + contract v2 identities, and always emits durable terminal evidence after irreversible start. Preserve all frozen scientific identities. Train nothing in this amendment.

## 2. Audit defects and repair mapping

| # | Defect | Repair |
|---|--------|--------|
| 1 | `--execute` created `execution_started.json` and returned `0` without training | Now `_run_scientific_training` is the sole reachable scientific call, invoked exactly once **after** `execution_started`; `--execute` without training now fails closed until authorization exists, and with authorization the single scientific call is always invoked |
| 2 | Authorization checked only 5 of 19 required fields | Now `REQUIRED_AUTH_FIELDS` (19) + seed tuple + blob/recipe/head + firewall fields are all enforced in `check_authorization`; missing/type/value/stale all fail closed |
| 3 | Runner identity not cryptographically bound; untracked/recommitted runner bypasses self-check | Now `_runner_self_check` requires tracked, has `HEAD` blob, blob == `HEAD` blob, clean; `check_authorization` recomputes current `runner_git_blob` and compares to `authorization.runner_git_blob`; no hard-coded self-hash |
| 4 | No terminal evidence machinery after irreversible start | Now `try/except/finally` after `execution_started` always persists `training_stdout.log`, `training_exit_code.txt`, `training_execution_manifest.json`, and on success `training_report.json`; manifest carries `FAILED`/`COMPLETED`, exception class/reason, hashes, counters |
| 5 | `execution_started.json` lacked full seed tuple + authorization identity | Now contains `schema_version`, `replicate_seed/model_init/data/eval`, `full_config_hash/run_prefix/family_hash`, `runner_blob`, `execution_contract_git_blob`, `schedule_git_blob`, `execution_recipe_head`, `authorization_path/git_blob`, `start_utc`, `attempt_number`, `training_invocations_before_start`, `validation/final_test/reserve` false |
| 6 | Failure-after-start and mocked-success tests absent | Now tests 25–40 exercise mocked success/failure exclusive-create, nonzero exit, transcript, FAILED manifest, false-success absence, second-attempt refusal |
| 7 | Validation-firewall test was vacuous (`... or True`) | Deleted; replaced by precise code-level firewall tests (§13) asserting no `split="validation"`, no `external_validation_harness`, no `final_test` builder |

## 3. Call graph (minimal orchestration, no scientific duplication)

Reuses exactly the accepted production/reproducibility helpers; no trainer/model/gate logic is copied:

```
load_schedule (blob-verified)
  -> get_member
  -> derive_effective_config (V5ExperimentConfig from frozen base YAML + schedule seed tuple)
     -> verify_config_hash (V5ExperimentConfig.config_hash, must equal 62c7406c.../e333325c.../77e7de9e.../1e8aa171...)
     -> verify_family_hash (canonical_dumps RNG-stripped payload -> 730475987368bf...)
  -> derive_report_dir / derive_model_dir (hash-derived, 16-char hex prefix)
  -> check_no_overwrite (both dirs absent + no execution_started)
  -> check_authorization (19 fields; see §4)
  -> _runner_self_check (tracked/clean/blob==HEAD)

Dry run: stops; prints DRY RUN OK.

Execute (after 15 exclusive-create execution_started):
  _run_scientific_training  (single reachable call)
    -> build_underlying_series(split="training" only, guarded boundary)
    -> build_windows / compute_context_features / fit_feature_normalizer / fit_cumret_scale / split_fit_selection
    -> build_v3_statistics
    -> set_deterministic_seeds(model_init_seed) + StructuredVolatilityNeuralSde
    -> train_internal_v3  (single training invocation)
    -> checkpoint.pt + training_curve.json
    -> refit_final_v3  (conditional on gate_passed, re-seeded)
    -> evaluate_gate_v2 (Gate-v2, fixed seeds 7777/7778/8801)
  -> terminal persistence (finally)
```

`run_v5_experiment` (which would touch validation) is **not** called. `build_underlying_series` is called only with `split="training"`; any other split raises before training.

## 4. Authorization exactness (19 fields)

Schema requires and runner enforces (§F of spec): `schema_version, authorization_task_id, member_id, replicate_seed, model_init_seed, data_seed, eval_seed, full_config_hash, run_prefix, family_methodology_identity, schedule_git_blob, schedule_sha256 (or local_worktree_sha256 alias), execution_contract_git_blob, runner_git_blob, execution_recipe_head, training_authorized, validation_authorized, final_test_authorized, reserve, max_training_invocations`. Additional rejected contradictions: wrong seed tuple, wrong runner/contract blob, wrong recipe recipe-head not ancestor of `HEAD`, wrong schedule blob, validation/final_test/reserve not false, `max_training_invocations != 1`.

Runner recomputes its **current** tracked blob (`git hash-object`) and compares to `authorization.runner_git_blob`; recomputes current contract v2 blob and compares to `authorization.execution_contract_git_blob`; never hard-codes its own blob.

## 5. execution_recipe_head semantics

`execution_recipe_head` is the immutable commit containing the repaired runner plus execution contract v2 **before** per-member authorization artifacts. At runtime: `execution_recipe_head` must be an ancestor of current `HEAD`; runner blob at `HEAD` equals `authorization.runner_git_blob`; contract v2 blob at `HEAD` equals `authorization.execution_contract_git_blob`; schedule blob equals `FROZEN_SCHEDULE_BLOB`; runner/contract/schedule are clean. No authorization artifact ever contains its own commit hash (avoids self-reference).

## 6. execution_started (repaired)

Exclusive `open("x")` immediately before scientific call; payload per §H of spec (schema 1.0, full seed tuple, hashes, runner/contract/schedule/recipe/authorization identities, `training_invocations_before_start = _SCIENTIFIC_INVOCATIONS`). Once written: never deleted; second execution refuses via overwrite check.

## 7. Terminal evidence (guaranteed)

In `try/except/finally` after irreversible start: always `training_stdout.log` (captured buffer), `training_exit_code.txt` (0 or nonzero), `training_execution_manifest.json` (`FAILED` with `exception_class/failure_reason/start/end_utc/exit/scientific_training_invocations` or `COMPLETED` with report hashes). On `COMPLETED` also `training_report.json` with Amendment 021 §11 evidence. Validation/external/final/provider counters always 0. Return `0` only on genuine `COMPLETED`; `nonzero` on any failure. No retry; no reserve fallback.

## 8. Scientific invocation count

`_SCIENTIFIC_INVOCATIONS` guards `_run_scientific_training`; called exactly once per successful authorization path; second call in same process raises `exceeded 1`. No retry loop. Tests 25–27, 37 prove single invocation.

## 9. v1 supersession

Execution contract v1 (`reports/research/structured_vol_v5_training_execution_contract_v1.json`, blob `97149dc3b25c7b65997664e3b67b800c6bed1008`, sha `9318e6e74061b193ea00f9711ebd1758c14335c9182f53351644e61d94fa0ee6`) is classified **SUPERSEDED_EXECUTION_CONTRACT, TRAINING_AUTHORIZATION_ELIGIBLE = false**. Not edited. New contract v2 is authoritative.

## 10. Historical quarantine

Three untracked historical reports (`structured_vol_v5_report.json c5ed284fe..., v3 585ecd886a..., v4 cb4610d08e...`) remain `HISTORICAL_NON_MEMBER_EVIDENCE, eligible false`; runner refuses generic path.

## 11. What this repair does not do

No training. No reserves. No validation/final-test/hedging. No scientific source change. No config/checkpoint mutation.

## 12. Next action

Independent read-only audit of repaired runner + contract v2 before any per-member authorization.

---

*Amendment 024 is append-only. Amendments 021–023 remain otherwise unchanged.*
