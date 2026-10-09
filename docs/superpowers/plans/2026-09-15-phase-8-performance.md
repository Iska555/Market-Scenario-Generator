# Phase 8 — performance measurement implementation plan

**Goal:** Measure realized portfolio performance from the existing immutable ledger and explicit supplied valuation evidence.

**Authorization:** The owner requested continuation into Phase 8 on 2026-09-15. This prospectively supersedes the stop-before-8 gate. Preserve the original brief, audits and existing dirty checkout. Stop before Phase 9. No commit, deployment, broker integration or provider download is included.

**Architecture / design:** Add a read-only private performance domain, using ledger replay and supplied raw prices/FX. Daily unit values neutralize external flows at their actual ledger timestamp and sequence. Require daily UTC closing valuations plus pre-flow marks; do not approximate flow timing or silently carry marks forward. Opening value and final value anchor period XIRR; deposits are investor outflows and withdrawals investor inflows. Missing coverage yields typed undefined results. Preserve the complete replay input and visible ledger records in a returned manifest; no licensed-data archive.

**Decision:** Continue implementation under the owner's explicit phase authorization and canonical specification. Normal engineering choices below do not require a second authorization gate. Independent tasks use the subagent-driven-development workflow; pre-existing changes remain uncommitted and untouched outside necessary integration points.

## Contracts and conventions

- Endpoint: POST `/api/performance/portfolios/{portfolio_id}/report`, existing private key guard and no-store responses. No writes.
- Request: `known_at`, `expected_version`, ordered `daily_marks` (date, prices, fx), `flow_marks` (transaction_id, prices, fx), annual effective `risk_free_rate` default 0, `confidence` default .95, `max_mark_age_days` default 3. Explicit fixed `calendar=UTC_calendar_daily`, `price_convention=unadjusted`, `periods_per_year=365`. At least two consecutive dates, at most 3661. Closing cutoff is UTC 23:59:59.999999. Raw quotes only, dividends come from the ledger. Source, observed time, currency and stable security ID required on each quote.
- Opening date is a valuation baseline. External flows strictly after that close through final close receive flow-boundary valuations. Inception labels require no active ledger history before opening, not a guessed inception date. A funded opening NAV starts with unit price 1. First subsequent funding may establish units at 1; flat/unfunded intervals are undefined. Full withdrawal preserves the final unit price; loss to zero cannot be resurrected by new capital without a separate segment.
- All flows at a shared timestamp use ledger sequence. Securities, cash and net booked fees/dividends remain ledger-defined. Foreign flows require explicit contemporaneous FX evidence. Corrections follow the existing known-at semantics and invalidate old-version requests.
- Missing daily/flow valuation coverage stops unitization for the affected report, rather than linking across a gap. XIRR can still be computed if opening/final NAV and all external-flow FX are available. No partial NAV is a complete NAV.
- Decimal unitization and ledger valuation use the accounting context. Statistical return calculations use finite floats with typed non-finite/undefined outcomes. Dated XIRR uses actual days / 365, aggregates same-date amounts, and refuses non-conventional multiple-sign-change schedules rather than selecting an arbitrary root. Unique conventional roots are bracketed in log(1+r) space with explicit finite numerical bounds.
- Daily, monthly, quarterly, annual and full-window geometric links are backend outputs. Partial calendar periods are labeled. Annualized return is not shown for windows shorter than 365 days. Ratios/tails describe realized daily net returns and their sample limitations; no confidence intervals or benchmark claims are invented.

## Task 1 — realized statistics and XIRR

**Files:** `backend/src/performance/metrics.py`, `backend/tests/test_performance_metrics.py`.
**Interfaces:** `Metric(value: float | None, reason: str | None, observations: int)`, `xirr(flows: list[tuple[date, Decimal]]) -> Metric`, `realized_statistics(dates: list[date], returns: list[float], risk_free_rate: float = 0, confidence: float = .95) -> dict[str, Metric]`. Dates are consecutive daily return end dates. Daily frequency fixed 365/year. Include annualized_return, annualized_volatility, sharpe, sortino, calmar, max_drawdown, longest_drawdown_days, recovery_days, best_month, worst_month, hit_rate, skewness, excess_kurtosis, realized_var, realized_cvar, effective_tail_observations. Mean excess returns for Sharpe; sample volatility; downside population RMS of min(excess,0); unbiased skew/kurtosis where defined. Drawdown starts at unit value 1; longest episode includes unrecovered duration; recovery_days is maximum peak-to-recovery duration only when all episodes recovered, else null/unrecovered_drawdown. Best/worst month use only complete calendar months. Tail uses linear quantile and exact fractional empirical mass. Return -100% is allowed. No near-zero denominator silently coerced to zero.

- [ ] Write analytical tests: dated 10% annual XIRR, negative return, same-date cancellation, multiple-sign-change rejection, root outside supported bounds, cash-flow scale invariance; zero excess Sharpe, known drawdown 1→1.2→.9→1.1, constant returns, short records, complete/partial months, fractional tail atoms.
- [ ] Observe failing tests, implement pure functions, run scoped tests/lint/types; report exact evidence and numerical limits.

## Task 2 — ledger-derived report

**Files:** `backend/src/performance/contracts.py`, `engine.py`, `routes.py`, `__init__.py`; `backend/main.py`; performance engine/API tests.
- [ ] Add strict request/response and analytical failing tests for neutral deposits, withdrawals, intraday ordering, fees/dividends/FX, missing marks, timestamps/staleness, corrections, dates/version, inception versus selected period.
- [ ] Reuse existing replay/valuation for each checkpoint. Derive unit issue/redemption at pre-flow value; geometric links and typed results. Include inputs, ledger record IDs/hashes/full visible rows, dependency/code identity and methodology in manifest.
- [ ] Integrate guarded no-write route with coherent locked portfolio snapshot; test auth, errors, no-store, old ledger/API behavior.

## Task 3 — private Performance workspace

**Files:** `frontend/src/features/performance/` plus `App.jsx` and `PlatformShell.jsx` integration and tests.
- [ ] Add controller tests for shared session, lock/late responses, account/version changes, exact decimal evidence, failure clearing stale report. Use real backend contract.
- [ ] Build account/window selection, supplied evidence workflow and result display with TWR/XIRR side by side, dated unit-value/daily history, linked period selection, realized stats, missing-data explanations and replay download. Keep technical evidence/settings progressively disclosed and never show fake records. No extra key field or browser financial calculations.
- [ ] Inspect empty, populated and error states at desktop/mobile; verify refresh/lock clears results.

## Task 4 — documentation and acceptance

- [ ] Update current README/architecture/phase status prospectively; write PERFORMANCE.md formulas, references, failure conditions, price/FX calendar rules and PHASE_8_AUDIT.md with review findings and exact limitations. Preserve all existing historical artifacts.
- [ ] Independent scoped review, repair with regressions, then full pytest/ruff/mypy/frontend tests/lint/build. Exercise real PostgreSQL checks if available; explicitly record skips if unavailable. No production claims from synthetic fixtures.
- [ ] Report evidence and stop before Phase 9.
