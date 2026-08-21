# Phase 0 + Phase 1: Correctness Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every number the simulator reports reproducible, correctly derived, and documented — fixing the eight confirmed defects in Phase 1 on top of the Phase 0 test and tooling foundation.

**Architecture:** The backend gains a set of small, single-responsibility, pure-numpy modules under `backend/src/` (data quality, linear algebra, joint models, portfolio construction, risk metrics, contributions, risk-free rate). Each is unit-tested against a closed-form or analytically known answer with no network access. `backend/main.py` becomes a thin composition root that creates one `np.random.Generator` per request and threads it through every sampling call. The frontend stops deriving any statistic client-side and consumes server-computed percentiles.

**Tech Stack:** Python 3.12 (Docker) / 3.14 (local venv), FastAPI, pydantic v2, numpy, pandas, scipy, scikit-learn, pytest, ruff, mypy, pre-commit. Frontend: React 19, Vite 7, Tailwind 4, Recharts 3, vitest.

**Spec:** `docs/superpowers/specs/2026-08-20-institutional-portfolio-platform.md` (Phase 0 and Phase 1 sections, plus the Phase 1 Definition of Done)

## Global Constraints

- **Scope is Phase 0 + Phase 1 only.** Phases 2–5 are out of scope for this plan. Do not add drift models, shrinkage estimators, bootstrap, GARCH, benchmark analytics, optimisers, stress tests, Postgres, or CI. The one exception the spec explicitly folds into Phase 1 is deleting the dead `"Adj Close"` branch in `data_download.py` (spec Phase 5), because Task 3 rewrites that function anyway.
- **No magnitude-based filtering or clipping of returns anywhere.** This is the defect in spec 1.3. A reviewer will grep for `abs() < 0.2`, `np.clip`, and mean-subtraction on simulated returns.
- **Every quantitative function gets a test with a closed-form or analytically known answer.** No exceptions (spec Phase 0.1).
- **No test may touch the network.** `yfinance` is monkeypatched or fixture-backed in every test.
- **Every sampling function takes an explicit `rng: np.random.Generator` parameter.** No `np.random.seed`, no `np.random.randn`, no `np.random.normal`, no `sklearn` `.sample()` calls anywhere in `backend/src/` or `backend/main.py` after Task 2.
- **Trading-day convention:** `TRADING_DAYS_PER_YEAR = 252`, defined once in `src/risk_metrics.py` and imported everywhere. Never hardcode 252 or 365 in another module.
- **Sign convention for tail risk:** losses are reported positive (`convention: "loss_positive"`).
- **Portfolio value convention:** `portfolio_paths[p, t]` is the value of an initially-1.0 portfolio *after* `t+1` days. The initial 1.0 is implicit and never stored as a column. Terminal return is `portfolio_paths[:, -1] - 1.0`.
- **Type annotations:** every function added or rewritten in `backend/src/` gets full annotations. mypy runs with `disallow_untyped_defs = true` over `backend/src` and `backend/main.py`.
- **The frontend's existing visual language is preserved.** No redesign, no restyle, no component split beyond the one new file this plan names. The `CLAUDE.md` design system in the *Azerbaijan-Economic-AI* project does **not** govern this repo.
- **Commit after every task.** Conventional-commit prefixes (`chore:`, `fix:`, `feat:`, `test:`, `docs:`).
- **Run `pytest` from the repo root**, not from `backend/`. `pythonpath = ["backend"]` in the root `pyproject.toml` makes `from src.x import y` and `import main` resolve.
- **One atomic commit per task, and the full suite must be green at that commit.** `git bisect` has to stay usable across this branch, so a task never lands with a known-red test.
- **No task may modify a file outside its stated `Files:` block.** If a task turns out to need a change elsewhere, stop and report it rather than widening scope. The `Files:` block is the contract.
- **No dead code is retained behind a lint exclusion.** Excluded dead code rots unnoticed and then gets copied. The four unused scripts are deleted in Task 1.

### Memory: the simulation streams, it does not materialise

The full `(num_paths, horizon, n_assets)` array is never allocated. At the maximum request configuration it is 400 MB, which is an artefact of the implementation rather than a requirement of the output.

Simulation runs in **path batches**. For each batch the engine generates `(batch, horizon, n_assets)` log returns, builds that batch's asset and portfolio paths, folds the batch into a set of accumulators, and discards it. Peak memory becomes `O(batch x horizon x n_assets)` and is independent of `num_paths`.

Accumulated per batch, because these are what the Phase 1 outputs actually require:

| Accumulator | Shape | Feeds |
|---|---|---|
| terminal portfolio returns | `(num_paths,)` | percentiles, full-horizon VaR/CVaR, mean/median/prob-loss |
| per-path max drawdown | `(num_paths,)` | median and 95th-percentile MDD, both Calmar variants |
| pooled 1-day and 10-day returns | `(num_paths x horizon)`, `(num_paths x horizon / 10)` | `d1` and `d10` VaR/CVaR |
| daily-return moments (`n`, `sum`, `sum_sq`, `sum_sq_shortfall`) | scalars | annualised volatility, Sortino |
| terminal asset value sums | `(n_assets,)` | per-asset mean return, return contributions |
| asset covariance | `(n_assets, n_assets)` | risk contributions — folded from the first batches only, up to `COVARIANCE_SUBSAMPLE_PATHS` |
| chart sample | `(30, horizon)` and `(30, horizon, n_assets)` | rendering only |

**Byte-identity across batch sizes is a hard requirement, and it constrains the RNG design.** A single parent `Generator` is drawn from sequentially; batches are never re-seeded and never spawn per batch.

- *Gaussian.* `rng.standard_normal((batch, horizon, n_assets))` fills in C order with paths as the leading axis, so twenty draws of 250 rows consume exactly the stream that one draw of 5000 rows would. Batch-invariant with no special handling.
- *Joint GMM.* Interleaving a component draw with per-component normal draws is **not** batch-invariant: regrouping changes consumption order. Two independent streams are therefore spawned **once**, before the batch loop (`component_rng, normal_rng = rng.spawn(2)`), and each is drawn at a fixed shape per batch. `rng.multivariate_normal` is replaced by an explicit per-component Cholesky transform, whose draw count does not depend on how many samples land in each component.

`batch_size` is an internal constant sized to a byte budget, not a fixed path count, so it adapts to horizon and asset count. Peak resident memory stays under 200 MB at the maximum configuration. Arrays stay `float64` throughout: `float32` is not used for accumulators under any circumstances, and is not needed for the path array at this batch size.

### Precision: never render more digits than the estimate supports

Phase 1 estimates drift as the sample mean of daily log returns. At 25% annual volatility over 3 years the standard error on annualised drift is roughly 14 percentage points. Rendering such a figure to two decimals is a false precision claim.

Any UI figure derived from estimated drift — expected or mean return, annualised return, and the scenario ladder — is rendered to **whole percents** in Phase 1. Measured quantities that do not inherit drift noise (volatility, VaR, CVaR, risk contributions, correlations, ratios) keep two decimals. Confidence intervals arrive with the Phase 2 plan; until they do, the rounding is what carries the honesty.

## File Structure

**Created:**

| Path | Responsibility |
|---|---|
| `pyproject.toml` (repo root) | ruff, mypy, pytest configuration for the whole repo |
| `.pre-commit-config.yaml` | local hooks running ruff + mypy against the installed dev deps |
| `backend/requirements-dev.txt` | pinned dev/test dependencies |
| `backend/tests/conftest.py` | shared fixtures: seeded rng, synthetic price frames, fake price provider |
| `backend/src/data_quality.py` | verified-data-error screening for price series (spec 1.3) |
| `backend/src/joint_models.py` | multivariate GMM fit + sampling + regime reporting (spec 1.2) |
| `backend/src/portfolio_math.py` | asset price paths, portfolio construction under rebalancing rules (spec 1.4) |
| `backend/src/risk_metrics.py` | percentiles, annualisation, Sharpe/Sortino/Calmar, drawdown, VaR/CVaR (spec 1.1, 1.5, 1.7) |
| `backend/src/contributions.py` | return and risk decomposition across holdings (spec 1.6) |
| `backend/src/risk_free.py` | `^IRX` 3-month T-bill provider with TTL cache and fallback (spec 1.5) |
| `docs/METHODOLOGY.md` | the public defence of every formula (spec Phase 0.2) |
| `frontend/src/lib/chartSample.js` | chart-sample marker + assertion guard (spec 1.1) |
| `frontend/src/components/RiskContribution.jsx` | weight-vs-risk-contribution panel (spec 1.6) |

**Rewritten:**

| Path | Change |
|---|---|
| `backend/src/data_download.py` | return volume alongside price; delete the dead `"Adj Close"` branch |
| `backend/src/correlation.py` | `eigvalsh` + Higham projection + vectorised chunked sampling; ticker-ordered returns frame |
| `backend/src/generative_model.py`, `gmm_model.py`, `ewma_vol.py` | accept an explicit `rng`; type annotations |
| `backend/main.py` | one `Generator` per request; new request/response models; wire every new module |
| `backend/requirements.txt` | exact version pins |
| `frontend/src/App.jsx` | consume server percentiles; renamed chart-sample fields; new request params; rf and VaR labelling |

**Deleted in Task 1** (unused, imported by nothing): `backend/src/visualization.py`, `backend/src/debug_day1.py`, `backend/src/simulate_paths.py`, `backend/src/test.portfolio.py`. Git history preserves them. Two of these are worse than merely unused: `test.portfolio.py` has a dot in its filename, so pytest's `test_*.py` / `*_test.py` collection patterns have never matched it and it has been silently uncollected for its whole life; and `simulate_paths.py` duplicates path-construction logic that now lives in `main.py` and `src/portfolio_math.py`, which is a divergence trap the moment someone opens the wrong file.

**Also created:** `backend/src/simulation_runner.py` (batch loop and accumulators, Task 10), `docs/golden/baseline_v2.json` (captured in Task 1), `docs/NUMBERS_CHANGED.md` (Task 14).

---

### Task 1: Test harness, linting, pinned dependencies, methodology skeleton

Implements spec Phase 0 items 1, 2, 3, 5. Establishes the gate every later task must keep green.

**Files:**
- Create: `pyproject.toml` (repo root)
- Create: `.pre-commit-config.yaml` (repo root)
- Create: `backend/requirements-dev.txt`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_smoke.py`
- Create: `docs/METHODOLOGY.md`
- Create: `scripts/capture_baseline.py`
- Create: `docs/golden/baseline_v2.json` (generated, committed)
- Modify: `backend/requirements.txt`
- Modify: `backend/src/returns_preprocess.py` (annotations only)
- Delete: `backend/src/visualization.py`, `backend/src/debug_day1.py`, `backend/src/simulate_paths.py`, `backend/src/test.portfolio.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `pytest` runnable from repo root with `backend` on the path; `ruff check .` and `mypy` both clean; fixtures `rng`, `make_prices`, `make_correlated_prices`, `fake_price_provider` available to every later test module.

- [ ] **Step 1: Pin the runtime dependencies**

Replace `backend/requirements.txt` entirely. These are the versions currently resolved in `backend/env`, verified with `pip list`:

```
# Core API Framework
fastapi==0.124.4
uvicorn[standard]==0.38.0
pydantic==2.12.5
python-multipart==0.0.20

# Data Processing & Simulation
numpy==2.3.5
pandas==2.3.3
scikit-learn==1.8.0
scipy==1.16.3

# Data Download
yfinance==0.2.66
requests==2.32.5

# Visualization (used only by src/visualization.py, not by the API)
matplotlib==3.10.8

# Environment Variables
python-dotenv==1.2.1
```

- [ ] **Step 2: Install and pin the dev dependencies**

```bash
backend/env/Scripts/python.exe -m pip install pytest pytest-cov httpx ruff mypy pre-commit pandas-stubs types-requests
```

Then freeze exactly what resolved, so the file contains no guessed versions:

```bash
backend/env/Scripts/python.exe -m pip freeze | grep -iE "^(pytest|pytest-cov|httpx|ruff|mypy|pre-commit|pandas-stubs|types-requests)==" > backend/requirements-dev.txt
```

Verify the file has 8 lines, each with a `==` pin:

```bash
cat backend/requirements-dev.txt
```

- [ ] **Step 3: Create the root `pyproject.toml`**

```toml
[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["backend/env", "frontend"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "NPY", "RUF"]

[tool.mypy]
python_version = "3.12"
mypy_path = "backend"
files = ["backend/src", "backend/main.py", "backend/tests"]
disallow_untyped_defs = true
warn_unused_ignores = true
warn_return_any = true
ignore_missing_imports = true
exclude = "(backend/env|backend/src/correlation\\.py|backend/main\\.py)"

[tool.pytest.ini_options]
testpaths = ["backend/tests"]
pythonpath = ["backend"]
addopts = "-q --strict-markers"
markers = [
    "benchmark: performance budget tests, slow and memory-hungry",
]
```

There is no dead-code exclusion list, because Step 3b deletes the dead code. The only two exclusions are `correlation.py` and `main.py`, un-excluded in Tasks 4 and 10 respectively when those files are rewritten with full annotations. This keeps the gate green at every commit instead of demanding a big-bang annotation pass on code that is about to be replaced.

- [ ] **Step 3b: Delete the dead scripts**

Confirm nothing imports them, then delete:

```bash
grep -rn "visualization\|debug_day1\|simulate_paths\|test\.portfolio" backend --include=*.py | grep -v "^backend/env"
```

Expected: no hits outside the four files themselves. If anything does import one of them, stop and report rather than deleting.

```bash
git rm backend/src/visualization.py backend/src/debug_day1.py backend/src/simulate_paths.py backend/src/test.portfolio.py
```

Then clear the stale bytecode so a `.pyc` cannot satisfy a stray import:

```bash
rm -rf backend/__pycache__ backend/src/__pycache__
```

Note for the record, and for the commit message: `test.portfolio.py` was never collected by pytest. The default collection patterns are `test_*.py` and `*_test.py`; a dot in the filename matches neither, so whatever it asserted has never run. It is not a test suite being deleted — it is a file that has never executed.

- [ ] **Step 4: Create `.pre-commit-config.yaml`**

Local hooks that call the already-installed dev tools. No `rev` pins to guess, and it works offline:

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: ruff check --fix
        language: system
        types: [python]
        files: ^backend/
      - id: ruff-format
        name: ruff format
        entry: ruff format
        language: system
        types: [python]
        files: ^backend/
      - id: mypy
        name: mypy
        entry: mypy
        language: system
        pass_filenames: false
        files: ^backend/
```

Install the hook:

```bash
backend/env/Scripts/pre-commit.exe install
```

- [ ] **Step 5: Write `backend/tests/conftest.py`**

These fixtures are the only source of market data in the entire test suite. Nothing hits the network.

```python
"""Shared fixtures. No test in this suite touches the network."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

PriceFactory = Callable[..., pd.DataFrame]


@pytest.fixture
def rng() -> np.random.Generator:
    """A seeded Generator. Every test that samples must use this or its own explicit one."""
    return np.random.default_rng(12345)


@pytest.fixture
def make_prices() -> PriceFactory:
    """Build a synthetic geometric-Brownian price frame shaped like download_price_data output."""

    def _make(
        n_days: int = 800,
        start: float = 100.0,
        mu: float = 0.0003,
        sigma: float = 0.012,
        seed: int = 7,
        volume: float = 1_000_000.0,
        index_start: str = "2021-01-04",
    ) -> pd.DataFrame:
        gen = np.random.default_rng(seed)
        log_rets = gen.normal(mu, sigma, size=n_days)
        prices = start * np.exp(np.cumsum(log_rets))
        index = pd.bdate_range(index_start, periods=n_days, name="date")
        return pd.DataFrame(
            {"price": prices, "volume": np.full(n_days, volume)},
            index=index,
        )

    return _make


@pytest.fixture
def make_correlated_prices() -> Callable[..., dict[str, pd.DataFrame]]:
    """Build price frames for several tickers with a known target correlation."""

    def _make(
        tickers: list[str],
        target_corr: float = 0.5,
        n_days: int = 800,
        sigma: float = 0.012,
        mu: float = 0.0003,
        seed: int = 11,
        index_start: str = "2021-01-04",
    ) -> dict[str, pd.DataFrame]:
        gen = np.random.default_rng(seed)
        n = len(tickers)
        corr = np.full((n, n), target_corr)
        np.fill_diagonal(corr, 1.0)
        chol = np.linalg.cholesky(corr)
        shocks = gen.standard_normal((n_days, n)) @ chol.T
        log_rets = mu + sigma * shocks
        index = pd.bdate_range(index_start, periods=n_days, name="date")
        out: dict[str, pd.DataFrame] = {}
        for i, ticker in enumerate(tickers):
            prices = 100.0 * np.exp(np.cumsum(log_rets[:, i]))
            out[ticker] = pd.DataFrame(
                {"price": prices, "volume": np.full(n_days, 1_000_000.0)},
                index=index,
            )
        return out

    return _make


@pytest.fixture
def fake_price_provider(
    make_correlated_prices: Callable[..., dict[str, pd.DataFrame]],
) -> Callable[[str, int], pd.DataFrame]:
    """Drop-in replacement for main.get_cached_price_data. Deterministic per ticker."""
    cache: dict[str, pd.DataFrame] = {}

    def _provider(ticker: str, years: int) -> pd.DataFrame:
        if ticker not in cache:
            seed = abs(hash(ticker)) % 10_000
            cache[ticker] = make_correlated_prices([ticker], seed=seed)[ticker]
        return cache[ticker]

    return _provider
```

- [ ] **Step 6: Write the failing smoke test**

`backend/tests/test_smoke.py`:

```python
"""Guards the test harness itself: imports resolve and fixtures produce usable data."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def test_src_package_imports() -> None:
    from src.returns_preprocess import compute_log_returns

    assert callable(compute_log_returns)


def test_make_prices_fixture_shape(make_prices: Callable[..., pd.DataFrame]) -> None:
    df = make_prices(n_days=250)
    assert list(df.columns) == ["price", "volume"]
    assert len(df) == 250
    assert df.index.name == "date"
    assert (df["price"] > 0).all()


def test_make_prices_is_deterministic(make_prices: Callable[..., pd.DataFrame]) -> None:
    assert make_prices(seed=3).equals(make_prices(seed=3))
```

- [ ] **Step 7: Run it to confirm the harness works**

```bash
backend/env/Scripts/python.exe -m pytest -v
```

Expected: 3 passed. If `pythonpath` is misconfigured the first test fails with `ModuleNotFoundError: No module named 'src'` — fix `pyproject.toml`, do not add `sys.path` hacks to the test file.

- [ ] **Step 8: Annotate `returns_preprocess.py` so mypy is clean**

Add annotations to the two public functions and drop the network-dependent `__main__` block (it calls `download_price_data`, which mypy and ruff both flag and which nothing imports):

```python
import numpy as np
import pandas as pd


def compute_log_returns(price_df: pd.DataFrame, price_col: str = "price") -> pd.Series:
    """
    Given a DataFrame with a price column, compute daily log returns.

    r_t = log(P_t / P_{t-1})
        = log(P_t) - log(P_{t-1})

    Returns a Series indexed by date with name 'log_return'.
    """
    if price_col not in price_df.columns:
        raise KeyError(f"Column '{price_col}' not found in DataFrame")

    prices = price_df[price_col].astype(float)
    log_returns = np.log(prices).diff().dropna()
    log_returns.name = "log_return"
    return log_returns


def attach_log_returns(price_df: pd.DataFrame, price_col: str = "price") -> pd.DataFrame:
    """
    Given a DataFrame with a price column, compute daily log returns and
    attach them as a new column 'log_return'.
    """
    if price_col not in price_df.columns:
        raise KeyError(f"Column '{price_col}' not found in DataFrame")

    df = price_df.copy()
    df["log_return"] = np.log(df[price_col].astype(float)).diff()
    return df.dropna()
```

- [ ] **Step 9: Run the lint and type gates**

```bash
backend/env/Scripts/python.exe -m ruff check .
```

Expected: `All checks passed!`

```bash
backend/env/Scripts/python.exe -m mypy
```

Expected: `Success: no issues found`. If `generative_model.py`, `gmm_model.py`, `ewma_vol.py`, or `data_download.py` raise `disallow_untyped_defs` errors, annotate their signatures now — they are small and Tasks 2 and 3 rewrite their bodies, not their shape. Do **not** widen the mypy exclude list to silence them.

- [ ] **Step 10: Create `docs/METHODOLOGY.md` with the conventions section**

This file is the public defence of the numbers (spec Phase 0.2). Later tasks append one section each; this step writes the front matter and the conventions that every later section depends on.

```markdown
# Methodology

This document is the defence of every number the platform reports. Each formula
implemented in the codebase has an entry below giving the equation, the assumption
set, the estimation window, and what breaks it.

Nothing here is a projection or an expectation. Every simulated figure is a
**conditional scenario**: the consequence of a stated model and a stated parameter
set, not a forecast.

## Conventions

These hold everywhere unless a section states otherwise.

| Convention | Value | Defined in |
|---|---|---|
| Trading days per year | 252 | `src/risk_metrics.TRADING_DAYS_PER_YEAR` |
| Return type used for estimation | daily log returns, `r_t = ln(P_t / P_{t-1})` | `src/returns_preprocess.compute_log_returns` |
| Return type used for portfolio arithmetic | daily simple returns, `s_t = exp(r_t) - 1` | `src/portfolio_math` |
| Prices | split- and dividend-adjusted close (`yfinance auto_adjust=True`) | `src/data_download` |
| Portfolio value path | `portfolio_paths[p, t]` is the value of an initially-1.0 portfolio after `t+1` days; the initial 1.0 is implicit | `src/portfolio_math.build_portfolio_paths` |
| Terminal return | `portfolio_paths[:, -1] - 1.0` | `src/portfolio_math` |
| Tail-risk sign | losses positive (`convention: "loss_positive"`) | `src/risk_metrics.tail_risk` |
| Percentile interpolation | `numpy` linear interpolation between order statistics (`np.percentile` default) | `src/risk_metrics.percentiles` |
| Randomness | one explicit `numpy.random.Generator` per request, threaded into every sampling function. No global `numpy` random state is read or written anywhere in the codebase. | `main.py` |

### Why log returns for estimation and simple returns for aggregation

Log returns are additive **across time**, which is what makes them the right unit
for fitting a daily model and for compounding a single asset's path. They are not
additive **across assets**: `ln(1 + Σ wᵢsᵢ) ≠ Σ wᵢ ln(1 + sᵢ)`. By the concavity of
the logarithm the right-hand side is strictly smaller whenever asset returns
differ, so aggregating a portfolio in log space understates its return by the
diversification (Jensen) term. Portfolio aggregation therefore always happens in
simple-return space. See "Portfolio construction" below.
```

- [ ] **Step 11: Capture the golden baseline (manual, requires network)**

This is the "before" side of the characterization diff Task 14 produces. It must be captured **now**, against completely unmodified behaviour — after this task, every commit changes numbers.

Write `scripts/capture_baseline.py`:

```python
"""Capture current API output for a fixed config, as the Task 14 baseline.

Run against the ORIGINAL code, before any Phase 1 fix lands. Requires network.

    python scripts/capture_baseline.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

TICKERS = ["SPY", "NVDA", "MSFT"]
OUTPUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "golden" / "baseline_v2.json"

# Fields that are large path dumps: recorded by shape only, not by value.
_BULKY = ("paths_sample", "portfolio_paths_sample", "asset_paths_sample", "final_prices")


def _summarise(payload: dict[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in payload.items():
        if key in _BULKY:
            if isinstance(value, list):
                out[f"{key}__shape"] = [len(value), len(value[0]) if value else 0]
            elif isinstance(value, dict):
                out[f"{key}__keys"] = sorted(value)
        elif key == "final_returns" and isinstance(value, list):
            out["final_returns__count"] = len(value)
        else:
            out[key] = value
    return out


def main_capture() -> None:
    client = TestClient(main.app)
    captured: dict[str, object] = {"config": {"tickers": TICKERS, "seed": 42}}

    for model in ("gaussian", "gmm"):
        response = client.post(
            "/api/simulate-portfolio",
            json={
                "tickers": TICKERS,
                "weights": [1 / 3, 1 / 3, 1 / 3],
                "years": 3,
                "horizon": 365,
                "num_paths": 1000,
                "model": model,
                "random_seed": 42,
            },
        )
        response.raise_for_status()
        captured[f"portfolio_{model}"] = _summarise(response.json())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(captured, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main_capture()
```

Run it:

```bash
backend/env/Scripts/python.exe scripts/capture_baseline.py
```

Expected: `docs/golden/baseline_v2.json` written, containing `portfolio_gaussian` and `portfolio_gmm` objects with `portfolio_stats`, `asset_stats`, and `correlation_matrix` populated.

Two things to verify before moving on, because both are load-bearing for Task 14:

- The equal weights must be sent as `[1/3, 1/3, 1/3]`, which sums to `0.9999999999999999`. The **old** validator uses `np.isclose`, so this passes. If it returns 400, the capture config is wrong — do not "fix" it by changing weights, since the whole point is to record what the old code did.
- Note the capture date in the commit message. `yfinance` returns a trailing window, so the baseline is not reproducible later; that is expected and is exactly why it is committed rather than regenerated.

- [ ] **Step 12: Commit**

```bash
git add pyproject.toml .pre-commit-config.yaml backend/requirements.txt backend/requirements-dev.txt backend/tests docs/METHODOLOGY.md docs/golden scripts/capture_baseline.py backend/src/returns_preprocess.py
git rm --cached -r --ignore-unmatch backend/__pycache__ backend/src/__pycache__
git commit -m "chore: add pytest harness, ruff/mypy gates, pinned deps, and golden baseline

Delete four unused scripts: visualization.py, debug_day1.py, simulate_paths.py,
test.portfolio.py. The last has a dot in its filename and so has never been
collected by pytest; simulate_paths.py duplicated path construction that lives
in main.py. Git history preserves all four.

Capture docs/golden/baseline_v2.json against unmodified behaviour, for the
Task 14 characterization diff."
```

---

### Task 2: Thread an explicit Generator through every sampling function

Implements spec Phase 0.4. The current code calls `np.random.seed(request.random_seed)` inside a request handler that runs in a `ThreadPoolExecutor` — two concurrent requests race on global numpy state and neither gets the seed it asked for.

**Files:**
- Modify: `backend/src/generative_model.py`
- Modify: `backend/src/gmm_model.py`
- Modify: `backend/src/ewma_vol.py:41-60`
- Modify: `backend/src/correlation.py:121-176` (`simulate_correlated_returns` — rng only; Task 4 vectorises it)
- Modify: `backend/main.py` (remove both `np.random.seed` calls, create one Generator per request)
- Test: `backend/tests/test_sampling_rng.py`

**Interfaces:**
- Consumes: `rng` fixture from Task 1.
- Produces:
  - `sample_gaussian(mu: float, sigma: float, horizon: int, num_paths: int, rng: np.random.Generator) -> np.ndarray` shape `(num_paths, horizon)`
  - `fit_gmm(returns: pd.Series, n_components: int = 3, seed: int = 42) -> GaussianMixture`
  - `sample_gmm(gmm: GaussianMixture, horizon: int, num_paths: int, rng: np.random.Generator) -> np.ndarray` shape `(num_paths, horizon)`
  - `sample_ewma_returns(mu: float, vol_forecast: np.ndarray, num_paths: int, rng: np.random.Generator) -> np.ndarray` shape `(num_paths, horizon)`
  - `simulate_correlated_returns(means, stds, cholesky_factor, horizon, num_paths, rng) -> np.ndarray` shape `(num_paths, horizon, n_assets)`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_sampling_rng.py`:

```python
"""Every sampling function must be a pure function of its explicit Generator."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.correlation import simulate_correlated_returns
from src.ewma_vol import sample_ewma_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm


def _seeded_pair(fn) -> tuple[np.ndarray, np.ndarray]:
    return fn(np.random.default_rng(99)), fn(np.random.default_rng(99))


def test_sample_gaussian_is_a_pure_function_of_its_generator() -> None:
    a, b = _seeded_pair(lambda g: sample_gaussian(0.0004, 0.011, 50, 200, g))
    np.testing.assert_array_equal(a, b)
    assert a.shape == (200, 50)


def test_sample_gaussian_ignores_global_numpy_state() -> None:
    """Reseeding global state between two identical calls must change nothing."""
    np.random.seed(1)
    first = sample_gaussian(0.0004, 0.011, 20, 50, np.random.default_rng(7))
    np.random.seed(2)
    second = sample_gaussian(0.0004, 0.011, 20, 50, np.random.default_rng(7))
    np.testing.assert_array_equal(first, second)


def test_sample_gaussian_recovers_its_moments() -> None:
    """Closed form: the sample mean and sd converge to the requested parameters."""
    mu, sigma = 0.0005, 0.02
    draws = sample_gaussian(mu, sigma, 1000, 2000, np.random.default_rng(3))
    assert draws.mean() == pytest.approx(mu, abs=4 * sigma / np.sqrt(draws.size))
    assert draws.std(ddof=1) == pytest.approx(sigma, rel=0.01)


def test_sample_ewma_returns_is_a_pure_function_of_its_generator() -> None:
    vol = np.full(30, 0.015)
    a, b = _seeded_pair(lambda g: sample_ewma_returns(0.0003, vol, 100, g))
    np.testing.assert_array_equal(a, b)
    assert a.shape == (100, 30)


def test_sample_ewma_returns_scales_with_the_vol_vector() -> None:
    """A vol vector that doubles halfway through must double the cross-path sd."""
    vol = np.concatenate([np.full(500, 0.01), np.full(500, 0.02)])
    draws = sample_ewma_returns(0.0, vol, 4000, np.random.default_rng(5))
    first_half = draws[:, :500].std(ddof=1)
    second_half = draws[:, 500:].std(ddof=1)
    assert second_half / first_half == pytest.approx(2.0, rel=0.03)


def test_sample_gmm_is_a_pure_function_of_its_generator() -> None:
    returns = pd.Series(np.random.default_rng(1).normal(0.0, 0.01, 600))
    gmm = fit_gmm(returns, n_components=2)
    a, b = _seeded_pair(lambda g: sample_gmm(gmm, 40, 150, g))
    np.testing.assert_array_equal(a, b)
    assert a.shape == (150, 40)


def test_sample_gmm_recovers_a_known_two_component_mixture() -> None:
    """Fit a mixture built by hand, then check the sampled sd matches the analytic sd.

    For a zero-mean scale mixture, Var = Σ wₖ σₖ².
    """
    gen = np.random.default_rng(21)
    calm = gen.normal(0.0, 0.005, 9000)
    crisis = gen.normal(0.0, 0.040, 1000)
    returns = pd.Series(np.concatenate([calm, crisis]))

    gmm = fit_gmm(returns, n_components=2)
    draws = sample_gmm(gmm, 200, 500, np.random.default_rng(4))

    analytic_sd = np.sqrt(0.9 * 0.005**2 + 0.1 * 0.040**2)
    assert draws.std(ddof=1) == pytest.approx(analytic_sd, rel=0.10)


def test_simulate_correlated_returns_is_a_pure_function_of_its_generator() -> None:
    means = np.array([0.0003, 0.0004])
    stds = np.array([0.010, 0.015])
    chol = np.linalg.cholesky(np.array([[1.0, 0.4], [0.4, 1.0]]))
    a, b = _seeded_pair(lambda g: simulate_correlated_returns(means, stds, chol, 30, 100, g))
    np.testing.assert_array_equal(a, b)
    assert a.shape == (100, 30, 2)


def test_no_global_numpy_seeding_remains_in_the_source() -> None:
    """Regression guard for spec Phase 0.4: the race condition must stay dead."""
    import pathlib

    banned = ("np.random.seed", "np.random.randn", "np.random.normal", "np.random.choice")
    src = pathlib.Path(__file__).resolve().parents[1]
    checked = 0
    for path in [*(src / "src").glob("*.py"), src / "main.py"]:
        text = path.read_text(encoding="utf-8")
        checked += 1
        for token in banned:
            assert token not in text, f"{path.name} still calls {token}"
    assert checked > 5
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_sampling_rng.py -v
```

Expected: failures. `sample_gaussian` raises `TypeError` on the Generator argument (it currently takes `random_state=42` and calls `default_rng` internally); `sample_gmm` and `sample_ewma_returns` raise `TypeError` for the extra argument; `test_no_global_numpy_seeding_remains_in_the_source` fails naming `main.py` and `correlation.py`.

- [ ] **Step 3: Rewrite `generative_model.py`**

```python
import numpy as np
import pandas as pd


def fit_gaussian(returns: pd.Series) -> tuple[float, float]:
    """Fit the mean and standard deviation of daily log returns."""
    clean = returns.dropna().astype(float)
    return float(clean.mean()), float(clean.std(ddof=1))


def sample_gaussian(
    mu: float,
    sigma: float,
    horizon: int,
    num_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample daily log returns from N(mu, sigma^2). Shape: (num_paths, horizon)."""
    return rng.normal(mu, sigma, size=(num_paths, horizon))
```

- [ ] **Step 4: Rewrite `gmm_model.py`**

`GaussianMixture.sample()` draws from global numpy state and cannot accept a Generator, so component selection and the conditional normals are sampled here instead. `reg_covar` is lowered from the sklearn default of `1e-6` because daily return variance is around `1.4e-4` — the default regulariser would be a material fraction of the quantity being estimated.

```python
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

# sklearn's default reg_covar (1e-6) is ~1% of daily return variance (~1.4e-4).
# At this scale it is a material distortion, not a numerical safeguard.
REG_COVAR = 1e-12


def fit_gmm(returns: pd.Series, n_components: int = 3, seed: int = 42) -> GaussianMixture:
    """Fit a Gaussian Mixture Model to daily log returns."""
    clean = returns.dropna().astype(float).to_numpy().reshape(-1, 1)
    if len(clean) < 30 * n_components:
        raise ValueError(
            f"Need at least {30 * n_components} observations to fit a "
            f"{n_components}-component GMM, got {len(clean)}"
        )
    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        random_state=seed,
        n_init=5,
        reg_covar=REG_COVAR,
    )
    gmm.fit(clean)
    return gmm


def sample_gmm(
    gmm: GaussianMixture,
    horizon: int,
    num_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample daily log returns from a fitted 1-D GMM. Shape: (num_paths, horizon).

    GaussianMixture.sample() draws from global numpy state, so the mixture is
    sampled here with the caller's Generator instead.
    """
    weights = np.asarray(gmm.weights_, dtype=float)
    means = np.asarray(gmm.means_, dtype=float).ravel()
    stds = np.sqrt(np.asarray(gmm.covariances_, dtype=float).reshape(-1))

    components = rng.choice(len(weights), size=horizon * num_paths, p=weights)
    samples = rng.normal(means[components], stds[components])
    return samples.reshape(num_paths, horizon)
```

- [ ] **Step 5: Update `sample_ewma_returns` in `ewma_vol.py`**

Replace the function body (lines 41-60). Leave `compute_ewma_vol` and `forecast_ewma_vol` alone apart from annotations, which they already carry:

```python
def sample_ewma_returns(
    mu: float,
    vol_forecast: np.ndarray,
    num_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate daily log returns using a forecast volatility vector.

    vol_forecast: shape (horizon,)
    Returns: shape (num_paths, horizon)
    """
    horizon = len(vol_forecast)
    z_scores = rng.standard_normal((num_paths, horizon))
    return mu + z_scores * vol_forecast.reshape(1, horizon)
```

- [ ] **Step 6: Swap the Generator into `simulate_correlated_returns`**

In `backend/src/correlation.py`, change only the signature and the random draw. The double loop stays for now — Task 4 removes it, and keeping the two changes in separate commits means the vectorisation can be reviewed as an isolated numerical equivalence:

```python
def simulate_correlated_returns(
    means: np.ndarray,
    stds: np.ndarray,
    cholesky_factor: np.ndarray,
    horizon: int,
    num_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate correlated daily log returns using a Cholesky factor.

    Returns shape (num_paths, horizon, n_assets).
    """
    n_assets = len(means)
    Z = rng.standard_normal((num_paths, horizon, n_assets))

    X = np.zeros_like(Z)
    for path in range(num_paths):
        for t in range(horizon):
            X[path, t, :] = cholesky_factor @ Z[path, t, :]

    return means + stds * X
```

Delete the `if random_seed is not None: np.random.seed(random_seed)` block and the `random_seed` parameter.

- [ ] **Step 7: Create one Generator per request in `main.py`**

Delete `np.random.seed(request.random_seed)` from both `/api/simulate` (line 175) and `/api/simulate-portfolio` (line 252). In each handler, build the Generator once, outside the thread-pool closure, and pass it down:

```python
rng = np.random.default_rng(request.random_seed)
```

In `/api/simulate`, update the three call sites inside `_run()`:

```python
returns_matrix = sample_gaussian(adj_mu, sigma, request.horizon, request.num_paths, rng)
...
returns_matrix = sample_gmm(gmm, request.horizon, request.num_paths, rng)
...
returns_matrix = sample_ewma_returns(adj_mu, vol_forecast, request.num_paths, rng)
```

In `/api/simulate-portfolio`, update the one call site:

```python
correlated_returns = simulate_correlated_returns(
    means, stds, L, request.horizon, request.num_paths, rng
)
```

The Generator is created per request and never shared, so two concurrent handlers cannot interfere — which is exactly what the old global `np.random.seed` could not guarantee.

- [ ] **Step 8: Run the tests to verify they pass**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_sampling_rng.py -v
```

Expected: 9 passed.

- [ ] **Step 9: Run the full gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

Expected: all pass. `correlation.py` and `main.py` are still mypy-excluded at this point, so annotate `generative_model.py`, `gmm_model.py`, and `ewma_vol.py` fully — they are checked.

- [ ] **Step 10: Append the randomness section to `docs/METHODOLOGY.md`**

```markdown
## Randomness and reproducibility

Every sampling function takes an explicit `numpy.random.Generator` as a required
argument. `main.py` constructs exactly one Generator per request from
`request.random_seed` and threads it into every draw.

**What this fixes.** The previous implementation called `np.random.seed(seed)`
inside a request handler that executes in a `ThreadPoolExecutor`. Global numpy
random state is process-wide, so two concurrent requests would reseed each other
mid-simulation: neither response was reproducible, and identical inputs could
return different numbers depending on traffic. Threading a Generator makes each
request's draw sequence a pure function of its own seed.

**Assumption set.** PCG64 (numpy's default bit generator) is adequate for Monte
Carlo risk work at these path counts. Seeds are not cryptographic.

**What breaks it.** Any new code path that calls `np.random.*` module-level
functions, or any library call that samples from global state — notably
`sklearn.mixture.GaussianMixture.sample()`, which is why `src/gmm_model.py` and
`src/joint_models.py` sample their mixtures by hand instead. A regression test
(`tests/test_sampling_rng.py::test_no_global_numpy_seeding_remains_in_the_source`)
greps the source for the banned calls.
```

- [ ] **Step 11: Commit**

```bash
git add backend/src/generative_model.py backend/src/gmm_model.py backend/src/ewma_vol.py backend/src/correlation.py backend/main.py backend/tests/test_sampling_rng.py docs/METHODOLOGY.md
git commit -m "fix: thread explicit numpy Generator through all sampling, removing global-seed race"
```

---

### Task 3: Replace the tail filter with a verified-data-error screen

Implements spec 1.3. `log_returns[log_returns.abs() < 0.20]` deletes every daily move above 20% before fitting — that is, it deletes precisely the observations a risk model exists to describe. The single-asset GMM branch then clips simulated returns to ±12% and subtracts their mean, truncating the tails a second time and annihilating drift.

**Files:**
- Create: `backend/src/data_quality.py`
- Create: `backend/tests/test_data_quality.py`
- Modify: `backend/src/data_download.py` (add volume, delete the dead `"Adj Close"` branch)
- Modify: `backend/main.py` (screen on fetch; delete the filter, the clip, and the demean)
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: `make_prices` fixture from Task 1.
- Produces:
  - `download_price_data(ticker: str, years: int = 3) -> pd.DataFrame` with columns `["price", "volume"]`
  - `screen_price_series(df: pd.DataFrame, ticker: str = "") -> tuple[pd.DataFrame, DataQualityReport]`
  - `DataQualityReport` dataclass with fields `ticker, rows_in, rows_out, non_finite_price_days, non_positive_price_days, zero_volume_days, stale_price_days, split_artifact_days, removed_dates`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_data_quality.py`. The first two tests are the regression tests for the defect — genuine crashes must survive the screen:

```python
"""The screen removes verified data errors only. Real market moves must survive."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from src.data_quality import screen_price_series


def _frame(prices: list[float], volume: list[float] | None = None) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-01", periods=len(prices), name="date")
    vol = volume if volume is not None else [1_000_000.0] * len(prices)
    return pd.DataFrame({"price": prices, "volume": vol}, index=index)


def test_a_thirty_percent_crash_day_survives() -> None:
    """The exact behaviour the old |r| < 0.20 filter destroyed."""
    df = _frame([100.0, 70.0, 72.0, 71.0])
    cleaned, report = screen_price_series(df, "CRASH")
    assert len(cleaned) == 4
    assert report.rows_out == 4
    assert report.removed_dates == []


def test_a_black_monday_scale_move_survives() -> None:
    """-22.6% in one session. Real, and the whole point of a tail model."""
    df = _frame([100.0, 77.4, 78.0])
    cleaned, _ = screen_price_series(df, "DJIA")
    assert len(cleaned) == 3


def test_an_exact_two_for_one_split_artifact_is_removed() -> None:
    """A failed split adjustment lands within 0.5% of exactly 0.5."""
    df = _frame([100.0, 101.0, 50.5, 51.0])
    cleaned, report = screen_price_series(df, "SPLIT")
    assert report.split_artifact_days == 1
    assert len(cleaned) == 3
    assert 50.5 not in set(cleaned["price"])


def test_a_stale_run_of_three_drops_the_repeats_and_keeps_the_first() -> None:
    df = _frame([100.0, 101.0, 101.0, 101.0, 102.0])
    cleaned, report = screen_price_series(df, "STALE")
    assert report.stale_price_days == 2
    assert list(cleaned["price"]) == [100.0, 101.0, 102.0]


def test_a_single_unchanged_day_is_not_treated_as_stale() -> None:
    """One flat day is an ordinary quiet session, not a frozen feed."""
    df = _frame([100.0, 101.0, 101.0, 102.0])
    cleaned, report = screen_price_series(df, "QUIET")
    assert report.stale_price_days == 0
    assert len(cleaned) == 4


def test_zero_volume_days_are_removed() -> None:
    df = _frame([100.0, 101.0, 102.0], volume=[1_000_000.0, 0.0, 1_000_000.0])
    cleaned, report = screen_price_series(df, "HALTED")
    assert report.zero_volume_days == 1
    assert list(cleaned["price"]) == [100.0, 102.0]


def test_non_finite_and_non_positive_prices_are_removed() -> None:
    df = _frame([100.0, np.nan, 0.0, -5.0, 102.0])
    cleaned, report = screen_price_series(df, "BROKEN")
    assert report.non_finite_price_days == 1
    assert report.non_positive_price_days == 2
    assert list(cleaned["price"]) == [100.0, 102.0]


def test_clean_synthetic_data_loses_nothing(make_prices: Callable[..., pd.DataFrame]) -> None:
    df = make_prices(n_days=500)
    cleaned, report = screen_price_series(df, "CLEAN")
    assert report.rows_in == report.rows_out == 500
    assert cleaned.equals(df)


def test_a_missing_volume_column_is_tolerated() -> None:
    index = pd.bdate_range("2024-01-01", periods=3, name="date")
    df = pd.DataFrame({"price": [100.0, 101.0, 102.0]}, index=index)
    cleaned, report = screen_price_series(df, "NOVOL")
    assert report.zero_volume_days == 0
    assert len(cleaned) == 3


def test_the_report_lists_the_dates_it_removed() -> None:
    df = _frame([100.0, 101.0, 102.0], volume=[1_000_000.0, 0.0, 1_000_000.0])
    _, report = screen_price_series(df, "HALTED")
    assert len(report.removed_dates) == 1
    assert "2024-01-02" in report.removed_dates[0]


def test_no_magnitude_filter_or_clip_survives_in_the_source() -> None:
    """Regression guard for spec 1.3."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    banned = ("abs() < 0.20", "np.clip(returns_matrix", "returns_matrix - np.mean")
    for path in [*(root / "src").glob("*.py"), root / "main.py"]:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} still contains {token!r}"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_data_quality.py -v
```

Expected: all fail with `ModuleNotFoundError: No module named 'src.data_quality'`, except `test_no_magnitude_filter_or_clip_survives_in_the_source`, which fails naming `main.py`.

- [ ] **Step 3: Write `backend/src/data_quality.py`**

```python
"""Data-quality screening for daily price series.

This module removes only observations that are verifiable data errors. Large but
genuine market moves are never removed: deleting tails is what makes a risk model
lie about risk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Ratios a failed split or reverse-split adjustment produces, e.g. 2:1 -> 0.5.
_SPLIT_RATIOS: tuple[float, ...] = (2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0)

# How close to an exact split ratio a move must land to be called an artifact.
_SPLIT_TOLERANCE = 0.005

# Never inspect a move smaller than this for split artifacts: |ln(1.4)| ~= 0.336.
_SPLIT_MIN_ABS_LOG_RETURN = 0.336

# A price is stale only inside a run of at least this many identical closes.
# One unchanged session is an ordinary quiet day; three is a frozen feed.
_STALE_RUN_MIN = 3


@dataclass
class DataQualityReport:
    """Audit trail for one screened series. Every removal is counted and dated."""

    ticker: str
    rows_in: int
    rows_out: int
    non_finite_price_days: int = 0
    non_positive_price_days: int = 0
    zero_volume_days: int = 0
    stale_price_days: int = 0
    split_artifact_days: int = 0
    removed_dates: list[str] = field(default_factory=list)


def _is_near_split_ratio(ratio: float) -> bool:
    """True if `ratio` sits within _SPLIT_TOLERANCE of a canonical split ratio."""
    if not np.isfinite(ratio) or ratio <= 0.0:
        return False
    for r in _SPLIT_RATIOS:
        for candidate in (r, 1.0 / r):
            if abs(ratio / candidate - 1.0) <= _SPLIT_TOLERANCE:
                return True
    return False


def screen_price_series(
    df: pd.DataFrame,
    ticker: str = "",
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Remove verified data errors from a price frame.

    Removes, and only removes:
      - non-finite prices (NaN, inf)
      - non-positive prices
      - zero-volume sessions (the instrument did not trade)
      - stale prices inside a run of >= _STALE_RUN_MIN identical closes
      - moves within _SPLIT_TOLERANCE of an exact split ratio and larger than
        _SPLIT_MIN_ABS_LOG_RETURN, i.e. failed corporate-action adjustments

    Returns the cleaned frame and an audit report. Every removal is logged.
    """
    report = DataQualityReport(ticker=ticker, rows_in=len(df), rows_out=len(df))
    if df.empty:
        return df.copy(), report

    prices = df["price"].astype(float)
    if "volume" in df.columns:
        volume = df["volume"].astype(float)
    else:
        volume = pd.Series(np.nan, index=df.index)

    drop = pd.Series(False, index=df.index)

    non_finite = ~np.isfinite(prices)
    report.non_finite_price_days = int(non_finite.sum())
    drop |= non_finite

    non_positive = prices.le(0.0).fillna(False) & ~non_finite
    report.non_positive_price_days = int(non_positive.sum())
    drop |= non_positive

    zero_volume = volume.eq(0.0).fillna(False)
    report.zero_volume_days = int(zero_volume.sum())
    drop |= zero_volume

    # A run boundary is any change in price; runs of length >= _STALE_RUN_MIN are
    # a frozen feed. The first observation of the run is kept.
    same_as_previous = prices.eq(prices.shift(1)) & prices.shift(1).notna()
    run_id = (~same_as_previous).cumsum()
    run_length = prices.groupby(run_id).transform("size")
    stale = same_as_previous & run_length.ge(_STALE_RUN_MIN)
    report.stale_price_days = int(stale.sum())
    drop |= stale

    ratio = prices / prices.shift(1)
    big_move = np.abs(np.log(ratio.where(ratio > 0.0))).gt(_SPLIT_MIN_ABS_LOG_RETURN)
    near_split = ratio.map(_is_near_split_ratio).astype(bool)
    split_artifact = big_move.fillna(False) & near_split
    report.split_artifact_days = int(split_artifact.sum())
    drop |= split_artifact

    cleaned = df.loc[~drop].copy()
    report.rows_out = len(cleaned)
    report.removed_dates = [str(d) for d in df.index[drop]]

    if report.rows_out < report.rows_in:
        logger.warning(
            "data-quality screen %s: removed %d of %d rows "
            "(non_finite=%d non_positive=%d zero_volume=%d stale=%d split=%d) first_dates=%s",
            ticker or "<unknown>",
            report.rows_in - report.rows_out,
            report.rows_in,
            report.non_finite_price_days,
            report.non_positive_price_days,
            report.zero_volume_days,
            report.stale_price_days,
            report.split_artifact_days,
            report.removed_dates[:10],
        )

    return cleaned, report
```

- [ ] **Step 4: Run the data-quality tests**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_data_quality.py -v
```

Expected: 10 passed, and `test_no_magnitude_filter_or_clip_survives_in_the_source` still failing until Step 6.

- [ ] **Step 5: Rewrite `data_download.py` to return volume**

Volume is what makes the zero-volume rule possible, and `auto_adjust=True` already returns adjusted values in `Close`, so the `"Adj Close"` branch is unreachable (spec Phase 5). Both changes land here:

```python
import pandas as pd
import yfinance as yf


def download_price_data(ticker: str, years: int = 3) -> pd.DataFrame:
    """
    Download daily price history for a ticker for the last `years` years.

    Returns a DataFrame with index = date and columns ['price', 'volume'].
    `auto_adjust=True` means `Close` is already split- and dividend-adjusted,
    so there is no `Adj Close` column to prefer.
    """
    data = yf.download(
        ticker,
        period=f"{years}y",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    if data is None or data.empty:
        raise ValueError(f"No data returned for ticker {ticker}")
    if "Close" not in data.columns:
        raise ValueError(f"Downloaded data for {ticker} has no 'Close' column")

    price = data["Close"]
    if isinstance(price, pd.DataFrame):
        price = price.iloc[:, 0]

    df = price.to_frame(name="price")

    if "Volume" in data.columns:
        volume = data["Volume"]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]
        df["volume"] = volume.astype(float)
    else:
        df["volume"] = float("nan")

    df.index.name = "date"
    return df
```

Delete the `__main__` block at the bottom — it performs a live download, which no automated gate can run.

- [ ] **Step 6: Apply the screen in `main.py` and delete the filter, clip, and demean**

In `get_cached_price_data`, screen once at fetch time so every consumer sees clean prices, and cache the report alongside the frame:

```python
# Cache: key -> (screened_dataframe, report, timestamp)
_price_cache: dict[str, tuple[pd.DataFrame, DataQualityReport, float]] = {}


def get_cached_price_data(ticker: str, years: int) -> tuple[pd.DataFrame, DataQualityReport]:
    key = f"{ticker}:{years}y"
    now = time.time()
    cached = _price_cache.get(key)
    if cached is not None and now - cached[2] < CACHE_TTL:
        return cached[0], cached[1]

    raw = download_price_data(ticker, years)
    screened, report = screen_price_series(raw, ticker)
    _price_cache[key] = (screened, report, now)
    return screened, report
```

Then, in `/api/simulate`, replace

```python
log_returns = compute_log_returns(df)
log_returns_clean = log_returns[log_returns.abs() < 0.20]
```

with

```python
log_returns_clean = compute_log_returns(df)
```

Keep the variable name so the three model branches below need no edit. In the `gmm` branch, delete both post-processing lines:

```python
returns_matrix = np.clip(returns_matrix, -0.12, 0.12)
returns_matrix = returns_matrix - np.mean(returns_matrix)
```

In `/api/simulate-portfolio`, replace

```python
log_rets = returns_df[ticker]
clean_rets = log_rets[log_rets.abs() < 0.20]
```

with

```python
clean_rets = returns_df[ticker]
```

Update the two `get_cached_price_data` call sites for the new tuple return. In `/api/simulate`:

```python
df, _quality = get_cached_price_data(request.ticker, request.years)
```

In `/api/simulate-portfolio`:

```python
fetched = {t: get_cached_price_data(t, request.years) for t in request.tickers}
price_data = {t: df for t, (df, _) in fetched.items() if df is not None and not df.empty}
quality_reports = {t: rep for t, (_, rep) in fetched.items()}
```

`quality_reports` is consumed by the response model in Task 10. Until then, prefix it with an underscore if ruff's unused-variable rule flags it.

- [ ] **Step 7: Run the full suite**

```bash
backend/env/Scripts/python.exe -m pytest
```

Expected: all pass, including `test_no_magnitude_filter_or_clip_survives_in_the_source`.

```bash
backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

Expected: both clean.

- [ ] **Step 8: Append the data-quality section to `docs/METHODOLOGY.md`**

```markdown
## Data quality screening

**What was wrong.** The previous pipeline applied `log_returns[log_returns.abs() < 0.20]`
before fitting any model, deleting every daily move larger than 20%. That filter
removes 1987, 2008, 2020, and every single-stock gap — the exact observations a risk
model exists to characterise. A fitted distribution conditioned on the absence of
large moves cannot say anything about large moves. The single-asset GMM branch
compounded it by clipping simulated returns to +/-12% and subtracting their mean,
truncating the simulated tails and destroying drift.

**What replaced it.** `src/data_quality.screen_price_series` removes only
verifiable data errors, counts every removal, and logs them:

| Rule | Threshold | Rationale |
|---|---|---|
| Non-finite price | `NaN`, `+/-inf` | Not a price |
| Non-positive price | `p <= 0` | Not a price; `ln(p)` undefined |
| Zero volume | `volume == 0` | The instrument did not trade; the close is carried, not observed |
| Stale price | inside a run of >= 3 identical closes | A frozen feed. One unchanged session is an ordinary quiet day and is kept |
| Split artifact | `abs(ln(ratio)) > ln(1.4)` **and** ratio within 0.5% of an exact split ratio (2, 3, 4, 5, 6, 7, 8, 10, 15, 20 or their reciprocals) | A failed corporate-action adjustment lands on an almost exact integer ratio; a real market move essentially never does |

**Estimation window.** The screen runs once per ticker at fetch time, over the full
requested history (1–10 years of daily closes), before returns are computed. Removed
rows create a gap that the next return spans, exactly as a market holiday does.

**Assumption set.** `yfinance` with `auto_adjust=True` returns split- and
dividend-adjusted closes, so a near-exact split ratio in the *adjusted* series
indicates the adjustment failed rather than that a split occurred.

**What breaks it.** A genuine move that lands within 0.5% of an exact split ratio
would be removed — a real, exact -50.0% session, for instance. This is a knowingly
accepted trade-off: the probability of a true return landing in that window is
negligible against the certainty that an unadjusted 2:1 split lands in it. It is
recorded in "Known limitations". Illiquid instruments that legitimately print three
identical closes in a row also lose two observations, which biases their measured
volatility marginally upward.
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/data_quality.py backend/src/data_download.py backend/main.py backend/tests/test_data_quality.py docs/METHODOLOGY.md
git commit -m "fix: replace magnitude tail filter with verified-data-error screen"
```

---

### Task 4: Correct the linear algebra and vectorise the correlated sampler

Implements spec 1.8. Three defects in one file: `np.linalg.eigvals` on a symmetric matrix (wrong routine, returns complex values), `C + 1e-6 * I` as a fix for a non-PSD correlation matrix (does not make it PSD — the classic counter-example has a -0.414 eigenvalue), and a `num_paths * horizon` Python-level loop of small matmuls. A fourth, latent defect: `compute_correlation_matrix` returns columns in dict-insertion order, while `weights[i]` is aligned to `request.tickers[i]`.

**Files:**
- Modify: `backend/src/correlation.py` (rewrite)
- Create: `backend/tests/test_correlation.py`
- Modify: `pyproject.toml` (drop `correlation.py` from the mypy exclude)
- Modify: `backend/main.py` (two call sites)
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: `simulate_correlated_returns` signature from Task 2; `make_correlated_prices` fixture from Task 1.
- Produces:
  - `compute_correlation_matrix(price_data: dict[str, pd.DataFrame], tickers: list[str], method: str = "pearson") -> tuple[pd.DataFrame, pd.DataFrame]` — returns frame columns and correlation rows/columns both ordered by `tickers`
  - `nearest_correlation_matrix(A: np.ndarray, max_iter: int = 100, tol: float = 1e-8) -> np.ndarray`
  - `cholesky_factor(corr_matrix: pd.DataFrame, jitter: float = 1e-10) -> np.ndarray`
  - `simulate_correlated_returns(means, stds, cholesky_factor, horizon, num_paths, rng) -> np.ndarray` (vectorised, path-chunked)
  - Module attribute `_MAX_CHUNK_ELEMENTS: int`, monkeypatched by one test
- Note: `build_portfolio_paths` and `compute_portfolio_risk_stats` stay in this file untouched. Tasks 6 and 7 supersede them and Task 10 deletes them, so `main.py` keeps working throughout.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_correlation.py`:

```python
"""Correlation estimation, PD projection, and correlated Gaussian sampling."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest

from src.correlation import (
    cholesky_factor,
    compute_correlation_matrix,
    nearest_correlation_matrix,
    simulate_correlated_returns,
)

# Higham (2002), the standard worked example. Eigenvalues are 1 and 1 +/- sqrt(2),
# so the smallest is about -0.4142 and the matrix is not PSD.
NOT_PSD = np.array([[1.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]])

# The published nearest correlation matrix for NOT_PSD.
HIGHAM_EXPECTED = np.array(
    [
        [1.0000, 0.7607, 0.1573],
        [0.7607, 1.0000, 0.7607],
        [0.1573, 0.7607, 1.0000],
    ]
)


def test_the_old_diagonal_jitter_hack_does_not_fix_a_non_psd_matrix() -> None:
    """Documents why `C + 1e-6 * I` was never a fix. This is the defect."""
    patched = NOT_PSD + np.eye(3) * 1e-6
    assert np.linalg.eigvalsh(patched).min() < -0.4


def test_nearest_correlation_matrix_matches_the_published_higham_answer() -> None:
    result = nearest_correlation_matrix(NOT_PSD)
    np.testing.assert_allclose(result, HIGHAM_EXPECTED, atol=1e-4)


def test_nearest_correlation_matrix_is_a_valid_correlation_matrix() -> None:
    result = nearest_correlation_matrix(NOT_PSD)
    np.testing.assert_allclose(np.diag(result), 1.0, atol=1e-12)
    np.testing.assert_allclose(result, result.T, atol=1e-12)
    assert np.linalg.eigvalsh(result).min() >= -1e-10


def test_nearest_correlation_matrix_leaves_a_valid_matrix_alone() -> None:
    valid = np.array([[1.0, 0.3, 0.1], [0.3, 1.0, 0.2], [0.1, 0.2, 1.0]])
    np.testing.assert_allclose(nearest_correlation_matrix(valid), valid, atol=1e-8)


def test_cholesky_factor_reconstructs_the_correlation_matrix() -> None:
    corr = pd.DataFrame(
        [[1.0, 0.6, -0.2], [0.6, 1.0, 0.1], [-0.2, 0.1, 1.0]],
        index=["A", "B", "C"],
        columns=["A", "B", "C"],
    )
    chol = cholesky_factor(corr)
    assert np.allclose(np.triu(chol, k=1), 0.0)
    np.testing.assert_allclose(chol @ chol.T, corr.to_numpy(), atol=1e-12)


def test_cholesky_factor_succeeds_on_a_non_psd_input() -> None:
    """The old implementation raised LinAlgError here; this must not."""
    corr = pd.DataFrame(NOT_PSD, index=list("ABC"), columns=list("ABC"))
    chol = cholesky_factor(corr)
    reconstructed = chol @ chol.T
    np.testing.assert_allclose(np.diag(reconstructed), 1.0, atol=1e-8)
    assert np.linalg.eigvalsh(reconstructed).min() > 0.0


def test_vectorised_sampler_equals_the_explicit_loop() -> None:
    """Numerical equivalence with the reference implementation it replaces."""
    means = np.array([0.0003, 0.0005, -0.0001])
    stds = np.array([0.010, 0.014, 0.008])
    corr = np.array([[1.0, 0.5, 0.2], [0.5, 1.0, 0.3], [0.2, 0.3, 1.0]])
    chol = np.linalg.cholesky(corr)
    horizon, num_paths = 12, 25

    z = np.random.default_rng(77).standard_normal((num_paths, horizon, 3))
    expected = np.zeros_like(z)
    for path in range(num_paths):
        for t in range(horizon):
            expected[path, t, :] = chol @ z[path, t, :]
    expected = means + stds * expected

    actual = simulate_correlated_returns(
        means, stds, chol, horizon, num_paths, np.random.default_rng(77)
    )
    np.testing.assert_allclose(actual, expected, atol=1e-14)


def test_sampled_returns_reproduce_the_target_correlation() -> None:
    means = np.zeros(3)
    stds = np.array([0.01, 0.02, 0.015])
    target = np.array([[1.0, 0.7, -0.3], [0.7, 1.0, 0.1], [-0.3, 0.1, 1.0]])
    chol = np.linalg.cholesky(target)

    draws = simulate_correlated_returns(means, stds, chol, 400, 500, np.random.default_rng(9))
    flat = draws.reshape(-1, 3)
    np.testing.assert_allclose(np.corrcoef(flat, rowvar=False), target, atol=0.01)


def test_sampled_returns_reproduce_the_target_moments() -> None:
    means = np.array([0.001, -0.002])
    stds = np.array([0.02, 0.03])
    chol = np.linalg.cholesky(np.array([[1.0, 0.4], [0.4, 1.0]]))
    draws = simulate_correlated_returns(means, stds, chol, 500, 400, np.random.default_rng(31))
    flat = draws.reshape(-1, 2)
    np.testing.assert_allclose(flat.mean(axis=0), means, atol=1e-4)
    np.testing.assert_allclose(flat.std(axis=0, ddof=1), stds, rtol=0.02)


def test_path_chunking_does_not_change_the_result() -> None:
    """Chunk size is a memory knob, never a numerical one."""
    from src import correlation

    means, stds = np.array([0.0]), np.array([0.01])
    chol = np.array([[1.0]])
    full = simulate_correlated_returns(means, stds, chol, 50, 200, np.random.default_rng(2))

    original = correlation._MAX_CHUNK_ELEMENTS
    try:
        correlation._MAX_CHUNK_ELEMENTS = 500
        chunked = simulate_correlated_returns(
            means, stds, chol, 50, 200, np.random.default_rng(2)
        )
    finally:
        correlation._MAX_CHUNK_ELEMENTS = original

    np.testing.assert_array_equal(full, chunked)


def test_returns_frame_and_correlation_follow_the_requested_ticker_order(
    make_correlated_prices: Callable[..., dict[str, pd.DataFrame]],
) -> None:
    """Latent defect: weights[i] is aligned to tickers[i], so column order matters."""
    tickers = ["ZZZ", "AAA", "MMM"]
    price_data = make_correlated_prices(tickers)
    shuffled = {"AAA": price_data["AAA"], "MMM": price_data["MMM"], "ZZZ": price_data["ZZZ"]}

    returns_df, corr = compute_correlation_matrix(shuffled, tickers)
    assert list(returns_df.columns) == tickers
    assert list(corr.columns) == tickers
    assert list(corr.index) == tickers


def test_compute_correlation_matrix_rejects_insufficient_overlap(
    make_correlated_prices: Callable[..., dict[str, pd.DataFrame]],
) -> None:
    price_data = make_correlated_prices(["A", "B"], n_days=20)
    with pytest.raises(ValueError, match="overlapping"):
        compute_correlation_matrix(price_data, ["A", "B"])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_correlation.py -v
```

Expected: `ImportError` for `cholesky_factor` and `nearest_correlation_matrix`. `test_the_old_diagonal_jitter_hack_does_not_fix_a_non_psd_matrix` passes immediately — it documents the defect rather than the fix.

- [ ] **Step 3: Rewrite the top of `correlation.py`**

Replace the module docstring, imports, `compute_correlation_matrix`, and `cholesky_decomposition`. Delete `download_multi_asset_data` (nothing imports it) and the `__main__` block (it performs live downloads):

```python
"""Correlation estimation and correlated Gaussian sampling.

Portfolio weights are aligned positionally to the caller's ticker list, so every
matrix this module returns is ordered by that list rather than by dict insertion
order.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.linalg import cholesky

from src.returns_preprocess import compute_log_returns

logger = logging.getLogger(__name__)

_MIN_OVERLAPPING_OBSERVATIONS = 30

# Cap on elements per sampling chunk (~150 MB per float64 temporary). Bounds peak
# memory independently of num_paths x horizon x n_assets.
_MAX_CHUNK_ELEMENTS = 20_000_000


def compute_correlation_matrix(
    price_data: dict[str, pd.DataFrame],
    tickers: list[str],
    method: str = "pearson",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute aligned log returns and their correlation matrix.

    Both returned objects are ordered by `tickers`, matching the positional
    alignment of the caller's weight vector.
    """
    missing = [t for t in tickers if t not in price_data]
    if missing:
        raise ValueError(f"No price data for {missing}")

    returns_df = pd.DataFrame({t: compute_log_returns(price_data[t]) for t in tickers})
    returns_df = returns_df[tickers].dropna()

    if len(returns_df) < _MIN_OVERLAPPING_OBSERVATIONS:
        raise ValueError(
            f"Not enough overlapping observations for correlation analysis: "
            f"{len(returns_df)} < {_MIN_OVERLAPPING_OBSERVATIONS}"
        )

    return returns_df, returns_df.corr(method=method)


def nearest_correlation_matrix(
    A: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> np.ndarray:
    """Nearest correlation matrix in the Frobenius norm (Higham 2002).

    Alternating projections between the PSD cone and the unit-diagonal set, with
    Dykstra's correction. Unlike adding a multiple of the identity, this both
    restores positive semi-definiteness and keeps the diagonal exactly 1.
    """
    A = np.asarray(A, dtype=float)
    Y = (A + A.T) / 2.0
    correction = np.zeros_like(Y)

    for _ in range(max_iter):
        R = Y - correction
        eigenvalues, eigenvectors = np.linalg.eigh(R)
        X = (eigenvectors * np.maximum(eigenvalues, 0.0)) @ eigenvectors.T
        correction = X - R

        Y_next = X.copy()
        np.fill_diagonal(Y_next, 1.0)
        converged = np.linalg.norm(Y_next - Y, ord="fro") <= tol * max(
            1.0, np.linalg.norm(Y, ord="fro")
        )
        Y = Y_next
        if converged:
            break

    np.fill_diagonal(Y, 1.0)
    return (Y + Y.T) / 2.0


def cholesky_factor(corr_matrix: pd.DataFrame, jitter: float = 1e-10) -> np.ndarray:
    """Lower-triangular L with L @ L.T == C.

    If C is not positive definite it is projected to the nearest positive-definite
    correlation matrix first. `eigvalsh` is used rather than `eigvals` because a
    correlation matrix is symmetric: `eigvals` runs the general routine and returns
    complex values whose comparison against a real threshold is meaningless.
    """
    C = np.asarray(corr_matrix.to_numpy(), dtype=float)
    min_eigenvalue = float(np.linalg.eigvalsh(C).min())

    if min_eigenvalue < jitter:
        logger.warning(
            "correlation matrix min eigenvalue %.3e < %.1e; projecting to the "
            "nearest positive-definite correlation matrix (Higham 2002)",
            min_eigenvalue,
            jitter,
        )
        C = nearest_correlation_matrix(C)

        # Projection can leave eigenvalues at exactly 0, which Cholesky rejects.
        # Floor them, then renormalise the diagonal back to 1.
        eigenvalues, eigenvectors = np.linalg.eigh(C)
        if eigenvalues.min() < jitter:
            C = (eigenvectors * np.maximum(eigenvalues, jitter)) @ eigenvectors.T
            scale = np.sqrt(np.diag(C))
            C = C / np.outer(scale, scale)
            np.fill_diagonal(C, 1.0)

    return cholesky(C, lower=True)
```

- [ ] **Step 4: Replace `simulate_correlated_returns` with the vectorised version**

`X[p, t, :] = L @ Z[p, t, :]` in row-vector form is `X = Z @ L.T`, which numpy broadcasts over the leading two axes as a single BLAS call. Chunking over paths bounds the peak temporary allocation without changing the numbers, because `Z` is drawn once for the whole array before any chunk is processed:

```python
def simulate_correlated_returns(
    means: np.ndarray,
    stds: np.ndarray,
    cholesky_factor: np.ndarray,
    horizon: int,
    num_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate correlated daily log returns.

    Draws independent standard normals Z, applies the Cholesky factor to induce
    the target correlation, then scales and shifts:

        X[p, t, :] = L @ Z[p, t, :]      <=>      X = Z @ L.T
        R          = means + stds * X

    Returns shape (num_paths, horizon, n_assets). Processed in path-chunks so peak
    memory does not scale with num_paths; the result is identical to the unchunked
    computation because Z is drawn once, up front.
    """
    means = np.asarray(means, dtype=float)
    stds = np.asarray(stds, dtype=float)
    n_assets = means.shape[0]

    out = rng.standard_normal((num_paths, horizon, n_assets))

    factor_t = np.ascontiguousarray(cholesky_factor.T)
    chunk = max(1, _MAX_CHUNK_ELEMENTS // max(1, horizon * n_assets))

    for start in range(0, num_paths, chunk):
        stop = min(start + chunk, num_paths)
        block = out[start:stop] @ factor_t
        block *= stds
        block += means
        out[start:stop] = block

    return out
```

- [ ] **Step 5: Update the two call sites in `main.py`**

```python
returns_df, corr_matrix = compute_correlation_matrix(price_data, request.tickers)
```

and

```python
L = cholesky_factor(corr_matrix)
```

Update the import block: `cholesky_decomposition` becomes `cholesky_factor`, and `download_multi_asset_data` is removed.

- [ ] **Step 6: Remove `correlation.py` from the mypy exclude**

In `pyproject.toml`, delete `backend/src/correlation\\.py|` from the `[tool.mypy] exclude` pattern. The rewritten functions are fully annotated; `build_portfolio_paths` and `compute_portfolio_risk_stats` already carry annotations from the original file.

- [ ] **Step 7: Run the tests and the gate**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_correlation.py -v
```

Expected: 12 passed.

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

Expected: all pass.

- [ ] **Step 8: Append the linear-algebra section to `docs/METHODOLOGY.md`**

```markdown
## Correlation estimation and correlated sampling

**Estimator.** Pearson correlation of daily log returns over the requested history
(1–10 years), computed on the inner join of all assets' dates so every asset
contributes the same sessions. A minimum of 30 overlapping observations is required.
Column and row order follows the caller's ticker list, because portfolio weights are
aligned positionally.

**Sampling.** With `L` the lower Cholesky factor of the correlation matrix
`C = L Lt` and `Z` independent standard normals,

    X[p, t, :] = L . Z[p, t, :]        equivalently        X = Z . Lt
    R          = mu + sigma * X

gives `Cov(X) = L Lt = C` by construction. The implementation is a single broadcast
matmul over the leading path and time axes, processed in path-chunks that bound peak
memory. Chunking is a memory parameter only: `Z` is drawn once before any chunk is
processed, so results are bit-identical at any chunk size, and a regression test
asserts that.

**Positive definiteness.** A sample correlation matrix can fail to be positive
semi-definite through missing-data alignment or near-collinear assets, and Cholesky
requires positive definiteness.

- *Detection* uses `numpy.linalg.eigvalsh`, the symmetric routine. The previous code
  used `eigvals`, the general routine, which returns complex eigenvalues for a
  symmetric input; comparing those against a real threshold is not a meaningful test.
- *Repair* uses Higham's (2002) alternating-projections algorithm to find the nearest
  correlation matrix in the Frobenius norm, projecting between the PSD cone and the
  unit-diagonal set with Dykstra's correction. Residual zero eigenvalues are floored
  and the diagonal renormalised to exactly 1.

The previous repair added `1e-6 * I` to the diagonal. That does not restore positive
semi-definiteness: for the standard counter-example `[[1,1,0],[1,1,1],[0,1,1]]` the
smallest eigenvalue is `1 - sqrt(2) ~= -0.414`, and adding `1e-6` leaves it at
`-0.414`. The Cholesky call then raised, or worse, succeeded on a matrix that was not
a correlation matrix. A test asserts both the failure of the old approach and the
published Higham answer for that example.

**Assumption set.** Correlation is constant over the horizon and identical across
paths. This is the central limitation of the Gaussian model and the reason the joint
GMM exists: a single Cholesky factor cannot express correlations that rise toward 1
in a crash.

**What breaks it.** Assets with short or non-overlapping histories (recent listings,
different trading calendars, crypto trading weekends against equities trading
weekdays) shrink the intersection and make the estimate noisy. Correlation estimated
over a calm window understates crisis correlation.
```

- [ ] **Step 9: Commit**

```bash
git add backend/src/correlation.py backend/main.py backend/tests/test_correlation.py pyproject.toml docs/METHODOLOGY.md
git commit -m "fix: eigvalsh + Higham PD projection, vectorised chunked correlated sampler"
```

---

### Task 5: Joint (multivariate) GMM sampling

Implements spec 1.2. Today the portfolio GMM branch sets `means.append(0.0)` (commented "Risk-neutral", which is wrong — risk-neutral drift is the risk-free rate, not zero), takes the empirical standard deviation, and then calls the Gaussian sampler. The fitted GMM object is discarded and the UI toggle changes nothing. The fix is to fit the mixture on the **joint** returns matrix and sample from it directly, which is what captures both fat tails and regime-dependent correlation — a single Cholesky factor cannot express correlations that rise toward 1 in a crash.

**Files:**
- Create: `backend/src/joint_models.py`
- Create: `backend/tests/test_joint_models.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: `rng` fixture from Task 1.
- Produces:
  - `fit_joint_gmm(returns_df: pd.DataFrame, n_components: int = 3, seed: int = 42) -> GaussianMixture`
  - `sample_joint_gmm(gmm: GaussianMixture, horizon: int, num_paths: int, rng: np.random.Generator) -> np.ndarray` shape `(num_paths, horizon, n_assets)`
  - `describe_mixture(gmm: GaussianMixture) -> list[MixtureComponent]`
  - `MixtureComponent` frozen dataclass with fields `weight: float`, `means: list[float]`, `covariance: list[list[float]]`
- Note: this task is a pure addition. `main.py` is not touched until Task 10.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_joint_models.py`. The kurtosis test is the Definition-of-Done item for spec 1.2:

```python
"""Joint GMM: fat tails and regime-dependent correlation a Cholesky factor cannot express."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.joint_models import describe_mixture, fit_joint_gmm, sample_joint_gmm


def _two_regime_returns(
    seed: int = 5,
    n_calm: int = 9000,
    n_crisis: int = 1000,
    calm_sigma: float = 0.005,
    crisis_sigma: float = 0.040,
    calm_corr: float = 0.20,
    crisis_corr: float = 0.90,
) -> pd.DataFrame:
    """A calm regime and a crisis regime: low vol / low correlation, high vol / high correlation."""
    gen = np.random.default_rng(seed)

    def block(n: int, sigma: float, corr: float) -> np.ndarray:
        c = np.array([[1.0, corr], [corr, 1.0]])
        return gen.standard_normal((n, 2)) @ np.linalg.cholesky(c).T * sigma

    joint = np.vstack([block(n_calm, calm_sigma, calm_corr), block(n_crisis, crisis_sigma, crisis_corr)])
    index = pd.bdate_range("2000-01-03", periods=len(joint), name="date")
    return pd.DataFrame(joint, columns=["A", "B"], index=index)


def test_sampled_returns_have_materially_positive_excess_kurtosis() -> None:
    """Definition of done for spec 1.2: GMM output must be demonstrably non-Gaussian.

    For a zero-mean two-component scale mixture the analytic excess kurtosis is
        3 * (w1*s1^4 + w2*s2^4) / (w1*s1^2 + w2*s2^2)^2 - 3
    which for w=(0.9, 0.1), s=(0.005, 0.040) is about 20.1.
    """
    returns = _two_regime_returns()
    gmm = fit_joint_gmm(returns, n_components=2)
    draws = sample_joint_gmm(gmm, 200, 400, np.random.default_rng(8))

    excess = stats.kurtosis(draws[:, :, 0].ravel(), fisher=True)
    assert excess > 5.0, f"excess kurtosis {excess:.2f} is not materially non-Gaussian"


def test_a_gaussian_sample_has_near_zero_excess_kurtosis_for_contrast() -> None:
    """Control: the same statistic on Gaussian draws, so the test above means something."""
    draws = np.random.default_rng(8).standard_normal(400 * 200)
    assert abs(stats.kurtosis(draws, fisher=True)) < 0.15


def test_correlation_is_regime_dependent() -> None:
    """The property a single Cholesky factor structurally cannot reproduce.

    Correlation conditional on the crisis regime must exceed unconditional
    correlation, because the high-vol component carries the higher correlation.
    """
    returns = _two_regime_returns()
    gmm = fit_joint_gmm(returns, n_components=2)
    draws = sample_joint_gmm(gmm, 200, 400, np.random.default_rng(12)).reshape(-1, 2)

    unconditional = np.corrcoef(draws, rowvar=False)[0, 1]
    magnitude = np.abs(draws).sum(axis=1)
    crisis = draws[magnitude >= np.quantile(magnitude, 0.95)]
    conditional = np.corrcoef(crisis, rowvar=False)[0, 1]

    assert conditional > unconditional + 0.10


def test_sampled_variance_matches_the_analytic_mixture_variance() -> None:
    """Closed form: Var = sum_k w_k * (Sigma_k + mu_k mu_k') - (sum_k w_k mu_k)^2."""
    returns = _two_regime_returns()
    gmm = fit_joint_gmm(returns, n_components=2)
    draws = sample_joint_gmm(gmm, 300, 300, np.random.default_rng(15)).reshape(-1, 2)

    weights = gmm.weights_
    means = gmm.means_
    covs = gmm.covariances_
    mixture_mean = np.einsum("k,ki->i", weights, means)
    second = np.einsum("k,kij->ij", weights, covs) + np.einsum("k,ki,kj->ij", weights, means, means)
    analytic_cov = second - np.outer(mixture_mean, mixture_mean)

    np.testing.assert_allclose(np.cov(draws, rowvar=False), analytic_cov, rtol=0.05, atol=1e-7)


def test_sampling_is_a_pure_function_of_its_generator() -> None:
    returns = _two_regime_returns(n_calm=900, n_crisis=100)
    gmm = fit_joint_gmm(returns, n_components=2)
    first = sample_joint_gmm(gmm, 20, 50, np.random.default_rng(3))
    second = sample_joint_gmm(gmm, 20, 50, np.random.default_rng(3))
    np.testing.assert_array_equal(first, second)


def test_sampling_ignores_global_numpy_state() -> None:
    """GaussianMixture.sample() would fail this; the hand-rolled sampler must not."""
    returns = _two_regime_returns(n_calm=900, n_crisis=100)
    gmm = fit_joint_gmm(returns, n_components=2)

    np.random.seed(1)
    first = sample_joint_gmm(gmm, 20, 50, np.random.default_rng(3))
    np.random.seed(2)
    second = sample_joint_gmm(gmm, 20, 50, np.random.default_rng(3))
    np.testing.assert_array_equal(first, second)


def test_output_shape_and_asset_ordering() -> None:
    returns = _two_regime_returns(n_calm=900, n_crisis=100)
    gmm = fit_joint_gmm(returns, n_components=2)
    draws = sample_joint_gmm(gmm, 30, 40, np.random.default_rng(1))
    assert draws.shape == (40, 30, 2)


def test_fit_is_deterministic_for_a_given_seed() -> None:
    returns = _two_regime_returns(n_calm=900, n_crisis=100)
    a = fit_joint_gmm(returns, n_components=2, seed=17)
    b = fit_joint_gmm(returns, n_components=2, seed=17)
    np.testing.assert_allclose(np.sort(a.weights_), np.sort(b.weights_))


def test_fit_rejects_too_few_observations() -> None:
    returns = _two_regime_returns(n_calm=40, n_crisis=5)
    with pytest.raises(ValueError, match="at least"):
        fit_joint_gmm(returns, n_components=3)


def test_describe_mixture_reports_inspectable_regimes() -> None:
    """Spec 1.2 requires the fitted regimes to be visible in the API response."""
    returns = _two_regime_returns()
    gmm = fit_joint_gmm(returns, n_components=2)
    described = describe_mixture(gmm)

    assert len(described) == 2
    assert sum(c.weight for c in described) == pytest.approx(1.0)
    for component in described:
        assert len(component.means) == 2
        assert np.array(component.covariance).shape == (2, 2)

    # The higher-variance component must be the lower-weight one for this fixture.
    by_variance = sorted(described, key=lambda c: c.covariance[0][0])
    assert by_variance[-1].weight < by_variance[0].weight
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_joint_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.joint_models'`, except `test_a_gaussian_sample_has_near_zero_excess_kurtosis_for_contrast`, which passes.

- [ ] **Step 3: Write `backend/src/joint_models.py`**

```python
"""Joint (multivariate) return models for portfolio simulation.

A Gaussian copula built from one Cholesky factor holds correlation fixed across all
market states. A joint Gaussian mixture instead fits several full covariance
matrices and mixes them, so the simulated data can carry both fat tails and
correlations that differ by regime — correlations rising toward 1 in a crash is the
behaviour that matters and the behaviour a single factor cannot express.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

# sklearn's default reg_covar (1e-6) is ~1% of daily return variance (~1.4e-4).
# At this scale it distorts the estimate rather than stabilising it.
REG_COVAR = 1e-12

# Minimum observations per fitted component.
MIN_OBSERVATIONS_PER_COMPONENT = 30


@dataclass(frozen=True)
class MixtureComponent:
    """One fitted regime, in a shape the API can serialise directly."""

    weight: float
    means: list[float]
    covariance: list[list[float]]


def fit_joint_gmm(
    returns_df: pd.DataFrame,
    n_components: int = 3,
    seed: int = 42,
) -> GaussianMixture:
    """Fit a full-covariance Gaussian mixture to the joint daily log-return matrix.

    `returns_df` is (n_observations, n_assets) with columns ordered to match the
    caller's weight vector.
    """
    X = returns_df.to_numpy(dtype=float)
    required = MIN_OBSERVATIONS_PER_COMPONENT * n_components
    if X.shape[0] < required:
        raise ValueError(
            f"Need at least {required} observations to fit a {n_components}-component "
            f"joint GMM, got {X.shape[0]}"
        )

    gmm = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        random_state=seed,
        n_init=5,
        reg_covar=REG_COVAR,
    )
    gmm.fit(X)
    return gmm


def sample_joint_gmm(
    gmm: GaussianMixture,
    horizon: int,
    num_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw (num_paths, horizon, n_assets) daily log returns from the joint mixture.

    `GaussianMixture.sample()` draws from global numpy state and returns its output
    grouped by component, so both component selection and the conditional normals
    are sampled here with the caller's Generator.
    """
    weights = np.asarray(gmm.weights_, dtype=float)
    means = np.asarray(gmm.means_, dtype=float)
    covariances = np.asarray(gmm.covariances_, dtype=float)
    n_assets = means.shape[1]
    n_draws = num_paths * horizon

    components = rng.choice(len(weights), size=n_draws, p=weights)
    out = np.empty((n_draws, n_assets), dtype=float)

    for k in range(len(weights)):
        mask = components == k
        count = int(mask.sum())
        if count:
            out[mask] = rng.multivariate_normal(means[k], covariances[k], size=count)

    return out.reshape(num_paths, horizon, n_assets)


def describe_mixture(gmm: GaussianMixture) -> list[MixtureComponent]:
    """Expose the fitted regimes so the API response is inspectable (spec 1.2)."""
    return [
        MixtureComponent(
            weight=float(weight),
            means=[float(x) for x in mean],
            covariance=[[float(x) for x in row] for row in covariance],
        )
        for weight, mean, covariance in zip(
            gmm.weights_, gmm.means_, gmm.covariances_, strict=True
        )
    ]
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_joint_models.py -v
```

Expected: 11 passed. If `test_correlation_is_regime_dependent` fails marginally, do **not** loosen the threshold — check that `covariance_type="full"` is set and that `n_init=5` is finding the two-regime optimum rather than a local one.

- [ ] **Step 5: Run the gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

- [ ] **Step 6: Append the joint-model section to `docs/METHODOLOGY.md`**

```markdown
## Joint return models

### What was wrong

The portfolio endpoint accepted a `model: "gmm"` flag, fitted nothing joint, set
each asset's drift to `0.0` with the comment "Risk-neutral", took each asset's
empirical standard deviation, and then sampled from the **Gaussian** correlated
sampler. The fitted mixture object was discarded. Selecting GMM in the UI changed
no number in the response.

Two errors compounded: the toggle was decorative, and the drift substitution was
wrong on its own terms. Risk-neutral drift is the risk-free rate, not zero. Setting
drift to zero is not a risk-neutral measure; it is an assumption that every asset
returns nothing.

### Joint Gaussian mixture (`correlation_model: "gmm_joint"`)

A `K`-component full-covariance mixture is fitted to the joint daily log-return
matrix (`n_observations x n_assets`) by expectation-maximisation:

    f(r) = sum_k  w_k * N(r; mu_k, Sigma_k),    sum_k w_k = 1

Sampling draws a component index from `w`, then a multivariate normal from that
component. Because each component carries its own **full** covariance matrix, the
model reproduces two things the Gaussian model structurally cannot:

1. **Fat tails.** A scale mixture of normals has positive excess kurtosis. For a
   zero-mean two-component mixture with weights `(0.9, 0.1)` and standard deviations
   `(0.005, 0.040)`, analytic excess kurtosis is about 20.1 against 0 for a normal.
2. **Regime-dependent correlation.** Component 1 can hold correlation 0.2 and
   component 2 correlation 0.9. A Gaussian copula with one Cholesky factor holds
   correlation fixed in every state of the world, which understates exactly the
   scenario that matters: diversification failing when it is needed.

Tests assert both properties directly, with a Gaussian control sample for contrast.

**Estimation window.** The full requested history (1–10 years of daily joint
returns), inner-joined across assets.

**Assumption set.** `K = 3` by default, configurable from 2 to 6. Returns are
independent across days — the mixture captures unconditional fat tails and
state-dependent correlation, but not volatility clustering, because component
membership is drawn independently each day. `reg_covar = 1e-12` rather than
sklearn's `1e-6` default, which at daily-return scale (variance ~1.4e-4) would be a
material fraction of the quantity being estimated. Fitting uses `n_init=5` to reduce
the chance of an EM local optimum.

**Reproducibility.** `GaussianMixture.sample()` draws from global numpy state, so
`sample_joint_gmm` performs component selection and the conditional draws itself
using the request's Generator. The fit is made deterministic through
`random_state=seed`.

**What breaks it.** Too few observations for `K` components (the fit requires at
least 30 per component and raises otherwise); a regime present in the future but
absent from the estimation window; and `K` chosen large enough to fit noise. EM can
converge to a local optimum, so weights and covariances are reported in the API
response rather than hidden — an implausible fit should be visible, not silent.

### Copula layer (`correlation_model: "t_copula"`) — interface only

Declared in the request model and rejected with HTTP 501. Fitting marginals
separately (Student-t or empirical) and coupling them with a t-copula separates tail
dependence from marginal shape, which is the more flexible construction. It is out
of scope for Phase 1 and is deliberately not stubbed with a silent fallback: a model
that claims to be a t-copula and is not is precisely the defect this section
documents.
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/joint_models.py backend/tests/test_joint_models.py docs/METHODOLOGY.md
git commit -m "feat: joint multivariate GMM sampling with regime-dependent correlation"
```

---

### Task 6: Portfolio construction from simple returns with explicit rebalancing

Implements spec 1.4. `build_portfolio_paths` computes `np.sum(weights * returns_matrix[path, t, :])` on **log** returns and then exponentiates. Log returns are additive across time, not across assets: by the concavity of the logarithm this understates the portfolio return by the diversification (Jensen) term on every single day. The rebalancing assumption is also silent — the old code is implicitly daily-rebalanced, the most return-flattering assumption available.

**Files:**
- Create: `backend/src/portfolio_math.py`
- Create: `backend/tests/test_portfolio_math.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure numpy).
- Produces:
  - `RebalanceRule = Literal["daily", "monthly", "quarterly", "annual", "buy_and_hold"]`
  - `asset_price_paths(start_prices: np.ndarray, log_returns: np.ndarray) -> np.ndarray` shape `(num_paths, horizon, n_assets)`
  - `build_portfolio_paths(start_prices, log_returns, weights, rebalance="buy_and_hold", rebalance_band=None, transaction_cost_bps=0.0) -> tuple[np.ndarray, np.ndarray]` returning `(asset_paths, portfolio_paths)`; `portfolio_paths` has shape `(num_paths, horizon)` and `portfolio_paths[p, t]` is the value of an initially-1.0 portfolio after `t+1` days
  - `REBALANCE_PERIOD_DAYS: dict[str, int]`
- Note: pure addition. The old `build_portfolio_paths` in `correlation.py` remains until Task 10 deletes it.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_portfolio_math.py`. The first test is the closed-form demonstration of the defect:

```python
"""Portfolio aggregation in simple-return space, under explicit rebalancing rules."""

from __future__ import annotations

import numpy as np
import pytest

from src.portfolio_math import asset_price_paths, build_portfolio_paths


def _log_returns(simple: list[list[list[float]]]) -> np.ndarray:
    """Build a (paths, horizon, assets) log-return array from simple returns."""
    return np.log1p(np.array(simple, dtype=float))


def test_log_space_aggregation_understates_return_closed_form() -> None:
    """The defect, with an exactly computable answer.

    Two assets, equal weights, one day: +10% and -10%.
      Correct (simple space):  0.5*0.10 + 0.5*(-0.10) = 0.0  -> value 1.0
      Old (log space): 0.5*ln(1.1) + 0.5*ln(0.9) = -0.0050252 -> value 0.994975
    The old method reports -0.50% for a portfolio that in fact returned 0.00%.
    """
    log_rets = _log_returns([[[0.10, -0.10]]])
    weights = np.array([0.5, 0.5])
    start_prices = np.array([100.0, 100.0])

    _, portfolio = build_portfolio_paths(start_prices, log_rets, weights, rebalance="daily")
    assert portfolio[0, -1] == pytest.approx(1.0, abs=1e-15)

    old_method = float(np.exp((log_rets[0, 0] * weights).sum()))
    assert old_method == pytest.approx(0.99497475, abs=1e-8)
    assert portfolio[0, -1] > old_method


def test_single_asset_portfolio_equals_its_own_price_path() -> None:
    """A one-asset portfolio must track the asset exactly, under any rule."""
    log_rets = _log_returns([[[0.02], [-0.01], [0.005]]])
    start_prices = np.array([50.0])
    weights = np.array([1.0])

    for rule in ("buy_and_hold", "daily", "monthly"):
        asset_paths, portfolio = build_portfolio_paths(
            start_prices, log_rets, weights, rebalance=rule
        )
        np.testing.assert_allclose(
            portfolio[0], asset_paths[0, :, 0] / start_prices[0], atol=1e-14
        )


def test_asset_price_paths_compound_log_returns() -> None:
    log_rets = _log_returns([[[0.10], [0.10]]])
    paths = asset_price_paths(np.array([100.0]), log_rets)
    np.testing.assert_allclose(paths[0, :, 0], [110.0, 121.0], atol=1e-10)


def test_daily_closed_form_matches_the_stepwise_loop() -> None:
    """The vectorised daily branch and the general loop must agree exactly."""
    gen = np.random.default_rng(4)
    log_rets = gen.normal(0.0003, 0.012, size=(60, 40, 3))
    weights = np.array([0.5, 0.3, 0.2])
    start_prices = np.array([100.0, 50.0, 20.0])

    _, closed_form = build_portfolio_paths(
        start_prices, log_rets, weights, rebalance="daily"
    )
    _, stepwise = build_portfolio_paths(
        start_prices, log_rets, weights, rebalance="daily", transaction_cost_bps=0.0,
        rebalance_band=0.0,
    )
    np.testing.assert_allclose(closed_form, stepwise, atol=1e-12)


def test_an_unreachable_band_reduces_periodic_rebalancing_to_buy_and_hold() -> None:
    """With a band no drift can breach, the periodic path must equal buy-and-hold."""
    gen = np.random.default_rng(6)
    log_rets = gen.normal(0.0005, 0.015, size=(40, 30, 3))
    weights = np.array([0.4, 0.4, 0.2])
    start_prices = np.array([100.0, 80.0, 10.0])

    _, hold = build_portfolio_paths(start_prices, log_rets, weights, rebalance="buy_and_hold")
    _, banded = build_portfolio_paths(
        start_prices, log_rets, weights, rebalance="monthly", rebalance_band=10.0
    )
    np.testing.assert_allclose(hold, banded, atol=1e-12)


def test_buy_and_hold_lets_weights_drift_with_performance() -> None:
    """Units held are fixed, so the winner's weight must grow (spec 1.4)."""
    log_rets = _log_returns([[[0.50, 0.00]]])
    weights = np.array([0.5, 0.5])
    start_prices = np.array([100.0, 100.0])

    asset_paths, portfolio = build_portfolio_paths(
        start_prices, log_rets, weights, rebalance="buy_and_hold"
    )
    units = weights / start_prices
    terminal_values = units * asset_paths[0, -1, :]
    drifted = terminal_values / terminal_values.sum()

    assert drifted[0] == pytest.approx(1.5 / 2.5)
    assert portfolio[0, -1] == pytest.approx(1.25)


def test_daily_rebalancing_beats_buy_and_hold_on_a_mean_reverting_pair() -> None:
    """The rebalancing premium, on a deterministic zig-zag. Documents the bias."""
    pattern = [[[0.10, -0.10]], [[-0.10, 0.10]]] * 20
    log_rets = _log_returns([[row[0] for row in pattern]])
    weights = np.array([0.5, 0.5])
    start_prices = np.array([100.0, 100.0])

    _, rebalanced = build_portfolio_paths(start_prices, log_rets, weights, rebalance="daily")
    _, hold = build_portfolio_paths(start_prices, log_rets, weights, rebalance="buy_and_hold")
    assert rebalanced[0, -1] > hold[0, -1]


def test_transaction_cost_is_charged_on_traded_notional() -> None:
    """Closed form for one rebalance.

    Day 1: asset A +10%, asset B 0%. From 50/50, drifted weights are
    1.10/2.10 and 1.00/2.10. Total traded notional is
    sum|w_drift - w_target| = 2 * (1.10/2.10 - 0.5) = 0.0476190.
    At 100 bps the cost is 0.0476190 * 0.01 = 0.000476190 of portfolio value.
    """
    log_rets = _log_returns([[[0.10, 0.00]]])
    weights = np.array([0.5, 0.5])
    start_prices = np.array([100.0, 100.0])

    _, free = build_portfolio_paths(start_prices, log_rets, weights, rebalance="daily")
    _, charged = build_portfolio_paths(
        start_prices, log_rets, weights, rebalance="daily", transaction_cost_bps=100.0
    )

    turnover = 2.0 * (1.10 / 2.10 - 0.5)
    assert charged[0, -1] == pytest.approx(free[0, -1] * (1.0 - turnover * 0.01), abs=1e-12)


def test_zero_cost_and_no_band_leave_the_path_unchanged() -> None:
    gen = np.random.default_rng(9)
    log_rets = gen.normal(0.0, 0.01, size=(20, 15, 2))
    weights = np.array([0.6, 0.4])
    start_prices = np.array([10.0, 20.0])

    _, a = build_portfolio_paths(start_prices, log_rets, weights, rebalance="quarterly")
    _, b = build_portfolio_paths(
        start_prices, log_rets, weights, rebalance="quarterly", transaction_cost_bps=0.0
    )
    np.testing.assert_allclose(a, b, atol=1e-15)


def test_periodic_rules_rebalance_on_the_documented_cadence() -> None:
    """Monthly = every 21 trading days. A 25-day horizon rebalances exactly once."""
    from src.portfolio_math import REBALANCE_PERIOD_DAYS

    assert REBALANCE_PERIOD_DAYS == {"daily": 1, "monthly": 21, "quarterly": 63, "annual": 252}

    gen = np.random.default_rng(2)
    log_rets = gen.normal(0.001, 0.02, size=(5, 25, 2))
    weights = np.array([0.5, 0.5])
    start_prices = np.array([100.0, 100.0])

    _, monthly = build_portfolio_paths(start_prices, log_rets, weights, rebalance="monthly")
    _, hold = build_portfolio_paths(start_prices, log_rets, weights, rebalance="buy_and_hold")

    # Identical up to and including the rebalance day, divergent after it.
    np.testing.assert_allclose(monthly[:, :21], hold[:, :21], atol=1e-12)
    assert not np.allclose(monthly[:, -1], hold[:, -1])


def test_weights_must_sum_to_one() -> None:
    log_rets = _log_returns([[[0.01, 0.01]]])
    with pytest.raises(ValueError, match="sum to 1"):
        build_portfolio_paths(np.array([1.0, 1.0]), log_rets, np.array([0.5, 0.4]))


def test_negative_weights_are_rejected() -> None:
    """Short positions can drive portfolio value through zero; out of scope for Phase 1."""
    log_rets = _log_returns([[[0.01, 0.01]]])
    with pytest.raises(ValueError, match="non-negative"):
        build_portfolio_paths(np.array([1.0, 1.0]), log_rets, np.array([1.4, -0.4]))


def test_output_shapes() -> None:
    gen = np.random.default_rng(1)
    log_rets = gen.normal(0.0, 0.01, size=(7, 11, 3))
    asset_paths, portfolio = build_portfolio_paths(
        np.array([1.0, 2.0, 3.0]), log_rets, np.array([0.2, 0.3, 0.5])
    )
    assert asset_paths.shape == (7, 11, 3)
    assert portfolio.shape == (7, 11)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_portfolio_math.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.portfolio_math'`.

- [ ] **Step 3: Write `backend/src/portfolio_math.py`**

```python
"""Portfolio path construction under explicit rebalancing rules.

Asset paths compound log returns, because log returns are additive across time.
Portfolio aggregation uses simple returns, because log returns are *not* additive
across assets: ln(1 + sum_i w_i s_i) != sum_i w_i ln(1 + s_i), and by the concavity
of the logarithm the right-hand side is strictly smaller whenever asset returns
differ. Aggregating in log space therefore understates the portfolio return by the
diversification (Jensen) term.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

RebalanceRule = Literal["daily", "monthly", "quarterly", "annual", "buy_and_hold"]

# Trading days per rebalancing interval.
REBALANCE_PERIOD_DAYS: dict[str, int] = {
    "daily": 1,
    "monthly": 21,
    "quarterly": 63,
    "annual": 252,
}


def asset_price_paths(start_prices: np.ndarray, log_returns: np.ndarray) -> np.ndarray:
    """Compound log returns into price paths.

    `log_returns` is (num_paths, horizon, n_assets); the result has the same shape.
    Computed with in-place cumsum and exp so peak memory is one array, not three.
    """
    paths = np.cumsum(log_returns, axis=1)
    np.exp(paths, out=paths)
    paths *= np.asarray(start_prices, dtype=float)
    return paths


def build_portfolio_paths(
    start_prices: np.ndarray,
    log_returns: np.ndarray,
    weights: np.ndarray,
    rebalance: RebalanceRule = "buy_and_hold",
    rebalance_band: float | None = None,
    transaction_cost_bps: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build asset price paths and the portfolio value path.

    Returns `(asset_paths, portfolio_paths)`. `portfolio_paths[p, t]` is the value of
    an initially-1.0 portfolio after `t + 1` days; the initial 1.0 is implicit, so the
    terminal return is `portfolio_paths[:, -1] - 1.0`.

    Parameters
    ----------
    rebalance
        `"buy_and_hold"` fixes the number of units held and lets weights drift with
        performance. The periodic rules restore target weights every 1 / 21 / 63 / 252
        trading days.
    rebalance_band
        If set, a rebalance is skipped unless some weight has drifted more than this
        (absolute) amount from its target. Applies per path.
    transaction_cost_bps
        Charged on traded notional at each rebalance, where traded notional is
        `sum_i |w_drifted,i - w_target,i|` as a fraction of portfolio value. Buys equal
        sells, so this counts both legs.
    """
    weights = np.asarray(weights, dtype=float)
    start_prices = np.asarray(start_prices, dtype=float)

    if not np.isclose(weights.sum(), 1.0):
        raise ValueError(f"Weights must sum to 1, got {weights.sum()}")
    if np.any(weights < 0.0):
        raise ValueError(
            "Weights must be non-negative: short positions can drive portfolio value "
            "through zero and are out of scope"
        )

    asset_paths = asset_price_paths(start_prices, log_returns)
    cost_rate = transaction_cost_bps / 1e4

    if rebalance == "buy_and_hold":
        # Units are fixed; weights drift. This is the honest default.
        units = weights / start_prices
        portfolio_paths = asset_paths @ units
    elif rebalance == "daily" and rebalance_band is None and cost_rate == 0.0:
        # Closed form: with no band and no cost, daily rebalancing is a plain
        # weighted average of simple returns, compounded.
        portfolio_paths = np.cumprod(1.0 + np.expm1(log_returns) @ weights, axis=1)
    else:
        portfolio_paths = _stepwise_rebalanced_paths(
            np.expm1(log_returns),
            weights,
            REBALANCE_PERIOD_DAYS[rebalance],
            rebalance_band,
            cost_rate,
        )

    return asset_paths, portfolio_paths


def _stepwise_rebalanced_paths(
    simple_returns: np.ndarray,
    target_weights: np.ndarray,
    period_days: int,
    band: float | None,
    cost_rate: float,
) -> np.ndarray:
    """Walk the horizon, letting weights drift and restoring them on schedule.

    Loops over time (at most 1000 steps) with every operation vectorised across paths.
    """
    num_paths, horizon, _ = simple_returns.shape
    growth = 1.0 + simple_returns

    value = np.ones(num_paths, dtype=float)
    current = np.tile(target_weights, (num_paths, 1))
    portfolio_paths = np.empty((num_paths, horizon), dtype=float)

    for t in range(horizon):
        current = current * growth[:, t, :]
        gross = current.sum(axis=1)
        value = value * gross
        current = current / gross[:, None]

        if (t + 1) % period_days == 0:
            drift = np.abs(current - target_weights)
            due = np.ones(num_paths, dtype=bool) if band is None else drift.max(axis=1) > band
            # Traded notional counts both legs, since buys equal sells.
            traded_notional = np.where(due, drift.sum(axis=1), 0.0)
            value = value * (1.0 - cost_rate * traded_notional)
            current = np.where(due[:, None], target_weights, current)

        portfolio_paths[:, t] = value

    return portfolio_paths
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_portfolio_math.py -v
```

Expected: 13 passed. `test_daily_closed_form_matches_the_stepwise_loop` passes `rebalance_band=0.0`, which is falsy but not `None` — confirm the branch condition tests `is None`, not truthiness, or that test will silently exercise the closed form twice and prove nothing.

- [ ] **Step 5: Run the gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

- [ ] **Step 6: Append the portfolio-construction section to `docs/METHODOLOGY.md`**

```markdown
## Portfolio construction

### What was wrong

`build_portfolio_paths` computed the portfolio return as a weighted sum of **log**
returns and then exponentiated:

    portfolio_return[p, t] = sum_i w_i * r_i[p, t]        # r = log return
    portfolio_value        = exp(cumsum(portfolio_return))

Log returns are additive across **time**, not across **assets**. The correct
aggregation is in simple-return space, and Jensen's inequality gives the size and
the sign of the error:

    ln(1 + sum_i w_i s_i)  >=  sum_i w_i ln(1 + s_i)

with strict inequality whenever asset returns differ. The old method therefore
understated the portfolio return by the diversification term every day, and the
shortfall compounded.

Worked example — two assets, equal weights, one day at +10% and -10%:

| Method | Computation | Reported return |
|---|---|---|
| Correct (simple space) | `0.5(0.10) + 0.5(-0.10) = 0.0` | **0.00%** |
| Old (log space) | `0.5 ln(1.1) + 0.5 ln(0.9) = -0.005025` | **-0.50%** |

A test asserts both numbers.

### Correct aggregation

    s          = expm1(r)                    # asset simple returns
    port_s     = s @ w                       # portfolio simple return
    port_value = cumprod(1 + port_s)         # value path, initial 1.0 implicit

### Rebalancing is now a declared parameter

The old implementation was implicitly daily-rebalanced without saying so, which is
the most return-flattering assumption available. `rebalance` is now explicit:

| Rule | Interval | Mechanics |
|---|---|---|
| `buy_and_hold` (**default**) | never | Units held are fixed; weights drift with performance |
| `daily` | 1 trading day | Target weights restored every day |
| `monthly` | 21 trading days | |
| `quarterly` | 63 trading days | |
| `annual` | 252 trading days | |

**Daily rebalancing is a flattered assumption.** Restoring target weights daily
harvests a rebalancing premium — mechanically selling winners and buying losers —
that a real portfolio does not earn for free, because it ignores transaction costs,
bid-ask spreads, and tax. A test on a deterministic mean-reverting pair shows the
daily-rebalanced path finishing ahead of buy-and-hold. **Buy-and-hold is the honest
default for a retail-scale portfolio** and is therefore the default here.

`buy_and_hold` tracks units, not weights: `units = w / p_0`, then
`portfolio_value = asset_paths @ units`. Weights drift with performance, so a winner's
weight grows exactly as it would in a real unmanaged account.

**Threshold rebalancing.** `rebalance_band` skips a scheduled rebalance unless some
weight has drifted more than the band from target, evaluated per path. With a band no
drift can breach, the periodic rules reduce exactly to buy-and-hold; a test asserts
that identity to 1e-12.

**Transaction costs.** `transaction_cost_bps` is charged on traded notional at each
rebalance, where traded notional is `sum_i |w_drifted,i - w_target,i|` expressed as a
fraction of portfolio value. Buys equal sells, so this figure counts both legs and
needs no factor-of-two convention. Cost is applied to portfolio value at the
rebalance instant.

**Implementation.** `buy_and_hold` and cost-free, band-free `daily` have closed forms
and are computed as single vectorised expressions. The general case walks the horizon
(at most 1000 steps) with all operations vectorised across paths. A test asserts the
closed form and the stepwise loop agree to 1e-12.

**Assumption set.** Rebalancing is frictionless apart from the stated bps, executes at
the close, and is exact. Long-only: negative weights are rejected, because a short
position can drive portfolio value through zero and the divide-by-gross step is then
undefined.

**What breaks it.** Real portfolios rebalance on cash flows and tax lots, not
calendars. The 21/63/252-day intervals are trading-day approximations to calendar
months, quarters, and years, and drift against real calendars over long horizons.
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/portfolio_math.py backend/tests/test_portfolio_math.py docs/METHODOLOGY.md
git commit -m "feat: portfolio aggregation in simple-return space with explicit rebalancing rules"
```

---

### Task 7: Risk metrics — percentiles, annualisation, Sharpe/Sortino/Calmar, VaR/CVaR

Implements spec 1.1 (server-side percentiles), 1.5 (Sharpe is wrong twice), and 1.7 (VaR is ambiguous). The current Sharpe divides a 365-day cumulative return by an annualised volatility and subtracts no risk-free rate — two errors in one expression. VaR is a bare percentage with no stated horizon and an inconsistent sign.

**Files:**
- Create: `backend/src/risk_metrics.py`
- Create: `backend/tests/test_risk_metrics.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure numpy).
- Produces:
  - `TRADING_DAYS_PER_YEAR: int = 252`, `PERCENTILE_LEVELS: tuple[int, ...] = (1, 5, 10, 25, 50, 75, 90, 95, 99)`
  - `percentiles(values: np.ndarray, levels=PERCENTILE_LEVELS) -> dict[str, float]` keyed `"p1"`…`"p99"`
  - `annualized_return(total_return: float, horizon_days: int) -> float`
  - `sharpe_ratio(total_return: float, horizon_days: int, annualized_vol: float, risk_free_rate: float) -> float`
  - `sortino_ratio(total_return: float, horizon_days: int, daily_returns: np.ndarray, risk_free_rate: float) -> float`
  - `calmar_ratio(total_return: float, horizon_days: int, max_drawdown_value: float) -> float`
  - `max_drawdown(paths: np.ndarray, initial_value: float = 1.0) -> np.ndarray` (per-path, positive fraction)
  - `daily_returns_from_paths(paths: np.ndarray, initial_value: float = 1.0) -> np.ndarray`
  - `horizon_returns(paths: np.ndarray, k: int, initial_value: float = 1.0) -> np.ndarray` (non-overlapping)
  - `tail_risk(returns, confidence, horizon_days, portfolio_value) -> TailRisk`
  - `TailRisk` frozen dataclass: `confidence, horizon_days, var_pct, cvar_pct, var_currency, cvar_currency, cvar_var_ratio, convention`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_risk_metrics.py`:

```python
"""Risk metrics, each against a closed-form or analytically known answer."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from src.risk_metrics import (
    PERCENTILE_LEVELS,
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    calmar_ratio,
    daily_returns_from_paths,
    horizon_returns,
    max_drawdown,
    percentiles,
    sharpe_ratio,
    sortino_ratio,
    tail_risk,
)


def test_percentiles_of_a_uniform_grid_are_exact() -> None:
    """On 0..100 the pth percentile is exactly p."""
    result = percentiles(np.arange(101, dtype=float))
    for level in PERCENTILE_LEVELS:
        assert result[f"p{level}"] == pytest.approx(float(level), abs=1e-12)


def test_percentiles_returns_every_required_level() -> None:
    """Spec 1.1 names these nine levels."""
    result = percentiles(np.linspace(0.0, 1.0, 500))
    assert set(result) == {f"p{level}" for level in (1, 5, 10, 25, 50, 75, 90, 95, 99)}


def test_percentiles_are_computed_from_the_full_sample() -> None:
    """Spec 1.1: the defect was deriving the ladder from a 30-path chart sample.

    A 1000-path sample and its first-30 truncation must disagree materially, which
    is the whole reason the computation moved server-side.
    """
    full = np.concatenate([np.full(30, 0.05), np.linspace(-0.9, 2.0, 970)])
    assert percentiles(full)["p99"] != pytest.approx(percentiles(full[:30])["p99"], abs=1e-6)


def test_annualized_return_is_the_inverse_of_compounding() -> None:
    """10% over 126 days (half a year) annualises to 1.1^2 - 1 = 21%."""
    assert annualized_return(0.10, 126) == pytest.approx(1.1**2 - 1.0, abs=1e-12)


def test_annualized_return_is_the_identity_at_one_year() -> None:
    assert annualized_return(0.17, TRADING_DAYS_PER_YEAR) == pytest.approx(0.17, abs=1e-12)


def test_annualized_return_rejects_a_non_positive_horizon() -> None:
    with pytest.raises(ValueError, match="positive"):
        annualized_return(0.1, 0)


def test_sharpe_is_exactly_zero_when_the_return_equals_the_risk_free_rate() -> None:
    """Definition of done for spec 1.5."""
    rf, horizon = 0.045, 365
    total_return = (1.0 + rf) ** (horizon / TRADING_DAYS_PER_YEAR) - 1.0
    result = sharpe_ratio(total_return, horizon, annualized_vol=0.18, risk_free_rate=rf)
    assert result == pytest.approx(0.0, abs=1e-12)


def test_sharpe_matches_a_hand_computed_case() -> None:
    """20% over 252 days, rf 5%, vol 30% -> (0.20 - 0.05) / 0.30 = 0.5."""
    assert sharpe_ratio(0.20, 252, 0.30, 0.05) == pytest.approx(0.5, abs=1e-12)


def test_sharpe_subtracts_the_risk_free_rate() -> None:
    """The old formula omitted rf entirely; raising rf must lower Sharpe."""
    high_rf = sharpe_ratio(0.20, 252, 0.30, 0.10)
    low_rf = sharpe_ratio(0.20, 252, 0.30, 0.02)
    assert low_rf > high_rf
    assert high_rf == pytest.approx((0.20 - 0.10) / 0.30, abs=1e-12)


def test_sharpe_matches_horizons_before_dividing() -> None:
    """The old code divided a 365-day cumulative return by an annualised vol.

    A 365-day return of 20% is an annualised 13.36%, so the old expression
    overstated Sharpe by the ratio of the two.
    """
    horizon = 365
    correct = sharpe_ratio(0.20, horizon, 0.30, 0.0)
    old_and_wrong = 0.20 / 0.30
    assert correct == pytest.approx(((1.20) ** (252 / 365) - 1.0) / 0.30, abs=1e-12)
    assert correct < old_and_wrong


def test_sharpe_is_zero_when_volatility_is_zero() -> None:
    assert sharpe_ratio(0.10, 252, 0.0, 0.04) == 0.0


def test_sortino_penalises_only_downside_deviation() -> None:
    """Two series, same mean, same total vol; the one with upside-only dispersion
    must score higher because its downside deviation is smaller."""
    upside_heavy = np.concatenate([np.full(200, 0.02), np.full(200, -0.001)])
    symmetric = np.concatenate([np.full(200, 0.012), np.full(200, -0.011)])
    total = 0.15
    a = sortino_ratio(total, 252, upside_heavy, 0.0)
    b = sortino_ratio(total, 252, symmetric, 0.0)
    assert a > b


def test_sortino_matches_a_hand_computed_downside_deviation() -> None:
    """Half the days at -1%, half at +1%, MAR 0.
    Downside deviation = sqrt(mean(min(r,0)^2)) * sqrt(252)
                       = sqrt(0.5 * 0.0001) * sqrt(252).
    """
    daily = np.array([-0.01, 0.01] * 100)
    expected_dd = np.sqrt(0.5 * 0.0001) * np.sqrt(252)
    assert sortino_ratio(0.10, 252, daily, 0.0) == pytest.approx(0.10 / expected_dd, abs=1e-12)


def test_sortino_is_zero_when_there_is_no_downside() -> None:
    assert sortino_ratio(0.10, 252, np.full(100, 0.01), 0.0) == 0.0


def test_max_drawdown_of_a_known_path() -> None:
    """1.0 -> 1.20 -> 0.60 -> 0.90: peak 1.20, trough 0.60, MDD = 50%."""
    paths = np.array([[1.20, 0.60, 0.90]])
    np.testing.assert_allclose(max_drawdown(paths), [0.5], atol=1e-12)


def test_max_drawdown_counts_a_fall_from_the_implicit_initial_value() -> None:
    """A path that only ever falls still has a drawdown measured from 1.0."""
    paths = np.array([[0.90, 0.80]])
    np.testing.assert_allclose(max_drawdown(paths), [0.2], atol=1e-12)


def test_max_drawdown_is_zero_for_a_monotonic_path() -> None:
    paths = np.array([[1.01, 1.02, 1.03]])
    np.testing.assert_allclose(max_drawdown(paths), [0.0], atol=1e-12)


def test_calmar_is_annualised_return_over_max_drawdown() -> None:
    assert calmar_ratio(0.21, 126, 0.20) == pytest.approx((1.1**2 - 1.0) / 0.20, abs=1e-12)


def test_calmar_is_zero_when_there_is_no_drawdown() -> None:
    assert calmar_ratio(0.10, 252, 0.0) == 0.0


def test_daily_returns_from_paths_recovers_a_constant_growth_rate() -> None:
    growth = 1.01 ** np.arange(1, 6, dtype=float)
    result = daily_returns_from_paths(growth.reshape(1, -1))
    np.testing.assert_allclose(result, np.full((1, 5), 0.01), atol=1e-12)


def test_horizon_returns_compounds_non_overlapping_windows() -> None:
    """Constant 1% daily growth: each 10-day window returns 1.01^10 - 1."""
    growth = 1.01 ** np.arange(1, 21, dtype=float)
    result = horizon_returns(growth.reshape(1, -1), 10)
    np.testing.assert_allclose(result, np.full(2, 1.01**10 - 1.0), atol=1e-12)


def test_horizon_returns_drops_an_incomplete_trailing_window() -> None:
    growth = 1.01 ** np.arange(1, 26, dtype=float)
    assert horizon_returns(growth.reshape(1, -1), 10).size == 2


def test_horizon_returns_rejects_a_window_longer_than_the_path() -> None:
    with pytest.raises(ValueError, match="window"):
        horizon_returns(np.ones((1, 5)), 10)


def test_var_and_cvar_match_the_gaussian_closed_form() -> None:
    """For X ~ N(0, sigma):
        VaR_95  = 1.6449 * sigma
        CVaR_95 = sigma * phi(z_0.05) / 0.05 = 2.0627 * sigma
    """
    sigma = 0.10
    draws = np.random.default_rng(42).normal(0.0, sigma, 2_000_000)
    result = tail_risk(draws, confidence=0.95, horizon_days=252, portfolio_value=1_000.0)

    z = stats.norm.ppf(0.05)
    assert result.var_pct == pytest.approx(-z * sigma, rel=0.01)
    assert result.cvar_pct == pytest.approx(sigma * stats.norm.pdf(z) / 0.05, rel=0.01)


def test_tail_risk_reports_losses_as_positive() -> None:
    """Spec 1.7: one stated sign convention, labelled in the payload."""
    losses = np.linspace(-0.50, 0.30, 10_000)
    result = tail_risk(losses, 0.95, 252, 1_000.0)
    assert result.var_pct > 0.0
    assert result.cvar_pct > result.var_pct
    assert result.convention == "loss_positive"


def test_tail_risk_currency_scales_with_portfolio_value() -> None:
    draws = np.random.default_rng(1).normal(0.0, 0.1, 100_000)
    small = tail_risk(draws, 0.95, 252, 1_000.0)
    large = tail_risk(draws, 0.95, 252, 250_000.0)
    assert large.var_currency == pytest.approx(small.var_currency * 250.0, rel=1e-12)
    assert small.var_currency == pytest.approx(small.var_pct * 1_000.0, rel=1e-12)


def test_tail_risk_records_its_horizon() -> None:
    """The defect was a bare percentage with no horizon attached."""
    draws = np.random.default_rng(2).normal(0.0, 0.1, 10_000)
    assert tail_risk(draws, 0.95, 10, 1_000.0).horizon_days == 10


def test_cvar_var_ratio_is_larger_for_a_fat_tailed_sample() -> None:
    """The tail-fatness diagnostic, and the justification for the GMM feature.

    Gaussian CVaR/VaR at 95% is 2.0627/1.6449 = 1.254. A fat-tailed mixture must
    exceed that.
    """
    gen = np.random.default_rng(3)
    gaussian = gen.normal(0.0, 0.02, 500_000)
    mixture = np.where(
        gen.random(500_000) < 0.9,
        gen.normal(0.0, 0.01, 500_000),
        gen.normal(0.0, 0.08, 500_000),
    )
    thin = tail_risk(gaussian, 0.95, 252, 1.0).cvar_var_ratio
    fat = tail_risk(mixture, 0.95, 252, 1.0).cvar_var_ratio

    assert thin == pytest.approx(1.254, rel=0.02)
    assert fat > thin + 0.10
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_risk_metrics.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.risk_metrics'`.

- [ ] **Step 3: Write `backend/src/risk_metrics.py`**

```python
"""Distribution and risk statistics, computed from full simulated path sets.

Every statistic here takes the complete array. Nothing in this module ever sees a
chart sample: the truncated sample exists only for rendering.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TRADING_DAYS_PER_YEAR = 252

# The ladder the API publishes (spec 1.1).
PERCENTILE_LEVELS: tuple[int, ...] = (1, 5, 10, 25, 50, 75, 90, 95, 99)


def percentiles(
    values: np.ndarray,
    levels: tuple[int, ...] = PERCENTILE_LEVELS,
) -> dict[str, float]:
    """Percentiles of the full sample, keyed 'p1', 'p5', ... , 'p99'.

    Uses numpy's default linear interpolation between order statistics.
    """
    flat = np.asarray(values, dtype=float).ravel()
    quantiles = np.percentile(flat, levels)
    return {f"p{level}": float(value) for level, value in zip(levels, quantiles, strict=True)}


def annualized_return(
    total_return: float,
    horizon_days: int,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Geometric annualisation: (1 + R)^(252 / horizon) - 1."""
    if horizon_days <= 0:
        raise ValueError(f"horizon_days must be positive, got {horizon_days}")
    return float((1.0 + total_return) ** (periods_per_year / horizon_days) - 1.0)


def sharpe_ratio(
    total_return: float,
    horizon_days: int,
    annualized_vol: float,
    risk_free_rate: float,
) -> float:
    """Annualised excess return over annualised volatility.

    Both numerator and denominator are annual quantities, which is the horizon
    match the previous implementation lacked.
    """
    if annualized_vol <= 0.0:
        return 0.0
    excess = annualized_return(total_return, horizon_days) - risk_free_rate
    return float(excess / annualized_vol)


def _daily_rate(annual_rate: float) -> float:
    """Compound an annual rate down to one trading day."""
    return float((1.0 + annual_rate) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0)


def sortino_ratio(
    total_return: float,
    horizon_days: int,
    daily_returns: np.ndarray,
    risk_free_rate: float,
) -> float:
    """Annualised excess return over annualised downside deviation.

    Downside deviation uses the risk-free rate as the minimum acceptable return and
    the full observation count in the denominator, so upside dispersion is not
    counted as risk.
    """
    minimum_acceptable = _daily_rate(risk_free_rate)
    shortfall = np.minimum(np.asarray(daily_returns, dtype=float) - minimum_acceptable, 0.0)
    downside_deviation = float(
        np.sqrt(np.mean(shortfall**2)) * np.sqrt(TRADING_DAYS_PER_YEAR)
    )
    if downside_deviation <= 0.0:
        return 0.0
    excess = annualized_return(total_return, horizon_days) - risk_free_rate
    return float(excess / downside_deviation)


def calmar_ratio(
    total_return: float,
    horizon_days: int,
    max_drawdown_value: float,
) -> float:
    """Annualised return over maximum drawdown.

    By convention Calmar uses total return, not excess return.
    """
    if max_drawdown_value <= 0.0:
        return 0.0
    return float(annualized_return(total_return, horizon_days) / max_drawdown_value)


def _with_initial_value(paths: np.ndarray, initial_value: float) -> np.ndarray:
    """Prepend the implicit starting value so day-1 moves are measured correctly."""
    paths = np.asarray(paths, dtype=float)
    leading = np.full((paths.shape[0], 1), initial_value, dtype=float)
    return np.concatenate([leading, paths], axis=1)


def max_drawdown(paths: np.ndarray, initial_value: float = 1.0) -> np.ndarray:
    """Per-path maximum drawdown, as a positive fraction of the running peak.

    The implicit initial value is included, so a path that only falls still records
    a drawdown.
    """
    full = _with_initial_value(paths, initial_value)
    running_peak = np.maximum.accumulate(full, axis=1)
    return np.max(1.0 - full / running_peak, axis=1)


def daily_returns_from_paths(paths: np.ndarray, initial_value: float = 1.0) -> np.ndarray:
    """Per-path daily simple returns implied by a value path."""
    full = _with_initial_value(paths, initial_value)
    return full[:, 1:] / full[:, :-1] - 1.0


def horizon_returns(paths: np.ndarray, k: int, initial_value: float = 1.0) -> np.ndarray:
    """Non-overlapping k-day simple returns, pooled across paths and windows.

    Non-overlapping windows keep the observations independent, which overlapping
    windows would not. An incomplete trailing window is dropped.
    """
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    full = _with_initial_value(paths, initial_value)
    n_windows = (full.shape[1] - 1) // k
    if n_windows < 1:
        raise ValueError(
            f"window of {k} days does not fit in a {full.shape[1] - 1}-day path"
        )
    starts = np.arange(n_windows) * k
    return (full[:, starts + k] / full[:, starts] - 1.0).ravel()


@dataclass(frozen=True)
class TailRisk:
    """VaR and CVaR with their confidence, horizon, and sign convention attached."""

    confidence: float
    horizon_days: int
    var_pct: float
    cvar_pct: float
    var_currency: float
    cvar_currency: float
    cvar_var_ratio: float
    convention: str = "loss_positive"


def tail_risk(
    returns: np.ndarray,
    confidence: float,
    horizon_days: int,
    portfolio_value: float,
) -> TailRisk:
    """Historical-simulation VaR and CVaR from the full simulated return sample.

    Losses are reported positive. CVaR is the mean of the returns at or below the
    VaR quantile, so CVaR >= VaR always holds under this convention.
    """
    flat = np.asarray(returns, dtype=float).ravel()
    quantile = float(np.percentile(flat, (1.0 - confidence) * 100.0))
    tail = flat[flat <= quantile]
    conditional = float(tail.mean()) if tail.size else quantile

    var_pct = -quantile
    cvar_pct = -conditional
    ratio = float(cvar_pct / var_pct) if abs(var_pct) > 1e-12 else float("nan")

    return TailRisk(
        confidence=confidence,
        horizon_days=horizon_days,
        var_pct=var_pct,
        cvar_pct=cvar_pct,
        var_currency=var_pct * portfolio_value,
        cvar_currency=cvar_pct * portfolio_value,
        cvar_var_ratio=ratio,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_risk_metrics.py -v
```

Expected: 28 passed.

- [ ] **Step 5: Run the gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

- [ ] **Step 6: Append the risk-metrics section to `docs/METHODOLOGY.md`**

```markdown
## Scenario percentiles

**What was wrong.** `PortfolioSimulationResponse` carried no terminal-return array.
The frontend checked for `final_returns`, did not find it, and fell through to
deriving the Best / Bullish / Median / Bearish / Worst ladder from
`portfolio_paths_sample` — which was `portfolio_paths[:30]`. A user who configured
1000 paths was shown a 1st and 99th percentile estimated from 30 observations. At
n=30 those order statistics are the sample minimum and maximum, so the reported
"1% worst case" was simply the worst of 30 draws.

**What replaced it.** All nine percentiles (1, 5, 10, 25, 50, 75, 90, 95, 99) are
computed server-side from the complete terminal-return array and returned in a
`percentiles` object. The chart sample is renamed `portfolio_paths_chart_sample` so
its purpose is unambiguous, and the frontend marks it on arrival and throws if any
statistic is derived from it.

**Method.** `numpy.percentile` with default linear interpolation between order
statistics.

**What breaks it.** Extreme percentiles remain sampling estimates: the 1st
percentile of 1000 paths is interpolated between the 10th and 11th smallest
observations and carries real Monte Carlo error. More paths narrow it; no number of
paths removes it.

## Risk-adjusted performance

### Sharpe ratio

**What was wrong.** `sharpe_ratio = mean / annualized_vol`, where `mean` was the
cumulative return over the horizon (365 days by default) and the denominator was
annualised. Two independent errors:

1. **No risk-free rate.** The Sharpe ratio is defined on excess return. Omitting rf
   at a 4% short rate inflates the ratio by `0.04 / sigma` — about 0.13 at 30% vol.
2. **Mismatched horizons.** A 365-day cumulative return divided by an annual
   volatility is a ratio of quantities measured over different periods. At a 20%
   365-day return the numerator was overstated by a factor of
   `0.20 / ((1.20)^(252/365) - 1) = 1.50`.

**Correct form.**

    excess_annualized = (1 + R_total)^(252 / horizon_days) - 1 - rf
    Sharpe            = excess_annualized / sigma_annualized

`R_total` is the mean terminal return across paths; `sigma_annualized` is the
standard deviation of simulated daily portfolio simple returns times `sqrt(252)`.
A test asserts the definitional property: a portfolio returning exactly rf scores
exactly 0.00.

### Sortino ratio

    MAR                = (1 + rf)^(1/252) - 1
    downside_deviation = sqrt(mean(min(r_t - MAR, 0)^2)) * sqrt(252)
    Sortino            = excess_annualized / downside_deviation

The full observation count is used in the mean, not only the count of losing days,
so upside dispersion is not counted as risk. Undefined when no observation falls
below MAR; reported as 0.0.

### Calmar ratio

    Calmar = annualized_return / median_max_drawdown_across_paths

By convention Calmar uses total rather than excess return. The median maximum
drawdown across paths is used, not the mean, because the MDD distribution is
right-skewed. Maximum drawdown is measured from the running peak including the
implicit initial value of 1.0, so a path that only falls still records a drawdown.

**Assumption set for all three.** The risk-free rate is constant over the horizon.
`R_total` is the mean terminal return, an arithmetic expectation across paths; the
median terminal return is reported alongside because the two differ materially for
a right-skewed terminal distribution.

## Value at Risk and Conditional VaR

**What was wrong.** VaR was a bare percentage. No horizon was attached, so a
one-year figure was rendered beside daily volatility with nothing distinguishing
them, and the sign convention was inconsistent between fields.

**What replaced it.** VaR and CVaR are returned as a single object carrying
`confidence`, `horizon_days`, percentage and currency values, and an explicit
`convention: "loss_positive"`. Three horizons are reported:

| Key | Horizon | Purpose |
|---|---|---|
| `d1` | 1 day | Standard daily risk figure |
| `d10` | 10 days | The Basel market-risk horizon |
| `horizon` | full simulated horizon | The scenario the user configured |

**Method.** Historical simulation on the simulated distribution — the empirical
quantile of the full sample, with no parametric assumption beyond the simulation
model itself. The 1-day and 10-day figures are computed from **non-overlapping**
windows of the simulated value paths, which keeps the observations independent;
overlapping windows would understate the dispersion. They are not obtained by
scaling the annual figure by `sqrt(t)`, because that scaling assumes normality and
independence and defeats the purpose of running a fat-tailed model.

    VaR_alpha  = -quantile(R, 1 - alpha)
    CVaR_alpha = -mean(R | R <= quantile(R, 1 - alpha))

**CVaR/VaR ratio.** Reported as the tail-fatness diagnostic. For a normal
distribution at 95% it is `2.0627 / 1.6449 = 1.254`; a materially higher value means
the simulated tail is fatter than Gaussian. This single number is the justification
for the joint GMM existing, and a test asserts the Gaussian value to 2% and that a
fat-tailed mixture exceeds it.

**What breaks it.** Empirical quantiles at 99% from 1000 paths rest on roughly ten
observations. VaR says nothing about losses beyond the quantile, which is why CVaR is
reported beside it, and neither is a bound: both are properties of the simulated
distribution, and if the model is wrong about the tail, so are they.
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/risk_metrics.py backend/tests/test_risk_metrics.py docs/METHODOLOGY.md
git commit -m "feat: risk metrics with matched-horizon Sharpe, Sortino, Calmar, and labelled VaR/CVaR"
```

---

### Task 8: Return and risk contributions

Implements spec 1.6. `asset_stats.contribution` is `weights[i] * asset_mean[i] / abs(total_weighted_return)`. Dividing by an absolute value breaks sign handling: for a portfolio that lost money the contributions sum to −1, and the frontend then took absolute values again to force the pie chart to add up, discarding the sign entirely. It was rendered under a heading called "Allocation", which is a third thing it is not.

**Files:**
- Create: `backend/src/contributions.py`
- Create: `backend/tests/test_contributions.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: `TRADING_DAYS_PER_YEAR` from `src.risk_metrics` (Task 7).
- Produces:
  - `annualized_covariance(daily_simple_returns: np.ndarray, max_paths: int = COVARIANCE_SUBSAMPLE_PATHS) -> np.ndarray` shape `(n_assets, n_assets)`
  - `risk_contributions(weights: np.ndarray, covariance: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]` returning `(marginal, contribution, portfolio_vol)`
  - `return_contributions(weights: np.ndarray, asset_returns: np.ndarray, portfolio_return: float) -> np.ndarray` (signed; `nan` when the portfolio return is degenerate)
  - `COVARIANCE_SUBSAMPLE_PATHS: int`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_contributions.py`:

```python
"""Return and risk decomposition. Risk contributions must sum to portfolio vol."""

from __future__ import annotations

import numpy as np
import pytest

from src.contributions import (
    annualized_covariance,
    return_contributions,
    risk_contributions,
)
from src.risk_metrics import TRADING_DAYS_PER_YEAR


def _random_covariance(n: int, seed: int = 3) -> np.ndarray:
    gen = np.random.default_rng(seed)
    a = gen.standard_normal((n, n + 5))
    return (a @ a.T) / (n + 5)


def test_risk_contributions_sum_to_portfolio_volatility() -> None:
    """Definition of done for spec 1.6, asserted to 1e-9."""
    weights = np.array([0.4, 0.35, 0.25])
    covariance = _random_covariance(3)
    _, contribution, portfolio_vol = risk_contributions(weights, covariance)
    assert contribution.sum() == pytest.approx(portfolio_vol, abs=1e-9)


def test_risk_contributions_sum_to_portfolio_volatility_for_ten_assets() -> None:
    gen = np.random.default_rng(8)
    weights = gen.random(10)
    weights /= weights.sum()
    _, contribution, portfolio_vol = risk_contributions(weights, _random_covariance(10, seed=9))
    assert contribution.sum() == pytest.approx(portfolio_vol, abs=1e-9)


def test_portfolio_vol_matches_the_quadratic_form() -> None:
    weights = np.array([0.6, 0.4])
    covariance = np.array([[0.04, 0.006], [0.006, 0.09]])
    _, _, portfolio_vol = risk_contributions(weights, covariance)
    assert portfolio_vol == pytest.approx(np.sqrt(weights @ covariance @ weights), abs=1e-14)


def test_equal_weighted_uncorrelated_equal_vol_assets_contribute_equally() -> None:
    """Closed form: each of N identical uncorrelated assets contributes sigma_p / N."""
    n = 4
    weights = np.full(n, 1.0 / n)
    covariance = np.eye(n) * 0.04
    _, contribution, portfolio_vol = risk_contributions(weights, covariance)

    np.testing.assert_allclose(contribution, portfolio_vol / n, atol=1e-14)
    assert portfolio_vol == pytest.approx(np.sqrt(0.04 / n), abs=1e-14)


def test_marginal_risk_is_the_gradient_of_portfolio_volatility() -> None:
    """MCR_i = d sigma_p / d w_i, verified by central finite difference."""
    weights = np.array([0.5, 0.3, 0.2])
    covariance = _random_covariance(3, seed=11)
    marginal, _, _ = risk_contributions(weights, covariance)

    def vol(w: np.ndarray) -> float:
        return float(np.sqrt(w @ covariance @ w))

    eps = 1e-7
    for i in range(3):
        step = np.zeros(3)
        step[i] = eps
        numerical = (vol(weights + step) - vol(weights - step)) / (2 * eps)
        assert marginal[i] == pytest.approx(numerical, rel=1e-6)


def test_a_high_vol_asset_carries_risk_far_above_its_weight() -> None:
    """The divergence the UI must show: weight and risk contribution are not the same."""
    weights = np.array([0.9, 0.1])
    covariance = np.array([[0.01, 0.0], [0.0, 1.00]])
    _, contribution, portfolio_vol = risk_contributions(weights, covariance)
    risk_share = contribution / portfolio_vol

    assert risk_share[1] > 0.5
    assert weights[1] == 0.1


def test_risk_contributions_are_zero_for_a_zero_variance_portfolio() -> None:
    marginal, contribution, portfolio_vol = risk_contributions(
        np.array([0.5, 0.5]), np.zeros((2, 2))
    )
    assert portfolio_vol == 0.0
    np.testing.assert_array_equal(marginal, np.zeros(2))
    np.testing.assert_array_equal(contribution, np.zeros(2))


def test_return_contributions_sum_to_one_for_a_positive_portfolio() -> None:
    weights = np.array([0.5, 0.3, 0.2])
    returns = np.array([0.20, 0.10, -0.05])
    portfolio_return = float(weights @ returns)
    result = return_contributions(weights, returns, portfolio_return)
    assert result.sum() == pytest.approx(1.0, abs=1e-12)


def test_return_contributions_sum_to_one_for_a_losing_portfolio() -> None:
    """The defect: dividing by abs(portfolio_return) made these sum to -1."""
    weights = np.array([0.5, 0.5])
    returns = np.array([-0.20, -0.05])
    portfolio_return = float(weights @ returns)
    assert portfolio_return < 0

    result = return_contributions(weights, returns, portfolio_return)
    assert result.sum() == pytest.approx(1.0, abs=1e-12)

    old_and_wrong = weights * returns / abs(portfolio_return)
    assert old_and_wrong.sum() == pytest.approx(-1.0, abs=1e-12)


def test_return_contributions_keep_their_sign() -> None:
    """A loser inside a winning portfolio must contribute negatively."""
    weights = np.array([0.5, 0.5])
    returns = np.array([0.40, -0.10])
    result = return_contributions(weights, returns, float(weights @ returns))
    assert result[0] > 0
    assert result[1] < 0


def test_return_contributions_are_nan_for_a_degenerate_portfolio_return() -> None:
    """No ZeroDivisionError, and no silently fabricated 0.0."""
    result = return_contributions(np.array([0.5, 0.5]), np.array([0.10, -0.10]), 0.0)
    assert np.isnan(result).all()


def test_annualized_covariance_scales_the_daily_estimate_by_252() -> None:
    gen = np.random.default_rng(5)
    daily = gen.normal(0.0, 0.01, size=(20, 500, 2))
    annual = annualized_covariance(daily)
    flat_daily_cov = np.cov(daily.reshape(-1, 2), rowvar=False, ddof=1)
    np.testing.assert_allclose(annual, flat_daily_cov * TRADING_DAYS_PER_YEAR, rtol=1e-12)


def test_annualized_covariance_recovers_a_known_target() -> None:
    """Daily sigma 1% with correlation 0.5 annualises to sigma 15.87%."""
    gen = np.random.default_rng(7)
    target_corr = np.array([[1.0, 0.5], [0.5, 1.0]])
    shocks = gen.standard_normal((400_000, 2)) @ np.linalg.cholesky(target_corr).T * 0.01
    annual = annualized_covariance(shocks.reshape(1, -1, 2))

    expected_vol = 0.01 * np.sqrt(TRADING_DAYS_PER_YEAR)
    np.testing.assert_allclose(np.sqrt(np.diag(annual)), expected_vol, rtol=0.01)
    assert annual[0, 1] / (expected_vol**2) == pytest.approx(0.5, abs=0.01)


def test_annualized_covariance_subsamples_paths_without_material_bias() -> None:
    """Subsampling is a compute bound, not a modelling choice: the estimate must hold."""
    gen = np.random.default_rng(13)
    daily = gen.normal(0.0, 0.012, size=(2000, 300, 2))
    full = annualized_covariance(daily, max_paths=2000)
    subsampled = annualized_covariance(daily, max_paths=200)
    np.testing.assert_allclose(subsampled, full, rtol=0.05)


def test_annualized_covariance_is_deterministic() -> None:
    """Subsampling takes the leading paths, never a random draw."""
    gen = np.random.default_rng(17)
    daily = gen.normal(0.0, 0.01, size=(600, 100, 3))
    first = annualized_covariance(daily, max_paths=100)
    second = annualized_covariance(daily, max_paths=100)
    np.testing.assert_array_equal(first, second)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_contributions.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.contributions'`.

- [ ] **Step 3: Write `backend/src/contributions.py`**

```python
"""Return and risk decomposition across portfolio holdings.

Return contribution answers "where did the return come from". Risk contribution
answers "where is the risk", which is the question that matters for management and
the one the previous implementation did not compute at all.
"""

from __future__ import annotations

import numpy as np

from src.risk_metrics import TRADING_DAYS_PER_YEAR

# Paths used to estimate the covariance matrix. At 300+ days per path this is
# 60,000+ joint observations, so the sampling error is negligible while the memory
# cost of materialising expm1 over every path is avoided.
COVARIANCE_SUBSAMPLE_PATHS = 500


def annualized_covariance(
    daily_simple_returns: np.ndarray,
    max_paths: int = COVARIANCE_SUBSAMPLE_PATHS,
) -> np.ndarray:
    """Annualised asset covariance from simulated daily simple returns.

    `daily_simple_returns` is (num_paths, horizon, n_assets). Estimated from the
    leading `max_paths` paths — a deterministic subsample, never a random draw, so
    the result is reproducible.

    Simple returns are used rather than log returns because the portfolio is
    aggregated in simple-return space, so this is the covariance of the quantities
    the weights actually multiply.
    """
    returns = np.asarray(daily_simple_returns, dtype=float)
    n_assets = returns.shape[-1]
    used = returns[: min(max_paths, returns.shape[0])]
    flat = used.reshape(-1, n_assets)
    return np.cov(flat, rowvar=False, ddof=1).reshape(n_assets, n_assets) * TRADING_DAYS_PER_YEAR


def risk_contributions(
    weights: np.ndarray,
    covariance: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Marginal and total contribution to portfolio risk.

        sigma_p = sqrt(w' S w)
        MCR_i   = (S w)_i / sigma_p          # d sigma_p / d w_i
        CTR_i   = w_i * MCR_i                # sums to sigma_p exactly

    The summation identity is Euler's homogeneous function theorem: sigma_p is
    homogeneous of degree 1 in w, so the weighted gradient recovers it exactly.

    Returns `(marginal, contribution, portfolio_vol)`.
    """
    w = np.asarray(weights, dtype=float)
    S = np.asarray(covariance, dtype=float)

    portfolio_vol = float(np.sqrt(max(w @ S @ w, 0.0)))
    if portfolio_vol <= 0.0:
        zeros = np.zeros_like(w)
        return zeros, zeros, 0.0

    marginal = (S @ w) / portfolio_vol
    return marginal, w * marginal, portfolio_vol


def return_contributions(
    weights: np.ndarray,
    asset_returns: np.ndarray,
    portfolio_return: float,
) -> np.ndarray:
    """Signed share of portfolio return attributable to each holding.

        contribution_i = w_i * r_i / R_p

    No absolute value in the denominator: the shares sum to exactly 1 whether the
    portfolio gained or lost, and a losing holding inside a winning portfolio
    carries a negative share. Returns `nan` when the portfolio return is too close
    to zero for the ratio to mean anything.
    """
    w = np.asarray(weights, dtype=float)
    r = np.asarray(asset_returns, dtype=float)

    if abs(portfolio_return) < 1e-12:
        return np.full(w.shape, np.nan)
    return w * r / portfolio_return
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_contributions.py -v
```

Expected: 15 passed.

- [ ] **Step 5: Run the gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

- [ ] **Step 6: Append the contributions section to `docs/METHODOLOGY.md`**

```markdown
## Return and risk contributions

**What was wrong.** A single field named `contribution` held

    w_i * r_i / abs(R_p)

and was rendered under a heading called "Allocation". Three problems:

1. **The absolute value breaks the sign.** For a portfolio that lost money the
   shares sum to −1, not +1. The frontend then applied `Math.abs` again to force the
   pie chart to add up, discarding the sign entirely — so a holding that lost money
   in a losing portfolio was displayed identically to one that made money.
2. **It is not allocation.** Allocation is `w_i`. This was a return attribution.
3. **Risk contribution did not exist.** The number that matters for portfolio
   management — where the risk is, as opposed to where the money is — was absent.

**Return contribution.**

    return_contribution_i = w_i * r_i / R_p,        R_p = sum_i w_i r_i

Signed, no absolute value, sums to exactly 1 in both gain and loss. Reported as
`nan` when `abs(R_p) < 1e-12`, because the ratio is meaningless there; it is not
silently reported as 0.

**Risk contribution.**

    sigma_p = sqrt(w' S w)
    MCR_i   = (S w)_i / sigma_p        # marginal contribution: d sigma_p / d w_i
    CTR_i   = w_i * MCR_i              # total contribution
    sum_i CTR_i = sigma_p              # exactly

The summation identity follows from Euler's homogeneous function theorem, since
`sigma_p` is homogeneous of degree 1 in `w`. It is asserted to 1e-9 in tests, and
`MCR` is separately verified against a central finite difference of `sigma_p`.

**Why risk contribution is the number that matters.** Weight and risk contribution
diverge sharply whenever volatilities differ. A 10% weight in an asset ten times as
volatile as the rest of the book can carry more than half the portfolio's risk. The
UI therefore shows weight and risk contribution side by side in a panel titled
"Risk Contribution", and a test asserts exactly that 10%-weight / >50%-risk case.

**Covariance estimation.** `S` is the annualised covariance of the **simulated**
daily simple returns, not of the historical sample. Two consequences, both
deliberate:

- the decomposition reflects the model actually used, so selecting the joint GMM
  changes the risk contributions through its regime-dependent covariance;
- simple returns are used rather than log returns, because the portfolio is
  aggregated in simple-return space, so these are the quantities the weights
  multiply.

`S` is estimated from the leading 500 simulated paths. At 250+ days per path that is
125,000+ joint observations, so the sampling error is far below the model error,
while the memory cost of materialising simple returns over all paths is avoided.
The subsample is the leading paths, never a random draw, so the estimate is
reproducible.

**What breaks it.** Contributions are point estimates carrying the covariance
estimate's error; with many assets and a short history the sample covariance is
poorly conditioned and the decomposition inherits that. Shrinkage (spec Phase 2)
addresses it and is not implemented here.
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/contributions.py backend/tests/test_contributions.py docs/METHODOLOGY.md
git commit -m "feat: signed return contributions and marginal risk contribution decomposition"
```

---

### Task 9: Risk-free rate provider

Supports spec 1.5. Sharpe needs a stated rf, defaulted from the 3-month T-bill and cached, with the assumed value displayed beside the ratio.

**Files:**
- Create: `backend/src/risk_free.py`
- Create: `backend/tests/test_risk_free.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `RiskFreeRate` frozen dataclass with `value: float` and `source: str` (`"^IRX" | "fallback" | "user"`)
  - `get_risk_free_rate(user_value: float | None = None, now: float | None = None) -> RiskFreeRate`
  - `clear_cache() -> None`
  - `FALLBACK_RATE: float`, `CACHE_TTL_SECONDS: int`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_risk_free.py`:

```python
"""The risk-free provider must never fail a request and must always state its source."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from src import risk_free
from src.risk_free import FALLBACK_RATE, clear_cache, get_risk_free_rate


@pytest.fixture(autouse=True)
def _clean_cache() -> Any:
    clear_cache()
    yield
    clear_cache()


def _irx_frame(rate_percent: float) -> pd.DataFrame:
    index = pd.bdate_range("2026-08-14", periods=2, name="Date")
    return pd.DataFrame({"Close": [rate_percent - 0.01, rate_percent]}, index=index)


def test_a_user_supplied_rate_is_used_verbatim_and_never_fetches(monkeypatch: Any) -> None:
    def _explode(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("must not hit the network when the user states a rate")

    monkeypatch.setattr(risk_free.yf, "download", _explode)
    result = get_risk_free_rate(user_value=0.0375)
    assert result.value == 0.0375
    assert result.source == "user"


def test_a_fetched_rate_is_converted_from_percent(monkeypatch: Any) -> None:
    """^IRX quotes 4.25 to mean 4.25%."""
    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: _irx_frame(4.25))
    result = get_risk_free_rate()
    assert result.value == pytest.approx(0.0425)
    assert result.source == "^IRX"


def test_a_failed_fetch_falls_back_without_raising(monkeypatch: Any) -> None:
    def _fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("yfinance schema changed again")

    monkeypatch.setattr(risk_free.yf, "download", _fail)
    result = get_risk_free_rate()
    assert result.value == FALLBACK_RATE
    assert result.source == "fallback"


def test_an_empty_response_falls_back(monkeypatch: Any) -> None:
    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: pd.DataFrame())
    assert get_risk_free_rate().source == "fallback"


def test_an_implausible_rate_falls_back(monkeypatch: Any) -> None:
    """A 4250% short rate is a units bug in the upstream feed, not a rate."""
    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: _irx_frame(4250.0))
    assert get_risk_free_rate().source == "fallback"


def test_a_negative_rate_falls_back(monkeypatch: Any) -> None:
    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: _irx_frame(-1.0))
    assert get_risk_free_rate().source == "fallback"


def test_a_multiindex_close_column_is_handled(monkeypatch: Any) -> None:
    """yfinance returns MultiIndex columns for a single ticker."""
    index = pd.bdate_range("2026-08-14", periods=2, name="Date")
    frame = pd.DataFrame(
        [[4.10], [4.20]],
        index=index,
        columns=pd.MultiIndex.from_tuples([("Close", "^IRX")]),
    )
    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: frame)
    assert get_risk_free_rate().value == pytest.approx(0.042)


def test_the_second_call_inside_the_ttl_is_served_from_cache(monkeypatch: Any) -> None:
    calls = {"n": 0}

    def _counted(*args: Any, **kwargs: Any) -> pd.DataFrame:
        calls["n"] += 1
        return _irx_frame(4.25)

    monkeypatch.setattr(risk_free.yf, "download", _counted)
    first = get_risk_free_rate(now=1_000.0)
    second = get_risk_free_rate(now=1_000.0 + risk_free.CACHE_TTL_SECONDS - 1)

    assert calls["n"] == 1
    assert first.value == second.value


def test_the_cache_expires_after_the_ttl(monkeypatch: Any) -> None:
    calls = {"n": 0}

    def _counted(*args: Any, **kwargs: Any) -> pd.DataFrame:
        calls["n"] += 1
        return _irx_frame(4.25)

    monkeypatch.setattr(risk_free.yf, "download", _counted)
    get_risk_free_rate(now=1_000.0)
    get_risk_free_rate(now=1_000.0 + risk_free.CACHE_TTL_SECONDS + 1)
    assert calls["n"] == 2


def test_a_failed_fetch_is_not_cached(monkeypatch: Any) -> None:
    """A transient outage must not pin the fallback for the whole TTL."""
    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: pd.DataFrame())
    assert get_risk_free_rate(now=1_000.0).source == "fallback"

    monkeypatch.setattr(risk_free.yf, "download", lambda *a, **k: _irx_frame(4.5))
    assert get_risk_free_rate(now=1_000.0).source == "^IRX"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_risk_free.py -v
```

Expected: `ModuleNotFoundError: No module named 'src.risk_free'`.

- [ ] **Step 3: Write `backend/src/risk_free.py`**

```python
"""Risk-free rate provider backed by the 13-week US T-bill (^IRX).

The Sharpe ratio is defined on excess return, so a rate is always required. This
provider therefore never raises: it degrades to a stated fallback and always reports
which source produced the number, so the UI can display the assumption.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Used when the fetch fails. Roughly the post-2023 US short-rate regime; stated
# explicitly rather than silently defaulting to zero, which would flatter Sharpe.
FALLBACK_RATE = 0.04

CACHE_TTL_SECONDS = 6 * 3600

# Outside this band the upstream value is a units or feed error, not a rate.
_PLAUSIBLE_RANGE = (0.0, 0.25)

_TICKER = "^IRX"
_cache: dict[str, tuple[float, float]] = {}


@dataclass(frozen=True)
class RiskFreeRate:
    """A rate and its provenance. `source` is always displayed beside the Sharpe."""

    value: float
    source: str


def clear_cache() -> None:
    """Drop the cached rate. Used by tests."""
    _cache.clear()


def _extract_latest_close(data: pd.DataFrame) -> float:
    """Last non-null close, tolerating yfinance's MultiIndex single-ticker columns."""
    if data is None or data.empty or "Close" not in data.columns:
        raise ValueError("no Close column in ^IRX response")

    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    cleaned = close.dropna()
    if cleaned.empty:
        raise ValueError("^IRX Close column is entirely null")
    return float(cleaned.iloc[-1])


def get_risk_free_rate(
    user_value: float | None = None,
    now: float | None = None,
) -> RiskFreeRate:
    """Resolve the annual risk-free rate.

    A user-supplied value always wins and never triggers a fetch. Otherwise the
    latest ^IRX close is used, cached for CACHE_TTL_SECONDS. ^IRX is quoted in
    percent, so 4.25 means 4.25%.
    """
    if user_value is not None:
        return RiskFreeRate(value=float(user_value), source="user")

    clock = time.time() if now is None else now
    cached = _cache.get(_TICKER)
    if cached is not None and clock - cached[1] < CACHE_TTL_SECONDS:
        return RiskFreeRate(value=cached[0], source=_TICKER)

    try:
        data = yf.download(
            _TICKER, period="5d", interval="1d", auto_adjust=True, progress=False
        )
        rate = _extract_latest_close(data) / 100.0
        low, high = _PLAUSIBLE_RANGE
        if not low <= rate <= high:
            raise ValueError(f"implausible {_TICKER} rate {rate!r}")
    except Exception as exc:  # noqa: BLE001 - degrade, never fail the request
        logger.warning(
            "risk-free rate fetch failed (%s); falling back to %.4f", exc, FALLBACK_RATE
        )
        return RiskFreeRate(value=FALLBACK_RATE, source="fallback")

    # Only successful fetches are cached, so an outage does not pin the fallback.
    _cache[_TICKER] = (rate, clock)
    return RiskFreeRate(value=rate, source=_TICKER)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_risk_free.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Run the gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

- [ ] **Step 6: Append the risk-free section to `docs/METHODOLOGY.md`**

```markdown
## Risk-free rate

**Source.** The latest close of `^IRX`, the CBOE 13-week US Treasury bill yield,
quoted in percent and divided by 100. Cached for 6 hours.

**Precedence.** A `risk_free_rate` supplied in the request always wins and skips the
fetch entirely. Otherwise the cached or freshly fetched `^IRX` value is used. If the
fetch fails, returns no usable close, or returns a value outside 0–25% — which
indicates a units or feed error rather than a rate — the provider falls back to a
stated 4.00%.

**Provenance is always reported.** Every response carries `risk_free_source`
(`"user"`, `"^IRX"`, or `"fallback"`) alongside the value, and the UI displays the
assumed rate beside the Sharpe ratio. A Sharpe ratio without a stated rf is not
interpretable, and a silent default of zero would flatter it.

**Assumption set.** The 13-week bill is used as the risk-free proxy at every
horizon, including multi-year ones, and is held constant over the simulated horizon.
Only successful fetches are cached, so a transient outage does not pin the fallback
for the full TTL.

**What breaks it.** The provider never raises, so a fallback rate can silently
underlie a Sharpe ratio — which is why the source is in the payload and on screen.
For a multi-year horizon the 3-month bill is the wrong tenor: a duration-matched
Treasury yield would be more defensible. For a non-USD portfolio it is the wrong
currency entirely. Both are recorded in "Known limitations".
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/risk_free.py backend/tests/test_risk_free.py docs/METHODOLOGY.md
git commit -m "feat: cached ^IRX risk-free rate provider with stated provenance"
```

---

### Task 10: Wire the API — server-side percentiles and the full response surface

Implements the server half of spec 1.1 and integrates Tasks 3–9. `main.py` becomes a thin composition root: it validates, fetches, creates one Generator, delegates every calculation, and serialises. No statistic is computed in this file.

**Files:**
- Modify: `backend/main.py` (rewrite)
- Modify: `backend/src/correlation.py` (delete the superseded `build_portfolio_paths` and `compute_portfolio_risk_stats`)
- Create: `backend/tests/test_api.py`
- Modify: `pyproject.toml` (drop `main.py` from the mypy exclude)
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: everything produced by Tasks 3–9.
- Produces the response contract Task 12's frontend depends on:
  - `POST /api/simulate` → `paths_chart_sample`, `percentiles`, `tail_risk`, `final_returns`, `data_quality`
  - `POST /api/simulate-portfolio` → `percentiles`, `tail_risk` (keys `d1`, `d10`, `horizon`), `portfolio_paths_chart_sample`, `asset_paths_chart_sample`, `asset_stats[].{weight,return_contribution_pct,marginal_risk,risk_contribution,risk_contribution_pct}`, `portfolio_stats.{sharpe_ratio,sortino_ratio,calmar_ratio,risk_free_rate,risk_free_source,volatility,decomposition_volatility,median_max_drawdown}`, `mixture_components`, `data_quality`
  - No `portfolio_paths_sample` and no `paths_sample` key exists anywhere in either response.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_api.py`:

```python
"""Endpoint contract tests. No network: the price provider and rf provider are faked."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

TICKERS = ["AAA", "BBB", "CCC"]


@pytest.fixture
def client(
    monkeypatch: Any,
    make_correlated_prices: Callable[..., dict[str, pd.DataFrame]],
) -> TestClient:
    import main
    from src.data_quality import screen_price_series
    from src.risk_free import RiskFreeRate

    prices = make_correlated_prices(TICKERS, target_corr=0.45, n_days=900)

    def _provider(ticker: str, years: int) -> tuple[pd.DataFrame, Any]:
        if ticker not in prices:
            raise ValueError(f"No data returned for ticker {ticker}")
        return screen_price_series(prices[ticker], ticker)

    def _rf(user_value: float | None = None, now: float | None = None) -> RiskFreeRate:
        if user_value is not None:
            return RiskFreeRate(value=user_value, source="user")
        return RiskFreeRate(value=0.04, source="fallback")

    monkeypatch.setattr(main, "get_cached_price_data", _provider)
    monkeypatch.setattr(main, "get_risk_free_rate", _rf)
    return TestClient(main.app)


def _portfolio(client: TestClient, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "tickers": TICKERS,
        "weights": [0.5, 0.3, 0.2],
        "years": 3,
        "horizon": 252,
        "num_paths": 500,
        "correlation_model": "gaussian",
        "random_seed": 42,
    }
    body.update(overrides)
    response = client.post("/api/simulate-portfolio", json=body)
    assert response.status_code == 200, response.text
    return response.json()


# --- spec 1.1: percentiles come from the full path set -----------------------


def test_the_response_carries_all_nine_percentiles(client: TestClient) -> None:
    result = _portfolio(client)
    assert set(result["percentiles"]) == {
        "p1", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99"
    }


def test_percentiles_are_monotonic(client: TestClient) -> None:
    p = _portfolio(client)["percentiles"]
    ordered = [p[f"p{level}"] for level in (1, 5, 10, 25, 50, 75, 90, 95, 99)]
    assert ordered == sorted(ordered)


def test_the_chart_sample_is_truncated_but_percentiles_are_not(client: TestClient) -> None:
    """The defect: the ladder came from these 30 paths. It must not any more."""
    result = _portfolio(client, num_paths=500)
    assert len(result["portfolio_paths_chart_sample"]) == 30
    assert result["num_paths"] == 500

    chart_terminal = [path[-1] - 1.0 for path in result["portfolio_paths_chart_sample"]]
    assert result["percentiles"]["p99"] > max(chart_terminal) - 1e-9 or (
        result["percentiles"]["p99"] != pytest.approx(max(chart_terminal), abs=1e-9)
    )


def test_the_old_sample_field_names_are_gone(client: TestClient) -> None:
    """Renamed so no one computes a statistic from a chart sample again."""
    result = _portfolio(client)
    assert "portfolio_paths_sample" not in result
    assert "asset_paths_sample" not in result
    assert "portfolio_paths_chart_sample" in result
    assert "asset_paths_chart_sample" in result


def test_the_chart_sample_never_exceeds_the_path_count(client: TestClient) -> None:
    result = _portfolio(client, num_paths=100)
    assert len(result["portfolio_paths_chart_sample"]) <= 100


# --- spec 1.2: the GMM toggle now changes the numbers ------------------------


def test_the_gmm_model_reports_its_fitted_regimes(client: TestClient) -> None:
    result = _portfolio(client, correlation_model="gmm_joint", gmm_components=3)
    components = result["mixture_components"]
    assert components is not None
    assert len(components) == 3
    assert sum(c["weight"] for c in components) == pytest.approx(1.0, abs=1e-9)
    for component in components:
        assert len(component["means"]) == 3
        assert np.array(component["covariance"]).shape == (3, 3)


def test_the_gaussian_model_reports_no_mixture(client: TestClient) -> None:
    assert _portfolio(client, correlation_model="gaussian")["mixture_components"] is None


def test_the_gmm_toggle_changes_the_result(client: TestClient) -> None:
    """It was decorative: the fitted mixture was discarded."""
    gaussian = _portfolio(client, correlation_model="gaussian")
    gmm = _portfolio(client, correlation_model="gmm_joint")
    assert gaussian["percentiles"]["p1"] != gmm["percentiles"]["p1"]


def test_the_gmm_produces_a_fatter_tail_than_the_gaussian(client: TestClient) -> None:
    """The CVaR/VaR ratio is the diagnostic; the fat-tailed model must exceed the thin one."""
    gaussian = _portfolio(client, correlation_model="gaussian", horizon=252)
    gmm = _portfolio(client, correlation_model="gmm_joint", horizon=252)
    assert gmm["tail_risk"]["d1"]["cvar_var_ratio"] > gaussian["tail_risk"]["d1"]["cvar_var_ratio"]


def test_the_t_copula_is_declared_but_not_implemented(client: TestClient) -> None:
    """Rejected explicitly rather than silently falling back to Gaussian."""
    response = client.post(
        "/api/simulate-portfolio",
        json={"tickers": TICKERS, "correlation_model": "t_copula"},
    )
    assert response.status_code == 501
    assert "t_copula" in response.json()["detail"]


# --- spec 1.4: rebalancing is a first-class parameter ------------------------


def test_buy_and_hold_is_the_default(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio", json={"tickers": TICKERS, "random_seed": 1}
    )
    assert response.status_code == 200
    assert response.json()["rebalance"] == "buy_and_hold"


def test_the_rebalancing_rule_changes_the_result(client: TestClient) -> None:
    hold = _portfolio(client, rebalance="buy_and_hold")
    daily = _portfolio(client, rebalance="daily")
    assert hold["percentiles"]["p50"] != daily["percentiles"]["p50"]


def test_transaction_costs_reduce_the_median_outcome(client: TestClient) -> None:
    free = _portfolio(client, rebalance="daily", transaction_cost_bps=0.0)
    charged = _portfolio(client, rebalance="daily", transaction_cost_bps=50.0)
    assert charged["percentiles"]["p50"] < free["percentiles"]["p50"]
    assert charged["transaction_cost_bps"] == 50.0


# --- spec 1.5: Sharpe and friends -------------------------------------------


def test_the_assumed_risk_free_rate_and_its_source_are_reported(client: TestClient) -> None:
    """A Sharpe ratio without a stated rf is not interpretable."""
    stats = _portfolio(client)["portfolio_stats"]
    assert stats["risk_free_rate"] == 0.04
    assert stats["risk_free_source"] == "fallback"


def test_a_user_supplied_risk_free_rate_is_echoed(client: TestClient) -> None:
    stats = _portfolio(client, risk_free_rate=0.02)["portfolio_stats"]
    assert stats["risk_free_rate"] == 0.02
    assert stats["risk_free_source"] == "user"


def test_a_higher_risk_free_rate_lowers_the_sharpe_ratio(client: TestClient) -> None:
    low = _portfolio(client, risk_free_rate=0.0)["portfolio_stats"]["sharpe_ratio"]
    high = _portfolio(client, risk_free_rate=0.10)["portfolio_stats"]["sharpe_ratio"]
    assert high < low


def test_sharpe_is_consistent_with_the_reported_inputs(client: TestClient) -> None:
    """Recompute the ratio from the payload: the arithmetic must be reproducible."""
    from src.risk_metrics import annualized_return

    result = _portfolio(client, horizon=365, risk_free_rate=0.03)
    stats = result["portfolio_stats"]
    excess = annualized_return(stats["mean_return"], result["horizon_days"]) - 0.03
    assert stats["sharpe_ratio"] == pytest.approx(excess / stats["volatility"], rel=1e-9)


def test_sortino_and_calmar_are_present(client: TestClient) -> None:
    stats = _portfolio(client)["portfolio_stats"]
    for key in ("sortino_ratio", "calmar_ratio", "median_max_drawdown"):
        assert key in stats
    assert stats["median_max_drawdown"] >= 0.0


# --- spec 1.6: contributions ------------------------------------------------


def test_risk_contribution_shares_sum_to_one(client: TestClient) -> None:
    assets = _portfolio(client)["asset_stats"]
    total = sum(a["risk_contribution_pct"] for a in assets)
    assert total == pytest.approx(1.0, abs=1e-9)


def test_risk_contributions_sum_to_the_decomposition_volatility(client: TestClient) -> None:
    result = _portfolio(client)
    total = sum(a["risk_contribution"] for a in result["asset_stats"])
    assert total == pytest.approx(result["portfolio_stats"]["decomposition_volatility"], abs=1e-9)


def test_return_contribution_shares_sum_to_one(client: TestClient) -> None:
    assets = _portfolio(client)["asset_stats"]
    total = sum(a["return_contribution_pct"] for a in assets)
    assert total == pytest.approx(1.0, abs=1e-6)


def test_weight_is_reported_alongside_risk_contribution(client: TestClient) -> None:
    """The UI shows them side by side so the divergence is visible."""
    assets = _portfolio(client, weights=[0.5, 0.3, 0.2])["asset_stats"]
    assert [a["weight"] for a in assets] == [0.5, 0.3, 0.2]
    assert all("risk_contribution_pct" in a for a in assets)


def test_the_mislabelled_contribution_field_is_gone(client: TestClient) -> None:
    assert "contribution" not in _portfolio(client)["asset_stats"][0]


# --- spec 1.7: tail risk ----------------------------------------------------


def test_tail_risk_reports_one_day_ten_day_and_full_horizon(client: TestClient) -> None:
    tails = _portfolio(client, horizon=252)["tail_risk"]
    assert set(tails) == {"d1", "d10", "horizon"}
    assert tails["d1"]["horizon_days"] == 1
    assert tails["d10"]["horizon_days"] == 10
    assert tails["horizon"]["horizon_days"] == 252


def test_the_ten_day_horizon_is_omitted_when_it_does_not_fit(client: TestClient) -> None:
    tails = _portfolio(client, horizon=5)["tail_risk"]
    assert "d10" not in tails
    assert set(tails) == {"d1", "horizon"}


def test_tail_risk_states_its_convention_and_reports_losses_positive(client: TestClient) -> None:
    horizon_tail = _portfolio(client)["tail_risk"]["horizon"]
    assert horizon_tail["convention"] == "loss_positive"
    assert horizon_tail["var_pct"] > 0.0
    assert horizon_tail["cvar_pct"] >= horizon_tail["var_pct"]
    assert horizon_tail["confidence"] == 0.95


def test_tail_risk_currency_uses_the_requested_portfolio_value(client: TestClient) -> None:
    tail = _portfolio(client, portfolio_value=250_000.0)["tail_risk"]["horizon"]
    assert tail["var_currency"] == pytest.approx(tail["var_pct"] * 250_000.0, rel=1e-9)


def test_a_longer_horizon_produces_a_larger_var(client: TestClient) -> None:
    short = _portfolio(client, horizon=63)["tail_risk"]["horizon"]["var_pct"]
    long = _portfolio(client, horizon=504)["tail_risk"]["horizon"]["var_pct"]
    assert long > short


# --- validation -------------------------------------------------------------


def test_duplicate_tickers_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio", json={"tickers": ["AAA", "AAA"], "random_seed": 1}
    )
    assert response.status_code == 422


def test_weights_that_do_not_sum_to_one_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio",
        json={"tickers": TICKERS, "weights": [0.5, 0.3, 0.1]},
    )
    assert response.status_code == 400
    assert "sum to 1" in response.json()["detail"]


def test_negative_weights_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio",
        json={"tickers": TICKERS, "weights": [1.2, 0.2, -0.4]},
    )
    assert response.status_code == 400


def test_a_weight_count_mismatch_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio", json={"tickers": TICKERS, "weights": [0.5, 0.5]}
    )
    assert response.status_code == 400


def test_an_unknown_ticker_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio", json={"tickers": ["AAA", "NOPE"], "random_seed": 1}
    )
    assert response.status_code == 404


def test_equal_weights_are_the_default(client: TestClient) -> None:
    response = client.post(
        "/api/simulate-portfolio", json={"tickers": TICKERS, "random_seed": 1}
    )
    assert response.json()["weights"] == pytest.approx([1 / 3, 1 / 3, 1 / 3])


# --- reproducibility and payload hygiene ------------------------------------


def test_the_same_seed_produces_a_byte_identical_payload(client: TestClient) -> None:
    first = _portfolio(client, random_seed=7)
    second = _portfolio(client, random_seed=7)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_a_different_seed_produces_a_different_payload(client: TestClient) -> None:
    assert _portfolio(client, random_seed=7) != _portfolio(client, random_seed=8)


def test_the_payload_contains_no_non_finite_numbers(client: TestClient) -> None:
    """NaN and Infinity are not valid JSON and break JSON.parse in the browser."""
    raw = client.post(
        "/api/simulate-portfolio",
        json={"tickers": TICKERS, "num_paths": 200, "random_seed": 3},
    ).text
    for token in ("NaN", "Infinity", "-Infinity"):
        assert token not in raw


def test_data_quality_is_reported_per_ticker(client: TestClient) -> None:
    quality = _portfolio(client)["data_quality"]
    assert set(quality) == set(TICKERS)
    assert quality["AAA"]["rows_in"] >= quality["AAA"]["rows_out"]


# --- single-asset endpoint --------------------------------------------------


def test_the_single_asset_endpoint_returns_server_side_percentiles(client: TestClient) -> None:
    response = client.post(
        "/api/simulate",
        json={"ticker": "AAA", "years": 3, "horizon": 252, "num_paths": 400, "model": "gaussian"},
    )
    assert response.status_code == 200
    result = response.json()
    assert set(result["percentiles"]) == {
        "p1", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99"
    }
    assert len(result["final_returns"]) == 400
    assert "paths_chart_sample" in result
    assert "paths_sample" not in result


def test_the_single_asset_gmm_branch_no_longer_clips_or_demeans(client: TestClient) -> None:
    """Spec 1.3: clipping to +/-12% capped the terminal spread; demeaning killed drift."""
    response = client.post(
        "/api/simulate",
        json={"ticker": "AAA", "years": 3, "horizon": 252, "num_paths": 1000, "model": "gmm"},
    )
    assert response.status_code == 200
    result = response.json()
    spread = result["percentiles"]["p99"] - result["percentiles"]["p1"]
    assert spread > 0.10


def test_all_three_single_asset_models_respond(client: TestClient) -> None:
    for model in ("gaussian", "gmm", "ewma"):
        response = client.post(
            "/api/simulate",
            json={"ticker": "AAA", "horizon": 60, "num_paths": 200, "model": model},
        )
        assert response.status_code == 200, f"{model}: {response.text}"


def test_health_and_root_endpoints_respond(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/ping").json() == {"status": "ok"}
    assert client.get("/api/health").json()["status"] == "healthy"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_api.py -v
```

Expected: widespread failures — `KeyError: 'percentiles'`, `422` for `correlation_model`, and the presence of `portfolio_paths_sample`.

- [ ] **Step 3: Rewrite `backend/main.py`**

Replace the file in full:

```python
"""Market Scenario Generator API.

A thin composition root. It validates requests, fetches and screens prices, creates
exactly one numpy Generator per request, delegates every calculation to `src/`, and
serialises the result. No statistic is computed in this file.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from src.contributions import (
    COVARIANCE_SUBSAMPLE_PATHS,
    annualized_covariance,
    return_contributions,
    risk_contributions,
)
from src.correlation import (
    cholesky_factor,
    compute_correlation_matrix,
    simulate_correlated_returns,
)
from src.data_download import download_price_data
from src.data_quality import DataQualityReport, screen_price_series
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol, sample_ewma_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm
from src.joint_models import describe_mixture, fit_joint_gmm, sample_joint_gmm
from src.portfolio_math import RebalanceRule, build_portfolio_paths
from src.returns_preprocess import compute_log_returns
from src.risk_free import get_risk_free_rate
from src.risk_metrics import (
    TRADING_DAYS_PER_YEAR,
    TailRisk,
    annualized_return,
    calmar_ratio,
    daily_returns_from_paths,
    horizon_returns,
    max_drawdown,
    percentiles,
    sharpe_ratio,
    sortino_ratio,
    tail_risk,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_TTL = 3600
PORTFOLIO_CHART_SAMPLE_PATHS = 30
SINGLE_ASSET_CHART_SAMPLE_PATHS = 50
VAR_CONFIDENCE = 0.95
BASEL_HORIZON_DAYS = 10
DEFAULT_GMM_SEED = 42

app = FastAPI(
    title="Market Scenario Generator API",
    description="Portfolio risk simulation with multi-asset correlation",
    version="3.0.0",
)

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=2)

# Cache: key -> (screened prices, quality report, fetch timestamp)
_price_cache: dict[str, tuple[pd.DataFrame, DataQualityReport, float]] = {}


def get_cached_price_data(ticker: str, years: int) -> tuple[pd.DataFrame, DataQualityReport]:
    """Fetch, screen, and cache one ticker's price history."""
    key = f"{ticker}:{years}y"
    now = time.time()
    cached = _price_cache.get(key)
    if cached is not None and now - cached[2] < CACHE_TTL:
        return cached[0], cached[1]

    screened, report = screen_price_series(download_price_data(ticker, years), ticker)
    _price_cache[key] = (screened, report, now)
    return screened, report


# ============================================================================
# Shared response models
# ============================================================================


class Percentiles(BaseModel):
    """Terminal-return ladder, always computed from the full path set (spec 1.1)."""

    p1: float
    p5: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float


class TailRiskOut(BaseModel):
    """VaR and CVaR with confidence, horizon, and sign convention attached."""

    confidence: float
    horizon_days: int
    var_pct: float
    var_currency: float
    cvar_pct: float
    cvar_currency: float
    cvar_var_ratio: float | None
    convention: Literal["loss_positive"] = "loss_positive"


class DataQualityOut(BaseModel):
    rows_in: int
    rows_out: int
    non_finite_price_days: int
    non_positive_price_days: int
    zero_volume_days: int
    stale_price_days: int
    split_artifact_days: int


def _finite_or_none(value: float) -> float | None:
    """NaN and Infinity are not valid JSON; emit null instead."""
    return float(value) if np.isfinite(value) else None


def _tail_risk_out(metric: TailRisk) -> TailRiskOut:
    return TailRiskOut(
        confidence=metric.confidence,
        horizon_days=metric.horizon_days,
        var_pct=metric.var_pct,
        var_currency=metric.var_currency,
        cvar_pct=metric.cvar_pct,
        cvar_currency=metric.cvar_currency,
        cvar_var_ratio=_finite_or_none(metric.cvar_var_ratio),
    )


def _quality_out(report: DataQualityReport) -> DataQualityOut:
    return DataQualityOut(
        rows_in=report.rows_in,
        rows_out=report.rows_out,
        non_finite_price_days=report.non_finite_price_days,
        non_positive_price_days=report.non_positive_price_days,
        zero_volume_days=report.zero_volume_days,
        stale_price_days=report.stale_price_days,
        split_artifact_days=report.split_artifact_days,
    )


def _tail_risk_by_horizon(
    portfolio_paths: np.ndarray,
    final_returns: np.ndarray,
    horizon: int,
    portfolio_value: float,
) -> dict[str, TailRiskOut]:
    """1-day, 10-day (Basel), and full-horizon tail risk from non-overlapping windows."""
    tails = {
        "d1": tail_risk(
            horizon_returns(portfolio_paths, 1), VAR_CONFIDENCE, 1, portfolio_value
        ),
        "horizon": tail_risk(final_returns, VAR_CONFIDENCE, horizon, portfolio_value),
    }
    if horizon >= BASEL_HORIZON_DAYS:
        tails["d10"] = tail_risk(
            horizon_returns(portfolio_paths, BASEL_HORIZON_DAYS),
            VAR_CONFIDENCE,
            BASEL_HORIZON_DAYS,
            portfolio_value,
        )
    return {key: _tail_risk_out(value) for key, value in tails.items()}


# ============================================================================
# Single-asset models
# ============================================================================


class SimulationRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    years: int = Field(3, ge=1, le=10)
    horizon: int = Field(252, ge=1, le=1000)
    num_paths: int = Field(1000, ge=100, le=10000)
    model: Literal["gaussian", "gmm", "ewma"] = Field("gaussian")
    portfolio_value: float = Field(100_000.0, gt=0.0)
    random_seed: int | None = Field(42)


class RiskStats(BaseModel):
    mean: float
    median: float
    vol: float
    prob_loss: float


class SimulationResponse(BaseModel):
    ticker: str
    model: str
    start_price: float
    horizon_days: int
    num_paths: int
    final_prices: list[float]
    final_returns: list[float]
    percentiles: Percentiles
    tail_risk: dict[str, TailRiskOut]
    risk_stats: RiskStats
    paths_chart_sample: list[list[float]]
    data_quality: DataQualityOut
    message: str


# ============================================================================
# Portfolio models
# ============================================================================


class PortfolioSimulationRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=2, max_length=10)
    weights: list[float] | None = Field(None, description="Must sum to 1 and be non-negative")
    years: int = Field(3, ge=1, le=10)
    horizon: int = Field(252, ge=1, le=1000)
    num_paths: int = Field(1000, ge=100, le=5000)
    correlation_model: Literal["gaussian", "gmm_joint", "t_copula"] = "gaussian"
    gmm_components: int = Field(3, ge=2, le=6)
    rebalance: RebalanceRule = "buy_and_hold"
    rebalance_band: float | None = Field(None, ge=0.0, le=1.0)
    transaction_cost_bps: float = Field(0.0, ge=0.0, le=500.0)
    risk_free_rate: float | None = Field(None, ge=-0.05, le=0.25)
    portfolio_value: float = Field(100_000.0, gt=0.0)
    random_seed: int | None = Field(42)

    @field_validator("tickers")
    @classmethod
    def _normalise_and_reject_duplicates(cls, value: list[str]) -> list[str]:
        normalised = [ticker.strip().upper() for ticker in value]
        if len(set(normalised)) != len(normalised):
            raise ValueError("tickers must be unique")
        return normalised


class AssetStats(BaseModel):
    ticker: str
    start_price: float
    weight: float
    final_mean_return: float
    return_contribution_pct: float | None
    marginal_risk: float
    risk_contribution: float
    risk_contribution_pct: float


class PortfolioRiskStats(BaseModel):
    mean_return: float
    median_return: float
    annualized_return: float
    volatility: float
    decomposition_volatility: float
    prob_loss: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    median_max_drawdown: float
    max_return: float
    min_return: float
    risk_free_rate: float
    risk_free_source: str


class MixtureComponentOut(BaseModel):
    weight: float
    means: list[float]
    covariance: list[list[float]]


class PortfolioSimulationResponse(BaseModel):
    tickers: list[str]
    weights: list[float]
    correlation_model: str
    rebalance: str
    transaction_cost_bps: float
    horizon_days: int
    num_paths: int
    correlation_matrix: dict[str, dict[str, float]]
    percentiles: Percentiles
    tail_risk: dict[str, TailRiskOut]
    portfolio_paths_chart_sample: list[list[float]]
    asset_paths_chart_sample: dict[str, list[list[float]]]
    asset_stats: list[AssetStats]
    portfolio_stats: PortfolioRiskStats
    mixture_components: list[MixtureComponentOut] | None
    data_quality: dict[str, DataQualityOut]
    message: str


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/")
def root() -> dict[str, object]:
    return {
        "status": "running",
        "version": "3.0.0",
        "features": ["single-asset", "multi-asset-portfolio", "joint-gmm", "rebalancing"],
    }


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "version": "3.0.0"}


@app.post("/api/simulate", response_model=SimulationResponse)
async def simulate_scenarios(request: SimulationRequest) -> SimulationResponse:
    """Single-asset simulation."""
    rng = np.random.default_rng(request.random_seed)
    seed = DEFAULT_GMM_SEED if request.random_seed is None else request.random_seed

    def _run() -> SimulationResponse:
        prices, quality = get_cached_price_data(request.ticker, request.years)
        if prices.empty or len(prices) < 50:
            raise ValueError(f"Insufficient data for {request.ticker}: {len(prices)} rows")

        log_returns = compute_log_returns(prices)
        start_price = float(prices["price"].iloc[-1])

        if request.model == "gaussian":
            mu, sigma = fit_gaussian(log_returns)
            # Ito correction: the drift of ln(S) is mu - sigma^2 / 2.
            returns_matrix = sample_gaussian(
                mu - 0.5 * sigma**2, sigma, request.horizon, request.num_paths, rng
            )
        elif request.model == "gmm":
            gmm = fit_gmm(log_returns, n_components=3, seed=seed)
            returns_matrix = sample_gmm(gmm, request.horizon, request.num_paths, rng)
        else:
            ewma_series = compute_ewma_vol(log_returns)
            vol_forecast = forecast_ewma_vol(
                float(ewma_series.iloc[-1]), lam=0.94, horizon=request.horizon
            )
            adjusted_mu = float(log_returns.mean()) - 0.5 * float(np.mean(vol_forecast**2))
            returns_matrix = sample_ewma_returns(
                adjusted_mu, vol_forecast, request.num_paths, rng
            )

        paths = start_price * np.exp(np.cumsum(returns_matrix, axis=1))
        final_prices = paths[:, -1]
        final_returns = final_prices / start_price - 1.0
        value_paths = paths / start_price

        annualized_vol = float(
            daily_returns_from_paths(value_paths).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        )

        return SimulationResponse(
            ticker=request.ticker,
            model=request.model,
            start_price=start_price,
            horizon_days=request.horizon,
            num_paths=request.num_paths,
            final_prices=final_prices.tolist(),
            final_returns=final_returns.tolist(),
            percentiles=Percentiles(**percentiles(final_returns)),
            tail_risk=_tail_risk_by_horizon(
                value_paths, final_returns, request.horizon, request.portfolio_value
            ),
            risk_stats=RiskStats(
                mean=float(final_returns.mean()),
                median=float(np.median(final_returns)),
                vol=annualized_vol,
                prob_loss=float((final_returns < 0).mean()),
            ),
            paths_chart_sample=paths[:SINGLE_ASSET_CHART_SAMPLE_PATHS].tolist(),
            data_quality=_quality_out(quality),
            message=f"Simulated {request.num_paths} paths over {request.horizon} trading days",
        )

    return await _execute(_run)


def _resolve_weights(request: PortfolioSimulationRequest) -> np.ndarray:
    """Validate weights at the API boundary, where a 400 is the right answer."""
    count = len(request.tickers)
    if request.weights is None:
        return np.ones(count) / count

    if len(request.weights) != count:
        raise HTTPException(
            status_code=400,
            detail=f"Expected {count} weights to match {count} tickers, got {len(request.weights)}",
        )

    weights = np.asarray(request.weights, dtype=float)
    if not np.isclose(weights.sum(), 1.0):
        raise HTTPException(
            status_code=400, detail=f"Weights must sum to 1.0, got {weights.sum():.6f}"
        )
    if np.any(weights < 0.0):
        raise HTTPException(
            status_code=400,
            detail="Weights must be non-negative: short positions are out of scope",
        )
    return weights


@app.post("/api/simulate-portfolio", response_model=PortfolioSimulationResponse)
async def simulate_portfolio(
    request: PortfolioSimulationRequest,
) -> PortfolioSimulationResponse:
    """Multi-asset portfolio simulation with correlation and explicit rebalancing."""
    if request.correlation_model == "t_copula":
        raise HTTPException(
            status_code=501,
            detail=(
                "correlation_model 't_copula' is declared but not implemented. "
                "Use 'gaussian' or 'gmm_joint'."
            ),
        )

    weights = _resolve_weights(request)
    rng = np.random.default_rng(request.random_seed)
    seed = DEFAULT_GMM_SEED if request.random_seed is None else request.random_seed

    def _run() -> PortfolioSimulationResponse:
        fetched: dict[str, tuple[pd.DataFrame, DataQualityReport]] = {}
        unavailable: list[str] = []
        for ticker in request.tickers:
            try:
                fetched[ticker] = get_cached_price_data(ticker, request.years)
            except Exception as exc:  # noqa: BLE001 - reported as 404 below
                logger.warning("price fetch failed for %s: %s", ticker, exc)
                unavailable.append(ticker)

        price_data = {t: frame for t, (frame, _) in fetched.items() if not frame.empty}
        unavailable.extend(t for t in request.tickers if t not in price_data)
        if unavailable:
            raise HTTPException(
                status_code=404, detail=f"Failed to download: {sorted(set(unavailable))}"
            )

        returns_df, corr_matrix = compute_correlation_matrix(price_data, request.tickers)
        start_prices = np.array(
            [float(price_data[t]["price"].iloc[-1]) for t in request.tickers], dtype=float
        )

        mixture: list[MixtureComponentOut] | None = None
        if request.correlation_model == "gaussian":
            count = len(request.tickers)
            means = np.empty(count)
            stds = np.empty(count)
            for i, ticker in enumerate(request.tickers):
                mu, sigma = fit_gaussian(returns_df[ticker])
                # Ito correction: the drift of ln(S) is mu - sigma^2 / 2.
                means[i] = mu - 0.5 * sigma**2
                stds[i] = sigma
            log_returns = simulate_correlated_returns(
                means,
                stds,
                cholesky_factor(corr_matrix),
                request.horizon,
                request.num_paths,
                rng,
            )
        else:
            gmm = fit_joint_gmm(returns_df, n_components=request.gmm_components, seed=seed)
            log_returns = sample_joint_gmm(gmm, request.horizon, request.num_paths, rng)
            mixture = [
                MixtureComponentOut(
                    weight=component.weight,
                    means=component.means,
                    covariance=component.covariance,
                )
                for component in describe_mixture(gmm)
            ]

        asset_paths, portfolio_paths = build_portfolio_paths(
            start_prices,
            log_returns,
            weights,
            rebalance=request.rebalance,
            rebalance_band=request.rebalance_band,
            transaction_cost_bps=request.transaction_cost_bps,
        )

        final_returns = portfolio_paths[:, -1] - 1.0
        daily_portfolio_returns = daily_returns_from_paths(portfolio_paths)
        annualized_vol = float(
            daily_portfolio_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
        mean_return = float(final_returns.mean())
        drawdowns = max_drawdown(portfolio_paths)
        median_drawdown = float(np.median(drawdowns))
        risk_free = get_risk_free_rate(request.risk_free_rate)

        # Covariance of the simulated returns actually used, on a deterministic
        # leading subsample so peak memory does not scale with num_paths.
        covariance = annualized_covariance(
            np.expm1(log_returns[:COVARIANCE_SUBSAMPLE_PATHS])
        )
        marginal, contribution, decomposition_vol = risk_contributions(weights, covariance)

        asset_mean_returns = np.array(
            [
                float((asset_paths[:, -1, i] / start_prices[i] - 1.0).mean())
                for i in range(len(request.tickers))
            ]
        )
        share_of_return = return_contributions(weights, asset_mean_returns, mean_return)

        asset_stats = [
            AssetStats(
                ticker=ticker,
                start_price=float(start_prices[i]),
                weight=float(weights[i]),
                final_mean_return=float(asset_mean_returns[i]),
                return_contribution_pct=_finite_or_none(share_of_return[i]),
                marginal_risk=float(marginal[i]),
                risk_contribution=float(contribution[i]),
                risk_contribution_pct=(
                    float(contribution[i] / decomposition_vol) if decomposition_vol > 0 else 0.0
                ),
            )
            for i, ticker in enumerate(request.tickers)
        ]

        return PortfolioSimulationResponse(
            tickers=request.tickers,
            weights=weights.tolist(),
            correlation_model=request.correlation_model,
            rebalance=request.rebalance,
            transaction_cost_bps=request.transaction_cost_bps,
            horizon_days=request.horizon,
            num_paths=request.num_paths,
            correlation_matrix={
                row: {col: float(corr_matrix.loc[row, col]) for col in request.tickers}
                for row in request.tickers
            },
            percentiles=Percentiles(**percentiles(final_returns)),
            tail_risk=_tail_risk_by_horizon(
                portfolio_paths, final_returns, request.horizon, request.portfolio_value
            ),
            portfolio_paths_chart_sample=portfolio_paths[
                :PORTFOLIO_CHART_SAMPLE_PATHS
            ].tolist(),
            asset_paths_chart_sample={
                ticker: asset_paths[:PORTFOLIO_CHART_SAMPLE_PATHS, :, i].tolist()
                for i, ticker in enumerate(request.tickers)
            },
            asset_stats=asset_stats,
            portfolio_stats=PortfolioRiskStats(
                mean_return=mean_return,
                median_return=float(np.median(final_returns)),
                annualized_return=annualized_return(mean_return, request.horizon),
                volatility=annualized_vol,
                decomposition_volatility=decomposition_vol,
                prob_loss=float((final_returns < 0).mean()),
                sharpe_ratio=sharpe_ratio(
                    mean_return, request.horizon, annualized_vol, risk_free.value
                ),
                sortino_ratio=sortino_ratio(
                    mean_return, request.horizon, daily_portfolio_returns, risk_free.value
                ),
                calmar_ratio=calmar_ratio(mean_return, request.horizon, median_drawdown),
                median_max_drawdown=median_drawdown,
                max_return=float(final_returns.max()),
                min_return=float(final_returns.min()),
                risk_free_rate=risk_free.value,
                risk_free_source=risk_free.source,
            ),
            mixture_components=mixture,
            data_quality={
                ticker: _quality_out(report) for ticker, (_, report) in fetched.items()
            },
            message=(
                f"Simulated {len(request.tickers)} assets over {request.horizon} trading "
                f"days with {request.num_paths} paths "
                f"({request.correlation_model}, {request.rebalance})"
            ),
        )

    return await _execute(_run)


async def _execute(work: object) -> object:
    """Run a blocking simulation off the event loop with uniform error mapping."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_executor, work)  # type: ignore[arg-type]
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("simulation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

`_execute` is deliberately loosely typed because it wraps two different return types; if mypy objects to the `object` annotation, make it generic instead:

```python
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


async def _execute(work: Callable[[], T]) -> T:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_executor, work)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("simulation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
```

Use the generic version — it is the correct signature and removes the `type: ignore`.

- [ ] **Step 4: Delete the superseded functions from `correlation.py`**

Remove `build_portfolio_paths` (superseded by `src/portfolio_math.build_portfolio_paths`, which aggregates in simple-return space) and `compute_portfolio_risk_stats` (superseded by `src/risk_metrics`, which fixes the Sharpe defect). Nothing imports them after Step 3 — confirm before deleting:

```bash
backend/env/Scripts/python.exe -m ruff check --select F401 . && grep -rn "compute_portfolio_risk_stats\|from src.correlation import" backend --include=*.py
```

Expected: the only `src.correlation` imports are `cholesky_factor`, `compute_correlation_matrix`, `simulate_correlated_returns`, and no hit for `compute_portfolio_risk_stats` outside the file being edited.

- [ ] **Step 5: Remove `main.py` from the mypy exclude**

In `pyproject.toml`, delete `backend/main\\.py` from the `[tool.mypy] exclude` pattern. The exclude should now list only the four dead scripts.

- [ ] **Step 6: Run the API tests**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_api.py -v
```

Expected: 43 passed. Two failures worth anticipating:

- `test_the_gmm_produces_a_fatter_tail_than_the_gaussian` is a statistical comparison on synthetic Gaussian fixture data, where there is no real second regime to find. If it fails, change the fixture to inject a crisis block — reuse the `_two_regime_returns` construction from `test_joint_models.py` to build the price frames — rather than weakening the assertion. The claim being tested is real and must be tested against data that contains the phenomenon.
- `test_the_payload_contains_no_non_finite_numbers` catches any missed `_finite_or_none` call site.

- [ ] **Step 7: Run the full gate**

```bash
backend/env/Scripts/python.exe -m pytest && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

Expected: all pass, with mypy now covering `main.py`.

- [ ] **Step 8: Verify the server actually starts**

The test client does not exercise app startup or the CORS middleware.

```bash
backend/env/Scripts/python.exe -c "import sys; sys.path.insert(0, 'backend'); import main; print('routes:', sorted(r.path for r in main.app.routes))"
```

Expected: the five paths `/`, `/api/health`, `/api/simulate`, `/api/simulate-portfolio`, `/ping` among the listed routes.

- [ ] **Step 9: Append the API-contract section to `docs/METHODOLOGY.md`**

```markdown
## API response contract

**One Generator per request.** Each handler constructs
`np.random.default_rng(request.random_seed)` before dispatching to the thread pool
and threads it into every sampling call. Two concurrent requests with the same seed
return identical payloads; a test asserts byte-identical JSON.

**Statistics are computed server-side, from complete arrays.** The client computes
no percentile, no ratio, and no tail statistic. `portfolio_paths_chart_sample` and
`paths_chart_sample` are named for their only purpose — rendering — and are capped at
30 and 50 paths respectively.

**Volatility is reported twice, deliberately.**

- `volatility` is the realised annualised volatility of the simulated portfolio value
  path. It reflects the rebalancing rule actually applied, including weight drift
  under buy-and-hold.
- `decomposition_volatility` is `sqrt(w' S w)` for the fixed target weights, the
  quantity the risk contributions sum to by construction.

Under `buy_and_hold` the two differ, because weights drift away from `w` as the
simulation proceeds. Reporting both makes the gap visible instead of implying a
precision that is not there. Risk contributions sum to `decomposition_volatility`,
and a test asserts it to 1e-9.

**Non-finite values are never emitted.** `NaN` and `Infinity` are not valid JSON and
break `JSON.parse`. Any statistic that is genuinely undefined — a return contribution
when the portfolio return is within 1e-12 of zero, a CVaR/VaR ratio when VaR is zero —
is serialised as `null`, not coerced to `0.0`. A test greps the raw response body for
those three tokens.

**Error mapping.** `400` for weight violations (count mismatch, not summing to 1,
negative); `404` for a ticker that could not be fetched; `422` for pydantic validation
and for a `ValueError` from an estimator (insufficient history, too few observations
for the requested component count); `501` for `correlation_model: "t_copula"`, which
is declared and deliberately unimplemented rather than silently falling back to
Gaussian; `500` otherwise, with the traceback logged.
```

- [ ] **Step 10: Commit**

```bash
git add backend/main.py backend/src/correlation.py backend/tests/test_api.py pyproject.toml docs/METHODOLOGY.md
git commit -m "fix: compute all percentiles server-side and expose the full risk response surface"
```

---

### Task 11: Performance budget and concurrent determinism

Implements the two remaining Definition-of-Done items that are properties of the system rather than of any one function: the 5000 x 10 x 1000 budget (spec 1.8) and byte-identical output under concurrent load (spec Phase 0.4).

**Files:**
- Create: `backend/tests/test_performance.py`
- Create: `backend/tests/test_determinism.py`
- Modify: `docs/METHODOLOGY.md`

**Interfaces:**
- Consumes: `simulate_correlated_returns` (Task 4), `build_portfolio_paths` (Task 6), the `/api/simulate-portfolio` endpoint (Task 10), the `client` fixture pattern from `test_api.py`.
- Produces: no source changes unless the budget is missed.

- [ ] **Step 1: Write the performance test**

`backend/tests/test_performance.py`. Marked `benchmark` so the default suite stays fast, and skipped when the machine cannot hold the arrays — a memory failure would otherwise look like a performance regression:

```python
"""Performance budget for spec 1.8: 5000 paths x 10 assets x 1000 days under 2 seconds."""

from __future__ import annotations

import time

import numpy as np
import pytest

from src.portfolio_math import build_portfolio_paths

NUM_PATHS = 5_000
N_ASSETS = 10
HORIZON = 1_000
BUDGET_SECONDS = 2.0

# Two float64 arrays of this shape, plus headroom.
_REQUIRED_BYTES = NUM_PATHS * HORIZON * N_ASSETS * 8 * 3


def _has_memory() -> bool:
    try:
        probe = np.empty(NUM_PATHS * HORIZON * N_ASSETS, dtype=np.float64)
    except MemoryError:
        return False
    del probe
    return True


pytestmark = pytest.mark.benchmark


@pytest.mark.skipif(not _has_memory(), reason="insufficient memory for the benchmark config")
def test_full_simulation_kernel_meets_the_two_second_budget() -> None:
    """Sampling plus portfolio construction, the whole numerical kernel."""
    from src.correlation import cholesky_factor
    import pandas as pd

    tickers = [f"A{i}" for i in range(N_ASSETS)]
    corr = np.full((N_ASSETS, N_ASSETS), 0.4)
    np.fill_diagonal(corr, 1.0)
    chol = cholesky_factor(pd.DataFrame(corr, index=tickers, columns=tickers))

    means = np.full(N_ASSETS, 0.0003)
    stds = np.full(N_ASSETS, 0.012)
    weights = np.full(N_ASSETS, 1.0 / N_ASSETS)
    start_prices = np.full(N_ASSETS, 100.0)
    rng = np.random.default_rng(1)

    from src.correlation import simulate_correlated_returns

    started = time.perf_counter()
    log_returns = simulate_correlated_returns(means, stds, chol, HORIZON, NUM_PATHS, rng)
    _, portfolio_paths = build_portfolio_paths(
        start_prices, log_returns, weights, rebalance="buy_and_hold"
    )
    elapsed = time.perf_counter() - started

    assert portfolio_paths.shape == (NUM_PATHS, HORIZON)
    assert elapsed < BUDGET_SECONDS, f"kernel took {elapsed:.2f}s, budget {BUDGET_SECONDS}s"


@pytest.mark.skipif(not _has_memory(), reason="insufficient memory for the benchmark config")
def test_daily_rebalancing_closed_form_meets_the_budget() -> None:
    """The other vectorised branch. The stepwise loop is not held to this budget."""
    rng = np.random.default_rng(2)
    log_returns = rng.normal(0.0003, 0.012, size=(NUM_PATHS, HORIZON, N_ASSETS))
    weights = np.full(N_ASSETS, 1.0 / N_ASSETS)
    start_prices = np.full(N_ASSETS, 100.0)

    started = time.perf_counter()
    build_portfolio_paths(start_prices, log_returns, weights, rebalance="daily")
    elapsed = time.perf_counter() - started

    assert elapsed < BUDGET_SECONDS, f"daily branch took {elapsed:.2f}s"


def test_the_vectorised_sampler_is_far_faster_than_the_loop_it_replaced() -> None:
    """Small config, no skip: proves the speedup rather than assuming it."""
    from src.correlation import simulate_correlated_returns

    n_assets, horizon, num_paths = 5, 200, 200
    chol = np.linalg.cholesky(np.eye(n_assets) * 0.9 + 0.1)
    means = np.zeros(n_assets)
    stds = np.full(n_assets, 0.01)

    started = time.perf_counter()
    simulate_correlated_returns(
        means, stds, chol, horizon, num_paths, np.random.default_rng(3)
    )
    vectorised = time.perf_counter() - started

    z = np.random.default_rng(3).standard_normal((num_paths, horizon, n_assets))
    started = time.perf_counter()
    reference = np.zeros_like(z)
    for path in range(num_paths):
        for t in range(horizon):
            reference[path, t, :] = chol @ z[path, t, :]
    looped = time.perf_counter() - started

    assert vectorised < looped / 10.0, f"vectorised {vectorised:.4f}s vs loop {looped:.4f}s"
```

- [ ] **Step 2: Run the benchmark**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_performance.py -v -m benchmark --no-header
```

Expected: passed, with the elapsed time under 2 seconds. If the budget is missed, the fix is in the code, not the assertion. In order of expected payoff:

1. Confirm `build_portfolio_paths` is taking the `buy_and_hold` branch (`asset_paths @ units`, one BLAS call) and not the stepwise loop.
2. Confirm `asset_price_paths` uses the in-place form (`np.exp(paths, out=paths)`); the naive `start * np.exp(np.cumsum(...))` allocates three arrays instead of one and is memory-bandwidth-bound at this size.
3. Confirm `_MAX_CHUNK_ELEMENTS` is not so small that the chunk loop dominates.

Do not raise `BUDGET_SECONDS` and do not shrink the config — both are specified in the spec's Definition of Done.

- [ ] **Step 3: Write the concurrency determinism test**

`backend/tests/test_determinism.py`. This is the regression test for the `ThreadPoolExecutor` race, and it must fail against the old global-seed implementation:

```python
"""Spec Phase 0.4: identical seeds must produce identical output under concurrent load."""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

TICKERS = ["AAA", "BBB", "CCC"]


@pytest.fixture
def client(
    monkeypatch: Any,
    make_correlated_prices: Callable[..., dict[str, pd.DataFrame]],
) -> TestClient:
    import main
    from src.data_quality import screen_price_series
    from src.risk_free import RiskFreeRate

    prices = make_correlated_prices(TICKERS, target_corr=0.45, n_days=900)

    def _provider(ticker: str, years: int) -> tuple[pd.DataFrame, Any]:
        if ticker not in prices:
            raise ValueError(f"No data returned for ticker {ticker}")
        return screen_price_series(prices[ticker], ticker)

    monkeypatch.setattr(main, "get_cached_price_data", _provider)
    monkeypatch.setattr(
        main,
        "get_risk_free_rate",
        lambda user_value=None, now=None: RiskFreeRate(value=0.04, source="fallback"),
    )
    return TestClient(main.app)


def _body(seed: int) -> dict[str, Any]:
    return {
        "tickers": TICKERS,
        "weights": [0.5, 0.3, 0.2],
        "horizon": 120,
        "num_paths": 300,
        "correlation_model": "gaussian",
        "random_seed": seed,
    }


def _post(client: TestClient, seed: int) -> str:
    response = client.post("/api/simulate-portfolio", json=_body(seed))
    assert response.status_code == 200, response.text
    return json.dumps(response.json(), sort_keys=True)


def test_concurrent_requests_with_the_same_seed_are_byte_identical(
    client: TestClient,
) -> None:
    """The old np.random.seed inside a ThreadPoolExecutor could not guarantee this."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        payloads = list(pool.map(lambda _: _post(client, 42), range(12)))

    assert len(set(payloads)) == 1, "same seed produced different payloads under load"


def test_interleaved_seeds_do_not_contaminate_each_other(client: TestClient) -> None:
    """Two seeds hammered concurrently: each must stay self-consistent."""
    seeds = [1, 2] * 8

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda seed: (seed, _post(client, seed)), seeds))

    by_seed: dict[int, set[str]] = {}
    for seed, payload in results:
        by_seed.setdefault(seed, set()).add(payload)

    assert len(by_seed[1]) == 1, "seed 1 was contaminated by concurrent seed 2"
    assert len(by_seed[2]) == 1, "seed 2 was contaminated by concurrent seed 1"
    assert by_seed[1] != by_seed[2], "different seeds produced identical output"


def test_concurrent_gmm_requests_are_also_deterministic(client: TestClient) -> None:
    """The GMM path samples its mixture by hand; it must be equally isolated."""

    def _gmm(_: int) -> str:
        response = client.post(
            "/api/simulate-portfolio",
            json={**_body(5), "correlation_model": "gmm_joint", "gmm_components": 2},
        )
        assert response.status_code == 200, response.text
        return json.dumps(response.json(), sort_keys=True)

    with ThreadPoolExecutor(max_workers=6) as pool:
        payloads = list(pool.map(_gmm, range(8)))

    assert len(set(payloads)) == 1


def test_sequential_repeats_match_concurrent_results(client: TestClient) -> None:
    """Concurrency must not change the answer, only the timing."""
    sequential = _post(client, 99)
    with ThreadPoolExecutor(max_workers=6) as pool:
        concurrent = set(pool.map(lambda _: _post(client, 99), range(6)))

    assert concurrent == {sequential}
```

- [ ] **Step 4: Run the determinism tests**

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_determinism.py -v
```

Expected: 4 passed. A failure here means a `np.random.*` module-level call survived somewhere in the request path — find it with the grep guard from Task 2 and with `git log -S "np.random." --oneline`.

- [ ] **Step 5: Run the full suite including benchmarks**

```bash
backend/env/Scripts/python.exe -m pytest -m "not benchmark" && backend/env/Scripts/python.exe -m pytest -m benchmark
```

Expected: both green. The split is how the suite will be run in CI later (spec Phase 5): fast tests on every push, benchmarks on demand.

- [ ] **Step 6: Append the performance section to `docs/METHODOLOGY.md`**

```markdown
## Performance and memory

**Budget.** A 5000-path, 10-asset, 1000-day simulation completes the numerical kernel
(correlated sampling plus portfolio construction) in under 2 seconds. A benchmark test
asserts it.

**What made it slow.** `simulate_correlated_returns` looped
`for path in range(num_paths): for t in range(horizon):`, performing
`num_paths x horizon` Python-level matrix-vector products — 365,000 for the default
configuration and 5,000,000 for the benchmark configuration. `build_portfolio_paths`
carried the same double loop. Both are now single broadcast operations
(`Z @ L.T` and `asset_paths @ units`), which dispatch to BLAS. A test asserts the
vectorised sampler beats the loop it replaced by more than 10x on a small
configuration, so the claim is measured rather than assumed.

**Memory.** At the benchmark configuration a single `(5000, 1000, 10)` float64 array
is 400 MB. Two design choices bound the peak:

- `simulate_correlated_returns` draws the output array once and applies the Cholesky
  factor in path-chunks capped at 20 million elements, so no full-size temporary is
  ever materialised alongside the result.
- `asset_price_paths` computes `cumsum`, `exp`, and the price scaling in place, using
  one array rather than three.
- The covariance used for risk decomposition is estimated from the leading 500 paths,
  so `expm1` is never materialised over the full array.

**What breaks it.** Peak memory still scales with `num_paths x horizon x n_assets`.
The request caps (5000 paths, 1000 days, 10 assets) permit roughly 800 MB of resident
arrays, which exceeds a 512 MB container. This is recorded in "Known limitations":
production deployment should lower the `num_paths` ceiling or the platform should
provide more memory. It is a deployment constraint, not a correctness defect, and is
deliberately not fixed by silently truncating the user's requested path count.
```

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_performance.py backend/tests/test_determinism.py docs/METHODOLOGY.md
git commit -m "test: performance budget and concurrent-determinism regression tests"
```

---

### Task 12: Frontend — consume server percentiles and stop deriving statistics

Implements the client half of spec 1.1, plus the UI requirements in 1.5 (display the assumed rf), 1.6 (a "Risk Contribution" panel, not "Allocation"), and 1.7 (label VaR with its horizon).

**Files:**
- Create: `frontend/src/lib/chartSample.js`
- Create: `frontend/src/lib/chartSample.test.js`
- Create: `frontend/src/components/RiskContribution.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/package.json` (add vitest)
- Modify: `frontend/vite.config.js` (test config)

**Interfaces:**
- Consumes the Task 10 response contract: `percentiles`, `tail_risk`, `portfolio_paths_chart_sample`, `asset_paths_chart_sample`, `paths_chart_sample`, `asset_stats[].{weight,risk_contribution_pct,return_contribution_pct}`, `portfolio_stats.{risk_free_rate,risk_free_source,sortino_ratio,calmar_ratio}`.
- Produces: `markChartSample(paths)`, `assertNotChartSample(data, statName)`, `<RiskContribution assets isDark />`.

- [ ] **Step 1: Add vitest**

```bash
cd frontend && npm install --save-dev vitest
```

Add the script to `frontend/package.json`:

```json
"test": "vitest run"
```

Add the test config to `frontend/vite.config.js`, inside the existing `defineConfig` object:

```js
  test: {
    environment: 'node',
    include: ['src/**/*.test.js'],
  },
```

- [ ] **Step 2: Write the failing guard test**

`frontend/src/lib/chartSample.test.js`:

```js
import { describe, expect, it } from 'vitest';
import { assertNotChartSample, markChartSample } from './chartSample';

describe('chart sample guard', () => {
  it('marks an array without adding an enumerable property', () => {
    const paths = markChartSample([[1, 2], [3, 4]]);
    expect(Object.keys(paths)).toEqual(['0', '1']);
    expect(JSON.stringify(paths)).toBe('[[1,2],[3,4]]');
  });

  it('throws when a statistic is derived from a marked chart sample', () => {
    const paths = markChartSample([[1, 2], [3, 4]]);
    expect(() => assertNotChartSample(paths, 'percentile')).toThrow(/chart sample/i);
  });

  it('names the offending statistic in the message', () => {
    const paths = markChartSample([[1]]);
    expect(() => assertNotChartSample(paths, 'median')).toThrow(/median/);
  });

  it('lets unmarked data through and returns it unchanged', () => {
    const values = [0.1, 0.2, 0.3];
    expect(assertNotChartSample(values, 'percentile')).toBe(values);
  });

  it('tolerates null and undefined', () => {
    expect(assertNotChartSample(null, 'percentile')).toBeNull();
    expect(assertNotChartSample(undefined, 'percentile')).toBeUndefined();
    expect(markChartSample(null)).toBeNull();
  });
});
```

- [ ] **Step 3: Run it to verify it fails**

```bash
cd frontend && npm test
```

Expected: `Failed to resolve import "./chartSample"`.

- [ ] **Step 4: Write `frontend/src/lib/chartSample.js`**

```js
/**
 * Chart samples are truncated path sets sent for rendering only. Deriving a
 * statistic from one is the defect described in spec 1.1: the scenario ladder was
 * computed from 30 paths while the user had configured 1000.
 *
 * Arrays arriving in a `*_chart_sample` field are marked here, and every statistical
 * helper asserts against the mark, so the mistake throws instead of quietly
 * producing a wrong number.
 */

export const CHART_SAMPLE_FLAG = '__chartSampleOnly';

/** Mark an array as render-only. The flag is non-enumerable, so JSON is unaffected. */
export function markChartSample(paths) {
  if (!Array.isArray(paths)) return paths;
  Object.defineProperty(paths, CHART_SAMPLE_FLAG, {
    value: true,
    enumerable: false,
    configurable: true,
  });
  return paths;
}

/** Throw if `data` is a marked chart sample. Returns `data` unchanged otherwise. */
export function assertNotChartSample(data, statName) {
  if (Array.isArray(data) && data[CHART_SAMPLE_FLAG]) {
    throw new Error(
      `${statName} was derived from a chart sample. Chart samples are truncated for ` +
        'rendering; use the server-computed `percentiles` and `tail_risk` fields instead.',
    );
  }
  return data;
}
```

- [ ] **Step 5: Run the guard test**

```bash
cd frontend && npm test
```

Expected: 5 passed.

- [ ] **Step 6: Mark chart samples on arrival in `App.jsx`**

Import the helpers at the top of the file:

```js
import { assertNotChartSample, markChartSample } from './lib/chartSample';
```

In `runSimulation`, after `const data = await response.json();`:

```js
      markChartSample(data.paths_chart_sample);
      setResults(data);
```

In `runPortfolioSimulation`, after `const data = await response.json();`:

```js
      markChartSample(data.portfolio_paths_chart_sample);
      Object.values(data.asset_paths_chart_sample ?? {}).forEach(markChartSample);
      setPortfolioResults(data);
```

- [ ] **Step 7: Send the new request parameters**

In `runPortfolioSimulation`, replace the request body. The single-asset `model` toggle maps to the portfolio endpoint's `correlation_model`:

```js
      const body = {
        tickers,
        weights,
        years,
        horizon,
        num_paths: numPaths,
        correlation_model: model === 'gmm' ? 'gmm_joint' : 'gaussian',
        rebalance,
        transaction_cost_bps: transactionCostBps,
      };

      const response = await fetch(`${API_URL}/api/simulate-portfolio?t=${Date.now()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
```

Add the two new pieces of state beside the existing `model` state:

```js
  const [rebalance, setRebalance] = useState('buy_and_hold');
  const [transactionCostBps, setTransactionCostBps] = useState(0);
```

Render a rebalance selector in the portfolio configuration panel, next to the existing controls and styled to match them:

```jsx
              <div>
                <label className={`block text-xs font-semibold mb-2 uppercase tracking-wider ${textSub}`}>
                  Rebalancing
                  <InfoTooltip
                    text="Buy-and-hold lets weights drift. Daily rebalancing harvests a rebalancing premium a real portfolio does not earn for free."
                    isDark={isDark}
                  />
                </label>
                <select
                  value={rebalance}
                  onChange={(e) => setRebalance(e.target.value)}
                  className={`w-full px-3 py-2 rounded-xl border text-sm ${
                    isDark
                      ? 'bg-slate-800 border-slate-700 text-slate-200'
                      : 'bg-white border-slate-200 text-slate-900'
                  }`}
                >
                  <option value="buy_and_hold">Buy and hold</option>
                  <option value="daily">Daily</option>
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="annual">Annual</option>
                </select>
              </div>
```

- [ ] **Step 8: Rewrite `ExtremeScenarios` to take server percentiles**

Delete the client-side `getPercentile` function entirely — it is the code path that produced the defect — and take the ladder from the payload:

```jsx
const ExtremeScenarios = ({ percentiles, meanReturn, isDark }) => {
  if (!percentiles) return null;

  // Guards against a regression: these values must come from the server's full-path
  // computation, never from a truncated chart sample.
  assertNotChartSample(percentiles, 'scenario ladder');

  const basePrice = 1000;
  const scenarios = [
    { label: 'Best Case (99%)', prob: '1%', val: percentiles.p99 },
    { label: 'Bullish (75%)', prob: '25%', val: percentiles.p75 },
    { label: 'Base Case (Median)', prob: '50%', val: percentiles.p50 },
    { label: 'Bearish (25%)', prob: '25%', val: percentiles.p25 },
    { label: 'Worst Case (1%)', prob: '1%', val: percentiles.p1 },
  ];

  const median = percentiles.p50;
  const mean = meanReturn ?? median;

  return (
    // ...the existing JSX body, unchanged from the `basePrice`/`scenarios` usage down
  );
};
```

Update both call sites. In the single-asset view, replace `<ExtremeScenarios returns={results.final_returns} isDark={isDark} />` with:

```jsx
            <ExtremeScenarios
              percentiles={results.percentiles}
              meanReturn={results.risk_stats.mean}
              isDark={isDark}
            />
```

In the portfolio view, delete the `derivedReturns` `useMemo` block entirely — it is the fallback that read the 30-path chart sample — and pass the server values:

```jsx
        <ExtremeScenarios
          percentiles={portfolioResults.percentiles}
          meanReturn={portfolioResults.portfolio_stats.mean_return}
          isDark={isDark}
        />
```

- [ ] **Step 9: Rename the chart-sample fields at the remaining call sites**

Six references change. In `chartData`:

```js
    if (!results?.paths_chart_sample) return [];
    return Array.from({ length: horizon }, (_, dayIndex) => {
      const dayData = { day: dayIndex };
      results.paths_chart_sample.forEach((path, pathIdx) => {
```

and at the single-asset chart's line rendering, `results.paths_sample.map(...)` becomes `results.paths_chart_sample.map(...)`.

In `portfolioChartData`:

```js
    if (!portfolioResults?.portfolio_paths_chart_sample) return [];
    const paths = portfolioResults.portfolio_paths_chart_sample;
```

and at the portfolio chart's line rendering, `portfolioResults.portfolio_paths_sample?.map(...)` becomes `portfolioResults.portfolio_paths_chart_sample?.map(...)`.

- [ ] **Step 10: Write `frontend/src/components/RiskContribution.jsx`**

Replaces the "Allocation" pie chart. Weight and risk contribution sit side by side so the divergence is visible, which is the point of spec 1.6:

```jsx
import { Shield } from 'lucide-react';

const formatPercent = (value) =>
  value === null || value === undefined ? '—' : `${(value * 100).toFixed(1)}%`;

/**
 * Weight answers "where is the money". Risk contribution answers "where is the risk".
 * They diverge sharply whenever volatilities differ, so both are shown together.
 */
export default function RiskContribution({ assets, isDark }) {
  if (!assets || assets.length === 0) return null;

  const maxShare = Math.max(...assets.map((a) => Math.max(a.weight, a.risk_contribution_pct)), 0.01);

  return (
    <div
      className={`${
        isDark
          ? 'bg-[#151e32] border-slate-700/50'
          : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'
      } rounded-3xl p-6 border transition-all`}
    >
      <div className="flex items-center gap-3 mb-1">
        <div className={`p-2 rounded-xl ${isDark ? 'bg-slate-800 text-white' : 'bg-slate-900 text-white'}`}>
          <Shield className="w-5 h-5" />
        </div>
        <h3 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>
          Risk Contribution
        </h3>
      </div>
      <p className={`text-xs mb-5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
        Share of portfolio volatility, beside portfolio weight. Contributions sum to 100%.
      </p>

      <div className="space-y-4">
        {assets.map((asset) => (
          <div key={asset.ticker}>
            <div className="flex justify-between items-baseline mb-1.5">
              <span className={`text-sm font-bold ${isDark ? 'text-slate-200' : 'text-slate-800'}`}>
                {asset.ticker}
              </span>
              <span className={`text-xs font-mono ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                weight {formatPercent(asset.weight)} · risk {formatPercent(asset.risk_contribution_pct)}
              </span>
            </div>
            <div className="space-y-1">
              <div className={`h-2 rounded-full ${isDark ? 'bg-slate-800' : 'bg-slate-100'}`}>
                <div
                  className={`h-2 rounded-full ${isDark ? 'bg-slate-500' : 'bg-slate-400'}`}
                  style={{ width: `${(asset.weight / maxShare) * 100}%` }}
                />
              </div>
              <div className={`h-2 rounded-full ${isDark ? 'bg-slate-800' : 'bg-slate-100'}`}>
                <div
                  className={`h-2 rounded-full ${isDark ? 'bg-indigo-400' : 'bg-indigo-600'}`}
                  style={{ width: `${(asset.risk_contribution_pct / maxShare) * 100}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className={`flex gap-4 mt-5 pt-4 border-t text-[10px] uppercase tracking-wider ${
        isDark ? 'border-slate-800 text-slate-500' : 'border-slate-100 text-slate-400'
      }`}>
        <span className="flex items-center gap-1.5">
          <span className={`w-3 h-2 rounded-full ${isDark ? 'bg-slate-500' : 'bg-slate-400'}`} />
          Weight
        </span>
        <span className="flex items-center gap-1.5">
          <span className={`w-3 h-2 rounded-full ${isDark ? 'bg-indigo-400' : 'bg-indigo-600'}`} />
          Risk contribution
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 11: Replace the Allocation pie with the new panel**

Import it in `App.jsx`:

```js
import RiskContribution from './components/RiskContribution';
```

Delete the `normalizedAssets` `useMemo` — the `Math.abs` normalisation that discarded the sign — and replace the entire "Allocation" card JSX block with:

```jsx
                <RiskContribution assets={portfolioResults.asset_stats} isDark={isDark} />
```

Remove the now-unused `RePieChart`, `Pie`, and `Cell` imports from the `recharts` import line if nothing else in the file uses them, and drop `pieColors` if it becomes unused. Verify with the lint step below rather than by eye.

- [ ] **Step 12: Label VaR with its horizon and show the assumed risk-free rate**

Both stat-card rows change. Task 10 moved VaR and CVaR out of `risk_stats` and into the `tail_risk` object, so the single-asset cards that read `results.risk_stats.VaR_95` and `.CVaR_95` would otherwise throw on `undefined`.

First, the **portfolio** row, so VaR carries its confidence and horizon (spec 1.7) and Sharpe carries its rf assumption (spec 1.5):

```jsx
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Portfolio Return"
          value={`${(portfolioResults.portfolio_stats.mean_return * 100).toFixed(2)}%`}
          icon={TrendingUp}
          color="emerald"
          trend="positive"
          isDark={isDark}
          info="Mean terminal return across all simulated paths. A conditional scenario, not a forecast."
        />
        <StatCard
          title="Volatility"
          value={`${(portfolioResults.portfolio_stats.volatility * 100).toFixed(2)}%`}
          icon={Activity}
          color="violet"
          isDark={isDark}
          info="Annualised volatility of the simulated portfolio path."
        />
        <StatCard
          title={`Sharpe (rf ${(portfolioResults.portfolio_stats.risk_free_rate * 100).toFixed(2)}%)`}
          value={portfolioResults.portfolio_stats.sharpe_ratio.toFixed(2)}
          icon={Target}
          color="blue"
          isDark={isDark}
          info={`Annualised excess return over annualised volatility. Risk-free rate source: ${portfolioResults.portfolio_stats.risk_free_source}.`}
        />
        <StatCard
          title={`VaR (95%, ${portfolioResults.tail_risk.horizon.horizon_days}-day)`}
          value={`${(portfolioResults.tail_risk.horizon.var_pct * 100).toFixed(2)}%`}
          icon={Shield}
          color="rose"
          trend="negative"
          isDark={isDark}
          info={`Loss exceeded in 5% of paths. CVaR ${(portfolioResults.tail_risk.horizon.cvar_pct * 100).toFixed(2)}%, tail-fatness ratio ${
            portfolioResults.tail_risk.horizon.cvar_var_ratio?.toFixed(2) ?? '—'
          }.`}
        />
      </div>
```

Then the **single-asset** row, which reads its tail figures from the same `tail_risk` object and its horizon from `horizon_days`:

```jsx
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard
          title="Mean Return"
          value={`${(results.risk_stats.mean * 100).toFixed(2)}%`}
          icon={TrendingUp}
          color="emerald"
          trend="positive"
          isDark={isDark}
          info={singleAssetInfo.mean}
        />
        <StatCard
          title="Volatility"
          value={`${(results.risk_stats.vol * 100).toFixed(2)}%`}
          icon={Activity}
          color="violet"
          isDark={isDark}
          info={singleAssetInfo.vol}
        />
        <StatCard
          title={`VaR (95%, ${results.tail_risk.horizon.horizon_days}-day)`}
          value={`${(results.tail_risk.horizon.var_pct * 100).toFixed(2)}%`}
          icon={Shield}
          color="rose"
          trend="negative"
          isDark={isDark}
          info={singleAssetInfo.var}
        />
        <StatCard
          title={`CVaR (95%, ${results.tail_risk.horizon.horizon_days}-day)`}
          value={`${(results.tail_risk.horizon.cvar_pct * 100).toFixed(2)}%`}
          icon={TrendingDown}
          color="orange"
          trend="negative"
          isDark={isDark}
          info={singleAssetInfo.cvar}
        />
        <StatCard
          title="Prob. Loss"
          value={`${(results.risk_stats.prob_loss * 100).toFixed(1)}%`}
          icon={AlertTriangle}
          color="amber"
          isDark={isDark}
          info={singleAssetInfo.prob}
        />
      </div>
```

Update the two matching entries in the `singleAssetInfo` tooltip object so they state the sign convention, since losses are now reported positive:

```js
    var: 'Loss exceeded in 5% of simulated paths, over the full horizon. Reported as a positive loss.',
    cvar: 'Mean loss in the worst 5% of paths. Always at least as large as VaR.',
```

- [ ] **Step 13: Run the frontend gates**

```bash
cd frontend && npm test && npm run lint && npm run build
```

Expected: 5 tests pass, lint clean (this is where unused `recharts` imports surface), build succeeds.

- [ ] **Step 14: Verify against the running backend**

```bash
backend/env/Scripts/python.exe -m uvicorn main:app --app-dir backend --port 8000
```

In a second terminal:

```bash
cd frontend && npm run dev
```

Check, in the portfolio tab: the scenario ladder changes when `num_paths` changes from 100 to 5000 (it could not before, because 30 paths were 30 paths either way); the panel reads "Risk Contribution"; the VaR card names its horizon; the Sharpe card names the rf. Then confirm the guard is live by running this in the browser console after a simulation:

```js
window.__test = (arr) => arr.reduce((a, b) => a + b, 0);
```

and confirming that the app itself never throws — a thrown chart-sample error in normal operation means a statistic is still being derived from the sample.

- [ ] **Step 15: Commit**

```bash
git add frontend/src/lib frontend/src/components frontend/src/App.jsx frontend/package.json frontend/package-lock.json frontend/vite.config.js
git commit -m "fix: consume server-computed percentiles and render risk contribution, not allocation"
```

---

### Task 13: Complete METHODOLOGY.md and verify the Definition of Done

The spec's Phase 1 Definition of Done is a checklist, and this task is where each line is verified with a command rather than asserted from memory.

**Files:**
- Modify: `docs/METHODOLOGY.md` (limitations, index)
- Modify: `README.md`

**Interfaces:**
- Consumes: every section appended by Tasks 1–11.
- Produces: nothing the code depends on.

- [ ] **Step 1: Append the known-limitations section to `docs/METHODOLOGY.md`**

Every trade-off flagged as "recorded in Known limitations" in an earlier section is collected here. This section is the reason the document is credible.

```markdown
## Known limitations

These are the things this model cannot do. They are listed because a risk document
that only lists capabilities is marketing.

**Estimation.** Drift is the sample mean of daily log returns, which is the noisiest
estimator in finance. At 25% annual volatility with 3 years of data the standard
error on the annualised drift is roughly `25% / sqrt(3) ~= 14%`. A 4% drift estimate
is statistically indistinguishable from 0%, from 20%, and from -10%. Every
forward-looking number here inherits that uncertainty, and Phase 1 does **not**
display it. Treat any single scenario figure as one draw from a wide distribution of
plausible models, not as an estimate with the precision its decimal places imply.
Addressing this is spec Phase 2.

**Covariance.** The sample covariance matrix is used without shrinkage. With 3 assets
and 750 observations that is acceptable; with 10 assets it is poorly conditioned, and
the risk decomposition inherits the conditioning. Ledoit-Wolf shrinkage is spec
Phase 2.

**Independence across days.** Every model here draws each day independently. None
reproduces volatility clustering: a calm week is exactly as likely to follow a crash
as to follow another calm week. Real markets do not behave this way. GARCH is spec
Phase 2.

**Correlation regimes.** The Gaussian model holds correlation fixed in every state of
the world. The joint GMM relaxes this, but component membership is still drawn
independently each day, so it captures state-dependent correlation without capturing
the persistence of those states.

**Data screening.** A genuine daily move landing within 0.5% of an exact split ratio
— a true, exact -50.0% session — would be removed as a split artifact. Illiquid
instruments printing three or more identical consecutive closes lose those
observations, biasing their measured volatility marginally upward.

**Risk-free rate.** The 13-week T-bill is used at every horizon, including multi-year
ones, where a duration-matched Treasury yield would be more defensible. For a non-USD
portfolio it is the wrong currency. The provider never raises, so a fallback rate can
silently underlie a Sharpe ratio — which is why the source is reported in the payload
and displayed beside the number.

**Tail estimates.** The 1st and 99th percentiles of 1000 paths rest on roughly ten
order statistics and carry material Monte Carlo error. More paths narrow it; no
number of paths removes it. VaR and CVaR are properties of the simulated
distribution: if the model is wrong about the tail, so are they, and neither is a
bound on loss.

**Rebalancing.** Real portfolios rebalance on cash flows and tax lots, not calendars.
The 21 / 63 / 252-day intervals approximate months, quarters, and years in trading
days and drift against real calendars over long horizons. Transaction costs are a
flat bps charge on traded notional; they model neither spread, nor market impact, nor
tax.

**Deployment memory.** Peak memory scales with `num_paths x horizon x n_assets`. The
request caps permit roughly 800 MB of resident arrays, which exceeds a 512 MB
container. Production deployment should lower the `num_paths` ceiling or provision
more memory.

**Nothing here is a forecast.** Every output is a conditional scenario: the
consequence of a stated model, a stated estimation window, and stated parameters. It
is not a prediction, not an expectation, and not investment advice.
```

- [ ] **Step 2: Add the index to the top of `docs/METHODOLOGY.md`**

Insert immediately after the opening paragraphs, before "## Conventions":

```markdown
## Contents

- [Conventions](#conventions)
- [Randomness and reproducibility](#randomness-and-reproducibility)
- [Data quality screening](#data-quality-screening)
- [Correlation estimation and correlated sampling](#correlation-estimation-and-correlated-sampling)
- [Joint return models](#joint-return-models)
- [Portfolio construction](#portfolio-construction)
- [Scenario percentiles](#scenario-percentiles)
- [Risk-adjusted performance](#risk-adjusted-performance)
- [Value at Risk and Conditional VaR](#value-at-risk-and-conditional-var)
- [Return and risk contributions](#return-and-risk-contributions)
- [Risk-free rate](#risk-free-rate)
- [API response contract](#api-response-contract)
- [Performance and memory](#performance-and-memory)
- [Known limitations](#known-limitations)
```

- [ ] **Step 3: Point the README at the methodology**

Add near the top of `README.md`, after the project description:

```markdown
## Methodology

Every formula this platform implements is documented in
[docs/METHODOLOGY.md](docs/METHODOLOGY.md) with its equation, assumption set,
estimation window, and failure modes — including a
[known limitations](docs/METHODOLOGY.md#known-limitations) section stating what the
model cannot do.

All outputs are **conditional scenarios**, not forecasts. This is not investment
advice.
```

- [ ] **Step 4: Verify the Definition of Done, line by line**

Run each command and confirm the stated expectation. Do not tick a box from memory.

1. *Every percentile displayed anywhere is computed from the full path set.*

```bash
grep -rn "getPercentile\|paths_sample\|final_returns" frontend/src/App.jsx
```

Expected: no `getPercentile`, no bare `paths_sample`, and `final_returns` only in the single-asset histogram (which uses the complete array).

2. *Selecting GMM produces demonstrably non-Gaussian output.*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_joint_models.py -k kurtosis -v
```

3. *No magnitude-based return filtering or output clipping anywhere.*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_data_quality.py -k "survives or no_magnitude" -v
```

4. *Portfolio returns from simple returns with an explicit rebalancing rule.*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_portfolio_math.py -v
```

5. *Sharpe uses excess return over a stated rf with matched annualisation.*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_risk_metrics.py -k sharpe -v
```

6. *Risk contributions sum to portfolio volatility (to 1e-9).*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_contributions.py -k sum_to -v
```

7. *Byte-identical output under concurrent load.*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_determinism.py -v
```

8. *5000 x 10 x 1000 under 2 seconds.*

```bash
backend/env/Scripts/python.exe -m pytest backend/tests/test_performance.py -m benchmark -v
```

9. *METHODOLOGY.md documents every formula and assumption.*

```bash
grep -c "^## " docs/METHODOLOGY.md
```

Expected: 14 sections, matching the index.

- [ ] **Step 5: Run every gate one final time**

```bash
backend/env/Scripts/python.exe -m pytest -m "not benchmark" && backend/env/Scripts/python.exe -m pytest -m benchmark && backend/env/Scripts/python.exe -m ruff check . && backend/env/Scripts/python.exe -m mypy
```

```bash
cd frontend && npm test && npm run lint && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add docs/METHODOLOGY.md README.md
git commit -m "docs: complete methodology with known limitations and DoD verification"
```

---

## Self-review notes

Checked against the spec's Phase 0 and Phase 1 sections and its Definition of Done:

**Spec coverage.** Phase 0 items 1–5 map to Tasks 1 and 2. Phase 1 items map as: 1.1 → Tasks 10 and 12; 1.2 → Task 5 (implemented) and Task 10 (`t_copula` interface, HTTP 501); 1.3 → Task 3; 1.4 → Task 6; 1.5 → Tasks 7, 9, and 12; 1.6 → Tasks 8 and 12; 1.7 → Tasks 7, 10, and 12; 1.8 → Tasks 4 and 11. Every Definition-of-Done line has a verifying command in Task 13 Step 4.

**Deliberate deviations from the spec's literal wording, each with a reason:**

- Spec 1.7 names the VaR field `value_pct`. The plan uses `var_pct` and `cvar_pct` in one object holding both measures, because a single field named `value_pct` in an object that carries both VaR and CVaR is ambiguous — the exact class of defect 1.7 exists to fix.
- Spec 1.2 says "Expose `correlation_model`" alongside the existing `model` field. The plan **replaces** the portfolio endpoint's `model` field with `correlation_model` rather than carrying both, because two overlapping model selectors on one endpoint invites the next version of the decorative-toggle bug. The frontend maps its existing toggle onto the new field.
- Spec 1.5 says to add Calmar as "return over max drawdown". The plan uses the **median** maximum drawdown across paths, since the MDD distribution is right-skewed and the mean is not representative. This is stated in METHODOLOGY.
- The spec's Phase 5 instruction to delete the dead `"Adj Close"` branch is pulled into Task 3, because that task rewrites the same function.

**Open decision for the reviewer.** `backend/src/` contains four modules nothing imports: `visualization.py`, `debug_day1.py`, `simulate_paths.py`, `test.portfolio.py`. This plan excludes them from linting and type-checking rather than deleting them, so the deletion can be gated separately. If they are dead, deleting them is a one-line follow-up commit.

**Phases 2–5 are not covered by this plan.** They need their own plans, written after this one is reviewed and merged. Phase 4 in particular (the live track record, Postgres, tamper-evidence, the legal surface) is a separate subsystem and should get a separate spec-and-plan pass of its own.
