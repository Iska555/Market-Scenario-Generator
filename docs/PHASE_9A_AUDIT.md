# Phase 9A acceptance — reconciled position contribution

Date: **2026-10-09**. The owner explicitly selected this bounded stage after Phase 8
closeout. This new audit preserves earlier phase records; it does not revise their
original findings or acceptance status. Plan: [Phase 9A execution](superpowers/plans/2026-10-09-phase-9a-contribution.md).
Numerical specification: [ATTRIBUTION.md](ATTRIBUTION.md).

## Disposition

**Accepted for bounded local Phase 9A use:** private ledger-derived position/cash
contribution to Phase 8 TWR, with booked net dividends/fees/FX, closed equities,
flow-aware wealth linking, exact component values, visible residual/tolerance,
opening exposure evidence and offline replay. Acceptance includes actual disposable
PostgreSQL tests and synthetic populated/missing/corrected browser workflows.
It does not establish broker reconciliation, hosted CI, deployment or production
readiness. Benchmark/active-risk, factor regression, Brinson and publication remain
separate subsequent stages.

## Implementation and findings

| Location / issue | Disposition and evidence |
| --- | --- |
| Prior implementation had Phase 8 performance without position contribution | Added `attribution/contracts.py`, `engine.py`, `routes.py` and `replay.py`; main.py mounts the private route. No historical performance formulas or DB tables were changed. |
| Today's weights cannot explain historical trades and cash flows | Replays the same knowledge-visible corrected ledger; daily/flow segments retain opening quantities, values, cash and weights. Closed securities and within-segment round trips remain included. Equal-time events preserve sequence. |
| Standalone returns do not add to geometrically linked TWR | Uses Phase 8 units/flow deltas; divides each segment base P&L by outstanding units and sums increments of normalized wealth. The compounding convention is declared, not presented as a unique attribution method. |
| Local price, FX cross-effects, fees and conversion principal can be double-counted or ambiguous | Explicit endpoint identity: local capital/income/cost at end FX, opening security/cash FX separately, conversion principal separately. Trade principal cancels cash; booked fees/net dividends are counted once. Alternate payout currency and closed/foreign positions have analytical coverage. |
| Contribution may require FX when ending currency exposure is zero | Missing/stale end FX leaves the entire window contribution undefined while retaining independently available performance; valid partial segment diagnostics are not a complete-window claim. |
| `attribution/engine.py:endpoint_effects.rate` initially compared offset dates without UTC normalization | Repaired during development before acceptance; offset-timestamp age regression passes. The inherited Phase 8 UTC behavior remains intact. |
| A reconciliation residual must not be hidden in security returns | Reports `Phase8 TWR − exact component sum`, with fixed `1e-12 + 1e-12 × abs(TWR)` tolerance. Artificial mismatch test verifies visible failure without a plug. Segment monetary mismatch produces typed undefined output. |
| Mutable sector/ticker metadata cannot certify historical classification | UUIDs remain authoritative; no sector aggregation inferred. Rankings include only signed net equity effects, with cash/account/conversion effects separately displayed. |
| Two separately computed reports could observe different ledger versions | One contribution request embeds the performance report; the existing portfolio lock remains held through calculation. Actual PostgreSQL tests confirm the lock and unchanged contents of every migrated table. |
| New browser results must follow existing privacy/staleness rules | Opt-in controller transport returns both reports; all edits/import/template/account/lock/navigation actions clear both and generation guards reject late results. Private key is absent from controller state/downloads. |
| Contribution download requires executable verification | `scripts/replay_contribution.py` validates source/runtime, input/ledger identities and embedded financial results, then compares every contribution field. Changed effect, methodology and exposure are rejected in tests. Actual browser download and corrected API export both replay successfully. |
| Backend addition changes conservative Phase 8 source identity | Intended compatibility boundary documented. Prior downloads/audits/evidence are preserved; use their matching `890dd4a` source/environment or explicitly regenerate reviewed inputs. No retrospective identity rewrite. |
| Exact-byte identity is sensitive to Git line-ending conversion | Retained the exact accepted backend bytes/offline scripts in an archival source ZIP with SHA-256 metadata. Both synthetic exports successfully replayed from its separately extracted source under the resolved runtime. No source identity or output was edited to force compatibility. |
| Temporary edit encoding and browser diagnostics during acceptance | Windows default decoding damaged punctuation in new frontend edits; repaired from original source before full verification. Temporary sanitized error logging was removed before final client checks. A transient browser account-read failure was not reproducible in the API/controller or later fresh browser unlock; final version-5 calculation and subsequent fresh unlock succeeded. No unverified root cause is claimed. |

Initial analytical fixture construction/date mistakes were corrected during development.
Those failed development runs do not count as passing acceptance. Final results below
come from the complete corrected suite. No historical audit was edited to hide them.

## Fresh verification

Executed `scripts/verify.ps1 -EvidenceDirectory .verification/phase9a/full` with an
isolated PostgreSQL URL on loopback port 55439 and bounded BLAS threads. Runtime:
Windows 11, Python **3.12.14**, PostgreSQL **17.11**, Node **24.18.0**, npm **11.16.0**,
Vite **7.3.7**. Dependencies and the 95% coverage threshold were unchanged.

| Gate | Result |
| --- | --- |
| Full backend including PostgreSQL | **579 passed, zero skipped**, 89.60s test execution |
| Combined statement/branch coverage | **97.64%**, above unchanged 95% gate |
| New attribution coverage | 30 analytical cases, 3 API cases and 2 actual-PostgreSQL cases |
| Ruff check / formatting | Passed; **122 files** already formatted |
| mypy | Passed over **118 source files** |
| Dependencies / configured hooks | Passed; staged-file hooks also checked before checkpoint |
| Frontend | **125 passed**, zero failures/skips; six new contribution tests |
| ESLint / production build | Passed; final client rechecked after temporary diagnostic removal |
| Existing scenario benchmark | 1,000 paths × 252 periods × 5 assets: Gaussian **0.2330s**, GMM **0.4676s**; excludes network/HTTP/UI |
| Offline retained reports | Actual browser download and corrected API report verified independently of DB/provider, also from the extracted exact-source bundle |

The backend emitted one inherited Starlette/AnyIO alias deprecation warning.
The Vite build retained its existing >500kB chunk warning: JS 750.91kB (220.45kB
gzip), CSS 35.90kB (7.55kB gzip). Neither warning was suppressed by relaxing a gate.
The scenario benchmark is regression evidence, not a contribution load test.

Analytical acceptance includes opposing equity effects, partial/new purchases,
full closure and round trips, net dividends in another payout currency, standalone
and trading/conversion fees, security/cash FX, conversion spread, multiple flows,
equal-time sequence, prior/later-known reversal, 100→110→121 compounding,
pre-funding/empty cases, total loss, full withdrawal/refunding with retained gains,
missing/stale evidence, UTC-offset quote age, explicit residual mismatch and capacity.

Actual PostgreSQL acceptance verifies all-table content unchanged on repeat requests,
identical outputs, a competing writer's lock timeout (`55P03`) while contribution
holds the portfolio lock, successful writing afterward, stale `409`, and refreshed
fee/NAV/TWR/contribution consistency. These are migrated disposable schemas, not
mock-only claims. Synthetic schemas and services were removed/stopped after checks.

## Browser and replay acceptance

Used only a disposable synthetic account. Deposit 100 GBP; buy one equity at 100;
marks 100/120/130; second deposit 110 at a pre-flow mark of 110; fee 10.
Opening units 100 become 200 after funding. The January 1–3 window gives:

- Final NAV **230**, TWR **15.00%**.
- Equity **+20.000pp**, standalone fee **−5.000pp**, cash **0.000pp**.
- Linked segment increments **10pp + 5pp + 0pp**, residual **0E−10**,
  tolerance **1.15E−12** decimal return; reconciliation passed.
- Actual contribution download was retained and verified by the offline command.

Removing the January 2 price made TWR and whole-window contribution explicitly
undefined, with no equity ranking or invented zero; final independently valued NAV
remained available. Reversing the fee advanced the ledger from version 4 to 5;
using the old version produced a stale error and removed both results. Fresh account
loading and reviewed evidence then gave NAV **240**, TWR **20.00%**, equity
**+20.000pp**, no standalone-fee component, residual **0E−10** and tolerance
**1.2E−12**. The corrected API export also replayed successfully. XIRR was honestly
undefined outside supported root bounds in this short corrected synthetic window.

Inspected desktop, mobile and dark-theme results, opening exposure/transaction
details, correction refresh and lock clearing. At the 390px viewport setting,
document width and client width both measured **375px**; wide tables scroll within
their containers. Lock removed the contribution heading; page refresh required
unlock and cleared evidence/results. Final client browser checks recorded no
console errors. A browser download wait took substantially longer than its requested
timeout; the returned actual file was retained and verified rather than substituting
a fabricated download. See screenshots and JSON under
[verification/phase9a-2026-10-09](verification/phase9a-2026-10-09/README.md).

## Preservation and next boundary

Task-entry byte sizes/SHA-256 values were retained before edits. The final proof
compares full files for the master brief, every existing audit/review and every
Phase 8 evidence file, and the original byte prefix of BRIEF_SUGGESTIONS.md.
All **35 records** pass. New suggestions are appended; previous records are untouched.
The result is a local reviewed checkpoint on the existing project branch, without
push, deployment or publication.

Next work follows the approved benchmark/active-risk stage with explicit versioned
benchmark identity, total-return/currency/calendar/effective-date alignment and
coverage gates. Statistical factor attribution remains later. Historical sector
classification/benchmark weights are prerequisites for Brinson. Real-account native
broker fixtures, deliberate fund/ETF support, ledger-to-construction integration,
deployment/restore and public-data separation remain outside this acceptance.
