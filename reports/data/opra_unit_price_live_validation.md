# OPRA Unit-Price Live Validation

## Outcome

```text
successful_snapshot
```

One authorized live `metadata.list_unit_prices(dataset="OPRA.PILLAR")` call ran
through the production isolated-child path at commit `bf59d97`. The corrected
parser accepted the real Databento `0.81.0` response and constructed a valid,
hash-bound unit-price snapshot for the target mode and schema. No prices for
unrelated modes/schemas, credentials, account data, or raw response were
persisted. The production metadata checkpoint was not resumed and is unchanged.

## Run identity

| Field | Value |
|---|---|
| Starting HEAD | `bf59d977b4c3371c3578e9a26ea51740405e8ef4` |
| Databento SDK | `0.81.0` |
| Permitted call | `metadata.list_unit_prices(dataset="OPRA.PILLAR")` |
| `list_unit_prices` calls | 1 |
| All other provider calls | 0 |
| Checkpoint SHA-256 before | `e08bd8c81ab99235d278005bfdb7d9c2d69d2040d13a5ebf7d0cd6065883d084` |
| Checkpoint SHA-256 after | `e08bd8c81ab99235d278005bfdb7d9c2d69d2040d13a5ebf7d0cd6065883d084` |
| Endpoints before/after | 16 of 75 / 16 of 75 |
| Logical requests before/after | 4 of 25 / 4 of 25 |
| Metadata resume run | no |

## Validated snapshot

| Field | Value |
|---|---|
| `outcome` | `successful_snapshot` |
| failure diagnostic | none |
| dataset | OPRA.PILLAR |
| selected feed mode | `historical-streaming` |
| selected schema | `cbbo-1m` |
| `cbbo-1m` unit price (USD/GiB) | `2.0` (positive finite Decimal) |
| target-mode schema count | 12 |
| response hash | `662d19a986bafba335f1cc0ce909ba336008386d67b7bbda751e6084636d1824` |
| snapshot hash | `662d19a986bafba335f1cc0ce909ba336008386d67b7bbda751e6084636d1824` |
| retrieved_at | `2026-07-15T07:47:21.525468+00:00` |
| expires_at | `2026-07-15T08:17:21.525468+00:00` |
| snapshot-schema validation | passed |
| child exit code | 0 |
| child joined | true |
| child terminated | false |
| remaining children | 0 |

The live `historical-streaming` / `cbbo-1m` unit price of `2.0` USD/GiB is
consistent with the earlier successful `get_cost` reference (which reproduced at
2.0 USD/GiB). Only the target schema's price and a schema-count are recorded;
prices for the other 11 schemas and other feed modes were not persisted.

## Safety confirmations

- Exactly one real `list_unit_prices` call; zero `list_publishers`,
  `get_record_count`, `get_billable_size`, `get_cost`, `timeseries.get_range`,
  batch, and live calls.
- No raw response, no unrelated-mode/schema prices, no credentials, no account
  identifiers, no headers, no SDK object representations in persisted evidence.
- Child exited cleanly (exit 0), joined, not terminated, zero remaining children.
- Production checkpoint byte-for-byte unchanged; 16/75 endpoints, 4/25 requests,
  billing uncertainty false.
- No purchase authorization, portal attestation, or downloaded records.
- **Acquisition remains unauthorized.** Resuming the metadata checkpoint requires
  a separate reviewed milestone.
