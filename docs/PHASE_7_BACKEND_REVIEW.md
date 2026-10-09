# Phase 7 backend review — 2026-09-12

## Verdict

**Spec:** Substantially implements the authorized minimal ledger scope, but the
claimed deterministic/exact accounting contract needs the arithmetic repairs below.
Canonical reviewed CSV is an authorized fallback; no native Lightyear parser or
real-account reconciliation has been verified. No Phase 8 functionality was found.

**Quality:** Changes requested for three reproducible P2 defects. These findings
were open when this report was written; this report does not claim subsequent fixes
or acceptance. Root-worker verification and final audit should record their repair
status and rerun evidence.

Scope: `backend/src/accounting/*`, `20260912_03_ledger.py`, accounting tests,
and integration in `main.py` / `migrations/env.py`. Read the canonical master brief
and dated Phase 7 plan. Earlier uncommitted Phases 4–6 were not reviewed generally.
The owner's current Phase 7 authorization supersedes the historical stop-before-7
instruction. Phase 8 remains outside scope.

## Findings

### P2 — Financial replay inherits ambient rounding and traps

Original functions: `accounting/ledger.py:replay` (lines 32–33),
`accounting/valuation.py:value_state` (35–36), and
`accounting/contracts.py:TransactionCreate.coherent` (96–97).

Each copies the caller's Decimal context and changes only precision. Consequently,
identical ledger records can yield different cost bases depending on ambient rounding;
an ambient `Inexact` trap can also turn ordinary proportional allocations into errors.
This contradicts deterministic replay and the plan's explicit rounding convention.

Minimal confirmed case: deposit 1; buy quantity 3 at 0.1 with fee 0.1; sell quantity 1
at 0.1. Run the same `replay` under `localcontext()` with `ROUND_DOWN`, then
`ROUND_UP`. Remaining basis is respectively:

```text
0.266666666666666666666666666666666666666666666666666666666667
0.266666666666666666666666666666666666666666666666666666666666
```

Repair: construct a complete, documented accounting Decimal context with explicit
rounding/traps/exponent bounds rather than inheriting caller settings. Add regression
coverage that changes ambient context and checks identical valid outcomes.

### P2 — Accepted valuation inputs exceed arithmetic precision

Original function: `accounting/valuation.py:value_state`, especially lines 35–36,
49 and 52. Precision 60 accommodates a single product of two 30-digit inputs, but
valuation multiplies quantity × price × FX, and quantities/NAV also aggregate rows.
It silently rounds finite monetary values despite the stated policy that only
proportional calculations require rounding.

Minimal confirmed case: deposit USD 2 and buy quantity `1.0000000001` at USD 1.
Supply price `99999999999999999999.1234567891` and GBP/USD FX
`99999999999999999999.9876543219`. All inputs pass the declared digit bounds.

```text
returned market_value_base:
10000000000999999999911111111091111111110.0108215203235939633

exact product, calculated independently with precision 120:
10000000000999999999911111111091111111110.010821520323593963322251181129
```

The magnitude is deliberately a boundary case, not a realistic ISA quote. The
contract nevertheless accepts it and currently returns an apparently exact result.
Repair: establish sufficient precision from input bounds, supported row capacity
and arithmetic depth, or explicitly reject values beyond a supported bound. Keep
documented rounding for nonterminating basis/weight ratios. Test accepted extremes
against independently calculated products and portfolio totals.

### P2 — Creating the 101st portfolio breaks all portfolio listing

Original functions: `accounting/repository.py:create_portfolio` (line 93) and
`portfolios` (85–90).

Creation has no capacity enforcement, whereas listing throws if it sees 101 rows.
Portfolios are immutable and have no delete/archive route, so a successful create
can leave the account selector permanently unable to list any portfolios.

Confirmed with a disposable in-memory SQLite database: create 101 distinct valid
portfolio IDs through `LedgerRepository.create_portfolio`; all succeed. Calling
`portfolios()` then raises `ValueError("More than 100 portfolios are unsupported")`
(HTTP 422 through the router). No persistent/project database was changed.

Repair: provide bounded pagination, or enforce the documented capacity before
accepting creation, including concurrent creates and duplicate-ID retries. Verify
that reaching capacity leaves existing accounts readable.

## Verification and positive checks

Executed offline:

```text
backend/env/Scripts/python.exe -m pytest backend/tests/test_accounting_domain.py backend/tests/test_accounting_api.py backend/tests/test_accounting_valuation.py --no-cov
39 passed in 2.70s
```

Also executed the three minimal reproductions above. Did not run PostgreSQL tests,
migrations, provider calls or a broad suite in this review. Existing PostgreSQL tests
were inspected, including serialized conflicting writes, duplicate concurrent imports,
numeric persistence, immutable triggers and downgrade/re-upgrade isolation; their
execution result belongs to the root worker's verification record.

Code inspection supports: cost includes buy fees; sales remove proportional local
basis and exact remaining basis on full closure; cash is trade-date economic cash;
FX reconciles explicit supplied legs; reversals preserve original rows and only
affect known history after recording; portfolio row locks serialize repository
reads/writes; stale new batches conflict while duplicate-only retries succeed;
replay validates the whole corrected chronology before persistence; nested writes
and request transactions provide rollback; incomplete price/FX coverage yields null
NAV/weights; translated local P&L is not represented as historical FX-inclusive gain.

Remaining intentional limitations include equities only, no corporate actions,
settlement accounting, tax engine, native broker import certification, performance
measurement or publication. The plan's phrase “decimal text persisted” should be
updated in current documentation: actual PostgreSQL storage is `NUMERIC(30,10)`;
only SQLite uses text. That storage choice itself is appropriate for the input bounds.

## Repair verification and narrow frontend review — 2026-09-12

This section appends the resolution without changing the original findings above.
The replacement AGENTS.md now explicitly records Phase 7 authorization, the planned
Lightyear ISA, equity-only registry, and the stop-before-Phase-8 boundary.

All three original backend findings are **resolved and independently verified**:

- `accounting/precision.py:accounting_context` constructs a fresh precision-120
  `Context`, with explicit `ROUND_HALF_EVEN`, traps, exponent bounds and empty
  flags. Contracts, replay and valuation each use that context. The regression
  changes ambient precision, rounding and `Inexact` trapping while requiring
  identical replay. Proportional basis/weights can remain nonterminating decimals;
  their deterministic rounding is intentional.
- The valid large three-factor valuation now matches an independent precision-200
  product and NAV calculation exactly. Precision 120 covers finite products and
  sums under the declared 30-digit inputs and 20,000-row portfolio bound.
- `LedgerRepository.portfolios` no longer imposes the arbitrary 101-row failure.
  The API regression creates 101 distinct accounts and verifies all remain listed.
  The current private-account list is unpaginated; large-account load certification
  is not claimed.

Executed again by this reviewer:

```text
backend/env/Scripts/python.exe -m pytest backend/tests/test_accounting_domain.py backend/tests/test_accounting_api.py backend/tests/test_accounting_valuation.py --no-cov
42 passed in 22.61s

cd frontend
node --test src/features/ledger/ledger.test.js src/features/ledger/LedgerWorkspace.test.js
27 passed; 0 failed
```

The root worker separately reported a PostgreSQL-inclusive full run of 470 tests
with 97.82% coverage and 87 full frontend tests. Those full results were not rerun
by this reviewer; consult the final phase audit for the authoritative full checks.

The additional frontend inspection covered `ledger.js` and `LedgerWorkspace.jsx`,
limited to lifecycle, captured saves, history pagination and currency rendering.
Session/account/draft guards discard stale results; save submits the captured
payload, suppresses overlapping saves, and retains stable references for uncertain
retries. History merging handles duplicate IDs and resets pagination when an
idempotent retry reveals an unseen server version. Exact decimal strings remain
strings, and undefined valuation outputs stay explicitly undefined.

One new **P2 frontend presentation finding remains open at this review point**:
`LedgerWorkspace.jsx:TransactionTable` (original line 44) displays cash amounts
and fees without a visible denomination; currency appears only inside collapsed
audit details. A mixed GBP/USD CSV preview therefore presents unlabeled monetary
rows immediately before immutable save. Keep currency visible in the main preview
and history table, with an explicit regression for mixed-currency rows. The root
worker has been notified. No other material defect was identified in this narrow
frontend review. Browser verification remains with the root worker.

Updated verdict: original backend changes requested are resolved; backend spec
and quality pass this bounded review. Final Phase 7 acceptance still requires
resolution of the frontend denomination finding and the root worker's full checks.


## Root resolution of frontend denomination finding — 2026-09-12

The original review finding above is preserved. `TransactionTable` now includes
a visible Currency column in preview and history. Component assertions verify
the column and GBP row; actual browser preview showed currency beside each
transaction before save. Root additionally verified explicit GBP/USD cash and
missing-FX valuation. Final frontend checks and browser evidence are recorded
in PHASE_7_AUDIT.md. This is root verification, not an additional independent
reviewer claim.
