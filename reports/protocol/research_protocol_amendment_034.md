# Amendment 034 — CUDA Runtime Enablement

**Date:** 2026-08-21
**Task:** NM-R4-GPU-RUNTIME-ENABLEMENT-049

## Status
Historical CPU lineage (seed-01/02/03/04) remains frozen on `2.13.0+cpu`;
`.venv-gpu` adds `2.8.0+cu128` for future work. No existing checkpoint/report
bytes changed; no training executed in this task.

## Environments
- `.venv` (CPU): Python 3.11.9, `torch==2.13.0+cpu`, `torch.version.cuda is None`, `cuda_available False`. Preserved, not modified.
- `.venv-gpu` (CUDA): Python 3.11.9, `torch==2.8.0+cu128`, `torch.version.cuda 12.8`, cuDNN 91002, `cuda_available True`, `device_count 1`.
  Hardware: NVIDIA GeForce RTX 4070 Laptop GPU 8188 MiB (WDDM, CC 8.9), driver 610.47 / KMD 610.47, CUDA UMD 13.3, VRAM 8187 MB.
  OS: Windows 11 Home 10.0.26200.0, Win x64. Wheel: official `https://download.pytorch.org/whl/cu128`, bundles CUDA runtime (no Toolkit install).

## Device semantics
`src/neuralmarket/core/device.py:resolve_device("cpu"|"cuda")` — single `torch.device` propagated.
`requested=cpu → cpu`; `requested=cuda` with `cuda unavailable → RuntimeError fail-closed, no CPU fallback`.
`requested=cuda` with `torch.version.cuda is None → RuntimeError`.
Historical/default config without `device` attr → `cpu` (V5ExperimentConfig frozen hash unchanged).
Checkpoint helper `load_checkpoint_state(..., map_location)` for CPU/GPU portability.

## Determinism
`configure_determinism(True)` + `configure_device_determinism(device)` sets
`torch.use_deterministic_algorithms(True, warn_only=False)`, `cudnn.benchmark=False`, `cudnn.deterministic=True`.
CUDA seeding via `torch.cuda.manual_seed_all` where relevant. If a future CUDA op requires `CUBLAS_WORKSPACE_CONFIG`, it will be documented rather than silently disabling determinism.

## Research wiring
`structured_vol_experiment.py` now resolves `getattr(config, "device", "cpu")` through `resolve_device`; default remains `cpu` so seed-01..04 lineage is byte-identical. Future experiments must explicitly state `device: cuda` in execution identity if they intend GPU.

## Verification
CUDA tensor test `a.to(cuda) @ b.to(cuda)` on `cuda:0` passed; `get_device_properties(0)` reported above.
Smoke without training: `StructuredVolatilityNeuralSde` on `cuda` forward OK; peak VRAM ~few MB.

## Governance
No seed-05, no reserves, no validation/external/final/hedging training in this task.
Future family mixing CPU/GPU inside a frozen replicate family requires separate governed methodological decision.
