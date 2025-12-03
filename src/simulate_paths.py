import numpy as np
from data_download import download_price_data
from returns_preprocess import compute_log_returns
from generative_model import fit_gaussian, sample_gaussian
from gmm_model import fit_gmm, sample_gmm


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

def run_scenario(
    ticker: str,
    years: int,
    horizon: int,
    num_paths: int,
    model: str = "gaussian",
):
    # 1. Get history
    df = download_price_data(ticker, years)
    log_returns = compute_log_returns(df)

    start_price = float(df["price"].iloc[-1])

    # 2. Fit model + sample returns
    if model == "gaussian":
        mu, sigma = fit_gaussian(log_returns)
        returns_matrix = sample_gaussian(mu, sigma, horizon, num_paths)

    elif model == "gmm":
        gmm = fit_gmm(log_returns, n_components=3)
        returns_matrix = sample_gmm(gmm, horizon, num_paths)

    else:
        raise ValueError(f"Unknown model: {model}")

    # 3. Price paths
    paths = build_paths_from_returns(start_price, returns_matrix)

    # 4. Final simple returns
    final_prices = paths[:, -1]
    final_returns = final_prices / start_price - 1

    stats = compute_risk_stats(final_returns)

    return paths, stats

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    paths, stats = run_scenario("SPY", 3, 252, 1000, model="gmm")

    print("Risk stats:")
    for k, v in stats.items():
        print(k, v)

    plt.plot(paths[:30].T, alpha=0.4)
    plt.title("Simulated GMM Paths")
    plt.show()