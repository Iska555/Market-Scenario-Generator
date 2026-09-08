"""Invalid observations break intervals; legitimate return tails are retained."""

import numpy as np
import pandas as pd


def valid_prices(price_df: pd.DataFrame, price_col: str = "price") -> pd.Series:
    if not price_df.index.is_unique or not price_df.index.is_monotonic_increasing:
        raise ValueError("Price dates must be unique and increasing")
    prices = price_df[price_col].astype(float)
    return prices.where(np.isfinite(prices) & (prices > 0))


def compute_log_returns(price_df: pd.DataFrame, price_col: str = "price") -> pd.Series:
    prices = valid_prices(price_df, price_col)
    result = pd.Series(np.log(prices.to_numpy()), index=prices.index).diff().dropna()
    result.name = "log_return"
    return result


def attach_log_returns(price_df: pd.DataFrame, price_col: str = "price") -> pd.DataFrame:
    df = price_df.copy()
    df["log_return"] = compute_log_returns(df, price_col)
    return df.dropna(subset=["log_return"])
