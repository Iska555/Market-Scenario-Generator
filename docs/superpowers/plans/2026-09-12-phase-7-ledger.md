# Phase 7 ledger implementation plan

> **For agentic workers:** Use the subagent-driven-development workflow for
> independent work and test-driven development for financial behavior. Continue
> in the authorized existing checkout; preserve all pre-existing uncommitted work.

**Goal:** Derive auditable holdings and cash from recorded transactions, with
Lightyear ISA-oriented import review and supplied-price valuation.

**Authority:** Owner explicitly authorized Phase 7 and confirmed Lightyear Stocks
& Shares ISA on 2026-09-12. Stop before Phase 8. This authorization supersedes the
prior stop-before-7 boundary, not the preserved brief or historical audits.

**Architecture:** `backend/src/accounting/{contracts,ledger,tables,repository,
routes,imports,valuation}.py`; separate migration `20260912_03_ledger.py`.
Private `/api/accounting` endpoints reuse existing owner-key/session dependencies.
Frontend `features/ledger` consumes backend calculations. No broker network access,
orders, performance measurement, attribution, tax calculations or publication.

## Design decisions

- Immutable portfolios and transaction rows; PostgreSQL triggers prohibit updates
  and deletes. Fixed base currency, broker and account label per portfolio.
- Exact Decimal input (at most 10 fractional / 20 integer digits), PostgreSQL
  NUMERIC(30,10) and SQLite decimal text for exact portable tests. Accounting uses
  an independent 120-digit round-half-even context; proportional basis, average
  cost, translated rounded basis and weights may be rounded. Exact mark products
  and cash/NAV aggregation fit within the supported input and row limits.
- Types BUY, SELL, DIVIDEND, FEE, DEPOSIT, WITHDRAWAL, FX_CONVERSION, plus REVERSAL
  for corrections. Interest/tax/corporate actions are rejected until modeled.
- Trade-date economic cash, not broker settled/available-to-withdraw cash. No
  shorting, margin or negative running cash. Transaction timestamps require UTC
  offsets. Sort by effective time then immutable sequence. Backdated inserts
  revalidate all later entries. No future-effective records.
- BUY cash debit = quantity * price + fees; basis includes buy fees. SELL removes
  proportional moving-average cost; full close removes exact remaining cost.
  Sell fees reduce cash proceeds. No realized-return reporting. DIVIDEND amount
  is explicitly net cash received; source note records gross/tax if applicable,
  without pretending to calculate tax. Other cash amounts positive; fees separate.
- FX explicitly debits source amount + source-currency fee and credits supplied
  target amount, with explicit fx_rate = target units per source unit and exact
  amount * rate reconciliation. Trade amounts and security currency must agree.
- REVERSAL refers to an existing transaction in the same portfolio and copies its
  effective timestamp; no reversal of reversal or twice-reversed records. Replay
  excludes canceled originals under a stated knowledge cutoff. Atomic batch may
  include both reversal and replacement. Revalidate resulting cash/positions.
- Transactions carry immutable sequence, source, external_reference and canonical
  content hash. Same source/reference + same content = replay, different = 409.
  Lock portfolio row to serialize writes; expected_version rejects stale batches.
  Duplicate-only retries succeed even with original expected_version. Max 1,000
  rows/batch and 20,000/portfolio; reject capacity before returning partial results.
- History has economic as_of and server known_at cutoffs. Market values require
  explicit supplied dated prices and positive FX in base units/local unit.
  Missing marks produce nulls/reasons; never sum partial valuations as complete NAV.
  Unrealized P&L is local market value less local moving-average basis; its base
  conversion is labeled translated local P&L, not historical FX-inclusive gain.
- Current equity registry reused. ETF support requires explicit registry extension
  and test compatibility; do not register a fund as an equity silently.
- Lightyear official help describes account statements but lacks a versioned CSV
  schema. The owner has no account/sample yet. Implement reviewed canonical CSV;
  native column/type mapping awaits a fixture, with no verified parser claim.
  Unknown/ambiguous rows block the whole import. No inferred deposits/opening lots.

## API/UI contract

All decimal JSON values are strings; all times offset-aware ISO timestamps.
Owner header `X-Research-Key`; no-store responses. Base `/api/accounting`.

- GET/POST `/portfolios`: list / create `{id(UUID supplied),name,base_currency,
  broker,account_label}`. GET returns list of `{id,name,base_currency,broker,
  account_label,created_at,version}`; repeated identical ID create is idempotent.
- GET `/portfolios/{id}/transactions?limit=100&offset=0`: newest sequence first,
  return `{transactions:[...],version,total}` including reversals.
- POST `/portfolios/{id}/transactions/preview` and `/transactions`: body
  `{expected_version,transactions:[{type,effective_at,currency,security_id?,
  quantity?,price?,amount?,fees:"0",to_currency?,to_amount?,fx_rate?,reverses_id?,
  source,external_reference,note:""}]}`. Return `{version,inserted,duplicates,
  transactions:[resolved proposed/replayed rows],state}`. Preview writes nothing;
  UI displays it and posts identical captured input on explicit save. A row has
  the input fields plus id, portfolio_id, sequence, recorded_at, content_sha256.
- GET `/portfolios/{id}/state?as_of=...&known_at=...`: `{portfolio_id,base_currency,
  version,as_of,known_at,cash:[{currency,amount}],positions:[{security_id,currency,
  quantity,cost_basis,average_cost}],active_transaction_ids,convention}`.
- POST `/portfolios/{id}/valuation`: `{as_of,known_at?,prices:[{security_id,
  currency,price,observed_at,source}],fx:[{currency,rate,observed_at,source}]}`.
  Return state plus `{positions:[...state position + market_value_local,
  unrealized_pnl_local,market_value_base,translated_unrealized_pnl_base,weight,
  reason],cash:[{currency,amount,value_base,weight,reason}],nav,reason,inputs}`.
  Nulls for undefined numbers; no frontend arithmetic.
- POST `/portfolios/{id}/imports/preview`: explicit canonical CSV body
  `{expected_version,csv_text,source}` with canonical fields from transaction
  contract (source applied to all rows). Return same batch preview plus
  `{normalized_request}` for explicit save through `/transactions`.
  CSV is UTF-8 text, no filesystem/network references; errors identify line number
  without raw financial/personal data. No automatic assumption about Lightyear
  PDF or CSV layout. Source `lightyear_reviewed` identifies owner-normalized rows.

## Tasks

### Task 1: Domain contracts and replay

- [x] Write analytical cases for weighted-average basis, cash, FX, closures,
  cancellation/knowledge cutoffs, negatives, chronology and invalid contracts.
- [x] Confirm missing feature failures, implement `contracts.py` and `ledger.py`.
- [x] Run targeted tests; exact integer/decimal identities and failure cases.

### Task 2: Persistence, API and imports

- [x] Add repository tests for atomicity, duplicate/conflicting sources, immutable
  history, wrong security/currency, backdates, preview no writes and stale version.
- [x] Implement separate tables/migration, row locks, routes and CSV validation.
- [x] Add actual PostgreSQL tests for exact decimals, concurrent imports,
  immutable triggers, migration down/up and prior phase preservation.

### Task 3: Valuation and usable portfolio workspace

- [x] Test complete/partial price and FX coverage, zero NAV, timestamps, currency
  mismatches and exact holdings/value/cash reconciliation; implement valuation.
- [x] Build private ledger UI with account creation/selection, manual transactions,
  correction controls, CSV preview/save, history, cash and holdings, supplied marks.
- [x] Test no fabricated data, exact decimal transport, captured save payload,
  edit/account/disconnect races and protection against accidental duplicate saves.
- [x] Integrate navigation with existing workspaces and visually inspect.

### Task 4: Verification and acceptance

- [x] Run full PostgreSQL pytest/coverage, Ruff/format, mypy, frontend tests,
  lint/build. Review code and resolve material findings.
- [x] Update methodology, architecture, README, AGENTS, BUILD_PLAN and dated
  master-brief addendum; preserve historical audit bytes.
- [x] Write PHASE_7_AUDIT with original functions, repair history, verification,
  broker/schema limits, supported instrument types and readiness boundaries.
- [x] Stop before Phase 8; do not commit/push/deploy unrelated prior work.

## Execution record

Ruling: continue in `phase-1-correctness` because approved Phases 4–6 remain
uncommitted dependencies in the requested checkout. Do not stash or lose them.
Ruling: the owner’s repeated “continue” authorizes this concrete Phase 7 scope;
routine reversible design choices do not require another phase approval.
Preflight: domain→repository uses TransactionRead; repository→frontend uses the
API above; imports→repository supplies the same batch; valuation→ledger uses the
same state. Shared interfaces are defined above and tests must exercise them.
