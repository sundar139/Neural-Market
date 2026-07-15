# Resilient Metadata Preflight Completion — January 2019 Pilot

**Status:** COMPLETE — 75 of 75 metadata endpoints, 25 of 25 logical requests.
**Date:** 2026-07-15 (UTC). **Repository revision:** `beb1114ca8bf145f0b4a82d0cd52ed0ec598f1d3`.
**Scope:** metadata-only preflight (`get_record_count`, `get_billable_size`,
`get_cost`, plus one `list_unit_prices` snapshot for the single derived-cost
fallback). **Acquisition remains explicitly unauthorized.**

## 1. Execution chronology

| Step | UTC (2026-07-15) | Action | Result |
| --- | --- | --- | --- |
| 1 | earlier sessions | Fresh generation + first bounded runs | 16/75 endpoints, 4/25 requests |
| 2 | 21:38:09–22:04:15 | First hash-bound continuation (`--resume --allow-stale-checkpoint-sha256`, bound to checkpoint `e08bd8c8…d084`) | Exit 1 after 1566 s: advanced to 59/75, 19/25; stopped fail-closed on a transient OPRA `record-count` HTTP 504 |
| 3 | 22:04–22:37 | Offline review milestone | Diagnosed collector defects (UTF-8 BOM marker load; naive safe-resume rule), classified all secret candidates as non-secret, proved copied-checkpoint resume acceptance with fake providers, built + hash-pinned the second continuation package and integrity manifest |
| 4 | 22:43:38–22:52:18 | Second hash-bound continuation (bound to checkpoint `986fa970…ce1fd`) | Exit 0 after 520 s: completed 75/75, 25/25, pending 0 |
| 5 | 22:54 | Offline evidence collector | Authoritative status `complete`; its final secret scan flagged high-entropy candidates (expected hash identifiers), so the wrapper exited nonzero pending the classification below |

Each continuation was authorized for exactly one foreground CLI invocation,
consumed its authorization via an atomic invocation marker, and was bound to
the exact starting checkpoint bytes via `--allow-stale-checkpoint-sha256`
(age bypass only; every integrity, plan, endpoint-hash, and configuration
check stayed mandatory).

## 2. Checkpoint lineage

| Point | Checkpoint SHA-256 | State |
| --- | --- | --- |
| Before continuation 1 | `e08bd8c81ab99235d278005bfdb7d9c2d69d2040d13a5ebf7d0cd6065883d084` | 16/75, 4/25 |
| After continuation 1 / before continuation 2 | `986fa970b67ccbf6d04390f6f91c28d6cb7dd38deb98d1f1c386a6b6ca2ce1fd` | 59/75, 19/25, failed `e85df5d330c0ea18`/`record-count` (504 ×2) |
| Final | `ede035f92b30c3b15d6fa0a9c61991225e216c943e86f059b7c52ed03b435706` | 75/75, 25/25, pending 0, failure state cleared |

The final checkpoint revalidates against the frozen external manifests
(source `3d31e373…0604`, split `877caee3…dcabe`, policy `affce36b…e9b6`),
the frozen request-specification hashes, endpoint-response hashes, endpoint
uniqueness, metadata-only endpoint surface, exact Decimal reload, client
`databento 0.81.0`, and estimator `pilot-metadata-process-v1`. Validation
did not mutate the checkpoint (byte hash identical before and after).

## 3. Preservation and resume behavior

- Continuation 2 started from 59 completed endpoints: **59 preserved,
  0 changed, 0 missing, 0 re-fetched** (field-level comparison of
  `response_hash`, `completed_at`, `cost_source` against the pre-run copy).
- The original 16 endpoints from the first checkpoint generation remain
  byte-identical through both continuations (16/16 preserved).
- The first resumed call was exactly the failed endpoint
  (`e85df5d330c0ea18` / `record-count`), as proven in advance by the offline
  copied-checkpoint fixture suite and confirmed live.
- Invocation marker and pre-run baseline agree on starting HEAD and starting
  checkpoint hash (BOM-tolerant field-level comparison, all equal).

## 4. Provider methods and retries

| Method | Calls | Notes |
| --- | --- | --- |
| `metadata.get_record_count` | 36 attempts, 25 succeeded | includes 11 transient failures across both continuations |
| `metadata.get_billable_size` | 30 attempts, 25 succeeded | 5 transient failures |
| `metadata.get_cost` | 37 attempts, 24 succeeded | 13 transient failures; 1 request completed via derived fallback |
| `metadata.list_unit_prices` | 1 | one isolated-child snapshot for the derived fallback |
| `metadata.list_publishers` | 0 | |
| `timeseries.get_range` | 0 | prohibited; confirmed zero |
| batch / live / symbology | 0 | prohibited; confirmed zero |

Report-level counters: `metadata_call_count = 25`,
`metadata_endpoint_call_count = 74` (74 provider endpoint successes; the
75th endpoint result is the derived cost), `retry_count = 28`. All 103
isolated child processes exited 0, joined, never terminated;
`remaining_children` was 0 after every attempt (maximum 0, final 0).

Key endpoints:

- `e85df5d330c0ea18` / `record-count`: attempts 1–2 failed HTTP 504
  (continuation 1, fail-closed stop at the configured
  `maximum_timeout_attempts = 2`); attempt 1 of continuation 2 succeeded.
- `e536e625287188b9` / `cost`: attempts 1–2 failed HTTP 504
  (`BentoServerError`) in continuation 2, exhausting the bounded retry
  policy and triggering the derived fallback.

## 5. Derived cost fallback (single occurrence)

Request `e536e625287188b9` (OPRA.PILLAR / cbbo-1m / 2019-01-25 session) is
the **only** derived-cost result; the other 24 costs are direct provider
responses (`cost_source = provider_response`, no margin applied).

Provenance recorded in the checkpoint (`cost_source = derived_response`):

- Trigger: `http_5xx`, HTTP 504, after bounded `get_cost` exhaustion —
  an eligible transient class (4xx/auth/entitlement failures do not
  qualify and fail closed instead).
- Billable size: `5,305,600` bytes with validated provider
  `response_hash e258cc43…4262`.
- Unit-price snapshot: hash `b8f69538…0714`, dataset-bound OPRA.PILLAR,
  feed mode `historical-streaming`, schema `cbbo-1m`, unit price
  `2.0 USD/GiB` (live-validated parser, commit `31e1c5e`), fresh at use
  time via the once-per-dataset snapshot cache.
- Binding hashes: derivation `0517a851…c3c8`, cross-validation evidence
  `a1d50711…a03b`, calculation version `derived-cost-v1`; request
  specification hash validated against the frozen plan.

Exact Decimal arithmetic (recomputed offline, equal to persisted values):

```text
raw     = 5305600 × 2.0 / 2^30 = 0.009882450103759765625 USD
conserv = raw × 1.25           = 0.01235306262969970703125 USD
```

The 1.25× conservative margin applies **only** to the derived cost;
recomputing conservative total as (24 provider raw costs) + (derived × 1.25)
reproduces the persisted conservative total exactly.

## 6. Final cost rollup and financial gates

| Quantity | Value (USD, exact Decimal) |
| --- | --- |
| Provider cost count | 24 |
| Derived cost count | 1 (`e536e625287188b9`) |
| Portal cost count | 0 |
| Unavailable cost count | 0 |
| Raw / fresh total | `0.460514456032759765625` |
| Conservative total | `0.46298506855869970703125` |
| Largest raw request | `0.243695452809` (`68b018c920c2427b`) |
| Largest conservative request | `0.243695452809` |
| Conservative total ÷ tracked total (`0.460514456033`) | `1.005364896787…` |
| Largest conservative ÷ tracked largest (`0.243695452809`) | `1` |

Gates (all PASS):

- largest conservative request `0.243695452809` ≤ **1.00**
- conservative total `0.46298…` ≤ **5.00**
- conservative total `0.46298…` ≤ drift ceiling **0.6907716840495** (1.5×
  tracked planner total)
- fresh vs accepted planner estimate `0.46`: difference
  `0.000514456032759765625` within tolerance `0.0920`.

## 7. Configuration compatibility

Checkpoint-stored pilot config hash `b490b3a1…1426` (540 s deadline era) is
operationally compatible with the current config `7be6bae3…fbbb`; the only
differing field is `metadata_execution.total_run_deadline_seconds`
(540 → 7200), which is on the reviewed operational allowlist. No scientific,
budget, retry, or timeout-policy field differs.

## 8. Secret-scan candidate classification

The collector's fail-closed secret scan flagged **116 lines** across the
operational evidence (stdout, report, request manifest, evidence,
compatibility). Offline classification of every candidate:

| Category | Count | Classification |
| --- | --- | --- |
| Request-specification SHA-256 | 50 | confirmed_nonsecret_identifier |
| Endpoint/response SHA-256 | 25 | confirmed_nonsecret_identifier |
| Request IDs (16-hex, all in frozen plan) | 22 | confirmed_nonsecret_identifier |
| Configuration/manifest SHA-256 | 12 | confirmed_nonsecret_identifier |
| Checkpoint SHA-256 | 2 | confirmed_nonsecret_identifier |
| Unit-price snapshot SHA-256 | 2 | confirmed_nonsecret_identifier |
| Plan SHA-256 | 2 | confirmed_nonsecret_identifier |
| Git commit | 1 | confirmed_nonsecret_identifier |

**possible_secret: 0 — confirmed_secret: 0.** Every candidate matched an
exact known non-secret identifier already bound into the frozen plan,
manifests, or checkpoint. stderr was empty (0 bytes). High-entropy detection
was not weakened; the full classification (lengths and SHA-256 fingerprints,
no raw unknown values) is preserved in the ignored local report
`hash_bound_resume2_986fa970_secret_candidates.local.json`.

## 9. Zero acquisition activity

Pre-run vs post-run artifact inventories show **no** newly created purchase
authorizations, portal attestations, paid execution journals, DBN
market-data files, or market-data Parquet files. Report counters:
`batch_jobs_submitted = 0`, `download_attempts = 0`,
`live_connections_opened = 0`, `timeseries.get_range` calls = 0,
`purchase_authorized = false`. Billing state: not applicable
(metadata-only; no billable market-data operation exists in this phase).

## 10. Limitations and unresolved items

- The derived cost for `e536e625287188b9` rests on one cross-validation
  sample (pilot policy minimum 1); full acquisition requires ≥ 2 samples.
- `record-count` has no derived fallback **by design**; a future transient
  failure there stops fail-closed and needs another reviewed continuation.
- Collector "complete" status and this report certify metadata preflight
  only. **Market-data acquisition remains unauthorized** and requires a
  separate reviewed milestone with explicit purchase authorization and
  portal attestation before any `timeseries.get_range`, batch, or live call.
