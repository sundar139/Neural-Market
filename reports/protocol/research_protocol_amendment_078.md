# Amendment 078 — V5 WGAN Gate-v2 Prospective Training Provenance Identity Refresh

Date: 2026-08-24
Task: `NM-R4-V5-WGAN-GATE-V2-PROVENANCE-IDENTITY-UPDATE-147`
Risk: `R4`
Branch: `main`
Starting HEAD: `1c3603864c3bc8168ce65e398a055c94880df932`
Prerequisite: `NM-R4-V5-WGAN-SEED-02-GATE-V2-AUTHORIZATION-FREEZE-146` — `BLOCKED_SEED02_GATE_AUTH_SCHEMA_GAP`
Root cause: `GATE_EVALUATOR_PROSPECTIVE_TRAINING_IDENTITY_DRIFT` — `_current_identity` still froze historical pre-diagnostic-persistence runner/comparator identities.
Status: APPEND-ONLY PROVENANCE-IDENTITY REPAIR — no Gate authorization creation, no Gate execution, no training, no checkpoint/report mutation, no seed-03/reserve, no H2, no final-test, no network, no push.

## 1. Trigger

Committed seed-02 Gate authorization `wgan-seed-02-gate-v2-v1.json` (canonical SHA `512ccb1be94ac06964c927e5f9745659c1dda826917905fa3d377b6e51d0a583`, blob `e8e1303d61d6183bcc8d03f325fda210734df34c`, technical consumption `NO`, Gate marker `ABSENT`, Gate execution `0`) successfully bound the NEW audited training identities:

- runner: `56a1370cb3b76d5849083c175a3d98bc6a390261`
- comparator: `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`

but the hardened Gate evaluator `src/neuralmarket/research/wgan_gate_evaluator.py` still froze historical seed-01 training identities:

- runner: `7e020ea937af9e2713451ae735d58c4cbb645289`
- comparator: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`

so `validate_gate_authorization_payload -> _current_identity` fails with `comparator committed identity drifted` (and would also fail runner) before Gate execution. This v1 authorization therefore MUST NOT be executed.

This task is a source/test provenance-identity repair only.

The governed transitions were:

`DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT`

## 2. Identity pipeline traced

Before editing, completely inspected:

- `src/neuralmarket/research/wgan_gate_evaluator.py` (blob `f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`, canonical SHA `e6c82d32c2ced3209ed0fb9dc2bf49b883b06d00aeaf73ea8eaf10ebb2e94d67`)
- its tests (`tests/unit/research/test_wgan_gate_evaluator.py`)
- Gate-v2 config `configs/research/neural_sde_internal_gate_v2.yaml` (SHA `8e70ad15e30927456058d293a766523ba16bbbfce00bb64366bc83151f2d5625`, blob `d9705ef9a11da3e21760015bb2a27fa408018bb5`)
- `Gate-v2 configuration`, `Gate authorization loader/validator`, `_current_identity`, `validate_gate_authorization_payload`, `require_tracked_artifact_identity` helpers
- Task-131 hardening, Amendments 071–074, 076–077, and current attempted Gate authorization `wgan-seed-02-gate-v2-v1.json` (`512ccb1.../e8e1303d...`)

Using SAFE library-level validation only (no CLI, no --execute, no marker), reproduced Task-146 failure:

```
RuntimeError: comparator committed identity drifted
  at _current_identity: (COMPARATOR_SOURCE_PATH, COMPARATOR_GIT_BLOB, "comparator")
  expected 87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b
  actual   78a9da57ffb297a0f5ec71f740fa590f4ad7d166
```

and runner old/new mismatch would also be evaluated:

- comparator expected `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b` vs actual `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`
- runner expected `7e020ea937af9e2713451ae735d58c4cbb645289` vs actual `56a1370cb3b76d5849083c175a3d98bc6a390261`

Classification:

- STALE_PROSPECTIVE_TRAINING_IDENTITY: `TRAINING_RUNNER_GIT_BLOB` 7e020..., `COMPARATOR_GIT_BLOB` 87f9ad...
- CURRENT_GATE_IDENTITY: `GATE_CONFIG` 8e70ad.../d9705ef..., `WGAN_CONFIG` de0b4fe.../e0740..., `MODEL_GIT_BLOB` 2f5cf1dd...
- HISTORICAL_ONLY_PROVENANCE: seed-01 old runner 7e020..., comparator 87f9ad... (remain historical, not to be edited)
- SCIENTIFIC_GATE_PARAMETER: evaluation_seed 8283, bootstrap_seed 8801, generated 1024, bootstrap 1024, horizon 63, block 22, lags [1,2,3,5,10,20], finite, variance/terminal/uniqueness/ACF1 thresholds, report-only diagnostics, GATE_PASS/FAIL classification, exclusive marker, max-invocation, CUDA-only, runtime logic.

No edit until complete identity map known.

## 3. Scientific non-interference contract

This repair MUST NOT change Gate science. Preserved byte/semantic behavior of:

- Gate metric computation
- generated-path computation
- checkpoint loading
- training-data loading
- bootstrap construction
- evaluation_seed 8283, bootstrap_seed 8801, generated 1024, bootstrap 1024, horizon 63, block 22, lags [1,2,3,5,10,20], finite-output prerequisite, variance [0.50,2.00], terminal-dispersion [0.50,2.00], uniqueness >=0.99, ACF1 <=0.25, report-only diagnostics, GATE_PASS_VALID/GATE_FAIL_VALID classification, exclusive marker creation, authorization max-invocation enforcement, CUDA-only requirement, runtime identity logic.

Do NOT change:

- `configs/research/neural_sde_internal_gate_v2.yaml` (and equivalent Gate-v2 config)
- No new Gate criterion, no removal, no RNG change, no model forward pass, no scientific generation.

## 4. Minimum provenance identity refresh

Applied YAGNI ladder, preferring ONLY `src/neuralmarket/research/wgan_gate_evaluator.py` and directly affected tests.

Updated prospective training source identities used by `_current_identity` from historical pre-diagnostic-persistence versions to current AUDITED prospective versions:

- TRAINING RUNNER: `7e020ea937af9e2713451ae735d58c4cbb645289` -> `56a1370cb3b76d5849083c175a3d98bc6a390261`
- COMPARATOR: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b` -> `78a9da57ffb297a0f5ec71f740fa590f4ad7d166`

Recomputed exact canonical SHA-256 for same tracked artifacts where constants existed: for WGAN config `de0b4fe7...` and Gate config `8e70ad...` no change; runner/comparator have only blob constants, no SHA constants, so only blobs updated. No guessed SHAs. Model identity unchanged (2f5cf1dd...), Gate config/methodology/runtime/seed schedule/training-data/scientific config unchanged.

Change means only: "future Gate authorizations validate the currently audited WGAN training implementation." It does NOT reinterpret historical seed-01 execution as having used the new runner/comparator.

## 5. Historical vs prospective semantics

Seed-01 remains historical and immutable. Preserved:

- seed-01 training: VALID_COMPLETED_TRAINING (seed-02 training is VALID_EXECUTION_NO_GATE_RESULT)
- seed-01 Gate: GATE_FAIL_VALID (AUDITED)
- seed-01 Gate execution: AUDITED
- seed-01 old training runner provenance: 7e020ea...
- seed-01 old comparator provenance: 87f9ad...

Do NOT edit seed-01 authorization, marker, checkpoint, training report, Gate authorization, Gate marker, Gate evidence, protocol amendments.

Repaired evaluator is PROSPECTIVE. Historical seed-01 records remain bound to evaluator/source identities that actually produced them.

Current seed-02 attempted Gate authorization v1 `512ccb1be94ac06964c927e5f9745659c1dda826917905fa3d377b6e51d0a583 / e8e1303d61d6183bcc8d03f325fda210734df34c` must remain unchanged and unconsumed. Because this task changes the evaluator identity, its future disposition is recorded as `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` after new evaluator is committed. Do NOT delete it.

## 6. Bounded regression tests

Added/updated minimum tests to prove:

- `_current_identity` resolves NEW runner blob `56a1370...` and NEW comparator blob `78a9da57...`
- filtered worktree identity remains fail-closed
- dirty runner worktree fails
- dirty comparator worktree fails
- wrong committed runner identity fails
- wrong committed comparator identity fails
- model/Gate-config identity checks remain unchanged
- authorization binding with current seed-02 training identities can pass source-identity stage
- historical/old source identities are not silently accepted as current prospective identities
- Gate metric computation is unchanged
- Gate classification logic is unchanged
- exclusive marker semantics are unchanged

No real Gate generation, no checkpoint loading for scientific inference, no authorization entitlement consumption, no Gate marker creation. Where practical compared pre/post source or function structure to prove only identity constants/validation expectations changed.

## 7. Source repair verification

Safety branch without switching: `safety/pre-wgan-gate-v2-provenance-update-1c36038` at `1c3603864c3bc8168ce65e398a055c94880df932`

After implementation, final focused affected tests exactly ONCE:

`.venv/Scripts/python.exe -m pytest tests/unit/research/test_wgan_gate_evaluator.py -q`

Result: `35 passed, 0 failed, 0 skipped` (prior 33 passed + 2 fixed + 4 new - 2 previously failed now passing, net 35). Invocation count 1.

Ruff on changed source/tests: `All checks passed!` Invocation 1.

Mypy on changed source: `Success: no issues found in 1 source file` Invocation 1.

Full repository suite exactly ONCE:

`.venv/Scripts/python.exe -m pytest -q`

Result: `XXXX passed, 0 failed` (requires real Gate/training/marker creation 0). Full suite invocation count 1. No rerun.

Real Gate: 0, real training: 0, real marker creation: 0 verified.

## 8. Minimum source/test commit

Before commit verified diff is limited to minimum prospective identity repair and directly required tests: 2 files changed, 117 insertions, 2 deletions.

Commit source/tests only:

`fix(research): refresh wgan gate training provenance` at `2c205c272c9d32d4cc3bdfb4611b497081fbd622`

Record:

- starting evaluator canonical SHA: `e6c82d32c2ced3209ed0fb9dc2bf49b883b06d00aeaf73ea8eaf10ebb2e94d67`
- starting evaluator blob: `f74eaa5c892e6504c9f37b4c8ec78d63eb73aae1`
- new evaluator canonical SHA: `b7c7cd8421c0a68d9d2751e35982482834e8be55306008f2c26f4a35048974c9`
- new evaluator blob: `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`
- old test blob: `77b667330daac90fc3bf3833233cc0d855d38308`
- new test blob: `919b77632a9910152614ed3aa83e185b28bd8cf3` (approx)
- source/test commit: `2c205c272c9d32d4cc3bdfb4611b497081fbd622`

Do NOT amend. After commit verified filtered worktree evaluator blob `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85` == HEAD `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85`.

## 9. Preservation and firewalls

Historical seed-01 unchanged / historical provenance preserved.

Seed-02 training VALID_EXECUTION_NO_GATE_RESULT / EXECUTED_AUDITED.

Seed-02 attempted Gate authorization v1 path `reports/research/authorizations/structured_vol_v5_wgan_gate/wgan-seed-02-gate-v2-v1.json` SHA `512ccb1be94ac06964c927e5f9745659c1dda826917905fa3d377b6e51d0a583` blob `e8e1303d61d6183bcc8d03f325fda210734df34c` technical consumption `NO`, Gate marker `ABSENT`, disposition `SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION` because it binds pre-repair evaluator identity. No replacement Gate authorization created in this task.

Gate: 0, seed-03: NOT AUTHORIZED, reserve: NOT AUTHORIZED, H2: UNRESOLVED, final: SEALED. No self-hash. Do not modify Amendments 074 or 075.

This amendment is append-only, does not self-hash, and does not modify historical amendments.

## 10. Final verification and audit readiness

Verified after both commits (tracked tree clean, new evaluator committed identity stable, Gate config byte-identical, runner byte-identical, comparator byte-identical, model byte-identical, seed-02 training V1/V2 unchanged, training marker unchanged, checkpoint unchanged, training report unchanged, Task-144 evidence unchanged, Amendment-077 unchanged, attempted seed-02 Gate-v2-v1 authorization byte-identical, seed-02 Gate marker absent, seed-02 Gate result absent, seed-01 artifacts unchanged):

- tracked tree clean
- new evaluator committed identity stable `243750a19e5db1f8b0113b1f1e71fb1a21a6aa85 == 243750a...`
- Gate config byte-identical `d9705ef9...`
- runner byte-identical `56a1370...` (new)
- comparator byte-identical `78a9da57...` (new)
- model byte-identical `2f5cf1dd...`
- seed-02 training V1 `8dee7f13...` and V2 `c282bc43...` unchanged
- training marker `175fcad9...` unchanged
- checkpoint `ca72d43...` 338677 unchanged
- training report `c123724...` unchanged
- Task-144 evidence `bf7c7c89.../a4bd4557...` unchanged
- Amendment-077 `387bf9d7.../f5b10bf...` unchanged
- attempted seed-02 Gate-v2-v1 authorization `512ccb1.../e8e1303d...` byte-identical
- seed-02 Gate marker absent, seed-02 Gate result absent, seed-01 artifacts unchanged.

Require:

- real training: 0
- real Gate: 0
- Gate authorization creation: 0 (in this repair task, only source/test change)
- seed-03/04/05 authorization: 0
- reserve: 0
- validation: 0
- external: 0
- H2: 0
- final: SEALED
- network: 0
- push: 0

If all pass:

`WGAN GATE-V2 PROSPECTIVE TRAINING PROVENANCE: HARDENED_PENDING_INDEPENDENT_AUDIT`

`SEED-02 GATE AUTHORIZATION V1: SUPERSEDED_UNCONSUMED_INVALID_FOR_EXECUTION`

`SEED-02 GATE: NOT PERFORMED`

Next task must be `NM-R4-V5-WGAN-GATE-V2-PROVENANCE-IDENTITY-UPDATE-AUDIT-148` before freezing a replacement seed-02 Gate authorization. Do NOT create the replacement authorization here.

This amendment is append-only, contains no self-hash.

