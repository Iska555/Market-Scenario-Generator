"""Reject invalid quantitative inputs instead of manufacturing finite results."""

import numpy as np
import pandas as pd
import pytest
from sklearn.mixture import GaussianMixture
from src.gmm_model import fit_gmm
from src.portfolio.paths import build_portfolio_paths
from src.risk.covariance import estimate_covariance, nearest_correlation, symmetric_matrix
from src.risk.statistics import scenario_percentiles, tail_risk


@pytest.mark.parametrize(
    "matrix", [np.array([]), np.ones((2, 3)), np.array([[np.inf]]), np.array([[1, 0], [1, 1]])]
)
def test_matrix_validation_rejects_nonfinite_nonsquare_and_asymmetric(matrix: np.ndarray) -> None:
    with pytest.raises(ValueError):
        symmetric_matrix(matrix)


def test_covariance_rejects_unknown_estimator() -> None:
    with pytest.raises(ValueError, match="estimator"):
        estimate_covariance(np.array([[1.0], [2.0]]), "unknown")  # type: ignore[arg-type]


def test_nearest_correlation_preserves_valid_singular_matrix() -> None:
    # Perfect anticorrelation is legitimate; no diagonal epsilon should be added.
    matrix = np.array([[1.0, -1.0], [-1.0, 1.0]])
    np.testing.assert_allclose(nearest_correlation(matrix), matrix, atol=1e-14)


@pytest.mark.parametrize("population", [np.array([]), np.array([np.nan]), np.array([[0.1, 0.2]])])
def test_percentiles_reject_invalid_populations(population: np.ndarray) -> None:
    with pytest.raises(ValueError):
        scenario_percentiles(population)


@pytest.mark.parametrize(
    "confidence,horizon,notional",
    [
        (0, 1, 100),
        (1, 1, 100),
        (np.nan, 1, 100),
        (0.95, 0, 100),
        (0.95, 1, 0),
        (0.95, 1, np.inf),
    ],
)
def test_tail_assumptions_must_be_valid(confidence: float, horizon: int, notional: float) -> None:
    with pytest.raises(ValueError):
        tail_risk(np.array([0.1]), confidence, horizon, notional, "USD")


@pytest.mark.parametrize(
    "prices,returns",
    [
        (np.ones(1), np.array([[0.1]])),
        (np.ones(1), np.zeros((0, 1, 1))),
        (np.ones(2), np.zeros((1, 1, 1))),
        (np.array([np.nan]), np.zeros((1, 1, 1))),
        (np.array([0.0]), np.zeros((1, 1, 1))),
        (np.ones(1), np.array([[[np.inf]]])),
    ],
)
def test_paths_reject_invalid_prices_and_tensor(prices: np.ndarray, returns: np.ndarray) -> None:
    with pytest.raises(ValueError):
        build_portfolio_paths(prices, returns)


def test_paths_reject_unimplemented_rebalancing() -> None:
    with pytest.raises(ValueError, match="rebalancing"):
        build_portfolio_paths(
            np.ones(1),
            np.zeros((1, 1, 1)),
            rebalance="monthly",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("rebalance", ["daily", "buy_and_hold"])
def test_underflow_is_rejected_without_clipping(rebalance: str) -> None:
    with pytest.raises(ValueError, match="numerical range"):
        build_portfolio_paths(
            np.ones(1),
            np.array([[[-1000.0]]]),
            rebalance=rebalance,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "values,components,regularization",
    [
        ([0.0], 1, 1e-6),
        ([0.0, np.nan], 1, 1e-6),
        ([0.0, 0.1], 0, 1e-6),
        ([0.0, 0.1], 1, 0.0),
    ],
)
def test_gmm_rejects_invalid_fit_assumptions(
    values: list[float],
    components: int,
    regularization: float,
) -> None:
    with pytest.raises(ValueError):
        fit_gmm(
            pd.Series(values), components, reg_covar=regularization, rng=np.random.default_rng(1)
        )


def test_gmm_one_component_matches_population_moments_plus_regularization() -> None:
    model = fit_gmm(pd.Series([-1.0, 0.0, 1.0]), 1, rng=np.random.default_rng(1))
    np.testing.assert_allclose(model.means_, [[0]], atol=1e-15)
    np.testing.assert_allclose(model.covariances_, [[[2 / 3 + 1e-6]]], atol=1e-14)


def test_gmm_nonconvergence_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Exercise the real fitter, then inject its documented failure status.
    original_fit = GaussianMixture.fit

    def nonconverged(model: GaussianMixture, values: np.ndarray) -> GaussianMixture:
        original_fit(model, values)
        model.converged_ = False
        return model

    monkeypatch.setattr(GaussianMixture, "fit", nonconverged)
    with pytest.raises(ValueError, match="converge"):
        fit_gmm(pd.Series([-1.0, 0.0, 1.0]), 1, rng=np.random.default_rng(1))
