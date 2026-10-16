# Portfolio identity boundary — launch L1

Accepted local scope: 2026-10-14. The owner approved the launch plan on 2026-10-13.

`portfolio_identities` is an additive, immutable registry keyed by the existing
accounting portfolio UUID. No old row is migrated to a mode. Absence means
`unclassified`, private and ineligible. The existing accounting request/response
contracts, ledger economic conventions and historical replay manifests are unchanged.
New backend source correctly changes new source fingerprints; old reports require
their matching retained archive and runtime.

Modes have distinct meanings: `demo` is synthetic, `paper` is prospective
hypothetical history, and `real` denotes actual-account history without certifying
reconciliation. The first-release creation API accepts only an explicit `demo`.
Paper and real creation remain deferred. No mode means broker verification.

Owner-only `GET /api/portfolio-identity/portfolios` adds an `identity` to the old
portfolio response. `POST` accepts UUID, name, base currency and required demo mode.
It fixes the broker/account labels to Synthetic demonstration / No real money
invested. Creation records actual UTC time, independent of fixture-effective dates.
Exact retries return the same identity. Changed attributes, attempts to reuse a
legacy/paper/real UUID and unsupported creation modes are rejected. There is no
mode-edit endpoint. Legacy accounting creation still works and remains unclassified.

The portfolio and identity insert occur in one live database savepoint. PostgreSQL
requires that the portfolio's inserting transaction lock is still held by this
session, a matching creation timestamp and no ledger history. Committed legacy
rows, including empty ones, cannot acquire a retroactive identity. Updates/deletes
of classified identities are blocked by a trigger. This uses PostgreSQL
[transaction locks](https://www.postgresql.org/docs/17/xact-locking.html), including
the live savepoint's lock; releasing that savepoint before identity insertion is
unsupported. SQLite portable tests use application guards; actual PostgreSQL tests
verify database enforcement. Database administrators retain privileged control.

`publication_eligible=true` means only that demo mode is a candidate for a later
reviewed snapshot. Every L1 response has `visibility=private`, `broker_verified=false`.
It is not published content, data provenance review or a privacy acceptance receipt.
No anonymous read/write or public export is implemented in L1.

The frontend uses a separate private adapter for identity-aware account lists and
demo creation. Financial requests still use the accepted accounting/performance
endpoints. Overview, Ledger and Performance show the identity with private status.
Switching modes in the creation form resets the UUID/draft; it never modifies
the selected history. Demo transaction/import source defaults are synthetic.
Selection clears prior financial state; lock/refresh clear private memory. There is
no automatic sample population of a personal dashboard.

Migration downgrade drops identity evidence and is a test-only schema roundtrip,
not an operational rollback. L5 recovery must preserve the additive registry.
