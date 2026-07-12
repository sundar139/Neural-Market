# Canonical Contracts

Canonical contracts are defined once as typed Pydantic models and expressed in
three consistent forms:

- **Pydantic models** — row-level semantic validation.
- **PyArrow schemas** — table-level storage contracts (`decimal128` prices,
  UTC timestamps, `date32` session dates).
- **JSON Schema** — language-neutral, versioned documents under `data_contracts/`,
  derived from the same typed models so the forms cannot silently diverge. The
  `data contracts validate` command fails if a committed schema drifts from its
  model.

## Contracts

| Contract | Purpose |
| --- | --- |
| `UnderlyingDailyBar` | Daily OHLCV bar for the underlying. |
| `OptionDefinition` | Point-in-time option contract definition. |
| `OptionQuoteSnapshot` | End-of-day consolidated option quote. |
| `RejectedRecord` | Explicit, typed record of why a row was rejected. |

## Rules that prevent silent errors

- Event timestamps are timezone-aware and normalized to UTC; naive timestamps are
  rejected. Session dates are kept separate as calendar dates.
- Prices and strikes use `Decimal`; no binary-float equality is used for financial
  validation.
- Currencies are explicit uppercase ISO-style codes.
- OHLC relationships are enforced (`high >= open,low,close`; `low <= open,high,close`).
- Option type is a strict `call`/`put` enum.
- Quotes with `ask < bid` (crossed) are rejected; locked quotes (`bid == ask`)
  remain valid but are flagged via `is_locked`; a missing side is a validation
  error, never silently coerced to zero.
- Underlying prices carry an explicit `adjustment_status` so unadjusted prices can
  never be mistaken for adjusted ones. No split/dividend adjustment is done yet.

## Why point-in-time option definitions

Collapsing option definitions into a single final-state table would leak the
future existence of contracts into the past (contract-listing lookahead). Storing
definitions as they were known at each `definition_timestamp` preserves the
point-in-time universe an agent could actually have traded.

## End-of-day quote snapshot policy

The planned snapshot rule (defined here, not yet applied to raw records):

> Use the final valid consolidated quote at or before 15:59:00 America/New_York,
> subject to a maximum quote age of five minutes.
