# Contributing

## Environment

- Work only from the repository root.
- Use the project interpreter at `.venv\Scripts\python.exe`.
- Never install project dependencies globally; use `python -m pip`.
- Do not recreate or delete `.venv`.

## Workflow

1. Add or update tests before modifying scientific logic.
2. Make the change with full type annotations and docstrings on public APIs.
3. Run the full verification gate:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1
   ```

   Equivalent individual commands:

   ```powershell
   & .\.venv\Scripts\python.exe -m ruff check .
   & .\.venv\Scripts\python.exe -m ruff format --check .
   & .\.venv\Scripts\python.exe -m mypy src
   & .\.venv\Scripts\python.exe -m pytest -m "unit or integration" --cov=neuralmarket --cov-branch --cov-report=term-missing --cov-fail-under=85
   & .\.venv\Scripts\pre-commit.exe run --all-files
   ```

4. All checks must pass with zero skipped or xfailed tests and coverage at least
   85%.

## Rules

- Do not weaken tests, relax typing, lower coverage, or skip checks to get a pass.
- Do not change dataset split manifests without explicit approval.
- Never use the final test set for debugging, model selection, or tuning.
- Record all experiment configurations and dataset hashes.
- Do not commit API keys, raw licensed data, checkpoints, `.env`, or `.venv`.
- Stop and report any nonfinite loss, exploding path, data leakage, or
  accounting mismatch.

## Commits

Use conventional commit messages (for example `feat:`, `fix:`, `chore:`). Do not
push to a remote or create a GitHub repository as part of foundation work.
