"""Explicit bounded cache; serialize yfinance downloads across request threads."""

import time
from collections import OrderedDict
from threading import Lock
from typing import Protocol

import pandas as pd

from src.data_download import download_price_data


class PriceDataProvider(Protocol):
    def __call__(self, ticker: str, years: int) -> pd.DataFrame: ...


class PriceDataError(RuntimeError):
    """Provider unavailable or returned no usable data."""


class CachedPriceProvider:
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 128) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: OrderedDict[tuple[str, int], tuple[float, pd.DataFrame]] = OrderedDict()
        self._lock = Lock()

    def __call__(self, ticker: str, years: int) -> pd.DataFrame:
        key = (ticker, years)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None and time.monotonic() - cached[0] < self.ttl_seconds:
                self._cache.move_to_end(key)
                return cached[1].copy(deep=True)
            try:
                frame = download_price_data(ticker, years)
            except Exception as exc:
                raise PriceDataError(f"Price provider failed for {ticker}") from exc
            self._cache[key] = (time.monotonic(), frame.copy(deep=True))
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)
            return frame.copy(deep=True)
