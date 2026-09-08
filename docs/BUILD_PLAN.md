# Build plan — Phases 1–3

The owner authorized Phase 2 and then Phase 3 on 2026-09-08. Earlier checklists
remain as execution history. The current review boundary is after Phase 3 and
before Phase 4; the original master brief remains unchanged.

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
