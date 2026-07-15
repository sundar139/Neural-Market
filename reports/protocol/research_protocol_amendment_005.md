# Research Protocol Amendment 005 — Resilient Usage-Based Cost Estimation

## Status and unchanged scope

This amendment approves implementation and offline validation of a conservative,
fail-closed derived cost fallback (hierarchy levels 1 and 2). It does not
authorize a purchase, a metadata network call, a paid request,
`timeseries.get_range`, batch submission, or any download. The January 2019
training boundary, sealed final test, USD 5.00 total cap, and USD 1.00
per-request cap are unchanged. No paid pilot was executed and no market
artifact was produced.

## Cost hierarchy

The authorized estimation hierarchy is:

1. Databento `metadata.get_cost` (authoritative provider quote).
2. Derived cost from `metadata.get_billable_size` and
   `metadata.list_unit_prices`.
3. Operator-attested portal quote.
4. Block execution.

This milestone implements levels 1 and 2. Levels 3 and 4 are represented by the
`CostSource` enum (`PROVIDER_GET_COST`, `DERIVED_BILLABLE_SIZE_UNIT_PRICE`,
`PORTAL_ATTESTED_QUOTE`, `UNAVAILABLE`) but are not built here.

## Derived formula and billing divisor

```
derived_cost_usd = Decimal(billable_size_bytes)
                   * Decimal(unit_price_usd_per_gib)
                   / Decimal(2**30)
```

The billing divisor is exactly `BYTES_PER_BILLING_GIB = 1_073_741_824`, never
`1_000_000_000`. Every monetary value is a `decimal.Decimal`; binary floating
point is never used for a price, product, tolerance, or hash input. Rounding is
presentation-only.

### Known-value regression

For the successful OPRA `cbbo-1m` reference request `e85df5d330c0ea18`
(billable size 5,209,600 bytes, unit price 2.0 USD/GiB):

- derived = `0.00970363616943359375`
- Databento `get_cost` = `0.009703636169`
- absolute error = `4.3359375e-13` ≤ `1e-12`

The residual is provider display/return precision, not a material price
disagreement. Substituting the `1e9` divisor fails this regression.

## Feed-mode binding

The paid path uses historical streaming retrieval (`timeseries.get_range`). The
successful reference `get_cost` — issued at the SDK default mode
`historical-streaming` — reproduces exactly at 2.0 USD/GiB, so the derived
fallback prices against the `historical-streaming` unit price. The cheaper
`historical` batch mode corresponds to unauthorized batch submission and is not
used. `ACQUISITION_FEED_MODE = "historical-streaming"`.

## Fallback eligibility (fail-closed)

A derived estimate is permitted only after `get_cost` exhausts its bounded
attempts with one of: HTTP 500, 502, 503, 504, provider timeout, or provider
network timeout. All other conditions block and continue to fail closed: HTTP
400, 401, 403, 404, 409, 429; entitlement, authentication, invalid
symbol/schema/time-range, and request-contract errors. Blocked request
`d5352ffb04e4bc83` (`OPRA.PILLAR / cbbo-1m`, 2019-01-02) failed `get_cost` with
three bounded HTTP 504s and is therefore fallback-eligible; its billable size
(5,616,000 bytes) is already hash-valid in the checkpoint.

## Cross-validation gate (mandatory)

Before a derived estimate may be used, the method is validated against at least
one successful provider `get_cost` for the exact dataset, schema, feed mode,
account pricing context, and calculation version, requiring absolute error
≤ `1e-9` USD and relative error ≤ `1e-6`. The OPRA `cbbo-1m` reference yields a
single compatible sample that passes (max absolute error `4.3359375e-13`, max
relative error ≈ `4.5e-11`). An ARCX comparison never authorizes an OPRA
estimate; a `definition` comparison never authorizes `cbbo-1m`. With no
compatible comparison the fallback stays disabled.

## Conservative margin and spending gates

Each derived estimate stores both its raw value and a conservative value
`max(raw, raw * 1.25)` = raw × 1.25. The conservative value drives the
per-request cap (≤ USD 1.00), the plan total cap (≤ USD 5.00), the drift gate,
and any authorization binding. The provider-returned cost is never altered when
`get_cost` succeeds. Because each derived request already carries a 25% margin,
the conservative total uses the wider 1.50 drift ceiling against the tracked
total, while provider-quoted totals keep their existing ceiling.

## Provenance and immutability

Every derived estimate binds the request-specification hash, billable-size
response hash, unit-price snapshot hash, cross-validation evidence hash, and
calculation version into an `estimate_hash`. Changing any input invalidates the
estimate. The unit-price snapshot binds dataset, Databento client version,
retrieved-at, feed mode, schema-to-price mapping, expiration, and a canonical
response hash (`data_contracts/metadata_cost_snapshot.schema.json`); only one
current snapshot per dataset and generation is allowed.

## Scope note

The first stage delivered the estimator as a tested library plus its contract,
tests, and documentation. No metadata call, paid request, download,
authorization, or portal attestation occurred; the production checkpoint was not
modified; only ignored backup copies were created under
`reports/data/execution/cost_fallback/`.

## Production metadata-runner integration

The estimator is now wired into the guarded metadata runner and the
`data pilot prepare` CLI. `metadata.get_cost` remains the preferred source: on
success the cost endpoint records `cost_source = provider_response`, the exact
provider decimal, and no 25% margin. Only after `get_cost` exhausts its bounded
attempts on HTTP 500/502/503/504 or a connection/network timeout does the runner
attempt the derived fallback (`cost_fallback_trigger`); prohibited failures
(4xx, 429, entitlement, authentication, invalid request) and any non-`cost`
failure continue to fail closed exactly as before, and the unit-price snapshot is
never fetched for them.

The restricted metadata facade now also exposes `list_publishers` and
`list_unit_prices`; time-series, batch, and live namespaces remain unreachable.
Unit-price snapshots are fetched at most once per dataset per preflight
(`UnitPriceSnapshotCache`) through the same Windows spawn-child boundary as the
other metadata endpoints (`run_isolated_unit_price_request`), with the same hard
deadline, terminate/kill, and zero-remaining-children guarantees.

A completed cost endpoint distinguishes provider, derived, and portal responses.
Derived entries persist the raw and conservative cost, billable size and its
response hash, the unit price and snapshot hash, the cross-validation evidence
hash, the calculation version, the sanitized fallback trigger class and HTTP
status, and an immutable `derivation_hash`
(`data_contracts/pilot_metadata_checkpoint.schema.json`). A derived cost still
counts as one completed cost result in the 75-endpoint preflight. Legacy
checkpoints without the new fields remain readable and load as provider costs;
loading never rewrites a checkpoint.

Plan-level aggregation (`plan_cost_rollup`) reports provider/derived/portal/
unavailable counts, raw and conservative totals, and the largest raw and
conservative requests. The conservative total (each derived request carrying its
25% margin) governs the ≤ USD 5.00 total cap, ≤ USD 1.00 per-request cap, and
the 1.50× drift ceiling; provider-only plans are unaffected because their
conservative cost equals their raw cost.

## Cross-validation sample policy

For the January pilot the minimum compatible sample count is **1**, because
exactly one exact `OPRA.PILLAR / cbbo-1m / historical-streaming` provider
comparison currently exists. The preflight report records
`pilot_cross_validation_sample_count = 1` and
`full_acquisition_minimum_sample_count = 2`: before full development-data
acquisition, at least two independent compatible provider comparisons are
required. One sample is not claimed sufficient for the full acquisition phase.

No metadata call, `list_unit_prices`, `get_billable_size`, `get_cost`,
`timeseries.get_range`, paid request, download, authorization, or portal
attestation occurred during this integration; all provider behavior was injected
or fixture-based. The production checkpoint retains its original SHA-256.
