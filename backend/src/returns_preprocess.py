import numpy as np
import pandas as pd

def compute_log_returns(price_df: pd.DataFrame,price_col: str = "price") -> pd.series:
    """
    Given a DataFrame with a price column, compute daily log returns.

    r_t = log(P_t / P_{t-1})
        = log(P_t) - log(P_{t-1})

    Returns a Series indexed by date with name 'log_return'.
    """
    if price_col not in price_df.columns:
        raise KeyError(f"Column '{price_col}' not found in DataFrame")

    prices = price_df[price_col].astype(float)

    log_prices = np.log(prices)
    log_returns = log_prices.diff().dropna()
    log_returns.name = "log_return"

    return log_returns

def attach_log_returns(price_df: pd.DataFrame, price_col: str = "price") -> pd.DataFrame:
    """
    Given a DataFrame with a price column, compute daily log returns and
    attach them as a new column 'log_return'.

    Returns the original DataFrame with an additional 'log_return' column.
    """
    df = price_df.copy()
    if price_col not in df.columns:
        raise KeyError(f"Column '{price_col}' not found in DataFrame")
    
    df['log_return'] = np.log(df[price_col].astype(float)).diff()
    df = df.dropna()

    return df


if __name__ == "__main__":
    #Example usage

    from data_download import download_price_data

    prices = download_price_data("SPY", years=3)
    log_rets = compute_log_returns(prices)

    print(log_rets.head())
    print(log_rets.describe())