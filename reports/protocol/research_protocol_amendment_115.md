# Amendment 115 — V5 GRU Recovery Protocol Freeze

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-PROTOCOL-FREEZE-222
Risk: R4
Type: PROTOCOL_FREEZE_ONLY
Branch: main
Starting HEAD: f05c7ee45ba67fef41b11af63badbcac68cd252f
Protocol commit: 3c62ee200c27c9077035985e5cf2c98c0622eba0
Prerequisites: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-AUDIT-220 — AUDIT_CLOSED_WITH_REPORT_ONLY_INTEGRITY_MISSTATEMENTS, NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-IMPLEMENTATION-AUDIT-CLOSURE-221 — AUDIT_INTEGRITY_CLOSURE_VALIDATED

## 1. Prior state

Task-220: AUDIT_CLOSED_WITH_REPORT_ONLY_INTEGRITY_MISSTATEMENTS
Task-221: AUDIT_INTEGRITY_CLOSURE_VALIDATED
Repaired implementation: 85f5363518786286247490d8d953701d18fa3ae8 trainer 1860f99fcbd52ac26daab33e5325c36955fde7f8 manifest 1f6524c6c470a7495e3f55168a0ef4b2dfe3b5b9ff8dd8a538aa691c5edc1e20
Historical invalid policies: 45 (0 valid, preserved immutable under data/processed/research/hedging_policies)
Historical authorization 212: reports/protocol/hedging_execution_authorization_212.json ceiling 45 consumed 45 remaining 0 — EXHAUSTED_CLOSED
Recovery tuples: 45 frozen (seed-01/02/04/05/reserve-j01 × 0.0/0.001/0.005 × 31001/2/3)
Recovery namespace: data/processed/research/hedging_policies_recovery_v1 — distinct, no collision, write-once, not yet exists
Recovery authorization: NOT_YET_CREATED
Recovery execution: 0
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
FINAL: SEALED 0 ACCESS NOT GRANTED

## 2. Protocol freeze

Recovery protocol v1: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_protocol_v1.md
Canonical LF SHA256: 4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8
Raw SHA256: 4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8
Git blob: 6fcb39c29827d0d35ce3c777298fb75a81d00cb4
Filtered-worktree blob: 6fcb39c29827d0d35ce3c777298fb75a81d00cb4 (no filter)

Frozen contents:
- 45 recovery tuples ↔ 45 historical invalid tuples (one-to-one, no orphan/duplicate, nested order member→cost→hedger_seed)
- Predecessor metadata per tuple (historical Task-216 path, execution_started SHA, checkpoint SHA, terminal SHA, classification SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP) — full mapping in evidence ee7da9f at 1d739b...
- Distinct recovery root `hedging_policies_recovery_v1` with deterministic v1/member/cost/hedger_seed hierarchy
- Science frozen: GRU 7/64/2/dropout0, features, prev_delta endogenous, batch64, PCG64, AdamW .001/.9/.999/1e-6 clip1, CVaR .95, max200 min20 patience20, selection 10k, strict-lower checkpoint, costs 0/0.001/0.005, seeds 31001/2/3, replacement NONE
- Datasets: Task-215 validated 5 retained, no regeneration
- H3 eligibility: historical EXCLUDED_PERMANENTLY, successful audited recovery ELIGIBLE_FOR_H3, unaudited NOT ELIGIBLE
- Accounting: 45 historical invalid + 45 planned recovery = 90 projected total; separate domains; stop on first failure
- Provenance fields: recovery task/authorization/protocol/implementation/manifest/trainer/contract/runtime/member/cost/seed/synthetic/historical predecessor/recovery execution SHAs, best epoch/CVaR, epochs

Scientific rationale: recovery of intended frozen training after implementation no-op defect — not new hypothesis, not new hyperparameter exploration, not synthetic regeneration, not final-test activity.

## 3. What was not done

- No retraining (0)
- No recovery execution (0) — no policy directory created under recovery root
- No new execution authorization (NOT_YET_CREATED)
- No synthetic generation (CLOSED)
- No held-out evaluation / H3 (NOT_YET_ADJUDICATED)
- No final-test access (0, SEALED)
- No network, no push

## 4. Reconciled state

TASK-222: GRU_TRAINING_RECOVERY_PROTOCOL_FROZEN
DEEP-HEDGING TRAINING IMPLEMENTATION: VALIDATED_FOR_RECOVERY_GOVERNANCE
HISTORICAL TASK-216 POLICIES: 45_SCIENTIFICALLY_INVALID_PRESERVED
AUTHORIZATION 212 TRAINING: EXHAUSTED_CLOSED
RECOVERY TUPLES: 45_FROZEN
RECOVERY ARTIFACT NAMESPACE: FROZEN
GRU RECOVERY TRAINING: NOT_AUTHORIZED
RECOVERY EXECUTION: 0
POLICY COMPLETENESS: NOT_SATISFIED
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-NAMESPACE-IMPLEMENTATION-223 (R4 IMPLEMENTATION_ONLY)
