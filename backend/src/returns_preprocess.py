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
    log_returns: pd.Series = np.log(prices).diff().dropna()  # type: ignore[attr-defined]
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
    df["log_return"] = np.log(df[price_col].astype(float)).diff()  # type: ignore[attr-defined]
    return df.dropna()
