# Amendment 066 — V5 WGAN Runner Authorization-Path Repair Completion

Date: 2026-08-23
Status: APPEND-ONLY REPAIR COMPLETION RECORD

## Task and trigger

- Task: NM-R3-V5-WGAN-RUNNER-MARKER-PATH-REPAIR-COMPLETION-120
- Risk: R3
- Starting branch: main
- Starting HEAD: 59d9392988dbb07a77a967ac6fb311ee0858e586
- Trigger: Audit 119 blocking finding 1
- Prerequisite: NM-R4-V5-WGAN-RUNNER-AUTHORIZATION-PATH-REPAIR-AUDIT-119
- Prerequisite verdict: REPAIR REQUIRED

## Chronology and residual defect

- Task 116: the repository-relative authorization path was refused in
  `_is_tracked` because an unresolved relative path reached
  `path.relative_to(REPO)`.
- Task 118: `_load_authorization` correctly normalized the path for its own
  tracking, committed-HEAD, clean-state, Git-blob, and file-reading checks.
- Audit 119: the caller-side `auth_path` retained by `main()` remained
  unresolved and continued to reach the marker boundary. Marker-payload
  identity construction evaluated `auth_path.relative_to(REPO)` again, so the
  original relative-versus-absolute `ValueError` remained possible. Because
  `report_dir.mkdir(parents=True, exist_ok=True)` ran before payload
  construction, the refusal could also leave an empty WGAN report namespace.

Classification: RUNNER_AUTHORIZATION_PATH_PROPAGATION_AND_PRE_MARKER_ORDERING_DEFECT.

## Completed repair

The final repaired runner establishes one authoritative normalized absolute
authorization path at the execution/readiness boundary in `main()` through the
private `_normalize_authorization_path(path: Path) -> Path` helper. The helper:

1. interprets a relative path beneath `REPO`;
2. resolves the candidate and repository;
3. enforces containment with `Path.relative_to()`; and
4. returns the canonical absolute path.

The normalized path is propagated through the complete caller/callee path into:

- `_load_authorization`;
- tracked, committed, clean, and byte-equal-to-HEAD authorization checks;
- `_exclusive_create_execution_started`;
- `_git_blob`;
- marker-payload identity construction;
- authorization-path serialization; and
- every later authorization-file operation.

No original relative authorization path remains available to later marker
logic, and normalization is not duplicated inside the authorization helpers.
The marker payload is fully prepared, including authorization-path
serialization and authorization Git-blob identity, before the report directory
is created. `report_dir.mkdir(parents=True, exist_ok=True)` now occurs only
after non-filesystem payload preparation succeeds. The existing temporary-file
and `os.link` exclusive marker operation is unchanged.

A controlled pre-marker payload failure now leaves no report directory, marker,
or scientific namespace. The relative and canonical absolute caller paths
reach the same marker payload identity, with the canonical repository-relative
authorization path in the payload.

## Security and platform preservation

The repair preserves:

- repository-relative authorization paths;
- repository-absolute authorization paths;
- rejection of absolute paths outside the repository;
- rejection of relative traversal escaping the repository;
- rejection of symlink escapes after `Path.resolve()`;
- tracked-artifact enforcement;
- committed-at-HEAD enforcement;
- clean and byte-equal-to-HEAD enforcement;
- authorization schema and identity validation;
- fail-closed member, seed, config, methodology, runner, implementation,
  contract, runtime, device, and permission checks; and
- Windows case behavior.

No string-prefix or `startswith` containment, manual path slicing, lowercase-only
containment, or validation bypass was introduced. Audit-115 hardening for
`full_config_hash`, `execution_recipe_head`, and `run_prefix` remains out of
scope and unchanged. No dependency was added.

## Regression verification

The focused in-process tests cover:

- relative authorization path through `main()` to the marker boundary;
- canonical absolute authorization path through the same boundary;
- canonical repository-relative marker-payload path identity;
- controlled payload refusal with no report namespace or marker; and
- no call to `execute_authorized_wgan` during these boundary tests.

The new relative marker-boundary regression fails against the Task-118
intermediate runner blob because the unresolved caller path still reaches the
marker serialization boundary. The final focused command was:

`.venv/Scripts/python.exe -m pytest tests/unit/research/test_wgan_runner.py -q`

Result: 22 passed, 0 failed, exit code 0.

No real runner CLI, scientific execution, market-data access, training,
simulation, checkpoint creation, marker creation, Gate, H2, validation,
external validation, final test, provider/scientific network, Git-remote
network, or push occurred.

## Implementation identities

- Old intermediate runner blob: 5e501140026eb004b5bc8e477f9ab44d549fd44f
- Final repaired runner blob: 7e020ea937af9e2713451ae735d58c4cbb645289
- Old focused test blob: cb12c6540bc7530094c0ff2c263ac14a3fc8d621
- Final focused test blob: b98f6d2eb8e8733226d1833bf10d63f6135c3876
- Repair commit: 78449c9a015a06233ee5a765b8a7fd2ee89d5d42

## Authorization and scientific state

- WGAN seed-01 authorization v1 technical consumption: UNCONSUMED
- WGAN seed-01 authorization v1 governance entitlement: EXHAUSTED
- WGAN seed-01 authorization v1 reusable: NO
- WGAN seed-01 authorization v1 SHA-256: 8d889457b48e20b81bd2ef841cd347b1ecd9d79df48d789a03d1ea7c05ac02e8
- WGAN seed-01 authorization v1 Git blob: c5e234e5a8efc31f9c882ba451c25d98a606ba9c
- Authorization v1 mutated: NO
- New v2 required after independent audit: YES
- Authorization v2: NOT CREATED
- Seed-02 authorization: NOT CREATED
- Scientific execution: 0
- Marker: 0
- Checkpoint: 0
- H2: UNRESOLVED
- Final: SEALED
- Push: 0

## Amendment 065 coverage clarification

This amendment prospectively clarifies, without modifying Amendment 065, that
Amendment 065 established normalization inside `_load_authorization` and
preserved its direct authorization checks, but did not prove propagation of the
normalized value from `main()` into the later marker boundary. Amendment 066
closes that caller-side coverage gap and records the end-to-end marker-boundary
regression and pre-marker ordering repair.

Amendment 064 and Amendment 065 were not modified. This amendment is
append-only and intentionally has no self-hash.
