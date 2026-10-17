"""Yahoo adjusted-close adapter; transformed series is explicitly identified."""

from datetime import UTC, datetime

import pandas as pd
import yfinance as yf


def download_price_data(ticker: str, years: int = 3) -> pd.DataFrame:
    data = yf.download(
        ticker,
        period=f"{years}y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
        timeout=10,
    )
    if data is None or data.empty or "Close" not in data:
        raise ValueError(f"No adjusted-close data for {ticker}")
    price = data["Close"]
    if isinstance(price, pd.DataFrame):
        if price.shape[1] != 1:
            raise ValueError("Expected a single ticker from provider")
        price = price.iloc[:, 0]
    frame: pd.DataFrame = price.to_frame(name="price")
    frame.index.name = "date"
    frame.attrs["source"] = "yfinance:auto_adjust=True:Close"
    frame.attrs["retrieved_at"] = datetime.now(UTC).isoformat()
    return frame
