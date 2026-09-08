"""Joint Gaussian mixtures with iid component labels and explicit request RNG."""

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from src.risk.covariance import psd_factor


def fit_gmm(
    returns: pd.Series | pd.DataFrame,
    n_components: int = 3,
    *,
    rng: np.random.Generator,
    reg_covar: float = 1e-6,
) -> GaussianMixture:
    x = np.asarray(returns, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or len(x) < max(n_components, 2) or not np.isfinite(x).all():
        raise ValueError("GMM requires finite joint observations")
    if not 1 <= n_components <= 5 or not 0 < reg_covar <= 0.01:
        raise ValueError("Invalid GMM components or regularization")
    # sklearn accepts an integer RandomState seed; derive it from the request RNG.
    model = GaussianMixture(
        n_components=n_components,
        covariance_type="full",
        random_state=int(rng.integers(0, 2**31 - 1)),
        reg_covar=reg_covar,
        n_init=3,
        max_iter=300,
    )
    model.fit(x)
    if not model.converged_:
        raise ValueError("GMM fit did not converge")
    return model


def sample_gmm(
    gmm: GaussianMixture,
    horizon: int,
    num_paths: int,
    *,
    rng: np.random.Generator,
    applied_means: np.ndarray | None = None,
) -> np.ndarray:
    means = np.asarray(gmm.means_ if applied_means is None else applied_means)
    labels = rng.choice(len(gmm.weights_), size=num_paths * horizon, p=gmm.weights_)
    samples = np.empty((len(labels), means.shape[1]))
    # A loop over a handful of components, not paths or simulated days.
    for component in range(len(gmm.weights_)):
        mask = labels == component
        z = rng.standard_normal((int(mask.sum()), means.shape[1]))
        samples[mask] = z @ psd_factor(gmm.covariances_[component]).T + means[component]
    return samples.reshape(num_paths, horizon, means.shape[1])
