# Amendment 124 — V5 GRU Recovery V2 Hardened Authorization Refreeze

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-V2-EXECUTION-AUTHORIZATION-REFREEZE-251
Risk: R4
Type: AUTHORIZATION_FREEZE_ONLY
Branch: main
Starting HEAD: 0b3841786ca77bbadb8c564ca33c75ff93f27bf1
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
- Task-249: RECOVERY_V2_AUTHORIZATION_VALIDATOR_HARDENING_VALIDATED — 0b3841786ca77bbadb8c564ca33c75ff93f27bf1 / 6c13b0ee960e2688aa71403edf9d9bbaca13c1ab451aebc266c1e81d35ab9cac
- Task-250: RECOVERY_V2_AUTHORIZATION_VALIDATOR_AUDIT_VALIDATED (Hermes)
- Task-236: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_EXCLUDED — 4 invocations, 1 unique, 3 duplicates, 0 ordinal2+, 0 scientific results
- New campaign: V5_GRU_RECOVERY_POST_INCIDENT_NEW_CAMPAIGN — SCIENTIFICALLY_ALLOWABLE

## 2. Authorization251 Identity

- Path: reports/protocol/hedging_recovery_v2_execution_authorization_251.json
- Task ID: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-EXECUTION-AUTHORIZATION-251
- Authorization type: GRU_TRAINING_RECOVERY_V1
- Commit: 638805b7c2837b764d4b3f479442236079557b25
- Canonical SHA256: e09b8a4268fb8a3a06f4036c84dfa4d3fa5b7b29b989c0e16e0e9b367fbbc1f3
- Raw SHA256: ba6d13be1e0459ff38602fa647707a5e0a6f7fc28e8189fe44bc671defc8006f
- Git blob: de8117fb5bdbf26d48ee56a63ef68c275996637b
- Commit→path blob: de8117fb5bdbf26d48ee56a63ef68c275996637b
- Filtered-worktree blob: de8117fb5bdbf26d48ee56a63ef68c275996637b
- Prerequisite: d4813d60002128c898fe88e40fd846dde80b5c3d / c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0 / 88b51be4822c23c6c608fc75cd3cb4299d96afc1f2a18b7d4e53b929df296224 / a9d74c8a9fdc325d7e0f99b8a382c4bf8b3428d3
- Prerequisite implementation (historic, preserved): f741f3625816ec7a6d0173cc0b949bee1dcba00d / 908ce6e16ff5dcded1d85de6b05486b8bc4c085a8abc17398b749bbaa3ef18f3
- Implementation: 0b3841786ca77bbadb8c564ca33c75ff93f27bf1
- Manifest: 6c13b0ee960e2688aa71403edf9d9bbaca13c1ab451aebc266c1e81d35ab9cac
- Source blobs: 15 exact (runner 5fac8765d3a4972d3d212d3261deab1caace4628, trainer f1024919901ba95273aebe05f6b881cbfded8a09, CLI 86b9468f81aa45755920907ec39f5ff7b795dcc9, generation 1b8710fc77362eb59a7167b3b4575d8b93f63d12)
- Training contract: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad220db889166469799372759dfe1a96e35f
- Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Root: data/processed/research/hedging_policies_recovery_v2
- Datasets: 5 — seed-01 cda7280a, seed-02 20a0390f, seed-04 60777e33, seed-05 8023c9f4, reserve-j01 60787517
- Tuples: 45 (5×3×3)
- Predecessors: 45 (classification SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP)
- Ceiling: 45, Consumed: 0, Remaining: 45, Generation: 0, Network: false, Final access: false, Retry: 0, Rerun: 0, Replacement: 0
- Recovery execution: 0, H3: NOT_YET_ADJUDICATED, H2: H2_NOT_SUPPORTED, FINAL: SEALED, Access: 0
- Verifier: PASS (hardened validate_recovery_authorization_schema at commit)

## 3. Historical Authorization248

- Status: FROZEN_HISTORICAL_NO_EXECUTION_AUTHORITY (preserved, not edited)
- Path: reports/protocol/hedging_recovery_v2_execution_authorization_248.json
- Commit: 7204cf1e753a93778ea6f25dff9a62db0fa18484
- Canonical: 80fb86574020510bad7c9bfcd0463176ffb4fc0082d15d553e6ef98fbcda41ae
- Blob: 8112ae411b54fdeaccc067f3482aa391b667c53b

## 4. Firewalls Preserved

No source mutation, no prerequisite edit, no historical authorization edit, no recovery execution, no root creation, no generation, no held-out, no H3, no final test, no network, no push.
