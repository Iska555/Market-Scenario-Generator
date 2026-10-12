# Real factor-data readiness — prospective policy, Phase 9D

This is a reviewed integration specification, not an implemented adapter or a
certification of usable real-account data. The existing [factor engine](FACTORS.md)
requires fully paired, funded UTC calendar intervals and returns already in the
account currency. The intended account is GBP; no real broker fixture or factor
source has been accepted for it.

## Source review

For example, the French developed-market description states its returns are USD,
include dividends/capital gains, and its market factor subtracts a US one-month
T-bill return. Its daily risk-free construction compounds across trading days.
Those conventions do not establish GBP UTC-calendar comparability.
[Primary source](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5developed.html).

The US five-factor description also distinguishes spread portfolios from the
market excess return and records a risk-free source change starting June 2024.
Source revisions and series definitions need preservation rather than assuming
one timeless feed.
[Primary source](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html).

## Required acceptance before an adapter

| Issue | Required reviewed evidence and policy |
| --- | --- |
| Source and access | Exact source/revision, permitted use/archive rights, retrieval time, publication availability, content hash and documented corrections. Retrieval is not proof of historical publication time. |
| Units | Explicit percentage-to-decimal conversion, sentinel interpretation and genuine missing values. Do not clip legitimate factor tails or relabel missing as zero. |
| Calendar | Exact observation interval boundaries, valuation time zones and treatment of holidays/weekends. Compare portfolio wealth at the same boundaries; do not invent weekend factor observations or silently fit fewer rows. |
| Currency | Specify account/research currency and hedging. Reconstruct same-currency market total returns and risk-free response; a foreign excess factor is not a foreign gross return level. |
| Risk-free | Identify actual period-effective return, asset/currency, accrual/calendar allocation and knowledge availability. Do not divide an annual yield by 365 without an accepted yield/accrual convention. |
| Spread factors | Define underlying long/short legs, funding/notional and currency transformation. Multiplying a return difference by an FX spot rate or adding FX return to a spread lacks a defined investment strategy. |
| Provenance | Retain actual observed/published/retrieved times and all FX evidence. Monthly or latest revisions cannot be labelled as known on earlier daily dates without evidence. |
| Statistical policy | Declare sampling frequency/annualization, minimum count, selected window, dependency assumptions and uncertainty estimator. HC3 does not account for serial dependence. |
| Reproducibility | Retain permitted exact inputs, transformation manifest, compatible source/runtime, independent analytical cases and a real reviewed fixture. Missing coverage must remain explicit. |

An unhedged foreign gross investment return can be reconciled by a reviewed
wealth-return identity, `(1 + asset_return) * (1 + FX_return) - 1`, when FX is
account-currency units per foreign unit over the same boundaries. This explains
why gross levels/returns and FX conventions are needed; it is not an implemented
transformation of market excess returns or self-financing spreads. Funding,
hedging and selected account-currency risk-free series must be specified first.

The recommended next adapter should use explicitly reviewed common valuation
boundaries and aggregated portfolio wealth intervals, preserving daily accounting.
Specify this as a new method/version rather than weakening the accepted daily
complete-window contract. Its estimator and annualization need analytical tests
and meaningful real-data acceptance. An alternative same-currency calendar-daily
source may satisfy the existing contract, but must establish every required row.

Do not label any current synthetic fixture as real factor evidence. Until a
reviewed source/fixture and transformation policy exist, retain the manual contract
and show gaps. Further HAC/bootstrap, rolling beta/capture and Brinson remain
separate scoped stages; Brinson additionally requires historical classifications
and benchmark weights.
