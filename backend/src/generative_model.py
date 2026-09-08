"""Gaussian marginal fitting: fitted log means need no further Ito adjustment."""

import numpy as np
import pandas as pd


def fit_gaussian(returns: pd.Series) -> tuple[float, float]:
    clean = returns.dropna().astype(float)
    if len(clean) < 2 or not np.isfinite(clean).all():
        raise ValueError("At least two finite returns are required")
    return float(clean.mean()), float(clean.std(ddof=1))


def sample_gaussian(
    mu: float, sigma: float, horizon: int, num_paths: int, *, rng: np.random.Generator
) -> np.ndarray:
    return rng.normal(mu, sigma, size=(num_paths, horizon))
