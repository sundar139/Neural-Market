# Research Protocol Amendment 026

## V5 Training Authorization Commitment Hardening

**Date:** 2026-08-19
**Task:** NM-R4-V5-TRAINING-RUNNER-V4-REPAIR-033
**Prior:** runner v3 `b9d0392` (blob `476c07aa1dcea77d13b29c352f8acb4dbf858f9e`) → v4 `4f9d087`/`88fc3cc` (blob `89aaa10a91259cd4fb4a4b448f3c6f4907b3a3d8`, sha `74ab19646fbe373db071bbc59ad9377993d1bbb901dcfecab14baa2bf3f30ae3`); contract v3 `05b1551978c6db9a00e0400f87fc6dd3f2fdd200` superseded by v4.

**Governance deviation:** Runner v3 was amended (`e993fb5` → `b9d0392`) before contract v3 despite prohibition. Recorded here, not rewritten. No scientific bytes changed. v4 proceeds append-only from `33c7bdf`.

## 1. Objective

Make authorization commitment absolute: must be committed at HEAD with clean worktree/index and matching blob. No pre-commit exception.

## 2. Rule (A–G)

A. Inside repo. B. `git ls-files --error-unmatch`. C. `HEAD:<path>` nonempty 40-hex, else refuse. D. `git diff --quiet` clean. E. `git diff --cached --quiet` clean. F. `hash-object == HEAD blob`. G. Record HEAD blob.

Staged-new (no HEAD) → refuse. Staged-modified → refuse. Unstaged → refuse. Committed clean → pass commitment check.

## 3. Preserved v3 Safety

Atomic `os.link` start, one scientific invocation, training-only split, allowlist `v5-seed-02..05`, hash checks, recipe structural binding, runner/schedule binding, no retry, no reserve, gate failure FAILED/2, terminal evidence, no validation/external/final.

## 4. Contracts

- v1 `97149dc3b25c7b65997664e3b67b800c6bed1008` SUPERSEDED
- v2 `1c20175755319f187bb865c7cef3ccbbacc58ebd` SUPERSEDED
- v3 `05b1551978c6db9a00e0400f87fc6dd3f2fdd200` SUPERSEDED
- v4 CURRENT — see JSON
- Authorization freeze: NOT AUTHORIZED until audit

## 5. Next

Independent audit of runner v4 + contract v4 before any authorization freeze.
