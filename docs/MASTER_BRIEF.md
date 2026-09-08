# Codex Master Brief: Rebuild Market-Scenario-Generator into an Investment Portfolio Management Platform

Repository:

`https://github.com/Iska555/Market-Scenario-Generator`

Current stack:

- Backend: FastAPI
- Quant stack: NumPy, pandas, SciPy, scikit-learn
- Frontend: React + Vite + Tailwind + Recharts
- Current deployment: Render backend + Vercel frontend

## Mission

This repository currently began as a Monte Carlo / stochastic market simulator built before the owner had significant finance knowledge.

It must now be rebuilt into a serious personal **Investment Portfolio Management Platform**.

The objective is not to create another retail portfolio tracker and not to create a system that pretends historical returns can reliably forecast future returns.

The platform should eventually support a complete investment process:

1. research businesses and assets,
2. record explicit investment theses,
3. form transparent expected-return assumptions,
4. construct portfolios,
5. analyse prospective risk,
6. stress-test positions and portfolios,
7. maintain an accurate live investment ledger,
8. calculate portfolio performance,
9. attribute performance and risk,
10. publish a transparent personal track record.

The final product should be credible enough that a portfolio manager, quant researcher, asset-management professional, or technical interviewer could inspect the methodology and source code and understand exactly where every reported number came from.

**Correctness, auditability, and intellectual honesty are more important than feature count.**

Do not build flashy functionality on top of questionable mathematics.

---

# Core investment philosophy

The platform must reflect the following principles.

## 1. Historical performance is evidence, not a forecast

Historical returns may be used to estimate or study:

- volatility,
- covariance,
- correlation,
- beta,
- drawdowns,
- factor exposures,
- volatility clustering,
- regime behaviour,
- liquidity,
- stress behaviour,
- empirical return distributions.

Historical sample mean return must NOT silently become a forward-looking expected return.

Expected return must always come from an explicitly selected model or declared investor view.

---

## 2. Monte Carlo is a conditional risk tool

Monte Carlo simulation remains useful, but it is no longer the centre of the application.

It belongs inside a future module called:

`Risk & Scenario Lab`

Simulation outputs must be presented as:

**conditional scenarios based on stated assumptions**

and never as predictions of future market returns.

---

## 3. Price paid is not the investment thesis

The platform should help prevent behavioural mistakes such as:

- refusing to sell because a position is below purchase price,
- taking profit mechanically at an arbitrary percentage,
- anchoring to historical price,
- extrapolating past performance,
- holding a stock simply because it previously performed well.

Investment decisions should instead depend on:

- current valuation,
- forward expected return,
- business fundamentals,
- thesis validity,
- opportunity cost,
- risk contribution,
- portfolio constraints,
- market conditions.

A useful conceptual question throughout the product is:

> If this position were not already owned today, would the investor initiate it at the current price under the current thesis?

---

## 4. Every assumption must be visible

Do not hide assumptions inside functions.

Examples:

- risk-free rate,
- equity risk premium,
- benchmark,
- covariance estimator,
- expected-return model,
- rebalancing frequency,
- transaction costs,
- simulation horizon,
- confidence level,
- block-bootstrap length,
- valuation assumptions.

These should either be request parameters, portfolio settings, or clearly documented system defaults.

---

# Canonical build order

Build strictly in this order:

1. Existing repo correctness
2. Methodology and tests
3. Fundamental research data model
4. Thesis system
5. Expected-return and scenario model
6. Portfolio construction and risk contribution
7. Minimal transaction ledger
8. TWR / XIRR performance measurement
9. Factor and performance attribution
10. Public track record

Do not reorder the phases.

Do not start later phases simply because they are more visually interesting.

Each phase depends on the previous ones being trustworthy.

---

# PHASE 1 — Existing repository correctness

## Objective

Before adding new investment-management functionality, repair the existing quantitative engine.

Treat the current simulator as untrusted until proven otherwise.

Inspect the entire codebase before changing implementation.

Document all quantitative defects discovered.

Known issues already identified include the following.

---

## 1. Scenario percentiles

The existing frontend has historically derived scenario statistics from a truncated chart sample rather than the entire Monte Carlo population.

All percentiles and statistics must be calculated server-side using the complete simulated path population.

Chart samples must NEVER be used for statistical calculations.

Return something like:

```python
percentiles = {
    "p01": ...,
    "p05": ...,
    "p10": ...,
    "p25": ...,
    "p50": ...,
    "p75": ...,
    "p90": ...,
    "p95": ...,
    "p99": ...,
}
```

Chart paths should have an unmistakable name such as:

`portfolio_paths_chart_sample`

Never derive statistics from it.

---

## 2. Random number generation

Remove global:

```python
np.random.seed(...)
```

Use explicit generators:

```python
rng = np.random.default_rng(seed)
```

Thread or pass the generator explicitly through sampling functions.

Concurrent requests using identical seeds must be reproducible and must not interfere with one another.

---

## 3. Remove artificial tail deletion

Inspect for logic equivalent to:

```python
returns[returns.abs() < 0.20]
```

or:

```python
np.clip(...)
```

Do not delete legitimate extreme market observations merely because they are inconvenient for the model.

Data cleaning should distinguish:

- actual market moves,
- bad price data,
- stale prices,
- missing observations,
- corporate actions,
- suspected feed errors.

Extreme market observations are not automatically data errors.

---

## 4. GMM correctness

If the UI offers a Gaussian Mixture Model, the backend must genuinely use one.

Do not:

- fit a GMM and discard it,
- replace it with Gaussian draws,
- force drift to zero without explanation,
- clip simulated outputs,
- demean simulated paths after sampling.

For portfolio simulation, prefer a joint model such as:

```python
GaussianMixture(
    n_components=k,
    covariance_type="full"
)
```

fitted to the joint asset-return matrix.

The result should be able to represent regime-dependent covariance.

Expose fitted regime diagnostics:

- component probabilities,
- mean vectors,
- covariance matrices.

Later architecture may also support:

```text
correlation_model:
- gaussian
- gmm_joint
- t_copula
```

but do not implement unnecessary alternatives before the core engine is correct.

---

## 5. Portfolio return arithmetic

Do not compute portfolio return by weighting log returns across assets.

Correct approach for daily rebalanced portfolios:

```python
simple_returns = np.expm1(asset_log_returns)

portfolio_simple_returns = simple_returns @ weights

portfolio_path = np.cumprod(
    1 + portfolio_simple_returns,
    axis=1
)
```

Rebalancing must eventually be explicit:

```text
daily
monthly
quarterly
annual
buy_and_hold
```

For buy-and-hold, holdings must drift with performance.

Do not pretend target weights remain constant.

---

## 6. Sharpe ratio

Sharpe must use excess return relative to an explicit risk-free rate and consistent annualisation.

Do not divide a cumulative horizon return by annualised volatility.

Implement a clean statistics module capable of handling:

- annualised return,
- annualised volatility,
- Sharpe,
- Sortino,
- Calmar,
- max drawdown.

Tests must include an analytically constructed portfolio whose expected excess return is zero and therefore Sharpe is zero.

---

## 7. Risk contribution

Implement proper volatility contribution.

Given covariance matrix:

\[
\Sigma
\]

portfolio weights:

\[
w
\]

and portfolio volatility:

\[
\sigma_p = \sqrt{w^\top\Sigma w}
\]

marginal contribution to risk:

\[
MCR_i = \frac{(\Sigma w)_i}{\sigma_p}
\]

component contribution:

\[
CTR_i = w_i MCR_i
\]

Require:

\[
\sum_i CTR_i = \sigma_p
\]

within numerical tolerance.

Return both:

- weight,
- absolute risk contribution,
- risk contribution percentage.

Never label return contribution as risk contribution.

---

## 8. VaR and CVaR

Risk metrics require explicit metadata.

Return objects similar to:

```json
{
  "confidence": 0.95,
  "horizon_days": 10,
  "value_pct": 0.083,
  "value_currency": 8300,
  "convention": "loss_positive"
}
```

Support both:

- VaR,
- CVaR / Expected Shortfall.

Do not make regulatory claims such as calling arbitrary 10-day VaR "Basel VaR."

Use neutral terminology unless implementing a regulatory framework precisely.

---

## 9. Covariance matrices

Use symmetric-matrix routines such as:

```python
np.linalg.eigvalsh
```

rather than generic eigenvalue functions.

Default covariance estimation should eventually use:

```python
sklearn.covariance.LedoitWolf
```

with sample covariance available as an explicit alternative.

Report shrinkage intensity.

For non-positive-definite correlation matrices, implement a defensible nearest-correlation or nearest-positive-definite treatment rather than repeatedly adding arbitrary epsilon values.

---

## 10. Vectorisation

Remove Python-level loops over simulation path × time where NumPy operations are possible.

Simulation should operate primarily with tensors and vectorised matrix operations.

Examples:

```python
X = Z @ L.T
```

and:

```python
portfolio_returns = asset_returns @ weights
```

Use `einsum` when it improves clarity.

Benchmark performance after correctness is established.

Do not sacrifice mathematical clarity for premature micro-optimisation.

---

# PHASE 2 — Methodology and tests

This phase overlaps the end of Phase 1 but must become a first-class part of the repository.

Create:

```text
backend/tests/
docs/METHODOLOGY.md
docs/ARCHITECTURE.md
```

Add:

- pytest
- ruff
- mypy
- pre-commit
- pinned dependency versions
- CI

Every quantitative function should have a test.

Prefer analytically known cases rather than snapshot testing.

Examples:

### Portfolio return

Two assets with deterministic one-period returns should yield exactly the weighted simple return.

### Portfolio volatility

Construct a simple covariance matrix with manually calculable variance.

### Risk contribution

Require:

```python
sum(component_risk) == portfolio_volatility
```

within strict numerical tolerance.

### Sharpe

Portfolio return exactly equal to risk-free rate:

```text
Sharpe = 0
```

### Max drawdown

Use a known sequence:

```text
100 → 120 → 90 → 110
```

and calculate expected maximum drawdown manually.

### Reproducibility

Same request + same seed:

```text
same output
```

even with concurrent requests.

---

# METHODOLOGY.md standard

For every formula implemented, document:

1. Formula
2. Variables
3. Economic interpretation
4. Estimation method
5. Data window
6. Assumptions
7. Known weaknesses
8. Failure conditions
9. References where appropriate

Example structure:

```markdown
## Ledoit-Wolf Covariance

### Purpose
...

### Formula
...

### Assumptions
...

### Why this estimator is used
...

### Failure modes
...
```

The methodology document is a public defence of the system.

---

# Architectural rule from this point onward

Separate:

```text
Data
Research
Views
Portfolio
Risk
Accounting
Performance
Attribution
Publishing
```

Do not mix these domains inside a giant `main.py`.

Move toward packages such as:

```text
backend/
  src/
    data/
    research/
    views/
    portfolio/
    risk/
    accounting/
    performance/
    attribution/
    public_track_record/
```

FastAPI route handlers should orchestrate application logic.

They should not contain financial mathematics.

---

# PHASE 3 — Fundamental research data model

## Objective

Build the research layer required before expected-return estimation.

The system must understand the underlying investment, not merely its price history.

Create:

```text
backend/src/research/
```

The architecture should support point-in-time security research.

Start with equities.

Do not attempt to support every asset class yet.

---

## Security master

Create entities similar to:

```text
securities
---------
id
ticker
name
exchange
currency
country
sector
industry
asset_type
isin
figi
created_at
```

Use stable internal IDs.

Do not use ticker symbol as permanent identity because tickers can change.

---

## Fundamental observations

Design for point-in-time values.

Example:

```text
fundamentals
------------
security_id
period_end
reported_at
metric
value
currency
source
fetched_at
```

The critical distinction is:

```text
period_end
```

versus:

```text
reported_at
```

The system must eventually be able to answer:

> What information was actually available to the investor on a given historical date?

Avoid look-ahead bias.

---

## Initial fundamental metrics

Support a useful core set such as:

### Valuation

- market capitalisation
- enterprise value
- P/E
- forward P/E if trustworthy data is available
- EV/EBIT
- EV/EBITDA
- price/book
- price/sales
- free cash flow yield
- earnings yield

### Profitability / quality

- ROE
- ROIC
- gross margin
- operating margin
- net margin
- FCF conversion

### Growth

- revenue growth
- EPS growth
- FCF growth

### Balance sheet

- net debt
- net debt / EBITDA
- interest coverage
- current ratio where relevant

### Capital allocation

- dividends
- buybacks
- share dilution
- capex
- acquisitions where available

Do not force all metrics onto every industry.

Bank valuation is not SaaS valuation.

The data model should allow sector-specific research later.

---

## Peer comparison

Eventually support:

```text
company
vs
sector
vs
peer group
vs
company historical valuation
```

But start with the data model and calculation infrastructure.

Do not spend this phase building beautiful peer dashboards.

---

# PHASE 4 — Thesis system

Create:

```text
backend/src/research/thesis/
```

Investment theses should be explicit, timestamped, versioned, and historically reviewable.

A thesis should contain fields like:

```text
ticker
created_at
updated_at
status
horizon
conviction
variant_perception
business_quality
earnings_drivers
catalysts
risks
bear_case
base_case
bull_case
invalidation_conditions
target_or_value_range
required_return
notes
```

Each revision must preserve history.

Never overwrite the past version as though it never existed.

Use versioned records.

---

## Thesis reviews

Create a review model:

```text
thesis_reviews
--------------
thesis_id
reviewed_at
decision
current_price
what_changed
what_was_correct
what_was_wrong
new_information
thesis_still_valid
updated_expected_return
notes
```

Possible decisions:

```text
BUY_MORE
HOLD
REDUCE
EXIT
WATCH
```

The decision should never be determined automatically.

The software provides evidence.

The owner makes the investment decision.

---

## Behavioural decision prompts

Create reusable research prompts in the product such as:

> If you did not own this security today, would you buy it at the current price?

> Has the investment thesis changed, or has only the price changed?

> What evidence would invalidate the thesis?

> Is the expected return from today's price still sufficient?

> Is another available investment now a better use of capital?

These should support disciplined decision-making without becoming investment advice to external users.

---

# PHASE 5 — Expected return and scenario model

Create:

```text
backend/src/views/
```

Expected return must become a declared modelling choice.

Design a common interface:

```python
class ExpectedReturnModel(Protocol):
    def estimate(...) -> ExpectedReturnEstimate:
        ...
```

Possible models:

```text
historical
zero
risk_free
capm
fundamental
black_litterman
user_specified
```

Not all need immediate implementation.

Start with:

1. historical — diagnostic only
2. CAPM
3. user-specified
4. fundamental

Then add Black-Litterman once portfolio views exist.

---

## ExpectedReturnEstimate

Return something similar to:

```python
ExpectedReturnEstimate(
    annual_return=...,
    lower_bound=...,
    upper_bound=...,
    model="fundamental",
    confidence=...,
    assumptions={...},
)
```

Never return a naked number without provenance.

---

# Fundamental expected return decomposition

For equities, create an interpretable decomposition resembling:

\[
E[R]
\approx
\text{fundamental growth}
+
\text{shareholder yield}
+
\text{valuation change}
+
\text{FX effect}
\]

Do not pretend this is an exact identity.

It is an investment framework.

Expose the assumptions.

Example:

```text
EPS / FCF growth: +8%
dividend + buyback yield: +2%
valuation compression: -3%
FX assumption: 0%

estimated expected return ≈ 7%
```

The value of the system is that the investor can inspect and challenge each assumption.

---

# Bear / base / bull cases

Every researched equity should support scenario assumptions.

Example:

```text
Bear:
growth = ...
margin = ...
terminal multiple = ...

Base:
growth = ...
margin = ...
terminal multiple = ...

Bull:
growth = ...
margin = ...
terminal multiple = ...
```

Return:

- scenario value,
- implied upside/downside,
- annualised return over stated horizon.

Avoid false precision.

---

# Reverse valuation

Add architecture for answering:

> What assumptions are required to justify today's market price?

Examples:

- implied long-term revenue growth,
- implied margin,
- implied terminal multiple,
- implied FCF growth.

This should eventually become one of the main research tools.

---

# Historical-return uncertainty

If historical drift is displayed, show its uncertainty.

Do not show:

```text
Expected return: 8.32%
```

as though it were known.

Calculate a confidence interval or standard error.

Historical mean should be visibly labelled:

**historical estimate, not forecast**

---

# PHASE 6 — Portfolio construction and risk contribution

Create:

```text
backend/src/portfolio/construction/
backend/src/risk/
```

The portfolio engine should answer:

> Given the investor's views, risks, and constraints, what does the portfolio look like?

Start with:

- current portfolio
- equal weight
- minimum variance
- maximum Sharpe
- risk parity / equal risk contribution

Later:

- Black-Litterman portfolio
- active benchmark-relative optimisation

---

## Constraints

Support an extensible constraints model:

```text
long_only
max_position_weight
min_position_weight
max_sector_weight
cash_minimum
cash_maximum
max_portfolio_beta
```

Do not implement every constraint immediately.

---

# Risk analytics

Implement:

- volatility
- covariance
- correlation
- marginal contribution to risk
- component contribution to risk
- percentage contribution to risk
- concentration by weight
- concentration by risk

Later:

- tracking error
- contribution to tracking error
- factor risk

Display:

```text
Asset
Weight
Risk Contribution
Expected Return Contribution
```

side by side.

This is one of the most important views in the application.

---

# Optimiser warning

Mean-variance optimisation is highly sensitive to expected-return assumptions.

Do not hide this.

The UI should explicitly explain that maximum-Sharpe optimisation can produce unstable results because expected return is estimated with substantial uncertainty.

Minimum-variance and risk-parity portfolios should be available as comparisons because they do not depend on expected-return estimates in the same way.

---

# Risk & Scenario Lab

Move the existing simulator conceptually into:

```text
backend/src/risk/scenarios/
```

Support separate scenario families.

## Historical replay

Apply actual historical joint return sequences to today's portfolio.

Examples eventually include:

- 2008 financial crisis
- March 2020
- 2022 equity / rates drawdown
- other periods added through data configuration

Do not hardcode narratives into quantitative functions.

---

## Block bootstrap

Resample blocks of joint historical returns.

Preserve:

- cross-asset dependence,
- some volatility persistence,
- empirical tails.

Make block length configurable.

---

## Parametric simulation

Support Gaussian / covariance-based simulation when requested.

Inputs must explicitly contain:

- drift model,
- covariance estimator,
- horizon,
- number of paths,
- seed.

---

## Regime simulation

Use joint GMM only after Phase 1 correctness is complete.

Show component regimes.

---

## Deterministic shocks

Create shock definitions such as:

```text
equity -20%
oil -30%
USD +10%
rates +100bp
volatility +10 points
correlation stress
```

Do not pretend arbitrary shock mappings are exact.

Document factor assumptions and approximations.

---

# PHASE 7 — Minimal transaction ledger

Do not build a full commercial IBOR yet.

Create:

```text
backend/src/accounting/
```

The minimum objective is to correctly derive holdings and cash from actual transactions.

---

## Transactions

Start with:

```text
BUY
SELL
DIVIDEND
FEE
DEPOSIT
WITHDRAWAL
FX_CONVERSION
```

Schema conceptually:

```text
transactions
------------
id
portfolio_id
timestamp
ticker/security_id
type
quantity
price
fees
currency
fx_rate
note
external_reference
created_at
```

Prefer append-only behaviour.

Corrections should eventually be reversal or superseding transactions.

---

## Derived positions

Positions should be derived from transactions.

Do not make mutable position weights the source of truth.

Support:

- quantity,
- average cost,
- current market value,
- portfolio weight,
- unrealised P&L.

---

## Cash

Maintain cash by currency.

Support a portfolio base currency.

FX conversion should be explicit.

---

## Import

Start with the broker actually used by the portfolio owner.

If IBKR is relevant, make its Flex Query / CSV format the first structured importer.

Do not spend time implementing six brokers before one works correctly.

Imports must be idempotent.

---

# PHASE 8 — TWR and XIRR

Create:

```text
backend/src/performance/
```

Performance reporting must distinguish investor timing from manager/investment performance.

---

## Time-weighted return

Implement daily TWR.

Prefer daily unit-value accounting once the ledger supports it.

Cash deposits and withdrawals should not artificially create investment performance.

Support geometric linking:

```text
daily
monthly
quarterly
annual
since inception
```

---

## Money-weighted return

Implement XIRR using actual dated cash flows.

Report:

```text
TWR
XIRR
```

side by side.

Explain:

- TWR evaluates portfolio investment performance independently of cash-flow timing.
- XIRR reflects the investor's realised capital experience including timing.

---

# Performance statistics

Implement from realised portfolio returns:

- annualised return
- annualised volatility
- Sharpe
- Sortino
- Calmar
- maximum drawdown
- longest drawdown
- recovery period
- best month
- worst month
- hit rate
- skewness
- excess kurtosis
- realised VaR
- realised CVaR

Display uncertainty where appropriate.

In particular, short track records must not be presented as statistically conclusive.

---

# PHASE 9 — Factor and performance attribution

Create:

```text
backend/src/attribution/
```

Start with the analyses most relevant to a concentrated personal equity portfolio.

Priority:

1. per-position return contribution
2. factor regression / attribution
3. active risk analysis
4. Brinson attribution where appropriate

---

# Position contribution

Calculate contribution to portfolio return using period-appropriate weights.

Contribution must reconcile to portfolio return within numerical tolerance.

Provide:

- top contributors,
- bottom contributors,
- contribution by sector if classifications exist.

---

# Factor model

Start with public research factors such as:

- market
- size
- value
- profitability
- investment
- momentum

Build regression infrastructure.

For each regression report:

```text
coefficient
standard error
t-stat
R²
sample period
number of observations
```

Do not report alpha without statistical context.

---

# Benchmark analytics

Support an explicit benchmark setting.

Do not hardcode SPY everywhere.

Analytics should eventually include:

- beta
- alpha
- tracking error
- information ratio
- rolling beta
- up capture
- down capture

Benchmark selection belongs to the portfolio configuration.

---

# Brinson

Implement only after the portfolio has meaningful sector/region classification and benchmark weights.

If implemented, use a correct Brinson-Fachler decomposition and ensure attribution effects reconcile.

Do not imply Brinson explains every investment process.

For a stock-selection portfolio, factor and security-level attribution may be more informative.

---

# PHASE 10 — Public track record

Create:

```text
backend/src/public_track_record/
```

The public product should NOT be called a fund unless it legally is one.

Use language such as:

**Personal Portfolio — Public Track Record**

or:

**Personal Investment Portfolio**

This is a personal portfolio and portfolio-management research project.

It must never imply that external capital is being managed.

---

# Public page

The public dashboard should eventually include:

## Performance

- portfolio TWR
- benchmark TWR
- since-inception chart
- drawdown / underwater chart
- monthly returns
- annual returns
- inception date

## Holdings

- position
- weight
- entry date
- current value
- risk contribution
- thesis link

## Research

For selected positions publish:

- original thesis
- subsequent thesis reviews
- bear/base/bull assumptions
- invalidation conditions

## Closed investments

Publish closed positions.

Do not hide losses.

Attach a post-mortem where useful.

---

# Public decision journal

A public track record is not merely a performance chart.

The strongest evidence of an investment process is:

```text
what was believed
when it was believed
what decision followed
what happened
what was learned
```

Preserve timestamped versions.

---

# Tamper evidence

Later implement daily portfolio snapshots.

Potential structure:

```text
date
portfolio state
NAV
positions
previous_hash
current_hash
```

Hash:

```text
SHA-256(
    canonical_snapshot + previous_hash
)
```

Eventually publish snapshots or hashes through a third-party timestamped system such as public Git history.

Do not implement this before performance accounting is correct.

---

# Legal / presentation rules

Persistent disclaimer on public pages:

- personal investment portfolio,
- not investment advice,
- no solicitation,
- past performance does not indicate future results.

Scenario outputs must be labelled as conditional scenarios.

Do not publish simulations as expected future performance.

Do not provide recommendations to external users.

This system manages and analyses the owner's own investment book.

---

# Product structure

The long-term frontend should move toward six primary areas:

```text
1. Portfolio
2. Research
3. Construction
4. Risk Lab
5. Performance
6. Decision Journal
```

Possible secondary areas:

```text
Methodology
Public Track Record
Settings
```

---

# Screen purpose

## Portfolio

Answers:

> What do I currently own and how am I positioned?

Show:

- NAV
- cash
- holdings
- weights
- P&L
- risk contribution
- benchmark context

---

## Research

Answers:

> Why do I own or consider owning this security?

Show:

- fundamentals
- valuation
- peer comparison
- thesis
- scenario assumptions
- expected return

---

## Construction

Answers:

> How much should I own?

Show:

- current weights
- risk contributions
- alternative portfolios
- constraints
- efficient frontier where useful

---

## Risk Lab

Answers:

> What could hurt this portfolio?

Show:

- historical stress
- Monte Carlo
- bootstrap
- regime scenarios
- deterministic shocks
- drawdown probability

---

## Performance

Answers:

> How have the investment decisions actually performed?

Show:

- TWR
- XIRR
- benchmark
- drawdown
- statistics
- attribution

---

## Decision Journal

Answers:

> Was the reasoning good, and what did I learn?

Show:

- thesis history
- trades
- thesis changes
- mistakes
- post-mortems

---

# Engineering requirements

## Backend

Prefer modular domain services.

Example:

```text
backend/
  src/
    api/
    data/
    research/
    views/
    portfolio/
    risk/
    accounting/
    performance/
    attribution/
    public_track_record/
```

Avoid one giant service or `main.py`.

---

## API models

Use typed Pydantic request/response models.

Do not return undocumented dictionaries from financial calculations.

Prefer domain objects.

---

## Typing

Use Python type hints throughout new code.

Run:

```text
mypy
ruff
pytest
```

in CI.

---

## Database

When persistence becomes necessary, use:

- PostgreSQL
- SQLAlchemy
- Alembic

Do not prematurely put research or transactions into ad-hoc JSON files if database persistence is already required.

---

## Data providers

Wrap external data sources behind interfaces.

For example:

```python
class PriceDataProvider(Protocol):
    ...

class FundamentalDataProvider(Protocol):
    ...
```

Do not scatter direct `yfinance` calls throughout financial logic.

Caching should be explicit.

Raw provider data and transformed data should be distinguishable.

---

## Data provenance

Where practical, stored observations should include:

```text
source
retrieved_at
effective_date
```

Financial numbers must have provenance.

---

## Versioning

Add:

```text
/api/version
```

that eventually reports:

- git commit SHA
- build timestamp
- API version

Published statistics should be reproducible from code version + input data where practical.

---

# Frontend requirements

The current React application should gradually be decomposed into feature-level components.

Possible structure:

```text
src/
  features/
    portfolio/
    research/
    construction/
    risk/
    performance/
    journal/
```

Do not perform financial calculations in frontend React components when those calculations belong in the backend.

Frontend responsibilities:

- presentation,
- user interaction,
- formatting,
- charts.

Backend responsibilities:

- financial calculations,
- statistics,
- portfolio accounting,
- modelling.

---

# Naming rules

Use economically precise names.

Bad:

```text
prediction
future return
expected outcome
risk score
contribution
```

when the metric is ambiguous.

Prefer:

```text
conditional_scenario_return
expected_return_assumption
component_risk_contribution
return_contribution
historical_mean_return
```

Names are part of correctness.

---

# Numerical honesty

Avoid displaying unnecessary precision.

If an input assumption is highly uncertain, do not output:

```text
8.3742%
```

Prefer appropriately rounded values and uncertainty ranges.

The software should distinguish between:

```text
measurement
estimate
assumption
scenario
forecast
```

These are not interchangeable.

---

# Documentation standards

Maintain:

```text
README.md
docs/METHODOLOGY.md
docs/ARCHITECTURE.md
docs/BUILD_PLAN.md
```

README should eventually describe the repository as an investment-management platform, not merely a Monte Carlo simulator.

---

# Development workflow

Work phase by phase.

For every phase:

1. inspect current implementation,
2. write down defects / architectural concerns,
3. write or update tests,
4. implement the smallest correct architecture,
5. run the full relevant test suite,
6. update methodology documentation,
7. summarise what changed,
8. list any unresolved risks,
9. stop before the next major phase.

Do not silently jump ahead.

---

# Immediate task for this Codex session

Begin only with:

## PHASE 1 — Existing repository correctness

Do not implement the research database or later portfolio-management features yet.

First:

### Step 1

Inspect the repository structure and identify all files involved in:

- return calculation,
- portfolio simulation,
- GMM simulation,
- covariance/correlation,
- statistics,
- VaR/CVaR,
- RNG,
- frontend scenario statistics.

### Step 2

Compare the actual implementation against the correctness requirements in this document.

Create a concise audit listing:

```text
CONFIRMED BUG
POTENTIAL BUG
DESIGN DEBT
CORRECT AS IMPLEMENTED
```

Include file paths and functions.

### Step 3

Create or reorganise:

```text
backend/tests/
docs/METHODOLOGY.md
```

Add the test infrastructure required for the first correctness fixes.

### Step 4

Repair correctness issues in a logical dependency order.

Suggested order:

```text
RNG
→ return arithmetic
→ statistical calculations
→ scenario percentiles
→ GMM
→ data cleaning
→ covariance handling
→ vectorisation
```

### Step 5

Add regression tests for every fixed defect.

### Step 6

Run:

```text
pytest
ruff
mypy
frontend build
```

where configured.

### Step 7

Update:

```text
docs/METHODOLOGY.md
```

for everything changed.

### Step 8

Stop.

Report:

- files changed,
- bugs fixed,
- tests added,
- test results,
- mathematical assumptions,
- remaining Phase 1 work,
- any disagreement with this brief.

Do not begin Phase 3 or later automatically.

---

# Definition of done for the initial correctness rebuild

Do not consider the existing simulator trustworthy until all of the following hold:

- all displayed scenario percentiles use the complete path population,
- chart samples are never used for statistics,
- simulations use explicit RNG generators,
- identical seeds produce deterministic outputs,
- legitimate extreme observations are not deleted by magnitude filters,
- simulation outputs are not arbitrarily clipped,
- portfolio returns use correct simple-return portfolio arithmetic,
- rebalancing assumptions are explicit,
- Sharpe uses a stated risk-free rate and consistent horizons,
- Sortino and Calmar calculations have tests,
- risk contribution reconciles exactly to portfolio volatility,
- VaR/CVaR contain horizon and confidence metadata,
- covariance estimation is explicit,
- GMM portfolio simulation genuinely uses fitted joint regime distributions,
- quantitative functions have regression or analytical tests,
- methodology documentation matches implementation,
- backend financial calculations are not duplicated in frontend code,
- CI can reproduce the test suite.

---

# Ultimate project standard

The final project should demonstrate the complete loop:

```text
Information
    ↓
Research
    ↓
Investment thesis
    ↓
Expected return / scenarios
    ↓
Portfolio construction
    ↓
Risk analysis
    ↓
Trade
    ↓
Accounting
    ↓
Performance
    ↓
Attribution
    ↓
Review
    ↓
Updated thesis
```

That loop is the product.

The goal is not to produce the largest number of quantitative features.

The goal is to build an investment process whose assumptions, decisions, risks, performance, and mistakes are all inspectable and reproducible.

Correctness is the product.