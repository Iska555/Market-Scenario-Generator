# Transaction ledger — Phase 7

This private, single-owner ledger reconstructs holdings and cash from recorded
transactions. It supports fully funded long-only registered equities and cash in
multiple currencies. Portfolio construction and risk scenarios remain separate
experiments with declared weights; neither places orders or modifies the ledger.

The owner plans to open a **Lightyear Stocks & Shares ISA**. No account statement
exists yet. Manual entry and reviewed canonical CSV are supported; native
Lightyear statement parsing is **not verified or implemented**. The broker and
account label are descriptive metadata, not an ISA allowance or tax engine.

## Setup and privacy

Use the existing private research configuration: PostgreSQL with the psycopg
driver, `DATABASE_URL`, and a strong `RESEARCH_API_KEY`. Apply Alembic through the
documented research migration process; revision `20260912_03` follows the thesis
migration. Application startup does not migrate databases automatically.

The `/api/accounting` routes require `X-Research-Key` and return successful
responses with `Cache-Control: no-store`. The shared key provides single-owner
access, not per-client authorization. Production credentials, hosting, backups,
restore exercises and operational hardening remain separate deployment work.

Unlock the global Private workspace control, then in the Portfolio ledger
workspace create an account identity, record or import
transactions, inspect a preview and explicitly save it. Saved rows persist in
PostgreSQL. Leaving Ledger clears its unsaved input and results while the shared
memory-only unlock stays active. Locking or refreshing clears the key and all
private frontend state; neither deletes saved transactions. A request already sent
may finish on the server after navigation. Retry uncertain saves with the same
source/reference and unchanged content; new references could create duplicates.

Overview reads recorded account identities, current open equity quantities and
trade-date cash from these ledger records. It does not infer NAV, portfolio
weights, returns or broker-reconciled balances. Construction remains a separate
hypothetical allocation workspace. Importing ledger positions as construction
weights is deferred until a reviewed dated valuation contract supplies complete
prices, cash, FX and cutoff provenance.

## Transaction conventions

All input decimals must be exact decimal strings (integers are also accepted by
the backend), at most 20 integer and 10 fractional digits. Binary floating-point
inputs and booleans are rejected for money, quantities, prices and rates.
PostgreSQL stores input decimals as `NUMERIC(30,10)`; SQLite tests use exact
decimal text. Arithmetic uses an explicit 120-digit, round-half-even Decimal
context, independent of ambient rounding and traps. Three-factor quantity/price/FX
products and 20,000-row cash/NAV sums fit within that precision. Proportional
basis division, average cost, translated rounded basis and weights can recur and
are rounded at 120 significant digits; they are not claims of exact rational
arithmetic or tax-lot accounting. A full close removes the entire residual basis.

Currencies are explicit uppercase three-letter codes; their validity against an
external currency registry is not certified. Convert GBX/GBp prices into GBP
explicitly before recording a GBP trade; never change the unit label alone.

Every transaction requires a timezone-aware effective timestamp, currency, source
and stable external reference. The server supplies an immutable ID, sequence,
recorded timestamp and canonical content hash. Ticker is not identity: security
transactions refer to the registered research security UUID. Trade currency must
match that registry entry; historical event currency remains stored in the event.

| Type | Required economic fields | Meaning |
|---|---|---|
| BUY | security_id, quantity, price, optional fees | Purchase; positive price and quantity; fee in trade currency |
| SELL | security_id, quantity, price, optional fees | Dispose of owned quantity; zero price allowed for explicitly recorded complete loss |
| DIVIDEND | security_id, amount | Positive **net cash received** in the payment currency |
| FEE | amount | Positive standalone charge, debited from cash |
| DEPOSIT | amount | Positive external cash inflow |
| WITHDRAWAL | amount | Positive external cash outflow |
| FX_CONVERSION | amount, to_currency, to_amount, fx_rate, optional fees | Source debit and target credit; rate is target units per source unit |
| REVERSAL | reverses_id | Cancel an existing active original, retaining both records |

Unrelated economic fields are rejected, not ignored. Fees default explicitly to
zero and are allowed as a separate field only on trades and FX conversions.
DIVIDEND already means net cash: do not deduct withholding a second time. Gross
dividend and withholding evidence can be referenced in notes; this does not
provide structured tax reporting. Interest, separate tax events, corporate
actions, transfers in kind, opening lots, derivatives, shorts, margin, ETFs and
bonds are unsupported. Do not disguise these as another transaction type.

Cash is **trade-date economic cash**, not settled cash, brokerage buying power or
cash available for withdrawal. There is no settlement receivable/payable engine.
Replay rejects negative running cash in any currency and negative security
quantities. Supply full funding/trade history; the importer never invents a
deposit or opening position to make an incomplete statement balance.

## Reconciliation and cost method

For trade quantity `q`, unit price `p`, and fee `f`, buy cash changes by
`-(q*p + f)`, and position cost increases by `q*p + f`. Buy fees are capitalized
in the moving-average local cost. Sale cash changes by `q*p - f`; a partial sale
removes `old_cost * sold_quantity / old_quantity` from remaining cost. A full
close sets remaining cost to exactly zero. Remaining average cost is
`remaining_cost / remaining_quantity`; closed positions are omitted.

This is an economic moving-average cost convention, not tax-lot matching or an
assertion that the broker uses the same cost method. There is no realized P&L,
TWR, XIRR or performance attribution calculation in Phase 7.

FX conversion debits `amount + fees` in source currency and credits `to_amount`
in target currency. The two currencies must differ and
`amount * fx_rate == to_amount` under exact decimal arithmetic. If a statement's
rounded displayed rate does not reconcile its actual legs, the row cannot be
represented under this strict initial contract; obtain sufficient rate precision
or defer that row. There is no hidden FX spread or balancing adjustment.

The pure `accounting/ledger.py:replay` function sorts active events by effective
timestamp then immutable sequence. For identical timestamps, input sequence is
economically significant. Do not fabricate intraday times to reverse a broker's
unknown event ordering. A backdated insert validates the complete resulting
history, including all later cash and position effects, before saving anything.

## Corrections and historical knowledge

Records cannot be edited or deleted through the API. PostgreSQL triggers also
reject ordinary row updates/deletes on portfolios and transactions. Database
administrators can change those controls; they are not external tamper evidence.

A reversal must identify an unreversed original in the same portfolio and match
its effective timestamp and currency. Reversals cannot themselves be reversed.
To correct an amount, submit an atomic batch with the reversal and a replacement
under a new stable reference. Canonical CSV can represent both entries. A
standalone reversal is rejected if it leaves later events unfunded or oversold.

`as_of` filters economic event time. `known_at` filters when the server recorded
the event or correction. A later-known cancellation restates its original
economic period only when included by `known_at`. Querying an earlier knowledge
cutoff preserves what the system then knew. Server recorded time is not the
broker's publication time or an independently certified timestamp.

Future-effective transactions and future cutoffs are rejected. Opening a new
portfolio today does not preclude importing older actual transactions. Empty
state means no eligible recorded activity, not verified absence of broker assets.

## Atomicity, idempotency and replay

`(portfolio_id, source, external_reference)` identifies an event. Repeating it
with economically identical canonical input returns the saved event. Changing
the content produces HTTP 409; whitespace-normalized text, equivalent decimal
spellings and equivalent timestamp offsets are canonicalized. Include the
broker account and stable transaction identifier in your source/reference scheme.
Do not use a changing CSV filename or row number as a broker transaction identity
across overlapping exports without a reviewed reconciliation process.

Source provenance is supplied by the owner; fingerprints establish content
identity, not authenticity. Stored transactions are the replay inputs; hashes do
not replace their retention. Valuation additionally needs its returned price/FX
inputs and cutoffs. Preserve the compatible code/methodology version when
reproducing reports. No new provider archive, report storage or public hash chain
is supplied by this phase.

Writes lock the portfolio row, compare `expected_version`, validate the complete
prospective state and insert atomically. A stale batch containing new events is
rejected; a fully duplicate retry succeeds with its original version. Preview
does not insert any rows. A later save revalidates the captured inputs against
the current version; a preview is not a reservation.

Limits are 1,000 rows per batch and 20,000 stored rows per portfolio. Reversals
count toward capacity. Oversized portfolios are rejected explicitly, not
silently truncated. History is paginated by descending sequence; use the response
version when deciding whether a page set is still consistent.

## Canonical CSV import

`POST /api/accounting/portfolios/{id}/imports/preview` accepts UTF-8 CSV text and
an explicit source. The CSV columns are transaction field names except `source`:

```csv
type,effective_at,currency,security_id,quantity,price,amount,fees,to_currency,to_amount,fx_rate,reverses_id,external_reference,note
```

The required columns are `type,effective_at,currency,external_reference`; include
the economic columns needed by every represented type. Blank optional cells mean
absent values. Offset-aware ISO timestamps and decimal strings use the API
conventions. Quoted commas/newlines in notes follow CSV quoting. Duplicate,
unknown, missing or uneven headers/fields and unsupported types block the import.
The API reports the failing record line without echoing private content.

Preview returns resolved rows, duplicate counts, prospective holdings/cash and
`normalized_request`. After review, submit that exact normalized request to the
transaction endpoint. There is no PDF extraction, ticker guessing, automatic
column/type mapping or native Lightyear-format compatibility claim.

Lightyear's [statement guide](https://lightyear.com/en-gb/help/trading-and-investments/tax-and-statement)
describes account statements containing transactions and balances. The owner
confirmed no account or sample exists yet. After the first export, add a separate
versioned adapter with a redacted fixture and statement-balance reconciliation.
Do not use an income or gains summary as a substitute for full transaction history.

## Supplied-price valuation

`POST /api/accounting/portfolios/{id}/valuation` uses a ledger economic cutoff,
optional knowledge cutoff, supplied prices and supplied FX. Each input has a
currency, observed timestamp and source. A price must refer to an open position
and use its currency; one FX rate per used non-base currency is in **base units
per one local unit**. Base currency has rate one. Duplicate marks, unused assets,
mismatched currencies and observations after either cutoff are rejected.

For quantity `q`, supplied local mark `m`, local basis `C`, and FX `x`:

- local market value = `q*m`;
- local unrealized P&L = `q*m - C`;
- base market value = `q*m*x`;
- translated local unrealized P&L = `(q*m - C)*x`;
- base cash value = local cash * `x`;
- NAV = sum of base position and cash values;
- each weight = its base value / NAV when all values are known and NAV is positive.

Translated local P&L excludes historical acquisition FX effects and is named
accordingly. No expected return, tax treatment or liquidation-cost estimate is
implied. Prices may be stale; observed times remain visible and the caller must
assess suitability. There is no automatic market-data retrieval or certification
that mixed-market valuation cutoffs are economically synchronized.

Missing price/FX produces typed nulls with reasons. Even if some values are known,
NAV and all weights remain undefined until coverage is complete. Complete zero
NAV is zero, with undefined weights and `zero_nav`. A supplied zero security
price is valid; unavailable data must never be substituted with zero.

## Acceptance and limits

The [Phase 7 audit](PHASE_7_AUDIT.md) records actual verification and remaining
limits. Analytical identities, negative-running-balance cases, correction
cutoffs, exact database decimals, duplicate/conflicting imports, concurrent
writes, migration compatibility, partial valuation and frontend request races
form the acceptance checks. Synthetic/offline tests do not establish actual
Lightyear compatibility, completeness of your account history or production
load/security readiness. Review before Phase 8.

### Subsequent authorized performance consumer — 2026-09-15

Phase 8 is now authorized and adds a read-only consumer of this ledger; it does
not change transaction, correction or accounting valuation formulas. See
[PERFORMANCE.md](PERFORMANCE.md) for unitized daily TWR, dated XIRR, explicit raw
price/FX evidence and missing-coverage behavior. The next owner gate is before
Phase 9. The Phase 7 audit above remains a historical acceptance record.
