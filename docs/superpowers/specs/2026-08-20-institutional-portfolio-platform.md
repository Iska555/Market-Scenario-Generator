# Market-Scenario-Generator → Institutional Portfolio Platform

**Source:** operator brief, 2026-08-20.
**Repo:** `Iska555/Market-Scenario-Generator`
**Stack:** FastAPI + numpy/pandas/scipy/sklearn backend on Render, React (Vite + Tailwind + Recharts) frontend on Vercel.

This is a quantitative risk platform that will be published as a public, permanent
track record. Correctness is the product. Every number on screen must be
reproducible from the code and defensible to a portfolio manager who reads the
source. Do not add features until the correctness phase is complete.

Work in phases. After each phase, run the test suite and stop for review. Do not
skip ahead.

---

## PHASE 0: Ground rules

Before writing code:

1. Create `backend/tests/` with pytest. Every quantitative function gets a test
   with a closed-form or analytically known answer. No exceptions.
2. Create `docs/METHODOLOGY.md`. Every formula implemented gets an entry: the
   equation, the assumption set, the estimation window, and what breaks it. This
   file is the public defence of the numbers.
3. Add `ruff` + `mypy` to the backend and a pre-commit hook.
4. Replace all `np.random.seed(...)` global calls with an explicit
   `np.random.default_rng(seed)` Generator threaded through every sampling
   function. The current code seeds global numpy state inside a
   `ThreadPoolExecutor`, which is a race condition under concurrent requests.
5. Pin dependency versions in `requirements.txt`. `yfinance` breaks its schema
   regularly.

---

## PHASE 1: Fix the correctness bugs (blocking, do these first)

These are confirmed defects, not preferences. Fix each, add a regression test for
each.

### 1.1 The scenario ladder is computed from 30 paths, not N paths

`PortfolioSimulationResponse` in `backend/main.py` does not include a
`final_returns` field. `frontend/src/App.jsx:716` checks
`portfolioResults.final_returns`, does not find it, and falls through to line
719, deriving the Best/Bullish/Median/Bearish/Worst ladder from
`portfolio_paths_sample`, which is truncated to `portfolio_paths[:30]`. The user
configures 1000 paths and sees percentiles from 30.

**Fix:** compute all percentiles server-side from the full path array and return
them in a `percentiles` object (1, 5, 10, 25, 50, 75, 90, 95, 99). Keep
`portfolio_paths_sample` for charting only, and rename it
`portfolio_paths_chart_sample` so no one ever computes statistics from it again.
Add an assertion in the frontend that throws if a statistic is derived from the
chart sample.

### 1.2 GMM is never used in portfolio mode

In `simulate_portfolio`, the `model == "gmm"` branch sets `means.append(0.0)`
(commented `# Risk-neutral`, which is wrong: risk-neutral drift is the risk-free
rate, not zero) and `stds.append(clean_rets.std())`, then calls
`simulate_correlated_returns`, which draws from `np.random.randn`. The fitted GMM
is discarded. The UI toggle is decorative.

**Fix:** implement genuinely correlated non-Gaussian sampling. Two acceptable
approaches, implement the first and leave the second as an interface:

- **Multivariate GMM:** fit `sklearn.mixture.GaussianMixture` on the joint returns
  matrix (n_obs x n_assets, `covariance_type='full'`). Sample directly from the
  joint mixture. This captures both fat tails and regime-dependent correlation,
  which is the actual point: correlations rise toward 1 in crashes and a single
  Cholesky factor cannot express that.
- **Copula layer:** fit marginals separately (Student-t or empirical), couple with
  a t-copula. Expose `correlation_model: Literal["gaussian", "gmm_joint", "t_copula"]`.

Report the fitted mixture weights, component means, and component covariances in
the API response so the regimes are inspectable.

### 1.3 The tail filter destroys the tails

`log_returns[log_returns.abs() < 0.20]` in both endpoints deletes every daily move
above 20% before fitting. The single-asset GMM path then applies
`np.clip(returns_matrix, -0.12, 0.12)` and `returns_matrix - np.mean(returns_matrix)`,
which truncates simulated tails and annihilates drift.

**Fix:** remove the magnitude filter entirely. Replace with an explicit, logged
data-quality step that only removes verified data errors: zero-volume days, stale
repeated prices, and prices flagged by a split/dividend check. Remove the clip.
Remove the demean. If outliers are genuinely a problem, handle them with a
Student-t marginal, not by deleting reality.

### 1.4 Portfolio return is computed as a weighted sum of log returns

`build_portfolio_paths` does
`portfolio_returns[path,t] = np.sum(weights * returns_matrix[path,t,:])` on log
returns, then exponentiates. Log returns are additive across time, not across
assets. This understates portfolio return by the Jensen/diversification term.

**Fix:**

```python
simple_returns = np.expm1(log_returns)             # asset simple returns
port_simple    = simple_returns @ weights          # portfolio simple return, daily rebalanced
port_path      = np.cumprod(1 + port_simple, axis=1)
```

Then make the rebalancing assumption a first-class parameter:

- `rebalance: Literal["daily", "monthly", "quarterly", "annual", "buy_and_hold"]`
- `buy_and_hold` must let weights drift with performance: track units held, not
  weights.
- Add optional `rebalance_band: float` for threshold rebalancing (rebalance only
  when a weight drifts more than X from target).
- Add optional `transaction_cost_bps: float` charged on turnover at each rebalance.

Document in METHODOLOGY.md that daily rebalancing is a rebalancing-premium-flattered
assumption and that buy-and-hold is the honest default for a retail-scale portfolio.

### 1.5 Sharpe ratio is wrong twice

`sharpe_ratio = mean / annualized_vol` where `mean` is a horizon-cumulative return
(365 days) and `annualized_vol` is annualized. Two errors: no risk-free rate, and
mismatched horizons.

**Fix:**

```python
excess_annualized = (1 + total_return) ** (252 / horizon_days) - 1 - risk_free_rate
sharpe = excess_annualized / annualized_vol
```

Add `risk_free_rate` as a request parameter, defaulted by fetching the 3-month
T-bill (`^IRX`) and cached. Display the assumed rf next to the Sharpe in the UI.
Add Sortino (downside deviation denominator) and Calmar (return over max drawdown)
alongside.

### 1.6 "Contribution" is mislabelled

`asset_stats.contribution` is `weights[i] * asset_mean[i] / abs(total_weighted_return)`,
a return contribution normalised by an absolute value that breaks sign handling for
negative portfolios. It is rendered in the UI under a heading called "Allocation".

**Fix:** compute and return both, clearly named:

- `return_contribution_pct`: w_i * r_i / portfolio_return, signed, no abs() in the
  denominator.
- `risk_contribution_pct`: the correct marginal-contribution-to-risk decomposition,
  `MCR_i = (Σw)_i / σ_p`, `CTR_i = w_i * MCR_i`, normalised so `Σ CTR_i = σ_p`.

Risk contribution is the number that matters. Render it as its own panel titled
"Risk Contribution", not "Allocation". Show weight and risk contribution side by
side so the divergence is visible.

### 1.7 VaR reporting is ambiguous

VaR is reported as a bare percentage with no horizon and an inconsistent sign
convention.

**Fix:** return VaR and CVaR as an object:
`{confidence, horizon_days, value_pct, value_currency, convention: "loss_positive"}`.
Label in the UI as "VaR (95%, 1-year)". Add 1-day and 10-day VaR (the Basel
horizon) alongside the full-horizon figure. Add the CVaR/VaR ratio, which is the
tail-fatness diagnostic and the entire justification for the GMM feature existing.

### 1.8 Vectorise

`simulate_correlated_returns` loops `for path in range(num_paths): for t in range(horizon):`
— that is `num_paths * horizon` Python-level matmuls (365,000 for the default
config). `build_portfolio_paths` has the same double loop.

**Fix:** `X = Z @ L.T` and `port = returns @ weights`. Use `np.einsum` where
clearer. Expect a 100x speedup. Add a benchmark test asserting a 5000-path,
10-asset, 1000-day simulation completes in under 2 seconds.

Also: `cholesky_decomposition` uses `np.linalg.eigvals` on a symmetric matrix. Use
`eigvalsh`. When regularising, project to the nearest positive-definite correlation
matrix (Higham's algorithm) and re-normalise the diagonal to 1, rather than adding
`1e-6 * I` and hoping.

---

## PHASE 2: The estimation problem (the real intellectual gap)

The current engine estimates drift as the sample mean of 3 years of daily log
returns. The sample mean of returns is the noisiest estimator in finance. With
annual vol of 25% and 3 years of data, the standard error on the annualised drift
is roughly 25% / sqrt(3) ≈ 14%. A 4% drift estimate is statistically
indistinguishable from zero, from 20%, and from -10%. Every forward-looking number
the app produces currently inherits that noise and presents it as a point estimate
to two decimal places.

Fix this explicitly, because it is the difference between a student project and
something a professional will respect:

1. **Make drift a declared choice, not a silent default.** Add
   `drift_model: Literal["historical", "zero", "risk_free", "capm", "black_litterman", "user_specified"]`.
   - `capm`: `μ_i = rf + β_i * ERP`, with ERP a stated parameter (default 4.5%) and
     β estimated against a benchmark. Far more stable than sample mean.
   - `user_specified`: the honest option. You state your view; the engine shows its
     consequences.
2. **Show the uncertainty.** Display a confidence interval on every drift estimate.
   Render the annualised drift as `4.1% ± 14.0% (95% CI)` in the UI, not as `4.12%`.
   This single change communicates more quantitative maturity than every other
   feature combined.
3. **Shrink the covariance matrix.** Sample covariance with 3 assets is fine; with
   20 assets and 750 observations it is garbage and its inverse is worse. Implement
   Ledoit-Wolf shrinkage (`sklearn.covariance.LedoitWolf`) as the default estimator,
   with sample covariance as an option. Report the shrinkage intensity.
4. **Add block bootstrap as a simulation model.** `model: "bootstrap"` — resample
   overlapping blocks of historical joint returns (block length ~20 days) rather
   than assuming any parametric form. This preserves fat tails, volatility
   clustering, and cross-asset correlation structure for free and requires no
   distributional assumption. It is often the most defensible model in the list.
   Expose block length as a parameter.
5. **Add GARCH(1,1)** as already promised in the README roadmap, with the `arch`
   package. EWMA's flat vol forecast is a special case with λ fixed and no mean
   reversion. Show the vol term structure converging to the long-run level.

---

## PHASE 3: Missing analytics

Add these. Every one is standard in an institutional risk report and every one is
absent.

**Path-dependent metrics** (the actual reason to run Monte Carlo rather than a
closed-form):

- Maximum drawdown distribution across paths: median MDD, 95th percentile MDD, and
  the full histogram.
- Probability of breaching a drawdown threshold at any point in the horizon (not
  just at terminal), for user-set thresholds (-10%, -20%, -30%).
- Time-to-recovery distribution: given a breach, how long until the path returns to
  its prior peak.
- Ulcer index.

**Benchmark-relative analytics** (currently zero of these exist, and they are the
entire subject of the alpha/beta module you are studying):

- `benchmark: str` request parameter, default `SPY`.
- Beta of the portfolio and of each asset, via OLS of excess returns on benchmark
  excess returns. Report the standard error and R² of the regression, not just the
  point estimate.
- Blume-adjusted beta (`0.67β + 0.33`) alongside raw beta.
- Jensen's alpha as the regression intercept, annualised, with its t-statistic. An
  alpha without a t-stat is a decoration.
- Tracking error and information ratio.
- Up-capture and down-capture ratios.
- Rolling 60-day beta chart, to demonstrate that beta is not a constant.

**Portfolio construction** (turn the simulator into a management tool):

- Efficient frontier via `scipy.optimize`, with the current portfolio plotted as a
  point on the risk/return plane. This one chart makes the whole application
  legible in three seconds.
- Minimum variance, maximum Sharpe, risk parity (equal risk contribution), and
  equal weight portfolios, each solved and displayed as comparison points.
- Constraints: long-only toggle, per-asset weight caps, sector caps.
- Explicitly warn in the UI that mean-variance optimisation is famously unstable
  and error-maximising, and that the risk-parity and minimum-variance solutions do
  not depend on the noisy drift estimate. Being the person who knows the optimiser
  is dangerous is worth more than being the person who ran it.

**Stress testing** (deterministic, not stochastic):

- Historical scenario replay: apply the actual joint return sequences from
  Sep-Nov 2008, Feb-Mar 2020, Jan-Oct 2022, and Aug 2024 to today's portfolio.
- Factor shocks: parallel rate shift, equity -20%, vol +10 points, correlations
  forced to 0.9.

---

## PHASE 4: The live portfolio and public track record

This is a new subsystem. Build it as a separate module, `backend/src/portfolio/`,
with persistent storage. The simulator becomes one tab; the live track record
becomes the front page.

### 4.1 Data model (Postgres, via SQLAlchemy + Alembic migrations)

```
transactions   id, timestamp_utc, ticker, side, quantity, price, fees, currency, note
positions      derived, never stored as source of truth
cash_flows     id, timestamp_utc, amount, type (deposit|withdrawal)
prices_eod     ticker, date, close_adj, source, fetched_at
theses         id, ticker, opened_at, thesis_md, target_price, invalidation_condition, horizon, conviction
thesis_reviews id, thesis_id, reviewed_at, outcome, what_i_got_wrong_md
nav_daily      date, nav, twr_daily, benchmark_close, flows
```

The transactions table is append-only. No UPDATE, no DELETE. Corrections are new
offsetting rows. Enforce it with a database trigger, not a code convention.

### 4.2 Return calculation (get this right or the whole site is worthless)

- **Time-weighted return (TWR)** is the headline number, computed with the Modified
  Dietz method or true daily unit-value accounting. TWR removes the effect of
  deposit and withdrawal timing, which is why it is the GIPS standard for evaluating
  a manager: you are not credited for luck in when money arrived.
- **Money-weighted return (IRR)** reported alongside, because it is what actually
  happened to the capital.
- Report both. Explain the difference on the page. Most amateur track records report
  neither correctly.
- Gross and net of a stated notional fee, so the numbers are comparable to a fund.

### 4.3 Tamper-evidence (this is the credibility problem, not the analytics)

Anybody can publish a chart claiming a 40% return. A track record only has value if
it is provably not edited after the fact. Implement:

- A daily job that serialises the full position and NAV state, hashes it (SHA-256),
  and chains it to the previous day's hash. Publish the hash chain.
- Commit each day's snapshot to a public git repository via GitHub Actions on a
  schedule. Git history is timestamped by a third party and rewriting it is visible.
- Optionally, publish the daily hash to a public timestamping service.
- Publish the thesis before the trade, with a timestamp. A public, dated,
  pre-registered thesis that turned out wrong is worth more professionally than an
  undated one that turned out right.

Put a short "How to verify these numbers" page on the site explaining exactly this.
That page is the single most impressive thing on the entire domain.

### 4.4 Public reporting page

- Cumulative TWR versus benchmark, since inception, log scale.
- Underwater (drawdown) chart. Never show a return chart without one.
- Monthly returns table, portfolio and benchmark, with the calendar-year row.
- Live risk panel: current beta, vol, concentration, top 5 risk contributors.
- Positions table with entry date, cost basis, current weight, risk contribution,
  and a link to the thesis.
- Closed positions with the post-mortem attached. Publish the losers. A track record
  without losses is either a lie or too short to mean anything.
- A prominent statistical honesty box: state the inception date, the number of
  months of data, and the fact that a track record shorter than roughly a decade
  cannot statistically distinguish skill from luck at a Sharpe of 1. Compute and
  display the standard error on the realised Sharpe:
  `SE(SR) ≈ sqrt((1 + SR²/2) / n)`.

### 4.5 Legal, non-negotiable

- Persistent disclaimer: personal account, not investment advice, no solicitation,
  past performance is not indicative of future results.
- Do not accept, pool, or manage third-party capital. Managing money for others is
  a regulated activity in nearly every jurisdiction, including the UK (FCA
  authorisation) and the EU. A public track record of a personal account is a
  portfolio piece; the same page plus one outside investor is an unauthorised
  business.
- No performance projections presented as expectations. The simulator's outputs are
  conditional scenarios, and every chart must be labelled as such.

---

## PHASE 5: Engineering hardening

- Move `yfinance` behind a `PriceDataProvider` interface with a Postgres-backed
  cache. The current in-memory dict evaporates on every Render cold start, and
  Render's free tier sleeps. A public track record cannot depend on a cache that
  dies.
- Add a fallback provider (Tiingo or Alpha Vantage) with automatic failover.
- Corporate action handling: verify adjusted prices against known splits. Note that
  `yf.download(auto_adjust=True)` already returns adjusted values in `Close`, which
  makes the `"Adj Close" in data.columns` branch in `data_download.py` dead code.
  Remove it.
- Rate limiting and request size caps on the public API.
- Structured logging (structlog), request IDs, and a `/api/version` endpoint
  returning the git SHA, so any published number can be traced to the exact code
  that produced it.
- Frontend: split `App.jsx` (currently monolithic) into feature components. Add
  error boundaries. Add a loading skeleton, because Render cold starts take 30+
  seconds and the current UI just hangs.
- CI: GitHub Actions running pytest, ruff, mypy, and a frontend build on every push.
  Block merge on failure.

---

## Definition of done for Phase 1

- [ ] Every percentile displayed anywhere is computed from the full path set.
- [ ] Selecting GMM produces demonstrably non-Gaussian output (test: excess
      kurtosis of simulated returns significantly exceeds 0).
- [ ] No magnitude-based return filtering or output clipping anywhere in the
      codebase.
- [ ] Portfolio returns computed from simple returns with an explicit, parameterised
      rebalancing rule.
- [ ] Sharpe uses excess return over a stated risk-free rate with matched
      annualisation. Test: a portfolio returning exactly rf has a Sharpe of 0.00.
- [ ] Risk contributions sum to portfolio volatility (test to 1e-9).
- [ ] All statistics reproducible from a seed; two runs with the same seed produce
      byte-identical output under concurrent load.
- [ ] 5000 paths x 10 assets x 1000 days runs in under 2 seconds.
- [ ] METHODOLOGY.md documents every formula and every assumption.
