# Benchmark comparison and realized active risk — Phase 9B

The owner authorized continuation on **2026-10-11** after Phase 9A acceptance.
This stage provides an explicit benchmark selection for an account/report and
compares recorded, flow-neutral portfolio returns with reviewed total-return
levels. It produces descriptive realized statistics, not expected returns,
investment decisions, alpha, factor inference or ex-ante tracking risk.
Acceptance belongs to the new [PHASE_9B_AUDIT.md](PHASE_9B_AUDIT.md).

## Selection, inputs and boundaries

In Performance, choose a funded opening close and reporting window, supply the
existing portfolio daily/pre-flow valuation evidence, and select **Compare with
a reviewed benchmark**. Prepare an empty benchmark template or import/paste
reviewed JSON. The template invents no index choice, level or provenance timestamp.
Selection is report-scoped for the chosen account, retained in a private download;
there is no durable database benchmark default or automatic provider connection.
A future portfolio-policy/default setting needs separate versioned persistence.

`POST /api/benchmark/portfolios/{portfolio_id}/comparison` accepts:

| Field | Meaning |
| --- | --- |
| `performance` | The unchanged Phase 8 PerformanceRequest: current ledger version, knowledge cutoff, ordered consecutive daily marks, active external-flow marks and explicit measurement conventions |
| `benchmark` | Identity/revision and reviewed dated total-return index levels |
| `include_contribution` | Boolean, default false; optional Phase 9A contribution from the same snapshot |

The route inherits private authorization, no-store response policy, completed-day
cutoffs and the locked portfolio snapshot. Its row lock remains held through
optional contribution and comparison. It adds no database tables, ledger writes,
provider calls, security registrations, migrations or public output. Benchmark
indices are evidence, not a fund/ETF falsely registered as an individual equity.

Benchmark `identity` fields:

| Field | Required meaning |
| --- | --- |
| `benchmark_id`, `revision`, `name` | Explicit stable chosen identity, reviewed evidence revision and display name; no global hardcoded index |
| `provider`, `methodology_reference` | Actual evidence provider/source and definition of the index methodology |
| `currency` | Exactly the account base currency; local/other-currency levels are rejected |
| `return_basis` | `gross_total_return` or `net_total_return`; price-only return is rejected |
| `hedging` | Explicit `unhedged`, `hedged` or `not_applicable` policy |
| `calendar`, `periods_per_year` | Exactly `UTC_calendar_daily` and 365 |
| `currency_policy` | Exactly `already_in_portfolio_currency`; this stage performs no FX conversion |
| `effective_from`, `effective_to` | This identity/revision applies throughout the entire requested window |
| `published_at`, `retrieved_at` | Aware publication and acquisition/knowledge times, ordered and no later than the report's knowledge cutoff |

Each `levels` row contains `date`, `level`, `observed_at`, `published_at`,
`retrieved_at` and `source`. Level is an exact nonnegative decimal string (existing
30-digit/10-decimal contract), or explicit null. Publication cannot precede
observation; retrieval cannot precede publication. Retrieval cannot exceed the
knowledge cutoff. Observation cannot exceed its UTC close, so future prices are
never used. Dates must be unique, ordered and within the exact portfolio window.
At most 3,661 level rows are allowed, matching the performance window cap.

`max_level_age_days` is explicit, defaults to **0**, ranges 0–30, and compares
the checkpoint date to the observation's UTC date. Missing/null/too-old levels
remain unavailable. Omitted dates are accepted as gaps; dates outside the selected
window, conflicting currencies/calendars, price-only series and future evidence
are rejected. No forward fill, interpolation, truncation to a date intersection,
or automatic trading-calendar resampling is performed.

Weekend/holiday levels require explicit reviewed inputs and, if using a prior
close, a deliberate age allowance and actual prior observation time. A manually
supplied repeated level is not independent proof of a contemporaneous executable
value. Matching date labels and currencies does not certify matched economic
closing times across markets. The user must review benchmark methodology/cutoffs,
FX/hedging basis, corporate-action adjustment and relevance to portfolio policy.

Publication/retrieval cutoffs identify evidence available by the requested knowledge
time, including explicitly selected later revisions. They do not certify that
today's reviewed revision was available at every past observation date. No
database revision registry, trusted external attestation or licensed-data archive
is implied by supplied identity strings and hashes.

## Return comparisons

Let L_t be the reviewed benchmark total-return level at the portfolio's daily
close t, and p_t the already calculated Phase 8 flow-neutral simple daily return
from close t−1 to t. Benchmark return is:

`b_t = L_t / L_(t−1) − 1`.

An interval beginning without outstanding portfolio units is unavailable for
comparison, even when Phase 8 can initialize its wealth chain and report a zero
return for the first funding interval. A partial first-funded day is not silently
matched to a whole benchmark day. The embedded Phase 8 return is preserved;
comparison's aligned portfolio return has `portfolio_not_funded_at_interval_start`.

Portfolio cash funding is neutralized by Phase 8 units; comparison never uses
raw NAV growth or XIRR. Booked dividends and costs remain in portfolio returns;
benchmark levels must already include index income/corporate-action treatment.
No dividend ledger entry is added to the benchmark level again.

For each exactly matched daily interval:

| Output | Formula and interpretation |
| --- | --- |
| `active_return` | `a_t = p_t − b_t`; arithmetic difference, displayed in percentage points |
| `relative_return` | `q_t = (1+p_t)/(1+b_t) − 1`; relative compounded wealth change, displayed as a percentage |

Over the selected window, R_p is independently computed Phase 8 TWR and R_b is
`L_end/L_start − 1`, requiring every benchmark checkpoint covered. Outputs:

| Output | Formula |
| --- | --- |
| `benchmark_return` | R_b |
| `cumulative_active_return` | `R_p − R_b`, percentage-point difference |
| `cumulative_relative_return` | `(1+R_p)/(1+R_b) − 1`, relative wealth return |

For complete funded positive-denominator intervals,
`product(1+q_t) = product(1+p_t)/product(1+b_t)`.
Daily arithmetic active returns neither sum nor compound to the cumulative return
difference. For portfolio wealth 100→102→106.08→112.4448 and benchmark
100→101→103.02→106.1106, R_p=12.4448%, R_b=6.1106%, the cumulative difference
is 6.3342pp, while relative wealth is `112.4448/106.1106 − 1`.

A selected window beginning before portfolio funding does not give the portfolio
and benchmark the same invested measurement period. Retain their independently
available returns, but withhold the cumulative comparison with
`portfolio_not_funded_at_opening`; select a reviewed funded opening close.
Whole-window cumulative comparisons also require every daily interval paired;
otherwise they are withheld with the applicable coverage reason. Independent
endpoint returns are retained even when this stricter comparison gate fails.
Undefined portfolio TWR does not erase an independently complete benchmark return,
and incomplete benchmark evidence does not erase independently complete portfolio
performance or contribution.

Zero opening benchmark level has no return denominator. A final zero level can
represent total loss (−100%); its relative wealth denominator is zero and therefore
undefined, while the arithmetic return difference can remain defined. A positive
level after zero in the same identity/revision is not accepted as a continuous
wealth chain: cumulative benchmark return is undefined with
`benchmark_recovery_after_zero_level`. Such evidence requires review, not an
invented reset. A subsequent interval starting at zero has no daily denominator.

## Realized sample statistics

Use exactly n paired finite p_t/b_t observations over the requested window.
All expected intervals must be available and n≥2 before any full-window active
statistic is published. A smaller complete-case sample is never silently substituted.
Every metric contains finite numeric `value` or null with an explicit `reason`,
plus its effective paired `observations`. Partial daily diagnostics remain visible.

Define means m_p, m_b, m_a and centered sample variance/covariance with denominator
`n−1`; A=365 calendar observations/year. The estimator uses stable sums of centered
values, retaining negative means/covariances and genuine zero variance.

| Statistic | Formula / units / interpretation |
| --- | --- |
| `mean_daily_active_return` | `m_a = mean(p_t−b_t)`; arithmetic average daily difference |
| `annualized_arithmetic_active_return` | `A × m_a`; scaled arithmetic active mean, not CAGR or a forecast |
| `annualized_tracking_error` | `sqrt(A) × sample_sd(a_t)`; realized annualized dispersion of active returns |
| `information_ratio` | `sqrt(A) × m_a/sample_sd(a_t)`; annualized arithmetic active mean divided by matching annualized tracking error |
| `beta` | `sample_cov(p,b)/sample_var(b)`; centered realized sensitivity to this selected benchmark, not causal factor exposure or forward market beta |
| `correlation` | `sample_cov(p,b)/(sample_sd(p) × sample_sd(b))`; signed descriptive co-movement |

Zero tracking error is a valid measured dispersion; information ratio is undefined
with `zero_tracking_error`, even if active mean is nonzero. Constant benchmark
returns make beta undefined with `zero_benchmark_variance`. Constant portfolio
returns and variable benchmark returns permit beta zero, but correlation is
undefined with `zero_portfolio_or_benchmark_variance`. No epsilon floor, positive
clamp, sign deletion or invented zero ratio is applied. Overflow/non-finite output
is typed undefined with `non_finite_result` rather than serialized NaN/Infinity.

The sqrt(A) scaling convention assumes stable variance and no serial correlation.
It is not market-calendar adjustment; weekends, stale marks, smoothing and serial
dependence can materially distort tracking error and information ratio. The annual
arithmetic mean is a mathematical scale, not a predicted or compounded one-year
return. Short samples can produce extreme beta/ratios/annualized values; sample
counts and an explicit warning below 365 paired observations are shown. Two points
can fit perfect sample correlation without establishing persistent skill.
No confidence interval, t-statistic, significance or alpha is claimed here; those
need the separate regression stage and its declared inference assumptions.

The definitions of active risk and information ratio are consistent with the CFA
Institute's [risk-adjusted performance measures case study](https://rpc.cfainstitute.org/-/media/documents/code/gips/case-study-risk-adjusted-performance-measures.pdf).
Benchmark suitability and measurement/appraisal limitations are discussed in its
[Portfolio Performance Evaluation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/portfolio-performance-evaluation)
and [Analysis of Active Portfolio Management](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/analysis-active-portfolio-management).
These provide context; the exact estimator, annualization and coverage rules above
define the implemented method. There is no GIPS-compliance claim.

## Replay, privacy and compatibility

The response retains complete performance, optional contribution, benchmark
identity/revision/levels, SHA-256 of canonical benchmark JSON, paired coverage,
daily comparisons, metrics, methodology and warnings. It is a private export;
locking/navigation/refresh and edits to any input clear all client results. Late
responses/imports cannot restore stale results. Keys remain memory-only and are
excluded from reports. A stale ledger version requires account reload/review.

```powershell
./backend/.venv/Scripts/python.exe scripts/replay_comparison.py path/to/private-report.json
```

`verify_comparison` validates embedded performance source/runtime/input/ledger
identity and every financial output, then benchmark evidence hash and contribution
setting, optional contribution replay, and the rebuilt complete comparison.
Changed identity/revision, levels, statistics, daily outputs or methodology fail.
This is consistency checking, not independent evidence authentication or broker
certification. A malicious party able to rewrite data and hashes is not defeated
by an unsigned self-contained report.

Adding Phase 9B changes the conservative exact-byte backend source identity.
Historical Phase 8/9A reports, audits and evidence are preserved. Retain their
compatible source/runtime, including the Phase 9A exact-source evidence bundle;
do not rewrite old hashes or histories. This phase retains its own accepted source
bytes/offline entry points alongside synthetic exports to protect exact replay
from Git line-ending conversion. Runtime versions must also match.

| Functions / transport | Tests |
| --- | --- |
| Benchmark identity/level/evidence validators | Gross/net basis, currency/calendar/age/knowledge cutoffs, duplicate/order/window and invalid decimal/provenance cases |
| `benchmark.engine.metric`, `active_statistics` | Hand-derived moments/beta/correlation/TE/IR, negative signs, zero denominators, small/gapped samples, overflow |
| `benchmark.engine.build_comparison` | Exact daily/cumulative return identities, flows/costs, independent missing results, funding/zero-wealth edge cases, snapshot consistency |
| `benchmark.replay.verify_comparison` | JSON roundtrip and altered evidence/revision/statistic/daily/methodology/setting rejection |
| `benchmark.routes.comparison` | Private API, actual migrated PostgreSQL all-table immutability, coherent lock/staleness/corrected result |
| Performance controller / benchmark inputs/results | Single request, explicit empty template, decimal/private transport, account/edit/lock/late-file/response clearing, safe errors, ratio/percentage-point/null presentation and browser acceptance |

Persistent benchmark defaults, automatic provider ingestion/FX conversion, ex-ante
tracking-risk contribution, rolling beta/capture, factor regression/alpha, Brinson,
fund support and publication remain subsequent work. Benchmark choice/relevance
is still the owner's explicit investment-policy judgment.
