# Research Protocol Amendment 008 — Live Confirmed Unit-Price Validation

## Status and unchanged scope

This amendment records one authorized metadata-only
`metadata.list_unit_prices(dataset="OPRA.PILLAR")` call run through the
production isolated-child path at commit `bf59d97`. It does not authorize a
purchase, a checkpoint resume, any other metadata call, `timeseries.get_range`,
batch/live access, or market-data acquisition. The January 2019 boundary, sealed
final test, USD 5.00 total cap, and USD 1.00 per-request cap are unchanged. No
paid pilot executed; no market artifact was produced; the production checkpoint
is byte-for-byte unchanged.

## Outcome

`successful_snapshot`. The parser correction from `bf59d97` accepted the real
Databento `0.81.0` response and produced a valid, hash-bound snapshot.

- dataset: OPRA.PILLAR
- selected feed mode: `historical-streaming`
- selected schema: `cbbo-1m`
- `cbbo-1m` unit price: `2.0` USD/GiB (positive finite Decimal)
- response hash / snapshot hash:
  `662d19a986bafba335f1cc0ce909ba336008386d67b7bbda751e6084636d1824`
- retrieved_at `2026-07-15T07:47:21.525468+00:00`,
  expires_at `2026-07-15T08:17:21.525468+00:00`
- snapshot-schema validation passed; no failure diagnostic
- child exit 0, joined, not terminated, zero remaining children

The real response used the confirmed `{"mode": <str>, "unit_prices": {schema:
price}}` form; the sanitizer normalized `unit_prices` to the canonical `schemas`
block, and the downstream Decimal/mode/schema validation accepted `cbbo-1m` at
`2.0` USD/GiB, matching the earlier successful `get_cost` reference.

## Live-call accounting

Exactly one real `list_unit_prices` call; zero `list_publishers`,
`get_record_count`, `get_billable_size`, `get_cost`, `timeseries.get_range`,
batch, and live calls. Zero downloads, authorizations, and attestations. Sanitized
probe evidence lives under `reports/data/execution/metadata_preflight/` (ignored)
and contains no raw response, unrelated-mode/schema prices, secrets, or account
data.

## Follow-up

The unit-price path is now validated end-to-end against the live SDK. Resuming
the January 2019 metadata checkpoint (completing the remaining cost endpoints,
including the previously-blocked `d5352ffb04e4bc83` OPRA `cbbo-1m` cost via the
derived fallback) is a separate reviewed milestone requiring explicit
authorization. Acquisition remains unauthorized; the checkpoint stays at 16/75
endpoints and 4/25 requests with billing uncertainty false.
