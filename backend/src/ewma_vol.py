"""Zero-centered EWMA second moments and a flat conditional variance forecast."""

import numpy as np
import pandas as pd


def compute_ewma_vol(log_returns: pd.Series, lam: float = 0.94) -> pd.Series:
    clean = log_returns.dropna().astype(float)
    if clean.empty or not np.isfinite(clean).all() or not 0 < lam < 1:
        raise ValueError("EWMA requires finite observations and 0 < lambda < 1")
    r = clean.to_numpy()
    variance = np.empty(len(r))
    variance[0] = r[0] ** 2
    # Sequential dependence is intrinsic here; no loop over simulation paths.
    for t in range(1, len(r)):
        variance[t] = lam * variance[t - 1] + (1 - lam) * r[t] ** 2
    return pd.Series(np.sqrt(variance), index=clean.index, name="ewma_vol")


def forecast_ewma_vol(last_vol: float, lam: float, horizon: int) -> np.ndarray:
    if not np.isfinite(last_vol) or last_vol < 0 or not 0 < lam < 1 or horizon < 1:
        raise ValueError("Invalid EWMA forecast parameters")
    return np.full(horizon, last_vol, dtype=float)


def sample_ewma_returns(
    mu: float, vol_forecast: np.ndarray, num_paths: int, *, rng: np.random.Generator
) -> np.ndarray:
    return np.asarray(mu + rng.standard_normal((num_paths, len(vol_forecast))) * vol_forecast)
