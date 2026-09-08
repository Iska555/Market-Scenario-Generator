"""v3 intentionally rejects implicit historical drift and ambiguous v2 fields."""

from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, field_validator, model_validator

from src.data.preparation import DataDiagnostic
from src.risk.contracts import HistogramBin, Percentiles, QuantModel, Statistics, TailRisk

Weight = Annotated[float, Field(ge=0, le=1)]
MAX_SIMULATION_CELLS = 2_000_000


class ScenarioRequest(QuantModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    years: int = Field(3, ge=1, le=10)
    horizon: int = Field(252, ge=1, le=1000)
    num_paths: int = Field(1000, ge=100, le=5000)
    random_seed: int = Field(42, ge=0, le=2**32 - 1)
    drift_model: Literal["zero_log_drift", "historical_diagnostic"]
    risk_free_rate: float = Field(0, gt=-1, le=1)
    periods_per_year: int = Field(252, ge=1, le=366)
    confidence: float = Field(0.95, gt=0, lt=1)
    initial_value: float = Field(1000, gt=0, le=1e12)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")
    covariance_estimator: Literal["ledoit_wolf", "sample"] = "ledoit_wolf"
    gmm_components: int = Field(3, ge=1, le=5)
    gmm_reg_covar: float = Field(1e-6, gt=0, le=0.01)
    ewma_lambda: float = Field(0.94, gt=0, lt=1)
    rebalance: Literal["daily", "buy_and_hold"] = "daily"

    @model_validator(mode="after")
    def bounded_tensor(self) -> Self:
        assets = len(self.tickers) if isinstance(self, PortfolioSimulationRequest) else 1
        if assets * self.horizon * self.num_paths > MAX_SIMULATION_CELLS:
            raise ValueError("Request exceeds 2,000,000 path x horizon x asset cells; reduce size")
        return self


def normalized_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not ticker or len(ticker) > 32 or any(char.isspace() for char in ticker):
        raise ValueError("Ticker must be nonempty, without whitespace, at most 32 characters")
    return ticker


class SimulationRequest(ScenarioRequest):
    ticker: str
    model: Literal["gaussian", "gmm", "ewma"] = "gaussian"

    @field_validator("ticker")
    @classmethod
    def clean_ticker(cls, value: str) -> str:
        return normalized_ticker(value)


class PortfolioSimulationRequest(ScenarioRequest):
    tickers: list[str] = Field(min_length=2, max_length=10)
    weights: list[Weight] | None = None
    model: Literal["gaussian", "gmm"] = "gaussian"

    @field_validator("tickers")
    @classmethod
    def clean_tickers(cls, values: list[str]) -> list[str]:
        tickers = [normalized_ticker(value) for value in values]
        if len(set(tickers)) != len(tickers):
            raise ValueError("Tickers must be unique")
        return tickers

    @model_validator(mode="after")
    def valid_weights(self) -> Self:
        if self.weights is None:
            self.weights = [1 / len(self.tickers)] * len(self.tickers)
        if len(self.weights) != len(self.tickers) or abs(sum(self.weights) - 1) > 1e-10:
            raise ValueError("Weights must match tickers and sum to one")
        return self


class ModelDiagnostics(QuantModel):
    applied_daily_log_means: list[float]
    historical_daily_log_means: list[float]
    log_covariance: list[list[float]]
    covariance_estimator: str
    shrinkage: float | None
    fitted_component_probabilities: list[float] | None = None
    fitted_component_means: list[list[float]] | None = None
    applied_component_means: list[list[float]] | None = None
    component_covariances: list[list[list[float]]] | None = None
    gmm_reg_covar: float | None = None
    ewma_lambda: float | None = None


class ScenarioResponse(QuantModel):
    api_version: Literal["3.0.0"] = "3.0.0"
    model: str
    assumptions: SimulationRequest | PortfolioSimulationRequest
    percentiles: Percentiles
    percentile_values: Percentiles
    statistics: Statistics
    tail_risk: TailRisk
    histogram: list[HistogramBin]
    model_diagnostics: ModelDiagnostics
    data_diagnostics: list[DataDiagnostic]
    excluded_interval_count: int
    estimation_observations: int
    estimation_start: str
    estimation_end: str
    valuation_date: str
    message: str = "Conditional scenarios under stated assumptions; not a forecast."


class SimulationResponse(ScenarioResponse):
    ticker: str
    start_price: float
    paths_chart_sample: list[list[float]]


class AssetStats(QuantModel):
    ticker: str
    start_price: float
    weight: float
    conditional_scenario_return_mean: float
    marginal_risk_contribution: float | None
    component_risk_contribution: float
    risk_contribution_pct: float | None


class RiskDecomposition(QuantModel):
    annualized_volatility: float
    covariance_estimator: str
    shrinkage: float
    annualized_simple_covariance: list[list[float]]
    basis: Literal["historical_simple_returns_at_initial_weights"] = (
        "historical_simple_returns_at_initial_weights"
    )


class PortfolioSimulationResponse(ScenarioResponse):
    tickers: list[str]
    weights: list[float]
    portfolio_paths_chart_sample: list[list[float]]
    correlation_matrix: dict[str, dict[str, float | None]]
    asset_stats: list[AssetStats]
    risk_decomposition: RiskDecomposition
