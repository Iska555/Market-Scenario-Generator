"""Unitized daily performance from immutable ledger rows and supplied marks."""

import calendar
import os
import platform
from datetime import UTC, date, datetime, time
from decimal import Decimal, localcontext
from importlib.metadata import version
from uuid import UUID

from src.accounting.contracts import FX, LedgerState, Price, TransactionRead, ValuationRequest
from src.accounting.ledger import replay
from src.accounting.precision import accounting_context
from src.accounting.valuation import value_state
from src.performance.contracts import (
    DailyResult,
    ExternalFlow,
    LinkedPeriod,
    Marks,
    PerformanceManifest,
    PerformanceReport,
    PerformanceRequest,
)
from src.performance.identity import digest, source_sha256
from src.performance.metrics import Metric, realized_statistics, xirr


def metric(value: Decimal | float | None, reason: str | None, count: int) -> Metric:
    return Metric(
        value=float(value) if value is not None else None, reason=reason, observations=count
    )


def close(day: date) -> datetime:
    return datetime.combine(day, time.max, UTC)


def _marked_value(
    state: LedgerState,
    marks: Marks,
    request: PerformanceRequest,
    flow_currency: str | None = None,
) -> tuple[Decimal | None, str | None]:
    prices, rates = marks.prices, marks.fx
    if len({p.security_id for p in prices}) != len(prices) or len(
        {f.currency for f in rates}
    ) != len(rates):
        raise ValueError("Duplicate price or FX evidence is ambiguous")
    currencies = {p.currency for p in state.positions} | {c.currency for c in state.cash}
    if set(f.currency for f in rates) - currencies - {state.base_currency, flow_currency}:
        raise ValueError("FX supplied for an unused currency")
    all_marks: list[Price | FX] = [*prices, *rates]
    for mark in all_marks:
        if mark.observed_at > state.as_of or mark.observed_at > request.known_at:
            raise ValueError("Mark timestamp exceeds valuation or knowledge cutoff")
    valuation = value_state(
        state,
        ValuationRequest(
            as_of=state.as_of,
            known_at=request.known_at,
            prices=prices,
            fx=[f for f in rates if f.currency in currencies or f.currency == state.base_currency],
        ),
    )
    for kind, evidence in (("price", prices), ("fx", rates)):
        if any(
            (state.as_of.astimezone(UTC).date() - p.observed_at.astimezone(UTC).date()).days
            > request.max_mark_age_days
            for p in evidence
        ):
            return None, f"stale_{kind}"
    return valuation.nav, "incomplete_valuation" if valuation.nav is None else None


def _periods(daily: list[DailyResult], frequency: str) -> list[LinkedPeriod]:
    groups: dict[str, list[DailyResult]] = {}
    for row in daily[1:]:
        if frequency == "monthly":
            label = row.date.strftime("%Y-%m")
        elif frequency == "quarterly":
            label = f"{row.date.year}-Q{(row.date.month - 1) // 3 + 1}"
        else:
            label = str(row.date.year)
        groups.setdefault(label, []).append(row)
    result = []
    with localcontext(accounting_context()):
        for label, rows in groups.items():
            start, end = rows[0].date, rows[-1].date
            first_month = (
                start.month
                if frequency == "monthly"
                else ((start.month - 1) // 3) * 3 + 1
                if frequency == "quarterly"
                else 1
            )
            last_month = (
                first_month
                if frequency == "monthly"
                else first_month + 2
                if frequency == "quarterly"
                else 12
            )
            complete = start == date(start.year, first_month, 1) and end == date(
                start.year, last_month, calendar.monthrange(start.year, last_month)[1]
            )
            reason = next(
                (r.daily_return.reason for r in rows if r.daily_return.value is None), None
            )
            linked = Decimal(1)
            for row in rows:
                if row.daily_return.value is not None:
                    linked *= 1 + Decimal(str(row.daily_return.value))
            result.append(
                LinkedPeriod(
                    label=label,
                    start=start,
                    end=end,
                    partial=not complete,
                    return_value=metric(None if reason else linked - 1, reason, len(rows)),
                )
            )
    return result


def build_report(
    portfolio_id: UUID,
    base_currency: str,
    rows: list[TransactionRead],
    request: PerformanceRequest,
) -> PerformanceReport:
    """No I/O: caller locks one portfolio snapshot and verifies current version."""
    if any(r.portfolio_id != portfolio_id for r in rows):
        raise ValueError("Every transaction must belong to this portfolio")
    visible = [r for r in rows if r.recorded_at <= request.known_at]
    canceled = {r.reverses_id for r in visible if r.type == "REVERSAL"}
    active = sorted(
        (r for r in visible if r.type != "REVERSAL" and r.id not in canceled),
        key=lambda r: (r.effective_at, r.sequence),
    )
    start, end = close(request.daily_marks[0].date), close(request.daily_marks[-1].date)
    flows = [
        r for r in active if start < r.effective_at <= end and r.type in ("DEPOSIT", "WITHDRAWAL")
    ]
    supplied = {m.transaction_id: m for m in request.flow_marks}
    if set(supplied) - {r.id for r in flows}:
        raise ValueError("Flow marks must reference active external flows inside the report window")
    if (len(request.daily_marks) + len(flows)) * max(len(active), 1) > 2_000_000:
        raise ValueError("Report exceeds replay capacity; request a shorter window")
    if (
        sum(len(m.prices) + len(m.fx) for m in [*request.daily_marks, *request.flow_marks])
        > 100_000
    ):
        raise ValueError("Report exceeds supplied quote capacity")

    def state(at: datetime, before: TransactionRead | None = None) -> LedgerState:
        selected = (
            active
            if before is None
            else [
                r
                for r in active
                if (r.effective_at, r.sequence) < (before.effective_at, before.sequence)
            ]
        )
        return replay(portfolio_id, base_currency, selected, at, request.known_at)

    daily: list[DailyResult] = []
    external: list[ExternalFlow] = []
    investor_flows: list[tuple[date, Decimal]] = []
    invalid: str | None = None
    flow_fx_missing = False
    units, unit_value = Decimal(0), Decimal(1)
    initialized = False
    loss_to_zero = False
    flow_index = 0
    previous_unit = Decimal(1)
    with localcontext(accounting_context()):
        for index, marks in enumerate(request.daily_marks):
            cutoff = close(marks.date)
            invested = units > 0
            while flow_index < len(flows) and flows[flow_index].effective_at <= cutoff:
                flow = flows[flow_index]
                flow_index += 1
                evidence = supplied.get(flow.id, Marks())
                pre_nav, pre_reason = _marked_value(
                    state(flow.effective_at, flow), evidence, request, flow.currency
                )
                fx = next((f for f in evidence.fx if f.currency == flow.currency), None)
                rate = Decimal(1) if flow.currency == base_currency else fx.rate if fx else None
                if (
                    fx
                    and (
                        flow.effective_at.astimezone(UTC).date()
                        - fx.observed_at.astimezone(UTC).date()
                    ).days
                    > request.max_mark_age_days
                ):
                    rate = None
                assert flow.amount is not None
                amount = flow.amount if flow.type == "DEPOSIT" else -flow.amount
                amount_base = amount * rate if rate is not None else None
                if amount_base is not None:
                    investor_flows.append((flow.effective_at.astimezone(UTC).date(), -amount_base))
                else:
                    flow_fx_missing = True
                reason = (
                    "missing_flow_fx"
                    if rate is None
                    else "missing_flow_valuation"
                    if pre_reason
                    else None
                )
                delta = None
                invalid = invalid or reason
                if invalid is None and pre_nav is not None and amount_base is not None:
                    if units > 0:
                        if loss_to_zero and pre_nav > 0:
                            invalid = "zero_unit_value_recovery_requires_new_segment"
                        elif pre_nav == 0:
                            invalid = "zero_unit_value_at_flow"
                        elif pre_nav + amount_base < 0:
                            raise ValueError("External flow exceeds marked portfolio value")
                        else:
                            unit_value = pre_nav / units
                            delta = (
                                -units if pre_nav + amount_base == 0 else amount_base / unit_value
                            )
                            units += delta
                    elif pre_nav != 0 or loss_to_zero:
                        invalid = "capital_without_valid_units"
                    elif amount_base > 0:
                        delta = amount_base / unit_value
                        units = delta
                        initialized = True
                    else:
                        invalid = "no_invested_capital"
                    invested = True
                external.append(
                    ExternalFlow(
                        transaction_id=flow.id,
                        effective_at=flow.effective_at,
                        currency=flow.currency,
                        amount=amount,
                        amount_base=amount_base,
                        nav_before=pre_nav,
                        units_delta=delta,
                        reason=reason or invalid,
                    )
                )
            nav, reason = _marked_value(state(cutoff), marks, request)
            invalid = invalid or reason
            if index == 0:
                if nav is not None and nav > 0:
                    units = nav
                    initialized = True
                    investor_flows.insert(0, (marks.date, -nav))
                daily_return = metric(None, "opening_valuation", 0)
            else:
                if invalid is None and nav is not None:
                    if units > 0:
                        if loss_to_zero and nav > 0:
                            invalid = "zero_unit_value_recovery_requires_new_segment"
                        else:
                            unit_value = nav / units
                            loss_to_zero = unit_value == 0
                    elif nav != 0:
                        invalid = "capital_without_valid_units"
                if invalid:
                    daily_return = metric(None, invalid, 0)
                elif not initialized or not invested:
                    daily_return = metric(None, "no_invested_capital", 0)
                elif previous_unit == 0:
                    daily_return = metric(None, "zero_prior_unit_value", 0)
                else:
                    daily_return = metric(unit_value / previous_unit - 1, None, 1)
            cumulative = metric(
                unit_value - 1 if initialized and invalid is None else None,
                invalid or (None if initialized else "no_invested_capital"),
                index,
            )
            daily.append(
                DailyResult(
                    date=marks.date,
                    nav=nav,
                    units=units if invalid is None else None,
                    unit_value=unit_value if initialized and invalid is None else None,
                    daily_return=daily_return,
                    cumulative_return=cumulative,
                    reason=reason or invalid,
                )
            )
            previous_unit = unit_value
        final_nav, opening_nav = daily[-1].nav, daily[0].nav
        if final_nav is not None:
            investor_flows.append((daily[-1].date, final_nav))
        xirr_result = (
            metric(None, "incomplete_cash_flow_valuation", len(investor_flows))
            if flow_fx_missing or opening_nav is None or final_nav is None
            else xirr(investor_flows)
        )

    returns = [r.daily_return.value for r in daily[1:]]
    if all(r is not None for r in returns):
        statistics = realized_statistics(
            [r.date for r in daily[1:]],
            [r for r in returns if r is not None],
            request.risk_free_rate,
            request.confidence,
        )
    else:
        template = realized_statistics([], [], request.risk_free_rate, request.confidence)
        missing_reason = invalid or "non_contiguous_invested_returns"
        statistics = {
            name: metric(None, missing_reason, sum(r is not None for r in returns))
            for name in template
        }
    warnings = [
        "Realized returns use supplied unadjusted prices, explicit FX and booked net "
        "dividends/fees. Unrecorded costs or events are absent.",
        "UTC calendar-day closes and 365 observations/year; no market-calendar alignment "
        "or automatic price carry-forward.",
        "XIRR includes the closing marked value; it is not a cash-only realized-profit figure.",
        "Supplied data quality is not independently verified. "
        "This report makes no GIPS compliance claim.",
    ]
    if len(daily) - 1 < 365:
        warnings.append(
            "Short track record: annualized time-weighted return is withheld; ratios and tails are "
            "descriptive and statistically uncertain."
        )
    if invalid:
        warnings.append(
            "Incomplete valuation coverage prevents continuous unitization. "
            "Resolve the reported gaps and recalculate."
        )
    if any(r.effective_at <= start for r in active):
        warnings.append(
            "Selected-period report: opening market value is treated as invested capital "
            "for XIRR, not an original deposit."
        )

    manifest = PerformanceManifest(
        portfolio_id=portfolio_id,
        base_currency=base_currency,
        ledger_version=max((r.sequence for r in rows), default=0),
        known_version=max((r.sequence for r in visible), default=0),
        inputs=request,
        ledger_records=visible,
        inputs_sha256=digest(request.model_dump(mode="json")),
        ledger_sha256=digest([r.model_dump(mode="json") for r in visible]),
        git_commit_sha=os.getenv("GIT_COMMIT_SHA"),
        build_timestamp=os.getenv("BUILD_TIMESTAMP"),
        libraries={
            "python": platform.python_version(),
            **{name: version(name) for name in ("numpy", "scipy", "pydantic")},
        },
        code_sha256=source_sha256(),
        conventions=[
            "daily_unit_value; external_flows_at_ledger_timestamp_and_sequence",
            "corrected_history_at_known_at; trade_date_cash",
            "unadjusted_prices; booked_net_dividends_and_fees; no_tax_inference",
            "UTC_calendar_daily; actual_days_365_XIRR; loss_positive_drawdowns_and_tails",
            "missing_coverage_is_undefined; no_automatic_mark_fill",
            "hashes_identify_inputs; returned_inputs_and_compatible_code_are_needed_for_replay",
        ],
    )
    return PerformanceReport(
        portfolio_id=portfolio_id,
        base_currency=base_currency,
        scope="selected_period"
        if any(r.effective_at <= start for r in active)
        else "since_inception",
        start=daily[0].date,
        end=daily[-1].date,
        twr=daily[-1].cumulative_return,
        xirr=xirr_result,
        daily=daily,
        external_flows=external,
        linked={
            frequency: _periods(daily, frequency)
            for frequency in ("monthly", "quarterly", "annual")
        },
        statistics=statistics,
        warnings=warnings,
        manifest=manifest,
    )
