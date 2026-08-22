# Amendment 044 — V5 Seed-05 CUDA Primary Execution Record

**Date:** 2026-08-22
**Task:** NM-R4-V5-SEED-05-EXECUTION-AMENDMENT-071
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `f72db0b0117de0d5e0335aa1454abe4eb69fed83`
**Safety branch:** `safety/pre-v5-seed05-execution-amendment-f72db0b` (created without switching at f72db0b)
**Execution task:** NM-R4-V5-SEED-05-CUDA-PRIMARY-EXECUTION-069
**Independent execution audit:** NM-R4-V5-SEED-05-CUDA-PRIMARY-EXECUTION-AUDIT-070
**Audit verdict:** VALIDATED WITH NON-BLOCKING FINDINGS
**Validated execution status:** `GATE_PASS_VALID` / `PRIMARY_VALID_COMPLETED`
**Seed-05 retry:** FORBIDDEN
**Execution commit (immutable):** `f72db0b0117de0d5e0335aa1454abe4eb69fed83` — `feat(research): record v5 seed-05 CUDA primary execution` (6 files, 749 insertions)
**Pre-execution HEAD (immutable):** `11b216d7dd93c75809557612220bb437ffb08ab4` — `docs(research): correct v5 seed-05 authorization record`
**Status:** APPEND-ONLY EXECUTION RECORD. No --execute, no runner invocation, no scientific training, no second seed-05 attempt, no namespace deletion, no artifact rewrite, no reserve, no fifth-member decision, no sensitivity analysis, no validation, no external validation, no final test, no hedging.

## 1. Scope and immutability

The scientific execution of `v5-seed-05` is closed and immutable at `f72db0b0117de0d5e0335aa1454abe4eb69fed83`.

- pre-execution HEAD: `11b216d7dd93c75809557612220bb437ffb08ab4`
- execution commit: `f72db0b0117de0d5e0335aa1454abe4eb69fed83` (parent is `11b216d...`, contains exactly the six committed evidence files below; no historical bytes rewritten)
- member: `v5-seed-05`
- run prefix: `1e8aa171993a1aba`
- execution validity: `GOVERNANCE_VALID`
- Gate status: `GATE_PASS_VALID` (governed six-criterion 6/6 pass)
- primary status: `PRIMARY_VALID_COMPLETED`
- retry: `FORBIDDEN`

Do NOT rerun, retrain, retune, change backend, change seed, change Gate-v2, regenerate diagnostics, or rewrite any of: checkpoints `checkpoint.pt` / `checkpoint_final.pt`, `training_curve.json`, `execution_started.json`, `training_execution_manifest.json`, `training_report.json`, `training_exit_code.txt`, `training_stdout.log`, or `structured_vol_v5_seed_05_primary_adjudication_v2.json`. All bytes are frozen.

Audit 070 independently validated the execution as governance-valid, Gate-pass, with only non-blocking governance-record timestamp deviations (see section 3). This amendment durably records that validated result without modifying any scientific byte.

Prior amendments 039–043 remain in force and are not superseded except where this amendment explicitly records the completed execution that they anticipated. Their CUDA recipe, runner, trainer, Gate-v2, config, family, schedule, and external-closure clauses are preserved.

## 2. Exact CUDA / scientific identity (frozen, no CPU fallback)

Validated exactly-once CUDA execution identity, recomputed from committed bytes and `v5-seed-05-v2.json` (blob `d77766320792c459df7566cdcf6ec12806e0da91`, FILE_SHA256 `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de`, commit `c937742b02be6f4a22e11fa5b1e61054addde076`):

- member: `v5-seed-05`
- replicate_seed: `12281`
- model_init_seed: `12281`
- data_seed: `12282`
- eval_seed: `8283` (COMMON_FIXED)
- full_config_hash: `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897`
- run prefix: `1e8aa171993a1aba` (first 16 of config hash; 16 hex chars, verified)
- family_methodology_identity: `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` (canonical V5ExperimentConfig with `model_init_seed`/`data_seed` stripped, eval 8283 kept)
- recipe (commit): `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a` — `fix(runtime): close remaining CUDA execution escapes`
- runner (blob): `05b704b254387d8f5ffdf1d847dd4289303b565c` — `reports/research/evidence/structured_vol_v5_replicate_training_runner.py` (device-aware, runtime-bound, exclusive-create `execution_started`)
- structured-vol experiment (blob): `16f5ec631eb71756084f3e74d006c31da2c6bcd8`
- trainer (blob): `85aabc6798b22a60bd4d94d4ee86bfae81a8a172` — `neural_sde_trainer_v3.py`
- Gate-v2 evaluator (blob): `05af8d0d864eddaae8c43e1cc3936d28e89abaf3` — spec hash `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469` (`configs/research/neural_sde_internal_gate_v2.yaml` blob `d9705ef9...` — preserved)
- auth-v2 schema (blob): `c74958f2c5d99753b05bf64c9b6880ee9bd37d94`
- runtime implementation (blob): `817ba53e2474c6e8dd7ecf15d64e0766e75f73e9` — `src/neuralmarket/core/runtime_identity.py` (schema `runtime-identity-v1`)
- execution contract (blob): `84a59c4d966b349be705a8a29fad07f81282ebdc` — `reports/research/structured_vol_v5_training_execution_contract_v5.json`
- schedule (blob): `558d08bfee98dbd0c170d65e6a9b1737700c9e98` — `reports/research/structured_vol_v5_seed_schedule_v1.json` (SHA `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`)
- runtime identity SHA-256 (normative capture point: after `resolve_device(cuda)` + `configure_device_determinism(cuda, enabled=True)`, before `execution_started`, before any scientific computation): `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (runtime-identity-v1, canonical JSON `sort_keys`/`separators (",", ":")` excluding stored hash field)
- Python: `3.11.9`
- PyTorch: `2.13.0+cu132`
- CUDA runtime: `13.2` (cudnn `92000`, driver `610.47`)
- device: `cuda` (requested `cuda`, resolved `cuda`; `requested_device` == `expected_resolved_device` == `resolved_device`)
- GPU: `NVIDIA GeForce RTX 4070 Laptop GPU`
- compute capability: `8.9`
- determinism at capture: `deterministic_algorithms true`, `cudnn_benchmark false`, `cudnn_deterministic true` (enforced via `configure_device_determinism` before identity capture)
- execution executable: `C:/Users/rohit/Documents/Personal Projects/Neural Market/.venv-gpu/Scripts/python.exe` (NOT `.venv`, NOT system Python, NOT CPU PyTorch)

No CPU fallback occurred. `resolve_device(cuda)` fail-closed path was not triggered; observed identity matched authorized `17e3bb52...` byte-exact.

## 3. Corrected execution chronology (authoritative)

Audit 070 independently determined that durable pre-launch evidence existed BEFORE the irreversible `execution_started` publication, but the ignored operational record `.agent-memory/tasks/NM-R4-V5-SEED-05-CUDA-PRIMARY-EXECUTION-069.json` contains two inaccurate embedded timestamp fields. The ignored state file is NOT edited. This amendment records the authoritative chronology from committed bytes and filesystem evidence.

### 3.1 Authoritative chronology (committed / recomputed)

All timestamps are UTC, recomputed from committed JSON bytes (no worktree mutation):

- durable task-record creation (filesystem evidence, before marker; Audit 070 value): `2026-08-22T03:21:15.608Z`
- background dispatch (Hermes `proc_57037da806a8` with `--execute` via `.venv-gpu`; single `BACKGROUND_FROM_OUTSET` launch): `2026-08-22T03:23:29Z` (task field `launch_utc` in manifest sense; OS process launch)
- `execution_started` marker (`execution_started.json` `start_utc`, exclusive-create `os.link` publication, attempt 1, `training_invocations_before_start 0`): `2026-08-22T03:23:31.485326+00:00` — committed marker bytes exact; SHA `11604cb60eff154d90c987a9033d12f900d37ef786a26d67b60aaa4eaeccc45c`, blob `4819dd5428e383c52d0f5df3545a4e1906963429`, report `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/execution_started.json`
- training start (`training_execution_manifest.json` / `training_report.json` `training_start_utc`): `2026-08-22T03:23:33.236586+00:00` (task-brief rounded as `2026-08-22T03:23:33.237Z` — same instant, sub-millisecond display rounding)
- training end (`training_end_utc`): `2026-08-22T03:43:20.337740+00:00` (rounded as `2026-08-22T03:43:20.338Z`)
- overall completion (`training_execution_manifest.json` / `training_report.json` `end_utc` / `training_report_created_utc`): `2026-08-22T04:01:29.930739+00:00`
- manifest `start_utc` (runner publication completion): `2026-08-22T03:23:31.498797+00:00` — 13 ms after marker `start_utc`, consistent with atomic `execution_started` -> training orchestration handoff
- commit timestamp (execution evidence commit `f72db0b`): `2026-08-22T00:04:17-04:00` (author date; `04:04:17Z` — after completion, records evidence durably)

Ordering is strictly: durable record `03:21:15Z` < dispatch `03:23:29Z` < marker `03:23:31.485326Z` < training start `03:23:33.236586Z` < training end `03:43:20.337740Z` < overall completion `04:01:29.930739Z` < commit `04:04:17Z`.

### 3.2 Two misleading ignored-state fields (NOT authoritative)

Do NOT use these ignored-state embedded values as execution chronology:

- `pre_launch/utc` in `.agent-memory/tasks/NM-R4-V5-SEED-05-CUDA-PRIMARY-EXECUTION-069.json` field `pre_launch.utc`: `2026-08-21T19:38:00.000000+00:00`
- `launch_utc` in same ignored file field `launch_utc`: `2026-08-22T03:29:18.805996+00:00` (task-record write at `00:03:53` local filesystem, re-recorded post-dispatch with clock skew)

Governance classification (per Audit 070):

- neither value is the authoritative execution chronology;
- `2026-08-21T19:38:00.000000Z` predates the starting HEAD `11b216d...` (committed `2026-08-21T` `11b216d`) and is not a truthful pre-launch event timestamp — it is a stale/default embedded value, but durable evidence itself did exist before `03:23:31Z` (verified by Audit 070 via filesystem/marker ordering), so execution remains governance-valid;
- `2026-08-22T03:29:18.805996Z` postdates the irreversible marker `03:23:31.485326Z` by ~5m47s and is not the actual launch timestamp (`03:23:29Z` dispatch is authoritative) — it is a delayed task-record write, not a second launch;
- Audit 070 independently established that durable evidence existed before launch despite these bad embedded values;
- this is a `NON_BLOCKING_GOVERNANCE_DEVIATION` (record-keeping inaccuracy in ignored operational state, not in committed scientific evidence);
- no scientific or result identity is affected (all nine artifact SHAs, training scalars, Gate diagnostics, and runtime identity are byte-exact and unchanged).

No historical evidence is rewritten. The ignored state file remains byte-unchanged; only this amendment's corrected chronology is authoritative.

## 4. Exactly-once execution accounting (Audit 070 validated)

Independently validated from committed `training_execution_manifest.json` / `execution_started.json` / `training_exit_code.txt` bytes:

- execution mode: `BACKGROUND_FROM_OUTSET` (single background `proc_57037da806a8` with `C:/Users/rohit/Documents/Personal Projects/Neural Market/.venv-gpu/Scripts/python.exe ... --member-id v5-seed-05 --authorization "C:/Users/rohit/Documents/Personal Projects/Neural Market/reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-05-v2.json" --execute`; `--authorization` supplied exactly once as absolute path; `--execute` supplied exactly once; no foreground predecessor, no relaunch)
- foreground launches: `0`
- background launches: `1`
- CLI `--execute` commands: `1` (max authorized `1`)
- irreversible starts (`execution_started` exclusive-create publications): `1` (`attempt_number 1`)
- scientific invocations (`_SCIENTIFIC_INVOCATIONS` in `training_execution_manifest.json`): `1` (max `1`; `training_invocations_before_start 0`)
- execution markers: `1` (`execution_started.json` only)
- relaunch count: `0`
- retry count: `0`
- overwrite tests: `0` (preflight `report_dir`/`model_dir` absent verified at dispatch; `1e8aa171993a1aba` absent before launch, now present exactly once)
- namespace deletions: `0` (no deletion/rename/cleanup of `1e8aa171993a1aba` or prior members `62c7406...`/`77e7de9...`/`e333325...`)
- exit code: `0`
- terminal status: `COMPLETED`
- Hermes/process ID: `proc_57037da806a8`
- OS PID: `54032`
- same process monitored through termination: YES (poll/inspect only `proc_57037da806a8`/`54032`; polling contained no `--execute`; process uptime ~2324 s, ~38.7 min; GPU utilization 84–90% observed during training)
- scientific source commit recorded in report: `357971a67c68492fc0c4f5bf31f94f9685639f65`

Limits:

- `MAX_AUTHORIZED_SCIENTIFIC_INVOCATIONS = 1`
- `CONSUMED_SCIENTIFIC_INVOCATIONS = 1`
- `RETRY_AUTHORIZED = false`

No future task may execute `v5-seed-05` again under any authorization. `v5-seed-05-v2.json` is now consumed (namespace `1e8aa171993a1aba` exists, overwrite refused); any new `--execute` for `v5-seed-05` would be `REFUSED: overwrite`.

## 5. Nine validated artifact identities (independently recomputed from actual bytes)

Audit 070 recomputed all nine SHA-256 values directly from actual file bytes (`hashlib.sha256(file_bytes)`). This amendment freezes those verified identities; no artifact was modified.

All values verified byte-exact from current committed/real bytes ( `sha256sum` / `git hash-object` ):

- execution marker `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/execution_started.json` — SHA-256 `11604cb60eff154d90c987a9033d12f900d37ef786a26d67b60aaa4eaeccc45c` (blob `4819dd5428e383c52d0f5df3545a4e1906963429`, size 2.0K, committed; tracks `runner_git_blob 05b704b...`, `authorization_git_blob d777663...`, `runtime_identity_sha256 17e3bb52...`)
- manifest `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_execution_manifest.json` — SHA-256 `2ca2e30bdc8b3703aa2237dfae46e18ba6c9da9cdeeba66f747b83d70b796e47` (blob `4a9128114f6920d6dc33ecf93c129df6117dc06b`, committed)
- training report `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_report.json` — SHA-256 `86bf6c0fe605643a2bd9a04811ad39911ad7ed9e96da9671b8fb6b29bc3dcdcd` (blob `4727d5138cfe50105b78ec51b75561b1f4ca5b8a`, committed)
- training curve `data/processed/research/model/structured-volatility-neural-sde-v5/1e8aa171993a1aba/training_curve.json` — SHA-256 `712b3da699fc063abca3ed11f4d6e95b78eba15cc0d6f6328f2e18ccae37586d` (blob `1603aa77ec0d8e73858b1ec8f52847e33ab08225`, **gitignored** per repo pattern `data/processed/` in `.gitignore`; NOT force-added; bytes preserved on disk, hash recorded in manifest/adjudication)
- selected checkpoint `data/processed/research/model/structured-volatility-neural-sde-v5/1e8aa171993a1aba/checkpoint.pt` — SHA-256 `3a71b12e1c0af08e1006b492aefd59d4e2b04ceee8e1f88a1ee07c0178f2d21a` (blob `808db090fe34f15bce8d881ad63616a738b019c3`, **gitignored**, size 83K)
- final-refit checkpoint `data/processed/research/model/structured-volatility-neural-sde-v5/1e8aa171993a1aba/checkpoint_final.pt` — SHA-256 `4d3b9475fbc9adba87bba7c84c044bd092747838538e0e69eaa05259e9a8e52f` (blob `de846f5c671f492ea167914acd521fd54a1b6ef7`, **gitignored**, size 84K; created only because Gate passed)
- adjudication `reports/research/structured_vol_v5_seed_05_primary_adjudication_v2.json` — SHA-256 `74a8c4c7196bd1227db78548f764085fa72637bddc6efe850912e6948349ee00` (blob `581079adcdc3191cef9ae5d95c3b9da0652d6879`, committed; compensates with adjudicator `39a45348056eef339958ae8298ff5d0886476cd9` `structured_vol_v5_primary_adjudicator.py`)
- training_exit_code `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_exit_code.txt` — SHA-256 `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354` (blob `573541ac9702dd3969c9bc859d2b91ec1f7e6e56`, committed, content `0\n`)
- training_stdout `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/training_stdout.log` — SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (blob `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`, committed, 0 bytes — runner captures stdout internally into manifest/report)

Tracked vs gitignored: `execution_started.json`, `training_execution_manifest.json`, `training_report.json`, `training_exit_code.txt`, `training_stdout.log`, `structured_vol_v5_seed_05_primary_adjudication_v2.json` are **tracked** (committed at `f72db0b`). `checkpoint.pt`, `checkpoint_final.pt`, `training_curve.json` remain **gitignored** under `data/processed/` per existing `seed-02`/`seed-04` pattern — this is intentional, not a gap. Their SHAs are durably recorded in the manifest/report/adjudication and remain verifiable on disk. Do NOT `git add -f` them.

## 6. Training geometry and frozen result

### 6.1 Geometry (frozen, matches `training_report.json` + `build_underlying_series`/`build_windows` pipeline)

- sessions: `926`
- returns: `925` ( `sessions - 1`; training daily log-returns from `926` sessions `2018-05-01`..`2021-12-31`)
- windows: `841` derived sliding windows (horizon `63`, lookback `22`, dt `1/252`)
- fit: `672`
- selection: `107`
- embargo (gap): `62`
- identity: `672 + 107 + 62 = 841` (verified: `fit + selection + embargo = all_training_derived_windows`)
- all_training_derived_windows: `841` (manifest `all_training_window_count`)
- training series SHA-256: `4863b2cc63a09ffb03bbe455c7859c46b521b6f7bef8212e0e3876ac8488669c`
- n_parameters: `18955`
- training_series provenance: `build_underlying_series` / `ResearchInventory` over frozen `data/manifests/research_development_inventory_v1.json` split `training` (`inventory_hash 371c148...` verified in prior Gate lineage)

### 6.2 Training result (frozen, from `training_curve.json` / `training_report.json`)

- initial selection total (`selection_total_curve[0]`): `10.106581687927246`
- best selection total (`selection_total_curve[best_epoch-1]`): `0.5789976716041565`
- best epoch: `104` (1-indexed; `best_internal_rbf 0.02688753604888916` at best epoch)
- final epoch: `144` (last curve epoch; `patience 40`, early stop `best 104 + 40 = 144`)
- curve lengths: `rbf_curve 144`, `total_curve 144`, `selection_rbf_curve 145`, `selection_total_curve 144`
- initial_internal_rbf: `0.6958807706832886` (report top-level; curve `rbf_curve[0] 0.348162...` is related but distinct scalar)

Criterion 1: `0.5789976716041565 < 10.106581687927246` — **PASS** (selection_total improvement).

## 7. Frozen Gate-v2 result (six-criterion, unchanged)

Gate-v2 spec hash `f27e5ccaba27c527f5149ff49e460dd45d9662cc86f26f5237aeffbda57d2469` (Amendment 029 lineage), evaluator `neuralmarket.research.neural_sde_internal_gate.evaluate_gate_v2` (blob `05af8d0d...`), seeds `gate_seed 7777` / `drift_diffusion_seed 7778` / `bootstrap_seed 8801` COMMON_FIXED (block bootstrap, block 22, 1024 real bootstrap + 1024 generated paths). All values from `training_report.json` `gate_diagnostics` (fail-closed numeric validation via adjudicator `39a4534805...`); recomputed independently without retraining or Gate re-evaluation.

- variance ratio (`generated_daily_variance / real_daily_variance`): `1.7002101928474205` — **PASS** in `[0.50, 2.00]` (criterion 2)
- terminal dispersion ratio (`generated_terminal_std / real_bootstrap_terminal_std`): `1.3589654002271032` — **PASS** in `[0.50, 2.00]` (criterion 3) — `real 0.04338 / gen 0.05895`
- path uniqueness (`path_uniqueness_fraction`): `1.0` — **PASS** `>= 0.99` (criterion 4)
- ACF1 absolute error (`|generated_return_acf1 - real_return_acf1|`): `0.06428223117957556` — **PASS** `<= 0.25` (criterion 5) — `real -0.065265 / gen -0.000983`
- drift/diffusion RMS ratio (`drift_increment_rms / diffusion_increment_rms`): `0.05277435327391064` — **PASS** `<= 0.50` (criterion 6) — `drift 0.000938 / diffusion 0.017792`

Governed six-criterion result: **PASS 6/6** (criterion 1 pass AND criteria 2–6 runner `gate_passed true` with frozen thresholds per Amendment 041 section 9).

Report-only normalized terminal Wasserstein (`terminal_wasserstein_normalized`): `0.6876953151338492` (raw `0.029836...`). **Wasserstein is REPORT_ONLY. It is NOT an acceptance criterion.** Do not convert report-only diagnostics (`acf_rmse 0.06142`, `acf_max_error 0.12881`, `cond_var_log_correlation 0.06477`, etc.) into Gate criteria. Gate-v2 remains unchanged; no threshold, band, or aggregation was altered.

## 8. Family accounting and scientific claim boundaries

Validated family manifest (Amendments 021/022/032 lineage, three-way semantics per Amendment 041):

- seed-01: `EXISTING_FROZEN_VALID` (CPU, `5bdbaabd2fb257a7`, gate `8.62828 -> 0.52516`, Gate PASS)
- seed-02: `PRIMARY_VALID_COMPLETED` (CPU, `62c7406cb3a2c642`, Gate PASS)
- seed-03: `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` — **inadmissible, retained** ( `e333325c804d95d2`, forensic record `reports/research/evidence/structured_vol_v5_seed_03_attempt_forensic_record.json`; `__link` marker deleted lineage; never counted)
- seed-04: `PRIMARY_VALID_COMPLETED` (CPU, `77e7de9efabb7ce3`, Gate PASS)
- seed-05: `PRIMARY_VALID_COMPLETED` / `GATE_PASS_VALID` / **CUDA** ( `1e8aa171993a1aba`, `17e3bb52...`, Gate PASS 6/6)

Counts (per Amendment 022 under-filled semantics):

- valid execution / admissible count (governance-valid): **4** (`01 + 02 + 04 + 05`) — seed-03 excluded from valid set
- Gate-pass valid count: **4** (all four governance-valid members pass Gate)
- historical CPU subset: `01 + 02 + 04` = 3 (for runtime-sensitivity CPU-vs-mixed framing per Amendments 039–041)
- valid runtime-sensitivity set: `01(cpu) + 02(cpu) + 04(cpu) + 05(cuda)` = 4 (seed-05 included because governance-valid; Gate outcome does NOT gate inclusion per Amendment 041 three-way semantics — here it happens to be PASS as well)

Boundaries:

- The five-seed requirement remains **UNRESOLVED**. `primary_valid_completed 4 != 5`; under-filled-family policy (Amendments 021/022 section 11, Amendment 032 verification) governs. Do NOT count seed-03. Do NOT claim five valid models. Do NOT claim H2 proven. Final test remains sealed.
- Do NOT authorize final test. Do NOT select a reserve (`reserve-j01..03` at `13281/14281/15281` remain not executed, separately governed). Do NOT select a fifth member or claim `PRIMARY_FULLY_VALID`.
- Do NOT perform family sensitivity analysis in this amendment. The preregistered runtime-sensitivity analysis (Amendment 040 plus Amendment 041 supersessions; scalar set, LOMO, CPU-vs-mixed design; seed-01 field mapping; RBF exclusion definitive) remains **pending a separate governed task after this amendment is independently audited** (see section 11). That later task will consume exactly the four valid members above and is outside this amendment.

## 9. Firewalls preserved (verified read-only, no access in this task)

Recomputed from committed `training_execution_manifest.json` access counters and authorization flags; no validation/external/final/hedging/provider path was accessed during task 071 (R2, no execution):

- validation constructions: `0` (`validation_constructions 0` in manifest)
- new external evaluations: `0` (`external_evaluations 0`)
- external validation: **CLOSED 2/2** (existing `reports/research/structured_vol_v5_external_validation*` artifacts untouched; no new `external_validation_evaluations`; per schedule `external_validation_firewall state CLOSED, construction_count 2, effective_max 2, third_permitted false`)
- third external construction: **FORBIDDEN** (not created)
- final-test accesses: `0` (`final_test_accesses 0` in manifest; `final_test_authorized false`; `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba` contains no final-test bytes)
- final: **SEALED** (split `2023-11-22` onward per `split_manifest_v1`; `final_test_authorized false` in authorization)
- hedging: `0`
- reserve executions: `0` ( `reserve false` in authorization and marker)
- provider calls: `0`
- network calls: `0`
- `validation_authorized false`, `final_test_authorized false`, `reserve false`, `max_training_invocations 1` (authorization enforcement verified)

Preserved unchanged (blobs/worktree == HEAD, no bytes modified):

- authorization `v5-seed-05-v2.json` (`d777663...` / `bc68789...`)
- Amendments 039–043 (family `730475...`, CUDA `6a6b9f...` recipe, sensitivity preregistration and correction, SHA correction `bc68789...`)
- CUDA recipe `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a`, runner `05b704b...`, trainer `85aabc67...`, Gate-v2 `05af8d0d...` / `f27e5cc...`, config `configs/research/structured_vol_neural_sde_v5.yaml` (`f9ca3e9b...`), family `730475...`, schedule `558d08b...` / `8c471c33...`, runtime-identity `817ba53e...`, historical seed evidence (`62c7406...`/`77e7de9...`/`e333325...`), external closure `fd142ad4...` lineage

No scientific bytes changed in this amendment — only this markdown file is created.

## 10. Append-only / Git discipline

- Safety branch `safety/pre-v5-seed05-execution-amendment-f72db0b` created without switching at `f72db0b` (no checkout).
- Exactly one file created: `reports/protocol/research_protocol_amendment_044.md` (this file).
- No execution artifacts rewritten, no checkpoints/curves force-added, no ignored `.agent-memory` state edited, no historical commit amended/rebased/reset.

Verification before commit: starting HEAD `f72db0b0117de0d5e0335aa1454abe4eb69fed83`, tracked tree clean except the new amendment file (pre-existing untracked `neural_sde_signature_v3/v4_report.json` / `structured_vol_v5_report.json` remain intentionally untracked per repo pattern).

After commit: tracked tree clean (only the three pre-existing untracked signature/report files remain untracked). No `amend`, no `rebase`, no `reset`, no `push`.

## 11. What this amendment does NOT do

- Does NOT rerun, retrain, retune, change backend, change seed, change config, change Gate-v2 thresholds, or regenerate diagnostics.
- Does NOT rewrite any of the nine artifact bytes or their SHAs (including gitignored `checkpoint.pt`/`checkpoint_final.pt`/`training_curve.json` — recorded but not force-added).
- Does NOT delete or rename the `1e8aa171993a1aba` namespace or any prior member namespace.
- Does NOT select or execute a reserve (`j01..03`) or fifth member, does NOT perform final family H1/H2/H3 inference, does NOT claim the five-seed requirement is satisfied.
- Does NOT perform or claim `externalsensitivity analysis`; does NOT run validation or final-test evaluation; does NOT access provider/network.
- Does NOT modify `f72db0b...` history.

## 12. Required next action

Next task MUST independently audit this Amendment 044 read-only (verify: Audit 070 verdict consumed correctly, execution commit `f72db0b` and pre-execution HEAD `11b216d` exact, CUDA/scientific identities exact, corrected chronology and bad-field classification accurate, exactly-once accounting `1/1/1/1/0` exact, nine SHA-256 identities byte-exact from actual bytes, training geometry `672+107+62=841` and Gate six-criterion PASS exact, Wasserstein report-only correctly labelled, family counts `4` / Gate-pass `4` / five-seed UNRESOLVED exact, firewalls `0` with external CLOSED 2/2 and final SEALED, no scientific bytes changed, single append-only file, no execution in this task) before any family sensitivity analysis may be separately governed. The preregistered runtime-sensitivity analysis may run only after that audit.

---

*Amendment 044 durably records the independently validated (`VALIDATED WITH NON-BLOCKING FINDINGS`, Audit 070) seed-05 CUDA primary execution at `f72db0b0117de0d5e0335aa1454abe4eb69fed83` (parent `11b216d...`; member `v5-seed-05`; `1e8aa171993a1aba`; CUDA `17e3bb52...` via `.venv-gpu` `3.11.9`/`2.13.0+cu132`/`RTX 4070` CC `8.9`): corrected chronology `03:21:15Z` durable record < `03:23:29Z` dispatch < `03:23:31.485326Z` marker < `03:23:33.236586Z` training start < `03:43:20.337740Z` training end < `04:01:29.930739Z` completion, explicitly classifying ignored-state `pre_launch/utc 2026-08-21T19:38:00Z` and `launch_utc 03:29:18.805996Z` as `NON_BLOCKING_GOVERNANCE_DEVIATION`; exactly-once `BACKGROUND_FROM_OUTSET 1/0/1/1/1/1` (`proc_57037da806a8`/`54032` exit `0`); nine artifacts SHA-256 `11604cb...`/`2ca2e30b...`/`86bf6c0f...`/`712b3da...`/`3a71b12e...`/`4d3b9475...`/`74a8c4c...`/`13bf7b30...`/`e3b0c442...`; training `10.1065 -> 0.5789` best `104`/final `144` (`672+107+62=841`); Gate-v2 6/6 PASS (`1.7002`/`1.3589`/`1.0`/`0.06428`/`0.05277`, Wasserstein `0.6876` report-only); status `GATE_PASS_VALID`/`PRIMARY_VALID_COMPLETED` retry `FORBIDDEN`; family `4` valid / `4` Gate-pass / five-seed UNRESOLVED; firewalls intact `0` (external CLOSED 2/2, third FORBIDDEN, final SEALED); NO NEW SCIENTIFIC EXECUTION.*
