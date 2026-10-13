# Phase 9E acceptance — native factor-source review

Closeout: **2026-10-13**. Work began 2026-10-12 after entry commit **913ccb1**;
the owner reiterated continuation during closeout. Scope:
[execution plan](superpowers/plans/2026-10-12-phase-9e-source-review.md).
This is a new record; historical master/audits/evidence retain their original text.

## Disposition

**Accepted for bounded local source review:** strict offline French developed
five-factor daily CSV parsing, private account-context preview, visible native
currency/calendar/provenance blockers, downloaded receipt and independent replay.
The application makes no provider call and does not promote a source review to
daily regression evidence. Existing financial formulas and daily evidence contracts
are unchanged. Broader Phase 9 remains incomplete.

[FACTOR_SOURCE_IMPORT.md](FACTOR_SOURCE_IMPORT.md) describes the implementation.
[FACTOR_ALIGNMENT.md](FACTOR_ALIGNMENT.md) specifies a proposed common-boundary
method; those calculations are **not implemented or accepted**. The raw source does
not resolve actual portfolio valuation boundaries, research-currency funding or
historical publication availability. No real-account regression, FX adapter,
HAC/rolling, Brinson, public track record or hosted deployment is claimed.

## Findings and implementation

| Location / issue | Resolution or explicit boundary |
| --- | --- |
| Factor inputs previously required already-reviewed daily JSON | Added `factors/source.py`, an independent native-source review contract/parser; it cannot validate as existing `FactorEvidence`. |
| Provider percentages and missing values could be misinterpreted | Exact decimal percentage division by 100; only declared -99.99 is null. Signed extremes and -999 factor values are retained. RF below/equal -100% fails. No clipping, filling, second RF subtraction, compounding or FX. |
| Loosely reading a CSV could silently drop malformed/out-of-window rows | Require supported preamble/vintage/header, seven columns, bounded exact numeric syntax and unique ascending valid dates. Validate every source row before selecting an inclusive window; unknown sections/footer/format fail. |
| Payload and provenance ambiguity | Bound submitted UTF-8 text to 2 MB, source to 25,000 rows and selection to 3660 days. Preserve submitted text, exact hash and metadata. Browser text decoding/textarea normalization can change raw file bytes; submitted-text hash is explicitly distinct from original-file/ZIP hash. |
| Source date or vintage could be mistaken for historical knowledge | Keep date labels separate from timestamps. Publication defaults to unknown; a supplied time needs an evidence note and remains an unverified claim. Reject future retrieval/source dates. Vintage is not publication. |
| A parsed file could appear suitable for GBP analysis | `regression_ready` remains false; show currency, boundary, risk-free/funding and publication blockers even for otherwise complete rows. USD account context does not remove noncurrency blockers. Structural checks do not certify provider origin or source completeness. |
| Privacy/account scope | New route uses existing authentication, portfolio row lock and no-store middleware. Account currency comes from the selected account. Actual PostgreSQL snapshots show no table changes after successful/rejected previews. |
| Import UI could restore stale/private state | Added explicit source review panel and optional transport. New file clears provenance; edited source/window clears receipt. Account change/lock/refresh clear source state; generation guards reject late reads/responses. Review leaves factor evidence and analysis checkboxes unchanged. |
| Reproducibility | Retain complete review inputs/outputs/context and backend identity in a receipt; offline CLI rebuilds and compares all fields. Hashes establish consistency, not authenticity or a signature. |
| Original provider fixture line endings | Added narrowly scoped `.gitattributes` byte-preservation/whitespace rules for the exact CSV excerpt, preserving its recorded byte hash across Git checkouts. Git initially flagged the provider's CR-CR-LF bytes as trailing whitespace; the exception applies only to this untouched source fixture. |

Initial style/typing checks found line-length/import ordering and optional Decimal
narrowing issues; these were corrected before final gates. The first scoped
backend run stopped producing output after its non-API cases, and an initial
frontend discovery run also stalled. Both were stopped; diagnostic/direct reruns
passed, followed by the complete suite. No passing claim relies on stopped runs.
The standalone frontend rerun emitted a Vite dependency-scan shutdown warning;
the final full run passed. The first browser navigation preceded dev-server
startup; the error-page binding was unusable, so a fresh local tab was used.
The download tool returned after a long tool-side wait; delivery was then verified
from the actual saved file, without treating that delay as app performance evidence.

## Actual source review

Retrieved the official developed daily ZIP on **2026-10-12T14:48:51.017259Z**.
Its member identifies database vintage **202608**. Parsed **9436 rows**, from
1990-07-02 to 2026-08-31. The six selected actual observations matched the retained
exact prefix fixture through 1990-07-09. Retrieval, full ZIP/member hashes and
excerpt hash are recorded in the fixture provenance. The complete provider file
was inspected locally; the repository retains a minimal attributed numerical
fixture, not the whole dataset or a general redistribution-license assertion.

The source description establishes USD returns and trading-day risk-free
construction; it does not establish synchronized portfolio valuation boundaries.
[Primary description](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5developed.html).
Publication availability stays unknown. Synthetic mutated cases are explicitly
tests for sentinel, extreme, precision and validation behavior; they are not
presented as provider observations or a real portfolio.

## Fresh verification

| Gate | Result |
| --- | --- |
| Full backend, including actual PostgreSQL | **733 passed**, zero skipped; 138.88s |
| Statement/branch coverage | **97.93%**, above the unchanged 95% gate |
| New source cases | **36 contract/numerical/API/replay**, **1 actual PostgreSQL** |
| Ruff / formatting / mypy | Passed; **149 files** formatted, **141 source files** typed |
| Full frontend | **153 passed**, zero failed/skipped; six new source-review cases |
| Hooks / dependencies / lint / production build | Passed; full runner completed with all zero exits |
| Scenario observation | Gaussian **0.1852s**, GMM **0.3698s**, existing 1000×252×5 workload |
| Independent replay | Actual browser download and two API receipts passed against working and separately extracted **89-file** source |
| Historical preservation | **186/186** full-file/original-suggestions-prefix checks |

Final build: 2351 modules, 10.34s, 788.78 kB main bundle (228.91 kB gzip).
Inherited Starlette deprecation and Vite bundle-size warnings remain visible.
Local timings exclude network/HTTP/client where stated; no improvement/capacity
claim. Python3.12.14 and existing pinned dependencies were used. Exact replay
requires compatible source/runtime; archive scope excludes migrations, dependency
installation, frontend and deployment. Earlier reports retain their own archives.

## Browser, exports and cleanup

Used an isolated synthetic GBP account with ledger version 0 and the six-row
actual provider excerpt. No holdings, transactions or invented market returns
were created. The desktop view displayed six decimal rows, native USD, zero
missing cells, one two-calendar-day gap and all four readiness blockers.
The analysis checkbox remained off. Light desktop and 390×844 mobile views were
visually inspected; mobile document width was 375, with horizontal table scrolling.
Edited review note removed the receipt. Lock/refresh returned locked Overview;
unlocking again showed blank source/provenance/window fields and no old receipt.
Final localhost console capture contained no errors. No dark-theme test is claimed.

“Download source review” delivered an actual local JSON file. Copied that exact
file into acceptance evidence and verified its offline replay from working and
extracted source. This confirms **this source-review download**, not earlier
performance/comparison download qualifications; historical audits are unchanged.
Browser acceptance used the CSV text field; the file-input path is covered by
client controller tests but was not exercised through a browser file chooser.
Two actual API exports cover normal native review and an empty selected window;
invalid source input returns sanitized no-store422. No source import is persisted.

The owner's later continuation stopped the disposable services after verification.
Restarted only the isolated database to remove the exact Phase9E schema, then
stopped it. Cleanup evidence records the result. Browser viewport was reset.

## Next procedure

Proceed to a separately versioned common-boundary measurement implementation
under FACTOR_ALIGNMENT.md with analytical reconciliation tests. Keep real-factor
integration gated on an actual reviewed boundary/valuation/FX/funding fixture and
publication evidence. A labelled USD research view is a candidate, not an adopted
GBP conversion policy. Do not invent those inputs or relabel source dates to pass
the current daily contract. Then scope serial-dependence-aware inference and
rolling beta/capture. Brinson still requires historical classifications/weights;
other broker/fund/restore/publication integrations retain their own gates.

[Evidence index](verification/phase9e-2026-10-12/README.md).
