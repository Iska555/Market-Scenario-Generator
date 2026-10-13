# Native factor-source review — Phase 9E

Implemented method: `french_developed_daily_source_review_v1`. This imports a
reviewed local French developed five-factor **daily** CSV into a source-review
receipt. It never produces `FactorEvidence` or enables regression. No network
fetch occurs in the application. The owner chooses a file and declares provenance.

## Input and validation

Private endpoint: `POST /api/factors/portfolios/{id}/source-review`. It uses the
existing private key and portfolio row lock to obtain the account currency.
It reads but does not mutate ledger/settings tables; responses and errors are
`no-store`. Request fields are `csv_text`, inclusive source-date `start`/`end`, and
`metadata` containing the fixed provider URL, actual `retrieved_at`, optional
`published_at`, supporting `publication_note` if supplied, and `review_note`.

Accepted input is at most 2,000,000 UTF-8 bytes, 25,000 source rows, and a selected
window spanning at most 3660 days. The parser requires the reviewed database-vintage
preamble, declared -99.99 sentinel and exact column order Mkt-RF/SMB/HML/RMW/CMA/RF.
Dates must be valid, strictly increasing and unique. All rows, including those
outside the selected window, must parse. Unknown preambles, additional sections,
columns, malformed dates/numbers and excessive precision fail explicitly. Current
support is intentionally restricted to this format; other regions/models can share
a header, so structural validation alone cannot authenticate origin.

## Numerical and provenance contract

Each numerical percentage is divided by 100 using decimal arithmetic. Exactly
-99.99 becomes null; -999 is not guessed to be a sentinel. Legitimate signed factor
tails are retained. RF must exceed -100% if present. No clipping, interpolation,
calendar filling, spread compounding, extra RF subtraction or FX is performed.
Output values serialize as decimal strings or null.

Native dates remain provider labels. There are no invented observed-at timestamps
or claims of UTC closes. Database vintage is distinct from publication. Unknown
publication stays null; a supplied publication time remains a claim requiring
independent review. Source dates cannot follow retrieval, and retrieval cannot be
later than the server's import time. The metadata is not authenticated by a hash.

Selected rows, complete source range/count, missing cells and gaps between selected
calendar labels are visible. A gap does not prove a missing trading observation;
an apparently contiguous or truncated file does not prove source completeness.
Even a USD account remains blocked on valuation, publication and funding policy.
A GBP account additionally shows currency mismatch. `regression_ready` is always
false for this native-review method. Existing daily regression contracts stay strict.

## UI, privacy and replay

Performance's “Review a public factor source” panel uses the reporting dates as
source-date selection, accepts the unzipped CSV, and asks for actual retrieval and
review metadata. A new file clears old provenance. Window edits clear the receipt;
account changes, lock, navigation and refresh clear all source state. Late reads
or responses cannot restore old private state. Review never changes factor inputs,
analysis checkboxes or benchmark settings. The table previews six selected rows;
the full receipt retains all selected rows and submitted text.

The submitted-text SHA-256 covers the UTF-8 encoding of the received string,
including its line endings/whitespace. It is **not** the ZIP hash or a guarantee of
original uploaded bytes: browser text decoding can remove a BOM. Receipt SHA-256
covers inputs, account context, import time, outputs, warnings and backend source
identity. These hashes check consistency, not authenticity.

Replay: `backend/.venv/Scripts/python.exe scripts/replay_factor_source.py review.json`.
Use the matching accepted source archive/runtime. Replay is offline and compares
the complete rebuilt receipt. Changing account context, inputs, provenance, units,
outputs, blockers or code identity invalidates an unchanged receipt. Someone who
rebuilds every field/hash can construct a different consistent receipt; this is not
a signature. Downloaded receipts contain supplied data/notes and remain private.

Actual-source acceptance uses the six-row attributed fixture under
`backend/tests/fixtures/french_developed_daily`; it does not establish real-account
alignment. Common-interval prerequisites are in [FACTOR_ALIGNMENT.md](FACTOR_ALIGNMENT.md).
