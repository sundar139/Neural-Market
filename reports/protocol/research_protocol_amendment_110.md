# Amendment 110 — V5 Hedging Synthetic Generation Execution

Date: 2026-08-25
Task: `NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-EXECUTION-212`
Risk: `R4`
Type: `SCIENTIFIC_EXECUTION`
Branch: `main`
Starting HEAD: `eb115afb09e6bff417ea037b012f2a56fc3e20ad`
Safety branch: `safety/pre-v5-hedging-synthetic-generation-19bd227` at `19bd2271e5eeb5234faf8c9961af96eca1238763`
Prerequisite: `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-211` — `AUTHORIZATION_FROZEN_VALID`
Authorization task: `NM-R4-V5-DEEP-HEDGING-TRAINING-EXECUTION-AUTHORIZATION-212`
Authorization commit: `69c534fedae0d3bf81ae55c00b50c737db4dfd6e`
Authorization path: `reports/protocol/hedging_execution_authorization_212.json`
Authorization canonical SHA: `b61999e16e7f695cc94ada354f70af690d7d038930e1231d4d81a86c5212a724`
Authorization Git blob: `f7d30259c7da43a631a1b30bea02d7490f0fa517`
Implementation commit: `1e6af6e9bcd1150700f34f8e7e0c7f9d280a934b`
Implementation manifest SHA: `e3e7b6192881a06c81893973ad9c40d981e11e240a4af450d9185e4fa78622f4` for 15 paths
Runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` — `torch 2.13.0+cu132 / CUDA 13.2 / cuDNN 92000 / RTX 4070 Laptop GPU / compute 8.9 / deterministic True`
Evidence commit: `7e6dd3788a3d7ab213d0bc3849c93a85c2bd53a1`
Evidence path: `reports/research/evidence/structured_vol_v5_hedging_synthetic_generation_execution_v1.json`
Evidence canonical SHA: `3907ec84ee857cba5312bd31623918eb668d55224208d6d937d3dcecf9d545fa`
Evidence Git blob: `8c6fcc65a3cfc77c1342d9d43efded73ab7ce91d`

## 1. Execution order and commands

Execution order: frozen `seed-01` (1), `seed-02` (2), `seed-04` (3), `seed-05` (4), `reserve-j01` (5) — exactly this order, one command per member, fail-stop.

Commands (via validated .venv-gpu interpreter, hard production CLI, deterministic preflight):
- `python -m neuralmarket.cli.deep_hedging generate-synthetic --execute --authorization reports/protocol/hedging_execution_authorization_212.json --member seed-01` → exit 0
- `python -m neuralmarket.cli.deep_hedging generate-synthetic --execute --authorization reports/protocol/hedging_execution_authorization_212.json --member seed-02` → exit 0
- `python -m neuralmarket.cli.deep_hedging generate-synthetic --execute --authorization reports/protocol/hedging_execution_authorization_212.json --member seed-04` → exit 0
- `python -m neuralmarket.cli.deep_hedging generate-synthetic --execute --authorization reports/protocol/hedging_execution_authorization_212.json --member seed-05` → exit 0
- `python -m neuralmarket.cli.deep_hedging generate-synthetic --execute --authorization reports/protocol/hedging_execution_authorization_212.json --member reserve-j01` → exit 0

No retry, no rerun, no replacement, no alternate generation, no direct `generate_and_persist` bypass in final committed execution (ad-hoc bypass during development was discarded and regenerated).

## 2. Per-member artifacts (each 50,000 episodes, horizon 63)

All datasets generated via frozen NSDE (real `.pt` checkpoints, no fabrications) with deterministic CUDA RNG and fail-closed preflight (commit-is-ancestor, manifest 15 blobs, clean tree, runtime identity, frozen contract v3, checkpoint identities).

| member | run_prefix | checkpoint_path | checkpoint_raw_sha256 | checkpoint_git_hash | synthetic_rng | dataset_path | dataset_sha256 | manifest_sha256 | rows | train | selection | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| seed-01 | 5bdbaabd2fb257a7 | data/processed/research/model/structured-volatility-neural-sde-v5/5bdbaabd2fb257a7/checkpoint.pt | 452f70058eb03a83af248fdb3c85f413264becd302b1e71d11167f10ac7b887f | 6820d07c0fb253a028c88e46b5db0b16363ae22c | 42001 | data/processed/research/hedging_synthetic/5bdbaabd2fb257a7_seed-01/synthetic_episodes_v1.parquet | cda7280a1cebe7fc389e547e276e6c3ffa7b949bfec8d12ca44e53da485f6287 | 772a0a18320ab524da031ecfe2af34442cf9ba3a42426140a3a8cc0db7122717 | 50000 | 40000 | 10000 | success |
| seed-02 | 62c7406cb3a2c642 | data/processed/research/model/structured-volatility-neural-sde-v5/62c7406cb3a2c642/checkpoint.pt | 9e6f8cd030d073d5c93ac36c94c55b09366f07b2f153f181fc82daedffc0064e | 592df5d33f9342902d5526a710ef4a2c633fe058 | 42002 | data/processed/research/hedging_synthetic/62c7406cb3a2c642_seed-02/synthetic_episodes_v1.parquet | 20a0390f1c1c5b4bbaede161436d336f4d847c7e0480420fc026be8d6e51dac7 | e35c069167eb84e77a9a4b3bc4d55e6b73add00d13a5708d71027cab0582f3aa | 50000 | 40000 | 10000 | success |
| seed-04 | 77e7de9efabb7ce3 | data/processed/research/model/structured-volatility-neural-sde-v5/77e7de9efabb7ce3/checkpoint.pt | 87d022152ba28f886b56bcf966ebc18d40e73d911258a83f01ece150ce8e7a89 | 3701888ef57f201370cfd66f763e9bf38e0e64d1 | 42004 | data/processed/research/hedging_synthetic/77e7de9efabb7ce3_seed-04/synthetic_episodes_v1.parquet | 60777e33ac94dbe8040490b1a37863260037defe46d9c8da63446c373b695bd8 | 4a51347c086c764d255f3e47a4b904b2dc4d4dcfe05c7135fb014c204e00af2a | 50000 | 40000 | 10000 | success |
| seed-05 | 1e8aa171993a1aba | data/processed/research/model/structured-volatility-neural-sde-v5/1e8aa171993a1aba/checkpoint.pt | 3a71b12e1c0af08e1006b492aefd59d4e2b04ceee8e1f88a1ee07c0178f2d21a | 808db090fe34f15bce8d881ad63616a738b019c3 | 42005 | data/processed/research/hedging_synthetic/1e8aa171993a1aba_seed-05/synthetic_episodes_v1.parquet | 8023c9f4ac5e959fa02844e7fd92823061dce079c7943d12e2d7ca49d556e204 | 98c3c4b402365876726d889c5f3e93861757d33a74392ee3e79ccbefabb6f97d | 50000 | 40000 | 10000 | success |
| reserve-j01 | 38c5113b27568e14 | data/processed/research/model/structured-volatility-neural-sde-v5/38c5113b27568e14/checkpoint.pt | 50d14095d95386c0596b36297185c3a1eca6182b463adfae52370890c600d183 | 38c9f8a0c8f97c64f1b14d269fc90cadbcccd1f8 | 42006 | data/processed/research/hedging_synthetic/38c5113b27568e14_reserve-j01/synthetic_episodes_v1.parquet | 60787517fbabb2d3ebd6169155f884f872730d0367beda4f59d7e399741830dc | 881db08f7c6b62123d77b7de81327794154c184afbad809e16dfbfbd9b8b5d83 | 50000 | 40000 | 10000 | success |

Each member directory contains exactly: `synthetic_episodes_v1.parquet` (tracked via Git LFS or untracked per data policy, manifest-tracked via SHA), `synthetic_manifest_v1.json` (plus started/exit/terminal sidecars not required for audit but present). Five datasets, five manifests, zero skipped, zero failed.

## 3. Firewalls and what was NOT done

- Training: 0 invocations, 0 policy checkpoints, 0 GRU training (AUTHORIZED_BUT_NOT_EXECUTED — requires separate Task 213+)
- GRU training invocations: 0
- Final-test access: 0, final-test marker absent, final result absent
- Network: 0, External: 0, Push: 0, Bootstrap: 0, Validation harness: 0
- No distributed comparison, no ACF, no hedging evaluation, no Wasserstein — deferred to independent audit

## 4. Completeness and next gate

Campaign: `authorized generation: 5 attempted, 5 consumed, 5 succeeded, 0 failed, 0 not attempted, 0 retries, 0 reruns, 0 replacements, 0 alternate generation` — verdict `Minimal integrity: five datasets, five manifests, 250,000 total rows, dataset SHA matches, terminal success.`

Scientific quality: `NOT_YET_AUDITED` — Task 213 independent audit must verify distribution, split stratification, and pricing contract before hedging.

Next governed task: `NM-R4-V5-DEEP-HEDGING-SYNTHETIC-GENERATION-AUDIT-213` (STRICT_READ_ONLY SCIENTIFIC_ARTIFACT_AUDIT) — DO NOT train any GRU policy before Task 213 passes.

If any member had failed: STOP, preserve consumed attempt, recommend exactly one Task-213 failure/recovery adjudication, do NOT execute remaining members.

