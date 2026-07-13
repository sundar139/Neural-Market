# Guarded January 2019 pilot

The pilot is a bounded, training-only acquisition of SPY underlying and option metadata for the 21 XNYS sessions in January 2019. It plans 25 requests: three ARCX catalog/underlying requests, one OPRA definition request, and 21 OPRA closing-quote windows.

No purchase or record download is authorized by the repository configuration. Planning uses only Databento metadata endpoints: `get_record_count`, `get_billable_size`, and `get_cost`. The acquisition guard blocks range retrieval, batch submission, downloads, and live APIs.

## Prepare a final request plan

Set the Databento API key locally without committing it, then run:

```powershell
& .\.venv\Scripts\neuralmarket.exe data pilot prepare `
  --config configs/data/acquisition/pilot_january_2019.yaml `
  --output reports/data/pilot_preflight.local.json `
  --request-manifest reports/data/pilot_request_plan_audit.local.json
```

Preparation verifies the source, split, and acquisition-policy manifests; performs fresh bounded metadata estimates; enforces the USD 5.00 total and USD 1.00 per-request caps; and writes an authorization-ready manifest atomically. Metadata failures or timeouts fail closed. Local reports are not committed.

## Verify offline

```powershell
& .\.venv\Scripts\neuralmarket.exe data pilot verify `
  --request-manifest reports/data/pilot_request_plan_audit.local.json `
  --authorization-template configs/data/acquisition/pilot_authorization.template.json
```

Verification checks the JSON schema, request hashes, plan hash, dependency hashes, budgets, and authorization state without contacting Databento.

## Authorization and execution

Copy `configs/data/acquisition/pilot_authorization.template.json` to a local ignored path only after independent review. Fill every binding and cap exactly, set a narrow UTC validity interval, use the required confirmation phrase, and compute the authorization hash according to the schema.

Execution requires the exact plan hash both in the authorization and on the command line. Authorization is consumed atomically in the SQLite journal before a paid provider can be constructed, so it cannot be reused after restart. The provider-neutral paid adapter is present behind these guards, but this milestone never constructs it; the false authorization template keeps execution closed and cannot download records.

```powershell
& .\.venv\Scripts\neuralmarket.exe data pilot execute `
  --plan reports/data/pilot_request_plan_audit.local.json `
  --authorization reports/data/pilot_authorization.local.json `
  --confirm-plan-hash <exact-plan-hash>
```

## Recovery

```powershell
& .\.venv\Scripts\neuralmarket.exe data pilot recover
```

Recovery is inspection-only. It reports journal state, missing or corrupt artifacts, unsafe paths, and retry candidates; it never retries, deletes, quarantines, or purchases automatically.

## Data safety

Raw DBN and normalized Parquet outputs are ignored and must not be committed. Atomic writers use `.partial` files, `fsync`, validation, checksums, and rename-without-overwrite publication. Stop immediately for a checksum mismatch, path-containment failure, record-window violation, nonfinite value, data leakage, or accounting mismatch.

See [data lineage](lineage.md) and [Protocol Amendment 003](../../reports/protocol/research_protocol_amendment_003.md).
