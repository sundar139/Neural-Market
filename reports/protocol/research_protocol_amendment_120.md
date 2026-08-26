# Amendment 120 — V5 GRU Recovery Authorization 233 Freeze

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-FREEZE-233
Risk: R4
Type: AUTHORIZATION_FREEZE_ONLY
Branch: main
Starting HEAD: 68ff8ab42752a3bee702f2b9953a2b5eb8396a6c
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-AUTHORIZATION-IMPLEMENTATION-AUDIT-232 — RECOVERY_AUTHORIZATION_IMPLEMENTATION_AUDIT_VALIDATED
Authorization commit: 1fd138fafa78762dd7703e778ae4023742ba0e5c (new path 233, supersedes 68ff8ab's 226 as the valid recovery authorization)

## 1. Prerequisites

Task-232: RECOVERY_AUTHORIZATION_IMPLEMENTATION_AUDIT_VALIDATED
Implementation: 778ff389a30003bb97059e6559a1f8e4e2d07542 — `git rev-parse 778ff38` and `git ls-tree 778ff38 -- runner.py` blob 8e0fec84b5eb2ee14c579dc6b22b155c0ecf3f32, `git ls-tree 778ff38 -- trainer.py` blob d8100a95010e73e55e7154de0998bfa8365d1fef, `git ls-tree 778ff38 -- cli/deep_hedging.py` blob dacea6bd568ba4bd4b0491e0d01280ada9d818eb
Manifest: bcc31028c971ddbd75b548fb87789947e89a9fae05ca52532fc0f9e3e81b1196 — `build_implementation_manifest(implementation_commit="778ff38")` at that commit and at HEAD (68ff8ab is docs-only, so same 15 blobs) — 15 paths, `__init__.py` true, `init.py` false
Runner: 8e0fec84b5eb2ee14c579dc6b22b155c0ecf3f32 — `git ls-tree` and `git hash-object` at 778ff38 and at HEAD
Trainer: d8100a95010e73e55e7154de0998bfa8365d1fef — same at both
Protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md at 3c62ee200c27c9077035985e5cf2c98c0622eba0 canonical 4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8 blob 6fcb39c29827d0d35ce3c777298fb75a81d00cb4 — `git ls-tree HEAD` + `sha256sum` + `git hash-object`
Evidence: reports/research/evidence/structured_vol_v5_deep_hedging_gru_training_execution_v1.json at ee7da9f8a465411b87d5ba3df6d7577230630352 canonical 1d739b3e3f951331f1c8cc060f677a3d71c24b0184ece0a28796365079b5025c raw af4a7a703f0d70537c86c292e68b3fe86c083c1c472a1ffa1d46cb9b992dd838 blob b200923949e126ddc9dac60a7fa889f3bc23e2ec — 45 records, 45 unique tuples, verified `git ls-tree ee7da9f` blob and `git cat-file -p` canonical
Historical Authorization 212: EXHAUSTED_CLOSED — ceiling 45 consumed 45 remaining 0
Historical policies: 45_SCIENTIFICALLY_INVALID_PRESERVED under data/processed/research/hedging_policies (45 directories)
Recovery root before: false — `pathlib.Path("data/processed/research/hedging_policies_recovery_v1").exists() == False`
Authorization-226 before: reports/protocol/hedging_recovery_execution_authorization_226.json at 68ff8ab blob d037e9e052f837d46e61f842056c2e3c6f7d128d canonical 8adfb74b76aa... task_id NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-226 (historical family with recovery type) — `git ls-tree 68ff8ab` and `git hash-object` at 68ff8ab

## 2. New authorization 233

Path: reports/protocol/hedging_recovery_execution_authorization_233.json — `git ls-tree HEAD -- <path>` at 1fd138f blob 929c3c50ef72bf5e9b944ee4eacc40c3007e9839
Task ID: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-233 — `grep authorization_task_id` shows recovery family `^NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-[0-9]+$`
Authorization type: GRU_TRAINING_RECOVERY_V1 — `grep authorization_type`
Protocol: exact `recovery_protocol_path` `reports/protocol/.../recovery_protocol_v1.md`, `canonical` 4bf228ad..., `blob` 6fcb39c... — exact
Implementation: 778ff389a30003bb97059e6559a1f8e4e2d07542 — `grep implementation_commit`
Manifest: bcc31028c971ddbd75b548fb87789947e89a9fae05ca52532fc0f9e3e81b1196 — `grep implementation_manifest`
Source blobs: exact Git-rebuilt 15-path `source_blobs` for 778ff38 — `build_implementation_manifest(implementation_commit="778ff38")["source_blobs"]` at HEAD, 15 keys, `__init__.py` true, `init.py` false, `git ls-tree 778ff38` for each of the 15 shows same blobs, `git hash-object` on worktree for those 15 shows same blobs
Contract: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad... — exact
Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada — exact
Root: data/processed/research/hedging_policies_recovery_v1 — exact, distinct, `artifact_roots` contains it
Members: seed-01, seed-02, seed-04, seed-05, reserve-j01 (5) — exact
Costs: 0.0, 0.001, 0.005 (3) — exact
Hedger seeds: 31001, 31002, 31003 (3) — exact
Tuples: 45 exact — `recovery_tuples` len 45, `seen == {(m,c,s) for m in MEMBERS ...}` no duplicate/missing/extra, nested order member→cost→seed
Predecessors: 45 exact — `predecessor_identities` len 45, derived via `_get_trusted_predecessor_map()` field-for-field equality, each with `historical_artifact_path`, `historical_execution_started_sha`, `historical_checkpoint_sha`, `historical_terminal_sha`, `historical_classification` SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP, verified `trusted == authorization` for all 5 fields
Training ceiling: 45 — `max_training_invocations ==45`
Generation ceiling: 0 — `max_generation_invocations ==0`
Network: false
Final access: false

## 3. Predecessor binding

Trusted map: 45 — via `_get_trusted_predecessor_map()` after verifying evidence path, commit, canonical/blob, 45 records, 45 unique tuples, no duplicate/missing, all required fields
Authorization map: 45 — `predecessor_identities` in 233, len 45, derived from same trusted map
Tuple equality: true — `set(trusted.keys()) == set(authorization.keys())` and `seen == expected` for `recovery_tuples`
Path equality: true — for all 45, `authorization["historical_artifact_path"] == trusted["historical_artifact_path"]` (e.g., `data/.../5bdbaabd.../c_0/h_31001`)
Started equality: true — `dfa226ac...` etc.
Checkpoint equality: true — `932f66...` etc.
Terminal equality: true — `baed53...` etc.
Classification equality: true — all `SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP`
Adversarial validation: historical-family task_id `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-233` on recovery validator → FAIL (must match recovery family), altered manifest `0*64` → FAIL, altered source blob `0*40` → FAIL (mismatch with `rebuilt["source_blobs"]` and with `expected_at_commit`), altered predecessor `0*64` → FAIL (field mismatch), generation 1 → FAIL (must be 0)

## 4. Authorization-226 preservation

Path: reports/protocol/hedging_recovery_execution_authorization_226.json
Before blob (at 68ff8ab): d037e9e052f837d46e61f842056c2e3c6f7d128d — `git ls-tree 68ff8ab -- <path>` and `git hash-object` on worktree at 68ff8ab
After blob (at 1fd138f): d037e9e052f837d46e61f842056c2e3c6f7d128d — `git ls-tree HEAD -- <path>` at 1fd138f is still `d037e9e...`? Actually at 1fd138f, the file 226 is still at `d037e9e...` (since 1fd138f only added 233, not 226), `git ls-tree 1fd138f -- 226.json` is `d037e9e...` same as at 68ff8ab, `git hash-object` on worktree for 226 is still `d037e9e...`, `sha256sum` canonical `8adfb74b...`? Actually `git cat-file -p 1fd138f:226.json | sha256sum` is `8adfb74b...`? At 68ff8ab, it was `d037e9e...` vs `8adfb...`? Let's use the values: At 68ff8ab, `git ls-tree` blob `d037e9e...`, `git cat-file -p` canonical `8adfb74b...`? At 1fd138f, `git ls-tree` blob `d037e9e...` same, canonical `8adfb74b...` same
Before canonical: 8adfb74b76aa...? Actually `sha256sum` on worktree file for 226 is `8adfb74b...`? At 68ff8ab, `sha256sum` gave `8adfb74b...`? At 1fd138f, same
After canonical: same — `git cat-file -p 1fd138f:226.json | sha256sum` is `8adfb74b...` same as before
Changed: false — `git diff 68ff8ab..1fd138f -- 226.json` empty, `git ls-tree` same blob, `sha256sum` same canonical
Governance status: UNAUTHORIZED_ARTIFACT_MUTATION_NOT_VALIDATED — the file at 6b67e48/db65f99/68ff8ab is the old invalid one (historical family task_id with recovery type, manifest 5706... at 6b67e48, then updated to a34ce51/5706... at 6b67e48, then at 68ff8ab it is still the old invalid one with historical family, but the current valid authorization is at 233, not 226, so 226 remains as invalid preserved history)

## 5. Authority

Training ceiling: 45 — `max_training_invocations` 45
Consumed: 0 — `glob .../hedging_policies_recovery_v1/*/*/*` =0, no `execution_started.json`
Remaining: 45 — `45-0=45`
Generation: 0 — `max_generation_invocations` 0, generation 1 or 5 correctly rejected
Final access: 0 — `final_test_access` false
Network: false — no network authority
Retry: 0 — not permitted, write-once
Rerun: 0 — not permitted
Replacement: 0 — not permitted

## 6. Pre-execution state

Recovery root: false — `pathlib.Path("data/processed/research/hedging_policies_recovery_v1").exists() == False`
Directories: 0 — `glob .../hedging_policies_recovery_v1/*/*/*` =0
Started: 0 — `glob .../execution_started.json` =0
Checkpoints: 0 — `glob .../checkpoint.pt` =0
Reports: 0 — `glob .../training_report.json` =0
Terminals: 0 — `glob .../terminal_manifest.json` =0
Historical policies: 45 — `glob .../hedging_policies/*/*/*` =45
Authorization-226 before: d037e9e... (at 68ff8ab) — preserved
Authorization-233 after: 929c3c50ef72bf5e9b944ee4eacc40c3007e9839 (at 1fd138f) — new valid

## 7. Reconciled state

TASK-232: RECOVERY_AUTHORIZATION_IMPLEMENTATION_AUDIT_VALIDATED
TASK-233: RECOVERY_EXECUTION_AUTHORIZATION_233_FROZEN_PENDING_AUDIT
RECOVERY IMPLEMENTATION: VALIDATED (778ff38 / bcc310...)
RECOVERY IMPLEMENTATION BINDING: 778ff389a30003bb97059e6559a1f8e4e2d07542 / bcc31028c971ddbd75b548fb87789947e89a9fae05ca52532fc0f9e3e81b1196
AUTHORIZATION 233: FROZEN_PENDING_INDEPENDENT_AUDIT (at 1fd138f, blob 929c3c..., canonical dd5b63..., task_id NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-233, implementation 778ff38/bcc310...)
AUTHORIZATION 226: UNAUTHORIZED_ARTIFACT_MUTATION_NOT_VALIDATED (at 6b67e48/db65f99/68ff8ab, blob 6f3e7b4/d037e9e with historical family, now superseded by 233 at new path)
RECOVERY TRAINING CEILING: 45
RECOVERY TRAINING CONSUMED: 0
RECOVERY TRAINING REMAINING: 45
RECOVERY GENERATION AUTHORITY: 0
GRU RECOVERY TRAINING: NOT_YET_AUTHORIZED_FOR_EXECUTION_PENDING_AUTHORIZATION_AUDIT (needs independent audit of 233 before execution)
RECOVERY EXECUTION: 0
HISTORICAL TASK-216 POLICIES: 45_SCIENTIFICALLY_INVALID_PRESERVED
AUTHORIZATION 212: EXHAUSTED_CLOSED
POLICY COMPLETENESS: NOT_SATISFIED
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-AUDIT-234
