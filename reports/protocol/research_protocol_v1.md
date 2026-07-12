# NeuralMarket Research Protocol v1

Status: frozen v1. No empirical result is claimed in this document.

## Research question

This study evaluates whether a conditional neural stochastic differential
equation (neural SDE) trained with a non-adversarial signature-kernel score:

1. reproduces financial path structure more faithfully and stably than classical
   and adversarial alternatives; and
2. improves downstream cost-aware hedging risk on held-out real-market episodes.

## Core scope

The initial confirmatory scope is frozen as:

- Underlying: SPY.
- Option payoffs: European-style calls and puts.
- Maturity range: approximately 5–30 trading days.
- Moneyness range: 0.90–1.10.
- Hedge frequency: daily.
- Primary generator comparison:
  - signature-score neural SDE;
  - WGAN neural-CDE neural SDE.
- Required classical generator baselines:
  - IID historical bootstrap;
  - stationary or block bootstrap;
  - geometric Brownian motion (GBM);
  - GJR-GARCH or EGARCH;
  - Heston.
- Primary hedging comparison:
  - GRU deep hedger;
  - Black–Scholes delta;
  - dynamically updated Black–Scholes delta;
  - cost-adjusted delta.
- Primary risk endpoint: 95% CVaR of hedging loss.
- Secondary risk objective: entropic risk.
- Primary transaction-cost model: proportional costs.

Intraday data, rough volatility, diffusion models, FI-2010, order-book
generation, market impact, and multi-asset hedging are extensions rather than
core confirmatory claims.

## Hypotheses

- **H1 (generator fidelity):** the signature-score neural SDE reproduces financial
  path structure more faithfully than classical and adversarial baselines.
- **H2 (training stability):** the signature-score training objective is more
  stable across seeds and epochs than adversarial (WGAN) training.
- **H3 (cost-aware hedging performance):** deep hedging on signature-score
  synthetic paths reduces cost-aware hedging risk on real held-out episodes.
- **H4 (CVaR versus entropic risk):** the relative behavior of 95% CVaR and
  entropic-risk objectives is characterized and compared.
- **H5 (synthetic pretraining then real fine-tuning):** synthetic pretraining
  followed by real fine-tuning improves held-out hedging risk over training on
  real data alone.

## Primary endpoint

Hedging loss is defined as:

```text
L = -P&L
```

The relative CVaR change is defined as:

```text
Delta_CVaR =
(CVaR_0.95(Deep) - CVaR_0.95(BS)) /
CVaR_0.95(BS)
```

Smaller CVaR is better.

The primary hedging claim requires **all** of the following:

- `Delta_CVaR < 0`;
- the paired 95% confidence interval excludes zero;
- the improvement is at least 5%;
- the improvement holds at two or more nonzero cost levels;
- no unacceptable deterioration in average loss;
- no pathological turnover or position behavior;
- the result is not driven by one seed or one isolated market period.

## Experimental governance

The following rules are frozen:

- No random train/test split; chronological splitting only.
- Purging and embargoing are required.
- Normalizers are fit on training data only.
- Option episodes may not cross split boundaries.
- Both episode inception and expiration must fall in the same split.
- Hyperparameters may not be selected using the final test period.
- The final test set may be accessed only after models, metrics, baselines,
  transaction costs, and statistical procedures are frozen.
- All neural comparisons use at least five independent seeds.
- Failed seeds must be reported and may not be silently discarded.
- Compute and hyperparameter-search budgets must be comparable between the
  signature and adversarial models.
- Paired and dependence-aware statistical inference is required.
- Multiple primary comparisons must use Holm correction.
- Market-period uncertainty and training-seed uncertainty are reported separately.

## Failure criteria

A neural generator run is predeclared **failed** if any of the following occurs:

- nonfinite training or validation loss;
- no valid checkpoint;
- more than 0.1% of generated paths contain nonfinite values;
- generated terminal-return dispersion collapses below 10% of the corresponding
  real-data dispersion;
- generated volatility exceeds ten times the declared training reference without
  a documented stress-test reason;
- an unresolved data-leakage violation is detected;
- an unreconciled accounting error is detected.

## Non-claims

- The simulator is a physical-measure scenario generator.
- It is not claimed to be risk-neutral.
- It is not claimed to be arbitrage-free.
- It is not intended to price securities without additional assumptions.
- Statistical improvement does not automatically imply production trading
  profitability.

## Protocol amendments

- No silent changes to primary hypotheses or endpoints.
- Amendments must be dated and justified.
- Changes made after final-test access must be labeled exploratory.
- Exact chronological split dates will be frozen in a later protocol amendment
  after data availability and legal access are confirmed.
- Model training may not begin until those split dates and purge rules are frozen.

### Amendment log

- 2026-07-12 — Protocol v1 frozen. No amendments yet.
