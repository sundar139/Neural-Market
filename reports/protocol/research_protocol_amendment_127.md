# Amendment 127 — V5 GRU Recovery Successor Authorization Prerequisite Freeze

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-AUTHORIZATION-PREREQUISITES-262
Risk: R4
Type: AUTHORIZATION_PREREQUISITE_FREEZE_ONLY
Branch: main
Starting HEAD: d762e5a18a1552d34fce79ea5d765a66c042d9c1
Prerequisite: reports/protocol/hedging_recovery_successor_authorization_prerequisites_262.json
Prerequisite commit: 90ff008925eef4819934b9d3f8bb999974e9d270
Prerequisite canonical: e2e121f6b62e424ccc95f501180595e642d14d71915939cc86fb5a51bfe2c74f
Prerequisite raw: d107c55a59fb044a2f4316328fbbdd762dcf7c206d24933bcaaa26e9dd644fba
Prerequisite blob: 5c7ab59b6e666eb38c5559be8030724a43418ee8
Training contract: reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md (79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad220db889166469799372759dfe1a96e35f)
Successor protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md (c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0 / 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418)
Implementation: d762e5a18a1552d34fce79ea5d765a66c042d9c1 / 9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a
Recovery root: data/processed/research/hedging_policies_recovery_v3 (not created)
Task261: RECOVERY_SUCCESSOR_SOURCE_AUDIT_VALIDATED

## 1. Validated Basis

- Task257: RECOVERY_SUCCESSOR_PROTOCOL_DESIGN_VALIDATED — c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0
- Task258: RECOVERY_SUCCESSOR_PROTOCOL_AUDIT_VALIDATED
- Task259: RECOVERY_SUCCESSOR_SOURCE_REPAIR_VALIDATED — d762e5a18a1552d34fce79ea5d765a66c042d9c1 / 9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a (trainer a9bfcb6a..., runner 5fac8765...)
- Task260: RECOVERY_SUCCESSOR_SOURCE_TEST_STATE_REPAIR_VALIDATED — d762e5a / 9e1b1a6c, 120/120 tests with forensic present
- Task261: RECOVERY_SUCCESSOR_SOURCE_AUDIT_VALIDATED
- Task255/256: RECOVERY_V2_EXECUTION_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED, recovery_v2 FORENSIC_READ_ONLY_NEVER_REUSE, original campaign PERMANENTLY_CLOSED, same-45 restart NOT_SCIENTIFICALLY_CLEAN
- Authorization251: CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY (638805b...)
- Authorization248: FROZEN_HISTORICAL_NO_EXECUTION_AUTHORITY (7204cf1...)
- Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE (1 terminal + 1 nonterminal, 43 not started, 0 valid)
- Recovery_v3: FROZEN_NOT_CREATED (not created)

## 2. Training Contract Freeze and Seed Supersession

- Training contract v3: reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md — UNCHANGED_FROZEN (canonical 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01, blob eef7ad220db889166469799372759dfe1a96e35f, raw d3e30e2cfa897d5b2c436d9c0a932b06fc862370c73ffbc3f80dcaf862c144dd)
- Contract bytes changed: false
- Old-seed clause 1: structured_vol_v5_deep_hedging_training_contract_v3.md:49 — "Hedger seeds 31001-31003 | SOURCE_FROZEN (harness v3 Section 7.3) | preserved 31001,31002,31003"
- Old-seed clause 2: structured_vol_v5_deep_hedging_training_contract_v3.md:198 — "Expected trained policy count: 45 = 5 generator members × 3 hedger seeds (31001,31002,31003) × 3 cost levels (0, 0.0010, 0.0050)"
- Additional seed clauses: none load-bearing (other mentions are examples or distinct seed families)
- Training contract v3 scientific parameters: FULLY_PRESERVED (architecture 7/64/2/dropout0, features 7, readout, P&L, CVaR 0.95, AdamW lr1e-3 betas0.9/0.999 wd1e-6, batch64, max200 min20 clip1 patience20, no scheduler, selection lowest finite CVaR earliest tie, datasets 5, train/selection 40k/10k, costs 0.0/0.001/0.005, H3 endpoint/comparator/criteria)
- Historical hedger seed family: 31001, 31002, 31003
- Historical status: SUPERSEDED_FOR_SUCCESSOR_CAMPAIGN_ONLY
- Successor hedger seed family: 60999, 53804, 89356
- Successor derivation: TASK257_WRITE_ONCE_OUTCOME_INDEPENDENT_DERIVATION (domain neuralmarket-v5-gru-recovery-successor-v1, SHA256 of contract+SAP+recovery_protocol+prereq+sorted dataset SHAs, 40000+(hash%50000), globally disjoint)
- Successor audit: TASK258_VALIDATED
- Supersession scope: seed-family enumeration only (2 clauses), no other scientific parameter superseded
- Outcome adaptation: PROHIBITED (no tuning based on Task253 best_epoch 11, CVaR 2.341..., trajectory, checkpoint)
- Verdict: PASS

## 3. Successor Binding

- Successor protocol: c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0 / 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418 (Amendment126 04bf5b3/72ce80...)
- Implementation: d762e5a18a1552d34fce79ea5d765a66c042d9c1 / 9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a (15-path, runner 5fac8765..., trainer a9bfcb6a..., CLI 86b9468f..., generation 1b8710fc...)
- Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Datasets: same 5 frozen (seed-01 cda728..., seed-02 20a039..., seed-04 60777e..., seed-05 8023c9f4..., reserve-j01 607875...)
- Root: data/processed/research/hedging_policies_recovery_v3 (not created)
- Seeds: 60999, 53804, 89356 (globally disjoint from 31001/31002/31003)
- Tuples: 45 prospective (5×3×3, members→costs→successor seeds, 45 unique keys, 45 unique successor paths, 0 recovery_v2, 0 historical)
- Predecessors: 45 Task216 historical predecessor identities (no Task253 import)
- Task253 imports: 0
- Verdict: PASS

## 4. Authority Limits (Frozen, No Execution Authority)

- Successor tuple count: 45
- Training ceiling: 45
- Prospective consumed: 0
- Prospective remaining: 45
- Generation: 0
- Retry: 0
- Rerun: 0
- Replacement: 0
- Network: false
- Final_test_access: false
- Reexecution: PROHIBITED (one-shot, whole-campaign stop on first failure/nonterminal/ambiguity/provenance/runtime/source/collision)
- Execution authority: NOT_GRANTED
- Execution authorization: NOT_CREATED
- Recovery_v3 root: NOT_CREATED
- Prerequisite9: NOT_SATISFIED_PENDING_INDEPENDENT_PREREQUISITE_AUDIT
- No field implies freezing prerequisites authorizes execution
- Verdict: PASS

## 5. Current Authority

- Successor prerequisite: FROZEN_NO_EXECUTION_AUTHORITY_PENDING_AUDIT (90ff008... / e2e121... / 5c7ab59b...)
- Successor protocol: FROZEN (c63df0e...)
- Training contract: UNCHANGED_FROZEN
- Old seed enumeration: SUPERSEDED_FOR_SUCCESSOR_CAMPAIGN_ONLY
- Successor seed family: 60999/53804/89356
- Successor implementation: d762e5a/9e1b1a6c
- Successor tuples: 45
- Recovery_v3: FROZEN_NOT_CREATED
- Recovery authorization: NONE_VALID_FOR_SUCCESSOR_EXECUTION
- Policy completeness: NOT_SATISFIED
- Prerequisite #9: NOT_SATISFIED_PENDING_INDEPENDENT_PREREQUISITE_AUDIT
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- Final: SEALED, access 0
