# Research Protocol Amendment 004 — Operational Pilot Execution Controls

## Status and unchanged scope

This amendment approves implementation and offline validation of the guarded
pilot executor. It does not authorize a purchase. The January 2019 training
boundary, sealed final test, original hypotheses, endpoints, USD 5.00 total
cap, and USD 1.00 per-request cap are unchanged. There is no current valid
authorization or portal-limit attestation. No paid pilot was executed and no
historical record or market artifact was produced.

## Restricted metadata architecture and timeout diagnosis

Preparation constructs `databento.Historical` only inside a spawned child and
immediately reduces it to `DatabentoMetadataProvider`. The facade exposes only
`metadata.get_record_count`, `metadata.get_billable_size`, and
`metadata.get_cost`; time-series, batch, and live capabilities are prohibited.
Only one request child and one endpoint are active at a time.

The two legacy unbounded runs ended while the first canonical request was the
narrowest durably identifiable location: `2750995e515e4f1a`,
`ARCX.PILLAR / definition`. The legacy path did not flush per-endpoint progress,
so the exact endpoint cannot be recovered. A sandboxed attempt separately
failed while awaiting `get_record_count`, but that does not prove the later
unbounded runs stalled at the same endpoint. Available evidence does not
establish whether the delay originated in the local HTTP stack, network path,
or remote processing.

Every new request runs in a Windows `spawn` child with a 120-second hard
deadline. The parent records the PID and flushed endpoint events, then
terminates, joins, and if necessary kills an overdue child. Timeouts are
`metadata_hard_timeout`, never uncertain billing. Tests identify a deliberately
hung `cost` endpoint, terminate and join its noncooperative child, and observe
zero remaining metadata children.

## Checkpoint and resume

The ignored `pilot_metadata_checkpoint.local.json` is written through a
flushed and fsynced `.partial` followed by atomic replacement after every
complete three-endpoint estimate. It binds source, split, policy, and config
hashes; calendar and Databento versions; estimator semantics; and all 25
ordered request-specification hashes. Corrupt, incomplete, negative, expired,
reordered, version-mismatched, or dependency-mismatched checkpoints fail
closed. Checkpoints expire after 30 minutes.

The five-category probe completed five estimates. The next bounded invocation
skipped those five, completed 17, and stopped with three pending at its run
deadline. The final invocation skipped 22 and completed the remaining three.
No partial invocation replaced the tracked plan.

## Final canonical metadata plan

- Plan hash: `9654fe1c2dfe98946560e27c6f51f110038613060461fdf75936edf1a7d0ae77`
- Requests: 25 logical requests / 75 successful endpoint calls
- Total estimate: USD `0.460514456033`
- Largest request: USD `0.243695452809`
- Metadata retries: 0
- Metadata hard timeouts: 0
- Total observed wall runtime across probe and resume invocations: 714.7 seconds
- Canonical order: three ARCX requests, OPRA definition, then 21 ascending
  January 2019 OPRA sessions

| Dataset | Schema | Requests | Estimated bytes | Estimated USD |
|---|---:|---:|---:|---:|
| ARCX.PILLAR | definition | 1 | 7,560 | 0.000112652779 |
| ARCX.PILLAR | ohlcv-1d | 1 | 1,176 | 0.000032857060 |
| ARCX.PILLAR | statistics | 1 | 3,712 | 0.000055313110 |
| OPRA.PILLAR | definition | 1 | 52,333,200 | 0.243695452809 |
| OPRA.PILLAR | cbbo-1m | 21 | 116,296,000 | 0.216618180275 |

The old hash `e86c20cc4e46db4fd6a8b9b3725aba3e58c16c78398bd8cd4e2aa179c34ad128`
is invalid after canonical-order and implementation-provenance changes.

## Paid execution and recovery controls

A valid short-lived portal-limit attestation and separately valid, hash-bound
authorization remain mandatory. After validation, fresh metadata preflight,
storage validation, and recovery inspection, authorization is reserved
transactionally. Provider-construction failure releases it. Consumption occurs
immediately before the first paid invocation.

The coordinator executes all requests sequentially. Each response is atomically
persisted and validated as raw DBN, reopened from disk for Parquet
normalization, reconciled, and evaluated by schema-specific quality checks.
Validated raw resumes normalization without redownload; validated normalized
resumes quality only; complete requests are skipped. Uncertain completion
blocks automatic retry. Missing, corrupt, or partial state is quarantined or
requires manual recovery.

Synthetic evidence completes 25 raw, normalized, and quality lifecycles. An
identical second run skips all 25 and performs zero provider calls. Actual
billed cost remains unavailable pending portal reconciliation.

## Follow-up provider wiring and endpoint resume

A controlled execution attempt correctly stopped before authorization
reservation when fresh metadata validation failed on request
`d5352ffb04e4bc83` (`OPRA.PILLAR / cbbo-1m`, 2019-01-02). Its first
`get_record_count` completed, `get_billable_size` then failed after about 30.5
seconds, and two subsequent request retries failed while awaiting
`get_record_count`. The evidence locates the waits but does not distinguish a
local HTTP, network-path, or remote-processing cause.

Review then found that the CLI still injected an intentionally unreachable
paid-provider factory. The follow-up replaces it with the existing
`DatabentoPaidHistoricalProvider`; construction creates only the historical
root client and performs no range, batch, or live operation. A non-network
readiness check runs before journal creation or authorization reservation.
Construction failure continues to release the reservation, and consumption
still occurs immediately before the first adapter invocation.

Metadata checkpoints now persist each successful record-count, billable-size,
and cost result with its completion time and deterministic response hash.
Within one fresh checkpoint generation, resume skips valid completed endpoints
and starts at the failed endpoint. An expired generation is discarded in full;
dependency or endpoint-hash mismatches fail closed. Atomic checkpoint writes
and the 30-minute freshness bound are unchanged.

The prior local authorization and portal attestation were removed. This change
does not authorize or complete the paid pilot; a new explicit authorization and
manual portal attestation are required after review. The accepted plan hash and
tracked estimates remain unchanged, and no paid request or market-data download
occurred during this follow-up.

The targeted OPRA resume reused its completed record-count and billable-size
results and called only `get_cost`, which completed in 16.73 seconds. The full
25-request validation then completed across three bounded invocations with the
unchanged USD `0.460514456033` total, USD `0.243695452809` largest request, and
plan hash `9654fe1c2dfe98946560e27c6f51f110038613060461fdf75936edf1a7d0ae77`.
Two hard metadata timeouts were retried; completed endpoints remained
checkpointed. All 75 endpoint results are present, no metadata child remains,
and paid-provider constructions, range calls, downloaded records, batch calls,
and live calls remained zero.
