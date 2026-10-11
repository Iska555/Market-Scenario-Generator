# Phase 9B — benchmark and realized active risk

Authorized by the owner's 2026-10-11 continuation of the approved sequence after
Phase 9A. Preserve master brief, previous audits and all historical evidence.

1. Define a report-scoped benchmark setting: identity/revision, provider/source,
   methodology reference, currency, gross/net total-return basis, hedging policy,
   effective dates and publication/retrieval times. Require supplied levels on the
   portfolio's UTC calendar-day intervals and explicit maximum quote age. Accept
   omitted/explicitly missing levels as typed coverage gaps; never auto-fill.
2. Implement pure comparison contracts/engine. Keep independently available
   portfolio/benchmark returns, daily arithmetic active and geometric relative
   returns. Require complete paired intervals for full-window descriptive active
   statistics. Sample tracking error and information ratio annualize with 365;
   beta/correlation use centered paired sample moments, with honest undefined
   denominators/counts and short-sample limitations.
3. Reuse one locked Phase 8 snapshot in a private read-only comparison endpoint.
   Optionally embed Phase 9A contribution from that snapshot. Add offline replay
   validating inputs, source/runtime and every comparison/contribution field.
4. Add explicit benchmark evidence controls in Performance, input templates with
   empty levels/provenance, one coherent request, private export and aligned result
   display. Apply existing edit/account/lock/late-response clearing to all results.
5. Test analytical identity/fees/flows/corrections, currency/calendar/version/age/
   cutoff validation, missing/zero/overflow/short/constant samples, exact active
   identities and modified replay rejection. Verify actual PostgreSQL all-table
   immutability, lock retention, stale versions and corrected reports. Inspect
   complete/missing/corrected/locked responsive browser workflows.
6. Run full PostgreSQL-enabled backend suite/coverage, Ruff/format/mypy/hooks,
   frontend tests/lint/build and existing scenario benchmark. Retain fresh logs,
   synthetic replay fixtures, exact accepted source bundle and preservation proof;
   write a separate methodology and Phase 9B audit, append suggestions/status and
   create a local checkpoint. Stop before factor regression/publication.

Boundaries: selection is explicit for the chosen account/report and retained in
private downloads, not a durable database default or certified benchmark archive.
No provider/license retention, currency conversion, 252-period substitution,
ex-ante tracking-risk model, security-level tracking-risk contribution, alpha,
rolling beta/capture, Brinson, fund registry extension or public release.
