import numpy as np
import pandas as pd



def fit_gaussian(returns: pd.Series):
    '''Fit mean and standard deviation to log returns .'''

    clean = returns.dropna().astype(float)
    mu = clean.mean()
    sigma = clean.std(ddof=1)
    return float(mu), float(sigma)

def sample_gaussian(mu, sigma, horizon, num_paths, random_state=42):
    """Sample returns from N(mu, sigma^2)."""
    rng = np.random.default_rng(random_state)
    return rng.normal(mu, sigma, size = (num_paths, horizon))

if __name__ == "__main__":
    print("Module OK")

