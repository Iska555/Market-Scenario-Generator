"""Shared fixtures. No test in this suite touches the network."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every provider interaction in this suite must use a controlled fixture."""
    import socket

    import yfinance

    original_connect = socket.socket.connect

    def external_connection(sock: socket.socket, address: object) -> None:
        # Windows asyncio creates a loopback socketpair for its wake-up pipe.
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            original_connect(sock, address)
            return
        raise AssertionError("External network access is forbidden in the test suite")

    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network access is forbidden in the test suite")

    monkeypatch.setattr(socket.socket, "connect", external_connection)
    monkeypatch.setattr(yfinance, "download", blocked)


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
            seed = int.from_bytes(hashlib.sha256(ticker.encode()).digest()[:4], "little")
            cache[ticker] = make_correlated_prices([ticker], seed=seed)[ticker]
        return cache[ticker]

    return _provider
