# V5 WGAN Comparator Implementation Freeze

## Amendment identity

- amendment: 061
- task: NM-R3-V5-WGAN-COMPARATOR-IMPLEMENTATION-109
- risk: R3
- starting branch: `main`
- starting HEAD: `cd657e624c7fda82f2d768e8d291db49e3f51972`
- implementation commit: `94e859fa8db4bf4785ecba536f040bfd6dbe94f8`
- safety branch: `safety/pre-wgan-comparator-implementation-cd657e6`
- prerequisite audit: NM-R4-V5-WGAN-H2-DENOMINATOR-CLARIFICATION-AUDIT-108
- prerequisite verdict: VALIDATED WITH NON-BLOCKING FINDINGS
- scope: implementation and non-scientific testing only

This amendment records the committed implementation identity and execution
boundary. It does not rewrite, supersede, or alter the frozen WGAN
preregistration or Amendment 060 semantics.

## Frozen methodology inputs

- preregistration path: `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json`
- preregistration SHA-256: `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037`
- preregistration Git blob: `72311888542ee83ff497b5f0adbbaf6429e8452a`
- Amendment 060 path: `reports/protocol/research_protocol_amendment_060.md`
- Amendment 060 SHA-256: `2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c`
- Amendment 060 Git blob: `a1ba052abe8b4a50887ec84b934e16a328e60596`
- contract drift: NONE
- methodology substitution: NONE

## Implementation paths and Git blobs

### Model

- `src/neuralmarket/models/wgan_cde.py`
- Git blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`
- generator: conditional Neural-CDE-style fixed explicit Euler generator; hidden dimension 64; context dimension 4; static latent dimension 32; temporal noise dimension 2; three-channel control; scalar daily raw-return output; no price-level output; no clipping
- critic: conditional Neural-CDE-style fixed explicit Euler path critic; hidden dimension 64; six-channel control; terminal scalar linear output; no sigmoid or probability semantics

### Comparator and training

- `src/neuralmarket/research/wgan_comparator.py`
- Git blob: `5f6591c272dea51bcf522ee1d3454e5291e89814`
- objective: WGAN-GP, lambda 10.0, uniform full-path interpolation, no weight clipping
- optimizer: Adam, learning rate 1e-4, betas (0.0, 0.9), eps 1e-8, weight decay 0, no gradient clipping, no scheduler
- update ratio: five critic updates per generator update
- batch size: 64
- maximum generator epochs: 400
- internal selection metric: `internal_selection_terminal_wasserstein_normalized`, lower is better
- patience: 40 generator epochs
- min_delta: 0.0
- checkpoint ties: lower metric, earliest epoch, lexicographically smallest identity
- refit: callable future exact-selected-epoch refit over all eligible training windows; not invoked in Task 109
- data flow: existing frozen 22-lookback/63-horizon windows, past-only context features, fit-only normalizer, fit/selection split, and training-derived cumulative-return scale
- new dependencies: NONE

### Governed runner

- `src/neuralmarket/research/wgan_runner.py`
- Git blob: `2e87199a2237b4f23576fa181a38ba29807c8ae2`
- readiness: dry-run supported without data access, markers, checkpoints, or training
- scientific execute boundary: requires later committed authorization, matching implementation/provenance identities, requested CUDA, resolved CUDA, runtime identity, one invocation, training authorization true, validation false, final-test false
- no automatic reserve chain, overwrite, relaunch, result-dependent retry, CPU fallback, validation access, or final-test access

### Runtime configuration

- path: `configs/research/structured_vol_wgan_comparator_v1.yaml`
- SHA-256: `de0b4fe775ead7bfad922189d5562c31f7229bbc785d3887e6342909b9a288f7`
- Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`
- effective config identity: member seed tuple is bound later by authorization; no implementation blob is frozen in the execution contract before the implementation commit

### Execution contract

- path: `reports/research/structured_vol_v5_wgan_execution_contract_v1.json`
- SHA-256: `4f2ab91c04e82a7eab26bad4808e57b8ed5eb0df53eaa6cbf95aa23ff3a951d4`
- Git blob: `194b68797538010f35f5d48a2ec7c4cc4eee533f`
- implementation binding: deferred to later authorization after this implementation commit
- methodology binding: preregistration and Amendment 060 identities are explicit
- seed schedule binding: `reports/research/structured_vol_v5_seed_schedule_v1.json`, SHA-256 `8c471c3311b05e647b543e46e310a8f1b1055ec00d4690f726dcd6d775f06fd0`, Git blob `558d08bfee98dbd0c170d65e6a9b1737700c9e98`

### Focused tests

- `tests/unit/models/test_wgan_cde.py`
- Git blob: `0ccb4369c8d3f918e78ed2f07506b02e01cc32fa`
- `tests/unit/research/test_wgan_comparator.py`
- Git blob: `eb6130980ff2a8eacc6a024ab159c3daa014d371`
- `tests/unit/research/test_wgan_runner.py`
- Git blob: `a9d63e669882755d4709c960425388a166d877b9`

## Determinism and smoke boundary

- scientific requested device: `cuda`
- scientific expected resolved device: `cuda`
- CPU fallback: prohibited
- deterministic algorithms: enabled by existing device helper
- cuDNN benchmark: disabled
- cuDNN deterministic: enabled
- unsupported nondeterministic kernel: fail closed
- CPU smoke: tiny synthetic tensors only; model construction, generator forward, critic forward, WGAN losses, gradient penalty, and finite checks
- CPU smoke label: `NON_SCIENTIFIC_TEST_ONLY`
- CPU smoke: no SPY data, optimizer loop, scientific checkpoint, execution marker, WGAN namespace, governed runner execute, Gate-v2 execution, or H2 result

## H2 metric implementation

The implementation exposes metric serializers only; it does not calculate an
H2 result or emit an H2 status.

- attempt denominator: exactly five fixed WGAN primary identities
- `valid_completed_member_fraction`: numerator is only `GATE_PASS_VALID` plus `GATE_FAIL_VALID`; denominator 5
- `nonfinite_or_missing_checkpoint_rate`: attempt-level denominator 5 with indicator and reason per primary
- reason taxonomy: `NONFINITE_TRAINING_OR_SELECTION`, `MISSING_VALID_CHECKPOINT`, `GOVERNANCE_INVALID`, `OTHER_FROZEN_FAILURE`, `NONE`
- governance-invalid reason: preserved as `GOVERNANCE_INVALID`; never converted to non-finite training
- non-finite reason: preserved separately as `NONFINITE_TRAINING_OR_SELECTION`
- missing checkpoint: no imputation
- completed metrics: normalized best checkpoint epoch SD and checkpoint selection metric SD
- completed-member SD: sample SD, `ddof=1`
- reserve treatment: a valid reserve may appear as a reserve-contributed completed member and never rewrites a primary
- preregistration binding: explicit constant and metadata binding to `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037`
- Amendment 060 binding: explicit constant and metadata binding to `2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c`
- H2 calculation: ZERO

## Focused verification

- focused command: `.venv/Scripts/python.exe -m pytest tests/unit/models/test_wgan_cde.py tests/unit/research/test_wgan_comparator.py tests/unit/research/test_wgan_runner.py -q`
- focused result before implementation commit: 27 passed
- focused result after implementation commit: 27 passed
- Ruff: passed for all implementation and focused-test paths
- mypy: passed for all three implementation modules
- compileall: passed
- dry-run CLI: passed; output explicitly classified `NON_SCIENTIFIC_TEST_ONLY`; training not invoked
- scientific data access: ZERO
- scientific training: ZERO
- scientific simulation: ZERO
- scientific checkpoint: ZERO
- scientific execution marker: ZERO
- Gate execution: ZERO
- validation: ZERO
- external validation: ZERO
- final-test access: ZERO
- authorization creation: ZERO
- provider/scientific network: ZERO
- Git-remote network: ZERO

## Protected state

- WGAN preregistration: unchanged
- Amendment 060: unchanged
- N5 analysis: unchanged
- reserve-j01: unchanged and remains `GATE_PASS_VALID`
- Gate-v2 specification/evaluator: unchanged
- Neural-SDE runner/config/authorization: unchanged
- final test: remains `SEALED`
- H2: remains unresolved pending WGAN comparator results

## Amendment status

- methodology changed: NO
- implementation frozen: YES
- authorization created: NO
- scientific execution performed: NO
- H2 result calculated: NO
- final-test access: NO
- self-authentication: ABSENT BY DESIGN; this amendment does not embed its own future SHA-256 or Git blob

WGAN COMPARATOR:
IMPLEMENTED_PENDING_INDEPENDENT_AUDIT

WGAN AUTHORIZATION:
NOT CREATED

WGAN SCIENTIFIC EXECUTION:
NOT PERFORMED

H2:
UNRESOLVED_PENDING_WGAN_COMPARATOR

FINAL TEST:
SEALED
