# Phase 9D acceptance — portfolio benchmark settings and factor-data readiness

Closeout date: **2026-10-12**. Continuation began 2026-10-11 after Phase 9C; the
owner subsequently reiterated continuation with the master plan. Scope:
[execution plan](superpowers/plans/2026-10-11-phase-9d-settings.md).
This is a new record. The master, every previous audit/evidence file and original
suggestions prefix are preserved, including earlier download qualifications.

## Disposition

**Accepted for bounded local use:** append-only portfolio benchmark identities,
private current/paginated history/save/clear API and UI, independent setting
revisions, idempotent retries, coherent report selection receipts and offline replay.
The master brief's portfolio-level explicit benchmark configuration now exists.
Saving does not choose suitability, supply prices or automatically enable comparison.

[BENCHMARK_SETTINGS.md](BENCHMARK_SETTINGS.md) specifies persistence and receipts.
[FACTOR_DATA_READINESS.md](FACTOR_DATA_READINESS.md) is prospective integration
policy; no real factor source/currency/calendar adapter is claimed implemented.
Existing return/regression/coverage formulas are unchanged. No HAC/rolling,
Brinson, actual broker/fund support, publication, hosted CI or deployment claim.
Broader Phase 9 remains incomplete.

## Implementation and findings

| Original location / issue | Repair or boundary |
| --- | --- |
| Accepted benchmark choice existed only inside report evidence | Added `benchmark.settings`, strict create/selection/history contracts and migration `20261011_04`. Identity and reasons persist; levels/factor data do not. No existing migration was rewritten. |
| Mutable defaults could erase selection history or alter old reports | Every save/clear appends an independent revision with server time/UUID/hash. PostgreSQL update/delete trigger, unique portfolio revision and optimistic current-revision check. Clearing retains old choice/reason. |
| Settings and ledger writers could race | Reuses the same portfolio row lock. Real competing writers produce one saved revision and one conflict; report retains the lock and changes no migrated table. Ledger sequence does not change when settings change. |
| A connection can fail after a write commits | UUID/content retries return the original record even after later revisions. Client retains unresolved request ID until inputs change, then reloads current history after success. Different content/portfolio ID reuse fails; no destructive retry. |
| A saved default could bypass review or leak later knowledge into a report | Explicit optional saved revision is checked under the report lock for current/non-cleared identity, equality and recorded-time cutoff. Changed/cleared selection returns 409; mismatched identity or cutoff returns 422. No fallback to a historical default. |
| Later settings lookup would make offline replay unstable | Comparison retains a full hashed selection receipt; factor retains it through nested comparison. Replay checks receipt identity/account/hash/provenance plus all financial outputs without a database. Old receipt remains replayable after later clearing. Hashing is consistency checking, not authenticated attestation. |
| Benchmark errors inherited dependency header limitations | Expanded the accepted scoped no-store middleware to benchmark routes, including expected authentication/schema/domain errors. Sanitized validation inputs remain excluded. |
| Performance state needed settings and explicit evidence binding | Sixth optional transport loads private settings. Separate reviewed identity/reason controls, save/clear/history, empty saved-identity template and explicit link control. Editing/importing benchmark evidence drops its receipt link. Generation guards prevent late settings reads/writes restoring private state. |
| Existing lock-test wrapper accepted only three calculation arguments | First full run had 695 passes and one TypeError in `test_benchmark_postgres.test_pg_comparison_lock_stale_rejection_then_changed_fee_report.checked`. Added the optional selection argument and forwarded it; original lock/stale/corrected assertions remain. Final full run passes all 696 cases. |
| Public factors do not automatically satisfy the accepted GBP daily contract | Read primary source descriptions; documented USD/trading-calendar/risk-free/spread/provenance review and common-boundary adapter requirements. No fabricated weekend observations, spot-rate multiplication of spreads or provider ingestion. |

Development style/typing and patch-context failures were repaired before final
gates. An initial scoped invocation without output was stopped. The diagnostic
rerun passed new API cases then exposed a PostgreSQL connection wait: the test
cluster had been started on default port5432 instead of acceptance port55439.
Restarted with explicit loopback/port and added a five-second connection timeout.
No passing PostgreSQL claim is based on those stopped invocations.

The final full runner passed backend/quality/hooks/benchmark/client tests; a later
continuation interrupted it during lint. Lint/build were completed explicitly,
with retained logs and successful command exit. The same interruption stopped
acceptance services; resumed only the original synthetic schema for remaining
API retention. Stopping that API session also ended its PostgreSQL process;
restarted briefly to remove the named schema, then stopped it explicitly. None of
these process interruptions changed source, calculations or retained old records.

## Fresh verification

Runtime: Windows 11, Python3.12.14, PostgreSQL17.11, Node24.18.0, npm11.16.0,
Vite7.3.7. Existing pinned dependencies and 95% coverage requirement remain.

| Gate | Verified result |
| --- | --- |
| Full backend including actual PostgreSQL | **696 passed, zero skipped**, 143.77s |
| Statement/branch coverage | **97.89%** |
| New settings cases | **13 contract/API/replay**, **4 actual PostgreSQL** |
| Ruff / format / mypy | Passed; **144 files** already formatted, **138 source files** typed |
| Configured hooks | Passed in full runner; final staged result retained separately |
| Full frontend | **147 passed**, zero failed/skipped; six new settings cases |
| ESLint / production build | Passed explicitly after runner interruption; build29.19s |
| Scenario observation | Gaussian0.2443s, GMM0.4631s, existing 1000×252×5 workload, excluding HTTP/network/client |
| API exports/replay | Three reports passed against working and separately extracted **87-file** exact backend source |
| Historical preservation | **148/148** full-file/original-suggestions-prefix checks |

The inherited Starlette deprecation and Vite bundle-size warnings remain visible.
Timings are local observations; no performance improvement or capacity claim.
Exact archived replay excludes migrations/dependencies/frontend/deployment and
requires compatible runtime. Old reports use their own accepted archives.

## Browser and actual API evidence

Separate disposable GBP cash account: synthetic deposit1000, ledger version1,
Jan1–3 2025 closing evidence without market quotes; benchmark levels100/102/101.
No live account or provider data. Browser initially used127.0.0.1 origin while
the API allowedlocalhost; switching to the configured localhost origin restored
access. Accessible date-value controls were used after locator date filling did
not update controlled state. These were development/automation setup findings.

- Saving reviewed identity with reason creates setting revision1; comparison
  stays off until explicitly using the saved identity/template.
- Fill reviewed levels, link to revision1 and measure: portfolio TWR0%, benchmark
  1%, difference−1pp, relative wealth−0.990099%. Receipt revision/time/reason is
  visible. Cash beta0 and undefined correlation retain honest zero-variance context.
- Clearing with a reason appends revision2. Old reports/evidence link clear; history
  retains both reasons and revision1. Ledger stays version1.
- Lock/refresh clears unsaved private state and returns locked Overview. After
  unlocking again, saved cleared revision2 remains; inputs/options are blank/off.
- Desktop and390×844 light views inspected; page width375≤390. Final localhost
  console capture has no errors. Viewport reset, theme left light, test tab closed.
- Actual API history before/after clear, selected comparison, nested factor report
  and report-only comparison retained. After clearing, old selected request gives
  no-store409; report-only explicit identity remains permitted. Both old receipt
  exports replay offline after clearing; no database/default lookup is performed.

Reports retained here are actual API exports. This stage does not independently
verify browser saved-file delivery; earlier Phase9B/9C qualifications remain intact.
Factor export uses32 cash intervals, an exact/constant response and incomplete
auxiliary benchmark coverage; null inference/statistics remain explicit.
Synthetic observations establish workflow/replay, not investment skill.

[Evidence index](verification/phase9d-2026-10-11/README.md) retains gate logs,
exports, screenshots, source identities, preservation and cleanup. Only the
explicit Phase9D schema was removed; no test/Phase9D schemas or acceptance
listeners on8000/5173/55439 remained after shutdown.

## Next procedure under the master

Specify common valuation intervals and a reviewed factor-data adapter before
using real USD trading-day factors for this GBP portfolio. Preserve daily ledger
accounting and introduce a separately versioned measurement/alignment policy.
Require an actual reviewed source/fixture and currency/funding/risk-free definitions;
do not invent inputs to unblock acceptance. Then scope HAC/bootstrap and rolling
beta/capture with dependence, window, coverage and sample diagnostics. Brinson
remains conditional on historical classifications/benchmark weights. Fund/broker,
ledger-to-construction, restore and public track-record work retain separate gates.
