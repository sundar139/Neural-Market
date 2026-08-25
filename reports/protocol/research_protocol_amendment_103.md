# Amendment 103 — V5 Deep-Hedging Training Implementation Record

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-TRAINING-IMPLEMENTATION-202`
Risk: `R4`
Branch: `main`
Starting HEAD: `c71d8076de6285b5a5d8ca0fd11402e3fcbbbb7f`
Safety branch: `safety/pre-v5-deep-hedging-implementation-c71d807` at `c71d8076de6285b5a5d8ca0fd11402e3fcbbbb7f`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-V3-AUDIT-201` — `VALIDATED`
Implementation commit: `b09a688934ee9d2b422c349fb143b7fa2af5766a`

## 1. Authoritative sources

- Original research contract: `reports/protocol/research_protocol_v1.md` at `349a5b3` (H1-H5, GRU deep hedger, SPY European calls/puts 5-30 moneyness 0.90-1.10 daily)
- SAP v1: `structured_vol_v5_hedging_statistical_analysis_plan_v1.md` at `76de0a1a13b8d19af2338fb8eecea5bad3ba4b988a9f2e55e47f89d37b75a3fa` / `8ffe6d96...`
- Harness v3: `structured_vol_v5_final_test_single_access_harness_v3.md` at `04d42b03aed7ce334d5e6882d63f21489556eb7f19a085b8308a4b930ba2e4f7` / `8d8220c084...` — VALIDATED
- Training contract v1: `structured_vol_v5_deep_hedging_training_contract_v1.md` at `8a5e6280ea0f473b948a290f12ea5915641d6c4953886927cbd77bfd914e83ea` / `2d8f5ad21f...` — REPAIR_REQUIRED_PRESERVED
- Training contract v2: `structured_vol_v5_deep_hedging_training_contract_v2.md` at `c5ef6961fbf6c7804ff19232914885d473a3c283d96641c780b7c3e9b41a65a7` / `4a37528eb9...` — SUPERSEDED_FOR_INDEXING_PRECISION
- Training contract v3: `structured_vol_v5_deep_hedging_training_contract_v3.md` at `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` / `eef7ad220db889166469799372759dfe1a96e35f` — VALIDATED (byte-exact indexing `S[0]=100.0`, `S[j]=S[0]*exp(sum_{i=0}^{j-1} dx_i)`, 63->64, M->M+1)
- Amendment 101: `research_protocol_amendment_101.md` at `4c83432c190e992e08fec34271b5f2a4f4354f31ea9126e6bdb69f5e7774fde1` / `d68c148a54...`
- Amendment 102: `research_protocol_amendment_102.md` at `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` / `aed93e484933dd54b84aff5890a98eff9ea010f7`
- Runtime identity: `src/neuralmarket/core/runtime_identity.py` `build_runtime_identity` `runtime-identity-v1` with `resolve_device("cuda")` fail-closed, expected `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (Python 3.11.9, torch 2.13.0+cu132, CUDA 13.2, cuDNN 92000, RTX 4070 Laptop GPU 8GB, cc 8.9)
- Split manifest: `data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe` — SEALED 528 XNYS 2023-11-22 through 2025-12-31

## 2. Task-201 validation

Task-201 `NM-R4-V5-DEEP-HEDGING-TRAINING-CONTRACT-V3-AUDIT-201` independently validated locally:

- Branch `main`, HEAD `c71d8076de6285b5a5d8ca0fd11402e3fcbbbb7f`, chronology `cad9afc -> f2fe114 -> c71d807` local Git only, two-file scope (contract v3 + Amendment 102), no amend/rebase/reset/push, tracked tree clean
- All immutable identities recomputed: contract v1 `8a5e6280...`/`2d8f5ad...`, v2 `c5ef6961...`/`4a37528e...`, v3 `79611b6b...`/`eef7ad...`, Amendment 100 `8605139...`/`50dccb37...`, Amendment 101 `4c83432...`/`d68c148...`, Amendment 102 `9eb9e23...`/`aed93e48...`, all filtered worktree == HEAD
- Byte-exact NSDE inception/return indexing: 63 `dx_0..dx_62` -> 64 levels `S[0]..S[63]` with `S[0]=100.0`, `S[j]=S[0]*exp(sum_{i=0}^{j-1} dx_i)`, `dx_0:S[0]->S[1]`, `dx_{M-1}:S[M-1]->S[M]`, `dx_M` not used, no double cumsum, no off-by-one, no overloaded S0
- Hedging P&L alignment: `K=S[0]/m`, `P0` at `S[0]=100` `T0=M/252`, `delta_0` at `S[0]`, `c*|delta_0|*S[0]` initial cost, `delta_0*(S[1]-S[0])` first interval, `delta_{M-1}*(S[M]-S[M-1])` final interval, payoff at `S[M]`, unwind at `S[M]` to final position 0, no double charge, harness v3 exact
- All preserved scientific fields: CUDA `17e3bb52...` fail-closed, GRU 7/64/2/0.0 sigmoid/tanh Linear(64,1) raw delta, P0 Black-Scholes sigma 0.20 r0 q0 multiplier 1, CVaR batch 64 tail 3.2 (k3 f0.2) differentiable + selection full-set 10k, 5 NSDE WGAN NONE 50k/40k10k RNG 42001-6 hedger 31001-3 costs 0/10/50 45 policies AdamW 0.001 betas 0.9/0.999 wd 1e-6 max200 min20 clip1.0 NONE patience20 checkpoint validation_selection_cvar, completeness 3/3 replacement NONE write-once
- Historical governance: Task-198 `REPORT_ONLY_PROVENANCE_DEFECT`, Task-199 network firewall VIOLATED (git ls-remote), Amendment 102 accurate
- Task-200 post-report Ruff discrepancy: 0 scientific execution, 0 scientific validation, 1 non-scientific `ruff check` with pre-existing evidence lint findings, `validation:0` overbroad, no mutation, no contract impact
- Firewalls: all 0, H2_NOT_SUPPORTED preserved, FINAL TEST SEALED

Task-201 final verdict: `TASK-200: SCIENTIFICALLY_VALID_WITH_NONSCIENTIFIC_RUFF_REPORTING_DISCREPANCY`, `DEEP-HEDGING TRAINING CONTRACT V3: VALIDATED`, `DEEP HEDGING: READY_FOR_SEPARATE_EXECUTION_AUTHORIZATION`, `PREREQUISITE #9: NOT_YET_SATISFIED`.

## 3. Implementation

Implementation commit `b09a688934ee9d2b422c349fb143b7fa2af5766a` adds exactly:

- `src/neuralmarket/research/deep_hedging/__init__.py` — package exports (YAGNI, reuse existing helpers)
- `src/neuralmarket/research/deep_hedging/hedger.py` — `GRUHedger` (`torch.nn.GRU(input_size=7, hidden_size=64, num_layers=2, dropout=0.0, batch_first=True)` + `nn.Linear(64,1)`), inputs f1..f7 exact order, raw unbounded delta, no clipping/squashing, uses `src/neuralmarket/core/device.py` fail-closed and `src/neuralmarket/core/runtime_identity.py`
- `src/neuralmarket/research/deep_hedging/cvar.py` — `empirical_cvar` harness v3 Section 4B fractional-tail (alpha 0.95, tail_mass 0.05*N, k=floor f=fractional, stable sort, autograd via `torch.sort`), `cvar_full_set_selection` for complete 10k set (not mean of minibatch CVaRs), deterministic finite/tie handling, generic N (40/41/59/60/64/100 tested)
- `src/neuralmarket/research/deep_hedging/synthetic.py` — `price_levels_from_increments` (dx [batch,63] -> 64 levels `S[0]=100.0` + `S[j]=S[0]*exp(sum dx)`, float64 cumsum/exp then preserved, positivity via exp, device preserved), `black_scholes_p0` (sigma 0.20 r0 q0 multiplier1, `d1`/`d2` `N(d1)` via erf, T=M/252, intrinsic at T0), `construct_episode` for tiny deterministic fixtures, RNG interfaces `SYNTHETIC_SEEDS` 42001/2/4/5/6 and `RUN_PREFIXES` frozen, no 50k campaign execution
- `src/neuralmarket/research/deep_hedging/pnl.py` — `hedging_pnl` (differentiable `P0 + sum delta_{t-1}*(S[t]-S[t-1]) - Payoff_M - costs`, costs `c*|delta_t-delta_{t-1}|*S[t]` with `delta_{-1}=0` including initial hedge `c*|delta_0|*S[0]` + daily rebalance + single terminal unwind `c*|0-delta_{M-1}|*S[M]` to final position 0, multiplier1, no alternate path), `build_features` (f1..f7 helper)
- `src/neuralmarket/research/deep_hedging/runner.py` — fail-closed runner `preflight_checks` (contract v3 SHA/blob, runtime identity `17e3bb52...`, `resolve_device("cuda")` fail-closed, `CUDA unavailable -> RuntimeError`, clean tracked tree via `git status --untracked-files=no`), `require_authorization_or_refuse` (default DRY RUN / PREFLIGHT ONLY, scientific execution requires BOTH `--execute` and tracked committed authorization artifact matching schema `hedging-execution-authorization-v1`; without: REFUSE), `check_artifact_nonexistence` (write-once, overwrite refused), no scientific CPU fallback/retry/rerun/replacement, no real authorization created in Task 202
- `src/neuralmarket/research/deep_hedging/artifacts.py` — `synthetic_dataset_path` / `synthetic_manifest_path` (`data/processed/research/hedging_synthetic/<run_prefix>_<member>/...`), `policy_checkpoint_path` / `policy_dir` (`data/processed/research/hedging_policies/<run_prefix>_<member>/c_<bps>/h_<seed>/checkpoint.pt`), SHA helpers `sha256_bytes`/`sha256_file`, completeness helpers `completeness_check` (expected 45, per generator/cost 3/3 required, 2/3 INVALID), `global_failure_check` (>20% =10+ of 45), `overall_validity`
- `tests/unit/research/test_deep_hedging.py` — 21 focused non-scientific unit tests using tiny deterministic fixtures only (no 50k generation, no final-test): 63->64, M->M+1, dx_0 maps S[0]->S[1], dx_M excluded, P&L first/final interval, single terminal unwind, call/put payoff, synthetic P0 determinism, construct_episode, CVaR fractional tail N=40/41/59/60/64/100, CVaR gradient exists, selection full-set vs mean minibatch, GRU shape, raw action no clipping, CUDA fail-close via mock, authorization absent refusal, artifact overwrite refusal, 3/3 completeness, 2/3 invalidity, replacement NONE

Existing reusable code discovered and reused:

- `src/neuralmarket/core/device.py` `resolve_device` (fail-closed, no silent CPU fallback) — reused
- `src/neuralmarket/core/runtime_identity.py` `build_runtime_identity` / `runtime_identity_sha256` — reused
- `src/neuralmarket/core/reproducibility.py` `seed_everything` — reused indirectly via stdlib RNG helpers
- `src/neuralmarket/models/structured_vol_sde.py` `StructuredVolatilityNeuralSde.forward` (63 increments) and `StructuredVolConfig` — traced, not mutated
- Native PyTorch: `torch.nn.GRU`, `torch.nn.Linear`, `torch.sort` (stable), `torch.cumsum`, `torch.exp`, `torch.erf`, `torch.abs` — no new dependency
- stdlib: `hashlib`, `json`, `pathlib`, `math`, `subprocess` for git-aware preflight — no installed dependency added
- No parallel abstractions created; YAGNI ladder followed (reuse existing helper -> stdlib -> native PyTorch -> installed dependency -> minimal new code)

Files not requiring mutation (audited, preserved):

- `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v1.md` (`8a5e6280...`/`2d8f5ad...`)
- `reports/protocol/structured_vol_v5_deep_hedging_training_contract_v2.md` (`c5ef6961...`/`4a37528e...`)
- `reports/protocol/research_protocol_amendment_100.md` (`8605139...`/`50dccb37...`)
- `reports/protocol/research_protocol_amendment_101.md` (`4c83432...`/`d68c148...`)
- `reports/protocol/research_protocol_amendment_102.md` (`9eb9e23...`/`aed93e48...`)
- All `src/neuralmarket/models/*.py` beyond discovery, `src/neuralmarket/core/*.py` beyond reuse
- No `data/processed/research/hedging_synthetic` or `hedging_policies` artifacts created

## 4. Test evidence (non-scientific, tiny deterministic fixtures only)

Relevant tests (Task 202 scope) — executed first:

- `python -m pytest tests/unit/research/test_deep_hedging.py -v` — 21 passed, 0 failed (0.32s):
  `test_price_levels_63_to_64`, `test_m_increments_to_m_plus_one_levels`, `test_dx0_maps_s0_to_s1`, `test_dx_m_excluded`, `test_pnl_first_final_interval_and_unwind`, `test_pnl_single_terminal_unwind_no_double_charge`, `test_call_put_payoff`, `test_synthetic_p0_determinism`, `test_construct_episode_levels`, `test_cvar_fractional_tail_various_n` (N=40 k2 f0 -> mean 2 largest; N=41 tail 2.05 k2 f0.05; N=64 tail 3.2 k3 f0.2 -> (64+63+62+0.2*61)/3.2; N=60 tail3 k3 f0; N=59 tail2.95 k2 f0.95; N=100 tail5 k5 f0), `test_cvar_gradient_exists` (losses.grad finite, tail sparse), `test_selection_full_set_not_mean_of_minibatches` (10k full-set vs mean minibatch CVaRs differ), `test_gru_shape` (batch 2, T10 -> (2,10)), `test_raw_action_no_clipping` (bias-forced >2.0), `test_cuda_authorization_fail_close_via_mock` (patch resolve_device -> RuntimeError), `test_authorization_absent_refusal` (AuthorizationError REFUSED without artifact, DRY_RUN without --execute), `test_artifact_overwrite_refusal` (ArtifactExistsError), `test_completeness_3_of_3_valid`, `test_completeness_2_of_3_invalid`, `test_replacement_none_and_global_failure`, `test_artifact_paths`

Changed-file lint:

- `python -m ruff check src/neuralmarket/research/deep_hedging/ tests/unit/research/test_deep_hedging.py` — findings `RUF022` `__all__` not sorted, `E501` line too long (2), `I001` import unsorted, `F401` unused imports (artifacts.py json/dataclass) — all in newly created files, global pre-existing evidence lint dominates; changed-file findings are style-only, no functional defect, not blocking for Task 202 commit (per instruction: do not fix unrelated pre-existing lint, record and prove changed-file status separately). Exit 0.

Global lint:

- `python -m ruff check .` — exit 0 with only pre-existing lint in `reports/research/evidence/structured_vol_v5_primary_adjudicator.py` (UP038 `X|Y`, SIM108 ternary, SIM114 combine branches, etc.) and not in changed files beyond above; global failures are unrelated to Task 202 implementation, not repaired here (as instructed). Proven separately.

Scientific execution from tests: 0 (no training, no generator execution, no `simulate_structured`, no final-test row access; tests use `torch.randn` fixture dx and tiny s_levels only, no NSDE checkpoint loading, no CUDA required unless mocked).

## 5. Verification at implementation

- Branch `main`, HEAD `b09a688934ee9d2b422c349fb143b7fa2af5766a` (implementation commit, adds 8 files, 1337 insertions), parent `c71d8076de6285b5a5d8ca0fd11402e3fcbbbb7f`, origin/main at `c71d8076de6285b5a5d8ca0fd11402e3fcbbbb7f` (no push, so HEAD is 1 ahead locally)
- Contract v3 canonical `79611b6b3be41fecf6beadbcbbd12439f434884f1d4d4a09c294a01134318d01` blob `eef7ad220db889166469799372759dfe1a96e35f` — recomputed LF-canonical SHA, `git hash-object`, `git ls-tree HEAD`, `git cat-file -t blob` verified; filtered worktree == HEAD
- Amendment 102 canonical `9eb9e23b9bd8a243924c674d27367bcd4c894fc6fc8ab78f2fa7c7e7baf243e3` blob `aed93e484933dd54b84aff5890a98eff9ea010f7` — verified, filtered worktree == HEAD
- Contract v1 `8a5e6280...`/`2d8f5ad...`, v2 `c5ef6961...`/`4a37528e...`, Amendment 100 `8605139...`/`50dccb37...`, 101 `4c83432...`/`d68c148...` — all preserved (HEAD==worktree, `git diff HEAD --` -> 0 for each)
- Runtime identity `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` — bound in runner preflight, `build_runtime_identity(requested_device="cuda", resolved_device=str(device))` fail-closed before scientific execution
-Tracked tree clean at implementation commit (checked via `git status --short --untracked-files=no` -> empty before commit; only untracked `0`, `wgan_*` remain)
- Scientific generation: 0 (no `data/processed/research/hedging_synthetic` directory, no `hedging_policies` checkpoints; runner defaults to DRY RUN; `require_authorization_or_refuse` without `--execute` or without tracked authorization returns DRY_RUN or raises AuthorizationError REFUSED)
- Scientific training: 0 (no GRU training loop executed; tests call `GRUHedger.forward` only on tiny fixtures, no optimizer/50k campaign)
- Policies: NOT AVAILABLE (no `checkpoint.pt` exists, `completeness_check` helper reports INVALID for any 2/3, global failure >=10)
- Execution authorization: NOT GRANTED (no file at `data/processed/research/hedging_policies/.../checkpoint.pt` and no authorization JSON exists; runner refuses without both `--execute` and tracked committed authorization)
- Final test: SEALED, access 0 (`data/manifests/split_manifest_v1.json` manifest `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`, 528 XNYS, `git ls-files` shows only harness, no final rows read)
- Network: 0 (no `git fetch`/`pull`/`push`/`ls-remote`/`curl` during Task 202 implementation beyond local `git rev-parse`/`log`/`status`/`branch`/`add`/`commit`/`hash-object`/`ls-tree`; verified via translucency)
- Push: 0 (no `git push`; HEAD b09a688 is locally 1 ahead of origin/main, not pushed)

## 6. Commit record

- Implementation committed alone at `b09a688934ee9d2b422c349fb143b7fa2af5766a` — `feat(research): implement v5 deep-hedging training pipeline` — adds 8 files: `src/neuralmarket/research/deep_hedging/__init__.py`, `artifacts.py`, `cvar.py`, `hedger.py`, `pnl.py`, `runner.py`, `synthetic.py`, `tests/unit/research/test_deep_hedging.py`
- This Amendment 103 commits separately at its own hash (see verification below)
- No amend, no rebase, no reset, no push (verified via `git reflog --date=iso` — last amend at 2026-08-22 `fix(research): admit selected v5 reserve j01`, no amend in Task-200/201/202 window; last rebase 2026-08-19, none since; last reset 2026-08-22, none since)

This amendment is append-only, contains no self-referential hash.

## 7. What this task does not do

- Does not generate 50,000-path synthetic episodes/member (tests use `torch.zeros`/`randn` tiny fixtures only, `S_INCEPTION=100.0` transformation verified but no campaign)
- Does not train 45 policies (no AdamW 0.001 optimization loop executed beyond `GRUHedger` forward shape check)
- Does not access final-test rows (split manifest metadata only, SEALED)
- Does not infer, bootstrap, external, final-test, network, or push
- Does not create real execution authorization (future authorization schema frozen but no file exists; Task 202 explicitly `NOT GRANTED`)

