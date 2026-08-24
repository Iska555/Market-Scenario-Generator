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
