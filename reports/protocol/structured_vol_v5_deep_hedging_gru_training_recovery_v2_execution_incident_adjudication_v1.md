# V5 GRU Recovery V2 Execution Incident Adjudication v1

Date: 2026-08-26
Task: NM-R4-V5-DEEP-HEDGING-GRU-TRAINING-RECOVERY-V2-EXECUTION-INCIDENT-PROTOCOL-ADJUDICATION-255
Risk: R4
Type: PROTOCOL_ADJUDICATION_ONLY
Branch: main
Starting HEAD: 257875c164dfc2ad7bf0e5dd047926e8ab84acec
Authorized implementation: 0b3841786ca77bbadb8c564ca33c75ff93f27bf1
Authorized manifest: 6c13b0ee960e2688aa71403edf9d9bbaca13c1ab451aebc266c1e81d35ab9cac
Authorization251: reports/protocol/hedging_recovery_v2_execution_authorization_251.json (638805b7c2837b764d4b3f479442236079557b25 / e09b8a4268fb8a3a06f4036c84dfa4d3fa5b7b29b989c0e16e0e9b367fbbc1f3 / de8117fb5bdbf26d48ee56a63ef68c275996637b)
Prerequisite: reports/protocol/hedging_recovery_v2_authorization_prerequisites_246.json (d4813d60002128c898fe88e40fd846dde80b5c3d / c416ba8141cf91f732dfe245552b6ce9035cfb079d5ab71d324db89bc7e0f8e0 / 88b51be4822c23c6c608fc75cd3cb4299d96afc1f2a18b7d4e53b929df296224 / a9d74c8a9fdc325d7e0f99b8a382c4bf8b3428d3)
Recovery root: data/processed/research/hedging_policies_recovery_v2

## 1. Forensic Binding Verification

- Task253: GOVERNANCE_INVALID_EXECUTION_RUNTIME_SOURCE_DRIFT (forensic accepted, Claude Task254 validated)
- Task254: EXECUTION_FORENSIC_AUDIT_VALIDATED
- Authorized implementation: 0b3841786ca77bbadb8c564ca33c75ff93f27bf1 / 6c13b0ee960e2688aa71403edf9d9bbaca13c1ab451aebc266c1e81d35ab9cac (15-path, runner 5fac8765d3a4972d3d212d3261deab1caace4628, trainer f1024919901ba95273aebe05f6b881cbfded8a09, CLI 86b9468f, generation 1b8710fc)
- Runtime-source identity: authorized source fails closed before execution_started (build_implementation_manifest with invalid keyword authorized_commit); Task253 runtime allowed provenance construction and scientific training via in-memory patch for authorized_commit alias
- Patch mechanism: in-memory monkey-patch of runner.build_implementation_manifest to accept authorized_commit, not durably reconstructible from committed source (transient, reverted, tracked tree clean)
- Patch active: ordinal1 YES (execution_started 8412b1d5..., patched), ordinal2 YES (execution_started 032a03a..., patched)
- Durable scan at HEAD 257875c: ceiling 45, consumed 2 (unique execution_started), remaining 43, valid terminal policies 0, governance-invalid terminal 1, governance-invalid started-nonterminal 1, not started 43, retry/rerun/replacement 0, no ordinal3+ execution_started
- Verified via pathlib scan of data/processed/research/hedging_policies_recovery_v2: 1 terminal_manifest.json (ordinal1), 1 execution_started.json without terminal (ordinal2), 43 tuples with no execution_started

## 2. Task253 Campaign Classification (Permanent)

- TASK253_CAMPAIGN: IRRECOVERABLY_GOVERNANCE_INVALID_SCIENCE_CONTAMINATED_EXECUTION
- All Task253 execution attempts: FORENSIC_ONLY_H3_INELIGIBLE_INFORMATION_EXPOSED
- Ordinal1 (seed-01/cost0/hedger31001): GOVERNANCE_INVALID_RUNTIME_MUTATION_TERMINAL — INELIGIBLE_FOR_POLICY_COMPLETENESS, INELIGIBLE_FOR_PREREQUISITE_9, INELIGIBLE_FOR_H3, MODEL_AND_SELECTION_INFORMATION_EXPOSED (checkpoint.pt preserved, checkpoint_final.pt preserved, model parameters preserved)
- Ordinal2 (seed-01/cost0/hedger31002): GOVERNANCE_INVALID_RUNTIME_MUTATION_NONTERMINAL — INELIGIBLE_FOR_POLICY_COMPLETENESS, INELIGIBLE_FOR_PREREQUISITE_9, INELIGIBLE_FOR_H3, DURABLY_CONSUMED_NONTERMINAL, NO_RETRY_AUTHORITY (execution_started 032a03a..., no checkpoint, no report, no terminal)
- Authorization251: CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY — must never be rebound to repaired source or reused for continuation
- Recovery root: data/processed/research/hedging_policies_recovery_v2 — FORENSIC_READ_ONLY_NEVER_REUSE — no future scientific execution may write into recovery_v2; any successor must use a new distinct namespace
- Task253 artifacts: FORENSIC_ONLY, never to be counted toward policy completeness or prerequisite #9

## 3. Scientific Information Exposure Record

Explicitly differs from Task236:

- Task236: SCIENTIFIC_RESULT_OBSERVED = 0 (no checkpoint/report/terminal exposed)
- Task253: SCIENTIFIC_RESULT_OBSERVED = YES

Frozen for Task253:

- Ordinal1 best_epoch = 11
- Ordinal1 best_validation_cvar = 2.3413521425265205
- Ordinal1 early stopping epoch = 31 (no improve 20 >= patience 20, max 200, min 20)
- Full 32-epoch train/validation-selection trajectory exposed (epochs 0-31, train_cvar 4.049→2.24, val_cvar 2.992→2.370, see training_curve.json 01aa9297 and training_stdout.log)
- Best checkpoint: data/processed/research/hedging_policies_recovery_v2/5bdbaabd2fb257a7_seed-01/c_0/h_31001/checkpoint.pt (sha ab65d67a77a6bc891d5f20dbd98aba051d35dd5499444422e41209f28b6535ae, blob 7a8fce3d79fc234084bd53ee53d8180d62219bba) PRESERVED
- Final checkpoint: checkpoint_final.pt (sha f1d7892e2513fb2ff74cfef75a75a5725b64574ea8717a1e50d09b0cddf3be07) PRESERVED
- Trained model parameters: preserved in checkpoint.pt (GRUHedger 7/64/2/dropout0)
- Selection information: lowest finite full-selection CVaR at epoch 11, earliest tie, preserved in training_report.json (5b81974e)
- Ordinal2 scientific metrics: UNKNOWN_BEYOND_PROCESS_STARTED (no checkpoint/report/terminal durably established; only execution_started with provenance)
- Information blindness: THE OPERATOR / PROJECT IS NO LONGER INFORMATION-BLIND TO THE ORIGINAL SEED-01 / COST-0 / HEDGER-SEED-31001 TUPLE. This is not minimized because H3 itself was not evaluated; selection and model information exposure alone contaminates.

## 4. Continuation of Remaining 43 Tuples

Facts: ordinal1 invalid, ordinal2 invalid/nonterminal, retry 0, rerun 0, replacement 0, 43 tuples remain unstarted.

Question: Can executing only ordinals 3-45 satisfy the frozen 45-policy contract, prerequisite #9, and original campaign completeness?

Evaluation:

- Original contract requires 45 valid recovery policies, each tuple exactly once, no retry/rerun/replacement, all policies must be governance-valid.
- Ordinal1 and ordinal2 are durably consumed but governance-invalid; they cannot be counted.
- Remaining 43 unstarted tuples, even if all succeed governance-valid, would yield at most 43 valid policies, not 45.
- No authority exists to retry ordinal1/2 (explicit 0 guardrails, write-once consumed).
- No contract clause allows 43/45 to satisfy 45-policy completeness.

Result:

- CONTINUATION_OF_REMAINING_43_CANNOT_SATISFY_POLICY_COMPLETENESS: true
- ORIGINAL_AUTHORIZATION251_CAMPAIGN_NOT_CONTINUABLE_FOR_SCIENCE: frozen

Do not authorize continuation of remaining 43 merely because they are unstarted.

## 5. Same-45 Tuple Restart Admissibility

Question: Can the same exact 45-tuple deterministic universe be restarted fresh and be called information-blind preregistered?

Evaluation:

- Same tuple seed-01/cost0/hedger31001 now has known selection CVaR (2.341...), best epoch (11), trajectory, and model parameters.
- Any fresh run of the same 45-tuple universe would include that exact tuple with known outcome, allowing outcome-dependent decisions (e.g., hyperparameter tuning, early stopping adaptation, favorable seed selection) even if not intended.
- Task236 precedent does not apply mechanically: Task236 had zero scientific result exposure, so restart was allowable as prospective new campaign. Task253 has non-zero exposure.
- No protocol argument defensibly restores information blindness for that tuple while reusing same hedger seed.

Result:

- SAME_45_TUPLE_RESTART_NOT_SCIENTIFICALLY_CLEAN: true
- Reason: deterministic outcome and selection information for seed-01/0/31001 is durably known and preserved; rerunning the identical 45-tuple universe cannot be honestly described as outcome-independent preregistered.

No execution decision in this section; this is scientific classification.

## 6. Successor H3 Recovery Campaign Admissibility

Question: Can H3 still be tested without using Task253 information to choose a favorable design via a completely new disjoint successor campaign?

Required properties for any successor to be defensible:

- New namespace distinct from recovery_v2 (never reuse data/processed/research/hedging_policies_recovery_v2)
- No reuse of Task253 checkpoint/model parameters, no warm start
- No reuse of exposed hedger-seed tuple (seed-01/0/31001) nor any tuple that would allow indirect exploitation of known CVaR
- Completely disjoint prospective hedger-seed universe (e.g., new seeds derived deterministically from immutable pre-outcome identities, not hand-picked post-outcome)
- Same frozen five synthetic datasets unless scientific reason requires otherwise (datasets remain valid)
- Same 3 costs (0.0, 0.001, 0.005)
- Same GRU architecture/features/training contract (7/64/2/dropout0, 7 features, prev_delta, P&L, CVaR alpha 0.95, AdamW lr 1e-3, batch 64, max200 min20 patience20 clip1, selection lowest finite CVaR earliest tie)
- Same evaluation/H3 success criteria
- No hyperparameter adaptation based on Task253 outcome (learning rate, batch, architecture, patience must remain frozen)
- Seeds selected by deterministic outcome-independent derivation rule from immutable pre-outcome identities, not hand-picked after seeing CVaR 2.341...

Evaluation:

- None of the successor constraints require using Task253 outcome; they can be satisfied by defining a new seed universe via pre-committed derivation (e.g., hash of contract + new namespace).
- Avoiding the exposed tuple and using disjoint seeds restores outcome independence for H3.
- Not inventing or executing seeds in this task is sufficient to make the admissibility decision; detailed seed derivation can be deferred to protocol design with independent audit.

Result:

- H3_SUCCESSOR_RECOVERY_CAMPAIGN_SCIENTIFICALLY_PERMISSIBLE_PENDING_PROTOCOL_DESIGN_AND_INDEPENDENT_AUDIT: true
- Rationale: H3 remains testable via a fully disjoint successor campaign that does not reuse the contaminated tuple or its model, does not adapt hyperparameters to the observed CVaR, and is defined by outcome-independent rules. Permissibility is conditional on protocol design and independent audit; it does not imply that the original 45-tuple campaign is continuable.

Do not silently relax H3 or policy-completeness criteria.

## 7. Source Defect (Separate from Scientific Incident)

Root defect:

- Location: src/neuralmarket/research/deep_hedging/trainer.py recovery path, function train_one_policy_recovery, line ~1160
- Invalid call: build_implementation_manifest(authorized_commit=_payload_impl_commit) — keyword authorized_commit does not exist; correct is implementation_commit
- Unmodified authorized source behavior: FAILS CLOSED BEFORE RECOVERY EXECUTION (RuntimeError: build_implementation_manifest() got an unexpected keyword argument 'authorized_commit')
- Task253 runtime behavior: allowed provenance construction and scientific training via in-memory patch (monkey-patch of runner.build_implementation_manifest to accept authorized_commit alias), not durably reconstructible
- Required code repair for any future recovery execution: YES (change to implementation_commit)
- Repaired in Task255: NO (protocol adjudication only, no source repair)
- Relationship to scientific authority: separate gates — source repair does not confer scientific authority; scientific successor admissibility does not imply source correctness

Frozen:

- IMPLEMENTATION_REPAIR_REQUIRED_BEFORE_ANY_FUTURE_RECOVERY_EXECUTION: true
- Authorization251 must never be rebound to repaired source

## 8. Current Authority and Future State

- Authorization251: CLOSED_USED_BY_GOVERNANCE_INVALID_EXECUTION_NO_FURTHER_AUTHORITY
- Recovery_v2 root: FORENSIC_READ_ONLY_NEVER_REUSE
- Recovery execution: SUSPENDED (no further writes into recovery_v2)
- Policy completeness: NOT_SATISFIED (0 valid policies, 2 consumed, 43 unstarted)
- Prerequisite #9: NOT_SATISFIED (no valid successor yet)
- H3: NOT_YET_ADJUDICATED (original campaign not continuable, successor permissible pending design)
- H2: H2_NOT_SUPPORTED
- Final: SEALED, access 0
- Synthetic generation: CLOSED_NO_FURTHER_EXECUTION
- Network: 0, held-out: 0, final-test: 0, push: 0

Adjudicated without source mutation, authorization creation/edit, artifact mutation, recovery execution, retry/rerun/replacement/deletion/rm-rf, generation, held-out, H3, or final-test activity.
