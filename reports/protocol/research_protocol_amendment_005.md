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

This milestone delivers the estimator as a tested library plus its contract,
tests, and documentation. It is not yet wired into the live metadata preflight
because no metadata network call runs in this milestone; integration into the
runner is deferred to the next authorized preflight. No metadata call, paid
request, download, authorization, or portal attestation occurred. The production
checkpoint was not modified; only an ignored backup copy was created under
`reports/data/execution/cost_fallback/`.
