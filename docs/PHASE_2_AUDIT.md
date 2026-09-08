# Phase 2 methodology and tests audit — 2026-09-08

## Scope and authority

The owner explicitly authorized Phase 2 on 2026-09-08. This continues the
canonical `MASTER_BRIEF.md` phase order after the Phase 1 rebuild. The existing
`phase-1-correctness` checkout contained uncommitted Phase 1 changes; these were
preserved and extended in place. No merge, commit, deployment or Phase 3 work
was performed. `AGENTS.md` records the updated authorization and review boundary.

The master brief remains byte-for-byte unchanged (SHA256):
`5615B5E7C4747A300C7FE54DF06CD41995A2A5F04CD82A42D69E76AE4E380AEA`.
The older user-edited August plan is also unchanged by this phase.

## Findings, original locations and disposition

| Classification | Original file/function or configuration | Finding and disposition |
|---|---|---|
| CONFIRMED BUG | `backend/src/risk/statistics.py::return_histogram` | Accepted an empty population and silently flattened a matrix into a histogram. Added the finite, nonempty vector validation already used by percentiles. The regression initially failed for both cases, then passed after the two-line fix. Valid request behavior is unchanged. |
| DESIGN DEBT — repaired | `pyproject.toml` pytest settings | Coverage was installed but not enforced. Default pytest now measures statements and branches across all `src` and `main`, writes terminal/XML reports and requires 95% aggregate coverage. No source exclusions were added. |
| DESIGN DEBT — repaired | `backend/tests/` model/statistics tests | Existing tests established many invariants but left sampler scale/covariance, several finite-tail cases and explicit failure paths weakly protected. Added independent analytical, distributional and numerical-boundary cases. |
| DESIGN DEBT — repaired | `.pre-commit-config.yaml` | Hooks were restricted to backend paths, omitted script/config triggers, and changed files automatically. Hooks now run whole-project Ruff lint, backend/script formatting checks and backend mypy under the active Python environment, with relevant config/requirements triggers. |
| DESIGN DEBT — repaired | `.github/workflows/ci.yml` | No coverage gate/artifact or resolved Python environment record; formatting was absent from CI. CI now uses the same static hooks, runs dependency consistency, and saves coverage plus `pip freeze` artifacts for each Python job. Hosted execution remains unverified in this session. |
| DESIGN DEBT — repaired | `docs/METHODOLOGY.md`, `docs/ARCHITECTURE.md` | Formula explanations existed, but lacked a complete function-to-test index and explicit window/aggregation matrix. Added both, finite quantile/ES/histogram formulas and verification/environment boundaries. |
| CORRECT AS IMPLEMENTED | `portfolio/paths.py`, `risk/covariance.py`, `risk/statistics.py`, model fitters/samplers and scenario service | New independent cases agree with existing arithmetic and calibration. No change to their formulas was needed. |

## New tests

The baseline had 65 passing tests. Phase 2 adds **47 cases**, for **112 total**:

- `backend/tests/test_methodology.py` (14 cases): Gaussian fitting and sampler
  moments, correlated shock orientation/scales, EWMA drift and forecast scales,
  GMM within/between covariance and declared mean shifts, sample versus MLE
  covariance, non-isotropic Ledoit–Wolf shrinkage, pathwise annualization,
  histogram validation/boundaries, fractional tails and ties.
- `backend/tests/test_numerical_failures.py` (30 cases): matrix validity,
  unknown estimator, singular correlation preservation, invalid percentiles/tail
  assumptions, invalid prices/tensors, unsupported rebalancing, numerical
  underflow, GMM parameter validity, one-component moments and nonconvergence.
- `backend/tests/test_scenario_analytics.py` (3 cases): full deterministic
  data-to-result daily and buy-and-hold portfolios, and a constant-price universe
  with explicit null risk ratios and correlations. The deterministic runs return
  no chart sample yet still produce all statistical results.

Example independent answers:

- At 60/40 weights and +10%/−10% per-asset returns each period, two-period
  daily wealth is 1.0404; buy-and-hold wealth is 1.05.
- For centered observations `(±2,0),(0,±1)`, Ledoit–Wolf shrinkage is 17/18
  and covariance is `diag(31/24,29/24)`, distinct from both sample and target.
- For losses `[0.4,0.2,0.2,−0.1]`, worst-half ES is 0.3. Including every tie at
  the VaR boundary would incorrectly enlarge the tail.

These tests use actual domain functions. Providers are synthetic; the GMM
nonconvergence test runs the fitter and then injects its failure flag to verify
our error handling. Random moment tests have fixed seeds and conservative
sampling-error tolerances. No historical incorrect-output snapshots were adopted.

## Verification executed locally

Environment: Windows 11, project Python **3.14.0**, NumPy **2.3.5**;
frontend Node **24.12.0**, Vite **7.2.7**. Python 3.12/3.14 and Node 22 remain
the configured hosted CI targets. Local execution does not establish hosted
Linux results or a fresh dependency installation on every supported platform.

| Check | Result |
|---|---|
| `backend/env/Scripts/python.exe -m pytest` | **112 passed**, final run 4.44 seconds |
| Statement + branch coverage | **98.12%**, required minimum 95%; 483 statements, 102 branches, 5 missed statements and 6 partial branches |
| `python -m ruff check .` | Pass |
| `python -m ruff format --check backend scripts` | Pass, 35 files |
| `python -m mypy` | Pass, 33 source files including tests |
| `python -m pip check` | Pass, no broken requirements |
| Pre-commit config validation and all static hooks | Pass with project Python environment selected |
| Frontend `npm test` | **14 passed** |
| Frontend `npm run lint` | Pass |
| Frontend `npm run build` | Pass; existing stale Browserslist and >500 kB chunk advisories remain |
| Offline engine benchmark | 1000 paths × 252 periods × 5 assets: Gaussian 0.1115 s, GMM 0.1945 s; histogram population 1000 in both |

The benchmark covers preparation, fitting, simulation, statistics and response
assembly; it excludes provider access, HTTP serialization and frontend rendering.
It is a single local timing, not a production latency or memory guarantee.

The Codex Windows execution environment reset the subprocess PATH during the
first pre-commit attempt, selecting system Python without Ruff/mypy. Verification
then prepended the project interpreter's directory to `os.environ['PATH']` inside
the Python process before invoking `pre_commit.main`; all hooks passed. The hook
cache used the temporary directory. Normal local usage requires activating the
venv as documented in README. No Git hook installation is claimed for this
checkout; CI invokes hooks directly.

An independent read-only reviewer checked the new tests, histogram fix and CI/
hook configuration and found no blocking issues. Its optional suggestion for a
non-isotropic shrinkage check was incorporated and verified. The reviewer did
not independently rerun checks or review the subsequently completed prose.

## Coverage limits and mathematical assumptions

Every current numerical function has analytical or regression evidence indexed
in `METHODOLOGY.md`. Coverage is an execution metric, not a correctness proof.
Unexecuted statements remain in empty-input/no-common-valuation errors in
`data/preparation.py`, absent/ambiguous provider data in `data_download.py`, and
the iteration-limit failure in `nearest_correlation`. The ordinary single-level
provider-column branch also lacks coverage. These are disclosed, not excluded
from the coverage denominator or represented as tested.

The assumptions remain those of Phase 1: explicit drift selection, conditional
simulations, iid Gaussian/GMM draws, flat EWMA forecast, fully invested long-only
weights, costless daily rebalancing or buy-and-hold, an explicit annual effective
risk-free rate and observation-period annualization. Zero log drift is not zero
expected simple return. Undefined ratios are null. Histogram validation changes
no financial formula or valid API v3 schema.

Direct Python dependency versions remain pinned, and frontend resolution uses
the existing npm lockfile. Python transitive dependencies are not locked; CI's
resolved-environment artifact improves identification but is not a hash-locked
installation specification. Exact random replay still requires the same data,
runtime, dependencies and numerical environment. Source price hashes alone do
not recreate data, which remains unpersisted.

The original provider/FX/calendar limitations, unverified production capacity,
lack of Monte Carlo uncertainty intervals and lack of live-market validation
remain. No hosted CI run, public publishing or deployment was requested or claimed.

## Phase 2 acceptance

The repository has backend tests, formula methodology and architecture; pinned
pytest/Ruff/mypy/pre-commit and application dependencies; and CI configured to
run the required suites. Analytical cases cover each numerical function and the
master brief's weighted return, known variance, risk contribution, zero-excess
Sharpe, known drawdown and concurrent reproducibility examples. Local checks
pass. Phase 2 is complete for owner review; **Phase 3 is not started**.
