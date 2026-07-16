# Pilot Purchase-Authorization Packet — January 2019 (FOR REVIEW — NOTHING AUTHORIZED)

**Prepared:** 2026-07-15 (UTC), repository `d3d43d2f7491ec664deee5eb791d9074285e7e51`.
**Status:** No acquisition has occurred. No authorization exists. This packet asks
Rohith for a deliberate purchase decision; it grants nothing by itself.

## 1. What would be purchased

One-time historical market-data download from Databento for the frozen
January 2019 pilot plan (plan hash `5ee6126ca9e27e3d1909c58b4e555526d5894dcd9ea129faf8d6159973aff1fe`,
25 logical requests, window 2019-01-02 → 2019-02-01 UTC):

- **ARCX.PILLAR / SPY** — `definition`, `ohlcv-1d`, `statistics` (underlying).
- **OPRA.PILLAR / SPY.OPT** (parent) — `definition` plus `cbbo-1m` quote
  windows (10 minutes before each XNYS session close).

Purpose: the capped pilot that qualifies data quality, storage, and cost
accounting before any full-study acquisition decision. The scope is frozen;
nothing outside these hashes can be requested.

## 2. Expected cost (validated live metadata, 2026-07-15)

| Quantity | USD (exact Decimal) |
| --- | --- |
| Raw expected total | `0.460514456032759765625` |
| Conservative expected total (single derived cost × 1.25) | `0.46298506855869970703125` |
| Maximum validated drift total (1.5× tracked) | `0.6907716840495` |
| Largest validated request | `0.243695452809` |
| Hard project per-request cap | `1.00` |
| Hard project total cap | `5.00` |

24 of 25 costs came directly from the provider; one (`e536e625287188b9`)
is a derived fallback with full provenance, already carrying its 1.25×
margin in the conservative total.

## 3. Proposed ceiling — RECOMMENDATION ONLY

**Proposed maximum purchase ceiling: `0.50 USD`.**

- It exceeds the conservative estimate (`0.46298…`), leaving headroom for
  benign rounding without permitting meaningful overrun.
- It is 10× below the `$5.00` hard project cap and below the validated
  drift ceiling (`0.69077…`).
- Execution must stop before any request that would push spend past the
  authorized remaining balance; nothing may silently raise the ceiling.

A different amount is valid only when it is **≥ `0.46298506855869970703125`**,
**≤ `0.6907716840495`**, and ≤ the `$5.00` hard cap. An authorization below
the conservative total fails validation by design.

## 4. What Rohith must do to authorize (two manual artifacts)

Nothing proceeds until BOTH artifacts are completed manually from the
templates in `reports/data/execution/authorization/` (ignored, local):

1. **Portal cost attestation** (`pilot_portal_attestation_template.local.json`
   → `pilot_portal_attestation.local.json`): open the Databento portal
   yourself, view the cost estimate for this exact scope, and record the
   portal-displayed estimate, observation time, and your confirmation.
   Valid for **30 minutes** from observation. The agent never invents,
   scrapes, or automates this value. The attestation carries an explicit
   `repository_head` that must match the authorization and the runner; the
   template ships with its fields as JSON `null` until you complete them.
2. **Purchase authorization**
   (`pilot_purchase_authorization_template.local.json` →
   `pilot_purchase_authorization.local.json`): set the ceiling, timestamps
   (validity ≤ **24 hours**), your operator label, recompute the review
   hash, and include this exact statement with your chosen amount:

   > I authorize NeuralMarket to execute the bound January 2019 pilot
   > acquisition with a maximum total charge of USD `<amount>`. I understand
   > that this permits paid Databento historical market-data requests only
   > for the hashes and request scope recorded in this authorization.

   The validator rejects "looks good", "continue", "probably okay",
   "run it", any wording without the amount, conditional approval, missing
   checkpoint binding, and any statement the agent wrote on your behalf.

Both artifacts are bound to the completed checkpoint
(`ede035f92b30c3b15d6fa0a9c61991225e216c943e86f059b7c52ed03b435706`), the
request manifest (`8e63d7b0de534173ce65ee7992f4e82239f531d16bbb4f67866771ac1f0bc9a8`),
the frozen manifests, and repository HEAD; changing any of these invalidates
them. The execution CLI additionally requires its own signed
`pilot_authorization` + `portal_limit_attestation` artifacts (existing
execution-layer gates) before any paid call.

## 5. Single use, revocation, and pricing changes

- The authorization is **single-use**: the runner writes a consumption
  marker before invoking the CLI, and the execution journal independently
  reserves/consumes the execution-layer authorization. A failed run is
  never retried automatically; any retry needs review and a fresh or
  explicitly renewed authorization.
- **To decline:** do nothing — the templates are inert and expire never
  having authorized anything. **To revoke** a created-but-unused
  authorization: delete your local completed artifact or let it expire
  (≤ 24 h); nothing else holds spending power.
- **If provider pricing changes:** the portal estimate you attest is your
  cross-check. If the portal shows more than the ceiling you authorize, do
  not sign; the run also stops fail-closed at the first request that would
  exceed the authorized balance, and the drift ceiling caps validated
  totals at `0.69077… USD`.

## 5b. Fresh cost recheck before you authorize

Before completing the authorization, run `data pilot recheck-cost` (see research
protocol amendment 012). It re-quotes the exact frozen 25 requests through
Databento's `metadata.get_cost`, validates each dataset's schemas, and confirms
the fresh provider total still passes the gates (largest ≤ $1.00, total ≤ $5.00,
conservative ≤ `0.6907716840495`). It is provider-only (no fallback), authorizes
nothing, and does not replace the portal attestation. If the fresh total exceeds
your chosen amount or the drift ceiling, reconsider the amount within the range —
do not raise it silently.

## 6. Current state

- Metadata preflight complete (75/75, 25/25); checkpoint validated against
  frozen manifests.
- Prior 2026-07-14 paid attempt: definitively reconciled
  `confirmed_not_billed` (0 records, 0.00 USD); its journal history remains
  and is surfaced — the review gate blocks on any unresolved billing,
  completed paid request, or same-plan consumption.
- **No acquisition has occurred. No credential is stored in any artifact.**
