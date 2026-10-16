# Launch L2 acceptance — original reproducible demonstration

Accepted **2026-10-14**, Europe/London, after bounded L1 acceptance. Scope:
L2.1–L2.3 of PLAN.md. The permanent master and all earlier records retain their
original text. [Evidence](verification/launch-l2-2026-10-14/README.md).

## Disposition

Accepted locally for a deliberate original synthetic demonstration, separate from
legacy/private, paper and future real-account histories. No broker execution,
personal historical decisions, verified personal track record, public publication,
backup restore, staging or deployment is claimed. Broader Phase 9 is unfinished.

[DEMONSTRATION.md](DEMONSTRATION.md) records setup, interpolation/valuation policy,
actual versus fictional dates, hand checks and private replay/archive limitations.
The immutable versioned fixture is `backend/demo/launch_v1.json`; no third-party
prices, research or native broker fixture are used in this demo.

## Implementation and findings

| Location | Finding / resulting behavior |
| --- | --- |
| public_track_record/demo.py | Explicit mode/currency/empty-history guards; an atomic savepoint creates two isolated fictional equities, 13 immutable ledger events, two theses/four revisions/two reviews and one immutable receipt. Exact reload preserves counts and identities. Modified ledger/research/security identity rejects reuse rather than resetting history. |
| new 20261014_06 migration | Additive immutable receipt storage; no old migration/ledger contract changed. Actual PostgreSQL checks cover concurrent loads and blocked receipt mutations. |
| original fixture | Covers funding, withdrawal, buys/sells, fees, dividends, FX, cash, closed loss and correcting reversal/replacement. Original daily anchors/flat-within-day quotes are declared synthetic inputs, not real-market carry-forward or broker evidence. |
| scripts/load_demo.py | Deliberate existing-demo load or explicit new creation; rejects nonempty output directories. Exports private reports, exact original inputs, load receipt, source/runtime/hash manifest and bounded compatible backend source. Not a public export or DB backup. |
| Ledger / Performance controllers | Explicit owner load/setup actions; never automatic sample population. Generation guards reject late/locked/wrong-identity inputs. Evidence setup selects contribution and original comparison, then requires Measure to calculate. Result heading and filenames explicitly identify synthetic data. |
| ThesisWorkspace.jsx Field/default labels | Browser inspection found pre-existing corrupted separators, ellipses and minus symbol. Repaired only those display literals. Final frontend tests/lint/build and browser dropdown recheck pass; research content and historical records are untouched. |
| Development contract checks | Corrected test references to existing replay/comparison field names, narrowed optional Decimal assertions and formatting before acceptance. No reporting formula was altered to make the example pass. |
| Verification services | The prior disposable services stopped across continuation. First new schema preparation timed out; restarted existing isolated PostgreSQL and completed preparation/gates. No stopped service/run is a passing claim. |
| Browser evidence setup | First evidence setup showed unavailable; coherent account reload and retry succeeded. A direct API/controller probe and final refreshed production-build keyboard setup succeeded. Rejection did not calculate partial results. |
| Browser downloads | Actual performance JSON was saved and replayed from working and archived source. Download event/path tool reported delivery after a long tool-side wait, not application latency evidence. Contribution/comparison buttons were exercised but saved-file delivery was not established; their CLI exports were replayed independently. Earlier download qualifications remain unchanged. |

## Independent numerical and reproducibility evidence

Final GBP cash **6154**, USD cash **2100**, Harbor quantity **40**, local cost
**2404**, NAV **10516**. Orchard's fully closed local net loss is **USD -400**.
The first invested closing NAV is **9985.88125**, return **-0.001411875**.
Hand arithmetic is documented separately; final NAV less net funding is not TWR.

Whole-window TWR **-0.002394074812561706** (-0.2394%). Contribution residual
**-2.732811729637569…e-19**, allowed tolerance **1.002394074812561706e-12**;
reconciled. The closed loser remains in contribution/rank history. Synthetic
comparison grows 100→102, with **47/47** paired intervals. Missing marks,
invalid FX and incomplete benchmark cases fail or remain typed unavailable.

The period is 2025-12-20→2026-02-05: 48 closing values, 47 return intervals,
partial December/February and a full January. Both calendar years are partial.
Annualized TWR remains unavailable. Private XIRR/ratio warnings identify the short
sample and mathematical annualization; no persistent-skill inference is made.

Two CLI loads preserve byte-identical receipt, evidence, fixture and all three raw
reports. Each report replays using working source and separately extracted compatible
source. The actual browser-delivered performance file also replays under both.
The fixture is retained alongside the source archive and compatible runtime manifest;
hashes establish consistency, not authenticity or external attestation.

## Fresh configured gate and browser acceptance

Final full runner `.verification/launch-l2-2026-10-14-run2`: **770 backend passed**,
zero skips, **97.89%** statement/branch coverage; **165 frontend passed**, zero
failures/skips. Dependencies/Ruff/format/mypy/hooks/benchmark/lint/build all exit 0.
After the small thesis punctuation repair, the complete frontend suite/lint/build
passed again; no backend source or report inputs changed. Python 3.12.14,
PostgreSQL 17.11; CI's other runtime/PostgreSQL profile and hosted CI were not run.
Inherited Starlette deprecation and Vite main-bundle size warning remain.

Production-build browser setup creates a separate empty demo and intentionally
loads the original fixture. Reload/second load preserve the complete history.
Displayed GBP/USD balances, cost/quantity, TWR, contribution and comparison agree
with backend outputs. A losing thesis preserves its original active revision,
closed revision and EXIT example review; example date 2025-12-21 differs from actual
2026-10-14 record timestamps. No required-return view was fabricated or adopted.
Keyboard Enter runs setup/measurement. Desktop **1280×900** and mobile **390×844**
were measured; mobile document width **375**, with contained horizontal tables.
This fresh hidden-tab workflow resolves the earlier L1 viewport limitation without
rewriting L1's historical default-width evidence. Lock/refresh return locked Overview
and clear private evidence; final localhost console capture has no errors.

## Remaining limits and next step

The private replay reports are not sanitized public downloads. Contribution/comparison
browser delivery remains unverified, although both CLI/archive replays passed.
No public response, publication or operational recovery is accepted by L2.

Continue **L3.1: typed allowlisted public snapshot and safe fixture-backed local
preview**, then backend aggregation/public performance/holdings and selected fictional
research/closed positions/journal. L4 publication and L5/L6 operations/deployment
remain ordered gates. No deferred real-account/factor analytics are launch blockers.
