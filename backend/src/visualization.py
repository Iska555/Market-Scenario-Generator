import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def plot_historical_price(price_df: pd.DataFrame, ticker: str):
    """Plot historical price series."""
    plt.figure()
    price_df["price"].plot()
    plt.title(f"{ticker} Historical Price")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.tight_layout()


def plot_simulated_paths(paths: np.ndarray, model_name: str, max_paths: int = 30):
    """Plot a subset of simulated price paths."""
    plt.figure()

    num_paths = min(max_paths, paths.shape[0])
    plt.plot(paths[:num_paths].T, alpha=0.4)

    plt.title(f"Simulated {model_name} Paths (Showing {num_paths} of {paths.shape[0]})")
    plt.xlabel("Day")
    plt.ylabel("Price")
    plt.tight_layout()


def plot_final_return_distribution(
        final_returns: np.ndarray,
        stats: dict,
        model_name: str,
):
    """Plot histogram of ending returns with VaR and CVaR lines."""
    plt.figure()
    plt.hist(final_returns, bins=50, density=True, alpha=0.7)

    var_95 = stats.get("VaR_95")
    cvar_95 = stats.get("CVaR_95")

    if var_95 is not None:
        plt.axvline(
            var_95, linestyle="--", linewidth=1.5,
            label=f"VaR 95% = {var_95:.3f}"
        )

    if cvar_95 is not None:
        plt.axvline(
            cvar_95, linestyle=":", linewidth=1.5,
            label=f"CVaR 95% = {cvar_95:.3f}"
        )

    plt.title(f"Final Return Distribution — {model_name}")
    plt.xlabel("Final Return")
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()


def plot_ewma_vol(vol_series: pd.Series, ticker: str):
    """Plot EWMA volatility time series."""
    plt.figure()
    vol_series.plot()
    plt.title(f"EWMA Volatility — {ticker}")
    plt.xlabel("Date")
    plt.ylabel("Volatility")
    plt.tight_layout()