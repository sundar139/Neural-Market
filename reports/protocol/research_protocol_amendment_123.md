# Amendment 123 — V5 GRU Recovery V2 Execution Authorization Freeze

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-V2-EXECUTION-AUTHORIZATION-FREEZE-248
Risk: R4
Type: AUTHORIZATION_FREEZE_ONLY
Branch: main
Starting HEAD: 293a66836c481cb9f19820b74b407cf8fdb3b6d8
Prerequisite artifact: reports/protocol/hedging_recovery_v2_authorization_prerequisites_246.json
Prerequisite commit: d4813d60002128c898fe88e40fd846dde80b5c3d
Prerequisite canonical: c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0
Prerequisite raw: 88b51be4822c23c6c608fc75cd3cb4299d96afc1f2a18b7d4e53b929df296224
Prerequisite blob: a9d74c8a9fdc325d7e0f99b8a382c4bf8b3428d3

## 1. Validated Chain

- Task-243: RECOVERY_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED — 40d2591ae59b6f504c65e7a5632ccf2a6606ed30 / ad29a5039849499336f97fef0dbadfc2abcc5009b4d55e810741dec8cf468015 / d4e57711fb5bad50495ed7aba018e5a9f4ccc121
- Task-244: RECOVERY_V2_NAMESPACE_IMPLEMENTATION_VALIDATED — f741f3625816ec7a6d0173cc0b949bee1dcba00d / 908ce6e16ff5dcded1d85de6b05486b8bc4c085a8abc17398b749bbaa3ef18f3
- Task-245: RECOVERY_V2_NAMESPACE_AUDIT_VALIDATED
- Task-246: RECOVERY_V2_AUTHORIZATION_PREREQUISITES_FROZEN_VALIDATED — d4813d60002128c898fe88e40fd846dde80b5c3d
- Task-247: RECOVERY_V2_AUTHORIZATION_PREREQUISITE_AUDIT_VALIDATED
- Task-236: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_EXCLUDED — 4 invocations, 1 unique, 3 duplicates, 0 ordinal2+, 0 scientific results
- New campaign: V5_GRU_RECOVERY_POST_INCIDENT_NEW_CAMPAIGN — SCIENTIFICALLY_ALLOWABLE

## 2. Authorization248 Identity

- Path: reports/protocol/hedging_recovery_v2_execution_authorization_248.json
- Task ID: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-248
- Authorization type: GRU_TRAINING_RECOVERY_V1 (schema version, not v1 namespace)
- Commit: 7204cf1e753a93778ea6f25dff9a62db0fa18484
- Canonical SHA256: 80fb86574020510bad7c9bfcd0463176ffb4fc0082d15d553e6ef98fbcda41ae
- Raw SHA256: cf3b3e6ed9c2fee8f4c3b5be35f32dff6727ca51943a4ddf6a907f9a108a1aa1
- Git blob: 8112ae411b54fdeaccc067f3482aa391b667c53b
- Commit→path blob: 8112ae411b54fdeaccc067f3482aa391b667c53b
- Filtered-worktree blob: 8112ae411b54fdeaccc067f3482aa391b667c53b
- Prerequisite: d4813d60002128c898fe88e40fd846dde80b5c3d / c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0
- Implementation: f741f3625816ec7a6d0173cc0b949bee1dcba00d
- Manifest: 908ce6e16ff5dcded1d85de6b05486b8bc4c085a8abc17398b749bbaa3ef18f3
- Source blobs: 15 exact (runner 14c35a69, trainer f1024919, CLI 86b9468f etc.)
- Training contract: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad220db889166469799372759dfe1a96e35f
- Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Root: data/processed/research/hedging_policies_recovery_v2
- Datasets: 5 — seed-01 cda7280a, seed-02 20a0390f, seed-04 60777e33, seed-05 8023c9f4, reserve-j01 60787517
- Tuples: 45 (5×3×3)
- Predecessors: 45 (classification SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP, zero Task236 incident entries)
- Ceiling: 45, Consumed: 0, Remaining: 45, Generation: 0, Network: false, Final access: false, Retry: 0, Rerun: 0, Replacement: 0
- Recovery execution: 0, H3: NOT_YET_ADJUDICATED, H2: H2_NOT_SUPPORTED, FINAL: SEALED, Access: 0
- Verifier: PASS (validate_recovery_authorization_schema at commit)

## 3. Firewalls Preserved

No source mutation, no prerequisite edit, no historical authorization edit, no recovery execution, no root creation, no generation, no held-out, no H3, no final test, no network, no push.
