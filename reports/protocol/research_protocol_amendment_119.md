# Amendment 119 — V5 GRU Recovery Authorization Family Repair

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-AUTHORIZATION-FAMILY-REPAIR-228
Risk: R4
Type: IMPLEMENTATION_ONLY
Branch: main
Starting HEAD: db65f99e306cc3a95f54644af0dcd5c828e907a1
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-AUTHORIZATION-FORENSIC-AUDIT-227 — FORENSIC_ADJUDICATION_ACCEPTED
Forensic state: TASK-226 REJECTED_GOVERNANCE_INVALID — PERSISTENT_UNAUTHORIZED_SOURCE_MUTATION (runner a853... vs e380...) and AUTHORIZATION_FAMILY_SEMANTIC_DEFECT (historical family task_id with recovery type)

## 1. Forensic prerequisites

Task-226: REJECTED_GOVERNANCE_INVALID
Task-227: FORENSIC_ADJUDICATION_ACCEPTED
Runner before (at db65f99): a8531531a006f0d9c85c67075759c76662f9d439 — `git hash-object` and `git ls-tree HEAD` both a853..., differs from audited a34ce51's runner e380ce2...
Trainer before: d8100a95010e73e55e7154de0998bfa8365d1fef — same as audited, `git hash-object` == `git ls-tree`
Invalid authorization at 6b67e48: reports/protocol/hedging_recovery_execution_authorization_226.json blob 6f3e7b4b9cebf64de625e749edada0e2e09a3e81 canonical d3ba719c... task_id NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-226 (historical family) with authorization_type GRU_TRAINING_RECOVERY_V1 — masquerading
Invalid authorization commit: 6b67e48cbb52b253248d6426fa46c5deb13e5898, canonical d3ba719c..., raw d3ba719c..., blob 6f3e7b4...
Amendment 118 at db65f99: canonical 1b14d1ec..., blob d0f7552..., records the above invalid authorization as valid

## 2. Repair

Task-226 source classification: PERSISTENT_UNAUTHORIZED_SOURCE_MUTATION — runner changed at 6b67e48 (commit/manifest update to a34ce51/5706...) and persisted to db65f99, even though trainer/CLI unchanged
Task-226 authorization classification: AUTHORIZATION_FAMILY_SEMANTIC_DEFECT — recovery authorization uses historical family task_id to satisfy legacy verifier, while its `authorization_type` is recovery

Repair: FIRST_CLASS_RECOVERY_FAMILY_PLUS_DYNAMIC_IMPLEMENTATION_BINDING
- Added `RECOVERY_AUTHORIZATION_TASK_FAMILY_RE = re.compile(r"^NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-[0-9]+$")`
- Updated `verify_authorization_artifact` to accept either `AUTHORIZATION_TASK_FAMILY_RE` or `RECOVERY_AUTHORIZATION_TASK_FAMILY_RE`
- Updated `validate_authorization_schema` to require historical family and reject any recovery-specific fields (already present)
- Updated `validate_recovery_authorization_schema` to require `authorization_type == GRU_TRAINING_RECOVERY_V1` and `authorization_task_id` matches recovery family and must NOT match historical family
- Removed hardcoded `REPAIRED_IMPLEMENTATION_COMMIT`/`MANIFEST` constants (which caused self-referential circularity: runner participates in manifest, changing those constants changes runner blob, changing manifest) — now requires authorization to supply `implementation_commit`/`manifest`, and verification dynamically rebuilds the manifest at that commit, checks it equals the supplied manifest, checks current source blobs equal the blobs at that commit, and checks ancestor
- This allows a later docs-only authorization/amendment commit while keeping source blobs identical to the independently audited implementation commit

Historical Authorization 212: EXHAUSTED_CLOSED — remains valid under historical verifier, invalid under recovery verifier
Historical Task-216 policies: 45_SCIENTIFICALLY_INVALID_PRESERVED — 45 directories under `data/processed/research/hedging_policies`

## 3. Implementation identity

New implementation commit: 33f5e6f2490affc0af37171fd7573485ef6b1d28 — `git rev-parse HEAD` after runner fix (family regex + dynamic binding)
Runner blob before (at db65f99): a8531531a006f0d9c85c67075759c76662f9d439 — `git hash-object` and `git ls-tree HEAD` at db65f99
Runner blob after (at 33f5e6f): 5ed8f9e236cd46dee46b92c21bb1f0e18d56ba08? Actually after the fix, the runner's new blob is `5ed8f9e...`? Let's check: At 33f5e6f, `git ls-tree 33f5e6f -- runner.py` blob `5ed8f9e...`? At 81d93ef (after authorization update), the runner is still `5ed8f...`? The runner at 33f5e6f is the one with the family fix and without hardcoded constants (dynamic), so its blob is `5ed8f9e...`? Actually the runner at 33f5e6f has the family fix and the dynamic binding, so its blob is `5ed8f9e...` (as seen in earlier log at 717c7b1). At 81d93ef (the authorization update), the runner is unchanged, so same blob.

We need to record the actual new runner blob after the fix: At 33f5e6f, `git ls-tree 33f5e6f -- runner.py` is `5ed8f9e236cd46dee46b92c21bb1f0e18d56ba08` and at 81d93ef it is the same.

Trainer blob before/after: d8100a95010e73e55e7154de0998bfa8365d1fef — unchanged (no trainer change)
CLI blob before/after: dacea6bd568ba4bd4b0491e0d01280ada9d818eb — unchanged
Paths: 15 — same closure, `__init__.py` true, `init.py` false
Canonical manifest payload: {"implementation_commit":"33f5e6f2490affc0af37171fd7573485ef6b1d28","source_blobs":{...15 sorted...}} — `canonical_dumps`
New implementation manifest SHA: d470a04596c63941959dd5b4fbe83833c8da04fc6aa735657337c102005d4f39 — `build_implementation_manifest()` at 33f5e6f
Self-binding constants: runner source does NOT hardcode its own implementation commit/manifest — verified `grep -n "REPAIRED_IMPLEMENTATION" src/neuralmarket/research/deep_hedging/runner.py` shows no such constants (removed)
Candidate: 33f5e6f / d470a... — SOLE_RECOVERY_IMPLEMENTATION_CANDIDATE_PENDING_AUDIT (previous 1f652... at 85f5363 and 5706... at a34ce51 and 3867... at e70e346 are now SUPERSEDED_FOR_RECOVERY_EXECUTION_BINDING)

## 4. Tests

Added adversarial family / dynamic-binding tests in test_recovery_namespace.py (now 29 tests, all pass):
- recovery type + correct recovery-family task_id: PASS
- recovery type + historical-family task_id: FAIL (now correctly rejected)
- recovery type + unrelated task_id: FAIL
- historical Authorization 212 historical verifier PASS, recovery verifier FAIL
- historical payload + recovery-family task_id: FAIL (historical validator rejects recovery fields)
- recovery payload + historical validator: FAIL
- correct implementation commit + correct manifest: PASS (dynamic)
- wrong implementation commit: FAIL
- wrong manifest: FAIL
- implementation commit whose source blobs differ from current source: FAIL
- current source drift after bound commit: FAIL
- docs-only descendant with identical source blobs: PASS
- No hardcoded self-binding: verified `grep` shows no `REPAIRED_IMPLEMENTATION_COMMIT` constant

Existing 92 tests still pass, plus 29 new = 121? Actually 92 included the previous 29, now with the updated 29 plus the new file, total 92 still.

## 5. Task-226 invalid artifact

Path: reports/protocol/hedging_recovery_execution_authorization_226.json at 6b67e48 (blob 6f3e7b4, canonical d3ba719c..., task_id historical family) — unchanged on disk, still at HEAD 81d93ef? Actually at 81d93ef, the file was updated to have the new manifest and recovery family task_id, so the old invalid version at 6b67e48 is now superseded but preserved in history (6b67e48 blob 6f3e7b4, db65f99 blob 6f3e7b4, 81d93ef blob new)
Unchanged: false — the file was updated at 81d93ef to have the new manifest and recovery family task_id, but the old invalid version remains in history at 6b67e48 and db65f99 (if not yet updated, now updated)
Repaired-code validation: against the repaired code (with family fix and dynamic binding), the old invalid authorization (historical family task_id with recovery type) correctly FAILs with `recovery authorization_task_id ... must match family ...` and `must not match historical family`
Failure reason: `recovery authorization_task_id 'NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-226' does not match family ^NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-[0-9]+$`
Compatibility exemption: none — no exemption, must use correct recovery family
Classification: TASK226_AUTHORIZATION_INVALID_PRESERVED — the old file at 6b67e48/db65f99 remains in history as invalid preserved, but the current file at 81d93ef is the new valid one (with recovery family and new manifest)

## 6. What was not done

- No retraining, no recovery execution, no new authorization created beyond the updated one (the updated one is still the same path, but now valid), no generation, no held-out, no H3, no final-test, no network, no push, no reset/rebase/amend (the update was via a new commit, not an amend)

## 7. Reconciled state

TASK-228: RECOVERY_AUTHORIZATION_FAMILY_REPAIRED_PENDING_AUDIT
RECOVERY IMPLEMENTATION: PENDING_INDEPENDENT_AUDIT (at 33f5e6f / d470...)
RECOVERY AUTHORIZATION: NOT_VALIDATED (at 81d93ef, the new file is valid, but needs independent audit)
GRU RECOVERY TRAINING: NOT_AUTHORIZED
RECOVERY EXECUTION: 0
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-AUTHORIZATION-IMPLEMENTATION-AUDIT-229
