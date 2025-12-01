import numpy as np
from data_download import download_price_data
from returns_preprocess import compute_log_returns
from generative_model import fit_gaussian, sample_gaussian


def build_paths_from_returns(start_price, returns_matrix):
    """Convert simulated returns into price paths."""
    cum_returns = returns_matrix.cumsum(axis=1)
    return start_price * np.exp(cum_returns)

def compute_risk_stats(final_returns):
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
        "prob_loss": float(prob_loss)
    }

def run_gaussian_scenario(ticker, years, horizon, num_paths):
    # 1. Get history
    df = download_price_data(ticker, years)
    log_returns = compute_log_returns(df)

    # 2. Fit model
    mu, sigma = fit_gaussian(log_returns)

    # 3. Sample future log returns
    sims = sample_gaussian(mu, sigma, horizon, num_paths)

    # 4. Build price paths
    start_price = float(df["price"].iloc[-1])
    paths = build_paths_from_returns(start_price, sims)

    # 5. Final simple returns: P_T / P_0 - 1
    final_prices = paths[:, -1]
    final_returns = final_prices / start_price - 1
    stats = compute_risk_stats(final_returns)

    return paths, stats


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    paths, stats = run_gaussian_scenario("SPY", 3, 252, 1000)

    print("Risk stats:")
    for k, v in stats.items():
        print(k, v)

    plt.plot(paths[:30].T, alpha=0.4)
    plt.title("Simulated Gaussian Paths")
    plt.show()