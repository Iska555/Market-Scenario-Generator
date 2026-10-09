"""Stable horizon conversions shared by scenario results and explicit views."""

import math

from src.valuation.contracts import ReturnPair


def finite(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("Calculation exceeds finite numerical domain")
    return value


def from_annualized(rate: float, years: float) -> ReturnPair:
    try:
        cumulative = math.expm1(years * math.log1p(rate)) if rate != -1 else -1.0
    except (ValueError, OverflowError) as exc:
        raise ValueError("Return conversion exceeds numerical domain") from exc
    return ReturnPair(
        annualized_return=rate, cumulative_return=finite(cumulative), horizon_years=years
    )


def from_cumulative(rate: float, years: float) -> ReturnPair:
    try:
        annualized = math.expm1(math.log1p(rate) / years) if rate != -1 else -1.0
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Return conversion exceeds numerical domain") from exc
    return ReturnPair(
        annualized_return=finite(annualized), cumulative_return=rate, horizon_years=years
    )
