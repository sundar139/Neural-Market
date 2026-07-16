# Research Protocol Amendment 012 — Reusable Provider Cost-Recheck Gate

**Date:** 2026-07-16 (UTC). **Amends:** Amendment 011 (guarded authorization package).
**Companion code:** `src/neuralmarket/data/acquisition/live_cost_recheck.py`,
CLI `data pilot recheck-cost`.

## 1. Purpose

A reusable, fail-closed gate obtains a fresh Databento `metadata.get_cost`
quote for the **exact frozen January 2019 pilot requests** and compares it
against the completed preflight totals and the project spending gates. It runs
immediately before a manual purchase authorization — and again whenever the
authorization expires, the scope or request manifest changes, the SDK version
changes, or pricing assumptions change — so the human decision rests on a
current provider quote rather than only the earlier preflight.

## 2. Exact frozen-request behavior (no cross product)

The gate never forms a `dataset x schema` cross product. The frozen request
plan (`build_pilot_request_plan`, validated by `validate_canonical_pilot_plan`
to the exact 25-request shape) is the sole source of quoted combinations:

- ARCX.PILLAR / SPY — `definition`, `ohlcv-1d`, `statistics`
- OPRA.PILLAR / SPY.OPT — `definition` (parent), plus 21 `cbbo-1m` 10-minute
  closing-quote windows on the exact January 2019 XNYS sessions.

Each quote uses the request's recorded `stype_in` — **`parent` for
`SPY.OPT`**, `raw_symbol` for `SPY` — and the request's exact start/end
(the 600-second quote windows, never a whole-month substitute). This
deliberately does not reproduce the naive
`for dataset: for schema: get_cost(..., start="2019-01-02", end="2019-02-01")`
loop, which would request invalid dataset/schema combinations, broaden scope,
use the wrong symbology, and produce totals not comparable to the approved
plan.

## 3. Dataset-specific schema validation

Before quoting, the gate groups requests by dataset and calls
`metadata.list_schemas(dataset=...)` **once per unique dataset** (two calls for
the current plan), verifying every frozen schema is present in that dataset's
own list. ARCX schema support is never inferred from OPRA or vice versa. An
unsupported frozen schema fails the gate before any `get_cost` call.

## 4. Provider-only fresh quotes; relationship to the derived fallback

Every fresh quote is a direct provider response. The gate never substitutes the
earlier derived unit-price fallback for a failed fresh quote: a quote that fails
its bounded two attempts is recorded as `unavailable`, the run status becomes
`incomplete`, and `authorization_ready` is `false` with partial evidence
preserved. Because all successful quotes are provider responses, the fresh
conservative total equals the fresh raw total (no 1.25× margin). The single
prior derived request (`e536e625287188b9`) remains documented for provenance in
Amendment 010; it is not carried into this fresh gate.

## 5. Exact Decimal, bounded retries, isolation

Provider costs are converted via `Decimal(str(cost))` so a binary float never
contaminates evidence; NaN, infinity, and negatives are rejected. Each quote is
isolated in a spawn child (reusing the reviewed metadata timeout/isolation), at
most two attempts per request, no unbounded retry, no whole-command relaunch,
deterministic child cleanup with zero remaining children, and sanitized attempt
history (HTTP status and exception class only — no raw response body). The API
key is read only from the dotenv-launched process environment and never
persisted, logged, hashed, or inspected.

## 6. Financial comparison

The gate reports the fresh raw and conservative totals, the prior totals, the
absolute and relative deltas, and the largest request, and evaluates the
unchanged gates: largest request ≤ $1.00, total ≤ $5.00, and conservative
total ≤ the drift ceiling `0.6907716840495` (1.5× the tracked
`0.460514456033`). A fresh total above the recommended `$0.50` amount does not
raise the authorization automatically — it means Rohith must reconsider the
amount within the allowed ceiling.

## 7. Relationship to portal attestation and authorization

This API cost-recheck is separate from, and does not replace, the mandatory
manual Databento portal attestation or the two-layer purchase authorization.
It authorizes nothing, constructs no paid provider, calls no `timeseries.get_range`,
submits no batch job, opens no live connection, creates no paid journal, and
downloads no market data. It is a pre-authorization verification only.

## 8. Future-use policy

Run the recheck: after metadata preflight; immediately before manual purchase
authorization; again when an authorization expires before use; before a
reviewed retry after a failed or interrupted acquisition; after any change to
scope, request manifest, SDK version, or pricing assumptions; and before
expanding from pilot to full acquisition. It must not run in unit/CI pipelines,
run silently at startup, create authorization, replace portal attestation,
trigger acquisition, raise a spending ceiling, or run repeatedly without
operator review.
