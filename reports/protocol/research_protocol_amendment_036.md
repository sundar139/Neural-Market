# Amendment 036 — Governed CUDA Execution Path and Runtime-Bound Authorization

**Date:** 2026-08-21
**Task:** NM-R4-GPU-GOVERNED-EXECUTION-REPAIR-053
**Risk:** R4
**Branch:** main @ a781206275893b6baf4b088d74e4a6547c742e84
**Safety branch:** safety/pre-gpu-governed-execution-repair-a781206
**Prior:** Amendment 035 (CUDA runtime enablement + identity correction)
**Audits:** NM-R4-GPU-RUNTIME-IDENTITY-AUDIT-051 (REPAIR REQUIRED), NM-R4-V5-SEED-04-EXECUTION-AUDIT-052 (VALIDATED)

## 1. Findings (Audit 051)

- Audit 051 found the governed runner `structured_vol_v5_replicate_training_runner.py`
  hardcoded `torch.device("cpu")`, hardcoded `"device": "cpu"` in report evidence,
  did not call `run_v5_experiment`, did not import/use `runtime_identity`, and
  authorization preflight could not bind `requested_device`/`runtime_identity`.
- Audit 051 found the trainer `neural_sde_trainer_v3.py` (and v1/v2 family)
  created CPU `torch.Generator` instances and `torch.randn`/`torch.tensor`/
  `torch.full` without device propagation; CUDA execution would fail or silently
  mis-route storage.
- Seed-04 Audit 052 validated seed-04 CPU lineage as PRIMARY_VALID_COMPLETED
  with non-blocking findings — historical evidence remains admissible, no replay
  required. All seed-01..04 evidence remains byte-identical.

## 2. Old vs repaired runner

- **Old:** `_run_scientific_training` set `device = torch.device("cpu")` unconditionally,
  `training_returns_tensor = torch.tensor(..., dtype=dtype)` without device,
  report `device: "cpu"` hardcoded, no runtime identity capture, `execution_started`
  published before any device/runtime check.
- **New:** Runner enforces the prospective ordering:
  `load authorization → validate scientific identities → read requested_device
  → resolve_device(requested_device) → configure_device_determinism(resolved)
  → build_runtime_identity (single normative capture point) → compare observed
  resolved + sha vs expected → REFUSE if mismatch → only then publish
  execution_started → scientific invocation → checkpoint`. No silent fallback;
  CUDA requested but unavailable raises RuntimeError before marker.

## 3. Trainer device propagation

- Thread ONE resolved `torch.device` from runner into `_run_scientific_training`
  and `train_internal_v3` / `refit_final_v3` (kwarg `device`, defaulting to model
  device for backwards-compatible CPU tests). No scattered `.cuda()` calls.
- All load-bearing constructions now use the resolved device:
  `torch.Generator(device=device).manual_seed(seed)` via `make_generator`,
  `torch.randn(..., device=device, dtype=..., generator=...)`,
  `torch.tensor(..., device=device, dtype=...)`,
  `torch.randperm(..., device=device, generator=...)`,
  `torch.full(..., device=device, dtype=...)` where present,
  `model.to(device=device)`, and `fit/sel` tensors moved via `.to(device=device)`.
  Gate noise/tensors likewise propagate device.
- CPU behaviour unchanged; CUDA path uses CUDA generators and CUDA storage.

## 4. Authorization v2 (prospective)

- New file `reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json`.
- Extends v1 (`structured-vol-v5-primary-training-authorization-v1`) with:
  `requested_device`, `expected_resolved_device`, `expected_runtime_identity_sha256`
  (64 hex), optional `expected_runtime_identity_schema`.
- For GPU: `requested_device=cuda`, `expected_resolved_device=cuda`,
  `expected_runtime_identity_sha256=17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`
  (CUDA 13.2, torch 2.13.0+cu132, driver 610.47, RTX 4070 Laptop CC 8.9, determinism enabled).
- Fail-closed on: unknown schema, unsupported device, missing/malformed runtime identity,
  requested != expected_resolved, observed != expected. v1 must not contain v2 fields.
- No seed-05 GPU authorization created in this task; schema/parser/test fixtures only.
- Existing four authorization files (`v5-seed-02..05.json`) remain unchanged, byte-identical.

## 5. Runtime identity

- Schema `runtime-identity-v1` unchanged; payload is deterministic and excludes
  timestamps, PIDs, free/allocated VRAM, temp paths. `runtime_identity_sha256`
  is SHA-256 over canonical JSON of payload sans the hash itself.
- **Normative capture point:** after `resolve_device` and `configure_device_determinism`,
  before `execution_started`, before any scientific computation. Single point,
  not recomputed later. If driver version drifts, runtime identity drifts
  intentionally and requires a newly bound future authorization.
- Current identities at the normative capture point (determinism enabled):
  `.venv` CPU: `e0eea36aa13ef9859e7def50e2c966d0ec69ac90a9d43d5b0ceac16475445863`
  (`torch 2.13.0+cpu`, Python 3.11.9, driver 610.47);
  `.venv-gpu` CPU-requested: `4a3c836c3bb0a1b3d3f38dadd715eec1628175036952474f98a1907603bcacdd`
  (`torch 2.13.0+cu132`, CUDA 13.2);
  `.venv-gpu` CUDA: `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada`.
  Prior commit `a781206` recorded `35d07adc...` captured before deterministic flags;
  the normative value `17e3bb52...` now governs prospectively and is recorded here openly.

## 6. Execution evidence

- `execution_started.json`, `training_execution_manifest.json`, and `training_report.json`
  now record `requested_device`, `resolved_device`, `runtime_identity_sha256`,
  `runtime_identity` payload, and `runtime_identity_schema` for new v2 executions.
  Historical artifacts remain untouched.

## 7. Tests (no scientific training)

- New `tests/unit/research/test_v5_governed_cuda_execution_repair.py` (18 pass CPU,
  20 pass GPU): v1 remains CPU-only, v1 cannot request CUDA, v2 parses, missing/bad
  identity fails closed, requested/resolved mismatch fails closed, wrong runtime fails
  before marker, CPU env cannot satisfy CUDA, CUDA env satisfies bound synthetic auth,
  `execution_started` not created on mismatch, invocation counter stays 0, report fields
  not hardcoded, device propagates, CUDA generator on CUDA, randn/tensor/full on device,
  checkpoint portability intact, runtime identity deterministic, real CUDA smoke gated by
  `torch.cuda.is_available()` on synthetic data only (no markers, no governed path).

## 8. Preserved invariants

- Historical seed-01..04 evidence/reports/checkpoints byte-identical.
- `v5-seed-02..05.json` unchanged; no seed-05 GPU authorization; no training executed.
- Schedule, Gate-v2, model architecture, loss, hyperparameters, windowing, config hashes unchanged.
- No reserves/validation/external/final/hedging; no push; no amend/rebase/reset.

## 9. Governance

No scientific training, no seed-05 execution, no final test in this task.
Next governed action: independent Claude read-only audit of this repair.
