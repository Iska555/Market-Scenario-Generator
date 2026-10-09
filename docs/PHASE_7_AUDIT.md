# Phase 7 audit — transaction ledger (2026-09-12)

Owner explicitly authorized Phase 7 and identified Lightyear Stocks & Shares ISA.
Historical Phase 1–6 audits and pre-existing uncommitted work are preserved.
Scope and execution record: [Phase 7 plan](superpowers/plans/2026-09-12-phase-7-ledger.md).
This opening boundary record was written before implementation; final acceptance
and verification are appended below. Stop before Phase 8.

| Original location | Finding | Disposition |
|---|---|---|
| No `backend/src/accounting` | Missing ledger/cash/positions | Implement separately from risk and construction |
| `research/tables.py:Security` | Equity-only registry | Preserve semantics; explicitly scope any fund extension |
| `research/database.py:get_session` | Commits before HTTP success | Reuse private transaction boundary |
| `portfolio/construction/contracts.py` | Owner-declared scenario weights | Preserve; do not silently replace with ledger state |
| `frontend/src/components/PlatformShell.jsx` | No holdings/ledger destination | Add real ledger workspace with honest empty states |

Lightyear's [official statement guide](https://lightyear.com/en-gb/help/trading-and-investments/tax-and-statement)
describes account statements and PDF export but provides no versioned CSV schema.
Requested a redacted CSV header/example from the owner. Native parser compatibility
must not be claimed without a matching fixture. No broker credentials or provider
calls are introduced.


## Final implementation and review disposition — 2026-09-12

**Status: bounded Phase 7 implementation complete and locally verified; ready
for owner review before Phase 8.** No hosted CI, deployment or real Lightyear
statement reconciliation is claimed. The owner later clarified that the account
has not opened; no statement sample can currently be supplied. Native Lightyear
mapping is explicitly deferred, not counted as implemented.

### Implemented behavior

- Separate private `/api/accounting` endpoints and `20260912_03` migration.
  Existing simulations, construction, valuation and thesis behavior remain separate.
- Immutable portfolio identity and transaction history. PostgreSQL triggers reject
  UPDATE/DELETE. User-source references and canonical content hashes make retries
  idempotent. Version checks and portfolio locks serialize atomic writes.
- BUY, SELL, net DIVIDEND, FEE, DEPOSIT, WITHDRAWAL, explicit FX_CONVERSION and
  correcting REVERSAL. Fully funded, long-only registered equities only.
- Economic-time/knowledge-time replay, deterministic sequence ordering, explicit
  per-currency cash, quantities, moving-average local basis, fee treatment and
  exact full closures. Impossible running balances reject the entire batch.
- Canonical CSV preview/normalization with atomic save and safe line-number
  errors. No native broker layout guessing or inferred opening funding/lots.
- Supplied dated price/FX valuation, local unrealized P&L, translated local P&L,
  complete NAV and portfolio/cash weights. Missing coverage produces typed nulls;
  no partial NAV is presented as complete. No historical FX-inclusive return claim.
- Private Ledger destination with creation/selection, manual correction controls,
  captured preview/save, safe uncertain-save retries, paginated immutable history,
  cash/holdings and supplied marks. No financial arithmetic occurs in the browser.
  Credentials and drafts clear on disconnect/navigation; recorded entries persist.

Methodology, exact contracts, formulas and limits: [ACCOUNTING.md](ACCOUNTING.md).

### Findings and repairs

The initial absence of a ledger was addressed by the new accounting domain and
workspace. Review findings are retained in [PHASE_7_BACKEND_REVIEW.md](PHASE_7_BACKEND_REVIEW.md),
including the original changes-requested verdict and subsequent verification.
The frontend implementation worker was interrupted before a standalone report;
root completed its integration, review, regression tests and browser checks.

| Original file / function | Defect found during Phase 7 | Repair and evidence |
|---|---|---|
| `accounting/contracts.py`: decimal fields | Pydantic accepted binary floats/bools into economic decimal fields | Explicit before-validator rejects them; failing regression reproduced then passed |
| `accounting/ledger.py:replay` | Pure replay accepted rows belonging to another portfolio | Portfolio identity guard; regression reproduced then passed |
| `accounting/ledger.py:replay`, `valuation.py:value_state`, `contracts.py:coherent` | Local contexts inherited ambient rounding/traps | Fresh explicit Context in `precision.py`, round-half-even and fixed traps; replay independent of ROUND_UP/ROUND_DOWN and Inexact trap |
| `accounting/valuation.py:value_state` | Precision 60 rounded valid quantity × price × FX products | Precision 120 covers finite products and bounded sums; independent precision-200 expected product/NAV regression passes |
| `accounting/repository.py:portfolios` | Account 101 could be created but made all list calls fail | Removed arbitrary list cap; API regression returns all 101 created accounts |
| `features/ledger/ledger.js`: draft/request lifecycle | Edited pending requests could leave busy state; account changes retained drafts | Busy cleanup and session/account/draft guards; deferred-response and account-switch tests |
| `features/ledger/ledger.js:savePreview` | Repeated references within one saved batch could repeat displayed history IDs; stale duplicate retries could leave gaps | Deduplicate IDs, preserve sequence order and reset history pagination when the server version reveals unseen entries; failing duplicate regression repaired |
| `features/ledger/LedgerWorkspace.jsx:TransactionTable` | Currency only inside collapsed details obscured denomination before save | Visible Currency column in main preview/history, component assertions and mixed-event browser verification |
| `features/ledger/LedgerWorkspace.jsx`: primary button/status styles | Generic hover background could obscure white button text; dark status/eyebrow contrast was weak | Preserve primary background on hover and inherit readable theme text; visual light/dark mobile checks |

The Decimal convention is deliberate: finite economic inputs/products and cash
sums fit within 120 significant digits; recurring proportional basis, average
cost, weights and translation of rounded basis are rounded. No finite-precision
implementation is described as exact rational arithmetic or tax-lot accounting.

### Verification actually executed

Environment: Windows, repository Python 3.14 environment, Node frontend tooling,
PostgreSQL 17.11 in a disposable local verification database. All source/provider
inputs in analytical/API/browser checks were synthetic. No broker network call.

| Check | Observed result |
|---|---|
| Full `pytest` with `TEST_DATABASE_URL` and `LOKY_MAX_CPU_COUNT=2` | **470 passed, no skips**, 33.31s; **97.82%** combined statement/branch coverage, above 95% gate |
| Actual PostgreSQL guarantees | Exact NUMERIC round-trip, idempotent concurrent imports, conflicting withdrawal serialization, append-only triggers, migration down/up and prior-phase schema preservation passed |
| Independent repair review | 42 targeted accounting tests passed; reviewer also ran 27 targeted frontend tests |
| Ruff check / format check | Passed; 100 Python files formatted at verification |
| mypy | Passed, 98 source files |
| `pip check` | No broken requirements |
| Full frontend `npm test` | **87 passed, 0 failed** |
| Frontend lint and production build | Passed; final presentation checks rerun after currency/contrast changes |

The build retains warnings about a nine-month-old Browserslist dataset and a
bundle over 500 kB. They are recorded, not suppressed or described as resolved.
The first dev-server startup hit the Windows/esbuild directory-access problem;
using the existing native Vite config loader started it successfully. Test and
server processes interrupted by usage-limit pauses were restarted; interrupted
runs are not counted as passing. A disposable PostgreSQL recovery completed
before the final uninterrupted tests.

### Browser acceptance with disposable data

Used the actual frontend and private API backed by an isolated PostgreSQL schema.
Created a synthetic portfolio through the UI and registered a synthetic equity
through the research API. No real owner holdings were created or assumed.

1. Previewed/saved GBP 1,000 deposit; preview showed state while history remained
   empty until explicit save.
2. Previewed/saved a five-row CSV: buy 2 at 100 with fee 2; sell 1 at 150 with
   fee 1; dividend 3; fee 4; convert GBP 100 + fee 2 to USD 125 at 1.25.
   Reconciled **GBP 844, USD 125, quantity 1, local basis/average cost GBP 101**.
3. Supplied price GBP 120 and USD-to-GBP FX 0.8: **NAV GBP 1,064**, local and
   translated local unrealized P&L **GBP 19**. Dates and sources visible.
4. Removed required USD FX: NAV and all weights became undefined; USD cash had
   `missing_fx`. Known local values remained labeled.
5. Repeated the original CSV: **0 new rows, 5 duplicate replays, version 6**.
6. Selected and reversed fee #5: appended row #7, retained original history,
   restored GBP cash to **848**, USD remained **125**.
7. Unsupported INTEREST CSV rejected with safe **line 2** feedback.
8. Navigated away/back: owner-key prompt returned and unsaved content cleared.
   Reconnected: **7 historical records** and GBP 848/USD 125 remained persisted.
9. Inspected default desktop and 390×844 mobile viewports in light/dark themes.
   No document-level horizontal overflow on mobile; wide data tables scroll
   within their containers. Restored the temporary viewport override afterward.

### Preserved records and remaining limits

Verified SHA-256 byte-prefix preservation for all **50,197 pre-Phase-7 bytes** of
MASTER_BRIEF.md, and exact full-byte preservation of BRIEF_SUGGESTIONS.md and all
Phase 1–6 audits against the captured pre-Phase-7 baseline. The 2026-09-12 master
continuation is append-only. Historical audit findings were not rewritten.
Existing approved uncommitted Phase 4–6 work remains in the same checkout; no
commit, push, public publication or deployment is included in this phase.

- **Native Lightyear import deferred:** actual redacted export/schema and balance
  reconciliation are prerequisites. Canonical CSV is owner-normalized input.
- **Equities and cash only:** no ETF/fund relabeling, bond accruals, derivatives,
  corporate actions, interest/tax lines, margin, shorting or in-kind transfers.
  This limits immediate use for the owner's eventual passive fund portfolio.
- **Accounting convention:** trade-date economic cash, moving-average local basis,
  net dividends; no settlement, ISA allowance/eligibility or tax engine.
- **Reproducibility:** immutable normalized events/IDs/hashes, cutoffs, convention,
  returned mark inputs and compatible code must be retained. No report archive,
  market-data archive, provider certification or external timestamp attestation.
- **Capacity/security:** 1,000 rows/batch and 20,000 stored rows/portfolio; private
  unpaginated portfolio list. No large-scale load certification. Single-owner
  key is not multi-client authorization. Durable hosting, backups, restore and
  production security/monitoring remain operational acceptance work.
- **Workflow:** registered security UUID and advanced supplied JSON inputs remain
  explicit. Further convenience controls are possible; no fabricated marks or
  automatic orders are used to conceal missing inputs.

**Review gate:** stop before Phase 8. Three canonical phases remain: 8 TWR/XIRR,
9 attribution, 10 public track record. Finishing the roadmap does not itself
verify every broker, instrument or production operating requirement.


## Handoff cleanup — 2026-09-13

Final frontend rerun after the currency/contrast edits: 87 tests passed, lint
and production build passed. Browser console had no errors. The disposable
browser schema was verified to contain only the synthetic portfolio before
removal; it is now absent. Temporary frontend/backend services were stopped,
and the disposable PostgreSQL server was shut down cleanly with pg_ctl.
No real broker account, account statement or owner holdings were used.
