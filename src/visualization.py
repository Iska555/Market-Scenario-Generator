import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def plot_historical_price(price_df: pd.DataFrame, ticker: str):
    """Plot historical price series."""
    plt.figure()
    price_df["price"].plot()
    plt.title(f"{ticker} historical price")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.tight_layout()



def plot_simulated_paths(paths: np.array, model_name: str, max_paths: int = 30):
    """Plot simulated price paths."""
    plt.figure()

    num_paths = min(max_paths, paths.shape[0])
    plt.plot(paths[:num_paths].T, alpha=0.4)

    plt.title(f"Simulated {model_name} paths (first {num_paths} of {paths.shape[0]})")
    plt.xlabel("Day")
    plt.ylabel("Price")
    plt.tight_layout()


def plot_final_return_distribution(
        final_returns: np.ndarray,
        stats: dict,
        model_name: str,
):
    """Plot histogram of final returns with VaR and CVar markers."""
    plt.figure()
    plt.hist(final_returns, bins=50, density=True,alpha=0.7)
    var_95=stats.get("VaR_95")
    cvar_95=stats.get("CVaR_95")    

    if var_95 is not None:
        plt.axvline(
            var_95,
            linestyle="--",
            linewidth=1.5,
            label=f"VaR 95% = {var_95:.3f}",
        )

    if cvar_95 is not None:
        plt.axvline(
            cvar_95,
            linestyle=":",
            linewidth=1.5,
            label=f"CVaR 95% = {cvar_95:.3f}",
        )

    plt.title(f"Distribution of final returns - {model_name}")
    plt.xlabel("Final return")
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()