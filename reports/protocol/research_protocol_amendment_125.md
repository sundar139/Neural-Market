# Amendment 125 — V5 GRU Recovery V2 Execution Incident Adjudication

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-V2-EXECUTION-INCIDENT-PROTOCOL-ADJUDICATION-255
Risk: R4
Type: PROTOCOL_ADJUDICATION_ONLY
Branch: main
Starting HEAD: 257875c164dfc2ad7bf0e5dd047926e8ab84acec
Adjudication: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_v2_execution_incident_adjudication_v1.md
Adjudication commit: ab11e706d4772746859f4523203182cb3098ba4a
Adjudication canonical: a3c0d9a39b7dcebe0f79f2f254f5be31eba63f27c7c58346cc6482a5c992d51b
Adjudication raw: a3c0d9a39b7dcebe0f79f2f254f5be31eba63f27c7c58346cc6482a5c992d51b
Adjudication blob: e94a0e62f304c7d418cfb1b44e8dc124e7c0b598
Authorization251: reports/protocol/hedging_recovery_v2_execution_authorization_251.json (638805b7c2837b764d4b3f479442236079557b25 / e09b8a4268fb8a3a06f4036c84dfa4d3fa5b7b29b989c0e16e0e9b367fbbc1f3 / de8117fb5bdbf26d48ee56a63ef68c275996637b)
Prerequisite: reports/protocol/hedging_recovery_v2_authorization_prerequisites_246.json (d4813d60002128c898fe88e40fd846dde80b5c3d / c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0)
Implementation: 0b3841786ca77bbadb8c564ca33c75ff93f27bf1 / 6c13b0ee960e2688aa71403edf9d9bbaca13c1ab451aebc266c1e81d35ab9cac
Recovery root: data/processed/research/hedging_policies_recovery_v2 (FORENSIC_READ_ONLY_NEVER_REUSE)

## 1. Validated Forensic Chain

- Task-249: RECOVERY_V2_AUTHORIZATION_VALIDATOR_HARDENING_VALIDATED — 0b3841786ca77bbadb8c564ca33c75ff93f27bf1
- Task-250: RECOVERY_V2_AUTHORIZATION_VALIDATOR_AUDIT_VALIDATED (Hermes)
- Task-251: RECOVERY_V2_EXECUTION_AUTHORIZATION_REFREEZE_VALIDATED — 638805b7c2837b764d4b3f479442236079557b25 / 257875c164dfc2ad7bf0e5dd047926e8ab84acec
- Task-252: RECOVERY_V2_EXECUTION_AUTHORIZATION_AUDIT_VALIDATED
- Task-253: GOVERNANCE_INVALID_EXECUTION_RUNTIME_SOURCE_DRIFT — 2 durable consumed (1 terminal, 1 nonterminal), 43 not started, 0 valid policies
- Task-254: EXECUTION_FORENSIC_AUDIT_VALIDATED (Claude)
- Task-236: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_EXCLUDED (0 scientific result observed, distinct incident)
- Authorization248: FROZEN_HISTORICAL_NO_EXECUTION_AUTHORITY (7204cf1e753a93778ea6f25dff9a62db0fa18484)
- Authorization251: CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY (638805b...)
- Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE (1 success preserved, 1 nonterminal preserved, 43 not started)

## 2. Task253 Campaign Classification

- Campaign: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_CONTAMINATED_EXECUTION
- Ordinal1 (seed-01/0.0/31001): GOVERNANCE_INVALID_RUNTIME_MUTATION_TERMINAL — INELIGIBLE_FOR_POLICY_COMPLETENESS, INELIGIBLE_FOR_PREREQUISITE_9, INELIGIBLE_FOR_H3, MODEL_AND_SELECTION_INFORMATION_EXPOSED
- Ordinal2 (seed-01/0.0/31002): GOVERNANCE_INVALID_RUNTIME_MUTATION_NONTERMINAL — INELIGIBLE_FOR_POLICY_COMPLETENESS, INELIGIBLE_FOR_PREREQUISITE_9, INELIGIBLE_FOR_H3, DURABLY_CONSUMED_NONTERMINAL, NO_RETRY_AUTHORITY
- All artifacts: FORENSIC_ONLY_H3_INELIGIBLE_INFORMATION_EXPOSED
- Authorization251: CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY
- Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE — no future writes into recovery_v2
- Accounting: ceiling 45, durable consumed 2, remaining 43, valid terminal policies 0, governance-invalid terminal 1, governance-invalid nonterminal 1, not started 43, retry/rerun/replacement 0

## 3. Scientific Exposure

- Task236 exposure: 0
- Task253 exposure: YES — best_epoch 11, best_validation_cvar 2.3413521425265205, early stopping 31, full 32-epoch trajectory exposed (training_curve.json 01aa9297), checkpoint.pt ab65d67a..., checkpoint_final.pt f1d7892e..., model parameters preserved, selection information exposed
- Ordinal2 metrics: UNKNOWN_BEYOND_PROCESS_STARTED (only execution_started 032a03a...)
- Information blindness: THE OPERATOR / PROJECT IS NO LONGER INFORMATION-BLIND TO THE ORIGINAL SEED-01 / COST-0 / HEDGER-SEED-31001 TUPLE

## 4. Continuation and Same-45 Restart

- Remaining 43 tuples: cannot satisfy 45-policy completeness (max 43 valid even if all succeed, plus 0 valid existing)
- Continuation: ORIGINAL_AUTHORIZATION251_CAMPAIGN_NOT_CONTINUABLE_FOR_SCIENCE
- Same-45 restart: SAME_45_TUPLE_RESTART_NOT_SCIENTIFICALLY_CLEAN — deterministic outcome (CVaR 2.341..., epoch 11, model) for seed-01/0/31001 is durably known; rerunning identical 45-tuple universe cannot be information-blind preregistered

## 5. Successor H3 Campaign

- H3 still scientifically testable: YES, via disjoint successor campaign
- Required: new namespace distinct from recovery_v2, no checkpoint reuse, no warm start, no reuse of exposed hedger seed (31001 for seed-01/0), disjoint hedger-seed universe derived deterministically from immutable pre-outcome identities (not hand-picked), same 5 datasets, same 3 costs, same GRU architecture/features/training contract, same H3 criteria, no hyperparameter adaptation
- Classification: H3_SUCCESSOR_RECOVERY_CAMPAIGN_SCIENTIFICALLY_PERMISSIBLE_PENDING_PROTOCOL_DESIGN_AND_INDEPENDENT_AUDIT
- Rationale: H3 remains testable without using Task253 information if successor is fully disjoint and outcome-independent; original campaign criteria not relaxed

## 6. Source Defect

- Location: src/neuralmarket/research/deep_hedging/trainer.py ~1160, train_one_policy_recovery
- Invalid call: build_implementation_manifest(authorized_commit=_payload_impl_commit)
- Authorized behavior: FAILS CLOSED BEFORE RECOVERY EXECUTION
- Task253 runtime: patched in-memory (authorized_commit alias) and executed
- Repair required: YES (change to implementation_commit)
- Repaired in Task255: NO
- Relationship: separate gates — source repair does not confer scientific authority; successor admissibility does not imply source correctness
- Frozen: IMPLEMENTATION_REPAIR_REQUIRED_BEFORE_ANY_FUTURE_RECOVERY_EXECUTION — Authorization251 must never be rebound to repaired source

## 7. Current Authority

- Authorization251: CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY
- Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE
- Policy completeness: NOT_SATISFIED (0 valid)
- Prerequisite #9: NOT_SATISFIED
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- Final: SEALED, access 0, synthetic generation closed, network 0, held-out 0

Adjudicated without source mutation, authorization creation/edit, artifact mutation, recovery execution, retry/rerun/replacement/deletion/rm-rf, generation, held-out, H3, or final-test activity.
