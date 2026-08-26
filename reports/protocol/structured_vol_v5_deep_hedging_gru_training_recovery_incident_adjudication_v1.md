# V5 GRU Recovery Incident Adjudication v1

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-INCIDENT-PROTOCOL-ADJUDICATION-243
Risk: R4
Type: PROTOCOL_ADJUDICATION_ONLY
Branch: main
Starting HEAD: be48d97e8eda73c17e0457b93e0ca43ff4c95927
Validated final post-incident recovery implementation: be48d97e8eda73c17e0457b93e0ca43ff4c95927
Validated implementation manifest: 77e06119922b2b8cfa300e0bf1372d22a069351c5cfd5ded7b8d722b95cab2f0

## 1. Pre-Adjudication State Verification

- Branch: main
- HEAD: be48d97e8eda73c17e0457b93e0ca43ff4c95927
- Parent: 874a959f4a19b6a1a6be73a2cba43782d0d26f8c
- Tracked tree: clean (git status --short --untracked-files=no empty)
- Implementation binding: be48d97e8eda73c17e0457b93e0ca43ff4c95927 / 77e06119922b2b8cfa300e0bf1372d22a069351c5cfd5ded7b8d722b95cab2f0 – verified via build_implementation_manifest() at HEAD, 15 paths, __init__.py present, init.py absent, trainer 972af6c61a825cb397a03552db694bf153b79c71, runner 0a5e51bb4af11f59898659a7cfe36e4bdfa6f8c4, CLI 5080c57dd17fd10d5b420d2bac369955661b3d57, generation 1b8710fc77362eb59a7167b3b4575d8b93f63d12
- Authorization233: reports/protocol/hedging_recovery_execution_authorization_233.json – POST_FREEZE_MUTATED_NO_AUTHORITY (manifest 86a8efea... vs rebuilt a94baea... / current 77e061..., source drift, invalidated)
- Authorization226: reports/protocol/hedging_recovery_execution_authorization_226.json – NO AUTHORITY (historical family task_id with recovery type, manifest bcc31028... vs current 77e061..., source drift, rejected by authoritative schema)
- Authorization212: reports/protocol/hedging_execution_authorization_212.json – EXHAUSTED_CLOSED (ceiling 45 consumed 45)
- Recovery root: data/processed/research/hedging_policies_recovery_v1 – absent (pathlib.Path.exists()==False)
- Recovery authority: NONE_VALID_FOR_EXECUTION
- Incident accounting from Task-238: 4 observed scientific invocations, 1 unique tuple, 3 duplicate invocations, 0 ordinal2+ – forensic accepted

## 2. Task-236 Incident Chronology Summary

- Task-236: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-INCIDENT – governed recovery execution attempt under Authorization233 (1fd138f) with implementation 778ff389.../bcc310... (later superseded by be48d97/77e061)
- Observed invocations: 4 ordinal-1 invocations (all same tuple, likely seed-01/0.0/31001 – the only tuple that reached process start)
- Unique tuples: 1
- Duplicate invocations: 3
- Marker deletions: 4 evidence-supported write-once marker deletions (execution_started.json deleted after each attempt, before forensic capture)
- Ordinal2+: 0 (no attempt beyond ordinal 1 observed)
- Evidence: forensic capture shows no checkpoint, no training_report, no terminal_manifest persisted at time of adjudication; all 4 attempts were killed/deleted before scientific result observation
- Authorization233 post-freeze mutation: source drift from 778ff38/bcc310... to be48d97/77e061... via Task-239/241 hardening causes 233 to be invalidated; 233 must never be reused

## 3. Scientific Information Actually Observed During Task-236

Using only existing forensic evidence (Task-238 accepted):

- Checkpoints: NONE – no checkpoint.pt exposed
- Training reports: NONE – no training_report.json exposed
- Terminal manifests: NONE – no terminal_manifest.json exposed
- Best epoch: NONE – no selection result observed
- Selection CVaR: NONE – no validated policy CVaR observed
- Epoch-level training CVaR: NONE – no epoch history observed
- Validation-selection history: NONE
- Model parameters selected for use: NONE – no validated policy
- Real held-out performance: NONE
- H3 result: NONE
- Final-test result: NONE

Classification of information exposure:

- PROCESS_STARTED: 4 invocations reached process start (execution_started intent)
- SCIENTIFIC_RESULT_OBSERVED: 0 – no usable scientific outcome was available before kill/delete

This distinction is load-bearing: no outcome-based selection could have occurred, therefore a wholly new campaign from the frozen contract does not constitute prohibited retry.

## 4. Task-236 Campaign Classification (Permanent)

- TASK236_CAMPAIGN: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_EXCLUDED
- All Task-236 execution attempts: FORENSIC_ONLY_NOT_SCIENTIFIC_DATA
- All deleted/partial Task-236 artifacts: INELIGIBLE_FOR_POLICY_SELECTION, INELIGIBLE_FOR_PREREQUISITE_9, INELIGIBLE_FOR_H3, INELIGIBLE_FOR_FINAL_ANALYSIS
- Authorization233: CLOSED_INVALIDATED_BY_POST_FREEZE_MUTATION_AND_INCIDENT – must never be reused, amended into validity, or treated as continuation authority
- Historical preservation: Task-236 artifacts remain forensic only, not edited, not restored

## 5. New Campaign Admissibility

Question: Can a new campaign execute the original frozen 45-tuple universe from scratch without constituting prohibited outcome-driven retry?

Evaluation:

- A. No usable checkpoint/report/terminal/policy or selection result was yielded by Task-236: TRUE (Section 3)
- B. No Task-236 scientific outcome used to alter members, datasets, costs, hedger seeds, architecture, features, optimizer, CVaR, epochs, patience, selection rule, runtime, or tuple order: TRUE – all remain frozen
- C. All original 45 frozen tuples remain exactly same: TRUE
- D. New campaign declared as NEW CAMPAIGN, not continuation/retry/rerun/replacement: REQUIRED
- E. All Task-236 attempts remain permanently excluded: TRUE
- F. New campaign uses distinct namespace and distinct authorization identity: REQUIRED (Section 7)
- G. No prior Task-236 artifact restored or imported: TRUE

Result:

- NEW RECOVERY CAMPAIGN: SCIENTIFICALLY_ALLOWABLE_PENDING_NAMESPACE_IMPLEMENTATION

Rationale: Task-236 yielded no scientific result that could bias tuple selection or hyperparameter adaptation; restarting the whole 45-tuple universe from the unchanged frozen contract with a new namespace is scientifically allowable as a prospective new campaign, not a retry. Allowability is conditional on distinct namespace and new authorization; otherwise blocked.

## 6. New-Campaign Scientific Contract (Frozen)

If allowable, the following contract is frozen for any future new campaign:

- Campaign classification: V5_GRU_RECOVERY_POST_INCIDENT_NEW_CAMPAIGN
- Scientific universe: exact same 45 tuples – 5 validated NSDE synthetic members × 3 costs × 3 hedger seeds
- Members exactly: seed-01, seed-02, seed-04, seed-05, reserve-j01
- Costs exactly: 0.0, 0.001, 0.005
- Hedger seeds exactly: 31001, 31002, 31003
- Datasets: same five Task-215 validated datasets and exact SHAs (synthetic_reconciliation 50bfad97..., synthetic_quality 8506ca2..., per-member dataset SHA cda7280a... etc.)
- Training contract: unchanged v3 (GRU 7/64/2/dropout0, 7 features, prev_delta, P&L, CVaR alpha 0.95, AdamW lr 0.001 betas 0.9/0.999 weight_decay 1e-6, batch 64, max200 min20 patience20 clip1, strict-lower checkpoint, full-selection CVaR, costs/seeds/replacement NONE)
- Implementation: be48d97e8eda73c17e0457b93e0ca43ff4c95927
- Manifest: 77e06119922b2b8cfa300e0bf1372d22a069351c5cfd5ded7b8d722b95cab2f0
- No hyperparameter adaptation, no seed adaptation, no tuple omission because ordinal1 was previously touched, no replacement, no use of Task-236 outcomes
- The previously touched seed-01/0.0/31001 tuple, if included, is included only because the WHOLE new 45-tuple universe is restarted prospectively from the unchanged frozen contract, not because that individual tuple is retried – this distinction is explicit

## 7. Distinct New Namespace / Authority Requirement

- Old root: data/processed/research/hedging_policies_recovery_v1 – must NOT be reused for new campaign
- Old root reusable: FALSE
- New root (frozen, suggested): data/processed/research/hedging_policies_recovery_v2 – unless existing production architecture requires another deterministic name; do not create now
- Future authorization must: use NEW path (e.g., reports/protocol/hedging_recovery_execution_authorization_244.json), use NEW task ID (NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-244), bind validated be48d97/77e061 implementation, bind new namespace, bind all exact 45 tuples, bind exact 45 trusted Task-216 predecessors, training ceiling 45, generation ceiling 0, network false, final_test_access false
- Authorization233 must not be copied, edited, aliased, or reused
- Current code support: IMPLEMENTATION_CHANGE_REQUIRED_FOR_NEW_NAMESPACE – RECOVERY_ROOT is hardcoded to recovery_v1 in runner.py and trainer.py (15-path manifest includes runner/trainer with that constant); new v2 root requires minimum governed source change to accept distinct root
- New root created: FALSE (not created in Task-243)

## 8. New-Campaign Write-Once / Incident Guardrails

For any future new campaign require:

- One invocation per tuple
- No retry, no rerun, no replacement
- No deletion of started/partial/failed artifacts
- No rm -rf of campaign root
- Stop entire campaign on first failure or ambiguity
- Preserve failed/nonterminal attempt byte-for-byte
- No source mutation after authorization freeze
- No authorization mutation after freeze
- No runtime mutation after freeze
- No execution while source/auth mismatch exists
- Pre-write provenance validation must PASS before execution_started creation (fail-before-write via _validate_recovery_provenance_packet is prerequisite)
- No cleanup command may restore authority

## 9. Current Authority and Future State

- Current recovery authorization: NONE_VALID_FOR_EXECUTION
- Current recovery execution: SUSPENDED
- New-campaign execution: NOT_AUTHORIZED (pending namespace implementation and new authorization freeze)
- Policy completeness: NOT_SATISFIED
- Prerequisite #9: NOT_YET_SATISFIED
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- Final: SEALED
- Final-test access: 0
- Final-test authorization: NOT GRANTED
- Synthetic generation: CLOSED_NO_FURTHER_EXECUTION

## 10. Implementation Audit Trail

- Task-239: RECOVERY_PROVENANCE_IMPLEMENTATION_REPAIR_VALIDATED (874a959)
- Task-240: RECOVERY_PROVENANCE_IMPLEMENTATION_AUDIT_VALIDATED_WITH_BOUNDED_HARDENING
- Task-241: RECOVERY_PROVENANCE_INTERNAL_HARDENING_VALIDATED (be48d97)
- Task-242: RECOVERY_PROVENANCE_HARDENING_AUDIT_VALIDATED (be48d97/77e061)
- Task-243: RECOVERY_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED (this document)

---

Adjudicated without source mutation, authorization creation/edit, recovery execution, artifact restoration, H3, or final-test activity.
