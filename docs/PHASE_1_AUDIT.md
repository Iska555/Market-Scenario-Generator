# Phase 1 correctness audit

Inspected 2026-09-06 against baseline commit `b6b1c3d`. All tracked implementation,
tests, scripts, frontend components, build/deployment configuration, and existing
methodology were inspected before implementation. The owner had an uncommitted
edit in the older implementation plan; that file is preserved.

## Findings at baseline

| Classification | Original file / function | Finding |
|---|---|---|
| CONFIRMED BUG | `frontend/src/App.jsx`: `PortfolioResults`, `ExtremeScenarios` | Percentiles use 30 chart paths, omit the first day by dividing by path[0], and duplicate financial calculations in the browser. |
| CONFIRMED BUG | `frontend/src/App.jsx`: `CustomTooltip` | High/average/low are calculated from displayed paths, incorrectly suggesting population statistics. |
| CONFIRMED BUG | `backend/main.py`: both endpoints; `src/correlation.py`: `simulate_correlated_returns`; `src/ewma_vol.py`: `sample_ewma_returns` | Shared global RNG introduces concurrent request interference. |
| CONFIRMED BUG | `backend/main.py`: both endpoints | Absolute 20% log-return filters delete genuine tails. GMM output clipping and sample demeaning further alter the distribution. |
| CONFIRMED BUG | `backend/main.py`: `simulate_portfolio` | GMM branch uses Gaussian sampling with forced zero drift, incorrectly called risk neutral. |
| CONFIRMED BUG | `backend/src/gmm_model.py`: `sample_gmm` | sklearn samples grouped by component; reshaping without random label allocation creates artificial consecutive regimes. Fitting seed hardcoded independently of request. |
| CONFIRMED BUG | `backend/main.py`: Gaussian/EWMA branches | Subtracts half variance from an already fitted log mean (double drift correction). Historical mean is an undeclared forward assumption. |
| CONFIRMED BUG | `backend/src/correlation.py`: `build_portfolio_paths` | Weights log returns across assets; no explicit rebalance rule. |
| CONFIRMED BUG | `backend/main.py`: `simulate_portfolio` | Volatility omits day one; horizon=1 produces an empty difference array and nonfinite output. |
| CONFIRMED BUG | `backend/src/correlation.py`: `compute_portfolio_risk_stats` | Sharpe mixes cumulative return and annual volatility without risk-free subtraction. |
| CONFIRMED BUG | `backend/main.py`: asset contribution block; frontend allocation pie | Return ratios masquerade as allocation/risk. Absolute normalization loses signs and does not reconcile to volatility. |
| CONFIRMED BUG | `backend/src/correlation.py`: `cholesky_decomposition` | Generic eigenvalues and an arbitrary diagonal bump do not reliably repair indefinite or singular matrices. |
| CONFIRMED BUG | `backend/src/ewma_vol.py`: `compute_ewma_vol` | Missing observations can cause index length mismatch; last return is not incorporated in the next-period variance used by the endpoint. |
| CONFIRMED BUG | `backend/src/returns_preprocess.py`: `compute_log_returns` | Nonpositive/infinite prices can yield invalid returns; duplicate or unsorted dates are accepted. |
| POTENTIAL BUG | `backend/src/correlation.py`: `compute_correlation_matrix` | Matching return end dates can align different start dates across asset calendars. |
| POTENTIAL BUG | `backend/main.py`: portfolio request | Duplicate/blank tickers and negative/nonfinite weights can reach a model outside its intended scope. Per-asset caps allow excessive tensor memory. |
| DESIGN DEBT | `backend/main.py`: both routes | Financial math, data access, response serialization and scheduling mixed together; portfolio work blocks event loop. |
| DESIGN DEBT | `backend/main.py`: risk response models | VaR/CVaR lack horizon, confidence and sign metadata; no currency notional. |
| DESIGN DEBT | `backend/src/correlation.py`: sampling/path building | Python loops over path × time; covariance estimator and rebalancing are implicit. |
| DESIGN DEBT | `docs/METHODOLOGY.md`, `pyproject.toml` | Documentation claims nonexistent modules/corrections; mypy excludes the engine/routes; only three harness smoke tests; no CI. |
| DESIGN DEBT | `frontend/src/App.jsx`, README | Predictions/best/worst-case language, hardcoded path counts and calendar ambiguity; EWMA incorrectly described as future volatility clustering. |
| CORRECT AS IMPLEMENTED | `backend/src/generative_model.py`: `sample_gaussian` | Uses local default_rng internally, but must accept the shared request Generator. |
| CORRECT AS IMPLEMENTED | `backend/src/returns_preprocess.py`: return identity | Log price differences are correct for time compounding when data is valid. |
| CORRECT AS IMPLEMENTED | `backend/src/ewma_vol.py`: `forecast_ewma_vol` | Flat future variance is consistent with a pure EWMA conditional forecast. |
| CORRECT AS IMPLEMENTED | `backend/main.py`: terminal tail sample | Terminal single/portfolio tail metrics use the full population; their metadata and presentation need correction. |

## Repair outcomes

The old financial code paths have been replaced with domain functions and typed
v3 responses. RNG, simple-return aggregation, complete-population statistics,
drift calibration, GMM sampling, data validity, covariance handling and risk
contributions are repaired. The baseline's "+20%, -10%, 50/50" example returned
3.923%; the analytical correct +5% result now passes at 1e-14 tolerance.

The review also found and repaired three edge cases in the rebuild: an empirical
CVaR boundary at extremely small positive confidence; selective Calmar medians
that dropped paths without drawdown; and HTTP 500 validation responses when
nonfinite user input was echoed into strict JSON. Each has a regression test.

## Backend verification, 2026-09-07

Executed locally with Python 3.14.0, NumPy 2.3.5, pandas 2.3.3, SciPy 1.16.3,
sklearn 1.8.0, FastAPI 0.124.4 and Pydantic 2.12.5. Direct dependency versions match
the pinned requirements and `pip check` reports no broken requirements.

- `pytest`: **65 passed**, including Gaussian/GMM portfolio and
  Gaussian/GMM/EWMA single-asset concurrent byte-reproducibility.
- Ruff: **passes** across the repository's Python code.
- mypy: **passes**, 30 source files including routes, engine and tests.
- Final coverage measurement: **96%** across `src` and `main`, with 65 tests.
  Coverage is diagnostic, not proof of validity. The run emitted a Windows
  physical-core discovery warning and used logical cores; no test failed.
- No test fetches market prices; deterministic synthetic providers are used.
- Independent quantitative review found three issues, all reproduced and repaired.

Added suites: `test_quant_correctness.py`, `test_risk_statistics.py`,
`test_joint_models.py`, `test_api.py`, `test_data_quality.py`, and
`test_boundaries.py`; retained three original smoke tests. These cover analytical
returns and ratios, covariance/risk identities, preserved extreme observations,
GMM distributions, missing/calendar data, cache isolation, JSON validation,
resource caps, one-day horizons and full-population/sample independence.

## Performance evidence

`python scripts/benchmark_phase1.py`, on Windows 11/Python 3.14.0:

| Workload | Gaussian | Joint GMM |
|---|---:|---:|
| 1000 paths × 252 periods × 5 assets, 800 history rows | 0.1250 s | 0.1915 s |

Includes data preparation, model fitting, paths, statistics and response assembly.
Excludes provider network calls, HTTP serialization and browser rendering. This
is one measured run, not a production latency SLA. No absolute two-second test is
imposed on arbitrary CI machines. Oversized requests are rejected rather than
attempting the old 50-million-cell workload in a 512 MB process.

## File groups changed

- `backend/main.py`: small HTTP orchestrator, version metadata, bounded workers,
  safe validation errors.
- `backend/src/api/`, `data/`, `portfolio/`, `risk/`: typed contracts, provider and
  quality boundary, portfolio arithmetic, covariance/statistics/scenario service.
- Existing return, Gaussian, GMM, EWMA and correlation modules: corrected helpers
  or explicit compatibility imports.
- `backend/tests/`, `pyproject.toml`, `.github/workflows/ci.yml`: tests and complete
  quality gates; existing pinned dependencies and pre-commit configuration retained.
- `scripts/benchmark_phase1.py`: offline benchmark; `capture_baseline.py` now writes
  v3 output separately, preserving the archived incorrect v2 baseline.
- `AGENTS.md`, `docs/MASTER_BRIEF.md`, methodology, architecture, build plan,
  suggestions, audit and README: permanent authority and accurate documentation.
- `frontend/src/App.jsx`, `scenarioContract.js`, `components/ScenarioResults.jsx`
  and their tests: explicit v3 inputs, server-only quantitative results,
  independent tab requests, captured instrument/assumption identity, exact weight
  normalization, signed risk tables and model/data diagnostics.
- `frontend/index.html`, `src/index.css`, `package.json`: local Tailwind v4 styles,
  product title, Node test command and native Vite configuration loading.

## Remaining limitations and scope decisions

No additional later-phase product work is authorized or implemented. Daily and
buy-and-hold rebalancing are the two supported policies; other frequencies and
costs were described as eventual in the new brief and remain deferred. Likewise,
there are no additional copulas, expected-return models, persistent research data,
ledger, realized performance, attribution or publishing features.

The Phase 1 mathematical scope assumes costless, long-only assets already in the
declared valuation currency. Quote currency is not verified; no FX conversion
occurs. Calendar interval matching prevents a known error but does not replace
exchange-calendar reconciliation and may exclude systematic subsets. Flagged
extreme/repeated observations are retained, not independently certified as clean.
Provider history can change, and exact source data is not persisted.

Simulations use iid periods and fixed fitted parameters; GMM components do not
persist through time, EWMA's future variance is flat, and formal sampling/model
uncertainty bands are not implemented. Risk decomposition uses historical simple
covariance at initial weights, distinct from the simulated pooled volatility.

CI is configured for Python 3.12/3.14 and Node 22, but no GitHub-hosted run or
production deployment was triggered. The legacy 512 MB container needs measured
load/RSS validation before making capacity claims. This audit does not certify
provider accuracy, future predictive validity, or production readiness.

The new brief is followed. Clarifications to older, superseded instructions:
use arithmetic excess-return Sharpe with matching annualization; do not fetch a
hidden risk-free fallback, delete split-like moves, call arbitrary VaR regulatory,
or impose a hardware-independent benchmark. Proposals are separate in
`BRIEF_SUGGESTIONS.md`; the original master brief is preserved byte-for-byte.

## Frontend integration and final review, 2026-09-08

The frontend consumes API v3. All nine percentile rows, histogram counts, ratios,
drawdowns and tail metrics come from the server. The path chart includes time
zero and has no sample-derived statistical tooltip. Signed contributions use
historical simple-return covariance at initial weights; both that basis and its
estimator/shrinkage are visible. Returned assumptions remain separate from edited
form inputs. Historical diagnostic drift is explicitly described as calibration.

The final frontend review identified and repaired missing captured ticker labels
and a shared loading flag that allowed overlapping same-tab requests after tab
switching. Loading and error state now belong to each tab. Blank numeric fields
no longer silently become zero. Confidence and annual effective risk-free rate
inputs show their units. Independent scoped re-review found no residual P1/P2
issues; request-state isolation was reviewed statically, not through an automated
browser concurrency test.

- `npm test`: **14 passed**, including React server rendering, misleading chart
  sample independence, signed negative risk contribution, unavailable ratios and
  Calmar coverage, captured instrument identity, blank-input rejection, day zero,
  exact 3/10-asset normalization and v3 compatibility errors.
- `npm run lint`: **passes**.
- `npm run build`: **passes**. Final JavaScript bundle is 583.65 kB (177.34 kB
  gzip). Vite warns about a chunk above 500 kB and stale Browserslist data;
  these are recorded build advisories, not suppressed failures.
- Local browser check against a synthetic-price API: single Gaussian and joint
  portfolio GMM/buy-and-hold runs rendered successfully. Confirmed all percentile
  rows, tail confidence/horizon/currency, risk contribution/correlation tables,
  component probabilities/means/covariances and data fingerprints. Editing the
  form's risk-free rate left the completed result's captured rate unchanged.
  This was a local fixture check, not a live-provider or production check.
- The build uses `vite build --configLoader native` to avoid esbuild configuration
  bundling traversing inaccessible Windows parent directories. No dependency
  versions were changed. The local runtime is Node 24.12.0/Vite 7.2.7; Node 22
  remains the configured CI target.
- `git diff --check`: **passes** under the repository's existing Windows line
  ending configuration. The original user edit in the superseded plan remains
  33 added / 8 removed lines; it was not rewritten or reverted.

## Phase 1 acceptance mapping

| Brief requirement | Implemented evidence |
|---|---|
| Full-population percentiles | Server statistics and histogram; regression comparing different chart samples |
| Local RNG and concurrency | Explicit Generator through sampling; identical concurrent requests tested for every supported model |
| Preserve genuine tails | Extreme observations retained and flagged; no return/path clipping or sample demeaning |
| Genuine joint GMM | Full joint fit, independent component labels, fitted/applied diagnostics and distribution tests |
| Portfolio arithmetic | Analytical +5% weighted-simple case; daily rebalance and drifting buy-and-hold tests |
| Ratios and drawdown | Zero-excess Sharpe, explicit annual rate, downside deviation, per-path Calmar and time-zero drawdown tests |
| Volatility contribution | Signed components reconcile to annual historical portfolio volatility; zero-risk behavior tested |
| VaR/CVaR | Full-population loss quantile/fractional-tail ES with confidence, modeled horizon, currency and sign metadata |
| Covariance | Ledoit-Wolf/sample choice, shrinkage, symmetric PSD factorization and nearest-correlation tests |
| Vectorization | Tensor sampling/path arithmetic and stated offline benchmark |
| Audit and methodology | Original findings above, matching formulas/assumptions, domain boundaries, offline tests and CI configuration |

The owner review boundary remains after Phase 1. No later phase, merge, hosted CI
execution or deployment is claimed. The preserved master brief matches the
attachment's SHA256:
`5615B5E7C4747A300C7FE54DF06CD41995A2A5F04CD82A42D69E76AE4E380AEA`.
