# Amendment 076 — V5 WGAN Seed-02 Training Authorization Provenance Repair

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-SEED-02-TRAINING-AUTHORIZATION-PROVENANCE-REPAIR-142`
Risk: `R4`
Branch: `main`
Starting HEAD: `55e61029e70e35efefbb430efac931ac8c49fb86`
Prerequisite: `NM-R4-V5-WGAN-SEED-02-TRAINING-AUTHORIZATION-UNIQUE-KEY-REPAIR-141` — `BLOCKED_SEED02_AUTHORIZATION_DUPLICATE_PROVENANCE_CONFLICT`
Prerequisite trigger: divergent `diagnostic_persistence_provenance` duplicate in `wgan-seed-02-v1.json`
Status: APPEND-ONLY PROVENANCE REPAIR — no WGAN training, Gate, seed-03/04/05, reserve, H2, final-test, network, or push; no source/comparator/model edit.

## 1. Trigger and authority

Audit-140 noted Task-139 Amendment-075 prose contained a report-only transcription error (malformed 59-char SHA `9a4b7e1c2f8d3c6b9e0f1a2d4c8b7d6e5f3a2c1` and commit prefix `55e6102` confused as blob). The committed Amendment 075 itself was adjudicated accurate: actual SHA `6da76064d10ec10b84e5937010aab2027a23665b0e8fd31f30b0d8422638738f`, blob `3c882eecd4a1471909f38e074a33316535662a17`, no self-hash, accurate authorization provenance. Therefore:

Task-139 report transcription: `REPORT_ONLY_TRANSCRIPTION_ERROR`
Committed Amendment-075 defect: `NO COMMITTED AMENDMENT-075 DEFECT` — no Amendment 075 repair required.

Trigger for this amendment is Task-141's divergent duplicate finding:

- `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v1.json` (canonical SHA `8dee7f132a5a5a610e97c9cf7ab774cfc362141226f4bc017db2cee9c483c75b`, blob `3a4d1977255e1eebbbeaf6a8e774e7fc6f3de4da`) contains two divergent top-level `diagnostic_persistence_provenance` objects:
  - occurrence 1: `amendment_074_sha256: ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00`, `amendment_074_git_blob: e5722ac2a2ad669cc95adbba408cc7db1b57c93a`
  - occurrence 2: `amendment_074_sha256: d4f9a7c9e0a1b3e8f2c6d5a4b3c2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3`, `amendment_074_git_blob: 7E0D`

Do NOT choose first-wins or last-wins. Authority is immutable source.

The governed transitions were:

`DISCOVER -> DECIDE -> REPAIR -> VERIFY -> REPORT`

This repair creates exactly one source-derived unique-key authorization `v2`; it does not train, execute the runner, create a marker, checkpoint, Gate, later authorization, H2, or final-test.

## 2. Authoritative Amendment-074 source

Read directly from the committed Git object `reports/protocol/research_protocol_amendment_074.md`:

- actual canonical SHA-256: `ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00` (SHA-256 of `git cat-file -p HEAD:reports/protocol/research_protocol_amendment_074.md`)
- actual Git blob: `e5722ac2a2ad669cc95adbba408cc7db1b57c93a` (`git rev-parse HEAD:reports/protocol/research_protocol_amendment_074.md` equals `git hash-object --path` filtered worktree)

Amendment 074 remains byte-identical to the previously audited artifact and binds the prospective diagnostic-persistence runner `56a1370cb3b76d5849083c175a3d98bc6a390261` / comparator `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`.

Comparison:

- occurrence 1: `MATCHES_IMMUTABLE_SOURCE` (both sha and blob equal authoritative)
- occurrence 2: `DOES_NOT_MATCH_IMMUTABLE_SOURCE` — classified as `INVALID_PLACEHOLDER_PROVENANCE` (placeholder values from pre-fix draft)

Authority basis: `SOURCE_DERIVED_NOT_POSITION_DERIVED` — not first/last-wins parsing, but source-of-truth adjudication.

If authoritative identity had not matched occurrence 1, the repair would have blocked as `BLOCKED_AUTHORITATIVE_PROVENANCE_NOT_ESTABLISHED`.

## 3. Complete seed-02 scientific contract re-verified

Independently recomputed at `55e6102` before creating v2; no drift:

- runner: `56a1370cb3b76d5849083c175a3d98bc6a390261`
- comparator: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
- model: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
- WGAN config canonical SHA: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7` (blob `e0740afc24697f2eab3620a4243d04411aa508cb`)
- full_config_hash (WGANTrainingConfig for seed-02): `5c223604327df9bcc61debaa8743db2d8f8101faadbf1dc9192b86d7bff3ee2f` (seed-01 reference `31c1dfb28737f9701c52ddbb7f496cf3ba03d7196c6d7ea948a02341c2ecbd58` — seed-specific)
- run prefix: `e1cc68218d9eef71`
- runtime identity: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (3.11.9 / 2.13.0+cu132 / 13.2 / RTX 4070 Laptop 8.9 / cuDNN 92000 / cuda/cuda deterministic true, rebuilt via runner order resolve->configure_determinism->build_runtime_identity using .venv-gpu)
- seed tuple: `replicate_seed: 9281`, `model_init_seed: 9281`, `data_seed: 9282`, `eval_seed: 8283`, internal-selection `7777`, bootstrap `8801`, future Gate `8283`
- additional provenance: seed schedule `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` / `558d08bfee98dbd0c170d65e6a9b1737700c9e98`, execution contract `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4` / `194b68797538010f35f5d48a2ec7c4cc4eee533f`, prereg `6c4a2725...` / `72311888...`, Amendment 060 `2f9bb12f...` / `a1ba052a...`, Amendment 062 `8befe31d...` / `086e13f0...`, training-data via frozen manifest.

No source/config/runtime drift — would have blocked as `BLOCKED_SEED02_V2_SOURCE_DRIFT`.

## 4. V2 construction — source-derived, not parsed v1

Do NOT ordinary-json-load v1 last-wins. Do NOT mutate v1.

Created exactly: `reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-02-v2.json` (authorization commit `7061f86b6e24d41ee733cff8a1d14743b4f1359f`)

Constructed from current validated schema + independently recomputed identities + frozen seed-02 tuple + actual Amendment-074 identity + audited diagnostic contract.

V2 binds exactly one `diagnostic_persistence_provenance`:

- `amendment_074_sha256: ef171da32921ea59f285a27db42b6142f45e6445137d3f453152132e751bda00`
- `amendment_074_git_blob: e5722ac2a2ad669cc95adbba408cc7db1b57c93a`
- `runner_git_blob: 56a1370cb3b76d5849083c175a3d98bc6a390261`
- `comparator_git_blob: 78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
- `training_diagnostics_schema: structured-vol-v5-wgan-training-diagnostics-v1`
- `historical_seed01_diagnostics: MISSING_BY_DESIGN_HISTORICAL`
- `mode_collapse_indicator: NOT_AVAILABLE_WITHOUT_SCIENTIFIC_CHANGE`
- `prospective_availability: PRESENT for critic/generator/gradient_penalty/selection curves, update counts, completion, finite status, checkpoint selection`

Retains same scientific meaning as intended v1: seed tuple `9281/9281/9282/8283`, runner/comparator/model, WGAN config/data/methodology, full_config_hash/run prefix, CUDA runtime `17e3bb52...`, `max_scientific_invocations: 1`, `training_authorized: true`, `validation_authorized: false`, `final_test_authorized: false`, `overwrite/relaunch/rerun: false`. No unsupported fields added except explicit `supersedes` lineage for provenance (already supported pattern via seed-01 authorization_lineage).

Serialized deterministically with repository JSON convention (indent 2 + LF).

## 5. Recursive unique-key and semantic correctness

Before commit, inspected raw V2 bytes with recursive duplicate-detecting decoder (object_pairs_hook at every level):

- recursive object count inspected: `11`
- recursive duplicate count: `0`
- duplicate names: `none`
- `diagnostic_persistence_provenance` occurrences: `exactly 1`

Field-level provenance table (load-bearing fields vs actual governing sources):

| Field | V2 value | Source | Equality |
|---|---|---|---|
| member_id | wgan-seed-02 | frozen roster | PASS |
| seeds | 9281/9281/9282/8283 | _SEED_TUPLES | PASS |
| runner | 56a1370... | HEAD:src/.../wgan_runner.py | PASS |
| comparator/model | 78a9da... / 2f5cf1... | HEAD blobs | PASS |
| WGAN config sha/blob | de0b4fe7... / e0740afc... | cat-file | PASS |
| full_config_hash / run_prefix | 5c223604... / e1cc68218d9eef71 | WGANTrainingConfig | PASS |
| seed schedule / exec contract / prereg / Am060 / Am062 | 8c471c... / 194b68... / 6c4a27... / 2f9bb1... / 8befe3... | cat-file | PASS |
| Amendment-074 | ef171da... / e5722ac2... | authoritative source | PASS |
| runtime | 17e3bb52... | rebuilt .venv-gpu | PASS |
| permissions | 1 / true / false / false | required | PASS |

Scientific differences from audited intended seed-02 contract: `0`. Allowed differences from v1: artifact version `v1->v2`, path `wgan-seed-02-v1.json -> wgan-seed-02-v2.json`, `execution_recipe_head`/`authorization_freeze_starting_head` `1aed3c6 -> 55e6102` (current HEAD), duplicate removal, replacement of invalid placeholder provenance with source-verified actual provenance, explicit `supersedes` metadata. No seed, model, config, data, runtime, permission, or methodology value changed.

## 6. CUDA runtime rebuild and SAFE validation

Rebuilt deterministically via runner prelaunch order using .venv-gpu:

- Python 3.11.9, PyTorch 2.13.0+cu132, CUDA 13.2, CUDA available true, GPU NVIDIA GeForce RTX 4070 Laptop GPU, capability 8.9, cuDNN 92000, requested cuda, resolved cuda, deterministic true, runtime 17e3bb52..., CPU fallback PROHIBITED — matches expected.

SAFE library-only validation (no CLI, no --execute, no marker):

- schema PASS
- member wgan-seed-02 PASS
- seeds PASS
- runner/comparator/model PASS
- config/data/methodology PASS
- runtime PASS
- permissions PASS (1 / true / false / false / overwrite/relaunch/rerun false)

Before/after:

- marker absent (reports/research/wgan_comparator_runs/wgan-seed-02/e1cc68218d9eef71/execution_started.json absent) PASS
- checkpoint absent (data/processed/research/model/wgan-comparator/wgan-seed-02/.../checkpoint.pt absent) PASS
- training report absent PASS
- training execution 0 PASS

## 7. V2 committed object verification

Safety branch without switching: `safety/pre-wgan-seed02-auth-provenance-repair-55e6102` at `55e61029e70e35efefbb430efac931ac8c49fb86`

Commit only `wgan-seed-02-v2.json`: `7061f86b6e24d41ee733cff8a1d14743b4f1359f` (`docs(research): repair wgan seed02 authorization provenance`)

After commit:

- v2 canonical SHA: `c282bc433905641e9413db28aa135cbfda60dac92d59b87cdaf68f766dae4491`
- v2 Git blob: `747a1d8a11a1a4d97605cad154d870dca196022c`
- filtered/path-aware worktree blob: `747a1d8a11a1a4d97605cad154d870dca196022c` (`git hash-object --path` filtered) — equality `PASS`
- recursive duplicate count on committed object: `0` PASS
- safe validation of committed v2 via _load_authorization + validate_authorization_payload: `PASS`

Recorded: authorization commit `7061f86...`, v2 SHA `c282bc43...`, v2 blob `747a1d8a...`, no amend.

## 8. V1 and V2 disposition

- `wgan-seed-02-v1.json`:
  - preserved: YES (byte-identical at 8dee7f13/3a4d1977)
  - mutated: NO
  - technical consumption: NO
  - marker: ABSENT
  - training: 0
  - scientific bindings: OTHERWISE_VALID (runner/comparator/model/config/runtime all validated)
  - provenance: DIVERGENT_DUPLICATE_KEY (ef171da... vs d4f9a...)
  - execution eligibility: SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION — MUST NEVER authorize training.

- `wgan-seed-02-v2.json`:
  - provenance: UNIQUE_AND_SOURCE_VERIFIED (single ef171da.../e5722ac2..., recursive 0)
  - technical consumption: NO
  - marker: ABSENT
  - training: 0
  - execution eligibility: FROZEN_PENDING_INDEPENDENT_AUDIT — future seed-02 execution may ONLY consume v2 after separate independent audit; v1 may never be used.

No ambiguity remains.

## 9. Final verification and audit readiness

Verified after both commits (tracked tree clean, safety branch preserved):

- v1 byte-identical (8dee7f13/3a4d1977)
- v2 exists exactly once (747a1d8a, c282bc43, duplicate 0)
- v1 marker absent, v2 marker absent, seed-02 checkpoint absent, seed-02 training report absent, no live WGAN runner process
- runner/comparator/model/config unchanged (56a1370 / 78a9da57 / 2f5cf1dd / de0b4fe7)
- seed-01 artifacts unchanged (v1 c5e234e5, v2 804d3b42, v3 c261b15c, Gate b6960813, checkpoint 332614..., marker 18d246aa, reports unchanged)
- Amendments 069–075 unchanged (074 ef171da..., 075 6da76064...)
- real training 0, real Gate 0, seed-03/04/05 0, reserve 0, H2 0 (UNRESOLVED_PENDING_WGAN_COMPARATOR), final SEALED, network 0, push 0

No source/tests changed — no repository-wide suite required.

Status:

`WGAN SEED-02 TRAINING AUTHORIZATION V1: SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION`

`WGAN SEED-02 TRAINING AUTHORIZATION V2: FROZEN_PENDING_INDEPENDENT_AUDIT`

`WGAN SEED-02 TRAINING: NOT EXECUTED`

Next task must be a separate independent read-only audit of v2.

This amendment is append-only, contains no self-hash, and does not modify Amendment 074 or 075.

