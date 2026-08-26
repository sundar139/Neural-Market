# Amendment 121 — V5 GRU Recovery Incident Protocol Adjudication

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-INCIDENT-PROTOCOL-ADJUDICATION-243
Risk: R4
Type: PROTOCOL_ADJUDICATION_ONLY
Branch: main
Starting HEAD: be48d97e8eda73c17e0457b93e0ca43ff4c95927
Prerequisite: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-PROVENANCE-HARDENING-AUDIT-242 — RECOVERY_PROVENANCE_HARDENING_AUDIT_VALIDATED
Adjudication document: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_incident_adjudication_v1.md
Adjudication commit: 40d2591ae59b6f504c65e7a5632ccf2a6606ed30
Adjudication canonical SHA256: ad29a5039849499336f97fef0dbadfc2abcc5009b4d55e810741dec8cf468015
Adjudication raw SHA256: ad29a5039849499336f97fef0dbadfc2abcc5009b4d55e810741dec8cf468015
Adjudication Git blob: d4e57711fb5bad50495ed7aba018e5a9f4ccc121

## 1. Adjudicated Incident State

- Task-236 campaign: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_EXCLUDED
- Observed invocations: 4
- Unique tuples: 1
- Duplicate invocations: 3
- Marker deletions: 4 (evidence-supported)
- Ordinal2+: 0
- Checkpoints: NONE
- Training reports: NONE
- Terminal manifests: NONE
- Best epoch / selection CVaR / epoch CVaR: NONE
- Selected parameters: NONE
- Held-out / H3 / final: NONE
- Scientific information observed: PROCESS_STARTED only, SCIENTIFIC_RESULT_OBSERVED 0
- All Task-236 attempts: FORENSIC_ONLY_NOT_SCIENTIFIC_DATA
- All deleted/partial Task-236 artifacts: INELIGIBLE_FOR_POLICY_SELECTION, INELIGIBLE_FOR_PREREQUISITE_9, INELIGIBLE_FOR_H3, INELIGIBLE_FOR_FINAL_ANALYSIS
- Authorization233: CLOSED_INVALIDATED_BY_POST_FREEZE_MUTATION_AND_INCIDENT – must never be reused
- Implementation audit trail: Task-239 (874a959), Task-240 (audit validated with bounded hardening), Task-241 (be48d97), Task-242 (be48d97/77e061 validated)

## 2. New Campaign Admissibility

- No usable prior result: TRUE
- No outcome-driven adaptation: TRUE – members, datasets, costs, hedger seeds, architecture, features, optimizer, CVaR, epochs, patience, selection rule, runtime, tuple order unchanged
- Same 45 tuples: TRUE – seed-01, seed-02, seed-04, seed-05, reserve-j01 × 0.0,0.001,0.005 × 31001,31002,31003
- Whole-campaign restart: REQUIRED – new campaign is V5_GRU_RECOVERY_POST_INCIDENT_NEW_CAMPAIGN, not continuation/retry
- Task-236 exclusion: TRUE – all prior attempts permanently excluded
- Distinct namespace and authorization: REQUIRED
- New campaign: SCIENTIFICALLY_ALLOWABLE_PENDING_NAMESPACE_IMPLEMENTATION – allowable only with new namespace and new authorization; otherwise blocked
- Rationale: Task-236 yielded no scientific outcome that could bias selection; restarting whole universe prospectively from frozen contract does not constitute prohibited retry

## 3. New-Campaign Frozen Contract

- Classification: V5_GRU_RECOVERY_POST_INCIDENT_NEW_CAMPAIGN
- Implementation: be48d97e8eda73c17e0457b93e0ca43ff4c95927
- Manifest: 77e06119922b2b8cfa300e0bf1372d22a069351c5cfd5ded7b8d722b95cab2f0 (15 paths, __init__.py present, init.py absent, trainer 972af6c..., runner 0a5e51..., CLI 5080..., generation 1b87...)
- Members: seed-01, seed-02, seed-04, seed-05, reserve-j01
- Costs: 0.0, 0.001, 0.005
- Hedger seeds: 31001, 31002, 31003
- Tuples: 45 exact
- Datasets: Task-215 validated 5 synthetic datasets and exact SHAs
- Hyperparameters: no adaptation, no seed adaptation, no tuple omission, no replacement, no use of Task-236 outcomes
- Previously touched tuple seed-01/0.0/31001 is included only because whole 45-tuple universe restarts prospectively, not as individual retry – explicit

## 4. Namespace and Authority

- Old root: data/processed/research/hedging_policies_recovery_v1 – not reusable
- New root (frozen): data/processed/research/hedging_policies_recovery_v2 (unless architecture requires another deterministic name) – not created now
- Current code support: IMPLEMENTATION_CHANGE_REQUIRED_FOR_NEW_NAMESPACE – RECOVERY_ROOT hardcoded to recovery_v1 in runner/trainer
- New root created: FALSE
- Future authorization must: new path, new task ID (e.g., 244), bind be48d97/77e061, bind new namespace, bind all 45 tuples, bind 45 trusted predecessors, training ceiling 45, generation ceiling 0, network false, final_test_access false; 233 must not be copied

## 5. Guardrails

- One invocation per tuple, no retry, no rerun, no replacement, no deletion of started/partial/failed artifacts, no rm -rf, stop on first failure, preserve failed byte-for-byte
- No source/authorization/runtime mutation after freeze, no execution while mismatch exists
- Pre-write provenance validation must PASS before execution_started creation (fail-before-write prerequisite)
- No cleanup may restore authority

## 6. Authority and Completeness

- Current recovery authorization: NONE_VALID_FOR_EXECUTION
- Current recovery execution: SUSPENDED
- New-campaign execution: NOT_AUTHORIZED (pending namespace implementation and new authorization freeze)
- Policy completeness: NOT_SATISFIED
- Prerequisite #9: NOT_YET_SATISFIED
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- Synthetic generation: CLOSED_NO_FURTHER_EXECUTION
- Final: SEALED, access 0, not granted
- Task state: TASK-236 REJECTED_GOVERNANCE_INVALID_EXECUTION, TASK-237 REJECTED_GOVERNANCE_INVALID_FORENSIC_HANDLING, TASK-238 INCIDENT_FORENSIC_ADJUDICATION_ACCEPTED, TASK-239 RECOVERY_PROVENANCE_IMPLEMENTATION_REPAIR_VALIDATED, TASK-240 RECOVERY_PROVENANCE_IMPLEMENTATION_AUDIT_VALIDATED_WITH_BOUNDED_HARDENING, TASK-241 RECOVERY_PROVENANCE_INTERNAL_HARDENING_VALIDATED, TASK-242 RECOVERY_PROVENANCE_HARDENING_AUDIT_VALIDATED, TASK-243 RECOVERY_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED
