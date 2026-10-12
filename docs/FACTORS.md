# Historical factor regression — Phase 9C

This stage fits a supplied research-factor model to recorded, flow-neutral daily
portfolio returns. It explains variation in the selected historical sample.
It is separate from position contribution, benchmark comparison, covariance risk,
expected-return assumptions and investment decisions. Acceptance evidence:
[PHASE_9C_AUDIT.md](PHASE_9C_AUDIT.md).

## Private contract and evidence

`POST /api/factors/portfolios/{portfolio_id}/report` takes `performance` (the exact
Phase 8 request), `factors`, `include_contribution` (default false) and optional
`benchmark` (Phase 9B evidence). The same locked ledger snapshot supplies all
selected reports. There are no database writes, migrations or provider calls.
Successful and expected error responses use `Cache-Control: no-store`; validation
errors omit submitted input values. Keys are excluded from reports.

`factors.identity` requires model ID/revision/name, provider/methodology reference,
account currency, `currency_policy=already_in_portfolio_currency`,
`calendar=UTC_calendar_daily`, `periods_per_year=365`, `units=decimal_simple_return`,
`risk_free_convention=period_effective_return`, effective dates covering the full
window and ordered publication/retrieval timestamps. One to six explicitly supplied
factor definitions each need `factor_id`, name, description and convention:

- `excess_market_return`: a market total return already reduced by its declared
  risk-free series. It is not reduced by risk-free again by this engine.
- `long_short_spread_return`: a supplied long-minus-short research portfolio return,
  such as size, value, profitability, investment or momentum. No additional
  risk-free subtraction is applied to a spread.

IDs are unique; `alpha` is reserved for the intercept. The template selects no
model/factors. Names do not certify the economic construction or suitability of
the supplied series; the provider/methodology fields must explain them.

`factors.rows` use interval **closing dates**, excluding the opening baseline.
Each row contains `risk_free_return`, `factor_returns` keyed by declared IDs,
`observed_at`, `published_at`, `retrieved_at` and source. Supply returns as quoted
decimal strings (`"0.01"` means 1%, not 0.01%). Client imports require strings or
null; backend exact-decimal validation also accepts lossless integers and internal
Decimal values but rejects floats/booleans. Values use the existing 30-digit,
10-decimal-place bound; factors are signed and are not filtered by magnitude.
Risk-free period returns must exceed −100% and may be negative.

Dates are unique, ordered and inside the exact reporting window. Observation time
must belong to the closing date in UTC, no later than its close; publication is
not before observation, retrieval is not before publication, and retrieval is no
later than the report's knowledge cutoff. Older-day observations are rejected;
there is no age allowance or factor-return carry-forward. An omitted row, missing
declared key or explicit null value is a coverage gap; undeclared keys are rejected.

Risk-free input is a **daily effective simple return**, separate from the annual
effective rate in Phase 8 statistics. Do not substitute that annual rate or subtract
it directly from daily returns. No yield/day-count conversion is performed.

The [Kenneth French factor library](https://mba.tuck.dartmouth.edu/pages/Faculty/ken.french/data_library.html)
is a research reference, not a connected provider. Its
[developed-market factor description](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5developed.html)
specifies USD returns and a trading-day risk-free construction. Those conventions
do not directly establish matching GBP/UTC-calendar-day portfolio intervals.
Deliberate currency/calendar/unit transformation and its evidence are prerequisites
for using such data here. Do not invent weekend zeros or silently reduce samples.
There is no provider download, licensed archive or automatic FX transformation.

## Response and estimator

For interval t, portfolio simple return p_t is Phase 8's daily unit-value return.
It includes booked net dividends and fees and neutralizes external capital flows.
The interval's opening units must be positive. Otherwise its comparable portfolio
return is undefined while the embedded independent Phase 8 report is preserved.

With supplied period-effective risk-free return r_t and factor row f_t:

```text
y_t = p_t − r_t
y_t = alpha + Σ_j beta_j f_tj + e_t
```

Every expected selected interval must have a valid funded portfolio return,
risk-free value and every declared factor. Fits require **at least 30 observations**;
this is a policy guard, not evidence that 30 observations establish reliable skill.
No fit is substituted from a smaller complete-case sample. Independently available
performance/contribution/comparison and daily excess-return evidence remain visible.

Let n be the paired count, k the declared factor count and q=k+1 the coefficient
count including intercept. Residual degrees of freedom are n−q. With F the factor
matrix, compute means m and RMS centered scales s_j, form
`Z = [1, (F_j−m_j)/s_j]`, and obtain its thin SVD `Z=U diag(d) Vᵀ`.
Solve using the SVD inverse; transform back to original factor units:

```text
theta = V diag(1/d) Uᵀ y
beta_j = theta_j / s_j
alpha = theta_0 − Σ_j m_j beta_j
fitted = Z theta
residual = y − fitted
```

The design is converted to finite binary floating point for the numerical fit.
Constant converted factor columns are undefined. Numerical rank uses
`max(Z.shape) × machine_epsilon × d_max`; a singular value at/below this tolerance
withholds the fit. Scaled condition number `d_max/d_min > 1e8` also withholds it.
There is no ridge regularization, factor dropping or denominator floor. The
reported condition number describes the centered/scaled design, not raw units;
the alpha estimate can still be uncertain when factor means are far from zero.

## Uncertainty and fit statistics

HC3 uses leverage h_t and squared residual weights `e_t²/(1−h_t)²` in the OLS
sandwich covariance. Standard errors are square roots of its diagonal in original
coefficient units. The implementation calculates weighted inverse-row norms
rather than directly inverting normal equations. This is the estimator documented
by [statsmodels HC3](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.HC3_se.html);
statsmodels is not added as a dependency.

```text
t_j = coefficient_j / HC3_standard_error_j
SSE = Σ e_t²
TSS = Σ (y_t − mean(y))²
R² = 1 − SSE/TSS
adjusted R² = 1 − (1−R²)(n−1)/(n−q)
daily residual standard deviation = sqrt(SSE/(n−q))
```

Alpha and its standard error are daily decimal excess returns; the UI displays
daily percentage points. Factor coefficients, their standard errors, t-statistics,
R² and condition numbers are dimensionless. Daily residual volatility displays
as a percentage. R²/adjusted R² display four decimals to avoid making a nearly
perfect synthetic fit appear exactly perfect. Full precision remains in JSON.
There is no annualized alpha or coefficient compounding.

An exact constant response has undefined R²/adjusted R². A zero standard error
has an undefined t-statistic, never infinity. For a numerical exact fit, inference
is withheld when `norm(e) <= 64 epsilon max(norm(y), norm(fitted))`; residuals and
point estimates are retained rather than clipped. If any `1−h <= 64 epsilon`,
HC3 errors/t-statistics are withheld as high-leverage inference. These declared
numerical diagnostics do not regularize coefficients or imply substantive certainty.
Overflow, failed decomposition or non-finite arithmetic yields typed undefined fit
results. Negative coefficients, t-statistics or adjusted R² are not clamped.

HC3 addresses heteroskedasticity, **not serial correlation**. The displayed
t-statistics do not establish a Student-t reference distribution, p-value or
significance decision under dependence. HAC, bootstrap and confidence intervals
are deferred. Model specification, data quality, selection bias, changing exposures,
omitted factors and short samples remain uncertainties. A fitted daily intercept
is not persistent skill, a causal effect or an investor expected-return view.

Regression residual identities `y=fitted+e`, `Σe≈0` and `Fᵀe≈0` hold within
floating-point tolerance for accepted OLS fits. They explain sample variation;
they do not geometrically reconcile cumulative portfolio return or replace Phase
9A accounting contribution. No factor covariance risk or Brinson is inferred.

## Replay and acceptance mapping

The private report retains the full factor identity/rows, canonical evidence hash,
methodology/HC3 declaration, minimum count, paired/expected counts, degrees of
freedom, fit reason, coefficients/inference, fit statistics and daily fitted values/
residuals, plus complete selected underlying reports.

```powershell
./backend/.venv/Scripts/python.exe scripts/replay_factors.py path/to/private-report.json
```

Replay verifies the embedded performance source/runtime/input/ledger/output
identity, optional contribution/comparison, factor hash/settings and every rebuilt
factor output. It needs no provider, key or database. Altered evidence, coefficient,
standard error, residual, statistic or methodology fails. Exact numerical replay
is tested in the documented local runtime, not guaranteed across numerical backends.
This is internal consistency, not independently authenticated data or timestamps.

The conservative source fingerprint changes with Phase 9C. Preserve prior
Phase 8/9A/9B exports and their matching source/runtime. This stage retains an
86-file exact-byte accepted source bundle and compatible runtime evidence; Git
line-ending conversion must not be bypassed by rewriting report hashes.

| Domain/transport | Acceptance evidence |
| --- | --- |
| `factors.engine.regress` | Independent one/six-factor OLS and HC3 identities, nonzero means, signed coefficients, residual orthogonality, constant/rank/condition/overflow/exact-fit/leverage cases |
| Identity/row/evidence validators; `build_factor_report` | Units, risk-free/calendar/currency/window/provenance, ordered dates/IDs, gaps, funded intervals and snapshot settings |
| `factors.replay.verify_factor_report` | JSON replay and altered evidence/inference/daily/statistic/methodology/setting rejection |
| Route; factor cache middleware | Authentication, no-store success/errors, sanitized validation, same snapshot, actual PostgreSQL all-table immutability/lock timeout/stale correction |
| Performance controller/inputs/results | Coherent selected transport, empty templates, memory-only keys, input/account/lock/late clearing, safe errors and meaningful unit/null/context presentation |

HAC/calendar reconciliation, rolling beta/capture, durable portfolio benchmark
defaults, live provider contracts, factor covariance risk, fund typing, actual broker
reconciliation, Brinson and publication retain separate acceptance requirements.


## Phase 9D integration update — 2026-10-12

Optional benchmark evidence can bind to an explicit saved portfolio setting
revision. Its complete receipt is retained in the nested comparison and verified
offline, including after a later settings clear. This changes source/export identity;
older accepted reports retain their matching archived source. No regression formula
changed. See BENCHMARK_SETTINGS.md and FACTOR_DATA_READINESS.md for the saved
identity contract and prospective real-factor currency/calendar review. Saved
benchmark settings do not establish usable research-factor data.
