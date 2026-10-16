# Launch L1 acceptance — portfolio modes and isolation

Accepted **2026-10-14** (Europe/London); work began 2026-10-13. Baseline `fb11200`
plus pre-existing uncommitted planning documentation, all preserved. Scope: L1.1
and L1.2 in the owner-approved PLAN.md. Broader Phase 9 and launch L2–L6 remain open.

## Disposition

Accepted for the bounded local identity workflow. A new additive immutable registry
preserves legacy accounting/report contracts, leaves every existing record private
and unclassified, and allows deliberate creation of a distinct synthetic demo.
See [identity boundary](PORTFOLIO_IDENTITY.md) and
[evidence](verification/launch-l1-2026-10-14/README.md).
No real broker account, verified personal performance, public publication, restore,
staging or deployment is claimed.

## Findings and repairs

| Location | Finding / repair |
| --- | --- |
| accounting contracts/repository | Existing portfolios have immutable accounting identity but no reviewed mode. Kept these contracts unchanged; added separate identity adapters and storage. No inference from name, broker label or prior synthetic tests. |
| public_track_record contracts/repository/routes | Added strict demo creation, explicit mode context, private defaults, no broker verification, atomic creation and idempotent retries. No classification/edit endpoint for existing histories or paper/real programme. |
| migration 20261013_05 | New migration only; legacy rows untouched. Database rejects identity mutation, historical inserts and invalid modes. Empty/populated upgrade, metadata and concurrent-write checks pass. |
| new birth-time guard during development | Comparing Python/DB clocks could reject valid creation. Repaired with a transaction-lock guard. A probe confirmed released child-savepoint locks do not survive; creation now keeps both inserts in one live savepoint. Tests cover this actual PostgreSQL path and the owner API. No cross-clock ordering check remains. |
| new PostgreSQL test | Initial post-commit ORM assertion accessed an expired detached object. Captured the UUID before commit; final test passes without changing application rules. |
| workspace / ledger / performance | Separate transport preserves old financial endpoints. Visible labels explain synthetic/private/unclassified status. Demo drafts use synthetic source defaults. Selection clears prior data; generation guards ignore late responses. |
| execution environment | Sandboxed TestClient run stalled after 11 contract cases and was stopped. Authorized execution completed API cases; first PG run failed because the sandbox-started service had stopped. Restarted the existing disposable PostgreSQL outside the sandbox, then completed real PG tests and full gates. No stopped/failed run is acceptance. |
| browser tooling | Development Vite served an empty React root; tested the built production artifact through Vite preview instead. First creation attempt showed an unconfirmed outcome; probing/retrying the same UUID returned one consistent record. A separate fresh browser-only creation succeeded. No duplicate/reset operation was used. |
| responsive evidence | Viewport capability calls did not change measured 714×660 viewport. Recorded actual default-width checks only; no claimed 1280/390-pixel acceptance. Override was reset. Mobile/desktop breakpoint acceptance remains for L2/L3. |

## Fresh verification

Final full runner: `.verification/launch-l1-2026-10-14-run2`, all ten exit codes 0.

- Backend: **759 passed**, **zero skipped**, **97.92%** statement/branch coverage;
  69.97 seconds. New identity suite: 26 cases (22 portable, 4 actual PostgreSQL).
- Frontend: **160 passed**, zero failed/skipped; seven new mode/transport/switch cases.
- Dependencies, Ruff/format, mypy, hooks, existing scenario benchmark, lint and
  production build pass. Build: 2353 modules; main JS 791.88 kB / 229.90 kB gzip.
- Retained Phase 9A corrected contribution report replays with its separately
  extracted 74-file accepted archive and compatible Python 3.12.14 runtime.
  Original report/archive hashes remain unchanged; no new-source replay claim.
- Preservation check covers all 253 starting records; suggestion text retained as
  a byte-identical prefix. Original planning work is preserved. New evidence and
  append-only launch records are separate from historical files.

Inherited Starlette deprecation and Vite bundle-size warnings remain. Local Python
3.12.14 and PostgreSQL 17.11 were used (CI specifies PostgreSQL 17.6). This does not
claim hosted CI, alternate runtime acceptance, production capacity or legal review.

## Actual browser acceptance

Used the production frontend and an isolated synthetic-only PostgreSQL schema.
A legacy private fixture had GBP 100 and no positions. In Ledger, selected explicit
demo mode, generated a separate UUID and created an empty demonstration. Browser-only
creation, reload/reselection, and persistence after lock/refresh were verified.
Demo kept zero ledger rows; legacy cash remained in the legacy identity. No holdings
or real trading history were invented. Demo broker labels and manual/import defaults
are synthetic. Overview and Performance display the same mode and creation time.
Switching back to legacy shows private/unclassified; lock and refresh remove private
identities/evidence and require unlocking. Mode and form controls use labelled native
selects/buttons; keyboard and late-response logic are covered by existing/new tests.
No complete report generation/download or mobile browser acceptance belongs to L1.

## Next unfinished step

**L2.1 — deterministic demo fixture and isolated idempotent loader**, followed by
fresh performance/contribution/comparison generation, exact replay and actual
download/browser acceptance. Public preview/publication and operational restore
remain subsequent ordered gates. Advanced real-factor/account work is deferred.
