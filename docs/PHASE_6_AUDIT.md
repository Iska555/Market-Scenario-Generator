# Phase 6 boundary audit — 2026-09-10

Authorization: owner approved Phase 5 continuation and requested Phase 6 plus a
permanent modern, soft, useful portfolio-platform UI/UX direction. This is an
append-only master-brief addition; Phase 1–5 audits remain historical records.
Work begins on `phase-1-correctness` with approved Phase 4–5 changes uncommitted.
Preserve them; no commit, deployment, push or Phase 7 work is implied.

| Original file / function | Classification | Phase 6 disposition |
|---|---|---|
| `risk/covariance.py:estimate_covariance`, `risk_contributions` | CORRECT AS IMPLEMENTED | Reuse annualized simple-return covariance and signed Euler contributions; preserve zero-risk undefined ratios |
| `portfolio/paths.py:build_portfolio_paths` | CORRECT AS IMPLEMENTED | Reuse costless daily/buy-and-hold scenario arithmetic; no realized holdings claim |
| `views/expected_return.py:user_view` | CORRECT AS IMPLEMENTED | Accept explicitly adopted one-year nominal total-return views; do not aggregate multi-year annualized equivalents as arithmetic means |
| `valuation/service.py:evidence`, `code_identity` | CORRECT AS IMPLEMENTED | Reuse private point-in-time evidence checks and proportional manifest identity |
| `risk/scenarios/service.py:draw_returns` | CORRECT AS IMPLEMENTED | Existing Gaussian/joint GMM remain separate conditional tools |
| Portfolio construction/constraints/comparison | NOT YET IMPLEMENTED | Add typed stateless private engine; current weights are owner-declared, not ledger-derived |
| Historical replay, joint block bootstrap, explicit security shocks | NOT YET IMPLEMENTED | Add offline supplied-data scenario families; do not invent factor-to-security mappings |
| `frontend/src/App.jsx` application shell | DESIGN DEBT | Simulator-centric navigation and decorative badge; introduce portfolio-platform structure and softer visual language |
| `frontend/src/App.css`, `assets/react.svg` | DESIGN DEBT | Inspect unused scaffold assets/styles; remove irrelevant branding only when verified unused |

## Acceptance design and conservative choices

One currency, long-only, fully invested securities; position bounds first. Cash,
sector/beta constraints, leverage and shorting remain unsupported and explicitly
rejected. Security order is stable UUID order from the submitted universe. Covariance
uses aligned supplied simple-return histories, sample or Ledoit-Wolf, with explicit
frequency, calendar, adjustment policy, observation window and annualization.

Optional adopted investor views must be one-year, nominal total returns in that
same currency and valuation context. Missing views leave aggregate expected return
undefined and do not block risk-only alternatives. Maximum Sharpe requires all
views and a feasible positive excess return; solver status, feasibility and
mathematical limitations are visible. Current/equal-weight references can violate
the proposed bounds and should display the violations instead of being rewritten.

Equal risk contribution is not approximate risk budgeting hidden behind a label:
only report a valid equal-contribution solution that satisfies the requested bounds;
otherwise report an explicit unavailable state. Signed contributions remain signed.
Weight concentration and risk concentration have distinct definitions.

Risk Lab additions resample/replay complete joint rows with explicit seed and
block length. Deterministic shocks are per-security simple returns, with a named
scenario and rationale; macro-factor transmission coefficients are deferred.

The entries above record the pre-implementation boundary. Final results follow.

## Implementation and review record — 2026-09-11

Phase 6 is implemented locally. The owner-approved 2026-09-10 UI direction is
appended to the master brief and reflected in AGENTS.md. The original brief and
Phase 1–5 audits remain historical records. No Phase 7 work is implemented.

| File / function | Final disposition and verification |
|---|---|
| `portfolio/construction/contracts.py:ConstructionRequest.coherent`, `JointHistory.aligned` | IMPLEMENTED: ordered IDs, interval/frequency/knowledge checks, feasible common position bounds, explicit compatible one-year investor views; invalid-domain tests |
| `portfolio/construction/algorithms.py:minimum_variance`, `maximum_sharpe`, `risk_parity` | IMPLEMENTED: convex alternatives with convergence, feasibility and optimality/equal-risk checks; diagonal analytical identities, corner solutions, scale invariance, singular/zero covariance, failed/spuriously successful solver tests |
| `portfolio/construction/analytics.py:construct`, `risk_report` | IMPLEMENTED: annualized covariance/correlation, signed Euler risk and return contributions, separate concentration measures, explicit unavailable candidates/null ratios; reconciliation tests |
| `portfolio/construction/service.py:evaluate_construction`, `routes.py` | IMPLEMENTED: private stateless evidence resolution, exact adopted views and replay manifests; authentication, missing/cross-currency evidence, replay, no-store and read-only PostgreSQL tests |
| `risk/scenarios/historical.py:joint_blocks`, `evaluate_scenario` | IMPLEMENTED: complete replay, seeded non-circular joint moving blocks and explicit security shocks; exact arithmetic, dependence/order, repeatability, full-population tails and bounded allocation tests |
| `risk/scenarios/historical.py:evaluate_scenario` complete-loss arithmetic | FIXED DURING REVIEW: normalized three-security weights could sum slightly above one, producing terminal wealth `-2.22e-14` for a 100-unit complete loss. A failing regression reproduced it; summing nonnegative gross wealth gives exactly zero, with return -1 and drawdown 1 |
| `historical.py` methodology and `StressWorkspace.jsx` bootstrap acknowledgement | FIXED DURING REVIEW: no-recentering was incorrectly described as exact empirical-mean preservation. Non-circular blocks overweight interior observations; text now explains endpoint weighting and random sampling can change the sample mean |
| `historical_contracts.py:StressResult`, `StressWorkspace.jsx:StressResults` | IMPLEMENTED: typed null/reasons, actual observation-period horizon, Calmar defined/total paths and fractional effective tail count; visible counts are formatted without changing server values |
| `frontend/src/App.jsx`, `components/PlatformShell.jsx`, `index.css` | IMPLEMENTED: text identity, softer neutral/teal surfaces, rounded controls, grouped task navigation, construction entry, skip link, responsive layout and theme control. Removed unused scaffold App.css and favicon reference; no fabricated holdings/NAV |
| `features/construction/*`, `features/stress/*` | IMPLEMENTED: registered securities, explicit supplied inputs, comparisons and contribution tables, advanced history/provenance disclosures; memory-only keys, stale-response guards, edit/disconnect/unmount invalidation and undefined-value tests |

Independent construction review reported no actionable findings. Its deterministic
120-case two-asset SPD/bounds probe reconciled minimum variance and available
maximum-Sharpe results to dense 20,001-point grids; available ERC results satisfied
the 1e-6 equal-contribution tolerance. A separate stress review identified the
bootstrap wording defect above; that review ended at the tool usage limit. The
parent verified and repaired that finding and completed the remaining local checks.

## Verification evidence

- Full offline backend run with actual isolated PostgreSQL 17.11: **424 passed,
  no skips**, **98.53%** aggregate statement/branch coverage (95% gate).
  Construction analytics and historical scenario domain each reached 100%; new
  solver module 98.68%. New construction PostgreSQL test compares all migrated
  table contents before/after evaluation and replay, preserving exact Decimal facts.
- Ruff check and format over `backend scripts`: passed. Mypy: passed across 84
  source files. Configured pre-commit hooks: all passed.
- Frontend: **60 tests passed**, ESLint and production build passed. Existing
  build warnings remain: old caniuse-lite dataset and roughly 673 kB JS bundle
  (199 kB gzip). No dependency refresh or hosted-performance claim is implied.
- Browser against a disposable migrated PostgreSQL schema: construction risk-only
  comparison completed with undefined return views and available risk alternatives;
  reference/contribution tables and covariance disclosure rendered. A 60/40 shock
  of -20%/-10% reconciled to -16% and 8,400 from 10,000. Seeded bootstrap rendered
  100 full-population scenarios over six monthly observations, typed undefined
  Calmar with 93/100 defined paths, tail confidence/effective count and corrected
  mean-policy disclosure. Changing assumptions cleared prior results. Shell and
  narrow-layout navigation were visually inspected. Automated tests cover explicit
  view adoption and privacy races; not every permutation was manually browser-tested.
- One intermediate run encountered a stopped disposable PostgreSQL process after
  session interruption. Restarting it in a maintained local session and rerunning
  the complete suite produced the passing result above. This was test-infrastructure
  unavailability, not a silently skipped database gate.

## Assumptions and remaining limitations

All new analyses are stateless conditional experiments with owner-declared weights,
supplied data and explicit inputs. They fetch no providers and do not save new
archives or reports. Current registry snapshots are not historical identifier/FX
or corporate-action reconciliation. Alignment/adjustment provenance is asserted
by the supplier; it cannot be independently certified by these endpoints.

Supported constraints are fully invested, long-only, common position minimum/maximum
in one currency. Cash, leverage, shorts, sector/beta constraints, Black-Litterman,
efficient-frontier visualization, benchmark-relative/factor risk, exact macro
transmission, ledger, TWR/XIRR, attribution and publication are deferred. No return
model is automatically adopted and no portfolio order or BUY/HOLD/SELL is generated.

Maximum Sharpe and ERC conservatively reject singular/ill-conditioned covariance.
ERC is unavailable when exact equal risk conflicts with the bounds. Current/equal
references may violate proposed bounds and remain labeled as such. Historical
complete-loss observations are explicitly rejected by the positive-path engine;
deterministic shocks support complete loss. Historical covariance IID annualization
and bootstrap model/parameter uncertainty remain assumptions, not calibrated claims.
Mean/variance estimates and more paths do not imply a forecast or eliminate model risk.

The current UI uses explicit JSON for advanced supplied histories, not a data-import
wizard, and retains no private state after leaving a workspace. This is an initial
modern platform design, not a complete portfolio-accounting dashboard. Tests use
synthetic/offline data, not provider production contracts or hosted load tests.

Changes remain uncommitted on the existing branch; no push, hosted CI run or
deployment was performed. Stop for owner review before Phase 7.

Final cleanup: the disposable browser schema and temporary smoke helper were
removed, and the local PostgreSQL verification server was shut down gracefully.
The original master brief's first 37,623 bytes still hash to
`5615b5e7c4747a300c7fe54df06cd41995a2a5f04cd82a42d69e76ae4e380aea`.
Final frontend recheck after display formatting: 60 tests, lint and build passed;
Ruff check/format and mypy were rechecked successfully. No test service is a deployment.
