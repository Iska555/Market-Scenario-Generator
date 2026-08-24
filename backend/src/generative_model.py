import numpy as np
import pandas as pd


def fit_gaussian(returns: pd.Series) -> tuple[float, float]:
    """Fit mean and standard deviation to log returns ."""

    clean = returns.dropna().astype(float)
    mu = clean.mean()
    sigma = clean.std(ddof=1)
    return float(mu), float(sigma)


def sample_gaussian(
    mu: float, sigma: float, horizon: int, num_paths: int, random_state: int = 42
) -> np.ndarray:
    """Sample returns from N(mu, sigma^2)."""
    rng = np.random.default_rng(random_state)
    return rng.normal(mu, sigma, size=(num_paths, horizon))


if __name__ == "__main__":
    print("Module OK")
