# Research Protocol Amendment 027

## V5 Replicate Training Execution Contract v5

**Date:** 2026-08-19
**Task:** NM-R4-V5-TRAINING-RUNNER-V5-REPAIR-035
**Prior:** runner v4 `9ea4224` (v2-bound) → v5 `41042ad` (v5-bound, exit 3, pytorch); contracts v1-v4 superseded.

**Binding:** Runner now requires `reports/research/structured_vol_v5_training_execution_contract_v5.json` unconditionally (exists, tracked, committed, clean, blob equality). No bypass.

**Recipe:** Must contain runner, contract v5, schedule at authorized blobs; ancestor of HEAD; v4-only ancestors fail.

**Gate failure:** Exit 3, FAILED/GATE_V2_FAILED, full metrics/criteria/epochs/checkpoint evidence, no retry.

**Success:** Adds `pytorch_version` to report.

**Contracts:** v1-v4 SUPERSEDED, v5 CURRENT, authorization NOT AUTHORIZED.

**Next:** Independent audit of runner v5 + contract v5.
