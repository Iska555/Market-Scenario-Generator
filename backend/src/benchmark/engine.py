"""Pure matched-interval total-return and realized active-risk calculation."""

from datetime import UTC
from decimal import Decimal, localcontext
from itertools import pairwise
from math import fsum, isfinite, sqrt

from src.accounting.precision import accounting_context
from src.attribution.contracts import ContributionReport
from src.benchmark.contracts import BenchmarkEvidence, ComparisonReport, DailyComparison
from src.performance.contracts import PerformanceReport
from src.performance.engine import close
from src.performance.identity import digest
from src.performance.metrics import Metric

STATS = (
    "mean_daily_active_return",
    "annualized_arithmetic_active_return",
    "annualized_tracking_error",
    "information_ratio",
    "beta",
    "correlation",
)
WARNINGS = [
    "Historical benchmark comparison is descriptive evidence, not an expected return or decision.",
    "Portfolio returns include booked net dividends and fees; benchmark gross/net and hedging "
    "conventions can differ. A net index does not necessarily include investor management costs.",
    "UTC calendar-day intervals and 365 observations/year. Supplied weekend levels and quote-age "
    "settings are explicit evidence, not automatic carry-forward or trading-calendar alignment.",
    "Tracking error is realized sample dispersion of arithmetic active returns, not ex-ante "
    "tracking risk or position risk contribution. Square-root annualization assumes stable "
    "variance and no serial correlation; stale/repeated levels can distort it.",
    "Information ratio uses annualized arithmetic mean active return, not a CAGR difference. "
    "Beta/correlation are centered paired sample moments; no alpha or factor inference is claimed.",
    "Benchmark identity, total-return basis, marks and suitability are supplied, not certified. "
    "Selection is for this account/report; no durable portfolio default or provider archive.",
]


def metric(value: float | Decimal | None, count: int, reason: str = "non_finite_result") -> Metric:
    converted = None if value is None else float(value)
    if converted is None or not isfinite(converted):
        return Metric(value=None, reason=reason, observations=count)
    return Metric(value=converted, reason=None, observations=count)


def active_statistics(pairs: list[tuple[float, float]], expected: int) -> dict[str, Metric]:
    """Never publish a whole-window statistic from a silently reduced complete-case sample."""
    n = len(pairs)
    reason = "incomplete_paired_coverage" if n != expected else "insufficient_observations"
    empty = {name: metric(None, n, reason) for name in STATS}
    if n != expected or n < 2:
        return empty
    try:
        p, b = zip(*pairs, strict=True)
        a = [x - y for x, y in pairs]
        mean_p, mean_b, mean_a = (fsum(values) / n for values in (p, b, a))
        vp, vb, va = (
            fsum((x - mean) ** 2 for x in values) / (n - 1)
            for values, mean in ((p, mean_p), (b, mean_b), (a, mean_a))
        )
        covariance = fsum((x - mean_p) * (y - mean_b) for x, y in pairs) / (n - 1)
        sd_a = sqrt(va)
        result = {
            "mean_daily_active_return": metric(mean_a, n),
            "annualized_arithmetic_active_return": metric(mean_a * 365, n),
            "annualized_tracking_error": metric(sd_a * sqrt(365), n),
            "information_ratio": metric(
                mean_a / sd_a * sqrt(365) if sd_a else None, n, "zero_tracking_error"
            ),
            "beta": metric(covariance / vb if vb else None, n, "zero_benchmark_variance"),
            "correlation": metric(
                covariance / sqrt(vp) / sqrt(vb) if vp and vb else None,
                n,
                "zero_portfolio_or_benchmark_variance",
            ),
        }
        return result
    except (OverflowError, ValueError):
        return {name: metric(None, n) for name in STATS}


def build_comparison(
    performance: PerformanceReport,
    benchmark: BenchmarkEvidence,
    contribution: ContributionReport | None = None,
) -> ComparisonReport:
    """Use exactly the portfolio's intervals; independent outputs survive paired gaps."""
    request, identity = performance.manifest.inputs, benchmark.identity
    if identity.currency != performance.base_currency:
        raise ValueError("Benchmark currency must match the account; conversion is not implemented")
    if identity.effective_from > performance.start or identity.effective_to < performance.end:
        raise ValueError("Benchmark version must cover the complete report window")
    if identity.retrieved_at > request.known_at:
        raise ValueError("Benchmark version was not available by the knowledge cutoff")
    dates = {r.date for r in performance.daily}
    if any(row.date not in dates for row in benchmark.levels):
        raise ValueError("Benchmark observations must belong to the exact portfolio window")
    for row in benchmark.levels:
        if row.observed_at > close(row.date) or row.retrieved_at > request.known_at:
            raise ValueError("Benchmark observation exceeds its valuation or knowledge cutoff")
    if contribution is not None and contribution.performance != performance:
        raise ValueError(
            "Contribution and benchmark comparison must share one performance snapshot"
        )
    marks = {r.date: r for r in benchmark.levels}
    levels: list[Decimal | None] = []
    for day in performance.daily:
        mark = marks.get(day.date)
        stale = mark and (day.date - mark.observed_at.astimezone(UTC).date()).days > (
            benchmark.max_level_age_days
        )
        levels.append(None if mark is None or stale else mark.level)
    expected = len(performance.daily) - 1
    daily: list[DailyComparison] = []
    pairs: list[tuple[float, float]] = []
    with localcontext(accounting_context()):
        for index, (opening, closing) in enumerate(pairwise(performance.daily)):
            l0, l1 = levels[index : index + 2]
            reason = (
                "missing_or_stale_benchmark_level"
                if l0 is None or l1 is None
                else ("zero_benchmark_start_level")
            )
            br = metric(
                l1 / l0 - 1 if l0 and l1 is not None else None,
                1 if l0 and l1 is not None else 0,
                reason,
            )
            pr = closing.daily_return
            if opening.units is None or opening.units <= 0:
                pr = metric(None, 0, "portfolio_not_funded_at_interval_start")
            available = pr.value is not None and br.value is not None
            ar = metric(
                pr.value - br.value if available else None,  # type: ignore[operator]
                1 if available else 0,
                pr.reason or br.reason or "incomplete_paired_coverage",
            )
            rr = metric(
                (1 + pr.value) / (1 + br.value) - 1  # type: ignore[operator]
                if available and br.value != -1
                else None,
                1 if available else 0,
                "zero_benchmark_wealth"
                if available
                else (pr.reason or br.reason or "coverage_gap"),
            )
            if available:
                assert pr.value is not None and br.value is not None
                pairs.append((pr.value, br.value))
            daily.append(
                DailyComparison(
                    start=opening.date,
                    end=closing.date,
                    portfolio_return=pr,
                    benchmark_return=br,
                    active_return=ar,
                    relative_return=rr,
                )
            )
        valid = all(level is not None for level in levels)
        recovery = any(
            earlier == 0 and later is not None and later > 0 for earlier, later in pairwise(levels)
        )
        first, last = levels[0], levels[-1]
        br_total = metric(
            last / first - 1 if valid and not recovery and first and last is not None else None,
            sum(row.benchmark_return.value is not None for row in daily),
            "zero_benchmark_start_level"
            if valid and first == 0
            else (
                "benchmark_recovery_after_zero_level"
                if recovery
                else "incomplete_benchmark_coverage"
            ),
        )
    twr = performance.twr.value
    opening_nav = performance.daily[0].nav
    funded_opening = opening_nav is not None and opening_nav > 0
    available = (
        twr is not None and br_total.value is not None and funded_opening and len(pairs) == expected
    )
    comparison_reason = (
        "portfolio_not_funded_at_opening"
        if twr is not None and not funded_opening
        else (performance.twr.reason or br_total.reason or "incomplete_paired_coverage")
    )
    cumulative_active = metric(
        twr - br_total.value if available else None,  # type: ignore[operator]
        len(pairs),
        comparison_reason,
    )
    cumulative_relative = metric(
        (1 + twr) / (1 + br_total.value) - 1  # type: ignore[operator]
        if available and br_total.value != -1
        else None,
        len(pairs),
        "zero_benchmark_wealth" if available else comparison_reason,
    )
    return ComparisonReport(
        performance=performance,
        contribution=contribution,
        benchmark=benchmark,
        benchmark_sha256=digest(benchmark.model_dump(mode="json")),
        include_contribution=contribution is not None,
        expected_intervals=expected,
        paired_intervals=len(pairs),
        benchmark_return=br_total,
        cumulative_active_return=cumulative_active,
        cumulative_relative_return=cumulative_relative,
        statistics=active_statistics(pairs, expected),
        daily=daily,
        warnings=[*WARNINGS]
        + (
            ["Short sample: estimates are unstable and not evidence of persistent skill."]
            if len(pairs) < 365
            else []
        )
        + (
            ["Incomplete paired coverage: whole-window active statistics are withheld."]
            if len(pairs) != expected
            else []
        ),
    )
