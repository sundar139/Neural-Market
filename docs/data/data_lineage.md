# Pilot data lineage

```text
frozen source manifest + sealed split manifest + acquisition policy
                              |
                       pilot configuration
                              |
                       draft request specs
                              |
                fresh metadata-only estimates
                              |
                 final request manifest + hash
                              |
  future authorized provider response (DBN, immutable raw artifact)
                              |
                 validated DBN + checksum sidecar
                              |
        deterministic normalized Parquet + provenance sidecar
                              |
                       synthetic quality report
```

Every request has a stable specification hash before estimation and a final
request hash after the fresh estimate is bound. The canonical plan hash binds
all final request hashes, dependency hashes, logical output paths, aggregate
cost and maximum request cost, caps, authorization requirements, calendar,
provider-client version, and implementation revision.

Raw files are never overwritten. Their sidecar records request identity,
request hash, logical path, checksum, and byte count. Normalized files retain
the source request, dataset, schema, ingestion timestamp, raw checksum, and
pipeline version. Recovery reconciles journal state, raw and normalized files,
sidecars, checksums, request hash, plan hash, and DBN validation. Any
disagreement yields manual recovery or quarantine recommendation; recovery is
read-only and never contacts the provider.

DVC is initialized with no remote and no tracked data. Raw and normalized
directories remain ignored until a future approved data-governance decision.
