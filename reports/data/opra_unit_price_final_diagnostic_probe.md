# OPRA Unit-Price Final Diagnostic Probe

## Outcome

```text
diagnosed_fail_closed
```

One authorized live `metadata.list_unit_prices(dataset="OPRA.PILLAR")` call ran
through the production isolated diagnostic path at commit `95983cc`. The real
response was rejected fail-closed, and the new diagnostics captured the exact
structural cause. No prices, credentials, account data, or raw response were
persisted. The production metadata checkpoint was not resumed and is unchanged.

## Run identity

| Field | Value |
|---|---|
| Starting HEAD | `95983cc3d79bcbb7132b203c5e15d7e2731ccb1e` |
| Databento SDK | `0.81.0` |
| Permitted call | `metadata.list_unit_prices(dataset="OPRA.PILLAR")` |
| `list_unit_prices` calls | 1 |
| All other provider calls | 0 |
| Checkpoint SHA-256 before | `e08bd8c81ab99235d278005bfdb7d9c2d69d2040d13a5ebf7d0cd6065883d084` |
| Checkpoint SHA-256 after | `e08bd8c81ab99235d278005bfdb7d9c2d69d2040d13a5ebf7d0cd6065883d084` |
| Metadata resume run | no |

## Sanitized diagnostic

| Field | Value |
|---|---|
| `diagnostic_schema_version` | `unit-price-diagnostic-v1` |
| `failure_stage` | `sanitization` |
| `failure_code` | `schemas_not_mapping` |
| `failure_type` | `CostEstimationError` |
| `response_shape_fingerprint` | `0832e91a656af85d83b10cb51f1d97baf6933790da781361f98d6ee75d67a8b9` |
| Serialized summary size | 3320 bytes (≤ 32 KiB) |
| `child_exit_code` | 0 |
| `child_joined` | true |
| `child_terminated` | false |
| `remaining_children` | 0 |

## Observed real response structure (price-free)

The `list_unit_prices` response is a **sequence of three mappings**, each with two
keys — `mode` (a string) and `unit_prices` (a mapping of 12 schema names to
prices):

```text
sequence (length 3)
└─ mapping (length 2)
   ├─ "mode": string
   └─ "unit_prices": mapping (length 12)
      └─ keys: cmbp-1, cbbo-1s, cbbo-1m, tcbbo, trades, ohlcv-1s,
               ohlcv-1m, ohlcv-1h, ohlcv-1d, statistics, status, definition
      └─ values: number  (prices — never captured)
```

Only value **types** and **key names** were captured; every price is recorded as
`number` with no value. `cbbo-1m` is present in each mode's `unit_prices` map.

## Evidence-based cause

The real Databento `0.81.0` shape is `[{"mode": <name>, "unit_prices": {schema:
price}}, ...]`. It is neither the earlier canonical list form
(`[{"mode", "schemas"}]`) nor the previously-assumed list-of-mode-maps
(`[{<mode>: {schema: price}}]`). The production sanitizer, seeing a list item
with a `mode` key but no `schemas` key, falls into its real-map branch and treats
each item key as a feed-mode name; the `mode` key's value is a string, not a
schema mapping, so `_mode_block` fails closed with `schemas_not_mapping` at the
sanitization stage. The compatible mode and `cbbo-1m` schema are in fact present
under `unit_prices`; the mismatch is purely the wrapper key name
(`unit_prices` vs `schemas`) combined with the mode being carried as a string
value under a `mode` key.

The correct fix (a separate correction milestone) is to recognize the real
`{"mode": <str>, "unit_prices": {...}}` item form and map `unit_prices` →
`schemas`. **The parser was not modified in this milestone.**

## Safety confirmations

- Exactly one real `list_unit_prices` call; zero `list_publishers`,
  `get_record_count`, `get_billable_size`, `get_cost`, `timeseries.get_range`,
  batch, and live calls.
- No prices, scalar values, credentials, account identifiers, headers, raw
  response, or object representations in any persisted evidence.
- Child joined cleanly (exit 0), not terminated, zero remaining children.
- Production checkpoint byte-for-byte unchanged; 16/75 endpoints, 4/25 requests,
  billing uncertainty false.
- No purchase authorization, portal attestation, or downloaded records.
- **Acquisition remains unauthorized;** checkpoint resume requires a separate
  reviewed milestone after the parser correction.
