# Amendment 109 — V5 Hedging Execution Authorization Provenance

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-211`
Type: `AUTHORIZATION_FREEZE_ONLY`
Branch: `main`
Starting HEAD: `19bd2271e5eeb5234faf8c9961af96eca1238763`
Safety branch: `safety/pre-v5-hedging-execution-auth-19bd227` at `19bd2271e5eeb5234faf8c9961af96eca1238763`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-EPISODE-IDENTITY-POSITION-AUDIT-CLOSURE-210` — `ACCEPTED`
Authorization commit: `583593cb340146be938cda4ffcbbe6db70b1eee2`
Authorization path: `reports/protocol/hedging_execution_authorization_211.json`
Authorization canonical SHA: `a4255a3da9a00bdb8bf01716463c52a9fdc41bc4b801281ae8f0ba7eafdfdc73`
Authorization Git blob: `f3bc2d058012cb1f0caaec018c67c4bb9ccc6fa2`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3`
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a...` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03...` / `8d8220c0...` — VALIDATED
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED
- Implementation commit: `66f0fce3f93c74090523a92617d5d980845e3b9d` (`fix(research): complete v5 hedging production execution path` — 7 files, 936 insertions, `cli/deep_hedging.py`/`hedger.step`/`generation` real NSDE/`trainer` batched)
- Implementation manifest SHA: `79cad575a932ed87dfd6336d058275431cd49b62988aabe20557eca60421bac3` for 15 paths (`src/neuralmarket/research/deep_hedging/*.py` 9 + `cli/deep_hedging.py`, `cli/main.py`, `core/device.py`, `core/runtime_identity.py`, `data/manifests.py`, `models/structured_vol_sde.py`)
- Amendment 108: `research_protocol_amendment_108.md` at `c0a4683e6b0f4011dc0508de02bdd927fa9ce9e979b0d726dbe604d854084dde` / `b8eeae383986ac38cd7a7c9043b52f793e7254cb` — split stratification `maturity_option_type_stratified_largest_remainder_v1`
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED

## 2. Task-210 acceptance

Task-210 `NM-R4-V5-DEEP-HEDGING-EPISODE-IDENTITY-POSITION-AUDIT-CLOSURE-210` at `19bd227` was `AUDIT_CLOSED_WITH_REPORT_ONLY_EPISODE_ID_POSITION_MISSTATEMENT` — original `episode_id` `0..49999` exactly once, `train_position` `0..39999` and `selection_position` `0..9999` correctly preserve `original episode_id` via `df_train["episode_id"]` and `df_selection["episode_id"]`, `reset_index(drop=True)` changes `DataFrame` index only, not `episode_id` column, `perm = PCG64(hedger_seed+epoch).permutation(40000)` indexes `train_position` `0..39999`, not `original`, `batch_positions = perm[start:end]` and `original` via `train_episode_ids[batch_positions]`, all scientific tensors `S`/`maturity`/`K`/`P0`/`option_type` use same `perm_idx`, no mixed indexing, selection `0..9999` vs original noncontiguous subset, `all_selection_losses` ordering does not alter `CVaR`, no false `position==ID` dependency.

Implementation correctly uses filtered tensor positions and preserves original episode IDs, and Task-209's statement was only inaccurate wording, not scientific.

Task-210 adjudicated state: `ACCEPTED`, `DEEP-HEDGING IMPLEMENTATION: VALIDATED`, `SCIENTIFIC TRAINING: READY_FOR_SEPARATE_EXECUTION_AUTHORIZATION`.

## 3. Authorization artifact (frozen, valid)

Authorization path: `reports/protocol/hedging_execution_authorization_211.json`

- Task ID: `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-211` (matches `^NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-[0-9]+$`)
- Schema: `hedging-execution-authorization-v1` (validated via `validate_authorization_schema`)
- Implementation commit: `66f0fce3f93c74090523a92617d5d980845e3b9d` (ancestor of HEAD, verified `git merge-base --is-ancestor 66f0fce3f93c74090523a92617d5d980845e3b9d HEAD`)
- Implementation manifest SHA: `79cad575a932ed87dfd6336d058275431cd49b62988aabe20557eca60421bac3` for 15 paths (verified `build_implementation_manifest` at `66f0fce3f93c74090523a92617d5d980845e3b9d` gives `79cad575a932ed87dfd6336d058275431cd49b62988aabe20557eca60421bac3` and `verify_implementation_manifest` with `authorized_commit=66f0fce3f93c74090523a92617d5d980845e3b9d` and `authorized_blobs` at HEAD passes, drift 0)
- Implementation source blobs: all 15 path->blob identities (sorted, verified `git hash-object` for each)
- Contract v3 canonical: `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / blob `eef7ad220db889166469799372759dfe1a96e35f` (verified `preflight_checks`)
- Runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (verified `build_runtime_identity` vs frozen)
- Member allowlist: 5 members `seed-01`, `seed-02`, `seed-04`, `seed-05`, `reserve-j01` (all `GATE_PASS_VALID` per `structured_vol_v5_n5_family_analysis_v1.json`)
- Checkpoint paths: `data/processed/research/model/structured-volatility-neural-sde-v5/<run_prefix>/checkpoint.pt` for each member, with `run_prefix` as per `RUN_PREFIXES`
- Checkpoint identities: `checkpoint_identities` (selected checkpoint raw SHA256) `seed-01: 452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f` (truncated display, full 64 in file), `seed-02: 9e6f8cd030d073d5c93ac36c94c55b09366f07b2f153f181fc82daedffc0064e`, `seed-04: 87d022152ba28f886b56bcf966ebc18d40e73d911258a83f01ece150ce8e7a89`, `seed-05: 3a71b12e1c0af08e1006b492aefd59d4e2b04ceee8e1f88a1ee07c0178f2d21a`, `reserve-j01: 50d14095d95386c0596b36297185c3a1eca6182b463adfae52370890c600d183` (full 64 in file)
- Checkpoint raw SHA map: same as above (full 64)
- Checkpoint Git hash map: `seed-01: 6820d07c0fb253a028c88e46b5db0b16363ae22c` (full 40 via `git hash-object`), etc.
- Synthetic RNG: `seed-01:42001`, `seed-02:42002`, `seed-04:42004`, `seed-05:42005`, `reserve-j01:42006`
- Costs: `[0.0, 0.0010, 0.0050]` exactly
- Hedger seeds: `[31001, 31002, 31003]` exactly
- Max generation: 5, Max training: 45
- Artifact roots: `["data/processed/research/hedging_synthetic", "data/processed/research/hedging_policies"]`
- Network: `false` (verified `payload.get("network") is False`)
- Final-test access: `false` (verified)
- No final-test entitlement, no external access, no alternate member/seed, no replacement, no retry/rerun, no wildcard checkpoint identity

All five members allowed exactly once, no extra member, all five checkpoint maps have identical key set (`seed-01` etc.), all checkpoint files/identities reconcile (`verify_nsde_checkpoint` checks `member`/`run_prefix`/`checkpoint_path`/`raw SHA`/`git hash`/`member association` and `model_state`/`sde_config` schema), synthetic RNG key set matches member key set, cost/hedger seeds exactly frozen, max generation 5 / max training 45, network false, final_test_access false, implementation commit ancestor, all 15 source blobs match, manifest SHA matches, contract SHA/blob matches, runtime field matches.

Authorization file is repository-relative (`reports/protocol/hedging_execution_authorization_211.json`), tracked (`git ls-files` not empty), clean (`git diff --name-only` and `git diff --cached --name-only` both empty), committed in current HEAD history (`git log --all --pretty=format:%H -- <path>` contains `583593c` and `git merge-base --is-ancestor 583593c HEAD` true), canonical LF SHA `a4255a3da9a00bdb8bf01716463c52a9fdc41bc4b801281ae8f0ba7eafdfdc73` (LF-canonical), raw SHA `486c7b161e23b9daa9bc290f4997fe2573c1b79f4b626c2e66c9352e44621743` (raw), Git blob `f3bc2d058012cb1f0caaec018c67c4bb9ccc6fa2` (via `git hash-object`), filtered worktree == committed Git object (`git diff HEAD` -> 0, `git hash-object` == `git ls-tree HEAD`).

## 4. Verification without execution

Before committing, read-only/schema validation helpers were used against candidate authorization bytes:

- `verify_authorization_artifact` checks repo-relative, tracked, clean, canonical, blob, commit, task family
- `validate_authorization_schema` checks all required fields and values
- `verify_implementation_manifest` checks ancestor and drift
- `preflight_checks` would check contract, runtime, clean tree, CUDA if executed

Do NOT call `generate-synthetic`, `train-policy`, `generate_and_persist_synthetic_dataset`, `train_one_policy`, do NOT invoke real checkpoint.

## 5. Scientific execution counters (still 0)

- Real synthetic generation: 0 (no `data/processed/research/hedging_synthetic` real datasets, only temp fixtures)
- Real NSDE inference: 0 (no `StructuredVolatilityNeuralSde` checkpoint instantiation beyond tiny fixture)
- Real GRU training: 0 (no `data/processed/research/hedging_policies` real checkpoints)
- Real synthetic datasets: 0
- Real policy checkpoints: 0
- Generation started markers: 0 (no `generation_execution_started.json` in `data/processed/research/hedging_synthetic`)
- Policy started markers: 0 (no `execution_started.json` in `hedging_policies`)
- Final-test markers: 0
- Final-test results: 0
- Final-test access: 0
- External: 0
- Network: 0
- Push: 0

Authorization is frozen but UNUSED, no invocation has been consumed, no scientific result exists.

## 6. What this task does not do

- Does not execute real synthetic generation (5 jobs) or real NSDE inference
- Does not execute real GRU training (45 jobs)
- Does not create real synthetic datasets or policy checkpoints
- Does not access final-test rows
- Does not external, network, or push
- Does not create or execute Task 212 here

This amendment is append-only, contains no self-referential hash.

Next governed action: `NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-EXECUTION-212` (Risk R5, Type SCIENTIFIC_EXECUTION, Task 212 must execute ONLY the five authorized synthetic-generation jobs, not GRU training, and after those five jobs, the next stage must independently audit all five generated datasets/manifests before any of the 45 policy-training jobs are executed).
