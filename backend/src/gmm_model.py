import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture


def fit_gmm(returns: pd.Series, n_components: int = 3) -> GaussianMixture:
    """Fit a Gaussian Mixture Model (GMM) to daily log returns."""
    clean = returns.dropna().astype(float).values.reshape(-1, 1)  # type: ignore[union-attr]

    gmm = GaussianMixture(n_components=n_components, covariance_type="full", random_state=42)
    gmm.fit(clean)

    return gmm


def sample_gmm(gmm: GaussianMixture, horizon: int, num_paths: int) -> np.ndarray:
    """Sample synthetic returns from a fitted GMM."""
    samples, _ = gmm.sample(n_samples=horizon * num_paths)
    samples = samples.reshape(num_paths, horizon)

    return samples.astype(float)  # type: ignore[no-any-return]


if __name__ == "__main__":
    print("GMM is OK")
