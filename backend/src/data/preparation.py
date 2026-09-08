"""Joint return intervals must share both start and end observations."""

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.returns_preprocess import compute_log_returns, valid_prices
from src.risk.contracts import QuantModel


class DataDiagnostic(QuantModel):
    ticker: str
    observations: int
    invalid_price_count: int
    missing_price_count: int
    repeated_price_count: int
    extreme_return_count: int
    start_date: str
    end_date: str
    source: str
    retrieved_at: str | None
    input_sha256: str


@dataclass(frozen=True)
class PreparedPrices:
    returns: pd.DataFrame
    start_prices: np.ndarray
    diagnostics: list[DataDiagnostic]
    excluded_interval_count: int
    valuation_date: str


def prepare_prices(price_data: dict[str, pd.DataFrame]) -> PreparedPrices:
    returns: dict[str, pd.Series] = {}
    starts: dict[str, pd.Series] = {}
    diagnostics: list[DataDiagnostic] = []
    valid: dict[str, pd.Series] = {}
    for ticker, frame in price_data.items():
        if frame.empty:
            raise ValueError(f"No price observations for {ticker}")
        prices = valid_prices(frame)
        if pd.isna(prices.iloc[-1]):
            raise ValueError(f"Invalid latest price for {ticker}")
        valid[ticker] = prices
        rets = compute_log_returns(frame)
        returns[ticker] = rets
        # Retain original predecessor, including a missing-price boundary.
        starts[ticker] = pd.Series(frame.index, index=frame.index).shift().reindex(rets.index)
        raw = frame["price"].astype(float)
        digest = hashlib.sha256(pd.util.hash_pandas_object(raw, index=True).to_numpy().tobytes())
        diagnostics.append(
            DataDiagnostic(
                ticker=ticker,
                observations=len(frame),
                invalid_price_count=int(((raw <= 0) | np.isinf(raw)).sum()),
                missing_price_count=int(raw.isna().sum()),
                repeated_price_count=int((prices.diff() == 0).sum()),
                extreme_return_count=int((rets.abs() >= 0.20).sum()),
                start_date=str(frame.index[0]),
                end_date=str(frame.index[-1]),
                source=str(frame.attrs.get("source", "provided_price_frame")),
                retrieved_at=frame.attrs.get("retrieved_at"),
                input_sha256=digest.hexdigest(),
            )
        )
    joint = pd.DataFrame(returns).dropna()
    previous = pd.DataFrame(starts).reindex(joint.index)
    same_interval = previous.eq(previous.iloc[:, 0], axis=0).all(axis=1)
    excluded = int((~same_interval).sum())
    joint = joint.loc[same_interval]
    if len(joint) < 30:
        raise ValueError("At least 30 valid joint return intervals are required")
    common_prices = pd.DataFrame(valid).dropna()
    if common_prices.empty:
        raise ValueError("No common valuation date")
    return PreparedPrices(
        joint,
        common_prices.iloc[-1].to_numpy(),
        diagnostics,
        excluded,
        str(common_prices.index[-1]),
    )
