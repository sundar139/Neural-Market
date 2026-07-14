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
# Data reports and pilot evidence

Local preflight, recovery, environment, and audit outputs use the `.local`
suffix and are ignored. The tracked acquisition policy, source, split, and
final pilot request manifest contain reproducible hashes and no credentials or
market observations. See [the pilot acquisition protocol](../../docs/data/pilot_acquisition.md)
and [the lineage contract](../../docs/data/data_lineage.md).
