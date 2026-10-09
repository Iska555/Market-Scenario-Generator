# Build plan — Phases 1–5

The owner authorized Phase 2 and then Phase 3 on 2026-09-08. Earlier checklists
remain as execution history. The owner authorized Phase 4 on 2026-09-09 after
committing Phases 1–3 as `88f4390`. On 2026-09-09 the owner approved Phases 1–4
for continuation and authorized Phase 5. The current review boundary is before
Phase 6. The original master brief is preserved with a dated approved addendum;
the completed phase checklists below remain execution history.

## Phase 1 (completed)

**Goal:** Repair the current simulator under `docs/MASTER_BRIEF.md`; stop after
Phase 1 and audit. Existing branch `phase-1-correctness` is the task checkout.

**Architecture:** Keep current endpoints with a deliberately versioned v3 response.
Use typed API contracts, data validation/provider boundary, portfolio arithmetic,
risk statistics/covariance, and a scenario service. No later domain scaffolding.
Preserve the older user-edited plan as historical context.

**Decisions:** Drift selection is required (`zero_log_drift` or
`historical_diagnostic`); no expected-return forecasting model. Support daily and
buy-and-hold only. Risk-free annual effective rate defaults to an explicit 0%.
Ledoit-Wolf default, sample alternative. Full joint GMM with disclosed fitted and
applied means. No stochastic path demeaning. Long-only, fully invested, costless,
single valuation currency with no FX conversion. All path arrays include day zero.

- [x] Inspect all source and configuration; document original defects.
- [x] Add failing analytical and regression tests: weighted one-period arithmetic,
  drifting holdings, day-zero drawdown, zero-excess Sharpe, tail quantiles, PSD
  handling, regime sampling, seed isolation, preserved extreme moves.
- [x] Repair RNG/model/data modules and create `src/risk/` and `src/portfolio/`
  functions; run their tests before integration.
- [x] Move request/response schemas into `src/api/` and orchestration into
  `src/risk/scenarios/service.py`; validate input and bound tensor memory. Add
  endpoint tests with a synthetic price provider, no network.
- [x] Update frontend to consume only server statistics and histogram. Expose
  assumptions and signed risk contribution, remove sample-based tooltips. Test
  presentation with intentionally misleading chart samples.
- [x] Update methodology, architecture, brief suggestions, README and CI. Run
  pytest, ruff, mypy, frontend tests/lint/build. Benchmark a stated workload without
  enforcing a hardware-dependent two-second claim.
- [x] Review repair outcomes and limitations against each Phase 1 done criterion;
  report and stop.

Each calculation change starts with an independently hand-derived expected result
or a test of a mathematical invariant, then implementation and regression checks.
Undefined ratios return null, never fabricated zero or infinity. Do not equate
zero log drift with zero expected simple return or risk neutrality.

## Phase 2 — methodology and tests

Execution plan: [2026-09-08-phase-2-methodology-tests.md](superpowers/plans/2026-09-08-phase-2-methodology-tests.md).

- [x] Inspect inherited tests, quantitative functions, methodology and tooling.
- [x] Expand known-answer tests for model moments, covariance, tail atoms,
  numerical boundaries and deterministic end-to-end scenarios.
- [x] Reproduce and fix invalid histogram population acceptance.
- [x] Enforce backend branch coverage, align pre-commit with CI, retain pinned
  dependencies and save hosted coverage/environment artifacts when CI runs.
- [x] Document all quantitative functions, formula windows, tests and limitations.
- [x] Finish verification and record Phase 2 acceptance in `PHASE_2_AUDIT.md`.
- [x] Stop for owner review before Phase 3.

## Phase 3 — fundamental research data model

Execution plan: [2026-09-08-phase-3-research.md](superpowers/plans/2026-09-08-phase-3-research.md).

- [x] Implement the 28-metric catalogue and tested Decimal calculation primitives.
- [x] Add stable equity IDs, explicit reporting/knowledge timestamps and provenance.
- [x] Add SQLAlchemy/PostgreSQL persistence and Alembic migration with immutable facts.
- [x] Add atomic repeatable imports and point-in-time revision selection.
- [x] Expose typed private research API while preserving simulator behavior.
- [x] Verify actual PostgreSQL precision, migrations and repository behavior.
- [x] Document setup, API use, calculation meanings and temporal limitations.
- [x] Complete full checks and final audit; stop before Phase 4.

## Phase 4 — thesis system

Execution plan: [2026-09-09-phase-4-thesis.md](superpowers/plans/2026-09-09-phase-4-thesis.md).

- [x] Add typed thesis identities, immutable complete revisions and manual reviews.
- [x] Add private routes and PostgreSQL migration with concurrent edit protection.
- [x] Add a focused thesis workspace with visible assumptions and version history.
- [x] Verify PostgreSQL guarantees, API and browser workflows and inherited checks.
- [x] Document assumptions, audit evidence and limitations; stop before Phase 5.

## Phase 5 — expected-return and scenario model (authorized 2026-09-09)

Execution plan: [2026-09-09-phase-5-valuation.md](superpowers/plans/2026-09-09-phase-5-valuation.md).
The [Phase 5 audit](PHASE_5_AUDIT.md) records implementation and verification
evidence; authorization and this checklist do not establish completion.

- [x] Adopt the owner's seven suggestions and permanent rules A–D in the dated
  master-brief addendum, preserving original text and historical audits.
- [x] Define the return contract before multiple models: explicit horizon,
  annualized/cumulative semantics, price/total and nominal/real bases, currency,
  model provenance, uncertainty and typed undefined states.
- [x] Keep research assumptions, valuation results, security scenarios and
  investor expected-return views distinct. Support explicit user views without
  automatically promoting any model output into construction.
- [x] Implement historical diagnostics with uncertainty, transparent CAPM, a
  tested fundamental model, bear/base/bull scenarios with optional explicit
  probabilities, and one useful reverse-valuation inversion.
- [x] Link supplied inputs to eligible research observations and exact thesis
  revisions under `as_of`/`known_at`; return proportionate replay manifests.
- [x] Add a focused private valuation workspace with visible assumptions,
  horizon/currency/return basis, uncertainty and separate model/view meanings.
- [x] Reconcile every quantitative function with analytical or invariant tests;
  cover invalid domains, numerical failures, temporal leakage, API compatibility,
  probabilities absent/present, and presentation of undefined/stale results.
- [x] Run offline pytest with the existing branch-coverage gate, Ruff/format,
  mypy, frontend tests/lint/build, and applicable PostgreSQL verification.
- [x] Match methodology to implementation; record limitations, data/provider
  assumptions, local and hosted verification, and deployment status in the audit.
- [x] Stop for owner review before Phase 6.

The Phase 5 design uses a stateless private calculation API with explicit inputs
and evidence manifests. It adds no persistence or automatic provider calls.
Data hashes identify inputs; they do not archive those inputs. Do not introduce
licensed-data retention without considering the provider's constraints.

Out of scope: portfolio optimization/efficient frontier/risk parity, ledger,
broker imports, TWR/XIRR, factor or performance attribution, public publishing,
automatic BUY/HOLD/SELL, and Black-Litterman implementation. Calendar/FX and
corporate-action reconciliation remain prerequisites for future multi-market
and multi-currency portfolios. Do not expand Phase 5 into those future systems.

Every future phase must define reconciliation identities, numerical failures,
API compatibility, reproducible checks, unsupported functionality, deployment
boundaries and data/provider assumptions. Provider-dependent production claims
require appropriate provider contract tests and representative memory/load tests.
# Phase 6 — construction, supplied stress and modern platform UI

Authorized 2026-09-10; next owner review is before Phase 7. The earlier phase
checklists below are historical boundaries. Execution plan:
[Phase 6 plan](superpowers/plans/2026-09-10-phase-6-construction.md).
Verification and remaining limitations: [Phase 6 audit](PHASE_6_AUDIT.md).

- [x] Preserve the original master brief and append Phase 6/UI authorization.
- [x] Define ordered joint-history, explicit one-year views and common bounds.
- [x] Implement current/equal references, minimum variance, maximum Sharpe and
  exact equal-risk contribution with checked numerical failure states.
- [x] Show volatility, covariance/correlation, signed contributions and distinct
  weight/risk concentration, with typed undefined values.
- [x] Add private stateless evidence/manifests and actual PostgreSQL verification.
- [x] Implement supplied historical replay, joint block bootstrap and security shocks.
- [x] Finish frontend/browser verification and independent review, then finalize audit.
- [x] Stop before Phase 7; no ledger, accounting, attribution or publication.


# Phase 7 — immutable transaction ledger

Authorized 2026-09-12. The earlier stop-before-7 checklist records its original
review boundary. Current gate: stop before Phase 8. Implementation and acceptance
record: [Phase 7 audit](PHASE_7_AUDIT.md); exact contract: [ACCOUNTING.md](ACCOUNTING.md).

- [x] Add exact contracts, cash/holdings replay and correcting reversals.
- [x] Add private atomic persistence, idempotency, PostgreSQL immutability and concurrency tests.
- [x] Add manual and reviewed canonical CSV previews/saves; defer native Lightyear schema until a fixture exists.
- [x] Add supplied-price/FX valuation with complete-coverage NAV and explicit missing values.
- [x] Integrate a private ledger workspace with safe retries, historical details and in-memory drafts.
- [x] Run backend/PostgreSQL and frontend tests, lint, type checks and build.
- [x] Complete browser acceptance and final audit disposition.

After this phase, the canonical roadmap has three phases: 8 performance
measurement (TWR/XIRR), 9 attribution, 10 public track record. A fully ready
personal platform also needs actual broker-data reconciliation, any required fund
or corporate-action support, durable hosting/backups/restore and operational
acceptance. Phase count is not a guarantee of readiness for every instrument.

## Phase 8 — realized performance (authorized 2026-09-15)

The owner requested continuation into Phase 8, prospectively superseding the
stop-before-8 gate above. Current gate: stop before Phase 9. Detailed execution
plan: [Phase 8 plan](superpowers/plans/2026-09-15-phase-8-performance.md).
Formulas/contracts: [PERFORMANCE.md](PERFORMANCE.md). Verification and remaining
limits: [Phase 8 audit](PHASE_8_AUDIT.md). Prior audit and phase boundary records
remain intact.

## Phase 8 closeout — approved and verified 2026-10-09

The owner approved the recommended proceeding procedure and selected acceptance
and reproducibility closeout. This prospective record preserves the earlier phase
gates in their original context. [Phase 8 audit](PHASE_8_AUDIT.md) records the fresh
local acceptance, repairs, evidence and remaining operational boundaries.

- [x] Restore the environment, execute repeatable bootstrap/verification scripts
  and capture the resolved Windows/Python 3.12 environment.
- [x] Add actual source/runtime identity and offline report replay with modification
  rejection and historical-cutoff regression coverage.
- [x] Verify PostgreSQL read-only results, coherent locking and stale-version handling.
- [x] Run the complete backend suite without skips, frontend tests/lint/build,
  configured quality checks and populated/missing/corrected browser cases.
- [x] Create the previously missing Phase 8 audit and append the approved sequence
  in suggestions, preserving the master brief and existing audit/review contents.

The next approved stage is Phase 9A reconciled position contribution, followed by
benchmark/active-risk analysis, factor regression and Phase 10 publication
acceptance. Each requires its own prospective plan and evidence. Ledger-to-
construction integration and deliberate fund/ETF support remain priorities before
real-account readiness; acceptance here does not implement those extensions.
