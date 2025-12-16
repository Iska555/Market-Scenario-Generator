# src/ewma_vol.py

import numpy as np
import pandas as pd

def compute_ewma_vol(log_returns: pd.Series, lam: float = 0.94) -> pd.Series:
    """
    Compute EWMA volatility series using lambda decay factor.
    sigma_t^2 = lambda * sigma_(t-1)^2 + (1 - lambda) * r_(t-1)^2
    """
    r = log_returns.dropna().values
    n = len(r)
    
    ewma_var = np.zeros(n)
    
    # Initialize with the variance of the first chunk of data or just r[0]^2
    # Using the first squared return is standard for simple recursions
    ewma_var[0] = r[0] ** 2 

    for t in range(1, n):
        ewma_var[t] = lam * ewma_var[t - 1] + (1 - lam) * (r[t - 1] ** 2)
    
    ewma_vol = np.sqrt(ewma_var)
    return pd.Series(ewma_vol, index=log_returns.index, name="ewma_vol")


def forecast_ewma_vol(last_vol: float, lam: float, horizon: int) -> np.ndarray:
    """
    Forecast future volatility.
    
    For a pure EWMA / Random Walk Volatility model, the best estimate 
    of future volatility is the current volatility (flat forecast).
    
    (Note: The previous version decayed vol to 0, which is incorrect for 
    risk simulation unless we assume the market dies.)
    """
    # Create an array of length 'horizon' filled with 'last_vol'
    return np.full(horizon, last_vol)


def sample_ewma_returns(mu: float, vol_forecast: np.ndarray, num_paths: int) -> np.ndarray:
    """
    Generate random returns using the forecasted volatility vector.
    
    vol_forecast: shape (horizon,)
    Returns: shape (num_paths, horizon)
    """
    horizon = len(vol_forecast)
    
    # 1. Generate standard normal random numbers (Z scores)
    # Shape: (num_paths, horizon)
    z_scores = np.random.randn(num_paths, horizon)
    
    # 2. Scale by volatility and add mean
    # Broadcasting: (num_paths, horizon) * (horizon,) works in numpy if aligned right
    # We might need to reshape vol_forecast to (1, horizon) to be safe
    vol_matrix = vol_forecast.reshape(1, horizon)
    
    simulated_returns = mu + (z_scores * vol_matrix)
    
    return simulated_returns