"""Capture current v3 API output for a fixed diagnostic config.

Requires network. Never overwrite baseline_v2.json: that is an archival record
of the incorrect pre-rebuild API, not a golden correctness oracle.

    python scripts/capture_baseline.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import main
from fastapi.testclient import TestClient

TICKERS = ["SPY", "NVDA", "MSFT"]
OUTPUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "golden" / "diagnostic_v3.json"

# Fields that are large path dumps: recorded by shape only, not by value.
_BULKY = ("paths_chart_sample", "portfolio_paths_chart_sample")


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
                "horizon": 252,
                "num_paths": 1000,
                "model": model,
                "drift_model": "historical_diagnostic",
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
