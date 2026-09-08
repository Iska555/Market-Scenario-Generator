"""Known-return histories verify data -> calibration -> paths -> API-domain results."""

from typing import Literal

import numpy as np
import pandas as pd
import pytest
from src.api.models import PortfolioSimulationRequest
from src.risk.scenarios.service import run_portfolio


@pytest.mark.parametrize("rebalance,terminal", [("daily", 1.0404), ("buy_and_hold", 1.05)])
def test_deterministic_portfolio_scenario_reconciles_all_reported_units(
    rebalance: Literal["daily", "buy_and_hold"],
    terminal: float,
) -> None:
    # Every historical interval: A +10%, B -10%; 60/40 initial weights.
    # Daily: (1.02)^2. Hold: 0.6*(1.1)^2 + 0.4*(0.9)^2.
    dates = pd.bdate_range("2025-01-01", periods=40)
    frames = {
        "AAA": pd.DataFrame({"price": 20 * 1.1 ** np.arange(40)}, index=dates),
        "BBB": pd.DataFrame({"price": 80 * 0.9 ** np.arange(40)}, index=dates),
    }

    def provider(ticker: str, years: int) -> pd.DataFrame:
        return frames[ticker]

    request = PortfolioSimulationRequest.model_validate(
        {
            "tickers": ["AAA", "BBB"],
            "weights": [0.6, 0.4],
            "horizon": 2,
            "num_paths": 100,
            "periods_per_year": 2,
            "initial_value": 2000,
            "covariance_estimator": "sample",
            "drift_model": "historical_diagnostic",
            "rebalance": rebalance,
        }
    )
    result = run_portfolio(request, provider, chart_sample_size=0)
    assert result.portfolio_paths_chart_sample == []
    np.testing.assert_allclose(
        list(result.percentiles.model_dump().values()), terminal - 1, rtol=0, atol=1e-13
    )
    np.testing.assert_allclose(
        list(result.percentile_values.model_dump().values()), 2000 * terminal, rtol=0, atol=1e-9
    )
    assert result.statistics.conditional_scenario_return_mean == pytest.approx(terminal - 1)
    assert result.statistics.annualized_return_median == pytest.approx(terminal - 1)
    assert result.statistics.max_drawdown_median == 0
    assert result.statistics.prob_loss == 0
    assert result.statistics.calmar_ratio_median is None
    assert result.statistics.calmar_defined_paths == 0
    assert result.tail_risk.var.value_pct == pytest.approx(1 - terminal)
    assert result.tail_risk.cvar.value_currency == pytest.approx(2000 * (1 - terminal))
    assert sum(bucket.count for bucket in result.histogram) == 100
    np.testing.assert_allclose(
        [a.conditional_scenario_return_mean for a in result.asset_stats], [0.21, -0.19], atol=1e-13
    )
    assert result.estimation_observations == 39
    assert result.valuation_date == str(dates[-1])


def test_constant_price_universe_has_explicit_undefined_risk_ratios() -> None:
    def provider(ticker: str, years: int) -> pd.DataFrame:
        return pd.DataFrame({"price": [100.0] * 40}, index=pd.bdate_range("2025-01-01", periods=40))

    result = run_portfolio(
        PortfolioSimulationRequest.model_validate(
            {
                "tickers": ["AAA", "BBB"],
                "num_paths": 100,
                "horizon": 2,
                "drift_model": "zero_log_drift",
                "covariance_estimator": "sample",
            }
        ),
        provider,
    )
    assert result.weights == [0.5, 0.5]
    assert result.risk_decomposition.annualized_volatility == 0
    for asset in result.asset_stats:
        assert asset.component_risk_contribution == 0
        assert asset.marginal_risk_contribution is None
        assert asset.risk_contribution_pct is None
    assert result.correlation_matrix == {
        "AAA": {"AAA": None, "BBB": None},
        "BBB": {"AAA": None, "BBB": None},
    }
    assert result.statistics.sharpe_ratio is None
    assert result.statistics.sortino_ratio is None
    assert result.statistics.calmar_ratio_median is None
    assert result.percentiles.p01 == result.percentiles.p99 == 0
