# Amendment 037 — Project-Wide CUDA Scientific Execution Enforcement and Canonical Recipe

**Date:** 2026-08-21
**Task:** NM-R4-PROJECT-WIDE-CUDA-ENFORCEMENT-055
**Risk:** R4
**Branch:** main
**Starting HEAD:** 168d93b7e3db4490ab5ee0f557cfd505b0dfefdf (Amendment 036)
**Canonical recipe (old):** 20d90f7484fe5df7cd62755a5810c8de78e5e92f (runner blob 7b46e0f6c805687977cd685ebb97741bd4243cbe) — superseded prospectively
**Canonical recipe (new):** d970acb901afe35bbdf47995550b2b5e0144c20c
**Safety:** no amend of prior history besides the scoped code commit above; no rebase/reset/push
**Audits:** NM-R4-GPU-GOVERNED-EXECUTION-AUDIT-054 (REPAIR REQUIRED)

## 1. User policy

From this task forward, all future real scientific PyTorch compute in NeuralMarket must use CUDA
(`requested_device=cuda`, `resolved_device=cuda`, fail-closed on unavailability, no silent CPU fallback).
Historical CPU seed lineage remains immutable and byte-identical. The policy is "all scientific PyTorch
compute on CUDA; CPU only for intentional non-compute/portability/orchestration boundaries."

CPU MAY remain for: Python orchestration, filesystem/Git, JSON/YAML parsing, hashing, pandas/NumPy
preprocessing where no GPU tensor is intended, checkpoint serialization to portable CPU `state_dict` bytes,
explicit transfer of final metrics to CPU for NumPy/JSON reporting, historical evidence inspection.

## 2. Project-wide torch audit

Scanned `src/`, `reports/research/evidence/`, `tests/` for device/tensor factories per Section 3 pattern list.
Classified every hit into A-E (see task inventory). Findings:

- **Governed path (A):** `structured_vol_v5_replicate_training_runner.py` → `neural_sde_trainer_v3.py`
  (`train_internal_v3`/`refit_final_v3`) → `neural_sde_internal_gate.py` (`evaluate_gate_v2`) was
  the only reachable SCIENTIFIC_COMPUTE_MUST_BE_CUDA path. `evaluate_internal_gate_v3` is NOT called by
  the governed runner (prior error); `structured_vol_experiment.run_v5_experiment` is a non-governed entry
  point but now propagates device and remains gated by runner authorization.
- **Intentional CPU boundaries (B):** `*.detach().cpu().numpy()` for metrics/hashing, `v.cpu()` for
  checkpoint portability, `numpy` preprocessing, `canonical_dumps`/`json`/`yaml`, `torch.as_tensor(...,
  dtype=torch.float32)` for fitted statistics (standardizer internals), `map_location="cpu"` for
  checkpoint loading. All retained.
- **Historical/test-only (C):** `neural_sde_trainer.py`/`v2`, `neural_sde_experiment*.py` legacy loops,
  `structured_vol_v5_reproducibility_harness.py`, unit tests that construct CPU fixtures. Not mutated.
- **Dead/unreachable (D):** none load-bearing.
- **After repairs:** zero unexplained SCIENTIFIC_COMPUTE_MUST_BE_CUDA violations. WGAN/neural-CDE/hedging
  have no PyTorch code in `src/` today — marked NOT_CURRENTLY_EXECUTABLE.

## 3. Gate-v2 repair

`src/neuralmarket/research/neural_sde_internal_gate.py::evaluate_gate_v2`:

- New kwarg `device: torch.device | None` (backwards-compatible; falls back to model device).
- Device resolved once (`explicit > model params > sel_ctx > cpu`), model placed on device.
- Selection context/targets materialised on device; `selection_returns_real` kept detached on CPU.
- Gate generators use `make_generator(device, seed)` for `gate_seed` 7777 and `drift_diffusion_seed` 7778.
- Gate noise `torch.randn(..., device=device, generator=gate_gen)` and `gen_ctx` on device; model call on CUDA.
- `_drift_diffusion_rms` already device-aware (`noise` and `t` on `ctx.device`). Drift/diffusion diagnostic
  now uses device-aware generator.
- Bootstrap/sample_block_bootstrap and NumPy statistics remain deliberately on CPU after model outputs
  detached (intentional boundary). No threshold/seed/bootstrap/horizon change.

Governed runner now passes `device=device` to `evaluate_gate_v2`.

## 4. Other scientific repairs

- `signature_mmd.py::SignatureStandardizer.standardize` co-locates `means`/`stds` to `features.device`
  so CUDA features on `cuda:0` no longer clash with CPU-fitted statistics.
- `structured_vol_experiment.run_v5_experiment` propagates device through training returns, trainer,
  Gate, final refit, and simulation tensors (with `.cpu()` portability for checkpoint/metrics).

## 5. Authorization / runtime consistency

- Existing v1 authorizations (`v5-seed-02..05.json`) preserved byte-identical.
- Prospective v2 schema `reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json`
  enforces exactly 64 lowercase hex `expected_runtime_identity_sha256` (no silent uppercase normalization).
  Parser, schema, tests and docs now agree. Runner refusal restores the specific `check_authorization` error
  (`REFUSED: authorization: {e}`) rather than collapsing to `***`.
- Future real scientific execution requires `requested_device=cuda`, `expected_resolved_device=cuda`,
  bound `expected_runtime_identity_sha256`. No seed-05 v2 authorization created in this task.

## 6. Tracked test regressions

Fixed Audit-054 regressions:

- `test_mocked_success_exactly_once` / `test_mocked_failure_exactly_once` / `test_success_all_five_files`
  fakes now accept `*args, **kwargs` so the new `_run_scientific_training(..., device=...)` call succeeds.
- `test_allowed_member_dry_run` now exercises `v5-seed-05` (only primary without an existing replicate dir);
  `v5-seed-02` is already executed and would otherwise refuse on overwrite.
- New `tests/unit/research/test_project_cuda_paths.py` adds real CUDA-gated coverage:
  Gate-v2 synthetic on `cuda:0`, trainer v3 one-step synthetic on `cuda:0`, model simulation smoke.

## 7. Canonical recipe

Old recipe `20d90f7484fe5df7cd62755a5810c8de78e5e92f` contained old runner blob
`7b46e0f6c805687977cd685ebb97741bd4243cbe` and predated task 053+055 repairs.

**New prospective canonical recipe:** `d970acb901afe35bbdf47995550b2b5e0144c20c`

Blobs at that tree:

- runner: `b46a0f8459a61f6d7ead2e2c802daaebe0a3a036` (`reports/research/evidence/structured_vol_v5_replicate_training_runner.py`)
- trainer v3: `85aabc6798b22a60bd4d94d4ee86bfae81a8a172` (`src/neuralmarket/research/neural_sde_trainer_v3.py`)
- Gate-v2: `05af8d0d864eddaae8c43e1cc3936d28e89abaf3` (`src/neuralmarket/research/neural_sde_internal_gate.py`)
- auth-v2 schema: `c74958f2c5d99753b05bf64c9b6880ee9bd37d94` (`reports/research/structured_vol_v5_primary_training_authorization_schema_v2.json`)
- runtime-identity: `817ba53e2474c6e8dd7ecf15d64e0766e75f73e9` (`src/neuralmarket/core/runtime_identity.py`)
- signature_mmd: `5e0df0e27343ce0f52f6b5d8c9212ea1cc96b2a2` (`src/neuralmarket/models/signature_mmd.py`)

No modification of the old recipe commit; no rewrite of v1 authorizations.
Seed-05 v1 remains historically preserved but not authorized for future execution; no v2 created.

## 8. Verification

- Full unit suite `.venv`: 90 passed, 4 skipped, 0 failed (relevant suite inc. production integrity).
- Full unit suite `.venv-gpu`: 57 passed (targeted) / 3 passed gate/trainer/model smoke on `cuda:0`,
  peak VRAM ~10 MB; no silent fallback.
- `ruff` (changed Python, E/F) clean; `mypy` (changed strict-typed modules) clean;
  `pip check` clean both envs; `git diff --check` clean.

## 9. Governance

No scientific training, no governed --execute, no seed-05/reserve/validation/external/final/hedging.
GPU execution remains NOT AUTHORIZED until independent Claude audit validates task 055.
Next: independent Claude read-only project-wide CUDA audit; do not decide original-family vs new-CUDA-family here.
