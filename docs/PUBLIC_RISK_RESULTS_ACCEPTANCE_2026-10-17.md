# Public Risk Labs and results presentation — 2026-10-17

The owner requested a text-only wordmark, the regular serif from the overview
introduction for headings, moderate heading sizes, and an institutional simulation
report without decorative icons. The owner also explicitly requested that the Risk
Labs work without a private workspace key. This prospectively supersedes the
owner-only calculation boundary in the earlier usability acceptance record for
**only the two stateless ticker-based Risk Labs**. Existing private records remain
protected. The previous acceptance record retains its original meaning and bytes.

## Implemented behavior

- `PlatformShell` now uses a text-only Portfolio Management identity. Headings and
  the wordmark use regular Georgia, the existing introduction face; ordinary text
  and numerical values use the normal sans-serif stack. Main headings scale from
  26 px on mobile to 32 px on desktop. No new font downloads or dependencies.
- `ScenarioResults` replaces the eleven icon cards with four primary risk measures
  and a compact supporting-metrics grid. Removed every decorative results icon,
  coloured badge and heavy card shadow. Percentiles use aligned figures, subdued
  signed colours and a highlighted median. VaR/CVaR explanations and their
  loss-positive convention remain visible; negative tail values remain signed.
- The path chart uses one selected trace, subdued comparison traces and a full-width
  plotting area. Choose a trace, expand the bounded sample, inspect its tooltip,
  or zoom with the range handles and their keyboard arrow controls. The default
  shows twelve traces, plus a selected trace if it lies outside those twelve.
  Charts retain exact period observations; no invented smoothing, confidence bands
  or intermediate percentile estimates were introduced.
- The histogram uses all backend counts, uncluttered lower-bound axis labels, exact
  range tooltips, muted loss/gain colours and neutral zero-crossing bins. The signed
  contribution table retains negative contributions and typed unavailable values;
  correlation cells add a restrained signed heatmap with numerical values and legend.
- Short entrance/bar/focused-line transitions respect the browser's reduced-motion
  preference through a media-query subscription. Background paths have no animation.
  All displayed returns, percentiles, drawdowns, risk ratios and decomposition values
  still come from the existing backend populations. Display controls cannot change
  financial statistics. Model settings shown in assumptions match the selected family;
  inactive GMM/EWMA options no longer appear as applied assumptions.
- Both simulation POST routes now accept anonymous callers. Frontend requests send
  no owner header, and Risk Labs show “No sign-in required”. The release profile
  permits **12 attempts per rolling minute across both endpoints, process-wide**,
  one active simulation, no waiting calculation queue and the existing two-million-
  cell bound. Invalid/busy attempts also count. Spoofed IP headers cannot expand
  the budget. `ENABLE_MARKET_SIMULATIONS` is the current availability switch, with
  the previous private-named flag retained as a fallback for older configurations.
- Saved accounts, research, accounting and publication remain owner-protected.
  Owner-key recovery instructions now explain that neither Risk Lab needs the key.
  The actual key stays in the ignored local file, never in public source or output.
  README now explains the report controls and uses the new deployed overview image.

## Verification and deployment

All ten configured local checks passed: **791 backend tests, 178 frontend tests,
zero skips, 97.26% backend coverage**, dependencies, Ruff, format, mypy, commit
hooks, the numerical benchmark, frontend lint and production build. The initial
run exposed a stale publication test expecting 401 on public simulation input;
its invalid-input expectation now correctly requires 422, while its private-record
401 checks remain. The complete gate passed after that correction.

[GitHub Actions](https://github.com/Iska555/Market-Scenario-Generator/actions/runs/39067510336)
passed all three jobs for the release code: frontend and backend Python 3.12 / 3.14.
Vercel's deployment check also passed, followed by the actual browser checks below.

Live checks used no owner key. Both the single-asset and portfolio responses validate
against their typed contracts; histogram counts and signed volatility contributions
reconcile. The exact NVDA/AAPL/MSFT 40/40/20, five-year, 365-period, 1,000-path Joint GMM
example renders in fresh anonymous browsers on Fly and the original Vercel site.
Vercel also renders anonymous single-asset results with no alerts or console errors.
Private research/accounting/publication reads return 401. Preflight remains successful.
An identical portfolio request returns byte-identical output; observed latencies were
1.791 s single, 1.140 s portfolio and 0.712 s repeated portfolio after readiness.
The two-million-cell case returns 200 in 1.021 s. Overlapping maximum requests return
200 and a bounded 503/Retry-After: 5; the busy response took 0.193 s. These are measured
examples, not a latency or capacity SLA. Initial readiness includes host wake-up time.

Deployed browser checks covered trace changes, full-sample expansion from 12 to 30,
unchanged percentile table through chart controls, keyboard range adjustment,
1600×1000 desktop and 390×844 mobile dark mode. Mobile document/client widths both
measured 375 px (remaining viewport space is its scrollbar). Zero document overflow,
zero brand SVGs and zero decorative result icons. Reduced-motion support is implemented;
the verification browser's preference was false, so no emulated reduced-motion browser
acceptance is claimed. Initial JavaScript is 255.53 KB / 80.54 KB compressed; charts
remain lazy-loaded. No extra dependency or animation library was added.

Release code: `443957f3b03213f7056727b25cf879989d332b6e`.
Image: `registry.fly.io/stochastic-market-simulator@sha256:08c287690db02e9034fac1c50e0e676653fa83fe73f4ddefbc34d0e9204ce429`.
All 95 deployed backend Python files match the working source. Runtime is Python
3.12.15, NumPy 2.3.5, pandas 2.3.3, scikit-learn 1.8.0, FastAPI 0.124.4 and yfinance
0.2.66. API peak resident memory observed after maximum/concurrent checks was
389,240 kB on the existing 512 MiB machine. The existing single Fly machine retains
auto-stop/start and minimum running count zero. No extra permanent compute, database,
secret rotation or migration. Traffic/uptime still determine provider billing; the
request limits do not constitute a guaranteed US$5 provider billing cap.

## Preservation and remaining work

All **509 prior documentation/evidence records**, the permanent master brief and
the existing suggestions prefix remain unchanged. Public synthetic version
`51b34ac3-3c73-43b6-b4f8-253eb70ba7a5`, content hash
`54f4a29668a7cc4a0478414c8c134ef262376615c7a393d3129f334442801e69`
and lifecycle history compare equal before/after deployment. No account, portfolio,
publication, research or transaction was created by these checks. Demo, paper and
future real histories remain distinct; no broker or verified personal record is claimed.

A new 206-file source/build/helper archive was extracted in memory and compared
byte-for-byte with its recorded manifest. Earlier replay archives remain intact.
This is not a claim of a newly executed three-report production replay or a new
production restore. The earlier 2026-10-17 fresh local restore of the retained synthetic
backup matched all 14 tables; that unchanged evidence remains in the preceding
usability acceptance. No database schema or persistence behavior changed in this repair.

Evidence: [dated records and screenshots](verification/public-risk-results-2026-10-17/).

**Next unfinished launch step: L6.2 — inspect the actual browser-saved production
snapshot JSON and record final launch acceptance.** Market-data outages, cold starts
and shared busy/rate responses remain possible. Private workspace access is still a
single-operator key workflow. Deferred advanced analytics, prospective paper operation
and real-account integration remain outside this bounded release.
