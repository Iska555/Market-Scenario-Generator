# Portfolio benchmark settings — Phase 9D

The account owner saves an explicit reviewed benchmark identity. Saving is a
human choice, not a suitability recommendation. These settings contain identity
and provenance, never provider levels, investor expected returns or factor data.

## Persistence and revisions

Migration `20261011_04` adds `portfolio_benchmark_settings` after the accepted
ledger migration. Existing accounts start at setting revision 0 with no choice.
Each append uses a caller UUID, expected current setting revision, full
`BenchmarkIdentity` or null, and a nonempty reason (up to 2000 characters).
The server records a monotonic UTC timestamp and revision. Currency must equal
the account currency; retrieval/publication cannot be future-known at save time.
The existing identity contract declares total-return basis, hedging, effective
window, daily calendar, source and methodology.

The portfolio row lock serializes settings and ledger work. Setting revisions
are independent of transaction sequence: saving never increments ledger version.
Update/delete triggers protect settings on PostgreSQL. Clearing appends a null
identity; it does not remove history. New settings never alter saved reports.
No automatic migration runs during application startup.

An exact retry of a UUID with the same portfolio, identity and reason returns
the original row, even after later revisions. Reuse with different content is
a conflict; a new UUID with a stale expected revision is also a conflict. The
client retains an unresolved request UUID for retry until inputs are changed,
then reloads current settings after successful saves. A failed connection may
occur after a commit; retry/reload resolves that uncertainty. Lock/navigation
clears in-memory retry state; persisted settings remain on the private server.

## Private API

- `GET /api/benchmark/portfolios/{id}/settings?limit=20&offset=0` returns latest,
  revision, total and descending records. Limit 1–100; offset nonnegative.
- `POST /api/benchmark/portfolios/{id}/settings` appends with the contract above.
- All benchmark responses, including expected authentication/schema/domain
  errors, receive `Cache-Control: no-store`. Keys are never in settings or exports.

The UI shows the latest 20 revisions; the API provides complete pagination.
Review settings in Performance, paste an identity or copy reviewed report identity,
enter a reason, then save or clear explicitly. Using a saved identity prepares an
empty level template and opts into benchmark comparison. Filling/importing evidence
clears its saved-revision link; use **Link reviewed evidence to saved revision**
after reviewing matching identity. No values are filled or selected automatically.

## Selection receipt and replay

Comparison and factor requests may include `saved_benchmark_revision`. Omission
keeps the existing report-only explicit choice. Factor requests require benchmark
evidence when this field is present. Under the same locked report snapshot, the
server checks current revision, non-cleared choice, exact identity equality and
setting recording time at or before `known_at`. A changed setting yields 409;
identity/cutoff mismatch yields 422. Knowledge-aware selection does not silently
fall back to an earlier revision or use a later default.

`ComparisonReport.selection` retains the full selected immutable row, including
UUID, portfolio, setting revision, reason, identity, recording time and SHA-256.
Factor reports retain this through their nested comparison. The content hash
uses canonical sorted JSON excluding the hash, with recording time normalized
to UTC. Replay validates hash, account, identity, recording/provenance cutoffs,
embedded reports and recalculated results; it needs no settings database. Hashes
detect inconsistent retained content, not malicious re-signing or authenticated
attestation. No online currency/default lookup occurs during replay.

Financial formulas, interval/coverage policy and estimators remain unchanged.
New fields/source/warning text change conservative replay identity; old reports
continue to use their exact accepted source archives. Earlier hashes and archives
must not be rewritten to force compatibility.

## Data readiness and remaining scope

[FACTOR_DATA_READINESS.md](FACTOR_DATA_READINESS.md) defines review requirements
before real research factors can satisfy the current UTC/currency contract.
Settings do not solve that mismatch. No currency transformation, trading-calendar
adapter, provider ingestion, HAC/rolling estimator, Brinson or public track record
is delivered by Phase 9D. The account owner still chooses a suitable benchmark.
