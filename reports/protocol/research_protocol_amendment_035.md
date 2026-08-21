# Amendment 035 — CUDA Runtime Version and Execution-Identity Correction

**Date:** 2026-08-21
**Task:** NM-R4-GPU-RUNTIME-IDENTITY-REPAIR-050
**Risk:** R4
**Prior:** NM-R4-GPU-RUNTIME-ENABLEMENT-049 / Amendment 034

## Findings

- Task 049 successfully enabled the RTX 4070 CUDA hardware path (driver 610.47, 8188 MiB, CC 8.9).
- Task 049 installed `torch==2.8.0+cu128` in `.venv-gpu`.
- Independent review found official PyTorch 2.13 CUDA packaging exists. Verified at
  `https://download.pytorch.org/whl/torch` (and per-CUDA indexes):
  `torch-2.13.0+cu126`, `+cu130`, `+cu132` wheels for `cp311-win_amd64` all published.
  `cu128` for 2.13 does not exist; `cu126/cu130/cu132` do. 2.13 was incorrectly
  claimed unavailable in 049.
- Selected **cu132** as newest official CUDA variant compatible with driver 610.47
  (CUDA UMD 13.3) and Windows/Python 3.11/x86_64. Installed via
  `pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu132`.

## Environments after correction

- `.venv` (CPU, historical): **untouched** — Python 3.11.9, `torch==2.13.0+cpu`,
  `torch.version.cuda is None`, `cuda_available False`.
- `.venv-gpu` (CUDA): **recreated cleanly** — Python 3.11.9, `torch==2.13.0+cu132`,
  `torch.version.cuda 13.2`, cuDNN 92000, `cuda_available True`.
  `numpy==2.4.6` in both envs (matches `numpy>=1.26,<3.0` contract; no opportunistic upgrade).
  `pip check` clean in both.

## Scientific hash invariant

- `V5ExperimentConfig.config_hash` unchanged (device not in scientific hash).
  Existing seed-01..04 artifacts, checkpoints, reports, gate, and runner remain byte-identical.

## Runtime identity (new)

- New module `src/neuralmarket/core/runtime_identity.py` defines
  `RUNTIME_IDENTITY_SCHEMA = runtime-identity-v1`.
- Payload fields (deterministic, stable):
  `schema_version, python_version, torch_version, requested_device, resolved_device,`
  `cuda_runtime_version, cudnn_version, gpu_name, gpu_compute_capability,`
  `deterministic_algorithms, cudnn_benchmark, cudnn_deterministic, nvidia_driver_version`
  (when available). Excludes PID, timestamps, free VRAM, temp paths.
- `runtime_identity_sha256` = SHA-256 over canonical JSON of the payload sans the hash itself.
- Observed identities (post-repair, both drivers report 610.47):
  - `.venv` CPU: `f91d94b7f1a7c6f41ec667d780004327a2123666c64120a353bca9a45396a31e`
    (`2.13.0+cpu`, no CUDA runtime, no GPU name)
  - `.venv-gpu` requested `cpu`: `179f53e06c6d0181d9d034bb914367ab50c3b38e67ecd37363eeedd5a4c5cc5a`
    (`2.13.0+cu132`, CUDA 13.2)
  - `.venv-gpu` requested/resolved `cuda`: `35d07adc53bebe974457f2e87e8af0b4ff9d3f0cb19791f6370f8cf98d82ffbd`
    (same package, but `requested=res cuda`)
  CPU and CUDA identities are distinct; identical inputs are deterministic.
- Fail-closed: `resolve_device("cuda")` and `assert_cuda_runtime_or_fail("cuda")`
  raise `RuntimeError` when CUDA unavailable; no silent CPU fallback.
  `cpu` remains `cpu` even when CUDA exists. Checkpoint portability via `map_location`.

## Integration rule (prepared, not yet enforced on historical authorizations)

- Future governed executions must record both `scientific_config_hash` and
  `runtime_identity_sha256` in manifests/evidence.
- CUDA-authorized execution must have `requested_device=cuda, resolved_device=cuda`
  and a CUDA runtime identity; mismatch refuses before scientific start.
- Existing frozen seed-02/03/04 authorization files are **not** modified in this task;
  seed-05 remains `NOT_AUTHORIZED`.

## Verification (no training)

- CUDA tensor matmul on `cuda:0` + `synchronize` OK; `StructuredVolatilityNeuralSde`
  on `cuda:0` + `simulate_structured` forward OK (`ctx cuda:0 -> out cuda:0 (4,63)`).
  All tensors/models on `cuda:0`. Peak VRAM ~8 MB. GPU RTX 4070 Laptop, CC 8.9, 8585 MB.
- Device/runtime tests (CPU + GPU envs): 21 passed.
- No `train_internal_v3`, no Gate-v2, no dataset experiment, no seed-05.

## Governance

No scientific training, no seed-05, no reserve/validation/external/final/hedging.
No claim that CPU and GPU numerics are identical; hardware not claimed interchangeable.
