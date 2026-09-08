# Portfolio Simulations

A personal investment portfolio-management research project. The long-term goal
is an inspectable investment process: research → thesis → construction → risk →
accounting → performance → attribution → review.

**Current scope: Phase 3, fundamental research data model.** The simulation module is
the Risk & Scenario Lab. All simulation outputs are conditional scenarios under
explicit assumptions. Historical sample means are available only through an
explicit historical diagnostic selection; they are not silently used as forecasts.

## Project authority

- [Permanent master brief](docs/MASTER_BRIEF.md) — canonical phase order and rules
- [Phase 1 audit](docs/PHASE_1_AUDIT.md) — original defects, verification, remaining limits
- [Phase 2 audit](docs/PHASE_2_AUDIT.md) — analytical coverage, tooling and verification evidence
- [Phase 3 research guide](docs/RESEARCH.md) — PostgreSQL setup, private API and as-of queries
- [Phase 3 audit](docs/PHASE_3_AUDIT.md) — research implementation and verification evidence
- [Methodology](docs/METHODOLOGY.md) — formulas, units, assumptions and failure conditions
- [Architecture](docs/ARCHITECTURE.md) — domain boundaries and API v3 contract
- [Build plan](docs/BUILD_PLAN.md)
- [Proposed brief additions](docs/BRIEF_SUGGESTIONS.md) — for owner review

The September 2026 master brief supersedes earlier plans in
`docs/superpowers/`. Thesis databases, portfolio optimization, a live
transaction ledger, realized TWR/XIRR, attribution and public publishing are not
implemented and are not part of this phase.

Phase 3 adds a PostgreSQL equity security master with stable UUIDs, append-only
fundamental observations, publication/system-knowledge cutoffs, idempotent atomic
imports and a 28-metric catalogue. Research routes are opt-in and require an owner
API key; existing simulation endpoints work without a database. This phase exposes
the research backend through the API/OpenAPI; there is no research dashboard or
automatic fundamental-data download. See the research guide for setup and examples.

## Implemented Risk Lab

- Gaussian, genuine joint full-covariance GMM and single-asset flat-forecast EWMA
- Request-local RNG and reproducible seeded requests against unchanged data
- Explicit zero-log-drift or historical-diagnostic calibration
- Correct simple-return portfolio arithmetic: daily rebalance or buy-and-hold
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
python -m venv backend/env
backend/env/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
backend/env/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --reload-exclude env
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

The existing backend virtual environment in this checkout may use Python 3.14.
Use the virtual-environment interpreter for checks, not an unrelated system Python.

## Verification

From the repository root:

```powershell
$env:LOKY_MAX_CPU_COUNT='2'
backend/env/Scripts/python.exe -m pytest
backend/env/Scripts/python.exe -m ruff check .
backend/env/Scripts/python.exe -m ruff format --check backend scripts
backend/env/Scripts/python.exe -m mypy
backend/env/Scripts/python.exe -m pip check
backend/env/Scripts/python.exe scripts/benchmark_phase1.py
```

Then run `npm test`, `npm run lint`, and `npm run build` in `frontend`.
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
. backend/env/Scripts/Activate.ps1
python -m pre_commit install
python -m pre_commit run --all-files
```

On Linux/macOS activate `backend/env/bin/activate` instead. Install is a one-time
local Git hook setup; CI invokes the hooks directly. Pytest and frontend
tests/lint/build remain mandatory full verification steps outside the commit
hooks. Direct Python dependencies are pinned in the two requirements files;
transitive Python dependencies are not locked. CI saves `pip freeze` with its
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

Known limits include no FX conversion, fees/taxes, persistent market-data
snapshots, exchange-calendar reconciliation, regime persistence or Monte Carlo
confidence intervals. The two-million-cell request cap and two-worker executor
bound core tensor workloads; they are not a capacity guarantee for the legacy
512 MB container.

`docs/golden/baseline_v2.json` preserves historical incorrect output.
It is not a reference for correct financial results. The optional
`scripts/capture_baseline.py` now writes a separate v3 diagnostic capture and
requires live provider access.
