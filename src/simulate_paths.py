import numpy as np
import matplotlib.pyplot as plt

from src.data_download import download_price_data
from src.returns_preprocess import compute_log_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import fit_gmm, sample_gmm
from src.visualization import (
    plot_historical_price,
    plot_simulated_paths,
    plot_final_return_distribution,
)


def build_paths_from_returns(start_price, returns_matrix):
    """Convert simulated returns into price paths."""
    cum_returns = returns_matrix.cumsum(axis=1)
    return start_price * np.exp(cum_returns)


def compute_risk_stats(final_returns):
    """Compute basic risk statistics."""
    fr = final_returns
    mean = fr.mean()
    vol = fr.std(ddof=1)
    var_95 = np.percentile(fr, 5)
    cvar_95 = fr[fr <= var_95].mean()
    prob_loss = (fr < 0).mean()

    return {
        "mean": float(mean),
        "vol": float(vol),
        "VaR_95": float(var_95),
        "CVaR_95": float(cvar_95),
        "prob_loss": float(prob_loss),
    }


def run_scenario(
    ticker: str,
    years: int,
    horizon: int,
    num_paths: int,
    model: str = "gaussian",
):
    """Run a full scenario simulation pipeline."""
    # 1. Get price history
    df = download_price_data(ticker, years)
    log_returns = compute_log_returns(df)

    start_price = float(df["price"].iloc[-1])

    # 2. Model choice
    if model == "gaussian":
        mu, sigma = fit_gaussian(log_returns)
        returns_matrix = sample_gaussian(mu, sigma, horizon, num_paths)

    elif model == "gmm":
        gmm = fit_gmm(log_returns, n_components=3)
        returns_matrix = sample_gmm(gmm, horizon, num_paths)

    else:
        raise ValueError(f"Unknown model: {model}")

    # 3. Simulated price paths
    paths = build_paths_from_returns(start_price, returns_matrix)

    # 4. Final returns (simple)
    final_prices = paths[:, -1]
    final_returns = final_prices / start_price - 1

    # 5. Compute risk statistics
    stats = compute_risk_stats(final_returns)

    return df, paths, final_returns, stats


# -----------------------------------------------------------------------
# Main entry point (visualization)
# -----------------------------------------------------------------------
if __name__ == "__main__":
    TICKER = "SPY"
    YEARS = 3
    HORIZON = 252
    NUM_PATHS = 1000
    MODEL = "gmm"

    df, paths, final_returns, stats = run_scenario(
        TICKER, YEARS, HORIZON, NUM_PATHS, model=MODEL
    )

    print("\n=== Risk statistics ===")
    for k, v in stats.items():
        print(f"{k}: {v:.4f}")

    # --- Visualization ---
    plot_historical_price(df, TICKER)
    plot_simulated_paths(paths, MODEL)
    plot_final_return_distribution(final_returns, stats, MODEL)

    plt.show()
