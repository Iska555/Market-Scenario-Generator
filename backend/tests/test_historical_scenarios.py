"""Analytical tests for supplied joint scenarios and private access."""

from typing import Any
from uuid import UUID

import numpy as np
import pytest
from pydantic import ValidationError
from src.risk.scenarios.historical import evaluate_scenario, joint_blocks
from src.risk.scenarios.historical_contracts import StressRequest

IDS = [str(UUID(int=1)), str(UUID(int=2))]


def request(**changes: Any) -> StressRequest:
    body: dict[str, Any] = {
        "method": "historical_replay",
        "scenario_name": "Supplied interval",
        "rationale": "Owner-selected stress evidence",
        "assets": [{"security_id": IDS[0], "weight": 0.6}, {"security_id": IDS[1], "weight": 0.4}],
        "currency": "USD",
        "valuation_date": "2026-01-05",
        "valuation_calendar": "XNYS",
        "as_of": "2026-01-05T00:00:00Z",
        "known_at": "2026-01-05T00:00:00Z",
        "initial_value": 100,
        "rebalance": "per_observation",
        "risk_free_rate": 0,
        "history": {
            "security_ids": IDS,
            "observations": [
                {"start": "2026-01-01", "end": "2026-01-02", "returns": [0.1, -0.1]},
                {"start": "2026-01-02", "end": "2026-01-03", "returns": [-0.2, 0.2]},
                {"start": "2026-01-03", "end": "2026-01-04", "returns": [0.3, -0.3]},
            ],
            "frequency": "daily",
            "periods_per_year": 252,
            "source": "Supplied test evidence",
            "retrieved_at": "2026-01-04T12:00:00Z",
            "adjustment_policy": "Nominal total returns including distributions",
            "interval_alignment": "identical_start_end_and_valuation_cutoff",
        },
    }
    return StressRequest.model_validate({**body, **changes})


def test_replay_uses_complete_joint_sequence_and_simple_arithmetic() -> None:
    result = evaluate_scenario(request())
    expected = np.array([1, 1.02, 1.02 * 0.96, 1.02 * 0.96 * 1.06])
    np.testing.assert_allclose(result.portfolio_paths_chart_sample[0], expected)
    assert result.scenario_mean_terminal_return == pytest.approx(expected[-1] - 1)
    assert result.horizon_periods == 3
    assert result.scenario_var.value is None
    assert result.scenario_var.reason


def test_buy_and_hold_allows_weights_to_drift() -> None:
    result = evaluate_scenario(request(rebalance="buy_and_hold"))
    expected = 0.6 * 1.1 * 0.8 * 1.3 + 0.4 * 0.9 * 1.2 * 0.7 - 1
    assert result.scenario_mean_terminal_return == pytest.approx(expected)


def test_blocks_preserve_joint_rows_and_contiguous_blocks_reproducibly() -> None:
    rows = np.array([[i, -i] for i in range(8)], dtype=float)
    draws = joint_blocks(rows, horizon=7, paths=100, block_length=3, seed=48)
    np.testing.assert_array_equal(draws, joint_blocks(rows, 7, 100, 3, 48))
    np.testing.assert_array_equal(draws[:, :, 0], -draws[:, :, 1])
    for start, stop in [(0, 3), (3, 6)]:
        np.testing.assert_array_equal(np.diff(draws[:, start:stop, 0]), np.ones((100, 2)))


def test_bootstrap_full_population_and_explicit_seed() -> None:
    req = request(
        method="block_bootstrap",
        horizon_periods=5,
        path_count=80,
        block_length=2,
        seed=15,
        confidence=0.95,
        mean_policy="resample_observed_returns_not_expected_return",
    )
    result = evaluate_scenario(req)
    assert result == evaluate_scenario(req)
    assert result.population_size == 80
    assert len(result.portfolio_paths_chart_sample) == 30
    assert req.history is not None
    assert result.terminal_return_percentiles is not None
    rows = np.array([r.returns for r in req.history.observations])
    draws = joint_blocks(rows, 5, 80, 2, 15)
    terminals = np.prod(1 + draws @ np.array([0.6, 0.4]), axis=1) - 1
    assert result.scenario_mean_terminal_return == pytest.approx(terminals.mean())
    assert result.terminal_return_percentiles.p95 == pytest.approx(np.percentile(terminals, 95))
    assert result.scenario_var.value == pytest.approx(np.quantile(-terminals, 0.95))


def test_shock_supports_total_loss_and_weighted_simple_returns() -> None:
    result = evaluate_scenario(
        request(
            method="deterministic_shock",
            history=None,
            risk_free_rate=None,
            rebalance=None,
            shocks=[-1, 0.25],
            shock_horizon_label="Immediate mark-to-market",
        )
    )
    assert result.scenario_mean_terminal_return == pytest.approx(-0.5)
    assert result.portfolio_paths_chart_sample == [[1, 0.5]]
    assert result.scenario_var.value is None
    assert result.scenario_annualized_volatility.reason


@pytest.mark.parametrize(
    "changes",
    [
        {"method": "block_bootstrap", "horizon_periods": 10, "path_count": 20, "block_length": 2},
        {
            "method": "block_bootstrap",
            "horizon_periods": 1000,
            "path_count": 2000,
            "block_length": 2,
            "seed": 1,
            "confidence": 0.95,
            "mean_policy": "resample_observed_returns_not_expected_return",
        },
        {
            "assets": [
                {"security_id": IDS[0], "weight": 0.4},
                {"security_id": IDS[1], "weight": 0.4},
            ]
        },
        {"as_of": "2026-01-02T00:00:00Z"},
        {"known_at": "2026-01-03T00:00:00Z"},
        {"method": "deterministic_shock", "history": None, "shocks": [-1.01, 0]},
        {"method": "historical_replay", "seed": 4},
    ],
)
def test_invalid_domains_fail_explicitly(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        request(**changes)


def test_complete_loss_history_is_rejected_never_removed() -> None:
    sample = request().history
    assert sample is not None
    history = sample.model_dump(mode="json")
    history["observations"][1]["returns"][0] = -1
    with pytest.raises(ValidationError, match="complete-loss"):
        request(history=history)


def test_private_route_security_currency_and_replay_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from src.research import database
    from src.research.routes import router as research_router
    from src.research.tables import Base
    from src.risk.scenarios.historical_routes import router

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(research_router)
    app.include_router(router)
    app.dependency_overrides[database.get_engine] = lambda: engine
    key = "offline-stress-owner-key-32-characters"
    monkeypatch.setenv("RESEARCH_API_KEY", key)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test@localhost/research")
    url = "/api/research/stress/evaluate"
    with TestClient(app) as client:
        body = request().model_dump(mode="json")
        assert client.post(url, json=body).status_code == 401
        client.headers["X-Research-Key"] = key
        assert client.post(url, json=body).status_code == 404
        registered = []
        for ticker in ["AAA", "BBB"]:
            security = client.post(
                "/api/research/securities",
                json={
                    "ticker": ticker,
                    "name": ticker,
                    "exchange": "XNYS",
                    "currency": "USD",
                    "country": "US",
                },
            ).json()
            registered.append(security["id"])
        for asset, identifier in zip(body["assets"], registered, strict=True):
            asset["security_id"] = identifier
        body["history"]["security_ids"] = registered
        response = client.post(url, json=body)
        assert response.status_code == 200, response.text
        output = response.json()
        assert response.headers["cache-control"] == "no-store"
        assert output["manifest"]["resolved_inputs"] == body
        assert len(output["manifest"]["securities"]) == 2
        assert output["manifest"]["code_sha256"]
        assert output["manifest"]["library_versions"]["numpy"]
        replay = client.post(url, json=output["manifest"]["resolved_inputs"]).json()
        assert replay["result"] == output["result"]
        assert replay["manifest"]["input_sha256"] == output["manifest"]["input_sha256"]
        assert client.post(url, json={**body, "currency": "EUR"}).status_code == 422
    engine.dispose()


def test_three_asset_complete_loss_has_exact_zero_wealth() -> None:
    weights = [0.18549529933759284, 0.5905947117139919, 0.22390998894841518]
    result = evaluate_scenario(
        request(
            method="deterministic_shock",
            history=None,
            risk_free_rate=None,
            rebalance=None,
            shocks=[-1, -1, -1],
            shock_horizon_label="Immediate",
            assets=[
                {"security_id": str(UUID(int=i + 1)), "weight": w} for i, w in enumerate(weights)
            ],
        )
    )
    assert result.scenario_mean_terminal_value == 0
    assert result.scenario_mean_terminal_return == -1
    assert result.portfolio_paths_chart_sample == [[1, 0]]
    assert result.scenario_max_drawdown_median == 1


def test_counts_and_complete_loss_roundoff() -> None:
    result = evaluate_scenario(
        request(
            method="block_bootstrap",
            horizon_periods=5,
            path_count=80,
            block_length=2,
            seed=15,
            confidence=0.95,
            mean_policy="resample_observed_returns_not_expected_return",
        )
    )
    assert result.tail_effective_count == pytest.approx(4)
    assert result.calmar_total_paths == 80
    assert 0 <= result.calmar_defined_paths <= 80
    shock = evaluate_scenario(
        request(
            method="deterministic_shock",
            history=None,
            risk_free_rate=None,
            rebalance=None,
            shocks=[-1, -1],
            shock_horizon_label="Immediate",
            assets=[
                {"security_id": IDS[0], "weight": 0.50000000001},
                {"security_id": IDS[1], "weight": 0.5},
            ],
        )
    )
    assert shock.scenario_mean_terminal_value == 0
    assert shock.scenario_mean_terminal_return == -1
    assert shock.tail_effective_count is None


@pytest.mark.parametrize(
    "changes",
    [
        {
            "assets": [
                {"security_id": IDS[0], "weight": 0.5},
                {"security_id": IDS[0], "weight": 0.5},
            ]
        },
        {"valuation_date": "2026-01-01"},
        {"method": "deterministic_shock", "shocks": [-1, 0], "shock_horizon_label": "Now"},
        {"shocks": [-1, 0]},
        {"history": None},
        {"risk_free_rate": None},
        {
            "method": "block_bootstrap",
            "horizon_periods": 1,
            "path_count": 2,
            "block_length": 4,
            "seed": 0,
            "confidence": 0.95,
            "mean_policy": "resample_observed_returns_not_expected_return",
        },
    ],
)
def test_family_specific_inputs_are_not_silently_ignored(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        request(**changes)


def test_history_identifiers_must_match_exact_order() -> None:
    sample = request().history
    assert sample is not None
    body = sample.model_dump(mode="json")
    body["security_ids"] = IDS[::-1]
    with pytest.raises(ValidationError, match="ordered"):
        request(history=body)


@pytest.mark.parametrize(
    "rows,horizon,paths,block_length",
    [
        (np.empty((0, 2)), 1, 1, 1),
        (np.ones((2, 2)), 0, 1, 1),
        (np.ones((2, 2)), 1, 1, 3),
        (np.ones((2, 2)), 2000, 2000, 1),
        (np.ones(2), 1, 1, 1),
        (np.array([[np.inf]]), 1, 1, 1),
    ],
)
def test_block_domain_rejects_before_allocation(
    rows: np.ndarray, horizon: int, paths: int, block_length: int
) -> None:
    with pytest.raises(ValueError):
        joint_blocks(rows, horizon, paths, block_length, 1)
