# Guarded January 2019 pilot acquisition

The controlled pilot covers SPY on XNYS in January 2019, training split only.
The plan contains 25 requests: four catalog requests and 21 ten-minute
OPRA closing-quote windows, one for each January 2019 XNYS session.

Preparation uses only Databento metadata endpoints for record count, billable
size, and cost. Each request uses one hard-bounded spawned child; execution is
sequential, checkpointed after every success, and resumes without repeating
completed estimates. It retries only bounded transient failures and enforces a
USD 5.00 aggregate cap and USD 1.00 per-request cap. The accepted planner
estimate is USD 0.46; the fresh exact estimate is recorded in the tracked
request manifest only after all 25 estimates complete successfully.

The final manifest binds source, split, policy, configuration, calendar,
provider-client, implementation, request identities, logical relative paths,
fresh estimates, and authorization requirements. It contains no API key,
account identifier, absolute path, or market observation.

No execution is authorized in this milestone. A future purchase requires the
exact plan hash, a narrow-lived authorization with the required confirmation
phrase, durable single-use consumption, and a second execution preflight.
The false authorization template is intentionally unusable.

If provider completion or local persistence is uncertain, the pipeline stops
and recovery is manual. It never automatically redownloads under uncertain
billing state. Raw DBN is immutable and published only after validation,
checksum, sidecar publication, and atomic rename. Normalized Parquet is an
immutable derivation with deterministic columns, UTC timestamps, provenance,
row-count reconciliation, schema fingerprint, and checksum.

The first controlled paid attempt stopped after the first provider invocation
failed before any raw artifact was persisted. The request is recorded as
`uncertain_billing`; recovery must surface that state and stale execution
attempts, but must not retry, delete, download, or infer billing from missing
files. Billing can be reconciled only from a local operator attestation created
after manual Databento portal review and applied with:

```powershell
& .\.venv\Scripts\neuralmarket.exe data pilot reconcile-billing `
    --journal "data/state/pilot_acquisition_journal.sqlite" `
    --reconciliation "reports/data/execution/reconciliation/billing_reconciliation_<execution>.local.json" `
    --output "reports/data/execution/reconciliation/reconciliation_result.local.json"
```

Reconciliation is immutable. If an initial `UNKNOWN` artifact is later resolved,
the new artifact must supersede the current effective reconciliation hash with a
monotonic `supersession_sequence`; stale predecessors and terminal-status
replacement fail closed. `BILLED` remains non-retriable as
`billed_without_validated_artifact`; `NOT_BILLED` becomes
`retry_eligible_after_manual_nonbilling_confirmation` but still requires a new
authorization and attestation before any later retry; `UNKNOWN` remains
`uncertain_billing`. Reconciliation never contacts Databento and never changes a
consumed authorization back to available.

Offline diagnosis of the first paid-provider failure found a deterministic
adapter-contract defect before Databento could receive a valid request: the
production `timeseries.get_range` call supplied an `encoding` keyword, but the
installed Databento 0.81.0 signature accepts only `dataset`, `start`, `end`,
`symbols`, `schema`, `stype_in`, `stype_out`, `limit`, and optional `path`.
Databento streams DBN/Zstd for this method internally. The repaired adapter
therefore passes only supported request keywords, validates the DBNStore-like
response shape, and classifies post-response serialization/persistence failures
without enabling automatic retry. Any future retry still requires fresh explicit
authorization and portal attestation.

## Resilient usage-based cost fallback

Cost estimation follows a fail-closed hierarchy: (1) Databento
`metadata.get_cost`; (2) a derived estimate from `metadata.get_billable_size`
and `metadata.list_unit_prices`; (3) an operator-attested portal quote; (4)
block execution. Levels 1 and 2 are implemented in
`neuralmarket.data.acquisition.cost_estimation`.

The derived cost is

```
derived_cost_usd = Decimal(billable_size_bytes)
                   * Decimal(unit_price_usd_per_gib)
                   / Decimal(1_073_741_824)
```

using the exact binary GiB divisor `2**30` (never `1e9`) with `Decimal`
throughout; rounding is presentation-only. The unit-price snapshot is bound to
the `historical-streaming` feed mode — the same streaming path
`timeseries.get_range` uses — because the successful reference `get_cost`
reproduces exactly at 2.0 USD/GiB in that mode; the cheaper `historical` batch
mode maps to unauthorized batch submission.

A derived estimate is permitted only after `get_cost` exhausts its bounded
attempts with HTTP 500/502/503/504 or a provider/network timeout. HTTP
400/401/403/404/409/429, entitlement, authentication, invalid symbol/schema/
range, and request-contract errors all continue to fail closed. Before use, the
method is cross-validated against at least one successful same-dataset,
same-schema, same-mode, same-account provider `get_cost` (absolute error ≤ 1e-9
USD, relative error ≤ 1e-6); with no compatible comparison the fallback stays
disabled. Each derived estimate stores a raw value and a conservative value
`raw × 1.25`; the conservative value drives every per-request cap, total cap,
drift gate, and authorization binding. Provider-returned costs are never
altered. Each estimate binds the request-specification, billable-size response,
unit-price snapshot, and cross-validation evidence hashes plus the calculation
version into an immutable `estimate_hash`.

In `data pilot prepare`, `get_cost` stays the preferred source and records
`cost_source = provider_response` with no added margin. Only after `get_cost`
exhausts its bounded attempts on HTTP 500/502/503/504 or a connection/network
timeout does the runner derive a cost; the unit-price snapshot for the dataset is
fetched at most once per preflight, through the same spawn-child boundary as the
other metadata endpoints, and cross-validated against a completed same-context
provider `get_cost` before use. A completed cost endpoint records provider,
derived, or portal provenance
(`data_contracts/pilot_metadata_checkpoint.schema.json`); legacy checkpoints
without the new fields load as provider costs and are never rewritten on load.
The preflight report's `cost_source_summary` lists provider/derived counts, raw
and conservative totals, fallback request IDs, unit-price snapshot hashes, and
the cross-validation sample counts (`pilot_cross_validation_sample_count = 1`,
`full_acquisition_minimum_sample_count = 2` — full development acquisition
requires at least two compatible provider comparisons). Conservative costs govern
the per-request, total, and drift gates.
