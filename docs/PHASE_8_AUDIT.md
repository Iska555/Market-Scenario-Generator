# Phase 8 acceptance and reproducibility closeout

Date: **2026-10-09**. The owner approved the recommended proceeding procedure
and selected this closeout. This is a new acceptance record. The permanent
master brief and the existing phase audits/reviews were not edited by this task.
The approved continuation is appended in [BRIEF_SUGGESTIONS.md](BRIEF_SUGGESTIONS.md).

## Disposition

**Accepted for the bounded local Phase 8 scope:** private ledger-derived TWR,
XIRR, linked calendar returns and descriptive realized statistics using explicit
supplied valuation evidence, with offline replay of downloaded reports.
Acceptance includes actual disposable PostgreSQL tests and synthetic browser
workflows. It does not establish real-account reconciliation or production
readiness. Attribution and publication require their own implementation and
acceptance records.

The checkout originally contained uncommitted Phases 4–8 work on top of
`88f4390`, which captured Phases 1–3. The closeout checkpoint includes that
existing implementation and its historical documents together with the repairs
below. It does not invent separate historical phase commits or backdate this audit.

## Findings and repair status

| Original location / issue | Disposition and evidence |
|---|---|
| `performance/engine.py:build_report`: zero unit-value recovery could resurrect continuous performance; full withdrawal bypassed the closing guard | Repaired before this closeout. The original finding and dated repair disposition remain in [PHASE_8_FINAL_REVIEW.md](PHASE_8_FINAL_REVIEW.md). Fresh full-suite verification includes `test_return_cannot_resume_after_zero_unit_value`, `test_zero_loss_recovery_cannot_be_hidden_by_same_day_full_withdrawal`, zero-value funding and persistent-zero regressions. |
| `performance/engine.py:build_report`: mark-age comparison must use UTC dates for offset timestamps | Existing UTC repair retained; `test_quote_age_uses_utc_day_for_offset_flow_timestamp` passed in the fresh suite. The prior review remains unchanged. |
| Referenced `docs/PHASE_8_AUDIT.md` did not exist | This dated audit supplies the missing acceptance record without replacing either independent review. |
| Copied `backend/env` referenced an unavailable machine interpreter | Created `backend/.venv` from pinned dependencies; left the inherited environment untouched. Added and executed `scripts/bootstrap.ps1`, plus full resolved Windows/Python 3.12 constraints. |
| `performance/engine.py` manifest could lack a configured source identity | Added an actual backend-source SHA-256 and Python version. Optional configured build identity remains separate. Source hashing includes all `backend/src/**/*.py` and `backend/main.py`, including dirty/untracked dependencies. |
| Downloaded reports lacked an executable offline consistency check | Added `performance/replay.py:verify_replay` and `scripts/replay_performance.py`. Checks source/runtime, input/ledger digests, portfolio identities, full/visible versions, methodology/conventions and every financial output. Twelve roundtrip, modification and historical-cutoff tests passed. |
| Performance transport lacked direct PostgreSQL acceptance evidence | Two new actual-PostgreSQL tests verify unchanged contents of every migrated table, identical repeated output, a held portfolio row lock, subsequent writer success, stale-version rejection and refreshed calculation. |
| Frontend lockfile audit reported 15 vulnerabilities | Applied compatible `npm audit fix`, without force or changing package.json ranges. Clean `npm ci`, tests, lint and build passed afterward; fresh npm audit reports zero vulnerabilities. |

No new TWR, XIRR, ratio, moment or tail formula was introduced by the closeout.
The original statistical conventions and repair history remain in
[PERFORMANCE.md](PERFORMANCE.md), [PHASE_8_METRICS_REVIEW.md](PHASE_8_METRICS_REVIEW.md)
and the final review.

## Fresh verification

Evidence: [dated verification directory](verification/phase8-closeout-2026-10-09/README.md).
The new `scripts/verify.ps1` was executed with an isolated PostgreSQL database.
It requires database configuration for acceptance and rejects skipped tests;
`-AllowDatabaseSkips` is an explicitly diagnostic alternative.

| Check | Observed result |
|---|---|
| Final full pytest with PostgreSQL enabled | **544 passed, zero skipped; 97.84% statement/branch coverage** against the unchanged 95% aggregate gate; initial run was 542 passed before the two metadata regressions |
| Ruff lint / formatting | Passed; 113 Python files already formatted |
| Mypy | Passed over 110 source files |
| Dependency consistency / configured pre-commit hooks | Passed |
| Frontend after dependency update and clean installation | **119 passed**, zero failures/skips; ESLint and production build passed |
| Fresh npm audit | Zero reported vulnerabilities at this verification date |
| Offline engine benchmark | Gaussian 0.2542 s; GMM 0.4798 s; 1,000 paths × 252 periods × 5 assets, including preparation through response assembly |
| Bootstrap script | Executed successfully with the bundled Python executable; constrained pip installation, pip check and npm ci passed |
| Download replay | Both direct synthetic HTTP output and the actual UI-downloaded JSON verified offline without database/provider access; an explicit fixture regeneration after the final metadata guard verified identical financial outputs against the final source |

Local profile: Windows 11, Python **3.12.14**, Node **24.18.0**, npm **11.16.0**,
PostgreSQL **17.11** and Vite **7.3.7**. The constraints capture the complete resolved
Python environment. They are version constraints, not package-hash locks or
cross-platform guarantees. Python 3.14 and CI's Node 22 profile were not rerun
locally. Hosted CI was not run as part of this closeout.

One inherited Starlette/AnyIO `BlockingPortal` alias deprecation warning remains.
The production build retains its >500 kB chunk warning: approximately 744 kB
JavaScript, 219 kB gzip. No warning threshold was raised. The bootstrap installation
also reports npm's pending esbuild install-script approval notice; the clean
installation nevertheless passes the actual build. Benchmark timings exclude
network, HTTP serialization and rendering and are not a service-level guarantee.

## Browser acceptance with a disposable synthetic account

The test account held one synthetic GBP equity. Opening NAV was 100; a subsequent
110 deposit issued 100 units at pre-flow NAV 110; the final price was 130 and a
booked fee was 10. The browser showed **15% TWR, NAV 230, 200 units and unit value
1.15**, with matching partial-month linking and daily history. Its short-window
annualized XIRR was extreme and explicitly warned about; annualized TWR was withheld.

Checked through the actual browser:

- Locked private access and an empty evidence template containing the actual
  external-flow transaction ID.
- Complete supplied evidence, daily history and the replay JSON download.
- Editing evidence cleared the prior report. Removing a required daily quote
  produced undefined linked TWR rather than a fabricated zero; independently
  covered final NAV remained available.
- A synthetic fee reversal submitted through the local API changed ledger
  version 4 to 5. The browser rejected its stale version and cleared the old
  report. Reloading and recalculating returned **20% TWR, NAV 240, 200 units and
  unit value 1.2**. XIRR then correctly reported a root outside supported bounds.
- Mobile width 390 px had no page-wide overflow (375 px content/scroll width).
  Navigation and tables retain their own scrolling. Light/dark appearance was
  inspected; locking cleared results and refresh returned to a locked overview.
- Browser error-log inspection returned no captured errors.

Screenshots retain the populated desktop and corrected mobile results. These
checks used synthetic data only; they are not a comprehensive accessibility audit
or a native broker-statement acceptance test. The reversal was submitted through
the API, not tested as a ledger-UI correction workflow in this closeout.

PostgreSQL ran in a new temporary cluster bound to loopback on port 55439. Tests
used isolated migrated schemas. The browser schema was explicitly removed,
remaining disposable schemas were verified absent, and the API, frontend and
temporary PostgreSQL server were stopped afterward. No existing user database
or broker account was used. PostgreSQL binaries came from the
[official vendor download](https://www.enterprisedb.com/download-postgresql-binaries).

The final backend rerun initially waited on a missing listener because its temporary
restart omitted the port option. That test attempt was stopped, the disposable
cluster restarted explicitly on loopback port 55439, and the complete suite rerun
with a five-second connection timeout. This was a test-setup error, not a product
repair or a reason to waive database checks.

## Replay contract and remaining limitations

Reports retain private visible ledger rows and resolved marks, not just hashes.
Exact replay requires matching source bytes and Python/numerical library versions.
A final review added rejection of altered methodology/convention metadata.
Because this changed source identity after browser capture, the original UI
download is retained alongside an explicitly regenerated fixture and provenance
record; all financial outputs are identical. The final-source replay command uses
the regenerated fixture rather than silently replacing the original download.
A legacy report still parses but cannot pass exact verification without its source
fingerprint; explicit regeneration is required. Later events unknown at a historical
knowledge cutoff are not fabricated to match the full ledger version.

The verifier proves internal consistency, not independent quote validation,
authentic timestamps, tamper-proof external attestation or GIPS compliance.
Source hashes are conservative: even an unrelated backend source change or
checkout line-ending change requires retaining compatible source or regenerating.

Performance uses UTC calendar-day closes and 365 observations/year, unadjusted
supplied prices, explicit FX, net booked dividends/fees and flow-boundary marks.
Missing coverage is not carried forward. XIRR uses actual days/365, rejects
nonconventional multiple-sign-change schedules and has explicit root bounds.
Corporate actions, settlement reconciliation and unrecorded events/costs are not
silently certified. Request limits are not production load certification.

Current instruments remain equities and ledger cash. Native Lightyear import
needs a verified statement fixture. Construction still accepts hypothetical
supplied weights. Live/provider reconciliation, fund/ETF semantics, durable
hosting, backup/restore evidence and operational acceptance remain separate work.
There was no push, deployment or publication in this closeout.

Historical documents were excluded from task edits. Checkpoint hashes identify
their retained bytes. The initial checksum file was written into temporary sandbox
storage and was unavailable at final collection, so the evidence does not claim
a completed task-entry-to-final checksum comparison. The suggestions continuation
was written by byte-preserving append; no earlier suggestion was rewritten.

## Approved next stage

Proceed with **Phase 9A reconciled position contribution**: specify period-appropriate
ledger exposures, external-flow boundaries, cash/dividends/fees/FX and multi-period
linking before implementation. Require the full breakdown to reconcile to Phase 8
TWR within a documented tolerance and show residuals explicitly. Follow with
versioned benchmark/active-risk analysis, then factor regression, then Phase 10
publication acceptance. The approved integration priorities and fund/ETF boundary
remain in the appended suggestions; later implementation gets its own plan and audit.
