# Amendment 122 — V5 GRU Recovery V2 Authorization Prerequisite Freeze

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-V2-AUTHORIZATION-PREREQUISITE-FREEZE-246
Risk: R4
Type: AUTHORIZATION_PREREQUISITE_FREEZE_ONLY
Branch: main
Starting HEAD: f741f3625816ec7a6d0173cc0b949bee1dcba00d
Prerequisite commit: d4813d60002128c898fe88e40fd846dde80b5c3d
Adjudication commit: 40d2591ae59b6f504c65e7a5632ccf2a6606ed30
Incident amendment: 258e7e058baae183b44c1e5ff7b4864583dcfa60
Adjudication document: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_incident_adjudication_v1.md

## 1. Prerequisite Validation

- Task-245 validated implementation: f741f3625816ec7a6d0173cc0b949bee1dcba00d / 908ce6e16ff5dcded1d85de6b05486b8bc4c085a8abc17398b749bbaa3ef18f3
- Source closure: 15 paths, __init__.py present, init.py absent, runner 14c35a693c4004e11b7adada9eab6779c34cbc45, trainer f1024919901ba95273aebe05f6b881cbfded8a09, CLI 86b9468f81aa45755920907ec39f5ff7b795dcc9, generation 1b8710fc77362eb59a7167b3b4575d8b93f63d12
- Adjudication validated: Task-243 RECOVERY_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED
- Task-236 classification: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_EXCLUDED, observed invocations 4, unique tuples 1, duplicates 3, ordinal2+ 0, scientific results observed 0
- New campaign classification: V5_GRU_RECOVERY_POST_INCIDENT_NEW_CAMPAIGN, SCIENTIFICALLY_ALLOWABLE

## 2. Frozen Prerequisites

- Implementation: f741f3625816ec7a6d0173cc0b949bee1dcba00d
- Manifest: 908ce6e16ff5dcded1d85de6b05486b8bc4c085a8abc17398b749bbaa3ef18f3
- Recovery root: data/processed/research/hedging_policies_recovery_v2
- Datasets: 5 validated Task-215 synthetic datasets — seed-01 cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287, seed-02 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7, seed-04 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8, seed-05 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204, reserve-j01 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc (each 50000/40000/10000)
- Tuples: 45 exact — members [seed-01, seed-02, seed-04, seed-05, reserve-j01] × costs [0.0, 0.001, 0.005] × hedger seeds [31001, 31002, 31003], ordinals 1..45, all expected paths under recovery_v2, none under v1
- Predecessors: 45 immutable Task-216 predecessor identities — each historical_artifact_path, historical_execution_started_sha, historical_checkpoint_sha, historical_terminal_sha, historical_classification SCIENTIFICALLY_INVALID_TRAINING_LOOP_NO_OP, Task-236 incident attempts NOT included
- Training contract: reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md canonical 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 raw d3e30e2cfa897d5b2c436d9c0a932b06fc862370c73ffbc3f80dcaf862c144dd blob eef7ad220db889166469799372759dfe1a96e35f
- Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Training ceiling: 45, prospective consumed: 0, prospective remaining: 45, generation: 0, network: false, final access: false, retry/rerun/replacement: 0

## 3. Guardrails

- One invocation per prospective tuple, stop entire campaign on first failure/ambiguity, preserve failed/partial artifacts byte-for-byte, no deletion, no rm-rf, no source mutation after authorization freeze, no authorization mutation after freeze, no runtime mutation after freeze, fail-before-write provenance validation required before execution_started

## 4. Artifact

- Prerequisite artifact: reports/protocol/hedging_recovery_v2_authorization_prerequisites_246.json
- Prerequisite commit: d4813d60002128c898fe88e40fd846dde80b5c3d
- Prerequisite canonical SHA256: c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0
- Prerequisite raw SHA256: 88b51be4822c23c6c608fc75cd3cb4299d96afc1f2a18b7d4e53b929df296224
- Prerequisite Git blob: a9d74c8a9fdc325d7e0f99b8a382c4bf8b3428d3
- Commit→path blob: a9d74c8a9fdc325d7e0f99b8a382c4bf8b3428d3
- Execution authority: NOT_GRANTED
- Authorization: NOT_CREATED
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- FINAL: SEALED
- Access: 0
