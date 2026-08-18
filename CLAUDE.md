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

## AI-assisted repository workflow

- At session start capture Git truth (`git branch --show-current`,
  `git rev-parse HEAD`, `git status --short --untracked-files=no`), read
  `docs/engineering/agent-contract.md`, read `.agent-memory/state.json` when
  present, and read the durable research entry point
  (`reports/protocol/research_protocol_v1.md` and its amendments). Inspect only
  files relevant to the active task; do not reread the whole repository.
- Treat Git, tests, immutable artifacts, and the governing research protocol as
  stronger evidence than any agent memory.
- For non-trivial work follow `DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT`
  and return the standard evidence report defined in
  `docs/engineering/agent-contract.md`.
- Do not perform unauthorized paid-data, provider, network, credential, remote,
  destructive-Git, production, or scientifically material actions. Classify
  every task's risk per `docs/engineering/agent-contract.md` (R0-R5) and never
  silently downgrade a task.
- Keep `.agent-memory/` concise, operational, and secret-free.
