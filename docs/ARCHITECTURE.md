# Architecture after Phases 1–3

The canonical product brief is [MASTER_BRIEF.md](MASTER_BRIEF.md). This checkout
implements the simulator's correctness rebuild, methodology/test infrastructure
and the Phase 3 equity research data model. Theses,
expected-return estimation services, ledgers, realized performance, attribution
and public publishing remain future phases.

## Boundaries

| Code | Responsibility |
|---|---|
| `backend/main.py` | HTTP routes, validated models, error translation, two-worker executor |
| `backend/src/api/models.py` | Versioned requests/responses, explicit assumptions and request limits |
| `backend/src/data/providers.py` | PriceDataProvider protocol, bounded cache, serialized provider access |
| `backend/src/data_download.py` | yfinance adjusted-close adapter |
| `backend/src/data/preparation.py`, `returns_preprocess.py` | Price validity, aligned return intervals, provenance/quality diagnostics |
| `backend/src/gmm_model.py`, `ewma_vol.py`, `generative_model.py` | Fitting and explicit-generator sampling |
| `backend/src/portfolio/paths.py` | Simple-return portfolio arithmetic and drifting buy-and-hold holdings |
| `backend/src/risk/covariance.py` | Covariance estimates, PSD factors, nearest-correlation projection, volatility contributions |
| `backend/src/risk/statistics.py`, `contracts.py` | Full-population statistics and typed quantitative results |
| `backend/src/risk/scenarios/service.py` | Data → calibrated model → paths → statistics → response orchestration |
| `backend/src/research/metrics.py` | Equity metric vocabulary and guarded Decimal ratio/growth arithmetic |
| `backend/src/research/schemas.py`, `tables.py` | Validated research contracts and typed persistent entities |
| `backend/src/research/repository.py` | Stable identities, transactional immutable imports and temporal revision selection |
| `backend/src/research/database.py`, `routes.py` | Lazy PostgreSQL sessions, private API access and HTTP orchestration |
| `backend/migrations/`, `backend/alembic.ini` | Explicit versioned PostgreSQL schema lifecycle |
| `frontend/src/App.jsx`, `components/ScenarioResults.jsx`, `scenarioContract.js` | Risk Lab controls, captured result presentation, request validation and display formatting |

`src/correlation.py` preserves imports for two existing Python helper names;
the removed v2 functions were incorrect and have no compatibility shim. There is
one active quantitative implementation of each calculation.

## API v3

`POST /api/simulate` and `POST /api/simulate-portfolio` retain their URLs. Both now
require `drift_model` and return `api_version: 3.0.0`. This is a breaking contract:
v2's ambiguous statistics and sample fields are removed. Update backend and
frontend together; external consumers must migrate using `/docs` or
`/openapi.json`. Unknown request fields are rejected instead of silently ignored.

Both responses carry the resolved request assumptions, typed statistics,
percentiles, percentile currency values, histogram, tail metadata, model
diagnostics, and actual estimation/valuation dates. Portfolio responses add a
separately labeled historical risk decomposition. Only fields explicitly named
`*_paths_chart_sample` contain chart samples, always including time zero. Changing
their size cannot alter statistics. Charts must never become a fallback data
source if statistical fields are missing.

Completed results retain their own instrument identity and returned assumptions
when the form changes. Loading and errors are independent for each tab, so a
portfolio request cannot re-enable a still-running single-asset request. Blank
numeric assumptions are rejected; zero must be explicit. The frontend performs
input validation and formatting, while financial statistics remain on the server.

`/api/version` reports API version plus `GIT_COMMIT_SHA` and `BUILD_TIMESTAMP` from
deployment environment variables, or null when unavailable. Local uncommitted
work is not represented as a clean commit. Data hashes fingerprint adjusted
input series; exact replay still requires saving those input series separately.

## Resource and failure behavior

All expensive work, including portfolio downloads, runs outside the ASGI event
loop. A process uses two simulation workers. Each request is limited to two
million `paths × horizon × assets` cells; independent dimension caps are also
validated. Tensors are vectorized. GMM loops only over components; EWMA's
historical recurrence is inherently sequential. HTTP response serialization and
browser rendering are outside the engine benchmark.

The cache holds at most 128 ticker/window entries for one hour using monotonic
time. A lock protects cache state and serializes downloads (the provider may
internally share state). Frames are copied on read to prevent request mutation.
Retrieval timestamps remain stable within the cached snapshot. No raw data is
persisted and cache entries expire; this is not a point-in-time research store.

Validation/calibration/numerical-range failures return 422; provider failures
return 503. Missing instruments are never silently removed or renormalized.
Nonfinite numerical results cause explicit failure; they are not clipped or
replaced by fabricated finite values. Undefined ratios use null.

The historical 512 MB deployment configuration has not been load-tested here.
The request budget bounds primary tensors, not total RSS, provider history,
concurrent response serialization, or a multi-process deployment. Do not infer a
production capacity guarantee from the offline benchmark. No deployment was
performed as part of this phase.

## Verification

Backend tests use deterministic synthetic providers and analytical cases.
External provider access is blocked, while Windows asyncio loopback sockets are
permitted. Frontend tests exercise presentation using deliberately misleading
chart samples. Ruff and mypy include the entire active backend and tests, with
no route/engine exclusions. CI installs pinned direct Python dependencies and
uses the committed frontend lockfile on Node 22; its Python matrix is 3.12/3.14.
Local evidence and limitations are recorded in [PHASE_1_AUDIT.md](PHASE_1_AUDIT.md)
and [PHASE_2_AUDIT.md](PHASE_2_AUDIT.md).

Phase 2 instruments all backend `src` modules and `main`, with branch coverage
and a 95% aggregate minimum. There are no financial-module exclusions. The
coverage XML is a CI artifact, together with the resolved Python environment.
Every quantitative function is mapped to tests in `METHODOLOGY.md`; coverage
does not replace known-answer tests or guarantee mathematical correctness.

Local pre-commit hooks and CI use the same Ruff lint/format and mypy commands.
Hooks are `language: system`: activate the installed project environment first.
Backend Python, scripts, requirements, hook configuration and `pyproject.toml`
changes trigger the relevant static checks. Full pytest and frontend checks run
as separate CI steps; commit hooks do not claim to run those suites. The pipeline
checks Python dependency consistency and retains pinned direct requirements and
the npm lockfile. Transitive Python versions remain resolver-dependent, recorded
by `pip freeze`; a cross-platform transitive lock has not been introduced.

Phase 2 adds no routes, changes no valid API v3 output, and creates no later-phase
domains. Its only domain behavior change rejects invalid histogram populations.
Data, portfolio and risk remain separate; FastAPI contains no financial formulas.

## Phase 3 research boundary

Research is a separate backend domain. It does not read or modify scenario models,
portfolio weights or future accounting entities. `main.py` includes its router;
financial arithmetic remains in `research/metrics.py`. A catalogue of supported
observations and two calculation primitives precede automated statement parsing,
provider adapters or research dashboards.

SQLAlchemy 2 maps securities and fundamental observations to PostgreSQL. Alembic
defines the schema independently of runtime mappings and is tested for agreement.
No engine connection or schema creation occurs when importing or starting the app.
Research endpoints require a PostgreSQL+psycopg URL and owner key; all research
reads and writes enforce the same key. The simulation endpoints are unaffected.
Session transactions commit before HTTP success; errors roll back and database
errors return sanitized 503 responses. This is a private single-owner interface,
not a multi-user permission system or a publishing API.

Security metadata is current-only; its UUID remains stable when ticker/exchange
labels change. Observations preserve source IDs and publication, fetch and
application recording times. Queries filter eligibility before ranking revisions.
Separate source, metric, fiscal period, accounting basis and currency dimensions
prevent silent merging. Monetary precision is fixed at `NUMERIC(30,10)`, with
request validation rejecting excess precision. PostgreSQL triggers reject updates
and deletes of fact rows; there is no application route for either operation.

`docs/RESEARCH.md` describes exact as-of versus system-knowledge semantics,
deduplication/conflict handling, API setup and limitations. Content/publication
hashes are internal identity aids rather than external attestations. A current
vendor response is never converted into a historical fundamental observation
without supplied publication provenance. No external fundamental provider is
called or hidden behind the current imports.

Offline SQLite tests exercise domain/API contracts; an explicit PostgreSQL suite
checks migration round trips, exact Decimal storage and immutable fact triggers.
When `TEST_DATABASE_URL` is configured, repository cases also run against isolated
PostgreSQL schemas. CI provisions PostgreSQL 17. Mypy includes migrations; backend
coverage instruments `src` and `main`, with migrations verified separately.
