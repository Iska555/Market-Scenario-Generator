"""Capture current API output for a fixed config, as the Task 14 baseline.

Run against the ORIGINAL code, before any Phase 1 fix lands. Requires network.

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
