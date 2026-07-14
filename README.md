# NeuralMarket

Research-grade foundation for conditional neural SDE market simulation and
cost-aware hedging.

## Research question

Does a conditional neural stochastic differential equation trained with a
non-adversarial signature-kernel score (1) reproduce financial path structure
more faithfully and stably than classical and adversarial alternatives, and
(2) improve downstream cost-aware hedging risk on held-out real-market episodes?

## Core scope

Initial confirmatory scope: SPY underlying; European calls and puts; maturities
of roughly 5–30 trading days; moneyness 0.90–1.10; daily hedging; 95% CVaR of
hedging loss as the primary risk endpoint. Signature-score and WGAN neural SDE
generators are compared against classical baselines (bootstraps, GBM,
GJR/EGARCH, Heston), and a GRU deep hedger against Black–Scholes delta variants.
See the [research protocol](reports/protocol/research_protocol_v1.md).

## Non-claims

The simulator is a physical-measure scenario generator. It is **not** claimed to
be risk-neutral or arbitrage-free, is not intended to price securities without
additional assumptions, and statistical improvement does not imply production
trading profitability.

## Repository status

Foundation and guarded acquisition tooling only: reproducibility, configuration,
environment diagnostics, data contracts, and a metadata-only January 2019 pilot.
No market records, models, hedging policies, or results exist yet. No empirical
result is claimed. Confirmatory results must be reproducible through versioned
CLI commands and configurations. Notebooks will never contain authoritative
implementations.

## Requirements

Python 3.11 (`>=3.11,<3.12`).

## Setup (PowerShell)

```powershell
Set-Location "<repository-root>"
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\pre-commit.exe install
```

Or run `scripts/bootstrap.ps1`.

## Quality verification

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

This runs Ruff lint and format checks, strict mypy, pytest with branch coverage
(minimum 85%), pre-commit, a CLI smoke test, and environment-report generation.

## Environment report

```powershell
& .\.venv\Scripts\neuralmarket.exe environment check `
    --config "configs/reproducibility/default.yaml" `
    --output "reports/environment/environment_check.json"
```

## Market-data qualification

Before any historical download, the data source is qualified and the chronological
splits are frozen. These commands are offline and need no credentials:

```powershell
& .\.venv\Scripts\neuralmarket.exe data contracts validate
& .\.venv\Scripts\neuralmarket.exe data split freeze --config "configs/data/spy_daily_databento.yaml" --output "data/manifests/split_manifest_v1.json"
& .\.venv\Scripts\neuralmarket.exe data manifests verify --source "data/manifests/source_manifest_v1.json" --split "data/manifests/split_manifest_v1.json"
```

Source qualification needs a Databento key in a local `.env` and only issues
metadata, symbology, and cost-estimation requests — no records are downloaded:

```powershell
& .\.venv\Scripts\neuralmarket.exe data qualify --config "configs/data/spy_daily_databento.yaml" --output "reports/data/source_qualification.local.json" --source-manifest "data/manifests/source_manifest_v1.json"
```

See [source selection](docs/data/source_selection.md), [canonical contracts](docs/data/canonical_contracts.md),
[split policy](docs/data/split_policy.md), and [Protocol Amendment 001](reports/protocol/research_protocol_amendment_001.md).

## Guarded acquisition pilot

The January 2019 SPY pilot plans 25 training-only requests using metadata
endpoints; it does not download records. Preparation, offline verification,
single-use authorization, read-only recovery, spend caps, storage, and lineage
are documented in [pilot acquisition](docs/data/pilot_acquisition.md) and
[data lineage](docs/data/data_lineage.md). Paid execution uses durable journal
accounting: uncertain billing blocks automatic retry, stale attempts are surfaced
by recovery, and manual portal reconciliation is applied only from ignored local
artifacts without provider activity.

## Data and secrets

Raw licensed vendor data is never committed; generated data is tracked with DVC
later. See [data governance](data/README.md). Never commit `.env`, API keys,
tokens, checkpoints, or `.venv`. Copy `.env.example` to a local, ignored `.env`
for optional non-secret settings.
