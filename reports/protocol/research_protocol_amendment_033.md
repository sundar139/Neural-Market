# Research Protocol Amendment 033

## V5 Primary Seed-04 Execution Authorization and Durable Launch Record

**Date:** 2026-08-20
**Task:** NM-R4-V5-PRIMARY-EXECUTION-SEED-04-048
**Independent closure audit:** NM-R4-V5-SEED-03-ATTEMPT-CLOSURE-AUDIT-047
**Audit verdict:** VALIDATED WITH NON-BLOCKING FINDINGS
**Seed-03 final governed status:** ATTEMPTED_FAILED_GOVERNANCE
**Protocol violation:** DOUBLE_SCIENTIFIC_INVOCATION
**Audit recommendation:** SEED-04 EXECUTION AUTHORIZATION RECOMMENDATION: AUTHORIZED

---

## Authorization basis

Audit 047 validated Amendment 032 and the seed-03 closure (forensic record
`80775a7f...` / closure `fda22484...` / Amendment 032 `42e79a50...`).
Seed-03 is `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` and is
**not admissible** as a valid single-invocation primary member. The surviving
seed-03 six-criterion PASS is preserved as internal evidence but does not cure
the protocol violation. The failure is retained in the primary record; no
reserve or automatic replacement is authorized.

This amendment authorizes **exactly one** additional primary scientific
execution:

- **Member:** `v5-seed-04` — and no other member, reserve, validation, external
  validation, final test, or hedging execution.

## Exact seed-04 authorization and configuration identity

- Authorization path: `reports/research/authorizations/structured_vol_v5_primary_training/v5-seed-04.json`
- Authorization SHA-256: `f605a28e34e8862f373efd3025abf04cf57221b78d3ab37eec1de244bba06e85`
- Authorization Git blob: `275842f4a630222a2de43be7f11282c06090c8f9`
- Member: `v5-seed-04`
- `replicate_seed`: `11281`
- `model_init_seed`: `11281`
- `data_seed`: `11282`
- `eval_seed`: `8283`
- Full config hash: `77e7de9efabb7ce35107e7c9f80f9fb9e28fff6f1a31978c35f601cbf154312b`
- Run prefix: `77e7de9efabb7ce3`
- Family methodology: `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`
- Eval policy: `COMMON_FIXED_POST_TRAINING`; `eval_seed 8283` is common-fixed
  byte-identical across family.

Recomputed via `reports/research/evidence/structured_vol_v5_replicate_training_runner.py:derive_effective_config("v5-seed-04")`
against `configs/research/structured_vol_neural_sde_v5.yaml` and
`reports/research/structured_vol_v5_seed_schedule_v1.json` — hash
`77e7de9e...` matches authorization `full_config_hash` and
`EXPECTED_CONFIG_HASHES["v5-seed-04"]`.

## Runner, contract, schedule, recipe, and adjudicator identities

- Runner path: `reports/research/evidence/structured_vol_v5_replicate_training_runner.py`
- Runner Git blob: `7b46e0f6c805687977cd685ebb97741bd4243cbe`
- Execution-contract-v5 path: `reports/research/structured_vol_v5_training_execution_contract_v5.json`
- Execution-contract-v5 Git blob: `84a59c4d966b349be705a8a29fad07f81282ebdc`
- Schedule path: `reports/research/structured_vol_v5_seed_schedule_v1.json`
- Schedule Git blob: `558d08bfee98dbd0c170d65e6a9b1737700c9e98`
- Schedule SHA-256: `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`
- Canonical execution recipe: `20d90f7484fe5df7cd62755a5810c8de78e5e92f`
  (ancestor verified; contains frozen runner/contract/schedule blobs above)
- Audited adjudicator path: `reports/research/evidence/structured_vol_v5_primary_adjudicator.py`
- Audited adjudicator SHA-256: `82c867151a257381dd35f4f32648e054a6266ad8f753096b7d8da420eb28c2ea`
- Audited adjudicator Git blob: `39a45348056eef339958ae8298ff5d0886476cd9`

## Six-criterion semantics (Amendment 029, unchanged)

Furnished verbatim; adjudicator `39a45348...` implements this rule.

1. `best_selection_total < initial_selection_total`
2. `0.50 <= variance_ratio <= 2.00`
3. `0.50 <= terminal_dispersion_ratio <= 2.00`
4. `path_uniqueness_fraction >= 0.99`
5. `return_acf1_abs_diff <= 0.25`
6. `drift_diffusion_rms_ratio <= 0.50`

`governed_six_criterion_pass = criterion_1_pass AND criteria_2_to_6_pass`.
`Wasserstein` is `REPORT_ONLY`. Governed statuses remain
`NOT_ATTEMPTED_REFUSED`, `ATTEMPTED_FAILED_EXECUTION`, `ATTEMPTED_FAILED_GATE_2_TO_6`,
`ATTEMPTED_FAILED_GATE_CRITERION_1`, `PRIMARY_VALID_COMPLETED`.

## Operational safeguards (Amendment 032, frozen, non-scientific)

For every remaining primary/reserve `--execute` task (including this one):

1. Exactly one CLI command containing `--execute` may be launched.
2. If expected runtime can exceed foreground timeout, that one process is launched
   background-capable from the outset.
3. No foreground-then-background relaunch for the same member.
4. Before launch, durable evidence records task ID, member ID, exact command,
   authorization path, intended mode, UTC pre-launch timestamp.
5. Immediately after launch, record tool/session ID, PID, start UTC where available.
6. After `execution_started` publication, only monitor/poll the same process.
7. Never delete `execution_started` / report namespace / model namespace to recover.
8. Killed/timed-out process after irreversible start = `ATTEMPTED` failure absent
   separately governed recovery protocol.
9. Polling does not count as another `--execute`.
10. Never test the overwrite guard with another `--execute` after irreversible start.

These controls change provenance only; seeds, model, training parameters, `Gate-v2`,
schedule, methodology, and artifact identities are unchanged.

## Intended execution for NM-R4-V5-PRIMARY-EXECUTION-SEED-04-048

- Intended exact runner command:
  `C:\Users\rohit\Documents\Personal Projects\Neural Market\.venv\Scripts\python.exe "C:\Users\rohit\Documents\Personal Projects\Neural Market\reports\research\evidence\structured_vol_v5_replicate_training_runner.py" --member-id v5-seed-04 --authorization "C:\Users\rohit\Documents\Personal Projects\Neural Market\reports\research\authorizations\structured_vol_v5_primary_training\v5-seed-04.json" --execute`
- Execution mode: `BACKGROUND_FROM_OUTSET`
- `notify_on_complete`: `true` where supported
- Maximum CLI `--execute` commands: `1`
- Maximum irreversible starts: `1`
- Maximum scientific invocations: `1`
- No retry; no deletion/recovery; polling only after `execution_started`.
- `seed-05`: `NOT_AUTHORIZED`
- Reserves: `NOT_AUTHORIZED`
- Validation / external validation / final test / hedging: `NOT_AUTHORIZED`

No other member may be executed under this amendment. The next task after `048`
must be an independent Claude read-only audit of seed-04.

---

*End of Amendment 033.*
