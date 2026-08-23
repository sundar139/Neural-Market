# Amendment 062 — V5 WGAN Comparator Seed-Binding Repair

**Date:** 2026-08-22
**Task:** `NM-R3-V5-WGAN-SEED-BINDING-REPAIR-111`
**Risk:** R3
**Starting branch:** `main`
**Starting HEAD:** `791d158783b09be4b0a8dcb76e9b06bd129b7adc`
**Safety branch:** `safety/pre-wgan-seed-binding-repair-791d158`
**Prerequisite audit:** `NM-R4-V5-WGAN-COMPARATOR-IMPLEMENTATION-AUDIT-110`
**Audit verdict:** `REPAIR REQUIRED`
**Repair commit:** `315aa278bf2c9d36e061bf643b00e839e22c1447`
**Scope:** seed-binding implementation repair, synthetic behavioral regression tests, and append-only protocol record only.

## 1. Trigger and governing boundary

Audit 110 blocking findings 1–3 identified random-source mismatches in the
Task-109 WGAN comparator implementation. Task 111 repairs those bindings to
match the frozen pre-existing contract. This amendment does not rewrite
Amendments 059, 060, or 061 and does not alter the preregistration JSON.

The governed transitions are:

`DISCOVER -> DECIDE -> MUTATE -> VERIFY -> REPORT`

The repair is limited to the training/refit data-seed bindings, the common
internal-selection generated-path seed binding, an explicit reserved-role
comment for `eval_seed`, and synthetic behavioral tests in the existing focused
WGAN comparator test module.

The following are unchanged and prohibited in Task 111:

- WGAN architecture and model implementation;
- WGAN-GP objective and gradient-penalty definition;
- optimizer, learning rate, betas, epsilon, weight decay, and update ratio;
- batch size, epoch budget, patience, checkpoint logic, and exact-selected-epoch refit semantics;
- search space and search/budget contract;
- H2 metric definitions and H2 calculation;
- runtime configuration, runner, execution contract, Neural-SDE code, Gate-v2, N4/N5 artifacts, and final controls;
- authorization creation, scientific training, scientific simulation, checkpoints, Gate execution, H2 calculation, validation, external validation, and final-test access;
- provider/scientific network, Git-remote network, and push.

**FROZEN METHODOLOGY CHANGED:** NO

**TASK-109 IMPLEMENTATION CONFORMED TO FROZEN SEED CONTRACT:** NO

**TASK-111 REPAIRS IMPLEMENTATION TO MATCH THE PRE-EXISTING FROZEN CONTRACT:** YES

## 2. Frozen random-source contract reconstructed

The controlling records were read before mutation:

- `reports/research/structured_vol_v5_wgan_comparator_preregistration_v1.json`;
- `reports/protocol/research_protocol_amendment_059.md`;
- `reports/protocol/research_protocol_amendment_060.md`;
- `reports/protocol/research_protocol_amendment_061.md`;
- `src/neuralmarket/research/wgan_comparator.py`;
- `src/neuralmarket/research/wgan_runner.py`;
- `configs/research/structured_vol_wgan_comparator_v1.yaml`;
- all Task-109 focused WGAN tests.

Independent source inspection reproduced Audit 110's findings. The frozen
random-source mapping is:

| Random role | Frozen source |
|---|---|
| Model initialization | member `model_init_seed` |
| Training static latent noise | member `data_seed` |
| Training temporal noise | member `data_seed` |
| Training window shuffle/order | member `data_seed` |
| Refit static/temporal noise | member `data_seed` |
| Refit window shuffle/order | member `data_seed` |
| Internal-selection generated paths | common fixed seed `7777` |
| Real circular/moving-block bootstrap reference | common fixed bootstrap seed `8801` |
| Future post-training evaluation/Gate | common fixed evaluation seed `8283` |

The preregistration records `data_seed` for training noise and shuffled-window
order, `generated_path_seed=7777`, `bootstrap_seed=8801`, block length `22`,
`1024` generated paths, `1024` real reference paths, and common post-training
`eval_seed=8283`. The runner binds model initialization through
`set_deterministic_seeds(config.model_init_seed)`.

**Contract conflict:** NONE

**Verdict:** `FROZEN_RANDOM_SOURCE_CONTRACT_RECONSTRUCTED_WITHOUT_CONFLICT`

## 3. Defective Task-109 bindings

Audit 110 identified the following defective bindings exactly:

- training noise: `bootstrap_seed` `8801` used incorrectly;
- training order: `bootstrap_seed` `8801` used incorrectly;
- refit noise: `bootstrap_seed` `8801` used incorrectly;
- refit order: `bootstrap_seed` `8801` used incorrectly;
- selection generated paths: member `data_seed` used incorrectly instead of common `7777`.

These defects could make training/refit stochastic streams incorrectly share the
real-reference bootstrap source and could make internal-selection generated
paths member-varying rather than common across members.

## 4. Corrected bindings

Task 111 applies the following minimum implementation repair:

| Path | Corrected source |
|---|---|
| Model initialization | member `model_init_seed` |
| Training static latent noise | member `data_seed` |
| Training temporal noise | member `data_seed` |
| Training window shuffle/order | member `data_seed` |
| Refit static/temporal noise | member `data_seed` |
| Refit window shuffle/order | member `data_seed` |
| Internal-selection generated paths | common `INTERNAL_SELECTION_GENERATED_PATH_SEED = 7777` |
| Real bootstrap reference | `config.bootstrap_seed`, frozen at `8801` |
| Future post-training evaluation/Gate | `config.eval_seed`, frozen at common `8283` |

The training and refit paths use the same repository-local generator binding
helper with `config.data_seed`. The helper drives both `_draw_noise` calls and
`torch.randperm` window order. No derived or ad-hoc seed offset was introduced.
The internal-selection path uses the explicit common constant and does not read
member `data_seed` or `eval_seed`.

`eval_seed=8283` remains present in the frozen WGAN configuration and is now
explicitly documented in source as **reserved for future post-training
Gate/evaluation only**. It is not a training-noise seed, window-order seed,
internal-selection generated-path seed, or bootstrap seed. No future Gate path
was created or executed to consume it.

Block length `22`, both `1024` path counts, exact-selected-epoch semantics, and
all training/checkpoint logic remain unchanged.

## 5. Behavioral seed-binding regression tests

The existing focused module `tests/unit/research/test_wgan_comparator.py` was
extended. Tests are synthetic and `NON_SCIENTIFIC_TEST_ONLY`; they do not load
SPY data, invoke the governed runner, require CUDA, perform scientific
training, perform scientific refit, create checkpoints, publish markers, run a
Gate, calculate H2, or access validation/final-test data.

The tests behaviorally verify:

- training static latent and temporal streams vary with different `data_seed`
  values and reproduce exactly for the same `data_seed`;
- deterministic training-window order varies with different `data_seed` values
  on a sufficiently large fixture and reproduces exactly for the same seed;
- the shared training/refit generator source produces distinct noise and order
  streams for distinct data seeds without executing refit;
- internal-selection generated draws are identical for otherwise identical
  members with different `data_seed` values;
- the internal-selection draw reproduces from frozen seed `7777` and differs
  from the reserved evaluation seed `8283`;
- the real bootstrap reference remains controlled by `8801` with block length
  `22`;
- `eval_seed=8283` remains separate from selection and bootstrap randomness.

Focused verification command:

`.venv/Scripts/python.exe -m pytest tests/unit/models/test_wgan_cde.py tests/unit/research/test_wgan_comparator.py tests/unit/research/test_wgan_runner.py -q`

Focused result after repair commit: **32 passed, 0 failed**.

Ruff passed for the implementation and focused WGAN paths. Mypy passed for the
three WGAN implementation modules. Compileall and Git diff checks passed.

## 6. Implementation identities

The repair commit records these new identities:

- comparator source:
  `src/neuralmarket/research/wgan_comparator.py`
  Git blob: `87f9ad37bcd92d7d0acc0383a5b8bab8a8a2f33b`;
- focused comparator tests:
  `tests/unit/research/test_wgan_comparator.py`
  Git blob: `cbac4f76ddf9b6265cb84db15f7e0a373e41b3b7`;
- implementation repair commit:
  `315aa278bf2c9d36e061bf643b00e839e22c1447`.

Pre-repair identities were:

- comparator source Git blob: `5f6591c272dea51bcf522ee1d3454e5291e89814`;
- focused comparator tests Git blob: `eb6130980ff2a8eacc6a024ab159c3daa014d371`.

Unchanged implementation identities:

- WGAN model Git blob: `2f5cf1dd2cc3eaa7c563529e5ae7bb127dcbbdfe`;
- WGAN runner Git blob: `2e87199a2237b4f23576fa181a38ba29807c8ae2`;
- runtime configuration Git blob: `e0740afc24697f2eab3620a4243d04411aa508cb`;
- execution-contract Git blob: `194b68797538010f35f5d48a2ec7c4cc4eee533f`.

**Execution-contract identity:** unchanged; authorization implementation
binding remains deferred to a later separately governed authorization.

**Verdict:** `SEED_BINDING_REPAIR_MINIMAL_AND_IDENTITY_RECORDED`

## 7. Protected methodology and scientific state

The following frozen identities and states remain unchanged:

- preregistration SHA-256:
  `6c4a2725daea9cc616cb540245f669ab8d230428309713202f9bb66ea535a037`;
- preregistration Git blob:
  `72311888542ee83ff497b5f0adbbaf6429e8452a`;
- Amendment 060 SHA-256:
  `2f9bb12f66496d2a7e60d8773271788090c7882c5a7c88171fabff45a6f8239c`;
- Amendment 060 Git blob:
  `a1ba052abe8b4a50887ec84b934e16a328e60596`;
- Amendment 061 bytes and historical identity;
- N5 family analysis SHA-256:
  `84e53a3e77e6eea12a1449aa08763766c6106d7fe16eb36d1285f0bd71bdf564`;
- N5 family analysis Git blob:
  `7c10e622db3415cae53fb9547d6ebef15decbb76`;
- Neural-SDE runner/configuration/authorization;
- Gate-v2 specification/evaluator;
- final chronological test: `SEALED`.

Task-111 creates no authorization, no WGAN scientific namespace, no scientific
marker, no WGAN checkpoint, and no scientific result.

## 8. Firewalls and status

Required Task-111 counts at this amendment stage are:

- authorization creation: `0`;
- scientific training: `0`;
- scientific simulation: `0`;
- scientific checkpoint: `0`;
- execution marker: `0`;
- Gate: `0`;
- H2 calculation: `0`;
- validation: `0`;
- external validation: `0`;
- final-test access: `0`;
- provider/scientific network: `0`;
- Git-remote network: `0`;
- push: `0`;
- amend: `0`;
- rebase: `0`;
- reset: `0`.

WGAN AUTHORIZATION:
`NOT CREATED`

WGAN SCIENTIFIC EXECUTION:
`0`

H2:
`UNRESOLVED`

FINAL:
`SEALED`

This amendment is append-only and does not modify Amendment 061's bytes.
**Self-authentication:** absent by design; Amendment 062 does not embed its own
future SHA-256 or Git blob.

## 9. Status and next governed action

WGAN COMPARATOR:
`SEED_BINDING_REPAIRED_PENDING_INDEPENDENT_AUDIT`

WGAN AUTHORIZATION READINESS:
`NOT_READY_PENDING_REAUDIT`

REPOSITORY TEST BASELINE:
`GREEN_PENDING_SINGLE_FULL_SUITE_VERIFICATION`

H2:
`UNRESOLVED_PENDING_WGAN_COMPARATOR`

FINAL TEST:
`SEALED`

The next governed action is an independent read-only audit of the Task-111
seed-binding repair before any WGAN authorization.

---

*Amendment 062 records a minimal implementation correction to restore the
pre-existing frozen WGAN random-source contract. It changes no methodology,
creates no authorization, performs no scientific execution, and leaves the
final test sealed.*
