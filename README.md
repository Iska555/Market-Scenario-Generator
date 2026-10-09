# Investment Management Workspace

A personal investment portfolio-management research project. The long-term goal
is an inspectable investment process: research → thesis → construction → risk →
accounting → performance → attribution → review.

**Phase 9A: private reconciled position contribution.**
The Performance workspace measures daily time-weighted returns, dated XIRR and
realized statistics using recorded transactions and supplied unadjusted price/FX
evidence. Missing coverage stays undefined. See the
[performance guide](docs/PERFORMANCE.md) and [Phase 8 audit](docs/PHASE_8_AUDIT.md).
Select **Include position contributions** to explain TWR using actual holdings,
trades, net dividends, fees, cash and FX. Closed equities remain included;
linked effects show an explicit reconciliation residual. See the
[contribution methodology](docs/ATTRIBUTION.md) and [Phase 9A audit](docs/PHASE_9A_AUDIT.md).

The transaction ledger supports holdings and supplied-mark valuation.
Preview and record immutable transactions, correct mistakes with reversals,
replay trade-date cash and moving-average local cost, and value positions using
explicit dated prices and FX. Manual entry and reviewed canonical CSV support
the planned Lightyear ISA; a native Lightyear parser remains unverified.
See the [accounting guide](docs/ACCOUNTING.md) and [Phase 7 audit](docs/PHASE_7_AUDIT.md).
The owner approved Phase 8 acceptance/reproducibility closeout on 2026-10-09
and the subsequent sequence recorded in [approved suggestions](docs/BRIEF_SUGGESTIONS.md).
Phase 8 closeout acceptance is recorded in its preserved audit; the owner's
subsequent Phase 9A authorization and acceptance have a separate record.
The simulation module is
the Risk & Scenario Lab. All simulation outputs are conditional scenarios under
explicit assumptions. Historical sample means are available only through an
explicit historical diagnostic selection; they are not silently used as forecasts.

## Project authority

- [Permanent master brief](docs/MASTER_BRIEF.md) — canonical phase order and rules
- [Phase 1 audit](docs/PHASE_1_AUDIT.md) — original defects, verification, remaining limits
- [Phase 2 audit](docs/PHASE_2_AUDIT.md) — analytical coverage, tooling and verification evidence
- [Phase 3 research guide](docs/RESEARCH.md) — PostgreSQL setup, private API and as-of queries
- [Phase 3 audit](docs/PHASE_3_AUDIT.md) — research implementation and verification evidence
- [Thesis guide](docs/THESIS.md) — version history, manual reviews and private workspace
- [Phase 4 audit](docs/PHASE_4_AUDIT.md) — thesis implementation and verification evidence
- [Phase 5 audit](docs/PHASE_5_AUDIT.md) — authorized valuation scope, current findings and verification status
- [Phase 6 audit](docs/PHASE_6_AUDIT.md) — construction, supplied stress and frontend verification
- [Accounting guide](docs/ACCOUNTING.md) — ledger conventions, canonical CSV, corrections and valuation
- [Phase 7 audit](docs/PHASE_7_AUDIT.md) — implementation, verification and broker limitations
- [Performance guide](docs/PERFORMANCE.md) — TWR/XIRR, valuation evidence, realized statistics and numerical limits
- [Phase 8 audit](docs/PHASE_8_AUDIT.md) — preserved performance closeout evidence
- [Contribution guide](docs/ATTRIBUTION.md) — endpoint accounting, wealth linking, FX allocation and replay
- [Phase 9A audit](docs/PHASE_9A_AUDIT.md) — current contribution acceptance and remaining boundaries
- [Methodology](docs/METHODOLOGY.md) — formulas, units, assumptions and failure conditions
- [Architecture](docs/ARCHITECTURE.md) — domain boundaries and API v3 contract
- [Asset-type roadmap](docs/ASSET_TYPE_ROADMAP.md) — typed future support beyond equities
- [Build plan](docs/BUILD_PLAN.md)
- [Proposed brief additions](docs/BRIEF_SUGGESTIONS.md) — for owner review

The September 2026 master brief supersedes earlier plans in
`docs/superpowers/`. Its dated 2026-09-09 addendum permanently adopts the seven
approved suggestions and rules A–D. The 2026-09-10 addendum authorizes Phase 6 and
permanently records the owner's soft, modern portfolio-platform design direction.
The 2026-09-12 continuation authorizes Phase 7. The owner's 2026-09-15 instruction
authorizes Phase 8, recorded prospectively in its plan and audit. On 2026-10-09
the owner explicitly authorized Phase 9A reconciled position contribution.
Benchmark/active-risk analysis, factor regression, Brinson and public publishing
remain subsequent stages. Completion of those later stages also
requires suitable data, deployment and operational checks.

Phase 3 adds a PostgreSQL equity security master with stable UUIDs, append-only
fundamental observations, publication/system-knowledge cutoffs, idempotent atomic
imports and a 28-metric catalogue. Research routes are opt-in and require an owner
API key; existing simulation endpoints work without a database. This phase exposes
the research backend through the API/OpenAPI; there is no research dashboard or
automatic fundamental-data download. See the research guide for setup and examples.

Phase 4 adds a private Thesis workspace, immutable timestamped revisions and
manual decision reviews tied to an exact revision. Required returns and valuation
ranges are owner-entered assumptions; they are not calculated forecasts. Run the
database migrations, then use the global Private workspace control to unlock
Thesis, Valuation, Construction, Stress, Ledger and Overview with one key.
See the thesis guide for the complete contract and limitations. Phases 1–3 were
committed as `88f4390`; the owner authorized Phase 5 on 2026-09-09.

The private key remains in browser memory only. Changing workspaces clears that
module's unsaved inputs and results while the global unlock remains active.
Locking the workspace or refreshing the page clears the key and private state;
saved server records remain. The backend still uses `RESEARCH_API_KEY` and
`X-Research-Key` for private routes. This is not a broker connection.

Overview reads recorded account identities, current equity quantities and cash
balances from the ledger. It does not invent holdings, NAV, returns or portfolio
weights when no reviewed valuation exists. Construction remains a hypothetical
allocation workspace with supplied weights; deriving those weights from ledger
holdings awaits a dated price, cash and FX valuation contract.

## Implemented Risk Lab

- Gaussian, genuine joint full-covariance GMM and single-asset flat-forecast EWMA
- Request-local RNG and reproducible seeded requests against unchanged data
- Explicit zero-log-drift or historical-diagnostic calibration
- Correct simple-return portfolio arithmetic: buy-and-hold is the new frontend
  request default; daily per-period rebalancing remains selectable
- Server-computed full-population percentiles, histograms and scenario statistics
- Annualized excess-return Sharpe, Sortino, path growth, drawdown and Calmar
- Signed volatility contributions that reconcile to historical ex-ante risk
- VaR/CVaR with confidence, modeled horizon, loss sign and currency notional
- Ledoit–Wolf/sample covariance, component diagnostics and data-quality provenance

Statistical outputs are estimates conditional on a model. Zero log drift is not
zero expected simple return. VaR is not a loss bound. Scenario volatility and
historical initial-weight risk decomposition are distinct and labeled separately.
The app does not provide investment recommendations or manage external capital.

## Local setup

Python 3.12 or 3.14 and Node 22 are the CI targets. Python's direct dependencies
are pinned; the frontend uses its committed npm lockfile.

```powershell
.\scripts\bootstrap.ps1 -PythonExecutable python
backend/.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --reload-exclude .venv
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The frontend defaults to `http://localhost:8000`; configure `VITE_API_URL` in
`frontend/.env.local` if needed. Backend allowed origins are configured with
`ALLOWED_ORIGINS` (default `http://localhost:5173`).
Interactive API documentation is served at `/docs`.

Recreate environments on each machine; copied environments contain absolute
interpreter paths. The closeout uses `backend/.venv` and leaves the inherited
`backend/env` untouched. On Windows/Python 3.12, bootstrap applies the complete
resolved version constraints in `backend/constraints-py312-windows.txt`.
That profile was verified with Python 3.12.14; it is not a cross-platform or
hash-locked installation specification. Python 3.14 uses the original direct pins.
For other platforms, create a local venv and install both requirements files.

## Verification

From the repository root:

```powershell
$env:LOKY_MAX_CPU_COUNT='2'
backend/.venv/Scripts/python.exe -m pytest
backend/.venv/Scripts/python.exe -m ruff check .
backend/.venv/Scripts/python.exe -m ruff format --check backend scripts
backend/.venv/Scripts/python.exe -m mypy
backend/.venv/Scripts/python.exe -m pip check
backend/.venv/Scripts/python.exe scripts/benchmark_phase1.py
```

Then run `npm test`, `npm run lint`, and `npm run build` in `frontend`.
On Windows, `scripts/verify.ps1` runs these checks plus the configured pre-commit
hooks and records results under ignored `.verification/phase8/`. It requires
`TEST_DATABASE_URL` for an isolated PostgreSQL test database. Tests create and
remove unique schemas; never point acceptance at a production database.
`-AllowDatabaseSkips` is available for diagnostic runs and does not establish
PostgreSQL acceptance.

Verify a downloaded private performance report without a database/provider:

```powershell
backend/.venv/Scripts/python.exe scripts/replay_performance.py path/to/performance.json
```

Replay requires matching backend source and Python/numerical library versions,
valid input/ledger fingerprints, and identical financial outputs. Older reports
without source identity must be regenerated; verification does not overwrite them.
See [PERFORMANCE.md](docs/PERFORMANCE.md) and the current acceptance audit.
The build script uses Vite's native config loader. If the default development
loader cannot read parent directories in a restricted Windows checkout, use
`npm run dev -- --configLoader native`.
Backend tests use synthetic data and block external provider access.
The benchmark is offline and reports its workload, environment and timing;
it does not impose a machine-independent latency promise.

CI is configured in `.github/workflows/ci.yml`. Its hosted execution is separate
from the local results recorded in the audit.

Pytest measures backend statement and branch coverage, including the API, with a
95% aggregate minimum and writes `coverage.xml`. A focused test run can use
`python -m pytest --no-cov backend/tests/test_methodology.py`; full verification
must use the default coverage configuration. The methodology includes an index
of each quantitative function and its analytical/regression tests.

Pre-commit runs Ruff lint, formatting checks and mypy using the active Python
environment; it reports changes needed without editing files. On Windows:

```powershell
. backend/.venv/Scripts/Activate.ps1
python -m pre_commit install
python -m pre_commit run --all-files
```

On Linux/macOS activate `backend/.venv/bin/activate` instead. Install is a one-time
local Git hook setup; CI invokes the hooks directly. Pytest and frontend
tests/lint/build remain mandatory full verification steps outside the commit
hooks. Direct Python dependencies are pinned in the two requirements files;
the closeout constraints additionally pin the Windows/Python 3.12 resolved
environment. Other runtime/platform profiles retain direct pins only.
CI saves `pip freeze` with its
coverage artifact for environment identification. These records are not a
promise of identical random draws across Python, BLAS or operating systems.

## Compatibility and deployment

API v3 is a deliberate breaking response update on the existing simulation
URLs. Requests require `drift_model`; v2 clients must migrate. Financial
statistics never fall back to chart samples. See the generated OpenAPI schema.

This checkout includes historical Fly.io configuration, although older
documentation referred to Render. Existing production deployment state was not
changed or verified. Deploy frontend and backend together only after reviewing
this phase. No site was published as part of the correctness rebuild.

Risk Lab scenario limits include no FX conversion, fees/taxes, persistent market-data
snapshots, exchange-calendar reconciliation, regime persistence or Monte Carlo
confidence intervals. The two-million-cell request cap and two-worker executor
bound core tensor workloads; they are not a capacity guarantee for the legacy
512 MB container.

`docs/golden/baseline_v2.json` preserves historical incorrect output.
It is not a reference for correct financial results. The optional
`scripts/capture_baseline.py` now writes a separate v3 diagnostic capture and
requires live provider access.
