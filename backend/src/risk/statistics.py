"""Statistics from the complete simulated population, never chart samples."""

import numpy as np

from src.risk.contracts import HistogramBin, Percentiles, Statistics, TailMetric, TailRisk

QUANTILES = (1, 5, 10, 25, 50, 75, 90, 95, 99)


def scenario_percentiles(values: np.ndarray) -> Percentiles:
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Percentiles require a nonempty finite population")
    values_at_quantiles = np.percentile(values, QUANTILES, method="linear")
    return Percentiles(
        **dict(zip((f"p{q:02d}" for q in QUANTILES), values_at_quantiles, strict=True))
    )


def tail_risk(
    returns: np.ndarray, confidence: float, horizon: int, initial_value: float, currency: str
) -> TailRisk:
    if (
        returns.ndim != 1
        or len(returns) == 0
        or not np.isfinite(returns).all()
        or not 0 < confidence < 1
        or horizon < 1
        or not np.isfinite(initial_value)
        or initial_value <= 0
    ):
        raise ValueError("Invalid tail-risk population or assumptions")
    losses = -returns
    var = float(np.quantile(losses, confidence, method="linear"))
    # Empirical Expected Shortfall includes a fractional boundary atom. Ties do
    # not accidentally expand the tail beyond its declared probability mass.
    descending = np.sort(losses)[::-1]
    mass = (1 - confidence) * len(losses)
    whole = int(np.floor(mass))
    fraction = mass - whole
    boundary = fraction * descending[whole] if whole < len(descending) else 0.0
    cvar = float((descending[:whole].sum() + boundary) / mass)

    def metric(value: float) -> TailMetric:
        return TailMetric(
            confidence=confidence,
            horizon_days=horizon,
            value_pct=value,
            value_currency=value * initial_value,
            currency=currency,
        )

    return TailRisk(var=metric(var), cvar=metric(cvar))


def return_statistics(daily_returns: np.ndarray, risk_free_rate: float, periods: int) -> Statistics:
    """Pooled daily ratios; medians of individually annualized path growth/Calmar."""
    r = np.asarray(daily_returns, dtype=float)
    if (
        r.ndim != 2
        or min(r.shape) < 1
        or not np.isfinite(r).all()
        or (r <= -1).any()
        or not np.isfinite(risk_free_rate)
        or risk_free_rate <= -1
        or periods < 1
    ):
        raise ValueError("Finite simple returns above -100% and valid assumptions required")
    with np.errstate(over="raise", invalid="raise"):
        paths = np.concatenate([np.ones((len(r), 1)), np.cumprod(1 + r, axis=1)], axis=1)
        terminal = paths[:, -1] - 1
        annualized = np.expm1(np.log1p(r).sum(axis=1) * periods / r.shape[1])
    peaks = np.maximum.accumulate(paths, axis=1)
    max_dd = np.max(1 - paths / peaks, axis=1)
    rf_daily = np.expm1(np.log1p(risk_free_rate) / periods)
    excess = r - rf_daily
    numerator = float(excess.mean() * periods)
    vol = float(r.std(ddof=1) * np.sqrt(periods)) if r.size > 1 else None
    downside = float(np.sqrt(np.square(np.minimum(excess, 0)).mean() * periods))
    # Ratios with no meaningful denominator are undefined, not zero.
    sharpe = numerator / vol if vol is not None and vol > 1e-14 else None
    sortino = numerator / downside if downside > 1e-14 else None
    calmar = annualized[max_dd > 1e-14] / max_dd[max_dd > 1e-14]
    return Statistics(
        conditional_scenario_return_mean=float(terminal.mean()),
        annualized_return_median=float(np.median(annualized)),
        annualized_volatility=vol,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio_median=float(np.median(calmar)) if calmar.size == len(r) else None,
        calmar_defined_paths=int(calmar.size),
        calmar_total_paths=len(r),
        max_drawdown_median=float(np.median(max_dd)),
        max_drawdown_p95=float(np.percentile(max_dd, 95)),
        prob_loss=float((terminal < 0).mean()),
        min_return=float(terminal.min()),
        max_return=float(terminal.max()),
    )


def return_histogram(returns: np.ndarray, bins: int = 30) -> list[HistogramBin]:
    if returns.ndim != 1 or not len(returns) or not np.isfinite(returns).all():
        raise ValueError("Histogram requires a nonempty finite population")
    counts, edges = np.histogram(returns, bins=bins)
    return [
        HistogramBin(lower=float(edges[i]), upper=float(edges[i + 1]), count=int(count))
        for i, count in enumerate(counts)
    ]
