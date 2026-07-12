# Acquisition Policy

## Why a budget-constrained planner

The full qualified OPRA request costs approximately $1,018 (dominated by
`cbbo-1m`, roughly $990 / 531 GB / 6.64 billion records). The project's
available Databento credit is $125 — far short. Rather than acquire the full
history, `neuralmarket data acquisition plan` compares cheaper close-window
sampling strategies against a hard budget and recommends one, without
spending anything.

## The budget model

`src/neuralmarket/data/acquisition/budget.py` defines `BudgetPolicy` with
`Decimal`-only money fields and a required invariant:

```text
maximum_project_spend_usd + minimum_unspent_reserve_usd <= available_credit_usd
```

Configured in `configs/data/acquisition/spy_daily_budgeted.yaml`:

| Field | Value |
| --- | --- |
| `available_credit_usd` | 125.00 |
| `maximum_project_spend_usd` | 95.00 |
| `minimum_unspent_reserve_usd` | 30.00 |
| `maximum_pilot_spend_usd` | 5.00 |
| `maximum_single_future_request_usd` | 10.00 |
| `maximum_development_quote_spend_usd` | 45.00 |
| `minimum_final_test_quote_reserve_usd` | 25.00 |

`purchase_authorized` must always be `false` in this milestone; the model
rejects a policy that claims otherwise. No purchase logic exists anywhere in
this codebase.

## Quote-window and definition-window rules

Every OPRA quote-cost estimate uses the **final 10 minutes** before the
scheduled session close (regular or early), computed from the XNYS calendar's
actual close and converted to timezone-aware UTC, half-open
`[window_start, window_end)`. Every definition/daily/statistics estimate uses
a **whole-day-multiple** UTC range instead, since Databento's estimators may
overreport non-conforming ranges.

## Deterministic development-period sampling

Instead of one metadata call per session, `quarterly_sample_sessions`
(`acquisition/calendar.py`) samples up to three sessions per calendar quarter
in the development period (training + validation), purely from calendar
rules — no market values are ever inspected:

1. **Ordinary-session sample** — first Wednesday of the quarter's middle month.
2. **Expiry-proxy sample** — third Friday of the middle month (or the
   preceding session if the Friday is not a trading day).
3. **Quarter-end sample** — the final session of the quarter.

Sampled costs feed `CostStatistics` (minimum, median, mean, p75, p95,
maximum) using an explicit nearest-rank percentile: `index = ceil(pct * n) - 1`.

## Candidate strategies

| ID | Name | Schedule |
| --- | --- | --- |
| A | Daily close windows | every development session |
| B | Twice-weekly close windows | Tuesday and Thursday sessions only (no shifting) |
| C | Weekly close windows | Wednesday sessions only (no shifting) |
| D | Contract-targeted close windows | pending the OPRA definition catalog; cost never fabricated |

A strategy's development-quote cost is projected as
`sessions * p95_cost * 1.25` (safety factor), with a worst-case projection of
`sessions * maximum_cost`. Feasible strategies (satisfying every budget
constraint) are ranked by highest session frequency, then lowest cost;
Strategy D is always unranked until its cost is known.

## Final-test reserve

The final-test wave is **never** queried session-by-session. Its cost is
projected only from development-period sampling:
`test_sessions * p95_cost * 1.50` (a larger safety factor, since the test
period is never directly sampled), recorded as
`test_estimate_method = sealed_development_projection`.

## The pilot wave

A bounded ($5 cap), training-only pilot validates real quote availability,
billed size, and cost before any larger acquisition. The training month is
selected by a pure calendar rule — the first complete calendar month in a
configured year with at least 18 valid XNYS sessions — never by inspecting
market values. The pilot plan documents exact request specifications but
contains **no callable download command**; execution requires a separate,
manually authorized step.

## Governance manifests

- `data/manifests/acquisition_policy_v1.json` — tracked, account-neutral:
  budget ceilings, approved datasets/schemas, the quote-window and sampling
  rules, candidate strategy IDs, the ranking rule, the recommended strategy,
  and a canonical hash. Never contains account balances, API keys, or
  detailed cost responses.
- `reports/data/acquisition_plan.local.json` — ignored, account-specific: the
  full per-window estimates, cost statistics, strategy projections, and pilot
  plan.

`neuralmarket data acquisition verify` cross-validates both offline: schema
and hash validity, budget-invariant arithmetic, and agreement between the
report and the manifest on the recommended strategy and every accepted-input
hash.

## What this milestone never does

- Never calls `timeseries`, `batch`, or `live` — an `AcquisitionGuardedClient`
  raises `AcquisitionNotAuthorizedError` on any attempt, including
  `get_range`, `get_range_async`, `submit_job`, and `download`.
- Never downloads, previews, or batches a single record.
- Never sets `purchase_authorized = true`.
- Never queries final-test sessions individually.
