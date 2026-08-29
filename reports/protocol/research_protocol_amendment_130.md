# Amendment 130 — Successor Predecessor Binding Normative Freeze

Date: 2026-08-28
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-PREDECESSOR-BINDING-NORMATIVE-FREEZE-AND-DETERMINISM-REPAIR-284
Risk: R4
Type: BOUNDED_PREDECESSOR_BINDING_FREEZE_AND_SOURCE_REPAIR
Branch: main
Starting HEAD: 57ce5fd87a39cf9471963eca7a72eea9a1306d6d
Starting manifest: 59d373294eedad54148d9c74fa044c5d043df4614e3737455b74921d7ecbd328
Task283 audit: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-EXECUTION-GATE-AUDIT-BLOCKER-REPAIR-AUDIT-283.md (57ce5fd / 59d37329... — AUDIT_COMPLETE_WITH_ONE_BLOCKING_FINDING)

## 1. Authority and Freeze Basis

This amendment is append-only and prospective. It freezes the complete bijective successor-to-Task216 predecessor relation BEFORE any successor execution.

- Task283 audit outcome: 45 successor tuples × 6 predecessor seed orderings = 270 bindings, 0 member mismatches, 0 cost-band mismatches, 165 historical-seed mismatches — no normative per-tuple historical hedger-seed mapping existed
- Starting implementation: 57ce5fd87a39cf9471963eca7a72eea9a1306d6d / 59d373294eedad54148d9c74fa044c5d043df4614e3737455b74921d7ecbd328 (runner 8410334da7dd553e90c3fc7ab06b61403bbe1511, trainer 1eddca78745e05a354ef9c29a7ac9da04ae50ac5)
- Task257 successor protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md (c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0 / 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418 / 8715db1c76bd8457eca29ff523e54b2d9ce573ef)
- Prerequisite264: reports/protocol/hedging_recovery_successor_authorization_prerequisites_264.json (0d4489fe1880a4cfed9752bf3cc32aa19953adae / fe5983662d4e8b1269c6d305a5a2741c7c171e38c4e92f9bf8c8e8e77b491496 / 24cfc59af40a80f51f5e3d4bc2b3297607f754d4)
- Task276 historical prerequisite: reports/protocol/hedging_recovery_successor_execution_authorization_prerequisites_276.json (7081b4465d00a65d9a26a995644fdc0eaed5f51a / be35558f77664244b74eb4ec8b857257829483b617a830b1fd508ee60a070f38 / 08030c4d0385131a50c36833b74f52e2f1232a52)
- Amendment129: reports/protocol/research_protocol_amendment_129.md (e077efa8f50aad5e778ecd2d1622375f05bf171c)
- Training contract v3: reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md (79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad220db889166469799372759dfe1a96e35f)
- SAP: 76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa
- Historical ordered seed family: 31001 / 31002 / 31003 (Task216)
- Successor ordered seed family: 60999 / 53804 / 89356 (Task257 §5, globally disjoint)
- Normative relation: 60999→31001, 53804→31002, 89356→31003 (ordinal-preserving bijection)
- Classification: PROSPECTIVE_OUTCOME_INDEPENDENT_PROVENANCE_BINDING
- Scope: SUCCESSOR_RECOVERY_V3_PREDECESSOR_IDENTITY_ONLY
- Successor execution at freeze: 0 tuples executed, consumed 0, remaining 45, no authorization, recovery_v3 ABSENT, no generation, no held-out, no H3, no final-test, no network, no push

This amendment binds the 45 predecessor identities only as a set (Amendment129) to a 45-entry explicit relation. It does NOT change successor hedger seeds, historical artifacts, datasets, training data, hyperparameters, optimizer, architecture, CVaR objective, SAP, H3 criteria, or final-test policy.

## 2. Normative Seed Mapping

Historical ordered family (Task216 evidence order):
- 31001 (i=0)
- 31002 (i=1)
- 31003 (i=2)

Successor ordered family (Task257 §5 derivation order i=0,1,2):
- 60999 (i=0)
- 53804 (i=1)
- 89356 (i=2)

Normative bijection (prospective, outcome-independent):
- 60999 → 31001
- 53804 → 31002
- 89356 → 31003

This rule is PROSPECTIVE_OUTCOME_INDEPENDENT_PROVENANCE_BINDING. No scientific result has been observed for recovery_v3. The mapping affects provenance identity ONLY.

## 3. Complete 45-Entry Successor-to-Predecessor Mapping

For every successor tuple (member, cost, successor_hedger_seed) its unique Task216 predecessor is (member, same cost, mapped historical_hedger_seed). Each Task216 predecessor is used exactly once. All 45 successor tuple keys are unique. All 45 historical predecessor identities are unique.

| member | cost | cost_bps | run_prefix | successor_hedger_seed | historical_hedger_seed | historical_predecessor_key | historical_predecessor_artifact_path | historical_classification |
|---|---|---|---|---|---|---|---|
| seed-01 | 0.0 | 0 | 5bdbaabd2fb257a7 | 60999 | 31001 | seed-01:0.0:31001 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.0 | 0 | 5bdbaabd2fb257a7 | 53804 | 31002 | seed-01:0.0:31002 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.0 | 0 | 5bdbaabd2fb257a7 | 89356 | 31003 | seed-01:0.0:31003 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_0/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.001 | 10 | 5bdbaabd2fb257a7 | 60999 | 31001 | seed-01:0.001:31001 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_10/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.001 | 10 | 5bdbaabd2fb257a7 | 53804 | 31002 | seed-01:0.001:31002 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_10/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.001 | 10 | 5bdbaabd2fb257a7 | 89356 | 31003 | seed-01:0.001:31003 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_10/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.005 | 50 | 5bdbaabd2fb257a7 | 60999 | 31001 | seed-01:0.005:31001 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_50/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.005 | 50 | 5bdbaabd2fb257a7 | 53804 | 31002 | seed-01:0.005:31002 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_50/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-01 | 0.005 | 50 | 5bdbaabd2fb257a7 | 89356 | 31003 | seed-01:0.005:31003 | data/processed/research/hedging_policies/5bdbaabd2fb257a7_seed-01/c_50/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.0 | 0 | 62c7406cb3a2c642 | 60999 | 31001 | seed-02:0.0:31001 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_0/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.0 | 0 | 62c7406cb3a2c642 | 53804 | 31002 | seed-02:0.0:31002 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_0/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.0 | 0 | 62c7406cb3a2c642 | 89356 | 31003 | seed-02:0.0:31003 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_0/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.001 | 10 | 62c7406cb3a2c642 | 60999 | 31001 | seed-02:0.001:31001 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_10/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.001 | 10 | 62c7406cb3a2c642 | 53804 | 31002 | seed-02:0.001:31002 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_10/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.001 | 10 | 62c7406cb3a2c642 | 89356 | 31003 | seed-02:0.001:31003 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_10/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.005 | 50 | 62c7406cb3a2c642 | 60999 | 31001 | seed-02:0.005:31001 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_50/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.005 | 50 | 62c7406cb3a2c642 | 53804 | 31002 | seed-02:0.005:31002 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_50/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-02 | 0.005 | 50 | 62c7406cb3a2c642 | 89356 | 31003 | seed-02:0.005:31003 | data/processed/research/hedging_policies/62c7406cb3a2c642_seed-02/c_50/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.0 | 0 | 77e7de9efabb7ce3 | 60999 | 31001 | seed-04:0.0:31001 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_0/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.0 | 0 | 77e7de9efabb7ce3 | 53804 | 31002 | seed-04:0.0:31002 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_0/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.0 | 0 | 77e7de9efabb7ce3 | 89356 | 31003 | seed-04:0.0:31003 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_0/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.001 | 10 | 77e7de9efabb7ce3 | 60999 | 31001 | seed-04:0.001:31001 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_10/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.001 | 10 | 77e7de9efabb7ce3 | 53804 | 31002 | seed-04:0.001:31002 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_10/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.001 | 10 | 77e7de9efabb7ce3 | 89356 | 31003 | seed-04:0.001:31003 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_10/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.005 | 50 | 77e7de9efabb7ce3 | 60999 | 31001 | seed-04:0.005:31001 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_50/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.005 | 50 | 77e7de9efabb7ce3 | 53804 | 31002 | seed-04:0.005:31002 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_50/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-04 | 0.005 | 50 | 77e7de9efabb7ce3 | 89356 | 31003 | seed-04:0.005:31003 | data/processed/research/hedging_policies/77e7de9efabb7ce3_seed-04/c_50/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.0 | 0 | 1e8aa171993a1aba | 60999 | 31001 | seed-05:0.0:31001 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_0/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.0 | 0 | 1e8aa171993a1aba | 53804 | 31002 | seed-05:0.0:31002 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_0/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.0 | 0 | 1e8aa171993a1aba | 89356 | 31003 | seed-05:0.0:31003 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_0/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.001 | 10 | 1e8aa171993a1aba | 60999 | 31001 | seed-05:0.001:31001 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_10/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.001 | 10 | 1e8aa171993a1aba | 53804 | 31002 | seed-05:0.001:31002 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_10/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.001 | 10 | 1e8aa171993a1aba | 89356 | 31003 | seed-05:0.001:31003 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_10/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.005 | 50 | 1e8aa171993a1aba | 60999 | 31001 | seed-05:0.005:31001 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_50/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.005 | 50 | 1e8aa171993a1aba | 53804 | 31002 | seed-05:0.005:31002 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_50/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| seed-05 | 0.005 | 50 | 1e8aa171993a1aba | 89356 | 31003 | seed-05:0.005:31003 | data/processed/research/hedging_policies/1e8aa171993a1aba_seed-05/c_50/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.0 | 0 | 38c5113b27568e14 | 60999 | 31001 | reserve-j01:0.0:31001 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_0/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.0 | 0 | 38c5113b27568e14 | 53804 | 31002 | reserve-j01:0.0:31002 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_0/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.0 | 0 | 38c5113b27568e14 | 89356 | 31003 | reserve-j01:0.0:31003 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_0/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.001 | 10 | 38c5113b27568e14 | 60999 | 31001 | reserve-j01:0.001:31001 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_10/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.001 | 10 | 38c5113b27568e14 | 53804 | 31002 | reserve-j01:0.001:31002 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_10/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.001 | 10 | 38c5113b27568e14 | 89356 | 31003 | reserve-j01:0.001:31003 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_10/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.005 | 50 | 38c5113b27568e14 | 60999 | 31001 | reserve-j01:0.005:31001 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_50/h_31001 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.005 | 50 | 38c5113b27568e14 | 53804 | 31002 | reserve-j01:0.005:31002 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_50/h_31002 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |
| reserve-j01 | 0.005 | 50 | 38c5113b27568e14 | 89356 | 31003 | reserve-j01:0.005:31003 | data/processed/research/hedging_policies/38c5113b27568e14_reserve-j01/c_50/h_31003 | SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP |

Verification: 45 entries, 45 unique successor tuple keys (member+cost+successor_hedger_seed), 45 unique historical predecessor keys, 45 unique historical artifact paths, each Task216 predecessor used exactly once, zero successor execution at freeze.

## 4. Preservation

All previous amendments 1-129 remain byte-for-byte, append-only. Training contract v3, SAP, successor protocol, prerequisite264, Task276 remain unchanged. Successor hedger seeds, historical artifacts, datasets, training data, hyperparameters, optimizer, architecture, CVaR objective remain unchanged.

## 5. Authority

- Successor implementation: 57ce5fd87a39cf9471963eca7a72eea9a1306d6d / 59d373294eedad54148d9c74fa044c5d043df4614e3737455b74921d7ecbd328 — FROZEN_PENDING_AUDIT_NO_AUTHORITY
- Prerequisite freeze: Amendment129 / 276 — FROZEN_PENDING_AUDIT_NO_AUTHORITY
- Successor protocol: canonical POSIX `reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md` — VALIDATED
- Successor tuples: 45 — FROZEN
- Predecessors: 45 Task216 — FROZEN as 45-entry explicit bijection per this amendment
- Authority: 45/0/45/0 — FROZEN
- Recovery_v3: FROZEN_NOT_CREATED
- Execution authorization: NONE
- Prerequisite9: NOT_SATISFIED
- H3: NOT_YET_ADJUDICATED
