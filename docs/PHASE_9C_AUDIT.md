# Phase 9C acceptance — historical factor regression

Date: **2026-10-11**. The owner instructed continuation after Phase 9B closeout.
Scope: [execution plan](superpowers/plans/2026-10-11-phase-9c-factors.md).
Numerical/input contract: [FACTORS.md](FACTORS.md). This new audit preserves the
master brief, all previous audits and their evidence without retrospective edits.

## Disposition

**Accepted for bounded local Phase 9C use:** supplied one-to-six-factor historical
regression against actual ledger-derived daily portfolio excess returns, centered/
scaled SVD OLS, HC3 standard errors/t-statistics, R²/adjusted R², sample/degree-of-
freedom context and daily residual evidence. Private reports share a locked Phase
8 snapshot with optional contribution/benchmark and support executable offline replay.

At least 30 fully matched funded UTC intervals are required; no incomplete-case
fit substitutes for the requested window. Alpha is a daily historical model
intercept with statistical context, never an annual forecast or skill decision.
HC3 addresses heteroskedasticity, not serial correlation. Public factor data is
not automatically fetched, converted or certified for this portfolio's calendar.
No hosted CI, deployment, broker/fund integration, Brinson or production claim.

The browser export control was exercised, but its saved file was not obtained for
independent verification. Retained reports are actual private API exports, not
browser-downloaded files. Actual browser file delivery remains unverified; working
and separately extracted source successfully verify the complete retained reports.
The corresponding Phase 9B qualification is preserved unchanged.

## Implementation and original findings

| Location / issue | Disposition and evidence |
| --- | --- |
| No historical multifactor regression in the accepted project | Added `factors/contracts.py`, `engine.py`, `routes.py`, `replay.py` and `scripts/replay_factors.py`. No dependencies, migrations or existing financial formulas changed. |
| Annual performance risk-free assumption is not a daily research risk-free series | Contract requires reviewed period-effective decimal returns and excess-market/spread factor definitions. Subtracts risk-free from portfolio once; does not subtract it again from already-excess market/spread factors. No yield/FX/calendar conversion. |
| A daily factor row can hide an unmatched or unfunded interval | Requires exact UTC closing-date observations, known publication/retrieval provenance and complete funded portfolio/risk-free/all-factor pairing. Explicit row/key/null gaps and actual initial-funding cases preserve independent portfolio results while withholding the fit. |
| Normal-equation inversion, collinearity or dropped factors can manufacture exposures | Centered/scaled SVD fit, explicit rank tolerance and 1e8 scaled condition ceiling. Constant/rank-deficient/ill-conditioned designs are undefined; no ridge, dropping, coefficient clipping or denominator floor. |
| Alpha without uncertainty would overstate meaning | Coefficient table includes HC3 SE/t-statistics, sample period/count/df, R² and limitations. High-leverage or numerical exact fits retain point estimates/residuals but withhold inference. No p-values, significance decision, annual alpha or persistent-skill claim. |
| OLS bookkeeping must be testable independently | Analytical fixtures verify closed-form one-factor HC3 and six orthogonal factors, nonzero factor means, negative coefficients and y=fitted+residual/orthogonality identities. Constant response, zero denominators, overflow and exact/leverage diagnostics remain typed. |
| Private error responses lost dependency-set no-store headers | API tests exposed this on factor validation errors. An initial custom route-wrapper attempt did not cover the dependency scope correctly. Replaced it with `main.factor_private_cache`, scoped to factor responses; final tests verify no-store and sanitized input errors. Existing private-route semantics were not retroactively relabelled. |
| Concurrent report requests could use different snapshots | Factor route obtains the existing locked performance report and computes optional contribution/comparison before regression. Actual PostgreSQL tests prove all migrated tables unchanged, repeatability, competing 55P03 row-lock timeout, later write/stale rejection and updated fit. |
| New client evidence/results must clear together | Optional fifth Performance transport supplies all selected reports in one request. Controller generation guards and edit/import/template/account/lock/navigation/refresh clearing include factor state. Keys never enter controller snapshots/exports. |
| Two-decimal R² presentation made 0.9982 look perfect | Final factor statistics show four-decimal R²/adjusted R². Shared formatter's other defaults remain intact; full client tests/lint/build rerun after this presentation refinement. |
| Source/runtime compatibility matters for numerical replay | Full factor report verifies embedded reports, factor evidence hash/settings and every regenerated output. Three actual API exports pass against working and separately extracted 86-file accepted source. Old archives/hashes remain untouched. Exact numerical replay is local-runtime evidence, not cross-platform attestation. |

Early analytical development failed five attempted mutations of frozen Metric
objects, followed by one malformed missing-metric fixture; tests were corrected
to create valid replacements with explicit reasons. An inline Windows Python edit
command also failed quoting before modifying a file; a saved script/patch replaced
it. Style/typing issues were repaired before final gates. A scoped API development
invocation stalled and was stopped; no passing claim is based on it. A premature
full-run invocation was stopped while the private-error/typing issue was still
under repair. Final evidence below comes from the subsequent complete corrected run.

## Fresh verification

`scripts/verify.ps1 -EvidenceDirectory .verification/phase9c/full`, using disposable
loopback PostgreSQL port 55439 and bounded BLAS threads. Runtime: Windows 11,
Python **3.12.14**, PostgreSQL **17.11**, Node **24.18.0**, npm **11.16.0**, Vite **7.3.7**.
Dependencies and the 95% coverage requirement remain unchanged.

| Gate | Final result |
| --- | --- |
| Full backend including actual PostgreSQL | **679 passed, zero skipped**, 114.62s |
| Combined statement/branch coverage | **97.87%** |
| New factor tests | **49 analytical**, **3 private API**, **2 actual PostgreSQL** cases |
| Ruff / format / mypy | Passed; **140 files** formatted, **134 source files** typed |
| Configured hooks | Full runner passed; final staged result retained separately |
| Full frontend | **141 passed**, zero failed/skipped; eight new factor cases |
| Final client after R² precision refinement | **141 passed**, ESLint and production build passed |
| Existing scenario workload observation | Gaussian **0.2307s**, GMM **0.4296s**, 1000 paths × 252 periods × 5 assets; excludes HTTP/network/client rendering |
| Offline verification | Complete/missing/corrected API exports passed against working and independently extracted accepted source |
| Historical preservation | **108/108** task-entry full-file/original-suggestions-prefix checks passed |

Inherited Starlette deprecation and Vite bundle-size warnings remain in the logs.
Timings are local observations, not comparative or production capacity claims.

## Synthetic browser/correction acceptance

Disposable GBP account: deposit1000, purchase one equity100 (remaining cash900),
and fee10 on the final day. Thirty-two supplied interval returns were constructed
from risk-free0.0001, daily intercept0.002, market coefficient1.5, market cycles
−0.02/−0.01/0.01/0.02, and orthogonal residual cycles0.001/−0.001/−0.001/0.001.
Prices are derived to ten decimals from that synthetic NAV path; none is market data.

The auxiliary benchmark has quantized nearly constant daily returns, producing a
very large benchmark beta under the existing no-denominator-floor method. This
artificial fixture sensitivity is distinct from the designed factor coefficient
1.5. Existing benchmark formulas and historical acceptance records were preserved.

- Version3 before correction: TWR **4.9883068%**, contribution reconciled, factor
  **32/32** and df30; displayed alpha **0.17pp**, SE **0.03pp**, t **5.01**, market
  coefficient **1.48**. The fee legitimately changes the observed regression.
- API missing-row version3 export and browser missing-row version4 check: **31/32**
  pairing; all fit outputs withheld with reasons. Independent performance,
  contribution and benchmark remain available. No reduced sample is fitted.
- Append-only fee reversal produces version4. Stale browser request is rejected
  and old results clear. Reload clears dates, options and all three evidence inputs.
- Corrected version4: TWR **5.9883068%**, daily alpha **0.20pp** (0.002), market
  coefficient **1.50**, alpha HC3 SE **0.02pp**, t **10.60**, market t **124.22**;
  R²/adjusted R² display **0.9982**, daily residual volatility **0.10%**, condition1.
  These are deliberately constructed analytical observations, not evidence of skill.
- Identity/evidence and fitted/residual interval sections expand. Desktop and
  390×844 light/dark views inspected; DOM page width375 fits viewport390 with
  bounded scrolling. No captured console errors. Lock clears private reports,
  refresh returns locked Overview. Theme restored, viewport reset, test tab closed.

Evidence: [verification index](verification/phase9c-2026-10-11/README.md). Only the
named synthetic schema was dropped. No test/Phase 9C schemas or acceptance
listeners on 8000/5173/55439 remained after service shutdown.

## Next boundary

The regression infrastructure is accepted locally; usable real-account factor
evidence still requires deliberate calendar/currency reconciliation and source
review. Prioritize versioned portfolio benchmark settings and that data-readiness
work, then decide HAC/rolling analytics with their own statistical acceptance.
Brinson needs historical sector/region classifications and benchmark weights;
the current registry does not establish that evidence. Defer it rather than
inventing constituents. The approved ledger-to-construction, fund/broker and
operational integration priorities remain separate. Broader Phase 9 and public
track-record delivery are not declared complete by this substage.
