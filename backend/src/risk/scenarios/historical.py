"""Joint moving-block bootstrap, complete historical replay and explicit security shocks."""

from typing import Literal

import numpy as np

from src.portfolio.paths import build_portfolio_paths
from src.risk.scenarios.historical_contracts import StressRequest, StressResult
from src.risk.statistics import return_statistics, scenario_percentiles, tail_risk
from src.valuation.contracts import Metric


def joint_blocks(
    rows: np.ndarray, horizon: int, paths: int, block_length: int, seed: int
) -> np.ndarray:
    """Uniform overlapping non-circular blocks; last sampled block is truncated."""
    if (
        rows.ndim != 2
        or min(rows.shape) < 1
        or not np.isfinite(rows).all()
        or min(horizon, paths, block_length) < 1
        or block_length > len(rows)
        or horizon * paths * rows.shape[1] > 2_000_000
    ):
        raise ValueError("Invalid bounded joint block dimensions")
    rng = np.random.default_rng(seed)
    blocks = (horizon + block_length - 1) // block_length
    starts = rng.integers(0, len(rows) - block_length + 1, size=(paths, blocks))
    # Allocate only the requested horizon, including when block length exceeds horizon.
    periods = np.arange(horizon)
    indices = starts[:, periods // block_length] + periods % block_length
    return np.asarray(rows[indices], dtype=float)


def metric(value: float | None, reason: str) -> Metric:
    return Metric(value=value, reason=reason if value is None else None)


def evaluate_scenario(request: StressRequest) -> StressResult:
    weights = np.array([a.weight for a in request.assets])
    # Contract already rejects deviations greater than 1e-10. Reconcile that
    # declared roundoff only so fully invested complete losses cannot turn negative.
    weights = weights / weights.sum()
    undefined = metric(None, "One scenario has no empirical tail distribution")
    ratios_undefined = metric(None, "One-shot shock has no periodic return series or annualization")
    methodology = [
        "Owner-declared fully invested long-only initial weights; one currency; no FX conversion.",
        "Weight-sum deviations within the accepted 1e-10 tolerance are reconciled to exactly one.",
        "Nominal total simple returns; no fees, taxes, transaction costs or investment decisions.",
        "All statistics use the complete population, independent of the chart sample.",
    ]
    if request.method == "deterministic_shock":
        assert request.shocks is not None
        # Nonnegative gross wealth avoids cancellation below zero at complete loss.
        terminal_gross = float(weights @ (1 + np.array(request.shocks)))
        terminal_return = terminal_gross - 1
        terminal_value = request.initial_value * terminal_gross
        methodology.append(
            "Portfolio shock equals sum(weight * explicit security simple "
            "return); no guessed macro mapping."
        )
        return StressResult(
            method=request.method,
            scenario_name=request.scenario_name,
            currency=request.currency,
            horizon_periods=1,
            horizon_label=request.shock_horizon_label or "",
            population_size=1,
            scenario_mean_terminal_return=terminal_return,
            scenario_mean_terminal_value=terminal_value,
            scenario_max_drawdown_median=max(0, -terminal_return),
            scenario_max_drawdown_p95=max(0, -terminal_return),
            scenario_annualized_volatility=ratios_undefined,
            scenario_sharpe_ratio=ratios_undefined,
            scenario_sortino_ratio=ratios_undefined,
            scenario_calmar_ratio_median=ratios_undefined,
            calmar_defined_paths=0,
            calmar_total_paths=1,
            scenario_var=undefined,
            scenario_expected_shortfall=undefined,
            tail_confidence=None,
            tail_effective_count=None,
            terminal_return_percentiles=None,
            portfolio_paths_chart_sample=[[1, terminal_gross]],
            methodology=methodology,
        )
    history = request.history
    assert history is not None and request.risk_free_rate is not None
    rows = np.array([row.returns for row in history.observations])
    if request.method == "historical_replay":
        draws = rows[None, :, :]
        methodology.append(
            "Complete ordered historical joint sequence applied to declared current weights."
        )
    else:
        assert request.horizon_periods is not None and request.path_count is not None
        assert request.block_length is not None and request.seed is not None
        draws = joint_blocks(
            rows, request.horizon_periods, request.path_count, request.block_length, request.seed
        )
        methodology.extend(
            [
                "Uniform overlapping non-circular joint moving blocks; final "
                "block truncated to horizon.",
                "Observed empirical returns are resampled unchanged, preserving "
                "joint rows and within-block order.",
                "No recentering: block endpoint weights and random sampling can change "
                "the sample mean; it is not adopted as expected return.",
            ]
        )
    mode: Literal["daily", "buy_and_hold"] = (
        "daily" if request.rebalance == "per_observation" else "buy_and_hold"
    )
    _, portfolio = build_portfolio_paths(np.ones(len(weights)), np.log1p(draws), weights, mode)
    returns = portfolio[:, 1:] / portfolio[:, :-1] - 1
    stats = return_statistics(returns, request.risk_free_rate, history.periods_per_year)
    terminal = portfolio[:, -1] - 1
    var, es, percentiles = undefined, undefined, None
    if request.method == "block_bootstrap":
        assert request.confidence is not None
        tails = tail_risk(
            terminal, request.confidence, draws.shape[1], request.initial_value, request.currency
        )
        # Expose supplied periods rather than the legacy helper's 'days' label.
        var = metric(tails.var.value_pct, "")
        es = metric(tails.cvar.value_pct, "")
        percentiles = scenario_percentiles(terminal)
    methodology.extend(
        [
            f"Rebalancing: {request.rebalance}; observation frequency: {history.frequency}.",
            f"Annualization: {history.periods_per_year} periods/year; IID "
            "pooled period volatility/excess-return ratios.",
            "Sharpe/Sortino use annual-effective risk-free rate; Calmar is "
            "median path annual growth/max drawdown, undefined if any path has zero drawdown.",
            "Tail losses are terminal simple-return losses; linear empirical "
            "VaR and fractional-boundary expected shortfall; losses may be negative.",
        ]
    )
    with np.errstate(over="raise", invalid="raise"):
        value = float((portfolio[:, -1] * request.initial_value).mean())
    return StressResult(
        method=request.method,
        scenario_name=request.scenario_name,
        currency=request.currency,
        horizon_periods=draws.shape[1],
        horizon_label=f"{draws.shape[1]} {history.frequency} observations",
        population_size=len(portfolio),
        scenario_mean_terminal_return=float(terminal.mean()),
        scenario_mean_terminal_value=value,
        scenario_max_drawdown_median=stats.max_drawdown_median,
        scenario_max_drawdown_p95=stats.max_drawdown_p95,
        scenario_annualized_volatility=metric(
            stats.annualized_volatility, "Insufficient period observations"
        ),
        scenario_sharpe_ratio=metric(stats.sharpe_ratio, "Zero or undefined period volatility"),
        scenario_sortino_ratio=metric(stats.sortino_ratio, "Zero downside deviation"),
        scenario_calmar_ratio_median=metric(
            stats.calmar_ratio_median, "At least one path has zero drawdown"
        ),
        calmar_defined_paths=stats.calmar_defined_paths,
        calmar_total_paths=stats.calmar_total_paths,
        scenario_var=var,
        scenario_expected_shortfall=es,
        tail_confidence=request.confidence,
        tail_effective_count=(1 - request.confidence) * len(portfolio)
        if request.confidence is not None
        else None,
        terminal_return_percentiles=percentiles,
        portfolio_paths_chart_sample=portfolio[:30].tolist(),
        methodology=methodology,
    )
