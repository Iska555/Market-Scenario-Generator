"""Typed quantitative results shared by services and the API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class QuantModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class Percentiles(QuantModel):
    p01: float
    p05: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float


class Statistics(QuantModel):
    conditional_scenario_return_mean: float
    annualized_return_median: float
    annualized_volatility: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    calmar_ratio_median: float | None
    calmar_defined_paths: int
    calmar_total_paths: int
    max_drawdown_median: float
    max_drawdown_p95: float
    prob_loss: float
    min_return: float
    max_return: float


class TailMetric(QuantModel):
    confidence: float
    horizon_days: int
    value_pct: float
    value_currency: float
    currency: str
    convention: Literal["loss_positive"] = "loss_positive"


class TailRisk(QuantModel):
    var: TailMetric
    cvar: TailMetric


class HistogramBin(QuantModel):
    lower: float
    upper: float
    count: int
