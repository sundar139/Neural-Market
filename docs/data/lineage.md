# Pilot data lineage

The January 2019 pilot binds every mutable artifact to immutable inputs with SHA-256 hashes.

## Dependency chain

1. `source_manifest_v1.json` identifies the qualified provider, datasets, schemas, and symbology.
2. `split_manifest_v1.json` freezes chronological training/validation/test boundaries. The pilot may use training dates only.
3. `acquisition_policy_v1.json` defines permitted acquisition behavior and safety constraints.
4. `pilot_january_2019.yaml` defines the calendar, windows, retry policy, and spend caps.
5. `pilot prepare` records hashes for all four inputs plus calendar, provider, and implementation versions.
6. Each finalized request binds its immutable specification to fresh record-count, billable-byte, and cost estimates. Runtime estimate timestamps are recorded but excluded from deterministic hashes.
7. The plan hash binds the ordered finalized requests and dependency metadata.
8. A separately reviewed authorization binds that exact plan hash, all dependency hashes, spend caps, validity interval, confirmation phrase, and authorization hash.
9. The journal records durable authorization consumption and request state transitions before provider construction.
10. Raw DBN publication records the content checksum, byte count, request ID/hash, logical path, and storage timestamp; the journal has fields for provider response ID, record count, and request timing.
11. Normalized Parquet files carry request ID, source dataset/schema, raw checksum, pipeline version, and ingestion timestamp in columns and sidecars.
12. Quality reports summarize evaluator results without altering source data.

## Verification rules

- Recompute hashes from canonical JSON rather than trusting stored values.
- Resolve raw and normalized data-artifact paths beneath the configured data root before access.
- Require half-open request windows: `start <= record_timestamp < end_exclusive`.
- Never use final-test data for debugging, selection, or tuning.
- Treat missing files, sidecars, checksums, dependency mismatches, and unsupported journal versions as hard failures.
- Recovery is read-only; retries require a new explicit operator action.

The repository does not commit licensed raw data, normalized outputs, journals, local reports, credentials, or authorization files.
