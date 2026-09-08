# Phase 3 fundamental research implementation plan

Authority: owner request to build Phase 3, following `docs/MASTER_BRIEF.md`.
The earlier Phase 1/2 working changes remain in this checkout. No commit, merge,
deployment, thesis, expected-return model or later-phase functionality is included.

## Design

Build a backend research domain with typed API access. Equities have immutable
UUID identity and editable descriptive/security-master fields. Ticker is a
current label, unique only within an exchange, never the observation foreign key.
Security creation and label edits do not claim historical classification coverage.

Fundamental observations are append-only, source-specific records with Decimal
values, metric, unit, currency, period start/end and kind (instant, quarter,
annual, TTM, estimate), reported_at, fetched_at and server recorded_at. Each
source record ID identifies one immutable published version. Repeated identical
imports reuse it; changed content with the same ID is a conflict. Restatements
require a new version ID and their actual later publication timestamp.

As-of queries filter publication time and an optional separate system-knowledge
cutoff before selecting the latest published revision within each
metric/period/basis/currency/source series. Sources are never silently combined.
Current observations cannot be backdated by assuming period_end is publication.

Use PostgreSQL, SQLAlchemy 2 typed mappings and Alembic. SQLite is permitted only
as an ephemeral offline test double; migrations and database behavior will also
be tested against local PostgreSQL when available, with PostgreSQL CI service.
No startup create_all or migrations against an unknown existing database.

Research API access is disabled unless a PostgreSQL URL and an owner API key are
configured. Require the key for all research reads/writes; existing simulator
endpoints remain unchanged. Supplied data ingestion uses the typed observation
contract; provider adapters are deferred, and no historical claims are inferred from live yfinance
fundamentals. OpenAPI is the initial interface; no research dashboard this phase.

## Tasks and ownership

- [x] 1. Metric catalogue and pure calculation infrastructure: define all brief
  metrics plus explicit units/categories and guarded Decimal ratio/growth helpers;
  independent hand-calculated tests. Delegate `research/metrics.py` and its tests.
- [x] 2. Research contracts, SQLAlchemy persistence, migration and repository:
  test stable identities, field validity, append-only/idempotent ingestion,
  rollback, restatement visibility, source separation and knowledge cutoffs first.
- [x] 3. Thin research routes and opt-in database/auth configuration: typed
  security create/read/update, bounded list/import/as-of observations, catalogue;
  synthetic API tests and disabled/unauthorized/database-error handling.
- [x] 4. Reproducible setup and documentation: PostgreSQL development compose,
  migration instructions, CI database suite, formula/availability methodology,
  Phase 3 audit; run all inherited checks and independent code review.
- [x] 5. Record results/limitations, preserve master brief, stop before Phase 4.

Decisions: Phase 3 exposes data/calculation infrastructure through the API, not
automatic investment judgments. Explicit source and accounting basis avoid
pretending heterogeneous ratios are interchangeable. Direct metric observations
are accepted without fabricating unavailable raw data or publication timestamps.

## Acceptance checks

No observation before reported_at or its first system knowledge time. A later
restatement never replaces earlier as-of values. Imports are transactional and
duplicates cannot silently revise facts. Security renaming preserves observation
foreign keys. Units and currency are validated against the metric catalogue.
Calculation denominators/bases are explicit; undefined values have reasons.
All tests are offline/synthetic; PostgreSQL execution is separately identified.
Pytest coverage floor95, Ruff, formatting, mypy, pre-commit, frontend tests/lint/
build and dependency check must pass, with migration evidence and honest limits.
