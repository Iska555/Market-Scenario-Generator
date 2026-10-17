"""Offline endpoint contracts exercise real model and statistics implementations."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, make_prices: Callable[..., pd.DataFrame]) -> TestClient:
    import main

    def provider(ticker: str, years: int) -> pd.DataFrame:
        return make_prices(n_days=100, seed=sum(ticker.encode()), mu=0.001)

    monkeypatch.setattr(main, "get_cached_price_data", provider)
    return TestClient(main.app)


def request_body(model: str = "gaussian") -> dict[str, object]:
    return {
        "tickers": ["AAA", "BBB"],
        "weights": [0.6, 0.4],
        "horizon": 5,
        "num_paths": 100,
        "model": model,
        "drift_model": "historical_diagnostic",
        "random_seed": 7,
        "initial_value": 1000,
    }


@pytest.mark.parametrize("model", ["gaussian", "gmm"])
def test_portfolio_contract_full_population(client: TestClient, model: str) -> None:
    response = client.post("/api/simulate-portfolio", json=request_body(model))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["api_version"] == "3.0.0"
    assert len(result["portfolio_paths_chart_sample"]) == 30
    assert len(result["portfolio_paths_chart_sample"][0]) == 6
    assert result["portfolio_paths_chart_sample"][0][0] == 1000
    assert sum(b["count"] for b in result["histogram"]) == 100
    assert result["tail_risk"]["var"]["horizon_days"] == 5
    assert result["tail_risk"]["var"]["value_currency"] == pytest.approx(
        1000 * result["tail_risk"]["var"]["value_pct"]
    )
    assert sum(a["component_risk_contribution"] for a in result["asset_stats"]) == pytest.approx(
        result["risk_decomposition"]["annualized_volatility"], abs=1e-12
    )
    if model == "gmm":
        assert len(result["model_diagnostics"]["fitted_component_probabilities"]) == 3
        assert len(result["model_diagnostics"]["component_covariances"][0]) == 2


@pytest.mark.parametrize("model", ["gaussian", "gmm", "ewma"])
def test_single_asset_one_day_is_finite(client: TestClient, model: str) -> None:
    response = client.post(
        "/api/simulate",
        json={
            "ticker": "AAA",
            "model": model,
            "horizon": 1,
            "num_paths": 100,
            "drift_model": "zero_log_drift",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["paths_chart_sample"][0]) == 2
    assert np.isfinite(result["statistics"]["annualized_volatility"])
    assert result["model_diagnostics"]["applied_daily_log_means"] == [0.0]


@pytest.mark.parametrize("model", ["gaussian", "gmm", "ewma"])
def test_concurrent_requests_byte_identical(client: TestClient, model: str) -> None:
    body = {
        "ticker": "AAA",
        "model": model,
        "horizon": 5,
        "num_paths": 100,
        "random_seed": 42,
        "drift_model": "historical_diagnostic",
    }
    expected = client.post("/api/simulate", json=body)
    assert expected.status_code == 200, expected.text

    def run(seed: int) -> bytes:
        response = client.post("/api/simulate", json={**body, "random_seed": seed})
        assert response.status_code == 200, response.text
        return response.content

    with ThreadPoolExecutor(4) as pool:
        values = list(pool.map(run, [42, 9, 42, 42]))
    assert values[0] == values[2] == values[3] == expected.content
    assert values[1] != expected.content


@pytest.mark.parametrize(
    "overrides",
    [
        {"tickers": ["AAA", "aaa"]},
        {"tickers": ["", "BBB"]},
        {"weights": [1.2, -0.2]},
        {"weights": [0.5]},
        {"weights": [0.4, 0.4]},
        {"horizon": 1000, "num_paths": 5000},
        {"random_seed": -1},
        {"model": "ewma"},
    ],
)
def test_bad_requests_rejected_before_provider(
    client: TestClient, overrides: dict[str, object]
) -> None:
    response = client.post("/api/simulate-portfolio", json={**request_body(), **overrides})
    assert response.status_code == 422


def test_drift_selection_required(client: TestClient) -> None:
    response = client.post("/api/simulate", json={"ticker": "AAA"})
    assert response.status_code == 422


def test_extremely_small_positive_confidence_has_no_server_error(client: TestClient) -> None:
    response = client.post("/api/simulate-portfolio", json={**request_body(), "confidence": 1e-20})
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("number", ["1e999", "NaN", "Infinity", "-Infinity"])
def test_nonfinite_input_validation_is_json_serializable(
    client: TestClient, number: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import main

    def forbidden_provider(*args: object) -> pd.DataFrame:
        raise AssertionError("Invalid request reached provider")

    monkeypatch.setattr(main, "get_cached_price_data", forbidden_provider)
    response = client.post(
        "/api/simulate-portfolio",
        content='{"tickers":["AAA","BBB"],"drift_model":"zero_log_drift","weights":['
        + number
        + ",0]}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]


def test_full_population_differs_from_chart_sample(client: TestClient) -> None:
    import main
    from src.api.models import PortfolioSimulationRequest
    from src.risk.scenarios.service import run_portfolio

    request = PortfolioSimulationRequest.model_validate(request_body())
    complete = run_portfolio(request, main.get_cached_price_data, chart_sample_size=100)
    truncated = run_portfolio(request, main.get_cached_price_data, chart_sample_size=1)
    assert complete.percentiles == truncated.percentiles
    assert complete.statistics == truncated.statistics
    paths = np.asarray(complete.portfolio_paths_chart_sample)
    terminal = paths[:, -1] / request.initial_value - 1
    assert truncated.percentiles.p01 == pytest.approx(np.percentile(terminal, 1))
    assert truncated.percentiles.p99 == pytest.approx(np.percentile(terminal, 99))


def test_gaussian_historical_log_mean_not_ito_adjusted(client: TestClient) -> None:
    response = client.post(
        "/api/simulate",
        json={
            "ticker": "AAA",
            "num_paths": 100,
            "horizon": 1,
            "drift_model": "historical_diagnostic",
            "covariance_estimator": "sample",
        },
    )
    assert response.status_code == 200, response.text
    import main
    from src.returns_preprocess import compute_log_returns

    mean = compute_log_returns(main.get_cached_price_data("AAA", 3)).mean()
    assert response.json()["model_diagnostics"]["applied_daily_log_means"][0] == pytest.approx(mean)


@pytest.mark.parametrize("model", ["gaussian", "gmm"])
def test_portfolio_concurrent_seed_reproducibility(client: TestClient, model: str) -> None:
    body = request_body(model)
    expected = client.post("/api/simulate-portfolio", json=body)
    assert expected.status_code == 200, expected.text

    def run(seed: int) -> bytes:
        response = client.post("/api/simulate-portfolio", json={**body, "random_seed": seed})
        assert response.status_code == 200, response.text
        return response.content

    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(run, [7, 8, 7, 9]))
    assert results[0] == results[2] == expected.content
    assert results[1] != expected.content


def test_global_random_state_is_not_accessed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Legacy global RNG accessed")

    monkeypatch.setattr(np.random, "seed", forbidden)
    monkeypatch.setattr(np.random, "randn", forbidden)
    for model in ("gaussian", "gmm"):
        response = client.post("/api/simulate-portfolio", json=request_body(model))
        assert response.status_code == 200, response.text


def test_http_failures_and_build_identity_are_explicit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import main
    from src.data.providers import PriceDataError

    assert client.get("/api/version").json()["api_version"] == "3.0.0"
    assert client.get("/ping").status_code == 200
    assert client.get("/").json()["version"] == "3.0.0"

    def unavailable(*args: object) -> pd.DataFrame:
        raise PriceDataError("Provider unavailable")

    monkeypatch.setattr(main, "get_cached_price_data", unavailable)
    assert client.post("/api/simulate-portfolio", json=request_body()).status_code == 503
    assert (
        client.post(
            "/api/simulate", json={"ticker": "AAA", "drift_model": "zero_log_drift"}
        ).status_code
        == 503
    )
    monkeypatch.setattr(
        main, "get_cached_price_data", lambda *args: pd.DataFrame({"price": [100.0]})
    )
    assert client.post("/api/simulate-portfolio", json=request_body()).status_code == 422
    assert (
        client.post(
            "/api/simulate", json={"ticker": "AAA", "drift_model": "zero_log_drift"}
        ).status_code
        == 422
    )


def test_release_preflight_and_rejected_access_keep_cors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test@localhost/isolated")
    monkeypatch.setenv("RESEARCH_API_KEY", "synthetic-release-test-key-123456789")
    origin = "http://localhost:5173"
    preflight = client.options(
        "/api/simulate-portfolio",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-research-key",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    rejected = client.post(
        "/api/simulate-portfolio", json=request_body(), headers={"Origin": origin}
    )
    assert rejected.status_code == 401
    assert rejected.headers["access-control-allow-origin"] == origin
    assert rejected.headers["cache-control"] == "no-store"
    monkeypatch.setenv("ENABLE_PRIVATE_SIMULATIONS", "1")
    accepted = client.post(
        "/api/simulate-portfolio",
        json=request_body(),
        headers={"X-Research-Key": "synthetic-release-test-key-123456789"},
    )
    assert accepted.status_code == 200
    assert accepted.headers["content-encoding"] == "gzip"


def test_release_refuses_overlapping_tensor_work_and_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio
    from threading import Event

    import main
    from fastapi import HTTPException

    monkeypatch.setenv("PUBLIC_RELEASE_MODE", "1")
    entered, finish = Event(), Event()

    def blocked() -> int:
        entered.set()
        assert finish.wait(5)
        return 7

    async def check() -> None:
        first = asyncio.create_task(main.execute_scenario(blocked))
        try:
            assert await asyncio.to_thread(entered.wait, 3)
            with pytest.raises(HTTPException) as failure:
                await main.execute_scenario(lambda: 9)
            assert failure.value.status_code == 503
            assert failure.value.headers == {"Retry-After": "5"}
        finally:
            finish.set()
        assert await first == 7
        assert await main.execute_scenario(lambda: 9) == 9

    asyncio.run(check())
