"""Explicit investor views, CAPM and diagnostic-only historical estimation."""

import math

import numpy as np

from src.valuation.arithmetic import finite, from_annualized, from_cumulative
from src.valuation.contracts import (
    CapmEstimate,
    CapmRequest,
    ExpectedReturnView,
    HistoricalDiagnostic,
    HistoricalRequest,
    Metric,
    Regression,
    ReturnPair,
    Uncertainty,
    UserViewRequest,
)


def user_view(request: UserViewRequest) -> ExpectedReturnView:
    years = request.context.horizon_years
    if request.annualized_return is not None:
        returns = from_annualized(float(request.annualized_return), years)
        if request.cumulative_return is not None:
            returns = ReturnPair(
                annualized_return=float(request.annualized_return),
                cumulative_return=float(request.cumulative_return),
                horizon_years=years,
            )
    else:
        assert request.cumulative_return is not None
        returns = from_cumulative(float(request.cumulative_return), years)
    return ExpectedReturnView(
        model="user_specified",
        context=request.context,
        returns=returns,
        interpretation=(
            "Owner-specified horizon return; annualized equivalent of cumulative "
            "view, not a forecast of realized CAGR."
        ),
        input=request,
        uncertainty=request.uncertainty,
    )


def validate_sample(request: HistoricalRequest | CapmRequest) -> None:
    context, sample = request.context, request.sample
    if context.currency_basis != "local" or context.money_basis != "nominal":
        raise ValueError("Statistical models support local nominal returns only")
    if (
        sample.observations[-1].end > context.valuation_date
        or sample.observations[-1].end > context.as_of.date()
    ):
        raise ValueError("Return sample extends beyond valuation/evidence cutoff")
    if sample.retrieved_at > context.known_at:
        raise ValueError("Sample retrieval follows requested knowledge cutoff")
    if sample.retrieved_at.date() < sample.observations[-1].end:
        raise ValueError("Sample cannot be retrieved before its final return interval")
    if isinstance(request, CapmRequest):
        if context.return_basis != "total":
            raise ValueError("CAPM requires total-return inputs for security and benchmark")
        if any(row.benchmark_return is None for row in sample.observations):
            raise ValueError("CAPM requires aligned benchmark returns for every interval")


def historical(request: HistoricalRequest) -> HistoricalDiagnostic:
    validate_sample(request)
    sample = request.sample
    values = np.array([row.security_return for row in sample.observations], dtype=float)
    n, a = len(values), sample.periods_per_year
    with np.errstate(over="ignore", invalid="ignore"):
        point = finite(float(values.mean()) * a)
        se = (
            Metric(value=finite(float(values.std(ddof=1)) * a / math.sqrt(n)), observation_count=n)
            if n > 1
            else Metric(value=None, reason="insufficient_observations", observation_count=n)
        )
    return HistoricalDiagnostic(
        context=request.context,
        annualized_arithmetic_mean=Metric(value=point, observation_count=n),
        annualized_mean_standard_error=se,
        observation_count=n,
        window_start=sample.observations[0].start,
        window_end=sample.observations[-1].end,
        frequency=sample.frequency,
        periods_per_year=a,
        uncertainty=Uncertainty(
            parameter_uncertainty=(
                "IID sample-mean standard error reported separately; "
                "serial dependence can invalidate it"
            ),
            model_uncertainty="Historical sample mean is not a forward forecast",
        ),
    )


def regress(request: CapmRequest) -> Regression:
    validate_sample(request)
    sample = request.sample
    n = len(sample.observations)

    def missing(reason: str) -> Metric:
        return Metric(value=None, reason=reason, observation_count=n)

    if n < 3:
        absent = missing("insufficient_observations")
        return Regression(
            beta=absent,
            beta_standard_error=absent,
            r_squared=absent,
            intercept_per_period=absent,
            observation_count=n,
        )
    rf = math.expm1(math.log1p(request.risk_free_rate) / sample.periods_per_year)
    x = np.array([row.benchmark_return for row in sample.observations], dtype=float) - rf
    y = np.array([row.security_return for row in sample.observations], dtype=float) - rf
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        xc, yc = x - x.mean(), y - y.mean()
        sxx, syy = finite(float(xc @ xc)), finite(float(yc @ yc))
        if sxx <= np.finfo(float).eps * n * float(np.max(np.abs(x))) ** 2:
            absent = missing("zero_benchmark_variance")
            return Regression(
                beta=absent,
                beta_standard_error=absent,
                r_squared=absent,
                intercept_per_period=absent,
                observation_count=n,
            )
        beta = finite(float(xc @ yc) / sxx)
        residual = yc - beta * xc
        sse = finite(float(residual @ residual))
        se = finite(math.sqrt(sse / (n - 2) / sxx))
        zero_y = syy <= np.finfo(float).eps * n * float(np.max(np.abs(y))) ** 2
        r2 = (
            missing("zero_security_variance")
            if zero_y
            else Metric(value=finite(1 - sse / syy), observation_count=n)
        )
        return Regression(
            beta=Metric(value=beta, observation_count=n),
            beta_standard_error=Metric(value=se, observation_count=n),
            r_squared=r2,
            intercept_per_period=Metric(
                value=finite(float(y.mean() - beta * x.mean())), observation_count=n
            ),
            observation_count=n,
        )


def capm(request: CapmRequest) -> CapmEstimate:
    regression = regress(request)
    reason = regression.beta.reason
    returns = None
    if regression.beta.value is not None:
        annual = finite(
            request.risk_free_rate + regression.beta.value * request.equity_risk_premium
        )
        if annual < -1:
            reason = "capm_return_below_minus_one"
        else:
            returns = from_annualized(annual, request.context.horizon_years)
    return CapmEstimate(
        model="capm",
        context=request.context,
        returns=returns,
        undefined_reason=reason,
        interpretation=(
            "CAPM one-year arithmetic expected simple total return; horizon "
            "wealth assumes repeated IID annual gross means. Not expected realized CAGR."
        ),
        input=request,
        regression=regression,
        uncertainty=Uncertainty(
            parameter_uncertainty=(
                "OLS IID beta standard error only; rf/ERP uncertainty not propagated"
            ),
            model_uncertainty="CAPM restrictions and stable beta are assumptions",
        ),
    )
