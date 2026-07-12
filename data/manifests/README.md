# Manifests

Small, deterministic research metadata is tracked here. No market-data records are
stored in this directory.

| File | Tracked | Produced by |
| --- | --- | --- |
| `split_manifest_v1.json` | yes | `neuralmarket data split freeze` (offline) |
| `source_manifest_v1.json` | yes | `neuralmarket data qualify` (needs a credential) |

Both manifests are canonicalized (UTF-8, sorted keys, ISO dates) and carry a
SHA-256 `manifest_hash` computed over the payload minus its own hash and its
`generated_at` timestamp. Verify them with:

```powershell
neuralmarket data manifests verify --source data/manifests/source_manifest_v1.json --split data/manifests/split_manifest_v1.json
```

Manifests contain only account-neutral metadata: dataset/schema identifiers,
symbol conventions, available ranges, split boundaries, session hashes, policy
statements, and hashes. They never contain credentials, account or billing
identifiers, per-account costs, or market values. Account-specific qualification
output is written to `reports/data/*.local.json`, which is ignored by Git.
