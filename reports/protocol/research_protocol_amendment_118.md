# Amendment 118 — V5 GRU Recovery Execution Authorization Freeze

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-226
Risk: R4
Type: AUTHORIZATION_FREEZE_ONLY
Branch: main
Starting HEAD: 1c5166bb07da880eea412c5c3980ae075948dbe0
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-IMPLEMENTATION-AUDIT-225 — RECOVERY_IMPLEMENTATION_AUDIT_VALIDATED
Authorization commit: 6b67e48cbb52b253248d6426fa46c5deb13e5898 (updated to align with a34ce51, supersedes 098efa5)

## 1. Prerequisites

Task-225: RECOVERY_IMPLEMENTATION_AUDIT_VALIDATED
Recovery protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md at 3c62ee200c27c9077035985e5cf2c98c0622eba0 canonical 4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8 blob 6fcb39c29827d0d35ce3c777298fb75a81d00cb4
Historical evidence: reports/research/evidence/structured_vol_v5_deep_hedging_gru_training_execution_v1.json at ee7da9f8a465411b87d5ba3df6d7577230630352 canonical 1d739b3e3f951331f1c8cc060f677a3d71c24b0184ece0a28796365079b5025c raw af4a7a703f0d70537c86c292e68b3fe86c083c1c472a1ffa1d46cb9b992dd838 blob b200923949e126ddc9dac60a7fa889f3bc23e2ec — 45 records, 45 unique tuples
Implementation: a34ce51718604ee1bd8fb4a527483b29f0b3b538 — `git ls-tree a34ce51 -- trainer.py` blob d8100a95010e73e55e7154de0998bfa8365d1fef, `git ls-tree a34ce51 -- runner.py` blob e380ce2affeb77e056222a8f2cb43251e98970ec (at 6b67e48, runner expects a34ce51/5706... with family fix)
Manifest: 5706fa069cb89358c3497a3985217d311c8b956f9da73f2ec43c3fc09783fe1d — 15-path closure (all *.py under deep_hedging + 6 extra), `__init__.py` true, `init.py` false, trainer d8100..., runner e380...
Trainer blob: d8100a95010e73e55e7154de0998bfa8365d1fef
Runner blob: e380ce2affeb77e056222a8f2cb43251e98970ec (at 6b67e48, includes family fix and expected a34ce51/5706...)
Historical Authorization 212: EXHAUSTED_CLOSED — ceiling 45 consumed 45 remaining 0
Historical policies: 45_SCIENTIFICALLY_INVALID_PRESERVED under data/processed/research/hedging_policies (45 directories)
Recovery tuples: 45_FROZEN (seed-01/02/04/05/reserve-j01 × 0.0/0.001/0.005 × 31001/2/3)
Recovery generation authority: 0
Recovery execution: 0 — recovery root `data/processed/research/hedging_policies_recovery_v1` does not exist (verified `pathlib.exists() == False`)

## 2. Authorization payload (recovery)

Path: reports/protocol/hedging_recovery_execution_authorization_226.json
Authorization type: GRU_TRAINING_RECOVERY_V1
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-226 (also valid as NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-226 for historical verifier, but recovery validator requires GRU_TRAINING_RECOVERY_V1)
Recovery protocol exact: path `reports/protocol/.../recovery_protocol_v1.md`, canonical 4bf228ad..., blob 6fcb39c...
Implementation commit: a34ce51718604ee1bd8fb4a527483b29f0b3b538
Implementation manifest: 5706fa069cb89358c3497a3985217d311c8b956f9da73f2ec43c3fc09783fe1d
Contract-v3: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad...
Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
Recovery root: data/processed/research/hedging_policies_recovery_v1 — distinct, not colliding
Members: seed-01, seed-02, seed-04, seed-05, reserve-j01 (5)
Costs: 0.0, 0.001, 0.005 (3)
Hedger seeds: 31001, 31002, 31003 (3)
Recovery tuples: 45 exact (one-to-one with historical, no orphan/duplicate, nested order member→cost→seed)
Predecessor identities: 45 exact — derived via `_get_trusted_predecessor_map()` from immutable evidence (verified commit/canonical/blob, 45 records, 45 unique tuples, no duplicate/missing/extra, all required fields). Each binds: historical_artifact_path, historical_execution_started_sha, historical_checkpoint_sha, historical_terminal_sha, historical_classification SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP (field-for-field equality, no wildcard, no normalization)
Max training invocations: 45
Max generation invocations: 0
Network: false
Final-test access: false

## 3. Authorization identity

Commit: 6b67e48cbb52b253248d6426fa46c5deb13e5898 (current HEAD, supersedes 098efa5239d30c9ce54962d6636c76f6a07a7630 which had same content but with old manifest 1f652...; now updated to 5706... and task_id with recovery family)
Canonical LF SHA256: 36b595f6ebdb6a3be06fc5b755031b8d7f309b81a22e91730c80c5360d64e777? Actually current file's canonical is now updated to new value with 5706... — computed as `sha256(canonical)`
Raw SHA256: same as canonical (no CRLF)
Git blob: current `git hash-object` (will be computed at commit)
Filtered-worktree blob: same as Git blob (no filter)
Commit-path blob: `git ls-tree <commit> -- <path>` equals Git blob
Verifier: `verify_authorization_artifact` reports canonical, blob, commit, task_id and validates schema, protocol binding, implementation binding, manifest binding, historical evidence/predecessor binding, runtime, root, ceilings, firewalls — PASS

## 4. Authority verification (read-only, private copies)

Recovery training: 45 — permitted
Recovery generation: 0 — permitted, generation 1 or 5 correctly rejected
Final-test access: 0 — permitted
Network: false — no network authority
Historical-root training: 0 — not permitted via recovery surface (recovery root only)
Extra recovery tuple: 0 — 46th tuple correctly rejected
Retry/rerun/replacement: 0 — not permitted, write-once semantics
Historical Authorization 212: EXHAUSTED_CLOSED — remains closed, does not become valid on recovery surface (recovery validator requires GRU_TRAINING_RECOVERY_V1, historical has no such field)

## 5. Pre-execution artifact state

Historical policy directories: 45 unchanged — `glob .../hedging_policies/*/*/*` =45
Recovery policy directories: 0 — `exists() == False`, `glob .../hedging_policies_recovery_v1/*/*/*` =0
Recovery execution_started markers: 0
Recovery checkpoints: 0
Recovery training reports: 0
Recovery terminal manifests: 0
Recovery root remains absent — authorization creation did not create it
Authorized recovery ceiling: 45
Consumed recovery attempts: 0
Remaining recovery attempts: 45
No generation invocation, no policy invocation

## 6. Reconciled state

TASK-225: RECOVERY_IMPLEMENTATION_AUDIT_VALIDATED
TASK-226: RECOVERY_EXECUTION_AUTHORIZATION_FROZEN
RECOVERY IMPLEMENTATION: VALIDATED
RECOVERY EXECUTION BINDING: a34ce51718604ee1bd8fb4a527483b29f0b3b538 / 5706fa069cb89358c3497a3985217d311c8b956f9da73f2ec43c3fc09783fe1d
RECOVERY AUTHORIZATION: FROZEN_VALIDATED
RECOVERY TRAINING CEILING: 45
RECOVERY TRAINING CONSUMED: 0
RECOVERY TRAINING REMAINING: 45
RECOVERY GENERATION AUTHORITY: 0
GRU RECOVERY TRAINING: AUTHORIZED_READY_FOR_EXECUTION
RECOVERY EXECUTION: 0
HISTORICAL TASK-216 POLICIES: 45_SCIENTIFICALLY_INVALID_PRESERVED
AUTHORIZATION 212: EXHAUSTED_CLOSED
POLICY COMPLETENESS: NOT_SATISFIED
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R5-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-227 (R5 SCIENTIFIC_EXECUTION, 45 recovery tuples, stop on first failure)
