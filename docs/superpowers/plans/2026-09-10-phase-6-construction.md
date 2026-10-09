# Phase 6 construction and platform design plan

**Goal:** Implement the canonical Phase 6 boundary and approved frontend direction;
stop before Phase 7. Owner authorizes autonomous continuation within this scope.

**Architecture:** Typed `portfolio/construction` contracts, numerical algorithms,
analytics and private routes/service. Reuse research identity and Phase 5 user views,
without automatic model adoption. Add supplied-history scenario families under
`risk/scenarios`. Create a modern application shell and construction workspace;
financial calculations remain server-side. Stateless reports, no ledger or archive.

- [x] Inspect prior phases and record boundary audit before implementation.
- [x] Append permanent owner-approved UI/UX direction and Phase 6 authorization.
- [x] Define typed joint history, adopted views, constraints, reports and manifests.
- [x] Add failing analytical/invariant tests; implement covariance risk, comparisons,
  minimum variance, maximum Sharpe and exact equal-risk contribution with explicit
  failure/feasibility states. Test degeneracy, incompatible horizons and constraints.
- [x] Add private security/evidence validation, replay metadata, API and PostgreSQL tests.
- [x] Add historical replay, joint moving-block bootstrap and deterministic shocks
  with full-population statistics, exact arithmetic/seed tests and clear boundaries.
- [x] Implement soft, modern product shell and focused construction/scenario flows;
  test stale/private state, null semantics, response-only calculations and navigation.
- [x] Update methodology and architecture with exact formulas/assumptions/limits.
- [x] Run full pytest/coverage with PostgreSQL, Ruff, mypy, frontend tests/lint/build;
  browser check, independent review, resolve findings, finalize audit and stop.

Use the subagent-driven-development workflow for independent numerical, UI and
scenario-family tasks, with explicit file ownership. Parent owns shared contracts,
service/API integration, documentation and final verification. Preserve existing
uncommitted work and historical audits; do not create a fresh checkout that loses
approved Phase 4–5 dependencies. Leave changes uncommitted under current workflow.
