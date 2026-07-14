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

`BILLED` remains non-retriable as
`billed_without_validated_artifact`; `NOT_BILLED` becomes
`retry_eligible_after_manual_nonbilling_confirmation` but still requires a new
authorization and attestation before any later retry; `UNKNOWN` remains
`uncertain_billing`. Reconciliation never contacts Databento and never changes a
consumed authorization back to available.
