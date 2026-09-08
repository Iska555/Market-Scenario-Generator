"""Offline, reproducible workload timing; no hardware-dependent pass threshold."""

import json
import pathlib
import platform
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from src.api.models import PortfolioSimulationRequest
from src.risk.scenarios.service import run_portfolio


def benchmark() -> None:
    rng = np.random.default_rng(2026)
    history = rng.normal(0, 0.012, (800, 5))
    dates = pd.bdate_range("2020-01-01", periods=800)
    frames = {
        f"A{i}": pd.DataFrame({"price": 100 * np.exp(history[:, i].cumsum())}, index=dates)
        for i in range(5)
    }

    def provider(ticker: str, years: int) -> pd.DataFrame:
        return frames[ticker]

    timings = {}
    for model in ("gaussian", "gmm"):
        request = PortfolioSimulationRequest.model_validate(
            {
                "tickers": list(frames),
                "num_paths": 1000,
                "horizon": 252,
                "model": model,
                "drift_model": "zero_log_drift",
                "random_seed": 42,
            }
        )
        start = time.perf_counter()
        result = run_portfolio(request, provider)
        elapsed = time.perf_counter() - start
        timings[model] = {
            "seconds": round(elapsed, 4),
            "histogram_count": sum(bucket.count for bucket in result.histogram),
            "chart_sample_paths": 30,
        }
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "numpy": np.__version__,
                "workload": "1000 paths x 252 periods x 5 assets",
                "includes": "preparation, fitting, simulation, statistics, response assembly",
                "excludes": "network, HTTP serialization, frontend rendering",
                "timings": timings,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    benchmark()
