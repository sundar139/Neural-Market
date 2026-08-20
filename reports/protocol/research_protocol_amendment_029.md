# Research Protocol Amendment 029

## V5 Primary Replicate Six-Criterion Adjudication and Seed-02 Execution Authorization

**Date:** 2026-08-19
**Task:** NM-R4-V5-PRIMARY-EXECUTION-SEED-02-039
**Recipe:** `20d90f7484fe5df7cd62755a5810c8de78e5e92f` (runner `7b46e0f6...`, contract v5 `84a59c4d...`, schedule `558d08bf...`)

## Six-Criterion Rule (Prospective, Seeds 02–05)

- `criterion_1_pass = best_selection_total < initial_selection_total`
- `criteria_2_to_6_pass = runner gate_passed` (diagnostic criteria 2–6)
- `governed_six_criterion_pass = criterion_1_pass AND criteria_2_to_6_pass`

Six frozen criteria:
1. `best_selection_total < initial_selection_total`
2. variance ratio [0.50, 2.00]
3. terminal dispersion [0.50, 2.00]
4. path uniqueness ≥0.99
5. ACF1 absolute error ≤0.25
6. drift/diffusion RMS ≤0.50

Wasserstein REPORT-ONLY, not Gate.

## Governed Statuses

- `NOT_ATTEMPTED_REFUSED` — pre-start refusal
- `ATTEMPTED_FAILED_EXECUTION` — exception after start (exit 1)
- `ATTEMPTED_FAILED_GATE_2_TO_6` — `GATE_V2_FAILED` (exit 3)
- `ATTEMPTED_FAILED_GATE_CRITERION_1` — `COMPLETED` but `criterion_1 == false`
- `PRIMARY_VALID_COMPLETED` — `COMPLETED` and `criterion_1 == true`

No retry, no reserve, failed primary stays in denominator.

## Member-01 Comparability

Member-01 satisfied criterion 1 (`0.5251655578613281 < 8.628283500671387`), so this restores comparable adjudication.

## Next

Seed-02 executes once under this rule.
