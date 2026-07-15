# Research Protocol Amendment 009 — Stale-Checkpoint Resume and Metadata Deadline

## Status and unchanged scope

This amendment approves offline hardening of the guarded metadata-resume path. It
does not authorize a purchase, a real Databento call, a checkpoint execution, or
market-data acquisition. The frozen January 2019 request plan, datasets, schemas,
time windows, symbols, split boundaries, sealed final test, USD 5.00 total cap,
USD 1.00 per-request cap, `2**30` billing divisor, 1.25× derived margin, retry
eligibility, request timeouts, and provider method allowlist are all unchanged.

## Why the prior live milestone was infeasible

Two frozen-config facts made single-invocation completion impossible:

1. The production checkpoint was ~386 minutes old, far past
   `checkpoint_max_age_minutes: 30`. The CLI turned `metadata_checkpoint_expired`
   into a **silent fresh generation** — discarding the 16 completed endpoints and
   restarting all 75, re-issuing authenticated metadata requests.
2. `total_run_deadline_seconds: 540` (9 minutes) could not complete 59 pending
   endpoints given 120-second hard timeouts, two attempts, and the OPRA `cbbo-1m`
   504 history (each blocked cost can consume ~240 s before deriving).

## Explicit resume contract

`--resume` now means *resume this exact checkpoint or fail closed*. A missing,
unreadable, malformed, schema-invalid, hash-invalid, plan-incompatible, or stale
(unauthorized) checkpoint exits nonzero and **never** creates a fresh generation.
A fresh generation requires the ordinary non-`--resume` invocation.

A stale checkpoint may be resumed only with
`--allow-stale-checkpoint-sha256 <64-lowercase-hex>`, valid only with `--resume`.
The supplied hash must equal the SHA-256 of the exact checkpoint bytes before
parsing. It **bypasses the age window only**; JSON-schema, canonical checkpoint
hash, plan/source/split/policy hashes, request-specification hashes, endpoint
uniqueness and response-hash checks, and configuration compatibility all remain
mandatory. A malformed, uppercase, shortened, prefixed, or mismatching hash fails
before any provider construction. Completed endpoint records, response hashes, and
cost provenance are preserved; the runner renews `updated_at` normally on its
first atomic write (no metadata-free timestamp rewrite).

## Metadata run deadline

`configs/data/acquisition/pilot_january_2019.yaml` now sets
`total_run_deadline_seconds: 7200` (and the model bound was raised to match).
Rationale: worst case ≈ 21 OPRA `cbbo-1m` cost endpoints × 120 s × 2 attempts =
5040 s, plus bounded record-count/billable-size, child-startup, and persistence
overhead; 7200 s leaves margin. `hard_request_timeout_seconds`,
`maximum_timeout_attempts`, and `checkpoint_max_age_minutes: 30` are unchanged;
the normal freshness window still applies to ordinary resumes.

## Configuration compatibility policy

`total_run_deadline_seconds` is an **operational** control: it changes neither
request definitions, datasets, schemas, windows, symbols, splits, budgets, nor
cost arithmetic. Because the checkpoint binds the whole-file config hash, changing
the deadline changes that hash. `checkpoint_compatibility.py` therefore accepts a
resume when the checkpoint's stored `pilot_config_hash` either equals the current
hash or is a hand-verified prior hash in
`OPERATIONALLY_COMPATIBLE_PRIOR_CONFIG_HASHES`. The one registered prior hash is
`b490b3a11d89707d8a9ab6d154eb6c03ee5d312e247a9d936e1caca4d2621426`
(the `total_run_deadline_seconds=540` config); a field-level diff
(`diff_config_compatibility`) confirms the only difference from the current config
is that operational field. Any scientific, request, budget, or acquisition-policy
difference remains incompatible and fails closed.

## Safety

Implemented and tested entirely offline with fake providers and temporary
checkpoints; no real Databento client was constructed and no provider call, paid
method, authorization, attestation, or download occurred. The production
checkpoint is byte-for-byte unchanged. A separate live milestone (with explicit
authorization) is still required to actually resume and complete the checkpoint,
and metadata completion does not authorize acquisition.
