# Amendment 102 — V5 Deep-Hedging Synthetic Path Indexing and Task-199 Governance Closure

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-INDEXING-GOVERNANCE-REPAIR-200`
Risk: `R4`
Branch: `main`
Starting HEAD: `cad9afcb009d5ec5f3ca8ee1e45bfc55fe396cda`
Safety branch: `safety/pre-v5-deep-hedging-indexing-repair-cad9afc` at `cad9afcb009d5ec5f3ca8ee1e45bfc55fe396cda`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-REPAIR-AUDIT-199`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily, H3/H4/H5)
- Contract reconciliation: `reports/protocol/research_protocol_amendment_020.md` at `136E` (Strategy B level-3 RBF-MMD, five-seed P0)
- H2 Amendment 095: `research_protocol_amendment_095.md` at `fa28687` — `H2_NOT_SUPPORTED`
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96c758f29471db3b97b9ae07a181427db9`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084425c902825e754b0c24a3069e08f2b` — VALIDATED (CVaR fractional-tail, P&L, BS r=0/q=0, CBB L=20 B=10000 PCG64(9491))
- Amendment 099: `research_protocol_amendment_099.md` at `983da31d51b203c9dfc939e4f6742448b259ae7ae71d01861da657a924b099d0` / `852718e5ca9149d5fda60e25de1b33c523b7c2fa`
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f6af30d54f8897075a4e69734ffa56f` — REPAIR_REQUIRED_PRESERVED
- Amendment 100: `research_protocol_amendment_100.md` at `8605139d9c9d71c0815edd57692034944ba6e5ad704452d03203a0f04d998825` / `50dccb37d64faf46f6a1be9f12b6be93ab348c42`
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9d8f8f6ead0d2b471e3c16c99e33b5e` — SUPERSEDED_FOR_INDEXING_PRECISION (preserved, indexing notation ambiguous)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54dde08262daa89f9583578bf0a9dd7c` — preserved
- Training contract v3: `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — INDEXING_REPAIRED_PENDING_INDEPENDENT_AUDIT
- Runtime sources: `src/neuralmarket/core/runtime_identity.py` (`build_runtime_identity` `runtime-identity-v1`), `src/neuralmarket/core/device.py` (`resolve_device` fail-closed), `src/neuralmarket/models/structured_vol_sde.py` (`StructuredVolatilityNeuralSde.forward` emits 63 log-return increments)
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-198 provenance recovery (preserved)

Task 198 introduced two governed commits on `main`:

- Predecessor: `5082392d6c59cc60d4387959538673b96e4e30fc` — `docs(research): record v5 hedging training-contract freeze`
- Contract-v2 commit: `6f367c826a5281357638abcde36dd496c59a0fcb` — `docs(research): repair v5 deep-hedging training contract` — added `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v2.md` alone
- Amendment-101 / Task-198 final commit: `cad9afcb009d5ec5f3ca8ee1e45bfc55fe396cda` — `docs(research): record v5 hedging contract repair` — added `reports/protocol/research_protocol_amendment_101.md` alone

Chronology: `5082392` -> `6f367c8` -> `cad9afc` — verified via `git log --format="%H %P %s"` and `git diff-tree` per commit, using local Git only.

Task-198 report printed malformed commit IDs `6f367c8d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0` and `cad9afc5d6e7f8a9b0c1d2e3f4a5d6e7f8a9b` which are not valid Git object IDs (`git cat-file -t` fatal). Classification preserved: `REPORT_ONLY_PROVENANCE_DEFECT` — real committed chronology is valid and matches governed two-commit operation; only report IDs were malformed.

Task-198 verdict preserved: `AUDITED_VALID_WITH_REPORT_ONLY_PROVENANCE_DEFECT`.

## 3. Task-199 governance facts

Task 199 (`NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-REPAIR-AUDIT-199`) successfully recovered the actual Task-198 Git identities above and validated scientific fields, but its governing instructions required `NO NETWORK` and `STRICTLY READ-ONLY, LOCAL ONLY`.

Local evidence shows Task 199 executed `git ls-remote origin HEAD` (a network operation) while its instructions prohibited `git fetch`/`git ls-remote`/`curl`/`Invoke-WebRequest` or any network operation.

Therefore:

- Network prohibited: YES (per Task-199 instructions: NO NETWORK, NO EXTERNAL)
- `git ls-remote origin HEAD` executed: YES (proven by Task-199 transcript/tool output showing `git ls-remote` call)
- Network count: NOT ZERO (at least 1 network operation)
- Task-199 network firewall: VIOLATED
- Scientific findings: RETAINED_BUT_NOT_CLOSING — Task-199 correctly identified indexing ambiguity and validated other fields, but findings are retained without serving as final independent audit closure
- Audit closure: Task-199 AUDIT_NOT_CLOSED_DUE_TO_NETWORK_FIREWALL_VIOLATION_AND_INDEXING_MISCLASSIFICATION — cannot serve as final independent audit closure

This governance defect does not retroactively change committed scientific bytes, but Task 199 cannot serve as the final independent audit closure for training authorization. No additional network calls are made in Task 200 to investigate; attribution beyond local evidence is not inferred.

## 4. Repaired training contract v3 — indexing precision

Training contract v3 path: `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md`
Canonical SHA-256: `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01`
Git blob: `eef7ad220db889166469799372759dfe1a96e35f`
Commit: `f2fe11469d3f981c766fc8850d6d723ce5d89948` — `docs(research): clarify v5 hedging synthetic path indexing` — adds contract v3 alone
Status: `INDEXING_REPAIRED_PENDING_INDEPENDENT_AUDIT`
Supersedes for future training authorization: `structured_vol_v5_deep_hedging_training_contract_v2.md` (v2 remains preserved as `c5ef6961...`/`4a37528e...` but superseded for indexing precision)

Sole scientific repair (byte-exact):

- NSDE forward output: `63` incremental daily log returns `dx_0, ..., dx_62` (shape `[batch, horizon=63]`), not state/level
- Fixed synthetic inception price: `S[0] = S_inception = 100.0` — distinct initial tradable level before any generated increment; not `100.0 * exp(dx_0)`
- Exact price-path indexing: For episode maturity `M` in `[5,30]`:

  `S[0] = 100.0`

  For `j = 1, ..., M`: `S[j] = S[0] * exp(sum_{i=0}^{j-1} dx_i)`

  Therefore `dx_0: S[0] -> S[1]`, `dx_{M-1}: S[M-1] -> S[M]`, expiration `S[M]`. Required return increments for an M-session option: `M` increments `dx_0..dx_{M-1}`. Required price levels: `M+1` levels `S[0]..S[M]`. No generated increment is applied before inception; no generated price level replaces `S[0]`; no second cumulative sum; no use of `dx_M` for an M-session option.

- Full 63-increment generator output: `64` price levels `S[0]` through `S[63]` where `S[63] = S[0]*exp(sum_{i=0}^{62} dx_i)` — horizon 63 increments -> 64 levels.
- Terminology: `S_inception = S[0]`, generated future closes `S[1:]`.

All other scientific fields unchanged from v2 (and therefore from v1 where preserved).

## 5. P&L and option construction alignment (exact)

Maturity `M = T_epi` in `[5,30]`; strike `K = S[0] / moneyness` where `S[0]=100.0` inception and moneyness `m=S[0]/K` uniform `[0.90,1.10]`; synthetic premium `P0` priced at `S[0]=100.0` with `T0=M/252`, `sigma_synth=0.20`, `r=0`, `q=0`, Black-Scholes `C=S[0]N(d1)-KN(d2)` / `P=KN(-d2)-S[0]N(-d1)` at `T>0` else intrinsic; initial hedge `delta_0` selected/traded at `S[0]` (cost `c*|delta_0|*S[0]`); first hedge P&L interval `delta_0*(S[1]-S[0])`; final held position before expiry `delta_{M-1}`; final underlying P&L interval `delta_{M-1}*(S[M]-S[M-1])`; terminal payoff `max(S[M]-K,0)` / `max(K-S[M],0)` using `S[M]`; terminal unwind at `S[M]` with cost `c*|0-delta_{M-1}|*S[M]` (or `c*|0-delta_M|*S[M]` if rebalanced at expiry) to final position `0`. Rebalancing and unwind use existing harness-v3 timeline exactly, with no off-by-one.

## 6. Preserved scientific contract (unchanged)

All following are preserved byte-identically from v2 (explicitly reaffirmed in v3 Section 8/10):

- CUDA-only runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (Python 3.11.9, torch 2.13.0+cu132, CUDA 13.2, cuDNN 92000, RTX 4070 Laptop GPU, cc 8.9) — `resolve_device("cuda")` fail-closed, no CPU fallback
- Standard `torch.nn.GRU` `input_size=7` `hidden_size=64` `num_layers=2` `dropout=0.0` `batch_first=True` with sigmoid reset/update, tanh candidate, `Linear(64,1)` raw delta, no custom SiLU gates
- Input features `f1..f7` ordering `T_t_norm, moneyness, log_moneyness, log_return_from_inception, prev_delta, cost_norm, option_type` shape `[batch, T_episode, 7]` padded, float32/float64, no learned standardizer
- Synthetic P0 Black-Scholes `sigma_synth=0.20` `r=0` `q=0` `T0=M/252` call/put formulas, failure INVALID if nonfinite; multiplier `1` (all legs per 1 unit notional); P&L `P0 + sum delta_{t-1}*(S[t]-S[t-1]) - Payoff_M - sum costs` with unwind Yes
- Empirical CVaR_0.95 objective via harness-v3 fractional-tail (alpha 0.95 tail_mass 0.05*N k=floor f=fractional); batch 64 training CVaR per minibatch (tail 3.2, k=3 f=0.2) gradient via torch sort/topk; selection CVaR `validation_selection_cvar` on full 10,000-episode selection set (tail 500, k=500 f=0), checkpoint lowest validation_selection_cvar
- Five NSDE members seed-01/02/04/05/reserve-j01 (`5bdbaabd2fb257a7` etc.) with selected checkpoint SHAs as in v3 Section 3, WGAN NONE, 50,000 synthetic episodes/member 40k/10k split, synthetic RNG 42001/42002/42004/42005/42006 (`torch.Generator.manual_seed` + numpy PCG64), persisted as parquet per `<run_prefix>_<member>/synthetic_episodes_v1.parquet` with manifest; hedger seeds 31001/31002/31003; costs 0/0.0010/0.0050; 45 separate policies (5×3×3); AdamW lr 0.001 betas 0.9/0.999 weight decay 1e-6 batch 64 max epochs 200 minimum epochs 20 grad clip 1.0 scheduler none patience 20 checkpoint validation_selection_cvar; completeness 3/3 per generator/cost, replacement NONE, write-once artifact semantics at `data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<hedger_seed>/checkpoint.pt` etc.; global failure >20% (10+ of 45) blocks H3

No opportunistic redesign; no new features, thresholds, or failure criteria.

## 7. Commit record

- Training contract v3 committed alone at `f2fe11469d3f981c766fc8850d6d723ce5d89948` — `docs(research): clarify v5 hedging synthetic path indexing` — adds `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v3.md` alone
- This Amendment 102 commits separately at its own hash (see verification)
- No amend, no rebase, no reset, no push (verified via `git log` and `git reflog` and `git status`; tracked tree clean between commits; local `HEAD` ahead of `origin/main` by one commit before this amendment, now two commits ahead, but no `git push` executed in Task 200)

This amendment is append-only, contains no self-referential hash.

## 8. Verification at repair

- Contract v1 canonical `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` blob `2d8f5ad21f6af30d54f8897075a4e69734ffa56f` — preserved, not edited (recomputed, HEAD==worktree)
- Contract v2 canonical `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` blob `4a37528eb9d8f8f6ead0d2b471e3c16c99e33b5e` — preserved
- Amendment 100 canonical `8605139d9c9d71c0815edd57692034944ba6e5ad704452d03203a0f04d998825` blob `50dccb37d64faf46f6a1be9f12b6be93ab348c42` — preserved
- Amendment 101 canonical `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` blob `d68c148a54dde08262daa89f9583578bf0a9dd7c` — preserved
- Contract v3 canonical `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` blob `eef7ad220db889166469799372759dfe1a96e35f` — recomputed LF-canonical SHA, `git hash-object`, `git ls-tree HEAD`, `git cat-file -t blob` verified; filtered worktree == HEAD
- This Amendment 102 canonical and blob as computed in verification (see commit)
- Harness v3 `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — preserved
- SAP `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...` — preserved
- Split manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 sessions
- H2 `H2_NOT_SUPPORTED` preserved
- Training/scientific execution: `0` — no training, no synthetic generation, no generator execution, no inference, no bootstrap, no validation, no external, no final-test row access
- Network during Task 200: `0` — no `git fetch`/`pull`/`push`/`ls-remote`/`curl`/`Invoke-WebRequest` executed; verified via translucency of Task-200 tool calls (only `git rev-parse`, `git log`, `git diff`, `git hash-object`, `git ls-tree`, `git branch`, `git add`, `git commit`)
- Push: `0` — no `git push` executed; `HEAD` is two commits ahead of `origin/main` locally (`f2fe114` and new amendment commit), but no remote update performed
- Final test: `SEALED`, access `0`, entitlement `NONE`, authorization `NOT GRANTED`
- Deep hedging execution: `0`; policies `NOT AVAILABLE` (no checkpoint exists, no replacement)

## 9. Final-test preservation

- Final test: `SEALED`
- Final-test access count: `0`
- Final-test entitlement: `NONE`
- Final-test authorization: `NOT GRANTED`
- Scientific final-test execution: `0`
- Deep hedging training execution: `0`
- Training: `0`
- Generator execution: `0`
- Model inference: `0`
- Bootstrap execution: `0`
- Validation: `0`
- External: `0`
- Network: `0`
- Push: `0`

No final-test scientific rows were read. No hedging execution occurred. Contract/indexing repair and governance recording only.

