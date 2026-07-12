# Reproducibility

## Principles

Confirmatory results must be reproducible through versioned CLI commands and
configurations. Notebooks never contain authoritative implementations.

## Seeding

`neuralmarket.core.reproducibility.seed_everything` seeds Python's `random`,
NumPy, and PyTorch (when installed). The default research seed is `1337` and
comes from configuration, not from scattered literals. Bitwise GPU
reproducibility cannot be guaranteed; a warning is emitted when deterministic
mode is requested with CUDA present.

## Configuration

Reproducibility settings live in `configs/reproducibility/default.yaml` and are
validated by a typed Pydantic model. Malformed YAML and invalid values are
rejected loudly; there is no silent fallback. Each environment report records the
configuration's SHA-256 hash.

## Environment provenance

`neuralmarket environment check` collects a redacted snapshot: UTC timestamp,
package and Python versions, executable, platform, repository root, Git commit
and dirty status, configured seed, configuration hash, direct dependency
versions, and optional PyTorch/CUDA status. PyTorch and CUDA are treated as
intentionally deferred, not as failures. Environment-variable values are never
serialized — only whether supported variables are configured.

## Determinism boundaries

- CPU pseudo-random sequences are reproducible given a fixed seed.
- GPU kernels and multi-threaded reductions may not be bitwise reproducible.
- Any nonfinite loss, exploding path, data leakage, or accounting mismatch must
  halt work and be reported, per the research protocol.
