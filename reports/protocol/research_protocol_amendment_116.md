# Amendment 116 — V5 GRU Recovery Namespace Implementation

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-NAMESPACE-IMPLEMENTATION-223
Risk: R4
Type: IMPLEMENTATION_ONLY
Branch: main
Starting HEAD: ed8f40284aff5c16327d5d5d0b4b1d1a4ba5909f
Safety branch: safety/pre-v5-gru-recovery-namespace-ed8f402 at ed8f40284aff5c16327d5d5d0b4b1d1a4ba5909f
Prerequisites: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-PROTOCOL-FREEZE-222 — GRU_TRAINING_RECOVERY_PROTOCOL_FROZEN at 3c62ee2

## 1. Implementation scope

Historical Authorization 212: EXHAUSTED_CLOSED (ceiling 45 consumed 45 remaining 0)
Historical policies: 45_SCIENTIFICALLY_INVALID_PRESERVED under data/processed/research/hedging_policies (45 directories)
Recovery protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md at 3c62ee2 canonical 4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8 blob 6fcb39c29827d0d35ce3c777298fb75a81d00cb4
Recovery namespace: data/processed/research/hedging_policies_recovery_v1 — distinct, does not exist pre-implementation (verified), deterministic v1/member/cost/seed hierarchy, write-once
Recovery authorization schema: implemented (GRU_TRAINING_RECOVERY_V1 discriminator)
Actual recovery authorization: NOT_CREATED (no JSON created in this task)
Recovery execution: 0 — no real recovery directory created, no 40k/10k training
Scientific trainer: UNCHANGED_REPAIRED_VALIDATED — optimization loop (hedger.train, zero_grad, autoregressive GRU, endogenous prev_delta, batched P&L, empirical CVaR alpha .95, backward, gradient checks, clip 1.0, optimizer.step, epoch_train_losses) unchanged; recovery reuses SAME internal `_train_one_policy_internal` (no duplication)

## 2. Authorization separation (distinct surfaces)

Historical validator: `validate_authorization_schema` — checks schema_version, contract 79611b..., runtime 17e3bb..., member/cost/seed allowlists, max 5/45, artifact_roots, network false, final false; plus new guard: if payload contains any recovery-specific key (`recovery_protocol_*`, `recovery_root`, `recovery_tuples`, `predecessor_identities`, `authorization_type`) → raise AuthorizationError (historical must not contain recovery fields)

Recovery validator: `validate_recovery_authorization_schema` — requires:
- authorization_type == GRU_TRAINING_RECOVERY_V1
- recovery_protocol_path == reports/protocol/.../recovery_protocol_v1.md
- recovery_protocol_canonical == 4bf228ad...
- recovery_protocol_blob == 6fcb39c...
- implementation_commit == 85f5363518786286247490d8d953701d18fa3ae8 (repaired)
- implementation_manifest == 1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20
- contract 79611b..., runtime 17e3bb..., recovery_root == data/processed/research/hedging_policies_recovery_v1, artifact_roots contains recovery root, network false, final false, max 45/5, member/cost/seed exactly frozen 5/3/3, recovery_tuples 45 unique, predecessor_identities 45 with historical_classification SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP

Historical Authorization 212 (no recovery fields) → recovery validator: REJECTED (missing authorization_type)
Recovery authorization (with recovery fields) → historical validator: REJECTED (contains recovery fields)
Wrong protocol SHA, wrong commit, wrong manifest, wrong root, tuple outside 45, predecessor mismatch, predecessor SHA mismatch — all REJECTED (tested)

## 3. Distinct recovery artifact routing (one trainer)

Historical `train-policy` / `train_one_policy`:
- Loads historical authorization via `verify_authorization_artifact` + `validate_authorization_schema`
- Rejects recovery authorization (explicit check)
- Resolves `policy_dir = data/processed/research/hedging_policies/{prefix}_{member}/c_{bps}/h_{seed}`
- Checks started/checkpoint existence (CONSUMED)
- Calls `_train_one_policy_internal(..., policy_root=None)` (defaults to historical)

Recovery `train-policy-recovery` / `train_one_policy_recovery`:
- Loads recovery authorization via `verify_authorization_artifact` + `validate_recovery_authorization_schema`
- Rejects historical Authorization 212 (authorization_type mismatch)
- Validates tuple in recovery_tuples and predecessor mapping
- Resolves `policy_dir = data/processed/research/hedging_policies_recovery_v1/{prefix}_{member}/c_{bps}/h_{seed}` (RECOVERY_ROOT_PATH)
- Checks recovery started/checkpoint existence (independent write-once)
- Builds recovery_provenance dict (protocol path/canonical/blob, authorization canonical/blob/commit, implementation commit/manifest, recovery_root, historical predecessor path/SHAs/classification)
- Calls SAME `_train_one_policy_internal(..., policy_root=RECOVERY_ROOT_PATH, recovery_provenance=...)` — no duplicated optimization loop

Scientific parameter overrides: 0 — recovery reuses same `max_epochs 200 min 20 patience 20 batch 64 AdamW .001/.9/.999/1e-6 clip 1.0 alpha .95` etc.

## 4. Recovery path and predecessor evidence semantics

Recovery path deterministic: `RECOVERY_ROOT_PATH / f"{run_prefix}_{member}/c_{bps}/h_{seed}"` — same hierarchy as historical, distinct root, collision-free (verified `hedging_policies` vs `hedging_policies_recovery_v1` distinct)

Predecessor evidence semantics in code (`_train_one_policy_internal`):
- execution_started, training_report, terminal_manifest now include `recovery_provenance` fields if provided (recovery_protocol_*, recovery_authorization_*, recovery_implementation_*, historical_predecessor_*, historical_classification)
- Historical artifacts are provenance only — not mutated, not copied as weights; recovery initialization remains `torch.manual_seed(hedger_seed) → fresh GRUHedger` per frozen contract

## 5. Write-once / no-retry recovery semantics

Recovery namespace independently enforces:
- execution_started write-once (`if exists: raise FileExistsError OVERWRITE_REFUSED`)
- Existing tuple directory → refuse
- Existing started marker → refuse
- Existing partial recovery artifact → refuse ambiguous overwrite
- Failed consumed attempt → no retry (second invocation on same recovery tuple raises OVERWRITE_REFUSED)
- Successful consumed attempt → no rerun
- No replacement tuple, no fallback to historical root
- Historical root existence does NOT block recovery tuple (roots distinct) — verified via tmp_path test where historical dir exists but recovery not
- Recovery-root existence for same recovery tuple DOES block reuse — verified via `test_recovery_started_marker_write_once` and `test_failed_recovery_cannot_retry`

If future real recovery fails after started marker: preserve failure evidence, do not delete, do not retry automatically.

## 6. Tests (private, no real recovery execution)

All tmp_path/private fixture authorizations, no real recovery root/auth, tiny CPU fixtures (8-16 episodes) where needed:

- historical Authorization 212 rejected by recovery surface — PASS
- recovery authorization rejected by historical surface — PASS
- wrong recovery protocol SHA rejected — PASS
- wrong repaired implementation commit rejected — PASS
- wrong manifest rejected — PASS
- wrong root rejected — PASS
- tuple outside frozen 45 rejected — PASS
- predecessor tuple mismatch rejected — PASS
- predecessor SHA mismatch rejected — PASS
- recovery path deterministic — PASS
- recovery path distinct from historical — PASS
- historical directory may exist without colliding — PASS
- recovery started marker write-once — PASS (second call raises OVERWRITE_REFUSED)
- failed recovery cannot retry — PASS (injected failure at epoch 0 → failure terminal, second call still OVERWRITE_REFUSED)
- recovery provenance fields emitted — PASS (execution_started and report contain recovery_protocol_canonical, historical_classification etc.)
- same repaired internal trainer invoked — PASS (`return _train_one_policy_internal(` present, `def _train_one_policy_internal` count 1)
- no duplicated optimization implementation — PASS (`cvar.backward()` 1, `clip_grad_norm_(` 1, `for start in range(0, N_train` 1, `hedger.train()` 1)

Total: 17 tests in test_recovery_namespace.py — 17 passed; plus 5+8+53 existing = 92 passed overall, 0 failed
Ruff: `ruff check src/neuralmarket/research/deep_hedging/trainer.py src/neuralmarket/research/deep_hedging/runner.py src/neuralmarket/cli/deep_hedging.py` — exit 0 (pre-existing E501 on long lines, no new blocking)

No real 40k/10k scientific policy training — 0
No real recovery directory — 0 (recovery root still does not exist: `pathlib.Path(...).exists() == False`)

## 7. Implementation identity

Implementation commit: e70e3465395e074d9b94c48383b6a7397a2d2df0
Previous trainer blob (at 85f5363): 1860f99fcbd52ac26daab33e5325c36955fde7f8
New trainer blob (at e70e346): d8100a95010e73e55e7154de0998bfa8365d1fef — changed due to recovery wrapper (provenance handling + new API), but optimization loop unchanged (verified `cvar.backward()` etc. still 1)
Previous runner blob: 49130c75...? Actually at 85f5363 runner was 49130c...? No, at 85f5363 runner was unchanged from earlier (maybe same as before), new runner blob 49130c75ce97e994d15c0dc00b51f458251f7122 (adds recovery validator)
Previous cli blob: dacea6bd...? At 85f5363 cli was dacea6..., new cli dacea6bd568ba4bd4b0491e0d01280ada9d818eb (adds train-policy-recovery)
Path count: 15 — same closure (all *.py under deep_hedging + 6 extra)
Source blobs at e70e346 (sorted):
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
  src/neuralmarket/research/deep_hedging/runner.py 49130c75ce97e994d15c0dc00b51f458251f7122
  src/neuralmarket/research/deep_hedging/synthetic.py f3838634a6afc57b438d1baa2d078e37d12dacb5
  src/neuralmarket/research/deep_hedging/trainer.py d8100a95010e73e55e7154de0998bfa8365d1fef
Canonical manifest SHA: 3867e66c02f5a6feba43f4ecad289e94c156392e86c9d723a6a01477df867eb6 — at e70e346
Previous manifest at 85f5363: 1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20
Scientific trainer change: optimization loop unchanged (verified single `cvar.backward()` etc.), only added recovery wrapper and provenance plumbing
