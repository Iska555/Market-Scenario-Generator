# Phase 3 audit — fundamental research data model, 2026-09-08

## Authorization and boundaries

The owner explicitly requested Phase 3 after completion of Phase 2, then asked
to continue. A subsequent injected AGENTS.md repeated the older Phase 2 boundary;
the specific Phase 3 build request remained the task authorization. The local
AGENTS.md and build plan now record the Phase 3 boundary and stop before Phase 4.
`docs/MASTER_BRIEF.md` is preserved. Earlier uncommitted Phase 1/2 work and the
user's older August-plan edit remain in place on `phase-1-correctness`.

Phase 3 builds the backend data model and calculation infrastructure, with API/
OpenAPI access. It does not add thesis/research dashboards, expected-return
models, portfolio optimization, ledgers, performance accounting or publishing.

## Findings and implementation

| Classification | Original location / concern | Disposition |
|---|---|---|
| DESIGN DEBT | No original `backend/src/research/` domain or stable research security identity | Added equity security master with UUID foreign keys, optional classification/identifiers, and unique exchange/ticker labels. Renaming preserves observations. |
| DESIGN DEBT | No persistent point-in-time fundamental observations | Added SQLAlchemy mappings and Alembic migration for PostgreSQL, with fiscal period/kind, reported/fetched/recorded timestamps, metric/unit/currency, source/version/document and accounting basis. |
| DESIGN DEBT | No research data availability/revision selection policy | Added publication and independent system-knowledge filters before per-series revision ranking. Different sources, periods and bases are kept separate. |
| CONFIRMED BUG — repaired during new implementation | `research/repository.py::observations` originally could rank conflicting same-publication facts arbitrarily | Added `version_fingerprint` and unique publication constraint. A failing regression demonstrated the ambiguity; the final code rejects competing versions with 409. |
| DESIGN DEBT | No repeatable, atomic fact import | Added immutable source record identity, canonical content fingerprinting, batch savepoints and outer HTTP transactions. Repeat equivalent imports retain original IDs/timestamps; changed source IDs/content conflicts cannot leave partial inserts. |
| DESIGN DEBT | No defined fundamental metric vocabulary or calculation infrastructure | Added all 28 Phase 3 metrics and tested Decimal ratio/growth primitives. Documented source-dependent mappings rather than claiming 28 automated valuation functions. |
| DESIGN DEBT | Existing simulator had no authenticated database-writing API | Research routes are opt-in and private, with a separate owner key and PostgreSQL-only configuration. Reads/writes share access checks; failed commits roll back before HTTP success. |
| CORRECT AS IMPLEMENTED | Existing simulation domain, statistics and chart contract | No financial formula changes. The simulator's full inherited suite passes with research disabled or configured. |

## Changed files and responsibilities

- `backend/src/research/`: `metrics.py`, `schemas.py`, `tables.py`, `repository.py`,
  `database.py`, `routes.py`, package initializer.
- `backend/migrations/`, `backend/alembic.ini`: versioned schema, precision and
  availability constraints, source/publication uniqueness, PostgreSQL update/
  delete rejection trigger. Migration uses explicit columns rather than runtime
  `create_all`, preventing future mapping edits from changing old migrations.
- `backend/main.py`: research router inclusion and PUT CORS support only.
- `backend/requirements.txt`: pinned SQLAlchemy 2.0.52, Alembic 1.19.2 and
  psycopg binary 3.3.4. Existing pinned versions were retained.
- `backend/tests/test_research_{metrics,contracts,repository,api,migrations}.py`:
  analytical, temporal, transactional, precision and migration verification.
- `.github/workflows/ci.yml`, `compose.research.yml`: PostgreSQL 17 test service
  and an opt-in local development database; `pyproject.toml`: migration typing
  and explicit PostgreSQL integration marker, existing coverage floor retained.
- README, AGENTS, architecture, methodology, build plan, Phase 3 execution plan,
  `RESEARCH.md`, `RESEARCH_METRICS.md`, and this audit: usage, authority, formulas,
  provenance, limitations and verified execution evidence.

## Verification evidence

Final environment: Windows 11, Python **3.14.0**, NumPy **2.3.5**, PostgreSQL
**17.11**, Node **24.12.0**, Vite **7.2.7**. All inputs were synthetic/offline.
Docker Desktop's engine was unavailable. Official PostgreSQL/EDB portable binaries
were used for a disposable loopback-only local server; no Windows service or
existing database was modified. Tests used unique schemas and removed them.

| Check | Actual result |
|---|---|
| Full pytest with `TEST_DATABASE_URL` | **238 passed**, no skips, final run 12.68 s |
| Backend statement + branch coverage | **97.22%**, against existing 95% minimum; 811 statements and 160 branches |
| Research metric cases | 52 analytical/catalogue tests |
| Research input contracts | 19 cases |
| Research repository | 8 cases each on SQLite and PostgreSQL |
| Research API | 35 cases, including commit-failure rollback and sanitized errors |
| Migration suite | 4 cases, including real PostgreSQL up/down, model-schema agreement, exact Decimal round trip and immutable fact trigger |
| Ruff / formatting / mypy | Pass; 49 formatted Python files, 47 mypy source files including migrations |
| Pre-commit | All configured static hooks pass using the project Python environment |
| Dependency consistency | `pip check` passes |
| Frontend | **14 tests pass**, lint passes, build passes |

Without `TEST_DATABASE_URL`, PostgreSQL-specific migration verification is
explicitly skipped and repository cases run on SQLite only. SQLite is a test
double, not the production storage or proof of NUMERIC precision. API tests use
SQLite's explicit transaction mode to ensure savepoints participate in the outer
transaction; rollback checks do not rely on SQLite's legacy autocommit behavior.

The final frontend build retains the inherited stale Browserslist and >500 kB
chunk advisories. No frontend feature was added, and the emitted bundle size is
unchanged. Hosted CI is configured for Python 3.12/3.14, Node 22 and PostgreSQL
17.6; no hosted run or production deployment was triggered. Local PostgreSQL
17.11 verification is not represented as an executed hosted 17.6 test.

An independent read-only reviewer inspected all new research code, migrations,
tests and related configuration and ran **117 targeted tests**, with the then-
unconfigured PostgreSQL test skipped. It found no must-fix correctness/security
defects. Its documentation note about an unimplemented provider protocol was
resolved by explicitly describing supplied-data imports and deferring adapters.
The main execution subsequently ran the complete suite against live PostgreSQL.

Coverage is not exhaustive proof. Remaining uncovered research statements include
some direct-internal malformed timestamp/null handling, zero-value fingerprint
normalization, conflicting security rename and a few input rejection branches.
No source exclusions or reduced coverage floor were introduced. Migrations are
tested separately and not included in the `src`/`main` coverage denominator.

## Assumptions and unresolved limitations

The exact contract is documented in [RESEARCH.md](RESEARCH.md) and the formulas
in [RESEARCH_METRICS.md](RESEARCH_METRICS.md). Key limits are:

- Published-history reconstruction and historical system knowledge are distinct.
  `as_of` limits publication; `known_at` limits first recording. By default the
  latter is now. A fiscal year-end alone never establishes availability.
- Publication times, source locators, scale, currency and accounting basis are
  supplied by the importer. No live fundamental adapter, filing parser, archived
  raw-document store or external source certification was added.
- Security metadata is current-only. Ticker/sector history, ISIN checksum/registry
  validation, cross-listing identity reconciliation and historical classifications
  are not implemented. UUID stability does not itself solve those identity tasks.
- Facts use 30-digit NUMERIC with 10 fractional places. Arithmetic primitives
  have their separately documented Decimal-context precision. Unit/basis matching
  for derived ratios and growth remains the caller's responsibility.
- All 28 metrics can be stored with explicit context; only generic ratio and
  growth are computed by the new module. Sector-specific formula selection,
  peer comparisons and automatic valuation calculations remain future work.
- Immutable rows and provenance fingerprints are not tamper evidence against a
  database administrator. Retractions, source-ID remapping and correction of
  series identity are not supported by the current import workflow.
- Simultaneous duplicate writes may return a uniqueness conflict and require a
  retry. Sequential equivalent imports reuse the stored observation. No claim
  of distributed ingestion/exactly-once delivery is made.
- The API uses one owner key; it is not multi-user authorization. No managed
  database, production secrets, backups or production load testing were set up.

The original simulation assumptions and limitations remain unchanged. There is
no historical-return-to-expected-return conversion and no Phase 4 functionality.

## Acceptance

Phase 3's equity data model, stable IDs, source-aware fundamental observations,
availability logic, metric vocabulary and calculation infrastructure are
implemented with PostgreSQL migrations and tested API access. Full local checks
pass. Work is left uncommitted for owner review; Phase 4 has not started.
