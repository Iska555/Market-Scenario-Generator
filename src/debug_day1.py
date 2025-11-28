import matplotlib.pyplot as plt

from data_download import download_price_data
from returns_preprocess import compute_log_returns


def main():
    ticker = "SPY"
    years = 3

    data = download_price_data(ticker, years=years)

    # Compute log returns from the downloaded data
    log_returns = compute_log_returns(data)

    print(f"{ticker}: {len(data)} price points, {len(log_returns)} returns")

    # Plot price history
    plt.figure()
    data["price"].plot()
    plt.title(f"{ticker} price history (last {years} years)")
    plt.xlabel("Date")
    plt.ylabel("Price")

    # Plot returns histogram
    plt.figure()
    plt.hist(log_returns, bins=50, density=True)
    plt.title(f"{ticker} daily log returns histogram")
    plt.xlabel("Log return")
    plt.ylabel("Density")

    plt.show()


if __name__ == "__main__":
    main()
