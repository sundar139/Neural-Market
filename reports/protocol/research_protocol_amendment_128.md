# Amendment 128 — Corrected V5 GRU Recovery Successor Seed Supersession

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-AUTHORIZATION-PREREQUISITES-SUPERSESSION-REPAIR-264
Risk: R4
Type: AUTHORIZATION_PREREQUISITE_REPAIR_ONLY
Branch: main
Starting HEAD: a4c22896142eecca651c724a3f8f959598aba184
Corrected prerequisite: reports/protocol/hedging_recovery_successor_authorization_prerequisites_264.json
Corrected prerequisite commit: 0d4489fe1880a4cfed9752bf3cc32aa19953adae
Corrected prerequisite canonical: fe5983662d4e8b1269c6d305a5a2741c7c171e38c4e92f9bf8c8e8e77b491496
Corrected prerequisite raw: 55675fbb78c1e20df1a130aa23ab9cb31bb4683bb40d8fd7fa82bc74719e14b7
Corrected prerequisite blob: 24cfc59af40a80f51f5e3d4bc2b3297607f754d4
Superseded prerequisite: reports/protocol/hedging_recovery_successor_authorization_prerequisites_262.json (90ff008925eef4819934b9d3f8bb999974e9d270 / e2e121f6b62e424ccc95f501180595e642d14d71915939cc86fb5a51bfe2c74f / 5c7ab59b6e666eb38c5559be8030724a43418ee8) — FROZEN_INCOMPLETE_SEED_SUPERSESSION_NO_EXECUTION_AUTHORITY
Superseded Amendment127: reports/protocol/research_protocol_amendment_127.md (a4c22896142eecca651c724a3f8f959598aba184 / 088a7c85c1379d61279dc189f8b307ad14a4d44d0b511d777f18b58b0732f4bf) — INCOMPLETE_AND_SUPERSEDED_BY_AMENDMENT128
Training contract: reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md (79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 / eef7ad220db889166469799372759dfe1a96e35f)
Successor protocol: reports/protocol/structured_vol_v5_deep_hedging_gru_training_recovery_successor_protocol_v1.md (c63df0ebdd589a1f7ecc1bcb312bc3d18baba7f0 / 922b4760a7b71a153289ef9b1ff05417045903c3a8070119f8ee6881f0ade418)
Implementation: d762e5a18a1552d34fce79ea5d765a66c042d9c1 / 9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a (runner 5fac8765..., trainer a9bfcb6a..., CLI 86b9468f...)
Task263: RECOVERY_SUCCESSOR_AUTHORIZATION_PREREQUISITES_AUDIT_REPAIR_REQUIRED (Claude)

## 1. Correction of Amendment127

Amendment127 remains historical append-only evidence and is not edited.

Its statements:

- "Additional seed clauses: none load-bearing"

and

- "Supersession ... (2 clauses)" / "superseded_clauses": 2

are:

INCOMPLETE_AND_SUPERSEDED_BY_AMENDMENT128.

Task263 independently identified FIVE load-bearing hedger-seed clauses in contract v3, not two. The two missing clauses are required for successor primary/confirmatory H3 and 3/3 completeness semantics.

This amendment corrects the supersession scope without mutating the frozen training contract, successor protocol, or the historical 262/127 artifacts.

## 2. Complete Contract Search and Classification

Machine search of structured_vol_v5_deep_hedging_training_contract_v3.md (canonical 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01, blob eef7ad220db889166469799372759dfe1a96e35f, raw d3e30e2cfa897d5b2c436d9c0a932b06fc862370c73ffbc3f80dcaf862c144dd) for 31001/31002/31003, hedger seed(s), preregistered hedger, valid hedger, policy count, SOURCE_FROZEN yields:

- Clause A — Line ~49: SOURCE_FROZEN historical hedger seed family 31001/31002/31003. Text: "Hedger seeds 31001-31003 | SOURCE_FROZEN (harness v3 Section 7.3) | preserved 31001,31002,31003" — LOAD_BEARING
- Clause B — Line ~198: Expected 45-policy count defined using 31001/31002/31003. Text: "Expected trained policy count: 45 = 5 generator members × 3 hedger seeds (31001,31002,31003) × 3 cost levels (0, 0.0010, 0.0050)" — LOAD_BEARING
- Clause C — Section 7.1 / lines ~302-310: Normative exact hedger-seed definition for GRU weight initialization, optimizer state and training shuffle. Text: "Exact hedger seeds (integer seeds for GRU weight init, optimizer state, and training shuffle, distinct from all other RNGs): 31001, 31002, 31003. These are the three preregistered hedger seeds. No other hedger seeds are used for primary H3." — LOAD_BEARING
- Clause D — Line ~346: ALL THREE preregistered hedger seeds require valid selected checkpoints; valid hedger count = 3/3 per generator/cost stratum. Text: "ALL THREE preregistered hedger seeds must have valid selected checkpoints: valid hedger count per generator per required cost level = 3/3" — LOAD_BEARING
- Clause E — Line ~362: No reserve hedger seeds are defined for hedging and 31001-31003 are the only valid hedger seeds for confirmatory H3. Text: "Therefore no reserve hedger seeds are defined for hedging; the three preregistered seeds 31001-31003 are the only valid hedger seeds for confirmatory H3." — LOAD_BEARING

Other occurrences:

- Line ~284: "Distinct from NSDE model seeds (8281 series, 9281, etc.), Gate seeds (7777/7778/8801), evaluation seed 8283, and hedger initialization seeds (31001-31003)." — OTHER_SEED_FAMILY / RNG namespace disambiguation, NOT load-bearing for successor hedger-seed validity
- Line ~392: "Report path: training_report.json contains ... hedger_seed (31001 etc.)" — EXAMPLE_ONLY / report-schema example, NOT normative

No additional load-bearing old-seed enumerations exist beyond these five.

## 3. Corrected Successor-Only Supersession (Five Clauses)

Training contract v3 remains UNCHANGED_FROZEN (79611b6b... / eef7ad...), scientific parameters FULLY_PRESERVED. Historical family 31001/31002/31003 is SUPERSEDED_FOR_SUCCESSOR_CAMPAIGN_ONLY by successor family 60999/53804/89356 (TASK257_WRITE_ONCE_OUTCOME_INDEPENDENT_DERIVATION, TASK258_VALIDATED).

Applied explicitly to every load-bearing clause:

- Clause A successor semantics: Historical family remains evidence but is not successor family; successor seeds are 60999/53804/89356.
- Clause B successor semantics: Successor expected policy count remains exactly 5 members × 3 successor hedger seeds (60999,53804,89356) × 3 costs = 45.
- Clause C successor semantics: For successor execution, exact GRU initialization/optimizer/shuffle seeds are 60999/53804/89356; no other successor seeds are used for primary H3.
- Clause D successor semantics: For successor completeness, ALL THREE successor seeds must produce valid selected checkpoints per required member/cost stratum: successor valid hedger count = 3/3.
- Clause E successor semantics: For successor confirmatory H3, the only valid hedger seeds are 60999/53804/89356; no reserve successor hedger seeds exist.

Other-seed-family (284) and example-only (392) are classified as above, not superseded.

Not superseded: architecture, features, readout, P&L, CVaR, AdamW, lr, betas, weight decay, batch, epochs, clip, patience, scheduler, selection rule, datasets, 40k/10k split, costs, H3 endpoint/comparator/statistical criteria. No Task253 outcome adaptation.

## 4. Corrected Prerequisite Artifact

- Path: reports/protocol/hedging_recovery_successor_authorization_prerequisites_264.json
- Type: GRU_TRAINING_RECOVERY_SUCCESSOR_AUTHORIZATION_PREREQUISITES_V2
- Supersedes: reports/protocol/hedging_recovery_successor_authorization_prerequisites_262.json (90ff008925eef4819934b9d3f8bb999974e9d270 / e2e121f6b62e424ccc95f501180595e642d14d71915939cc86fb5a51bfe2c74f / 5c7ab59b6e666eb38c5559be8030724a43418ee8) — superseded status INCOMPLETE_SEED_SUPERSESSION_NO_EXECUTION_AUTHORITY (preserved as historical no-authority)
- Commit: 0d4489fe1880a4cfed9752bf3cc32aa19953adae
- Canonical: fe5983662d4e8b1269c6d305a5a2741c7c171e38c4e92f9bf8c8e8e77b491496
- Raw: 55675fbb78c1e20df1a130aa23ab9cb31bb4683bb40d8fd7fa82bc74719e14b7
- Blob: 24cfc59af40a80f51f5e3d4bc2b3297607f754d4
- Implementation: d762e5a18a1552d34fce79ea5d765a66c042d9c1 / 9e1b1a6c0f1e8fc1f226ccbace3cad2c019c432b900c9419eedf8ddeb9b7711a
- Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada
- Datasets: same 5 frozen (cda728...,20a039...,60777e...,8023c9...,607875...)
- Root: data/processed/research/hedging_policies_recovery_v3 (not created)
- Seeds: 60999,53804,89356 (globally disjoint)
- Tuples: 45 exact Task257 successor tuples (5×3×3, 45 unique keys, 45 unique successor paths, 0 recovery_v2)
- Predecessors: 45 Task216 historical predecessor identities (0 Task253 imports)
- Authority: ceiling45 consumed0 remaining45 generation0 retry0 rerun0 replacement0 network false final false, reexecution PROHIBITED, execution authority NOT_GRANTED, authorization NOT_CREATED

## 5. Consistency Verification

- Under combined frozen-contract + successor-prerequisite semantics, no remaining contract sentence reasonably implies 60999/53804/89356 are invalid for successor primary/confirmatory H3 (all five load-bearing historical clauses now explicitly superseded for successor).
- Successor completeness remains 3/3 successor hedger seeds per required member/cost stratum, 45 total prospective policies.
- No old seed 31001/31002/31003 appears as authorized successor hedger seed (historical references remain labeled historical/superseded).
- Successor valid seeds 60999/53804/89356 are the only valid hedger seeds for successor H3.

## 6. Current Authority

- Task262 prerequisite: FROZEN_INCOMPLETE_SEED_SUPERSESSION_NO_EXECUTION_AUTHORITY (historical, no authority)
- Corrected prerequisite 264: V2_FROZEN_NO_EXECUTION_AUTHORITY_PENDING_AUDIT (0d4489f / fe5983...)
- Training contract v3: UNCHANGED_FROZEN
- Old seed enumeration: COMPLETE_SUCCESSOR_ONLY_SUPERSESSION_PENDING_AUDIT (5 clauses)
- Successor protocol: c63df0e/922b47... (unchanged)
- Successor seeds: 60999/53804/89356
- Successor tuples: 45
- Recovery_v3: FROZEN_NOT_CREATED
- Recovery authorization: NONE_VALID_FOR_SUCCESSOR_EXECUTION
- Task253 forensic: unchanged (1 terminal +1 nonterminal, 43 not started, 0 valid)
- Prerequisite9: NOT_SATISFIED_PENDING_INDEPENDENT_PREREQUISITE_REPAIR_AUDIT
- H3: NOT_YET_ADJUDICATED
- H2: H2_NOT_SUPPORTED
- Final: SEALED, access 0
