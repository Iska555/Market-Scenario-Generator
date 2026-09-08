"""Analytical contracts for the Phase 1 rebuild, independent of provider data."""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest
from src.correlation import build_portfolio_paths, simulate_correlated_returns
from src.ewma_vol import compute_ewma_vol, sample_ewma_returns
from src.returns_preprocess import compute_log_returns


def test_weighted_simple_return_not_weighted_log() -> None:
    _, paths = build_portfolio_paths(
        np.array([100.0, 100.0]), np.log1p(np.array([[[0.2, -0.1]]])), np.array([0.5, 0.5])
    )
    assert paths[0, -1] == pytest.approx(1.05, abs=1e-14)


def test_paths_include_day_zero_and_buy_hold_weights_drift() -> None:
    logs = np.log1p(np.array([[[1.0, 0.0], [0.0, 1.0]]]))
    _, daily = build_portfolio_paths(np.ones(2), logs, np.array([0.5, 0.5]), rebalance="daily")
    _, hold = build_portfolio_paths(
        np.ones(2), logs, np.array([0.5, 0.5]), rebalance="buy_and_hold"
    )
    np.testing.assert_allclose(daily, [[1, 1.5, 2.25]])
    np.testing.assert_allclose(hold, [[1, 1.5, 2]])


def test_explicit_rng_isolated_and_reproducible() -> None:
    def sample(seed: int) -> np.ndarray:
        return simulate_correlated_returns(
            np.zeros(2), np.ones(2), np.eye(2), 20, 100, rng=np.random.default_rng(seed)
        )

    expected = sample(7)
    with ThreadPoolExecutor(4) as pool:
        outputs = list(pool.map(sample, [7, 8, 7, 9]))
    np.testing.assert_array_equal(outputs[0], expected)
    np.testing.assert_array_equal(outputs[2], expected)
    assert not np.array_equal(outputs[1], expected)


def test_ewma_uses_last_observation_and_missing_index() -> None:
    result = compute_ewma_vol(pd.Series([0.1, np.nan, 0.2]), lam=0.5)
    assert list(result.index) == [0, 2]
    np.testing.assert_allclose(result, np.sqrt([0.01, 0.025]))
    draws = sample_ewma_returns(0, np.zeros(3), 2, rng=np.random.default_rng(1))
    np.testing.assert_array_equal(draws, np.zeros((2, 3)))


def test_extreme_moves_and_flat_prices_survive() -> None:
    data = pd.DataFrame({"price": [100, 50, 50, 100]})
    np.testing.assert_allclose(compute_log_returns(data), [-np.log(2), 0, np.log(2)])


def test_invalid_prices_do_not_bridge_or_create_infinite_returns() -> None:
    data = pd.DataFrame({"price": [100, 0, 110, 121, np.inf, 133.1]})
    result = compute_log_returns(data)
    assert len(result) == 1
    assert result.iloc[0] == pytest.approx(np.log(1.1))


def test_duplicate_dates_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        compute_log_returns(pd.DataFrame({"price": [100, 101]}, index=[0, 0]))
