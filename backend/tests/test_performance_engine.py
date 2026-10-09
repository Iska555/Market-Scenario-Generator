"""Analytical ledger-to-performance reconciliation, with no provider data."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.accounting.contracts import Kind, TransactionRead
from src.performance.contracts import PerformanceRequest
from src.performance.engine import build_report

PORTFOLIO = UUID(int=801)
SECURITY = UUID(int=802)
KNOWN = datetime(2025, 2, 1, tzinfo=UTC)


def transaction(sequence: int, kind: Kind, at: str, **fields: Any) -> TransactionRead:
    return TransactionRead(
        id=UUID(int=sequence),
        portfolio_id=PORTFOLIO,
        sequence=sequence,
        type=kind,
        effective_at=datetime.fromisoformat(at),
        recorded_at=KNOWN,
        currency="GBP",
        source="analytical fixture",
        external_reference=str(sequence),
        content_sha256=str(sequence),
        **fields,
    )


def price(value: str, at: str) -> dict[str, str]:
    return dict(
        security_id=str(SECURITY),
        currency="GBP",
        price=value,
        observed_at=at,
        source="supplied test quote",
    )


def request(*daily_prices: str | None, **changes: Any) -> PerformanceRequest:
    return PerformanceRequest.model_validate(
        dict(
            expected_version=3,
            known_at=KNOWN,
            daily_marks=[
                dict(
                    date=f"2025-01-{i + 1:02d}",
                    prices=[]
                    if value is None
                    else [price(value, f"2025-01-{i + 1:02d}T20:00:00Z")],
                )
                for i, value in enumerate(daily_prices)
            ],
        )
        | changes
    )


def funded() -> list[TransactionRead]:
    return [
        transaction(1, "DEPOSIT", "2025-01-01T09:00:00Z", amount="100"),
        transaction(
            2, "BUY", "2025-01-01T10:00:00Z", security_id=SECURITY, quantity="1", price="100"
        ),
    ]


def report(rows: list[TransactionRead], req: PerformanceRequest) -> Any:
    return build_report(PORTFOLIO, "GBP", rows, req)


def test_deposit_is_neutralized_at_actual_preflow_unit_value() -> None:
    rows = [*funded(), transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="110")]
    result = report(
        rows,
        request(
            "100",
            "120",
            flow_marks=[
                dict(transaction_id=str(rows[2].id), prices=[price("110", "2025-01-02T12:00:00Z")])
            ],
        ),
    )
    # 10% before deposit, then 230/220 after; linked growth 15%, not 130% or 10%.
    assert result.twr.value == pytest.approx(0.15)
    assert result.daily[-1].nav == Decimal(230)
    assert result.daily[-1].units == Decimal(200)
    assert result.daily[-1].unit_value == Decimal("1.15")
    assert result.scope == "selected_period"
    assert result.manifest.ledger_records == rows
    assert result.manifest.inputs == request(
        "100",
        "120",
        flow_marks=[
            dict(transaction_id=str(rows[2].id), prices=[price("110", "2025-01-02T12:00:00Z")])
        ],
    )


def test_booked_dividend_and_fee_are_internal_performance() -> None:
    rows = [
        *funded(),
        transaction(3, "DIVIDEND", "2025-01-02T11:00:00Z", security_id=SECURITY, amount="5"),
        transaction(4, "FEE", "2025-01-02T12:00:00Z", amount="2"),
    ]
    result = report(rows, request("100", "100", expected_version=4))
    assert result.twr.value == pytest.approx(0.03)
    assert result.external_flows == []


def test_missing_flow_mark_does_not_treat_deposit_as_gain() -> None:
    rows = [*funded(), transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100")]
    result = report(rows, request("100", "120"))
    assert result.twr.value is None
    assert result.twr.reason == "missing_flow_valuation"
    assert result.daily[-1].nav == Decimal(220)
    assert result.xirr.reason == "root_outside_supported_bounds"


def test_missing_daily_price_invalidates_linked_returns_not_nav_coverage() -> None:
    rows = funded()
    result = report(rows, request("100", None, "110", expected_version=2))
    assert result.daily[1].nav is None
    assert result.daily[-1].nav == Decimal(110)
    assert result.twr.value is None
    assert result.statistics["max_drawdown"].value is None


def test_first_funding_establishes_units_and_since_inception_scope() -> None:
    rows = [transaction(1, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100")]
    result = report(rows, request(None, None, None, expected_version=1))
    assert result.scope == "since_inception"
    assert result.twr.value == 0
    assert result.daily[1].units == Decimal(100)
    assert result.daily[0].daily_return.value is None
    assert result.xirr.value == pytest.approx(0)


def test_full_withdrawal_does_not_create_a_loss() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T12:00:00Z", amount="100"),
        transaction(2, "WITHDRAWAL", "2025-01-02T12:00:00Z", amount="100"),
    ]
    result = report(rows, request(None, None, expected_version=2))
    assert result.twr.value == 0
    assert result.daily[-1].nav == 0
    assert result.daily[-1].units == 0


def test_reversal_is_restatement_at_known_cutoff() -> None:
    rows = [*funded(), transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100")]
    reversal = transaction(4, "REVERSAL", "2025-01-02T12:00:00Z", reverses_id=rows[2].id)
    result = report([*rows, reversal], request("100", "110", expected_version=4))
    assert result.external_flows == []
    assert result.twr.value == pytest.approx(0.1)


def test_duplicate_or_missing_calendar_days_are_rejected() -> None:
    for dates in (["2025-01-01", "2025-01-03"], ["2025-01-01", "2025-01-01"]):
        with pytest.raises(ValueError, match="consecutive"):
            request(None, None, daily_marks=[dict(date=d) for d in dates])


def test_unrelated_portfolio_and_unused_flow_marks_are_rejected() -> None:
    rows = funded()
    with pytest.raises(ValueError, match="portfolio"):
        build_report(uuid4(), "GBP", rows, request("100", "110", expected_version=2))
    with pytest.raises(ValueError, match="flow"):
        report(
            rows,
            request(
                "100", "110", expected_version=2, flow_marks=[dict(transaction_id=str(uuid4()))]
            ),
        )


def test_future_quote_is_not_valid_performance_evidence() -> None:
    req = request("100", "110", expected_version=2)
    req.daily_marks[0].prices[0].observed_at = datetime(2025, 1, 2, tzinfo=UTC)
    with pytest.raises(ValueError, match="cutoff"):
        report(funded(), req)


def test_stale_marks_are_typed_missing_coverage() -> None:
    req = request("100", "110", expected_version=2, max_mark_age_days=0)
    req.daily_marks[1].prices[0].observed_at = datetime(2025, 1, 1, 20, tzinfo=UTC)
    result = report(funded(), req)
    assert result.daily[-1].reason == "stale_price"
    assert result.twr.value is None


def test_foreign_cash_deposit_and_fx_gain_are_distinct() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T12:00:00Z", amount="100").model_copy(
            update={"currency": "USD"}
        ),
        transaction(2, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100").model_copy(
            update={"currency": "USD"}
        ),
    ]

    def fx(rate: str, at: str) -> dict[str, str]:
        return dict(currency="USD", rate=rate, observed_at=at, source="fixture FX")

    req = request(
        None,
        None,
        expected_version=2,
        daily_marks=[
            dict(date="2025-01-01", fx=[fx(".8", "2025-01-01T20:00:00Z")]),
            dict(date="2025-01-02", fx=[fx(".9", "2025-01-02T20:00:00Z")]),
        ],
        flow_marks=[dict(transaction_id=str(rows[1].id), fx=[fx(".85", "2025-01-02T12:00:00Z")])],
    )
    result = report(rows, req)
    assert result.twr.value == pytest.approx(0.125)
    assert result.external_flows[0].amount_base == Decimal(85)
    assert result.daily[-1].nav == Decimal(180)
    req.flow_marks.clear()
    missing = report(rows, req)
    assert missing.twr.reason == "missing_flow_fx"
    assert missing.xirr.reason == "incomplete_cash_flow_valuation"


def test_flow_sequence_at_same_timestamp_respects_prior_trade() -> None:
    rows = [
        *funded(),
        transaction(
            3, "SELL", "2025-01-02T12:00:00Z", security_id=SECURITY, quantity="1", price="110"
        ),
        transaction(4, "DEPOSIT", "2025-01-02T12:00:00Z", amount="110"),
    ]
    result = report(rows, request("100", None, expected_version=4))
    assert result.external_flows[0].nav_before == Decimal(110)
    assert result.twr.value == pytest.approx(0.1)


def test_period_links_have_explicit_partial_calendar_bounds() -> None:
    result = report(funded(), request("100", "120", "90", "110", expected_version=2))
    for frequency in ("monthly", "quarterly", "annual"):
        period = result.linked[frequency][0]
        assert period.partial
        assert period.return_value.value == pytest.approx(0.1)
    assert result.statistics["max_drawdown"].value == pytest.approx(0.25)
    assert result.statistics["recovery_days"].reason == "unrecovered_drawdown"


def test_zero_value_and_new_funding_cannot_reset_a_total_loss() -> None:
    rows = [*funded(), transaction(3, "DEPOSIT", "2025-01-03T12:00:00Z", amount="100")]
    result = report(
        rows,
        request(
            "100",
            "0",
            "0",
            flow_marks=[
                dict(transaction_id=str(rows[-1].id), prices=[price("0", "2025-01-03T12:00:00Z")])
            ],
        ),
    )
    assert result.daily[1].daily_return.value == -1
    assert result.twr.value is None
    assert result.twr.reason == "zero_unit_value_at_flow"


def test_flat_zero_value_interval_after_total_loss_is_not_a_zero_return() -> None:
    result = report(funded(), request("100", "0", "0", expected_version=2))
    assert result.daily[-1].daily_return.reason == "zero_prior_unit_value"
    assert result.twr.value == -1


def test_unfunded_days_and_refunding_preserve_units_without_fabricating_returns() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T12:00:00Z", amount="100"),
        transaction(2, "WITHDRAWAL", "2025-01-02T12:00:00Z", amount="100"),
        transaction(3, "DEPOSIT", "2025-01-04T12:00:00Z", amount="100"),
    ]
    result = report(rows, request(None, None, None, None))
    assert result.daily[2].daily_return.reason == "no_invested_capital"
    assert result.daily[3].unit_value == 1
    assert result.twr.value == 0
    assert result.statistics["sharpe"].reason == "non_contiguous_invested_returns"


@pytest.mark.parametrize(
    "case", ["duplicate_price", "duplicate_fx", "unused_fx", "future_flow_quote", "duplicate_flow"]
)
def test_ambiguous_evidence_is_rejected(case: str) -> None:
    rows = [*funded(), transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100")]
    data = request("100", "110").model_dump(mode="json")
    fx = dict(currency="EUR", rate=".8", observed_at="2025-01-01T12:00:00Z", source="test")
    if case == "duplicate_price":
        data["daily_marks"][0]["prices"] *= 2
    elif case in ("duplicate_fx", "unused_fx"):
        data["daily_marks"][0]["fx"] = [fx, fx] if case == "duplicate_fx" else [fx]
    else:
        data["flow_marks"] = [
            dict(transaction_id=str(rows[-1].id), prices=[price("110", "2025-01-02T20:00:00Z")])
        ]
        if case == "duplicate_flow":
            data["flow_marks"] *= 2
    with pytest.raises(ValueError):
        report(rows, PerformanceRequest.model_validate(data))


def test_historical_knowledge_excludes_later_reversal() -> None:
    rows = funded()
    reversal = transaction(3, "REVERSAL", "2025-01-01T10:00:00Z", reverses_id=rows[1].id)
    reversal.recorded_at = datetime(2025, 2, 2, tzinfo=UTC)
    result = report([*rows, reversal], request("100", "110"))
    assert result.twr.value == pytest.approx(0.1)
    assert result.manifest.known_version == 2
    assert result.manifest.ledger_version == 3
    assert len(result.manifest.ledger_records) == 2


def test_return_cannot_resume_after_zero_unit_value() -> None:
    result = report(funded(), request("100", "0", "110", expected_version=2))
    assert result.daily[1].cumulative_return.value == -1
    assert result.twr.value is None
    assert result.twr.reason == "zero_unit_value_recovery_requires_new_segment"


def test_zero_loss_recovery_cannot_be_hidden_by_same_day_full_withdrawal() -> None:
    rows = [
        *funded(),
        transaction(
            3, "SELL", "2025-01-03T10:00:00Z", security_id=SECURITY, quantity="1", price="110"
        ),
        transaction(4, "WITHDRAWAL", "2025-01-03T12:00:00Z", amount="110"),
    ]
    result = report(rows, request("100", "0", None, expected_version=4))
    assert result.daily[-1].nav == 0
    assert result.twr.value is None
    assert result.twr.reason == "zero_unit_value_recovery_requires_new_segment"


def test_fx_conversion_and_fee_remain_internal_performance() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T12:00:00Z", amount="100"),
        transaction(
            2,
            "FX_CONVERSION",
            "2025-01-02T12:00:00Z",
            amount="80",
            to_currency="USD",
            to_amount="100",
            fx_rate="1.25",
            fees="2",
        ),
    ]
    data = request(
        None,
        None,
        expected_version=2,
        daily_marks=[
            dict(date="2025-01-01"),
            dict(
                date="2025-01-02",
                fx=[
                    dict(
                        currency="USD",
                        rate=".8",
                        observed_at="2025-01-02T20:00:00Z",
                        source="fixture",
                    )
                ],
            ),
        ],
    )
    result = report(rows, data)
    assert result.external_flows == []
    assert result.daily[-1].nav == Decimal(98)
    assert result.twr.value == pytest.approx(-0.02)


def test_quote_age_uses_utc_day_for_offset_flow_timestamp() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-02T00:30:00+04:00", amount="100").model_copy(
            update={"currency": "USD"}
        ),
        transaction(2, "DEPOSIT", "2025-01-03T00:30:00+04:00", amount="100").model_copy(
            update={"currency": "USD"}
        ),
    ]

    def fx(at: str) -> dict[str, str]:
        return dict(currency="USD", rate=".8", observed_at=at, source="fixture")

    data = request(
        None,
        None,
        expected_version=2,
        max_mark_age_days=0,
        daily_marks=[
            dict(date="2025-01-01", fx=[fx("2025-01-01T20:00:00Z")]),
            dict(date="2025-01-02", fx=[fx("2025-01-02T20:00:00Z")]),
        ],
        flow_marks=[dict(transaction_id=str(rows[1].id), fx=[fx("2025-01-02T20:00:00Z")])],
    )
    result = report(rows, data)
    assert result.twr.value == 0
    assert result.external_flows[0].amount_base == Decimal(80)
