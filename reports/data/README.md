# Data Reports

Generated, account-specific data reports are written here and are **ignored by
Git**:

- `source_qualification.local.json` — the full qualification report, including
  cost estimates and dataset ranges for your account.
- `acquisition_plan.local.json` — the full budget-constrained acquisition plan:
  per-window metadata estimates, sampled cost statistics, candidate strategy
  projections, the pilot plan, and the final-test reserve projection.
- `split_manifest_repeat.local.json` — a scratch split manifest used to check
  determinism against the tracked one.

Only this README is tracked. These reports never contain the API key, account
or billing identifiers, payment information, raw exceptions, or market values
— but because they carry account-specific cost and entitlement details, they
stay local. Account-neutral metadata belongs in `data/manifests/` instead
(`source_manifest_v1.json`, `split_manifest_v1.json`,
`acquisition_policy_v1.json`).

Pilot metadata checkpoints and endpoint diagnostics use ignored `*.local.*`
paths. They contain dependency hashes, request identities, estimates, and safe
timing events, but never credentials, headers, response bodies, or market data.

Manual billing reconciliation evidence lives under
`reports/data/execution/reconciliation/` as ignored `.local.json` and
`.local.sqlite` files. These artifacts bind the execution ID, request ID, plan
hash, authorization hash, manual portal status, artifact hash, and any immediate
superseded reconciliation hash; they must not contain portal HTML, screenshots,
API keys, card data, or market records.

Live metadata-preflight evidence lives under
`reports/data/execution/metadata_preflight/` as ignored `.local.*` files:
byte-for-byte checkpoint backups plus sanitized unit-price probe results
(dataset, selected feed mode, schema, decimal price, hashes, child exit/cleanup).
They never contain API keys, authorization headers, account identifiers, or raw
SDK objects. The observed Databento `0.81.0` `list_unit_prices` response is a list
of maps of feed mode to schema to unit price; the production sanitizer normalizes
it (and the earlier canonical/dict forms) into one `{mode, schemas}` block per
mode, preserving duplicate modes for downstream rejection and failing closed on
malformed responses. On failure the isolated child returns a sanitized,
versioned `UnitPriceFailureDiagnostic` (failing stage, stable failure code,
bounded price-free structural summary, structural fingerprint, child exit code).
The summary and fingerprint capture only value types, mapping/schema key names,
lengths, and truncation flags — never prices, scalar values, credentials, or
`repr()` of arbitrary objects — so probe evidence stays free of prices and
account data while remaining diagnosable. The confirmed Databento `0.81.0` shape
is a list of `{"mode": <str>, "unit_prices": {schema: price}}` items; the
sanitizer normalizes `unit_prices` to the canonical `schemas` block, preserves
duplicate modes for downstream rejection, and fails closed on ambiguous
(`schemas` + `unit_prices`) or malformed wrappers. Downstream Decimal/mode/schema
validation is unchanged.

Cost-fallback checkpoint backups live under
`reports/data/execution/cost_fallback/` as ignored `.local.json` files. They are
byte-for-byte copies of the metadata checkpoint taken before derived-cost work
(estimator build and metadata-runner integration),
carrying the same dependency hashes, request identities, and safe timing events,
and never credentials, response bodies, or market data.

Paid-failure diagnostics live under `reports/data/execution/diagnostics/` as
ignored `.local.json`, `.local.sqlite`, and `.local.patch` files. They may record
sanitized request parameters, local adapter source locations, Databento client
method signatures, classification, and retry-safety state, but must not contain
API keys, authorization headers, account identifiers, portal screenshots, raw
market records, DBN/DBZ files, or paid-provider response bodies.
# Data reports and pilot evidence

Local preflight, recovery, environment, and audit outputs use the `.local`
suffix and are ignored. The tracked acquisition policy, source, split, and
final pilot request manifest contain reproducible hashes and no credentials or
market observations. See [the pilot acquisition protocol](../../docs/data/pilot_acquisition.md)
and [the lineage contract](../../docs/data/data_lineage.md).
