# Phase 3 research API and persistence

The research layer stores equity identities and fundamental observations. It is
accessible through the typed API and `/docs`; this phase adds no research screen,
thesis system, expected-return model or automated provider download. The existing
Risk & Scenario Lab remains usable without database configuration.

## Local database setup

Install the pinned backend requirements, including development requirements for
tests. PostgreSQL 17 is the current verification target. SQLAlchemy 2.0.52,
Alembic 1.19.2 and psycopg 3.3.4 are pinned. Production database URLs must explicitly
use `postgresql+psycopg://`; SQLite is only an ephemeral test double.

From the repository root in PowerShell, choose a local development password and
a separate owner key (at least 32 characters; generate a random secret). Do not
commit either value. URL-encode reserved characters in the database password.

```powershell
$env:RESEARCH_DB_PASSWORD='<local-development-password>'
docker compose -f compose.research.yml up -d --wait
$env:DATABASE_URL='postgresql+psycopg://research:<URL-encoded-password>@127.0.0.1:54329/research'
$env:RESEARCH_API_KEY='<separate-random-owner-key-at-least-32-characters>'
backend/env/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
backend/env/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload
```

Migrations run only through this explicit command, never at application startup.
Select the intended database before running a migration. The supplied compose
file binds PostgreSQL only to loopback and uses a named persistent volume.
`docker compose -f compose.research.yml stop` stops it while preserving data.
Do not use `down -v` unless intentionally deleting the development data.

An existing PostgreSQL instance is also supported; point `DATABASE_URL` at a
dedicated database and run the same migration command. Hosted deployment and
database provisioning are not part of this phase. Research routes default to
503 when the database URL or key is not configured. A missing/wrong key returns
401 once configured. Use `X-Research-Key` for every research operation.

## API surface

| Method/path under `/api/research` | Behavior |
|---|---|
| `GET /metrics` | Catalogue of 28 keys with labels, categories and units |
| `POST /securities` | Register an equity and assign an immutable UUID |
| `GET /securities?limit=100&offset=0` | Bounded current security-master list |
| `GET /securities/{id}` | Current descriptive identity |
| `PUT /securities/{id}` | Replace descriptive fields while preserving UUID and creation time |
| `POST /securities/{id}/fundamentals` | Atomic import of 1–500 observations; repeat immutable records reuse original IDs |
| `GET /securities/{id}/fundamentals?as_of=...` | Latest eligible published revision for each source/metric/period/basis/currency series |

Listing limits are 1–500, offset is nonnegative. Fundamental queries return
`items`, `as_of`, resolved `known_at`, `limit` and `offset`. Reuse those exact
cutoffs across pagination to keep eligibility stable. The list includes all
eligible reporting periods; it does not silently select one latest fiscal period
or combine data vendors. Optional `source` is an exact source-name filter.

Security UUIDs, never tickers, link observations. Exchange/ticker pairs are unique;
renaming either preserves facts. Sector, industry, ISIN and FIGI are optional.
Country/currency and identifier syntax are checked, but no security registry,
ISIN checksum, quote currency or corporate-action identity is independently
verified. Security metadata is **current only**; historical sector/classification,
ticker aliases, delistings and cross-listing consolidation are not implemented.

## Minimal import example

Using the same PowerShell environment:

```powershell
$headers = @{'X-Research-Key'=$env:RESEARCH_API_KEY}
$asset = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/research/securities' `
  -Headers $headers -ContentType 'application/json' -Body '{"ticker":"EXAMPLE","exchange":"XNAS","name":"Synthetic Example","currency":"USD","country":"US"}'
$body = @'
{"observations":[{
  "metric":"net_margin","value":"0.125","unit":"fraction",
  "period_start":"2024-01-01","period_end":"2024-12-31","period_kind":"annual",
  "reported_at":"2025-02-01T12:00:00Z","fetched_at":"2025-02-02T12:00:00Z",
  "source":"synthetic-example","source_record_id":"2024-net-margin-original",
  "source_document":"synthetic-annual-report-2024","basis":"consolidated reported"
}]}
'@
$url = "http://localhost:8000/api/research/securities/$($asset.id)/fundamentals"
Invoke-RestMethod -Method Post -Uri $url -Headers $headers -ContentType 'application/json' -Body $body
Invoke-RestMethod -Uri "${url}?as_of=2025-03-01T00:00:00Z" -Headers $headers
```

This is fabricated test data, not an actual issuer filing. A real importer must
provide genuine source publication timestamps and normalized values. No timestamp
is inferred from a fiscal period end, current API response, or fetch date.

## Availability and revisions

- `period_start`/`period_end`: the fiscal duration, valuation date or forecast
  horizon the number describes. Kinds are `instant`, `quarter`, `annual`, `ttm`,
  `estimate`. Duration observations require a start; instant observations have
  none. Forward P/E must use `estimate` and can describe a future horizon.
- `reported_at`: when this exact source version was published, with timezone.
  Later restatements retain their actual later publication timestamp.
- `fetched_at`: when this source version was obtained, with timezone; must be at
  or after publication and cannot be in the future at import.
- `recorded_at`: application-server UTC time of first successful ingestion;
  clients cannot set it. Stored constraints require reported ≤ fetched ≤ recorded.

Eligibility is `reported_at <= as_of AND recorded_at <= known_at`. Since
fetched ≤ recorded is enforced, the knowledge cutoff also excludes later fetches.
`known_at` defaults to the current server time: this reconstructs public history
using facts archived so far. To ask what **this system** knew on a past date,
also set `known_at` to that date. An old publication imported today is not
visible to a historical system-knowledge query. Inclusive timestamp boundaries
are used; date-only cutoffs are rejected rather than assigned an implicit time.

After filtering, revisions are ranked by publication time within the security,
metric, period start/end/kind, basis, currency and source. Distinct sources and
accounting bases remain distinct. A unique publication fingerprint prevents two
competing versions in the same series at the same publication timestamp.

The pair `(source, source_record_id)` identifies one immutable fact version,
not just a filing containing many facts. A repeated import with equal content
reuses its UUID and first fetch/recording times; a later repeat fetch alone is not
a new observation. Changed content under that same source ID returns 409.
Restatements require a new source record ID and their actual publication time.
Concurrent duplicates may conflict at the database uniqueness constraint; retrying
the identical import then resolves to the already stored record.

An import batch is all-or-nothing. Conflicts cannot leave preceding batch rows
behind. PostgreSQL prevents UPDATE and DELETE of observations with a trigger;
application code exposes neither operation. Administrators can still alter schema,
so this is data discipline rather than tamper-proof storage. Retractions, revisions
that change series identity, source-ID remapping and administrative correction
workflows are not implemented; they must not be represented as ordinary value
restatements in this version.

## Numeric and provenance contracts

Values use Decimal and PostgreSQL `NUMERIC(30,10)`. Inputs exceeding 30 total
digits or 10 fractional digits are rejected instead of silently rounded. Decimal
JSON results are strings. Zero and negative values remain signed. Currency amounts
are whole currency units, ratios are dimensionless multiples, and fractions use
0.15 for 15%. Only monetary observations require a three-letter currency.

Each fact requires `source`, `source_record_id`, `source_document` (URL/accession
or other locator), and `basis` explaining accounting scope and formula convention.
Raw filings are not fetched or archived. Fingerprints verify import identity,
not the truth of a vendor's publication time or the immutability of its URL.
Missing metrics are absent, never converted to zero. No sector must supply every
metric. See [RESEARCH_METRICS.md](RESEARCH_METRICS.md) for definitions and the two
implemented calculation primitives; the catalogue is not an automatic calculator
for all 28 metrics.

## Reproducible checks

Run the normal full checks from README. To include real PostgreSQL tests:

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://<test-user>:<password>@127.0.0.1:<port>/<test-db>'
backend/env/Scripts/python.exe -m pytest
```

Use a dedicated test database whose role can create schemas. Tests create uniquely
named schemas, migrate/use them and remove only those schemas. Repository cases
run on SQLite and PostgreSQL when the variable is present. Without it, the explicit
PostgreSQL migration/precision/immutability check is skipped; SQLite checks cannot
establish PostgreSQL guarantees. CI provisions its own PostgreSQL 17 service and
sets the variable. Test inputs remain synthetic and never fetch external data.
See [PHASE_3_AUDIT.md](PHASE_3_AUDIT.md) for actual local results and review limits.
