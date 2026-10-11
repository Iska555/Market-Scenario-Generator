# Quantitative methodology — Phases 1–6

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
claim. Costs are zero. The backend's legacy default is daily rebalancing;
current frontend portfolio requests explicitly default to buy-and-hold.
Daily rebalancing remains selectable as `rebalance`. Monthly, quarterly, annual, threshold rebalancing and
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

## Phase 4: owner-authored thesis assumptions

Thesis targets, required returns and review return assumptions are declared
judgments. This phase adds no financial formula or expected-return estimator.
The horizon is explicitly in months. Monetary values are positive per-share
amounts in the declared valuation currency; a low/high pair is an owner value
range without implied confidence or probability. Review prices are manually
entered and have no automatic market-data freshness guarantee or FX conversion.

Required and review expected returns are optional annual effective decimal
fractions (`0.08` represents 8% per year), strictly greater than −1. They are
stored as Decimal values without binary-float conversion, hidden compounding,
target-price arithmetic or reuse of historical sample means. The backend permits
10 fractional digits, 30 total digits for prices and 20 for rates. Validation
rejects nonfinite, inconsistent, out-of-range or excessive-precision inputs.

The authoring timestamp is server-recorded UTC. An as-of read filters complete
versions by that inclusive timestamp before selecting the highest revision. It
does not certify when underlying source information became available. Revision
and per-thesis review times are monotonic even if the server clock moves backward,
by advancing the prior applicable timestamp by a microsecond when needed.
Consequently these are application-ordering times, not independent time attestations.

Behavioral prompts and explicit manual decisions support a repeatable review
process. Saving a review does not change thesis status, create a trade, or assess
whether its return assumption is sufficient. [THESIS.md](THESIS.md) documents the
schema and remaining limits; [PHASE_4_AUDIT.md](PHASE_4_AUDIT.md) records verification.

## Phase 5 return contract and numerical conventions

**Expected-return estimates are assumption-dependent estimates, not predictions.**
`valuation/contracts.py` separates `ResearchAssumptionSet`, `ValuationModelResult`,
`CapmEstimate`, `SecurityScenario`, `HistoricalDiagnostic` and `ExpectedReturnView`.
Only an explicit `user_specified` request produces an investor view. Running CAPM,
fundamental valuation or probability weighting does not adopt a construction input.
To adopt a result, the owner must deliberately supply a user view with rationale
and an optional reference. There is no optimizer, adoption automation or trading
decision. Legacy Phase 4 review percentages are never imported automatically.

Every result carries a security ID, valuation date, horizon H in calendar years
(positive, at most 100), price/total basis, nominal/real basis, local/base currency,
valuation/local currency codes, declared valuation calendar/cutoff description,
publication `as_of`, knowledge `known_at` and optional evidence/revision IDs.
Currency codes are three uppercase letters. A local return uses the local
currency. The API checks that local currency matches the security master.
User views may express any of these declared bases; fundamental models support
nominal returns, and statistical models support local nominal returns. Unsupported
conversions fail rather than assume inflation or an FX series.

Rates are dimensionless fractions (0.08 = 8%); prices, fundamentals and dividends
are local-currency amounts per share. Source research decimals remain exact in
evidence snapshots. User return inputs remain Decimal values (30 digits, up to 15
fractional places), including their supplied annual/cumulative choice and decimal
spelling, in the resolved request. Calculation outputs use IEEE double precision;
tests reconcile at stated tolerances and the UI rounds return presentation to one
decimal percentage point. The UI does not compute financial results.

For annualized equivalent a and cumulative simple return c:

```text
c = (1 + a)^H - 1
a = (1 + c)^(1/H) - 1
```

`valuation/arithmetic.py` uses log1p/expm1 for conversions. −100% is explicitly
supported for user/CAPM return wealth, and rates below −100% are rejected or
reported undefined when CAPM implies one. Both supplied rates must reconcile
(relative tolerance 1e-9, absolute tolerance 1e-12). Numerical overflow,
nonfinite values, underflow of positive valuation quantities and positive wealth
that would round to a complete loss fail explicitly; outputs are never clipped.

The annualized equivalent of expected horizon wealth is not E[realized CAGR].
CAGR is the realized compound rate of an actual wealth ratio. Arithmetic expected
simple return is E[R]; geometric/log growth depends on E[log(1+R)]. Log drift is
the mean log increment, not arithmetic expected return. Zero Gaussian log drift
has E[R] = exp(variance/2) − 1, generally positive, and is not risk neutrality.
Price returns exclude distributions; total-return scenarios include the declared
cash treatment below. Sharpe, tail and risk calculations from earlier phases
remain unchanged and keep their own explicit period/path conventions.

## Historical expected-return diagnostic

**Formula:** point estimate = A × mean(r); IID standard error = A × s / sqrt(n),
where r is supplied arithmetic simple period returns, n is observation count,
s is sample standard deviation (ddof=1), and A is periods/year. The standard error
measures uncertainty of the annualized arithmetic mean, not annual return
volatility. n=1 has a defined mean and undefined SE (`insufficient_observations`).
Constant samples have zero estimated SE; this is not proof of zero future risk.

The API always labels this **Historical estimate — not a forward forecast**.
It returns actual start/end dates, n, frequency, A, estimator and uncertainty.
No forward cumulative return or realized CAGR is calculated. The context horizon
is retained only to make the surrounding research question explicit. This
diagnostic cannot produce an investor view automatically or act as a default.

Each supplied sample includes source, retrieval time, adjustment policy and an
explicit assertion that security/benchmark intervals and valuation cutoffs match.
Rows contain interval start/end dates and simple returns (both series in CAPM).
Dates must be sorted, unique and nonoverlapping. A is 12 monthly, 52 weekly, 1
annual, or an explicit 200–366 for daily observations. Supported interval lengths
are daily 1–7, weekly 5–9, monthly 25–35, annual 350–380 calendar days. These are
input sanity bounds, not an exchange-calendar reconciliation engine. Gaps between
sample intervals are allowed; unusually long closures/irregular intervals require
preparation outside this engine and cannot silently receive standard annualization.

The sample may not end after valuation/publication cutoff or be retrieved before
its final interval or after knowledge cutoff. Samples are manually supplied;
source attribution, corporate-action policy and interval/currency alignment are
caller assertions, not independently verified provider contracts. No live provider
is called. The actual sample is returned in the manifest for owner-controlled
replay. Serial dependence, heteroskedasticity, selection bias and regime shifts
invalidate an IID interpretation; no HAC estimator or calibrated confidence
interval is claimed. Implementation: `views/expected_return.py:historical`.

## CAPM model estimate

**Formula (one-year arithmetic expected simple total return):**

```text
E[R_i] = rf + beta × ERP
rf_period = (1 + rf)^(1/A) - 1
x_t = benchmark_simple_return_t - rf_period
y_t = security_simple_return_t - rf_period
beta = sum((x - mean(x)) × (y - mean(y))) / sum((x - mean(x))²)
intercept = mean(y) - beta × mean(x)
beta_SE = sqrt(SSE / (n - 2) / Sxx)
R² = 1 - SSE / Syy
```

rf is explicitly **annual effective** and ERP is a user-supplied one-year
arithmetic equity risk premium. There is no hidden ERP default or macro fetch.
The request records benchmark, assumption source, return sample, window, frequency,
adjustments and cutoffs. Regression is OLS with intercept on aligned arithmetic
excess period returns; a constant period rf leaves the slope unchanged. The
intercept is a diagnostic and is not added as forecast alpha. Both series must
represent total returns in the same local currency and cutoff convention.

At least three observations are required for regression diagnostics. Insufficient
data and effectively zero benchmark variance return null metrics with reasons.
Variance is treated as numerically zero when its centered sum of squares is no
greater than machine epsilon × n × max(abs(series))². Zero security variance has
undefined R² even when beta is defined. The API returns beta SE, R², intercept,
n and estimator wording; no arbitrary zero substitutes for undefined values.
An implied annual return below −100% yields no ReturnPair and an explicit reason.

For a multi-year horizon the caller must explicitly choose
`horizon_assumption="iid_annual_gross_mean"`. The engine uses
`E[wealth_H]/wealth_0 = (1 + rf + beta × ERP)^H`, extending the annual gross-mean
assumption to fractional H as a compound interpolation. This is not a calibrated
multi-year stochastic model or expected realized CAGR. Static beta, a constant
rf/ERP, the CAPM restrictions and IID OLS errors are assumptions. Beta estimation
SE is reported; ERP/rf uncertainty and parameter propagation are not implemented.
Known tests: rf=3%, beta=1.2, ERP=5% gives 9%; beta=0 gives rf; negative beta remains
negative. Implementation: `views/expected_return.py:regress`, `capm`.

## Fundamental terminal-wealth valuation

The initial model uses a positive EPS or FCF-per-share anchor F0, growth g > −1,
positive terminal multiple MH, current local price P0, annual cash dividend D ≥ 0,
horizon H and explicit spot/terminal FX X0, XH (valuation currency per local
currency). Price time must be on valuation date and available by both cutoffs.
Same-currency FX must equal one. Cross-currency requests must explicitly supply
both rates, even if parity is intended. No currency conversion is inferred.

```text
FH = F0 × (1 + g)^H
PH = FH × MH
C = D × H for total-return basis; C = 0 for price-return basis
WH = (PH + C) × XH
W0 = P0 × X0
c = WH / W0 - 1
a = (1 + c)^(1/H) - 1
```

D is a fixed annual local cash amount accrued pro rata over fractional years,
held without reinvestment or interest, and converted together with terminal
proceeds at XH. This is an explicit terminal-wealth scenario, not dated dividend
cash-flow IRR. P0 and F0 must be on a consistent per-share/split basis asserted by
the owner. Dividends are separate from growth; **buybacks are already included in
per-share growth** and no additional buyback yield is added. Revenue, margins and
net debt are not modelled separately. Negative/zero EPS or FCF cannot be valued
with this positive-multiple model; select another future model rather than force
these inputs into it. g/MH/D are owner assumptions, not historical estimates.

The exact exposed decomposition is multiplicative:

```text
1 + c = growth_factor × multiple_factor × dividend_wealth_factor × fx_factor
growth_factor = (1 + g)^H
multiple_factor = MH / (P0/F0)
dividend_wealth_factor = 1 + C/PH
fx_factor = XH/X0
```

The commonly used growth + yield + multiple-change + FX decomposition is only an
investment approximation, not this model's identity. No additive percentage-point
contributions are fabricated. Costs, taxes, dilution beyond the per-share input,
dividend reinvestment, inflation and DCF are unsupported. User-supplied terminal
FX is a deterministic sensitivity; it does not implement historical FX risk,
multi-currency portfolio reconciliation or corporate-action accounting.
Implementation: `valuation/models.py:fundamental`, `terminal_fundamental`, `dividends`.

## Bear/base/bull and probability-weighted scenario expectation

Exactly one bear, base and bull label is required; the labels do not guarantee
ordered outcomes. Each retains its own assumption set and valuation output. All
share context, metric, current F0/P0, spot FX and price timestamp. They can exist
without probabilities: `probability_weighted_return=null` then means no
distribution was supplied. No probability is invented.

When probabilities p_s are explicitly supplied, require every probability, each
in [0,1], with sum one (floating tolerance approximately 1e-9), a source statement
and `user_assumption` or `model_assumption` type. There is no silent normalization.
Compute c_weighted = sum(p_s × (1 + c_s)) − 1 and then annualize that horizon
wealth return. Do **not** average annualized scenario rates; the two operations
do not generally commute. These probabilities express assumptions, not statistical
calibration. No tail estimator, Monte Carlo paths or parameter uncertainty is
introduced here. Implementation: `valuation/models.py:scenario_set`.

## Reverse valuation

Hold every forward assumption fixed except MH. Given required annualized a_req,
solve analytically:

```text
required_local_price = P0 × X0 × (1 + a_req)^H / XH - C
required_MH = required_local_price / (F0 × (1 + g)^H)
```

The response names the solved field, preserves the submitted assumptions and
explicitly states that their original terminal_multiple is ignored. Nonpositive
required terminal price has no solution in this positive-multiple model and
returns `{value:null, reason:"nonpositive_required_terminal_price"}`. A multiple
underflowing to zero returns `numerical_underflow`; overflow fails. A forward
round trip recovers the original multiple. This asks what terminal multiple
would satisfy the owner's required return at today's price; it does not establish
fair value or recommend an investment. Implementation: `valuation/models.py:reverse`.

## Evidence, reproducibility and Phase 5 boundaries

`valuation/service.py` resolves explicit observation IDs and an optional thesis
revision for the selected security. Require `reported_at <= as_of` and
`recorded_at <= known_at` for facts, and revision creation time <= both cutoffs
for the thesis. Monetary facts must match local currency. IDs can deliberately
refer to an older eligible observation: this is explicit evidence selection, not
automatic latest-restatement selection. Frontend browsing uses Phase 3's latest
eligible fact query. Linkage does not claim that model inputs were extracted from
the attached facts; all assumptions remain separately supplied by the owner.

`POST /api/research/valuation/evaluate` dispatches six typed model inputs behind
the existing owner-key/database dependencies. It returns `result` plus `manifest`
and `Cache-Control: no-store`; existing API v3 simulation behavior is unchanged.
The manifest includes resolved inputs, model/methodology version (`phase5.1`),
valuation/evidence/sample metadata, exact research and thesis snapshots, input and
evidence SHA-256, a hash over backend Python source content, git SHA/dirty status
when available, optional BUILD_ID, runtime/library versions and generated time.
No RNG is used (`random_seed=null`). Non-git deployments explicitly report missing
git identity; dirty source hashes distinguish local changes from a clean commit.

Replaying resolved inputs reproduces the result in a matching environment with
eligible database records. Returned snapshots support later examination but are
not accepted as database truth by the API. Mutable security-master labels/currency
may change or prevent a future API replay; original manifest snapshots retain
their original values. Hashes identify data and do not preserve it. There is no
new persistence table, provider data retention process, archive, or save/export
service. The owner controls retention of responses subject to source licensing.
Same-run timestamp/manifests need not be byte-identical across executions.

Uncertainty records distinguish parameter estimation, model specification and
sampling. User ranges are declared annualized ranges without inferred confidence;
fundamental/reverse sensitivity is conditional, and statistical SEs use the stated
IID assumptions. No Monte Carlo sampling occurs in this engine, and extra Risk Lab
paths would not remove parameter or model uncertainty. Phase 6 construction,
ledger/accounting, attribution, publishing and Black-Litterman remain unsupported.
# Phase 6 — supplied-data construction and stress

Construction uses owner-declared fully invested, long-only security weights, in
one local/valuation currency. These are hypothetical allocations, not holdings
derived from transactions. All financial calculations run in backend domain
functions. The private APIs return complete resolved inputs and registry/evidence
snapshots with code, input and evidence hashes and library versions. Saving the
response is necessary for replay; a hash alone does not archive data.

## Joint data and expected-return conventions

Every supplied row contains identical start/end economic intervals across the
ordered security UUIDs, with explicit calendar/cutoff alignment, total-return
adjustment policy, frequency, periods per year, source and retrieval time. The
server rejects dimension/order mismatches, invalid frequencies, overlapping
intervals and data unavailable under the supplied knowledge cutoff. It cannot
independently certify the owner's declared corporate-action or calendar alignment.
There are no provider calls or automatic history archives in these endpoints.

An adopted return view must explicitly specify one-year nominal total simple
return, local currency, matching valuation date/calendar and eligible evidence
cutoffs. Model estimates are never silently adopted. For complete views mu,
portfolio expected return is sum(w_i * mu_i), and the expected Sharpe comparison
is (sum(w_i * mu_i) - annual_effective_risk_free_rate) / annualized_volatility.
These are conditional one-year assumptions; geometric multi-year annualized rates
are not interchangeable with arithmetic one-year means. Missing views produce
typed undefined aggregate returns/Sharpe; known asset contributions remain visible.

## Covariance and contributions

Sample covariance uses n-1 degrees of freedom; Ledoit-Wolf uses the library's
shrunk covariance estimator. Annual covariance Sigma is period covariance times
declared periods per year, assuming IID covariance scaling. Correlation is
Sigma_ij / sqrt(Sigma_ii * Sigma_jj), undefined when either variance is zero.
This is current-weight historical covariance risk, separate from stress population
risk and future realized portfolio risk. Parameter/model uncertainty is not propagated.

Portfolio volatility sigma = sqrt(w' Sigma w). Marginal contribution is
(Sigma w)_i / sigma; component contribution is w_i times marginal contribution;
percentage contribution is component / sigma. Components sum to sigma and
percentages sum to one when sigma is positive. Negative contributions remain
signed. Zero sigma gives zero components and undefined marginal/percentage ratios.
Weight concentration is sum(w_i^2), with effective positions its reciprocal.
Risk concentration is sum((abs(component_i) / sum(abs(component)))^2), explicitly
an absolute-contribution HHI; it is undefined when all components are zero.

## Allocation alternatives and numerical limits

Current and equal weights are reference allocations. Any violation of proposed
common minimum/maximum position weights is shown rather than silently repaired.
Optimized alternatives require unit sum and the declared position bounds.

Minimum variance minimizes w' Sigma w using convex SLSQP with analytical gradients.
A bounded-simplex first-order gap checks optimality, in addition to solver status
and feasibility. Zero covariance or a unique feasible portfolio is handled
analytically; uniqueness is not claimed for singular objectives.

Maximum Sharpe requires all investor views, positive-definite covariance and a
feasible positive expected excess return. It solves the convex transformation
minimize y' Sigma y subject to excess' y = 1 and
lower * sum(y) <= y_i <= upper * sum(y), then normalizes y to unit sum.
Positive rescaling improves conditioning without changing the solution. Solver,
feasibility and first-order checks must pass. Singular/ill-conditioned covariance,
nonpositive feasible excess return or numerical failure produces an explicit
unavailable comparison. Maximum Sharpe is highly sensitive to uncertain return
assumptions; it is presented beside minimum variance and risk parity.

Equal risk contribution solves the positive convex risk-budget objective
0.5 * x' Sigma x - sum(log(x_i)) / number_of_assets, then normalizes x.
It requires positive-definite covariance, successful numerical convergence and
equal risk percentages within 1e-6 absolute tolerance. If this solution violates
position bounds it is unavailable; a constrained approximation is not labeled
equal risk contribution. Position feasibility tolerance is 1e-8; only numerical
roundoff outside [0, 1] is cleaned in optimized weights.

Cash, leverage, shorting, sector/beta caps, factor mapping, Black-Litterman and
benchmark-relative optimization are unsupported. Unsupported request fields are
rejected. No allocation is an order or an automatic investment decision.

## Historical replay, bootstrap and security shocks

Replay applies the complete ordered supplied joint history to declared weights.
Moving-block bootstrap draws uniform overlapping, non-circular joint blocks;
within-block sequence and cross-security rows are retained, and the final block
is truncated to the explicit horizon. Seed, block length, path count, horizon,
confidence and unchanged empirical-mean policy are required. The sample's returns
are resampled without recentering; non-circular blocks weight interior rows more
heavily than endpoints, and sampled means need not equal the source sample mean.
This is not an investor expected-return view. The tensor
is limited to two million cells. Model uncertainty and uncertainty about the
historical data-generating process are not eliminated by more paths.

Both history methods use the existing exact simple-return portfolio path engine,
with costless per-observation rebalancing or buy-and-hold. They reject complete-loss
history observations explicitly because the inherited logarithmic path/statistics
domain excludes them; observations are never silently dropped. Deterministic
shocks accept complete loss and compute a single terminal weighted security shock,
with explicit horizon label and rationale. No arbitrary oil/rate/FX transmission
coefficients are invented. One replay or shock has no empirical tail distribution.

Stress weights are reconciled to unit sum only within the contract's accepted
1e-10 roundoff tolerance. Deterministic terminal wealth sums nonnegative gross
security wealth before subtracting one for the return; this avoids tiny negative
wealth caused by cancellation at complete loss. Calmar defined/total path counts
and bootstrap effective tail mass `(1-confidence)*path_count` are exposed.

Stress statistics use all paths; the chart sample is only the first at most 30.
Pooled periodic volatility and excess-return Sharpe/Sortino use the supplied
periods-per-year assumption and annual-effective risk-free conversion. Calmar is
the median of path annual growth divided by path maximum drawdown, undefined if
any path has zero drawdown. Bootstrap terminal losses use loss-positive simple
returns, linear empirical VaR and fractional-boundary expected shortfall. Negative
losses are valid gains. Percentiles are not worst/best cases or loss bounds.
All outputs identify the actual observation-period horizon rather than calling
monthly or weekly intervals days. Fees, taxes, costs and realized accounting are
outside these conditional scenarios.


# Phase 7 ledger and supplied-mark valuation — 2026-09-12

The ledger records economic events rather than simulated outcomes. Its formulas,
trade-date cash convention, positive debit/credit fields, moving-average local
cost, fee treatment, FX direction, cancellation/knowledge semantics, decimal
rounding and missing-data rules are documented in [ACCOUNTING.md](ACCOUNTING.md).

The fundamental identities are cash = inflows − outflows per currency, quantity
= active buys − active sells per security, and complete NAV = all local position
values and cash translated with supplied base-units/local-unit rates. Buy fees
enter basis; sell fees reduce cash proceeds. Full closure removes all remaining
basis. Partial sales allocate average cost; this is not tax-lot accounting.

Missing required price/FX inputs make complete NAV and all weights undefined.
Local unrealized P&L equals local market value minus local basis. Translating it
at current supplied FX excludes historical FX gains/losses and is labeled as such.
Supplied prices use their actual dates/sources; no stale-price, corporate-action
or broker-settlement reconciliation is silently certified. No TWR, XIRR, realized
performance, benchmark attribution or automatic order follows from these values.

## Risk Lab input conventions — 2026-09-13 UX clarification

The Risk Lab names `zero_log_drift` **No directional return assumption** and
`historical_diagnostic` **Historical average — diagnostic only**. These are the
two currently implemented scenario drift choices, not investor return views.
Zero applied mean log return does not imply zero expected simple return or a
risk-neutral model. The historical mean is diagnostic evidence, not an implicit
forecast. A thesis-conditioned expected return requires a separate declared
view and is not a selectable Risk Lab drift source.

The estimation-window shortcuts send exactly 3 (Recent), 5 (Medium), or 10
(Long) years; Custom sends the entered 1–10 year value. A shorter window can
respond to recent changes while using fewer observations; a longer window can
stabilize an estimate while mixing older conditions. The response, rather than
the shortcut label, reports the actual estimation dates and valid intervals.

New frontend portfolio requests explicitly select `buy_and_hold` by default,
so weights drift with simulated returns. The backend's legacy default is
unchanged. A user may select `daily`, which resets target weights each modeled
period without transaction costs. Ledoit-Wolf remains the portfolio historical
covariance estimator default. The single-asset form omits covariance and
rebalancing selectors because those choices are not meaningful controls there;
the existing v3 request fields remain explicit for compatibility. Valuation
currency labels outputs and does not perform FX conversion. Path count, seed,
periods per year, confidence and method-specific numeric parameters remain
editable under Advanced settings. The two-million-cell request limit is
unchanged and blocks oversized runs with an explanatory message.

Historical replay and block-bootstrap forms also now explicitly default to
`buy_and_hold`; `per_observation` rebalancing remains selectable. These are
frontend default changes only. All resolved choices still enter their request
and replay manifest. Ledoit-Wolf estimates how assets move together while
shrinking noisy historical covariance toward a more stable structure; it does
not remove model or parameter uncertainty. For a single asset the shared
infrastructure estimates variance; no cross-asset selector is presented.

## Phase 8 realized performance — 2026-09-15 authorization

The separately implemented [performance methodology](PERFORMANCE.md) specifies
daily flow-neutral unitization, actual-day/365 XIRR, geometric calendar links,
realized sample ratios/moments/tails, valuation/FX evidence and typed undefined
states. Its fixed UTC calendar / 365-observation convention applies only to this
realized-performance domain. Existing 252-period Risk Lab conventions and
scenario-distribution calculations are unchanged. No historical sample performance
is promoted into an investor expected-return view.

### Phase 8 closeout identity and verification — 2026-10-09

No financial formula changes in this closeout. `performance.identity.digest`
hashes canonical JSON with non-finite values forbidden. `source_sha256` hashes
the ordered relative paths and actual bytes of every backend domain Python file
and main.py. This identifies dirty/untracked code as well as committed source;
configured Git/build identity remains additional metadata.

`performance.replay.verify_replay` requires matching source and Python/library
versions, validates retained input/ledger hashes, identities and declared
methodology/conventions, recalculates
from the visible immutable records and compares every financial output. Full
ledger version and knowledge-visible version are checked separately. This is
consistency evidence, not independent data attestation. Missing source identity
on a legacy report requires explicit regeneration for exact verification.

| Functions / transport | Analytical/regression evidence |
|---|---|
| `performance.engine.build_report`; `identity.digest`, `source_sha256`; `replay.verify_replay` | `test_performance_replay.py`: download roundtrip, modified inputs/records/results/source/runtime/identities/versions/methodology/conventions, legacy reports and later unknown reversals |
| `performance.routes.report`; coherent ledger snapshot | `test_performance_postgres.py`: unchanged contents across every migrated table, repeatability, competing row-lock timeout, later write, stale rejection and refreshed fee/NAV/TWR identities |

The complete numerical specification remains in [PERFORMANCE.md](PERFORMANCE.md),
and fresh acceptance evidence is in [PHASE_8_AUDIT.md](PHASE_8_AUDIT.md).

## Phase 9A reconciled position contribution — 2026-10-09 authorization

[ATTRIBUTION.md](ATTRIBUTION.md) specifies the implemented endpoint P&L identities,
input/output units, forward unit-wealth linking, price/FX interaction allocation,
flow ordering, corrections, assumptions, undefined cases and exact reconciliation
tolerance. It maps the pure backend functions and private transport to analytical,
actual PostgreSQL and frontend evidence. This is a separate accounting explanation
of Phase 8 TWR, not a security return, risk contribution, benchmark attribution,
factor explanation or investor return view.

Phase 8 source hashing includes all backend source, so Phase 9A appropriately changes
that identity. Preserve old reports and their compatible checkpoint/environment;
do not rewrite source identities retrospectively. Current acceptance and limitations
are recorded in the new [PHASE_9A_AUDIT.md](PHASE_9A_AUDIT.md).


## Phase 9B benchmark and realized active risk — 2026-10-11 continuation

[BENCHMARK.md](BENCHMARK.md) specifies same-currency versioned total-return
evidence, aligned funded intervals, arithmetic active versus relative wealth
returns, cumulative comparison, centered sample covariance/variance, realized
tracking error, information ratio, beta/correlation and 365 annualization.
It declares units, estimator assumptions, sample/coverage counts, zero-variance/
zero-wealth/overflow outcomes, short-sample uncertainty and replay identity.
These are descriptive historical sample estimates, not forecasts, factor alpha
or ex-ante tracking-risk contributions. Price-only, wrong-currency and incompatible
calendar series are rejected rather than silently transformed. See the new
[Phase 9B audit](PHASE_9B_AUDIT.md) for verification and remaining limitations.
