# Data Governance

No dataset is downloaded, generated, or committed in the current repository
foundation. This document describes the intended immutable data layers and the
rules that govern them.

## Immutable layers

1. **Raw** — vendor-native data exactly as delivered. Treated as immutable.
2. **Canonical** — normalized canonical tables derived from raw data.
3. **Features** — derived model features computed from canonical tables.
4. **Episodes** — hedging episodes assembled for training and evaluation.

Each layer is derived only from the one above it. Lower layers are never edited
in place; changes flow forward through regeneration.

## Rules

- Raw licensed vendor data **will not** be committed to Git.
- Generated local data will be tracked through DVC in later work, not Git.
- Only metadata, manifests, schemas, and small approved summaries belong in Git.
- No dataset is downloaded as part of this foundation.
- All data access must be legal, ethical, and consistent with vendor licensing.
- Dataset split manifests are not changed without explicit approval.
- The final test set is never used for debugging, model selection, or tuning.

## Provenance

Every experiment records its dataset hashes and configuration so that any result
can be reproduced from versioned CLI commands and configurations.
