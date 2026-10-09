# Investment Management Workspace — asset-type roadmap

This is a future architecture note, not an implementation claim or authorization
to start another financial phase. The registry currently accepts individual
equities only. ETF/fund records remain rejected until the registry, valuation,
accounting and risk behavior have been reviewed and tested.

## Deliberate progression

1. Individual equities — the current security registry.
2. ETFs / exchange-traded funds — a planned typed registry extension.
3. Cash / FX instruments — extend instrument identity deliberately; the existing
   ledger already records currency cash balances and explicit FX conversions.
4. Bonds / fixed income — a separate domain extension.
5. Other assets only when the actual portfolio requires them.

A ticker is an identifier used at a venue, not a complete economic model. Keep a
stable security identity and an explicit `asset_type` discriminator. Introduce a
typed fund extension table (or equivalent composed domain object) linked to that
identity, rather than adding mostly-null fund fields to the equity table. Do not
build a universal schema before the first supported fund use case is agreed.

## Planned fund metadata

Fund records should be able to represent `fund_type`, `issuer`, `domicile`,
`base_currency`, `share_class`, `distributing_vs_accumulating`, `expense_ratio`,
`benchmark_or_index`, `replication_method`, and `fund_identifier` / ISIN. Listing
currency and fund base currency are distinct. Not every field is mandatory for
every fund; required fields must follow the operation being performed. Unknown
values remain explicit rather than guessed. Preserve source, effective date,
retrieval time and adjustment provenance for supplied metadata.

Later reliable provider data may add holdings, sector, country and factor
exposures. Provider contracts, retention permissions, publication lag and data
quality must be reviewed before enabling these capabilities.

## Look-through exposure is later scope

Direct portfolio weight and underlying exposure are distinct. A 20% portfolio
position in a global equity ETF is a direct holding; decomposing it into US,
European, technology or financial-sector exposure requires dated fund holdings
or other reliable exposure evidence. Such decomposition may eventually support
concentration, overlap detection, factor analysis and attribution. Do not infer
these exposures from the ticker, benchmark name or fund marketing label. The
fund registry and provider model must exist first; look-through is not currently
implemented.

## Accounting and valuation gates

Future fund ledger support should cover BUY, SELL, actual DISTRIBUTION / DIVIDEND,
applicable FEES, explicit FX conversion and relevant corporate-action events.
Accumulating funds must not generate fictitious cash distributions. Distribution
classification, domicile-specific treatment and tax assumptions must come from
verified evidence rather than guesses. These are later accounting enhancements,
not new transaction types enabled by this UX pass.

Before connecting current ledger holdings to Construction, define a reviewed
handoff containing a coherent ledger version, dated prices and FX, valuation and
knowledge cutoffs, cash treatment, eligible security types and complete portfolio
weights. Construction currently consumes hypothetical declared weights and
supplied joint return histories; quantity or cost basis cannot substitute for
market-value weights. Implemented alternatives are hypothetical portfolio,
equal weight, minimum variance, equal risk contribution (risk parity), and
maximum Sharpe when its explicit-view and feasibility requirements are met.
Actual and target portfolio modes are future integration work.

## Fixed income is a separate extension

Bonds may require coupon, maturity, face value, yield, duration, convexity,
accrued interest, clean price, dirty price, credit spread and currency. Those
concepts affect valuation, cash flows and risk. Fixed income must not be treated
as equities with different tickers. This support is intentionally deferred.

Phase 8 performance measurement was authorized on 2026-09-15. The next financial
phase remains subject to owner review before Phase 9; this does not authorize
ETF/fund or fixed-income implementation.
