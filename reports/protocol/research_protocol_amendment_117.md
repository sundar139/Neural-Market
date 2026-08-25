# Amendment 117 — V5 GRU Recovery Authorization Binding Repair

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-AUTHORIZATION-BINDING-REPAIR-224
Risk: R4
Type: IMPLEMENTATION_ONLY
Branch: main
Starting HEAD: 6ddc4ad5738180bac410279894092b16ae69c9e5
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-NAMESPACE-IMPLEMENTATION-223 — RECOVERY_NAMESPACE_IMPLEMENTED_PENDING_AUDIT
Repair commit: a34ce51718604ee1bd8fb4a527483b29f0b3b538

## 1. Prior state

Task-223: RECOVERY_NAMESPACE_IMPLEMENTATION_REQUIRES_BINDING_REPAIR
Current candidate recovery implementation: e70e3465395e074d9b94c48383b6a7397a2d2df0 manifest 3867e66c02f5a6feba43f4ecad289e94c156392e86c9d723a6a01477df867eb6
Blocking findings at e70e346:
1. Recovery predecessor authorization entries structurally validated (tuple count 45, field presence, hash shape, classification) but exact field-for-field cryptographic equality against immutable Task-216 execution evidence not proven — adversarial wrong 64-hex historical_checkpoint_sha and wrong historical_artifact_path both passed validation before repair (proven via tiny adversarial fixture with correct 45 tuples but one wrong SHA/path).
2. Recovery validator reports `max_generation_invocations == 5` despite `SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION`.
3. Future authorization binding described ambiguously as potentially using either 3867e66... or 1f6524... instead of one exact final audited recovery implementation identity.

## 2. Historical evidence (immutable)

Path: reports/research/evidence/structured_vol_v5_deep_hedging_gru_training_execution_v1.json
Commit: ee7da9f8a465411b87d5ba3df6d7577230630352
Canonical LF SHA256: 1d739b3e3f951331f1c8cc060f677a3d71c24b0184ece0a28796365079b5025c
Raw SHA256: af4a7a703f0d70537c86c292e68b3fe86c083c1c472a1ffa1d46cb9b992dd838
Git blob: b200923949e126ddc9dac60a7fa889f3bc23e2ec
Records: 45
Tuples: exact frozen 45 (seed-01/02/04/05/reserve-j01 × 0.0/0.001/0.005 × 31001/2/3), no duplicate, no missing
Byte match: verified via `git cat-file -p HEAD:` canonical/raw, `git hash-object`, `git log --all -- <path>` contains ee7da9f, current worktree bytes match committed identity — no mutation

## 3. Repair

Defect: PREDECESSOR_IDENTITIES_NOT_PROVEN_AGAINST_IMMUTABLE_TASK216_EVIDENCE
Repair: FIELD_FOR_FIELD_PREDECESSOR_BINDING
- Added trusted helper `_get_trusted_predecessor_map()` in runner.py that derives expected predecessor map from immutable evidence ONLY after verifying evidence path exact, committed/canonical/blob identity exact, record count 45, tuple set exact frozen 45, no duplicate, all required historical fields present. Derives per tuple: historical_artifact_path (parent of checkpoint_path), historical_execution_started_sha, historical_checkpoint_sha, historical_terminal_sha, historical_classification = SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP (from frozen audit adjudication).
- After structural validation, `validate_recovery_authorization_schema` now compares `authorization predecessor_identities` against trusted expected map for all 45 tuples, requiring exact equality for tuple key, historical_artifact_path, historical_execution_started_sha, historical_checkpoint_sha, historical_terminal_sha, historical_classification. Any mismatch → AuthorizationError identifying tuple, field, expected, actual. No wildcard, no normalization that permits alternate paths, no omitted field, no extra tuple.
- Recovery generation authority: changed `max_generation_invocations` requirement from 5 to 0 (if field required, must be 0; recovery authorization granting generation >0 now fails). Historical Authorization 212 remains unchanged (5). Normal historical generation/training surfaces unchanged. Recovery public surface never calls generation.
- Preserved recovery science/routing exactly: GRU 7/64/2/dropout0, features, prev_delta, optimizer, CVaR, training loop, fail-close, synthetic datasets, member/cost/seed, tuple order, recovery root, write-once, historical root, selection, early stopping all unchanged. Recovery remains routed through one shared `_train_one_policy_internal` (no trainer duplication). If trainer.py required no change, its blob unchanged (proven same blob d8100a... before and after).

Historical predecessor tuples: 45 exact — verified via trusted map, no orphan/duplicate
Recovery generation authority: 0 — `max_generation_invocations` must be 0, recovery with 1 or 5 now fails (tested)
Recovery training ceiling: 45 — unchanged
Historical Authorization 212: EXHAUSTED_CLOSED — 45 consumed, 0 remaining, must not be reused
Trainer science: UNCHANGED — optimization loop still single, verified
Recovery root: UNCHANGED — `data/processed/research/hedging_policies_recovery_v1`

## 4. Implementation identity

New implementation commit: a34ce51718604ee1bd8fb4a527483b29f0b3b538
Trainer blob before (at e70e346): d8100a95010e73e55e7154de0998bfa8365d1fef
Trainer blob after (at a34ce51): d8100a95010e73e55e7154de0998bfa8365d1fef — UNCHANGED (no trainer change, as preferred)
Runner blob before: 49130c75ce97e994d15c0dc00b51f458251f7122
Runner blob after: e380ce2affeb77e056222a8f2cb43251e98970ec — changed (added trusted helper and field-for-field check, generation 0)
All 15 source paths (sorted, same closure):
  src/neuralmarket/cli/deep_hedging.py dacea6bd568ba4bd4b0491e0d01280ada9d818eb
  src/neuralmarket/cli/main.py ac7aa07e3304e91894fd5717f33c40b57bc83ae4
  src/neuralmarket/core/device.py 5f7f7a1ec29407c5a1734a71a994f444cf092386
  src/neuralmarket/core/runtime_identity.py 817ba53e2474c6e8dd7ecf15d64e0766e75f73e9
  src/neuralmarket/data/manifests.py 7ec3a80a795f82bfd19020bd21358e76a300615d
  src/neuralmarket/models/structured_vol_sde.py e828a8748216cc9d8d79593e1dd2e42a6226ab08
  src/neuralmarket/research/deep_hedging/__init__.py bd994657eab9407ff8593b2c2ad3ede31a689f44
  src/neuralmarket/research/deep_hedging/artifacts.py 28e3254a16977970a0860f9fc438d05e3949ac30
  src/neuralmarket/research/deep_hedging/cvar.py c03166afeb23b34d8fbf8d3d29357933eca2524a
  src/neuralmarket/research/deep_hedging/generation.py 1b8710fc77362eb59a7167b3b4575d8b93f63d12
  src/neuralmarket/research/deep_hedging/hedger.py 9a003e45687e1bbd409bde2c37ed39644be9e2ad
  src/neuralmarket/research/deep_hedging/pnl.py 122a00c996f8d4d01b89474fe98dee5ec49a393f
  src/neuralmarket/research/deep_hedging/runner.py e380ce2affeb77e056222a8f2cb43251e98970ec
  src/neuralmarket/research/deep_hedging/synthetic.py f3838634a6afc57b438d1baa2d078e37d12dacb5
  src/neuralmarket/research/deep_hedging/trainer.py d8100a95010e73e55e7154de0998bfa8365d1fef
Canonical manifest: {"implementation_commit":"a34ce51718604ee1bd8fb4a527483b29f0b3b538","source_blobs":{...15 sorted...}}
New manifest SHA: 5706fa069cb89358c3497a3985217d311c8b956f9da73f2ec43c3fc09783fe1d
Previous candidate manifests:
  1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20 at 85f5363: SUPERSEDED_FOR_RECOVERY_EXECUTION_BINDING
  3867e66c02f5a6feba43f4ecad289e94c156392e86c9d723a6a01477df867eb6 at e70e346: SUPERSEDED_FOR_RECOVERY_EXECUTION_BINDING
New Task-224 implementation/manifest: SOLE_CANDIDATE_PENDING_AUDIT — a34ce51 / 5706fa... (only candidate for future recovery authorization)

Actual recovery authorization: NOT_CREATED — no JSON created, no recovery root directory created
Recovery execution: 0 — no real 40k/10k training

## 5. Adversarial authorization tests (private tmp_path fixtures)

Added tests in test_recovery_namespace.py (now 29 tests) proving recovery validator rejects:

- wrong historical_artifact_path for one otherwise-valid tuple — REJECTED
- wrong historical_execution_started_sha — REJECTED
- wrong historical_checkpoint_sha — REJECTED (previously passed before repair, now correctly rejected)
- wrong historical_terminal_sha — REJECTED
- wrong historical_classification — REJECTED
- wrong Task-216 evidence canonical SHA (patched EVIDENCE_CANONICAL to 0*64) — REJECTED via trusted helper
- wrong Task-216 evidence blob (patched EVIDENCE_BLOB) — REJECTED
- historical evidence with duplicate tuple (duplicate recovery tuple) — REJECTED
- historical evidence missing tuple (remove one tuple) — REJECTED
- historical evidence record count !=45 (10 tuples) — REJECTED
- recovery max_generation_invocations =1 — REJECTED (must be 0)
- recovery max_generation_invocations =5 — REJECTED (must be 0, previously required 5 before repair)
And proves:

- exact trusted 45 predecessor map passes — PASS
- Authorization 212 still rejected by recovery validator — PASS
- recovery auth still rejected by historical validator — PASS
- recovery max_generation_invocations=0 passes — PASS
- All 29 recovery namespace tests pass, plus 5+8+53 existing = 92 passed overall, 0 failed, Ruff exit 0, no real recovery execution

## 6. What was not done

- No real retraining, no recovery execution, no recovery authorization artifact, no real recovery root creation, no generation, no held-out, no H3, no final-test, no network, no push

## 7. Reconciled state

TASK-224: RECOVERY_AUTHORIZATION_BINDING_REPAIRED_PENDING_AUDIT
GRU RECOVERY TRAINING: NOT_AUTHORIZED
RECOVERY EXECUTION: 0
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-IMPLEMENTATION-AUDIT-225 (R4 STRICT_READ_ONLY_IMPLEMENTATION_AUDIT)
