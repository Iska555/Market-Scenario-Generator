# Reconciled position contribution — Phase 9A

Authorized 2026-10-09 after Phase 8 acceptance. This private, read-only explanation
uses actual corrected ledger holdings, executed trades and supplied valuations.
It explains portfolio TWR; it does not estimate expected returns, recommend trades,
explain XIRR or perform benchmark/factor attribution. The underlying performance
methodology remains [PERFORMANCE.md](PERFORMANCE.md). Current acceptance is recorded
separately in [PHASE_9A_AUDIT.md](PHASE_9A_AUDIT.md).

## Workflow and contract

In Performance, select an account and completed UTC reporting dates, review the
knowledge cutoff and dated evidence, then select **Include position contributions**.
One request returns performance and contribution from the same locked ledger
snapshot. Review the reconciliation, equity rankings, component table and segment
opening exposures. Closed positions remain included. Download contribution replay
JSON explicitly if you need to retain this private evidence. Edits, account reload,
navigation, lock and refresh clear client results; stale versions require reload.

`POST /api/attribution/portfolios/{portfolio_id}/contribution` accepts the exact
`PerformanceRequest`, including `expected_version`, `known_at`, consecutive daily
marks, active flow marks, unadjusted prices and explicit FX. It inherits Phase 8's
authorization, quote validation, completed-day rules, capacity limits and
`Cache-Control: no-store`. It adds no tables, migrations, provider calls or writes.
The portfolio row lock remains held through contribution calculation.

The response embeds the complete Phase 8 report in `performance`. Other fields:

| Field | Meaning |
| --- | --- |
| `methodology` | `ledger_endpoint_contribution_v1` |
| `linking` | `forward_unit_wealth_increments` |
| `fx_convention` | End FX for local P&L; opening exposure FX; separate conversion principal |
| `units` | Exact decimal portfolio return; presentation in percentage points |
| `components` | Security UUID, cash currency, standalone account fees and FX conversions |
| `segments` | Daily/flow boundaries, units, opening/closing NAV, opening quantities/values/weights, internal transaction IDs and linked effects |
| `top_contributors`, `bottom_contributors` | Up to five positive/negative net equity effects, respectively |
| `reconciliation` | Explained sum, residual, fixed tolerance and nullable pass/fail |
| `warnings` | Conventions, limitations and any missing/reconciliation reason |

Each effect has `{value: decimal-string-or-null, reason: string-or-null}`. A finite
value has no undefined reason; a null value requires one. Components expose price,
net dividends, fees, FX and their total. `pnl_base` is an unlinked monetary P&L
diagnostic in account base currency; it is not another return contribution.

Security UUIDs are authoritative. Current ticker/sector metadata is not backfilled
into old exposure history. Sector aggregation awaits point-in-time classifications.
Cash, account fees and conversion effects are displayed outside equity rankings.
Rankings use the full net linked equity contribution, including its income/cost/FX
effects, with deterministic UUID tie ordering. They are contribution rankings,
not rankings of standalone security return or investment skill.

## Segment accounting identities

Let a segment start just after its preceding external flow or daily close and end
at the next daily close or immediately before an external flow. External funding
is excluded from internal segment events. At equal timestamps, immutable ledger
sequence determines which trades precede a flow. Corrections use the same visible
records and knowledge cutoff as Phase 8; a later-known reversal does not rewrite
an earlier-cutoff report.

For security i, let M0 and M1 be opening/closing local marked value, B and S be
summed executed buy/sell principal (`quantity × price`), and F0 and F1 be opening
and closing base-currency units per local-currency unit. An absent endpoint
position has marked value zero; it is not assigned an invented price.

| Effect | Base-currency monetary identity |
| --- | --- |
| Security price/capital P&L | `(M1 − M0 − B + S) × F1` |
| Security FX | `M0 × F1 − opening marked base value` (equivalent to `M0 × (F1 − F0)` when held) |
| Booked net dividend | `dividend amount × end FX of payout currency`, assigned to its security UUID |
| Trade fees | `−booked fees × end FX of transaction currency`, assigned to the traded security |
| Standalone account fees | `−fee amount × end FX of fee currency` |
| Opening cash FX | `opening local cash × end FX − opening marked base cash` |
| Conversion principal | `to_amount × end FX(to_currency) − amount × end FX(from_currency)` |
| Conversion fees | `−booked fees × end FX(from_currency)` |

Buy/sell principal cancels the corresponding cash movement, so it is not counted
as a return. Dividends are booked net amounts, not an inferred gross dividend plus
an invented tax entry. Unadjusted prices prevent counting dividends twice. Trade
principal excludes fees; fees reduce cash and are shown separately. The identity
uses marked value and cash, not moving-average cost basis
or a tax-lot realized gain. A buy/sell within one segment remains attributable
even when no position exists at either endpoint.

Summed effects must equal `closing NAV − opening NAV` before linking. A segment
monetary mismatch above `1e-12 + 1e-12 × abs(segment P&L)` leaves the whole window
contribution undefined with `segment_pnl_does_not_reconcile`; no balancing entry
is assigned to a security.

## FX allocation and assumptions

This is a declared endpoint allocation. Local price P&L, booked income and costs
use segment-end FX; opening equity and cash receive the opening-exposure FX
change. Thus the local-price/FX interaction is assigned to price. Opening FX
exposure can remain assigned to a security that is sold inside the segment.
Conversion principal is translated at the same endpoint rates and shown separately.
This gives a complete accounting identity without asserting transaction-time market
FX rates that the evidence does not contain. A different allocation convention can
change price/FX splits while retaining the same total.

Extra end FX may be required for a foreign currency fully spent during the segment,
or a foreign security fully sold, although Phase 8 needs no FX to value a zero
closing balance. Supply that currency's end mark in the existing FX array.
Base-currency FX is exactly one. Required contribution FX uses the same explicit
maximum age measured in UTC calendar dates; no FX is guessed or carried forward.
Cash has no modeled interest. Only booked events and supplied FX can contribute;
unrecorded interest, charges, taxes, corporate actions and instruments remain absent.

## Geometric linking and reconciliation

Phase 8 issues/redeems units at each external-flow boundary. Let U_s be its constant
units during segment s, V_s its NAV and P_s = V_s/U_s its unit value. Unit value is
normalized to one at inception of the measured wealth chain. Funding changes U,
preserving P. For base P&L e_i,s, the full-window linked effect is:

`c_i,s = e_i,s / U_s`, and `C_i = Σ_s c_i,s`.

For a funded positive-value segment this equals `P_start × e_i,s / V_start`,
so the segment's return contribution is scaled by prior compounded wealth.
Summing all linked effects gives `P_final − 1`, the geometrically linked Phase 8
TWR. For example, wealth 100 → 110 → 121 with 100 units contributes 0.10 then
0.11, totaling 0.21, rather than adding two standalone 10% returns.
The implementation divides by units directly, which also handles valid total-loss
and zero-NAV segments without dividing by zero NAV. An unfunded interval with
zero P&L contributes zero to an otherwise valid measured chain; it does not create
a defined standalone return. Full withdrawal/refunding follows Phase 8's retained
unit value. Capital without valid units is undefined.

This is forward wealth linking, not a claim of a unique economic or causal
attribution. Compounding is assigned to later increments; alternative linking
methods can allocate components differently. Flow-neutral unitization and
geometric linking are consistent with the cash-flow measurement concepts in the
[GIPS handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/).
No GIPS compliance claim is made. The separation of contribution, benchmark
attribution and statistical explanation follows the scope distinctions discussed
in the CFA Institute's [Performance Attribution](https://rpc.cfainstitute.org/research/foundation/2019/performance-attribution).
These sources provide context; the precise implemented allocation is specified here.

Reconciliation uses `R = Decimal(str(Phase8 TWR)) − Σ_i C_i` and fixed tolerance
`T = 1e-12 + 1e-12 × abs(TWR)`, both in decimal return units. `within_tolerance`
is `abs(R) ≤ T`. Phase 8 returns a finite floating-point TWR; contribution arithmetic
retains the existing high-precision accounting Decimal context. R is always shown,
including harmless float/Decimal differences. Above tolerance the result visibly
fails reconciliation; it is never force-balanced, rescaled or silently accepted.
The UI multiplies decimal returns by 100 only for presentation in percentage points.

## Undefined values, limits and reproducibility

If portfolio TWR is undefined, the window contribution is undefined with its reason.
If additional contribution evidence is missing/stale or segment accounting fails,
the embedded independently computed performance report remains available, but all
window component effects/P&L are null, rankings empty and reconciliation unknown.
Previously completed segment diagnostics can remain in the report; they are not
presented as a complete window explanation. No missing component is set to zero
and remaining components are not renormalized. Empty/pre-funding windows retain
Phase 8's undefined semantics. Valid total loss can contribute −100%.

Existing request/ledger/mark limits apply. A further maximum of 100,000 cumulative
segment component plus opening position/cash cells bounds contribution exposure
output. Above this limit the request is rejected with a shorter-window instruction.
No claim of large-account load acceptance is made.

Verify a private saved report locally with:

```powershell
./backend/.venv/Scripts/python.exe scripts/replay_contribution.py path/to/report.json
```

`verify_contribution` first verifies the complete embedded performance manifest:
actual backend source/runtime, inputs, visible ledger records, versions, conventions
and recalculated financial outputs. It then rebuilds and compares the complete
contribution report, including effects, exposure evidence, rankings and methodology.
No database or provider is required. This checks internal consistency, not broker
attestation, authenticity against a separate trusted signature, or certification
of supplied price/FX evidence.

Phase 8 source identity conservatively hashes all backend source files. Adding
Phase 9A changes that identity. Retain the compatible Phase 8 checkpoint/environment
(`890dd4a`) to verify old Phase 8 downloads, or explicitly regenerate from reviewed
evidence in the new source environment. Historical downloads/audits are preserved;
their identity is never rewritten to make them pass under changed source.

The source identity also includes line endings. Git checkout conversion can change
bytes even when the source commit is unchanged. This phase therefore retains
`accepted-replay-source.zip` with the exact backend bytes and offline entry points
used by its synthetic reports, plus archive/source hashes and runtime packages in
the new evidence directory. Both exports were verified from the extracted bundle.
This is archival replay evidence, not another active implementation or a complete
application deployment. Its SHA-256 establishes consistency with the retained
metadata, not authenticity against an independent trusted signature.

| Implemented functions | Verification |
| --- | --- |
| `attribution.engine.endpoint_effects` | Analytical trades/closures/dividends/fees/FX/cross-effects, spent foreign currency and UTC quote age |
| `attribution.engine.build_contribution` | Flow/order/correction cases, geometric linking, total loss, withdrawal/refunding, missing coverage, explicit residual and capacity |
| `ContributionValue.coherent`; `attribution.replay.verify_contribution` | Finite/null contract and changed result/methodology/exposure rejection |
| `attribution.routes.contribution` | Private API, coherent read-only PostgreSQL snapshots, lock, stale version and refreshed result |
| Performance controller and `ContributionResults` | Shared results from one request, edit/lock/account/late-response clearing, undefined presentation and real browser acceptance |
