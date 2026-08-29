# Amendment 132 — Unscheduled Lineage Divergence Forensic Record and Recovery

Date: 2026-08-29
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-SUCCESSOR-UNSCHEDULED-LINEAGE-RECOVERY-294
Risk: R4
Type: BOUNDED_GIT_LINEAGE_RECOVERY_ONLY
Branch: main
Starting HEAD (forensic): a222903900e7d7ae8d3439ba5be0470570fc519a
Recovery anchor: 9a118f7b2356c7c2994ff11d40cc7ab0f3fa50ce
Authoritative executable source: 990c4aaafb86b4fb6d83e060c5402086ac58f774 / 9184b22b86cf191d93645086efaac45a5ce15af4b56d02174ea49d91cb7b1296
Forensic ref: forensic/unscheduled-lineage-a222903 → a222903900e7d7ae8d3439ba5be0470570fc519a
Incident commits (6): 2b9742a5310edd9d03aad783af52e641e7c908fc, 2000cf7870e7b37f43a61ce4f3a2a0e0a79f9012, bf4b071fd2f3ec2b339fffd19db97bf1d7ba5222, 7c4048b494c7fe671fd66bce37c57c38e48ed6df, 57b4720faf6a58e6c6232ce860cef2f519505bae, a222903900e7d7ae8d3439ba5be0470570fc519a
Production source drift during incident: 0 (git diff 9a118f7..a222903 -- src/ 0 paths)
Unauthorized prerequisite287: FORENSIC_ONLY_INVALID_NOT_GOVERNED (reports/protocol/hedging_recovery_successor_final_execution_authorization_prerequisites_287.json — present on forensic ref, absent on governed main)
Immutable-freeze violation: YES (post-freeze rewrite of prerequisite 287 without normative governance)
Successor authorization: NONE
Recovery_v3: ABSENT
Scientific execution during incident: 0
Consumed: 0
Remaining: 45
H3: NOT_YET_ADJUDICATED
Final: SEALED / access 0
H2: H2_NOT_SUPPORTED

## 1. Forensic Audit Identity (Task293)

Task293 classification: UNSCHEDULED_LINEAGE_DIVERGENCE_CONFIRMED
Current HEAD at forensic audit: FORENSIC_ONLY_NOT_GOVERNED (a222903)
Scientific contamination: NONE
Successor authorization: NONE
Recovery_v3: ABSENT
Consumed: 0 / Remaining: 45
Incident chain reconstructed and verified linear: 9a118f7 → 2b9742a → 2000cf7 → bf4b071 → 7c4048b → 57b4720 → a222903 (6 incident commits, linear ancestry, no forks).
Cumulative source drift `git diff 9a118f7..a222903 -- src/` = 0 paths — incident was test/protocol-only, no executable-source mutation.
No recovery_v3 created, no authorization created, no execution claims, no scientific execution during incident.

## 2. Forensic Preservation

Before any mutation, exactly one durable local forensic ref was created:

`forensic/unscheduled-lineage-a222903` → `a222903900e7d7ae8d3439ba5be0470570fc519a`

Verified: `git rev-parse forensic/unscheduled-lineage-a222903` equals forensic HEAD.
All six incident commits remain ancestors/reachable from that ref (`git branch --contains`).
Ref is local-only, not pushed, and will not be moved or deleted by this recovery.
No `git clean` was run; untracked governance/audit reports preserved.

## 3. Main Restoration

After forensic preservation, `main` was restored exactly to the last safe governed anchor:

`9a118f7b2356c7c2994ff11d40cc7ab0f3fa50ce` via `git reset --hard`

Verified:
- `HEAD == 9a118f7b2356c7c2994ff11d40cc7ab0f3fa50ce`
- `reports/protocol/hedging_recovery_successor_final_execution_authorization_prerequisites_287.json` is ABSENT from governed main (present only on forensic ref)
- All six incident commits remain reachable from forensic ref, not from main
- Branch is `main`
- Forensic ref unmodified

## 4. Recovered Source / Protocol State

At recovered `9a118f7` production source remains:

- Commit: `990c4aaafb86b4fb6d83e060c5402086ac58f774`
- Manifest: `9184b22b86cf191d93645086efaac45a5ce15af4b56d02174ea49d91cb7b1296`
- runner: `7d269f119d031fd4bc42f2543890d12b72d9dfba`
- trainer: `341f87783417b6f2243604dc392508aa05628f29`
- CLI: `25b0b1fd38bbf846c94393a67ba9f653544ae49b`
- generation: `1b8710fc77362eb59a7167b3b4575d8b93f63d12`

No source/test/config/data mutation in the recovery commit beyond this amendment.
Recovered protocol state verified:
- prerequisite286 present and unchanged (`hedging_recovery_successor_final_execution_authorization_prerequisites_286.json` at `5b8e6d03... / 08d148fb... / a743c1d...`)
- unauthorized prerequisite287 ABSENT
- Amendment130 unchanged, Amendment131 unchanged, Task276 unchanged, prerequisite264 unchanged, successor protocol unchanged, contract unchanged, SAP unchanged, Authorization248/251 unchanged
- Scientific state zero (model init 0, optimizer 0, execution 0, generation 0)

## 5. Incident-Record Amendment (This Amendment)

This amendment is append-only, does not modify any previous amendment, and grants **NO execution authority**.

It prospectively records:
- Build-implementation-manifest HEAD-embedding issue: IDENTIFIED_PENDING_SEPARATE_ADJUDICATION (manifest binds `implementation_commit` to current HEAD, causing rewrite loop when prerequisite287 was repeatedly amended to chase HEAD; identified for separate adjudication, not repaired here)
- Task292 test-governance repair: NOT_RESUMED_BY_THIS_TASK
- Unauthorized prerequisite287: FORENSIC_ONLY_INVALID_NOT_GOVERNED, immutable-freeze violation YES
- All firewalls remain: recovery_v2 10/4/14, recovery_v3 ABSENT, successor authorization NONE, claims 0, consumed 0, remaining 45, model init 0, optimizer 0, execution 0, generation 0, held-out 0, H3 NOT_YET_ADJUDICATED, H2 H2_NOT_SUPPORTED, final SEALED/access 0, network 0, push 0

## 6. Authority

- Successor authorization: NONE — this amendment creates no authorization
- Recovery_v3: ABSENT — no creation
- Execution: NONE — no scientific execution, no model/optimizer steps
- Network: NONE — no push

## 7. Next Step

Task295 (Claude Code, R4, STRICT_READ_ONLY_GIT_LINEAGE_RECOVERY_AUDIT) must independently verify forensic ref preserves a222903 and all six commits, main excludes all six, anchor was exactly 9a118f7, only this amendment follows that anchor, prerequisite287 absent from main and present on forensic ref, production source remains 990c4aa, zero scientific execution/authorization/recovery_v3. No test repair in Task295.
