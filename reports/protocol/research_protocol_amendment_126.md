# Amendment 126 — V5 GRU Recovery Successor Protocol Freeze

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-PROTOCOL-DESIGN-257
Risk: R4
Type: PROTOCOL_DESIGN_ONLY
Branch: main
Starting HEAD: 4abfa98fedf364dff9d4e476db2db8efca3031ab
Successor protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md
Successor protocol commit: c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0
Successor protocol canonical: 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418
Successor protocol raw: 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418
Successor protocol blob: 8715db1c76bd8457eca29ff523e54b2d9ce573ef
Successor namespace: data/processed/research/hedging_policies_recovery_v3
Task256: RECOVERY_V2_EXECUTION_INCIDENT_PROTOCOL_AUDIT_VALIDATED (Claude)
Original campaign: PERMANENTLY_CLOSED
Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE

## 1. Validated Basis

- Task253: GOVERNANCE_INVALID_EXECUTION_RUNTIME_SOURCE_DRIFT — 2 consumed (1 terminal, 1 nonterminal), 0 valid policies
- Task254: EXECUTION_FORENSIC_AUDIT_VALIDATED
- Task255: RECOVERY_V2_EXECUTION_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED — original campaign IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_CONTAMINATED_EXECUTION, Authorization251 CLOSED, recovery_v2 forensic read-only, same-45 restart not clean, successor permissible pending design
- Task256: RECOVERY_V2_EXECUTION_INCIDENT_PROTOCOL_AUDIT_VALIDATED
- Successor admissibility: H3_SUCCESSOR_RECOVERY_CAMPAIGN_SCIENTIFICALLY_PERMISSIBLE_PENDING_PROTOCOL_DESIGN_AND_INDEPENDENT_AUDIT (Task255)
- Source: REPAIR_REQUIRED_BEFORE_FUTURE_RECOVERY (trainer.py authorized_commit bug, not repaired in Task257)

## 2. Successor Protocol Identity

- Path: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md
- Commit: c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0
- Canonical: 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418
- Blob: 8715db1c76bd8457eca29ff523e54b2d9ce573ef
- H3/SAP/training contract: unchanged (H3 Delta_CVaR, SAP 76de0a..., contract v3 79611b...)
- Datasets: same 5 frozen (cda728..., 20a039..., 60777e..., 8023c9..., 607875...)
- Costs: 0.0, 0.001, 0.005 (unchanged)
- No hyperparameter adaptation from Task253

## 3. New Namespace and Firewall

- Successor root: data/processed/research/hedging_policies_recovery_v3 (versioned v3, distinct from hedging_policies, recovery_v1, recovery_v2)
- Historical roots: hedging_policies, recovery_v1, recovery_v2 — distinct, no collision
- Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE — successor must never read checkpoint.pt, checkpoint_final.pt, warm-start, or load Task253 model; no trajectory/stdout/CVaR reference
- Collision: 0 recovery_v2 paths in 45-tuple ledger
- Root creation: false (not created in Task257)

## 4. Seed Derivation (One-Shot, Outcome-Independent)

- Algorithm: SHA256 of domain-separated canonical string, first 8 hex → 40000 + (int % 50000), range 40000-89999
- Domain separator: neuralmarket-v5-gru-recovery-successor-v1
- Immutable inputs: contract v3 canonical 79611b6b..., SAP canonical 76de0a1a..., recovery protocol canonical 4bf228ad..., prereq canonical c416ba81..., sorted dataset SHAs (20a039...|60777e...|607875...|8023c9...|cda728...), i in [0,1,2]
- Prohibited inputs: Task253 hashes/CVaR/epoch/checkpoints/trajectory/timestamps, Task254/255/256 classifications except as justification, wall-clock, OS entropy
- Encoding: "{domain}|{contract}|{sap}|{recovery_protocol}|{prereq}|{sorted_dataset_concat}|{i}" UTF-8, SHA256
- Extraction: hash[:8] hex → int → 40000 + (int % 50000)
- Bounds: 40000-89999, positive, torch-compatible
- Collision handling: deterministic counter rehash "{base}|{i}|{c}" if seed in old {31001,31002,31003} or duplicate among derived (none needed)
- Rule count: 1
- Rule revision: PROHIBITED_AFTER_FREEZE
- Alternative-rule evaluation: PROHIBITED
- Derived seed 0: 60999 (hash c4a61e07bd31..., input base|0)
- Derived seed 1: 53804 (hash 72f5d64c7e87..., input base|1)
- Derived seed 2: 89356 (hash 29d0cb2c350a..., input base|2)
- Old-seed overlap: 0 (60999,53804,89356 ≠ 31001/31002/31003)
- Reproducibility: deterministic SHA256, all intermediates recorded

## 5. Prospective Ledger

- Members: seed-01, seed-02, seed-04, seed-05, reserve-j01 (5)
- Costs: 0.0, 0.001, 0.005 (3)
- Hedger seeds: 60999, 53804, 89356 (3, derivation order)
- Ordinals: 1..45 deterministic (members → costs → successor seeds)
- Tuple count: 45 exact (5×3×3)
- Unique tuples: 45 (member+cost+seed)
- Unique paths: 45 (successor root + run_prefix + cost_bps + hedger_seed)
- Successor paths: 45 (all under recovery_v3)
- Recovery_v2 paths: 0
- Historical paths: 0
- Predecessors: Task216 historical predecessor evidence (no Task253 ordinal import)

## 6. Authority Limits (Frozen)

- Ceiling: 45
- Consumed: 0
- Remaining: 45
- Generation: 0
- Retry: 0
- Rerun: 0
- Replacement: 0
- Network: false
- Final: false
- First-failure stop: entire successor campaign stops on first failure/nonterminal/ambiguity/provenance/runtime/source/collision, no continuation until independent adjudication
- Reexecution: PROHIBITED (one-shot prospective, no resumability)

## 7. Task253 Firewall

- Checkpoint reuse: 0 (no recovery_v2 checkpoint.pt)
- Final checkpoint reuse: 0
- Warm start: 0
- Trajectory reference: 0
- Stdout reference: 0
- Metric reference: 0 (no CVaR/best_epoch use)
- Model parameter reuse: 0
- Execution-path reference: 0
- Verdict: PASS (all 45 successor tuples use only frozen datasets and new seeds)

## 8. Source State

- Defect: trainer.py ~1160 authorized_commit typo (Task255)
- Repair required: YES
- Repaired: NO (Task257 protocol design only)
- Authorization: NONE_VALID_FOR_SUCCESSOR_EXECUTION (no successor authorization created)
- Relationship: separate gates — source repair does not confer successor scientific authority; successor protocol does not imply source correctness

## 9. Current Authority

- Successor campaign: SCIENTIFICALLY_PERMISSIBLE_PROTOCOL_FROZEN_PENDING_AUDIT
- Original campaign: PERMANENTLY_CLOSED
- Recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE
- Successor seed family: FROZEN_PENDING_INDEPENDENT_AUDIT (60999,53804,89356)
- Successor tuples: 45
- Successor ceiling: 45, consumed 0, remaining 45, retry/rerun/replacement 0
- Source: REPAIR_REQUIRED_BEFORE_FUTURE_RECOVERY
- Recovery authorization: NONE_VALID_FOR_SUCCESSOR_EXECUTION
- Prerequisite #9: NOT_SATISFIED
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- Final: SEALED, access 0

Protocol frozen without source mutation, authorization creation, recovery execution, synthetic generation, held-out, H3, or final-test activity. Successor root not created.

