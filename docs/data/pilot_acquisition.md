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

### Databento unit-price response shape

The installed Databento SDK (`0.81.0`) returns
`metadata.list_unit_prices(dataset)` as a **list of maps of feed mode to schema
to unit price**, e.g. `[{"historical-streaming": {"cbbo-1m": 2.0}}]`, where each
map's keys are feed-mode names and prices are JSON floats. A single list item may
carry several modes. `_sanitize_unit_price_response` normalizes this — plus the
earlier canonical `[{"mode": ..., "schemas": {...}}]` list form and the top-level
`{mode: {schema: price}}` mapping — into one canonical
`{"mode": ..., "schemas": {schema: price-string}}` block per feed mode. It
transforms structure and representation only (SDK floats become decimal strings);
`parse_unit_price_snapshot` still decides price validity (positive, finite,
non-bool). Duplicate feed-mode blocks are **preserved, never merged**, so the
parser's ambiguity check can reject them, and block order is deterministic. A
malformed or mixed response (a non-mapping entry, an empty or non-mapping schema
map, an empty mode name) fails the whole response closed rather than returning a
partial subset.

This correction was developed and validated entirely offline against fixtures
that model the observed SDK shape. A new live unit-price probe is still required
before the production metadata checkpoint may be resumed, and market-data
acquisition remains unauthorized.

### Unit-price failure diagnostics

The first shape correction remained insufficient: a second live probe still
failed, and the child returned only the exception class, so neither the failing
**stage** nor the response **structure** was recoverable — a single authorized
call could not be diagnosed. `unit_price_diagnostics.py` closes that gap. On any
failure the isolated child now returns a typed, versioned
`UnitPriceFailureDiagnostic` (`diagnostic_schema_version =
"unit-price-diagnostic-v1"`) carrying the failing stage (`provider_call`,
`sanitization`, `snapshot_parsing`, `child_timeout`, …), a stable machine-readable
`failure_code` (e.g. `sequence_item_not_mapping`, `schemas_empty`,
`target_mode_missing`, `target_mode_duplicate`, `target_schema_missing`,
`target_price_invalid`), a bounded price-free structural summary, and a SHA-256
structural fingerprint. `IsolatedUnitPriceResult` also exposes `child_exit_code`.

Raw response logging is prohibited because a real response carries prices and may
carry account-linked values. The summary captures only **structure** — value
types, mapping/schema **key names**, lengths, and truncation flags — never
prices, scalar values, string contents, credentials, or `repr()` of arbitrary
objects. It is bounded (≤16 sequence items, ≤32 keys per level, depth ≤3, key
length ≤128, ≤32 KiB) with explicit truncation flags, and cycle-safe. The
fingerprint hashes only that structural summary, so **changing prices does not
change it** while changing a mode or schema key does — a stable signal for
comparing responses across probes.

Parser acceptance/rejection was deliberately left **unchanged**; diagnostics only
observe and classify it. One new controlled live probe is still required, the
metadata checkpoint remains blocked, and acquisition remains unauthorized.

### Confirmed Databento 0.81.0 response contract

The final diagnostic probe confirmed the real `list_unit_prices` shape: a list of
items `{"mode": <string>, "unit_prices": {<schema>: <price>}}` (12 OPRA schemas
per mode). The sanitizer now recognizes this alongside the earlier forms and
normalizes `unit_prices` to the canonical `schemas` block — the mode name and
every schema key are preserved and each price passes through the same
representation normalization (`str(price)`), so the confirmed float prices survive
to `parse_unit_price_snapshot`, which remains the sole authority on price
validity. `unit_prices` is mapped to `schemas` purely to reach one canonical
internal block shape; nothing else about parsing, mode/schema selection, Decimal
validation, duplicate-mode rejection, or hashing changed.

Wrapper disambiguation is strict and fail-closed: an item with `mode` + `schemas`
is canonical; `mode` + `unit_prices` is the confirmed form; an item declaring
**both** `schemas` and `unit_prices` is ambiguous; a `mode`/`unit_prices` item
with any unexpected sibling key, a `unit_prices` without `mode`, or a `mode`
without a wrapper all fail closed. Duplicate feed modes are still preserved (never
merged) so the parser rejects the ambiguity. The correction was implemented and
tested entirely offline; **one new controlled live probe is still required**
before the metadata checkpoint may be resumed, and acquisition remains
unauthorized. This milestone did not run a live probe — do not assume the live
call now passes.

### Stale-checkpoint resume and metadata deadline

`data pilot prepare --resume` now means *resume this exact checkpoint or fail
closed*: a missing, stale, hash-invalid, plan-incompatible, or otherwise-invalid
checkpoint exits nonzero and never silently starts a fresh generation (the prior
behavior, which discarded completed endpoints). A checkpoint older than
`checkpoint_max_age_minutes` (still 30) may be resumed only with
`--allow-stale-checkpoint-sha256 <64-lowercase-hex>` matching the checkpoint's
exact bytes; this bypasses **age only** — every schema, canonical-hash,
plan/source/split/policy, request, endpoint-hash, and configuration-compatibility
check remains mandatory, and completed endpoints are preserved rather than
re-fetched. The option is valid only with `--resume`.

`total_run_deadline_seconds` is raised to `7200` so one bounded invocation can
complete the 59 pending endpoints (worst case ≈ 21 OPRA `cbbo-1m` costs × 120 s ×
2 attempts). Because that is an operational control (it changes no request, budget,
or cost semantics), `checkpoint_compatibility.py` lets a checkpoint bound to the
prior `540`-second config resume: the stored config hash must equal the current
hash or a hand-verified prior hash whose only field difference is the deadline
(see amendment 009). Any scientific/budget difference fails closed. Everything was
implemented and tested offline; a separate authorized live milestone is still
required to resume and complete the checkpoint, and acquisition remains
unauthorized.

## Fresh provider cost recheck (`data pilot recheck-cost`)

Before a manual purchase authorization, `data pilot recheck-cost` obtains a
fresh `metadata.get_cost` quote for the **exact frozen 25-request plan** and
compares it against the completed preflight totals and the spending gates. It
uses `metadata.get_cost` (not the naive `dataset x schema` cross-product loop):
the frozen plan is the sole source of quoted combinations, each request keeps
its recorded symbology (`parent` for `SPY.OPT`, `raw_symbol` for `SPY`) and its
exact start/end (the 600 s closing-quote windows, never a whole month). Schemas
are validated per dataset via one `metadata.list_schemas` call each; an
unsupported frozen schema fails before any quote.

Every quote is a direct provider response — no derived unit-price fallback is
substituted for a failure, so a failed quote makes the run `incomplete` with
`authorization_ready=false` and partial evidence preserved. Costs use
`Decimal(str(cost))`; each quote is isolated in a spawn child with at most two
attempts and deterministic cleanup. The command constructs one `databento`
client via the env-based key, calls only approved metadata methods, and never
runs `timeseries.get_range`, batch, live, acquisition, or authorization. It is a
separate, reusable pre-authorization check that does **not** replace the manual
portal attestation (see research protocol amendment 012).
