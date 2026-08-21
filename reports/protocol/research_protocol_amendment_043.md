# Amendment 043 — V5 Seed-05 CUDA Authorization Record Correction

**Date:** 2026-08-21
**Task:** NM-R4-V5-SEED-05-AUTHORIZATION-RECORD-REPAIR-067
**Risk:** R2
**Branch:** `main`
**Starting HEAD:** `89872d89532b5d1e081d146d67eee783de87a863`
**Safety branch:** `safety/pre-v5-seed05-auth-record-repair-89872d8`
**Prior task:** NM-R4-V5-SEED-05-AUTHORIZATION-FREEZE-065
**Prior audit:** NM-R4-V5-SEED-05-AUTHORIZATION-AUDIT-066 — REPAIR REQUIRED (governance-record only)
**Validated authorization (unchanged, byte-exact):** `reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-05-v2.json` at commit `c937742b02be6f4a22e11fa5b1e61054addde076`
**Amendment 042 commit:** `89872d89532b5d1e081d146d67eee783de87a863` — historically immutable, NOT modified
**Status:** RECORD CORRECTION — append-only governance-record repair. No authorization mutation, no scientific training, no --execute, no execution marker, no reserve/validation/final/hedging.

## 1. Scope

Audit 066 independently validated the authorization artifact `v5-seed-05-v2.json` as complete, internally consistent, correctly bound, and unconsumed. The artifact itself was never corrupt; its committed bytes are unchanged. The only blocking defect is Amendment 042's governance-record transcription of the authorization SHA-256.

Amendment 042 remains historically immutable. This amendment supersedes ONLY the erroneous SHA-256 statement in Amendment 042 section 2.1. No other Amendment 042 clause is superseded. Amendment 043 does not regenerate, replace, rewrite, rename, or reserialize the authorization artifact in any way.

## 2. Authorization re-verified (read, not modified)

Recomputed directly from `v5-seed-05-v2.json` current committed bytes (no worktree/index difference; no mutation):

- path: `reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-05-v2.json`
- SHA-256 (FILE_SHA256, `hashlib.sha256(file_bytes)`): `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de`
- Git blob (GIT_BLOB_SHA1, `git hash-object` / SHA-1 over `blob <size>\0<bytes>`): `d77766320792c459df7566cdcf6ec12806e0da91`
- authorization commit (full SHA): `c937742b02be6f4a22e11fa5b1e61054addde076` (subject: `docs(research): freeze v5 seed-05 CUDA authorization`; contains ONLY the v2 artifact, 25 insertions)
- file size: `1199` bytes
- field count: `23` (exactly `REQUIRED_AUTH_FIELDS_V2`; see section 5)
- worktree clean: YES (`git diff --quiet -- <path>` rc 0)
- index clean: YES (`git diff --cached --quiet -- <path>` rc 0)
- worktree blob == HEAD blob: YES
- historical `v5-seed-05.json` preserved (blob `dcfb2c188c5155111e5dcfc39ca331b49ce2f80b`, `authorization-v1`, inspection-only): YES

Expected values per Audit 066 and section 5 of the task are EXACTLY matched — `PASS`.

### Hash-system distinction

- `FILE_SHA256` (hex, 64 chars) is SHA-256 over raw file bytes. The authoritative file identity is `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de`.
- `GIT_BLOB_SHA1` (hex, 40 chars) is SHA-1 over the Git blob object (`blob 1199\0` prefix + file bytes). The authoritative Git blob is `d77766320792c459df7566cdcf6ec12806e0da91`.

These are distinct hash systems and MUST NOT be confused. Amendment 042's erroneous SHA was recorded as a FILE_SHA256, not a Git blob.

## 3. Governance-record defect (reconstructed)

### 3.1 Location

Amendment 042 `reports/protocol/research_protocol_amendment_042.md` section 2.1 line:

`- SHA-256: \`29d11cf53da65429327623ec1211b9b7b35b46e5cf7025d53a47d7f3e7fe49c2\` (verify via \`sha256sum\` / \`Get-FileHash\`)`

Only this SHA statement is superseded. The Git blob recorded on the next line (`d77766320792c459df7566cdcf6ec12806e0da91`) was correct.

### 3.2 Incorrect versus correct

- incorrect SHA as written in Amendment 042 section 2.1: `29d11cf53da65429327623ec1211b9b7b35b46e5cf7025d53a47d7f3e7fe49c2` (full value, untruncated)
- correct SHA from actual artifact bytes (recomputed above): `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de`
- correct Git blob: `d77766320792c459df7566cdcf6ec12806e0da91`
- authorization commit (full): `c937742b02be6f4a22e11fa5b1e61054addde076`
- Amendment 042 commit (full, immutable): `89872d89532b5d1e081d146d67eee783de87a863`

### 3.3 Nature of the defect

- The authorization artifact was never corrupt.
- The committed authorization bytes at `c937742` are unchanged (verified: worktree == HEAD, blob `d777663...`, FILE_SHA256 `bc68789...`).
- Audit 066 independently validated the artifact as complete, correctly bound, and unconsumed.
- Only Amendment 042's recorded SHA-256 was wrong — a governance-record transcription error.
- This is a documentation/governance-record correction, not a scientific or authorization mutation. No authorization field, CUDA identity, scientific identity, or semantic has changed.

## 4. Serialization / hash evidence (bounded, read-only)

Recomputed without modifying the real file; all hashes are SHA-256 over bytes unless labelled Git blob:

- (1) current committed bytes (1199 bytes): `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de` — matches authoritative FILE_SHA256, `PASS`
- (2) canonical repo formatting `json.dumps(data, indent=2).encode()+b'\n'` (reconstructed from parsed data): `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de` — identical to (1) because current bytes already use this formatting
- (3) compact `json.dumps(data, separators=(',',':')).encode()`: `69c676908f1e7a029d0bd1b43237c128a9f96673d1e9c7ed66b1f380fef66b34` — not `29d11cf5...`
- (4) no-final-newline `file_bytes.rstrip(b'\n')` (1198 bytes): `1813027a2bd4f60c70fd85d9f1ebe95d721d0046a01c783c18d743db4c33af32` — not `29d11cf5...`
- (5) sorted-key canonical `json.dumps(data, indent=2, sort_keys=True).encode()+b'\n'`: `31fff63e0b8c648a1b16c27e622229cc811ef67e9e0576361e5f957ca051f0ae` — not `29d11cf5...`
- Git blob (SHA-1, for distinction): `d77766320792c459df7566cdcf6ec12806e0da91`

Erroneous `29d11cf53da65429327623ec1211b9b7b35b46e5cf7025d53a47d7f3e7fe49c2` was NOT reproduced by any legitimate tested serialization — consistent with Audit 066's finding that none of five plausible serialization variants legitimately produces that identity. Only in-memory/temp variants were tested; the real file was never overwritten.

Only the variants above were tested; no fifth variant was invented merely to reach a count.

## 5. Authorization semantics (verification only, not changed)

Confirmed from committed `v5-seed-05-v2.json` (23 fields, no extras; field order is canonical as committed):

- member_id: `v5-seed-05`
- replicate_seed: `12281`
- model_init_seed: `12281`
- data_seed: `12282`
- eval_seed: `8283`
- full_config_hash: `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897`
- run_prefix: `1e8aa171993a1aba`
- family_methodology_identity: `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`
- schedule_git_blob: `558d08bfee98dbd0c170d65e6a9b1737700c9e98`
- schedule_sha256: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`
- execution_contract_git_blob: `84a59c4d966b349be705a8a29fad07f81282ebdc`
- runner_git_blob: `05b704b254387d8f5ffdf1d847dd4289303b565c`
- execution_recipe_head: `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a` (ancestor of HEAD, contains runner/contract/schedule at correct blobs)
- requested_device: `cuda`
- expected_resolved_device: `cuda`
- expected_runtime_identity_sha256: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` (runtime-identity-v1)
- authorization_task_id: `NM-R4-V5-SEED-05-AUTHORIZATION-FREEZE-065`
- training_authorized: `true`
- validation_authorized: `false`
- final_test_authorized: `false`
- reserve: `false`
- max_training_invocations: `1`

No field has changed; no semantics have changed.

## 6. Unconsumed authorization state (verified before and after)

Run prefix `1e8aa171993a1aba` has no real execution evidence:

- `reports/research/structured_vol_v5_replicates/1e8aa171993a1aba/execution_started.json`: ABSENT
- training report: ABSENT
- checkpoint: ABSENT
- curve: ABSENT
- Gate report: ABSENT
- model namespace `data/processed/research/model/structured-volatility-neural-sde-v5/1e8aa171993a1aba/`: ABSENT

Counters:

- scientific invocation count: `0`
- training: `0`
- --execute: `0`
- execution_started: `0`
- seed-05 attempts: `0`

No intercepted execution-boundary probe was run in this task (not required; Audit 066 already validated runtime/authorization semantics). Seed-05 remains `NOT_ATTEMPTED` and `NOT AUTHORIZED FOR EXECUTION UNTIL AUDIT`.

## 7. Methodology and sensitivity contracts (unchanged)

Verified unchanged (blobs/worktree == HEAD, no bytes modified):

- Amendments 039 (`730475...` family, `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT`), 040, 041 (effective sensitivity), and 042 (all content except superseded SHA statement)
- `v5-seed-05-v2.json` (blob `d777663...`, FILE_SHA256 `bc68789...`) and `v5-seed-05.json` (blob `dcfb2c18...`)
- CUDA recipe `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a`, runner `05b704b25...`, trainer `85aabc67...`, Gate-v2 `05af8d0d...`, auth-v2 schema `c74958f2...`, runtime implementation `817ba53e...` at `src/neuralmarket/core/runtime_identity.py`, config `configs/research/structured_vol_neural_sde_v5.yaml`, family `730475...`, schedule `558d08b...`, external-validation closure `fd142ad4...`

Status semantics preserved: `GATE_PASS_VALID`, `GATE_FAIL_VALID`, `VALID_EXECUTION_NO_GATE_RESULT`, `GOVERNANCE_INVALID` per Amendments 041/042. No fifth-member/reserve decision created; five-seed requirement remains unresolved; final test remains sealed (split `2023-11-22` onward).

## 8. What this amendment does NOT do

Does not modify Amendment 042 file bytes; does not regenerate or reserialize any authorization artifact; does not change any authorization field, scientific identity, or CUDA binding; does not perform training/--execute/validation/final/hedging; does not rewrite history of `c937742`.

## 9. Required next action

Next task MUST independently audit Amendment 043 only (read-only) before any execution task exists. Authorization remains `VALIDATED_BUT_RECORD_REPAIR_PENDING_AUDIT` until audit.

---
*Amendment 043 supersedes ONLY the erroneous authorization SHA-256 `29d11cf53da65429327623ec1211b9b7b35b46e5cf7025d53a47d7f3e7fe49c2` in Amendment 042 section 2.1; the correct FILE_SHA256 is `bc68789426a032f8ee80f1ef08b31e9eb5f59c518fefb0e20bfce0d37bc021de` (blob `d77766320792c459df7566cdcf6ec12806e0da91`, commit `c937742b02be6f4a22e11fa5b1e61054addde076`). No authorization bytes changed.*
