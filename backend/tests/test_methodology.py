"""Independent answers for model moments and finite-population conventions."""

import numpy as np
import pandas as pd
import pytest
from sklearn.mixture import GaussianMixture
from src.ewma_vol import sample_ewma_returns
from src.generative_model import fit_gaussian, sample_gaussian
from src.gmm_model import sample_gmm
from src.risk.covariance import estimate_covariance, simulate_correlated_returns
from src.risk.statistics import return_histogram, return_statistics, scenario_percentiles, tail_risk


def test_gaussian_fit_uses_sample_variance_and_no_ito_adjustment() -> None:
    # Mean=0.2; squared deviations total=0.02; sample variance=0.01.
    mean, sigma = fit_gaussian(pd.Series([0.1, np.nan, 0.2, 0.3]))
    assert mean == pytest.approx(0.2)
    assert sigma == pytest.approx(0.1)
    draws = sample_gaussian(mean, 0, 3, 2, rng=np.random.default_rng(4))
    np.testing.assert_allclose(draws, np.full((2, 3), 0.2), atol=1e-15)


def test_gaussian_sampler_preserves_declared_moments() -> None:
    draws = sample_gaussian(0.03, 0.2, 10, 20_000, rng=np.random.default_rng(11))
    # Tolerances exceed six normal sampling standard errors for 200,000 draws.
    assert draws.shape == (20_000, 10)
    assert draws.mean() == pytest.approx(0.03, abs=0.003)
    assert draws.var() == pytest.approx(0.04, abs=0.001)


def test_correlated_sampler_scales_each_asset_after_joint_shocks() -> None:
    # rho=0.6, sigmas=(2,3) => covariance=3.6, variances=(4,9).
    draws = simulate_correlated_returns(
        np.array([1.0, -2.0]),
        np.array([2.0, 3.0]),
        np.array([[1.0, 0.0], [0.6, 0.8]]),
        10,
        20_000,
        rng=np.random.default_rng(21),
    ).reshape(-1, 2)
    np.testing.assert_allclose(draws.mean(axis=0), [1, -2], atol=0.05)
    np.testing.assert_allclose(np.cov(draws, rowvar=False), [[4, 3.6], [3.6, 9]], atol=0.2)


def test_ewma_sampler_preserves_nonzero_drift_and_each_forecast_scale() -> None:
    draws = sample_ewma_returns(
        0.1, np.array([0, 0.2, 0.4]), 200_000, rng=np.random.default_rng(31)
    )
    np.testing.assert_array_equal(draws[:, 0], np.full(200_000, 0.1))
    np.testing.assert_allclose(draws.mean(axis=0), [0.1, 0.1, 0.1], atol=0.006)
    np.testing.assert_allclose(draws.var(axis=0), [0, 0.04, 0.16], atol=0.004)


def test_gmm_total_covariance_includes_within_and_between_regime_risk() -> None:
    model = GaussianMixture(n_components=2, covariance_type="full")
    model.weights_ = np.array([0.25, 0.75])
    model.means_ = np.array([[-1.0, 0.0], [1.0, 2.0]])
    model.covariances_ = np.array([[[1, 0.5], [0.5, 2]], [[2, -0.25], [-0.25, 1]]])
    # Mean=(0.5,1.5); between variance/covariance=0.75 in all entries.
    # Within covariance=[[1.75,-0.0625],[-0.0625,1.25]].
    draws = sample_gmm(model, 10, 20_000, rng=np.random.default_rng(41)).reshape(-1, 2)
    np.testing.assert_allclose(draws.mean(axis=0), [0.5, 1.5], atol=0.03)
    np.testing.assert_allclose(np.cov(draws, rowvar=False), [[2.5, 0.6875], [0.6875, 2]], atol=0.06)
    centered = sample_gmm(
        model,
        10,
        20_000,
        rng=np.random.default_rng(41),
        applied_means=np.array([[-1.5, -1.5], [0.5, 0.5]]),
    ).reshape(-1, 2)
    np.testing.assert_allclose(draws - centered, np.tile([0.5, 1.5], (len(draws), 1)))
    assert np.linalg.norm(centered.mean(axis=0)) > 1e-6  # No realized-sample demeaning.


def test_ledoit_wolf_uses_mle_denominator_and_isotropic_target() -> None:
    observations = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=float)
    shrunk = estimate_covariance(observations)
    # Centered cross products = 2I; T=4. S_MLE=0.5I equals shrinkage target.
    np.testing.assert_allclose(shrunk.matrix, [[0.5, 0], [0, 0.5]], atol=1e-15)
    sample = estimate_covariance(observations, "sample")
    np.testing.assert_allclose(sample.matrix, [[2 / 3, 0], [0, 2 / 3]], atol=1e-15)
    single = estimate_covariance(np.array([[1.0], [2.0], [3.0]]), "sample")
    np.testing.assert_array_equal(single.matrix, [[1.0]])


def test_statistics_annualize_each_path_before_taking_median() -> None:
    stats = return_statistics(np.array([[0.1, 0.1], [-0.1, -0.1]]), 0, 4)
    # Two-period terminal values: 1.21 and 0.81; annualized: 1.4641 and 0.6561.
    assert stats.conditional_scenario_return_mean == pytest.approx(0.01)
    assert stats.annualized_return_median == pytest.approx(0.0601)
    assert stats.annualized_volatility == pytest.approx(np.sqrt(0.16 / 3))
    assert stats.prob_loss == 0.5
    assert stats.min_return == pytest.approx(-0.19)
    assert stats.max_return == pytest.approx(0.21)
    assert stats.max_drawdown_median == pytest.approx(0.095)
    assert stats.max_drawdown_p95 == pytest.approx(0.1805)


def test_ledoit_wolf_nonisotropic_shrinkage_has_known_weight_and_covariance() -> None:
    # S_MLE=diag(2, 1/2), target=(5/4)I, p=2, T=4.
    # beta=(mean(||x||^4)-||S||_F^2)/(p*T)=(17/2-17/4)/8=17/32.
    # delta=||S-target||_F^2/p=9/16; lambda=beta/delta=17/18.
    # (1-lambda)S+lambda*target=diag(31/24,29/24).
    result = estimate_covariance(np.array([[2, 0], [-2, 0], [0, 1], [0, -1]], dtype=float))
    assert result.shrinkage == pytest.approx(17 / 18, abs=1e-14)
    np.testing.assert_allclose(result.matrix, [[31 / 24, 0], [0, 29 / 24]], atol=1e-14)


@pytest.mark.parametrize(
    "population", [np.array([]), np.array([np.nan]), np.array([np.inf]), np.array([[0.0, 1.0]])]
)
def test_histogram_rejects_missing_or_invalid_population(population: np.ndarray) -> None:
    with pytest.raises(ValueError):
        return_histogram(population)


def test_histogram_boundary_atoms_and_identical_population_reconcile() -> None:
    bins = return_histogram(np.array([0, 0.5, 1, 1.5, 2]), bins=2)
    assert [(b.lower, b.upper, b.count) for b in bins] == [(0, 1, 2), (1, 2, 3)]
    equal = return_histogram(np.full(10, 0.1))
    assert sum(b.count for b in equal) == 10
    assert sum(b.count > 0 for b in equal) == 1


def test_tail_ties_and_sub_observation_mass_do_not_enlarge_the_tail() -> None:
    # Worst half: [0.4,0.2], not all three losses at/above the VaR=0.2 boundary.
    tied = tail_risk(np.array([-0.4, -0.2, -0.2, 0.1]), 0.5, 1, 100, "USD")
    assert tied.var.value_pct == pytest.approx(0.2)
    assert tied.cvar.value_pct == pytest.approx(0.3)
    tiny = tail_risk(np.array([-0.4, 0.2]), 0.99, 1, 100, "USD")
    assert tiny.cvar.value_pct == pytest.approx(0.4)
    singleton = tail_risk(np.array([0.1]), 0.95, 2, 500, "EUR")
    assert singleton.cvar.value_pct == pytest.approx(-0.1)
    assert singleton.cvar.value_currency == pytest.approx(-50)
    assert singleton.cvar.currency == "EUR"
    assert scenario_percentiles(np.array([0.1])).p99 == pytest.approx(0.1)
