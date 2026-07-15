# Research Protocol Amendment 010 — Resilient Metadata Preflight Completion

**Date:** 2026-07-15 (UTC). **Repository revision:** `beb1114ca8bf145f0b4a82d0cd52ed0ec598f1d3`.
**Amends:** the January 2019 pilot acquisition protocol (Amendments 004–008).
**Companion evidence:** `reports/data/resilient_metadata_preflight_completion.md`.

## 1. What changed

The January 2019 pilot metadata preflight is now COMPLETE: 75/75 metadata
endpoints and 25/25 logical requests, final checkpoint
`ede035f92b30c3b15d6fa0a9c61991225e216c943e86f059b7c52ed03b435706`, with
every completed result carrying provider or derived provenance and all
conservative financial gates passing. No market data was requested or
received; no purchase was authorized.

## 2. Why multiple reviewed continuations were required

The original single-invocation design (540 s run deadline, 30-minute
checkpoint freshness window) could not absorb repeated OPRA.PILLAR
`cbbo-1m` HTTP 504 responses on metadata endpoints. Rather than weaken
fail-closed semantics, the protocol evolved to **hash-authorized bounded
continuations**: each reviewed continuation binds to the exact byte hash of
the current checkpoint (`--allow-stale-checkpoint-sha256`, age bypass only),
performs exactly one foreground CLI invocation, consumes its authorization
via an atomic invocation marker, and stops atomically on the next
unrecoverable failure. Two live continuations were needed:

1. **Continuation 1** (checkpoint `e08bd8c8…d084` → `986fa970…ce1fd`):
   advanced 16/75 → 59/75 in 1566 s, then stopped fail-closed when
   `e85df5d330c0ea18` / `record-count` returned HTTP 504 on both bounded
   attempts (`maximum_timeout_attempts = 2`).
2. **Continuation 2** (checkpoint `986fa970…ce1fd` → `ede035f9…5706`):
   completed 59/75 → 75/75 in 520 s with exit code 0.

Between the two, an offline review milestone diagnosed and corrected two
local-evidence defects (a UTF-8-BOM marker-loading bug and an over-strict
safe-resume rule in the throwaway validation library), proved
copied-checkpoint resume acceptance with fake providers (20 offline fixture
scenarios), and hash-pinned the continuation package via an integrity
manifest before execution was authorized.

## 3. The transient OPRA record-count 504, and why no fallback exists

`metadata.get_record_count` for OPRA.PILLAR `cbbo-1m` session 2019-01-24
(`e85df5d330c0ea18`) failed twice with HTTP 504 (`BentoServerError`) in
continuation 1 and succeeded on the first attempt of continuation 2 —
a genuinely transient server-side condition. **No derived fallback exists
for `record-count` by design:** unlike cost (which is arithmetically
derivable from billable size × unit price), a record count has no
independent authoritative derivation, so substituting one would fabricate
scientific metadata. Transient record-count failures therefore always stop
the run fail-closed and require a new reviewed continuation.

## 4. The single derived get_cost fallback

Request `e536e625287188b9` (OPRA.PILLAR / cbbo-1m) exhausted its bounded
`get_cost` attempts with two HTTP 504s in continuation 2 and completed via
the reviewed derived-cost path (`cost_source = derived_response`) — the only
non-provider cost among 25:

- Eligibility: HTTP 5xx/timeout classes only; 4xx, auth, and entitlement
  failures never trigger derivation.
- Inputs: provider billable size `5,305,600` bytes (validated response
  hash) × live-validated unit price `2.0 USD/GiB`
  (`historical-streaming` / `cbbo-1m`, snapshot hash `b8f69538…0714`,
  dataset-bound, fetched once via an isolated child) ÷ `2^30` bytes/GiB.
- Exact Decimal result: raw `0.009882450103759765625` USD; conservative
  `× 1.25 = 0.01235306262969970703125` USD. Both recomputed offline and
  equal to the persisted values; binding hashes (derivation,
  cross-validation evidence, request specification, snapshot) validate.

## 5. Conservative-cost methodology

Conservative totals apply the 1.25× safety margin **only to derived costs**;
provider-returned costs enter at face value. Final rollup: raw/fresh total
`0.460514456032759765625` USD; conservative total
`0.46298506855869970703125` USD; largest request `0.243695452809` USD.
Gates: largest ≤ $1.00; conservative total ≤ $5.00; conservative total ≤
`0.6907716840495` (1.5× the accepted planner estimate `0.460514456033`).
All pass. The fresh metadata total differs from the accepted planner
estimate `0.46` by `0.000514456032759765625`, within the `0.0920` tolerance.

## 6. Completed metadata evidence

Ignored local evidence under
`reports/data/execution/metadata_completion/` (both continuations):
invocation markers, exit codes, stdout/stderr, CLI reports, request
manifests, pre-run baselines and byte-exact pre-run checkpoint copies,
authoritative evidence/cost-rollup/checkpoint-validation/compatibility
JSONs, a hash-pinned validation library + integrity manifest, a 20-scenario
offline fixture suite, and the secret-candidate classification (116
flagged lines, all `confirmed_nonsecret_identifier`, zero possible or
confirmed secrets). Preservation proofs: 59/59 continuation-2 starting
endpoints and the original 16 first-generation endpoints unchanged; zero
completed-endpoint re-fetches; 103 isolated children all exited 0 with
zero remaining processes.

## 7. What remains prohibited

Completion of the metadata preflight does **not** authorize acquisition.
Before any market-data request (`timeseries.get_range`, batch download, or
live session) the protocol still requires, in a separate reviewed
milestone: explicit user purchase authorization, the authorization-manifest
workflow, portal attestation, and the paid-execution journal path. Derived
costs used for planning require a second cross-validation sample before
full acquisition. Until then the acquisition guard remains in force and
`purchase_authorized` stays `false` everywhere.
