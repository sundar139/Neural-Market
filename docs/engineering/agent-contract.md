# Agent Engineering Contract

This contract governs AI-assisted repository work. It is intentionally small and should be reused rather than repeated in every prompt.

## Source of truth

1. Git is the source of truth for repository state.
2. Read the repository's `AGENTS.md` and this contract before mutating files.
3. Read `.agent-memory/state.json` when present for hot operational state.
4. Durable decisions belong in the project's existing architecture/protocol/decision records, not in chat transcripts.
5. Never treat agent memory as stronger evidence than repository state, tests, or immutable experiment artifacts.

## Required execution order

For non-trivial work, follow:

DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT

Do not edit while root cause or runtime flow is still uncertain.

## Minimal-change rule

Use this order:

YAGNI -> existing helper/pattern -> standard library -> native platform feature ->
already-installed dependency -> smallest local change -> new abstraction only when necessary.

Prefer deletion over addition and boring code over clever code.

## Scope

Before mutation, state:

- task objective
- risk class
- starting branch and HEAD
- files/runtime paths that must be inspected
- files expected to change
- protected invariants
- explicit stop conditions

Do not modify unrelated files or perform opportunistic cleanup.

## Risk classes

| Class | Meaning | Minimum gate |
|---|---|---|
| R0 | Read-only inspection / explanation | Evidence only |
| R1 | Isolated low-risk code or docs | Targeted tests |
| R2 | Cross-module behavior / architecture | Full relevant tests + independent review when material |
| R3 | External state, paid data, credentials, network mutation | Preflight + budget/authorization + independent review |
| R4 | Scientific method, dataset split, labels, metrics, experiment protocol | Reproducibility + provenance + independent scientific validation |
| R5 | Destructive/irreversible production or external action | Explicit human authorization immediately before action |

A task may be promoted to a higher class during discovery. It must never be silently downgraded.

## Stop states

The following are valid successful outcomes:

- IMPLEMENTED
- VALIDATED
- BLOCKED
- NEEDS_DECISION
- NEEDS_EXTERNAL_ACTION
- SCIENTIFICALLY_INCONCLUSIVE

Never guess merely to avoid a stop state.

## Git safety

- Capture starting branch, HEAD, and tracked status.
- Do not use destructive Git operations unless explicitly authorized.
- For R3-R5 work, require a known-good checkpoint and follow the repository's safety-branch policy.
- One commit should represent one coherent hypothesis/change.
- Do not mix refactors or cleanup into a functional repair unless required.

## External effects

Before any network, paid-data, credential, remote mutation, or production action, report:

- exact operation
- estimated/known cost
- destination/vendor
- expected mutation
- rollback/recovery path
- authorization requirement

Fail closed when authorization or provenance is ambiguous.

## Verification

Verification must test the claimed behavior, not merely execute the code.

Return exact commands and outcomes. Distinguish:

- targeted validation
- regression validation
- static checks
- reproducibility/provenance checks
- hosted/remote checks not actually executed

Never report an unexecuted check as passing.

## Evidence report

At completion return:

START
- branch
- HEAD
- tracked status

TASK
- objective
- risk class
- stop conditions

DISCOVERY
- root cause / actual flow
- evidence supporting it

CHANGE
- files changed
- why each change was necessary

VALIDATION
- exact command -> exact result
- failures and their interpretation

INVARIANTS
- preserved
- intentionally changed

EXTERNAL EFFECTS
- network
- cost
- external mutation

FINAL
- branch
- HEAD
- tracked status
- outcome

RESIDUAL RISK
- remaining uncertainty

NEXT ACTION
- exactly one recommended next action, or NONE

## Memory

`.agent-memory/` is hot, ignored operational memory. Keep it concise.

Durable architectural, methodological, security, budget, and recovery decisions must be written to the repository's existing durable records when they materially affect future work.

Do not store secrets. Store only environment-variable names or secret-manager references.
