# Phase 9B acceptance — benchmark and realized active risk

Date: **2026-10-11**. The owner instructed continuation of the approved sequence
after Phase 9A acceptance. This is a new record; the master brief and historical
audits/evidence retain their original content and findings. Execution plan:
[Phase 9B](superpowers/plans/2026-10-11-phase-9b-benchmark.md). Numerical specification:
[BENCHMARK.md](BENCHMARK.md).

## Disposition

**Accepted for bounded local Phase 9B use:** explicit benchmark selection for the
chosen account/report, reviewed same-currency gross/net total-return levels,
aligned daily/cumulative comparisons, sample tracking error, information ratio,
beta/correlation, coherent optional position contribution and offline replay.
Actual disposable PostgreSQL and synthetic browser workflows were exercised.
Selection is retained in the report, not as a persistent portfolio default.

The browser download control was activated, but its downloaded file was not
obtained for independent verification in this run. The three retained exports
come from the actual private API and replay successfully; they are not described
as browser-downloaded files. End-to-end browser file delivery remains unverified.
This qualification does not affect the verified calculation, API exports or
offline replay. No hosted CI, deployment, broker reconciliation, licensed provider
archive, benchmark suitability certification or production readiness is claimed.
Factor regression/alpha, rolling analytics, Brinson and publication remain later.

## Implementation and findings

| Location / issue | Disposition and evidence |
| --- | --- |
| Phase 9A explains TWR without an explicit market comparator | New `benchmark/contracts.py`, `engine.py`, `routes.py`, `replay.py` and `scripts/replay_comparison.py`; main.py mounts the private route. No migrations, dependencies or prior financial formulas changed. |
| A price-only or mismatched-currency/calendar series can misstate active results | Requires total-return basis, account currency, UTC daily calendar/365, hedging declaration, effective revision dates and ordered observation/publication/retrieval provenance. Wrong currency, price-only/252 basis and future evidence are rejected. No automatic FX or index choice. |
| Cumulative differences and daily active returns have different meanings | Reports TWR minus benchmark in percentage points and compounded relative wealth separately. Daily arithmetic differences are not compounded into the cumulative difference. Methodology states input/output units and exact estimators. |
| Reduced samples can hide missing-data bias | Full-window statistics require every expected paired interval and at least two observations. Null/missing/stale levels remain gaps; available independent portfolio or benchmark output survives. No silent forward-fill or complete-case window substitution. |
| Initial funding during a day can create unequal investment intervals | During development, the new first-funding regression showed Phase 8's valid post-funding zero return could appear paired with a full benchmark day. `build_comparison` now withholds a portfolio interval if opening units are absent/nonpositive, and withholds cumulative comparisons when the opening portfolio is unfunded. Embedded Phase 8 outputs are unchanged. The funded-window regression and replay pass. |
| Zero or very small variance must not manufacture a ratio | Realized sample TE may validly equal zero; IR is undefined at zero TE, beta at zero benchmark variance, and correlation at either zero variance. Negative beta/correlation retain their signs. No epsilon denominator floor or sign clamp. Zero wealth/recovery and overflow have explicit nullable outcomes. |
| Two reports could read different ledger versions | One request uses the existing locked Phase 8 snapshot, optionally computes Phase 9A contribution, then compares the benchmark before releasing the lock. Actual PostgreSQL tests prove competing row-lock timeout, all-table immutability, repeated output, stale rejection and updated fees. |
| Short samples can generate spectacular annualized numbers | The browser fixture has only two intervals. Visible sample counts, a prominent short-sample warning and declared 365 scaling distinguish descriptive estimates from forecasts or evidence of skill. No alpha or ex-ante risk model is implied. |
| Private/stale client state must clear coherently | Optional fourth Performance transport supplies all three reports in one response. Edits, imports, templates, account selection/reload, lock/navigation/refresh and generation guards cover comparison state. Frontend tests verify late import/result rejection and sanitized errors. |
| Exported inputs alone are not sufficient replay acceptance | Verifier checks embedded performance source/runtime/input/ledger identity, benchmark evidence hash, contribution-setting consistency and every rebuilt financial/comparison field. Altered identity/revision/marks/metrics/daily/methodology fail tests. Three actual API exports replay from both working source and independently extracted accepted source. |
| New backend files change conservative exact-source identity | Old Phase 8/9A reports and source archives remain unchanged. New 80-file exact-byte backend/offline-script archive preserves accepted source independently of Git line-ending conversion. Matching runtime is still required; hashes are consistency checks, not an external signature. |

Development runs initially exposed a fixture version mismatch and a zero-start
reason precedence expectation; those were repaired before analytical acceptance.
The first full run passed 624 backend cases but stopped at a main.py formatting
failure. Formatting was corrected. The additional initial-funding regression
then exposed and repaired the alignment issue above. Final gates below use the
complete corrected source and 625-case suite, not the earlier failed runs.

The first local commit attempt selected the system Python 3.11 for Git hooks,
which lacked Ruff/mypy, although the staged hooks had passed in the project venv.
No commit was created. The retry places `backend/.venv/Scripts` on PATH, retaining
the configured hooks and their gates rather than bypassing them.

## Fresh verification

Executed `scripts/verify.ps1 -EvidenceDirectory .verification/phase9b/full` with
disposable PostgreSQL on loopback port 55439 and bounded BLAS threads. Environment:
Windows 11, Python **3.12.14**, PostgreSQL **17.11**, Node **24.18.0**, npm **11.16.0**,
Vite **7.3.7**. Dependencies and the 95% coverage threshold were unchanged.

| Gate | Final result |
| --- | --- |
| Full backend including actual PostgreSQL | **625 passed, zero skipped**, 113.91s test execution |
| Combined statement/branch coverage | **97.76%**, above unchanged 95% gate |
| New benchmark tests | **41 analytical**, **3 private API**, **2 actual PostgreSQL** cases |
| Ruff / formatting / mypy | Passed; **131 files** formatted, **126 source files** typed |
| Configured hooks | Full-run hooks passed; final staged-file result retained separately |
| Full frontend | **133 passed**, zero failed/skipped; eight new benchmark cases |
| ESLint / production build | Passed |
| Existing scenario performance observation | Gaussian **0.1618s**, GMM **0.5050s**, 1000 paths × 252 periods × 5 assets; excludes HTTP/network/client rendering |
| Offline replay | Complete, missing and corrected actual API exports passed against working and separately extracted archived source |
| Historical preservation | **70/70** entry-baseline checks: complete master/audits/old evidence unchanged, original suggestions byte prefix unchanged |

Inherited Starlette/httpx deprecation and Vite chunk-size warnings remain visible
in the logs. They were not suppressed or represented as new benchmark defects.
Local observations do not establish comparative performance or production load.

## Synthetic browser and correction acceptance

The populated test account contains a GBP deposit of 100, a purchase of one equity
at 100, another deposit of 110 at a pre-flow price of 110, and a booked fee of 10.
Closing prices are 100/120/130; supplied benchmark total-return levels are 100/105/110.
These are explicitly synthetic test records, not the owner's portfolio or a real
market index.

- Version 4: closing NAV **230**, portfolio TWR **15%**, reconciled equity **+20pp**
  and account fee **−5pp**. Benchmark **10%**, cumulative difference **5pp**, relative
  wealth **4.54545%**; **2/2** paired intervals.
- Removing the intermediate benchmark level leaves portfolio/contribution available
  but makes whole-window benchmark/comparison/statistics undefined; **0/2** pairs.
  The browser displayed reasons rather than invented zero returns.
- An append-only reversal of the synthetic fee produces version 5. The stale browser
  request is rejected with a reload instruction and clears all old results. Reload
  clears both evidence inputs and selected dates before review/re-entry.
- Corrected version 5: NAV **240**, portfolio/contribution **20%**, benchmark **10%**,
  cumulative difference **10pp**, relative wealth **9.09091%**. Aligned daily evidence
  and benchmark identity/revision/provenance expand correctly.
- Corrected desktop and 390px viewport light/dark views inspected. DOM page width
  **375px** is within the 390px viewport, including expanded scrollable tables/evidence.
  No browser console errors were captured. Lock removes private results; refresh
  returns locked with no restored reports. Theme restored, viewport reset and test
  tab closed.

Evidence: [verification directory](verification/phase9b-2026-10-11/README.md).
Only the explicitly created browser test schema was removed. No test/Phase 9B
schemas or listeners on ports 8000, 5173 or 55439 remained after cleanup.

## Next boundary

Proceed with a separately specified **factor-regression stage** using reviewed
dated factor and risk-free series, explicit currency/calendar and excess-return
conventions, uncertainty diagnostics and replay. Do not silently substitute
benchmark beta for a factor model or alpha for an expected-return estimate.

Durable versioned portfolio benchmark defaults and automatic currency conversion
need separate data/settings contracts and acceptance. Broker reconciliation, fund
typing, historical classifications/benchmark constituent weights for Brinson,
provider licenses, backup/restore and publication remain separate work. The master
brief's broader Phase 9 goals are not declared complete by this bounded stage.
