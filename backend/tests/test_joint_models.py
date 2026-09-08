"""Joint-mixture regression: mixture moments and iid component allocation."""

import numpy as np
import pandas as pd
import pytest
from sklearn.mixture import GaussianMixture
from src.gmm_model import fit_gmm, sample_gmm


def test_joint_sampling_preserves_regimes_without_grouping_paths() -> None:
    model = GaussianMixture(n_components=2, covariance_type="full")
    model.weights_ = np.array([0.5, 0.5])
    model.means_ = np.array([[-0.5, -0.25], [0.5, 0.25]])
    model.covariances_ = np.array([np.eye(2) * 1e-8, np.eye(2) * 1e-8])
    draws = sample_gmm(model, 100, 1000, rng=np.random.default_rng(4))
    assert draws.shape == (1000, 100, 2)
    assert draws[:, :, 0].mean() == pytest.approx(0, abs=0.006)
    assert draws[:, :, 0].var() == pytest.approx(0.25, abs=0.001)
    assert np.abs(draws[:, :, 0]).min() > 0.49  # Gaussian substitution fails.
    assert np.mean(np.abs(draws[:, :, 0].mean(axis=1)) < 0.2) > 0.99
    assert np.corrcoef(draws.reshape(-1, 2), rowvar=False)[0, 1] > 0.99


def test_fit_joint_and_reproduce_seed_with_no_sample_demean() -> None:
    rng = np.random.default_rng(7)
    observations = pd.DataFrame(rng.normal([0.1, -0.02], [0.02, 0.04], (500, 2)))
    model = fit_gmm(observations, 2, rng=np.random.default_rng(9))
    assert model.means_.shape == (2, 2)
    a = sample_gmm(model, 5, 100, rng=np.random.default_rng(8))
    b = sample_gmm(model, 5, 100, rng=np.random.default_rng(8))
    np.testing.assert_array_equal(a, b)
    assert a[:, :, 0].mean() > 0.09
