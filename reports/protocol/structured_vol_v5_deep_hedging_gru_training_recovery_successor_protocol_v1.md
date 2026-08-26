# V5 GRU Recovery Successor Protocol v1

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-PROTOCOL-DESIGN-257
Risk: R4
Type: PROTOCOL_DESIGN_ONLY
Branch: main
Starting HEAD: 4abfa98fedf364dff9d4e476db2db8efca3031ab
Predecessor: Task255/Task256 adjudicated incident
Authorized successor implementation: REPAIR_REQUIRED_BEFORE_FUTURE_RECOVERY (no execution authorization yet)

## 1. Scientific Basis and Contamination

- Task253: GOVERNANCE_INVALID_EXECUTION_RUNTIME_SOURCE_DRIFT — 2 durable consumed (1 governance-invalid terminal ordinal1 seed-01/0.0/31001, 1 governance-invalid nonterminal ordinal2), 43 not started, 0 valid policies (Task254 forensic validated)
- Task255: RECOVERY_V2_EXECUTION_INCIDENT_PROTOCOL_ADJUDICATION_VALIDATED — original campaign IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_CONTAMINATED_EXECUTION, Authorization251 CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY, recovery_v2 FORENSIC_READ_ONLY_NEVER_REUSE
- Task256: RECOVERY_V2_EXECUTION_INCIDENT_PROTOCOL_AUDIT_VALIDATED (Claude)
- Original campaign: PERMANENTLY_CLOSED — ORIGINAL_AUTHORIZATION251_CAMPAIGN_NOT_CONTINUABLE_FOR_SCIENCE, remaining 43 cannot satisfy 45-policy completeness
- Same-45 restart: SAME_45_TUPLE_RESTART_NOT_SCIENTIFICALLY_CLEAN — seed-01/0/31001 outcome (best_epoch 11, CVaR 2.3413521425265205, trajectory, checkpoint) is durably known and preserved; rerunning identical 45-tuple universe cannot be information-blind preregistered
- Successor admissibility: H3_SUCCESSOR_RECOVERY_CAMPAIGN_SCIENTIFICALLY_PERMISSIBLE_PENDING_PROTOCOL_DESIGN_AND_INDEPENDENT_AUDIT — H3 remains testable via fully disjoint successor with outcome-independent seeding, as adjudicated in Task255

This successor protocol exists only to restore a clean prospective GRU policy family after Task253 contamination.

## 2. Frozen H3 / SAP / Training Contract (Unchanged)

H3 preserved exactly (deep hedging on signature-score synthetic paths reduces cost-aware hedging risk on real held-out episodes):

- Comparator: GRU deep hedger vs Black-Scholes delta
- Primary endpoint: 95% CVaR of loss
- Delta_CVaR = (CVaR_Deep - CVaR_BS) / CVaR_BS, negative favors deep
- Success criteria preserved exactly: Delta_CVaR < 0, paired 95% CI excludes 0, relative improvement <= -0.05, holds at >=2 nonzero transaction-cost levels, no unacceptable average-loss pathology, no turnover/position pathology, not driven by one seed/period

WGAN retains no H3 role. Task253 metrics (best_epoch 11, CVaR 2.341..., trajectory, checkpoint) must NOT alter any threshold, comparator, endpoint, or analysis method.

Training contract v3 preserved exactly (same five datasets, costs, costs, GRU architecture):

- GRUHedger: input features 7, hidden 64, layers 2, dropout 0, Linear -> one raw delta
- AdamW: lr 1e-3, betas 0.9/0.999, weight decay 1e-6
- Batch 64, max epochs 200, min epochs 20, clip 1, patience 20, no scheduler
- Empirical CVaR alpha 0.95
- Selection: lowest finite full-selection CVaR, earliest tie
- Synthetic split: 40,000 train / 10,000 selection (from frozen 50k)
- Costs: 0.0, 0.001, 0.005
- No hyperparameter or selection-rule change may be justified by Task253 best_epoch/CVaR/trajectory/checkpoint/runtime duration

## 3. Frozen Datasets (Same Five, No Regeneration)

Exact frozen synthetic datasets (same as Task216/Task246, no regeneration, no subset selection based on Task253):

- seed-01: data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet sha256 cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287, manifest 772a0a18320ab524da031ecfe2af34442cf9ba3a42426140a3a8cc0db7122717
- seed-02: data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet sha256 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7
- seed-04: data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet sha256 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8
- seed-05: data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet sha256 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204
- reserve-j01: data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet sha256 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc

Each dataset: 50,000 episodes, 10,000 selection held-out for validation-selection, not real held-out.

## 4. Successor Namespace and Contamination Firewall

Exactly one new prospective namespace distinct from every historical policy root. It MUST NOT be:

- data/processed/research/hedging_policies
- data/processed/research/hedging_policies_recovery_v1
- data/processed/research/hedging_policies_recovery_v2 (now FORENSIC_READ_ONLY_NEVER_REUSE)

Frozen successor namespace (boring explicit versioned v3):

- SUCCESSOR_ROOT: data/processed/research/hedging_policies_recovery_v3

No root creation in Task257 (directory not created).

Firewall (applies to all successor code/execution):

- recovery_v2: FORENSIC_READ_ONLY_NEVER_REUSE
- Successor must never read checkpoint.pt from recovery_v2
- Must never read checkpoint_final.pt from recovery_v2
- Must never warm-start from recovery_v2
- Must never load Task253 model parameters
- Must never use Task253 training_curve.json, training_stdout.log, CVaR/best_epoch, trajectory, or runtime duration for selection/design
- Must never compare candidate successor runs against Task253 model performance during training/design
- Task253 artifacts remain forensic evidence only, never imported as predecessors (Task216 predecessors remain the historical evidence unless protocol proves different binding necessary)

Zero recovery_v2 paths in successor ledger.

## 5. One-Shot Outcome-Independent Hedger-Seed Derivation Rule (Load-Bearing)

Successor must use a COMPLETELY DISJOINT hedger-seed universe from old seeds 31001, 31002, 31003. Disjointness applies globally across entire successor campaign, not merely to contaminated tuple.

Do not hand-pick successor seeds.

Exactly ONE deterministic derivation rule whose inputs are only immutable PRE-TASK253 identities. Allowed inputs (deterministic canonical encodings):

- training contract v3 canonical hash: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01
- SAP canonical hash: 76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa
- Task222 recovery protocol canonical hash: 4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8
- Task246 prerequisite canonical hash: c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0
- Five frozen dataset SHAs (sorted lexicographically, pipe-joined): 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7|60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8|60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc|8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204|cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287
- Fixed literal successor-campaign domain-separation string: neuralmarket-v5-gru-recovery-successor-v1

Prohibited inputs: Task253 artifact hashes, CVaR, best epoch, checkpoints, trajectory, timestamps, runtime duration, Task254/255/256 classifications except as justification that successor is needed, wall-clock time, random OS entropy.

Derivation must be deterministic and reproducible using standard-library SHA256 or already-existing repo-native deterministic helper. Prefer minimum boring implementation.

Frozen algorithm (write-once, before seed values):

- Domain separator: neuralmarket-v5-gru-recovery-successor-v1
- Base canonical: "{domain}|{contract_canonical}|{sap_canonical}|{recovery_protocol_canonical}|{prereq_canonical}|{sorted_dataset_concat}" where sorted_dataset_concat is pipe-joined sorted dataset SHAs as above
- For ordinal i in [0,1,2] (for three successor seeds in derivation order):
  - Input: "{base}|{i}"
  - Hash: SHA256(input) hex digest (lowercase)
  - Extraction: take first 8 hex characters, interpret as 32-bit unsigned integer, compute seed = 40000 + (int(hash[:8],16) % 50000) → range 40000-89999 inclusive, positive bounded integer compatible with torch/manual_seed
  - Bounds: 40000-89999 ensures disjointness from old 31001-31003 and fits torch seed handling
  - Collision handling (deterministic, defined prospectively): if derived seed equals any old seed (31001/31002/31003) or duplicates an already derived successor seed, then increment counter c=1,2,... and rehash input "{base}|{i}|{c}" until unique and disjoint; record final c if used
  - Record input and hash for each i for independent reproduction

This rule produces exactly THREE globally new hedger seeds (one per i), in deterministic derivation order i=0,1,2.

## 6. Anti-Rule-Shopping / Write-Once Seed Governance

Frozen exactly:

- SEED_DERIVATION_RULE_COUNT: 1
- DERIVATION_RULE_REVISION: PROHIBITED_AFTER_FREEZE
- ALTERNATIVE_RULE_EVALUATION: PROHIBITED
- SEED_SHOPPING: PROHIBITED

Do not generate candidate seeds from multiple algorithms and choose attractive ones. Do not alter encoding, hash function, truncation, modulus, collision handling, or domain separator after inspecting resulting seed values.

The protocol artifact specifies the rule BEFORE recording derived seed values (Section 5 before Section 7).

For collision handling, deterministic rule prospectively defined above (counter/domain-separated rehash) before computing any seed.

Compute three values once using frozen algorithm. Record all intermediate canonical input identities needed for independent reproduction (contract, SAP, recovery protocol, prereq, dataset SHAs, base, per-i inputs/hashes).

No later seed change based on training result is permitted.

## 7. Derived Successor Hedger Seeds (Frozen)

Computed once via frozen algorithm (no collision, no rehash needed):

- Derived seed 0: 60999 (input: neuralmarket-v5-gru-recovery-successor-v1|79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01|76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa|4bf228ad508da7a71a07d659d383a5601e0a50540bea248dfccbfbeda9ce6be8|c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0|20a0390f...|cda728...|0 → hash c4a61e07bd31..., seed 60999)
- Derived seed 1: 53804 (input base|1 → hash 72f5d64c7e87..., seed 53804)
- Derived seed 2: 89356 (input base|2 → hash 29d0cb2c350a..., seed 89356)

Verification:

- Three unique values: true
- None equal 31001/31002/31003: true (60999,53804,89356 ≠ old)
- Global disjointness: true
- Positive bounded: true (40000-89999)
- Reproducibility: deterministic SHA256 of canonical inputs as frozen

Intermediates recorded for independent reproduction (contract, SAP, recovery protocol, prereq, sorted dataset SHAs, base, per-i hash).

## 8. Complete Successor 45-Tuple Prospective Ledger

Using:

- Five frozen members: seed-01, seed-02, seed-04, seed-05, reserve-j01
- Three frozen costs: 0.0 (bps 0), 0.001 (bps 10), 0.005 (bps 50)
- Three newly derived globally disjoint hedger seeds in derivation order: 60999, 53804, 89356

Construct exactly 5×3×3 = 45 prospective successor tuples.

Deterministic ordering (members → costs → successor seeds in derivation order):

Members: seed-01, seed-02, seed-04, seed-05, reserve-j01
Costs: 0.0, 0.001, 0.005
Successor seeds: 60999, 53804, 89356 (i=0,1,2)

Prospective ledger (45 rows, ordinal 1..45):

| ordinal | member | run_prefix | cost | cost_bps | hedger_seed | dataset_path | dataset_sha256 | expected_successor_artifact_path |
|---|---|---|---|---|---|---|---|
| 01 | seed-01 | 5bdbaabd2fb257a7 | 0.0 | 0 | 60999 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_0/h_60999 |
| 02 | seed-01 | 5bdbaabd2fb257a7 | 0.0 | 0 | 53804 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_0/h_53804 |
| 03 | seed-01 | 5bdbaabd2fb257a7 | 0.0 | 0 | 89356 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_0/h_89356 |
| 04 | seed-01 | 5bdbaabd2fb257a7 | 0.001 | 10 | 60999 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_10/h_60999 |
| 05 | seed-01 | 5bdbaabd2fb257a7 | 0.001 | 10 | 53804 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_10/h_53804 |
| 06 | seed-01 | 5bdbaabd2fb257a7 | 0.001 | 10 | 89356 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_10/h_89356 |
| 07 | seed-01 | 5bdbaabd2fb257a7 | 0.005 | 50 | 60999 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_50/h_60999 |
| 08 | seed-01 | 5bdbaabd2fb257a7 | 0.005 | 50 | 53804 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_50/h_53804 |
| 09 | seed-01 | 5bdbaabd2fb257a7 | 0.005 | 50 | 89356 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | data/processed/research/hedging_policies_recovery_v3/5bdbaabd2fb257a7_seed-01/c_50/h_89356 |
| 10 | seed-02 | 62c7406cb3a2c642 | 0.0 | 0 | 60999 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_0/h_60999 |
| 11 | seed-02 | 62c7406cb3a2c642 | 0.0 | 0 | 53804 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_0/h_53804 |
| 12 | seed-02 | 62c7406cb3a2c642 | 0.0 | 0 | 89356 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_0/h_89356 |
| 13 | seed-02 | 62c7406cb3a2c642 | 0.001 | 10 | 60999 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_10/h_60999 |
| 14 | seed-02 | 62c7406cb3a2c642 | 0.001 | 10 | 53804 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_10/h_53804 |
| 15 | seed-02 | 62c7406cb3a2c642 | 0.001 | 10 | 89356 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_10/h_89356 |
| 16 | seed-02 | 62c7406cb3a2c642 | 0.005 | 50 | 60999 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_50/h_60999 |
| 17 | seed-02 | 62c7406cb3a2c642 | 0.005 | 50 | 53804 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_50/h_53804 |
| 18 | seed-02 | 62c7406cb3a2c642 | 0.005 | 50 | 89356 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | data/processed/research/hedging_policies_recovery_v3/62c7406cb3a2c642_seed-02/c_50/h_89356 |
| 19 | seed-04 | 77e7de9efabb7ce3 | 0.0 | 0 | 60999 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_0/h_60999 |
| 20 | seed-04 | 77e7de9efabb7ce3 | 0.0 | 0 | 53804 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_0/h_53804 |
| 21 | seed-04 | 77e7de9efabb7ce3 | 0.0 | 0 | 89356 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_0/h_89356 |
| 22 | seed-04 | 77e7de9efabb7ce3 | 0.001 | 10 | 60999 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_10/h_60999 |
| 23 | seed-04 | 77e7de9efabb7ce3 | 0.001 | 10 | 53804 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_10/h_53804 |
| 24 | seed-04 | 77e7de9efabb7ce3 | 0.001 | 10 | 89356 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_10/h_89356 |
| 25 | seed-04 | 77e7de9efabb7ce3 | 0.005 | 50 | 60999 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_50/h_60999 |
| 26 | seed-04 | 77e7de9efabb7ce3 | 0.005 | 50 | 53804 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_50/h_53804 |
| 27 | seed-04 | 77e7de9efabb7ce3 | 0.005 | 50 | 89356 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | data/processed/research/hedging_policies_recovery_v3/77e7de9efabb7ce3_seed-04/c_50/h_89356 |
| 28 | seed-05 | 1e8aa171993a1aba | 0.0 | 0 | 60999 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_0/h_60999 |
| 29 | seed-05 | 1e8aa171993a1aba | 0.0 | 0 | 53804 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_0/h_53804 |
| 30 | seed-05 | 1e8aa171993a1aba | 0.0 | 0 | 89356 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_0/h_89356 |
| 31 | seed-05 | 1e8aa171993a1aba | 0.001 | 10 | 60999 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_10/h_60999 |
| 32 | seed-05 | 1e8aa171993a1aba | 0.001 | 10 | 53804 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_10/h_53804 |
| 33 | seed-05 | 1e8aa171993a1aba | 0.001 | 10 | 89356 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_10/h_89356 |
| 34 | seed-05 | 1e8aa171993a1aba | 0.005 | 50 | 60999 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_50/h_60999 |
| 35 | seed-05 | 1e8aa171993a1aba | 0.005 | 50 | 53804 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_50/h_53804 |
| 36 | seed-05 | 1e8aa171993a1aba | 0.005 | 50 | 89356 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | data/processed/research/hedging_policies_recovery_v3/1e8aa171993a1aba_seed-05/c_50/h_89356 |
| 37 | reserve-j01 | 38c5113b27568e14 | 0.0 | 0 | 60999 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_0/h_60999 |
| 38 | reserve-j01 | 38c5113b27568e14 | 0.0 | 0 | 53804 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_0/h_53804 |
| 39 | reserve-j01 | 38c5113b27568e14 | 0.0 | 0 | 89356 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_0/h_89356 |
| 40 | reserve-j01 | 38c5113b27568e14 | 0.001 | 10 | 60999 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_10/h_60999 |
| 41 | reserve-j01 | 38c5113b27568e14 | 0.001 | 10 | 53804 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_10/h_53804 |
| 42 | reserve-j01 | 38c5113b27568e14 | 0.001 | 10 | 89356 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_10/h_89356 |
| 43 | reserve-j01 | 38c5113b27568e14 | 0.005 | 50 | 60999 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_50/h_60999 |
| 44 | reserve-j01 | 38c5113b27568e14 | 0.005 | 50 | 53804 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_50/h_53804 |
| 45 | reserve-j01 | 38c5113b27568e14 | 0.005 | 50 | 89356 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | data/processed/research/hedging_policies_recovery_v3/38c5113b27568e14_reserve-j01/c_50/h_89356 |

Verification: 45 exact, 45 unique tuple keys (member+cost+hedger_seed), 45 unique artifact paths, zero recovery_v2 paths, zero historical policy paths. Task216 predecessor identities remain historical predecessor evidence (no Task253 ordinal import).

## 9. Successor Execution Authority Limits (Frozen Before Any Implementation/Authorization)

- Training ceiling: 45
- Prospective consumed: 0
- Prospective remaining: 45
- Generation: 0
- Retry: 0
- Rerun: 0
- Replacement: 0
- Network: false
- Final_test_access: false
- One invocation per tuple
- Stop entire successor campaign on first: failure, nonterminal interruption, ambiguity, provenance mismatch, runtime mismatch, source mismatch, artifact collision
- No retry, no rerun, no replacement, no deletion, no rm-rf, no continuation after first failed/nonterminal tuple until independent adjudication
- SUCCESSOR_CAMPAIGN_REEXECUTION_AFTER_RESULT: PROHIBITED (one-shot prospective, no resumability; operational scheduling may be designed later without weakening scientific one-shot semantics)

## 10. Source State

- Defect: trainer.py ~1160 authorized_commit typo (as adjudicated in Task255)
- Repair required: YES
- Repaired in Task257: NO (protocol design only, no source repair)
- Authorization: NONE_VALID_FOR_SUCCESSOR_EXECUTION (no successor authorization created in Task257)
- Relationship to successor protocol: separate gates — source repair is prerequisite for any future successor execution but does not confer successor scientific authority; successor protocol does not imply source correctness

## 11. Execution Authority

- Execution authority NOT_GRANTED in Task257
- Authorization NOT_CREATED in Task257
- Any future successor execution requires: source repair, new implementation commit/manifest, new authorization binding successor namespace + derived seeds + 45 ledger, independent audit
- Prerequisite #9 remains NOT_SATISFIED, H3 NOT_YET_ADJUDICATED, H2_NOT_SUPPORTED, FINAL SEALED

Protocol frozen without source mutation, authorization creation, recovery execution, synthetic generation, held-out, H3, or final-test activity. Successor root not created.

