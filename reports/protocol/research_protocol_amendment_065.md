# Amendment 065 — V5 WGAN Runner Authorization-Path Repair

Date: 2026-08-23
Status: APPEND-ONLY REPAIR RECORD

## Task and trigger

- Task: NM-R3-V5-WGAN-RUNNER-AUTHORIZATION-PATH-REPAIR-118
- Risk: R3
- Starting branch: main
- Starting HEAD: 132462107ccefa9c1605be1de3430b1d382bd09c
- Prerequisite audit: NM-R5-V5-WGAN-SEED-01-EXECUTION-AUDIT-117
- Prerequisite verdict: PRELAUNCH REFUSAL CONFIRMED — NO SCIENTIFIC EXECUTION OCCURRED
- Trigger: Task-116 prelaunch refusal and Audit-117
- Repair scope: authorization-path normalization only

## Defect reconstruction

The Task-116 command supplied the repository-relative path:

`reports/research/authorizations/structured_vol_v5_wgan_training/wgan-seed-01-v1.json`

The containment guard in the pre-repair runner succeeded because it evaluated:

`path.resolve().relative_to(REPO.resolve())`

The actual failure occurred in the next check, `_is_tracked(path)`, where the
unresolved relative path reached `path.relative_to(REPO)` with a relative path
against an absolute repository path. The same unresolved path could flow into
`_is_tracked`, `_git_head_blob`, `_is_clean`, `_git_blob`, and file reading.

- Defect classification: RUNNER_RELATIVE_AUTHORIZATION_PATH_NORMALIZATION_DEFECT
- Containment check itself: PASSED before repair
- Actual failing helper: `_is_tracked`
- Actual failing operation: `path.relative_to(REPO)` on unresolved relative path
- Authorization validation reached: NO
- Marker boundary reached: NO
- Scientific boundary reached: NO

## Repair

The authorization-loading boundary now normalizes exactly once:

1. Resolve the repository root.
2. Interpret a relative candidate as `repo / path`.
3. Resolve the candidate.
4. Verify `candidate.relative_to(repo)`.
5. Reuse the normalized candidate for tracking, HEAD blob, clean-state, Git blob,
   and file-reading checks.

No helper-by-helper patches, dependency, abstraction, or fail-closed guard
weakening was introduced.

- Relative-path handling: accepted when it resolves inside the repository
- Absolute-path handling: accepted when it resolves inside the repository
- Containment method: `Path.resolve()` plus `Path.relative_to()`; no string-prefix check
- Normalized candidate reused by: `_is_tracked`, `_git_head_blob`, `_is_clean`, `_git_blob`, and file reading
- Absolute outside repository: rejected
- Relative `../` traversal: rejected
- Symlink escape: rejected when the symlink resolves outside the repository
- Windows case behavior: supported naturally; an uppercase case-variant path resolves to the canonical existing Windows path and is accepted
- New dependencies: none

Existing tracked, committed, clean/equal-to-HEAD, schema, identity, permission,
CUDA, invocation, marker, and authorization-consumption semantics are unchanged.
`full_config_hash` and `execution_recipe_head` behavior are unchanged.

## Implementation identities

- Old runner blob: 2e87199a2237b4f23576fa181a38ba29807c8ae2
- New runner blob: 5e501140026eb004b5bc8e477f9ab44d549fd44f
- Old focused test blob: a9d63e669882755d4709c960425388a166d877b9
- New focused test blob: cb12c6540bc7530094c0ff2c263ac14a3fc8d621
- Repair commit: 755750a03455ea7213a98aa614408a7e74a74949

The repair commit changes only:

- `src/neuralmarket/research/wgan_runner.py`
- `tests/unit/research/test_wgan_runner.py`

## Regression verification

The focused runner test command was run exactly once after repair:

`.venv/Scripts/python.exe -m pytest tests/unit/research/test_wgan_runner.py -q`

Result: 19 passed, 0 failed, exit code 0.

The red pre-repair run failed the new relative-path and protection tests,
including the original unresolved-relative-path failure, confirming the tests
would detect the old runner behavior.

Additional static checks:

- Ruff: PASS
- mypy: PASS; no issues in `wgan_runner.py`
- `git diff --check`: PASS

No test invoked `--execute`, the scientific runner CLI, scientific training,
market-data loading, Gate, H2, validation, external validation, or final test.

## Authorization and scientific state

- WGAN seed-01 authorization v1: technically UNCONSUMED
- WGAN seed-01 authorization v1 governance state: EXHAUSTED
- WGAN seed-01 authorization v1 reusable: NO
- Authorization SHA-256: 8d889457b48e20b81bd2ef841cd347b1ecd9d79df48d789a03d1ea7c05ac02e8
- Authorization Git blob: c5e234e5a8efc31f9c882ba451c25d98a606ba9c
- New authorization required after independent repair audit: YES
- Authorization creation: 0
- Authorization mutation: 0
- Scientific execution: 0
- Marker: 0
- Checkpoint: 0
- H2: UNRESOLVED
- Final: SEALED
- Push: 0

Amendment 064 was not modified. No authorization v2 was created. No seed-02
authorization was created.

This amendment is append-only and intentionally does not self-hash. Its own
SHA-256 and Git blob are recorded only after commit in the governed report or
later append-only provenance.
