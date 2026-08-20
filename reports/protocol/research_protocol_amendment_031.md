# Research Protocol Amendment 031

## V5 Primary Seed-03 Execution Authorization

**Date:** 2026-08-20
**Task:** NM-R4-V5-PRIMARY-EXECUTION-SEED-03-043
**Independent audit:** NM-R4-V5-SEED-02-ADJUDICATION-V2-AUDIT-042
**Audit verdict:** VALIDATED WITH NON-BLOCKING FINDINGS
**Seed-02 scientific status:** PRIMARY_VALID_COMPLETED
**Seed-03 execution recommendation:** AUTHORIZED

## Authorization basis

Independent audit 042 validated the corrected seed-02 adjudication v2. The raw
seed-02 execution remains PRIMARY_VALID_COMPLETED and its six-criterion result
remains PASS on frozen Gate diagnostics. The audited adjudicator implementation
is frozen and unchanged in task 043.

This amendment authorizes exactly one additional primary scientific execution:

- **Member:** v5-seed-03

No other member, reserve, validation, external validation, final test, or hedging
execution is authorized by this amendment.

## Exact seed-03 authorization and configuration identity

- Authorization path: `reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-03.json`
- Authorization SHA-256: `61224c0f59b4d0985d6f40cbe3f0e2e6d95bdf663594b8ba9c300afae14bc902`
- Authorization Git blob: `9e5de9d03042429ba12f0324f6d8bb51701f5228`
- Member: v5-seed-03
- replicate_seed: 10281
- model_init_seed: 10281
- data_seed: 10282
- eval_seed: 8283
- Full config hash: `e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955`
- Run prefix: `e333325c804d95d2`
- Family methodology: `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`

## Runner, contract, schedule, and recipe identities

- Runner path: `reports/research/evidence/structured_vol_v5_replicate_training_runner.py`
- Runner Git blob: `7b46e0f6c805687977cd685ebb97741bd4243cbe`
- Execution-contract-v5 path: `reports/research/structured_vol_v5_training_execution_contract_v5.json`
- Execution-contract-v5 Git blob: `84a59c4d966b349be705a8a29fad07f81282ebdc`
- Schedule path: `reports/research/structured_vol_v5_seed_schedule_v1.json`
- Schedule Git blob: `558d08bfee98dbd0c170d65e6a9b1737700c9e98`
- Schedule SHA-256: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`
- Canonical recipe: `20d90f7484fe5df7cd62755a5810c8de78e5e92f`
- The canonical recipe remains an ancestor of HEAD and its tree contains the
  frozen runner, contract-v5, and schedule blobs.

## Audited adjudicator identity

- Adjudicator path: `reports/research/evidence/structured_vol_v5_primary_adjudicator.py`
- Adjudicator SHA-256: `82c867151a257381dd35f4f32648e054a6266ad8f753096b7d8da420eb28c2ea`
- Adjudicator Git blob: `39a45348056eef339958ae8298ff5d0886476cd9`
- The adjudicator remains unchanged in task 043. Non-blocking findings from
  audit 042 (dict/list TypeError edge case, window-count derivation location)
  are acknowledged and deferred; changing the helper would invalidate the
  audited implementation, so seed-03 must be adjudicated using the exact
  audited helper above.

## Six-criterion semantics

Amendment 029 six-criterion semantics remain unchanged:

1. `best_selection_total < initial_selection_total`
2. `0.50 <= variance_ratio <= 2.00`
3. `0.50 <= terminal_dispersion_ratio <= 2.00`
4. `path_uniqueness_fraction >= 0.99`
5. `return_acf1_abs_diff <= 0.25`
6. `drift_diffusion_rms_ratio <= 0.50`

Governed pass is the conjunction of all six. Terminal Wasserstein remains
REPORT_ONLY.

## Training-structure metadata provenance

Window-count and training-series metadata in the seed-03 adjudication will be
independently reconstructed from the frozen training pipeline (existing
training-only data and window construction helpers, read-only), not copied from
prose literals. Expected family-invariant values (sessions 926, returns 925,
derived windows 841, fit 672, selection 107, embargo gap 62) will be recomputed
and the derivation source recorded.

## Execution scope and prohibitions

- Exactly one seed-03 scientific invocation is permitted (`--execute` once).
- Seed-04 and seed-05 remain NOT_AUTHORIZED.
- No retry after irreversible start.
- No reserve fallback.
- No parameter adaptation based on seed-01 or seed-02.
- Validation, external validation, final test, and hedging remain prohibited.
- External validation remains CLOSED 2/2; third construction is FORBIDDEN.

## Next

Execute v5-seed-03 once under the frozen runner, then adjudicate with the
exact audited helper and record governed status per Amendment 029.
The next task after execution must be an independent Claude read-only audit
of seed-03 raw execution and adjudication-v2 before seed-04 can be considered.
