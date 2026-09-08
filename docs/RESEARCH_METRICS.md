# Research metric definitions and arithmetic

Phase 3 implements a vocabulary of 28 equity metrics and two pure arithmetic
helpers in `backend/src/research/metrics.py`. It does not implement a financial
statement parser, an automated valuation pipeline or an expected-return model.
The catalogue identifies the meaning and unit of an observation; a recognised
key does not certify its source, sector relevance or accounting comparability.

`MetricDefinition` is a frozen dataclass with `key`, `label`, `category` and
`unit`. `METRICS` is the dictionary keyed by metric name. `currency` means a
monetary amount with a separately declared currency and scale normalised to
whole currency units. `ratio` means a dimensionless multiple, such as `15` for
15 times earnings. `fraction` means a dimensionless percentage-like quantity:
`0.15` means 15%, including for margins, yields, growth and share dilution.
Negative observations remain signed; no helper clips a loss or a negative yield.

## Implemented calculation primitives

`ratio(numerator, denominator)` calculates `numerator / denominator`, requiring
a positive denominator. `growth(current, previous)` calculates
`(current - previous) / previous`, requiring a positive prior value. Both return
the frozen `CalculationResult(value, reason)` dataclass. Successful results
have a Decimal value and no reason. A zero or negative denominator/base produces
`value=None` and a reason; undefined does not mean zero. Negative numerators and
negative current values are allowed. For example, moving from 100 to -25 gives
growth of -1.25; moving from -25 to 100 is undefined under this convention.

All operands must be finite `Decimal` instances; floats, strings, integers,
booleans, NaN and infinities raise `ValueError`. Parse numeric strings at the
data boundary before calling the helpers. Arithmetic exceptions and nonfinite
outputs also raise `ValueError`. Calculations use the caller's Decimal context,
with no binary float conversion, explicit rounding, quantization or multiplication
by 100. Recurring decimals still round at that context's precision; this is not
an arbitrary-precision exact rational engine. The default Decimal context's
precision and exponent range apply unless the caller supplies a local context.

The helpers do not select observations or estimate inputs. Callers must establish
currency, reporting period, fiscal calendar, consolidated scope, accounting basis
and point-in-time availability before arithmetic. Growth must compare equivalent
periods (for example annual versus annual), and is neither annualised nor a CAGR.
Per-share growth requires a consistent split-adjusted share basis. Ratios combining
stocks and flows need an explicit date and trailing, annual or forecast window.
No data window, forecast horizon, FX conversion or sector applicability is inferred.

## Catalogue and formula mappings

The formulas below define possible caller mappings to the arithmetic primitives.
They are documented conventions, **not 28 implemented calculation functions**.
Source-derived observations must retain their actual formula/basis when different;
do not silently relabel adjusted, forecast or otherwise incompatible measures.

| Key | Unit | Meaning and formula/input convention |
| --- | --- | --- |
| `market_cap` | currency | Price times shares outstanding at the stated valuation date; share-class scope must match. |
| `enterprise_value` | currency | Market cap plus debt, preferred equity and noncontrolling interests minus cash under a declared source definition; lease debt and cash treatment vary. |
| `pe` | ratio | `ratio(market_cap, earnings attributable to common shareholders)` for a declared historical window, or price/EPS on a consistent share basis. |
| `forward_pe` | ratio | Price/forecast EPS (or equivalent equity totals) for a declared forecast horizon; only ingest when forecast provenance is trustworthy. No forecast is generated here. |
| `ev_ebit` | ratio | `ratio(enterprise_value, EBIT)` with explicit trailing/annual window and adjustment basis. |
| `ev_ebitda` | ratio | `ratio(enterprise_value, EBITDA)`; EBITDA and enterprise-value adjustments are source dependent. |
| `price_book` | ratio | `ratio(market_cap, common book equity)`; tangible book is a different declared basis. |
| `price_sales` | ratio | `ratio(market_cap, revenue)` for an explicit revenue window. |
| `fcf_yield` | fraction | `ratio(equity free cash flow, market_cap)`; source must identify the FCF definition. Enterprise FCF/EV must be separately identified by basis. |
| `earnings_yield` | fraction | `ratio(earnings attributable to common shareholders, market_cap)`; negative earnings yield is retained even though P/E on a loss denominator is undefined. |
| `roe` | fraction | `ratio(earnings attributable to common shareholders, average common equity)`; ending versus average equity, averaging dates and adjustments must be declared. |
| `roic` | fraction | `ratio(NOPAT, invested capital)` under an explicit source definition, including tax treatment, average versus ending capital, leases, goodwill and excess cash. No universal ROIC construction is asserted. |
| `gross_margin` | fraction | `ratio(gross profit, revenue)` for the same scope and period. |
| `operating_margin` | fraction | `ratio(operating profit, revenue)`; adjusted operating profit requires a declared basis. |
| `net_margin` | fraction | `ratio(net income, revenue)` with explicit consolidated versus attributable-income scope. |
| `fcf_conversion` | fraction | `ratio(free cash flow, net income)` is one convention; FCF/EBITDA and other source conventions require an explicit basis and must not be pooled. |
| `revenue_growth` | fraction | `growth(current revenue, comparable previous revenue)`; organic or constant-currency growth is a separate source basis. |
| `eps_growth` | fraction | `growth(current EPS, comparable previous EPS)` with basic/diluted, split and adjustment basis declared. |
| `fcf_growth` | fraction | `growth(current FCF, comparable previous FCF)` under an unchanged FCF definition. |
| `net_debt` | currency | Debt minus eligible cash/cash equivalents under a declared source definition; negative values represent net cash. Lease obligations and restricted cash treatment vary. |
| `net_debt_ebitda` | ratio | `ratio(net_debt, EBITDA)` with debt date and earnings window declared; negative net debt retains its sign. |
| `interest_coverage` | ratio | `ratio(EBIT, interest expense)` is one convention; EBITDA or net-interest definitions require a declared basis. No interest expense produces an undefined value, not infinity. |
| `current_ratio` | ratio | `ratio(current assets, current liabilities)` at the same balance-sheet date; applicability depends on the industry. |
| `dividends` | currency | Aggregate cash dividends paid during the period, positive for cash paid; identify common versus total equity scope. This is neither dividends per share nor dividend yield. |
| `buybacks` | currency | Aggregate gross cash paid to repurchase shares during the period, positive for cash paid; not a net buyback yield. |
| `share_dilution` | fraction | `growth(current shares, previous shares)` on a consistent split-adjusted basis; positive means dilution and negative means share-count contraction. Weighted-average diluted shares and period-end shares are distinct bases. |
| `capex` | currency | Capital expenditure during the period, positive for expenditure; identify gross versus net disposals and treatment of capitalised intangibles. |
| `acquisitions` | currency | Acquisition expenditure during the period; declare cash paid gross/net of acquired cash and whether noncash consideration is included. Positive means expenditure. |

Source cash-flow signs and scales must be normalised explicitly when importing
capital-allocation amounts; the arithmetic primitives do not do that conversion.
The catalogue permits metric observations without requiring all raw components.
The positive-denominator rule is a conservative calculation convention: it avoids
misleading multiples on losses or negative equity, but does not invalidate a
source's differently defined observation automatically. Imported values and locally
calculated results require their own provenance and accounting-basis explanation.

## Verification and limitations

`backend/tests/test_research_metrics.py` uses hand-calculated synthetic values for
ratios and growth, decimal fractions, sign preservation, near-zero changes,
nonpositive denominators, nonfinite/invalid inputs and Decimal context overflow.
No online data or provider confidence is involved. Unit/currency enforcement at
ingestion and point-in-time selection belong to the research contracts and
repository; they are outside these two arithmetic functions.

There was no original research metric calculation module to repair. This is new
calculation infrastructure. It does not address differences between accounting
standards, determine whether an industry should use a metric, certify forecast
quality, or make incomparable source definitions comparable. Those remain explicit
limitations of research observations and their use.
