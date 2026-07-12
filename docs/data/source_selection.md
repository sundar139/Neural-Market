# Source Selection

## Why vendor-neutral contracts

NeuralMarket qualifies a market-data vendor before committing to a large,
expensive historical download. Canonical contracts (`src/neuralmarket/data/contracts.py`)
are provider-neutral: no vendor class names, integer price encodings, or vendor
enum values appear in them. A later vendor adapter can be added under
`src/neuralmarket/data/sources/` without changing the canonical models, the split
logic, or any downstream consumer.

## Why Databento and OPRA

The first source qualified is Databento:

- `EQUS.SUMMARY` / `ohlcv-1d` for daily SPY underlying bars;
- `OPRA.PILLAR` / `definition` for point-in-time SPY option definitions;
- `OPRA.PILLAR` / `cbbo-1m` for consolidated (OPRA) option quotes.

OPRA-derived consolidated quotes give exchange-official best bid/offer across
venues, which suits end-of-day snapshot construction for the hedging study.

## What is and is not downloaded

Qualification issues only metadata, symbology, and cost-estimation requests. A
download guard (`GuardedClient`) hard-fails if the adapter touches time-series
retrieval, batch submission, downloads, or live subscriptions. No records are
downloaded in this work.

## How costs are estimated

Costs come from the provider's own metadata cost endpoint for representative
one-session and full-study requests — never guessed from row counts or marketing
prices. The account-specific report is written to an ignored local file; only
broad, account-neutral metadata is committed in the source manifest.

## Credential protection

`DATABENTO_API_KEY` is read from a local, ignored `.env`. It is never logged,
serialized, hashed into reports, or embedded in exceptions. A redaction helper
(`redaction.py`) scrubs credential-like strings from any message that is logged
or written.

## Adding another vendor later

Implement the `MarketDataSource` protocol (`sources/base.py`) in a new adapter,
translate that vendor's errors into the shared domain errors, and return the same
NeuralMarket-owned result types. Nothing downstream changes.
