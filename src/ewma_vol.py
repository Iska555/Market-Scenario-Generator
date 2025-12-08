import numpy as np
import pandas as pd


def compute_ewma_vol(log_returns: pd.Series, lam: float = 0.94) -> pd.Series:
    """
    Compute EWMA volatility series using lambda decay factor.
    r_t = daily log returns
    sigma_t^2 = lambda * sigma_(t-1)^2 + (1 - lambda) * r_(t-1)^2
    """
    r = log_returns.dropna().values
    n = len(r)

    ewma_var = np.zeros(n)
    ewma_var[0] = r[0] ** 2  # start with squared return

    for t in range(1, n):
        ewma_var[t] = lam * ewma_var[t - 1] + (1 - lam) * r[t - 1] ** 2

    ewma_vol = np.sqrt(ewma_var)
    return pd.Series(ewma_vol, index=log_returns.index, name="ewma_vol")


def forecast_ewma_vol(last_vol: float, lam: float, horizon: int) -> np.ndarray:
    """
    Forecast future volatility path assuming EWMA persistence:
    sigma_{t+1} = sqrt(lambda) * sigma_t
    """
    vols = np.zeros(horizon)
    vols[0] = last_vol

    for t in range(1, horizon):
        vols[t] = np.sqrt(lam) * vols[t - 1]

    return vols


def sample_ewma_returns(mu: float, vol_forecast: np.ndarray, num_paths: int) -> np.ndarray:
    """
    For each day t:
        r_t ~ N(mu, vol_forecast[t]^2)
    Returns matrix shape: (num_paths, horizon)
    """
    horizon = len(vol_forecast)
    rand_norm = np.random.randn(num_paths, horizon)
    return mu + vol_forecast * rand_norm
