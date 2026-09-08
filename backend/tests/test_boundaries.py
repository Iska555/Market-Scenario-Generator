"""Boundary cases: no artificial certainty, clipping, or unsafe data reuse."""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest
from src.data.providers import CachedPriceProvider, PriceDataError
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol
from src.generative_model import fit_gaussian, sample_gaussian
from src.portfolio.paths import build_portfolio_paths
from src.returns_preprocess import attach_log_returns
from src.risk.covariance import estimate_covariance, risk_contributions
from src.risk.statistics import return_histogram, return_statistics, tail_risk


def test_tail_confidence_near_zero_is_defined() -> None:
    result = tail_risk(np.array([-0.5, 0.5]), 1e-20, 1, 100, "USD")
    assert result.cvar.value_pct == pytest.approx(0)


def test_gaussian_fitted_mean_and_zero_sigma_sampling() -> None:
    mean, sigma = fit_gaussian(pd.Series([0.0, 0.02]))
    assert mean == pytest.approx(0.01)
    assert sigma == pytest.approx(np.sqrt(0.0002))
    draws = sample_gaussian(mean, 0, 3, 2, rng=np.random.default_rng(2))
    np.testing.assert_array_equal(draws, np.full((2, 3), 0.01))
    with pytest.raises(ValueError):
        fit_gaussian(pd.Series([np.inf]))


def test_ewma_flat_forecast_and_invalid_inputs() -> None:
    np.testing.assert_array_equal(forecast_ewma_vol(0.3, 0.94, 3), [0.3, 0.3, 0.3])
    with pytest.raises(ValueError):
        compute_ewma_vol(pd.Series([], dtype=float))
    with pytest.raises(ValueError):
        forecast_ewma_vol(-0.1, 0.94, 1)


def test_attach_returns_preserves_only_valid_intervals() -> None:
    result = attach_log_returns(pd.DataFrame({"price": [100, np.nan, 110, 121]}))
    assert result.index.to_list() == [3]
    assert result.log_return.iloc[0] == pytest.approx(np.log(1.1))


@pytest.mark.parametrize("weights", [np.array([1.2, -0.2]), np.array([0.3, 0.3]), np.array([1.0])])
def test_portfolio_invalid_weights(weights: np.ndarray) -> None:
    with pytest.raises(ValueError):
        build_portfolio_paths(np.ones(2), np.zeros((1, 1, 2)), weights)


def test_extreme_simulated_returns_are_not_clipped() -> None:
    _, paths = build_portfolio_paths(np.ones(2), np.array([[[1.0, -1.0]]]))
    assert paths[0, -1] == pytest.approx((np.e + 1 / np.e) / 2)
    with pytest.raises(FloatingPointError):
        build_portfolio_paths(np.ones(1), np.array([[[1000.0]]]))


def test_histogram_reconciles_full_population_including_tails() -> None:
    bins = return_histogram(np.array([-0.9, 0.0, 0.1, 10.0]), 2)
    assert [b.count for b in bins] == [3, 1]
    assert bins[0].lower == -0.9
    assert bins[-1].upper == 10


def test_invalid_statistics_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        return_statistics(np.array([[-1.0, 0.1]]), 0, 252)
    with pytest.raises(ValueError):
        tail_risk(np.array([np.nan]), 0.95, 1, 100, "USD")
    with pytest.raises(ValueError):
        estimate_covariance(np.ones((1, 2)))
    with pytest.raises(ValueError):
        risk_contributions(np.eye(2), np.ones(3))


def test_cache_is_deterministic_and_returns_copies(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.data.providers as providers

    count = 0

    def download(ticker: str, years: int) -> pd.DataFrame:
        nonlocal count
        count += 1
        return pd.DataFrame({"price": [100.0, 101.0]})

    monkeypatch.setattr(providers, "download_price_data", download)
    cache = CachedPriceProvider(max_entries=1)
    with ThreadPoolExecutor(4) as pool:
        frames = list(pool.map(lambda _: cache("AAA", 1), range(4)))
    assert count == 1
    frames[0].iloc[0, 0] = 999
    assert frames[1].iloc[0, 0] == 100
    assert cache("AAA", 1).iloc[0, 0] == 100
    cache("BBB", 1)
    cache("AAA", 1)
    assert count == 3


def test_cache_expiration_and_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.data.providers as providers

    instant = [0.0]
    monkeypatch.setattr(providers.time, "monotonic", lambda: instant[0])
    monkeypatch.setattr(
        providers,
        "download_price_data",
        lambda *args: pd.DataFrame({"price": [100.0 + instant[0]]}),
    )
    cache = CachedPriceProvider(ttl_seconds=10)
    assert cache("AAA", 1).iloc[0, 0] == 100
    instant[0] = 20
    assert cache("AAA", 1).iloc[0, 0] == 120

    def fail(*args: object) -> pd.DataFrame:
        raise ValueError("Bad provider data")

    monkeypatch.setattr(providers, "download_price_data", fail)
    with pytest.raises(PriceDataError):
        cache("BBB", 1)


def test_yahoo_adjusted_close_multilevel_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.data_download as adapter

    frame = pd.DataFrame([[100.0], [101.0]], columns=pd.MultiIndex.from_tuples([("Close", "AAA")]))
    monkeypatch.setattr(adapter.yf, "download", lambda *args, **kwargs: frame)
    result = adapter.download_price_data("AAA")
    assert result.price.to_list() == [100, 101]
    assert result.attrs["source"] == "yfinance:auto_adjust=True:Close"
    assert result.attrs["retrieved_at"]
