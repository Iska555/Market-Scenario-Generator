"""Pure realized daily statistics and conservatively identified dated XIRR."""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, DecimalException, localcontext
from itertools import pairwise
from math import exp, expm1, fsum, isfinite, log, log1p, sqrt
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.accounting.precision import accounting_context

PERIODS_PER_YEAR = 365
XIRR_LOG_RATE_BOUND = 32.0
METRICS = (
    "annualized_return",
    "annualized_volatility",
    "sharpe",
    "sortino",
    "calmar",
    "max_drawdown",
    "longest_drawdown_days",
    "recovery_days",
    "best_month",
    "worst_month",
    "hit_rate",
    "skewness",
    "excess_kurtosis",
    "realized_var",
    "realized_cvar",
    "effective_tail_observations",
)


class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True, strict=True)
    value: float | None
    reason: str | None
    observations: int = Field(ge=0)

    @model_validator(mode="after")
    def defined_or_reason(self) -> Self:
        if (self.value is None and not self.reason) or (
            self.value is not None and self.reason is not None
        ):
            raise ValueError("An undefined metric needs a reason; a defined metric cannot have one")
        return self


def _metric(value: float, count: int) -> Metric:
    if not isfinite(value):
        return _undefined("non_finite_result", count)
    return Metric(value=value, reason=None, observations=count)


def _undefined(reason: str, count: int) -> Metric:
    return Metric(value=None, reason=reason, observations=count)


def xirr(flows: list[tuple[date, Decimal]]) -> Metric:
    """Actual-day/365 IRR; aggregate dates and accept only one sign change.

    Solve equality of positive and negative discounted log sums. The finite
    log(1+r) interval [-32,32] avoids rates rounding to -100% and overflow.
    """
    amounts: dict[date, Decimal] = {}
    try:
        with localcontext(accounting_context()):
            for day, amount in flows:
                if (
                    type(day) is not date
                    or not isinstance(amount, Decimal)
                    or not amount.is_finite()
                ):
                    raise ValueError("Cash flows require dates and finite Decimal amounts")
                amounts[day] = amounts.get(day, Decimal(0)) + amount
            schedule = sorted((day, value) for day, value in amounts.items() if value)
            n = len(schedule)
            if not n:
                return _undefined("no_nonzero_cash_flows", 0)
            signs = [value > 0 for _, value in schedule]
            if all(signs) or not any(signs):
                return _undefined("cash_flows_need_both_signs", n)
            if sum(a != b for a, b in pairwise(signs)) != 1:
                return _undefined("non_conventional_cash_flows", n)
            start = schedule[0][0]
            terms = [
                (float(abs(value).ln()), (day - start).days / 365, value > 0)
                for day, value in schedule
            ]
    except DecimalException as exc:
        raise ValueError("Cash flows exceed supported decimal arithmetic") from exc

    def balance(rate: float) -> float:
        sides: list[float] = []
        for sign in (True, False):
            values = [
                amount - rate * years for amount, years, positive in terms if positive == sign
            ]
            largest = max(values)
            sides.append(largest + log(fsum(exp(value - largest) for value in values)))
        return sides[0] - sides[1]

    low, high = -XIRR_LOG_RATE_BOUND, XIRR_LOG_RATE_BOUND
    left, right = balance(low), balance(high)
    if left == 0:
        return _metric(expm1(low), n)
    if right == 0:
        return _metric(expm1(high), n)
    if (left > 0) == (right > 0):
        return _undefined("root_outside_supported_bounds", n)
    for _ in range(120):
        middle = (low + high) / 2
        result = balance(middle)
        if result == 0 or middle == low or middle == high:
            return _metric(expm1(middle), n)
        if (result > 0) == (left > 0):
            low, left = middle, result
        else:
            high = middle
    return _metric(expm1((low + high) / 2), n)


def _geometric(values: list[float], exponent: float = 1) -> float:
    if -1 in values:
        return -1.0
    try:
        return expm1(fsum(log1p(value) for value in values) * exponent)
    except OverflowError:
        return float("inf")


def _drawdowns(values: list[float]) -> tuple[float, int, int | None]:
    log_wealth = peak = 0.0
    peak_day = longest = recovery = 0
    deepest = 0.0
    unrecovered = False
    for day, value in enumerate(values, start=1):
        log_wealth = float("-inf") if value == -1 else log_wealth + log1p(value)
        if log_wealth >= peak:
            if unrecovered:
                recovery = max(recovery, day - peak_day)
                longest = max(longest, day - peak_day)
            peak, peak_day, unrecovered = log_wealth, day, False
        else:
            deepest = max(deepest, -expm1(log_wealth - peak))
            longest = max(longest, day - peak_day)
            unrecovered = True
    return deepest, longest, None if unrecovered else recovery


def realized_statistics(
    dates: list[date],
    returns: list[float],
    risk_free_rate: float = 0,
    confidence: float = 0.95,
) -> dict[str, Metric]:
    """Statistics of consecutive UTC calendar daily net simple returns.

    VaR/CVaR and drawdown are loss-positive. Empirical tails may legitimately
    be negative. Missing observations cannot be skipped or linked across.
    """
    if len(dates) != len(returns) or any(type(day) is not date for day in dates):
        raise ValueError("Return dates and values must match")
    if any(b - a != timedelta(days=1) for a, b in pairwise(dates)):
        raise ValueError("Return end dates must be consecutive calendar days")
    if any(
        isinstance(r, bool) or not isinstance(r, (float, int)) or not isfinite(r) or r < -1
        for r in returns
    ):
        raise ValueError("Returns must be finite simple returns greater than or equal to -1")
    if isinstance(risk_free_rate, bool) or not isfinite(risk_free_rate) or risk_free_rate <= -1:
        raise ValueError("Risk-free rate must be finite and greater than -1")
    if isinstance(confidence, bool) or not isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Confidence must be strictly between zero and one")
    n = len(returns)
    if not n:
        return {key: _undefined("no_observations", 0) for key in METRICS}
    daily_rf = expm1(log1p(risk_free_rate) / 365)
    scale = max(abs(value) for value in returns)
    mean = fsum(value / scale for value in returns) / n * scale if scale else 0.0
    deviations = [value - mean for value in returns]
    deviation_scale = max(abs(value) for value in deviations)
    normalized = [value / deviation_scale for value in deviations] if deviation_scale else [0.0] * n
    m2 = fsum(value * value for value in normalized) / n
    sd = deviation_scale * sqrt(m2 * n / (n - 1)) if n > 1 else 0.0
    excess_mean = mean - daily_rf
    downside = [min(value - daily_rf, 0) for value in returns]
    downside_scale = max(abs(value) for value in downside)
    downside_rms = (
        (downside_scale * sqrt(fsum((value / downside_scale) ** 2 for value in downside) / n))
        if downside_scale
        else 0.0
    )
    drawdown, longest, recovery = _drawdowns(returns)
    annual = (
        _metric(_geometric(returns, 365 / n), n)
        if n >= 365
        else _undefined("window_shorter_than_one_year", n)
    )
    result = {
        "annualized_return": annual,
        "annualized_volatility": (
            _metric(sd * sqrt(365), n) if n > 1 else _undefined("insufficient_observations", n)
        ),
        "sharpe": (
            _metric(excess_mean / sd * sqrt(365), n)
            if sd
            else _undefined("zero_volatility" if n > 1 else "insufficient_observations", n)
        ),
        "sortino": (
            _metric(excess_mean / downside_rms * sqrt(365), n)
            if downside_rms
            else _undefined("zero_downside_deviation", n)
        ),
        "calmar": (
            _metric(annual.value / drawdown, n)
            if annual.value is not None and drawdown
            else _undefined(annual.reason or "zero_drawdown", n)
        ),
        "max_drawdown": _metric(drawdown, n),
        "longest_drawdown_days": _metric(longest, n),
        "recovery_days": (
            _metric(recovery, n) if recovery is not None else _undefined("unrecovered_drawdown", n)
        ),
        "hit_rate": _metric(sum(value > 0 for value in returns) / n, n),
    }
    months: dict[tuple[int, int], list[tuple[date, float]]] = {}
    for day, value in zip(dates, returns, strict=True):
        months.setdefault((day.year, day.month), []).append((day, value))
    complete = [
        _geometric([value for _, value in group])
        for (year, month), group in months.items()
        if group[0][0].day == 1 and group[-1][0].day == monthrange(year, month)[1]
    ]
    for name, choose in [("best_month", max), ("worst_month", min)]:
        result[name] = (
            _metric(choose(complete), len(complete))
            if complete
            else _undefined("no_complete_calendar_months", 0)
        )
    for name, minimum in [("skewness", 3), ("excess_kurtosis", 4)]:
        if n < minimum or not deviation_scale:
            result[name] = _undefined(
                "insufficient_observations" if n < minimum else "zero_volatility", n
            )
        elif name == "skewness":
            m3 = fsum(value**3 for value in normalized) / n
            result[name] = _metric(sqrt(n * (n - 1)) / (n - 2) * m3 / m2**1.5, n)
        else:
            m4 = fsum(value**4 for value in normalized) / n
            result[name] = _metric(
                (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * m4 / m2**2 - 3 * (n - 1)), n
            )
    losses = sorted(-value for value in returns)
    position = (n - 1) * confidence
    index = int(position)
    fraction = position - index
    quantile = losses[index] * (1 - fraction) + losses[min(index + 1, n - 1)] * fraction
    tail_mass = (1 - confidence) * n
    whole = int(tail_mass)
    descending = losses[::-1]
    # Divide each atom before summing to avoid overflowing an intermediate sum.
    tail = fsum(value / tail_mass for value in descending[:whole])
    if whole < n:
        tail += descending[whole] * ((tail_mass - whole) / tail_mass)
    result["realized_var"] = _metric(quantile, n)
    result["realized_cvar"] = _metric(tail, n)
    result["effective_tail_observations"] = _metric(tail_mass, n)
    return result
