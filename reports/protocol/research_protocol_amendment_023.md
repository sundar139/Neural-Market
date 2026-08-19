# Research Protocol Amendment 023

## V5 Replicate Training Execution and Evidence Contract

**Date:** 2026-08-19
**Status:** CONTRACT — execution and evidence rules for the five-member training family. No training. No validation. No final-test access.
**Task:** NM-R4-V5-TRAINING-AUTHORIZATION-028
**Prior:** Amendment 022 `4416f7a9a847bade1b8d864ae582f9d22971df389035b26d0a7e2858772c4f31` (schedule), schedule `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` (blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`), Amendment 021 `4ad94bceed70bb70a282bc472b97bc5fd0aad8bffb856d18bad3743c4bd822c2` (RNG contract), replicate contract `c28eb6d8d8de89381de9ff28b697c8190d1910af87612a57bbe9df768aa0c98f` (family hash `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`). Audit 025 — VALIDATED. External validation CLOSED 2/2, third FORBIDDEN. Runner frozen at `3091dd5d7bd89ed9cdfee36fed97d197418c70e8` (blob `abdfbbcce829f5069746a1b5b3a59ebb0e2bcf79`, worktree SHA `6559ee7ad5bed0eec949547f8131f97d8201282ee1be359a55a9d578a37dcb85`).

---

## 1. Purpose

Freeze a single reusable, fail-closed per-member training runner and its execution-evidence contract before any member #2–#5 scientific training. The runner makes later execution mechanically incapable of using an unscheduled seed, changing methodology, overwriting an existing member, reusing the historical generic report path, retrying silently, accessing validation/final test, or executing reserves without separate authorization. No training occurs in this amendment.

## 2. Per-member report-path defect (resolved)

The historical generic path `reports/research/structured_vol_v5_report.json` (SHA `c5ed284fe44af3cd2a04d8553d97b5830042c7cfbf1404a453ea084b23512548`, historical non-member) must not be used by any scheduled member.

Per-member report namespace (frozen, hash-derived):

```
reports/research/structured_vol_v5_replicates/<RUN_PREFIX>/
```

For each future member execution, the runner derives `<RUN_PREFIX>` from the recomputed `V5ExperimentConfig.config_hash()` (first 16 hex chars), not from a user-supplied string. Each namespace may contain exactly:

```
training_report.json
training_stdout.log
training_exit_code.txt
training_execution_manifest.json
execution_started.json
```

Expected primaries:

- v5-seed-02 → `…/62c7406cb3a2c642/` (hash `62c7406cb3a2c64237d39559370d70a27f8111f7dd1dc7ee581da9bd475cf00b`)
- v5-seed-03 → `…/e333325c804d95d2/` (hash `e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955`)
- v5-seed-04 → `…/77e7de9efabb7ce3/` (hash `77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b`)
- v5-seed-05 → `…/1e8aa171993a1aba/` (hash `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897`)

These directories do not exist at `3091dd5`; the runner refuses to overwrite an existing one.

## 3. Model-output namespaces

Scientific output remains the existing convention:

```
data/processed/research/model/structured-volatility-neural-sde-v5/<RUN_PREFIX>/
```

Before execution, the runner requires the selected member's model directory to be absent. Member #1 (`5bdbaabd2fb257a7`) is `EXISTING_FROZEN` and the runner refuses it as an execution target. Reserves use prospective prefixes `38c5113b27568e14`, `423277df1ac4cd9a`, `e89b0ac0956d197e` but are not executable under this contract.

## 4. Runner orchestration contract

File: `reports/research/evidence/structured_vol_v5_replicate_training_runner.py`
Commit: `3091dd5d7bd89ed9cdfee36fed97d197418c70e8` · Blob: `abdfbbcce829f5069746a1b5b3a59ebb0e2bcf79` · Worktree SHA-256: `6559ee7ad5bed0eec949547f8131f97d8201282ee1be359a55a9d578a37dcb85` (blob is authoritative for tracked text; local SHA is informational)

- Minimal orchestration/evidence only. No scientific model/trainer/Gate-v2 logic is duplicated. The runner imports and reuses exact production helpers (`load_v5_config`, `V5ExperimentConfig.config_hash`, `train_internal_v3` / `refit_final_v3` / `evaluate_gate_v2`-class helpers) when training is later authorized.
- If `run_v5_experiment` would touch validation, the runner uses a lower internal API that cannot (`train_internal_v3`-level, training-only series, fail-closed split boundary `\u2260 validation`). The runner contains no `build_underlying_series(split="validation")` and no `external_validation_harness` import.
- Invariant: runner self-verifies `git hash-object` equals `git rev-parse HEAD:<runner_path>` and that the runner file has no working-tree diff before any execution; `git blob` is authoritative.

CLI:

```
.venv/Scripts/python.exe reports/research/evidence/structured_vol_v5_replicate_training_runner.py \
  --member-id v5-seed-02 \
  [--authorization <FUTURE_AUTHORIZATION_JSON>] \
  [--execute]
```

- Default (no `--execute`): **DRY RUN ONLY** — may load schedule/contracts, recompute config, verify hashes, derive paths, verify absence, print preflight. Dry run creates no model/report directories, constructs no scientific training data beyond config objects, and does not train/simulate/Gate-evaluate.
- `--execute` without a tracked/committed authorization artifact is **refused** (exit 2). No such authorization exists at `3091dd5`, so training is impossible even if misinvoked.

Allowlist: exactly `v5-seed-02, v5-seed-03, v5-seed-04, v5-seed-05`. Member `v5-seed-01` (EXISTING_FROZEN) and any `reserve-*` are refused (exit 2). Unlisted ids are refused.

## 5. Future authorization handshake (requirements)

A later governed task must create a tracked/committed authorization artifact for the *single* member to be executed, with at least:

```
schema_version, authorization_task_id,
member_id, replicate_seed, model_init_seed, data_seed, eval_seed,
full_config_hash, run_prefix, family_methodology_identity,
schedule SHA/blob, execution-contract SHA/blob,
runner commit/blob/SHA, execution-recipe HEAD,
training_authorized = true, validation_authorized = false,
final_test_authorized = false, reserve = false,
max_training_invocations = 1
```

The runner requires the artifact to be tracked (`git ls-files --error-unmatch`) and clean (`git diff/diff --cached --quiet`). No such artifact exists at `3091dd5`.

## 6. Irreversible-start semantics

Immediately before the first scientific training call, future execution must create `execution_started.json` via **exclusive create** (`open("x")`) containing: member id, seed tuple, config hash, run prefix, family hash, runner blob/head, execution-recipe HEAD, authorization identity, start UTC, `attempt = 1`.

If the file already exists: **REFUSE** (exit 2). Once created, the member is considered **ATTEMPTED** even if Python later fails. No automatic retry. No second invocation. Recovery requires a separate governed task. Tests use `tmp_path` only.

## 7. Training-invocation and failure rules

- At most **ONE** scientific training flow invocation per process (`_INVOCATIONS` guard). No internal retry loop, no alternate-seed fallback, no reserve fallback, no "try again on numerical failure".
- A failed member produces failure evidence and stops. The predeclared failed-seed policy (Amendments 021 §§10–11 / 022 §§10–11) remains controlling: failed primaries stay in roster, are counted in `failed_in_primary`, never silently discarded or relabelled, reserves (if separately authorized) are reported separately.

## 8. Seed/config verification

For any future member execution:

1. Load frozen schedule `8c471c33...` and verify blob.
2. Derive effective config from frozen seed-01 config by changing **only** `training.model_init_seed` and `training.data_seed` (`eval_seed` stays `8283`).
3. Recompute `V5ExperimentConfig.config_hash()` and require the exact scheduled hash (`62c7406c...`, `e333325c...`, `77e7de9e...`, `1e8aa171...`).
4. Recompute `family_methodology_identity` (RNG-stripped) and require `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`.

Any mismatch: fail closed before execution. Runner self-verifies via `derive_effective_config` / `verify_config_hash` / `verify_family_hash` (unit-proven).

## 9. Common evaluation / Gate policy

- `eval_seed = 8283` — `COMMON_FIXED_POST_TRAINING` for all five.
- Gate seeds common fixed: `7777 / 7778 / 8801`.
- Runner does not mutate these; future report records them explicitly.
- Later analysis must not treat common evaluation randomness as independent training-seed uncertainty (Amendment 021 §14).

## 10. Per-member evidence output (future requirement)

`training_report.json` under the per-member report namespace must contain at least:

```
member_id, replicate_seed, model_init_seed, data_seed, eval_seed,
starting/execution Git HEAD, scientific source 357971a67c68492fc0c4f5bf31f94f9685639f65,
runner path/blob/SHA, Python version, PyTorch version, device cpu, determinism,
full effective V5ExperimentConfig, full config_hash, run_prefix, family_methodology_identity,
training-series SHA, fit/selection identities,
initial/best selection loss, best_epoch, final_epoch,
selected checkpoint + curve + final-refit checkpoint paths/SHAs,
Gate-v2 six metrics + per-criterion result under fixed gate seeds,
training start/end UTC, process exit, training invocation count,
failure status/reason,
validation_constructions = 0, external_evaluations = 0, final_test_accesses = 0, provider/network = 0
```

No raw validation values. No final-test values.

Transcripts/manifests are per-member: `training_stdout.log`, `training_exit_code.txt`, `training_execution_manifest.json` (cross-references report/transcript/exit/checkpoint/curve SHAs + runner/authorization/schedule/config/family identities, write-once/exclusive where practicable).

## 11. Tracked-text identity policy

For **tracked text** artifacts (`*.md`, `*.json`, `*.py`, `*.yaml` under Git): **Git blob ID is authoritative** cross-platform byte identity (`git hash-object` / `git rev-parse HEAD:<path>`). Worktree `sha256` may also be recorded as `local_worktree_sha256` but is not load-bearing (worktree CRLF/LF ambiguity, `*.ps1 text eol=crlf`). Runner verifies `HEAD:<runner_path>` equals the contract's runner blob and that the file has no diff.

For **binary/untracked immutable scientific artifacts** (checkpoints `.pt`, training curves before commit): continue using `sha256` as frozen.

Amendment 021's earlier `local_worktree_sha256` note is superseded by this rule for tracked text. Old evidence is not rewritten.

## 12. Manifest-schema wording (supersession)

Amendment 021 §12 suggested the replicate contract might be reused as a family manifest schema. Amendment 022 §13 requires a **separately versioned** completed-family manifest.

**Amendment 022 supersedes Amendment 021 on this point.** The future completed-family manifest will carry distinct schema version `structured-vol-v5-completed-family-v1`. The schedule JSON (`structured_vol_v5_seed_schedule_v1.json`) and replicate contract (`structured_vol_v5_replicate_seed_contract_v1.json`) are **not** completed-family manifests and must not be treated as such. That manifest is not created in this task.

## 13. Historical non-member evidence (logical quarantine)

The three existing historical untracked reports are **not** deleted or moved. They are hashed and explicitly excluded from member evidence:

| path | sha256 | config identity if determinable | classification | eligible_for_member_evidence |
|------|--------|----------------------------------|----------------|------------------------------|
| `reports/research/structured_vol_v5_report.json` | `c5ed284fe44af3cd2a04d8553d97b5830042c7cfbf1404a453ea084b23512548` | `69623a82f91ff0db` lineage (historic v5, invalidated by Amendment 016), `c5ed28...` | HISTORICAL_NON_MEMBER_EVIDENCE | false |
| `reports/research/neural_sde_signature_v3_report.json` | `585ecd886a3619c0ee95242bd8cf668fe529e48e67d42b41676133519645a312` | v3 smoke `a60107...` | HISTORICAL_NON_MEMBER_EVIDENCE | false |
| `reports/research/neural_sde_signature_v4_report.json` | `cb4610d08e9545562d78d8c72b1a7d01381bc33ae1ac35e0a564397e70ece29c` | v4 `87f1d5a2...` | HISTORICAL_NON_MEMBER_EVIDENCE | false |

The runner derives per-member paths under `structured_vol_v5_replicates/<prefix>/` and refuses the generic `structured_vol_v5_report.json` path. This is logical quarantine without touching preserved historical bytes.

## 14. Prospective reserve identities

Reserves are **not authorized** for execution. Verified prospective identities (from schedule §9):

- reserve-01: replicate `13281` data `13282` → hash `38c5113b27568e14eabb04621595e7114b8140577459abfe7061ffafd118b605` prefix `38c5113b27568e14`
- reserve-02: replicate `14281` data `14282` → hash `423277df1ac4cd9a4088141e4cc483561b29d4aa6ff2973e57d379cdbe3d2969` prefix `423277df1ac4cd9a`
- reserve-03: replicate `15281` data `15282` → hash `e89b0ac0956d197e8b335b28873e6d6802ff8176a21e18f35a5d3d7e88dbb2df` prefix `e89b0ac0956d197e`

`reserve_execution_authorized = false`. No reserve directories created.

## 15. Future completed-family schema requirement

After primary training finishes, a separately governed task must create `structured-vol-v5-completed-family-v1` manifest containing the per-member evidence requirements from Amendment 021 §11 plus:

```
primary_scheduled, primary_attempted, primary_valid_completed,
failed_in_primary, family_methodology_identity,
runner identity, execution contract identity
```

No raw validation values. No final-test values. Not created in this task.

## 16. External-validation firewall

`external_validation_state: CLOSED`, `construction_count: 2`, `effective_max: 2`, `third_permitted: false`. Member #1: existing report-only `a28345587989ea1d91d46ed7c9b332151b84af98c0d4918f0fc281d03ba4ca38`; members #2–#5: no external evidence; reserves: no external evidence; transfer forbidden. No validation reconstruction ever.

## 17. What this amendment does not do

- Does not train any member or reserve.
- Does not authorize final test or hedging.
- Does not choose new seed values or modify frozen schedule.
- Does not install `sigkernel`/`torchsde` or add dependencies.
- Does not create a completed-family manifest.

## 18. Next action

Independent read-only audit of the frozen runner (`3091dd5`) and this execution contract before any member authorization or training.

## 19. Prohibited actions (this contract)

- Executing `v5-seed-01` or any reserve via this runner.
- Overwriting an existing model/report namespace or reusing `structured_vol_v5_report.json`.
- Supplying a member id or prefix outside the allowlist.
- Bypassing `--authorization` for `--execute`.
- Automatic retry after a started member.
- Any validation, final-test, or hedging execution.

---

*Amendment 023 is append-only. Amendments 021 and 022 remain otherwise unchanged except for the explicit supersessions in §§11–12. Historical reports are quarantined logically; no bytes were moved. Any training or final-test access requires a separate, explicitly authorized task.*
