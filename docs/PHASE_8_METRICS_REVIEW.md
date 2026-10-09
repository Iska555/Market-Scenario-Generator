# Phase 8 realized-statistics implementation review

Date: 2026-09-15. This records the new Phase 8 metrics work prospectively; it does
not amend prior audits or claim that the complete performance feature is accepted.

## Scope and files

- `backend/src/performance/metrics.py`: pure `Metric`, `xirr`, and
  `realized_statistics` interfaces for the ledger report engine.
- `backend/tests/test_performance_metrics.py`: 22 offline analytical and boundary
  regression cases. The engine, API and interface have separate acceptance tests.

No existing simulation formula, accounting behavior or historical audit was
changed by this task. No provider or broker call is needed by these functions.

## Numerical conventions

The input is consecutive UTC calendar daily net simple returns, with 365 periods
per year. Missing dates, inconsistent lengths, non-finite returns, returns below
-100%, boolean returns and invalid assumptions are rejected. Empty records yield
typed `no_observations` metrics. Every result includes a nullable finite value,
an undefined reason when needed, and an observation count. Model validation rejects
non-finite values and contradictory value/reason states.

Annualized return is the geometric link raised to 365 divided by the daily return
count. It is undefined for fewer than 365 returns. Volatility uses sample standard
deviation times square root of 365. The annual effective risk-free rate is converted
to a daily effective rate. Sharpe uses arithmetic mean daily excess return over
sample daily volatility, annualized by square root of 365. Sortino uses the same
numerator over the population RMS of negative daily excess returns, including zero
contributions from other days. Calmar divides annualized geometric return by maximum
drawdown. These are descriptive realized-sample ratios, not confidence estimates.

Maximum drawdown is loss-positive, relative to running peaks including opening
unit value 1. Log wealth avoids overflow in long or extreme paths. Longest drawdown
includes peak-to-recovery duration for recovered episodes and peak-to-end duration
for open episodes. Recovery days is the largest completed peak-to-recovery duration
only when there is no unrecovered episode; otherwise it is undefined. No drawdown
has duration zero. A -100% daily return is accepted and wealth remains zero.

Best/worst month include only complete calendar months covered by daily return end
dates; their observation counts are the number of complete months. Hit rate counts
strictly positive days. Skewness and excess kurtosis use finite-sample unbiased
corrections, requiring at least three and four observations respectively. Constant
records have undefined standardized moments. Scaling centered observations before
forming powers avoids underflow in very small nonzero volatility. No tolerance
silently replaces a small nonzero denominator with zero. Floating-point overflow
in final statistics is reported as `non_finite_result`.

Realized daily VaR uses the linear interpolated empirical loss quantile at supplied
confidence. CVaR uses the worst exact `(1-confidence) × n` empirical observations,
including fractional mass at the boundary. It is not an inclusive average of all
observations beyond the interpolated quantile. Effective tail observations reports
that possibly fractional count. Loss-positive tails can legitimately be negative
in an all-gain record; no artificial zero floor is applied.

XIRR aggregates nonzero cash flows by calendar date using the accounting Decimal
context (120 significant digits), sorts dates and requires both signs. A schedule
with more than one sign change is reported as `non_conventional_cash_flows` rather
than selecting one of potentially multiple roots. A one-sign-change schedule can
run in either direction. Zero or same-date-cancelled schedules are undefined.
The exponent uses actual elapsed calendar days divided by 365, including leap-day
effects. Positive and negative discounted sums are compared in logarithmic space.
The root is bracketed over `log(1+r)` in **[-32, 32]**, approximately rates
**-0.9999999999999873 through 78,962,960,182,679.7**. A root beyond this numerical
interval is explicitly undefined. Bisection uses at most 120 iterations and stops
on equality or a floating-point interval that cannot shrink. Scale-invariance is
tested with amounts multiplied by 10^-500 and 10^500. Decimal values exceeding the
accounting context's supported arithmetic are rejected.

The dated exponent convention follows Microsoft's
[XIRR function reference](https://support.microsoft.com/en-us/excel/functions/xirr-function).
The root's parent task verified this primary reference; numerical root rejection
is this implementation's deliberately stricter policy, not a claim that Excel
uses the same root-selection policy. Flow-neutralized TWR belongs to the separate
ledger report engine and is not reconstructed from aggregate scenario statistics.

## Defect and verification record

There was no previous realized-performance module to repair. Initial tests failed
because `src.performance.metrics` did not exist. During new implementation review,
`Metric.defined_or_reason` initially allowed an empty reason alongside a defined
value; a failing regression was added and the validator was corrected. Strict
validation additionally prevents boolean metrics from being coerced to numbers.
Two first-pass test expectations were corrected against independent arithmetic:
the hand-computed four-observation excess kurtosis and an explicitly relative
tolerance for a volatility near 10^-149.

Verified locally on 2026-09-15:

- Scoped pytest: **22 passed** (1.07 seconds, no coverage gate on this scoped run).
- Scoped Ruff: **all checks passed**.
- Scoped mypy: **success, no issues in 2 source files**.

The root task owns whole-project coverage, integration tests and final acceptance.
Unfunded segments, missing marks, corrections, flow timestamps and ledger version
guards are responsibilities of that report engine. These functions do not add
benchmarks, factor attribution, confidence intervals, provider-derived prices,
broker integrations, or investment recommendations.

## Independent ledger-performance review — 2026-09-15

Reviewed the new performance `contracts.py`, `engine.py`, `routes.py`, engine/API
tests, and the accounting replay, supplied valuation and repository snapshot
dependencies. The scoped engine/API suite passed **27 tests** (3.75 seconds) before
the following additional adversarial cases were exercised. Passing existing tests
did not cover these defects. Findings were sent to the root implementer; this
reviewer did not edit those implementation files.

1. **P1 — `engine.build_report`: total-loss recovery can produce an invalid finite
   TWR.** Funded one-share fixture with daily supplied prices `100 → 0 → 110`
   returns final TWR **+10%**, although the final daily return is explicitly
   undefined as `zero_prior_unit_value`. The unit value recovers from zero and the
   cumulative output is independently calculated as `unit_value - 1`. A continuous
   unitized return cannot link across that undefined recovery. Preserve a final
   -100% when value remains zero; require a separate segment or an undefined TWR
   when capital value becomes positive after the zero-unit point. Add a regression
   for positive recovery after total loss, including a later external flow.

2. **P2 — `engine._marked_value` and the external-flow FX age check use a local
   cutoff date within the declared UTC calendar.** A USD deposit effective at
   `2025-01-03T00:30:00+04:00` is on January 2 UTC. With `max_mark_age_days=0`, a
   contemporaneous quote observed at `2025-01-02T20:00:00Z` is incorrectly stale:
   the report returns `missing_flow_fx` and no TWR, even though both instants share
   the same UTC date. Both cutoff dates need `.astimezone(UTC).date()`, just as the
   evidence dates already use. Add equivalent-offset regression fixtures for
   flow price and FX evidence and a genuinely stale UTC-day counterexample.

The existing snapshot route correctly obtains the portfolio lock before reading
rows, compares the current ledger version, and uses the shared private guard and
ValueError-to-422 repository boundary. Reversal restatement, sequencing trades
before same-timestamp flows, typed missing coverage and ordinary deposit/withdrawal
neutralization are covered by current tests. A dedicated FX-conversion-with-fee
performance reconciliation would further protect the existing internal/external
flow distinction. These observations do not replace whole-project verification
or PostgreSQL concurrency checks.
