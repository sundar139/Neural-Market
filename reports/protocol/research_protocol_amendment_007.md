# Research Protocol Amendment 007 — Final OPRA Unit-Price Diagnostic Probe

## Status and unchanged scope

This amendment records one authorized metadata-only
`metadata.list_unit_prices(dataset="OPRA.PILLAR")` probe run through the
production isolated diagnostic path at commit `95983cc`. It does not authorize a
purchase, a checkpoint resume, any other metadata call,
`timeseries.get_range`, batch/live access, or market-data acquisition. The
January 2019 boundary, sealed final test, USD 5.00 total cap, and USD 1.00
per-request cap are unchanged. No paid pilot executed; no market artifact was
produced; the production checkpoint is byte-for-byte unchanged.

## Outcome

`diagnosed_fail_closed`. The corrected parser from `88b48ea` still rejects the
real response, but the diagnostics from `95983cc` captured the exact cause
without exposing prices, credentials, account data, or the raw response.

- failure stage: `sanitization`
- failure code: `schemas_not_mapping`
- failure type: `CostEstimationError`
- diagnostic schema version: `unit-price-diagnostic-v1`
- structural fingerprint:
  `0832e91a656af85d83b10cb51f1d97baf6933790da781361f98d6ee75d67a8b9`
- child exit code 0, joined, not terminated, zero remaining children

## Real response structure

Databento `0.81.0` returns `list_unit_prices` as a sequence of three mappings,
each `{"mode": <string>, "unit_prices": {<schema>: <price>}}` with 12 OPRA
schemas per mode (including `cbbo-1m`). This is a third, distinct shape: not the
canonical `{"mode", "schemas"}` list form and not the previously-assumed
`{<mode>: {schema: price}}` map form. The wrapper key is `unit_prices`, and the
mode name is a string value under a `mode` key.

The production sanitizer, seeing a `mode` key but no `schemas` key, treats each
item key as a feed mode; the `mode` key's string value is not a schema mapping,
so it fails closed with `schemas_not_mapping`. The compatible mode and `cbbo-1m`
are present under `unit_prices`.

## Required follow-up (separate milestone)

Extend `_sanitize_unit_price_response` to recognize the real
`{"mode": <str>, "unit_prices": {...}}` item form, mapping `unit_prices` to the
canonical `schemas` block, with real-shape regression coverage. Then re-probe and,
only after a successful snapshot, resume the metadata checkpoint under a reviewed
milestone. The parser was deliberately left unchanged here.

## Safety

Exactly one real `list_unit_prices` call; zero other provider calls; zero paid
calls, downloads, authorizations, and attestations. Sanitized probe evidence
lives under `reports/data/execution/metadata_preflight/` (ignored) and contains
no prices, secrets, account data, or raw responses. Acquisition remains
unauthorized.
