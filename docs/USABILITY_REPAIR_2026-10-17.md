# Simulation, access and product experience acceptance — 2026-10-17

The owner requested repair of the failing hosted simulation, usable private
access, a feature-led README and a clearer, stronger interface. This is a bounded
repair to the existing release, not acceptance of deferred analytics or real-account
integration. The Merton project was read as a design/documentation reference only.

## What failed and what changed

- `backend/main.py::factor_private_cache` authenticated `OPTIONS` before the CORS
  layer could answer. The original Vercel simulation reproduced **Failed to fetch**;
  its preflight returned 401 without an allow-origin header. CORS now wraps
  authentication, and preflights reach it without a credential. Unauthorized
  calculations still return 401. Tests cover both paths.
- The Fly profile explicitly set `ENABLE_PRIVATE_SIMULATIONS=0`, so a valid owner
  key would still receive 503. The existing machine now enables owner simulations
  with one active tensor workload and no waiting calculation queue. Overlap returns
  a quick 503 with `Retry-After: 5`; the slot remains held until the worker finishes,
  including after caller cancellation. The two-million-cell input bound remains.
- Production frontend requests now use same-origin `/api`. Vercel rewrites proxy
  that path to Fly; local development retains an explicit configurable API address.
  The two existing HTTPS domains are permitted origins. No authentication bypass,
  anonymous private calculation path or frontend credential was introduced.
- The existing owner key had not been handed over usefully. It was recovered from
  its local Windows-protected copy, verified against the live owner API, and made
  available in a Git-ignored file restricted to the current Windows user.
  `scripts/owner-access.ps1` repeats that local recovery without printing the key.
  The form explains access, and locked Risk Labs offer a direct unlock action
  instead of allowing a doomed submission. Browser refresh and lock clear access
  and private results. No credential was rotated or embedded in the application.
- The README is now a user guide: purpose, capabilities, all nine workspaces,
  practical workflows, simulation instructions, public demonstration, private
  access and a short installation section. Prior phase notes remain in Git and
  historical documentation. The permanent master brief was preserved.
- The interface uses a larger Portfolio Management identity, stronger typography,
  shorter descriptions, a responsive workspace menu and clearer access controls.
  Removed the sidebar slogan and personal planned-account display. New account
  fields no longer prefill a nonexistent Lightyear account; CSV source defaults
  no longer imply a particular broker. Detailed simulation qualifications remain
  available in expandable settings and results. Browser review caught punctuation
  encoding damage during editing; it was repaired and the frontend reverified.

## Verification

- **790 backend tests, 178 frontend tests, zero skips, 97.25% backend coverage.**
  Dependencies, Ruff, formatting, mypy, existing hooks, numerical benchmark,
  frontend tests, lint and build all passed. Frontend assertions were updated for
  the new unlock action, then the complete frontend suite was rerun after final
  copy/encoding changes. No backend source changed after its full passing run.
- [GitHub Actions](https://github.com/Iska555/Market-Scenario-Generator/actions/runs/39065184305)
  passed frontend and both Python 3.12 / 3.14 backend jobs for release code commit
  `8e879d550d39f038c66bf348dd22e1b35d9f5bb8`. Vercel's production deployment check
  for that commit passed; actual HTTP and browser checks followed deployment.
- The exact reported browser setup — **NVDA/AAPL/MSFT, 40/40/20, five years,
  365 periods, 1,000 paths, joint GMM** — renders results on **both Fly and the
  original Vercel URL**, with zero alert elements. Owner unlock works through
  Vercel's proxy. Single-asset and portfolio API outputs validate against their
  typed contracts; histogram counts and volatility contributions reconcile.
- The default initial JavaScript bundle fell from **828.47 KB to 255.85 KB**
  (239.24 KB to 80.72 KB compressed). Research modules and charts load when needed.
  Gzip reduces response transfer size; price history remains cached for one hour.
  Financial formulas, statistical populations and chart-sample limits are unchanged.
- On the live Fly service after readiness, measured requests took **1.318 s**
  (single), **1.053 s** (three-asset GMM) and **0.559 s** (identical repeat).
  Repeat portfolio response bytes matched. The two-million-cell request passed
  in 0.951 s. Observed API process peak RSS was **386,812 kB**, within the 512 MiB
  machine. A pair of overlapping maximum requests returned 200 and 503; the latter
  took 0.239 s. These are bounded observations, not a latency or capacity SLA.
- Actual desktop and 390×844 mobile checks covered the responsive menu, direct
  unlock focus, simulation results, theme switching, and clearing results on lock.
  Mobile document width was 375 px with a 390 px viewport including its scrollbar;
  no document horizontal overflow. The final result page has no damaged punctuation.
- A **fresh local restore on 2026-10-17** of the retained 2026-10-16 synthetic
  production backup matched all values, counts and identities in **14 tables**
  in 0.720 s. This was a new separate local database, not a new cloud backup or a
  production restoration. The original dump and databases remain unchanged.
- Public snapshot and lifecycle history were compared before/after deployments
  and through Vercel's proxy: unchanged. The original synthetic publication
  `51b34ac3-3c73-43b6-b4f8-253eb70ba7a5` retains its content hash
  `54f4a29668a7cc4a0478414c8c134ef262376615c7a393d3129f334442801e69`.
  No new portfolio, publication, transaction or private research record was created.

## Deployment and reproducibility

Final image:
`registry.fly.io/stochastic-market-simulator@sha256:96e6f35ddd6687e798e438a2901edb25cd7a139f948108cbf92065cc5bc51001`.
All **95 deployed backend Python files** match the working source bytes. The image
uses Python 3.12.15; the local full gate used Python 3.12.14. Matching source and
runtime identities are retained with a verified 206-file source/build/helper
archive. It contains no credentials, database dumps, raw hosted reports or OS layers.
This archive verification does not claim a newly executed three-report replay;
all earlier exact-runtime replay evidence and archives remain preserved.

The existing single shared-CPU 512 MiB Fly machine remains, with auto-stop/start
and minimum running count zero. No extra permanent compute or database was added.
The build used Depot. The first post-deployment health request took
12.669 s; provider outages and host sleep still affect first use. Keeping a server
always warm would trade cost for latency. The owner's US$5/month ceiling remains;
the existing configuration does not provide a guaranteed account-wide dollar cap.

The private workspace remains operator-only. The public demonstration remains
synthetic/read-only, with no broker connection or verified personal track record.
Advanced analytics, paper operation and real-account integrations remain deferred.

**Accepted for this repair scope.** Next unfinished launch step remains **L6.2**:
inspect the actual browser-saved production demonstration JSON before recording
final launch acceptance. This repair does not silently close that older gate.

[Verification files and screenshots](verification/usability-2026-10-17/README.md).
