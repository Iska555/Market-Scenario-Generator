# Quantitative methodology — Phases 1–3

Status: correctness rebuild and Phase 2 analytical verification under the
[master brief](MASTER_BRIEF.md).
Every output is a **conditional scenario under stated assumptions**, not a forecast.
These are simulated statistics, not portfolio performance from a transaction ledger.

## Units, data window and assumptions

Let P(i,t) denote an adjusted price for asset i, x(i,t) its log return, s(i,t)
its simple return, w(i) the initial/target portfolio weight, H the simulated
number of observation periods, N the number of paths and A the periods per year.
Decimal returns are used throughout: 0.08 means 8%. The API calls H
`horizon_days` for compatibility with the brief; these are modeled observation
periods, not elapsed calendar days. A defaults to 252 and is explicit (1–366).
Use 365 for a daily crypto-only history if that is the intended convention.

All estimation uses the requested history window (1–10 years) after the screening
and alignment below. Responses report actual estimation start/end dates, joint
observation count, per-asset input dates and hashes, provider retrieval timestamps
when available, and the common valuation date. At least 30 joint observations are
required. Missing histories are not silently replaced. Insufficient data,
nonconvergence and numerical failure produce errors.

The model is costless, long-only, fully invested, with weights summing to 1.
No leverage, short positions, fees, tax, financing, FX conversion or trades are
modeled. The requested currency denominates the notional; the caller must supply
a universe consistent with that currency. The current provider does not verify
quote currencies. This is a material limitation for multi-currency tickers.

## Prices, returns and screening

**Formula:** x(i,t) = ln(P(i,t)) − ln(P(i,t−1)); s(i,t) = exp(x(i,t)) − 1.

**Meaning and estimation:** log returns compound across time; simple returns
aggregate across assets. The provider requests `auto_adjust=True` and uses its
adjusted Close. This is an adjusted-return proxy including the provider's
corporate-action treatment, not a cash-dividend ledger or an executable quote.

**Screening:** dates must be unique and increasing. Nonpositive and infinite
prices are invalid. Missing prices remain missing. Invalid/missing prices break
both neighboring return intervals; no interpolation, forward filling, or
bridging over invalid rows is performed. Invalid latest prices are rejected.
Identical consecutive prices and |log return| ≥ 0.20 are counted as diagnostic
flags and retained. Such flags do not prove staleness, splits or feed errors.
Zero-volume observations and split-like price ratios are not sufficient evidence
to delete observations.

Joint returns are kept only when both their start dates and end dates agree
across assets. This avoids correlating a Friday–Monday equity return with a
Sunday–Monday crypto return. The number of otherwise-overlapping intervals
excluded for this mismatch is reported. Prices for scenario initialization use
the latest common valid valuation date.

**Weaknesses/failures:** the adapter cannot establish that a flagged observation
is a verified feed error, nor reconcile corporate actions independently.
Provider-adjusted history can be revised. Exchange calendars, holiday gaps,
time zones and intraday valuation cutoffs are not modeled. Mixed calendars can
exclude systematic subsets (for example Mondays); the resulting distribution may
be biased. Review the actual window and interval exclusions before interpretation.
All-zero histories imply no observed variance, not proof of no economic risk.

Implementation: `data_download.py`, `data/preparation.py`,
`returns_preprocess.py`. Tests: data-quality, boundary and arithmetic suites.

## Drift and Gaussian scenarios

Drift selection is **required**, with two Phase 1 choices:

- `historical_diagnostic`: use the fitted historical daily log mean. This is an
  explicit diagnostic calibration to historical evidence, not an expected-return
  forecast. A Gaussian model uses the arithmetic mean of historical log returns.
- `zero_log_drift`: set each model's unconditional daily log mean to zero. This
  is a declared scenario assumption. It is not risk neutrality and does not imply
  zero expected simple return: for Gaussian log returns,
  E[s] = exp(mu + variance/2) − 1.

**Formula:** x = mu + z Bᵀ, where z has independent standard-normal entries and
B Bᵀ = Sigma_log. Tensors have shape N × H × assets. The historical log mean is
already in log units, so no additional −variance/2 adjustment is applied.

**Assumptions:** independent draws across periods, fixed covariance and chosen
drift throughout H. No parameter uncertainty, volatility clustering or structural
break forecasting is included. Historical means are especially noisy. Gaussian
tails and covariance estimated in one window may misrepresent future stress.
Invalid covariance or numerical overflow fails explicitly; no output is clipped.

Implementation: `risk/scenarios/service.draw_returns`,
`risk/covariance.py`, `generative_model.py`.

## Randomness and reproducibility

Each request creates one `numpy.random.default_rng(random_seed)` with a validated
integer seed (default 42), explicitly passed to each sampler. GMM fitting derives
its sklearn integer initialization seed from this generator. No global NumPy RNG
state is used. Cache data is copied, with serialized provider access.

The same request, exact input data, dependency/runtime environment and seed
produce identical results even in concurrent requests. A seed alone cannot
reproduce changing provider data. Generator algorithm/library/BLAS changes or
platform differences can change bitwise output. The test suite verifies
byte-identical API output with deterministic provider fixtures. Raw price hashes
and reported API/build metadata aid identification; exact source observations are
not persisted in Phase 1.

Reference: [NumPy Generator documentation](https://numpy.org/doc/stable/reference/random/generator.html).

## Covariance, correlation and numerical treatment

For T rows x(t) with mean xbar:

**Sample formula:** S = sum[(x(t)−xbar)(x(t)−xbar)ᵀ] / (T−1).

**Ledoit–Wolf formula:** Sigma_hat = (1−lambda) S_MLE + lambda tau I,
where S_MLE uses denominator T, tau = trace(S_MLE)/assets, and lambda is estimated
by sklearn's LedoitWolf procedure. `ledoit_wolf` is the default; `sample` is an
explicit alternative. The API reports lambda (0 for sample covariance).

Gaussian simulation estimates covariance from **log** returns. The ex-ante
risk decomposition separately estimates covariance from **simple** returns.
This distinction is explicit in the result names. Correlation is
rho(i,j) = Sigma(i,j)/sqrt(Sigma(i,i) Sigma(j,j)); zero-variance correlations are
null. The portfolio correlation table uses the historical simple-return estimator.

Symmetric matrices use `eigh`/`eigvalsh`-compatible decomposition.
The sampling factor uses a spectral factor of the symmetric covariance matrix, supporting singular
positive-semidefinite matrices without arbitrary diagonal increments.
Negative eigenvalues within relative roundoff tolerance 1e−12 are set to zero;
material indefiniteness is rejected. This eigenvalue operation is unrelated to
clipping simulated returns.

For an explicitly supplied indefinite correlation matrix, `nearest_correlation`
implements Higham alternating PSD/unit-diagonal projections with Dykstra
correction, Frobenius convergence tolerance 1e−11, maximum 1000 iterations, then
PSD roundoff cleanup and diagonal normalization. This yields a numerical nearest
correlation approximation; it is not used to hide invalid provider inputs.
The estimated covariance path is PSD by construction. No user correlation-matrix
override is exposed in this phase.

**Weaknesses:** shrinkage trades bias for stability. Estimates depend on sample
window and covariance stationarity. Shrinkage does not establish tail dependence
or forecast stress correlation. A singular matrix can be legitimate; rejecting
all singular matrices would itself be an error.

References: [sklearn covariance estimation](https://scikit-learn.org/stable/modules/covariance.html),
[Higham's nearest correlation paper](https://doi.org/10.1093/imanum/22.3.329).

## Joint Gaussian mixture model

**Formula:** x ~ sum_k pi(k) Normal(mu(k), Sigma(k)), with sum pi(k)=1.
Unconditional mean m = sum pi(k)mu(k). Total covariance is
sum pi(k)[Sigma(k) + (mu(k)−m)(mu(k)−m)ᵀ].

The model fits the **joint** T × assets log-return matrix using full component
covariance. Number of components defaults to 3 (1–5), covariance regularization
defaults to 1e−6 in daily log-variance units, three initializations and at most
300 EM iterations. These fixed fitting settings are documented system defaults.
Nonconvergence is an error.

For historical diagnostic drift, fitted means are used directly. For zero log
drift, subtract the fitted mixture's analytic mean from every component mean
**before sampling**. Relative regime means and component covariances are retained.
The realized sample is never demeaned. This deterministic model-location change
is the explicit zero-log-drift assumption.

Each path-period gets an independently sampled categorical component label, then
a joint Gaussian draw using that component. This avoids sklearn's grouped sample
ordering being mistaken for persistent time regimes. The API exposes probabilities,
original and applied component mean vectors, full covariances and unconditional
log covariance, in request ticker order. For GMM the covariance estimator is
`gmm_full`; the requested shrinkage estimator still applies independently to the
historical risk decomposition.

**Weaknesses:** component labels have no intrinsic bull/bear economic identity.
Mixtures can represent state-dependent covariance and non-Gaussian shapes, but
do not guarantee fat tails or identify future states. Components are iid across
time, with no regime persistence or transition model. Regularization materially
affects nearly deterministic data and is disclosed; mixtures can overfit short
histories. No tail observations or simulated draws are deleted.

Reference: [sklearn Gaussian mixtures](https://scikit-learn.org/stable/modules/mixture.html).
Implementation: `gmm_model.py`, `risk/scenarios/service.py`.

## EWMA

**Formula:** v(0)=x(0)²; v(t)=lambda v(t−1)+(1−lambda)x(t)².
The value at t is the next-period variance after incorporating observation t.
The final observation is included. `lambda` defaults to 0.94 and is explicit.

The conditional forecast uses the final variance at every future horizon step.
Samples are x(h)=mu+sqrt(v_last)z(h). This uses a zero-centered historical second
moment approximation, which is approximately variance for small daily means;
it is not a demeaned sample variance. Log drift is chosen separately as above.

**Weaknesses:** initialization matters in short windows, missing intervals reduce
the observations in the recurrence, and squared extreme returns strongly affect
v_last. The flat forecast is consistent with pure EWMA but does not simulate
future volatility clustering. EWMA is single-asset only. Empty/nonfinite series
or invalid lambda/volatility are rejected. Tests cover final-observation inclusion,
missing-index alignment and flat forecasts.

## Portfolio paths and rebalancing

All paths include day zero: asset prices P(i,0), normalized portfolio value V(0)=1.
The API's portfolio chart paths multiply V by the declared initial notional.

**Daily rebalanced formula:** s_p(t)=sum_i w(i)s(i,t);
V(t)=product_{u=1..t}[1+s_p(u)]. Target weights apply at the start of every period.
Log returns are never weighted across assets.

**Buy-and-hold formula:** G(i,t)=exp(sum_{u=1..t}x(i,u));
V(t)=sum_i w(i)G(i,t). Fixed initial units w(i)/P(i,0) cause position weights to
drift with performance. No target-weight reset occurs.

**Interpretation:** these are two different policies; neither is a forecasting
claim. Costs are zero. Default daily rebalancing is an idealization, selectable
explicitly as `rebalance`. Monthly, quarterly, annual, threshold rebalancing and
transaction costs remain unimplemented. Unsupported modes are rejected.

**Failure conditions:** mismatched dimensions, nonfinite returns/prices,
nonpositive initial prices, negative or nonsumming weights, overflow and values
outside floating-point range fail explicitly. No arbitrary path clipping.

Implementation: `portfolio/paths.py`. Tests include +20%/−10% equally weighted
giving exactly +5%, and alternating doubles yielding 2.25 daily versus 2.0 held.

## Annualized statistics, Sharpe and Sortino

Statistics are computed from the full N × H matrix of **portfolio simple returns**,
including the first day. The annualized volatility is pooled daily sample standard
deviation (ddof=1) multiplied by sqrt(A). It is not dispersion of terminal returns.

Annual effective risk-free rate f defaults to an explicitly reported 0%.
Convert it to a modeled period rate r_f = (1+f)^(1/A)−1. There is no hidden
T-bill fetch or fallback rate. Define e = s_p−r_f.

**Sharpe:** A mean(e) / [sqrt(A) std(s_p, ddof=1)].
The numerator is arithmetic mean excess period return annualized consistently.
It is never cumulative horizon return divided by annual volatility.

**Sortino:** A mean(e) / sqrt(A mean[min(e,0)²]).
Downside deviation divides by **all observations**, not only negative ones.
The target equals the explicit per-period risk-free rate.

**Annualized growth:** each path has CAGR_j =
exp[(A/H) sum_t ln(1+s_p(j,t))]−1. The response reports the median path CAGR.
Mean terminal scenario return is separately mean[V(j,H)−1].
Neither equals an investor's expected-return assumption by definition.

**Undefined cases:** insufficient observations for sample volatility yield null.
A ratio denominator ≤1e−14 yields null rather than 0 or infinity.
A nonzero-variance series [0%,20%] with A=2 and annual rf=21% has exactly zero
expected excess return and Sharpe=Sortino=0; this is tested.

**Weaknesses:** sqrt-time scaling assumes the relevant dependence structure.
Pooled estimates in buy-and-hold mix different evolving weights; they are
descriptive conditional scenario summaries. Short horizons can produce extreme
annualized growth figures and should not be interpreted as forecasts.

## Drawdown and Calmar

For each path including time zero, running peak Q(t)=max_{u≤t}V(u).
Loss-positive drawdown D(t)=1−V(t)/Q(t); MDD=max_t D(t).
Return median and 95th percentile MDD across all paths.

**Calmar:** CAGR_j / MDD_j for each path with MDD_j>1e−14.
The reported median Calmar is defined only when **all** paths have a valid
denominator. Otherwise it is null, with `calmar_defined_paths` and
`calmar_total_paths` provided. This avoids selectively reporting a median of
only losing/drawing-down paths. It is not a ratio of median growth to median MDD.

The known sequence 100→120→90→110 gives MDD=25%, CAGR=10% when A=H=3 and
Calmar=0.4. A first-day loss is included. All-flat or all-up paths have undefined
Calmar. MDD is path-dependent and horizon-dependent; these are scenario
distributions, not probabilities of future recovery.

## Risk contribution

Use the selected historical **simple-return** covariance Sigma_daily and initial
weights w. Annualize Sigma = A Sigma_daily.

**Formulas:** sigma_p=sqrt(wᵀSigma w);
MCR(i)=(Sigma w)(i)/sigma_p;
CTR(i)=w(i)MCR(i);
risk_share(i)=CTR(i)/sigma_p.

**Identity:** sum CTR(i)=sigma_p within floating-point tolerance, and nonzero-risk
shares sum to 1. Negative contributions can represent hedging; signs are retained.
Return weight, marginal contribution, absolute contribution and share separately.
Zero portfolio volatility returns zero components and null marginal/share ratios.

This is ex-ante historical risk at the initial weights, identified as
`historical_simple_returns_at_initial_weights`. It does not purport to decompose
the separate simulated pooled volatility, a realized P&L, or future buy-and-hold
weights. Per-asset mean terminal scenario return is not labeled return contribution.
Return attribution is deferred. Covariance limitations apply directly.

## Scenario percentiles, histogram and tail risk

Terminal simple return R_j=V(j,H)−1 uses all N paths. The server calculates
p01, p05, p10, p25, p50, p75, p90, p95 and p99 using NumPy linear interpolation
between order statistics, plus matching currency values and a 30-bin histogram.
All bins include the complete terminal population. Bin endpoints are half-open
except the last, which includes its upper endpoint.

For sorted observations y[0] through y[N−1] and probability q, define
h=(N−1)q, j=floor(h), g=h−j. The linear quantile is
(1−g)y[j]+g y[min(j+1,N−1)]. This is a finite-sample interpolation convention,
not a fitted density or a worst-case loss estimate.
[NumPy quantile definition](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html).

Histogram count b[k] is the sum of indicators that R_j lies in bin k. Its sum
must equal N. All 30 bins span the observed range; no explicit range drops tails.
For identical observations NumPy expands the range around that value; empty bins
are presentation, not evidence of other outcomes. The domain function rejects
empty, nonfinite and non-vector populations, although NumPy itself allows array
flattening. Invalid bin counts fail through NumPy's validation.
[NumPy histogram conventions](https://numpy.org/doc/stable/reference/generated/numpy.histogram.html).

For confidence c and loss L_j=−R_j:

**VaR:** linear-interpolated c-quantile of L.
**CVaR / empirical Expected Shortfall:** average of exactly the worst (1−c)N
equally weighted empirical losses, including a fractional boundary observation
if necessary. Sorting ties does not enlarge the tail probability. This finite
empirical ES convention uses fractional atoms; it is not the average of every
sample below an interpolated return threshold.

Explicitly, let d[0]≥...≥d[N−1] be sorted losses, m=(1−c)N,
k=floor(m), a=m−k. ES=(sum_{i<k} d[i]+a d[k])/m, omitting the boundary
term when k=N. If 0<m<1, ES equals the largest observed loss. Ties retain
their individual probability mass. VaR uses linear interpolation while ES uses
the empirical distribution's tail mass; the two finite-sample conventions are
deliberately distinct and need not form a single interpolated quantile curve.

Each metric reports confidence, H, decimal loss, initial_notional × decimal loss,
currency and `loss_positive`. Negative values are allowed when the relevant tail
still represents a gain. Neither absolute values nor floors at zero are applied.
The percentile endpoints are not maximum/minimum possible losses. VaR is a
quantile, not a guaranteed loss bound; no regulatory label is claimed.

**Weaknesses:** small N gives noisy tail estimates, particularly for 99%.
CVaR can rest on one effective observation. Increasing N reduces sampling error,
not model misspecification. Formal Monte Carlo confidence intervals and separate
1-/10-day reports are not implemented. All reported tails use the requested H.

Implementation: `risk/statistics.py`, `risk/contracts.py`.
[NumPy quantile convention](https://numpy.org/doc/stable/reference/generated/numpy.quantile.html).

## Verification and remaining limits

Analytical tests and regressions cover the implemented formulas, extreme moves,
calendar interval matching, local RNG concurrency, GMM regime behavior, singular
covariance, null ratios, sample independence, provider cache isolation and API
validation. Tests use synthetic data and cannot certify live provider reliability.

See [PHASE_1_AUDIT.md](PHASE_1_AUDIT.md) for current execution evidence and
[ARCHITECTURE.md](ARCHITECTURE.md) for memory/CI/API boundaries.
Phases 1/2 added no research database. Phase 3 adds the research layer described
below. No thesis system, portfolio optimizer, transaction ledger, realized
TWR/XIRR, attribution or public track record is implemented.

## Formula scope and additional summaries

The data-window and currency assumptions at the start of this document apply to
every estimator below. Historical estimators use T valid aligned observations;
scenario statistics use all N simulated paths over H periods. No formula changes
its data window based on chart sample size. Per-formula sections above provide
economic meaning, assumptions, limitations and failure conditions; this table
makes the estimation window and aggregation choices explicit.

| Calculation | Estimation method and window | Interpretation and failure policy |
|---|---|---|
| `fit_gaussian` | mu=sum(x)/T; sigma=sqrt(sum((x−mu)²)/(T−1)), after missing values are removed | Marginal log-return sample fit, no Ito subtraction; reject fewer than two or nonfinite observations |
| Gaussian/EWMA sampling | Independent standard normal draws at each path/period; Gaussian scale sigma, EWMA scale sqrt(v_last) | Fixed conditional distribution, not evolving parameter estimates; internal samplers require validated finite parameters/shapes from callers |
| Sample/Ledoit–Wolf covariance | Full T×assets history, centered sample/MLE conventions documented above | Statistical dependence estimate; both log and simple versions are computed and labeled separately |
| GMM | EM maximum likelihood over the joint historical window, with disclosed covariance regularization | Mixture distribution with iid regime allocation; fitted weights/means/covariances, not economic regime forecasts |
| EWMA | All retained observations in order, zero-centered recursion initialized at the first squared return | Historical second moment and flat conditional scale; missing values are omitted, no calendar decay adjustment |
| Portfolio paths | All H draws for each of N paths; fixed daily weights or fixed initial units | Hypothetical wealth under a stated costless policy; invalid inputs or numerical range failures are rejected |
| Ratios/drawdown/growth | Pooled N×H daily returns for volatility, Sharpe and Sortino; pathwise H-period growth and drawdown before aggregation | Different statistics intentionally aggregate differently; undefined ratios remain null |
| Loss frequency | sum_j 1[R_j<0]/N | Conditional simulated loss frequency; break-even is not a loss; finite N and model risk apply |
| Minimum/maximum return | min_j R_j and max_j R_j over N terminal outcomes | Observed simulation extrema, not support bounds; sensitive to path count |
| Asset scenario mean | mean_j[P(i,j,H)/P(i,0)−1] | Each asset's own terminal mean; not its weighted contribution to portfolio return |
| Currency percentile | Q_q(initial_notional × V(j,H)) | Positive-notional scaling of terminal wealth, not gain alone; no FX conversion |
| Histogram/percentiles/VaR/ES | Equal mass 1/N per terminal outcome; order-statistic conventions above | Finite population summaries; reject invalid/empty populations and invalid tail assumptions |
| Volatility contribution/correlation | Historical simple-return covariance at initial weights; multiply covariance by A for annual risk | Ex-ante decomposition, not realized or simulated return attribution; undefined zero-risk shares/correlations remain null |

Low-level samplers are internal numerical building blocks, not independent input
validation APIs. `ScenarioRequest`, fitting functions and path/statistics functions
enforce the public request boundaries. Distributional tests verify both scale
and location; deterministic tests cover zero variance without manufacturing a
defined Sharpe for a constant return equal to the risk-free rate (0/0 is null).

## Quantitative function to test index

Paths in the first column are relative to `backend/src/`; tests are under
`backend/tests/`. This inventories every current numerical function, including
compatibility helpers that are not used by the API. Typed result containers and
import-only modules have no independent financial formula.

| Functions | Analytical/regression evidence |
|---|---|
| `returns_preprocess.valid_prices`, `compute_log_returns` | `test_quant_correctness.py`: extremes/flat prices retained, invalid intervals not bridged, duplicate dates rejected |
| `returns_preprocess.attach_log_returns` | `test_boundaries.py::test_attach_returns_preserves_only_valid_intervals` |
| `data/preparation.prepare_prices` | `test_data_quality.py`: interval alignment, data fingerprints/flags, invalid latest price; `test_scenario_analytics.py`: deterministic full data flow |
| `generative_model.fit_gaussian`, `sample_gaussian` | `test_methodology.py`: exact sample mean/variance, zero sigma, sampled moments; `test_boundaries.py`: invalid fitting data |
| `ewma_vol.compute_ewma_vol`, `forecast_ewma_vol` | `test_quant_correctness.py`: final observation/index; `test_boundaries.py`: flat forecast and invalid inputs |
| `ewma_vol.sample_ewma_returns` | `test_methodology.py::test_ewma_sampler_preserves_nonzero_drift_and_each_forecast_scale` |
| `gmm_model.fit_gmm` | `test_joint_models.py`: actual joint fit; `test_numerical_failures.py`: one-component analytical moments, invalid inputs, nonconvergence |
| `gmm_model.sample_gmm` | `test_joint_models.py`: iid allocation/regime retention; `test_methodology.py`: within/between covariance, applied means |
| `portfolio/paths.build_portfolio_paths` | `test_quant_correctness.py`: +5% simple return, drifting holdings; `test_numerical_failures.py`: shapes, prices, underflow, unsupported rebalancing |
| `risk/covariance.symmetric_matrix`, `psd_factor` | `test_numerical_failures.py`: matrix validation; `test_risk_statistics.py`: factor reconstruction and indefinite rejection |
| `risk/covariance.nearest_correlation` | `test_risk_statistics.py`: known 3×3 projection; `test_numerical_failures.py`: preserve perfect anticorrelation |
| `risk/covariance.estimate_covariance` | `test_risk_statistics.py`: exact sample matrix/shrinkage; `test_methodology.py`: isotropic MLE versus sample denominator |
| `risk/covariance.risk_contributions` | `test_risk_statistics.py`: exact variance, strict reconciliation, signed hedge and zero risk |
| `risk/covariance.simulate_correlated_returns` | `test_quant_correctness.py`: concurrent seed isolation; `test_methodology.py`: known marginal scales and cross covariance |
| `risk/statistics.scenario_percentiles` | `test_risk_statistics.py`: exact percentiles; `test_numerical_failures.py`: invalid population |
| `risk/statistics.return_histogram` | `test_methodology.py`: exact bin boundaries/constant population/invalid population; `test_boundaries.py`: tails included |
| `risk/statistics.tail_risk` | `test_risk_statistics.py`: fractional atoms/units; `test_methodology.py`: ties, tiny tail, gains; `test_numerical_failures.py`: invalid assumptions |
| `risk/statistics.return_statistics` | `test_risk_statistics.py`: zero excess, Sortino, 100→120→90→110 drawdown/Calmar, undefined ratios; `test_methodology.py`: pathwise annualization and loss frequency |
| `risk/scenarios/service.draw_returns`, `summarize`, `run_single`, `run_portfolio` | `test_api.py`: all supported models, chart independence, concurrent requests, drift and units; `test_scenario_analytics.py`: hand-calculable daily/held portfolios and zero-risk universe |

Coverage instrumentation includes all `src` modules and `main`, with statements
and branches and a 95% aggregate floor. It does not prove every numeric input or
all failure paths are covered. Fixed-seed moment tests use conservative tolerances
for sampling error; exact arithmetic tests use tight floating-point tolerances.
See [PHASE_2_AUDIT.md](PHASE_2_AUDIT.md) for measured coverage, untested paths and
the distinction between local checks and hosted CI evidence.

## Phase 3 fundamental observations and calculation infrastructure

Fundamental observations are source-reported measurements or estimates, not
simulation inputs or implicit forecasts. A supported metric key does not prove
its relevance to every sector or certify provider accuracy. Missing observations
remain absent. `forward_pe` requires an explicit estimate period; no forward
earnings forecast is generated by this system.

Eligibility is `reported_at <= as_of AND recorded_at <= known_at`. Timestamp
inequalities are inclusive, UTC-aware and applied **before** selecting the newest
publication per source/metric/period/basis/currency series. Constraints require
reported ≤ fetched ≤ recorded. The default knowledge cutoff is now; a historical
system-knowledge question must also supply the past `known_at`. The fiscal period
end is never substituted for publication time. See [RESEARCH.md](RESEARCH.md) for
restatement, source-identity, ingestion and retrieval semantics and failure modes.

The new quantitative functions are:

- `research.metrics.ratio(numerator, denominator)`: numerator/denominator for
  positive denominator; an undefined result with a reason for nonpositive bases.
- `research.metrics.growth(current, previous)`: (current−previous)/previous for
  positive previous; an undefined result with a reason otherwise. This is period
  growth, not CAGR or annualization.

Both accept finite Decimal values and preserve negative numerators/current values.
They perform no FX conversion, hidden window selection or binary-float conversion.
The caller must match currency, fiscal period, share basis and accounting scope;
the arithmetic uses the caller's Decimal context and its rounding precision.
Nonfinite or unrepresentable arithmetic fails explicitly. Imported observations
are limited to 30 digits including at most 10 fractional digits and stored in
PostgreSQL NUMERIC; derived in-memory arithmetic has its separately declared
Decimal-context precision.

[RESEARCH_METRICS.md](RESEARCH_METRICS.md) documents all 28 metric definitions,
input mappings, economic interpretation, accounting conventions, period choices
and weaknesses. These are source-aware catalogue definitions and two implemented
primitives, not 28 automated calculation pipelines. ROIC, FCF, enterprise value,
adjustments and forecast denominators particularly require source definitions.

`test_research_metrics.py` supplies 52 independent cases for both primitives and
the catalogue. `test_research_contracts.py` validates financial units, precision,
publication/fetch ordering and estimate labeling. `test_research_repository.py`
checks identity, temporal ranking, conflicts and atomicity; `test_research_api.py`
checks the real API/repository transaction boundary. PostgreSQL migration tests
verify exact Decimal round trips and update/delete rejection. No live provider
accuracy or real historical publication archive is certified by synthetic tests.
