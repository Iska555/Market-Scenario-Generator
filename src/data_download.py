import yfinance as yf
import pandas as pd


def download_price_data(ticker: str, years: int = 3) -> pd.DataFrame:
    """
    Download daily price history for a ticker for the last `years` years.
    Returns a DataFrame with index = date, column = 'price'.
    """
    period = f"{years}y"

    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if data.empty:
        raise ValueError(f"No data returned for ticker {ticker}") 
    if "Adj Close" in data.columns:
        price = data["Adj Close"]
    elif "Close" in data.columns:
        price = data["Close"]
    else:
        raise ValueError("Downloaded data has no 'Adj Close' or 'Close' column")

    # Safety: if for some reason this is (n, 1) DataFrame, convert to Series
    if isinstance(price, pd.DataFrame):
        price = price.iloc[:, 0]

    # Make it a single-column DataFrame named 'price'
    df = price.to_frame(name="price")
    df.index.name = "date"

    return df


if __name__ == "__main__":
    df = download_price_data("SPY", years=1)
    print(df.head())
    print(df.tail())
    print(f"Downloaded {len(df)} rows for SPY")
