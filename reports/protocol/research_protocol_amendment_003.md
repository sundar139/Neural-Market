# Research Protocol Amendment 003 — Guarded January 2019 acquisition pilot

Date: 2026-07-13

## Scope and unchanged hypotheses

The pilot is January 2019 training-only data for SPY on XNYS. It contains
exactly 21 exchange sessions and 25 requests: ARCX definition, daily OHLCV,
statistics, OPRA definitions, and one final-ten-minute OPRA quote window per
session. The original research hypotheses are unchanged; this amendment
governs acquisition and lineage only.

The fresh metadata-only pilot estimate is USD 0.460514456033, with a largest
single request of USD 0.243695452809. The hard aggregate cap is USD 5.00 and
the hard individual cap is USD 1.00. The authorization-ready manifest records
the exact request-plan hash and dependency hashes.

## Authorization and execution controls

The transport is direct DBN historical range output. A future authorized run
must use one-time authorization bound to the exact plan, a dual guard requiring
the plan hash confirmation and authorization file, and durable SQLite
consumption before paid-provider construction. The journal records the
authorization hash, plan hash, consumed timestamp, execution ID, maximum
authorized spend, and currency. A timeout after provider submission is treated
as uncertain billing; no automatic redownload occurs.

Raw DBN is immutable. It is written to a partial file, flushed, fsynced,
validated, checksummed, accompanied by atomic metadata and checksum sidecars,
and atomically renamed into its relative logical path. Normalized Parquet is a
deterministic derivation with provider timestamps, raw symbol and instrument
ID when available, provenance columns, stable compression, row-count
reconciliation, schema fingerprint, and checksum.

Recovery is read-only by default, never retries, never deletes partial files,
and never contacts the provider. Quality evaluators cover ARCX daily and
statistics data plus OPRA definitions and quotes, including session coverage,
duplicates, prices, OHLC, volumes, timezone, publishers, contract metadata,
quote validity, quote age, final valid quotes, and rejection reasons.

## Reproducibility and safety status

DVC is initialized without a remote. There is no current purchase
authorization, zero downloaded records, zero paid requests, zero batch jobs,
zero live connections, and zero acquisition credits spent. The final-test
split remains sealed and has not been queried. No market observations are
included in the plan or amendment.

The request plan hash and all final dependency hashes are in the tracked
manifest and are verified offline before any future authorization can be
accepted.

## Final manifest identity

- Request count: 25; exact January 2019 XNYS session count: 21.
- Fresh total estimate: USD 0.460514456033.
- Largest request estimate: USD 0.243695452809.
- Plan hash: e86c20cc4e46db4fd6a8b9b3725aba3e58c16c78398bd8cd4e2aa179c34ad128.
- Source manifest hash: 3d31e373defbe43aa8eb30c453c1e65c1913d3103e336e02b26757fecd710604.
- Split manifest hash: 877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe.
- Acquisition-policy hash: ffce36b4e5da07f60c578e3743b320a6c5ce63e559433b473148423fbb4e9b6.
- Pilot configuration hash: 25451287f116e0da47b6e073a8da0931b48da1e5d00c7fa3d12c5bc59c7856c7.
- Fresh metadata evidence: 27 logical calls, 77 endpoint calls, 2 retries; no paid requests.
