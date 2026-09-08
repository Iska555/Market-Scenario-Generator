"""Known-answer checks for ratios, tail risk, covariance and contribution."""

import numpy as np
import pytest


def test_zero_expected_excess_sharpe_and_sortino() -> None:
    from src.risk.statistics import return_statistics

    # Annual effective rf=21%, two observations/year => per-period rf=10%.
    # Arithmetic mean of +0%, +20% is exactly rf, with nonzero volatility.
    stats = return_statistics(np.array([[0.0, 0.2]]), risk_free_rate=0.21, periods=2)
    assert stats.sharpe_ratio == pytest.approx(0, abs=1e-14)
    assert stats.sortino_ratio == pytest.approx(0, abs=1e-14)
    assert stats.annualized_volatility == pytest.approx(0.2)


def test_sortino_uses_all_periods_and_calmar_is_pathwise() -> None:
    from src.risk.statistics import return_statistics

    stats = return_statistics(np.array([[0.2, -0.25, 2 / 9]]), 0, 3)
    assert stats.max_drawdown_median == pytest.approx(0.25)
    assert stats.annualized_return_median == pytest.approx(0.10)
    assert stats.calmar_ratio_median == pytest.approx(0.4)
    assert stats.sortino_ratio == pytest.approx((0.2 - 0.25 + 2 / 9) / 0.25)


def test_day_one_drawdown_and_undefined_ratios() -> None:
    from src.risk.statistics import return_statistics

    stats = return_statistics(np.array([[-0.2]]), 0, 252)
    assert stats.max_drawdown_median == pytest.approx(0.2)
    assert stats.annualized_volatility is None
    assert stats.sharpe_ratio is None
    flat = return_statistics(np.zeros((2, 3)), 0, 252)
    assert flat.sharpe_ratio is None
    assert flat.sortino_ratio is None
    assert flat.calmar_ratio_median is None


def test_full_population_percentiles() -> None:
    from src.risk.statistics import scenario_percentiles

    result = scenario_percentiles(np.arange(101) / 100)
    assert result.p01 == pytest.approx(0.01)
    assert result.p50 == pytest.approx(0.5)
    assert result.p99 == pytest.approx(0.99)


def test_calmar_does_not_silently_discard_paths_without_drawdowns() -> None:
    from src.risk.statistics import return_statistics

    stats = return_statistics(np.array([[0.1], [0.2], [-0.1]]), 0, 1)
    assert stats.calmar_ratio_median is None
    assert stats.calmar_defined_paths == 1
    assert stats.calmar_total_paths == 3


def test_tail_confidence_horizon_currency_and_fractional_atom() -> None:
    from src.risk.statistics import tail_risk

    # Worst 37.5% = 1.5 equally weighted atoms: 40% loss and half of 20% loss.
    risk = tail_risk(np.array([-0.4, -0.2, 0.1, 0.3]), 0.625, 10, 1000, "USD")
    assert risk.var.value_pct == pytest.approx(0.1625)
    assert risk.cvar.value_pct == pytest.approx(1 / 3)
    assert risk.cvar.value_currency == pytest.approx(1000 / 3)
    assert risk.var.confidence == 0.625
    assert risk.var.horizon_days == 10
    assert risk.var.convention == "loss_positive"
    assert tail_risk(np.ones(10) * 0.1, 0.95, 1, 100, "USD").var.value_pct == -0.1


def test_risk_contributions_reconcile_and_can_be_negative() -> None:
    from src.risk.covariance import risk_contributions

    result = risk_contributions(np.array([[0.04, 0.006], [0.006, 0.09]]), np.array([0.6, 0.4]))
    assert result.volatility == pytest.approx(np.sqrt(0.03168))
    assert result.component.sum() == pytest.approx(result.volatility, abs=1e-14)
    assert result.percentage is not None
    assert result.percentage.sum() == pytest.approx(1)
    hedge = risk_contributions(np.array([[1.0, -1.5], [-1.5, 4.0]]), np.array([0.9, 0.1]))
    assert hedge.component[1] < 0
    zero = risk_contributions(np.zeros((2, 2)), np.array([0.5, 0.5]))
    assert zero.percentage is None


def test_singular_and_indefinite_correlation_handling() -> None:
    from src.risk.covariance import nearest_correlation, psd_factor

    singular = np.ones((2, 2))
    factor = psd_factor(singular)
    np.testing.assert_allclose(factor @ factor.T, singular, atol=1e-14)
    repaired = nearest_correlation(np.array([[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]]))
    np.testing.assert_allclose(np.diag(repaired), 1, atol=1e-12)
    assert np.linalg.eigvalsh(repaired).min() >= -1e-12
    np.testing.assert_allclose(repaired[0, 1:], [0.5, 0.5], atol=1e-8)
    with pytest.raises(ValueError):
        psd_factor(np.array([[1, 2], [2, 1]]))


def test_sample_covariance_and_shrinkage_are_explicit() -> None:
    from src.risk.covariance import estimate_covariance

    observations = np.array([[1, 2], [2, 0], [3, 4]], dtype=float)
    sample = estimate_covariance(observations, "sample")
    np.testing.assert_allclose(sample.matrix, [[1, 1], [1, 4]])
    assert sample.shrinkage == 0
    shrunk = estimate_covariance(observations, "ledoit_wolf")
    assert 0 < shrunk.shrinkage <= 1
    assert np.linalg.eigvalsh(shrunk.matrix).min() > 0
