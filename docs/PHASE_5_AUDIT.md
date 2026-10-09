# Phase 5 audit — 2026-09-09

## Authorization and pre-implementation boundary audit

The owner's Phase 5 continuation request explicitly approves Phases 1–4 and
authorizes expected-return/scenario modelling, including the seven design
suggestions and permanent rules A–D. Stop before Phase 6. Existing Phase 4 work
was uncommitted on entry on `phase-1-correctness`; preserve it and historical
audits. Work in this checkout to retain that dependency. No commit, push or
deployment is implied.

| Original file / function | Classification | Disposition / limitation |
|---|---|---|
| `research/schemas.py:ObservationCreate`, `repository.py:observations` | CORRECT AS IMPLEMENTED | Decimal facts; publication `as_of` and server `recorded_at` knowledge cutoff; rank eligible restatements only. Reuse availability semantics. |
| `research/thesis/repository.py:append_revision` | CORRECT AS IMPLEMENTED | Immutable IDs, complete revisions, monotonic creation times. Validate explicit revision linkage and cutoff. |
| `research/thesis/schemas.py:ReviewCreate` | DESIGN DEBT | Legacy owner review return has no independent horizon; retain API compatibility and never import it as a Phase 5 view. |
| `data/preparation.py`, `data/providers.py` | DESIGN DEBT | Adjusted historical price proxy lacks verified FX/calendar reconciliation. Do not use automatically as present valuation or forward return. |
| `risk/scenarios/service.py:draw_returns`, `api/models.py` | CORRECT AS IMPLEMENTED | Explicit zero-log/historical diagnostic drift and simulation assumptions. Phase 5 has no connection that changes these formulas. |
| `research/database.py:require_research_access`, `get_session` | CORRECT AS IMPLEMENTED | Private owner-key API and transactional dependency; reuse for valuation evidence reads. |
| `research/metrics.py` | CORRECT AS IMPLEMENTED | Exact Decimal research arithmetic stays separate from statistical floating-point calculations. Preserve source values in evidence snapshots. |
| `docs/METHODOLOGY.md` | DESIGN DEBT | No Phase 5 return contract or valuation interpretation. Add forward-looking sections without revising historical audits. |
| Expected-return, fundamental/reverse valuation and scenario-set domains | NOT YET IMPLEMENTED at entry | Implement typed domain functions, private API and focused workspace with analytical tests. |

No confirmed pre-existing quantitative defect was identified in this boundary
audit. Numerical and integration findings discovered during implementation will
be appended below with repair status.

## Design decisions for owner review

Use a small stateless calculation API, with complete resolved inputs and referenced
evidence in returned run manifests. Do not add a new database archive or retain
provider datasets automatically. Return model outputs and explicit investor views
as different types; scenario probabilities remain optional. Fundamental valuation
uses EPS or FCF per share, terminal multiple, fixed annual cash dividends held
without reinvestment, and an explicit terminal FX factor. Buybacks enter the
per-share growth assumption only. No independent buyback yield is added.

Annualized scenario return is the equivalent compound rate of terminal wealth,
not expected realized CAGR. CAPM is a one-year arithmetic expected simple return;
multi-year conversion explicitly assumes a repeated independent annual gross mean.
Historical diagnostics report annualized arithmetic sample mean and IID standard
error, without assigning a forward horizon return. Local nominal models are the
initial statistical boundary; deterministic fundamental FX scenarios require
explicit exchange-rate assumptions and do not implement a multi-currency portfolio.

## Verification and completion record

Implemented `valuation/contracts.py`, `arithmetic.py`, `models.py`, `service.py`,
`routes.py`, and `views/expected_return.py`. The single private evaluation resource
dispatches user views, historical diagnostics, CAPM model estimates, fundamental
valuation, scenario sets and reverse valuation. No Phase 1–4 financial formula was
modified; `backend/main.py` only registers the additional router. No new database
table or migration was required. The Valuation tab contains explicit context,
security/revision/evidence selection, model forms and server-only result display.

### New defects found and repaired during development

| Original Phase 5 file / function | Classification | Repair / regression |
|---|---|---|
| `valuation/service.py:code_identity` | CONFIRMED BUG — FIXED | Initial parent-directory index selected repository root instead of backend; API replay tests caught missing main.py. Hash now includes actual backend source. |
| `views/expected_return.py:capm` | CONFIRMED BUG — FIXED in independent review | Separate `CapmEstimate(kind=model_estimate)` from explicit `ExpectedReturnView`; API/domain/React regressions verify no automatic adoption. |
| `valuation/models.py:validate_assumptions` | CONFIRMED BUG — FIXED in independent review | Cross-currency calculations reject omitted FX values; same-currency unity remains explicit. UI currency changes clear FX fields and require new entry. |
| `valuation/contracts.py:ReturnSample.coherent_sample` | CONFIRMED BUG — FIXED in independent review | Reject durations inconsistent with stated frequency; regression rejects annual intervals labelled monthly. Sanity bounds are documented, not claimed as exchange-calendar reconciliation. |
| `valuation/models.py:reverse` | CONFIRMED BUG — FIXED in independent review | Underflowed positive multiple returns typed undefined rather than defined zero. Regression uses near-zero/huge denominator inputs. |
| `valuation/models.py:fundamental` | CONFIRMED BUG — FIXED | Reject positive terminal wealth that would round to complete-loss return; regression covers cancellation at very small wealth. |
| `frontend/.../ValuationWorkspace.jsx` sample help | DESIGN DEBT — FIXED in re-review | Removed claim that quoted sample numbers preserve exact spelling; statistical samples resolve to floats. Exact decimal preservation applies to user return inputs and stored research evidence. |

### Verification evidence

- Full offline backend suite with actual PostgreSQL: **345 passed, no skips**;
  combined statement/branch coverage **98.36%** (95% gate). This is 72 additional
  tests relative to the 273-test Phase 4 baseline. New arithmetic, model and
  contract modules have 100% measured statement/branch coverage. Coverage is
  supporting evidence, not a proof of financial correctness.
- Analytical tests cover horizon conversion, CAPM known beta/rf/ERP cases and
  nonzero residual diagnostics, fundamental multiplicative decomposition, price
  versus cash-inclusive wealth, explicit FX, reverse recovery/impossibility,
  weighted terminal wealth, missing probabilities, undefined metrics, finite
  numerical boundaries and point-in-time API linkage.
- Three new PostgreSQL tests pass: source `NUMERIC(30,10)` precision survives in
  returned snapshots, explicit old revisions remain identifiable after append,
  publication/knowledge boundaries are inclusive and reject one-microsecond
  violations, missing/cross-security references fail, replayed results match,
  and whole-table/schema snapshots remain unchanged after evaluation. Existing
  PostgreSQL precision, immutability, concurrent-write and migration tests pass.
- Ruff lint, configured Ruff format (`--check backend scripts`), mypy (68 files),
  and `pip check` pass on Python 3.14.0. An exploratory `ruff format --check .`
  also scanned code blocks in the original brief and historical design files;
  those formatting differences were deliberately not applied. The repository's
  actual format gate passes and original documents remain preserved.
- Independent review identified four material findings above. All were repaired
  and re-reviewed. Reviewer reran **69 targeted valuation tests**, all passing,
  and found no remaining material backend/frontend integration issue. Final
  wording correction and explicit UI FX-reset regression were checked locally.
- Frontend: **41 tests pass**, lint passes and production build passes.
  Tests cover contextual rate display,
  model/view separation, historical labels, undefined values, probabilities,
  exact user decimals, stale private requests, cutoff changes and explicit FX.
- Browser with synthetic data in an isolated PostgreSQL schema: connected to
  the private Valuation tab, selected a security, ran a 10% three-year owner view
  (33.1% cumulative), ran the known fundamental example (USD 139.10 terminal
  wealth, 39.1% cumulative, displayed 11.6% annualized), visually inspected the
  result/components/uncertainty/manifest layout, and confirmed disconnect cleared
  private state. Browser coverage was a focused smoke check, not exhaustive E2E.
- No external/live market data was used. No hosted CI ran, no deployment/push/
  commit occurred, and no production database migration was attempted. Testing
  used the existing disposable local PostgreSQL 17.11 runtime. The Windows
  pg_ctl start helper failed to create a restricted token; launching postgres
  directly in a hidden process succeeded. Vite dev required the native config
  loader already used by this repository's build command.

### Major conventions and remaining limits

`METHODOLOGY.md` records each formula, units, horizon, estimator/window, assumptions,
interpretation and failure domains. Owner review should focus on the fundamental
cash-dividend convention (fixed annual local cash, no reinvestment, terminal FX),
positive EPS/FCF/multiple domain, and CAPM's explicitly selected repeated annual
gross-mean extrapolation. There is no expectation of realized CAGR implied by
annualizing expected terminal wealth. Buybacks are part of per-share growth only.

Manual samples and current prices have owner-declared source/adjustment/calendar
metadata, not a verified market-data adapter. Historical and OLS standard errors
assume IID observations; no HAC, ERP uncertainty propagation, model calibration or
prediction intervals are implemented. Frequency sanity checks do not prove
economic interval alignment. No multi-market/currency portfolio risk or corporate-
action reconciliation is supplied by deterministic FX sensitivity.

Responses contain complete resolved requests, selected evidence/revision snapshots,
source hashes, code hash, git/dirty identity when available and runtime versions.
There is no permanent run archive or save/export service, and hashes do not
preserve data. Replay through the API needs the original database references and
a compatible security master/environment; a later security currency change can
prevent replay, although the original response preserves its snapshot. Source
licensing/retention remains the owner's responsibility. Assumptions are not
automatically derived from attached evidence. User adoption of a model result
requires a deliberate user-view input/reference; no automatic promotion exists.

Existing single-owner shared-key limitations persist. Inputs/results/keys remain
in frontend memory and are cleared on navigation/disconnect. No optimizer,
ledger, TWR/XIRR, attribution, public publishing, automatic recommendations or
Black-Litterman was added. Representative production load/provider-contract
testing is not claimed. Build warnings about bundle size/browser support data
remain inherited limitations. No further master-brief change is proposed here;
the approved seven suggestions and A–D are now a dated permanent addendum,
preserving the original 37,623-byte prefix and all Phase 1–4 audits.

Phase 5 code/docs and the pre-existing Phase 4 changes remain uncommitted on
`phase-1-correctness` for owner review. **Stop before Phase 6.**

### Final completion and cleanup — 2026-09-10

After an interrupted finalization, the complete backend suite was rerun with
PostgreSQL: 345 passed, no skips, 98.36% coverage. All pre-commit hooks passed.
The desktop shell's child-process PATH selected system Python despite a shell
PATH override; prepending the project interpreter directory inside the Python
process before invoking pre-commit resolved the environment selection. No hook
or repository configuration was weakened. Dependency consistency also passed.

The synthetic browser schema
`browser_valuation_975b641a858c4705b9312e9bbb6f069e` was checked and removed; its
absence was verified. Backend/frontend test listeners were absent after the
interruption. The restarted disposable PostgreSQL was stopped cleanly;
`pg_ctl status` reported no server running and ports 5173, 8015 and 55439 had
no listeners. No user application data was removed.

Original master-brief prefix SHA-256 remains
`5615b5e7c4747a300c7fe54df06cd41995a2a5f04cd82a42d69e76ae4e380aea`.

Phase 5 files: new `backend/src/valuation/` and `backend/src/views/` packages;
new `backend/tests/test_valuation_{contracts,models,failures,api,postgres}.py`;
new `frontend/src/features/valuation/`; registration/navigation updates in
`backend/main.py` and `frontend/src/App.jsx`; forward-looking updates to
`AGENTS.md`, `README.md`, `MASTER_BRIEF.md`, `BUILD_PLAN.md`, `ARCHITECTURE.md`,
`METHODOLOGY.md`; this audit and the Phase 5 execution plan. The pre-existing
Phase 4 migration, thesis package/tests/UI and historical audit remain separate
uncommitted work. No Phase 6 implementation has begun.
