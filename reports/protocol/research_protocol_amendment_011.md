# Research Protocol Amendment 011 — Guarded Pilot Purchase-Authorization Package

**Date:** 2026-07-15 (UTC). **Repository revision:** `d3d43d2f7491ec664deee5eb791d9074285e7e51`.
**Amends:** Amendment 010 (completed metadata preflight).
**Companion:** `reports/data/pilot_purchase_authorization_packet.md`.

## 1. Basis: completed metadata evidence

Checkpoint `ede035f92b30c3b15d6fa0a9c61991225e216c943e86f059b7c52ed03b435706`
is complete (75/75 endpoints, 25/25 requests) and validates against the
frozen source/split/policy manifests. Costs: 24 provider responses plus one
derived fallback (`e536e625287188b9`: 5,305,600 bytes × 2.0 USD/GiB ÷ 2³⁰ =
`0.009882450103759765625`; ×1.25 conservative). Raw total
`0.460514456032759765625`; conservative total
`0.46298506855869970703125`; all gates pass.

## 2. Purchase-review layer (new)

A review layer now sits IN FRONT of the existing execution gates
(`authorization.py`, `attestation.py`, the journal-backed executor); it does
not replace them. New tracked contracts:

- `data_contracts/pilot_purchase_authorization.schema.json` — the human
  purchase decision, bound to repository HEAD, plan hash, completed
  checkpoint bytes, request-manifest hash, frozen manifest hashes,
  configuration-compatibility evidence, SDK version, exact Decimal raw and
  conservative totals, the authorized ceiling, the frozen scope, UTC
  creation/expiry, operator label, the exact authorization statement, and a
  canonical self-hash. Strict `additionalProperties: false`; Decimal
  strings; lowercase 64-hex patterns; no secret-bearing fields.
- `data_contracts/pilot_portal_attestation.schema.json` — a manual,
  short-lived record of the portal-displayed cost estimate for the bound
  scope (never invented or scraped by tooling), hash-bound to the same
  checkpoint and request manifest.

### Contract hardening (v1.1 schemas)

Both schemas were subsequently hardened:

- **True null template state.** Template artifacts now carry actual JSON
  `null` for operator-supplied fields (ceiling, statement, operator label,
  timestamps, self-hash for the authorization; estimate, confirmation,
  timestamps, self-hash for the attestation), replacing the earlier
  epoch-timestamp sentinels. `if/then/else` conditioned on `template_only`
  enforces this: `template_only=true` requires those fields to be `null`
  and the decision flags false; `template_only=false` requires valid
  non-null values (fixed-point Decimal strings, non-empty statement/label,
  date-time timestamps, lowercase 64-hex self-hash). A completed artifact
  with a null required field, or a template with a filled field, is
  schema-invalid.
- **Explicit portal repository binding.** The portal attestation now
  carries a required `repository_head` (`^[0-9a-f]{40}$`) in both states.
- **Three-way HEAD agreement.** The validator now requires the repository
  binding to agree across the purchase authorization, the portal
  attestation, and the expected review context (the runner binds the same
  HEAD it passes into the expected context). Any disagreement yields a
  `repository_head_mismatch` rejection. Epoch-sentinel timestamps on a
  completed artifact fail as `invalid_timestamps`/`authorization_expired`.

Validator: `neuralmarket.data.acquisition.purchase_review` — pure offline,
no provider import, returns structured secret-free rejection reasons.
Rules: ceiling ∈ [conservative total, drift ceiling] and ≤ $5.00 hard cap;
authorization validity ≤ 24 h; attestation validity ≤ 30 min; future-dated
artifacts fail; exact-statement matching (the required wording with the
ceiling amount; "looks good"/"continue"/amount-less approvals all reject);
template/unauthorized/unattested states reject; self-hash tampering
rejects; a consumption marker or `consumed=true` rejects; the execution
journal blocks on same-plan consumption, any completed/billed paid
request, or unresolved billing reconciliation.

## 3. Expiration and one-time use

Authorization: ≤ 24 hours, single-use. Portal attestation: ≤ 30 minutes.
Both must be valid at execution start. Consumption is double-tracked: the
review layer writes a consumption marker before the CLI is invoked, and the
execution layer's SQLite journal reserves-then-consumes its own
authorization hash. Failed acquisitions are never retried automatically;
retry requires review plus a new or explicitly renewed authorization.

## 4. Fail-closed proof (offline, fake artifacts only)

`tests/unit/data/acquisition/test_purchase_review.py` (25 tests): missing
authorization, template-only, `authorized=false`, missing attestation,
`attested=false`, ceiling below conservative, ceiling above drift limit,
checkpoint/plan/request-manifest hash mismatches, expired authorization,
expired attestation, future-dated artifacts, six ambiguous approval
wordings, reuse via marker and via `consumed=true`, paid-journal conflict,
tampered self-hash — all rejected; a fully valid fake pair reaches the
final pre-provider gate with zero rejections; an autouse guard proves no
test imports `databento`. The reconciled `confirmed_not_billed` prior
journal (different plan hash, zero completed requests) is proven
non-blocking while remaining surfaced for review.

## 5. Separation of preparation from authorization

This milestone created templates
(`template_only=true, authorized=false, attested=false`, null
statement/estimate/hashes), the review packet, and an acquisition-runner
TEMPLATE that throws unconditionally while marked as a template and cannot
pass validation with template artifacts. No completed authorization, no
attestation, no provider call, no checkpoint mutation, and no market-data
operation occurred. The proposed `$0.50` ceiling is a documented
recommendation only. Purchase authority rests solely with Rohith through
the manual artifacts described in the packet.

## 6. Baseline deviation record (from Amendment 010's commit)

Commit `d3d43d2` included `.secrets.baseline` beyond its documented 3-file
scope because the mandatory pre-commit hook requires new detector findings
to be registered: the sole added entry is the benign, already-committed
prior-config-hash constant in
`src/neuralmarket/data/acquisition/checkpoint_compatibility.py` (line 33).
It is a configuration SHA-256, not a credential; no detector was disabled,
no report content was suppressed, and the entry must remain.
