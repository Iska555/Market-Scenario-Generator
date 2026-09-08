"""Costless, fully invested long-only paths, always including time zero."""

from typing import Literal

import numpy as np


def build_portfolio_paths(
    start_prices: np.ndarray,
    returns_matrix: np.ndarray,
    weights: np.ndarray | None = None,
    rebalance: Literal["daily", "buy_and_hold"] = "daily",
) -> tuple[np.ndarray, np.ndarray]:
    if returns_matrix.ndim != 3 or not np.isfinite(returns_matrix).all():
        raise ValueError("Log returns must be a finite path x time x asset tensor")
    n_paths, horizon, n_assets = returns_matrix.shape
    if min(n_paths, horizon, n_assets) < 1:
        raise ValueError("Path, horizon and asset counts must be positive")
    if start_prices.shape != (n_assets,) or not np.isfinite(start_prices).all():
        raise ValueError("Start prices must match assets and be finite")
    if (start_prices <= 0).any():
        raise ValueError("Start prices must be positive")
    if weights is None:
        weights = np.full(n_assets, 1 / n_assets)
    if (
        weights.shape != (n_assets,)
        or not np.isfinite(weights).all()
        or (weights < 0).any()
        or not np.isclose(weights.sum(), 1, rtol=0, atol=1e-10)
    ):
        raise ValueError("Long-only weights must match assets and sum to one")
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        growth = np.exp(returns_matrix.cumsum(axis=1))
        if rebalance == "daily":
            portfolio = np.cumprod(1 + np.expm1(returns_matrix) @ weights, axis=1)
        elif rebalance == "buy_and_hold":
            portfolio = growth @ weights
        else:
            raise ValueError("Unsupported rebalancing rule")
        assets = np.concatenate(
            [np.broadcast_to(start_prices, (n_paths, 1, n_assets)), growth * start_prices],
            axis=1,
        )
        portfolio = np.concatenate([np.ones((n_paths, 1)), portfolio], axis=1)
    if not np.isfinite(portfolio).all() or (portfolio <= 0).any() or (assets <= 0).any():
        raise ValueError("Path exceeds numerical range; no clipping is applied")
    return assets, portfolio
