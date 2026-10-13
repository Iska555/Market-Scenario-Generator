# Common valuation intervals — proposed method, Phase 9E

This is the specification for a subsequent implementation, **not an accepted
calculation method**. Native source import is implemented separately in
[FACTOR_SOURCE_IMPORT.md](FACTOR_SOURCE_IMPORT.md). The current funded UTC daily
OLS/HC3 method remains unchanged.

## Proposed `funded_common_boundary_v1` contract

Require an ordered, explicit list of timezone-aware valuation boundaries, the
source intervals each pair represents, a declared research currency, and a
reviewed interval/risk-free/funding policy. Dates from the French file alone do
not establish these boundaries. Do not reinterpret a daily label as UTC midnight,
New York close, or a simultaneous global-market close without evidence.

Preserve Phase 8 daily accounting. A separate measurement request must obtain
complete ledger-derived valuations at each reviewed boundary and each external
flow inside it, using unadjusted prices, net recorded dividends/fees, exact FX
quotes and the existing knowledge/staleness rules. A daily report can be reused
only when its actual boundaries match exactly. Otherwise additional boundary
valuations are required; daily-close interpolation is not permitted.

For each fully funded interval, chain the existing unitized flow-neutral wealth
segments, so interval return is the ending/opening unit-price ratio minus one.
Require reconciliation of the product of complete interval wealth relatives with
the corresponding complete-window TWR. Show initial unfunded intervals, missing
marks and gaps explicitly; never fit a selectively reduced sample. A mid-interval
complete withdrawal or invalid unit path needs a typed unavailable reason.

## Currency and factor meaning

An explicit **USD research view of a GBP account** is a candidate that avoids
altering the native USD factor definitions. It still requires actual synchronized
USD valuations, GBP/USD quote direction and external-flow conversions throughout
each interval. It must be labelled as a USD analytical view and cannot replace
the account's GBP performance. It is not accepted merely by changing a currency
field or multiplying reported excess returns by FX.

A GBP factor view instead needs a specified investable market/funding strategy,
underlying long/short legs and hedging/notional conventions before transforming
spreads or market excess returns. Native spread factors cannot simply be compounded
as gross wealth. Require reviewed period-effective risk-free returns for the same
research currency and exact intervals. Provider daily RF allocation across trading
days cannot silently become calendar-day accrual.

## Statistical and replay acceptance

Regression operates on one row per accepted common interval. The contract must
declare sampling frequency, interval duration/regularity, intercept units, estimator,
minimum observations, rank/conditioning limits and complete paired coverage.
Use per-interval alpha until a defensible annualization exists. Irregular intervals
need an explicit estimation decision; do not assume equal-duration daily samples
or reuse 365 periods/year. HAC/bootstrap and rolling windows need their own lag,
dependence, window and sample policies after this alignment is accepted.

Retain exact permitted source rows/revision, original labels, explicit boundary
mapping, quote and external-flow evidence, all publication/retrieval/correction
records, transformation choices and compatible code/runtime identity. Hashes do
not establish historical knowledge or licensing. Future acceptance must include:

- An actual reviewed source/valuation fixture with evidenced boundary mapping and
  publication availability, plus documented permitted retention/use.
- Independent analytical cases for no flows, multiple flows, weekends/holidays,
  fees, FX direction, missing legs and fully withdrawn portfolios.
- Unit-wealth/TWR reconciliation, no double RF subtraction or spread compounding,
  and explicit incomplete-coverage/irregular-sampling failures.
- Private API/UI, immutable ledger behavior and independent offline replay.

The six-row source fixture proves parsing only. The provider description establishes
USD returns and its trading-day RF construction but does not supply the portfolio
valuations or intraday boundaries required above.
[Primary source](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5developed.html).
