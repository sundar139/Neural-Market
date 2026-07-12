# Repository Standards

## Layout

- `src/neuralmarket/` — the installable package (src layout).
- `configs/` — typed, path-free configuration files.
- `reports/` — research protocol and generated (ignored) environment reports.
- `docs/engineering/` — engineering conventions and reproducibility policy.
- `scripts/` — PowerShell bootstrap and verification helpers.
- `tests/` — `unit/` and `integration/` suites.

## Naming

Use professional, descriptive names. Do not use tutorial-style names such as
`phase`, `step`, `part`, `demo`, `toy`, or `practice` for project artifacts.

## Code quality

- All code is fully typed and passes strict mypy.
- Public interfaces carry useful docstrings.
- Use `pathlib` for path operations and explicit UTF-8 encoding.
- Use the logging utilities, not `print`, for diagnostics.
- No import-time side effects and no mutable global configuration.
- No hardcoded machine-specific absolute paths in tracked files.
- No `TODO`, `pass`, or `NotImplementedError` placeholders in shipped code.

## Tooling

- Ruff for linting and formatting (line length 100, target Python 3.11).
- mypy in strict mode with zero errors.
- pytest with branch coverage, minimum 85%.
- pre-commit with detect-secrets for secret scanning.

## Verification

Run `scripts/verify.ps1` before every commit. It must pass end to end.
