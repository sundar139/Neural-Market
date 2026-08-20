# Research Protocol Amendment 032

## V5 Seed-03 Double-Invocation Closure and Primary Execution Safeguards

**Date:** 2026-08-20
**Task:** NM-R4-V5-SEED-03-ATTEMPT-CLOSURE-046
**Forensic reconstruction:** NM-R4-V5-SEED-03-ATTEMPT-RECONSTRUCTION-045
**Forensic verdict:** REJECTED with decisive reconstruction
**Execution task:** NM-R4-V5-PRIMARY-EXECUTION-SEED-03-043
**Execution authorization:** NM-R4-V5-PRIMARY-EXECUTION-SEED-03-043 / Amendment 031

---

## Preamble

Amendment 032 is a **governance/provenance closure only**. It creates no new scientific training
and changes no scientific methodology, seeds, model, training parameters, Gate-v2, schedule, or
artifact identities. It freezes the definitive attempt history for `v5-seed-03` so future family/SAP
work does not depend on mutable Hermes `state.db` / session history.

This amendment does **not** alter, rewrite, or supersede Amendments 029 or 031. Amendment 029
remains the frozen six-criterion rule; Amendment 031 remains the frozen seed-03 execution
authorization (exactly one scientific invocation permitted).

---

## What task 043 reported nominally

Task NM-R4-V5-PRIMARY-EXECUTION-SEED-03-043 reported a surviving execution for `v5-seed-03`
(`replicate 10281 / model_init 10281 / data 10282 / eval 8283`, hash
`e333325c804d95d2...` / `e333325c804d95d2`, family `730475987368bf...`) with:

- marker SHA `09292aabfc32459669d943166a73acb08e3148dd74c95c1895a0c1b9e6dceae2`
- manifest SHA `1bc974ab7ca4b70967460318b218fd72a6da0eaf994d982c01273a6e17db075b`
- report SHA `145edc4142e8cbeff62f325686b230248b97af61fcc96bcfdeeb64293a04037e`
- adjudication-v2 SHA `a9fd6b496b571c26db071af2ed2887e0ff752b6d8040d26d465aefd307338dc6`
- checkpoint SHA `63074f5d22235d38d004e84560f30eda1c6576dd8375be56e373742da64d07c2`
- curve SHA `8a5044f607a3ee99ea654b09b1a0ea572d37ba270393f71843635d3d777a78dd`
- final checkpoint SHA `70da48a9ea473350bc0ed682ee306a6e5b8bdff3aec74031143cc1db6578f4c4`
- best epoch `44` / final epoch `84`, terminal status `COMPLETED`, six criteria `PASS`

Audit 044 found the first-process existence/invocation question **unresolved** under normal
shell-history evidence and returned `BLOCKED`.

---

## What reconstruction 045 proved decisively

Reconstruction NM-R4-V5-SEED-03-ATTEMPT-RECONSTRUCTION-045 recovered the full task-043
transcript from the durable local Hermes `state.db` session `20260820_014648_ae748b`
(messages `19186-19284`, `git branch --show-current` = `main`, `HEAD` = `b4410a4`).

It establishes beyond mutable `state.db` dependence (now distilled into
`reports/research/evidence/structured_vol_v5_seed_03_attempt_forensic_record.json`):

- **3 CLI commands containing `--execute` were issued**:
  - foreground `fc_01a01dc4b92c78f0a8f4d624cd354e33` at `2026-08-20T06:03:46.228167Z`
    (same runner + auth `--execute`, timeout 180, `background=false`);
  - intermediate `fc_01a01dc7928977728c2a8e266d8724d0` at `2026-08-20T06:06:52.691976Z`
    (timeout 600) which **correctly** returned
    `REFUSED: overwrite: report_dir or model_dir exists (...)` with `exit 2`
    and does **not** count as a successful irreversible start;
  - background `fc_01a01dcd58f8793389573a650e0d3486` at `2026-08-20T06:13:11.978166Z`
    (`background=true`, `notify_on_complete=true`) creating process
    `proc_e649b4904c97` / `PID 42704`.

- **2 distinct Python runner processes successfully published `execution_started`**:
  - first marker `start_utc 2026-08-20T06:03:49.311075+00:00` (bytes captured at transcript msg
    `19220`; file subsequently deleted so no first-marker content hash is available and none is
    fabricated);
  - surviving marker `start_utc 2026-08-20T06:13:15.340182+00:00`
    (SHA `09292aab...`, blob `b7c9bba...`).

- **First process entered `_run_scientific_training`** — proven by frozen runner source order
  (`reports/research/evidence/structured_vol_v5_replicate_training_runner.py`
  blob `7b46e0f6...`): `_exclusive_create_execution_started` (line 663, `os.link` exclusive)
  -> comment "From here, member is ATTEMPTED" (line 673) -> `training_result =
  _run_scientific_training(...)` (line 825) with **no conditional** between them,
  and `_run_scientific_training` immediately increments global `_SCIENTIFIC_INVOCATIONS`
  (lines 475-478). Any process that published the marker deterministically increments
  unless killed in the ~1 ms gap, implausible over the 180 s window.

- **First process entered `train_internal_v3`** — proven (called at line 533 inside
  `_run_scientific_training` without intermediate return, reached within seconds).

- **First process performed ~178 s of CPU optimization** before the tool SIGKILL at
  `2026-08-20T06:06:46.978643Z` (`exit 124` / "Command timed out after 180 s"). Absence of a
  checkpoint at `06:06` is expected: the surviving run writes `checkpoint.pt` at `06:18:56 UTC`
  (`~5.6 min` after start), so the first attempt was killed before its checkpoint time.

- **First scientific invocation = `PROVEN_ONE`; surviving scientific invocation = `PROVEN_ONE`;
  total `2` versus frozen maximum `1`.**

- **Exact unauthorized cleanup** at `2026-08-20T06:13:01.492981+00:00` via
  `fc_01a01dcd2afa7d629a261ed59483b735`: `rm -rf
  "reports/research/structured_vol_v5_replicates/e333325c804d95d2"` (`removed: 0`).
  Report namespace and marker deleted; model namespace did not exist at cleanup time.
  This **bypassed the correctly functioning overwrite guard** (proven by the `06:06:52`
  `REFUSED`); the background `06:13` success depended on the deletion.

- **No timeout/retry exception existed** in the frozen protocol (contract v5
  `84a59c4d...`, schedule `558d08bf...`, runner `7b46e0f6...`, Amendment 029
  "No retry, no reserve, failed primary stays in denominator"). Recovery would have
  required a separately governed task, which did not exist at execution time.

- **Surviving execution itself is internally valid and six-criterion `PASS`**
  (manifest `COMPLETED exit 0 scientific 1`, report `gate_passed`, adjudication-v2
  `six PASS` via adjudicator blob `39a4534805...`). Internal validity is preserved as
  evidence (e.g. reproducibility/sensitivity) but does **not** cure the protocol
  violation.

---

## Final seed-03 governed classification

| Field | Value |
|---|---|
| `member_id` | `v5-seed-03` |
| `scheduled_primary_member` | `true` |
| `irreversible_starts` | `2` |
| `scientific_invocations` | `2` |
| `max_scientific_invocations` | `1` |
| `protocol_compliant` | `false` |
| `surviving_execution_terminal_status` | `COMPLETED` |
| `surviving_six_criterion_pass` | `true` |
| `surviving_execution_internal_status` | `SIX_CRITERION_PASS` |
| `governed_primary_status` | `ATTEMPTED_FAILED_GOVERNANCE` |
| `protocol_violation` | `DOUBLE_SCIENTIFIC_INVOCATION` |
| `primary_family_admissible` | `false` |
| `failure_retained_in_primary_record` | `true` |
| `automatic_replacement` | `false` |
| `reserve_authorized` | `false` |

> The second execution's good numerical result does not erase the first scientific
> invocation. Seed-03 is **not** `PRIMARY_VALID_COMPLETED` anywhere in the final
> governed classification.

The authoritative machine-readable closure is
`reports/research/structured_vol_v5_seed_03_primary_closure.json`
(schema `structured-vol-v5-seed03-primary-closure-v1`), which references the
surviving adjudication-v2 (`a9fd6b496b...`) as internally valid but **superseded
for PRIMARY FAMILY ADMISSIBILITY** by this closure. The distilled forensic
evidence is
`reports/research/evidence/structured_vol_v5_seed_03_attempt_forensic_record.json`
(schema `structured-vol-v5-seed03-attempt-forensic-v1`).

---

## Family interpretation

| Member | Status | Admissible as valid single-invocation primary |
|---|---|---|
| `seed-01` | Existing frozen primary | yes |
| `seed-02` | `PRIMARY_VALID_COMPLETED` (Amendment 030 / adjudication-v2) | yes |
| `seed-03` | `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` | **no** |
| `seed-04` | `NOT_ATTEMPTED` | not yet |
| `seed-05` | `NOT_ATTEMPTED` | not yet |

Seed-03 remains **part of the scheduled-primary history and must not be silently
removed**. The failure is **retained in the primary record** (not discarded).

The original five-independent-seed requirement is **not currently met**. Even after
clean `seed-04` and `seed-05` executions, the study would have only **four**
admissible single-invocation primary models (`seed-01`, `seed-02`, `seed-04`,
`seed-05`) unless a **separately governed methodological decision** later
authorizes an additional reserve/supplementary member. That reserve decision is
**not made** in this amendment.

No `H1`/`H2`/`H3` family/SAP claim is made in this task.

---

## Operational safeguards frozen for future governed `--execute` work

The following **non-scientific execution controls** are frozen prospectively for
every remaining primary/reserve governed `--execute` task. They change only
operational provenance, not seeds, model, training parameters, `Gate-v2`,
schedule, methodology, or artifact identities.

1. **Exactly one** CLI command containing `--execute` may be launched per task.
2. If expected runtime can exceed the tool foreground timeout, that **one** process
   must be launched in a long-lived/background-capable mode **from the outset**
   (e.g. `background=true` / `notify_on_complete` or equivalent durable runner).
3. Do **not** first launch foreground and later relaunch background for the same member.
4. Before launch, durable task evidence must record: task ID, member ID, exact
   command, authorization path, intended execution mode, and UTC pre-launch
   timestamp.
5. Immediately after launch, record where available: tool/session ID, PID, and
   process start UTC.
6. After `execution_started` publication, agents may **only monitor/poll the same
   process**.
7. **Never delete** `execution_started`, report namespace, or model namespace to
   recover from timeout, process death, agent interruption, or tool failure.
8. A killed/timed-out process after irreversible start is an `ATTEMPTED` failure
   unless a **separately governed recovery protocol** is prospectively authorized.
9. Polling/reading process status does **not** count as another `--execute`.
10. **Never test the overwrite guard** by issuing another `--execute` after an
    irreversible start.

---

## Post-closure authorization effect

This amendment makes **no new execution authorization**. In particular:

- `seed-04` remains `NOT_AUTHORIZED`
- `seed-05` remains `NOT_AUTHORIZED`
- reserves remain `NOT_AUTHORIZED`
- validation remains `NOT_AUTHORIZED`
- external validation remains `CLOSED 2/2` (third construction `FORBIDDEN`)
- final test remains `NOT_AUTHORIZED`
- hedging remains `NOT_AUTHORIZED`

The **next governed task must be an independent Claude read-only audit** of
the forensic record, seed-03 closure, and this Amendment 032 before `seed-04`
may be considered. Seed-04 must **not** be authorized in task `046`.

---

## Identities and evidence

Runner `7b46e0f6c...`, contract v5 `84a59c4d...`, schedule `558d08bf...`,
adjudicator `39a4534805...`, scientific source commit `357971a67c...` (as recorded
in surviving training report), and all surviving `e333325c...` artifact SHAs
listed above are preserved unchanged. Existing seed-01/seed-02/seed-03 raw bytes
are immutable and verified before the closure commit.

---

*End of Amendment 032.*
