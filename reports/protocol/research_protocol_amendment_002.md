# NeuralMarket Protocol Amendment 002 — Budget-Constrained Data Acquisition

Date: 2026-07-12
Base commit: 81064f9 (source qualification and frozen data contracts)
Status: acquisition planned and budget-bounded; no data acquired. This
amendment does not alter the hypotheses, endpoints, primary research
methodology, approved sources, study dates, or split design of Research
Protocol v1 or Amendment 001.

## 1. Why the full OPRA request was rejected

The qualified source (Amendment 001) requires approximately $1,018 to acquire
in full, dominated by the OPRA `cbbo-1m` full-study option-quote history
(approximately $990, 531 GB, 6.64 billion records). The project's available
Databento credit is $125 — acquiring the full history is not possible.

## 2. Available-credit constraint

Available Databento credit: **$125.00**.

## 3. Project-spend ceiling

Maximum project spend: **$95.00** (leaves at least the unspent reserve below
untouched even if the full cap is used).

## 4. Unspent reserve

Minimum unspent reserve: **$30.00**, enforced as an invariant:
`maximum_project_spend_usd + minimum_unspent_reserve_usd <= available_credit_usd`
(`95.00 + 30.00 = 125.00 <= 125.00`).

## 5. Pilot ceiling

Maximum pilot spend: **$5.00**. The pilot is a bounded, training-only,
one-calendar-month validation of real quote availability, billed size, and
cost — never a production acquisition.

## 6. Ten-minute close-window design

Every OPRA quote-cost estimate uses the **final 10 minutes** before each
session's scheduled close (regular or early), read from the XNYS calendar's
actual close and converted to timezone-aware UTC. Definition/daily/statistics
estimates instead use whole-day-multiple ranges, since Databento's estimators
may overreport non-conforming ranges.

## 7. Daily, twice-weekly, and weekly strategies

Three concrete candidate strategies were generated and projected:

- **Strategy A** — daily close windows (every development session).
- **Strategy B** — twice-weekly close windows (Tuesday and Thursday sessions
  only; a non-session target weekday is omitted, never shifted).
- **Strategy C** — weekly close windows (Wednesday sessions only; same
  omission rule).
- **Strategy D** — contract-targeted close windows, representing the future
  state after the OPRA definition catalog is acquired and eligible contracts
  are selected locally. Its cost is explicitly `requires_definition_catalog`
  and is never fabricated.

## 8. Deterministic development-period sampling

Rather than one metadata call per session, up to three sessions per calendar
quarter of the development period (training + validation) are sampled purely
from calendar rules: the first Wednesday of the quarter's middle month, the
third Friday of the middle month (or its preceding session), and the final
session of the quarter. No market value is inspected to select these dates.

## 9. No test-period cost queries at session granularity

The final-test wave is never queried session-by-session. No metadata call is
ever issued against an individual final-test session.

## 10. Development-derived test reserve projection

The final-test quote reserve is projected only from development-period
sampling: `test_session_count * sampled_p95_cost * 1.50`
(`test_estimate_method = sealed_development_projection`), using only
calendar dates and the already-accepted split-manifest boundaries.

## 11. Explicit wave separation

Acquisition is modeled as four explicit waves, each requiring separate manual
authorization before any paid request:

1. **Catalog wave** — ARCX definitions/daily/statistics and OPRA point-in-time
   definitions, estimated separately for training and validation (development)
   and, separately, reserved for the test period. Never merges final-test
   definitions into development storage.
2. **Pilot wave** — one calendar month, training only, capped at $5.
3. **Development quote wave** — training and validation OPRA quotes, capped by
   `maximum_development_quote_spend_usd`.
4. **Final-test quote wave** — sealed; `purchase_authorized = false`; no
   session-specific metadata calls; acquired only after the model and
   experimental configuration are frozen.

## 12. No download authorization

No download, batch, or live-streaming call is made anywhere in this
milestone. `AcquisitionGuardedClient` raises `AcquisitionNotAuthorizedError`
on any attempt to reach `timeseries`, `batch`, `live`, `get_range`,
`get_range_async`, `submit_job`, or `download`.

## 13. Required manual approval before every paid wave

`require_manual_purchase_approval = true` and `purchase_authorized = false`
in both the configuration and every tracked/local artifact. The recommended
strategy is reported as `recommended_not_authorized`, never auto-authorized.

## 14. Policy-manifest hash

`data/manifests/acquisition_policy_v1.json` field `manifest_hash`:
`affce36b4e5da07f60c578e3743b320a6c5ce63e559433b473148423fbb4e9b6` (see the
amendment log below for the full live run result).

## 15. Original hypotheses and primary endpoint unchanged

This amendment governs spending discipline for data acquisition only. The
research hypotheses, the primary CVaR-hedging endpoint, the approved
ARCX/OPRA source selection, the study dates, and the split design established
in Research Protocol v1 and Amendment 001 are unchanged.

## Amendment log

- 2026-07-12 — Amendment 002 drafted alongside the budget-constrained
  acquisition planner.
- 2026-07-12 — Live plan run executed against the qualified account
  (`neuralmarket data acquisition plan`, 95 metadata calls, 1 transient retry,
  zero downloads). Results:
  - Catalog wave: development total $16.61, test-reserved total $8.45.
  - Development-period sampled OPRA `cbbo-1m` ten-minute window cost (59
    quarterly-sampled sessions): min $0.01, median $0.02, mean $0.02,
    p75 $0.03, p95 $0.03, maximum $0.03.
  - Strategy A (daily, 1201 sessions): projected $45.04 — exceeds
    `maximum_development_quote_spend_usd` ($45.00) by $0.04; infeasible.
  - Strategy B (twice-weekly, 491 sessions): projected $18.41, worst-case
    $14.73 (uses the sampled maximum, not p95); satisfies every budget
    constraint; **recommended** (rank 1).
  - Strategy C (weekly, 245 sessions): projected $9.19; feasible, rank 2.
  - Strategy D (contract-targeted): `requires_definition_catalog`, unranked,
    no fabricated cost.
  - Pilot plan (2019-01, 21 training sessions): estimated total $0.46,
    well under the $5.00 cap.
  - Final-test reserve projection: $23.76 (528 sealed test sessions),
    within the $25.00 reserve; no session-specific metadata call was made
    against the test period.
  - Total committed if Strategy B proceeds: catalog $16.61 + pilot $0.46 +
    quotes $18.41 = $35.48, leaving $89.52 unspent (well above the $30.00
    minimum reserve).
  - `recommendation_status = recommended_not_authorized`;
    `purchase_authorized = false` throughout.
  - Source-manifest hash `3d31e373defbe43aa8eb30c453c1e65c1913d3103e336e02b26757fecd710604`;
    split-manifest hash `877caee3f7bb471a491c299a8673fdf1b386b12b9ba7f4d17bd52d2954bdcabe`;
    acquisition-policy-manifest hash
    `affce36b4e5da07f60c578e3743b320a6c5ce63e559433b473148423fbb4e9b6`.
  - Zero downloads, zero batch jobs, zero live connections; no vendor record
    file exists anywhere in the repository.
