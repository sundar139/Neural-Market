# Amendment 112 — V5 Deep-Hedging GRU Training Completion

Date: 2026-08-25
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-EXECUTION-216
Risk: R5
Type: SCIENTIFIC_EXECUTION
Branch: main
Starting HEAD: 8506ca2c49443759c4071dd4037531c05c0dc79f
Prerequisite: NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-QUALITY-AUDIT-215 — SYNTHETIC_QUALITY_AUDIT_VALIDATED

## 1. Authorization and implementation

Authorization: reports/protocol/hedging_execution_authorization_212.json at 69c534fedae0d3bf81ae55c00b50c737db4dfd6e — canonical 42eb310d28d628995319d9143ef1ec5c234429aedabc6d338f678f233df8c6a2 raw b61999e16e7f695cc94ada354f70af690d7d038930e1231d4d81a86c5212a724 blob f7d30259c7da43a631a1b30bea02d7490f0fa517
Implementation: 1e6af6e9bcd1150700f34f8e7e0c7f9d280a934b manifest e3e7b6192881a06c81893973ad9c40d981e11e240a4af450d9185e4fa78622f4 for 15 paths
Contract v3: 79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01 blob eef7ad220db889166469799372759dfe1a96e35f
Runtime: 17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada (torch 2.13.0+cu132 CUDA 13.2 cuDNN 92000 RTX 4070 Laptop 8.9 deterministic)
Synthetic provenance: Task-214 reconciled 50bfad97 af3b8475..., Task-215 validated 8506ca2... — 5 datasets validated for GRU training
Training ceiling: 45 — all consumed
Synthetic generation: CLOSED_NO_FURTHER_EXECUTION

## 2. Execution order

Frozen nested order (45 unique tuples):
Members: seed-01, seed-02, seed-04, seed-05, reserve-j01 (5)
Costs: 0.0, 0.001, 0.005 (3 per member)
Hedger seeds: 31001, 31002, 31003 (3 per member/cost)
Total 5×3×3=45 — exact ordering seed-01/0.0/31001 … reserve-j01/0.005/31003 as enumerated in evidence.
In-memory enumeration verified: count 45, unique 45.
Command shape (validated .venv-gpu): `.venv-gpu\Scripts\python.exe -m neuralmarket.cli.deep_hedging train-policy --execute --authorization reports/protocol/hedging_execution_authorization_212.json --member <M> --cost <C> --hedger-seed <S>`

## 3. Campaign result

Authorized ceiling: 45
Attempted: 45
Consumed: 45
Succeeded: 45
Failed: 0
Not attempted: 0
Retries: 0
Reruns: 0
Replacements: 0
Generation invocations Task-216: 0
Final-test access: 0
Network: 0
All 45 via hard production CLI, derived scientific parameters from frozen source/authorization only, fail-stop never triggered.

## 4. Per-policy operational evidence (summary)

All 45 policies: process exit 0, execution_started.json present, checkpoint.pt + checkpoint_final.pt present, training_curve.json (21 epochs, 0..20), training_report.json, training_exit_code 0, terminal_manifest status success. No missing artifact, no nonfinite, no overwrite.
Sample first/last as in evidence:
- 1 seed-01/0.0/31001 5bdbaabd2fb257a7 c0 h31001 checkpoint 932f66... best_epoch 0 cvar 13.617667 15:26:54Z-15:30:03Z success 21 epochs
- 45 reserve-j01/0.005/31003 38c5113b27568e14 c50 h31003 checkpoint d82aba... best 0 cvar 8.377729
Full 45 rows in evidence: reports/research/evidence/structured_vol_v5_deep_hedging_gru_training_execution_v1.json at ee7da9f canonical 1d739b3e3f951331f1c8cc060f677a3d71c24b0184ece0a28796365079b5025c raw af4a7a70... blob b200923949e126ddc9dac60a7fa889f3bc23e2ec — 45 records, H3 NOT_YET_ADJUDICATED.

## 5. Training science (frozen, unchanged)

GRU: 7 input features, 64 hidden, 2 layers, dropout 0, raw delta output, prev_delta[0]=0 prev_delta[t]=delta[t-1]; costs 0.0/0.001/0.005; hedger seeds 31001/31002/31003; batch 64; AdamW lr 0.001 betas 0.9/0.999 weight_decay 1e-6; grad clip 1.0; max 200 min 20 patience 20 scheduler none; objective empirical CVaR alpha 0.95 per frozen minibatch 64; selection metric one empirical CVaR over full 10000 selection universe; checkpoint strictly lower validation CVaR replaces best, tie earliest remains; replacement NONE; no source mutation.

## 6. Completeness

Per generator/cost 3/3 hedger seeds required — PENDING_INDEPENDENT_AUDIT for Task-217 to verify:
- seed-01 cost0 31001/31002/31003, cost10bp 3/3, cost50bp 3/3
- seed-02 cost0 3/3, cost10bp 3/3, cost50bp 3/3
- seed-04 cost0 3/3, cost10bp 3/3, cost50bp 3/3
- seed-05 cost0 3/3, cost10bp 3/3, cost50bp 3/3
- reserve-j01 cost0 3/3, cost10bp 3/3, cost50bp 3/3
15 cells ×3 =45, 0 incomplete, no existing policy marker before execution, 45 after — write-once respected.

## 7. What was not done

- No synthetic generation/regeneration/NSDE inference
- No real held-out hedging evaluation, no H3 adjudication, no BS comparator, no bootstrap CI
- No final-test access (0), no final marker/result, no external/network/push
- Generation remains CLOSED

## 8. Reconciled state

TASK-216: GRU_TRAINING_COMPLETE_PENDING_AUDIT
GRU TRAINING: 45_OF_45_EXECUTED_SUCCESSFULLY_PENDING_AUDIT
GRU TRAINING INVOCATIONS: 45
POLICY COMPLETENESS: PENDING_INDEPENDENT_AUDIT
PREREQUISITE #9: NOT_YET_SATISFIED
H3: NOT_YET_ADJUDICATED
H2: H2_NOT_SUPPORTED
SYNTHETIC GENERATION: CLOSED_NO_FURTHER_EXECUTION
FINAL TEST: SEALED 0 ACCESS NOT GRANTED
Next: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-AUDIT-217 (R4 STRICT_READ_ONLY_SCIENTIFIC_ARTIFACT_AUDIT)

