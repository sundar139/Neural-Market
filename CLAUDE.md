# NeuralMarket Development Rules

- Work only from the repository root.
- Use the project interpreter at `.venv/Scripts/python.exe`.
- Never install project dependencies globally.
- Use `python -m pip`, not bare `pip`.
- Do not recreate or delete `.venv`.
- Do not change dataset split manifests without explicit approval.
- Never use the final test set for debugging, model selection, or tuning.
- Add or update tests before modifying scientific logic.
- Run Ruff, mypy, unit tests, leakage tests, and relevant scientific tests
  after each implementation step.
- Do not silently discard failed experiments or seeds.
- Record all experiment configurations and dataset hashes.
- Do not commit API keys, raw licensed data, checkpoints, `.env`, or `.venv`.
- Stop and report any nonfinite loss, exploding path, data leakage, or
  accounting mismatch.
