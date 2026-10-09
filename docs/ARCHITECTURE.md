# Architecture through Phase 9A

The canonical product brief is [MASTER_BRIEF.md](MASTER_BRIEF.md). This checkout
contains the simulator correctness rebuild, methodology/tests, an equity research
registry, versioned thesis and valuation workspaces, hypothetical construction,
supplied stress scenarios and a private transaction ledger with supplied-mark
valuation, realized performance from the ledger and explicit valuation evidence,
and reconciled ledger position contribution.
Phase-specific sections below retain their phase boundaries; the current owner
review gate is after bounded Phase 9A acceptance. See the respective phase audits
for implementation and verification evidence. Benchmark/active-risk analysis,
factor regression, Brinson and publishing require separate stages.

## Phase 9A contribution boundary — authorized 2026-10-09

`backend/src/attribution/contracts.py` defines exact nullable Decimal effects,
segment exposures, rankings and reconciliation. `engine.endpoint_effects` derives
base P&L from actual marked holdings, executed trade principal and booked income,
fees/currency conversions. `build_contribution` uses the embedded performance
report's visible ledger records and exact flow unit deltas. Daily/flow segments
preserve ledger sequence and retain closed positions; current metadata is not
treated as historical sector evidence.

`routes.contribution` calls the accepted performance route inside the same existing
repository transaction, retaining its row lock through contribution calculation.
The returned Phase 8 report and contribution therefore share one snapshot/version,
knowledge cutoff and input manifest. There is no persistence migration or provider
adapter. Local P&L uses explicit segment-end FX; opening FX and conversion principal
remain separate. Forward unit-wealth increments reconcile to TWR with visible
residual/tolerance rather than an inferred balancing effect.

`attribution/replay.py` verifies the embedded performance replay then compares all
contribution fields. `scripts/replay_contribution.py` exposes this offline check.
Adding backend source changes the conservative Phase 8 source identity; historical
downloads require their compatible source/environment and are never rewritten.

The Performance controller accepts an optional third contribution transport.
When opted in, one request supplies both results; generation guards and all state
clearing actions cover both. `ContributionResults.jsx` formats percentage points,
exact residuals, equity rankings and expandable opening exposures. Undefined
window contributions retain the independent performance results without invented
zeros. No financial arithmetic is performed in the browser.
See [ATTRIBUTION.md](ATTRIBUTION.md) and [PHASE_9A_AUDIT.md](PHASE_9A_AUDIT.md).

## Phase 8 performance boundary — authorized 2026-09-15

`backend/src/performance/contracts.py` defines strict daily/flow valuation inputs
and typed outputs. `engine.py` reuses accounting replay and valuation to derive
unit issuance/redemption, daily returns and calendar links. `metrics.py` implements
dated XIRR and descriptive realized statistics, separate from scenario statistics.
`routes.py` obtains the existing locked portfolio snapshot, verifies its version
and completed-day cutoffs, and exposes a private read-only report endpoint.
No new tables, migrations, provider calls, ledger mutations or archive are needed.

The 2026-10-09 closeout adds `performance/identity.py` for actual source and input
fingerprints and `performance/replay.py` for offline verification of downloaded
reports. The additive nullable source-identity field preserves legacy parsing;
legacy reports without identity cannot pass exact replay. The command under
`scripts/replay_performance.py` compares all financial outputs using supplied
snapshots, independently of database availability and optional git/build settings.

The Performance frontend controller shares the memory-only workspace session,
loads recorded account state, prepares empty evidence templates using active
transaction IDs and paginated immutable history, and submits explicit evidence.
Client generation guards reject late reads/reports after edits, navigation or lock.
All economic arithmetic stays in the backend; the browser formats returned values.

The return calendar is explicitly UTC calendar daily / 365 observations per year,
not the simulation engine's default 252 trading periods. Unadjusted prices avoid
double-counting booked dividends. Missing marks, stale evidence, zero-denominator
ratios and non-conventional XIRR schedules return honest undefined states.
See [PERFORMANCE.md](PERFORMANCE.md) for contracts/formulas and
[PHASE_8_AUDIT.md](PHASE_8_AUDIT.md) for actual acceptance evidence. Phase sections
below are historical descriptions, not renewed stop-before-8 instructions.

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
| `frontend/src/App.jsx`, `components/SimulationConfig.jsx`, `components/ScenarioResults.jsx`, `scenarioContract.js` | Risk Lab controls, captured result presentation, request validation and display formatting |
| `frontend/src/features/workspace/session.js`, `sessionContext.js`, `PrivateWorkspace.jsx` | Memory-only shared private key, global unlock/lock control and controller registration |
| `frontend/src/features/workspace/Overview.jsx`, `overview.js` | Recorded account, quantity and cash read model; no inferred NAV or portfolio weights |

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

## Phase 4 thesis boundary

`research/thesis/schemas.py` validates owner-authored content; `repository.py`
appends immutable versions and reviews inside the existing request transaction;
`routes.py` handles private transport. The new Alembic migration adds three tables
without changing the earlier research migration. A stable thesis row is locked
while allocating sequential revisions; `expected_revision` rejects stale edits.
Composite foreign keys bind a revision to its security and a review to its thesis.
PostgreSQL triggers reject updates and deletes. Server UTC timestamps and captured
listing labels preserve what the application recorded at each version.

The React feature in `frontend/src/features/thesis/` separates an in-memory
workspace controller/API adapter from form and history presentation. Credentials
remain in memory; disconnected or superseded requests cannot repopulate private
state. Saved history and editable content have separate state. Both thesis and
review drafts require deliberate save/discard handling. The existing Risk Lab
remains a separate tab and continues using its existing scenario API.

This domain records decisions; it does not feed rates into simulations, generate
expected returns, place trades or maintain portfolio holdings. Full field/time
semantics and operational limitations are in [THESIS.md](THESIS.md).

## Phase 5 authorized design boundary — 2026-09-09

The following describes the implemented Phase 5 boundary; verification is recorded
in `PHASE_5_AUDIT.md`. The
permanent requirements are the seven suggestions and rules A–D in the dated
[master-brief addendum](MASTER_BRIEF.md#approved-addendum--2026-09-09-phase-5-and-permanent-design-guidance).

| Code | Responsibility |
|---|---|
| `backend/src/valuation/contracts.py` | Typed return context, uncertainty/undefined values, assumption sets, valuation results and scenarios |
| `backend/src/valuation/arithmetic.py` | Stable tested horizon conversions and finite-result validation |
| `backend/src/valuation/models.py` | Tested fundamental, scenario-set and reverse-valuation domain calculations |
| `backend/src/views/expected_return.py` | Explicit investor views, historical diagnostics and CAPM with declared estimation conventions |
| `backend/src/valuation/service.py` | Existing research/thesis evidence validation, typed response and complete resolved-input manifests |
| `backend/src/valuation/routes.py` | Thin private HTTP orchestration using existing owner-key access conventions |
| `frontend/src/features/valuation/` | Focused security/thesis/assumption workspace and rendering of server results |

The domain flow is research assumptions → valuation/return model → security
scenario → investor expected-return view → future portfolio construction. Each
step must retain a distinct meaning and type. An EPS-growth assumption is not a
return estimate. A model result is not automatically an investor view. Legacy
owner-entered thesis-review returns lack the independent Phase 5 horizon contract
and must not be silently imported as Phase 5 views. No model generates an
investment decision; human decisions remain in the thesis/review system.

Use a stateless calculation API. Requests supply the chosen model, resolved
numeric assumptions, horizon, valuation date, return/currency conventions and
evidence references. Services may read existing research and thesis records;
Phase 5 adds no database persistence, automatic market/macro provider requests,
provider-document archive, or coupling that changes the Risk Lab's existing
drift and portfolio calculations. Model implementations share explicit contracts
while retaining model-specific assumptions instead of a universal valuation form.

Any linked research observation must satisfy the requested publication `as_of`
and system-knowledge `known_at` cutoffs. A linked thesis revision must belong to
the security and be available under the requested cutoff. Preserve source values
and identifiers in the returned evidence snapshot. Distinguish documentary
evidence from supplied assumptions; linking a record does not establish that
every input was computed from it. Record valuation price, date, currency,
assumption set and exact revision used for later reconstruction.

Run manifests should contain proportionate resolved inputs, model/version,
code/build identity and git SHA when available, library versions, observation
window, valuation date, provider/retrieval metadata when applicable, adjustment
policy, data hashes and calculation settings. Record seed only where relevant.
Missing build identity must remain explicit; do not label uncommitted local work
as a verified clean commit. A hash identifies data and cannot preserve it.
No automatic permanent retention of licensed provider datasets is authorized.

Return values must identify the horizon and distinguish arithmetic expected
simple return, geometric compound growth, realized CAGR and log drift; distinguish
price/total, nominal/real, local/base currency and annualized/cumulative bases.
Annual-effective is the preferred risk-free convention; any other convention
must be named. Return frequency, periods per year and valuation calendar must be
explicit. Historical diagnostics remain visibly diagnostic and cannot silently
become forward return inputs. Sharpe continues to use arithmetic excess period
returns with matching annualization. Zero log drift is neither a claim of zero
expected simple return nor risk neutrality.

Bear/base/bull scenario sets are valid without probabilities. If supplied,
probabilities must be explicit assumptions, identify their user/model source,
and be coherently normalized before mathematical weighting. A weighted scenario
result is not a statistically calibrated forecast unless calibration exists.
Historical parameter-estimation uncertainty, Monte Carlo sampling uncertainty
and model-specification uncertainty are separate concepts; increasing path count
does not eliminate parameter or model uncertainty. Undefined financial values
use typed null/reason semantics, with effective counts where relevant, throughout
the API and UI. Null must never become zero in presentation.

The UI must retain each completed result's exact submitted assumptions and
evidence context, protect against superseded private responses, and show horizon,
currency, return basis and model meaning alongside every result. Financial
calculations remain in tested backend functions. Do not show automatic
BUY/HOLD/SELL or present a precise-looking percentage without its assumptions.

## Permanent boundaries for subsequent phases

Serious multi-market/currency analysis requires explicit FX series, valuation
cutoff, base/local currency and corporate-action adjustment conventions; matching
end dates alone does not establish aligned economic intervals. Split-like moves,
zero-volume days and repeated prices require investigation, not automatic
deletion. Phase 5 does not implement the ledger/corporate-action system.

Keep current/ex-ante covariance risk, scenario-distribution risk and realized
portfolio risk distinct in schemas and labels. Risk contribution must identify
its covariance estimator, period and weight basis; negative contributions are
valid and must not be clamped. Tail results must identify quantile/interpolation,
finite-sample CVaR and fractional-tail-atom conventions with effective tail counts.
A percentile is not an extremum and must not be labeled best/worst case.

Future acceptance gates require analytical reconciliation identities, numerical
failure cases, API compatibility expectations, reproducible checks, unsupported
functionality, deployment boundaries and data/provider assumptions. Relevant
provider contract tests and representative memory/load tests are prerequisites
for provider-dependent production claims. Audit records must distinguish planned,
locally verified, hosted-CI verified and deployed behavior.
# Phase 6 construction and supplied stress boundary

The owner authorized Phase 6 on 2026-09-10. `portfolio/construction/contracts.py` owns aligned history, one-year
adopted investor views, extensible strict constraints and typed results;
`algorithms.py` owns checked numerical allocation solvers; `analytics.py` owns
covariance, signed contributions and comparison reports. `service.py` resolves
eligible private evidence and replay manifests. Thin `/api/research/construction`
routes authenticate with the existing owner key and return no-store responses.

`risk/scenarios/historical_contracts.py`, `historical.py`, `historical_service.py`
and `historical_routes.py` provide a separate stateless supplied-data boundary at
`POST /api/research/stress/evaluate`. Replay, seeded joint block bootstrap and
explicit security shocks share identity/currency checks and manifests. Existing
parametric Gaussian/GMM/EWMA endpoints remain compatible and separate. Both new
POST endpoints return `{result, manifest}` and add no tables, migrations, archives
or provider calls. Existing migrations are required for the private research base.

The frontend enters through a text-branded platform shell with Construction,
Thesis, Valuation and distinct risk tools. Construction and stress workspaces keep
supplied inputs and results in memory; edits/superseding requests invalidate
results, and disconnect/unmount clears module state. The global key survives
navigation but clears on lock or refresh. Form/controllers handle
transport and display only, preserving backend null/reason meanings. Matrices,
solver diagnostics and replay records use progressive disclosure. Soft surfaces,
rounded corners and responsive navigation implement the permanent UI direction.

Phase 6 added no ledger, NAV, holdings reconciliation, realized performance,
attribution, transaction creation or publication. Single-currency registry snapshots
do not certify historical corporate-action or identifier mappings; the owner must
supply truthful adjustment/calendar provenance. See Phase 6 methodology and audit
for numerical/resource domains and what has actually been verified.


# Phase 7 accounting boundary — 2026-09-12

The owner authorized Phase 7; the current review gate is before Phase 8. Earlier
phase sections above retain their original scope. `accounting/contracts.py`
owns exact economic inputs and typed outputs; `ledger.py` replays immutable
transactions, `precision.py` fixes arithmetic context, and `valuation.py` applies
explicit dated prices/FX. `repository.py` locks the portfolio for coherent reads
and atomic version-checked writes; `imports.py` validates canonical CSV before
passing the same batch contract to preview/save. No provider/broker call occurs.

Revision `20260912_03` adds separate accounting portfolios/transactions, exact
PostgreSQL NUMERIC input fields, unique source/reference and sequence constraints,
and append-only UPDATE/DELETE triggers. Existing research/thesis migrations are
preserved. SQLite exact-text storage is a test convenience, not production.
Private `/api/accounting` uses existing owner authentication and commit-before-
success sessions. There are no transaction mutation or order endpoints.

`frontend/features/ledger` owns memory-only drafts, captured preview/save
payloads, account/session/draft generations, exact-decimal transport, paginated
history and server-result presentation. Holdings are separate from construction
weights; saving a ledger event invalidates supplied-mark results. More advanced
controls still use registered UUIDs and supplied JSON; native broker mapping and
fund support remain deferred. See [ACCOUNTING.md](ACCOUNTING.md) for the complete
contract and [PHASE_7_AUDIT.md](PHASE_7_AUDIT.md) for verification and limitations.

One frontend session controller validates the owner key against the existing
private research API, passes it to the active private module, and keeps it only in
memory. Navigation unmounts each module and clears its unsaved private drafts and
results without requiring another unlock. Locking disconnects registered modules,
invalidates pending responses and clears the key; a page refresh also clears the
memory-only session. Successful server writes remain saved. The backend boundary
is unchanged: `RESEARCH_API_KEY` configures access and private requests use
`X-Research-Key`. There is no broker login or new permission tier.

Overview reads actual accounting portfolios, recorded open equity quantities and
trade-date cash. It shows empty/unavailable states instead of fabricating NAV,
weights or performance. Construction accepts hypothetical supplied weights only;
importing ledger weights awaits a reviewed dated valuation contract covering
security marks, cash, FX and as-of cutoffs. The existing security registry remains
equity-only. [ASSET_TYPE_ROADMAP.md](ASSET_TYPE_ROADMAP.md) describes proposed typed
extensions without changing the present tables or APIs.
