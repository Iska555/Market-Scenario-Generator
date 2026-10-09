"""Explicit supplied-data scenario assumptions; no automatic provider or investor view."""

import math
from datetime import date
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from src.portfolio.construction.contracts import JointHistory, Weight
from src.research.schemas import Currency
from src.risk.contracts import Percentiles
from src.valuation.contracts import Contract, Finite, Growth, Metric, Positive, Rate, Text

Count = Annotated[int, Field(ge=1, le=10000, strict=True)]
Method = Literal["historical_replay", "block_bootstrap", "deterministic_shock"]


class StressAsset(Contract):
    security_id: UUID
    weight: Weight


class StressRequest(Contract):
    method: Method
    scenario_name: Text
    rationale: Text
    assets: Annotated[list[StressAsset], Field(min_length=1, max_length=30)]
    currency: Currency
    valuation_date: date
    valuation_calendar: Text
    as_of: AwareDatetime
    known_at: AwareDatetime
    initial_value: Positive
    return_basis: Literal["nominal_total_simple_return"] = "nominal_total_simple_return"
    history: JointHistory | None = None
    rebalance: Literal["per_observation", "buy_and_hold"] | None = None
    risk_free_rate: Growth | None = None
    risk_free_convention: Literal["annual_effective"] = "annual_effective"
    horizon_periods: Count | None = None
    path_count: Count | None = None
    block_length: Count | None = None
    seed: Annotated[int, Field(ge=0, le=2**32 - 1, strict=True)] | None = None
    confidence: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)] | None = None
    mean_policy: Literal["resample_observed_returns_not_expected_return"] | None = None
    shocks: Annotated[list[Rate], Field(min_length=1, max_length=30)] | None = None
    shock_horizon_label: Text | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        ids = [a.security_id for a in self.assets]
        if len(set(ids)) != len(ids):
            raise ValueError("Security IDs must be unique")
        if not math.isclose(sum(a.weight for a in self.assets), 1, rel_tol=0, abs_tol=1e-10):
            raise ValueError("Declared long-only weights must sum to one")
        if self.as_of.date() > self.valuation_date:
            raise ValueError("Publication cutoff cannot follow valuation date")
        bootstrap = (
            self.horizon_periods,
            self.path_count,
            self.block_length,
            self.seed,
            self.confidence,
            self.mean_policy,
        )
        if self.method != "block_bootstrap" and any(v is not None for v in bootstrap):
            raise ValueError("Bootstrap assumptions are valid only for block bootstrap")
        if self.method == "deterministic_shock":
            if (
                self.history is not None
                or self.rebalance is not None
                or self.risk_free_rate is not None
            ):
                raise ValueError(
                    "One-shot shocks do not accept history or rebalancing/ratio assumptions"
                )
            if self.shocks is None or len(self.shocks) != len(ids) or not self.shock_horizon_label:
                raise ValueError("Explicit ordered security shocks and horizon label required")
            return self
        if self.shocks is not None or self.shock_horizon_label is not None:
            raise ValueError("Security shocks only apply to deterministic shock")
        if self.history is None or self.rebalance is None or self.risk_free_rate is None:
            raise ValueError("History, rebalancing and explicit risk-free rate required")
        if self.history.security_ids != ids:
            raise ValueError("History and assets must use identical ordered security IDs")
        if self.history.observations[-1].end > self.as_of.date():
            raise ValueError("Historical intervals cannot follow publication cutoff")
        if self.history.retrieved_at > self.known_at:
            raise ValueError("Historical sample unavailable under knowledge cutoff")
        if any(r <= -1 for row in self.history.observations for r in row.returns):
            raise ValueError(
                "Replay path domain excludes complete-loss observations; none are deleted"
            )
        if self.method == "block_bootstrap":
            if any(v is None for v in bootstrap):
                raise ValueError(
                    "Bootstrap requires horizon, paths, block length, seed, "
                    "confidence and mean policy"
                )
            assert self.block_length is not None and self.path_count is not None
            assert self.horizon_periods is not None
            if self.block_length > len(self.history.observations):
                raise ValueError("Block length cannot exceed complete history length")
            if self.path_count * self.horizon_periods * len(ids) > 2_000_000:
                raise ValueError("Scenario tensor exceeds two million cells")
        return self


class StressResult(Contract):
    kind: Literal["conditional_stress_scenario"] = "conditional_stress_scenario"
    method: Method
    scenario_name: str
    currency: Currency
    horizon_periods: int
    horizon_label: str
    population_size: int
    scenario_mean_terminal_return: Finite
    scenario_mean_terminal_value: Finite
    scenario_max_drawdown_median: Finite
    scenario_max_drawdown_p95: Finite
    scenario_annualized_volatility: Metric
    scenario_sharpe_ratio: Metric
    scenario_sortino_ratio: Metric
    scenario_calmar_ratio_median: Metric
    calmar_defined_paths: int
    calmar_total_paths: int
    scenario_var: Metric
    scenario_expected_shortfall: Metric
    tail_confidence: float | None
    tail_effective_count: Finite | None
    loss_convention: Literal["loss_positive"] = "loss_positive"
    terminal_return_percentiles: Percentiles | None
    portfolio_paths_chart_sample: list[list[Finite]]
    chart_sample_policy: str = (
        "First at most 30 full paths including time zero; never used for statistics"
    )
    methodology: list[str]
    interpretation: str = (
        "Conditional stress evidence, not a forecast, investor "
        "expected-return view or realized performance"
    )
    uncertainty: str = (
        "Parameter/model uncertainty is not propagated; resampling "
        "uncertainty is conditional on the supplied empirical history"
    )
