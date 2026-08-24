# Methodology

This document is the defence of every number the platform reports. Each formula
implemented in the codebase has an entry below giving the equation, the assumption
set, the estimation window, and what breaks it.

Nothing here is a projection or an expectation. Every simulated figure is a
**conditional scenario**: the consequence of a stated model and a stated parameter
set, not a forecast.

## Conventions

These hold everywhere unless a section states otherwise.

| Convention | Value | Defined in |
|---|---|---|
| Trading days per year | 252 | `src/risk_metrics.TRADING_DAYS_PER_YEAR` |
| Return type used for estimation | daily log returns, `r_t = ln(P_t / P_{t-1})` | `src/returns_preprocess.compute_log_returns` |
| Return type used for portfolio arithmetic | daily simple returns, `s_t = exp(r_t) - 1` | `src/portfolio_math` |
| Prices | split- and dividend-adjusted close (`yfinance auto_adjust=True`) | `src/data_download` |
| Portfolio value path | `portfolio_paths[p, t]` is the value of an initially-1.0 portfolio after `t+1` days; the initial 1.0 is implicit | `src/portfolio_math.build_portfolio_paths` |
| Terminal return | `portfolio_paths[:, -1] - 1.0` | `src/portfolio_math` |
| Tail-risk sign | losses positive (`convention: "loss_positive"`) | `src/risk_metrics.tail_risk` |
| Percentile interpolation | `numpy` linear interpolation between order statistics (`np.percentile` default) | `src/risk_metrics.percentiles` |
| Randomness | one explicit `numpy.random.Generator` per request, threaded into every sampling function. No global `numpy` random state is read or written anywhere in the codebase. | `main.py` |

### Why log returns for estimation and simple returns for aggregation

Log returns are additive **across time**, which is what makes them the right unit
for fitting a daily model and for compounding a single asset's path. They are not
additive **across assets**: `ln(1 + Σ wᵢsᵢ) ≠ Σ wᵢ ln(1 + sᵢ)`. By the concavity of
the logarithm the right-hand side is strictly smaller whenever asset returns
differ, so aggregating a portfolio in log space understates its return by the
diversification (Jensen) term. Portfolio aggregation therefore always happens in
simple-return space. See "Portfolio construction" below.
