# Research Protocol Amendment 028

## V5 Primary Training Authorization Freeze and Execution Provenance Closure

**Date:** 2026-08-19
**Task:** NM-R4-V5-PRIMARY-AUTHORIZATION-FREEZE-037
**Prior:** runner v5 `41042ad78ed6348d9b1fa11a4ae7d582e3e0e104` (blob `7b46e0f6c805687977cd685ebb97741bd4243cbe`, sha `8843340bf445eb32f2cf1c005666c8eaf4f36a8173c5da3f2da1c1dcfc04e860`), contract v5 `20d90f7484fe5df7cd62755a5810c8de78e5e92f` (blob `84a59c4d966b349be705a8a29fad07f81282ebdc`, sha `191b2b2c399749a29796671ff21d3e51a349a83194fac333cc5ec1e1cac59f65`), schedule `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0` (blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`), family `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`.

## A. Audit Basis

Audit `NM-R4-V5-TRAINING-RUNNER-V5-AUDIT-036` — `VALIDATED WITH NON-BLOCKING FINDINGS` — authorization freeze `AUTHORIZED`.

## B. Canonical Recipe

`20d90f7484fe5df7cd62755a5810c8de78e5e92f` contains runner `7b46e0f6...`, contract v5 `84a59c4d...`, schedule `558d08bf...` — verified via `git rev-parse`.

## C. Authorizations

All at `reports/research/authorizations/structured_vol_v5_primary_training/`:

| member | replicate | config hash | prefix | SHA-256 | Git blob |
|--------|-----------|-------------|--------|---------|----------|
| v5-seed-02 | 9281 | 62c7406cb3a2c64237d39559370d70a27f8111f7dd1dc7ee581da9bd475cf00b | 62c7406cb3a2c642 | 27e5a51df2f9... | 3759c2528175... |
| v5-seed-03 | 10281 | e333325c804d95d2f34ad14138e312cde0a00df2ebf1056741abbdc52a8b0955 | e333325c804d95d2 | 61224c0f59b4... | 9e5de9d03042... |
| v5-seed-04 | 11281 | 77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b | 77e7de9efabb7ce3 | f605a28e34e8... | 275842f4a630... |
| v5-seed-05 | 12281 | 1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897 | 1e8aa171993a1aba | 669f34d4f61a... | dcfb2c188c51... |

Recomputed via `V5ExperimentConfig.config_hash()` — exact. 20 fields each, `training_authorized=true`, others `false`, `reserve=false`, `max=1`.

## D. Process Closure (Task 035)

- Contract v5 amended 3× (`c3756a2`→`6b61b5a`→`790824d`→`20d90f7`) despite NO AMEND; no scientific change, runner unchanged.
- Aborted rebase at `20d90f7` had no final effect.
- Placeholder `8f1c70425cc66fce48b2672938ad1b7dccc262d5` (`ac4afc74...`) remains in ancestry, structurally rejected.
- Canonical recipe is ONLY `20d90f7`; all ancestors/placeholders rejected by runner.
- Audit: no execution integrity impact; governance impact recorded; no history rewrite now.

## E. Gate-v2 Semantics

Six criteria: (1) `best < initial` selection total, (2) variance ratio [0.50,2.00], (3) dispersion [0.50,2.00], (4) uniqueness ≥0.99, (5) ACF1 ≤0.25, (6) drift/diffusion ≤0.50. `initial/best_selection_total` preserves (1); `criterion_results`/diagnostics preserve (2–6); `gate_passed` aggregate; Wasserstein REPORT-ONLY, not Gate.

## F. Authorization Semantics

JSON `training_authorized=true` means prospectively authorized record. Governed execution remains `NOT_AUTHORIZED` until independent audit + explicit execution task. No execution in 037.

## Next

Independent audit of four authorizations + this amendment.
