"""Orchestrate calibrated models, full-population statistics and typed results."""

import numpy as np

from src.api.models import (
    AssetStats,
    ModelDiagnostics,
    PortfolioSimulationRequest,
    PortfolioSimulationResponse,
    RiskDecomposition,
    ScenarioResponse,
    SimulationRequest,
    SimulationResponse,
)
from src.data.preparation import PreparedPrices, prepare_prices
from src.data.providers import PriceDataProvider
from src.ewma_vol import compute_ewma_vol, forecast_ewma_vol, sample_ewma_returns
from src.gmm_model import fit_gmm, sample_gmm
from src.portfolio.paths import build_portfolio_paths
from src.risk.covariance import estimate_covariance, psd_factor, risk_contributions
from src.risk.statistics import (
    return_histogram,
    return_statistics,
    scenario_percentiles,
    tail_risk,
)

Request = SimulationRequest | PortfolioSimulationRequest


def draw_returns(request: Request, data: PreparedPrices) -> tuple[np.ndarray, ModelDiagnostics]:
    rng = np.random.default_rng(request.random_seed)
    history = data.returns.to_numpy()
    historical_mean = history.mean(axis=0)
    mean = (
        historical_mean
        if request.drift_model == "historical_diagnostic"
        else np.zeros_like(historical_mean)
    )
    if request.model == "gmm":
        model = fit_gmm(
            data.returns, request.gmm_components, rng=rng, reg_covar=request.gmm_reg_covar
        )
        fitted_mean = model.weights_ @ model.means_
        # A declared change of the fitted distribution's location, before drawing.
        # Preserve all relative regime means; never demean the realized sample.
        applied = model.means_.copy()
        if request.drift_model == "zero_log_drift":
            applied = applied - fitted_mean
        else:
            mean = fitted_mean
        offsets = applied - mean
        covariance = np.einsum("k,kij->ij", model.weights_, model.covariances_) + np.einsum(
            "k,ki,kj->ij", model.weights_, offsets, offsets
        )
        diagnostics = ModelDiagnostics(
            applied_daily_log_means=mean.tolist(),
            historical_daily_log_means=historical_mean.tolist(),
            log_covariance=covariance.tolist(),
            covariance_estimator="gmm_full",
            shrinkage=None,
            fitted_component_probabilities=model.weights_.tolist(),
            fitted_component_means=model.means_.tolist(),
            applied_component_means=applied.tolist(),
            component_covariances=model.covariances_.tolist(),
            gmm_reg_covar=request.gmm_reg_covar,
        )
        return sample_gmm(
            model, request.horizon, request.num_paths, rng=rng, applied_means=applied
        ), diagnostics
    if request.model == "ewma":
        vol = float(compute_ewma_vol(data.returns.iloc[:, 0], request.ewma_lambda).iloc[-1])
        forecast = forecast_ewma_vol(vol, request.ewma_lambda, request.horizon)
        draws = sample_ewma_returns(float(mean[0]), forecast, request.num_paths, rng=rng)
        return draws[:, :, None], ModelDiagnostics(
            applied_daily_log_means=mean.tolist(),
            historical_daily_log_means=historical_mean.tolist(),
            log_covariance=[[vol**2]],
            covariance_estimator="ewma_second_moment",
            shrinkage=None,
            ewma_lambda=request.ewma_lambda,
        )
    covariance_fit = estimate_covariance(history, request.covariance_estimator)
    shocks = rng.standard_normal((request.num_paths, request.horizon, history.shape[1]))
    draws = mean + shocks @ psd_factor(covariance_fit.matrix).T
    return draws, ModelDiagnostics(
        applied_daily_log_means=mean.tolist(),
        historical_daily_log_means=historical_mean.tolist(),
        log_covariance=covariance_fit.matrix.tolist(),
        covariance_estimator=request.covariance_estimator,
        shrinkage=covariance_fit.shrinkage,
    )


def summarize(
    request: Request, data: PreparedPrices, paths: np.ndarray, diagnostics: ModelDiagnostics
) -> ScenarioResponse:
    final = paths[:, -1] - 1
    daily = paths[:, 1:] / paths[:, :-1] - 1
    return ScenarioResponse(
        model=request.model,
        assumptions=request,
        percentiles=scenario_percentiles(final),
        percentile_values=scenario_percentiles(paths[:, -1] * request.initial_value),
        statistics=return_statistics(daily, request.risk_free_rate, request.periods_per_year),
        tail_risk=tail_risk(
            final, request.confidence, request.horizon, request.initial_value, request.currency
        ),
        histogram=return_histogram(final),
        model_diagnostics=diagnostics,
        data_diagnostics=data.diagnostics,
        excluded_interval_count=data.excluded_interval_count,
        estimation_observations=len(data.returns),
        estimation_start=str(data.returns.index[0]),
        estimation_end=str(data.returns.index[-1]),
        valuation_date=data.valuation_date,
    )


def run_single(
    request: SimulationRequest, provider: PriceDataProvider, chart_sample_size: int = 30
) -> SimulationResponse:
    data = prepare_prices({request.ticker: provider(request.ticker, request.years)})
    draws, diagnostics = draw_returns(request, data)
    assets, portfolio = build_portfolio_paths(data.start_prices, draws)
    summary = summarize(request, data, portfolio, diagnostics)
    return SimulationResponse(
        **summary.model_dump(),
        ticker=request.ticker,
        start_price=float(data.start_prices[0]),
        paths_chart_sample=assets[:chart_sample_size, :, 0].tolist(),
    )


def run_portfolio(
    request: PortfolioSimulationRequest, provider: PriceDataProvider, chart_sample_size: int = 30
) -> PortfolioSimulationResponse:
    data = prepare_prices({ticker: provider(ticker, request.years) for ticker in request.tickers})
    draws, diagnostics = draw_returns(request, data)
    weights = np.asarray(request.weights)
    assets, portfolio = build_portfolio_paths(data.start_prices, draws, weights, request.rebalance)
    summary = summarize(request, data, portfolio, diagnostics)
    # A separate ex-ante decomposition at initial weights, using historical SIMPLE
    # returns. It is not the pooled simulated volatility, especially for buy/hold.
    fitted = estimate_covariance(np.expm1(data.returns.to_numpy()), request.covariance_estimator)
    covariance = fitted.matrix * request.periods_per_year
    contributions = risk_contributions(covariance, weights)
    asset_means = (assets[:, -1, :] / data.start_prices - 1).mean(axis=0)
    asset_stats = [
        AssetStats(
            ticker=ticker,
            start_price=float(data.start_prices[i]),
            weight=float(weights[i]),
            conditional_scenario_return_mean=float(asset_means[i]),
            marginal_risk_contribution=(
                float(contributions.marginal[i]) if contributions.marginal is not None else None
            ),
            component_risk_contribution=float(contributions.component[i]),
            risk_contribution_pct=(
                float(contributions.percentage[i]) if contributions.percentage is not None else None
            ),
        )
        for i, ticker in enumerate(request.tickers)
    ]
    scale = np.sqrt(np.diag(fitted.matrix))
    correlations = {
        ticker: {
            other: (
                float(fitted.matrix[i, j] / (scale[i] * scale[j]))
                if scale[i] * scale[j] > 0
                else None
            )
            for j, other in enumerate(request.tickers)
        }
        for i, ticker in enumerate(request.tickers)
    }
    return PortfolioSimulationResponse(
        **summary.model_dump(),
        tickers=request.tickers,
        weights=weights.tolist(),
        portfolio_paths_chart_sample=(
            portfolio[:chart_sample_size] * request.initial_value
        ).tolist(),
        asset_stats=asset_stats,
        correlation_matrix=correlations,
        risk_decomposition=RiskDecomposition(
            annualized_volatility=contributions.volatility,
            covariance_estimator=request.covariance_estimator,
            shrinkage=fitted.shrinkage,
            annualized_simple_covariance=covariance.tolist(),
        ),
    )
