# Realized performance — Phase 8

The owner authorized Phase 8 on 2026-09-15. Performance is private, read-only and
derived from recorded ledger events plus explicitly supplied valuation evidence.
It is separate from expected-return views and simulated risk. Phase 9 attribution
and Phase 10 publishing remain outside scope.

## Workflow and data boundary

Unlock the private Investment Management Workspace, choose **Performance**, an
account and a reporting window. The opening date is a closing valuation baseline;
daily returns begin on the following date. Choose an explicit knowledge cutoff.
Import reviewed valuation evidence, or prepare an empty template from the account's
actual transaction IDs. Fill required prices and FX before calculating. Base-currency
cash needs no price quote or FX rate. Evidence and reports stay in memory until
explicitly downloaded; locking, navigation and refresh clear private client state.

The report presents total-window TWR beside annualized XIRR, linked calendar
returns, daily NAV and units, descriptive realized statistics and a replay download.
It never treats a missing value as zero. Changing inputs removes the previous
report. A ledger-version conflict requires reloading and reviewing the evidence.

No automatic broker/provider connection, benchmark, tax calculation, fund support,
performance attribution or public publication is added. The existing registry
accepts individual equities; unsupported corporate actions and instruments must be
reconciled in an explicit future extension. Lightyear remains the intended account,
not an integrated live broker.

## Evidence, currency and calendar

`POST /api/performance/portfolios/{portfolio_id}/report` uses the existing
`X-Research-Key` authorization and a locked, coherent ledger read. It creates no
database rows. Successful responses use `Cache-Control: no-store`. Request fields:

| Field | Meaning |
| --- | --- |
| `expected_version` | Current ledger version; conflicts reject the request |
| `known_at` | Aware timestamp; corrections and records known after it are excluded |
| `daily_marks` | Ordered consecutive dates, each with `prices` and `fx` arrays |
| `flow_marks` | Price/FX arrays keyed by active deposit/withdrawal transaction ID |
| `risk_free_rate` | Annual effective decimal rate, default 0 |
| `confidence` | Realized one-day empirical loss-quantile confidence, default 0.95 |
| `max_mark_age_days` | Explicit permitted quote age in UTC calendar dates, default 3, range 0–30 |
| `calendar` | Fixed `UTC_calendar_daily` |
| `periods_per_year` | Fixed 365; deliberately different from the 252-observation equity Risk Lab |
| `price_convention` | Fixed `unadjusted`; total-return-adjusted input is rejected |

A price contains stable `security_id`, `currency`, `price`, `observed_at` and
`source`. FX contains `currency`, `rate`, `observed_at` and `source`; the rate is
base-currency units per one unit of the local currency. Amounts must be exact
decimal strings (up to the existing accounting contract's 30 digits / 10 decimal
places). Quotes are never downloaded, imputed or automatically carried forward.

Every UTC date, including weekends, needs an explicit checkpoint. A daily close
is `23:59:59.999999Z`. A flow checkpoint uses its actual timestamp and ledger
sequence. Quote timestamps cannot exceed their checkpoint or the knowledge cutoff.
Older quotes within the declared age limit remain supplied evidence, not proof of
an executable price at the checkpoint; stale evidence produces undefined coverage.
The default three-day limit allows deliberate prior-close inputs over weekends,
but does not validate market-calendar alignment or price quality.

Prices are unadjusted quotes because cash dividends already enter the ledger.
Using dividend-adjusted prices would double-count income. The API can validate
the declared convention, not independently certify the provider's adjustment
policy. Splits, in-kind transfers and other unsupported actions must not be
disguised as returns or relabeled securities.

At a checkpoint, portfolio NAV is the sum of ledger cash and equity market values,
translated with that checkpoint's supplied FX. All required coverage is necessary;
a partial NAV never becomes a total. The existing accounting domain performs this
calculation. Moving-average cost is not used to infer market prices or returns.

## Daily time-weighted return

Let `U` be outstanding performance units, `V⁻` the marked NAV immediately before
an external flow, `C` the signed flow in base currency (deposit positive), and `P`
the unit value. For funded periods:

```text
P = V⁻ / U
ΔU = C / P
U_after = U_before + ΔU
V_after = V⁻ + C
P_after = P_before
```

The final equality is the reconciliation identity: funding itself changes units,
not performance. A complete withdrawal explicitly redeems all units to avoid a
rounded residue. Intraday events before a flow are included, events after it are
excluded, and same-timestamp events follow ledger sequence.

An existing funded opening NAV starts at unit value 1 with `U = NAV`. First funding
after an unfunded opening similarly establishes units at 1. With valid coverage,
daily closing `P_t = NAV_t / U_t`, daily simple return is `P_t/P_(t-1) - 1`, and
geometrically linked TWR is `product(1+r_t)-1`. The full-window return is the final
unit value divided by the initial unit value, minus one. Monthly, quarterly and
annual links group daily return end dates; incomplete calendar buckets are
explicitly marked partial. Since-inception labeling requires the baseline to
precede all active recorded economic history. Otherwise the label is selected period.

Trades, booked net dividends, trading fees, standalone fees and FX conversions
are internal events. They can affect NAV and performance; they never become
external investor cash flows. Foreign deposits/withdrawals need explicit FX at
their event; an internal FX conversion is not an investor contribution.

No approximation substitutes for missing pre-flow valuation. Missing daily or
flow coverage invalidates continuous unitization from that point. Known later
NAVs may still be shown, but they do not repair the gap. Entirely unfunded days
have no daily return. A full withdrawal retains the last unit value; later funding
can issue at that value. Loss to zero is different: subsequent recovery or funding
cannot silently restart a continuous return segment. New-period analysis requires
an explicit new opening baseline. Empty accounts have no invented zero return.

Unit arithmetic uses the accounting domain's explicit 120-digit Decimal context;
recurring division is rounded, not described as exact rational arithmetic. Returned
NAV, units and unit values preserve decimal strings. Statistical rates use finite
floating point; no financial calculations occur in the browser beyond formatting.

The flow-boundary approach follows the rationale in the GIPS
[calculation methodology guidance](https://www.gipsstandards.org/wp-content/uploads/2021/03/calculation_methodology_gs_2006.pdf).
This implementation makes no GIPS compliance claim.

## Money-weighted return — dated XIRR

From the investor's perspective, deposits are negative and withdrawals positive.
An opening NAV is a synthetic investment at the selected baseline, and closing
NAV is terminal marked capital. Booked dividends remain inside portfolio cash;
only a recorded withdrawal distributes that capital to the investor.

For aggregated same-date investor flows `F_i` and actual date offsets `d_i`:

```text
sum(F_i / (1+r)^(d_i/365)) = 0, r > -1
```

XIRR is annualized even for short windows and may therefore look extreme. It
reflects dated capital exposure plus the terminal mark; it is not merely realized
cash profit. The actual-day/365 convention includes leap-day effects and follows
Microsoft's [XIRR definition](https://support.microsoft.com/en-us/excel/functions/xirr-function).

Same-date amounts are aggregated in Decimal. There must be both signs and exactly
one sign change after zero amounts are removed. Non-conventional schedules can
have multiple roots; this implementation returns `non_conventional_cash_flows`
rather than selecting an arbitrary root, even if a particular such schedule has
only one root. Same-day canceling schedules and one-sided flows are undefined.

The solver compares positive/negative discounted sums in log space and bisects
`log(1+r)` over [-32, 32], with at most 120 iterations. Roots outside the supported
range are explicitly unavailable. This is a conservative numerical domain, not
Excel's guess-based root-selection policy. XIRR may remain available when an
intermediate equity valuation is missing, provided opening/final NAV and every
external-flow FX amount are known.

## Realized statistics and uncertainty

Statistics require a contiguous series of invested daily returns. Missing days
are not deleted. Every metric reports `value`, `reason` and `observations`.
Undefined denominators do not become zero. The annual effective risk-free rate
converts to `rf_day = (1+rf_annual)^(1/365)-1`.

| Metric | Formula / convention |
| --- | --- |
| Annualized return | `(product(1+r))^(365/n)-1`; withheld for n < 365 |
| Annualized volatility | Sample daily standard deviation × √365; needs n ≥ 2 |
| Sharpe | `mean(r-rf_day) / sample_sd(r) × √365` |
| Sortino | `mean(r-rf_day) / sqrt(mean(min(r-rf_day,0)^2)) × √365` |
| Calmar | Annualized geometric return / maximum drawdown |
| Maximum drawdown | Maximum `1 - wealth/running_peak`, including opening wealth 1; loss-positive |
| Longest drawdown | Maximum peak-to-recovery duration, or peak-to-end for an open episode, in calendar days |
| Recovery days | Longest completed peak-to-recovery duration; undefined when a drawdown is still open; zero with no drawdown |
| Best / worst month | Maximum/minimum linked return among complete calendar months only |
| Hit rate | Fraction of daily returns strictly above zero |
| Skewness | Adjusted Fisher-Pearson sample skewness; n ≥ 3 and nonzero variance |
| Excess kurtosis | Unbiased sample excess kurtosis; n ≥ 4 and nonzero variance |
| Realized VaR | Linear empirical quantile of daily losses `-r` at declared confidence |
| Realized CVaR | Mean of exactly `(1-confidence)*n` worst empirical loss atoms, including fractional boundary mass |

For central normalized moments `m_k`, skewness is
`sqrt(n*(n-1))/(n-2) * m_3/m_2^(3/2)`; excess kurtosis is
`(n-1)/((n-2)*(n-3))*((n+1)*m_4/m_2² - 3*(n-1))`.
Effective tail observations explicitly reports the possibly fractional tail mass.
VaR/CVaR can be negative when the observed tail still consists of gains; there is
no artificial zero floor. They are daily realized empirical losses, not prospective
scenario risk, forecasts or regulatory risk measures.

Daily return autocorrelation, stale prices, asynchronous markets and short records
can make square-root annualization and sample moments misleading. Ratios are
descriptive. The interface warns on short records and sparse tails; it does not
invent confidence intervals, independent observations or statistical significance.

## Replay and limits

The returned manifest includes resolved inputs, visible immutable ledger rows,
their IDs/content hashes, full/known ledger versions, input hashes, conventions,
Python/library versions, an actual backend-source SHA-256, and optional configured
git/build identity. The source fingerprint includes every backend domain Python
file and main.py, including uncommitted dependencies. Hashes identify the
supplied inputs; retaining hashes alone cannot replay a report. Downloaded reports
contain private financial records and should be stored accordingly. They do not
contain the workspace authentication key.

The offline verifier `scripts/replay_performance.py` validates a downloaded report,
checks its source/runtime identity, declared methodology/conventions and
input/ledger fingerprints, and recalculates
every financial output from the retained visible ledger rows and supplied marks.
It needs no PostgreSQL, security registry, owner key or provider connection.
Historical knowledge cutoffs can retain fewer rows than the full ledger version;
the verifier checks the visible version without inventing later unknown events.
Changes to source, runtime, evidence or financial outputs fail verification.
Legacy reports may still be parsed, but a missing source fingerprint prevents
exact replay verification and requires explicit regeneration. Nothing is silently
replaced. Verification establishes internal consistency, not certified prices,
external timestamps or protection against someone rewriting a whole report.

No permanent report or licensed-provider archive is created. A null build identity
means it was not configured; retain compatible source/environment for replay.
Reports support 2–3661 dates, existing ledger capacity, at most 100,000 supplied
quotes, and at most 2,000,000 active-row × checkpoint combinations. Larger requests
must use a shorter window. These bounds are not a production load certification.
Deployment, backups, live-provider reconciliation and real-account acceptance are
separate operational work. See the [Phase 8 audit](PHASE_8_AUDIT.md) for checks
actually performed and the remaining boundary before Phase 9.


## Optional Phase 9B benchmark comparison — 2026-10-11

The Performance workspace now offers **Compare with a reviewed benchmark** and
an explicit report-scoped identity/revision plus total-return evidence input.
It can request benchmark comparison and Phase 9A contribution from one locked
performance snapshot. The existing performance conventions remain unchanged.
Opening portfolio funding and full paired coverage are required before comparing
whole-window returns/statistics. Independent portfolio performance survives
benchmark gaps. Benchmark choice, levels, currency and provenance are supplied;
no automatic index/FX/provider or permanent account default is implied.
See [BENCHMARK.md](BENCHMARK.md) for the strict contract/formulas and
[PHASE_9B_AUDIT.md](PHASE_9B_AUDIT.md) for fresh verification and export qualification.
