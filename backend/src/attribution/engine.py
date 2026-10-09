"""Endpoint ledger P&L linked through actual Phase 8 performance units."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from uuid import UUID

from src.accounting.contracts import LedgerState, TransactionRead, ValuationRequest, ValuationResult
from src.accounting.ledger import replay
from src.accounting.precision import accounting_context
from src.accounting.valuation import value_state
from src.attribution.contracts import (
    Component,
    ContributionReport,
    ContributionValue,
    Reconciliation,
    Segment,
)
from src.performance.contracts import Marks, PerformanceReport
from src.performance.engine import close

ZERO = Decimal(0)
ABS_TOL = Decimal("1e-12")
REL_TOL = Decimal("1e-12")
MAX_CELLS = 100_000
WARNINGS = [
    "Contributions explain recorded TWR in percentage points, "
    "not security returns or risk contributions.",
    "Local capital P&L, net dividends and fees use segment-end FX. "
    "Opening equity/cash receive FX changes; conversion principal is separate. "
    "Price/FX interaction is assigned to price.",
    "This endpoint allocation is not transaction-time FX attribution. "
    "Supplied quotes and booked events are not independently certified.",
    "Cash has no modeled interest; only booked events and marked FX can contribute. "
    "Standalone fees and conversion effects remain separate from equity rankings.",
    "Closed equities remain included. Security UUIDs identify holdings; historical sector "
    "classifications are unavailable, so no sector aggregation is inferred.",
    "Forward wealth linking allocates compounding to later increments; alternative linking "
    "conventions can assign different component results while reconciling to the same TWR.",
]


class CoverageGap(ValueError):
    """Independent contribution evidence can be incomplete while NAV is observable."""


@dataclass
class Effect:
    price: Decimal = ZERO
    dividends: Decimal = ZERO
    fees: Decimal = ZERO
    fx: Decimal = ZERO

    @property
    def total(self) -> Decimal:
        return self.price + self.dividends + self.fees + self.fx


@dataclass
class Accumulator:
    linked: Effect = field(default_factory=Effect)
    pnl: Decimal = ZERO


def valued(value: Decimal | None, reason: str | None = None) -> ContributionValue:
    return ContributionValue(value=value, reason=reason)


def component(key: str, effect: Effect, pnl: Decimal) -> Component:
    kind, _, identity = key.partition(":")
    return Component(
        key=key,
        kind=kind,  # type: ignore[arg-type]
        security_id=UUID(identity) if kind == "security" else None,
        currency=identity if kind == "cash" else None,
        price=valued(effect.price),
        dividends=valued(effect.dividends),
        fees=valued(effect.fees),
        fx=valued(effect.fx),
        total=valued(effect.total),
        pnl_base=pnl,
    )


def endpoint_effects(
    opening: ValuationResult,
    closing: ValuationResult,
    events: list[TransactionRead],
    end_marks: Marks,
    max_age: int,
) -> dict[str, Effect]:
    """Exact base P&L identity; external funding is excluded by segment boundaries."""
    parts: dict[str, Effect] = {}

    def effect(key: str) -> Effect:
        return parts.setdefault(key, Effect())

    def rate(currency: str) -> Decimal:
        if currency == opening.state.base_currency:
            return Decimal(1)
        mark = next((f for f in end_marks.fx if f.currency == currency), None)
        if mark is None:
            raise CoverageGap(f"missing_contribution_fx:{currency}")
        if (
            closing.state.as_of.astimezone(UTC).date() - mark.observed_at.astimezone(UTC).date()
        ).days > max_age:
            raise CoverageGap(f"stale_contribution_fx:{currency}")
        return mark.rate

    start_positions = {p.security_id: p for p in opening.positions}
    end_positions = {p.security_id: p for p in closing.positions}
    for security_id in sorted(start_positions.keys() | end_positions.keys()):
        start, end = start_positions.get(security_id), end_positions.get(security_id)
        position = start or end
        assert position is not None
        r_end = rate(position.currency)
        mv_start = start.market_value_local if start else ZERO
        mv_end = end.market_value_local if end else ZERO
        assert mv_start is not None and mv_end is not None
        value = effect(f"security:{security_id}")
        value.price += (mv_end - mv_start) * r_end
        if start:
            assert start.market_value_base is not None
            value.fx += mv_start * r_end - start.market_value_base
    for cash in opening.cash:
        value = effect(f"cash:{cash.currency}")
        if cash.amount:
            assert cash.value_base is not None
            value.fx += cash.amount * rate(cash.currency) - cash.value_base
    for cash in closing.cash:
        effect(f"cash:{cash.currency}")
    for row in events:
        if row.type in ("DEPOSIT", "WITHDRAWAL", "REVERSAL"):
            raise ValueError("External flows and reversals cannot be internal segment events")
        r_end = rate(row.currency)
        if row.type in ("BUY", "SELL"):
            assert row.security_id is not None and row.quantity is not None
            assert row.price is not None
            value = effect(f"security:{row.security_id}")
            principal = row.quantity * row.price * r_end
            value.price += -principal if row.type == "BUY" else principal
            value.fees -= row.fees * r_end
        elif row.type == "DIVIDEND":
            assert row.amount is not None and row.security_id is not None
            effect(f"security:{row.security_id}").dividends += row.amount * r_end
        elif row.type == "FEE":
            assert row.amount is not None
            effect("account_fees").fees -= row.amount * r_end
        else:
            assert row.amount is not None and row.to_amount is not None
            assert row.to_currency is not None
            value = effect("fx_conversion")
            value.fx += row.to_amount * rate(row.to_currency) - row.amount * r_end
            value.fees -= row.fees * r_end
    return parts


def build_contribution(performance: PerformanceReport) -> ContributionReport:
    """Reuse the accepted report's snapshot/flow deltas; do not approximate funding."""
    request = performance.manifest.inputs
    rows = performance.manifest.ledger_records
    canceled = {r.reverses_id for r in rows if r.type == "REVERSAL"}
    active = sorted(
        (r for r in rows if r.type != "REVERSAL" and r.id not in canceled),
        key=lambda r: (r.effective_at, r.sequence),
    )
    start, end = close(performance.start), close(performance.end)
    initial_state = replay(
        performance.portfolio_id, performance.base_currency, active, start, request.known_at
    )
    keys = {f"security:{p.security_id}" for p in initial_state.positions}
    keys.update(f"cash:{c.currency}" for c in initial_state.cash)
    keys.update(
        f"security:{r.security_id}"
        for r in active
        if start < r.effective_at <= end and r.security_id
    )
    for row in active:
        if start < row.effective_at <= end:
            keys.add(f"cash:{row.currency}")
            if row.type == "FEE":
                keys.add("account_fees")
            elif row.type == "FX_CONVERSION":
                keys.update(("fx_conversion", f"cash:{row.to_currency}"))
    segments: list[Segment] = []

    def unavailable(reason: str) -> ContributionReport:
        empty = [component(key, Effect(), ZERO) for key in sorted(keys)]
        for row in empty:
            for name in ("price", "dividends", "fees", "fx", "total"):
                setattr(row, name, valued(None, reason))
            row.pnl_base = None
        return ContributionReport(
            performance=performance,
            components=empty,
            segments=segments,
            top_contributors=[],
            bottom_contributors=[],
            warnings=[*WARNINGS, reason],
            reconciliation=Reconciliation(
                component_total=valued(None, reason),
                residual=valued(None, reason),
                tolerance=None,
                within_tolerance=None,
            ),
        )

    if performance.twr.value is None:
        return unavailable(performance.twr.reason or "undefined_portfolio_twr")

    def state(
        at: datetime, flow: TransactionRead | None = None, after: bool = False
    ) -> LedgerState:
        selected = (
            active
            if flow is None
            else [
                r
                for r in active
                if (r.effective_at, r.sequence) < (flow.effective_at, flow.sequence)
                or (after and r.id == flow.id)
            ]
        )
        return replay(
            performance.portfolio_id, performance.base_currency, selected, at, request.known_at
        )

    def snapshot(current: LedgerState, marks: Marks) -> ValuationResult:
        currencies = {p.currency for p in current.positions} | {c.currency for c in current.cash}
        result = value_state(
            current,
            ValuationRequest(
                as_of=current.as_of,
                known_at=request.known_at,
                prices=marks.prices,
                fx=[
                    f
                    for f in marks.fx
                    if f.currency in currencies or f.currency == current.base_currency
                ],
            ),
        )
        if result.nav is None:
            raise CoverageGap("incomplete_contribution_valuation")
        return result

    accumulated: dict[str, Accumulator] = {}
    cells = 0
    with localcontext(accounting_context()):
        try:
            opening = snapshot(state(start), request.daily_marks[0])
            units = performance.daily[0].units or ZERO
            flows = {f.transaction_id: f for f in performance.external_flows}
            evidence = {m.transaction_id: m for m in request.flow_marks}
            remaining = [r for r in active if r.id in flows]
            flow_index = 0

            def segment(closing: ValuationResult, marks: Marks, flow_id: UUID | None) -> None:
                nonlocal cells
                previous_ids = set(opening.state.active_transaction_ids)
                final_ids = set(closing.state.active_transaction_ids)
                events = [r for r in active if r.id in final_ids - previous_ids]
                parts = endpoint_effects(opening, closing, events, marks, request.max_mark_age_days)
                keys.update(parts)
                assert opening.nav is not None and closing.nav is not None
                pnl = closing.nav - opening.nav
                explained = sum((p.total for p in parts.values()), ZERO)
                if abs(pnl - explained) > ABS_TOL + REL_TOL * abs(pnl):
                    raise CoverageGap("segment_pnl_does_not_reconcile")
                if units == 0 and pnl != 0:
                    raise CoverageGap("capital_without_valid_units")
                linked: dict[str, Effect] = {}
                for key, part in parts.items():
                    rates = Effect(
                        **{
                            name: getattr(part, name) / units if units else ZERO
                            for name in ("price", "dividends", "fees", "fx")
                        }
                    )
                    linked[key] = rates
                    total = accumulated.setdefault(key, Accumulator())
                    for name in ("price", "dividends", "fees", "fx"):
                        setattr(
                            total.linked, name, getattr(total.linked, name) + getattr(rates, name)
                        )
                    total.pnl += part.total
                cells += len(parts) + len(opening.positions) + len(opening.cash)
                if cells > MAX_CELLS:
                    raise ValueError(
                        "Contribution exceeds segment/exposure capacity; request a shorter window"
                    )
                segments.append(
                    Segment(
                        start=opening.state.as_of,
                        end=closing.state.as_of,
                        before_flow_id=flow_id,
                        transaction_ids=[r.id for r in events],
                        units=units,
                        opening_nav=opening.nav,
                        closing_nav=closing.nav,
                        opening_positions=opening.positions,
                        opening_cash=opening.cash,
                        components=[component(k, linked[k], parts[k].total) for k in sorted(parts)],
                        linked_total=valued(sum((p.total for p in linked.values()), ZERO)),
                    )
                )

            for index, marks in enumerate(request.daily_marks[1:], 1):
                cutoff = close(marks.date)
                while flow_index < len(remaining) and remaining[flow_index].effective_at <= cutoff:
                    flow = remaining[flow_index]
                    flow_index += 1
                    mark = evidence.get(flow.id, Marks())
                    closing = snapshot(state(flow.effective_at, flow), mark)
                    segment(closing, mark, flow.id)
                    delta = flows[flow.id].units_delta
                    if delta is None:
                        raise CoverageGap(flows[flow.id].reason or "undefined_flow_units")
                    units += delta
                    opening = snapshot(state(flow.effective_at, flow, after=True), mark)
                closing = snapshot(state(cutoff), marks)
                segment(closing, marks, None)
                if performance.daily[index].units != units:
                    raise CoverageGap("performance_unit_mismatch")
                opening = closing
        except CoverageGap as exc:
            return unavailable(str(exc))
        components = [component(k, v.linked, v.pnl) for k, v in sorted(accumulated.items())]
        total = sum((v.linked.total for v in accumulated.values()), ZERO)
        twr = Decimal(str(performance.twr.value))
        residual = twr - total
        tolerance = ABS_TOL + REL_TOL * abs(twr)
        equities = [c for c in components if c.kind == "security"]
        ranking = sorted(equities, key=lambda c: (-(c.total.value or ZERO), c.key))
        return ContributionReport(
            performance=performance,
            components=components,
            segments=segments,
            top_contributors=[c.key for c in ranking if c.total.value and c.total.value > 0][:5],
            bottom_contributors=[
                c.key for c in reversed(ranking) if c.total.value and c.total.value < 0
            ][:5],
            reconciliation=Reconciliation(
                component_total=valued(total),
                residual=valued(residual),
                tolerance=tolerance,
                within_tolerance=abs(residual) <= tolerance,
            ),
            warnings=WARNINGS
            + ([] if abs(residual) <= tolerance else ["linked_contributions_do_not_reconcile"]),
        )
