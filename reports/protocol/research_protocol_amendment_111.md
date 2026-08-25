# Amendment 111 — V5 Synthetic Generation Protocol / Evidence Reconciliation

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-PROTOCOL-RECONCILIATION-214
Risk: R4
Type: PROTOCOL_EVIDENCE_RECONCILIATION_ONLY
Branch: main
Starting HEAD: b72010f2e7bdf8c75b158f28b7c4f5e20a795cc6
Prerequisite: NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-FORENSIC-ADJUDICATION-213 — ACCEPTED_FORENSIC_ADJUDICATION

## 1. Adjudicated chronology and identities

Task-212 execution chain (forensically recovered):
- eb115afb09e6bff417ea037b012f2a56fc3e20ad (Task-211 frozen head, implementation 66f0fce)
- → 1e6af6e9bcd1150700f34f8e7e0c7f9d280a934b (fix: align production dispatch with v3 authorization API and deterministic preflight — 2 files, 8 insertions)
- → 69c534fedae0d3bf81ae55c00b50c737db4dfd6e (authorize 212)
- → 7e6dd3788a3d7ab213d0bc3849c93a85c2bd53a1 (evidence v1)
- → b72010f2e7bdf8c75b158f28b7c4f5e20a795cc6 (Amendment 110)
- → 50bfad97e8efb0a7c6490dc7ed0420f2b4794760 (reconciliation v2, this task first stage)

Original evidence v1: reports/research/evidence/structured_vol_v5_hedging_synthetic_generation_execution_v1.json at 7e6dd3788a3d7ab213d0bc3849c93a85c2bd53a1 — canonical LF 5c56de49c799610d3847d5ca190106d66168eeff2039b3923449da717fa980cd / raw 8373adec35ecdb27c1d6fcc3b02ff5ce218170679a6e566ab62df18a981e4d11 / blob 8c6fcc65a3cfc77c1342d9d43efded73ab7ce91d — PRESERVED_INACCURATE_HISTORICAL_EVIDENCE
Amendment 110: reports/protocol/research_protocol_amendment_110.md at b72010f2e7bdf8c75b158f28b7c4f5e20a795cc6 — canonical/raw 91f6087fbee548dd57b5353628991d5b143c74cdfdb3fe004eda42bca1d632f9 / blob 31b3f514c5a4a04c55aa13ea0825b55b25783e94 — PRESERVED_PARTIALLY_INACCURATE_HISTORICAL_PROTOCOL
Reconciliation v2: reports/research/evidence/structured_vol_v5_hedging_synthetic_generation_execution_reconciliation_v2.json at 50bfad97e8efb0a7c6490dc7ed0420f2b4794760 — canonical af3b8475bb0b84ac32ead6e512aa338f1995e0fdd08e2d7173c13c15da20567a / raw bd2dde9da3fd7b2f3120c7da003dc00b7ee2729fca70e0a7dec4c702c9d294b3 / blob 2d7941e3e7152945e2394720b9080d96ab6bc874 — authoritative corrected execution history

Implementation transition: 66f0fce3f93c74090523a92617d5d980845e3b9d (manifest 79cad575a932ed87dfd6336d058275431cd49b62988aabe20557eca60421bac3) → 1e6af6e9bcd1150700f34f8e7e0c7f9d280a934b (manifest e3e7b6192881a06c81893973ad9c40d981e11e240a4af450d9185e4fa78622f4) — dispatch/preflight only, no scientific change.
Authorization 212: reports/protocol/hedging_execution_authorization_212.json at 69c534fedae0d3bf81ae55c00b50c737db4dfd6e — canonical 42eb310d28d628995319d9143ef1ec5c234429aedabc6d338f678f233df8c6a2 / raw b61999e16e7f695cc94ada354f70af690d7d038930e1231d4d81a86c5212a724 / blob f7d30259c7da43a631a1b30bea02d7490f0fa517 — binds implementation 1e6af6e, contract v3 eef7ad..., runtime 17e3bb52..., members 5, checkpoints 5, RNG 42001/42002/42004/42005/42006, generation 5, training 45.

## 2. Corrected six-attempt ledger (authoritative)

Attempt 1: seed-01 UNAUTHORIZED_SCIENTIFIC_EXECUTION — private/internal helper (direct generate_and_persist with monkey-patched verify), eb115af pre-fix, 211 not bound, RNG 42001, N 50000, checkpoint 452f70..., dataset SHA cda7280a..., manifest 176838..., real inference true, started true, dataset true, retained false, deleted true, consumed-marker deletion true.

Attempts 2-6: AUTHORIZED_VALID_EXECUTION via hard CLI with authorization 212 and implementation 1e6af6e:
- Attempt 2: seed-01 2026-08-25T08:26:31Z-08:26:34Z dataset cda7280a... manifest 772a0a... rows 50000 terminal 062ea1...
- Attempt 3: seed-02 08:26:48Z-08:26:50Z dataset 20a0390f... manifest e35c06...
- Attempt 4: seed-04 08:26:58Z-08:27:00Z dataset 60777e33... manifest 4a51347c...
- Attempt 5: seed-05 08:27:07Z-08:27:10Z dataset 8023c9f4... manifest 98c3c4b4...
- Attempt 6: reserve-j01 08:27:18Z-08:27:20Z dataset 60787517... manifest 881db08f...

Total scientific invocations: 6 (authorized 5, unauthorized 1, successful 6, retained 5, deleted 1, seed-01 count 2, rerun true, replacement true, consumed deletion true, generation ceiling 5, ceiling exceeded true for global history but retained count equals ceiling).

Task-212 status: REJECTED_GOVERNANCE_INVALID — due to unauthorized invocation, ceiling exceed (6 > 5), consumed-marker deletion, and original evidence inaccuracy; retained 5 bytes themselves are uncontaminated.

## 3. Generation authority closure

AUTHORIZATION 212 GENERATION SLOTS: 5_OF_5_CONSUMED
FURTHER SYNTHETIC GENERATION: PROHIBITED
REGENERATION: PROHIBITED
RETRY: PROHIBITED
RERUN: PROHIBITED
REPLACEMENT: PROHIBITED
Historical unauthorized Attempt 1 is OUTSIDE AUTHORIZATION-212 CEILING BUT COUNTS IN GLOBAL SCIENTIFIC INVOCATION HISTORY (6 vs 5) — not mathematically forced to 5.

## 4. Retained datasets admitted for quality audit

All five current bytes match Task-213 forensic values and are ADMITTED_FOR_SCIENTIFIC_QUALITY_AUDIT (not fully validated, not training-ready):

- seed-01: 5bdbaabd2fb257a7 08:26:31Z-08:26:34Z checkpoint 452f70... RNG 42001 started 36279aef... dataset 9436669 cda7280... rows 50000 manifest 772a0a... terminal 062ea1... success
- seed-02: 62c7406cb3a2c642 08:26:48Z-08:26:50Z 9e6f8cd... 42002 17fdb24c... 9423877 20a0390... e35c06... 9d44390f...
- seed-04: 77e7de9efabb7ce3 08:26:58Z-08:27:00Z 87d02215... 42004 a88c8290... 9432177 60777e33... 4a51347c... 99cf1c96...
- seed-05: 1e8aa171993a1aba 08:27:07Z-08:27:10Z 3a71b12e... 42005 608f1a73... 9434738 8023c9f4... 98c3c4b4...
- reserve-j01: 38c5113b27568e14 08:27:18Z-08:27:20Z 50d14095... 42006 1a4f... 9426840 60787517... 881db08f...

Bytes changed: false. Scientific quality: NOT_YET_AUDITED. Aggregate admissibility: 5_ADMITTED_FOR_SCIENTIFIC_QUALITY_AUDIT.

## 5. What this reconciliation does not do

- Does not mutate evidence v1 or Amendment 110 bytes.
- Does not edit authorization 212.
- Does not regenerate datasets.
- Does not train GRU policies (0 invocations consumed).
- Does not compute Wasserstein/ACF/variance/bootstrap/hedging P&L/CVaR.
- Does not access final-test rows or network.

## 6. Reconciled protocol state

TASK-212: REJECTED_GOVERNANCE_INVALID_RECONCILED
TASK-213: FORENSIC_ADJUDICATION_ACCEPTED
TASK-214: PROTOCOL_EVIDENCE_RECONCILED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
RETAINED SYNTHETIC DATASETS: 5_ADMITTED_FOR_SCIENTIFIC_QUALITY_AUDIT
SCIENTIFIC QUALITY: NOT_YET_AUDITED
GRU TRAINING: NOT_AUTHORIZED_TO_PROCEED
GRU TRAINING INVOCATIONS: 0
PREREQUISITE #9: NOT_YET_SATISFIED
H2: H2_NOT_SUPPORTED
FINAL TEST: SEALED
FINAL-TEST ACCESS: 0
FINAL-TEST AUTHORIZATION: NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-QUALITY-AUDIT-215 (STRICT_READ_ONLY_SCIENTIFIC_ARTIFACT_AUDIT)

