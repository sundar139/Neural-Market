# Amendment 039 — V5 Seed-05 CUDA Execution Methodology Decision

**Date:** 2026-08-21
**Task:** NM-R4-V5-SEED-05-EXECUTION-DECISION-059
**Risk:** R4
**Branch:** `main`
**Starting HEAD:** `97968236dd9ba69c8b62d03ee3892532db5eeed4`
**Independent CUDA closure audit:** `NM-R4-PROJECT-WIDE-CUDA-CLOSURE-AUDIT-058`
**Audit verdict:** VALIDATED WITH NON-BLOCKING FINDINGS
**Technical CUDA status:** VALIDATED
**Status:** DECISION — append-only methodology record. No scientific training, no `--execute`, no authorization artifact, no validation, no external validation, no final-test access, and no hedging.

## 1. Purpose and decision

This amendment decides whether prospective `v5-seed-05` may remain the scheduled fifth primary member of the existing v5 replicate family when the project policy requires all future real scientific PyTorch computation to use CUDA.

**METHODOLOGICAL DECISION: `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT`**

Seed-05 remains the scheduled fifth primary member of the existing family. The scientific family methodology identity remains:

`730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719`

This decision freezes prospective identity and interpretation only. It does not authorize seed-05, create an authorization artifact, or authorize any scientific execution.

## 2. Authoritative family contract

The original family contract is reconstructed from the following committed sources:

- `reports/protocol/research_protocol_v1.md`, line 99: “All neural comparisons use at least five independent seeds.” Line 100 requires failed seeds to be reported and not silently discarded. Line 105 requires market-period and training-seed uncertainty to be reported separately.
- Amendment 020 §2.4 and §4.1: the five-seed requirement is normative, applies to H1/H2 and the primary hedging claim, and is required before a full confirmatory final-test claim.
- Amendment 021 §4: a fully independent stochastic training replicate requires both `{model_init_seed, data_seed}`. Amendment 021 §8 fixes `eval_seed = 8283` as common post-training evaluation randomness. Amendment 021 §9 freezes the scientific methodology invariants and says only replicate RNG identity may vary. Amendment 021 §10 preserves failed primary members and forbids silent replacement. Amendment 021 §11 requires recording Python/PyTorch versions, device, and determinism state for every member.
- Amendment 022 §§5–7: the five-member primary schedule, derived training seeds, common evaluation policy, and fixed Gate-v2 seeds are frozen before training.
- Amendment 022 §§10–15: failed primaries remain in the primary roster; reserves do not retroactively replace them; `PRIMARY_UNDERFILLED` leaves H2 not proven and blocks H3/final-test authorization.
- Amendment 032 §§114–169: seed-03 is retained as scheduled-primary history but is `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION` and inadmissible as a valid primary; its numerical result does not cure the protocol violation.
- Amendment 034 §Governance: future CPU/GPU mixing within a frozen replicate family requires a separate governed methodological decision. This amendment is that decision.
- Amendments 035–038: runtime identity is separate from scientific config identity; the prospective policy is CUDA-only for real scientific PyTorch computation; historical CPU lineage remains immutable.

### 2.1 Hardware rule

The original family contract does **not** contain a rule requiring all family members to run on the same CPU/GPU device, the same hardware, or bit-identical kernels. It requires device and determinism to be recorded as execution provenance, but it does not define hardware equivalence or prohibit differing execution hardware within one family.

The literal `device (cpu)` wording in Amendment 021 §11 and the companion JSON is a contemporaneous evidence-field value from the historical CPU execution lineage. It is not a committed sentence requiring every future member to execute on CPU or requiring all members to share hardware.

Therefore:

`HARDWARE_NOT_FROZEN_IN_ORIGINAL_FAMILY_CONTRACT`

No hardware rule is inferred from convention. The current CUDA-only project policy and the explicit runtime identity contract now govern prospective execution.

### 2.2 Runtime and determinism rule

Replicate independence is defined by the training RNG pair `{model_init_seed, data_seed}`. `eval_seed = 8283` is common and post-training; Gate-v2 seeds `7777/7778/8801` are common and are not training-replicate seeds. Python/PyTorch versions, device, and determinism state must be recorded for each member.

The contract does not claim CPU/CUDA bit identity. Runtime identity is execution provenance, not part of `V5ExperimentConfig.config_hash` or the family methodology identity.

### 2.3 Failed-member and five-seed rules

The scheduled primary family has five permanent slots. A failed or inadmissible primary remains recorded and is not silently discarded, relabelled, or replaced. Primary attempted, valid-completed, and failed counts must be reported separately. A reserve never erases a failed primary and does not count as a successful primary.

The original five-independent-seed requirement remains active. Seed-03 is not silently replaced. If seed-05 later succeeds, the admissible primary members will be exactly four: seed-01, seed-02, seed-04, and seed-05. The five-seed requirement will therefore remain unresolved, and a later separately governed extra/replacement/reserve methodological decision will still be required. This amendment does not make that reserve decision.

## 3. CPU/CUDA scientific assessment

### 3.1 What is unchanged

Seed-05 uses the already frozen scientific config and schedule. The architecture, loss, optimizer, windowing, data split, model-init/data/evaluation seed tuple, simulator, Gate-v2 criteria, and family methodology identity are unchanged. The prospective recipe is the validated CUDA recipe `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a`.

This is not `SCIENTIFIC_CONFIG_VARIATION`.

### 3.2 What changes

The historical admissible members seed-01, seed-02, and seed-04 were executed on the preserved CPU lineage. Prospective seed-05, if later separately authorized, will execute on the bound CUDA runtime. CPU and CUDA can produce numerically different results even with deterministic settings because kernels, floating-point reduction order, libraries, and hardware differ.

This is `EXECUTION_RUNTIME_VARIATION`. The runtime identity is recorded separately and CPU/CUDA numerical equivalence is not claimed.

### 3.3 Classification

The runtime variation is acceptable within the existing replicate family only with an explicit narrowed interpretation and sensitivity disclosure. It does not require a new CUDA family because:

1. The original contract did not freeze same-hardware execution or hardware equivalence.
2. The scientific config and family methodology identity remain unchanged.
3. The project policy prohibits choosing CPU for new scientific execution.
4. A separate runtime identity records the material execution difference without conflating it with the scientific config hash.
5. A new family would incorrectly treat a runtime provenance change as a scientific-methodology change when the committed family contract distinguishes scientific invariants from execution provenance.

Observed seed-to-seed variation across the resulting family cannot automatically be attributed only to random seed. Runtime heterogeneity is a possible contributor and must be disclosed.

## 4. Frozen prospective seed-05 identity

These are proposed frozen identities only. They authorize no execution and do not create an authorization artifact.

| Field | Frozen value |
|---|---|
| member | `v5-seed-05` |
| replicate_seed | `12281` |
| model_init_seed | `12281` |
| data_seed | `12282` |
| eval_seed | `8283` |
| config hash | `1e8aa171993a1aba52534ae031d05ba5e8dbdb15772678bf3ec72fc68dcde897` |
| config prefix | `1e8aa171993a1aba` |
| family methodology | `730475987368bf8f408e44e8e387682f178a0cdd7a358939016ba9b6df57a719` |
| prospective authorization schema | `structured-vol-v5-primary-training-authorization-v2` |
| requested_device | `cuda` |
| expected_resolved_device | `cuda` |
| expected_runtime_identity_sha256 | `17e3bb52d5893c4e09ecb759a925004f2e75a37d7d4faf4ece7de41f81870ada` |
| execution recipe | `6a6b9f894e36a09eb7f8e43be78e869a6f35d10a` |
| runner blob | `05b704b254387d8f5ffdf1d847dd4289303b565c` |
| trainer blob | `85aabc6798b22a60bd4d94d4ee86bfae81a8a172` |
| Gate-v2 blob | `05af8d0d864eddaae8c43e1cc3936d28e89abaf3` |
| auth-v2 schema blob | `c74958f2c5d99753b05bf64c9b6880ee9bd37d94` |
| runtime-identity blob | `817ba53e2474c6e8dd7ecf15d64e0766e75f73e9` |
| authorization artifact created | **NO** — no prospective v2 authorization was created; any historical v1 artifact remains unchanged and inspection-only |

## 5. Later claim boundary

If seed-05 is later authorized and completed, later family analysis must state all of the following:

- seed-01, seed-02, and seed-04 are historical CPU members;
- seed-05 is a prospective CUDA member;
- each member's runtime identity is recorded separately from scientific config identity;
- hardware equivalence is not claimed;
- CPU/CUDA numerical identity is not claimed;
- observed variation is not automatically attributable only to replicate seed;
- any H2, seed-stability, or family-level interpretation explicitly discloses runtime heterogeneity;
- if a conclusion depends materially on seed-05, an appropriate sensitivity analysis must be performed or prospectively defined before broad claims;
- no dropping of failed or inadmissible primaries and no silent reserve substitution is permitted.

This amendment does not change Gate-v2, retune because of CUDA, reopen external validation, or access the sealed final test.

## 6. Execution and authorization firewall

This amendment creates no authorization artifact and authorizes no scientific execution. In particular:

- seed-05 remains `NOT_AUTHORIZED`;
- no `--execute` command is permitted by this amendment;
- no scientific training or simulation is performed;
- no reserve is selected or executed;
- no validation or external-validation construction is performed;
- no final-test data is accessed;
- no hedging is performed;
- final-test status remains `NOT_AUTHORIZED`;
- external validation remains CLOSED at 2/2, with the third construction forbidden;
- the final chronological test remains sealed.

## 7. Protected family state

| Member | State | Admissible primary |
|---|---|---:|
| seed-01 | historical CPU, existing frozen primary | yes |
| seed-02 | historical CPU, `PRIMARY_VALID_COMPLETED` | yes |
| seed-03 | `ATTEMPTED_FAILED_GOVERNANCE` / `DOUBLE_SCIENTIFIC_INVOCATION`, retained | no |
| seed-04 | historical CPU, `PRIMARY_VALID_COMPLETED` | yes |
| seed-05 | scheduled fifth primary, prospective CUDA, not authorized | pending |

Current admissible historical primary count is **3**: seed-01, seed-02, and seed-04.

If seed-05 later succeeds, the admissible primary count becomes **4**, not 5. The five-seed requirement remains unresolved until a later separately governed decision addresses an additional member without silently replacing seed-03 or using a reserve by default.

The historical CPU lineage, frozen seed schedule, family methodology identity, existing authorization artifacts, external-validation closure, Gate-v2 specification, CUDA recipe, and scientific source bytes remain unchanged.

## 8. Required next action

The next governed task must be an independent read-only audit of this seed-05 CUDA methodology decision before any authorization artifact is created. No authorization or execution may be inferred from this amendment alone.

---

*Amendment 039 is append-only methodology reasoning. It freezes `CUDA_SAME_FAMILY_ACCEPTED_WITH_RUNTIME_CAVEAT`, preserves the historical CPU lineage, and does not authorize seed-05 or any other scientific operation.*
